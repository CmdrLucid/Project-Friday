"""LIGHT PROXY: Mercator church complex, room 632 (landstalker/docs/LIGHT_PROXY_PLAN.md, user 2026-11-04: 'blender').
An invisible shape for the lighting only (never drawn): church hall with a hip roof, the yellow house in front of it, the entrance gable.
Measured on the original picture of room 632 (projection U = x - y + 1184, V = (x + y) / 2 - z; map cells 15..23 x 50..61 = object 8).
Run: python3 remake/tools/build_asset.py proxy_church_632
Output: landstalker/data/proxies/church_632.obj (GAME coordinates: x east, y south, z up, world units; our own geometry, committed)
        ~/.landstalker_remake/assets/proxy_church_632/preview.png (game camera, local only)."""
import bpy, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx
out = os.environ.get("R_OUT", "/tmp/proxy_church_632"); os.makedirs(out, exist_ok=True)
OBJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "data", "proxies", "church_632.obj")
bpy.ops.wm.read_factory_settings(use_empty=True)

# parts in game coordinates: (x0, y0, x1, y1, z0, eave, ridge, roof, ridge axis)
PARTS = [
    ("hall",   240, 800, 376, 928, 16, 64, 109, "hip", None),
    ("house",  240, 928, 326, 992, 16, 64, 83, "hip", None),
    ("porch",  360, 828, 392, 900, 16, 64, 107, "gable", "x"),
]

def part_mesh(x0, y0, x1, y1, z0, ze, zr, roof, axis):
    """vertices / faces of a box with a hip (flat top, 45 deg sides) or gable roof, game coordinates"""
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze)]
    f = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (0, 3, 2, 1)]
    if zr <= ze: f.append((4, 5, 6, 7)); return v, f
    if roof == "hip":
        i = min(zr - ze, (x1 - x0) / 2 - 1, (y1 - y0) / 2 - 1)
        v += [(x0 + i, y0 + i, zr), (x1 - i, y0 + i, zr), (x1 - i, y1 - i, zr), (x0 + i, y1 - i, zr)]
        f += [(4, 5, 9, 8), (5, 6, 10, 9), (6, 7, 11, 10), (7, 4, 8, 11), (8, 9, 10, 11)]
    else:
        if axis == "x": v += [(x0, (y0 + y1) / 2, zr), (x1, (y0 + y1) / 2, zr)]; f += [(4, 5, 9, 8), (6, 7, 8, 9), (4, 8, 7), (5, 6, 9)]
        else: v += [((x0 + x1) / 2, y0, zr), ((x0 + x1) / 2, y1, zr)]; f += [(7, 4, 8, 9), (5, 6, 9, 8), (4, 5, 8), (6, 7, 9)]
    return v, f

verts, faces = [], []
for name, x0, y0, x1, y1, z0, ze, zr, roof, axis in PARTS:
    v, f = part_mesh(x0, y0, x1, y1, z0, ze, zr, roof, axis); n = len(verts)
    verts += v; faces += [tuple(n + k for k in q) for q in f]
    me = bpy.data.meshes.new(name); me.from_pydata([(x, -y, z) for (x, y, z) in v], [], f); me.update()   # Blender: y = north
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(blx.flat_material("m_" + name, {"hall": (200, 200, 205), "house": (215, 180, 90), "porch": (150, 210, 150)}[name]))

os.makedirs(os.path.dirname(OBJ), exist_ok=True)
with open(OBJ, "w") as fo:
    fo.write("# light proxy: Mercator church complex, room 632 (remake/recipes/proxy_church_632.py). GAME coordinates x east, y south, z up, world units.\n")
    fo.write("# our own geometry measured on the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
    for (x, y, z) in verts: fo.write("v %g %g %g\n" % (x, y, z))
    for q in faces: fo.write("f " + " ".join(str(k + 1) for k in q) + "\n")

blx.ground_plane(size=600).location = (312, -896, 16)
sc, co = blx.game_view(os.path.join(out, "preview.png"), px_per_unit=3, size=(720, 540), target=(312, -896, 60))
bpy.ops.render.render(write_still=True)
print("proxy_church_632: %d vertices, %d faces -> %s" % (len(verts), len(faces), OBJ))
