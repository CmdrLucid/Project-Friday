#!/usr/bin/env python3
"""roommap.py ROM OUTDIR [--thumbs] [--force]   -- data for the in-game room map (2026-10-31, user wish 'eigene Raumkarte', MODERN_IDEAS (B), docs/MAP.md).
Built on the player's machine from his own ROM by build.sh (nothing of it goes into git).  Writes OUTDIR/layout.txt and OUTDIR/thumbs.bin:
 * areas: rooms grouped by region (name prefix from docs/ROOMS.md, unnamed rooms inherit their neighbours' region) and connected by the room connections
   (tools/roomgraph.py, `$11CEA2`); one area = one map.  The rooms do NOT fit together geometrically (measured: placing them by the door cells overlaps them), so the
   map is SCHEMATIC: a 2:1 grid, each room one cell, a neighbour one cell in the direction of its exit (which edge of the room's floor the door cell lies on: NE / NW / SE / SW).
 * floors: a connection with extra bits 10 / 20 (`$0A` / `$14`) is a staircase from the LOWER room (first in the record) to the UPPER one (checked: Mercator armory 0F -> 1F -> 2F,
   castle 1F -> 2F hallway, Ryuma lighthouse 2F -> top); floor = steps from the area's first room, normalised to start at 0.
 * visited bit per room: `RoomVisitedFlagLookup $00C74E` (word per room = bit number in the flags at `$FF10C0`, SetRoomVisited `$00293C`).
 * thumbs: every room drawn from the ROM (tools/romrender.py) and shrunk to at most TW pixels wide, RGB565, 0 = transparent.
layout.txt lines:  'A area floors name' / 'R room area floor gx gy visitbit floor_left floor_top floor_w floor_h W H' (box W x H grid units at gx, gy) /
'E room1 room2 stairs door1_u door1_v door2_u door2_v' (door points in the rooms' local units x 10) / 'V variant original'.
Takes ~1 s per room on one core; runs on all cores (multiprocessing); skipped when OUTDIR already holds the data of this ROM and VERSION (--force rebuilds)."""
import hashlib, os, re, struct, sys, zlib
from collections import Counter, defaultdict, deque
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import roomgraph, romroom

VERSION = "roommap v8"   # v8: boxes sized by door count, one slot per door, best of TRIALS randomised placements (user: proportions need not be right, doors must fit)   # v7: floors from a walk over the stairs first; v6: most-linked room next, spot with the smallest total door distance (user: a door into nothing)   # v5: rooms as W x H boxes, neighbours at their door, connectors at the doors (user: connections where there are none)   # v4: height map cells shifted by (12, 12) to the game's cell coordinates   # v3: dungeons only (user 2026-10-31: towns with all their interiors were too cluttered)   # v2: nearest free cell instead of pushing along the line
TRIALS = 60   # randomised placements per area (v8)
TW = 112                     # thumbnail width (pixels): the map cells are drawn at most ~1.3 x this at 1280 x 800
MULTI = ["KN_LABYRINTH", "KN_CAVE", "KN_PALACE", "LAKE_SHRINE", "SWAMP_SHRINE", "WATERFALL_SHRINE", "THIEVES_HIDEOUT", "DESTEL_WELL", "MIR_TOWER", "VERLA_MINES",
         "HELGAS_HUT", "MERCATOR_CASTLE", "MERCATOR_DUNGEON", "RYUMA_LIGHTHOUSE", "GREENMAZE", "ROUTE_GUMI_RYUMA", "ROUTE_AFTER_DESTEL", "MASSAN_CAVE"]
DUNGEONS = {"SWAMP_SHRINE", "MERCATOR_DUNGEON", "KN_LABYRINTH", "KN_CAVE", "KN_PALACE", "LAKE_SHRINE", "WATERFALL_SHRINE", "THIEVES_HIDEOUT", "DESTEL_WELL",
            "MIR_TOWER", "VERLA_MINES", "MASSAN_CAVE", "CRYPT", "GREENMAZE", "HELGAS_HUT", "TIBOR", "RYUMA_LIGHTHOUSE"}   # map areas (user 2026-10-31: nur Dungeon-Karten)
