#!/usr/bin/env python3
"""railing_737.py [--ops] : the ROPE RAILINGS of room 737 (Kazalt outside) as real 3D light shapes -> landstalker/data/proxies/railing_737_*.obj (our own geometry, committed).
--ops prints the light_proxies.json ops for them (room 737 in landstalker/data/light_proxies.json holds them).

Measured on the drawn room picture (measure.py -> params.json, 73 posts; light variant = AS DRAWN, memory 'remake vs light variant'):
  * post (one drawing, mirrored copies): round shaft 5 px wide (r 1.75) and 16 high, a dark neck, a teal RING 8 px wide (r 2.7) 4 high where the rope runs through,
    a short neck and a round CAP 6 px wide / 6 high (ellipsoid r 2.1 x 3.0); 27 high from the foot (bug sweep 2026-11-26: the game's collision is a 2 step box strip
    under every railing = a hard edge through the sword glow on the path);
  * rope: teal, 2 px thick (r 0.9), from ring to ring at foot + 19.5, sagging 3.3 at the middle of a 32 unit span (drawn, between the posts at the door), sag ~ span^2;
  * feet: measure.py (view ray through the foot pixel; stair posts on their step).
Runs = straight railing strips (one light op each, floor = the walkway height 112 under posts and rope: air below the rope); every STAIR post is its own op with its step
height as floor (one floor per op), with the rope down to the next lower post.  Pure Python, no ROM.  Run from the repo root: python3 remake/recipes/railing_737/railing_737.py"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUTD = os.path.join(ROOT, "landstalker", "data", "proxies")
P = [(p["x"], p["y"], p["z"]) for p in json.load(open(os.path.join(HERE, "params.json")))["posts"]]
NU = 12
# profile of a post: (z above the foot, radius); the cap is an ellipsoid below
PROFILE = [(0.0, 1.75), (15.5, 1.75), (15.8, 1.5), (16.5, 1.5), (16.7, 2.3), (17.2, 2.7), (20.0, 2.7), (20.5, 2.3), (20.7, 1.6), (21.2, 1.6)]
CAP_C, CAP_RX, CAP_RZ = 24.0, 2.1, 3.0
ROPE_R, ROPE_UP, SAG32 = 0.9, 19.5, 3.3
# runs: name -> (post filter, strip cell rectangle [x0, y0, x1, y1], floor)
RUNS = {   # post filters with a tolerance of 2.5 units around the measured lines (2026-11-26: the posts moved 2 units when the axis was corrected)
    "a": (lambda x, y, z: abs(y - 383.25) < 2.5 and x < 700, [28, 24, 39, 24], 112, "upper walkway, left part (row 24 x 28..39) above the inner courtyard"),
    "b": (lambda x, y, z: abs(y - 387.25) < 2.5 and x > 700, [47, 24, 61, 24], 112, "upper walkway at the door (row 24 x 47..61), corner post of the descent included"),
    "c": (lambda x, y, z: abs(x - 754.75) < 2.5 or (abs(x - 762.75) < 2.5 and abs(y - 719.25) < 2.5), [47, 25, 47, 44], 112, "descent, outer side (x 47, rows 25..44)"),
    "d": (lambda x, y, z: 645.0 < y < 660.0 and x < 636.0, [24, 40, 39, 40], 112, "lower walkway, inner courtyard side (row 40 x 24..39)"),
    "e": (lambda x, y, z: abs(x - 638.75) < 2.5, [39, 25, 39, 39], 112, "inner courtyard, east side (x 39, rows 25..39; the posts stand on the walkway's edge)"),
    "f": (lambda x, y, z: abs(y - 807.25) < 2.5 or (abs(x - 765.75) < 2.5 and abs(y - 810.25) < 2.5), [20, 50, 47, 50], 112, "lower walkway, front (row 50 x 20..47)"),
}
STAIRS = (lambda x, y, z: abs(y - 799.25) < 2.5 or (abs(y - 719.25) < 2.5 and x > 770) or abs(x - 446.75) < 2.5)

V, F = [], []
def lathe(cx, cy, z0):
    rings = []
    for zz, r in PROFILE:
        o = len(V)
        for i in range(NU):
            t = 2 * math.pi * i / NU; V.append((cx + r * math.cos(t), cy + r * math.sin(t), z0 + zz))
        rings.append(o)
    zs = [21.2, 21.6, 22.2, 23.0, 24.0, 25.0, 25.8, 26.4, 26.8]
    for zz in zs:
        e = (zz - CAP_C) / CAP_RZ; r = CAP_RX   # cap: ellipsoid rings from the neck to the top * math.sqrt(max(0.0, 1 - e * e)); r = max(r, 1.6 if zz < CAP_C else 0.0)
        o = len(V)
        for i in range(NU):
            t = 2 * math.pi * i / NU; V.append((cx + r * math.cos(t), cy + r * math.sin(t), z0 + zz))
        rings.append(o)
    top = len(V); V.append((cx, cy, z0 + CAP_C + CAP_RZ))
    bot = len(V); V.append((cx, cy, z0))
    for a, b in zip(rings, rings[1:]):
        for i in range(NU):
            j = (i + 1) % NU; F.append((a + i, a + j, b + j)); F.append((a + i, b + j, b + i))
    for i in range(NU):
        j = (i + 1) % NU; F.append((rings[-1] + i, rings[-1] + j, top)); F.append((rings[0] + j, rings[0] + i, bot))
def rope(p, q):
    """a sagging rope (tube r ROPE_R) from post p's ring to post q's ring: parabola below the chord, sag = SAG32 * (horizontal span / 32)^2"""
    a = (p[0], p[1], p[2] + ROPE_UP); b = (q[0], q[1], q[2] + ROPE_UP); L = math.hypot(b[0] - a[0], b[1] - a[1]); sag = SAG32 * (L / 32.0) ** 2; n = 12
    pts = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t - 4 * sag * t * (1 - t)) for t in (k / n for k in range(n + 1))]
    rings = []
    for k, c in enumerate(pts):
        d = [pts[min(k + 1, n)][j] - pts[max(k - 1, 0)][j] for j in range(3)]; m = math.sqrt(sum(s * s for s in d)); d = [s / m for s in d]
        up = (0, 0, 1) if abs(d[2]) < 0.9 else (1, 0, 0)
        u = (d[1] * up[2] - d[2] * up[1], d[2] * up[0] - d[0] * up[2], d[0] * up[1] - d[1] * up[0]); mu = math.sqrt(sum(s * s for s in u)); u = [s / mu for s in u]
        w = (d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0])
        o = len(V)
        for i in range(8):
            t = 2 * math.pi * i / 8; V.append(tuple(c[j] + ROPE_R * (math.cos(t) * u[j] + math.sin(t) * w[j]) for j in range(3)))
        rings.append(o)
    for a2, b2 in zip(rings, rings[1:]):
        for i in range(8):
            j = (i + 1) % 8; F.append((a2 + i, a2 + j, b2 + j)); F.append((a2 + i, b2 + j, b2 + i))
def spans():
    """neighbouring posts: within 34 (x y), no other post on the way (detour < 25 %: stairs 16 apart skip the 32 pair, corners link through the corner post)"""
    out = []
    for i, p in enumerate(P):
        for j, q in enumerate(P):
            if j <= i: continue
            dx, dy = q[0] - p[0], q[1] - p[1]; L = math.hypot(dx, dy)
            if L > 34.0 or L < 4.0: continue
            if any(k not in (i, j) and math.hypot(r[0] - p[0], r[1] - p[1]) + math.hypot(q[0] - r[0], q[1] - r[1]) < 1.25 * L for k, r in enumerate(P)): continue   # another post (nearly) on the way: corners / stairs link through it
            out.append((i, j))
    return out
def write(name, idx, sp, why):
    V.clear(); F.clear()
    for i in idx: lathe(*P[i])
    for i, j in sp: rope(P[i], P[j])
    path = os.path.join(OUTD, "railing_737_%s.obj" % name)
    with open(path, "w") as f:
        f.write("# room 737 rope railing '%s' (%s): %d posts, %d rope spans; remake/recipes/railing_737/railing_737.py, light variant as drawn\n" % (name, why, len(idx), len(sp)))
        for v in V: f.write("v %.3f %.3f %.3f\n" % v)
        for a, b, c in F: f.write("f %d %d %d\n" % (a + 1, b + 1, c + 1))
    return path
def main():
    S = spans(); owner = {}; ops = []
    for name, (flt, rect, fl, why) in RUNS.items():
        for i, p in enumerate(P):
            if flt(*p) and not STAIRS(*p): owner.setdefault(i, name)
    for i, p in enumerate(P):
        if STAIRS(*p) and i not in owner: owner[i] = "s%02d" % i
    miss = [i for i in range(len(P)) if i not in owner]
    if miss: print("posts without a run:", [P[i] for i in miss]); sys.exit(1)
    groups = {}
    for i, g in owner.items(): groups.setdefault(g, []).append(i)
    for g, idx in sorted(groups.items()):
        sp = [(i, j) for i, j in S if owner[i] == g and (owner[j] == g or P[i][2] >= P[j][2]) or owner[j] == g and owner[i] != g and P[j][2] > P[i][2]]   # a span belongs to the run of both posts, else to the HIGHER post's
        if g in RUNS: rect, fl, why = RUNS[g][1], RUNS[g][2], RUNS[g][3]
        else:
            x, y, z = P[idx[0]]; why = "stair post on its step %d" % z; fl = int(z)
            rect = [int(x // 16), int(y // 16), int(x // 16), int(y // 16)]
            if abs(y - 799.25) < 2.5: rect[3] += 1   # the south stair's posts stand on the step (row 49), their collision strip is the cell in front (row 50)
        path = write(g, idx, sp, why)
        ops.append({"op": "mesh", "cells": rect, "file": "proxies/" + os.path.basename(path), "surface": True, "floor": fl,
                    "why": "ROPE RAILING '%s': %s; remake/recipes/railing_737 (posts with cap / ring / shaft measured on the drawing, ropes sagging as drawn); the game's 2 step collision strip goes (bug sweep 2026-11-26, sword glow edge on the path)" % (g, why)})
        print("%-4s %2d posts %2d spans floor %3d cells %s -> %s" % (g, len(idx), len(sp), fl, rect, os.path.basename(path)))
    cnt = {}
    for g, idx in groups.items():
        for i, j in S:
            if (owner[i] == g and (owner[j] == g or P[i][2] >= P[j][2])) or (owner[j] == g and owner[i] != g and P[j][2] > P[i][2]): cnt[(i, j)] = cnt.get((i, j), 0) + 1
    bad = [(sp, cnt.get(sp, 0)) for sp in S if cnt.get(sp, 0) != 1]
    print("%d posts, %d rope spans%s" % (len(P), len(S), ", every span in exactly one model" if not bad else ", SPAN PROBLEM: %s" % bad))
    if "--ops" in sys.argv: print(json.dumps(ops))
main()
