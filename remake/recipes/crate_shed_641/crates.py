#!/usr/bin/env python3
"""crates.py OUT.obj PARAMS.json : wooden CRATES of the Mercator docks (rooms 641 / 642 / 644) as OUR OWN 3D model (2026-11-21). One crate = a box of
side `s` (one cell, 16) with a raised FRAME on every face (border strips `fw` wide, `fd` proud) and a middle board, so the light sees real relief
(>= 1 unit, MODELING_LESSONS). PARAMS: {"ground": 16, "s": 16, "fw": 2.0, "fd": 1.0, "stacks": [[cell x, cell y, crates], ...]}: a stack of `crates`
crates on the ground of that cell (the collision height minus the ground, 16 per crate). Pure Python, no ROM data (cells and counts are our reading)."""
import json, sys
P = json.load(open(sys.argv[2])); G = P["ground"]; S = P.get("s", 16.0); FW = P.get("fw", 2.0); FD = P.get("fd", 1.0); IN = P.get("inset", 0.4)
V, F = [], []
def box(x0, y0, z0, x1, y1, z1):
    o = len(V); V.extend([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
    F.extend([(o, o + 3, o + 2, o + 1), (o + 4, o + 5, o + 6, o + 7), (o, o + 1, o + 5, o + 4), (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7)])
def cpost(x0, y0, z0, x1, y1, z1, c):
    """an upright post with all four vertical edges chamfered by c (>= 1 unit: smaller bevels gave dotted light lines, HANDOFF 0a413)"""
    pts = [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]; o = len(V)
    V.extend([(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]); n = 8
    for i in range(n): F.append((o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i))
    F.append(tuple(o + i for i in range(n - 1, -1, -1))); F.append(tuple(o + n + i for i in range(n)))
def crate(x0, y0, z0):
    """core box inset by fd, plus the frame: 12 edge bars (fw x fw) along the box edges and a middle board band around the sides"""
    x1, y1, z1 = x0 + S, y0 + S, z0 + S
    box(x0 + FD + IN, y0 + FD + IN, z0, x1 - FD - IN, y1 - FD - IN, z1 - FD)   # core (the boards, sunk by fd)
    a, b = IN, FW + IN
    for (xa, xb) in ((x0 + a, x0 + b), (x1 - b, x1 - a)):   # vertical corner posts
        for (ya, yb) in ((y0 + a, y0 + b), (y1 - b, y1 - a)): cpost(xa, ya, z0, xb, yb, z1, P.get("post_chamfer", 1.0))   # chamfered corner posts
    for (za, zb) in ((z0, z0 + FW), (z1 - FW, z1)):   # horizontal rails at the bottom and the top, all four sides
        box(x0 + a, y0 + a, za, x1 - a, y0 + b, zb); box(x0 + a, y1 - b, za, x1 - a, y1 - a, zb)
        box(x0 + a, y0 + a, za, x0 + b, y1 - a, zb); box(x1 - b, y0 + a, za, x1 - a, y1 - a, zb)
    zm = z0 + S / 2   # middle board band
    box(x0 + a, y0 + a, zm - FW / 2, x1 - a, y1 - a, zm + FW / 2) if P.get("band", True) else None
for cx, cy, n in P["stacks"]:
    for k in range(int(n)): crate(16 * cx, 16 * cy, G + 16 * k)
R = P.get("roof")
if R:   # gable THATCH ROOF along x over the crate wall: ends x0..x1, eaves at y0 / y1 (z eave), ridge at the middle (z ridge), slab thickness th,
    # crossed sticks over the ridge every `stick_step` (pairs of thin bars, 'X' seen from the end)
    x0, x1, y0, y1, ze, zr, th = R["x0"], R["x1"], R["y0"], R["y1"], R["eave"], R["ridge"], R.get("th", 2.5); ym = (y0 + y1) / 2
    hl, hr = R.get("hip_l", R.get("hip", 0.0)), R.get("hip_r", R.get("hip", 0.0))   # HIPPED ends: the ridge runs from x0 + hip_l to x1 - hip_r (read on the drawing: 6.5 / 11.5)
    hp = (hl + hr) / 2
    o = len(V); V.extend([(x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze), (x0 + hl, ym, zr), (x1 - hr, ym, zr)])
    F.extend([(o, o + 3, o + 2, o + 1), (o, o + 1, o + 5, o + 4), (o + 2, o + 3, o + 4, o + 5), (o + 3, o, o + 4), (o + 1, o + 2, o + 5)])
    box(x0, y0, ze - th, x1, y1, ze)   # the thatch layer's own thickness at the eave
    st = R.get("stick_step", 0)
    if st:
        L, w = R.get("stick_len", 5.0), R.get("stick_w", 0.9); x = x0 + hl + st / 2
        while x < x1 - hr:
            for sgn in (-1, 1):   # two bars crossing over the ridge, each leaning out over one roof side
                a = (x - w, ym - sgn * L * 0.3, zr - 0.5); b = (x + w, ym + sgn * L, zr + L * 0.55)
                n = 6; o = len(V)
                for t in (0.0, 1.0):
                    px, py, pz = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t
                    V.extend([(px - w, py, pz - w), (px + w, py, pz - w), (px + w, py, pz + w), (px - w, py, pz + w)])
                F.extend([(o, o + 1, o + 5, o + 4), (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7), (o, o + 3, o + 2, o + 1), (o + 4, o + 5, o + 6, o + 7)])
            x += st
with open(sys.argv[1], "w") as f:
    f.write("# crates of the Mercator docks (remake/recipes/crate_shed_641/crates.py), game coordinates\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
