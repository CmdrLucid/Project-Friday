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
# the LOG HOUSE BED of tileset 8 (reference 491 / 735 cells 15..17 x 14..15, head at the west, back at the north wall; user OK on the clay sheet 2026-11-25):
# a plank box exactly on the 3 x 2 cell collision box (16): a lower plank (0..8) and an upper course (8..16) with the drawn seam between them; the upper course =
# a 1 thick front board and foot board up to the top (the drawn front / foot faces are wood up to the top edge in two 8 high bands), bare boards at the head
# end; the grey mattress lies IN the frame, flush with its top (drawn without thickness: its front corner meets the box corner, head edge 17.5 from the head
# end), its rounded rim = the drawn dark outline; ONE flat pillow on the head boards, read on its drawn outline in 491 (U 1180..1199, V 221..233: 8 long x 12
# across x 2.5 high, rounded).  x0 / y0 = the box corner at the head end / back wall.
def BOATBED(x0, y0, z=0.0):
    R = lambda a, b, c, d, e, f, r: ("rbox", (x0 + a, x0 + b, y0 + c, y0 + d, z + e, z + f, r))
    return [R(0.0, 48.0, 0.0, 32.0, 0.0, 8.4, 0.8),          # lower plank
            R(0.0, 48.0, 31.0, 32.0, 7.6, 16.0, 0.45),       # upper front board (whole length: no joint on the face)
            R(47.0, 48.0, 0.0, 32.0, 7.6, 16.0, 0.45),       # upper foot board
            R(0.0, 17.5, 0.0, 31.5, 7.6, 16.0, 0.6),         # head boards
            R(17.0, 47.5, 0.0, 31.5, 7.6, 12.6, 0.5),        # bed bottom under the mattress
            R(17.6, 46.9, 0.2, 30.9, 12.2, 16.0, 1.3),       # mattress (cloth), flush with the frame top
            R(3.5, 11.5, 11.5, 23.5, 16.0, 18.8, 1.2)]       # pillow (cloth)
def BOATBED_Y(x0, y0, z=0.0):   # the same bed mirrored at the diagonal: head at the NORTH wall (y0), running south (2 x 3 cells), back at the west wall (x0)
    return [("rbox", (x0 + b[2], x0 + b[3], y0 + b[0], y0 + b[1], b[4], b[5], b[6])) for b in (q[1] for q in BOATBED(0.0, 0.0, z))]
# the CLAY JAR of tileset 8 (furniture.JAR, fitted on 597; axis 3 in front of its cell centre in +x / +y) as a case part: x / y = its axis
def TS8JAR(x, y, z=0.0):
    import furniture
    return [("lathe", (x, y, z, 23.0, [(zz / 23.0, r) for zz, r in furniture.JAR["prof"]], 24))]
def TILTLATHE(x, y, z, h, prof, seg, lean):   # a lathe whose axis leans: lean = (dx, dy) offset of the TOP centre against the foot (a tilted sack mouth)
    import math
    V, F = lathe(x, y, z, h, prof, seg); L = math.sqrt(lean[0] ** 2 + lean[1] ** 2 + h * h); ux, uy, uz = lean[0] / L, lean[1] / L, h / L
    def rot(p):   # rotate p about the foot centre so that +z goes to (ux, uy, uz) (Rodrigues, axis = z x u)
        ax, ay = -uy, ux; sn = math.sqrt(ax * ax + ay * ay); c = uz
        if sn < 1e-9: return p
        ax, ay = ax / sn, ay / sn; px, py, pz = p[0] - x, p[1] - y, p[2] - z; d = ax * px + ay * py
        cx, cy, cz = ay * pz, -ax * pz, ax * py - ay * px   # axis x p (axis z component 0)
        return (x + px * c + cx * sn + ax * d * (1 - c), y + py * c + cy * sn + ay * d * (1 - c), z + pz * c + cz * sn)
    return [("raw", [([rot(p) for p in V], F)])]
