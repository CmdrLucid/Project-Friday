#!/usr/bin/env python3
"""Project-Friday branding on the title screen (2026-10-15, user wish): the words 'PROJECT FRIDAY' are drawn into the finished picture
(vdp_render.c, after the pixel conversion, same hook place as the shadow / quick HUD) while the final title screen runs (`WaitForStartGame $039988`; the logo animation before it `TitleScreenSwordSlash $0399CC` stays clean).
Picture only: nothing is written to the game's RAM / VRAM, so the title screen is byte-identical for the game. Own 5x7 letters scaled x2, blue fill + yellow outline like the logo.
Also the window of the file select options (LK_WIN v1, 2026-10-15): the game side (tools/patch_options.py, lk_fs_modal) renders the row texts with the game's own text engine into
RAM and copies the pixels to lk_win_row[]; this file draws a purple window with the game's white rounded frame and the golden selection corners over the picture (picture only).
Env LANDSTALKER_BRAND=0 switches it off, LANDSTALKER_BRAND_Y=N moves it (default 198).  Idempotent.  usage: patch_overlay.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_BRAND v1"
VER2 = "LK_WIN v1"

p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    a = "void remap_line(int line)\n{\n"
    assert s.count(a) == 1, "vdp_render.c: remap_line layout changed"
    b = "  /* Adjust line offset in framebuffer */\n  line = (line + bitmap.viewport.y) % lines_per_frame;\n"
    assert s.count(b) == 1
    s = s.replace(b, "  lk_br_line = line;   /* LK_BRAND v1 */\n" + b, 1)
    d = "      lk_quick_hud(lk_row0, lk_w0);   /* LK_QUICK v1 */\n"
    assert s.count(d) == 1, "vdp_render.c: run patch_quick.py first"
    s = s.replace(d, d + "      lk_brand_row(lk_row0, lk_w0);   /* LK_BRAND v1 */\n", 1)
    c = "void render_line(int line)"
    assert s.count(c) == 1
    module = r'''/* ---- LK_BRAND v1: 'PROJECT FRIDAY' on the title screen (tools/patch_overlay.py) ---- */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
int lk_brand_on;   /* set by the game side while the title loop runs */
static int lk_br_line;
#define LK_BR_S 2          /* letter scale */
#define LK_BR_O 1          /* outline width in picture pixels */
#define LK_BR_W (14 * 6 * LK_BR_S + 2 * LK_BR_O)
#define LK_BR_WAVE 0       /* baseline swing in px (2 = wavy like the logo; the user preferred it flat); the map is 2 * this taller */
#define LK_BR_H (7 * LK_BR_S + 2 * LK_BR_O + 2 * LK_BR_WAVE)
static uint8 lk_br_map[LK_BR_H][LK_BR_W];   /* 0 empty, 1 fill, 2 outline */
static int lk_br_ready, lk_br_y = -1;
static const uint8 *lk_br_glyph(char ch) {
  static const uint8 P[7] = {30,17,17,30,16,16,16}, R[7] = {30,17,17,30,20,18,17}, O[7] = {14,17,17,17,17,17,14}, J[7] = {7,2,2,2,2,18,12}, E[7] = {31,16,16,30,16,16,31},
    C[7] = {14,17,16,16,16,17,14}, T[7] = {31,4,4,4,4,4,4}, F[7] = {31,16,16,30,16,16,16}, I[7] = {14,4,4,4,4,4,14}, D[7] = {30,17,17,17,17,17,30}, A[7] = {14,17,17,31,17,17,17}, Y[7] = {17,17,10,4,4,4,4}, B[7] = {0,0,0,0,0,0,0};
  switch (ch) { case 'P': return P; case 'R': return R; case 'O': return O; case 'J': return J; case 'E': return E; case 'C': return C; case 'T': return T; case 'F': return F; case 'I': return I; case 'D': return D; case 'A': return A; case 'Y': return Y; default: return B; }
}
static void lk_br_build(void) {
  static const char *t = "PROJECT FRIDAY";
  int i, r, c, y, x, dy, dx;
  memset(lk_br_map, 0, sizeof lk_br_map);
  for (i = 0; t[i]; i++) { const uint8 *g = lk_br_glyph(t[i]);
    for (r = 0; r < 7; r++) for (c = 0; c < 5; c++) if (g[r] & (0x10 >> c))
      for (y = 0; y < LK_BR_S; y++) for (x = 0; x < LK_BR_S; x++) lk_br_map[LK_BR_WAVE + LK_BR_O + r * LK_BR_S + y][LK_BR_O + (i * 6 + c) * LK_BR_S + x] = 1; }
  { static uint8 tmp[LK_BR_H][LK_BR_W]; memcpy(tmp, lk_br_map, sizeof tmp); memset(lk_br_map, 0, sizeof lk_br_map);   /* swing every column up / down */
    for (x = 0; x < LK_BR_W; x++) { int d = (int)floor(LK_BR_WAVE * sin(x * 0.085) + 0.5); for (y = 0; y < LK_BR_H; y++) { int yy = y + d; if (yy >= 0 && yy < LK_BR_H) lk_br_map[yy][x] = tmp[y][x]; } } }
  for (y = 0; y < LK_BR_H; y++) for (x = 0; x < LK_BR_W; x++) if (lk_br_map[y][x] == 1)
    for (dy = -LK_BR_O; dy <= LK_BR_O; dy++) for (dx = -LK_BR_O; dx <= LK_BR_O; dx++) {
      int yy = y + dy, xx = x + dx;
      if (yy >= 0 && yy < LK_BR_H && xx >= 0 && xx < LK_BR_W && lk_br_map[yy][xx] == 0) lk_br_map[yy][xx] = 2; }
  { const char *e = getenv("LANDSTALKER_BRAND_Y"); lk_br_y = e && *e ? atoi(e) : 198; }
  lk_br_ready = 1;
}
static void lk_brand_row(PIXEL_OUT_T *row, int width) {
  int line = lk_br_line, Wp = bitmap.viewport.w, ox = bitmap.viewport.x, y, x, x0;
  PIXEL_OUT_T *r;
  static int off = -1;
  if (!lk_brand_on) return;
  if (off < 0) { const char *e = getenv("LANDSTALKER_BRAND"); off = e && *e && atoi(e) == 0; }
  if (off) return;
  if (!lk_br_ready) lk_br_build();
  y = line - lk_br_y;
  if (y < 0 || y >= LK_BR_H) return;
  if (Wp < 320 || width < Wp + 2 * ox) return;
  r = row + ox; x0 = (Wp - LK_BR_W) / 2;
  for (x = 0; x < LK_BR_W; x++) {
    int m = lk_br_map[y][x];
    if (m == 1) r[x0 + x] = 0xFF5050F0u | (r[x0 + x] & 0xFF000000u);          /* fill: the logo's blue (a little brighter at the top) */
    else if (m == 2) r[x0 + x] = 0xFFF0E850u | (r[x0 + x] & 0xFF000000u);     /* outline: the logo's yellow */
  }
}
'''
    s = s.replace(c, module + c, 1)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)

s = open(p).read()
if VER2 not in s:
    d = "      lk_brand_row(lk_row0, lk_w0);   /* LK_BRAND v1 */\n"
    assert s.count(d) == 1
    s = s.replace(d, d + "      lk_win_draw(lk_row0, lk_w0);   /* LK_WIN v1 */\n", 1)
    c = "void render_line(int line)"
    module = r'''/* ---- LK_WIN v1: options window over the file select (tools/patch_overlay.py; rows are filled by tools/patch_options.py) ---- */
int lk_win_on, lk_win_sel = -1, lk_win_blink, lk_win_n, lk_win_pitch = 28, lk_win_compact;   /* row pitch; compact = the 24 px selection frame of the Video page (like the Start menu: the full frame would enclose almost two rows) */
uint8 lk_win_row[8][16][288];
uint8 lk_win_arrow[16][16]; int lk_win_arr;   /* scroll arrow (ROM graphic ArrowGraphic2BPP, copied at run time), bit 0 = up arrow, bit 1 = down arrow (flipped) */
uint8 lk_win_cur[32][32];   /* selection frame graphic, colour indices 0 (transparent) .. 3 */   /* per row: 288 x 16 text pixels (1 = glyph), copied from the game's text buffer */
#define LK_WIN_X 17
#define LK_WIN_Y 9
#define LK_WIN_W 286
#define LK_WIN_H 158
static int lk_win_class(int lx, int ly) {   /* 0 outside, 1 white frame, 2 black ring, 3 purple: the look of the game's slot windows (measured on the file select screenshot) */
  static const char T[5][6] = { "TTWWW", "TWWWW", "WWWKK", "WWKKP", "WWKPP" };
  int mx = lx < LK_WIN_W - 1 - lx ? lx : LK_WIN_W - 1 - lx, my = ly < LK_WIN_H - 1 - ly ? ly : LK_WIN_H - 1 - ly;
  if (mx < 5 && my < 5) { char ch = T[my][mx]; return ch == 'T' ? 0 : ch == 'W' ? 1 : ch == 'K' ? 2 : 3; }
  if (mx <= 1 || my <= 1) return 1;
  if (mx == 2 || my == 2) return 2;
  return 3;
}
static void lk_win_draw(PIXEL_OUT_T *row, int width) {
  int ly, lx, Wp = bitmap.viewport.w, ox = bitmap.viewport.x, xo;
  PIXEL_OUT_T *r;
  if (!lk_win_on) return;
  ly = lk_br_line - LK_WIN_Y;
  if (ly < 0 || ly >= LK_WIN_H) return;
  if (Wp < 320 || width < Wp + 2 * ox) return;
  r = row + ox; xo = (Wp - 320) / 2 + LK_WIN_X;
  for (lx = 0; lx < LK_WIN_W; lx++) {
    int cl = lk_win_class(lx, ly);
    PIXEL_OUT_T col;
    if (!cl) continue;
    col = cl == 1 ? 0xFFEEEEEEu : cl == 2 ? 0xFF000000u : 0xFF442288u;
    if (cl == 3) {
      int pt = lk_win_pitch, tt = (pt - 16) / 2, t = ly - 8, k = t >= 0 ? t / pt : -1, off = t >= 0 ? t % pt - tt : -1;   /* off = row inside the 16 px text bitmap */
      if (k >= 0 && k < lk_win_n) {
        int bx = lx - 20;
        if (off >= 0 && off < 16 && bx >= 0 && bx < 288 && lk_win_row[k][off][bx]) col = 0xFFEEEEEEu;
      }
      if (lk_win_sel >= 0 && !lk_win_blink) {   /* the game's own selection frame (MenuCursor2BPP, 32 x 32 = four corner pieces, copied from the ROM by the game side), centred on the text line; compact (Video page) = top and bottom tile row only, 24 px */
        int ft = 8 + lk_win_sel * pt + tt - (lk_win_compact ? 4 : 8), cy = ly - ft, gy = -1, cx = -1, idx;
        if (lk_win_compact) { if (cy >= 0 && cy < 8) gy = cy; else if (cy >= 16 && cy < 24) gy = 24 + (cy - 16); } else if (cy >= 0 && cy < 32) gy = cy;
        if (gy >= 0) {
          if (lx >= 4 && lx < 20) cx = lx - 4; else if (lx >= LK_WIN_W - 20 && lx < LK_WIN_W - 4) cx = 16 + (lx - (LK_WIN_W - 20));
          if (cx >= 0 && (idx = lk_win_cur[gy][cx]) != 0) col = idx == 1 ? 0xFFAA6600u : idx == 2 ? 0xFFCCAA00u : 0xFF000000u;
        }
      }
    }
    if (cl == 3 && lk_win_arr && lx >= 0 && lx < 16) {   /* the game's scroll arrows (Use list): left of the rows, up near the title, down at the bottom */
      static const PIXEL_OUT_T ac[4] = { 0, 0xFFDBDBDBu, 0xFF494949u, 0xFF000000u };
      int ay = ly - 6, idx;
      if ((lk_win_arr & 1) && ay >= 0 && ay < 16 && (idx = lk_win_arrow[ay][lx]) != 0) col = ac[idx];
      ay = ly - (LK_WIN_H - 24);
      if ((lk_win_arr & 2) && ay >= 0 && ay < 16 && (idx = lk_win_arrow[15 - ay][lx]) != 0) col = ac[idx];
    }
    r[xo + lx] = col;
  }
}
'''
    s = s.replace(c, module + c, 1)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER2)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "lk_shadow_install" in s, "func_table.c: run patch_shadow.py first"
    module = r'''/* ---- LK_BRAND v1: title screen branding flag (tools/patch_overlay.py) ---- */
extern int lk_brand_on;
static gen_func_t lk_o_title;
static void lk_h_title(void) { lk_brand_on = 1; lk_o_title(); lk_brand_on = 0; }   /* WaitForStartGame $039988: the final title screen (PUSH START BUTTON) until START */
static void lk_brand_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_title = func_table_lookup(0x039988);
    if (lk_o_title) func_table_register(0x039988, lk_h_title); else fprintf(stderr, "brand: title loop not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_shadow_install();   /* LANDSTALKER shadow option */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_brand_install();   /* LK_BRAND v1 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
