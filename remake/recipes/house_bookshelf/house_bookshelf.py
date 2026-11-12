#!/usr/bin/env python3
"""house_bookshelf.py OUT.obj x0 y0 floor - the BOOKSHELF corner of the Mercator houses 693 / 715 / 716 (tileset 2): the bookshelf on the north wall
(cells x 13..17, y 12, 48 high = its collision box, fits the drawing) with a tall bottle, a picture frame and a crate on top, and the small SIDE TABLE in
front of its west end (cell 13, 13; collision a solid 1 step box) as a slab 12..16 on four straight legs (r 1.8, ~3 in) with a vase. Measured on
rom_picture 693 (corner points converted to world units, U = x - y + 1184, V = (x + y) / 2 - z). x0 / y0 = world units of the shelf's north-west
corner (693: 208, 192). GAME coordinates x east, y south, z up."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, os.path.join(HERE, "..", "castle_bench"))
sys.path.insert(0, os.path.join(HERE, "..", "kitchen_table"))
from furniture import rbox, lathe
from castle_bench import write_obj
import kitchen_table

def parts(x0, y0, z0):
    X = lambda v: x0 + v; Y = lambda v: y0 + v
    out = [rbox(X(0.0), X(80.0), Y(0.0), Y(16.0), z0, z0 + 48.0, 0.6, n=2),                                   # bookshelf
           lathe(X(7.0), Y(3.0), z0 + 48.0, 13.0, [(0.0, 1.9), (0.7, 2.0), (0.85, 1.0), (1.0, 1.0)], seg=12), # tall bottle
           rbox(X(41.0), X(51.0), Y(12.0), Y(13.5), z0 + 48.0, z0 + 58.0, 0.3, n=1),                         # picture frame
           rbox(X(60.5), X(68.5), Y(4.5), Y(12.5), z0 + 48.0, z0 + 55.0, 0.4, n=1)]                          # crate
    for cx, cy in ((14.3, 11.1), (22.0, 3.4), (30.4, 11.7)):                                                    # three small grey boxes on top
        out.append(rbox(X(cx - 2.0), X(cx + 2.0), Y(cy - 2.0), Y(cy + 2.0), z0 + 48.0, z0 + 51.0, 0.3, n=1))
    out += kitchen_table.parts(X(0.0), X(16.0), Y(16.0), Y(32.0), z0, 16.0, 4.0, 3.0, 1.8)                   # side table
    out.append(lathe(X(2.5), Y(22.5), z0 + 16.0, 10.0, [(0.0, 1.6), (0.3, 2.2), (0.6, 2.0), (0.8, 0.9), (1.0, 1.2)], seg=12))   # vase
    return out

if __name__ == "__main__":
    a = sys.argv; write_obj(a[1], parts(*map(float, a[2:5])), "house bookshelf corner")
