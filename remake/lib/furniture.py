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

# THE CHURCH ANGEL STATUE (tileset 3: 613 614 699 700 721, pixel-identical there; user 2026-11-10 'Sockel und Statuen in den Kirchen ja'): stands in a NICHE of
# the -x wall on a 2 x 2 cell pedestal (cells 22..23 x 27..28, 16 high on the dais floor 16; its front face flush with the wall line x = 384, read from the
# drawn rim / bottom corners, ~/lktest/cangel/pov.png) that the game's height map leaves VOID (the light saw a wall up to the room top there) -> data op
# "ground" (LK_LTGROUND v1) gives those cells height 32.  The statue is NOT the chapel drawing (17 % of the pixels equal): axis fixed from its foot point on
# v3 after the user's second marks ('ragt hinaus, weil du den gezeichneten Schatten mitnimmst, unten fehlt immer noch ein Stueck Standfuss'): the statue's pixels
# are taken by COLOUR (not the painted wall shadow 108,108,72 / 72,72,36, not the wall, not the red top, not the pedestal rim beside the robe / foot,
# ~/lktest/cangel/fit.py statue()); the foot reaches down to picture row V 383 (not 377.5) -> axis (375.75, 449.25) near the front of the pedestal centre;
# body may NEVER stick out (covered - 12 x outside, grown from thin rings, r <= 7.5, ~/lktest/cangel/fith2.py), head top rounded (no 1 px spike), wings = the
# rest; together IoU 0.970, 0 px outside the statue (~/lktest/cangel/ov_v3.png)
CHURCH_ANGEL = dict(dx=15.75, dy=9.25, back=6.0, prof=[(0.0, 4.75), (2.0, 4.75), (4.0, 4.75), (6.0, 4.0), (8.0, 4.0), (10.0, 4.0), (12.0, 3.75), (14.0, 3.0), (16.0, 3.75), (18.0, 4.0), (20.0, 4.0), (22.0, 4.25), (24.0, 5.25), (26.0, 7.0), (28.0, 7.5), (30.0, 7.5), (32.0, 7.5), (34.0, 7.5), (36.0, 5.75), (38.0, 4.75), (40.0, 4.25), (42.0, 4.0), (44.0, 3.0), (45.0, 1.5)],
                    wing=[(48.5, 7.5, 10.5), (47.5, 6.5, 13.5), (46.5, 5.5, 21.5), (45.5, 5.5, 22.5), (44.5, 4.5, 22.5), (43.5, 1.5, 2.5), (43.5, 4.5, 21.5), (42.5, 3.5, 21.5), (41.5, 4.5, 21.5), (40.5, 5.5, 20.5), (39.5, 5.5, 19.5), (38.5, -15.5, -11.5), (38.5, 5.5, 19.5), (37.5, -17.5, -10.5), (37.5, 6.5, 18.5), (36.5, -18.5, -8.5), (36.5, 6.5, 18.5), (35.5, -19.5, -7.5), (35.5, 7.5, 17.5), (34.5, -20.5, -8.5), (34.5, 8.5, 17.5), (33.5, -22.5, -9.5), (33.5, 9.5, 16.5), (32.5, -24.5, -10.5), (32.5, 10.5, 15.5), (31.5, -27.5, -10.5), (31.5, 10.5, 15.5), (30.5, -28.5, -10.5), (30.5, 10.5, 14.5), (29.5, -29.5, -10.5), (29.5, 10.5, 13.5), (28.5, -28.5, -10.5), (28.5, 10.5, 12.5), (27.5, -26.5, -10.5), (27.5, 10.5, 11.5), (26.5, -24.5, -10.5), (26.5, 10.5, 11.5), (25.5, -22.5, -10.5), (25.5, 10.5, 11.5), (24.5, -22.5, -10.5), (24.5, 10.5, 11.5), (23.5, -22.5, -10.5), (22.5, -22.5, -9.5), (22.5, 9.5, 10.5), (21.5, -21.5, -9.5), (20.5, -20.5, -7.5), (19.5, -17.5, -6.5), (18.5, -10.5, -6.5), (18.5, 5.5, 6.5)])

