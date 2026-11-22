#!/usr/bin/env python3
"""well.py OUT.obj PARAMS.json : the WELL HOIST and the TUB of Mercator (room 632): a square stone well rim (walkable 32 around a water hole, the
collision) carries at its back a wooden hoist (square post, crossbar along +x, a diagonal brace, a rope with two weights hanging into the well) and
a wooden tub (staved, slightly widening upwards, rim). Read on the 1 px grid with both planes (2026-11-21; first taken for a lantern on a wall).
Round parts 12 sides (smooth in the light). Game coordinates. Pure Python, no ROM data."""
import json, math, sys
P = json.load(open(sys.argv[2])); V, F = [], []
def box(x0, y0, z0, x1, y1, z1):
    o = len(V); V.extend([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
    F.extend([(o, o + 3, o + 2, o + 1), (o + 4, o + 5, o + 6, o + 7), (o, o + 1, o + 5, o + 4), (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7)])
def lathe(cx, cy, prof, n=12):
    o = len(V)
    for z, r in prof:
        for i in range(n): a = 2 * math.pi * i / n; V.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    for j in range(len(prof) - 1):
        for i in range(n): a = o + j * n + i; b = o + j * n + (i + 1) % n; F.append((a, b, b + n, a + n))
    V.append((cx, cy, prof[0][0])); V.append((cx, cy, prof[-1][0])); c0, c1 = len(V) - 2, len(V) - 1; k = len(prof)
    for i in range(n): F.append((c0, o + (i + 1) % n, o + i)); F.append((c1, o + (k - 1) * n + i, o + (k - 1) * n + (i + 1) % n))
H = P["hoist"]; px, py, z0, zt, w = H["x"], H["y"], H["z0"], H["top"], H.get("w", 2.4); L = H.get("bar", 9.0)
box(px - w / 2, py - w / 2, z0, px + w / 2, py + w / 2, zt)                         # post
LB = H.get("bar_back", 5.0); box(px - LB, py - w / 2 + 0.3, zt - 2.0, px + L, py + w / 2 - 0.3, zt)   # crossbar along x, over both sides of the post
for k in range(5):   # diagonal brace on the BACK side (-x, as drawn) from the post (zt - 9) to the bar end: a chain of small boxes
    t0, t1 = k / 5, (k + 1) / 5; xa, xb = px - w / 2 - (LB - 0.6) * t0, px - w / 2 - (LB - 0.6) * t1; za, zb = zt - 9 + 7 * t0, zt - 9 + 7 * t1
    box(min(xa, xb) - 0.6, py - 0.6, min(za, zb), max(xa, xb), py + 0.6, max(za, zb) + 1.2)
rx = px + L - 1.0; box(rx - 0.35, py - 0.35, H.get("rope_low", 20.0), rx + 0.35, py + 0.35, zt - 2.0)   # rope
for zw in H.get("weights", [52.0, 46.0]): lathe(rx, py, [(zw - 1.6, 0.4), (zw - 1.0, 1.2), (zw + 1.0, 1.2), (zw + 1.6, 0.4)])
T = P["tub"]; tx, ty, tz, th, r0, r1 = T["x"], T["y"], T["z0"], T["h"], T["r0"], T["r1"]
lathe(tx, ty, [(tz, r0 - 0.3), (tz + 0.8, r0), (tz + th - 1.2, r1), (tz + th - 1.2, r1 + 0.5), (tz + th, r1 + 0.5), (tz + th, r1 - 0.6), (tz + th - 2.5, r1 - 0.8)])
with open(sys.argv[1], "w") as f:
    f.write("# well hoist + tub of room 632 (remake/recipes/well_632/well.py), game coordinates\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
