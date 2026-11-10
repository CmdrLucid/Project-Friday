"""Measured FURNITURE shapes shared by the light proxies (remake/recipes/proxy_*.py) and later remake assets (user 2026-11-09: 'mit Tischen etc.
weiter' + 'direkt so umsetzen, dass es wiederverwendbar wird/bleibt').  Parts in GAME coordinates (x east, y south, z up, world units; one map
cell = 16), the format of remake/lib/proxy.py.  The collision of indoor furniture is a solid raised box (the game cannot know legs); these shapes
put the light where the drawing has wood: a table top with AIR below it (the light op 'mesh' with "air": true makes the floating top a slab)."""

def table(name, x0, y0, x1, y1, floor, top, thick, leg, inset, outline=0):
    """a table on four square legs: top face at `top`, `thick` units thick, legs `leg` units square set `inset` in from each corner (outer leg
    faces), standing on `floor`; returns proxy parts (boxes). `outline`: the top reaches that far beyond x0 / y0 (the back sides): the drawn
    1 pixel black outline of the top lies there, its pixels must hit the table, not the floor behind it (else a dark 1 px line, room 670)"""
    u = top - thick
    parts = [(name + "_top", x0 - outline, y0 - outline, x1, y1, u, top, top, "flat", None)]
    for k, (lx, ly) in enumerate(((x0 + inset, y0 + inset), (x1 - inset - leg, y0 + inset), (x1 - inset - leg, y1 - inset - leg), (x0 + inset, y1 - inset - leg))):
        parts.append(("%s_leg%d" % (name, k), lx, ly, lx + leg, ly + leg, floor, u, u, "flat", None))
    return parts

def top_on_legs(name, rects, legs, floor, top, thick, leg, outline=0):
    """a piece of any outline: a top made of several rectangles `rects` [(x0, y0, x1, y1), ..] (top face at `top`, `thick` units thick, each
    reaching `outline` beyond its back sides x0 / y0 like table()) on square legs `leg` units wide whose min corners are `legs` [(lx, ly), ..]
    (only where the drawing has a leg: an L bench has none at its inner corner); returns proxy parts (boxes)"""
    u = top - thick
    parts = [("%s_top%d" % (name, k), x0 - outline, y0 - outline, x1, y1, u, top, top, "flat", None) for k, (x0, y0, x1, y1) in enumerate(rects)]
    return parts + [("%s_leg%d" % (name, k), lx, ly, lx + leg, ly + leg, floor, u, u, "flat", None) for k, (lx, ly) in enumerate(legs)]

def l_bench(name, x0, y0, x1, y1, ax0, floor, top, thick, leg, inset, outline=0):
    """the L BENCH of the Mercator bedrooms (623 / 624 / 701 / 702, user 2026-11-09: 'der geht als L um die Ecke'): a long arm x0..x1 / y0..y1
    (one cell wide, along y) and at its back end y0 a short arm reaching west to ax0 (one cell deep, y0 .. y0 + 16).  Legs as drawn (feet
    measured on the picture of 623, ~/lktest/bench/legs.py: (401, 605) (413, 605) at the front end, (412, 545) at the outer back corner,
    (384, 556) at the west end of the short arm; the leg behind it is hidden, placed symmetric); NO leg at the inner corner (floor there)."""
    rects = [(x0, y0, x1, y1), (ax0, y0, x0, y0 + 16)]
    legs = [(x0 + inset, y1 - inset - leg), (x1 - inset - leg, y1 - inset - leg), (x1 - inset - leg, y0 + inset),
            (ax0 + inset, y0 + inset), (ax0 + inset, y0 + 16 - inset - leg)]
    return top_on_legs(name, rects, legs, floor, top, thick, leg, outline)

