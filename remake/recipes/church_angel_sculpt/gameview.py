# gameview.py (Blender): the EXACT game picture of an OBJ (U = x - y + 1184, V = (x + y) / 2 - z): orthographic camera at 30 degrees elevation with the
# model's z scaled by sqrt(2 / 3); the picture = the window (GV_U0, GV_V0, GV_W, GV_H in game pixels) at GV_PX render pixels per game pixel, so it can be
# laid beside / over the original sprite 1 : 1. Light from the upper left like the drawing (GV_SUN = yaw, elevation), a gold material.
import bpy, math, os
E = os.environ.get; OBJ = E('GV_OBJ'); OUT = E('GV_OUT'); U0, V0, W, H = [float(E(k, d)) for k, d in (('GV_U0', 1074), ('GV_V0', 324), ('GV_W', 64), ('GV_H', 66))]; PX = int(E('GV_PX', 14))
bpy.ops.wm.read_factory_settings(use_empty=True)
ZS = math.sqrt(2.0 / 3.0); V, F = [], []
for l in open(OBJ):
    if l.startswith('v '): x, y, z = map(float, l.split()[1:4]); V.append((x, -y, z * ZS))
    elif l.startswith('f '): F.append([int(t) - 1 for t in l.split()[1:]])
me = bpy.data.meshes.new('m'); me.from_pydata(V, [], F); me.update()
for p in me.polygons: p.use_smooth = True
ob = bpy.data.objects.new('m', me); bpy.context.scene.collection.objects.link(ob)
mat = bpy.data.materials.new('g'); mat.use_nodes = True; bs = mat.node_tree.nodes['Principled BSDF']
col = [float(t) for t in E('GV_COL', '0.80,0.56,0.12').split(',')]; bs.inputs['Base Color'].default_value = (*col, 1); bs.inputs['Metallic'].default_value = float(E('GV_METAL', 0.0)); bs.inputs['Roughness'].default_value = 0.55
me.materials.append(mat)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = int(W * PX); sc.render.resolution_y = int(H * PX); sc.render.film_transparent = False
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.45, 0.45, 0.33, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.5
sy, se = [float(t) for t in E('GV_SUN', '25,48').split(',')]   # from the front right of the picture: the wall plane (wings) is lit; '-55,50' grazed it = dark wings (not a model fault)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 4.5; sc.collection.objects.link(sun)
# window centre -> a world point on the view ray: x - y = Uc - 1184, (x + y) / 2 - z = Vc at z = 55
Uc, Vc = U0 + W / 2, V0 + H / 2; z = 55.0; xmy = Uc - 1184; xpy = 2 * (Vc + z); x = (xpy + xmy) / 2; y = (xpy - xmy) / 2
tx, ty, tz = x, -y, z * ZS
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); cam.data.type = 'ORTHO'; cam.data.clip_end = 3000; sc.collection.objects.link(cam); sc.camera = cam
cam.data.ortho_scale = max(W, H) / math.sqrt(2)   # W game pixels across = W / sqrt(2) world units along the camera's right
tgt = bpy.data.objects.new('t', None); sc.collection.objects.link(tgt); tgt.location = (tx, ty, tz)
el = math.radians(30); a = math.radians(-45); d = 400
cam.location = (tx + d * math.cos(el) * math.cos(a), ty + d * math.cos(el) * math.sin(a), tz + d * math.sin(el))
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
# sun: direction given in the camera's picture (yaw from the picture's up towards the right, elevation above the picture plane) -> simple: place it like a camera
ya = math.radians(-45 + sy); sl = bpy.data.objects.new('sl', None); sc.collection.objects.link(sl)
sun.location = (tx + d * math.cos(math.radians(se)) * math.cos(ya), ty + d * math.cos(math.radians(se)) * math.sin(ya), tz + d * math.sin(math.radians(se)))
c2 = sun.constraints.new('TRACK_TO'); c2.target = tgt; c2.track_axis = 'TRACK_NEGATIVE_Z'; c2.up_axis = 'UP_Y'
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True); print('gv done')
