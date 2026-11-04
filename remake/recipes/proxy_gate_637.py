"""LIGHT PROXY: Mercator north gate, room 637 (MERCATOR_NORTH_GATE; landstalker/docs/LIGHT_PROXY_PLAN.md 'Blender shapes', user 2026-11-04: 'mach direkt weiter').
An invisible shape for the lighting only (never drawn). Why: the height map holds the gate wall, its two round towers and the high wall behind them only as column 15
(heights 6 / 8) or not at all (the gate wall stands behind the walkable column 15 of rows 30..41); the automatic proposal left all of them flat (objects 3 / 4 'flat').
Measured on the original picture (remake/tools/rom_picture.py ROM 637 600 0 700 500, top silhouette scanned per picture column; base line checked on a ground grid):
  gate wall: face x 240 (its base meets the x 240 grid line), y 480..672, top 128 (merlons), gatehouse over the door y 560..608 up to 160;
  left tower: half cylinder radius 32 on the face x 240, centre y 702 (left picture edge U 690), top 199 (back edge, flat drawn top V 256);
  big tower: half cylinder radius 32 on the face x 256, centre y 476 (U 930..1010), top 222 (flat drawn top V 128);
  high wall behind: face x 256 (column 15 blocked), y 288..444, top falling from ~235 to ~192 (segments below);
  pines in front of the wall on the blocked cells of row 21 (cells 16..20, height 4): crowns ~96.
Run: python3 remake/tools/build_asset.py proxy_gate_637
Output: landstalker/data/proxies/gate_637.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_gate_637/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

PARTS = [
    ("gate_wall",  224, 480, 240, 672, 0, 128, 128, "flat", None),
    ("gatehouse",  224, 560, 240, 608, 0, 160, 160, "flat", None),   # drawn U 815..865 on the face x 240
    proxy.cylinder("tower_left", 240, 702, 32, 0, 199, -90, 90),
    ("left_wall",  224, 672, 240, 736, 0, 128, 128, "flat", None),  # wall behind the left tower (column 15 rows 42..45 blocked)
    proxy.cylinder("tower_big", 256, 476, 32, 0, 222, -90, 90),
    ("wall_1",     240, 400, 256, 448, 0, 232, 232, "flat", None),  # high wall behind the big tower
    ("wall_2",     240, 368, 256, 400, 0, 236, 236, "flat", None),
    ("wall_3",     240, 336, 256, 368, 0, 200, 200, "flat", None),
    ("wall_4",     240, 288, 256, 336, 0, 192, 192, "flat", None),   # the drawn wall ends at U 1150 (y 290)
    ("pines",      256, 336, 336, 352, 32, 64, 96, "hip", None),     # pine row on the blocked cells 16..20 of row 21
]

proxy.build("gate_637", PARTS, "Mercator north gate, room 637",
            {"pines": (60, 150, 70)}, target=(260, 520, 100), ground_z=32, px_per_unit=1.2, size=(1000, 900))
