"""LIGHT SHAPE (near-final, as drawn): the LOG HUT of room 468 (the shore below the cliff stairs; leftover list 0a496 '468 hut (own type)').
Measured 2026-11-24: it is NOT its own type: the walls are Massan house B's tiles in a greener palette (shutter, door, posts of the S wall, the round
window of the E wall at the same screen offsets; picture match room 592 U 1148 V 474 <-> room 468 U 1228 V 434), only shorter: collision x 35..39
y 27..31 (5 x 5) height 64 on ground 16 = the S five rows of B (x 34..38 y 29..35 height 48 on ground 0) moved (+16, -64, +16) (picture U +80 V -40).
So: B's numbers (remake/recipes/proxy_houses_592.py) moved, the N / W posts at the same distance from the N corner as B's, and the square roof of
the drawing: thatch with ONE crossing of sticks in the middle, no vents (as Gumi Q / Massan A).
Run: python3 remake/tools/build_asset.py proxy_house_468  ->  landstalker/data/proxies/house_468.obj"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
import blx, log_house as L
blx.PIXEL = False
PROX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "data", "proxies")
mats = [blx.flat_material(n, (150, 150, 150)) for n in ("bark", "post", "endgrain", "dark", "hole", "thatch", "under", "plank")]
DX, DY = 16, -64   # B -> hut (z0 0 -> 16)
HUT = dict(planes=(547 + DX, 621 + DX, 435, 573 + DY), z0=16, back_in=3.0, corners="mitre",
           doors=[("S", 590 + DX, 606 + DX, 35)], windows=[("E", 530 + DY, 28)], shutters=[("S", 557 + DX, 569 + DX, 24, 38, 3)],
           posts={"S": [586.5 + DX, 609.5 + DX], "N": [556 + DX, 563 + DX, 605 + DX, 612 + DX],
                  "E": [444, 451, 557 + DY, 564 + DY], "W": [444, 451]},     # N-end pairs 9 / 16 from the N plane 435 (B: 476 / 483 from 467)
           noext=[("W", 1)], ext={("S", 0): 1.5}, ridge="sticks", stick_r=2.6)
M = blx.Mesh("house_468", mats); M.density = 1.0
L.build(M, HUT)
ob = M.finish()
bm = bmesh.new(); bm.from_mesh(ob.data); bm.transform(ob.matrix_world); bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)
bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.verts.index_update()
path = os.path.join(PROX, "house_468.obj")
with open(path, "w") as fo:
    fo.write("# light proxy: log hut of room 468 = Massan house B's S part moved (remake/recipes/proxy_house_468.py). GAME coordinates x east, y south, z up, world units.\n")
    for v in bm.verts: fo.write("v %g %g %g\n" % (round(v.co.x, 2), round(-v.co.y, 2), round(v.co.z, 2)))
    for f in bm.faces: fo.write("f " + " ".join(str(v.index + 1) for v in reversed(f.verts)) + "\n")
print("proxy_house_468: %d vertices, %d triangles -> %s" % (len(bm.verts), len(bm.faces), path))
