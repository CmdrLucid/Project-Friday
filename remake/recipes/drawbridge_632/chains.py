#!/usr/bin/env python3
"""chains.py OUT.obj PARAMS.json : the two CHAINS of the Mercator castle drawbridge (room 632) as OUR OWN 3D model (2026-11-21): the bridge deck is
walkable floor (collision x 37..40, y 16..19, height 16; plane B), the chains (plane A) run from the deck's outer end (y 320, z ~25) up to the castle
wall face above the gate (y 224, z ~69); the right chain's both ends land on the deck edge x 656 (measured), the left one on x 592. Each chain = links
(elongated rings as flat ellipsoids) every `step`, turned 90 deg in turn. Game coordinates. Pure Python, no ROM data."""
import json, math, sys
P = json.load(open(sys.argv[2])); V, F = [], []
def link(c, d, up, a, b, t, nu=10, nv=6):
    """flat ellipsoid: half length a along d, half width b along up, half thickness t along d x up"""
    s = (d[1] * up[2] - d[2] * up[1], d[2] * up[0] - d[0] * up[2], d[0] * up[1] - d[1] * up[0])
    o = len(V)
    V.append(tuple(c[k] + a * d[k] for k in range(3)))
    for j in range(1, nv):
        ph = math.pi * j / nv
        for i in range(nu):
            th = 2 * math.pi * i / nu; ca, cb, ct = math.cos(ph) * a, math.sin(ph) * math.cos(th) * b, math.sin(ph) * math.sin(th) * t
            V.append(tuple(c[k] + ca * d[k] + cb * up[k] + ct * s[k] for k in range(3)))
    V.append(tuple(c[k] - a * d[k] for k in range(3))); last = len(V) - 1
    for i in range(nu): F.append((o, o + 1 + i, o + 1 + (i + 1) % nu)); F.append((last, o + 1 + (nv - 2) * nu + (i + 1) % nu, o + 1 + (nv - 2) * nu + i))
    for j in range(nv - 2):
        for i in range(nu): p = o + 1 + j * nu + i; q = o + 1 + j * nu + (i + 1) % nu; F.append((p, p + nu, q + nu, q))
for p0, p1 in P["chains"]:
    dv = [p1[k] - p0[k] for k in range(3)]; L = math.sqrt(sum(x * x for x in dv)); d = [x / L for x in dv]
    up1 = (0.0, 0.0, 1.0); up1 = [up1[k] - d[k] * sum(up1[j] * d[j] for j in range(3)) for k in range(3)]; l = math.sqrt(sum(x * x for x in up1)); up1 = [x / l for x in up1]
    up2 = (d[1] * up1[2] - d[2] * up1[1], d[2] * up1[0] - d[0] * up1[2], d[0] * up1[1] - d[1] * up1[0])
    n = max(2, int(L / P.get("step", 2.6))); 
    for k in range(n + 1):
        c = [p0[j] + dv[j] * k / n for j in range(3)]
        link(c, d, up1 if k % 2 == 0 else up2, P.get("a", 1.8), P.get("b", 1.0), P.get("t", 0.45))
with open(sys.argv[1], "w") as f:
    f.write("# drawbridge chains of room 632 (remake/recipes/drawbridge_632/chains.py), game coordinates\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
