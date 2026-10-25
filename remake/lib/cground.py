"""STYLE C ground helpers shared by the ground recipes: grass tufts of real blades (asset 5b, approved 2026-10-25)."""
import math, random
import bpy, bmesh
import cmat
from massan_a import G

def grass(points, height_at, edge_d, seed=7, name="grass_blades"):
    """points = iterable of (x, y) tuft positions (game); height_at(x, y) = ground z; edge_d(x, y) = distance to the nearest edge (path / bank),
    tufts within 4 of an edge are denser, shorter and lighter (the light grass lip of the original)."""
    bg = bmesh.new(); hl = bg.loops.layers.color.new("h"); grs = random.Random(seed)
    for (x, y) in points:
        d = edge_d(x, y); near = d < 4; z0 = height_at(x, y)
        n = 7 if near else 5; hgt = (4.5 if near else 5.5) + grs.random() * 2.0; light = 0.25 if near else 0.0
        for k in range(n):
            a = grs.random() * 2 * math.pi; rr = grs.random() * 1.6; bx, by = x + rr * math.cos(a), y + rr * math.sin(a)
            h = hgt * (0.6 + grs.random() * 0.6); w = 0.45 + grs.random() * 0.25; ang = grs.random() * math.pi
            lx = 0.7 * h * 0.35 + (grs.random() - 0.5) * h * 0.4; ly = 0.7 * h * 0.35 + (grs.random() - 0.5) * h * 0.4
            p0 = (bx - w * math.cos(ang), by - w * math.sin(ang), z0 - 0.2); p1 = (bx + w * math.cos(ang), by + w * math.sin(ang), z0 - 0.2); p2 = (bx + lx, by + ly, z0 + h)
            f = bg.faces.new([bg.verts.new(G(*p0)), bg.verts.new(G(*p1)), bg.verts.new(G(*p2))])
            t = 0.85 + grs.random() * 0.25 + light
            for l, hv in zip(f.loops, (0.0, 0.0, 1.0)): l[hl] = (hv, t, t, 1.0)
    me = bpy.data.meshes.new(name); bg.to_mesh(me); bg.free(); me.materials.append(cmat.blade_mat())
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob); return ob
