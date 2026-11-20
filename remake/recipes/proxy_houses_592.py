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
H.POSTS = dict(H.POSTS, E=[445, 452, 462.5, 485.5, 492, 499])     # door posts beside the opening (as kit_c.house_a, from the picture)
H.build(M, nseg=8, den=1.0, roof_jitter=0.0, hx=H.HX, lip=3.5, door="open", ridge_knot=False, log_over_door=True)   # no gap above the door (user)
export(M.finish(), "house_592_a", "Massan log house A (the lone house west of the statue), room 592")

import log_house as L
# HOUSE B (the south house, cells 34..38 x 29..35, 5 x 7): log planes = cell lines inset 3 (as A), ground 0, eave 50, top 77 like A (collision h 3);
# door S x 593..609 up to 35 (dark block on the S wall plane map), round window E at y 530 z 28, boarded window S left, ridge log bundle along y,
# two roof vents on the E slope (placed by eye, checked on the overlay)
B = dict(planes=(547, 621, 467, 573), z0=0, doors=[("S", 590, 606, 35)],   # door: drawn dark opening U 1201..1216 (was 593..609)
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
C = dict(planes=(371, 445, 291, 349), z0=32, doors=[("E", 318, 334, 35)],
         posts={"E": [314.5, 337.5]},
         ridge="sticks_ends", sticks_shift=(3.5, -4.25), stick_r=2.6, vents=[(405.5, 338)])
D = dict(planes=(371, 445, 355, 413), z0=32, doors=[("E", 366, 382, 35)],
         shutters=[("S", 397, 408, 22, 38, 6)],   # drawn plank: hinge edge x 397..407 at z 71, lower edge x 391..402 at z ~52 (6 left = propped out 6)
         posts={"E": [362.5, 385.5, 401.5], "S": [378.5, 385.5, 426.5, 433.5]},   # S posts in pairs 7 apart (dark edge of each drawn post + 4.5, as B)
         ridge="sticks_ends", sticks_shift=(3.5, -4.25), stick_r=2.6)   # drawn bindings at screen (+3.5, +6) from the ridge ends x 400 / 416 at the top: kept on the ridge -> x +3.5, z -4.25
for key, h, title in (("c", C, "west pair, back house C"), ("d", D, "west pair, front house D")):
    MM = blx.Mesh("house_592_" + key, mats); MM.density = 1.0
    L.build(MM, h)
    export(MM.finish(), "house_592_" + key, "Massan log house %s, room 592" % title)
