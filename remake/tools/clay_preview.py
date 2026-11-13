#!/usr/bin/env python3
"""clay_preview.py OUT.png A.obj [B.obj ...] [--turns 0,60,120,180] [--px 1600]
CLAY PREVIEW of light / remake models (OBJ in GAME coordinates: x east, y south, z up, units) for the user's OK (remake/MODELING_LESSONS.md: game view +
turned 60 / 120 / 180 degrees). One row per OBJ, one column per turn (each copy turned about its own centre), rendered headless with Blender's
Workbench engine (flatpak org.blender.Blender, like build_asset.py): matte clay, soft studio light, shadows, cavity. Camera = orthographic from the
game's side (screen right = +x -y, looking down 30 degrees). Local output only (never in git)."""
import os, subprocess, sys

BLENDER_SCRIPT = r'''
import bpy, math, sys, mathutils
a = sys.argv[sys.argv.index("--") + 1:]
out, px, turns, objs = a[0], int(a[1]), [float(t) for t in a[2].split(",")], a[3:]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
def load(path):
    V, F = [], []
    for l in open(path):
        if l.startswith("v "):
            x, y, z = map(float, l.split()[1:4]); V.append((x, -y, z))          # game (x, y south, z) -> Blender (x, -y, z)
        elif l.startswith("f "): F.append([int(t.split("/")[0]) - 1 for t in l.split()[1:]])
    return V, F
rows = []
for p in objs:
    V, F = load(p)
    xs = [v[0] for v in V]; ys = [v[1] for v in V]; zs = [v[2] for v in V]
    c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs))
    V = [(v[0] - c[0], v[1] - c[1], v[2] - c[2]) for v in V]
    r = max(max(xs) - min(xs), max(ys) - min(ys)) * 0.75 + 4
    rows.append((p, V, F, r, max(zs) - min(zs)))
step = max(t[3] for t in rows) * 2.1
offs, acc = [], 0.0
for t in rows: acc += t[4] * 2.0; offs.append(acc); acc += step                                # a tall row reaches up the screen: room above it
mat = bpy.data.materials.new("clay"); mat.diffuse_color = (0.92, 0.90, 0.86, 1)
right = mathutils.Vector((1, 1, 0)).normalized()                                 # screen right in Blender coordinates
down = mathutils.Vector((1, -1, 0)).normalized()                                 # towards the camera on the ground (screen down)
for i, (p, V, F, r, hz) in enumerate(rows):
    me0 = bpy.data.meshes.new("m%d" % i); me0.from_pydata(V, [], F); me0.validate(); me0.update()
    for k in me0.polygons: k.use_smooth = False
    for j, t in enumerate(turns):
        ob = bpy.data.objects.new("o%d_%d" % (i, j), me0); sc.collection.objects.link(ob); ob.data.materials.append(mat)
        ob.rotation_euler = (0, 0, math.radians(t))
        ob.location = right * (j * step) + down * offs[i]
bpy.ops.mesh.primitive_plane_add(size=1); pl = bpy.context.active_object; pl.scale = (1e4, 1e4, 1); pl.location = (0, 0, -0.01); pl.data.materials.append(mat)
n, m = len(turns), len(rows)
cen = right * ((n - 1) * step / 2) + down * (offs[-1] / 2)
el = math.radians(30.0)
d = (down * math.cos(el) + mathutils.Vector((0, 0, 1)) * math.sin(el)).normalized()
cam = bpy.data.cameras.new("cam"); cam.type = "ORTHO"
co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
bpy.context.view_layer.update()
up = d.cross(right).normalized()                                                    # screen up
pts = [ob.matrix_world @ v.co for ob in sc.objects if ob.type == "MESH" and ob.name.startswith("o") for v in ob.data.vertices]
us = [p.dot(right) for p in pts]; vs = [p.dot(up) for p in pts]
cu, cv = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2; w, h = max(us) - min(us) + 8, max(vs) - min(vs) + 8
co.location = right * cu + up * cv + d * 3000
co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
cam.ortho_scale = max(w, h) * 1.04; cam.clip_end = 8000
sc.render.resolution_x = px; sc.render.resolution_y = max(200, int(px * h / w)); sc.render.resolution_percentage = 100
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "SINGLE"; sh.single_color = (0.85, 0.83, 0.79); sh.show_shadows = True; sh.show_cavity = True; sh.cavity_type = "BOTH"
sc.display.shadow_focus = 0.6; sc.display.light_direction = (0.45, -0.35, 0.82)
sc.render.film_transparent = False; sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.62, 0.61, 0.58)
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
print("clay_preview: %d models x %d turns -> %s" % (m, n, out))
'''

def main():
    a = sys.argv[1:]; turns = "0,60,120,180"; px = 1600
    if "--turns" in a: i = a.index("--turns"); turns = a[i + 1]; del a[i:i + 2]
    if "--px" in a: i = a.index("--px"); px = int(a[i + 1]); del a[i:i + 2]
    out, objs = os.path.abspath(a[0]), [os.path.abspath(p) for p in a[1:]]
    d = os.path.join(os.path.expanduser("~"), ".landstalker_remake", "build"); os.makedirs(d, exist_ok=True)   # flatpak has its own /tmp
    sp = os.path.join(d, "clay_preview_blender.py"); open(sp, "w").write(BLENDER_SCRIPT)
    r = subprocess.run(["flatpak", "run", "--filesystem=host", "--command=blender", "org.blender.Blender", "-b", "-P", sp, "--", out, str(px), turns] + objs,
                       capture_output=True, text=True)
    print("\n".join(l for l in (r.stdout + r.stderr).splitlines() if "clay_preview" in l or "Error" in l or "Traceback" in l)[-3000:]); sys.exit(r.returncode)

if __name__ == "__main__":
    main()
