"""MASSAN HOUSE A, VARIANT C (2026-10-25, 'modern remake' study 3 of 3): smooth 'toy diorama' look (like the 2019 Link's Awakening remake):
the same modelled house as variant A (lib/massan_a.py: build), but smooth round logs, soft painted materials (procedural, no pixels), a modelled
skull on a board, warm sun, ambient occlusion, soft shadows and a tilt-shift depth of field on the low shot.  Colours from the original's palette.
Run: python3 remake/tools/build_asset.py massan_house_vc"""
import bpy, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, massan_a as H
out = os.environ.get("R_OUT", "/tmp/massan_house_vc"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
def srgb(c): return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)
def pmat(name, c1, c2, scale=0.15, detail=4.0, bump=0.3, stretch=(1, 1, 1), rough=0.75, streaks=0.0):
    """soft painted material: two colours mixed by noise in object space (stretch > 1 = longer blotches along that axis), light bump; streaks = straw strands along z."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale / stretch[0], scale / stretch[1], scale / stretch[2])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Detail"].default_value = detail
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[0].color = srgb(c1); ramp.color_ramp.elements[1].color = srgb(c2)
    L(tc.outputs["Object"], mp.inputs["Vector"]); L(mp.outputs["Vector"], nz.inputs["Vector"]); L(nz.outputs["Fac"], ramp.inputs["Fac"]); L(ramp.outputs["Color"], b.inputs["Base Color"])
    bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = bump
    if streaks:
        wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"; wv.inputs["Scale"].default_value = streaks; wv.inputs["Distortion"].default_value = 6.0
        mp2 = nt.nodes.new("ShaderNodeMapping"); mp2.inputs["Rotation"].default_value = (0, math.radians(90), 0); L(tc.outputs["Object"], mp2.inputs["Vector"]); L(mp2.outputs["Vector"], wv.inputs["Vector"])
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MULTIPLY"; L(wv.outputs["Fac"], mx.inputs[0]); L(nz.outputs["Fac"], mx.inputs[1]); L(mx.outputs[0], bm.inputs["Height"])
    else: L(nz.outputs["Fac"], bm.inputs["Height"])
    L(bm.outputs["Normal"], b.inputs["Normal"]); L(b.outputs["BSDF"], o.inputs["Surface"])
    return m
mats = [pmat("bark", (40, 84, 20), (104, 134, 40), scale=0.25, stretch=(5, 1, 1), bump=0.5),
        pmat("post", (150, 92, 44), (196, 130, 70), scale=0.2, stretch=(1, 1, 5), bump=0.2),
        pmat("endgrain", (170, 120, 70), (214, 168, 110), scale=0.4, bump=0.1),
        pmat("dark", (10, 12, 8), (24, 26, 16), rough=1.0), pmat("hole", (8, 14, 10), (20, 28, 20), rough=1.0),
        pmat("thatch", (176, 126, 30), (240, 200, 90), scale=0.25, stretch=(1, 1, 4), bump=1.0, rough=0.9, streaks=3.0),
        pmat("under", (110, 80, 24), (150, 112, 40), rough=1.0),
        pmat("bone", (226, 220, 200), (246, 242, 230), scale=0.5, bump=0.1, rough=0.5),
        pmat("plank", (92, 58, 28), (128, 84, 44), scale=0.3, stretch=(1, 1, 6), bump=0.4, rough=0.85)]
M = blx.Mesh("massan_house_vc", mats); M.density = 1.0
H.build(M, nseg=20, den=1.0, roof_jitter=0.5, hx=H.HX + 4.5, lip=4.5, door="planks", door_top=29.0)
# the sign: a small plank board with a modelled skull
ya = (H.DOOR["a0"] + H.DOOR["a1"]) / 2; zc = 37.0                                          # centred over the door, above the lintel
M.box("post", H.X1 + 0.4, H.X1 + 1.6, -(ya + 5.5), -(ya - 5.5), zc - 4.5, zc + 4.5)
ob = M.finish()
for p in ob.data.polygons: p.use_smooth = True
import bmesh, mathutils
def blob(name, mat, centre, scale):
    me = bpy.data.meshes.new(name); b = bmesh.new(); bmesh.ops.create_uvsphere(b, u_segments=24, v_segments=14, radius=1.0)
    bmesh.ops.scale(b, vec=scale, verts=b.verts); bmesh.ops.translate(b, vec=centre, verts=b.verts); b.to_mesh(me); b.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o
bone = bpy.data.materials["bone"]; drk = bpy.data.materials["dark"]
sx = H.X1 + 3.0
blob("skull", bone, H.G(sx, ya, zc + 0.8), (2.4, 3.4, 3.3)); blob("jaw", bone, H.G(sx + 0.5, ya, zc - 2.4), (1.9, 2.3, 1.4))
for dy in (-1.3, 1.3): blob("eye", drk, H.G(sx + 1.9, ya + dy, zc + 0.6), (0.7, 0.9, 1.0))
blob("nose", drk, H.G(sx + 2.1, ya, zc - 1.0), (0.4, 0.4, 0.6))
# ground: soft grass / dirt
gm = pmat("ground", (120, 96, 52), (88, 116, 44), scale=0.02, detail=6.0, bump=0.1, rough=1.0)
gme = bpy.data.meshes.new("ground"); b = bmesh.new(); s = 260
b.faces.new([b.verts.new(H.G(H.CX + a, H.CY + c, 0)) for a, c in ((-s, s), (s, s), (s, -s), (-s, -s))]); b.to_mesh(gme); b.free(); gme.materials.append(gm)
bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", gme))
bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "massan_house_vc.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
sc = bpy.context.scene
H.render_set(out, px=float(os.environ.get("R_PX", "2")), dof=True, modern=True)
print("massan_house_vc done ->", out)
