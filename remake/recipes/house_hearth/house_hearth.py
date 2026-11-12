#!/usr/bin/env python3
"""house_hearth.py OUT.obj x0 y0 floor - the HEARTH corner of the Mercator houses 691 / 692 / 713 / 714 (tileset 2, blocks $166 $185 $17A $188; cells
x 13, y 12..14 = a 2 step collision box): the brick hearth (the box, fire opening on its east face) with a KETTLE and a small crate on top, and above it
the WALL SHELF on the west wall (x 208..222, z 60..64; NOT in the collision at all, so the light had no shelf) with two plate stacks and a bottle.
Measured on rom_picture 691 (corner points converted to world units, U = x - y + 1184, V = (x + y) / 2 - z). x0 / y0 = world units of the hearth
column's north-west corner (691: 208, 192). GAME coordinates x east, y south, z up."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, os.path.join(HERE, "..", "castle_bench"))
from furniture import rbox, lathe
from castle_bench import write_obj

KETTLE = [(0.0, 4.5), (0.2, 7.0), (0.55, 7.6), (0.85, 6.8), (1.0, 7.2)]
PLATES = [(0.0, 4.5), (0.2, 5.5), (1.0, 5.5)]

def parts(x0, y0, z0):
    X = lambda v: x0 + v; Y = lambda v: y0 + v
    return [rbox(X(0.0), X(16.0), Y(0.0), Y(48.0), z0, z0 + 32.0, 0.6, n=2),                 # brick hearth = the collision box
            lathe(X(10.0), Y(26.0), z0 + 32.0, 11.0, KETTLE),                                # kettle on the hearth
            rbox(X(2.0), X(10.0), Y(0.0), Y(7.0), z0 + 32.0, z0 + 39.0, 0.4, n=1),          # small crate at the back
            rbox(X(0.0), X(14.0), Y(0.0), Y(48.0), z0 + 60.0, z0 + 64.0, 0.6, n=2),         # wall shelf
            lathe(X(4.0), Y(34.5), z0 + 64.0, 6.0, PLATES, seg=16), lathe(X(5.0), Y(14.0), z0 + 64.0, 6.0, PLATES, seg=16),
            lathe(X(8.0), Y(29.0), z0 + 64.0, 12.0, [(0.0, 1.8), (0.7, 1.9), (0.85, 1.0), (1.0, 1.0)], seg=12)]   # bottle

if __name__ == "__main__":
    a = sys.argv; write_obj(a[1], parts(*map(float, a[2:5])), "house hearth corner")
