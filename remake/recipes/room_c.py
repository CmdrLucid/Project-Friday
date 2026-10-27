"""ROOM BLOCKOUT in style C (2026-10-25): a WHOLE ROOM assembled from the room data of the user's ROM (lib/roomdata.py) and the approved assets
(lib/kit_c.py), first Massan (room 592).  Nothing of the original picture is used for the 3D look; the picture only decides grass / dirt and
pine / bush / fence where the height map alone cannot tell (roomdata.py).
  terrain   every height map cell at its height (blocked objects stand on their 'base'), vertical faces where the ground drops (placeholder 'cliff'
            material: asset 5d cliff wall is not made yet), the room edge drops to z = BOTTOM like a diorama; dirt / grass by a soft ragged mask
            (cmat.dirt_mat, asset 5a) and blade tufts on the grass (lib/cground.py, asset 5b)
  houses    the approved house A (kit_c.house_a) at its own place; the other houses = linked copies of it moved / turned to their door side and
            STRETCHED to their footprint (placeholders until houses B.. are made); the tower = a copy stretched upwards (placeholder)
  objects   palisade along fence cells (asset 3), one shrub per bush cell (asset 2), pines on every second pine cell (asset 2), log-stump steps on
            every walkable edge one step high (asset 4), sea east of the room (cmat.water_mat, asset 5c); statue and cave = grey / dark placeholders
Run: R_FIGURE=~/.landstalker_remake/figures/nigel_a4.png python3 remake/tools/build_asset.py room_c   (R_ROOM=592, R_ROM=path, R_PX=1)
Output (local): game.png (the original's projection, window in window.txt for rom_picture.py), q1..q3.png (camera turned by 90 degree steps)."""
import bpy, bmesh, sys, os, math, random
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import blx, cmat, cground, cliff_c, kit_c, roomdata as RD, massan_a as H
out = os.environ.get("R_OUT", "/tmp/room_c"); os.makedirs(out, exist_ok=True)
ROM = os.path.expanduser(os.environ.get("R_ROM", "~/Documents/NonSteamGames/landstalker/landstalker.md")); ROOM = int(os.environ.get("R_ROOM", "592"))
PX = float(os.environ.get("R_PX", "1"))
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = False
G = H.G; O = 16 * RD.OFF; BOTTOM = -160.0; SEA = -56.0
R = RD.classify(RD.load(ROM, ROOM)); C = R["cells"]
print("room %d: %d cells, %d groups" % (ROOM, len(C), len(R["groups"])), flush=True)
grp = {p: gr for gr in R["groups"] for p in gr["cells"]}
step_cells = {k for k, e in R["steps"]}

# ---- terrain heights -------------------------------------------------------------------------------------------------------------------------------
top = {}
for k, c in C.items():
    gr = grp.get(k)
    top[k] = 16.0 * (gr["base"] if gr and ("obj" in gr or gr["cls"] in ("house", "tower")) else c["h"])
