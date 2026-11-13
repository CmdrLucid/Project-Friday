#!/usr/bin/env python3
"""kitchen_table.py OUT.obj x0 x1 y0 y1 floor [top=16 slab=5 inset=2.5 r=1.8] - the big KITCHEN TABLE of the Mercator castle (tileset 15, 4 x 4 cells,
blocks $025 $342..$354; rooms 68 / 69: cells 19..22 x 18..21, collision a 1 step box) as a near-final 3D light shape: a thin rounded slab (z 11 .. 16,
measured on rom_picture 68: the drawn top edge band is ~5 high) on four thin STRAIGHT legs (radius ~1.8, ~2.5 in from the corners), air below.
Unlike the castle room table (furniture.castle_table_mesh: 8 thick, curved legs). GAME coordinates x east, y south, z up."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "castle_bench"))
from furniture import rbox, tube
from castle_bench import write_obj

def parts(x0, x1, y0, y1, z0, top=16.0, slab=5.0, inset=2.5, r=1.8):
    out = [rbox(x0, x1, y0, y1, z0 + top - slab, z0 + top, 1.0, n=2)]
    for cx in (x0 + inset, x1 - inset):
        for cy in (y0 + inset, y1 - inset):
            out.append(tube([(cx, cy, z0 + top - slab + 0.4), (cx, cy, z0 + 0.25)], [r, r * 0.9], seg=10))
    return out

if __name__ == "__main__":
    a = sys.argv; f = list(map(float, a[2:]))
    write_obj(a[1], parts(*f[:5], *f[5:]), "castle kitchen table")
