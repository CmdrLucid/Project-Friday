"""ASSET 5d (style C, 2026-10-25): CLIFFS as slopes, built from the room's height map (used by recipes/room_c.py).
The height map's cliff columns (7..11 steps) are collision walls; the original picture draws the Massan mountain as a SLOPE of dark olive rock with
ochre streaks, light ridges, dark crevices and moss, and the plateau edges as steep grassy earth banks (docs/FORMATS.md, 2026-10-25).
Built here on a fine grid (STEP units) over the room + MARGIN cells:
  rock  (cliff cells, and outside cells whose nearest room cell is a cliff): rises from the nearest ground with K_ROCK per unit, at most to the
        cliff's height map height; beyond the room the mountain goes on rising (like the original, where it runs out of the picture)
  bank  (outside cells next to ground): falls from the edge of the ground with K_BANK per unit down to BOTTOM
  relief: rounded bumps (sum of sines with random phases) as z displacement, fading out within FADE of the ground so the slope meets the flat
        ground without a step; OUTCROPS = broad light rock patches elongated down the slope, raised, written as colour attribute 'ridge'
        (cmat.rock_mat: light rock where ridge > 0).
Returns the mesh objects and a height function (for trees standing on the slopes)."""
import math, random
import numpy as np
import bpy, bmesh
import cmat
from massan_a import G
import os
STYLE = os.environ.get("R_ROCK", "A"); STEP = float(os.environ.get("R_ROCK_STEP", "2")); MARGIN = 6; K_ROCK = 1.5; K_BANK = 2.4; FADE = 10.0; AMP = 5.0

STONE = dict(dark=(86, 78, 66), olive=(140, 128, 110), ochre=(162, 134, 98), light=(206, 194, 170), moss=((42, 70, 32), (76, 100, 40)))
def rock_material(name):
    """user 2026-10-25: the original's olive / ochre rock is a PALETTE limit and does not read as rock in 3D -> deliberately real stone colours
    (warm grey-brown sandstone, light faces, dark joints, muted moss); R_ROCK_COL=orig keeps the palette colours."""
    return cmat.rock_mat(name) if os.environ.get("R_ROCK_COL", "stone") == "orig" else cmat.rock_mat(name, **STONE)

def relief(X, Y, seed=5):
    rr = random.Random(seed); v = np.zeros_like(X)
    for k in range(7):
        f = 0.03 * (1.6 ** k); a = rr.random() * math.pi; ph = rr.random() * 6.28; w = 1.0 / (1.5 ** k)
        v += w * np.sin(f * (X * math.cos(a) + Y * math.sin(a)) + ph + 1.5 * np.sin(0.02 * (X * math.sin(a) - Y * math.cos(a))))
    return v / 2.2

