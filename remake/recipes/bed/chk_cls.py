#!/usr/bin/env python3
"""chk_cls.py OBJ PICDIR MASK.json [--map]: class-aware projection check (z-buffer along the view ray (1,1,1), U = x - y + 1184, V = (x + y) / 2 - z)
of an OBJ with groups 'wood' / 'cloth' against the drawn pixels: PICDIR = a remake/tools/rom_picture.py window (layerA.png + window.txt, local),
MASK.json = the object's window pixels (local). Drawn class from the colour: wood = the three browns, black = outline (matches either), else cloth.
Prints IoU (silhouette), class hits and with --map a character map (# right class, x wrong class, O model only, m drawing only)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")); from proxy_overlay import read_png
WOOD = {(144, 72, 0), (216, 144, 72), (72, 36, 0)}

def load_obj(path):
    V, T, g = [], [], "cloth"
    for l in open(path):
        if l.startswith("g "): g = l.split()[1]
        elif l.startswith("v "): V.append(tuple(map(float, l.split()[1:4])))
        elif l.startswith("f "):
            q = [int(t) - 1 for t in l.split()[1:]]
            T += [((V[q[0]], V[q[k]], V[q[k + 1]]), g) for k in range(1, len(q) - 1)]
    return T

def raster(T, U0, V0):
    Z = {}
    for (A, B, C), g in T:
        P = [(p[0] - p[1] + 1184 - U0, (p[0] + p[1]) / 2 - p[2] - V0, p[0] + p[1] + p[2]) for p in (A, B, C)]
        ar = (P[1][0] - P[0][0]) * (P[2][1] - P[0][1]) - (P[1][1] - P[0][1]) * (P[2][0] - P[0][0])
        if abs(ar) < 1e-9: continue
        for v in range(int(min(p[1] for p in P)), int(max(p[1] for p in P)) + 1):
            for u in range(int(min(p[0] for p in P)), int(max(p[0] for p in P)) + 1):
                x, y = u + .5, v + .5
                l1 = ((P[1][0] - x) * (P[2][1] - y) - (P[1][1] - y) * (P[2][0] - x)) / ar
                l2 = ((P[2][0] - x) * (P[0][1] - y) - (P[2][1] - y) * (P[0][0] - x)) / ar
                l3 = 1 - l1 - l2
                if min(l1, l2, l3) < -1e-6: continue
                d = l1 * P[0][2] + l2 * P[1][2] + l3 * P[2][2]
                if (u, v) not in Z or d > Z[(u, v)][0]: Z[(u, v)] = (d, g)
    return Z

def classes(picdir, mask):
    w, h, c, rows = read_png(os.path.join(picdir, "layerA.png")); out = {}
    for (u, v) in mask:
        col = tuple(rows[v][u * 4:u * 4 + 3]); out[(u, v)] = "wood" if col in WOOD else ("black" if col == (0, 0, 0) else "cloth")
    return out

def score(Z, K):
    M = set(K); R = set(Z); good = sum(1 for p in R & M if K[p] in ("black", Z[p][1]))
    return len(R & M) / len(R | M), good / len(R | M), len(R - M), len(M - R)

if __name__ == "__main__":
    U0, V0 = map(int, open(os.path.join(sys.argv[2], "window.txt")).read().split()[:2])
    K = classes(sys.argv[2], [tuple(p) for p in json.load(open(sys.argv[3]))]); Z = raster(load_obj(sys.argv[1]), U0, V0)
    s = score(Z, K); print("IoU %.3f  class-IoU %.3f  outside %d  missed %d" % s)
    if "--map" in sys.argv:
        A = set(K) | set(Z); us = [p[0] for p in A]; vs = [p[1] for p in A]
        for v in range(min(vs), max(vs) + 1):
            print("%3d " % v + "".join((("#" if K[(u, v)] in ("black", Z[(u, v)][1]) else "x") if (u, v) in K else "O") if (u, v) in Z else ("m" if (u, v) in K else ".") for u in range(min(us), max(us) + 1)))
