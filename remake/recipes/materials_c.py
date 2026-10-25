"""STYLE C material library preview (lib/cmat.py LIB): one rounded block per material (ground materials as flat slabs), name on a plate in front,
seen with the game projection and the C light.  Run: python3 remake/tools/build_asset.py materials_c  -> ~/.landstalker_remake/assets/materials_c/game.png"""
import bpy, bmesh, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat
out = os.environ.get("R_OUT", "/tmp/materials_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
FLAT = {"grass", "dirt", "sand", "water", "cobble"}
names = list(cmat.LIB); COLS = 5; SX, SY = 100.0, 80.0           # grid in SCREEN units of the game projection (x - y across, (x + y) / 2 down)
def world(sx, sy): return (sy + sx / 2, -(sy - sx / 2))              # screen -> Blender (x, y) on the ground
def block(name, cx, cy, flat):
    me = bpy.data.meshes.new(name); b = bmesh.new(); bmesh.ops.create_cube(b, size=1.0)
    bmesh.ops.scale(b, vec=(44, 44, 8 if flat else 40), verts=b.verts); bmesh.ops.translate(b, vec=(cx, cy, 4 if flat else 20), verts=b.verts)
    bmesh.ops.bevel(b, geom=b.edges[:], offset=3.0 if flat else 6.0, segments=4, profile=0.5, affect="EDGES"); b.to_mesh(me); b.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(cmat.get(name)); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o
label_mat = cmat.pmat("label", (30, 28, 26), (40, 36, 32), rough=1.0)
for i, n in enumerate(names):
    cx, cy = world((i % COLS) * SX, (i // COLS) * SY)
    block(n, cx, cy, n in FLAT)
    cu = bpy.data.curves.new("t_" + n, "FONT"); cu.body = n; cu.size = 9.0; cu.align_x = "CENTER"; cu.extrude = 0.4
    t = bpy.data.objects.new("t_" + n, cu); t.location = (cx + 27, cy - 27, 0.3); t.rotation_euler = (0, 0, math.radians(45))
    t.data.materials.append(label_mat); bpy.context.scene.collection.objects.link(t)
g = bpy.data.meshes.new("ground"); b = bmesh.new(); s = 600
b.faces.new([b.verts.new(p) for p in ((-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0))]); b.to_mesh(g); b.free()
g.materials.append(cmat.pmat("floor", (96, 90, 80), (110, 104, 92), scale=0.01, bump=0.0, rough=1.0)); bpy.context.scene.collection.objects.link(bpy.data.objects.new("floor", g))
rows = (len(names) + COLS - 1) // COLS; tx, ty = world((COLS - 1) * SX / 2, (rows - 1) * SY / 2 + 6); T = (tx, ty, 10)
sc, co = blx.game_view(os.path.join(out, "game.png"), px_per_unit=2.8, size=(1500, 1050), target=T, squash=False)
cmat.modern_look(sc)
bpy.ops.render.render(write_still=True)
print("materials_c done ->", out)
