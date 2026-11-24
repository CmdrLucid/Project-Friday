#!/usr/bin/env python3
"""lantern_628.py [OUT.obj] : the CUT-AWAY drawing of the Ryuma lighthouse lantern room = room 628 RYUMA_LIGHTHOUSE_BROKEN (the same map as 627,
but 628 puts the OTHER drawing over the cells: picture U - 512, V + 32 against 627, found by matching the floor grid, 2311 / 2400 pixels equal).
As drawn (measured 2026-11-24 on that drawing, shifted back into the standard projection U = x - y + 1184, V = (x + y) / 2 - z):
  floor 16 inside a 16 rim (room x / y 320..496), curb, tower body below - as 627 (lantern.py);
  the outer roof and the FRONT (SE) corner post are cut away; the other three corner posts (15 wide) end at z ~102 (SW / NE tops V 305.5);
  in the middle a SMALLER pyramid roof floats: square 106 wide around the room centre, base z 127 (left corner V 280.5), apex 182 (V 225.5),
  with a hanging lamp HOUSING under it: 44 wide, z 62..127 (drawn arch feet V 345), four corner legs + concave arches on each side (the drawn white arches);
  on the floor the broken lamp: a pedestal with a dome r 14 (top ~40) inside a wide crown of 12 glass petals (r 17 -> 25, up to ~46) (instead of 627's two glass cylinders).
Pure Python, no ROM.  Run: python3 remake/recipes/lantern_627/lantern_628.py"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "landstalker", "data", "proxies", "lantern_628.obj")
X0, Y0, X1, Y1 = 320.0, 320.0, 496.0, 496.0; ZF = 16.0; PS = 15.0; CX, CY = (X0 + X1) / 2, (Y0 + Y1) / 2
ZE0 = 127.0   # the brackets in the helper hang under ZE0: here under the small roof
V, F = [], []
def cbox(x0, y0, z0, x1, y1, z1, c=1.0):
    """box with chamfered vertical edges (c), closed"""
    pts = [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]; o = len(V); n = 8
    V.extend([(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts])
    for i in range(n): F.append((o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i))
    F.append(tuple(o + i for i in range(n - 1, -1, -1))); F.append(tuple(o + n + i for i in range(n)))
def lathe(cx, cy, prof, n=20):
    o = len(V)
    for z, r in prof:
        for i in range(n): a = 2 * math.pi * i / n; V.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    for j in range(len(prof) - 1):
        for i in range(n): a = o + j * n + i; b = o + j * n + (i + 1) % n; F.append((a, b, b + n, a + n))
    F.append(tuple(o + i for i in reversed(range(n)))); last = o + (len(prof) - 1) * n; F.append(tuple(last + i for i in range(n)))
def bracket(px, py, dx, dy, w=14.0, h=22.0, t=PS - 3.0):
    """concave quarter-arch bracket under the plate: starts at the post face (px, py), runs w along (dx, dy), h high, t thick (centred on the post)"""
    k = 10; prof = [(0.0, ZE0 - h)] + [(w * (1 - math.cos(math.pi / 2 * i / k)), ZE0 - h + h * math.sin(math.pi / 2 * i / k)) for i in range(1, k + 1)] + [(0.0, ZE0)]
    # prof = (distance from the post face along the edge, z); concave side faces the room opening
    nx, ny = -dy, dx; o = len(V); n = len(prof)
    for s in (-t / 2, t / 2):
        for d, z in prof: V.append((px + dx * d + nx * s, py + dy * d + ny * s, z))
    area = sum(prof[i][0] * prof[(i + 1) % n][1] - prof[(i + 1) % n][0] * prof[i][1] for i in range(n))
    side = 1 if (area > 0) == (dx + dy > 0) else -1
    for i in range(n):
        j = (i + 1) % n; q = (o + i, o + j, o + n + j, o + n + i); F.append(q if side > 0 else q[::-1])
    a, b = tuple(o + i for i in range(n)), tuple(o + n + i for i in range(n)); F.append(a[::-1] if side > 0 else a); F.append(b if side > 0 else b[::-1])
    f0 = len(F) - n - 2; vol = 0.0
    for fc in F[f0:]:
        for i in range(1, len(fc) - 1):
            p0, p1, p2 = V[fc[0]], V[fc[i]], V[fc[i + 1]]
            vol += p0[0] * (p1[1] * p2[2] - p1[2] * p2[1]) - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0]) + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])
    if vol < 0: F[f0:] = [fc[::-1] for fc in F[f0:]]   # outward normals whatever the direction

cbox(X0, Y0, -160.0, X1, Y1, ZF, 1.0)                                                  # tower body up to the floor
for a, b, c, d in ((X0, Y0, X1, Y0 + 10), (X0, Y1 - 10, X1, Y1), (X0, Y0, X0 + 10, Y1), (X1 - 10, Y0, X1, Y1)): cbox(a, b, ZF, c, d, ZF + 8, 0.8)   # curb
for sx, sy in ((X0, Y0), (X1 - PS, Y0), (X0, Y1 - PS)):                                 # three posts (the front SE one is cut away), cut at ~102
    cbox(sx, sy, ZF, sx + PS, sy + PS, 102.0, 1.5)
R = 53.0; o = len(V)                                                                   # small floating pyramid roof
cbox(CX - R, CY - R, ZE0, CX + R, CY + R, ZE0 + 3, 1.0)
o = len(V); V.extend([(CX - R, CY - R, ZE0 + 3), (CX + R, CY - R, ZE0 + 3), (CX + R, CY + R, ZE0 + 3), (CX - R, CY + R, ZE0 + 3), (CX, CY, 182.0)])
F.extend([(o, o + 1, o + 4), (o + 1, o + 2, o + 4), (o + 2, o + 3, o + 4), (o + 3, o, o + 4), (o + 3, o + 2, o + 1, o)])
H = 22.0; L = 5.0                                                                      # lamp housing under it: four legs + arches
for sx, sy in ((CX - H, CY - H), (CX + H - L, CY - H), (CX - H, CY + H - L), (CX + H - L, CY + H - L)):
    cbox(sx, sy, 62.0, sx + L, sy + L, ZE0, 0.8)
for sx, sy in ((CX - H, CY - H), (CX + H - L, CY + H - L)):
    ix = 1 if sx < CX else -1; iy = 1 if sy < CY else -1
    bracket(sx + (L if ix > 0 else 0), sy + L / 2, ix, 0, w=17.0, h=34.0, t=L - 1.0)
    bracket(sx + L / 2, sy + (L if iy > 0 else 0), 0, iy, w=17.0, h=34.0, t=L - 1.0)
lathe(CX, CY, [(ZF, 9.0), (ZF + 2.0, 9.0), (ZF + 4.0, 4.0), (ZF + 8.0, 3.5), (ZF + 10.0, 13.0), (ZF + 15.0, 14.0), (ZF + 20.0, 12.5), (ZF + 24.0, 7.0), (ZF + 25.0, 2.0)])   # pedestal + dome r 14, top ~40 (drawn U 1165..1205)
for k in range(12):                                                                     # wide crown of glass petals (drawn U 1145..1227 = r ~24..29), leaning outward
    a = 2 * math.pi * (k + 0.5) / 12; ca, sa = math.cos(a), math.sin(a)
    o = len(V); n = 6
    for (rr, z, w) in ((17.0, ZF + 8.0, 2.4), (22.0, ZF + 20.0, 2.0), (25.0, ZF + 30.0, 0.4)):
        for i in range(n):
            t = 2 * math.pi * i / n; V.append((CX + (rr + w * math.cos(t)) * ca - w * math.sin(t) * sa, CY + (rr + w * math.cos(t)) * sa + w * math.sin(t) * ca, z))
    for j in range(2):
        for i in range(n): q0 = o + j * n + i; q1 = o + j * n + (i + 1) % n; F.append((q0, q1, q1 + n, q0 + n))
    F.append(tuple(o + i for i in reversed(range(n)))); F.append(tuple(o + 2 * n + i for i in range(n)))
with open(OUT, "w") as f:
    f.write("# light proxy: Ryuma lighthouse lantern room, CUT-AWAY drawing of room 628 (remake/recipes/lantern_627/lantern_628.py). GAME coordinates x east, y south, z up.\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
print("lantern_628: %d vertices, %d faces -> %s" % (len(V), len(F), OUT))
