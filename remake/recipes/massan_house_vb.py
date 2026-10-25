"""MASSAN HOUSE A, VARIANT B (2026-10-25, 'modern remake' study 2 of 3): VOXEL house (lib/massan_a.py: voxels()).
Second pass ('C am besten bisher, ausser wir kriegen B noch sauberer'): voxel edge R_VS (default 0.5 = 2 x 2 voxels per original pixel, read from the
Scale2x picture), clean hidden sides, real light.
Colours: a voxel the original camera sees (the front one along its view ray, direction (1, 1, 1) in game units) takes the ORIGINAL PIXEL it covers.
Hidden voxels: logs = the log swatch of variant A by angle around the log + position along it; roof = the thatch swatch of variant A (top planar);
posts / sticks = the mirrored seen voxel (positions are symmetric), else a seen voxel of the same kind at the same height; core / door = dark.
R_LIT=1 (default): lit material (sun, soft shadows, ambient occlusion) on a soft ground; R_LIT=0: unlit, fixed shade per face direction, pixel ground.
R_COL = orig (default: the picture as it is) / dedither (the picture smoothed inside areas of similar colour, then snapped back to its own palette:
the dither checkers turn into flat shades, black seams stay) / clean (every voxel coloured by a pattern per kind in the original's palette: logs by the
angle around the log, posts lit on the south east side, thatch in courses with strands; only the skull keeps the picture).  Output: <out>[_mode]/.
Run: python3 remake/tools/build_asset.py massan_house_vb   (R_COL=clean python3 remake/tools/build_asset.py massan_house_vb)"""
import bpy, sys, os, math
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx, massan_a as H
MODE = os.environ.get("R_COL", "orig")
out = os.environ.get("R_OUT", "/tmp/massan_house_vb").rstrip("/") + ("" if MODE == "orig" else "_" + MODE); os.makedirs(out, exist_ok=True)
pic_dir = os.path.expanduser(os.environ.get("R_PIC", "~/.landstalker_remake/rooms/592_houseA"))
VS = float(os.environ.get("R_VS", "0.5")); LIT = os.environ.get("R_LIT", "1") == "1"
bpy.ops.wm.read_factory_settings(use_empty=True)
pic = H.Picture(pic_dir); full = H.Picture(pic_dir, "full.png"); M_ = H.MAT
def dedither(a, rad=3, thr=0.5):
    """edge preserving smoothing (only neighbours of similar colour count), then back to the picture's own palette."""
    rgb = a[..., :3]; al = a[..., 3] > 0.5; h, w = al.shape
    acc = np.zeros_like(rgb); cnt = np.zeros((h, w, 1), np.float32)
    P = np.pad(rgb, ((rad, rad), (rad, rad), (0, 0))); PA = np.pad(al, rad)
    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            nb = P[rad + dy:rad + dy + h, rad + dx:rad + dx + w]; na = PA[rad + dy:rad + dy + h, rad + dx:rad + dx + w]
            wgt = (na & (np.sqrt(((nb - rgb) ** 2).sum(-1)) < thr)).astype(np.float32)[..., None]
            acc += nb * wgt; cnt += wgt
    mean = acc / np.maximum(cnt, 1)
    pal = np.unique((rgb[al] * 255).round().astype(np.int32), axis=0).astype(np.float32) / 255
    out = a.copy(); m = mean[al]
    best = np.argmin(((m[:, None, :] - pal[None, :, :]) ** 2).sum(-1), axis=1); out[..., :3][al] = pal[best]
    return out
