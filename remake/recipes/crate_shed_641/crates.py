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
def cpost(x0, y0, z0, x1, y1, z1, c, inner=None):
    """an upright post; only its INNER vertical edge (towards the crate's middle, `inner` = (sx, sy) signs) is chamfered by c, so the crate's outer
    corner stays one straight line in the silhouette (user 2026-11-21: 'das sind alles gerade Linien'; chamfers >= 1 unit, HANDOFF 0a413)"""
    sx, sy = inner if inner else (1, 1)
    cx = x1 if sx > 0 else x0; cy = y1 if sy > 0 else y0   # the inner corner
    pts = []
    for (px, py) in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
        if (px, py) == (cx, cy):   # replace the inner corner by two points
            a = (px - sx * c, py); b_ = (px, py - sy * c)
            nxt = {(x0, y0): (x1, y0), (x1, y0): (x1, y1), (x1, y1): (x0, y1), (x0, y1): (x0, y0)}[(px, py)]
            pts += [b_, a] if nxt[0] == px else [a, b_]
        else: pts.append((px, py))
    o = len(V); n = len(pts)
    V.extend([(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts])
    for i in range(n): F.append((o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i))
    F.append(tuple(o + i for i in range(n - 1, -1, -1))); F.append(tuple(o + n + i for i in range(n)))
def crate(x0, y0, z0):
    """core box inset by fd, plus the frame: 12 edge bars (fw x fw) along the box edges and a middle board band around the sides"""
    x1, y1, z1 = x0 + S, y0 + S, z0 + S
    box(x0 + FD + IN, y0 + FD + IN, z0, x1 - FD - IN, y1 - FD - IN, z1 - FD)   # core (the boards, sunk by fd)
    a, b = IN, FW + IN
    for (xa, xb) in ((x0 + a, x0 + b), (x1 - b, x1 - a)):   # vertical corner posts
        for (ya, yb) in ((y0 + a, y0 + b), (y1 - b, y1 - a)): cpost(xa, ya, z0, xb, yb, z1, P.get("post_chamfer", 1.0), (1 if xa < x0 + S / 2 else -1, 1 if ya < y0 + S / 2 else -1))   # corner posts, inner edge chamfered
    for (za, zb) in ((z0, z0 + FW), (z1 - FW, z1)):   # horizontal rails at the bottom and the top, all four sides
        box(x0 + a, y0 + a, za, x1 - a, y0 + b, zb); box(x0 + a, y1 - b, za, x1 - a, y1 - a, zb)
        box(x0 + a, y0 + a, za, x0 + b, y1 - a, zb); box(x1 - b, y0 + a, za, x1 - a, y1 - a, zb)
    zm = z0 + S / 2   # middle board band
    box(x0 + a, y0 + a, zm - FW / 2, x1 - a, y1 - a, zm + FW / 2) if P.get("band", True) else None
for cx, cy, n in P["stacks"]:
    for k in range(int(n)): crate(16 * cx, 16 * cy, G + 16 * k)
NC = len(V)   # vertices so far = crates (clipped to the roof below)
def roof_z(R, x, y):
    """height of the (convex, hipped) roof surface at x, y = the lowest of its four face planes"""
    x0, x1, y0, y1, ze, zr = R["x0"], R["x1"], R["y0"], R["y1"], R["eave"], R["ridge"]; ym = R.get("ridge_y", (y0 + y1) / 2)
    hl, hr = R.get("hip_l", 0.0), R.get("hip_r", 0.0)
    zb = R.get("eave_back", ze)
    zs = [zb + (zr - zb) / (ym - y0) * (y - y0), ze + (zr - ze) / (y1 - ym) * (y1 - y)]
    if hl > 0: zs.append(ze + (zr - ze) / hl * (x - x0))
    if hr > 0: zs.append(ze + (zr - ze) / hr * (x1 - x))
    return min(zs)
if P.get("roof") and P.get("clip_to_roof"):   # the top crate row under the roof ends AT the roof (user 2026-11-21: 'die letzte Reihe oben abschneiden')
    R0 = P["roof"]
    for i in range(NC):
        x, y, z = V[i]
        if R0["y0"] <= y <= R0["y1"] and R0["x0"] - 16 <= x <= R0["x1"] + 0.01: V[i] = (x, y, min(z, roof_z(R0, x, y)))   # crates just beside the roof ends: cut along the end slope continued (user: 'auch abschneiden')
for R in [P.get("roof")] + P.get("roof_caps", []):   # main roof + optional CAPS (a short roof piece resting on higher crates, e.g. the 4 high column x 57)
  if R:   # gable THATCH ROOF along x over the crate wall: ends x0..x1, eaves at y0 / y1 (z eave), ridge at the middle (z ridge), slab thickness th,
    # crossed sticks over the ridge every `stick_step` (pairs of thin bars, 'X' seen from the end)
    x0, x1, y0, y1, ze, zr, th = R["x0"], R["x1"], R["y0"], R["y1"], R["eave"], R["ridge"], R.get("th", 2.5); ym = R.get("ridge_y", (y0 + y1) / 2)   # ridge line (may sit off centre when the back eave ends on the crates)
    hl, hr = R.get("hip_l", R.get("hip", 0.0)), R.get("hip_r", R.get("hip", 0.0))   # HIPPED ends: the ridge runs from x0 + hip_l to x1 - hip_r (read on the drawing: 6.5 / 11.5)
    hp = (hl + hr) / 2
    el = R.get("eave_l", ze)   # the LEFT end's FRONT eave corner sits higher (the thatch flares up at the hip, read on the drawing 2026-11-21: 80)
    er = R.get("eave_r", ze)   # same for the RIGHT end (over the 4 high crate column x 57)
    x1b, erb = R.get("x1_back", x1), R.get("eave_rb", R.get("eave_back", ze))   # BACK-right corner may sit further right and higher (docks shed: on the 4th crate of column 57 at the back, 2026-11-21)
    zb = R.get("eave_back", ze)   # BACK eave height (docks shed: 80 = resting on the back crate row's top edge)
    zbl = R.get("eave_back_l", zb)   # back-LEFT corner (lower, so it stays hidden behind the ridge like in the drawing)
    x0b = R.get("x0_back", x0)   # back-left corner x (with a lower back eave the back corners sit 8 left of the front ones: same picture, iso-parallel end edges)
    FL = R.get("front_left")   # [x, y]: the front-left corner CUT BACK (drawing: the thatch tapers in at the left end); the eave starts at front_left_eave_x
    fx, fy = (FL[0], FL[1]) if FL else (x0, y1)
    o = len(V); V.extend([(x0b, y0, zbl), (x1b, y0, max(erb, zb)), (x1, y1, er), (fx, fy, el), (x0 + hl, ym, zr), (x1 - hr, ym, zr)])
    # SOLID roof body: the underside lies flat at `eave` on the crates (no gap, no separate slab), the raised end corners get thatch walls down to it
    b = len(V); V.extend([(x0b, y0, zbl), (x1b, y0, zb), (x1, y1, ze), (fx, fy, ze)])
    if FL:
        e = len(V); V.extend([(R["front_left_eave_x"], y1, el), (R["front_left_eave_x"], y1, ze)])
        F.extend([(b, b + 3, e + 1, b + 2, b + 1), (o, o + 1, o + 5, o + 4), (o + 2, e, o + 3, o + 4, o + 5), (o + 3, o, o + 4), (o + 1, o + 2, o + 5)])
    else:
        F.extend([(b, b + 3, b + 2, b + 1), (o, o + 1, o + 5, o + 4), (o + 2, o + 3, o + 4, o + 5), (o + 3, o, o + 4), (o + 1, o + 2, o + 5)])
    if el > ze: F.extend([(o + 3, o + 2, b + 2, b + 3), (o, o + 3, b + 3, b)])
    if erb > R.get("eave_back", ze) and er <= ze: F.extend([(b + 1, b + 2, o + 2, o + 1), (o, o + 1, b + 1, b)])   # thatch walls under the raised back-right corner
    if er > ze: F.extend([(b + 1, b + 2, o + 2, o + 1)]) if el > ze else F.extend([(o + 3, o + 2, b + 2, b + 3), (b + 1, b + 2, o + 2, o + 1)])
    if th > 0: box(x0, y0, ze - th, x1, y1, ze)   # optional eave slab (off since 2026-11-21: the user saw it as a lid under the roof; the thatch sits right on the crates)
    st = R.get("stick_step", 0)
    if st:   # crossed short LOGS on the ridge ('X' pairs) like the Massan houses (remake/recipes/massan_house.py: L 8, 40 deg, r 1.5, +-1.2 apart
        # along the ridge); user 2026-11-21: 'dieselben Kreuze wie in Massan oben am Dach', the old thin single bars read as strokes
        import math
        L, ang, r = R.get("stick_len", 8.0), math.radians(R.get("stick_ang", 40.0)), R.get("stick_r", 1.5); dz, dw = L * math.sin(ang), L * math.cos(ang)
        def log(p0, p1, n=8):
            ax = [p1[i] - p0[i] for i in range(3)]; ln = math.sqrt(sum(c * c for c in ax)); ax = [c / ln for c in ax]
            u = [1.0, 0.0, 0.0]   # the logs lie in a y-z plane, so x is perpendicular
            v = [ax[1] * u[2] - ax[2] * u[1], ax[2] * u[0] - ax[0] * u[2], ax[0] * u[1] - ax[1] * u[0]]
            o = len(V)
            for p in (p0, p1):
                for k in range(n):
                    c, s_ = math.cos(2 * math.pi * k / n) * r, math.sin(2 * math.pi * k / n) * r
                    V.append(tuple(p[i] + c * u[i] + s_ * v[i] for i in range(3)))
            for k in range(n): F.append((o + k, o + (k + 1) % n, o + n + (k + 1) % n, o + n + k))
            F.append(tuple(o + k for k in range(n - 1, -1, -1))); F.append(tuple(o + n + k for k in range(n)))
        x = x0 + hl + st / 2
        while x < x1 - hr:
            for sgn in (-1, 1):   # each log rises from one roof side over the ridge to the other side: the pair crosses above the ridge
                log((x + sgn * 1.2, ym - sgn * dw, zr - 3), (x + sgn * 1.2, ym + sgn * dw, zr - 3 + 2 * dz))
            x += st
with open(sys.argv[1], "w") as f:
    f.write("# crates of the Mercator docks (remake/recipes/crate_shed_641/crates.py), game coordinates\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