# THE MERCATOR TABLE (room 670, MERCATOR_HOUSE_NEAR_WELL_FIRST_FLOOR), measured 2026-11-09 on 8x zooms of the drawing: the top's four corners sit
# exactly on its collision cells (22..24 x 22..23 = x 352..400, y 352..384, walkable height 1 = 16); legs
# ~4 units (5 picture columns), their floor feet at (354, 381) / (397, 381) / (397, 354) = 2..3 in from the outer corners.
# EDGE BAND re-measured 2026-11-09 night per picture column against the GPU model buffer (gm dump, ~/lktest/unsh): the drawn layer A band ends 3 rows
# below the top face edge (z ~13), thickness 5 put 2 rows of carpet under the edge on the slab's side face = a bright strip (user: 'direkt unter der
# Platte noch ein hellerer gruener Streifen') -> thickness 3.
MERCATOR_TABLE = dict(thick=3, leg=4, inset=1, outline=1)

# THE CASTLE TABLE (Mercator castle rooms, tileset 1: gold rim, curved legs), measured 2026-11-09 on room 96 (cells 20..22 x 21..23, height 1):
# top corners U 1167.5 / 1120 / 1215 / 1167 = exactly the 3 x 3 cells at z 16, gold edge band ~6, curved legs ~5 wide standing AT the corners.
# EDGE BAND re-measured 2026-11-09 night (picture rows vs GPU model buffer, room 96): the gold band + its black outline reach 8 rows below the top
# face edge (z 8), thickness 6 lit the lowest 2 rows as floor -> thickness 8.
CASTLE_TABLE = dict(thick=8, leg=5, inset=0, outline=1)

# THE VASE (Mercator houses, tileset 2: the pair by the hearth of 670 / 671 / 694, user 2026-11-09 'Objekte wie diese Vasen als echte 3D-Form fuers
# Licht'), fitted 2026-11-09 night to the drawn layer A silhouette of 670 (~/lktest/vase/fit2.py: view rays through a lathe vs the picture mask,
# IoU 0.965): axis 4 units in FRONT of the cell centre (+x, +y), 23 units high (the collision box is only 16), profile (height share, radius):
VASE = dict(h=23.0, dx=4.0, dy=4.0, prof=[(0.0, 3.5), (0.1, 7.75), (0.3, 8.5), (0.6, 7.0), (0.8, 4.75), (0.92, 6.0), (1.0, 5.5)])

# THE BRAZIER STAND (castle, tileset 1, flame $098AAA = Tileset02Anim01): a round foot plate, a thin stem, a knobbed head with the fire bowl on top.
# Fitted 2026-11-09 to the drawn layer A silhouettes (~/lktest/braz/fit.py, lathe vs picture mask by view rays, prongs / flame above the rim
# ignored): short stand of room 51 (27, 44) IoU 0.942, tall stand of room 59 (29, 28) IoU 0.955; both: axis 1 unit in front of the cell centre
# (+x, +y), the same foot and head, the tall stem 24 units longer (stem 4 vs 28). Collision: 2 steps (short) / 4 steps (tall).
BRAZIER_FOOT = [(0.0, 8.44), (1.0, 9.19), (2.0, 8.19), (3.0, 7.19), (4.0, 6.49), (5.0, 6.28), (6.0, 5.66), (7.0, 4.95), (8.0, 4.24), (9.0, 3.54), (10.0, 2.83)]
BRAZIER_HEAD = [(1.0, 3.54), (2.0, 4.24), (3.0, 4.95), (4.0, 5.66), (8.0, 5.66), (9.0, 4.66), (10.0, 3.95), (11.0, 4.24), (14.0, 4.24), (15.0, 4.95),
                (16.0, 5.66), (17.0, 5.66), (18.0, 6.36), (19.0, 6.36), (20.0, 6.78), (21.0, 7.49), (21.5, 6.74)]   # heights above the stem top
BRAZIER = dict(dx=1.0, dy=1.0, stem={2: 4.0, 4: 28.0})   # stem length by collision steps

# THE BARREL (cellars / storerooms of tileset 15, top blocks $051 / $094 / $290 / $35B, one barrel per walkable cell one step above the floor):
# fitted 2026-11-10 to the single barrel of room 71 (21, 15) (~/lktest/barrel/fitq.py: a symmetric barrel grid search, then the rings; IoU 0.986
# with a FLAT top, a free profile reached 0.994 only with a domed top = the open lid drawn as a cone): axis 2 units in front of the cell
# centre (+x, +y), 19 high (the collision box is 16), profile (height, radius) bottom to top with the hoop bulges:
BARREL = dict(dx=2.0, dy=2.0, prof=[(0.0, 8.0), (1.58, 8.46), (3.17, 8.83), (4.75, 8.62), (6.33, 9.33), (7.92, 9.71), (9.5, 10.25), (11.08, 9.46),
                                    (12.67, 9.33), (14.25, 9.38), (15.83, 8.83), (17.42, 8.46), (19.0, 7.5)])