DIRS = {'NE': (0, -1), 'NW': (-1, 0), 'SE': (1, 0), 'SW': (0, 1)}
OPP = {'NE': 'SW', 'SW': 'NE', 'NW': 'SE', 'SE': 'NW'}

def room_names():
    names = {}
    for ln in open(os.path.join(HERE, "..", "docs", "ROOMS.md")):
        m = re.match(r'\| (\d+) \| \$[0-9A-F]+ \| (\w+)', ln)
        if m: names[int(m.group(1))] = m.group(2)
    return names

def region_of(name):
    for p in MULTI:
        if name.startswith(p): return p
    return name.split('_')[0]

def footprint(rom, room):
    """walkable cells of the room's height map (type nibble != 4), dict (x, y) -> word, plus the map size.  Keys in GAME cell coordinates (the coordinates of the
    connection records and of Nigel `$FF5400 / $FF5401`): the height map lands at offset (12, 12) in RAM (FORMATS 'placement'), romroom.arrays gives it unshifted
    (v4 fix, user 2026-10-31: 'I leave the first room south-east, the map shows the next one north-east' = every exit side was judged 12 cells off)"""
    d = romroom.decode(rom, room); hm = romroom.arrays(d)['HM']
    return {(k[0] + 12, k[1] + 12): v for k, v in hm.items() if k[0] < d['hm_w'] and k[1] < d['hm_h'] and (v >> 12) != 4}, d

def side(fp, x, y):
    if not fp: return None
    xs = [k[0] for k in fp]; ys = [k[1] for k in fp]
    d = {'NW': x - min(xs), 'SE': max(xs) - x, 'NE': y - min(ys), 'SW': max(ys) - y}
    k = min(d, key=d.get)
    return k if d[k] <= 3 else None

