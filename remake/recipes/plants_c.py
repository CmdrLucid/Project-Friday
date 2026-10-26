"""ASSET 2 (style C, 2026-10-25): PINE and HEDGE of Massan (room 592), shown with Nigel for scale; Nigel stands ON the hedge (user: 'Nigel kann auf den
Bueschen laufen, das muss in 3D nach wie vor so aussehen').
Pine (original: bright green cone of drooping branch tiers, round brown stump at the foot, ~28 px wide): trunk + root flare + 6 tiers of star-shaped
branch rings (tips out and down), each tier turned a little; material 'needles'.
Bushes (original, seen from the front in rooms 424 / 425: one small shrub per map cell, round dark green crown on a short Y-shaped stem, crowns touching,
walkable on top): kit_c.bushes(); crown tops at the cell height H (env R_HEDGE_H, default 16 = one height step).
Run: R_FIGURE=~/.landstalker_remake/figures/nigel_a4.png python3 remake/tools/build_asset.py plants_c"""
import bpy, bmesh, sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat, kit_c, massan_a as H
out = os.environ.get("R_OUT", "/tmp/plants_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
rnd = random.Random(11)
G = H.G

# scene around the centre the previews look at (lib/massan_a.py CX, CY)
cx, cy = H.CX, H.CY
kit_c.pine(cx - 30, cy - 18, rnd=rnd); kit_c.pine(cx - 46, cy + 6, height=36, radius=11, name="pine2", rnd=rnd); kit_c.pine(cx - 14, cy - 40, height=46, radius=14, name="pine3", rnd=rnd)
HH = float(os.environ.get("R_HEDGE_H", "16"))
kit_c.bushes([(cx + 2 + 16 * i, cy - 8 + 16 * j) for i in range(3) for j in range(2)], HH, rnd=rnd)
g = bpy.data.meshes.new("ground"); b = bmesh.new(); s = 260
b.faces.new([b.verts.new(G(cx + a, cy + c, 0)) for a, c in ((-s, s), (s, s), (s, -s), (-s, -s))]); b.to_mesh(g); b.free()
g.materials.append(cmat.pmat("ground", (120, 96, 52), (88, 116, 44), scale=0.02, detail=6.0, bump=0.1, rough=1.0)); bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", g))
figs = []
fig = os.path.expanduser(os.environ.get("R_FIGURE", ""))
if fig and os.path.exists(fig):
    figs.append(H.add_figure(fig, (cx + 26, cy + 4, HH)))                      # Nigel standing ON the hedge
    figs.append(H.add_figure(fig, (cx - 10, cy + 26, 0)))                      # and on the ground beside the pines
H.render_set(out, px=2.0, dof=True, modern=True, figures=figs, quarter=True, tz=20, fh=170)
if os.environ.get("R_CLOSE"):                                                  # close-up of the front bush from the game camera (stem check)
    sc = bpy.context.scene; co = sc.camera; co.data.type = "ORTHO"; co.data.ortho_scale = 42; co.data.dof.use_dof = False
    for f in figs: f.hide_render = True
    blx.orbit(co, G(cx + 2 + 16 * 2 + 8, cy - 8 + 16 + 8, 8), 0, 30); sc.render.resolution_x, sc.render.resolution_y = 700, 600
    sc.render.filepath = os.path.join(out, "close.png"); bpy.ops.render.render(write_still=True)
print("plants_c done ->", out)
