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
v5 (2026-11-06, user: 'wie von dir empfohlen'): Options > Display > Light Engine GPU / CPU (id 56, ~/.landstalker_lightengine, env LANDSTALKER_LIGHTENGINE; default GPU;
LANDSTALKER_GPULT still wins as test aid) + a GPU TIME WATCHDOG (timer query around the light pass; 120 frame average > LANDSTALKER_GPULT_MAXMS, default 6 ms, twice in a row
-> CPU lighting for the rest of the run, option unchanged; LANDSTALKER_GPULT_TIME=1 prints the average).  The CPU lighting stays the fallback for good (user 2026-11-06).
GL5a (v5, compare only, LANDSTALKER_GL5CMP=1 [+ _SHOW=N, _EVERY=N]): a second shader computes every uploaded light block from its geometry and the world (lk_gl_world: heights, thin columns,
back walls, water, object field, proxies, lathe profiles, bushes / pines, early exit field; lk_gl_shafts; lk_gl_bextra: robj + layer A bit) in 5 planes = flame terms, AO, sun / key share,
shaft beam / pool, reads it back and compares with the CPU block ('gl5:' lines).  Nothing changes for the player.
GL5b (v5): the view ray (lk_lt_ray / lk_lt_rayf) on the GPU too (geometry pass); the CPU block keeps the layer A bit it used (b->la: animated tiles).
GL5f (v5, step 1): Options > Graphics > Round Figures (id 59, default On, GPU light with GL5c only): in the post pass every figure pixel is relit as a round body
(width of the figure's own pixels in its row -> normal from the card normal to the side; surface point in front of the card) with flame shadows (one point, 3 unit steps,
soft clearance) and the sun / key light shaded by the normal (0.4 .. 1.8 x the share); applied as the ratio new / old light on the lit pixel, its deviation x LANDSTALKER_ROUNDFIG_K (2.0 since 2026-11-07, was 2.5 after the user's 'mach den Effekt staerker' 2026-11-06; v2 soft knee towards 0.6 .. 1.9).  Step 2: figures shadow each other (flames: another figure's silhouette card turned to the light, as lk_lt_shadowed; sun / key: as lk_lt_figdir).
GL5e (v5): Options > Graphics > Sword Shadows (id 58, default On, GPU light with GL5c only): the light pass leaves the sword glow out on scenery pixels (uSwSh) and the post pass
(lk_gb_run, also used by Bounce Light) adds it back times a soft shadow (march to the sword through the GL5 world texture, LK_LT_IPEN clearance rule); figures keep the unshadowed half glow.
GL5c (v5): Light Engine GPU (default since 2026-11-06 late; was the option value GPU+; env LANDSTALKER_GL5=0 = the GL4 path with CPU blocks, also the watchdog's fallback): the GPU computes the visible light blocks itself (geometry pass -> 32 x 64 texture, packed pass ->
copied into roomT0 / T1 / A / B / K), block table + light lists from lk_gl_blist5, keys lk_gl_wkey (hard = room world, soft = sun steps: stale blocks stay until recomputed),
budget LANDSTALKER_GL5_CAP (18 visible without data, was 24) / _CAP2 (4 ring + stale) per frame, watchdog (timer query, > LANDSTALKER_GL5_MAXMS 5 ms average -> GPU), LANDSTALKER_GL5_TIME=1..3
debug prints.  v5 CPU SAVING (user 2026-11-06 'CPU entlasten'): while GL5c runs the CPU computes NO light blocks (no prefetch jobs, no on-demand;
lk_gl5_cpufr); the particles' floor (lk_am_surf) comes from the GPU blocks' room A / B planes read back through 2 pixel buffers one frame late (lk_gl_surfput, no stall;
a GPU sun step swap is mirrored, lk_gl_surfswap); test aid LANDSTALKER_GL5_CPUKEEP=1 = the CPU keeps computing.  rec_20261106_1322: user CPU 41.3 s -> 30.2 s (-27 %%), pictures identical.
Needs the GPU filter path (patch_gpu.py, option GPU Filters On) and a window (the GL context): LANDSTALKER_HIDDEN=1 creates the window hidden (test aid).
Needs patch_lights.py, patch_bootcol.py, patch_gpu.py before it.  Idempotent.  usage: patch_gpulight.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_GPULT v5"

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
#define LK_GLE_DEF 1   /* GPU on every system since 2026-11-08 (user: 'GPU-Weg einschlagen' + 'bitte GPU auch auf Windows zum Standard'; was CPU on Windows since 2026-11-07); the watchdog / lk_gpu_lightok still fall back to the CPU */
static int lk_gle_o = -1;    /* v5: Options > Display > Light Engine (id 56, ~/.landstalker_lightengine, env LANDSTALKER_LIGHTENGINE=0|1 wins): 1 GPU (default; the GPU also computes the light blocks, GL5c, user 2026-11-06 'GPU+ kann einfach Standard werden'; old value 2 = GPU), 0 CPU */
int lk_gle_get(void) { if (lk_gle_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_LIGHTENGINE"); char pth[512]; FILE *f; int v = LK_GLE_DEF; snprintf(pth, sizeof pth, "%%s/.landstalker_lightengine", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%%d", &v) != 1) v = LK_GLE_DEF; fclose(f); } if (e) v = atoi(e); lk_gle_o = v < 0 ? 0 : v > 2 ? 2 : v; } return lk_gle_o; }
void lk_gle_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_gle_get(); lk_gle_o = v < 0 ? 0 : v > 2 ? 2 : v; snprintf(pth, sizeof pth, "%%s/.landstalker_lightengine", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_gle_o); fclose(f); } }
static int lk_bl_o = -1;     /* v5 GL5d: Options > Graphics > Bounce Light (id 57, ~/.landstalker_bounce, env LANDSTALKER_BOUNCE=0|1 wins), default Off (user's check first); GPU light engines only */
int lk_bl_get(void) { if (lk_bl_o < 0) { const char *e = getenv("LANDSTALKER_BOUNCE"); lk_bl_o = e ? (atoi(e) ? 1 : 0) : 1; } return lk_bl_o; }   /* 2026-11-08 (user: options menu clean-up): no menu row any more, ON with Lighting (GPU light); the env still switches it for tests; the old file is ignored */
void lk_bl_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_bl_get(); lk_bl_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_bounce", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_bl_o); fclose(f); } }
static int lk_swsh_o = -1;   /* v5 GL5e: Options > Graphics > Sword Shadows (id 58, ~/.landstalker_swordshadow, env LANDSTALKER_SWORDSHADOW=0|1 wins), default On; GPU light engine only */
int lk_swsh_get(void) { if (lk_swsh_o < 0) { const char *e = getenv("LANDSTALKER_SWORDSHADOW"); lk_swsh_o = e ? (atoi(e) ? 1 : 0) : 1; } return lk_swsh_o; }   /* 2026-11-08 (user: options menu clean-up): no menu row any more, ON with Lighting (GPU light); the env still switches it for tests; the old file is ignored */
void lk_swsh_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_swsh_get(); lk_swsh_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_swordshadow", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_swsh_o); fclose(f); } }
static int lk_rf_o = -1;     /* v5 GL5f: Options > Graphics > Round Figures (id 59, ~/.landstalker_roundfig, env LANDSTALKER_ROUNDFIG=0|1 wins), default On; GPU light only */
int lk_rf_get(void) { if (lk_rf_o < 0) { const char *e = getenv("LANDSTALKER_ROUNDFIG"); lk_rf_o = e ? (atoi(e) ? 1 : 0) : 1; } return lk_rf_o; }   /* 2026-11-08 (user: options menu clean-up): no menu row any more, ON with Lighting (GPU light); the env still switches it for tests; the old file is ignored */
void lk_rf_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_rf_get(); lk_rf_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_roundfig", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_rf_o); fclose(f); } }
int lk_gl_slow;               /* v5: set by the GPU time watchdog (platform_sdl.c): the light pass was too slow -> CPU lighting for the rest of the run (the option is not changed) */
static int lk_gl_env = -2;    /* LANDSTALKER_GPULT (test aid) wins over the option: 0 CPU, 1 GPU, 2 compare harness */
int lk_gl_getmode(void) { if (lk_gl_env == -2) { const char *e = getenv("LANDSTALKER_GPULT"); lk_gl_env = e ? atoi(e) : -1; if (e && (lk_gl_env < 0 || lk_gl_env > 2)) lk_gl_env = 0; }
  lk_gl_mode = lk_gl_env >= 0 ? lk_gl_env : (lk_gle_get() && !lk_gl_slow) ? 1 : 0; if (lk_gl_mode == 1 && lk_gl_slow) lk_gl_mode = 0; return lk_gl_mode; }
static void lk_gl_put(int line, int i, int cls, int U, int V, int c0, int c1, int w) {
  int o = line * 448 + i;
  int q = ((V & 511) << 9) | (U & 511);
  if (cls == 1 && (lk_gl_pf & 1)) cls = 16 + lk_gl_fj;   /* a figure pixel: class 16 + figure */
  lk_gl_unlit[o] = (uint32_t)c0; lk_gl_ref[o] = (uint32_t)c1; lk_gl_cls[o] = (uint8_t)cls;
  lk_gl_flg[o] = (uint8_t)(cls ? (lk_gl_pf | ((lk_am_dn && lk_am_map[q]) ? 8 : 0) | ((lk_lt_nsh && lk_lt_dmap[q]) ? 64 : 0)) : 0);
  if (i == 0 || lk_gl_rowfr[line] != platform_frame_number()) { lk_gl_row[line] = ((uint32_t)(uint16_t)(int16_t)(U - i)) | ((uint32_t)(uint16_t)(int16_t)V << 16); lk_gl_rowfr[line] = platform_frame_number(); }
  lk_gl_capfr = platform_frame_number(); lk_gl_w = w; }
long lk_gl_realcap = -9;   /* v5: frame whose rows were composed unlit for the GPU (the present lights it even if the mode switched since: no unlit frame at a switch) */
static int lk_gl_pl[224 * 448], lk_gl_pn; int lk_gl_postprev;   /* GL4: pixels with a mix after the light this frame (reset to 'none' at the next frame) */
static void lk_gl_line(int line, int u0, int v, int w) {   /* GL4, once per captured line: picture position (U = u0 + i, V) + frame stamps */
  long f = platform_frame_number(); int j;
  if (lk_gl_postfr != f) { lk_gl_postfr = f; lk_gl_postprev = lk_gl_postany; lk_gl_postany = 0; for (j = 0; j < lk_gl_pn; j++) { lk_gl_post[0][lk_gl_pl[j]] = 0; lk_gl_post[1][lk_gl_pl[j]] = 0xFFFFFFu; } lk_gl_pn = 0; }
  lk_gl_row[line] = ((uint32_t)(uint16_t)(int16_t)u0) | ((uint32_t)(uint16_t)(int16_t)v << 16); lk_gl_rowfr[line] = f; lk_gl_capfr = f; lk_gl_realcap = f; lk_gl_w = w; }
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
static int lk_gl_wideopt(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_LT_WIDE"); v = e ? atoi(e) != 0 : 1; } return v; }   /* LK_GLWIDE v2: wide fires (0 = old two point flames) */
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
  { const float *sdd = lk_lt_sun && lk_dn_on && lk_lt_sdf[2] > 0.0f ? lk_lt_sdf : lk_lt_sd; fu[24] = sdd[0]; fu[25] = sdd[1]; fu[26] = sdd[2]; }   /* LK_DAYNIGHT v5: figure shadows with the blended direction (lk_lt_figsun) */
  for (k = 0; k < LK_LT_NSH; k++) { const lk_lt_shaft_t *S = &lk_lt_sh[k]; fu[32 + 8 * k] = S->x; fu[33 + 8 * k] = S->y; fu[34 + 8 * k] = S->z; fu[35 + 8 * k] = S->r; fu[36 + 8 * k] = S->d[0]; fu[37 + 8 * k] = S->d[1]; fu[38 + 8 * k] = S->d[2]; fu[39 + 8 * k] = 0.0f; }
  for (k = 0; k < LK_LT_ML; k++) { const lk_lt_light *Lq = &lk_lt_l[k];
    lp[4 * k] = Lq->x; lp[4 * k + 1] = Lq->y; lp[4 * k + 2] = Lq->z; lp[4 * k + 3] = Lq->rad > 0.0f ? Lq->rad : LK_LT_RAD;
    lc[4 * k] = Lq->r; lc[4 * k + 1] = Lq->g; lc[4 * k + 2] = Lq->b; lc[4 * k + 3] = Lq->k > 0.0f ? Lq->k : 1.0f;
    lf[4 * k] = k < lk_lt_nl ? lk_lt_flk[k] : 0.0f; lf[4 * k + 1] = Lq->lava == 2 ? 1.0f : 0.0f; lf[4 * k + 2] = lk_gl_wideopt() ? Lq->hw : 0.0f; lf[4 * k + 3] = (float)Lq->tan + 4.0f * floorf(Lq->hv + 0.5f);
    if (k < lk_lt_nl && Lq->own > 0.0f && !(lk_gl_wideopt() && Lq->hw > 0.5f)) lf[4 * k + 3] = -Lq->own; }   /* LK_GLCARRIER v1: w = -radius for a flame on its own stand (set by patch_lights from data "carrier"; LANDSTALKER_LT_CARRIER=0 = off) */   /* LK_GLWIDE v2: w = along (1 x / 2 y) + 4 * half height */   /* LK_GLWIDE v2: the fire width for termS */
  for (k = 0; k < 16; k++) { fg[4 * k] = lk_lt_f[k].fx; fg[4 * k + 1] = lk_lt_f[k].fy; fg[4 * k + 2] = lk_lt_f[k].fz; fg[4 * k + 3] = lk_lt_f[k].sun; fa[4 * k] = (float)lk_lt_f[k].ax; fa[4 * k + 1] = (float)lk_lt_f[k].ay; fa[4 * k + 2] = (float)lk_lt_f[k].tag; fa[4 * k + 3] = 0.0f; }
  return 1; }
/* v5 GL5a: the world of the shadow terms for the GPU (re-upload when the returned hash changes):
   w  = 74 x 222 RGBA: rows 0..73 top lo / hi, thin lo / hi; rows 74..147 back wall bits lk_lt_vw, water, early exit field lk_lt_hd lo / hi (current sun / key direction); rows 148..221 b / a: lk_lt_hdn (next sun direction);
   w2 = 74 x 222 RGBA: rows 0..73 sun height (game height, ground of a small object for class 1 objects; -32768 = void) lo / hi, bush / pine kind lk_lt_tk, radius lk_lt_tr;
        rows 74..147 tree top lk_lt_tt lo / hi, base lk_lt_tb lo / hi; rows 148..221 the game height lk_lt_gh lo / hi;
   fn = 296 x 888 RGBA: rows 0..295 object top lk_lt_fh lo / hi, owner lk_lt_fo lo / hi (indoors LK_LT_IFO = data height); rows 296..591 proxy lk_lt_fp, its type, the owner's class lk_lt_ocl;
        rows 592..887 (v9) slab bottom lk_lt_sb lo / hi, top lk_lt_st lo / hi;
   px = 26 x 255 RGBA: per proxy x0 y0 | z0 ridge | 96 lathe profile bytes;
   f2 = 296 x 296 RGBA: the view ray fields lk_lt_vt / lk_lt_vg (layer A / B) lo / hi; w2 rows 148..221 also carry lk_lt_obj in b / a.
   sc: 0 sun room, 1 room light (AO) on, 2 main floor height, 3 AO strength, 4 AO wall share, 5 ztop, 6..8 sun / key direction, 9 key light room, 10 key back wall height, 11 key penumbra. */
unsigned lk_gl_world(uint32_t *w, uint32_t *w2, uint32_t *fn, uint32_t *px, uint32_t *f2, float *sc) { int x, y, k, nhand = 0; unsigned h = 2166136261u;   /* LK_GLFINE v1: fn rows 592..887 = slabs */
  #define LK_GL_H(v) (h = (h ^ (uint32_t)(v)) * 16777619u)
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int o = y * 74 + x, ob = lk_lt_obj[y][x], hc = lk_lt_gh[y][x];
    if (ob > 0 && ob < 1024 && lk_lt_ocl[ob] == 1) { hc = lk_lt_sgnd[ob]; if (hc == -32768) hc = -32767; }
    w[o] = (uint32_t)(uint16_t)lk_lt_top[y][x] | ((uint32_t)(uint16_t)lk_lt_thin[y][x] << 16); w[5476 + o] = (uint32_t)lk_lt_vw[y][x] | ((uint32_t)(lk_lt_wat[y][x] ? 1 : 0) << 8) | ((uint32_t)(uint16_t)lk_lt_hd[y][x] << 16);
    { int i2, j2, hm = 0; for (j2 = 0; j2 < 4; j2++) for (i2 = 0; i2 < 4; i2++) if (lk_lt_mown[4 * y + j2][4 * x + i2] == 1) hm = 1;   /* LK_GLROOM v1: the cell holds a hand-made model (bit 9) */
      if (hm) { w[5476 + o] |= 1u << 9; nhand++; if (lk_lt_sun) w[o] = (w[o] & 0xFFFFu) | (0x8001u << 16); } }   /* outdoors also in the (unused) thin half: aoh2 reads it with the height (no extra fetch) */
    { extern uint16_t lk_lt_cpk_at(int x, int y); w[2 * 5476 + o] = ((uint32_t)(uint16_t)lk_lt_hdn[y][x] << 16) | ((w[5476 + o] >> 9) & 1u ? 0u : lk_lt_cpk_at(x, y)); }   /* LK_GLROOM v1: no side record for a hand model cell (its shadow map casts it; saves a fetch per neighbour and march step) */   /* GL5c: the early exit field of the NEXT sun direction (sunn); low half: side penumbra objects lk_lt_cpk */
    w2[o] = (uint32_t)(uint16_t)hc | ((uint32_t)lk_lt_tk[y][x] << 16) | ((uint32_t)lk_lt_tr[y][x] << 24); w2[5476 + o] = (uint32_t)(uint16_t)lk_lt_tt[y][x] | ((uint32_t)(uint16_t)lk_lt_tb[y][x] << 16); w2[2 * 5476 + o] = (uint32_t)(uint16_t)lk_lt_gh[y][x] | ((uint32_t)(uint16_t)lk_lt_obj[y][x] << 16);
    LK_GL_H(w[o]); LK_GL_H(w[5476 + o]); LK_GL_H(w[2 * 5476 + o]); LK_GL_H(w2[o]); LK_GL_H(w2[5476 + o]); LK_GL_H(w2[2 * 5476 + o]); }
  { const char *e = getenv("LANDSTALKER_LT_CPKDUMP"); int x0, y0; if (e && sscanf(e, "%%d,%%d", &x0, &y0) == 2) { extern uint16_t lk_lt_cpk_at(int x, int y); printf("cpkdump room %%d around %%d,%%d (cpk hex / model bit / gh):\n", lk_o_room, x0, y0);   /* test aid: side penumbra records */
    for (y = y0 - 2; y <= y0 + 2; y++) { printf("cpk %%2d:", y); for (x = x0 - 3; x <= x0 + 3; x++) printf("  %%2d:%%04X/%%d/%%d", x, lk_lt_cpk_at(x, y), (w[5476 + y * 74 + x] >> 9) & 1, lk_lt_gh[y][x]); printf("\n"); } } }
  for (y = 0; y < LK_LT_FN; y++) for (x = 0; x < LK_LT_FN; x++) { int o = y * LK_LT_FN + x, q = lk_lt_fp[y][x], fo = lk_lt_fo[y][x];
    fn[o] = (uint32_t)(uint16_t)lk_lt_fh[y][x] | ((uint32_t)(uint16_t)fo << 16);
    { extern unsigned lk_lt_m3q_at(int x, int y); fn[LK_LT_FN * LK_LT_FN + o] = (uint32_t)q | ((uint32_t)(q ? lk_lt_px[q - 1].type : 0) << 8) | ((uint32_t)(fo > 0 && fo < 1024 ? lk_lt_ocl[fo] : 0) << 16) | (lk_lt_m3q_at(x >> 2, y >> 2) << 24); }   /* top byte: side penumbra bound lk_lt_m3q of the cell */
    f2[o] = (uint32_t)(uint16_t)lk_lt_vt[y][x] | ((uint32_t)(uint16_t)lk_lt_vg[y][x] << 16);
    fn[2 * LK_LT_FN * LK_LT_FN + o] = (uint32_t)(uint16_t)lk_lt_sb[y][x] | ((uint32_t)(uint16_t)lk_lt_st[y][x] << 16);   /* v9 slabs: bottom lo / hi, top lo / hi */
    fn[3 * LK_LT_FN * LK_LT_FN + o] = lk_lt_hk[y][x] ? ((uint32_t)(uint16_t)lk_lt_hb[y][x] | ((uint32_t)lk_lt_hk[y][x] << 16) | ((uint32_t)lk_lt_hs[y][x] << 24)) : 0u;   /* v9 slab halo: bottom lo / hi, k, height / 2 */
    LK_GL_H(fn[3 * LK_LT_FN * LK_LT_FN + o]);
    fn[4 * LK_LT_FN * LK_LT_FN + o] = lk_lt_mown[y][x] ? ((uint32_t)lk_lt_mown[y][x] | ((uint32_t)(lk_lt_mb[y][x] - lk_lt_mg[y][x] < 0 ? 0 : lk_lt_mb[y][x] - lk_lt_mg[y][x] > 255 ? 255 : lk_lt_mb[y][x] - lk_lt_mg[y][x]) << 8) | ((uint32_t)(uint16_t)lk_lt_mg[y][x] << 16)) : 0u; LK_GL_H(fn[4 * LK_LT_FN * LK_LT_FN + o]);   /* LK_GLMODEL v1: model owned, model bottom - ground (g), ground below the model (b / a) */
    LK_GL_H(fn[o]); LK_GL_H(fn[LK_LT_FN * LK_LT_FN + o]); LK_GL_H(fn[2 * LK_LT_FN * LK_LT_FN + o]); LK_GL_H(f2[o]); }
  for (k = 0; k < 255; k++) { const lk_lt_proxy *P = &lk_lt_px[k]; uint32_t *r = px + k * 26; int j;
    r[0] = (uint32_t)(uint16_t)P->x0 | ((uint32_t)(uint16_t)P->y0 << 16); r[1] = (uint32_t)(uint16_t)P->z0 | ((uint32_t)(uint16_t)P->ridge << 16);
    for (j = 0; j < 24; j++) r[2 + j] = (uint32_t)lk_lt_prof[k][4 * j] | ((uint32_t)lk_lt_prof[k][4 * j + 1] << 8) | ((uint32_t)lk_lt_prof[k][4 * j + 2] << 16) | ((uint32_t)lk_lt_prof[k][4 * j + 3] << 24);
    if (k < lk_lt_npx) for (j = 0; j < 26; j++) LK_GL_H(r[j]); }
  sc[0] = (float)lk_lt_sun; sc[1] = (float)lk_lt_aor; sc[2] = (float)lk_lt_zref; sc[3] = lk_lt_aok < 0.0f ? 0.55f : lk_lt_aok; sc[4] = lk_lt_aotop < 0.0f ? 0.0f : lk_lt_aotop;
  sc[5] = (float)lk_lt_ztop; sc[6] = lk_lt_sd[0]; sc[7] = lk_lt_sd[1]; sc[8] = lk_lt_sd[2]; sc[9] = (float)lk_lt_key;
  { const char *e = getenv("LANDSTALKER_LT_KBW"); float v = e ? (float)atof(e) : 40.0f; sc[10] = v < 0.0f ? 0.0f : v; }   /* as lk_lt_keyvisd */
  { const char *e = getenv("LANDSTALKER_LT_KPEN"), *e2 = getenv("LANDSTALKER_LT_KBWSOFT"); float v = e ? (float)atof(e) : 3.0f; sc[11] = v < 0.5f ? 0.5f : v; { const char *e4 = getenv("LANDSTALKER_LT_KSLANT"); if (e4 && !atoi(e4)) sc[11] += 2000.0f; } if (e2 && !atoi(e2)) sc[11] = -sc[11]; }   /* 2026-11-08: negative = old knife-sharp back wall (lk_lt_kbwsoft) */
  sc[12] = (float)lk_lt_zmax; sc[13] = (lk_lt_sun && lk_lt_fhmax > -32768) ? 1.0f : 0.0f;   /* GL5b: the view ray: start height, fine field ray (lk_lt_rayf) or cell ray (lk_lt_ray) */
  sc[14] = lk_lt_sdn[0]; sc[15] = lk_lt_sdn[1]; sc[16] = lk_lt_sdn[2]; sc[17] = (lk_lt_sun && lk_dn_upd && lk_dn_hdok) ? 1.0f : 0.0f;   /* GL5c: sunn for the next sun direction */
  sc[18] = lk_lt_kA; sc[19] = lk_lt_kK; sc[20] = lk_lt_sh[0].cr; sc[21] = lk_lt_sh[0].cg; sc[22] = lk_lt_sh[0].cb; sc[23] = (lk_lt_key && !lk_lt_nl) ? 1.0f : 0.0f;   /* the finished key light km */
  sc[28] = nhand > 0 ? 1.0f : 0.0f;   /* LK_GLROOM v1: the room has hand-made model cells (uHand: every per-sample model test is skipped without them) */
  sc[24] = (float)lk_lt_ifine; sc[25] = (float)lk_lt_nslab; sc[26] = (float)lk_lt_pinet(); sc[27] = (float)lk_lt_bushe();   /* v9: fine field indoors / slabs / pine tiers / bush crowns */
  for (k = 0; k < 29; k++) { union { float f; uint32_t u; } cv; cv.f = sc[k]; LK_GL_H(cv.u); }
  #undef LK_GL_H
  return h | 1u; }
/* LK_GLMODEL v1 (REAL 3D LIGHT SHAPES stage 1): the triangles of the room's Blender meshes for the GPU model buffer (indoors, LANDSTALKER_LT_MODEL, lk_lt_finebuild marked them) */
int lk_gl_mgenix = -1, lk_gl_mobjix = -1;   /* LK_GLROOM v1 / LK_GLOBJ v1 */
static struct timespec lk_gm_tt; void lk_gm_t0(void) { clock_gettime(CLOCK_MONOTONIC, &lk_gm_tt); } double lk_gm_ms(void) { return lk_sm_ms_since(&lk_gm_tt); }   /* LK_GLROOM v1: model buffer draw time (test aid) */
int lk_gl_mlist(const float **tri, int *ntri, int max) { int q, n = 0; lk_gl_mgenix = -1; lk_gl_mobjix = -1;
  if (!lk_lt_modelopt() || !lk_lt_nmodel) return 0;   /* indoors + outdoors (lk_lt_finebuild marked them) */
  for (q = 0; lk_lt_corr[q].room >= 0 && n < max; q++) { const int16_t *a = lk_lt_corr[q].a;
    if (lk_lt_corr[q].room != lk_o_room || lk_lt_corr[q].op != 5 || !lk_lt_msok(a[4])) continue;
    tri[n] = lk_lt_mtris[a[4]]; ntri[n] = lk_lt_mtrin[a[4]]; n++; }
  { static int dr = -1; if (dr < 0) { const char *e = getenv("LANDSTALKER_LT_ROOMDRAW"); dr = e ? atoi(e) : 1; } if (!dr) return n; }   /* test aid: =0 the room model is built but not drawn */
  if (lk_lt_omn > 0 && n < max) { lk_gl_mobjix = n; tri[n] = lk_lt_omt; ntri[n] = lk_lt_omn; n++; }   /* LK_GLOBJ v1: the room's trees / bushes */
  if (lk_lt_rmn > 0 && n < max) { lk_gl_mgenix = n; tri[n] = lk_lt_rmt; ntri[n] = lk_lt_rmn; n++; }   /* LK_LTROOM v1: the room's generated box model (lk_gl_mgenix: its index for the model buffer pass) */
  return n; }
/* v5 GL5a: per block pixel the object of its view ray (b->robj) and whether layer A is drawn there (lk_o_fetch), for the sun's 'own object' rule */
/* v5 GL5a: light shafts for the GPU: per shaft x y z r | k h | d (3 x 3 vec4); returns their number */
int lk_gl_shafts(float *o) { int k; for (k = 0; k < LK_LT_NSH; k++) { const lk_lt_shaft_t *S = &lk_lt_sh[k]; float *a = o + 12 * k;
    a[0] = S->x; a[1] = S->y; a[2] = S->z; a[3] = S->r; a[4] = S->k; a[5] = S->h; a[6] = a[7] = 0.0f; a[8] = S->d[0]; a[9] = S->d[1]; a[10] = S->d[2]; a[11] = 0.0f; }
  return lk_lt_nsh; }
/* v5 GL5c: cheap keys of what the GPU blocks depend on: hard = the room's world (a change makes every GPU block invalid), soft = the sun / key direction and the
   next sun step (a change makes the blocks stale: they stay on screen until they are recomputed) */
void lk_gl_wkey(unsigned *hard, unsigned *soft, float *dirs, int *sunn) { unsigned h = 2166136261u, f = 2166136261u; int k; union { float x; uint32_t u; } cv;
  for (k = 0; k < 3; k++) { dirs[k] = lk_lt_sd[k]; dirs[3 + k] = lk_lt_sdn[k]; } *sunn = lk_lt_sun && lk_dn_upd && lk_dn_hdok;   /* GL5c: for the sun step swap on the GPU */
  #define LK_GL_K(hh, v) (hh = (hh ^ (uint32_t)(v)) * 16777619u)
  LK_GL_K(h, lk_lt_gen); LK_GL_K(h, lk_lt_room); LK_GL_K(h, lk_lt_hash); LK_GL_K(h, lk_lt_nl); LK_GL_K(h, lk_lt_nsh); LK_GL_K(h, lk_lt_sun); LK_GL_K(h, lk_lt_key); LK_GL_K(h, lk_lt_aor);
  LK_GL_K(h, lk_lt_ztop); LK_GL_K(h, lk_lt_zmax); LK_GL_K(h, lk_lt_zref); LK_GL_K(h, lk_lt_fhmax); LK_GL_K(h, lk_lt_npx); LK_GL_K(h, lk_o_room);
  for (k = 0; k < lk_lt_nl; k++) { cv.x = lk_lt_l[k].hw; LK_GL_K(h, cv.u); cv.x = lk_lt_l[k].x; LK_GL_K(h, cv.u); cv.x = lk_lt_l[k].y; LK_GL_K(h, cv.u); cv.x = lk_lt_l[k].z; LK_GL_K(h, cv.u); cv.x = lk_lt_l[k].rad; LK_GL_K(h, cv.u); cv.x = lk_lt_l[k].k; LK_GL_K(h, cv.u); }
  for (k = 0; k < lk_lt_nsh; k++) { cv.x = lk_lt_sh[k].x; LK_GL_K(h, cv.u); cv.x = lk_lt_sh[k].y; LK_GL_K(h, cv.u); cv.x = lk_lt_sh[k].z; LK_GL_K(h, cv.u); cv.x = lk_lt_sh[k].r; LK_GL_K(h, cv.u); }
  for (k = 0; k < 3; k++) { cv.x = lk_lt_sd[k]; LK_GL_K(f, cv.u); }
  if (lk_lt_sun && lk_dn_upd && lk_dn_hdok) { LK_GL_K(f, lk_dn_gen); for (k = 0; k < 3; k++) { cv.x = lk_lt_sdn[k]; LK_GL_K(f, cv.u); } }
  #undef LK_GL_K
  *hard = h | 1u; *soft = f | 1u; }
/* v5 GL5c: the nearest lights of a block (the list of lk_lt_blockcalc, without a CPU block) */
void lk_gl_blist5(int bx, int by, uint32_t *a, uint32_t *b2, int *nlo) { int k, nl = 0, U0 = bx * 32, V0 = by * 32; uint8 li[LK_LT_NL]; float bd[LK_LT_NL];
  for (k = 0; k < lk_lt_nl; k++) {
    float lu = lk_lt_l[k].x - lk_lt_l[k].y + 1184.0f, lv = (lk_lt_l[k].x + lk_lt_l[k].y) * 0.5f - lk_lt_l[k].z, du = lu - (float)(U0 + 16), dv = lv - (float)(V0 + 16), d2 = du * du + dv * dv; int m;
    { float lim = (lk_lt_l[k].rad > 0.0f ? lk_lt_l[k].rad : LK_LT_RAD) * 1.6f + 24.0f; if (fabsf(du) >= lim || fabsf(dv) >= lim) continue; }   /* 2026-11-08 (user: room 58 'harte Schattenkante am Teppich'): the reach of EACH light (castle standing torches 260, was the fixed 120: the block boundary cut a torch that still gave 10 percent) */
    if (nl < LK_LT_NL) m = nl++; else { int q; m = 0; for (q = 1; q < LK_LT_NL; q++) if (bd[q] > bd[m]) m = q; if (bd[m] <= d2) continue; }
    li[m] = (uint8)k; bd[m] = d2; }
  *a = *b2 = 0; *nlo = nl;
  for (k = 0; k < 4; k++) { if (k < nl) *a |= (uint32_t)li[k] << (8 * k); if (k + 4 < nl) *b2 |= (uint32_t)li[k + 4] << (8 * k); } }
/* v5 CPU saving: the platform hands back the GPU blocks' room A (face sun sunn ao) and room B (z lo hi beam pool) planes one frame later (pixel buffer, no stall) */
void lk_gl_surfput(int bx, int by, const uint32_t *A, const uint32_t *Bp, int sg) { lk_gs_t *g; int i;
  if (bx < 0 || by < 0 || bx >= 76 || by >= 38) return;
  if (!(g = lk_gs[by][bx]) && !(g = lk_gs[by][bx] = (lk_gs_t *)malloc(sizeof *g))) return;
  for (i = 0; i < 1024; i++) { g->a[i] = (A[i] & 0xFFFFFFu) | (sg ? 0x1000000u : 0u); g->z[i] = (int16_t)(Bp[i] & 0xFFFF); }
  g->gen = lk_lt_gen; g->dng = lk_dn_gen; }
void lk_gl_surfswap(void) { int x, y, i; for (y = 0; y < 38; y++) for (x = 0; x < 76; x++) { lk_gs_t *g = lk_gs[y][x]; if (!g || g->gen != lk_lt_gen) continue;   /* a GPU sun step swap: sun <- sunn */
    for (i = 0; i < 1024; i++) if (g->a[i] >> 24) g->a[i] = (g->a[i] & 0xFF00FFu) | (((g->a[i] >> 16) & 255) << 8); } }
