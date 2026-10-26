"""Massan statue (style C, 2026-10-26): preview of lib/props_c.massan_statue alone (humanoid bear like the villagers, vines, ivy) on village ground,
close views from the game direction and turned by 90 / 180 degrees.  Run: python3 remake/tools/build_asset.py statue_c"""
import bpy, bmesh, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, cmat, props_c, massan_a as H
out = os.environ.get("R_OUT", "/tmp/statue_c"); os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False; G = H.G
cx, cy = H.CX, H.CY
props_c.massan_statue(cx, cy, 0.0)
g = bpy.data.meshes.new("ground"); b = bmesh.new(); s = 200
b.faces.new([b.verts.new(G(cx + a, cy + c, 0)) for a, c in ((-s, s), (s, s), (s, -s), (-s, -s))]); b.to_mesh(g); b.free()
g.materials.append(cmat.get("dirt")); bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", g))
H.render_set(out, px=2.0, dof=False, modern=True, figures=[], quarter=True, tz=20, fh=120)
sc = bpy.context.scene; co = sc.camera; co.data.type = "ORTHO"; co.data.ortho_scale = 62; co.data.dof.use_dof = False
sc.render.resolution_x, sc.render.resolution_y = 600, 760
for k, yaw in enumerate((0, 90, 180)):
    blx.orbit(co, G(cx, cy, 28), yaw, 20); sc.render.filepath = os.path.join(out, "close_%d.png" % k); bpy.ops.render.render(write_still=True)
print("statue_c done ->", out)
