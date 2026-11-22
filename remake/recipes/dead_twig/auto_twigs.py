#!/usr/bin/env python3
"""auto_twigs.py ROM [ROOMS] [--write] [--png DIR] (default ROOMS = SWAMP: the swamp rooms; elsewhere the colours also hit statues / roots / vines) : every DEAD SWAMP TWIG of the given rooms as its own 3D light model, built straight from the drawing
(user 2026-11-21: many twigs, nearly each one its own drawing -> 'automatisch'). Needs numpy, scipy, Pillow (~/Project-Friday-Test/hdvenv/bin/python3).
1. plane A of the room alone (romrender, layer B empty); twig STEMS = 8-connected groups of bark colours (216,144,72 / 144,108,36 / 216,216,216) away from
   the bright grass greens (2 px), at least 7 rows high, thin (median 2.5 px per row; board walk posts are wider, its nail heads wider than high) and
   free standing (>= 50 % of a ring around them transparent: no cliff streaks).
2. the twig = everything 8-connected to a stem over bark + outline colours (0,72,36 / 72,72,36) away from the grass: the side branches come along.
3. skeleton of its bark pixels (Zhang-Suen thinning), cut into chains between end points / forks, every 2nd pixel kept; radius = (median bark width + 2
   outline px) / 2.83 (a round stem of radius r is 2.83 r wide in U), 60 % at the tips.
4. foot = the lowest skeleton pixel; world foot by the view ray (remake/recipes/plants/plants.py foot_world on heights_full); the chains lie in the
   picture plane through it (x = X + dU / 2, y = Y - dU / 2, z = Z - dV) = the light variant 'as drawn'.
5. tubes with 12 sides (the light smooths normals within 35 deg: round). --write: landstalker/data/proxies/twig_ROOM_K.obj + one 'mesh' op (surface) per twig
   in data/light_proxies.json (old auto_twigs ops of the room are replaced). No ROM data in git: only this recipe; the OBJs are our geometry."""
import collections, json, math, os, sys
import numpy as np
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "landstalker", "tools")); sys.path.insert(0, os.path.join(ROOT, "remake", "recipes", "plants"))
_argv = sys.argv; sys.argv = [_argv[0], _argv[1]]
import plants as P, romrender as R
sys.argv = _argv
P.ROM = open(sys.argv[1], "rb").read(); W, H = P.W, P.H
BARK = [(216, 144, 72), (144, 108, 36), (216, 216, 216)]; LINE = [(0, 72, 36), (72, 72, 36)]; GREEN = [(72, 144, 0), (0, 216, 72)]
NS = 12
SWAMP = [431, 432, 433, 436, 443, 444]   # tileset 13 rooms with dead twigs (2026-11-21 survey of all 28 tileset 13 rooms: elsewhere only false hits)
def isin(rgb, cols):
    m = np.zeros(rgb.shape[:2], bool)
    for c in cols: m |= (rgb[:, :, 0] == c[0]) & (rgb[:, :, 1] == c[1]) & (rgb[:, :, 2] == c[2])
    return m
def thin(m):   # Zhang-Suen
    m = m.copy().astype(np.uint8); ch = True
    while ch:
        ch = False
        for step in (0, 1):
            p = np.pad(m, 1); P2, P3, P4, P5, P6, P7, P8, P9 = (p[:-2, 1:-1], p[:-2, 2:], p[1:-1, 2:], p[2:, 2:], p[2:, 1:-1], p[2:, :-2], p[1:-1, :-2], p[:-2, :-2])
            B = P2 + P3 + P4 + P5 + P6 + P7 + P8 + P9; seq = [P2, P3, P4, P5, P6, P7, P8, P9, P2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8) for i in range(8))
            c1 = (P2 * P4 * P6 == 0) & (P4 * P6 * P8 == 0) if step == 0 else (P2 * P4 * P8 == 0) & (P2 * P6 * P8 == 0)
            d = (m == 1) & (B >= 2) & (B <= 6) & (A == 1) & c1
            if d.any(): m[d] = 0; ch = True
    return m.astype(bool)
