#!/usr/bin/env python3
"""lantern.py [OUT.obj] : the LANTERN ROOM of the Ryuma lighthouse as a close-up (rooms 627 RYUMA_LIGHTHOUSE / 628 _BROKEN, one map) as a light
shape (near-final 3D, as drawn). Measured 2026-11-24 on the room picture (U = x - y + 1184, V = (x + y) / 2 - z) + the collision:
  floor walkable 16, cells x 20..29 y 21..29 inside a blocked 16 rim (x / y 20 and 30) = room x 320..496 y 320..496;
  four square corner posts 15 wide (front post U 1170..1200 = 2 x side), flush with the room edge, up to the roof plate;
  roof flush with the posts (U span 351 = 2 x 175.5): the roof SQUARE at z 167 (left corner V 240, front corner V 329, back corner V 155 =
  the top point of the drawn roof: the pyramid apex 253 at the centre projects onto the same V 155, so it may not be higher), an eave band
  158..167 under it (first read 168..181 = the back corner taken for the plate top: corrected in self-review); small concave ARCH brackets under the plate on the inner side of each post (drawn arcs ~14 wide, ~22 high);
  the lamp: two hanging GLASS CYLINDERS r 8 (drawn 23 px wide at U ~1153 / ~1211) from the plate down to z ~22, on the line through the room
  centre (depth not visible), a small round lamp base under them; a low stone curb on the rim (drawn grey band ~8 high); the tower body below
  the floor (drawn stone walls down to the picture edge) as a block to z -160. The 208 high blocked cells of the lamp mechanism are no drawn solid
  (the op's floor 16 covers them). Pure Python, no ROM.  Run: python3 remake/recipes/lantern_627/lantern.py"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "landstalker", "data", "proxies", "lantern_627.obj")
X0, Y0, X1, Y1 = 320.0, 320.0, 496.0, 496.0; ZF, ZE0, ZE1, ZA = 16.0, 158.0, 167.0, 253.0; PS = 15.0; CX, CY = (X0 + X1) / 2, (Y0 + Y1) / 2
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
def tiled_pyramid(cx, cy, half, z0, z1, step=4.0, lip=0.8):
    """pyramid roof as TILE COURSES (drawn: one course every 8 px on the slope = 4 units of height): stacked square frustum layers, each
    starting lip units outside the pyramid surface (the tile's lower edge) and closing on it at its top; four ridge caps on the hips"""
    n = max(1, int(round((z1 - z0) / step))); hs = lambda z: half * (z1 - z) / (z1 - z0)
    for k in range(n):
        za, zb = z0 + (z1 - z0) * k / n, z0 + (z1 - z0) * (k + 1) / n
        a, b = hs(za) + (lip if k else 0.0), max(0.3, hs(zb))
        o = len(V); V.extend([(cx - a, cy - a, za), (cx + a, cy - a, za), (cx + a, cy + a, za), (cx - a, cy + a, za),
                              (cx - b, cy - b, zb), (cx + b, cy - b, zb), (cx + b, cy + b, zb), (cx - b, cy + b, zb)])
        F.extend([(o, o + 1, o + 5, o + 4), (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7), (o + 3, o + 2, o + 1, o), (o + 4, o + 5, o + 6, o + 7)])
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):                          # ridge caps along the four hips
        p0 = (cx + sx * half, cy + sy * half, z0); p1 = (cx, cy, z1); m = 8; o = len(V)
        d = [p1[i] - p0[i] for i in range(3)]; L = math.sqrt(sum(v * v for v in d)); d = [v / L for v in d]
        u = (sx / math.sqrt(2), -sy / math.sqrt(2), 0.0); w = (d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0])
        for p in (p0, p1):
            for i in range(m):
                t = 2 * math.pi * i / m; V.append(tuple(p[j] + 1.1 * (math.cos(t) * u[j] + math.sin(t) * w[j]) for j in range(3)))
        for i in range(m): F.append((o + i, o + (i + 1) % m, o + m + (i + 1) % m, o + m + i))
        F.append(tuple(o + i for i in reversed(range(m)))); F.append(tuple(o + m + i for i in range(m)))
def post(sx, sy, z0, z1):
    """square stone post with a base and a capital (instead of a plain chamfered box)"""
    cbox(sx - 1.0, sy - 1.0, z0, sx + PS + 1.0, sy + PS + 1.0, z0 + 5.0, 1.0)  # base
    cbox(sx, sy, z0 + 5.0, sx + PS, sy + PS, z1 - 5.0, 1.5)                    # shaft
    cbox(sx - 1.0, sy - 1.0, z1 - 5.0, sx + PS + 1.0, sy + PS + 1.0, z1, 1.0)  # capital
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
for sx, sy in ((X0, Y0), (X1 - PS, Y0), (X0, Y1 - PS), (X1 - PS, Y1 - PS)):
    post(sx, sy, ZF, ZE0)                                                              # corner posts (base, shaft, capital)
    ix = 1 if sx == X0 else -1; iy = 1 if sy == Y0 else -1                             # towards the room inside
    bracket(sx + (PS if ix > 0 else 0), sy + PS / 2, ix, 0)                            # along x from the post's inner x face
    bracket(sx + PS / 2, sy + (PS if iy > 0 else 0), 0, iy)                            # along y
cbox(X0, Y0, ZE0, X1, Y1, ZE1, 1.5)                                                    # roof plate
tiled_pyramid(CX, CY, (X1 - X0) / 2, ZE1, ZA)                                        # tile courses + ridge caps (2026-11-24 review: no plain pyramid)
for u in (-30.5, 27.0):                                                                # glass cylinders (x - y = u on the line x + y = 816)
    gx, gy = CX + u / 2, CY - u / 2
    lathe(gx, gy, [(22.0, 0.5), (23.0, 5.0), (26.0, 7.6), (30.0, 8.0), (ZE0 - 6, 8.0), (ZE0, 6.0)])
lathe(CX, CY, [(ZF, 9.0), (ZF + 2.5, 9.0), (ZF + 4.0, 5.0), (ZF + 6.0, 4.0)])           # lamp base
with open(OUT, "w") as f:
    f.write("# light proxy: Ryuma lighthouse lantern room close-up, rooms 627 / 628 (remake/recipes/lantern_627/lantern.py). GAME coordinates x east, y south, z up.\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
print("lantern_627: %d vertices, %d faces -> %s" % (len(V), len(F), OUT))
