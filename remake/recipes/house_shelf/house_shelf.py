#!/usr/bin/env python3
"""house_shelf.py OUT.obj x0 y0 floor - the north-east corner of the Mercator houses 691 / 692 / 713 / 714 (tileset 2, blocks $00D $00E $326; cells
x 17..19, y 12 = ONE collision column 4 steps = 64 high, which the light saw as a solid wall block): as drawn it holds a CLAY JAR on the floor (cell 17),
a low GLASS CABINET (x 290..320, 16 deep, 32 high) with a small vase and a box on top, and a WALL SHELF (whole cell deep, z 60..64, on two brackets) with a
stack of plates; between them AIR in front of the wall. Measured on rom_picture 691 (corner points converted to world units: U = x - y + 1184,
V = (x + y) / 2 - z). x0 / y0 = world units of the column's north-west corner (691: 272, 192). GAME coordinates x east, y south, z up."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, os.path.join(HERE, "..", "castle_bench"))
from furniture import rbox, lathe
from castle_bench import write_obj

JAR = [(0.0, 4.0), (0.15, 6.5), (0.45, 7.0), (0.75, 5.5), (0.88, 3.6), (1.0, 4.2)]

def parts(x0, y0, z0):
    X = lambda v: x0 + v; Y = lambda v: y0 + v
    out = [lathe(X(8.0), Y(13.0), z0, 22.0, JAR),                                        # clay jar on the floor, in front of the cabinet's left
           rbox(X(18.0), X(48.0), Y(0.0), Y(16.0), z0, z0 + 32.0, 0.8, n=2),             # glass cabinet
           rbox(X(37.0), X(45.0), Y(5.0), Y(13.0), z0 + 32.0, z0 + 39.0, 0.4, n=1),      # box on the cabinet
           lathe(X(31.7), Y(11.7), z0 + 32.0, 10.0, [(0.0, 1.6), (0.3, 2.6), (0.7, 1.4), (1.0, 1.8)], seg=12),   # small vase
           rbox(X(0.0), X(48.0), Y(0.0), Y(16.0), z0 + 60.0, z0 + 64.0, 0.6, n=2),       # wall shelf
           lathe(X(31.6), Y(8.1), z0 + 64.0, 5.0, [(0.0, 4.5), (0.2, 5.6), (1.0, 5.6)], seg=16)]                # plate stack
    for bx in (6.0, 42.0):                                                                # brackets under the shelf (thin wedges against the wall)
        out.append(rbox(X(bx - 0.75), X(bx + 0.75), Y(0.0), Y(9.0), z0 + 53.0, z0 + 60.2, 0.3, n=1, shear=None))
    return out

if __name__ == "__main__":
    a = sys.argv; write_obj(a[1], parts(*map(float, a[2:5])), "house shelf corner")
