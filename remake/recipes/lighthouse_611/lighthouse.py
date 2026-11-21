#!/usr/bin/env python3
"""lighthouse.py OUT.obj PARAMS.json : the LIGHTHOUSE of Ryuma (rooms 610 / 611, one map) as OUR OWN 3D model (2026-11-21): a square stone tower
(collision x 15..17, y 56..58, blocked 192 = up to the roof eave; a door niche in the east face at the walkable cell (17,57)) whose top is an open
lantern room: parapet, four corner posts with small arch brackets, a grey tile pyramid roof up to the apex, the beacon (a box with a flame cone) in
the middle. Read on the 1 px grid (roof eave z 192 at the tower's edge, apex 214, parapet top ~159). Edges chamfered >= 1 unit. Game coordinates."""
import json, math, sys
P = json.load(open(sys.argv[2])); V, F = [], []
def cbox(x0, y0, z0, x1, y1, z1, c=1.0):
    pts = [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]; o = len(V); n = 8
    V.extend([(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts])
    for i in range(n): F.append((o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i))
    F.append(tuple(o + i for i in range(n - 1, -1, -1))); F.append(tuple(o + n + i for i in range(n)))
X0, Y0, X1, Y1 = P["rect"]; G, ZF, ZP, ZE, ZA = P["ground"], P["floor"], P["parapet"], P["eave"], P["apex"]; T = P.get("wall", 3.0)
cbox(X0, Y0, G, X1, Y1, ZF)                                              # tower body up to the lantern room floor
for (a, b, c, d) in ((X0, Y0, X1, Y0 + T), (X0, Y1 - T, X1, Y1), (X0, Y0, X0 + T, Y1), (X1 - T, Y0, X1, Y1)): cbox(a, b, ZF, c, d, ZP, 0.6)   # parapet
PS = P.get("post", 4.0)
for sx, sy in ((X0, Y0), (X1 - PS, Y0), (X0, Y1 - PS), (X1 - PS, Y1 - PS)):
    cbox(sx, sy, ZP, sx + PS, sy + PS, ZE - 2.0, 1.0)                    # corner posts
    for dx, dy in ((1, 0), (0, 1)):   # arch brackets: small wedges under the eave towards the next post
        bx = sx + (PS if sx == X0 else -3.0) * dx; by = sy + (PS if sy == Y0 else -3.0) * dy
        if dx: cbox(min(bx, bx + 3), sy + 0.5, ZE - 6.0, max(bx, bx + 3), sy + PS - 0.5, ZE - 2.0, 0.5)
        else: cbox(sx + 0.5, min(by, by + 3), ZE - 6.0, sx + PS - 0.5, max(by, by + 3), ZE - 2.0, 0.5)
cbox(X0 - 0.5, Y0 - 0.5, ZE - 2.0, X1 + 0.5, Y1 + 0.5, ZE, 1.0)          # beam ring under the roof
ov = P.get("overhang", 1.0); cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2; o = len(V)
V.extend([(X0 - ov, Y0 - ov, ZE), (X1 + ov, Y0 - ov, ZE), (X1 + ov, Y1 + ov, ZE), (X0 - ov, Y1 + ov, ZE), (cx, cy, ZA)])
F.extend([(o, o + 1, o + 4), (o + 1, o + 2, o + 4), (o + 2, o + 3, o + 4), (o + 3, o, o + 4), (o, o + 3, o + 2, o + 1)])   # tile pyramid roof
bs = P.get("beacon", 8.0); cbox(cx - bs / 2, cy - bs / 2, ZF, cx + bs / 2, cy + bs / 2, ZF + P.get("beacon_h", 14.0), 1.0)
n = 12; o = len(V); zb = ZF + P.get("beacon_h", 14.0); r = bs / 2 - 1
for i in range(n): a = 2 * math.pi * i / n; V.append((cx + r * math.cos(a), cy + r * math.sin(a), zb))
V.append((cx, cy, zb + P.get("flame_h", 6.0)))
for i in range(n): F.append((o + i, o + (i + 1) % n, o + n))
F.append(tuple(o + i for i in range(n - 1, -1, -1)))
d = P.get("door")   # door niche on the east face: [y0, y1, z1, depth]
if d: cbox(X1 - d[3], d[0], G, X1 + 0.3, d[1], d[2], 0.4)
with open(sys.argv[1], "w") as f:
    f.write("# lighthouse of Ryuma (remake/recipes/lighthouse_611/lighthouse.py), game coordinates\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
