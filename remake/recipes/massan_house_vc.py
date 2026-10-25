"""MASSAN HOUSE A, VARIANT C (2026-10-25, 'modern remake' study 3 of 3): smooth 'toy diorama' look (like the 2019 Link's Awakening remake):
the same modelled house as variant A (lib/massan_a.py: build), but smooth round logs, soft painted materials (procedural, no pixels), a modelled
skull on a board, warm sun, ambient occlusion, soft shadows and a tilt-shift depth of field on the low shot.  Colours from the original's palette.
Run: python3 remake/tools/build_asset.py massan_house_vc"""
import bpy, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, massan_a as H
out = os.environ.get("R_OUT", "/tmp/massan_house_vc"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
import cmat
mats = [cmat.get(n) for n in ("bark", "post", "endgrain", "dark", "hole", "thatch", "under", "bone", "plank")]
M = blx.Mesh("massan_house_vc", mats); M.density = 1.0
# 1:1 the original (user 2026-10-25: 'mach es mal 1:1 wie im Original'): the picture's heights (door 35 > Nigel's 31), only a little more eave
H.build(M, nseg=20, den=1.0, roof_jitter=0.5, hx=H.HX + 1.5, lip=3.5, door="planks")
# the sign: a small plank board with a modelled skull
ya = (H.DOOR["a0"] + H.DOOR["a1"]) / 2; zc = 42.0                                          # centred over the door, above the lintel (like the original)
M.box("post", H.X1 + 0.4, H.X1 + 1.6, -(ya + 5.0), -(ya - 5.0), zc - 4.0, zc + 4.0)
ob = M.finish()
for p in ob.data.polygons: p.use_smooth = True
import bmesh, mathutils
def blob(name, mat, centre, scale):
    me = bpy.data.meshes.new(name); b = bmesh.new(); bmesh.ops.create_uvsphere(b, u_segments=24, v_segments=14, radius=1.0)
    bmesh.ops.scale(b, vec=scale, verts=b.verts); bmesh.ops.translate(b, vec=centre, verts=b.verts); b.to_mesh(me); b.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o
bone = bpy.data.materials["bone"]; drk = bpy.data.materials["dark"]
sx = H.X1 + 3.4
blob("skull", bone, H.G(sx, ya, zc + 0.8), (2.4, 3.4, 3.3)); blob("jaw", bone, H.G(sx + 0.5, ya, zc - 2.4), (1.9, 2.3, 1.4))
for dy in (-1.3, 1.3): blob("eye", drk, H.G(sx + 1.9, ya + dy, zc + 0.6), (0.7, 0.9, 1.0))
blob("nose", drk, H.G(sx + 2.1, ya, zc - 1.0), (0.4, 0.4, 0.6))
# ground: soft grass / dirt
gm = cmat.pmat("ground", (120, 96, 52), (88, 116, 44), scale=0.02, detail=6.0, bump=0.1, rough=1.0)
gme = bpy.data.meshes.new("ground"); b = bmesh.new(); s = 260
b.faces.new([b.verts.new(H.G(H.CX + a, H.CY + c, 0)) for a, c in ((-s, s), (s, s), (s, -s), (-s, -s))]); b.to_mesh(gme); b.free(); gme.materials.append(gm)
bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", gme))
bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "massan_house_vc.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
sc = bpy.context.scene
figs = []                                                                   # R_FIGURE = a rom_sprite.py cut-out (local), standing in front of the door
fig = os.path.expanduser(os.environ.get("R_FIGURE", ""))
if fig and os.path.exists(fig): figs.append(H.add_figure(fig, (H.X1 + 18, H.DOOR["a1"] + 4, 0)))
H.render_set(out, px=float(os.environ.get("R_PX", "2")), dof=True, modern=True, figures=figs, quarter=True) if not os.environ.get("R_ALIGN") else \
    H.render_set(out, px=2.0, dof=False, modern=True, figures=figs, tz=44, fh=216)       # R_ALIGN=1: game view exactly on the window of rom_picture.py (overlay test)
print("massan_house_vc done ->", out)