void lk_gl5_cpuset(void) { lk_gl5_cpufr = platform_frame_number(); }
void lk_gl_bextra(int bx, int by, uint32_t *o) { const lk_lt_blk *b = lk_lt_b[by][bx]; int i, pal, pr;
  for (i = 0; i < 1024; i++) o[i] = (uint32_t)(uint16_t)(b ? b->robj[i] : 0) | (((b ? b->la[i] : lk_o_fetch(lk_o_pa, bx * 32 + (i & 31), by * 32 + (i >> 5), &pal, &pr, 0) != 0) ? 1u : 0u) << 16); }   /* the bit the block's view ray used */
const uint16_t *lk_gl_fmk(void) { return &lk_lt_fmk[0][0]; }   /* figure shadow box mask 224 x 448 (lk_lt_infb) */
/* per light k / figure j: row j = card normal x, y, pair, 0; row 16 + j = the shadow box x0 y0 x1 y1 (96 x 32 RGBA floats) */
void lk_gl_pairs(float *o) { int k, j; for (j = 0; j < 16; j++) for (k = 0; k < 96; k++) { float *a = o + 4 * (j * 96 + k), *b = o + 4 * ((16 + j) * 96 + k);
  a[0] = lk_lt_pn[k][j][0]; a[1] = lk_lt_pn[k][j][1]; a[2] = lk_lt_pair[k][j] ? 1.0f : 0.0f; a[3] = 0.0f; b[0] = (float)lk_lt_pbox[k][j][0]; b[1] = (float)lk_lt_pbox[k][j][1]; b[2] = (float)lk_lt_pbox[k][j][2]; b[3] = (float)lk_lt_pbox[k][j][3]; } }
/* class + own-sprite tag per screen pixel (RGBA: class, class, hidden figure tag (LK_LTHIDE v1, lk_lt_spre2), tag): the silhouettes of the figure shadows */
void lk_gl_clstag(uint32_t *o) { int y, x; for (y = 0; y < 224; y++) for (x = 0; x < 448; x++) { uint32_t c = lk_gl_cls[y * 448 + x] & 255u; int sp = (lk_o_spr[y][x] & 0x200) != 0; o[y * 448 + x] = c | (c << 8) | ((uint32_t)(sp ? lk_lt_spre2[y][x] : 0) << 16) | ((uint32_t)(sp ? lk_lt_spre[y][x] : 0) << 24); } }
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
    # LK_GLUNPAINT v1 (user 2026-11-09: 'kannst du den Teppich unter dem Tisch im normalen Gruen zeichnen, so dass der Tisch nur unseren Schatten wirft?'):
    # the shadow the artist PAINTED under furniture on legs (darker carpet / floor tiles) would double our GPU model shadow; while the GPU light with the
    # 3D models is on, the plane B cells on the floor footprint of a piece (data/light_proxies.json op 'unpaint') draw the same tile without the shadow
    # (unpaint_tiles, per tileset).  Lighting off / CPU light / LANDSTALKER_LT_UNPAINT=0: the original tiles (the CPU light keeps the table as a box).
    rep(a, r'''/* LK_GLUNPAINT v1 (tools/patch_gpulight.py): painted furniture shadows off while the GPU light shades the furniture models */
static int lk_gl_upopt(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_LT_UNPAINT"); v = e ? atoi(e) : 1; } return v; }
void lk_gl_unpaint(void) { int q, ts = -1;
  if (!lk_gl_upopt() || !lk_lt_get() || !lk_lt_modelopt() || lk_gl_getmode() != 1 || !lk_gl_realok()) return;
  for (q = 0; lk_lt_corr[q].room >= 0; q++) { const int16_t *a = lk_lt_corr[q].a; int X, Y;
    if (lk_lt_corr[q].op != 11 || lk_lt_corr[q].room != lk_o_room) continue;
    if (a[5] == 1) { int tc, tr;   /* LK_GLUNPAINTA v1: shadow dots painted INTO the object's plane A tiles: lk_o_fetch / the GPU compositor drop colour a[4] there (bits 17 / 18..21) */
      for (tr = a[1]; tr <= a[3]; tr++) for (tc = a[0]; tc <= a[2]; tc++) if (tc >= 0 && tc < 304 && tr >= 0 && tr < 152 && (lk_o_pa[tr][tc] & 0x10000)) lk_o_pa[tr][tc] = (lk_o_pa[tr][tc] & 0x1FFFFu) | 0x20000u | ((uint32)(a[4] & 15) << 18);
      continue; }
    if (ts < 0) ts = OB(OL(0xA0A00) + 8u * (uint32_t)lk_o_room + 4u) & 0x1F;   /* the room's tileset (as lk_lt_shafts) */
    for (Y = 16 * a[1]; Y < 16 * a[3] + 16; Y += 2) for (X = 16 * a[0]; X < 16 * a[2] + 16; X += 2) {   /* the floor footprint of the cells, 2 unit steps */
      int cc = (X - Y + 1184) >> 3, rr = ((X + Y) / 2 - a[4]) >> 3, k; uint32 w;
      if (cc < 0 || cc >= 304 || rr < 0 || rr >= 152) continue;
      w = lk_o_pb[rr][cc]; if (!(w & 0x10000)) continue;
      for (k = 0; lk_lt_uptile[k][0] >= 0; k++) if (lk_lt_uptile[k][0] == ts && (int)(w & 0x7FF) == lk_lt_uptile[k][1]) { lk_o_pb[rr][cc] = (w & ~0x7FFu) | (uint32)lk_lt_uptile[k][2]; break; } } } }
''' + a)
    rep("static void lk_o_build(void) {", "void lk_gl_unpaint(void);   /* LK_GLUNPAINT v1 (tools/patch_gpulight.py) */\nstatic void lk_o_build(void) {")
    rep("  lk_o_exon = 0; lk_o_sprites(chosen, 1, 0,", "  lk_gl_unpaint();   /* LK_GLUNPAINT v1: painted furniture shadows off under the GPU light (tools/patch_gpulight.py) */\n  lk_o_exon = 0; lk_o_sprites(chosen, 1, 0,")
    # v5 GL5b: the block keeps the 'layer A drawn' bit its view ray used (animated tiles change it between the block's computation and a later look)
    rep("int16_t robj[1024]; int sungen; } lk_lt_blk;", "int16_t robj[1024]; int sungen; uint8 la[1024]; } lk_lt_blk;")
    rep("b->face[i] = (uint8)lk_lt_ray(U0 + (i & 31), V0 + (i >> 5), &z); b->z[i] = (int16_t)z; robj[i] = (int16_t)lk_lt_rob; }",
        "b->face[i] = (uint8)lk_lt_ray(U0 + (i & 31), V0 + (i >> 5), &z); b->z[i] = (int16_t)z; robj[i] = (int16_t)lk_lt_rob; b->la[i] = (uint8)lk_lt_rayA; }")
    a = "/* ---- LK_LIGHTS v8: lighting from flames"
    rep(a, "static int lk_gl_pf, lk_gl_fj; static unsigned lk_gl_sunver;   /* %s (tools/patch_gpulight.py): used inside the Lighting code */\n" % VER +
        "long lk_gl5_cpufr = -99;   /* v5 CPU SAVING: frame in which the GPU computed the light blocks (platform_sdl.c); while it is recent the CPU computes none (no prefetch, no on-demand) */\n"
        "static int lk_gl5_cpuoff(void) { return lk_gl5_cpufr >= platform_frame_number() - 2; }\n"
        "typedef struct { uint32_t a[1024]; int16_t z[1024]; int gen, dng; } lk_gs_t; static lk_gs_t *lk_gs[38][76];   /* the GPU blocks' face / sun / sunn / sunn-valid + z, read back for the particles (lk_am_surf) */\n" + a)
    rep("if (idle && lk_lt_on && lk_lt_umax >= lk_lt_umin) {   /* v7 PREFETCH", "if (idle && lk_lt_on && lk_lt_umax >= lk_lt_umin && !lk_gl5_cpuoff()) {   /* v5 GL5: not while the GPU computes the blocks */   /* v7 PREFETCH")
    rep("if (!lk_lt_pre && lk_lt_odn >= lk_lt_odcap) return 0;", "if (!lk_lt_pre && (lk_lt_odn >= lk_lt_odcap || lk_gl5_cpuoff())) return 0;   /* v5 GL5: no on-demand blocks while the GPU computes them */")
    rep("  i = ((V & 31) << 5) | (U & 31); if (b->face[i] != 1) return 0;",
        "  i = ((V & 31) << 5) | (U & 31); if (b->face[i] != 1) return 0;   /* (v5 GL5: no CPU block -> lk_gs below) */")
    rep("  if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH || !(b = lk_lt_b[by][bx])) return 0;\n  i = ((V & 31) << 5) | (U & 31);",
        "  if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH) return 0;\n"
        "  if (!(b = lk_lt_b[by][bx])) { const lk_gs_t *g = lk_gs[by][bx]; uint32_t w; if (!g || g->gen != lk_lt_gen) return 0;   /* v5 GL5: the surface the GPU computed */\n"
        "    i = ((V & 31) << 5) | (U & 31); w = g->a[i]; if ((w & 255) != 1) return 0; lk_lt_pos(U, V, g->z[i], px, py); *pz = (float)g->z[i];\n"
        "    { int s0 = (int)((w >> 8) & 255), s1 = (int)((w >> 16) & 255); *sun = lk_lt_sun ? (lk_dn_mix && (w >> 24) && g->dng == lk_dn_gen ? s0 + ((s1 - s0) * lk_dn_mix >> 8) : s0) : 255; } return 1; }\n"
        "  i = ((V & 31) << 5) | (U & 31);")
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
uniform vec4 uLP[96]; uniform vec4 uLC[96]; uniform vec4 uLF[96]; uniform vec4 uFG[16]; uniform vec4 uFA[16]; uniform float uSwSh;
float B(float v) { return floor(v * 255.0 + 0.5); }
float FNX(float f) { if (f == 2.0) return 1.0; if (f < 4.0 || f > 19.0) return 0.0; if (f == 4.0) return 0.707106781; if (f == 5.0) return 0.831469612; if (f == 6.0) return 0.923879533; if (f == 7.0) return 0.98078528; if (f == 8.0) return 1.0; if (f == 9.0) return 0.98078528; if (f == 10.0) return 0.923879533; if (f == 11.0) return 0.831469612; if (f == 12.0) return 0.707106781; if (f == 13.0) return 0.555570233; if (f == 14.0) return 0.382683432; if (f == 15.0) return 0.195090322; if (f == 16.0) return 6.123234e-17; if (f == 17.0) return -0.195090322; if (f == 18.0) return -0.382683432; if (f == 19.0) return -0.555570233; return 0.0; }   /* v9 lk_lt_fnx: face codes 4..19 = slanted faces */
float FNY(float f) { if (f == 3.0) return 1.0; if (f < 4.0 || f > 19.0) return 0.0; if (f == 4.0) return -0.707106781; if (f == 5.0) return -0.555570233; if (f == 6.0) return -0.382683432; if (f == 7.0) return -0.195090322; if (f == 8.0) return 0.0; if (f == 9.0) return 0.195090322; if (f == 10.0) return 0.382683432; if (f == 11.0) return 0.555570233; if (f == 12.0) return 0.707106781; if (f == 13.0) return 0.831469612; if (f == 14.0) return 0.923879533; if (f == 15.0) return 0.98078528; if (f == 16.0) return 1.0; if (f == 17.0) return 0.98078528; if (f == 18.0) return 0.923879533; if (f == 19.0) return 0.831469612; return 0.0; }   /* v9 lk_lt_fny */
float trc(float v) { return v < 0.0 ? -floor(-v) : floor(v); }   /* C (int) */
float rne(float v) { float r = floor(v + 0.5); if (r - v == 0.5 && mod(r, 2.0) != 0.0) r -= 1.0; return r; }   /* lrintf */
float bit(float m, int j) { return mod(floor(m / exp2(float(j))), 2.0); }
vec3 lit(vec3 c, vec3 f) { return min(floor(c * f), vec3(255.0)); }
vec4 fin(vec3 o, vec2 fc) {   /* GL4: the emissive mix after the light (offset p0, slope (p1 - p0) / 255) */
  if (uPost > 0.5) { vec4 a = texture2D(post, (fc + 0.5) / vec2(448.0, 448.0)), b = texture2D(post, (vec2(fc.x, fc.y + 224.0) + 0.5) / vec2(448.0, 448.0));
    if (a.rgb != vec3(0.0) || b.rgb != vec3(1.0)) { vec3 p0 = vec3(B(a.r), B(a.g), B(a.b)), p1 = vec3(B(b.r), B(b.g), B(b.b)); o = floor(p0 + (p1 - p0) * o / 255.0 + 0.5); } }
  return vec4(clamp(o, 0.0, 255.0) / 255.0, 1.0); }
float tagAt(float x, float y) { return B(texture2D(cls, (vec2(x, y) + 0.5) / vec2(448.0, 224.0)).a); }
bool ownAt(float x, float y, float t) { vec4 c = texture2D(cls, (vec2(x, y) + 0.5) / vec2(448.0, 224.0)); return B(c.a) == t || B(c.b) == t; }   /* LK_LTHIDE v1: own pixel, also where another figure hides it */
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
    if (mx >= 0.0 && mx < 448.0 && my >= 0.0 && my < 224.0 && ownAt(mx, my, Fa.z)) return true; }
  return false; }
float shadowed(vec3 p, int li, float fm, float cx, float cy) {   /* lk_lt_shadowed */
  vec4 L = uLP[li]; float best = 0.0;   /* LK_LTSHMAX v1: the strongest figure on the ray, not the first */
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
      if (ux >= 0.0 && ux < 448.0 && uy >= 0.0 && uy < 224.0 && ownAt(ux, uy, Fa.z)) hit += 1.0; }
    if (hit > 0.0) { vec3 e = L.xyz - p; float d = t * sqrt(e.x * e.x + e.y * e.y + e.z * e.z), w = (60.0 - d) * (1.0 / 40.0);
      w = w >= 1.0 ? 1.0 : w > 0.0 ? w : 0.0; best = max(best, w * hit / 9.0); if (best >= 1.0) return best; } }
  return best; }   /* LK_LTSHMAX v1 */
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
    if (u > 0.0 && uNf > 0.5 && !((face == 2.0 && uSd.x <= 0.0) || (face == 3.0 && uSd.y <= 0.0) || (face >= 4.0 && FNX(face) * uSd.x + FNY(face) * uSd.y <= 0.0))) { if (figdir(uSd, pp, fm)) u = 0.0; }   /* = lk_lt_figface: no figure shadow on a face the sun cannot reach */
    if (uDn > 0.5) a = uAmb3 + uSun3 * u;
    else { float k2 = uSK * u; a = vec3(uSS * 0.95 + k2, uSS * 0.98 + k2 * 0.97, uSS * 1.06 + k2 * 0.90); } }
  else if (uKey > 0.5) { float u = sun * (1.0 / 255.0);
    if (u > 0.0 && uNfb > 0.5 && infb > 0.5 && !((face == 2.0 && uSd.x <= 0.0) || (face == 3.0 && uSd.y <= 0.0) || (face >= 4.0 && FNX(face) * uSd.x + FNY(face) * uSd.y <= 0.0))) { if (figdir(uSd, pp, fm)) u *= 0.45; }
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
  if (uSwon > 0.5 && uSwSh < 0.5) { float t = term(pp, vec3(FNX(face), FNY(face), face == 1.0 ? 1.0 : 0.0), uSwP, uSwC.w); sr += t * uSwC.rgb; }
  vec3 o = floor(c * min(a + 2.2 * sr, vec3(2.4)));
  if (uNsh > 0.5) { float dz, d = moteAt(q, dz), gl = bm * 0.38; if (d > 0.0 && dz >= bz - 2.0) gl += d * 0.50; gl *= uFade; if (gl > 0.0) o += floor(gl * uShc); }
  if (uAm > 0.5) o = amix(o, q, bz, -32768.0, false);
  gl_FragColor = fin(o, fc); }
'''

SHB = r'''
uniform sampler2D lit; uniform sampler2D unl; uniform sampler2D cls; uniform sampler2D rows; uniform sampler2D roomA; uniform sampler2D roomB; uniform sampler2D rad; uniform sampler2D post; uniform sampler2D btab;
uniform float uMode; uniform vec3 uBase; uniform float uW; uniform float uK; uniform float uR; uniform float uD; uniform float uPost; uniform vec2 uPh; uniform float uOut;
uniform sampler2D wld; uniform vec4 uSwP; uniform vec4 uSwC; uniform float uSw; uniform float uSunR;
uniform vec4 uLP[96]; uniform vec4 uLC[96]; uniform vec4 uLF[96]; uniform vec4 uFG[16]; uniform vec4 uFA[16];
uniform float uNl; uniform float uAmb; uniform float uSS; uniform float uSK; uniform vec3 uAmb3; uniform vec3 uSun3; uniform float uDn; uniform float uKey; uniform float uKA; uniform float uKK; uniform vec3 uSd; uniform float uE; uniform float uSwon; uniform float uFig; uniform float uNf; uniform float uRfK; uniform float uRfD;
float B(float v) { return floor(v * 255.0 + 0.5); }
float FNX(float f) { if (f == 2.0) return 1.0; if (f < 4.0 || f > 19.0) return 0.0; if (f == 4.0) return 0.707106781; if (f == 5.0) return 0.831469612; if (f == 6.0) return 0.923879533; if (f == 7.0) return 0.98078528; if (f == 8.0) return 1.0; if (f == 9.0) return 0.98078528; if (f == 10.0) return 0.923879533; if (f == 11.0) return 0.831469612; if (f == 12.0) return 0.707106781; if (f == 13.0) return 0.555570233; if (f == 14.0) return 0.382683432; if (f == 15.0) return 0.195090322; if (f == 16.0) return 6.123234e-17; if (f == 17.0) return -0.195090322; if (f == 18.0) return -0.382683432; if (f == 19.0) return -0.555570233; return 0.0; }   /* v9 lk_lt_fnx: face codes 4..19 = slanted faces */
float FNY(float f) { if (f == 3.0) return 1.0; if (f < 4.0 || f > 19.0) return 0.0; if (f == 4.0) return -0.707106781; if (f == 5.0) return -0.555570233; if (f == 6.0) return -0.382683432; if (f == 7.0) return -0.195090322; if (f == 8.0) return 0.0; if (f == 9.0) return 0.195090322; if (f == 10.0) return 0.382683432; if (f == 11.0) return 0.555570233; if (f == 12.0) return 0.707106781; if (f == 13.0) return 0.831469612; if (f == 14.0) return 0.923879533; if (f == 15.0) return 0.98078528; if (f == 16.0) return 1.0; if (f == 17.0) return 0.98078528; if (f == 18.0) return 0.923879533; if (f == 19.0) return 0.831469612; return 0.0; }   /* v9 lk_lt_fny */
float S16(float lo, float hi) { float v = lo + 256.0 * hi; return v >= 32768.0 ? v - 65536.0 : v; }
vec3 posAt(vec2 q, out float face) {   /* world position + face of a picture pixel from the light blocks (U / V of its line) */
  vec4 ro = texture2D(rows, vec2((q.y + 0.5) / 224.0, 0.5)); float U = S16(B(ro.r), B(ro.g)) + q.x, V = S16(B(ro.b), B(ro.a));
  vec2 rt = (vec2(U, V) + 0.5) / vec2(2432.0, 1216.0); face = B(texture2D(roomA, rt).r); vec4 b = texture2D(roomB, rt); float z = S16(B(b.r), B(b.g)), D = U - 1184.0;
  vec2 bq = floor(vec2(U, V) / 32.0); if (bq.x < 0.0 || bq.y < 0.0 || bq.x > 75.0 || bq.y > 37.0 || texture2D(btab, (bq + 0.5) / vec2(76.0, 38.0)).r < 0.5) face = 0.0;   /* a block not computed yet holds another room's data */
  return vec3((2.0 * V + 2.0 * z + D) * 0.5, (2.0 * V + 2.0 * z - D) * 0.5, z); }
vec3 nrm(float f) { return vec3(FNX(f), FNY(f), f == 1.0 ? 1.0 : 0.0); }
float topT(float cx, float cy) {   /* the world heights of the GL5 block pass (top + thin columns indoors) */
  if (cx < 0.0 || cy < 0.0 || cx >= 74.0 || cy >= 74.0) return -32768.0;
  vec4 w = texture2D(wld, (vec2(cx, cy) + 0.5) / vec2(74.0, 222.0)); float t = S16(B(w.r), B(w.g));
  if (uSunR < 0.5) { float n = S16(B(w.b), B(w.a)); if (n > -32768.0) t = n; }
  return t; }
float term0(vec3 p, vec3 n, vec4 L, float kk) {   /* the light pass' term (no shadow) */
  vec3 v = L.xyz - p; float d = sqrt(v.x * v.x + v.y * v.y + v.z * v.z), rad = L.w, ndl, q;
  if (d >= rad || d < 0.001) return d < 0.001 ? kk : 0.0;
  ndl = (n.x * v.x + n.y * v.y + n.z * v.z) / d; if (ndl < 0.0) ndl = 0.0;
  q = 1.0 - d / rad; return kk * q * q * (0.25 + 0.75 * ndl); }
float figVis(vec3 o, vec3 L, float fz) {   /* GL5f v2 (2026-11-07 user rec_20261107_1740 'scharfe Trennungen'): how much of a flame reaches a figure row; marched from the figure's AXIS o (v1 started at the
     round surface point pushed towards the camera = inside a counter / wall in front of the figure: whole figure black), cells no higher than the figure's floor fz skipped (no
     self shadow at the feet), soft edge of at least 6 units (v1 hard 0 / 1 per pixel = sharp splits across a figure) */
  vec3 w = L - o; float e = length(w), res = 1.0;
  for (int st = 0; st < 140; st++) { float tt = 4.0 + 3.0 * float(st); if (tt >= e - 3.0) break;
    vec3 q = o + w * tt / e; float top = topT(floor(q.x / 16.0), floor(q.y / 16.0));
    if (top <= fz + 0.5) continue;
    res = min(res, 0.5 + (q.z - top) / max(tt * 0.25, 6.0)); if (res <= 0.0) return 0.0; }
  return clamp(res, 0.0, 1.0); }
vec3 ambient(float u) {   /* the light pass' figure base light for sun share u */
  vec3 a = vec3(uAmb * 0.93, uAmb * 0.96, uAmb * 1.06);
  if (uNl < 0.5 && uSunR < 0.5) a = vec3(1.0);
  if (uSunR > 0.5 && uDn > 0.5) a = uAmb3 + uSun3 * u;
  else if (uSunR > 0.5) { float k2 = uSK * u; a = vec3(uSS * 0.95 + k2, uSS * 0.98 + k2 * 0.97, uSS * 1.06 + k2 * 0.90); }
  else if (uKey > 0.5) { float k2 = uKK * u; a = vec3(uKA * 0.97 + k2 * 1.04, uKA * 0.99 + k2, uKA * 1.05 + k2 * 0.92); }
  return a; }
float tagAt2(float x, float y) { return B(texture2D(cls, (vec2(x, y) + 0.5) / vec2(448.0, 224.0)).a); }
bool ownAt2(float x, float y, float t) { vec4 c = texture2D(cls, (vec2(x, y) + 0.5) / vec2(448.0, 224.0)); return B(c.a) == t || B(c.b) == t; }   /* LK_LTHIDE v1 */
float figBlock(vec3 p, vec3 L, int self) {   /* GL5f step 2: share of a flame's light at p that another figure's silhouette blocks (its card turned to the light; v2: 3 x 3 taps 2 px apart = softer edge, at most 0.8; fading with the distance as lk_lt_shadowed) */
  float best = 0.0; vec3 e = L - p; float el = length(e);
  for (int i = 0; i < 16; i++) { if (float(i) >= uNf) break; if (i == self) continue;
    vec4 F = uFG[i], Fa = uFA[i]; vec2 h = L.xy - F.xy; float hl = length(h); if (hl < 1e-3) continue; vec2 nn = h / hl;
    float den = dot(nn, L.xy - p.xy), num = dot(nn, F.xy - p.xy); if (abs(den) < 1e-4) continue;
    float t = num / den; if (t < 0.02 || t > 0.98) continue;
    vec3 q = p + t * e; float tx = nn.y, ty = -nn.x; if (tx - ty < 0.0) { tx = -tx; ty = -ty; }
    float dx = 1.4142 * (tx * (q.x - F.x) + ty * (q.y - F.y)), hh = q.z - F.z;
    if (dx < -18.0 || dx > 18.0 || hh < -8.0 || hh > 58.0) continue;
    float mx = Fa.x + floor(dx + 0.5) + uE, my = Fa.y - floor(hh + 0.5), hit = 0.0;
    for (int b2 = -1; b2 <= 1; b2++) for (int a2 = -1; a2 <= 1; a2++) { float ux = mx + 2.0 * float(a2), uy = my + 2.0 * float(b2); if (ux >= 0.0 && ux < 448.0 && uy >= 0.0 && uy < 224.0 && ownAt2(ux, uy, Fa.z)) hit += 1.0; }
    if (hit > 0.0) { float w = clamp((60.0 - t * el) * (1.0 / 40.0), 0.0, 1.0); best = max(best, 0.45 * w * hit / 9.0); } }   /* at most 0.45 (user 2026-11-07: faces too dark; 0.8 made a neighbour 30 % darker = a grey dead figure: sprites are flat cards) */
  return best; }
float figSun(vec3 p, int self) {   /* GL5f step 2: share of the sun / key light another figure's silhouette blocks at p (lk_lt_figdir; v2 soft: 3 x 3 taps 2 px apart instead of one yes / no tap) */
  vec3 sd = uSd; float hl = length(sd.xy), best = 0.0; if (hl < 1e-3) return 0.0;
  float nx = sd.x / hl, ny = sd.y / hl, den = nx * sd.x + ny * sd.y, tx = ny, ty = -nx; if (tx - ty < 0.0) { tx = -tx; ty = -ty; }
  for (int i = 0; i < 16; i++) { if (float(i) >= uNf) break; if (i == self) continue;
    vec4 F = uFG[i], Fa = uFA[i];
    if (abs(F.x - p.x) > 110.0 || abs(F.y - p.y) > 110.0 || p.z > F.z + 58.0) continue;
    float t = (nx * (F.x - p.x) + ny * (F.y - p.y)) / den; if (t <= 0.5) continue;
    vec3 q = p + t * sd; float dx = 1.4142 * (tx * (q.x - F.x) + ty * (q.y - F.y)), hh = q.z - F.z;
    if (dx < -18.0 || dx > 18.0 || hh < -8.0 || hh > 58.0) continue;
    float mx = Fa.x + floor(dx + 0.5) + uE, my = Fa.y - floor(hh + 0.5), hit = 0.0;
    for (int b2 = -1; b2 <= 1; b2++) for (int a2 = -1; a2 <= 1; a2++) { float ux = mx + 2.0 * float(a2), uy = my + 2.0 * float(b2); if (ux >= 0.0 && ux < 448.0 && uy >= 0.0 && uy < 224.0 && ownAt2(ux, uy, Fa.z)) hit += 1.0; }
    best = max(best, hit / 9.0); }
  return best; }
vec3 rowSpan(float x0, float line, float tg) {   /* the figure's own CONNECTED sprite pixels (owner tag tg) in a row around x0 (gaps up to 3 px, at most 24 px each side): (left, right, found).  v1 took the farthest
     pixel of the figure within 24 px across any gap: next to another figure / a stretched arm the width jumped from row to row = diagonal hard edges (two maids in room 680) */
  float xl = x0, xr = x0, f = 0.0, g = 0.0;
  if (line < 0.0 || line > 223.0) return vec3(x0, x0, 0.0);
  if (B(texture2D(cls, (vec2(x0, line) + 0.5) / vec2(448.0, 224.0)).a) == tg) f = 1.0;
  for (int k = 1; k <= 24; k++) { float xx = x0 - float(k); if (xx < 0.0) break; if (B(texture2D(cls, (vec2(xx, line) + 0.5) / vec2(448.0, 224.0)).a) == tg) { xl = xx; f = 1.0; g = 0.0; } else { g += 1.0; if (g > 3.0) break; } }
  g = 0.0;
  for (int k = 1; k <= 24; k++) { float xx = x0 + float(k); if (xx >= uW) break; if (B(texture2D(cls, (vec2(xx, line) + 0.5) / vec2(448.0, 224.0)).a) == tg) { xr = xx; f = 1.0; g = 0.0; } else { g += 1.0; if (g > 3.0) break; } }
  return vec3(xl, xr, f); }
vec4 roundFig(vec2 fc, float cl, vec4 L4) {   /* GL5f: a figure as a round body (width of its own pixels in this row): per pixel normal + flame shadows; relit by the ratio new / old light.
     v2 (2026-11-07): the body width is averaged over the row above / below (no stripes where an arm sticks out); only the SHAPE part (normal) is amplified by LANDSTALKER_ROUNDFIG_K,
     the shadows (terrain: figVis from the figure axis, soft; other figures: figBlock / figSun, soft) multiply unamplified; the sword glow stays as the light pass has it (v1 amplified it =
     'Nigel lights the other figure'). Test aid LANDSTALKER_ROUNDFIG_DBG bits: 1 no terrain shadow, 2 no figure-on-figure shadow, 4 no shape, 8 show the figure classes, 16 show the position across the body */
  int j0 = int(cl - 16.0), j = j0; float line = fc.y, x = fc.x - uE, tg = tagAt2(fc.x, line);
  for (int i = 0; i < 16; i++) { if (float(i) >= uNf) break; if (uFA[i].z == tg) j = i; }   /* v2: the figure that OWNS the sprite pixel (the class = lk_lt_figat = the first figure whose +-16 px box holds the pixel: two maids side by side were one body) */
  vec4 F = uFG[j], Fa = uFA[j], F0 = uFG[j0], Fa0 = uFA[j0];
  vec3 s0 = rowSpan(fc.x, line, tg), s1 = rowSpan(fc.x, line - 1.0, tg), s2 = rowSpan(fc.x, line + 1.0, tg);
  float wsum = 2.0 + s1.z + s2.z, xl = (2.0 * s0.x + s1.z * s1.x + s2.z * s2.x) / wsum, xr = (2.0 * s0.y + s1.z * s1.y + s2.z * s2.y) / wsum;
  float hw = (xr - xl) * 0.5 + 0.5, u = clamp((fc.x - (xl + xr) * 0.5) / hw, -1.0, 1.0), wv = sqrt(max(1.0 - u * u, 0.0));
  vec3 tv = vec3(0.7071, -0.7071, 0.0), nc = vec3(0.7071, 0.7071, 0.0), n = normalize(tv * u + nc * wv);
  float dx = x - Fa.x, dx0 = x - Fa0.x; vec3 pc = vec3(F.x + dx * 0.5, F.y - dx * 0.5, F.z + (Fa.y - line)), p = pc + nc * (wv * hw * 0.7071), ax = vec3(F.x, F.y, max(pc.z, F.z + 2.0));
  vec3 pc0 = vec3(F0.x + dx0 * 0.5, F0.y - dx0 * 0.5, F0.z + (Fa0.y - line));   /* where the light pass lit this pixel (its card of figure j0): the ratio's denominator */
  bool tsh = mod(uRfD, 2.0) < 0.5, fsh = mod(floor(uRfD / 2.0), 2.0) < 0.5 && uNf > 1.5, shp = mod(floor(uRfD / 4.0), 2.0) < 0.5;
  if (!shp) n = nc;
  if (mod(floor(uRfD / 8.0), 2.0) > 0.5) return vec4(fract(cl * 0.37), fract(cl * 0.61), fract(cl * 0.13 + 0.5), 1.0);   /* DBG 8: which figure a pixel belongs to */
  if (mod(floor(uRfD / 16.0), 2.0) > 0.5) return vec4(0.5 + 0.5 * u, 0.5 - 0.5 * u, wv, 1.0);   /* DBG 16: position across the body (red = right side) */
  vec3 so = vec3(0.0), sc = vec3(0.0), sl = vec3(0.0), ss = vec3(0.0);
  for (int k = 0; k < 96; k++) { if (float(k) >= uNl) break; vec4 Lf = uLF[k]; if (Lf.y > 0.5 && Lf.x <= 0.004) continue;
    vec3 lc = Lf.x * uLC[k].rgb; so += term0(pc0, nc, uLP[k], uLC[k].w) * lc; sc += term0(pc, nc, uLP[k], uLC[k].w) * lc;
    float tn = term0(pc, n, uLP[k], uLC[k].w); if (tn <= 0.0) continue; sl += tn * lc;   /* distance from the CARD (v2 first try used the round surface point p in front of it: a torch behind / beside the figure was farther away = whole figure 15 .. 30 % darker, the user: 'Gesichter teilweise immer noch recht dunkel'); the round normal only turns the angle */
    if (tsh) tn *= figVis(ax, uLP[k].xyz, F.z); if (tn > 0.0 && fsh) tn *= 1.0 - figBlock(pc, uLP[k].xyz, j); ss += tn * lc; }
  if (uSwon > 0.5) { vec3 g0 = term0(pc0, nc, uSwP, uSwC.w) * 0.5 * uSwC.rgb, g = term0(pc, nc, uSwP, uSwC.w) * 0.5 * uSwC.rgb; so += g0; sc += g; sl += g; ss += g; }
  float hc = 0.25 + 0.75 * max(dot(nc, uSd), 0.0), hn = 0.25 + 0.75 * max(dot(n, uSd), 0.0);   /* the sun / key light on the round body */
  float us = F.w * clamp(hn / hc, 0.4, 1.8), uss = us; if (us > 0.0 && fsh && (uSunR > 0.5 || uKey > 0.5)) uss = us * (1.0 - figSun(pc, j) * (uKey > 0.5 ? 0.35 : 0.6));   /* at most 0.6 of the sun (was all of it), key light 0.35 (was 0.55) */   /* step 2: another figure's shadow */
  vec3 fo = min(ambient(F0.w) + 2.2 * so, vec3(2.4)), fc0 = min(ambient(F.w) + 2.2 * sc, vec3(2.4)), fl = min(ambient(us) + 2.2 * sl, vec3(2.4)), fs = min(ambient(uss) + 2.2 * ss, vec3(2.4));
     /* fo = the card the light pass used (figure j0), fc0 = the card of the owner j: fc0 / fo moves the pixel's light to its owner UNAMPLIFIED (v2 first try amplified it: the maid
        became brighter whenever Nigel stood in front of her, user rec_20261107_1822) */
  vec3 a = uRfK * (fl / max(fc0, vec3(0.01)) - vec3(1.0));   /* the user wanted the shape stronger (2026-11-06): its deviation x LANDSTALKER_ROUNDFIG_K */
  vec3 rs = mix(vec3(1.0) + 0.9 * (vec3(1.0) - exp(-max(a, vec3(0.0)) / 0.9)), vec3(1.0) - 0.3 * (vec3(1.0) - exp(min(a, vec3(0.0)) / 0.3)), step(a, vec3(0.0)));
     /* v2 (user 2026-11-07 'uebergang sanfter machen'): soft knee instead of the hard clamp 0.4 .. 1.9: small deviations stay as strong (slope 1 at 0), large ones approach 0.7 / 1.9 (0.55, then 0.6; user 2026-11-07 'Gesichter noch etwas heller', 'teilweise immer noch recht dunkel')
        gently (v1: the side away from a torch sat flat at 0.4 = grey maids in room 680) */
  vec3 r = clamp(rs * (fc0 / max(fo, vec3(0.01))) * min(fs / max(fl, vec3(0.01)), vec3(1.0)), vec3(0.3), vec3(1.9));
  return vec4(min(L4.rgb * 255.0 * r, vec3(255.0)) / 255.0, 1.0); }
