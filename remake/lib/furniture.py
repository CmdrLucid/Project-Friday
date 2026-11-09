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

# THE MERCATOR TABLE (room 670, MERCATOR_HOUSE_NEAR_WELL_FIRST_FLOOR), measured 2026-11-09 on 8x zooms of the drawing: the top's four corners sit
# exactly on its collision cells (22..24 x 22..23 = x 352..400, y 352..384, walkable height 1 = 16); edge band down to ~11 (thickness 5); legs
# ~4 units (5 picture columns), their floor feet at (354, 381) / (397, 381) / (397, 354) = 2..3 in from the outer corners.
MERCATOR_TABLE = dict(thick=5, leg=4, inset=1, outline=1)

# THE CASTLE TABLE (Mercator castle rooms, tileset 1: gold rim, curved legs), measured 2026-11-09 on room 96 (cells 20..22 x 21..23, height 1):
# top corners U 1167.5 / 1120 / 1215 / 1167 = exactly the 3 x 3 cells at z 16, gold edge band ~6, curved legs ~5 wide standing AT the corners.
CASTLE_TABLE = dict(thick=6, leg=5, inset=0, outline=1)
