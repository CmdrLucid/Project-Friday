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