def obox(o, a, b, c):
    """a closed box from corner o spanned by the vectors a, b, c (any directions) -> (vertices, outward faces)"""
    P = lambda i, j, k: tuple(o[q] + i * a[q] + j * b[q] + k * c[q] for q in range(3))
    v = [P(i, j, k) for i in (0, 1) for j in (0, 1) for k in (0, 1)]   # index = 4 i + 2 j + k
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    cr = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    if cr[0] * c[0] + cr[1] * c[1] + cr[2] * c[2] < 0: f = [tuple(reversed(q)) for q in f]
    return (v, f)

def easel_frame(xb, yb, z0, L=7.5, H=9.2, tilt=53.5, t=1.0):   # sizes incl. the 1 px black outline
    """the small PICTURE FRAME on an easel back of the Mercator furniture (one tile drawing in 616 675 677 683 687 689 698 717, user 2026-11-24
    'ein Viereck mit einem Staender hinten raus'): a square plate L along y, H up its slope, leaning back by `tilt` degrees from upright, the picture
    facing +x and up; its lower front edge at x = xb, y = yb - L .. yb, on z0 (read on the drawn corners of 687); a strut from its back down to z0."""
    import math
    th = math.radians(tilt); up = (-math.sin(th) * H, 0.0, math.cos(th) * H); nb = (-math.cos(th) * t, 0.0, -math.sin(th) * t)
    plate = obox((xb, yb - L, z0 + 0.3), (0.0, L, 0.0), up, nb)
    # the strut as DRAWN = the two brown pixels at the frame's lower left (user 2026-11-24): a short steep leg from the back of the plate at
    # 0.46 of its slope, left edge, straight down onto the top it stands on (687: attach (210.4, 279.3, 34.0), foot (209.65, 280.55, 32))
    k = 0.46; ax, az, ay = xb + up[0] * k + nb[0], z0 + 0.3 + up[2] * k + nb[2], yb + 0.4
    fx, fy = ax - 0.75, ay + 1.25
    strut = obox((fx - 0.45, fy - 0.45, z0), (ax - fx, ay - fy, az - z0 + 0.3), (0.0, 0.9, 0.0), (0.9, 0.0, 0.0))
    return [plate, strut]
