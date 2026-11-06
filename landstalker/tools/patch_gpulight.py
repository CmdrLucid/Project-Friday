#!/usr/bin/env python3
"""GPU lighting, stage GL1 (2026-11-06, user: '1 umsetzen danach 2' = lighting on the GPU, docs/RENDERER_IDEAS.md 'Step 3 plan: deferred lighting').
GL1 = the harness, NOTHING changes for the player: with LANDSTALKER_GPULT=2 (compare mode, test aid) the own map renderer records per picture pixel
(1) the colour BEFORE Lighting (lk_lt_pix / lk_lt_voidglow), (2) the colour after it (the CPU result), (3) a light class (0 none, 1 lk_lt_pix,
3 lk_lt_voidglow) + flags of the paths GL1 does not do yet, and per line the room picture position (U = ru + i, V = rv).  At the next present the GPU
lights the recorded unlit picture in an offscreen pass (FBO 448 x 224, one fragment shader) from the light block cache (lk_lt_b, uploaded per 32 x 32
block as a room picture texture face / sun / sunn / ao) and the frame's light state; the result is read back and compared with the CPU colours.
GL1 covers: blocks not computed yet (base light), outdoor sun + Day / Night (incl. the crossfade to the next sun direction), corner shadows (ao),
pixels without geometry.  GL2 (v2) adds: flame terms with flicker, lava, window lights (lava 2), sword glow, key light rooms (fast path with the finished
light km and the slow path), shaft pools and the beam glow, figure pixels (lit at their card).  GL3 (v3) adds: figure sun / key shadows, figure flame
shadows (every pixel: the CPU's 'every 2nd pixel' shortcut LANDSTALKER_LT_SHHALF must be 0 for an exact compare), figure shade in a shaft pool, dust motes,
ambient particles.  The flags (2 / 8 / 16 / 32 / 64) are kept for the per-path statistics only.
GL4 (v4) = THE REAL PATH (default with Options > Display > GPU Filters On; LANDSTALKER_GPULT=0 = CPU lighting, =2 = the compare harness): the row compositor
skips lk_lt_pix / lk_lt_voidglow and keeps their side effects (prefetch area, block requests), the figure of a figure pixel (lk_lt_figat) and the class;
surface effects after the light point (water, cloud shadows, heat haze, de-dither) stay in the unlit picture and are lit with it; emissive mixes
(lit window glass, sword effects, enemy dissolve, the Modern HUD with its soft edges) are recorded as 'mix after the light' (the chain applied to black and to white = offset and slope per
channel) and applied by the GPU after lighting.  The GPU lights the presented 1x picture (the filter's source texture) into
an FBO texture that the filter shader then samples.  If the GPU fails, lk_gpu_lightok() turns the CPU lighting back on from the next frame.
Console every 300 compared frames: 'gpult: frames F skipped S pixels P exact E off1 O1 worse W excluded X (fig A figsun B flame C particle D)'
plus the first 12 pixels with a difference > 1 ('gpult: diff frame .. x .. line .. U .. V .. class .. cpu RRGGBB gpu RRGGBB unlit RRGGBB').
Needs the GPU filter path (patch_gpu.py, option GPU Filters On) and a window (the GL context): LANDSTALKER_HIDDEN=1 creates the window hidden (test aid).
Needs patch_lights.py, patch_bootcol.py, patch_gpu.py before it.  Idempotent.  usage: patch_gpulight.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_GPULT v4"

# ---------------------------------------------------------------- vdp_render.c: capture + block access
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, ("vdp_render.c: anchor not found once", a[:90], s.count(a))
    s = s.replace(a, b)

if VER not in s:
    MODULE = r'''/* ---- %s: GPU lighting harness (tools/patch_gpulight.py): capture of the unlit / lit map pixels + access to the light block cache ---- */
static int lk_gl_mode = -1;   /* LANDSTALKER_GPULT: 0 CPU lighting, 1 GPU lighting (default; only while the GPU path works), 2 compare harness */
int (*lk_gl_okfn)(void);      /* platform_sdl.c: lk_gpu_lightok (GPU filters on and working) */
static long lk_gl_okfr = -1; static int lk_gl_okv;
static int lk_gl_realok(void) { long f = platform_frame_number(); if (f != lk_gl_okfr) { lk_gl_okfr = f; lk_gl_okv = lk_gl_okfn && lk_gl_okfn(); } return lk_gl_okv; }
uint32_t lk_gl_post[2][224 * 448]; int lk_gl_postany; static long lk_gl_postfr = -1;   /* (identity = 0 / 0xFFFFFF, see lk_gl_postinit) */
static int lk_gl_postok; static void lk_gl_postinit(void) { int i; for (i = 0; i < 224 * 448; i++) lk_gl_post[1][i] = 0xFFFFFFu; lk_gl_postok = 1; }   /* GL4: mix after the light (chain applied to black / to white) */
static int lk_gl_pf;          /* flags of the current lk_lt_pix call: 1 figure pixel, 2 figure sun / key shadow, 4 a flame term, 8 particle, 16 figure flame shadow, 32 figure shade in a pool, 64 dust mote */
static unsigned lk_gl_sunver; /* bumped when the blocks take over the next sun direction (memcpy sun <- sunn) */
uint32_t lk_gl_unlit[224 * 448], lk_gl_ref[224 * 448]; uint8_t lk_gl_cls[224 * 448], lk_gl_flg[224 * 448]; uint32_t lk_gl_row[224]; long lk_gl_rowfr[224]; int lk_gl_w; long lk_gl_capfr = -9;
int lk_gl_getmode(void) { if (lk_gl_mode < 0) { const char *e = getenv("LANDSTALKER_GPULT"); lk_gl_mode = e ? atoi(e) : 1; if (lk_gl_mode < 0 || lk_gl_mode > 2) lk_gl_mode = 0; } return lk_gl_mode; }
static void lk_gl_put(int line, int i, int cls, int U, int V, int c0, int c1, int w) {
  int o = line * 448 + i;
  int q = ((V & 511) << 9) | (U & 511);
  if (cls == 1 && (lk_gl_pf & 1)) cls = 16 + lk_gl_fj;   /* a figure pixel: class 16 + figure */
  lk_gl_unlit[o] = (uint32_t)c0; lk_gl_ref[o] = (uint32_t)c1; lk_gl_cls[o] = (uint8_t)cls;
  lk_gl_flg[o] = (uint8_t)(cls ? (lk_gl_pf | ((lk_am_dn && lk_am_map[q]) ? 8 : 0) | ((lk_lt_nsh && lk_lt_dmap[q]) ? 64 : 0)) : 0);
  if (i == 0 || lk_gl_rowfr[line] != platform_frame_number()) { lk_gl_row[line] = ((uint32_t)(uint16_t)(int16_t)(U - i)) | ((uint32_t)(uint16_t)(int16_t)V << 16); lk_gl_rowfr[line] = platform_frame_number(); }
  lk_gl_capfr = platform_frame_number(); lk_gl_w = w; }
static int lk_gl_pl[224 * 448], lk_gl_pn; int lk_gl_postprev;   /* GL4: pixels with a mix after the light this frame (reset to 'none' at the next frame) */
static void lk_gl_line(int line, int u0, int v, int w) {   /* GL4, once per captured line: picture position (U = u0 + i, V) + frame stamps */
  long f = platform_frame_number(); int j;
  if (lk_gl_postfr != f) { lk_gl_postfr = f; lk_gl_postprev = lk_gl_postany; lk_gl_postany = 0; for (j = 0; j < lk_gl_pn; j++) { lk_gl_post[0][lk_gl_pl[j]] = 0; lk_gl_post[1][lk_gl_pl[j]] = 0xFFFFFFu; } lk_gl_pn = 0; }
  lk_gl_row[line] = ((uint32_t)(uint16_t)(int16_t)u0) | ((uint32_t)(uint16_t)(int16_t)v << 16); lk_gl_rowfr[line] = f; lk_gl_capfr = f; lk_gl_w = w; }
static void lk_gl_postset(int o, uint32_t p0, uint32_t p1) { if (lk_gl_pn < 224 * 448) lk_gl_pl[lk_gl_pn++] = o; lk_gl_post[0][o] = p0; lk_gl_post[1][o] = p1; lk_gl_postany = 1; }
static int lk_gl_classify(int x, int line, int src, int sp2, int black, int U, int V) {   /* GL4: what lk_lt_pix would do with this pixel (+ its side effects) */
  int j; if (black) return 0;
  if (src >= 1 && src <= 3) {
    if (U < lk_lt_umin) lk_lt_umin = U; if (U > lk_lt_umax) lk_lt_umax = U; if (V < lk_lt_vmin) lk_lt_vmin = V; if (V > lk_lt_vmax) lk_lt_vmax = V;   /* prefetch area */
    if ((sp2 & 0x200) && (j = lk_lt_figat(x, line)) >= 0) return 16 + j;
    { static int lbx = -99, lby = -99; static long lf = -1; int bx = lk_lt_fdiv(U, 32), by = lk_lt_fdiv(V, 32); long f = platform_frame_number();
      if (bx != lbx || by != lby || f != lf) { lbx = bx; lby = by; lf = f; (void)lk_lt_block(bx, by); } }   /* on-demand blocks (builds without the light worker) */
    return 1; }
  return (src == 0 || src == 6 || src == 7) ? 3 : 0; }
/* for the GL side (platform_sdl.c, once per present): 1 = the last frame was captured; fills the frame's light state.
   fu: 0 amb, 1 sS, 2 sK, 3..5 amb3, 6..8 sun3, 9 dn_mix, 10 kA, 11 kK, 12 fadek, 13..15 shaft colour, 16..19 sword x y z rad, 20..23 sword r g b k;
   iu: 0 sun, 1 key, 2 nl, 3 nsh, 4 swon, 5 dn_on, 6 odcap == 0, 7 width, 8 skip bits (none since v2), 9 nf, 10 nfb > 0, 11 fmall, 12 wide e, 13 particles on;
   lp / lc / lf (96 x 4): light x y z rad / r g b k / flicker, window light (lava 2), 0, 0;  fg / fa (16 x 4): figure fx fy fz sun / ax ay */
int lk_gl_frame(long fr, float *fu, int *iu, float *lp, float *lc, float *lf, float *fg, float *fa) {
  int L, k;
  if (lk_gl_capfr != fr - 1 || lk_gl_w < 1 || lk_gl_w > 448) return 0;
  for (L = 0; L < 224; L++) if (lk_gl_rowfr[L] != lk_gl_capfr) memset(lk_gl_cls + L * 448, 0, 448);   /* lines not captured this frame: no light */
  fu[0] = lk_lt_amb < 0.0f ? 0.85f : lk_lt_amb; fu[1] = lk_lt_sS; fu[2] = lk_lt_sK; for (k = 0; k < 3; k++) { fu[3 + k] = lk_dn_amb3[k]; fu[6 + k] = lk_dn_sun3[k]; } fu[9] = (float)lk_dn_mix;
  iu[0] = lk_lt_sun; iu[1] = lk_lt_key; iu[2] = lk_lt_nl; iu[3] = lk_lt_nsh; iu[4] = lk_lt_swon; iu[5] = lk_dn_on; iu[6] = lk_lt_odcap == 0; iu[7] = lk_gl_w;
  iu[8] = 0;
  fu[10] = lk_lt_kA; fu[11] = lk_lt_kK; fu[12] = lk_lt_fadek; fu[13] = lk_lt_sh[0].cr; fu[14] = lk_lt_sh[0].cg; fu[15] = lk_lt_sh[0].cb;
  fu[16] = lk_lt_sw.x; fu[17] = lk_lt_sw.y; fu[18] = lk_lt_sw.z; fu[19] = lk_lt_sw.rad > 0.0f ? lk_lt_sw.rad : LK_LT_RAD; fu[20] = lk_lt_sw.r; fu[21] = lk_lt_sw.g; fu[22] = lk_lt_sw.b; fu[23] = lk_lt_sw.k > 0.0f ? lk_lt_sw.k : 1.0f;
  iu[9] = lk_lt_nf; iu[10] = lk_lt_nfb > 0; iu[11] = lk_lt_fmall; iu[12] = lk_wide_e; iu[13] = lk_am_dn != 0; iu[14] = lk_lt_nsh;
  fu[24] = lk_lt_sd[0]; fu[25] = lk_lt_sd[1]; fu[26] = lk_lt_sd[2];
  for (k = 0; k < LK_LT_NSH; k++) { const lk_lt_shaft_t *S = &lk_lt_sh[k]; fu[32 + 8 * k] = S->x; fu[33 + 8 * k] = S->y; fu[34 + 8 * k] = S->z; fu[35 + 8 * k] = S->r; fu[36 + 8 * k] = S->d[0]; fu[37 + 8 * k] = S->d[1]; fu[38 + 8 * k] = S->d[2]; fu[39 + 8 * k] = 0.0f; }
  for (k = 0; k < LK_LT_ML; k++) { const lk_lt_light *Lq = &lk_lt_l[k];
    lp[4 * k] = Lq->x; lp[4 * k + 1] = Lq->y; lp[4 * k + 2] = Lq->z; lp[4 * k + 3] = Lq->rad > 0.0f ? Lq->rad : LK_LT_RAD;
    lc[4 * k] = Lq->r; lc[4 * k + 1] = Lq->g; lc[4 * k + 2] = Lq->b; lc[4 * k + 3] = Lq->k > 0.0f ? Lq->k : 1.0f;
    lf[4 * k] = k < lk_lt_nl ? lk_lt_flk[k] : 0.0f; lf[4 * k + 1] = Lq->lava == 2 ? 1.0f : 0.0f; lf[4 * k + 2] = lf[4 * k + 3] = 0.0f; }
  for (k = 0; k < 16; k++) { fg[4 * k] = lk_lt_f[k].fx; fg[4 * k + 1] = lk_lt_f[k].fy; fg[4 * k + 2] = lk_lt_f[k].fz; fg[4 * k + 3] = lk_lt_f[k].sun; fa[4 * k] = (float)lk_lt_f[k].ax; fa[4 * k + 1] = (float)lk_lt_f[k].ay; fa[4 * k + 2] = (float)lk_lt_f[k].tag; fa[4 * k + 3] = 0.0f; }
  return 1; }
const uint16_t *lk_gl_fmk(void) { return &lk_lt_fmk[0][0]; }   /* figure shadow box mask 224 x 448 (lk_lt_infb) */
/* per light k / figure j: row j = card normal x, y, pair, 0; row 16 + j = the shadow box x0 y0 x1 y1 (96 x 32 RGBA floats) */
void lk_gl_pairs(float *o) { int k, j; for (j = 0; j < 16; j++) for (k = 0; k < 96; k++) { float *a = o + 4 * (j * 96 + k), *b = o + 4 * ((16 + j) * 96 + k);
  a[0] = lk_lt_pn[k][j][0]; a[1] = lk_lt_pn[k][j][1]; a[2] = lk_lt_pair[k][j] ? 1.0f : 0.0f; a[3] = 0.0f; b[0] = (float)lk_lt_pbox[k][j][0]; b[1] = (float)lk_lt_pbox[k][j][1]; b[2] = (float)lk_lt_pbox[k][j][2]; b[3] = (float)lk_lt_pbox[k][j][3]; } }
/* class + own-sprite tag per screen pixel (luminance / alpha): the silhouettes of the figure shadows */
void lk_gl_clstag(uint16_t *o) { int y, x; for (y = 0; y < 224; y++) for (x = 0; x < 448; x++) o[y * 448 + x] = (uint16_t)(lk_gl_cls[y * 448 + x] | (((lk_o_spr[y][x] & 0x200) ? lk_lt_spre[y][x] : 0) << 8)); }
/* dust motes (dmap | dmz << 8) and particle depths (mz | md << 16) as RGBA words, 512 x 512 */
const uint32_t *lk_gl_am(void) { return lk_am_map; }
#define LK_GL_BB(q) { int bx_ = (q) & 511, by_ = (q) >> 9; if (bx_ < bb[0]) bb[0] = bx_; if (bx_ > bb[2]) bb[2] = bx_; if (by_ < bb[1]) bb[1] = by_; if (by_ > bb[3]) bb[3] = by_; }
static int lk_gl_mpl[LK_LT_NSH * LK_LT_NMO * 2], lk_gl_mpn, lk_gl_apl[LK_AM_N * 10], lk_gl_apn;
void lk_gl_motes(uint32_t *o, int *bb) { int j, q; bb[0] = bb[1] = 512; bb[2] = bb[3] = -1;   /* only the texels of this frame's and the last frame's motes (bb = the box to upload) */
  for (j = 0; j < lk_gl_mpn; j++) { q = lk_gl_mpl[j]; o[q] = 0; LK_GL_BB(q) }
  for (j = 0; j < lk_lt_dn; j++) { q = lk_lt_dl[j]; o[q] = (uint32_t)lk_lt_dmap[q] | ((uint32_t)(uint16_t)lk_lt_dmz[q] << 8); lk_gl_mpl[j] = q; LK_GL_BB(q) } lk_gl_mpn = lk_lt_dn; }
void lk_gl_amzd(uint32_t *o, int *bb) { int j, q; bb[0] = bb[1] = 512; bb[2] = bb[3] = -1;
  for (j = 0; j < lk_gl_apn; j++) { q = lk_gl_apl[j]; o[q] = 0; LK_GL_BB(q) }
  for (j = 0; j < lk_am_dn; j++) { q = lk_am_dl[j]; o[q] = (uint32_t)(uint16_t)lk_am_mz[q] | ((uint32_t)(uint16_t)lk_am_md[q] << 16); lk_gl_apl[j] = q; LK_GL_BB(q) } lk_gl_apn = lk_am_dn; }
/* block version (0 = no block) and its packed plane A: face | sun << 8 | sunn << 16 | ao << 24 per pixel (row-major 32 x 32) */
unsigned lk_gl_bver(int bx, int by) { const lk_lt_blk *b; uintptr_t v;
  if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH || !(b = lk_lt_b[by][bx])) return 0;
  v = (uintptr_t)b; return ((unsigned)v ^ (unsigned)(v >> 32) ^ ((unsigned)b->sungen * 2654435761u) ^ (lk_gl_sunver * 40503u) ^ ((unsigned)lk_lt_gen * 97u)) | 1u; }
int lk_gl_bsg(int bx, int by) { const lk_lt_blk *b; if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH || !(b = lk_lt_b[by][bx])) return 0; return b->sungen == lk_dn_gen; }
/* planes (row-major 32 x 32, RGBA bytes): 0 face sun sunn ao, 1 term 0..3, 2 term 4..7, 3 z lo / hi beam pool, 4 key light km (low bytes + 2 high bits each) */
void lk_gl_bpack(int bx, int by, uint32_t (*o)[1024]) { const lk_lt_blk *b = lk_lt_b[by][bx]; int i, k;
  for (i = 0; i < 1024; i++) { uint32_t t0 = 0, t1 = 0; uint16_t z = (uint16_t)b->z[i];
    for (k = 0; k < 4; k++) { if (k < b->nl) t0 |= (uint32_t)b->term[k][i] << (8 * k); if (k + 4 < b->nl) t1 |= (uint32_t)b->term[k + 4][i] << (8 * k); }
    o[0][i] = (uint32_t)b->face[i] | ((uint32_t)b->sun[i] << 8) | ((uint32_t)b->sunn[i] << 16) | ((uint32_t)b->ao[i] << 24); o[1][i] = t0; o[2][i] = t1;
    o[3][i] = (uint32_t)(z & 255) | ((uint32_t)(z >> 8) << 8) | ((uint32_t)b->beam[i] << 16) | ((uint32_t)b->pool[i] << 24);
    o[4][i] = (uint32_t)(b->km[0][i] & 255) | ((uint32_t)(b->km[1][i] & 255) << 8) | ((uint32_t)(b->km[2][i] & 255) << 16) | ((uint32_t)(((b->km[0][i] >> 8) & 3) | (((b->km[1][i] >> 8) & 3) << 2) | (((b->km[2][i] >> 8) & 3) << 4)) << 24); } }
void lk_gl_blist(int bx, int by, uint32_t *a, uint32_t *b2, int *nl) { const lk_lt_blk *b = lk_lt_b[by][bx]; int k; *a = *b2 = 0; *nl = b->nl;
  for (k = 0; k < 4; k++) { if (k < b->nl) *a |= (uint32_t)b->li[k] << (8 * k); if (k + 4 < b->nl) *b2 |= (uint32_t)b->li[k + 4] << (8 * k); } }

''' % VER
    a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
    rep(a, MODULE + a)
    a = "/* ---- LK_LIGHTS v8: lighting from flames"
    rep(a, "static int lk_gl_pf, lk_gl_fj; static unsigned lk_gl_sunver;   /* %s (tools/patch_gpulight.py): used inside the Lighting code */\n" % VER + a)
    # per line: capture on?
    a = "int lk_lt_ln = lk_lt_linebegin();"
    rep(a, a + " int lk_gl_cap = (lk_gl_getmode() == 2 || (lk_gl_mode == 1 && lk_gl_realok())) && lk_lt_ln && !lk_hd_n && !lk_lt_dbg && w <= 448 && line >= 0 && line < 224, lk_gl_real = lk_gl_cap && lk_gl_mode == 1;   /* %s */" % VER +
           " if (lk_gl_real) { if (!lk_gl_postok) lk_gl_postinit(); lk_gl_line(line, ubase - e - lk_sm_sxn, vbase - lk_sm_syn, w); }")
    # around the lighting call of the composed pixel
    a = "      if (lk_lt_ln && !black && (src == 1 || src == 2 || src == 3)) col = lk_lt_pix("
    rep(a, "      int lk_gl_c0 = col, lk_gl_k = 0; uint32_t lk_gl_p0 = 0, lk_gl_p1 = 0xFFFFFFu; lk_gl_pf = 0;   /* %s */\n" % VER +
           "      if (lk_gl_real) lk_gl_k = lk_gl_classify(x, line, src, src == 1 ? sp : 0, black, ubase + x - lk_sm_sxn, vbase - lk_sm_syn);   /* GL4: the GPU lights it */\n      else " + a.lstrip())
    a = "      else if (lk_lt_ln && !black && (src == 0 || src == 6 || src == 7)) col = lk_lt_voidglow("
    i0 = s.index(a); i1 = s.index("\n", i0) + 1
    s = s[:i1] + ("      if (lk_gl_cap && !lk_gl_real) lk_gl_put(line, i, black ? 0 : (src >= 1 && src <= 3) ? 1 : (src == 0 || src == 6 || src == 7) ? 3 : 0, ubase + x - lk_sm_sxn, vbase - lk_sm_syn, lk_gl_c0, col, w);   /* %s */\n" % VER) + s[i1:]
    # flags inside lk_lt_pix
    rep("if ((sp & 0x200) && (j = lk_lt_figat(x, line)) >= 0) {", "if ((sp & 0x200) && (j = lk_lt_figat(x, line)) >= 0) { lk_gl_pf |= 1;")
    rep("if (lk_lt_figsun(px, py, (float)b->z[i])) u = 0.0f; }", "if (lk_lt_figsun(px, py, (float)b->z[i])) { u = 0.0f; lk_gl_pf |= 2; } }")
    rep("      if (t <= 0.0f) continue;\n", "      if (t <= 0.0f) continue;\n      lk_gl_pf |= 4;   /* %s */\n" % VER)
    rep("if ((sp & 0x200) && (j = lk_lt_figat(x, line)) >= 0) { lk_gl_pf |= 1;", "if ((sp & 0x200) && (j = lk_lt_figat(x, line)) >= 0) { lk_gl_pf |= 1; lk_gl_fj = j;")
    rep("if (lk_lt_figsun(px, py, (float)b->z[i])) u *= 0.45f; }", "if (lk_lt_figsun(px, py, (float)b->z[i])) { u *= 0.45f; lk_gl_pf |= 2; } }")
    rep("if (w >= 1.0f) { tb += t; continue; }", "if (w > 0.0f) lk_gl_pf |= 16; if (w >= 1.0f) { tb += t; continue; }")
    rep("if (sh > 0.0f) { float cd = 1.0f - 0.30f * sh;", "if (sh > 0.0f) { float cd = 1.0f - 0.30f * sh; lk_gl_pf |= 32;")
    rep("memcpy(lk_lt_sd, lk_lt_sdn, sizeof lk_lt_sd);", "memcpy(lk_lt_sd, lk_lt_sdn, sizeof lk_lt_sd); lk_gl_sunver++;")
    # GL4: emissive mixes after the light point -> 'mix after the light' (applied to black and white) when the GPU lights the pixel
    def fx(cond, call):
        X = call.replace("@", "col")
        P0 = call.replace("@", "(int)(0xFF000000u | lk_gl_p0)"); P1 = call.replace("@", "(int)(0xFF000000u | lk_gl_p1)")
        T = call.replace("@", "col")
        rep("      if (%s) col = %s;" % (cond, X), "      if (%s) { if (lk_gl_k) { if (%s != col) { lk_gl_p0 = (uint32_t)%s & 0xFFFFFFu; lk_gl_p1 = (uint32_t)%s & 0xFFFFFFu; } } else col = %s; }   /* %s */" % (cond, T, P0, P1, X, VER))
    fx("lk_lt_ln && lk_dn_win && !black && (src == 2 || src == 3)", "lk_dn_winpix(src == 2 ? &afi : &bfi, pick, @)")
    fx("lk_sfx_ln && !black && src != 4", "lk_sfx_pix(line, i, src == 1 ? sp : 0, @)")
    fx("lk_dz_ln && !black && src != 4", "lk_dz_pix(line, i, @)")
    a = "      lk_mh_hit = nohud ? lk_mh_pix(line, i, &col) : 0;"
    rep(a, "      if (lk_gl_k && nohud) { int cc = col; lk_mh_hit = lk_mh_pix(line, i, &cc); if (cc != col) { int q0 = (int)(0xFF000000u | lk_gl_p0), q1 = (int)(0xFF000000u | lk_gl_p1); lk_mh_pix(line, i, &q0); lk_mh_pix(line, i, &q1); lk_gl_p0 = (uint32_t)q0 & 0xFFFFFFu; lk_gl_p1 = (uint32_t)q1 & 0xFFFFFFu; } }   /* %s: the Modern HUD (soft edges) mixes after the light */\n      else " % VER + a.lstrip() +
           "\n      if (lk_gl_real) { lk_gl_cls[line * 448 + i] = (uint8_t)lk_gl_k; if (lk_gl_k && (lk_gl_p0 != 0 || lk_gl_p1 != 0xFFFFFFu)) lk_gl_postset(line * 448 + i, lk_gl_p0, lk_gl_p1); }   /* %s */" % VER)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
else:
    print("vdp_render.c already patched:", VER)

# ---------------------------------------------------------------- platform_sdl.c: the GPU pass + compare
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()

SHADER = r'''
uniform sampler2D unl; uniform sampler2D cls; uniform sampler2D rows; uniform sampler2D roomA; uniform sampler2D btab;
uniform sampler2D roomT0; uniform sampler2D roomT1; uniform sampler2D roomB; uniform sampler2D roomK; uniform sampler2D bli; uniform sampler2D post; uniform sampler2D fmk; uniform float uPost;
uniform sampler2D pairs; uniform sampler2D motes; uniform sampler2D amap; uniform sampler2D amzd;
uniform float uAmb; uniform float uSS; uniform float uSK; uniform vec3 uAmb3; uniform vec3 uSun3; uniform float uMix;
uniform float uSun; uniform float uNl; uniform float uDn; uniform float uOd0; uniform float uKey; uniform float uNsh; uniform float uSwon; uniform float uAm;
uniform float uKA; uniform float uKK; uniform float uFade; uniform vec3 uShc; uniform vec4 uSwP; uniform vec4 uSwC;
uniform float uNf; uniform float uNfb; uniform float uFall; uniform float uE; uniform vec3 uSd; uniform vec4 uShA[3]; uniform vec4 uShD[3];
uniform vec4 uLP[96]; uniform vec4 uLC[96]; uniform vec4 uLF[96]; uniform vec4 uFG[16]; uniform vec4 uFA[16];
float B(float v) { return floor(v * 255.0 + 0.5); }
float trc(float v) { return v < 0.0 ? -floor(-v) : floor(v); }   /* C (int) */
float rne(float v) { float r = floor(v + 0.5); if (r - v == 0.5 && mod(r, 2.0) != 0.0) r -= 1.0; return r; }   /* lrintf */
float bit(float m, int j) { return mod(floor(m / exp2(float(j))), 2.0); }
vec3 lit(vec3 c, vec3 f) { return min(floor(c * f), vec3(255.0)); }
vec4 fin(vec3 o, vec2 fc) {   /* GL4: the emissive mix after the light (offset p0, slope (p1 - p0) / 255) */
  if (uPost > 0.5) { vec4 a = texture2D(post, (fc + 0.5) / vec2(448.0, 448.0)), b = texture2D(post, (vec2(fc.x, fc.y + 224.0) + 0.5) / vec2(448.0, 448.0));
    if (a.rgb != vec3(0.0) || b.rgb != vec3(1.0)) { vec3 p0 = vec3(B(a.r), B(a.g), B(a.b)), p1 = vec3(B(b.r), B(b.g), B(b.b)); o = floor(p0 + (p1 - p0) * o / 255.0 + 0.5); } }
  return vec4(clamp(o, 0.0, 255.0) / 255.0, 1.0); }
float tagAt(float x, float y) { return B(texture2D(cls, (vec2(x, y) + 0.5) / vec2(448.0, 224.0)).a); }
float term(vec3 p, vec3 n, vec4 LP, float kk) {   /* lk_lt_term without shadow */
  vec3 v = LP.xyz - p; float d = sqrt(v.x * v.x + v.y * v.y + v.z * v.z), rad = LP.w, ndl, q;
  if (d >= rad || d < 0.001) return d < 0.001 ? kk : 0.0;
  ndl = (n.x * v.x + n.y * v.y + n.z * v.z) / d; if (ndl < 0.0) ndl = 0.0;
  q = 1.0 - d / rad; return kk * q * q * (0.25 + 0.75 * ndl); }
bool figdir(vec3 sd, vec3 p, float fm) {   /* lk_lt_figdir */
  float hl = sqrt(sd.x * sd.x + sd.y * sd.y); if (hl < 1e-3) return false;
  float nx = sd.x / hl, ny = sd.y / hl, den = nx * sd.x + ny * sd.y, tx = ny, ty = -nx; if (tx - ty < 0.0) { tx = -tx; ty = -ty; }
  for (int j = 0; j < 16; j++) { if (float(j) >= uNf) break;
    vec4 F = uFG[j], Fa = uFA[j];
    if (uKey > 0.5 && bit(fm, j) < 0.5) continue;
    if (abs(F.x - p.x) > 110.0 || abs(F.y - p.y) > 110.0 || p.z > F.z + 56.0) continue;
    float t = (nx * (F.x - p.x) + ny * (F.y - p.y)) / den; if (t <= 0.5) continue;
    vec3 q = p + t * sd; float dx = 1.4142 * (tx * (q.x - F.x) + ty * (q.y - F.y)), hh = q.z - F.z;
    if (dx < -16.0 || dx > 16.0 || hh < -6.0 || hh > 56.0) continue;
    float mx = Fa.x + rne(dx) + uE, my = Fa.y - rne(hh);
    if (mx >= 0.0 && mx < 448.0 && my >= 0.0 && my < 224.0 && tagAt(mx, my) == Fa.z) return true; }
  return false; }
float shadowed(vec3 p, int li, float fm, float cx, float cy) {   /* lk_lt_shadowed */
  vec4 L = uLP[li];
  for (int j = 0; j < 16; j++) { if (float(j) >= uNf) break;
    vec4 P = texture2D(pairs, (vec2(float(li), float(j)) + 0.5) / vec2(96.0, 32.0)); if (P.z < 0.5 || bit(fm, j) < 0.5) continue;
    vec4 pb = texture2D(pairs, (vec2(float(li), float(16 + j)) + 0.5) / vec2(96.0, 32.0)); if (cx < pb.x || cx > pb.z || cy < pb.y || cy > pb.w) continue;
    vec4 F = uFG[j], Fa = uFA[j]; float nx = P.x, ny = P.y;
    float den = nx * (L.x - p.x) + ny * (L.y - p.y), num = nx * (F.x - p.x) + ny * (F.y - p.y);
    if (abs(den) < 1e-4) continue;
    float t = num / den; if (t < 0.02 || t > 0.98) continue;
    vec3 q = vec3(p.x + t * (L.x - p.x), p.y + t * (L.y - p.y), p.z + t * (L.z - p.z));
    float tx = ny, ty = -nx; if (tx - ty < 0.0) { tx = -tx; ty = -ty; }
    float dx = 1.4142 * (tx * (q.x - F.x) + ty * (q.y - F.y)), hh = q.z - F.z;
    if (dx < -16.0 || dx > 16.0 || hh < -6.0 || hh > 56.0) continue;
    float mx = Fa.x + rne(dx) + uE, my = Fa.y - rne(hh), hit = 0.0;
    for (int b2 = -1; b2 <= 1; b2++) for (int a2 = -1; a2 <= 1; a2++) { float ux = mx + float(a2), uy = my + float(b2);
      if (ux >= 0.0 && ux < 448.0 && uy >= 0.0 && uy < 224.0 && tagAt(ux, uy) == Fa.z) hit += 1.0; }
    if (hit > 0.0) { vec3 e = L.xyz - p; float d = t * sqrt(e.x * e.x + e.y * e.y + e.z * e.z), w = (60.0 - d) * (1.0 / 40.0);
      w = w >= 1.0 ? 1.0 : w > 0.0 ? w : 0.0; return w * hit / 9.0; } }
  return 0.0; }
vec3 amix(vec3 r, vec2 q, float zs, float fd, bool noadd) {   /* lk_am_mix (noadd: only drops / splashes, the void) */
  vec4 m = texture2D(amap, q); if (m == vec4(0.0)) return r;
  float al = B(m.a); bool add = al > 127.5; if (add) { al -= 128.0; if (noadd) return r; }
  vec4 zd = texture2D(amzd, q); float mz = B(zd.r) + 256.0 * B(zd.g), md = B(zd.b) + 256.0 * B(zd.a); if (mz >= 32768.0) mz -= 65536.0; if (md >= 32768.0) md -= 65536.0;
  if (zs != -32768.0 && mz < zs - 2.0) return r;
  if (fd != -32768.0 && md < fd - 4.0) return r;
  float a = al * (1.0 / 127.0) * uFade; vec3 cc = vec3(B(m.r), B(m.g), B(m.b));
  if (add) return r + floor(cc * a);
  return r + vec3(trc((cc.r - r.r) * a), trc((cc.g - r.g) * a), trc((cc.b - r.b) * a)); }
vec2 mq(float U, float V) { return (vec2(mod(U, 512.0), mod(V, 512.0)) + 0.5) / 512.0; }
float moteAt(vec2 q, out float dz) { vec4 m = texture2D(motes, q); dz = B(m.g) + 256.0 * B(m.b); if (dz >= 32768.0) dz -= 65536.0; return B(m.r); }
void main() {
  vec2 fc = floor(gl_FragCoord.xy); float line = fc.y;
  vec2 tc = (fc + 0.5) / vec2(448.0, 224.0);
  vec4 cu = texture2D(unl, tc); vec3 c = vec3(B(cu.r), B(cu.g), B(cu.b));
  float cl = B(texture2D(cls, tc).r);
  if (cl < 0.5 || (cl > 3.5 && cl < 15.5) || cl == 2.0) { gl_FragColor = vec4(c / 255.0, 1.0); return; }
  vec4 ro = texture2D(rows, vec2((line + 0.5) / 224.0, 0.5));
  float U = B(ro.r) + 256.0 * B(ro.g), V = B(ro.b) + 256.0 * B(ro.a);
  if (U >= 32768.0) U -= 65536.0; if (V >= 32768.0) V -= 65536.0;
  U += fc.x;
  float bx = floor(U / 32.0), by = floor(V / 32.0), have = 0.0, sg = 0.0, bnl = 0.0; vec2 bt2 = (vec2(bx, by) + 0.5) / vec2(76.0, 38.0);
  if (bx >= 0.0 && by >= 0.0 && bx < 76.0 && by < 38.0) { vec4 bt = texture2D(btab, bt2); have = bt.r > 0.5 ? 1.0 : 0.0; sg = bt.g > 0.5 ? 1.0 : 0.0; bnl = B(bt.b); }
  vec3 a = vec3(uAmb * 0.93, uAmb * 0.96, uAmb * 1.06), sr = vec3(0.0); float bm = 0.0, bz = -32768.0, x = fc.x - uE;
  if (uNl < 0.5 && uSun < 0.5) a = vec3(1.0);
  vec2 rt = (vec2(U, V) + 0.5) / vec2(2432.0, 1216.0), q = mq(U, V);
  vec4 A = texture2D(roomA, rt), Bp = texture2D(roomB, rt);
  float face = B(A.r), sun = B(A.g), sunn = B(A.b), ao = B(A.a), z = B(Bp.r) + 256.0 * B(Bp.g), beam = B(Bp.b), pool = B(Bp.a);
  if (z >= 32768.0) z -= 65536.0;
  if (cl > 15.5) {   /* a figure pixel, lit at its card facing the camera */
    int j = int(cl - 16.0); vec4 F = uFG[j]; vec4 Fa = uFA[j]; float dx = x - Fa.x; vec3 pp = vec3(F.x + dx * 0.5, F.y - dx * 0.5, F.z + (Fa.y - line)); vec3 nn = vec3(0.7071, 0.7071, 0.0);
    for (int k = 0; k < 96; k++) { if (float(k) >= uNl) break; vec4 Lf = uLF[k]; if (Lf.y > 0.5 && Lf.x <= 0.004) continue; float t = term(pp, nn, uLP[k], uLC[k].w) * Lf.x; sr += t * uLC[k].rgb; }
    if (uSwon > 0.5) { float t = term(pp, nn, uSwP, uSwC.w) * 0.5; sr += t * uSwC.rgb; }
    float u = F.w;
    if (uSun > 0.5 && uDn > 0.5) a = uAmb3 + uSun3 * u;
    else if (uSun > 0.5) { float k2 = uSK * u; a = vec3(uSS * 0.95 + k2, uSS * 0.98 + k2 * 0.97, uSS * 1.06 + k2 * 0.90); }
    else if (uKey > 0.5) { float k2 = uKK * u; a = vec3(uKA * 0.97 + k2 * 1.04, uKA * 0.99 + k2, uKA * 1.05 + k2 * 0.92); }
    vec3 o = floor(c * min(a + 2.2 * sr, vec3(2.4)));
    if (uNsh > 0.5) { float dz, d = moteAt(q, dz), gl = 0.0; if (d > 0.0) gl += d * 0.50; gl *= uFade; if (gl > 0.0) o += floor(gl * uShc); }
    if (uAm > 0.5) o = amix(o, q, -32768.0, trc(F.x + F.y), false);
    gl_FragColor = fin(o, fc); return; }
  if (cl > 2.5 || (have > 0.5 && face < 0.5)) {   /* void glow */
    vec3 o = c;
    if ((uNsh > 0.5 || uAm > 0.5) && have > 0.5) { float dz, d = uNsh > 0.5 ? moteAt(q, dz) : 0.0, gl = uNsh > 0.5 ? (beam * 0.38 + d * 0.50) * uFade : 0.0; o = c + floor(gl * uShc);
      if (uAm > 0.5) o = amix(o, q, -32768.0, -32768.0, true); o = min(o, vec3(255.0)); }
    gl_FragColor = fin(o, fc); return; }
  if (have < 0.5) {
    vec3 o = c;
    if (uSun < 0.5 && uOd0 > 0.5) { if (uKey > 0.5) { float k2 = uKK * 0.6; o = lit(c, vec3(uKA * 0.97 + k2 * 1.04, uKA * 0.99 + k2, uKA * 1.05 + k2 * 0.92)); } else if (uNl > 0.5) o = lit(c, a); }
    else if (uSun > 0.5 && uDn < 0.5 && uOd0 > 0.5) o = lit(c, min(vec3(uSS * 0.95 + uSK, uSS * 0.98 + uSK * 0.97, uSS * 1.06 + uSK * 0.90), vec3(2.4)));
    else if (uSun > 0.5 && uDn > 0.5) o = lit(c, min(uAmb3 + uSun3, vec3(2.4)));
    gl_FragColor = fin(o, fc); return; }
  bz = z;
  float D = U - 1184.0; vec3 pp = vec3((2.0 * V + 2.0 * z + D) * 0.5, (2.0 * V + 2.0 * z - D) * 0.5, z);
  float infb = uFall > 0.5 ? 1.0 : 0.0, fm = uFall > 0.5 ? 65535.0 : 0.0;
  if (uNfb > 0.5 && infb < 0.5) { vec4 m = texture2D(fmk, tc); fm = B(m.r) + 256.0 * B(m.a); infb = fm > 0.0 ? 1.0 : 0.0; }
  if (uKey > 0.5 && uNl < 0.5 && !(uNfb > 0.5 && (sun > 0.5 || pool > 0.5) && infb > 0.5)) {   /* key light fast path: the finished static light */
    vec4 K = texture2D(roomK, rt); float hb = B(K.a); vec3 km = vec3(B(K.r) + 256.0 * mod(hb, 4.0), B(K.g) + 256.0 * mod(floor(hb / 4.0), 4.0), B(K.b) + 256.0 * mod(floor(hb / 16.0), 4.0));
    vec3 o = floor((c * km + 128.0) / 256.0);
    if (uNsh > 0.5) { float dz, d = moteAt(q, dz), gl = beam * 0.38; if (d > 0.0 && dz >= z - 2.0) gl += d * 0.50; gl *= uFade; if (gl > 0.0) o += floor(gl * uShc); }
    if (uAm > 0.5) o = amix(o, q, z, -32768.0, false);
    gl_FragColor = fin(o, fc); return; }
  if (uSun > 0.5) { float u = sun * (1.0 / 255.0);
    if (uMix > 0.5 && sg > 0.5) u += (sunn * (1.0 / 255.0) - u) * uMix * (1.0 / 256.0);
    if (u > 0.0 && uNf > 0.5) { if (figdir(uSd, pp, fm)) u = 0.0; }
    if (uDn > 0.5) a = uAmb3 + uSun3 * u;
    else { float k2 = uSK * u; a = vec3(uSS * 0.95 + k2, uSS * 0.98 + k2 * 0.97, uSS * 1.06 + k2 * 0.90); } }
  else if (uKey > 0.5) { float u = sun * (1.0 / 255.0);
    if (u > 0.0 && uNfb > 0.5 && infb > 0.5) { if (figdir(uSd, pp, fm)) u *= 0.45; }
    float k2 = uKK * u; a = vec3(uKA * 0.97 + k2 * 1.04, uKA * 0.99 + k2, uKA * 1.05 + k2 * 0.92);
    if (pool > 0.5) { float pq = pool * (1.0 / 255.0) * 0.65;
      if (uNfb > 0.5 && uNf > 0.5 && infb > 0.5) { float sh = 0.0;
        for (int qq = 0; qq < 3; qq++) { if (float(qq) >= uNsh) break; vec4 SA = uShA[qq], SD = uShD[qq];
          float hl = sqrt(SD.x * SD.x + SD.y * SD.y), axh = hl > 1e-3 ? -SD.x / hl : 0.0, ayh = hl > 1e-3 ? -SD.y / hl : 0.0, off = 24.0 * hl / SD.z, Lq = off + 10.0, Wd = 10.0;
          vec3 vv = pp - SA.xyz; float s2 = vv.x * SD.x + vv.y * SD.y + vv.z * SD.z; vec3 qv = vec3(vv.x - s2 * SD.x, vv.y - s2 * SD.y, vv.z - s2 * SD.z);
          if (sqrt(qv.x * qv.x + qv.y * qv.y + qv.z * qv.z) > SA.w * 1.3) continue;
          for (int jf = 0; jf < 16; jf++) { if (float(jf) >= uNf) break; vec4 F = uFG[jf];
            if (bit(fm, jf) < 0.5 || abs(z - F.z) > 8.0) continue;
            float vx = pp.x - (F.x + axh * off), vy = pp.y - (F.y + ayh * off), al = vx * axh + vy * ayh, ac = -vx * ayh + vy * axh, e = (al * al) / (Lq * Lq) + (ac * ac) / (Wd * Wd);
            if (e >= 1.0) continue; float f = (1.0 - e) * 1.6; if (f > 1.0) f = 1.0; if (f > sh) sh = f; } }
        if (sh > 0.0) { float cd = 1.0 - 0.30 * sh; pq *= 1.0 - 0.85 * sh; a *= cd; } }
      a += pq * uShc; }
    bm = beam; }
  float tb = 0.0, tl = 0.0, fmo = (uNfb > 0.5 && uNf > 0.5) ? infb : 0.0;
  if (bnl > 0.5) { vec4 T0 = texture2D(roomT0, rt), T1 = texture2D(roomT1, rt), I0 = texture2D(bli, (vec2(bx, by) + 0.5) / vec2(152.0, 38.0)), I1 = texture2D(bli, (vec2(bx + 76.0, by) + 0.5) / vec2(152.0, 38.0));
    for (int k = 0; k < 8; k++) { if (float(k) >= bnl) break;
      float tv = k == 0 ? T0.r : k == 1 ? T0.g : k == 2 ? T0.b : k == 3 ? T0.a : k == 4 ? T1.r : k == 5 ? T1.g : k == 6 ? T1.b : T1.a;
      float ib = k == 0 ? I0.r : k == 1 ? I0.g : k == 2 ? I0.b : k == 3 ? I0.a : k == 4 ? I1.r : k == 5 ? I1.g : k == 6 ? I1.b : I1.a;
      float t = B(tv) * (1.0 / 255.0); int li = int(B(ib));
      if (t <= 0.0) continue;
      vec4 Lf = uLF[li];
      if (Lf.y > 0.5) { if (Lf.x <= 0.004) continue; t *= Lf.x > 1.0 ? 1.0 : Lf.x; }
      if (fmo > 0.5 && !(Lf.y > 0.5 && face != 1.0)) { float w = shadowed(pp, li, fm, x, line);
        if (w >= 1.0) { tb += t; continue; } if (w > 0.0) { tb += t * w; t *= 1.0 - w; } }
      tl += t; if (Lf.y < 0.5) t *= Lf.x; sr += t * uLC[li].rgb; } }
  if (ao < 254.5) a *= ao * (1.0 / 255.0);
  if (tb > 0.0) { float d = 1.0 - 0.5 * tb / (tb + tl + 0.05); a *= d; }
  if (uSwon > 0.5) { float t = term(pp, vec3(face == 2.0 ? 1.0 : 0.0, face == 3.0 ? 1.0 : 0.0, face == 1.0 ? 1.0 : 0.0), uSwP, uSwC.w); sr += t * uSwC.rgb; }
  vec3 o = floor(c * min(a + 2.2 * sr, vec3(2.4)));
  if (uNsh > 0.5) { float dz, d = moteAt(q, dz), gl = bm * 0.38; if (d > 0.0 && dz >= bz - 2.0) gl += d * 0.50; gl *= uFade; if (gl > 0.0) o += floor(gl * uShc); }
  if (uAm > 0.5) o = amix(o, q, bz, -32768.0, false);
  gl_FragColor = fin(o, fc); }
'''

if VER not in s:
    MODULE = r'''/* ---- %s: GPU lighting harness (tools/patch_gpulight.py): offscreen light pass + compare with the CPU result ---- */
extern int lk_gl_getmode(void); extern int lk_gl_frame(long fr, float *fu, int *iu, float *lp, float *lc, float *lf, float *fg, float *fa); extern unsigned lk_gl_bver(int bx, int by); extern int lk_gl_bsg(int bx, int by);
extern void lk_gl_bpack(int bx, int by, uint32_t (*o)[1024]); extern void lk_gl_blist(int bx, int by, uint32_t *a, uint32_t *b2, int *nl); extern const uint16_t *lk_gl_fmk(void);
extern void lk_gl_pairs(float *o); extern void lk_gl_clstag(uint16_t *o); extern const uint32_t *lk_gl_am(void); extern void lk_gl_motes(uint32_t *o, int *bb); extern void lk_gl_amzd(uint32_t *o, int *bb);
extern uint32_t lk_gl_post[2][224 * 448]; extern int lk_gl_postany, lk_gl_postprev;
extern uint32_t lk_gl_unlit[224 * 448], lk_gl_ref[224 * 448]; extern uint8_t lk_gl_cls[224 * 448], lk_gl_flg[224 * 448]; extern uint32_t lk_gl_row[224];
LKGL_FN(void, glUniform3f, (lkGLint, lkGLfloat, lkGLfloat, lkGLfloat)); LKGL_FN(void, glUniform4f, (lkGLint, lkGLfloat, lkGLfloat, lkGLfloat, lkGLfloat)); LKGL_FN(void, glUniform4fv, (lkGLint, lkGLsizei, const lkGLfloat *));
LKGL_FN(void, glGenFramebuffers, (lkGLsizei, lkGLuint *)); LKGL_FN(void, glBindFramebuffer, (lkGLenum, lkGLuint)); LKGL_FN(void, glFramebufferTexture2D, (lkGLenum, lkGLenum, lkGLenum, lkGLuint, lkGLint)); LKGL_FN(lkGLenum, glCheckFramebufferStatus, (lkGLenum));
static int lk_glt_st;   /* 0 not tried, 1 ready, -1 failed */
#define LK_GLT_NT 16   /* textures of the pass: 0 unlit, 1 class + tag, 2 rows, 3 room A, 4 block table, 5 / 6 terms, 7 room B, 8 key light, 9 light lists, 10 mix after the light (448 x 448), 11 figure box mask, 12 pairs, 13 motes, 14 particles, 15 particle depths */
static lkGLuint lk_glt_prog, lk_glt_fbo, lk_glt_out, lk_glt_t[LK_GLT_NT]; static lkGLint lk_glt_u[64];
static unsigned lk_glt_ver[38][76]; static uint16_t lk_glt_ct[224 * 448]; static uint32_t lk_glt_mo[512 * 512], lk_glt_az[512 * 512]; static float lk_glt_pr[96 * 32 * 4];
static const char *lk_glt_fs = "#version 120\n" @SHADER@;
static const char *lk_glt_un[] = { "unl", "cls", "rows", "roomA", "btab", "roomT0", "roomT1", "roomB", "roomK", "bli", "post", "fmk", "pairs", "motes", "amap", "amzd",
  "uAmb", "uSS", "uSK", "uAmb3", "uSun3", "uMix", "uSun", "uNl", "uDn", "uOd0", "uKey", "uNsh", "uSwon", "uAm", "uKA", "uKK", "uFade", "uShc", "uSwP", "uSwC", "uNf", "uNfb", "uFall", "uE", "uSd", "uShA", "uShD",
  "uLP", "uLC", "uLF", "uFG", "uFA", "uPost", 0 };
static lkGLuint lk_glt_tex(int w, int h, lkGLenum ifmt, lkGLenum fmt) { lkGLuint t; lk_glGenTextures(1, &t); lk_glBindTexture(0x0DE1, t); lk_glTexImage2D(0x0DE1, 0, (lkGLint)ifmt, w, h, 0, fmt, 0x1401, 0);
  lk_glTexParameteri(0x0DE1, 0x2801, 0x2600); lk_glTexParameteri(0x0DE1, 0x2800, 0x2600); lk_glTexParameteri(0x0DE1, 0x2802, 0x812F); lk_glTexParameteri(0x0DE1, 0x2803, 0x812F); return t; }
static int lk_glt_init(void) {   /* inside lk_gpu_present (SDL's state saved, texture unit 0 active) */
  lkGLint ok = 0, t0 = 0; lkGLuint vs, fs; char log[2048]; int i;
  *(void **)&lk_glGenFramebuffers = lk_gpu_fn("glGenFramebuffers"); *(void **)&lk_glBindFramebuffer = lk_gpu_fn("glBindFramebuffer");
  *(void **)&lk_glFramebufferTexture2D = lk_gpu_fn("glFramebufferTexture2D"); *(void **)&lk_glCheckFramebufferStatus = lk_gpu_fn("glCheckFramebufferStatus");
  if (!lk_glGenFramebuffers) { *(void **)&lk_glGenFramebuffers = lk_gpu_fn("glGenFramebuffersEXT"); *(void **)&lk_glBindFramebuffer = lk_gpu_fn("glBindFramebufferEXT");
    *(void **)&lk_glFramebufferTexture2D = lk_gpu_fn("glFramebufferTexture2DEXT"); *(void **)&lk_glCheckFramebufferStatus = lk_gpu_fn("glCheckFramebufferStatusEXT"); }
  *(void **)&lk_glUniform3f = lk_gpu_fn("glUniform3f"); *(void **)&lk_glUniform4f = lk_gpu_fn("glUniform4f"); *(void **)&lk_glUniform4fv = lk_gpu_fn("glUniform4fv");
  if (!lk_glUniform3f || !lk_glUniform4f || !lk_glUniform4fv || !lk_glGenFramebuffers || !lk_glBindFramebuffer || !lk_glFramebufferTexture2D || !lk_glCheckFramebufferStatus) { printf("gpult: GL functions missing\n"); return -1; }
  { static const char *vsrc = "#version 120\nvoid main() { gl_Position = gl_Vertex; }\n"; vs = lk_glCreateShader(0x8B31); lk_glShaderSource(vs, 1, &vsrc, 0); lk_glCompileShader(vs); lk_glGetShaderiv(vs, 0x8B81, &ok); if (!ok) return -1; }
  fs = lk_glCreateShader(0x8B30); lk_glShaderSource(fs, 1, &lk_glt_fs, 0); lk_glCompileShader(fs); lk_glGetShaderiv(fs, 0x8B81, &ok);
  if (!ok) { lk_glGetShaderInfoLog(fs, sizeof log, 0, log); printf("gpult: light shader failed: %%s\n", log); return -1; }
  lk_glt_prog = lk_glCreateProgram(); lk_glAttachShader(lk_glt_prog, vs); lk_glAttachShader(lk_glt_prog, fs); lk_glLinkProgram(lk_glt_prog); lk_glGetProgramiv(lk_glt_prog, 0x8B82, &ok);
  if (!ok) { lk_glGetProgramInfoLog(lk_glt_prog, sizeof log, 0, log); printf("gpult: link failed: %%s\n", log); return -1; }
  for (i = 0; lk_glt_un[i]; i++) lk_glt_u[i] = lk_glGetUniformLocation(lk_glt_prog, lk_glt_un[i]);
  lk_glGetIntegerv(0x8069, &t0);
  lk_glt_out = lk_glt_tex(448, 224, 0x1908, 0x1908);
  lk_glt_t[0] = lk_glt_tex(448, 224, 0x1908, 0x80E1); lk_glt_t[1] = lk_glt_tex(448, 224, 0x190A, 0x190A); lk_glt_t[2] = lk_glt_tex(224, 1, 0x1908, 0x1908);
  lk_glt_t[3] = lk_glt_tex(2432, 1216, 0x1908, 0x1908); lk_glt_t[4] = lk_glt_tex(76, 38, 0x1908, 0x1908); lk_glt_t[5] = lk_glt_tex(2432, 1216, 0x1908, 0x1908); lk_glt_t[6] = lk_glt_tex(2432, 1216, 0x1908, 0x1908);
  lk_glt_t[7] = lk_glt_tex(2432, 1216, 0x1908, 0x1908); lk_glt_t[8] = lk_glt_tex(2432, 1216, 0x1908, 0x1908); lk_glt_t[9] = lk_glt_tex(152, 38, 0x1908, 0x1908); lk_glt_t[10] = lk_glt_tex(448, 448, 0x1908, 0x1908);
  lk_glt_t[11] = lk_glt_tex(448, 224, 0x190A, 0x190A); lk_glt_t[12] = lk_glt_tex(96, 32, 0x8814, 0x1908);
  lk_glt_t[13] = lk_glt_tex(512, 512, 0x1908, 0x1908); lk_glt_t[14] = lk_glt_tex(512, 512, 0x1908, 0x80E1); lk_glt_t[15] = lk_glt_tex(512, 512, 0x1908, 0x1908);
  { lkGLenum e = lk_glGetError(); if (e) { printf("gpult: texture setup GL error %%04X (float textures?)\n", (unsigned)e); return -1; } }
  lk_glBindTexture(0x0DE1, (lkGLuint)t0);
  { lkGLint fb0 = 0; lkGLenum st; lk_glGetIntegerv(0x8CA6, &fb0); lk_glGenFramebuffers(1, &lk_glt_fbo); lk_glBindFramebuffer(0x8D40, lk_glt_fbo); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_glt_out, 0);
    st = lk_glCheckFramebufferStatus(0x8D40); lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); if (st != 0x8CD5) { printf("gpult: framebuffer incomplete %%04X\n", (unsigned)st); return -1; } }
  memset(lk_glt_ver, 0, sizeof lk_glt_ver);
  printf("gpult: GPU lighting ready (%%s)\n", lk_gl_getmode() == 2 ? "compare" : "real"); return 1; }
int lk_gpu_lightok(void) { return lk_gpu_get() && lk_gpu_st >= 0 && lk_glt_st >= 0; }   /* vdp_render.c (lk_gl_okfn): may the rows leave the light to the GPU? */
static long lk_glt_fb[8]; static long lk_glt_n, lk_glt_skip, lk_glt_px, lk_glt_ex, lk_glt_o1, lk_glt_bad, lk_glt_xc, lk_glt_xf[8], lk_glt_cpx[3], lk_glt_cbad[3]; static int lk_glt_shown;
static int lk_glt_pass(int real) {   /* inside lk_gpu_present after SDL's state is saved; compare (real 0): before the picture upload, unit 0 = recorded unlit picture;
     real (1): after it, unit 0 = the presented picture; returns 1 when lk_glt_out holds the lit picture.  Leaves texture unit 0 active, vertex array enabled */
  float fu[64], lp[96 * 4], lc[96 * 4], lf[96 * 4], fg[16 * 4], fa[16 * 4]; int iu[32], L, i, bx, by, u0 = 1 << 30, u1 = -(1 << 30), v0 = 1 << 30, v1 = -(1 << 30); long fr = platform_frame_number();
  lkGLint fb0 = 0, tb[LK_GLT_NT]; static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 }; static uint32_t pk[5][1024], bt[38 * 76], bl0[38 * 76], bl1[38 * 76], *rb;
  if (lk_gl_getmode() != (real ? 1 : 2) || lk_glt_st < 0 || !lk_gl_frame(fr, fu, iu, lp, lc, lf, fg, fa)) return 0;
  if (lk_glt_st == 0) { lk_glt_st = lk_glt_init(); if (lk_glt_st < 0) return 0; }
  for (i = 0; i < LK_GLT_NT; i++) { lk_glActiveTexture(0x84C0 + i); lk_glGetIntegerv(0x8069, &tb[i]); }
  /* visible blocks: upload what changed */
  for (L = 0; L < 224; L++) { int U = (int)(int16_t)(lk_gl_row[L] & 0xFFFF), V = (int)(int16_t)(lk_gl_row[L] >> 16); if (U < u0) u0 = U; if (U + iu[7] - 1 > u1) u1 = U + iu[7] - 1; if (V < v0) v0 = V; if (V > v1) v1 = V; }
  for (by = 0; by < 38; by++) for (bx = 0; bx < 76; bx++) { unsigned v = lk_gl_bver(bx, by); int nl = 0; uint32_t a = 0, b2 = 0;
    if (v) lk_gl_blist(bx, by, &a, &b2, &nl);
    bt[by * 76 + bx] = (v ? 0xFFu : 0u) | (lk_gl_bsg(bx, by) ? 0xFF00u : 0u) | ((uint32_t)nl << 16); bl0[by * 76 + bx] = a; bl1[by * 76 + bx] = b2;
    if (v && v != lk_glt_ver[by][bx] && bx * 32 + 31 >= u0 && bx * 32 <= u1 && by * 32 + 31 >= v0 && by * 32 <= v1) { static const int pt[5] = { 3, 5, 6, 7, 8 }; int k;
      lk_gl_bpack(bx, by, pk);
      for (k = 0; k < 5; k++) { lk_glActiveTexture(0x84C0 + pt[k]); lk_glBindTexture(0x0DE1, lk_glt_t[pt[k]]); lk_glTexSubImage2D(0x0DE1, 0, bx * 32, by * 32, 32, 32, 0x1908, 0x1401, pk[k]); }
      lk_glt_ver[by][bx] = v; } }
  lk_glActiveTexture(0x84C4); lk_glBindTexture(0x0DE1, lk_glt_t[4]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 76, 38, 0x1908, 0x1401, bt);
  lk_glActiveTexture(0x84C9); lk_glBindTexture(0x0DE1, lk_glt_t[9]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 76, 38, 0x1908, 0x1401, bl0); lk_glTexSubImage2D(0x0DE1, 0, 76, 0, 76, 38, 0x1908, 0x1401, bl1);
  if (real && (lk_gl_postany || lk_gl_postprev)) { lk_glActiveTexture(0x84CA); lk_glBindTexture(0x0DE1, lk_glt_t[10]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x80E1, 0x1401, lk_gl_post[0]); lk_glTexSubImage2D(0x0DE1, 0, 0, 224, 448, 224, 0x80E1, 0x1401, lk_gl_post[1]); }
  lk_glActiveTexture(0x84CB); lk_glBindTexture(0x0DE1, lk_glt_t[11]); if (iu[10]) lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x190A, 0x1401, lk_gl_fmk());
  lk_glActiveTexture(0x84C2); lk_glBindTexture(0x0DE1, lk_glt_t[2]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 224, 1, 0x1908, 0x1401, lk_gl_row);
  lk_gl_clstag(lk_glt_ct); lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, lk_glt_t[1]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x190A, 0x1401, lk_glt_ct);
  if (iu[10]) { lk_gl_pairs(lk_glt_pr); lk_glActiveTexture(0x84CC); lk_glBindTexture(0x0DE1, lk_glt_t[12]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 96, 32, 0x1908, 0x1406, lk_glt_pr); }
  lk_glPixelStorei(0x0CF2, 512);   /* motes / particles: sub-rectangles of the 512 x 512 maps */
  { int bb[4]; lk_gl_motes(lk_glt_mo, bb); if (bb[2] >= bb[0]) { lk_glActiveTexture(0x84CD); lk_glBindTexture(0x0DE1, lk_glt_t[13]); lk_glTexSubImage2D(0x0DE1, 0, bb[0], bb[1], bb[2] - bb[0] + 1, bb[3] - bb[1] + 1, 0x1908, 0x1401, lk_glt_mo + bb[1] * 512 + bb[0]); } }
  { int bb[4]; lk_gl_amzd(lk_glt_az, bb); if (bb[2] >= bb[0]) { lk_glActiveTexture(0x84CE); lk_glBindTexture(0x0DE1, lk_glt_t[14]); lk_glTexSubImage2D(0x0DE1, 0, bb[0], bb[1], bb[2] - bb[0] + 1, bb[3] - bb[1] + 1, 0x80E1, 0x1401, lk_gl_am() + bb[1] * 512 + bb[0]);
    lk_glActiveTexture(0x84CF); lk_glBindTexture(0x0DE1, lk_glt_t[15]); lk_glTexSubImage2D(0x0DE1, 0, bb[0], bb[1], bb[2] - bb[0] + 1, bb[3] - bb[1] + 1, 0x1908, 0x1401, lk_glt_az + bb[1] * 512 + bb[0]); } }
  lk_glPixelStorei(0x0CF2, 0);
  if (!real) { lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_glt_t[0]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x80E1, 0x1401, lk_gl_unlit); }
  else { lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, (lkGLuint)tb[0]); }   /* the presented picture (lk_gpu_tex) */
  for (i = 3; i < LK_GLT_NT; i++) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, lk_glt_t[i]); }
  lk_glActiveTexture(0x84C0);
  lk_glUseProgram(lk_glt_prog);
  for (i = 0; i < LK_GLT_NT; i++) lk_glUniform1i(lk_glt_u[i], i);
  #define U1(n, v) lk_glUniform1f(lk_glt_u[n], (float)(v))
  U1(16, fu[0]); U1(17, fu[1]); U1(18, fu[2]); lk_glUniform3f(lk_glt_u[19], fu[3], fu[4], fu[5]); lk_glUniform3f(lk_glt_u[20], fu[6], fu[7], fu[8]); U1(21, fu[9]);
  U1(22, iu[0]); U1(23, iu[2]); U1(24, iu[5]); U1(25, iu[6]); U1(26, iu[1]); U1(27, iu[14]); U1(28, iu[4]); U1(29, iu[13]);
  U1(30, fu[10]); U1(31, fu[11]); U1(32, fu[12]); lk_glUniform3f(lk_glt_u[33], fu[13], fu[14], fu[15]); lk_glUniform4f(lk_glt_u[34], fu[16], fu[17], fu[18], fu[19]); lk_glUniform4f(lk_glt_u[35], fu[20], fu[21], fu[22], fu[23]);
  U1(36, iu[9]); U1(37, iu[10]); U1(38, iu[11]); U1(39, iu[12]); lk_glUniform3f(lk_glt_u[40], fu[24], fu[25], fu[26]);
  { float sa[12], sd2[12]; int k; for (k = 0; k < 3; k++) { sa[4 * k] = fu[32 + 8 * k]; sa[4 * k + 1] = fu[33 + 8 * k]; sa[4 * k + 2] = fu[34 + 8 * k]; sa[4 * k + 3] = fu[35 + 8 * k]; sd2[4 * k] = fu[36 + 8 * k]; sd2[4 * k + 1] = fu[37 + 8 * k]; sd2[4 * k + 2] = fu[38 + 8 * k]; sd2[4 * k + 3] = 0.0f; }
    lk_glUniform4fv(lk_glt_u[41], 3, sa); lk_glUniform4fv(lk_glt_u[42], 3, sd2); }
  #undef U1
  lk_glUniform1f(lk_glt_u[48], real && lk_gl_postany ? 1.0f : 0.0f);
  lk_glUniform4fv(lk_glt_u[43], 96, lp); lk_glUniform4fv(lk_glt_u[44], 96, lc); lk_glUniform4fv(lk_glt_u[45], 96, lf); lk_glUniform4fv(lk_glt_u[46], 16, fg); lk_glUniform4fv(lk_glt_u[47], 16, fa);
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glBindFramebuffer(0x8D40, lk_glt_fbo); lk_glViewport(0, 0, 448, 224);
  lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad); lk_glDrawArrays(0x0005, 0, 4);
  if (real) { lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); for (i = LK_GLT_NT - 1; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); } return 1; }
  if (!rb) rb = (uint32_t *)malloc(448 * 224 * 4);
  if (rb) { lk_glPixelStorei(0x0D02, 0); lk_glPixelStorei(0x0D05, 4); lk_glReadPixels(0, 0, 448, 224, 0x80E1, 0x1401, rb); }
  lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0);
  for (i = LK_GLT_NT - 1; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); }
  if (!rb) return 0;
  lk_glt_n++;
  for (L = 0; L < 224; L++) for (i = 0; i < iu[7]; i++) { int o = L * 448 + i, c = lk_gl_cls[o], f = 0, d, k, ck = c >= 16 ? 2 : c == 3 ? 1 : 0; uint32_t a, b;
    if (c != 1 && c != 3 && c < 16) continue;
    if (f) { lk_glt_xc++; for (k = 0; k < 8; k++) if (f & (1 << k)) lk_glt_xf[k]++; continue; }
    { int fl = lk_gl_flg[o]; for (k = 1; k < 7; k++) if (fl & (1 << k)) lk_glt_xf[k]++; }
    lk_glt_px++; lk_glt_cpx[ck]++; a = lk_gl_ref[o]; b = rb[o]; d = 0;
    for (k = 0; k < 24; k += 8) { int e = abs((int)((a >> k) & 255) - (int)((b >> k) & 255)); if (e > d) d = e; }
    if (d == 0) lk_glt_ex++; else if (d == 1) lk_glt_o1++;
    else { lk_glt_bad++; lk_glt_cbad[ck]++; { int fl = lk_gl_flg[o]; for (k = 1; k < 7; k++) if (fl & (1 << k)) lk_glt_fb[k]++; } if (lk_glt_shown < 16) { lk_glt_shown++; printf("gpult: diff frame %%ld x %%d line %%d U %%d V %%d class %%d flags %%d cpu %%06X gpu %%06X unlit %%06X (key %%d nsh %%d sw %%d nl %%d sun %%d)\n", fr - 1, i, L, (int)(int16_t)(lk_gl_row[L] & 0xFFFF) + i, (int)(int16_t)(lk_gl_row[L] >> 16), c, lk_gl_flg[o], (unsigned)(a & 0xFFFFFF), (unsigned)(b & 0xFFFFFF), (unsigned)(lk_gl_unlit[o] & 0xFFFFFF), iu[1], iu[3], iu[4], iu[2], iu[0]); } } }
  if (lk_glt_n %% 300 == 0) printf("gpult: frames %%ld pixels %%ld exact %%ld off1 %%ld worse %%ld (scenery %%ld/%%ld void %%ld/%%ld figure %%ld/%%ld) worse/with: figshadow %%ld/%%ld particle %%ld/%%ld flameshadow %%ld/%%ld poolshade %%ld/%%ld motes %%ld/%%ld\n", lk_glt_n, lk_glt_px, lk_glt_ex, lk_glt_o1, lk_glt_bad,
    lk_glt_cbad[0], lk_glt_cpx[0], lk_glt_cbad[1], lk_glt_cpx[1], lk_glt_cbad[2], lk_glt_cpx[2], lk_glt_fb[1], lk_glt_xf[1], lk_glt_fb[3], lk_glt_xf[3], lk_glt_fb[4], lk_glt_xf[4], lk_glt_fb[5], lk_glt_xf[5], lk_glt_fb[6], lk_glt_xf[6]);
  return 0;
}

''' % VER
    MODULE = MODULE.replace("@SHADER@", "\n".join('"%s\\n"' % l.replace("\\", "\\\\").replace('"', '\\"') for l in SHADER.strip("\n").split("\n")))
    a = "static long lk_gpu_frames;\n"
    assert s.count(a) == 1, "platform_sdl.c: LK_GPU module not found (patch_gpu.py first)"
    s = s.replace(a, MODULE + a)
    a = "  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_gpu_tex); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, sw, 224, 0x80E1, 0x1401, fb);\n"
    assert s.count(a) == 1, "platform_sdl.c: GPU upload line changed"
    s = s.replace(a, "  lk_glt_pass(0);   /* %s: compare harness */\n" % VER + a + "  if (lk_glt_pass(1)) lk_glBindTexture(0x0DE1, lk_glt_out);   /* %s: the filters read the GPU-lit picture */\n" % VER)
    a = '    if (!s_renderer) { SDL_SetHint(SDL_HINT_RENDER_DRIVER, ""); s_renderer = SDL_CreateRenderer(s_window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC); }'
    assert s.count(a) == 1, "platform_sdl.c: renderer fallback line changed"
    i0 = s.index(a); i1 = s.index("\n", i0) + 1
    s = s[:i1] + "    { extern int (*lk_gl_okfn)(void); extern int lk_gpu_lightok(void); lk_gl_okfn = lk_gpu_lightok; }   /* %s */\n" % VER + s[i1:]
    # test aid: hidden window (the GL context without anything on the screen)
    a = "        SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE\n"
    assert s.count(a) == 1, "platform_sdl.c: window flags changed"
    s = s.replace(a, "        (getenv(\"LANDSTALKER_HIDDEN\") ? SDL_WINDOW_HIDDEN : SDL_WINDOW_SHOWN) | SDL_WINDOW_RESIZABLE   /* %s test aid */\n" % VER)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)
else:
    print("platform_sdl.c already patched:", VER)
