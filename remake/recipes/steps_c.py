"""ASSET 4 (style C, 2026-10-25): STONE STEPS and loose stones of Massan (room 592, the terrace between the houses).
Original: dry-stone steps of rounded stones, grey-blue rounded tops (the walking surface), earthy ochre sides; the height map has one band of height-1
cells between the ground (0) and the upper level (2), i.e. two steps of 16.  Built here: every step = a row of map cells at height h: an earth body,
two courses of rounded stones on the front face, two rows of flattened cap stones on top whose tops stay within h .. h + 1 (walkable), material 'stepstone'
(sides earthy, faces looking up grey-blue).  Loose stones: 'boulder'.  Nigel stands on the middle step.
Run: R_FIGURE=~/.landstalker_remake/figures/nigel_a4.png R_CLOSE=1 python3 remake/tools/build_asset.py steps_c"""
import bpy, bmesh, sys, os, math, random, mathutils
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat, kit_c, massan_a as H
out = os.environ.get("R_OUT", "/tmp/steps_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
rnd = random.Random(31); G = H.G

cx, cy = H.CX, H.CY
bst = bmesh.new(); bbody = bmesh.new(); seed = 0
x0, x1 = cx - 40, cx + 40
STYLE = os.environ.get("R_STEPS", "stumps")                                      # stumps (Massan) / stones (dry-stone steps elsewhere)
row = kit_c.stump_row if STYLE == "stumps" else kit_c.step_row
seed = row(bst, bbody, x0, x1, cy + 16, 16, 16.0, seed, rnd=rnd)                         # step 1: top 16
seed = row(bst, bbody, x0, x1, cy, 16, 32.0, seed, rnd=rnd)                              # step 2 = edge of the upper level (top 32)
def obj(name, bm, mat):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o
for (h, yf, dp) in (((16.0, cy + 16, 16), (32.0, cy, 16)) if STYLE != "stumps" else ()):                      # stones on the open west / east ends of each step
    for xe in (x0 - 1.5, x1 + 1.5):
        for k in range(int(dp / 7.6)):
            for zc in (h - 4.6, h - 12.0):
                if zc < 2: continue
                seed += 1; kit_c.rock(bst, G(xe, yf - 4 - k * 7.6 + (rnd.random() - 0.5), zc), 4.0, (0.85, 1.0, 0.95), seed)
so = obj("step_stones", bst, cmat.get("stump" if STYLE == "stumps" else "stepstone"))
so.data.materials.append(cmat.rings_mat() if STYLE == "stumps" else cmat.get("stepstone")); obj("step_body", bbody, cmat.get("earth"))
pl = bmesh.new(); bmesh.ops.create_cube(pl, size=1.0)                         # preview only: the upper level (height 32) the steps lead up to
bmesh.ops.scale(pl, vec=(x1 - x0 + 120, 120, 32), verts=pl.verts); bmesh.ops.translate(pl, vec=G(cx, cy - 16 - 60 + 1.5, 16), verts=pl.verts)
obj("upper_level", pl, cmat.get("dirt"))
bl = bmesh.new()                                                                # loose stones on the ground
for k, (dx, dy, r) in enumerate(((-52, 34, 3.2), (-46, 40, 2.2), (50, 30, 2.6), (30, 44, 1.8), (-10, 46, 2.0))):
    kit_c.rock(bl, G(cx + dx, cy + dy, r * 0.35), r, (1.1, 0.9, 0.7), 500 + k, 0.18)
obj("loose_stones", bl, cmat.get("boulder"))
g = bpy.data.meshes.new("ground"); b = bmesh.new(); s = 260
b.faces.new([b.verts.new(G(cx + a, cy + c, 0)) for a, c in ((-s, s), (s, s), (s, -s), (-s, -s))]); b.to_mesh(g); b.free()
g.materials.append(cmat.get("dirt")); bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", g))
figs = []
fig = os.path.expanduser(os.environ.get("R_FIGURE", ""))
if fig and os.path.exists(fig): figs.append(H.add_figure(fig, (cx + 6, cy + 8, 16.0)))
H.render_set(out, px=2.0, dof=True, modern=True, figures=figs, quarter=True, tz=20, fh=170)
if os.environ.get("R_CLOSE"):
    sc = bpy.context.scene; co = sc.camera; co.data.type = "ORTHO"; co.data.ortho_scale = 70; co.data.dof.use_dof = False
    for f in figs: f.hide_render = True
    blx.orbit(co, G(cx - 10, cy + 8, 16), 0, 30); sc.render.resolution_x, sc.render.resolution_y = 700, 600
    sc.render.filepath = os.path.join(out, "close.png"); bpy.ops.render.render(write_still=True)
print("steps_c done ->", out)
