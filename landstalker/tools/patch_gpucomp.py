#!/usr/bin/env python3
"""Picture composition on the GPU, STEP 4 (docs/RENDERER_IDEAS.md 'STEP 4'; user 2026-11-07: '1' = start STEP 4).
Stage 4a = the COMPARE HARNESS, nothing changes for the player: with LANDSTALKER_GPUCOMP=2 (test aid) the own map renderer (lk_own_row) records per
map line its state (picture position U0 / V, black line, text box / window line flags, window range wlo..whi, smooth move shift, backdrop, black colours),
the line's 64 colour palette, the window plane pixels (HUD rows / text box, lk_o_win) and per pixel its own result (pick = palette index, src = 1 sprite,
2 layer A, 3 layer B, 4 window, 0 backdrop; black) + the colour before boot colours / light / effects.  At the next present the GPU composes the same
lines from the room's layer cells (lk_o_pa / pb), the tile pixels (lk_o_tiles) and the sprite buffer (lk_o_spr, still built by the CPU) in an offscreen pass
(FBO 448 x 224, one fragment shader, two draws: colour / meta), reads both back and compares.
Lines that use what 4a does not cover are not recorded: the seamless room change (lk_sm_state != 0), the neighbour rooms of the seam option (lk_nbn > 0).
Console every 300 compared frames: 'gpucomp: frames F lines L pixels P exact E meta-diff M colour-diff C (backdrop / sprite / A / B / window / black pixel counts)' + the first 12 differences
('gpucomp: diff frame .. line .. i .. cpu pick/src/black .. colour .. gpu ..').
Needs patch_own.py (+ the effect patches whose anchors it uses), patch_gpu.py, patch_gpulight.py before it.  Idempotent.  usage: patch_gpucomp.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_GPUCOMP v1"

# ---------------------------------------------------------------- vdp_render.c: capture of the compositor's state per line
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, ("vdp_render.c: anchor not found once", a[:90], s.count(a))
    s = s.replace(a, b)

if VER not in s:
    MODULE = r'''/* ---- %s: picture composition on the GPU, stage 4a = compare harness (tools/patch_gpucomp.py, docs/RENDERER_IDEAS.md 'STEP 4') ---- */
static int lk_gc_mode = -2;   /* LANDSTALKER_GPUCOMP: 0 off (default), 2 compare harness (test aid) */
int lk_gc_getmode(void) { if (lk_gc_mode == -2) { const char *e = getenv("LANDSTALKER_GPUCOMP"); lk_gc_mode = e ? atoi(e) : 0; if (lk_gc_mode != 2) lk_gc_mode = 0; } return lk_gc_mode; }
uint16_t lk_gc_ref[224 * 448];   /* the CPU's result per pixel: 0x8000 | black ? 0x200 : pick | src << 6 */
uint32_t lk_gc_col[224 * 448];   /* the CPU's colour (before boot colours / light / effects) */
uint8_t lk_gc_rows[224 * 8 * 4]; /* per line 8 RGBA texels: 0 U0 lo hi, V lo hi | 1 flags, e, wlo lo hi | 2 whi lo hi, w lo hi | 3 sxn lo hi, syn lo hi | 4 backdrop | 5 margin black RGB | 6 black RGB */
uint32_t lk_gc_pal[224 * 64];    /* the palette of every line (as the CPU picks it: lk_o_pix / warp pad lk_o_fxpix / pixel[]) */
uint16_t lk_gc_win[224 * 320];   /* window plane pixel + 1 (0 = none; also 0 where the Modern HUD hides the HUD rows) */
long lk_gc_rowfr[224], lk_gc_capfr = -9;
long lk_gc_fx[12];   /* recorded lines with: 0 boot colours, 1 water, 2 clouds, 3 haze, 4 dissolve, 5 sword fx, 6 Modern HUD, 7 smooth sub-pixel, 8 HD, 9 depth fx, 10 lit windows, 11 GPU light */
const uint32_t *lk_gc_planes(void) { return &lk_o_pa[0][0]; }   /* lk_o_pa then lk_o_pb (152 x 304 each, bit 16 = present, low 16 = tile word) */
const uint32_t *lk_gc_planesb(void) { return &lk_o_pb[0][0]; }
const uint8_t *lk_gc_tiles(void) { return lk_o_tiles; }          /* 0x12000 bytes, 4 bits per pixel */
const uint16_t *lk_gc_spr(void) { return &lk_o_spr[0][0]; }     /* 224 x 448: pal * 16 + index | 0x100 priority | 0x200 present | 0x400 behind the text box */
static void lk_gc_put32(uint8_t *q, uint32_t c) { q[0] = (uint8_t)(c >> 16); q[1] = (uint8_t)(c >> 8); q[2] = (uint8_t)c; q[3] = 255; }
static int lk_gc_linebegin(int line, int w, int e, int u0, int v, int black_line, int text, int wline, int tb, int nohud, int wlo, int whi, int hint) {
  uint8_t *q = lk_gc_rows + line * 32; int x, k; const PIXEL_OUT_T *pl;
  if (line < 0 || line >= 224 || w > 448 || lk_sm_state != 0 || lk_nbn > 0) return 0;   /* 4a: no seamless room change, no neighbour rooms */
  if (!lk_o_palmode) pl = pixel; else if (lk_o_fxon) { k = lk_o_fxk[line & 255]; if (k < 0 || k > 7) return 0; pl = lk_o_fxpix[k]; } else pl = lk_o_pix;
  for (k = 0; k < 64; k++) lk_gc_pal[line * 64 + k] = (uint32_t)pl[k];
  memset(q, 0, 32);
  q[0] = (uint8_t)u0; q[1] = (uint8_t)(u0 >> 8); q[2] = (uint8_t)v; q[3] = (uint8_t)(v >> 8);
  q[4] = (uint8_t)((black_line ? 1 : 0) | (text ? 2 : 0) | (wline ? 4 : 0) | (tb ? 8 : 0) | (nohud ? 16 : 0) | 32); q[5] = (uint8_t)e; q[6] = (uint8_t)wlo; q[7] = (uint8_t)(wlo >> 8);
  q[8] = (uint8_t)whi; q[9] = (uint8_t)(whi >> 8); q[10] = (uint8_t)w; q[11] = (uint8_t)(w >> 8);
  q[12] = (uint8_t)lk_sm_sxn; q[13] = (uint8_t)(lk_sm_sxn >> 8); q[14] = (uint8_t)lk_sm_syn; q[15] = (uint8_t)(lk_sm_syn >> 8);
  q[16] = (uint8_t)(LK_REG(7) & 0x3F);
  lk_gc_put32(q + 20, (uint32_t)(lk_o_regvdp ? pixel[0x40] : lk_o_palmode ? lk_o_pix[LK_REG(7) & 0x3F] : pixel_lut[1][0]));
  lk_gc_put32(q + 24, (uint32_t)pixel_lut[1][0]);
  if ((line < 24 && !nohud) || (line >= 160 && (hint & 0xFF) == 0xA0)) { for (x = 0; x < 320; x++) { int wp = lk_o_win(line, x, hint); lk_gc_win[line * 320 + x] = (uint16_t)(wp + 1); } }
  else memset(lk_gc_win + line * 320, 0, 320 * sizeof(uint16_t));
  lk_gc_rowfr[line] = platform_frame_number(); lk_gc_capfr = lk_gc_rowfr[line];
  return 1; }
''' % VER
    a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
    rep(a, MODULE + a)
    a = "    int lk_cs_ln = lk_cs_linebegin();   /* LK_CLOUDS v1 */\n"
    rep(a, a + "    int lk_gc_ln = lk_gc_getmode() == 2 && lk_gc_linebegin(line, w, e, ubase - e - lk_sm_sxn, vbase - lk_sm_syn, black_line, text, wline, tb, nohud, wlo, whi, hint);   /* %s */\n" % VER
        + "    if (lk_gc_ln) { lk_gc_fx[0] += lk_bc_ln != 0; lk_gc_fx[1] += lk_wr_ln != 0; lk_gc_fx[2] += lk_cs_ln != 0; lk_gc_fx[3] += lk_hz_ln != 0; lk_gc_fx[4] += lk_dz_ln != 0; lk_gc_fx[5] += lk_sfx_ln != 0; lk_gc_fx[6] += nohud != 0; lk_gc_fx[7] += lk_ss_frac != 0; lk_gc_fx[8] += lk_hd_n != 0; lk_gc_fx[9] += fxon != 0; lk_gc_fx[10] += (lk_lt_ln && lk_dn_win) != 0; lk_gc_fx[11] += lk_gl_real != 0; }   /* %s: which effects the lines use */\n" % VER)
    a = "      lk_vh[line & 7][i] = (PIXEL_OUT_T)col; lk_vhv[line & 7][i] = (src == 0 || black || margin || (col & 0xFFFFFF) == 0) ? 1 : 0;\n"
    rep(a, a + "      if (lk_gc_ln) { lk_gc_ref[line * 448 + i] = (uint16_t)(0x8000 | (black ? 0x200 : ((pick & 0x3F) | (src << 6)))); lk_gc_col[line * 448 + i] = (uint32_t)col; }   /* %s */\n" % VER)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
else:
    print("vdp_render.c already patched:", VER)

# ---------------------------------------------------------------- platform_sdl.c: the GPU pass + compare at the present
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    MODULE = r'''/* ---- %s: picture composition on the GPU, stage 4a compare harness (tools/patch_gpucomp.py) ---- */
extern int lk_gc_getmode(void); extern uint16_t lk_gc_ref[224 * 448]; extern uint32_t lk_gc_col[224 * 448]; extern uint8_t lk_gc_rows[224 * 8 * 4]; extern uint32_t lk_gc_pal[224 * 64];
extern uint16_t lk_gc_win[224 * 320]; extern long lk_gc_rowfr[224], lk_gc_capfr, lk_gc_fx[12];
extern const uint32_t *lk_gc_planes(void); extern const uint32_t *lk_gc_planesb(void); extern const uint8_t *lk_gc_tiles(void); extern const uint16_t *lk_gc_spr(void);
static const char *lk_gc_fs = "#version 120\n"
"uniform sampler2D rows; uniform sampler2D pal; uniform sampler2D win; uniform sampler2D spr; uniform sampler2D pln; uniform sampler2D til; uniform float uMode;\n"
"float by(float v) { return floor(v * 255.0 + 0.5); }\n"
"float bit(float v, float n) { return mod(floor(v / exp2(n)), 2.0); }\n"
"float s16(float lo, float hi) { float v = by(lo) + 256.0 * by(hi); return v >= 32768.0 ? v - 65536.0 : v; }\n"
"float u16(float lo, float hi) { return by(lo) + 256.0 * by(hi); }\n"
"vec4 rowt(float c, float line) { return texture2D(rows, vec2((c + 0.5) / 8.0, (line + 0.5) / 224.0)); }\n"
"vec3 fetch(float U, float V, float layer) {\n"   /* lk_o_fetch: (colour index, palette, priority) of one layer pixel at picture position (U, V) */
"  if (U < 0.0 || V < 0.0 || U >= 2432.0 || V >= 1216.0) return vec3(0.0);\n"
"  float tc = floor(U / 8.0), tr = floor(V / 8.0), ix = U - tc * 8.0, iy = V - tr * 8.0;\n"
"  vec4 c = texture2D(pln, vec2((tc + 0.5) / 304.0, (tr + layer * 152.0 + 0.5) / 304.0));\n"
"  if (c.b < 0.5) return vec3(0.0);\n"
"  float lo = by(c.r), hi = by(c.g);\n"
"  if (bit(hi, 3.0) > 0.5) ix = 7.0 - ix; if (bit(hi, 4.0) > 0.5) iy = 7.0 - iy;\n"
"  float a = (lo + 256.0 * mod(hi, 8.0)) * 32.0 + iy * 4.0 + floor(ix / 2.0);\n"
"  float b = by(texture2D(til, vec2((mod(a, 1024.0) + 0.5) / 1024.0, (floor(a / 1024.0) + 0.5) / 72.0)).r);\n"
"  return vec3(mod(ix, 2.0) < 0.5 ? floor(b / 16.0) : mod(b, 16.0), mod(floor(hi / 32.0), 4.0), floor(hi / 128.0)); }\n"
"void main() {\n"
"  vec2 fc = floor(gl_FragCoord.xy); float i = fc.x, line = fc.y;\n"
"  vec4 r0 = rowt(0.0, line), r1 = rowt(1.0, line), r2 = rowt(2.0, line), r3 = rowt(3.0, line), r4 = rowt(4.0, line);\n"
"  float fl = by(r1.r), w = u16(r2.b, r2.a);\n"
"  if (bit(fl, 5.0) < 0.5 || i >= w) { gl_FragColor = vec4(0.0); return; }\n"
"  bool bline = bit(fl, 0.0) > 0.5, text = bit(fl, 1.0) > 0.5, wline = bit(fl, 2.0) > 0.5, tb = bit(fl, 3.0) > 0.5, nohud = bit(fl, 4.0) > 0.5;\n"
"  float U0 = s16(r0.r, r0.g), V = s16(r0.b, r0.a), e = by(r1.g), wlo = u16(r1.b, r1.a), whi = u16(r2.r, r2.g), sxn = s16(r3.r, r3.g), syn = s16(r3.b, r3.a);\n"
"  float x = i - e; bool margin = x < 0.0 || x >= 320.0;\n"
"  float sl = line - syn, si = i - sxn, sp = 0.0;\n"
"  if (sl >= 0.0 && sl < 224.0 && si >= 0.0 && si < 448.0) { vec4 t = texture2D(spr, vec2((si + 0.5) / 448.0, (sl + 0.5) / 224.0)); sp = by(t.r) + 256.0 * by(t.a); }\n"
"  bool s200 = bit(sp, 9.0) > 0.5, s100 = bit(sp, 8.0) > 0.5, s400 = bit(sp, 10.0) > 0.5;\n"
"  bool black = bline; float pick = 0.0, src = 0.0;\n"
"  if (!black) {\n"
"    vec3 A = fetch(U0 + i, V, 0.0), B = fetch(U0 + i, V, 1.0);\n"
"    if (s200 && s100) { pick = mod(sp, 64.0); src = 1.0; }\n"
"    else if (A.x > 0.0 && A.z > 0.0) { pick = A.y * 16.0 + A.x; src = 2.0; }\n"
"    else if (B.x > 0.0 && B.z > 0.0) { pick = B.y * 16.0 + B.x; src = 3.0; }\n"
"    else if (s200) { pick = mod(sp, 64.0); src = 1.0; }\n"
"    else if (A.x > 0.0) { pick = A.y * 16.0 + A.x; src = 2.0; }\n"
"    else if (B.x > 0.0) { pick = B.y * 16.0 + B.x; src = 3.0; }\n"
"    else pick = by(r4.r);\n"
"    if (margin) { if ((line < 23.0 && !nohud) || (wline && !tb)) black = true; }\n"
"    else { vec4 t = texture2D(win, vec2((x + 0.5) / 320.0, (line + 0.5) / 224.0)); float wp = by(t.r) + 256.0 * by(t.a) - 1.0;\n"
"      if (wp >= 0.0 && mod(wp, 16.0) > 0.0 && i >= wlo && i < whi) { if (!(text && s200 && s100 && !s400 && bit(wp, 9.0) < 0.5)) { pick = mod(wp, 64.0); src = 4.0; } }\n"
"      else if (wp >= 0.0 && !tb && wline) black = true; } }\n"
"  if (uMode > 0.5) { float m = black ? 512.0 : pick + 64.0 * src; gl_FragColor = vec4(mod(m, 256.0) / 255.0, floor(m / 256.0) / 255.0, 1.0, 1.0); return; }\n"
"  vec3 c = black ? (margin ? rowt(5.0, line).rgb : rowt(6.0, line).rgb) : texture2D(pal, vec2((pick + 0.5) / 64.0, (line + 0.5) / 224.0)).rgb;\n"
"  gl_FragColor = vec4(c, 1.0); }\n";
static int lk_gc_st; static lkGLuint lk_gc_prog, lk_gc_fbo, lk_gc_out, lk_gc_t[6]; static lkGLint lk_gc_u[7];
static long lk_gc_n, lk_gc_lines, lk_gc_px, lk_gc_ex, lk_gc_md, lk_gc_cd, lk_gc_src[6]; static int lk_gc_shown;
static int lk_gc_init(void) {
  static const char *un[] = { "rows", "pal", "win", "spr", "pln", "til", "uMode" }; lkGLint ok = 0; lkGLuint vs, fs; char log[2048]; int i;
  static const int tw[6] = { 8, 64, 320, 448, 304, 1024 }, th[6] = { 224, 224, 224, 224, 304, 72 }; static const lkGLenum tf[6] = { 0x1908, 0x1908, 0x190A, 0x190A, 0x1908, 0x1909 };
  if (!lk_glGenFramebuffers) { *(void **)&lk_glGenFramebuffers = lk_gpu_fn("glGenFramebuffers"); *(void **)&lk_glBindFramebuffer = lk_gpu_fn("glBindFramebuffer");
    *(void **)&lk_glFramebufferTexture2D = lk_gpu_fn("glFramebufferTexture2D"); *(void **)&lk_glCheckFramebufferStatus = lk_gpu_fn("glCheckFramebufferStatus"); }
  if (!lk_glGenFramebuffers || !lk_glBindFramebuffer || !lk_glFramebufferTexture2D || !lk_glCheckFramebufferStatus) { printf("gpucomp: GL functions missing\n"); return -1; }
  { static const char *vsrc = "#version 120\nvoid main() { gl_Position = gl_Vertex; }\n"; vs = lk_glCreateShader(0x8B31); lk_glShaderSource(vs, 1, &vsrc, 0); lk_glCompileShader(vs); lk_glGetShaderiv(vs, 0x8B81, &ok); if (!ok) return -1; }
  fs = lk_glCreateShader(0x8B30); lk_glShaderSource(fs, 1, &lk_gc_fs, 0); lk_glCompileShader(fs); lk_glGetShaderiv(fs, 0x8B81, &ok);
  if (!ok) { lk_glGetShaderInfoLog(fs, sizeof log, 0, log); printf("gpucomp: shader failed: %%s\n", log); return -1; }
  lk_gc_prog = lk_glCreateProgram(); lk_glAttachShader(lk_gc_prog, vs); lk_glAttachShader(lk_gc_prog, fs); lk_glLinkProgram(lk_gc_prog); lk_glGetProgramiv(lk_gc_prog, 0x8B82, &ok);
  if (!ok) { lk_glGetProgramInfoLog(lk_gc_prog, sizeof log, 0, log); printf("gpucomp: link failed: %%s\n", log); return -1; }
  for (i = 0; i < 7; i++) lk_gc_u[i] = lk_glGetUniformLocation(lk_gc_prog, un[i]);
  for (i = 0; i < 6; i++) { lk_glActiveTexture(0x84C0 + i); lk_gc_t[i] = lk_glt_tex(tw[i], th[i], tf[i], tf[i]); }
  lk_glActiveTexture(0x84C0); lk_gc_out = lk_glt_tex(448, 224, 0x1908, 0x1908);
  lk_glGenFramebuffers(1, &lk_gc_fbo); lk_glBindFramebuffer(0x8D40, lk_gc_fbo); lk_glFramebufferTexture2D(0x8D40, 0x8CE0, 0x0DE1, lk_gc_out, 0);
  ok = lk_glCheckFramebufferStatus(0x8D40) == 0x8CD5; lk_glBindFramebuffer(0x8D40, 0);
  { lkGLenum e = lk_glGetError(); if (e || !ok) { printf("gpucomp: setup failed (GL error %%04X, fbo %%d)\n", (unsigned)e, ok); return -1; } }
  printf("gpucomp: %s compare harness ready (LANDSTALKER_GPUCOMP=2)\n");
  return 1; }
static void lk_gc_pass(void) {   /* inside lk_gpu_present after SDL's state is saved (texture unit 0 active, unpack alignment 4) */
  static uint8_t pl[304 * 304 * 4], rows[224 * 32], col[224 * 448 * 4], meta[224 * 448 * 4]; static const lkGLfloat quad[8] = { -1, -1, 1, -1, -1, 1, 1, 1 };
  lkGLint fb0 = 0, tb[6], vp[4]; long fr = platform_frame_number(); int i, L, k, nl = 0; const uint32_t *pa, *pb;
  if (lk_gc_getmode() != 2 || lk_gc_st < 0 || lk_gc_capfr != fr - 1) return;
  for (i = 0; i < 6; i++) { lk_glActiveTexture(0x84C0 + i); lk_glGetIntegerv(0x8069, &tb[i]); }
  if (lk_gc_st == 0) { lk_gc_st = lk_gc_init(); if (lk_gc_st < 0) { for (i = 5; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); } return; } }
  lk_glGetIntegerv(0x8CA6, &fb0); lk_glGetIntegerv(0x0BA2, vp);
  memcpy(rows, lk_gc_rows, sizeof rows); for (L = 0; L < 224; L++) if (lk_gc_rowfr[L] != lk_gc_capfr) rows[L * 32 + 4] = 0; else nl++;   /* lines not recorded this frame: skipped */
  pa = lk_gc_planes(); pb = lk_gc_planesb();
  for (k = 0; k < 2; k++) { const uint32_t *P = k ? pb : pa; uint8_t *o = pl + k * 152 * 304 * 4; for (i = 0; i < 152 * 304; i++) { uint32_t c = P[i]; o[4 * i] = (uint8_t)c; o[4 * i + 1] = (uint8_t)(c >> 8); o[4 * i + 2] = (c & 0x10000) ? 255 : 0; o[4 * i + 3] = 255; } }
  lk_glActiveTexture(0x84C0); lk_glBindTexture(0x0DE1, lk_gc_t[0]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 8, 224, 0x1908, 0x1401, rows);
  lk_glActiveTexture(0x84C1); lk_glBindTexture(0x0DE1, lk_gc_t[1]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 64, 224, 0x80E1, 0x1401, lk_gc_pal);
  lk_glActiveTexture(0x84C2); lk_glBindTexture(0x0DE1, lk_gc_t[2]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 320, 224, 0x190A, 0x1401, lk_gc_win);
  lk_glActiveTexture(0x84C3); lk_glBindTexture(0x0DE1, lk_gc_t[3]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 448, 224, 0x190A, 0x1401, lk_gc_spr());
  lk_glActiveTexture(0x84C4); lk_glBindTexture(0x0DE1, lk_gc_t[4]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 304, 304, 0x1908, 0x1401, pl);
  lk_glActiveTexture(0x84C5); lk_glBindTexture(0x0DE1, lk_gc_t[5]); lk_glTexSubImage2D(0x0DE1, 0, 0, 0, 1024, 72, 0x1909, 0x1401, lk_gc_tiles());
  lk_glUseProgram(lk_gc_prog); for (i = 0; i < 6; i++) lk_glUniform1i(lk_gc_u[i], i);
  lk_glBindFramebuffer(0x8D40, lk_gc_fbo); lk_glViewport(0, 0, 448, 224); lk_glEnableClientState(0x8074); lk_glVertexPointer(2, 0x1406, 0, quad);
  lk_glUniform1f(lk_gc_u[6], 0.0f); lk_glDrawArrays(0x0005, 0, 4); lk_glReadPixels(0, 0, 448, 224, 0x1908, 0x1401, col);
  lk_glUniform1f(lk_gc_u[6], 1.0f); lk_glDrawArrays(0x0005, 0, 4); lk_glReadPixels(0, 0, 448, 224, 0x1908, 0x1401, meta);
  lk_glBindFramebuffer(0x8D40, (lkGLuint)fb0); lk_glViewport(vp[0], vp[1], vp[2], vp[3]);
  for (i = 5; i >= 0; i--) { lk_glActiveTexture(0x84C0 + i); lk_glBindTexture(0x0DE1, (lkGLuint)tb[i]); }
  lk_gc_n++; lk_gc_lines += nl;
  for (L = 0; L < 224; L++) { int w; if (!(rows[L * 32 + 4] & 32)) continue; w = rows[L * 32 + 10] | (rows[L * 32 + 11] << 8);
    for (i = 0; i < w && i < 448; i++) { int o = L * 448 + i; uint16_t rf = lk_gc_ref[o]; uint32_t cc = lk_gc_col[o] & 0xFFFFFFu, gc = ((uint32_t)col[4 * o] << 16) | ((uint32_t)col[4 * o + 1] << 8) | col[4 * o + 2];
      int gm = meta[4 * o] | (meta[4 * o + 1] << 8), cm = rf & 0x3FF, bm = gm != cm, bc = gc != cc;
      if (!(rf & 0x8000)) continue;
      lk_gc_px++; lk_gc_src[(cm & 0x200) ? 5 : ((cm >> 6) & 7) > 4 ? 4 : ((cm >> 6) & 7)]++; if (!bm && !bc) { lk_gc_ex++; continue; } if (bm) lk_gc_md++; if (bc) lk_gc_cd++;
      if (lk_gc_shown < 12) { lk_gc_shown++; printf("gpucomp: diff frame %%ld line %%d i %%d cpu pick %%d src %%d black %%d colour %%06X | gpu pick %%d src %%d black %%d colour %%06X\n", fr - 1, L, i,
        cm & 63, (cm >> 6) & 7, (cm >> 9) & 1, (unsigned)cc, gm & 63, (gm >> 6) & 7, (gm >> 9) & 1, (unsigned)gc); } } }
  if (lk_gc_n %% 300 == 0) printf("gpucomp: frames %%ld lines %%ld pixels %%ld exact %%ld meta-diff %%ld colour-diff %%ld (backdrop %%ld sprite %%ld A %%ld B %%ld window %%ld black %%ld)\n", lk_gc_n, lk_gc_lines, lk_gc_px, lk_gc_ex, lk_gc_md, lk_gc_cd,
    lk_gc_src[0], lk_gc_src[1], lk_gc_src[2], lk_gc_src[3], lk_gc_src[4], lk_gc_src[5]);
  if (lk_gc_n %% 300 == 0) printf("gpucomp: lines with: boots %%ld water %%ld clouds %%ld haze %%ld dissolve %%ld swordfx %%ld modernhud %%ld subpix %%ld hd %%ld depthfx %%ld litwin %%ld gpulight %%ld\n", lk_gc_fx[0], lk_gc_fx[1], lk_gc_fx[2], lk_gc_fx[3], lk_gc_fx[4], lk_gc_fx[5], lk_gc_fx[6], lk_gc_fx[7], lk_gc_fx[8], lk_gc_fx[9], lk_gc_fx[10], lk_gc_fx[11]);
}
''' % (VER, VER)
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
