"""ASSET 5c (style C, 2026-10-25): WATER - the river of route 424 (and the sea of Massan 592 uses the same material).
Original: deep teal-blue water with short light ripple strokes running with the current, in a channel with steep ochre earth banks (roots, darker
streaks) and the grass lip on top.  Built here: terrain grid with a channel (bank walls ~10 high, slightly jagged), grass on top (lib/cground.py),
earth banks (cmat.dirt_mat via the 'mask' attribute), water surface 4 below the bank top (cmat.water_mat, flow along game x), a little foam where
water meets the bank.  Run: R_FIGURE=~/.landstalker_remake/figures/nigel_a4.png R_CLOSE=1 python3 remake/tools/build_asset.py water_c"""
import bpy, bmesh, sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat, cground, massan_a as H
out = os.environ.get("R_OUT", "/tmp/water_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
G = H.G; cx, cy = H.CX, H.CY
HALF = 22.0; DEPTH = 12.0; WL = -5.0                                            # channel half width, bed depth, water level
def jag(x): return 1.2 * math.sin(x * 0.31) + 0.7 * math.sin(x * 0.83 + 1.3)
def bank_d(x, y): return abs(y - cy) - (HALF + jag(x))                        # < 0 inside the channel
def ground_z(x, y):
    d = bank_d(x, y)
    if d > 1.5: return 0.3 * math.sin(x * 0.21) * math.sin(y * 0.17)
    if d < -1.5: return -DEPTH
    t = (d + 1.5) / 3.0; return -DEPTH * (1 - t) ** 1.5 + 0.0
S = 110; N = 330
bm = bmesh.new(); vs = {}
for i in range(N + 1):
    for j in range(N + 1):
        x = cx - S + 2 * S * i / N; y = cy - S + 2 * S * j / N; vs[(i, j)] = bm.verts.new(G(x, y, ground_z(x, y)))
cl = bm.loops.layers.color.new("mask")
for i in range(N):
    for j in range(N):
        f = bm.faces.new([vs[(i, j)], vs[(i + 1, j)], vs[(i + 1, j + 1)], vs[(i, j + 1)]])
        for l in f.loops:
            x, y = l.vert.co.x, -l.vert.co.y; d = bank_d(x, y)
            t = 1.0 if d < 1.2 else max(0.0, 1 - (d - 1.2) / 1.0); l[cl] = (t, t, t, 1)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("terrain"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = True
me.materials.append(cmat.dirt_mat("bank", base=((96, 62, 26), (170, 114, 50)), mask="mask", other=((30, 84, 26), (58, 118, 34))))
bpy.context.scene.collection.objects.link(bpy.data.objects.new("terrain", me))
wb = bmesh.new()                                                                # water surface
wf = wb.faces.new([wb.verts.new(G(cx + a, cy + b, WL)) for a, b in ((-S, HALF + 3), (S, HALF + 3), (S, -HALF - 3), (-S, -HALF - 3))])
wf.normal_update()
if wf.normal.z < 0: wf.normal_flip()                                             # the water must face up (a downward face showed white in one camera view)
wm = bpy.data.meshes.new("water"); wb.to_mesh(wm); wb.free(); wm.materials.append(cmat.water_mat(flow=(1.0, 0.0)))
bpy.context.scene.collection.objects.link(bpy.data.objects.new("water", wm))
fb = bmesh.new(); rnd = random.Random(3)                                         # foam: small flat white blobs along the banks at the water line
for side in (-1, 1):
    x = cx - S
    while x < cx + S:
        y = cy + side * (HALF + jag(x) - 1.2 - (DEPTH + WL) * 0.0); r = 0.5 + rnd.random() * 0.6
        res = bmesh.ops.create_icosphere(fb, subdivisions=1, radius=r)
        for v in res["verts"]: v.co.z *= 0.15
        bmesh.ops.translate(fb, vec=G(x, y - side * (0.6 + rnd.random() * 1.5), WL + 0.1), verts=res["verts"]); x += 3.0 + rnd.random() * 6.0
fm = bpy.data.meshes.new("foam"); fb.to_mesh(fm); fb.free(); fm.materials.append(cmat.pmat("foam", (150, 190, 210), (210, 232, 240), scale=0.5, rough=0.6))
bpy.context.scene.collection.objects.link(bpy.data.objects.new("foam", fm))
grs = random.Random(9); pts = []
for i in range(int(2 * S / 3.2)):
    for j in range(int(2 * S / 3.2)):
        x = cx - S + 1.6 + i * 3.2 + (grs.random() - 0.5) * 2.4; y = cy - S + 1.6 + j * 3.2 + (grs.random() - 0.5) * 2.4
        if bank_d(x, y) > 1.8: pts.append((x, y))
cground.grass(pts, ground_z, bank_d)
figs = []
fig = os.path.expanduser(os.environ.get("R_FIGURE", ""))
if fig and os.path.exists(fig): figs.append(H.add_figure(fig, (cx - 10, cy + HALF + 14, 0)))
H.render_set(out, px=2.0, dof=True, modern=True, figures=figs, quarter=True, tz=-2, fh=170, sun_spec=0.0)     # no sun gloss: with 0.25 (even 0.05) the water of view q1 was one white sheet (ortho camera near the mirror angle)
if os.environ.get("R_CLOSE"):
    sc = bpy.context.scene; co = sc.camera; co.data.type = "ORTHO"; co.data.ortho_scale = 80; co.data.dof.use_dof = False
    for f in figs: f.hide_render = True
    blx.orbit(co, G(cx, cy + 10, -4), 0, 30); sc.render.resolution_x, sc.render.resolution_y = 700, 600
    sc.render.filepath = os.path.join(out, "close.png"); bpy.ops.render.render(write_still=True)
print("water_c done ->", out)