for k in R["statues"]: top[k] = min(top.get((k[0] + dx, k[1] + dy), 0.0) for dx, dy in RD.N4)
for k in step_cells: top[k] -= 4.0                                               # the stump tops (at the cell height) stay visible above the ground
rock = {k: 16.0 * C[k]["h"] for gr in R["groups"] if gr["cls"] in ("cliff", "cave") for k in gr["cells"]}   # asset 5d: these become slopes
for k in rock: top.pop(k, None)
dirt = {k: 1.0 if c["kind"] == "dirt" else 0.0 for k, c in C.items()}
def field(gx, gy):
    """dirt fraction at a game point: bilinear between cell centres (missing cells take the nearest existing one)."""
    fx = (gx - O) / 16.0 - 0.5; fy = (gy - O) / 16.0 - 0.5; x0 = math.floor(fx); y0 = math.floor(fy); tx = fx - x0; ty = fy - y0
    own = dirt.get((int((gx - O) // 16), int((gy - O) // 16)), 0.0)
    v = lambda x, y: dirt.get((x, y), own)
    return (v(x0, y0) * (1 - tx) + v(x0 + 1, y0) * tx) * (1 - ty) + (v(x0, y0 + 1) * (1 - tx) + v(x0 + 1, y0 + 1) * tx) * ty
def mask(gx, gy):
    n = (math.sin(gx * 0.35) + math.sin(gy * 0.5 + 1)) * 0.06 + math.sin(gx * 1.3 + gy * 0.7) * 0.04
    return min(1.0, max(0.0, (field(gx, gy) - 0.5 + n) / 0.22 + 0.5))

# RAISED cells (a blocked edge of a walkable level, rel 0) are a SLOPED bank in the original, not a wall (user 2026-10-27: behind the church the original
# leaves space, ours stood right against the bank): their top falls from the level's height to the lower neighbour across the group's depth
bank = {}                                                                        # cell -> (low side direction, rows from the low edge, depth, low z, high z)
for gr in R["groups"]:
    if gr["cls"] != "raised": continue
    cells_ = set(gr["cells"]); hi_ = 16.0 * gr["h"]
    lows = {k: [(dx, dy, top[(k[0] + dx, k[1] + dy)]) for dx, dy in RD.N4 if (k[0] + dx, k[1] + dy) in top and (k[0] + dx, k[1] + dy) not in cells_
                and top[(k[0] + dx, k[1] + dy)] < hi_ - 8] for k in cells_}
    for d_ in RD.N4:                                                             # the main low side of the group
        edge = [k for k in cells_ if any((dx, dy) == d_ for dx, dy, _ in lows[k])]
        if not edge: continue
        lo_ = max(z_ for k in edge for dx, dy, z_ in lows[k] if (dx, dy) == d_)
        for k in cells_:
            n = 0
            while (k[0] + d_[0] * (n + 1), k[1] + d_[1] * (n + 1)) in cells_: n += 1
            m = 0
            while (k[0] - d_[0] * (m + 1), k[1] - d_[1] * (m + 1)) in cells_: m += 1
            if n == 0 and k not in edge: continue
            if k not in bank or bank[k][2] < n + m + 1: bank[k] = (d_, n, n + m + 1, lo_, hi_)
        break
def zat(k, gx, gy):
    """terrain height of cell k at the game point (gx, gy) (flat except bank cells)."""
    if k not in bank: return top[k]
    (dx, dy), n, D, lo_, hi_ = bank[k]
    cx, cy = 16 * k[0] + O + 8, 16 * k[1] + O + 8
    t = ((gx - cx) * dx + (gy - cy) * dy) / 16.0 + 0.5                           # 0 = far edge, 1 = low edge of this cell
    f = (n + 1 - t) / D                                                          # 1 at the group's high edge, 0 at the low edge
    return lo_ + (hi_ - lo_) * min(1.0, max(0.0, f))

bm = bmesh.new(); cl = bm.loops.layers.color.new("mask"); NS = 6
def quad(ps, mat, want):
    f = bm.faces.new([bm.verts.new(G(*p)) for p in ps]); f.material_index = mat; f.normal_update()
    if f.normal.dot(want) < 0: f.normal_flip()
    for l in f.loops:
        m = mask(l.vert.co.x, -l.vert.co.y) if mat == 0 else 0.0; l[cl] = (m, m, m, 1.0)
import mathutils
UP = mathutils.Vector((0, 0, 1))
for (x, y), z in top.items():
    gx, gy = 16 * x + O, 16 * y + O
    for i in range(NS):                                                          # top: NS x NS quads (smooth mask edges)
        for j in range(NS):
            a, b = gx + 16 * i / NS, gy + 16 * j / NS; s = 16 / NS
            k_ = (x, y); Z = lambda u, v: zat(k_, u, v)
            quad([(a, b, Z(a, b)), (a + s, b, Z(a + s, b)), (a + s, b + s, Z(a + s, b + s)), (a, b + s, Z(a, b + s))], 0, UP)
    for (dx, dy), e in (((1, 0), ((16, 0), (16, 16))), ((-1, 0), ((0, 0), (0, 16))), ((0, 1), ((0, 16), (16, 16))), ((0, -1), ((0, 0), (16, 0)))):
        if (x + dx, y + dy) not in top: continue                                 # rock / outside: the slopes of lib/cliff_c.py meet this edge
        (u0, v0), (u1, v1) = e
        z0_, z1_ = zat((x, y), gx + u0, gy + v0), zat((x, y), gx + u1, gy + v1)
        n0_, n1_ = zat((x + dx, y + dy), gx + u0, gy + v0), zat((x + dx, y + dy), gx + u1, gy + v1)
        if n0_ >= z0_ - 0.01 and n1_ >= z1_ - 0.01: continue
        quad([(gx + u0, gy + v0, min(n0_, z0_)), (gx + u1, gy + v1, min(n1_, z1_)), (gx + u1, gy + v1, z1_), (gx + u0, gy + v0, z0_)], 1, mathutils.Vector((dx, -dy, 0)))
me = bpy.data.meshes.new("terrain"); bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth = p.material_index == 0
me.materials.append(cmat.dirt_mat("room_ground", mask="mask", other=((30, 84, 26), (58, 118, 34)))); me.materials.append(cmat.get("cliff"))
bpy.context.scene.collection.objects.link(bpy.data.objects.new("terrain", me))

cave_doors = [d for d in R["doors"] if not any(d in gr["cells"] for gr in R["groups"] if gr["cls"] in ("house", "tower"))
              and C.get((d[0] - 1, d[1]), {}).get("blk") and any(grp.get((d[0] - 1, d[1]), {}).get("cls") == cls for cls in ("cave", "cliff"))]
cave_groups = []                                                                 # neighbouring door cells = ONE opening (user: 'sieht aus wie 2 Eingaenge')
for d in sorted(cave_doors):
    for g_ in cave_groups:
        if any(abs(d[0] - e[0]) + abs(d[1] - e[1]) == 1 for e in g_): g_.append(d); break
    else: cave_groups.append([d])
calm = [(16 * min(e[0] for e in g_) + O, 16 * (min(e[1] for e in g_) + max(e[1] for e in g_) + 1) / 2 + O, 8.0 * len(g_) + 14.0) for g_ in cave_groups]
holes = [(16 * min(e[0] for e in g_) + O, 16 * (min(e[1] for e in g_) + max(e[1] for e in g_) + 1) / 2 + O, 8.0 * len(g_) - 1.5, 20.5, cliff_c.K_ROCK) for g_ in cave_groups]
cliffs, slope_at = cliff_c.build(C, top, rock, O, BOTTOM, calm=calm, holes=holes)          # no rock facets around a cave mouth
def surface(gx, gy):
    k = (int((gx - O) // 16), int((gy - O) // 16))
    return top[k] if k in top else slope_at(gx, gy)

# ---- grass blades on grass tops (not under houses / the tower) ------------------------------------------------------------------------------------
grs = random.Random(9); pts = []
for (x, y), z in top.items():
    gr = grp.get((x, y))
    if gr and gr["cls"] in ("house", "tower") or (x, y) in R["statues"]: continue
    gx, gy = 16 * x + O, 16 * y + O
    for i in range(5):
        for j in range(5):
            px_, py_ = gx + 1.6 + i * 3.2 + (grs.random() - 0.5) * 2.4, gy + 1.6 + j * 3.2 + (grs.random() - 0.5) * 2.4
            if mask(px_, py_) < 0.45: pts.append((px_, py_))
def height_at(gx, gy): return top.get((int((gx - O) // 16), int((gy - O) // 16)), 0.0)
def edge_d(gx, gy): return max(0.0, 0.5 - field(gx, gy)) * 32.0
cground.grass(pts, height_at, edge_d)
print("grass tufts", len(pts), flush=True)

# ---- houses -------------------------------------------------------------------------------------------------------------------------------------------
ha = kit_c.house_a(); A_BOX = (6, 10, 15, 19)                                    # house A's own cells in room 592 (lib/massan_a.py measures)
A_C = (16 * (A_BOX[0] + A_BOX[1] + 1) / 2 + O, 16 * (A_BOX[2] + A_BOX[3] + 1) / 2 + O)
YAW = dict(E=0.0, N=90.0, W=180.0, S=-90.0)                                      # house A's door looks east (+x)
import house_c, props_c
# details of the Massan houses as seen in the original picture (box = height map cells incl. the doorway cell): windows, boarded windows, roof
# hatches, tower banner / sign; everything else (footprint, door side / place, base height) comes from the room data
MASSAN = {(11, 15, 10, 13): dict(boards=[("S", 0.3, 26)]),                                   # terrace west: boarded window on the south wall
          (11, 15, 6, 9): dict(hatch_px=[(653, 286)]),                                       # terrace middle: a smoke-hole cover
          (20, 24, 9, 12): dict(hatch_px=[(800, 385)], squares=[("S", 0.46, 24, 14)]),               # behind the church: a square window south (user: one was missing; 2026-10-26 'passt noch nicht' -> measured on the picture: middle of the wall, right under the eave, 14 wide)
          (20, 24, 4, 8): dict(),
          (22, 26, 17, 23): dict(boards=[("S", 0.2, 26)], windows=[("E", 0.45, 27)], hatch_px=[(657, 522), (687, 505)]),
          (11, 15, 2, 5): dict(windows=[("S", 0.5, 70), ("S", 0.5, 92)], squares=[("E", 0.45, 93)], banner=("E", 0.45, 87), ZE=110, ZT=137)}   # tower: two centred round windows,
# the cloth hangs out of the east window, the sign above the door (placed in spec_of)
def spec_of(gr):
    x0, x1, y0, y1 = gr["box"]; d = gr["doors"][0]
    sp = dict(X0=16 * (x0 + RD.OFF) + 3, X1=16 * (x1 + 1 + RD.OFF) - 3, Y0=16 * (y0 + RD.OFF) + 3, Y1=16 * (y1 + 1 + RD.OFF) - 3, seed=x0 * 100 + y0)
    side = gr["door_side"]; ca = 16 * ((d[1] if side in "EW" else d[0]) + RD.OFF)
    sp["door"] = dict(side=side, a0=ca + 2.0, a1=ca + 18.0, top=35.0)
    ex = MASSAN.get((x0, x1, y0, y1), {}) if ROOM == 592 else {}
    def along(side_, f): L0, L1 = (sp["X0"], sp["X1"]) if side_ in "NS" else (sp["Y0"], sp["Y1"]); return L0 + (L1 - L0) * f
    sp["windows"] = [dict(side=w[0], a=along(w[0], w[1]), z=w[2]) for w in ex.get("windows", [])]
    sp["boards"] = [dict(side=w[0], a=along(w[0], w[1]), z=w[2]) for w in ex.get("boards", [])]
    sp["hatches"] = [((sp["X0"] + sp["X1"]) / 2 + (sp["X1"] - sp["X0"]) * hx_, sp["Y0"] + (sp["Y1"] - sp["Y0"]) * hy_) for hx_, hy_ in ex.get("hatches", [])]
    if "hatch_px" in ex:                                                          # user 2026-10-26: hatches where the picture has them -> given as the screen point of the
        z0 = 16.0 * gr["base"]; H = house_c.House(dict(sp, ZT=77.0, overhang=1.5)); best = []   # cover in the original (full.png of window.txt 600 -16), solved onto the roof
        for (U, V) in ex["hatch_px"]:
            cand = ((abs(x - y + 584 - U) + abs((x + y) / 2 - (z0 + H.roof_z(x, y) + 4) + 16 - V), x, y)
                    for x in [sp["X0"] + 0.5 * i for i in range(int(2 * (sp["X1"] - sp["X0"])) + 1)]
                    for y in [sp["Y0"] + 0.5 * j for j in range(int(2 * (sp["Y1"] - sp["Y0"])) + 1)])
            e, x, y = min(cand); best.append((x, y))
            if os.environ.get("R_DEBUG"): print("hatch", gr["box"], (U, V), "->", (x, y), "err", round(e, 2))
        sp["hatches"] = best
    for k in ("banner", "sign"):
        if k in ex: sp[k] = dict(side=ex[k][0], a=along(ex[k][0], ex[k][1]), z=ex[k][2])
    sp.update(overhang=1.5, lip=3.5, ZT=77.0)                                   # roofs like house A (user 2026-10-25)
    sp["squares"] = [dict(side=w[0], a=along(w[0], w[1]), z=w[2], **({"w": w[3], "h": w[3]} if len(w) > 3 else {})) for w in ex.get("squares", [])]
    for k in ("ZE", "ZT"):
        if k in ex: sp[k] = ex[k]
    if gr["cls"] == "tower" and "ZE" not in ex: sp["ZE"] = 16.0 * gr["rel"] - 2; sp["ZT"] = sp["ZE"] + 27
    if gr["cls"] == "tower":                                                     # door, sign, cloth and window in ONE column (user: 'ueber der Tuer, nicht versetzt')
        ad = (sp["door"]["a0"] + sp["door"]["a1"]) / 2
        sp["sign"] = dict(side=side, a=ad, z=sp["door"]["top"] + 17)              # hangs a log above the door, under the cloth
        for q in sp["squares"]: q["a"] = ad
        if "banner" in sp: sp["banner"]["a"] = ad
    return sp
first = True
for gr in R["groups"]:
    if gr["cls"] not in ("house", "tower"): continue
    x0, x1, y0, y1 = gr["box"]
    if ROOM == 592 and (x0, x1, y0, y1) == A_BOX and first:
        first = False; continue                                                  # house A itself = the approved asset 1
    house_c.house(spec_of(gr), name="house_%d_%d" % (x0, y0), z0=16.0 * gr["base"])
if ROOM != 592:
    for o in ha: o.hide_render = True                                            # house A lives in Massan only

# pines / bushes as ORIGINAL PIXEL billboards (2026-10-26, DECIDED by the user: pixel, user: 'bringt mich dazu, Baeume und Straeucher auch so zu machen'): R_PLANTS=pixel cuts one
# free-standing pine and the single round bush beside house A out of plane A of the user's picture (props_c.cut_template, local PNGs) and stands a card on
# every place where the 3D pine / bush would stand (bottom row = trunk / stem foot); hedge rows stay one bush card per cell like the 3D bushes
PIX_PINE = None; plant_cards = []
if os.environ.get("R_PLANTS", "pixel") == "pixel" and ROOM == 592:              # user 2026-10-26: 'pixel' (default now; R_PLANTS=3d = the approved 3D pines / bushes)
    la_ = os.path.expanduser("~/.landstalker_remake/rooms/592_room_c/layerA.png")
    if os.path.exists(la_):
        # the pine at the west edge (box (132, 515, 168, 584)) has its trunk in plane A; the free-standing ones keep it in plane B (user 2026-10-27: 'der Kiefer fehlt der Stamm')
        PIX_PINE = props_c.cut_template(la_, (132, 515, 168, 584), os.path.expanduser("~/.landstalker_remake/props/pine_592.png"))
def plant_card(png, x, y, z, fwd=0.0, side=0.0):
    # add_figure puts the card's bottom row FIG_FWD towards the camera (the front corner of a figure's box); a plant's bottom row is its trunk foot, so the
    # card's base goes back by the same amount (7.5 along x and y = FIG_FWD) to land the foot on (x, y); fwd / side = extra screen pixels down / right
    ob = H.add_figure(png, (x - 7.5 + fwd + side / 2, y - 7.5 + fwd - side / 2, z), light=0.45)
    ob["base_q"] = H.G(x - 7.5, y - 7.5, z)   # turned views: the card stands in the middle of the cell (the front corner of the GAME view would push it into fences / slopes)
    plant_cards.append(ob)


# ---- fences, bushes, pines ----------------------------------------------------------------------------------------------------------------------------
FENCE_OUT = float(os.environ.get("R_FENCE_OUT", "8"))   # user 2026-10-27: 'der Zaun muesste ein Stueck naeher Richtung Klippe' / pines in front of it as in the original: stakes on the OUTER edge
frnd = random.Random(21); brnd = random.Random(11); prnd = random.Random(12)
fb = bmesh.new()
for gr in R["groups"]:
    obj = gr.get("obj")
    if not obj: continue
    z0 = 16.0 * gr["base"]
    fence = {p for p, v in obj.items() if v == "fence"}
    if fence:
        bmf = bmesh.new()
        def fpos(x, y):                                                          # stake line of a fence cell: FENCE_OUT towards the outside (a missing or lower neighbour)
            ox = oy = 0
            for dx, dy in RD.N4:
                n = C.get((x + dx, y + dy))
                if (x + dx, y + dy) not in fence and (n is None or n["h"] < gr["base"]): ox += dx; oy += dy
            return 16 * x + O + 8 + FENCE_OUT * (ox > 0) - FENCE_OUT * (ox < 0), 16 * y + O + 8 + FENCE_OUT * (oy > 0) - FENCE_OUT * (oy < 0)
        for (x, y) in sorted(fence):
            cx, cy = fpos(x, y); linked = False
            for dx, dy in ((1, 0), (0, 1)):
                if (x + dx, y + dy) in fence:
                    kit_c.palisade(bmf, (cx, cy), fpos(x + dx, y + dy), (-dy, dx), rnd=frnd); linked = True
            if not linked and not any((x - dx, y - dy) in fence for dx, dy in ((1, 0), (0, 1))):
                kit_c.palisade(bmf, (cx - 6, cy), (cx + 6, cy), (0, -1), rnd=frnd)
        for (x, y) in fence:                                                     # end posts where a fence line stops at walkable ground (gates)
            nbs = sum((x + dx, y + dy) in fence for dx, dy in RD.N4)
            if nbs == 1:
                ox, oy = [(dx, dy) for dx, dy in RD.N4 if (x + dx, y + dy) in fence][0]
                if (x - ox, y - oy) in C and not C[(x - ox, y - oy)]["blk"]:
                    kit_c.end_post(bmf, 16 * x + O + 8 - 6 * ox, 16 * y + O + 8 - 6 * oy)
        kit_c.link("fence_%d_%d" % gr["cells"][0], bmf, kit_c.fence_mats(), z0=z0)
    bush = [p for p, v in obj.items() if v == "bush"]
    if PIX_PINE: continue                                                        # pixel plants: placed from the picture below (lib/plants_px.py)
    if bush: kit_c.bushes([(16 * x + O, 16 * y + O) for (x, y) in bush], Hh=16.0 * gr["rel"], rnd=brnd, z0=z0, name="bushes_%d_%d" % gr["cells"][0])
    for (x, y) in sorted(p for p, v in obj.items() if v == "pine"):
        if (x + y) % 2: continue                                                 # 3D pines are big: every second cell
        kit_c.pine(16 * x + O + 8 + (prnd.random() - 0.5) * 6, 16 * y + O + 8 + (prnd.random() - 0.5) * 6, height=38 + prnd.random() * 10, radius=12 + prnd.random() * 2.5,
                   rnd=prnd, z0=z0, name="pine_%d_%d" % (x, y))

def recast(wx, wy, z):
    """the same picture point on the new surface: walk the view ray (U fixed) from the viewer until it meets the ground / the slopes."""
    d = wx - wy; V = (wx + wy) / 2 - z
    for s_ in range(4000, -600, -1):
        zz = s_ / 2 - V; px_, py_ = (s_ + d) / 2, (s_ - d) / 2
        if zz <= surface(px_, py_): return px_, py_, zz
    return wx, wy, z
def card_at(png, Ub, Vb, z):
    """a pixel card whose bottom-centre pixel lands on the picture point (Ub, Vb), standing at height z (the depth along the view ray)."""
    Ub += 1; Vb += 1                                                             # pixel index -> the card's edge convention (measured: else 1 px up / left)
    X = (Ub - 1184) / 2.0 + Vb + z; Y = X - (Ub - 1184); plant_card(png, X, Y, z)
if PIX_PINE:
    # pixel plants EXACTLY as the original draws them (2026-10-27, user: 'exakt wie im Original'; lib/plants_px.py): pines found by their tips in plane A,
    # bushes / hedges = one card per plant cell of the height map, cut from plane A
    import plants_px as PP
    U0_, V0_ = [int(v) for v in open(os.path.join(os.path.dirname(la_), "window.txt")).read().split()[:2]]
    LA = PP.load(la_); PT = PP.load(PIX_PINE); th_, tw_ = PT.shape[:2]
    tips = PP.find_tips(LA, PT); skip = PP.pine_mask(LA, PT, tips)            # (the trunk rows of grove pines mask nothing: they are not in the picture)
    # single decorations drawn over WALKABLE ground (no plant cell under them): Massan's round bush beside house A; found like the pines, standing on
    # the terrain along the view ray
    PB = props_c.cut_template(la_, (329, 391, 362, 426), os.path.expanduser("~/.landstalker_remake/props/bush_592.png"))
    BT = PP.load(PB); bh_, bw_ = BT.shape[:2]; btips = PP.find_tips(LA, BT, rows=bh_, match=0.9)     # the whole bush: its top alone also matches the leaf clumps of the hedges; skip |= PP.pine_mask(LA, BT, btips)
    for px_, py_ in btips:
        Ub, Vb = px_ + (bw_ - 1) // 2 + U0_, py_ + bh_ - 1 + V0_
        X = (Ub - 1184) / 2.0 + Vb; wx, wy, z = recast(X, X - (Ub - 1184), 0.0); card_at(PB, Ub, Vb, z)
    plant_cells = {}
    for gr in R["groups"]:
        for k, v in (gr.get("obj") or {}).items():
            if v in ("pine", "bush"): plant_cells[k] = gr
    bush_cells = {k: gr for k, gr in plant_cells.items() if gr["obj"][k] == "bush"}
    np_grid = np_cliff = 0
    for px_, py_ in tips:
        png_ = PIX_PINE                                                          # every pine with its trunk (user 2026-10-27); covered by the pines in front by depth
        Ub, Vb = px_ + (tw_ - 1) // 2 + U0_, py_ + th_ - 1 + V0_                # the trunk foot in the picture = the front corner of its cell
        hs = sorted({gr["base"] for gr in plant_cells.values()} | {C[k]["h"] for k in plant_cells}, reverse=True)
        cand = [(b, 0) for b in hs] + [(b, 1) for b in hs]                       # first: on the ground of its cell (base); only then: on the TOP of a cell (pines in a
        for b, on_top in cand:                                                   # hedge, Massan (28, 17)); top first wrongly put grove pines one row too far forward
            z = 16.0 * b; cx = (Ub - 1184) / 2.0 + Vb - 8 + z; cy = cx - (Ub - 1184)
            k = (int((cx - O) // 16), int((cy - O) // 16))
            if k in plant_cells and b == (C[k]["h"] if on_top else plant_cells[k]["base"]):
                # on top of a hedge cell: the same picture point 8 back along the view ray = the cell MIDDLE, 8 below its top, so the trunk stands in the
                # leaves as in the original (user: 'eine Kiefer auf einem Busch')
                card_at(png_, Ub, Vb, z - 8.0 if on_top else z); np_grid += 1; break
        else:                                                                    # a pine on a slope: the terrain along the view ray
            X = (Ub - 1184) / 2.0 + Vb; wx, wy, z = recast(X, X - (Ub - 1184), 0.0)
            card_at(png_, Ub, Vb, z); np_cliff += 1
    skip |= ~PP.leaf_mask(LA)                                                    # only leaf colours (no roof / log / fence / grass speck pieces)
    # HEDGES (user 2026-10-27: cut picture pieces looked half drawn / junk when turned): every bush cell whose picture shows leaves (>= PP.MIN_LEAF leaf
    # pixels in its outline); pixels of pines / fences / logs in front of a hedge are filled from a clean hedge top (the pattern repeats per cell)
    leafy = PP.cell_cards(LA, U0_, V0_, {(16 * x + O + 8, 16 * y + O + 8): (16.0 * gr["base"], 16.0 * (gr["base"] + gr["rel"])) for (x, y), gr in bush_cells.items()}, skip)
    hedge = sorted((int((cx - O) // 16), int((cy - O) // 16)) for (cx, cy) in leafy)
    if hedge:
        best = None
        for k in hedge:                                                          # the cleanest top: most leaf pixels inside its top diamond
            cx, cy = 16 * k[0] + O + 8, 16 * k[1] + O + 8; zt = 16.0 * (bush_cells[k]["base"] + bush_cells[k]["rel"])
            uc, vc = cx - cy + 1184 - U0_, int((cx + cy) / 2 - zt - V0_)
            n = sum(1 for du in range(-14, 15) for dv in range(-(16 - abs(du)) // 2 + 1, (16 - abs(du)) // 2)
                    if 0 <= vc + dv < LA.shape[0] and not skip[vc + dv, uc + du] and LA[vc + dv, uc + du, 3] > 0)
            if best is None or n > best[0]: best = (n, (uc, vc))
        pic = PP.leaf_picture(LA, ~skip & (LA[:, :, 3] > 0), best[1])
        # one camera-facing CARD per hedge cell like the pines (user 2026-10-27: 'warum nicht das Sprite immer zur Kamera gedreht'): the cell's box outline
        # cut from the filled hedge picture + the original leaves sticking up over it
        keep = ~skip & (LA[:, :, 3] > 0); pic[:, :, 3] = np.where(keep, 255, 0)
        hc = PP.cell_cards(pic, U0_, V0_, {(16 * x + O + 8, 16 * y + O + 8): (16.0 * bush_cells[(x, y)]["base"], 16.0 * (bush_cells[(x, y)]["base"] + bush_cells[(x, y)]["rel"])) for (x, y) in hedge}, core_all=True)
        pdir = os.path.expanduser("~/.landstalker_remake/props/hedge_%d" % ROOM)
        for (cx, cy), (a_, (Ub, Vb)) in hc.items():
            zb = 16.0 * bush_cells[(int((cx - O) // 16), int((cy - O) // 16))]["base"]
            card_at(PP.save(a_, os.path.join(pdir, "hedge_%d_%d.png" % (cx, cy))), Ub, Vb, zb)
    cards = leafy
    print("pixel plants: %d pines on cells, %d on slopes, %d round bushes, %d hedge blocks" % (np_grid, np_cliff, len(btips), len(hedge)), flush=True)
for (wx, wy, z, k) in ([] if PIX_PINE else R["pines"]):
    wx, wy, z = recast(wx, wy, z)                                                # single pines on the cliffs, found in the picture (roomdata.cliff_pines)
    kit_c.pine(wx, wy, height=40 + prnd.random() * 6, radius=12.5 + prnd.random() * 1.5, rnd=prnd, z0=z, name="cliffpine_%d_%d" % k)

# ---- steps: log stumps along every walkable edge one step high (runs of cells along x) -------------------------------------------------------------------
srnd = random.Random(31); bst = bmesh.new(); bbody = bmesh.new(); seed = 0
runs = {}
for k, e in R["steps"]:
    if e == "S": runs.setdefault((k[1], C[k]["h"]), []).append(k[0])
for (y, h), xs in sorted(runs.items()):
    xs = sorted(xs); a = xs[0]
    for i, x in enumerate(xs + [None]):
        if x is not None and (i == 0 or x == xs[i - 1] + 1): continue
        b = xs[i - 1]
        seed = kit_c.stump_row(bst, bbody, 16 * a + O, 16 * (b + 1) + O, 16 * (y + 1) + O, 16, 16.0 * h, seed, rnd=srnd)
        a = x
so = kit_c.link("step_stumps", bst, [cmat.get("stump"), cmat.rings_mat()]); kit_c.link("step_body", bbody, cmat.get("earth"))

# ---- statue, cave; the sea ---------------------------------------------------------------------------------------------------------------
# the statue (2026-10-26): the user's idea after three 3D attempts ('Schnauze zu lang, falsche Form'): the ORIGINAL PIXELS as a camera-facing billboard
# like the figures, cut out of plane A of the user's own picture (rom_picture.py layerA.png; the PNG stays local); R_STATUE=3d = props_c.massan_statue
statue_cards = []
ORIG_DIR = os.path.expanduser(os.environ.get("R_ORIG_DIR", "~/.landstalker_remake/rooms/%d_room_c" % ROOM))
for (x, y) in R["statues"]:
    xc, yc = 16 * x + O + 8, 16 * y + O + 8
    la = os.path.join(ORIG_DIR, "layerA.png")
    if os.environ.get("R_STATUE") == "3d" or not os.path.exists(la):
        props_c.massan_statue(xc, yc, top[(x, y)], name="statue_%d_%d" % (x, y)); continue
    U0w, V0w = [int(v) for v in open(os.path.join(ORIG_DIR, "window.txt")).read().split()[:2]]
    uc = xc - yc + 1184 - U0w; vcorner = (xc + yc) / 2 + 8 - top[(x, y)] - V0w     # picture column of the cell centre, row of its front corner on the ground
    path = props_c.cut_billboard(la, int(uc) - 30, int(vcorner) - 90, 60, 100, os.path.expanduser("~/.landstalker_remake/props/statue_%d_%d_%d.png" % (ROOM, x, y)))
    if path:
        img_path, bottom = path                                                  # bottom = picture row of the lowest statue pixel; rows below the corner go under the ground
        statue_cards.append(H.add_figure(img_path, (xc, yc, top[(x, y)] - (bottom - vcorner) * H.FIG_PX), light=0.45))
for g_ in cave_groups:                                                           # the mouth lies in the slope west of the door cells (Massan: faces east)
    x = min(e[0] for e in g_); y0_, y1_ = min(e[1] for e in g_), max(e[1] for e in g_) + 1; z = top[g_[0]]
    k = cliff_c.K_ROCK; n_ = mathutils.Vector((k, 0, 1)).normalized(); up_ = mathutils.Vector((-1, 0, k)).normalized()
    kit_c.cave_mouth((16 * x + O, 16 * (y0_ + y1_) / 2 + O, z), (0, 1, 0), up_, n_, (-1, 0, 0), 8.0 * (y1_ - y0_) - 1.0, 21.0,
                     bpy.data.materials["rock_c"], cmat.get("dark"))
xs = [k[0] for k in C]; ys = [k[1] for k in C]
SEA_X, SEA_Y = 16 * (24 + RD.OFF), 16 * (min(ys) + RD.OFF)                       # Massan: the sea lies NORTH-EAST of the room (behind the tower), the
sb = bmesh.new()                                                                 # east / south faces of the plateau drop into the dark (picture, 2026-10-25)
sb.faces.new([sb.verts.new(G(*p)) for p in ((SEA_X, SEA_Y - 1600, SEA), (SEA_X + 1600, SEA_Y - 1600, SEA), (SEA_X + 1600, SEA_Y, SEA), (SEA_X, SEA_Y, SEA))])
for f in sb.faces:
    f.normal_update()
    if f.normal.z < 0: f.normal_flip()
kit_c.link("sea", sb, cmat.water_mat("sea", flow=(0.0, 1.0)), smooth=False)

# ---- figure, camera, renders --------------------------------------------------------------------------------------------------------------------------
figs = []
fig = os.path.expanduser(os.environ.get("R_FIGURE", ""))
if fig and os.path.exists(fig) and R["statues"]:
    sx, sy = R["statues"][0]; figs.append(H.add_figure(fig, (16 * sx + O + 8 + 18, 16 * sy + O + 8 + 22, top[(sx, sy)])))
U0, V0, W_, H_ = RD.window(R, BOTTOM); U1, V1 = U0 + W_, V0 + H_                   # the same window as the original picture (rom_picture.py)
open(os.path.join(out, "window.txt"), "w").write("%d %d %d %d\n" % (U0, V0, W_, H_))
uc, vc = (U0 + U1) / 2, (V0 + V1) / 2                                            # the ground point (z = 0) in the window centre
tx = (uc - 1184 + 2 * vc) / 2; ty = (2 * vc - (uc - 1184)) / 2
sc, co = blx.game_view(os.path.join(out, "game.png"), px_per_unit=PX, size=(int(W_ * PX), int(H_ * PX)), target=G(tx, ty, 0), squash=True)
cmat.modern_look(sc); co.data.clip_end = 6000
bpy.data.objects["sun"].data.specular_factor = 0.0                               # like the water asset: no sun gloss (the sea turned white in view q1)
# fill light for the ROCK only (light linking): the low west sun leaves the east-facing slopes in their own shadow, so no rock form showed
# (the original painter drew them lit anyway); other assets keep the approved light
rc = bpy.data.collections.new("rock_lit"); sc.collection.children.link(rc)
for ob in list(sc.objects):
    if ob.name.startswith("cliffs"): rc.objects.link(ob)
fl = bpy.data.lights.new("rock_fill", "SUN"); fl.energy = float(os.environ.get("R_ROCK_FILL", "3.0")); fl.color = (1.0, 0.92, 0.8); fl.angle = math.radians(8); fl.specular_factor = 0.0
flo = bpy.data.objects.new("rock_fill", fl); sc.collection.objects.link(flo)
flo.rotation_euler = (-mathutils.Vector((0.25, -0.75, 0.6))).to_track_quat("-Z", "Y").to_euler()     # from the south-south-east, high
try:
    flo.light_linking.receiver_collection = rc
except Exception as e: print("no light linking:", e)
for ob in sc.objects:                                                            # game_view squashes the meshes' z scale only: objects placed on raised
    if ob.parent is None and ob.type in ("MESH", "EMPTY") and ob.location.z:   # ground (z0) must move down with them
        ob.location.z *= math.sqrt(2.0 / 3.0)
    if "base" in ob: ob["base"] = (ob["base"][0], ob["base"][1], ob["base"][2] * math.sqrt(2.0 / 3.0))
figs += statue_cards + plant_cards
for f in figs: f.scale = (1, 1, 1); H.face_camera(f, co, upright=False, game=True)   # pixel cards are not squashed (game_view squashes every mesh; massan_a.render_set does the same reset)
bpy.ops.render.render(write_still=True)
print("game view done", flush=True)
zs = math.sqrt(2.0 / 3.0)
cxr, cyr = 16 * (min(xs) + max(xs) + 1) / 2 + O, 16 * (min(ys) + max(ys) + 1) / 2 + O
sc.render.resolution_x = sc.render.resolution_y = int(max(W_, H_) * PX * 0.92); co.data.ortho_scale = max(W_, H_) * 0.92 * math.sqrt(0.5) * 1.15
for q in (1, 2, 3):
    blx.orbit(co, G(cxr, cyr, 0), 90 * q, 30)
    for f in figs: H.face_camera(f, co, upright=False)
    sc.render.filepath = os.path.join(out, "q%d.png" % q); bpy.ops.render.render(write_still=True)
    print("view q%d done" % q, flush=True)
print("room_c done ->", out)