uniform sampler2D fine; uniform float uFn;
vec4 FNb(float sx, float sy, float hf) { return texture2D(fine, (vec2(sx, sy + 296.0 * hf) + 0.5) / vec2(296.0, 1480.0)); }
float swocc(vec3 q, float tt, inout float res) {   /* LK_SWSHFINE v1: 1 = q is inside the scenery; else the clearance shrinks res (soft edge, LK_LT_IPEN rule) */
  float top = topT(floor(q.x / 16.0), floor(q.y / 16.0)), sx = floor(q.x / 4.0), sy = floor(q.y / 4.0);
  if (uFn > 0.5 && sx >= 0.0 && sy >= 0.0 && sx < 296.0 && sy < 296.0) {   /* (user 2026-11-11: 'nachts neben einem grossen Baum mit dem Schwert schlagen: der Schatten sieht aus wie eine Box') */
    vec4 f0 = FNb(sx, sy, 0.0), f4 = FNb(sx, sy, 4.0), f2 = FNb(sx, sy, 2.0); float fo = S16(B(f0.b), B(f0.a)), fh = S16(B(f0.r), B(f0.g)), k = B(f4.r);
    float sb = S16(B(f2.r), B(f2.g)), st = S16(B(f2.b), B(f2.a));
    if (st > sb && q.z > sb && q.z < st) return 1.0;   /* v9 slab (floating part) */
    if (st > sb) { float c = q.z <= sb ? sb - q.z : q.z - st, r = 4.0 * c / tt; if (r < res) res = r; }
    if (k > 0.5 && k < 1.5) {   /* a hand-made model's sub column (tree, statue, furniture): ground g, air up to g + gap, the model up to its top */
      float g = S16(B(f4.b), B(f4.a)), gap = B(f4.g), mt = fo != 0.0 && fh > g ? fh : g;
      if (q.z < g - 0.5) return 1.0;
      if (gap > 4.0 && q.z < g + gap) { float r = 4.0 * min(q.z - g, g + gap - q.z) / tt; if (r < res) res = r; return 0.0; }
      top = mt; }
    else if (fo == 2047.0) top = fh; }   /* the data height indoors (ops box / mesh) */
  if (q.z < top - 0.5) return 1.0;
  if (top > -32768.0) { float r = 4.0 * (q.z - top) / tt; if (r < res) res = r; }
  return 0.0; }
float swlight(vec3 p, vec3 n) {   /* GL5e: the sword glow (lk_lt_term without shadow, as the light pass) times its soft shadow (march to the sword, LK_LT_IPEN clearance rule; LK_SWSHFINE v1: through the fine field) */
  vec3 v = uSwP.xyz - p; float d = length(v), rad = uSwP.w;
  if (d >= rad || d < 0.001) return d < 0.001 ? uSwC.w : 0.0;
  float ndl = max(dot(n, v) / d, 0.0), q = 1.0 - d / rad, t = uSwC.w * q * q * (0.25 + 0.75 * ndl);
  if (t <= 0.0) return 0.0;
  vec3 s = p + n * 3.0, w = uSwP.xyz - s; float e = length(w), res = 1.0;
  for (int st = 0; st < 200; st++) { float tt = 2.0 + 2.0 * float(st); if (tt >= e - 3.0) break;
    if (swocc(s + w * tt / e, tt, res) > 0.5) return 0.0; }
  return t * max(res, 0.0); }
void main() {
  vec2 fc = floor(gl_FragCoord.xy);
  if (uMode < 0.5) {   /* pass A, 113 x 57: the light each 4 x 4 cell gets on top of the room's base light (scenery pixels only); cells aligned to the room picture (phase uPh), not to the screen */
    vec3 s = vec3(0.0); float n = 0.0;
    for (int j = 0; j < 4; j++) for (int i = 0; i < 4; i++) { vec2 q = fc * 4.0 - uPh + vec2(float(i), float(j)); if (q.x < 0.0 || q.y < 0.0 || q.y > 223.0 || q.x >= uW) continue;
      vec2 tc = (q + 0.5) / vec2(448.0, 224.0); if (B(texture2D(cls, tc).r) != 1.0) continue;
      vec3 L = texture2D(lit, tc).rgb * 255.0, C = texture2D(unl, tc).rgb * 255.0; s += max(L - C * uBase, vec3(0.0)); n += 1.0; }
    gl_FragColor = vec4(n > 0.0 ? s / n / 255.0 : vec3(0.0), n / 16.0); return; }   /* (alpha: share of scenery pixels) */
  vec2 tc = (fc + 0.5) / vec2(448.0, 224.0); vec4 L4 = texture2D(lit, tc); vec3 L = L4.rgb * 255.0;
  { float cl0 = B(texture2D(cls, tc).r);
    if (uFig > 0.5 && cl0 > 15.5 && fc.x < uW) { if (uPost > 0.5) { vec4 a = texture2D(post, (fc + 0.5) / vec2(448.0, 448.0)), b = texture2D(post, (vec2(fc.x, fc.y + 224.0) + 0.5) / vec2(448.0, 448.0)); if (a.rgb != vec3(0.0) || b.rgb != vec3(1.0)) { gl_FragColor = L4; return; } }
      gl_FragColor = roundFig(fc, cl0, L4); return; } }
  if (fc.x >= uW || B(texture2D(cls, tc).r) != 1.0) { gl_FragColor = L4; return; }
  if (uPost > 0.5) { vec4 a = texture2D(post, (fc + 0.5) / vec2(448.0, 448.0)), b = texture2D(post, (vec2(fc.x, fc.y + 224.0) + 0.5) / vec2(448.0, 448.0)); if (a.rgb != vec3(0.0) || b.rgb != vec3(1.0)) { gl_FragColor = L4; return; } }   /* emissive / HUD */
  float f; vec3 p = posAt(fc, f); if (f < 0.5) { gl_FragColor = L4; return; }
  vec3 n = nrm(f), g = vec3(0.0);
  if (uK > 0.0) for (int k = 0; k < 32; k++) { float a = float(k) * 2.39996, r = uR * sqrt((float(k) + 0.5) / 32.0); vec2 sp = floor(fc + vec2(cos(a), sin(a)) * r);
    if (sp.x < 0.0 || sp.y < 0.0 || sp.x >= uW || sp.y > 223.0) continue;
    vec4 R = texture2D(rad, ((sp + uPh) / 4.0) / vec2(116.0, 60.0)); if (R.a < 0.05 || R.rgb == vec3(0.0)) continue;   /* linear filtered cells: no cell steps (v1 made blocky spots that scrolled) */
    float fs; vec3 ps = posAt(sp, fs); if (fs < 0.5 || (uOut > 0.5 && fs != 1.0)) continue;   /* outdoors only lit ground sends (tree crowns / proxies are rough shapes: blotches under trees, user 2026-11-06) */
    vec3 d = ps - p; float dl = length(d); if (dl < 6.0) continue; d /= dl;   /* not its own surroundings (a single bright source, e.g. a firefly glow, made a hot spot) */
    float w = max(dot(n, d), 0.0) * max(-dot(nrm(fs), d), 0.0) / (1.0 + (dl / uD) * (dl / uD));   /* the two surfaces must face each other, soft distance falloff */
    g += w * min(R.rgb, vec3(0.4)) * 255.0; }   /* one source adds at most ~100 levels of light */
  vec3 C = texture2D(unl, tc).rgb * 255.0, o = L + uK * (C / 255.0) * g * (1.0 / 8.0);
  if (uSw > 0.5) { float t = swlight(p, n); if (t > 0.0) o = min(o + floor(C * (2.2 * t) * uSwC.rgb), max(L, floor(C * 2.4))); }   /* GL5e: added after the light (the light pass leaves it out on scenery) */
  gl_FragColor = vec4(min(o, vec3(255.0)) / 255.0, 1.0); }
'''

SH5 = r'''
uniform sampler2D roomA; uniform sampler2D roomB; uniform sampler2D btab; uniform sampler2D bli; uniform sampler2D wld;
uniform vec4 uLP[96]; uniform vec4 uLC[96]; uniform vec4 uLF[96]; uniform float uSoftR; uniform vec2 uBlk; uniform float uSunR; uniform float uAor; uniform float uZref; uniform float uAok; uniform float uAotop; uniform vec2 uDv[16];
uniform float uIfine; uniform float uNslab; uniform float uPineT; uniform float uBushE;   /* v9 */
uniform sampler2D wld2; uniform sampler2D fine; uniform sampler2D prx; uniform sampler2D bex; uniform float uSside; uniform float uZtop; uniform vec3 uSd; uniform float uKey; uniform float uKbw; uniform float uKpen; uniform float uNsh; uniform vec4 uSh[9]; uniform sampler2D fine2; uniform float uZmax; uniform float uRayF;
uniform sampler2D mdl; uniform vec4 uMo; uniform float uMdl; uniform vec4 uSmo; uniform vec2 uSmSl; uniform float uHand; uniform float uAoflt; uniform vec4 uSm; uniform vec3 uE1; uniform vec3 uE2; uniform vec4 uSm2; uniform vec3 uE12; uniform vec3 uE22;   /* + the next sun step's map (third part) */   /* + stage 2: the key light SHADOW MAP in the right half (uSm = s0, t0, texels per unit, on) */   /* LK_GLMODEL v1: model buffer (z * 8 + 32768 in r / g, octahedral normal in b / a), its room picture origin + size, on */
float gBest = 0.0, gBH = 0.0, gBX = 0.0, gBY = 0.0; vec3 gN = vec3(0.0, 0.0, 1.0); vec2 gMB = vec2(0.0, 0.0); float gGen = 0.0, gMH = 0.0, gMS = 0.0, gKM = 0.0, gSoft = 0.0;   /* gKM: the key light march of keyShare (the model's own sub columns come from the shadow map) */   /* gMH: the view ray returned the model; gMS: this pixel is a model SIDE face (AO sees the ground below the model) */   /* LK_GLMODEL v1: the real normal of a model pixel (face code 20) / its raw bytes from the model buffer */
vec3 octdec(vec2 b) { vec2 e = b / 255.0 * 2.0 - 1.0; vec3 n = vec3(e.x, e.y, 1.0 - abs(e.x) - abs(e.y)); if (n.z < 0.0) { vec2 w = (1.0 - abs(n.yx)) * vec2(n.x >= 0.0 ? 1.0 : -1.0, n.y >= 0.0 ? 1.0 : -1.0); n.x = w.x; n.y = w.y; } return normalize(n); }
float fclassic(vec3 n) { if (n.z > 0.94) return 1.0; float a = degrees(atan(n.y, n.x)), k = floor((a + 45.0) / 11.25 + 0.5); return clamp(4.0 + k, 4.0, 19.0); }   /* the nearest old face code (room A for the light pass / CPU readers) */
uniform sampler2D geo; uniform float uMode; uniform vec3 uSdN; uniform float uSunN; uniform float uKA; uniform float uKK; uniform vec3 uShc; uniform float uKm;
float B(float v) { return floor(v * 255.0 + 0.5); }
float FNX(float f) { if (f > 19.5) return gN.x; if (f == 2.0) return 1.0; if (f < 4.0 || f > 19.0) return 0.0; if (f == 4.0) return 0.707106781; if (f == 5.0) return 0.831469612; if (f == 6.0) return 0.923879533; if (f == 7.0) return 0.98078528; if (f == 8.0) return 1.0; if (f == 9.0) return 0.98078528; if (f == 10.0) return 0.923879533; if (f == 11.0) return 0.831469612; if (f == 12.0) return 0.707106781; if (f == 13.0) return 0.555570233; if (f == 14.0) return 0.382683432; if (f == 15.0) return 0.195090322; if (f == 16.0) return 6.123234e-17; if (f == 17.0) return -0.195090322; if (f == 18.0) return -0.382683432; if (f == 19.0) return -0.555570233; return 0.0; }   /* v9 lk_lt_fnx: face codes 4..19 = slanted faces */
float FNY(float f) { if (f > 19.5) return gN.y; if (f == 3.0) return 1.0; if (f < 4.0 || f > 19.0) return 0.0; if (f == 4.0) return -0.707106781; if (f == 5.0) return -0.555570233; if (f == 6.0) return -0.382683432; if (f == 7.0) return -0.195090322; if (f == 8.0) return 0.0; if (f == 9.0) return 0.195090322; if (f == 10.0) return 0.382683432; if (f == 11.0) return 0.555570233; if (f == 12.0) return 0.707106781; if (f == 13.0) return 0.831469612; if (f == 14.0) return 0.923879533; if (f == 15.0) return 0.98078528; if (f == 16.0) return 1.0; if (f == 17.0) return 0.98078528; if (f == 18.0) return 0.923879533; if (f == 19.0) return 0.831469612; return 0.0; }   /* v9 lk_lt_fny */
float FNZ(float f) { return f == 1.0 ? 1.0 : f > 19.5 ? gN.z : 0.0; }
float S16(float lo, float hi) { float v = lo + 256.0 * hi; return v >= 32768.0 ? v - 65536.0 : v; }
vec4 W(float cx, float cy, float hf) { return texture2D(wld, (vec2(cx, cy + 74.0 * hf) + 0.5) / vec2(74.0, 222.0)); }
bool inr(float cx, float cy) { return cx >= 0.0 && cy >= 0.0 && cx < 74.0 && cy < 74.0; }
float pinr(float f) { if (f < 0.0 || f >= 1.0) return 0.0; if (uPineT < 0.5) return 1.0 - f; float k = floor(f * 6.0), t = f * 6.0 - k; return (1.0 - k / 6.0) * (1.0 - 0.55 * t); }   /* v9 lk_lt_pinr */
float OFF2(float nx, float ny, float d) { return (nx != 0.0 && ny != 0.0) ? 5.0 : d; }   /* v9 LK_LT_OFF */
vec4 FN(float sx, float sy, float hf);   /* below */
float smvis2(vec3 p, vec3 n, vec3 sd, float hs, float kp);   /* below */
bool mownd(float sx, float sy) { if (uMdl < 0.5 || sx < 0.0 || sy < 0.0 || sx >= 296.0 || sy >= 296.0) return false; return B(FN(sx, sy, 4.0).r) > 0.5; }   /* LK_GLMODEL v1: model owned sub column (any kind) */
bool mownh(float sx, float sy) { if (uHand < 0.5 || uMdl < 0.5 || sx < 0.0 || sy < 0.0 || sx >= 296.0 || sy >= 296.0) return false; float r = B(FN(sx, sy, 4.0).r); return r > 0.5 && r < 1.5; }   /* LK_GLROOM v1: owned by a HAND-MADE model (kind 1) */
bool cellmdl(float cx, float cy);   /* below (LK_GLROOM v1) */
bool mowng(float sx, float sy) { if (uMdl < 0.5 || sx < 0.0 || sy < 0.0 || sx >= 296.0 || sy >= 296.0) return false; return B(FN(sx, sy, 4.0).r) > 1.5; }   /* LK_GLROOM v1: a GENERATED room box column (kind 2, or 3 = a thin pillar's cell: the field answers) */   /* LK_GLMODEL v1: model owned sub column */
vec2 SLB(float sx, float sy) { if (sx < 0.0 || sy < 0.0 || sx >= 296.0 || sy >= 296.0) return vec2(0.0, -32768.0); vec4 f = FN(sx, sy, 2.0); return vec2(S16(B(f.r), B(f.g)), S16(B(f.b), B(f.a))); }   /* v9: slab bottom / top */
float ifh(float sx, float sy, float thin) {   /* v9 lk_lt_ifh: the data height indoors or the cell (+ thin column rule) */
  if (sx < 0.0 || sy < 0.0 || sx >= 296.0 || sy >= 296.0) return -32768.0;
  vec4 f = FN(sx, sy, 0.0); if (S16(B(f.b), B(f.a)) == 2047.0) return S16(B(f.r), B(f.g));
  vec4 w = W(floor(sx / 4.0), floor(sy / 4.0), 0.0); float t = S16(B(w.r), B(w.g));
  if (thin > 0.5) { float n = S16(B(w.b), B(w.a)); if (n > -32768.0) t = n; }
  return t; }
float slabcl(float sx, float sy, float z) { if (gKM > 0.5 && mownh(sx, sy)) return 9999.0; vec2 q = SLB(sx, sy); if (q.y <= q.x) return 9999.0; return z <= q.x ? q.x - z : z >= q.y ? z - q.y : 0.0; }   /* v9 lk_lt_slabcl */
float halocl(float x, float y, float z) {   /* v9 lk_lt_halocl: soft slab sides */
  float sx = floor(x / 4.0), sy = floor(y / 4.0); if (sx < 0.0 || sy < 0.0 || sx >= 296.0 || sy >= 296.0) return 9999.0;
  vec4 f = FN(sx, sy, 3.0); float k = B(f.b); if (k < 0.5) return 9999.0;
  float b = S16(B(f.r), B(f.g)), t = b + 2.0 * B(f.a); if (z <= b || z >= t) return 9999.0;
  float x0 = 4.0 * (sx + mod(k - 1.0, 5.0) - 2.0), y0 = 4.0 * (sy + floor((k - 1.0) / 5.0) - 2.0);
  if (gKM > 0.5 && mownh(x0 / 4.0, y0 / 4.0)) return 9999.0;   /* LK_GLMODEL v1: a model's slab: the shadow map has it */
  float ex = x < x0 ? x0 - x : x > x0 + 4.0 ? x - x0 - 4.0 : 0.0, ey = y < y0 ? y0 - y : y > y0 + 4.0 ? y - y0 - 4.0 : 0.0;
  return sqrt(ex * ex + ey * ey); }
bool slabin(float sx, float sy, float z) { vec2 q = SLB(sx, sy); return q.y > q.x && z > q.x && z < q.y; }   /* v9 lk_lt_slabin */
float topT(float cx, float cy) {   /* lk_lt_cell + the thin column rule indoors */
  if (!inr(cx, cy)) return -32768.0;
  vec4 w = W(cx, cy, 0.0); float t = S16(B(w.r), B(w.g));
  if (uSunR < 0.5) { float n = S16(B(w.b), B(w.a)); if (n > -32768.0) t = n; }
  return t; }
float termS(vec3 p, vec3 n, vec4 L, float kk, vec2 wf) {   /* lk_lt_term with its shadow (2 area points + soft edges indoors, one hard march outdoors); LK_GLWIDE v2: wf = (half width, along 1 x / 2 y) of a wide fire */
  vec3 v = L.xyz - p; float d = sqrt(v.x * v.x + v.y * v.y + v.z * v.z), rad = L.w;
  if (d >= rad || d < 0.001) return d < 0.001 ? kk : 0.0;
  float own = wf.x < 0.5 && wf.y < -0.5 ? -wf.y : 0.0;   /* LK_GLCARRIER v1 (brazier stands, user 2026-11-09 'next forms'): a flame on its own stand: march samples in the stand's column
     (closer than own to the flame's axis, below the flame) do not shadow it (the bowl under the fire darkened the whole room; the painting has no such shadow) */
  float ndl = (n.x * v.x + n.y * v.y + n.z * v.z) / d; if (gSoft > 0.5) ndl = 0.5 + 0.5 * ndl; if (ndl < 0.0) ndl = 0.0;   /* LK_GLSOFTR v1: round model surface = wrapped (half the direction contrast) */
  float att = kk * (1.0 - d / rad) * (1.0 - d / rad);
  vec3 s = vec3(p.x + n.x * OFF2(n.x, n.y, 3.0), p.y + n.y * OFF2(n.x, n.y, 3.0), p.z + n.z * 3.0);
  if (uSunR < 0.5) { float sum = 0.0;
    float ns = wf.x > 0.5 ? 6.0 : 2.0;   /* LK_GLWIDE v2 (user 2026-11-09: the hearth shone through a 0.1 unit gap between two vases = a bright streak; a real fire is ~30 wide):
       a wide fire lights from 6 points spread over its drawn width along its wall -> half shadows behind objects it partly sees; small flames keep the 2 points */
    for (int o = 0; o < 6; o++) { if (float(o) >= ns) break;
      float wt = mod(wf.y, 4.0), wv = floor(wf.y / 4.0);   /* LK_GLWIDE v2 (user 2026-11-09 'ja versuch erst 2'): the fire is also TALL: the 6 points zigzag over its width and height (stratified: 2 rows at +-half of its half height) */
      vec3 off = wf.x > 0.5 ? (wt < 1.5 ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 1.0, 0.0)) * wf.x * ((float(o) + 0.5) / 3.0 - 1.0) + vec3(0.0, 0.0, wv * (mod(float(o), 2.0) < 0.5 ? -0.5 : 0.5)) : (o == 0 ? vec3(3.5, -3.5, 1.0) : vec3(-3.5, 3.5, -1.0)); vec3 w = vec3(L.x + off.x - s.x, L.y + off.y - s.y, L.z + off.z - s.z);
      float e = sqrt(w.x * w.x + w.y * w.y + w.z * w.z), res = 1.0;
      for (int st = 0; st < 400; st++) { float t = 2.0 + 2.0 * float(st); if (t >= e - 3.0) break;
        vec3 q = vec3(s.x + w.x * t / e, s.y + w.y * t / e, s.z + w.z * t / e); if (own > 0.0 && q.z < L.z && length(q.xy - L.xy) < own) continue;
        float fx = floor(q.x / 4.0), fy = floor(q.y / 4.0), top = uIfine > 0.5 ? ifh(fx, fy, 1.0) : topT(floor(q.x / 16.0), floor(q.y / 16.0));
        if (uNslab > 0.5 && slabin(fx, fy, q.z)) { res = 0.0; break; }   /* v9 */
        if (q.z < top - 0.5) { res = 0.0; break; }
        if (uIfine > 0.5) { float c2 = slabcl(fx, fy, q.z); if (c2 < 9999.0) { float r2 = 4.0 * c2 / t; if (r2 < res) res = r2; } c2 = halocl(q.x, q.y, q.z); if (c2 < 9999.0) { float r2 = 4.0 * c2 / t; if (r2 < res) res = r2; } }
        if (top > -32768.0) { float r = 4.0 * (q.z - top) / t; if (r < res) res = r; } }
      sum += (res < 0.0 ? 0.0 : res) * (wf.x > 0.5 ? 0.25 + 0.75 * max(gSoft > 0.5 ? 0.5 + 0.5 * (n.x * w.x + n.y * w.y + n.z * w.z) / e : (n.x * w.x + n.y * w.y + n.z * w.z) / e, 0.0) : 1.0); }   /* LK_GLWIDE v2: each point of a wide fire with its own angle */
    return att * (wf.x > 0.5 ? 1.0 : 0.25 + 0.75 * ndl) * sum / ns; }
  vec3 w = vec3(L.x - s.x, L.y - s.y, L.z - s.z); float e = sqrt(w.x * w.x + w.y * w.y + w.z * w.z);
  for (int st = 0; st < 400; st++) { float t = 2.0 + 2.0 * float(st); if (t >= e - 3.0) break;
    vec3 q = vec3(s.x + w.x * t / e, s.y + w.y * t / e, s.z + w.z * t / e); if (own > 0.0 && q.z < L.z && length(q.xy - L.xy) < own) continue; if (uNslab > 0.5 && slabin(floor(q.x / 4.0), floor(q.y / 4.0), q.z)) return 0.0; if (q.z < topT(floor(q.x / 16.0), floor(q.y / 16.0)) - 0.5) return 0.0; }
  return att * (0.25 + 0.75 * ndl); }
float mslabcl(float x, float y, float z) {   /* LK_GLMODEL v1: clearance of a point to the FLOATING part of a model sub column (bottom above ground + 4 .. top), 9999 = none */
  float sx = floor(x / 4.0), sy = floor(y / 4.0); if (uHand < 0.5 || uMdl < 0.5 || (gKM > 0.5 && uSm.w > 0.5) || sx < 0.0 || sy < 0.0 || sx >= 296.0 || sy >= 296.0) return 9999.0;
  vec4 f4 = FN(sx, sy, 4.0); if (B(f4.r) < 0.5 || B(f4.g) <= 4.0) return 9999.0;
  float b = S16(B(f4.b), B(f4.a)) + B(f4.g); vec4 f0 = FN(sx, sy, 0.0); float t = S16(B(f0.r), B(f0.g)); if (t <= b) return 9999.0;
  return z <= b ? b - z : z >= t ? z - t : 0.0; }
float aohm(float sx, float sy, float slab) {   /* LK_GLMODEL v1: one sub column's AO height near a model (owned: floating = ground, else the model top) */
  float t = ifh(sx, sy, 0.0); if (slab > 0.5) { vec2 q = SLB(sx, sy); if (q.y > q.x && q.y > t) t = q.y; }
  if (sx >= 0.0 && sy >= 0.0 && sx < 296.0 && sy < 296.0) { vec4 f4 = FN(sx, sy, 4.0); if (B(f4.r) > 0.5 && (B(f4.g) > 4.0 || (gKM > 0.5 && uSm.w > 0.5))) t = S16(B(f4.b), B(f4.a)); }
  return t; }
float aoh2(float x, float y, float dx, float dy, float slab) {   /* lk_lt_aoh2 */
  float cx = floor(x / 16.0), cy = floor(y / 16.0);
  if (!inr(cx, cy)) return (dx < 0.0 || dy < 0.0) ? 32767.0 : -32768.0;
  vec4 w = W(cx, cy, 0.0); float t = S16(B(w.r), B(w.g));
  if (uIfine < 0.5 && uHand > 0.5 && S16(B(w.b), B(w.a)) == -32767.0) { float sx = floor(x / 4.0), sy = floor(y / 4.0); if (mownh(sx, sy)) { vec4 f4 = FN(sx, sy, 4.0), f0 = FN(sx, sy, 0.0); float g = S16(B(f4.b), B(f4.a)), fo = S16(B(f0.b), B(f0.a)), fh = S16(B(f0.r), B(f0.g)); t = fo != 0.0 && fh > g ? fh : g; } }   /* LK_GLROOM v1 outdoors: a model's area = the model's stamped top or the ground (no collision box) */
  if (uIfine > 0.5) { float sx = floor(x / 4.0), sy = floor(y / 4.0); t = ifh(sx, sy, 0.0); if (slab > 0.5) { vec2 q = SLB(sx, sy); if (q.y > q.x && q.y > t) t = q.y; }   /* v9 */
    if (uMdl > 0.5 && sx >= 0.0 && sy >= 0.0 && sx < 296.0 && sy < 296.0) { float gx = x / 4.0 - 0.5, gy = y / 4.0 - 0.5, ax = floor(gx), ay = floor(gy), fx = gx - ax, fy = gy - ay;
      if (gKM > 0.5 && uSm.w > 1.5 && slab < 0.5 && mowng(sx, sy)) return -32768.0;   /* test aid LANDSTALKER_LT_ROOMSM=1: the boxes are in the shadow map */
      if (mownh(ax, ay) || mownh(ax + 1.0, ay) || mownh(ax, ay + 1.0) || mownh(ax + 1.0, ay + 1.0)) {   /* near a model: the 4 sub column heights interpolated (no 4 unit stairs in the AO, user 2026-11-08 'harte Kanten') */
        float h00 = aohm(ax, ay, slab), h10 = aohm(ax + 1.0, ay, slab), h01 = aohm(ax, ay + 1.0, slab), h11 = aohm(ax + 1.0, ay + 1.0, slab);
        if (h00 > -32768.0 && h10 > -32768.0 && h01 > -32768.0 && h11 > -32768.0 && (gKM < 0.5 || slab > 0.5)) t = mix(mix(h00, h10, fx), mix(h01, h11, fx), fy);
        else t = aohm(sx, sy, slab); } } }   /* LK_GLMODEL v1: a FLOATING model sub column (bottom above ground + 4: a hull bulge, the bow overhang) is air down to the ground for AO and the key march (keyvis tests the floating part itself, mslabcl) */
  if (t != -32768.0) return t;
  float vw = B(W(cx, cy, 1.0).r);
  if ((dx < 0.0 && mod(vw, 2.0) > 0.5) || (dy < 0.0 && mod(floor(vw / 2.0), 2.0) > 0.5)) return 32767.0;
  return -32768.0; }
float aoh(float x, float y, float dx, float dy) { return aoh2(x, y, dx, dy, 1.0); }
float aoflt(float x, float y, out float b) {   /* LK_GLAOFLT v2 (user 2026-11-09, table 670: 'drunter sollte es nicht so hell sein, weil der Tisch den Schatten wirft'): the FLOATING part of a
     hand model sub column (bottom above ground + 4, as mslabcl) -> its top, its bottom in b; -32768 = none.  aoh treats such parts as AIR (no columns down to the
     ground under the ship's overhangs), so without this the floor under a table top saw open sky */
  b = 0.0; float sx = floor(x / 4.0), sy = floor(y / 4.0); if (uAoflt < 0.5 || uHand < 0.5 || uMdl < 0.5 || sx < 0.0 || sy < 0.0 || sx >= 296.0 || sy >= 296.0) return -32768.0;
  vec4 f4 = FN(sx, sy, 4.0); if (B(f4.r) < 0.5 || B(f4.g) <= 4.0) return -32768.0;
  b = S16(B(f4.b), B(f4.a)) + B(f4.g); vec4 f0 = FN(sx, sy, 0.0); float t = S16(B(f0.r), B(f0.g)); return t > b ? t : -32768.0; }
float aoval(float px, float py, float z, float f) {   /* lk_lt_aoval */
  float nx = FNX(f), ny = FNY(f), x0 = px + nx * OFF2(nx, ny, 2.0), y0 = py + ny * OFF2(nx, ny, 2.0), sum = 0.0, n = 0.0, cov = 0.0;
  if (f != 1.0) { float fl = aoh(x0, y0, 0.0, 0.0); if (fl > z) z = fl; }
  float fc = 0.0, fcb = 0.0;   /* LK_GLAOSOFT v1 (user 2026-11-12, table 67: 'sieht nach harten Kanten aus'): the share of the point UNDER a floating part, bilinear over the 4 nearest
                                  sub columns (was: its own sub column only = 4 unit stairs along the table top's outline) */
  if (uAoflt > 0.5 && uHand > 0.5 && uMdl > 0.5) { float gx = x0 / 4.0 - 0.5, gy = y0 / 4.0 - 0.5, ax = floor(gx), ay = floor(gy), ux = gx - ax, uy = gy - ay;
    for (int j = 0; j < 4; j++) { float ix = float(j - 2 * (j / 2)), iy = float(j / 2), bq, tq = aoflt((ax + ix) * 4.0 + 2.0, (ay + iy) * 4.0 + 2.0, bq);
      if (tq > -32768.0 && bq > z) { fc += (ix > 0.5 ? ux : 1.0 - ux) * (iy > 0.5 ? uy : 1.0 - uy); fcb = max(fcb, bq); } } }
  for (int k = 0; k < 16; k++) { vec2 dv = uDv[k]; float dix = dv.x > 0.01 ? 1.0 : dv.x < -0.01 ? -1.0 : 0.0, diy = dv.y > 0.01 ? 1.0 : dv.y < -0.01 ? -1.0 : 0.0, best = 0.0;
    if (f != 1.0 && dv.x * nx + dv.y * ny < -0.1) continue;
    n += 1.0;
    if (uAoflt > 0.5 && uHand > 0.5 && uMdl > 0.5) {   /* LK_GLAOFLT v2: a floating part only hides the sky ABOVE its bottom: under it (cover) everything above the edge seen from here, beside it the band bottom .. top */
      float cb0, ct0 = aoflt(x0, y0, cb0), U = 0.0, Bd = 0.0; bool own = ct0 > -32768.0 && cb0 > z;
      float wU = f == 1.0 ? fc : (own ? 1.0 : 0.0);   /* LK_GLAOSOFT v1 (user 2026-11-12, table 67 'harte Kanten'): a FLOOR point blends 'under the part' and 'beside it' by its share under the part (bilinear over 4 sub columns; was 0 / 1 = 4 unit stairs along the outline); walls keep 0 / 1 */
      for (int pass = 0; pass < 2; pass++) {
        if (pass == 0 ? wU <= 0.0 : wU >= 1.0) continue;
        bool ins = pass == 0; float lb = own ? cb0 : fcb, amt = 0.0, smin = 1.0, smax = 0.0, dn = 0.0;
        for (int st = 1; st < 20; st++) { float d = 2.0 * float(st), bb, tt = aoflt(x0 + dv.x * d, y0 + dv.y * d, bb); bool here = tt > -32768.0 && bb > z;
          if (ins) { if (here) { lb = bb; continue; } float e = (lb - z) / d, se = e / sqrt(1.0 + e * e); amt = 1.0 - (uAoflt > 1.5 && f == 1.0 ? se * se : se); ins = false; break; }   /* LK_GLAOFLT v2: under the part the sky ABOVE the edge (elevation asin se .. 90) is hidden; its share of the light from a uniform sky on a floor is 1 - se^2 (Lambert: weight 2 sin cos per elevation), v1 took 1 - se (the table 670 floor only 25 percent darker, user 2026-11-09: 'direkt unter der Platte noch ein hellerer gruener Streifen') */
          if (here) { float e1 = (bb - z) / d, e2 = (tt - z) / d; smin = min(smin, e1 / sqrt(1.0 + e1 * e1)); smax = max(smax, e2 / sqrt(1.0 + e2 * e2)); if (dn == 0.0) dn = d; } }
        if (ins) amt = 1.0;
        if (pass == 0) U = amt; else Bd = dn > 0.0 ? (smax - smin) * (1.0 - dn / 40.0) : 0.0; }   /* beside it: the whole part as ONE band (nearest top .. farthest bottom), not step by step (a 41 step at the table edge) */
      if (f == 1.0) cov += U * wU;   /* LK_GLAOFLT v2: the share a part ABOVE a FLOOR point hides (a table top; walls / the ship hull keep v1) */
      best = U * wU + Bd * (1.0 - wU); }
    for (int st = 1; st < 20; st++) { float d = 2.0 * float(st), fall = 1.0 - d / 40.0; if (fall <= best) break;
      float h = aoh(x0 + dv.x * d, y0 + dv.y * d, dix, diy); if (h <= z) continue;
      float t = (h - z) / d, sn = t / sqrt(1.0 + t * t) * fall; if (sn > best) { best = sn; if (sn > gBest) { gBest = sn; gBH = h; gBX = x0 + dv.x * d; gBY = y0 + dv.y * d; } } }
    sum += best; }
  float ao = n > 0.0 ? 1.0 - uAok * sum / n - (uAoflt > 1.5 ? (uAoflt - 2.0 - uAok) * cov / n : 0.0) : 1.0;   /* LK_GLAOFLT v2: the room light comes from above, a part over the point holds it back stronger than a corner: strength uAoflt - 2 (LANDSTALKER_LT_AOCOV, default 0.75; the corner strength uAok is 0.55; user 2026-11-09: 0.55 'duerfte noch etwas kraeftiger sein', 1.0 'zu stark') */
  if (uMdl > 4.5 && gMS > 0.5) { if (uMdl < 5.5) return clamp((gBH - z) / 255.0, 0.0, 1.0); if (uMdl < 6.5) return mod(gBX, 256.0) / 255.0; if (uMdl < 7.5) return mod(gBY, 256.0) / 255.0; return clamp(z + 64.0, 0.0, 255.0) / 255.0; }   /* test aid 6..9: strongest occluder height above z / its x / y (mod 256) / z + 64 */
  if (uMdl > 2.5 && gMS > 0.5) return clamp(ao, 0.0, 1.0) * (uMdl > 3.5 ? 0.0 : 1.0) + (uMdl > 3.5 ? n / 16.0 : 0.0);   /* LK_GLMODEL v1 test aid: 3 = horizon part only, 4 = number of directions / 16 */
  if (f != 1.0 && uAotop > 0.0) ao *= 1.0 - uAotop;
  if (f != 1.0) { float fl = aoh(x0, y0, 0.0, 0.0); if (fl > -32768.0 && z >= fl) { float c = 1.0 - (z - fl) / 24.0; if (c > 0.0) ao *= 1.0 - 0.30 * c; } }
  { float cx = floor(px / 16.0), cy = floor(py / 16.0); if (f == 1.0 && inr(cx, cy) && mod(B(W(cx, cy, 1.0).g), 2.0) > 0.5) z = 32767.0; }
  if (f == 1.0 && uHand > 0.5 && uMdl > 0.5 && uSunR < 0.5 && px >= 0.0 && py >= 0.0 && px < 1184.0 && py < 1184.0) { vec4 f4 = FN(floor(px / 4.0), floor(py / 4.0), 4.0); if (B(f4.r) > 0.5 && B(f4.r) < 1.5 && z <= S16(B(f4.b), B(f4.a)) + 0.5) z = 32767.0; }   /* LK_GLMODEL v1: the ground below a model (the ship's sea) is not darkened by depth: the game's cells there are the deck, not water */
  if (uZref > -32768.0 && z < uZref) { float dd = (uZref - z) / 64.0; if (dd > 1.0) dd = 1.0; ao *= 1.0 - 0.18 * dd; }
  return ao < 0.35 ? 0.35 : ao > 1.0 ? 1.0 : ao; }
