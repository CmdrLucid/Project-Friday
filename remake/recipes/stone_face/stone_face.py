#!/usr/bin/env python3
"""stone_face.py OUT.obj [params.json] : the STONE FACE of the swamp (room 433, six copies on single blocked cells $43 = top 48 on ground 16: cells
(19,22) (28,22) (33,22) (19,30) (28,30) (33,30)) as OUR OWN 3D model (user 2026-11-20 leftover list group (4): 'Steingesichter 433').
Read on the 1 px grid (reference cell (19,22), base centre x 312 y 360 z 16 = picture U 1136 V 320): a weathered stone head, ~32 units tall on its
16 x 16 cell, round dome on top, the FACE looks to +x (the dark open mouth on the right front of the sprite), moss at its foot (colour only).
Model: a lathe (radius per height, fitted to the drawn silhouette), the +x side cut flatter (the face plane), the mouth = a recess into that plane,
a brow ledge above it. Origin = base centre on the ground; the face looks to +x. Pure Python, no ROM data."""
import json, math, sys
P = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
g = lambda k, d: P.get(k, d)
H = g("H", 32.0)                       # height above the ground
RB, RM = g("Rb", 7.0), g("Rm", 8.2)      # radius at the foot / the widest radius
TM, TD = g("tm", 0.35), g("td", 0.55)    # height share where the widest radius is reached / where the round dome starts
FX = g("face_x", 5.6)                  # the face plane: x <= FX (the +x side cut flat)
M = g("mouth", [0.55, 0.78, 3.4, 2.2])  # mouth: z0 / z1 as a share of H, half width (y), depth into the face plane
BROW = g("brow", 0.8)                  # brow ledge: how far it stands out over the mouth (x)
SX = g("sx", 1.0)                      # depth along x (the face side) / width (y): the head is deeper towards its face
SXB = g("sx_back", 1.0)                # the same for the back (-x) half
YAW = g("yaw", 0.0)                    # the face turned this many degrees from +x towards +y (the drawing: a little towards the viewer)
NU = 24
V, F = [], []
def rad(t):   # smooth head profile: foot -> widest (smoothstep), straight, then an elliptic dome (round, no cone tip)
    if t < TM: q = t / TM; return RB + (RM - RB) * q * q * (3 - 2 * q)
    if t < TD: return RM
    q = (t - TD) / (1 - TD); return RM * math.sqrt(max(0.0, 1 - q * q))
rings = []
NZ = 28
for j in range(NZ + 1):
    t = math.sin(0.5 * math.pi * j / NZ) ** 0.7 if j < NZ else 1.0; z = H * t; r = rad(t); ring = []   # rings denser towards the dome
    for i in range(NU):
        a = 2 * math.pi * i / NU; x, y = r * math.cos(a), r * math.sin(a); x *= SX if x > 0 else SXB
        if x > FX: x = FX + (x - FX) * 0.25          # the face plane: flatter on +x
        mz0, mz1, mw, md = M[0] * H, M[1] * H, M[2], M[3]
        if mz0 <= z <= mz1 and abs(y) <= mw and x > 0: x -= md                       # the mouth recess
        elif mz1 < z <= mz1 + 2.0 and abs(y) <= mw + 1.0 and x > 0: x += BROW        # brow ledge over it
        ring.append((x, y, z))
    rings.append(ring)
ca, sa = math.cos(math.radians(YAW)), math.sin(math.radians(YAW))
for ring in rings: V.extend([(x * ca - y * sa, x * sa + y * ca, z) for x, y, z in ring])
for j in range(NZ):
    for i in range(NU):
        a = j * NU + i; b = j * NU + (i + 1) % NU; F.append((a, b, b + NU, a + NU))
V.append((0.0, 0.0, 0.0)); bot = len(V) - 1
for i in range(NU): F.append((bot, (i + 1) % NU, i))
V.append((0.0, 0.0, H)); top = len(V) - 1
for i in range(NU): F.append((top, NZ * NU + i, NZ * NU + (i + 1) % NU))
with open(sys.argv[1], "w") as f:
    f.write("# stone face of room 433 (remake/recipes/stone_face/stone_face.py), origin = base centre on the ground, face to +x\n")
    for v in V: f.write("v %g %g %g\n" % tuple(round(c, 3) for c in v))
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
