#!/usr/bin/env python3
"""griffin.py : the GRIFFIN HEAD over the door of Mir's tower (room 475) as a smooth SCULPT (Blender metaballs, like the church angel):
user 2026-11-24 ('das ist eigentlich ein Statuenkopf', 'eher der Kopf eines Vogel Greifs', 'aus der Wand heraus in der normalen isometrischen
Perspektive', 'gerne mehr Dreiecke und detaillierter', 'von den Proportionen her nach dem Original'). Three hand-built primitive heads and an
image relief were rejected; this one is sculpted: a fan of feathers on the wall, an elongated skull, cheeks, a heavy brow over sunken eyes, a
laterally narrow hooked beak (chain of shrinking ellipsoids with a cere at the root and a cut gape), two laid-back ear tufts.
Local frame: x right, y = OUT of the wall (the head looks along +y), z up, origin on the wall at the head centre. The result is scaled / placed
by tower.py onto the drawn head (U 1104..1132, V 271..296; beak tip = the lower-left drawn point).
Run: python3 remake/recipes/mir_tower_475/griffin.py  ->  ~/.landstalker_remake/assets/griffin_475/griffin_head_{full,light}.obj (local frame;
generated, not in git), then tower.py places the light version (fit to the drawn outline: scale 0.85, width x 2.0, centre x 353 z 100)."""
import json, math, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, "..", "church_angel_sculpt", "mb_blender.py")
K = 1 / 0.575          # metaball radius for a wanted surface radius (lone ball)
def ball(c, r, neg=False, st=2.0): return {"type": "BALL", "co": list(c), "radius": r * K, "neg": neg, "stiffness": st}
def ell(c, r, size, quat=None, neg=False, st=2.0):
    e = {"type": "ELLIPSOID", "co": list(c), "radius": r * K, "size": list(size), "neg": neg, "stiffness": st}
    if quat: e["quat"] = list(quat)
    return e
def qz(deg):   # rotation about z
    a = math.radians(deg) / 2; return (math.cos(a), 0, 0, math.sin(a))
def qy(deg):   # rotation about y (in the wall plane)
    a = math.radians(deg) / 2; return (math.cos(a), 0, math.sin(a), 0)
def qx(deg):
    a = math.radians(deg) / 2; return (math.cos(a), math.sin(a), 0, 0)
E = []
# feathered NECK (user 2026-11-24 mark: the feathers at the back go BACK and UP, they do not lie flat; they form the neck the head sits on at the
# wall): a thick neck from the back of the skull back and up into the wall, covered with three rows of shingle feathers whose tips point back / up
# v3 (user: 'der Hals geht nicht gerade nach oben sondern ist gebogen, der Kopf sitzt gerade auf dem Hals'): a CURVED neck = cubic Bezier from
# the root on the wall (high) out and over, bending down into the back / top of the skull; the head sits upright at its end looking out (+y)
def bez(t, P):
    a, b, c, d = P; u = 1 - t
    return tuple(u ** 3 * a[i] + 3 * u * u * t * b[i] + 3 * u * t * t * c[i] + t ** 3 * d[i] for i in range(3))
def bezd(t, P):
    a, b, c, d = P; u = 1 - t
    return tuple(3 * u * u * (b[i] - a[i]) + 6 * u * t * (c[i] - b[i]) + 3 * t * t * (d[i] - c[i]) for i in range(3))
HO = (0.0, 2.0, -1.0)                                                            # the head (elements below) moves here: out
NP = ((0.0, -1.5, 3.0), (0.0, 1.0, 4.6), (0.0, 3.2, 4.4), (0.0, 5.0, 2.6))    # neck: out of the wall at about head height, a gentle arch into the back of the skull (v4, user: 'nicht so nach oben weg', 'mach es so, dass es fuer die Lichtform passt und auf der Zeichnung liegt')
NR = lambda t: 5.2 - 1.2 * t                                                     # neck radius
for k in range(10):
    t = k / 9; c = bez(t, NP); r = NR(t); E.append(ell(c, 1.0, (r, r * 0.9, r * 0.9), st=2.5))