# THE CLAY JAR (chapels of tileset 8, the jar by the angel statue of 597 / 607 / 736): fitted 2026-11-10 to room 597 (30, 25) (~/lktest/jar/fitc.py: free
# rings, then the top 2 rings held at radius >= 5 = the open mouth as a flat lip, IoU 0.986; free 0.990 only with a cone top): axis 3 units in front of
# the cell centre (+x, +y), 23 high (collision 16), belly r 8.5, neck r 4.7, lip r 5.7
JAR = dict(dx=3.0, dy=3.0, prof=[(0.0, 7.24), (1.05, 8.28), (2.09, 7.78), (3.14, 7.99), (4.18, 8.49), (8.36, 8.49), (9.41, 7.49), (10.45, 7.78), (11.5, 6.78),
                                 (12.55, 6.07), (13.59, 5.36), (14.64, 5.66), (15.68, 4.66), (16.73, 4.95), (17.77, 4.95), (18.82, 4.66), (19.86, 5.91), (21.95, 5.66), (23.0, 5.16)])

def hexa(x0, x1, y0, y1, zb, zt):
    """a closed six-sided solid over the rectangle x0..x1 x y0..y1: bottom heights zb(x, y), top heights zt(x, y) at the 4 corners (planes, slopes allowed);
    returns (vertices, faces) with outward counter-clockwise quads (as lathe())"""
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    v = [(x, y, zb(x, y)) for x, y in c] + [(x, y, zt(x, y)) for x, y in c]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    m = [sum(p[i] for p in v) / 8.0 for i in range(3)]; out = []
    for q in f:   # orient every quad outward (normal away from the centre)
        a, b, d = v[q[0]], v[q[1]], v[q[3]]; e1 = [b[i] - a[i] for i in range(3)]; e2 = [d[i] - a[i] for i in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]); fc = [sum(v[k][i] for k in q) / 4.0 - m[i] for i in range(3)]
        out.append(q if sum(n[i] * fc[i] for i in range(3)) > 0 else tuple(reversed(q)))
    return v, out

# BOX FURNITURE WITH A TOP PLATE (body + a top plate that may overhang on the +x / +y side, top plane may slope), fitted by view rays to the drawn
# silhouette (~/lktest/pew/fit.py, multi start over the slopes): units from the corner of the first cell, h at the centre, a / b = slope per unit along x / y,
# ox / oy = plate overhang on the +x / +y side, t = plate thickness.
# THE CHAPEL LECTERN ($2EF, 597 / 607 / 736, one cell, collision 16): 597 (27, 26) IoU 0.947 (the carved notch in its +x face is not in the silhouette);
# the top really slopes (flat top: 0.912), rising towards +y
LECTERN = dict(x0=1.5, x1=16.5, y0=2.5, y1=16.5, h=20.0, a=0.0, b=0.15, ox=2.0, oy=1.0, t=5.5, ns=-1, nd=4.0, fz=4.0)
# THE CHURCH ALTAR ($181 over $185, tileset 3: 613 614 699 700 721, cells x, y .. y + 1, collision 1 step): 613 (26, 27) IoU 0.970, flat top, the plate
# overhangs 2 on +x and 4.5 on +y (the front end)
ALTAR = dict(x0=3.5, x1=17.0, y0=2.0, y1=34.5, h=19.5, a=-0.05, b=0.0, ox=2.0, oy=3.0, t=3.0, ns=1, nd=4.0, fz=4.0)
# THE NICHE (user 2026-11-10 on the outlines: 'die Pulte sind keine 4ecke, sondern haben hinten diesen Ausschnitt'): both have a knee niche at one end:
# the end face is set back nd = 4 units from fz = 4 above the floor up to the plate, a foot stays below it.  Read from the drawn pixels (~/lktest/pult/grid_p.png /
# grid_a.png: the recessed end edge 4 px in from the foot and the plate, the foot ledge 4 rows above the bottom corner); ns = which end (-1: the -y end =
# lectern, +1: the +y end = altar); then the rest refitted with the niche fixed (~/lktest/pew/fitf.py: lectern 0.943 (0.929 without the niche, same window),
# altar 0.969)

