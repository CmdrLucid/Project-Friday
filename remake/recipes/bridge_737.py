#!/usr/bin/env python3
"""LIGHT SHAPE: the stone ARCH BRIDGE of Kazalt 737 (2026-11-28, user: 'unter der Bruecke ist noch Wasser und keine Wand').

The big walkway (cells x 40..47, rows 24..44, top 112) is a bridge: the channel between the inner courtyard pond and the outer water runs UNDER it along x.
The light's height field had a solid column from the walkway down to the water = a wall where the drawing shows the arch opening with water inside.
Measured on the room picture (projection U = x - y + 1184, V = (x + y) / 2 - z):
  * front face of the deck x 768 (the z 112 line on it lies on the drawn top edge of the stone band);
  * the arch opening spans y 416 .. 672: left pier edge U 1280 (y 672); the right pier is FLUSH with the deck face (user 2026-11-28: a buttress standing 26
    forward was wrong): its front x 768 has its top exactly at 112 (the drawn dark pier strip U 1539..1552 tops out at V 474), its brick side face at y 416
    meets it at the drawn vertical corner U 1538 (the water line along the bricks gave y 438.5 only with the water at 8; the corner and the top fix y 416);
  * soffit flat at 96 (the band below the walkway edge is 16 thick), rounded haunches r 26 springing at 70 (measured: z 67..69 at y 672, 93 at y 652);
  * water 8 (the room's water ops).
Model: two piers (y 384..416, 672..720) from 0 to 112, the deck over the channel (top 112, soffit with the haunches), extruded along x 640..768
(through the whole walkway; the courtyard side is hidden), and the water floor quad at 8 under the deck. GAME coordinates x east, y south, z up.
Run: python3 remake/recipes/bridge_737.py  -> landstalker/data/proxies/bridge_737.obj (our own geometry)."""
import math, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "landstalker", "data", "proxies", "bridge_737.obj")
X0, X1 = 640.0, 768.0
YR0, YC0, YC1, YL1 = 384.0, 416.0, 672.0, 720.0     # right pier y 384..416, channel 416..672, left pier 672..720
TOP, SOFFIT, SPRING, R, WATER, BOT = 112.0, 96.0, 70.0, 26.0, 8.0, 0.0

V, F = [], []
def v(p): V.append(p); return len(V)
def quad(a, b, c, d): F.append((a, b, c, d))

def box(x0, x1, y0, y1, z0, z1):
    p = [v((x0, y0, z0)), v((x1, y0, z0)), v((x1, y1, z0)), v((x0, y1, z0)), v((x0, y0, z1)), v((x1, y0, z1)), v((x1, y1, z1)), v((x0, y1, z1))]
    quad(p[0], p[3], p[2], p[1]); quad(p[4], p[5], p[6], p[7])            # bottom, top
    quad(p[0], p[1], p[5], p[4]); quad(p[2], p[3], p[7], p[6])            # -y, +y
    quad(p[1], p[2], p[6], p[5]); quad(p[3], p[0], p[4], p[7])            # +x, -x

box(X0, X1, YR0, YC0, BOT, TOP)      # right pier (rows 24..27)
box(X0, X1, YC1, YL1, BOT, TOP)      # left pier (rows 42..44)

def soffit(y):   # underside of the deck over the channel
    if y < YC0 + R: return SPRING + math.sqrt(max(R * R - (YC0 + R - y) ** 2, 0.0))
    if y > YC1 - R: return SPRING + math.sqrt(max(R * R - (y - (YC1 - R)) ** 2, 0.0))
    return SOFFIT
ys = [YC0 + R * (1 - math.cos(a * math.pi / 16)) for a in range(0, 9)] + [YC1 - R * (1 - math.cos(a * math.pi / 16)) for a in range(8, -1, -1)]
# the cross section y -> [soffit(y), TOP], extruded along x: front (x1) and back (x0) caps as strips, soffit and top as quads along x
fr = [(v((X1, y, soffit(y))), v((X1, y, TOP))) for y in ys]
bk = [(v((X0, y, soffit(y))), v((X0, y, TOP))) for y in ys]
for i in range(len(ys) - 1):
    (fb0, ft0), (fb1, ft1) = fr[i], fr[i + 1]; (bb0, bt0), (bb1, bt1) = bk[i], bk[i + 1]
    quad(fb0, fb1, ft1, ft0)          # front cap +x
    quad(bb1, bb0, bt0, bt1)          # back cap -x
    quad(ft0, ft1, bt1, bt0)          # top +z
    quad(fb1, fb0, bb0, bb1)          # soffit (faces down / into the channel)
quad(fr[0][0], fr[0][1], bk[0][1], bk[0][0])          # side at y 440 (inside the right pier's face plane)
quad(fr[-1][1], fr[-1][0], bk[-1][0], bk[-1][1])      # side at y 672
w = [v((X0, YC0, WATER)), v((X1, YC0, WATER)), v((X1, YC1, WATER)), v((X0, YC1, WATER))]
quad(w[0], w[1], w[2], w[3])          # water floor under the deck (faces up)

with open(OUT, "w") as f:
    f.write("# Kazalt 737 stone ARCH BRIDGE light shape (remake/recipes/bridge_737.py): piers y 384..416 / 672..720, deck top 112 over the channel y 416..672 "
            "(soffit 96, haunches r 26 from 70), extruded x 640..768, water floor 8 under it. GAME coordinates x east, y south, z up.\n")
    for p in V: f.write("v %g %g %g\n" % (round(p[0], 3), round(p[1], 3), round(p[2], 3)))
    for q in F: f.write("f " + " ".join(str(i) for i in q) + "\n")
print("bridge_737.obj: %d vertices, %d faces" % (len(V), len(F)))