vec3 P(float U, float V, float z) { float D = U - 1184.0; return vec3((2.0 * V + 2.0 * z + D) * 0.5, (2.0 * V + 2.0 * z - D) * 0.5, z); }
vec4 W2(float cx, float cy, float hf) { return texture2D(wld2, (vec2(cx, cy + 74.0 * hf) + 0.5) / vec2(74.0, 222.0)); }
vec4 FN(float sx, float sy, float hf) { return texture2D(fine, (vec2(sx, sy + 296.0 * hf) + 0.5) / vec2(296.0, 1480.0)); }
bool cellmdl(float cx, float cy) { return uHand > 0.5 && uMdl > 0.5 && inr(cx, cy) && B(W(cx, cy, 1.0).g) > 1.5; }   /* LK_GLROOM v1: the cell holds a hand-made model (w2 bit 9) */
float sidecl(float x, float y, float z, float cx, float cy, float self, float m3) {   /* = lk_lt_sidecl (patch_lights.py): horizontal distance to a neighbour cell whose side record lk_lt_spk (w row 2 low half) reaches above z */
  float cl = 9999.0;
  if (z >= 4.0 * m3 + 0.5) return cl;   /* lk_lt_m3q (passed in from the fine plane the march already read): nothing around reaches the ray */
  for (int b2 = -1; b2 <= 1; b2++) for (int a2 = -1; a2 <= 1; a2++) { float ax = cx + float(a2), by = cy + float(b2);
    if ((a2 == 0 && b2 == 0) || ax < 0.0 || by < 0.0 || ax > 73.0 || by > 73.0) continue;
    vec4 wc = W(ax, by, 2.0); float tq = B(wc.r), bb = B(wc.g); if (tq == 0.0 || 4.0 * tq + 0.5 <= z) continue;
    if (self != 0.0 && S16(B(W2(ax, by, 2.0).b), B(W2(ax, by, 2.0).a)) == self) continue;
    float bx0 = 16.0 * ax + 4.0 * mod(bb, 4.0), bx1 = 16.0 * ax + 4.0 * (mod(floor(bb / 4.0), 4.0) + 1.0), by0 = 16.0 * by + 4.0 * mod(floor(bb / 16.0), 4.0), by1 = 16.0 * by + 4.0 * (floor(bb / 64.0) + 1.0);
    float ex = x < bx0 ? bx0 - x : x > bx1 ? x - bx1 : 0.0, ey = y < by0 ? by0 - y : y > by1 ? y - by1 : 0.0; cl = min(cl, sqrt(ex * ex + ey * ey)); }
  return cl; }
float sunvis(vec3 sd, float hs, vec3 p, float self) {   /* lk_lt_sunvis: march to the sun through the game heights, the object field, lathes, bushes / pines; soft edge LK_LT_PEN 12 */
  float hl = sqrt(sd.x * sd.x + sd.y * sd.y), res = 1.0, t = 2.0;
  if (hl < 1e-3) hl = 1e-3;
  for (int st = 0; st < 1400; st++) {
    if (st > 0) t += t < 32.0 ? 1.0 : 2.0;
    float x = p.x + sd.x * t, y = p.y + sd.y * t, z = p.z + sd.z * t;
    if (z > uZtop + 1.0 || x < 0.0 || y < 0.0 || x >= 1184.0 || y >= 1184.0) return res;
    float sx = floor(x * 0.25), sy = floor(y * 0.25), cx = floor(sx / 4.0), cy = floor(sy / 4.0);
    vec4 f0 = FN(sx, sy, 0.0), f1 = FN(sx, sy, 1.0); float o = S16(B(f0.b), B(f0.a));
    if (uNslab > 0.5) { float c2 = slabcl(sx, sy, z); if (c2 <= 0.0) return 0.0; if (c2 < 9999.0) { float r2 = 12.0 * c2 / (t * hl); if (r2 < res) res = r2; }
      float c3 = halocl(x, y, z); if (c3 < 9999.0) { float r3 = 12.0 * c3 / (t * hl); if (r3 < res) res = r3; } }   /* v9: slabs + soft sides */
    if (o != 0.0 && o == self) continue;
    if (gKM > 0.5 && uSm.w > 0.5 && ((uHand > 0.5 && mownh(sx, sy)) || (uSm.w > 1.5 && mowng(sx, sy)))) continue;   /* LK_GLMODEL v1: a model's own sub columns: the shadow map has it (LK_GLROOM v1: hand-made models only) */
    vec4 g0 = W2(cx, cy, 0.0); float h = S16(B(g0.r), B(g0.g)); if (h == -32768.0) h = -1e9;
    float hdv = S16(B(W(cx, cy, 1.0 + hs).b), B(W(cx, cy, 1.0 + hs).a)), q = B(f1.r), qt = B(f1.g), r, d;
    if (q > 0.0 && qt == 5.0 && B(g0.b) > 0.0) {   /* a bush (sphere) or pine (cone) + stem */
      vec4 g1 = W2(cx, cy, 1.0); float top = S16(B(g1.r), B(g1.g)), rr = B(g0.a), zb = S16(B(g1.b), B(g1.a)), ddx = x - (16.0 * cx + 8.0), ddy = y - (16.0 * cy + 8.0), dh = sqrt(ddx * ddx + ddy * ddy), cl, zc;
      if (B(g0.b) == 2.0) { zc = zb + 4.0; cl = z >= top ? sqrt(dh * dh + (z - top) * (z - top)) : z >= zc ? dh - rr * pinr((z - zc) / (top - zc)) : 9999.0; }   /* v9 tiers */
      else { float qb = uBushE > 0.5 ? 0.8 : 1.0; zc = top - rr * qb; cl = sqrt(dh * dh + (z - zc) * (z - zc) / (qb * qb)) - rr; }   /* v9 squashed bush crown */
      if (z <= zc && dh - 1.5 < cl) cl = dh - 1.5;
      if (cl <= 0.0) return 0.0; r = 12.0 * cl / (t * hl); if (r < res) res = r;
      d = z - zb + 0.5; if (d <= 0.0) return 0.0; r = 12.0 * d / (t * hl); if (r < res) res = r;
      if (uSside > 0.5) { float cl2 = sidecl(x, y, z, cx, cy, self, B(f1.a)); if (cl2 < 9999.0) { r = 12.0 * cl2 / (t * hl); if (r < res) res = r; } }
      if (12.0 * (z - hdv + 0.5) >= res * t * hl) return res;
      continue; }
    if (q > 0.0 && qt == 3.0) {   /* a lathe (tree) with its drawn profile */
      vec4 a0 = texture2D(prx, (vec2(0.0, q - 1.0) + 0.5) / vec2(26.0, 255.0)), a1 = texture2D(prx, (vec2(1.0, q - 1.0) + 0.5) / vec2(26.0, 255.0));
      float x0 = S16(B(a0.r), B(a0.g)), y0 = S16(B(a0.b), B(a0.a)), z0 = S16(B(a1.r), B(a1.g)), ridge = S16(B(a1.b), B(a1.a)), kk = floor(z - z0), ddx = x - x0, ddy = y - y0, dd = sqrt(ddx * ddx + ddy * ddy);
      if (kk >= 0.0 && kk < ridge - z0) { vec4 pf = texture2D(prx, (vec2(2.0 + floor(kk / 4.0), q - 1.0) + 0.5) / vec2(26.0, 255.0)); float m = mod(kk, 4.0), pv = B(m < 0.5 ? pf.r : m < 1.5 ? pf.g : m < 2.5 ? pf.b : pf.a);
        float cl = dd - pv; if (cl <= 0.0) return 0.0; r = 12.0 * cl / (t * hl); if (r < res) res = r; }
      d = z - h + 0.5; if (d <= 0.0) return 0.0; r = 12.0 * d / (t * hl); if (r < res) res = r;
      if (uSside > 0.5) { float cl2 = sidecl(x, y, z, cx, cy, self, B(f1.a)); if (cl2 < 9999.0) { r = 12.0 * cl2 / (t * hl); if (r < res) res = r; } }
      if (12.0 * (z - hdv + 0.5) >= res * t * hl) return res;
      continue; }
    float fh = S16(B(f0.r), B(f0.g)); if (o != 0.0 && fh > h) h = fh;
    d = z - h + 0.5; if (d <= 0.0) return 0.0;
    r = 12.0 * d / (t * hl); if (r < res) res = r;
    if (uSside > 0.5) { float cl2 = sidecl(x, y, z, cx, cy, self, B(f1.a)); if (cl2 < 9999.0) { r = 12.0 * cl2 / (t * hl); if (r < res) res = r; } }
    if (12.0 * (z - hdv + 0.5) >= res * t * hl) return res; }
  return res; }
float keyvis(vec3 sd, vec3 p) {   /* lk_lt_keyvisd */
  float hl = sqrt(sd.x * sd.x + sd.y * sd.y), res = 1.0, zr = uZref > -32768.0 ? uZref : 0.0, wt = zr + uKbw;
  if (wt < uZtop + 1.0) wt = uZtop + 1.0;
  float dx = sd.x > 0.01 ? 1.0 : sd.x < -0.01 ? -1.0 : 0.0, dy = sd.y > 0.01 ? 1.0 : sd.y < -0.01 ? -1.0 : 0.0, t = 2.0;
  if (hl < 1e-3) hl = 1e-3;
  float kp = mod(abs(uKpen), 2000.0);   /* 2026-11-08: |uKpen| + 2000 = LANDSTALKER_LT_KSLANT=0 (keyShare) */
  for (int st = 0; st < 400; st++) {
    if (st > 0) t += t < 32.0 ? 1.0 : 2.0;
    if (t >= 600.0) break;
    float x = p.x + sd.x * t, y = p.y + sd.y * t, z = p.z + sd.z * t, hh;
    if (z > wt && (uKpen < 0.0 || kp * (z - wt) >= res * t * hl)) return res;   /* 2026-11-08 lk_lt_kbwsoft */
    if (uIfine > 0.5) { float c2 = slabcl(floor(x / 4.0), floor(y / 4.0), z), c3 = halocl(x, y, z); if (c2 <= 0.0) return 0.0; if (c2 < 9999.0) { float r2 = kp * c2 / (t * hl); if (r2 < res) res = r2; }
      if (c3 < 9999.0) { float r3 = kp * c3 / (t * hl); if (r3 < res) res = r3; }   /* v9 */
      float c4 = mslabcl(x, y, z); if (c4 <= 0.0) return 0.0; if (c4 < 9999.0) { float r4 = kp * c4 / (t * hl); if (r4 < res) res = r4; } }   /* LK_GLMODEL v1: floating model parts */
    float h = aoh2(x, y, dx, dy, 0.0); if (h == -32768.0) continue;
    if (h == 32767.0) { if (uKpen > 0.0) hh = zr + uKbw; else { if (z > zr + uKbw) continue; hh = 1e9; } } else hh = h;   /* 2026-11-08 lk_lt_kbwsoft */
    float d = z - hh + 0.5; if (d <= 0.0) return 0.0;
    float r = kp * d / (t * hl); if (r < res) res = r; }
  return res; }
float sunShare(vec3 sd, float hs, float U, float V, float face, float z, float robj, float layA) {   /* lk_lt_sunfill for one pixel */
  vec3 n = vec3(FNX(face), FNY(face), FNZ(face)), pp = P(U, V, z); float ndl = sd.z;
  if (face != 1.0 && n.x * sd.x + n.y * sd.y + (face > 19.5 ? n.z * sd.z : 0.0) <= 0.0) { float vis = 1.0, qx = pp.x - n.x * 2.0, qy = pp.y - n.y * 2.0, sx = floor(qx / 4.0), sy = floor(qy / 4.0);
    if (sx >= 0.0 && sy >= 0.0 && sx < 296.0 && sy < 296.0) { vec4 f1 = FN(sx, sy, 1.0); float gh = S16(B(W2(floor(sx / 4.0), floor(sy / 4.0), 2.0).r), B(W2(floor(sx / 4.0), floor(sy / 4.0), 2.0).g));
      if (B(f1.r) == 0.0 && !mownh(sx, sy) && gh != -32768.0 && gh <= 48.0 && z <= gh) {   /* LK_GLROOM v1: inside a hand-made model = like a proxy (the wall keeps the sky share; a corner sub column of the model was 0) */ vec4 f0 = FN(sx, sy, 0.0); vis = sunvis(sd, hs, vec3(qx, qy, gh + 0.5), S16(B(f0.b), B(f0.a))); } }
    return floor(ndl * vis * 255.0); }
  float cx = floor((pp.x - n.x * 2.0) / 4.0), cy = floor((pp.y - n.y * 2.0) / 4.0), ob = 0.0;
  if (cx >= 0.0 && cy >= 0.0 && cx < 296.0 && cy < 296.0) { vec4 f0 = FN(cx, cy, 0.0), f1 = FN(cx, cy, 1.0); ob = S16(B(f0.b), B(f0.a)); if (ob > 0.0 && ob < 1024.0 && B(f1.b) == 1.0 && layA < 0.5) ob = 0.0; }
  if (ob == 0.0 && robj != 0.0 && layA > 0.5) ob = robj;
  vec3 ps = vec3(pp.x + n.x * 3.0, pp.y + n.y * 3.0, z + n.z * 3.0); gKM = 1.0; float vis = sunvis(sd, hs, ps, ob); gKM = 0.0;
  vis = min(vis, smvis2(ps, n, sd, hs, 12.0)) * ndl;   /* LK_GLMODEL v1 outdoors: field march without the models (gKM) + the models' sun shadow map */
  return vis >= 1.0 ? 255.0 : vis <= 0.0 ? 0.0 : floor(vis * 255.0); }
float smD(vec2 c, float hs) { if (c.x < 0.0 || c.y < 0.0 || c.x >= 1024.0 || c.y >= 1024.0) return -99999.0; vec4 m = texture2D(mdl, (vec2(2048.0 + 1024.0 * (hs > 0.5 ? uSmSl.y : uSmSl.x), 0.0) + floor(c) + 0.5) / vec2(4096.0, 2048.0));   /* LK_GLOBJ v1: the slot that holds this map */
  float e = B(m.r) + 256.0 * B(m.g); return e > 0.5 ? (e - 32768.0) / 8.0 : -99999.0; }   /* stage 2: the model's nearest depth towards the key light at shadow map texel c */
float smvis2(vec3 p, vec3 n, vec3 sd, float hs, float kp) {   /* n: the receiver's normal (receiver plane bias: a tap expects the receiver's own plane, so a flat or slanted surface never shadows itself) */   /* stage 2: light share from a MODEL SHADOW MAP (hs 0: key / sun, 1: next sun step): blocker search, then a filter whose width grows with the distance to the blocker (the march's penumbra rule, kp) */
  vec4 sm = hs > 0.5 ? uSm2 : uSm; if (sm.w < 0.5) return 1.0;
  vec3 e1 = hs > 0.5 ? uE12 : uE1, e2 = hs > 0.5 ? uE22 : uE2;
  vec3 d = normalize(sd); p += d * uSmo.x; float dp = dot(p, d), bs = 0.0, bn = 0.0, lit = 0.0, nd = max(dot(n, d), 0.25); vec2 c = (vec2(dot(p, e1), dot(p, e2)) - sm.xy) * sm.z, g = -vec2(dot(n, e1), dot(n, e2)) / nd;   /* LK_GLROOM v1 tunables uSmo: x = receiver moved towards the light, y = least filter width, z = depth bias (default 0 / 0.75 / 1.5 = before) */   /* g: depth change of the receiver's plane per unit */
  for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++) { vec2 o = vec2(float(i), float(j)) * 2.0; float D = smD(c + o * sm.z, hs), e = dp + dot(o, g); if (D > e + uSmo.z) { bs += D - e; bn += 1.0; } }
  if (bn < 0.5) return 1.0;
  float w = clamp((bs / bn) * sqrt(d.x * d.x + d.y * d.y) / kp, uSmo.y, 12.0);
  for (int j = -3; j <= 3; j++) for (int i = -3; i <= 3; i++) { vec2 o = vec2(float(i), float(j)) * w / 3.0; float D = smD(c + o * sm.z, hs); if (D <= dp + dot(o, g) + uSmo.z) lit += 1.0; }
  return lit / 49.0; }
float smvis(vec3 p, vec3 n) { return smvis2(p, n, uSd, 0.0, mod(abs(uKpen), 2000.0)); }
float keyShare(float U, float V, float face, float z) {   /* the key light share of lk_lt_blockcalc */
  vec3 n = vec3(FNX(face), FNY(face), FNZ(face)), pp = P(U, V, z);
  float ndl = n.x * uSd.x + n.y * uSd.y + (face > 19.5 ? n.z * uSd.z : 0.0), kw = 1.0;   /* LK_GLMODEL v1: a model normal tilts in z too */
  if (face >= 4.0 && abs(uKpen) < 2000.0) kw = min((ndl + 0.25) * 2.0, 1.0);   /* 2026-11-08 lk_lt_kslant */
  else if (face != 1.0 && ndl <= 0.0) kw = 0.0;
  if (kw <= 0.0) return 255.0;
  vec3 ps = vec3(pp.x + n.x * OFF2(n.x, n.y, 3.0), pp.y + n.y * OFF2(n.x, n.y, 3.0), z + n.z * 3.0); gKM = 1.0;
  float vis = keyvis(uSd, ps); gKM = 0.0; vis = min(vis, smvis(ps, n));   /* LK_GLMODEL v1 stage 2: field march without the models + the models' shadow map */
  vis = 1.0 - kw * (1.0 - clamp(vis, 0.0, 1.0));
  return vis >= 1.0 ? 255.0 : vis <= 0.0 ? 0.0 : floor(vis * 255.0); }
float trc(float v) { return v < 0.0 ? -floor(-v) : floor(v); }
float cellT(float cx, float cy);   /* below */
vec2 shafts(float U, float V, float face, float z) {   /* lk_lt_shblock: beam (glow along the view ray) and pool (lit floor inside the shaft, with the shaft's own shadows), quantised per shaft as the CPU */
  float beam = 0.0, pool = 0.0, bx0 = uBlk.x * 32.0, by0 = uBlk.y * 32.0;
  for (int k = 0; k < 3; k++) { if (float(k) >= uNsh) break;
    vec4 A = uSh[3 * k], Q = uSh[3 * k + 1]; vec3 d = uSh[3 * k + 2].xyz; float r = A.w, kk = Q.x, h = Q.y;
    float u0 = A.x - A.y + 1184.0, v0 = (A.x + A.y) * 0.5 - A.z, u1 = u0 + (d.x - d.y) * h, v1 = v0 + ((d.x + d.y) * 0.5 - d.z) * h, m = r * 2.0 + 8.0;
    if (bx0 + 32.0 < min(u0, u1) - m || bx0 > max(u0, u1) + m || by0 + 32.0 < min(v0, v1) - m - 20.0 || by0 > max(v0, v1) + m + 20.0) continue;
    float zs = face > 0.5 ? z : trc(A.z) - 24.0, sum = 0.0;
    if (face > 0.5) { vec3 pp = P(U, V, zs); vec3 vv = vec3(pp.x - A.x, pp.y - A.y, zs - A.z); float s2 = vv.x * d.x + vv.y * d.y + vv.z * d.z; vec3 qv = vec3(vv.x - s2 * d.x, vv.y - s2 * d.y, vv.z - s2 * d.z); float q = sqrt(qv.x * qv.x + qv.y * qv.y + qv.z * qv.z);
      if (q < r * 1.25 && s2 > -8.0) { vec3 n = vec3(FNX(face), FNY(face), FNZ(face));
        float w = (r * 1.25 - q) / (r * 1.1); if (w > 1.0) w = 1.0; w = w * w * (3.0 - 2.0 * w) * kk * 0.8;
        w *= keyvis(d, vec3(pp.x + n.x * OFF2(n.x, n.y, 3.0), pp.y + n.y * OFF2(n.x, n.y, 3.0), zs + n.z * 3.0)); w += pool * (1.0 / 255.0); pool = w >= 1.0 ? 255.0 : floor(w * 255.0); } }
    for (int st = 0; st < 400; st++) { float zz = zs + 2.0 + 4.0 * float(st); if (zz >= A.z + h * d.z) break;
      vec3 pp = P(U, V, trc(zz)); if (cellT(floor(pp.x / 16.0), floor(pp.y / 16.0)) <= -32768.0) continue;   /* 2026-11-08: only over the room's cells (lk_lt_shblock) */
      vec3 vv = vec3(pp.x - A.x, pp.y - A.y, zz - A.z); float s2 = vv.x * d.x + vv.y * d.y + vv.z * d.z; vec3 qv = vec3(vv.x - s2 * d.x, vv.y - s2 * d.y, vv.z - s2 * d.z); float q = sqrt(qv.x * qv.x + qv.y * qv.y + qv.z * qv.z);
      if (q >= r || s2 < 0.0 || s2 > h) continue;
      float w = 1.0 - (q / r) * (q / r); w *= w;
      float fa = s2 < 70.0 ? s2 / 70.0 : 1.0; if (s2 > h - 70.0) fa *= (h - s2) / 70.0; fa *= s2 < 220.0 ? 0.55 + 0.45 * s2 / 220.0 : 1.0;
      sum += w * fa; }
    sum *= 0.26 * kk; sum += beam * (1.0 / 255.0); beam = sum >= 1.0 ? 255.0 : floor(sum * 255.0); }
  return vec2(beam, pool); }
float cellT(float cx, float cy) { if (!inr(cx, cy)) return -32768.0; vec4 w = W(cx, cy, 0.0); return S16(B(w.r), B(w.g)); }   /* lk_lt_cell */
bool dent(float cx, float cy, float cf) {   /* lk_lt_dent */
  float n = 1.0, ax = cf == 3.0 ? 1.0 : 0.0, ay = cf == 2.0 ? 1.0 : 0.0;
  for (int d = 1; d <= 3; d++) { if (cellT(cx - float(d) * ax, cy - float(d) * ay) <= -32768.0) break; n += 1.0; }
  for (int d = 1; d <= 3; d++) { if (cellT(cx + float(d) * ax, cy + float(d) * ay) <= -32768.0) break; n += 1.0; }
  return n <= 3.0; }
float fdv(float a, float b) { return floor(a / b); }
float vtAt(float sx, float sy, float layA) { if (sx < 0.0 || sy < 0.0 || sx >= 296.0 || sy >= 296.0) return -32768.0; vec4 v = texture2D(fine2, (vec2(sx, sy) + 0.5) / 296.0); return layA > 0.5 ? S16(B(v.r), B(v.g)) : S16(B(v.b), B(v.a)); }
float rfocc(float sx, float sy, float z) { if (z <= vtAt(sx, sy, 1.0)) return 1.0; vec2 q = SLB(sx, sy); return (q.y > q.x && z >= q.x && z <= q.y) ? 1.0 : 0.0; }   /* v9 lk_lt_rfocc */
float iocc(float sx, float sy, float z, float layA) { if (z <= ifh(sx, sy, 0.0)) return 1.0; if (layA > 0.5) { vec2 q = SLB(sx, sy); if (q.y > q.x && z >= q.x && z <= q.y) return 1.0; } return 0.0; }   /* v9 lk_lt_occ */
float idiag(float sx, float sy, float z, float f, float layA) {   /* v9 lk_lt_idiag: the normal of a fine field side face from the shape around it (16 directions) */
  float gx = 0.0, gy = 0.0, k = 0.0;
  for (int dy = -3; dy <= 3; dy++) for (int dx = 1; dx <= 3; dx++) { float ex = float(dx), ey = float(dy); gx += iocc(sx - ex, sy + ey, z, layA) - iocc(sx + ex, sy + ey, z, layA); gy += iocc(sx + ey, sy - ex, z, layA) - iocc(sx + ey, sy + ex, z, layA); }
  if (gx + gy <= 0.0) return f;
  if (0.773010453 * gy - -0.634393284 * gx > 0.0) k += 1.0;
  if (0.881921264 * gy - -0.471396737 * gx > 0.0) k += 1.0;
  if (0.956940336 * gy - -0.290284677 * gx > 0.0) k += 1.0;
  if (0.995184727 * gy - -0.0980171403 * gx > 0.0) k += 1.0;
  if (0.995184727 * gy - 0.0980171403 * gx > 0.0) k += 1.0;
  if (0.956940336 * gy - 0.290284677 * gx > 0.0) k += 1.0;
  if (0.881921264 * gy - 0.471396737 * gx > 0.0) k += 1.0;
  if (0.773010453 * gy - 0.634393284 * gx > 0.0) k += 1.0;
  if (0.634393284 * gy - 0.773010453 * gx > 0.0) k += 1.0;
  if (0.471396737 * gy - 0.881921264 * gx > 0.0) k += 1.0;
  if (0.290284677 * gy - 0.956940336 * gx > 0.0) k += 1.0;
  if (0.0980171403 * gy - 0.995184727 * gx > 0.0) k += 1.0;
  if (-0.0980171403 * gy - 0.995184727 * gx > 0.0) k += 1.0;
  if (-0.290284677 * gy - 0.956940336 * gx > 0.0) k += 1.0;
  if (-0.471396737 * gy - 0.881921264 * gx > 0.0) k += 1.0;
  return k == 4.0 ? 2.0 : k == 12.0 ? 3.0 : 4.0 + k; }
float mfc(vec3 mn) { return mn.z > 0.94 ? 1.0 : mn.x > 0.995 ? 2.0 : mn.y > 0.995 ? 3.0 : 20.0; }   /* LK_GLROOM v1: a hand model's (near) axis wall = the classic +x / +y face (the stored normal is up to 0.004 off: code 20 sent a straight wall down the slanted-face rules, church 632 door wall dark) */
vec2 gdec(float U, float V, float zm) {   /* LK_GLROOM v1: the generated room model's answer for a view ray, decided before the field ray: (face, whole z), (0, 0) = the field answers, (-1, 0) = no generated model here */
  float D = U - 1184.0, gfc = -1.0, gz = 0.0;
  if (uMdl > 1.2 && uMdl < 1.3 && zm > -99998.0) return vec2(0.0, 0.0);   /* test aid LANDSTALKER_GL5_MODELDBG=20: every model hit answered by the field */
  if (zm > -99998.0) { vec3 mn = octdec(gMB); vec3 q = P(U, V, zm);
    float fc = mn.z > 0.94 ? 1.0 : mn.x > 0.99 ? 2.0 : mn.y > 0.99 ? 3.0 : 0.0, zf = floor(zm + 0.5);   /* a generated box face gives the field view ray's answer: face code, whole z, the hit sub column checked with the field's half open rule */
    float zx = fc == 2.0 ? 4.0 * floor(q.x / 4.0 + 0.5) - V - D * 0.5 : fc == 3.0 ? 4.0 * floor(q.y / 4.0 + 0.5) - V + D * 0.5 : zf;   /* a wall: the exact z where the ray meets the wall plane (plane = the nearest multiple of 4) */
    if (fc > 1.5) zf = ceil(zx) - 1.0;   /* the field's whole z (first whole z inside the wall's sub column).  Tried 2026-11-08: the NEAREST whole z (user: 'wenn das neue genauer ist, nimm das') ->
       exact only on every 2nd pixel column (odd D: half a unit off), and the flame / AO terms are tuned to the field point: a 2 pixel light band on room 680's stair (user: 'hier verlaeuft ein dunkler Streifen') */
    float hsx = fdv(2.0 * V + 2.0 * zf + D, 8.0), hsy = fdv(2.0 * V + 2.0 * zf - D, 8.0);
    if (gGen > 0.5) {   /* the buffer's surface is the generated room model (a hand-made model keeps its own path) */
      bool foot = false; if (fc > 1.5 && zx == floor(zx)) { float lsx = fdv(2.0 * V + 2.0 * zx + D, 8.0), lsy = fdv(2.0 * V + 2.0 * zx - D, 8.0); vec4 lf = FN(lsx, lsy, 4.0); foot = B(lf.r) > 0.5 && zx <= S16(B(lf.b), B(lf.a)); }   /* the ray meets the wall
         exactly at its foot edge (whole z on the top of the sub column in front): the field takes that top, the buffer's depth tie may take the wall */
      if (fc > 0.5 && !foot && !(fc > 1.5 && mod(D, 4.0) == 0.0) && mowng(hsx, hsy) && B(FN(hsx, hsy, 4.0).r) < 2.5 && zf <= S16(B(FN(hsx, hsy, 4.0).b), B(FN(hsx, hsy, 4.0).a))) { gfc = fc; gz = zf; }
      else gfc = 0.0; } }   /* else: a vertical corner line of the boxes (D = x - y a multiple of 4: the field's half open / diagonal rules decide there), a wall foot tie or a thin pillar:
       the field answers (it equals the box model) */
  return vec2(gfc, gz); }