# CHURCH ANGEL v4 (user 2026-11-10: 'an den markierten Stellen noch nicht ganz - baust du ein echtes 3D-Modell?'): an exact light model instead of lathe + plates.
# BODY = rings per 2 units of height, each with its own centre offset c along the screen-right axis s = (1, -1) / sqrt 2 and radius r (the twisted, lopsided robe is
# not round about one axis), fitted to the statue's own pixels by moving the LEFT and RIGHT edge of each ring (~/lktest/angel3/body2.py: start = the measured edges,
# never outside the drawing); WINGS = one cell per drawn wing pixel (du = picture column - axis column, v = picture row of the 613 picture), a sheet 1.5 thick
# in the plane x = 371 (v5, user 2026-11-10 'dahinter haben wir harte Kanten an der Wand': the v4 sheet swept back along the screen axis and its left wing stuck into
# the niche's back wall x = 368 = the light cut the wall; the niche is 1 cell deep (x 368..384) and 4 wide (y 416..480), the wings parallel to its back wall fit it).  The triangle mesh projected exactly into the game picture: 1204 statue pixels,
# 0 missed, 3 outside (two hair pixels, one robe), IoU 0.998 (~/lktest/angel3/build.py / check.py).  Remake model with arms / child / feathers: later (own asset).
CHURCH_ANGEL4 = dict(wing_x=371.0, axis=(375.75, 449.25), v0=280, rings=[[0, 0.0, 4.846], [2, 0.0, 4.846], [4, 0.0, 4.846], [6, 0.729, 4.118], [8, 0.354, 4.493], [10, 0.354, 4.493], [12, 0.604, 4.243], [14, 1.311, 3.993], [16, 0.957, 4.596], [18, 0.707, 4.846], [20, 0.354, 3.743], [22, -0.457, 4.553], [24, -0.896, 6.364], [26, 0.332, 6.593], [28, 0.936, 7.196], [30, 1.061, 7.321], [32, 1.061, 7.321], [34, 1.061, 7.321], [36, 0.332, 5.178], [38, 0.707, 5.553], [40, 0.957, 5.303], [42, 1.186, 5.075], [44, 1.789, 4.221], [46, 0.0, 0.3]],
                     wing=[[-29.5, 68], [-28.5, 67], [-28.5, 68], [-28.5, 69], [-27.5, 66], [-27.5, 67], [-27.5, 68], [-27.5, 69], [-26.5, 66], [-26.5, 67], [-26.5, 68], [-26.5, 69], [-26.5, 70], [-25.5, 66], [-25.5, 67], [-25.5, 68], [-25.5, 69], [-25.5, 70], [-24.5, 65], [-24.5, 66], [-24.5, 67], [-24.5, 68], [-24.5, 69], [-24.5, 70], [-24.5, 71], [-23.5, 65], [-23.5, 66], [-23.5, 67], [-23.5, 68], [-23.5, 69], [-23.5, 70], [-23.5, 71], [-22.5, 64], [-22.5, 65], [-22.5, 66], [-22.5, 67], [-22.5, 68], [-22.5, 69], [-22.5, 70], [-22.5, 71], [-22.5, 72], [-22.5, 73], [-22.5, 74], [-22.5, 75], [-21.5, 64], [-21.5, 65], [-21.5, 66], [-21.5, 67], [-21.5, 68], [-21.5, 69], [-21.5, 70], [-21.5, 71], [-21.5, 72], [-21.5, 73], [-21.5, 74], [-21.5, 75], [-21.5, 76], [-20.5, 63], [-20.5, 64], [-20.5, 65], [-20.5, 66], [-20.5, 67], [-20.5, 68], [-20.5, 69], [-20.5, 70], [-20.5, 71], [-20.5, 72], [-20.5, 73], [-20.5, 74], [-20.5, 75], [-20.5, 76], [-20.5, 77], [-19.5, 62], [-19.5, 63], [-19.5, 64], [-19.5, 65], [-19.5, 66], [-19.5, 67], [-19.5, 68], [-19.5, 69], [-19.5, 70], [-19.5, 71], [-19.5, 72], [-19.5, 73], [-19.5, 74], [-19.5, 75], [-19.5, 76], [-19.5, 77], [-18.5, 61], [-18.5, 62], [-18.5, 63], [-18.5, 64], [-18.5, 65], [-18.5, 66], [-18.5, 67], [-18.5, 68], [-18.5, 69], [-18.5, 70], [-18.5, 71], [-18.5, 72], [-18.5, 73], [-18.5, 74], [-18.5, 75], [-18.5, 76], [-18.5, 77], [-17.5, 60], [-17.5, 61], [-17.5, 62], [-17.5, 63], [-17.5, 64], [-17.5, 65], [-17.5, 66], [-17.5, 67], [-17.5, 68], [-17.5, 69], [-17.5, 70], [-17.5, 71], [-17.5, 72], [-17.5, 73], [-17.5, 74], [-17.5, 75], [-17.5, 76], [-17.5, 77], [-17.5, 78], [-16.5, 60], [-16.5, 61], [-16.5, 62], [-16.5, 63], [-16.5, 64], [-16.5, 65], [-16.5, 66], [-16.5, 67], [-16.5, 68], [-16.5, 69], [-16.5, 70], [-16.5, 71], [-16.5, 72], [-16.5, 73], [-16.5, 74], [-16.5, 75], [-16.5, 76], [-16.5, 77], [-16.5, 78], [-15.5, 59], [-15.5, 60], [-15.5, 61], [-15.5, 62], [-15.5, 63], [-15.5, 64], [-15.5, 65], [-15.5, 66], [-15.5, 67], [-15.5, 68], [-15.5, 69], [-15.5, 70], [-15.5, 71], [-15.5, 72], [-15.5, 73], [-15.5, 74], [-15.5, 75], [-15.5, 76], [-15.5, 77], [-15.5, 78], [-14.5, 59], [-14.5, 60], [-14.5, 61], [-14.5, 62], [-14.5, 63], [-14.5, 64], [-14.5, 65], [-14.5, 66], [-14.5, 67], [-14.5, 68], [-14.5, 69], [-14.5, 70], [-14.5, 71], [-14.5, 72], [-14.5, 73], [-14.5, 74], [-14.5, 75], [-14.5, 76], [-14.5, 77], [-14.5, 78], [-13.5, 59], [-13.5, 60], [-13.5, 61], [-13.5, 62], [-13.5, 63], [-13.5, 64], [-13.5, 65], [-13.5, 66], [-13.5, 67], [-13.5, 68], [-13.5, 69], [-13.5, 70], [-13.5, 71], [-13.5, 72], [-13.5, 73], [-13.5, 74], [-13.5, 75], [-13.5, 76], [-13.5, 77], [-13.5, 78], [-12.5, 59], [-12.5, 60], [-12.5, 61], [-12.5, 62], [-12.5, 63], [-12.5, 64], [-12.5, 65], [-12.5, 66], [-12.5, 67], [-12.5, 68], [-12.5, 69], [-12.5, 70], [-12.5, 71], [-12.5, 72], [-12.5, 73], [-12.5, 74], [-12.5, 75], [-12.5, 76], [-12.5, 77], [-12.5, 78], [-11.5, 60], [-11.5, 61], [-11.5, 62], [-11.5, 63], [-11.5, 64], [-11.5, 65], [-11.5, 66], [-11.5, 67], [-11.5, 68], [-11.5, 69], [-11.5, 70], [-11.5, 71], [-11.5, 72], [-11.5, 73], [-11.5, 74], [-11.5, 75], [-11.5, 76], [-11.5, 77], [-11.5, 78], [-10.5, 61], [-10.5, 62], [-10.5, 63], [-10.5, 64], [-10.5, 65], [-10.5, 66], [-10.5, 67], [-10.5, 68], [-10.5, 69], [-10.5, 70], [-10.5, 71], [-10.5, 72], [-10.5, 73], [-10.5, 74], [-10.5, 78], [-10.5, 79], [-9.5, 61], [-9.5, 62], [-9.5, 63], [-9.5, 64], [-9.5, 65], [-9.5, 66], [-9.5, 67], [-9.5, 68], [-9.5, 69], [-9.5, 70], [-9.5, 71], [-9.5, 72], [-9.5, 73], [-9.5, 79], [-8.5, 62], [-8.5, 63], [-8.5, 79], [-7.5, 62], [-7.5, 63], [4.5, 53], [5.5, 51], [5.5, 52], [5.5, 53], [5.5, 79], [6.5, 50], [6.5, 51], [6.5, 52], [6.5, 53], [6.5, 54], [7.5, 49], [7.5, 50], [7.5, 51], [7.5, 52], [7.5, 53], [7.5, 54], [8.5, 49], [8.5, 50], [8.5, 51], [8.5, 52], [8.5, 53], [8.5, 54], [8.5, 55], [8.5, 56], [8.5, 57], [8.5, 58], [8.5, 59], [8.5, 60], [8.5, 61], [8.5, 62], [8.5, 76], [9.5, 49], [9.5, 50], [9.5, 51], [9.5, 52], [9.5, 53], [9.5, 54], [9.5, 55], [9.5, 56], [9.5, 57], [9.5, 58], [9.5, 59], [9.5, 60], [9.5, 61], [9.5, 62], [9.5, 63], [9.5, 75], [10.5, 50], [10.5, 51], [10.5, 52], [10.5, 53], [10.5, 54], [10.5, 55], [10.5, 56], [10.5, 57], [10.5, 58], [10.5, 59], [10.5, 60], [10.5, 61], [10.5, 62], [10.5, 63], [11.5, 50], [11.5, 51], [11.5, 52], [11.5, 53], [11.5, 54], [11.5, 55], [11.5, 56], [11.5, 57], [11.5, 58], [11.5, 59], [11.5, 60], [11.5, 61], [11.5, 62], [11.5, 63], [11.5, 64], [11.5, 65], [11.5, 66], [11.5, 67], [11.5, 68], [11.5, 69], [12.5, 50], [12.5, 51], [12.5, 52], [12.5, 53], [12.5, 54], [12.5, 55], [12.5, 56], [12.5, 57], [12.5, 58], [12.5, 59], [12.5, 60], [12.5, 61], [12.5, 62], [12.5, 63], [12.5, 64], [12.5, 65], [12.5, 66], [12.5, 67], [12.5, 68], [13.5, 51], [13.5, 52], [13.5, 53], [13.5, 54], [13.5, 55], [13.5, 56], [13.5, 57], [13.5, 58], [13.5, 59], [13.5, 60], [13.5, 61], [13.5, 62], [13.5, 63], [13.5, 64], [13.5, 65], [13.5, 66], [13.5, 67], [14.5, 51], [14.5, 52], [14.5, 53], [14.5, 54], [14.5, 55], [14.5, 56], [14.5, 57], [14.5, 58], [14.5, 59], [14.5, 60], [14.5, 61], [14.5, 62], [14.5, 63], [14.5, 64], [14.5, 65], [14.5, 66], [15.5, 51], [15.5, 52], [15.5, 53], [15.5, 54], [15.5, 55], [15.5, 56], [15.5, 57], [15.5, 58], [15.5, 59], [15.5, 60], [15.5, 61], [15.5, 62], [15.5, 63], [15.5, 64], [16.5, 51], [16.5, 52], [16.5, 53], [16.5, 54], [16.5, 55], [16.5, 56], [16.5, 57], [16.5, 58], [16.5, 59], [16.5, 60], [16.5, 61], [16.5, 62], [16.5, 63], [17.5, 51], [17.5, 52], [17.5, 53], [17.5, 54], [17.5, 55], [17.5, 56], [17.5, 57], [17.5, 58], [17.5, 59], [17.5, 60], [17.5, 61], [18.5, 51], [18.5, 52], [18.5, 53], [18.5, 54], [18.5, 55], [18.5, 56], [18.5, 57], [18.5, 58], [18.5, 59], [19.5, 51], [19.5, 52], [19.5, 53], [19.5, 54], [19.5, 55], [19.5, 56], [19.5, 57], [20.5, 51], [20.5, 52], [20.5, 53], [20.5, 54], [20.5, 55], [20.5, 56], [21.5, 52], [21.5, 53]])

