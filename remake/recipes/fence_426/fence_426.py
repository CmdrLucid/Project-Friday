#!/usr/bin/env python3
"""fence_426.py [OUT.obj] : the RUSTIC LOG FENCE beside the waterfall in room 426 (light shape, near-final 3D: round tapered posts with a rounded,
slightly slanted cut top, round rail logs with rounded ends) -> landstalker/data/proxies/fence_426.obj (our own geometry, committed).

Read on the 1 px grid of the room picture (U = x - y + 1184, V = (x + y) / 2 - z) on 2026-11-24:
  * collision: blocked height 48 cells (27,34) (28,34) (27,35) (28,35) (28,36) (28,37) (27,38) (28,38) on ground 0 (the walk way next to it is 0);
  * posts: axis column U and the top pixel V of each drawn post; the visible feet (D 518, C 534, B 540, E 494, F ~504) put the side posts on the
    line x = 464 (the cells' +x edge: B C D F), A on the front line, E on the back line (x 444, the middle of cells 27..28) -> top z = (x + y) / 2 - V;
  * rails: every drawn rail log as its centre line (two picture points) lifted onto the vertical plane of its fence run (front y 621, side x 464,
    back y 546): rustic = rails slope and some end in the air or pass over a short post (B), exactly as drawn.
Light variant = AS DRAWN (memory 'remake vs light variant'). Pure Python, no ROM.  Run: python3 remake/recipes/fence_426/fence_426.py"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "landstalker", "data", "proxies", "fence_426.obj")
R_POST, R_RAIL, NU = 2.1, 2.0, 12        # drawn post 6 px wide in U (cylinder: 2 r sqrt 2), rail ~4 px high
GROUND = 0.0
# name: (x, y, top V)  (axis column U = x - y + 1184 was measured; x / y from the run line)
POSTS = {"A": (440.5, 620.5, 479.0), "B": (464.0, 620.5, 504.5), "C": (464.0, 605.0, 472.5),
         "D": (464.0, 572.5, 464.0), "E": (444.0, 544.0, 456.0), "F": (464.0, 547.5, 456.0)}
# rails: (plane, (U1, V1), (U2, V2)); plane ('y', Y) = front / back run, ('x', X) = side run
FRONT, SIDE, BACK = ("y", 621.0), ("x", 464.0), ("y", 546.0)
RAILS = [
    (FRONT, (1006.4, 489.0), (1024.0, 500.7)),   # upper A -> B
    (FRONT, (992.0, 512.0), (1024.0, 527.5)),    # lower, sticks out left of A
    (FRONT, (1016.0, 513.0), (1024.5, 518.0)),   # short middle piece in front of B
    (SIDE, (1024.0, 490.0), (1040.0, 481.6)),    # upper B .. C, passes over the short post B
    (SIDE, (1032.0, 512.5), (1040.0, 508.0)),    # middle B -> C
    (SIDE, (1046.0, 502.0), (1055.0, 497.0)),    # stub right of C
    (SIDE, (1056.5, 484.5), (1073.0, 477.5)),    # upper C .. D (its C end is free)
    (SIDE, (1056.0, 511.0), (1073.0, 503.0)),    # lower C .. D
    (SIDE, (1046.0, 517.0), (1063.0, 512.5)),    # lowest from C
    (SIDE, (1079.0, 481.0), (1103.0, 486.0)),    # D -> F, sloping down towards F
    (SIDE, (1081.0, 502.0), (1095.0, 497.0)),    # D -> F middle
    (SIDE, (1080.0, 508.0), (1095.0, 504.0)),    # D -> F low
    (BACK, (1089.0, 465.0), (1097.0, 469.5)),    # back run E -> F
    (BACK, (1104.0, 464.0), (1112.0, 471.0)),    # stub beyond F
]
V, F = [], []
def lift(plane, U, Vp):
    k, c = plane
    if k == "x": x = c; y = x - (U - 1184.0)
    else: y = c; x = U - 1184.0 + y
    return (x, y, (x + y) / 2.0 - Vp)
def frame(d):
    d = [t / math.sqrt(sum(s * s for s in d)) for t in d]
    a = (0, 0, 1) if abs(d[2]) < 0.9 else (1, 0, 0)
    u = (d[1] * a[2] - d[2] * a[1], d[2] * a[0] - d[0] * a[2], d[0] * a[1] - d[1] * a[0]); n = math.sqrt(sum(s * s for s in u)); u = [s / n for s in u]
    w = (d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0])
    return d, u, w
def tube(p0, p1, r0, r1, cap0, cap1):
    """round log p0 -> p1 (radius r0 -> r1); cap = 'dome' (rounded end, 3 rings) or 'slant' (cut top tilted 15 deg) or None (flat)"""
    d, u, w = frame([b - a for a, b in zip(p0, p1)])
    rings = []
    def ring(c, r, tilt=0.0):
        o = len(V)
        for i in range(NU):
            t = 2 * math.pi * i / NU; cs, sn = math.cos(t), math.sin(t)
            off = tilt * r * cs
            V.append(tuple(c[j] + r * (cs * u[j] + sn * w[j]) + off * d[j] for j in range(3)))
        return o
    def dome(c, r, sgn):
        out = []
        for k, (f, s) in enumerate(((0.0, 1.0), (0.45, 0.89), (0.8, 0.6))):
            out.append(ring([c[j] + sgn * f * r * d[j] for j in range(3)], r * s))
        V.append(tuple(c[j] + sgn * r * d[j] for j in range(3))); return out, len(V) - 1
    if cap0 == "dome": rs0, tip0 = dome(p0, r0, -1); rs0 = rs0[::-1]
    else: rs0, tip0 = [ring(p0, r0)], None
    if cap1 == "dome": rs1, tip1 = dome(p1, r1, 1)
    elif cap1 == "slant": rs1, tip1 = [ring(p1, r1, math.tan(math.radians(15)))], None
    else: rs1, tip1 = [ring(p1, r1)], None
    rings = rs0 + rs1
    for a, b in zip(rings, rings[1:]):
        for i in range(NU): j = (i + 1) % NU; F.append((a + i, a + j, b + j, b + i))
    if tip0 is None: F.append(tuple(rings[0] + i for i in reversed(range(NU))))
    else: F.extend((tip0, rings[0] + (i + 1) % NU, rings[0] + i) for i in range(NU))
    if tip1 is None: F.append(tuple(rings[-1] + i for i in range(NU)))
    else: F.extend((tip1, rings[-1] + i, rings[-1] + (i + 1) % NU) for i in range(NU))
tops = {}
for n, (x, y, vt) in POSTS.items():
    zt = (x + y) / 2.0 - vt; tops[n] = zt
    tube((x, y, GROUND), (x, y, zt - 0.8), R_POST * 1.08, R_POST * 0.95, None, "dome")      # slight taper, rounded worn top
# a rail end read within SNAP units (along its run) of a post on the same run is hidden behind that post in the drawing: continue the drawn
# centre line to the post axis (else the clay preview showed rails floating between the posts); clearly drawn free ends further away stay free
SNAP = 7.5; snapped = 0
def on_run(plane):
    k, c = plane; i = 0 if k == "x" else 1
    return [(p[1 - i], n) for n, p in POSTS.items() if abs(p[i] - c) <= 3.0]       # (run coordinate, name) of the posts on this run line
for plane, a, b in RAILS:
    p0, p1 = lift(plane, *a), lift(plane, *b); i = 1 if plane[0] == "x" else 0     # run coordinate = y on a side run, x on a front / back run
    for end in (0, 1):
        q = p0 if end == 0 else p1
        best = min(on_run(plane), key=lambda t: abs(t[0] - q[i]))
        if 0.3 < abs(best[0] - q[i]) <= SNAP:
            t = (best[0] - p0[i]) / (p1[i] - p0[i]); q = tuple(p0[j] + t * (p1[j] - p0[j]) for j in range(3)); snapped += 1
            if end == 0: p0n = q
            else: p1n = q
        elif end == 0: p0n = p0
        else: p1n = p1
    tube(p0n, p1n, R_RAIL, R_RAIL * 0.9, "dome", "dome")
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
with open(OUT, "w") as f:
    f.write("# light proxy: rustic log fence by the waterfall, room 426 (remake/recipes/fence_426/fence_426.py). GAME coordinates x east, y south, z up.\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
xs = [v[0] for v in V]; ys = [v[1] for v in V]; zs = [v[2] for v in V]
print("fence_426: %d posts (tops %s), %d rails (%d ends continued to a post), %d vertices, %d faces -> %s; x %.0f..%.0f y %.0f..%.0f z %.0f..%.0f" % (
    len(POSTS), " ".join("%s %.0f" % (n, t) for n, t in tops.items()), len(RAILS), snapped, len(V), len(F), OUT, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