vec3 viewray(float U, float V, float layA) {   /* lk_lt_ray / lk_lt_rayf: (face, z, robj) of one room picture pixel */
  float D = U - 1184.0, rob = 0.0, cf = 0.0, cz = 0.0, pin = 0.0, ptop = -32768.0, pcx = -999.0, pcy = -999.0;
  if (uRayF > 0.5) { float zmo = -99999.0;
    if (uMdl > 0.5) { float mu = U - uMo.x, mv = V - uMo.y; if (mu >= 0.0 && mv >= 0.0 && mu < uMo.z && mv < uMo.w) { vec4 m = texture2D(mdl, (vec2(mu, mv) + 0.5) / vec2(4096.0, 2048.0)); float e = B(m.r) + 256.0 * B(m.g);
      if (e > 0.5) { gGen = e > 45056.0 ? 1.0 : 0.0; float ob = e < 24576.0 ? 1.0 : 0.0; zmo = (e - (gGen > 0.5 ? 49152.0 : ob > 0.5 ? 16384.0 : 32768.0)) / 8.0; gMB = vec2(B(m.b), B(m.a)); if (ob > 0.5 && layA < 0.5) zmo = -99999.0; } } }   /* LK_GLOBJ v1: a tree / bush surface only for layer A pixels (the drawn crown) */   /* LK_GLMODEL v1 outdoors: both layers (first try layer A only: walls drawn in layer B then lay under their own model = shadowed by it) */
    vec2 gd = zmo > -99998.0 ? gdec(U, V, zmo) : vec2(-1.0, 0.0); if (gd.x > -0.5 && gd.x < 0.5) zmo = -99999.0;   /* LK_GLROOM v1: the generated ground model outdoors (objects stay the field's: kind 3) */
    float z0 = max(uZtop + 2.0 < uZmax ? uZtop + 2.0 : uZmax, ceil(zmo));
    for (int st = 0; st < 2400; st++) { float z = z0 - float(st); if (z < -40.0) break;
      if (gd.x > 0.5) { if (z <= gd.y) { gMH = 1.0; float hx2 = fdv(2.0 * V + 2.0 * gd.y + D, 8.0), hy2 = fdv(2.0 * V + 2.0 * gd.y - D, 8.0); if (rob == 0.0 && layA > 0.5) { vec4 f0 = FN(hx2, hy2, 0.0); rob = S16(B(f0.b), B(f0.a)); } return vec3(gd.x, gd.y, rob); } }
      else if (z <= zmo) { vec3 mn = octdec(gMB); gMH = 1.0; return vec3(mfc(mn), floor(zmo + 0.5), rob); }
      float sx = fdv(2.0 * V + 2.0 * z + D, 8.0), sy = fdv(2.0 * V + 2.0 * z - D, 8.0), top = vtAt(sx, sy, layA), inn = top > -32768.0 ? 1.0 : 0.0, fo = 0.0;
      float mo = -99999.0; if (uMdl > 0.5 && sx >= 0.0 && sy >= 0.0 && sx < 296.0 && sy < 296.0) { vec4 f4 = FN(sx, sy, 4.0); if (B(f4.r) > 0.5 && B(f4.r) < 1.5) { mo = S16(B(f4.b), B(f4.a)); top = mo; inn = mo > -32768.0 ? 1.0 : 0.0; } }   /* owned by a hand-made model: the ground below the model (LK_GLROOM v1: generated kinds 2 / 3 stay field columns) */
      if (inn > 0.5) { vec4 f0 = FN(sx, sy, 0.0); fo = S16(B(f0.b), B(f0.a)); }
      if (cf > 0.0 && inn > 0.5 && z > top && !dent(floor(sx / 4.0), floor(sy / 4.0), cf)) cf = 0.0;
      if (inn > 0.5 && rob == 0.0 && fo != 0.0 && layA > 0.5) rob = fo;
      if (uNslab > 0.5 && layA > 0.5 && mo < -99998.0) { vec2 sb = SLB(sx, sy); if (sb.y > sb.x && z >= sb.x && z <= sb.y) {   /* v9: a slab */
        if ((sx == pcx && sy == pcy) || pcx == -999.0 || z == sb.y) return vec3(1.0, z, rob);
        if (sx == pcx) return vec3(3.0, z, rob);
        if (sy == pcy) return vec3(2.0, z, rob);
        return vec3(rfocc(pcx, sy, z) > 0.5 && rfocc(sx, pcy, z) < 0.5 ? 3.0 : 2.0, z, rob); } }
      if (z <= top) { if (fo != 0.0 && layA > 0.5) rob = fo;
        if ((sx == pcx && sy == pcy) || pcx == -999.0 || z == top) return vec3(1.0, z, rob);
        if (sx == pcx) return vec3(3.0, z, rob);
        if (sy == pcy) return vec3(2.0, z, rob);
        { float ty = vtAt(pcx, sy, 1.0), tx = vtAt(sx, pcy, 1.0); return vec3(z <= ty && z > tx ? 3.0 : 2.0, z, rob); } }
      if (pcx != -999.0 && pin > 0.5 && inn < 0.5 && z > ptop && cf == 0.0) { float ty = vtAt(pcx, sy, 1.0), tx = vtAt(sx, pcy, 1.0); cz = z; cf = sx == pcx ? 3.0 : sy == pcy ? 2.0 : (ty == -32768.0 && tx > -32768.0 ? 3.0 : 2.0); }
      pcx = sx; pcy = sy; ptop = top; pin = inn; }
    return cf > 0.0 ? vec3(cf, cz, rob) : vec3(0.0, 0.0, rob); }
  if (uIfine > 0.5) { float psx = -999.0, psy = -999.0, pfn = 0.0, zm = -99999.0;   /* v9 lk_lt_rayi */
    if (uMdl > 0.5) { float mu = U - uMo.x, mv = V - uMo.y; if (mu >= 0.0 && mv >= 0.0 && mu < uMo.z && mv < uMo.w) { vec4 m = texture2D(mdl, (vec2(mu, mv) + 0.5) / vec2(4096.0, 2048.0)); float e = B(m.r) + 256.0 * B(m.g);
      if (e > 0.5) { gGen = e > 45056.0 ? 1.0 : 0.0; float ob = e < 24576.0 ? 1.0 : 0.0; zm = (e - (gGen > 0.5 ? 49152.0 : ob > 0.5 ? 16384.0 : 32768.0)) / 8.0; gMB = vec2(B(m.b), B(m.a)); if (ob > 0.5 && layA < 0.5) zm = -99999.0; } } }   /* LK_GLMODEL v1: the model's first surface on this view ray */
    vec2 gd = gdec(U, V, zm); float gfc = gd.x, gz = gd.y; if (gfc > -0.5 && gfc < 0.5) zm = -99999.0;   /* LK_GLROOM v1: decided BEFORE the field ray (a fallback must let the field start at its own first z, else it skips the top in front of a wall foot) */
    float zst = max(uZmax, ceil(zm));
    for (int st = 0; st < 2400; st++) { float z = zst - float(st); if (z < -40.0) break;
      if (gfc > 0.5) { if (z <= gz) { gMH = 1.0; float hx2 = fdv(2.0 * V + 2.0 * gz + D, 8.0), hy2 = fdv(2.0 * V + 2.0 * gz - D, 8.0);
          if (rob == 0.0) { vec4 g2 = W2(floor(hx2 / 4.0), floor(hy2 / 4.0), 2.0); rob = S16(B(g2.b), B(g2.a)); }   /* the cell's object, as the field ray takes it at its hit */
          return vec3(gfc, gz, rob); } }
      else if (z <= zm) { vec3 mn = octdec(gMB); gMH = 1.0; return vec3(mfc(mn), floor(zm + 0.5), rob); }   /* LK_GLMODEL v1: reached the model surface before any field hit */
      float sx = fdv(2.0 * V + 2.0 * z + D, 8.0), sy = fdv(2.0 * V + 2.0 * z - D, 8.0), cx = floor(sx / 4.0), cy = floor(sy / 4.0);
      bool ins = sx >= 0.0 && sy >= 0.0 && sx < 296.0 && sy < 296.0; vec2 sb = SLB(sx, sy); float fo = 0.0;
      if (ins) { vec4 f0 = FN(sx, sy, 0.0); if (S16(B(f0.b), B(f0.a)) == 2047.0) fo = 1.0; }
      float mo = -99999.0; if (uMdl > 0.5 && ins) { vec4 f4 = FN(sx, sy, 4.0); if (B(f4.r) > 0.5 && B(f4.r) < 1.5) mo = S16(B(f4.b), B(f4.a)); }   /* LK_GLROOM v1: a generated box column (kind 2) stays a plain field column here (its top = the field's) */   /* LK_GLMODEL v1: model owned = the ground below the model, no slab (the model buffer has the real surface) */
      float sl = (ins && layA > 0.5 && sb.y > sb.x && mo < -99998.0) ? 1.0 : 0.0, fn = (sl > 0.5 || fo > 0.5 || mo > -99998.0) ? 1.0 : 0.0, top = mo > -99998.0 ? mo : ifh(sx, sy, layA > 0.5 ? 0.0 : 1.0), inn = top > -32768.0 ? 1.0 : 0.0;
      if (inn > 0.5 && rob == 0.0) { vec4 g2 = W2(cx, cy, 2.0); float ob = S16(B(g2.b), B(g2.a)); if (ob != 0.0) rob = ob; }
      if (cf > 0.0 && inn > 0.5 && z > top && !dent(cx, cy, cf)) cf = 0.0;
      if (sl > 0.5 && z >= sb.x && z <= sb.y) {
        if ((sx == psx && sy == psy) || psx == -999.0 || z == sb.y) return vec3(1.0, z, rob);
        return vec3(idiag(sx, sy, z, sx == psx ? 3.0 : sy == psy ? 2.0 : (iocc(psx, sy, z, layA) > 0.5 && iocc(sx, psy, z, layA) < 0.5 ? 3.0 : 2.0), layA), z, rob); }
      if (z <= top) {
        if (fn < 0.5 && pfn < 0.5) {
          if ((cx == pcx && cy == pcy) || pcx == -999.0 || z == top) return vec3(1.0, z, rob);
          if (cx == pcx) return vec3(3.0, z, rob);
          if (cy == pcy) return vec3(2.0, z, rob);
          { float ty = cellT(pcx, cy), tx = cellT(cx, pcy); return vec3(z <= ty && z > tx ? 3.0 : 2.0, z, rob); } }
        if ((sx == psx && sy == psy) || psx == -999.0 || z == top) return vec3(1.0, z, rob);
        return vec3(idiag(sx, sy, z, sx == psx ? 3.0 : sy == psy ? 2.0 : (iocc(psx, sy, z, layA) > 0.5 && iocc(sx, psy, z, layA) < 0.5 ? 3.0 : 2.0), layA), z, rob); }
      if (pcx != -999.0 && pin > 0.5 && inn < 0.5 && z >= ptop && cf == 0.0) { cz = z;
        if (fn < 0.5 && pfn < 0.5) { float ty = cellT(pcx, cy), tx = cellT(cx, pcy); cf = cx == pcx ? 3.0 : cy == pcy ? 2.0 : (ty == -32768.0 && tx > -32768.0 ? 3.0 : 2.0); }
        else { float ty = ifh(psx, sy, 0.0), tx = ifh(sx, psy, 0.0); cf = sx == psx ? 3.0 : sy == psy ? 2.0 : (ty == -32768.0 && tx > -32768.0 ? 3.0 : 2.0); } }
      pcx = cx; pcy = cy; psx = sx; psy = sy; ptop = top; pin = inn; pfn = fn; }
    return cf > 0.0 ? vec3(cf, cz, rob) : vec3(0.0, 0.0, rob); }
  vec2 gc = vec2(-1.0, 0.0);   /* LK_GLROOM v1: the cell ray (outdoor rooms without objects) with a generated room model: decided before the march, as in the fine rays */
  if (uMdl > 0.5) { float mu = U - uMo.x, mv = V - uMo.y; if (mu >= 0.0 && mv >= 0.0 && mu < uMo.z && mv < uMo.w) { vec4 m = texture2D(mdl, (vec2(mu, mv) + 0.5) / vec2(4096.0, 2048.0)); float e = B(m.r) + 256.0 * B(m.g);
    if (e > 0.5 && e >= 24576.0) { gMB = vec2(B(m.b), B(m.a)); gGen = e > 45056.0 ? 1.0 : 0.0; gc = gdec(U, V, (e - (gGen > 0.5 ? 49152.0 : 32768.0)) / 8.0); } } }   /* (trees / bushes: the cell ray has no object rooms) */
  for (int st = 0; st < 2400; st++) { float z = uZmax - float(st); if (z < -40.0) break;
    if (gc.x > 0.5 && z <= gc.y) { gMH = 1.0; float hx2 = fdv(2.0 * V + 2.0 * gc.y + D, 8.0), hy2 = fdv(2.0 * V + 2.0 * gc.y - D, 8.0); if (rob == 0.0) { vec4 g2 = W2(floor(hx2 / 4.0), floor(hy2 / 4.0), 2.0); rob = S16(B(g2.b), B(g2.a)); } return vec3(gc.x, gc.y, rob); }
    float cx = fdv(2.0 * V + 2.0 * z + D, 32.0), cy = fdv(2.0 * V + 2.0 * z - D, 32.0), top = cellT(cx, cy), inn = top > -32768.0 ? 1.0 : 0.0;
    if (inn > 0.5 && layA < 0.5 && uSunR < 0.5) { float n = S16(B(W(cx, cy, 0.0).b), B(W(cx, cy, 0.0).a)); if (n > -32768.0) top = n; }
    if (inn > 0.5 && rob == 0.0) { vec4 g2 = W2(cx, cy, 2.0); float ob = S16(B(g2.b), B(g2.a)); if (ob != 0.0) rob = ob; }
    if (cf > 0.0 && inn > 0.5 && z > top && !dent(cx, cy, cf)) cf = 0.0;
    if (z <= top) {
      if ((cx == pcx && cy == pcy) || pcx == -999.0 || z == top) return vec3(1.0, z, rob);
      if (cx == pcx) return vec3(3.0, z, rob);
      if (cy == pcy) return vec3(2.0, z, rob);
      { float ty = cellT(pcx, cy), tx = cellT(cx, pcy); return vec3(z <= ty && z > tx ? 3.0 : 2.0, z, rob); } }
    if (pcx != -999.0 && pin > 0.5 && inn < 0.5 && z >= ptop && cf == 0.0) { float ty = cellT(pcx, cy), tx = cellT(cx, pcy); cz = z; cf = cx == pcx ? 3.0 : cy == pcy ? 2.0 : (ty == -32768.0 && tx > -32768.0 ? 3.0 : 2.0); }
    pcx = cx; pcy = cy; ptop = top; pin = inn; }
  return cf > 0.0 ? vec3(cf, cz, rob) : vec3(0.0, 0.0, rob); }
vec4 G(float x, float y) { return texture2D(geo, (vec2(x, y) + 0.5) / vec2(32.0, 64.0)); }
vec4 termsP(float plane, float face, float z, float U, float V) {   /* flame terms 4 * plane .. 4 * plane + 3 of the block's light list */
  vec3 n = vec3(FNX(face), FNY(face), FNZ(face)), p = P(U, V, z);
  float nl = B(texture2D(btab, (uBlk + 0.5) / vec2(76.0, 38.0)).b); vec4 I = texture2D(bli, (vec2(uBlk.x + 76.0 * plane, uBlk.y) + 0.5) / vec2(152.0, 38.0)), o = vec4(0.0);
  for (int c = 0; c < 4; c++) { if (plane * 4.0 + float(c) >= nl) break;
    int li = int(B(c == 0 ? I.r : c == 1 ? I.g : c == 2 ? I.b : I.a));
    gSoft = uSoftR > 0.5 && face > 19.5 && abs(n.x) < 0.97 && abs(n.y) < 0.97 && abs(n.z) < 0.97 ? 1.0 : 0.0;   /* LK_GLSOFTR v1 (user 2026-11-09 'ja'): ROUND model surfaces (model pixels, face 20 with the model normal gN, whose normal is not along an axis: lathes / hulls; boxes and table tops are axis-aligned) take the fire light
       wrapped (0.5 + 0.5 n.l): the art already paints their shading (light from the left), a fire from the other side turned it round too hard (vase lip streak) */
    float t = termS(p, n, uLP[li], uLC[li].w, uLF[li].zw), q = t > 1.0 ? 255.0 : floor(t * 255.0); gSoft = 0.0;
    if (c == 0) o.r = q; else if (c == 1) o.g = q; else if (c == 2) o.b = q; else o.a = q; }
  return o; }
vec3 anchor(float ix, float iy, float face, float z) {   /* the 2 x 2 shortcut of lk_lt_blockcalc (AO, key light): the odd pixels use the even one on the same surface; returns (ix, iy, z) to compute at */
  float ax = floor(ix / 2.0) * 2.0, ay = floor(iy / 2.0) * 2.0;
  if (ax != ix || ay != iy) { vec4 g = G(ax, ay); float f2 = B(g.r), z2 = S16(B(g.g), B(g.b)); if (f2 == face && abs(z2 - z) <= 2.0) return vec3(ax, ay, z2); }
  return vec3(ix, iy, z); }
float aoP(float ix, float iy, float face, float z) {
  if (face < 0.5 || uAor < 0.5) return 255.0;
  if (uMdl > 1.5 && uMdl < 2.5 && gMS > 0.5) return 7.0;   /* LK_GLMODEL v1 test aid (LANDSTALKER_GL5_MODELDBG=3): marks model side pixels */
  vec3 a = anchor(ix, iy, face, z); vec3 p = P(uBlk.x * 32.0 + a.x, uBlk.y * 32.0 + a.y, a.z); return floor(aoval(p.x, p.y, a.z, face) * 255.0 + 0.5); }
float sunP(vec3 sd, float hs, float ix, float iy, float face, float z, float robj, float la) {   /* sun share (sun rooms) or key light share (key light rooms), as the block stores it */
  float U = uBlk.x * 32.0 + ix, V = uBlk.y * 32.0 + iy;
  if (uSunR > 0.5) return face < 0.5 ? 0.0 : sunShare(sd, hs, U, V, face, z, robj, la);
  if (uKey > 0.5) { if (face < 0.5) return 255.0; vec3 a = anchor(ix, iy, face, z); return keyShare(uBlk.x * 32.0 + a.x, uBlk.y * 32.0 + a.y, face, a.z); }
  return 0.0; }
void main() {   /* uMode 0: GL5b geometry (32 x 64: rows 0..31 face / z lo / z hi / layer A, 32..63 robj lo / hi);
     1: compare planes (rows 0..31 terms 0..3, 32..63 terms 4..7, 64..95 AO, 96..127 sun / key share, 128..159 shaft beam / pool);
     2: GL5c packed planes for the room textures (0 roomT0, 1 roomT1, 2 roomA face / sun / sunn / ao, 3 roomB z lo / z hi / beam / pool, 4 roomK key light km) */
  vec2 fc = floor(gl_FragCoord.xy); float ix = fc.x, plane = floor(fc.y / 32.0), iy = fc.y - 32.0 * plane, U = uBlk.x * 32.0 + ix, V = uBlk.y * 32.0 + iy;
  if (uMode < 0.5) { float la = B(texture2D(bex, (vec2(ix, iy) + 0.5) / 32.0).b); vec3 vr = viewray(U, V, la); float zz = vr.y < 0.0 ? vr.y + 65536.0 : vr.y, ro = vr.z < 0.0 ? vr.z + 65536.0 : vr.z;
    gl_FragColor = plane < 0.5 ? vec4(vr.x, mod(zz, 256.0), floor(zz / 256.0), la) / 255.0 : vec4(mod(ro, 256.0), floor(ro / 256.0), gMH * gMB.x, gMH * gMB.y) / 255.0; return; }
  vec4 g0 = G(ix, iy), g1 = G(ix, iy + 32.0); float face = B(g0.r), z = S16(B(g0.g), B(g0.b)), la = B(g0.a), robj = S16(B(g1.r), B(g1.g));
  if (face > 19.5) { gN = octdec(vec2(B(g1.b), B(g1.a))); gMS = 1.0; }   /* LK_GLMODEL v1 */
  if (plane < 1.5) { gl_FragColor = face < 0.5 ? vec4(0.0) : termsP(plane, face, z, U, V) / 255.0; return; }
  if (uMode < 1.5) {
    if (plane < 2.5) { gl_FragColor = vec4(aoP(ix, iy, face, z) / 255.0, 0.0, 0.0, 0.0); return; }
    if (plane < 3.5) { gl_FragColor = vec4(sunP(uSd, 0.0, ix, iy, face, z, robj, la) / 255.0, 0.0, 0.0, 0.0); return; }
    vec2 bp = uNsh > 0.5 ? shafts(U, V, face, z) : vec2(0.0); gl_FragColor = vec4(bp.x / 255.0, bp.y / 255.0, 0.0, 0.0); return; }
  if (plane < 2.5) { float sv = sunP(uSd, 0.0, ix, iy, face, z, robj, la), svn = (uSunN > 0.5 && face > 0.5) ? sunP(uSdN, 1.0, ix, iy, face, z, robj, la) : 0.0;
    gl_FragColor = vec4(face > 19.5 ? fclassic(gN) : face, sv, svn, aoP(ix, iy, face, z)) / 255.0; return; }
  vec2 bp = uNsh > 0.5 ? shafts(U, V, face, z) : vec2(0.0);
  if (plane < 3.5) { float zz = z < 0.0 ? z + 65536.0 : z; gl_FragColor = vec4(mod(zz, 256.0), floor(zz / 256.0), bp.x, bp.y) / 255.0; return; }
  vec4 K = vec4(0.0);
  if (uKm > 0.5) { float u = sunP(uSd, 0.0, ix, iy, face, z, robj, la) / 255.0, a = aoP(ix, iy, face, z) / 255.0; vec3 f3 = vec3(uKA * 0.97 + uKK * u * 1.04, uKA * 0.99 + uKK * u, uKA * 1.05 + uKK * u * 0.92);
    if (bp.y > 0.0) { float pq = bp.y * (1.0 / 255.0) * 0.65; f3 += pq * uShc; }
    vec3 km = floor(min(f3 * a, vec3(2.4)) * 256.0 + 0.5);
    K = vec4(mod(km.r, 256.0), mod(km.g, 256.0), mod(km.b, 256.0), mod(floor(km.r / 256.0), 4.0) + 4.0 * mod(floor(km.g / 256.0), 4.0) + 16.0 * mod(floor(km.b / 256.0), 4.0)); }
  gl_FragColor = K / 255.0; }
'''

if VER not in s:
    MODULE = r'''/* ---- %s: GPU lighting harness (tools/patch_gpulight.py): offscreen light pass + compare with the CPU result ---- */
extern int lk_gl_getmode(void); extern int lk_gl_frame(long fr, float *fu, int *iu, float *lp, float *lc, float *lf, float *fg, float *fa); extern unsigned lk_gl_bver(int bx, int by); extern int lk_gl_bsg(int bx, int by);
extern void lk_gl_bpack(int bx, int by, uint32_t (*o)[1024]); extern void lk_gl_blist(int bx, int by, uint32_t *a, uint32_t *b2, int *nl); extern const uint16_t *lk_gl_fmk(void);
extern void lk_gl_pairs(float *o); extern void lk_gl_clstag(uint32_t *o); extern const uint32_t *lk_gl_am(void); extern void lk_gl_motes(uint32_t *o, int *bb); extern void lk_gl_amzd(uint32_t *o, int *bb);
extern uint32_t lk_gl_post[2][224 * 448]; extern int lk_gl_postany, lk_gl_postprev;
extern uint32_t lk_gl_unlit[224 * 448], lk_gl_ref[224 * 448]; extern uint8_t lk_gl_cls[224 * 448], lk_gl_flg[224 * 448]; extern uint32_t lk_gl_row[224];
LKGL_FN(void, glUniform3f, (lkGLint, lkGLfloat, lkGLfloat, lkGLfloat)); LKGL_FN(void, glUniform4f, (lkGLint, lkGLfloat, lkGLfloat, lkGLfloat, lkGLfloat)); LKGL_FN(void, glUniform4fv, (lkGLint, lkGLsizei, const lkGLfloat *));
LKGL_FN(void, glGenFramebuffers, (lkGLsizei, lkGLuint *)); LKGL_FN(void, glBindFramebuffer, (lkGLenum, lkGLuint)); LKGL_FN(void, glFramebufferTexture2D, (lkGLenum, lkGLenum, lkGLenum, lkGLuint, lkGLint)); LKGL_FN(lkGLenum, glCheckFramebufferStatus, (lkGLenum));
static int lk_glt_st;   /* 0 not tried, 1 ready, -1 failed */
LKGL_FN(void, glGenQueries, (lkGLsizei, lkGLuint *)); LKGL_FN(void, glBeginQuery, (lkGLenum, lkGLuint)); LKGL_FN(void, glEndQuery, (lkGLenum)); LKGL_FN(void, glGetQueryObjectiv, (lkGLuint, lkGLenum, lkGLint *)); LKGL_FN(void, glGetQueryObjectui64v, (lkGLuint, lkGLenum, unsigned long long *));
/* v5 GPU TIME WATCHDOG (user 2026-11-06: automatic fallback for weak GPUs): a timer query around the real light pass (2 queries, read one frame late);
   average over 120 frames above LANDSTALKER_GPULT_MAXMS (default 6 ms) in 2 windows in a row -> lk_gl_slow = 1 = CPU lighting for the rest of the run (console line).
   LANDSTALKER_GPULT_TIME=1 prints the average every 120 frames (test aid, cost budget of GL5).  No timer queries (old GL) = no watchdog. */
static lkGLuint lk_glt_q[2]; static int lk_glt_qst, lk_glt_qi, lk_glt_qpend[2], lk_glt_qn, lk_glt_qover; static double lk_glt_qsum, lk_glt_qmax = -1.0; static int lk_glt_qdbg = -1;
static void lk_glt_qinit(void) { *(void **)&lk_glGenQueries = lk_gpu_fn("glGenQueries"); *(void **)&lk_glBeginQuery = lk_gpu_fn("glBeginQuery"); *(void **)&lk_glEndQuery = lk_gpu_fn("glEndQuery");
  *(void **)&lk_glGetQueryObjectiv = lk_gpu_fn("glGetQueryObjectiv"); *(void **)&lk_glGetQueryObjectui64v = lk_gpu_fn("glGetQueryObjectui64v");
  if (!lk_glGetQueryObjectui64v) *(void **)&lk_glGetQueryObjectui64v = lk_gpu_fn("glGetQueryObjectui64vEXT");
  { const char *e = getenv("LANDSTALKER_GPULT_MAXMS"); lk_glt_qmax = e ? atof(e) : 6.0; } { const char *e = getenv("LANDSTALKER_GPULT_TIME"); lk_glt_qdbg = e ? atoi(e) : 0; }
  if (!lk_glGenQueries || !lk_glBeginQuery || !lk_glEndQuery || !lk_glGetQueryObjectiv || !lk_glGetQueryObjectui64v || !(SDL_GL_ExtensionSupported("GL_ARB_timer_query") || SDL_GL_ExtensionSupported("GL_EXT_timer_query"))) { lk_glt_qst = -1; printf("gpult: no timer queries, no GPU time watchdog\n"); return; }
  lk_glGenQueries(2, lk_glt_q); lk_glt_qst = 1; }
static void lk_glt_qresult(void) {   /* finished queries of both slots: add their time */
  extern int lk_gl_slow; int o; lkGLint av; unsigned long long ns;
  for (o = 0; o < 2; o++) { if (!lk_glt_qpend[o]) continue; av = 0; ns = 0;
    lk_glGetQueryObjectiv(lk_glt_q[o], 0x8867, &av); if (!av) continue;
    lk_glGetQueryObjectui64v(lk_glt_q[o], 0x8866, &ns); lk_glt_qpend[o] = 0; lk_glt_qsum += (double)ns * 1e-6; lk_glt_qn++; }
  if (lk_glt_qn < 120) return;
  { double avg = lk_glt_qsum / lk_glt_qn; lk_glt_qsum = 0.0; lk_glt_qn = 0;
    if (lk_glt_qdbg) printf("gpult: light pass %%.3f ms on the GPU (120 frame average)\n", avg);
    if (lk_glt_qmax > 0.0 && avg > lk_glt_qmax) { if (++lk_glt_qover >= 2) { lk_gl_slow = 1; printf("gpult: light pass too slow on this GPU (%%.2f ms > %%.2f ms), CPU lighting from now on\n", avg, lk_glt_qmax); } }
    else lk_glt_qover = 0; } }
#define LK_GLT_NT 16   /* textures of the pass: 0 unlit, 1 class + tag, 2 rows, 3 room A, 4 block table, 5 / 6 terms, 7 room B, 8 key light, 9 light lists, 10 mix after the light (448 x 448), 11 figure box mask, 12 pairs, 13 motes, 14 particles, 15 particle depths */
static lkGLuint lk_glt_prog, lk_glt_fbo, lk_glt_out, lk_glt_t[LK_GLT_NT]; static lkGLint lk_glt_u[64];
static unsigned lk_glt_ver[38][76]; static uint32_t lk_glt_ct[224 * 448]; static uint32_t lk_glt_mo[512 * 512], lk_glt_az[512 * 512]; static float lk_glt_pr[96 * 32 * 4];
static const char *lk_glt_fs = "#version 120\n" @SHADER@;
static const char *lk_glt_un[] = { "unl", "cls", "rows", "roomA", "btab", "roomT0", "roomT1", "roomB", "roomK", "bli", "post", "fmk", "pairs", "motes", "amap", "amzd",
  "uAmb", "uSS", "uSK", "uAmb3", "uSun3", "uMix", "uSun", "uNl", "uDn", "uOd0", "uKey", "uNsh", "uSwon", "uAm", "uKA", "uKK", "uFade", "uShc", "uSwP", "uSwC", "uNf", "uNfb", "uFall", "uE", "uSd", "uShA", "uShD",
  "uLP", "uLC", "uLF", "uFG", "uFA", "uPost", "uSwSh", 0 };
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
  lk_glt_t[0] = lk_glt_tex(448, 224, 0x1908, 0x80E1); lk_glt_t[1] = lk_glt_tex(448, 224, 0x1908, 0x1908); lk_glt_t[2] = lk_glt_tex(224, 1, 0x1908, 0x1908);
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
/* ---- v5 GL5a: the shadow terms of a light block on the GPU (flame terms with shadow, room light AO), compare only: LANDSTALKER_GL5CMP=1 ----
   Every block the light pass uploads (CPU values) is also computed by this pass from the block's geometry (face / z, already on the GPU) and the world (lk_gl_world),
   read back and compared.  Console every 300 frames with compared blocks: 'gl5: blocks .. terms exact/off1/worse .. ao exact/off1/worse ..' + the first 16 differences. */
extern unsigned lk_gl_world(uint32_t *w, uint32_t *w2, uint32_t *fn, uint32_t *px, uint32_t *f2, float *sc); extern void lk_gl_bextra(int bx, int by, uint32_t *o); extern int lk_gl_shafts(float *o); extern void lk_gl_wkey(unsigned *hard, unsigned *soft, float *dirs, int *sunn); extern void lk_gl_blist5(int bx, int by, uint32_t *a, uint32_t *b2, int *nl);
static int lk_g5_on = -1, lk_g5_st; static lkGLuint lk_g5_prog, lk_g5_fbo, lk_g5_out, lk_g5_wt, lk_g5_w2, lk_g5_fn, lk_g5_px, lk_g5_bx2, lk_g5_f2, lk_g5_geo; static lkGLint lk_g5_u[56];
LKGL_FN(void, glCopyTexSubImage2D, (lkGLenum, lkGLint, lkGLint, lkGLint, lkGLint, lkGLint, lkGLsizei, lkGLsizei)); LKGL_FN(void, glFinish, (void));
LKGL_FN(void, glGenBuffers, (lkGLsizei, lkGLuint *)); LKGL_FN(void, glBindBuffer, (lkGLenum, lkGLuint)); LKGL_FN(void, glBufferData, (lkGLenum, long, const void *, lkGLenum)); LKGL_FN(void *, glMapBuffer, (lkGLenum, lkGLenum)); LKGL_FN(lkGLboolean, glUnmapBuffer, (lkGLenum));
extern void lk_gl_surfput(int bx, int by, const uint32_t *A, const uint32_t *Bp, int sg); extern void lk_gl_surfswap(void); extern void lk_gl5_cpuset(void);
static lkGLuint lk_g5_pbo[2]; static int lk_g5_pbst, lk_g5_pbi, lk_g5_pbn[2], lk_g5_pbx[2][96], lk_g5_pby[2][96], lk_g5_pbsg[2], lk_g5_keep = -1;   /* v5 CPU saving: block planes back to the CPU, one frame late */
static void lk_g5_pbinit(void) { const char *e = getenv("LANDSTALKER_GL5_CPUKEEP"); lk_g5_keep = e ? atoi(e) : 0; lk_g5_pbst = -1;   /* test aid LANDSTALKER_GL5_CPUKEEP=1: the CPU keeps computing its blocks */
  *(void **)&lk_glGenBuffers = lk_gpu_fn("glGenBuffers"); *(void **)&lk_glBindBuffer = lk_gpu_fn("glBindBuffer"); *(void **)&lk_glBufferData = lk_gpu_fn("glBufferData"); *(void **)&lk_glMapBuffer = lk_gpu_fn("glMapBuffer"); *(void **)&lk_glUnmapBuffer = lk_gpu_fn("glUnmapBuffer");
  if (lk_g5_keep || !lk_glGenBuffers || !lk_glBindBuffer || !lk_glBufferData || !lk_glMapBuffer || !lk_glUnmapBuffer) return;
  lk_glGenBuffers(2, lk_g5_pbo); { int k; for (k = 0; k < 2; k++) { lk_glBindBuffer(0x88EB, lk_g5_pbo[k]); lk_glBufferData(0x88EB, 96L * 32 * 64 * 4, 0, 0x88E1); } } lk_glBindBuffer(0x88EB, 0);
  if (lk_glGetError()) { printf("gl5: no pixel buffers, the CPU keeps computing its light blocks\n"); return; } lk_g5_pbst = 1; }
static void lk_g5_pbdrain(void) { int k = lk_g5_pbi ^ 1, j; const uint32_t *m;   /* the buffer filled last frame: hand its blocks to the CPU side */
  if (lk_g5_pbst <= 0 || !lk_g5_pbn[k]) return;
  lk_glBindBuffer(0x88EB, lk_g5_pbo[k]); m = (const uint32_t *)lk_glMapBuffer(0x88EB, 0x88B8);
  if (m) { for (j = 0; j < lk_g5_pbn[k]; j++) lk_gl_surfput(lk_g5_pbx[k][j], lk_g5_pby[k][j], m + j * 2048, m + j * 2048 + 1024, lk_g5_pbsg[k]); lk_glUnmapBuffer(0x88EB); }
  lk_glBindBuffer(0x88EB, 0); lk_g5_pbn[k] = 0; } static unsigned lk_g5_wh;
#define LK_G5_Q 24
static int lk_g5_n, lk_g5_bx[LK_G5_Q], lk_g5_by[LK_G5_Q], lk_g5_nl[LK_G5_Q]; static uint32_t lk_g5_ref[LK_G5_Q][5][1024]; static int lk_g5_maxshow = 16, lk_g5_every = 300; static long lk_g5_cnt[6][3], lk_g5_blocks, lk_g5_frames, lk_g5_last; static int lk_g5_shown;
static const char *lk_g5_fs = "#version 120\n" @SHADER5@;
static const char *lk_g5_un[] = { "roomA", "roomB", "btab", "bli", "wld", "uLP", "uLC", "uBlk", "uSunR", "uAor", "uZref", "uAok", "uAotop", "uDv", "wld2", "fine", "prx", "bex", "uZtop", "uSd", "uKey", "uKbw", "uKpen", "uNsh", "uSh", "fine2", "uZmax", "uRayF", "geo", "uMode", "uSdN", "uSunN", "uKA", "uKK", "uShc", "uKm", "uSside", "uIfine", "uNslab", "uPineT", "uBushE", "mdl", "uMo", "uMdl", "uSm", "uE1", "uE2", "uSm2", "uE12", "uE22", "uSmo", "uSmSl", "uHand", "uAoflt", "uLF", "uSoftR", 0 };   /* 54 uLF: LK_GLWIDE v2 */
static int lk_g5_want(void) { if (lk_g5_on < 0) { const char *e = getenv("LANDSTALKER_GL5CMP"), *e2 = getenv("LANDSTALKER_GL5CMP_SHOW"), *e3 = getenv("LANDSTALKER_GL5CMP_EVERY"); lk_g5_on = e ? atoi(e) : 0; if (e2) lk_g5_maxshow = atoi(e2); if (e3 && atoi(e3) > 0) lk_g5_every = atoi(e3); } return lk_g5_on > 0 && lk_g5_st >= 0; }
/* ---- LK_GLMODEL v1 (REAL 3D LIGHT SHAPES stage 1, 2026-11-08, user: 'echte 3D-Formen brauchen wir doch fuers Remake ohnehin' + 'GPU-Weg'): at a new room world the room's model
   triangles (lk_gl_mlist: the Blender meshes of data/light_proxies.json) are rasterized once into a MODEL BUFFER in ROOM PICTURE space: orthographic along the view ray (1, 1, 1),
   U = x - y + 1184, V = (x + y) / 2 - z, depth = -z (nearest = highest z on a ray); per texel z * 8 + 32768 (r / g, 0 = no model) and the octahedral smooth normal (b / a).
   The block shader's view ray (indoors) takes that surface when it comes before any field hit; model owned sub columns show only the ground below the model.  Shadows / AO
   still use the fine field (stage 2: shadow maps).  No models / no FBO depth = old path. ---- */