OVAL = lambda x, y, z: [("raw", easel_frame(x, y, z))]   # (name kept from the first reading: the frame is SQUARE on an easel back)
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
                                + FLASK(260.4, 344.4, 48.0) + OVAL(266.4, 338.9, 48.0)),
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
                                 + FLASK(278.0, 376.0, 36.0) + OVAL(279.4, 359.9, 33.0) + VASE(278.0, 358.0, 33.0)
                                 + SHELF_X(272.0, 13.0, 336.0, 384.0, 61.0) + PLATES(278.5, 350.0, 61.0) + PLATES(278.5, 364.0, 61.0, 8.0) + BOTTLE(278.0, 378.0, 61.0)),
    # 677 (cells 17 x 17..20, 64): the same corner on four cells: CHEST OF DRAWERS (y 320..336), BOOKCASE (y 290..320), a clay jar (y ~280), WALL SHELF (top 61) with plates, a box and two bottles
    "merc_chest_677": dict(rooms=[677], cells=[17, 17, 17, 20], floor=0,
                           parts=[("cab", (272, 288, 320, 336, 0, 36), "+x", [("plinth", 2), ("drawers", 8, 1), ("drawers", 8, 1), ("drawers", 8, 1), ("drawers", 8, 1)]),
                                  ("cab", (272, 286, 290, 320, 0, 33), "+x", [("plinth", 2), ("drawers", 8, 2), ("shelf", 21)])]
                                 + FLASK(278.0, 328.0, 36.0) + OVAL(279.4, 311.9, 33.0) + VASE(278.0, 313.0, 33.0) + JARFIT(285.0, 285.0)
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
    # 683 / 684 (cells 18 x 22..26, 32): a NIGHTSTAND (y 352..368, top 17 = lower than the bookcase, drawn front corner) and a long low BOOKCASE (y 368..416.5, top 34; user marks 2026-11-24; the cello leaning beside it is not modelled yet) with a box, a vase and a frame, open to the east
    "merc_books_683": dict(rooms=[683, 684], cells=[18, 22, 18, 26], floor=0,
                           parts=[("cab", (290, 304, 352, 368, 0, 17), "+x", [("plinth", 2), ("drawers", 7.5, 1), ("drawers", 7.5, 1)]),
                                  ("cab", (290, 304, 368, 416.5, 0, 34), "+x", [("plinth", 2), ("drawers", 9, 3), ("shelf", 21, 2)]),
                                  ("box", (298.0, 306.0, 404.0, 411.0, 34.0, 40.0))] + VASE(301.0, 400.0, 34.0) + OVAL(300.4, 388.9, 34.0)),
    # 687 / 688 (cells 13 x 13..17, 48): a brick HEARTH (y 240..288, top 32 with a cloth, a box and a frame; fire opening to the east) and a GLASS CABINET
    # (y 208..240, front x 223: its front corner on the drawn outline column, lightedges 2026-11-24; 48) open to the east
    "merc_hearth_687": dict(rooms=[687, 688], cells=[13, 13, 13, 17], floor=0, carrier={"r": 4, "axis": [230, 269], "z": 12},
                            parts=[("hearth", (208, 224, 240, 288, 0, 30), "+x", dict(open_u=(0.34, 0.86), open_h=0.85, depth=1.0)),
                                   ("rbox", (208.0, 225.0, 240.0, 288.0, 30.0, 32.0, 0.5)),
                                   ("cab", (208, 223, 208, 240, 0, 48), "+x", [("plinth", 2), ("glassflat", 22, 2), ("glassflat", 22, 2)]),
                                   ("box", (211.5, 218.5, 259.5, 266.5, 32.0, 38.0))] + OVAL(214.4, 278.9, 32.0)),
    # 687 / 688 (cells 13 x 19..20, 32): a low BOOKCASE open to the east with a vase and a small box
    "merc_books_687": dict(rooms=[687, 688], cells=[13, 19, 13, 20], floor=0,
                           parts=[("cab", (208, 222, 304, 336, 0, 31.5), "+x", [("plinth", 2), ("drawers", 8, 2), ("shelf", 21.5)]),
                                  ("box", (213.75, 219.75, 309.75, 315.75, 31.5, 35.5))] + VASE(215.75, 327.75, 31.5)),
    # 689 / 690 (cells 17..19 x 13, 64): the house corner of house_shelf.py on the north wall: a clay jar (x ~280), a low GLASS CABINET (x 291.5..318.5, 17 deep, top 33.5) with a
    # box, AIR, and the WALL SHELF (top 47, 14.5 deep: re-read pixel by pixel on the drawn corner points; lower than in 691) with plates, a bottle and a flask
    "merc_shelf_689": dict(rooms=[689, 690], cells=[17, 13, 19, 13], floor=0,
                           parts=[("cab", (291.5, 318.5, 208, 225, 0, 33.5), "+y", [("plinth", 2), ("glassflat", 29.5, 2)]), ("box", (299.0, 304.0, 217.0, 222.0, 33.5, 36.5))]
                                 + JARFIT(285.0, 221.0) + SHELF_Y(208.0, 14.5, 272.0, 320.0, 47.0) + PLATES(288.0, 215.0, 47.0, 8.0) + BOTTLE(300.0, 215.0, 47.0) + FLASK(312.0, 216.0, 47.0)),
    # 689 / 690 (cells 13 x 17..19, 48): a BOOKCASE (y 304..320, 48: drawn top corner, user 2026-11-24 'geht deutlich hoeher') with a vase and a CHEST OF DRAWERS (y 272..304, 32, two columns) with a frame, open to the east
    "merc_chest_689": dict(rooms=[689, 690], cells=[13, 17, 13, 19], floor=0,
                           parts=[("cab", (208, 222, 304, 320, 0, 48), "+x", [("plinth", 2), ("drawers", 8, 1), ("shelf", 19), ("shelf", 18)]),
                                  ("cab", (208, 223, 272, 304, 0, 32), "+x", [("plinth", 3), ("drawers", 9, 2), ("drawers", 9, 2), ("drawers", 9, 2)])]
                                 + VASE(212.0, 312.0, 48.0) + OVAL(218.4, 290.9, 32.0)),
    # 717 / 718 (cells 13 x 12..18, 48): a CHEST OF DRAWERS (y 192..240, top 36, three columns) with a frame and a flask, a tall BOOKCASE (y 240..272, 48)
    # with a flask and a vase, and two clay jars at the south end; open to the east (corners read on the drawing)
    "merc_chest_717": dict(rooms=[717, 718], cells=[13, 12, 13, 18], floor=0,
                           parts=[("cab", (208, 224, 192, 240, 0, 36), "+x", [("plinth", 3), ("drawers", 8, 3), ("drawers", 8, 3), ("drawers", 8, 3), ("drawers", 8, 3)]),
                                  ("cab", (208, 223, 240, 272, 0, 48), "+x", [("plinth", 2), ("drawers", 9, 2), ("shelf", 18), ("shelf", 17)])]
                                 + OVAL(222.4, 230.9, 36.0) + FLASK(218.0, 207.0, 36.0) + FLASK(212.5, 262.0, 48.0) + VASE(218.0, 255.0, 48.0)
                                 + JARFIT(221.0, 285.0) + JARFIT(221.0, 301.0)),
    # 722 / 723 (cells 18..20 x 16..21, 48): a GLASS CABINET (x 288..304, y 320..352, 48, open to the east), a CHEST OF DRAWERS (y 290..320, top 33: re-read on its drawn right top corner) with a vase and
    # a box, a clay jar, a brick HEARTH along the north wall (x 288..336, 12 deep, top 30 with a cloth, two flasks + a box; fire opening to the south at x 300..316 = where the fire is DRAWN: the game puts the flame light on the drawn fire's view ray, a solid jamb there threw the light out in front = a hard shadow edge on the cloth, user 2026-11-24) and the
    # WALL SHELF over it (x 288..336, top 61 read on its drawn left top corner, above the collision) with two plate stacks and a bottle
    "merc_corner_722": dict(rooms=[722, 723], cells=[18, 16, 20, 21], floor=0, carrier={"r": 4, "axis": [308, 274], "z": 12},
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
    "merc_hearth_698": dict(rooms=[698], cells=[14, 15, 14, 17], floor=0, carrier={"r": 4, "axis": [246, 267], "z": 12},
                            parts=[("hearth", (224, 240, 240, 288, 0, 30), "+x", dict(open_u=(0.34, 0.79), open_h=0.85, depth=1.0)),
                                   ("rbox", (224.0, 241.0, 240.0, 288.0, 30.0, 32.0, 0.5)),
                                   ("box", (222.0 + 2.0, 230.0, 270.0, 277.0, 32.0, 38.0))] + OVAL(234.4, 258.9, 32.0)),
    # 491 / 735 (boatman's house after Destel, tileset 8; cells 15..17 x 14..15, collision 16 walkable): the LOG HOUSE BED (BOATBED above); the same drawing (cell top
    # blocks $05E..$062) stands in 517 (cells 25..27 x 17..18) and twice in 732 (cells 14..16 x 14..15 and 14..16 x 17..18); 728 has it mirrored (cells 14..15 x 14..16)
    "boat_bed_491": dict(rooms=[491, 735], cells=[15, 14, 17, 15], floor=0, parts=BOATBED(240.0, 224.0)),
    "boat_bed_517": dict(rooms=[517], cells=[25, 17, 27, 18], floor=0, parts=BOATBED(400.0, 272.0)),
    "boat_bed_732": dict(rooms=[732], cells=[14, 14, 16, 18], floor=0, parts=BOATBED(224.0, 224.0) + BOATBED(224.0, 272.0)),
    "boat_bed_728": dict(rooms=[728], cells=[14, 14, 15, 16], floor=0, parts=BOATBED_Y(224.0, 224.0)),   # mirrored: head at the north wall (overlay checked)
    # 491 / 735: the WEST BOOKCASE ROW (cells 14 x 14..20, collision 48): three open bookcases of the same height side by side, fronts to the east, three book shelves
    # each: back y 224..256 (a bottle + a round flask on top), middle 256..304 (a small grey idol + two lying book stacks), front 304..336 (the two tileset 8 clay jars
    # on top at their usual cell offset); the front end shows its plank side panel (drawn)
    "boat_books_491": dict(rooms=[491, 735], cells=[14, 14, 14, 20], floor=0,
                           parts=[("cab", (224, 240, 224, 256, 0, 48), "+x", [("plinth", 2), ("shelf", 15), ("shelf", 15), ("shelf", 15)]),
                                  ("cab", (224, 240, 256, 304, 0, 48), "+x", [("plinth", 2), ("shelf", 15), ("shelf", 15), ("shelf", 15)]),
                                  ("cab", (224, 240, 304, 336, 0, 48), "+x", [("plinth", 2), ("shelf", 15), ("shelf", 15), ("shelf", 15)])]
                                 + TS8JAR(235.0, 315.0, 48.0) + TS8JAR(235.0, 331.0, 48.0)
                                 + [("rbox", (229.0, 234.0, 284.5, 289.5, 48.0, 58.0, 1.2)), ("lathe", (231.5, 287.0, 58.0, 6.0, [(0.0, 2.2), (0.5, 2.8), (1.0, 1.0)], 12))]   # idol
                                 + [("rbox", (228.5, 237.5, 268.5, 277.0, 48.0, 51.0, 0.6)), ("rbox", (229.0, 237.0, 269.0, 276.5, 51.0, 53.0, 0.6))]                          # book stack
                                 + [("rbox", (228.0, 237.0, 252.0, 261.0, 48.0, 51.0, 0.6)), ("rbox", (228.5, 236.5, 252.5, 260.5, 51.0, 53.0, 0.6))]                          # book stack
                                 + [("lathe", (230.5, 243.0, 48.0, 12.0, [(0.0, 2.3), (0.85, 2.3), (0.9, 1.2), (1.0, 1.2)], 12))]                                             # bottle
                                 + [("lathe", (233.5, 237.5, 48.0, 10.0, [(0.0, 2.0), (0.3, 3.2), (0.6, 2.4), (0.75, 0.9), (1.0, 1.0)], 12))]),                              # round flask
    # 491 / 735: the small BOOKCASE right of the bed (cells 18..19 x 14, collision 32): open to the south, two book shelves, plain east side; on top a lying book
    # stack, a vase with a flower (body 10 + flower 8) and a small ball at the front corner
    "boat_cab_491": dict(rooms=[491, 735], cells=[18, 14, 19, 14], floor=0,
                         parts=[("cab", (288, 320, 224, 240, 0, 32), "+y", [("plinth", 2), ("shelf", 14), ("shelf", 14)])]
                               + [("rbox", (299.5, 308.5, 227.5, 236.0, 32.0, 34.5, 0.6)), ("rbox", (300.0, 308.0, 228.0, 235.5, 34.5, 36.5, 0.6))]   # book stack
                               + [("lathe", (312.0, 228.0, 32.0, 10.0, [(0.0, 1.5), (0.35, 2.3), (0.75, 1.2), (1.0, 1.6)], 12)),           # vase (body 10 + flower 8, read on the drawing)
                                  ("lathe", (312.0, 228.0, 42.0, 8.0, [(0.0, 0.6), (0.35, 2.4), (0.75, 2.6), (1.0, 0.6)], 12))]
                               + [("lathe", (315.0, 238.0, 32.0, 4.0, [(0.0, 0.8), (0.15, 1.7), (0.5, 2.0), (0.85, 1.7), (1.0, 0.6)], 12))]),        # small ball
    # 491 / 735: the TABLE on legs (cells 17..19 x 19..20, collision 16): furniture.mercator_table_mesh (the same build as the approved Mercator table: flat top,
    # the light rim lines = paint) on the cell box, here with POINTED corners (rc 0.6), a 2.5 top and thin legs (r 1.3, 1.5 in from the corners), all read on the
    # drawing; on top a candle on a blue holder, an open book, a lantern (base, glass body, cap), a cup and a green bottle
    "boat_table_491": dict(rooms=[491, 735], cells=[17, 19, 19, 20], floor=0,
                           parts=[("raw", __import__("furniture").mercator_table_mesh(272.0, 304.0, 320.0, 336.0, 0.0, 16.0, 2.5,
                                   dict(__import__("furniture").MERCATOR_FINE, rc=0.6, ex0=0.0, ey0=0.0, leg_r=1.3, i0=1.5, i1=1.5)))]
                                 + [("lathe", (282.0, 327.0, 16.0, 7.5, [(0.0, 1.8), (0.2, 1.8), (0.22, 0.9), (1.0, 0.9)], 12))]                           # candle on a holder
                                 + [("rbox", (283.0, 293.0, 314.0, 324.0, 16.0, 17.5, 0.4)), ("rbox", (283.5, 292.5, 314.5, 323.5, 17.5, 19.0, 0.7))]       # open book (drawn 20 x 13.6 px: raised pages)
                                 + [("lathe", (310.5, 324.5, 16.0, 12.0, [(0.0, 3.0), (0.15, 3.0), (0.18, 3.3), (0.75, 3.3), (0.8, 2.2), (1.0, 1.2)], 16))]   # lantern
                                 + [("lathe", (301.5, 329.0, 16.0, 3.0, [(0.0, 1.6), (1.0, 2.2)], 12))]                                                   # cup
                                 + [("lathe", (312.5, 316.5, 16.0, 10.0, [(0.0, 1.6), (0.6, 1.6), (0.75, 0.7), (1.0, 0.7)], 12))]),                        # green bottle
    # 491 / 735: the grey SACK in the north-east corner (cell 20 x 14, collision 16): a round belly (drawn 25 px wide = r 8.8, flattened on the floor), a neck with the
    # open mouth on its upper west side (fitted on the drawn sack pixels)
    "boat_sack_491": dict(rooms=[491, 735], cells=[20, 14, 20, 14], floor=0,
                          parts=[("lathe", (328.5, 232.5, 0.0, 14.5, [(0.0, 7.0), (0.14, 8.3), (0.34, 8.8), (0.55, 8.6), (0.75, 7.4), (0.9, 5.2), (1.0, 3.0)], 32)),   # belly (1.3 into the void wall behind)
                                ] + TILTLATHE(324.0, 236.5, 12.5, 8.0, [(0.0, 3.6), (0.3, 3.06), (0.5, 3.6), (0.8, 4.8), (1.0, 4.56)], 24, (1.5, -3.5))),   # tied neck flaring to the open mouth on the belly's upper WEST side, leaning
                                # back (the drawn dark opening; fitted by IoU on the drawn sack pixels, 0.67 belly alone -> 0.79 with the tied / flared neck; user mark 2026-11-25 'liegt noch nicht ganz drauf')
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
        elif p[0] == "raw": out += p[1]
        elif p[0] == "hearth": out += cabinet.hearth(*p[1], p[2], **(p[3] if len(p) > 3 else {}))
        elif p[0] == "tray":   # open box: floor slab + four rounded rim walls (thickness p[2]), the inside p[3] deep
            x0, x1, y0, y1, z0, z1 = p[1]; t, dp = p[2], p[3]
            out.append(rbox(x0, x1, y0, y1, z0, z1 - dp, 0.4, n=1))
            for b in ((x0, x1, y0, y0 + t), (x0, x1, y1 - t, y1), (x0, x0 + t, y0 + t, y1 - t), (x1 - t, x1, y0 + t, y1 - t)): out.append(rbox(*b, z1 - dp - 0.5, z1, 0.5, n=1))
    return out

def small(p, floor):
    """a part standing ON the furniture (not on the floor and not a case / hearth / shelf board): flasks, vases, bottles, plates, boxes, frames, the crystal ball"""
    if p[0] == "lathe": return p[1][2] > floor + 1.0
    if p[0] == "box": return p[1][4] > floor + 1.0
    if p[0] == "raw": return min(v[2] for V, F in p[1] for v in V) > floor + 1.0
    return False

def write_split(path, spec, title):
    """the OBJ with the small things after 'g nofield' (patch_lights.py mesh_cells: GPU surfaces + shadows, but no light field blocks / room light steps)"""
    big = build(dict(spec, parts=[p for p in spec["parts"] if not small(p, spec["floor"])]))
    sm = build(dict(spec, parts=[p for p in spec["parts"] if small(p, spec["floor"])]))
    with open(path, "w") as fo:
        fo.write("# %s (remake/recipes/case/case.py). GAME coordinates x east, y south, z up, world units.\n" % title)
        fo.write("# our own geometry fitted to the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh'); parts after 'g nofield' do not stamp the light field.\n")
        b = 0
        for grp, ps in (("furniture", big), ("nofield", sm)):
            if not ps: continue
            fo.write("g %s\n" % grp)
            for V, F in ps:
                for v in V: fo.write("v %.3f %.3f %.3f\n" % v)
                for f in F: fo.write("f " + " ".join(str(i + 1 + b) for i in f) + "\n")
                b += len(V)
    print("%s: %d + %d small parts" % (path, len(big), len(sm)))

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
            write_split(os.path.join(root, "landstalker", "data", fn), sp, "%s, room %d" % (name, r))
            ops = list(data["rooms"].get(str(r), [])); at = next((i for i, e in enumerate(ops) if e.get("file") == fn), None)   # replace IN PLACE: the op order decides who owns a sub column
            ops = [e for e in ops if e.get("file") != fn]
            ops.insert(len(ops) if at is None else at, collections.OrderedDict([("op", "mesh"), ("cells", sp["cells"]), ("file", fn), ("surface", True), ("air", True), ("floor", sp["floor"])]
                + ([("carrier", collections.OrderedDict(sorted(sp["carrier"].items(), key=lambda t: "raz".index(t[0][0]))))] if sp.get("carrier") else []) + [
                ("why", "case furniture '%s' as a real model (remake/recipes/case/case.py spec %s, parts of remake/lib/cabinet.py: plinth, doors / drawers / compartments with contents, hearth, things on top), measured on rom_picture %d by projection overlay (indoor furniture survey 2026-11-24)%s" % (base, name, ref, "; carrier = the fire's flame light fixed 6 in front of the opening (the game's wall flame offset), below the hearth top (it streaked the top from just above = hard item shadows, user marks 2026-11-24)" if sp.get("carrier") else ""))]))
            data["rooms"][str(r)] = ops   # a new room goes to the end (the file keeps its order)
    open(jp, "w").write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    if sys.argv[1] == "--list":
        for k, s in SPECS.items(): print(k, s["rooms"], s["cells"])
    elif sys.argv[1] == "--write": write_ops(sys.argv[2:] if len(sys.argv) > 2 else [k for k in SPECS if k.startswith("merc_")])
    else: write_obj(sys.argv[1], build(SPECS[sys.argv[2]]), sys.argv[2])