def build(rom):
    names = room_names(); g = roomgraph.read(rom)
    nroom = (0x01B6F0 - 0x01B090) // 2
    fps, dims = {}, {}
    for r in range(nroom):
        try: fps[r], d = footprint(rom, r); dims[r] = (d['hm_w'], d['hm_h'])
        except Exception: pass
    conns = [c for c in g['conns'] if c['r1'] in fps and c['r2'] in fps]
    adj = defaultdict(set)
    for c in conns: adj[c['r1']].add(c['r2']); adj[c['r2']].add(c['r1'])
    region = {r: region_of(n) for r, n in names.items()}
    for _ in range(8):   # unnamed rooms: the most common region of their neighbours
        for r in adj:
            if r not in region:
                cand = Counter(region[o] for o in adj[r] if o in region)
                if cand: region[r] = cand.most_common(1)[0][0]
    rooms = sorted(r for r in adj if r in region)
    area_of, areas = {}, []
    for r in rooms:
        if r in area_of: continue
        comp, q = [], deque([r]); area_of[r] = len(areas)
        while q:
            x = q.popleft(); comp.append(x)
            for o in adj[x]:
                if o not in area_of and region.get(o) == region[r]: area_of[o] = len(areas); q.append(o)
        areas.append((region[r], sorted(comp)))
    areas = [a for a in areas if a[0] in DUNGEONS]   # towns, routes, castles: no map
    area_of = {x: ai for ai, (reg, comp) in enumerate(areas) for x in comp}
    # v8 (user 2026-10-31: 'schematic, proportions need not be right, as long as the doors fit'): a room's box is as long on a side as it has doors there
    # (at least 1 x 1), each door gets its own unit slot on its side (in the order of the real door positions), a neighbour is put so that both door slots
    # face each other exactly.  Loops of the dungeon may still not close: several randomised placements per area, the one with the fewest doors that do not
    # meet (then the smallest total door distance, then the smallest area) wins.
    import random
    rawe = []
    for c in conns:
        a, b = c['r1'], c['r2']
        if area_of.get(a) is None or area_of.get(a) != area_of.get(b): continue
        s1 = side(fps[a], c['x1'], c['y1']); s2 = side(fps[b], c['x2'], c['y2'])
        rawe.append((a, b, 1 if c['e1'] in (10, 20) else 0, s1 or (OPP[s2] if s2 else 'SE'), c['x1'], c['y1'], c['x2'], c['y2']))
    slots = defaultdict(list)
    for k, (a, b, up, d, x1, y1, x2, y2) in enumerate(rawe):
        if up: continue
        slots[(a, d)].append((y1 if d in ('NW', 'SE') else x1, k, 0))
        slots[(b, OPP[d])].append((y2 if OPP[d] in ('NW', 'SE') else x2, k, 1))
    box = {}
    for r in area_of:
        xs = [k[0] for k in fps[r]] or [0]; ys = [k[1] for k in fps[r]] or [0]
        n = {sd: len(slots.get((r, sd), [])) for sd in DIRS}
        box[r] = (min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, max(2, n['NE'], n['SW']), max(2, n['NW'], n['SE']))   # at least 2 x 2 (a 4 x 1 strip looked odd, user)
    dp = {}
    for (r, sd), lst in slots.items():
        lst.sort(); W, H = box[r][4], box[r][5]; L = H if sd in ('NW', 'SE') else W; off = (L - len(lst)) // 2
        for i, (al, k, end) in enumerate(lst):
            q_ = off + i + 0.5
            dp[(k, end)] = {'NW': (0.0, q_), 'SE': (float(W), q_), 'NE': (q_, 0.0), 'SW': (q_, float(H))}[sd]
    nb = defaultdict(list); edges = []
    for k, (a, b, up, d, x1, y1, x2, y2) in enumerate(rawe):
        pa = dp.get((k, 0), (box[a][4] / 2.0, box[a][5] / 2.0)); pb = dp.get((k, 1), (box[b][4] / 2.0, box[b][5] / 2.0))   # stairs: the middle of the room
        nb[a].append((b, d, up, pa, pb)); nb[b].append((a, OPP[d], -up, pb, pa)); edges.append((a, b, up, pa, pb))
    def floors(comp):   # floors first: ONE walk over the stairs from the area's first room (the stairs of some areas are not free of contradictions, so the result must not depend on the trial)
        lev = {comp[0]: 0}; q = deque([comp[0]])
        while q:
            r = q.popleft()
            for (m, d, up, pr, pm) in nb[r]:
                if m not in lev: lev[m] = lev[r] + up; q.append(m)
        return lev
    def place(comp, rng, start, lev):
        p0 = {start: (0, 0, lev.get(start, 0))}
        def free(r, gx, gy, l):
            W, H = box[r][4], box[r][5]
            for o, (ox, oy, ol) in p0.items():
                if ol == l and o != r and gx < ox + box[o][4] and ox < gx + W and gy < oy + box[o][5] and oy < gy + H: return False
            return True
        def want(r, o, d, up, pr, po):
            x, y, l = p0[r]; W, H = box[o][4], box[o][5]
            bx, by = int(round(x + pr[0] - po[0])), int(round(y + pr[1] - po[1]))
            if up: return bx, by, (0, 0), (0, 0)
            if d == 'NW': return x - W, by, DIRS['NW'], (0, 1)
            if d == 'SE': return x + box[r][4], by, DIRS['SE'], (0, 1)
            if d == 'NE': return bx, y - H, DIRS['NE'], (1, 0)
            return bx, y + box[r][5], DIRS['SW'], (1, 0)
        while True:
            best_n, todo = 0, []
            for o in comp:
                if o in p0: continue
                n = sum(1 for t in nb[o] if t[0] in p0)
                if n > best_n: best_n, todo = n, [o]
                elif n == best_n and n: todo.append(o)
            if not todo: break
            o = rng.choice(todo); fl = lev.get(o, 0)
            links = [(m, OPP[d], -up, pm, po) for (m, d, up, po, pm) in nb[o] if m in p0]
            cands = set()
            for (m, d, up, pm, po) in links:
                gx0, gy0, out, along = want(m, o, d, up, pm, po)
                if up or p0[m][2] != fl: cands.add((gx0, gy0, 0)); continue
                for k in range(0, 8):
                    for sl in range(-5, 6): cands.add((gx0 + out[0] * k + along[0] * sl, gy0 + out[1] * k + along[1] * sl, k + abs(sl)))
            best = None
            for (gx, gy, pen) in cands:
                if not free(o, gx, gy, fl): continue
                miss = 0; cost = 0.05 * pen
                for (m, d, up, pm, po) in links:
                    mx, my, ml = p0[m]
                    if up or ml != fl: continue
                    dd = abs(mx + pm[0] - gx - po[0]) + abs(my + pm[1] - gy - po[1]); cost += dd; miss += dd > 0.01
                key = (miss, cost, rng.random())
                if best is None or key < best[0]: best = (key, gx, gy)
            if best is None:   # every candidate taken: the nearest free spot around the first wanted one (ring by ring)
                gx0, gy0, out, along = want(*links[0][:1], o, *links[0][1:])
                for rad in range(1, 60):
                    ring = [(gx0 + dx, gy0 + dy) for dx in range(-rad, rad + 1) for dy in range(-rad, rad + 1) if max(abs(dx), abs(dy)) == rad and free(o, gx0 + dx, gy0 + dy, fl)]
                    if ring: best = (None,) + min(ring, key=lambda c: abs(c[0] - gx0) + abs(c[1] - gy0)); break
            p0[o] = (best[1], best[2], fl)
        miss = cost = 0
        for (a, b, up, pa, pb) in edges:
            if a in p0 and b in p0 and not up and p0[a][2] == p0[b][2]:
                dd = abs(p0[a][0] + pa[0] - p0[b][0] - pb[0]) + abs(p0[a][1] + pa[1] - p0[b][1] - pb[1]); cost += dd; miss += dd > 0.01
        xs = [p[0] for p in p0.values()]; ys = [p[1] for p in p0.values()]
        return (miss, cost, (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)), p0
    pos = {}
    for ai, (reg, comp) in enumerate(areas):
        rng = random.Random(1000 + ai); best = None; lev = floors(comp)
        for t in range(TRIALS):
            sc, p0 = place(comp, rng, comp[0] if t == 0 else rng.choice(comp), lev)
            if best is None or sc < best[0]: best = (sc, p0)
        p0 = best[1]
        lmin = min(p[2] for p in p0.values())
        for r, (x, y, l) in p0.items(): pos[r] = (ai, l - lmin, x, y)
    variants = [(v['variant'], v['room']) for v in g['variants']]
    lines = []
    for ai, (reg, comp) in enumerate(areas):
        lines.append("A %d %d %s" % (ai, 1 + max(pos[r][1] for r in comp if r in pos), reg))
    for r in sorted(pos):
        ai, l, x, y = pos[r]; vb = (rom[0xC74E + 2 * r] << 8) | rom[0xC74E + 2 * r + 1]
        xs = [k[0] for k in fps[r]] or [0]; ys = [k[1] for k in fps[r]] or [0]
        lines.append("R %d %d %d %d %d %d %d %d %d %d %d %d" % (r, ai, l, x, y, vb, min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, box[r][4], box[r][5]))
    for r1, r2, up, pa, pb in edges: lines.append("E %d %d %d %d %d %d %d" % (r1, r2, up, round(pa[0] * 10), round(pa[1] * 10), round(pb[0] * 10), round(pb[1] * 10)))
    for v, o in variants: lines.append("V %d %d" % (v, o))
    return lines, sorted(pos), areas, pos

