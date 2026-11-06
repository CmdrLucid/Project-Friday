#!/usr/bin/env python3
"""Option 'Cloud Shadows' (2026-11-06, user: modern effects list item 1 'Wolkenschatten', 'wolken ja').
Outdoors (tileset 0 / 7 / 12 / 13 / 14 / 17 like Lighting's sun rooms, not the intro 139..143 / 148, not the dark docks 643) soft cloud shadows drift over
the map: a tileable fractal noise (128 x 128, two octaves, smooth) laid on the room picture (image coordinates U / V, so the shadows stay on the world while
the camera scrolls), 1 texel = 8 px (clouds ~170..340 px), drifting slowly to the lower right (wind); cover (share of the picture in shadow) ~35 %%, soft edges.
A shadowed pixel gets darker (at most LANDSTALKER_CLOUD_K, default 0.20) and a touch bluer.  Map pixels of layers, sprites and neighbour rooms are darkened;
window pixels (HUD, text box) and black lines stay.  Picture only.  Independent of Lighting.  Not with HD graphics.
Option: Options > Graphics > Cloud Shadows (id 53, ~/.landstalker_clouds, env LANDSTALKER_CLOUDS=0|1 wins), default On.
Test aids: LANDSTALKER_CLOUD_K=<0..0.6>, LANDSTALKER_CLOUD_COVER=<0..1> (default 0.35), LANDSTALKER_CLOUD_SPEED=<px per frame> (default 0.12), LANDSTALKER_CLOUD_FORCE=1 (every room).
Needs patch_own.py, patch_water.py before it.  Idempotent.  usage: patch_clouds.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_CLOUDS v1"

p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, ("vdp_render.c: anchor not found once", a[:80])
    s = s.replace(a, b)

if VER not in s:
    MODULE = r'''/* ---- %s: soft cloud shadows drifting over outdoor maps (tools/patch_clouds.py) ---- */
static int lk_cs_o = -1;
int lk_cs_get(void) { if (lk_cs_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_CLOUDS"); char pth[512]; FILE *f; int v = 1; snprintf(pth, sizeof pth, "%%s/.landstalker_clouds", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%%d", &v) != 1) v = 1; fclose(f); } if (e) v = atoi(e); lk_cs_o = v ? 1 : 0; } return lk_cs_o; }
void lk_cs_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_cs_get(); lk_cs_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_clouds", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_cs_o); fclose(f); } }
#define LK_CS_N 128   /* noise texture size (tiles) */
static uint8 lk_cs_tex[LK_CS_N * LK_CS_N];   /* shadow strength 0..255 per texel (cover + soft edge already applied) */
static int lk_cs_ready, lk_cs_room = -2, lk_cs_out, lk_cs_k = -1, lk_cs_ox, lk_cs_oy; static long lk_cs_frame = -1; static float lk_cs_sp = 0.12f;
static float lk_cs_lat(const float *g, int n, float x, float y) {   /* smooth (smoothstep) interpolation of an n x n random lattice, tileable */
  int x0 = (int)floorf(x), y0 = (int)floorf(y); float fx = x - (float)x0, fy = y - (float)y0, a, b, c, d;
  fx = fx * fx * (3.0f - 2.0f * fx); fy = fy * fy * (3.0f - 2.0f * fy);
  x0 = ((x0 %% n) + n) %% n; y0 = ((y0 %% n) + n) %% n;
  a = g[y0 * n + x0]; b = g[y0 * n + (x0 + 1) %% n]; c = g[((y0 + 1) %% n) * n + x0]; d = g[((y0 + 1) %% n) * n + (x0 + 1) %% n];
  return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fy; }
static void lk_cs_init(void) {
  static float g1[6 * 6], g2[12 * 12], g3[24 * 24]; float v[LK_CS_N * LK_CS_N], th, srt[LK_CS_N * LK_CS_N / 16]; uint32_t rng = 20261106u; int i, j, ns = 0;
  const char *e = getenv("LANDSTALKER_CLOUD_COVER"); float cover = e ? (float)atof(e) : 0.35f;
  if (cover < 0.0f) cover = 0.0f; if (cover > 1.0f) cover = 1.0f;
  #define LK_CS_R() (rng = rng * 1664525u + 1013904223u, (float)(rng >> 8) * (1.0f / 16777216.0f))
  for (i = 0; i < 36; i++) g1[i] = LK_CS_R(); for (i = 0; i < 144; i++) g2[i] = LK_CS_R(); for (i = 0; i < 576; i++) g3[i] = LK_CS_R();
  #undef LK_CS_R
  for (j = 0; j < LK_CS_N; j++) for (i = 0; i < LK_CS_N; i++) {
    float x = (float)i / (float)LK_CS_N, y = (float)j / (float)LK_CS_N;
    v[j * LK_CS_N + i] = 0.60f * lk_cs_lat(g1, 6, x * 6.0f, y * 6.0f) + 0.28f * lk_cs_lat(g2, 12, x * 12.0f, y * 12.0f) + 0.12f * lk_cs_lat(g3, 24, x * 24.0f, y * 24.0f); }
  for (i = 0; i < LK_CS_N * LK_CS_N; i += 16) srt[ns++] = v[i];   /* threshold for the wanted cover from a sample of the values */
  for (i = 1; i < ns; i++) { float t = srt[i]; j = i - 1; while (j >= 0 && srt[j] > t) { srt[j + 1] = srt[j]; j--; } srt[j + 1] = t; }
  th = srt[(int)((1.0f - cover) * (float)(ns - 1))];
  for (i = 0; i < LK_CS_N * LK_CS_N; i++) { float t = (v[i] - th) / 0.07f; if (t < 0.0f) t = 0.0f; if (t > 1.0f) t = 1.0f; t = t * t * (3.0f - 2.0f * t); lk_cs_tex[i] = (uint8)(t * 255.0f); }   /* soft edge over 0.07 of the value range */
  lk_cs_ready = 1; }
static int lk_cs_isout(int room) {   /* the same rooms as Lighting's sun (lk_lt_isout) */
  int ts;
  if (room < 0 || (room >= 139 && room <= 143) || room == 148 || room == 643) return 0;
  ts = OB(OL(0xA0A00) + 8u * (uint32_t)room + 4u) & 0x1F;
  return ts == 0 || ts == 7 || ts == 12 || ts == 13 || ts == 14 || ts == 17;
}
static void lk_cs_step(void) {
  lk_cs_frame = platform_frame_number();
  if (!lk_cs_ready) lk_cs_init();
  if (lk_cs_k < 0) { const char *e = getenv("LANDSTALKER_CLOUD_K"), *f = getenv("LANDSTALKER_CLOUD_SPEED"); float k = e ? (float)atof(e) : 0.20f; if (k < 0.0f) k = 0.0f; if (k > 0.6f) k = 0.6f; lk_cs_k = (int)(k * 256.0f); if (f) lk_cs_sp = (float)atof(f); }
  if (lk_o_room != lk_cs_room) { lk_cs_room = lk_o_room; lk_cs_out = lk_cs_isout(lk_o_room) || getenv("LANDSTALKER_CLOUD_FORCE"); }
  { float t = (float)lk_cs_frame * lk_cs_sp; lk_cs_ox = (int)(t * 256.0f); lk_cs_oy = (int)(t * 0.55f * 256.0f); }   /* wind: towards the lower right of the picture, in 1/256 px */
}
static int lk_cs_linebegin(void) {
  if (!lk_cs_get() || lk_hd_n || lk_o_mode != 2) return 0;
  if (lk_cs_frame != platform_frame_number()) lk_cs_step();
  return lk_cs_out && lk_cs_k > 0;
}
static int lk_cs_pix(int U, int V, int col) {   /* U / V: image coordinates of the pixel; 1 texel = 8 picture px (texture period 1024 px, clouds ~170..340 px) */
  int fu = (U << 5) - (lk_cs_ox >> 3), fv = (V << 5) - (lk_cs_oy >> 3), iu = fu >> 8, iv = fv >> 8, au = fu & 255, av = fv & 255, s0, s1, sh, k, r, g, b; uint32_t c = (uint32_t)col;
  iu &= LK_CS_N - 1; iv &= LK_CS_N - 1;
  { int iu1 = (iu + 1) & (LK_CS_N - 1), iv1 = (iv + 1) & (LK_CS_N - 1);
    s0 = lk_cs_tex[iv * LK_CS_N + iu] * (256 - au) + lk_cs_tex[iv * LK_CS_N + iu1] * au;
    s1 = lk_cs_tex[iv1 * LK_CS_N + iu] * (256 - au) + lk_cs_tex[iv1 * LK_CS_N + iu1] * au;
    sh = ((s0 >> 8) * (256 - av) + (s1 >> 8) * av) >> 8; }
  if (sh <= 0) return col;
  k = sh * lk_cs_k >> 8;   /* darkening 0..lk_cs_k (of 256) */
  r = (int)((c >> 16) & 255); g = (int)((c >> 8) & 255); b = (int)(c & 255);
  r = r * (256 - k) >> 8; g = g * (256 - k * 15 / 16) >> 8; b = b * (256 - k * 3 / 4) >> 8;   /* a touch bluer in the shade */
  return (int)((c & 0xFF000000u) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b); }

''' % VER
    a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
    rep(a, MODULE + a)
    a = "    int lk_wr_ln = lk_wr_linebegin(line);   /* LK_WATER v1 */\n"
    rep(a, a + "    int lk_cs_ln = lk_cs_linebegin();   /* %s */\n" % VER)
    a = "      if (lk_sfx_ln && !black && src != 4) col = lk_sfx_pix(line, i, src == 1 ? sp : 0, col);   /* LK_SWORDFX v1 */\n"
    rep(a, "      if (lk_cs_ln && !black && (src == 1 || src == 2 || src == 3 || src == 6)) col = lk_cs_pix(ubase + x - lk_sm_sxn, vbase - lk_sm_syn, col);   /* %s */\n" % VER + a)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
else:
    print("vdp_render.c already patched:", VER)
