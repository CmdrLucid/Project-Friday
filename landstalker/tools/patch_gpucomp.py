#!/usr/bin/env python3
"""Picture composition on the GPU, STEP 4 (docs/RENDERER_IDEAS.md 'STEP 4' + 'STEP 4 STAGE PLAN'; user 2026-11-07: '1' = start STEP 4, 'ja' = go on with 4b).
COMPARE HARNESS, nothing changes for the player: with LANDSTALKER_GPUCOMP=2 (test aid) the own map renderer (lk_own_row) records per map line its state
(picture position U0 / V, black line, text box / window line flags, window range wlo..whi, smooth move shift, backdrop, black colours, which effects run),
the line's 64 colour palette, the window plane pixels (HUD rows / text box, lk_o_win), the water ripple of reflection lines, and per pixel its own results.
At the next present the GPU composes the same lines in an offscreen pass (FBO 448 x 224, one fragment shader, 5 draws) and reads them back:
- 4a (v1) BASE PICTURE: from the room's layer cells (lk_o_pa / pb), the tile pixels (lk_o_tiles) and the sprite buffer (lk_o_spr, still built by the CPU):
  pick (palette index), src (1 sprite, 2 layer A, 3 layer B, 4 window, 0 backdrop), black, and the colour before boot colours / light / effects.
- 4b (v2) THE FULL INPUT OF THE GPU LIGHT (lines with the GPU light lk_gl_real and without sword fx / dissolve / heat haze): boot colours (lk_bc_st mask as bit 11
  of the sprite word + lk_bc_tint), the light class (lk_gl_classify: 0 / 1 / 3 / 16 + figure via lk_lt_figat), lit windows (lk_dn_winpix, as the 'mix after
  the light' p0 / p1), water (lk_wr_pix: tile classes, tint, reflection buffer lk_wr_buf + ripple table), cloud shadows (lk_cs_pix), the Modern HUD overlay
  (lk_mh_a / lk_mh_c: on class 0 into the colour, else into p0 / p1) = the row colour, the class and p0 / p1 the CPU hands to the GPU light.
  Known source of differences: the water LEARNS its colours while drawing (lk_wr_pix sets lk_wr_pal / lk_wr_idx at the first animated water pixel of a colour);
  the GPU uses the state after the frame, so the pixels the CPU drew before the learning differ in such frames ('water-learn' frames are counted, not compared).
Lines not recorded: the seamless room change (lk_sm_state != 0), the neighbour rooms of the seam option (lk_nbn > 0).
- 4d (v3) THE REAL PATH: Options > Display > Picture Engine CPU / GPU (id 60, ~/.landstalker_pictureengine, env LANDSTALKER_PICTUREENGINE; default GPU since 2026-11-07,
  CPU on Windows builds; LANDSTALKER_GPUCOMP=0|1|2 wins as test aid).  A GPU LINE = every pixel need is on the GPU and nothing reads the CPU row: GPU light on (lk_gl_real), no sword fx /
  dissolve / heat haze / smooth sub-pixel (lk_ss_frac) / HD / depth fx / hard shadow ellipse on the line (lk_sh_row_on, darkened after lk_own_row), not the classic HUD rows,
  no title brand / window / model overlay, no seam capture, no de-dither, no frame recorder, no test aid that reads rows (LANDSTALKER_SHOT, GENRECOMP_ASCII, LANDSTALKER_MAPSHOT).
  For a GPU line lk_own_row skips its pixel loop; lk_gc_side keeps the loop's side effects: the drawn area for the light prefetch / particles (lk_lt_umin..vmax from the exact
  leftmost / rightmost counted pixel, lk_gc_src1), on-demand light blocks, the water's colour learning (lk_gc_wscan over the visible animated water cells), lk_gl_postany,
  and fills the row with 0 (alpha 0 = 'the GPU composes it'; an overlay drawn into the row later wins).  At the present: lk_gc_real1 (after the CPU picture went into
  lk_gpu_tex) composes the GPU lines into lk_gc_pic (other lines = the CPU picture) and binds it as the presented picture; lk_gc_real2 (inside the light pass, after its
  class / mix uploads) renders the GPU lines' class tags (lk_glt_t[1], now RGBA) and mixes after the light (lk_glt_t[10]), as scissor rectangles per run of GPU lines:
  NO discard in the shader (Mesa / AMD dropped whole 8 pixel blocks around the discarded pixels right of w).  Checked: presented pictures GPU == CPU in 5 recordings.
Console every 300 compared frames: 'gpucomp: frames F lines L pixels P exact E meta-diff M colour-diff C (source counts)' and
'gpucomp: full lines L pixels P exact E colour C class K mix M (water-learn frames W)' + 'gpucomp: lines with: ...' (effect use) + the first 12 differences of each kind.
Needs patch_options.py (id 60), patch_own.py and the effect patches (bootcol, water, clouds, daynight, modernhud), patch_gpu.py, patch_gpulight.py before it.  Idempotent.  usage: patch_gpucomp.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_GPUCOMP v3"

# ---------------------------------------------------------------- vdp_render.c: capture of the compositor's state per line
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, ("vdp_render.c: anchor not found once", a[:90], s.count(a))
    s = s.replace(a, b)

if VER not in s:
    MODULE = r'''/* ---- @VER@: picture composition on the GPU, compare harness (tools/patch_gpucomp.py, docs/RENDERER_IDEAS.md 'STEP 4 STAGE PLAN') ---- */
static int lk_gc_mode = -2;   /* LANDSTALKER_GPUCOMP: 0 off (default), 2 compare harness (test aid) */
static int lk_gco_o = -1;   /* 4d: Options > Display > Picture Engine (id 60, ~/.landstalker_pictureengine, env LANDSTALKER_PICTUREENGINE=0|1 wins): 0 CPU, 1 GPU (default since 2026-11-07, user 'ja picture engine = gpu bitte standard (ausgenommen windows)'; Windows builds default CPU until a Windows user tested the GPU path) */
#define LK_GCO_DEF 1   /* 2026-11-08: GPU on Windows too (user); unused since the one 'Renderer' row (follows lk_gle_get) */
extern int lk_gle_get(void);
int lk_gco_get(void) { if (lk_gco_o < 0) { const char *e = getenv("LANDSTALKER_PICTUREENGINE"); lk_gco_o = (e && *e) ? (atoi(e) ? 1 : 0) : (lk_gle_get() ? 1 : 0); } return lk_gco_o; }   /* 2026-11-08 (user: options menu clean-up): ONE row 'Renderer' (Light Engine id 56) sets both; the Picture Engine follows it, LANDSTALKER_PICTUREENGINE still wins */
void lk_gco_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_gco_get(); lk_gco_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%s/.landstalker_pictureengine", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%d\n", lk_gco_o); fclose(f); } }
static int lk_gc_env = -2, lk_gc_aid;
int lk_gc_getmode(void) {   /* 0 CPU, 1 REAL PATH (4d: the GPU composes the lines that qualify), 2 compare harness; LANDSTALKER_GPUCOMP (test aid) wins over the option */
  if (lk_gc_env == -2) { const char *e = getenv("LANDSTALKER_GPUCOMP"); lk_gc_env = e ? atoi(e) : -1; if (e && lk_gc_env != 0 && lk_gc_env != 1 && lk_gc_env != 2) lk_gc_env = 0;
    lk_gc_aid = getenv("LANDSTALKER_SHOT") || getenv("GENRECOMP_ASCII") || getenv("LANDSTALKER_MAPSHOT"); }
  lk_gc_mode = lk_gc_env >= 0 ? lk_gc_env : lk_gco_get();
  if (lk_gc_mode == 1 && lk_gc_aid) lk_gc_mode = 0;   /* a test aid reads the CPU rows */
  return lk_gc_mode; }
int lk_gc_block;   /* platform_sdl.c, per present: something reads the CPU rows (de-dither, frame recorder) -> no GPU lines */
long lk_gc_realfr = -9; int lk_gc_nreal; static long lk_gc_scanfr = -9;   /* frame + number of its GPU lines; water pre-scan done in frame */
uint16_t lk_gc_ref[224 * 448];   /* the CPU's result per pixel: 0x8000 | black ? 0x200 : pick | src << 6 */
uint32_t lk_gc_col[224 * 448];   /* the CPU's colour (before boot colours / light / effects) */
uint32_t lk_gc_fin[224 * 448], lk_gc_p0[224 * 448], lk_gc_p1[224 * 448]; uint8_t lk_gc_k[224 * 448];   /* 4b: the row colour, the mix after the light (black / white), the light class */
uint8_t lk_gc_rows[224 * 16 * 4]; /* per line 16 RGBA texels: 0 U0 lo hi, V lo hi | 1 flags, e, wlo lo hi | 2 whi lo hi, w lo hi | 3 sxn lo hi, syn lo hi | 4 backdrop | 5 margin black RGB | 6 black RGB
                                     | 7 flags2 (1 boots, 2 water, 4 clouds, 8 lit windows, 16 full compare, 32 reflection line), boot kind, window glow w | 8..11 boot colours | 12..15 boot base colours */
uint32_t lk_gc_pal[224 * 64];    /* the palette of every line (as the CPU picks it: lk_o_pix / warp pad lk_o_fxpix / pixel[]) */
uint16_t lk_gc_win[224 * 320];   /* window plane pixel + 1 (0 = none; also 0 where the Modern HUD hides the HUD rows) */
uint16_t lk_gc_rip[224 * 448];   /* water ripple of reflection lines: weight fw | (x0 - i + 1) << 8 */
long lk_gc_rowfr[224], lk_gc_capfr = -9;
long lk_gc_fx[13];   /* (12 = water reflection lines) recorded lines with: 0 boot colours, 1 water, 2 clouds, 3 haze, 4 dissolve, 5 sword fx, 6 Modern HUD, 7 smooth sub-pixel, 8 HD, 9 depth fx, 10 lit windows, 11 GPU light */
static uint16_t lk_gc_lidx, lk_gc_lpal; long lk_gc_learnfr = -9;   /* water colours at the frame's first line: a change during the frame = learning */
static void lk_gc_put32(uint8_t *q, uint32_t c) { q[0] = (uint8_t)(c >> 16); q[1] = (uint8_t)(c >> 8); q[2] = (uint8_t)c; q[3] = 255; }
static int lk_gc_linebegin(int line, int w, int e, int u0, int v, int black_line, int text, int wline, int tb, int nohud, int wlo, int whi, int hint, int fl2) {
  uint8_t *q = lk_gc_rows + line * 64; int x, k; const PIXEL_OUT_T *pl;
  if (line < 0 || line >= 224 || w > 448 || lk_sm_state != 0 || lk_nbn > 0) return 0;   /* not ported: seamless room change, neighbour rooms */
  if (!lk_o_palmode) pl = pixel; else if (lk_o_fxon) { k = lk_o_fxk[line & 255]; if (k < 0 || k > 7) return 0; pl = lk_o_fxpix[k]; } else pl = lk_o_pix;
  for (k = 0; k < 64; k++) lk_gc_pal[line * 64 + k] = (uint32_t)pl[k];
  memset(q, 0, 64);
  q[0] = (uint8_t)u0; q[1] = (uint8_t)(u0 >> 8); q[2] = (uint8_t)v; q[3] = (uint8_t)(v >> 8);
  q[4] = (uint8_t)((black_line ? 1 : 0) | (text ? 2 : 0) | (wline ? 4 : 0) | (tb ? 8 : 0) | (nohud ? 16 : 0) | 32 | ((fl2 & 64) ? 64 : 0)); q[5] = (uint8_t)e; q[6] = (uint8_t)wlo; q[7] = (uint8_t)(wlo >> 8);
  q[8] = (uint8_t)whi; q[9] = (uint8_t)(whi >> 8); q[10] = (uint8_t)w; q[11] = (uint8_t)(w >> 8);
  q[12] = (uint8_t)lk_sm_sxn; q[13] = (uint8_t)(lk_sm_sxn >> 8); q[14] = (uint8_t)lk_sm_syn; q[15] = (uint8_t)(lk_sm_syn >> 8);
  q[16] = (uint8_t)(LK_REG(7) & 0x3F);
  lk_gc_put32(q + 20, (uint32_t)(lk_o_regvdp ? pixel[0x40] : lk_o_palmode ? lk_o_pix[LK_REG(7) & 0x3F] : pixel_lut[1][0]));
  lk_gc_put32(q + 24, (uint32_t)pixel_lut[1][0]);
  if ((fl2 & 2) && lk_wr_line[line]) { fl2 |= 32; lk_gc_fx[12]++; }
  q[28] = (uint8_t)fl2; q[29] = (uint8_t)lk_bc_kind; q[30] = (fl2 & 8) ? (uint8_t)(int)(lk_dn_wk * lk_lt_fadek * 235.0f) : 0;
  if ((fl2 & 1) && lk_bc_kind >= 5 && lk_bc_kind <= 8) { static const int ent[4] = { 8, 3, 4, 5 }; for (k = 0; k < 4; k++) { lk_gc_put32(q + 32 + 4 * k, (uint32_t)lk_bc_md(lk_bc_col[lk_bc_kind - 5][k])); lk_gc_put32(q + 48 + 4 * k, (uint32_t)lk_bc_md(OW(0x901C + 2 * ent[k]))); } }
  if ((fl2 & 8) && lk_dn_wmroom != lk_o_room) lk_dn_wmask();
  if (fl2 & 32) { float off = 0.45f * sinf(0.30f * (float)line + 0.07f * (float)lk_wr_frame); for (x = 0; x < w; x++) { float p = (float)x + off; int x0 = (int)floorf(p), fw = (int)((p - (float)x0) * 256.0f); lk_gc_rip[line * 448 + x] = (uint16_t)(fw | ((x0 - x + 1) << 8)); } }   /* as lk_wr_pix */
  if ((line < 24 && !nohud) || (line >= 160 && (hint & 0xFF) == 0xA0)) { for (x = 0; x < 320; x++) { int wp = lk_o_win(line, x, hint); lk_gc_win[line * 320 + x] = (uint16_t)(wp + 1); } }
  else memset(lk_gc_win + line * 320, 0, 320 * sizeof(uint16_t));
  lk_gc_rowfr[line] = platform_frame_number();
  if (lk_gc_capfr != lk_gc_rowfr[line]) { lk_gc_lidx = lk_wr_idx; lk_gc_lpal = lk_wr_pal; }
  else if (lk_wr_idx != lk_gc_lidx || lk_wr_pal != lk_gc_lpal) lk_gc_learnfr = lk_gc_rowfr[line];
  lk_gc_capfr = lk_gc_rowfr[line];
  if (fl2 & 64) { if (lk_gc_realfr != lk_gc_capfr) { lk_gc_realfr = lk_gc_capfr; lk_gc_nreal = 0; } lk_gc_nreal++; }
  return 1; }
static int lk_gc_src1(int line, int i, int e, int u0, int v, int black_line, int text, int wline, int tb, int nohud, int wlo, int whi, int hint) {   /* 4d: the source of ONE pixel exactly as the row loop decides it, 0 when lk_gl_classify would not count it (black, window, backdrop) */
  int x = i - e, margin = (x < 0 || x >= 320), sl = line - lk_sm_syn, si = i - lk_sm_sxn, sp, ap = 0, bp = 0, apal = 0, bpal = 0, ai, bi, src = 0;
  if (black_line) return 0;
  sp = (sl >= 0 && sl < 224 && si >= 0 && si < LK_OSW) ? lk_o_spr[sl][si] : 0;
  ai = lk_o_fetch(lk_o_pa, u0 + i, v, &apal, &ap, 0); bi = lk_o_fetch(lk_o_pb, u0 + i, v, &bpal, &bp, 0);
  if ((sp & 0x200) && (sp & 0x100)) src = 1; else if (ai && ap) src = 2; else if (bi && bp) src = 3; else if (sp & 0x200) src = 1; else if (ai) src = 2; else if (bi) src = 3;
  if (margin) { if ((line < 23 && !nohud) || (wline && !tb)) return 0; }
  else { int wp = (nohud && line < 24) ? -1 : lk_o_win(line, x, hint); if (wp >= 0 && (wp & 0xF) && i >= wlo && i < whi) { if (!(text && (sp & 0x200) && (sp & 0x100) && !(sp & 0x400) && !(wp & 0x200))) return 0; } else if (wp >= 0 && !tb && wline) return 0; }
  return src; }
static void lk_gc_wscan(int u0, int v0, int w) {   /* 4d: the water learns its colours from the visible animated water cells (the CPU row loop learns them in lk_wr_pix, which GPU lines skip) */
  int L, r, c, k, j;
  for (L = 0; L < 2; L++) for (r = (v0 >> 3) - 1; r <= ((v0 + 224) >> 3) + 1; r++) for (c = (u0 >> 3) - 1; c <= ((u0 + w) >> 3) + 1; c++) { uint32 cell; long ob;
    if (r < 0 || r >= 152 || c < 0 || c >= 304) continue;
    cell = L ? lk_o_pb[r][c] : lk_o_pa[r][c]; if (!(cell & 0x10000)) continue;
    ob = (long)(cell & 0x7FF) << 5;
    for (k = 0; k < lk_o_ngrp; k++) if (lk_wr_g[k] && ob >= lk_o_grp[k].dest && ob < lk_o_grp[k].dest + 2 * lk_o_grp[k].words) break;
    if (k >= lk_o_ngrp) continue;
    lk_wr_pal |= (uint16_t)(1u << ((cell >> 13) & 3));
    for (j = 0; j < 32; j++) { int h = lk_o_tiles[ob + j] >> 4, l2 = lk_o_tiles[ob + j] & 15;
      if (h && !(lk_wr_idx >> h & 1)) { lk_wr_idx |= (uint16_t)(1u << h); memset(lk_wr_ts, 0, sizeof lk_wr_ts); }
      if (l2 && !(lk_wr_idx >> l2 & 1)) { lk_wr_idx |= (uint16_t)(1u << l2); memset(lk_wr_ts, 0, sizeof lk_wr_ts); } } } }
static void lk_gc_side(PIXEL_OUT_T *row, int line, int w, int e, int u0, int v, int black_line, int text, int wline, int tb, int nohud, int wlo, int whi, int hint, int water) {   /* 4d: what the skipped row loop leaves for others */
  int i, l = -1, r = -1; long f = platform_frame_number();
  if (water && lk_wr_any && lk_gc_scanfr != f) { lk_gc_scanfr = f; lk_gc_wscan(u0, v, w); }
  for (i = 0; i < w && l < 0; i++) if (lk_gc_src1(line, i, e, u0, v, black_line, text, wline, tb, nohud, wlo, whi, hint)) l = i;   /* lk_gl_classify: the drawn picture area (GL5 ring, particles) */
  for (i = w - 1; l >= 0 && i >= l && r < 0; i--) if (lk_gc_src1(line, i, e, u0, v, black_line, text, wline, tb, nohud, wlo, whi, hint)) r = i;
  if (l >= 0) { int U = u0 + l, U2 = u0 + r;   /* the drawn area (GL5 ring); no CPU light blocks since 2026-11-12 */
    if (U < lk_lt_umin) lk_lt_umin = U; if (U2 > lk_lt_umax) lk_lt_umax = U2; if (v < lk_lt_vmin) lk_lt_vmin = v; if (v > lk_lt_vmax) lk_lt_vmax = v; }
  for (i = 0; i < w; i++) row[i] = 0;   /* alpha 0 = 'the GPU composes this pixel'; what is drawn into the row later (overlays) wins on the GPU */
  lk_gl_postany = 1;   /* the GPU writes the mix after the light of these lines: the light pass must read it */
  lk_o_shline = -1; }
'''.replace("@VER@", VER)
    a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
    rep(a, MODULE + a)
    a = "    int lk_cs_ln = lk_cs_linebegin();   /* LK_CLOUDS v1 */\n"
    rep(a, a + "    int lk_gc_md = lk_gc_getmode(), lk_gc_skip = 0, lk_gc_gl = lk_gc_md == 1 && lk_gl_real && !lk_sfx_ln && !lk_dz_ln && !lk_hz_ln && !lk_ss_frac && !lk_hd_n && !fxon && !lk_sh_row_on && (nohud || line >= 24)\n"
           "      && !lk_brand_on && !lk_win_on && lk_m_on <= 0 && !lk_sm_capture_now && !lk_gc_block && lk_o_mode == 2;   /* @VER@ 4d: a GPU line (everything its pixels need is on the GPU, nothing reads the CPU row) */\n"
           "    int lk_gc_ln = (lk_gc_md == 2 || lk_gc_gl) && lk_gc_linebegin(line, w, e, ubase - e - lk_sm_sxn, vbase - lk_sm_syn, black_line, text, wline, tb, nohud, wlo, whi, hint,\n"
           "      (lk_bc_ln ? 1 : 0) | (lk_wr_ln ? 2 : 0) | (lk_cs_ln ? 4 : 0) | ((lk_lt_ln && lk_dn_win) ? 8 : 0) | ((lk_gl_real && !lk_sfx_ln && !lk_dz_ln && !lk_hz_ln) ? 16 : 0) | (lk_gc_gl ? 64 : 0));   /* @VER@ */\n"
           "    if (lk_gc_ln) { lk_gc_fx[0] += lk_bc_ln != 0; lk_gc_fx[1] += lk_wr_ln != 0; lk_gc_fx[2] += lk_cs_ln != 0; lk_gc_fx[3] += lk_hz_ln != 0; lk_gc_fx[4] += lk_dz_ln != 0; lk_gc_fx[5] += lk_sfx_ln != 0; lk_gc_fx[6] += nohud != 0; lk_gc_fx[7] += lk_ss_frac != 0; lk_gc_fx[8] += lk_hd_n != 0; lk_gc_fx[9] += fxon != 0; lk_gc_fx[10] += (lk_lt_ln && lk_dn_win) != 0; lk_gc_fx[11] += lk_gl_real != 0; }   /* @VER@: which effects the lines use */\n"
           "    if (lk_gc_md == 1 && lk_gc_ln) { lk_gc_side(row, line, w, e, ubase - e - lk_sm_sxn, vbase - lk_sm_syn, black_line, text, wline, tb, nohud, wlo, whi, hint, lk_wr_ln); lk_gc_skip = w; lk_gc_ln = 0; }   /* @VER@ 4d: the row loop is skipped */\n".replace("@VER@", VER))
    a = "    for (i = 0; i < w; i++) {\n      int x = i - e, margin = (x < 0 || x >= 320), pick = -1,"
    rep(a, a.replace("for (i = 0; i < w; i++)", "for (i = lk_gc_skip; i < w; i++)"))
    a = "      lk_vh[line & 7][i] = (PIXEL_OUT_T)col; lk_vhv[line & 7][i] = (src == 0 || black || margin || (col & 0xFFFFFF) == 0) ? 1 : 0;\n"
    rep(a, a + "      if (lk_gc_ln) { lk_gc_ref[line * 448 + i] = (uint16_t)(0x8000 | (black ? 0x200 : ((pick & 0x3F) | (src << 6)))); lk_gc_col[line * 448 + i] = (uint32_t)col; }   /* %s */\n" % VER)
    a = "      if (lk_hz_ln) { lk_hz_keep[i < LK_OSW ? i : LK_OSW - 1] = "
    rep(a, "      if (lk_gc_ln) { int o_ = line * 448 + i; lk_gc_fin[o_] = (uint32_t)col; lk_gc_k[o_] = (uint8_t)lk_gl_k; lk_gc_p0[o_] = lk_gl_p0; lk_gc_p1[o_] = lk_gl_p1; }   /* %s */\n" % VER + a)
    TAIL = r'''
/* ---- @VER@: data access for the GPU side (platform_sdl.c lk_gc_pass; at the present, after the frame was composed) ---- */
const uint32_t *lk_gc_planes(void) { return &lk_o_pa[0][0]; }   /* lk_o_pa then lk_o_pb (152 x 304 each, bit 16 = present, low 16 = tile word) */
const uint32_t *lk_gc_planesb(void) { return &lk_o_pb[0][0]; }
const uint8_t *lk_gc_tiles(void) { return lk_o_tiles; }          /* 0x12000 bytes, 4 bits per pixel */
void lk_gc_sprb(uint16_t *o) { int y, x; for (y = 0; y < 224; y++) for (x = 0; x < 448; x++) o[y * 448 + x] = (uint16_t)(lk_o_spr[y][x] | (lk_bc_st[y][x] == lk_bc_stamp ? 0x800 : 0)); }   /* sprite word + 0x800 boot pixel */
void lk_gc_wclass(uint8_t *o) { int t;   /* per tile: 1 = in an animated water group, 2 = a static tile in the water colours (lk_wr_tilewater, without filling its cache), 0 = not water */
  for (t = 0; t < 2304; t++) { long ob = (long)t << 5; int k, c = 0; for (k = 0; k < lk_o_ngrp; k++) if (lk_wr_g[k] && ob >= lk_o_grp[k].dest && ob < lk_o_grp[k].dest + 2 * lk_o_grp[k].words) break;
    if (k < lk_o_ngrp) c = 1;
    else if (lk_wr_ts[t]) c = lk_wr_ts[t] == 1 ? 2 : 0;
    else { const uint8 *q = lk_o_tiles + ob; int j, n = 0, ns = 0; for (j = 0; j < 32; j++) { int h = q[j] >> 4, l2 = q[j] & 15; if (h) { ns++; if (lk_wr_idx >> h & 1) n++; } if (l2) { ns++; if (lk_wr_idx >> l2 & 1) n++; } } c = (ns >= 48 && n * 100 >= ns * 97) ? 2 : 0; }
    o[t] = (uint8_t)c; } }
const uint32_t *lk_gc_wrbuf(void) { return &lk_wr_buf[0][0]; }
const uint8_t *lk_gc_spre(void) { static uint8_t b[224 * 448 * 2]; int i; for (i = 0; i < 224 * 448; i++) { b[2 * i] = (&lk_lt_spre[0][0])[i]; b[2 * i + 1] = (&lk_lt_spre2[0][0])[i]; } return b; }   /* figure tag of every sprite pixel + the tag of a figure hidden under it (LK_LTHIDE v1), luminance alpha (the light's class tag, lk_gl_clstag) */
void lk_gc_water(int *tk, int *pal, int *idx) { *tk = lk_wr_tk > 0 ? lk_wr_tk : 0; *pal = lk_wr_pal; *idx = lk_wr_idx; }
const uint8_t *lk_gc_clouds(int *ox8, int *oy8, int *kf) { *ox8 = lk_cs_ox >> 3; *oy8 = lk_cs_oy >> 3; *kf = lk_cs_kf; return lk_cs_tex; }   /* 128 x 128 */
void lk_gc_mhud(uint8_t *o, int *y0, int *y1) { int y, x; *y0 = lk_mh_y0; *y1 = lk_mh_y1;   /* 464 x 240 RGBA: colour + alpha */
  for (y = 0; y < LK_MH_H; y++) for (x = 0; x < LK_MH_W; x++) { uint8_t *q = o + 4 * (y * LK_MH_W + x); int a = (y >= lk_mh_y0 && y <= lk_mh_y1) ? lk_mh_a[y][x] : 0; uint32_t c = (uint32_t)lk_mh_c[y][x];
    q[0] = (uint8_t)(c >> 16); q[1] = (uint8_t)(c >> 8); q[2] = (uint8_t)c; q[3] = (uint8_t)a; } }
void lk_gc_dnmask(float *m) { int k, y; for (k = 0; k < 8; k++) for (y = 0; y < 8; y++) m[k * 8 + y] = (float)lk_dn_wm[k][y]; }   /* LK_DNWIN197 v1: 8 window tiles */
int lk_gc_learned(void) { return lk_gc_learnfr == lk_gc_capfr || lk_wr_idx != lk_gc_lidx || lk_wr_pal != lk_gc_lpal; }   /* the water learned a colour during the frame */
int lk_gc_figs(float *f) { int j; for (j = 0; j < lk_lt_nf && j < 16; j++) { f[2 * j] = (float)lk_lt_f[j].ax; f[2 * j + 1] = (float)lk_lt_f[j].ay; } return lk_lt_nf < 16 ? lk_lt_nf : 16; }
'''.replace("@VER@", VER)
    s = s.rstrip("\n") + "\n" + TAIL
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
else:
    print("vdp_render.c already patched:", VER)

# ---------------------------------------------------------------- platform_sdl.c: the GPU pass + compare at the present
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    MODULE = r'''/* ---- @VER@: picture composition on the GPU, compare harness (tools/patch_gpucomp.py) ---- */
extern int lk_gc_getmode(void); extern uint16_t lk_gc_ref[224 * 448]; extern uint32_t lk_gc_col[224 * 448]; extern uint8_t lk_gc_rows[224 * 16 * 4]; extern uint32_t lk_gc_pal[224 * 64];
extern uint16_t lk_gc_win[224 * 320], lk_gc_rip[224 * 448]; extern long lk_gc_rowfr[224], lk_gc_capfr, lk_gc_fx[13], lk_gc_learnfr;
extern uint32_t lk_gc_fin[224 * 448], lk_gc_p0[224 * 448], lk_gc_p1[224 * 448]; extern uint8_t lk_gc_k[224 * 448];
extern const uint32_t *lk_gc_planes(void); extern const uint32_t *lk_gc_planesb(void); extern const uint8_t *lk_gc_tiles(void); extern void lk_gc_sprb(uint16_t *o);
extern void lk_gc_wclass(uint8_t *o); extern const uint32_t *lk_gc_wrbuf(void); extern void lk_gc_water(int *tk, int *pal, int *idx); extern const uint8_t *lk_gc_clouds(int *ox8, int *oy8, int *kf);
extern const uint8_t *lk_gc_spre(void); extern long lk_gc_realfr; extern int lk_gc_nreal, lk_gc_block;
extern void lk_gc_mhud(uint8_t *o, int *y0, int *y1); extern void lk_gc_dnmask(float *m); extern int lk_gc_figs(float *f); extern int lk_gc_learned(void);
static const char *lk_gc_fs = "#version 120\n"
"uniform sampler2D rows; uniform sampler2D pal; uniform sampler2D win; uniform sampler2D spr; uniform sampler2D pln; uniform sampler2D til;\n"
"uniform sampler2D wcl; uniform sampler2D wrb; uniform sampler2D rip; uniform sampler2D mhd; uniform sampler2D cst; uniform sampler2D fbt; uniform sampler2D spe; uniform float uReal; uniform float uYo;\n"
"uniform float uMode; uniform vec4 uFig[8]; uniform float uNf; uniform vec4 uDnM[16]; uniform vec3 uCs; uniform vec3 uWr; uniform vec2 uMh;\n"
"float by(float v) { return floor(v * 255.0 + 0.5); }\n"
"vec3 by3(vec3 v) { return floor(v * 255.0 + 0.5); }\n"
"float bit(float v, float n) { return mod(floor(v / exp2(n)), 2.0); }\n"
"float tdiv(float a, float b) { return a >= 0.0 ? floor(a / b) : -floor(-a / b); }\n"   /* C integer division (towards zero) */
"float s16(float lo, float hi) { float v = by(lo) + 256.0 * by(hi); return v >= 32768.0 ? v - 65536.0 : v; }\n"
"float u16(float lo, float hi) { return by(lo) + 256.0 * by(hi); }\n"
"vec4 rowt(float c, float line) { return texture2D(rows, vec2((c + 0.5) / 16.0, (line + 0.5) / 224.0)); }\n"
"vec4 fetch(float U, float V, float layer, out vec2 ixy) {\n"   /* lk_o_fetch: (colour index, palette, priority, tile) of one layer pixel at picture position (U, V); ixy = pixel in the tile after the flips */
"  ixy = vec2(0.0); if (U < 0.0 || V < 0.0 || U >= 2432.0 || V >= 1216.0) return vec4(0.0);\n"
"  float tc = floor(U / 8.0), tr = floor(V / 8.0), ix = U - tc * 8.0, iy = V - tr * 8.0;\n"
"  vec4 c = texture2D(pln, vec2((tc + 0.5) / 304.0, (tr + layer * 152.0 + 0.5) / 304.0));\n"
"  if (c.b < 0.5) return vec4(0.0);\n"
"  float lo = by(c.r), hi = by(c.g), t = lo + 256.0 * mod(hi, 8.0);\n"
"  if (bit(hi, 3.0) > 0.5) ix = 7.0 - ix; if (bit(hi, 4.0) > 0.5) iy = 7.0 - iy; ixy = vec2(ix, iy);\n"
"  float a = t * 32.0 + iy * 4.0 + floor(ix / 2.0);\n"
"  float b = by(texture2D(til, vec2((mod(a, 1024.0) + 0.5) / 1024.0, (floor(a / 1024.0) + 0.5) / 72.0)).r);\n"
"  float ci = mod(ix, 2.0) < 0.5 ? floor(b / 16.0) : mod(b, 16.0); if (by(c.a) < 16.0 && ci == by(c.a)) return vec4(0.0);\n"   /* LK_GLUNPAINTA v1 */
"  return vec4(ci, mod(floor(hi / 32.0), 4.0), floor(hi / 128.0), t); }\n"
"vec3 boot(vec3 c, float pk, float line) {\n"   /* lk_bc_tint */
"  float k = -1.0; pk = mod(pk, 64.0); if (pk == 40.0) k = 0.0; else if (pk == 35.0) k = 1.0; else if (pk == 36.0) k = 2.0; else if (pk == 37.0) k = 3.0; if (k < 0.0) return c;\n"
"  vec3 o = by3(rowt(8.0 + k, line).rgb), b = by3(rowt(12.0 + k, line).rgb); float sb = b.r + b.g + b.b, sc = c.r + c.g + c.b; if (sb <= 0.0) return c;\n"
"  return min(floor((o * sc + floor(sb / 2.0)) / sb), vec3(255.0)); }\n"
"vec3 winpix(vec3 c, float pick, float t, vec2 ixy, float w) {\n"   /* lk_dn_winpix */
"  float idx = mod(pick, 16.0), k = -1.0; if (pick >= 16.0 || (idx != 1.0 && idx != 14.0)) return c;\n"
"  if (t == 195.0) k = 0.0; else if (t == 196.0) k = 1.0; else if (t == 199.0) k = 2.0; else if (t == 200.0) k = 3.0; else if (t == 210.0) k = 4.0; else if (t == 211.0) k = 5.0; else if (t == 197.0) k = 6.0; else if (t == 198.0) k = 7.0; if (k < 0.0) return c;\n"
"  float n = k * 8.0 + ixy.y, nc = mod(n, 4.0); vec4 mv = uDnM[int(floor(n / 4.0))]; float mk = nc == 0.0 ? mv.x : nc == 1.0 ? mv.y : nc == 2.0 ? mv.z : mv.w;\n"
"  if (bit(mk, ixy.x) < 0.5) return c;\n"
"  vec3 g = idx == 1.0 ? vec3(255.0, 200.0, 100.0) : vec3(232.0, 154.0, 72.0);\n"
"  return vec3(c.r + tdiv((g.r - c.r) * w, 256.0), c.g + tdiv((g.g - c.g) * w, 256.0), c.b + tdiv((g.b - c.b) * w, 256.0)); }\n"
"vec3 water(vec3 c, float pick, float t, float line, float i, bool rl) {\n"   /* lk_wr_pix */
"  float wc = by(texture2D(wcl, vec2((mod(t, 48.0) + 0.5) / 48.0, (floor(t / 48.0) + 0.5) / 48.0)).r);\n"
"  if (wc != 1.0 && !(wc == 2.0 && bit(uWr.y, floor(pick / 16.0)) > 0.5 && bit(uWr.z, mod(pick, 16.0)) > 0.5)) return c;\n"
"  float r = c.r, g = c.g, b = c.b, tk = uWr.x; if (b <= r) return c;\n"
"  if (tk > 0.0) { float l = floor((r * 77.0 + g * 151.0 + b * 28.0) / 256.0);\n"
"    r += tdiv((l - r) * tk * 150.0, 65536.0); g += tdiv((l - g) * tk * 150.0, 65536.0); b += tdiv((l - b) * tk * 150.0, 65536.0);\n"
"    r = tdiv(r * (256.0 - floor(tk * 56.0 / 256.0)), 256.0); g = tdiv(g * (256.0 - floor(tk * 40.0 / 256.0)), 256.0); b = tdiv(b * (256.0 - floor(tk * 64.0 / 256.0)), 256.0); }\n"
"  if (rl) { vec4 rp = texture2D(rip, vec2((i + 0.5) / 448.0, (line + 0.5) / 224.0)); float fw = by(rp.r), x0 = i + by(rp.a) - 1.0;\n"
"    for (int k2 = 0; k2 < 2; k2++) { float rx = x0 + float(k2), w8 = k2 == 1 ? fw : 256.0 - fw; if (rx < 0.0 || rx >= 448.0) continue;\n"
"      vec4 q = texture2D(wrb, vec2((rx + 0.5) / 448.0, (line + 0.5) / 224.0)); vec3 qc = by3(q.rgb); float qa = by(q.a); if (qa == 0.0 && qc == vec3(0.0)) continue;\n"
"      float al = floor(qa * w8 / 256.0);\n"
"      r += tdiv((floor(qc.r * 7.0 / 8.0) - r) * al, 256.0); g += tdiv((floor(qc.g * 7.0 / 8.0) - g) * al, 256.0); b += tdiv((floor(qc.b * 15.0 / 16.0) - b) * al, 256.0); } }\n"
"  return clamp(vec3(r, g, b), 0.0, 255.0); }\n"
"vec3 cloud(vec3 c, float U, float V) {\n"   /* lk_cs_pix */
"  float fu = U * 32.0 - uCs.x, fv = V * 32.0 - uCs.y, iu = floor(fu / 256.0), iv = floor(fv / 256.0), au = fu - iu * 256.0, av = fv - iv * 256.0;\n"
"  iu = mod(iu, 128.0); iv = mod(iv, 128.0); float iu1 = mod(iu + 1.0, 128.0), iv1 = mod(iv + 1.0, 128.0);\n"
"  float t00 = by(texture2D(cst, vec2((iu + 0.5) / 128.0, (iv + 0.5) / 128.0)).r), t10 = by(texture2D(cst, vec2((iu1 + 0.5) / 128.0, (iv + 0.5) / 128.0)).r);\n"
"  float t01 = by(texture2D(cst, vec2((iu + 0.5) / 128.0, (iv1 + 0.5) / 128.0)).r), t11 = by(texture2D(cst, vec2((iu1 + 0.5) / 128.0, (iv1 + 0.5) / 128.0)).r);\n"
"  float s0 = t00 * (256.0 - au) + t10 * au, s1 = t01 * (256.0 - au) + t11 * au, sh = floor((floor(s0 / 256.0) * (256.0 - av) + floor(s1 / 256.0) * av) / 256.0);\n"
"  if (sh <= 0.0) return c; float k = floor(sh * uCs.z / 256.0);\n"
"  return vec3(floor(c.r * (256.0 - k) / 256.0), floor(c.g * (256.0 - floor(k * 15.0 / 16.0)) / 256.0), floor(c.b * (256.0 - floor(k * 3.0 / 4.0)) / 256.0)); }\n"
"vec3 mh(vec3 c, float line, float i) {\n"   /* lk_mh_pix */
"  if (line < uMh.x || line > uMh.y || i >= 464.0) return c; vec4 m = texture2D(mhd, vec2((i + 0.5) / 464.0, (line + 0.5) / 240.0)); float a = by(m.a); vec3 mc = by3(m.rgb);\n"
"  if (a <= 0.0) return c; if (a >= 255.0) return mc; return floor((mc * a + c * (255.0 - a)) / 255.0); }\n"
"vec4 outv(float m) { return vec4(mod(m, 256.0) / 255.0, floor(m / 256.0) / 255.0, 0.0, 1.0); }\n"
"void main() {\n"
"  vec2 fc = floor(gl_FragCoord.xy); float i = fc.x, line = fc.y - uYo; bool real = uReal > 0.5;\n"
"  vec4 r0 = rowt(0.0, line), r1 = rowt(1.0, line), r2 = rowt(2.0, line), r3 = rowt(3.0, line), r4 = rowt(4.0, line), r7 = rowt(7.0, line);\n"
"  float fl = by(r1.r), w = u16(r2.b, r2.a), f2 = by(r7.r);\n"
"  if (bit(fl, 5.0) < 0.5 || i >= w || (real && bit(fl, 6.0) < 0.5)) { if (uMode > 4.5 && uMode < 5.5) { gl_FragColor = texture2D(fbt, (fc + 0.5) / vec2(448.0, 224.0)); return; } gl_FragColor = vec4(0.0); return; }\n"
"  bool bline = bit(fl, 0.0) > 0.5, text = bit(fl, 1.0) > 0.5, wline = bit(fl, 2.0) > 0.5, tb = bit(fl, 3.0) > 0.5, nohud = bit(fl, 4.0) > 0.5;\n"
"  float U0 = s16(r0.r, r0.g), V = s16(r0.b, r0.a), e = by(r1.g), wlo = u16(r1.b, r1.a), whi = u16(r2.r, r2.g), sxn = s16(r3.r, r3.g), syn = s16(r3.b, r3.a);\n"
"  float x = i - e; bool margin = x < 0.0 || x >= 320.0;\n"
"  float sl = line - syn, si = i - sxn, sp = 0.0;\n"
"  if (sl >= 0.0 && sl < 224.0 && si >= 0.0 && si < 448.0) { vec4 t = texture2D(spr, vec2((si + 0.5) / 448.0, (sl + 0.5) / 224.0)); sp = by(t.r) + 256.0 * by(t.a); }\n"
"  bool s200 = bit(sp, 9.0) > 0.5, s100 = bit(sp, 8.0) > 0.5, s400 = bit(sp, 10.0) > 0.5;\n"
"  bool black = bline, ovw = false; float pick = 0.0, src = 0.0, tile = 0.0; vec2 ixy = vec2(0.0);\n"
"  if (!black) {\n"
"    vec2 ia, ib; vec4 A = fetch(U0 + i, V, 0.0, ia), B = fetch(U0 + i, V, 1.0, ib);\n"
"    if (s200 && s100) { pick = mod(sp, 64.0); src = 1.0; }\n"
"    else if (A.x > 0.0 && A.z > 0.0) { pick = A.y * 16.0 + A.x; src = 2.0; }\n"
"    else if (B.x > 0.0 && B.z > 0.0) { pick = B.y * 16.0 + B.x; src = 3.0; }\n"
"    else if (s200) { pick = mod(sp, 64.0); src = 1.0; }\n"
"    else if (A.x > 0.0) { pick = A.y * 16.0 + A.x; src = 2.0; }\n"
"    else if (B.x > 0.0) { pick = B.y * 16.0 + B.x; src = 3.0; }\n"
"    else pick = by(r4.r);\n"
"    if (src == 2.0) { tile = A.w; ixy = ia; } else if (src == 3.0) { tile = B.w; ixy = ib; }\n"
"    if (margin) { if ((line < 23.0 && !nohud) || (wline && !tb)) black = true; }\n"
"    else { vec4 t = texture2D(win, vec2((x + 0.5) / 320.0, (line + 0.5) / 224.0)); float wp = by(t.r) + 256.0 * by(t.a) - 1.0;\n"
"      if (wp >= 0.0 && mod(wp, 16.0) > 0.0 && i >= wlo && i < whi) { if (!(text && s200 && s100 && !s400 && bit(wp, 9.0) < 0.5)) { pick = mod(wp, 64.0); src = 4.0; } else ovw = true; }\n"
"      else if (wp >= 0.0 && !tb && wline) black = true; } }\n"
"  float k = 0.0;\n"   /* lk_gl_classify; LK_OVWUNLIT v1: a sprite above the text box stays unlit */
"  if (!black && !ovw) { if (src >= 1.0 && src <= 3.0) { k = 1.0; if (src == 1.0 && s200) { for (int j = 0; j < 16; j++) { if (float(j) >= uNf) break; vec4 fv = uFig[j / 2]; vec2 fj = (j - 2 * (j / 2)) == 0 ? fv.xy : fv.zw; float dx = x - fj.x, dy = fj.y - line; if (dx >= -16.0 && dx <= 16.0 && dy >= -6.0 && dy <= 56.0) { k = 16.0 + float(j); break; } } } }\n"
"    else if (src == 0.0) k = 3.0; }\n"
"  if (uMode > 5.5) { vec4 st = texture2D(spr, vec2((i + 0.5) / 448.0, (line + 0.5) / 224.0)); vec4 se = texture2D(spe, vec2((i + 0.5) / 448.0, (line + 0.5) / 224.0)); float tg = bit(by(st.a), 1.0) > 0.5 ? by(se.r) : 0.0, tg2 = bit(by(st.a), 1.0) > 0.5 ? by(se.a) : 0.0;\n"   /* the light's class tag (lk_gl_clstag): class | figure tag of the unshifted sprite pixel << 8 */
"    gl_FragColor = vec4(k / 255.0, k / 255.0, tg2 / 255.0, tg / 255.0); return; }\n"
"  if (uMode > 0.5 && uMode < 1.5) { float m = black ? 512.0 : pick + 64.0 * src; gl_FragColor = vec4(mod(m, 256.0) / 255.0, floor(m / 256.0) / 255.0, k / 255.0, 1.0); return; }\n"
"  vec3 col = black ? by3(margin ? rowt(5.0, line).rgb : rowt(6.0, line).rgb) : by3(texture2D(pal, vec2((pick + 0.5) / 64.0, (line + 0.5) / 224.0)).rgb);\n"
"  if (uMode < 0.5) { gl_FragColor = vec4(col / 255.0, 1.0); return; }\n"
"  vec3 p0 = vec3(0.0), p1 = vec3(255.0); float bk = by(r7.g), dnw = by(r7.b);\n"
"  if (bit(f2, 0.0) > 0.5 && !black && src == 1.0 && bit(sp, 11.0) > 0.5 && bk >= 5.0 && bk <= 8.0) col = boot(col, sp, line);\n"
"  if (bit(f2, 3.0) > 0.5 && !black && (src == 2.0 || src == 3.0)) { vec3 c2 = winpix(col, pick, tile, ixy, dnw); if (c2 != col) { p0 = winpix(p0, pick, tile, ixy, dnw); p1 = winpix(p1, pick, tile, ixy, dnw); } }\n"
"  if (bit(f2, 1.0) > 0.5 && !black && (src == 2.0 || src == 3.0)) col = water(col, pick, tile, line, i, bit(f2, 5.0) > 0.5);\n"
"  if (bit(f2, 2.0) > 0.5 && !black && src >= 1.0 && src <= 3.0) col = cloud(col, U0 + i, V);\n"
"  if (nohud) { if (k > 0.0) { vec3 cc = mh(col, line, i); if (cc != col) { p0 = mh(p0, line, i); p1 = mh(p1, line, i); } } else col = mh(col, line, i); }\n"
"  if (uMode > 4.5) { vec4 f = texture2D(fbt, (fc + 0.5) / vec2(448.0, 224.0)); if (by(f.a) == 0.0 && by3(f.rgb) == vec3(0.0)) gl_FragColor = vec4(col / 255.0, 1.0); else gl_FragColor = f; return; }\n"   /* the presented picture: GPU colour, or what was drawn into the row afterwards */
"  gl_FragColor = uMode < 2.5 ? vec4(col / 255.0, 1.0) : vec4((uMode < 3.5 ? p0 : p1) / 255.0, 0.0); }\n";
#define LK_GC_NT 13
static int lk_gc_st; static lkGLuint lk_gc_prog, lk_gc_fbo, lk_gc_out, lk_gc_pic, lk_gc_t[LK_GC_NT]; static lkGLint lk_gc_u[LK_GC_NT + 10]; static long lk_gc_r2fr = -9;
static long lk_gc_n, lk_gc_lines, lk_gc_px, lk_gc_ex, lk_gc_md, lk_gc_cd, lk_gc_src[6], lk_gc_fl, lk_gc_fpx, lk_gc_fex, lk_gc_fc, lk_gc_fk, lk_gc_fm, lk_gc_learn, lk_gc_fchg, lk_gc_ffig, lk_gc_fmix; static int lk_gc_shown, lk_gc_fshown;
static int lk_gc_init(void) {
  static const char *un[] = { "rows", "pal", "win", "spr", "pln", "til", "wcl", "wrb", "rip", "mhd", "cst", "fbt", "spe", "uMode", "uFig", "uNf", "uDnM", "uCs", "uWr", "uMh", "uReal", "uYo" }; lkGLint ok = 0; lkGLuint vs, fs; char log[2048]; int i;
  static const int tw[LK_GC_NT] = { 16, 64, 320, 448, 304, 1024, 48, 448, 448, 464, 128, 1, 448 }, th[LK_GC_NT] = { 224, 224, 224, 224, 304, 72, 48, 224, 224, 240, 128, 1, 224 };
  static const lkGLenum tf[LK_GC_NT] = { 0x1908, 0x1908, 0x190A, 0x190A, 0x1908, 0x1909, 0x1909, 0x1908, 0x190A, 0x1908, 0x1909, 0x1908, 0x190A };   /* unit 11 = fbt: the presented picture (lk_gpu_tex) is bound there */
  if (!lk_glGenFramebuffers) { *(void **)&lk_glGenFramebuffers = lk_gpu_fn("glGenFramebuffers"); *(void **)&lk_glBindFramebuffer = lk_gpu_fn("glBindFramebuffer");
    *(void **)&lk_glFramebufferTexture2D = lk_gpu_fn("glFramebufferTexture2D"); *(void **)&lk_glCheckFramebufferStatus = lk_gpu_fn("glCheckFramebufferStatus"); }
  if (!lk_glUniform4fv) *(void **)&lk_glUniform4fv = lk_gpu_fn("glUniform4fv");
  if (!lk_glUniform3f) *(void **)&lk_glUniform3f = lk_gpu_fn("glUniform3f");
  if (!lk_glGenFramebuffers || !lk_glBindFramebuffer || !lk_glFramebufferTexture2D || !lk_glCheckFramebufferStatus || !lk_glUniform3f) { printf("gpucomp: GL functions missing\n"); return -1; }
  { static const char *vsrc = "#version 120\nvoid main() { gl_Position = gl_Vertex; }\n"; vs = lk_glCreateShader(0x8B31); lk_glShaderSource(vs, 1, &vsrc, 0); lk_glCompileShader(vs); lk_glGetShaderiv(vs, 0x8B81, &ok); if (!ok) return -1; }
  fs = lk_glCreateShader(0x8B30); lk_glShaderSource(fs, 1, &lk_gc_fs, 0); lk_glCompileShader(fs); lk_glGetShaderiv(fs, 0x8B81, &ok);
  if (!ok) { lk_glGetShaderInfoLog(fs, sizeof log, 0, log); printf("gpucomp: shader failed: %s\n", log); return -1; }
  lk_gc_prog = lk_glCreateProgram(); lk_glAttachShader(lk_gc_prog, vs); lk_glAttachShader(lk_gc_prog, fs); lk_glLinkProgram(lk_gc_prog); lk_glGetProgramiv(lk_gc_prog, 0x8B82, &ok);
  if (!ok) { lk_glGetProgramInfoLog(lk_gc_prog, sizeof log, 0, log); printf("gpucomp: link failed: %s\n", log); return -1; }
  for (i = 0; i < LK_GC_NT + 9; i++) lk_gc_u[i] = lk_glGetUniformLocation(lk_gc_prog, un[i]);
  for (i = 0; i < LK_GC_NT; i++) { lk_glActiveTexture(0x84C0 + i); lk_gc_t[i] = lk_glt_tex(tw[i], th[i], tf[i], tf[i]); }
  lk_glActiveTexture(0x84C0); lk_gc_out = lk_glt_tex(448, 224, 0x1908, 0x1908); lk_gc_pic = lk_glt_tex(448, 224, 0x1908, 0x80E1);
  lk_glGenFramebuffers(1, &lk_gc_fbo); lk_glBindFramebuffer(0x8D40, lk_gc_fbo); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_gc_out, 0);
  ok = lk_glCheckFramebufferStatus(0x8D40) == 0x8CD5; lk_glBindFramebuffer(0x8D40, 0);
  { lkGLenum e = lk_glGetError(); if (e || !ok) { printf("gpucomp: setup failed (GL error %04X, fbo %d)\n", (unsigned)e, ok); return -1; } }
  printf("gpucomp: @VER@ ready (%s)\n", lk_gc_getmode() == 1 ? "real path, LANDSTALKER_GPUCOMP=1" : "compare harness, LANDSTALKER_GPUCOMP=2");
  return 1; }
static uint8_t lk_gc_rowsu[224 * 64]; static int lk_gc_nl;
static void lk_gc_upload(void) {   /* the frame's data -> textures (units 0..10, 12) + uniforms; leaves the program in use */
  static uint8_t pl[304 * 304 * 4], wc[48 * 48], mhb[464 * 240 * 4]; static uint16_t sprb[224 * 448]; uint8_t *rows = lk_gc_rowsu;
  int i, L, k, tk, wpal, widx, ox8, oy8, kf, my0, my1, nf; const uint32_t *pa, *pb; const uint8_t *cst; float fig[32], dnm[64];
  memcpy(rows, lk_gc_rows, sizeof lk_gc_rowsu); lk_gc_nl = 0; for (L = 0; L < 224; L++) if (lk_gc_rowfr[L] != lk_gc_capfr) rows[L * 64 + 4] = 0; else lk_gc_nl++;   /* lines not recorded this frame: skipped */
  pa = lk_gc_planes(); pb = lk_gc_planesb();
  for (k = 0; k < 2; k++) { const uint32_t *P = k ? pb : pa; uint8_t *o = pl + k * 152 * 304 * 4; for (i = 0; i < 152 * 304; i++) { uint32_t c = P[i]; o[4 * i] = (uint8_t)c; o[4 * i + 1] = (uint8_t)(c >> 8); o[4 * i + 2] = (c & 0x10000) ? 255 : 0; o[4 * i + 3] = (c & 0x20000u) ? (uint8_t)((c >> 18) & 15u) : 255; }   /* LK_GLUNPAINTA v1: alpha < 16 = a colour dropped in this cell */ }
  lk_gc_sprb(sprb); lk_gc_wclass(wc); lk_gc_water(&tk, &wpal, &widx); cst = lk_gc_clouds(&ox8, &oy8, &kf); lk_gc_mhud(mhb, &my0, &my1); lk_gc_dnmask(dnm); nf = lk_gc_figs(fig);
  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_gc_t[0]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 16, 224, 0x1908, 0x1401, rows);
  lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, lk_gc_t[1]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 64, 224, 0x80E1, 0x1401, lk_gc_pal);
  lk_glActiveTexture(0x84C2); lk_glBindTexture(0x0DE1, lk_gc_t[2]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 320, 224, 0x190A, 0x1401, lk_gc_win);
  lk_glActiveTexture(0x84C3); lk_glBindTexture(0x0DE1, lk_gc_t[3]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x190A, 0x1401, sprb);
  lk_glActiveTexture(0x84C4); lk_glBindTexture(0x0DE1, lk_gc_t[4]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 304, 304, 0x1908, 0x1401, pl);
  lk_glActiveTexture(0x84C5); lk_glBindTexture(0x0DE1, lk_gc_t[5]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 1024, 72, 0x1909, 0x1401, lk_gc_tiles());
  lk_glActiveTexture(0x84C6); lk_glBindTexture(0x0DE1, lk_gc_t[6]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 48, 48, 0x1909, 0x1401, wc);
  lk_glActiveTexture(0x84C7); lk_glBindTexture(0x0DE1, lk_gc_t[7]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x80E1, 0x1401, lk_gc_wrbuf());
  lk_glActiveTexture(0x84C8); lk_glBindTexture(0x0DE1, lk_gc_t[8]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x190A, 0x1401, lk_gc_rip);
  lk_glActiveTexture(0x84C9); lk_glBindTexture(0x0DE1, lk_gc_t[9]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 464, 240, 0x1908, 0x1401, mhb);
  lk_glActiveTexture(0x84CA); lk_glBindTexture(0x0DE1, lk_gc_t[10]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 128, 128, 0x1909, 0x1401, cst);
  lk_glActiveTexture(0x84CC); lk_glBindTexture(0x0DE1, lk_gc_t[12]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x190A, 0x1401, lk_gc_spre());
  lk_glUseProgram(lk_gc_prog); for (i = 0; i < LK_GC_NT; i++) lk_glUniform1i(lk_gc_u[i], i);
  lk_glUniform4fv(lk_gc_u[LK_GC_NT + 1], 8, fig); lk_glUniform1f(lk_gc_u[LK_GC_NT + 2], (float)nf); lk_glUniform4fv(lk_gc_u[LK_GC_NT + 3], 16, dnm);
  lk_glUniform3f(lk_gc_u[LK_GC_NT + 4], (float)ox8, (float)oy8, (float)kf); lk_glUniform3f(lk_gc_u[LK_GC_NT + 5], (float)tk, (float)wpal, (float)widx); lk_glUniform2f(lk_gc_u[LK_GC_NT + 6], (float)my0, (float)my1);
  lk_glUniform1f(lk_gc_u[LK_GC_NT + 8], 0.0f); }
static void lk_gc_pass(void) {   /* compare harness, inside lk_gpu_present after SDL's state is saved (texture unit 0 active, unpack alignment 4) */
  static uint8_t rb[5][224 * 448 * 4]; static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 }; uint8_t *rows = lk_gc_rowsu;
  lkGLint fb0 = 0, tb[LK_GC_NT], vp[4]; long fr = platform_frame_number(); int i, L, k, nl, learn;
  if (lk_gc_getmode() != 2 || lk_gc_st < 0 || lk_gc_capfr != fr - 1) return;
  for (i = 0; i < LK_GC_NT; i++) { lk_glActiveTexture(0x84C0 + i); lk_glGetIntegerv(0x8069, &tb[i]); }
  if (lk_gc_st == 0) { lk_gc_st = lk_gc_init(); if (lk_gc_st < 0) { for (i = LK_GC_NT - 1; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); } return; } }
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glGetIntegerv(0x0BA2, vp);
  learn = lk_gc_learned(); lk_gc_upload(); nl = lk_gc_nl; lk_glUniform1f(lk_gc_u[LK_GC_NT + 7], 0.0f);
  lk_glBindFramebuffer(0x8D40, lk_gc_fbo); lk_glViewport(0, 0, 448, 224); lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad);
  for (k = 0; k < 5; k++) { lk_glUniform1f(lk_gc_u[LK_GC_NT], (float)k); lk_glDrawArrays(0x0005, 0, 4); lk_glReadPixels(0, 0, 448, 224, 0x1908, 0x1401, rb[k]); }   /* 0 base colour, 1 meta + class, 2 row colour, 3 / 4 mix after the light */
  lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); lk_glViewport(vp[0], vp[1], vp[2], vp[3]);
  for (i = LK_GC_NT - 1; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); }
  lk_gc_n++; lk_gc_lines += nl; if (learn) lk_gc_learn++;
#define LK_GC_RGB(b, o) (((uint32_t)(b)[4 * (o)] << 16) | ((uint32_t)(b)[4 * (o) + 1] << 8) | (b)[4 * (o) + 2])
  for (L = 0; L < 224; L++) { int w, full; if (!(rows[L * 64 + 4] & 32)) continue; w = rows[L * 64 + 10] | (rows[L * 64 + 11] << 8); full = (rows[L * 64 + 28] & 16) && !learn; if (full) lk_gc_fl++;
    for (i = 0; i < w && i < 448; i++) { int o = L * 448 + i; uint16_t rf = lk_gc_ref[o]; uint32_t cc = lk_gc_col[o] & 0xFFFFFFu, gc = LK_GC_RGB(rb[0], o);
      int gm = rb[1][4 * o] | (rb[1][4 * o + 1] << 8), cm = rf & 0x3FF, bm = gm != cm, bc = gc != cc;
      if (!(rf & 0x8000)) continue;
      lk_gc_px++; lk_gc_src[(cm & 0x200) ? 5 : ((cm >> 6) & 7) > 4 ? 4 : ((cm >> 6) & 7)]++;
      if (!bm && !bc) lk_gc_ex++; else { if (bm) lk_gc_md++; if (bc) lk_gc_cd++;
        if (lk_gc_shown < 12) { lk_gc_shown++; printf("gpucomp: diff frame %ld line %d i %d cpu pick %d src %d black %d colour %06X | gpu pick %d src %d black %d colour %06X\n", fr - 1, L, i,
          cm & 63, (cm >> 6) & 7, (cm >> 9) & 1, (unsigned)cc, gm & 63, (gm >> 6) & 7, (gm >> 9) & 1, (unsigned)gc); } }
      if (full) { uint32_t cf = lk_gc_fin[o] & 0xFFFFFFu, gf = LK_GC_RGB(rb[2], o), c0 = lk_gc_p0[o] & 0xFFFFFFu, g0 = LK_GC_RGB(rb[3], o), c1 = lk_gc_p1[o] & 0xFFFFFFu, g1 = LK_GC_RGB(rb[4], o); int ck = lk_gc_k[o], gk = rb[1][4 * o + 2];
        int dc = cf != gf, dk = ck != gk, dm = c0 != g0 || c1 != g1;
        lk_gc_fpx++; if (cf != cc) lk_gc_fchg++; if (ck >= 16) lk_gc_ffig++; if (c0 != 0 || c1 != 0xFFFFFFu) lk_gc_fmix++; if (!dc && !dk && !dm) { lk_gc_fex++; continue; } if (dc) lk_gc_fc++; if (dk) lk_gc_fk++; if (dm) lk_gc_fm++;
        if (lk_gc_fshown < 12) { lk_gc_fshown++; printf("gpucomp: full diff frame %ld line %d i %d pick %d src %d | cpu row %06X class %d mix %06X/%06X | gpu row %06X class %d mix %06X/%06X\n", fr - 1, L, i, cm & 63, (cm >> 6) & 7,
          (unsigned)cf, ck, (unsigned)c0, (unsigned)c1, (unsigned)gf, gk, (unsigned)g0, (unsigned)g1); } } } }
  if (lk_gc_n % 300 == 0) {
    printf("gpucomp: frames %ld lines %ld pixels %ld exact %ld meta-diff %ld colour-diff %ld (backdrop %ld sprite %ld A %ld B %ld window %ld black %ld)\n", lk_gc_n, lk_gc_lines, lk_gc_px, lk_gc_ex, lk_gc_md, lk_gc_cd,
      lk_gc_src[0], lk_gc_src[1], lk_gc_src[2], lk_gc_src[3], lk_gc_src[4], lk_gc_src[5]);
    printf("gpucomp: full lines %ld pixels %ld exact %ld colour %ld class %ld mix %ld (water-learn frames %ld, not compared; changed by effects %ld, figure pixels %ld, with a mix %ld)\n", lk_gc_fl, lk_gc_fpx, lk_gc_fex, lk_gc_fc, lk_gc_fk, lk_gc_fm, lk_gc_learn, lk_gc_fchg, lk_gc_ffig, lk_gc_fmix);
    printf("gpucomp: lines with: boots %ld water %ld clouds %ld haze %ld dissolve %ld swordfx %ld modernhud %ld subpix %ld hd %ld depthfx %ld litwin %ld gpulight %ld reflection %ld\n", lk_gc_fx[0], lk_gc_fx[1], lk_gc_fx[2], lk_gc_fx[3], lk_gc_fx[4], lk_gc_fx[5], lk_gc_fx[6], lk_gc_fx[7], lk_gc_fx[8], lk_gc_fx[9], lk_gc_fx[10], lk_gc_fx[11], lk_gc_fx[12]); }
}
static long lk_gc_rn, lk_gc_rlines;
static void lk_gc_real1(void) {   /* 4d REAL PATH, in lk_gpu_present right after the CPU picture (fb) went into lk_gpu_tex: the GPU lines composed into lk_gc_pic (the other lines = fb), unit 0 -> lk_gc_pic */
  static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 }; lkGLint fb0 = 0, tb[LK_GC_NT], vp[4], prog = 0; long fr = platform_frame_number(); int i;
  lk_gc_block = lk_dd_mode != 0 || s_record != NULL || lk_gc_st < 0;   /* (a failed GPU setup: CPU lines from the next frame) */
  if (lk_gc_getmode() != 1 || lk_gc_st < 0 || lk_gc_capfr != fr - 1 || lk_gc_realfr != lk_gc_capfr || lk_gc_nreal <= 0) return;
  for (i = 0; i < LK_GC_NT; i++) { lk_glActiveTexture(0x84C0 + i); lk_glGetIntegerv(0x8069, &tb[i]); }
  if (lk_gc_st == 0) { lk_gc_st = lk_gc_init(); if (lk_gc_st < 0) { for (i = LK_GC_NT - 1; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); } return; } }
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glGetIntegerv(0x0BA2, vp); lk_glGetIntegerv(0x8B8D, &prog);
  lk_gc_upload(); lk_glActiveTexture(0x84CB); lk_glBindTexture(0x0DE1, (lkGLuint)tb[0]);   /* fbt = the CPU picture */
  lk_glUniform1f(lk_gc_u[LK_GC_NT + 7], 1.0f); lk_glUniform1f(lk_gc_u[LK_GC_NT], 5.0f);
  lk_glBindFramebuffer(0x8D40, lk_gc_fbo); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_gc_pic, 0); lk_glViewport(0, 0, 448, 224); lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad);
  lk_glDrawArrays(0x0005, 0, 4);
  lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_gc_out, 0); lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); lk_glViewport(vp[0], vp[1], vp[2], vp[3]); lk_glUseProgram((lkGLuint)prog);
  for (i = LK_GC_NT - 1; i >= 1; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); }
  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_gc_pic);   /* everything after (light, bounce, filters) reads the composed picture */
  lk_gc_r2fr = fr; lk_gc_rn++; lk_gc_rlines += lk_gc_nreal;
  { static int dbg = -1; if (dbg < 0) { const char *e = getenv("LANDSTALKER_GPUCOMP_DBG"); dbg = e ? atoi(e) : 0; } if (dbg >= 2 && fr % 300 == 1) printf("gpucomp: frame %ld composed on the GPU: %d lines\n", fr - 1, lk_gc_nreal); if (dbg && lk_gc_rn % 300 == 0) printf("gpucomp: real frames %ld, GPU lines %ld (%.1f per frame)\n", lk_gc_rn, lk_gc_rlines, (double)lk_gc_rlines / (double)lk_gc_rn); }
}
static void lk_gc_draws(int yoff) {   /* 4d: the quad over every run of GPU lines (scissor rectangles, width w): no discard in the shader (AMD / Mesa dropped whole 8 pixel blocks around discarded pixels) */
  int L = 0; lk_glEnable(0x0C11);
  while (L < 224) { const uint8_t *q = lk_gc_rowsu + L * 64; int w, L1; if ((q[4] & 0x60) != 0x60) { L++; continue; } w = q[10] | (q[11] << 8); L1 = L + 1;
    while (L1 < 224 && (lk_gc_rowsu[L1 * 64 + 4] & 0x60) == 0x60 && (lk_gc_rowsu[L1 * 64 + 10] | (lk_gc_rowsu[L1 * 64 + 11] << 8)) == w) L1++;
    lk_glScissor(0, L + yoff, w, L1 - L); lk_glDrawArrays(0x0005, 0, 4); L = L1; }
  lk_glDisable(0x0C11); }
static void lk_gc_real2(lkGLuint tcls, lkGLuint tpost) {   /* 4d, inside the real light pass after its class / mix uploads: the GPU lines' class tags and mixes after the light */
  static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 }; lkGLint fb0 = 0, tb[LK_GC_NT], vp[4], prog = 0, act = 0; int i;
  if (lk_gc_r2fr != platform_frame_number()) return;
  lk_glGetIntegerv(0x84E0, &act); for (i = 0; i < LK_GC_NT; i++) { lk_glActiveTexture(0x84C0 + i); lk_glGetIntegerv(0x8069, &tb[i]); }
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glGetIntegerv(0x0BA2, vp); lk_glGetIntegerv(0x8B8D, &prog);
  lk_glUseProgram(lk_gc_prog); for (i = 0; i < LK_GC_NT; i++) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, i == 11 ? 0 : lk_gc_t[i]); }
  lk_glUniform1f(lk_gc_u[LK_GC_NT + 7], 1.0f); lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad);
  lk_glBindFramebuffer(0x8D40, lk_gc_fbo);
  lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, tcls, 0); lk_glViewport(0, 0, 448, 224); lk_glUniform1f(lk_gc_u[LK_GC_NT + 8], 0.0f); lk_glUniform1f(lk_gc_u[LK_GC_NT], 6.0f); lk_gc_draws(0);
  lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, tpost, 0); lk_glUniform1f(lk_gc_u[LK_GC_NT], 3.0f); lk_glViewport(0, 0, 448, 224); lk_gc_draws(0);
  lk_glUniform1f(lk_gc_u[LK_GC_NT], 4.0f); lk_glUniform1f(lk_gc_u[LK_GC_NT + 8], 224.0f); lk_glViewport(0, 224, 448, 224); lk_gc_draws(224);
  lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_gc_out, 0); lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); lk_glViewport(vp[0], vp[1], vp[2], vp[3]); lk_glUseProgram((lkGLuint)prog);
  for (i = LK_GC_NT - 1; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); }
  lk_glActiveTexture((lkGLenum)act); }
'''.replace("@VER@", VER)
    a = "static int lk_gpu_present(const uint8_t *fb, int sw, const lk_rect *r, int ow, int oh, int fx) {\n"
    assert s.count(a) == 1, "platform_sdl.c: lk_gpu_present not found"
    s = s.replace(a, MODULE + a)
    a = "  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_gpu_tex); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, sw, 224, 0x80E1, 0x1401, fb);\n"   # (was the GPULT compare call lk_glt_pass(0), gone 2026-11-12)
    assert s.count(a) == 1, "platform_sdl.c: picture upload anchor not found (lk_gc_pass)"
    s = s.replace(a, "  lk_gc_pass();   /* %s: compare harness */\n" % VER + a)
    a = "  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_gpu_tex); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, sw, 224, 0x80E1, 0x1401, fb);\n  if (lk_glt_pass(1))"
    assert s.count(a) == 1, "platform_sdl.c: picture upload anchor not found"
    s = s.replace(a, a.replace("\n  if (lk_glt_pass(1))", "\n  lk_gc_real1();   /* %s: real path, the GPU lines */\n  if (lk_glt_pass(1))" % VER))
    a = "  lk_gl_clstag(lk_glt_ct); lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, lk_glt_t[1]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x1908, 0x1401, lk_glt_ct);\n"
    assert s.count(a) == 1, "platform_sdl.c: class tag upload anchor not found"
    s = s.replace(a, a + "  if (real) lk_gc_real2(lk_glt_t[1], lk_glt_t[10]);   /* %s: the GPU lines' class tags + mixes */\n" % VER)
    a = "static int lk_glt_pass(int real) {"
    assert s.count(a) == 1
    s = s.replace(a, "static void lk_gc_real2(lkGLuint tcls, lkGLuint tpost);   /* %s */\n" % VER + a)
    a = "lk_glt_t[1] = lk_glt_tex(448, 224, 0x1908, 0x1908);"   # RGBA since LK_LTHIDE v1 (patch_gpulight.py): the GPU composition renders into it
    assert s.count(a) == 1, "platform_sdl.c: class texture anchor not found"
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)
else:
    print("platform_sdl.c already patched:", VER)