def thumb(args):
    """one room drawn from the ROM, shrunk (box filter, black = transparent) to at most TW wide; returns (room, w, h, RGB565 bytes)"""
    romp, room = args
    import romrender
    rom = open(romp, 'rb').read()
    try:
        g, r, pa, pb, getpal = romrender.rom_planes(rom, room)
        cells = list(pb.t) + list(pa.t)
        c0 = min(c for c, rr in cells); c1 = max(c for c, rr in cells); r0 = min(rr for c, rr in cells); r1 = max(rr for c, rr in cells)
        w, h = (c1 - c0 + 1) * 8, (r1 - r0 + 1) * 8
        rgb = romrender.compose(pa, pb, getpal, c0 * 8, r0 * 8, w, h, romrender.md_to_rgb(0), g['tiles'])
    except Exception:
        return room, 0, 0, b''
    f = max(1, (w + TW - 1) // TW); tw, th = w // f, h // f; out = bytearray()
    for y in range(th):
        for x in range(tw):
            ar = ag = ab = n = nb = 0
            for yy in range(y * f, y * f + f):
                i = (yy * w + x * f) * 3
                for k in range(f):
                    c0_, c1_, c2_ = rgb[i], rgb[i + 1], rgb[i + 2]; i += 3
                    if c0_ == 0 and c1_ == 0 and c2_ == 0: nb += 1; continue
                    ar += c0_; ag += c1_; ab += c2_; n += 1
            if n <= nb: out += b'\0\0'; continue
            v = ((ar // n >> 3) << 11) | ((ag // n >> 2) << 5) | (ab // n >> 3)
            out += struct.pack('<H', v or 1)
    return room, tw, th, bytes(out)

def main():
    a = sys.argv[1:]
    if len(a) < 2: print(__doc__); sys.exit(1)
    romp, outd = a[0], a[1]
    rom = open(romp, 'rb').read()
    key = hashlib.sha256(rom).hexdigest()[:16] + " " + VERSION + " " + hashlib.sha256(open(__file__, 'rb').read()).hexdigest()[:12]
    os.makedirs(outd, exist_ok=True)
    stamp = os.path.join(outd, "stamp.txt")
    if "--force" not in a and os.path.exists(stamp) and open(stamp).read().strip() == key:
        print("roommap: up to date (%s)" % outd); return
    lines, rooms, areas, pos = build(rom)
    open(os.path.join(outd, "layout.txt"), "w").write("\n".join(lines) + "\n")
    print("roommap: %d areas, %d rooms" % (len(areas), len(rooms)), flush=True)
    if "--thumbs" not in a:   # v7: the map is schematic (user: the room pictures looked pixelated), no pictures needed; --thumbs still makes them
        tb = os.path.join(outd, "thumbs.bin")
        if os.path.exists(tb): os.remove(tb)
        open(stamp, "w").write(key + "\n"); print("roommap: layout written (no room pictures)"); return
    import inspect
    tkey = hashlib.sha256(rom).hexdigest()[:16] + " TW %d " % TW + hashlib.sha256(inspect.getsource(thumb).encode()).hexdigest()[:12] + " %d" % len(rooms)
    tstamp = os.path.join(outd, "thumbs_stamp.txt")
    if "--force" not in a and os.path.exists(tstamp) and os.path.exists(os.path.join(outd, "thumbs.bin")) and open(tstamp).read().strip() == tkey:
        open(stamp, "w").write(key + "\n"); print("roommap: layout written, thumbnails up to date"); return
    import multiprocessing
    with multiprocessing.Pool() as pool:
        res = []
        for i, t in enumerate(pool.imap_unordered(thumb, [(romp, r) for r in rooms], chunksize=4)):
            res.append(t)
            if i % 50 == 0: print("roommap: thumbnails %d / %d" % (i, len(rooms)), flush=True)
    res.sort()
    hdr = b"LKRM1" + struct.pack('<I', len(res)); body = b''; idx = b''
    for room, w, h, data in res:
        idx += struct.pack('<HHHI', room, w, h, len(body)); body += data
    open(os.path.join(outd, "thumbs.bin"), "wb").write(hdr + idx + body)
    open(stamp, "w").write(key + "\n"); open(tstamp, "w").write(tkey + "\n")
    print("roommap: wrote %s (layout.txt, thumbs.bin %d KB)" % (outd, (len(hdr) + len(idx) + len(body)) // 1024))

if __name__ == '__main__':
    try: main()
    except Exception as e:   # the map is optional: a failure must not stop the build
        import traceback; traceback.print_exc(); print('roommap: WARNING: no room map data (%s); the game runs without the map' % e)
