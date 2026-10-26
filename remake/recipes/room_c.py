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
            quad([(a, b, z), (a + s, b, z), (a + s, b + s, z), (a, b + s, z)], 0, UP)
    for (dx, dy), e in (((1, 0), ((16, 0), (16, 16))), ((-1, 0), ((0, 0), (0, 16))), ((0, 1), ((0, 16), (16, 16))), ((0, -1), ((0, 0), (16, 0)))):
        if (x + dx, y + dy) not in top: continue                                 # rock / outside: the slopes of lib/cliff_c.py meet this edge
        nz = top[(x + dx, y + dy)]
        if nz >= z: continue
        (u0, v0), (u1, v1) = e
        quad([(gx + u0, gy + v0, nz), (gx + u1, gy + v1, nz), (gx + u1, gy + v1, z), (gx + u0, gy + v0, z)], 1, mathutils.Vector((dx, -dy, 0)))
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
import house_c
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

# ---- fences, bushes, pines ----------------------------------------------------------------------------------------------------------------------------
frnd = random.Random(21); brnd = random.Random(11); prnd = random.Random(12)
fb = bmesh.new()
for gr in R["groups"]:
    obj = gr.get("obj")
    if not obj: continue
    z0 = 16.0 * gr["base"]
    fence = {p for p, v in obj.items() if v == "fence"}
    if fence:
        bmf = bmesh.new()
        for (x, y) in sorted(fence):
            cx, cy = 16 * x + O + 8, 16 * y + O + 8; linked = False
            for dx, dy in ((1, 0), (0, 1)):
                if (x + dx, y + dy) in fence:
                    kit_c.palisade(bmf, (cx, cy), (cx + 16 * dx, cy + 16 * dy), (-dy, dx), rnd=frnd); linked = True
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
    if bush: kit_c.bushes([(16 * x + O, 16 * y + O) for (x, y) in bush], Hh=16.0 * gr["rel"], rnd=brnd, z0=z0, name="bushes_%d_%d" % gr["cells"][0])
    for (x, y) in sorted(p for p, v in obj.items() if v == "pine"):
        if (x + y) % 2: continue
        kit_c.pine(16 * x + O + 8 + (prnd.random() - 0.5) * 6, 16 * y + O + 8 + (prnd.random() - 0.5) * 6, height=38 + prnd.random() * 10, radius=12 + prnd.random() * 2.5,
                   rnd=prnd, z0=z0, name="pine_%d_%d" % (x, y))

def recast(wx, wy, z):
    """the same picture point on the new surface: walk the view ray (U fixed) from the viewer until it meets the ground / the slopes."""
    d = wx - wy; V = (wx + wy) / 2 - z
    for s_ in range(4000, -600, -1):
        zz = s_ / 2 - V; px_, py_ = (s_ + d) / 2, (s_ - d) / 2
        if zz <= surface(px_, py_): return px_, py_, zz
    return wx, wy, z
for (wx, wy, z, k) in R["pines"]:
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

# ---- placeholders: statue, cave; the sea ---------------------------------------------------------------------------------------------------------------
pb = bmesh.new()
for (x, y) in R["statues"]:
    kit_c.rock(pb, G(16 * x + O + 8, 16 * y + O + 8, top[(x, y)] + 22), 8.0, (0.9, 0.8, 2.6), seed=7, lump=0.18)
if pb.verts: kit_c.link("statue_placeholder", pb, cmat.get("boulder"))
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
for f in figs: H.face_camera(f, co, upright=False)
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
