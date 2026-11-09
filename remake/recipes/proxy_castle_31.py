"""LIGHT PROXY: Mercator castle facade, room 31 (MERCATOR_CASTLE_EXTERIOR; landstalker/docs/LIGHT_PROXY_PLAN.md 'Blender shapes', user 2026-11-04: 'weiter mit den naechsten Formen').
An invisible shape for the lighting only (never drawn). Why: the height map holds the castle only as BLOCKED cells of height 0 (rows 14..28), so the automatic
proposal made no facade at all (its wall pixels were read as ground and got dark blotches) and put a hip roof up to 204 onto the entrance stairs instead.
RE-MEASURED 2026-11-09 (HANDOFF 0a354; projection U = x - y + 1184, V = (x + y) / 2 - z; court z 0):
  facade: front y 464 (first free row 29; with it the 16 high plinth line fits), ends x 352 / 992 (picture edges U 1072 / 1711);
          cornice protrudes 4 (left end U 1068), top 180; the green roof is a ROLL, not a hip: front y 466.5 (its left end U 1075 V 232),
          vertical up to 197, rounding 10 back / 3 up to the crest (456.5, 200) = the drawn top silhouette V = U / 2 - 336 in every column;
          nothing is drawn behind the crest (black), so the body behind falls at 45 deg (invisible, depth unknown: 32 kept).
  centre tower: front y 496 (door centre U 1360 = x 672; front corners U 1312 / 1408), x 624..720, back y 444 (its side cornice ends over
          the facade roof at U 1460); cornice 224..236 protruding 4; roll to 249, flat crest x 629..713 y 453..497 z 253 (top silhouette
          corners U 1360 V 288, U 1316 V 311, U 1444 V 329).
  stairs, landing, steps, planters, low walls: the height map (rows 29..34), checked on the overlay; the right low wall is drawn one cell
          left of its collision cells. The pines in the planters are object models of their own (no stand-in).
Run: python3 remake/tools/build_asset.py proxy_castle_31
Output: landstalker/data/proxies/castle_31.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_castle_31/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

# parts in game coordinates: (name, x0, y0, x1, y1, z0, eave, ridge, roof, ridge axis), see remake/lib/proxy.py
RE = 466.5   # front of the green roof roll (the cornice in front of it at y 468)
def roll(t):   # the roll's rounded front edge: vertical front up to 197, a quarter ellipse 10 deep / 3 high to the crest (456.5, 200)
    import math
    return (RE - 10 * (1 - math.cos(math.radians(t))), 197 + 3 * math.sin(math.radians(t)))
PARTS = [
    ("facade",  352, 432, 992, 464, 0, 168, 168, "flat", None),          # wall face y 464 (left edge U 1072, right edge U 1711)
    ("cornice", 352, 464, 992, 468, 168, 180, 180, "flat", None),        # protrudes 4 (left end U 1068), top 180
    proxy.extrude_x("roof", 357.5, 986.5, [(432, 168), (RE, 168), (RE, 197), roll(30), roll(60), roll(90), (432, 175.5)]),   # crest silhouette V = U / 2 - 336
    ("tower",   624, 444, 720, 496, 0, 224, 224, "flat", None),          # front corners U 1312 / 1408 (white pilaster edges), door centre U 1360 = x 672;
                                                                         # back y 444 = where its side cornice ends over the facade roof (U 1460)
    ("tower_cornice", 620, 444, 724, 500, 224, 236, 236, "flat", None),  # top cornice band, protrudes 4 on the front and the +x side like the facade's
    ("tower_roll", 621.5, 449, 722.5, 499.5, 236, 249, 249, "flat", None),   # the roof roll's vertical part (back y 449: nothing may show above the crest)
    {"name": "tower_crest", "poly": [(621.5, 449), (722.5, 449), (722.5, 499.5), (621.5, 499.5)],   # rounding to the flat crest x 629..713 y 453..497 z 253
     "top": [(629, 453), (713, 453), (713, 497), (629, 497)], "z0": 249, "z1": 253},   # (silhouette corners U 1360 V 288 / U 1316 V 311 / U 1444 V 329)
    # from the height map (exact by construction; the op rectangle owns these cells, so they must be in the model):
    ("stairs",  624, 496, 720, 528, 0, 32, 32, "flat", None),     # rows 31..32, cells 39..44, height 2
    ("landing", 656, 496, 688, 512, 0, 48, 48, "flat", None),     # row 31, cells 41..42, height 3 (at the door)
    ("step1",   576, 528, 768, 544, 0, 16, 16, "flat", None),     # row 33, cells 36..47, height 1
    ("step0",   656, 544, 688, 560, 0, 16, 16, "flat", None),     # row 34, cells 41..42, height 1
    ("planter_l", 576, 464, 624, 528, 0, 16, 16, "flat", None),   # rows 29..32, cells 36..38 (collision 32 = a barrier; the pines stand on 16, see PINES)
    ("planter_r", 720, 464, 768, 528, 0, 16, 16, "flat", None),   # cells 45..47
    ("lowwall_l", 352, 512, 496, 528, 0, 32, 32, "flat", None),   # row 32, cells 22..30, blocked height 2 (low stone wall)
    ("lowwall_r", 848, 512, 992, 528, 0, 32, 32, "flat", None),   # DRAWN one cell left of its collision (row 32, cells 54..62 = x 864..1008): overlay
]

# PINES in the two planters: the catalogue pine (data/object_blocks.json 'pine': crown base + 4 .. base + 30, radius 7, 6 drooping tiers like
# patch_lights.py lk_lt_pinr) on base z 16, placed by their drawn TIPS (tip z 46: x - y = U - 1184, x + y = 2 (V + 46)); with tips at 62 (base 32)
# the lattice would stand a cell outside both planters. Tips read on 6x zooms (U, V): left 4 + 3 + ..., right 3 x 4 lattice of 16.
def pine(name, U, V):
    s, d = 2 * (V + 46), U - 1184; cx, cy = (s + d) / 2, (s - d) / 2
    prof = [(16, 1.5), (20, 1.5), (20, 7.0)]
    for k in range(6):
        z0 = 20 + 26 * k / 6; z1 = 20 + 26 * (k + 1) / 6; r0 = 7.0 * (1 - k / 6)
        prof += [(z1, r0 * 0.45)] + ([(z1, 7.0 * (1 - (k + 1) / 6))] if k < 5 else [])
    return proxy.revolve(name, cx, cy, prof[:-1] + [(46, 0.05)], n=12)
TIPS_L = [(1294, 490), (1278, 497.5), (1264, 507), (1248, 514), (1309, 497), (1296, 522), (1279, 530), (1264, 522.5)]
TIPS_R = [(1440, 561), (1456, 568), (1471, 578), (1423, 569), (1407, 576), (1392, 584), (1406, 591), (1423, 601), (1440, 593), (1456, 587)]
for i, (U, V) in enumerate(TIPS_L + TIPS_R): PARTS.append(pine("pine%d" % i, U, V))

proxy.build("castle_31", PARTS, "Mercator castle facade, room 31",
            {"facade": (150, 160, 150), "roof": (60, 120, 90), "tower": (120, 170, 160), "tower_roof": (60, 120, 90)},
            target=(672, 464, 90), ground_z=0, px_per_unit=1.4, size=(1100, 800))