def church_angel4(floor):
    """the exact light model of the church angel (CHURCH_ANGEL4), standing on `floor` (units): [(vertices, faces)] in world units"""
    import math
    A = CHURCH_ANGEL4; AX, AY = A["axis"]; ASUM = AX + AY; SQ2 = math.sqrt(2.0); RZ = [z for z, c, r in A["rings"]]
    C = {z: c for z, c, r in A["rings"]}; Rr = {z: r for z, c, r in A["rings"]}
    def ip(tab, z):
        if z <= RZ[0]: return tab[RZ[0]]
        if z >= RZ[-1]: return tab[RZ[-1]]
        i = int(z // 2); t = (z - RZ[i]) / 2.0; return tab[RZ[i]] + (tab[RZ[i + 1]] - tab[RZ[i]]) * t
    W = lambda s, f, zl: (AX + (s + f) / SQ2, AY + (f - s) / SQ2, floor + zl)
    V, F = [], []
    def add(p): V.append(p); return len(V) - 1
    SEG = 32; rings = []; ztop = RZ[-1]
    for k in range(0, int(ztop) + 1):
        c = ip(C, k); r = ip(Rr, k); rings.append([add(W(c + r * math.cos(2 * math.pi * j / SEG), r * math.sin(2 * math.pi * j / SEG), k)) for j in range(SEG)])
    for a, b in zip(rings, rings[1:]):
        for j in range(SEG): F.append((a[j], a[(j + 1) % SEG], b[(j + 1) % SEG], b[j]))
    bot = add(W(ip(C, 0), 0, 0)); top = add(W(ip(C, ztop), 0, ztop))
    for j in range(SEG): F.append((rings[0][(j + 1) % SEG], rings[0][j], bot)); F.append((rings[-1][j], rings[-1][(j + 1) % SEG], top))
    wing = {(du, v) for du, v in A["wing"]}; cache = {}; TH = 0.75; XW = A["wing_x"]   # v5: the wings stand in a plane PARALLEL to the niche's back wall
    AU = AX - AY + 1184.0
    def vid(du, v, off):   # picture corner (U = AU + du, V = v0 + v) on the plane x = XW, moved by off along the view ray (1, 1, 1): same picture point
        k = (du, v, off)
        if k not in cache:
            U = AU + du; y = XW + 1184.0 - U; z = (XW + y) / 2.0 - (A["v0"] + v)
            cache[k] = add((XW + off, y + off, z + off))
        return cache[k]
    for (du, v) in sorted(wing):
        a, b = du, du + 1
        F.append((vid(a, v, TH), vid(b, v, TH), vid(b, v + 1, TH), vid(a, v + 1, TH))); F.append((vid(a, v, -TH), vid(a, v + 1, -TH), vid(b, v + 1, -TH), vid(b, v, -TH)))
        for n, e0, e1 in (((du - 1, v), (a, v), (a, v + 1)), ((du + 1, v), (b, v + 1), (b, v)), ((du, v - 1), (b, v), (a, v)), ((du, v + 1), (a, v + 1), (b, v + 1))):
            if n not in wing: F.append((vid(e0[0], e0[1], TH), vid(e1[0], e1[1], TH), vid(e1[0], e1[1], -TH), vid(e0[0], e0[1], -TH)))
    return [(V, F)]

def box8(v):
    """8 corners (bottom 4 then top 4, same order) -> (vertices, outward quads)"""
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    m = [sum(p[i] for p in v) / 8.0 for i in range(3)]; out = []
    for q in f:
        a, b, d = v[q[0]], v[q[1]], v[q[3]]; e1 = [b[i] - a[i] for i in range(3)]; e2 = [d[i] - a[i] for i in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]); fc = [sum(v[k][i] for k in q) / 4.0 - m[i] for i in range(3)]
        out.append(q if sum(n[i] * fc[i] for i in range(3)) > 0 else tuple(reversed(q)))
    return list(v), out

