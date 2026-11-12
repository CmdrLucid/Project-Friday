#!/usr/bin/env python3
"""castle_sofa.py OUT.obj x0 y0 floor - the L-shaped upholstered SOFA BENCH of the castle (tileset 1, blocks $198 $19C $19D $0EF; room 664: cells
(28, 16..17) + (29..30, 17), collision 1 step above the floor, walkable) as a near-final 3D light shape: an L seat (z 8 .. 16 above the floor: top and
front band measured on rom_picture 664) with a slightly sunk red cushion, on five short cabriole legs (outer corners + the inner corner), air below.
x0 / y0 = world units of the L's corner cell's north-west corner (664: 448, 256); short arm along -y (2 cells), long arm along +x (3 cells).
GAME coordinates x east, y south, z up."""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, os.path.join(HERE, "..", "castle_bench"))
from furniture import rbox, tube
from castle_bench import write_obj

def leg(cx, cy, ox, oy, z0, s):
    n = math.hypot(ox, oy); d = (ox / n, oy / n)
    pts = [(cx, cy, z0 + s + 0.4), (cx + 0.7 * d[0], cy + 0.7 * d[1], z0 + s - 2.0), (cx + 0.3 * d[0], cy + 0.3 * d[1], z0 + s - 4.5),
           (cx - 0.2 * d[0], cy - 0.2 * d[1], z0 + 1.5), (cx + 0.5 * d[0], cy + 0.5 * d[1], z0 + 0.25)]
    return tube(pts, [1.1, 1.15, 0.8, 0.6, 0.85], seg=10)

def parts(x0, y0, z0, seat=(8.0, 16.0), i=2.2):
    a, b = seat
    out = [rbox(x0, x0 + 16, y0, y0 + 32, z0 + a, z0 + b - 0.6, 1.2, n=2),            # short arm (incl. the corner cell)
           rbox(x0, x0 + 48, y0 + 16, y0 + 32, z0 + a, z0 + b - 0.6, 1.2, n=2),       # long arm
           rbox(x0 + 3, x0 + 13, y0 + 3, y0 + 29, z0 + b - 1.2, z0 + b, 0.8, n=2),    # cushion, inset like the drawn rim
           rbox(x0 + 3, x0 + 45, y0 + 19, y0 + 29, z0 + b - 1.2, z0 + b, 0.8, n=2)]
    for (cx, cy, ox, oy) in ((x0 + i, y0 + i, -1, -1), (x0 + 16 - i, y0 + i, 1, -1), (x0 + i, y0 + 32 - i, -1, 1),
                             (x0 + 48 - i, y0 + 32 - i, 1, 1), (x0 + 48 - i, y0 + 16 + i, 1, -1)):
        out.append(leg(cx, cy, ox, oy, z0, a))
    return out

if __name__ == "__main__":
    a = sys.argv; write_obj(a[1], parts(*map(float, a[2:5])), "castle sofa bench")
