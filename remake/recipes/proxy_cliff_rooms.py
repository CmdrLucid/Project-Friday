#!/usr/bin/env python3
"""LIGHT SHAPES: the CLASS B CLIFFS below walkways (2026-11-27, user: 'mach die Klippe unter den Gehwegen'; rules from the user's marks on room 465).

Problem: a walkway at the top of a cliff has VOID cells in front of it (+x / +y); the light's water rule painted them 8 below the walkway and then in
8 unit terraces, so the drawn cliff face was read as a gentle FLOOR: the sword glow ran down the cliff as if on ground, the sun lit it like a floor.

Recipe per room (measured on the drawn room picture + the game's height map; prints the light ops, writes landstalker/data/proxies/cliffedge_<room>_<k>.obj):
  * SEEDS = the void cells in front of the class B walkway edges (a walkable cell with a void cell at +x / +y whose drawn pixels below the edge are drawn,
    non-water for >= 48 units), minus the cells of earlier mesh / ground / water ops (rock walls etc.); the RIVER grows from them through void cells whose
    floor point at L is drawn as water (v2 2026-11-27: a flood through all void cells caught the space behind the drawing = hundreds of 'rock' cells).
  * RIVER LEVEL L (per room, SPECS): the lowest drawn cliff foot. A seed is WATER where its floor point at L is drawn as water (blue), ROCK where
    rock is drawn there (the cliff stands in front of it). Choose L so that NO rock seed is left: then the drawn bank line lies on the walkway's own cell
    edges and the cliff IS the walkway's vertical face from its height down to L (user rule: 'the face under a walkway edge follows the edge's direction';
    a rock solid in front of the walkway made faces across the edge = wrong colour in the light view). Room 465: L = -32 (at 0 rock cells stood in the
    bank's notches and the river showed as floor in front of the faces).
  * WATER ops at L over rectangles of the water cells (a water op sets EVERY cell of its rectangle, so the rectangles hold only region cells).
  * EDGE MODEL: the walkway cells along the cliff (a water cell at +x, +y or +x+y) as real blocks from L up to their walkway height, one mesh per
    rectangle of such cells ('surface'): with the height field alone the light drew a bright 1 px seam at every +x / +y corner of the cliff (GPU
    2026-11-27); as a model the corners are clean.
Check every room with the light view (local scratch ~/Project-Friday-Test/lktest/klippe/lview.py: +x red, +y blue, up green over the drawing) and
lightedges old / new (day + night sword) before keeping it.

Run (numpy + PIL, the ROM): ~/Project-Friday-Test/hdvenv/bin/python remake/recipes/proxy_cliff_rooms.py ROM ROOM [--level L] [--map]
     -> JSON list of ops on stdout (put them into landstalker/data/light_proxies.json), the OBJs into landstalker/data/proxies/ (our own geometry)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "landstalker", "tools"))
import numpy as np, romrender, romroom, proxysurvey as PS

SPECS = {465: dict(level=-32, note="cliff path above the river: walkways 80..144, the drawn bank lies on their cell edges at -32"),
         601: dict(level=0, also=[602, 603], note="Gumi village hill in the river (601..603 = one map): the drawn bank lies on the walkway edges at 0 (foot measured 2)"),
         226: dict(level=-160, deep=True, note="plateau with the stone door: the cliff below runs off the picture (deep mode; needs LK_RAYZMIN v1: the GPU view ray stopped at -40)"),
         475: dict(zones=[   # Mir's tower hill (2026-11-28): every walkway is 16 in the game, the drawing digs forest DITCHES between the switchbacks and drops off the picture at the front / right
             dict(kind="pit", level=-40, rect=(20, 14, 39, 53), note="forest ditch inside the switchback (down to row 53, right of the descending path x 25..26) + the band between the plateau and the right path "
                  "(drawn rock under the walkway edges (19,37..46)x, (34,14..18)x, (32,33)y, (26,49..53)x ends where the pines begin, 54..56 px below = -40)"),
             dict(kind="pit", level=-40, rect=(12, 49, 24, 54), note="forest ditch below the path row 48 (left of the descending path; user mark 2026-11-28), same drawn depth"),
             dict(kind="deep", level=-160, rect=(12, 55, 21, 66), outside=True, note="the left front cliff below the meadow's left edge (19..21, 54) runs off the picture (user mark 2026-11-28)"),
             dict(kind="pit", level=-40, rect=(25, 55, 33, 57), note="forest ditch between the path row 54 and the meadow row 58"),
             dict(kind="pit", level=-96, rect=(14, 36, 17, 36), note="ROCK WEDGE between the plateau corner (15..17, 35) and the lake left of the path start (user mark 2026-11-28): "
                  "the lake cells drawn as rock (blue share <= 3 of 9 floor points); the plateau's +y face reaches the water at 84..100 px below its edge"),
             dict(kind="pit", level=-96, rect=(15, 37, 17, 38), note="rock wedge, rows 37..38"),
             dict(kind="pit", level=-96, rect=(16, 39, 17, 39), note="rock wedge, row 39"),
             dict(kind="pit", level=-96, rect=(17, 40, 17, 41), note="rock wedge, rows 40..41"),
             dict(kind="deep", level=-160, rect=(40, 48, 50, 66), outside=True, note="the right front cliff runs off the picture (faces 85..160 px down to the picture edge)"),
             dict(kind="deep", level=-160, rect=(45, 14, 50, 47), outside=True, note="the strip beyond the right path: the cliff runs off the picture"),
             dict(kind="deep", level=-160, rect=(22, 59, 39, 66), outside=True, note="the front cliff below the meadow runs off the picture")]),
         478: dict(zones=[   # waterfall room with the cave door (2026-11-28): the ledge (28..40, 47..51, 0..48) in front of the door drops off the picture (faces 80..128 px to the picture edge); the light had water 0 there
             dict(kind="deep", level=-160, rect=(28, 51, 46, 62), outside=True, note="the cliff below the door ledge runs off the picture (the waterfall columns x <= 27 stay)"),
             dict(kind="deep", level=-160, rect=(41, 47, 46, 50), outside=True, note="the cliff right of the door ledge runs off the picture")]),
         505: dict(zones=[   # path descending along x in front of the rock wall (2026-11-28): the face below its +y edge runs to the picture edge; the light painted the void as water terraces 56..136
             dict(kind="deep", level=-160, rect=(28, 25, 47, 40), outside=True, note="the cliff below the descending path runs off the picture"),
             dict(kind="deep", level=-160, rect=(48, 28, 54, 40), outside=True, note="the cliff below the last steps (48..51, 26..27); the void behind the steps (rows 23..25) is drawn rock wall, not cliff: left out")]),
         501: dict(level=0, bulge=-48, note="shore below the round-tree hill: the faces reach the water exactly 80 px below the 80 walkway edges (22..23, 25)y, (36..37, 29)y = water 0; "
                   "the bank's bulges (floor point at 0 drawn rock) at -48 (the level where no cell in front of the faces is drawn rock)"),
         523: dict(level=0, bulge=-48, add_water=[(46, 20, 55, 23)], note="cave-door ledge above the water: faces 80 px from the 80 walkways (47..49, 19)y down to the water = 0; bulges at -48; "
                   "the water right of the ledge reaches the wall at y 320 (drawn water edge V - U / 2 = y - 592: U 1590..1700 -> 327), the flood stopped short of it"),
         470: dict(zones=[   # rock bowl with the cave door (2026-11-28): the forest plateau (80) drops off the picture at the front; a small drawn LEDGE with two pines on that face (like 469)
             dict(kind="ledge", level=-23, rect=(28, 41, 29, 41), note="the drawn ledge with two pines on the front cliff: pine feet U 976 / 992 V 583 / 591 moved along the view ray onto the first cells in front "
                  "of the +y face of the 112 rim (28..29, 40): feet at the centres of (28, 41) / (29, 41), ground 80 - 103 = -23; its front corner then lies at U 992 V 599 = the drawn corner"),
             dict(kind="deep", level=-160, rect=(23, 41, 40, 56), outside=True, note="the cliff below the forest plateau and the stairs runs off the picture (the light painted it as water 8 / 72 / 112)"),
             dict(kind="deep", level=-160, rect=(30, 37, 40, 40), outside=True, note="the same cliff in front of the plateau's stepped right front (rows 37..40)")]),
         461: dict(zones=[   # forest maze (2026-11-28): the rock face below the 80..112 walkways of row 36 (x 19..23, 27..30) runs down to the drawing's bottom edge (z 16 at its foot, measured);
             # the light painted the void in front 72..88 (a face only 8..24 high)
             dict(kind="deep", level=-160, rect=(19, 37, 30, 44), note="the face below the row-36 walkways runs to the picture's bottom edge")]),
         469: dict(zones=[   # the stair path across the rock wall (2026-11-28): the face below the path's +x edge runs to the picture edge (127..231 px, foot below -110); the light had a floor at 0
             dict(kind="ledge", level=107, rect=(28, 34, 31, 36), note="the drawn FOREST LEDGE on the rock face (user mark 2026-11-28): 4 x 3 bushes (+ 3 pines behind) on a cell grid, "
                  "trunk feet front corner U 1102 V 433; moved along the view ray onto the first cells in front of the walkway's +y face (row 33): bush feet at cell centres x 28..31 y 34..36, ground 107"),
             dict(kind="deep", level=-160, rect=(24, 34, 33, 59), outside=True, note="the cliff below the stair path runs off the picture (also the drawn cliff beyond the height map's x 28, which the light painted as water 0)"),
             dict(kind="deep", level=-160, rect=(22, 58, 23, 63), outside=True, note="below the end of the stair path (22..23, 57) the cliff runs on to the picture edge")])}

def picture(rom, room):
    g, r, pa, pb, getpal = romrender.rom_planes(rom, room)
    return np.frombuffer(bytes(romrender.compose(pa, pb, getpal, 0, 0, 2400, 1300, (0, 0, 0), g['tiles'])), np.uint8).reshape(1300, 2400, 3).astype(int)

def class_b_edges(rom, room, hm, img, skip):
    """walkable cells with a void cell in FRONT (+x / +y) whose drawn pixels below the shared edge are drawn, non-water for 48 units (a cliff over void)"""
    d = romroom.decode(rom, room); a = romroom.arrays(d)['HM']
    W = {(x + 12, y + 12): v for (x, y), v in a.items() if 0 <= x < d['hm_w'] and 0 <= y < d['hm_h']}
    def kind(v):
        if v == 0: return 'w'
        hi = v >> 8
        if hi == 0x4F: return 'bar'
        if hi & 0x40 and (hi & 15) == 0 and not hi & 0x20: return 'void'
        return 'blk' if hi & 0x60 else 'w'
    m = img.sum(2) > 30; blue = (img[..., 2] > img[..., 0] + 30) & (img[..., 2] >= img[..., 1])
    out = []
    for (x, y), v in W.items():
        if kind(v) != 'w': continue
        z = 16 * ((v >> 8) & 15)
        for dx, dy in ((1, 0), (0, 1)):
            n = W.get((x + dx, y + dy))
            if n is None or kind(n) != 'void' or skip((x + dx, y + dy)): continue
            ex, ey = (16 * (x + 1), 16 * y + 8) if dx else (16 * x + 8, 16 * (y + 1))
            U = int(ex - ey + 1184); V0 = int((ex + ey) / 2 - z)
            if not 0 <= U < 2400: continue
            col = m[V0 + 2:V0 + 50, U] & ~blue[V0 + 2:V0 + 50, U]
            if len(col) and col.mean() > 0.95: out.append((x, y))
    return out

def rects(cells):
    left = set(cells); out = []
    while left:
        x0, y0 = min(left, key=lambda c: (c[1], c[0])); x1 = x0
        while (x1 + 1, y0) in left: x1 += 1
        y1 = y0
        while all((x, y1 + 1) in left for x in range(x0, x1 + 1)): y1 += 1
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1): left.discard((x, y))
        out.append((x0, y0, x1, y1))
    return out

def build(rom, room, level, show_map=False, dry=False, deep=False, bulge=None):
    hm = PS.heights(rom, room); img = picture(rom, room)
    drawn = img.sum(2) > 30; blue = (img[..., 2] > img[..., 0] + 30) & (img[..., 2] >= img[..., 1])
    lp = json.load(open(os.path.join(ROOT, "landstalker", "data", "light_proxies.json")))["rooms"].get(str(room), [])
    other = [o["cells"] for o in lp if o["op"] in ("mesh", "ground", "water") and "CLASS B" not in o.get("why", "")]
    skip = lambda c: any(r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3] for r in other)
    void = lambda c: hm.get(c) == (0, True) and not skip(c)
    walkable = lambda c: c in hm and not hm[c][1]
    cb = class_b_edges(rom, room, hm, img, skip)
    seed = {(x + dx, y + dy) for x, y in cb for dx, dy in ((1, 0), (0, 1)) if void((x + dx, y + dy))}
    def cls(c):   # 'water' / 'rock' / None (outside the drawing) for a void cell at the river level
        X, Y = 16 * c[0] + 8, 16 * c[1] + 8; U, V = int(round(X - Y + 1184)), int(round((X + Y) / 2 - level))
        if not (0 <= U < 2400 and 0 <= V < 1300) or not drawn[V, U]: return None
        return 'water' if blue[V, U] else 'rock'
    water, rock = set(), {c for c in seed if cls(c) == 'rock'}   # ROCK = a cell right in front of a cliff edge whose floor at the level is drawn as rock: the level is too high (or the cliff stands on ground)
    st = [c for c in seed if cls(c) == 'water']; water.update(st)
    while st:   # the river: grow from the seeds through void cells drawn as WATER only (the void behind the drawing, other areas stay as they are)
        x, y = st.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in water and void(n) and cls(n) == 'water': water.add(n); st.append(n)
    def wet(c):   # deep mode: a cell whose floor point is drawn as WATER at a usual water height (0..48) stays the painted river (room 226: the river beside the plateau was pulled down to the deep floor at first)
        X, Y = 16 * c[0] + 8, 16 * c[1] + 8
        for zz in (0, 16, 24, 32, 48):
            U, V = int(round(X - Y + 1184)), int(round((X + Y) / 2 - zz))
            if 0 <= U < 2400 and 0 <= V < 1300 and blue[V, U]: return True
        return False
    if deep:   # CLIFF INTO THE DEEP (the drawn cliff runs off the picture, no foot): the void IN FRONT of the edges (forward only: +x / +y, at most 12 cells) becomes a deep
        # floor at the level (ground op, replace = no water), so the walkway's face reaches below the picture
        water, rock, st = set(seed), set(), [(c, 0) for c in seed]
        while st:
            (x, y), d = st.pop()
            for n in ((x + 1, y), (x, y + 1)):
                if n not in water and void(n) and d < 12 and not wet(n): water.add(n); st.append((n, d + 1))
        water = {c for c in water if not wet(c)}
    reg = water | rock
    for r in SPECS.get(room, {}).get("add_water", []):   # 2026-11-28 (523): measured water cells the flood did not reach (floor point on the drawn water edge)
        water |= {(x, y) for x in range(r[0], r[2] + 1) for y in range(r[1], r[3] + 1) if void((x, y))}
    reg = water | rock
    if bulge is not None and not deep:   # 2026-11-28 (501 / 523): the river at its MEASURED surface L (faces reach the water F = z - L px below straight edges); the cells in front of
        # the bank's drawn BULGES (floor point at L drawn as rock) become ground at the bulge level instead, so the drawn bank there is the walkway's face, not a floor
        low = {}
        for c in hm:
            if not walkable(c): continue
            ls = [level if n in water else bulge for n in ((c[0] + 1, c[1]), (c[0], c[1] + 1), (c[0] + 1, c[1] + 1)) if n in reg]
            if ls and min(ls) < 16 * hm[c][0]: low[c] = min(ls)
        ops = [{"op": "water", "cells": list(r) + [level], "why": "room %d CLASS B CLIFF below the walkway (2026-11-28): the river at its drawn surface %d (the faces reach the water %d below "
                "straight walkway edges); the cliff is the walkway's own vertical face; remake/recipes/proxy_cliff_rooms.py" % (room, level, level)} for r in rects(water)]
        ops += [{"op": "ground", "cells": list(r) + [bulge], "replace": True, "why": "room %d CLASS B CLIFF: a drawn BULGE of the bank in front of the walkway (its floor point at the river level %d "
                 "is drawn rock) = floor at %d below the face, no floor in the drawn rock; remake/recipes/proxy_cliff_rooms.py" % (room, level, bulge)} for r in rects(rock)]
        groups = {}
        for c, lv in low.items(): groups.setdefault(lv, set()).add(c)
        k = 0
        for lv in sorted(groups):
            for r in rects(groups[lv]):
                name = edge_obj(room, k, r, hm, low, "level %d" % lv, dry); k += 1
                ops.append({"op": "mesh", "cells": list(r), "file": "proxies/" + name, "surface": True,
                            "why": "room %d CLASS B cliff EDGE: the walkway cells along the cliff as real blocks from %d up to their walkway height (the cliff = their own vertical faces, user "
                                   "2026-11-27; as a model its corners have no height-field seam); remake/recipes/proxy_cliff_rooms.py" % (room, lv)})
        ops += notch_ops(room, hm, low, {**{c: level for c in water}, **{c: bulge for c in rock}}, dry, "river / bulge level")
        print("proxy_cliff_rooms %d: river %d, %d water cells, %d bulge cells at %d, %d edge cells, %d ops" % (room, level, len(water), len(rock), bulge, len(low), len(ops)), file=sys.stderr)
        return ops, set()
    edge = {c for c in hm if walkable(c) and any((c[0] + dx, c[1] + dy) in water for dx, dy in ((1, 0), (0, 1), (1, 1)))}
    if deep:   # only the walkways AT a detected cliff edge (the forward flood reached an unrelated path at the picture edge in room 226)
        near = set(cb) | {c for c in hm if walkable(c) and any((c[0] + dx, c[1] + dy) in seed for dx, dy in ((1, 0), (0, 1), (1, 1)))}
        edge &= near
    if show_map:
        xs = [c[0] for c in reg]; ys = [c[1] for c in reg]
        for y in range(min(ys) - 1, max(ys) + 2):
            print("%2d " % y + "".join("R" if (x, y) in rock else "w" if (x, y) in water else "E" if (x, y) in edge else
                  ("." if (x, y) not in hm else "#" if hm[(x, y)][1] else "%X" % min(hm[(x, y)][0], 15)) for x in range(min(xs) - 3, max(xs) + 2)), file=sys.stderr)
    if deep: ops = [{"op": "ground", "cells": list(r) + [level], "replace": True, "why": "room %d CLASS B CLIFF INTO THE DEEP below the walkway (2026-11-27): the drawn cliff runs off the picture; the void in front of the walkway "
            "(forward, 12 cells) = a deep floor at %d so the walkway's own vertical face reaches below the picture (the water rule had painted it 8 below the walkway = the cliff read as a gentle floor); "
            "remake/recipes/proxy_cliff_rooms.py" % (room, level)} for r in rects(water)]
    else: ops = [{"op": "water", "cells": list(r) + [level], "why": "room %d CLASS B CLIFF below the walkway (2026-11-27): the void in front of the walkway down to the drawn river bank = water at %d; "
            "the cliff is the walkway's own vertical face reaching down to it (the water rule had painted it 8 below the walkway = the drawn cliff read as a gentle floor); "
            "remake/recipes/proxy_cliff_rooms.py" % (room, level)} for r in rects(water)]
    for k, r in enumerate(rects(edge)):
        V, F = [], []
        for x in range(r[0], r[2] + 1):
            for y in range(r[1], r[3] + 1):
                z = 16 * hm[(x, y)][0]; x0, y0, x1, y1 = 16 * x, 16 * y, 16 * x + 16, 16 * y + 16; n = len(V)
                V += [(x0, y0, level), (x1, y0, level), (x1, y1, level), (x0, y1, level), (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
                F += [tuple(n + i for i in f) for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]]
        name = "cliffedge_%d_%d.obj" % (room, k)
        if not dry:
          with open(os.path.join(ROOT, "landstalker", "data", "proxies", name), "w") as f:
            f.write("# room %d CLASS B cliff EDGE piece %d: walkway cells %d..%d x %d..%d as blocks from the river level %d up to their walkway height "
                    "(remake/recipes/proxy_cliff_rooms.py). GAME coordinates x east, y south, z up.\n" % (room, k, r[0], r[2], r[1], r[3], level))
            for v in V: f.write("v %g %g %g\n" % v)
            for q in F: f.write("f " + " ".join(str(i + 1) for i in q) + "\n")
        ops.append({"op": "mesh", "cells": list(r), "file": "proxies/" + name, "surface": True,
                    "why": "room %d CLASS B cliff EDGE: the walkway cells along the cliff as real blocks from the river level %d up to their walkway height (the cliff = their own "
                           "vertical faces, following the walkway edge, user 2026-11-27; as a model its corners have no height-field seam); remake/recipes/proxy_cliff_rooms.py" % (room, level)})
    print("proxy_cliff_rooms %d: level %d, region %d cells, water %d, ROCK %d (should be 0: lower the level), edge cells %d, %d ops"
          % (room, level, len(reg), len(water), len(rock), len(edge), len(ops)), file=sys.stderr)
    return ops, rock

def notch_ops(room, hm, low, zlevel, dry, tag):
    """2026-11-28 (505: the sword glow lit the 1-cell +x faces of a diagonal staircase edge as hard vertical stripes, LESSONS 9 'jagged cell front of a diagonal face'):
    a zone cell whose -x AND -y neighbours are edge cells is a NOTCH of a diagonal cliff edge; a triangular prism fills its back half, so the cliff below the diagonal
    is one plane facing (+1, +1) instead of a saw-tooth of +x / +y faces. One small mesh op per notch (an outdoor surface model owns its op cell)."""
    ops = []
    for (nx, ny), lv in sorted(zlevel.items()):
        a, b = (nx - 1, ny), (nx, ny - 1)
        # both back neighbours stand above the zone floor: edge cells (walkways) or other solid cells outside the zones (470: the blocked tree rim of a
        # stepped plateau front gave the same 1-cell +x stripes)
        solid = lambda c: c in hm and c not in zlevel and (c in low or hm[c][1]) and 16 * hm[c][0] > lv
        if not (solid(a) and solid(b)): continue
        top = min(16 * hm[a][0], 16 * hm[b][0])
        if top <= lv: continue
        X, Y = 16 * nx, 16 * ny
        P = [(X, Y), (X, Y + 16), (X + 16, Y)]
        V = [(x, y, lv) for x, y in P] + [(x, y, top) for x, y in P]
        F = [(0, 2, 1), (3, 4, 5), (1, 2, 5, 4), (0, 1, 4, 3), (2, 0, 3, 5)]
        name = "cliffnotch_%d_%d_%d.obj" % (room, nx, ny)
        if not dry:
            with open(os.path.join(ROOT, "landstalker", "data", "proxies", name), "w") as f:
                f.write("# room %d CLASS B cliff NOTCH (%d, %d): triangular prism %s .. %d behind the diagonal between the edge cells (%d, %d) and (%d, %d) "
                        "(remake/recipes/proxy_cliff_rooms.py). GAME coordinates x east, y south, z up.\n" % (room, nx, ny, tag, top, a[0], a[1], b[0], b[1]))
                for v in V: f.write("v %g %g %g\n" % v)
                for q in F: f.write("f " + " ".join(str(i + 1) for i in q) + "\n")
        ops.append({"op": "mesh", "cells": [nx, ny, nx, ny], "file": "proxies/" + name, "surface": True,
                    "why": "room %d CLASS B cliff NOTCH: the back half of the cell between two edge cells of a diagonal cliff edge, so the cliff below it is one diagonal plane "
                           "(no saw-tooth of 1-cell faces = no hard light stripes); remake/recipes/proxy_cliff_rooms.py" % room})
    return ops

def edge_obj(room, k, r, hm, low, tag, dry):
    """one mesh per rectangle of edge cells: each cell a block from low(cell) up to its walkway height. v2 2026-11-28 (505: a bright vertical line in the sword glow
    at the joint of two edge blocks in one wall plane): ONE closed solid per rectangle, no inner faces: a side face between two cells of the rectangle is only
    built where this cell stands higher than its neighbour (the step), from max(low, neighbour top) up"""
    V, F = [], []
    def quad(a, b, c, d): n = len(V); V.extend([a, b, c, d]); F.append((n, n + 1, n + 2, n + 3))
    inr = lambda c: r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3]
    for x in range(r[0], r[2] + 1):
        for y in range(r[1], r[3] + 1):
            z = 16 * hm[(x, y)][0]; lv = low[(x, y)]; x0, y0, x1, y1 = 16 * x, 16 * y, 16 * x + 16, 16 * y + 16
            quad((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))      # top
            quad((x0, y0, lv), (x0, y1, lv), (x1, y1, lv), (x1, y0, lv))  # bottom
            for (nx, ny), pts in (((x + 1, y), ((x1, y0), (x1, y1))), ((x, y + 1), ((x1, y1), (x0, y1))), ((x - 1, y), ((x0, y1), (x0, y0))), ((x, y - 1), ((x0, y0), (x1, y0)))):
                zb = lv
                if inr((nx, ny)):
                    zb = max(lv, 16 * hm[(nx, ny)][0])
                    if zb >= z: continue
                (ax, ay), (bx, by) = pts
                quad((ax, ay, zb), (bx, by, zb), (bx, by, z), (ax, ay, z))
    name = "cliffedge_%d_%d.obj" % (room, k)
    if not dry:
        with open(os.path.join(ROOT, "landstalker", "data", "proxies", name), "w") as f:
            f.write("# room %d CLASS B cliff EDGE piece %d: walkway cells %d..%d x %d..%d as blocks from the %s up to their walkway height "
                    "(remake/recipes/proxy_cliff_rooms.py). GAME coordinates x east, y south, z up.\n" % (room, k, r[0], r[2], r[1], r[3], tag))
            for v in V: f.write("v %g %g %g\n" % v)
            for q in F: f.write("f " + " ".join(str(i + 1) for i in q) + "\n")
    return name

def build_zones(rom, room, zones, show_map=False, dry=False):
    """ZONES mode (2026-11-28, room 475): the void in front of the cliffs is not one river but measured ZONES, each a rectangle of void cells
    at one floor level: 'pit' = a drawn ditch / forest pit between walkways (its floor measured where the drawn face meets the plants / ground),
    'deep' = the cliff runs off the picture (no foot). Every zone becomes ground ops (replace) at its level over the void cells of its rectangle;
    the walkways with a zone cell at +x, +y or +x+y get the edge blocks down to that level (the cliff = their own vertical faces)."""
    hm = PS.heights(rom, room)
    lp = json.load(open(os.path.join(ROOT, "landstalker", "data", "light_proxies.json")))["rooms"].get(str(room), [])
    other = [o["cells"] for o in lp if o["op"] in ("mesh", "ground", "water") and "CLASS B" not in o.get("why", "")]
    skip = lambda c: any(r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3] for r in other)
    level = {}
    for zn in zones:
        x0, y0, x1, y1 = zn["rect"]
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                free = hm.get((x, y)) == (0, True) or ((zn["kind"] == "ledge" or zn.get("outside")) and (x, y) not in hm)   # a ledge may stand outside the game's height map (469: drawn beyond x 28)
                if free and not skip((x, y)) and (x, y) not in level: level[(x, y)] = (zn["level"], zn["kind"])
    walkable = lambda c: c in hm and not hm[c][1]
    low = {}
    for c in hm:
        if not walkable(c): continue
        ls = [level[n][0] for n in ((c[0] + 1, c[1]), (c[0], c[1] + 1), (c[0] + 1, c[1] + 1)) if n in level]
        if ls and min(ls) < 16 * hm[c][0]: low[c] = min(ls)
    if show_map:
        xs = [c[0] for c in level] + [c[0] for c in low]; ys = [c[1] for c in level] + [c[1] for c in low]
        for y in range(min(ys) - 1, max(ys) + 2):
            print("%2d " % y + "".join({"pit": "p", "deep": "d", "ledge": "L"}[level[(x, y)][1]] if (x, y) in level else "E" if (x, y) in low else
                  ("." if (x, y) not in hm else "#" if hm[(x, y)][1] else "%X" % min(hm[(x, y)][0], 15)) for x in range(min(xs) - 1, max(xs) + 2)), file=sys.stderr)
    ops = []
    for zn in zones:
        cells = {c for c, (lv, kd) in level.items() if lv == zn["level"] and kd == zn["kind"] and zn["rect"][0] <= c[0] <= zn["rect"][2] and zn["rect"][1] <= c[1] <= zn["rect"][3]}
        for r in rects(cells):
            ops.append({"op": "ground", "cells": list(r) + [zn["level"]], "replace": True,
                        "why": "room %d CLASS B %s (2026-11-28): %s; the void in front of the walkways = floor at %d so the walkway's own vertical face reaches down to it "
                               "(the water rule had painted it 8 below the walkway = the drawn cliff read as a gentle floor); remake/recipes/proxy_cliff_rooms.py zones"
                               % (room, {"pit": "DITCH / PIT", "deep": "CLIFF INTO THE DEEP", "ledge": "LEDGE"}[zn["kind"]], zn["note"], zn["level"])})
    groups = {}
    for c, lv in low.items(): groups.setdefault(lv, set()).add(c)
    k = 0
    for lv in sorted(groups):
        for r in rects(groups[lv]):
            name = edge_obj(room, k, r, hm, low, "zone floor %d" % lv, dry); k += 1
            ops.append({"op": "mesh", "cells": list(r), "file": "proxies/" + name, "surface": True,
                        "why": "room %d CLASS B cliff EDGE: the walkway cells along the cliff as real blocks from the zone floor %d up to their walkway height (the cliff = their own "
                               "vertical faces, following the walkway edge, user 2026-11-27; as a model its corners have no height-field seam); remake/recipes/proxy_cliff_rooms.py" % (room, lv)})
    ops += notch_ops(room, hm, low, {c: lv for c, (lv, kd) in level.items()}, dry, "zone floor")
    print("proxy_cliff_rooms %d zones: %d zone cells, %d edge cells, %d ops (%d meshes)" % (room, len(level), len(low), len(ops), sum(1 for o in ops if o["op"] == "mesh")), file=sys.stderr)
    return ops

if __name__ == "__main__":
    a = sys.argv[1:]; rom = open(a[0], "rb").read(); room = int(a[1])
    if "zones" in SPECS.get(room, {}) and "--level" not in a:
        print(json.dumps(build_zones(rom, room, SPECS[room]["zones"], "--map" in a, "--dry" in a))); sys.exit(0)
    level = int(a[a.index("--level") + 1]) if "--level" in a else SPECS.get(room, {}).get("level", 0)
    ops, rock = build(rom, room, level, "--map" in a, "--dry" in a, "--deep" in a or SPECS.get(room, {}).get("deep", False), SPECS.get(room, {}).get("bulge"))
    print(json.dumps(ops))
