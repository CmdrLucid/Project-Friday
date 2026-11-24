#!/usr/bin/env python3
"""case.py OUT.obj NAME - CASE FURNITURE (wardrobes, racks, shelves) built from remake/lib/cabinet.py by the measured specs below (rooms where the piece
stands, its world box, front face, rows from the bottom up, extras). Each spec was checked by overlay on rom_picture (remake/tools/proxy_overlay.py) and
in the clay preview (remake/tools/clay_preview.py). GAME coordinates x east, y south, z up, units.  `case.py --list` prints the specs; `case.py --write [NAME..]` writes the OBJs + light ops (default: every merc_ spec)."""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, os.path.join(HERE, "..", "castle_bench"))
import cabinet
from furniture import rbox, lathe
from castle_bench import write_obj

SPEAR = [(0.0, 0.7), (0.84, 0.6), (0.86, 1.0), (0.9, 1.3), (0.97, 0.8), (1.0, 0.15)]   # shaft, socket, leaf blade, tip
WARDROBE = [("plinth", 2), ("drawers", 5, 1), ("doors", 40, 2)]
# small things on the Mercator furniture (measured on 616: vase body 11 high + a bouquet to 22, flask 7, standing picture frame 10 x 9)
VASE = lambda x, y, z: [("lathe", (x, y, z, 11.0, [(0.0, 1.5), (0.35, 2.3), (0.75, 1.2), (1.0, 1.6)], 12)),
                        ("lathe", (x, y, z + 11.0, 10.0, [(0.0, 0.6), (0.35, 2.6), (0.75, 2.9), (1.0, 0.6)], 12))]
FLASK = lambda x, y, z: [("lathe", (x, y, z, 7.0, [(0.0, 2.3), (0.45, 2.7), (0.7, 1.0), (1.0, 0.9)], 12))]
BOTTLE = lambda x, y, z: [("lathe", (x, y, z, 10.0, [(0.0, 1.6), (0.55, 1.7), (0.7, 0.8), (1.0, 0.7)], 12))]   # tall blue bottle
# the CLAY JAR of the Mercator houses = ONE tile drawing in every room: profile fitted on the fully visible jar of 683 (plane A outline, fitlathe.py), the
# other jars placed by the picture shift of that drawing (template match, shifts are whole tiles; on the floor: dx = dV + dU / 2, dy = dV - dU / 2)
JAR_T = [(0.0, 5.43), (0.15, 8.10), (0.45, 8.79), (0.75, 5.36), (0.88, 5.74), (1.0, 5.15)]
JARFIT = lambda x, y, z=0.0: [("lathe", (x, y, z, 24.12, JAR_T, 16))]
JAR = lambda x, y, z, h=22.0, k=1.0: [("lathe", (x, y, z, h, [(t, r * k) for t, r in ((0.0, 3.8), (0.15, 6.0), (0.45, 6.4), (0.75, 5.1), (0.88, 3.4), (1.0, 4.0))], 16))]   # k = radius scale (silhouette fit)   # clay jar (house_shelf.py)
PLATES = lambda x, y, z, h=6.0: [("lathe", (x, y, z, h, [(0.0, 4.5), (0.2, 5.6), (1.0, 5.6)], 16))]   # stack of plates
def SHELF_X(xw, d, y0, y1, z):   # wall shelf on the WEST wall (board xw .. xw + d, top z) on two thin brackets near its ends
    return [("rbox", (xw, xw + d, y0, y1, z - 3.0, z, 0.6))] + [("rbox", (xw, xw + d * 0.6, yb - 0.75, yb + 0.75, z - 10.0, z - 2.8, 0.3)) for yb in (y0 + 5.0, y1 - 5.0)]
def SHELF_Y(yw, d, x0, x1, z):   # on the NORTH wall
    return [("rbox", (x0, x1, yw, yw + d, z - 3.0, z, 0.6))] + [("rbox", (xb - 0.75, xb + 0.75, yw, yw + d * 0.6, z - 10.0, z - 2.8, 0.3)) for xb in (x0 + 5.0, x1 - 5.0)]
