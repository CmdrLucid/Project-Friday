"""LIGHT PROXY: Mercator fountain court, room 638 (MERCATOR_FOUNTAIN; landstalker/docs/LIGHT_PROXY_PLAN.md 'Blender shapes', user 2026-11-04: 'weiter damit').
An invisible shape for the lighting only (never drawn). Why: the height map holds the city wall only as BLOCKED height 0 cells (column 17) and the round towers as
single blocked cells of height 9 (column 18, rows 26..29 / 38..41 / 50..53), so the automatic proposal made a 32 unit strip with a hip up to 247 IN FRONT of the wall
(cells 18..19 = the walkable bank) and no towers; the pines at the north wall (cells 25..27 x 19..20) got a hip up to 222 (the wall behind them counted as their height).
RE-MEASURED 2026-11-09 (HANDOFF 0a355; same method as the gate 637; projection U = x - y + 1184, V = (x + y) / 2 - z; bank z 48):
  west wall: face x 288 (layer A wall segments, foot on the bank: about half the columns exactly 288, fit_foot), one cell thick (x 272..288);
  towers: BOXES on their collision blocks (column 18 = x 288..304, rows 26..29 / 38..41 / 50..53), like the gate 637 towers: the front
          tower's foot corners sit exactly on U 608 / 624 (V 528 / 536); only the shading is round;
  tops: everything runs out of the picture (black above, cut in steps of 16 picture columns = the drawn merlon blocks); height = the highest
          block start on the front edge: wall 248 (y 864..912), 240 (672..800), 232 / 224 (576..608 / 480..576), 216 / 208 (400..416 / 288..400);
          towers 280 / 264 / 240 (front to back); north wall (face y 288, x 288..) 192 along its whole length;
  the pines at the north wall are catalogue object models (blockcat cells 638: P), no stand-in.
v2 2026-11-18 (user rule: light shapes = near-final 3D models, never boxes; user chose variant 'C' on the overlay ~/Project-Friday-Test/lktest/proxy638/mock):
  the towers are drawn ROUND (curved brick rows, narrow bricks at the edges) but their foot sits on the collision edge x 304 (grass is drawn in front):
  each tower = half cylinder r 32 centred on the wall face (288, cy), CLIPPED at x 304 (round flanks, flat front on the collision edge); the full half
  cylinder (to x 320) stood in the drawn grass. Fit: left edge U 608 exact, right edge U 684 (drawing 688), foot on the drawn grass line.
  DOOR NICHES (measured by colour: the door slab has only the colours 72,72,36 / 144,144,108, no black joints / white highlights): every tower
  y cy-15 .. cy-1, z 48 .. 120 (tower 1 U 657..670, V 444..516), 4 deep (one light sub column); the wooden door in the west wall y 336..352,
  z 48 .. 90 (U 1120..1136, V 226..265), 4 deep.  The tops leave the picture (cut in 16 column steps by the black): flat at the measured heights.
  The remake builds its own symmetric towers later (remake/MODELS.md, 'remake vs light variant').
Run: python3 remake/tools/build_asset.py proxy_wall_638
Output: landstalker/data/proxies/wall_638.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_wall_638/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy, blx

G = 48            # bank / ground height
WX0, WX1 = 272, 288   # west wall, one cell thick, face x 288
R, CLIP = 32, 304     # tower radius (centre on the wall face) and the collision edge that flattens the front
ND = 4                # niche depth (one light sub column)
TOWERS = [("t1", 832, 280), ("t2", 640, 264), ("t3", 448, 240)]   # centre y, top z (front to back)
WALL = [(864, 912, 248), (672, 800, 240), (576, 608, 232), (480, 576, 224), (400, 416, 216), (272, 400, 208)]   # visible west wall segments y0, y1, top
BEHIND = [(800, 864, 248), (608, 672, 240), (416, 480, 224)]   # the wall behind each tower (keeps the wall closed)
DOOR = (336, 352, 90)   # the wooden door in the west wall: y0, y1, top

def arc(cy, y0, y1, n=48):
    """the clipped tower outline (x, y) from y0 to y1 (y0 < y1) on the round / flat front, as a list along y"""
    pts = []
    for i in range(n + 1):
        y = y0 + (y1 - y0) * i / n
        d = y - cy; x = WX1 + math.sqrt(max(R * R - d * d, 0.0)); pts.append((round(min(x, CLIP), 3), round(y, 3)))
    return pts

def slab(name, y0, y1, z0, z1, x1=None, top_arc=None, cy=None):
    """a convex prism between y0 and y1: back on the wall face x 288, front = the tower outline (cy given) or the plane x1"""
    if cy is not None: front = arc(cy, y0, y1)
    else: front = [(x1, y0), (x1, y1)]
    poly = [(WX1, y0)] + front + [(WX1, y1)]
    poly = [p for k, p in enumerate(poly) if k == 0 or p != poly[k - 1]]
    return {"name": name, "poly": poly, "z0": z0, "z1": z1}

parts = []
for nm, cy, top in TOWERS:   # round tower in three convex pieces below the niche top, whole above it
    a, b = cy - R, cy + R; n0, n1 = cy - 15, cy - 1
    parts.append(slab(nm + "_n", a, n0, G, 120, cy=cy))           # north flank
    parts.append(slab(nm + "_s", n1, b, G, 120, cy=cy))           # south flank
    parts.append(slab(nm + "_b", n0, n1, G, 120, x1=CLIP - ND))   # behind the door niche
    parts.append(slab(nm + "_top", a, b, 120, top, cy=cy))        # above the niche
for k, (y0, y1, top) in enumerate(WALL + BEHIND):
    if (y0, y1) == (272, 400):   # the segment with the wooden door
        d0, d1, dt = DOOR
        parts += [("w_door_n", WX0, y0, WX1, d0, G, top, top, "flat", None), ("w_door_s", WX0, d1, WX1, y1, G, top, top, "flat", None),
                  ("w_door_b", WX0, d0, WX1 - ND, d1, G, dt, dt, "flat", None), ("w_door_t", WX0, d0, WX1, d1, dt, top, top, "flat", None)]
    else: parts.append(("w%d" % k, WX0, y0, WX1, y1, G, top, top, "flat", None))
parts.append(("north", 272, 272, 496, 288, G, 192, 192, "flat", None))   # north wall (row 17 of the blocked rows 12..17), one cell thick like the west wall

proxy.build("wall_638", parts, "Mercator fountain court city wall with round towers, room 638 (v2)", {"north": (200, 195, 170)}, target=(330, 600, 120), ground_z=G, px_per_unit=0.9, size=(1000, 900))
import bpy   # clay previews of the front tower: game direction, turned -40 / +40 / +80 degrees and from above (MODELING_LESSONS 1)
sc = bpy.context.scene; out = os.environ.get("R_OUT", "/tmp/proxy_wall_638"); sc.camera.data.ortho_scale = 300
sc.render.resolution_x, sc.render.resolution_y = 700, 700
for tag, yaw, el in (("game", 0, 30), ("turn_m40", -40, 20), ("turn_p40", 40, 20), ("turn_p80", 80, 15), ("top", 0, 89)):
    blx.orbit(sc.camera, (296, -800, 140), yaw, el_deg=el, dist=1500); sc.render.filepath = os.path.join(out, "close_%s.png" % tag); bpy.ops.render.render(write_still=True)
