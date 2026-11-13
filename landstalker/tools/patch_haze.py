#!/usr/bin/env python3
"""Option 'Heat Haze' (2026-11-06, user: modern effects list item 4 'Hitzeflimmern ueber Lava und grossen Feuern', MODERN_IDEAS (C); every effect gets its own switch).
The air above lava (AnimatedTilesetData entry 21 $099E8A, red only in rooms 403 / 404), fireplaces (entry 3 $095BAA) and the castle standing torches
(entry 15 $098AAA) wobbles: picture rows are shifted sideways by a fraction of a pixel (linear mix of the two neighbours) with a wave that rises.
Where: every map pixel whose winning layer tile belongs to one of these animated tile groups is a HEAT SOURCE (weight lava 1.0, fireplace 0.75, standing
torch 0.5); the strength field of a frame is made from the previous frame's sources (shifted by the camera step): it fades by LK_HZ_DEC per line upwards
(lava ~40 lines, fireplace ~30, torch ~20) and is softened sideways.  Picture only, nothing of the game is read but the room's tile groups.
Independent of Lighting.  Not applied to window pixels (HUD, text box), Modern HUD discs, black lines, or with HD replacement graphics (lk_hd_n).
Option: Options > Graphics > Heat Haze (id 51, ~/.landstalker_haze, env LANDSTALKER_HAZE=0|1 wins), default On.
Test aids: LANDSTALKER_HAZE_DBG=1 (room weights + source pixels every 60 frames), =2 (field shown as red), LANDSTALKER_HAZE_AMP=<px> (largest shift, default 1.3).
Needs patch_own.py, patch_subpix.py, patch_modernhud.py, patch_dissolve.py before it.  Idempotent.  usage: patch_haze.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_HAZE v1"

p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, ("vdp_render.c: anchor not found once", a[:80])
    s = s.replace(a, b)

if VER not in s:
    MODULE = r'''/* ---- %s: heat haze over lava and big fires (tools/patch_haze.py) ---- */
static int lk_hz_o = -1;
int lk_hz_get(void) { if (lk_hz_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_HAZE"); char pth[512]; FILE *f; int v = 1; snprintf(pth, sizeof pth, "%%s/.landstalker_haze", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%%d", &v) != 1) v = 1; fclose(f); } if (e) v = atoi(e); lk_hz_o = v ? 1 : 0; } return lk_hz_o; }
void lk_hz_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_hz_get(); lk_hz_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_haze", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_hz_o); fclose(f); } }
#define LK_HZ_DEC 6   /* strength lost per line upwards (of 255) */
static uint8 lk_hz_w[8]; static int lk_hz_room = -2, lk_hz_any, lk_hz_cur, lk_hz_has, lk_hz_du, lk_hz_dv, lk_hz_dbg = -1; static long lk_hz_frame = -1;
static int lk_hz_su[2], lk_hz_sv[2]; static float lk_hz_amp = -1.0f;
static uint8 lk_hz_src[2][224][LK_OSW];   /* heat source pixels of this frame (written while drawing) and of the previous one */
static uint8 lk_hz_f[224][LK_OSW];        /* strength field 0..255 in the previous frame's screen positions */
static uint8 lk_hz_keep[LK_OSW]; static uint32_t lk_hz_tmp[LK_OSW];
static void lk_hz_newroom(void) {   /* weights of the room's animated tile groups */
  int k; lk_hz_room = lk_o_room; lk_hz_any = 0; lk_hz_has = 0;
  for (k = 0; k < 8; k++) { uint8 w = 0;
    if (k < lk_o_ngrp) { uint32_t b = lk_o_grp[k].base;
      if (b == 0x099E8A && (lk_o_room == 403 || lk_o_room == 404)) w = 255;   /* lava (the same tiles are blue water in 406..411, Lighting v3) */
      else if (b == 0x095BAA) w = 190;   /* fireplace */
      else if (b == 0x098AAA) w = 128; }   /* castle standing torch */
    lk_hz_w[k] = w; if (w) lk_hz_any = 1; }
  memset(lk_hz_src, 0, sizeof lk_hz_src); memset(lk_hz_f, 0, sizeof lk_hz_f);
  if (lk_hz_dbg) printf("haze: room %%d groups %%d heat %%d (w %%d %%d %%d %%d %%d %%d %%d %%d)\n", lk_o_room, lk_o_ngrp, lk_hz_any, lk_hz_w[0], lk_hz_w[1], lk_hz_w[2], lk_hz_w[3], lk_hz_w[4], lk_hz_w[5], lk_hz_w[6], lk_hz_w[7]); }
static void lk_hz_step(void) {   /* once per map frame (first composed line): field from the previous frame's sources */
  int i, L, pv, n = 0;
  lk_hz_frame = platform_frame_number();
  if (lk_hz_dbg < 0) { const char *e = getenv("LANDSTALKER_HAZE_DBG"); lk_hz_dbg = e ? atoi(e) : 0; }
  if (lk_hz_amp < 0.0f) { const char *e = getenv("LANDSTALKER_HAZE_AMP"); lk_hz_amp = e ? (float)atof(e) : 1.3f; if (lk_hz_amp < 0.0f || lk_hz_amp > 6.0f) lk_hz_amp = 1.3f; }
  if (lk_o_room != lk_hz_room) lk_hz_newroom();
  if (!lk_hz_any) return;
  pv = lk_hz_cur; lk_hz_cur ^= 1;
  lk_hz_su[lk_hz_cur] = lk_o_u0; lk_hz_sv[lk_hz_cur] = lk_o_v0;
  lk_hz_du = lk_o_u0 - lk_hz_su[pv]; lk_hz_dv = lk_o_v0 - lk_hz_sv[pv];   /* same picture point: previous x = x + du, previous line = line + dv */
  if (abs(lk_hz_du) > 64 || abs(lk_hz_dv) > 64) lk_hz_du = lk_hz_dv = 1 << 20;   /* a jump (room change, warp): no field this frame */
  lk_hz_has = 0;
  for (i = 0; i < LK_OSW; i++) { int h = 0;   /* heat rises: each line keeps the strongest source below it, weaker by LK_HZ_DEC per line */
    for (L = 223; L >= 0; L--) { int sv = lk_hz_src[pv][L][i]; h -= LK_HZ_DEC; if (sv) n++; if (sv > h) h = sv; if (h < 0) h = 0; lk_hz_f[L][i] = (uint8)h; if (h) lk_hz_has = 1; } }
  if (lk_hz_has) for (L = 0; L < 224; L++) { int acc = 0, nz = 0; uint8 rowc[LK_OSW]; memcpy(rowc, lk_hz_f[L], LK_OSW);   /* soft sides: box of 7 */
    for (i = 0; i < LK_OSW; i++) if (rowc[i]) { nz = 1; break; }
    if (!nz) continue;
    for (i = 0; i < 3; i++) acc += rowc[i];
    for (i = 0; i < LK_OSW; i++) { if (i + 3 < LK_OSW) acc += rowc[i + 3]; if (i - 4 >= 0) acc -= rowc[i - 4]; lk_hz_f[L][i] = (uint8)(acc / 7); } }
  memset(lk_hz_src[lk_hz_cur], 0, sizeof lk_hz_src[lk_hz_cur]);
  if (lk_hz_dbg == 1 && lk_hz_frame %% 60 == 0) printf("haze: frame %%ld room %%d source pixels %%d field %%d shift %%d,%%d\n", lk_hz_frame, lk_o_room, n, lk_hz_has, lk_hz_du, lk_hz_dv);
}
static int lk_hz_linebegin(int line) {
  if (!lk_hz_get() || lk_hd_n || lk_o_mode != 2) return 0;
  if (lk_hz_frame != platform_frame_number()) lk_hz_step();
  return lk_hz_any && line >= 0 && line < 224;
}
static void lk_hz_mark(int line, int i, const uint8 *t) {   /* a layer pixel: heat source if its tile is in a hot group */
  long o; int k;
  if (!t || t < lk_o_tiles || t >= lk_o_tiles + sizeof lk_o_tiles || i < 0 || i >= LK_OSW) return;
  o = (long)(t - lk_o_tiles);
  for (k = 0; k < lk_o_ngrp; k++) if (lk_hz_w[k] && o >= lk_o_grp[k].dest && o < lk_o_grp[k].dest + 2 * lk_o_grp[k].words) { lk_hz_src[lk_hz_cur][line][i] = lk_hz_w[k]; return; } }
static void lk_hz_apply(PIXEL_OUT_T *row, int w, int line) {   /* after the line is composed: shift the hot pixels sideways by the rising wave */
  int i, Lp = line + lk_hz_dv; float t = (float)lk_hz_frame;
  if (!lk_hz_has || Lp < 0 || Lp >= 224 || w > LK_OSW) return;
  for (i = 0; i < w; i++) lk_hz_tmp[i] = (uint32_t)row[i];
  for (i = 0; i < w; i++) { int ip = i + lk_hz_du, s, j, k2; float off, fr, p; uint32_t a, b, c;
    if (ip < 0 || ip >= LK_OSW || lk_hz_keep[i] || (s = lk_hz_f[Lp][ip]) < 4) continue;
    if (lk_hz_dbg == 2) { c = lk_hz_tmp[i]; row[i] = (PIXEL_OUT_T)((c & 0xFF00FFFFu) | ((uint32_t)(((c >> 16) & 255) / 2 + s / 2) << 16)); continue; }
    off = lk_hz_amp * (float)s * (1.0f / 255.0f) * (0.65f * sinf(0.42f * (float)line + 0.19f * t + 0.031f * (float)i) + 0.35f * sinf(1.13f * (float)line + 0.27f * t - 0.047f * (float)i));   /* both waves climb (phase grows with line and time) */
    p = (float)i + off; j = (int)floorf(p); fr = p - (float)j;
    if (j < 0 || j + 1 >= w) continue;
    a = lk_hz_keep[j] ? lk_hz_tmp[i] : lk_hz_tmp[j]; b = lk_hz_keep[j + 1] ? lk_hz_tmp[i] : lk_hz_tmp[j + 1];
    k2 = (int)(fr * 256.0f);
    c = (lk_hz_tmp[i] & 0xFF000000u)
      | ((((a >> 16) & 255) * (256 - k2) + ((b >> 16) & 255) * k2) >> 8 << 16)
      | ((((a >> 8) & 255) * (256 - k2) + ((b >> 8) & 255) * k2) >> 8 << 8)
      | (((a & 255) * (256 - k2) + (b & 255) * k2) >> 8);
    if (lk_ss_frac && lk_ss_ref[line][i] == lk_hz_tmp[i]) lk_ss_ref[line][i] = c;   /* LK_SUBPIX v3: keep 'nobody drew over this world pixel' true */
    row[i] = (PIXEL_OUT_T)c; } }

''' % VER
    a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
    rep(a, MODULE + a)
    a = "    int lk_dz_ln = lk_dz_linebegin(line);   /* LK_DISSOLVE v1 */\n"
    rep(a, a + "    int lk_hz_ln = lk_hz_linebegin(line);   /* %s */\n" % VER)
    a = "      lk_mh_hit = nohud ? lk_mh_pix(line, i, &col) : 0;   /* LK_MHUD v3 */\n"
    rep(a, a + "      if (lk_hz_ln) { lk_hz_keep[i < LK_OSW ? i : LK_OSW - 1] = (uint8)(black || src == 4 || lk_mh_hit); if (!black && (src == 2 || src == 3)) lk_hz_mark(line, i, src == 2 ? afi.t : bfi.t); }   /* %s */\n" % VER)
    a = "    if (lk_hd_n) lk_hd_stamp[line] = lk_hd_gen;\n    lk_hd_dstamp[line] = lk_hd_gen;\n"
    rep(a, "    if (lk_hz_ln) lk_hz_apply(row, w, line);   /* %s */\n" % VER + a)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
else:
    print("vdp_render.c already patched:", VER)
