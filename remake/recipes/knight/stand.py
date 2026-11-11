#!/usr/bin/env python3
"""stand.py OUT.obj [params.json] : the ARMOUR ON A STAND of the castle (tileset 15, top block $0B5: rooms 63 64 83 84 93) as OUR OWN 3D model from parts
(user 2026-11-11 'ja mach diese Ruestung als naechstes'). Reference: room 63 cell (19, 28) on floor 32, window U0 1008 V0 280 (72 x 110), the armour's own
pixels = its layer A component. Read on the 1 px grid: no legs; a round stepped foot (radius 6) exactly on the cell centre, a thin pole, on it a fauld,
a breastplate with a round boss, a collar, a round helm with a visor, two big ball pauldrons high beside the helm, the arms hanging down past the fauld
with gauntlets. It stands at the west wall and faces the room (+x), turned ~11 degrees towards the camera (read from the line through the pauldrons).
The part makers come from knight.py (same folder). Pure Python, no ROM data."""
import os, sys
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "knight.py")).read().split("# ---- the figure")[0])
TW = 0.0
def T(p): return p
H = g('scale', 1.0)
lathe((0.0, 0.0), [(0.0, 6.7, 6.7), (0.7, 6.7, 6.7), (1.0, 5.9, 5.9), (1.2, 4.0, 4.0), (1.9, 3.8, 3.8), (2.3, 1.8, 1.8), (2.9, 0.95, 0.95)], nu=40)   # the stepped round foot
capsule((0.0, 0.0, 2.6), (0.0, 0.0, 13.5), 0.8, 0.8, nu=12, cap=2)                                                                               # the pole
BF = g('body_f', 0.3)
N0 = len(V)   # the armour hangs a little off the pole's axis (read from the drawing): everything from here on is shifted by `off` (s, f) at the end
lathe((0.0, BF), [(11.6, 5.7, 4.7), (12.4, 5.8, 4.8), (13.3, 5.5, 4.5), (13.4, 5.3, 4.35), (14.4, 5.4, 4.45), (15.2, 5.1, 4.2), (15.3, 4.95, 4.05), (16.3, 5.0, 4.1), (17.0, 4.6, 3.8)], sq=2.3)   # fauld: three hoops
lathe((0.0, BF), [(16.6, 4.6, 3.8), (17.2, 4.9, 4.0), (17.8, 4.6, 3.8), (18.6, 4.5, 3.75), (20.5, 5.3, 4.5), (23.0, 5.9, 4.9), (25.2, 5.7, 4.6), (26.6, 4.6, 3.8), (27.3, 3.3, 3.0)], sq=2.3)      # belt, waist, breastplate
ellipsoid((0.0, BF + 4.1, 21.2), (2.9, 1.5, 2.7))
for ts in (-2.5, 2.3): ellipsoid((ts, BF + 3.7, 9.8), (2.2, 1.0, 3.3))                                                                           # two tassets hanging from the fauld                                                                                                # the round boss on the breastplate
lathe((0.0, BF), [(26.8, 3.9, 3.7), (27.5, 4.2, 4.0), (28.2, 3.7, 3.5)], sq=2.0)                                                                 # the collar
HZ = g('helm_z', 27.6); HCU = (g('helm_s', 1.6), BF + 0.3)
lathe(HCU, [(HZ, 3.9, 4.1), (HZ + 0.8, 4.8, 5.0), (HZ + 3.2, 5.3, 5.5), (HZ + 5.4, 5.25, 5.45), (HZ + 7.4, 4.6, 4.8), (HZ + 9.0, 3.3, 3.5), (HZ + 10.0, 1.7, 1.8), (HZ + 10.4, 0.3, 0.3)], sq=2.0)   # the round helm
visor(HCU, 5.3, 5.5, HZ + 0.6, HZ + 6.2, g('visor_depth', 1.5), slit=(0.66, 0.82))
for sg in (-1, 1): ellipsoid((HCU[0] + sg * 5.6, HCU[1] + 0.8, HZ + 3.4), (0.45, 0.9, 0.9), nu=12, nv=8)                                           # the visor's pivots
for sg in (-1, 1):
    sh = (-8.4, BF, 30.6) if sg < 0 else (7.4, BF, 28.8)   # drawn unequal: the near one big and high, the far one small behind the helm
    ellipsoid(sh, (4.0, 4.0, 3.8) if sg < 0 else (2.9, 2.9, 2.7))                                                                                                              # the big ball pauldron, high beside the helm
    ellipsoid((sg * 8.5, BF, 26.6), (2.7, 2.8, 1.5))                                                                                             # a lame under it
    el = (sg * 8.9, BF + 0.4, 20.2); ha = (sg * 8.7, BF + 1.5, 12.6 if sg < 0 else 15.0)   # the far (left) arm is drawn shorter
    capsule((sg * 8.5, BF, 26.0), el, 2.0, 1.8); ellipsoid(el, (2.05, 2.1, 1.9)); capsule(el, ha, 1.75, 1.55)                                    # upper arm, couter, forearm
    capsule((ha[0], ha[1], ha[2] + 0.8), (ha[0], ha[1] + 0.3, ha[2] - 1.4), 2.0, 1.6, nu=14, cap=3)                                              # gauntlet cuff
    ellipsoid((ha[0], ha[1] + 0.5, ha[2] - 2.6), (1.6, 1.8, 1.7))                                                                                # the hanging hand
OFF = g('off', [-1.9, -0.4])
for k in range(N0, len(V)): V[k] = (V[k][0] + OFF[0], V[k][1] + OFF[1], V[k][2])
YAW = g('yaw', 79.0); ct, st = math.cos(math.radians(YAW)), math.sin(math.radians(YAW)); BX, BY = g('body', [0.0, 0.0])
CX, CY, FLO = g('cx', 312.0), g('cy', 456.0), g('floor', 32.0)
XMIN, XMAX, YMIN = g('xmin', -1e9), g('xmax', 1e9), g('ymin', -1e9)
def W(p):
    """body frame -> world; a vertex beyond xmin / xmax / ymin (a wall block beside the cell) slides along the view ray (1, 1, 1) back to the bound"""
    s, f, z = p; x, y, z = CX + BX + s * ct + f * st, CY + BY - s * st + f * ct, FLO + max(0.0, z) * H
    if x > XMAX: d = x - XMAX; x, y, z = x - d, y - d, z - d
    if x < XMIN: d = XMIN - x; x, y, z = x + d, y + d, z + d
    if y < YMIN: d = YMIN - y; x, y, z = x + d, y + d, z + d
    return (x, y, max(FLO, z))
with open(sys.argv[1], 'w') as fo:
    fo.write("# armour on a stand (remake/recipes/knight/stand.py): our own geometry from parts. GAME coordinates x east, y south, z up, world units.\n")
    for p in V: fo.write('v %.3f %.3f %.3f\n' % W(p))
    for q in F: fo.write('f ' + ' '.join(str(i + 1) for i in q) + '\n')
print('stand', len(V), 'verts', len(F), 'faces')
