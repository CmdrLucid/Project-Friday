# decimate.py (Blender): DC_IN obj -> DC_OUT obj with about DC_TRIS triangles (collapse decimate, triangulated): the LIGHT PROXY of the sculpt (the light
# field works on 4 unit columns and the GPU model buffer on game pixels: sub-pixel detail of the 400 000 face sculpt is useless there and slow to build)
import bpy, os
E = os.environ.get; V, F = [], []
for l in open(E('DC_IN')):
    if l.startswith('v '): V.append(tuple(map(float, l.split()[1:4])))
    elif l.startswith('f '): F.append([int(t) - 1 for t in l.split()[1:]])
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('m'); me.from_pydata(V, [], F); me.update()
ob = bpy.data.objects.new('m', me); bpy.context.scene.collection.objects.link(ob); bpy.context.view_layer.objects.active = ob; ob.select_set(True)
t = ob.modifiers.new('t', 'TRIANGULATE'); bpy.ops.object.modifier_apply(modifier='t')
n0 = len(ob.data.polygons); d = ob.modifiers.new('d', 'DECIMATE'); d.ratio = min(1.0, float(E('DC_TRIS', '9000')) / n0); bpy.ops.object.modifier_apply(modifier='d')
m = ob.data
with open(E('DC_OUT'), 'w') as fo:
    fo.write(E('DC_HEAD', '# light proxy') + '\n')
    for v in m.vertices: fo.write('v %.3f %.3f %.3f\n' % tuple(v.co))
    for p in m.polygons: fo.write('f ' + ' '.join(str(i + 1) for i in p.vertices) + '\n')
print('decimated', n0, '->', len(m.polygons))
