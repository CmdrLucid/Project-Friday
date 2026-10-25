"""MASSAN HOUSE A, VARIANT A (2026-10-25, 'modern remake' study 1 of 3): a MODELLED 3D house (round logs, posts, thick bulging thatch, real door /
window openings) with PIXEL TEXTURES CUT FROM THE ORIGINAL as tileable swatches (one log of the south wall, the thatch of the south / east roof face,
mirror-repeated), not projected: so every side looks right from every angle.  Stepped light + 1 px outlines (blx.PIXEL), like HD-2D games.
Needs the picture of rom_picture.py (see lib/massan_a.py).  Run: python3 remake/tools/build_asset.py massan_house_va"""
import bpy, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, massan_a as H
out = os.environ.get("R_OUT", "/tmp/massan_house_va"); os.makedirs(out, exist_ok=True)
pic_dir = os.path.expanduser(os.environ.get("R_PIC", "~/.landstalker_remake/rooms/592_houseA"))
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = os.environ.get("R_DBG", "") != "1"; DEN = 2.0
pic = H.Picture(pic_dir); full = H.Picture(pic_dir, "full.png")
BROWN = [(40, 32, 14), (72, 72, 36), (110, 86, 30), (144, 108, 36), (182, 126, 54), (216, 144, 72), (232, 176, 110)]
def hsh(*k):
    v = 2166136261
    for x in k: v = ((v ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    v ^= v >> 13; v = (v * 1274126177) & 0xFFFFFFFF; return ((v >> 8) & 0xFFFF) / 65536.0
def post(x, y):          # posts: the original's light orange wood with a white stripe on the lit side
    n = hsh(x // 2, y, 5); s = math.cos(y / 36.0 * 2 * math.pi)
    if 4 <= y <= 6: return (232, 228, 210) if n > 0.2 else BROWN[6]
    if s > -0.2: return BROWN[5] if n > 0.2 else BROWN[6]
    return BROWN[4] if n > 0.3 else BROWN[3]
def endgrain(x, y):
    r = math.hypot(x - 7.5, y - 7.5)
    if r > 6.6: return (0, 72, 36) if hsh(x, y, 3) > 0.3 else (30, 96, 18)          # mossy rim like the original's log ends
    if r > 5.4: return BROWN[2]
    return BROWN[4] if int(r) % 2 == 0 else BROWN[3]
def dark(x, y): return (0, 0, 0) if hsh(x, y, 8) > 0.15 else (0, 30, 14)
def hole(x, y): return (0, 20, 10) if hsh(x, y, 9) > 0.2 else (0, 40, 20)
def under(x, y): return (108, 80, 0) if hsh(x // 2, y, 14) > 0.3 else (72, 56, 0)
bf, bw, bh = H.bark_texture(pic, 2); tf, tw, th = H.thatch_texture(pic, 2); gf, gw, gh = H.ground_texture(full, 64)
# sign: the picture itself, mapped by projection onto the flat board (exact, it is a flat thing hanging on the wall)
sign_img = bpy.data.images.load(os.path.join(pic_dir, "layerA.png")); sign_img.colorspace_settings.name = "sRGB"
def sign_mat():
    m = bpy.data.materials.new("sign"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    o = nt.nodes.new("ShaderNodeOutputMaterial"); t = nt.nodes.new("ShaderNodeTexImage"); t.image = sign_img; t.interpolation = "Closest"
    em = nt.nodes.new("ShaderNodeEmission"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    L(t.outputs["Color"], em.inputs["Color"]); L(t.outputs["Alpha"], mx.inputs["Fac"]); L(tr.outputs["BSDF"], mx.inputs[1]); L(em.outputs["Emission"], mx.inputs[2]); L(mx.outputs["Shader"], o.inputs["Surface"])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "DITHERED"
    return m
mats = [blx.material("bark", blx.px_image("bark", bf, bw, bh)), blx.material("post", blx.px_image("post", post, 96, 36)),
        blx.material("endgrain", blx.px_image("endgrain", endgrain, 16, 16)), blx.material("dark", blx.px_image("dark", dark, 16, 16)),
        blx.material("hole", blx.px_image("hole", hole, 16, 16)), blx.material("thatch", blx.px_image("thatch", tf, tw, th)),
        blx.material("under", blx.px_image("under", under, 32, 32)), sign_mat()]
M = blx.Mesh("massan_house_va", mats); M.density = DEN
M.size["sign"] = (1, 1)
def sign_uv(x, y, z):
    u, v = pic.uv(x, y, z); return (u / pic.w, 1 - v / pic.h)
H.build(M, nseg=10, den=DEN, sign_uv=sign_uv)
ob = M.finish()
bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "massan_house_va.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
# ground
import bmesh
gm = blx.material("dirt", blx.px_image("dirt", gf, gw, gh)); me = bpy.data.meshes.new("ground"); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UV"); s = 200
f = bm.faces.new([bm.verts.new(H.G(H.CX + a, H.CY + b, 0)) for a, b in ((-s, s), (s, s), (s, -s), (-s, -s))])
for l in f.loops: l[uvl].uv = (l.vert.co.x * DEN / 64, l.vert.co.y * DEN / 64)
bm.to_mesh(me); bm.free(); me.materials.append(gm); bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", me))
H.render_set(out, px=float(os.environ.get("R_PX", "2")))
print("massan_house_va done ->", out)
