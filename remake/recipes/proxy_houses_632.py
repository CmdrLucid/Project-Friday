"""LIGHT SHAPES (= near-final remake geometry): the TOWN HOUSES of Mercator room 632 (landstalker/docs/LIGHT_PROXY_PLAN.md 'WHOLE ROOMS AS 3D MODELS',
HANDOFF NEXT -238, user 2026-11-20: 'ja go' for the town house as the first recurring object type; details OK with: stone plinth FLUSH with the wall,
windows / doors recessed as drawn).
House type (remake/MODELS.md 'Town house'): brick walls straight up from the ground, a hip roof flush with the walls (no overhang drawn), 41 deg slopes
up to a flat grey top; an L or long house = the UNION of several wings with the same heights (their roofs meet in valleys, room 632 house 5 / 7).
MEASURED 2026-11-20 with remake/tools/fit_house.py (scene fit of all houses at once on layer A of the drawn picture, walls free):
  one storey: walls 16 -> eave 64, flat top 86.5 starting 25.5 in (41 deg); two storeys (house 4): eave 112, top 134.5, 26 in.
  every wall came out ON the map cell lines; 90.4 % of the model pixels match the picture classes (wall / roof / top), the rest are
  doors / windows drawn in layer B and the pines in front of house 5 (no model error).
OPENINGS (remake/tools/find_openings.py: every 16 unit wall slot per storey of 48 classified on the composed picture, frame = black frame lines):
  the walls are built from 16 unit wall tiles, so windows / doors are the SAME tiles everywhere, at the same place in their slot (both walls):
  window frame slot + 3 .. slot + 16, storey floor + 22 .. + 38 (z 38..54), recess 1.5; sill slot + 0 .. + 16, floor + 16 .. + 21, 1 out of the wall;
  door frame slot + 4 .. slot + 16, z 19..59 (threshold step 16..19 stays), recess 2.5; one SMALL window (house 8 +y wall x 791..796 z 40..53, no sill).
  A framed shop sign low on house 6 (+x wall y 800..816 z 36..48) is drawn flat: no opening. Depths: user OK on the example 2026-11-20.
The big building in the upper left (cells 15..20 x 24..41: two storeys, balcony, lower wing) is a one-off and gets its own recipe.
Run: python3 remake/tools/build_asset.py proxy_houses_632
Output: landstalker/data/proxies/house_632_<n>.obj (GAME coordinates: x east, y south, z up, world units; our own geometry, committed; triangles)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy
import town_house as th

ONE = (64, 86.5, 25.5)     # eave, flat top, inset of the top (one storey)
TWO = (112, 134.5, 26)     # two storeys
WIN, DOOR = th.WIN, th.DOOR
# house -> (wings (x0, y0, x1, y1), heights, openings (wing, wall 'x' = the +x wall x = x1 / 'y' = the +y wall y = y1, slot start along the wall, storey, kind))
HOUSES = {
    1: ([(480, 384, 576, 464)], ONE, [(0, "x", 400, 0, WIN), (0, "x", 432, 0, DOOR)]),                       # cells 30..35 x 24..28, behind house 4
    2: ([(704, 384, 800, 464)], ONE, [(0, "x", 400, 0, DOOR), (0, "x", 432, 0, WIN)]),                       # cells 44..49 x 24..28
    4: ([(480, 464, 560, 544)], TWO, [(0, "y", 496, 1, WIN), (0, "y", 528, 1, WIN), (0, "x", 480, 0, WIN), (0, "x", 480, 1, WIN),
                                      (0, "x", 512, 0, DOOR), (0, "x", 512, 1, WIN)]),                         # cells 30..34 x 29..33, two storeys
    5: ([(704, 480, 848, 560), (704, 480, 784, 608)], ONE,                                                    # L: cells 44..52 x 30..34 + 44..48 x 35..37
        [(0, "y", 800, 0, WIN), (0, "x", 496, 0, WIN), (0, "x", 528, 0, DOOR), (0, "x", 544, 0, WIN),
         (1, "y", 720, 0, WIN), (1, "y", 752, 0, WIN), (1, "x", 576, 0, WIN)]),
    6: ([(720, 736, 864, 816)], ONE, [(0, "y", 800, 0, WIN), (0, "x", 752, 0, WIN), (0, "x", 784, 0, DOOR)]),  # cells 45..53 x 46..50
    7: ([(512, 768, 592, 848), (512, 848, 592, 928)], ONE,                                                    # long house cells 32..36 x 48..57: two flat tops
        [(0, "x", 784, 0, WIN), (0, "x", 816, 0, DOOR), (1, "y", 528, 0, WIN), (1, "y", 560, 0, WIN), (1, "x", 864, 0, DOOR), (1, "x", 896, 0, WIN)]),
    8: ([(720, 832, 816, 928)], ONE, [(0, "y", 736, 0, WIN), (0, "x", 864, 0, WIN), (0, "x", 896, 0, DOOR)]),  # cells 45..50 x 52..57
    9: ([(240, 928, 320, 992)], (64, 79.5, 17), [(0, "y", 256, 0, WIN), (0, "y", 288, 0, WIN), (0, "x", 960, 0, DOOR)]),   # cells 15..19 x 58..61
}
# house 9 = the yellow house in front of the church (was a part of church_632 until 2026-11-20, user: 'eigentlich ein eigenes Haus'): drawn in
# layer B, so fit_house (layer A) cannot see it: footprint / eave / top terrace from the 2026-11-09 fit_foot measurement (front y 992, left x 240,
# eave 64, terrace -> top 79.5, 17 in on every side = a steeper roof than the other houses); right wall on the cell line x 320 (the 2026-11-09
# value 319 put the door 1 unit off the door tile; with 320 find_openings gives the standard tiles: windows slots 256 / 288, door slot 960).
SMALL = {8: [(0, "y", 791, 796, 40, 53)]}   # (wing, wall, a0, a1, z0, z1): measured frame, recess 1.5, no sill

for n, (wings, heights, openings) in HOUSES.items():
    th.house("house_632_%d" % n, "Mercator town house %d, room 632" % n, "proxy_houses_632", wings, heights, openings, 16, SMALL.get(n, ()))