def angel(cx, cy, floor, A=None):
    """an angel statue (A = ANGEL / CHURCH_ANGEL) of the cell (cx, cy) standing on `floor` (units): [body lathe, wing row plates ...] in world units"""
    A = A or ANGEL; ax, ay = 16 * cx + 8 + A["dx"], 16 * cy + 8 + A["dy"]; top = A["prof"][-1][0]
    out = [lathe(ax, ay, floor, top, [(z / top, r) for z, r in A["prof"]])]
    S = ax + ay - A["back"]; Dax = ax - ay
    for zt, dl, dr in A["wing"]:
        cs = []
        for z in (floor + zt - 1.0, floor + zt):
            for D, w in ((Dax + dl, -0.7), (Dax + dr, -0.7), (Dax + dr, 0.7), (Dax + dl, 0.7)):
                cs.append(((S + D) / 2 + w, (S - D) / 2 + w, z))
        out.append(box8(cs))
    return out

# NEAR-FINAL BARREL GEOMETRY (user 2026-11-10: forms close to the final remake version right away, materials later; reference + numbers in remake/MODELS.md):
# the fitted outline BARREL["prof"] is the outer envelope (= the hoops); measured on the drawing of room 71 (21, 15) by which pixels are hoop grey
# (72,72,72 / 36,36,36) at which model height (~/lktest/barrel/hoops.py): hoops at z 1..3.5, 9..11.5, 15.5..17.5, the top rim = a metal ring; the wood
# between the hoops lies 0.35 lower, 16 staves with shallow V grooves, the lid recessed 1.5 below the rim with 4 planks along the screen axis (1, -1).
BARREL_HOOPS = [(1.0, 3.5), (9.0, 11.5), (15.5, 17.5)]