def plated_box(cx, cy, floor, L):
    """box furniture L (LECTERN / ALTAR) at the cell (cx, cy) on `floor` (units): body up to the plate + the plate as (vertices, faces) meshes in world units"""
    X0, X1, Y0, Y1 = 16 * cx + L["x0"], 16 * cx + L["x1"], 16 * cy + L["y0"], 16 * cy + L["y1"]; xc, yc = (X0 + X1) / 2, (Y0 + Y1) / 2
    top = lambda x, y: floor + L["h"] + L["a"] * (x - xc) + L["b"] * (y - yc)
    under = lambda x, y: top(x, y) - L["t"]; flo = lambda x, y: floor; foot = lambda x, y: floor + L["fz"]
    if L.get("nd", 0) <= 0: body = [hexa(X0, X1, Y0, Y1, flo, under)]
    elif L["ns"] > 0: body = [hexa(X0, X1, Y0, Y1 - L["nd"], flo, under), hexa(X0, X1, Y1 - L["nd"], Y1, flo, foot)]   # niche at the +y end, the foot below it
    else: body = [hexa(X0, X1, Y0 + L["nd"], Y1, flo, under), hexa(X0, X1, Y0, Y0 + L["nd"], flo, foot)]                  # niche at the -y end
    return body + [hexa(X0, X1 + L["ox"], Y0, Y1 + L["oy"], under, top)]

# THE ANGEL STATUE (chapel, tileset 8: on the 1 step platform $2EB / $2EC of 597 / 607 / 736, cell 27, 24; 2026-11-10 user 'baenke statue und pult'):
# a winged figure = BODY lathe + WINGS as a thin plate. Body fitted by view rays to the drawn silhouette with the wing zone as don't care
# (~/lktest/angel/fit.py, IoU 0.863: the figure is not round), axis 3.5 units in front of the cell centre; the wings = the drawn pixels the body does not
# cover, one row run per picture row (~/lktest/angel/wing.py), standing in a plate 2 thick facing the viewer (plane x + y = axis sum - BACK: the depth is
# not in the picture, BACK = 6 chosen = just behind the body). Body + wings cover the drawn statue with IoU 0.921 (~/lktest/angel/ov.png).
ANGEL = dict(dx=3.5, dy=3.5, back=6.0, prof=[(0.0, 5.7), (2.0, 5.45), (4.0, 4.99), (6.0, 4.74), (8.0, 4.99), (10.0, 4.74), (12.0, 4.49), (14.0, 4.24), (16.0, 4.6), (18.0, 4.95), (20.0, 6.01), (22.0, 7.03), (24.0, 5.66), (26.0, 5.66), (28.0, 5.66), (30.0, 5.66), (32.0, 5.66), (34.0, 5.66), (36.0, 5.66), (38.0, 5.66), (40.0, 5.55), (42.0, 7.05), (44.0, 3.6), (46.0, 0.77), (48.0, 0.5), (48.5, 0.71)],
             wing=[(47.5, -9.0, -6.0), (46.5, -12.0, -5.0), (45.5, -20.0, -4.0), (44.5, -21.0, -4.0), (43.5, -21.0, -6.0), (42.5, -20.0, -8.0), (41.5, -20.0, -8.0), (40.5, -20.0, -8.0), (39.5, -19.0, -8.0), (38.5, -18.0, -8.0), (37.5, -18.0, -8.0), (37.5, 13.0, 16.0), (36.5, -17.0, -8.0), (36.5, 12.0, 16.0), (35.5, -17.0, -8.0), (35.5, 10.0, 16.0), (34.5, -16.0, -8.0), (34.5, 8.0, 16.0), (33.5, -16.0, -8.0), (33.5, 8.0, 16.0), (32.5, -15.0, -8.0), (32.5, 8.0, 16.0), (31.5, -14.0, -8.0), (31.5, 8.0, 16.0), (30.5, -14.0, -8.0), (30.5, 8.0, 16.0), (29.5, -13.0, -8.0), (29.5, 8.0, 16.0), (28.5, -12.0, -8.0), (28.5, 8.0, 16.0), (27.5, -11.0, -8.0), (27.5, 8.0, 16.0), (26.5, -10.0, -8.0), (26.5, 8.0, 16.0), (25.5, -10.0, -8.0), (25.5, 8.0, 16.0), (24.5, -10.0, -8.0), (24.5, 8.0, 16.0), (23.5, -10.0, -8.0), (23.5, 8.0, 16.0), (22.5, -9.0, -8.0), (22.5, 8.0, 16.0), (21.5, -9.0, -8.0), (21.5, 8.0, 16.0), (20.5, 8.0, 16.0), (19.5, 10.0, 16.0), (18.5, 10.0, 16.0), (17.5, 9.0, 12.0)])   # wing rows: (top height, picture offset left, right of the axis (U units))

