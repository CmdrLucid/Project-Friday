#!/usr/bin/env python3
"""pavilion.py OUT.obj [params.json] : the LOG HUT on stilts over the water (first read as an open pavilion from plane A alone) of the Mercator docks (rooms 641 / 642 / 644) as OUR OWN 3D model, read on the
1 px grid of plane A (2026-11-21): a square thatched roof (half side a ~31, a low pyramid up to a knob, a green fascia band at the eave) on three corner
pillars that are LOG CRIBS (horizontal round logs crossing in alternating directions: the drawn chevrons of the front pillar). Two pillars stand in the
water (floor 8), the right one on the pier (16); the collision is only three single high cells, so the footprint is measured on the drawing:
roof centre x 750.5 y 559.5, eave z 77, knob top z ~107. Game coordinates. Round parts 12 sides (smooth in the light). Pure Python, no ROM data."""
import json, math, sys
P = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
g = lambda k, d: P.get(k, d)
CX, CY = g("cx", 750.5), g("cy", 559.5); A = g("a", 31.0); ZE = g("eave", 77.0); ZAP = g("apex", 100.0); ZK = g("knob_top", 107.0)
PS = g("pillar", 14.0); LD = g("log_d", 3.6); FAS = g("fascia_h", 4.0); TH = g("thatch", 3.0); OVH = g("overhang", 0.0)
FLOORS = g("floors", {"left": 8.0, "front": 8.0, "right": 16.0, "back": 8.0})
V, F = [], []
def add(vs, fs): o = len(V); V.extend(vs); F.extend([tuple(i + o for i in fc) for fc in fs])
def box(x0, y0, z0, x1, y1, z1):
    add([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
def log(p0, p1, r, n=12):   # a round log along x or y, closed ends
    ax = 0 if abs(p1[0] - p0[0]) > abs(p1[1] - p0[1]) else 1; vs = []; fs = []
    for e in (p0, p1):
        for i in range(n):
            t = 2 * math.pi * i / n; u, w = r * math.cos(t), r * math.sin(t)
            vs.append((e[0], e[1] + u, e[2] + w) if ax == 0 else (e[0] + u, e[1], e[2] + w))
    for i in range(n): fs.append((i, (i + 1) % n, n + (i + 1) % n, n + i))
    vs.append(p0); vs.append(p1); c0, c1 = 2 * n, 2 * n + 1
    for i in range(n): fs.append((c0, (i + 1) % n, i)); fs.append((c1, n + i, n + (i + 1) % n))
    add(vs, fs)
# LOG HUT ON STILTS (2026-11-21, user: look at BOTH planes: plane B holds the dark interior and the back walls): four log-crib corners on the floor,
# the two back walls closed (round logs, alternating with the corners' notches), the two front walls with big openings (a sill log on the floor, the
# fascia above), a floor deck at the pier's height and short round stilts under the corners down to the water
ZF = g("floor", 16.0); ZW = g("water", 8.0); r = LD / 2
cpos = {"left": (-1, 1), "front": (1, 1), "right": (1, -1), "back": (-1, -1)}
for name, (sx, sy) in cpos.items():
    px, py = CX + sx * (A - PS / 2), CY + sy * (A - PS / 2); z = ZF; k = 0
    while z + r < ZE - FAS:
        zc = z + r
        if k % 2 == 0:
            for oy in (-1, 1): log((px - PS / 2 - 0.5, py + oy * (PS / 2 - r), zc), (px + PS / 2 + 0.5, py + oy * (PS / 2 - r), zc), r)
        else:
            for ox in (-1, 1): log((px + ox * (PS / 2 - r), py - PS / 2 - 0.5, zc), (px + ox * (PS / 2 - r), py + PS / 2 + 0.5, zc), r)
        z += LD * 0.5; k += 1
for name, (sx, sy) in cpos.items():   # stilts (vertical round posts) under the corners, except the right one that stands on the pier
    if name == "right": continue
    px, py = CX + sx * (A - PS / 2), CY + sy * (A - PS / 2); sr = g("stilt_r", 2.0); n = 12; o = len(V)
    for zz in (ZW, ZF):
        for i in range(n): t = 2 * math.pi * i / n; V.append((px + sr * math.cos(t), py + sr * math.sin(t), zz))
    for i in range(n): F.append((o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i))
inner = A - PS   # half length of a wall between the corners
z = ZF + r; k = 0
while z < ZE - FAS:   # back walls: logs along x at y = CY - A + r (the -y side) and along y at x = CX - A + r (the -x side)
    log((CX - inner, CY - A + r, z), (CX + inner, CY - A + r, z), r); log((CX - A + r, CY - inner, z), (CX - A + r, CY + inner, z), r); z += LD
for (a0, b0, along_x) in ((CX - inner, CX + inner, True), (CY - inner, CY + inner, False)):   # front walls: only the sill log on the floor
    if along_x: log((a0, CY + A - r, ZF + r), (b0, CY + A - r, ZF + r), r)
    else: log((CX + A - r, a0, ZF + r), (CX + A - r, b0, ZF + r), r)
box(CX - A, CY - A, ZF - 2.0, CX + A, CY + A, ZF)   # floor deck
# fascia band under the eave and the roof slab
e = A + OVH
box(CX - e, CY - e, ZE - FAS, CX + e, CY + e, ZE + TH)   # fascia band + the thatch's own thickness at the eave
# thatch roof: four faces from the eave square to the apex, each a grid bulging outwards by `bulge` (thatch is convex), closed underneath by the fascia
BUL = g("bulge", 2.0); NG = 6
def rp(u, w, side):   # u along the eave (0..1), w up the face (0 = eave .. 1 = apex) -> point
    c4 = [(CX - e, CY - e), (CX + e, CY - e), (CX + e, CY + e), (CX - e, CY + e)]; p0, p1 = c4[side], c4[(side + 1) % 4]
    ex, ey = p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u
    x, y = ex + (CX - ex) * w, ey + (CY - ey) * w; z = ZE + TH + (ZAP - ZE - TH) * w
    b = BUL * math.sin(math.pi * u) * math.sin(math.pi * w) if 0 < w < 1 else 0.0   # hips (u = 0 / 1) and apex stay on the straight lines
    return (x, y, z + b)
for side in range(4):
    o = len(V)
    for jw in range(NG + 1):
        for iu in range(NG + 1): V.append(rp(iu / NG, jw / NG, side))
    for jw in range(NG):
        for iu in range(NG): a = o + jw * (NG + 1) + iu; F.append((a, a + 1, a + NG + 2, a + NG + 1))
o = len(V); V.extend([(CX - e, CY - e, ZE + TH), (CX + e, CY - e, ZE + TH), (CX + e, CY + e, ZE + TH), (CX - e, CY + e, ZE + TH)]); F.append((o, o + 3, o + 2, o + 1))
# knob: a small bundle on the apex
kr = g("knob_r", 3.0); n = 12; o = len(V)
for j in range(1, 6):
    ph = math.pi * j / 6
    for i in range(n): t = 2 * math.pi * i / n; V.append((CX + kr * math.sin(ph) * math.cos(t), CY + kr * math.sin(ph) * math.sin(t), (ZAP + ZK) / 2 + (ZK - ZAP) / 2 * math.cos(ph)))
V.append((CX, CY, ZK)); V.append((CX, CY, ZAP)); top, bot = len(V) - 2, len(V) - 1
for i in range(n): F.append((top, o + i, o + (i + 1) % n)); F.append((bot, o + 4 * n + (i + 1) % n, o + 4 * n + i))
for j in range(4):
    for i in range(n): a = o + j * n + i; b = o + j * n + (i + 1) % n; F.append((a, a + n, b + n, b))
with open(sys.argv[1], "w") as f:
    f.write("# pavilion of the Mercator docks (remake/recipes/pavilion_641/pavilion.py), game coordinates\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
