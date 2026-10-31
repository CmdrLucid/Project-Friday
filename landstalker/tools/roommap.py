#!/usr/bin/env python3
"""roommap.py ROM OUTDIR [--png AREA_ROOM OUT.png] [--force]   -- data for the in-game room map (2026-10-31, user wish 'eigene Raumkarte', MODERN_IDEAS (B), docs/MAP.md).
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

VERSION = "roommap v5"   # v5: rooms as W x H boxes, neighbours at their door, connectors at the doors (user: connections where there are none)   # v4: height map cells shifted by (12, 12) to the game's cell coordinates   # v3: dungeons only (user 2026-10-31: towns with all their interiors were too cluttered)   # v2: nearest free cell instead of pushing along the line
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
    # v5 (user 2026-10-31: 'connections where there are none' in the Swamp Shrine): rooms have several doors on one side (room 5: three to the NW), one cell per room
    # cannot show that.  Each room is now a box of W x H grid units (U cells per unit, at least 1) in the proportions of its floor; a neighbour is put against the
    # side of the door, shifted along that side so that both door units meet; stairs put the upper room over the door on the next floor.  Taken places: slide along
    # the side, then push outwards.  Edges carry both door points (local units x 10) so the map draws short connectors exactly at the doors.
    U = 8
    box = {}
    for r in area_of:
        xs = [k[0] for k in fps[r]] or [0]; ys = [k[1] for k in fps[r]] or [0]
        x0, y0, w, h = min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        box[r] = (x0, y0, w, h, max(1, int(w / U + 0.5)), max(1, int(h / U + 0.5)))
    def dpt(r, x, y):   # door point in the room's local units (fraction), clamped into the box
        x0, y0, w, h, W, H = box[r]
        return (min(max((x - x0 + 0.5) / w * W, 0.0), W), min(max((y - y0 + 0.5) / h * H, 0.0), H))
    def snap(r, p, d):   # put the door point on the side d
        W, H = box[r][4], box[r][5]; u, v = p
        if d == 'NW': u = 0.0
        elif d == 'SE': u = float(W)
        elif d == 'NE': v = 0.0
        elif d == 'SW': v = float(H)
        return (u, v)
    nb = defaultdict(list); edges = []
    for c in conns:
        a, b = c['r1'], c['r2']
        if area_of.get(a) is None or area_of.get(a) != area_of.get(b): continue
        s1 = side(fps[a], c['x1'], c['y1']); s2 = side(fps[b], c['x2'], c['y2'])
        d = s1 or (OPP[s2] if s2 else 'SE'); up = 1 if c['e1'] in (10, 20) else 0
        pa = dpt(a, c['x1'], c['y1']); pb = dpt(b, c['x2'], c['y2'])
        if not up: pa = snap(a, pa, d); pb = snap(b, pb, OPP[d])
        nb[a].append((b, d, up, pa, pb)); nb[b].append((a, OPP[d], -up, pb, pa)); edges.append((a, b, up, pa, pb))
    pos = {}
    for ai, (reg, comp) in enumerate(areas):
        start = comp[0]; p0 = {start: (0, 0, 0)}; q = deque([start])
        def free(r, gx, gy, l):
            W, H = box[r][4], box[r][5]
            for o, (ox, oy, ol) in p0.items():
                if ol == l and o != r and gx < ox + box[o][4] and ox < gx + W and gy < oy + box[o][5] and oy < gy + H: return False
            return True
        while q:
            r = q.popleft(); x, y, l = p0[r]
            for o, d, up, pr, po in sorted(nb[r], key=lambda t: (t[0], t[1], t[2])):
                if o in p0: continue
                W, H = box[o][4], box[o][5]
                bx, by = x + pr[0] - po[0], y + pr[1] - po[1]          # door points meet
                if up: cand = [(0, 0)]
                elif d == 'NW': bx = x - W; cand = [(0, 1)]
                elif d == 'SE': bx = x + box[r][4]; cand = [(0, 1)]
                elif d == 'NE': by = y - H; cand = [(1, 0)]
                else: by = y + box[r][5]; cand = [(1, 0)]
                gx0, gy0 = int(round(bx)), int(round(by)); out = DIRS.get(d, (1, 1)); along = cand[0]
                spot = None
                for k in range(0, 12):
                    for sl in (0, 1, -1, 2, -2, 3, -3, 4, -4):
                        gx = gx0 + out[0] * k + along[0] * sl; gy = gy0 + out[1] * k + along[1] * sl
                        if up or free(o, gx, gy, l + up): spot = (gx, gy); break
                    if spot: break
                if not spot: spot = (gx0 + out[0] * 12, gy0 + out[1] * 12)
                p0[o] = (spot[0], spot[1], l + up); q.append(o)
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
