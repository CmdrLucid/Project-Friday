#!/usr/bin/env python3
"""awning.py OUT.obj PARAMS.json : the red CLOTH CANOPY with a BANNER on the two watchtowers of room 454 (Gumi / Ryuma / Mercator gates) as OUR OWN
model (2026-11-21): a square cloth (side s) sagging in the middle, a fringe band hanging from its edge, four thin poles from the tower top to its
corners, an A-frame of two poles over it carrying a banner plate that faces the viewer (plane x + y = const). Read on the 1 px grid; the tower itself
is the collision (round crenellated top, blocked 112). Round parts 12 sides. Game coordinates. Pure Python, no ROM data."""
import json, math, sys
P = json.load(open(sys.argv[2])); V, F = [], []
def rod(p0, p1, r, n=12):
    d = [p1[k] - p0[k] for k in range(3)]; L = math.sqrt(sum(x * x for x in d)) or 1e-6; d = [x / L for x in d]
    ref = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
    e1 = [d[1] * ref[2] - d[2] * ref[1], d[2] * ref[0] - d[0] * ref[2], d[0] * ref[1] - d[1] * ref[0]]; l = math.sqrt(sum(x * x for x in e1)); e1 = [x / l for x in e1]
    e2 = [d[1] * e1[2] - d[2] * e1[1], d[2] * e1[0] - d[0] * e1[2], d[0] * e1[1] - d[1] * e1[0]]; o = len(V)
    for p in (p0, p1):
        for i in range(n): a = 2 * math.pi * i / n; V.append(tuple(p[k] + r * (math.cos(a) * e1[k] + math.sin(a) * e2[k]) for k in range(3)))
    for i in range(n): F.append((o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i))
    F.append(tuple(o + i for i in range(n - 1, -1, -1))); F.append(tuple(o + n + i for i in range(n)))
for cx, cy in P["centres"]:
    s, ze, sag, th, fr, zt = P["s"], P["edge_z"], P["sag"], P.get("th", 1.0), P.get("fringe", 4.0), P["tower_top"]
    N = 8; h = s / 2; o = len(V)
    def zat(i, j): u, w = i / N * 2 - 1, j / N * 2 - 1; return ze - sag * (1 - u * u) * (1 - w * w)
    for layer in (0, 1):   # top / bottom sheet of the cloth
        for j in range(N + 1):
            for i in range(N + 1): V.append((cx - h + s * i / N, cy - h + s * j / N, zat(i, j) - th * layer))
    M = (N + 1) * (N + 1)
    for j in range(N):
        for i in range(N):
            a = o + j * (N + 1) + i; F.append((a, a + 1, a + N + 2, a + N + 1)); b = a + M; F.append((b, b + N + 1, b + N + 2, b + 1))
    ring = [(i, 0) for i in range(N)] + [(N, j) for j in range(N)] + [(i, N) for i in range(N, 0, -1)] + [(0, j) for j in range(N, 0, -1)]
    o2 = len(V)   # fringe band: hangs fr below the edge, 0.4 out
    for i, j in ring:
        x, y = cx - h + s * i / N, cy - h + s * j / N; ox = 0.4 * (1 if i == N else -1 if i == 0 else 0); oy = 0.4 * (1 if j == N else -1 if j == 0 else 0)
        V.append((x + ox, y + oy, zat(i, j))); V.append((x + ox, y + oy, zat(i, j) - fr))
    n = len(ring)
    for k in range(n): a = o2 + 2 * k; b = o2 + 2 * ((k + 1) % n); F.append((a, b, b + 1, a + 1))
    ins = P.get("pole_in", 2.0); pr = P.get("pole_r", 0.6)
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)): rod((cx + sx * (h - ins), cy + sy * (h - ins), zt), (cx + sx * (h - ins), cy + sy * (h - ins), ze - 0.5), pr)
    ap = (cx, cy, P["apex_z"]); fa = P.get("frame_off", h - ins)
    rod((cx - fa, cy + fa, ze), ap, pr); rod((cx + fa, cy - fa, ze), ap, pr)   # the A-frame over the cloth, in the picture plane
    bw, bt, bb = P.get("banner_w", 9.0), P.get("banner_top", P["apex_z"] - 3), P.get("banner_bottom", P["apex_z"] - 20)
    d = 0.4; o3 = len(V)   # banner plate in the plane x + y = cx + cy (faces the viewer), width along (1, -1)
    for zz in (bb, bt):
        for t in (-1, 1):
            for e in (-d, d): V.append((cx + t * bw / 2 / math.sqrt(2) + e / math.sqrt(2), cy - t * bw / 2 / math.sqrt(2) + e / math.sqrt(2), zz))
    # vertices: (bb,-1,-d) 0 (bb,-1,+d) 1 (bb,+1,-d) 2 (bb,+1,+d) 3 (bt,-1,-d) 4 (bt,-1,+d) 5 (bt,+1,-d) 6 (bt,+1,+d) 7
    for q in ((0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6), (0, 1, 3, 2), (4, 6, 7, 5)): F.append(tuple(o3 + k for k in q))
with open(sys.argv[1], "w") as f:
    f.write("# canopies + banners of room 454 (remake/recipes/awning_454/awning.py), game coordinates\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
