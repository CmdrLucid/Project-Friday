#!/usr/bin/env python3
"""De-Dither on the GPU (LK_DDGPU v1, 2026-11-17, user rec_20261117_0811: with De-Dither on, things jitter while scrolling outdoors, e.g. Mercator's house windows).
Why it jittered: the CPU de-dither (tools/display_core.c lk_dedither_bil, ~5 ms outdoors) also blocked the GPU picture composition (patch_gpucomp.py lk_gc_block:
'something reads the CPU rows'), so every line was composed on the CPU again (~5 ms more); together they broke the 16.7 ms frame and dropped frames (framestat:
16..24 frames > 20 ms per second outdoors instead of 6..10), which shows as jitter on fine edges while the camera moves.
What this does: the SAME edge-preserving smoothing (5 x 5 window, gaussian x colour similarity, colour range 90 / 120 / 150 for Light / Medium / Strong) runs as one
fragment shader pass right after the picture is composed on the GPU (after lk_gc_real1, before the light pass and the display filters, which all read texture unit 0),
into its own texture that is then bound to unit 0.  The guards are the CPU ones: the window purple $442288 / text white $EEEEEE within 3 px (dialogue boxes, menus),
the Modern HUD's own pixels + 1 px (mask from lk_mh_ddmark, uploaded per frame), the Original HUD bar = the top 24 rows (lk_dd_hud of patch_display.py), the outer
2 columns / bottom 2 rows.  The GPU composition is no longer blocked by De-Dither; the CPU de-dither stays as the fallback (GPU Filters off / failed, 3D room path,
the first frame before the GPU is ready: then lk_dd_cpudone keeps the GPU pass from smoothing twice).  The HD picture keeps De-Dither off as before.
Needs patch_display.py, patch_hd.py, patch_modernhud.py, patch_gpu.py, patch_gpulight.py, patch_gpucomp.py before it.  Idempotent.  usage: patch_ddgpu.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_DDGPU v1"

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched:", VER); sys.exit(0)

def rep(a, b):
    global s
    assert s.count(a) == 1, ("platform_sdl.c: anchor not found once", a[:90], s.count(a))
    s = s.replace(a, b)

SHADER = r'''
uniform sampler2D src; uniform sampler2D hud;
uniform float uW; uniform float uTop; uniform float uRange; uniform float uHud;
vec4 P(vec2 q) { return texture2D(src, (q + 0.5) / vec2(448.0, 224.0)); }
vec3 I(vec2 q) { return floor(P(q).rgb * 255.0 + 0.5); }
float spw(float a, float b) { if (a < 0.5) return b < 0.5 ? 16.0 : b < 1.5 ? 11.0 : 8.0; if (a < 1.5) return b < 0.5 ? 11.0 : b < 1.5 ? 8.0 : 4.0; return b < 0.5 ? 8.0 : b < 1.5 ? 4.0 : 3.0; }
bool ui(vec3 a) { return (a.r == 68.0 && a.g == 34.0 && a.b == 136.0) || (a.r == 238.0 && a.g == 238.0 && a.b == 238.0); }
void main() {
  vec2 fc = floor(gl_FragCoord.xy); vec4 c4 = P(fc); vec3 c = floor(c4.rgb * 255.0 + 0.5);
  gl_FragColor = c4;
  if (fc.x < 2.0 || fc.x >= uW - 2.0 || fc.y < uTop || fc.y >= 222.0) return;
  if (uHud > 0.5 && texture2D(hud, (fc + 0.5) / vec2(448.0, 224.0)).r > 0.5 / 255.0) return;   /* (the mask bytes are 0 / 1) */
  bool flat = true;
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) if ((i != 0 || j != 0) && I(fc + vec2(float(i), float(j))) != c) flat = false;
  if (flat) return;
  for (int j = -3; j <= 3; j++) for (int i = -3; i <= 3; i++) { vec2 q = fc + vec2(float(i), float(j)); if (q.y >= 0.0 && q.y <= 223.0 && q.x >= 0.0 && q.x < uW && ui(I(q))) return; }
  vec3 sum = vec3(0.0); float ws = 0.0;
  for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++) {
    vec3 n = I(fc + vec2(float(i), float(j))); vec3 dd = abs(n - c); float d = max(dd.r, max(dd.g, dd.b));
    if (d >= uRange) continue;
    float w = spw(abs(float(j)), abs(float(i))) * floor((uRange - d) * 16.0 / uRange);
    sum += n * w; ws += w; }
  if (ws > 0.0) gl_FragColor = vec4(floor(sum / ws) / 255.0, c4.a);
}
'''

MODULE = r'''/* ---- LK_DDGPU v1: De-Dither on the GPU (tools/patch_ddgpu.py) ---- */
static int lk_ddg_st;   /* 0 not tried, 1 ready, -1 failed (the CPU de-dither from then on) */
static lkGLuint lk_ddg_prog, lk_ddg_out, lk_ddg_hud, lk_ddg_fbo; static lkGLint lk_ddg_u[6]; static uint8_t lk_ddg_m[448 * 224];
static int lk_dd_cpudone;   /* the CPU de-dither already ran on the picture being presented (first frame, fallback): no second pass on the GPU */
static const char *lk_ddg_fs = "#version 120\n" @SHADER@;
static int lk_dd_ongpu(void) { extern int lk_r3d_on(void); return lk_ddg_st >= 0 && lk_gpu_get() && lk_gpu_st == 1 && !lk_r3d_on(); }   /* the GPU path presents and can smooth this frame */
static int lk_ddg_init(void) {
  static const char *un[6] = { "src", "hud", "uW", "uTop", "uRange", "uHud" }; lkGLint ok = 0, t0 = 0, fb0 = 0; lkGLuint vs, fs; char log[2048]; int i;
  if (!lk_glGenFramebuffers) { *(void **)&lk_glGenFramebuffers = lk_gpu_fn("glGenFramebuffers"); *(void **)&lk_glBindFramebuffer = lk_gpu_fn("glBindFramebuffer");
    *(void **)&lk_glFramebufferTexture2D = lk_gpu_fn("glFramebufferTexture2D"); *(void **)&lk_glCheckFramebufferStatus = lk_gpu_fn("glCheckFramebufferStatus"); }
  if (!lk_glGenFramebuffers || !lk_glBindFramebuffer || !lk_glFramebufferTexture2D || !lk_glCheckFramebufferStatus) { printf("ddgpu: GL functions missing: CPU de-dither\n"); return -1; }
  { static const char *vsrc = "#version 120\nvoid main() { gl_Position = gl_Vertex; }\n"; vs = lk_glCreateShader(0x8B31); lk_glShaderSource(vs, 1, &vsrc, 0); lk_glCompileShader(vs); lk_glGetShaderiv(vs, 0x8B81, &ok); if (!ok) return -1; }
  fs = lk_glCreateShader(0x8B30); lk_glShaderSource(fs, 1, &lk_ddg_fs, 0); lk_glCompileShader(fs); lk_glGetShaderiv(fs, 0x8B81, &ok);
  if (!ok) { lk_glGetShaderInfoLog(fs, sizeof log, 0, log); printf("ddgpu: shader failed: %s\n", log); return -1; }
  lk_ddg_prog = lk_glCreateProgram(); lk_glAttachShader(lk_ddg_prog, vs); lk_glAttachShader(lk_ddg_prog, fs); lk_glLinkProgram(lk_ddg_prog); lk_glGetProgramiv(lk_ddg_prog, 0x8B82, &ok);
  if (!ok) { lk_glGetProgramInfoLog(lk_ddg_prog, sizeof log, 0, log); printf("ddgpu: link failed: %s\n", log); return -1; }
  for (i = 0; i < 6; i++) lk_ddg_u[i] = lk_glGetUniformLocation(lk_ddg_prog, un[i]);
  lk_glGetIntegerv(0x8069, &t0);
  lk_ddg_out = lk_glt_tex(448, 224, 0x1908, 0x80E1); lk_ddg_hud = lk_glt_tex(448, 224, 0x1909, 0x1909);
  lk_glBindTexture(0x0DE1, (lkGLuint)t0);
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glGenFramebuffers(1, &lk_ddg_fbo); lk_glBindFramebuffer(0x8D40, lk_ddg_fbo); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_ddg_out, 0);
  ok = lk_glCheckFramebufferStatus(0x8D40) == 0x8CD5; lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0);
  if (!ok) { printf("ddgpu: framebuffer incomplete: CPU de-dither\n"); return -1; }
  return 1; }
static void lk_ddg_pass(int sw) {   /* in lk_gpu_present after the picture is composed (unit 0 = the picture): the smoothed copy -> unit 0 */
  static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 }; lkGLint fb0 = 0, vp[4], prog = 0, t1 = 0; extern int lk_hd_active(void);
  if (!lk_dd_loaded) lk_dd_load();
  if (!lk_dd_mode || lk_dd_cpudone || !lk_dd_ongpu() || lk_hd_active() || sw > 448) return;
  if (lk_ddg_st == 0) { lk_ddg_st = lk_ddg_init(); if (lk_ddg_st < 0) return; }
  lk_dd_hud();   /* Original HUD: skip the bar rows; Modern HUD: its pixels as a mask */
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glGetIntegerv(0x0BA2, vp); lk_glGetIntegerv(0x8B8D, &prog);
  lk_glActiveTexture(0x84C1); lk_glGetIntegerv(0x8069, &t1); lk_glBindTexture(0x0DE1, lk_ddg_hud);
  if (lk_dd_hudmark) { memset(lk_ddg_m, 0, sizeof lk_ddg_m); lk_dd_hudmark(lk_ddg_m, 448, 224); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x1909, 0x1401, lk_ddg_m); }
  lk_glActiveTexture(0x84C0);
  lk_glUseProgram(lk_ddg_prog); lk_glUniform1i(lk_ddg_u[0], 0); lk_glUniform1i(lk_ddg_u[1], 1);
  lk_glUniform1f(lk_ddg_u[2], (float)sw); lk_glUniform1f(lk_ddg_u[3], (float)lk_dd_skip_top); lk_glUniform1f(lk_ddg_u[4], lk_dd_mode == 3 ? 150.0f : lk_dd_mode == 2 ? 120.0f : 90.0f); lk_glUniform1f(lk_ddg_u[5], lk_dd_hudmark ? 1.0f : 0.0f);
  lk_glBindFramebuffer(0x8D40, lk_ddg_fbo); lk_glViewport(0, 0, 448, 224); lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad);
  lk_glDrawArrays(0x0005, 0, 4);
  lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); lk_glViewport(vp[0], vp[1], vp[2], vp[3]); lk_glUseProgram((lkGLuint)prog);
  lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, (lkGLuint)t1);
  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_ddg_out);   /* light, bounce and the display filters read the smoothed picture */
}
'''
MODULE = MODULE.replace("@SHADER@", "\n".join('"%s\\n"' % l.replace("\\", "\\\\").replace('"', '\\"') for l in SHADER.strip("\n").split("\n")))

# the module right before lk_gpu_present (after the GPU filter / light / composition helpers it uses)
a = "static int lk_gpu_present(const uint8_t *fb, int sw, const lk_rect *r, int ow, int oh, int fx) {\n"
rep(a, MODULE + a)

# the pass: right after the GPU composition of the lines, before the light pass
import re
m = re.findall(r"  lk_gc_real1\(\);   /\* [^\n]*\*/\n", s)
assert len(m) == 1, ("platform_sdl.c: lk_gc_real1 call not found once", len(m))
rep(m[0], m[0] + "  lk_ddg_pass(sw);   /* %s */\n" % VER)

# the CPU de-dither only when the GPU does not do it (fallback), and remember that it ran
a = "if (lk_dd_mode && !lk_hd_active()) {"
rep(a, "lk_dd_cpudone = 0; if (lk_dd_mode && !lk_hd_active() && !lk_dd_ongpu() && (lk_dd_cpudone = 1)) {   /* %s: the GPU smooths when it presents */" % VER)

# the GPU composition is not blocked by De-Dither any more (only by the CPU fallback)
a = "  lk_gc_block = lk_dd_mode != 0 || s_record != NULL || lk_gc_st < 0;"
rep(a, "  lk_gc_block = (lk_dd_mode != 0 && !lk_dd_ongpu()) || s_record != NULL || lk_gc_st < 0;   /* (%s: De-Dither on the GPU keeps the GPU lines) */" % VER)
a = "static void lk_gc_real1(void) {"
rep(a, "static int lk_dd_ongpu(void);   /* %s */\n" % VER + a)

open(p, "w").write(s)
print("platform_sdl.c patched:", VER)
