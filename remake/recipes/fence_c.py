"""ASSET 3 (style C, 2026-10-25): the PALISADE fence of Massan (room 592, south west edge and the village entrance).
Original: thin sharpened stakes close together (about every 4 px), dark tips, slightly uneven heights and leaning; at an opening a thicker end post with
a dark flat top and a few stones at its foot.  Built here: palisade(p0, p1) = stakes every ~3.3 units along the line (radius ~1.3, ~22 high + a 3.5 unit
point, random lean), a thin binding rail on the inner side; end_post(); stones.  Scene: an L with a corner and a gate opening, Nigel in the opening.
Run: R_FIGURE=~/.landstalker_remake/figures/nigel_a4.png python3 remake/tools/build_asset.py fence_c   (R_CLOSE=1 adds a close-up)"""
import bpy, bmesh, sys, os, math, random, mathutils
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat, massan_a as H
out = os.environ.get("R_OUT", "/tmp/fence_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
rnd = random.Random(21); G = H.G
WOOD = cmat.pmat("stake", (142, 88, 44), (196, 136, 78), scale=0.3, stretch=(1, 1, 6), bump=0.4, rough=0.85)
TIP = cmat.pmat("stake_tip", (52, 38, 20), (88, 64, 34), scale=0.4, bump=0.2, rough=0.9)

def cyl(bm, a, b, r1, r2, seg=10, mat_i=0):
    A = mathutils.Vector(a); B = mathutils.Vector(b); d = B - A
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=d.length)
    vs = res["verts"]; bmesh.ops.translate(bm, vec=(0, 0, d.length / 2), verts=vs)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=d.normalized().to_track_quat("Z", "Y").to_matrix(), verts=vs); bmesh.ops.translate(bm, vec=A, verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.material_index = mat_i

def stake(bm, x, y, h, r, lean):
    """one sharpened stake: shaft (wood) + point (dark tip), leaning by lean = (dx, dy) per unit of height."""
    top = (x + lean[0] * h, y + lean[1] * h, h); tip = (x + lean[0] * (h + 3.5), y + lean[1] * (h + 3.5), h + 3.5)
    cyl(bm, G(x, y, -1.0), G(*top), r, r * 0.92, 10, 0)
    cyl(bm, G(*top), G(*tip), r * 0.92, 0.12, 10, 1)

def palisade(bm, p0, p1, inner, spacing=3.3):
    """stakes from p0 to p1 (game x, y); inner = unit vector to the inside (for the binding rail)."""
    L = math.dist(p0, p1); n = max(2, int(L / spacing)); ux, uy = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L
    for k in range(n + 1):
        t = k / n; x = p0[0] + (p1[0] - p0[0]) * t + (rnd.random() - 0.5) * 0.5; y = p0[1] + (p1[1] - p0[1]) * t + (rnd.random() - 0.5) * 0.5
        h = 21.0 + rnd.random() * 3.0; r = 1.2 + rnd.random() * 0.3
        lean = ((rnd.random() - 0.5) * 0.06, (rnd.random() - 0.5) * 0.06)
        stake(bm, x, y, h, r, lean)
    for z in (6.0, 15.0):                                                        # binding rail on the inner side
        a = (p0[0] + inner[0] * 1.6, p0[1] + inner[1] * 1.6, z); b = (p1[0] + inner[0] * 1.6, p1[1] + inner[1] * 1.6, z)
        cyl(bm, G(*a), G(*b), 0.6, 0.6, 8, 0)

def end_post(bm, x, y):
    cyl(bm, G(x, y, -1.0), G(x, y, 25.0), 2.6, 2.4, 14, 0)
    cyl(bm, G(x, y, 25.0), G(x, y, 26.2), 2.45, 2.2, 14, 1)                      # dark flat top

def stones(x, y, n=3):
    bm = bmesh.new()
    for k in range(n):
        res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0); r = 1.6 + rnd.random() * 1.2
        rr = random.Random(k + int(x))
        for v in res["verts"]: v.co = mathutils.Vector((v.co.x * r * (1 + (rr.random() - 0.5) * 0.3), v.co.y * r * (1 + (rr.random() - 0.5) * 0.3), v.co.z * r * 0.65))
        bmesh.ops.translate(bm, vec=G(x + (rnd.random() - 0.5) * 6, y + 3 + rnd.random() * 3, r * 0.3), verts=res["verts"])
    me = bpy.data.meshes.new("stones"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(cmat.get("boulder")); o = bpy.data.objects.new("stones", me); bpy.context.scene.collection.objects.link(o)

cx, cy = H.CX, H.CY
bm = bmesh.new()
gate0, gate1 = cx - 2, cx + 22                                                   # the opening along the south fence (24 units = 1.5 cells)
palisade(bm, (cx - 56, cy + 24), (gate0 - 3, cy + 24), (0, -1)); end_post(bm, gate0, cy + 24)
end_post(bm, gate1, cy + 24); palisade(bm, (gate1 + 3, cy + 24), (cx + 56, cy + 24), (0, -1))
palisade(bm, (cx - 56, cy + 21), (cx - 56, cy - 40), (1, 0))                     # the corner, running north
me = bpy.data.meshes.new("palisade"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
me.materials.append(WOOD); me.materials.append(TIP); ob = bpy.data.objects.new("palisade", me); bpy.context.scene.collection.objects.link(ob)
stones(gate0, cy + 24); stones(gate1, cy + 24, 2)
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
