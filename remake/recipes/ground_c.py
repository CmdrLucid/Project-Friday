"""ASSET 5a (style C, 2026-10-25): the DIRT PATH / village ground (user: 'mach erstmal nur den Erdweg').
Original (rooms 592 / 424): packed ochre earth, fine dark grit, light diagonal drag marks, a few small pebbles; on the route the path is a band through
the grass with a soft raised grass lip.  Built here: a subdivided ground mesh with gentle unevenness (worn path slightly lower than the edges, shallow
wheel / foot ruts along the path), material cmat.dirt_mat, small pebbles ('boulder').  The grass around it is a PLACEHOLDER (asset 5b).
Run: R_FIGURE=~/.landstalker_remake/figures/nigel_a4.png R_CLOSE=1 python3 remake/tools/build_asset.py ground_c"""
import bpy, bmesh, sys, os, math, random, mathutils
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat, massan_a as H
out = os.environ.get("R_OUT", "/tmp/ground_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
rnd = random.Random(41); G = H.G
cx, cy = H.CX, H.CY
W = 32.0                                                                        # path width = 2 map cells (like route 424)
def path_d(x, y):
    """distance from the path centre line: an L (east-west, then turning north), game coordinates."""
    d1 = abs(y - (cy + 10)) if x < cx + 20 else 1e9
    d2 = abs(x - (cx + 20)) if y < cy + 10 + W / 2 else 1e9
    corner = math.hypot(x - (cx + 20), y - (cy + 10)) if (x >= cx + 20 and y >= cy + 10) else 1e9
    return min(d1, d2, corner)
S = 120; N = 300
bm = bmesh.new(); uv = None
verts = {}
for i in range(N + 1):
    for j in range(N + 1):
        x = cx - S + 2 * S * i / N; y = cy - S + 2 * S * j / N; d = path_d(x, y)
        z = 0.0
        if d < W / 2:                                                           # worn path: a little lower, two shallow ruts
            t = d / (W / 2); z = -0.8 * (1 - t * t) - 0.35 * math.exp(-((d - 7) / 1.6) ** 2)
            z += 0.25 * math.sin(x * 0.7 + y * 0.3) * math.sin(y * 0.9)
        else:                                                                   # placeholder grass: a soft lip at the path edge
            z = 0.9 * math.exp(-((d - W / 2 - 1.5) / 2.0) ** 2) + 0.4
        verts[(i, j)] = bm.verts.new(G(x, y, z))
dirt = cmat.dirt_mat(mask="mask", other=((62, 112, 28), (112, 152, 44)))
faces = []
for i in range(N):
    for j in range(N):
        faces.append(bm.faces.new([verts[(i, j)], verts[(i + 1, j)], verts[(i + 1, j + 1)], verts[(i, j + 1)]]))
cl = bm.loops.layers.color.new("mask")
for f in faces:                                                                 # soft, ragged edge between path and grass (1 = dirt)
    for l in f.loops:
        x, y = l.vert.co.x, -l.vert.co.y
        edge = W / 2 + (math.sin(x * 0.35) + math.sin(y * 0.5 + 1)) * 0.9 + math.sin(x * 1.3 + y * 0.7) * 0.5
        t = min(1.0, max(0.0, (edge - path_d(x, y)) / 2.5 + 0.5)); l[cl] = (t, t, t, 1.0)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("ground"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
me.materials.append(dirt)
ob = bpy.data.objects.new("ground", me); bpy.context.scene.collection.objects.link(ob)
bp = bmesh.new()                                                                # pebbles on the path
for k in range(14):
    for _ in range(50):
        x = cx - S + 10 + rnd.random() * (2 * S - 20); y = cy - S + 10 + rnd.random() * (2 * S - 20)
        if path_d(x, y) < W / 2 - 3: break
    r = 0.8 + rnd.random() * 1.0; res = bmesh.ops.create_icosphere(bp, subdivisions=2, radius=r)
    for v in res["verts"]: v.co.z *= 0.6
    bmesh.ops.translate(bp, vec=G(x, y, -0.3), verts=res["verts"])
pm = bpy.data.meshes.new("pebbles"); bp.to_mesh(pm); bp.free()
for p in pm.polygons: p.use_smooth = True
pm.materials.append(cmat.get("boulder")); bpy.context.scene.collection.objects.link(bpy.data.objects.new("pebbles", pm))
figs = []
fig = os.path.expanduser(os.environ.get("R_FIGURE", ""))
if fig and os.path.exists(fig): figs.append(H.add_figure(fig, (cx - 20, cy + 10, -0.6)))
H.render_set(out, px=2.0, dof=True, modern=True, figures=figs, quarter=True, tz=0, fh=170)
if os.environ.get("R_CLOSE"):
    sc = bpy.context.scene; co = sc.camera; co.data.type = "ORTHO"; co.data.ortho_scale = 70; co.data.dof.use_dof = False
    for f in figs: f.hide_render = True
    blx.orbit(co, G(cx - 30, cy + 10, 0), 0, 30); sc.render.resolution_x, sc.render.resolution_y = 700, 600
    sc.render.filepath = os.path.join(out, "close.png"); bpy.ops.render.render(write_still=True)
print("ground_c done ->", out)