extern int lk_gl_mlist(const float **tri, int *ntri, int max);
extern int lk_gl_mgenix, lk_gl_mobjix;   /* LK_GLROOM v1: index of the generated room model in lk_gl_mlist (-1 none); LK_GLOBJ v1: of the object meshes */
LKGL_FN(void, glClear, (lkGLenum)); LKGL_FN(void, glClearColor, (lkGLfloat, lkGLfloat, lkGLfloat, lkGLfloat)); LKGL_FN(void, glClearDepth, (double)); LKGL_FN(void, glNormalPointer, (lkGLenum, lkGLsizei, const void *));
LKGL_FN(void, glGenRenderbuffers, (lkGLsizei, lkGLuint *)); LKGL_FN(void, glBindRenderbuffer, (lkGLenum, lkGLuint)); LKGL_FN(void, glRenderbufferStorage, (lkGLenum, lkGLenum, lkGLsizei, lkGLsizei));
LKGL_FN(void, glFramebufferRenderbuffer, (lkGLenum, lkGLenum, lkGLenum, lkGLuint)); LKGL_FN(void, glDepthFunc, (lkGLenum)); LKGL_FN(void, glDepthMask, (lkGLboolean));
#define LK_GM_SZ 1024   /* one shadow map */
#define LK_GM_MB 2048   /* LK_GLROOM v1: the model buffer (whole rooms: up to ~1750 x 1100 picture pixels); texture 4096 x 2048 = model buffer | shadow map 0 | shadow map 1 (each 1024 x 1024) */
static float lk_gs_sdir[2][3], lk_gs_ssm[2][4], lk_gs_se1[2][3], lk_gs_se2[2][3]; static unsigned lk_gs_sgen[2] = { 0xFFFFFFFFu, 0xFFFFFFFFu }; static int lk_gs_slot[2] = { 0, 1 };   /* LK_GLOBJ v1: the two shadow map slots (direction + projection they hold) */
static int lk_gm_roomsm(void) { static int v = -1; if (v < 0) { const char *e = getenv("LANDSTALKER_LT_ROOMSM"); v = e ? atoi(e) : 0; } return v; }   /* LK_GLROOM v1 test aid */
static int lk_gm_st, lk_gm_on, lk_gm_dbg = -1; static lkGLuint lk_gm_prog, lk_gm_fbo, lk_gm_tex, lk_gm_rb; static lkGLint lk_gm_uo, lk_gm_ug, lk_gm_ub; static float lk_gm_mo[4];
/* stage 2 (key light SHADOW MAP, right half of the same texture): the models seen from the key light direction d (lk_lt_sd), orthographic, s = p . e1, t = p . e2, depth = p . d
   (nearest to the light kept), texels per unit uSm.z; redrawn when the room world or d changes.  LANDSTALKER_LT_MODELSM=0 = off (test aid: stage 1 only) */
static lkGLuint lk_gs_prog; static lkGLint lk_gs_u[4]; static float lk_gs_sm[4], lk_gs_e1[3], lk_gs_e2[3], lk_gs_sm2[4], lk_gs_e12[3], lk_gs_e22[3]; static int lk_gs_opt = -1;
static const char *lk_gs_vs = "#version 120\nuniform vec4 uSm; uniform vec3 uE1; uniform vec3 uE2; uniform vec3 uD; varying float vD;\n"
  "void main() { vec3 p = gl_Vertex.xyz; vD = dot(p, uD); vec2 c = (vec2(dot(p, uE1), dot(p, uE2)) - uSm.xy) * uSm.z;\n"
  "  gl_Position = vec4(c.x / 512.0 - 1.0, c.y / 512.0 - 1.0, -vD / 4096.0, 1.0); }\n";
static const char *lk_gs_fs = "#version 120\nvarying float vD; uniform float uSmB;\n"
  "void main() { if (uSmB > 0.5 && gl_FrontFacing == (uSmB < 1.5)) discard;   /* LK_GLROOM v1: back face shadow map (only the faces turned away from the light) */ float q = clamp(floor(vD * 8.0 + 32768.5), 1.0, 65535.0); gl_FragColor = vec4(mod(q, 256.0), floor(q / 256.0), 0.0, 0.0) / 255.0; }\n";
static const char *lk_gm_vs = "#version 120\nuniform vec4 uMo; varying vec3 vN; varying float vZ;\n"
  "void main() { vec3 p = gl_Vertex.xyz; float U = p.x - p.y + 1184.0, V = (p.x + p.y) * 0.5 - p.z; vN = gl_Normal; vZ = p.z;\n"
  "  gl_Position = vec4((U - uMo.x + 0.5) / uMo.z * 2.0 - 1.0, (V - uMo.y + 0.5) / uMo.w * 2.0 - 1.0, -p.z / 4096.0, 1.0); }\n";
static const char *lk_gm_fs = "#version 120\nvarying vec3 vN; varying float vZ; uniform float uGen; uniform float uBack;\n"
  "void main() { if (uGen > 0.5 && vN.x + vN.y + vN.z < -0.01) discard; if (uBack > 0.5 && dot(vN, vN) > 2.25) discard; vec3 n = normalize(vN);   /* LK_GLROOM v1: a generated room model's -x / -y walls (back faces) never in the model buffer: at box edges they won the depth tie */ n /= abs(n.x) + abs(n.y) + abs(n.z); vec2 e = n.xy;\n"
  "  if (n.z < 0.0) e = (1.0 - abs(n.yx)) * vec2(n.x >= 0.0 ? 1.0 : -1.0, n.y >= 0.0 ? 1.0 : -1.0);\n"
  "  e = floor((e * 0.5 + 0.5) * 255.0 + 0.5); float q = clamp(floor(vZ * 8.0 + 32768.5 + (uGen > 1.5 ? -16384.0 : uGen > 0.5 ? 16384.0 : 0.0)), 1.0, 65535.0);   /* LK_GLROOM v1: a generated room model = z * 8 + 49152 (hand-made models unchanged) */\n"
  "  gl_FragColor = vec4(mod(q, 256.0), floor(q / 256.0), e.x, e.y) / 255.0; }\n";
static int lk_gm_bindmesh(int i, const float *t, int ntri);
static lkGLuint lk_gm_vbo[16]; static const float *lk_gm_vp[16];
static int lk_gm_init(void) { lkGLint ok = 0, fb0 = 0, t0 = 0; lkGLuint vs, fs; char log[1024]; lkGLenum st;
  { const char *e = getenv("LANDSTALKER_GL5_MODELDBG"); lk_gm_dbg = e ? atoi(e) : 0; }
  *(void **)&lk_glClear = lk_gpu_fn("glClear"); *(void **)&lk_glClearColor = lk_gpu_fn("glClearColor"); *(void **)&lk_glClearDepth = lk_gpu_fn("glClearDepth"); *(void **)&lk_glNormalPointer = lk_gpu_fn("glNormalPointer");
  *(void **)&lk_glGenRenderbuffers = lk_gpu_fn("glGenRenderbuffers"); *(void **)&lk_glBindRenderbuffer = lk_gpu_fn("glBindRenderbuffer"); *(void **)&lk_glRenderbufferStorage = lk_gpu_fn("glRenderbufferStorage");
  *(void **)&lk_glFramebufferRenderbuffer = lk_gpu_fn("glFramebufferRenderbuffer"); *(void **)&lk_glDepthFunc = lk_gpu_fn("glDepthFunc"); *(void **)&lk_glDepthMask = lk_gpu_fn("glDepthMask");
  if (!lk_glClear || !lk_glClearColor || !lk_glClearDepth || !lk_glNormalPointer || !lk_glGenRenderbuffers || !lk_glBindRenderbuffer || !lk_glRenderbufferStorage || !lk_glFramebufferRenderbuffer || !lk_glDepthFunc || !lk_glDepthMask) { printf("gl5: model buffer: GL functions missing, real 3D light shapes off\n"); return -1; }
  vs = lk_glCreateShader(0x8B31); lk_glShaderSource(vs, 1, &lk_gm_vs, 0); lk_glCompileShader(vs); lk_glGetShaderiv(vs, 0x8B81, &ok);
  if (!ok) { lk_glGetShaderInfoLog(vs, sizeof log, 0, log); printf("gl5: model vertex shader failed: %%s\n", log); return -1; }
  fs = lk_glCreateShader(0x8B30); lk_glShaderSource(fs, 1, &lk_gm_fs, 0); lk_glCompileShader(fs); lk_glGetShaderiv(fs, 0x8B81, &ok);
  if (!ok) { lk_glGetShaderInfoLog(fs, sizeof log, 0, log); printf("gl5: model fragment shader failed: %%s\n", log); return -1; }
  lk_gm_prog = lk_glCreateProgram(); lk_glAttachShader(lk_gm_prog, vs); lk_glAttachShader(lk_gm_prog, fs); lk_glLinkProgram(lk_gm_prog); lk_glGetProgramiv(lk_gm_prog, 0x8B82, &ok);
  if (!ok) { lk_glGetProgramInfoLog(lk_gm_prog, sizeof log, 0, log); printf("gl5: model link failed: %%s\n", log); return -1; }
  lk_gm_uo = lk_glGetUniformLocation(lk_gm_prog, "uMo"); lk_gm_ug = lk_glGetUniformLocation(lk_gm_prog, "uGen"); lk_gm_ub = lk_glGetUniformLocation(lk_gm_prog, "uBack");
  { const char *e = getenv("LANDSTALKER_LT_MODELSM"); lk_gs_opt = e ? atoi(e) : 1; }
  if (lk_gs_opt) { lkGLuint v2 = lk_glCreateShader(0x8B31), f2 = lk_glCreateShader(0x8B30); lk_glShaderSource(v2, 1, &lk_gs_vs, 0); lk_glCompileShader(v2); lk_glShaderSource(f2, 1, &lk_gs_fs, 0); lk_glCompileShader(f2);
    lk_gs_prog = lk_glCreateProgram(); lk_glAttachShader(lk_gs_prog, v2); lk_glAttachShader(lk_gs_prog, f2); lk_glLinkProgram(lk_gs_prog); lk_glGetProgramiv(lk_gs_prog, 0x8B82, &ok);
    if (!ok) { lk_glGetProgramInfoLog(lk_gs_prog, sizeof log, 0, log); printf("gl5: shadow map program failed: %%s\n", log); lk_gs_opt = 0; }
    else { lk_gs_u[0] = lk_glGetUniformLocation(lk_gs_prog, "uSm"); lk_gs_u[1] = lk_glGetUniformLocation(lk_gs_prog, "uE1"); lk_gs_u[2] = lk_glGetUniformLocation(lk_gs_prog, "uE2"); lk_gs_u[3] = lk_glGetUniformLocation(lk_gs_prog, "uSmB"); } }
  lk_glGetIntegerv(0x8069, &t0); lk_gm_tex = lk_glt_tex(LK_GM_MB + 2 * LK_GM_SZ, LK_GM_MB, 0x1908, 0x1908); lk_glBindTexture(0x0DE1, (lkGLuint)t0);
  lk_glGenRenderbuffers(1, &lk_gm_rb); lk_glBindRenderbuffer(0x8D41, lk_gm_rb); lk_glRenderbufferStorage(0x8D41, 0x81A6, LK_GM_MB + 2 * LK_GM_SZ, LK_GM_MB); lk_glBindRenderbuffer(0x8D41, 0);   /* DEPTH_COMPONENT24 */
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glGenFramebuffers(1, &lk_gm_fbo); lk_glBindFramebuffer(0x8D40, lk_gm_fbo); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_gm_tex, 0);
  lk_glFramebufferRenderbuffer(0x8D40, 0x8D00, 0x8D41, lk_gm_rb); st = lk_glCheckFramebufferStatus(0x8D40); lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0);
  if (st != 0x8CD5) { printf("gl5: model buffer framebuffer incomplete %%04X, real 3D light shapes off\n", (unsigned)st); return -1; }
  { static const float wt[18] = { 0, 0, 0, 0, 0, 1,  1, 0, 0, 0, 0, 1,  0, 1, 0, 0, 0, 1 }; lkGLint fb1 = 0, vp1[4], pr1 = 0; int dt1 = lk_glIsEnabled(0x0B71), va1 = lk_glIsEnabled(0x8074), na1 = lk_glIsEnabled(0x8075);   /* LK_GLOBJ v1 WARM-UP: one tiny triangle with
      both model programs at start-up, so the driver finishes compiling them now and not in the first room with a shadow map (31 ms hitch after the file select, user 2026-11-09) */
    lk_glGetIntegerv(0x8CA6, &fb1); lk_glGetIntegerv(0x0BA2, vp1); lk_glGetIntegerv(0x8B8D, &pr1); lk_glBindFramebuffer(0x8D40, lk_gm_fbo); lk_glViewport(0, 0, 4, 4);
    lk_glEnable(0x0B71); lk_glDepthFunc(0x0201); lk_glDepthMask(1); lk_glEnableClientState(0x8074); lk_glEnableClientState(0x8075); lk_glVertexPointer(3, 0x1406, 24, wt); lk_glNormalPointer(0x1406, 24, wt + 3);
    lk_glUseProgram(lk_gm_prog); lk_glDrawArrays(0x0004, 0, 3);   /* client arrays, then the same from a vertex buffer (the real passes use buffers: lk_gm_bindmesh) */
    if (lk_gm_bindmesh(15, wt, 1)) { lk_glVertexPointer(3, 0x1406, 24, (const void *)0); lk_glNormalPointer(0x1406, 24, (const void *)12); lk_glDrawArrays(0x0004, 0, 3); }
    if (lk_gs_opt > 0) { lk_glUseProgram(lk_gs_prog); lk_glUniform1f(lk_gs_u[3], 1.0f); lk_glDisableClientState(0x8075);   /* the shadow pass: normals off, as in lk_gm_render */
      lk_glDrawArrays(0x0004, 0, 3); lk_glEnable(0x0C11); lk_glScissor(0, 0, 4, 4); lk_glClear(0x4100); lk_glDisable(0x0C11); lk_glDrawArrays(0x0004, 0, 3); lk_glEnableClientState(0x8075); }
    if (lk_glBindBuffer) lk_glBindBuffer(0x8892, 0); lk_gm_vp[15] = 0;
    if (lk_glFinish) lk_glFinish();
    if (!na1) lk_glDisableClientState(0x8075); if (!va1) lk_glDisableClientState(0x8074); if (!dt1) lk_glDisable(0x0B71);
    lk_glClearColor(0.0f, 0.0f, 0.0f, 0.0f); lk_glClearDepth(1.0); lk_glClear(0x4100);
    lk_glUseProgram((lkGLuint)pr1); lk_glViewport(vp1[0], vp1[1], vp1[2], vp1[3]); lk_glBindFramebuffer(0x8D40, (lkGLuint)fb1); }
  printf("gl5: model buffer ready (real 3D light shapes)\n"); return 1; }
static int lk_gm_vn[16]; static unsigned lk_gm_vg[16];
static const float *lk_gm_bp[16]; static int lk_gm_bn[16]; static unsigned lk_gm_bg[16]; static float lk_gm_bb[16][6];
static const float *lk_gm_box(int i, const float *t, int ntri) {   /* LK_GLOBJ v1: a mesh's bounding box, once per room (the shadow map extent from 8 corners, not from every vertex) */
  extern unsigned lk_lt_mgen; int j;
  if (lk_gm_bp[i] != t || lk_gm_bn[i] != ntri || lk_gm_bg[i] != lk_lt_mgen) { float *b = lk_gm_bb[i]; b[0] = b[1] = b[2] = 1e9f; b[3] = b[4] = b[5] = -1e9f;
    for (j = 0; j < 3 * ntri; j++) { const float *v = t + 6 * j; int c; for (c = 0; c < 3; c++) { if (v[c] < b[c]) b[c] = v[c]; if (v[c] > b[3 + c]) b[3 + c] = v[c]; } }
    lk_gm_bp[i] = t; lk_gm_bn[i] = ntri; lk_gm_bg[i] = lk_lt_mgen; }
  return lk_gm_bb[i]; }
static int lk_gm_bindmesh(int i, const float *t, int ntri) {   /* LK_GLOBJ v1: each mesh once per room in a GPU vertex buffer (dense forests: 200000+ triangles, drawn 3 times: model buffer + 2 shadow maps) */
  extern unsigned lk_lt_mgen;
  if (!lk_glGenBuffers) { *(void **)&lk_glGenBuffers = lk_gpu_fn("glGenBuffers"); *(void **)&lk_glBindBuffer = lk_gpu_fn("glBindBuffer"); *(void **)&lk_glBufferData = lk_gpu_fn("glBufferData"); }
  if (!lk_glGenBuffers || !lk_glBindBuffer || !lk_glBufferData || i < 0 || i >= 16) return 0;
  if (!lk_gm_vbo[i]) lk_glGenBuffers(1, &lk_gm_vbo[i]);
  lk_glBindBuffer(0x8892, lk_gm_vbo[i]);
  if (lk_gm_vp[i] != t || lk_gm_vn[i] != ntri || lk_gm_vg[i] != lk_lt_mgen) { lk_glBufferData(0x8892, (long)ntri * 72L, t, 0x88E4); lk_gm_vp[i] = t; lk_gm_vn[i] = ntri; lk_gm_vg[i] = lk_lt_mgen; }
  return 1; }
static void lk_gm_render(const float *sc, int smonly) {   /* smonly (LK_GLOBJ v1): a new key / sun direction redraws the shadow maps only (the model buffer stays) */   /* at a new room world / key direction (lk_g5_bind): the room's models into the model buffer + the key light shadow map */
  const float *tri[16]; int nt[16], n, i, j, ntot = 0; float u0 = 1e9f, v0 = 1e9f, u1 = -1e9f, v1 = -1e9f, W, H, cc[4]; lkGLint fb0 = 0, vp[4], prog0 = 0; int bl, sci, dt, cu, va, na;
  lk_gm_on = 0; lk_gs_sm[3] = 0.0f; lk_gs_sm2[3] = 0.0f; if (lk_gm_st <= 0) return;
  n = lk_gl_mlist(tri, nt, 16); if (!n) return;
  if (lk_gm_dbg) { extern void lk_gm_t0(void); if (lk_glFinish) lk_glFinish(); lk_gm_t0(); }   /* LK_GLROOM v1 load time check: earlier GPU work finished first (debug only) */
  for (i = 0; i < n; i++) for (j = 0; j < 3 * nt[i]; j++) { const float *v = tri[i] + 6 * j; float U = v[0] - v[1] + 1184.0f, V = (v[0] + v[1]) * 0.5f - v[2];
      if (U < u0) u0 = U; if (U > u1) u1 = U; if (V < v0) v0 = V; if (V > v1) v1 = V; }
  for (i = 0; i < n; i++) ntot += nt[i];
  u0 = floorf(u0) - 2.0f; v0 = floorf(v0) - 2.0f; W = ceilf(u1) + 3.0f - u0; H = ceilf(v1) + 3.0f - v0;
  if (W > LK_GM_MB || H > LK_GM_MB) { printf("gl5: model buffer too small for this room (%%.0f x %%.0f), real 3D light shapes off here\n", W, H); return; }
  lk_gm_mo[0] = u0; lk_gm_mo[1] = v0; lk_gm_mo[2] = W; lk_gm_mo[3] = H;
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glGetIntegerv(0x0BA2, vp); lk_glGetFloatv(0x0C22, cc); lk_glGetIntegerv(0x8B8D, &prog0);
  bl = lk_glIsEnabled(0x0BE2); sci = lk_glIsEnabled(0x0C11); dt = lk_glIsEnabled(0x0B71); cu = lk_glIsEnabled(0x0B44); va = lk_glIsEnabled(0x8074); na = lk_glIsEnabled(0x8075);
  lk_glBindFramebuffer(0x8D40, lk_gm_fbo); lk_glViewport(0, 0, (lkGLsizei)W, (lkGLsizei)H);
  lk_glDisable(0x0BE2); lk_glDisable(0x0C11); lk_glDisable(0x0B44); lk_glEnable(0x0B71); lk_glDepthFunc(0x0201); lk_glDepthMask(1);
  lk_glClearColor(0.0f, 0.0f, 0.0f, 0.0f); lk_glClearDepth(1.0);
  if (!smonly) { lk_glClear(0x4100); lk_gs_sgen[0] = lk_gs_sgen[1] = 0xFFFFFFFFu; }   /* a new room world: both shadow map slots are stale */
  lk_glUseProgram(lk_gm_prog); lk_glUniform4f(lk_gm_uo, u0, v0, W, H);
  lk_glEnableClientState(0x8074); lk_glEnableClientState(0x8075);
  for (i = 0; i < n && !smonly; i++) { static int mb = -1; if (mb < 0) { const char *e = getenv("LANDSTALKER_LT_MBACK"); mb = e ? atoi(e) : 0; }
    lk_glUniform1f(lk_gm_ub, mb && i != lk_gl_mgenix ? 1.0f : 0.0f);   /* test aid LANDSTALKER_LT_MBACK=1: a hand model's camera-averted triangles out of the model buffer */
    lk_glUniform1f(lk_gm_ug, i == lk_gl_mgenix ? 1.0f : i == lk_gl_mobjix ? 2.0f : 0.0f);   /* 2 = trees / bushes (LK_GLOBJ v1) */
    if (lk_gm_bindmesh(i, tri[i], nt[i])) { lk_glVertexPointer(3, 0x1406, 24, (const void *)0); lk_glNormalPointer(0x1406, 24, (const void *)12); } else { lk_glVertexPointer(3, 0x1406, 24, tri[i]); lk_glNormalPointer(0x1406, 24, tri[i] + 3); }
    lk_glDrawArrays(0x0004, 0, 3 * nt[i]); }
  if (lk_glBindBuffer) lk_glBindBuffer(0x8892, 0);
  if (lk_gm_dbg) { extern double lk_gm_ms(void); if (lk_glFinish) lk_glFinish(); printf("gl5: model pass done %%.2f ms\n", lk_gm_ms()); }
  { int hs; lk_gs_sm2[3] = 0.0f; for (hs = 0; hs < 2 && lk_gs_opt > 0; hs++) { float d[3], l, e1[3], e2[3], s0 = 1e9f, s1 = -1e9f, t0 = 1e9f, t1 = -1e9f, k, *SM = hs ? lk_gs_sm2 : lk_gs_sm;   /* stage 2: shadow maps (key light / sun, next sun step) */
    if (n == 1 && lk_gl_mgenix == 0 && !lk_gm_roomsm()) continue;   /* LK_GLROOM v1: only the generated room model: no shadow map (test aid LANDSTALKER_LT_ROOMSM=1: the boxes in the shadow maps too) */
    if (hs == 0 && !(sc[9] > 0.5f || sc[0] > 0.5f)) continue; if (hs == 1 && !(sc[0] > 0.5f && sc[17] > 0.5f)) continue;
    d[0] = hs ? sc[14] : sc[6]; d[1] = hs ? sc[15] : sc[7]; d[2] = hs ? sc[16] : sc[8]; l = sqrtf(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]); if (l < 1e-3f || d[2] <= 0.02f * l) continue;
    d[0] /= l; d[1] /= l; d[2] /= l; e1[0] = -d[1]; e1[1] = d[0]; e1[2] = 0.0f; l = sqrtf(e1[0] * e1[0] + e1[1] * e1[1]); if (l < 1e-3f) { e1[0] = 1.0f; e1[1] = 0.0f; l = 1.0f; } e1[0] /= l; e1[1] /= l;
    e2[0] = d[1] * e1[2] - d[2] * e1[1]; e2[1] = d[2] * e1[0] - d[0] * e1[2]; e2[2] = d[0] * e1[1] - d[1] * e1[0];
    for (i = 0; i < n; i++) if ((i != lk_gl_mgenix || lk_gm_roomsm()) && i < 16) for (j = 0; j < 8; j++) { const float *B0 = lk_gm_box(i, tri[i], nt[i]); float v[3] = { B0[(j & 1) ? 3 : 0], B0[(j & 2) ? 4 : 1], B0[(j & 4) ? 5 : 2] }; float a = v[0] * e1[0] + v[1] * e1[1] + v[2] * e1[2], b = v[0] * e2[0] + v[1] * e2[1] + v[2] * e2[2];
        if (a < s0) s0 = a; if (a > s1) s1 = a; if (b < t0) t0 = b; if (b > t1) t1 = b; }
    s0 -= 16.0f; t0 -= 16.0f; s1 += 16.0f; t1 += 16.0f; k = 1000.0f / (s1 - s0 > t1 - t0 ? s1 - s0 : t1 - t0); if (k > 4.0f) k = 4.0f;
    SM[0] = s0; SM[1] = t0; SM[2] = k; SM[3] = lk_gm_roomsm() && lk_gl_mgenix >= 0 ? 2.0f : 1.0f;   /* 2 = the room boxes are in it (the marches leave them out) */ memcpy(hs ? lk_gs_e12 : lk_gs_e1, e1, sizeof e1); memcpy(hs ? lk_gs_e22 : lk_gs_e2, e2, sizeof e2);
    { extern unsigned lk_lt_mgen; int sl, hit = -1; for (sl = 0; sl < 2; sl++) if (lk_gs_sgen[sl] == lk_lt_mgen && !memcmp(lk_gs_sdir[sl], d, sizeof lk_gs_sdir[sl]) && !memcmp(lk_gs_ssm[sl], SM, sizeof lk_gs_ssm[sl])) hit = sl;   /* LK_GLOBJ v1: a sun step: the new 'current'
           map is the old 'next' one -> reuse its slot, draw only the new one */
      if (hit >= 0) { lk_gs_slot[hs] = hit; if (lk_gm_dbg) printf("gl5: shadow map %%d reused from slot %%d\n", hs, hit); continue; }
      sl = hs == 1 && lk_gs_sm[3] > 0.5f ? 1 - lk_gs_slot[0] : (lk_gs_sgen[0] == lk_lt_mgen && lk_gs_sgen[1] != lk_lt_mgen ? 1 : 0);
      if (hs == 0 && sc[0] > 0.5f && sc[17] > 0.5f) { int o2; for (o2 = 0; o2 < 2; o2++) { float dn[3] = { sc[14], sc[15], sc[16] }; float ln = sqrtf(dn[0] * dn[0] + dn[1] * dn[1] + dn[2] * dn[2]); if (ln > 1e-3f) { dn[0] /= ln; dn[1] /= ln; dn[2] /= ln; } if (lk_gs_sgen[o2] == lk_lt_mgen && !memcmp(lk_gs_sdir[o2], dn, sizeof dn)) sl = 1 - o2; } }   /* keep the slot of the next direction */
      lk_gs_slot[hs] = sl; memcpy(lk_gs_sdir[sl], d, sizeof d); memcpy(lk_gs_ssm[sl], SM, sizeof lk_gs_ssm[sl]); lk_gs_sgen[sl] = lk_lt_mgen;
      { lkGLint box[4]; lk_glGetIntegerv(0x0C10, box); lk_glEnable(0x0C11); lk_glScissor(LK_GM_MB + LK_GM_SZ * sl, 0, LK_GM_SZ, LK_GM_SZ); lk_glClear(0x4100); lk_glScissor(box[0], box[1], box[2], box[3]); lk_glDisable(0x0C11); } }
    lk_glViewport(LK_GM_MB + LK_GM_SZ * lk_gs_slot[hs], 0, LK_GM_SZ, LK_GM_SZ); lk_glUseProgram(lk_gs_prog); lk_glUniform4f(lk_gs_u[0], s0, t0, k, 1.0f); lk_glUniform3f(lk_gs_u[1], e1[0], e1[1], e1[2]); lk_glUniform3f(lk_gs_u[2], e2[0], e2[1], e2[2]);
    lk_glUniform3f(lk_glGetUniformLocation(lk_gs_prog, "uD"), d[0], d[1], d[2]); lk_glDisableClientState(0x8075);
    { static int sb = -1; if (sb < 0) { const char *e = getenv("LANDSTALKER_LT_SMBACK"); sb = e ? atoi(e) : 1; } lk_glUniform1f(lk_gs_u[3], (float)sb); }   /* LK_GLROOM v1 BACK FACE SHADOW MAPS (2026-11-08): only the triangles turned AWAY from the light;
      a lit face can no longer shadow itself at an edge (the PCF taps caught the neighbouring face: dark lines along every wall corner of a hand-made model, church 632 corner 89 -> 208);
      needs outward counter-clockwise triangles (Blender meshes: checked; the room model: lk_lt_rmquad).  LANDSTALKER_LT_SMBACK=0 = old (all triangles), 2 = only the light-facing ones (test) */
    for (i = 0; i < n; i++) if (i != lk_gl_mgenix || lk_gm_roomsm()) { if (lk_gm_bindmesh(i, tri[i], nt[i])) lk_glVertexPointer(3, 0x1406, 24, (const void *)0); else lk_glVertexPointer(3, 0x1406, 24, tri[i]); lk_glDrawArrays(0x0004, 0, 3 * nt[i]); }
    if (lk_glBindBuffer) lk_glBindBuffer(0x8892, 0);   /* LK_GLROOM v1: the generated box model casts through the field march (the same boxes, exact + soft; a shadow map gave PCF lines at every box edge) */
    lk_glEnableClientState(0x8075);
    if (lk_gm_dbg) { extern double lk_gm_ms(void); if (lk_glFinish) lk_glFinish(); printf("gl5: shadow map %%d: s %%.0f..%%.0f t %%.0f..%%.0f, %%.2f texels per unit, d %%.2f %%.2f %%.2f (done %%.2f ms)\n", hs, s0, s1, t0, t1, k, d[0], d[1], d[2], lk_gm_ms()); } } }
  if (!na) lk_glDisableClientState(0x8075); if (!va) lk_glDisableClientState(0x8074);
  if (!dt) lk_glDisable(0x0B71); if (bl) lk_glEnable(0x0BE2); if (sci) lk_glEnable(0x0C11); if (cu) lk_glEnable(0x0B44);
  lk_glClearColor(cc[0], cc[1], cc[2], cc[3]); lk_glViewport(vp[0], vp[1], vp[2], vp[3]); lk_glUseProgram((lkGLuint)prog0); lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0);
  if (lk_gm_dbg) { extern double lk_gm_ms(void); if (lk_glFinish) lk_glFinish(); printf("gl5: model buffer + shadow maps drawn in %%.2f ms\n", lk_gm_ms()); }   /* before the debug read back */
  if (lk_gm_dbg) { static uint32_t rb[LK_GM_MB * 4]; int hit = 0, k; lk_glBindFramebuffer(0x8D40, lk_gm_fbo); lk_glPixelStorei(0x0D05, 4);
    for (k = 0; k < (int)H; k++) { int x; lk_glReadPixels(0, k, (lkGLsizei)W, 1, 0x1908, 0x1401, rb); for (x = 0; x < (int)W; x++) if (rb[x] & 0xFFFF) hit++; }
    lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); printf("gl5: model buffer: %%d meshes, %%d triangles, U %%.0f.. V %%.0f.. (%%.0f x %%.0f), %%d texels hit\n", n, ntot, u0, v0, W, H, hit); }
  lk_gm_on = 1; }
static int lk_g5_init(void) {
  lkGLint ok = 0, t0 = 0, fb0 = 0; lkGLuint vs, fs; char log[2048]; int i; lkGLenum st;
  { static const char *vsrc = "#version 120\nvoid main() { gl_Position = gl_Vertex; }\n"; vs = lk_glCreateShader(0x8B31); lk_glShaderSource(vs, 1, &vsrc, 0); lk_glCompileShader(vs); lk_glGetShaderiv(vs, 0x8B81, &ok); if (!ok) return -1; }
  fs = lk_glCreateShader(0x8B30); lk_glShaderSource(fs, 1, &lk_g5_fs, 0); lk_glCompileShader(fs); lk_glGetShaderiv(fs, 0x8B81, &ok);
  if (!ok) { lk_glGetShaderInfoLog(fs, sizeof log, 0, log); printf("gl5: term shader failed: %%s\n", log); return -1; }
  lk_g5_prog = lk_glCreateProgram(); lk_glAttachShader(lk_g5_prog, vs); lk_glAttachShader(lk_g5_prog, fs); lk_glLinkProgram(lk_g5_prog); lk_glGetProgramiv(lk_g5_prog, 0x8B82, &ok);
  if (!ok) { lk_glGetProgramInfoLog(lk_g5_prog, sizeof log, 0, log); printf("gl5: link failed: %%s\n", log); return -1; }
  for (i = 0; lk_g5_un[i]; i++) lk_g5_u[i] = lk_glGetUniformLocation(lk_g5_prog, lk_g5_un[i]);
  lk_glGetIntegerv(0x8069, &t0);
  lk_g5_out = lk_glt_tex(32, 224, 0x1908, 0x1908); lk_g5_f2 = lk_glt_tex(296, 296, 0x1908, 0x1908); lk_g5_wt = lk_glt_tex(74, 222, 0x1908, 0x1908); lk_g5_geo = lk_glt_tex(32, 64, 0x1908, 0x1908);
  *(void **)&lk_glCopyTexSubImage2D = lk_gpu_fn("glCopyTexSubImage2D"); if (!lk_glCopyTexSubImage2D) { printf("gl5: glCopyTexSubImage2D missing\n"); return -1; } *(void **)&lk_glFinish = lk_gpu_fn("glFinish"); lk_g5_w2 = lk_glt_tex(74, 222, 0x1908, 0x1908); lk_g5_fn = lk_glt_tex(296, 1480, 0x1908, 0x1908);
  lk_g5_px = lk_glt_tex(26, 255, 0x1908, 0x1908); lk_g5_bx2 = lk_glt_tex(32, 32, 0x1908, 0x1908);
  lk_glBindTexture(0x0DE1, (lkGLuint)t0);
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glGenFramebuffers(1, &lk_g5_fbo); lk_glBindFramebuffer(0x8D40, lk_g5_fbo); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_g5_out, 0);
  st = lk_glCheckFramebufferStatus(0x8D40); lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); if (st != 0x8CD5) { printf("gl5: framebuffer incomplete %%04X\n", (unsigned)st); return -1; }
  lk_gm_st = lk_gm_init();
  printf("gl5: GPU light block pass ready\n"); return 1; }
