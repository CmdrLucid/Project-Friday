"""LIGHT SHAPE (= near-final remake geometry): the TOWN HOUSE of room 442 (2026-11-21). Same type and wall tiles as the Ryuma houses
(remake/recipes/proxy_houses_610.py, builder remake/lib/town_house.py): a pixel search found the Ryuma house 'fr' 90 % equal on the front walls,
but 442's house is SQUARE (80 x 80: flat square roof top, not fr's ridge) and its door sits in the second slot. Collision: blocked 96 at cells
x 17..21 y 17..21 on the ground 48 (row 16 is the void at the map edge), door = the walkable cell (18,21). Heights = the Ryuma values moved to
this ground: eave 96, flat top 120, inset 24.5. Openings read on the composed picture: door +y wall slot x 288, windows +x wall slots y 288 / 320.
Run: python3 remake/tools/build_asset.py proxy_houses_442  ->  landstalker/data/proxies/house_442.obj (our own geometry)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import town_house as th
WIN, DOOR = th.WIN, th.DOOR
th.house("house_442", "town house of room 442 (Ryuma type)", "proxy_houses_442", [(272, 272, 352, 352)], (96, 120, 24.5),
         [(0, "y", 288, 0, DOOR), (0, "x", 288, 0, WIN), (0, "x", 320, 0, WIN)], 48, ())
