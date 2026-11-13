#!/usr/bin/env python3
"""Option 'Water Reflections' (2026-11-06, user: modern effects list item 3; 'das originale Wasser ist sehr blau, ersetzen wir die Textur ganz oder kriegen wir das
anders gut hin?' -> keep the original animated water, calm its blue, mirror the figures on it).
WATER = map pixels whose winning layer tile is in one of the animated water groups (AnimatedTilesetData, tools/animsurvey.py): rivers / sea / ponds / cave water
$094F2A $09552A $09614A $09700A $09760A $097B4A $09820A $09838A $09912A $09960A, and $099E8A outside the lava rooms 403 / 404.  Waterfalls ($0957EA, the waterfall
shrine group $0968CA) and $098EAA are left out; a pixel must also be bluish (blue > red), which keeps the ship's fluttering sail ($09912A) out.
(1) Calm blue: water pixels move towards their grey value and get a little darker (LANDSTALKER_WATER_TINT 0..1, default 0 = the original colours, user 2026-11-06: 'blau original').
(2) Reflections: every figure of the visible list ($FF11DE, entity +$0E / +$10 screen foot, +$12 z, +$14 / +$16 x / y) is mirrored at the line where the water
plane under it would be: by default the floor under the figure (user pick B: the reflection starts at the feet; a jump mirrors at the floor);
LANDSTALKER_WATER_FOOT=0 = foot line + entity z - height of the first lower cell in front of it, within 6 cells (variant A, physically offset); its own sprite pixels (lk_lt_spre tag) of this frame are written upside down into a
reflection picture (nearer figures win), fading with distance from the mirror line; water pixels mix it in (alpha LANDSTALKER_WATER_ALPHA, default 0.6 (user 2026-11-06: 'etwas staerker, aber nicht viel'; was 0.5))
read through a small slow ripple (v2: under half a pixel, mixed between two neighbours).  Static tiles drawn >= 97 % in the colour indexes of the animated water tiles (in a palette line the animated water uses) count as water too
(v2, 2026-11-06: v1 took tiles with >= 12 such pixels, which caught the tiled floor of the Mercator docks)
(docks / sea rooms: few animated tiles among static ones).  Picture only.  Independent of Lighting.  Not with HD graphics.
Option: Options > Graphics > Water Reflections (id 52, ~/.landstalker_water, env LANDSTALKER_WATER=0|1 wins), default On.
Test aid: LANDSTALKER_WATER_DBG=1 (room groups + figures every 60 frames), =2 (water pixels magenta).
v3 (2026-11-06): the scan box is +-48 px wide (sword swings), Boot Colors recolour the reflection too (lk_bc_pix).
Needs patch_own.py, patch_lights.py (lk_lt_spre), patch_bootcol.py (lk_bc_pix), patch_dissolve.py, patch_haze.py before it.  Idempotent.  usage: patch_water.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_WATER v3"

p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, ("vdp_render.c: anchor not found once", a[:80])
    s = s.replace(a, b)

if VER not in s:
    MODULE = r'''/* ---- %s: calm water colour + reflections of the figures (tools/patch_water.py) ---- */
static int lk_wr_o = -1;
int lk_wr_get(void) { if (lk_wr_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_WATER"); char pth[512]; FILE *f; int v = 1; snprintf(pth, sizeof pth, "%%s/.landstalker_water", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%%d", &v) != 1) v = 1; fclose(f); } if (e) v = atoi(e); lk_wr_o = v ? 1 : 0; } return lk_wr_o; }
void lk_wr_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_wr_get(); lk_wr_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_water", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_wr_o); fclose(f); } }
static uint8 lk_wr_g[8], lk_wr_ts[2304]; static uint16_t lk_wr_idx, lk_wr_pal;   /* tile state 0 unknown / 1 water / 2 not; colour indexes of the animated water tiles; palette lines seen */
static int lk_wr_room = -2, lk_wr_any, lk_wr_dbg = -1, lk_wr_tk = -1, lk_wr_ak = -1; static long lk_wr_frame = -1; static int lk_wr_foot = -1;
static uint32_t lk_wr_buf[224][LK_OSW]; static int16_t lk_wr_dep[224][LK_OSW]; static uint8 lk_wr_line[224];   /* reflection picture: rgb + alpha (bits 24..31), depth = foot line of its figure */
static int lk_wr_iswater(uint32_t b) { switch (b) { case 0x094F2A: case 0x09552A: case 0x09614A: case 0x09700A: case 0x09760A: case 0x097B4A: case 0x09820A: case 0x09838A: case 0x09912A: case 0x09960A: return 1; } return 0; }
static void lk_wr_newroom(void) {
  int k; lk_wr_room = lk_o_room; lk_wr_any = 0;
  for (k = 0; k < 8; k++) { uint32_t b = k < lk_o_ngrp ? lk_o_grp[k].base : 0;
    lk_wr_g[k] = (uint8)(k < lk_o_ngrp && (lk_wr_iswater(b) || (b == 0x099E8A && lk_o_room != 403 && lk_o_room != 404))); if (lk_wr_g[k]) lk_wr_any = 1; }
  lk_wr_idx = 0; lk_wr_pal = 0; memset(lk_wr_ts, 0, sizeof lk_wr_ts);
  for (k = 0; k < lk_o_ngrp; k++) if (lk_wr_g[k]) { int j; for (j = lk_o_grp[k].dest; j < lk_o_grp[k].dest + 2 * lk_o_grp[k].words && j < (int)sizeof lk_o_tiles; j++) { lk_wr_idx |= (uint16_t)(1u << (lk_o_tiles[j] >> 4)); lk_wr_idx |= (uint16_t)(1u << (lk_o_tiles[j] & 15)); } }
  lk_wr_idx &= 0xFFFE;
  if (lk_wr_dbg) printf("water: room %%d colour indexes %%04X\n", lk_o_room, lk_wr_idx);
  if (lk_wr_dbg) printf("water: room %%d groups %%d water %%d (%%d %%d %%d %%d %%d %%d %%d %%d)\n", lk_o_room, lk_o_ngrp, lk_wr_any, lk_wr_g[0], lk_wr_g[1], lk_wr_g[2], lk_wr_g[3], lk_wr_g[4], lk_wr_g[5], lk_wr_g[6], lk_wr_g[7]); }
static void lk_wr_step(void) {   /* once per map frame: the reflection picture from this frame's sprite picture */
  int a, y, nf = 0;
  lk_wr_frame = platform_frame_number();
  if (lk_wr_dbg < 0) { const char *e = getenv("LANDSTALKER_WATER_DBG"); lk_wr_dbg = e ? atoi(e) : 0; }
  if (lk_wr_tk < 0) { const char *e = getenv("LANDSTALKER_WATER_TINT"), *f = getenv("LANDSTALKER_WATER_ALPHA"); float t = e ? (float)atof(e) : 0.0f, al = f ? (float)atof(f) : 0.6f; if (t < 0) t = 0; if (t > 1) t = 1; if (al < 0) al = 0; if (al > 1) al = 1; lk_wr_tk = (int)(t * 256.0f); lk_wr_ak = (int)(al * 256.0f); }
  if (lk_o_room != lk_wr_room) lk_wr_newroom();
  for (y = 0; y < 224; y++) if (lk_wr_line[y]) { memset(lk_wr_buf[y], 0, sizeof lk_wr_buf[y]); lk_wr_line[y] = 0; }
  if (!lk_wr_any || !lk_wr_ak) return;
  lk_bc_kind = lk_bc_curkind();   /* (Boot Colors: the kind of this frame, also used by lk_bc_pix) */
  for (a = 0xFF11DE; a < 0xFF11DE + 40; a += 2) {   /* the visible figures (same list as Lighting's figures) */
    int o = SW(a), b, ax, ay, fz, cx, cy, gz = 0, M, tag, x, x0, x1, y0;
    if (o & 0x8000) break;
    b = 0xFF5400 + o; ax = SW(b + 0x0E) - 128 + lk_wide_e; ay = SW(b + 0x10) - 128; fz = (int16_t)SW(b + 0x12); tag = (o >> 7) + 1;
    if (ay == -128) continue;
    cx = SW(b + 0x14) / 16; cy = SW(b + 0x16) / 16;
    if (cx >= 0 && cy >= 0 && cx < 74 && cy < 74) { int w2 = UW(0xFFD192 + 148 * cy + 2 * cx); if (w2 != 0x4000) gz = 16 * ((w2 >> 8) & 15); }
    { int zw = gz, k, d;   /* the water plane: the first LOWER cell in front of the figure (towards the viewer, +x / +y) within 6 cells; outdoor water is height 0 (blocked or void cells) */
      for (k = 1; k <= 6 && zw == gz; k++) for (d = 0; d < 3; d++) { int qx = cx + k - (d == 2), qy = cy + k - (d == 1), w3, h3;
        if (qx < 0 || qy < 0 || qx >= 74 || qy >= 74) continue;
        w3 = UW(0xFFD192 + 148 * qy + 2 * qx); h3 = w3 == 0x4000 ? 0 : 16 * ((w3 >> 8) & 15); if (h3 < zw) zw = h3; }
      if (lk_wr_foot < 0) { const char *e = getenv("LANDSTALKER_WATER_FOOT"); lk_wr_foot = e ? atoi(e) : 1; }
      if (lk_wr_foot) zw = gz;   /* default (user 2026-11-06 picked B of A / B): mirror at the floor under the figure, the reflection starts at the feet; LANDSTALKER_WATER_FOOT=0 = mirror at the water plane in front (A, physically offset) */
      M = ay + (fz > zw ? fz - zw : 0); }   /* mirror line = foot line + the figure's height above the water plane (a jump mirrors at the water too) */
    nf++;
    x0 = ax - 48; x1 = ax + 48;   /* v3: the sword swing reaches ~40 px to the side (user 2026-11-06: the sword was missing in the reflection; was +-28) */ y0 = ay - (M - ay) - 72; if (x0 < 0) x0 = 0; if (x1 > LK_OSW - 1) x1 = LK_OSW - 1; if (y0 < 0) y0 = 0;
    for (y = y0; y <= M && y < 224; y++) { int yr = 2 * M - y + 1, d = yr - M, al; if (yr < 0 || yr >= 224) continue;
      al = lk_wr_ak * (88 - d) / 88; if (al <= 4) continue;   /* fades out 88 lines below the mirror line */
      for (x = x0; x <= x1; x++) { int sp = lk_o_spr[y][x];
        if (!(sp & 0x200) || lk_lt_spre[y][x] != tag) continue;
        if (lk_wr_buf[yr][x] && lk_wr_dep[yr][x] > M) continue;   /* a nearer figure's reflection is already there */
        { PIXEL_OUT_T cc = lk_o_colour(y, sp & 0x3F); if (lk_bc_kind) cc = lk_bc_pix(y, x, sp, cc);   /* v3: Boot Colors also in the reflection (user 2026-11-06) */
          lk_wr_buf[yr][x] = ((uint32_t)(al > 255 ? 255 : al) << 24) | ((uint32_t)cc & 0xFFFFFFu); } lk_wr_dep[yr][x] = (int16_t)M; lk_wr_line[yr] = 1; } } }
  if (lk_wr_dbg == 1 && lk_wr_frame %% 60 == 0) printf("water: frame %%ld room %%d figures %%d\n", lk_wr_frame, lk_o_room, nf);
}
static int lk_wr_linebegin(int line) {
  if (!lk_wr_get() || lk_hd_n || lk_o_mode != 2) return 0;
  if (lk_wr_frame != platform_frame_number()) lk_wr_step();
  return lk_wr_any && line >= 0 && line < 224;
}
static int lk_wr_tilewater(long o) {   /* a static tile drawn >= 97 %% in the water colours counts as water too (v2): the docks / sea rooms use few animated tiles among many static ones */
  int ti = (int)(o >> 5), j, n = 0; const uint8 *q;
  if (ti < 0 || ti >= 2304) return 0;
  if (lk_wr_ts[ti]) return lk_wr_ts[ti] == 1;
  q = lk_o_tiles + ((long)ti << 5);
  { int ns = 0; for (j = 0; j < 32; j++) { int h = q[j] >> 4, l2 = q[j] & 15; if (h) { ns++; if (lk_wr_idx >> h & 1) n++; } if (l2) { ns++; if (lk_wr_idx >> l2 & 1) n++; } }
    lk_wr_ts[ti] = (uint8)((ns >= 48 && n * 100 >= ns * 97) ? 1 : 2); if (lk_wr_dbg == 3 && n >= 8) printf("water: tile %%d set %%d water %%d -> %%d\n", ti, ns, n, lk_wr_ts[ti]); }   /* v2: only tiles drawn (almost) entirely in the water colours (user 2026-11-06: the tiled floor of the Mercator docks 641 got reflections; it shares the colours; v1 took any tile with >= 12 water pixels) */
  return lk_wr_ts[ti] == 1; }
static int lk_wr_pix(int line, int i, const uint8 *t, int pick, int col) {   /* a layer pixel: water? then calm colour + reflection */
  long o; int k, r, g, b, l, tk = lk_wr_tk; uint32_t c = (uint32_t)col;
  if (!t || t < lk_o_tiles || t >= lk_o_tiles + sizeof lk_o_tiles) return col;
  o = (long)(t - lk_o_tiles);
  for (k = 0; k < lk_o_ngrp; k++) if (lk_wr_g[k] && o >= lk_o_grp[k].dest && o < lk_o_grp[k].dest + 2 * lk_o_grp[k].words) break;
  if (k < lk_o_ngrp) { lk_wr_pal |= (uint16_t)(1u << ((pick >> 4) & 3));   /* the palette line(s) the animated water is drawn with */
    if ((pick & 15) && !(lk_wr_idx >> (pick & 15) & 1)) { lk_wr_idx |= (uint16_t)(1u << (pick & 15)); memset(lk_wr_ts, 0, sizeof lk_wr_ts); } }   /* another animation frame uses one more colour */
  else if (!(lk_wr_pal >> ((pick >> 4) & 3) & 1) || !(lk_wr_idx >> (pick & 15) & 1) || !lk_wr_tilewater(o)) return col;
  r = (c >> 16) & 255; g = (c >> 8) & 255; b = c & 255;
  if (b <= r) return col;   /* foam / sail / non-water pixels of the group */
  if (lk_wr_dbg == 2) return (int)((c & 0xFF000000u) | 0xFF00FFu);
  if (tk) { l = (r * 77 + g * 151 + b * 28) >> 8;   /* calm blue: 59 %% towards grey, 22 %% darker, a touch of green (deep blue-green) at full strength */
    r += (l - r) * tk * 150 / 65536; g += (l - g) * tk * 150 / 65536; b += (l - b) * tk * 150 / 65536;
    r = r * (256 - tk * 56 / 256) / 256; g = g * (256 - tk * 40 / 256) / 256; b = b * (256 - tk * 64 / 256) / 256; }
  if (lk_wr_line[line]) { float off = 0.45f * sinf(0.30f * (float)line + 0.07f * (float)lk_wr_frame), p = (float)i + off; int x0 = (int)floorf(p), fw = (int)((p - (float)x0) * 256.0f), k2;   /* v2 ripple (user 2026-11-06: 'wabert zu viel'): under half a pixel, slower, mixed between two neighbours (was 1 px jumps) */
    for (k2 = 0; k2 < 2; k2++) { int rx = x0 + k2, w8 = k2 ? fw : 256 - fw; uint32_t q; int al;
      if (rx < 0 || rx >= LK_OSW || !(q = lk_wr_buf[line][rx])) continue;
      al = (int)(q >> 24) * w8 >> 8;
      r += ((int)((q >> 16) & 255) * 7 / 8 - r) * al / 256; g += ((int)((q >> 8) & 255) * 7 / 8 - g) * al / 256; b += ((int)(q & 255) * 15 / 16 - b) * al / 256; } }
  if (r < 0) r = 0; if (g < 0) g = 0; if (b < 0) b = 0; if (r > 255) r = 255; if (g > 255) g = 255; if (b > 255) b = 255;
  return (int)((c & 0xFF000000u) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b); }

''' % VER
    a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
    rep(a, MODULE + a)
    a = "    int lk_hz_ln = lk_hz_linebegin(line);   /* LK_HAZE v1 */\n"
    rep(a, a + "    int lk_wr_ln = lk_wr_linebegin(line);   /* %s */\n" % VER)
    a = "      if (lk_sfx_ln && !black && src != 4) col = lk_sfx_pix(line, i, src == 1 ? sp : 0, col);   /* LK_SWORDFX v1 */\n"
    rep(a, "      if (lk_wr_ln && !black && (src == 2 || src == 3)) col = lk_wr_pix(line, i, src == 2 ? afi.t : bfi.t, pick, col);   /* %s */\n" % VER + a)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
else:
    print("vdp_render.c already patched:", VER)
