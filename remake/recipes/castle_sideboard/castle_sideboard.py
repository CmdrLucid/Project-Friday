#!/usr/bin/env python3
"""castle_sideboard.py OUT.obj x0 y0 floor - the furniture row on the west wall of the castle bedrooms 67 / 77 (tileset 15, cells x 15, y 15..20): WARDROBE
(y 19..20, 48 high) + low BOOKCASE (y 16..18, 32 high) = their stepped collision boxes (fit the drawing), the NIGHTSTAND beside the bed (y 15) drawn ~21
high (collision 16), plus the vase and cup on the bookcase. Measured on rom_picture 67 by overlay. x0 / y0 = world units of the row's north-west corner
(67: 240, 240). GAME coordinates x east, y south, z up."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, os.path.join(HERE, "..", "castle_bench"))
from furniture import rbox, lathe
from castle_bench import write_obj

def parts(x0, y0, z0):
    X = lambda v: x0 + v; Y = lambda v: y0 + v
    return [rbox(X(0.0), X(16.0), Y(64.0), Y(96.0), z0, z0 + 48.0, 0.6, n=2),                # wardrobe
            rbox(X(0.0), X(16.0), Y(16.0), Y(64.0), z0, z0 + 32.0, 0.6, n=2),                # bookcase
            rbox(X(0.0), X(16.0), Y(0.0), Y(16.0), z0, z0 + 21.0, 0.6, n=2),                 # nightstand
            lathe(X(11.4), Y(47.4), z0 + 32.0, 12.0, [(0.0, 1.9), (0.3, 2.6), (0.6, 2.3), (0.8, 1.0), (1.0, 1.3)], seg=12),   # vase
            lathe(X(7.5), Y(51.5), z0 + 32.0, 4.5, [(0.0, 1.8), (1.0, 2.0)], seg=12)]                             # cup

if __name__ == "__main__":
    a = sys.argv; write_obj(a[1], parts(*map(float, a[2:5])), "castle sideboard row")