# (the neck FEATHERS are explicit blades appended after the metaball mesh, see FEATHERS below: metaball feathers fused into a smooth hood)
H0 = len(E)
# skull, elongated forward, cheeks, brow, eyes
E.append(ell((0, 6.0, 2.2), 1.0, (6.2, 6.4, 6.0)))
for sx in (-1, 1):
    E.append(ell((sx * 3.8, 7.2, -0.8), 1.0, (2.8, 3.6, 2.6)))                 # cheek feathers
    E.append(ell((sx * 3.2, 9.4, 4.4), 1.0, (2.6, 2.0, 1.2), qy(sx * -12)))     # brow over the eye
    E.append(ball((sx * 3.9, 9.6, 2.6), 1.6, neg=True))                         # eye socket
    E.append(ball((sx * 3.7, 9.2, 2.6), 0.9))                                   # eyeball
E.append(ell((0, 9.0, 5.6), 1.0, (2.2, 2.6, 1.2)))                              # forehead ridge between the brows
# beak: cere at the root, then a laterally narrow chain curving out and down to the hook
E.append(ell((0, 10.6, 2.4), 1.0, (2.6, 1.4, 1.6)))                              # cere
# beak: a dense chain along a smooth curve (v1: 7 elements = a thin trunk with beads at the tip), thicker, laterally narrow (0.72)
def bez(t, P):
    a, b, c, d = P; u = 1 - t
    return tuple(u ** 3 * a[i] + 3 * u * u * t * b[i] + 3 * u * t * t * c[i] + t ** 3 * d[i] for i in range(3))
BP = ((0, 10.8, 2.0), (0, 14.0, 2.4), (0, 16.6, 0.0), (0, 15.6, -5.6))   # (head frame, shifted by HO below)
for k in range(16):
    t = k / 15; c = bez(t, BP); r = 3.3 * (1 - t) ** 0.85 + 0.45
    E.append(ell(c, 1.0, (r * 0.72, r * 1.0, r), st=3.0))
E.append(ell((0, 10.0, 4.4), 1.0, (1.8, 3.2, 1.3), qx(18)))                      # ridge from the forehead into the beak top
E.append(ell((0, 12.8, -0.9), 1.0, (1.8, 2.8, 1.1)))                             # lower mandible under the hook
for sx in (-1, 1):
    E.append(ell((sx * 2.2, 12.6, -0.25), 1.0, (0.4, 2.8, 0.3), neg=True))    # gape line
for e in E[H0:]: e["co"] = [e["co"][i] + HO[i] for i in range(3)]
data = {"groups": [{"name": "griffin", "elements": E, "res": 0.22, "threshold": 0.6}]}
GEN = os.path.expanduser("~/.landstalker_remake/assets/griffin_475"); os.makedirs(GEN, exist_ok=True)
pj = os.path.join(GEN, "parts.json"); raw = os.path.join(GEN, "raw.obj"); out = os.path.join(GEN, "griffin_head_full.obj"); light = os.path.join(GEN, "griffin_head_light.obj")
json.dump(data, open(pj, "w"))
env = dict(os.environ, MB_IN=pj, MB_OUT=raw, MB_RES="0.22")
r = subprocess.run(["flatpak", "run", "--filesystem=home", "org.blender.Blender", "-b", "--python", MB], env=env, capture_output=True, text=True)
if not os.path.exists(raw): print(r.stdout[-2000:], r.stderr[-2000:]); sys.exit(1)
V, F = [], []
for l in open(raw):
    if l.startswith("v "): V.append(tuple(map(float, l.split()[1:4])))
    elif l.startswith("f "): F.append([int(t) for t in l.split()[1:]])

