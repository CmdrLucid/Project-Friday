"""LIGHT SHAPES (= near-final remake geometry): the TOWN HOUSES of VERLA, rooms 711 / 712 (one map, $0A669E, tileset 0; user 2026-11-20: 'Verla
haben wir vergessen, die benutzen die gleichen Haeuser wie Mercator und Ryuma'). Builder remake/lib/town_house.py (as 632 / 610).
MEASURED 2026-11-20 (~/Project-Friday-Test/lktest/verla): the collision height of a town house cell = its EAVE (Ryuma checked: right 96 / hill 160 /
fr 64 / left 80), the ground 48 below. remake/tools/fit_house.py scene fit on layer A: B and D (drawn in layer A) land on their cell lines with the
Ryuma heights (eave + 24 top, inset 24.5); C and E are drawn mostly in layer B (invisible to fit_house): walls on their cell lines, the same type
heights. Openings: remake/tools/find_openings.py (standard tiles); E's +y 'door' at 378 is a small flat plaque (ignored), the shop sign on E's +x wall
is flat. The church (cells 22..31 x 22..29) is a one-off (later).
Run: python3 remake/tools/build_asset.py proxy_houses_711  ->  landstalker/data/proxies/house_711_<name>.obj"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import town_house as th
WIN, DOOR = th.WIN, th.DOOR
HOUSES = {
    "b": ([(672, 416, 768, 528)], (128, 152, 24.5), [(0, "y", 704, 0, DOOR), (0, "x", 432, 0, WIN), (0, "x", 464, 0, WIN)], 80),                       # 42..47 x 26..32
    "c": ([(352, 528, 464, 608)], (128, 152, 24.5), [(0, "y", 368, 0, WIN), (0, "y", 400, 0, WIN), (0, "y", 432, 0, WIN),
                                                     (0, "x", 544, 0, WIN), (0, "x", 576, 0, DOOR)], 80),                                              # 22..28 x 33..37
    "d": ([(688, 656, 768, 736)], (128, 152, 24.5), [(0, "y", 720, 0, DOOR), (0, "x", 672, 0, WIN), (0, "x", 704, 0, WIN)], 80),                       # 43..47 x 41..45
    "e": ([(352, 656, 464, 736)], (96, 120, 24.5), [(0, "y", 400, 0, WIN), (0, "x", 672, 0, WIN), (0, "x", 704, 0, DOOR)], 48),                        # 22..28 x 41..45
}
for n, (wings, heights, openings, z0) in HOUSES.items():
    th.house("house_711_" + n, "Verla town house '%s', rooms 711 / 712" % n, "proxy_houses_711", wings, heights, openings, z0)
