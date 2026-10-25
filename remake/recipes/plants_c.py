"""ASSET 2 (style C, 2026-10-25): PINE and HEDGE of Massan (room 592), shown with Nigel for scale; Nigel stands ON the hedge (user: 'Nigel kann auf den
Bueschen laufen, das muss in 3D nach wie vor so aussehen').
Pine (original: bright green cone of drooping branch tiers, round brown stump at the foot, ~28 px wide): trunk + root flare + 6 tiers of star-shaped
branch rings (tips out and down), each tier turned a little; material 'needles'.
Bushes (original, seen from the front in rooms 424 / 425: one small shrub per map cell, round dark green crown on a short Y-shaped stem, crowns touching,
walkable on top): bushes() below; crown tops at the cell height H (env R_HEDGE_H, default 16 = one height step).
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

def bushes(cells, Hh=16.0, name="bushes"):
    """the Massan / route bushes (rooms 424 / 425 seen from the front, 2026-10-25): ONE small shrub per 16 x 16 map cell, a round dark green crown on
    a short Y-shaped brown stem; neighbouring crowns touch, so a row reads as one walkable top at Hh (crown tops within Hh .. Hh + 1.5)."""
    bm = bmesh.new(); bs = bmesh.new(); seed = 100
    for (cx, cy) in cells:
        seed += 1; x = cx + 8 + (rnd.random() - 0.5) * 1.2; y = cy + 8 + (rnd.random() - 0.5) * 1.2
        r = 7.3 + rnd.random() * 0.5; sz = 0.72; zc = Hh + 1.0 - r * sz
        clump(bm, G(x, y, zc), r, sz, seed)                                     # the crown
        for k in range(5):                                                      # leaf lumps on the crown: a rounder, leafy outline
            seed += 1; a = 2 * math.pi * k / 5 + rnd.random(); rr = 2.8 + rnd.random() * 1.0
            clump(bm, G(x + 4.6 * math.cos(a), y + 4.6 * math.sin(a), zc + 0.6 + rnd.random()), rr, 0.85, seed)
        zb = zc - r * sz + 1.0                                                  # bottom of the crown
        for (a, b, rad) in (((0, 0, 0), (0, 0, 3.0), 1.3), ((0, 0, 2.6), (-3.0, 1.4, zb + 2.0), 0.9), ((0, 0, 2.6), (2.8, -1.6, zb + 2.0), 0.9), ((0, 0, 2.6), (0.8, 2.8, zb + 1.5), 0.7)):
            pa = G(x + a[0], y + a[1], a[2]); pb = G(x + b[0], y + b[1], b[2])
            import mathutils
            A = mathutils.Vector(pa); B = mathutils.Vector(pb); d = B - A
            res = bmesh.ops.create_cone(bs, cap_ends=True, segments=8, radius1=rad, radius2=rad * 0.75, depth=d.length)
            vs = res["verts"]; bmesh.ops.translate(bs, vec=(0, 0, d.length / 2), verts=vs)
            bmesh.ops.rotate(bs, cent=(0, 0, 0), matrix=d.normalized().to_track_quat("Z", "Y").to_matrix(), verts=vs); bmesh.ops.translate(bs, vec=A, verts=vs)
    crowns = mesh_obj(name, bm, cmat.get("shrub")); stems = mesh_obj(name + "_stems", bs, cmat.get("stem")); return crowns, stems

# scene around the centre the previews look at (lib/massan_a.py CX, CY)
cx, cy = H.CX, H.CY
pine(cx - 30, cy - 18); pine(cx - 46, cy + 6, height=36, radius=11, name="pine2"); pine(cx - 14, cy - 40, height=46, radius=14, name="pine3")
HH = float(os.environ.get("R_HEDGE_H", "16"))
bushes([(cx + 2 + 16 * i, cy - 8 + 16 * j) for i in range(3) for j in range(2)], HH)
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
