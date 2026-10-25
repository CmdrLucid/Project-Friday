"""MASSAN HOUSE A, VARIANT B (2026-10-25, 'modern remake' study 2 of 3): VOXEL house, 1 voxel = 1 game pixel (lib/massan_a.py: voxels()).
Colours: a voxel the original camera sees (the front one along its view ray, direction (1, 1, 1) in game units) takes the ORIGINAL PIXEL it covers;
a hidden voxel takes the colour of a seen voxel of the same kind: mirrored north <-> south / west <-> east (never into the door, the sign or the window),
else a seen voxel of the same kind at the same height.  Faces get a mild fixed shade per direction so the blocks read as 3D.  No outlines.
Run: python3 remake/tools/build_asset.py massan_house_vb"""
import bpy, sys, os, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, massan_a as H
out = os.environ.get("R_OUT", "/tmp/massan_house_vb"); os.makedirs(out, exist_ok=True)
pic_dir = os.path.expanduser(os.environ.get("R_PIC", "~/.landstalker_remake/rooms/592_houseA"))
bpy.ops.wm.read_factory_settings(use_empty=True)
pic = H.Picture(pic_dir); full = H.Picture(pic_dir, "full.png"); M_ = H.MAT
V, (ox, oy, oz) = H.voxels(); nx, ny, nz = V.shape
occ = V > 0
idx = np.argwhere(occ); X = idx[:, 0] + ox + 0.5; Y = idx[:, 1] + oy + 0.5; Z = idx[:, 2] + oz + 0.5; mat = V[occ]
# ---- which voxels does the original camera see? -----------------------------------------------------------------------------------------------
ka = (X - Y).astype(int); kb = (X + Y - 2 * Z).astype(int); depth = X + Y + Z
key = (ka - ka.min()) * (kb.max() - kb.min() + 1) + (kb - kb.min())
best = np.full(key.max() + 1, -1e9); np.maximum.at(best, key, depth); seen = depth >= best[key] - 1e-6
U = ((ka + 1184 - pic.U0) * pic.K).astype(int); Vv = ((kb / 2.0 - pic.V0) * pic.K).astype(int)
ok = seen & (U >= 0) & (U < pic.w) & (Vv >= 0) & (Vv < pic.h)
col = np.zeros((len(X), 3), np.float32); have = np.zeros(len(X), bool)
px = pic.a[np.clip(Vv, 0, pic.h - 1), np.clip(U, 0, pic.w - 1)]
good = ok & (px[:, 3] > 0.5)
# a seen voxel must show a pixel that fits its kind (no tree / sky pixel on the roof, no straw on a log)
r, g, b = px[:, 0], px[:, 1], px[:, 2]
greenish = g > r + 0.05; yellowish = (r > 0.45) & (g > 0.35) & (b < 0.5) & ~greenish
good &= ~((mat == M_["roof"]) & greenish)
good &= ~(np.isin(mat, [M_["log"], M_["post"]]) & yellowish & (Z > H.ZE - 6))
col[good] = px[good, :3]; have[good] = True
# the sign board keeps only the skull pixels the picture shows
sign = mat == M_["sign"]; drop = sign & ~(seen & (px[:, 3] > 0.5) & (px[:, 0] > 0.35) & (np.abs(px[:, 0] - px[:, 2]) < 0.15))
# ---- hidden voxels: mirrored / same kind -------------------------------------------------------------------------------------------------------
lut = {}
for i in np.nonzero(have)[0]: lut[(int(X[i]), int(Y[i]), int(Z[i]))] = i
def forbidden(x, y, z):
    d = H.DOOR; w = H.WINDOW
    if x > H.X1 - 2 * H.RL - 2 and d["a0"] - 6 < y < d["a1"] + 6 and z < 50: return True
    if y > H.Y1 - 2 * H.RL - 2 and abs(x - w["a"]) < w["R"] + 3 and abs(z - w["z"]) < w["R"] + 3: return True
    return False
rng = np.random.default_rng(7)
top = {}                                                                       # roof: the top seen voxel of every column (straw, never a dark step edge)
for i in np.nonzero(have & (mat == M_["roof"]))[0]:
    k = (int(X[i]), int(Y[i]))
    if k not in top or Z[i] > Z[top[k]]: top[k] = i
byz = {}
for i in np.nonzero(have)[0]:
    if mat[i] == M_["roof"] and col[i].sum() < 1.0: continue                 # no dark eave pixels as stand-ins on the roof
    byz.setdefault((int(mat[i]), int(Z[i])), []).append(i)
