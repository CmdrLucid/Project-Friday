#!/usr/bin/env python3
"""LIGHT SHAPES: the left Mercator castle court, rooms 32 / 33 (MERCATOR_CASTLE_EXTERIOR_LEFT_COURT + its ribbonless variant, same picture and
height map). Invisible shapes for the lighting only (never drawn). GAME coordinates x east, y south, z up (units; a cell = 16).

Why: the height map holds the KEEP (the tall wall with the round corner tower at the back of the court) only as BARRIER cells $4F00 (rows 28..30,
x 31..39) and void behind; the light's void painter turned all of it into water 0 = the keep's wall pixels were read as FLOOR (no wall for the sun /
the sword glow, HANDOFF 0a537 follow-up 2026-11-28).

Measured on the room picture (U = x - y + 1184, V = (x + y) / 2 - z; scratch ~/Project-Friday-Test/lktest/burg32 ov.py overlays):
  * KEEP front face y 496 (the walkway row 31 at 48 lies against it: its outline sits exactly on the drawn stone blocks), left end x 464 (hidden behind the slim
    left tower; the windowed face starts at U 1183), right face x 640 (its foot line on the grass matches; it runs back to the green-roofed house front
    y 432, U 1392). The face and the tower run off the picture top (V 152 at the tower: z >= 416) -> top 440, depth back to y 224 (invisible).
  * ROUND TOWER in the keep's front-right corner: silhouette U 1297 .. 1360 -> radius 22.5 (U width = 2 r sqrt 2), axis U 1328.5; its foot (front
    point V 559, just behind the courtyard pine at cell 40,31) -> centre (615, 471). It is NOT standing in front of the corner (that circle would
    swallow the pine's walkable cell and its foot would lie in the drawn grass): the keep's corner is NOTCHED (x 608..640, y 464..496) and the tower
    fills the notch; the flat faces end behind its silhouette (front face up to x 608 = U 1296, right face from y 464 = U 1360).
  * SLIM ROUND TOWER at the keep's front-left corner (curved brick rows, zoom): silhouette U 1136 .. 1182.5 (the windowed face starts at U 1183 =
    x 496 on y 496) -> radius 16.5, axis U 1159.4; its foot is hidden behind the left curtain wall / walkway, so its depth is taken from the face:
    centre (471.5, 496) (it stays out of the walkway cells x >= 496 and the curtain wall rows >= 33).
Run: python3 remake/recipes/proxy_castle_32.py -> landstalker/data/proxies/castle_32_keep.obj (our own geometry)."""
import math, os
HERE = os.path.dirname(os.path.abspath(__file__))
PROX = os.path.join(HERE, "..", "..", "landstalker", "data", "proxies")

KX0, KY0, KX1, KY1, KTOP = 464.0, 224.0, 640.0, 496.0, 440.0   # keep block
NX, NY = 608.0, 464.0                                          # notch corner (the tower stands in it)
TCX, TCY, TR, TTOP, TSEG = 615.0, 471.0, 22.5, 460.0, 32       # round tower (front-right corner)
LCX, LCY, LR, LTOP, LSEG = 471.5, 496.0, 16.5, 450.0, 24       # slim round tower (front-left corner)

class Mesh:
    def __init__(self): self.V, self.F = [], []
    def v(self, p): self.V.append(p); return len(self.V)
    def f(self, *ix): self.F.append(ix)
    def prism(self, poly, z0, z1):
        """vertical prism over a CONVEX polygon (counter-clockwise seen from above in x / y with y south = clockwise on screen); closed"""
        n = len(poly); lo = [self.v((x, y, z0)) for x, y in poly]; hi = [self.v((x, y, z1)) for x, y in poly]
        self.f(*reversed(lo)); self.f(*hi)
        for i in range(n):
            j = (i + 1) % n; self.f(lo[i], lo[j], hi[j], hi[i])
    def write(self, path, head):
        with open(path, "w") as o:
            o.write("# " + head + "\n")
            for p in self.V: o.write("v %.3f %.3f %.3f\n" % p)
            for t in self.F: o.write("f " + " ".join(str(i) for i in t) + "\n")

def keep():
    m = Mesh()
    # the notched footprint as two convex prisms (back part full width, front strip up to the notch)
    m.prism([(KX0, KY0), (KX1, KY0), (KX1, NY), (KX0, NY)], 0.0, KTOP)
    m.prism([(KX0, NY), (NX, NY), (NX, KY1), (KX0, KY1)], 0.0, KTOP)
    circ = [(TCX + TR * math.cos(2 * math.pi * i / TSEG), TCY + TR * math.sin(2 * math.pi * i / TSEG)) for i in range(TSEG)]
    m.prism(circ, 0.0, TTOP)
    circ = [(LCX + LR * math.cos(2 * math.pi * i / LSEG), LCY + LR * math.sin(2 * math.pi * i / LSEG)) for i in range(LSEG)]
    m.prism(circ, 0.0, LTOP)
    return m

if __name__ == "__main__":
    os.makedirs(PROX, exist_ok=True)
    p = os.path.join(PROX, "castle_32_keep.obj")
    keep().write(p, "castle court 32 / 33: keep (notched block) + round corner tower + slim left corner tower; remake/recipes/proxy_castle_32.py")
    print(p)
