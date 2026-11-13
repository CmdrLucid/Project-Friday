#!/usr/bin/env python3
"""NEAR-FINAL laid DINING TABLE of Kayla's room (98, 99 variant; tileset 1, cells 21..23 x 21..23, floor 0): the approved castle table model
(remake/lib/furniture.py castle_table_mesh, reference room 96) + the dishes drawn on it, positions read off the picture on the table top plane z 16
(x - y = U - 1184, x + y = 2 (V + 16); proxy_overlay 5x, 2026-11-13): the MESSY table as drawn (user 2026-11-13: 'unordentlich, das Geschirr liegt kreuz und quer darauf und rundherum'): plates, small dishes,
cups, a tipped goblet on the table; bones, food scraps and two lying bottles on the floor around it (reliefs >= 1 unit; cutlery and the wine are paint).  Deco survey 2026-11-13 (HANDOFF -182).
  python3 remake/recipes/dining_table/dining98.py OUT.obj"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import furniture as F
X0, Y0, X1, Y1, FLOOR, TOP = 336, 336, 384, 384, 0, 16
# all positions read off the OBJECT layer (layer A) of the room picture, window U0 1094 V0 285 at 4x (pixel -> U = U0 + px / 4, V = V0 + py / 4),
# inverted on the plane they lie on (table top z 16, floor z 0): x = ((U - 1184) + 2 (V + z)) / 2, y = (2 (V + z) - (U - 1184)) / 2
U0, V0, S = 1094, 285, 4.0
def W(px, py, z):
    U = U0 + px / S; V = V0 + py / S; a = U - 1184; b = 2 * (V + z); return ((a + b) / 2, (b - a) / 2)
ON_TABLE = dict(plates=[(300, 232), (420, 262)], dishes=[(375, 188), (440, 218), (345, 282)], cups=[(406, 186), (470, 216)], small_cups=[(313, 275)],
                goblet=((308, 154), (346, 178)))           # the tipped goblet (foot at the second point), the red wine is paint
ON_FLOOR = dict(bones=[((210, 190), (228, 178)), ((433, 150), (452, 163)), ((588, 210), (604, 226)), ((106, 305), (126, 320)), ((146, 348), (163, 338)),
                       ((493, 340), (510, 352)), ((555, 370), (573, 382)), ((597, 310), (612, 322)), ((300, 405), (317, 412))],
                scraps=[(118, 250), (568, 282), (279, 378), (216, 410), (437, 410), (503, 378)],     # the yellow food scraps
                bottles=[((225, 355), (180, 378)), ((627, 262), (670, 284))])                          # lying blue bottles: bottom -> neck
def build():
    ms = F.castle_table_mesh(X0, Y0, X1, Y1, FLOOR, TOP, F.CASTLE_TABLE["thick"])
    T = ON_TABLE
    for p in T["plates"]: x, y = W(*p, TOP); ms.append(F.lathe(x, y, TOP, 1.2, [(0.0, 6.5), (0.5, 8.6), (1.0, 9.0), (1.0, 7.0)], seg=32))
    for p in T["dishes"]: x, y = W(*p, TOP); ms.append(F.lathe(x, y, TOP, 1.2, [(0.0, 2.6), (0.6, 3.6), (1.0, 3.8)], seg=20))
    for p in T["cups"]: x, y = W(*p, TOP); ms.append(F.lathe(x, y, TOP, 4.0, [(0.0, 1.8), (0.15, 1.9), (1.0, 2.3)], seg=16))
    for p in T["small_cups"]: x, y = W(*p, TOP); ms.append(F.lathe(x, y, TOP, 2.5, [(0.0, 1.4), (1.0, 1.8)], seg=16))
    (a, b) = T["goblet"]; xa, ya = W(*a, TOP + 2.0); xb, yb = W(*b, TOP + 2.0)
    ms.append(F.tube([(xa, ya, TOP + 2.0), ((xa + xb) / 2, (ya + yb) / 2, TOP + 1.8), (xb, yb, TOP + 1.2)], [2.4, 1.0, 1.8], seg=12))   # bowl -> stem -> foot, lying
    G = ON_FLOOR
    for a, b in G["bones"]:
        xa, ya = W(*a, 1.0); xb, yb = W(*b, 1.0)
        ms.append(F.tube([(xa, ya, 1.0), (xb, yb, 1.0)], [0.9, 0.9], seg=8))
        for x, y in ((xa, ya), (xb, yb)): ms.append(F.lathe(x, y, 0.0, 2.2, [(0.0, 0.6), (0.3, 1.3), (0.7, 1.3), (1.0, 0.5)], seg=10))   # knuckles
    for p in G["scraps"]: x, y = W(*p, 1.5); ms.append(F.lathe(x, y, 0.0, 2.6, [(0.0, 1.8), (0.4, 2.4), (0.8, 1.8), (1.0, 0.6)], seg=12))
    for a, b in G["bottles"]:
        xa, ya = W(*a, 2.6); xb, yb = W(*b, 2.6); dx, dy = xb - xa, yb - ya
        pts = [(xa + dx * t, ya + dy * t, 2.6) for t in (0.0, 0.55, 0.75, 1.0)]
        ms.append(F.tube(pts, [2.6, 2.6, 1.2, 1.1], seg=14))
    return ms
if __name__ == "__main__":
    import furniture_ops as fo
    open(sys.argv[1], "w").write(fo.lathe_obj(build(), "laid dining table (castle table + plates + cups), Kayla's room 98 / 99"))
    print("dining98 ->", sys.argv[1])
