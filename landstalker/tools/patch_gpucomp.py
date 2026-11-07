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
Console every 300 compared frames: 'gpucomp: frames F lines L pixels P exact E meta-diff M colour-diff C (source counts)' and
'gpucomp: full lines L pixels P exact E colour C class K mix M (water-learn frames W)' + 'gpucomp: lines with: ...' (effect use) + the first 12 differences of each kind.
Needs patch_own.py and the effect patches (bootcol, water, clouds, daynight, modernhud), patch_gpu.py, patch_gpulight.py before it.  Idempotent.  usage: patch_gpucomp.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_GPUCOMP v2"

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
int lk_gc_getmode(void) { if (lk_gc_mode == -2) { const char *e = getenv("LANDSTALKER_GPUCOMP"); lk_gc_mode = e ? atoi(e) : 0; if (lk_gc_mode != 2) lk_gc_mode = 0; } return lk_gc_mode; }
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
  q[4] = (uint8_t)((black_line ? 1 : 0) | (text ? 2 : 0) | (wline ? 4 : 0) | (tb ? 8 : 0) | (nohud ? 16 : 0) | 32); q[5] = (uint8_t)e; q[6] = (uint8_t)wlo; q[7] = (uint8_t)(wlo >> 8);
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
  return 1; }
'''.replace("@VER@", VER)
    a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
    rep(a, MODULE + a)
    a = "    int lk_cs_ln = lk_cs_linebegin();   /* LK_CLOUDS v1 */\n"
    rep(a, a + "    int lk_gc_ln = lk_gc_getmode() == 2 && lk_gc_linebegin(line, w, e, ubase - e - lk_sm_sxn, vbase - lk_sm_syn, black_line, text, wline, tb, nohud, wlo, whi, hint,\n"
           "      (lk_bc_ln ? 1 : 0) | (lk_wr_ln ? 2 : 0) | (lk_cs_ln ? 4 : 0) | ((lk_lt_ln && lk_dn_win) ? 8 : 0) | ((lk_gl_real && !lk_sfx_ln && !lk_dz_ln && !lk_hz_ln) ? 16 : 0));   /* @VER@ */\n"
           "    if (lk_gc_ln) { lk_gc_fx[0] += lk_bc_ln != 0; lk_gc_fx[1] += lk_wr_ln != 0; lk_gc_fx[2] += lk_cs_ln != 0; lk_gc_fx[3] += lk_hz_ln != 0; lk_gc_fx[4] += lk_dz_ln != 0; lk_gc_fx[5] += lk_sfx_ln != 0; lk_gc_fx[6] += nohud != 0; lk_gc_fx[7] += lk_ss_frac != 0; lk_gc_fx[8] += lk_hd_n != 0; lk_gc_fx[9] += fxon != 0; lk_gc_fx[10] += (lk_lt_ln && lk_dn_win) != 0; lk_gc_fx[11] += lk_gl_real != 0; }   /* @VER@: which effects the lines use */\n".replace("@VER@", VER))
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
void lk_gc_water(int *tk, int *pal, int *idx) { *tk = lk_wr_tk > 0 ? lk_wr_tk : 0; *pal = lk_wr_pal; *idx = lk_wr_idx; }
const uint8_t *lk_gc_clouds(int *ox8, int *oy8, int *kf) { *ox8 = lk_cs_ox >> 3; *oy8 = lk_cs_oy >> 3; *kf = lk_cs_kf; return lk_cs_tex; }   /* 128 x 128 */
void lk_gc_mhud(uint8_t *o, int *y0, int *y1) { int y, x; *y0 = lk_mh_y0; *y1 = lk_mh_y1;   /* 464 x 240 RGBA: colour + alpha */
  for (y = 0; y < LK_MH_H; y++) for (x = 0; x < LK_MH_W; x++) { uint8_t *q = o + 4 * (y * LK_MH_W + x); int a = (y >= lk_mh_y0 && y <= lk_mh_y1) ? lk_mh_a[y][x] : 0; uint32_t c = (uint32_t)lk_mh_c[y][x];
    q[0] = (uint8_t)(c >> 16); q[1] = (uint8_t)(c >> 8); q[2] = (uint8_t)c; q[3] = (uint8_t)a; } }
void lk_gc_dnmask(float *m) { int k, y; for (k = 0; k < 6; k++) for (y = 0; y < 8; y++) m[k * 8 + y] = (float)lk_dn_wm[k][y]; }
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
extern void lk_gc_mhud(uint8_t *o, int *y0, int *y1); extern void lk_gc_dnmask(float *m); extern int lk_gc_figs(float *f); extern int lk_gc_learned(void);
static const char *lk_gc_fs = "#version 120\n"
"uniform sampler2D rows; uniform sampler2D pal; uniform sampler2D win; uniform sampler2D spr; uniform sampler2D pln; uniform sampler2D til;\n"
"uniform sampler2D wcl; uniform sampler2D wrb; uniform sampler2D rip; uniform sampler2D mhd; uniform sampler2D cst;\n"
"uniform float uMode; uniform vec4 uFig[8]; uniform float uNf; uniform vec4 uDnM[12]; uniform vec3 uCs; uniform vec3 uWr; uniform vec2 uMh;\n"
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
"  return vec4(mod(ix, 2.0) < 0.5 ? floor(b / 16.0) : mod(b, 16.0), mod(floor(hi / 32.0), 4.0), floor(hi / 128.0), t); }\n"
"vec3 boot(vec3 c, float pk, float line) {\n"   /* lk_bc_tint */
"  float k = -1.0; pk = mod(pk, 64.0); if (pk == 40.0) k = 0.0; else if (pk == 35.0) k = 1.0; else if (pk == 36.0) k = 2.0; else if (pk == 37.0) k = 3.0; if (k < 0.0) return c;\n"
"  vec3 o = by3(rowt(8.0 + k, line).rgb), b = by3(rowt(12.0 + k, line).rgb); float sb = b.r + b.g + b.b, sc = c.r + c.g + c.b; if (sb <= 0.0) return c;\n"
"  return min(floor((o * sc + floor(sb / 2.0)) / sb), vec3(255.0)); }\n"
"vec3 winpix(vec3 c, float pick, float t, vec2 ixy, float w) {\n"   /* lk_dn_winpix */
"  float idx = mod(pick, 16.0), k = -1.0; if (pick >= 16.0 || (idx != 1.0 && idx != 14.0)) return c;\n"
"  if (t == 195.0) k = 0.0; else if (t == 196.0) k = 1.0; else if (t == 199.0) k = 2.0; else if (t == 200.0) k = 3.0; else if (t == 210.0) k = 4.0; else if (t == 211.0) k = 5.0; if (k < 0.0) return c;\n"
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
"  vec2 fc = floor(gl_FragCoord.xy); float i = fc.x, line = fc.y;\n"
"  vec4 r0 = rowt(0.0, line), r1 = rowt(1.0, line), r2 = rowt(2.0, line), r3 = rowt(3.0, line), r4 = rowt(4.0, line), r7 = rowt(7.0, line);\n"
"  float fl = by(r1.r), w = u16(r2.b, r2.a), f2 = by(r7.r);\n"
"  if (bit(fl, 5.0) < 0.5 || i >= w) { gl_FragColor = vec4(0.0); return; }\n"
"  bool bline = bit(fl, 0.0) > 0.5, text = bit(fl, 1.0) > 0.5, wline = bit(fl, 2.0) > 0.5, tb = bit(fl, 3.0) > 0.5, nohud = bit(fl, 4.0) > 0.5;\n"
"  float U0 = s16(r0.r, r0.g), V = s16(r0.b, r0.a), e = by(r1.g), wlo = u16(r1.b, r1.a), whi = u16(r2.r, r2.g), sxn = s16(r3.r, r3.g), syn = s16(r3.b, r3.a);\n"
"  float x = i - e; bool margin = x < 0.0 || x >= 320.0;\n"
"  float sl = line - syn, si = i - sxn, sp = 0.0;\n"
"  if (sl >= 0.0 && sl < 224.0 && si >= 0.0 && si < 448.0) { vec4 t = texture2D(spr, vec2((si + 0.5) / 448.0, (sl + 0.5) / 224.0)); sp = by(t.r) + 256.0 * by(t.a); }\n"
"  bool s200 = bit(sp, 9.0) > 0.5, s100 = bit(sp, 8.0) > 0.5, s400 = bit(sp, 10.0) > 0.5;\n"
"  bool black = bline; float pick = 0.0, src = 0.0, tile = 0.0; vec2 ixy = vec2(0.0);\n"
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
"      if (wp >= 0.0 && mod(wp, 16.0) > 0.0 && i >= wlo && i < whi) { if (!(text && s200 && s100 && !s400 && bit(wp, 9.0) < 0.5)) { pick = mod(wp, 64.0); src = 4.0; } }\n"
"      else if (wp >= 0.0 && !tb && wline) black = true; } }\n"
"  float k = 0.0;\n"   /* lk_gl_classify */
"  if (!black) { if (src >= 1.0 && src <= 3.0) { k = 1.0; if (src == 1.0 && s200) { for (int j = 0; j < 16; j++) { if (float(j) >= uNf) break; vec4 fv = uFig[j / 2]; vec2 fj = (j - 2 * (j / 2)) == 0 ? fv.xy : fv.zw; float dx = x - fj.x, dy = fj.y - line; if (dx >= -16.0 && dx <= 16.0 && dy >= -6.0 && dy <= 56.0) { k = 16.0 + float(j); break; } } } }\n"
"    else if (src == 0.0) k = 3.0; }\n"
"  if (uMode > 0.5 && uMode < 1.5) { float m = black ? 512.0 : pick + 64.0 * src; gl_FragColor = vec4(mod(m, 256.0) / 255.0, floor(m / 256.0) / 255.0, k / 255.0, 1.0); return; }\n"
"  vec3 col = black ? by3(margin ? rowt(5.0, line).rgb : rowt(6.0, line).rgb) : by3(texture2D(pal, vec2((pick + 0.5) / 64.0, (line + 0.5) / 224.0)).rgb);\n"
"  if (uMode < 0.5) { gl_FragColor = vec4(col / 255.0, 1.0); return; }\n"
"  vec3 p0 = vec3(0.0), p1 = vec3(255.0); float bk = by(r7.g), dnw = by(r7.b);\n"
"  if (bit(f2, 0.0) > 0.5 && !black && src == 1.0 && bit(sp, 11.0) > 0.5 && bk >= 5.0 && bk <= 8.0) col = boot(col, sp, line);\n"
"  if (bit(f2, 3.0) > 0.5 && !black && (src == 2.0 || src == 3.0)) { vec3 c2 = winpix(col, pick, tile, ixy, dnw); if (c2 != col) { p0 = winpix(p0, pick, tile, ixy, dnw); p1 = winpix(p1, pick, tile, ixy, dnw); } }\n"
"  if (bit(f2, 1.0) > 0.5 && !black && (src == 2.0 || src == 3.0)) col = water(col, pick, tile, line, i, bit(f2, 5.0) > 0.5);\n"
"  if (bit(f2, 2.0) > 0.5 && !black && src >= 1.0 && src <= 3.0) col = cloud(col, U0 + i, V);\n"
"  if (nohud) { if (k > 0.0) { vec3 cc = mh(col, line, i); if (cc != col) { p0 = mh(p0, line, i); p1 = mh(p1, line, i); } } else col = mh(col, line, i); }\n"
"  gl_FragColor = vec4((uMode < 2.5 ? col : uMode < 3.5 ? p0 : p1) / 255.0, 1.0); }\n";
#define LK_GC_NT 11
static int lk_gc_st; static lkGLuint lk_gc_prog, lk_gc_fbo, lk_gc_out, lk_gc_t[LK_GC_NT]; static lkGLint lk_gc_u[LK_GC_NT + 8];
static long lk_gc_n, lk_gc_lines, lk_gc_px, lk_gc_ex, lk_gc_md, lk_gc_cd, lk_gc_src[6], lk_gc_fl, lk_gc_fpx, lk_gc_fex, lk_gc_fc, lk_gc_fk, lk_gc_fm, lk_gc_learn, lk_gc_fchg, lk_gc_ffig, lk_gc_fmix; static int lk_gc_shown, lk_gc_fshown;
static int lk_gc_init(void) {
  static const char *un[] = { "rows", "pal", "win", "spr", "pln", "til", "wcl", "wrb", "rip", "mhd", "cst", "uMode", "uFig", "uNf", "uDnM", "uCs", "uWr", "uMh" }; lkGLint ok = 0; lkGLuint vs, fs; char log[2048]; int i;
  static const int tw[LK_GC_NT] = { 16, 64, 320, 448, 304, 1024, 48, 448, 448, 464, 128 }, th[LK_GC_NT] = { 224, 224, 224, 224, 304, 72, 48, 224, 224, 240, 128 };
  static const lkGLenum tf[LK_GC_NT] = { 0x1908, 0x1908, 0x190A, 0x190A, 0x1908, 0x1909, 0x1909, 0x1908, 0x190A, 0x1908, 0x1909 };
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
  for (i = 0; i < LK_GC_NT + 7; i++) lk_gc_u[i] = lk_glGetUniformLocation(lk_gc_prog, un[i]);
  for (i = 0; i < LK_GC_NT; i++) { lk_glActiveTexture(0x84C0 + i); lk_gc_t[i] = lk_glt_tex(tw[i], th[i], tf[i], tf[i]); }
  lk_glActiveTexture(0x84C0); lk_gc_out = lk_glt_tex(448, 224, 0x1908, 0x1908);
  lk_glGenFramebuffers(1, &lk_gc_fbo); lk_glBindFramebuffer(0x8D40, lk_gc_fbo); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_gc_out, 0);
  ok = lk_glCheckFramebufferStatus(0x8D40) == 0x8CD5; lk_glBindFramebuffer(0x8D40, 0);
  { lkGLenum e = lk_glGetError(); if (e || !ok) { printf("gpucomp: setup failed (GL error %04X, fbo %d)\n", (unsigned)e, ok); return -1; } }
  printf("gpucomp: @VER@ compare harness ready (LANDSTALKER_GPUCOMP=2)\n");
  return 1; }
static void lk_gc_pass(void) {   /* inside lk_gpu_present after SDL's state is saved (texture unit 0 active, unpack alignment 4) */
  static uint8_t pl[304 * 304 * 4], rows[224 * 64], rb[5][224 * 448 * 4], wc[48 * 48], mhb[464 * 240 * 4]; static uint16_t sprb[224 * 448]; static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 };
  lkGLint fb0 = 0, tb[LK_GC_NT], vp[4]; long fr = platform_frame_number(); int i, L, k, nl = 0, tk, wpal, widx, ox8, oy8, kf, my0, my1, nf, learn; const uint32_t *pa, *pb; const uint8_t *cst; float fig[32], dnm[48];
  if (lk_gc_getmode() != 2 || lk_gc_st < 0 || lk_gc_capfr != fr - 1) return;
  for (i = 0; i < LK_GC_NT; i++) { lk_glActiveTexture(0x84C0 + i); lk_glGetIntegerv(0x8069, &tb[i]); }
  if (lk_gc_st == 0) { lk_gc_st = lk_gc_init(); if (lk_gc_st < 0) { for (i = LK_GC_NT - 1; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); } return; } }
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glGetIntegerv(0x0BA2, vp);
  memcpy(rows, lk_gc_rows, sizeof rows); for (L = 0; L < 224; L++) if (lk_gc_rowfr[L] != lk_gc_capfr) rows[L * 64 + 4] = 0; else nl++;   /* lines not recorded this frame: skipped */
  pa = lk_gc_planes(); pb = lk_gc_planesb();
  for (k = 0; k < 2; k++) { const uint32_t *P = k ? pb : pa; uint8_t *o = pl + k * 152 * 304 * 4; for (i = 0; i < 152 * 304; i++) { uint32_t c = P[i]; o[4 * i] = (uint8_t)c; o[4 * i + 1] = (uint8_t)(c >> 8); o[4 * i + 2] = (c & 0x10000) ? 255 : 0; o[4 * i + 3] = 255; } }
  lk_gc_sprb(sprb); lk_gc_wclass(wc); lk_gc_water(&tk, &wpal, &widx); cst = lk_gc_clouds(&ox8, &oy8, &kf); lk_gc_mhud(mhb, &my0, &my1); lk_gc_dnmask(dnm); nf = lk_gc_figs(fig);
  learn = lk_gc_learned();
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
  lk_glUseProgram(lk_gc_prog); for (i = 0; i < LK_GC_NT; i++) lk_glUniform1i(lk_gc_u[i], i);
  lk_glUniform4fv(lk_gc_u[LK_GC_NT + 1], 8, fig); lk_glUniform1f(lk_gc_u[LK_GC_NT + 2], (float)nf); lk_glUniform4fv(lk_gc_u[LK_GC_NT + 3], 12, dnm);
  lk_glUniform3f(lk_gc_u[LK_GC_NT + 4], (float)ox8, (float)oy8, (float)kf); lk_glUniform3f(lk_gc_u[LK_GC_NT + 5], (float)tk, (float)wpal, (float)widx); lk_glUniform2f(lk_gc_u[LK_GC_NT + 6], (float)my0, (float)my1);
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
'''.replace("@VER@", VER)
    a = "static int lk_gpu_present(const uint8_t *fb, int sw, const lk_rect *r, int ow, int oh, int fx) {\n"
    assert s.count(a) == 1, "platform_sdl.c: lk_gpu_present not found"
    s = s.replace(a, MODULE + a)
    a = "  lk_glt_pass(0);   /* LK_GPULT v5: compare harness */\n"
    assert s.count(a) == 1, "platform_sdl.c: lk_glt_pass(0) anchor not found"
    s = s.replace(a, "  lk_gc_pass();   /* %s: compare harness */\n" % VER + a)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)
else:
    print("platform_sdl.c already patched:", VER)
