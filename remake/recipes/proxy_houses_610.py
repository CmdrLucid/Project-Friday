"""LIGHT SHAPES (= near-final remake geometry): the TOWN HOUSES of RYUMA, rooms 610 / 611 (one map, $0A6F20; HANDOFF -238 / -239, user 2026-11-20:
the Mercator town house type is also Ryuma's). Same type and wall tiles as remake/recipes/proxy_houses_632.py (builder remake/lib/town_house.py).
MEASURED 2026-11-20: remake/tools/fit_house.py scene fit on layer A (houses 'right', 'hill', 'fr'; walls on the cell lines, walls 48 high, flat top
24 above the eave, 24.5 in = 44 deg, i.e. the Ryuma roofs sit 1.5 higher than Mercator's 22.5); 'left', 'pb', 'pf' are drawn mostly in layer B
(fit_house cannot see them): walls on their cell lines, heights = the Ryuma values (pb / pf: the small grey top diamond read on the composed
picture: inset + top = 114 above the floor plane -> top 88, inset 24.5, eave 64-65). Ryuma lies on terraces: every house has its own ground z0.
Openings: remake/tools/find_openings.py on the composed picture, all standard tiles (windows / doors relative to the storey floor).
The church, the lighthouse and the stone stairs are one-offs (later).
Run: python3 remake/tools/build_asset.py proxy_houses_610  ->  landstalker/data/proxies/house_610_<name>.obj (committed, our own geometry)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import town_house as th
WIN, DOOR = th.WIN, th.DOOR
# name -> (wings, (eave, top, inset) absolute, openings (wing, wall, slot, storey, kind), ground z0); comments: map cells
HOUSES = {
    "right": ([(640, 384, 752, 464)], (96, 120, 24.5), [(0, "y", 656, 0, WIN), (0, "y", 704, 0, DOOR), (0, "x", 416, 0, WIN)], 48),      # 40..46 x 24..28
    "hill":  ([(288, 336, 384, 464)], (160, 184, 24.5), [(0, "y", 320, 0, WIN), (0, "y", 352, 0, WIN), (0, "x", 352, 0, WIN),
                                                         (0, "x", 384, 0, WIN), (0, "x", 432, 0, DOOR)], 112),                         # 18..23 x 21..28 (on the hill)
    "left":  ([(320, 784, 400, 864)], (80, 104, 24.5), [(0, "y", 320, 0, WIN), (0, "y", 368, 0, WIN), (0, "x", 800, 0, WIN),
                                                        (0, "x", 832, 0, DOOR), (0, "x", 848, 0, WIN)], 32),                           # 20..24 x 49..53 (by the lighthouse)
    "fr":    ([(688, 624, 768, 720)], (64, 88, 24.5), [(0, "y", 736, 0, DOOR), (0, "x", 640, 0, WIN), (0, "x", 688, 0, WIN)], 16),        # 43..47 x 39..44
    "pb":    ([(544, 608, 608, 672)], (64, 88, 24.5), [(0, "y", 560, 0, WIN), (0, "x", 624, 0, DOOR)], 16),                              # 34..37 x 38..41
    "pf":    ([(544, 704, 608, 768)], (64, 88, 24.5), [(0, "y", 560, 0, WIN), (0, "x", 720, 0, DOOR)], 16),                              # 34..37 x 44..47
}
# the SMALL window tile (as house 8 of room 632) near the front corner of the +y wall of pb / pf: frame x 591..596 z 40..53 (black frame mask on the
# wall plane; it straddles the slots 576 / 592, so find_openings saw no window)
SMALL = {"pb": [(0, "y", 591, 596, 40, 53)], "pf": [(0, "y", 591, 596, 40, 53)]}
for n, (wings, heights, openings, z0) in HOUSES.items():
    th.house("house_610_" + n, "Ryuma town house '%s', rooms 610 / 611" % n, "proxy_houses_610", wings, heights, openings, z0, SMALL.get(n, ()))
