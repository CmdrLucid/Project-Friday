#!/usr/bin/env python3
"""LIGHT SHAPE: the stone ARCH BRIDGE of Kazalt 737 (2026-11-28, user: 'unter der Bruecke ist noch Wasser und keine Wand').

The big walkway (cells x 40..47, rows 24..44, top 112) is a bridge: the channel between the inner courtyard pond and the outer water runs UNDER it along x.
The light's height field had a solid column from the walkway down to the water = a wall where the drawing shows the arch opening with water inside.
Measured on the room picture (projection U = x - y + 1184, V = (x + y) / 2 - z):
  * front face of the deck x 768 (the z 112 line on it lies on the drawn top edge of the stone band);
  * the arch opening spans y 440 .. 672: left pier edge U 1280 (y 672), right pier edge U 1553 (y 399 -> the pier's side face at y 440, measured on the drawn
    water line along it: V - U / 2 ... two points give y 438.5);
  * soffit flat at 96 (the band below the walkway edge is 16 thick), rounded haunches r 26 springing at 70 (measured: z 67..69 at y 672, 93 at y 652);
  * water 8 (the room's water ops).
Model: two piers (y 384..440, 672..720) from 0 to 112, the deck over the channel (top 112, soffit with the haunches), extruded along x 640..768
(through the whole walkway; the courtyard side is hidden), and the water floor quad at 8 under the deck. GAME coordinates x east, y south, z up.
Run: python3 remake/recipes/bridge_737.py  -> landstalker/data/proxies/bridge_737.obj (our own geometry)."""
import math, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "landstalker", "data", "proxies", "bridge_737.obj")
X0, X1 = 640.0, 768.0
YR0, YC0, YC1, YL1 = 384.0, 440.0, 672.0, 720.0     # right pier y 384..440, channel 440..672, left pier 672..720
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

# the right pier stands FORWARD of the deck face as a buttress (user mark 2026-11-28: 'das ist alles noch Pfeiler'): its brick side face (y 440, drawn water line on it)
# runs on past the deck face to the drawn vertical corner U 1538 = x 794, its dark front face (x 794) to U 1555 = y 423; from the water to the deck top. The dark
# band above the bricks there is the arch's HAUNCH running on to the buttress front (8x zoom: the shade over the bricks reaches the corner), so the buttress
# carries the haunch fillet (r 26 from 70 to 96) and the 16 deck band above it over y 440..466. Own small mesh op over cells 48..49 x 26..29 (outside the
# walkway rectangle), with the water floor 8 around / under it inside those cells.
PV, PF = [], []
def pv(p): PV.append(p); return len(PV)
def pquad(a, b, c, d): PF.append((a, b, c, d))
BX0, BX1, BY0, BY1 = 768.0, 794.0, 423.0, 440.0
p = [pv((BX0, BY0, BOT)), pv((BX1, BY0, BOT)), pv((BX1, BY1, BOT)), pv((BX0, BY1, BOT)), pv((BX0, BY0, TOP)), pv((BX1, BY0, TOP)), pv((BX1, BY1, TOP)), pv((BX0, BY1, TOP))]
pquad(p[0], p[3], p[2], p[1]); pquad(p[4], p[5], p[6], p[7]); pquad(p[0], p[1], p[5], p[4]); pquad(p[2], p[3], p[7], p[6]); pquad(p[1], p[2], p[6], p[5]); pquad(p[3], p[0], p[4], p[7])
# haunch + band over y 440..466: cross section y -> [fillet(y), TOP] with fillet = the arch haunch (centre y 466, z 70), extruded x 768..794
hy = [BY1 + R * (1 - math.cos(a * math.pi / 16)) for a in range(0, 9)]
hz = lambda y: SPRING + math.sqrt(max(R * R - (BY1 + R - y) ** 2, 0.0))
hf = [(pv((BX1, y, hz(y))), pv((BX1, y, TOP))) for y in hy]; hb = [(pv((BX0, y, hz(y))), pv((BX0, y, TOP))) for y in hy]
for k in range(len(hy) - 1):
    (fb0, ft0), (fb1, ft1) = hf[k], hf[k + 1]; (bb0, bt0), (bb1, bt1) = hb[k], hb[k + 1]
    pquad(fb0, fb1, ft1, ft0); pquad(bb1, bb0, bt0, bt1); pquad(ft0, ft1, bt1, bt0); pquad(fb1, fb0, bb0, bb1)
pquad(hf[-1][1], hf[-1][0], hb[-1][0], hb[-1][1])   # end at y 466 (+y, under the soffit line)
for x0, y0, x1, y1 in ((768.0, 416.0, 800.0, BY0), (768.0, BY1, 800.0, 480.0), (BX1, BY0, 800.0, BY1)):   # water floor 8 around / under it (cells 48..49 x 26..29)
    w = [pv((x0, y0, WATER)), pv((x1, y0, WATER)), pv((x1, y1, WATER)), pv((x0, y1, WATER))]; pquad(w[0], w[1], w[2], w[3])
with open(OUT.replace(".obj", "_pier.obj"), "w") as f:
    f.write("# Kazalt 737 arch bridge: the right pier's BUTTRESS in front of the deck face (x 768..794, y 423..440, 0..112) with the arch haunch + band over y 440..466, the water floor 8 around it in cells 48..49 x 26..29 "
            "(remake/recipes/bridge_737.py). GAME coordinates x east, y south, z up.\n")
    for q in PV: f.write("v %g %g %g\n" % q)
    for q in PF: f.write("f " + " ".join(str(i) for i in q) + "\n")
with open(OUT, "w") as f:
    f.write("# Kazalt 737 stone ARCH BRIDGE light shape (remake/recipes/bridge_737.py): piers y 384..440 / 672..720, deck top 112 over the channel y 440..672 "
            "(soffit 96, haunches r 26 from 70), extruded x 640..768, water floor 8 under it. GAME coordinates x east, y south, z up.\n")
    for p in V: f.write("v %g %g %g\n" % (round(p[0], 3), round(p[1], 3), round(p[2], 3)))
    for q in F: f.write("f " + " ".join(str(i) for i in q) + "\n")
print("bridge_737.obj: %d vertices, %d faces" % (len(V), len(F)))