# FEATHERS: explicit shingle blades on the neck (rows from the head back to the wall, the sides and the top), each a pointed, slightly cupped
# leaf 5.5 long, 2.6 wide, 0.7 thick, its tip pointing BACK and UP along the neck (user mark), overlapping like roof tiles
nb = 0
def blade(root, d, n, L=5.5, W=2.6, T=0.7, nu=7, nw=4):
    global nb
    s_ = (d[1] * n[2] - d[2] * n[1], d[2] * n[0] - d[0] * n[2], d[0] * n[1] - d[1] * n[0])   # side axis
    o = len(V); rows = []
    for side in (1, -1):                                                         # top and bottom surface
        for i in range(nu + 1):
            t = i / nu; half = W / 2 * math.sin(math.pi * min(1.0, t * 1.08)) ** 0.7 if t < 0.999 else 0.0
            for j in range(nw + 1):
                q = -1 + 2 * j / nw; w_ = half * q; cup = 0.5 * (1 - q * q) * math.sin(math.pi * t)
                off = side * T / 2 * (1 - t * 0.7) + cup
                V.append(tuple(root[k] + d[k] * L * t + s_[k] * w_ + n[k] * off for k in range(3)))
    m = (nu + 1) * (nw + 1)
    def idx(sd, i, j): return o + sd * m + i * (nw + 1) + j
    for sd in (0, 1):
        for i in range(nu):
            for j in range(nw):
                a_, b_, c_, d_ = idx(sd, i, j), idx(sd, i + 1, j), idx(sd, i + 1, j + 1), idx(sd, i, j + 1)
                F.append([x + 1 for x in ((a_, b_, c_, d_) if sd == 0 else (a_, d_, c_, b_))])
    for i in range(nu):                                                          # rims
        for j in (0, nw):
            a_, b_ = idx(0, i, j), idx(0, i + 1, j); c_, d_ = idx(1, i + 1, j), idx(1, i, j)
            F.append([x + 1 for x in ((a_, d_, c_, b_) if j == 0 else (a_, b_, c_, d_))])
    for j in range(nw):
        a_, b_ = idx(0, 0, j), idx(0, 0, j + 1); c_, d_ = idx(1, 0, j + 1), idx(1, 0, j)
        F.append([x + 1 for x in (a_, b_, c_, d_)])
    nb += 1
for row, t in enumerate((0.92, 0.75, 0.58, 0.41, 0.24, 0.08)):                 # from the head back to the wall root
    c0 = bez(t, NP); tg = bezd(t, NP); Lt = math.sqrt(sum(v * v for v in tg)); tg = [v / Lt for v in tg]
    side = (1.0, 0.0, 0.0); up = (tg[1] * side[2] - tg[2] * side[1], tg[2] * side[0] - tg[0] * side[2], tg[0] * side[1] - tg[1] * side[0])
    Lu = math.sqrt(sum(v * v for v in up)); up = [v / Lu for v in up]
    if up[2] < 0: up = [-v for v in up]
    rr = NR(t) * 0.9 + 0.1
    for k in range(13):
        ph = math.radians(-30 + 240 * k / 12 + (9 if row % 2 else 0))        # around the neck: the sides and the outer (upper) side
        nrm = [math.cos(ph) * side[i] + math.sin(ph) * up[i] for i in range(3)]
        if math.sin(ph) < -0.5: continue
        root = [c0[i] + rr * nrm[i] for i in range(3)]
        d = [-tg[i] * 0.9 + nrm[i] * 0.3 for i in range(3)]; Ld = math.sqrt(sum(v * v for v in d)); d = [v / Ld for v in d]
        nn = [nrm[i] - sum(nrm[j] * d[j] for j in range(3)) * d[i] for i in range(3)]; Ln_ = math.sqrt(sum(v * v for v in nn)); nn = [v / Ln_ for v in nn]
        blade(root, d, nn, L=4.6, W=2.4)
print("griffin: %d feather blades" % nb)
# keep only what stands in front of the wall (y > 0.2); the faces behind it are hidden in the tower anyway
with open(out, "w") as f:
    f.write("# griffin head sculpt (remake/recipes/mir_tower_475/griffin.py), LOCAL frame: x right, y out of the wall, z up; placed by tower.py\n")
    for v in V: f.write("v %.4f %.4f %.4f\n" % v)
    for fc in F: f.write("f " + " ".join(map(str, fc)) + "\n")
os.remove(pj); os.remove(raw)
# light version: collapse-decimated to ~6000 triangles (the light works on 4 unit columns / game pixels), read by tower.py
DEC = os.path.join(HERE, "..", "church_angel_sculpt", "decimate.py")
subprocess.run(["flatpak", "run", "--filesystem=home", "org.blender.Blender", "-b", "--python", DEC], env=dict(os.environ, DC_IN=out, DC_OUT=light, DC_TRIS="6000", DC_HEAD="# griffin head, light version, LOCAL frame (griffin.py)"), capture_output=True, text=True)
print("griffin: light version", light, os.path.exists(light))
xs = [v[0] for v in V]; ys = [v[1] for v in V]; zs = [v[2] for v in V]
print("griffin: %d vertices %d triangles, x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f -> %s" % (len(V), len(F), min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), out))
