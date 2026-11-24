#!/usr/bin/env python3
"""warp_tree.py ROM [OUT.obj] : the BIG APPLE TREE of the tree-warp map $11759C (rooms 510..513, 533..539: the same map) as a light shape (near-final 3D,
as drawn): round trunk with a root flare and six root buttresses + a lumpy canopy whose outline follows the drawn crown.
Measured 2026-11-24 on the room picture (U = x - y + 1184, V = (x + y) / 2 - z):
  * trunk collision: blocked height 160, cells x 29..32 y 27..28 + x 29..30 y 29..30, island walkable at 0;
  * trunk: drawn (layer A) a constant 60 px wide from V 435 to ~500 (U 1185..1246) -> radius 21, axis U 1215.5 -> x 493.75 y 462.25 (inside the
    collision), roots flare into the ground (plane B);
  * crown (layer A green, holes closed): U 984..1455, V 296..~446, centred on the trunk axis -> an ellipsoid around (493.75, 462.25, 107) with
    half axes 166 along the screen (x - y), 63.6 in depth (x + y) and 60 high (V half 75 = sqrt(b^2 / 2 + c^2); depth is not visible in the drawing,
    the height 47..167 then agrees with the 160 collision); per screen direction the ellipsoid is scaled to the drawn, smoothed crown outline.
Reads the user's ROM only to measure the outline (romrender via remake/tools/rom_picture.py's layer A), writes only our geometry.
Run: python3 remake/recipes/warp_tree_510/warp_tree.py ROM  ->  landstalker/data/proxies/warp_tree_510.obj"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", "..")
sys.path.insert(0, os.path.join(ROOT, "landstalker", "tools"))
import romrender as R
ROM = sys.argv[1]; OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "landstalker", "data", "proxies", "warp_tree_510.obj")
CX, CY = 493.75, 462.25; R_TRUNK = 21.0
CZ, A_S, B_D, C_H = 107.0, 166.0, 63.6, 60.0
UC, VC = CX - CY + 1184, (CX + CY) / 2 - CZ

# ---- drawn crown outline: layer A green pixels of the tree, holes closed, distance from (UC, VC) per screen angle (1 deg), smoothed
rom = open(ROM, "rb").read(); g, r, pa, pb, getpal = R.rom_planes(rom, 510); tp = R.tile_cache(g["tiles"])
U0, U1, V0, V1 = 960, 1480, 280, 470
mask = [[False] * (U1 - U0) for _ in range(V1 - V0)]
for v in range(V0, V1):
    for u in range(U0, U1):
        t = pa.t.get((u // 8, v // 8))
        if not t: continue
        i = tp(t[0], t[3], t[4])[v % 8][u % 8]
        if not i: continue
        cr, cg, cb = getpal(t[1], i)
        if cg > cr + 20 and cg >= cb: mask[v - V0][u - U0] = True
NA = 360; dist = [0.0] * NA
for v in range(V0, V1):
    for u in range(U0, U1):
        if mask[v - V0][u - U0]:
            du, dv = u - UC, v - VC; k = int(round(math.degrees(math.atan2(dv, du)))) % NA
            dist[k] = max(dist[k], math.hypot(du, dv))
# directions without leaves (below the crown, where the trunk is): the ellipse's own outline
def ell_d(phi):   # silhouette of the ellipsoid in screen: U half A_S * sqrt 2 ... computed from the projected half axes
    au = A_S * math.sqrt(2); bv = math.sqrt(B_D * B_D / 2 + C_H * C_H)
    c, s = math.cos(phi), math.sin(phi); return 1.0 / math.sqrt((c / au) ** 2 + (s / bv) ** 2)
for k in range(NA):
    if dist[k] < 0.5 * ell_d(math.radians(k)): dist[k] = ell_d(math.radians(k))
sm = [sum(dist[(k + j) % NA] for j in range(-12, 13)) / 25 for k in range(NA)]   # +-12 deg: the leaf clumps become soft lumps

V, F = [], []
def lathe(prof, n=32):
    o = len(V)
    for z, rr in prof:
        for i in range(n): a = 2 * math.pi * i / n; V.append((CX + rr * math.cos(a), CY + rr * math.sin(a), z))
    for j in range(len(prof) - 1):
        for i in range(n): a = o + j * n + i; b = o + j * n + (i + 1) % n; F.append((a, b, b + n, a + n))
    F.append(tuple(o + i for i in reversed(range(n)))); last = o + (len(prof) - 1) * n; F.append(tuple(last + i for i in range(n)))
# trunk: flare at the foot, slight taper, into the crown (ends inside it)
lathe([(0, 30.0), (4, 26.0), (10, 22.5), (20, 21.2), (60, 20.6), (100, 19.6), (140, 18.0)])
def root(ang, length, r0):
    """a buttress root: a tapered, flattened tube from the trunk surface down into the ground"""
    o = len(V); n = 10; c, s = math.cos(ang), math.sin(ang); steps = 5
    for k in range(steps + 1):
        t = k / steps; rr = r0 * (1 - 0.55 * t); d = R_TRUNK - 3 + length * t; zc = 7.0 * (1 - t) ** 1.3 + 0.5   # flatter, blunter roots (v1 looked like spikes)
        for i in range(n):
            a = 2 * math.pi * i / n; w = rr * math.cos(a); h = rr * math.sin(a) * 0.6
            V.append((CX + c * d - s * w, CY + s * d + c * w, max(0.0, zc + h)))
    for k in range(steps):
        for i in range(n): a = o + k * n + i; b = o + k * n + (i + 1) % n; F.append((a, b, b + n, a + n))
    F.append(tuple(o + i for i in reversed(range(n)))); last = o + steps * n; F.append(tuple(last + i for i in range(n)))
for k in range(6): root(math.radians(15 + 60 * k), 26.0, 7.5)   # drawn roots reach ~30 beyond the trunk (U 1147 .. 1270 at the ground)
# canopy (2026-11-24 v2, after the first clay preview looked like a smooth mushroom cap with a dent at the pole): a CORE ellipsoid (0.8 of the
# envelope) + leaf CLUMPS (spheres r 30..40) whose outer side reaches the ENVELOPE = the screen-aligned ellipsoid scaled per screen direction to the
# drawn, smoothed crown outline (the drawn crown is a heap of leaf clumps, the outline keeps its lumps)
eu = (1 / math.sqrt(2), -1 / math.sqrt(2), 0.0); ed = (1 / math.sqrt(2), 1 / math.sqrt(2), 0.0)
def env(th, ph, shrink=1.0):
    """envelope point (offset from the crown centre) for polar angle th (0 = up) and azimuth ph (0 = screen right)"""
    p = (A_S * math.sin(th) * math.cos(ph), B_D * math.sin(th) * math.sin(ph), C_H * math.cos(th))
    off = [p[0] * eu[m] + p[1] * ed[m] for m in range(2)] + [p[2]]
    du = off[0] - off[1]; dv = (off[0] + off[1]) / 2 - off[2]; dd = math.hypot(du, dv)
    a = math.atan2(dv, du); k = int(round(math.degrees(a))) % NA; f = sm[k] / ell_d(a)
    f = 1 + (f - 1) * min(1.0, (dd / ell_d(a)) ** 2) if dd > 1e-6 else 1.0   # full correction at the outline, none at the centre
    return [c * f * shrink for c in off]
def blob(cx, cy, cz, rx, ry, rz, n1=10, n2=16, off=None):
    """closed ellipsoid / sphere mesh; off(th, ph) -> offset overrides the plain radii (the core)"""
    o = len(V); d0 = off if off else (lambda th, ph: (rx * math.sin(th) * math.cos(ph), ry * math.sin(th) * math.sin(ph), rz * math.cos(th)))
    for i in range(1, n1):
        th = math.pi * i / n1
        for j in range(n2):
            d = d0(th, 2 * math.pi * j / n2); V.append((cx + d[0], cy + d[1], cz + d[2]))
    d = d0(0.0, 0.0); t = len(V); V.append((cx + d[0], cy + d[1], cz + d[2]))
    d = d0(math.pi, 0.0); b = len(V); V.append((cx + d[0], cy + d[1], cz + d[2]))
    for i in range(n1 - 2):
        for j in range(n2):
            a = o + i * n2 + j; c = o + i * n2 + (j + 1) % n2; F.append((a, a + n2, c + n2, c))
    for j in range(n2):
        F.append((t, o + j, o + (j + 1) % n2)); l = o + (n1 - 2) * n2; F.append((b, l + (j + 1) % n2, l + j))
blob(CX, CY, CZ, 0, 0, 0, 14, 40, off=lambda th, ph: env(th, ph, 0.8))
import random
rnd = random.Random(510); clumps = 0
for th_deg, n in ((0, 1), (28, 7), (52, 11), (76, 15), (100, 13)):    # rings of clumps from the top down to just under the widest line
    for j in range(n):
        th = math.radians(th_deg); ph = 2 * math.pi * (j + 0.5 * (th_deg // 24 % 2)) / n + rnd.uniform(-0.12, 0.12)
        e = env(th, ph); le = math.sqrt(sum(c * c for c in e)); rl = rnd.uniform(30.0, 40.0) * (0.75 if th_deg >= 100 else 1.0)
        k = max(0.0, le - rl) / le if le > 1e-6 else 0.0
        blob(CX + e[0] * k, CY + e[1] * k, CZ + e[2] * k, rl, rl, rl * 0.85); clumps += 1
with open(OUT, "w") as f:
    f.write("# light proxy: big apple tree of the tree-warp map, rooms 510..513 533..539 (remake/recipes/warp_tree_510/warp_tree.py). GAME coordinates.\n")
    for v in V: f.write("v %.2f %.2f %.2f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
zs = [v[2] for v in V]
print("warp_tree: %d clumps, %d vertices %d faces, z %.0f..%.0f, outline scale %.2f..%.2f -> %s" % (clumps, len(V), len(F), min(zs), max(zs),
      min(sm[k] / ell_d(math.radians(k)) for k in range(NA)), max(sm[k] / ell_d(math.radians(k)) for k in range(NA)), OUT))