def box8(v):
    """8 corners (bottom 4 then top 4, same order) -> (vertices, outward quads)"""
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    m = [sum(p[i] for p in v) / 8.0 for i in range(3)]; out = []
    for q in f:
        a, b, d = v[q[0]], v[q[1]], v[q[3]]; e1 = [b[i] - a[i] for i in range(3)]; e2 = [d[i] - a[i] for i in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]); fc = [sum(v[k][i] for k in q) / 4.0 - m[i] for i in range(3)]
        out.append(q if sum(n[i] * fc[i] for i in range(3)) > 0 else tuple(reversed(q)))
    return list(v), out

def angel(cx, cy, floor):
    """the angel statue of the cell (cx, cy) standing on `floor` (units): [body lathe, wing row plates ...] in world units"""
    A = ANGEL; ax, ay = 16 * cx + 8 + A["dx"], 16 * cy + 8 + A["dy"]; top = A["prof"][-1][0]
    out = [lathe(ax, ay, floor, top, [(z / top, r) for z, r in A["prof"]])]
    S = ax + ay - A["back"]; Dax = ax - ay
    for zt, dl, dr in A["wing"]:
        cs = []
        for z in (floor + zt - 1.0, floor + zt):
            for D, w in ((Dax + dl, -0.7), (Dax + dr, -0.7), (Dax + dr, 0.7), (Dax + dl, 0.7)):
                cs.append(((S + D) / 2 + w, (S - D) / 2 + w, z))
        out.append(box8(cs))
    return out

def brazier_prof(steps):
    """the stand's profile [(height, radius)] in units (absolute heights) for a stand of `steps` collision steps"""
    st = 10.0 + BRAZIER["stem"][steps]
    return BRAZIER_FOOT + [(st, 2.83)] + [(st + z, r) for z, r in BRAZIER_HEAD]

def lathe(ax, ay, floor, h, prof, seg=24):
    """a closed solid of revolution around (ax, ay) standing on `floor`: rings of `prof` [(height share, radius)], capped top and bottom;
    returns (vertices, faces) with outward counter-clockwise faces (as the Blender meshes, back face shadow maps)"""
    import math
    v, f = [], []
    for t, r in prof:
        for k in range(seg):
            a = 2 * math.pi * k / seg; v.append((ax + r * math.cos(a), ay + r * math.sin(a), floor + t * h))
    n = len(prof)
    for i in range(n - 1):
        for k in range(seg):
            a0 = i * seg + k; a1 = i * seg + (k + 1) % seg; f.append((a0, a1, a1 + seg, a0 + seg))
    v.append((ax, ay, floor + prof[-1][0] * h)); top = len(v) - 1
    f += [((n - 1) * seg + k, (n - 1) * seg + (k + 1) % seg, top) for k in range(seg)]
    v.append((ax, ay, floor + prof[0][0] * h)); bot = len(v) - 1
    f += [((k + 1) % seg, k, bot) for k in range(seg)]
    return v, f
