#!/usr/bin/env python3
"""dead_twig.py OUT.obj VARIANT [X Y Z] : the DEAD SWAMP TWIGS (tileset 13, rooms 432 / 433 / 436 / 443 ...; user 2026-11-20 leftover list group (4):
'tote Sumpfbaeume') as OUR OWN 3D model: round branches (tubes, 12 sides: the light smooths normals within 35 deg, so they stay round) along the
skeleton read on the 1 px grid of the drawing. variants.json: per variant a list of branches, each a list of [dU, dV, r] points in PICTURE pixels
relative to the drawn foot (U right, V down) and the radius in world units. The branches lie in the picture plane (x = X + dU / 2, y = Y - dU / 2,
z = Z - dV: moving along the view ray changes nothing in the picture, so a flat skeleton is the honest reading). X Y Z = the foot in world units
(default 0 0 0). Pure Python, no ROM data."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
var = json.load(open(os.path.join(HERE, "variants.json")))[sys.argv[2]]
X, Y, Z = (float(a) for a in sys.argv[3:6]) if len(sys.argv) > 5 else (0.0, 0.0, 0.0)
NS = 12; V, F = [], []
def w(p): return (X + p[0] / 2.0, Y - p[0] / 2.0, Z - p[1])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def norm(a): l = math.sqrt(sum(t * t for t in a)) or 1.0; return tuple(t / l for t in a)
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
for br in var["branches"]:
    P = [w(p) for p in br]; R = [p[2] for p in br]; n = len(P); base = len(V); prev = None
    for i in range(n):
        d = norm(sub(P[min(i + 1, n - 1)], P[max(i - 1, 0)]))
        ref = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
        e1 = norm(cross(d, ref)) if prev is None else norm(sub(prev, tuple(d[k] * sum(prev[j] * d[j] for j in range(3)) for k in range(3))))   # parallel transport: no twist
        e2 = cross(d, e1); prev = e1
        for k in range(NS):
            a = 2 * math.pi * k / NS; V.append(tuple(P[i][j] + R[i] * (math.cos(a) * e1[j] + math.sin(a) * e2[j]) for j in range(3)))
    for i in range(n - 1):
        for k in range(NS): a = base + i * NS + k; b = base + i * NS + (k + 1) % NS; F.append((a, b, b + NS, a + NS))
    V.append(P[0]); c0 = len(V) - 1; V.append(P[-1]); c1 = len(V) - 1
    for k in range(NS): F.append((c0, base + (k + 1) % NS, base + k)); F.append((c1, base + (n - 1) * NS + k, base + (n - 1) * NS + (k + 1) % NS))
with open(sys.argv[1], "w") as f:
    f.write("# dead swamp twig '%s' (remake/recipes/dead_twig/dead_twig.py), foot at %g %g %g\n" % (sys.argv[2], X, Y, Z))
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