if MODE == "dedither": pic.a = dedither(pic.a)
V, LS, (ox, oy, oz) = H.voxels(VS); nx, ny, nz = V.shape
occ = V > 0
# keep only voxels with an empty neighbour (the inside is never drawn)
pad = np.zeros((nx + 2, ny + 2, nz + 2), bool); pad[1:-1, 1:-1, 1:-1] = occ
inner = pad[2:, 1:-1, 1:-1] & pad[:-2, 1:-1, 1:-1] & pad[1:-1, 2:, 1:-1] & pad[1:-1, :-2, 1:-1] & pad[1:-1, 1:-1, 2:] & pad[1:-1, 1:-1, :-2]
# ---- which voxels does the original camera see? (all occupied voxels occlude) -----------------------------------------------------------------
ai = np.argwhere(occ); ka = ai[:, 0] - ai[:, 1]; kb = ai[:, 0] + ai[:, 1] - 2 * ai[:, 2]; dep = ai.sum(1)
key = (ka - ka.min()) * (kb.max() - kb.min() + 1) + (kb - kb.min())
best = np.full(key.max() + 1, -10 ** 9); np.maximum.at(best, key, dep)
seen_all = np.zeros(V.shape, bool); seen_all[tuple(ai[dep == best[key]].T)] = True
surf = occ & ~inner
idx = np.argwhere(surf); X = ox + VS * (idx[:, 0] + 0.5); Y = oy + VS * (idx[:, 1] + 0.5); Z = oz + VS * (idx[:, 2] + 0.5)
mat = V[surf]; side = LS[surf]; seen = seen_all[surf]
px = pic.at_many(X, Y, Z)
r, g, b = px[:, 0], px[:, 1], px[:, 2]
greenish = g > r + 0.05; yellowish = (r > 0.45) & (g > 0.35) & (b < 0.5) & ~greenish
good = seen & (px[:, 3] > 0.5)
good &= ~((mat == M_["roof"]) & greenish)
good &= ~(np.isin(mat, [M_["log"], M_["post"]]) & yellowish & (Z > H.ZE - 6))
col = np.zeros((len(X), 3), np.float32); have = good.copy(); col[good] = px[good, :3]
sign = mat == M_["sign"]; drop = sign & ~(seen & (px[:, 3] > 0.5) & (r > 0.35) & (np.abs(r - b) < 0.15))
# ---- hidden logs: variant A's log swatch (angle around the log, position along it) --------------------------------------------------------------
hl = ~have & (mat == M_["log"])
ns = np.isin(side, (1, 2)); sgn = np.where((side == 1) | (side == 3), 1.0, -1.0)
cen = np.where(side == 1, H.Y1 - H.RL, np.where(side == 2, H.Y0 + H.RL, np.where(side == 3, H.X1 - H.RL, H.X0 + H.RL)))
outw = np.where(ns, Y - cen, X - cen) * sgn; along = np.where(ns, X, Y)
logz = np.array(H.LOG_Z, np.float32); zc = logz[np.argmin(np.abs(Z[:, None] - logz[None, :]), axis=1)]
ang = np.abs(np.arctan2(outw, Z - zc))                                                  # 0 = top of the log, pi/2 = outside, pi = bottom
sw = pic.at_many(308.5 + np.mod(along - H.X0, 33.0), np.full(len(X), H.Y1), H.LOG_Z[1] + 3.0 - 7.0 * ang / math.pi)
col[hl] = sw[hl, :3]; have |= hl
# ---- hidden roof: variant A's thatch swatch, top planar ------------------------------------------------------------------------------------------
hr = ~have & (mat == M_["roof"])
tf, tw, th = H.thatch_texture(pic, 2)
timg = np.array([[tf(tx, ty) for tx in range(tw)] for ty in range(th)], np.float32) / 255.0
tx = np.clip(((X - (H.CX - H.HX)) * 2).astype(int), 0, tw - 1); ty = np.clip(((Y - (H.CY - H.HX)) * 2).astype(int), 0, th - 1)
col[hr] = timg[ty[hr], tx[hr]] * np.where(Z[hr] < H.ZE - 1, 0.7, 1.0)[:, None]; have |= hr
# ---- the rest: mirrored seen voxel of the same kind, else same kind at the same height ----------------------------------------------------------
cell = lambda x, y, z: (int(math.floor((x - ox) / VS)), int(math.floor((y - oy) / VS)), int(math.floor((z - oz) / VS)))
lut = {cell(X[i], Y[i], Z[i]): i for i in np.nonzero(good)[0]}
byz = {}
for i in np.nonzero(good)[0]: byz.setdefault((int(mat[i]), int(Z[i])), []).append(i)
rng = np.random.default_rng(7)
for i in np.nonzero(~have)[0]:
    m = int(mat[i])
    if m in (M_["core"], M_["hole"], M_["door"]): col[i] = (0.02, 0.06, 0.03); continue
    mx, my = 2 * H.CX - X[i], 2 * H.CY - Y[i]
    for q in ((X[i], my), (mx, Y[i]), (mx, my)):
        j = lut.get(cell(q[0], q[1], Z[i]))
        if j is not None and mat[j] == m: col[i] = col[j]; break
    else:
        for dz in (0, 1, -1, 2, -2, 4, -4):
            lst = byz.get((m, int(Z[i]) + dz))
            if lst: col[i] = col[lst[rng.integers(len(lst))]]; break
        else: col[i] = (0.55, 0.36, 0.16)
