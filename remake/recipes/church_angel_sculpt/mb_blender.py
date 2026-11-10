# Blender: metaball elements from a JSON file (game coordinates) -> triangle OBJ (game coordinates). env MB_IN, MB_OUT, MB_RES
import bpy, json, os, mathutils
bpy.ops.wm.read_factory_settings(use_empty=True)
E = json.load(open(os.environ['MB_IN'])); res = float(os.environ.get('MB_RES', '0.35'))
out = open(os.environ['MB_OUT'], 'w'); base = 1
for gi, grp in enumerate(E['groups']):
    nm = 'G' + chr(65 + gi) + 'x'; mb = bpy.data.metaballs.new(nm); r_ = grp.get('res', res); mb.resolution = r_; mb.render_resolution = r_; mb.threshold = grp.get('threshold', 0.6)
    ob = bpy.data.objects.new(nm, mb); bpy.context.scene.collection.objects.link(ob)
    for e in grp['elements']:
        el = mb.elements.new(); el.type = e['type']; el.co = e['co']; el.radius = e['radius']; el.stiffness = e.get('stiffness', 2.0)
        el.use_negative = e.get('neg', False)
        if 'size' in e: el.size_x, el.size_y, el.size_z = e['size']
        if 'quat' in e: el.rotation = mathutils.Quaternion(e['quat'])
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.calc_loop_triangles()
    for v in me.vertices: out.write('v %.4f %.4f %.4f\n' % tuple(v.co))
    for t in me.loop_triangles: out.write('f %d %d %d\n' % tuple(base + i for i in t.vertices))
    out.write('# group %d %s %d verts\n' % (gi, grp.get('name', ''), len(me.vertices))); base += len(me.vertices)
    print('group', gi, grp.get('name'), len(me.vertices), 'verts', len(me.loop_triangles), 'tris')
out.close(); print('mb done')
