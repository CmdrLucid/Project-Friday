#!/usr/bin/env python3
"""castle_bench.py OUT.obj x0 x1 y0 y1 floor - the upholstered BENCH of the Mercator castle bedrooms (tileset 15, blocks $370 $371 $06F; rooms 67 / 77:
cells x 20..22, y 13, collision height 1) as a near-final 3D model = light shape: a padded seat (z 9 .. 16, soft rounded edges; its top and front
measured on rom_picture 67: top at the collision box, front band ~7 high) on four CABRIOLE legs (knee out, ankle in, a small foot out), air below.
GAME coordinates x east, y south, z up."""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
from furniture import rbox, tube

def parts(x0, x1, y0, y1, z0, seat=(9.0, 16.0), inset=2.6):
    out = [rbox(x0, x1, y0, y1, z0 + seat[0], z0 + seat[1], 1.4, n=2)]
    for (cx, ox) in ((x0 + inset, -1), (x1 - inset, 1)):
        for (cy, oy) in ((y0 + inset, -1), (y1 - inset, 1)):
            d = (ox / math.sqrt(2), oy / math.sqrt(2)); s = seat[0]
            pts = [(cx, cy, z0 + s + 0.4), (cx + 0.9 * d[0], cy + 0.9 * d[1], z0 + s - 2.5), (cx + 0.5 * d[0], cy + 0.5 * d[1], z0 + s - 5.5),
                   (cx - 0.2 * d[0], cy - 0.2 * d[1], z0 + 2.0), (cx + 0.6 * d[0], cy + 0.6 * d[1], z0 + 0.25)]
            out.append(tube(pts, [1.15, 1.2, 0.85, 0.6, 0.9], seg=10))
    return out

def write_obj(path, ps, title):
    with open(path, "w") as fo:
        fo.write("# %s (remake/recipes/castle_bench/castle_bench.py). GAME coordinates x east, y south, z up, world units.\n" % title)
        fo.write("# our own geometry fitted to the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        b = 0
        for V, F in ps:
            for v in V: fo.write("v %.3f %.3f %.3f\n" % v)
            for f in F: fo.write("f " + " ".join(str(i + 1 + b) for i in f) + "\n")
            b += len(V)
    print("%s: %d parts" % (path, len(ps)))

if __name__ == "__main__":
    a = sys.argv; write_obj(a[1], parts(*map(float, a[2:7])), "castle bench")
