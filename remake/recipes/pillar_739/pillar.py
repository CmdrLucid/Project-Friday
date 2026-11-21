#!/usr/bin/env python3
"""pillar.py OUT.obj [params.json] : the STONE PILLAR of room 739 (two copies on single blocked cells $43 = top 48, ground 0: cells (24,15) and the
second one; user 2026-11-20 leftover list group (4): 'Saeulen 545 / 739') as OUR OWN 3D model. Read on the 1 px grid (reference cell (24,15), axis
x 392 y 248 = picture U 1328): square plinth (side 13), round base ring, round shaft (radius ~5, slight entasis), neck ring, flaring echinus, square
abacus (side 13) whose top is at ~49.5. Round parts 24 sides (smooth in the light), square parts with sharp edges. Origin = axis on the ground."""
import json, math, sys
P = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
g = lambda k, d: P.get(k, d)
S_PL, H_PL = g("plinth_side", 13.0), g("plinth_h", 5.0)
R_BR, H_BR = g("base_ring_r", 6.4), g("base_ring_h", 3.0)
R_SH0, R_SH1 = g("shaft_r0", 5.2), g("shaft_r1", 4.8)
Z_NK, R_NK, H_NK = g("neck_z", 40.0), g("neck_r", 5.6), g("neck_h", 1.6)
R_EC1, H_EC = g("echinus_r", 6.6), g("echinus_h", 4.0)
S_AB, H_AB = g("abacus_side", 13.0), g("abacus_h", 3.8)
NU = 24; V, F = [], []
def box(x0, y0, z0, x1, y1, z1):
    o = len(V); V.extend([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
    F.extend([(o, o + 3, o + 2, o + 1), (o + 4, o + 5, o + 6, o + 7), (o, o + 1, o + 5, o + 4), (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7)])
def lathe(prof):   # prof = [(z, r), ...] bottom -> top, closed by caps
    o = len(V)
    for z, r in prof:
        for i in range(NU): a = 2 * math.pi * i / NU; V.append((r * math.cos(a), r * math.sin(a), z))
    for j in range(len(prof) - 1):
        for i in range(NU): a = o + j * NU + i; b = o + j * NU + (i + 1) % NU; F.append((a, b, b + NU, a + NU))
    V.append((0, 0, prof[0][0])); c0 = len(V) - 1; V.append((0, 0, prof[-1][0])); c1 = len(V) - 1; n = len(prof)
    for i in range(NU): F.append((c0, o + (i + 1) % NU, o + i)); F.append((c1, o + (n - 1) * NU + i, o + (n - 1) * NU + (i + 1) % NU))
a = S_PL / 2; box(-a, -a, 0, a, a, H_PL)
z = H_PL; zt = Z_NK + H_NK + H_EC; zab = zt; ztop = zab + H_AB
prof = [(z, R_BR), (z + H_BR * 0.5, R_BR + 0.3), (z + H_BR, R_SH0 + 0.4), (z + H_BR + 0.8, R_SH0)]
for k in range(1, 6):   # shaft with a slight entasis
    t = k / 6.0; zz = z + H_BR + 0.8 + (Z_NK - z - H_BR - 0.8) * t; prof.append((zz, R_SH0 + (R_SH1 - R_SH0) * t + 0.25 * math.sin(math.pi * t)))
prof += [(Z_NK, R_SH1), (Z_NK, R_NK), (Z_NK + H_NK, R_NK), (Z_NK + H_NK, R_SH1 - 0.3), (Z_NK + H_NK + H_EC * 0.5, (R_SH1 + R_EC1) / 2 - 0.3), (zt, R_EC1)]
lathe(prof)
b = S_AB / 2; box(-b, -b, zab, b, b, ztop)
with open(sys.argv[1], "w") as f:
    f.write("# stone pillar of room 739 (remake/recipes/pillar_739/pillar.py), origin = axis on the ground, top %.1f\n" % ztop)
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
