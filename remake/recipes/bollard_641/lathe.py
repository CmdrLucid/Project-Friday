#!/usr/bin/env python3
"""lathe.py OUT.obj PARAMS.json : a body of revolution (here the stone MOORING POST of the Mercator docks, rooms 641 / 642 / 644) as a stack of horizontal rings,
one per height knot [z, c, r] = height above its foot, offset c along the PICTURE's horizontal direction (world (1, -1) / sqrt 2: U grows by c * sqrt 2)
and radius r; between the knots linear, a ring every unit, 32 segments (smooth in the light). The rings are fitted so that the union of their discs fills
the drawn silhouette and never leaves it (fit tool local: ~/Project-Friday-Test/lktest/statue/fit_rings.py). PARAMS: axis [x, y], ground (foot z), rings.
Mooring post: offsets c = 0 (a true lathe), radius profile fitted smooth (2nd-difference penalty) to the drawn silhouette, never outside."""
import json, math, sys
P = json.load(open(sys.argv[2])); AX, AY = P["axis"]; G = P["ground"]; RG = sorted(P["rings"])
SQ2 = math.sqrt(2.0); SEG = 32
def ip(z, k):
    if z <= RG[0][0]: return RG[0][k]
    for a, b in zip(RG, RG[1:]):
        if z <= b[0]: t = (z - a[0]) / (b[0] - a[0]); return a[k] + (b[k] - a[k]) * t
    return RG[-1][k]
W = lambda s, f, z: (AX + (s + f) / SQ2, AY + (f - s) / SQ2, G + z)
V, F = [], []; ztop = RG[-1][0]; rings = []
zs = [i * 1.0 for i in range(int(ztop))] + [ztop]
for z in zs:
    c, r = ip(z, 1), max(0.05, ip(z, 2)); o = len(V)
    V.extend(W(c + r * math.cos(2 * math.pi * j / SEG), r * math.sin(2 * math.pi * j / SEG), z) for j in range(SEG)); rings.append(o)
for a, b in zip(rings, rings[1:]):
    for j in range(SEG): F.append((a + j, a + (j + 1) % SEG, b + (j + 1) % SEG, b + j))
V.append(W(ip(0, 1), 0, 0)); bot = len(V) - 1; V.append(W(ip(ztop, 1), 0, ztop)); top = len(V) - 1
for j in range(SEG): F.append((rings[0] + (j + 1) % SEG, rings[0] + j, bot)); F.append((rings[-1] + j, rings[-1] + (j + 1) % SEG, top))
with open(sys.argv[1], "w") as f:
    f.write("# %s (remake/recipes/bollard_641/lathe.py), game coordinates\n" % P.get("name", "statue"))
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