FRAME_X = lambda x, y0, y1, z, h=9.0: [("box", (x - 0.75, x + 0.75, y0, y1, z, z + h))]   # frame standing upright, facing east
FRAME_Y = lambda x0, x1, y, z, h=9.0: [("box", (x0, x1, y - 0.75, y + 0.75, z, z + h))]   # facing south
SPECS = {
    # the two wardrobes on the west wall of the castle rooms 65 / 66 (tileset 15, cells x 14, y 31..34, 48 high): double doors over a drawer rail
    "castle_wardrobes_65": dict(rooms=[65, 66], cells=[14, 31, 14, 34], floor=0,
                                parts=[("cab", (224, 240, 496, 528, 0, 48), "+x", WARDROBE), ("cab", (224, 240, 528, 560, 0, 48), "+x", WARDROBE)]),
    # the plate rack on the west wall of the castle kitchen 68 / 69 (tileset 15, cells x 13, y 17..21, 48 high): five compartments, drawers at the
    # bottom, bottles in the middle row, upright plates on top
    "castle_plate_rack_68": dict(rooms=[68, 69], cells=[13, 17, 13, 21], floor=0,
                                 parts=[("cab", (208, 224, 272, 352, 0, 48), "+x", [("plinth", 2), ("drawers", 9, 5), ("shelf", 14, 5, "bottles"), ("shelf", 14, 5, "plates")])]),
    # the spear rack of the castle armoury 78 / 79 (tileset 15, cells x 17, y 28..29, 48 high): a plank case open to the east with four spears standing
    # in it (blade tops at z ~39, read from the drawn blades)
    "castle_spear_rack_78": dict(rooms=[78, 79], cells=[17, 28, 17, 29], floor=0,
                                 parts=[("cab", (272, 288, 448, 480, 0, 48), "+x", [("open", 48)])]
                                       + [("lathe", (285.0, y, 0.0, 40.0, SPEAR, 10)) for y in (474.0, 466.7, 458.3, 450.3)]),
    # Mercator inn 623 / 624 / 701 / 702 (tileset 2, cells x 23, y 34..37, floor 0): a GLASS CABINET (y 36..37, 48 high, two glass doors over two)
    # and a low DRESSER (y 34..35, top drawn at 22, collision 16) with a vase, both open to the east
    "inn_cabinet_623": dict(rooms=[623, 624, 701, 702], cells=[23, 34, 23, 37], floor=0,
                            parts=[("cab", (368, 384, 576, 608, 0, 48), "+x", [("plinth", 2), ("glass", 22, 2), ("glass", 22, 2)]),
                                   ("cab", (370, 384, 544, 576, 0, 22), "+x", [("plinth", 2), ("drawers", 9, 2), ("drawers", 9, 2)]),
                                   ("lathe", (382.5, 563.5, 22.0, 10.0, [(0.0, 1.6), (0.3, 2.5), (0.6, 2.2), (0.8, 0.9), (1.0, 1.2)], 12))]),
    # the wardrobe of the castle storeroom 72 (tileset 15, cells x 24..25, y 18, floor 16, 48 high): double doors to the south over a drawer rail
    "castle_wardrobe_72": dict(rooms=[72], cells=[24, 18, 25, 18], floor=16,
                               parts=[("cab", (384, 416, 288, 304, 16, 64), "+y", WARDROBE)]),
    # (merc_ specs: glass rows as 'glassflat' = the light variant; hearth openings as HIGH as the drawn fire (the flame light sits on the fire's view ray:
    # a fire drawn over a lower lintel lay in the lintel's shadow = dark fire, user 2026-11-24) and only 1 deep: the game puts the flame in
    # front of the hearth face, drawn fire pixels 8 deep in an opening stayed dark (LANDSTALKER_LT_MODEL=0 = bright again))
    # MERCATOR HOUSES (tileset 2, indoor furniture survey 2026-11-24, remake/tools/deco_survey.py --todo): measured by wire boxes on rom_picture
    # 616 / 617 (cells x 16, y 20..22, 48 high, west wall): a BOOKCASE (y 22: drawer + two book shelves) with a vase of flowers and a GLASS CABINET
    # (y 20..21: two rows of two glass doors) with a flask + a picture frame on top, both open to the east
    "merc_case_616": dict(rooms=[616, 617], cells=[16, 20, 16, 22], floor=0,
                          parts=[("cab", (256, 272, 352, 368, 0, 48), "+x", [("plinth", 2), ("drawers", 12, 1), ("shelf", 17), ("shelf", 15)]),
                                 ("cab", (256, 272, 320, 352, 0, 48), "+x", [("plinth", 2), ("glassflat", 21, 2), ("glassflat", 23, 2)])] + VASE(260.0, 360.0, 48.0)
                                + FLASK(260.4, 344.4, 48.0) + FRAME_X(263.0, 331.0, 342.0, 48.0, 7.0)),
    # 618 / 619 (cells x 16, y 18..19, collision 48 = with the things on top): a CHEST OF DRAWERS (top 32, two columns of three drawers) open to the east,
    # flask + vase of flowers on its cloth (corner points of the drawn top: x 258.25 .. 271.25, z 32)
    "merc_chest_618": dict(rooms=[618, 619], cells=[16, 18, 16, 19], floor=0,
                           parts=[("cab", (258, 271.5, 288, 320, 0, 32), "+x", [("plinth", 3), ("drawers", 9, 2), ("drawers", 9, 2), ("drawers", 9, 2)])]
                                 + FLASK(260.75, 313.75, 32.0) + VASE(267.6, 304.4, 32.0)),
    # 618 / 619 (cells 20..21 x 18..19, 16 high): a low open WOODEN BOX (plank walls, rim, dark inside)
    "merc_box_618": dict(rooms=[618, 619], cells=[20, 18, 21, 19], floor=0, parts=[("tray", (321, 351, 289, 319, 0, 16), 2.5, 6.0)]),
    # 622 (cells 26..27 x 19, 48 high): a GLASS CABINET open to the south (two rows of two glass doors), a blue bottle on top
    "merc_glass_622": dict(rooms=[622], cells=[26, 19, 27, 19], floor=0,
                           parts=[("cab", (416, 448, 304, 320, 0, 48), "+y", [("plinth", 2), ("glassflat", 22, 2), ("glassflat", 22, 2)])] + BOTTLE(436.0, 312.0, 48.0)),
    # 673 / 674 (cells 15..16 x 17, between the beds): a NIGHTSTAND (top 16.5 with a cloth, two rows of two drawers) open to the south (drawn x 241.75 .. 270.5)
    "merc_night_673": dict(rooms=[673, 674], cells=[15, 17, 16, 17], floor=0,
                           parts=[("cab", (241.75, 270.5, 272, 288, 0, 16.5), "+y", [("plinth", 2), ("drawers", 7, 2), ("drawers", 6, 2)])]),
    # 673 / 674 (cells 20..23 x 17, 48 high): a GLASS CABINET (x 320..352, top 36 as drawn: collision 48 = with the vase) with a vase and a BOOKCASE (x 352..384: drawers + two book shelves) with a
    # picture frame and a small box, both open to the south
    "merc_case_673": dict(rooms=[673, 674], cells=[20, 17, 23, 17], floor=0,
                          parts=[("cab", (320, 352, 272, 288, 0, 36), "+y", [("plinth", 2), ("glassflat", 16, 2), ("glassflat", 16, 2)]),
                                 ("cab", (352, 384, 274, 288, 0, 36), "+y", [("plinth", 2), ("drawers", 7, 2), ("shelf", 13), ("shelf", 12)])]
                                + VASE(338.5, 286.5, 36.0) + FRAME_Y(365.0, 375.0, 280.0, 36.0, 8.0) + [("box", (376.0, 381.0, 279.0, 284.0, 36.0, 39.0))]),
    # 675 (cells 22..23 x 13..15, 48 high): a GLASS CABINET against the north wall (x 352..384, 12 deep: drawn top corners) with a box on top, and in front of it a low open WOODEN BOX (2 x 2)
    "merc_glass_675": dict(rooms=[675], cells=[22, 13, 23, 15], floor=0,
                           parts=[("cab", (352, 384, 208, 220, 0, 48), "+y", [("plinth", 2), ("glassflat", 22, 2), ("glassflat", 22, 2)]), ("box", (359.0, 368.0, 209.0, 217.0, 48.0, 54.0)),
                                  ("tray", (353, 383, 225, 255, 0, 16), 2.5, 6.0)]),
    # 675 (cells 17 x 15..16, between the beds): a low open WOODEN BOX 1 x 2
    "merc_box_675": dict(rooms=[675], cells=[17, 15, 17, 16], floor=0, parts=[("tray", (273, 287, 241, 271, 0, 16), 2.5, 6.0)]),
    # 675 (cells 17 x 21..23, collision 64 = up to the wall shelf): a CHEST OF DRAWERS (y 368..384, top 36) with a flask, a low BOOKCASE (y 336..368, top 33) with a frame and
    # a vase, and the WALL SHELF over both (top 61) with two plate stacks and a blue bottle; AIR between the furniture and the shelf
    "merc_chest_675": dict(rooms=[675], cells=[17, 21, 17, 23], floor=0,
                           parts=[("cab", (272, 288, 368, 384, 0, 36), "+x", [("plinth", 2), ("drawers", 8, 1), ("drawers", 8, 1), ("drawers", 8, 1), ("drawers", 8, 1)]),
                                  ("cab", (272, 286, 336, 368, 0, 33), "+x", [("plinth", 2), ("drawers", 8, 2), ("shelf", 21)])]
                                 + FLASK(278.0, 376.0, 36.0) + FRAME_X(276.0, 340.0, 350.0, 33.0, 8.0) + VASE(278.0, 358.0, 33.0)
                                 + SHELF_X(272.0, 13.0, 336.0, 384.0, 61.0) + PLATES(278.5, 350.0, 61.0) + PLATES(278.5, 364.0, 61.0, 8.0) + BOTTLE(278.0, 378.0, 61.0)),
    # 677 (cells 17 x 17..20, 64): the same corner on four cells: CHEST OF DRAWERS (y 320..336), BOOKCASE (y 290..320), a clay jar (y ~280), WALL SHELF (top 61) with plates, a box and two bottles
    "merc_chest_677": dict(rooms=[677], cells=[17, 17, 17, 20], floor=0,
                           parts=[("cab", (272, 288, 320, 336, 0, 36), "+x", [("plinth", 2), ("drawers", 8, 1), ("drawers", 8, 1), ("drawers", 8, 1), ("drawers", 8, 1)]),
                                  ("cab", (272, 286, 290, 320, 0, 33), "+x", [("plinth", 2), ("drawers", 8, 2), ("shelf", 21)])]
                                 + FLASK(278.0, 328.0, 36.0) + FRAME_X(276.0, 296.0, 306.0, 33.0, 8.0) + VASE(278.0, 313.0, 33.0) + JARFIT(285.0, 285.0)
                                 + SHELF_X(272.0, 13.0, 272.0, 336.0, 61.0) + PLATES(278.5, 300.0, 61.0) + PLATES(278.5, 286.0, 61.0, 8.0) + BOTTLE(278.0, 332.0, 61.0)
                                 + BOTTLE(278.0, 275.0, 61.0) + [("box", (274.0, 282.0, 315.0, 323.0, 61.0, 67.0))]),
    # 677 (cell 23 x 17, 48): a narrow tall BOOKCASE open to the south (drawer + three book shelves)
    "merc_books_677": dict(rooms=[677], cells=[23, 17, 23, 17], floor=0,
                           parts=[("cab", (368, 384, 272, 288, 0, 48), "+y", [("plinth", 2), ("drawers", 8, 1), ("shelf", 13), ("shelf", 13), ("shelf", 12)])]),
    # 683 / 684 (cells 21..25 x 20, collision 64): a GLASS CABINET (x 336..368, 48) with a box and a bottle, a BOOKCASE (x 368..400, top 45: drawn right top corner) with plates and a small box,
    # a clay jar at the east end; open to the south
    "merc_case_683": dict(rooms=[683, 684], cells=[21, 20, 25, 20], floor=0,
                          parts=[("cab", (336, 368, 320, 334, 0, 48), "+y", [("plinth", 2), ("glassflat", 22, 2), ("glassflat", 22, 2)]),
                                 ("cab", (368, 400, 322, 336, 0, 45), "+y", [("plinth", 2), ("drawers", 8, 2), ("shelf", 17), ("shelf", 16)]),
                                 ("box", (346.0, 354.0, 323.0, 331.0, 48.0, 54.0)), ("box", (386.5, 391.0, 322.5, 327.0, 45.0, 47.5))]
                                + [("lathe", (360.0, 324.3, 48.0, 13.0, [(0.0, 1.6), (0.55, 1.7), (0.7, 0.8), (1.0, 0.7)], 12))] + PLATES(383.8, 327.8, 45.0, 10.0) + JARFIT(413.0, 333.0)),
    # 683 / 684 (cells 18 x 22..26, 32): a NIGHTSTAND (y 352..368, 29) and a long low BOOKCASE (y 368..410; the cello leaning in y 410..432 is not modelled yet) with a box, a vase and a frame, open to the east
    "merc_books_683": dict(rooms=[683, 684], cells=[18, 22, 18, 26], floor=0,
                           parts=[("cab", (290, 304, 352, 368, 0, 29), "+x", [("plinth", 2), ("drawers", 13, 1), ("drawers", 13, 1)]),
                                  ("cab", (290, 304, 368, 410, 0, 30), "+x", [("plinth", 2), ("drawers", 8, 3), ("shelf", 18, 2)]),
                                  ("box", (294.0, 302.0, 400.0, 407.0, 30.0, 36.0))] + VASE(297.0, 396.0, 30.0) + FRAME_X(296.0, 378.0, 388.0, 30.0, 8.0)),
    # 687 / 688 (cells 13 x 13..17, 48): a brick HEARTH (y 240..288, top 32 with a cloth, a box and a frame; fire opening to the east) and a GLASS CABINET
    # (y 208..240, front x 223: its front corner on the drawn outline column, lightedges 2026-11-24; 48) open to the east
    "merc_hearth_687": dict(rooms=[687, 688], cells=[13, 13, 13, 17], floor=0,
                            parts=[("hearth", (208, 224, 240, 288, 0, 30), "+x", dict(open_u=(0.34, 0.86), open_h=0.85, depth=1.0)),
                                   ("rbox", (208.0, 225.0, 240.0, 288.0, 30.0, 32.0, 0.5)),
                                   ("cab", (208, 223, 208, 240, 0, 48), "+x", [("plinth", 2), ("glassflat", 22, 2), ("glassflat", 22, 2)]),
                                   ("box", (212.0, 220.0, 274.0, 281.0, 32.0, 38.0))] + FRAME_X(214.0, 254.0, 264.0, 32.0, 8.0)),
    # 687 / 688 (cells 13 x 19..20, 32): a low BOOKCASE open to the east with a vase and a small box
    "merc_books_687": dict(rooms=[687, 688], cells=[13, 19, 13, 20], floor=0,
                           parts=[("cab", (208, 222, 304, 336, 0, 28), "+x", [("plinth", 2), ("drawers", 7, 2), ("shelf", 19)]),
                                  ("box", (212.0, 218.0, 308.0, 314.0, 28.0, 32.0))] + VASE(214.0, 326.0, 28.0)),
    # 689 / 690 (cells 17..19 x 13, 64): the house corner of house_shelf.py on the north wall: a clay jar (x ~280), a low GLASS CABINET (x 291.5..318.5, 17 deep, top 33.5) with a
    # box, AIR, and the WALL SHELF (top 47, 14.5 deep: re-read pixel by pixel on the drawn corner points; lower than in 691) with plates, a bottle and a flask
    "merc_shelf_689": dict(rooms=[689, 690], cells=[17, 13, 19, 13], floor=0,
                           parts=[("cab", (291.5, 318.5, 208, 225, 0, 33.5), "+y", [("plinth", 2), ("glassflat", 29.5, 2)]), ("box", (299.0, 304.0, 217.0, 222.0, 33.5, 36.5))]
                                 + JARFIT(285.0, 221.0) + SHELF_Y(208.0, 14.5, 272.0, 320.0, 47.0) + PLATES(288.0, 215.0, 47.0, 8.0) + BOTTLE(300.0, 215.0, 47.0) + FLASK(312.0, 216.0, 47.0)),
    # 689 / 690 (cells 13 x 17..19, 48): a BOOKCASE (y 304..320, 36) with a vase and a CHEST OF DRAWERS (y 272..304, 32, two columns) with a frame, open to the east
    "merc_chest_689": dict(rooms=[689, 690], cells=[13, 17, 13, 19], floor=0,
                           parts=[("cab", (208, 222, 304, 320, 0, 36), "+x", [("plinth", 2), ("drawers", 8, 1), ("shelf", 13), ("shelf", 13)]),
                                  ("cab", (208, 223, 272, 304, 0, 32), "+x", [("plinth", 3), ("drawers", 9, 2), ("drawers", 9, 2), ("drawers", 9, 2)])]
                                 + VASE(213.0, 312.0, 36.0) + FRAME_X(214.0, 284.0, 294.0, 32.0, 8.0)),
    # 717 / 718 (cells 13 x 12..18, 48): a CHEST OF DRAWERS (y 192..240, top 36, three columns) with a frame and a flask, a tall BOOKCASE (y 240..272, 48)
    # with a flask and a vase, and two clay jars at the south end; open to the east (corners read on the drawing)
    "merc_chest_717": dict(rooms=[717, 718], cells=[13, 12, 13, 18], floor=0,
                           parts=[("cab", (208, 224, 192, 240, 0, 36), "+x", [("plinth", 3), ("drawers", 8, 3), ("drawers", 8, 3), ("drawers", 8, 3), ("drawers", 8, 3)]),
                                  ("cab", (208, 223, 240, 272, 0, 48), "+x", [("plinth", 2), ("drawers", 9, 2), ("shelf", 18), ("shelf", 17)])]
                                 + FRAME_X(216.0, 220.0, 230.0, 36.0, 8.0) + FLASK(218.0, 207.0, 36.0) + FLASK(212.5, 262.0, 48.0) + VASE(218.0, 255.0, 48.0)
                                 + JARFIT(221.0, 285.0) + JARFIT(221.0, 301.0)),
    # 722 / 723 (cells 18..20 x 16..21, 48): a GLASS CABINET (x 288..304, y 320..352, 48, open to the east), a CHEST OF DRAWERS (y 290..320, top 33: re-read on its drawn right top corner) with a vase and
    # a box, a clay jar, a brick HEARTH along the north wall (x 288..336, 12 deep, top 30 with a cloth, two flasks + a box; fire opening to the south at x 300..316 = where the fire is DRAWN: the game puts the flame light on the drawn fire's view ray, a solid jamb there threw the light out in front = a hard shadow edge on the cloth, user 2026-11-24) and the
    # WALL SHELF over it (x 288..336, top 61 read on its drawn left top corner, above the collision) with two plate stacks and a bottle
    "merc_corner_722": dict(rooms=[722, 723], cells=[18, 16, 20, 21], floor=0,
                            parts=[("cab", (288, 304, 320, 352, 0, 48), "+x", [("plinth", 2), ("glassflat", 22, 2), ("glassflat", 22, 2)]),
                                   ("cab", (288, 303, 290, 320, 0, 33), "+x", [("plinth", 3), ("drawers", 7.5, 2), ("drawers", 7.5, 2), ("drawers", 7.5, 2), ("drawers", 7.5, 2)]),
                                   ("hearth", (288, 336, 256, 268, 0, 28), "+y", dict(open_u=(0.25, 0.58), open_h=0.88, depth=1.0)),
                                   ("rbox", (288.0, 336.0, 256.0, 269.0, 28.0, 30.0, 0.5)),
                                   ("box", (304.0, 312.0, 256.5, 263.0, 30.0, 36.0))]
                                  + VASE(300.5, 305.5, 33.0) + [("box", (290.5, 296.5, 304.5, 310.5, 33.0, 37.0))] + JARFIT(301.0, 285.0)
                                  + FLASK(300.0, 263.0, 30.0) + FLASK(322.0, 262.0, 30.0)
                                  + SHELF_Y(256.0, 13.0, 288.0, 336.0, 61.0) + PLATES(305.4, 262.0, 61.0) + PLATES(316.3, 261.0, 61.0, 8.0) + BOTTLE(326.0, 260.0, 61.0)),
    # 722 / 723 (cells 22 x 16..18, 48): a free standing BOOKCASE open to the east (drawers + two book shelves)
    "merc_books_722": dict(rooms=[722, 723], cells=[22, 16, 22, 18], floor=0,
                           parts=[("cab", (352, 368, 256, 304, 0, 48), "+x", [("plinth", 2), ("drawers", 9, 3), ("shelf", 18), ("shelf", 17)])]),
    # 698 (cells 14 x 14..17, 32): a brick HEARTH (y 240..288, top 30 + cloth to 32, a box and a frame; fire opening to the east, read on the drawing u 0.34..0.79);
    # the armour heap on cell 14, 14 (y 224..240) is not modelled yet
    "merc_hearth_698": dict(rooms=[698], cells=[14, 15, 14, 17], floor=0,
                            parts=[("hearth", (224, 240, 240, 288, 0, 30), "+x", dict(open_u=(0.34, 0.79), open_h=0.85, depth=1.0)),
                                   ("rbox", (224.0, 241.0, 240.0, 288.0, 30.0, 32.0, 0.5)),
                                   ("box", (222.0 + 2.0, 230.0, 270.0, 277.0, 32.0, 38.0))] + FRAME_X(229.0, 249.0, 259.0, 32.0, 8.0)),
    # 704 (cell 32 x 25 on the floor 32, between the beds): a NIGHTSTAND (top 48 with a cloth, two drawers) open to the south
    "merc_night_704": dict(rooms=[704], cells=[32, 25, 32, 25], floor=32,
                           parts=[("cab", (512, 528, 400, 416, 32, 48), "+y", [("plinth", 2), ("drawers", 7, 1), ("drawers", 6, 1)])]),
    # 685 / 686 (cell 24 x 24, collision 32): the fortune teller's CRYSTAL BALL: a LOW wooden pedestal read pixel by pixel (user 2026-11-24 'Podest nicht genau genug'): a 15.5 x 15.5 block 14 high with a vertical groove in the middle of each face (the light stripes), a top plate 14..17 with a raised rim (the orange ring) round a dark sunken centre, a FLAT grey ring (user: 'flacheres Podest fuer die Kugel') and the glass ball resting on it, 2.7 back from the cell centre so the drawn ball position is kept: a true sphere r 5.0 = ONLY the blue pixels (user: 'nur das Blaue ist die Kugel'; the dark / grey pixels under it are the holder ring, 2 high; drawn 14 px wide: a sphere's picture width is 2 r x 1.41, user 2026-11-24 'zu gross')
    "merc_crystal_685": dict(rooms=[685, 686], cells=[24, 24, 24, 24], floor=0,
                             parts=[("rbox", (385.25, 398.75, 385.25, 398.75, 0.0, 14.0, 0.4))]   # core; four quarter blocks around it leave a 0.8 wide, 1 deep groove in the middle of each face
                                   + [("rbox", (qx, qx + 7.35, qy, qy + 7.35, 0.0, 14.2, 0.3)) for qx in (384.25, 392.4) for qy in (384.25, 392.4)]
                                   + [("tray", (384.25, 399.75, 384.25, 399.75, 14.0, 17.0), 1.75, 1.5),
                                    ("lathe", (389.3, 389.3, 15.4, 2.1, [(0.0, 2.6), (0.6, 3.2), (1.0, 3.4)], 16)),
                                    ("lathe", (389.3, 389.3, 16.8, 10.0, [((1.0 - math.cos(math.pi * t / 16.0)) / 2.0, max(0.3, 5.0 * math.sin(math.pi * t / 16.0))) for t in range(17)], 24))]),
    # 668 / 669 (cells 35..36 x 27..28, walkable 1 step): a square TABLE under a white CLOTH hanging down to z 3.5 on every side (one leg shows below the front)
    "merc_cloth_668": dict(rooms=[668, 669], cells=[35, 27, 36, 28], floor=0,
                         parts=[("rbox", (562.0, 590.0, 434.0, 462.0, 10.0, 13.5, 1.0)), ("rbox", (560.5, 591.5, 432.5, 463.5, 3.5, 16.0, 3.0))]
                               + [("rbox", (x, x + 2.5, y, y + 2.5, 0.0, 10.5, 0.6)) for x in (563.0, 586.5) for y in (435.0, 458.5)]),
}

