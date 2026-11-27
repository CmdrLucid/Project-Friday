#!/usr/bin/env python3
"""LIGHT SHAPE + remake form: the LAKE SHRINE building of room 524 (LAKE_SHRINE_EXTERIOR_WITH_MAGMA), measured 2026-11-27/28 on the drawn room picture
(projection U = x - y + 1184, V = (x + y) / 2 - z; scratch overlays ~/Project-Friday-Test/lktest/shrine524, local).
  * COLLISION: the body = blocked cells x 27..40 y 37..47 (height 15 = 240), the door = walkable cells (33..34, 47) at 80; the two COLUMNS = the blocked
    single cells (27, 49) and (40, 49); between the columns and the front wall the walkable porch rows 48..49 at 80 (ground of the room 32).
  * BODY x 432..656, y 592..768 (front wall: the door foot lies on y 768 at z 80; right wall: its vertical corner edge U 1072 runs from the roof down to the
    foundation at z 32), flat roof z 240 (top silhouette: back corner U 1024 V 272, right corner U 1248 V 384, both exact).
  * PORCH ROOF: the flat roof slab runs on 32 units in front of the wall (to y 800) over the two columns: the roof texture reaches 27 px below the
    y 768 edge line and its left end corner sits at U 816 V 376 = (432, 800, 240); the slab's front face shows as the dark moulding under the balls
    (bricks of the wall behind start 46 px below the y 768 line -> slab bottom z 226).
  * KNOBS on the roof edge, front and right side only in the drawing (the back / left edges are clean top silhouette lines), one every 16 units
    (picture period 16 on both sides). Re-measured 2026-11-27 on straightened strips of the cornice (user: the first balls did not fit): each knob is
    TALLER than wide (12 px wide, 14 px tall -> egg, horizontal radius 4.5, vertical 5.5), centre 27 px below the y 768 edge line = (y 798, z 243),
    i.e. low on the roof edge, half in front of it; under each knob a CONSOLE stone (dark joints at U mod 16 = 4 / 13, 9 wide) on the cornice face
    z 226..240; front row x 455..647 (the end over the left column is bare), right row x 654 y 597..789. LIGHT shape = as drawn; the REMAKE variant
    (--remake, user 2026-11-27 'wenn, dann rundherum') adds the back / left rows.
  * COLUMNS: fluted round shaft r 8.5 (picture width 26 px incl. outline), axes (440, 792) / (648, 792) = the centres of the blocked cells, square
    plinth 15.5 on the porch floor 80, base ring, shaft up to the slab (the flutes end at z ~227), thin abacus under the slab.
  * DOOR: panel x 526..561, z 80..136 (dark lintel line) recessed 4; pilasters x 520..526 / 561..567 up to z 148 (2 proud), lintel band z 136..150.
  * two small wall ornaments (carved stones) at x 497 / 589, z ~120, symmetric about the door axis 543.5.
Two light ops (an outdoor surface model owns its whole op rectangle, remake/MODELING_LESSONS.md section 4): body = cells 27..40 x 37..47 (solid),
porch = cells 27..40 x 48..49 with "air" (the slab floats over the walkable porch) and "floor" 80.
Pure Python, no ROM.  Run: python3 remake/recipes/proxy_shrine_524.py  -> landstalker/data/proxies/shrine_524_{body,porch}.obj (game coordinates)."""
import math, os
HERE = os.path.dirname(os.path.abspath(__file__)); PROX = os.path.join(HERE, "..", "..", "landstalker", "data", "proxies")

