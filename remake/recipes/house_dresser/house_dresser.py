#!/usr/bin/env python3
"""house_dresser.py OUT.obj x0 y0 floor - the CHEST OF DRAWERS + small BOOKCASE on the north wall of the Mercator houses 620 / 621 / 724 / 725 (tileset 2,
blocks $001 $02E $096 $0CC; cells x 17..20, y 15 = one 3 step = 48 high collision box): as drawn the drawers (3 cells, top 33, ~14 deep from the front)
and at the east end a bookcase cell 48 high (= its collision) with a vase on top; a bottle on the drawers. Measured on rom_picture 620 (corner points converted to world
units, U = x - y + 1184, V = (x + y) / 2 - z). x0 / y0 = world units of the box's north-west corner (620: 272, 240). GAME coordinates x east, y south, z up."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, os.path.join(HERE, "..", "castle_bench"))
from furniture import rbox, lathe
from castle_bench import write_obj

def parts(x0, y0, z0):
    X = lambda v: x0 + v; Y = lambda v: y0 + v
    return [rbox(X(0.0), X(48.0), Y(2.0), Y(16.0), z0, z0 + 33.0, 0.7, n=2),                  # chest of drawers
            rbox(X(48.0), X(64.0), Y(0.0), Y(16.0), z0, z0 + 48.0, 0.7, n=2),                 # bookcase (= the collision height)
            lathe(X(54.0), Y(2.5), z0 + 48.0, 9.0, [(0.0, 1.6), (0.35, 2.4), (0.75, 1.3), (1.0, 1.6)], seg=12),   # vase on the bookcase
            lathe(X(37.25), Y(8.75), z0 + 33.0, 6.0, [(0.0, 2.2), (0.6, 2.6), (0.85, 1.2), (1.0, 1.0)], seg=12),   # bottle on the drawers
            rbox(X(14.0), X(24.0), Y(9.5), Y(11.0), z0 + 33.0, z0 + 43.0, 0.3, n=1)]                             # picture frame on the drawers

if __name__ == "__main__":
    a = sys.argv; write_obj(a[1], parts(*map(float, a[2:5])), "house dresser")
