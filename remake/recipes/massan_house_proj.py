"""MASSAN HOUSE A by PROJECTION (user 2026-10-24: 'kannst du das Original einfach 1:1 nehmen und als 3D-Modell auch die anderen Seiten bauen?').
The original pixels (plane A of room 592 from the user's own ROM, cut out by remake/tools/rom_picture.py, optionally Scale2x) are projected onto simple 3D
geometry from the original camera: seen from the game's view the model shows exactly the original picture; the HIDDEN sides (north / west walls, north / west
roof faces) take the pixels of the visible sides MIRRORED through the house centre (so the back is an invented mirror image: window / door / sign repeat there).
Needs first:  python3 remake/tools/rom_picture.py ROM 592 936 248 208 216 ~/.landstalker_remake/rooms/592_houseA --scale2x
Run:          R_PIC=~/.landstalker_remake/rooms/592_houseA python3 remake/tools/build_asset.py massan_house_proj
World: the house = height map cells x 6..10, y 15..19 of room 592; block / picture cells are the height map cells + 12 (measured on this picture), so world
x 288..368, y 432..512 (16 units per cell); picture U = wx - wy + 1184, V = (wx + wy) / 2 - z.  Measured on the picture: eave ~ z 50 at the cell edge, thatch top ~ z 77,
ridge sticks up to ~ z 85, walls (outer log surface) ~ 3 units inside the cells.  Light is in the pixels (no scene light: emission + alpha clip)."""
import bpy, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx
out = os.environ.get("R_OUT", "/tmp/massan_house_proj"); os.makedirs(out, exist_ok=True)
pic = os.path.expanduser(os.environ.get("R_PIC", "~/.landstalker_remake/rooms/592_houseA"))
bpy.ops.wm.read_factory_settings(use_empty=True)
U0, V0, PW, PH, K = map(int, open(os.path.join(pic, "window.txt")).read().split())
img = bpy.data.images.load(os.path.join(pic, "layerA.png")); img.colorspace_settings.name = "sRGB"
IW, IH = img.size
def G(x, y, z): return (x, -y, z)

