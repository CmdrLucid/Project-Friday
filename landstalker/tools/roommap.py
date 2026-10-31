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
'E room1 room2 stairs door1_u door1_v door2_u door2_v' (door points in the rooms' local units x 10) / 'W k' (E line k is a river passage) / 'V variant original'.
Takes ~1 s per room on one core; runs on all cores (multiprocessing); skipped when OUTDIR already holds the data of this ROM and VERSION (--force rebuilds)."""
import hashlib, os, re, struct, sys, zlib
from collections import Counter, defaultdict, deque
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import roomgraph, romroom

VERSION = "roommap v17"   # v17: W lines = river / raft passages (KN cave 163 / 165 / 167: user saw 2 doors, the map 3)   # v16: door side from the door cell's floor type (01..04 = NE / SE / SW / NW), not the nearest footprint edge (user: door top left drawn into a room on the left)   # v15: route search through the free lanes for the pairs still apart (any number of bends, at most 8)   # v14: connections keyed by their index (two rooms can be joined twice)   # v13: layout pulled apart by one unit at every box edge (longer bridges, lanes for the bent corridors)   # v12: bent corridors (L / Z / U) for the pairs still apart   # v11: corridors must not cross   # v10: straight free corridors between facing doors count as connected (E lines: last field)   # v9: no door may touch a room it does not lead to (false contacts weigh more than missed doors)   # v8: boxes sized by door count, one slot per door, best of TRIALS randomised placements (user: proportions need not be right, doors must fit)   # v7: floors from a walk over the stairs first; v6: most-linked room next, spot with the smallest total door distance (user: a door into nothing)   # v5: rooms as W x H boxes, neighbours at their door, connectors at the doors (user: connections where there are none)   # v4: height map cells shifted by (12, 12) to the game's cell coordinates   # v3: dungeons only (user 2026-10-31: towns with all their interiors were too cluttered)   # v2: nearest free cell instead of pushing along the line
TRIALS = 60   # randomised placements per area (v8)
KMAX = 8      # how far out (grid units) a room may be put from the door that asks for it (v12)
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

DOORTYPE = {1: 'NE', 2: 'SE', 3: 'SW', 4: 'NW'}   # floor type (low byte of the height map cell & $3F) of a door cell: ProcessFloorType $00603C 01..04 = door NE / SE / SW / NW

def door_side(fa, xa, ya, fb, xb, yb):
    """wall of room a that the connection (xa, ya) -> room b (xb, yb) leaves through (v16, user recording rec_20261031_1743: KN cave 165 -> 170 drawn to the NW,
    the door is in the NE wall next to the corner).  1) the door cell's own floor type (the game's exit direction; set on 663 of 1576 connection ends, the walk-in end),
    2) the partner end's floor type, opposite side, 3) the sum of both ends' distances to their footprint edges (one end alone ties at corners)"""
    t = fa.get((xa, ya), 0) & 0x3F if fa else 0
    if t in DOORTYPE: return DOORTYPE[t]
    t = fb.get((xb, yb), 0) & 0x3F if fb else 0
    if t in DOORTYPE: return OPP[DOORTYPE[t]]
    def dist(fp, x, y):
        xs = [k[0] for k in fp]; ys = [k[1] for k in fp]
        return {'NW': x - min(xs), 'SE': max(xs) - x, 'NE': y - min(ys), 'SW': max(ys) - y}
    if not fa or not fb: return side(fa, xa, ya) or (OPP[side(fb, xb, yb)] if side(fb, xb, yb) else None)
    da, db = dist(fa, xa, ya), dist(fb, xb, yb)
    return min(DIRS, key=lambda k: da[k] + db[OPP[k]])

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
    rawe = []; water = set()
    for c in conns:
        a, b = c['r1'], c['r2']
        if area_of.get(a) is None or area_of.get(a) != area_of.get(b): continue
        s1 = door_side(fps[a], c['x1'], c['y1'], fps[b], c['x2'], c['y2'])   # v16: the door cell's floor type first (was: nearest footprint edge of one end)
        rawe.append((a, b, 1 if c['e1'] in (10, 20) else 0, s1 or 'SE', c['x1'], c['y1'], c['x2'], c['y2']))
        if (fps[a].get((c['x1'], c['y1']), 0) >> 12) & 1 or (fps[b].get((c['x2'], c['y2']), 0) >> 12) & 1: water.add(len(rawe) - 1)   # v17: an end on a raft track cell (byte 0 bit 4) = a river passage, not a door
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
    doorpts = defaultdict(list)   # room -> [(local door point, partner)] (no stairs): for the 'false contact' test
    for (a, b, up, pa, pb) in edges:
        if not up: doorpts[a].append((pa, b)); doorpts[b].append((pb, a))
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
        def dside(r, pt):   # which side of its box a door point is on (outward direction)
            if pt[0] < 0.01: return (-1, 0)
            if pt[0] > box[r][4] - 0.01: return (1, 0)
            if pt[1] < 0.01: return (0, -1)
            return (0, 1)
        def cut(r0, r1, ua, va, ub, vb, l, extra=None):   # does any other box (on floor l) cut the straight corridor (ua, va) - (ub, vb)?  extra = (room, gx, gy) not yet in p0
            items = list(p0.items()) + ([(extra[0], (extra[1], extra[2], l))] if extra else [])
            lo_u, hi_u, lo_v, hi_v = min(ua, ub), max(ua, ub), min(va, vb), max(va, vb)
            for m, (mx, my, ml) in items:
                if ml != l or m in (r0, r1): continue
                if mx < hi_u + 0.01 and mx + box[m][4] > lo_u - 0.01 and my < hi_v + 0.01 and my + box[m][5] > lo_v - 0.01: return True
            return False
        def linked(a, pa, ga, b, pb, gb, l, extra=None):   # v10: doors meet, or face each other on one straight free line (a corridor)
            ua, va, ub, vb = ga[0] + pa[0], ga[1] + pa[1], gb[0] + pb[0], gb[1] + pb[1]
            if abs(ua - ub) + abs(va - vb) < 0.01: return True
            da, db = dside(a, pa), dside(b, pb)
            if (da[0] + db[0], da[1] + db[1]) != (0, 0): return False
            if da[0] and abs(va - vb) < 0.01 and (ub - ua) * da[0] > 0: return not cut(a, b, ua, va, ub, vb, l, extra)
            if da[1] and abs(ua - ub) < 0.01 and (vb - va) * da[1] > 0: return not cut(a, b, ua, va, ub, vb, l, extra)
            return False
        def falses(o, gx, gy, l):   # v9: doors that would touch a room they do not lead to (user: 'why does door 1 connect to door 2?')
            n = 0; W, H = box[o][4], box[o][5]
            for (pt, partner) in doorpts[o]:
                u, v = gx + pt[0], gy + pt[1]
                for m, (mx, my, ml) in p0.items():
                    if ml == l and m != partner and m != o and mx - 0.01 <= u <= mx + box[m][4] + 0.01 and my - 0.01 <= v <= my + box[m][5] + 0.01: n += 1
            for m, (mx, my, ml) in p0.items():
                if ml != l or m == o: continue
                for (pt, partner) in doorpts[m]:
                    if partner == o: continue
                    u, v = mx + pt[0], my + pt[1]
                    if gx - 0.01 <= u <= gx + W + 0.01 and gy - 0.01 <= v <= gy + H + 0.01: n += 1
            return n
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
                for k in range(0, KMAX):   # v12: farther out (longer corridors, user: 'longer bridges to line things up better'; the map scrolls now)
                    for sl in range(-5, 6): cands.add((gx0 + out[0] * k + along[0] * sl, gy0 + out[1] * k + along[1] * sl, k + abs(sl)))
            best = None
            corrs = []   # the corridors between placed rooms on this floor (once per step; a new box must not cut them)
            for (a, b, up, pa, pb) in edges:
                if up or a not in p0 or b not in p0 or p0[a][2] != fl or p0[b][2] != fl: continue
                ua, va, ub, vb = p0[a][0] + pa[0], p0[a][1] + pa[1], p0[b][0] + pb[0], p0[b][1] + pb[1]
                if abs(ua - ub) + abs(va - vb) > 0.01 and linked(a, pa, p0[a][:2], b, pb, p0[b][:2], fl): corrs.append((min(ua, ub), max(ua, ub), min(va, vb), max(va, vb)))
            for (gx, gy, pen) in cands:
                if not free(o, gx, gy, fl): continue
                miss = 0; cost = 0.05 * pen; cross = 0
                for (m, d, up, pm, po) in links:
                    mx, my, ml = p0[m]
                    if up or ml != fl: continue
                    dd = abs(mx + pm[0] - gx - po[0]) + abs(my + pm[1] - gy - po[1]); cost += 0.3 * dd
                    if not linked(m, pm, (mx, my), o, po, (gx, gy), fl, (o, gx, gy)): miss += 1; continue
                    ua, va, ub, vb = mx + pm[0], my + pm[1], gx + po[0], gy + po[1]   # the new corridor must not cross an existing one (it would look like a junction, user)
                    nu0, nu1, nv0, nv1 = min(ua, ub), max(ua, ub), min(va, vb), max(va, vb)
                    for (u0, u1, v0, v1) in corrs:
                        if nu0 < u1 - 0.01 and nu1 > u0 + 0.01 and nv0 < v1 + 0.01 and nv1 > v0 - 0.01 or nv0 < v1 - 0.01 and nv1 > v0 + 0.01 and nu0 < u1 + 0.01 and nu1 > u0 - 0.01: cross += 1
                W_, H_ = box[o][4], box[o][5]
                brk = sum(1 for (u0, u1, v0, v1) in corrs if gx < u1 + 0.01 and gx + W_ > u0 - 0.01 and gy < v1 + 0.01 and gy + H_ > v0 - 0.01)   # corridors this box would cut
                key = (falses(o, gx, gy, fl) + brk + cross, miss, cost, rng.random())
                if best is None or key < best[0]: best = (key, gx, gy)
            if best is None:   # every candidate taken: the nearest free spot around the first wanted one (ring by ring)
                gx0, gy0, out, along = want(*links[0][:1], o, *links[0][1:])
                for rad in range(1, 60):
                    ring = [(gx0 + dx, gy0 + dy) for dx in range(-rad, rad + 1) for dy in range(-rad, rad + 1) if max(abs(dx), abs(dy)) == rad and free(o, gx0 + dx, gy0 + dy, fl)]
                    if ring: best = (None,) + min(ring, key=lambda c: abs(c[0] - gx0) + abs(c[1] - gy0)); break
            p0[o] = (best[1], best[2], fl)
        miss = cost = fal = 0
        for r in p0: fal += sum(1 for (pt, partner) in doorpts[r] for m, (mx, my, ml) in p0.items() if ml == p0[r][2] and m not in (r, partner) and mx - 0.01 <= p0[r][0] + pt[0] <= mx + box[m][4] + 0.01 and my - 0.01 <= p0[r][1] + pt[1] <= my + box[m][5] + 0.01)
        for (a, b, up, pa, pb) in edges:
            if a in p0 and b in p0 and not up and p0[a][2] == p0[b][2]:
                dd = abs(p0[a][0] + pa[0] - p0[b][0] - pb[0]) + abs(p0[a][1] + pa[1] - p0[b][1] - pb[1]); cost += dd; miss += not linked(a, pa, p0[a][:2], b, pb, p0[b][:2], p0[a][2])
        met = {k for k, (a, b, up, pa, pb) in enumerate(edges) if a in p0 and b in p0 and not up and p0[a][2] == p0[b][2] and linked(a, pa, p0[a][:2], b, pb, p0[b][:2], p0[a][2])}   # by edge index: two rooms can be joined twice
        xs = [p[0] for p in p0.values()]; ys = [p[1] for p in p0.values()]
        return (fal, miss, cost, (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)), (p0, met)
    pos = {}; metall = set(); bends = {}; edgefix = {}; boxfix = {}
    for ai, (reg, comp) in enumerate(areas):
        rng = random.Random(1000 + ai); best = None; lev = floors(comp)
        for t in range(TRIALS):
            sc, p0 = place(comp, rng, comp[0] if t == 0 else rng.choice(comp), lev)
            if best is None or sc < best[0]: best = (sc, p0)
        p0, mt = best[1]
        # v13 (user: 'make the bridges longer'): pull the layout apart by one unit at every box edge (per floor): touching doors become short straight bridges and
        # free lanes appear between all rooms for the bent corridors.  Start edges map with 'lines <= x', end edges and doors with 'lines < x', so two boxes that
        # touched get exactly one unit between them, every box keeps its order and doors that met stay face to face.
        bx = {}; ept = {}; p1 = {}
        for l in set(q[2] for q in p0.values()):
            rs = [r for r in p0 if p0[r][2] == l]
            Lu = sorted(set([p0[r][0] for r in rs] + [p0[r][0] + box[r][4] for r in rs])); Lv = sorted(set([p0[r][1] for r in rs] + [p0[r][1] + box[r][5] for r in rs]))
            fs = lambda x, L: x + sum(1 for t in L if t <= x + 1e-6); fe = lambda x, L: x + sum(1 for t in L if t < x - 1e-6)
            for r in rs:
                u0, v0 = fs(p0[r][0], Lu), fs(p0[r][1], Lv); u1, v1 = fe(p0[r][0] + box[r][4], Lu), fe(p0[r][1] + box[r][5], Lv)
                p1[r] = (u0, v0, l); bx[r] = (u1 - u0, v1 - v0)
            for ke, (a, b, up, pa, pb) in enumerate(edges):
                for (r, pt, end) in ((a, pa, 0), (b, pb, 1)):
                    if r not in p1 or p0[r][2] != l: continue
                    gu, gv = p0[r][0] + pt[0], p0[r][1] + pt[1]
                    nu = fs(gu, Lu) if pt[0] < 0.01 and not up else fe(gu, Lu); nv = fs(gv, Lv) if pt[1] < 0.01 and not up else fe(gv, Lv)
                    ept[(ke, end)] = (nu - p1[r][0], nv - p1[r][1])
        for r in p0: p0[r] = p1[r]
        edges2 = [(a, b, up, ept.get((k, 0), pa), ept.get((k, 1), pb)) for k, (a, b, up, pa, pb) in enumerate(edges)]
        for k, (a, b, up, pa, pb) in enumerate(edges):   # only this area's doors (an earlier version overwrote every other area's mapped doors with the old ones)
            if (k, 0) in ept or (k, 1) in ept: edgefix[k] = (ept.get((k, 0), pa), ept.get((k, 1), pb))
        for r in bx: boxfix[r] = bx[r]
        box_ = dict(box); box = {r: (box_[r][0], box_[r][1], box_[r][2], box_[r][3]) + bx.get(r, box_[r][4:6]) for r in box_}
        edges_l = edges2
        # the pairs that met / had a straight corridor still do (same lines, order kept)
        metall |= mt
        # v12: bent corridors (user: 'longer bridges to line things up better'): every pair still apart gets an L / Z / U route if one exists that touches no box
        # (other than its two rooms) and crosses no corridor; straight corridors of the layout come first
        segs = []
        for k, (a, b, up, pa, pb) in enumerate(edges_l):
            if k in mt:
                ua, va, ub, vb = p0[a][0] + pa[0], p0[a][1] + pa[1], p0[b][0] + pb[0], p0[b][1] + pb[1]
                if abs(ua - ub) + abs(va - vb) > 0.01: segs.append((p0[a][2], ua, va, ub, vb))
        def sfree(l, a, b, u0, v0, u1, v1):
            lu, hu, lv, hv = min(u0, u1), max(u0, u1), min(v0, v1), max(v0, v1)
            for m, (mx, my, ml) in p0.items():
                if ml != l: continue
                inner = 0.0 if m in (a, b) else -0.01   # its own two rooms: only the inside is forbidden (the route starts on their edge)
                if m in (a, b):
                    if mx + 0.01 < hu and mx + box[m][4] - 0.01 > lu and my + 0.01 < hv and my + box[m][5] - 0.01 > lv: return False
                elif mx < hu + 0.01 and mx + box[m][4] > lu - 0.01 and my < hv + 0.01 and my + box[m][5] > lv - 0.01: return False
            for (sl_, su0, sv0, su1, sv1) in segs:   # no crossing / overlapping another corridor
                if sl_ != l: continue
                slu, shu, slv, shv = min(su0, su1), max(su0, su1), min(sv0, sv1), max(sv0, sv1)
                if lu <= shu + 0.01 and hu >= slu - 0.01 and lv <= shv + 0.01 and hv >= slv - 0.01: return False
            return True
        def side_of(r, pt):
            if pt[0] < 0.01: return (-1, 0)
            if pt[0] > box[r][4] - 0.01: return (1, 0)
            if pt[1] < 0.01: return (0, -1)
            return (0, 1)
        for k, (a, b, up, pa, pb) in enumerate(edges_l):
            if up or k in mt or a not in p0 or b not in p0 or p0[a][2] != p0[b][2]: continue
            l = p0[a][2]; A = (p0[a][0] + pa[0], p0[a][1] + pa[1]); B = (p0[b][0] + pb[0], p0[b][1] + pb[1]); da, db = side_of(a, pa), side_of(b, pb)
            routes = []
            if da[0] * db[0] + da[1] * db[1] == 0:   # perpendicular: L (one corner)
                C = (B[0], A[1]) if da[0] else (A[0], B[1])
                if (C[0] - A[0]) * da[0] + (C[1] - A[1]) * da[1] > 0.3 and (C[0] - B[0]) * db[0] + (C[1] - B[1]) * db[1] > 0.3: routes.append([C])
            else:
                for t in [x * 0.5 for x in range(1, 25)]:   # Z (facing, offset) or U (same side): out by t, across, in
                    P = (A[0] + da[0] * t, A[1] + da[1] * t)
                    Q = (P[0], B[1]) if da[0] else (B[0], P[1])
                    if (Q[0] - B[0]) * db[0] + (Q[1] - B[1]) * db[1] < 0.3: continue
                    routes.append([P, Q])
            for wp in sorted(routes, key=lambda w: sum(abs(x[0] - y[0]) + abs(x[1] - y[1]) for x, y in zip([A] + w, w + [B]))):
                pts = [A] + wp + [B]
                if all(sfree(l, a, b, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1)):
                    bends[k] = wp; metall.add(k)
                    for i in range(len(pts) - 1): segs.append((l, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]))
                    break
        # v15 (user: 'the two 1-doors could be joined too'): every pair still apart gets a route found by a search through the free lanes (half-unit grid between
        # the boxes, any number of bends, fewest bends first, then the shortest), never through a box, never on / across another corridor
        import heapq
        def route(l, a, b, A, da, B, db):
            occ = set()
            for m, (mx, my, ml) in p0.items():
                if ml != l: continue
                for i in range(int(2 * mx) + 1, int(2 * (mx + box[m][4]))):
                    for j in range(int(2 * my) + 1, int(2 * (my + box[m][5]))): occ.add((i, j))
            for (sl_, su0, sv0, su1, sv1) in segs:
                if sl_ != l: continue
                n = int(round(2 * (abs(su1 - su0) + abs(sv1 - sv0))))
                for t in range(n + 1):
                    occ.add((int(round(2 * su0 + (2 * su1 - 2 * su0) * t / max(n, 1))), int(round(2 * sv0 + (2 * sv1 - 2 * sv0) * t / max(n, 1)))))
            S = (int(round(2 * A[0] + da[0])), int(round(2 * A[1] + da[1]))); G = (int(round(2 * B[0] + db[0])), int(round(2 * B[1] + db[1])))
            if S in occ or G in occ: return None
            us = [i for (i, j) in occ] + [S[0], G[0]]; vs = [j for (i, j) in occ] + [S[1], G[1]]
            lo_i, hi_i, lo_j, hi_j = min(us) - 8, max(us) + 8, min(vs) - 8, max(vs) + 8
            start = (S, da); dist = {start: (0, 0)}; prev = {}; pq = [(0, 0, S, da)]
            while pq:
                c, ln, node, d = heapq.heappop(pq)
                if dist.get((node, d), (1e9,))[0] < c: continue
                if node == G and d == (-db[0], -db[1]):
                    path = [node]; st = (node, d)
                    while st in prev: st = prev[st]; path.append(st[0])
                    path.reverse(); pts = [A] + [(x / 2.0, y / 2.0) for (x, y) in path] + [B]
                    wp = [pts[i] for i in range(1, len(pts) - 1) if (pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) != (0, 0) and
                          ((pts[i][0] - pts[i - 1][0]) * (pts[i + 1][1] - pts[i][1]) - (pts[i][1] - pts[i - 1][1]) * (pts[i + 1][0] - pts[i][0])) != 0]
                    return wp
                for nd in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if nd == (-d[0], -d[1]): continue
                    nx = (node[0] + 2 * nd[0], node[1] + 2 * nd[1])
                    if nx != G and (nx in occ or not (lo_i <= nx[0] <= hi_i and lo_j <= nx[1] <= hi_j)): continue
                    if nx == G and nx in occ: continue
                    nc = c + 1 + (6 if nd != d else 0)
                    if nc < dist.get((nx, nd), (1e9,))[0]:
                        dist[(nx, nd)] = (nc, 0); prev[(nx, nd)] = (node, d); heapq.heappush(pq, (nc, 0, nx, nd))
            return None
        todo = [k for k, (a, b, up, pa, pb) in enumerate(edges_l) if not up and k not in mt and k not in bends and a in p0 and b in p0 and p0[a][2] == p0[b][2]]
        todo.sort(key=lambda k: abs(p0[edges_l[k][0]][0] - p0[edges_l[k][1]][0]) + abs(p0[edges_l[k][0]][1] - p0[edges_l[k][1]][1]))
        for k in todo:
            a, b, up, pa, pb = edges_l[k]; l = p0[a][2]
            A = (p0[a][0] + pa[0], p0[a][1] + pa[1]); B = (p0[b][0] + pb[0], p0[b][1] + pb[1])
            wp = route(l, a, b, A, side_of(a, pa), B, side_of(b, pb))
            if wp is None or len(wp) > 8: continue
            bends[k] = wp; metall.add(k); pts = [A] + wp + [B]
            for i in range(len(pts) - 1): segs.append((l, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]))
        lmin = min(p[2] for p in p0.values())
        for r, (x, y, l) in p0.items(): pos[r] = (ai, l - lmin, x, y)
    variants = [(v['variant'], v['room']) for v in g['variants']]
    lines = []
    for ai, (reg, comp) in enumerate(areas):
        lines.append("A %d %d %s" % (ai, 1 + max(pos[r][1] for r in comp if r in pos), reg))
    for r in sorted(pos):
        ai, l, x, y = pos[r]; vb = (rom[0xC74E + 2 * r] << 8) | rom[0xC74E + 2 * r + 1]
        xs = [k[0] for k in fps[r]] or [0]; ys = [k[1] for k in fps[r]] or [0]
        lines.append("R %d %d %d %d %d %d %d %d %d %d %d %d" % (r, ai, l, x, y, vb, min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, boxfix.get(r, box[r][4:6])[0], boxfix.get(r, box[r][4:6])[1]))
    for k, (r1, r2, up, pa, pb) in enumerate([(a, b, up, *edgefix.get(k, (pa, pb))) for k, (a, b, up, pa, pb) in enumerate(edges)]):   # last fields: 1 = connected (doors meet / straight corridor / bent corridor), then the corridor's bend points (absolute grid units x 10)
        wp = bends.get(k, [])
        lines.append("E %d %d %d %d %d %d %d %d" % (r1, r2, up, round(pa[0] * 10), round(pa[1] * 10), round(pb[0] * 10), round(pb[1] * 10), 1 if k in metall else 0) + "".join(" %d %d" % (round(x * 10), round(y * 10)) for x, y in wp))   # last field: 1 = doors meet or face each other on a free straight corridor
    for k in sorted(water): lines.append("W %d" % k)   # v17: E line number k (0-based, file order) is a river / raft passage (drawn blue)
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
