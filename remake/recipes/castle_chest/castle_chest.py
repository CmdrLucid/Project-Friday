#!/usr/bin/env python3
"""castle_chest.py OUT.obj x0 y0 floor - the castle CHEST OF DRAWERS with a big clay POT (tileset 15, blocks $05C $38D $04E; rooms 65 / 66: cells x 15,
y 21..23; collision 2 steps for the chest, 3 steps on the pot's cell): the chest = its collision box (fits the drawing exactly), the pot a lathe on its
north cell instead of a 16 x 16 x 16 cube (drawn: rim at z 47 on the cell axis, belly r ~9 (wider than the cell by 1, as drawn), mouth r ~6.5). Measured on rom_picture 65 by overlay.
x0 / y0 = world units of the chest's north-west corner (65: 240, 336). GAME coordinates x east, y south, z up."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, os.path.join(HERE, "..", "castle_bench"))
from furniture import rbox, lathe
from castle_bench import write_obj
import cabinet

POT = [(0.0, 6.0), (0.15, 8.3), (0.45, 9.0), (0.75, 7.9), (0.88, 6.2), (0.95, 6.5), (1.0, 6.5)]

def parts(x0, y0, z0):
    return cabinet.cabinet(x0, x0 + 16.0, y0, y0 + 48.0, z0, z0 + 32.0, '+x', [('plinth', 2)] + [('drawers', 7, 3)] * 4) + [lathe(x0 + 8.0, y0 + 8.0, z0 + 32.0, 15.0, POT)]

if __name__ == "__main__":
    a = sys.argv; write_obj(a[1], parts(*map(float, a[2:5])), "castle chest with pot")
