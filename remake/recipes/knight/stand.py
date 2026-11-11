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
lathe((0.0, 0.0), [(0.0, 6.7, 6.7), (0.8, 6.7, 6.7), (1.1, 6.0, 6.0), (1.3, 4.2, 4.2), (2.1, 4.0, 4.0), (2.5, 2.2, 2.2), (3.3, 1.5, 1.5), (3.6, 1.05, 1.05)], nu=40)   # the stepped round foot
capsule((0.0, 0.0, 3.0), (0.0, 0.0, 14.5), 0.95, 0.95, nu=12, cap=2)
lathe((0.0, 0.0), [(6.6, 0.95, 0.95), (6.9, 1.55, 1.55), (7.5, 1.55, 1.55), (7.8, 0.95, 0.95)], nu=20)   # a turned collar on the pole (v2: the stand must read from the game view)
#                                                                              # the pole
BF = g('body_f', 0.3)
N0 = len(V)   # the armour hangs a little off the pole's axis (read from the drawing): everything from here on is shifted by `off` (s, f) at the end
# v2 (user: 'die Platten unten an der Ruestung sind noch nicht gut', 'der Staender ist aus der Spielperspektive kaum zu erkennen'): the fauld = a short bell
# of three overlapping lames (each a little wider than the one above, a step between), ending at z 12.8; the TASSETS hang at the two HIPS (pointed plates,
# turned outwards), not in front: the front stays open and the pole shows between them, as drawn
lathe((0.0, BF), [(12.8, 6.0, 5.0), (13.0, 6.1, 5.1), (14.3, 5.75, 4.8), (14.35, 5.45, 4.5), (15.6, 5.2, 4.3), (15.65, 4.95, 4.05), (16.8, 4.7, 3.85), (17.2, 4.5, 3.7)], sq=2.2)
TASSET = [(-2.5, 2.7), (-1.2, 3.0), (0.0, 3.1), (1.2, 3.0), (2.5, 2.7), (2.7, 1.0), (2.4, -0.8), (1.5, -2.4), (0.0, -3.6), (-1.5, -2.4), (-2.4, -0.8), (-2.7, 1.0)]
for sg in (-1, 1): plate((sg * 4.5, BF + 2.9, 10.3), sg * g('tasset_yaw', 40.0), TASSET, 0.75, bend=0.05, n=10)   # fauld: three hoops
lathe((0.0, BF), [(16.6, 4.6, 3.8), (17.2, 4.9, 4.0), (17.8, 4.6, 3.8), (18.6, 4.5, 3.75), (20.5, 5.3, 4.5), (23.0, 5.9, 4.9), (25.2, 5.7, 4.6), (26.6, 4.6, 3.8), (27.3, 3.3, 3.0)], sq=2.3)      # belt, waist, breastplate
ellipsoid((0.0, BF + 4.1, 21.2), (2.9, 1.5, 2.7))                                                                                                # the round boss on the breastplate
lathe((0.0, BF), [(26.6, 3.9, 3.7), (27.6, 4.3, 4.1), (28.6, 4.1, 3.9), (29.2, 3.6, 3.4)], sq=2.0)                                                                 # the collar
HZ = g('helm_z', 28.5); HCU = (g('helm_s', 0.0), BF + 0.3)   # v3 (user: 'Schultern sitzen zu hoch ... oder Kopf zu niedrig'): the helm a little higher on a taller collar, the pauldrons lower
lathe(HCU, [(HZ, 3.9, 4.1), (HZ + 0.8, 4.8, 5.0), (HZ + 3.2, 5.3, 5.5), (HZ + 5.4, 5.25, 5.45), (HZ + 7.4, 4.6, 4.8), (HZ + 9.0, 3.3, 3.5), (HZ + 10.0, 1.7, 1.8), (HZ + 10.4, 0.3, 0.3)], sq=2.0)   # the round helm
visor(HCU, 5.3, 5.5, HZ + 0.6, HZ + 6.2, g('visor_depth', 1.5), slit=(0.66, 0.82))
for sg in (-1, 1): ellipsoid((HCU[0] + sg * 5.6, HCU[1] + 0.8, HZ + 3.4), (0.45, 0.9, 0.9), nu=12, nv=8)                                           # the visor's pivots
for sg in (-1, 1):
    sh = (sg * 8.0, BF, g('pauldron_z', 26.9))   # v2 (user: 'richtig in 3D bauen'): SYMMETRIC; the far pauldron looks smaller in the game view because the helm hides part of it
    ellipsoid(sh, (3.7, 3.7, 3.5))                                                                                                              # the big ball pauldron, high beside the helm
    ellipsoid((sg * 8.5, BF, 24.0), (2.7, 2.8, 1.5))                                                                                             # a lame under it
    el = (sg * 8.9, BF + 0.4, 19.4); ha = (sg * 8.7, BF + 1.5, 12.8)
    capsule((sg * 8.5, BF, 24.6), el, 2.0, 1.8); ellipsoid(el, (2.05, 2.1, 1.9)); capsule(el, ha, 1.75, 1.55)                                    # upper arm, couter, forearm
    capsule((ha[0], ha[1], ha[2] + 0.8), (ha[0], ha[1] + 0.3, ha[2] - 1.4), 2.0, 1.6, nu=14, cap=3)                                              # gauntlet cuff
    ellipsoid((ha[0], ha[1] + 0.5, ha[2] - 2.6), (1.6, 1.8, 1.7))                                                                                # the hanging hand
OFF = g('off', [0.0, 0.0])   # v2: centred on the pole (the drawing shows it ~2 off; a real stand carries it in the middle)
for k in range(N0, len(V)): V[k] = (V[k][0] + OFF[0], V[k][1] + OFF[1], V[k][2])
YAW = g('yaw', 79.0); ct, st = math.cos(math.radians(YAW)), math.sin(math.radians(YAW)); BX, BY = g('body', [0.0, 0.0])
CX, CY, FLO = g('cx', 312.0), g('cy', 456.0), g('floor', 32.0)
XMIN, XMAX, YMIN, YMAX = g('xmin', -1e9), g('xmax', 1e9), g('ymin', -1e9), g('ymax', 1e9)
def W(p):
    """body frame -> world; a vertex beyond xmin / xmax / ymin (a wall block beside the cell) slides along the view ray (1, 1, 1) back to the bound"""
    s, f, z = p; x, y, z = CX + BX + s * ct + f * st, CY + BY - s * st + f * ct, FLO + max(0.0, z) * H
    if x > XMAX: d = x - XMAX; x, y, z = x - d, y - d, z - d
    if x < XMIN: d = XMIN - x; x, y, z = x + d, y + d, z + d
    if y < YMIN: d = YMIN - y; x, y, z = x + d, y + d, z + d
    if y > YMAX: d = y - YMAX; x, y, z = x - d, y - d, z - d
    return (x, y, max(FLO, z))
with open(sys.argv[1], 'w') as fo:
    fo.write("# armour on a stand (remake/recipes/knight/stand.py): our own geometry from parts. GAME coordinates x east, y south, z up, world units.\n")
    for p in V: fo.write('v %.3f %.3f %.3f\n' % W(p))
    for q in F: fo.write('f ' + ' '.join(str(i + 1) for i in q) + '\n')
print('stand', len(V), 'verts', len(F), 'faces')
