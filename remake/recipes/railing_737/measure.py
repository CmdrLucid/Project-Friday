#!/usr/bin/env python3
"""measure.py ROM : the posts of the rope railings of room 737 (Kazalt outside) measured on the drawn room picture -> params.json (our measurements only, no ROM data).
Posts: template match of one drawn post (cap, ring, shaft; 7 x 27 px, >= 80 %% equal colours, mirrored copies included) on the 1 px room grid (U = x - y + 1184, V = (x + y) / 2 - z);
foot = the shaft's lower end. Foot in the world: the view ray through the foot pixel, from high to low, stops at the first floor (free cell: its height; a blocked railing STRIP: the
walkway it borders); a post whose ray meets a step's SIDE (height off the 16 grid) or no floor (north side of the east stair, top of the inner stair) takes the highest free floor k with a blocked cell within 8 units (its stair step).
Runs: posts on one line (same x or y within 2.5), neighbours 14..34 apart; the strip rectangle and its ground BEHIND the posts (the light op's floor) are listed in RUNS.
Needs numpy + PIL (e.g. ~/Project-Friday-Test/hdvenv/bin/python) and the ROM; run from the repo root."""
import json, os, sys, types
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "landstalker", "tools"))
import numpy as np, romrender as R, proxysurvey as ps
ROM = open(sys.argv[1], "rb").read(); ROOM = 737; W, H = 2400, 1300
g, rr, pa, pb, getpal = R.rom_planes(ROM, ROOM)
rgb = np.frombuffer(bytes(R.compose(pa, pb, getpal, 0, 0, W, H, (0, 0, 0), g['tiles'])), np.uint8).reshape(H, W, 3).astype(int)
K = rgb[..., 0] * 65536 + rgb[..., 1] * 256 + rgb[..., 2]
T = K[434:461, 1556:1563]; mask = np.isin(T, [0xd8d8d8, 0x6c906c, 0x009048, 0x004848])   # the corner post of the path at the door (axis U 1559.5, foot V 461)
hits = []
for V in range(250, 850):
    for U in range(700, 1950):
        w = K[V:V + 27, U:U + 7]
        if w.shape == T.shape:
            s = (w[mask] == T[mask]).mean()
            if s >= 0.80: hits.append((s, U, V))
hits.sort(reverse=True); found = []
for s, U, V in hits:
    if all(abs(U - u) > 4 or abs(V - v) > 6 for _, u, v in found): found.append((s, U, V))
hm = ps.heights(ROM, ROOM)
def floor(c):
    h = hm.get(c)
    if not h: return None
    if not h[1]: return 16 * h[0]
    if h[0] < 1: return None
    nb = [hm[q][0] for q in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)) if q in hm and not hm[q][1] and hm[q][0] <= h[0]]
    return 16 * max(nb) if nb else None
def near(x, y, r, pred):
    return any((lambda h: h and pred(h))(hm.get((int((x + dx) // 16), int((y + dy) // 16)))) for dx in range(-r, r + 1, 2) for dy in range(-r, r + 1, 2))
posts = []
for s, U, V in sorted(found, key=lambda t: (t[1], t[2])):
    Ua, Vf = U - 0.5, V + 27; D = Ua - 1184; got = None   # the template window starts at the shaft's light core: the drawn shaft (dark rims incl.) is columns U - 3 .. U + 1, axis U - 0.5 (2026-11-26: U + 3.5 put every post 4 px right, user: 'die Pfaehle liegen noch nicht gut drauf')
    for zz in range(400, -32, -1):
        z = zz / 2.0; x = Vf + z + D / 2; y = Vf + z - D / 2; f = floor((int(x // 16), int(y // 16)))
        if f is not None and z <= f: got = [x, y, z]; break
    if got is None or got[2] % 16:   # the ray met a step's SIDE (height not on the 16 grid) or found no floor: beside the void, the stair step it stands on
        for k in range(10, -1, -1):
            z = 16 * k; x = Vf + z + D / 2; y = Vf + z - D / 2
            if near(x, y, 8, lambda h: not h[1] and h[0] == k) and near(x, y, 8, lambda h: h[1]): got = [x, y, z]; break
    posts.append({"U": Ua, "V": Vf, "x": round(got[0], 2), "y": round(got[1], 2), "z": got[2]})
json.dump({"_about": "room 737 rope railing posts measured on the drawn picture by measure.py (axis U, foot V, world foot x y z)", "posts": posts}, open(os.path.join(HERE, "params.json"), "w"), indent=0)
print(len(posts), "posts ->", os.path.join(HERE, "params.json"))
