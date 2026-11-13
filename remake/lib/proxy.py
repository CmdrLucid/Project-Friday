"""Shared parts of the LIGHT PROXY recipes (remake/recipes/proxy_*.py, landstalker/docs/LIGHT_PROXY_PLAN.md 'Blender shapes').
A light proxy is an invisible shape for the game's lighting only (never drawn). Recipes list their parts in GAME coordinates
(x east, y south, z up, world units; one map cell = 16) and call build(); the OBJ goes to landstalker/data/proxies/<name>.obj (our own geometry,
committed) and a preview with the game camera to the recipe's R_OUT folder (local only).
Part = (name, x0, y0, x1, y1, z0, eave, ridge, roof, axis):  roof 'hip' = walls up to eave, 45 deg slopes up to a flat top at ridge ('hip:N': the top starts N units in, steeper);
'gable' = a ridge along axis 'x' or 'y'; 'flat' (or ridge <= eave) = a plain box. The game reads the OBJ as a height field (top per 4 unit column).
A part can also be a dict {'name', 'poly': [(x, y), ...] (convex, counter-clockwise on screen does not matter), 'z0', 'z1'} = a prism with a flat top,
e.g. cylinder(...) for round towers; with a 'top' poly (same length) the top face differs from the bottom: lathe(...) stacks such frustums (round trees)."""
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import blx

def part_mesh(x0, y0, x1, y1, z0, ze, zr, roof, axis):
    """vertices / faces of a box with a hip (flat top, 45 deg sides) or gable roof, game coordinates"""
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze)]
    f = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (0, 3, 2, 1)]
    if zr <= ze or roof == "flat": f.append((4, 5, 6, 7)); return v, f
    if roof.startswith("hip"):   # 'hip' = 45 deg slopes; 'hip:N' = slopes that reach the top N units in from the walls (a steep cushion roof)
        i = min(float(roof[4:]) if roof[3:4] == ":" else zr - ze, (x1 - x0) / 2 - 1, (y1 - y0) / 2 - 1)
        v += [(x0 + i, y0 + i, zr), (x1 - i, y0 + i, zr), (x1 - i, y1 - i, zr), (x0 + i, y1 - i, zr)]
        f += [(4, 5, 9, 8), (5, 6, 10, 9), (6, 7, 11, 10), (7, 4, 8, 11), (8, 9, 10, 11)]
    else:
        if axis == "x": v += [(x0, (y0 + y1) / 2, zr), (x1, (y0 + y1) / 2, zr)]; f += [(4, 5, 9, 8), (6, 7, 8, 9), (4, 8, 7), (5, 6, 9)]
        else: v += [((x0 + x1) / 2, y0, zr), ((x0 + x1) / 2, y1, zr)]; f += [(7, 4, 8, 9), (5, 6, 9, 8), (4, 5, 8), (6, 7, 9)]
    return v, f

def cylinder(name, cx, cy, r, z0, z1, a0=0, a1=360, n=24):
    """round tower as a prism part; a0..a1 in degrees (0 = +x east, 90 = +y south): a0 = -90, a1 = 90 is a half tower standing out of a wall along y"""
    k = max(2, int(n * (a1 - a0) / 360))
    pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / k)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / k))) for i in range(k + 1)]
    if a1 - a0 >= 360: pts = pts[:-1]
    return {"name": name, "poly": [(round(x, 2), round(y, 2)) for x, y in pts], "z0": z0, "z1": z1}

def lathe(name, cx, cy, profile, n=24):
    """a round solid (big tree) from a profile [(z, radius), ...] bottom to top: one frustum part per step (a radius 0 ends in a point)"""
    ring = lambda r: [(round(cx + max(r, 0.25) * math.cos(2 * math.pi * i / n), 2), round(cy + max(r, 0.25) * math.sin(2 * math.pi * i / n), 2)) for i in range(n)]
    return [{"name": "%s_%d" % (name, k), "poly": ring(r0), "top": ring(r1), "z0": z0, "z1": z1} for k, ((z0, r0), (z1, r1)) in enumerate(zip(profile, profile[1:]))]

