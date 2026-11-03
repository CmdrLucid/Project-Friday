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
   moves with Nigel (+18 above his foot), weak (0.55) while walking, strong while swinging (Player_ActionHigh $FF542C bits 0..3 = 1..4); only in rooms
   that are lit (flames / lava), no shadow, lights the other figures at half strength.
 * SCENERY LIGHT per block and light (<= 6 per block): distance falloff (radius 120 units), the angle to the face, and the shadow of the height
   map (march to the light) -> 0..255; per frame only the flicker of each light is applied.
 * FIGURES (visible entities, g_VisibleEntityList $FF11DE): upright cut-outs at their foot point (+14 / +16 / +12), silhouette = their sprite
   pixels of lk_o_spr inside a box around the anchor (+0E / +10): their own pixels are lit at their cut-out position (normal to the camera) and
   they cast shadows: a light ray from a scenery pixel that crosses a silhouette is blocked (only light / figure pairs closer than the radius).
 * Colour: ambient 0.55 (slightly cool) + 2.2 x the warm light sum, clamped at 2.4; only in rooms with at least one flame light, map frames only
   (not the screens / menus), not with HD tile packs.  Picture only (Off = bit exact).
Option: Options > Graphics > Lighting Off / On (id 47, ~/.landstalker_lighting, env LANDSTALKER_LIGHTING=0|1), default Off.
Test aid: LANDSTALKER_LIGHTING_DBG=1 prints the lights of every new room; =2 shows the geometry colours instead of the picture;
LANDSTALKER_LIGHTING_SWORD=1..4 = sword glow of that sword (Magic / Ice / Thunder / Gaia) whatever is equipped.
Needs patch_own.py, patch_modernhud.py and patch_swordfx.py before it.  Idempotent.  usage: patch_lights.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_LIGHTS v3"
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
typedef struct { int16_t z[1024]; uint8 face[1024]; uint8 nl, li[LK_LT_NL]; uint8 term[LK_LT_NL][1024]; } lk_lt_blk;
static lk_lt_blk *lk_lt_b[LK_LT_BH][LK_LT_BW];
typedef struct { float x, y, z; float r, g, b; int lava; } lk_lt_light;
static lk_lt_light lk_lt_l[LK_LT_ML]; static int lk_lt_nl, lk_lt_room = -2, lk_lt_zmax; static uint32_t lk_lt_hash; static long lk_lt_frame = -1;
static int16_t lk_lt_top[74][74];
static float lk_lt_flk[LK_LT_ML];
static lk_lt_light lk_lt_sw; static float lk_lt_swk; static int lk_lt_swon;   /* v3: glow of Nigel's sword (EquippedSword $FF114E 1..4), a light that moves: no cache, no shadow */
typedef struct { float fx, fy, fz; int ax, ay; } lk_lt_fig;
static lk_lt_fig lk_lt_f[16]; static int lk_lt_nf, lk_lt_on;
static int lk_lt_retry;               /* a new room whose planes were not built yet: look for lights again a few times */
static uint8 lk_lt_pair[LK_LT_ML][16];        /* light k / figure j close enough for a shadow */
static int lk_lt_cell(int cx, int cy) { return (cx < 0 || cy < 0 || cx >= 74 || cy >= 74) ? -32768 : lk_lt_top[cy][cx]; }
static int lk_lt_fdiv(int a, int b) { return a >= 0 ? a / b : -((-a + b - 1) / b); }
static int lk_lt_ray(int U, int V, int *zo) {   /* geometry of one picture pixel: 0 none, 1 floor, 2 face +x, 3 face +y; *zo = z of the hit */
  int D = U - 1184, z, pcx = -999, pcy = -999, ptop = -32768, pin = 0;
  for (z = lk_lt_zmax; z >= -16; z--) {
    int cx = lk_lt_fdiv(2 * V + 2 * z + D, 32), cy = lk_lt_fdiv(2 * V + 2 * z - D, 32), top = lk_lt_cell(cx, cy), in = top > -32768;
    if (z <= top) { *zo = z; return (cx == pcx && cy == pcy) || pcx == -999 ? 1 : (cx != pcx ? 2 : 3); }
    if (pcx != -999 && pin && !in && z > ptop) { *zo = z; return cx != pcx ? 2 : 3; }
    pcx = cx; pcy = cy; ptop = top; pin = in;
  }
  return 0;
}
static void lk_lt_pos(int U, int V, int z, float *x, float *y) { int D = U - 1184; *x = (float)(2 * V + 2 * z + D) * 0.5f; *y = (float)(2 * V + 2 * z - D) * 0.5f; }
static int lk_lt_solid(float x, float y, float z) { return z < (float)lk_lt_cell((int)floorf(x / 16.0f), (int)floorf(y / 16.0f)) - 0.5f; }
static float lk_lt_term(float px, float py, float pz, float nx, float ny, float nz, const lk_lt_light *L, int shadow) {
  float vx = L->x - px, vy = L->y - py, vz = L->z - pz, d = sqrtf(vx * vx + vy * vy + vz * vz), ndl, att, t;
  if (d >= LK_LT_RAD || d < 0.001f) return d < 0.001f ? 1.0f : 0.0f;
  ndl = (nx * vx + ny * vy + nz * vz) / d; if (ndl < 0) ndl = 0;
  att = 1.0f - d / LK_LT_RAD; att *= att;
  if (shadow) for (t = 4.0f; t < d - 3.0f; t += 2.0f) if (lk_lt_solid(px + vx * t / d, py + vy * t / d, pz + vz * t / d)) return 0.0f;
  return att * (0.25f + 0.75f * ndl);
}
static void lk_lt_free(void) { int x, y; for (y = 0; y < LK_LT_BH; y++) for (x = 0; x < LK_LT_BW; x++) if (lk_lt_b[y][x]) { free(lk_lt_b[y][x]); lk_lt_b[y][x] = 0; } }
static const lk_lt_blk *lk_lt_block(int bx, int by) {   /* the block, computed on first use */
  lk_lt_blk *b; int i, k, U0 = bx * 32, V0 = by * 32;
  if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH) return 0;
  if ((b = lk_lt_b[by][bx])) return b;
  b = (lk_lt_blk *)calloc(1, sizeof *b); if (!b) return 0;
  for (i = 0; i < 1024; i++) { int z = 0; b->face[i] = (uint8)lk_lt_ray(U0 + (i & 31), V0 + (i >> 5), &z); b->z[i] = (int16_t)z; }
  { float bd[LK_LT_NL]; for (k = 0; k < lk_lt_nl; k++) {   /* the nearest lights of the block (picture distance of the light's projection) */
    float lu = lk_lt_l[k].x - lk_lt_l[k].y + 1184.0f, lv = (lk_lt_l[k].x + lk_lt_l[k].y) * 0.5f - lk_lt_l[k].z, du = lu - (float)(U0 + 16), dv = lv - (float)(V0 + 16), d2 = du * du + dv * dv; int m;
    if (fabsf(du) >= LK_LT_RAD * 1.6f + 24.0f || fabsf(dv) >= LK_LT_RAD * 1.6f + 24.0f) continue;
    if (b->nl < LK_LT_NL) m = b->nl++; else { int q; m = 0; for (q = 1; q < LK_LT_NL; q++) if (bd[q] > bd[m]) m = q; if (bd[m] <= d2) continue; }
    b->li[m] = (uint8)k; bd[m] = d2;
  } }
  for (k = 0; k < b->nl; k++) for (i = 0; i < 1024; i++) {
    int f = b->face[i]; float px, py, t;
    if (!f) continue;
    lk_lt_pos(U0 + (i & 31), V0 + (i >> 5), b->z[i], &px, &py);
    t = lk_lt_term(px, py, (float)b->z[i], f == 2 ? 1.0f : 0.0f, f == 3 ? 1.0f : 0.0f, f == 1 ? 1.0f : 0.0f, &lk_lt_l[b->li[k]], 1);
    b->term[k][i] = (uint8)(t > 1.0f ? 255 : (int)(t * 255.0f));
  }
  lk_lt_b[by][bx] = b; return b;
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
static void lk_lt_newroom(void) {   /* height map + lights of the current room */
  int x, y, k; static uint8 seen[152][304];
  lk_lt_free(); lk_lt_nl = 0; lk_lt_zmax = 0;
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int w = UW(0xFFD192 + 148 * y + 2 * x); lk_lt_top[y][x] = (int16_t)(w == 0x4000 ? -32768 : 16 * ((w >> 8) & 15)); if (w != 0x4000 && lk_lt_top[y][x] > lk_lt_zmax) lk_lt_zmax = lk_lt_top[y][x]; }
  lk_lt_zmax += 192;   /* walls stand high above the floor: the view ray must start above the top of the back walls (v2: was 48, the torches of room 177 hang higher) */
  memset(seen, 0, sizeof seen);
  for (k = 0; k < lk_o_ngrp; k++) {
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
  if (lk_lt_dbg) { printf("lighting: room %%d, %%d lights\n", lk_o_room, lk_lt_nl); for (k = 0; k < lk_lt_nl; k++) printf("  light %%d at (%%.0f, %%.0f, %%.0f)\n", k, lk_lt_l[k].x, lk_lt_l[k].y, lk_lt_l[k].z); }
}
static int lk_lt_swtest(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_LIGHTING_SWORD"); v = e ? atoi(e) : 0; if (v < 0 || v > 4) v = 0; } return v; }   /* test aid: sword glow colour 1..4 without that sword */
static void lk_lt_step(void) {   /* once per frame: room / height map change, flicker, figures */
  long fr = platform_frame_number(); int x, y, k, j; uint32_t h = 2166136261u; uint32_t a;
  lk_lt_frame = fr;
  if (lk_lt_dbg < 0) { const char *e = getenv("LANDSTALKER_LIGHTING_DBG"); lk_lt_dbg = e ? atoi(e) : 0; }
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) h = (h ^ (uint32_t)UW(0xFFD192 + 148 * y + 2 * x)) * 16777619u;
  if (lk_o_room != lk_lt_room || h != lk_lt_hash) { lk_lt_room = lk_o_room; lk_lt_hash = h; lk_lt_retry = 12; lk_lt_newroom(); }
  else if (lk_lt_nl == 0 && lk_lt_retry > 0 && (fr & 7) == 0) { lk_lt_retry--; lk_lt_newroom(); }
  lk_lt_on = lk_lt_nl > 0 && !lk_hd_n;
  for (k = 0; k < lk_lt_nl; k++) lk_lt_flk[k] = lk_lt_l[k].lava ? 1.0f + 0.10f * sinf((float)fr * 0.045f + (float)k * 0.9f)   /* lava: slow glow */
                                                 : 1.0f + 0.12f * sinf((float)fr * 0.21f + (float)k * 2.1f) + 0.06f * sinf((float)fr * 0.53f + (float)k * 1.3f);
  {   /* v3 sword glow (user 2026-11-03: all swords except the basic one, in the sword's colour): only where the room is lit; stronger while swinging */
    static const float swc[5][3] = { { 0, 0, 0 }, { 1.0f, 0.50f, 0.15f }, { 0.45f, 0.75f, 1.0f }, { 0.95f, 0.85f, 0.35f }, { 0.35f, 1.0f, 0.45f } };   /* Magic, Ice, Thunder, Gaia (lk_sfx_tint) */
    int sw = SB(0xFF114E) & 0xFF, swt = lk_lt_swtest(), act = SB(0xFF542C) & 0x0F, swing = act >= 1 && act <= 4; float want;
    if (swt) sw = swt;
    lk_lt_swon = lk_lt_on && sw >= 1 && sw <= 4;
    want = swing ? 1.0f : 0.55f; lk_lt_swk += (want - lk_lt_swk) * (want > lk_lt_swk ? 0.6f : 0.15f);
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
    lk_lt_f[lk_lt_nf].ax = ax; lk_lt_f[lk_lt_nf].ay = ay; lk_lt_nf++;
  }
  for (k = 0; k < lk_lt_nl; k++) for (j = 0; j < lk_lt_nf; j++) {
    float dx = lk_lt_l[k].x - lk_lt_f[j].fx, dy = lk_lt_l[k].y - lk_lt_f[j].fy, dz = lk_lt_l[k].z - lk_lt_f[j].fz - 20.0f;
    lk_lt_pair[k][j] = dx * dx + dy * dy + dz * dz < (LK_LT_RAD + 24.0f) * (LK_LT_RAD + 24.0f);
  }
}
static int lk_lt_figat(int x, int y) {   /* figure whose box holds screen pixel (x, y) (x = 0..319 + margins), -1 none */
  int j; for (j = 0; j < lk_lt_nf; j++) { int dx = x - lk_lt_f[j].ax, dy = lk_lt_f[j].ay - y; if (dx >= -16 && dx <= 16 && dy >= -6 && dy <= 56) return j; } return -1;
}
static int lk_lt_shadowed(float px, float py, float pz, const lk_lt_light *L, int k) {   /* the ray scenery pixel -> light crosses a figure's silhouette */
  int j; for (j = 0; j < lk_lt_nf; j++) {
    const lk_lt_fig *F = &lk_lt_f[j]; float den, num, t, qx, qy, qz, dx, hh; int mx, my;
    if (!lk_lt_pair[k][j]) continue;
    den = (L->x - px) + (L->y - py); num = (F->fx - px) + (F->fy - py);
    if (fabsf(den) < 1e-4f) continue;
    t = num / den; if (t < 0.02f || t > 0.98f) continue;
    qx = px + t * (L->x - px); qy = py + t * (L->y - py); qz = pz + t * (L->z - pz);
    dx = (qx - F->fx) - (qy - F->fy); hh = qz - F->fz;
    if (dx < -16.0f || dx > 16.0f || hh < -6.0f || hh > 56.0f) continue;
    mx = F->ax + (int)lrintf(dx) + lk_wide_e; my = F->ay - (int)lrintf(hh);
    if (mx >= 0 && mx < LK_OSW && my >= 0 && my < 224 && (lk_o_spr[my][mx] & 0x200)) return 1;
  }
  return 0;
}
static int lk_lt_linebegin(void) { if (!lk_lt_get()) return 0; if (lk_lt_frame != platform_frame_number()) lk_lt_step(); return lk_lt_on; }
static int lk_lt_pix(int x, int line, int U, int V, int sp, int col) {   /* one composed map pixel; sp = winning sprite pixel or 0 */
  float ar = 0.55f * 0.93f, ag = 0.55f * 0.96f, ab = 0.55f * 1.06f, sr = 0, sg = 0, sb = 0; int k, j = -1;
  if ((sp & 0x200) && (j = lk_lt_figat(x, line)) >= 0) {   /* a figure pixel: lit at its cut-out position, facing the camera */
    const lk_lt_fig *F = &lk_lt_f[j]; float dx = (float)(x - F->ax), px = F->fx + dx * 0.5f, py = F->fy - dx * 0.5f, pz = F->fz + (float)(F->ay - line);
    for (k = 0; k < lk_lt_nl; k++) { float t = lk_lt_term(px, py, pz, 0.7071f, 0.7071f, 0.0f, &lk_lt_l[k], 0) * lk_lt_flk[k]; sr += t * lk_lt_l[k].r; sg += t * lk_lt_l[k].g; sb += t * lk_lt_l[k].b; }
    if (lk_lt_swon) { float t = lk_lt_term(px, py, pz, 0.7071f, 0.7071f, 0.0f, &lk_lt_sw, 0) * 0.5f; sr += t * lk_lt_sw.r; sg += t * lk_lt_sw.g; sb += t * lk_lt_sw.b; }   /* v3 */
  } else {
    const lk_lt_blk *b = lk_lt_block(lk_lt_fdiv(U, 32), lk_lt_fdiv(V, 32)); int i;
    if (!b) return col;
    i = ((V & 31) << 5) | (U & 31);
    if (lk_lt_dbg == 2) { static const int dc[4] = { 0x000000, 0x6E6E8C, 0xC8503C, 0x3CAA50 }; return (int)(0xFF000000u | (uint32_t)dc[b->face[i] & 3]); }
    if (!b->face[i]) return col;
    for (k = 0; k < b->nl; k++) {
      float t = (float)b->term[k][i] * (1.0f / 255.0f); const lk_lt_light *L;
      if (t <= 0.0f) continue;
      L = &lk_lt_l[b->li[k]];
      if (lk_lt_nf) { float px, py; lk_lt_pos(U, V, b->z[i], &px, &py); if (lk_lt_shadowed(px, py, (float)b->z[i], L, b->li[k])) continue; }
      t *= lk_lt_flk[b->li[k]]; sr += t * L->r; sg += t * L->g; sb += t * L->b;
    }
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
rep("int lk_sfx_ln = lk_sfx_linebegin(line);   /* LK_SWORDFX v1 */\n",
    "int lk_sfx_ln = lk_sfx_linebegin(line);   /* LK_SWORDFX v1 */\n    int lk_lt_ln = lk_lt_linebegin();   /* %s */\n" % VER)
rep("      if (lk_sfx_ln && !black && src != 4) col = lk_sfx_pix(line, i, src == 1 ? sp : 0, col);   /* LK_SWORDFX v1 */\n",
    "      if (lk_lt_ln && !black && (src == 1 || src == 2 || src == 3)) col = lk_lt_pix(x, line, ubase + x - lk_sm_sxn, vbase - lk_sm_syn, src == 1 ? sp : 0, col);   /* %s */\n" % VER +
    "      if (lk_sfx_ln && !black && src != 4) col = lk_sfx_pix(line, i, src == 1 ? sp : 0, col);   /* LK_SWORDFX v1 */\n")
open(p, "w").write(s)
print("vdp_render.c patched:", VER)