def build(cells, top, rock, O, bottom, name="cliffs"):
    """cells: all room cells; top: {cell: flat top} of the cells NOT in rock; rock: {cell: height map top} of the cliff cells."""
    xs = [k[0] for k in cells]; ys = [k[1] for k in cells]
    gx0, gy0 = 16 * (min(xs) - MARGIN) + O, 16 * (min(ys) - MARGIN) + O
    nx = int((16 * (max(xs) - min(xs) + 1 + 2 * MARGIN)) / STEP); ny = int((16 * (max(ys) - min(ys) + 1 + 2 * MARGIN)) / STEP)
    X, Y = np.meshgrid(gx0 + STEP * np.arange(nx + 1), gy0 + STEP * np.arange(ny + 1), indexing="ij")
    P = np.stack([X.ravel(), Y.ravel()], 1)
    ground = sorted(top); gc = np.array([(16 * x + O + 8, 16 * y + O + 8) for x, y in ground], float); gt = np.array([top[k] for k in ground])
    cl = sorted(rock); cc = np.array([(16 * x + O + 8, 16 * y + O + 8) for x, y in cl], float); ch = np.array([rock[k] for k in cl])
    front = np.zeros(len(P), bool); cone = np.empty(len(P)); dg = np.empty(len(P)); tg = np.empty(len(P)); dc = np.empty(len(P)); hc = np.empty(len(P))
    for s in range(0, len(P), 3000):
        p = P[s:s + 3000]
        d = np.hypot(np.maximum(np.abs(p[:, None, 0] - gc[None, :, 0]) - 8, 0), np.maximum(np.abs(p[:, None, 1] - gc[None, :, 1]) - 8, 0))
        cone[s:s + 3000] = (gt[None, :] + K_ROCK * d).min(1); j = d.argmin(1); dg[s:s + 3000] = d[np.arange(len(p)), j]; tg[s:s + 3000] = gt[j]
        if len(cc):
            e = np.hypot(np.maximum(np.abs(p[:, None, 0] - cc[None, :, 0]) - 8, 0), np.maximum(np.abs(p[:, None, 1] - cc[None, :, 1]) - 8, 0))
            i = e.argmin(1); dc[s:s + 3000] = e[np.arange(len(p)), i]; hc[s:s + 3000] = ch[i]
            front[s:s + 3000] = (p[:, 0] > cc[i, 0] + 8) | (p[:, 1] > cc[i, 1] + 8)   # outside in FRONT of that cliff cell (south / east = towards the viewer)
        else: dc[s:s + 3000] = 1e9; hc[s:s + 3000] = 0
    cx = np.floor((P[:, 0] - O) / 16).astype(int); cy = np.floor((P[:, 1] - O) / 16).astype(int)
    inroom = np.array([(a, b) in cells for a, b in zip(cx, cy)]); incliff = np.array([(a, b) in rock for a, b in zip(cx, cy)])
    is_rock = incliff | (~inroom & (dc < dg))
    H = np.where(is_rock, np.minimum(hc, cone), np.maximum(tg - K_BANK * dg, bottom))
    out_front = is_rock & ~incliff & front                                       # the mountain runs on behind the room only; in front it drops like a bank
    H = np.where(out_front, np.maximum(np.minimum(hc, cone) - K_BANK * dc, bottom), H)
    steep = np.where(is_rock, (cone < hc - 2).astype(float) * 1.0 + 0.35, 1.0)        # flat mountain tops get less relief
    live = np.where(H > bottom + 1, 1.0, 0.0); fade = np.clip(dg / FADE, 0, 1)
    H2 = H.reshape(nx + 1, ny + 1); gxv, gyv = np.gradient(H2)                  # fall line = the smoothed gradient of the plain slope
    for _ in range(int(12 / STEP) + 2):
        gxv = (gxv + np.roll(gxv, 1, 0) + np.roll(gxv, -1, 0) + np.roll(gxv, 1, 1) + np.roll(gxv, -1, 1)) / 5
        gyv = (gyv + np.roll(gyv, 1, 0) + np.roll(gyv, -1, 0) + np.roll(gyv, 1, 1) + np.roll(gyv, -1, 1)) / 5
    gl = np.hypot(gxv, gyv) + 1e-6; ux, uy = (gxv / gl).ravel(), (gyv / gl).ravel()
    t = P[:, 0] * (-uy) + P[:, 1] * ux; along = P[:, 0] * ux + P[:, 1] * uy        # across / along the fall line
    ridge = np.zeros(len(P)); boulders = []; flat = False
    w = steep * fade * live                                                      # where the rock form may act
    if STYLE == "A":
        # A = FACETED ROCK: every Voronoi cell (seeds on a jittered 15 unit lattice) is one flat plane, the plain slope's tangent plane at the seed,
        # tilted at random: flat faces with sharp edges; plus strata = soft terraces every 11 units (ledges catch moss); flat shading
        S = 15.0; rr = np.random.default_rng(3)
        li, lj = np.floor(P[:, 0] / S).astype(int), np.floor(P[:, 1] / S).astype(int)
        best = np.full(len(P), 1e9); val = np.zeros(len(P)); fid = np.zeros(len(P))
        Hf = H.reshape(nx + 1, ny + 1)
        def jit(a, b, k): return ((a * 73856093) ^ (b * 19349663) ^ (k * 83492791)) % 1000 / 1000.0
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                a_, b_ = li + da, lj + db
                sx_ = (a_ + 0.15 + 0.7 * jit(a_, b_, 1)) * S; sy_ = (b_ + 0.15 + 0.7 * jit(a_, b_, 2)) * S
                d2 = (P[:, 0] - sx_) ** 2 + (P[:, 1] - sy_) ** 2
                ii = np.clip(((sx_ - gx0) / STEP).astype(int), 0, nx); jj = np.clip(((sy_ - gy0) / STEP).astype(int), 0, ny)
                hs = Hf[ii, jj]; gx_s = gxv[ii, jj] / STEP; gy_s = gyv[ii, jj] / STEP
                tx_ = (jit(a_, b_, 3) - 0.5) * 1.4; ty_ = (jit(a_, b_, 4) - 0.5) * 1.4
                plane = hs + (gx_s + tx_) * (P[:, 0] - sx_) + (gy_s + ty_) * (P[:, 1] - sy_) + (jit(a_, b_, 5) - 0.5) * 6
                m = d2 < best; best = np.where(m, d2, best); val = np.where(m, plane, val); fid = np.where(m, jit(a_, b_, 6), fid)
        dz = np.clip(val - H, -10, 10)
        Hs = H + dz * w
        terr = 11.0 * np.round(Hs / 11.0); Hs = Hs + (terr - Hs) * 0.45 * w          # strata ledges
        H = Hs + 1.5 * relief(P[:, 0] * 1.7, P[:, 1] * 1.7) * w; flat = True
        ridge = (fid - 0.5) * 0.7 * w                                            # every face its own shade (lighter / darker stone)
    elif STYLE == "B":
        # B = STACKED BOULDERS: the plain slope (mossy, sunk a little) carries many big rounded-angular rocks, half buried, overlapping
        H = H - 3.0 * w
        rr = random.Random(23); cand = np.nonzero(is_rock & (w > 0.5))[0]
        for _ in range(int(len(cand) * STEP * STEP / 230)):
            c = cand[rr.randrange(len(cand))]; r = 6 + rr.random() ** 1.5 * 10
            boulders.append((float(P[c, 0]), float(P[c, 1]), float(H[c]), r, rr.randrange(10 ** 6)))
        ridge[:] = 0.0
    elif STYLE == "C":
        # C = FLUTED BANDS: sharp crested ribs running down the slope with deep runnels between them (triangle wave across the fall line,
        # varying spacing / height, crests broken along the slope); the crests a touch warmer (ridge attribute)
        warp = 7.0 * np.sin(along * 0.04 + 1.3) + 4.0 * np.sin(along * 0.09 + t * 0.013)
        sp = 20.0; ph = (t + warp) / sp; fr = ph - np.floor(ph)
        tri = 1.0 - 2.0 * np.abs(fr - 0.5)                                       # 1 at the crest, 0 in the runnel
        cell = np.floor(ph); amp = 0.55 + 0.45 * np.sin(cell * 2.7 + 1.1) * np.sin(along * 0.03 + cell)
        brk = np.clip(0.6 + 0.6 * np.sin(along * 0.07 + cell * 1.9), 0, 1)       # crests break up along the slope
        prof = (tri ** 1.6) * amp * (0.5 + 0.5 * brk)
        H = H + 13.0 * (prof - 0.35) * w + 1.2 * relief(P[:, 0] * 1.5, P[:, 1] * 1.5) * w
        ridge = np.clip((prof - 0.45) / 0.4, 0, 1) * 0.5 * w
    H = H + AMP * 0.5 * relief(P[:, 0], P[:, 1]) * w * (0 if STYLE == "A" else 1)
    H = H.reshape(nx + 1, ny + 1); RV = ridge.reshape(nx + 1, ny + 1); ROCK = is_rock.reshape(nx + 1, ny + 1)
    # quads whose centre lies in a rock cell or outside the room
    bm = bmesh.new(); cl_ = bm.loops.layers.color.new("ridge"); vs = {}
    def V(i, j):
        if (i, j) not in vs: vs[(i, j)] = bm.verts.new(G(gx0 + STEP * i, gy0 + STEP * j, float(H[i, j])))
        return vs[(i, j)]
    for i in range(nx):
        for j in range(ny):
            mx, my = gx0 + STEP * (i + 0.5), gy0 + STEP * (j + 0.5); k = (int((mx - O) // 16), int((my - O) // 16))
            if k in cells and k not in rock: continue
            if max(H[i, j], H[i + 1, j], H[i, j + 1], H[i + 1, j + 1]) <= bottom + 1: continue   # nothing at the very bottom
            f = bm.faces.new([V(i, j), V(i + 1, j), V(i + 1, j + 1), V(i, j + 1)])
            f.material_index = 0 if ROCK[i, j] or ROCK[i + 1, j + 1] else 1
            for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                r = float(RV[a, b]); l[cl_] = (r, r, r, 1.0)
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < 0: f.normal_flip()
    # skirt down to the bottom along the outer border (closes the mountain's cut edge)
    for (i0, j0, i1, j1) in [(i, 0, i + 1, 0) for i in range(nx)] + [(i, ny, i + 1, ny) for i in range(nx)] + [(0, j, 0, j + 1) for j in range(ny)] + [(nx, j, nx, j + 1) for j in range(ny)]:
        if (i0, j0) not in vs or (i1, j1) not in vs or H[i0, j0] <= bottom + 1: continue
        a, b = vs[(i0, j0)], vs[(i1, j1)]
        f = bm.faces.new([a, b, bm.verts.new((b.co.x, b.co.y, bottom)), bm.verts.new((a.co.x, a.co.y, bottom))]); f.material_index = 0
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = not (flat and p.material_index == 0)
    me.materials.append(rock_material("rock_c")); me.materials.append(cmat.rock_mat("bank_c", dark=(66, 52, 32), olive=(110, 86, 52), ochre=(140, 106, 58), moss_amt=2.2))
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    if boulders:                                                                 # study B: the rocks
        import kit_c
        bb = bmesh.new()
        for (x, y, z, r, sd) in boulders:
            r2 = random.Random(sd); sq = (1.0 + r2.random() * 0.5, 0.8 + r2.random() * 0.4, 0.55 + r2.random() * 0.3)
            kit_c.rock(bb, G(x, y, z + r * sq[2] * 0.25), r, sq, seed=sd, lump=0.28)
        mb = bpy.data.meshes.new(name + "_boulders"); bb.to_mesh(mb); bb.free()
        for p in mb.polygons: p.use_smooth = False
        mb.materials.append(rock_material("boulder_rock")); bpy.context.scene.collection.objects.link(bpy.data.objects.new(name + "_boulders", mb))
    def height_at(px, py):
        fi = (px - gx0) / STEP; fj = (py - gy0) / STEP; i = int(min(max(fi, 0), nx - 1)); j = int(min(max(fj, 0), ny - 1)); ti, tj = fi - i, fj - j
        return float((H[i, j] * (1 - ti) + H[i + 1, j] * ti) * (1 - tj) + (H[i, j + 1] * (1 - ti) + H[i + 1, j + 1] * ti) * tj)
    return ob, height_at
