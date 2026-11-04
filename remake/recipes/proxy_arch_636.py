"""LIGHT PROXY: Mercator rocky arch over the river, room 636 (MERCATOR_ROCKY_ARCH_OVER_RIVER; landstalker/docs/LIGHT_PROXY_PLAN.md 'Blender shapes', user 2026-11-04: 'mach direkt weiter').
An invisible shape for the lighting only (never drawn). Why: (1) the city wall stands in the height map as height 3 cells (column 14) and its towers as height 12
cells, the automatic proposal turned the towers into small cones (z up to 62 / 76) and gave the drawn ~180 high wall no shape; (2) the terraced grass mound that
bridges the river (cells 18..25 x 38..42, WALKABLE heights 2..5) became hip roofs, one of them up to 142 on the walkable terrace (cells 24..25 x 41..42).
Measured on the original picture (remake/tools/rom_picture.py ROM 636 400 0 820 640, top silhouette scanned per picture column at the wall face):
  wall: face x 240 (column 14 = x 224..240), y 192..960, top ~179 (merlons 175 / 183), on ground 16;
  towers: half cylinders radius 32 on the face (drawn width 78), centres y 446 / 687 / 920 (from the left picture edges U 945 / 705 / ~465), tops 159 / 184 / 188
          (top point = back edge on the face; the drawn tower tops sit BELOW the wall top, as painted); the tower at the far end (rows 12..13) is left out (cut by the room edge);
  mound: the height map's own terrace heights (16 units per step), copied cell by cell below (our measurement), the two blocked tree clumps on it
          (cells 18..19 x 38..40 and 23..25 x 38..39, height 3) with pine crowns up to ~70 (drawn tops V 400 / 440); the two round
          trees are the drawn crowns ON the height 5 cells (21..22, 39).
Run: python3 remake/tools/build_asset.py proxy_arch_636
Output: landstalker/data/proxies/arch_636.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_arch_636/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

# terrace steps of the mound: {(cell x, cell y): height step} (16 units each); river cells under the arch are left out
MOUND = {(20, 40): 4, (21, 40): 4, (22, 40): 4, (23, 40): 4, (24, 40): 3, (25, 40): 2, (21, 39): 5, (22, 39): 5,
         (18, 41): 3, (19, 41): 3, (20, 41): 3, (23, 41): 3, (24, 41): 3, (25, 41): 2,
         (18, 42): 2, (19, 42): 2, (23, 42): 2, (24, 42): 2, (25, 42): 2}

PARTS = [
    ("wall",   224, 192, 240, 960, 0, 179, 179, "flat", None),
    proxy.cylinder("tower_1", 240, 446, 32, 0, 159, -90, 90),
    proxy.cylinder("tower_2", 240, 687, 32, 0, 184, -90, 90),
    proxy.cylinder("tower_3", 240, 920, 32, 0, 188, -90, 90),
    ("trees_l", 288, 608, 320, 656, 0, 48, 72, "hip", None),    # pine clump on the mound (cells 18..19 x 38..40, blocked height 3)
    ("trees_r", 368, 608, 416, 640, 0, 48, 72, "hip", None),    # pines (cells 23..25 x 38..39, blocked height 3)
] + [("t%d_%d" % c, 16 * c[0], 16 * c[1], 16 * c[0] + 16, 16 * c[1] + 16, 0, 16 * h, 16 * h, "flat", None) for c, h in sorted(MOUND.items())]

proxy.build("arch_636", PARTS, "Mercator rocky arch over the river and city wall, room 636",
            {"trees_l": (60, 150, 70), "trees_r": (60, 150, 70)}, target=(300, 640, 80), ground_z=16, px_per_unit=1.0, size=(1000, 900))
