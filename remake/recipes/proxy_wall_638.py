"""LIGHT PROXY: Mercator fountain court, room 638 (MERCATOR_FOUNTAIN; landstalker/docs/LIGHT_PROXY_PLAN.md 'Blender shapes', user 2026-11-04: 'weiter damit').
An invisible shape for the lighting only (never drawn). Why: the height map holds the city wall only as BLOCKED height 0 cells (column 17) and the round towers as
single blocked cells of height 9 (column 18, rows 26..29 / 38..41 / 50..53), so the automatic proposal made a 32 unit strip with a hip up to 247 IN FRONT of the wall
(cells 18..19 = the walkable bank) and no towers; the pines at the north wall (cells 25..27 x 19..20) got a hip up to 222 (the wall behind them counted as their height).
Measured on the original picture (remake/tools/rom_picture.py ROM 638 480 0 900 760 + remake/tools/proxy_overlay.py, top silhouette scanned per picture column):
  west wall: face x 288, one cell thick (= height map column 17, x 272..288; the art draws no top face, so the top silhouette is read at the face) (its base meets the bank at ground 48 along the whole length), y 288..912; the drawn top FALLS towards the back (forced perspective of the
             art): ~245 at the front, 236, 234, 221, 212, 204 at the back (segments below);
  towers: half cylinders radius 32 standing out of the wall (U width 77 ~ the drawn 80), centres y 832 / 640 / 448, tops 257 / 241 / 220 (back edge of the top);
  north wall: face y 288, x 288..496, top ~196; pines in front of it: tops ~96 on ground 48.
Run: python3 remake/tools/build_asset.py proxy_wall_638
Output: landstalker/data/proxies/wall_638.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_wall_638/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

# parts in game coordinates: (name, x0, y0, x1, y1, z0, eave, ridge, roof, ridge axis) or proxy.cylinder(...), see remake/lib/proxy.py
PARTS = [
    ("wall_a",  272, 840, 288, 912, 48, 245, 245, "flat", None),   # west wall, front segment
    ("wall_b",  272, 680, 288, 840, 48, 236, 236, "flat", None),
    ("wall_c",  272, 600, 288, 680, 48, 234, 234, "flat", None),
    ("wall_d",  272, 480, 288, 600, 48, 221, 221, "flat", None),
    ("wall_e",  272, 400, 288, 480, 48, 212, 212, "flat", None),
    ("wall_f",  272, 272, 288, 400, 48, 204, 204, "flat", None),   # back segment, runs into the north wall
    proxy.cylinder("tower_1", 288, 832, 32, 48, 257, -90, 90),     # half towers on the wall face (height map column 18 = their blocked cells)
    proxy.cylinder("tower_2", 288, 640, 32, 48, 241, -90, 90),
    proxy.cylinder("tower_3", 288, 448, 32, 48, 220, -90, 90),
    ("north",   272, 272, 496, 288, 48, 196, 196, "flat", None),  # north wall (row 17 of the blocked rows 12..17), one cell thick like the west wall
    ("pines",   400, 304, 448, 336, 48, 64, 96, "hip", None),     # pine group at the north wall (cells 25..27 x 19..20)
]

proxy.build("wall_638", PARTS, "Mercator fountain court city wall, room 638",
            {"north": (200, 195, 170), "pines": (60, 150, 70)}, target=(330, 600, 120), ground_z=48, px_per_unit=0.9, size=(1000, 900))
