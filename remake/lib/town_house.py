"""TOWN HOUSE builder (Mercator / Ryuma house type, remake/MODELS.md 'Town house'): wings with a hip roof and a flat top, windows / doors
recessed from the standard wall tiles (measured 2026-11-20 with remake/tools/fit_house.py + find_openings.py). Used by remake/recipes/proxy_houses_*.py
inside Blender. A house = (wings [(x0, y0, x1, y1)], (eave, top, inset) ABSOLUTE heights, openings [(wing, wall, slot, storey, kind)], z0 ground).
Tile geometry relative to the slot start along the wall and the storey floor fz = z0 + 48 * storey:
  window frame slot + 3 .. + 16, fz + 22 .. + 38, recess 1.5; sill slot + 0 .. + 16, fz + 16 .. + 21, 1 out; door slot + 4 .. + 16, fz + 3 .. + 43, recess 2.5."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import proxy
import bpy, bmesh
WIN, DOOR = "window", "door"
PROX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "data", "proxies")

def mk(name, v, f):
    """game coordinates -> Blender (y north): flipping y mirrors, so the faces are reversed to keep them pointing outward"""
    me = bpy.data.meshes.new(name); me.from_pydata([(x, -y, z) for x, y, z in v], [], [tuple(reversed(q)) for q in f]); me.update()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob); return ob

def box(name, x0, y0, z0, x1, y1, z1):
    v, f = proxy.part_mesh(x0, y0, x1, y1, z0, z1, z1, "flat", None); return mk(name, v, f)

def boolean(target, tool, op):
    m = target.modifiers.new("b", "BOOLEAN"); m.object = tool; m.operation = op; m.solver = "EXACT"
    bpy.context.view_layer.objects.active = target; bpy.ops.object.modifier_apply(modifier="b"); bpy.data.objects.remove(tool)

def wall_box(wing, wall, a0, a1, z0, z1, inside, outside, name):
    """a box on the wall plane: along the wall a0..a1, z0..z1, from 'inside' units behind the wall face to 'outside' units in front of it"""
    x0, y0, x1, y1 = wing
    if wall == "y": return box(name, a0, y1 - inside, z0, a1, y1 + outside, z1)
    return box(name, x1 - inside, a0, z0, x1 + outside, a1, z1)

def house(name, title, recipe, wings, heights, openings, z0=16, small=()):
    ze, zt, i = heights
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obs = []
    for k, (x0, y0, x1, y1) in enumerate(wings):
        v, f = proxy.part_mesh(x0, y0, x1, y1, z0, ze, zt, "hip:%g" % i, None); obs.append(mk("w%d" % k, v, f))
    h = obs[0]
    for o in obs[1:]: boolean(h, o, "UNION")
    for wk, wall, s0, st, kind in openings:
        fz = z0 + 48 * st
        if kind == WIN:
            boolean(h, wall_box(wings[wk], wall, s0 + 3, s0 + 16, fz + 22, fz + 38, 1.5, 5, "win"), "DIFFERENCE")
            boolean(h, wall_box(wings[wk], wall, s0, s0 + 16, fz + 16, fz + 21, 1, 1, "sill"), "UNION")
        else:
            boolean(h, wall_box(wings[wk], wall, s0 + 4, s0 + 16, fz + 3, fz + 43, 2.5, 5, "door"), "DIFFERENCE")
    for wk, wall, a0, a1, za, zb in small:
        boolean(h, wall_box(wings[wk], wall, a0, a1, za, zb, 1.5, 5, "small"), "DIFFERENCE")
    bm = bmesh.new(); bm.from_mesh(h.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.verts.index_update()
    path = os.path.join(PROX, name + ".obj")
    with open(path, "w") as fo:
        fo.write("# light proxy: %s (remake/recipes/%s.py). GAME coordinates x east, y south, z up, world units.\n" % (title, recipe))
        fo.write("# our own geometry measured on the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        for vv in bm.verts: fo.write("v %g %g %g\n" % (round(vv.co.x, 3), round(-vv.co.y, 3), round(vv.co.z, 3)))
        for ff in bm.faces: fo.write("f " + " ".join(str(vv.index + 1) for vv in reversed(ff.verts)) + "\n")
    print("%s: %s: %d vertices, %d triangles -> %s" % (recipe, name, len(bm.verts), len(bm.faces), path))