# ---- R_COL=clean: patterns per kind in the original's palette ------------------------------------------------------------------------------------
if MODE == "clean":
    pal = lambda l: np.array(l, np.float32) / 255
    GR = pal([(0, 32, 16), (0, 72, 36), (30, 96, 18), (60, 126, 0), (84, 144, 18)])
    BR = pal([(40, 32, 14), (72, 72, 36), (110, 86, 30), (144, 108, 36), (182, 126, 54), (216, 144, 72), (232, 176, 110), (232, 228, 210)])
    TH = pal([(72, 56, 0), (108, 80, 0), (144, 108, 0), (180, 144, 0), (216, 180, 0), (232, 200, 40), (240, 232, 200)])
    def hh(*k):
        v = sum(np.asarray(x, np.float64) * c for x, c in zip(k, (12.9898, 78.233, 37.719, 4.581)))
        return np.modf(np.abs(np.sin(v) * 43758.5453))[0]
    keepsign = mat == M_["sign"]
    c = np.zeros((len(X), 3), np.float32)
    # logs: lit top edge, moss green front with patches, darker underside, black seam; protruding ends show rings
    lg = mat == M_["log"]; n1 = hh(np.floor(along / 3), np.floor(Z), side); n2 = hh(np.floor(along), np.floor(Z * 2), side, 3)
    moss = np.where(n1 > 0.62, 4, np.where(n1 < 0.18, 2, 3)); moss = np.where(n2 > 0.93, -5, moss)            # -5 = a light bark speck
    idxc = np.where(ang < 0.35, -6, np.where(ang < 0.7, np.where(n2 > 0.7, -5, 4), np.where(ang < 1.9, moss, np.where(ang < 2.5, 1 + (n2 > 0.5), 0))))
    c[lg] = np.where((idxc < 0)[:, None], BR[np.clip(-idxc, 0, 7)], GR[np.clip(idxc, 0, 4)])[lg]
    L0 = np.where(ns, H.X0, H.Y0); L1 = np.where(ns, H.X1, H.Y1); stub = lg & ((along < L0 - 0.2) | (along > L1 + 0.2))
    rr = np.sqrt(outw ** 2 + (Z - zc) ** 2)
    c[stub] = np.where((rr > 3.0)[:, None], GR[1], np.where((np.floor(rr) % 2 == 0)[:, None], BR[4], BR[3]))[stub]
    # posts / lintel / sticks / ring: lit on the south east side
    wood = np.isin(mat, (M_["post"], M_["stick"], M_["ring"]))
    pc = np.array([H.wall_pos(sd, a, H.POST_R - 0.6, 0)[:2] for sd, al in H.POSTS.items() for a in al], np.float32)
    dpx = X[:, None] - pc[None, :, 0]; dpy = Y[:, None] - pc[None, :, 1]; k = np.argmin(dpx ** 2 + dpy ** 2, axis=1)
    dx_, dy_ = dpx[np.arange(len(X)), k], dpy[np.arange(len(X)), k]; nearpost = (dx_ ** 2 + dy_ ** 2) < (H.POST_R + 0.8) ** 2
    lit = (dx_ + dy_) / np.sqrt(2) / np.maximum(np.sqrt(dx_ ** 2 + dy_ ** 2), 1e-3)
    ng = hh(np.floor(Z / 2), k, 7)
    cpost = np.where((lit > 0.995)[:, None] & (ng > 0.5)[:, None], BR[7], np.where((lit > 0.75)[:, None], BR[6], np.where((lit > 0.1)[:, None], np.where((ng > 0.3)[:, None], BR[5], BR[4]), np.where((lit > -0.4)[:, None], BR[3], BR[2]))))
    cwood = np.where((hh(np.floor(X), np.floor(Y), np.floor(Z), 9) > 0.5)[:, None], BR[4], BR[5])
    c[wood] = np.where(nearpost[:, None] & (mat == M_["post"])[:, None], cpost, cwood)[wood]
    # thatch: courses every 5 units down the slope, strands across, light tips, shadow under the next course; darker underside and eave
    rf = mat == M_["roof"]
    tt = np.minimum.reduce([X - (H.CX - H.HX), (H.CX + H.HX) - X, Y - (H.CY - H.HX), (H.CY + H.HX) - Y])
    aa = np.where(np.abs(X - H.CX) > np.abs(Y - H.CY), Y, X)
    wob = 0.8 * np.sin(aa * 0.9) + 0.6 * np.sin(aa * 2.3 + tt * 0.4)
    course = np.floor((tt + wob) / 5.0); fr = np.modf((tt + wob) / 5.0)[0]; st = hh(np.floor(aa * 1.5), course, 11); sp = hh(np.floor(X * 2), np.floor(Y * 2), 12)
    ti = np.where(fr < 0.22, np.where(st > 0.45, 5, 6), np.where(fr > 0.8, 2, np.where(st > 0.85, 5, np.where(st > 0.3, 4, 3))))
    ti = np.where(sp > 0.97, 6, ti); ti = np.where(Z < H.ZE - 1, 1, np.where(tt < 1.0, 2, ti))
    c[rf] = TH[ti][rf]
    dk = np.isin(mat, (M_["core"], M_["hole"], M_["door"])); c[dk] = (0.02, 0.06, 0.03)
    c[keepsign] = col[keepsign]; col = c
