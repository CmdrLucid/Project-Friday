import bpy, math, os
OUT = os.environ.get('R_OUT', '/home/deck/lktest/angel3'); OBJ = os.environ.get('R_OBJ', '/home/deck/lktest/angel3/angel.obj')
bpy.ops.wm.read_factory_settings(use_empty=True)
V, F = [], []
for l in open(OBJ):
    if l.startswith('v '): x, y, z = map(float, l.split()[1:]); V.append((x, -y, z))   # Blender y = north
    elif l.startswith('f '): F.append([int(t) - 1 for t in l.split()[1:]])
me = bpy.data.meshes.new('angel'); me.from_pydata(V, [], F); me.update(); me.set_sharp_from_angle(angle=math.radians(35))
for p in me.polygons: p.use_smooth = True
ob = bpy.data.objects.new('angel', me); bpy.context.scene.collection.objects.link(ob)
mat = bpy.data.materials.new('gold'); mat.use_nodes = True; bs = mat.node_tree.nodes['Principled BSDF']
bs.inputs['Base Color'].default_value = (0.62, 0.58, 0.52, 1); bs.inputs['Metallic'].default_value = 0.0; bs.inputs['Roughness'].default_value = 0.7
me.materials.append(mat)
cx = sum(v[0] for v in V) / len(V); cy = sum(v[1] for v in V) / len(V); cz = sum(v[2] for v in V) / len(V)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = sc.render.resolution_y = 600; sc.render.film_transparent = False
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.75, 0.73, 0.62, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 0.6
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(30 + float(os.environ.get('R_SUNYAW', '0')))); sc.collection.objects.link(sun)
tgt = bpy.data.objects.new('tgt', None); bpy.context.scene.collection.objects.link(tgt)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); cam.data.type = 'ORTHO'; cam.data.ortho_scale = float(os.environ.get('R_SCALE', '62')); cam.data.clip_end = 2000; sc.collection.objects.link(cam); sc.camera = cam
tgt.location = (cx, cy, cz); con = cam.constraints.new('TRACK_TO'); con.target = tgt; con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
print('centre', cx, cy, cz)
VIEWS = [tuple(map(float, t.split(':'))) for t in os.environ.get('R_VIEWS', '0:35.26,60:35.26,120:35.26,180:35.26').split(',')]
for k, (yaw, elev) in enumerate(VIEWS):
    a = math.radians(-45 + yaw); el = math.radians(elev)   # game view: from +x / +y (Blender -y) and above
    d = 120; cam.location = (cx + d * math.cos(el) * math.cos(a), cy + d * math.cos(el) * math.sin(a), cz + d * math.sin(el))
    sc.render.filepath = os.path.join(OUT, os.environ.get('R_PRE','prev') + '_%d.png' % k); bpy.ops.render.render(write_still=True)
print('prev done')
