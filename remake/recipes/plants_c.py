"""ASSET 2 (style C, 2026-10-25): PINE and HEDGE of Massan (room 592), shown with Nigel for scale; Nigel stands ON the hedge (user: 'Nigel kann auf den
Bueschen laufen, das muss in 3D nach wie vor so aussehen').
Pine (original: bright green cone of drooping branch tiers, round brown stump at the foot, ~28 px wide): trunk + root flare + 6 tiers of star-shaped
branch rings (tips out and down), each tier turned a little; material 'needles'.
Hedge (original: a block of dense round leaf clumps on whole map cells, walkable on top): per 16 x 16 cell a 2 x 2 group of squashed clumps whose tops
stay within +1.5 of the cell height H (env R_HEDGE_H, default 16 = one height step: the top reads as a floor), rounder clumps on the open sides.
Run: R_FIGURE=~/.landstalker_remake/figures/nigel_a4.png python3 remake/tools/build_asset.py plants_c"""
import bpy, bmesh, sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat, massan_a as H
out = os.environ.get("R_OUT", "/tmp/plants_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
rnd = random.Random(11)
G = H.G

def mesh_obj(name, bm, mat, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    me.materials.append(mat); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def pine(x, y, height=42.0, radius=13.0, tiers=6, name="pine"):
    """game position of the trunk foot (x, y); height / radius of the crown."""
    bm = bmesh.new()
    # crown: star-shaped tiers, tips out and drooping, notches in and up
    for i in range(tiers):
        f = i / tiers; z0 = 7.0 + f * (height - 13.0); r = radius * (1 - 0.78 * f) + 1.5; h = 10.0 - 3.0 * f
        n = 14 - i; rot = rnd.random() * math.pi; ring = []
        for k in range(2 * n):
            a = rot + math.pi * k / n; tip = k % 2 == 0
            rr = r * (1.0 if tip else 0.62) * (1 + (rnd.random() - 0.5) * 0.12); zz = z0 + (-1.6 if tip else 0.8) + (rnd.random() - 0.5) * 0.6
            ring.append(bm.verts.new(G(x + rr * math.cos(a), y + rr * math.sin(a), zz)))
        mid = [bm.verts.new(G(x + 0.55 * r * math.cos(rot + math.pi * k / n), y + 0.55 * r * math.sin(rot + math.pi * k / n), z0 + h * 0.45)) for k in range(0, 2 * n, 1)]
        top = bm.verts.new(G(x, y, z0 + h)); under = bm.verts.new(G(x, y, z0 - 0.5))
        m2 = len(ring)
        for k in range(m2):
            bm.faces.new([ring[k], ring[(k + 1) % m2], mid[(k + 1) % m2], mid[k]])
            bm.faces.new([mid[k], mid[(k + 1) % m2], top])
            bm.faces.new([ring[(k + 1) % m2], ring[k], under])
    crown = mesh_obj(name, bm, cmat.get("needles"))
    bm = bmesh.new()                                                            # trunk + root flare (the round stump of the picture)
    r1 = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=3.0, radius2=2.4, depth=12.0)
    bmesh.ops.translate(bm, vec=(0, 0, 6.0), verts=r1["verts"])
    r2 = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=5.2, radius2=3.0, depth=3.0)
    bmesh.ops.translate(bm, vec=(0, 0, 1.5), verts=r2["verts"])
    bmesh.ops.translate(bm, vec=G(x, y, 0), verts=bm.verts)
    trunk = mesh_obj(name + "_trunk", bm, cmat.get("post"))
    return crown, trunk

def clump(bm, c, r, sz, seed):
    """one leaf clump: an icosphere with bumpy surface, squashed by sz in z."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
    rr = random.Random(seed)
    for v in res["verts"]:
        n = v.co.normalized(); bump = 1 + 0.10 * math.sin(7 * n.x + seed) * math.sin(6 * n.y + 2 * seed) + (rr.random() - 0.5) * 0.06
        v.co = mathutils_vec(n.x * r * bump, n.y * r * bump, n.z * r * bump * sz)
    bmesh.ops.translate(bm, vec=c, verts=res["verts"])
def mathutils_vec(x, y, z):
    import mathutils; return mathutils.Vector((x, y, z))

def hedge(cells, Hh=16.0, name="hedge"):
    """cells = [(cx, cy)] map cells (16 x 16 units, game x / y of the cell's north west corner); Hh = the walkable top height."""
    bm = bmesh.new(); S = 16.0; seed = 0; cs = set(cells)
    for (cx, cy) in cells:
        for (ix, iy) in ((0, 0), (1, 0), (0, 1), (1, 1)):
            seed += 1; px = cx + 4 + 8 * ix + (rnd.random() - 0.5) * 4.0; py = cy + 4 + 8 * iy + (rnd.random() - 0.5) * 4.0
            r = 5.0 + rnd.random() * 2.6; sz = 0.45 + rnd.random() * 0.2
            clump(bm, G(px, py, Hh + 1.2 - r * sz), r, sz, seed)                 # top clumps: their tops lie at Hh .. Hh + 1.5
            open_side = [(dx, dy) for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)) if (cx + dx * S, cy + dy * S) not in cs and ((dx == -1 and ix == 0) or (dx == 1 and ix == 1) or (dy == -1 and iy == 0) or (dy == 1 and iy == 1))]
            if open_side:                                                       # rounder clumps lower down on the open sides
                seed += 1; dx = sum(d[0] for d in open_side) * 1.5; dy = sum(d[1] for d in open_side) * 1.5
                clump(bm, G(px + dx, py + dy, Hh * 0.45), 6.0 + rnd.random(), 0.95, seed)
        seed += 1; clump(bm, G(cx + 8, cy + 8, Hh * 0.45), 7.5, 1.0, seed)           # core, so nothing is see-through
        for k in range(2):                                                      # a few small clumps on top at random spots: no regular grid
            seed += 1; r = 3.0 + rnd.random() * 1.5
            clump(bm, G(cx + 2 + rnd.random() * 12, cy + 2 + rnd.random() * 12, Hh + 1.3 - r * 0.5), r, 0.5, seed)
    return mesh_obj(name, bm, cmat.get("leaves"))

# scene around the centre the previews look at (lib/massan_a.py CX, CY)
cx, cy = H.CX, H.CY
pine(cx - 30, cy - 18); pine(cx - 46, cy + 6, height=36, radius=11, name="pine2"); pine(cx - 14, cy - 40, height=46, radius=14, name="pine3")
HH = float(os.environ.get("R_HEDGE_H", "16"))
hedge([(cx + 2 + 16 * i, cy - 8 + 16 * j) for i in range(3) for j in range(2)], HH)
g = bpy.data.meshes.new("ground"); b = bmesh.new(); s = 260
b.faces.new([b.verts.new(G(cx + a, cy + c, 0)) for a, c in ((-s, s), (s, s), (s, -s), (-s, -s))]); b.to_mesh(g); b.free()
g.materials.append(cmat.pmat("ground", (120, 96, 52), (88, 116, 44), scale=0.02, detail=6.0, bump=0.1, rough=1.0)); bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", g))
figs = []
fig = os.path.expanduser(os.environ.get("R_FIGURE", ""))
if fig and os.path.exists(fig):
    figs.append(H.add_figure(fig, (cx + 26, cy + 4, HH)))                      # Nigel standing ON the hedge
    figs.append(H.add_figure(fig, (cx - 10, cy + 26, 0)))                      # and on the ground beside the pines
H.render_set(out, px=2.0, dof=True, modern=True, figures=figs, quarter=True, tz=20, fh=170)
print("plants_c done ->", out)
