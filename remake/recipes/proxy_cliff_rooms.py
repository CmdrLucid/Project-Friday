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
         601: dict(level=0, also=[602, 603], note="Gumi village hill in the river (601..603 = one map): the drawn bank lies on the walkway edges at 0 (foot measured 2)")}

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

def build(rom, room, level, show_map=False, dry=False):
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
    reg = water | rock
    edge = {c for c in hm if walkable(c) and any((c[0] + dx, c[1] + dy) in water for dx, dy in ((1, 0), (0, 1), (1, 1)))}
    if show_map:
        xs = [c[0] for c in reg]; ys = [c[1] for c in reg]
        for y in range(min(ys) - 1, max(ys) + 2):
            print("%2d " % y + "".join("R" if (x, y) in rock else "w" if (x, y) in water else "E" if (x, y) in edge else
                  ("." if (x, y) not in hm else "#" if hm[(x, y)][1] else "%X" % min(hm[(x, y)][0], 15)) for x in range(min(xs) - 3, max(xs) + 2)), file=sys.stderr)
    ops = [{"op": "water", "cells": list(r) + [level], "why": "room %d CLASS B CLIFF below the walkway (2026-11-27): the void in front of the walkway down to the drawn river bank = water at %d; "
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

if __name__ == "__main__":
    a = sys.argv[1:]; rom = open(a[0], "rb").read(); room = int(a[1])
    level = int(a[a.index("--level") + 1]) if "--level" in a else SPECS.get(room, {}).get("level", 0)
    ops, rock = build(rom, room, level, "--map" in a, "--dry" in a)
    print(json.dumps(ops))
