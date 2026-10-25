"""ASSET 4 (style C, 2026-10-25): STONE STEPS and loose stones of Massan (room 592, the terrace between the houses).
Original: dry-stone steps of rounded stones, grey-blue rounded tops (the walking surface), earthy ochre sides; the height map has one band of height-1
cells between the ground (0) and the upper level (2), i.e. two steps of 16.  Built here: every step = a row of map cells at height h: an earth body,
two courses of rounded stones on the front face, two rows of flattened cap stones on top whose tops stay within h .. h + 1 (walkable), material 'stepstone'
(sides earthy, faces looking up grey-blue).  Loose stones: 'boulder'.  Nigel stands on the middle step.
Run: R_FIGURE=~/.landstalker_remake/figures/nigel_a4.png R_CLOSE=1 python3 remake/tools/build_asset.py steps_c"""
import bpy, bmesh, sys, os, math, random, mathutils
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat, massan_a as H
out = os.environ.get("R_OUT", "/tmp/steps_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
rnd = random.Random(31); G = H.G

def rock(bm, c, r, sq=(1, 1, 1), seed=0, lump=0.12):
    res = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0); rr = random.Random(seed)
    ph = [rr.random() * 6 for _ in range(4)]
    for v in res["verts"]:
        n = v.co.normalized(); k = 1 + lump * math.sin(3 * n.x + ph[0]) * math.sin(3 * n.y + ph[1]) + lump * 0.6 * math.sin(5 * n.z + ph[2])
        v.co = mathutils.Vector((n.x * r * sq[0] * k, n.y * r * sq[1] * k, n.z * r * sq[2] * k))
    bmesh.ops.translate(bm, vec=c, verts=res["verts"])

def stump_row(bm, bm_body, x0, x1, y_front, depth, h, seed):
    """Massan variant (user 2026-10-25: 'sieht eher nach Baumstaemmen im Boden aus'): the step is rows of UPRIGHT LOG STUMPS set in the ground,
    tops at h (+-0.7, slightly domed, weathered grey), rows 7.5 apart and staggered, radius ~3.6."""
    bmesh.ops.create_cube(bm_body, size=1.0); vs = bm_body.verts[-8:]
    bmesh.ops.scale(bm_body, vec=(x1 - x0 - 8, depth - 7, h - 3), verts=vs); bmesh.ops.translate(bm_body, vec=G((x0 + x1) / 2, y_front - 3.5 - (depth - 7) / 2, (h - 3) / 2), verts=vs)   # core behind the stump centres
    rows = max(1, int(depth / 7.5))
    for j in range(rows):
        y0 = y_front - 3.7 - j * 7.5; x = x0 + 2.5 + (3.0 if j % 2 else 0.0) * rnd.random()
        while x < x1 - 2.5:
            seed += 1; r = 3.1 + rnd.random() * 1.1                               # irregular like the original: sizes, heights, lean, slanted cuts
            xc = x + r; x = xc + r + rnd.random() * 0.6
            if xc > x1 - 1.5: break
            top = h - 0.4 + (rnd.random() - 0.5) * 0.4                                 # same height for all stumps, like the original
            res = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r * (1.0 + rnd.random() * 0.1), radius2=r * (0.88 + rnd.random() * 0.1), depth=top + 1.0)
            vs = res["verts"]; bmesh.ops.translate(bm, vec=(0, 0, (top + 1.0) / 2 - 1.0), verts=vs)
            sa, sb = (rnd.random() - 0.5) * 0.08, (rnd.random() - 0.5) * 0.08   # slanted, uneven top cut
            for v in vs:
                if v.co.z > top - 0.01:
                    v.co.z += sa * v.co.x + sb * v.co.y + (0.9 if math.hypot(v.co.x, v.co.y) < 0.01 else (rnd.random() - 0.5) * 0.5)
                v.co.x *= 1 + (rnd.random() - 0.5) * 0.08; v.co.y *= 1 + (rnd.random() - 0.5) * 0.08
            lean = mathutils.Euler(((rnd.random() - 0.5) * 0.04, (rnd.random() - 0.5) * 0.04, rnd.random() * 6.28)).to_matrix()
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=lean, verts=vs)
            bmesh.ops.translate(bm, vec=G(xc, y0 + (rnd.random() - 0.5) * 1.4, 0), verts=vs)
    return seed