# ---- material: the picture as emission, alpha 0 = cut away ---------------------------------------------------------------------------------------
def pic_material(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    o = nt.nodes.new("ShaderNodeOutputMaterial"); t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; t.interpolation = "Closest"; t.extension = "CLIP"
    em = nt.nodes.new("ShaderNodeEmission"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.5
    L(t.outputs["Color"], em.inputs["Color"]); L(t.outputs["Alpha"], gt.inputs[0]); L(gt.outputs[0], mx.inputs["Fac"])
    L(tr.outputs["BSDF"], mx.inputs[1]); L(em.outputs["Emission"], mx.inputs[2]); L(mx.outputs["Shader"], o.inputs["Surface"])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "DITHERED"
    if hasattr(m, "blend_method"): m.blend_method = "CLIP"
    return m
def flat(name, rgb):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission"); lin = lambda c: (c / 255) / 12.92 if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4     # sRGB -> linear (node colours are linear)
    em.inputs["Color"].default_value = (lin(rgb[0]), lin(rgb[1]), lin(rgb[2]), 1)
    nt.links.new(em.outputs["Emission"], o.inputs["Surface"]); return m
PM = pic_material("picture"); DK = flat("core", (0, 0, 0))
img_px = lambda wx, wy, z: ((wx - wy + 1184 - U0) * K, ((wx + wy) / 2 - z - V0) * K)

# ---- geometry (game coordinates) -------------------------------------------------------------------------------------------------------------------
CX0, CX1, CY0, CY1 = 288.0, 368.0, 432.0, 512.0; CX, CY = (CX0 + CX1) / 2, (CY0 + CY1) / 2
IN = 3.0; x0, x1, y0, y1 = CX0 + IN, CX1 - IN, CY0 + IN, CY1 - IN         # wall planes (outer log surface)
ZE, ZT = 50.0, 77.0                                                        # eave at the cell edge, thatch top
import bmesh
bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UV")
def mirror(p, side):
    """hidden faces take the pixel of the point mirrored through the centre to the visible side (north -> south, west -> east)."""
    x, y, z = p
    if side in ("N", "RN"): y = 2 * CY - y
    if side in ("W", "RW"): x = 2 * CX - x
    return (x, y, z)
def face(pts, side, mat=0):
    f = bm.faces.new([bm.verts.new(G(*p)) for p in pts]); f.material_index = mat
    for l, p in zip(f.loops, pts):
        u, v = img_px(*mirror(p, side)); l[uvl].uv = (u / IW, 1 - v / IH)
    return f
def quad_grid(p00, p10, p11, p01, side, nu=8, nv=6):
    """subdivided quad (keeps the projection exact on bent / mirrored faces and gives Blender enough vertices)."""
    L = lambda a, b, t: tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
    for i in range(nu):
        for j in range(nv):
            a0, a1 = L(p00, p10, i / nu), L(p00, p10, (i + 1) / nu); b0, b1 = L(p01, p11, i / nu), L(p01, p11, (i + 1) / nu)
            face([L(a0, b0, j / nv), L(a1, b1, j / nv), L(a1, b1, (j + 1) / nv), L(a0, b0, (j + 1) / nv)], side)
ZW = ZE + 2
quad_grid((x0, y1, 0), (x1, y1, 0), (x1, y1, ZW), (x0, y1, ZW), "S")                 # south wall (visible)
quad_grid((x1, y1, 0), (x1, y0, 0), (x1, y0, ZW), (x1, y1, ZW), "E")                 # east wall (visible)
quad_grid((x1, y0, 0), (x0, y0, 0), (x0, y0, ZW), (x1, y0, ZW), "N")                 # north (hidden, mirrored)
quad_grid((x0, y0, 0), (x0, y1, 0), (x0, y1, ZW), (x0, y0, ZW), "W")                 # west (hidden, mirrored)
# log ends / posts stick out past the corners in the picture: thin corner fins carry those pixels
for (cx, cy, sx, sy) in ((x0, y1, -1, 1), (x1, y1, 1, 1), (x1, y0, 1, -1), (x0, y0, -1, -1)):
    side_a = "S" if sy > 0 else "N"; side_b = "E" if sx > 0 else "W"
    quad_grid((cx, cy, 0), (cx + sx * IN, cy, 0), (cx + sx * IN, cy, ZW), (cx, cy, ZW), side_a, 1, 6)
    quad_grid((cx, cy, 0), (cx, cy + sy * IN, 0), (cx, cy + sy * IN, ZW), (cx, cy, ZW), side_b, 1, 6)
# hip roof (square -> pyramid): four faces from the eave at the cell edge up to the top, a little bulge
def rz(t): return ZE + (ZT - ZE) * (1 - (1 - t) ** 1.25)
N = 10
corners = [(CX0, CY1), (CX1, CY1), (CX1, CY0), (CX0, CY0)]
for k, side in enumerate(("RS", "RE", "RN", "RW")):
    (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
    for i in range(N):
        t0, t1 = i / N, (i + 1) / N
        P = lambda px, py, t: (px + (CX - px) * t, py + (CY - py) * t, rz(t))
        if i < N - 1:
            for j in range(6):
                s0, s1 = j / 6, (j + 1) / 6
                A0 = (ax + (bx - ax) * s0, ay + (by - ay) * s0); A1 = (ax + (bx - ax) * s1, ay + (by - ay) * s1)
                face([P(A0[0], A0[1], t0), P(A1[0], A1[1], t0), P(A1[0], A1[1], t1), P(A0[0], A0[1], t1)], side)
        else:
            face([P(ax, ay, t0), P(bx, by, t0), (CX, CY, ZT)], side)
# ridge sticks: an upright card through the apex, facing the original camera (diagonal plane), only as wide as the sticks
cw, z0c, z1c = 6.5, ZT - 6, ZT + 9
face([(CX - cw, CY + cw, z0c), (CX + cw, CY - cw, z0c), (CX + cw, CY - cw, z1c), (CX - cw, CY + cw, z1c)], "card")
face([(CX + cw, CY - cw, z0c), (CX - cw, CY + cw, z0c), (CX - cw, CY + cw, z1c), (CX + cw, CY - cw, z1c)], "card")
# dark core inside (the doorway and gaps show black like the original)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
me = bpy.data.meshes.new("massan_house_A_proj"); bm.to_mesh(me); bm.free(); me.materials.append(PM)
ob = bpy.data.objects.new("massan_house_A_proj", me); bpy.context.scene.collection.objects.link(ob)
cm = bpy.data.meshes.new("core"); b2 = bmesh.new()
bmesh.ops.create_cube(b2, size=1.0); bmesh.ops.scale(b2, vec=(x1 - x0 - 2, y1 - y0 - 2, ZW), verts=b2.verts)
bmesh.ops.translate(b2, vec=(CX, -CY, ZW / 2), verts=b2.verts); b2.to_mesh(cm); b2.free(); cm.materials.append(DK)
core = bpy.data.objects.new("core", cm); bpy.context.scene.collection.objects.link(core)

# ---- export + previews ---------------------------------------------------------------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); core.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "massan_house_A_proj.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
gm = flat("ground", (126, 96, 34)); gme = bpy.data.meshes.new("ground"); b3 = bmesh.new(); s = 160
b3.faces.new([b3.verts.new(G(CX + a, CY + b, -0.2)) for a, b in ((-s, s), (s, s), (s, -s), (-s, -s))]); b3.to_mesh(gme); b3.free(); gme.materials.append(gm)
bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", gme))
blx.PIXEL = True
px = float(os.environ.get("R_PX", str(K)))
T = G(CX, CY, 40)
sc, co = blx.game_view(os.path.join(out, "game.png"), px_per_unit=px, size=(int(208 * px), int(190 * px)), target=T, sun_energy=0.0, sky=0.0)
sc.render.use_freestyle = False
bpy.ops.render.render(write_still=True)
zs = math.sqrt(2 / 3)
for i, yaw in enumerate((-35, 35, 135, 180)):
    blx.orbit(co, (T[0], T[1], T[2] * zs), yaw, 30); sc.render.filepath = os.path.join(out, "turn_%d.png" % i); bpy.ops.render.render(write_still=True)
print("massan_house_proj done ->", out)