X0, X1, YB, YF = 432.0, 656.0, 592.0, 768.0      # body walls
ZG, ZP, ZR = 32.0, 80.0, 240.0                    # foundation (room ground), porch floor, roof top
YS, ZS = 800.0, 226.0                             # porch slab front, slab bottom
KNOB_A, KNOB_C, KNOB_Z, KNOB_IN = 4.5, 5.5, 243.0, 2.0   # knobs: egg shape (horizontal / vertical radius), centre height, centre inset from the roof edge
RAY_BACK = 2.5                                    # light shape only: shift of the front / right knob rows along the view ray (see Mesh.knob)
CONS_W, CONS_OUT = 9.0, 2.5                       # console stone under each knob: width, how far it stands out of the cornice face (z ZS..ZR)
COLS = [(440.0, 792.0), (648.0, 792.0)]
DOOR = dict(x0=526.0, x1=561.0, z1=136.0, depth=4.0, pil=6.0, pil_z=148.0, proud=2.0, lint=(136.0, 150.0))
FRONT_X = [567.0 + 16 * k for k in range(-7, 6)]   # front knob row x 455..647 (picture phase U 953 + 16 k; the left end over the column is bare)
RIGHT_Y = [757.0 - 16 * k for k in range(-2, 11)]  # right knob row y 597..789 (picture phase U 1081 + 16 k)
ORN = [(497.0, 120.0), (589.0, 120.0)]            # wall ornaments: x centre, z centre

class Mesh:
    def __init__(s): s.V, s.F = [], []
    def box(s, x0, y0, z0, x1, y1, z1):
        o = len(s.V); s.V += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        s.F += [tuple(o + i for i in f) for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]]
    def lathe(s, cx, cy, prof, n=24):
        """closed solid of revolution, prof = [(z, r), ...] bottom -> top"""
        o = len(s.V)
        for z, r in prof: s.V += [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z) for i in range(n)]
        for j in range(len(prof) - 1):
            for i in range(n): a = o + j * n + i; b = o + j * n + (i + 1) % n; s.F.append((a, b, b + n, a + n))
        s.V += [(cx, cy, prof[0][0]), (cx, cy, prof[-1][0])]; c0, c1 = len(s.V) - 2, len(s.V) - 1; m = len(prof)
        for i in range(n): s.F += [(c0, o + (i + 1) % n, o + i), (c1, o + (m - 1) * n + i, o + (m - 1) * n + (i + 1) % n)]
    def egg(s, cx, cy, cz, a, c, n=12, k=8):
        prof = [(cz - c * math.cos(math.pi * j / k), a * math.sin(math.pi * j / k)) for j in range(1, k)]
        s.lathe(cx, cy, [(cz - c, 0.0)] + prof + [(cz + c, 0.0)], n)
    def knob(s, side, t):
        """one knob on its console: side 'f' front (y YS), 'b' back (y YB), 'r' right (x X1), 'l' left (x X0); t = x (f / b) or y (r / l).
        LIGHT shape: the front / right knobs + consoles move by RAY_BACK along the view ray (-1, -1, -1): the game picture stays pixel-identical, but
        nothing reaches past the op cells (y 800 / x 656): the first build had them 2.5 out = vertical stripes every 16 on the porch front wall below
        (sword glow, lightedges 524 cell (38, 52): 328 px; the light works in 4 unit sub columns)."""
        w = CONS_W / 2; d = 0.0 if ALL_ROUND else RAY_BACK
        def bx(x0, y0, z0, x1, y1, z1): s.box(x0 - d, y0 - d, z0 - d, x1 - d, y1 - d, z1 - d)
        def eg(x, y): s.egg(x - d, y - d, KNOB_Z - d, KNOB_A, KNOB_C)
        if side == "f": bx(t - w, YS - 0.5, ZS, t + w, YS + CONS_OUT, ZR); eg(t, YS - KNOB_IN)
        if side == "r": bx(X1 - 0.5, t - w, ZS, X1 + CONS_OUT, t + w, ZR); eg(X1 - KNOB_IN, t)
        if side == "b": s.box(t - w, YB - CONS_OUT, ZS, t + w, YB + 0.5, ZR); s.egg(t, YB + KNOB_IN, KNOB_Z, KNOB_A, KNOB_C)
        if side == "l": s.box(X0 - CONS_OUT, t - w, ZS, X0 + 0.5, t + w, ZR); s.egg(X0 + KNOB_IN, t, KNOB_Z, KNOB_A, KNOB_C)
    def write(s, path, title):
        with open(path, "w") as f:
            f.write("# %s (remake/recipes/proxy_shrine_524.py). GAME coordinates x east, y south, z up, world units; our own geometry measured on the original picture.\n" % title)
            for v in s.V: f.write("v %g %g %g\n" % tuple(round(c, 3) for c in v))
            for q in s.F: f.write("f " + " ".join(str(i + 1) for i in q) + "\n")
        xs = [v[0] for v in s.V]; ys = [v[1] for v in s.V]; zs = [v[2] for v in s.V]
        print("%s: %d vertices, %d faces, x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f" % (os.path.basename(path), len(s.V), len(s.F), min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))

