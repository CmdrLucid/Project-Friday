"""LIGHT PROXY: Mercator castle facade, room 31 (MERCATOR_CASTLE_EXTERIOR; landstalker/docs/LIGHT_PROXY_PLAN.md 'Blender shapes', user 2026-11-04: 'weiter mit den naechsten Formen').
An invisible shape for the lighting only (never drawn). Why: the height map holds the castle only as BLOCKED cells of height 0 (rows 14..28), so the automatic
proposal made no facade at all (its wall pixels were read as ground and got dark blotches) and put a hip roof up to 204 onto the entrance stairs instead.
Measured on the original picture (remake/tools/rom_picture.py ROM 31 760 0 1240 900 + remake/tools/proxy_overlay.py with rung planes every 8 units):
  facade: front y 464 (= first free row 29 of the height map; the wall base meets the flower strip there), left end x 352 (picture corner), right end x 992,
          wall top (cornice) 176, green roof roll ~16 high (top 192);
  centre tower: x 624..720 (front corners U 1312 / 1407, centred on the door x 672), front y 496 (the door cells (41, 30), (42, 30) are its niche; row 31 in front
          is the free landing), cornice 228 (left corner V 332), steep cushion roof, flat top 252 set back ~8 (top corners V 308 front, U 1360 / V 290 back -> back y ~448);
  entrance stairs from the height map (cells 39..44 rows 31..32 height 2, landing 41..42 row 31 height 3, step rows 33 / 34 height 1); the blocked height 2 cells
  36..38 / 45..47 of rows 29..32 are planters with pines (drawn tops ~64). Court ground = 0.
Run: python3 remake/tools/build_asset.py proxy_castle_31
Output: landstalker/data/proxies/castle_31.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_castle_31/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

# parts in game coordinates: (name, x0, y0, x1, y1, z0, eave, ridge, roof, ridge axis), see remake/lib/proxy.py
PARTS = [
    ("facade",  352, 224, 992, 464, 0, 176, 192, "hip", None),    # deep box: the castle behind the facade (rows 14..28 blocked); 45 deg roll stands in for the rounded roof
    ("tower",   624, 448, 720, 496, 0, 228, 252, "hip:8", None),  # centre tower in front of the facade (door niche = cells (41, 30), (42, 30)), steep cushion roof
    ("stairs",  624, 496, 720, 528, 0, 32, 32, "flat", None),     # steps of height 2 in front of the tower (cells 39..44, rows 31..32)
    ("trees_l", 576, 464, 624, 528, 0, 32, 64, "hip", None),      # planter (cells 36..38, rows 29..32, height 2, blocked) with its pines (tops ~64 in the picture)
    ("trees_r", 720, 464, 768, 528, 0, 32, 64, "hip", None),      # the same on the right (cells 45..47)
    ("landing", 656, 496, 688, 512, 0, 48, 48, "flat", None),     # top landing at the door, height 3 (cells 41..42, row 31)
    ("step1",   576, 528, 768, 544, 0, 16, 16, "flat", None),     # lowest step row 33 (cells 36..47), height 1
    ("step0",   656, 544, 688, 560, 0, 16, 16, "flat", None),     # row 34 (cells 41..42), height 1
]

proxy.build("castle_31", PARTS, "Mercator castle facade, room 31",
            {"facade": (150, 160, 150), "tower": (120, 170, 160), "stairs": (190, 190, 190), "trees_l": (60, 150, 70), "trees_r": (60, 150, 70), "landing": (210, 210, 210), "step1": (170, 170, 170), "step0": (170, 170, 170)},
            target=(672, 464, 90), ground_z=0, px_per_unit=1.4, size=(1100, 800))
