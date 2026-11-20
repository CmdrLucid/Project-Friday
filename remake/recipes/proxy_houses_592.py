"""LIGHT SHAPES (= near-final geometry, the AS-DRAWN variant): the LOG HOUSES of MASSAN, room 592 (HANDOFF -238 / -239, user 2026-11-20: Massan has
its own house type; remake house shapes exist: remake/recipes/massan_house_vc.py on remake/lib/massan_a.py = the style C REMAKE variant).
Memory 'remake vs light variant': the light takes the house as DRAWN, the remake keeps its own (rounder, more eave). So this recipe builds the
same measured geometry of lib/massan_a.py (log planes x 291 / 365, y 435 / 509, logs r 4 every 8, posts, open doorway east y 466..482 up to z 35,
round window south, eave 50, bulging thatch top 77) but with hx = HX (the drawn eave, the remake adds 1.5), fewer segments (light budget) and
no skull / ridge knot (thin parts the drawing shows only as pixels).
House A first (one model at a time, user OK before the next); B..F (the south house, the two joined pairs, the tall house) follow.
Run: python3 remake/tools/build_asset.py proxy_houses_592  ->  landstalker/data/proxies/house_592_a.obj"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
import blx, massan_a as H
blx.PIXEL = False
PROX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "data", "proxies")

def export(ob, name, title):
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.transform(ob.matrix_world); bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)
    bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.verts.index_update()
    path = os.path.join(PROX, name + ".obj")
    with open(path, "w") as fo:
        fo.write("# light proxy: %s (remake/recipes/proxy_houses_592.py). GAME coordinates x east, y south, z up, world units.\n" % title)
        fo.write("# our own geometry measured on the original picture (remake/lib/massan_a.py); read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        for v in bm.verts: fo.write("v %g %g %g\n" % (round(v.co.x, 2), round(-v.co.y, 2), round(v.co.z, 2)))
        for f in bm.faces: fo.write("f " + " ".join(str(v.index + 1) for v in reversed(f.verts)) + "\n")
    print("proxy_houses_592: %s: %d vertices, %d triangles -> %s" % (name, len(bm.verts), len(bm.faces), path))

mats = [blx.flat_material(n, (150, 150, 150)) for n in ("bark", "post", "endgrain", "dark", "hole", "thatch", "under", "plank")]
M = blx.Mesh("house_592_a", mats); M.density = 1.0
# A re-measured 2026-11-20 with the rule calibrated on B (post centre = dark edge of the drawn post + 4.5, door = dark span +- 1): the kit_c numbers sat
# 1.5..4 units too far along (door was 466..482, posts S 300 / 307 / 349 / 356, E 445 / 452 / 464 / 484 / 492 / 499); the remake (massan_a defaults) is unchanged
H.POSTS = dict(H.POSTS, S=[298.5, 305.5, 346.5, 353.5], N=[298.5, 305.5, 346.5, 353.5], E=[442.5, 449.5, 458.5, 481.5, 497.5], W=[442.5, 449.5, 489.5, 496.5])
H.DOOR = dict(H.DOOR, a0=462.0, a1=478.0)   # drawn dark 463..477
H.build(M, nseg=8, den=1.0, roof_jitter=0.0, hx=H.HX, lip=3.5, door="open", ridge_knot=False, log_over_door=True, mitre=True, back_in=3.0)   # no gap above the door (user)
export(M.finish(), "house_592_a", "Massan log house A (the lone house west of the statue), room 592")

import log_house as L
# HOUSE B (the south house, cells 34..38 x 29..35, 5 x 7): log planes = cell lines inset 3 (as A), ground 0, eave 50, top 77 like A (collision h 3);
# door S x 593..609 up to 35 (dark block on the S wall plane map), round window E at y 530 z 28, boarded window S left, ridge log bundle along y,
# two roof vents on the E slope (placed by eye, checked on the overlay)
B = dict(planes=(547, 621, 467, 573), z0=0, back_in=3.0, corners="mitre",   # flush corners (user 2026-11-20); the SW corner keeps its marks (noext W / ext S)
         doors=[("S", 590, 606, 35)],   # door: drawn dark opening U 1201..1216 (was 593..609)
         windows=[("E", 530, 28)], shutters=[("S", 557, 569, 24, 38, 3)],   # window x 556..567 z 24..38 behind a top-hinged shutter propped out 3 (drawn hinge edge U 1166..1177, its lower edge only ~3 px further left; user: was too far left with 553 / out 7)
        
         posts={"S": [586.5, 609.5],   # S: only the two posts beside the door are drawn (U 1196 / 1219); they hid the shutter (user)
                "N": [556, 563, 605, 612], "E": [476, 483, 557, 564], "W": [476, 483]},   # W: no posts at the S end (the drawing shows only the log ends at that corner, user)
         noext=[("W", 1)], ext={("S", 0): 1.5},   # S logs stick out only ~1.5 at the SW corner; spacing as drawn: corner -> shutter ~10, shutter -> door ~16 (user marks)
           # the W logs end at the S plane: no log ends at the SW corner in the drawing (user: the shutter looked as if at the corner)
         ridge="bundle", vents=[(606, 535), (608, 502)])   # vents: back-projected from the drawn cap centres U 1255 / 1290, V 502 / 487 onto the roof surface
MB = blx.Mesh("house_592_b", mats); MB.density = 1.0
L.build(MB, B)
export(MB.finish(), "house_592_b", "Massan log house B (the south house), room 592")

# WEST PAIR (cells 23..27 x 18..25, ground 32 = z0, collision h 5): TWO houses of 5 x 4 cells wall to wall (back C y 18..21, front D y 22..25), each with
# its own walls (the drawing shows two columns of log ends at the joint on the E side, y ~340 / ~355) and its own roof (back roof edge y 287..353,
# the front roof lies over it). Measured on the rectified wall pictures (2026-11-20): doors = the same tiles as B (dark 319..333 / 367..381 -> 318..334 /
# 366..382, top 35), posts beside them +-3.5 from the door edge; the E pattern repeats with a period of 48 (door cells y 20 / 23 in the height map).
# Roofs: one crossing of sticks at EACH END of the short ridge (x 400 / 416); back roof: square vent hood, cap top centre drawn at U 1251.5 V 269.5.
C = dict(planes=(371, 445, 291, 349), z0=32, back_in=3.0, corners="mitre", doors=[("E", 318, 334, 35)],
         posts={"E": [314.5, 337.5]},
         ridge="sticks_ends", sticks_shift=(3.5, -4.25), stick_r=2.6, vents=[(405.5, 338)])
D = dict(planes=(371, 445, 355, 413), z0=32, back_in=3.0, corners="mitre", doors=[("E", 366, 382, 35)],
         shutters=[("S", 397, 408, 22, 38, 6)],   # drawn plank: hinge edge x 397..407 at z 71, lower edge x 391..402 at z ~52 (6 left = propped out 6)
         posts={"E": [362.5, 385.5, 401.5], "S": [378.5, 385.5, 426.5, 433.5]},   # S posts in pairs 7 apart (dark edge of each drawn post + 4.5, as B)
         ridge="sticks_ends", sticks_shift=(3.5, -4.25), stick_r=2.6)   # drawn bindings at screen (+3.5, +6) from the ridge ends x 400 / 416 at the top: kept on the ridge -> x +3.5, z -4.25
# back_in=3 (2026-11-20, user: dark strip beside the roofs at night): the drawn W / N eave outline is 3 px inside the model's on ALL houses (front S / E
# edges match); the overhang lay over the ground and darkened it. corners="mitre" (user 2026-11-20 mark on the SE corner of D: 'eher eine normale Ecke im Sprite'): the drawing shows the logs of both walls meeting in a
# chevron at every corner (also at the joint), no stack of end discs; the protruding ends also made a serrated silhouette = frayed light edges.
for key, h, title in (("c", C, "west pair, back house C"), ("d", D, "west pair, front house D")):
    MM = blx.Mesh("house_592_" + key, mats); MM.density = 1.0
    L.build(MM, h)
    export(MM.finish(), "house_592_" + key, "Massan log house %s, room 592" % title)

# EAST PAIR (cells 32..36 x 16..24, ground 32): back house E 5 x 4 (y 16..19), front house F 5 x 5 (y 20..24), wall to wall like C / D (joint at the cell
# line y 320, same E wall tiles as C shifted by -32). Doors E dark 287..301 / 351..365 -> 286..302 / 350..366 (door cells y 18 / 22). Posts: dark edge of
# each drawn post + 4.5 (E: 273.5 [no post at 282.5], 305.5 / 346.5, 369.5, 385.5; F S in two pairs around the window). F S: plain open WINDOW (no
# shutter) between the posts 538.5 / 561.5, dark x 540..556, z 57..66 (25..34.5 above the ground). Roofs: E sticks at both ridge ends (bindings at the
# same screen offset as C / D), F square roof: one crossing in the middle (as A), vent hood cap top centre drawn at U 1401 V 366.
E_ = dict(planes=(515, 589, 259, 317), z0=32, back_in=3.0, corners="mitre", doors=[("E", 286, 302, 35)],
          posts={"E": [273.5, 305.5]},
          ridge="sticks_ends", sticks_shift=(3.5, -4.25), stick_r=2.6)
F_ = dict(planes=(515, 589, 323, 397), z0=32, back_in=3.0, corners="mitre", doors=[("E", 350, 366, 35)],
          openings=[("S", 540, 557, 25, 34.5)],
          posts={"E": [346.5, 369.5, 385.5], "S": [522.5, 538.5, 561.5, 577.5]},
          ridge="sticks", stick_r=2.6, vents=[(576, 359)])
for key, h, title in (("e", E_, "east pair, back house E"), ("f", F_, "east pair, front house F")):
    MM = blx.Mesh("house_592_" + key, mats); MM.density = 1.0
    L.build(MM, h)
    export(MM.finish(), "house_592_" + key, "Massan log house %s, room 592" % title)

# TALL HOUSE G (cells 23..27 x 14..17, ground 32, collision top 144 -> eave 146 = 114 above the ground, top 141 above it; footprint from the drawn roof
# corners, N part under the map's void rows). Measured 2026-11-20 on the rectified walls: E door = the same tile (dark 254..269, top 35), the two door
# posts run the full height (250.5 / 273.5); above it a SIGN board (grey frame y 253..268, z 44..60.5 above the ground) and an upper WINDOW (dark top at
# z 97.5 + 2.5 like the door, sill = the cloth's top z 89.5) with a blue CLOTH hanging out over the sill down the wall (drawn y 249..269, lower edge
# 72 at the sides / 67.5 in the middle; out 0.8 / 1.6, positions corrected for the projection shift). S: two round windows = A's tile (hole centroid offset as A) at x 400.5, z 59 / 91; posts 378.5 / 426.5.
G_ = dict(planes=(371, 445, 227, 285), z0=32, back_in=3.0, ze=114, zt=141, corners="mitre", doors=[("E", 254, 270, 35)],
          openings=[("E", 254, 270, 89.5, 100)], boards=[("E", 253, 269, 44, 60.5)],   # SMALL window (user 2026-11-20): only the dark strip above the cloth
          cloths=[("E", 250.2, 270.2, 90, 72.8, 68.3, 0.8, 1.6)],   # the cloth hangs OUT over the sill and down the outside of the wall (in front of the logs)
          windows=[("S", 400.5, 59), ("S", 400.5, 91)],
          posts={"E": [250.5, 273.5], "S": [378.5, 426.5]},
          ridge="sticks_ends", sticks_shift=(3.5, -4.25), stick_r=2.6)
MM = blx.Mesh("house_592_g", mats); MM.density = 1.0
L.build(MM, G_)
export(MM.finish(), "house_592_g", "Massan log house G (the tall house), room 592")