def extrude_x(name, x0, x1, prof):
    """a straight part along x with a measured cross-section prof = [(y, z), ...] (closed, convex or not, any winding): roof rolls, cornices"""
    n = len(prof); area = sum(prof[i][0] * prof[(i + 1) % n][1] - prof[(i + 1) % n][0] * prof[i][1] for i in range(n))
    if area > 0: prof = prof[::-1]   # clockwise in the (y, z) plane = outward normals with the faces below (checked: right-hand rule, like part_mesh)
    v = [(x0, y, z) for y, z in prof] + [(x1, y, z) for y, z in prof]
    f = [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)] + [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    return {"name": name, "verts": v, "faces": f}

def revolve(name, cx, cy, profile, n=12):
    """ONE closed surface of revolution from a profile [(z, radius), ...] bottom to top (steps allowed: two entries at the same z = a flat ring,
    e.g. the drooping tiers of a pine); bottom and top capped, faces outward (no inner caps like lathe(): clean for back face shadow maps)"""
    ring = lambda z, r: [(cx + max(r, 0.05) * math.cos(2 * math.pi * i / n), cy + max(r, 0.05) * math.sin(2 * math.pi * i / n), z) for i in range(n)]
    v = []; f = []
    for z, r in profile: v += ring(z, r)
    for k in range(len(profile) - 1):
        a, b = k * n, (k + 1) * n
        f += [(a + i, a + (i + 1) % n, b + (i + 1) % n, b + i) for i in range(n)]
    f += [tuple(range(n - 1, -1, -1)), tuple(range((len(profile) - 1) * n, len(profile) * n))]
    return {"name": name, "verts": [(round(x, 3), round(y, 3), z) for x, y, z in v], "faces": f}

def prism_mesh(poly, z0, z1, top=None):
    n = len(poly); v = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in (top or poly)]
    f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)] + [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    return v, f

def build(name, parts, title, colours=None, target=(0, 0, 40), ground_z=16, px_per_unit=3, size=(720, 540)):
    """parts -> Blender objects + landstalker/data/proxies/<name>.obj + preview.png in R_OUT"""
    out = os.environ.get("R_OUT", "/tmp/proxy_" + name); os.makedirs(out, exist_ok=True)
    obj = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "data", "proxies", name + ".obj")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    verts, faces = [], []
    for part in parts:
        if isinstance(part, dict) and "verts" in part: pname = part["name"]; v, f = part["verts"], part["faces"]
        elif isinstance(part, dict): pname = part["name"]; v, f = prism_mesh(part["poly"], part["z0"], part["z1"], part.get("top"))
        else: pname = part[0]; v, f = part_mesh(*part[1:])
        n = len(verts)
        verts += v; faces += [tuple(n + k for k in q) for q in f]
        me = bpy.data.meshes.new(pname); me.from_pydata([(x, -y, z) for (x, y, z) in v], [], f); me.update()   # Blender: y = north
        ob = bpy.data.objects.new(pname, me); bpy.context.scene.collection.objects.link(ob)
        ob.data.materials.append(blx.flat_material("m_" + pname, (colours or {}).get(pname, (200, 200, 205))))
    os.makedirs(os.path.dirname(obj), exist_ok=True)
    with open(obj, "w") as fo:
        fo.write("# light proxy: %s (remake/recipes/proxy_%s.py). GAME coordinates x east, y south, z up, world units.\n" % (title, name))
        fo.write("# our own geometry measured on the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        for (x, y, z) in verts: fo.write("v %g %g %g\n" % (x, y, z))
        for q in faces: fo.write("f " + " ".join(str(k + 1) for k in q) + "\n")
    blx.ground_plane(size=900).location = (target[0], -target[1], ground_z)
    blx.game_view(os.path.join(out, "preview.png"), px_per_unit=px_per_unit, size=size, target=(target[0], -target[1], target[2]))
    bpy.ops.render.render(write_still=True)
    print("proxy_%s: %d vertices, %d faces -> %s" % (name, len(verts), len(faces), obj))
