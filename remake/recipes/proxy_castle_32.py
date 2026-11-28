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
  * LOWER LEFT TOWER (barrier $4F00 cells x 31..32 rows 50..53 = painted water 0 for the light): the twin of the upper left tower, whose height map
    is exact (x 30..32 rows 39..42, ring 240, inner cells 224): body 48 x 64 (x 480..528, y 800..864; drawn left edge U 800, front corner U 848,
    right edge U 912 = 112 px wide, the front corner's top at V 456 = 240), a closed RING of 10 cube blocks (one cell each, 224..240, fine seams, no
    crenels) around the 1 x 2 recess (cells 31, 51..52) at 224; the body's vertical edges are drawn ROUNDED (front edge: bright curved bricks
    U 832 .. 848 -> radius 12), the cube blocks on top keep square corners (they overhang the rounding a little, as drawn).
Run: python3 remake/recipes/proxy_castle_32.py -> landstalker/data/proxies/castle_32_keep.obj, castle_32_tower_ll.obj (our own geometry)."""
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

def chamfer_rect(x0, y0, x1, y1, c):
    """rectangle with its 4 corners cut by c (octagon, convex, order as Mesh.prism wants)"""
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]

def frustum(m, lo_poly, hi_poly, z0, z1):
    """closed solid between two convex polygons with the same vertex count (bottom at z0, top at z1)"""
    lo = [m.v((x, y, z0)) for x, y in lo_poly]; hi = [m.v((x, y, z1)) for x, y in hi_poly]; n = len(lo)
    m.f(*reversed(lo)); m.f(*hi)
    for i in range(n):
        j = (i + 1) % n; m.f(lo[i], lo[j], hi[j], hi[i])

def round_rect(x0, y0, x1, y1, r, seg=4):
    """rectangle with rounded vertical edges (quarter circles of radius r, seg segments each); convex, order as Mesh.prism wants"""
    pts = []
    for (cx, cy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90.0 * k / seg); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def wall_tower(cx0, cy0, w=3, d=4, inner=((1, 1), (1, 2)), body=224.0, top=240.0, chamfer=0.0, bevel=2.0, round_r=12.0):
    """square crenellated tower of the left curtain wall: body w x d cells from cell (cx0, cy0), a ring of cube blocks (one cell each) from body to
    top around the inner recess cells (relative), the recess floor = body; chamfered vertical body edges, bevelled block tops"""
    m = Mesh(); X0, Y0 = 16.0 * cx0, 16.0 * cy0; X1, Y1 = X0 + 16 * w, Y0 + 16 * d
    m.prism(round_rect(X0, Y0, X1, Y1, round_r), 0.0, body)   # the body's vertical edges are drawn rounded (the front edge: bright curved bricks U 832 .. 848)
    for i in range(w):
        for j in range(d):
            if (i, j) in inner: continue
            bx0, by0 = X0 + 16 * i, Y0 + 16 * j; bx1, by1 = bx0 + 16, by0 + 16
            # outer corners of the ring follow the body chamfer
            c = chamfer if (i in (0, w - 1) and j in (0, d - 1)) else 0.0
            poly = [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)]
            if c:
                cut = {(0, 0): 0, (w - 1, 0): 1, (w - 1, d - 1): 2, (0, d - 1): 3}[(i, j)]
                pts = []
                for k, (px, py) in enumerate(poly):
                    if k != cut: pts.append((px, py)); continue
                    nx_, ny_ = poly[(k + 1) % 4]; qx, qy = poly[(k - 1) % 4]
                    def toward(ax, ay, bx, by): L = math.hypot(bx - ax, by - ay); return (ax + (bx - ax) * c / L, ay + (by - ay) * c / L)
                    pts.append(toward(px, py, qx, qy)); pts.append(toward(px, py, nx_, ny_))
                poly = pts
            m.prism(poly, body, top - bevel)
            cxm = sum(p[0] for p in poly) / len(poly); cym = sum(p[1] for p in poly) / len(poly)
            inset = [(px + (cxm - px) * bevel / 8.0, py + (cym - py) * bevel / 8.0) for px, py in poly]
            frustum(m, poly, inset, top - bevel, top)
    return m

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
    p = os.path.join(PROX, "castle_32_tower_ll.obj")
    wall_tower(30, 50).write(p, "castle court 32 / 33: lower left curtain wall tower (twin of the upper one); remake/recipes/proxy_castle_32.py")
    print(p)
