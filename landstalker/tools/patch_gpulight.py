#!/usr/bin/env python3
"""GPU lighting, stage GL1 (2026-11-06, user: '1 umsetzen danach 2' = lighting on the GPU, docs/RENDERER_IDEAS.md 'Step 3 plan: deferred lighting').
GL1 = the harness, NOTHING changes for the player: with LANDSTALKER_GPULT=2 (compare mode, test aid) the own map renderer records per picture pixel
(1) the colour BEFORE Lighting (lk_lt_pix / lk_lt_voidglow), (2) the colour after it (the CPU result), (3) a light class (0 none, 1 lk_lt_pix,
3 lk_lt_voidglow) + flags of the paths GL1 does not do yet, and per line the room picture position (U = ru + i, V = rv).  At the next present the GPU
lights the recorded unlit picture in an offscreen pass (FBO 448 x 224, one fragment shader) from the light block cache (lk_lt_b, uploaded per 32 x 32
block as a room picture texture face / sun / sunn / ao) and the frame's light state; the result is read back and compared with the CPU colours.
GL1 covers: blocks not computed yet (base light), outdoor sun + Day / Night (incl. the crossfade to the next sun direction), corner shadows (ao),
pixels without geometry, rooms with flames where no flame reaches the pixel.  Not yet (counted as 'skipped'): figure pixels, figure sun shadows,
flame terms, ambient particles (pixel flags), key light rooms, shafts, sword glow (whole frames).
Console every 300 compared frames: 'gpult: frames F skipped S pixels P exact E off1 O1 worse W excluded X (fig A figsun B flame C particle D)'
plus the first 12 pixels with a difference > 1 ('gpult: diff frame .. x .. line .. U .. V .. class .. cpu RRGGBB gpu RRGGBB unlit RRGGBB').
Needs the GPU filter path (patch_gpu.py, option GPU Filters On) and a window (the GL context): LANDSTALKER_HIDDEN=1 creates the window hidden (test aid).
Needs patch_lights.py, patch_bootcol.py, patch_gpu.py before it.  Idempotent.  usage: patch_gpulight.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_GPULT v1"

# ---------------------------------------------------------------- vdp_render.c: capture + block access
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, ("vdp_render.c: anchor not found once", a[:90], s.count(a))
    s = s.replace(a, b)

if VER not in s:
    MODULE = r'''/* ---- %s: GPU lighting harness (tools/patch_gpulight.py): capture of the unlit / lit map pixels + access to the light block cache ---- */
static int lk_gl_mode = -1;   /* LANDSTALKER_GPULT: 0 off, 2 compare (GL1) */
static int lk_gl_pf;          /* flags of the current lk_lt_pix call: 1 figure pixel, 2 figure sun shadow, 4 a flame term, 8 particle */
static unsigned lk_gl_sunver; /* bumped when the blocks take over the next sun direction (memcpy sun <- sunn) */
uint32_t lk_gl_unlit[224 * 448], lk_gl_ref[224 * 448]; uint8_t lk_gl_cls[224 * 448], lk_gl_flg[224 * 448]; uint32_t lk_gl_row[224]; long lk_gl_rowfr[224]; int lk_gl_w; long lk_gl_capfr = -9;
int lk_gl_getmode(void) { if (lk_gl_mode < 0) { const char *e = getenv("LANDSTALKER_GPULT"); lk_gl_mode = e ? atoi(e) : 0; if (lk_gl_mode != 2) lk_gl_mode = 0; } return lk_gl_mode; }
static void lk_gl_put(int line, int i, int cls, int U, int V, int c0, int c1, int w) {
  int o = line * 448 + i;
  lk_gl_unlit[o] = (uint32_t)c0; lk_gl_ref[o] = (uint32_t)c1; lk_gl_cls[o] = (uint8_t)cls;
  lk_gl_flg[o] = (uint8_t)(cls ? (lk_gl_pf | ((lk_am_dn && lk_am_map[((V & 511) << 9) | (U & 511)]) ? 8 : 0)) : 0);
  if (i == 0 || lk_gl_rowfr[line] != platform_frame_number()) { lk_gl_row[line] = ((uint32_t)(uint16_t)(int16_t)(U - i)) | ((uint32_t)(uint16_t)(int16_t)V << 16); lk_gl_rowfr[line] = platform_frame_number(); }
  lk_gl_capfr = platform_frame_number(); lk_gl_w = w; }
/* for the GL side (platform_sdl.c, once per present): 1 = the last frame was captured; fills the frame's light state.
   fu: 0 amb, 1 sS, 2 sK, 3..5 amb3, 6..8 sun3, 9 dn_mix;  iu: 0 sun, 1 key, 2 nl, 3 nsh, 4 swon, 5 dn_on, 6 odcap == 0, 7 width, 8 skip reason bits (1 key, 2 shafts, 4 sword) */
int lk_gl_frame(long fr, float *fu, int *iu) {
  int L, k;
  if (lk_gl_capfr != fr - 1 || lk_gl_w < 1 || lk_gl_w > 448) return 0;
  for (L = 0; L < 224; L++) if (lk_gl_rowfr[L] != lk_gl_capfr) memset(lk_gl_cls + L * 448, 0, 448);   /* lines not captured this frame: no light */
  fu[0] = lk_lt_amb < 0.0f ? 0.85f : lk_lt_amb; fu[1] = lk_lt_sS; fu[2] = lk_lt_sK; for (k = 0; k < 3; k++) { fu[3 + k] = lk_dn_amb3[k]; fu[6 + k] = lk_dn_sun3[k]; } fu[9] = (float)lk_dn_mix;
  iu[0] = lk_lt_sun; iu[1] = lk_lt_key; iu[2] = lk_lt_nl; iu[3] = lk_lt_nsh; iu[4] = lk_lt_swon; iu[5] = lk_dn_on; iu[6] = lk_lt_odcap == 0; iu[7] = lk_gl_w;
  iu[8] = (lk_lt_key ? 1 : 0) | (lk_lt_nsh ? 2 : 0) | (lk_lt_swon ? 4 : 0);
  return 1; }
/* block version (0 = no block) and its packed plane A: face | sun << 8 | sunn << 16 | ao << 24 per pixel (row-major 32 x 32) */
unsigned lk_gl_bver(int bx, int by) { const lk_lt_blk *b; uintptr_t v;
  if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH || !(b = lk_lt_b[by][bx])) return 0;
  v = (uintptr_t)b; return ((unsigned)v ^ (unsigned)(v >> 32) ^ ((unsigned)b->sungen * 2654435761u) ^ (lk_gl_sunver * 40503u) ^ ((unsigned)lk_lt_gen * 97u)) | 1u; }
int lk_gl_bsg(int bx, int by) { const lk_lt_blk *b; if (bx < 0 || by < 0 || bx >= LK_LT_BW || by >= LK_LT_BH || !(b = lk_lt_b[by][bx])) return 0; return b->sungen == lk_dn_gen; }
void lk_gl_bpack(int bx, int by, uint32_t *o) { const lk_lt_blk *b = lk_lt_b[by][bx]; int i;
  for (i = 0; i < 1024; i++) o[i] = (uint32_t)b->face[i] | ((uint32_t)b->sun[i] << 8) | ((uint32_t)b->sunn[i] << 16) | ((uint32_t)b->ao[i] << 24); }

''' % VER
    a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
    rep(a, MODULE + a)
    a = "/* ---- LK_LIGHTS v8: lighting from flames"
    rep(a, "static int lk_gl_pf; static unsigned lk_gl_sunver;   /* %s (tools/patch_gpulight.py): used inside the Lighting code */\n" % VER + a)
    # per line: capture on?
    a = "int lk_lt_ln = lk_lt_linebegin();"
    rep(a, a + " int lk_gl_cap = lk_gl_getmode() == 2 && lk_lt_ln && !lk_hd_n && !lk_lt_dbg && w <= 448 && line >= 0 && line < 224;   /* %s */" % VER)
    # around the lighting call of the composed pixel
    a = "      if (lk_lt_ln && !black && (src == 1 || src == 2 || src == 3)) col = lk_lt_pix("
    rep(a, "      int lk_gl_c0 = col; lk_gl_pf = 0;   /* %s */\n" % VER + a)
    a = "      else if (lk_lt_ln && !black && (src == 0 || src == 6 || src == 7)) col = lk_lt_voidglow("
    i0 = s.index(a); i1 = s.index("\n", i0) + 1
    s = s[:i1] + ("      if (lk_gl_cap) lk_gl_put(line, i, black ? 0 : (src >= 1 && src <= 3) ? 1 : (src == 0 || src == 6 || src == 7) ? 3 : 0, ubase + x - lk_sm_sxn, vbase - lk_sm_syn, lk_gl_c0, col, w);   /* %s */\n" % VER) + s[i1:]
    # flags inside lk_lt_pix
    rep("if ((sp & 0x200) && (j = lk_lt_figat(x, line)) >= 0) {", "if ((sp & 0x200) && (j = lk_lt_figat(x, line)) >= 0) { lk_gl_pf |= 1;")
    rep("if (lk_lt_figsun(px, py, (float)b->z[i])) u = 0.0f; }", "if (lk_lt_figsun(px, py, (float)b->z[i])) { u = 0.0f; lk_gl_pf |= 2; } }")
    rep("      if (t <= 0.0f) continue;\n", "      if (t <= 0.0f) continue;\n      lk_gl_pf |= 4;   /* %s */\n" % VER)
    rep("memcpy(lk_lt_sd, lk_lt_sdn, sizeof lk_lt_sd);", "memcpy(lk_lt_sd, lk_lt_sdn, sizeof lk_lt_sd); lk_gl_sunver++;")
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
else:
    print("vdp_render.c already patched:", VER)

# ---------------------------------------------------------------- platform_sdl.c: the GPU pass + compare
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()

SHADER = r'''
uniform sampler2D unl; uniform sampler2D cls; uniform sampler2D rows; uniform sampler2D roomA; uniform sampler2D btab;
uniform float uAmb; uniform float uSS; uniform float uSK; uniform vec3 uAmb3; uniform vec3 uSun3; uniform float uMix;
uniform float uSun; uniform float uNl; uniform float uDn; uniform float uOd0;
float B(float v) { return floor(v * 255.0 + 0.5); }
vec3 lit(vec3 c, vec3 f) { return min(floor(c * f), vec3(255.0)); }
void main() {
  vec2 fc = floor(gl_FragCoord.xy); float line = fc.y;
  vec2 tc = (fc + 0.5) / vec2(448.0, 224.0);
  vec3 c = vec3(B(texture2D(unl, tc).r), B(texture2D(unl, tc).g), B(texture2D(unl, tc).b));
  float cl = B(texture2D(cls, tc).r);
  vec3 o = c;
  if (cl > 0.5 && cl < 3.5) {
    vec4 ro = texture2D(rows, vec2((line + 0.5) / 224.0, 0.5));
    float U = B(ro.r) + 256.0 * B(ro.g), V = B(ro.b) + 256.0 * B(ro.a);
    if (U >= 32768.0) U -= 65536.0; if (V >= 32768.0) V -= 65536.0;
    U += fc.x;
    float bx = floor(U / 32.0), by = floor(V / 32.0), have = 0.0, sg = 0.0;
    if (bx >= 0.0 && by >= 0.0 && bx < 76.0 && by < 38.0) { vec4 bt = texture2D(btab, (vec2(bx, by) + 0.5) / vec2(76.0, 38.0)); have = bt.r > 0.5 ? 1.0 : 0.0; sg = bt.g > 0.5 ? 1.0 : 0.0; }
    vec3 a = vec3(uAmb * 0.93, uAmb * 0.96, uAmb * 1.06);
    if (uNl < 0.5 && uSun < 0.5) a = vec3(1.0);
    if (cl > 2.5) o = c;   /* void glow without shafts / particles: unchanged */
    else if (have < 0.5) {
      if (uSun < 0.5 && uOd0 > 0.5) { if (uNl > 0.5) o = lit(c, a); }
      else if (uSun > 0.5 && uDn < 0.5 && uOd0 > 0.5) o = lit(c, min(vec3(uSS * 0.95 + uSK, uSS * 0.98 + uSK * 0.97, uSS * 1.06 + uSK * 0.90), vec3(2.4)));
      else if (uSun > 0.5 && uDn > 0.5) o = lit(c, min(uAmb3 + uSun3, vec3(2.4)));
    } else {
      vec4 A = texture2D(roomA, (vec2(U, V) + 0.5) / vec2(2432.0, 1216.0));
      float face = B(A.r), sun = B(A.g), sunn = B(A.b), ao = B(A.a);
      if (face < 0.5) o = c;
      else {
        if (uSun > 0.5) { float u = sun * (1.0 / 255.0);
          if (uMix > 0.5 && sg > 0.5) u += (sunn * (1.0 / 255.0) - u) * uMix * (1.0 / 256.0);
          if (uDn > 0.5) a = uAmb3 + uSun3 * u;
          else { float k = uSK * u; a = vec3(uSS * 0.95 + k, uSS * 0.98 + k * 0.97, uSS * 1.06 + k * 0.90); } }
        if (ao < 254.5) a *= ao * (1.0 / 255.0);
        o = lit(c, min(a, vec3(2.4)));
      }
    }
  }
  gl_FragColor = vec4(o / 255.0, 1.0); }
'''

if VER not in s:
    MODULE = r'''/* ---- %s: GPU lighting harness GL1 (tools/patch_gpulight.py): offscreen light pass + compare with the CPU result ---- */
extern int lk_gl_getmode(void); extern int lk_gl_frame(long fr, float *fu, int *iu); extern unsigned lk_gl_bver(int bx, int by); extern int lk_gl_bsg(int bx, int by); extern void lk_gl_bpack(int bx, int by, uint32_t *o);
extern uint32_t lk_gl_unlit[224 * 448], lk_gl_ref[224 * 448]; extern uint8_t lk_gl_cls[224 * 448], lk_gl_flg[224 * 448]; extern uint32_t lk_gl_row[224];
LKGL_FN(void, glUniform3f, (lkGLint, lkGLfloat, lkGLfloat, lkGLfloat)); LKGL_FN(void, glGenFramebuffers, (lkGLsizei, lkGLuint *)); LKGL_FN(void, glBindFramebuffer, (lkGLenum, lkGLuint)); LKGL_FN(void, glFramebufferTexture2D, (lkGLenum, lkGLenum, lkGLenum, lkGLuint, lkGLint)); LKGL_FN(lkGLenum, glCheckFramebufferStatus, (lkGLenum));
static int lk_glt_st;   /* 0 not tried, 1 ready, -1 failed */
static lkGLuint lk_glt_prog, lk_glt_fbo, lk_glt_out, lk_glt_unl, lk_glt_cls, lk_glt_rows, lk_glt_roomA, lk_glt_btab; static lkGLint lk_glt_u[16];
static unsigned lk_glt_ver[38][76];
static const char *lk_glt_fs = "#version 120\n" @SHADER@;
static lkGLuint lk_glt_tex(int w, int h, lkGLenum ifmt, lkGLenum fmt) { lkGLuint t; lk_glGenTextures(1, &t); lk_glBindTexture(0x0DE1, t); lk_glTexImage2D(0x0DE1, 0, (lkGLint)ifmt, w, h, 0, fmt, 0x1401, 0);
  lk_glTexParameteri(0x0DE1, 0x2801, 0x2600); lk_glTexParameteri(0x0DE1, 0x2800, 0x2600); lk_glTexParameteri(0x0DE1, 0x2802, 0x812F); lk_glTexParameteri(0x0DE1, 0x2803, 0x812F); return t; }
static int lk_glt_init(void) {   /* inside lk_gpu_present (SDL's state saved, texture unit 0 active) */
  lkGLint ok = 0, t0 = 0; lkGLuint vs, fs; char log[1024];
  *(void **)&lk_glGenFramebuffers = lk_gpu_fn("glGenFramebuffers"); *(void **)&lk_glBindFramebuffer = lk_gpu_fn("glBindFramebuffer");
  *(void **)&lk_glFramebufferTexture2D = lk_gpu_fn("glFramebufferTexture2D"); *(void **)&lk_glCheckFramebufferStatus = lk_gpu_fn("glCheckFramebufferStatus");
  if (!lk_glGenFramebuffers) { *(void **)&lk_glGenFramebuffers = lk_gpu_fn("glGenFramebuffersEXT"); *(void **)&lk_glBindFramebuffer = lk_gpu_fn("glBindFramebufferEXT");
    *(void **)&lk_glFramebufferTexture2D = lk_gpu_fn("glFramebufferTexture2DEXT"); *(void **)&lk_glCheckFramebufferStatus = lk_gpu_fn("glCheckFramebufferStatusEXT"); }
  *(void **)&lk_glUniform3f = lk_gpu_fn("glUniform3f");
  if (!lk_glUniform3f || !lk_glGenFramebuffers || !lk_glBindFramebuffer || !lk_glFramebufferTexture2D || !lk_glCheckFramebufferStatus) { printf("gpult: no framebuffer objects\n"); return -1; }
  { static const char *vsrc = "#version 120\nvoid main() { gl_Position = gl_Vertex; }\n"; vs = lk_glCreateShader(0x8B31); lk_glShaderSource(vs, 1, &vsrc, 0); lk_glCompileShader(vs); lk_glGetShaderiv(vs, 0x8B81, &ok); if (!ok) return -1; }
  fs = lk_glCreateShader(0x8B30); lk_glShaderSource(fs, 1, &lk_glt_fs, 0); lk_glCompileShader(fs); lk_glGetShaderiv(fs, 0x8B81, &ok);
  if (!ok) { lk_glGetShaderInfoLog(fs, sizeof log, 0, log); printf("gpult: light shader failed: %%s\n", log); return -1; }
  lk_glt_prog = lk_glCreateProgram(); lk_glAttachShader(lk_glt_prog, vs); lk_glAttachShader(lk_glt_prog, fs); lk_glLinkProgram(lk_glt_prog); lk_glGetProgramiv(lk_glt_prog, 0x8B82, &ok);
  if (!ok) { lk_glGetProgramInfoLog(lk_glt_prog, sizeof log, 0, log); printf("gpult: link failed: %%s\n", log); return -1; }
  { static const char *un[] = { "unl", "cls", "rows", "roomA", "btab", "uAmb", "uSS", "uSK", "uAmb3", "uSun3", "uMix", "uSun", "uNl", "uDn", "uOd0", 0 }; int i; for (i = 0; un[i]; i++) lk_glt_u[i] = lk_glGetUniformLocation(lk_glt_prog, un[i]); }
  lk_glGetIntegerv(0x8069, &t0);
  lk_glt_out = lk_glt_tex(448, 224, 0x1908, 0x1908); lk_glt_unl = lk_glt_tex(448, 224, 0x1908, 0x80E1); lk_glt_cls = lk_glt_tex(448, 224, 0x1909, 0x1909);
  lk_glt_rows = lk_glt_tex(224, 1, 0x1908, 0x1908); lk_glt_roomA = lk_glt_tex(2432, 1216, 0x1908, 0x1908); lk_glt_btab = lk_glt_tex(76, 38, 0x1908, 0x1908);
  lk_glBindTexture(0x0DE1, (lkGLuint)t0);
  { lkGLint fb0 = 0; lkGLenum st; lk_glGetIntegerv(0x8CA6, &fb0); lk_glGenFramebuffers(1, &lk_glt_fbo); lk_glBindFramebuffer(0x8D40, lk_glt_fbo); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_glt_out, 0);
    st = lk_glCheckFramebufferStatus(0x8D40); lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); if (st != 0x8CD5) { printf("gpult: framebuffer incomplete %%04X\n", (unsigned)st); return -1; } }
  memset(lk_glt_ver, 0, sizeof lk_glt_ver);
  printf("gpult: GL1 compare ready\n"); return 1; }
static long lk_glt_n, lk_glt_skip, lk_glt_px, lk_glt_ex, lk_glt_o1, lk_glt_bad, lk_glt_xc, lk_glt_xf[4]; static int lk_glt_shown;
static void lk_glt_pass(void) {   /* called inside lk_gpu_present after SDL's state is saved; leaves texture unit 0 active, vertex array enabled */
  float fu[16]; int iu[16], L, i, bx, by, u0 = 1 << 30, u1 = -(1 << 30), v0 = 1 << 30, v1 = -(1 << 30); long fr = platform_frame_number();
  lkGLint fb0 = 0, tb[5]; static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 }; static uint32_t pk[1024], bt[38 * 76], *rb;
  if (lk_gl_getmode() != 2 || lk_glt_st < 0 || !lk_gl_frame(fr, fu, iu)) return;
  if (lk_glt_st == 0) { lk_glt_st = lk_glt_init(); if (lk_glt_st < 0) return; }
  if (iu[8]) { lk_glt_skip++; return; }   /* GL1: key light / shafts / sword glow frames not yet */
  for (i = 0; i < 5; i++) { lk_glActiveTexture(0x84C0 + i); lk_glGetIntegerv(0x8069, &tb[i]); }
  /* visible blocks: upload what changed */
  for (L = 0; L < 224; L++) { int U = (int)(int16_t)(lk_gl_row[L] & 0xFFFF), V = (int)(int16_t)(lk_gl_row[L] >> 16); if (U < u0) u0 = U; if (U + iu[7] - 1 > u1) u1 = U + iu[7] - 1; if (V < v0) v0 = V; if (V > v1) v1 = V; }
  lk_glActiveTexture(0x84C3); lk_glBindTexture(0x0DE1, lk_glt_roomA);
  for (by = 0; by < 38; by++) for (bx = 0; bx < 76; bx++) { unsigned v = lk_gl_bver(bx, by); bt[by * 76 + bx] = (v ? 0xFFu : 0u) | (lk_gl_bsg(bx, by) ? 0xFF00u : 0u);
    if (v && v != lk_glt_ver[by][bx] && bx * 32 + 31 >= u0 && bx * 32 <= u1 && by * 32 + 31 >= v0 && by * 32 <= v1) { lk_gl_bpack(bx, by, pk); lk_glTexSubImage2D(0x0DE1, 0, bx * 32, by * 32, 32, 32, 0x1908, 0x1401, pk); lk_glt_ver[by][bx] = v; } }
  lk_glActiveTexture(0x84C4); lk_glBindTexture(0x0DE1, lk_glt_btab); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 76, 38, 0x1908, 0x1401, bt);
  lk_glActiveTexture(0x84C2); lk_glBindTexture(0x0DE1, lk_glt_rows); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 224, 1, 0x1908, 0x1401, lk_gl_row);
  lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, lk_glt_cls); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x1909, 0x1401, lk_gl_cls);
  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_glt_unl); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x80E1, 0x1401, lk_gl_unlit);
  lk_glUseProgram(lk_glt_prog);
  for (i = 0; i < 5; i++) lk_glUniform1i(lk_glt_u[i], i);
  lk_glUniform1f(lk_glt_u[5], fu[0]); lk_glUniform1f(lk_glt_u[6], fu[1]); lk_glUniform1f(lk_glt_u[7], fu[2]);
  lk_glUniform3f(lk_glt_u[8], fu[3], fu[4], fu[5]); lk_glUniform3f(lk_glt_u[9], fu[6], fu[7], fu[8]);
  lk_glUniform1f(lk_glt_u[10], fu[9]); lk_glUniform1f(lk_glt_u[11], (float)iu[0]); lk_glUniform1f(lk_glt_u[12], iu[2] ? 1.0f : 0.0f); lk_glUniform1f(lk_glt_u[13], (float)iu[5]); lk_glUniform1f(lk_glt_u[14], (float)iu[6]);
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glBindFramebuffer(0x8D40, lk_glt_fbo); lk_glViewport(0, 0, 448, 224);
  lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad); lk_glDrawArrays(0x0005, 0, 4);
  if (!rb) rb = (uint32_t *)malloc(448 * 224 * 4);
  if (rb) { lk_glPixelStorei(0x0D02, 0); lk_glPixelStorei(0x0D05, 4); lk_glReadPixels(0, 0, 448, 224, 0x80E1, 0x1401, rb); }
  lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0);
  for (i = 4; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); }
  if (!rb) return;
  lk_glt_n++;
  for (L = 0; L < 224; L++) for (i = 0; i < iu[7]; i++) { int o = L * 448 + i, c = lk_gl_cls[o], f = lk_gl_flg[o], d, k; uint32_t a, b;
    if (c != 1 && c != 3) continue;
    if (f) { lk_glt_xc++; for (k = 0; k < 4; k++) if (f & (1 << k)) lk_glt_xf[k]++; continue; }
    lk_glt_px++; a = lk_gl_ref[o]; b = rb[o]; d = 0;
    for (k = 0; k < 24; k += 8) { int e = abs((int)((a >> k) & 255) - (int)((b >> k) & 255)); if (e > d) d = e; }
    if (d == 0) lk_glt_ex++; else if (d == 1) lk_glt_o1++;
    else { lk_glt_bad++; if (lk_glt_shown < 12) { lk_glt_shown++; printf("gpult: diff frame %%ld x %%d line %%d U %%d V %%d class %%d cpu %%06X gpu %%06X unlit %%06X\n", fr - 1, i, L, (int)(int16_t)(lk_gl_row[L] & 0xFFFF) + i, (int)(int16_t)(lk_gl_row[L] >> 16), c, (unsigned)(a & 0xFFFFFF), (unsigned)(b & 0xFFFFFF), (unsigned)(lk_gl_unlit[o] & 0xFFFFFF)); } } }
  if (lk_glt_n %% 300 == 0) printf("gpult: frames %%ld skipped %%ld pixels %%ld exact %%ld off1 %%ld worse %%ld excluded %%ld (fig %%ld figsun %%ld flame %%ld particle %%ld)\n", lk_glt_n, lk_glt_skip, lk_glt_px, lk_glt_ex, lk_glt_o1, lk_glt_bad, lk_glt_xc, lk_glt_xf[0], lk_glt_xf[1], lk_glt_xf[2], lk_glt_xf[3]);
}

''' % VER
    MODULE = MODULE.replace("@SHADER@", "\n".join('"%s\\n"' % l.replace("\\", "\\\\").replace('"', '\\"') for l in SHADER.strip("\n").split("\n")))
    a = "static long lk_gpu_frames;\n"
    assert s.count(a) == 1, "platform_sdl.c: LK_GPU module not found (patch_gpu.py first)"
    s = s.replace(a, MODULE + a)
    a = "  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_gpu_tex); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, sw, 224, 0x80E1, 0x1401, fb);\n"
    assert s.count(a) == 1, "platform_sdl.c: GPU upload line changed"
    s = s.replace(a, "  lk_glt_pass();   /* %s */\n" % VER + a)
    # test aid: hidden window (the GL context without anything on the screen)
    a = "        SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE\n"
    assert s.count(a) == 1, "platform_sdl.c: window flags changed"
    s = s.replace(a, "        (getenv(\"LANDSTALKER_HIDDEN\") ? SDL_WINDOW_HIDDEN : SDL_WINDOW_SHOWN) | SDL_WINDOW_RESIZABLE   /* %s test aid */\n" % VER)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)
else:
    print("platform_sdl.c already patched:", VER)
