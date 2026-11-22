#!/usr/bin/env python3
"""stone_cube.py OUT.obj [params.json] : the small weathered STONE BLOCK of room 486 (four pixel-equal copies on isolated walkable 1 step cells $0100:
(49,35) (57,35) (49,55) (57,55), ground 0; user 2026-11-20 leftover list group (4): 'kleine Steinwuerfel 486'; the automatic lathe 37 high was wrong)
as OUR OWN 3D model: a block of side ~16 and height ~16 with rounded vertical edges (corner radius rc) and a chamfered / rounded top edge (bevel),
read on the 1 px grid (reference cell (49,55): centre x 792 y 888 = picture U 1088 V 840). Rounded parts 6 segments per corner quarter (smooth in the
light: < 35 deg). Origin = centre on the ground."""
import json, math, sys
P = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
g = lambda k, d: P.get(k, d)
A, H, RC, BV = g("a", 8.0), g("h", 15.5), g("rc", 2.0), g("bevel", 1.6)
NQ = 6; V, F = [], []
def ring(a, rc, z):
    pts = []
    for q, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        cx, cy = sx * (a - rc), sy * (a - rc)
        for i in range(NQ + 1):
            t = (q + i / NQ) * math.pi / 2; pts.append((cx + rc * math.cos(t), cy + rc * math.sin(t), z))
    return pts
levels = [(0.0, 0.0)] + [(H - BV + BV * math.sin(math.pi / 2 * k / 4), BV * (1 - math.cos(math.pi / 2 * k / 4))) for k in range(5)]   # (z, inset)
rings = [ring(A - ins, max(0.3, RC - ins * 0.3), z) for z, ins in levels]; n = len(rings[0])
for r in rings: V.extend(r)
for j in range(len(rings) - 1):
    for i in range(n): a = j * n + i; b = j * n + (i + 1) % n; F.append((a, b, b + n, a + n))
V.append((0.0, 0.0, 0.0)); c0 = len(V) - 1; V.append((0.0, 0.0, H)); c1 = len(V) - 1; top = (len(rings) - 1) * n
for i in range(n): F.append((c0, (i + 1) % n, i)); F.append((c1, top + i, top + (i + 1) % n))
with open(sys.argv[1], "w") as f:
    f.write("# stone block of room 486 (remake/recipes/stone_cube_486/stone_cube.py), origin = centre on the ground\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
