"""LIGHT PROXY: Mercator north gate, room 637 (MERCATOR_NORTH_GATE; landstalker/docs/LIGHT_PROXY_PLAN.md 'Blender shapes').
An invisible shape for the lighting only (never drawn): gate wall with the gatehouse merlons, two corner towers, the high wall behind.
RE-MEASURED 2026-11-09 (HANDOFF 0a353; the 2026-11-04 version stood up to 42 units in front of the drawing and 16 units too high).
Projection U = x - y + 1184, V = (x + y) / 2 - z (docs/FORMATS.md). Floor z 32 (height map step 2), moat water z 8.
How (all on the composed room picture, ~/lktest/g637 scratch scripts):
  * WALL FEET: the cobble floor in front of every wall is drawn in LAYER A, the walls in layer B, so the upper edge of the layer A floor
    per picture column IS the wall foot (on z 32 every foot pixel fixes x and y):
      gate wall      x 240 (U 768..944 = y 481..655, every column 239..241),
      corner step    y 480 from x 241 to 255 (U 944..960),
      big tower + the wall next to it  x 256 (U 960..1056 = y 479..384, every column 255..256),
    and the left tower over the water (dark sea foot, U 688..730): +y face y 736 from x 240 (U 688) to the front corner (256, 736, z 8)
    at U 704 V 488, then its +x face x 256 rising to the right = exactly the collision block (column 15, rows 42..45).
  * The towers are BOXES, not half cylinders: their brick courses run straight with the faces (slope + 1/2 left of the corner seam,
    - 1/2 right of it) and their feet are straight lines; only the shading is round. Big tower: left silhouette U 928 (= x 224 at
    y 480, constant from V 132 to the gate wall top V 246), +x face flush with the high wall (x 256, the layer A strip U 1008..1024 is
    part of it, drawn over the pines). Footprints = the collision blocks (column 15 rows 26..29 and 42..45), widened to the silhouette.
  * TOPS: gate wall merlon row: back edge (x 224) silhouette V gives z 112 in every column, the top face front edge 16 lower on the
    screen = 16 deep; gatehouse = three merlon blocks: y 576..592 up to 144 (apex U 832 V 256), y 592..608 and y 560..576 up to 128.
    The door (y 560..608, z 32..~80) is drawn flush with the wall face (its foot line gives x 240..242): no recess.
  * Towers and the high wall run out of the picture (their tops are cut by the black picture edge in steps of 8 lines): heights = the
    lowest that still fills every drawn pixel at the cut = front edge z at the cut (left tower 240, big tower 240, wall 240 / 208 / 200).
  * The pines in front of the high wall are object models of their own (catalogue, LK_LTOBJ); no stand-in here.
Run: python3 remake/tools/build_asset.py proxy_gate_637
Output: landstalker/data/proxies/gate_637.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_gate_637/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

PARTS = [
    ("gate_wall_n", 224, 480, 240, 560, 32, 112, 112, "flat", None),   # right of the gatehouse (towards the big tower)
    ("gh_right",    224, 560, 240, 576, 32, 128, 128, "flat", None),   # gatehouse: three merlon blocks over the door
    ("gh_top",      224, 576, 240, 592, 32, 144, 144, "flat", None),
    ("gh_left",     224, 592, 240, 608, 32, 128, 128, "flat", None),
    ("gate_wall_s", 224, 608, 240, 672, 32, 112, 112, "flat", None),   # left of the gatehouse (towards the left tower)
    ("tower_left",  240, 672, 256, 736, 8, 240, 240, "flat", None),   # stands in the moat (front corner foot z 8)
    proxy.cylinder("tower_big", 236, 452, 28.3, 32, 240),            # round as drawn (user 2026-11-09: the box stood too far left): silhouette U 928..1008
                                                                     # -> centre U 968, r 28.3; its lowest drawn bricks (U 968, V 332 = the floor edge) fix the
                                                                     # depth: foot circle touches y 480, stands 8 over the x 256 floor edge (drawn floor in front)
    ("wall_0",      240, 384, 256, 432, 32, 240, 240, "flat", None),   # next to the tower (small bricks like the tower): its +x face = the layer A strip
                                                                     # U 1008..1024 + U 1024..1056, floor edge x 256 measured up to U 1056 (y 384); cut V 96 / 88
    ("wall_1",      224, 352, 240, 384, 32, 216, 216, "flat", None),   # the big-block wall behind the pines: ONE TILE BACK, face x 240 (user 2026-11-09:
                                                                     # 'dort eine Tile nach hinten'; at x 256 the back pine crowns of row 21 stood in it);
                                                                     # its foot is hidden by the pines; tops = front edge z at the picture cut: U 1056..1071 V 88
    ("wall_2",      224, 320, 240, 352, 32, 192, 192, "flat", None),   # cut V 104 (U 1072..1104)
    ("wall_3",      224, 272, 240, 320, 32, 184, 184, "flat", None),   # cut V 96 / 88 (U 1105..1152); the drawn wall ends at U 1152 (= y 272 on x 240)
]

proxy.build("gate_637", PARTS, "Mercator north gate, room 637",
            {"tower_left": (190, 190, 170), "tower_big": (190, 190, 170)}, target=(260, 520, 100), ground_z=32, px_per_unit=1.2, size=(1000, 900))
