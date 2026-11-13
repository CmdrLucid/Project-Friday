#!/usr/bin/env python3
"""NEAR-FINAL laid DINING TABLE of Kayla's room (98, 99 variant; tileset 1, cells 21..23 x 21..23, floor 0): the approved castle table model
(remake/lib/furniture.py castle_table_mesh, reference room 96) + the dishes drawn on it, positions read off the picture on the table top plane z 16
(x - y = U - 1184, x + y = 2 (V + 16); proxy_overlay 5x, 2026-11-13): two plates with food (diameter 18, 1.2 high: reliefs >= 1 unit, no dotted light
lines), two glass cups (r 2.2, 4 high) at the back.  Bones / cutlery / the bottle on the floor are paint.  Deco survey 2026-11-13 (HANDOFF -182).
  python3 remake/recipes/dining_table/dining98.py OUT.obj"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib")); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import furniture as F
X0, Y0, X1, Y1, FLOOR, TOP = 336, 336, 384, 384, 0, 16
PLATES = [(351.0, 367.0), (375.0, 359.0)]
CUPS = [(353.5, 342.0), (369.0, 341.5)]
def build():
    ms = F.castle_table_mesh(X0, Y0, X1, Y1, FLOOR, TOP, F.CASTLE_TABLE["thick"])
    for x, y in PLATES: ms.append(F.lathe(x, y, TOP, 1.2, [(0.0, 6.5), (0.5, 8.6), (1.0, 9.0), (1.0, 7.0)], seg=32))
    for x, y in CUPS: ms.append(F.lathe(x, y, TOP, 4.0, [(0.0, 1.8), (0.15, 1.9), (1.0, 2.3)], seg=16))
    return ms
if __name__ == "__main__":
    import furniture_ops as fo
    open(sys.argv[1], "w").write(fo.lathe_obj(build(), "laid dining table (castle table + plates + cups), Kayla's room 98 / 99"))
    print("dining98 ->", sys.argv[1])