def build(spec):
    out = []
    for p in spec["parts"]:
        if p[0] == "cab": out += cabinet.cabinet(*p[1], p[2], p[3], **(p[4] if len(p) > 4 else {}))
        elif p[0] == "box": out.append(rbox(*p[1], 0.3, n=1))
        elif p[0] == "rbox": out.append(rbox(*p[1][:6], p[1][6], n=2))
        elif p[0] == "lathe": out.append(lathe(*p[1]))
        elif p[0] == "hearth": out += cabinet.hearth(*p[1], p[2], **(p[3] if len(p) > 3 else {}))
        elif p[0] == "tray":   # open box: floor slab + four rounded rim walls (thickness p[2]), the inside p[3] deep
            x0, x1, y0, y1, z0, z1 = p[1]; t, dp = p[2], p[3]
            out.append(rbox(x0, x1, y0, y1, z0, z1 - dp, 0.4, n=1))
            for b in ((x0, x1, y0, y0 + t), (x0, x1, y1 - t, y1), (x0, x0 + t, y0 + t, y1 - t), (x1 - t, x1, y0 + t, y1 - t)): out.append(rbox(*b, z1 - dp - 0.5, z1, 0.5, n=1))
    return out

def write_ops(names):
    """--write NAME..: the OBJ per room (landstalker/data/proxies/NAME_ROOM.obj, NAME = spec name without its room suffix) + the 'mesh' op in
    landstalker/data/light_proxies.json (an op with the same file is replaced). The spec's floor is in world units."""
    import json, collections
    root = os.path.join(HERE, "..", "..", ".."); jp = os.path.join(root, "landstalker", "data", "light_proxies.json")
    data = json.load(open(jp), object_pairs_hook=collections.OrderedDict)
    for name in names:
        sp = SPECS[name]; base = name.rsplit("_", 1)[0]; ref = sp["rooms"][0]
        for r in sp["rooms"]:
            fn = "proxies/%s_%d.obj" % (base, r)
            write_obj(os.path.join(root, "landstalker", "data", fn), build(sp), "%s, room %d" % (name, r))
            ops = [e for e in data["rooms"].get(str(r), []) if e.get("file") != fn]
            ops.append(collections.OrderedDict([("op", "mesh"), ("cells", sp["cells"]), ("file", fn), ("surface", True), ("air", True), ("floor", sp["floor"]),
                ("why", "case furniture '%s' as a real model (remake/recipes/case/case.py spec %s, parts of remake/lib/cabinet.py: plinth, doors / drawers / compartments with contents, hearth, things on top), measured on rom_picture %d by projection overlay (indoor furniture survey 2026-11-24)" % (base, name, ref))]))
            data["rooms"][str(r)] = ops   # a new room goes to the end (the file keeps its order)
    open(jp, "w").write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    if sys.argv[1] == "--list":
        for k, s in SPECS.items(): print(k, s["rooms"], s["cells"])
    elif sys.argv[1] == "--write": write_ops(sys.argv[2:] if len(sys.argv) > 2 else [k for k in SPECS if k.startswith("merc_")])
    else: write_obj(sys.argv[1], build(SPECS[sys.argv[2]]), sys.argv[2])
