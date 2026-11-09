"""LIGHT PROXY: Mercator rocky arch over the river, room 636 (MERCATOR_ROCKY_ARCH_OVER_RIVER; landstalker/docs/LIGHT_PROXY_PLAN.md 'Blender shapes', user 2026-11-04: 'mach direkt weiter').
An invisible shape for the lighting only (never drawn). Why: (1) the city wall stands in the height map as height 3 cells (column 14) and its towers as height 12
cells, the automatic proposal turned the towers into small cones (z up to 62 / 76) and gave the drawn ~180 high wall no shape; (2) the terraced grass mound that
bridges the river (cells 18..25 x 38..42, WALKABLE heights 2..5) became hip roofs, one of them up to 142 on the walkable terrace (cells 24..25 x 41..42).
RE-MEASURED 2026-11-09 (HANDOFF 0a357; projection U = x - y + 1184, V = (x + y) / 2 - z; ground 16):
  towers: BOXES on their collision cells (column 14 = x 224..240, rows 12..13 / 25..28 / 40..43 / 55..58, height 12), like the gate 637 and the
          fountain court 638: the left picture edges U 944 (row 25..28 tower) / 1184 (far tower) and the far tower's right edge = the start of the north
          wall (U 1232) sit exactly on those boxes; only the shading is round. Tops 208 (the two front towers, both uncut; the back ones are cut by the
          picture edge lower, same tower = same height);
  west wall: face x 224 (column 13), ONE CELL BEHIND the 2026-11-04 shape: the pine row stands on column 14 (catalogue pines, blockcat cells 636)
          in front of it, between the towers; top 176 in every merlon block where the picture does not cut it;
  north wall: face y 192 (the far tower's right edge U 1232 = x 240), merlon tops 168;
  mound: the height map's terraces (unchanged); the two round trees on the walkable crown cells (21..22, 39): trunks on the terrace (z 64,
          trunk feet U 894 V 427 / U 910 V 436 = within the cells), crowns to 91 / 93 (trees.SMALL_ROUND_636); the left pine clump (cells 18..19 x 38..40,
          collision 48) = three catalogue pines on base 32 placed by their tips (base 48 would put them a cell outside the clump, as at the castle
          planters); the right clump is catalogue pines (no stand-in).
Run: python3 remake/tools/build_asset.py proxy_arch_636
Output: landstalker/data/proxies/arch_636.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_arch_636/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

# terrace steps of the mound: {(cell x, cell y): height step} (16 units each); river cells under the arch are left out
MOUND = {(20, 40): 4, (21, 40): 4, (22, 40): 4, (23, 40): 4, (24, 40): 3, (25, 40): 2, (21, 39): 5, (22, 39): 5,
         (18, 41): 3, (19, 41): 3, (20, 41): 3, (23, 41): 3, (24, 41): 3, (25, 41): 2,
         (18, 42): 2, (19, 42): 2, (23, 42): 2, (24, 42): 2, (25, 42): 2}

import trees
def pine(name, U, V, base):   # the catalogue pine (as proxy_castle_31.pine) placed by its drawn tip (tip z = base + 30)
    s, d = 2 * (V + base + 30), U - 1184; cx, cy = (s + d) / 2, (s - d) / 2
    prof = [(base, 1.5), (base + 4, 1.5), (base + 4, 7.0)]
    for k in range(6):
        z1 = base + 4 + 26 * (k + 1) / 6; prof += [(z1, 7.0 * (1 - k / 6) * 0.45)] + ([(z1, 7.0 * (1 - (k + 1) / 6))] if k < 5 else [])
    return proxy.revolve(name, cx, cy, prof[:-1] + [(base + 30, 0.05)], n=12)

PARTS = [
    ("wall",    208, 192, 224, 960, 0, 176, 176, "flat", None),          # west wall, face x 224 (column 13)
    ("north",   224, 176, 464, 192, 0, 168, 168, "flat", None),          # north wall, face y 192
    ("tower_0", 224, 192, 240, 224, 0, 208, 208, "flat", None),          # towers = collision boxes in column 14
    ("tower_1", 224, 400, 240, 464, 0, 208, 208, "flat", None),
    ("tower_2", 224, 640, 240, 704, 0, 208, 208, "flat", None),
    ("tower_3", 224, 880, 240, 944, 0, 208, 208, "flat", None),
    trees.round_tree("tree_a", 346, 636, 64, trees.SMALL_ROUND_636),     # the two round trees on the mound (walkable crown cells 21..22, 39)
    trees.round_tree("tree_b", 363, 637, 64, trees.SMALL_ROUND_636),
    pine("pine_0", 864, 401, 32), pine("pine_1", 846, 409, 32), pine("pine_2", 834, 417, 32),   # left clump (cells 18..19 x 38..40)
] + [("t%d_%d" % c, 16 * c[0], 16 * c[1], 16 * c[0] + 16, 16 * c[1] + 16, 0, 16 * h, 16 * h, "flat", None) for c, h in sorted(MOUND.items()) if c not in ((21, 39), (22, 39))]

proxy.build("arch_636", PARTS, "Mercator rocky arch over the river and city wall, room 636",
            {}, target=(300, 640, 80), ground_z=16, px_per_unit=1.0, size=(1000, 900))