static void lk_g5_queue(int bx, int by, uint32_t (*pk)[1024]) { int i, nl; uint32_t a, b2;   /* inside the upload loop: the CPU values of a block just uploaded */
  if (lk_g5_n >= LK_G5_Q) return;
  lk_gl_blist(bx, by, &a, &b2, &nl); lk_g5_bx[lk_g5_n] = bx; lk_g5_by[lk_g5_n] = by; lk_g5_nl[lk_g5_n] = nl;
  for (i = 0; i < 1024; i++) { lk_g5_ref[lk_g5_n][0][i] = pk[1][i]; lk_g5_ref[lk_g5_n][1][i] = pk[2][i]; lk_g5_ref[lk_g5_n][2][i] = (pk[0][i] >> 24) | ((pk[0][i] & 255) << 8) | ((pk[3][i] & 0xFFFF) << 16); }
  for (i = 0; i < 1024; i++) lk_g5_ref[lk_g5_n][4][i] = pk[3][i] >> 16;   /* beam | pool << 8 */
  lk_gl_bextra(bx, by, lk_g5_ref[lk_g5_n][3]); for (i = 0; i < 1024; i++) lk_g5_ref[lk_g5_n][3][i] = (lk_g5_ref[lk_g5_n][3][i] & 0x1FFFFu) | (((pk[0][i] >> 8) & 255) << 24);   /* robj | layer A << 16 | CPU sun share << 24 */
  lk_g5_n++; }
static float lk_g5_sc[32];
static const float *lk_g5_lf;   /* LK_GLWIDE v2: the frame's per light extras (uLF: flicker, lava, fire half width, along) */
static int lk_g5_bind(const float *lp, const float *lc, int fresh) {   /* program, textures and uniforms of the block pass (units 0 / 1 / 2 / 5 / 6 / 8 / 10 = world / sun heights / object field / proxies / layer A / view fields / geometry; 4 / 9 = block table / lists) */
  static uint32_t w[5476 * 3], w2[5476 * 3], fnb[296 * 1480], pxb[26 * 255], f2b[296 * 296]; float dv[32], shf[36]; unsigned h; int k; float *sc = lk_g5_sc;
  if (lk_g5_st == 0) lk_g5_st = lk_g5_init();
  if (lk_g5_st < 0) return 0;
  if (fresh) { h = lk_gl_world(w, w2, fnb, pxb, f2b, sc);
    if (h != lk_g5_wh) { lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_g5_wt); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 74, 222, 0x1908, 0x1401, w);
      lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, lk_g5_w2); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 74, 222, 0x1908, 0x1401, w2);
      lk_glActiveTexture(0x84C2); lk_glBindTexture(0x0DE1, lk_g5_fn); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 296, 1480, 0x1908, 0x1401, fnb);
      lk_glActiveTexture(0x84C5); lk_glBindTexture(0x0DE1, lk_g5_px); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 26, 255, 0x1908, 0x1401, pxb);
      lk_glActiveTexture(0x84C8); lk_glBindTexture(0x0DE1, lk_g5_f2); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 296, 296, 0x1908, 0x1401, f2b); lk_g5_wh = h;
      lk_gm_render(sc, 0); } }   /* LK_GLMODEL v1 */
  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_g5_wt); lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, lk_g5_w2); lk_glActiveTexture(0x84C2); lk_glBindTexture(0x0DE1, lk_g5_fn);
  lk_glActiveTexture(0x84C5); lk_glBindTexture(0x0DE1, lk_g5_px); lk_glActiveTexture(0x84C6); lk_glBindTexture(0x0DE1, lk_g5_bx2); lk_glActiveTexture(0x84C8); lk_glBindTexture(0x0DE1, lk_g5_f2);
  lk_glActiveTexture(0x84CA); lk_glBindTexture(0x0DE1, lk_g5_geo);
  if (lk_gm_st > 0) { lk_glActiveTexture(0x84CB); lk_glBindTexture(0x0DE1, lk_gm_tex); }   /* LK_GLMODEL v1 */
  lk_glActiveTexture(0x84C4); lk_glBindTexture(0x0DE1, lk_glt_t[4]); lk_glActiveTexture(0x84C9); lk_glBindTexture(0x0DE1, lk_glt_t[9]); lk_glActiveTexture(0x84C0);
  for (k = 0; k < 16; k++) { float a = (float)k * 0.39269908f; dv[2 * k] = cosf(a); dv[2 * k + 1] = sinf(a); }   /* the directions of lk_lt_aoval (same libm) */
  lk_glUseProgram(lk_g5_prog);
  lk_glUniform1i(lk_g5_u[2], 4); lk_glUniform1i(lk_g5_u[3], 9); lk_glUniform1i(lk_g5_u[4], 0);
  lk_glUniform4fv(lk_g5_u[5], 96, lp); lk_glUniform4fv(lk_g5_u[6], 96, lc); if (lk_g5_lf) lk_glUniform4fv(lk_g5_u[54], 96, lk_g5_lf); { static int sr = -1; if (sr < 0) { const char *e = getenv("LANDSTALKER_LT_SOFTR"); sr = e ? atoi(e) != 0 : 0; } lk_glUniform1f(lk_g5_u[55], (float)sr); }   /* LK_GLSOFTR v1 */   /* LK_GLWIDE v2 */
  { extern int lk_lt_sside_get(void); lk_glUniform1f(lk_g5_u[36], lk_lt_sside_get() ? 1.0f : 0.0f); } lk_glUniform1f(lk_g5_u[37], sc[24]); lk_glUniform1f(lk_g5_u[38], sc[25]); lk_glUniform1f(lk_g5_u[39], sc[26]); lk_glUniform1f(lk_g5_u[40], sc[27]); lk_glUniform1f(lk_g5_u[8], sc[0]); lk_glUniform1f(lk_g5_u[9], sc[1]); lk_glUniform1f(lk_g5_u[10], sc[2]); lk_glUniform1f(lk_g5_u[11], sc[3]); lk_glUniform1f(lk_g5_u[12], sc[4]);
  { static float pd[7]; if (lk_gm_on && lk_gs_opt > 0 && (sc[6] != pd[0] || sc[7] != pd[1] || sc[8] != pd[2] || sc[14] != pd[3] || sc[15] != pd[4] || sc[16] != pd[5] || sc[17] != pd[6])) {
      pd[0] = sc[6]; pd[1] = sc[7]; pd[2] = sc[8]; pd[3] = sc[14]; pd[4] = sc[15]; pd[5] = sc[16]; pd[6] = sc[17]; lk_gm_render(sc, 1); lk_glUseProgram(lk_g5_prog); } }   /* stage 2: a new key / sun direction */
  lk_glUniform2f(lk_g5_u[51], (float)lk_gs_slot[0], (float)lk_gs_slot[1]);   /* LK_GLOBJ v1 */ lk_glUniform1f(lk_g5_u[52], sc[28]);
  { static int af = -1; if (af < 0) { const char *e = getenv("LANDSTALKER_LT_AOFLT"); af = e ? atoi(e) : 2; if (af < 0 || af > 2) af = 2; } { static float ck = -1.0f; if (ck < 0.0f) { const char *e = getenv("LANDSTALKER_LT_AOCOV"); ck = e ? (float)atof(e) : 0.75f; if (ck < 0.0f || ck > 1.0f) ck = 0.75f; } lk_glUniform1f(lk_g5_u[53], af == 2 ? 2.0f + ck : (float)af); } }   /* LK_GLAOFLT v2: floating model parts cover the AO (2 = Lambert share under the part, 1 = v1 linear share, 0 = old: air) */
  lk_glUniform4f(lk_g5_u[44], lk_gs_sm[0], lk_gs_sm[1], lk_gs_sm[2], lk_gs_sm[3]); lk_glUniform3f(lk_g5_u[45], lk_gs_e1[0], lk_gs_e1[1], lk_gs_e1[2]); lk_glUniform3f(lk_g5_u[46], lk_gs_e2[0], lk_gs_e2[1], lk_gs_e2[2]);
  lk_glUniform4f(lk_g5_u[47], lk_gs_sm2[0], lk_gs_sm2[1], lk_gs_sm2[2], lk_gs_sm2[3]); lk_glUniform3f(lk_g5_u[48], lk_gs_e12[0], lk_gs_e12[1], lk_gs_e12[2]); lk_glUniform3f(lk_g5_u[49], lk_gs_e22[0], lk_gs_e22[1], lk_gs_e22[2]);
  { static float so[4] = { -1.0f }; if (so[0] < -0.5f) { const char *e = getenv("LANDSTALKER_LT_SMO"); so[0] = 0.0f; so[1] = 0.75f; so[2] = 1.5f; so[3] = 0.0f; if (e) sscanf(e, "%%f,%%f,%%f", &so[0], &so[1], &so[2]); }
    lk_glUniform4f(lk_g5_u[50], so[0], so[1], so[2], so[3]); }   /* LK_GLROOM v1: shadow map filter tunables (test aid LANDSTALKER_LT_SMO=offset,minwidth,bias) */
  lk_glUniform1i(lk_g5_u[41], 11); lk_glUniform4f(lk_g5_u[42], lk_gm_mo[0], lk_gm_mo[1], lk_gm_mo[2], lk_gm_mo[3]); lk_glUniform1f(lk_g5_u[43], lk_gm_on ? (lk_gm_dbg == 20 ? 1.25f : lk_gm_dbg >= 3 ? (float)(lk_gm_dbg - 1) : 1.0f) : 0.0f);   /* LK_GLMODEL v1 */
  lk_glUniform1i(lk_g5_u[14], 1); lk_glUniform1i(lk_g5_u[15], 2); lk_glUniform1i(lk_g5_u[16], 5); lk_glUniform1i(lk_g5_u[17], 6);
  lk_glUniform1i(lk_g5_u[25], 8); lk_glUniform1f(lk_g5_u[26], sc[12]); lk_glUniform1f(lk_g5_u[27], sc[13]); lk_glUniform1i(lk_g5_u[28], 10);
  { int nsh = lk_gl_shafts(shf); lk_glUniform1f(lk_g5_u[23], (float)nsh); lk_glUniform4fv(lk_g5_u[24], 9, shf); sc[31] = (float)nsh; }
  lk_glUniform1f(lk_g5_u[18], sc[5]); lk_glUniform3f(lk_g5_u[19], sc[6], sc[7], sc[8]); lk_glUniform1f(lk_g5_u[20], sc[9]); lk_glUniform1f(lk_g5_u[21], sc[10]); lk_glUniform1f(lk_g5_u[22], sc[11]);
  lk_glUniform3f(lk_g5_u[30], sc[14], sc[15], sc[16]); lk_glUniform1f(lk_g5_u[31], sc[17]); lk_glUniform1f(lk_g5_u[32], sc[18]); lk_glUniform1f(lk_g5_u[33], sc[19]); lk_glUniform3f(lk_g5_u[34], sc[20], sc[21], sc[22]); lk_glUniform1f(lk_g5_u[35], sc[23]);
  { void (*u2v)(lkGLint, lkGLsizei, const lkGLfloat *) = (void (*)(lkGLint, lkGLsizei, const lkGLfloat *))lk_gpu_fn("glUniform2fv"); if (u2v) u2v(lk_g5_u[13], 16, dv); }
  return 1; }
static void lk_g5_run(const float *lp, const float *lc) {   /* compare (LANDSTALKER_GL5CMP): after the CPU block / list uploads, before the light pass */
  static uint32_t rb[32 * 160], rb0[32 * 64], ex[1024], gb[2048]; float *sc = lk_g5_sc; int nsh, j, i; lkGLint fb0 = 0; static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 };
  if (!lk_g5_bind(lp, lc, 1)) { lk_g5_n = 0; return; }
  nsh = (int)sc[31];
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glBindFramebuffer(0x8D40, lk_g5_fbo);
  lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad);
  lk_glPixelStorei(0x0D02, 0); lk_glPixelStorei(0x0D05, 4);
  for (j = 0; j < lk_g5_n; j++) { int nl = lk_g5_nl[j];
    for (i = 0; i < 1024; i++) ex[i] = lk_g5_ref[j][3][i] & 0x1FFFFu;
    lk_glActiveTexture(0x84C6); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 32, 32, 0x1908, 0x1401, ex); lk_glActiveTexture(0x84C0);
    lk_glUniform2f(lk_g5_u[7], (float)lk_g5_bx[j], (float)lk_g5_by[j]);
    lk_glUniform1f(lk_g5_u[29], 0.0f); lk_glViewport(0, 0, 32, 64); lk_glDrawArrays(0x0005, 0, 4); lk_glReadPixels(0, 0, 32, 64, 0x1908, 0x1401, rb0);   /* GL5b: the GPU's own view ray */
    for (i = 0; i < 1024; i++) { uint32_t e2 = lk_g5_ref[j][2][i], e3 = lk_g5_ref[j][3][i]; gb[i] = ((e2 >> 8) & 255) | (((e2 >> 16) & 0xFFFF) << 8) | (((e3 >> 16) & 1) << 24); gb[1024 + i] = e3 & 0xFFFF; }   /* the CPU's geometry for the term planes */
    lk_glActiveTexture(0x84CA); lk_glBindTexture(0x0DE1, lk_g5_geo); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 32, 64, 0x1908, 0x1401, gb); lk_glActiveTexture(0x84C0);
    lk_glUniform1f(lk_g5_u[29], 1.0f); lk_glViewport(0, 0, 32, 160); lk_glDrawArrays(0x0005, 0, 4); lk_glReadPixels(0, 0, 32, 160, 0x1908, 0x1401, rb);
    lk_g5_blocks++;
    for (i = 0; i < 1024; i++) { int ix = i & 31, iy = i >> 5, pl, c; uint32_t ex = lk_g5_ref[j][2][i]; int face = (ex >> 8) & 255, z = (int)(int16_t)(ex >> 16);
      { uint32_t g5 = rb0[iy * 32 + ix], g6 = rb0[(32 + iy) * 32 + ix]; int gf = (int)(g5 & 255), gz = (int)(int16_t)((g5 >> 8) & 0xFFFF), gr = (int)(int16_t)(g6 & 0xFFFF), cr = (int)(int16_t)(lk_g5_ref[j][3][i] & 0xFFFF), bad = gf != face || (face && gz != z) || gr != cr;   /* GL5b view ray */
        lk_g5_cnt[5][bad ? 2 : 0]++;
        if (bad && lk_g5_shown < lk_g5_maxshow) { lk_g5_shown++; printf("gl5: diff block %%d,%%d pixel %%d,%%d U %%d V %%d ray cpu face %%d z %%d robj %%d gpu face %%d z %%d robj %%d layerA %%d rayf %%d\n", lk_g5_bx[j], lk_g5_by[j], ix, iy, lk_g5_bx[j] * 32 + ix, lk_g5_by[j] * 32 + iy, face, z, cr, gf, gz, gr, (int)((lk_g5_ref[j][3][i] >> 16) & 1), (int)sc[13]); } }
      if (nsh) { uint32_t g = rb[(4 * 32 + iy) * 32 + ix], r = lk_g5_ref[j][4][i]; for (c = 0; c < 2; c++) { int a = (int)((r >> (8 * c)) & 255), b = (int)((g >> (8 * c)) & 255), d = abs(a - b); lk_g5_cnt[4][d == 0 ? 0 : d == 1 ? 1 : 2]++;
        if (d > 1 && lk_g5_shown < lk_g5_maxshow) { lk_g5_shown++; printf("gl5: diff block %%d,%%d pixel %%d,%%d U %%d V %%d %%s cpu %%d gpu %%d face %%d z %%d\n", lk_g5_bx[j], lk_g5_by[j], ix, iy, lk_g5_bx[j] * 32 + ix, lk_g5_by[j] * 32 + iy, c ? "pool" : "beam", a, b, face, z); } } }
      if (!face) continue;
      for (pl = 0; pl < 4; pl++) { uint32_t g = rb[(pl * 32 + iy) * 32 + ix], r = pl < 2 ? lk_g5_ref[j][pl][i] : pl == 2 ? (ex & 255) : (lk_g5_ref[j][3][i] >> 24);
        if (pl == 3 && !sc[0] && !sc[9]) continue;
        for (c = 0; c < (pl < 2 ? 4 : 1); c++) { int kk = pl * 4 + c, cls = pl < 2 ? 0 : pl == 2 ? 1 : sc[0] ? 2 : 3, a = (int)((r >> (8 * c)) & 255), b = (int)((g >> (8 * c)) & 255), d = abs(a - b);
          if (pl < 2 && kk >= nl) continue;
          if (pl == 2 && !sc[1]) continue;
          lk_g5_cnt[cls][d == 0 ? 0 : d == 1 ? 1 : 2]++;
          if (d > 1 && lk_g5_shown < lk_g5_maxshow) { lk_g5_shown++; printf("gl5: diff block %%d,%%d pixel %%d,%%d U %%d V %%d %%s %%d cpu %%d gpu %%d face %%d z %%d sun %%d\n", lk_g5_bx[j], lk_g5_by[j], ix, iy, lk_g5_bx[j] * 32 + ix, lk_g5_by[j] * 32 + iy, cls == 2 ? "sun" : cls == 3 ? "key" : cls ? "ao" : "term", kk, a, b, face, z, (int)sc[0]); } } } } }
  lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0);
  lk_g5_n = 0; lk_g5_frames++;
  if (lk_g5_frames - lk_g5_last >= lk_g5_every) { lk_g5_last = lk_g5_frames;
    printf("gl5: frames %%ld blocks %%ld terms exact %%ld off1 %%ld worse %%ld | ao exact %%ld off1 %%ld worse %%ld | sun exact %%ld off1 %%ld worse %%ld | key exact %%ld off1 %%ld worse %%ld | shaft exact %%ld off1 %%ld worse %%ld | view ray same %%ld different %%ld\n", lk_g5_frames, lk_g5_blocks, lk_g5_cnt[0][0], lk_g5_cnt[0][1], lk_g5_cnt[0][2], lk_g5_cnt[1][0], lk_g5_cnt[1][1], lk_g5_cnt[1][2], lk_g5_cnt[2][0], lk_g5_cnt[2][1], lk_g5_cnt[2][2], lk_g5_cnt[3][0], lk_g5_cnt[3][1], lk_g5_cnt[3][2], lk_g5_cnt[4][0], lk_g5_cnt[4][1], lk_g5_cnt[4][2], lk_g5_cnt[5][0], lk_g5_cnt[5][2]); } }
/* ---- v5 GL5c: the GPU computes the light blocks itself (LANDSTALKER_GL5=1, test aid until the user's check): every visible block that has no GPU data or is stale
   (sun step) gets the geometry pass (view ray) and the packed pass, copied straight into the room textures the light shader reads (roomT0 / T1 / A / B / K);
   block table + light lists come from the GPU side (lk_gl_blist5).  Stale blocks stay on screen until recomputed (no flicker at a sun step); a new room clears all.
   The CPU light blocks are still computed (fallback, motes / particles depth); LANDSTALKER_GL5_CAP = visible blocks without data per frame (18, was 24) / LANDSTALKER_GL5_CAP2 = look-ahead ring + stale blocks per frame (4); ~0.2..0.4 ms per block on the Deck, LANDSTALKER_GL5_TIME=1 prints the GPU time. ---- */
static int lk_g5_slow, lk_g5_ron = -1, lk_g5_cap = 18, lk_g5_cap2 = 4,   /* cap 18 (was 24) since 2026-11-07: the side penumbra makes a block ~20 %% dearer, 24 per frame gave extra 20 ms frames after room changes (rec_20261107_2031) */  lk_g5_tdbg, lk_g5_wdirty = 1; static unsigned lk_g5_hk, lk_g5_sk, lk_g5_bk[38][76]; static uint32_t lk_g5_bt[38][76], lk_g5_l0[38][76], lk_g5_l1[38][76];
static lkGLuint lk_g5_q[2]; static int lk_g5_qst, lk_g5_qi, lk_g5_qp[2], lk_g5_qn, lk_g5_qover; static double lk_g5_qsum;
static int lk_g5_qb[2]; static double lk_g5_bms = -1.0;   /* LK_GL5RING v1 (2026-11-11, user rec_20261111_2006: stutter in Mercator 632): blocks in each timer query, running GPU ms per block.
   The Deck GPU idles at 200 MHz (measured 88 %% of the time in 632, desktop mode): a look-ahead block then costs ~2.5 ms instead of ~0.4, and 4 ring blocks per frame
   made 21..29 ms frames while walking.  The ring (not visible yet) now gets as many blocks as fit into LANDSTALKER_GL5_RINGMS (5 ms) at the measured cost (ring now 2 blocks wide, LANDSTALKER_GL5_RING; nearest ring first, the side the camera moves to first), at least 1,
   at most CAP2, and none in a frame that already computes visible blocks; visible blocks keep their budget (CAP).  LANDSTALKER_GL5_RINGMS=0 = old fixed CAP2. */   /* GPU+ watchdog: block pass time per frame (120 frame average > LANDSTALKER_GL5_MAXMS, default 5 ms, twice -> GPU (GL4) for the rest of the run) */
static void lk_g5_qpoll(void) { int o; lkGLint av; unsigned long long ns; static double mx = -1.0; if (mx < 0.0) { const char *e = getenv("LANDSTALKER_GL5_MAXMS"); mx = e ? atof(e) : 5.0; }
  for (o = 0; o < 2; o++) { if (!lk_g5_qp[o]) continue; av = 0; ns = 0; lk_glGetQueryObjectiv(lk_g5_q[o], 0x8867, &av); if (!av) continue; lk_glGetQueryObjectui64v(lk_g5_q[o], 0x8866, &ns); lk_g5_qp[o] = 0; lk_g5_qsum += (double)ns * 1e-6;
    if (lk_g5_qb[o] > 0) { double per = (double)ns * 1e-6 / (double)lk_g5_qb[o]; lk_g5_bms = lk_g5_bms < 0.0 ? per : lk_g5_bms * 0.75 + per * 0.25; } }   /* LK_GL5RING v1 */
  if (++lk_g5_qn < 120) return;
  { double avg = lk_g5_qsum / lk_g5_qn; lk_g5_qsum = 0.0; lk_g5_qn = 0; if (lk_glt_qdbg) printf("gl5: block passes %%.3f ms per frame on the GPU (120 frame average)\n", avg);
    if (mx > 0.0 && avg > mx) { if (++lk_g5_qover >= 2) { lk_g5_slow = 1; printf("gl5: light block pass too slow on this GPU (%%.2f ms > %%.2f ms), the CPU computes the light blocks from now on (GPU light stays)\n", avg, mx); } } else lk_g5_qover = 0; } }
static int lk_g5_vc = 18;   /* LK_GL5ENTRY v1 (2026-11-11, user: 'Haenger von Mercator'): after a room change (new hard key) the visible blocks without data are spread
   over the fade-in by the measured GPU time (LANDSTALKER_GL5_ENTRYMS, 18 ms, for 40 frames; a frame of 20 or 33 ms both miss exactly one vsync; was CAP 18 at once = 5 frames of 60..87 ms at 200 MHz); a block not computed yet
   shows the flat base light (no shadows) while the picture is still dark (fade-in of 632: frames 604..624); at most 18 / 2.5 = 7 blocks per frame (632: all done by frame 616, frames 27..37 ms instead of 5 frames of 58..87 ms).  LANDSTALKER_GL5_ENTRYMS=0 = old. */
static int lk_g5_rc = 4, lk_g5_rw = 2; static float lk_g5_mu, lk_g5_mv;   /* LK_GL5RING v1: ring blocks allowed this frame */
static long lk_g5_tn, lk_g5_tbl, lk_g5_tfr; static unsigned char lk_g5_pn[38][76]; static double lk_g5_tms, lk_g5_tmax;
extern int lk_gle_get(void);
static int lk_g5_realon(void) { if (lk_g5_ron < 0) { const char *e = getenv("LANDSTALKER_GL5"), *c = getenv("LANDSTALKER_GL5_CAP"), *t = getenv("LANDSTALKER_GL5_TIME"); lk_g5_ron = e ? atoi(e) : -1; if (c && atoi(c) > 0) lk_g5_cap = atoi(c); { const char *c2 = getenv("LANDSTALKER_GL5_CAP2"); if (c2 && atoi(c2) >= 0) lk_g5_cap2 = atoi(c2); } lk_g5_tdbg = t ? atoi(t) : 0;
    if (lk_g5_ron > 0) printf("gl5: the GPU computes the light blocks (LANDSTALKER_GL5=1)\n"); if (lk_g5_ron < 0) lk_g5_ron = -2; }
  return (lk_g5_ron == -2 ? lk_gle_get() >= 1 : lk_g5_ron > 0) && lk_g5_st >= 0 && !lk_g5_slow; }   /* Light Engine GPU = GL5c (env LANDSTALKER_GL5=0 = the old GPU path with CPU blocks, test aid); the block watchdog falls back to that path */
/* GL5c sun step swap: when the blocks take over the next sun direction (CPU: memcpy sun <- sunn), the GPU copies roomA.b (sunn) into roomA.g (sun) for every block that has sunn
   (block table .g) in one full texture pass, so no block shows the old direction until it is recomputed (user 2026-11-06: 'beim Rausgehen legt sich kurz was ueber den Screen') */
static lkGLuint lk_g5_swp, lk_g5_swt, lk_g5_swf; static lkGLint lk_g5_swu[2]; static int lk_g5_swst; static float lk_g5_pdir[6]; static int lk_g5_psunn;
static const char *lk_g5_swfs = "#version 120\nuniform sampler2D tmp; uniform sampler2D btab;\nvoid main() { vec2 fc = floor(gl_FragCoord.xy); vec4 t = texture2D(tmp, (fc + 0.5) / vec2(2432.0, 1216.0)); float sg = texture2D(btab, (floor(fc / 32.0) + 0.5) / vec2(76.0, 38.0)).g;\n  gl_FragColor = vec4(t.r, sg > 0.5 ? t.b : t.g, t.b, t.a); }\n";
static int lk_g5_swap(void) {
  static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 }; static uint32_t btm[38 * 76]; lkGLint fb0 = 0, ok = 0; int x, y;
  if (lk_g5_swst == 0) { lkGLuint vs, fs; lkGLenum st; lkGLint t0 = 0; static const char *vsrc = "#version 120\nvoid main() { gl_Position = gl_Vertex; }\n";
    lk_g5_swst = -1;
    vs = lk_glCreateShader(0x8B31); lk_glShaderSource(vs, 1, &vsrc, 0); lk_glCompileShader(vs); lk_glGetShaderiv(vs, 0x8B81, &ok); if (!ok) return 0;
    fs = lk_glCreateShader(0x8B30); lk_glShaderSource(fs, 1, &lk_g5_swfs, 0); lk_glCompileShader(fs); lk_glGetShaderiv(fs, 0x8B81, &ok); if (!ok) { printf("gl5: swap shader failed\n"); return 0; }
    lk_g5_swp = lk_glCreateProgram(); lk_glAttachShader(lk_g5_swp, vs); lk_glAttachShader(lk_g5_swp, fs); lk_glLinkProgram(lk_g5_swp); lk_glGetProgramiv(lk_g5_swp, 0x8B82, &ok); if (!ok) return 0;
    lk_g5_swu[0] = lk_glGetUniformLocation(lk_g5_swp, "tmp"); lk_g5_swu[1] = lk_glGetUniformLocation(lk_g5_swp, "btab");
    lk_glGetIntegerv(0x8069, &t0); lk_g5_swt = lk_glt_tex(2432, 1216, 0x1908, 0x1908); lk_glBindTexture(0x0DE1, (lkGLuint)t0);
    lk_glGetIntegerv(0x8CA6, &fb0); lk_glGenFramebuffers(1, &lk_g5_swf); lk_glBindFramebuffer(0x8D40, lk_g5_swf); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_glt_t[3], 0);
    st = lk_glCheckFramebufferStatus(0x8D40); lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); if (st != 0x8CD5) { printf("gl5: swap framebuffer incomplete\n"); return 0; }
    lk_g5_swst = 1; }
  if (lk_g5_swst < 0) return 0;
  for (y = 0; y < 38; y++) for (x = 0; x < 76; x++) btm[y * 76 + x] = lk_g5_bt[y][x];
  lk_glActiveTexture(0x84C4); lk_glBindTexture(0x0DE1, lk_glt_t[4]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 76, 38, 0x1908, 0x1401, btm);
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glBindFramebuffer(0x8D40, lk_g5_swf);
  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_g5_swt); lk_glCopyTexSubImage2D(0x0DE1, 0, 0, 0, 0, 0, 2432, 1216);   /* roomA -> copy */
  lk_glUseProgram(lk_g5_swp); lk_glUniform1i(lk_g5_swu[0], 0); lk_glUniform1i(lk_g5_swu[1], 4); lk_glViewport(0, 0, 2432, 1216);
  lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad); lk_glDrawArrays(0x0005, 0, 4);
  lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); return 1; }
static void lk_g5_prep(void) { unsigned hk, sk; int x, y, sunn; float dirs[6]; lk_gl_wkey(&hk, &sk, dirs, &sunn);
  if (lk_g5_tdbg > 1 && (hk != lk_g5_hk || sk != lk_g5_sk)) printf("gl5: key change frame %%ld hard %%08X -> %%08X soft %%08X -> %%08X\n", platform_frame_number(), lk_g5_hk, hk, lk_g5_sk, sk);
  if (hk != lk_g5_hk && lk_g5_tdbg > 2) { int tot = 0, nb = 0; for (y = 0; y < 38; y++) for (x = 0; x < 76; x++) { tot += lk_g5_pn[y][x]; nb += lk_g5_pn[y][x] > 0; } printf("gl5: room done: %%d computes of %%d blocks\n", tot, nb); }
  if (hk != lk_g5_hk) { memset(lk_g5_pn, 0, sizeof lk_g5_pn); lk_g5_hk = hk; lk_g5_sk = sk; memset(lk_g5_bt, 0, sizeof lk_g5_bt); memset(lk_g5_bk, 0, sizeof lk_g5_bk); lk_g5_wdirty = 1; }
  else if (sk != lk_g5_sk) { unsigned osk = lk_g5_sk; int swap = lk_g5_psunn && dirs[0] == lk_g5_pdir[3] && dirs[1] == lk_g5_pdir[4] && dirs[2] == lk_g5_pdir[5];   /* the step finished: the new direction is the old 'next' one */
    if (swap && lk_g5_swap()) { lk_gl_surfswap(); for (y = 0; y < 38; y++) for (x = 0; x < 76; x++) if ((lk_g5_bt[y][x] & 0xFF00u) && lk_g5_bk[y][x] == osk) lk_g5_bk[y][x] = sk; if (lk_g5_tdbg > 1) printf("gl5: sun step swap on the GPU (frame %%ld)\n", platform_frame_number()); }
    lk_g5_sk = sk; lk_g5_wdirty = 1; for (y = 0; y < 38; y++) for (x = 0; x < 76; x++) lk_g5_bt[y][x] &= ~0xFF00u; }   /* stale: no sunn crossfade until recomputed */
  for (x = 0; x < 6; x++) lk_g5_pdir[x] = dirs[x]; lk_g5_psunn = sunn; }
