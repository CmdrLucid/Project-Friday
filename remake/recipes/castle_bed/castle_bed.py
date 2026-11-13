#!/usr/bin/env python3
"""castle_bed.py OUT.obj x0 y0 floor [params.json] - the BED of the Mercator castle rooms (tileset 15, blocks $031..$038; rooms 63 / 64 / 67 / 77 / 108)
as a near-final 3D model = light shape. Reference: room 67 cells x 15..17, y 13..14 (3 x 2, collision height 1), head at the WEST end (x0), along +x.
Parts in (u = x - x0 along the bed, w = y - y0 across, z up from the floor), all from the drawing (remake/tools/proxy_overlay.py on rom_picture 67):
  legs (4 square), frame rail (visible under the blanket hem), blanket (soft slab over the rail, hanging a little over the foot and the open side),
  ONE pillow at the head end, HEADBOARD at the head end (top ~ 24). GAME coordinates x east, y south, z up."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
from furniture import rbox

P0 = dict(L=48.0, W=32.0, leg=2.6, rail=(5.5, 10.0), blanket=(2.5, 49.0, 0.0, 33.0, 9.0, 16.0, 2.2), pillow=(3.0, 13.0, 8.0, 23.5, 15.0, 19.5, 2.2),
          head=(0.0, 2.6, 0.0, 32.0, 0.0, 24.0, 0.9))

def parts(x0, y0, z0, P):
    L, W, g = P['L'], P['W'], P['leg']; out = []
    def B(u0, u1, w0, w1, a, b, r, n=2, flat=False): out.append(rbox(x0 + u0, x0 + u1, y0 + w0, y0 + w1, z0 + a, z0 + b, r, n=n, flat_bottom=flat))
    for u in (P['head'][1], L - g):
        for w in (0.5, W - g - 0.5): B(u, u + g, w, w + g, 0.0, P['rail'][1], 0.5, n=1, flat=True)              # legs
    B(P['head'][1] - 0.2, L, 0.5, W - 0.5, P['rail'][0], P['rail'][1], 0.6)                                       # frame rail
    u0, u1, w0, w1, a, b, r = P['blanket']; B(u0, u1, w0, w1, a, b, r)                                            # blanket
    u0, u1, w0, w1, a, b, r = P['pillow']; B(u0, u1, w0, w1, a, b, r)                                             # pillow
    u0, u1, w0, w1, a, b, r = P['head']; B(u0, u1, w0, w1, a, b, r, flat=True)                                    # headboard
    return out

def write_obj(path, ps, title):
    with open(path, "w") as fo:
        fo.write("# %s (remake/recipes/castle_bed/castle_bed.py). GAME coordinates x east, y south, z up, world units.\n" % title)
        fo.write("# our own geometry fitted to the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        b = 0
        for V, F in ps:
            for v in V: fo.write("v %.3f %.3f %.3f\n" % v)
            for f in F: fo.write("f " + " ".join(str(i + 1 + b) for i in f) + "\n")
            b += len(V)
    print("%s: %d parts" % (path, len(ps)))

if __name__ == "__main__":
    a = sys.argv; P = dict(P0)
    if len(a) > 5: P.update(json.load(open(a[5])))
    write_obj(a[1], parts(float(a[2]), float(a[3]), float(a[4]), P), "castle bed")
