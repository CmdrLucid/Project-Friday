#!/usr/bin/env python3
"""chk.py OBJ MASK.json U0 V0 [W H]: projection of the model against the drawn pixels (U = x - y + 1184, V = (x + y) / 2 - z): drawn / covered / outside /
missed / IoU + a character map (# both, O model only, m drawing only). MASK.json = window pixels of the object (local, from the user's ROM, never in git)."""
import json, sys
mask = {tuple(p) for p in json.load(open(sys.argv[2]))}; U0, V0 = int(sys.argv[3]), int(sys.argv[4])
V, Fc = [], []
for l in open(sys.argv[1]):
    if l.startswith('v '): V.append(tuple(map(float, l.split()[1:4])))
    elif l.startswith('f '): Fc.append([int(t) - 1 for t in l.split()[1:]])
proj = lambda p: (p[0] - p[1] + 1184, (p[0] + p[1]) / 2 - p[2]); c = set()
for f in Fc:
    pts = [proj(V[i]) for i in f]
    for t in range(1, len(pts) - 1):
        A, B, C = pts[0], pts[t], pts[t + 1]
        e = lambda P1, P2, x, y: (P2[0] - P1[0]) * (y - P1[1]) - (P2[1] - P1[1]) * (x - P1[0]); ar = e(A, B, C[0], C[1])
        if abs(ar) < 1e-9: continue
        for vv in range(int(min(A[1], B[1], C[1])), int(max(A[1], B[1], C[1])) + 1):
            for uu in range(int(min(A[0], B[0], C[0])), int(max(A[0], B[0], C[0])) + 1):
                x, y = uu + .5, vv + .5
                if e(B, C, x, y) / ar >= -1e-6 and e(C, A, x, y) / ar >= -1e-6 and e(A, B, x, y) / ar >= -1e-6: c.add((uu - U0, vv - V0))
print('drawn', len(mask), 'cov', len(c), 'outside', len(c - mask), 'missed', len(mask - c), 'IoU %.3f' % (len(c & mask) / len(c | mask)))
us = [p[0] for p in mask | c]; vs = [p[1] for p in mask | c]
for v in range(min(vs), max(vs) + 1): print('%3d ' % v + ''.join(('#' if (u, v) in mask else 'O') if (u, v) in c else ('m' if (u, v) in mask else '.') for u in range(min(us), max(us) + 1)))
