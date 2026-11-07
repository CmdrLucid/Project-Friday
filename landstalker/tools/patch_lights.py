#!/usr/bin/env python3
"""Lighting (2026-11-02, user: 'Licht soll wirklich Licht in den Raum werfen und Objekte Schatten werfen lassen' -> mock-ups ~/Mockups/licht2.html /
licht3.html, 'ja, bau es als Option ein').  In rooms with flame tiles the own map renderer lights the picture from the flames:
 * GEOMETRY from the game's height map (g_HeightMap $FFD192, 74 x 74 cells of 16 units, floor height = low nibble of byte 0 * 16, $4000 = void):
   every image pixel (U, V) of the room picture (lk_o_pa / lk_o_pb space: U = wx - wy + 1184, V = (wx + wy) / 2 - z) is followed along its view
   ray from high z down; the first solid column gives a FLOOR (came from above), a SIDE face (+x or +y normal) or, when the ray leaves the room
   into void above the last floor, a BACK WALL.  Computed per 32 x 32 block of the room picture the first time the block is on screen, kept
   until the room / height map changes (camera independent).
 * LIGHTS = the animated tile groups that are flames (ROM base address of frame 0 = AnimatedTilesetData entries 3 fireplace, 4 lamp, 7 / 11
   torches, 15 / 16 candles, 17 candelabra, 20 cauldron (green), 6 = waterfall shrine water + torches, only its torch tiles 917 / 927 / 928 /
   934 / 935 (v2, user report room 177, 2026-11-03); tools/animsurvey.py numbers, user check 2026-11-02; lava (21) not yet): the
   plane cells with those tiles, connected groups (<= 40 cells) -> one light at the 3D point of the group's centre pixel, 6 units in front of
   its face.  LAVA (21, `$099E8A`, v3; red only in rooms 403 / 404, the same tiles are blue water in 406..411) is a field: one weak orange light per 8 x 8 cells holding >= 8 lava tiles, slow glow; every block uses
   its 8 NEAREST lights.
 * SWORD GLOW (v3, user 2026-11-03): with Magic / Ice / Thunder / Gaia sword equipped (EquippedSword $FF114E 1..4) a light in the sword's colour
   moves with Nigel (+18 above his foot), no light while walking (user), only while swinging (Player_ActionHigh $FF542C bits 0..3 = 1..4); only in rooms
   that are lit (flames / lava), no shadow, lights the other figures at half strength.
 * SCENERY LIGHT per block and light (<= 6 per block): distance falloff (radius 120 units), the angle to the face, and the shadow of the height
   map (march to the light) -> 0..255; per frame only the flicker of each light is applied.
 * FIGURES (visible entities, g_VisibleEntityList $FF11DE): upright cut-outs at their foot point (+14 / +16 / +12), silhouette = their sprite
   pixels of lk_o_spr inside a box around the anchor (+0E / +10): their own pixels are lit at their cut-out position (normal to the camera) and
   they cast shadows: a light ray from a scenery pixel that crosses a silhouette is blocked (only light / figure pairs closer than the radius).
   v4: for the shadow the cut-out turns to face each light (a camera-facing card was seen edge-on by lights beside the figure = thin streaks).
 * v4: a void gap is kept as a wall when the room cells behind it are a narrow niche (<= 3 cells across, a door in the wall: room 5).
 * Colour: ambient 0.85 (v8, user 2026-11-05; was 0.55) (slightly cool) + 2.2 x the warm light sum, clamped at 2.4; only in rooms with at least one flame light, map frames only
   (not the screens / menus), not with HD tile packs.  Picture only (Off = bit exact).
 * v8 ROOM LIGHT (user 2026-11-05, idea 1 for flat dungeon rooms): every indoor room (not only rooms with flames; not the intro) gets soft corner
   shadows from the height map (lk_lt_aoval: per direction the highest occluder angle within 40 units, fading with distance; void cells on the -x / -y side
   with no room cell behind them count as back walls (lk_lt_vw); wall feet darker; floors below the room's main height (lk_lt_zref) up to 18 % darker);
   rooms without flames keep the original brightness apart from that.  Test aids LANDSTALKER_LT_AO=0 (off), LANDSTALKER_LIGHTING_DBG=8 (share as grey).
Option: Options > Graphics > Lighting Off / On (id 47, ~/.landstalker_lighting, env LANDSTALKER_LIGHTING=0|1), default Off.
Test aid: LANDSTALKER_LIGHTING_DBG=1 prints the lights of every new room; =2 shows the geometry colours instead of the picture;
LANDSTALKER_LIGHTING_SWORD=1..4 = sword glow of that sword (Magic / Ice / Thunder / Gaia) whatever is equipped.
=3 also prints the height map rows 18..33 / columns 18..43; =6 (v7) shows the sun share as grey, tinted by the outdoor object of the hit cell; =7 the light proxies as colours; LANDSTALKER_LIGHTING_PROBE=x0,line[,x1[,frame]] prints face / z / world position / light terms of
every 4th picture pixel x0..x1 on that line at frame 1260 or the given frame (v3 church fixes; v4: 4th value = frame).
v7 + LIGHT PROXIES (docs/LIGHT_PROXY_PLAN.md, 2026-11-03): outdoors the sun works on invisible shapes per object, proposed at room entry:
buildings (up to 5 heights) -> a hip roof box per equal height part (eave / ridge measured from the drawn picture: visual hull mirrored in the part),
small objects (<= 4 cells, drawn >= 32 high) -> a LATHE solid from the sprite's drawn width per row (trees), lower / flat ones nothing; everything else
(cliffs, terraces) is the game's height map.  The proxies are rasterised into a 4 unit field (lk_lt_fh, owner lk_lt_fo, proxy lk_lt_fp).  ONE pixel rule:
layer A pixels find their surface on the proxies, layer B pixels on the ground (lk_lt_vt / lk_lt_vg).  The sun march goes through game heights + proxies
(lathes with their real profile), skips the pixel's own object, soft penumbra (LK_LT_PEN).  Faces turned away from the sun keep their painted shading
(low boxes without a proxy follow the top behind them).  Speed: early exits (lk_lt_hd), 16-step skips, prefetch ring, on-demand cap per frame.
Figures: shadows only from their own sprite pixels (lk_lt_spre), flame shadows fade with distance.
Needs patch_own.py, patch_modernhud.py and patch_swordfx.py before it.  Idempotent.  usage: patch_lights.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_LIGHTS v8"
import json
CORR_OPS = {"flat": (1, 4), "water": (2, 5), "remove": (3, 4), "hip": (4, 7), "mesh": (5, 4), "bushes": (6, 4), "pines": (7, 4)}
def mesh_cells(path):   # an OBJ (game coordinates) -> {(sx, sy): top height} on the 4 unit grid of the light field (sub column centres), max over all faces
    vs, top = [], {}
    for line in open(path):
        t = line.split()
        if not t: continue
        if t[0] == "v": vs.append(tuple(float(q) for q in t[1:4]))
        elif t[0] == "f":
            idx = [int(q.split("/")[0]) - 1 for q in t[1:]]
            for k in range(1, len(idx) - 1):
                a, b, c = vs[idx[0]], vs[idx[k]], vs[idx[k + 1]]
                den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(den) < 1e-6: continue   # a wall seen from above
                for sy in range(int(min(a[1], b[1], c[1]) // 4), int(max(a[1], b[1], c[1]) // 4) + 1):
                    for sx in range(int(min(a[0], b[0], c[0]) // 4), int(max(a[0], b[0], c[0]) // 4) + 1):
                        x, y = 4 * sx + 2, 4 * sy + 2
                        w1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / den; w2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / den; w3 = 1 - w1 - w2
                        if min(w1, w2, w3) < -1e-6: continue
                        z = w1 * a[2] + w2 * b[2] + w3 * c[2]
                        if z > top.get((sx, sy), -1e9): top[(sx, sy)] = z
    return top
def cat_table():   # data/object_blocks.json (OBJECT CATALOGUE, LIGHT_PROXY_PLAN 'Object catalogue'): per tileset the layer A blocks that draw a recurring object -> class
    path = os.environ.get("LANDSTALKER_OBJCAT_JSON") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "object_blocks.json")
    rows, cls = [], []
    if os.path.isfile(path):
        d = json.load(open(path)); names = list(d["classes"].keys())
        for n in names:
            c = d["classes"][n]; cls.append("{%d, %d, %d}" % ({"sphere": 1, "cone": 2, "flat": 3}[c["shape"]], int(c.get("r", 6)), int(c.get("h", 16))))
        for ts, m in sorted(d["tilesets"].items(), key=lambda kv: int(kv[0])):
            for n, ids in m.items():
                for i in ids: rows.append("{%d, %d, %d}" % (int(ts), int(i, 16), names.index(n) + 1))
    print("patch_lights: object catalogue: %d classes, %d blocks from %s" % (len(cls), len(rows), path))
    return ("static const int16_t lk_lt_catc[][3] = { {0, 0, 0}%s };\n" % "".join(", " + c for c in cls) +
            "static const int16_t lk_lt_cat[][3] = { %s };\n" % ", ".join(rows + ["{-1, 0, 0}"]))
MESHES = []
def corr_table():   # data/light_proxies.json (our own data, LIGHT_PROXY_PLAN step 2) -> C rows {room, op, a[7]}
    path = os.environ.get("LANDSTALKER_LIGHTPROXY_JSON") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "light_proxies.json")
    rows = []
    if os.path.isfile(path):
        for room, lst in sorted(json.load(open(path))["rooms"].items(), key=lambda kv: int(kv[0])):
            for e in lst:
                op, n = CORR_OPS[e["op"]]; a = [int(v) for v in e["cells"]]
                assert len(a) == n, ("light_proxies.json: room %s op %s needs %d numbers" % (room, e["op"], n))
                if op == 5:   # mesh: the rectangle's automatic shapes go, the mesh is stamped (a[4] = mesh number)
                    top = mesh_cells(os.path.join(os.path.dirname(path), e["file"])); mi = len(MESHES)
                    MESHES.append(", ".join("{%d, %d, %d}" % (sx, sy, int(round(h))) for (sx, sy), h in sorted(top.items()) if 0 <= sx < 296 and 0 <= sy < 296))
                    a = a + [mi]; n += 1
                if op in (6, 7):   # bushes / pines: + top above the base (0 = the game's height of each cell), crown radius (0 = default), base (-999 = automatic)
                    a = a + [int(e.get("h", 0)), int(e.get("r", 0)), int(e.get("base", -999))]; n += 3
                rows.append("{%d, %d, {%s}}" % (int(room), op, ", ".join(str(v) for v in a + [0] * (7 - n))))
    print("patch_lights: %d light proxy corrections from %s" % (len(rows), path))
    mesh = "".join("static const int16_t lk_lt_mesh%d[][3] = { %s, {-1, -1, -1} };\n" % (i, m) for i, m in enumerate(MESHES))
    mesh += "static const int16_t (*const lk_lt_meshes[])[3] = { " + ", ".join(["lk_lt_mesh%d" % i for i in range(len(MESHES))] + ["0"]) + " };\n"
    print("patch_lights: %d light proxy meshes (%s cells)" % (len(MESHES), ", ".join(str(m.count("{")) for m in MESHES)))
    return "static const lk_lt_corr_t lk_lt_corr[] = { " + ", ".join(rows + ["{-1, 0, {0}}"]) + " };\n" + mesh
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER in s:
    print("vdp_render.c already patched:", VER); sys.exit(0)

def rep(a, b):
    global s
    assert s.count(a) == 1, f"vdp_render.c layout changed: {a[:70]!r} ({s.count(a)}x)"
    s = s.replace(a, b, 1)

MODULE = r'''/* ---- %s: lighting from flames with height map geometry and figure shadows (tools/patch_lights.py) ---- */
static int lk_lt_o = -1, lk_lt_dbg = -1;
int lk_lt_get(void) { if (lk_lt_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_LIGHTING"); char pth[512]; FILE *f; int v = 0; snprintf(pth, sizeof pth, "%%s/.landstalker_lighting", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); lk_lt_o = v ? 1 : 0; } return lk_lt_o; }
void lk_lt_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_lt_get(); lk_lt_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_lighting", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_lt_o); fclose(f); } }
#define LK_LT_BW 76                     /* blocks of 32 px over the room picture (304 x 152 tiles = 2432 x 1216 px) */
#define LK_LT_BH 38
#define LK_LT_NL 8                      /* lights per block (v3: the nearest ones; was the first 6) */
#define LK_LT_ML 96                     /* lights per room (v3: lava fields; was 32) */
#define LK_LT_RAD 120.0f   /* v2: was 90, the floor under high wall torches stayed dark (room 177) */
typedef struct { int16_t z[1024]; uint8 face[1024]; uint8 nl, li[LK_LT_NL]; uint8 term[LK_LT_NL][1024]; uint8 sun[1024]; uint8 ao[1024]; uint8 beam[1024], pool[1024]; uint16_t km[3][1024]; uint8 sunn[1024]; int16_t robj[1024]; int sungen; } lk_lt_blk;   /* LK_DAYNIGHT v1: sunn = sun share for the NEXT sun direction (lk_lt_sdn), valid when sungen == lk_dn_gen; robj = object of the view ray per pixel (kept for sun-only recomputes) */   /* km: v8 SPEED, key light rooms: the finished light factor (x 256) of every pixel (user 2026-11-05: 'generell ruckeliger') */   /* v8 ao: room light share 0..255 (corner shadows) */
static lk_lt_blk *lk_lt_b[LK_LT_BH][LK_LT_BW]; static int lk_lt_gen;   /* v8 MT: bumped by lk_lt_free (worker results of an older generation are dropped) */
typedef struct { float x, y, z; float r, g, b; int lava; uint32_t base; float k, rad; } lk_lt_light;   /* k: strength, rad: reach (LK_LT_RAD; castle torches more, user 2026-11-04) */   /* base: the AnimatedTilesetData entry of the flame (kind of torch) */
static lk_lt_light lk_lt_l[LK_LT_ML]; static int lk_lt_nfl, lk_lt_nl, lk_lt_room = -2, lk_lt_zmax; static uint32_t lk_lt_hash; static long lk_lt_frame = -1;
static int16_t lk_lt_top[74][74];
static int16_t lk_lt_gh[74][74];   /* v6: the game's heights (lk_lt_top = ours: outdoor objects raised to their drawn height for the view ray); the sun's shadow march uses these + lk_lt_fh */
#define LK_LT_FN 296                /* v7: fine object height field, 4 units per entry (74 * 16 / 4) */
#define LK_LT_IPEN 4.0f            /* indoor soft shadow edges (lk_lt_term): lit share = min over the march of IPEN * clearance / distance */
#define LK_LT_PEN 12.0f             /* v7: penumbra: lit share = min over the march of PEN * clearance / horizontal distance */
static int16_t lk_lt_fh[LK_LT_FN][LK_LT_FN], lk_lt_fo[LK_LT_FN][LK_LT_FN]; static int lk_lt_fhmax;   /* v7: object top + owner object per sub column */
typedef struct { float x, y; int16_t h, hh, U, V0, w, obj; } lk_lt_card;   /* upright card facing the sun, silhouette = drawn layer A picture: v7 one per SMALL object (tree, post), one per cell of class 3 objects (v6) */
static lk_lt_card lk_lt_c[1024]; static int lk_lt_nc;
typedef struct { uint8 type; int16_t x0, y0, x1, y1, z0, eave, ridge, obj, part; } lk_lt_proxy;   /* LIGHT PROXY (docs/LIGHT_PROXY_PLAN.md): invisible shape for light only; type 1 hip (box to eave + hip roof to ridge), 2 cone (centre (x0, y0), radius x1, z0 .. ridge); type 5 BUSHES / PINES (data op bushes / pines: CELLS x0..x1 / y0..y1, part 0 round bush / 1 pine cone, z0 = base, eave = top above base or 0 = each cell's game height, ridge = radius): one tree per raised cell */
static uint8 lk_lt_tk[74][74], lk_lt_tr[74][74]; static int16_t lk_lt_tb[74][74], lk_lt_tt[74][74], lk_lt_to[74][74];   /* RECURRING OBJECTS per cell (catalogue + data ops bushes / pines):
     kind 1 round bush (sphere radius tr, top tt) / 2 pine (cone base tb + 4 .. tt, radius tr) / 3 flat (flower bed: no shape, none over it), base tb, owner object lk_lt_to (= the type 5 proxy's obj); 0 = none */
static uint8 lk_lt_walk[74][74];   /* the game's height map cell is walkable (not blocked, $4x / $2x clear): an automatic hip never stands on such a cell of its own base height (Nigel would be inside it) */
static lk_lt_proxy lk_lt_px[255]; static int lk_lt_npx; static uint8 lk_lt_prof[255][96];   /* type 3 LATHE (centre (x0, y0), z0, height ridge - z0): radius per unit of height from the sprite's drawn width per row (like Blender's screw modifier) */ static uint8 lk_lt_fp[LK_LT_FN][LK_LT_FN];   /* proxies of the room; lk_lt_fp = proxy + 1 of every sub column (0 none) */

static int16_t lk_lt_vt[LK_LT_FN][LK_LT_FN], lk_lt_vg[LK_LT_FN][LK_LT_FN], lk_lt_vm[74][74]; static __thread int lk_lt_rayA;   /* lk_lt_vg: proxy step 1b, the same without the proxies (pixels not drawn in layer A are ground: they pass the proxies); lk_lt_rayA = the pixel is drawn in layer A */   /* v7 speed: lk_lt_fcell of every sub column; per cell the 3 x 3 max of it (32767 = void / object near: no skip) */
static int16_t lk_lt_hd[74][74];   /* v7 speed: per cell the highest thing (field / cards) the sun ray can still meet from this cell on (3 x 3 dilated), cards only */
static int16_t lk_lt_bb[1024][5], lk_lt_sgnd[1024], lk_lt_omax[1024]; static uint8 lk_lt_ocl[1024];   /* lk_lt_sgnd: v7 ground around a SMALL object (its collision box is no picture: light and shadow use the ground + the card) */ static int16_t lk_lt_part[74][74], lk_lt_pb[2048][4]; static uint8 lk_lt_pkeep[74][74], lk_lt_wat[74][74], lk_lt_flat[74][74];   /* lk_lt_flat: cells marked flat by data/light_proxies.json */
typedef struct { int16_t room; uint8 op; int16_t a[7]; } lk_lt_corr_t;   /* corrections from data/light_proxies.json (op 1 flat, 2 water, 3 remove, 4 hip; cells inclusive, heights in units) */
/*LK_LT_CORR*/   /* lk_lt_wat: water cells filled by us (no part of any object) */ static int16_t lk_lt_pb2[2048][4];   /* box of the kept cells per part */   /* v7: equal height parts of the objects + their boxes (mirror boxes of the fine field) */   /* v7: per outdoor object: footprint box (cells) + cell count; class 1 small (one card), 2 building (fine field), 3 other (a card per cell, v6) */
static int16_t lk_lt_obj[74][74];
static float lk_lt_flk[LK_LT_ML];
static lk_lt_light lk_lt_sw; static float lk_lt_swk; static int lk_lt_swon;   /* v3: glow of Nigel's sword (EquippedSword $FF114E 1..4), a light that moves: no cache, no shadow */
typedef struct { float fx, fy, fz; int ax, ay; float sun; int tag; } lk_lt_fig;   /* tag (v7): entity offset / 0x80 + 1 = lk_lt_spre of its own sprite pixels */
static lk_lt_fig lk_lt_f[16]; static int lk_lt_nf, lk_lt_on;
static float lk_lt_fb[512][12]; static int lk_lt_nfb, lk_lt_fbj[512], lk_lt_fmall, lk_lt_fmask, lk_lt_pbox[LK_LT_ML][16][4], lk_lt_curx, lk_lt_cury;   /* pbox: v8 SPEED, screen box of each flame / figure shadow (lk_lt_shadowed skips pixels outside) */ static void lk_lt_fmkbuild(void);   /* v8 SPEED: per figure the screen region its shadow can fall into (key light): its card box x0 y0 x1 y1 swept along (ex, ey); figsun only there, only those figures */
static float lk_lt_thinz = 16.0f;   /* the flame check of lk_lt_thin: a light within one cell at most this far below the column top */
static int16_t lk_lt_thin[74][74];   /* indoors: a THIN free standing column (pillar / post: <= 4 blocked cells of one height, higher than all neighbours) -> the floor around it, else -32768;
     layer B pixels (walls / floors behind it) pass through it, only its own layer A pixels sit on it (user 2026-11-04: the torches stood in a lit box = the pillar's collision column);
     kept only under a flame; such a pillar casts no shadow either (its 16 x 16 collision column under its own flame shaded the room: user 2026-11-05) */
static int lk_lt_sun, lk_lt_ztop;   /* v5: outdoor room lit by the sun (tilesets 0 / 7 / 12 / 13 / 14 / 17), highest floor */
static float lk_lt_sd[3] = { -0.72f, -0.26f, 0.64f }, lk_lt_sS = 0.70f, lk_lt_sK = 0.6f;   /* v5: unit vector to the sun, shadow level, sun strength (lk_lt_sunp) */
/* LK_DAYNIGHT v1 (user 2026-11-06: 'Tag-Nacht-Wechsel: die Sonne draussen soll wandern, Schatten laenger wenn sie tiefer steht, nach dem Sonnenstand ausgerichtet; Farblicht nach Tageszeit;
   die Zeichnung der Schatten ruckelt; eine Taste fuer den Zeitraffer; optional im Menue').  SMOOTH SUN STEPS: the blocks keep showing the shadows of the current direction (lk_lt_sd)
   while the light worker computes the share for the next direction (lk_lt_sdn, early exit field lk_lt_hdn) into b->sunn; when every block has it, the two are crossfaded
   (lk_dn_mix 0..256) and then swapped.  Blocks made during a step compute both.  Used by the day / night cycle and by the sun test aid (L5 + right stick, was: drop all blocks). */
static double lk_dn_st0 = -1.0, lk_dn_st1 = -1.0; static float lk_lt_sdf[3];   /* LK_DAYNIGHT v5: time of the shown direction / of the next one; the direction the figures' sun shadows use (blended) */
static float lk_lt_sdn[3]; static int16_t lk_lt_hdn[74][74]; static volatile int lk_dn_hdok; static int lk_dn_upd, lk_dn_gen = 1, lk_dn_mix, lk_dn_on, lk_dn_night; static float lk_dn_amb3[3], lk_dn_sun3[3], lk_dn_sunk = 1.0f;   /* upd: 0 none, 1 the worker computes sunn, 2 crossfade */
static __thread const float *lk_lt_sdp; static __thread int16_t (*lk_lt_hdp)[74];
static void lk_dn_cancel(void); static int lk_dn_iswt(uint32 c); int lk_dn_get(void);
static float lk_lt_fadek = 1.0f;   /* v4 (user 2026-11-06: 'beim Raumwechsel blenden die beleuchteten Fenster und die Lichtstrahlen nicht richtig mit aus / ein'): brightness of the drawn colours (lk_o_pix, v5) against the room's palette ($FF0080, DarkenActivePalette $0009BE) 0..1; every ADDED light (shafts, motes, particles, window glass / window lights) is scaled by it */   /* per thread: the direction / early exit field the sun march uses (0 = lk_lt_sd / lk_lt_hd) */
static int lk_lt_odcap = 6; static double lk_lt_lbms; static int lk_lt_lbn, lk_lt_lpfn; static double lk_lt_bms, lk_lt_pms; static int lk_lt_bn, lk_lt_pfn, lk_lt_pre, lk_lt_odn;   /* lk_lt_odn: v7 blocks computed on demand this frame (max 6: a room entry needed 60..80 = one 90 ms frame; the rest are drawn unlit for a few frames of the dark fade in) */   /* v7 test aid (DBG=5): block time of the last frame on demand / prefetched */
static int lk_lt_umin = 1 << 30, lk_lt_umax = -(1 << 30), lk_lt_vmin = 1 << 30, lk_lt_vmax = -(1 << 30);   /* v7: picture area drawn in the last frame (prefetch around it) */   /* v7 test aid (DBG=5): time spent computing blocks in the last frame */
static int lk_lt_retry;               /* a new room whose planes were not built yet: look for lights again a few times */
static uint32_t lk_lt_pah;            /* v7: hash of the layer A plane at the last rebuild (outdoors a retry rebuilds only when the picture changed: 12 rebuilds of 40..70 ms each stuttered) */
static uint32_t lk_lt_pahash(void) { uint32_t h = 2166136261u; int x, y; for (y = 0; y < 152; y++) for (x = 0; x < 304; x++) h = (h ^ (lk_o_pa[y][x] & 0x1FFFF)) * 16777619u; return h; }
static uint8 lk_lt_pair[LK_LT_ML][16];        /* light k / figure j close enough for a shadow */
static float lk_lt_pn[LK_LT_ML][16][2];       /* v4: per pair the horizontal direction figure -> light: the shadow card faces the light (a camera-facing card cast thin streaks from lights beside the figure, user 2026-11-03: 'Silhouette kaum erkennbar') */
static int lk_lt_cell(int cx, int cy) { return (cx < 0 || cy < 0 || cx >= 74 || cy >= 74) ? -32768 : lk_lt_top[cy][cx]; }
static int lk_lt_fdiv(int a, int b) { return a >= 0 ? a / b : -((-a + b - 1) / b); }
static int lk_lt_side(int cx, int cy, int pcx, int pcy, int z) {   /* v3: which side the ray entered (cx, cy) from; both indices change in the same step on every 16th picture column, then the neighbour that is solid decides (was always +x: box-shaped dark stripes on +y walls, user: church wall by the books) */
  int ty, tx;
  if (cx == pcx) return 3;
  if (cy == pcy) return 2;
  ty = lk_lt_cell(pcx, cy); tx = lk_lt_cell(cx, pcy);
  if (z <= ty && z > tx) return 3;
  if (z <= tx && z > ty) return 2;
  return 2;
}
static int lk_lt_dent(int cx, int cy, int cf) {   /* v4: room cell (cx, cy) is part of a narrow recess (<= 3 cells wide across the wall) = a door niche in the wall (room 5, user 2026-11-03: light stripe at the right door); the wall beside it stays a wall */
  int n = 1, d, ax = cf == 3, ay = cf == 2;
  for (d = 1; d <= 3 && lk_lt_cell(cx - d * ax, cy - d * ay) > -32768; d++) n++;
  for (d = 1; d <= 3 && lk_lt_cell(cx + d * ax, cy + d * ay) > -32768; d++) n++;
  return n <= 3;
}
static __thread int lk_lt_rob;   /* v8 MT: per thread; v6: the first outdoor object (lk_lt_obj) the last view ray passed */
static int lk_lt_fcell(int sx, int sy) { int t, o; if (sx < 0 || sy < 0 || sx >= LK_LT_FN || sy >= LK_LT_FN) return -32768; o = lk_lt_fo[sy][sx];   /* v7: buildings = game height + fine field; other objects = the raised cell of v6 */
  t = lk_lt_gh[sy >> 2][sx >> 2]; { int ob = lk_lt_obj[sy >> 2][sx >> 2]; if (ob > 0 && ob < 1024 && lk_lt_ocl[ob] == 1) t = lk_lt_sgnd[ob]; } if (o && lk_lt_fh[sy][sx] > t) t = lk_lt_fh[sy][sx]; return t; }
static int lk_lt_rayf(int U, int V, int *zo) {   /* v7: outdoors with objects: the view ray through the game's heights + the fine object field (4 units), so drawn roofs / crowns
     are where the sun's march sees them (v6 raised whole cells: a church cell stood as a column over the path); faces from the sub column steps; lk_lt_rob = owner of the hit */
  int D = U - 1184, z, psx = -999, psy = -999, ptop = -32768, pin = 0, cf = 0, cz = 0;
  for (z = lk_lt_ztop + 2 < lk_lt_zmax ? lk_lt_ztop + 2 : lk_lt_zmax; z >= -16; z--) {   /* v7 speed: nothing stands above lk_lt_ztop */
    int sx = lk_lt_fdiv(2 * V + 2 * z + D, 8), sy = lk_lt_fdiv(2 * V + 2 * z - D, 8), top = sx >= 0 && sy >= 0 && sx < LK_LT_FN && sy < LK_LT_FN ? (lk_lt_rayA ? lk_lt_vt[sy][sx] : lk_lt_vg[sy][sx]) : -32768, in = top > -32768;
    if (cf && in && z > top && !lk_lt_dent(sx >> 2, sy >> 2, cf)) cf = 0;
    if (in && !lk_lt_rob && lk_lt_fo[sy][sx] && lk_lt_rayA) lk_lt_rob = lk_lt_fo[sy][sx];
    if (z <= top) { *zo = z; if (lk_lt_fo[sy][sx] && lk_lt_rayA) lk_lt_rob = lk_lt_fo[sy][sx];
      if ((sx == psx && sy == psy) || psx == -999 || z == top) return 1;
      if (sx == psx) return 3;
      if (sy == psy) return 2;
      { int ty = lk_lt_fcell(psx, sy), tx = lk_lt_fcell(sx, psy); if (z <= ty && z > tx) return 3; return 2; } }
    if (psx != -999 && pin && !in && z > ptop && !cf) { int ty = lk_lt_fcell(psx, sy), tx = lk_lt_fcell(sx, psy); cz = z; cf = sx == psx ? 3 : sy == psy ? 2 : (ty == -32768 && tx > -32768 ? 3 : 2); }
    psx = sx; psy = sy; ptop = top; pin = in;
    if (!cf && in && z - 16 > (int)lk_lt_vm[sy >> 2][sx >> 2] + 1) {   /* v7 speed: 16 steps stay inside the 3 x 3 cells around: nothing to hit, no void, no object there -> same result */
      z -= 15; psx = lk_lt_fdiv(2 * V + 2 * z + D, 8); psy = lk_lt_fdiv(2 * V + 2 * z - D, 8); ptop = lk_lt_rayA ? lk_lt_vt[psy][psx] : lk_lt_vg[psy][psx]; pin = 1; }
  }
  if (cf) { *zo = cz; return cf; }
  return 0;
}
static int lk_lt_ray(int U, int V, int *zo) {   /* geometry of one picture pixel: 0 none, 1 floor, 2 face +x, 3 face +y; *zo = z of the hit */
  int D = U - 1184, z, pcx = -999, pcy = -999, ptop = -32768, pin = 0, cf = 0, cz = 0;
  if (lk_lt_sun && lk_lt_fhmax > -32768) return lk_lt_rayf(U, V, zo);   /* v7 */
  for (z = lk_lt_zmax; z >= -16; z--) {
    int cx = lk_lt_fdiv(2 * V + 2 * z + D, 32), cy = lk_lt_fdiv(2 * V + 2 * z - D, 32), top = lk_lt_cell(cx, cy), in = top > -32768;
    if (in && !lk_lt_rayA && !lk_lt_sun && cx >= 0 && cy >= 0 && cx < 74 && cy < 74 && lk_lt_thin[cy][cx] > -32768) top = lk_lt_thin[cy][cx];
    if (in && !lk_lt_rob && lk_lt_obj[cy][cx]) lk_lt_rob = lk_lt_obj[cy][cx];
    if (cf && in && z > top && !lk_lt_dent(cx, cy, cf)) cf = 0;   /* v3: back on room cells after a void gap (beside a corridor that sticks out of the room, church room 700): the gap was no wall; v4: at any distance (a pit in front of the walkway of room 5 = void, was a high wall), unless those cells are a narrow door niche in the wall (room 5) */
    if (z <= top) { *zo = z; return (cx == pcx && cy == pcy) || pcx == -999 || z == top ? 1 : lk_lt_side(cx, cy, pcx, pcy, z); }
    if (pcx != -999 && pin && !in && z >= ptop && !cf) {   /* v8: >= (was >): a ray leaving the room exactly at the floor's back edge found nothing = a 1 pixel seam between floor and back wall (room 200 / 185, lightedges) */
      int ty = lk_lt_cell(pcx, cy), tx = lk_lt_cell(cx, pcy); cz = z; cf = cx == pcx ? 3 : cy == pcy ? 2 : (ty == -32768 && tx > -32768 ? 3 : 2); }   /* back wall candidate: the side that leads into the void */
    pcx = cx; pcy = cy; ptop = top; pin = in;
  }
  if (cf) { *zo = cz; return cf; }
  return 0;
}
static void lk_lt_pos(int U, int V, int z, float *x, float *y) { int D = U - 1184; *x = (float)(2 * V + 2 * z + D) * 0.5f; *y = (float)(2 * V + 2 * z - D) * 0.5f; }
static int lk_lt_solid(float x, float y, float z) { int cx = (int)floorf(x / 16.0f), cy = (int)floorf(y / 16.0f), t = lk_lt_cell(cx, cy);
  if (!lk_lt_sun && cx >= 0 && cy >= 0 && cx < 74 && cy < 74 && lk_lt_thin[cy][cx] > -32768) t = lk_lt_thin[cy][cx];
  return z < (float)t - 0.5f; }
static int lk_lt_aor;                 /* v8 ROOM LIGHT (user 2026-11-05, idea 1: 'Dungeon-Raeume ohne Lichtquelle wirken flach'): indoor rooms get soft corner shadows (ambient occlusion from the height map), also rooms without flames */
static uint8 lk_lt_vw[74][74];        /* v8: void cell that is a BACK WALL seen from the room: bit 0 looking -x, bit 1 looking -y (no room cell within 8 cells further on: not a pit / gap) */
static int lk_lt_zref = -32768;       /* v8: the room's main floor height (most walkable cells); lower floors get a little darker (depth) */
static int lk_lt_aoopt(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_LT_AO"); v = e ? atoi(e) : 1; } return v; }   /* test aid: LANDSTALKER_LT_AO=0 switches the room light off */
static int lk_lt_aoh(float x, float y, int dx, int dy) {   /* v8: top of what stands at (x, y) seen from direction (dx, dy); a back wall void = very high, other void = nothing */
  int cx = (int)floorf(x / 16.0f), cy = (int)floorf(y / 16.0f), t;
  if (cx < 0 || cy < 0 || cx >= 74 || cy >= 74) return (dx < 0 || dy < 0) ? 32767 : -32768;
  t = lk_lt_top[cy][cx]; if (t != -32768) return t;
  if ((dx < 0 && (lk_lt_vw[cy][cx] & 1)) || (dy < 0 && (lk_lt_vw[cy][cx] & 2))) return 32767;
  return -32768; }
#define LK_LT_AOR 40.0f   /* v8: reach of the corner shadows (units; a cell is 16) */
static float lk_lt_aoenv(const char *n, float d) { const char *e = getenv(n); float v = e ? (float)atof(e) : d; return v < 0.0f ? 0.0f : v > 1.5f ? 1.5f : v; }
static float lk_lt_aok = -1.0f, lk_lt_aotop = -1.0f;   /* v8: strength of the corner shadows (test aid LANDSTALKER_LT_AOK) and how much darker walls are than floors under the light from above (LANDSTALKER_LT_AOTOP) */
#define LK_LT_AOK lk_lt_aok
static float lk_lt_aoval(float px, float py, int z, int f) {   /* v8: room light share of a surface point (1 = open floor): per direction the highest occluder angle, fading with distance (soft, no cell steps) */
  static float dv[16][2]; static int di[16][2], init;   /* 16 directions (8 gave visible facets) */
  float nx = f == 2 ? 1.0f : 0.0f, ny = f == 3 ? 1.0f : 0.0f, x0 = px + nx * 2.0f, y0 = py + ny * 2.0f, sum = 0.0f, ao; int k, n = 0;
  if (!init) { for (k = 0; k < 16; k++) { float a = (float)k * 0.39269908f; dv[k][0] = cosf(a); dv[k][1] = sinf(a); di[k][0] = dv[k][0] > 0.01f ? 1 : dv[k][0] < -0.01f ? -1 : 0; di[k][1] = dv[k][1] > 0.01f ? 1 : dv[k][1] < -0.01f ? -1 : 0; } init = 1; }
  if (f != 1) { int fl = lk_lt_aoh(x0, y0, 0, 0); if (fl > z) z = fl; }   /* a wall point just below the floor in front of it (view ray rounding): measure from the floor, else a thin dark line at the wall foot */
  for (k = 0; k < 16; k++) { float best = 0.0f, d;
    if (f != 1 && dv[k][0] * nx + dv[k][1] * ny < -0.1f) continue;   /* a wall: only the half space in front of it */
    n++;
    for (d = 2.0f; d < LK_LT_AOR; d += 2.0f) { float fall = 1.0f - d / LK_LT_AOR, t, sn; int h;
      if (fall <= best) break;
      h = lk_lt_aoh(x0 + dv[k][0] * d, y0 + dv[k][1] * d, di[k][0], di[k][1]);
      if (h <= z) continue;
      t = (float)(h - z) / d; sn = t / sqrtf(1.0f + t * t) * fall; if (sn > best) best = sn; }
    sum += best; }
  if (lk_lt_aok < 0.0f) { lk_lt_aok = lk_lt_aoenv("LANDSTALKER_LT_AOK", 0.55f); lk_lt_aotop = lk_lt_aoenv("LANDSTALKER_LT_AOTOP", 0.0f); }
  ao = n ? 1.0f - LK_LT_AOK * sum / (float)n : 1.0f;
  if (f != 1 && lk_lt_aotop > 0.0f) ao *= 1.0f - lk_lt_aotop;   /* light from above: a wall gets less of it than a floor */
  if (f != 1) { int fl = lk_lt_aoh(x0, y0, 0, 0);   /* the foot of a wall: darker just above the floor in front of it */
    if (fl > -32768 && z >= fl) { float c = 1.0f - (float)(z - fl) / 24.0f; if (c > 0.0f) ao *= 1.0f - 0.30f * c; } }
  { int cx = (int)floorf(px / 16.0f), cy = (int)floorf(py / 16.0f); if (f == 1 && cx >= 0 && cy >= 0 && cx < 74 && cy < 74 && lk_lt_wat[cy][cx]) z = 32767; }   /* v8: painted water (our fill) gets no depth darkening: it meets water pixels without geometry (left as they are) = a hard edge */
  if (lk_lt_zref > -32768 && z < lk_lt_zref) { float dd = (float)(lk_lt_zref - z) / 64.0f; if (dd > 1.0f) dd = 1.0f; ao *= 1.0f - 0.18f * dd; }   /* depth: lower levels a little darker */
  return ao < 0.35f ? 0.35f : ao > 1.0f ? 1.0f : ao; }
static int lk_lt_key;                 /* v8 KEY LIGHT (user 2026-11-05: 'nirgends sieht man wirklich das Licht ... schraeg einfallen damit Schatten geworfen werden'): indoor rooms without flames get a soft light from above at an angle (lk_lt_sd), with shadows */
static float lk_lt_kA = 0.80f, lk_lt_kK = 0.30f, lk_lt_kaz = 135.0f, lk_lt_kel = 50.0f;   /* shadow level, light strength, direction (degrees as the sun: azimuth in the world x / y plane, 135 = from the screen's left) */
static int lk_lt_keyopt(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_LT_KEY"), *a = getenv("LANDSTALKER_LT_KAZ"), *l = getenv("LANDSTALKER_LT_KEL"), *s2 = getenv("LANDSTALKER_LT_KS");   /* test aids */
    v = e ? atoi(e) : 1; if (a) lk_lt_kaz = (float)atof(a); if (l) lk_lt_kel = (float)atof(l); if (lk_lt_kel < 10.0f) lk_lt_kel = 10.0f; if (lk_lt_kel > 89.0f) lk_lt_kel = 89.0f;
    if (s2) { lk_lt_kA = (float)atof(s2); if (lk_lt_kA < 0.3f || lk_lt_kA > 1.0f) lk_lt_kA = 0.80f; } lk_lt_kK = 1.10f - lk_lt_kA; }
  return v; }
static void lk_lt_keyset(void) { float az = lk_lt_kaz * 3.14159265f / 180.0f, el = lk_lt_kel * 3.14159265f / 180.0f; lk_lt_sd[0] = cosf(az) * cosf(el); lk_lt_sd[1] = sinf(az) * cosf(el); lk_lt_sd[2] = sinf(el); }
static float lk_lt_keyvisd(const float *sd, float px, float py, float pz) {   /* v8: share of the light from direction sd that reaches a point: march towards it through the height map (back wall voids = walls up to the room's top + 128), soft penumbra */
  static float kbw = -1.0f; float hl = sqrtf(sd[0] * sd[0] + sd[1] * sd[1]), res = 1.0f, t, wt;
  static float kpen = -1.0f; if (kpen < 0.0f) { const char *e = getenv("LANDSTALKER_LT_KPEN"); kpen = e ? (float)atof(e) : 3.0f; if (kpen < 0.5f) kpen = 0.5f; }   /* penumbra: smaller = softer (sun 12; the light from above is a wide opening, soft shadows: lightedges / user rule 'harte Lichtkanten = Fehler') */
  if (kbw < 0.0f) { const char *e = getenv("LANDSTALKER_LT_KBW"); kbw = e ? (float)atof(e) : 40.0f; if (kbw < 0.0f) kbw = 0.0f; }   /* test aid: height of the back walls for the key light above the main floor */
  wt = (lk_lt_zref > -32768 ? (float)lk_lt_zref : 0.0f) + kbw; if (wt < (float)lk_lt_ztop + 1.0f) wt = (float)lk_lt_ztop + 1.0f;   /* the light falls in from inside the room (an opening above it): a back wall shades only a band along its foot, not the whole room (room 12) */
  int dx = sd[0] > 0.01f ? 1 : sd[0] < -0.01f ? -1 : 0, dy = sd[1] > 0.01f ? 1 : sd[1] < -0.01f ? -1 : 0;
  if (hl < 1e-3f) hl = 1e-3f;
  for (t = 2.0f; t < 600.0f; t += t < 32.0f ? 1.0f : 2.0f) {
    float x = px + sd[0] * t, y = py + sd[1] * t, z = pz + sd[2] * t, hh, d, r; int h;
    if (z > wt) return res;
    h = lk_lt_aoh(x, y, dx, dy); if (h == -32768) continue;
    if (h == 32767) { if (z > (lk_lt_zref > -32768 ? (float)lk_lt_zref : 0.0f) + kbw) continue; hh = 1e9f; } else hh = (float)h;
    d = z - hh + 0.5f; if (d <= 0.0f) return 0.0f;
    r = kpen * d / (t * hl); if (r < res) res = r; }
  return res; }
static float lk_lt_keyvis(float px, float py, float pz) { return lk_lt_keyvisd(lk_lt_sd, px, py, pz); }
/* v8 LIGHT SHAFTS (user 2026-11-05: 'leichte Lichtstrahlen ... durch die Decke in einen etwas staubigen Raum, ganz leicht Partikel in den Sonnenstrahlen'; 'nicht immer ganz gleich in jedem Raum'):
   key light rooms get 0..3 shafts along the key light direction (lk_lt_sd); per room a fixed mix from the room number: count, place (open floor of the main height), width, strength,
   tint, dust.  Per block pixel: pool = share of the surface inside the shaft (lit with the key light's shadows, b->sun), beam = glow integrated along the view ray; per frame: dust motes. */
typedef struct { float x, y, z, r, k, cr, cg, cb, h, d[3]; int nd; } lk_lt_shaft_t;   /* d: unit vector up the shaft (to the opening in the ceiling) */
typedef struct { float t, ang, rad, ph, sp, tw; } lk_lt_mote_t;
#define LK_LT_NSH 3
#define LK_LT_NMO 112
#define LK_LT_MOTEH 230.0f   /* dust only in the lower part of the (now very long) shaft, where it is seen */
static lk_lt_shaft_t lk_lt_sh[LK_LT_NSH]; static int lk_lt_nsh; static lk_lt_mote_t lk_lt_mo[LK_LT_NSH][LK_LT_NMO];
static uint8 lk_lt_dmap[512 * 512]; static int16_t lk_lt_dmz[512 * 512]; static int lk_lt_dl[LK_LT_NSH * LK_LT_NMO * 2], lk_lt_dn;
static uint32_t lk_lt_rng;
static float lk_lt_rnd(void) { lk_lt_rng = lk_lt_rng * 1664525u + 1013904223u; return (float)(lk_lt_rng >> 8) * (1.0f / 16777216.0f); }
static int lk_lt_shopt(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_LT_SHAFT"); v = e ? atoi(e) : 1; } return v; }   /* test aid: 0 none, 1 some rooms (default), 2 every key light room, 3 = 2 + shaft #0 beside Nigel (pictures), 4 = on Nigel */
static int lk_lt_shwait; static void lk_lt_free(void);
static void lk_lt_shsetup(void) {
  static int16_t cand[5476][2]; int n = 0, x, y, k, want, tries;
  lk_lt_nsh = 0; if (!lk_lt_key || lk_lt_shopt() <= 0 || lk_lt_zref == -32768) return;
  { int ts = OB(OL(0xA0A00) + 8u * (uint32_t)lk_o_room + 4u) & 0x1F; if (ts == 2 || ts == 8) return; }   /* user 2026-11-05: no shafts in houses (tileset 2: town houses / shops / inns, 8: huts / churches / Kazalt; room table $0A0A00 byte 4) */
  lk_lt_rng = (uint32_t)(lk_o_room + 1) * 2654435761u ^ 0x9E3779B9u; lk_lt_rnd(); lk_lt_rnd();
  if (lk_lt_shopt() >= 3) lk_lt_shwait = 4;   /* test aid: placed beside Nigel once he stands in the room (lk_lt_shstep) */
  if (lk_lt_shopt() == 1 && lk_lt_rnd() < 0.35f) return;   /* about two rooms in three */
  for (y = 1; y < 73; y++) for (x = 1; x < 73; x++) { int a, b2, ok = lk_lt_top[y][x] == lk_lt_zref;   /* open floor: the cell and its 8 neighbours at the main height */
    for (b2 = y - 1; ok && b2 <= y + 1; b2++) for (a = x - 1; a <= x + 1; a++) if (lk_lt_top[b2][a] != lk_lt_zref) { ok = 0; break; }
    if (ok) { cand[n][0] = (int16_t)x; cand[n][1] = (int16_t)y; n++; } }
  if (!n) return;
  want = 1 + (int)(lk_lt_rnd() * 3.0f); if (want > LK_LT_NSH) want = LK_LT_NSH;
  for (tries = 0; tries < 40 && lk_lt_nsh < want; tries++) { int c = (int)(lk_lt_rnd() * (float)n), ok = 1; float cx, cy, w; lk_lt_shaft_t *S;
    if (c >= n) c = n - 1; cx = 16.0f * cand[c][0] + 8.0f; cy = 16.0f * cand[c][1] + 8.0f;
    for (k = 0; k < lk_lt_nsh; k++) if (fabsf(lk_lt_sh[k].x - cx) + fabsf(lk_lt_sh[k].y - cy) < 72.0f) ok = 0;
    if (!ok) continue;
    S = &lk_lt_sh[lk_lt_nsh++]; S->x = cx + (lk_lt_rnd() - 0.5f) * 10.0f; S->y = cy + (lk_lt_rnd() - 0.5f) * 10.0f; S->z = (float)lk_lt_zref;
    S->r = 22.0f + lk_lt_rnd() * 26.0f;   /* user 2026-11-05: 'breiter mit besserem Verlauf, Octopath Traveler Stil' (was 10..24) */ S->k = 0.55f + lk_lt_rnd() * 0.45f; S->h = 460.0f + lk_lt_rnd() * 60.0f;   /* user 2026-11-05: shafts must leave the picture at the top (from the ceiling, not starting in the middle of the room): far above every back wall */ S->nd = 40 + (int)(lk_lt_rnd() * 60.0f);   /* user 2026-11-05: 'ein paar mehr Staubpartikel' (was 10..48) */ if (S->nd > LK_LT_NMO) S->nd = LK_LT_NMO;
    { float az = (lk_lt_kaz + (lk_lt_rnd() - 0.5f) * 50.0f) * 3.14159265f / 180.0f, el = (74.0f + lk_lt_rnd() * 12.0f) * 3.14159265f / 180.0f;   /* user 2026-11-05: 'viel zu steil ... als wuerden die links aus der Wand kommen, nicht von der Decke': nearly vertical, 74..86 degrees, leaning roughly like the key light */
      S->d[0] = cosf(az) * cosf(el); S->d[1] = sinf(az) * cosf(el); S->d[2] = sinf(el); }
    w = lk_lt_rnd(); S->cr = 0.84f + 0.08f * w; S->cg = 0.88f + 0.04f * w; S->cb = 0.92f - 0.02f * w;   /* user 2026-11-05: 'weniger hell, fahles Licht': pale grey white, a hint warmer or cooler per room */
    for (k = 0; k < S->nd; k++) { lk_lt_mote_t *M = &lk_lt_mo[lk_lt_nsh - 1][k]; M->t = lk_lt_rnd() * LK_LT_MOTEH; M->ang = lk_lt_rnd() * 6.2831853f; M->rad = sqrtf(lk_lt_rnd()) * 0.85f;
      M->ph = lk_lt_rnd() * 6.2831853f; M->sp = 0.04f + lk_lt_rnd() * 0.10f; M->tw = 0.02f + lk_lt_rnd() * 0.05f; } }
  if (lk_lt_dbg == 1) for (k = 0; k < lk_lt_nsh; k++) printf("shaft: room %%d #%%d at (%%.0f, %%.0f, %%.0f) r %%.0f k %%.2f h %%.0f motes %%d\n", lk_o_room, k, lk_lt_sh[k].x, lk_lt_sh[k].y, lk_lt_sh[k].z, lk_lt_sh[k].r, lk_lt_sh[k].k, lk_lt_sh[k].h, lk_lt_sh[k].nd);
}
static float lk_lt_shdist(const lk_lt_shaft_t *S, float px, float py, float pz, float *sv) {   /* distance of a point from the shaft's axis (+ position along it) */
  float vx = px - S->x, vy = py - S->y, vz = pz - S->z, s2 = vx * S->d[0] + vy * S->d[1] + vz * S->d[2], qx = vx - s2 * S->d[0], qy = vy - s2 * S->d[1], qz = vz - s2 * S->d[2];
  *sv = s2; return sqrtf(qx * qx + qy * qy + qz * qz); }
static void lk_lt_shblock(lk_lt_blk *b, int U0, int V0) {   /* pool + beam of one block */
  int i, k; memset(b->beam, 0, sizeof b->beam); memset(b->pool, 0, sizeof b->pool);
  for (k = 0; k < lk_lt_nsh; k++) { const lk_lt_shaft_t *S = &lk_lt_sh[k];
    float u0 = S->x - S->y + 1184.0f, v0 = (S->x + S->y) * 0.5f - S->z, u1 = u0 + (S->d[0] - S->d[1]) * S->h, v1 = v0 + ((S->d[0] + S->d[1]) * 0.5f - S->d[2]) * S->h, m = S->r * 2.0f + 8.0f;
    if ((float)(U0 + 32) < fminf(u0, u1) - m || (float)U0 > fmaxf(u0, u1) + m || (float)(V0 + 32) < fminf(v0, v1) - m - 20.0f || (float)V0 > fmaxf(v0, v1) + m + 20.0f) continue;
    for (i = 0; i < 1024; i++) { int U = U0 + (i & 31), V = V0 + (i >> 5), zs = b->face[i] ? b->z[i] : (int)S->z - 24; float sum = 0.0f, z, px, py, sv, q, w;
      if (b->face[i]) { lk_lt_pos(U, V, zs, &px, &py); q = lk_lt_shdist(S, px, py, (float)zs, &sv);
        if (q < S->r * 1.25f && sv > -8.0f) { float nx = b->face[i] == 2 ? 1.0f : 0.0f, ny = b->face[i] == 3 ? 1.0f : 0.0f, nz = b->face[i] == 1 ? 1.0f : 0.0f;
          w = (S->r * 1.25f - q) / (S->r * 1.1f); if (w > 1.0f) w = 1.0f; w = w * w * (3.0f - 2.0f * w) * S->k * 0.8f;   /* soft wide edge */
          w *= lk_lt_keyvisd(S->d, px + nx * 3.0f, py + ny * 3.0f, (float)zs + nz * 3.0f);   /* the shaft's own shadows (v8 MT: no global swap) */ w += (float)b->pool[i] * (1.0f / 255.0f); b->pool[i] = (uint8)(w >= 1.0f ? 255 : (int)(w * 255.0f)); } }
      for (z = (float)zs + 2.0f; z < S->z + S->h * S->d[2]; z += 4.0f) { float fa; lk_lt_pos(U, V, (int)z, &px, &py); q = lk_lt_shdist(S, px, py, z, &sv);
        if (q >= S->r || sv < 0.0f || sv > S->h) continue;
        w = 1.0f - (q / S->r) * (q / S->r); w *= w;   /* soft gaussian-like edge, no rim */
        fa = sv < 70.0f ? sv / 70.0f : 1.0f; if (sv > S->h - 70.0f) fa *= (S->h - sv) / 70.0f; fa *= sv < 220.0f ? 0.55f + 0.45f * sv / 220.0f : 1.0f;   /* fades into the floor, brighter towards the opening, soft top */
        sum += w * fa; }
      sum *= 0.26f * S->k;   /* the wider beam is crossed by more samples */ sum += (float)b->beam[i] * (1.0f / 255.0f); b->beam[i] = (uint8)(sum >= 1.0f ? 255 : (int)(sum * 255.0f)); }
    if (lk_lt_dbg == 9) { int nb = 0, np = 0, mb = 0; for (i = 0; i < 1024; i++) { if (b->beam[i]) nb++; if (b->pool[i]) np++; if (b->beam[i] > mb) mb = b->beam[i]; } if (nb || np) printf("shaft block %%d,%%d: beam %%d px (max %%d) pool %%d px\n", U0, V0, nb, mb, np); } }
}
static void lk_lt_shstep(long fr) {   /* dust motes: drift slowly down the shaft, swirl, twinkle; drawn into a small map (picture coordinates & 511) with their height for the occlusion test */
  int k, j;
  for (j = 0; j < lk_lt_dn; j++) lk_lt_dmap[lk_lt_dl[j]] = 0;
  if (lk_lt_shwait > 0 && --lk_lt_shwait == 0 && lk_lt_key) { lk_lt_shaft_t *S = &lk_lt_sh[0]; if (!lk_lt_nsh) { lk_lt_nsh = 1; S->r = 32.0f; S->k = 0.8f; S->h = 480.0f; S->nd = 70; S->cr = 0.88f; S->cg = 0.90f; S->cb = 0.92f; S->d[0] = -0.17f; S->d[1] = 0.17f; S->d[2] = 0.97f; }
    { int jj, cx, cy; for (jj = 0; jj < lk_lt_nf; jj++) if (lk_lt_f[jj].tag == 1) break;   /* Nigel (entity 0) of this frame's figure list */
      if (jj < lk_lt_nf) { int on = lk_lt_shopt() == 4; S->x = lk_lt_f[jj].fx + (on ? 2.0f : 8.0f); S->y = lk_lt_f[jj].fy + (on ? 2.0f : 44.0f); }   /* 4: right on Nigel (his shadow in the shaft) */ else { S->x = (float)SW(0xFF5414) + 8.0f; S->y = (float)SW(0xFF5416) + 44.0f; }
      cx = (int)(S->x / 16.0f); cy = (int)(S->y / 16.0f); S->z = (cx >= 0 && cy >= 0 && cx < 74 && cy < 74 && lk_lt_top[cy][cx] != -32768) ? (float)lk_lt_top[cy][cx] : (float)lk_lt_zref; }
    lk_lt_free(); if (lk_lt_dbg == 1) printf("shaft: test #0 at (%%.0f, %%.0f, %%.0f)\n", S->x, S->y, S->z); }
  lk_lt_dn = 0; if (!lk_lt_nsh) return;
  for (k = 0; k < lk_lt_nsh; k++) { const lk_lt_shaft_t *S = &lk_lt_sh[k]; float ex, ey, ez = 0.0f, fx, fy, fz, l;
    ex = S->d[1]; ey = -S->d[0]; l = sqrtf(ex * ex + ey * ey); if (l < 1e-3f) { ex = 1.0f; ey = 0.0f; l = 1.0f; } ex /= l; ey /= l;   /* a basis across the shaft */
    fx = S->d[1] * ez - S->d[2] * ey; fy = S->d[2] * ex - S->d[0] * ez; fz = S->d[0] * ey - S->d[1] * ex;
    for (j = 0; j < S->nd; j++) { lk_lt_mote_t *M = &lk_lt_mo[k][j]; float a, rr, px, py, pz, br, fa; int U, V, idx, v;
      M->t -= M->sp; if (M->t < 4.0f) M->t += LK_LT_MOTEH - 8.0f; M->ang += 0.006f + 0.004f * M->sp * 10.0f;
      a = M->ang + 0.6f * sinf(M->ph + (float)fr * 0.011f); rr = M->rad * S->r;
      px = S->x + S->d[0] * M->t + (ex * cosf(a) + fx * sinf(a)) * rr; py = S->y + S->d[1] * M->t + (ey * cosf(a) + fy * sinf(a)) * rr; pz = S->z + S->d[2] * M->t + (ez * cosf(a) + fz * sinf(a)) * rr;
      fa = M->t < 20.0f ? M->t / 20.0f : M->t > LK_LT_MOTEH - 40.0f ? (LK_LT_MOTEH - M->t) / 40.0f : 1.0f; if (fa <= 0.0f) continue;
      br = (0.35f + 0.65f * (0.5f + 0.5f * sinf(M->ph * 3.0f + (float)fr * M->tw))) * fa * (1.0f - 0.5f * M->rad) * S->k;
      U = (int)lrintf(px - py + 1184.0f); V = (int)lrintf((px + py) * 0.5f - pz); idx = ((V & 511) << 9) | (U & 511);
      v = (int)(br * 150.0f); if (v < 8) continue; if (v > 255) v = 255;
      if (lk_lt_dmap[idx] < v) { if (!lk_lt_dmap[idx] && lk_lt_dn < LK_LT_NSH * LK_LT_NMO * 2) lk_lt_dl[lk_lt_dn++] = idx; lk_lt_dmap[idx] = (uint8)v; lk_lt_dmz[idx] = (int16_t)pz; } } }
}
/* v8 AMBIENT PARTICLES (user 2026-11-05 night: 'Umgebungs-Partikel je Gegend' chosen from the modern effects list, MODERN_IDEAS (C) 2): leaves drifting down on routes / in forests,
   fireflies in shaded spots there, sparks rising from flames, embers over lava, water drops in caves (a small splash where they land).  Particles live in the room's world
   (positions on the computed surfaces), are drawn into a small map in picture coordinates (& 511) with their height + depth, so walls / figures in front hide them. */
#define LK_AM_N 224
typedef struct { float x, y, z, vx, vy, vz, ph, gz; int16_t age, life; uint8_t kind; } lk_am_p;   /* kind 1 leaf, 2 firefly, 3 spark, 4 ember, 5 drop, 6 splash */
static lk_am_p lk_am_ps[LK_AM_N]; static int lk_am_np, lk_am_bio;
static int16_t lk_am_spot[16][3]; static int lk_am_nspot, lk_am_ffmax;   /* LK_DAYNIGHT v4: firefly spots of the room (cell x, y, floor z) and the cap */
static uint32_t lk_am_map[512 * 512]; static int16_t lk_am_mz[512 * 512], lk_am_md[512 * 512]; static int lk_am_dl[LK_AM_N * 10], lk_am_dn; static uint32_t lk_am_rng = 12345u;
static float lk_am_rnd(void) { lk_am_rng = lk_am_rng * 1664525u + 1013904223u; return (float)(lk_am_rng >> 8) * (1.0f / 16777216.0f); }
static int lk_am_o = -1;   /* Options > Graphics > Particles On / Off (id 49, user 2026-11-05: 'bitte als Partikeleffekte optional machen im Menue'), ~/.landstalker_particles, env LANDSTALKER_AMBIENT=0|1 wins, default On (needs Lighting On) */
int lk_am_get(void) { if (lk_am_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_AMBIENT"); char pth[512]; FILE *f; int v = 1; snprintf(pth, sizeof pth, "%%s/.landstalker_particles", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%%d", &v) != 1) v = 1; fclose(f); } if (e) v = atoi(e); lk_am_o = v ? 1 : 0; } return lk_am_o; }
void lk_am_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_am_get(); lk_am_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_particles", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_am_o); fclose(f); } }
static int lk_am_opt(void) { return lk_am_get(); }
static int lk_am_force(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_AMBIENT_FORCE"); v = e ? atoi(e) : 0; } return v; }   /* test aid: these kinds in every lit room (bits: 1 leaves, 2 fireflies, 4 sparks, 8 drops, 16 embers) */
static void lk_am_setup(void) {   /* kinds of the room (lk_lt_newroom, after the lights) */
  int ts = lk_o_room >= 0 ? (OB(OL(0xA0A00) + 8u * (uint32_t)lk_o_room + 4u) & 0x1F) : -1, k;
  lk_am_np = 0; lk_am_bio = 0; lk_am_rng = (uint32_t)(lk_o_room + 7) * 2246822519u;
  if (lk_o_room < 0 || (lk_o_room >= 139 && lk_o_room <= 143) || lk_o_room == 148) return;   /* (the option is asked every frame in lk_am_step: switching it in the menu works at once) */
  /* leaves (1) removed and fireflies (2) kept for a later day / night cycle (user 2026-11-05: 'die Blaetter raus', 'Gluehwuermchen heben wir uns auf fuer den Tag-Nacht-Zyklus'); both still work with LANDSTALKER_AMBIENT_FORCE */
  if (ts == 4 || ts == 5 || ts == 9) lk_am_bio |= 8;   /* caves, waterfall shrine, swamp shrine */
  for (k = 0; k < lk_lt_nl; k++) if (lk_lt_l[k].lava != 2) lk_am_bio |= lk_lt_l[k].lava ? 16 : 4;   /* (window lights: no sparks) */
  if (lk_am_force()) lk_am_bio = lk_am_force();
  lk_am_nspot = 0; lk_am_ffmax = 0;
  if (lk_lt_sun && ts != 0 && !(lk_o_room >= 601 && lk_o_room <= 603) && lk_o_room != 737 && !(lk_o_room >= 31 && lk_o_room <= 33)) {   /* v4 FIREFLY SPOTS (user 2026-11-06: 'nur spothaft, nahe Baeumen oder Straeuchern oder am Wasser, nicht in der Stadt;
       Ausnahme Destel, aber weniger'): walkable cells next to a bush / pine (lk_lt_tk), a small object (tree, lk_lt_ocl 1) or our water fill; up to 6 spots >= 7 cells apart (Destel 3), 10 fireflies (Destel 4) (v5), not in the towns
       (tileset 0 = Ryuma / Mercator / Verla, Gumi 601..603, Kazalt 737, the castle yard 31..33) */
    static int16_t cand[2048][3]; int nc = 0, x, y, want = lk_o_room == 726 ? 3 : 6, tries;
    for (y = 1; y < 73 && nc < 2048; y++) for (x = 1; x < 73 && nc < 2048; x++) { int w = UW(0xFFD192 + 148 * y + 2 * x), a, b2, near = 0;
      if (w == 0x4000 || ((w >> 8) & 0x60)) continue;
      for (b2 = y - 1; b2 <= y + 1 && !near; b2++) for (a = x - 1; a <= x + 1; a++) { int ob = lk_lt_obj[b2][a]; if (lk_lt_tk[b2][a] == 1 || lk_lt_tk[b2][a] == 2 || lk_lt_wat[b2][a] || (ob > 0 && ob < 1024 && lk_lt_ocl[ob] == 1)) { near = 1; break; } }
      if (near) { cand[nc][0] = (int16_t)x; cand[nc][1] = (int16_t)y; cand[nc][2] = (int16_t)(16 * ((w >> 8) & 15)); nc++; } }
    for (tries = 0; tries < 400 && lk_am_nspot < want && nc; tries++) { int c = (int)(lk_am_rnd() * (float)nc) %% nc, q, ok = 1;
      for (q = 0; q < lk_am_nspot; q++) if (abs(lk_am_spot[q][0] - cand[c][0]) < 7 && abs(lk_am_spot[q][1] - cand[c][1]) < 7) { ok = 0; break; }
      if (ok) { lk_am_spot[lk_am_nspot][0] = cand[c][0]; lk_am_spot[lk_am_nspot][1] = cand[c][1]; lk_am_spot[lk_am_nspot][2] = cand[c][2]; lk_am_nspot++; } }
    lk_am_ffmax = lk_o_room == 726 ? 4 : 10;   /* v5 (user 2026-11-06: 'noch zu viele Gluehwuermchen'; was 30 / 8, 14 spots) */
    if (lk_lt_dbg == 1) printf("fireflies: room %%d %%d candidate cells, %%d spots\n", lk_o_room, nc, lk_am_nspot); }
}
static int lk_am_surf(int U, int V, float *px, float *py, float *pz, int *sun) {   /* the floor under a picture pixel from the computed blocks (0: not computed / no floor) */
  int bx = lk_lt_fdiv(U, 32), by = lk_lt_fdiv(V, 32), i; const lk_lt_blk *b;
  if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH || !(b = lk_lt_b[by][bx])) return 0;
  i = ((V & 31) << 5) | (U & 31); if (b->face[i] != 1) return 0;
  lk_lt_pos(U, V, b->z[i], px, py); *pz = (float)b->z[i]; *sun = lk_lt_sun ? (lk_dn_mix && b->sungen == lk_dn_gen ? b->sun[i] + (((int)b->sunn[i] - b->sun[i]) * lk_dn_mix >> 8) : b->sun[i]) : 255; return 1; }
static void lk_am_px(int U, int V, float z, float d, uint32_t rgb, float a, int add) {   /* one particle pixel (the strongest wins); map word: rgb + alpha 0..127 in bits 24..30 + additive flag bit 31 */
  int q = ((V & 511) << 9) | (U & 511), al = (int)(a * 127.0f + 0.5f);
  if (al <= 0) return; if (al > 127) al = 127;
  if (lk_am_map[q] && (int)((lk_am_map[q] >> 24) & 0x7F) >= al) return;
  if (!lk_am_map[q] && lk_am_dn < LK_AM_N * 10) lk_am_dl[lk_am_dn++] = q;
  lk_am_map[q] = (rgb & 0xFFFFFFu) | ((uint32_t)al << 24) | (add ? 0x80000000u : 0u); lk_am_mz[q] = (int16_t)z; lk_am_md[q] = (int16_t)d; }
static void lk_am_dot(const lk_am_p *P, int du, int dv, uint32_t rgb, float a, int add) {
  int U = (int)lrintf(P->x - P->y + 1184.0f) + du, V = (int)lrintf((P->x + P->y) * 0.5f - P->z) + dv; lk_am_px(U, V, P->z, P->x + P->y, rgb, a, add); }
static lk_am_p *lk_am_new(int kind) { lk_am_p *P; if (lk_am_np >= LK_AM_N) return 0; P = &lk_am_ps[lk_am_np++]; memset(P, 0, sizeof *P); P->kind = (uint8_t)kind; P->ph = lk_am_rnd() * 6.2831853f; return P; }
static void lk_am_step(long fr) {   /* once per lit frame (lk_lt_step, before the drawn area is reset): spawn, move, draw */
  int j, k, nff = 0; (void)fr;
  for (j = 0; j < lk_am_dn; j++) lk_am_map[lk_am_dl[j]] = 0;
  lk_am_dn = 0;
  if (!lk_am_opt()) { lk_am_np = 0; return; }
  if ((!lk_am_bio && !(lk_dn_night && lk_am_nspot)) || lk_lt_umax < lk_lt_umin) return;   /* LK_DAYNIGHT v3 / v4: at night fireflies at the room's spots even without other particles */
  for (j = 0; j < lk_am_np; j++) if (lk_am_ps[j].kind == 2) nff++;
  if (lk_dn_night && lk_am_nspot && nff < lk_am_ffmax && lk_am_rnd() < 0.12f) {   /* v4: a firefly at a spot that is on screen, hovering 6..30 units above its floor within 20 units */
    int q = (int)(lk_am_rnd() * (float)lk_am_nspot) %% lk_am_nspot; float sx = 16.0f * lk_am_spot[q][0] + 8.0f, sy = 16.0f * lk_am_spot[q][1] + 8.0f, sz = (float)lk_am_spot[q][2];
    int U = (int)(sx - sy) + 1184, V = (int)((sx + sy) * 0.5f - sz); lk_am_p *P;
    float nx2 = sx + (lk_am_rnd() - 0.5f) * 32.0f, ny2 = sy + (lk_am_rnd() - 0.5f) * 32.0f; int wc = (nx2 >= 0.0f && ny2 >= 0.0f && nx2 < 1184.0f && ny2 < 1184.0f) ? UW(0xFFD192 + 148 * (int)(ny2 / 16.0f) + 2 * (int)(nx2 / 16.0f)) : 0x4000;
    if (wc != 0x4000 && !((wc >> 8) & 0x40) && U >= lk_lt_umin - 24 && U <= lk_lt_umax + 24 && V >= lk_lt_vmin - 24 && V <= lk_lt_vmax + 24 && (P = lk_am_new(2))) {   /* v6: only above a room cell (user 2026-11-06: fireflies outside the room) */
      P->x = nx2; P->y = ny2; P->gz = sz; P->z = sz + 6.0f + lk_am_rnd() * 22.0f; P->life = (int16_t)(160 + lk_am_rnd() * 160.0f); nff++; } }   /* a small swarm per spot (shorter life: they stay near it) */
  { int tries; float px, py, pz; int sun;   /* spawns on the floor of the area drawn last frame */
    for (tries = 0; tries < 6; tries++) { int U = lk_lt_umin + (int)(lk_am_rnd() * (float)(lk_lt_umax - lk_lt_umin + 1)), V = lk_lt_vmin + (int)(lk_am_rnd() * (float)(lk_lt_vmax - lk_lt_vmin + 1)), want = 0; float r = lk_am_rnd();
      if ((lk_am_bio & 1) && r < 0.028f) want = 1; else if ((lk_am_bio & 2) && r > 0.975f && nff < 16) want = 2; else if ((lk_am_bio & 8) && r > 0.40f && r < 0.408f) want = 5;
      if (!want || !lk_am_surf(U, V, &px, &py, &pz, &sun)) continue;
      if (want == 5) { int cx = (int)floorf(px / 16.0f), cy = (int)floorf(py / 16.0f), w2;   /* drops land on WALKABLE floor only (user 2026-11-05: 'nicht immer nur am Boden': tops of walls / pillars / boxes are floor faces too) */
        if (cx < 0 || cy < 0 || cx >= 74 || cy >= 74) continue;
        w2 = UW(0xFFD192 + 148 * cy + 2 * cx); if (w2 == 0x4000 || ((w2 >> 8) & 0x60) || (int)pz != 16 * ((w2 >> 8) & 15)) continue; }
      if (want == 2 && sun > 140) continue;   /* fireflies only in the shade (test aid LANDSTALKER_AMBIENT_FORCE=2; at night they come from the spots, below) */
      { lk_am_p *P = lk_am_new(want); if (!P) break; P->gz = pz;
        if (want == 1) { P->x = px - 30.0f; P->y = py + 30.0f; P->z = pz + 90.0f + lk_am_rnd() * 70.0f; P->vx = 0.22f + lk_am_rnd() * 0.15f; P->vy = -0.18f - lk_am_rnd() * 0.12f; P->vz = -0.30f - lk_am_rnd() * 0.20f; P->life = (int16_t)((P->z - pz) / -P->vz + 60.0f); }
        else if (want == 2) { P->x = px; P->y = py; P->z = pz + 6.0f + lk_am_rnd() * 14.0f; P->life = (int16_t)(240 + lk_am_rnd() * 240.0f); }
        else { float ztop = (px + py) * 0.5f - (float)lk_lt_vmin + 8.0f;   /* above the top of the picture (user 2026-11-05: 'Wassertropfen muessen ueber dem Raum anfangen zu fallen, sonst spawnen sie aus dem Nichts') */
          P->x = px; P->y = py; P->z = ztop > pz + 110.0f ? ztop + lk_am_rnd() * 20.0f : pz + 110.0f + lk_am_rnd() * 30.0f; P->vz = -3.2f; P->life = (int16_t)((P->z - pz) / 3.2f + 20.0f); } } } }
  for (k = 0; k < lk_lt_nl; k++) { const lk_lt_light *L = &lk_lt_l[k]; lk_am_p *P;   /* sparks / embers from the flames of the room */
    if (L->lava == 2) continue;   /* LK_DAYNIGHT v3: window lights */
    if (L->lava ? !(lk_am_bio & 16) || lk_am_rnd() > 0.05f : !(lk_am_bio & 4) || lk_am_rnd() > 0.05f) continue;
    if (!(P = lk_am_new(L->lava ? 4 : 3))) break;
    P->x = L->x + (lk_am_rnd() - 0.5f) * (L->lava ? 40.0f : 4.0f); P->y = L->y + (lk_am_rnd() - 0.5f) * (L->lava ? 40.0f : 4.0f); P->z = L->z - (L->lava ? 8.0f : 2.0f);
    P->vx = (lk_am_rnd() - 0.5f) * 0.25f; P->vy = (lk_am_rnd() - 0.5f) * 0.25f; P->vz = L->lava ? 0.30f + lk_am_rnd() * 0.30f : 0.55f + lk_am_rnd() * 0.40f; P->life = (int16_t)(L->lava ? 60 + lk_am_rnd() * 50.0f : 22 + lk_am_rnd() * 22.0f); }
  for (j = 0, k = 0; j < lk_am_np; j++) { lk_am_p *P = &lk_am_ps[j]; float t, a;
    if (++P->age >= P->life) continue;
    if (P->kind != 2 && P->kind != 5) { int cx = (int)floorf(P->x / 16.0f), cy = (int)floorf(P->y / 16.0f);   /* v9 (user 2026-11-06, recording rec_20261106_1322 frame 2688: sparks over the black void beside the waterfall shrine 178): a particle over a cell outside the room is gone (fireflies turn back, drops land on floor cells) */
      if (cx < 0 || cy < 0 || cx >= 74 || cy >= 74 || UW(0xFFD192 + 148 * cy + 2 * cx) == 0x4000) continue; }
    t = (float)P->age;
    if (P->kind == 1) {   /* leaf: sways while it drifts down, lies on the ground for a moment, fades */
      static const uint32_t lc[4] = { 0x6E962Eu, 0xA89632u, 0x8C5A28u, 0x587A28u }; float sw = sinf(P->ph + t * 0.09f);
      if (P->z > P->gz) { P->x += P->vx + 0.35f * sw; P->y += P->vy + 0.35f * cosf(P->ph * 0.7f + t * 0.07f); P->z += P->vz; if (P->z < P->gz) P->z = P->gz; }
      a = P->life - P->age < 40 ? (float)(P->life - P->age) / 40.0f : 1.0f; a *= t < 15.0f ? t / 15.0f : 1.0f;
      lk_am_dot(P, 0, 0, lc[(int)(P->ph * 0.6f) & 3], 0.95f * a, 0); lk_am_dot(P, sw > 0.0f ? 1 : -1, 0, lc[(int)(P->ph * 0.6f) & 3], 0.70f * a, 0); }
    else if (P->kind == 2) {   /* firefly: slow wander, bob, blink, soft glow */
      float br = 0.5f + 0.5f * sinf(P->ph + t * 0.06f); P->vx += (lk_am_rnd() - 0.5f) * 0.03f; P->vy += (lk_am_rnd() - 0.5f) * 0.03f;
      if (P->vx > 0.25f) P->vx = 0.25f; if (P->vx < -0.25f) P->vx = -0.25f; if (P->vy > 0.25f) P->vy = 0.25f; if (P->vy < -0.25f) P->vy = -0.25f;
      P->x += P->vx; P->y += P->vy; P->z += 0.08f * sinf(P->ph * 1.3f + t * 0.05f);
      { int cx = (int)floorf(P->x / 16.0f), cy = (int)floorf(P->y / 16.0f), wc = (cx >= 0 && cy >= 0 && cx < 74 && cy < 74) ? UW(0xFFD192 + 148 * cy + 2 * cx) : 0x4000;   /* v6: drifted over the void / out of the room: turn back */
        if (wc == 0x4000) { P->vx = -P->vx; P->vy = -P->vy; P->x += 2.0f * P->vx; P->y += 2.0f * P->vy; if (P->life - P->age > 30) P->life = (int16_t)(P->age + 30); } }
      a = (t < 40.0f ? t / 40.0f : 1.0f) * (P->life - P->age < 40 ? (float)(P->life - P->age) / 40.0f : 1.0f) * (br > 0.25f ? (br - 0.25f) / 0.75f : 0.0f);
      lk_am_dot(P, 0, 0, 0xFFF078u, 0.85f * a, 1); lk_am_dot(P, 1, 0, 0xC8E650u, 0.30f * a, 1); lk_am_dot(P, -1, 0, 0xC8E650u, 0.30f * a, 1); lk_am_dot(P, 0, 1, 0xC8E650u, 0.30f * a, 1); lk_am_dot(P, 0, -1, 0xC8E650u, 0.30f * a, 1); }
    else if (P->kind == 3 || P->kind == 4) {   /* spark / ember: rises, cools from yellow to red, fades */
      float f = t / (float)P->life; uint32_t c = f < 0.3f ? 0xFFE68Cu : f < 0.65f ? 0xFF9030u : 0xC8441Eu;
      P->x += P->vx + (P->kind == 4 ? 0.15f * sinf(P->ph + t * 0.1f) : 0.0f); P->y += P->vy; P->z += P->vz; P->vz *= P->kind == 3 ? 0.975f : 0.995f;
      lk_am_dot(P, 0, 0, c, (1.0f - f) * (P->kind == 3 ? 0.9f : 0.75f), 1); }
    else if (P->kind == 5) {   /* water drop: falls, then a splash where it lands */
      P->z += P->vz; if (P->z <= P->gz) { P->z = P->gz; P->kind = 6; P->age = 0; P->life = 12; }
      else { lk_am_dot(P, 0, 0, 0xC8DCF0u, 0.75f, 0); lk_am_dot(P, 0, -1, 0xC8DCF0u, 0.45f, 0); } }
    else if (P->kind == 6) {   /* splash: a small ring widening on the floor */
      int rr = 1 + P->age / 4; a = 0.7f * (1.0f - t / (float)P->life);
      lk_am_dot(P, rr, 0, 0xDCEBFAu, a, 0); lk_am_dot(P, -rr, 0, 0xDCEBFAu, a, 0); lk_am_dot(P, 0, (rr + 1) / 2, 0xDCEBFAu, a, 0); lk_am_dot(P, 0, -(rr + 1) / 2, 0xDCEBFAu, a, 0); }
    lk_am_ps[k++] = *P; }
  lk_am_np = k; }
static void lk_am_mix(int U, int V, int zs, int fd, int *r, int *g, int *b) {   /* blend the particle of this picture pixel (zs: surface height, -32768 = none; fd: depth x + y of a figure pixel, -32768 = scenery) */
  int q = ((V & 511) << 9) | (U & 511); uint32_t m = lk_am_map[q]; float a; int cr, cg, cb;
  if (!m) return;
  if (zs != -32768 && lk_am_mz[q] < zs - 2) return;   /* behind / under the surface */
  if (fd != -32768 && lk_am_md[q] < fd - 4) return;   /* behind the figure */
  a = (float)((m >> 24) & 0x7F) * (1.0f / 127.0f) * lk_lt_fadek; cr = (int)((m >> 16) & 255);   /* (v4: fades with the palette) */ cg = (int)((m >> 8) & 255); cb = (int)(m & 255);
  if (m & 0x80000000u) { *r += (int)((float)cr * a); *g += (int)((float)cg * a); *b += (int)((float)cb * a); }
  else { *r += (int)((float)(cr - *r) * a); *g += (int)((float)(cg - *g) * a); *b += (int)((float)(cb - *b) * a); } }
static float lk_lt_term(float px, float py, float pz, float nx, float ny, float nz, const lk_lt_light *L, int shadow) {
  float vx = L->x - px, vy = L->y - py, vz = L->z - pz, d = sqrtf(vx * vx + vy * vy + vz * vz), ndl, att, t;
  float rad = L->rad > 0.0f ? L->rad : LK_LT_RAD, kk = L->k > 0.0f ? L->k : 1.0f;
  if (d >= rad || d < 0.001f) return d < 0.001f ? kk : 0.0f;
  ndl = (nx * vx + ny * vy + nz * vz) / d; if (ndl < 0) ndl = 0;
  att = kk * (1.0f - d / rad) * (1.0f - d / rad);
  if (shadow && !lk_lt_sun) {   /* indoors the flame is a small AREA (user 2026-11-05: hard step shadows): the shadow share of 2 points 5 units apart along the screen's x (world (1, -1): softens edges along both world axes), each with the soft clearance edge
       (4 points cost twice the time, 60..80 ms block peaks at room entry; 2 points measured 2026-11-05) */
    static const float off[2][3] = { {3.5f, -3.5f, 1.0f}, {-3.5f, 3.5f, -1.0f} };
    float sx = px + nx * 3.0f, sy = py + ny * 3.0f, sz = pz + nz * 3.0f, sum = 0.0f; int o;
    for (o = 0; o < 2; o++) { float wx = L->x + off[o][0] - sx, wy = L->y + off[o][1] - sy, wz = L->z + off[o][2] - sz, e = sqrtf(wx * wx + wy * wy + wz * wz), res = 1.0f;
      for (t = 2.0f; t < e - 3.0f; t += 2.0f) { float qx = sx + wx * t / e, qy = sy + wy * t / e, qz = sz + wz * t / e, cl, r; int cx, cy, top;
        if (lk_lt_solid(qx, qy, qz)) { res = 0.0f; break; }
        cx = (int)floorf(qx / 16.0f); cy = (int)floorf(qy / 16.0f); top = lk_lt_cell(cx, cy);
        if (cx >= 0 && cy >= 0 && cx < 74 && cy < 74 && lk_lt_thin[cy][cx] > -32768) top = lk_lt_thin[cy][cx];
        if (top > -32768) { cl = qz - (float)top; r = LK_LT_IPEN * cl / t; if (r < res) res = r; } }
      sum += res < 0.0f ? 0.0f : res; }
    return att * (0.25f + 0.75f * ndl) * sum * 0.5f;
  }
  if (shadow) {   /* v3: march from 3 units in front of the surface (a wall pixel lies on the cell border: the march along the wall hit the wall itself = box-shaped shadows, user: church wall by the books) */
    float sx = px + nx * 3.0f, sy = py + ny * 3.0f, sz = pz + nz * 3.0f, wx = L->x - sx, wy = L->y - sy, wz = L->z - sz, e = sqrtf(wx * wx + wy * wy + wz * wz), res = 1.0f;
    for (t = 2.0f; t < e - 3.0f; t += 2.0f) { float qx = sx + wx * t / e, qy = sy + wy * t / e, qz = sz + wz * t / e, cl, r;
      if (lk_lt_solid(qx, qy, qz)) return 0.0f;
      if (!lk_lt_sun) {   /* SOFT EDGES indoors (user 2026-11-05: 'ausgefranzte Ecken'): a ray that passes just over a block top loses part of the light (clearance / distance), so the
           16 x 16 steps of the height map no longer give hard stair edges; the share grows over LK_LT_IPEN units of clearance per unit of distance */
        int cx = (int)floorf(qx / 16.0f), cy = (int)floorf(qy / 16.0f), top = lk_lt_cell(cx, cy);
        if (cx >= 0 && cy >= 0 && cx < 74 && cy < 74 && lk_lt_thin[cy][cx] > -32768) top = lk_lt_thin[cy][cx];
        if (top > -32768) { cl = qz - (float)top; r = LK_LT_IPEN * cl / t; if (r < res) res = r; } } }
    if (res < 0.0f) res = 0.0f;
    return att * (0.25f + 0.75f * ndl) * res;
  }
  return att * (0.25f + 0.75f * ndl);
}
static float lk_lt_azd = 90.0f, lk_lt_eld = 55.0f; static volatile int lk_lt_sunmov;
static float lk_lt_azt = -1.0f, lk_lt_elt = 55.0f; static volatile double lk_dn_scrub;   /* LK_DAYNIGHT v1: target sun (test aid / cycle; lk_lt_azd / eld = the direction the blocks show), time scrub of the test aid in hours */
static int lk_dn_o = -1;   /* Options > Graphics > Day / Night (id 54, ~/.landstalker_daynight, env LANDSTALKER_DAYNIGHT=0|1 wins), default On; needs Lighting On (outdoor sun rooms) */
int lk_dn_get(void) { if (lk_dn_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_DAYNIGHT"); char pth[512]; FILE *f; int v = 1; snprintf(pth, sizeof pth, "%%s/.landstalker_daynight", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%%d", &v) != 1) v = 1; fclose(f); } if (e) v = atoi(e); lk_dn_o = v ? 1 : 0; } return lk_dn_o; }
void lk_dn_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_dn_get(); lk_dn_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_daynight", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_dn_o); fclose(f); } }   /* the sun in degrees: azimuth in the world x / y plane (90 = from +y), elevation */
static void lk_lt_sunset(void) { float az = lk_lt_azd * 3.14159265f / 180.0f, el = lk_lt_eld * 3.14159265f / 180.0f;
  lk_lt_sd[0] = cosf(az) * cosf(el); lk_lt_sd[1] = sinf(az) * cosf(el); lk_lt_sd[2] = sinf(el); lk_lt_sK = (1.08f - lk_lt_sS) / (lk_lt_sd[2] > 0.2f ? lk_lt_sd[2] : 0.2f); }
void lk_lt_sun_nudge(float daz, float del) {   /* SUN TEST AID (user 2026-11-04, also the base of a later day / night cycle): pad L5 (or R5) held + right stick turns / raises the sun
     (src/input.c, patched below); applied in lk_lt_step at most every 4th frame (each change recomputes the light of the screen) */
  if (daz == 0.0f && del == 0.0f) return;
  if (lk_dn_get()) { lk_dn_scrub += daz * 0.01; return; }   /* LK_DAYNIGHT v1: with the day / night cycle on, left / right moves the time of day (a whole day in ~20 s) */
  if (lk_lt_azt < 0.0f) { lk_lt_azt = lk_lt_azd; lk_lt_elt = lk_lt_eld; }
  lk_lt_azt = fmodf(lk_lt_azt + daz + 360.0f, 360.0f); lk_lt_elt += del; if (lk_lt_elt < 5.0f) lk_lt_elt = 5.0f; if (lk_lt_elt > 89.0f) lk_lt_elt = 89.0f; lk_lt_sunmov = 1; }
static int lk_lt_sunp(void) {   /* v5 prototype: LANDSTALKER_SUN=1..3 (soft / medium / strong shadows), _SUN_AZ (degrees in the world x/y plane, 110 = from the lower left of the screen like the painted light: +y faces are the brightest, user 2026-11-03), _SUN_EL (elevation) */
  static int v = -1; int r;   /* v6: part of the Lighting option (user 2026-11-03: 'gehoert alles zu Lighting'), strength 2 unless LANDSTALKER_SUN says otherwise (0 = no sun) */
  if (v < 0) { const char *e = getenv("LANDSTALKER_SUN"), *a = getenv("LANDSTALKER_SUN_AZ"), *l = getenv("LANDSTALKER_SUN_EL"); float az = a ? (float)atof(a) : lk_lt_azd, el = l ? (float)atof(l) : lk_lt_eld;   /* az 90 (user 2026-11-03: Nigel's shadow along the isometric grid; the sun exactly from the lower left = world +y, was 110); el 55 (user 2026-11-03: 'Nigels Schatten wirkt draussen sehr lang', chose 55 of 40 / 55 / 65; was 40) */
    v = e ? atoi(e) : 1; if (v < 0 || v > 3) v = 1;   /* v7: default 1 = soft (user 2026-11-03: 'ich denke leicht') */
    lk_lt_azd = az; lk_lt_eld = el;
    lk_lt_sS = v == 1 ? 0.80f : v == 2 ? 0.70f : 0.60f; lk_lt_sunset(); }
  r = lk_lt_get() ? v : 0;
  return r;
}
static uint16_t lk_lt_cpk[74][74];   /* side penumbra: per cell the drawn OBJECT inside it (fine field, not bush / pine / lathe): bits 0..7 top / 4 (rounded up, 0 = none), bits 8..15 fine box x0 x1 y0 y1 (2 bits each); also sent to the GPU (lk_gl_world w row 2) */
static int lk_lt_sside = 1;   /* side penumbra of the sun march (LANDSTALKER_LT_SSIDE=0 = off, read at room setup) */
int lk_lt_sside_get(void) { return lk_lt_sside; }
uint16_t lk_lt_cpk_at(int x, int y) { return lk_lt_cpk[y][x]; }   /* for the GPU port (patch_gpulight.py sunvis) */
static float lk_lt_sidecl(float x, float y, float z, int cx, int cy, int self) {   /* 2026-11-07 SIDE PENUMBRA (GitHub issue #14, user 'ja'): the closest pass of lk_lt_sunvis only measured
     the clearance ABOVE the cell under the ray, so a ray passing BESIDE a taller cell (a pine block's base, a cliff, a house) gave a knife-sharp edge.  Horizontal distance from (x, y) to the
     nearest neighbour cell that reaches above z: game height (bush / pine cells: their base lk_lt_tb, the cone has its own soft edge; lathes skipped) and the drawn object inside it (lk_lt_cpk box).
     The point's own object is skipped.  Mirrored in patch_gpulight.py sidecl (lockstep).  9999 = nothing */
  float cl = 9999.0f; int a, b2;
  for (b2 = cy - 1; b2 <= cy + 1; b2++) for (a = cx - 1; a <= cx + 1; a++) { float hn, ex, ey; int ob, q2; unsigned pk;
    if ((a == cx && b2 == cy) || a < 0 || b2 < 0 || a >= 74 || b2 >= 74 || lk_lt_gh[b2][a] == -32768) continue;
    ob = lk_lt_obj[b2][a]; if (self && ob == self) continue;
    hn = (float)lk_lt_gh[b2][a]; if (ob > 0 && ob < 1024 && lk_lt_ocl[ob] == 1) hn = (float)lk_lt_sgnd[ob];
    q2 = lk_lt_fp[4 * b2 + 2][4 * a + 2];
    if (q2 && lk_lt_px[q2 - 1].type == 3) continue;
    if (q2 && lk_lt_px[q2 - 1].type == 5 && lk_lt_tk[b2][a]) hn = (float)lk_lt_tb[b2][a];
    if (hn + 0.5f > z) { ex = a > cx ? 16.0f * (float)a - x : a < cx ? x - 16.0f * (float)(a + 1) : 0.0f; ey = b2 > cy ? 16.0f * (float)b2 - y : b2 < cy ? y - 16.0f * (float)(b2 + 1) : 0.0f;
      if (ex < 0.0f) ex = 0.0f; if (ey < 0.0f) ey = 0.0f; ex = sqrtf(ex * ex + ey * ey); if (ex < cl) cl = ex; }
    pk = lk_lt_cpk[b2][a];
    if (pk && 4.0f * (float)(pk & 255) + 0.5f > z) { float bx0 = 16.0f * (float)a + 4.0f * (float)((pk >> 8) & 3), bx1 = 16.0f * (float)a + 4.0f * (float)(((pk >> 10) & 3) + 1),
        by0 = 16.0f * (float)b2 + 4.0f * (float)((pk >> 12) & 3), by1 = 16.0f * (float)b2 + 4.0f * (float)(((pk >> 14) & 3) + 1);
      ex = x < bx0 ? bx0 - x : x > bx1 ? x - bx1 : 0.0f; ey = y < by0 ? by0 - y : y > by1 ? y - by1 : 0.0f; ex = sqrtf(ex * ex + ey * ey); if (ex < cl) cl = ex; } }
  return cl; }
static float lk_lt_sunvis(float px, float py, float pz, int self) {   /* v7: share of the sun that reaches a point (0..1): march to the sun through the game's
     heights and the fine object field (lk_lt_fh), objects of the pixel's own object skipped (no self shadow: the painting has it); the closest pass gives a soft edge */
  const float *sd = lk_lt_sdp ? lk_lt_sdp : lk_lt_sd; int16_t (*hd)[74] = lk_lt_hdp ? lk_lt_hdp : lk_lt_hd;   /* LK_DAYNIGHT v1 */
  float hl = sqrtf(sd[0] * sd[0] + sd[1] * sd[1]), res = 1.0f, t;
  if (hl < 1e-3f) hl = 1e-3f;
  for (t = 2.0f; ; t += t < 32.0f ? 1.0f : 2.0f) {
    float x = px + sd[0] * t, y = py + sd[1] * t, z = pz + sd[2] * t, h, d, r; int cx, cy, o;
    if (z > (float)lk_lt_ztop + 1.0f || x < 0.0f || y < 0.0f || x >= 74.0f * 16.0f || y >= 74.0f * 16.0f) return res;
    { int sx = (int)(x * 0.25f), sy = (int)(y * 0.25f); cx = sx >> 2; cy = sy >> 2; o = lk_lt_fo[sy][sx];
      if (o && o == self) continue;
      h = lk_lt_gh[cy][cx] == -32768 ? -1e9f : (float)lk_lt_gh[cy][cx]; { int ob = lk_lt_obj[cy][cx]; if (ob > 0 && ob < 1024 && lk_lt_ocl[ob] == 1) h = (float)lk_lt_sgnd[ob]; }
      { int q = lk_lt_fp[sy][sx];
        if (q && lk_lt_px[q - 1].type == 5 && lk_lt_tk[cy][cx]) {   /* a recurring object: bush (sphere) or pine (cone) + stem over the base, light passes between the stems */
          float top = (float)lk_lt_tt[cy][cx], rr = (float)lk_lt_tr[cy][cx], zb = (float)lk_lt_tb[cy][cx], ddx = x - (16.0f * cx + 8.0f), ddy = y - (16.0f * cy + 8.0f), dh = sqrtf(ddx * ddx + ddy * ddy), cl, zc;
          if (lk_lt_tk[cy][cx] == 2) { zc = zb + 4.0f; cl = z >= top ? sqrtf(dh * dh + (z - top) * (z - top)) : z >= zc ? dh - rr * (top - z) / (top - zc) : 9999.0f; }
          else { zc = top - rr; cl = sqrtf(dh * dh + (z - zc) * (z - zc)) - rr; }
          if (z <= zc && dh - 1.5f < cl) cl = dh - 1.5f;   /* trunk */
          if (cl <= 0.0f) return 0.0f; r = LK_LT_PEN * cl / (t * hl); if (r < res) res = r;
          d = z - zb + 0.5f; if (d <= 0.0f) return 0.0f; r = LK_LT_PEN * d / (t * hl); if (r < res) res = r;
          if (lk_lt_sside) { float cl2 = lk_lt_sidecl(x, y, z, cx, cy, self); if (cl2 < 9999.0f) { r = LK_LT_PEN * cl2 / (t * hl); if (r < res) res = r; } }
          if (LK_LT_PEN * (z - (float)hd[cy][cx] + 0.5f) >= res * t * hl) return res;
          continue; }
        if (q && lk_lt_px[q - 1].type == 3) { const lk_lt_proxy *P = &lk_lt_px[q - 1]; int kk = (int)floorf(z - (float)P->z0); float ddx = x - P->x0, ddy = y - P->y0, dd = sqrtf(ddx * ddx + ddy * ddy), cl;
          if (kk >= 0 && kk < P->ridge - P->z0) { cl = dd - (float)lk_lt_prof[q - 1][kk]; if (cl <= 0.0f) return 0.0f; r = LK_LT_PEN * cl / (t * hl); if (r < res) res = r; }
          d = z - h + 0.5f; if (d <= 0.0f) return 0.0f; r = LK_LT_PEN * d / (t * hl); if (r < res) res = r;
          if (lk_lt_sside) { float cl2 = lk_lt_sidecl(x, y, z, cx, cy, self); if (cl2 < 9999.0f) { r = LK_LT_PEN * cl2 / (t * hl); if (r < res) res = r; } }
          if (LK_LT_PEN * (z - (float)hd[cy][cx] + 0.5f) >= res * t * hl) return res;
          continue; }
        if (o && (float)lk_lt_fh[sy][sx] > h) h = (float)lk_lt_fh[sy][sx]; } }
    d = z - h + 0.5f; if (d <= 0.0f) return 0.0f;
    r = LK_LT_PEN * d / (t * hl); if (r < res) res = r;
    if (lk_lt_sside) { float cl = lk_lt_sidecl(x, y, z, cx, cy, self); if (cl < 9999.0f) { r = LK_LT_PEN * cl / (t * hl); if (r < res) res = r; } }
    if (LK_LT_PEN * (z - (float)hd[cy][cx] + 0.5f) >= res * t * hl) return res;   /* v7 speed: nothing ahead reaches the ray any more (later passes are >= min(res, PEN * 0.64 / hl)) */
  }
}
static int16_t lk_lt_dm[74][74];   /* LK_DAYNIGHT v1: the 3 x 3 dilated highest field / card per cell (lk_lt_horizon), kept for lk_lt_hdcalc of another sun direction */
static void lk_lt_hdcalc(const float *sd, int16_t (*out)[74]) {   /* the early exit field of the sun march for direction sd: per cell the highest thing along the ray to the sun (~1 ms) */
  float hl = sqrtf(sd[0] * sd[0] + sd[1] * sd[1]), ux, uy; int x, y;
  if (hl < 1e-3f) hl = 1e-3f;
  ux = sd[0] / hl * 8.0f; uy = sd[1] / hl * 8.0f;
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { float px = 16.0f * x + 8.0f, py = 16.0f * y + 8.0f; int m = -32768;
    for (;;) { int a, b; if (px < 0.0f || py < 0.0f) break; a = (int)(px * 0.0625f); b = (int)(py * 0.0625f); if (a >= 74 || b >= 74) break;
      if (lk_lt_dm[b][a] > m) m = lk_lt_dm[b][a]; px += ux; py += uy; }
    out[y][x] = (int16_t)m; } }
static void lk_lt_horizon(void) {   /* v7 speed: lk_lt_hd for the early exit of the sun march, lk_lt_vt / vg / vm for the view ray (once per room, ~2 ms) */
  static int16_t cm[74][74], cc[74][74], dm[74][74], dc[74][74]; int x, y, j, sx, sy;
  float hl = sqrtf(lk_lt_sd[0] * lk_lt_sd[0] + lk_lt_sd[1] * lk_lt_sd[1]), ux, uy;
  { static int16_t vc[74][74]; static uint8 bad[74][74];
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { vc[y][x] = -32768; bad[y][x] = lk_lt_gh[y][x] == -32768; }
    for (sy = 0; sy < LK_LT_FN; sy++) for (sx = 0; sx < LK_LT_FN; sx++) { int t = lk_lt_fcell(sx, sy), o = lk_lt_fo[sy][sx]; lk_lt_vt[sy][sx] = (int16_t)t;
      { int ob = lk_lt_obj[sy >> 2][sx >> 2]; lk_lt_vg[sy][sx] = (int16_t)(ob > 0 && ob < 1024 && lk_lt_ocl[ob] == 1 ? lk_lt_sgnd[ob] : lk_lt_gh[sy >> 2][sx >> 2]); (void)o; }
      if (t > vc[sy >> 2][sx >> 2]) vc[sy >> 2][sx >> 2] = (int16_t)t; if (t == -32768 || lk_lt_fo[sy][sx]) bad[sy >> 2][sx >> 2] = 1; }
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int a, b, m = -32768;
      for (b = y - 1; b <= y + 1; b++) for (a = x - 1; a <= x + 1; a++) { if (a < 0 || b < 0 || a >= 74 || b >= 74 || bad[b][a]) { m = 32767; break; } if (vc[b][a] > m) m = vc[b][a]; }
      lk_lt_vm[y][x] = (int16_t)m; } }
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { cm[y][x] = lk_lt_gh[y][x]; cc[y][x] = -32768; }
  for (sy = 0; sy < LK_LT_FN; sy++) for (sx = 0; sx < LK_LT_FN; sx++) if (lk_lt_fo[sy][sx] && lk_lt_fh[sy][sx] > cm[sy >> 2][sx >> 2]) cm[sy >> 2][sx >> 2] = lk_lt_fh[sy][sx];
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int a, b, m = -32768, n = -32768;
    for (b = y - 1; b <= y + 1; b++) for (a = x - 1; a <= x + 1; a++) if (a >= 0 && b >= 0 && a < 74 && b < 74) { if (cm[b][a] > m) m = cm[b][a]; if (cc[b][a] > n) n = cc[b][a]; }
    dm[y][x] = (int16_t)m; dc[y][x] = (int16_t)n; }
  (void)hl; (void)ux; (void)uy; memcpy(lk_lt_dm, dm, sizeof lk_lt_dm); (void)dc;
  lk_lt_hdcalc(lk_lt_sd, lk_lt_hd);
}
static int lk_lt_isout(int room) {   /* v5: outdoor room = tileset 0 / 7 / 12 / 13 / 14 / 17 (towns, routes, docks, castle yard; tools: room table $0A0A00 byte 4), not the intro (139..143, 148) and not the dark docks (643) */
  int ts = OB(OL(0xA0A00) + 8u * (uint32_t)room + 4u) & 0x1F;
  if (room < 0 || (room >= 139 && room <= 143) || room == 148 || room == 643) return 0;
  return ts == 0 || ts == 7 || ts == 12 || ts == 13 || ts == 14 || ts == 17;
}
static int lk_lt_jobwait(int block); static void lk_lt_free(void) { int x, y; lk_lt_jobwait(1); lk_lt_gen++;   /* v8 MT: the worker must be idle */ for (y = 0; y < LK_LT_BH; y++) for (x = 0; x < LK_LT_BW; x++) if (lk_lt_b[y][x]) { free(lk_lt_b[y][x]); lk_lt_b[y][x] = 0; } }
static void lk_lt_sunfill(const lk_lt_blk *b, int U0, int V0, uint8 *out) {   /* LK_DAYNIGHT v1: the sun share of a block's pixels (was inline in lk_lt_blockcalc) for the direction of this thread (lk_lt_sdp) */
  const float *sd = lk_lt_sdp ? lk_lt_sdp : lk_lt_sd; int i;
  for (i = 0; i < 1024; i++) {   /* v5: sun = lit floor level, 0 in the shadow of the height map; faces keep their painted shading
                                                  (outdoors the height map holds only the low collision boxes of the houses, not walls / roofs: an angle term shaded them wrongly) */
    int f = b->face[i], cx, cy, ob; float px, py, nx = f == 2 ? 1.0f : 0.0f, ny = f == 3 ? 1.0f : 0.0f, nz = f == 1 ? 1.0f : 0.0f, ndl = sd[2];
    if (!f) continue;
    if (f != 1 && nx * sd[0] + ny * sd[1] <= 0.0f) {   /* a face turned away from the sun is painted darker already: no extra shadow (user: 'als wuerde ein Schatten auf die rechte vordere Wand geworfen') */
      float vis = 1.0f; int sx, sy;
      { float qx, qy; lk_lt_pos(U0 + (i & 31), V0 + (i >> 5), b->z[i], &qx, &qy); sx = (int)floorf((qx - nx * 2.0f) / 4.0f); sy = (int)floorf((qy - ny * 2.0f) / 4.0f);
        if (sx >= 0 && sy >= 0 && sx < LK_LT_FN && sy < LK_LT_FN && !lk_lt_fp[sy][sx] && lk_lt_gh[sy >> 2][sx >> 2] != -32768 && lk_lt_gh[sy >> 2][sx >> 2] <= 48 && b->z[i] <= lk_lt_gh[sy >> 2][sx >> 2])   /* low boxes only (rings, flower boxes): a tall wall without a proxy keeps its painting */   /* proxies 1c: the face of a box without a proxy (eave ring, flower box) is as lit as the top just behind its edge (the tulip box at a house stayed bright in the house's shadow) */
          vis = lk_lt_sunvis(qx - nx * 2.0f, qy - ny * 2.0f, (float)lk_lt_gh[sy >> 2][sx >> 2] + 0.5f, lk_lt_fo[sy][sx]); }
      out[i] = (uint8)(int)(ndl * vis * 255.0f); continue; }   /* v6: a face turned away from the sun is painted darker already: no extra shadow (user: 'als wuerde ein Schatten auf die rechte vordere Wand geworfen') */
    lk_lt_pos(U0 + (i & 31), V0 + (i >> 5), b->z[i], &px, &py);
    cx = (int)floorf((px - nx * 2.0f) / 4.0f); cy = (int)floorf((py - ny * 2.0f) / 4.0f); ob = (cx >= 0 && cy >= 0 && cx < LK_LT_FN && cy < LK_LT_FN) ? lk_lt_fo[cy][cx] : 0;   /* v7: owner of the sub column */
    if (ob > 0 && ob < 1024 && lk_lt_ocl[ob] == 1) { int pal, pr; if (!lk_o_fetch(lk_o_pa, U0 + (i & 31), V0 + (i >> 5), &pal, &pr, 0)) ob = 0; }   /* proxies 1b: ground drawn beside a trunk is ground, the tree shades it (user: 'Tannenschatten nicht bis zum Stamm') */
    if (!ob && b->robj[i]) { int pal, pr; if (lk_o_fetch(lk_o_pa, U0 + (i & 31), V0 + (i >> 5), &pal, &pr, 0)) ob = b->robj[i]; }
    { float vis = lk_lt_sunvis(px + nx * 3.0f, py + ny * 3.0f, (float)b->z[i] + nz * 3.0f, ob) * ndl;
      out[i] = (uint8)(vis >= 1.0f ? 255 : vis <= 0.0f ? 0 : (int)(vis * 255.0f)); }
  }
}
static lk_lt_blk *lk_lt_blockcalc(int bx, int by) {   /* v8 MT: computes one block (main thread or the light worker; touches no shared state: per thread lk_lt_rob / lk_lt_rayA / robj) */
  lk_lt_blk *b; int i, k, U0 = bx * 32, V0 = by * 32;
  b = (lk_lt_blk *)calloc(1, sizeof *b); if (!b) return 0;
  static __thread int16_t robj[1024];
  for (i = 0; i < 1024; i++) { int z = 0, pal, pr; lk_lt_rob = 0; lk_lt_rayA = lk_o_fetch(lk_o_pa, U0 + (i & 31), V0 + (i >> 5), &pal, &pr, 0) != 0; b->face[i] = (uint8)lk_lt_ray(U0 + (i & 31), V0 + (i >> 5), &z); b->z[i] = (int16_t)z; robj[i] = (int16_t)lk_lt_rob; }
  memcpy(b->robj, robj, sizeof b->robj);   /* LK_DAYNIGHT v1 */
  lk_lt_rayA = 1;
  { int pass2; for (pass2 = 0; pass2 < 2; pass2++) for (i = 0; i < 1024; i++) { float px, py; int an = i & ~0x21;   /* v8 room light; SPEED (measured 2026-11-05: 2..4 ms per block, room entry 20..45 ms frames): the even pixel of each 2 x 2 first, the others copy it when they lie on the same surface (soft light changes slowly) */
    if ((i == an) != (pass2 == 0)) continue;
    b->ao[i] = 255; if (!lk_lt_aor || !b->face[i]) continue;
    if (pass2 && b->face[an] == b->face[i] && abs(b->z[an] - b->z[i]) <= 2) { b->ao[i] = b->ao[an]; continue; }
    lk_lt_pos(U0 + (i & 31), V0 + (i >> 5), b->z[i], &px, &py); b->ao[i] = (uint8)(int)(lk_lt_aoval(px, py, b->z[i], b->face[i]) * 255.0f + 0.5f); } }
  { float bd[LK_LT_NL]; for (k = 0; k < lk_lt_nl; k++) {   /* the nearest lights of the block (picture distance of the light's projection) */
    float lu = lk_lt_l[k].x - lk_lt_l[k].y + 1184.0f, lv = (lk_lt_l[k].x + lk_lt_l[k].y) * 0.5f - lk_lt_l[k].z, du = lu - (float)(U0 + 16), dv = lv - (float)(V0 + 16), d2 = du * du + dv * dv; int m;
    if (fabsf(du) >= LK_LT_RAD * 1.6f + 24.0f || fabsf(dv) >= LK_LT_RAD * 1.6f + 24.0f) continue;
    if (b->nl < LK_LT_NL) m = b->nl++; else { int q; m = 0; for (q = 1; q < LK_LT_NL; q++) if (bd[q] > bd[m]) m = q; if (bd[m] <= d2) continue; }
    b->li[m] = (uint8)k; bd[m] = d2;
  } }
  if (lk_lt_sun) { lk_lt_sunfill(b, U0, V0, b->sun);   /* LK_DAYNIGHT v1: during a sun step a new block also gets the next direction's share */
    if (lk_dn_upd && lk_dn_hdok) { lk_lt_sdp = lk_lt_sdn; lk_lt_hdp = lk_lt_hdn; lk_lt_sunfill(b, U0, V0, b->sunn); lk_lt_sdp = 0; lk_lt_hdp = 0; b->sungen = lk_dn_gen; } }
  if (lk_lt_key) { int pass2; for (pass2 = 0; pass2 < 2; pass2++) for (i = 0; i < 1024; i++) {   /* v8 key light share; a face turned away keeps its painted shading (as the sun); 2 x 2 like the room light */
    int f = b->face[i], an = i & ~0x21; float px, py, nx = f == 2 ? 1.0f : 0.0f, ny = f == 3 ? 1.0f : 0.0f, nz = f == 1 ? 1.0f : 0.0f, vis;
    if ((i == an) != (pass2 == 0)) continue;
    b->sun[i] = 255; if (!f) continue;
    if (pass2 && b->face[an] == f && abs(b->z[an] - b->z[i]) <= 2) { b->sun[i] = b->sun[an]; continue; }
    if (f != 1 && nx * lk_lt_sd[0] + ny * lk_lt_sd[1] <= 0.0f) continue;
    lk_lt_pos(U0 + (i & 31), V0 + (i >> 5), b->z[i], &px, &py);
    vis = lk_lt_keyvis(px + nx * 3.0f, py + ny * 3.0f, (float)b->z[i] + nz * 3.0f);
    b->sun[i] = (uint8)(vis >= 1.0f ? 255 : vis <= 0.0f ? 0 : (int)(vis * 255.0f)); } }
  if (lk_lt_nsh) lk_lt_shblock(b, U0, V0); else { memset(b->beam, 0, sizeof b->beam); memset(b->pool, 0, sizeof b->pool); }   /* v8 light shafts */
  if (lk_lt_key && !lk_lt_nl) for (i = 0; i < 1024; i++) {   /* v8 SPEED: the static light of a key light room, finished once (lk_lt_pix applies it; figure shadows take the full path) */
    float u = (float)b->sun[i] * (1.0f / 255.0f), a = (float)b->ao[i] * (1.0f / 255.0f), f3[3]; int c;
    f3[0] = lk_lt_kA * 0.97f + lk_lt_kK * u * 1.04f; f3[1] = lk_lt_kA * 0.99f + lk_lt_kK * u; f3[2] = lk_lt_kA * 1.05f + lk_lt_kK * u * 0.92f;
    if (b->pool[i]) { float pp = (float)b->pool[i] * (1.0f / 255.0f) * 0.65f; f3[0] += pp * lk_lt_sh[0].cr; f3[1] += pp * lk_lt_sh[0].cg; f3[2] += pp * lk_lt_sh[0].cb; }
    for (c = 0; c < 3; c++) { float v = f3[c] * a; if (v > 2.4f) v = 2.4f; b->km[c][i] = (uint16_t)(int)(v * 256.0f + 0.5f); } }
  for (k = 0; k < b->nl; k++) for (i = 0; i < 1024; i++) {
    int f = b->face[i]; float px, py, t;
    if (!f) continue;
    lk_lt_pos(U0 + (i & 31), V0 + (i >> 5), b->z[i], &px, &py);
    t = lk_lt_term(px, py, (float)b->z[i], f == 2 ? 1.0f : 0.0f, f == 3 ? 1.0f : 0.0f, f == 1 ? 1.0f : 0.0f, &lk_lt_l[b->li[k]], 1);
    b->term[k][i] = (uint8)(t > 1.0f ? 255 : (int)(t * 255.0f));
  }
  return b;
}
static const lk_lt_blk *lk_lt_block(int bx, int by) {   /* the block, computed on first use (main thread) */
  lk_lt_blk *b;
  if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH) return 0;
  if ((b = lk_lt_b[by][bx])) return b;
  if (!lk_lt_pre && lk_lt_odn >= lk_lt_odcap) return 0;   /* v9: with worker threads the main thread computes none (lk_lt_odcap 0; missing blocks get the base light, lk_lt_pix) */
  if (!lk_lt_pre) lk_lt_odn++;
  struct timespec lk_bt0; clock_gettime(CLOCK_MONOTONIC, &lk_bt0); if (lk_lt_pre) lk_lt_pfn++; else lk_lt_bn++;
  if (!(b = lk_lt_blockcalc(bx, by))) return 0;
  lk_lt_b[by][bx] = b; if (lk_lt_pre) lk_lt_pms += lk_sm_ms_since(&lk_bt0); else lk_lt_bms += lk_sm_ms_since(&lk_bt0); return b;
}
/* v8 MT LIGHT WORKER (user 2026-11-05: 'generell ruckeliger ... Performance pruefen und optimieren'; measured: entering a room = ~40 frames over 12 ms from the block work):
   a second thread computes the blocks of the ring around the view between two frames.  Frame-synchronous: lk_lt_step first waits for the worker (it stops after
   LK_LT_WMS ms), publishes its blocks (lk_lt_b is only ever written by the main thread), then hands out the next list.  Room changes / lk_lt_free happen after that wait.
   Windows build: no thread, the list is worked off on the main thread with the old 2.5 ms budget. */
#define LK_LT_JMAX 64
#define LK_LT_WMS 14.0   /* v9: 14 (was 11; the workers run beside the frame, the main thread no longer waits) */
static int lk_lt_jn, lk_lt_jbx[LK_LT_JMAX], lk_lt_jby[LK_LT_JMAX], lk_lt_jgen; static lk_lt_blk *lk_lt_jres[LK_LT_JMAX], *lk_lt_jsun[LK_LT_JMAX];   /* jsun: LK_DAYNIGHT v1 sun-only job (the block gets sunn for lk_lt_sdn) */
static volatile int lk_lt_jnext, lk_lt_nact = 1;   /* v9 MT: next job of the list (atomic), active workers of this list */
static void lk_lt_jobrun(double ms) { struct timespec t0; int j, done = 0; clock_gettime(CLOCK_MONOTONIC, &t0);   /* several workers take jobs from one list (v9) */
  if (lk_dn_upd && !lk_dn_hdok) { lk_lt_hdcalc(lk_lt_sdn, lk_lt_hdn); lk_dn_hdok = 1; }   /* LK_DAYNIGHT v1: the early exit field of the next sun direction (a list with sun work runs on one worker only) */
  for (;;) { j = __atomic_fetch_add(&lk_lt_jnext, 1, __ATOMIC_RELAXED); if (j >= lk_lt_jn) break;
    lk_lt_jres[j] = 0; if (done && lk_sm_ms_since(&t0) > ms) continue;
    done++;
    if (lk_lt_jsun[j]) { lk_lt_blk *b = lk_lt_jsun[j]; lk_lt_sdp = lk_lt_sdn; lk_lt_hdp = lk_lt_hdn; lk_lt_sunfill(b, lk_lt_jbx[j] * 32, lk_lt_jby[j] * 32, b->sunn); lk_lt_sdp = 0; lk_lt_hdp = 0; b->sungen = lk_dn_gen; continue; }
    lk_lt_jres[j] = lk_lt_blockcalc(lk_lt_jbx[j], lk_lt_jby[j]); } }
#if !defined(_WIN32)
#include <pthread.h>
#define LK_LT_NTH 4
static pthread_t lk_lt_th[LK_LT_NTH]; static pthread_mutex_t lk_lt_mx = PTHREAD_MUTEX_INITIALIZER; static pthread_cond_t lk_lt_cvgo = PTHREAD_COND_INITIALIZER, lk_lt_cvdone = PTHREAD_COND_INITIALIZER;
static int lk_lt_thst, lk_lt_busy, lk_lt_nth, lk_lt_go;   /* thst: 0 not started, 1 running, -1 failed; busy: workers still on the current list; go: list generation */
static void *lk_lt_worker(void *arg) { int idx = (int)(intptr_t)arg, seen = 0;
  for (;;) { pthread_mutex_lock(&lk_lt_mx); while (lk_lt_go == seen) pthread_cond_wait(&lk_lt_cvgo, &lk_lt_mx); seen = lk_lt_go; pthread_mutex_unlock(&lk_lt_mx);
    if (idx < lk_lt_nact) lk_lt_jobrun(LK_LT_WMS);
    pthread_mutex_lock(&lk_lt_mx); if (--lk_lt_busy == 0) pthread_cond_signal(&lk_lt_cvdone); pthread_mutex_unlock(&lk_lt_mx); }
  return 0; }
static int lk_lt_mtopt(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_LT_MT"); v = e ? atoi(e) : 3; if (v < 0) v = 0; if (v > LK_LT_NTH) v = LK_LT_NTH; } return v; }   /* workers (v9 default 3; user 2026-11-06: stutter at room changes = 6 blocks of 4..6 ms on the main thread per frame); test aid LANDSTALKER_LT_MT=0 = none */
#endif
static int lk_lt_jobwait(int block) {   /* main: publish the workers' blocks; block = 0: only if they are done (returns 0 while they still work), 1: wait for them */
  int j;
#if !defined(_WIN32)
  if (lk_lt_thst == 1) { int busy; pthread_mutex_lock(&lk_lt_mx); if (block) while (lk_lt_busy) pthread_cond_wait(&lk_lt_cvdone, &lk_lt_mx); busy = lk_lt_busy; pthread_mutex_unlock(&lk_lt_mx); if (busy) return 0; }
#endif
  for (j = 0; j < lk_lt_jn; j++) { lk_lt_blk *b = lk_lt_jres[j]; lk_lt_jres[j] = 0; lk_lt_jsun[j] = 0; if (!b) continue;
    if (lk_lt_jgen == lk_lt_gen && !lk_lt_b[lk_lt_jby[j]][lk_lt_jbx[j]]) { lk_lt_b[lk_lt_jby[j]][lk_lt_jbx[j]] = b; lk_lt_pfn++; } else free(b); }
  lk_lt_jn = 0; return 1; }
static void lk_lt_jobstart(void) {   /* main: hand out the list (lk_lt_jn entries); no thread: work it off here */
  int j, sun = 0;
  if (!lk_lt_jn) return;
  lk_lt_jgen = lk_lt_gen; lk_lt_jnext = 0;
  for (j = 0; j < lk_lt_jn; j++) if (lk_lt_jsun[j]) sun = 1;
#if !defined(_WIN32)
  if (lk_lt_thst == 0 && lk_lt_mtopt()) { int k; lk_lt_nth = 0; for (k = 0; k < lk_lt_mtopt(); k++) if (pthread_create(&lk_lt_th[k], 0, lk_lt_worker, (void *)(intptr_t)k) == 0) { pthread_detach(lk_lt_th[k]); lk_lt_nth++; } lk_lt_thst = lk_lt_nth ? 1 : -1; if (lk_lt_thst == 1) lk_lt_odcap = 0; }
  if (lk_lt_thst == 1) { pthread_mutex_lock(&lk_lt_mx); lk_lt_nact = (sun || (lk_dn_upd && !lk_dn_hdok)) ? 1 : lk_lt_nth; lk_lt_busy = lk_lt_nth; lk_lt_go++; pthread_cond_broadcast(&lk_lt_cvgo); pthread_mutex_unlock(&lk_lt_mx); return; }
#endif
  lk_lt_jobrun(2.5); lk_lt_jobwait(1); }
static int lk_lt_isflame(uint32_t base, float *r, float *g, float *bl) {   /* AnimatedTilesetData entries that are light sources (tools/animsurvey.py, user 2026-11-02) */
  switch (base) {
    case 0x095BAA: case 0x096E8A: case 0x097CCA: case 0x098AAA: case 0x098CAA: case 0x09906A: *r = 1.0f; *g = 0.72f; *bl = 0.42f; return 1;   /* fireplace, torches, candles, candelabra */
    case 0x09608A: *r = 1.0f; *g = 0.84f; *bl = 0.55f; return 1;    /* lamp */
    case 0x099C0A: *r = 0.55f; *g = 1.0f; *bl = 0.45f; return 1;    /* cauldron */
    case 0x099E8A: *r = 0.95f; *g = 0.42f; *bl = 0.12f; return 2;   /* lava (entry 21, only rooms 403 / 404 are lava, the others water): a field, one weak light per 64 x 64 px of it (v3) */
    case 0x0968CA: *r = 1.0f; *g = 0.72f; *bl = 0.42f; return 1;    /* waterfall shrine: water AND wall torches in one group (only the torch tiles, lk_lt_tileok; user report room 177, 2026-11-03) */
  }
  return 0;
}
static int lk_lt_tileok(uint32_t base, int t) {   /* groups that mix flames with other tiles: only the flame tiles light */
  if (base == 0x0968CA) return t == 917 || t == 927 || t == 928 || t == 934 || t == 935;
  return 1;
}
static int lk_lt_extrude(void) {   /* v5: OWN LIGHT HEIGHT MAP outdoors (user 2026-11-03: 'sollten wir nicht eher fixen dass die Haeuser im Raumplan korrekt sind?'):
     the game's height map holds only the low collision boxes of houses / trees; their drawn walls, roofs and crowns are layer A (foreground) pixels
     above the box.  Small raised boxes (<= 128 cells of one height with a lower neighbour; large areas = terrain stay) are raised in OUR copy (lk_lt_top) cell by cell
     to the top of the layer A pixels in the picture column above the cell's top face.  The game's height map is not touched.  Returns the cells raised. */
  static uint8 comp[74][74]; static int16_t st[5476][2]; int x, y, n = 0;
  memset(comp, 0, sizeof comp);
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
    int h = lk_lt_top[y][x], sp = 0, cnt = 0, ok = 1, low = 0, i;
    if (comp[y][x] || h == -32768 || lk_lt_wat[y][x]) continue;   /* water (our fill) is no object: it merged the church with the painted border into one terrain object */
    comp[y][x] = 1; st[sp][0] = (int16_t)x; st[sp][1] = (int16_t)y; sp++;
    for (i = 0; i < sp; i++) { int cx = st[i][0], cy = st[i][1], d; cnt++;
      for (d = 0; d < 4; d++) { int nx = cx + (d == 0) - (d == 1), ny = cy + (d == 2) - (d == 3), t = lk_lt_cell(nx, ny);
        if (t == -32768 || (nx >= 0 && ny >= 0 && nx < 74 && ny < 74 && lk_lt_wat[ny][nx])) continue;
        if (t == h) { if (!comp[ny][nx] && sp < 5476) { comp[ny][nx] = 1; st[sp][0] = (int16_t)nx; st[sp][1] = (int16_t)ny; sp++; } }
        else if (t > h) ok = 0; else low = 1; } }
    if (lk_lt_dbg == 5 && cnt > 1) printf("extrude: room %%d comp at (%%d, %%d) h %%d cells %%d ok %%d low %%d\n", lk_o_room, x, y, h, cnt, ok, low);
    if (!low || cnt > 128) continue;
    for (i = 0; i < sp; i++) comp[st[i][1]][st[i][0]] = 2;   /* 2 = candidate (a house's eave ring and core are separate boxes of different height) */
  }
  { static uint8 ob[74][74]; int no = 0;   /* objects = 4-connected candidate cells (a whole house / tree) */
    memset(lk_lt_obj, 0, sizeof lk_lt_obj); memset(ob, 0, sizeof ob);
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int sp = 0, i;
      if (comp[y][x] != 2 || lk_lt_obj[y][x]) continue;
      no++; lk_lt_obj[y][x] = (int16_t)no; st[sp][0] = (int16_t)x; st[sp][1] = (int16_t)y; sp++;
      for (i = 0; i < sp; i++) { int d; for (d = 0; d < 4; d++) { int nx = st[i][0] + (d == 0) - (d == 1), ny = st[i][1] + (d == 2) - (d == 3);
        if (nx >= 0 && ny >= 0 && nx < 74 && ny < 74 && comp[ny][nx] == 2 && !lk_lt_obj[ny][nx] && sp < 5476) { lk_lt_obj[ny][nx] = (int16_t)no; st[sp][0] = (int16_t)nx; st[sp][1] = (int16_t)ny; sp++; } } }
    } }
  {   /* v7: object classes.  SMALL (<= 4 cells: tree, post, rock) = one card for the whole object; up to 5 heights (houses: eave ring + core, the church: hall,
         wing, porch; terraces of trees) = the fine field (drawn tops, mirrored per equal height part); more heights (cliffs) = a card per cell as in v6.
         PARTS (lk_lt_part / lk_lt_pb) = 4-connected cells of one object with the same game height: the mirror boxes of the fine field */
    static uint16_t hm[1024]; int o, w, hgt;
    for (o = 0; o < 1024; o++) { lk_lt_bb[o][0] = lk_lt_bb[o][1] = 9999; lk_lt_bb[o][2] = lk_lt_bb[o][3] = -1; lk_lt_bb[o][4] = 0; hm[o] = 0; lk_lt_ocl[o] = 0; lk_lt_omax[o] = -32768; }
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) if ((o = lk_lt_obj[y][x]) > 0 && o < 1024) { int16_t *B = lk_lt_bb[o];
      if (x < B[0]) B[0] = (int16_t)x; if (y < B[1]) B[1] = (int16_t)y; if (x > B[2]) B[2] = (int16_t)x; if (y > B[3]) B[3] = (int16_t)y; B[4]++; hm[o] |= (uint16_t)(1u << ((lk_lt_gh[y][x] >> 4) & 15)); if (lk_lt_gh[y][x] > lk_lt_omax[o]) lk_lt_omax[o] = lk_lt_gh[y][x]; }
    for (o = 1; o < 1024; o++) { int nh = 0, k; if (!lk_lt_bb[o][4]) continue;
      for (k = 0; k < 16; k++) nh += (hm[o] >> k) & 1;
      w = lk_lt_bb[o][2] - lk_lt_bb[o][0] + 1; hgt = lk_lt_bb[o][3] - lk_lt_bb[o][1] + 1;
      lk_lt_ocl[o] = lk_lt_bb[o][4] <= 4 ? 1 : nh <= 5 ? 2 : 3;   /* a mirror image is taken inside each equal height PART only (lk_lt_part), along an axis only when the part is not long that way */
      if (lk_lt_ocl[o] == 1) { int gx, gy, g = 9999; for (gy = lk_lt_bb[o][1] - 1; gy <= lk_lt_bb[o][3] + 1; gy++) for (gx = lk_lt_bb[o][0] - 1; gx <= lk_lt_bb[o][2] + 1; gx++) { int t = lk_lt_cell(gx, gy);
          if (t != -32768 && gx >= 0 && gy >= 0 && gx < 74 && gy < 74 && !lk_lt_obj[gy][gx] && t < g) g = t; }
        lk_lt_sgnd[o] = (int16_t)(g == 9999 ? lk_lt_gh[lk_lt_bb[o][1]][lk_lt_bb[o][0]] : g); }   /* user: 'der Schatten geht nicht ganz zum Stamm' (the box hid the ground beside the trunk) */
      if (lk_lt_dbg == 5) printf("extrude: room %%d object %%d cells %%d box %%d,%%d %%dx%%d heights %%d class %%d\n", lk_o_room, o, lk_lt_bb[o][4], lk_lt_bb[o][0], lk_lt_bb[o][1], w, hgt, nh, lk_lt_ocl[o]); }
    lk_lt_nc = 0;
    { static int16_t pst[5476][2]; int np = 0;   /* parts: 4-connected cells of one object with the same game height */
      memset(lk_lt_part, 0, sizeof lk_lt_part);
      for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int sp = 0, i, oo = lk_lt_obj[y][x], hh = lk_lt_gh[y][x];
        if (!oo || lk_lt_part[y][x] || np >= 2047) continue;
        np++; lk_lt_part[y][x] = (int16_t)np; pst[sp][0] = (int16_t)x; pst[sp][1] = (int16_t)y; sp++;
        lk_lt_pb[np][0] = lk_lt_pb[np][2] = (int16_t)x; lk_lt_pb[np][1] = lk_lt_pb[np][3] = (int16_t)y;
        for (i = 0; i < sp; i++) { int d; for (d = 0; d < 4; d++) { int nx = pst[i][0] + (d == 0) - (d == 1), ny = pst[i][1] + (d == 2) - (d == 3);
          if (nx < 0 || ny < 0 || nx >= 74 || ny >= 74 || lk_lt_part[ny][nx] || lk_lt_obj[ny][nx] != oo || lk_lt_gh[ny][nx] != hh || sp >= 5476) continue;
          lk_lt_part[ny][nx] = (int16_t)np; pst[sp][0] = (int16_t)nx; pst[sp][1] = (int16_t)ny; sp++;
          if (nx < lk_lt_pb[np][0]) lk_lt_pb[np][0] = (int16_t)nx; if (ny < lk_lt_pb[np][1]) lk_lt_pb[np][1] = (int16_t)ny; if (nx > lk_lt_pb[np][2]) lk_lt_pb[np][2] = (int16_t)nx; if (ny > lk_lt_pb[np][3]) lk_lt_pb[np][3] = (int16_t)ny; } } }
    { int pt, nobj = 0;   /* SMALL PIECES ON A BIGGER OBJECT (pines whose box touches a house core, room 632, user 2026-11-03: no tree shadow, lit grass between shadow and object): a part of <= 4 cells
           with at least as many lower as higher neighbours becomes an object of its own (class 1: one card, its own ground) */
      for (o = 1; o < 1024; o++) if (lk_lt_bb[o][4]) nobj = o;
      for (pt = 1; pt <= np && nobj < 1023; pt++) { int cnt = 0, nlow = 0, nhigh = 0, low = 0, oo = 0, hh = 0, g = 9999;
        for (y = lk_lt_pb[pt][1]; y <= lk_lt_pb[pt][3]; y++) for (x = lk_lt_pb[pt][0]; x <= lk_lt_pb[pt][2]; x++) if (lk_lt_part[y][x] == pt) { int d; cnt++; oo = lk_lt_obj[y][x]; hh = lk_lt_gh[y][x];
          for (d = 0; d < 4; d++) { int nx = x + (d == 0) - (d == 1), ny = y + (d == 2) - (d == 3), t;
            if (nx < 0 || ny < 0 || nx >= 74 || ny >= 74 || lk_lt_part[ny][nx] == pt) continue;
            t = lk_lt_gh[ny][nx]; if (t == -32768) continue;
            if (t > hh) nhigh++; else if (t < hh) { nlow++; if (lk_lt_obj[ny][nx] == oo || lk_lt_obj[ny][nx] == 0) low = 1; if (t < g) g = t; } } }
        if (!low || nlow < nhigh || cnt > 4 || !oo || oo >= 1024 || lk_lt_ocl[oo] != 2 || lk_lt_bb[oo][4] < cnt + 8) continue;   /* only off buildings: the steps of a cliff (class 3) are terrain */   /* mostly free standing (pines beside a house core: 2..3 of 4 sides low) */
        nobj++; lk_lt_bb[oo][4] = (int16_t)(lk_lt_bb[oo][4] - cnt);
        lk_lt_bb[nobj][0] = lk_lt_pb[pt][0]; lk_lt_bb[nobj][1] = lk_lt_pb[pt][1]; lk_lt_bb[nobj][2] = lk_lt_pb[pt][2]; lk_lt_bb[nobj][3] = lk_lt_pb[pt][3]; lk_lt_bb[nobj][4] = (int16_t)cnt;
        lk_lt_ocl[nobj] = 1; lk_lt_omax[nobj] = (int16_t)hh; lk_lt_sgnd[nobj] = (int16_t)g;
        for (y = lk_lt_pb[pt][1]; y <= lk_lt_pb[pt][3]; y++) for (x = lk_lt_pb[pt][0]; x <= lk_lt_pb[pt][2]; x++) if (lk_lt_part[y][x] == pt) lk_lt_obj[y][x] = (int16_t)nobj;
        if (lk_lt_dbg == 5) printf("extrude: room %%d part %%d (%%d cells, h %%d) of object %%d -> small object %%d on ground %%d\n", lk_o_room, pt, cnt, hh, oo, nobj, g); } }
    }
  }
  {   /* v7: FINE OBJECT HEIGHT FIELD (4 units; replaces the per cell cards of v6 for houses, user: stair steps on the shadows of the Mercator houses).  Per sub
         column of an object: the layer A run above its box top in the picture (the visual hull: walls may be layer B, so up to 64 px before the first drawn
         pixel, then gaps of 6 px).  One view sees the front: the hull is too high at the front (rays over the ridge), right at the back -> the minimum with the
         mirror images inside the sub column's PART box (houses are symmetric: hip roofs stay hip roofs; a part mirrors only along an axis on which it is not
         more than 2x longer than across, so a row of trees is not mirrored onto other trees; the church after the per object box: Mercator).  SMALL objects (<= 4 cells: trees, posts) are drawn
         wider than their box: one card for the whole object (its drawn silhouette, facing the sun, lk_lt_cardsun) instead of a field.
         lk_lt_fo = owner object of every sub column (also for small objects: no self shadow). */
    static int16_t hull[LK_LT_FN][LK_LT_FN]; int16_t (*bb)[5] = lk_lt_bb; int i, j, o;
    for (j = 0; j < LK_LT_FN; j++) for (i = 0; i < LK_LT_FN; i++) {
      int z0, z, top, gap = 0, seen = 0, U = 4 * (i - j) + 1184, V = 2 * (i + j) + 2;
      o = lk_lt_obj[j >> 2][i >> 2]; lk_lt_fo[j][i] = (int16_t)(o < 1024 ? o : 0);
      hull[j][i] = -32768; lk_lt_fh[j][i] = -32768;
      if (!o || o >= 1024 || lk_lt_ocl[o] != 2) continue;
      z0 = lk_lt_gh[j >> 2][i >> 2]; top = z0;
      { int pal, pr; if (z0 < lk_lt_omax[o] && V - z0 - 2 >= 0 && !lk_o_fetch(lk_o_pa, U, V - z0, &pal, &pr, 0) && !lk_o_fetch(lk_o_pa, U, V - z0 - 2, &pal, &pr, 0)) { hull[j][i] = (int16_t)z0; continue; } }
        /* a LOWER part (the eave ring / foundation around a house core) whose top is visible in the picture (not covered by layer A) carries nothing: the visual hull
           filled it up to the roof, the grass strip along the wall stayed lit between the wall and its shadow (user: 'helle Flaechen zwischen Schatten und Objekt') */
      for (z = z0; z < z0 + 200; z++) { int pal, pr; if (V - z < 0) break;
        if (lk_o_fetch(lk_o_pa, U, V - z, &pal, &pr, 0)) { top = z; seen = 1; gap = 0; } else if (++gap > (seen ? 6 : 64)) break; }
      hull[j][i] = (int16_t)top;
    }
    for (j = 0; j < LK_LT_FN; j++) for (i = 0; i < LK_LT_FN; i++) {
      int m = hull[j][i], k, mi, mj; if (m == -32768) continue;
      { int pt = lk_lt_part[j >> 2][i >> 2], pw = lk_lt_pb[pt][2] - lk_lt_pb[pt][0] + 1, ph = lk_lt_pb[pt][3] - lk_lt_pb[pt][1] + 1, ax = pw <= 2 * ph + 1, ay = ph <= 2 * pw + 1;
      mi = 4 * (lk_lt_pb[pt][0] + lk_lt_pb[pt][2]) + 3 - i; mj = 4 * (lk_lt_pb[pt][1] + lk_lt_pb[pt][3]) + 3 - j;
      for (k = 0; k < 3; k++) { int a = k == 1 ? i : mi, c = k == 0 ? j : mj;
        if ((k != 1 && !ax) || (k != 0 && !ay)) continue;
        if (a < 0 || c < 0 || a >= LK_LT_FN || c >= LK_LT_FN || lk_lt_part[c >> 2][a >> 2] != pt || hull[c][a] == -32768) continue;
        if (hull[c][a] < m) m = hull[c][a]; } }
      lk_lt_fh[j][i] = (int16_t)m; if (m > lk_lt_fhmax) lk_lt_fhmax = m;
    }
    for (o = 1; o < 1024 && lk_lt_nc < 1024; o++) if (lk_lt_ocl[o] == 1) {   /* the card of a small object: through its centre, its drawn picture up to the top */
      int h = lk_lt_sgnd[o], wx = 8 * (bb[o][0] + bb[o][2]) + 8, wy = 8 * (bb[o][1] + bb[o][3]) + 8, U = wx - wy + 1184, V0 = (wx + wy) / 2 - h, du, v, best = 0;
      int hw = 16 + 8 * ((bb[o][2] - bb[o][0] > bb[o][3] - bb[o][1] ? bb[o][2] - bb[o][0] : bb[o][3] - bb[o][1]));
      { int d, foot = 0; for (d = 1; d <= 24; d++) { int pal, pr; if (lk_o_fetch(lk_o_pa, U, V0 + d, &pal, &pr, 0) || lk_o_fetch(lk_o_pa, U - 2, V0 + d, &pal, &pr, 0) || lk_o_fetch(lk_o_pa, U + 2, V0 + d, &pal, &pr, 0)) foot = d; }
        wx += foot; wy += foot; V0 += foot; }   /* the drawn foot (trunk) is often below the cell centre (pines: at the front corner): the card stands there, so the shadow starts at the trunk (user) */
      for (du = -12; du <= 12; du += 4) { int last = V0 + 1, seen = 0;
        for (v = V0; v >= V0 - 176 && v >= 0; v--) { int pal, pr; if (lk_o_fetch(lk_o_pa, U + du, v, &pal, &pr, 0)) { last = v; seen = 1; } else if (v < last - (seen ? 6 : 64)) break; }
        if (seen && V0 - last > best) best = V0 - last; }
      if (best > 8) { lk_lt_card *C = &lk_lt_c[lk_lt_nc++]; C->x = (float)wx; C->y = (float)wy; C->h = (int16_t)h; C->hh = (int16_t)best; C->U = (int16_t)U; C->V0 = (int16_t)V0; C->w = (int16_t)hw; C->obj = (int16_t)o;
        if (h + best > lk_lt_fhmax) lk_lt_fhmax = h + best; }
    }
  }
  lk_lt_npx = 0; memset(lk_lt_fp, 0, sizeof lk_lt_fp);
  {   /* LIGHT PROXIES step 1 (user 2026-11-03: 'dann haben wir es an Objekten und muessen nicht mehr raten'): a clean shape per building part / small object,
       proposed from the measured field / card, then the field is redrawn from the shapes only (no holes, towers or gaps of the guessed hull) */
    static int16_t pb[2048][4]; static int32_t pcnt[2048]; int pt, j, i, c, k;
    for (pt = 0; pt < 2048; pt++) { pb[pt][0] = pb[pt][1] = 9999; pb[pt][2] = pb[pt][3] = -1; pcnt[pt] = 0; }
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int q = lk_lt_part[y][x], nb = 0;   /* a cell sticking out of its part alone (<= 1 neighbour of the part: steps, bumps of the collision) carries no house (dark stripe in front of the church) */
      if (q > 0) nb = (x > 0 && lk_lt_part[y][x - 1] == q) + (x < 73 && lk_lt_part[y][x + 1] == q) + (y > 0 && lk_lt_part[y - 1][x] == q) + (y < 73 && lk_lt_part[y + 1][x] == q);
      lk_lt_pkeep[y][x] = (uint8)(q > 0 && nb >= 2); }
    for (pt = 0; pt < 2048; pt++) { pb[pt][0] = pb[pt][1] = 9999; pb[pt][2] = pb[pt][3] = -1; }
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int q = lk_lt_part[y][x]; if (q <= 0 || q >= 2048 || !lk_lt_pkeep[y][x]) continue;   /* the hip's box: the kept cells */
      if (x < pb[q][0]) pb[q][0] = (int16_t)x; if (y < pb[q][1]) pb[q][1] = (int16_t)y; if (x > pb[q][2]) pb[q][2] = (int16_t)x; if (y > pb[q][3]) pb[q][3] = (int16_t)y; }
    for (pt = 0; pt < 2048; pt++) { lk_lt_pb2[pt][0] = pb[pt][0]; lk_lt_pb2[pt][1] = pb[pt][1]; lk_lt_pb2[pt][2] = pb[pt][2]; lk_lt_pb2[pt][3] = pb[pt][3]; pb[pt][0] = pb[pt][1] = 9999; pb[pt][2] = pb[pt][3] = -1; }
    for (j = 0; j < LK_LT_FN; j++) for (i = 0; i < LK_LT_FN; i++) {   /* per part: the sub columns that stand clearly above the part's box top */
      int o = lk_lt_fo[j][i], q = lk_lt_part[j >> 2][i >> 2]; if (!o || o >= 1024 || lk_lt_ocl[o] != 2 || q <= 0 || q >= 2048) continue;
      if (lk_lt_fh[j][i] < lk_lt_gh[j >> 2][i >> 2] + 8) continue;
      if (i < pb[q][0]) pb[q][0] = (int16_t)i; if (j < pb[q][1]) pb[q][1] = (int16_t)j; if (i > pb[q][2]) pb[q][2] = (int16_t)i; if (j > pb[q][3]) pb[q][3] = (int16_t)j; pcnt[q]++; }
    for (pt = 1; pt < 2048 && lk_lt_npx < 255; pt++) { int o = 0, mx = -32768, z0 = 0, nb = 0; static int16_t ev[1024]; lk_lt_proxy *P;
      if (pcnt[pt] < 16) continue;
      for (j = pb[pt][1]; j <= pb[pt][3]; j++) for (i = pb[pt][0]; i <= pb[pt][2]; i++) if (lk_lt_part[j >> 2][i >> 2] == pt && lk_lt_fh[j][i] >= lk_lt_gh[j >> 2][i >> 2] + 8) {
        int f = lk_lt_fh[j][i]; o = lk_lt_fo[j][i]; z0 = lk_lt_gh[j >> 2][i >> 2]; if (f > mx) mx = f;
        if ((i == pb[pt][0] || i == pb[pt][2] || j == pb[pt][1] || j == pb[pt][3]) && nb < 1024) ev[nb++] = (int16_t)f; }
      if (!o || nb == 0 || pb[pt][2] - pb[pt][0] < 5 || pb[pt][3] - pb[pt][1] < 5) continue;   /* strips < 24 units (eave rings, borders behind a tall core) are no building of their own */
      for (k = 1; k < nb; k++) { int16_t t = ev[k]; c = k - 1; while (c >= 0 && ev[c] > t) { ev[c + 1] = ev[c]; c--; } ev[c + 1] = t; }   /* eave = median height along the border */
      P = &lk_lt_px[lk_lt_npx++]; P->type = 1; P->obj = (int16_t)o; P->part = (int16_t)pt; if (lk_lt_pb2[pt][2] < 0) { lk_lt_npx--; continue; }
      P->x0 = (int16_t)(16 * lk_lt_pb2[pt][0]); P->y0 = (int16_t)(16 * lk_lt_pb2[pt][1]); P->x1 = (int16_t)(16 * lk_lt_pb2[pt][2] + 16); P->y1 = (int16_t)(16 * lk_lt_pb2[pt][3] + 16);   /* the part's whole footprint: the drawn walls stand on its edge */
      P->z0 = (int16_t)z0; P->ridge = (int16_t)mx; P->eave = ev[nb / 2]; if (P->eave > P->ridge) P->eave = P->ridge;
      if (lk_lt_dbg == 5) printf("proxy: room %%d #%%d hip x %%d..%%d y %%d..%%d z0 %%d eave %%d ridge %%d (object %%d part %%d)\n", lk_o_room, lk_lt_npx - 1, P->x0, P->x1, P->y0, P->y1, P->z0, P->eave, P->ridge, o, pt); }
    for (c = 0, j = 0; j < lk_lt_nc; j++) { lk_lt_card *C = &lk_lt_c[j];   /* small objects: a LATHE solid from the sprite (user: 'der Schatten soll wie das Sprite aussehen'), drawn foot = axis */
      if (C->obj > 0 && C->obj < 1024 && lk_lt_ocl[C->obj] == 1) {
        int H = C->hh, kk, bad = 0, any = 0; lk_lt_proxy *P; uint8 *R;
        { int cap = 48 + 24 * (lk_lt_bb[C->obj][2] - lk_lt_bb[C->obj][0] > lk_lt_bb[C->obj][3] - lk_lt_bb[C->obj][1] ? lk_lt_bb[C->obj][2] - lk_lt_bb[C->obj][0] + 1 : lk_lt_bb[C->obj][3] - lk_lt_bb[C->obj][1] + 1); if (H > cap) H = cap; if (H > 95) H = 95; }   /* a pine at a house: the drawn run goes on into the wall */
        if (H < 32 || lk_lt_npx >= 255 || (lk_lt_bb[C->obj][2] - lk_lt_bb[C->obj][0] != lk_lt_bb[C->obj][3] - lk_lt_bb[C->obj][1] && H < 48)) {   /* low, or a low row (a tulip row of 1 x 3 cells became a round blob) */ if (lk_lt_dbg == 5) printf("proxy: room %%d object %%d flat (drawn %%d high)\n", lk_o_room, C->obj, C->hh); continue; }   /* tulips, low bushes: no shape, they take the shadows */
        P = &lk_lt_px[lk_lt_npx]; R = lk_lt_prof[lk_lt_npx]; lk_lt_npx++;
        P->type = 3; P->part = 0; P->obj = C->obj; P->x0 = (int16_t)C->x; P->y0 = (int16_t)C->y; P->z0 = C->h; P->eave = C->h; P->ridge = (int16_t)(C->h + H); P->y1 = 0;
        for (kk = 0; kk < 96; kk++) { int l = 0, r = 0, pal, pr, g;
          R[kk] = 0; if (kk >= H) continue;
          if (!lk_o_fetch(lk_o_pa, C->U, C->V0 - kk, &pal, &pr, 0) && !lk_o_fetch(lk_o_pa, C->U - 1, C->V0 - kk, &pal, &pr, 0) && !lk_o_fetch(lk_o_pa, C->U + 1, C->V0 - kk, &pal, &pr, 0)) continue;
          for (g = 0, l = 1; l <= 28; l++) { if (lk_o_fetch(lk_o_pa, C->U - l, C->V0 - kk, &pal, &pr, 0)) g = 0; else if (++g > 1) break; } l -= g;
          for (g = 0, r = 1; r <= 28; r++) { if (lk_o_fetch(lk_o_pa, C->U + r, C->V0 - kk, &pal, &pr, 0)) g = 0; else if (++g > 1) break; } r -= g;
          if (l >= 27 || r >= 27) { bad++; R[kk] = 255; continue; }   /* the run went on into a wall behind */
          R[kk] = (uint8)((float)(l + r) * 0.5f / 1.4142f + 0.5f); any++; }
        P->y1 = (int16_t)bad; P->x1 = 0; for (kk = 0; kk < H; kk++) if (R[kk] != 255 && R[kk] > P->x1) P->x1 = R[kk];
        if (!any) { P->type = 2; P->x1 = (int16_t)((float)C->w * 0.7072f); }
        if (lk_lt_dbg == 5) printf("proxy: room %%d #%%d lathe at %%d,%%d z %%d..%%d max r %%d, %%d rows hidden by a wall (object %%d)\n", lk_o_room, lk_lt_npx - 1, P->x0, P->y0, P->z0, P->ridge, P->x1, bad, P->obj);
        continue; }
      }
    for (k = 0; k < lk_lt_npx; k++) { lk_lt_proxy *P = &lk_lt_px[k]; int best = -1, kk, bd = 9999, q;   /* rows hidden by a wall: the profile of the most alike free standing tree of the room, else the row below */
      if (P->type != 3 || !P->y1) continue;
      for (q = 0; q < lk_lt_npx; q++) if (q != k && lk_lt_px[q].type == 3 && !lk_lt_px[q].y1) { int dd = abs((lk_lt_px[q].ridge - lk_lt_px[q].z0) - (P->ridge - P->z0)); if (dd < bd) { bd = dd; best = q; } }
      if (best >= 0) { memcpy(lk_lt_prof[k], lk_lt_prof[best], 96); P->ridge = (int16_t)(P->z0 + (lk_lt_px[best].ridge - lk_lt_px[best].z0)); }   /* the same tree drawn free elsewhere in the room: take its whole shape (a pine at a house wall) */
      else for (kk = 0; kk < 96; kk++) if (lk_lt_prof[k][kk] == 255) lk_lt_prof[k][kk] = kk ? lk_lt_prof[k][kk - 1] : 0;
      P->x1 = 0; for (kk = 0; kk < 96; kk++) if (lk_lt_prof[k][kk] > P->x1) P->x1 = lk_lt_prof[k][kk]; }
    lk_lt_nc = 0; (void)c;   /* the cards were only the measurement of the small objects */
    memset(lk_lt_tk, 0, sizeof lk_lt_tk); memset(lk_lt_to, 0, sizeof lk_lt_to);
    { static uint8 lut[1024], cls[74][74]; static int8_t bh[74][74]; static uint8 bx2[74][74], by2[74][74]; int ts = OB(OL(0xA0A00) + 8u * (uint32_t)lk_o_room + 4u) & 0x1F, q, n = 0, nb = 0, np = 0, nf = 0;
      /* OBJECT CATALOGUE (data/object_blocks.json, user 2026-11-04: 'generell etwas fuer wiederkehrende Objekte'): the layer A block that draws the TOP of cell (x, y) at height h
         is block (x - h, y - h) (of all cells on that view diagonal the highest one is seen); a block of the catalogue makes the cell a recurring object (bush, pine) */
      memset(lut, 0, sizeof lut); memset(cls, 0, sizeof cls); memset(bh, -1, sizeof bh);
      for (q = 0; lk_lt_cat[q][0] >= 0; q++) if (lk_lt_cat[q][0] == ts) lut[lk_lt_cat[q][1] & 1023] = (uint8)lk_lt_cat[q][2];
      for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int w = UW(0xFFD192 + 148 * y + 2 * x), h, bx, by; lk_lt_walk[y][x] = (uint8)(w != 0x4000 && !((w >> 8) & 0x60)); if (w == 0x4000 || !w) continue;
        h = (w >> 8) & 15; bx = x - h; by = y - h; if (bx < 0 || by < 0) continue;
        if (h > bh[by][bx]) { bh[by][bx] = (int8_t)h; bx2[by][bx] = (uint8)x; by2[by][bx] = (uint8)y; } }
      for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) if (bh[y][x] >= 0) { int c = lut[UW(0xFF7C02 + 148 * y + 2 * x) & 1023], cx = bx2[y][x], cy = by2[y][x], ob = lk_lt_obj[cy][cx];
        if (c && !(ob > 0 && ob < 1024 && lk_lt_ocl[ob] == 1) && lk_lt_gh[cy][cx] != -32768) cls[cy][cx] = (uint8)c; }   /* a SMALL free standing object keeps its sprite lathe */
      { static uint8 inq[74][74]; memset(inq, 0, sizeof inq);   /* inq: cell already in a component (each cell is looked at once) */
      for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) if (cls[y][x] && !inq[y][x]) {   /* components of equal class: base = most common game height on their ring (ties: the lower) */
        static uint8 st[74 * 74][2]; int sp = 0, m, vals[64], cnt[64], nv = 0, i, best = 0, base = 0, c = cls[y][x], ncell = 0;
        st[sp][0] = (uint8)x; st[sp][1] = (uint8)y; sp++; inq[y][x] = 1;
        for (m = 0; m < sp; m++) { int cx = st[m][0], cy = st[m][1], d; static const int dd[4][2] = { {1, 0}, {-1, 0}, {0, 1}, {0, -1} }; ncell++;
          for (d = 0; d < 4; d++) { int nx = cx + dd[d][0], ny = cy + dd[d][1], g; if (nx < 0 || ny < 0 || nx >= 74 || ny >= 74 || inq[ny][nx]) continue;
            if (cls[ny][nx] == c) { inq[ny][nx] = 1; st[sp][0] = (uint8)nx; st[sp][1] = (uint8)ny; sp++; continue; }
            if (cls[ny][nx] || (g = lk_lt_gh[ny][nx]) == -32768) continue;
            for (i = 0; i < nv && vals[i] != g; i++) ; if (i == nv) { if (nv == 64) continue; vals[nv] = g; cnt[nv++] = 0; } cnt[i]++; } }
        for (i = 0; i < nv; i++) if (cnt[i] > best || (cnt[i] == best && vals[i] < base)) { best = cnt[i]; base = vals[i]; }
        if (!nv) base = lk_lt_gh[y][x] - 16;
        for (m = 0; m < sp; m++) { int cx = st[m][0], cy = st[m][1], g = lk_lt_gh[cy][cx], kind = lk_lt_catc[c][0], top = kind == 1 ? (g > base + 16 ? g : base + 16) : (g > base + lk_lt_catc[c][2] ? g : base + lk_lt_catc[c][2]);
          { int k2, dup = 0; for (k2 = 0; k2 < lk_lt_npx && !dup; k2++) { const lk_lt_proxy *L2 = &lk_lt_px[k2]; float ddx = 16.0f * cx + 8.0f - (float)L2->x0, ddy = 16.0f * cy + 8.0f - (float)L2->y0; if (L2->type == 3 && ddx * ddx + ddy * ddy < 48.0f * 48.0f) dup = 1; }
            if (dup && kind != 3) { if (lk_lt_dbg == 5) printf("catalogue: room %%d cell %%d,%%d skipped: a lathe tree stands there\n", lk_o_room, cx, cy); continue; } }   /* v8 (user 2026-11-06: 'der Baum wirft 3 Schatten'): the crown blocks of a free standing tree that already has its sprite lathe map to the cells behind it = 3 more pine cones */
          if (kind == 1 && g < base + 8) continue;   /* kind 3 FLAT (flower beds): no shape, and no automatic shape over it either */   /* a bush only on a RAISED cell: the side faces / back edge of a bush block also draw the top of lower cells in front / behind */
          lk_lt_tk[cy][cx] = (uint8)kind; lk_lt_tr[cy][cx] = (uint8)lk_lt_catc[c][1]; lk_lt_tb[cy][cx] = (int16_t)base; lk_lt_tt[cy][cx] = (int16_t)top; lk_lt_to[cy][cx] = 1031; if (kind == 1) nb++; else if (kind == 2) np++; else nf++; if (lk_lt_dbg == 5) printf("catalogue: room %%d cell %%d,%%d kind %%d base %%d top %%d r %%d\n", lk_o_room, cx, cy, kind, base, top, lk_lt_catc[c][1]); }
        n++; } }
      if (nb + np + nf && lk_lt_npx < 255) { int m, kept = 0; lk_lt_proxy *P;
        for (m = 0; m < lk_lt_npx; m++) { const lk_lt_proxy *Q = &lk_lt_px[m]; int tot = 0, hit = 0, cx, cy;   /* automatic hips mostly over catalogue cells go */
          if (Q->type == 1 && Q->part) for (cy = Q->y0 >> 4; cy < (Q->y1 + 15) >> 4 && cy < 74; cy++) for (cx = Q->x0 >> 4; cx < (Q->x1 + 15) >> 4 && cx < 74; cx++) if (cx >= 0 && cy >= 0 && lk_lt_part[cy][cx] == Q->part) { tot++; if (lk_lt_to[cy][cx]) hit++;
            if (lk_lt_tk[cy][cx] == 2 && Q->ridge > lk_lt_tt[cy][cx]) lk_lt_tt[cy][cx] = Q->ridge; }   /* pines: the catalogue gives the shape, the automatic proposal measured the drawn height (big pines of room 637: tips ~109) */
          if (tot && 2 * hit >= tot) { if (lk_lt_dbg == 5) printf("catalogue: room %%d drops hip #%%d (%%d of %%d cells are recurring objects)\n", lk_o_room, m, hit, tot); continue; }
          if (kept != m) { lk_lt_px[kept] = lk_lt_px[m]; memcpy(lk_lt_prof[kept], lk_lt_prof[m], 96); } kept++; }
        lk_lt_npx = kept;
        P = &lk_lt_px[lk_lt_npx++]; P->type = 5; P->part = 0; P->obj = 1031; lk_lt_ocl[1031] = 2; P->x0 = P->y0 = 0; P->x1 = P->y1 = 73; P->z0 = P->eave = P->ridge = 0; }
      if (lk_lt_dbg == 5) printf("catalogue: room %%d tileset %%d: %%d bush cells, %%d pine cells, %%d flat cells, %%d groups\n", lk_o_room, ts, nb, np, nf, n); }
    { int q; memset(lk_lt_flat, 0, sizeof lk_lt_flat);   /* CORRECTIONS (data/light_proxies.json, LIGHT_PROXY_PLAN step 2) */
      for (q = 0; lk_lt_corr[q].room >= 0; q++) { const int16_t *a = lk_lt_corr[q].a; int op = lk_lt_corr[q].op;
        if (lk_lt_corr[q].room != lk_o_room) continue;
        if (op == 1) for (y = a[1]; y <= a[3]; y++) for (x = a[0]; x <= a[2]; x++) if (x >= 0 && y >= 0 && x < 74 && y < 74) lk_lt_flat[y][x] = 1;
        if (op == 1 || op == 3 || op == 5 || op == 6 || op == 7) { int m, kept = 0; for (m = 0; m < lk_lt_npx; m++) { const lk_lt_proxy *P = &lk_lt_px[m]; int cx = (P->type == 1 ? (P->x0 + P->x1) / 2 : P->x0) >> 4, cy = (P->type == 1 ? (P->y0 + P->y1) / 2 : P->y0) >> 4;
            if (P->type != 5 && cx >= a[0] && cx <= a[2] && cy >= a[1] && cy <= a[3]) { if (lk_lt_dbg == 5) printf("correction: room %%d drops proxy #%%d\n", lk_o_room, m); continue; }
            if (kept != m) { lk_lt_px[kept] = lk_lt_px[m]; memcpy(lk_lt_prof[kept], lk_lt_prof[m], 96); } kept++; }
          lk_lt_npx = kept; }
        if (op == 4 && lk_lt_npx < 255) { lk_lt_proxy *P = &lk_lt_px[lk_lt_npx++]; int id = 1000 + (q %% 24);
          P->type = 1; P->part = 0; P->obj = (int16_t)id; lk_lt_ocl[id] = 2; P->x0 = (int16_t)(16 * a[0]); P->y0 = (int16_t)(16 * a[1]); P->x1 = (int16_t)(16 * a[2] + 16); P->y1 = (int16_t)(16 * a[3] + 16); P->z0 = a[4]; P->eave = a[5]; P->ridge = a[6];
          if (lk_lt_dbg == 5) printf("correction: room %%d adds hip #%%d\n", lk_o_room, lk_lt_npx - 1); }
        if (op == 5 && lk_lt_npx < 255) { lk_lt_proxy *P = &lk_lt_px[lk_lt_npx++]; int id = 1000 + (q %% 24);   /* a Blender shape (data/proxies/*.obj, stamped at build time) */
          P->type = 4; P->part = a[4]; P->obj = (int16_t)id; lk_lt_ocl[id] = 2; P->x0 = (int16_t)(16 * a[0]); P->y0 = (int16_t)(16 * a[1]); P->x1 = (int16_t)(16 * a[2] + 16); P->y1 = (int16_t)(16 * a[3] + 16); P->z0 = 0; P->eave = P->ridge = 0;
          if (lk_lt_dbg == 5) printf("correction: room %%d adds mesh %%d as #%%d\n", lk_o_room, a[4], lk_lt_npx - 1); }
        if ((op == 6 || op == 7) && lk_lt_npx < 255) { lk_lt_proxy *P = &lk_lt_px[lk_lt_npx++]; int id = 1000 + (q %% 24), base = a[6];   /* FORESTS (user 2026-11-04: 'der Schatten soll nach dem Baum oder Busch aussehen und nicht wie ein Block'):
            one round bush (bushes; the one step forest blocks are BUSH sprites, user) or cone (pines) per raised cell, on a regular grid like the painting; the game's raised block itself casts nothing */
          if (base == -999) { int vals[64], cnt[64], nv = 0, i, best = 0; base = 0;   /* automatic base: the most common game height on the ring of cells around the rectangle */
            for (y = a[1] - 1; y <= a[3] + 1; y++) for (x = a[0] - 1; x <= a[2] + 1; x++) { int g;
              if (x >= a[0] && x <= a[2] && y >= a[1] && y <= a[3]) continue;
              if (x < 0 || y < 0 || x >= 74 || y >= 74 || (g = lk_lt_gh[y][x]) == -32768) continue;
              for (i = 0; i < nv && vals[i] != g; i++) ; if (i == nv) { if (nv == 64) continue; vals[nv] = g; cnt[nv++] = 0; } cnt[i]++; }
            for (x = 0; x < nv; x++) if (cnt[x] > best || (cnt[x] == best && vals[x] < base)) { best = cnt[x]; base = vals[x]; } }   /* a tie: the lower one */
          P->type = 5; P->part = 0; P->obj = (int16_t)id; lk_lt_ocl[id] = 2; P->x0 = a[0]; P->y0 = a[1]; P->x1 = a[2]; P->y1 = a[3]; P->z0 = (int16_t)base; P->eave = a[4];
          P->ridge = (int16_t)(a[5] > 0 ? a[5] : op == 6 ? 6 : 7); if (P->ridge > 8) P->ridge = 8;   /* radius <= half a cell: a crown never reaches into the next cell */
          for (y = a[1]; y <= a[3]; y++) for (x = a[0]; x <= a[2]; x++) { int g;   /* every RAISED cell of the rectangle (game height >= base + 8) */
            if (x < 0 || y < 0 || x >= 74 || y >= 74 || (g = lk_lt_gh[y][x]) == -32768 || g < base + 8) continue;
            lk_lt_tk[y][x] = (uint8)(op - 5); lk_lt_tr[y][x] = (uint8)P->ridge; lk_lt_tb[y][x] = (int16_t)base; lk_lt_tt[y][x] = (int16_t)(a[4] > 0 ? base + a[4] : g); lk_lt_to[y][x] = (int16_t)id; }
          if (lk_lt_dbg == 5) printf("correction: room %%d adds %%s #%%d cells %%d..%%d x %%d..%%d base %%d top %%d radius %%d\n", lk_o_room, op == 6 ? "bushes" : "pines", lk_lt_npx - 1, a[0], a[2], a[1], a[3], base, a[4], P->ridge); } } }
    for (j = 0; j < LK_LT_FN; j++) for (i = 0; i < LK_LT_FN; i++) { lk_lt_fh[j][i] = -32768; lk_lt_fo[j][i] = 0; }   /* clean-up: the field holds the proxies only */
    for (k = 0; k < lk_lt_npx; k++) { const lk_lt_proxy *P = &lk_lt_px[k]; int i0, i1, j0, j1;   /* rasterise (4 units, sub column centres) */
      if (P->type == 4) { const int16_t (*m)[3] = lk_lt_meshes[P->part]; int e; if (!m) continue;   /* mesh: its stamped tops */
        for (e = 0; m[e][0] >= 0; e++) { int sx = m[e][0], sy = m[e][1], h = m[e][2]; if (lk_lt_fo[sy][sx] && lk_lt_fh[sy][sx] >= h) continue; lk_lt_fh[sy][sx] = (int16_t)h; lk_lt_fo[sy][sx] = P->obj; lk_lt_fp[sy][sx] = (uint8)(k + 1); }
        continue; }
      if (P->type == 5) { int cx, cy, sx, sy;   /* recurring objects (catalogue / data ops): the cells this proxy owns; all their sub columns belong to it (the march uses the base there, not the raised block) */
        for (cy = 0; cy < 74; cy++) for (cx = 0; cx < 74; cx++) { float top, r, zb; if (!lk_lt_tk[cy][cx] || lk_lt_tk[cy][cx] == 3 || lk_lt_to[cy][cx] != P->obj) continue;
          top = (float)lk_lt_tt[cy][cx]; r = (float)lk_lt_tr[cy][cx]; zb = (float)lk_lt_tb[cy][cx];
          for (sy = 4 * cy; sy < 4 * cy + 4; sy++) for (sx = 4 * cx; sx < 4 * cx + 4; sx++) { float dx = 4.0f * sx + 2.0f - (16.0f * cx + 8.0f), dy = 4.0f * sy + 2.0f - (16.0f * cy + 8.0f), d = sqrtf(dx * dx + dy * dy), h = zb;
            if (d < r) h = lk_lt_tk[cy][cx] == 2 ? top - (top - zb - 4.0f) * d / r : top - r + sqrtf(r * r - d * d);
            lk_lt_fh[sy][sx] = (int16_t)h; lk_lt_fo[sy][sx] = P->obj; lk_lt_fp[sy][sx] = (uint8)(k + 1); } }
        continue; }
      if (P->type == 1) { i0 = P->x0 >> 2; i1 = (P->x1 >> 2) - 1; j0 = P->y0 >> 2; j1 = (P->y1 >> 2) - 1; }
      else { i0 = (P->x0 - P->x1 - 2) >> 2; i1 = (P->x0 + P->x1 + 2) >> 2; j0 = (P->y0 - P->x1 - 2) >> 2; j1 = (P->y0 + P->x1 + 2) >> 2; }
      for (j = j0 < 0 ? 0 : j0; j <= j1 && j < LK_LT_FN; j++) for (i = i0 < 0 ? 0 : i0; i <= i1 && i < LK_LT_FN; i++) { float x = 4.0f * i + 2.0f, y = 4.0f * j + 2.0f, h;
        if (P->type == 1 && P->part && (lk_lt_part[j >> 2][i >> 2] != P->part || !lk_lt_pkeep[j >> 2][i >> 2])) continue;
        if (P->type == 1 && P->part && lk_lt_walk[j >> 2][i >> 2] && lk_lt_gh[j >> 2][i >> 2] <= P->z0) continue;   /* WALKABLE ground (clearings, paths, terraces read as an object): no solid over it (user 2026-11-04: 'weiter mit den Formen'; survey WALK) */
        if (lk_lt_flat[j >> 2][i >> 2] || lk_lt_tk[j >> 2][i >> 2]) continue;   /* data: flat; recurring objects have their own shape */   /* only the part's own cells: its box is a rectangle, the part may not be (a phantom wall cast the dark stripe in front of the church) */
        if (P->type == 1) { float w = (float)(P->x1 - P->x0), hh = (float)(P->y1 - P->y0), d = x - P->x0, half = 0.5f * (w < hh ? w : hh);
          if (P->x1 - x < d) d = P->x1 - x; if (y - P->y0 < d) d = y - P->y0; if (P->y1 - y < d) d = P->y1 - y;
          h = half > 0.0f ? (float)P->eave + (float)(P->ridge - P->eave) * d / half : (float)P->ridge; if (h > P->ridge) h = (float)P->ridge; }
        else if (P->type == 3) { float dx = x - P->x0, dy = y - P->y0, d = sqrtf(dx * dx + dy * dy); int kk, top = -1; for (kk = P->ridge - P->z0 - 1; kk >= 0; kk--) if ((float)lk_lt_prof[k][kk] >= d) { top = kk; break; } if (top < 0) continue; h = (float)(P->z0 + top + 1); }
        else { float dx = x - P->x0, dy = y - P->y0, d = sqrtf(dx * dx + dy * dy); if (d >= (float)P->x1 || P->x1 <= 0) continue; h = (float)P->ridge - (float)(P->ridge - P->z0) * d / (float)P->x1; }
        if (lk_lt_fo[j][i] && (float)lk_lt_fh[j][i] >= h) continue;
        lk_lt_fh[j][i] = (int16_t)h; lk_lt_fo[j][i] = P->obj; lk_lt_fp[j][i] = (uint8)(k + 1); } }
    lk_lt_fhmax = -32768;
    for (j = 0; j < LK_LT_FN; j++) for (i = 0; i < LK_LT_FN; i++) if (lk_lt_fo[j][i] && lk_lt_fh[j][i] > lk_lt_fhmax) lk_lt_fhmax = lk_lt_fh[j][i];
  }
  return n;
}
static void lk_lt_newroom(void) {   /* (v8 MT: waits for the light worker first: it reads everything rebuilt here) */   /* height map + lights of the current room */
  int x, y, k; static uint8 seen[152][304];
  lk_lt_jobwait(1);
  lk_lt_free(); lk_lt_nl = 0; lk_lt_zmax = 0;
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int w = UW(0xFFD192 + 148 * y + 2 * x); lk_lt_top[y][x] = (int16_t)(w == 0x4000 ? -32768 : 16 * ((w >> 8) & 15)); if (w != 0x4000 && lk_lt_top[y][x] > lk_lt_zmax) lk_lt_zmax = lk_lt_top[y][x]; }
  memcpy(lk_lt_gh, lk_lt_top, sizeof lk_lt_gh); lk_lt_fhmax = -32768; lk_lt_nc = 0; memset(lk_lt_obj, 0, sizeof lk_lt_obj);
  { static uint8 done[74][74]; static int16_t st[16][2]; memset(done, 0, sizeof done);   /* thin columns (lk_lt_thin) */
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) lk_lt_thin[y][x] = -32768;
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int w = UW(0xFFD192 + 148 * y + 2 * x), h = lk_lt_top[y][x], n = 0, m, ok = 1, gnd = -32768;
      if (done[y][x] || w == 0x4000 || h <= 0) continue;
      st[n][0] = (int16_t)x; st[n][1] = (int16_t)y; n++; done[y][x] = 1;
      for (m = 0; m < n && ok; m++) { int d, cx = st[m][0], cy = st[m][1]; static const int dd[4][2] = { {1, 0}, {-1, 0}, {0, 1}, {0, -1} };
        for (d = 0; d < 4; d++) { int nx = cx + dd[d][0], ny = cy + dd[d][1], t; if (nx < 0 || ny < 0 || nx >= 74 || ny >= 74) { ok = 0; break; }
          t = lk_lt_top[ny][nx];
          if (t == h) { int w2 = UW(0xFFD192 + 148 * ny + 2 * nx);   /* same height: the same column only with the same blocked flag (room 87: walkable pillar cells of height 5 in front of a blocked wall of height 5) */
            if (((w2 >> 8) & 0x60) != ((w >> 8) & 0x60)) continue;
            if (done[ny][nx]) { int q2, mine = 0; for (q2 = 0; q2 < n; q2++) if (st[q2][0] == nx && st[q2][1] == ny) mine = 1; if (mine) continue; ok = 0; break; }   /* 2026-11-07: a cell of an EARLIER flood
               (one that grew too big = a wall) joins this one: the end piece of a long wall is no column (room 86: wall x 38 rows 22..28, the last two cells were 'thin' beside a torch) */
            if (n >= 4) { ok = 0; break; } done[ny][nx] = 1; st[n][0] = (int16_t)nx; st[n][1] = (int16_t)ny; n++; continue; }
          if (t == -32768 || t > h) continue;   /* a void gap (stairwell, room 55) or a higher wall behind it: still a pillar (only columns that CARRY a flame stay thin, below) */
          if (t > gnd) gnd = t; } }
      if (ok && gnd > -32768 && !(getenv("LANDSTALKER_LT_THIN") && atoi(getenv("LANDSTALKER_LT_THIN")) == 0)) for (m = 0; m < n; m++) lk_lt_thin[st[m][1]][st[m][0]] = (int16_t)gnd; } }   /* test aid: LANDSTALKER_LT_THIN=0 switches the rule off */
  lk_lt_sun = lk_lt_sunp() && lk_lt_isout(lk_o_room);   /* v5 */
  lk_dn_cancel();   /* LK_DAYNIGHT v1 */
  lk_lt_key = 0; if (lk_lt_sun) lk_lt_sunset();   /* v8: lk_lt_sd may hold the key light of the room before */
  if (lk_lt_dbg == 1 && lk_lt_sun) printf("sun: room %%d az %%.0f el %%.0f dir %%.2f %%.2f %%.2f\n", lk_o_room, lk_lt_azd, lk_lt_eld, lk_lt_sd[0], lk_lt_sd[1], lk_lt_sd[2]);
  lk_lt_aor = !lk_lt_sun && lk_lt_aoopt() && lk_o_room >= 0 && !lk_lt_isout(lk_o_room) && !(lk_o_room >= 139 && lk_o_room <= 143) && lk_o_room != 148;   /* v8: indoors, not the intro */
  memset(lk_lt_vw, 0, sizeof lk_lt_vw); lk_lt_zref = -32768;
  if (lk_lt_aor) { int hist[16] = { 0 }, m, ok, best = 0;
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int w = UW(0xFFD192 + 148 * y + 2 * x);
      if (w != 0x4000 && !((w >> 8) & 0x60)) hist[(w >> 8) & 15]++;   /* walkable cell */
      if (lk_lt_top[y][x] != -32768) continue;
      for (ok = 1, m = 1; m <= 8 && x - m >= 0; m++) if (lk_lt_top[y][x - m] != -32768) { ok = 0; break; } if (ok) lk_lt_vw[y][x] |= 1;
      for (ok = 1, m = 1; m <= 8 && y - m >= 0; m++) if (lk_lt_top[y - m][x] != -32768) { ok = 0; break; } if (ok) lk_lt_vw[y][x] |= 2; }
    { static uint8 v2[74][74]; memcpy(v2, lk_lt_vw, sizeof v2);   /* a back wall is WIDE: >= 4 such void cells in a row along the wall (a water channel running to the room edge is narrow, room 185) */
      for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int a, r;
        if (v2[y][x] & 1) { for (r = 1, a = y - 1; a >= 0 && (v2[a][x] & 1); a--) r++; for (a = y + 1; a < 74 && (v2[a][x] & 1); a++) r++; if (r < 4) lk_lt_vw[y][x] &= (uint8)~1; }
        if (v2[y][x] & 2) { for (r = 1, a = x - 1; a >= 0 && (v2[y][a] & 2); a--) r++; for (a = x + 1; a < 74 && (v2[y][a] & 2); a++) r++; if (r < 4) lk_lt_vw[y][x] &= (uint8)~2; } } }
    for (m = 1; m < 16; m++) if (hist[m] > hist[best]) best = m;
    if (hist[best] > 0) lk_lt_zref = 16 * best; }
  if (lk_lt_sun && !(getenv("LANDSTALKER_LT_INVIS") && atoi(getenv("LANDSTALKER_LT_INVIS")) == 0)) { static int16_t dn2[74][74]; int ni = 0;   /* 2026-11-07 INVISIBLE BARRIERS outdoors (GitHub issue #14,
       room 483 north of Destel: 'out of place looking environmental shadow'): height map word $4Fxx = blocked + height 15 (240 units, taller than the screen) marks the invisible walls at a
       room's edge (483: x 21..23, y 50..60, nothing drawn there); they cast huge shadows with hard edges and no visible caster.  Our copy: such a cell takes the highest height of its
       non-barrier neighbours, BEFORE the water rule (a painted void cell beside a barrier became a 'water floor' at 232 = an invisible block, room 483 front edge).  Test aid LANDSTALKER_LT_INVIS=0 */
    memcpy(dn2, lk_lt_top, sizeof dn2);
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int w = UW(0xFFD192 + 148 * y + 2 * x), m = -32768, a, b2; if (w == 0x4000 || (w >> 8) != 0x4F) continue;
      for (b2 = y - 1; b2 <= y + 1; b2++) for (a = x - 1; a <= x + 1; a++) { int w2; if (a < 0 || b2 < 0 || a >= 74 || b2 >= 74) continue; w2 = UW(0xFFD192 + 148 * b2 + 2 * a);
        if (w2 == 0x4000 || (w2 >> 8) == 0x4F || lk_lt_top[b2][a] == -32768) continue; if (lk_lt_top[b2][a] > m) m = lk_lt_top[b2][a]; }
      dn2[y][x] = (int16_t)(m == -32768 ? 0 : m); ni++; }
    memcpy(lk_lt_top, dn2, sizeof dn2);
    if (lk_lt_dbg == 1 && ni) printf("invisible barriers: room %%d, %%d cells lowered\n", lk_o_room, ni); }
  memset(lk_lt_wat, 0, sizeof lk_lt_wat);
  if (lk_lt_sun || lk_lt_aor) { int pass, ch = 1, nw = 0; static int16_t org[74][74];   /* v8: also indoors (room light): painted water beside a walkway was void = an endless wall down = a dark box on the water (room 185, lightedges) */
    memcpy(org, lk_lt_top, sizeof org);
    /* proxies: WATER = a void cell whose picture is painted (river, pond): a floor 8 below its lowest neighbour (user: 'Nigels Schatten biegt sich am Fluss auf als waere das eine Wand');
       our copy only (lk_lt_top / lk_lt_gh), unpainted void (the black outside) stays void */
    for (pass = 0; pass < 12 && ch; pass++) { static int16_t nh[74][74]; ch = 0;
      for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int m = 9999, a, b2, U, V, pal, pr, wo = 0; nh[y][x] = lk_lt_top[y][x];
        if (lk_lt_top[y][x] != -32768) continue;
        if (!lk_lt_sun) { int e1 = 0, e2 = 0, e3 = 0, e4 = 0, d;   /* v8 indoors: never a back wall void, and only between room cells (a channel / pool INSIDE the room): room cells within 8 on both sides along x or along y, else a front edge wall (painted down into the black) would become a floor */
          if (lk_lt_vw[y][x]) continue;
          for (d = 1; d <= 8; d++) { if (x - d >= 0 && org[y][x - d] != -32768) e1 = 1; if (x + d < 74 && org[y][x + d] != -32768) e2 = 1; if (y - d >= 0 && org[y - d][x] != -32768) e3 = 1; if (y + d < 74 && org[y + d][x] != -32768) e4 = 1; }
          if (!((e1 && e2) || (e3 && e4))) { if (!pass) continue; wo = 1; } }   /* v8: outside that only as a continuation of water found already (the water runs on to the room edge in the picture, room 185), at the water's height */
        for (b2 = y - 1; b2 <= y + 1; b2++) for (a = x - 1; a <= x + 1; a++) if (a >= 0 && b2 >= 0 && a < 74 && b2 < 74 && lk_lt_top[b2][a] != -32768 && lk_lt_top[b2][a] < m && (!wo || lk_lt_wat[b2][a])) m = lk_lt_top[b2][a];
        if (m == 9999) continue;
        m = pass == 0 ? m - 8 : m; if (m < 0) m = 0;
        U = 16 * (x - y) + 1184; V = 8 * (x + y) + 8 - m;
        if (!lk_o_fetch(lk_o_pb, U, V, &pal, &pr, 0) && !lk_o_fetch(lk_o_pa, U, V, &pal, &pr, 0)) continue;
        nh[y][x] = (int16_t)m; lk_lt_wat[y][x] = 1; ch = 1; nw++; }
      memcpy(lk_lt_top, nh, sizeof nh); }
    { int q; for (q = 0; lk_lt_corr[q].room >= 0; q++) if (lk_lt_corr[q].room == lk_o_room && lk_lt_corr[q].op == 2) { const int16_t *a = lk_lt_corr[q].a;   /* data: water */
        for (y = a[1]; y <= a[3]; y++) for (x = a[0]; x <= a[2]; x++) if (x >= 0 && y >= 0 && x < 74 && y < 74) { lk_lt_top[y][x] = a[4]; lk_lt_wat[y][x] = 1; nw++; } } }
    if (lk_lt_sun && !(getenv("LANDSTALKER_LT_DOORFILL") && atoi(getenv("LANDSTALKER_LT_DOORFILL")) == 0)) { static int16_t dn[74][74]; int nd = 0, ax;   /* 2026-11-07 DOOR NICHES outdoors (user rec_20261107_1822,
         room 635: 'das Haus hat einen harten Kanten Schatten ueber der Tuere'): a door is a 1..3 cell niche in the height map that runs up the WHOLE wall (cell 23,31 height 16 in a wall of 112),
         so the wall above the door was a deep slot shaded by its sides = a dark band with hard edges.  Our copy: the niche is filled up to the wall (the door sits flush); test aid LANDSTALKER_LT_DOORFILL=0 */
      memcpy(dn, lk_lt_top, sizeof dn);
      for (y = 1; y < 73; y++) for (x = 1; x < 73; x++) { int h = lk_lt_top[y][x]; if (h == -32768) continue;
        for (ax = 0; ax < 2; ax++) { int fx = ax == 0, fy = ax == 1, sx2 = fy, sy2 = fx, n = 1, d, lo = 9999, ok = 1, bt, ft;   /* ax 0: wall face +x (the niche opens to +x, its sides along y); ax 1: face +y */
          bt = lk_lt_top[y - fy][x - fx]; ft = lk_lt_top[y + fy][x + fx];
          if (bt == -32768 || bt < h + 32 || ft == -32768 || ft > h + 8) continue;
          for (d = 1; ; d++) { int cx = x - d * sx2, cy = y - d * sy2, t = (cx >= 0 && cy >= 0) ? lk_lt_top[cy][cx] : -32768; if (t == h) { if (++n > 3) { ok = 0; break; } continue; } if (t == -32768 || t < h + 32) ok = 0; else if (t < lo) lo = t; break; }
          for (d = 1; ok; d++) { int cx = x + d * sx2, cy = y + d * sy2, t = (cx < 74 && cy < 74) ? lk_lt_top[cy][cx] : -32768; if (t == h) { if (++n > 3) { ok = 0; break; } continue; } if (t == -32768 || t < h + 32) ok = 0; else if (t < lo) lo = t; break; }
          if (ok && lo < 9999) { if (bt < lo) lo = bt; if (lo > dn[y][x]) { dn[y][x] = (int16_t)lo; nd++; } } } }
      memcpy(lk_lt_top, dn, sizeof dn);
      if (lk_lt_dbg == 1 && nd) printf("door niches: room %%d, %%d cells filled\n", lk_o_room, nd); }
    memcpy(lk_lt_gh, lk_lt_top, sizeof lk_lt_gh);
    if (lk_lt_dbg == 5) printf("water: room %%d, %%d void cells painted -> floor\n", lk_o_room, nw); }
  { struct timespec t0; clock_gettime(CLOCK_MONOTONIC, &t0);
    if (lk_lt_sun && lk_lt_extrude()) for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) if (lk_lt_top[y][x] > lk_lt_zmax) lk_lt_zmax = lk_lt_top[y][x];
    memset(lk_lt_cpk, 0, sizeof lk_lt_cpk);
    if (lk_lt_sun) for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int i, j, top = -32768, x0 = 4, x1 = -1, y0 = 4, y1 = -1;   /* side penumbra data (lk_lt_cpk) */
      for (j = 0; j < 4; j++) for (i = 0; i < 4; i++) { int sx = 4 * x + i, sy = 4 * y + j, q = lk_lt_fp[sy][sx], f = lk_lt_fh[sy][sx];
        if (!lk_lt_fo[sy][sx] || f <= lk_lt_gh[y][x] || (q && (lk_lt_px[q - 1].type == 5 || lk_lt_px[q - 1].type == 3))) continue;
        if (f > top) top = f; if (i < x0) x0 = i; if (i > x1) x1 = i; if (j < y0) y0 = j; if (j > y1) y1 = j; }
      if (top > 0) { int tq = (top + 3) / 4; if (tq > 255) tq = 255; lk_lt_cpk[y][x] = (uint16_t)(tq | (x0 << 8) | (x1 << 10) | (y0 << 12) | (y1 << 14)); } }
    if (lk_lt_dbg == 5 && lk_lt_sun) printf("extrude: room %%d %%.1f ms, %%d cards\n", lk_o_room, lk_sm_ms_since(&t0), lk_lt_nc); }   /* v7 test aid: room load cost of the outdoor objects */
  if (lk_lt_sun && lk_lt_fhmax > lk_lt_zmax) lk_lt_zmax = lk_lt_fhmax;   /* v7: the sun march stops above the highest object */
  lk_lt_ztop = lk_lt_zmax; lk_lt_pah = lk_lt_pahash();
  if (lk_lt_sun) lk_lt_horizon();   /* v7 speed */
  lk_lt_zmax += 192;   /* walls stand high above the floor: the view ray must start above the top of the back walls (v2: was 48, the torches of room 177 hang higher) */
  memset(seen, 0, sizeof seen);
  if (lk_lt_get()) for (k = 0; k < lk_o_ngrp; k++) {   /* v5: flames only with the Lighting option (the sun works without it) */
    float cr, cg, cb; int t0 = lk_o_grp[k].dest / 32, tn = lk_o_grp[k].words * 2 / 32, r0, c0, kind = lk_lt_isflame(lk_o_grp[k].base, &cr, &cg, &cb);
    if (kind == 2 && lk_o_room != 403 && lk_o_room != 404) continue;   /* entry 21 is red lava only in rooms 403 / 404; blue water in 406..411 (same tiles, other palette; ROM colour check 2026-11-03) */
    if (!kind || tn < 1) continue;
    if (kind == 2) {   /* a field (lava): one light per 8 x 8 cells with >= 8 of its tiles, at their centre, above the surface */
      #define LK_LT_IN(rr, cc) ((((lk_o_pa[rr][cc] & 0x10000) && (int)(lk_o_pa[rr][cc] & 0x7FF) >= t0 && (int)(lk_o_pa[rr][cc] & 0x7FF) < t0 + tn)) || (((lk_o_pb[rr][cc] & 0x10000) && (int)(lk_o_pb[rr][cc] & 0x7FF) >= t0 && (int)(lk_o_pb[rr][cc] & 0x7FF) < t0 + tn)))
      for (r0 = 0; r0 < 152; r0 += 8) for (c0 = 0; c0 < 304; c0 += 8) {
        int rr, cc, n = 0, su = 0, sv = 0;
        for (rr = r0; rr < r0 + 8; rr++) for (cc = c0; cc < c0 + 8; cc++) if (LK_LT_IN(rr, cc)) { n++; su += cc * 8 + 4; sv += rr * 8 + 4; }
        if (n < 8 || lk_lt_nl >= LK_LT_ML) continue;
        { int U = su / n, V = sv / n, z = 0, f = lk_lt_ray(U, V, &z); float px, py; lk_lt_light *L = &lk_lt_l[lk_lt_nl];
          if (!f) continue;
          lk_lt_pos(U, V, z, &px, &py);
          L->x = px; L->y = py; L->z = (float)z + 10.0f; L->r = cr; L->g = cg; L->b = cb; L->lava = 1; L->base = lk_o_grp[k].base; L->k = 1.0f; L->rad = LK_LT_RAD; lk_lt_nl++; }
      }
      #undef LK_LT_IN
      continue;
    }
    for (r0 = 0; r0 < 152; r0++) for (c0 = 0; c0 < 304; c0++) {
      static int16_t st[4096][2]; int sp = 0, n = 0, su = 0, sv = 0;
      #define LK_LT_IS(rr, cc) ((((lk_o_pa[rr][cc] & 0x10000) && (int)(lk_o_pa[rr][cc] & 0x7FF) >= t0 && (int)(lk_o_pa[rr][cc] & 0x7FF) < t0 + tn && lk_lt_tileok(lk_o_grp[k].base, (int)(lk_o_pa[rr][cc] & 0x7FF)))) || (((lk_o_pb[rr][cc] & 0x10000) && (int)(lk_o_pb[rr][cc] & 0x7FF) >= t0 && (int)(lk_o_pb[rr][cc] & 0x7FF) < t0 + tn && lk_lt_tileok(lk_o_grp[k].base, (int)(lk_o_pb[rr][cc] & 0x7FF)))))
      if (seen[r0][c0] || !LK_LT_IS(r0, c0)) continue;
      seen[r0][c0] = 1; st[sp][0] = (int16_t)r0; st[sp][1] = (int16_t)c0; sp++;
      while (sp) { int rr, cc, dr, dc; sp--; rr = st[sp][0]; cc = st[sp][1]; n++; su += cc * 8 + 4; sv += rr * 8 + 4;
        for (dr = -1; dr <= 1; dr++) for (dc = -1; dc <= 1; dc++) { int r2 = rr + dr, c2 = cc + dc; if (r2 >= 0 && r2 < 152 && c2 >= 0 && c2 < 304 && !seen[r2][c2] && LK_LT_IS(r2, c2) && sp < 4096) { seen[r2][c2] = 1; st[sp][0] = (int16_t)r2; st[sp][1] = (int16_t)c2; sp++; } } }
      #undef LK_LT_IS
      if (n > 40 || lk_lt_nl >= LK_LT_ML) continue;
      { int U = su / n, V = sv / n, z = 0, f = lk_lt_ray(U, V, &z); float px, py; lk_lt_light *L = &lk_lt_l[lk_lt_nl];
        if (!f) continue;
        lk_lt_pos(U, V, z, &px, &py);
        L->x = px + (f == 2 ? 6.0f : 0.0f); L->y = py + (f == 3 ? 6.0f : 0.0f); L->z = (float)z + (f == 1 ? 8.0f : 2.0f); L->r = cr; L->g = cg; L->b = cb; L->lava = 0; L->base = lk_o_grp[k].base;
        L->k = 1.0f; L->rad = LK_LT_RAD; if (L->base == 0x098AAA) { L->k = 1.15f; L->rad = 260.0f; }   /* the standing torches of the castle (user 2026-11-04: 'im Schloss zu dunkel, koennte nur diese Art der Fackel mehr Licht abgeben?'; 2026-11-05: base light 0.85, then this torch a bit weaker: k 1.5 -> 1.15) */
        lk_lt_nl++; }
    }
  }
  if (lk_lt_dbg == 3) { int x0 = 18, y0 = 18; const char *e = getenv("LANDSTALKER_LT_HMWIN"); if (e) sscanf(e, "%%d,%%d", &x0, &y0);   /* LANDSTALKER_LT_HMWIN=x0,y0: the 26 x 16 window printed (lk_lt_top / lk_lt_gh) */
    for (y = y0; y < y0 + 16 && y < 74; y++) { printf("hm %%2d:", y); for (x = x0; x < x0 + 26 && x < 74; x++) printf(" %%4d", y < 0 || x < 0 ? -2 : lk_lt_top[y][x] == -32768 ? -1 : lk_lt_top[y][x]); printf("  | gh"); for (x = x0; x < x0 + 26 && x < 74; x++) printf(" %%4d", y < 0 || x < 0 ? -2 : lk_lt_gh[y][x] == -32768 ? -1 : lk_lt_gh[y][x]); printf("\n"); } }
  { const char *e = getenv("LANDSTALKER_LT_THINRAY"); lk_lt_thinz = e && atoi(e) == 0 ? 8.0f : 16.0f; } { const char *e = getenv("LANDSTALKER_LT_SSIDE"); lk_lt_sside = !(e && atoi(e) == 0); }   /* 2026-11-07 (user rec_20261107_1822, room 680: light box + hard shadow at the standing torch
       by the wall): the flame is found 15 below its pillar's collision top (light (293, 415, 49), pillar (17, 25) top 64: the drawn torch stands one cell in front of its collision
       cell, at the room's front edge) -> tolerance 16 (was 8); test aid LANDSTALKER_LT_THINRAY=0 = 8 */
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) if (lk_lt_thin[y][x] > -32768) { int keep = 0;   /* only a column that CARRIES a flame (a light within one cell, at or above its top) stays thin:
       wall pieces at the edge of the void looked like free standing columns too (user 2026-11-05: big wrong shadow in room 55) */
    for (k = 0; k < lk_lt_nl; k++) { int lx = (int)floorf(lk_lt_l[k].x / 16.0f), ly = (int)floorf(lk_lt_l[k].y / 16.0f); if (abs(lx - x) <= 1 && abs(ly - y) <= 1 && lk_lt_l[k].z >= (float)lk_lt_top[y][x] - lk_lt_thinz) keep = 1; }
    if (!keep) lk_lt_thin[y][x] = -32768;
    else if (lk_lt_dbg == 1) printf("thin column: room %%d cell %%d,%%d top %%d floor %%d\n", lk_o_room, x, y, lk_lt_top[y][x], lk_lt_thin[y][x]); }
  lk_lt_nfl = lk_lt_nl;   /* LK_DAYNIGHT v3: the flames (lava, torches); window lights follow */
  if (lk_lt_sun && lk_dn_get() && lk_o_room >= 0 && (OB(OL(0xA0A00) + 8u * (uint32_t)lk_o_room + 4u) & 0x1F) == 0) {   /* v3 WINDOW LIGHT (user 2026-11-06: 'auf den Boden vor dem Haus fallendes Licht aus den Fenstern', 'muss fuer Nigels Schatten beruecksichtigt werden'):
       one weak warm light in front of every window (tileset 0 window tiles, one group per window), strength = the window glow (lk_lt_flk = lk_dn_wk), figures cast shadows from it like from a torch */
    static uint8 wseen[152][304]; static int16_t st[512][2]; int r0, c0;
    memset(wseen, 0, sizeof wseen);
    #define LK_DN_ISW(rr, cc) (lk_dn_iswt(lk_o_pa[rr][cc]) || lk_dn_iswt(lk_o_pb[rr][cc]))
    for (r0 = 0; r0 < 152; r0++) for (c0 = 0; c0 < 304; c0++) { int sp = 0, n = 0, su = 0, sv = 0;
      if (wseen[r0][c0] || !LK_DN_ISW(r0, c0)) continue;
      wseen[r0][c0] = 1; st[sp][0] = (int16_t)r0; st[sp][1] = (int16_t)c0; sp++;
      while (sp) { int rr, cc, dr, dc; sp--; rr = st[sp][0]; cc = st[sp][1]; n++; su += cc * 8 + 4; sv += rr * 8 + 4;
        for (dr = -1; dr <= 1; dr++) for (dc = -1; dc <= 1; dc++) { int r2 = rr + dr, c2 = cc + dc; if (r2 >= 0 && r2 < 152 && c2 >= 0 && c2 < 304 && !wseen[r2][c2] && LK_DN_ISW(r2, c2) && sp < 512) { wseen[r2][c2] = 1; st[sp][0] = (int16_t)r2; st[sp][1] = (int16_t)c2; sp++; } } }
      if (n > 12 || lk_lt_nl >= LK_LT_ML) continue;
      { int U = su / n, V = sv / n, z = 0, f = lk_lt_ray(U, V, &z); float px, py; lk_lt_light *L = &lk_lt_l[lk_lt_nl];
        if (f != 2 && f != 3) continue;   /* the window must sit on a wall facing the viewer */
        lk_lt_pos(U, V, z, &px, &py);
        L->x = px + (f == 2 ? 14.0f : 0.0f); L->y = py + (f == 3 ? 14.0f : 0.0f); L->z = (float)z - 6.0f; L->r = 1.0f; L->g = 0.68f; L->b = 0.32f; L->lava = 2; L->base = (uint32_t)f;
        { int q, mg = 0; for (q = lk_lt_nfl; q < lk_lt_nl; q++) { lk_lt_light *M = &lk_lt_l[q]; float ddx = M->x - L->x, ddy = M->y - L->y, ddz = M->z - L->z;   /* windows of one wall within 56 units share one light (fewer lights: Mercator had 42) */
            if (M->base == (uint32_t)f && ddx * ddx + ddy * ddy + ddz * ddz < 56.0f * 56.0f) { M->x = (M->x + L->x) * 0.5f; M->y = (M->y + L->y) * 0.5f; M->z = (M->z + L->z) * 0.5f; M->k += 0.12f; mg = 1; break; } }
          if (mg) continue; }
        L->k = 0.30f; L->rad = 76.0f; lk_lt_nl++;   /* weak and short: a room holds up to ~40 windows (k 0.85 / reach 120 lit whole towns like day) */
        if (lk_lt_dbg == 1) printf("window light: room %%d at (%%.0f, %%.0f, %%.0f) face %%d\n", lk_o_room, L->x, L->y, L->z, f); } }
    #undef LK_DN_ISW
  }
  lk_lt_key = lk_lt_aor && !lk_lt_nl && lk_lt_keyopt() > 0; if (lk_lt_key) lk_lt_keyset();   /* v8 key light: indoors, rooms without flames */
  lk_lt_shsetup();   /* v8 light shafts */
  lk_am_setup();   /* v8 ambient particles */
  if (lk_lt_dbg) { printf("lighting: room %%d, %%d lights\n", lk_o_room, lk_lt_nl); for (k = 0; k < lk_lt_nl; k++) printf("  light %%d at (%%.0f, %%.0f, %%.0f) flame $%%06X%%s\n", k, lk_lt_l[k].x, lk_lt_l[k].y, lk_lt_l[k].z, (unsigned)lk_lt_l[k].base, lk_lt_solid(lk_lt_l[k].x, lk_lt_l[k].y, lk_lt_l[k].z) ? " INSIDE A SOLID" : ""); }
}
static int lk_lt_swtest(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_LIGHTING_SWORD"); v = e ? atoi(e) : 0; if (v < 0 || v > 4) v = 0; } return v; }   /* test aid: sword glow colour 1..4 without that sword */
/* ---- LK_DAYNIGHT v1 (+ v2 colours 2026-11-06): the day / night cycle (sun path, moon, light colours by the time of day, time-lapse) ---- */
static double lk_dn_t = -1.0; static volatile int lk_dn_fast = -1; static float lk_dn_naz, lk_dn_nel; static int lk_dn_dbg = -1; static double lk_dn_len = 24.0;
static float lk_dn_ss(float a, float b, float x) { float t = (x - a) / (b - a); if (t < 0.0f) t = 0.0f; if (t > 1.0f) t = 1.0f; return t * t * (3.0f - 2.0f * t); }
static void lk_dn_lerp(const float *E, const float (*C)[3], int n, float e, float *o) {   /* piecewise linear over E (ascending) */
  int k; if (e <= E[0]) { o[0] = C[0][0]; o[1] = C[0][1]; o[2] = C[0][2]; return; }
  for (k = 1; k < n; k++) if (e <= E[k]) { float t = (e - E[k - 1]) / (E[k] - E[k - 1]); int c; for (c = 0; c < 3; c++) o[c] = C[k - 1][c] + (C[k][c] - C[k - 1][c]) * t; return; }
  o[0] = C[n - 1][0]; o[1] = C[n - 1][1]; o[2] = C[n - 1][2]; }
static float lk_dn_minel(void) { static float v = -1.0f; if (v < 0.0f) { const char *e = getenv("LANDSTALKER_DN_MINEL"); v = e ? (float)atof(e) : 35.0f; if (v < 5.0f) v = 5.0f; if (v > 60.0f) v = 60.0f; } return v; }
static void lk_dn_dir(double t, float *az, float *el) {   /* LK_DAYNIGHT v5 (user 2026-11-06: 'Schatten sehr lang abends und morgens', 'der Schatten springt einmal komplett 180 Grad wenn die Nacht wieder zum Tag wird'):
     the light's direction only.  Sun 6:00 -> 18:00 from az 10 to 170 (as v1); the MOON now walks the path BACKWARDS 18:00 -> 6:00 (170 -> 10), so the shadow direction is continuous at
     dusk and dawn (v1..v4: the moon started at 10 again = a ~160 deg jump); lowest elevation LANDSTALKER_DN_MINEL (35, user 2026-11-06 'nicht unter 35 Grad'; v5 first 22, before 12: shadows at most ~1.4 x the height instead of ~4.7 x) */
  float p = (float)(fmod(t - 6.0 + 48.0, 24.0) / 12.0), q = (float)(fmod(t - 18.0 + 48.0, 24.0) / 12.0), es = 58.0f * sinf(3.14159265f * p), em = 40.0f * sinf(3.14159265f * q), mn = lk_dn_minel();
  if (es > -3.0f) { *az = 90.0f - 80.0f * cosf(3.14159265f * p); *el = es > mn ? es : mn; }
  else { *az = 90.0f + 80.0f * cosf(3.14159265f * (q > 1.0f ? 1.0f : q)); *el = em > mn ? em : mn; } }
static void lk_dn_eval(double t, float *az, float *el) {   /* time of day (hours) -> shadow direction + colours (lk_dn_amb3, lk_dn_sun3 before the sun strength factor) */
  /* v2 (user 2026-11-06: 'Farben morgens / abends roetlicher', 'Uebergang Abend -> Nacht wirkt recht ploetzlich', 'nachts schon sehr dunkel'): redder low sun, twilight over twice the elevation range, brighter night */
  static const float EA[9] = { -90, -16, -9, -3, 2, 7, 14, 28, 90 };   /* sky light, relative to the noon sky light (lk_lt_sS * 0.95 / 0.98 / 1.06): night blue, blue hour, violet-red, red dusk, day */
  static const float CA[9][3] = { { 0.45f, 0.50f, 0.72f }, { 0.45f, 0.50f, 0.72f }, { 0.50f, 0.50f, 0.70f }, { 0.66f, 0.52f, 0.62f }, { 0.86f, 0.62f, 0.56f }, { 0.95f, 0.78f, 0.70f }, { 0.99f, 0.92f, 0.88f }, { 1, 1, 1 }, { 1, 1, 1 } };
  static const float ES[6] = { 0, 4, 9, 16, 30, 90 };   /* sun colour, relative to the day sun (1, 0.97, 0.90): red at the horizon, orange-red low sun, white at noon */
  static const float CS[6][3] = { { 1, 0.48f, 0.32f }, { 1, 0.56f, 0.38f }, { 1, 0.70f, 0.52f }, { 1, 0.86f, 0.74f }, { 1, 1, 1 }, { 1, 1, 1 } };
  float p = (float)(fmod(t - 6.0 + 48.0, 24.0) / 12.0), q = (float)(fmod(t - 18.0 + 48.0, 24.0) / 12.0);   /* day / night fraction 0..2 (sunrise 6:00, sunset 18:00) */
  float es = 58.0f * sinf(3.14159265f * p), em = 40.0f * sinf(3.14159265f * q), fs = lk_dn_ss(-3.0f, 10.0f, es), fm = 0.38f * lk_dn_ss(0.0f, 10.0f, em) * lk_dn_ss(-3.0f, -14.0f, es), a3[3], c3[3];   /* v2: the sun fades over 13 deg (was 9), the moon a bit stronger */
  float N[3] = { lk_lt_sS * 0.95f, lk_lt_sS * 0.98f, lk_lt_sS * 1.06f };
  lk_dn_lerp(EA, CA, 9, es, a3); lk_dn_amb3[0] = N[0] * a3[0]; lk_dn_amb3[1] = N[1] * a3[1]; lk_dn_amb3[2] = N[2] * a3[2];
  lk_dn_dir(t, az, el);   /* LK_DAYNIGHT v5: direction in its own function (the smooth steps look ahead) */
  if (es > -3.0f) { lk_dn_lerp(ES, CS, 6, es, c3);   /* the sun: from the upper left of the world to the lower right over noon (az 90 = the day light the user picked), shadows at most ~4.7 x the height */
    lk_dn_sun3[0] = c3[0] * fs; lk_dn_sun3[1] = 0.97f * c3[1] * fs; lk_dn_sun3[2] = 0.90f * c3[2] * fs; }
  else {   /* the moon: weak cold light with soft shadows (direction: lk_dn_dir) */
    lk_dn_sun3[0] = 0.55f * fm; lk_dn_sun3[1] = 0.68f * fm; lk_dn_sun3[2] = 1.00f * fm; }
  lk_dn_sunk = fs; lk_dn_night = es < -6.0f; }
static int lk_dn_iswt(uint32 c) { int t; if (!(c & 0x10000)) return 0; t = (int)(c & 0x7FF); return t == 195 || t == 196 || t == 199 || t == 210 || t == 211; }   /* v3: a plane cell holds a window tile */
static int lk_dn_win;   /* v2 LIT WINDOWS (user 2026-11-06: 'beleuchtete Fenster nachts find ich gut'): window glass glows warm from dusk on.  Tileset 0 (Ryuma, Mercator, Verla houses):
   the window tiles 195 / 196 / 199 / 210 / 211 (right walls: the same, mirrored), glass = colour indexes 1 / 14 of palette line 0 (the walls of these tiles use 2 / 3 / 4 / 13; the church windows share
   the wall grey and are left out; the log huts of tileset 7 have no glass).  Strength = 1 - the sun factor (lk_dn_sunk). */
static float lk_dn_wk; static uint8 lk_dn_wm[6][8]; static int lk_dn_wmroom = -2;   /* v3: glass mask per window tile (bit x of row y, tile-native coordinates) */
static const int lk_dn_wt[6] = { 195, 196, 199, 200, 210, 211 };   /* tileset 0 window tiles, as left | right pairs (195 196) (199 200) (210 211); right walls draw them mirrored */
static void lk_dn_wmask(void) {   /* v3 (user 2026-11-06: 'Ecken im Fenster, Randpixel unsauber'): glass = index 1 / 14 pixels BETWEEN two frame pixels (index 15) of the same row of the
     pair; v2 lit every 1 / 14 pixel of the tiles: the light outer frame edge beside the black frame and the sill glowed */
  int p, y, x;
  lk_dn_wmroom = lk_o_room; memset(lk_dn_wm, 0, sizeof lk_dn_wm);
  for (p = 0; p < 3; p++) for (y = 0; y < 8; y++) { int v[16], f0 = -1, f1 = -1;
    for (x = 0; x < 16; x++) { int t = lk_dn_wt[2 * p + (x >> 3)], b = lk_o_tiles[t * 32 + y * 4 + ((x & 7) >> 1)]; v[x] = (x & 1) ? (b & 15) : (b >> 4); if (v[x] == 15) { if (f0 < 0) f0 = x; f1 = x; } }
    for (x = f0 + 1; f0 >= 0 && x < f1; x++) if (v[x] == 1 || v[x] == 14) lk_dn_wm[2 * p + (x >> 3)][y] |= (uint8)(1u << (x & 7)); } }
static int lk_dn_winpix(const lk_o_fi_t *fi, int pick, int col) {
  long o; int ti, idx = pick & 15, r, g, b, w, k; uint32_t c = (uint32_t)col, gl;
  if ((pick >> 4) != 0 || (idx != 1 && idx != 14) || !fi->t || fi->t < lk_o_tiles || fi->t >= lk_o_tiles + sizeof lk_o_tiles) return col;
  o = (long)(fi->t - lk_o_tiles); ti = (int)(o >> 5);
  for (k = 0; k < 6 && lk_dn_wt[k] != ti; k++) ;
  if (k >= 6) return col;
  if (lk_dn_wmroom != lk_o_room) lk_dn_wmask();
  if (!(lk_dn_wm[k][fi->iy & 7] >> (fi->ix & 7) & 1)) return col;
  gl = idx == 1 ? 0xFFC864u : 0xE89A48u;   /* warm lamp light; the darker glass a deeper orange */
  w = (int)(lk_dn_wk * lk_lt_fadek * 235.0f);   /* (v4: fades with the palette) */
  r = (int)((c >> 16) & 255); g = (int)((c >> 8) & 255); b = (int)(c & 255);
  r += (((int)(gl >> 16) & 255) - r) * w / 256; g += (((int)(gl >> 8) & 255) - g) * w / 256; b += ((int)(gl & 255) - b) * w / 256;
  return (int)((c & 0xFF000000u) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b); }
static float lk_dn_cloudf(void) { return lk_dn_on ? lk_dn_sunk : 1.0f; }   /* tools/patch_clouds.py: no cloud shadows at night */
void lk_dn_fasttoggle(void) { extern void lk_osd_say(const char *t); char m[40]; if (lk_dn_fast < 0) lk_dn_fast = 0; lk_dn_fast = !lk_dn_fast;   /* pad L5 + R5 together (src/input.c) */
  if (lk_dn_t < 0.0) lk_dn_t = 9.0;
  snprintf(m, sizeof m, "TIMELAPSE %%s %%02d:%%02d", lk_dn_fast ? "ON" : "OFF", (int)lk_dn_t, (int)(fmod(lk_dn_t, 1.0) * 60.0)); lk_osd_say(m); }
static void lk_dn_save(void) { const char *h = getenv("HOME"); char pth[512]; FILE *f; snprintf(pth, sizeof pth, "%%s/.landstalker_daytime", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%.3f\n", lk_dn_t); fclose(f); } }
static void lk_dn_cancel(void) {   /* a new room: no step in progress, the target direction is built at once */
  lk_dn_upd = 0; lk_dn_mix = 0; if (lk_lt_azt >= 0.0f) { lk_lt_azd = lk_lt_azt; lk_lt_eld = lk_lt_elt; } }
static void lk_dn_frame(long fr, int idle) {   /* once per lit frame in lk_lt_step, before the prefetch: time, target sun, sun steps */
  extern void lk_osd_say(const char *t); char m[48]; static long lastsay;
  if (lk_dn_dbg < 0) { const char *e = getenv("LANDSTALKER_DN_DBG"), *l = getenv("LANDSTALKER_DAYLEN"); lk_dn_dbg = e ? atoi(e) : 0; if (l && atof(l) > 0.05) lk_dn_len = atof(l); }
  if (lk_dn_fast < 0) { const char *e = getenv("LANDSTALKER_TIMELAPSE"); lk_dn_fast = e && atoi(e) > 0; }
  if (lk_lt_azt < 0.0f) { lk_lt_azt = lk_lt_azd; lk_lt_elt = lk_lt_eld; }
  { static const char *at = (const char *)1;   /* test aid LANDSTALKER_SUN_AT="frame:az:el,..." (without the cycle) */
    if (at == (const char *)1) at = getenv("LANDSTALKER_SUN_AT");
    if (at) { char l[256], *t; snprintf(l, sizeof l, "%%s", at); for (t = strtok(l, ","); t; t = strtok(NULL, ",")) { long f; float a2, e2; if (sscanf(t, "%%ld:%%f:%%f", &f, &a2, &e2) == 3 && f == fr) { lk_lt_azt = a2; lk_lt_elt = e2; lk_lt_sunmov = 1; } } } }
  if (lk_dn_get()) {
    if (lk_dn_t < 0.0) { const char *e = getenv("LANDSTALKER_DAYTIME"), *h = getenv("HOME"); char pth[512]; FILE *f; lk_dn_t = 9.0;   /* the time of day goes on where it was (~/.landstalker_daytime), first start 9:00 */
      snprintf(pth, sizeof pth, "%%s/.landstalker_daytime", h ? h : "."); if ((f = fopen(pth, "r"))) { double v; if (fscanf(f, "%%lf", &v) == 1 && v >= 0.0 && v < 24.0) lk_dn_t = v; fclose(f); }
      if (e) lk_dn_t = fmod(atof(e) + 24.0, 24.0); }
    { double sc = lk_dn_scrub, before = lk_dn_t; lk_dn_scrub -= sc;
      lk_dn_t = fmod(lk_dn_t + sc + (lk_dn_fast ? 24.0 / 3600.0 : 24.0 / (lk_dn_len * 3600.0)) + 48.0, 24.0);   /* normal: a day in LANDSTALKER_DAYLEN minutes (24 = one hour per minute); time-lapse: a day in 60 s */
      if ((sc != 0.0 && fr - lastsay >= 6) || (lk_dn_fast && (int)before != (int)lk_dn_t)) { snprintf(m, sizeof m, "%%02d:%%02d", (int)lk_dn_t, (int)(fmod(lk_dn_t, 1.0) * 60.0)); lk_osd_say(m); lastsay = fr; } }
    if (fr %% 1800 == 0) lk_dn_save(); }
  lk_dn_on = lk_dn_get() && lk_lt_sun;
  lk_dn_win = 0;
  if (!lk_dn_on) { lk_dn_sunk = 1.0f; lk_dn_night = 0; }
  else { float az, el, k; lk_dn_eval(lk_dn_t, &az, &el); lk_lt_azt = az; lk_lt_elt = el;
    k = (1.08f - lk_lt_sS) / (lk_lt_sd[2] > 0.2f ? lk_lt_sd[2] : 0.2f); lk_dn_sun3[0] *= k; lk_dn_sun3[1] *= k; lk_dn_sun3[2] *= k;
    lk_dn_wk = 1.0f - lk_dn_sunk; lk_dn_win = lk_dn_wk > 0.02f && lk_o_room >= 0 && (OB(OL(0xA0A00) + 8u * (uint32_t)lk_o_room + 4u) & 0x1F) == 0; }   /* v2 lit windows (tileset 0) */   /* the sun strength of lk_lt_sunset for the direction the blocks show */
  if (!lk_lt_sun) return;
  if (lk_dn_upd == 0 && idle) { float taz = lk_lt_azt, tel = lk_lt_elt, daz, del; int smooth = lk_dn_on;
    if (smooth) {   /* LK_DAYNIGHT v5 SMOOTH STEPS (user 2026-11-06: 'Schatten ruckeln Stueck fuer Stueck statt smooth mit dem Sonnenstand zu wandern'): the next direction is where the light will be
         LANDSTALKER_DN_LOOK game hours (0.12 = ~1.6 deg) after the shown one; the crossfade then follows the clock over the whole step (was: a jump + 0.35 s fade every 1.5 deg) */
      static double look = -1.0; double dt; if (look < 0.0) { const char *e = getenv("LANDSTALKER_DN_LOOK"); look = e ? atof(e) : 0.12; if (look < 0.02) look = 0.02; if (look > 1.0) look = 1.0; }
      dt = lk_dn_st0 < 0.0 ? 99.0 : fmod(lk_dn_t - lk_dn_st0 + 48.0, 24.0); if (dt > 12.0) dt -= 24.0;
      if (lk_dn_st0 < 0.0 || dt > 2.0 * look || dt < -look) lk_dn_st0 = lk_dn_t;   /* first step / a jump of the clock: the step starts now (the blocks show their direction until the swap) */
      lk_dn_st1 = fmod(lk_dn_st0 + look, 24.0); lk_dn_dir(lk_dn_st1, &taz, &tel); }
    daz = fabsf(fmodf(taz - lk_lt_azd + 540.0f, 360.0f) - 180.0f); del = fabsf(tel - lk_lt_eld);
    if (smooth ? (daz >= 0.05f || del >= 0.05f) : (daz >= 1.5f || del >= 1.0f)) { float a = taz * 3.14159265f / 180.0f, e = tel * 3.14159265f / 180.0f;   /* a SUN STEP: the next direction, its early exit field; the worker computes the blocks' share */
      lk_dn_naz = taz; lk_dn_nel = tel; lk_lt_sdn[0] = cosf(a) * cosf(e); lk_lt_sdn[1] = sinf(a) * cosf(e); lk_lt_sdn[2] = sinf(e);
      lk_dn_hdok = 0; lk_dn_gen++; lk_dn_upd = 1; lk_dn_mix = 0;   /* (the worker computes lk_lt_hdn first, lk_lt_jobrun) */
      if (lk_lt_sunmov && !lk_dn_get()) { snprintf(m, sizeof m, "SUN DIR %%d HEIGHT %%d", (int)(lk_lt_azt + 0.5f) %% 360, (int)(lk_lt_elt + 0.5f)); lk_osd_say(m); printf("sun: azimuth %%.0f elevation %%.0f (frame %%ld)\n", lk_lt_azt, lk_lt_elt, fr); }
      lk_lt_sunmov = 0;
      if (lk_dn_dbg) printf("daynight: frame %%ld time %%.2f step to az %%.1f el %%.1f\n", fr, lk_dn_t, lk_dn_naz, lk_dn_nel); } }
  if (lk_dn_upd == 1 && idle) { int x, y, pass, cx = (lk_lt_fdiv(lk_lt_umin, 32) + lk_lt_fdiv(lk_lt_umax, 32)) / 2, cy = (lk_lt_fdiv(lk_lt_vmin, 32) + lk_lt_fdiv(lk_lt_vmax, 32)) / 2, left = 0;
    if (lk_lt_umax < lk_lt_umin) { cx = LK_LT_BW / 2; cy = LK_LT_BH / 2; }
    for (pass = 0; pass < 2; pass++) for (y = 0; y < LK_LT_BH; y++) for (x = 0; x < LK_LT_BW; x++) { lk_lt_blk *b = lk_lt_b[y][x]; int near = abs(x - cx) <= 7 && abs(y - cy) <= 5;   /* the view first */
      if (!b || b->sungen == lk_dn_gen || near != (pass == 0)) continue;
      if (lk_lt_jn >= LK_LT_JMAX) { left++; continue; }
      lk_lt_jsun[lk_lt_jn] = b; lk_lt_jbx[lk_lt_jn] = x; lk_lt_jby[lk_lt_jn] = y; lk_lt_jn++; }
    if (!lk_lt_jn && !left) { if (!lk_dn_hdok) lk_lt_hdcalc(lk_lt_sdn, lk_lt_hdn), lk_dn_hdok = 1; lk_dn_upd = 2; } }
  else if (lk_dn_upd == 2) { int rate = lk_dn_fast ? 40 : 12;   /* crossfade ~0.35 s (time-lapse ~0.1 s) */
    if (lk_dn_on && lk_dn_st0 >= 0.0) { double span = fmod(lk_dn_st1 - lk_dn_st0 + 48.0, 24.0), dt = fmod(lk_dn_t - lk_dn_st0 + 48.0, 24.0); int tgt; if (dt > 12.0) dt = 0.0;   /* v5: follow the clock, never faster than the old fade */
      tgt = span > 1e-6 ? (int)(256.0 * dt / span) : 256; if (tgt > 256) tgt = 256; if (tgt > lk_dn_mix) lk_dn_mix = tgt < lk_dn_mix + rate ? tgt : lk_dn_mix + rate; }
    else lk_dn_mix += rate;
    if (lk_dn_mix > 256) lk_dn_mix = 256;
    if (lk_dn_dbg >= 2) printf("daynight: frame %%ld time %%.4f mix %%d\n", fr, lk_dn_t, lk_dn_mix);
    if (lk_dn_mix >= 256 && idle) { int x, y;   /* swap: the blocks show the new direction */
      for (y = 0; y < LK_LT_BH; y++) for (x = 0; x < LK_LT_BW; x++) { lk_lt_blk *b = lk_lt_b[y][x]; if (!b) continue;
        if (b->sungen == lk_dn_gen) memcpy(b->sun, b->sunn, sizeof b->sun); else { free(b); lk_lt_b[y][x] = 0; } }
      memcpy(lk_lt_sd, lk_lt_sdn, sizeof lk_lt_sd); memcpy(lk_lt_hd, lk_lt_hdn, sizeof lk_lt_hd); lk_lt_azd = lk_dn_naz; lk_lt_eld = lk_dn_nel;
      lk_lt_sK = (1.08f - lk_lt_sS) / (lk_lt_sd[2] > 0.2f ? lk_lt_sd[2] : 0.2f); lk_dn_upd = 0; lk_dn_mix = 0; if (lk_dn_on) lk_dn_st0 = lk_dn_st1; } }
  { float m = lk_dn_upd == 2 ? (float)lk_dn_mix * (1.0f / 256.0f) : 0.0f, l; int k;   /* v5: the figures' sun shadows turn with the blended direction */
    for (k = 0; k < 3; k++) lk_lt_sdf[k] = lk_lt_sd[k] + (lk_lt_sdn[k] - lk_lt_sd[k]) * m; l = sqrtf(lk_lt_sdf[0] * lk_lt_sdf[0] + lk_lt_sdf[1] * lk_lt_sdf[1] + lk_lt_sdf[2] * lk_lt_sdf[2]);
    if (l > 1e-6f) for (k = 0; k < 3; k++) lk_lt_sdf[k] /= l; else memcpy(lk_lt_sdf, lk_lt_sd, sizeof lk_lt_sdf); }
}
static float lk_lt_fadecalc(void) {   /* v5: colour sum of the 64 colours the own renderer DRAWS with this frame (lk_o_pix) / of the room's palette words ($FF0080, Mega Drive word 0BBB0GGG0RRR0, x 36)
     (user 2026-11-06 recording rec_20261106_1305, KN cave 171: light shafts drawn over the black pause of a room change; v4 used the RAM palette $FF0ED0, which still held the full colours
     there, and returned 1 when the room palette was empty) */
  int i; long a = 0, t = 0;
  for (i = 0; i < 64; i++) { uint32_t c = (uint32_t)lk_o_colour(112, i); int w0 = UW(0xFF0080 + 2 * i);   /* (the colour really drawn: also the effect palettes lk_o_fxpix of a fade) */ a += (long)((c >> 16) & 255) + (long)((c >> 8) & 255) + (long)(c & 255); t += 36L * (((w0 >> 1) & 7) + ((w0 >> 5) & 7) + ((w0 >> 9) & 7)); }
  if (t < 200) return 0.0f;   /* no room palette (loading): nothing to add */
  if (!(LK_REG(1) & 0x40) || lk_loadroom_on()) return 0.0f;   /* v5: display switched off / a room is being loaded (the black pause of a room change: rec_20261106_1305 frames 3374..3387, 3643..3647) */
  { float k = a >= t ? 1.0f : (float)a / (float)t; return k * k; } }   /* squared: the darkest fade steps (0.13..0.17) leave ~3 %% of the added light; the room itself is still black there */
static void lk_lt_step(void) {   /* once per frame: room / height map change, flicker, figures */
  int idle = lk_lt_jobwait(0);   /* v8 MT: the worker's blocks, if it is done (the main thread never waits for it here) */
  long fr = platform_frame_number(); int x, y, k, j; uint32_t h = 2166136261u; uint32_t a;
  lk_lt_frame = fr;
  lk_lt_lbn = lk_lt_bn; lk_lt_lbms = lk_lt_bms; lk_lt_lpfn = lk_lt_pfn;   /* (the last frame's block counts for LANDSTALKER_LT_TIME=2) */
  if (lk_lt_bn || lk_lt_pfn) { if (lk_lt_dbg == 5 && lk_lt_bms + lk_lt_pms > 1.0) printf("blocks: frame %%ld room %%d %%d blocks %%.1f ms, prefetched %%d %%.1f ms\n", fr - 1, lk_o_room, lk_lt_bn, lk_lt_bms, lk_lt_pfn, lk_lt_pms); lk_lt_bn = lk_lt_pfn = 0; lk_lt_bms = lk_lt_pms = 0.0; }
  if (lk_lt_dbg < 0) { const char *e = getenv("LANDSTALKER_LIGHTING_DBG"); lk_lt_dbg = e ? atoi(e) : 0; }
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) h = (h ^ (uint32_t)UW(0xFFD192 + 148 * y + 2 * x)) * 16777619u;
  { static int lastopt = -1; if (lk_lt_get() != lastopt) { lastopt = lk_lt_get(); lk_lt_room = -2; } }   /* v6: the option changes what is built (flames, sun) */
  if (lk_o_room != lk_lt_room || h != lk_lt_hash) { lk_lt_room = lk_o_room; lk_lt_hash = h; lk_lt_retry = 12; lk_lt_newroom(); }
  else if (lk_lt_nfl == 0 && lk_lt_retry > 0 && (fr & 7) == 0) { lk_lt_retry--; if ((!lk_lt_sun && !lk_lt_aor) || lk_lt_pahash() != lk_lt_pah) lk_lt_newroom(); }   /* v8: room light rooms like the sun: only when the picture changed */
  lk_lt_fadek = lk_lt_fadecalc(); { static int fd = -1; if (fd < 0) { const char *e = getenv("LANDSTALKER_DN_DBG"); fd = e ? atoi(e) : 0; } if (fd == 2 && lk_lt_fadek < 0.995f) printf("fade: frame %%ld room %%d k %%.2f\n", fr, lk_o_room, lk_lt_fadek); }   /* v4 */
  lk_dn_frame(fr, idle);   /* LK_DAYNIGHT v1: the time of day, the sun test aid (L5 + right stick) and smooth sun steps (was: drop every block when the sun moved) */
  lk_lt_on = (lk_lt_nl > 0 || lk_lt_sun || lk_lt_aor) && !lk_hd_n;   /* v8: room light */
  lk_lt_shstep(fr);   /* v8 dust motes */
  if (lk_lt_on) lk_am_step(fr); else if (lk_am_dn) { int jj; for (jj = 0; jj < lk_am_dn; jj++) lk_am_map[lk_am_dl[jj]] = 0; lk_am_dn = 0; }   /* v8 ambient particles */
  { static int tv = -1; static struct timespec tl; static double sum, mx; static int n, over; struct timespec tn;   /* test aid LANDSTALKER_LT_TIME=1: headless frame time (emulation + picture) between two lit frames, per 300 frames */
    if (tv < 0) { const char *e = getenv("LANDSTALKER_LT_TIME"); tv = e ? atoi(e) : 0; if (tv < 0) tv = 0; }   /* 2 = also every frame > 12 ms */
    if (tv) { clock_gettime(CLOCK_MONOTONIC, &tn); if (tl.tv_sec) { double d = (double)(tn.tv_sec - tl.tv_sec) * 1000.0 + (double)(tn.tv_nsec - tl.tv_nsec) / 1e6; if (d < 200.0) { sum += d; n++; if (d > mx) mx = d; if (d > 12.0) over++; if (d > 12.0 && tv >= 2) printf("ltslow: frame %%ld room %%d %%.1f ms (blocks %%d / %%.1f ms, prefetched %%d, sun step %%d)\n", fr, lk_o_room, d, lk_lt_lbn, lk_lt_lbms, lk_lt_lpfn, lk_dn_upd); } }
      tl = tn; if (n >= 300) { printf("lttime: frame %%ld room %%d avg %%.2f ms max %%.1f ms >12ms %%d\n", fr, lk_o_room, sum / n, mx, over); sum = mx = 0.0; n = over = 0; } } }
  if (idle && lk_lt_on && lk_lt_umax >= lk_lt_umin) {   /* v7 PREFETCH, v8 MT: the missing blocks of the ring 2 blocks around the area drawn last frame, nearest first, go to the light worker */
    int bx, by, bx0 = lk_lt_fdiv(lk_lt_umin, 32) - 2, bx1 = lk_lt_fdiv(lk_lt_umax, 32) + 2, by0 = lk_lt_fdiv(lk_lt_vmin, 32) - 2, by1 = lk_lt_fdiv(lk_lt_vmax, 32) + 2, cx = (bx0 + bx1) / 2, cy = (by0 + by1) / 2, r, rm;
    rm = (bx1 - bx0 > by1 - by0 ? bx1 - bx0 : by1 - by0) / 2 + 1;
    for (r = 0; r <= rm && lk_lt_jn < LK_LT_JMAX; r++) for (by = cy - r; by <= cy + r && lk_lt_jn < LK_LT_JMAX; by++) for (bx = cx - r; bx <= cx + r && lk_lt_jn < LK_LT_JMAX; bx++) {
      if ((by != cy - r && by != cy + r && bx != cx - r && bx != cx + r) || bx < bx0 || bx > bx1 || by < by0 || by > by1) continue;   /* the ring at distance r only, inside the area */
      if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH || lk_lt_b[by][bx]) continue;
      lk_lt_jbx[lk_lt_jn] = bx; lk_lt_jby[lk_lt_jn] = by; lk_lt_jsun[lk_lt_jn] = 0; lk_lt_jn++; }
    lk_lt_jobstart(); }
  else if (idle && lk_lt_jn) lk_lt_jobstart();   /* LK_DAYNIGHT v1: sun jobs without a prefetch */
  lk_lt_umin = lk_lt_vmin = 1 << 30; lk_lt_umax = lk_lt_vmax = -(1 << 30); lk_lt_odn = 0;
  for (k = 0; k < lk_lt_nl; k++) lk_lt_flk[k] = lk_lt_l[k].lava == 2 ? (lk_dn_on ? lk_dn_wk * lk_lt_fadek : 0.0f) : lk_lt_l[k].lava ? 1.0f + 0.10f * sinf((float)fr * 0.045f + (float)k * 0.9f)   /* LK_DAYNIGHT v3: window lights burn with the window glow; lava: slow glow */
                                                 : 1.0f + 0.12f * sinf((float)fr * 0.21f + (float)k * 2.1f) + 0.06f * sinf((float)fr * 0.53f + (float)k * 1.3f);
  {   /* v3 sword glow (user 2026-11-03: all swords except the basic one, in the sword's colour): only where the room is lit; stronger while swinging */
    static const float swc[5][3] = { { 0, 0, 0 }, { 1.0f, 0.50f, 0.15f }, { 0.45f, 0.75f, 1.0f }, { 0.95f, 0.85f, 0.35f }, { 0.35f, 1.0f, 0.45f } };   /* Magic, Ice, Thunder, Gaia (lk_sfx_tint) */
    int sw = SB(0xFF114E) & 0xFF, swt = lk_lt_swtest(), act = SB(0xFF542C) & 0x0F, swing = act >= 1 && act <= 4; float want;
    if (swt) sw = swt;
    lk_lt_swon = lk_lt_on && (lk_lt_nfl > 0 || (lk_dn_on && lk_dn_sunk < 0.7f)) && sw >= 1 && sw <= 4;   /* v5: not in rooms lit only by the sun; LK_DAYNIGHT v2: outdoors at dusk / night too (user 2026-11-06: 'nachts sollten die Schwerteffekte auch draussen Licht abgeben') */
    want = swing ? 1.0f : 0.0f;   /* user 2026-11-03: no light while walking, only while swinging */ lk_lt_swk += (want - lk_lt_swk) * (want > lk_lt_swk ? 0.6f : 0.15f);
    if (lk_lt_swk < 0.02f) lk_lt_swon = 0;
    if (lk_lt_swon) { float f = (1.0f + 0.05f * sinf((float)fr * 0.3f)) * (lk_lt_nfl > 0 || !lk_dn_on ? 1.0f : (0.7f - lk_dn_sunk) / 0.7f * 1.3f);   /* (outdoors: grows as the sun fades) */
      lk_lt_sw.x = (float)SW(0xFF5414); lk_lt_sw.y = (float)SW(0xFF5416); lk_lt_sw.z = (float)(int16_t)SW(0xFF5412) + 18.0f;
      lk_lt_sw.r = swc[sw][0] * lk_lt_swk * 0.8f * f; lk_lt_sw.g = swc[sw][1] * lk_lt_swk * 0.8f * f; lk_lt_sw.b = swc[sw][2] * lk_lt_swk * 0.8f * f; lk_lt_sw.lava = 0; }
  }
  lk_lt_nf = 0;
  for (a = 0xFF11DE; a < 0xFF11DE + 40 && lk_lt_nf < 16; a += 2) {
    int o = SW(a), b, ax, ay; if (o & 0x8000) break;
    b = 0xFF5400 + o; ax = SW(b + 0x0E) - 128; ay = SW(b + 0x10) - 128;
    if (ax == -128 && ay == -128) continue;
    lk_lt_f[lk_lt_nf].fx = (float)SW(b + 0x14); lk_lt_f[lk_lt_nf].fy = (float)SW(b + 0x16); lk_lt_f[lk_lt_nf].fz = (float)(int16_t)SW(b + 0x12);
    lk_lt_f[lk_lt_nf].ax = ax; lk_lt_f[lk_lt_nf].ay = ay; lk_lt_f[lk_lt_nf].tag = (o >> 7) + 1;
    lk_lt_f[lk_lt_nf].sun = lk_lt_sun ? lk_lt_sd[2] * lk_lt_sunvis(lk_lt_f[lk_lt_nf].fx, lk_lt_f[lk_lt_nf].fy, lk_lt_f[lk_lt_nf].fz + 20.0f, 0) : lk_lt_key ? lk_lt_keyvis(lk_lt_f[lk_lt_nf].fx, lk_lt_f[lk_lt_nf].fy, lk_lt_f[lk_lt_nf].fz + 20.0f) : 0.0f;
    lk_lt_nf++;
  }
  lk_lt_nfb = 0;
  if (lk_lt_key && lk_lt_sd[2] > 0.05f) { float du = lk_lt_sd[0] - lk_lt_sd[1], dv = (lk_lt_sd[0] + lk_lt_sd[1]) * 0.5f - lk_lt_sd[2], tm = 120.0f / lk_lt_sd[2], ex = -tm * du, ey = -tm * dv;   /* v8: a shadow point lies at most 64 below the foot (t <= (56 + 64) / sd_z) */
    for (j = 0; j < lk_lt_nf; j++) { float *B = lk_lt_fb[lk_lt_nfb]; lk_lt_fbj[lk_lt_nfb++] = j;
      B[0] = (float)lk_lt_f[j].ax - 20.0f; B[2] = (float)lk_lt_f[j].ax + 20.0f; B[1] = (float)lk_lt_f[j].ay - 60.0f; B[3] = (float)lk_lt_f[j].ay + 10.0f;
      B[4] = fabsf(ex) > 0.5f ? 1.0f / ex : 0.0f; B[5] = fabsf(ey) > 0.5f ? 1.0f / ey : 0.0f;
      B[6] = B[0] + (ex < 0.0f ? ex : 0.0f); B[8] = B[2] + (ex > 0.0f ? ex : 0.0f); B[7] = B[1] + (ey < 0.0f ? ey : 0.0f); B[9] = B[3] + (ey > 0.0f ? ey : 0.0f); B[10] = ex; B[11] = ey; } }
  if (lk_lt_key) { int q;   /* v8 (user 2026-11-05: 'die Lichtstrahlen sollten sich auch auf Schatten von Figuren auswirken'): a figure standing in a shaft: its short shadow region along the shaft */
    for (q = 0; q < lk_lt_nsh; q++) { const lk_lt_shaft_t *S = &lk_lt_sh[q]; float du = S->d[0] - S->d[1], dv = (S->d[0] + S->d[1]) * 0.5f - S->d[2], tm = 120.0f / S->d[2], ex = -tm * du, ey = -tm * dv;
      for (j = 0; j < lk_lt_nf && lk_lt_nfb < 512; j++) { const lk_lt_fig *F = &lk_lt_f[j]; float sz = (F->fz - S->z) / S->d[2], axx = S->x + S->d[0] * sz, ayy = S->y + S->d[1] * sz, dd = sqrtf((F->fx - axx) * (F->fx - axx) + (F->fy - ayy) * (F->fy - ayy)); float *B;
        if (dd > S->r * 1.3f + 24.0f) continue;
        B = lk_lt_fb[lk_lt_nfb]; lk_lt_fbj[lk_lt_nfb++] = j;
        B[0] = (float)F->ax - 20.0f; B[2] = (float)F->ax + 20.0f; B[1] = (float)F->ay - 60.0f; B[3] = (float)F->ay + 10.0f;
        B[4] = fabsf(ex) > 0.5f ? 1.0f / ex : 0.0f; B[5] = fabsf(ey) > 0.5f ? 1.0f / ey : 0.0f;
        B[6] = B[0] + (ex < 0.0f ? ex : 0.0f); B[8] = B[2] + (ex > 0.0f ? ex : 0.0f); B[7] = B[1] + (ey < 0.0f ? ey : 0.0f); B[9] = B[3] + (ey > 0.0f ? ey : 0.0f); B[10] = ex; B[11] = ey; } } }

  for (k = 0; k < lk_lt_nl; k++) for (j = 0; j < lk_lt_nf; j++) {
    float dx = lk_lt_l[k].x - lk_lt_f[j].fx, dy = lk_lt_l[k].y - lk_lt_f[j].fy, dz = lk_lt_l[k].z - lk_lt_f[j].fz - 20.0f;
    float hd = sqrtf(dx * dx + dy * dy);
    lk_lt_pair[k][j] = dx * dx + dy * dy + dz * dz < (LK_LT_RAD + 24.0f) * (LK_LT_RAD + 24.0f) && !(lk_lt_l[k].lava == 2 && lk_lt_flk[k] <= 0.004f);   /* (LK_DAYNIGHT v3: an unlit window light casts no figure shadow) */
    if (hd < 1.0f) { lk_lt_pn[k][j][0] = 0.7071f; lk_lt_pn[k][j][1] = 0.7071f; } else { lk_lt_pn[k][j][0] = dx / hd; lk_lt_pn[k][j][1] = dy / hd; }   /* v4 */
  }
  lk_lt_fmall = 0;
  for (k = 0; k < lk_lt_nl; k++) for (j = 0; j < lk_lt_nf; j++) if (lk_lt_pair[k][j]) {   /* v8 SPEED (user 2026-11-05: 'gerne noch die Fackelraeume optimieren'): the screen box a flame's figure shadow can fall into:
       the card corners and the points 62 units further away from the flame (lk_lt_shadowed fades the shadow out at 60 units behind the figure) */
    const lk_lt_light *L = &lk_lt_l[k]; const lk_lt_fig *F = &lk_lt_f[j]; float tx = lk_lt_pn[k][j][1], ty = -lk_lt_pn[k][j][0], x0 = 1e9f, x1 = -1e9f, y0 = 1e9f, y1 = -1e9f, *B; int c, e2;
    for (c = 0; c < 4; c++) { float sc = (c & 1) ? 12.0f : -12.0f, h = (c & 2) ? 58.0f : -8.0f, qx = F->fx + sc * tx, qy = F->fy + sc * ty, qz = F->fz + h, vx = qx - L->x, vy = qy - L->y, vz = qz - L->z, l = sqrtf(vx * vx + vy * vy + vz * vz), m;
      if (l < 1.0f) l = 1.0f; m = 62.0f / l;
      for (e2 = 0; e2 < 2; e2++) { float px = qx + vx * m * (float)e2 - F->fx, py = qy + vy * m * (float)e2 - F->fy, pz = qz + vz * m * (float)e2 - F->fz, sx = (float)F->ax + px - py, sy = (float)F->ay + (px + py) * 0.5f - pz;
        if (sx < x0) x0 = sx; if (sx > x1) x1 = sx; if (sy < y0) y0 = sy; if (sy > y1) y1 = sy; } }
    lk_lt_pbox[k][j][0] = (int)floorf(x0) - 14; lk_lt_pbox[k][j][1] = (int)floorf(y0) - 14; lk_lt_pbox[k][j][2] = (int)ceilf(x1) + 14; lk_lt_pbox[k][j][3] = (int)ceilf(y1) + 14;
    if (lk_lt_nfb >= 512) { lk_lt_fmall = 1; continue; }   /* (too many pairs: every pixel tests every figure, as before) */
    B = lk_lt_fb[lk_lt_nfb]; lk_lt_fbj[lk_lt_nfb++] = j;
    B[0] = B[6] = x0 - 14.0f; B[2] = B[8] = x1 + 14.0f; B[1] = B[7] = y0 - 14.0f; B[3] = B[9] = y1 + 14.0f; B[4] = B[5] = B[10] = B[11] = 0.0f; }
  lk_lt_fmkbuild();
}
static uint16_t lk_lt_fmk[224][LK_OSW]; static int lk_lt_fmky0 = 224, lk_lt_fmky1 = -1;   /* v8 SPEED: per frame a screen mask of the figures whose shadow can reach a pixel (rows fmky0..fmky1 in use) */
static int lk_lt_infb(int x, int y) { int xi = x + lk_wide_e; if (lk_lt_fmall) { lk_lt_fmask = 0xFFFF; return 1; } lk_lt_fmask = (y >= 0 && y < 224 && xi >= 0 && xi < LK_OSW) ? lk_lt_fmk[y][xi] : 0; return lk_lt_fmask != 0; }
static void lk_lt_fmkbuild(void) {   /* rasterise every figure's swept card (B: x0 y0 x1 y1, 1 / ex, 1 / ey, bbox, ex ey in 10 / 11) */
  int j, y;
  for (y = lk_lt_fmky0; y <= lk_lt_fmky1; y++) memset(lk_lt_fmk[y], 0, sizeof lk_lt_fmk[y]);
  lk_lt_fmky0 = 224; lk_lt_fmky1 = -1;
  for (j = 0; j < lk_lt_nfb; j++) { const float *B = lk_lt_fb[j]; int ya = (int)floorf(B[7]), yb = (int)ceilf(B[9]); uint16_t bit = (uint16_t)(1u << lk_lt_fbj[j]);
    if (ya < 0) ya = 0; if (yb > 223) yb = 223;
    for (y = ya; y <= yb; y++) { float s0 = 0.0f, s1 = 1.0f, a, b2, xa, xb; int x, xi0, xi1;
      if (B[5] != 0.0f) { a = ((float)y - B[3]) * B[5]; b2 = ((float)y - B[1]) * B[5]; if (a > b2) { float t = a; a = b2; b2 = t; } if (a > s0) s0 = a; if (b2 < s1) s1 = b2; } else if ((float)y < B[1] || (float)y > B[3]) continue;
      if (s0 > s1) continue;
      xa = B[0] + (B[10] < 0.0f ? s1 : s0) * B[10]; xb = B[2] + (B[10] < 0.0f ? s0 : s1) * B[10];
      xi0 = (int)floorf(xa) + lk_wide_e; xi1 = (int)ceilf(xb) + lk_wide_e; if (xi0 < 0) xi0 = 0; if (xi1 > LK_OSW - 1) xi1 = LK_OSW - 1;
      for (x = xi0; x <= xi1; x++) lk_lt_fmk[y][x] |= bit;
      if (y < lk_lt_fmky0) lk_lt_fmky0 = y; if (y > lk_lt_fmky1) lk_lt_fmky1 = y; } } }
static int lk_lt_figat(int x, int y) {   /* figure whose box holds screen pixel (x, y) (x = 0..319 + margins), -1 none */
  int j; for (j = 0; j < lk_lt_nf; j++) { int dx = x - lk_lt_f[j].ax, dy = lk_lt_f[j].ay - y; if (dx >= -16 && dx <= 16 && dy >= -6 && dy <= 56) return j; } return -1;
}
static float lk_lt_shadowed(float px, float py, float pz, const lk_lt_light *L, int k) {   /* the ray scenery pixel -> light crosses a figure's silhouette: 0..1 (v7: only the figure's OWN sprite pixels, fading with the distance pixel -> figure) */
  int j; for (j = 0; j < lk_lt_nf; j++) {
    const lk_lt_fig *F = &lk_lt_f[j]; float den, num, t, qx, qy, qz, dx, hh, nx, ny, tx, ty; int mx, my;
    if (!lk_lt_pair[k][j] || !(lk_lt_fmask & (1 << j))) continue;   /* v8 SPEED: lk_lt_fmask from lk_lt_infb of this pixel */
    { const int *pb = lk_lt_pbox[k][j]; if (lk_lt_curx < pb[0] || lk_lt_curx > pb[2] || lk_lt_cury < pb[1] || lk_lt_cury > pb[3]) continue; }   /* v8 SPEED: outside this flame's shadow box of the figure */
    nx = lk_lt_pn[k][j][0]; ny = lk_lt_pn[k][j][1];   /* v4: card through the foot point, facing the light */
    den = nx * (L->x - px) + ny * (L->y - py); num = nx * (F->fx - px) + ny * (F->fy - py);
    if (fabsf(den) < 1e-4f) continue;
    t = num / den; if (t < 0.02f || t > 0.98f) continue;
    qx = px + t * (L->x - px); qy = py + t * (L->y - py); qz = pz + t * (L->z - pz);
    tx = ny; ty = -nx; if (tx - ty < 0.0f) { tx = -tx; ty = -ty; }   /* along the card, oriented like the screen's +x (world (1, -1)): sprite column = world offset * 1.414 as on the camera card */
    dx = 1.4142f * (tx * (qx - F->fx) + ty * (qy - F->fy)); hh = qz - F->fz;
    if (dx < -16.0f || dx > 16.0f || hh < -6.0f || hh > 56.0f) continue;
    mx = F->ax + (int)lrintf(dx) + lk_wide_e; my = F->ay - (int)lrintf(hh);
    { int hit = 0, a2, b2;   /* SOFT EDGE (user 2026-11-05: 'ausgefranzt' at the knights' shadows): the share of the 3 x 3 sprite pixels around the hit, not one pixel */
      for (b2 = -1; b2 <= 1; b2++) for (a2 = -1; a2 <= 1; a2++) { int ux = mx + a2, uy = my + b2;
        if (ux >= 0 && ux < LK_OSW && uy >= 0 && uy < 224 && (lk_o_spr[uy][ux] & 0x200) && lk_lt_spre[uy][ux] == F->tag) hit++; }   /* v7: the books on the church shelf are figures too: their pixels made Nigel's shadow a block (user rec_20261103_2149) */
      if (hit) { float ex = L->x - px, ey = L->y - py, ez = L->z - pz, d = t * sqrtf(ex * ex + ey * ey + ez * ez), w = (60.0f - d) * (1.0f / 40.0f);   /* v7: a candle close to the head stretched the shadow far and jagged: fade from 20 to 60 units */
        w = w >= 1.0f ? 1.0f : w > 0.0f ? w : 0.0f; return w * (float)hit / 9.0f; } }
  }
  return 0.0f;
}
static int lk_lt_figdir(const float *sd, float px, float py, float pz) {   /* v5: the way scenery pixel -> a far light in direction sd crosses a figure (a card through its foot point, facing the light); v8: any direction (sun, key light, shaft) */
  int j; float hx = sd[0], hy = sd[1], hl = sqrtf(hx * hx + hy * hy), nx, ny, tx, ty, den;
  if (hl < 1e-3f) return 0;
  nx = hx / hl; ny = hy / hl; den = nx * sd[0] + ny * sd[1]; tx = ny; ty = -nx; if (tx - ty < 0.0f) { tx = -tx; ty = -ty; }
  for (j = 0; j < lk_lt_nf; j++) {
    const lk_lt_fig *F = &lk_lt_f[j]; float t, qx, qy, qz, dx, hh; int mx, my;
    if (lk_lt_key && !(lk_lt_fmask & (1 << j))) continue;   /* v8 SPEED: only the figures whose shadow region holds this pixel (lk_lt_infb) */
    if (fabsf(F->fx - px) > 110.0f || fabsf(F->fy - py) > 110.0f || pz > F->fz + 56.0f) continue;
    t = (nx * (F->fx - px) + ny * (F->fy - py)) / den; if (t <= 0.5f) continue;
    qx = px + t * sd[0]; qy = py + t * sd[1]; qz = pz + t * sd[2];
    dx = 1.4142f * (tx * (qx - F->fx) + ty * (qy - F->fy)); hh = qz - F->fz;
    if (dx < -16.0f || dx > 16.0f || hh < -6.0f || hh > 56.0f) continue;
    mx = F->ax + (int)lrintf(dx) + lk_wide_e; my = F->ay - (int)lrintf(hh);
    if (mx >= 0 && mx < LK_OSW && my >= 0 && my < 224 && (lk_o_spr[my][mx] & 0x200) && lk_lt_spre[my][mx] == F->tag) return 1;   /* v7: own pixels only */
  }
  return 0;
}
static int lk_lt_figsun(float px, float py, float pz) { return lk_lt_figdir(lk_lt_sun && lk_dn_on && lk_lt_sdf[2] > 0.0f ? lk_lt_sdf : lk_lt_sd, px, py, pz); }   /* LK_DAYNIGHT v5: blended direction during a step */
static int lk_lt_linebegin(void) { if (!lk_lt_get()) return 0; if (lk_lt_frame != platform_frame_number()) lk_lt_step(); return lk_lt_on; }
static float lk_lt_amb = -1.0f;   /* indoor base light (unlit share of the original brightness): 0.85 (user 2026-11-05: castle too dark, picked 85 %% of 55 / 70 / 85; was 0.55); test aid LANDSTALKER_LT_AMB=0.70 */
static int lk_lt_bm, lk_lt_bz;   /* v8: beam glow + surface height of the current pixel (set by the key light branch) */
static int lk_lt_voidglow(int U, int V, int col) {   /* v8 shafts over pixels without geometry (the black void below a walkway, painted pixels the view ray missed): beam + motes only */
  const lk_lt_blk *b; int i, d, r, g, bl; float gl; uint32_t c = (uint32_t)col;
  if ((!lk_lt_nsh && !lk_am_dn) || !(b = lk_lt_block(lk_lt_fdiv(U, 32), lk_lt_fdiv(V, 32)))) return col;
  i = ((V & 31) << 5) | (U & 31);   /* (the view ray of a backdrop pixel often meets a pit wall far below: its beam is integrated from there, fine) */
  if (lk_lt_dbg == 10) return (int)(0xFF000000u | ((uint32_t)b->beam[i] << 16) | 0x30);   /* test aid: dark blue = void pixel reached */
  d = lk_lt_nsh ? lk_lt_dmap[((V & 511) << 9) | (U & 511)] : 0;
  gl = lk_lt_nsh ? ((float)b->beam[i] * 0.38f + (float)d * 0.50f) * lk_lt_fadek : 0.0f;   /* (v4: fades with the palette) */
  r = (int)((c >> 16) & 255) + (int)(gl * lk_lt_sh[0].cr); g = (int)((c >> 8) & 255) + (int)(gl * lk_lt_sh[0].cg); bl = (int)(c & 255) + (int)(gl * lk_lt_sh[0].cb);
  if (lk_am_dn && !(lk_am_map[((V & 511) << 9) | (U & 511)] & 0x80000000u)) lk_am_mix(U, V, -32768, -32768, &r, &g, &bl);   /* v8 ambient particles over the void; v9: only drops / splashes there, glowing ones (sparks, embers, fireflies: additive) not (user: particles outside the room) */
  if (r > 255) r = 255; if (g > 255) g = 255; if (bl > 255) bl = 255;
  return (int)((c & 0xFF000000u) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)bl); }
static int lk_lt_pix(int x, int line, int U, int V, int sp, int col) {   /* one composed map pixel; sp = winning sprite pixel or 0 */
  float ar, ag, ab, sr = 0, sg = 0, sb = 0, tl = 0, tb = 0; int k, j = -1;
  lk_lt_bm = 0; lk_lt_bz = -32768;
  if (lk_lt_amb < 0.0f) { const char *e = getenv("LANDSTALKER_LT_AMB"); lk_lt_amb = e ? (float)atof(e) : 0.85f; if (lk_lt_amb < 0.0f || lk_lt_amb > 1.5f) lk_lt_amb = 0.85f; }
  ar = lk_lt_amb * 0.93f; ag = lk_lt_amb * 0.96f; ab = lk_lt_amb * 1.06f;
  if (!lk_lt_nl && !lk_lt_sun) ar = ag = ab = 1.0f;   /* v8: a room without flames keeps the original brightness (only the corner shadows) */
  if (U < lk_lt_umin) lk_lt_umin = U; if (U > lk_lt_umax) lk_lt_umax = U; if (V < lk_lt_vmin) lk_lt_vmin = V; if (V > lk_lt_vmax) lk_lt_vmax = V;   /* v7: area for the prefetch */
  if ((sp & 0x200) && (j = lk_lt_figat(x, line)) >= 0) {   /* a figure pixel: lit at its cut-out position, facing the camera */
    const lk_lt_fig *F = &lk_lt_f[j]; float dx = (float)(x - F->ax), px = F->fx + dx * 0.5f, py = F->fy - dx * 0.5f, pz = F->fz + (float)(F->ay - line);
    for (k = 0; k < lk_lt_nl; k++) { if (lk_lt_l[k].lava == 2 && lk_lt_flk[k] <= 0.004f) continue; float t = lk_lt_term(px, py, pz, 0.7071f, 0.7071f, 0.0f, &lk_lt_l[k], 0) * lk_lt_flk[k]; sr += t * lk_lt_l[k].r; sg += t * lk_lt_l[k].g; sb += t * lk_lt_l[k].b; }
    if (lk_lt_swon) { float t = lk_lt_term(px, py, pz, 0.7071f, 0.7071f, 0.0f, &lk_lt_sw, 0) * 0.5f; sr += t * lk_lt_sw.r; sg += t * lk_lt_sw.g; sb += t * lk_lt_sw.b; }   /* v3 */
    if (lk_lt_sun && lk_dn_on) { float u = F->sun; ar = lk_dn_amb3[0] + lk_dn_sun3[0] * u; ag = lk_dn_amb3[1] + lk_dn_sun3[1] * u; ab = lk_dn_amb3[2] + lk_dn_sun3[2] * u; }   /* LK_DAYNIGHT v1 */
    else if (lk_lt_sun) { float u = F->sun; ar = lk_lt_sS * 0.95f + lk_lt_sK * u; ag = lk_lt_sS * 0.98f + lk_lt_sK * u * 0.97f; ab = lk_lt_sS * 1.06f + lk_lt_sK * u * 0.90f; }   /* v5 */
    else if (lk_lt_key) { float u = F->sun; ar = lk_lt_kA * 0.97f + lk_lt_kK * u * 1.04f; ag = lk_lt_kA * 0.99f + lk_lt_kK * u; ab = lk_lt_kA * 1.05f + lk_lt_kK * u * 0.92f; }   /* v8 */
  } else {
    const lk_lt_blk *b = lk_lt_block(lk_lt_fdiv(U, 32), lk_lt_fdiv(V, 32)); int i;
    if (lk_lt_dbg == 4) { int pa = 0, pra = 0, pb = 0, prb = 0, ia = lk_o_fetch(lk_o_pa, U, V, &pa, &pra, 0), ib = lk_o_fetch(lk_o_pb, U, V, &pb, &prb, 0); uint32_t c = (uint32_t)col;   /* v5 test aid: priority pixels (layer A magenta, B cyan) */
      if (ia) return (int)(pra ? 0xFFE040E0u : 0xFF902090u); if (ib) return (int)(prb ? 0xFF40E0E0u : (0xFF000000u | ((c >> 2) & 0x3F3F3F))); return (int)(0xFF000000u | ((c >> 2) & 0x3F3F3F)); }
    if (!b && !lk_lt_sun && lk_lt_odcap == 0) {   /* v9: indoors, a block the workers have not finished yet: the room's base light (flames / shafts come with the block a frame or two later) */
      uint32_t c = (uint32_t)col; float fr, fg, fb; int r, g, bl;
      if (lk_lt_key) { fr = lk_lt_kA * 0.97f + lk_lt_kK * 0.6f * 1.04f; fg = lk_lt_kA * 0.99f + lk_lt_kK * 0.6f; fb = lk_lt_kA * 1.05f + lk_lt_kK * 0.6f * 0.92f; }
      else if (lk_lt_nl) { fr = ar; fg = ag; fb = ab; }
      else return col;
      r = (int)((float)((c >> 16) & 255) * fr); g = (int)((float)((c >> 8) & 255) * fg); bl = (int)((float)(c & 255) * fb);
      if (r > 255) r = 255; if (g > 255) g = 255; if (bl > 255) bl = 255;
      return (int)((c & 0xFF000000u) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)bl); }
    if (!b && lk_lt_sun && !lk_dn_on && lk_lt_odcap == 0) {   /* v9: outdoors without the cycle: sky light + sun, unshaded */
      uint32_t c = (uint32_t)col; float fr = lk_lt_sS * 0.95f + lk_lt_sK, fg = lk_lt_sS * 0.98f + lk_lt_sK * 0.97f, fb = lk_lt_sS * 1.06f + lk_lt_sK * 0.90f; int r, g, bl;
      if (fr > 2.4f) fr = 2.4f; if (fg > 2.4f) fg = 2.4f; if (fb > 2.4f) fb = 2.4f;
      r = (int)((float)((c >> 16) & 255) * fr); g = (int)((float)((c >> 8) & 255) * fg); bl = (int)((float)(c & 255) * fb);
      if (r > 255) r = 255; if (g > 255) g = 255; if (bl > 255) bl = 255;
      return (int)((c & 0xFF000000u) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)bl); }
    if (!b && lk_lt_sun && lk_dn_on) {   /* LK_DAYNIGHT v5 (user 2026-11-06: 'Mercator Raumwechsel nachts: das Bild flackert kurz'): a block not computed yet (the first frames of a room) got the ORIGINAL colour = daylight;
         at night it flashed bright until the worker had it.  Now: the time of day's sky light + its sun as if unshaded (no shadows yet) */
      uint32_t c = (uint32_t)col; float fr = lk_dn_amb3[0] + lk_dn_sun3[0], fg = lk_dn_amb3[1] + lk_dn_sun3[1], fb = lk_dn_amb3[2] + lk_dn_sun3[2]; int r, g, bl;
      if (fr > 2.4f) fr = 2.4f; if (fg > 2.4f) fg = 2.4f; if (fb > 2.4f) fb = 2.4f;
      r = (int)((float)((c >> 16) & 255) * fr); g = (int)((float)((c >> 8) & 255) * fg); bl = (int)((float)(c & 255) * fb);
      if (r > 255) r = 255; if (g > 255) g = 255; if (bl > 255) bl = 255;
      return (int)((c & 0xFF000000u) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)bl); }
    if (!b) return col;
    i = ((V & 31) << 5) | (U & 31);
    if (lk_lt_dbg == 2) { static const int dc[4] = { 0x000000, 0x6E6E8C, 0xC8503C, 0x3CAA50 }; return (int)(0xFF000000u | (uint32_t)dc[b->face[i] & 3]); }
    if (lk_lt_dbg == 7) { float px, py; int sx, sy, q = 0; uint32_t c = (uint32_t)col, h; lk_lt_pos(U, V, b->z[i], &px, &py); sx = (int)floorf(px / 4.0f); sy = (int)floorf(py / 4.0f);   /* light proxies over the picture */
      if (b->face[i] && sx >= 0 && sy >= 0 && sx < LK_LT_FN && sy < LK_LT_FN) q = lk_lt_fp[sy][sx];
      if (!q) return (int)(0xFF000000u | ((c >> 1) & 0x7F7F7F));
      h = (uint32_t)q * 2654435761u; { int f = b->face[i] == 1 ? 255 : b->face[i] == 3 ? 200 : 150;
        return (int)(0xFF000000u | ((uint32_t)((((h >> 8) & 255) | 64) * f / 255 / 2 + ((c >> 17) & 127)) << 16) | ((uint32_t)((((h >> 16) & 255) | 64) * f / 255 / 2 + ((c >> 9) & 127)) << 8) | (uint32_t)((((h >> 24) & 255) | 64) * f / 255 / 2 + ((c >> 1) & 127))); } }
    if (lk_lt_dbg == 6 && b->face[i]) { float px, py; int cx, cy, o, g = b->sun[i]; uint32_t h; lk_lt_pos(U, V, b->z[i], &px, &py); cx = (int)floorf(px / 16.0f); cy = (int)floorf(py / 16.0f);   /* v7 test aid: sun share (grey) + outdoor object of the hit cell (colour) */
      o = (cx >= 0 && cy >= 0 && cx < 74 && cy < 74) ? lk_lt_obj[cy][cx] : 0; if (!o) return (int)(0xFF000000u | (uint32_t)(g * 0x010101));
      h = (uint32_t)o * 2654435761u; return (int)(0xFF000000u | ((uint32_t)((g + (int)((h >> 8) & 127)) / 2) << 16) | ((uint32_t)((g + (int)((h >> 16) & 127)) / 2) << 8) | (uint32_t)((g + (int)((h >> 24) & 127)) / 2)); }
    if (!b->face[i]) return lk_lt_voidglow(U, V, col);   /* v8: shafts also where the view ray found nothing */
    lk_lt_bz = b->z[i];   /* v8: surface height for the motes / particles (all branches) */
    if (lk_lt_key && !lk_lt_nl && !lk_lt_dbg && !(lk_lt_nfb && (b->sun[i] || b->pool[i]) && lk_lt_infb(x, line))) {   /* v8 SPEED: the finished static light (no figure shadow can reach this pixel) */
      uint32_t c = (uint32_t)col; int r = (int)((((c >> 16) & 255) * b->km[0][i] + 128) >> 8), g = (int)((((c >> 8) & 255) * b->km[1][i] + 128) >> 8), bl = (int)(((c & 255) * b->km[2][i] + 128) >> 8);
      if (lk_lt_nsh) { int q = ((V & 511) << 9) | (U & 511), d = lk_lt_dmap[q]; float gl = (float)b->beam[i] * 0.38f;
        if (d && lk_lt_dmz[q] >= b->z[i] - 2) gl += (float)d * 0.50f;
        gl *= lk_lt_fadek; if (gl > 0.0f) { r += (int)(gl * lk_lt_sh[0].cr); g += (int)(gl * lk_lt_sh[0].cg); bl += (int)(gl * lk_lt_sh[0].cb); } }
      if (lk_am_dn) lk_am_mix(U, V, b->z[i], -32768, &r, &g, &bl);   /* v8 ambient particles */
      if (r > 255) r = 255; if (g > 255) g = 255; if (bl > 255) bl = 255;
      return (int)((c & 0xFF000000u) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)bl); }
    if (lk_lt_dbg == 10) return (int)(0xFF000000u | ((uint32_t)b->beam[i] << 16) | ((uint32_t)b->pool[i] << 8) | (uint32_t)(b->sun[i] >> 2));   /* v8 test aid: shafts (red beam, green pool, blue key light) */
    if (lk_lt_dbg == 8) { int g = b->ao[i]; return (int)(0xFF000000u | (uint32_t)(g * 0x010101)); }   /* v8 test aid: room light share as grey */
    if (lk_lt_sun) { float u = (float)b->sun[i] * (1.0f / 255.0f);   /* v5: sky light (cool) + sun (warm), figures' shadows take the sun */
      if (lk_dn_mix && b->sungen == lk_dn_gen) u += ((float)b->sunn[i] * (1.0f / 255.0f) - u) * (float)lk_dn_mix * (1.0f / 256.0f);   /* LK_DAYNIGHT v1: crossfade to the next sun direction */
      if (u > 0.0f && lk_lt_nf) { float px, py; lk_lt_pos(U, V, b->z[i], &px, &py); if (lk_lt_figsun(px, py, (float)b->z[i])) u = 0.0f; }
      if (lk_dn_on) { ar = lk_dn_amb3[0] + lk_dn_sun3[0] * u; ag = lk_dn_amb3[1] + lk_dn_sun3[1] * u; ab = lk_dn_amb3[2] + lk_dn_sun3[2] * u; }   /* LK_DAYNIGHT v1 */
      else { ar = lk_lt_sS * 0.95f + lk_lt_sK * u; ag = lk_lt_sS * 0.98f + lk_lt_sK * u * 0.97f; ab = lk_lt_sS * 1.06f + lk_lt_sK * u * 0.90f; } }
    else if (lk_lt_key) { float u = (float)b->sun[i] * (1.0f / 255.0f);   /* v8 key light: shadow level + slightly warm light, figures cast shadows */
      if (u > 0.0f && lk_lt_nfb && lk_lt_infb(x, line)) { float px, py; lk_lt_pos(U, V, b->z[i], &px, &py); if (lk_lt_figsun(px, py, (float)b->z[i])) u *= 0.45f; }   /* v8 SPEED: only inside a figure's shadow box */   /* a figure's shadow under the wide light from above is light (its edge is hard: keep the step small) */
      ar = lk_lt_kA * 0.97f + lk_lt_kK * u * 1.04f; ag = lk_lt_kA * 0.99f + lk_lt_kK * u; ab = lk_lt_kA * 1.05f + lk_lt_kK * u * 0.92f;
      if (b->pool[i]) { float p = (float)b->pool[i] * (1.0f / 255.0f) * 0.65f; int q;
        if (lk_lt_nfb && lk_lt_nf && lk_lt_infb(x, line)) { float px, py, sv; lk_lt_pos(U, V, b->z[i], &px, &py);   /* v8: a figure in the shaft shades the pool */
          float sh = 0.0f; int jf;   /* nearly vertical light: a soft oval on the ground around the feet, pushed a little away from the light (a card shadow would hide behind the sprite itself: 11 pixels, measured) */
          for (q = 0; q < lk_lt_nsh; q++) { const lk_lt_shaft_t *S = &lk_lt_sh[q]; float hl = sqrtf(S->d[0] * S->d[0] + S->d[1] * S->d[1]), axh = hl > 1e-3f ? -S->d[0] / hl : 0.0f, ayh = hl > 1e-3f ? -S->d[1] / hl : 0.0f, off = 24.0f * hl / S->d[2], L = off + 10.0f, Wd = 10.0f;
            if (lk_lt_shdist(S, px, py, (float)b->z[i], &sv) > S->r * 1.3f) continue;
            for (jf = 0; jf < lk_lt_nf; jf++) { const lk_lt_fig *F = &lk_lt_f[jf]; float vx, vy, al, ac, e, f;
              if (!(lk_lt_fmask & (1 << jf)) || fabsf((float)b->z[i] - F->fz) > 8.0f) continue;
              vx = px - (F->fx + axh * off); vy = py - (F->fy + ayh * off); al = vx * axh + vy * ayh; ac = -vx * ayh + vy * axh; e = (al * al) / (L * L) + (ac * ac) / (Wd * Wd);
              if (e >= 1.0f) continue; f = (1.0f - e) * 1.6f; if (f > 1.0f) f = 1.0f; if (f > sh) sh = f; } }
          if (sh > 0.0f) { float cd = 1.0f - 0.30f * sh; p *= 1.0f - 0.85f * sh; ar *= cd; ag *= cd; ab *= cd;   /* + a soft contact darkening, so it reads under the pale shaft (user 2026-11-05: 'fahles Licht') */
            if (getenv("LANDSTALKER_LT_SHFIGDBG")) return (int)(0xFF000000u | ((uint32_t)(int)(sh * 255.0f) << 16) | 0xFF); } }
        ar += p * lk_lt_sh[0].cr; ag += p * lk_lt_sh[0].cg; ab += p * lk_lt_sh[0].cb; }   /* v8 shaft: light pool (with the key light's shadows) */
      lk_lt_bm = b->beam[i]; lk_lt_bz = b->z[i]; }
    { static int px0 = -2, py0, px1; static long pfr = 1260; if (px0 == -2) { const char *e = getenv("LANDSTALKER_LIGHTING_PROBE"); px0 = -1; if (e && sscanf(e, "%%d,%%d,%%d,%%ld", &px0, &py0, &px1, &pfr) < 2) px0 = -1; if (px1 < px0) px1 = px0; }   /* test aid: one picture pixel's geometry + light terms */
      if (x >= px0 && x <= px1 && (x - px0) %% 4 == 0 && line == py0 && platform_frame_number() == pfr) { float qx, qy; lk_lt_pos(U, V, b->z[i], &qx, &qy); printf("probe: x %%d U %%d V %%d face %%d z %%d pos (%%.0f, %%.0f) sun %%d nl %%d:", x, U, V, b->face[i], b->z[i], qx, qy, b->sun[i], b->nl);
        for (k = 0; k < b->nl; k++) { const lk_lt_light *L = &lk_lt_l[b->li[k]]; printf(" L%%d t%%d n%%.2f", b->li[k], b->term[k][i], lk_lt_term(qx, qy, (float)b->z[i], b->face[i] == 2, b->face[i] == 3, b->face[i] == 1, L, 0)); } printf("\n"); } }
    int fm = lk_lt_nfb && lk_lt_nf ? lk_lt_infb(x, line) : 0;   /* v8 SPEED: figures whose flame shadow can reach this pixel (lk_lt_fmask) */
    lk_lt_curx = x; lk_lt_cury = line;
    for (k = 0; k < b->nl; k++) {
      float t = (float)b->term[k][i] * (1.0f / 255.0f); const lk_lt_light *L;
      if (t <= 0.0f) continue;
      L = &lk_lt_l[b->li[k]];
      if (L->lava == 2) { if (lk_lt_flk[b->li[k]] <= 0.004f) continue; t *= lk_lt_flk[b->li[k]] > 1.0f ? 1.0f : lk_lt_flk[b->li[k]]; }   /* LK_DAYNIGHT v3: window light by day = nothing; its shadow share follows its strength */
      if (fm && !(L->lava == 2 && b->face[i] != 1)) {   /* v4: a window light (from inside the house) throws figure shadows onto the floor only (user 2026-11-06: Nigel's shadow on the house wall makes no sense) */ float px, py; lk_lt_pos(U, V, b->z[i], &px, &py); { static int st[LK_LT_ML], st2[LK_LT_ML]; static float sw2[LK_LT_ML]; int li = b->li[k], key = (line << 11) | (x & 2047); float w;   /* v8 SPEED: one test per 2 pixels of a line (even x computes, odd x takes its left neighbour; the shadow edge is soft anyway) */
        static int half = -1; if (half < 0) { const char *e = getenv("LANDSTALKER_LT_SHHALF"); half = e ? atoi(e) : 1; }   /* test aid: 0 = every pixel */
        if (half && (x & 1) && st[li] == key - 1 && st2[li] == lk_lt_frame) w = sw2[li]; else { w = lk_lt_shadowed(px, py, (float)b->z[i], L, li); st[li] = key; st2[li] = (int)lk_lt_frame; sw2[li] = w; }
        if (w >= 1.0f) { tb += t; continue; } if (w > 0.0f) { tb += t * w; t *= 1.0f - w; } } }
      tl += t; if (L->lava != 2) t *= lk_lt_flk[b->li[k]]; sr += t * L->r; sg += t * L->g; sb += t * L->b;
    }
    if (b->ao[i] < 255) { float a = (float)b->ao[i] * (1.0f / 255.0f); ar *= a; ag *= a; ab *= a; }   /* v8 room light: corner shadows take the base light only */
    if (tb > 0.0f) { float d = 1.0f - 0.5f * tb / (tb + tl + 0.05f); ar *= d; ag *= d; ab *= d; }   /* v4: a figure's shadow also takes part of the base light (share of the blocked light), so the silhouette reads (user 2026-11-03) */
    if (lk_lt_swon) { int f = b->face[i]; float px, py, t; lk_lt_pos(U, V, b->z[i], &px, &py);   /* v3 sword glow */
      t = lk_lt_term(px, py, (float)b->z[i], f == 2 ? 1.0f : 0.0f, f == 3 ? 1.0f : 0.0f, f == 1 ? 1.0f : 0.0f, &lk_lt_sw, 0); sr += t * lk_lt_sw.r; sg += t * lk_lt_sw.g; sb += t * lk_lt_sw.b; }
  }
  { uint32_t c = (uint32_t)col; float fr = ar + 2.2f * sr, fg = ag + 2.2f * sg, fb = ab + 2.2f * sb; int r, g, bl;
    if (fr > 2.4f) fr = 2.4f; if (fg > 2.4f) fg = 2.4f; if (fb > 2.4f) fb = 2.4f;
    r = (int)((float)((c >> 16) & 255) * fr); g = (int)((float)((c >> 8) & 255) * fg); bl = (int)((float)(c & 255) * fb);
    if (lk_lt_nsh) { int d = lk_lt_dmap[((V & 511) << 9) | (U & 511)]; float gl = (float)lk_lt_bm * 0.38f;   /* user 2026-11-05: the beam stands still (no shimmer), only the motes move */   /* v8 shafts: beam glow (pale, user 2026-11-05) (slow shimmer) + dust motes in front of the surface */
      if (d && (lk_lt_bz == -32768 || lk_lt_dmz[((V & 511) << 9) | (U & 511)] >= lk_lt_bz - 2)) gl += (float)d * 0.50f;
      gl *= lk_lt_fadek; if (gl > 0.0f) { r += (int)(gl * lk_lt_sh[0].cr); g += (int)(gl * lk_lt_sh[0].cg); bl += (int)(gl * lk_lt_sh[0].cb); } }
    if (lk_am_dn) lk_am_mix(U, V, lk_lt_bz, j >= 0 ? (int)(lk_lt_f[j].fx + lk_lt_f[j].fy) : -32768, &r, &g, &bl);   /* v8 ambient particles (a figure pixel: depth test against the figure) */
    if (r > 255) r = 255; if (g > 255) g = 255; if (bl > 255) bl = 255;
    return (int)((c & 0xFF000000u) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)bl); }
}

''' % VER
MODULE = MODULE.replace("/*LK_LT_CORR*/", corr_table() + cat_table())

a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
rep(a, MODULE + a)
# v7: entity of every sprite pixel (figure shadows take only their own pixels); marked /*LK_LT_ENT*/
rep("static uint8 lk_ss_nig[224][LK_OSW]; static int lk_ss_cur;", "static uint8 lk_lt_spre[224][LK_OSW]; static int lk_lt_ecur; /*LK_LT_ENT*/\nstatic uint8 lk_ss_nig[224][LK_OSW]; static int lk_ss_cur;")
assert s.count("lk_ss_nig[Y][X] = (uint8)lk_ss_cur;") == 3
s = s.replace("lk_ss_nig[Y][X] = (uint8)lk_ss_cur;", "lk_ss_nig[Y][X] = (uint8)lk_ss_cur; lk_lt_spre[Y][X] = (uint8)lk_lt_ecur; /*LK_LT_ENT*/")
rep("    lk_ss_cur = offs[k] == 0;   /* LK_SUBPIX v3: Nigel's pieces (also the sprint pose canvas) */\n", "    lk_ss_cur = offs[k] == 0;   /* LK_SUBPIX v3: Nigel's pieces (also the sprint pose canvas) */\n    lk_lt_ecur = (offs[k] >> 7) + 1; /*LK_LT_ENT*/\n")
rep("    lk_ss_cur = 0;\n    if (draw && lk_o_exon)", "    lk_ss_cur = 0; lk_lt_ecur = 0; /*LK_LT_ENT*/\n    if (draw && lk_o_exon)")
rep("int lk_sfx_ln = lk_sfx_linebegin(line);   /* LK_SWORDFX v1 */\n",
    "int lk_sfx_ln = lk_sfx_linebegin(line);   /* LK_SWORDFX v1 */\n    int lk_lt_ln = lk_lt_linebegin();   /* %s */\n" % VER)
rep("      if (lk_sfx_ln && !black && src != 4) col = lk_sfx_pix(line, i, src == 1 ? sp : 0, col);   /* LK_SWORDFX v1 */\n",
    "      if (lk_lt_ln && !black && (src == 1 || src == 2 || src == 3)) col = lk_lt_pix(x, line, ubase + x - lk_sm_sxn, vbase - lk_sm_syn, src == 1 ? sp : 0, col);   /* %s */\n" % VER +
    "      else if (lk_lt_ln && !black && (src == 0 || src == 6 || src == 7)) col = lk_lt_voidglow(ubase + x - lk_sm_sxn, vbase - lk_sm_syn, col);   /* LK_LIGHTS v8 shafts over the void */\n" +
    "      if (lk_lt_ln && lk_dn_win && !black && (src == 2 || src == 3)) col = lk_dn_winpix(src == 2 ? &afi : &bfi, pick, col);   /* LK_DAYNIGHT v3 lit windows */\n" +
    "      if (lk_sfx_ln && !black && src != 4) col = lk_sfx_pix(line, i, src == 1 ? sp : 0, col);   /* LK_SWORDFX v1 */\n")
open(p, "w").write(s)
print("vdp_render.c patched:", VER)

# ---- src/input.c: SUN TEST AID (user 2026-11-04): hold pad L5 (or R5; SDL paddle 3 / 4, the lower back buttons) + right stick: left / right turns the sun, up / down raises it
pi = os.path.join(root, "src/input.c")
t = open(pi).read()
if "lk_lt_sun_nudge" not in t:
    a = "        if (d[LK_BCOORD] && !prev[LK_BCOORD]) platform_display_toggle_coords();\n"
    assert t.count(a) == 1, "input.c: coordinate line changed"
    t = t.replace(a, a + "        { extern void lk_lt_sun_nudge(float daz, float del);   /* SUN TEST AID (tools/patch_lights.py) */\n"
        "          if (lk_pad_code_down(pads, LKP(SDL_CONTROLLER_BUTTON_PADDLE3)) || lk_pad_code_down(pads, LKP(SDL_CONTROLLER_BUTTON_PADDLE4))) {\n"
        "            int ax = lk_pad_axis(pads, SDL_CONTROLLER_AXIS_RIGHTX), ay = lk_pad_axis(pads, SDL_CONTROLLER_AXIS_RIGHTY);\n"
        "            float fx = (ax > 8000 || ax < -8000) ? (float)ax / 32767.0f : 0.0f, fy = (ay > 8000 || ay < -8000) ? (float)ay / 32767.0f : 0.0f;\n"
        "            lk_lt_sun_nudge(2.0f * fx, -1.0f * fy); } }\n", 1)
    open(pi, "w").write(t)
    print("input.c patched: sun test aid (L5 / R5 + right stick)")
if "lk_dn_fasttoggle" not in t:   # LK_DAYNIGHT v1 (user 2026-11-06: 'eine Taste, die das Ganze im Zeitraffer abspielt'): L5 + R5 pressed together toggle the time-lapse (a day in 60 s)
    a = "            lk_lt_sun_nudge(2.0f * fx, -1.0f * fy); } }\n"
    assert t.count(a) == 1, "input.c: sun test aid line changed"
    t = t.replace(a, a + "        { extern void lk_dn_fasttoggle(void); static int both0; int both = lk_pad_code_down(pads, LKP(SDL_CONTROLLER_BUTTON_PADDLE3)) && lk_pad_code_down(pads, LKP(SDL_CONTROLLER_BUTTON_PADDLE4));   /* TIME-LAPSE (tools/patch_lights.py LK_DAYNIGHT v1) */\n"
        "          if (both && !both0) lk_dn_fasttoggle(); both0 = both; }\n", 1)
    open(pi, "w").write(t)
    print("input.c patched: time-lapse (L5 + R5)")

