#!/usr/bin/env python3
"""LIGHT SHAPES: the two river TUNNELS of room 482 (2026-11-28, user: 'mach mit 482 weiter').

The river at the foot of the terrace mountain passes under the 2-cell wide terrace path (cells x 22..23, x 352..384) twice: the drawing shows an arched
cave mouth in the path's +x face (x 384) with the water running into it (the west mouths are hidden). The light's height field had a solid column from the
path down = a wall where the drawing shows the opening with water. Measured on the room picture (U = x - y + 1184, V = (x + y) / 2 - z) with height lines
on the face x 384 (scratch zlines): the faces reach the water at 0..8 (the river, class B, level 0).
  * UPPER tunnel under the 112 path cells 22..23 x 25..27: mouth y 408..446 (sides U 1160 / 1122), crown 46 (V 360 at U 1140);
  * LOWER tunnel under the 64 path cells 22..23 x 37..40: mouth y 601..639 (sides U 967 / 929), crown 32 (V 471 at U 947).
Model per tunnel (one mesh op over its path cells, "surface"): the path block from 0 up to the path height over the whole cell rectangle with the tunnel cut
through along x (x 352..384): straight sides up to the springing, a half-circle vault (radius = half the mouth width) up to the measured crown; the water
floor at 0 in the tunnel. GAME coordinates x east, y south, z up.
Run: python3 remake/recipes/tunnel_482.py -> landstalker/data/proxies/tunnel_482_upper.obj / tunnel_482_lower.obj (our own geometry)."""
import math, os
HERE = os.path.dirname(os.path.abspath(__file__))
PROX = os.path.join(HERE, "..", "..", "landstalker", "data", "proxies")
X0, X1, WATER = 352.0, 384.0, 0.0

def tunnel(name, y0, y1, top, ty0, ty1, crown, note):
    r = (ty1 - ty0) / 2.0; spring = crown - r; yc = (ty0 + ty1) / 2.0
    V, F = [], []
    def v(p): V.append(p); return len(V)
    def quad(a, b, c, d): F.append((a, b, c, d))
    def box(ya, yb):
        p = [v((X0, ya, 0.0)), v((X1, ya, 0.0)), v((X1, yb, 0.0)), v((X0, yb, 0.0)), v((X0, ya, top)), v((X1, ya, top)), v((X1, yb, top)), v((X0, yb, top))]
        quad(p[0], p[3], p[2], p[1]); quad(p[4], p[5], p[6], p[7]); quad(p[0], p[1], p[5], p[4]); quad(p[2], p[3], p[7], p[6]); quad(p[1], p[2], p[6], p[5]); quad(p[3], p[0], p[4], p[7])
    box(y0, ty0); box(ty1, y1)                       # the path block beside the tunnel
    def vault(y):                                    # underside over the tunnel: straight sides up to the springing, half circle to the crown
        return spring + math.sqrt(max(r * r - (y - yc) ** 2, 0.0))
    P = [(yc - r * math.cos(a * math.pi / 16), None) for a in range(0, 17)]   # the vault from springing to springing (the tunnel's straight sides = the blocks' faces)
    P = [(y, vault(y)) for y, z in P]
    fr = [(v((X1, y, z)), v((X1, y, top))) for y, z in P]
    bk = [(v((X0, y, z)), v((X0, y, top))) for y, z in P]
    ys = P
    for i in range(len(ys) - 1):
        (fb0, ft0), (fb1, ft1) = fr[i], fr[i + 1]; (bb0, bt0), (bb1, bt1) = bk[i], bk[i + 1]
        quad(fb0, fb1, ft1, ft0); quad(bb1, bb0, bt0, bt1); quad(ft0, ft1, bt1, bt0); quad(fb1, fb0, bb0, bb1)
    w = [v((X0, ty0, WATER)), v((X1, ty0, WATER)), v((X1, ty1, WATER)), v((X0, ty1, WATER))]; quad(w[0], w[1], w[2], w[3])   # water floor
    with open(os.path.join(PROX, name), "w") as f:
        f.write("# room 482 river TUNNEL (%s) under the terrace path (remake/recipes/tunnel_482.py): path block y %g..%g up to %g, tunnel y %g..%g, crown %g, water %g. "
                "GAME coordinates x east, y south, z up.\n" % (note, y0, y1, top, ty0, ty1, crown, WATER))
        for p in V: f.write("v %g %g %g\n" % (round(p[0], 3), round(p[1], 3), round(p[2], 3)))
        for q in F: f.write("f " + " ".join(str(i) for i in q) + "\n")
    print("%s: %d vertices, %d faces, springing %.1f" % (name, len(V), len(F), spring))

tunnel("tunnel_482_upper.obj", 400.0, 448.0, 112.0, 408.0, 446.0, 46.0, "upper, under the 112 path cells 22..23 x 25..27")
tunnel("tunnel_482_lower.obj", 592.0, 656.0, 64.0, 601.0, 639.0, 32.0, "lower, under the 64 path cells 22..23 x 37..40")
