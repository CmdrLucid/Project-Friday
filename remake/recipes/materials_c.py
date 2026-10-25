"""STYLE C material library preview (lib/cmat.py LIB): one rounded block per material (ground materials as flat slabs), each rendered on its own from the
game camera with the C light -> ~/.landstalker_remake/assets/materials_c/<name>.png; the labelled sheet: ~/hdvenv/bin/python remake/tools/sheet.py materials_c.
Run: python3 remake/tools/build_asset.py materials_c"""
import bpy, bmesh, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat
out = os.environ.get("R_OUT", "/tmp/materials_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
FLAT = {"grass", "dirt", "sand", "water", "cobble"}
SP = 300.0
def block(name, cx, flat):
    me = bpy.data.meshes.new(name); b = bmesh.new(); bmesh.ops.create_cube(b, size=1.0)
    bmesh.ops.scale(b, vec=(44, 44, 8 if flat else 40), verts=b.verts); bmesh.ops.translate(b, vec=(cx, 0, 4 if flat else 20), verts=b.verts)
    bmesh.ops.bevel(b, geom=b.edges[:], offset=3.0 if flat else 6.0, segments=4, profile=0.5, affect="EDGES"); b.to_mesh(me); b.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(cmat.get(name)); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o
names = list(cmat.LIB)
for i, n in enumerate(names): block(n, i * SP, n in FLAT)
g = bpy.data.meshes.new("floor"); b = bmesh.new(); s = 200
b.faces.new([b.verts.new(p) for p in ((-s, -s, 0), (len(names) * SP + s, -s, 0), (len(names) * SP + s, s, 0), (-s, s, 0))]); b.to_mesh(g); b.free()
g.materials.append(cmat.pmat("floor", (96, 90, 80), (110, 104, 92), scale=0.01, bump=0.0, rough=1.0)); bpy.context.scene.collection.objects.link(bpy.data.objects.new("floor", g))
sc, co = blx.game_view(os.path.join(out, "x.png"), px_per_unit=4.0, size=(320, 300), target=(0, 0, 16), squash=False)
cmat.modern_look(sc)
for i, n in enumerate(names):
    blx.orbit(co, (i * SP, 0, 16), 0, 30); sc.render.filepath = os.path.join(out, n + ".png"); bpy.ops.render.render(write_still=True)
open(os.path.join(out, "names.txt"), "w").write("\n".join("%s\t%s" % (n, cmat.LIB[n][0]) for n in names))
print("materials_c done ->", out)
