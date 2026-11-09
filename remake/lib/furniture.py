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
