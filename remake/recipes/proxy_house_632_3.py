"""LIGHT SHAPE (near-final, as drawn): Mercator TOWN HOUSE 3, room 632 = the one-off building in the upper left (cells 15..20 x 29..41) that
proxy_houses_632.py left for its own recipe: two two-storey wings, a one-storey front annex with a walkable ROOF TERRACE behind a stone parapet,
an upper door onto the terrace, a small one-storey wing with a pointed hip roof (shop sign + door).
Measured 2026-11-24 (remake/tools/fit_house.py scene ~/Project-Friday-Test/lktest/lf4/h3_scene.json + find_openings.py, collision of room 632):
  right wing x 240..320 y 464..544 and left wing x 240..304 y 544..672: collision 112 = eave 112, fit: top 134.5, inset 26 (= house 4, TWO);
  annex x 304..336 y 544..624: walls 16..64, terrace floor walkable 64, parapet cells 80 on the +x side and the back / front rows; the drawn parapet
  top band is ~12 px high = 12 units thick (the collision takes whole cells);
  small wing x 304..336 y 624..672: collision 64 = eave 64, fit: hip to a point at 84 (inset capped by the 32 wide wing);
  openings (standard tiles of town_house.py): right +x: windows slots 480 / 512 storey 1, door 496 storey 0; left +y: windows 256 storeys 0 / 1;
  left +x: door 576 storey 1 (the dark doorway onto the terrace = walkable cell (18,36) at 64 -> recessed a whole cell, 16), window 640 storey 1;
  annex +x: windows 544 / 576 / 608; small wing +x: door 640 (the framed shop sign is drawn flat).
Run: python3 remake/tools/build_asset.py proxy_house_632_3  ->  landstalker/data/proxies/house_632_3.obj"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import bpy, bmesh
import proxy, town_house as th
bpy.ops.wm.read_factory_settings(use_empty=True)
Z0 = 16; TWO = (112, 134.5, 26)
RIGHT, LEFT, ANNEX, SMALL = (240, 464, 320, 544), (240, 544, 304, 672), (304, 544, 336, 624), (304, 624, 336, 672)
def hip(name, wing, ze, zt, i):
    v, f = proxy.part_mesh(wing[0], wing[1], wing[2], wing[3], Z0, ze, zt, "hip:%g" % i, None); return th.mk(name, v, f)
h = hip("right", RIGHT, *TWO)
th.boolean(h, hip("left", LEFT, *TWO), "UNION")
th.boolean(h, th.box("annex", ANNEX[0] - 2, ANNEX[1], Z0, ANNEX[2], ANNEX[3], 64), "UNION")          # 2 into the left wing: one closed solid
PT = 12.0   # parapet thickness
for nm, b in (("par_x", (ANNEX[2] - PT, ANNEX[1], 64 - 1, ANNEX[2], ANNEX[3], 80)),
              ("par_back", (ANNEX[0] - 2, ANNEX[1], 64 - 1, ANNEX[2], ANNEX[1] + PT, 80)),
              ("par_front", (ANNEX[0] - 2, ANNEX[3] - PT, 64 - 1, ANNEX[2], ANNEX[3], 80))):
    th.boolean(h, th.box(nm, *b), "UNION")
th.boolean(h, hip("small", SMALL, 64, 84, 15), "UNION")
def opening(wing, wall, s0, st, kind, deep=None):
    fz = Z0 + 48 * st
    if kind == th.WIN:
        th.boolean(h, th.wall_box(wing, wall, s0 + 3, s0 + 16, fz + 22, fz + 38, 1.5, 5, "win"), "DIFFERENCE")
        th.boolean(h, th.wall_box(wing, wall, s0, s0 + 16, fz + 16, fz + 21, 1, 1, "sill"), "UNION")
    else:
        th.boolean(h, th.wall_box(wing, wall, s0 + 4, s0 + 16, fz + 3, fz + 43, deep or 2.5, 5, "door"), "DIFFERENCE")
for args in ((RIGHT, "x", 480, 1, th.WIN), (RIGHT, "x", 512, 1, th.WIN), (RIGHT, "x", 496, 0, th.DOOR),
             (LEFT, "y", 256, 0, th.WIN), (LEFT, "y", 256, 1, th.WIN), (LEFT, "x", 640, 1, th.WIN),
             (ANNEX, "x", 544, 0, th.WIN), (ANNEX, "x", 576, 0, th.WIN), (ANNEX, "x", 608, 0, th.WIN), (SMALL, "x", 640, 0, th.DOOR)):
    opening(*args)
opening(LEFT, "x", 576, 1, th.DOOR, deep=16.0)    # open doorway onto the terrace, one cell deep (walkable cell 18,36)
bm = bmesh.new(); bm.from_mesh(h.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.verts.index_update()
path = os.path.join(th.PROX, "house_632_3.obj")
with open(path, "w") as fo:
    fo.write("# light proxy: Mercator town house 3 (two wings, roof terrace, small wing), room 632 (remake/recipes/proxy_house_632_3.py). GAME coordinates x east, y south, z up.\n")
    for vv in bm.verts: fo.write("v %g %g %g\n" % (round(vv.co.x, 3), round(-vv.co.y, 3), round(vv.co.z, 3)))
    for ff in bm.faces: fo.write("f " + " ".join(str(vv.index + 1) for vv in reversed(ff.verts)) + "\n")
print("proxy_house_632_3: %d vertices, %d triangles -> %s" % (len(bm.verts), len(bm.faces), path))