def barrel_mesh(ax, ay, floor, seg=64, staves=16):
    """near-final barrel: [(vertices, faces)] in world units (closed, outward quads / triangles)"""
    import math
    P = BARREL["prof"]; top = P[-1][0]
    def env(z):
        for (z0, r0), (z1, r1) in zip(P, P[1:]):
            if z0 <= z <= z1: return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return P[-1][1]
    def hoop(z): return any(a <= z <= b for a, b in BARREL_HOOPS) or z >= top - 0.6 or z <= 0.6   # + the stave ends (chimes) at top and bottom
    def rad(z, th):
        r = env(z)
        if hoop(z): return r
        g = abs(((th / (2 * math.pi) * staves) % 1.0) - 0.5) * 2.0          # 0 at a stave seam, 1 in the stave middle
        return r - 0.35 - 0.18 * (1.0 - min(1.0, g * 3.0))                   # wood below the hoops + a V groove at each seam
    zs = sorted(set([round(0.25 * k, 2) for k in range(0, int(top * 4) + 1)] + [a for h in BARREL_HOOPS for a in h] + [top]))
    V, F = [], []
    def add(p): V.append(p); return len(V) - 1
    rings = [[add((ax + rad(z, 2 * math.pi * j / seg) * math.cos(2 * math.pi * j / seg), ay + rad(z, 2 * math.pi * j / seg) * math.sin(2 * math.pi * j / seg), floor + z)) for j in range(seg)] for z in zs]
    for a, b in zip(rings, rings[1:]):
        for j in range(seg): F.append((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
    bot = add((ax, ay, floor))
    for j in range(seg): F.append((rings[0][(j + 1) % seg], rings[0][j], bot))
    # top: rim lip inwards (to radius rt - 0.9), inner wall down 1.5, lid with 4 planks (grooves 0.25 deep between them, along the screen axis (1, -1))
    rt = env(top); ri = rt - 0.9; zl = top - 1.5
    lip = [add((ax + ri * math.cos(2 * math.pi * j / seg), ay + ri * math.sin(2 * math.pi * j / seg), floor + top)) for j in range(seg)]
    inner = [add((ax + ri * math.cos(2 * math.pi * j / seg), ay + ri * math.sin(2 * math.pi * j / seg), floor + zl)) for j in range(seg)]
    for j in range(seg):
        F.append((rings[-1][j], rings[-1][(j + 1) % seg], lip[(j + 1) % seg], lip[j]))
        F.append((lip[j], lip[(j + 1) % seg], inner[(j + 1) % seg], inner[j]))
    n = 24; grid = {}
    for i in range(-n, n + 1):
        for k in range(-n, n + 1):
            u, w = ri * i / n, ri * k / n                                      # u along (1, -1) / sqrt 2 (plank direction), w across
            if u * u + w * w > (ri * 1.02) ** 2: continue
            gw = abs(((w / ri + 1.0) * 2.0) % 1.0 - 0.5) * 2.0                   # 4 planks across: 0 at a joint
            dz = -0.25 * (1.0 - min(1.0, gw * 4.0))
            grid[(i, k)] = add((ax + (u + w) / math.sqrt(2), ay + (w - u) / math.sqrt(2), floor + zl + dz))
    for (i, k), a in grid.items():
        b, c, d = grid.get((i + 1, k)), grid.get((i + 1, k + 1)), grid.get((i, k + 1))
        if b is not None and c is not None and d is not None: F.append((a, d, c, b))
    # close the gap between the lid grid edge and the inner wall bottom: a fan from each inner wall vertex to the nearest grid vertices
    edge = [(math.atan2(V[g][1] - ay, V[g][0] - ax), g) for (i, k), g in grid.items() if any(nb not in grid for nb in ((i + 1, k), (i - 1, k), (i, k + 1), (i, k - 1)))]
    edge.sort()
    for t in range(len(edge)):
        a1, g1 = edge[t]; a2, g2 = edge[(t + 1) % len(edge)]
        j1 = int(round((a1 % (2 * math.pi)) / (2 * math.pi) * seg)) % seg; j2 = int(round((a2 % (2 * math.pi)) / (2 * math.pi) * seg)) % seg
        F.append((inner[j1], g2, g1) if False else (g1, g2, inner[j2]))
        if j1 != j2: F.append((g1, inner[j2], inner[j1]))
    return [(V, F)]

def revolve(ax, ay, floor, pts, seg=64):
    """a closed solid of revolution around (ax, ay) from a profile polyline pts [(r, z)] that starts and ends on the axis (r = 0), e.g. outside up, over a lip,
    inside down; faces follow the polyline direction (outward like lathe())"""
    import math
    V, F = [], []; rings = []
    for r, z in pts:
        if r <= 1e-6: V.append((ax, ay, floor + z)); rings.append(("pole", len(V) - 1))
        else:
            b = len(V); V.extend((ax + r * math.cos(2 * math.pi * j / seg), ay + r * math.sin(2 * math.pi * j / seg), floor + z) for j in range(seg)); rings.append(("ring", b))
    for (ka, a), (kb, b) in zip(rings, rings[1:]):
        if ka == "ring" and kb == "ring":
            for j in range(seg): F.append((a + j, a + (j + 1) % seg, b + (j + 1) % seg, b + j))
        elif ka == "pole" and kb == "ring":
            for j in range(seg): F.append((a, b + (j + 1) % seg, b + j)) if False else F.append((b + j, a, b + (j + 1) % seg))
        elif ka == "ring" and kb == "pole":
            for j in range(seg): F.append((a + j, a + (j + 1) % seg, b))
    return V, F

# NEAR-FINAL CLAY JAR (reference room 597 (30, 25), remake/MODELS.md): the fitted outline JAR["prof"] outside; the drawing shows an OPEN mouth (black inside,
# rows 43..48 of the reference window, ~10 px wide -> inner radius 3.6) inside a grey lip ring (outer r 5.7): the lip is rolled over (round top at z 23) into a
# hollow neck 6 deep with a flat inner bottom; the red band on the shoulder and the grey lower body are paint (material later).
def jar_mesh(ax, ay, floor, seg=64, BASE_R=6.2, LIP_DROP=0.8, SMOOTH=1):
    import math
    J = JAR; out = [(BASE_R, 0.0), (7.0, 0.6), (7.7, 1.05)] + [(r, z) for z, r in J["prof"][2:-1]]   # outside up to the lip's outer edge; the foot bevelled so
    # that its front edge stays above picture row 71 (exact triangle projection: the sampled fit let the foot ring stick out 1 row)
    for _ in range(SMOOTH):   # the fitted radii carry the drawing's pixel steps (ripples); a real jar is smooth: 3-tap average, ends kept
        out = [out[0]] + [((a[0] + 2 * b[0] + c[0]) / 4.0, b[1]) for a, b, c in zip(out, out[1:], out[2:])] + [out[-1]]
    zt = J["prof"][-1][0]; ro = J["prof"][-2][1]; ri = 3.6
    lip = []
    for k in range(1, 8):                                                   # half round over the top from the outer edge to the inner edge
        t = math.pi * k / 8; c = (ro + ri) / 2; w = (ro - ri) / 2
        lip.append((c + w * math.cos(t), zt - LIP_DROP + LIP_DROP * math.sin(t)))
    inside = [(ri, zt - 1.2), (ri - 0.2, zt - 4.0), (ri - 0.5, zt - 6.0), (0.0, zt - 6.0)]
    return [revolve(ax, ay, floor, [(0.0, 0.0)] + out + lip + inside, seg)]

def vessel_mesh(ax, ay, floor, prof, ri, depth, foot=None, smooth=1, lip_drop=0.8, seg=64, spline=False):
    """near-final open vessel (jar / vase): outside = prof [(z, r)] (absolute heights, the last knot = the top of the lip), the second last = the lip's outer
    edge; a rolled lip (half round) to the inner radius ri, a hollow neck `depth` deep with a flat bottom; foot = replacement for the first knots
    [(r, z), ..] (bevel); outline radii smoothed `smooth` times (3-tap: the drawing's pixel steps)"""
    import math
    out = (list(foot) if foot else [(prof[0][1], prof[0][0])]) + [(r, z) for z, r in prof[(len(foot) if foot else 1):-1]]
    for _ in range(smooth):
        out = [out[0]] + [((a[0] + 2 * b[0] + c[0]) / 4.0, b[1]) for a, b, c in zip(out, out[1:], out[2:])] + [out[-1]]
    if spline and len(out) >= 3:   # Catmull-Rom through the knots, 4 steps per span: no kinks between the measured knots, the knots themselves unchanged
        q = [out[0]] + out + [out[-1]]; res = []
        for i in range(1, len(q) - 2):
            p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
            for k in range(4):
                t = k / 4.0; t2 = t * t; t3 = t2 * t
                res.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
        out = res + [out[-1]]
    zt = prof[-1][0]; ro = out[-1][0]; lip = []
    for k in range(1, 8):
        t = math.pi * k / 8; c = (ro + ri) / 2; w = (ro - ri) / 2
        lip.append((c + w * math.cos(t), zt - lip_drop + lip_drop * math.sin(t)))
    inside = [(ri, zt - 1.2), (ri - 0.2, zt - depth * 0.6), (ri - 0.5, zt - depth), (0.0, zt - depth)]
    return [revolve(ax, ay, floor, [(0.0, 0.0)] + out + lip + inside, seg)]

def tube(pts, radii, seg=10):
    """a closed tapered tube along the polyline pts [(x, y, z)] with radii per point (cones at the ends): (vertices, faces)"""
    import math
    V, F = [], []
    def norm(v):
        l = math.sqrt(sum(c * c for c in v)) or 1.0; return tuple(c / l for c in v)
    def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    rings = []
    for i, (p, r) in enumerate(zip(pts, radii)):
        d = norm(tuple(pts[min(i + 1, len(pts) - 1)][k] - pts[max(i - 1, 0)][k] for k in range(3)))
        a = norm(cross(d, (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0))); b = cross(d, a)
        b0 = len(V); V.extend(tuple(p[k] + r * (math.cos(2 * math.pi * j / seg) * a[k] + math.sin(2 * math.pi * j / seg) * b[k]) for k in range(3)) for j in range(seg)); rings.append(b0)
    for a0, a1 in zip(rings, rings[1:]):
        for j in range(seg): F.append((a0 + j, a0 + (j + 1) % seg, a1 + (j + 1) % seg, a1 + j))
    V.append(pts[0]); s0 = len(V) - 1; V.append(pts[-1]); s1 = len(V) - 1
    for j in range(seg): F.append((rings[0] + (j + 1) % seg, rings[0] + j, s0)); F.append((rings[-1] + j, rings[-1] + (j + 1) % seg, s1))
    return V, F

# NEAR-FINAL BRAZIER STAND (references room 51 (27, 44) short, 59 (29, 28) tall; remake/MODELS.md): the turned body (foot disc, stem, knobbed head) from the
# fitted outline (Catmull-Rom through the knots), an OPEN bowl on top (grey, inner radius 5.3, 2.5 deep) and its PRONGS as drawn (window rows 48..60 of the
# short reference): two tall curved prongs left / right of the flame (screen offset ~5.5 px, rising ~11 above the rim) + two more behind them, and a short
# leaf on each side pointing outwards along the screen axis (offset ~9..11 px, ~4 above the rim). The flame itself is light / paint, no geometry.
BRAZIER_PRONGS = dict(rim_rel=18.0, rim=6.0, petals=[(47.0, 7.0, 1.3), (133.0, 7.0, 1.3), (227.0, 7.0, 1.3), (313.0, 7.0, 1.3)], petal_out=0.5,
                      leaves=[(0.0, 4.0, 4.2), (180.0, 4.0, 4.2)])
# v2 after the user ('die Krone oben stimmt noch gar nicht mit dem Sprite ueberein'): read on the 1 px grid of the short reference (~/lktest/braz/crown.png):
# the bowl opening is the dark ellipse around the flame's foot, centre row 57 = z 32 (rim r ~6) - the old outline's top 3.5 units (r up to 7.5) were the CROWN.
# The tall prong left / right of the flame (rows 48..60, 2 px grey, ~6 px from the axis) = a FRONT and a BACK petal at the same screen offset drawn as one
# (petals at +-40 / +-140 degrees from the screen-right axis, 5.5 high, leaning out 1.3); the short leaf on each side (rows 53..56, reaching ~12 px out) =
# a petal at 0 / 180 degrees bent outwards (3.0 out, 2.6 up).  petals: (angle, height, base thickness); leaves: (angle, outward, up).

def brazier_mesh(ax, ay, floor, steps, SPL=False):
    import math
    P = brazier_prof(steps); BP = BRAZIER_PRONGS; st = 10.0 + BRAZIER["stem"][steps]; top = st + BP["rim_rel"]
    prof = [p for p in P if p[0] < top - 0.4] + [(top - 0.4, BP["rim"]), (top, BP["rim"])]
    meshes = list(vessel_mesh(ax, ay, floor, prof, ri=BP["rim"] - 0.9, depth=2.5, smooth=0, lip_drop=0.4, spline=SPL)); SQ = math.sqrt(2.0)
    def at(ang, rho, z):   # angle from the screen-right axis s = (1, -1) / sqrt 2 towards the viewer axis f = (1, 1) / sqrt 2
        s_ = rho * math.cos(math.radians(ang)); f_ = rho * math.sin(math.radians(ang))
        return (ax + (s_ + f_) / SQ, ay + (f_ - s_) / SQ, floor + z)
    rr = BP["rim"] - 0.45
    for ang, h, th in BP["petals"]:   # upright petal on the rim, leaning out, pointed
        pts = [at(ang, rr + BP["petal_out"] * (k / 6.0) ** 1.5, top - 0.3 + h * k / 6.0) for k in range(7)]
        meshes.append(tube(pts, [th, th, th * 0.9, th * 0.75, th * 0.55, th * 0.35, 0.08]))
    for ang, out, up in BP["leaves"]:   # side petal bent outwards
        pts = [at(ang, rr + out * k / 5.0, top - 0.3 + up * math.sin(math.pi * 0.5 * k / 5.0)) for k in range(6)]
        meshes.append(tube(pts, [1.15, 1.1, 0.95, 0.75, 0.45, 0.08]))
    return meshes

# NEAR-FINAL VASE (reference room 670 (18, 24) / (18, 25), remake/MODELS.md): the drawing shows an OPEN mouth (dark inside, lip ring ~18 px wide -> outer
# r 6.0, inner ~12 px -> ri 4.2) over a short neck, wide shoulder and belly; the white glaze pattern is paint (material later).
# v2 outline (2026-11-10): refitted with the vase's OWN pixels (the black floor shadow under the foot left out) on the LEFT half of the front vase (the right
# half overlaps the back vase), knots every 2 units, never outside (~/lktest/vase2/fitv.py: 251 of 257 px, 0 outside); the old VASE lathe was 0.914 in the
# exact projection.
VASE_PROF2 = [(0.0, 3.5), (2.0, 5.5), (4.0, 6.75), (6.0, 8.25), (8.0, 8.5), (10.0, 8.5), (12.0, 8.0), (14.0, 6.75), (16.0, 5.75), (18.0, 5.25), (20.0, 5.25),
              (22.0, 5.5), (22.5, 5.5)]
def vase_mesh(ax, ay, floor):
    return vessel_mesh(ax, ay, floor, VASE_PROF2, ri=4.2, depth=7.0, smooth=0, lip_drop=0.5, spline=True)

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