def step_row(bm_st, bm_body, x0, x1, y_front, depth, h, seed):
    """one step: cells from x0 to x1 (game x), front edge at y_front (south), 'depth' units deep to the north, top at h."""
    # earth body (hidden behind the stones, closes the gaps)
    bmesh.ops.create_cube(bm_body, size=1.0); vs = bm_body.verts[-8:]
    bmesh.ops.scale(bm_body, vec=(x1 - x0, depth, h - 1), verts=vs); bmesh.ops.translate(bm_body, vec=G((x0 + x1) / 2, y_front - depth / 2 - 1.5, (h - 1) / 2), verts=vs)
    n = int((x1 - x0) / 7.6)
    for k in range(n):                                                          # two courses of stones on the front face
        x = x0 + (k + 0.5) * (x1 - x0) / n
        for (zc, rz, off) in ((h - 4.6, 4.4, 0.0), (h - 12.0, 4.2, 0.5)):
            if zc - rz < -2: continue
            seed += 1; xx = x + off * 3.8 + (rnd.random() - 0.5) * 1.2
            rock(bm_st, G(xx, y_front - 2.8, zc), 4.0 + rnd.random() * 0.6, (1.0, 0.85, rz / 4.4 * 0.95), seed)
    for k in range(n):                                                          # cap stones on top (walking surface: tops at h .. h + 1)
        for j, yy in enumerate((y_front - 4.0, y_front - 11.5)):
            if y_front - yy > depth - 2: continue
            seed += 1; x = x0 + (k + 0.5 + 0.5 * (j % 2)) * (x1 - x0) / n
            if x > x1 - 2: continue
            r = 4.0 + rnd.random() * 0.5; sz = 0.45
            rock(bm_st, G(x + (rnd.random() - 0.5) * 1.5, yy + (rnd.random() - 0.5) * 1.5, h + 1.0 - r * sz), r, (1.0, 1.0, sz), seed)
    return seed

cx, cy = H.CX, H.CY
bst = bmesh.new(); bbody = bmesh.new(); seed = 0
x0, x1 = cx - 40, cx + 40
STYLE = os.environ.get("R_STEPS", "stumps")                                      # stumps (Massan) / stones (dry-stone steps elsewhere)
row = stump_row if STYLE == "stumps" else step_row
seed = row(bst, bbody, x0, x1, cy + 16, 16, 16.0, seed)                         # step 1: top 16
seed = row(bst, bbody, x0, x1, cy, 16, 32.0, seed)                              # step 2 = edge of the upper level (top 32)
def obj(name, bm, mat):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o
for (h, yf, dp) in (((16.0, cy + 16, 16), (32.0, cy, 16)) if STYLE != "stumps" else ()):                      # stones on the open west / east ends of each step
    for xe in (x0 - 1.5, x1 + 1.5):
        for k in range(int(dp / 7.6)):
            for zc in (h - 4.6, h - 12.0):
                if zc < 2: continue
                seed += 1; rock(bst, G(xe, yf - 4 - k * 7.6 + (rnd.random() - 0.5), zc), 4.0, (0.85, 1.0, 0.95), seed)
obj("step_stones", bst, cmat.get("stump" if STYLE == "stumps" else "stepstone")); obj("step_body", bbody, cmat.get("earth"))
pl = bmesh.new(); bmesh.ops.create_cube(pl, size=1.0)                         # preview only: the upper level (height 32) the steps lead up to
bmesh.ops.scale(pl, vec=(x1 - x0 + 120, 120, 32), verts=pl.verts); bmesh.ops.translate(pl, vec=G(cx, cy - 16 - 60 + 1.5, 16), verts=pl.verts)
obj("upper_level", pl, cmat.get("dirt"))
bl = bmesh.new()                                                                # loose stones on the ground
for k, (dx, dy, r) in enumerate(((-52, 34, 3.2), (-46, 40, 2.2), (50, 30, 2.6), (30, 44, 1.8), (-10, 46, 2.0))):
    rock(bl, G(cx + dx, cy + dy, r * 0.35), r, (1.1, 0.9, 0.7), 500 + k, 0.18)
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
