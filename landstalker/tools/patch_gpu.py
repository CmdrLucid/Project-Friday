#!/usr/bin/env python3
"""GPU presentation step 1 (2026-11-06, user: 'nutzen wir die GPU ueberhaupt?' -> 'was leicht zu aendern ist, wuerde ich jetzt schon machen' -> 'ja mach Schritt 1').
The scaling and the display filters (Off = sharp-bilinear / nearest, Scanlines, CRT, CRT Pro, CRT Curved, plus the LK_SSHARP world pixel shift) run as ONE fragment shader
on the GPU instead of the CPU bands (lk_fx_render_mt).  The 1x picture (sw x 224, after de-dither / depth blur, which stay on the CPU) is uploaded as a texture; the
shader writes the destination rectangle straight into SDL's OpenGL context; SDL then draws the overlays (room map, OSD, coordinates) as before.
How: SDL's renderer must be 'opengl' (default on Linux / Steam Deck; with the option on, the hint SDL_RENDER_DRIVER=opengl is set before the renderer is made, so
Windows uses OpenGL too).  The GL functions come from SDL_GL_GetProcAddress (no extra library).  Our draw flushes SDL (SDL_RenderFlush), saves every GL state it
touches (program, textures of units 0 / 1, viewport, scissor, blend, client arrays / pointers, array buffer, pixel store) and restores it afterwards.
Fallback: no OpenGL renderer, a GL function missing, a shader compile / link error or a GL error after the first draw -> the CPU path, for the rest of the run.
Not on the GPU: the HD picture and the 3D room paths (unchanged), the de-dither and the depth blur (1x, CPU).
Option: Options > Display > GPU Filters (id 55, ~/.landstalker_gpu, env LANDSTALKER_GPU=0|1 wins), default On.  Off = the old CPU path, unchanged.
Test aids: LANDSTALKER_GPU_DBG=1 (renderer / init / errors), LANDSTALKER_PRESENT_SHOT=frame,.. writes the PRESENTED picture (destination rectangle, CPU or GPU)
to LANDSTALKER_SHOT_DIR as present_<frame>_<gpu|cpu>.png (compare the two paths).
Needs patch_display.py, patch_subpix.py, patch_shot.py, patch_options.py before it.  Idempotent.  usage: patch_gpu.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_GPU v1"

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, ("platform_sdl.c: anchor not found once", a[:80], s.count(a))
    s = s.replace(a, b)

SHADER = r'''
uniform sampler2D src; uniform sampler2D okm;
uniform vec2 texSize; uniform vec2 srcSize; uniform vec2 dstSize; uniform vec2 origin;
uniform int mode; uniform float whole; uniform float ssh; uniform float exact;
vec3 px(float ix, float iy) { return texture2D(src, (vec2(ix, iy) + 0.5) / texSize).rgb; }
float okAt(float x, float y) {
  float cx = min(floor((2.0 * x + 1.0) * srcSize.x / (2.0 * dstSize.x)), srcSize.x - 1.0), ry = min(floor((2.0 * y + 1.0) * 224.0 / (2.0 * dstSize.y)), 223.0);
  return texture2D(okm, (vec2(cx, ry) + 0.5) / vec2(448.0, 224.0)).r; }
vec3 lin(vec3 c) { return pow(c, vec3(2.2)); }
vec3 hrow(float r, float x0, float f) {   /* CRT Pro horizontal pass: gaussian (sigma 0.42) over 4 taps in linear light */
  vec3 acc = vec3(0.0); float ws = 0.0;
  for (int k = 0; k < 4; k++) { float d = f - float(k - 1), w = exp(-d * d / (2.0 * 0.42 * 0.42)); acc += w * lin(px(clamp(x0 + float(k - 1), 0.0, srcSize.x - 1.0), r)); ws += w; }
  return acc / ws; }
float beam(float fr8, vec3 h) {   /* vertical beam weight: distance class of the CPU table, sigma 0.20 (dark) .. 0.42 (bright) rows */
  float lum = dot(h, vec3(54.0, 183.0, 19.0) / 256.0), b = floor(pow(clamp(lum, 0.0, 1.0), 1.0 / 2.2) * 255.0 / 8.0), sg = 0.20 + 0.22 * (b / 31.0), d = (floor(fr8 / 4.0) + 0.5) / 64.0;
  return exp(-d * d / (2.0 * sg * sg)); }
void main() {
  float x = floor(gl_FragCoord.x - origin.x), y = dstSize.y - 1.0 - floor(gl_FragCoord.y - origin.y), yy = y;
  if (ssh != 0.0) { float y2 = clamp(y + ssh, 0.0, dstSize.y - 1.0); if (okAt(x, y) > 0.5 && okAt(x, y2) > 0.5) yy = y2; }   /* LK_SSHARP: world pixels sample like the output row y2 */
  vec3 c;
  if (mode == 0) {
    if (exact > 0.5) c = px(floor((x + 0.5) * srcSize.x / dstSize.x), floor((yy + 0.5) * 224.0 / dstSize.y));
    else {   /* exact sharp-bilinear */
      float S = dstSize.x / srcSize.x, p = (x + 0.5) * srcSize.x / dstSize.x - 0.5, i0 = floor(p), wx = clamp((p - i0 - 0.5) * S + 0.5, 0.0, 1.0);
      float T = dstSize.y / 224.0, q = (yy + 0.5) * 224.0 / dstSize.y - 0.5, j0 = floor(q), wy = clamp((q - j0 - 0.5) * T + 0.5, 0.0, 1.0);
      float ax = clamp(i0, 0.0, srcSize.x - 1.0), bx = clamp(i0 + 1.0, 0.0, srcSize.x - 1.0), ay = clamp(j0, 0.0, 223.0), by = clamp(j0 + 1.0, 0.0, 223.0);
      c = mix(mix(px(ax, ay), px(bx, ay), wx), mix(px(ax, by), px(bx, by), wx), wy); }
  } else if (mode == 1 || mode == 2) {   /* SCANLINES / CRT */
    float f = max((x + 0.5) * srcSize.x / dstSize.x - 0.5, 0.0), x0 = min(floor(f), srcSize.x - 1.0), x1 = min(x0 + 1.0, srcSize.x - 1.0), wx = mode == 2 ? floor((f - x0) * 256.0) / 256.0 : 0.0;
    float sy = (yy + 0.5) * 224.0 / dstSize.y, row = min(floor(sy), 223.0), a = mode == 2 ? 0.65 : 0.50, ws = 0.0;
    if (whole < 0.5) a *= 0.70;
    if (whole > 0.5) { float d = abs(fract(sy) - 0.5) * 2.0; ws = 1.0 - a * d * d; }
    else for (int k = 0; k < 8; k++) { float s2 = (yy + (float(k) + 0.5) / 8.0) * 224.0 / dstSize.y, d = abs(fract(s2) - 0.5) * 2.0; ws += (1.0 - a * d * d) / 8.0; }
    float wy = floor(256.0 * ws / (1.0 - a / 3.0)) / 256.0, ph = mod(x, 3.0);
    vec3 m = vec3(1.0);
    if (mode == 2) { float mc = 1.0 / ((1.0 + 2.0 * 0.70) / 3.0); m = mc * vec3(ph == 0.0 ? 1.0 : 0.70, ph == 1.0 ? 1.0 : 0.70, ph == 2.0 ? 1.0 : 0.70); }
    c = mix(px(x0, row), px(x1, row), wx) * wy * m;
  } else {   /* CRT PRO / CRT CURVED */
    float k = mode == 4 ? 0.025 : 0.0, z = 1.0 / (1.0 + k), g = 1.0;
    float u = 2.0 * (x + 0.5) / dstSize.x - 1.0, v = 2.0 * (y + 0.5) / dstSize.y - 1.0, v2 = 2.0 * (yy + 0.5) / dstSize.y - 1.0;
    float uu = u * z * (1.0 + k * v * v), vv = v * z * (1.0 + k * u * u), vs = v2 * z * (1.0 + k * u * u);
    if (mode == 4) { float e = min((1.0 - abs(uu)) * dstSize.x * 0.5, (1.0 - abs(vv)) * dstSize.y * 0.5); g = e <= 0.0 ? 0.0 : min(e / 1.5, 1.0); g *= 1.0 - 0.28 * (uu * uu + vv * vv) * 0.5; }
    float mx = floor(clamp((uu + 1.0) * 0.5 * dstSize.x, 0.0, dstSize.x - 1.0)), sy = floor(clamp((vs + 1.0) * 0.5 * 224.0 - 0.5, 0.0, 223.0) * 256.0 + 0.5);
    float pp = max(floor((2.0 * mx + 1.0) * srcSize.x * 128.0 / dstSize.x) - 128.0, 0.0), x0 = floor(pp / 256.0), f = mod(pp, 256.0) / 256.0;
    if (x0 > srcSize.x - 1.0) { x0 = srcSize.x - 1.0; f = 0.0; }
    float r0 = floor(sy / 256.0), fr = mod(sy, 256.0), r1 = min(r0 + 1.0, 223.0);
    vec3 ha = hrow(r0, x0, f), hb = hrow(r1, x0, f);
    vec3 vl = ha * beam(fr, ha) + hb * beam(255.0 - fr, hb);
    float ph = mod(x, 3.0); vec3 m = 1.38 * vec3(ph == 0.0 ? 1.0 : 0.62, ph == 1.0 ? 1.0 : 0.62, ph == 2.0 ? 1.0 : 0.62);
    c = pow(clamp(vl * m * g, 0.0, 1.0), vec3(1.0 / 2.2));
  }
  gl_FragColor = vec4(clamp(c, 0.0, 1.0), 1.0); }
'''

if VER not in s:
    MODULE = r'''/* ---- %s: the display filters on the GPU (tools/patch_gpu.py) ---- */
static int lk_gpu_o = -1;
int lk_gpu_get(void) { if (lk_gpu_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_GPU"); char pth[512]; FILE *f; int v = 1; snprintf(pth, sizeof pth, "%%s/.landstalker_gpu", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%%d", &v) != 1) v = 1; fclose(f); } if (e) v = atoi(e); lk_gpu_o = v ? 1 : 0; } return lk_gpu_o; }
void lk_gpu_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_gpu_get(); lk_gpu_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_gpu", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_gpu_o); fclose(f); } }
typedef unsigned int lkGLenum; typedef unsigned int lkGLuint; typedef int lkGLint; typedef int lkGLsizei; typedef float lkGLfloat; typedef unsigned char lkGLboolean; typedef char lkGLchar;
#define LKGL_FN(ret, name, args) static ret (*lk_##name) args
LKGL_FN(lkGLuint, glCreateShader, (lkGLenum)); LKGL_FN(void, glShaderSource, (lkGLuint, lkGLsizei, const lkGLchar *const *, const lkGLint *)); LKGL_FN(void, glCompileShader, (lkGLuint));
LKGL_FN(void, glGetShaderiv, (lkGLuint, lkGLenum, lkGLint *)); LKGL_FN(void, glGetShaderInfoLog, (lkGLuint, lkGLsizei, lkGLsizei *, lkGLchar *)); LKGL_FN(lkGLuint, glCreateProgram, (void));
LKGL_FN(void, glAttachShader, (lkGLuint, lkGLuint)); LKGL_FN(void, glLinkProgram, (lkGLuint)); LKGL_FN(void, glGetProgramiv, (lkGLuint, lkGLenum, lkGLint *)); LKGL_FN(void, glGetProgramInfoLog, (lkGLuint, lkGLsizei, lkGLsizei *, lkGLchar *));
LKGL_FN(void, glUseProgram, (lkGLuint)); LKGL_FN(lkGLint, glGetUniformLocation, (lkGLuint, const lkGLchar *)); LKGL_FN(void, glUniform1i, (lkGLint, lkGLint)); LKGL_FN(void, glUniform1f, (lkGLint, lkGLfloat)); LKGL_FN(void, glUniform2f, (lkGLint, lkGLfloat, lkGLfloat));
LKGL_FN(void, glActiveTexture, (lkGLenum)); LKGL_FN(void, glGenTextures, (lkGLsizei, lkGLuint *)); LKGL_FN(void, glBindTexture, (lkGLenum, lkGLuint)); LKGL_FN(void, glTexImage2D, (lkGLenum, lkGLint, lkGLint, lkGLsizei, lkGLsizei, lkGLint, lkGLenum, lkGLenum, const void *));
LKGL_FN(void, glTexSubImage2D, (lkGLenum, lkGLint, lkGLint, lkGLint, lkGLsizei, lkGLsizei, lkGLenum, lkGLenum, const void *)); LKGL_FN(void, glTexParameteri, (lkGLenum, lkGLenum, lkGLint)); LKGL_FN(void, glPixelStorei, (lkGLenum, lkGLint));
LKGL_FN(void, glViewport, (lkGLint, lkGLint, lkGLsizei, lkGLsizei)); LKGL_FN(void, glGetIntegerv, (lkGLenum, lkGLint *)); LKGL_FN(lkGLboolean, glIsEnabled, (lkGLenum)); LKGL_FN(void, glEnable, (lkGLenum)); LKGL_FN(void, glDisable, (lkGLenum));
LKGL_FN(void, glScissor, (lkGLint, lkGLint, lkGLsizei, lkGLsizei)); LKGL_FN(void, glDrawArrays, (lkGLenum, lkGLint, lkGLsizei)); LKGL_FN(void, glEnableClientState, (lkGLenum)); LKGL_FN(void, glDisableClientState, (lkGLenum));
LKGL_FN(void, glVertexPointer, (lkGLint, lkGLenum, lkGLsizei, const void *)); LKGL_FN(void, glGetPointerv, (lkGLenum, void **)); LKGL_FN(void, glBindBuffer, (lkGLenum, lkGLuint)); LKGL_FN(lkGLenum, glGetError, (void));
LKGL_FN(void, glClientActiveTexture, (lkGLenum)); LKGL_FN(void, glGetVertexAttribiv, (lkGLuint, lkGLenum, lkGLint *)); LKGL_FN(void, glEnableVertexAttribArray, (lkGLuint)); LKGL_FN(void, glDisableVertexAttribArray, (lkGLuint));
LKGL_FN(void, glReadPixels, (lkGLint, lkGLint, lkGLsizei, lkGLsizei, lkGLenum, lkGLenum, void *)); LKGL_FN(void, glGetFloatv, (lkGLenum, lkGLfloat *));
static int lk_gpu_st;   /* 0 not tried, 1 ready, -1 failed (CPU path for the rest of the run) */
static int lk_gpu_dbg = -1; static lkGLuint lk_gpu_prog, lk_gpu_tex, lk_gpu_okt; static lkGLint lk_gpu_u[12];
static const char *lk_gpu_fs = "#version 120\n" @SHADER@;
static void *lk_gpu_fn(const char *n) { void *f = SDL_GL_GetProcAddress(n); if (!f && lk_gpu_dbg) printf("gpu: missing %%s\n", n); return f; }
static int lk_gpu_init(void) {   /* once, inside SDL's GL context */
  SDL_RendererInfo ri; lkGLint ok = 0; lkGLuint vs, fs; char log[1024]; int miss = 0;
  if (lk_gpu_dbg < 0) { const char *e = getenv("LANDSTALKER_GPU_DBG"); lk_gpu_dbg = e ? atoi(e) : 0; }
  if (SDL_GetRendererInfo(s_renderer, &ri) != 0 || strcmp(ri.name, "opengl") != 0) { if (lk_gpu_dbg) printf("gpu: renderer '%%s' is not opengl: CPU filters\n", ri.name ? ri.name : "?"); return -1; }
  #define LKGL_LOAD(n) do { *(void **)&lk_##n = lk_gpu_fn(#n); if (!lk_##n) miss++; } while (0)
  LKGL_LOAD(glCreateShader); LKGL_LOAD(glShaderSource); LKGL_LOAD(glCompileShader); LKGL_LOAD(glGetShaderiv); LKGL_LOAD(glGetShaderInfoLog); LKGL_LOAD(glCreateProgram); LKGL_LOAD(glAttachShader);
  LKGL_LOAD(glLinkProgram); LKGL_LOAD(glGetProgramiv); LKGL_LOAD(glGetProgramInfoLog); LKGL_LOAD(glUseProgram); LKGL_LOAD(glGetUniformLocation); LKGL_LOAD(glUniform1i); LKGL_LOAD(glUniform1f); LKGL_LOAD(glUniform2f);
  LKGL_LOAD(glActiveTexture); LKGL_LOAD(glGenTextures); LKGL_LOAD(glBindTexture); LKGL_LOAD(glTexImage2D); LKGL_LOAD(glTexSubImage2D); LKGL_LOAD(glTexParameteri); LKGL_LOAD(glPixelStorei); LKGL_LOAD(glViewport);
  LKGL_LOAD(glGetIntegerv); LKGL_LOAD(glIsEnabled); LKGL_LOAD(glEnable); LKGL_LOAD(glDisable); LKGL_LOAD(glScissor); LKGL_LOAD(glDrawArrays); LKGL_LOAD(glEnableClientState); LKGL_LOAD(glDisableClientState);
  LKGL_LOAD(glVertexPointer); LKGL_LOAD(glGetPointerv); LKGL_LOAD(glBindBuffer); LKGL_LOAD(glGetError); LKGL_LOAD(glClientActiveTexture); LKGL_LOAD(glGetVertexAttribiv); LKGL_LOAD(glEnableVertexAttribArray);
  LKGL_LOAD(glDisableVertexAttribArray); LKGL_LOAD(glReadPixels); LKGL_LOAD(glGetFloatv);
  #undef LKGL_LOAD
  if (miss) { if (lk_gpu_dbg) printf("gpu: %%d GL functions missing: CPU filters\n", miss); return -1; }
  { static const char *vsrc = "#version 120\nvoid main() { gl_Position = gl_Vertex; }\n"; vs = lk_glCreateShader(0x8B31); lk_glShaderSource(vs, 1, &vsrc, 0); lk_glCompileShader(vs); lk_glGetShaderiv(vs, 0x8B81, &ok);
    if (!ok) { lk_glGetShaderInfoLog(vs, sizeof log, 0, log); printf("gpu: vertex shader failed: %%s\n", log); return -1; } }
  fs = lk_glCreateShader(0x8B30); lk_glShaderSource(fs, 1, &lk_gpu_fs, 0); lk_glCompileShader(fs); lk_glGetShaderiv(fs, 0x8B81, &ok);
  if (!ok) { lk_glGetShaderInfoLog(fs, sizeof log, 0, log); printf("gpu: fragment shader failed: %%s\n", log); return -1; }
  lk_gpu_prog = lk_glCreateProgram(); lk_glAttachShader(lk_gpu_prog, vs); lk_glAttachShader(lk_gpu_prog, fs); lk_glLinkProgram(lk_gpu_prog); lk_glGetProgramiv(lk_gpu_prog, 0x8B82, &ok);
  if (!ok) { lk_glGetProgramInfoLog(lk_gpu_prog, sizeof log, 0, log); printf("gpu: link failed: %%s\n", log); return -1; }
  { static const char *un[11] = { "src", "okm", "texSize", "srcSize", "dstSize", "origin", "mode", "whole", "ssh", "exact", 0 }; int i; for (i = 0; un[i]; i++) lk_gpu_u[i] = lk_glGetUniformLocation(lk_gpu_prog, un[i]); }
  { lkGLint t0 = 0; lk_glGetIntegerv(0x8069, &t0); lk_glGenTextures(1, &lk_gpu_tex); lk_glGenTextures(1, &lk_gpu_okt);
    lk_glBindTexture(0x0DE1, lk_gpu_tex); lk_glTexImage2D(0x0DE1, 0, 0x1908, 448, 224, 0, 0x80E1, 0x1401, 0);
    lk_glTexParameteri(0x0DE1, 0x2801, 0x2600); lk_glTexParameteri(0x0DE1, 0x2800, 0x2600); lk_glTexParameteri(0x0DE1, 0x2802, 0x812F); lk_glTexParameteri(0x0DE1, 0x2803, 0x812F);
    lk_glBindTexture(0x0DE1, lk_gpu_okt); lk_glTexImage2D(0x0DE1, 0, 0x1909, 448, 224, 0, 0x1909, 0x1401, 0);
    lk_glTexParameteri(0x0DE1, 0x2801, 0x2600); lk_glTexParameteri(0x0DE1, 0x2800, 0x2600); lk_glTexParameteri(0x0DE1, 0x2802, 0x812F); lk_glTexParameteri(0x0DE1, 0x2803, 0x812F);
    lk_glBindTexture(0x0DE1, (lkGLuint)t0); }
  if (lk_gpu_dbg) printf("gpu: ready (renderer %%s)\n", ri.name);
  return 1; }
static long lk_gpu_frames;
/* returns 1 when the destination rectangle was drawn by the GPU (the caller skips the CPU filters) */
static int lk_gpu_present(const uint8_t *fb, int sw, const lk_rect *r, int ow, int oh, int fx) {
  lkGLint prog, act, tex0, tex1, vp[4], sc[4], abuf, vsize, vtype, vstride, unrow, unal, attr[8]; void *vptr; lkGLboolean scis, blend, va, ca, ta0, ta1; int i, exact;
  static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 };
  if (!lk_gpu_get() || lk_gpu_st < 0 || sw > 448 || r->w < 1 || r->h < 1) return 0;
  if (lk_gpu_st == 0) { SDL_RenderFlush(s_renderer); lk_gpu_st = lk_gpu_init(); if (lk_gpu_st < 0) return 0; }
  SDL_RenderFlush(s_renderer);   /* SDL's queued commands (the clear) first */
  lk_glGetIntegerv(0x8B8D, &prog); lk_glGetIntegerv(0x84E0, &act); lk_glGetIntegerv(0x0BA2, vp); lk_glGetIntegerv(0x0C10, sc); lk_glGetIntegerv(0x8894, &abuf);
  lk_glGetIntegerv(0x0CF2, &unrow); lk_glGetIntegerv(0x0CF5, &unal); scis = lk_glIsEnabled(0x0C11); blend = lk_glIsEnabled(0x0BE2);
  va = lk_glIsEnabled(0x8074); ca = lk_glIsEnabled(0x8076); lk_glGetIntegerv(0x807A, &vsize); lk_glGetIntegerv(0x807B, &vtype); lk_glGetIntegerv(0x807C, &vstride); lk_glGetPointerv(0x808E, &vptr);
  lk_glClientActiveTexture(0x84C0); ta0 = lk_glIsEnabled(0x8078); lk_glClientActiveTexture(0x84C1); ta1 = lk_glIsEnabled(0x8078); lk_glClientActiveTexture(0x84C0);
  for (i = 0; i < 8; i++) { attr[i] = 0; lk_glGetVertexAttribiv((lkGLuint)i, 0x8622, &attr[i]); }
  lk_glActiveTexture(0x84C1); lk_glGetIntegerv(0x8069, &tex1); lk_glActiveTexture(0x84C0); lk_glGetIntegerv(0x8069, &tex0);
  /* our state */
  lk_glBindBuffer(0x8892, 0); lk_glDisable(0x0C11); lk_glDisable(0x0BE2);
  if (ca) lk_glDisableClientState(0x8076); if (ta0) lk_glDisableClientState(0x8078); if (ta1) { lk_glClientActiveTexture(0x84C1); lk_glDisableClientState(0x8078); lk_glClientActiveTexture(0x84C0); }
  for (i = 0; i < 8; i++) if (attr[i]) lk_glDisableVertexAttribArray((lkGLuint)i);
  lk_glPixelStorei(0x0CF2, 0); lk_glPixelStorei(0x0CF5, 4);
  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_gpu_tex); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, sw, 224, 0x80E1, 0x1401, fb);
  lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, lk_gpu_okt); if (lk_ssh_d) lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x1909, 0x1401, lk_ssh_ok);
  lk_glUseProgram(lk_gpu_prog);
  exact = (r->w %% sw == 0) && (r->h %% LK_SRC_H == 0);
  lk_glUniform1i(lk_gpu_u[0], 0); lk_glUniform1i(lk_gpu_u[1], 1); lk_glUniform2f(lk_gpu_u[2], 448.0f, 224.0f); lk_glUniform2f(lk_gpu_u[3], (float)sw, 224.0f); lk_glUniform2f(lk_gpu_u[4], (float)r->w, (float)r->h);
  lk_glUniform2f(lk_gpu_u[5], (float)r->x, (float)(oh - r->y - r->h)); lk_glUniform1i(lk_gpu_u[6], fx); lk_glUniform1f(lk_gpu_u[7], (r->h %% LK_SRC_H) == 0 ? 1.0f : 0.0f);
  lk_glUniform1f(lk_gpu_u[8], lk_ssh_d ? (float)(lk_ssh_d * lk_ssh_k) : 0.0f); lk_glUniform1f(lk_gpu_u[9], exact ? 1.0f : 0.0f);
  lk_glViewport(r->x, oh - r->y - r->h, r->w, r->h);
  if (!va) lk_glEnableClientState(0x8074);
  lk_glVertexPointer(2, 0x1406, 0, quad); lk_glDrawArrays(0x0005, 0, 4);
  { static int shot = -1; static const char *list; static int fn;   /* test aid LANDSTALKER_PRESENT_SHOT: the presented GPU picture */
    if (shot < 0) { list = getenv("LANDSTALKER_PRESENT_SHOT"); shot = list != 0; }
    if (shot && lk_shot_wanted(list, platform_frame_number())) { uint32_t *b = (uint32_t *)malloc((size_t)r->w * r->h * 4), *t = (uint32_t *)malloc((size_t)r->w * r->h * 4); char pth[700]; const char *d = getenv("LANDSTALKER_SHOT_DIR");
      if (b && t) { int yy; lk_glPixelStorei(0x0D02, 0); lk_glPixelStorei(0x0D05, 4); lk_glReadPixels(r->x, oh - r->y - r->h, r->w, r->h, 0x80E1, 0x1401, b);
        for (yy = 0; yy < r->h; yy++) memcpy(t + (size_t)yy * r->w, b + (size_t)(r->h - 1 - yy) * r->w, (size_t)r->w * 4);
        snprintf(pth, sizeof pth, "%%s/present_%%06ld_gpu.png", d ? d : ".", platform_frame_number()); lk_shot_png(pth, t, r->w, r->h, 1); fn++; }
      free(b); free(t); } }
  /* restore SDL's state */
  lk_glVertexPointer(vsize, (lkGLenum)vtype, vstride, vptr); if (!va) lk_glDisableClientState(0x8074);
  if (ca) lk_glEnableClientState(0x8076); if (ta0) lk_glEnableClientState(0x8078); if (ta1) { lk_glClientActiveTexture(0x84C1); lk_glEnableClientState(0x8078); lk_glClientActiveTexture(0x84C0); }
  for (i = 0; i < 8; i++) if (attr[i]) lk_glEnableVertexAttribArray((lkGLuint)i);
  lk_glUseProgram((lkGLuint)prog);
  lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, (lkGLuint)tex1); lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, (lkGLuint)tex0); lk_glActiveTexture((lkGLenum)act);
  lk_glViewport(vp[0], vp[1], vp[2], vp[3]); lk_glScissor(sc[0], sc[1], sc[2], sc[3]); if (scis) lk_glEnable(0x0C11); if (blend) lk_glEnable(0x0BE2);
  lk_glBindBuffer(0x8892, (lkGLuint)abuf); lk_glPixelStorei(0x0CF2, unrow); lk_glPixelStorei(0x0CF5, unal);
  if (lk_gpu_frames++ < 3) { lkGLenum e = lk_glGetError(); if (e) { printf("gpu: GL error %%04X after the first draws: CPU filters from now on\n", (unsigned)e); lk_gpu_st = -1; return 0; } }
  (void)ow; return 1; }

''' % VER
    MODULE = MODULE.replace("@SHADER@", "\n".join('"%s\\n"' % l.replace("\\", "\\\\").replace('"', '\\"') for l in SHADER.strip("\n").split("\n")))
    a = "static void lk_disp_present(const uint8_t *framebuffer) {\n"
    rep(a, "static int lk_shot_png(const char *path, const uint32_t *px, int w, int h, int scale); static int lk_shot_wanted(const char *list, long n);   /* (LK_SHOT, defined below) */\n" + MODULE + a)
    # the GPU draws the destination rectangle instead of the CPU filter bands
    a = "    if ((lk_fx_mode != LK_FX_OFF || lk_sb_cpu) && r.w <= LK_MAXDIM && r.h <= LK_MAXDIM && r.w >= LK_SRC_W && r.h >= LK_SRC_H) {\n        if (!lk_fx_tex || lk_fx_tw != r.w || lk_fx_th != r.h) {"
    rep(a, "    if (lk_gpu_present(framebuffer, sw, &r, ow, oh, (lk_fx_mode != LK_FX_OFF && r.w >= LK_SRC_W && r.h >= LK_SRC_H) ? lk_fx_mode : 0)) { }   /* %s */\n    else " % VER + a.lstrip())
    # test aid: the presented CPU picture
    a = "            SDL_UpdateTexture(lk_fx_tex, NULL, lk_fx_buf, r.w * 4);\n            SDL_Rect d = { r.x, r.y, r.w, r.h }; SDL_RenderCopy(s_renderer, lk_fx_tex, NULL, &d);"
    rep(a, "            { static int shot = -1; static const char *list; if (shot < 0) { list = getenv(\"LANDSTALKER_PRESENT_SHOT\"); shot = list != 0; }   /* %s test aid: the presented CPU picture */\n" % VER +
           "              if (shot && lk_shot_wanted(list, platform_frame_number())) { char pth[700]; const char *dd = getenv(\"LANDSTALKER_SHOT_DIR\"); snprintf(pth, sizeof pth, \"%s/present_%06ld_cpu.png\", dd ? dd : \".\", platform_frame_number()); lk_shot_png(pth, lk_fx_buf, r.w, r.h, 1); } }\n" + a)
    # OpenGL renderer when the option is on (Windows defaults to Direct3D)
    a = "    s_renderer = SDL_CreateRenderer(s_window, -1,\n        SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);"
    rep(a, "    { extern int lk_gpu_get(void); if (lk_gpu_get() && !getenv(\"SDL_RENDER_DRIVER\")) SDL_SetHint(SDL_HINT_RENDER_DRIVER, \"opengl\"); }   /* %s: the GPU filters need SDL's OpenGL renderer */\n" % VER + a +
           "\n    if (!s_renderer) { SDL_SetHint(SDL_HINT_RENDER_DRIVER, \"\"); s_renderer = SDL_CreateRenderer(s_window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC); }   /* (no OpenGL: any renderer, CPU filters) */")
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)
else:
    print("platform_sdl.c already patched:", VER)