static void lk_g5_real(int u0, int u1, int v0, int v1, const float *lp, const float *lc, uint32_t *bt, uint32_t *bl0, uint32_t *bl1) {
  static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 }; static uint32_t ex[1024]; int lx[96], ly[96], n = 0, pass, bx, by, j, bxa, bxb, bya, byb, L; lkGLint fb0 = 0; Uint64 t0 = 0;
  extern long lk_gl_rowfr[224], lk_gl_capfr; extern int lk_gl_w;
  u0 = v0 = 1 << 30; u1 = v1 = -(1 << 30);   /* only the lines composed this frame (the others hold old positions) */
  for (L = 0; L < 224; L++) { int U, V; if (lk_gl_rowfr[L] != lk_gl_capfr) continue; U = (int)(int16_t)(lk_gl_row[L] & 0xFFFF); V = (int)(int16_t)(lk_gl_row[L] >> 16);
    if (U < u0) u0 = U; if (U + lk_gl_w - 1 > u1) u1 = U + lk_gl_w - 1; if (V < v0) v0 = V; if (V > v1) v1 = V; }
  if (lk_g5_pbst == 0) lk_g5_pbinit();
  if (u1 >= u0) { static int pu = 1 << 30, pv; if (pu != (1 << 30) && abs(u0 - pu) < 64 && abs(v0 - pv) < 64) { lk_g5_mu = lk_g5_mu * 0.9f + 0.1f * (float)(u0 - pu); lk_g5_mv = lk_g5_mv * 0.9f + 0.1f * (float)(v0 - pv); } else lk_g5_mu = lk_g5_mv = 0.0f; pu = u0; pv = v0; }   /* LK_GL5RING v1: camera motion (blocks ahead first) */
  lk_g5_pbdrain(); if (lk_g5_pbst > 0) lk_gl5_cpuset();   /* v5 CPU saving: the CPU computes no light blocks while this runs */
  if (u1 < u0) return;
  { static int rw = -1; if (rw < 0) { const char *e = getenv("LANDSTALKER_GL5_RING"); rw = e ? atoi(e) : 2; if (rw < 1) rw = 1; if (rw > 4) rw = 4; } lk_g5_rw = rw; }   /* LK_GL5RING v1: look-ahead ring width in blocks (was 1) */
  bxa = (int)floorf((float)u0 / 32.0f) - lk_g5_rw; bxb = (int)floorf((float)u1 / 32.0f) + lk_g5_rw; bya = (int)floorf((float)v0 / 32.0f) - lk_g5_rw; byb = (int)floorf((float)v1 / 32.0f) + lk_g5_rw;
  if (bxa < 0) bxa = 0; if (bya < 0) bya = 0; if (bxb > 75) bxb = 75; if (byb > 37) byb = 37;
  { int base = 0; for (pass = 0; pass < 2 + 4 * lk_g5_rw && n < 96; pass++) { int cap;   /* LK_GL5RING v1: ring passes per distance (nearest ring first), the side the camera moves to first */   /* 0 visible without data (up to CAP), then visible stale, ring without data, ring stale (together CAP2 more) */
    if (pass == 2) { static double rms = -1.0; int rc = lk_g5_cap2; base = n; if (rms < 0.0) { const char *e = getenv("LANDSTALKER_GL5_RINGMS"); rms = e ? atof(e) : 5.0; }   /* LK_GL5RING v1 */
      if (rms > 0.0) { if (base > 0) rc = 0; else if (lk_g5_bms > 0.0) { int k = (int)(rms / lk_g5_bms); if (k < 1) k = 1; if (k < rc) rc = k; } } lk_g5_rc = rc; }
    if (pass == 0) { static unsigned lhk; static long efr = -1000; static double ems = -1.0; long fr = platform_frame_number(); lk_g5_vc = lk_g5_cap;   /* LK_GL5ENTRY v1 */
      if (ems < 0.0) { const char *e = getenv("LANDSTALKER_GL5_ENTRYMS"); ems = e ? atof(e) : 18.0; }
      if (lk_g5_hk != lhk) { lhk = lk_g5_hk; efr = fr; }
      if (ems > 0.0 && fr - efr < 40) { int k = (int)(ems / (lk_g5_bms > 2.5 ? lk_g5_bms : 2.5));   /* at least 2.5 ms per block assumed: the estimate of the last room can be from a faster clock */ if (k < 2) k = 2; if (k < lk_g5_vc) lk_g5_vc = k; } }
    cap = pass < 2 ? lk_g5_vc : base + lk_g5_rc;   /* visible blocks (missing, then stale: a sun step) get the big budget, the ring the small one */
    for (by = bya; by <= byb && n < cap && n < 96; by++) for (bx = bxa; bx <= bxb && n < cap && n < 96; bx++) {
      int vis = bx * 32 + 31 >= u0 && bx * 32 <= u1 && by * 32 + 31 >= v0 && by * 32 <= v1, nod = !lk_g5_bt[by][bx], st = !nod && lk_g5_bk[by][bx] != lk_g5_sk;
      if ((pass < 2) != (vis != 0)) continue;
      if ((pass & 1) ? !st : !nod) continue;
      if (pass >= 2) { int ex0 = bx * 32 + 31 < u0 ? (u0 - bx * 32) / 32 : bx * 32 > u1 ? (bx * 32 - u1 + 31) / 32 : 0, ey0 = by * 32 + 31 < v0 ? (v0 - by * 32) / 32 : by * 32 > v1 ? (by * 32 - v1 + 31) / 32 : 0, dd = ex0 > ey0 ? ex0 : ey0;   /* LK_GL5RING v1 */
        if (dd < 1) dd = 1; if (dd != 1 + (pass - 2) / 4) continue;
        { int ah = (lk_g5_mu > 0.05f && bx * 32 > u1) || (lk_g5_mu < -0.05f && bx * 32 + 31 < u0) || (lk_g5_mv > 0.05f && by * 32 > v1) || (lk_g5_mv < -0.05f && by * 32 + 31 < v0);
          if (ah != ((((pass - 2) / 2) & 1) == 0)) continue; } }
      if (lk_g5_tdbg > 2 && platform_frame_number() %% 97 == 0) printf("gl5: frame %%ld pick %%d,%%d pass %%d (u %%d..%%d v %%d..%%d) bt %%08X bk %%08X sk %%08X\n", platform_frame_number(), bx, by, pass, u0, u1, v0, v1, lk_g5_bt[by][bx], lk_g5_bk[by][bx], lk_g5_sk);
      if (lk_g5_tdbg > 2 && nod && lk_g5_pn[by][bx]) printf("gl5: REPICK frame %%ld block %%d,%%d picked %%d times bt %%08X\n", platform_frame_number(), bx, by, lk_g5_pn[by][bx], lk_g5_bt[by][bx]);
      if (lk_g5_pn[by][bx] < 255) lk_g5_pn[by][bx]++;
      lx[n] = bx; ly[n] = by; n++; } } }
  if (lk_g5_tdbg >= 4) { int vn = 0, vs = 0, x2, y2; for (y2 = bya; y2 <= byb; y2++) for (x2 = bxa; x2 <= bxb; x2++) { int vis2 = x2 * 32 + 31 >= u0 && x2 * 32 <= u1 && y2 * 32 + 31 >= v0 && y2 * 32 <= v1; if (!vis2) continue; if (!lk_g5_bt[y2][x2]) vn++; else if (lk_g5_bk[y2][x2] != lk_g5_sk) vs++; }
    printf("gl5: frame %%ld computes %%d, visible without data %%d stale %%d\n", platform_frame_number(), n, vn, vs); }
  if (!n) return;
  if (lk_g5_tdbg && lk_glFinish) { lk_glFinish(); t0 = SDL_GetPerformanceCounter(); }
  if (!lk_g5_bind(lp, lc, lk_g5_wdirty)) return;
  if (lk_g5_qst == 0) { if (lk_glt_qst == 0) lk_glt_qinit(); if (lk_glt_qst > 0) { lk_glGenQueries(2, lk_g5_q); lk_g5_qst = 1; } else lk_g5_qst = -1; }
  if (lk_g5_qst > 0 && !lk_g5_qp[lk_g5_qi]) { lk_glBeginQuery(0x88BF, lk_g5_q[lk_g5_qi]); lk_g5_qb[lk_g5_qi] = n; } else if (lk_g5_qst > 0) lk_g5_qst = 2;   /* 2: slot busy, no query this frame */
  lk_g5_wdirty = 0;
  for (j = 0; j < n; j++) { uint32_t a, b2; int nl; bx = lx[j]; by = ly[j]; lk_gl_blist5(bx, by, &a, &b2, &nl);
    lk_g5_l0[by][bx] = a; lk_g5_l1[by][bx] = b2; lk_g5_bt[by][bx] = 0xFFu | (lk_g5_sc[17] > 0.5f ? 0xFF00u : 0u) | ((uint32_t)nl << 16);
    bt[by * 76 + bx] = lk_g5_bt[by][bx]; bl0[by * 76 + bx] = a; bl1[by * 76 + bx] = b2; }
  lk_glActiveTexture(0x84C4); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 76, 38, 0x1908, 0x1401, bt);
  lk_glActiveTexture(0x84C9); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 76, 38, 0x1908, 0x1401, bl0); lk_glTexSubImage2D(0x0DE1, 0, 76, 0, 76, 38, 0x1908, 0x1401, bl1);
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glBindFramebuffer(0x8D40, lk_g5_fbo);
  lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad);
  for (j = 0; j < n; j++) { static const int pt[5] = { 5, 6, 3, 7, 8 }; int k; bx = lx[j]; by = ly[j];
    lk_gl_bextra(bx, by, ex); lk_glActiveTexture(0x84C6); lk_glBindTexture(0x0DE1, lk_g5_bx2); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 32, 32, 0x1908, 0x1401, ex);
    lk_glUniform2f(lk_g5_u[7], (float)bx, (float)by);
    lk_glUniform1f(lk_g5_u[29], 0.0f); lk_glViewport(0, 0, 32, 64); lk_glDrawArrays(0x0005, 0, 4);
    lk_glActiveTexture(0x84CA); lk_glBindTexture(0x0DE1, lk_g5_geo); lk_glCopyTexSubImage2D(0x0DE1, 0, 0, 0, 0, 0, 32, 64);
    lk_glUniform1f(lk_g5_u[29], 2.0f); lk_glViewport(0, 0, 32, 160); lk_glDrawArrays(0x0005, 0, 4);
    lk_glActiveTexture(0x84CC); for (k = 0; k < 5; k++) { lk_glBindTexture(0x0DE1, lk_glt_t[pt[k]]); lk_glCopyTexSubImage2D(0x0DE1, 0, bx * 32, by * 32, 0, 32 * k, 32, 32); }
    if (lk_gm_dbg >= 2) { static uint32_t gq[32 * 64], pq[32 * 160]; int i2; lk_glPixelStorei(0x0D05, 4); lk_glReadPixels(0, 0, 32, 160, 0x1908, 0x1401, pq);   /* LK_GLMODEL v1 test aid: per model pixel (every 2nd) face / z / normal / AO / key share */
      lk_glActiveTexture(0x84CA); { lkGLint fbx = 0; lk_glGetIntegerv(0x8CA6, &fbx); } lk_glActiveTexture(0x84CC);
      static int all = -1; if (all < 0) { const char *e = getenv("LANDSTALKER_GL5_MODELDBGALL"); all = e && atoi(e); }   /* LK_GLROOM v1 test aid: =1 every pixel (default every 2nd in U and V) */
      for (i2 = 0; i2 < 1024; i2 += all ? 1 : 2) { int ix2 = i2 & 31, iy2 = i2 >> 5; uint32_t A = pq[(64 + iy2) * 32 + ix2], K = pq[(128 + iy2) * 32 + ix2], Bq = pq[(96 + iy2) * 32 + ix2];
        (void)gq; if ((iy2 & 1) && !all) continue;
        printf("gm: U %%d V %%d face %%u key %%u ao %%u z %%d km %%u\n", bx * 32 + ix2, by * 32 + iy2, A & 255, (A >> 8) & 255, A >> 24, (int)(int16_t)(Bq & 0xFFFF), K & 255); } }
    if (lk_g5_pbst > 0 && lk_g5_pbn[lk_g5_pbi] < 96) { int q = lk_g5_pbn[lk_g5_pbi]++; lk_g5_pbx[lk_g5_pbi][q] = bx; lk_g5_pby[lk_g5_pbi][q] = by; lk_g5_pbsg[lk_g5_pbi] = lk_g5_sc[17] > 0.5f;
      lk_glBindBuffer(0x88EB, lk_g5_pbo[lk_g5_pbi]); lk_glPixelStorei(0x0D02, 0); lk_glPixelStorei(0x0D05, 4); lk_glReadPixels(0, 64, 32, 64, 0x1908, 0x1401, (void *)(intptr_t)(q * 32 * 64 * 4)); lk_glBindBuffer(0x88EB, 0); }   /* room A + room B planes */
    lk_g5_bk[by][bx] = lk_g5_sk; }
  lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); lk_glActiveTexture(0x84C0);
  if (lk_g5_pbst > 0 && lk_g5_pbn[lk_g5_pbi]) lk_g5_pbi ^= 1;   /* next frame drains it */
  if (lk_g5_qst == 1) { lk_glEndQuery(0x88BF); lk_g5_qp[lk_g5_qi] = 1; lk_g5_qi ^= 1; } else if (lk_g5_qst == 2) lk_g5_qst = 1;
  if (lk_g5_tdbg && lk_glFinish) { double ms; lk_glFinish(); ms = (double)(SDL_GetPerformanceCounter() - t0) * 1e3 / (double)SDL_GetPerformanceFrequency();
    lk_g5_tms += ms; lk_g5_tbl += n; lk_g5_tn++; if (ms > lk_g5_tmax) lk_g5_tmax = ms;
    if (++lk_g5_tfr >= 60) { printf("gl5: GPU blocks: %%ld frames with work, %%ld blocks, %%.2f ms per block, max %%.1f ms in one frame\n", lk_g5_tn, lk_g5_tbl, lk_g5_tbl ? lk_g5_tms / lk_g5_tbl : 0.0, lk_g5_tmax); lk_g5_tfr = 0; lk_g5_tn = lk_g5_tbl = 0; lk_g5_tms = lk_g5_tmax = 0.0; } } }
/* ---- v5 GL5d BOUNCE LIGHT (user 2026-11-06: 'GL5 mit abprallendem Licht'; option Graphics > Bounce Light, default Off): one bounce, approximated after the light pass.
   Pass A (113 x 57, v2 cells on the room picture grid, linear filtered: no spots that scroll, user 2026-11-06): per 4 x 4 cell the light its scenery pixels get on top of the room's base light (lit - unlit * base).  Pass B (448 x 224): every scenery pixel gathers 32
   cells around it (spiral, radius LANDSTALKER_BOUNCE_R px, default 96) weighted by the two faces' cosines (only surfaces that face each other exchange light: floor <-> wall, not floor <->
   floor) and distance (LANDSTALKER_BOUNCE_D, 56 units), times its own colour, strength LANDSTALKER_BOUNCE_K (5; first look by eye 2026-11-06: 0.6 / 3 were invisible).  Emissive / HUD pixels (mix after the light) and figures stay as they are.
   GPU light engines only (the CPU engine keeps the old look); off without a light source (no flames / sun / key light). ---- */
extern int lk_bl_get(void);
static int lk_gb_st; static lkGLuint lk_gb_prog, lk_gb_fa, lk_gb_fb, lk_gb_ra, lk_gb_out; static lkGLint lk_gb_u[48];
static long lk_gsw_fr = -9; static int lk_gsw_on;   /* GL5e: the frame's decision (light pass and post pass must agree) */
int lk_gsw_frame(int real, int swon) { extern int lk_swsh_get(void); long f = platform_frame_number(); if (lk_gsw_fr != f) { lk_gsw_fr = f; lk_gsw_on = real && swon && lk_swsh_get() && lk_g5_realon() && lk_g5_wh != 0 && lk_gb_st >= 0; } return lk_gsw_on; } static float lk_gb_k = -1.0f, lk_gb_r, lk_gb_d;
static const char *lk_gb_fs = "#version 120\n" @SHADERB@;
static const char *lk_gb_un[] = { "lit", "unl", "cls", "rows", "roomA", "roomB", "rad", "post", "btab", "uMode", "uBase", "uW", "uK", "uR", "uD", "uPost", "uPh", "uOut", "wld", "uSwP", "uSwC", "uSw", "uSunR", "uLP", "uLC", "uLF", "uFG", "uFA", "uNl", "uAmb", "uSS", "uSK", "uAmb3", "uSun3", "uDn", "uKey", "uKA", "uKK", "uSd", "uE", "uSwon", "uFig", "uNf", "uRfK", "uRfD", "fine", "uFn", 0 };
static int lk_gb_init(void) {
  lkGLint ok = 0, t0 = 0, fb0 = 0; lkGLuint vs, fs; char log[2048]; int i; lkGLenum st1, st2;
  { static const char *vsrc = "#version 120\nvoid main() { gl_Position = gl_Vertex; }\n"; vs = lk_glCreateShader(0x8B31); lk_glShaderSource(vs, 1, &vsrc, 0); lk_glCompileShader(vs); lk_glGetShaderiv(vs, 0x8B81, &ok); if (!ok) return -1; }
  fs = lk_glCreateShader(0x8B30); lk_glShaderSource(fs, 1, &lk_gb_fs, 0); lk_glCompileShader(fs); lk_glGetShaderiv(fs, 0x8B81, &ok);
  if (!ok) { lk_glGetShaderInfoLog(fs, sizeof log, 0, log); printf("bounce: shader failed: %%s\n", log); return -1; }
  lk_gb_prog = lk_glCreateProgram(); lk_glAttachShader(lk_gb_prog, vs); lk_glAttachShader(lk_gb_prog, fs); lk_glLinkProgram(lk_gb_prog); lk_glGetProgramiv(lk_gb_prog, 0x8B82, &ok);
  if (!ok) { lk_glGetProgramInfoLog(lk_gb_prog, sizeof log, 0, log); printf("bounce: link failed: %%s\n", log); return -1; }
  for (i = 0; lk_gb_un[i]; i++) lk_gb_u[i] = lk_glGetUniformLocation(lk_gb_prog, lk_gb_un[i]);
  lk_glGetIntegerv(0x8069, &t0); lk_gb_ra = lk_glt_tex(116, 60, 0x1908, 0x1908); lk_glTexParameteri(0x0DE1, 0x2801, 0x2601); lk_glTexParameteri(0x0DE1, 0x2800, 0x2601); lk_gb_out = lk_glt_tex(448, 224, 0x1908, 0x1908); lk_glBindTexture(0x0DE1, (lkGLuint)t0);
  lk_glGetIntegerv(0x8CA6, &fb0);
  lk_glGenFramebuffers(1, &lk_gb_fa); lk_glBindFramebuffer(0x8D40, lk_gb_fa); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_gb_ra, 0); st1 = lk_glCheckFramebufferStatus(0x8D40);
  lk_glGenFramebuffers(1, &lk_gb_fb); lk_glBindFramebuffer(0x8D40, lk_gb_fb); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_gb_out, 0); st2 = lk_glCheckFramebufferStatus(0x8D40);
  lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); if (st1 != 0x8CD5 || st2 != 0x8CD5) { printf("bounce: framebuffer incomplete\n"); return -1; }
  { const char *e = getenv("LANDSTALKER_BOUNCE_K"), *r = getenv("LANDSTALKER_BOUNCE_R"), *d = getenv("LANDSTALKER_BOUNCE_D"); lk_gb_k = e ? (float)atof(e) : 5.0f; lk_gb_r = r ? (float)atof(r) : 96.0f; lk_gb_d = d ? (float)atof(d) : 56.0f; }
  printf("bounce: ready\n"); return 1; }
static int lk_gb_run(void) {   /* right after the real light pass (lk_glt_out holds the lit picture, unit 0 = the presented unlit picture); returns 1 when lk_gb_out holds the result */
  static float fu[64], lp[96 * 4], lc[96 * 4], lf[96 * 4], fg[16 * 4], fa[16 * 4]; static int iu[32]; float base[3], phu = 0.0f, phv = 0.0f; int i; lkGLint tb[11], fb0 = 0, unl = 0; static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 };
  extern int lk_gl_postany;
  int bon = lk_bl_get(), sw, fig; extern int lk_rf_get(void);
  if (lk_gb_st < 0) return 0;
  if (!lk_gl_frame(platform_frame_number(), fu, iu, lp, lc, lf, fg, fa)) return 0;   /* the frame's light state (same as the light pass) */
  sw = lk_gsw_fr == platform_frame_number() && lk_gsw_on;   /* GL5e: decided by the light pass this frame */
  fig = lk_rf_get() && iu[9] > 0 && lk_g5_realon() && lk_g5_wh != 0 && (iu[0] || iu[1] || iu[2]);   /* GL5f: figures on screen, a light source, the GL5 world texture */
  if (!bon && !sw && !fig) return 0;
  if (iu[0] && iu[5]) { base[0] = fu[3]; base[1] = fu[4]; base[2] = fu[5]; }
  else if (iu[0]) { base[0] = fu[1] * 0.95f; base[1] = fu[1] * 0.98f; base[2] = fu[1] * 1.06f; }
  else if (iu[1]) { base[0] = fu[10] * 0.97f; base[1] = fu[10] * 0.99f; base[2] = fu[10] * 1.05f; }
  else if (iu[2]) { base[0] = fu[0] * 0.93f; base[1] = fu[0] * 0.96f; base[2] = fu[0] * 1.06f; }
  else if (!sw && !fig) return 0;   /* no light source in this room */
  else { base[0] = base[1] = base[2] = 1.0f; bon = 0; }
  { static int dbg = -1; if (dbg < 0) { const char *e = getenv("LANDSTALKER_BOUNCE_DBG"); dbg = e ? atoi(e) : 0; } if (dbg && platform_frame_number() %% 100 == 0) printf("bounce: frame %%ld sun %%d dn %%d key %%d nl %%d base %%.2f %%.2f %%.2f w %%d\n", platform_frame_number(), iu[0], iu[5], iu[1], iu[2], base[0], base[1], base[2], iu[7]); }
  if (lk_gb_st == 0) { lk_gb_st = lk_gb_init(); if (lk_gb_st < 0) return 0; }
  lk_glGetIntegerv(0x8069, &unl);   /* unit 0 (active) = the presented unlit picture */
  for (i = 0; i < 11; i++) { lk_glActiveTexture(0x84C0 + i); lk_glGetIntegerv(0x8069, &tb[i]); }
  { extern long lk_gl_rowfr[224], lk_gl_capfr; extern uint32_t lk_gl_row[224]; int L; for (L = 0; L < 224; L++) if (lk_gl_rowfr[L] == lk_gl_capfr) { int U = (int)(int16_t)(lk_gl_row[L] & 0xFFFF), V = (int)(int16_t)(lk_gl_row[L] >> 16) - L; phu = (float)(((U %% 4) + 4) %% 4); phv = (float)(((V %% 4) + 4) %% 4); break; } }   /* cells on the room picture grid */
  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_glt_out); lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, (lkGLuint)unl); lk_glActiveTexture(0x84C2); lk_glBindTexture(0x0DE1, lk_glt_t[1]);
  lk_glActiveTexture(0x84C3); lk_glBindTexture(0x0DE1, lk_glt_t[2]); lk_glActiveTexture(0x84C4); lk_glBindTexture(0x0DE1, lk_glt_t[3]); lk_glActiveTexture(0x84C5); lk_glBindTexture(0x0DE1, lk_glt_t[7]);
  lk_glActiveTexture(0x84C6); lk_glBindTexture(0x0DE1, lk_gb_ra); lk_glActiveTexture(0x84C7); lk_glBindTexture(0x0DE1, lk_glt_t[10]); lk_glActiveTexture(0x84C8); lk_glBindTexture(0x0DE1, lk_glt_t[4]); lk_glActiveTexture(0x84C9); lk_glBindTexture(0x0DE1, lk_g5_wt); lk_glActiveTexture(0x84CA); lk_glBindTexture(0x0DE1, lk_g5_fn); lk_glActiveTexture(0x84C0);   /* LK_SWSHFINE v1: unit 10 = the fine field of the block pass */
  lk_glUseProgram(lk_gb_prog); for (i = 0; i < 9; i++) lk_glUniform1i(lk_gb_u[i], i);
  { static int fo = -1; if (fo < 0) { const char *e = getenv("LANDSTALKER_SWORDSH_FINE"); fo = e ? atoi(e) : 1; } lk_glUniform1i(lk_gb_u[45], 10); lk_glUniform1f(lk_gb_u[46], fo && lk_g5_fn ? 1.0f : 0.0f); }   /* LK_SWSHFINE v1 (=0: the old 16 unit cells) */
  lk_glUniform1i(lk_gb_u[18], 9); lk_glUniform4f(lk_gb_u[19], fu[16], fu[17], fu[18], fu[19]); lk_glUniform4f(lk_gb_u[20], fu[20], fu[21], fu[22], fu[23]); lk_glUniform1f(lk_gb_u[21], sw ? 1.0f : 0.0f); lk_glUniform1f(lk_gb_u[22], iu[0] ? 1.0f : 0.0f);
  lk_glUniform4fv(lk_gb_u[23], 96, lp); lk_glUniform4fv(lk_gb_u[24], 96, lc); lk_glUniform4fv(lk_gb_u[25], 96, lf); lk_glUniform4fv(lk_gb_u[26], 16, fg); lk_glUniform4fv(lk_gb_u[27], 16, fa);
  lk_glUniform1f(lk_gb_u[28], (float)iu[2]); lk_glUniform1f(lk_gb_u[29], fu[0]); lk_glUniform1f(lk_gb_u[30], fu[1]); lk_glUniform1f(lk_gb_u[31], fu[2]); lk_glUniform3f(lk_gb_u[32], fu[3], fu[4], fu[5]); lk_glUniform3f(lk_gb_u[33], fu[6], fu[7], fu[8]);
  lk_glUniform1f(lk_gb_u[34], (float)iu[5]); lk_glUniform1f(lk_gb_u[35], (float)iu[1]); lk_glUniform1f(lk_gb_u[36], fu[10]); lk_glUniform1f(lk_gb_u[37], fu[11]); lk_glUniform3f(lk_gb_u[38], fu[24], fu[25], fu[26]); lk_glUniform1f(lk_gb_u[39], (float)iu[12]);
  lk_glUniform1f(lk_gb_u[40], (float)iu[4]); lk_glUniform1f(lk_gb_u[41], fig ? 1.0f : 0.0f); lk_glUniform1f(lk_gb_u[42], (float)iu[9]); { static float rk = -1.0f; if (rk < 0.0f) { const char *e = getenv("LANDSTALKER_ROUNDFIG_K"); rk = e ? (float)atof(e) : 2.0f; if (rk < 0.0f) rk = 0.0f; } lk_glUniform1f(lk_gb_u[43], rk); } { static float rd = -1.0f; if (rd < 0.0f) { const char *e = getenv("LANDSTALKER_ROUNDFIG_DBG"); rd = e ? (float)atoi(e) : 0.0f; } lk_glUniform1f(lk_gb_u[44], rd); }
  lk_glUniform3f(lk_gb_u[10], base[0], base[1], base[2]); lk_glUniform1f(lk_gb_u[11], (float)iu[7]); lk_glUniform1f(lk_gb_u[12], bon ? lk_gb_k : 0.0f); lk_glUniform1f(lk_gb_u[13], lk_gb_r); lk_glUniform1f(lk_gb_u[14], lk_gb_d); lk_glUniform1f(lk_gb_u[15], lk_gl_postany ? 1.0f : 0.0f); lk_glUniform2f(lk_gb_u[16], phu, phv); lk_glUniform1f(lk_gb_u[17], iu[0] ? 1.0f : 0.0f);
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad);
  { static int tdb = -1; if (tdb < 0) { const char *e = getenv("LANDSTALKER_BOUNCE_DBG"); tdb = e ? atoi(e) : 0; } if (tdb >= 2 && lk_glFinish) { static double sum; static int n; Uint64 t0; lk_glFinish(); t0 = SDL_GetPerformanceCounter();
    lk_glUniform1f(lk_gb_u[9], 0.0f); lk_glBindFramebuffer(0x8D40, lk_gb_fa); lk_glViewport(0, 0, 113, 57); lk_glDrawArrays(0x0005, 0, 4); lk_glUniform1f(lk_gb_u[9], 1.0f); lk_glBindFramebuffer(0x8D40, lk_gb_fb); lk_glViewport(0, 0, 448, 224); lk_glDrawArrays(0x0005, 0, 4);
    lk_glFinish(); sum += (double)(SDL_GetPerformanceCounter() - t0) * 1e3 / (double)SDL_GetPerformanceFrequency(); if (++n >= 120) { printf("bounce: %%.3f ms per frame on the GPU (120 frame average)\n", sum / n); sum = 0.0; n = 0; } } }
  if (bon) { lk_glUniform1f(lk_gb_u[9], 0.0f); lk_glBindFramebuffer(0x8D40, lk_gb_fa); lk_glViewport(0, 0, 113, 57); lk_glDrawArrays(0x0005, 0, 4); }
  lk_glUniform1f(lk_gb_u[9], 1.0f); lk_glBindFramebuffer(0x8D40, lk_gb_fb); lk_glViewport(0, 0, 448, 224); lk_glDrawArrays(0x0005, 0, 4);
  lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0);
  for (i = 10; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); }
  return 1; }

static long lk_glt_fb[8]; static long lk_glt_n, lk_glt_skip, lk_glt_px, lk_glt_ex, lk_glt_o1, lk_glt_bad, lk_glt_xc, lk_glt_xf[8], lk_glt_cpx[3], lk_glt_cbad[3]; static int lk_glt_shown;
static int lk_glt_pass(int real) {   /* inside lk_gpu_present after SDL's state is saved; compare (real 0): before the picture upload, unit 0 = recorded unlit picture;
     real (1): after it, unit 0 = the presented picture; returns 1 when lk_glt_out holds the lit picture.  Leaves texture unit 0 active, vertex array enabled */
  float fu[64], lp[96 * 4], lc[96 * 4], lf[96 * 4], fg[16 * 4], fa[16 * 4]; int iu[32], L, i, bx, by, u0 = 1 << 30, u1 = -(1 << 30), v0 = 1 << 30, v1 = -(1 << 30); long fr = platform_frame_number();
  lkGLint fb0 = 0, tb[LK_GLT_NT]; static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 }; static uint32_t pk[5][1024], bt[38 * 76], bl0[38 * 76], bl1[38 * 76], *rb;
  { extern long lk_gl_realcap; int md = lk_gl_getmode(); if (!(real ? (md == 1 || lk_gl_realcap == fr - 1) : md == 2) || lk_glt_st < 0 || !lk_gl_frame(fr, fu, iu, lp, lc, lf, fg, fa)) return 0; }   /* v5: a real frame is lit even if the mode switched after its rows */
  if (lk_glt_st == 0) { lk_glt_st = lk_glt_init(); if (lk_glt_st < 0) return 0; }
  for (i = 0; i < LK_GLT_NT; i++) { lk_glActiveTexture(0x84C0 + i); lk_glGetIntegerv(0x8069, &tb[i]); }
  /* visible blocks: upload what changed */
  for (L = 0; L < 224; L++) { int U = (int)(int16_t)(lk_gl_row[L] & 0xFFFF), V = (int)(int16_t)(lk_gl_row[L] >> 16); if (U < u0) u0 = U; if (U + iu[7] - 1 > u1) u1 = U + iu[7] - 1; if (V < v0) v0 = V; if (V > v1) v1 = V; }
  { int g5r = real && lk_g5_realon(); static int g5prev = -1; if (g5r != g5prev) { memset(lk_glt_ver, 0, sizeof lk_glt_ver); memset(lk_g5_bt, 0, sizeof lk_g5_bt); memset(lk_g5_bk, 0, sizeof lk_g5_bk); g5prev = g5r; }   /* a switch GPU <-> GPU+: everything fresh */
    if (g5r) { lk_g5_prep(); if (lk_g5_qst > 0) lk_g5_qpoll(); }   /* v5 GL5c */
  for (by = 0; by < 38; by++) for (bx = 0; bx < 76; bx++) { unsigned v; int nl = 0; uint32_t a = 0, b2 = 0;
    if (g5r) { bt[by * 76 + bx] = lk_g5_bt[by][bx]; bl0[by * 76 + bx] = lk_g5_l0[by][bx]; bl1[by * 76 + bx] = lk_g5_l1[by][bx]; continue; }
    v = lk_gl_bver(bx, by);
    if (v) lk_gl_blist(bx, by, &a, &b2, &nl);
    bt[by * 76 + bx] = (v ? 0xFFu : 0u) | (lk_gl_bsg(bx, by) ? 0xFF00u : 0u) | ((uint32_t)nl << 16); bl0[by * 76 + bx] = a; bl1[by * 76 + bx] = b2;
    if (v && v != lk_glt_ver[by][bx] && bx * 32 + 31 >= u0 && bx * 32 <= u1 && by * 32 + 31 >= v0 && by * 32 <= v1) { static const int pt[5] = { 3, 5, 6, 7, 8 }; int k;
      lk_gl_bpack(bx, by, pk); if (lk_g5_want()) lk_g5_queue(bx, by, pk);   /* v5 GL5a compare */
      for (k = 0; k < 5; k++) { lk_glActiveTexture(0x84C0 + pt[k]); lk_glBindTexture(0x0DE1, lk_glt_t[pt[k]]); lk_glTexSubImage2D(0x0DE1, 0, bx * 32, by * 32, 32, 32, 0x1908, 0x1401, pk[k]); }
      lk_glt_ver[by][bx] = v; } }
  lk_glActiveTexture(0x84C4); lk_glBindTexture(0x0DE1, lk_glt_t[4]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 76, 38, 0x1908, 0x1401, bt);
  lk_glActiveTexture(0x84C9); lk_glBindTexture(0x0DE1, lk_glt_t[9]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 76, 38, 0x1908, 0x1401, bl0); lk_glTexSubImage2D(0x0DE1, 0, 76, 0, 76, 38, 0x1908, 0x1401, bl1);
  lk_g5_lf = lf;   /* LK_GLWIDE v2 */
  if (lk_g5_n) lk_g5_run(lp, lc);   /* v5 GL5a compare */
  if (g5r) lk_g5_real(u0, u1, v0, v1, lp, lc, bt, bl0, bl1); }   /* v5 GL5c */
  if (real && (lk_gl_postany || lk_gl_postprev)) { lk_glActiveTexture(0x84CA); lk_glBindTexture(0x0DE1, lk_glt_t[10]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x80E1, 0x1401, lk_gl_post[0]); lk_glTexSubImage2D(0x0DE1, 0, 0, 224, 448, 224, 0x80E1, 0x1401, lk_gl_post[1]); }
  lk_glActiveTexture(0x84CB); lk_glBindTexture(0x0DE1, lk_glt_t[11]); if (iu[10]) lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x190A, 0x1401, lk_gl_fmk());
  lk_glActiveTexture(0x84C2); lk_glBindTexture(0x0DE1, lk_glt_t[2]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 224, 1, 0x1908, 0x1401, lk_gl_row);
  lk_gl_clstag(lk_glt_ct); lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, lk_glt_t[1]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x1908, 0x1401, lk_glt_ct);
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
  { extern int lk_gsw_frame(int real, int swon); lk_glUniform1f(lk_glt_u[49], lk_gsw_frame(real, iu[4]) ? 1.0f : 0.0f); }   /* GL5e: the post pass adds the sword light with its shadow */
  lk_glUniform4fv(lk_glt_u[43], 96, lp); lk_glUniform4fv(lk_glt_u[44], 96, lc); lk_glUniform4fv(lk_glt_u[45], 96, lf); lk_glUniform4fv(lk_glt_u[46], 16, fg); lk_glUniform4fv(lk_glt_u[47], 16, fa);
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glBindFramebuffer(0x8D40, lk_glt_fbo); lk_glViewport(0, 0, 448, 224);
  if (real && lk_glt_qst == 0) lk_glt_qinit();
  if (real && lk_glt_qst > 0) { lk_glt_qresult(); if (!lk_glt_qpend[lk_glt_qi]) { lk_glBeginQuery(0x88BF, lk_glt_q[lk_glt_qi]); } else real |= 2; }   /* v5 watchdog (2: slot still busy, no query this frame) */
  lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad); lk_glDrawArrays(0x0005, 0, 4);
  if (real && lk_glt_qst > 0 && !(real & 2)) { lk_glEndQuery(0x88BF); lk_glt_qpend[lk_glt_qi] = 1; lk_glt_qi ^= 1; }
  real &= 1;
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
    MODULE = MODULE.replace("@SHADERB@", "\n".join('"%s\\n"' % l.replace("\\", "\\\\").replace('"', '\\"') for l in SHB.strip("\n").split("\n")))
    MODULE = MODULE.replace("@SHADER5@", "\n".join('"%s\\n"' % l.replace("\\", "\\\\").replace('"', '\\"') for l in SH5.strip("\n").split("\n")))
    MODULE = MODULE.replace("@SHADER@", "\n".join('"%s\\n"' % l.replace("\\", "\\\\").replace('"', '\\"') for l in SHADER.strip("\n").split("\n")))
    a = "static long lk_gpu_frames;\n"
    assert s.count(a) == 1, "platform_sdl.c: LK_GPU module not found (patch_gpu.py first)"
    s = s.replace(a, MODULE + a)
    a = "  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_gpu_tex); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, sw, 224, 0x80E1, 0x1401, fb);\n"
    assert s.count(a) == 1, "platform_sdl.c: GPU upload line changed"
    s = s.replace(a, "  lk_glt_pass(0);   /* %s: compare harness */\n" % VER + a + "  if (lk_glt_pass(1)) { int lk_gbok = lk_gb_run(); lk_glBindTexture(0x0DE1, lk_gbok ? lk_gb_out : lk_glt_out); }   /* %s: the filters read the GPU-lit picture */\n" % VER)
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
