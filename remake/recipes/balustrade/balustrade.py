#!/usr/bin/env python3
"""NEAR-FINAL BALUSTRADE (castle stairwells; references room 95 (stairwell rail, rows 19..27), 89 (x 28 rows 19..26), 62 / 59..61 (hall stairs)).
Recipe only (no ROM data).  Measured on the drawing (remake/tools/rom_picture.py + proxy_overlay.py, 6x / 10x, 2026-11-13):
  * turned balusters every 8 units: ribbed lower part (3 rings), a vase bulb above, a collar under the handrail; radius 1.2 .. 1.9 (the drawn
    baluster is 4 px wide = 2 r sqrt 2 in U), height from the plinth top to the handrail bottom;
  * a low plinth (bottom rail) on the floor, 1.5 high, 5 deep, edges rounded;
  * the handrail: a rounded bar 3 high, 5 deep (light grey top band in the drawing), edges r 1.2;
  * posts (89 / 62): square post with a turned ball cap.
Parameters per room in ROOMS below (outer edge line measured with proxy_overlay; rail axes along x or y).
  python3 remake/recipes/balustrade/balustrade.py ROOM OUTDIR   -> OUTDIR/rail_ROOM.obj (plinth, balusters, posts) + OUTDIR/rail_ROOM_rail.obj (handrail: op 'air')
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
import furniture as F

# baluster profile: (height above the plinth top, radius) for a baluster of the standard height 7.5 (scaled to the room's height)
BAL = [(0.0, 1.6), (0.4, 1.6), (0.6, 1.25), (1.1, 1.5), (1.5, 1.25), (2.0, 1.5), (2.4, 1.25), (2.9, 1.5), (3.3, 1.15), (3.7, 1.15),
       (4.1, 1.55), (4.9, 1.85), (5.8, 1.75), (6.5, 1.3), (6.9, 1.2), (7.1, 1.55), (7.5, 1.55)]
BAL_H = 7.5

# per room: floor, handrail top, runs = (axis, fixed coordinate of the rail centre line, from, to) in world units; posts = (x, y, top)
ROOMS = {
    95: dict(floor=32, top=44, depth=5.0, runs=[("y", 317.5, 304.0, 448.0), ("x", 445.5, 240.0, 320.0)], posts=[]),
    89: dict(floor=16, top=32, depth=4.5, runs=[("y", 448.0, 304.0, 427.0), ("x", 304.0, 448.0, 459.0)],
             posts=[(448.0, 429.5, 34.0), (448.0, 302.5, 33.0), (462.0, 305.0, 37.0)]),
}
PL_H, RAIL_H, SPACE = 1.5, 3.0, 8.0
PHASE = 0.0   # baluster centres at lo + PHASE + 8 i (measured: the drawn balusters sit on the 8 grid)

def build(room):
    P = ROOMS[room]; fl, top, d = P["floor"], P["top"], P["depth"]; solid, rail = [], []
    zb0, zb1 = fl + PL_H, top - RAIL_H                         # baluster span
    for axis, c, a0, a1 in P["runs"]:
        lo, hi = min(a0, a1), max(a0, a1)
        if axis == "y":
            solid.append(F.rbox(c - d / 2, c + d / 2, lo, hi, fl, fl + PL_H, 0.6, n=2, flat_bottom=True))
            rail.append(F.rbox(c - d / 2, c + d / 2, lo, hi, top - RAIL_H, top, 1.2, n=3))
        else:
            solid.append(F.rbox(lo, hi, c - d / 2, c + d / 2, fl, fl + PL_H, 0.6, n=2, flat_bottom=True))
            rail.append(F.rbox(lo, hi, c - d / 2, c + d / 2, top - RAIL_H, top, 1.2, n=3))
        n = int((hi - lo - PHASE) / SPACE + 1e-6) + 1
        for i in range(n):
            t = lo + PHASE + i * SPACE
            if t < lo + 1.0 or t > hi - 1.0: continue
            bx, by = (c, t) if axis == "y" else (t, c)
            s = (zb1 - zb0) / BAL_H
            solid.append(F.lathe(bx, by, zb0, 1.0, [(z * s, r) for z, r in BAL], seg=12))
    for x, y, pt in P["posts"]:
        solid.append(F.rbox(x - 2.2, x + 2.2, y - 2.2, y + 2.2, fl, pt - 4.0, 0.5, n=2, flat_bottom=True))
        solid.append(F.lathe(x, y, pt - 4.2, 1.0, [(0.0, 1.6), (0.6, 2.2), (1.6, 2.4), (2.6, 2.1), (3.4, 1.3), (3.8, 0.6), (4.0, 0.0)], seg=16))   # ball cap
    return solid, rail

def write(meshes, path, title):
    vs, fs, b = [], [], 0
    for v, f in meshes:
        vs += v; fs += [tuple(i + b for i in q) for q in f]; b += len(v)
    with open(path, "w") as o:
        o.write("# light proxy: %s (remake/recipes/balustrade/balustrade.py, near-final model). GAME coordinates x east, y south, z up, world units.\n" % title)
        o.write("# our own geometry measured on the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        for v in vs: o.write("v %.3f %.3f %.3f\n" % v)
        for q in fs: o.write("f " + " ".join(str(i + 1) for i in q) + "\n")

if __name__ == "__main__":
    room, out = int(sys.argv[1]), sys.argv[2]
    s, r = build(room)
    write(s, os.path.join(out, "rail_%d.obj" % room), "balustrade (plinth, turned balusters, posts), room %d" % room)
    write(r, os.path.join(out, "rail_%d_rail.obj" % room), "balustrade handrail, room %d" % room)
    print("balustrade: room %d -> %s/rail_%d*.obj" % (room, out, room))