def clean(sk):
    """staircase pixels out (a pixel with 3+ neighbours whose neighbours stay 8-connected without it), then spurs shorter than 3 px cut"""
    sk = sk.copy(); N8 = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]
    def nbs(y, x): return [(y + a, x + b) for a, b in N8 if sk[y + a, x + b]]
    def conn(ps):
        if not ps: return True
        st = [ps[0]]; seen = {ps[0]}
        while st:
            q = st.pop()
            for r in ps:
                if r not in seen and max(abs(r[0] - q[0]), abs(r[1] - q[1])) == 1: seen.add(r); st.append(r)
        return len(seen) == len(ps)
    ch = True
    while ch:
        ch = False
        for y, x in zip(*np.nonzero(sk)):
            nb = nbs(y, x)
            if len(nb) >= 3 and conn(nb): sk[y, x] = False; ch = True
    for _ in range(2):
        for y, x in zip(*np.nonzero(sk)):
            if len(nbs(y, x)) != 1: continue
            path = [(y, x)]; cur = (y, x); prev = None
            while True:
                nb = [q for q in nbs(*cur) if q != prev]
                if len(nb) != 1 or len(path) > 3: break
                prev, cur = cur, nb[0]; path.append(cur)
            if len(path) <= 3 and len(nbs(*cur)) >= 3:
                for q in path[:-1]: sk[q] = False
    return sk

