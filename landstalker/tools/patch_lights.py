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
 * Colour: ambient 0.55 (slightly cool) + 2.2 x the warm light sum, clamped at 2.4; only in rooms with at least one flame light, map frames only
   (not the screens / menus), not with HD tile packs.  Picture only (Off = bit exact).
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
VER = "LK_LIGHTS v7"
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
typedef struct { int16_t z[1024]; uint8 face[1024]; uint8 nl, li[LK_LT_NL]; uint8 term[LK_LT_NL][1024]; uint8 sun[1024]; } lk_lt_blk;
static lk_lt_blk *lk_lt_b[LK_LT_BH][LK_LT_BW];
typedef struct { float x, y, z; float r, g, b; int lava; } lk_lt_light;
static lk_lt_light lk_lt_l[LK_LT_ML]; static int lk_lt_nl, lk_lt_room = -2, lk_lt_zmax; static uint32_t lk_lt_hash; static long lk_lt_frame = -1;
static int16_t lk_lt_top[74][74];
static int16_t lk_lt_gh[74][74];   /* v6: the game's heights (lk_lt_top = ours: outdoor objects raised to their drawn height for the view ray); the sun's shadow march uses these + lk_lt_fh */
#define LK_LT_FN 296                /* v7: fine object height field, 4 units per entry (74 * 16 / 4) */
#define LK_LT_PEN 12.0f             /* v7: penumbra: lit share = min over the march of PEN * clearance / horizontal distance */
static int16_t lk_lt_fh[LK_LT_FN][LK_LT_FN], lk_lt_fo[LK_LT_FN][LK_LT_FN]; static int lk_lt_fhmax;   /* v7: object top + owner object per sub column */
typedef struct { float x, y; int16_t h, hh, U, V0, w, obj; } lk_lt_card;   /* upright card facing the sun, silhouette = drawn layer A picture: v7 one per SMALL object (tree, post), one per cell of class 3 objects (v6) */
static lk_lt_card lk_lt_c[1024]; static int lk_lt_nc;
typedef struct { uint8 type; int16_t x0, y0, x1, y1, z0, eave, ridge, obj, part; } lk_lt_proxy;   /* LIGHT PROXY (docs/LIGHT_PROXY_PLAN.md): invisible shape for light only; type 1 hip (box to eave + hip roof to ridge), 2 cone (centre (x0, y0), radius x1, z0 .. ridge) */
static lk_lt_proxy lk_lt_px[255]; static int lk_lt_npx; static uint8 lk_lt_prof[255][96];   /* type 3 LATHE (centre (x0, y0), z0, height ridge - z0): radius per unit of height from the sprite's drawn width per row (like Blender's screw modifier) */ static uint8 lk_lt_fp[LK_LT_FN][LK_LT_FN];   /* proxies of the room; lk_lt_fp = proxy + 1 of every sub column (0 none) */