for i in np.nonzero(~have)[0]:
    x, y, z, m = int(X[i]), int(Y[i]), int(Z[i]), int(mat[i])
    if m in (M_["core"], M_["hole"], M_["door"]): col[i] = (0.02, 0.06, 0.03); continue
    my = int(math.floor(2 * H.CY - Y[i])); mx = int(math.floor(2 * H.CX - X[i]))           # mirror the voxel CENTRE
    if m == M_["roof"]:
        j = next((top[k] for k in ((x, my), (mx, y), (mx, my)) if k in top), None)
        if j is not None:
            if col[j].sum() < 1.1:                                                # dark course shadows would line up into stripes on the back
                lst = byz.get((m, z)) or byz.get((m, z - 1)) or [j]; j = lst[rng.integers(len(lst))]
            col[i] = col[j]; continue
    qs = [(x, my, z), (mx, y, z), (mx, my, z), (x, my - 16, z), (x - 16, my, z)]
    for q in qs:
        j = lut.get(q)
        if j is not None and mat[j] == m and not forbidden(*q): col[i] = col[j]; break
    else:
        for dz in (0, 1, -1, 2, -2, 3, -3, 8, -8):
            lst = byz.get((m, z + dz))
            if lst: col[i] = col[lst[rng.integers(len(lst))]] * (0.85 if m == M_["roof"] and z < H.ZE - 1 else 1.0); break
        else: col[i] = (1.0, 0.0, 1.0) if os.environ.get("R_DBG") else (0.3, 0.25, 0.1)
keep = ~drop
# ---- mesh of the exposed faces -----------------------------------------------------------------------------------------------------------------
occ2 = occ.copy(); occ2[tuple(idx[drop].T)] = False
idx = idx[keep]; col = col[keep]
SHADE = {(0, 0, 1): 1.0, (0, 0, -1): 0.6, (0, 1, 0): 0.93, (0, -1, 0): 0.8, (1, 0, 0): 0.88, (-1, 0, 0): 0.84}     # game directions: +y = south
CORN = {(0, 0, 1): [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)], (0, 0, -1): [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)],
        (1, 0, 0): [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)], (-1, 0, 0): [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)],
        (0, 1, 0): [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)], (0, -1, 0): [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]}
pad = np.zeros((nx + 2, ny + 2, nz + 2), bool); pad[1:-1, 1:-1, 1:-1] = occ2
verts = []; cols = []
for dvec, corners in CORN.items():
    dx, dy, dz = dvec
    nb = pad[1 + idx[:, 0] + dx, 1 + idx[:, 1] + dy, 1 + idx[:, 2] + dz]
    sel = ~nb; base = idx[sel] + np.array((ox, oy, oz)); c = np.clip(col[sel] * SHADE[dvec], 0, 1)
    for cx, cy, cz in corners: verts.append(base + np.array((cx, cy, cz)))
    cols.append(c)
nf = sum(len(c) for c in cols)
P = np.concatenate([np.stack(verts[k * 4:(k + 1) * 4], axis=1) for k in range(6)], axis=0).reshape(-1, 3).astype(np.float32)
P[:, 1] = -P[:, 1]                                     # game y south -> Blender y north (faces flip: fixed below by flipping the loop order)
C = np.repeat(np.concatenate(cols, axis=0), 4, axis=0)
lin = np.where(C <= 0.04045, C / 12.92, ((C + 0.055) / 1.055) ** 2.4)
me = bpy.data.meshes.new("massan_house_vb"); me.vertices.add(len(P)); me.vertices.foreach_set("co", P.ravel())
me.loops.add(len(P)); me.loops.foreach_set("vertex_index", np.arange(len(P))[::-1].copy().reshape(-1, 4)[::-1].ravel())
me.polygons.add(nf); me.polygons.foreach_set("loop_start", np.arange(0, len(P), 4)); me.polygons.foreach_set("loop_total", np.full(nf, 4))
me.update(calc_edges=True)
ca = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
li = np.empty(len(P), np.int64); me.loops.foreach_get("vertex_index", li)
ca.data.foreach_set("color", np.concatenate([lin[li], np.ones((len(P), 1))], axis=1).astype(np.float32).ravel())
m = bpy.data.materials.new("voxel"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
o = nt.nodes.new("ShaderNodeOutputMaterial"); at = nt.nodes.new("ShaderNodeVertexColor"); at.layer_name = "Col"; em = nt.nodes.new("ShaderNodeEmission")
nt.links.new(at.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs["Emission"], o.inputs["Surface"]); me.materials.append(m)
ob = bpy.data.objects.new("massan_house_vb", me); bpy.context.scene.collection.objects.link(ob)
print("voxel faces:", nf, "voxels:", len(idx))
bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "massan_house_vb.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
# ground: voxel-sized dirt squares from the picture's ground
import bmesh
gf, gw, gh = H.ground_texture(full, 64); blx.PIXEL = True
gm = blx.material("dirt", blx.px_image("dirt", gf, gw, gh)); gme = bpy.data.meshes.new("ground"); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UV"); s = 200
f = bm.faces.new([bm.verts.new(H.G(H.CX + a, H.CY + b, 0)) for a, b in ((-s, s), (s, s), (s, -s), (-s, -s))])
for l in f.loops: l[uvl].uv = (l.vert.co.x / 64, l.vert.co.y / 64)
bm.to_mesh(gme); bm.free(); gme.materials.append(gm); bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", gme))
H.render_set(out, px=float(os.environ.get("R_PX", "2")), outlines=False)
print("massan_house_vb done ->", out)