def body():
    m = Mesh(); d = DOOR; yr = YF - d["depth"]
    m.box(X0, YB, ZG, X1, yr, ZR)                                  # core up to the door recess plane
    m.box(X0, yr, ZG, d["x0"], YF, ZR); m.box(d["x1"], yr, ZG, X1, YF, ZR)   # front wall left / right of the door
    m.box(d["x0"], yr, d["z1"], d["x1"], YF, ZR); m.box(d["x0"], yr, ZG, d["x1"], YF, ZP)   # above / below the door panel
    p = d["proud"]
    m.box(d["x0"] - d["pil"], YF, ZP, d["x0"], YF + p, d["pil_z"]); m.box(d["x1"], YF, ZP, d["x1"] + d["pil"], YF + p, d["pil_z"])   # pilasters
    m.box(d["x0"] - d["pil"] - 1, YF, d["lint"][0], d["x1"] + d["pil"] + 1, YF + p + 1, d["lint"][1])   # lintel band over the door
    for x, z in ORN: m.box(x - 5, YF, z - 5, x + 5, YF + 3, z + 5)
    for y in RIGHT_Y:
        if y < YF: m.knob("r", y)                                   # right knob row over the body (the two over the porch slab: porch())
    if ALL_ROUND:                                                   # REMAKE variant only (user 2026-11-27: 'wenn, dann rundherum'); not drawn -> not in the light shape
        for x in FRONT_X: m.knob("b", x)
        for y in RIGHT_Y:
            if y < YF: m.knob("l", y)
    return m

def porch():
    m = Mesh()
    m.box(X0, YF, ZS, X1, YS, ZR)                                   # the roof slab in front of the wall
    for cx, cy in COLS:
        m.box(cx - 7.75, cy - 7.75, ZP, cx + 7.75, cy + 7.75, ZP + 4)                       # plinth
        rmax = 99.0 if ALL_ROUND else 7.95   # LIGHT shape: radii capped so the column stays inside its 16 x 16 cell (rings 9.4..9.9 and the shaft 8.5 -> 7.95; the 4 unit light grid made stripes where parts reached a neighbour cell)
        m.lathe(cx, cy, [(z, min(r, rmax)) for z, r in [(ZP + 4, 9.6), (ZP + 5.5, 9.9), (ZP + 7, 9.0), (ZP + 8, 8.5), (150, 8.45), (220, 8.3), (220, 9.4), (222, 9.4)]])   # base ring + shaft + top ring
        a = 8.5 if ALL_ROUND else 7.95
        m.box(cx - a, cy - a, 222, cx + a, cy + a, ZS)                                      # abacus under the slab
    for x in FRONT_X: m.knob("f", x)                                 # front knob row
    for y in RIGHT_Y:
        if y >= YF: m.knob("r", y)
    if ALL_ROUND:
        for y in RIGHT_Y:
            if y >= YF: m.knob("l", y)
        m.knob("f", FRONT_X[0] - 16)                                  # the left end over the column (bare in the drawing)
    return m

ALL_ROUND = False
if __name__ == "__main__":
    import sys
    if "--remake" in sys.argv:   # the remake variant (knobs on all four sides) -> ~/.landstalker_remake/assets/shrine_524/ (local, never in git)
        ALL_ROUND = True; out = os.path.expanduser("~/.landstalker_remake/assets/shrine_524"); os.makedirs(out, exist_ok=True)
        body().write(os.path.join(out, "shrine_524_body_remake.obj"), "Lake shrine of room 524, REMAKE variant: knobs on all sides")
        porch().write(os.path.join(out, "shrine_524_porch_remake.obj"), "Lake shrine of room 524, REMAKE variant: knobs on all sides")
    else:
        body().write(os.path.join(PROX, "shrine_524_body.obj"), "Lake shrine of room 524: body, door, ornaments, right knob row")
        porch().write(os.path.join(PROX, "shrine_524_porch.obj"), "Lake shrine of room 524: porch roof slab, two fluted columns, front knob row")