static int16_t lk_lt_vt[LK_LT_FN][LK_LT_FN], lk_lt_vg[LK_LT_FN][LK_LT_FN], lk_lt_vm[74][74]; static int lk_lt_rayA;   /* lk_lt_vg: proxy step 1b, the same without the proxies (pixels not drawn in layer A are ground: they pass the proxies); lk_lt_rayA = the pixel is drawn in layer A */   /* v7 speed: lk_lt_fcell of every sub column; per cell the 3 x 3 max of it (32767 = void / object near: no skip) */
static int16_t lk_lt_hd[74][74];   /* v7 speed: per cell the highest thing (field / cards) the sun ray can still meet from this cell on (3 x 3 dilated), cards only */
static int16_t lk_lt_bb[1024][5], lk_lt_sgnd[1024], lk_lt_omax[1024]; static uint8 lk_lt_ocl[1024];   /* lk_lt_sgnd: v7 ground around a SMALL object (its collision box is no picture: light and shadow use the ground + the card) */ static int16_t lk_lt_part[74][74], lk_lt_pb[2048][4]; static uint8 lk_lt_pkeep[74][74], lk_lt_wat[74][74];   /* lk_lt_wat: water cells filled by us (no part of any object) */ static int16_t lk_lt_pb2[2048][4];   /* box of the kept cells per part */   /* v7: equal height parts of the objects + their boxes (mirror boxes of the fine field) */   /* v7: per outdoor object: footprint box (cells) + cell count; class 1 small (one card), 2 building (fine field), 3 other (a card per cell, v6) */
static int16_t lk_lt_obj[74][74];
static float lk_lt_flk[LK_LT_ML];
static lk_lt_light lk_lt_sw; static float lk_lt_swk; static int lk_lt_swon;   /* v3: glow of Nigel's sword (EquippedSword $FF114E 1..4), a light that moves: no cache, no shadow */
typedef struct { float fx, fy, fz; int ax, ay; float sun; int tag; } lk_lt_fig;   /* tag (v7): entity offset / 0x80 + 1 = lk_lt_spre of its own sprite pixels */
static lk_lt_fig lk_lt_f[16]; static int lk_lt_nf, lk_lt_on;
static int lk_lt_sun, lk_lt_ztop;   /* v5: outdoor room lit by the sun (tilesets 0 / 7 / 12 / 13 / 14 / 17), highest floor */
static float lk_lt_sd[3] = { -0.72f, -0.26f, 0.64f }, lk_lt_sS = 0.70f, lk_lt_sK = 0.6f;   /* v5: unit vector to the sun, shadow level, sun strength (lk_lt_sunp) */
static double lk_lt_bms, lk_lt_pms; static int lk_lt_bn, lk_lt_pfn, lk_lt_pre, lk_lt_odn;   /* lk_lt_odn: v7 blocks computed on demand this frame (max 6: a room entry needed 60..80 = one 90 ms frame; the rest are drawn unlit for a few frames of the dark fade in) */   /* v7 test aid (DBG=5): block time of the last frame on demand / prefetched */
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
static int lk_lt_rob;   /* v6: the first outdoor object (lk_lt_obj) the last view ray passed */
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
    if (in && !lk_lt_rob && lk_lt_obj[cy][cx]) lk_lt_rob = lk_lt_obj[cy][cx];
    if (cf && in && z > top && !lk_lt_dent(cx, cy, cf)) cf = 0;   /* v3: back on room cells after a void gap (beside a corridor that sticks out of the room, church room 700): the gap was no wall; v4: at any distance (a pit in front of the walkway of room 5 = void, was a high wall), unless those cells are a narrow door niche in the wall (room 5) */
    if (z <= top) { *zo = z; return (cx == pcx && cy == pcy) || pcx == -999 || z == top ? 1 : lk_lt_side(cx, cy, pcx, pcy, z); }
    if (pcx != -999 && pin && !in && z > ptop && !cf) { int ty = lk_lt_cell(pcx, cy), tx = lk_lt_cell(cx, pcy); cz = z; cf = cx == pcx ? 3 : cy == pcy ? 2 : (ty == -32768 && tx > -32768 ? 3 : 2); }   /* back wall candidate: the side that leads into the void */
    pcx = cx; pcy = cy; ptop = top; pin = in;
  }
  if (cf) { *zo = cz; return cf; }
  return 0;
}
static void lk_lt_pos(int U, int V, int z, float *x, float *y) { int D = U - 1184; *x = (float)(2 * V + 2 * z + D) * 0.5f; *y = (float)(2 * V + 2 * z - D) * 0.5f; }
static int lk_lt_solid(float x, float y, float z) { return z < (float)lk_lt_cell((int)floorf(x / 16.0f), (int)floorf(y / 16.0f)) - 0.5f; }
static float lk_lt_term(float px, float py, float pz, float nx, float ny, float nz, const lk_lt_light *L, int shadow) {
  float vx = L->x - px, vy = L->y - py, vz = L->z - pz, d = sqrtf(vx * vx + vy * vy + vz * vz), ndl, att, t;
  if (d >= LK_LT_RAD || d < 0.001f) return d < 0.001f ? 1.0f : 0.0f;
  ndl = (nx * vx + ny * vy + nz * vz) / d; if (ndl < 0) ndl = 0;
  att = 1.0f - d / LK_LT_RAD; att *= att;
  if (shadow) {   /* v3: march from 3 units in front of the surface (a wall pixel lies on the cell border: the march along the wall hit the wall itself = box-shaped shadows, user: church wall by the books) */
    float sx = px + nx * 3.0f, sy = py + ny * 3.0f, sz = pz + nz * 3.0f, wx = L->x - sx, wy = L->y - sy, wz = L->z - sz, e = sqrtf(wx * wx + wy * wy + wz * wz);
    for (t = 2.0f; t < e - 3.0f; t += 2.0f) if (lk_lt_solid(sx + wx * t / e, sy + wy * t / e, sz + wz * t / e)) return 0.0f;
  }
  return att * (0.25f + 0.75f * ndl);
}
static int lk_lt_sunp(void) {   /* v5 prototype: LANDSTALKER_SUN=1..3 (soft / medium / strong shadows), _SUN_AZ (degrees in the world x/y plane, 110 = from the lower left of the screen like the painted light: +y faces are the brightest, user 2026-11-03), _SUN_EL (elevation) */
  static int v = -1; int r;   /* v6: part of the Lighting option (user 2026-11-03: 'gehoert alles zu Lighting'), strength 2 unless LANDSTALKER_SUN says otherwise (0 = no sun) */
  if (v < 0) { const char *e = getenv("LANDSTALKER_SUN"), *a = getenv("LANDSTALKER_SUN_AZ"), *l = getenv("LANDSTALKER_SUN_EL"); float az = a ? (float)atof(a) : 90.0f, el = l ? (float)atof(l) : 55.0f;   /* az 90 (user 2026-11-03: Nigel's shadow along the isometric grid; the sun exactly from the lower left = world +y, was 110); el 55 (user 2026-11-03: 'Nigels Schatten wirkt draussen sehr lang', chose 55 of 40 / 55 / 65; was 40) */
    v = e ? atoi(e) : 1; if (v < 0 || v > 3) v = 1;   /* v7: default 1 = soft (user 2026-11-03: 'ich denke leicht') */
    az *= 3.14159265f / 180.0f; el *= 3.14159265f / 180.0f;
    lk_lt_sd[0] = cosf(az) * cosf(el); lk_lt_sd[1] = sinf(az) * cosf(el); lk_lt_sd[2] = sinf(el);
    lk_lt_sS = v == 1 ? 0.80f : v == 2 ? 0.70f : 0.60f; lk_lt_sK = (1.08f - lk_lt_sS) / (lk_lt_sd[2] > 0.2f ? lk_lt_sd[2] : 0.2f); }
  r = lk_lt_get() ? v : 0;
  return r;
}
static float lk_lt_sunvis(float px, float py, float pz, int self) {   /* v7: share of the sun that reaches a point (0..1): march to the sun through the game's
     heights and the fine object field (lk_lt_fh), objects of the pixel's own object skipped (no self shadow: the painting has it); the closest pass gives a soft edge */
  float hl = sqrtf(lk_lt_sd[0] * lk_lt_sd[0] + lk_lt_sd[1] * lk_lt_sd[1]), res = 1.0f, t;
  if (hl < 1e-3f) hl = 1e-3f;
  for (t = 2.0f; ; t += t < 32.0f ? 1.0f : 2.0f) {
    float x = px + lk_lt_sd[0] * t, y = py + lk_lt_sd[1] * t, z = pz + lk_lt_sd[2] * t, h, d, r; int cx, cy, o;
    if (z > (float)lk_lt_ztop + 1.0f || x < 0.0f || y < 0.0f || x >= 74.0f * 16.0f || y >= 74.0f * 16.0f) return res;
    { int sx = (int)(x * 0.25f), sy = (int)(y * 0.25f); cx = sx >> 2; cy = sy >> 2; o = lk_lt_fo[sy][sx];
      if (o && o == self) continue;
      h = lk_lt_gh[cy][cx] == -32768 ? -1e9f : (float)lk_lt_gh[cy][cx]; { int ob = lk_lt_obj[cy][cx]; if (ob > 0 && ob < 1024 && lk_lt_ocl[ob] == 1) h = (float)lk_lt_sgnd[ob]; }
      { int q = lk_lt_fp[sy][sx];
        if (q && lk_lt_px[q - 1].type == 3) { const lk_lt_proxy *P = &lk_lt_px[q - 1]; int kk = (int)floorf(z - (float)P->z0); float ddx = x - P->x0, ddy = y - P->y0, dd = sqrtf(ddx * ddx + ddy * ddy), cl;
          if (kk >= 0 && kk < P->ridge - P->z0) { cl = dd - (float)lk_lt_prof[q - 1][kk]; if (cl <= 0.0f) return 0.0f; r = LK_LT_PEN * cl / (t * hl); if (r < res) res = r; }
          d = z - h + 0.5f; if (d <= 0.0f) return 0.0f; r = LK_LT_PEN * d / (t * hl); if (r < res) res = r;
          if (LK_LT_PEN * (z - (float)lk_lt_hd[cy][cx] + 0.5f) >= res * t * hl) return res;
          continue; }
        if (o && (float)lk_lt_fh[sy][sx] > h) h = (float)lk_lt_fh[sy][sx]; } }
    d = z - h + 0.5f; if (d <= 0.0f) return 0.0f;
    r = LK_LT_PEN * d / (t * hl); if (r < res) res = r;
    if (LK_LT_PEN * (z - (float)lk_lt_hd[cy][cx] + 0.5f) >= res * t * hl) return res;   /* v7 speed: nothing ahead reaches the ray any more (later passes are >= min(res, PEN * 0.64 / hl)) */
  }
}
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
  if (hl < 1e-3f) hl = 1e-3f;
  ux = lk_lt_sd[0] / hl * 8.0f; uy = lk_lt_sd[1] / hl * 8.0f;
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { float px = 16.0f * x + 8.0f, py = 16.0f * y + 8.0f; int m = -32768, n = -32768;
    for (;;) { int a = (int)floorf(px / 16.0f), b = (int)floorf(py / 16.0f); if (a < 0 || b < 0 || a >= 74 || b >= 74) break;
      if (dm[b][a] > m) m = dm[b][a]; if (dc[b][a] > n) n = dc[b][a]; px += ux; py += uy; }
    lk_lt_hd[y][x] = (int16_t)m; (void)n; }
}
static int lk_lt_isout(int room) {   /* v5: outdoor room = tileset 0 / 7 / 12 / 13 / 14 / 17 (towns, routes, docks, castle yard; tools: room table $0A0A00 byte 4), not the intro (139..143, 148) and not the dark docks (643) */
  int ts = OB(OL(0xA0A00) + 8u * (uint32_t)room + 4u) & 0x1F;
  if (room < 0 || (room >= 139 && room <= 143) || room == 148 || room == 643) return 0;
  return ts == 0 || ts == 7 || ts == 12 || ts == 13 || ts == 14 || ts == 17;
}
static void lk_lt_free(void) { int x, y; for (y = 0; y < LK_LT_BH; y++) for (x = 0; x < LK_LT_BW; x++) if (lk_lt_b[y][x]) { free(lk_lt_b[y][x]); lk_lt_b[y][x] = 0; } }
static const lk_lt_blk *lk_lt_block(int bx, int by) {   /* the block, computed on first use */
  lk_lt_blk *b; int i, k, U0 = bx * 32, V0 = by * 32;
  if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH) return 0;
  if ((b = lk_lt_b[by][bx])) return b;
  if (!lk_lt_pre && lk_lt_odn >= 6) return 0;
  if (!lk_lt_pre) lk_lt_odn++;
  b = (lk_lt_blk *)calloc(1, sizeof *b); if (!b) return 0;
  struct timespec lk_bt0; clock_gettime(CLOCK_MONOTONIC, &lk_bt0); if (lk_lt_pre) lk_lt_pfn++; else lk_lt_bn++;
  static int16_t robj[1024];
  for (i = 0; i < 1024; i++) { int z = 0, pal, pr; lk_lt_rob = 0; lk_lt_rayA = lk_o_fetch(lk_o_pa, U0 + (i & 31), V0 + (i >> 5), &pal, &pr, 0) != 0; b->face[i] = (uint8)lk_lt_ray(U0 + (i & 31), V0 + (i >> 5), &z); b->z[i] = (int16_t)z; robj[i] = (int16_t)lk_lt_rob; }
  lk_lt_rayA = 1;
  { float bd[LK_LT_NL]; for (k = 0; k < lk_lt_nl; k++) {   /* the nearest lights of the block (picture distance of the light's projection) */
    float lu = lk_lt_l[k].x - lk_lt_l[k].y + 1184.0f, lv = (lk_lt_l[k].x + lk_lt_l[k].y) * 0.5f - lk_lt_l[k].z, du = lu - (float)(U0 + 16), dv = lv - (float)(V0 + 16), d2 = du * du + dv * dv; int m;
    if (fabsf(du) >= LK_LT_RAD * 1.6f + 24.0f || fabsf(dv) >= LK_LT_RAD * 1.6f + 24.0f) continue;
    if (b->nl < LK_LT_NL) m = b->nl++; else { int q; m = 0; for (q = 1; q < LK_LT_NL; q++) if (bd[q] > bd[m]) m = q; if (bd[m] <= d2) continue; }
    b->li[m] = (uint8)k; bd[m] = d2;
  } }
  if (lk_lt_sun) for (i = 0; i < 1024; i++) {   /* v5: sun = lit floor level, 0 in the shadow of the height map; faces keep their painted shading
                                                  (outdoors the height map holds only the low collision boxes of the houses, not walls / roofs: an angle term shaded them wrongly) */
    int f = b->face[i], cx, cy, ob; float px, py, nx = f == 2 ? 1.0f : 0.0f, ny = f == 3 ? 1.0f : 0.0f, nz = f == 1 ? 1.0f : 0.0f, ndl = lk_lt_sd[2];
    if (!f) continue;
    if (f != 1 && nx * lk_lt_sd[0] + ny * lk_lt_sd[1] <= 0.0f) {   /* a face turned away from the sun is painted darker already: no extra shadow (user: 'als wuerde ein Schatten auf die rechte vordere Wand geworfen') */
      float vis = 1.0f; int sx, sy;
      { float qx, qy; lk_lt_pos(U0 + (i & 31), V0 + (i >> 5), b->z[i], &qx, &qy); sx = (int)floorf((qx - nx * 2.0f) / 4.0f); sy = (int)floorf((qy - ny * 2.0f) / 4.0f);
        if (sx >= 0 && sy >= 0 && sx < LK_LT_FN && sy < LK_LT_FN && !lk_lt_fp[sy][sx] && lk_lt_gh[sy >> 2][sx >> 2] != -32768 && lk_lt_gh[sy >> 2][sx >> 2] <= 48 && b->z[i] <= lk_lt_gh[sy >> 2][sx >> 2])   /* low boxes only (rings, flower boxes): a tall wall without a proxy keeps its painting */   /* proxies 1c: the face of a box without a proxy (eave ring, flower box) is as lit as the top just behind its edge (the tulip box at a house stayed bright in the house's shadow) */
          vis = lk_lt_sunvis(qx - nx * 2.0f, qy - ny * 2.0f, (float)lk_lt_gh[sy >> 2][sx >> 2] + 0.5f, lk_lt_fo[sy][sx]); }
      b->sun[i] = (uint8)(int)(ndl * vis * 255.0f); continue; }   /* v6: a face turned away from the sun is painted darker already: no extra shadow (user: 'als wuerde ein Schatten auf die rechte vordere Wand geworfen') */
    lk_lt_pos(U0 + (i & 31), V0 + (i >> 5), b->z[i], &px, &py);
    cx = (int)floorf((px - nx * 2.0f) / 4.0f); cy = (int)floorf((py - ny * 2.0f) / 4.0f); ob = (cx >= 0 && cy >= 0 && cx < LK_LT_FN && cy < LK_LT_FN) ? lk_lt_fo[cy][cx] : 0;   /* v7: owner of the sub column */
    if (ob > 0 && ob < 1024 && lk_lt_ocl[ob] == 1) { int pal, pr; if (!lk_o_fetch(lk_o_pa, U0 + (i & 31), V0 + (i >> 5), &pal, &pr, 0)) ob = 0; }   /* proxies 1b: ground drawn beside a trunk is ground, the tree shades it (user: 'Tannenschatten nicht bis zum Stamm') */
    if (!ob && robj[i]) { int pal, pr; if (lk_o_fetch(lk_o_pa, U0 + (i & 31), V0 + (i >> 5), &pal, &pr, 0)) ob = robj[i]; }
    { float vis = lk_lt_sunvis(px + nx * 3.0f, py + ny * 3.0f, (float)b->z[i] + nz * 3.0f, ob) * ndl;
      b->sun[i] = (uint8)(vis >= 1.0f ? 255 : vis <= 0.0f ? 0 : (int)(vis * 255.0f)); }
  }
  for (k = 0; k < b->nl; k++) for (i = 0; i < 1024; i++) {
    int f = b->face[i]; float px, py, t;
    if (!f) continue;
    lk_lt_pos(U0 + (i & 31), V0 + (i >> 5), b->z[i], &px, &py);
    t = lk_lt_term(px, py, (float)b->z[i], f == 2 ? 1.0f : 0.0f, f == 3 ? 1.0f : 0.0f, f == 1 ? 1.0f : 0.0f, &lk_lt_l[b->li[k]], 1);
    b->term[k][i] = (uint8)(t > 1.0f ? 255 : (int)(t * 255.0f));
  }
  lk_lt_b[by][bx] = b; if (lk_lt_pre) lk_lt_pms += lk_sm_ms_since(&lk_bt0); else lk_lt_bms += lk_sm_ms_since(&lk_bt0); return b;
}
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
    for (j = 0; j < LK_LT_FN; j++) for (i = 0; i < LK_LT_FN; i++) { lk_lt_fh[j][i] = -32768; lk_lt_fo[j][i] = 0; }   /* clean-up: the field holds the proxies only */
    for (k = 0; k < lk_lt_npx; k++) { const lk_lt_proxy *P = &lk_lt_px[k]; int i0, i1, j0, j1;   /* rasterise (4 units, sub column centres) */
      if (P->type == 1) { i0 = P->x0 >> 2; i1 = (P->x1 >> 2) - 1; j0 = P->y0 >> 2; j1 = (P->y1 >> 2) - 1; }
      else { i0 = (P->x0 - P->x1 - 2) >> 2; i1 = (P->x0 + P->x1 + 2) >> 2; j0 = (P->y0 - P->x1 - 2) >> 2; j1 = (P->y0 + P->x1 + 2) >> 2; }
      for (j = j0 < 0 ? 0 : j0; j <= j1 && j < LK_LT_FN; j++) for (i = i0 < 0 ? 0 : i0; i <= i1 && i < LK_LT_FN; i++) { float x = 4.0f * i + 2.0f, y = 4.0f * j + 2.0f, h;
        if (P->type == 1 && P->part && (lk_lt_part[j >> 2][i >> 2] != P->part || !lk_lt_pkeep[j >> 2][i >> 2])) continue;   /* only the part's own cells: its box is a rectangle, the part may not be (a phantom wall cast the dark stripe in front of the church) */
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
static void lk_lt_newroom(void) {   /* height map + lights of the current room */
  int x, y, k; static uint8 seen[152][304];
  lk_lt_free(); lk_lt_nl = 0; lk_lt_zmax = 0;
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int w = UW(0xFFD192 + 148 * y + 2 * x); lk_lt_top[y][x] = (int16_t)(w == 0x4000 ? -32768 : 16 * ((w >> 8) & 15)); if (w != 0x4000 && lk_lt_top[y][x] > lk_lt_zmax) lk_lt_zmax = lk_lt_top[y][x]; }
  memcpy(lk_lt_gh, lk_lt_top, sizeof lk_lt_gh); lk_lt_fhmax = -32768; lk_lt_nc = 0; memset(lk_lt_obj, 0, sizeof lk_lt_obj);
  lk_lt_sun = lk_lt_sunp() && lk_lt_isout(lk_o_room);   /* v5 */
  memset(lk_lt_wat, 0, sizeof lk_lt_wat);
  if (lk_lt_sun) { int pass, ch = 1, nw = 0;   /* proxies: WATER = a void cell whose picture is painted (river, pond): a floor 8 below its lowest neighbour (user: 'Nigels Schatten biegt sich am Fluss auf als waere das eine Wand');
       our copy only (lk_lt_top / lk_lt_gh), unpainted void (the black outside) stays void */
    for (pass = 0; pass < 12 && ch; pass++) { static int16_t nh[74][74]; ch = 0;
      for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int m = 9999, a, b2, U, V, pal, pr; nh[y][x] = lk_lt_top[y][x];
        if (lk_lt_top[y][x] != -32768) continue;
        for (b2 = y - 1; b2 <= y + 1; b2++) for (a = x - 1; a <= x + 1; a++) if (a >= 0 && b2 >= 0 && a < 74 && b2 < 74 && lk_lt_top[b2][a] != -32768 && lk_lt_top[b2][a] < m) m = lk_lt_top[b2][a];
        if (m == 9999) continue;
        m = pass == 0 ? m - 8 : m; if (m < 0) m = 0;
        U = 16 * (x - y) + 1184; V = 8 * (x + y) + 8 - m;
        if (!lk_o_fetch(lk_o_pb, U, V, &pal, &pr, 0) && !lk_o_fetch(lk_o_pa, U, V, &pal, &pr, 0)) continue;
        nh[y][x] = (int16_t)m; lk_lt_wat[y][x] = 1; ch = 1; nw++; }
      memcpy(lk_lt_top, nh, sizeof nh); }
    memcpy(lk_lt_gh, lk_lt_top, sizeof lk_lt_gh);
    if (lk_lt_dbg == 5) printf("water: room %%d, %%d void cells painted -> floor\n", lk_o_room, nw); }
  { struct timespec t0; clock_gettime(CLOCK_MONOTONIC, &t0);
    if (lk_lt_sun && lk_lt_extrude()) for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) if (lk_lt_top[y][x] > lk_lt_zmax) lk_lt_zmax = lk_lt_top[y][x];
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
          L->x = px; L->y = py; L->z = (float)z + 10.0f; L->r = cr; L->g = cg; L->b = cb; L->lava = 1; lk_lt_nl++; }
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
        L->x = px + (f == 2 ? 6.0f : 0.0f); L->y = py + (f == 3 ? 6.0f : 0.0f); L->z = (float)z + (f == 1 ? 8.0f : 2.0f); L->r = cr; L->g = cg; L->b = cb; L->lava = 0; lk_lt_nl++; }
    }
  }
  if (lk_lt_dbg == 3) { for (y = 18; y < 34; y++) { printf("hm %%2d:", y); for (x = 18; x < 44; x++) printf(" %%4d", lk_lt_top[y][x] == -32768 ? -1 : lk_lt_top[y][x]); printf("\n"); } }
  if (lk_lt_dbg) { printf("lighting: room %%d, %%d lights\n", lk_o_room, lk_lt_nl); for (k = 0; k < lk_lt_nl; k++) printf("  light %%d at (%%.0f, %%.0f, %%.0f)\n", k, lk_lt_l[k].x, lk_lt_l[k].y, lk_lt_l[k].z); }
}
static int lk_lt_swtest(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_LIGHTING_SWORD"); v = e ? atoi(e) : 0; if (v < 0 || v > 4) v = 0; } return v; }   /* test aid: sword glow colour 1..4 without that sword */
static void lk_lt_step(void) {   /* once per frame: room / height map change, flicker, figures */
  long fr = platform_frame_number(); int x, y, k, j; uint32_t h = 2166136261u; uint32_t a;
  lk_lt_frame = fr;
  if (lk_lt_bn || lk_lt_pfn) { if (lk_lt_dbg == 5 && lk_lt_bms + lk_lt_pms > 1.0) printf("blocks: frame %%ld room %%d %%d blocks %%.1f ms, prefetched %%d %%.1f ms\n", fr - 1, lk_o_room, lk_lt_bn, lk_lt_bms, lk_lt_pfn, lk_lt_pms); lk_lt_bn = lk_lt_pfn = 0; lk_lt_bms = lk_lt_pms = 0.0; }
  if (lk_lt_dbg < 0) { const char *e = getenv("LANDSTALKER_LIGHTING_DBG"); lk_lt_dbg = e ? atoi(e) : 0; }
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) h = (h ^ (uint32_t)UW(0xFFD192 + 148 * y + 2 * x)) * 16777619u;
  { static int lastopt = -1; if (lk_lt_get() != lastopt) { lastopt = lk_lt_get(); lk_lt_room = -2; } }   /* v6: the option changes what is built (flames, sun) */
  if (lk_o_room != lk_lt_room || h != lk_lt_hash) { lk_lt_room = lk_o_room; lk_lt_hash = h; lk_lt_retry = 12; lk_lt_newroom(); }
  else if (lk_lt_nl == 0 && lk_lt_retry > 0 && (fr & 7) == 0) { lk_lt_retry--; if (!lk_lt_sun || lk_lt_pahash() != lk_lt_pah) lk_lt_newroom(); }
  lk_lt_on = (lk_lt_nl > 0 || lk_lt_sun) && !lk_hd_n;
  if (lk_lt_on && lk_lt_umax >= lk_lt_umin) {   /* v7 PREFETCH (user: 'jetzt haben wir Ruckler'): blocks that came into view while walking cost ~1 ms each, up to 13 in one
      frame; compute up to 2.5 ms / 6 blocks per frame of the ring 2 blocks around the area drawn last frame, so they are ready before they are needed */
    struct timespec t0; int bx, by, n = 0, bx0 = lk_lt_fdiv(lk_lt_umin, 32) - 2, bx1 = lk_lt_fdiv(lk_lt_umax, 32) + 2, by0 = lk_lt_fdiv(lk_lt_vmin, 32) - 2, by1 = lk_lt_fdiv(lk_lt_vmax, 32) + 2;
    clock_gettime(CLOCK_MONOTONIC, &t0); lk_lt_pre = 1;
    for (by = by0 < 0 ? 0 : by0; by <= by1 && by < LK_LT_BH && n < 6; by++) for (bx = bx0 < 0 ? 0 : bx0; bx <= bx1 && bx < LK_LT_BW && n < 6; bx++)
      if (!lk_lt_b[by][bx]) { lk_lt_block(bx, by); n++; if (lk_sm_ms_since(&t0) > 2.5) n = 6; }
    lk_lt_pre = 0; }
  lk_lt_umin = lk_lt_vmin = 1 << 30; lk_lt_umax = lk_lt_vmax = -(1 << 30); lk_lt_odn = 0;
  for (k = 0; k < lk_lt_nl; k++) lk_lt_flk[k] = lk_lt_l[k].lava ? 1.0f + 0.10f * sinf((float)fr * 0.045f + (float)k * 0.9f)   /* lava: slow glow */
                                                 : 1.0f + 0.12f * sinf((float)fr * 0.21f + (float)k * 2.1f) + 0.06f * sinf((float)fr * 0.53f + (float)k * 1.3f);
  {   /* v3 sword glow (user 2026-11-03: all swords except the basic one, in the sword's colour): only where the room is lit; stronger while swinging */
    static const float swc[5][3] = { { 0, 0, 0 }, { 1.0f, 0.50f, 0.15f }, { 0.45f, 0.75f, 1.0f }, { 0.95f, 0.85f, 0.35f }, { 0.35f, 1.0f, 0.45f } };   /* Magic, Ice, Thunder, Gaia (lk_sfx_tint) */
    int sw = SB(0xFF114E) & 0xFF, swt = lk_lt_swtest(), act = SB(0xFF542C) & 0x0F, swing = act >= 1 && act <= 4; float want;
    if (swt) sw = swt;
    lk_lt_swon = lk_lt_on && lk_lt_nl > 0 && sw >= 1 && sw <= 4;   /* v5: not in rooms lit only by the sun */
    want = swing ? 1.0f : 0.0f;   /* user 2026-11-03: no light while walking, only while swinging */ lk_lt_swk += (want - lk_lt_swk) * (want > lk_lt_swk ? 0.6f : 0.15f);
    if (lk_lt_swk < 0.02f) lk_lt_swon = 0;
    if (lk_lt_swon) { float f = 1.0f + 0.05f * sinf((float)fr * 0.3f);
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
    lk_lt_f[lk_lt_nf].sun = lk_lt_sun ? lk_lt_sd[2] * lk_lt_sunvis(lk_lt_f[lk_lt_nf].fx, lk_lt_f[lk_lt_nf].fy, lk_lt_f[lk_lt_nf].fz + 20.0f, 0) : 0.0f;
    lk_lt_nf++;
  }
  for (k = 0; k < lk_lt_nl; k++) for (j = 0; j < lk_lt_nf; j++) {
    float dx = lk_lt_l[k].x - lk_lt_f[j].fx, dy = lk_lt_l[k].y - lk_lt_f[j].fy, dz = lk_lt_l[k].z - lk_lt_f[j].fz - 20.0f;
    float hd = sqrtf(dx * dx + dy * dy);
    lk_lt_pair[k][j] = dx * dx + dy * dy + dz * dz < (LK_LT_RAD + 24.0f) * (LK_LT_RAD + 24.0f);
    if (hd < 1.0f) { lk_lt_pn[k][j][0] = 0.7071f; lk_lt_pn[k][j][1] = 0.7071f; } else { lk_lt_pn[k][j][0] = dx / hd; lk_lt_pn[k][j][1] = dy / hd; }   /* v4 */
  }
}
static int lk_lt_figat(int x, int y) {   /* figure whose box holds screen pixel (x, y) (x = 0..319 + margins), -1 none */
  int j; for (j = 0; j < lk_lt_nf; j++) { int dx = x - lk_lt_f[j].ax, dy = lk_lt_f[j].ay - y; if (dx >= -16 && dx <= 16 && dy >= -6 && dy <= 56) return j; } return -1;
}
static float lk_lt_shadowed(float px, float py, float pz, const lk_lt_light *L, int k) {   /* the ray scenery pixel -> light crosses a figure's silhouette: 0..1 (v7: only the figure's OWN sprite pixels, fading with the distance pixel -> figure) */
  int j; for (j = 0; j < lk_lt_nf; j++) {
    const lk_lt_fig *F = &lk_lt_f[j]; float den, num, t, qx, qy, qz, dx, hh, nx, ny, tx, ty; int mx, my;
    if (!lk_lt_pair[k][j]) continue;
    nx = lk_lt_pn[k][j][0]; ny = lk_lt_pn[k][j][1];   /* v4: card through the foot point, facing the light */
    den = nx * (L->x - px) + ny * (L->y - py); num = nx * (F->fx - px) + ny * (F->fy - py);
    if (fabsf(den) < 1e-4f) continue;
    t = num / den; if (t < 0.02f || t > 0.98f) continue;
    qx = px + t * (L->x - px); qy = py + t * (L->y - py); qz = pz + t * (L->z - pz);
    tx = ny; ty = -nx; if (tx - ty < 0.0f) { tx = -tx; ty = -ty; }   /* along the card, oriented like the screen's +x (world (1, -1)): sprite column = world offset * 1.414 as on the camera card */
    dx = 1.4142f * (tx * (qx - F->fx) + ty * (qy - F->fy)); hh = qz - F->fz;
    if (dx < -16.0f || dx > 16.0f || hh < -6.0f || hh > 56.0f) continue;
    mx = F->ax + (int)lrintf(dx) + lk_wide_e; my = F->ay - (int)lrintf(hh);
    if (mx >= 0 && mx < LK_OSW && my >= 0 && my < 224 && (lk_o_spr[my][mx] & 0x200) && lk_lt_spre[my][mx] == F->tag) {   /* v7: the books on the church shelf are figures too: their pixels made Nigel's shadow a block (user rec_20261103_2149) */
      float ex = L->x - px, ey = L->y - py, ez = L->z - pz, d = t * sqrtf(ex * ex + ey * ey + ez * ez), w = (60.0f - d) * (1.0f / 40.0f);   /* v7: a candle close to the head stretched the shadow far and jagged: fade from 20 to 60 units */
      return w >= 1.0f ? 1.0f : w > 0.0f ? w : 0.0f; }
  }
  return 0.0f;
}
static int lk_lt_figsun(float px, float py, float pz) {   /* v5: the way scenery pixel -> sun crosses a figure (a card through its foot point, facing the sun) */
  int j; float hx = lk_lt_sd[0], hy = lk_lt_sd[1], hl = sqrtf(hx * hx + hy * hy), nx, ny, tx, ty, den;
  if (hl < 1e-3f) return 0;
  nx = hx / hl; ny = hy / hl; den = nx * lk_lt_sd[0] + ny * lk_lt_sd[1]; tx = ny; ty = -nx; if (tx - ty < 0.0f) { tx = -tx; ty = -ty; }
  for (j = 0; j < lk_lt_nf; j++) {
    const lk_lt_fig *F = &lk_lt_f[j]; float t, qx, qy, qz, dx, hh; int mx, my;
    if (fabsf(F->fx - px) > 110.0f || fabsf(F->fy - py) > 110.0f || pz > F->fz + 56.0f) continue;
    t = (nx * (F->fx - px) + ny * (F->fy - py)) / den; if (t <= 0.5f) continue;
    qx = px + t * lk_lt_sd[0]; qy = py + t * lk_lt_sd[1]; qz = pz + t * lk_lt_sd[2];
    dx = 1.4142f * (tx * (qx - F->fx) + ty * (qy - F->fy)); hh = qz - F->fz;
    if (dx < -16.0f || dx > 16.0f || hh < -6.0f || hh > 56.0f) continue;
    mx = F->ax + (int)lrintf(dx) + lk_wide_e; my = F->ay - (int)lrintf(hh);
    if (mx >= 0 && mx < LK_OSW && my >= 0 && my < 224 && (lk_o_spr[my][mx] & 0x200) && lk_lt_spre[my][mx] == F->tag) return 1;   /* v7: own pixels only */
  }
  return 0;
}
static int lk_lt_linebegin(void) { if (!lk_lt_get()) return 0; if (lk_lt_frame != platform_frame_number()) lk_lt_step(); return lk_lt_on; }
static int lk_lt_pix(int x, int line, int U, int V, int sp, int col) {   /* one composed map pixel; sp = winning sprite pixel or 0 */
  float ar = 0.55f * 0.93f, ag = 0.55f * 0.96f, ab = 0.55f * 1.06f, sr = 0, sg = 0, sb = 0, tl = 0, tb = 0; int k, j = -1;
  if (U < lk_lt_umin) lk_lt_umin = U; if (U > lk_lt_umax) lk_lt_umax = U; if (V < lk_lt_vmin) lk_lt_vmin = V; if (V > lk_lt_vmax) lk_lt_vmax = V;   /* v7: area for the prefetch */
  if ((sp & 0x200) && (j = lk_lt_figat(x, line)) >= 0) {   /* a figure pixel: lit at its cut-out position, facing the camera */
    const lk_lt_fig *F = &lk_lt_f[j]; float dx = (float)(x - F->ax), px = F->fx + dx * 0.5f, py = F->fy - dx * 0.5f, pz = F->fz + (float)(F->ay - line);
    for (k = 0; k < lk_lt_nl; k++) { float t = lk_lt_term(px, py, pz, 0.7071f, 0.7071f, 0.0f, &lk_lt_l[k], 0) * lk_lt_flk[k]; sr += t * lk_lt_l[k].r; sg += t * lk_lt_l[k].g; sb += t * lk_lt_l[k].b; }
    if (lk_lt_swon) { float t = lk_lt_term(px, py, pz, 0.7071f, 0.7071f, 0.0f, &lk_lt_sw, 0) * 0.5f; sr += t * lk_lt_sw.r; sg += t * lk_lt_sw.g; sb += t * lk_lt_sw.b; }   /* v3 */
    if (lk_lt_sun) { float u = F->sun; ar = lk_lt_sS * 0.95f + lk_lt_sK * u; ag = lk_lt_sS * 0.98f + lk_lt_sK * u * 0.97f; ab = lk_lt_sS * 1.06f + lk_lt_sK * u * 0.90f; }   /* v5 */
  } else {
    const lk_lt_blk *b = lk_lt_block(lk_lt_fdiv(U, 32), lk_lt_fdiv(V, 32)); int i;
    if (lk_lt_dbg == 4) { int pa = 0, pra = 0, pb = 0, prb = 0, ia = lk_o_fetch(lk_o_pa, U, V, &pa, &pra, 0), ib = lk_o_fetch(lk_o_pb, U, V, &pb, &prb, 0); uint32_t c = (uint32_t)col;   /* v5 test aid: priority pixels (layer A magenta, B cyan) */
      if (ia) return (int)(pra ? 0xFFE040E0u : 0xFF902090u); if (ib) return (int)(prb ? 0xFF40E0E0u : (0xFF000000u | ((c >> 2) & 0x3F3F3F))); return (int)(0xFF000000u | ((c >> 2) & 0x3F3F3F)); }
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
    if (!b->face[i]) return col;
    if (lk_lt_sun) { float u = (float)b->sun[i] * (1.0f / 255.0f);   /* v5: sky light (cool) + sun (warm), figures' shadows take the sun */
      if (u > 0.0f && lk_lt_nf) { float px, py; lk_lt_pos(U, V, b->z[i], &px, &py); if (lk_lt_figsun(px, py, (float)b->z[i])) u = 0.0f; }
      ar = lk_lt_sS * 0.95f + lk_lt_sK * u; ag = lk_lt_sS * 0.98f + lk_lt_sK * u * 0.97f; ab = lk_lt_sS * 1.06f + lk_lt_sK * u * 0.90f; }
    { static int px0 = -2, py0, px1; static long pfr = 1260; if (px0 == -2) { const char *e = getenv("LANDSTALKER_LIGHTING_PROBE"); px0 = -1; if (e && sscanf(e, "%%d,%%d,%%d,%%ld", &px0, &py0, &px1, &pfr) < 2) px0 = -1; if (px1 < px0) px1 = px0; }   /* test aid: one picture pixel's geometry + light terms */
      if (x >= px0 && x <= px1 && (x - px0) %% 4 == 0 && line == py0 && platform_frame_number() == pfr) { float qx, qy; lk_lt_pos(U, V, b->z[i], &qx, &qy); printf("probe: x %%d U %%d V %%d face %%d z %%d pos (%%.0f, %%.0f) sun %%d nl %%d:", x, U, V, b->face[i], b->z[i], qx, qy, b->sun[i], b->nl);
        for (k = 0; k < b->nl; k++) { const lk_lt_light *L = &lk_lt_l[b->li[k]]; printf(" L%%d t%%d n%%.2f", b->li[k], b->term[k][i], lk_lt_term(qx, qy, (float)b->z[i], b->face[i] == 2, b->face[i] == 3, b->face[i] == 1, L, 0)); } printf("\n"); } }
    for (k = 0; k < b->nl; k++) {
      float t = (float)b->term[k][i] * (1.0f / 255.0f); const lk_lt_light *L;
      if (t <= 0.0f) continue;
      L = &lk_lt_l[b->li[k]];
      if (lk_lt_nf) { float px, py; lk_lt_pos(U, V, b->z[i], &px, &py); { float w = lk_lt_shadowed(px, py, (float)b->z[i], L, b->li[k]); if (w >= 1.0f) { tb += t; continue; } if (w > 0.0f) { tb += t * w; t *= 1.0f - w; } } }
      tl += t; t *= lk_lt_flk[b->li[k]]; sr += t * L->r; sg += t * L->g; sb += t * L->b;
    }
    if (tb > 0.0f) { float d = 1.0f - 0.5f * tb / (tb + tl + 0.05f); ar *= d; ag *= d; ab *= d; }   /* v4: a figure's shadow also takes part of the base light (share of the blocked light), so the silhouette reads (user 2026-11-03) */
    if (lk_lt_swon) { int f = b->face[i]; float px, py, t; lk_lt_pos(U, V, b->z[i], &px, &py);   /* v3 sword glow */
      t = lk_lt_term(px, py, (float)b->z[i], f == 2 ? 1.0f : 0.0f, f == 3 ? 1.0f : 0.0f, f == 1 ? 1.0f : 0.0f, &lk_lt_sw, 0); sr += t * lk_lt_sw.r; sg += t * lk_lt_sw.g; sb += t * lk_lt_sw.b; }
  }
  { uint32_t c = (uint32_t)col; float fr = ar + 2.2f * sr, fg = ag + 2.2f * sg, fb = ab + 2.2f * sb; int r, g, bl;
    if (fr > 2.4f) fr = 2.4f; if (fg > 2.4f) fg = 2.4f; if (fb > 2.4f) fb = 2.4f;
    r = (int)((float)((c >> 16) & 255) * fr); g = (int)((float)((c >> 8) & 255) * fg); bl = (int)((float)(c & 255) * fb);
    if (r > 255) r = 255; if (g > 255) g = 255; if (bl > 255) bl = 255;
    return (int)((c & 0xFF000000u) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)bl); }
}

''' % VER

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
    "      if (lk_sfx_ln && !black && src != 4) col = lk_sfx_pix(line, i, src == 1 ? sp : 0, col);   /* LK_SWORDFX v1 */\n")
open(p, "w").write(s)
print("vdp_render.c patched:", VER)
