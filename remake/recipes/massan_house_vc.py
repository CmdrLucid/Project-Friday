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
import kit_c, bmesh
ob = kit_c.house_a()[0]
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