# ---- mesh of the exposed faces -------------------------------------------------------------------------------------------------------------------
keep = ~drop; idx = idx[keep]; col = col[keep]
occ2 = occ.copy(); dropped = np.argwhere(surf)[drop]; occ2[tuple(dropped.T)] = False
pad = np.zeros((nx + 2, ny + 2, nz + 2), bool); pad[1:-1, 1:-1, 1:-1] = occ2
SHADE = {(0, 0, 1): 1.0, (0, 0, -1): 0.6, (0, 1, 0): 0.93, (0, -1, 0): 0.8, (1, 0, 0): 0.88, (-1, 0, 0): 0.84}     # unlit only; game +y = south
CORN = {(0, 0, 1): [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)], (0, 0, -1): [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)],
        (1, 0, 0): [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)], (-1, 0, 0): [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)],
        (0, 1, 0): [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)], (0, -1, 0): [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]}
quads = []; cols = []
for dvec, corners in CORN.items():
    dx, dy, dz = dvec
    sel = ~pad[1 + idx[:, 0] + dx, 1 + idx[:, 1] + dy, 1 + idx[:, 2] + dz]
    base = idx[sel]
    quads.append(np.stack([base + np.array(c) for c in corners], axis=1))
    cols.append(np.clip(col[sel] * (1.0 if LIT else SHADE[dvec]), 0, 1))
