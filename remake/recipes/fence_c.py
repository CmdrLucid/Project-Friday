"""ASSET 3 (style C, 2026-10-25): the PALISADE fence of Massan (room 592, south west edge and the village entrance).
Original: thin sharpened stakes close together (about every 4 px), dark tips, slightly uneven heights and leaning; at an opening a thicker end post with
a dark flat top and a few stones at its foot.  Built here: palisade(p0, p1) = stakes every ~3.3 units along the line (radius ~1.3, ~22 high + a 3.5 unit
point, random lean), a thin binding rail on the inner side; end_post(); stones.  Scene: an L with a corner and a gate opening, Nigel in the opening.
Run: R_FIGURE=~/.landstalker_remake/figures/nigel_a4.png python3 remake/tools/build_asset.py fence_c   (R_CLOSE=1 adds a close-up)"""
import bpy, bmesh, sys, os, math, random, mathutils
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat, kit_c, massan_a as H
out = os.environ.get("R_OUT", "/tmp/fence_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
rnd = random.Random(21); G = H.G
cx, cy = H.CX, H.CY
bm = bmesh.new()
gate0, gate1 = cx - 2, cx + 22                                                   # the opening along the south fence (24 units = 1.5 cells)
kit_c.palisade(bm, (cx - 56, cy + 24), (gate0 - 3, cy + 24), (0, -1), rnd=rnd); kit_c.end_post(bm, gate0, cy + 24)
kit_c.end_post(bm, gate1, cy + 24); kit_c.palisade(bm, (gate1 + 3, cy + 24), (cx + 56, cy + 24), (0, -1), rnd=rnd)
kit_c.palisade(bm, (cx - 56, cy + 21), (cx - 56, cy - 40), (1, 0), rnd=rnd)                     # the corner, running north
me = bpy.data.meshes.new("palisade"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
[me.materials.append(m) for m in kit_c.fence_mats()]; ob = bpy.data.objects.new("palisade", me); bpy.context.scene.collection.objects.link(ob)
kit_c.stones(gate0, cy + 24, rnd=rnd); kit_c.stones(gate1, cy + 24, 2, rnd=rnd)
g = bpy.data.meshes.new("ground"); b = bmesh.new(); s = 260
b.faces.new([b.verts.new(G(cx + a, cy + c, 0)) for a, c in ((-s, s), (s, s), (s, -s), (-s, -s))]); b.to_mesh(g); b.free()
g.materials.append(cmat.pmat("ground", (120, 96, 52), (88, 116, 44), scale=0.02, detail=6.0, bump=0.1, rough=1.0)); bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", g))
bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "fence_c.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
figs = []
fig = os.path.expanduser(os.environ.get("R_FIGURE", ""))
if fig and os.path.exists(fig): figs.append(H.add_figure(fig, ((gate0 + gate1) / 2, cy + 24, 0)))
H.render_set(out, px=2.0, dof=True, modern=True, figures=figs, quarter=True, tz=12, fh=170)
if os.environ.get("R_CLOSE"):
    sc = bpy.context.scene; co = sc.camera; co.data.type = "ORTHO"; co.data.ortho_scale = 60; co.data.dof.use_dof = False
    for f in figs: f.hide_render = True
    blx.orbit(co, G(gate0 - 6, cy + 24, 12), 0, 30); sc.render.resolution_x, sc.render.resolution_y = 700, 600
    sc.render.filepath = os.path.join(out, "close.png"); bpy.ops.render.render(write_still=True)
print("fence_c done ->", out)
