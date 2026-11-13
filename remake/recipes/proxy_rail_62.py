"""LIGHT PROXY: the balustrades of room 62 (MERCATOR_CASTLE_MAIN_HALL_62): gallery rail + the two stair rails (user 2026-11-11, rec_20261111_2006:
'die Schatten auf der Treppe passen oft nicht'; HANDOFF -175 item 2).
The height map holds every balustrade as a SOLID wall one cell wide and 32 above the floor / stair (cells x 20 and x 43 rows 23..32, row 22 x 20..43):
the light cast a box shadow with straight edges beside the stairs.  Here the drawn balustrade, measured on the room picture with
remake/tools/proxy_overlay.py (projection U = x - y + 1184, V = (x + y) / 2 - z; 6x zoom, rom_picture.py windows U 990 V 300 / U 1400 V 400 / U 1080 V 160):
  stairs: step fronts at y 400 / 432 / 464 / 496 / 528, tread behind each front 96 / 80 / 64 / 48 / 32 (the game's cell heights x 18..19 / 44..45);
  LEFT rail: square posts x 324..328, y front..front + 4, from the upper tread t to t + 28 (ball top); handrail top t + 17 at the post, falling 16 per 32 (the stair);
  RIGHT rail (not a mirror of the left one, measured): posts x 700..704, y front - 8..front - 4, from t - 4 to t + 24, handrail top t + 13 at the post
  (the light posts are 8 long and reach t + 28: the drawn ball overhangs, user saw bright dots on the balls);
  (each fit is exact along the view ray (1, 1, 1) only: the variant inside the game's rail cell was taken)
  gallery: the rail along x at y 356..360 on the landing floor 96, posts at x 324 / 488 / 552 / 700 (corners + two middle posts, 4x zoom U 1290 V 270), handrail top 113;
  the stair tops connect to the gallery corners with a level rail (x 324 / 700, y 360..400 / 360..392).
Balusters: the drawing has ~4 thin turned balusters per 32 units; the light field has 4 unit columns, so one 4 unit baluster every 8 units (half the line
covered, like the drawing) under a handrail of 3 units ('air': the rail pieces between balusters are slabs).  The stone stringer under each rail keeps the
stair's stepped height (step moved to the post: left front + 4, right front - 4); the gallery cells are solid up to the landing floor 96.
Run: python3 remake/tools/build_asset.py proxy_rail_62   (six OBJs in landstalker/data/proxies/: rail_62_gallery / _left / _right = solid parts, + *_rail = handrail slabs)"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

STEPS = [(400, 96), (432, 80), (464, 64), (496, 48), (528, 32)]   # step front y, tread height behind (smaller y) the front
FLOOR = 16                                                         # hall floor
GY0, GY1, GZ, GRAIL = 356, 360, 96, 113                            # gallery rail line and landing floor
GPOSTS = [324, 488, 552, 700]
RDROP = 2   # handrail top this much below the drawn top (see span)

def box(name, x0, y0, x1, y1, z0, z1):
    return (name, x0, y0, x1, y1, z0, z1, z1, "flat", None)

def span(name, a0, a1, axis, fixed, z0f, railf):
    """balusters (4 wide, every 8) + handrail pieces (3 high slabs between them) from a0 to a1 along 'x' or 'y'; fixed = (c0, c1) across;
    z0f(a) = foot height, railf(a) = handrail top at a (piece centre)"""
    P = []; a = a0; k = 0
    while a + 4 <= a1:
        rz = min(railf(a), railf(a + 4)) - RDROP   # RDROP: the light rail is 4 wide (one sub column) but drawn as a thin line: its top face would catch the carpet pixels
        # just behind the drawn rail; 2 lower = the top face stays inside the drawn rail.  # the LOWER end: a flat 4 unit piece must not stick out above the drawn sloping rail (its top caught carpet pixels behind = bright dots, user 2026-11-11)
        if k % 2 == 1:   # baluster up to the rail
            lo, hi = z0f(a + 2), rz
        else:            # rail piece only (air below)
            lo, hi = rz - 3, rz
        r = (a, fixed[0], a + 4, fixed[1]) if axis == "x" else (fixed[0], a, fixed[1], a + 4)
        if hi > lo: P.append(box(("rail:%s_%d" if k % 2 == 0 else "%s_%d") % (name, k), r[0], r[1], r[2], r[3], lo, hi))
        a += 4; k += 1
    return P

def stair(side):
    P = []
    if side == "left":
        px, dy, dz, rh, cx0, cx1, y_top, plen, pup = 324, 0, 0, 17, 320, 336, 368, 4, 0
        step_at = lambda yf: yf + 4
    else:
        px, dy, dz, rh, cx0, cx1, y_top, plen, pup = 700, -8, -4, 13, 688, 704, 368, 8, 4   # posts 8 long + 4 higher: the drawn ball overhangs a 4 x 4 post
        # (user 2026-11-11 on the first try: 'auf den Saeulen ... lichte Punkte oben drauf' = ball pixels whose view ray missed the post and lit as the tread behind)
        step_at = lambda yf: yf - 4
    # stone stringer: the stair's stepped height, step under the post
    edges = [y_top] + [step_at(yf) for yf, t in STEPS] + [step_at(STEPS[-1][0]) + 4]
    heights = [t for yf, t in STEPS] + [FLOOR + 16]
    for i, (yf, t) in enumerate(STEPS):
        y0, y1 = edges[i], edges[i + 1]
        if y1 > y0: P.append(box("%s_stringer_%d" % (side, i), cx0, y0, cx1, y1, FLOOR, t))
    for i, (yf, t) in enumerate(STEPS):
        py = yf + dy
        P.append(box("%s_post_%d" % (side, i), px, py, px + 4, py + plen, t + dz, t + dz + rh - RDROP + pup))   # up to the rail, without the ball: the 4 x 4 top face is wider than the
        # drawn ball and caught the carpet pixels around it = a bright ring (user 2026-11-11 'lichte Punkte oben drauf')
        if i + 1 < len(STEPS):
            ztop = t + dz + rh
            foot = lambda a, yf=yf, t=t: t - 16 if a >= step_at(yf) else t
            rail = lambda a, py=py, ztop=ztop: ztop - 0.5 * (a - (py + 2))
            P += span("%s_span_%d" % (side, i), py + plen, py + 32, "y", (px, px + 4), foot, rail)
    # level rail from the gallery corner (y 360) to the top post
    top = STEPS[0][0] + dy
    P += span("%s_top" % side, y_top, top, "y", (px, px + 4), lambda a: GZ, lambda a: GRAIL)
    return P

def gallery():
    P = [box("gallery_floor", 320, 352, 704, 368, FLOOR, GZ)]
    for i, x in enumerate(GPOSTS): P.append(box("gallery_post_%d" % i, x, GY0, x + 4, GY1, GZ, GRAIL - RDROP))   # up to the rail (see stair posts)
    for i, (a, b) in enumerate(zip(GPOSTS, GPOSTS[1:])):
        P += span("gallery_span_%d" % i, a + 4, b, "x", (GY0, GY1), lambda q: GZ, lambda q: GRAIL)
    P += [box("rail:gallery_conn_l", 324, GY1, 328, 368, GRAIL - RDROP - 3, GRAIL - RDROP), box("rail:gallery_conn_r", 700, GY1, 704, 368, GRAIL - RDROP - 3, GRAIL - RDROP)]
    return P

# The light reads an OBJ as ONE column per 4 unit sub column (top = highest, bottom = lowest point): a handrail piece over the stringer would become
# a solid wall.  So two OBJs per balustrade: the solid part (stringer / landing, posts, balusters) and the handrail pieces ('rail:' parts), a second
# op with "air" whose pieces float above what the first op shaped = slabs (patch_lights.py op 5: the ground as earlier ops shaped it).
def both(name, parts, title, target, ppu, size):
    proxy.build(name, [q for q in parts if not q[0].startswith("rail:")], title, {}, target=target, ground_z=16, px_per_unit=ppu, size=size)
    proxy.build(name + "_rail", [q for q in parts if q[0].startswith("rail:")], title + " (handrail slabs)", {}, target=target, ground_z=16, px_per_unit=ppu, size=size)

both("rail_62_gallery", gallery(), "Gallery balustrade, room 62", (512, 360, 100), 2, (900, 500))
both("rail_62_left", stair("left"), "Left stair balustrade, room 62", (328, 460, 70), 4, (600, 600))
both("rail_62_right", stair("right"), "Right stair balustrade, room 62", (700, 460, 70), 4, (600, 600))
