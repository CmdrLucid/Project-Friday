"""LIGHT PROXY: Mercator fountain court, room 638 (MERCATOR_FOUNTAIN; landstalker/docs/LIGHT_PROXY_PLAN.md 'Blender shapes', user 2026-11-04: 'weiter damit').
An invisible shape for the lighting only (never drawn). Why: the height map holds the city wall only as BLOCKED height 0 cells (column 17) and the round towers as
single blocked cells of height 9 (column 18, rows 26..29 / 38..41 / 50..53), so the automatic proposal made a 32 unit strip with a hip up to 247 IN FRONT of the wall
(cells 18..19 = the walkable bank) and no towers; the pines at the north wall (cells 25..27 x 19..20) got a hip up to 222 (the wall behind them counted as their height).
RE-MEASURED 2026-11-09 (HANDOFF 0a355; same method as the gate 637; projection U = x - y + 1184, V = (x + y) / 2 - z; bank z 48):
  west wall: face x 288 (layer A wall segments, foot on the bank: about half the columns exactly 288, fit_foot), one cell thick (x 272..288);
  towers: BOXES on their collision blocks (column 18 = x 288..304, rows 26..29 / 38..41 / 50..53), like the gate 637 towers: the front
          tower's foot corners sit exactly on U 608 / 624 (V 528 / 536); only the shading is round;
  tops: everything runs out of the picture (black above, cut in steps of 16 picture columns = the drawn merlon blocks); height = the highest
          block start on the front edge: wall 248 (y 864..912), 240 (672..800), 232 / 224 (576..608 / 480..576), 216 / 208 (400..416 / 288..400);
          towers 280 / 264 / 240 (front to back); north wall (face y 288, x 288..) 192 along its whole length;
  the pines at the north wall are catalogue object models (blockcat cells 638: P), no stand-in.
Run: python3 remake/tools/build_asset.py proxy_wall_638
Output: landstalker/data/proxies/wall_638.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_wall_638/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

# parts in game coordinates: (name, x0, y0, x1, y1, z0, eave, ridge, roof, ridge axis) or proxy.cylinder(...), see remake/lib/proxy.py
PARTS = [
    ("wall_a",  272, 864, 288, 912, 48, 248, 248, "flat", None),   # west wall, front segment
    ("wall_b",  272, 672, 288, 800, 48, 240, 240, "flat", None),
    ("wall_c1", 272, 576, 288, 608, 48, 232, 232, "flat", None),
    ("wall_c2", 272, 480, 288, 576, 48, 224, 224, "flat", None),
    ("wall_d1", 272, 400, 288, 416, 48, 216, 216, "flat", None),
    ("wall_d2", 272, 272, 288, 400, 48, 208, 208, "flat", None),   # back segment, runs into the north wall
    ("wall_t1", 272, 800, 288, 864, 48, 248, 248, "flat", None),   # the wall behind each tower (hidden, keeps the wall closed)
    ("wall_t2", 272, 608, 288, 672, 48, 240, 240, "flat", None),
    ("wall_t3", 272, 416, 288, 480, 48, 224, 224, "flat", None),
    ("tower_1", 288, 800, 304, 864, 48, 280, 280, "flat", None),   # boxes on the collision blocks (height map column 18, height 9)
    ("tower_2", 288, 608, 304, 672, 48, 264, 264, "flat", None),
    ("tower_3", 288, 416, 304, 480, 48, 240, 240, "flat", None),
    ("north",   272, 272, 496, 288, 48, 192, 192, "flat", None),   # north wall (row 17 of the blocked rows 12..17), one cell thick like the west wall
]


proxy.build("wall_638", PARTS, "Mercator fountain court city wall, room 638",
            {"north": (200, 195, 170)}, target=(330, 600, 120), ground_z=48, px_per_unit=0.9, size=(1000, 900))
