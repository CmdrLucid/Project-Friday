#!/usr/bin/env python3
"""NEAR-FINAL BALUSTRADE (castle stairwells; references room 95 (stairwell rail, rows 19..27), 89 (x 28 rows 19..26), 62 / 59..61 (hall stairs)).
Recipe only (no ROM data).  Measured on the drawing (remake/tools/rom_picture.py + proxy_overlay.py, 6x / 10x, 2026-11-13):
  * turned balusters every 8 units: ribbed lower part (3 rings), a vase bulb above, a collar under the handrail; radius 1.2 .. 1.9 (the drawn
    baluster is 4 px wide = 2 r sqrt 2 in U), height from the plinth top to the handrail bottom;
  * a low plinth (bottom rail) on the floor, 1.5 high, 5 deep, edges rounded;
  * the handrail: a rounded bar 3 high, 5 deep (light grey top band in the drawing), edges r 1.2;
  * posts (89 / 62): square post with a turned ball cap.
  * the stairwell's side wall under the rail (wall = its bottom z): the light needs it, the op 'floor' of the rail cells is the stair / well height
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
ROOMS = {   # path = centre line of the rail (axis-parallel polyline, corners MITRED as drawn: the handrail / plinth meet in a clean V, no baluster
           # on the corner itself, the nearest ones ~5.5 units either side (16x zoom of 95, 2026-11-13)); posts = (x, y, top): the rail stops at their faces
    95: dict(floor=32, top=44, depth=5.0, wall=0, path=[(317.5, 304.0), (317.5, 445.5), (240.0, 445.5)], posts=[]),
    89: dict(floor=16, top=32, depth=4.5, wall=0, path=[(448.0, 427.0), (448.0, 304.0), (459.0, 304.0)],
             posts=[(448.0, 429.5, 34.0), (448.0, 302.5, 33.0), (462.0, 305.0, 37.0)]),
}
PL_H, RAIL_H, SPACE = 1.5, 3.0, 8.0
PHASE = 0.0   # baluster centres at lo + PHASE + 8 i (measured: the drawn balusters sit on the 8 grid)

def band(path, d):
    """outline polygon of a band of width d around an axis-parallel open polyline (mitred corners, square ends)"""
    import math
    def nrm(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]; l = math.hypot(dx, dy); return (-dy / l, dx / l)
    L, R = [], []
    n = len(path)
    for i, p in enumerate(path):
        ns = []
        if i > 0: ns.append(nrm(path[i - 1], p))
        if i < n - 1: ns.append(nrm(p, path[i + 1]))
        if len(ns) == 1: off = ns[0]
        else: off = (ns[0][0] + ns[1][0], ns[0][1] + ns[1][1])        # 90 degree corner: the mitre point (both offsets add up)
        L.append((p[0] + off[0] * d / 2, p[1] + off[1] * d / 2)); R.append((p[0] - off[0] * d / 2, p[1] - off[1] * d / 2))
    return L + R[::-1]

def split(path, posts, gap):
    """cut the path where a post stands (the rail ends gap from the post centre); returns sub-paths"""
    import math
    pts = [path[0]]; out = []
    for a, b in zip(path, path[1:]):
        cuts = []
        for x, y, _ in posts:
            if abs(a[0] - b[0]) < 1e-6 and abs(x - a[0]) < 3 and min(a[1], b[1]) - 3 <= y <= max(a[1], b[1]) + 3: cuts.append(abs(y - a[1]))
            if abs(a[1] - b[1]) < 1e-6 and abs(y - a[1]) < 3 and min(a[0], b[0]) - 3 <= x <= max(a[0], b[0]) + 3: cuts.append(abs(x - a[0]))
        L = math.hypot(b[0] - a[0], b[1] - a[1]); u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        for t in sorted(cuts):
            if t - gap > 1e-3: pts.append((a[0] + u[0] * (t - gap), a[1] + u[1] * (t - gap)))
            if len(pts) > 1: out.append(pts)
            pts = [(a[0] + u[0] * min(L, t + gap), a[1] + u[1] * min(L, t + gap))]
        pts.append(b)
    if len(pts) > 1 and math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) > 1e-3: out.append(pts)
    return [p for p in out if sum(math.hypot(q[0] - r[0], q[1] - r[1]) for q, r in zip(p, p[1:])) > 0.5]

def sweep(path, d, z0, z1, r):
    """a rounded bar of width d from z0 to z1 along the path (mitred corners, ends rounded by r in plan): furniture.sweep_poly over the band outline"""
    poly = band(path, d)
    prof = [(r, z0), (r * 0.3, z0 + r * 0.3), (0.0, z0 + r), (0.0, z1 - r), (r * 0.3, z1 - r * 0.3), (r, z1)]
    k = 1 if len(path) > 2 else 0
    star = path[k] if len(path) > 2 else ((path[0][0] + path[-1][0]) / 2, (path[0][1] + path[-1][1]) / 2)
    return F.sweep_poly(poly, min(r, d / 2 - 0.05), prof, star, nc=4)

def build(room):
    import math
    P = ROOMS[room]; fl, top, d = P["floor"], P["top"], P["depth"]; solid, rail = [], []
    zb0, zb1 = fl + PL_H, top - RAIL_H                         # baluster span
    if P.get("wall") is not None and P["wall"] < fl:   # the stairwell's side wall under the rail (the room floor's edge): from the well bottom up to the floor
        solid.append(sweep(P["path"], d, P["wall"], fl, 0.3))
    for sub in split(P["path"], P["posts"], 2.2):
        solid.append(sweep(sub, d, fl, fl + PL_H, 0.6))
        rail.append(sweep(sub, d, top - RAIL_H, top, 1.2))
    s = (zb1 - zb0) / BAL_H
    for a, b in zip(P["path"], P["path"][1:]):                 # balusters on the 8 grid of each straight run (measured phase), not on corners / posts
        L = math.hypot(b[0] - a[0], b[1] - a[1]); u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        axis_y = abs(u[0]) < 0.5; c0 = a[1] if axis_y else a[0]; sg = 1 if (u[1] if axis_y else u[0]) > 0 else -1
        for i in range(-200, 200):
            g = PHASE + SPACE * i                              # world grid coordinate along the run
            t = (g - c0) * sg
            if t < 3.0 or t > L - 3.0: continue
            bx, by = (a[0], g) if axis_y else (g, a[1])
            if any(math.hypot(bx - x, by - y) < 4.5 for x, y, _ in P["posts"]): continue
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