def chains(sk):
    pts = set(zip(*np.nonzero(sk))); nb = lambda p: [(p[0] + a, p[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (p[0] + a, p[1] + b) in pts]
    nodes = {p for p in pts if len(nb(p)) != 2}; used = set(); out = []
    starts = list(nodes) or [next(iter(pts))]
    for s in starts:
        for q in nb(s):
            if (s, q) in used: continue
            ch = [s, q]; used.add((s, q)); used.add((q, s)); prev, cur = s, q
            while cur not in nodes:
                nx = [r for r in nb(cur) if r != prev and (cur, r) not in used]
                if not nx: break
                used.add((cur, nx[0])); used.add((nx[0], cur)); prev, cur = cur, nx[0]; ch.append(cur)
                if cur == s: break
            out.append(ch)
    return out
def tube(V, F, P3, R3):
    n = len(P3); base = len(V); prev = None
    sub = lambda a, b: (a[0] - b[0], a[1] - b[1], a[2] - b[2]); nrm = lambda a: tuple(t / (math.sqrt(sum(x * x for x in a)) or 1) for t in a)
    cr = lambda a, b: (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    for i in range(n):
        d = nrm(sub(P3[min(i + 1, n - 1)], P3[max(i - 1, 0)])); ref = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
        e1 = nrm(cr(d, ref)) if prev is None else nrm(sub(prev, tuple(d[k] * sum(prev[j] * d[j] for j in range(3)) for k in range(3))))
        e2 = cr(d, e1); prev = e1
        for k in range(NS):
            a = 2 * math.pi * k / NS; V.append(tuple(P3[i][j] + R3[i] * (math.cos(a) * e1[j] + math.sin(a) * e2[j]) for j in range(3)))
    for i in range(n - 1):
        for k in range(NS): a = base + i * NS + k; b = base + i * NS + (k + 1) % NS; F.append((a, b, b + NS, a + NS))
    V.append(P3[0]); c0 = len(V) - 1; V.append(P3[-1]); c1 = len(V) - 1
    for k in range(NS): F.append((c0, base + (k + 1) % NS, base + k)); F.append((c1, base + (n - 1) * NS + k, base + (n - 1) * NS + (k + 1) % NS))
def survey(room):
    g, rr, pa, pb, getpal = R.rom_planes(P.ROM, room)
    rgb = np.frombuffer(bytes(R.compose(pa, P.E, getpal, 0, 0, W, H, (0, 0, 0), g['tiles'])), np.uint8).reshape(H, W, 3)
    bark = isin(rgb, BARK); line = isin(rgb, LINE); nogreen = ~ndimage.binary_dilation(isin(rgb, GREEN), iterations=2)
    core = bark & nogreen; lab, n = ndimage.label(core, structure=np.ones((3, 3))); seeds = np.zeros((H, W), bool)
    for k, sl in enumerate(ndimage.find_objects(lab)):
        m = lab[sl] == k + 1; h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start; cnt = int(m.sum())
        rw = np.median([row.sum() for row in m if row.any()])
        if not (h >= 7 and cnt >= 8 and rw <= 2.5 and not (h <= 10 and w >= h)): continue
        full = np.zeros((H, W), bool); full[sl] = m; ring = ndimage.binary_dilation(full, iterations=3) & ~ndimage.binary_dilation(full, iterations=1)
        if ring.any() and float((rgb[ring].sum(1) == 0).mean()) >= 0.5: seeds |= full
    obj, no = ndimage.label((bark | line) & nogreen, structure=np.ones((3, 3))); ids = sorted(set(np.unique(obj[seeds])) - {0})
    plants = json.load(open(os.path.join(ROOT, "landstalker", "data", "plants.json")))["rooms"].get(str(room), [])
    hm = P.heights_full(room); P._gfc.clear(); P._vc.clear(); bushes = set(); twigs = []
    for i in ids:
        m = obj == i; bm = m & bark; ys, xs = np.nonzero(bm)
        if len(ys) < 8: continue
        if (ys.max() - ys.min() + 1) < 0.8 * (xs.max() - xs.min() + 1) and ys.max() - ys.min() + 1 < 20: continue   # flat + wide = tree roots at a forest edge (444), not a twig
        ring = ndimage.binary_dilation(m, iterations=3) & ~ndimage.binary_dilation(m, iterations=1)
        if float((rgb[ring].sum(1) == 0).mean()) < 0.5: continue   # the whole twig stands free too (roots under tree crowns: 444 / 431)
        sk = clean(thin(np.pad(bm, 2)))[2:-2, 2:-2]; rw = float(np.median([r.sum() for r in bm[ys.min():ys.max() + 1] if r.any()])); r0 = (rw + 2) / 2.83
        sy, sx = np.nonzero(sk); k = int(np.argmax(sy)); fU, fV = int(sx[k]), int(sy[k]) + 1
        w = P.foot_world(hm, fU, fV, bushes, True) or P.foot_world(hm, fU, fV, bushes, True, skipvoid=False)
        if not w: print("room %d: twig at U %d V %d: no floor, skipped" % (room, fU, fV)); continue
        X, Y, Z = w[0], w[1], w[2]; parts = []
        if any(abs(q[1] - X) < 24 and abs(q[2] - Y) < 24 and abs(q[3] - Z) <= 16 for q in plants): print("room %d: twig at U %d V %d = the trunk of a plant model (data/plants.json), skipped" % (room, fU, fV)); continue
        deg = lambda p: sum(1 for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and sk[p[0] + a, p[1] + b])
        for ch in chains(sk):
            if len(ch) < 2: continue
            sel = ch[::2] + ([ch[-1]] if (len(ch) - 1) % 2 else [])
            P3 = [(X + (p[1] - fU) / 2.0, Y - (p[1] - fU) / 2.0, Z - (p[0] + 0.5 - fV)) for p in sel]
            R3 = [r0 * (0.6 if deg(p) == 1 else 1.0) for p in sel]; parts.append((P3, R3))
        twigs.append(dict(foot=(fU, fV), world=(round(X, 2), round(Y, 2), Z), cell=(int(X // 16), int(Y // 16)), parts=parts, mask=m))
    return twigs, rgb
def main():
    a = [x for x in sys.argv[2:] if not x.startswith("--")]; png = sys.argv[sys.argv.index("--png") + 1] if "--png" in sys.argv else None
    rooms = [int(x) for x in a if x != png] or SWAMP; jp = os.path.join(ROOT, "landstalker", "data", "light_proxies.json")
    data = json.load(open(jp), object_pairs_hook=collections.OrderedDict)
    for room in rooms:
        twigs, rgb = survey(room); ops = [e for e in data["rooms"].get(str(room), []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/twig_"))]
        for k, t in enumerate(twigs):
            V, F = [], []
            for P3, R3 in t["parts"]: tube(V, F, P3, R3)
            fn = "twig_%d_%d.obj" % (room, k)
            print("room %d: twig %d foot U %d V %d -> world %s cell %s, %d chains, %d faces" % (room, k, t["foot"][0], t["foot"][1], t["world"], t["cell"], len(t["parts"]), len(F)))
            if "--write" in sys.argv:
                with open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w") as f:
                    f.write("# dead swamp twig %d of room %d (remake/recipes/dead_twig/auto_twigs.py: skeleton of the drawn twig -> tubes), game coordinates\n" % (k, room))
                    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
                    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
                cx, cy = t["cell"]
                ops.append(collections.OrderedDict([("op", "mesh"), ("cells", [cx, cy, cx, cy]), ("file", "proxies/" + fn), ("surface", True),
                    ("why", "dead swamp twig: its own skeleton read from the drawing -> round tubes in the picture plane (remake/recipes/dead_twig/auto_twigs.py), user 2026-11-21 'automatisch'")]))
        if "--write" in sys.argv: data["rooms"][str(room)] = ops
        if png:
            os.makedirs(png, exist_ok=True); from PIL import Image
            out = rgb.copy() // 3
            for t in twigs: out[t["mask"]] = (255, 60, 255)
            Image.fromarray(out).save(os.path.join(png, "twigs_%d.png" % room))
    if "--write" in sys.argv:
        with open(jp, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False); f.write("\n")
        print("wrote", jp)
if __name__ == "__main__":
    main()