Q = np.concatenate(quads, axis=0).astype(np.float32) * VS + np.array((ox, oy, oz), np.float32)    # (faces, 4, 3) game coordinates
nf = len(Q); Q[:, :, 1] = -Q[:, :, 1]; Q = Q[:, ::-1, :]                                          # game y south -> Blender y north; keep faces outward
P = Q.reshape(-1, 3); C = np.repeat(np.concatenate(cols, axis=0), 4, axis=0)
lin = np.where(C <= 0.04045, C / 12.92, ((C + 0.055) / 1.055) ** 2.4)
me = bpy.data.meshes.new("massan_house_vb"); me.vertices.add(len(P)); me.vertices.foreach_set("co", P.ravel())
me.loops.add(len(P)); me.loops.foreach_set("vertex_index", np.arange(len(P)))
me.polygons.add(nf); me.polygons.foreach_set("loop_start", np.arange(0, len(P), 4)); me.polygons.foreach_set("loop_total", np.full(nf, 4))
me.update(calc_edges=True)
ca = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
ca.data.foreach_set("color", np.concatenate([lin, np.ones((len(P), 1))], axis=1).astype(np.float32).ravel())
m = bpy.data.materials.new("voxel"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
o = nt.nodes.new("ShaderNodeOutputMaterial"); at = nt.nodes.new("ShaderNodeVertexColor"); at.layer_name = "Col"
if LIT:
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.inputs["Roughness"].default_value = 0.85
    nt.links.new(at.outputs["Color"], bs.inputs["Base Color"]); nt.links.new(bs.outputs["BSDF"], o.inputs["Surface"])
else:
    em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(at.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs["Emission"], o.inputs["Surface"])
me.materials.append(m)
ob = bpy.data.objects.new("massan_house_vb", me); bpy.context.scene.collection.objects.link(ob)
print("voxel size", VS, "faces:", nf, "surface voxels:", len(idx))
bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "massan_house_vb.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
# ---- ground ------------------------------------------------------------------------------------------------------------------------------------------
import bmesh
gme = bpy.data.meshes.new("ground"); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UV"); s = 260
f = bm.faces.new([bm.verts.new(H.G(H.CX + a, H.CY + c, 0)) for a, c in ((-s, s), (s, s), (s, -s), (-s, -s))])
for l in f.loops: l[uvl].uv = (l.vert.co.x / 64, l.vert.co.y / 64)
bm.to_mesh(gme); bm.free()
if LIT:                                                                          # soft ground like variant C
    gm = bpy.data.materials.new("ground"); gm.use_nodes = True; gnt = gm.node_tree; gb = gnt.nodes["Principled BSDF"]; gb.inputs["Roughness"].default_value = 1.0
    nz_ = gnt.nodes.new("ShaderNodeTexNoise"); nz_.inputs["Scale"].default_value = 0.02; nz_.inputs["Detail"].default_value = 6.0
    tc = gnt.nodes.new("ShaderNodeTexCoord"); rp = gnt.nodes.new("ShaderNodeValToRGB"); rp.color_ramp.elements[0].position = 0.35; rp.color_ramp.elements[1].position = 0.65
    rp.color_ramp.elements[0].color = (0.18, 0.11, 0.035, 1); rp.color_ramp.elements[1].color = (0.10, 0.17, 0.025, 1)
    gnt.links.new(tc.outputs["Object"], nz_.inputs["Vector"]); gnt.links.new(nz_.outputs["Fac"], rp.inputs["Fac"]); gnt.links.new(rp.outputs["Color"], gb.inputs["Base Color"])
else:
    blx.PIXEL = True; gf, gw, gh = H.ground_texture(full, 64); gm = blx.material("dirt", blx.px_image("dirt", gf, gw, gh))
gme.materials.append(gm); bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", gme))
blx.PIXEL = not LIT
H.render_set(out, px=float(os.environ.get("R_PX", "2")), outlines=False, dof=LIT, modern="std" if LIT else False)
print("massan_house_vb done ->", out)
