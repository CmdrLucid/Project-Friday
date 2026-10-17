#!/usr/bin/env python3
"""Model overlay (2026-10-17, renderer groundwork, RENDERER_IDEAS Option B step 1): draws what the game STATE says is on screen over the normal picture, so the two can be compared.
For every visible entity (list g_VisibleEntityList $FF11DE) it draws, from work RAM only (picture only, nothing is written to the game):
 * a cross at the position the game stored for the sprite (+0E x / +10 y, minus $80) in a colour per slot,
 * the diamond of the hit box (+18 x1, +1A x2, +1C y1, +1E y2) on the floor under the entity at its Z, projected with OUR copy of the game's formula
   (CheckEntityOnScreen $004144: a = X - Z - cam$FF1200, b = Y - Z - cam$FF1202, screen x = a - b + $A0, screen y = ((a + b + k) >> 1) + $68, k = 0 for the player else word $FF1180 ^ 1),
 * a tiny label: sprite graphic id, animation / 4, frame / 4 in hex (the stable sprite key, FORMATS.md 'Sprite upload').
Block grid (v2): every cell of the height map ($FFD192, words, 74 x 74, cell (x, y) = world units x * 16 .. x * 16 + 15, byte 0: low nibble = floor height in 16 unit steps, high nibble 4 with height 0 = void)
that is not void is outlined as a diamond at its floor height with the same projection; colour = height (grey 0, cyan 1, green 2, yellow 3, orange 4, red 5, pink 6, white 7), purple = cells blocked for everybody or for NPCs (byte 0 bits 6 / 5), a CROSS through the cell = floor type (byte 1): yellow doors, green stairs / ladders / elevator / Nole staircase, red pit / spikes / swamp / lava, white others,
the cell under Nigel is white-bordered.  Modes (R3 / F7 cycles): off -> cells (height map grid) -> blocks (16x16 block squares of both map layers, ids of the BG layer in hex) -> off. Toggle at run time: pad R3 (click of the right stick) or key F7 (fixed, not in the Keybindings list); LANDSTALKER_MODEL=1 starts with it on,
LANDSTALKER_MODEL_AT="f1,f2" toggles at those frames (headless tests); LANDSTALKER_MODEL_GRID=0 hides the grid.
Env LANDSTALKER_MODEL=1 switches it on (off by default, debug aid); LANDSTALKER_MODEL_LOG=N prints, every N frames, per entity the game's screen position and the model's (they must agree).
The overlay shows the snapshot of the PREVIOUS frame (the picture itself is one frame behind the RAM, see the C comment), so it does not slide against the background during jumps.  Hidden while a full-screen picture is shown (lk_picture).  Needs patch_wide.py and patch_overlay.py first.  Idempotent.  usage: patch_model.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_MODEL v2"
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    d = "      lk_win_draw(lk_row0, lk_w0);   /* LK_WIN v1 */\n"
    assert s.count(d) == 1, "vdp_render.c: run patch_overlay.py first"
    s = s.replace(d, d + "      lk_model_row(lk_row0, lk_w0);   /* LK_MODEL v2 */\n", 1)
    c = "void render_line(int line)"
    assert s.count(c) == 1
    module = r'''/* ---- LK_MODEL v2: state-driven model overlay (tools/patch_model.py) ---- */
extern uint8_t *bus_get_ram(void);
extern int lk_picture;
#define LK_M_N 16
typedef struct { int ax, ay, gx[4], gy[4], id, m_g, m_a, m_f; } lk_m_ent_t;
static lk_m_ent_t lk_m_e[LK_M_N], lk_m_de[LK_M_N]; static int lk_m_dn, lk_m_n, lk_m_on = -1, lk_m_log, lk_m_grid = 1;   /* lk_m_on: 0 off, 1 cells + entities, 2 block ids + entities */
#define LK_MM_W 960
#define LK_MM_H 512
#define LK_MM_X0 320   /* mask column of picture x = 0 (margins of wide pictures are negative x) */
static uint8 lk_m_mask[LK_MM_H][LK_MM_W], lk_m_dmask[LK_MM_H][LK_MM_W];   /* write buffer (snapshot of this frame) / display buffer (snapshot of the PREVIOUS frame: the game's scroll registers and sprite table are written at VBlank from the RAM state of the previous pass, measured: vscroll(t) = camera(t - 1) + const, so the picture lags the RAM by one frame and a live snapshot slides ahead of it in jumps) */   /* 0 none, 1..8 height colours, 9 special cell, 10 border of Nigel's cell */
static const uint32 lk_m_gcol[18] = { 0, 0xFF909090u, 0xFF40C0FFu, 0xFF60FF60u, 0xFFFFFF60u, 0xFFFFA040u, 0xFFFF6060u, 0xFFFF60FFu, 0xFFFFFFFFu, 0xFFB040E0u, 0xFFFFFFFFu,
                                      0xFFFFE000u, 0xFF00FF80u, 0xFFFF2020u, 0xFFFFFFFFu, 0xFF3090B0u, 0xFFB07030u, 0xFFFFFFFFu };   /* 15 BG block square, 16 FG block square, 17 block id text; 11 door, 12 stairs / ladder / elevator, 13 hazard, 14 other floor type: cross through the cell */
static void lk_m_init(void) { if (lk_m_on < 0) { const char *e = getenv("LANDSTALKER_MODEL"), *l = getenv("LANDSTALKER_MODEL_LOG"), *g = getenv("LANDSTALKER_MODEL_GRID"); lk_m_on = e ? atoi(e) : 0; if (lk_m_on > 2) lk_m_on = 1; lk_m_log = l ? atoi(l) : 0; lk_m_grid = !(g && atoi(g) == 0); } }
int lk_model_toggle(void) { lk_m_init(); lk_m_on = (lk_m_on + 1) % 3; return lk_m_on; }   /* off -> cells -> blocks -> off */
static void lk_m_seg(int x0, int y0, int x1, int y1, uint8 v) {   /* Bresenham into the mask (a later segment never overwrites a higher value: the player's border wins) */
  int dx = x1 > x0 ? x1 - x0 : x0 - x1, dy = y1 > y0 ? y1 - y0 : y0 - y1, sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, err = dx - dy;
  for (;;) {
    int mx = x0 + LK_MM_X0;
    if (mx >= 0 && mx < LK_MM_W && y0 >= 0 && y0 < LK_MM_H && lk_m_mask[y0][mx] < v) lk_m_mask[y0][mx] = v;
    if (x0 == x1 && y0 == y1) break;
    { int e2 = 2 * err; if (e2 > -dy) { err -= dy; x0 += sx; } if (e2 < dx) { err += dx; y0 += sy; } }
  }
}
static const uint8 lk_m_font[16] [5] = { {7,5,5,5,7},{2,6,2,2,7},{7,1,7,4,7},{7,1,7,1,7},{5,5,7,1,1},{7,4,7,1,7},{7,4,7,5,7},{7,1,1,1,1},
                                         {7,5,7,5,7},{7,5,7,1,7},{2,5,7,5,5},{6,5,6,5,6},{3,4,4,4,3},{6,5,5,5,6},{7,4,6,4,7},{7,4,6,4,4} };
static const uint32 lk_m_col[LK_M_N] = { 0xFFFFFF40u, 0xFF40FF40u, 0xFFFF6060u, 0xFF60C0FFu, 0xFFFF80FFu, 0xFFFFA030u, 0xFF40FFFFu, 0xFFC0C0C0u,
                                         0xFFFF4040u, 0xFF80FF80u, 0xFF8080FFu, 0xFFFFE080u, 0xFF80FFE0u, 0xFFE080FFu, 0xFFA0A060u, 0xFFFFFFFFu };
#define LKB(a) (r[((a) & 0xFFFF) ^ 1])
#define LKW(a) ((int)((LKB(a) << 8) | LKB((a) + 1)))
#define LKS(a) ((int)(int16_t)LKW(a))
static void lk_m_snapshot(void) {
  const uint8_t *r = bus_get_ram(); int cam0 = LKS(0xFF1200), cam2 = LKS(0xFF1202), k1 = (LKW(0xFF1180) ^ 1) & 0xFFFF, a, i, c;
  lk_m_n = 0;
  if (!r) return;
  memset(lk_m_mask, 0, sizeof lk_m_mask);
  if (lk_m_grid && lk_m_on == 2) {   /* block ids: screen position of array block (x, y) = 16 (x - y) + (cam2 - cam0 + 160) [FG layer: another -16], 8 (x + y) - (cam0 + cam2) / 2 + 104 (fit on 299 plane / array pairs, FORMATS 'Block map') */
    int x, y, lay;
    for (lay = 0; lay < 2; lay++) for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
      int id = LKW((lay ? 0xFF7C02 : 0xFFA6CA) + 148 * y + 2 * x) & 0x3FF, bx, by, d;
      if (!id) continue;
      bx = 16 * (x - y) + (cam2 - cam0 + 160) - (lay ? 16 : 0); by = 8 * (x + y) - ((cam0 + cam2) >> 1) + 104;
      if (bx < -220 || bx > 540 || by < -20 || by > 260) continue;
      lk_m_seg(bx, by, bx + 15, by, lay ? 16 : 15); lk_m_seg(bx + 15, by, bx + 15, by + 15, lay ? 16 : 15); lk_m_seg(bx + 15, by + 15, bx, by + 15, lay ? 16 : 15); lk_m_seg(bx, by + 15, bx, by, lay ? 16 : 15);
      if (!lay) for (d = 0; d < 3; d++) { int dig = (id >> (8 - 4 * d)) & 15, rr, cc; for (rr = 0; rr < 5; rr++) for (cc = 0; cc < 3; cc++) if (lk_m_font[dig][rr] & (4 >> cc)) { int mx = bx + 2 + d * 4 + cc + LK_MM_X0, my = by + 5 + rr; if (mx >= 0 && mx < LK_MM_W && my >= 0 && my < LK_MM_H) lk_m_mask[my][mx] = 17; } }
    }
  }
  if (lk_m_grid && lk_m_on == 1) {
    int px = LKB(0xFF5400), py = LKB(0xFF5401), cx, cy;
    for (cy = 0; cy < 74; cy++) for (cx = 0; cx < 74; cx++) {
      int b0 = LKB(0xFFD192 + 148 * cy + 2 * cx), b1 = LKB(0xFFD192 + 148 * cy + 2 * cx + 1) & 0x3F, h = b0 & 15, t = b0 >> 4, z, sxx[4], syy[4], k, v, ccx, ccy;
      if (t == 4 && h == 0) continue;
      z = h * 16;
      for (k = 0; k < 4; k++) {
        int wx = (cx + (k == 1 || k == 2)) * 16, wy = (cy + (k >= 2)) * 16, aa = wx - z - cam0, bb = wy - z - cam2;
        sxx[k] = aa - bb + 0xA0; syy[k] = ((aa + bb) >> 1) + 0x68;
      }
      ccx = (sxx[0] + sxx[2]) / 2; ccy = (syy[0] + syy[2]) / 2;
      if (ccx < -200 || ccx > 520 || ccy < -20 || ccy > 260) continue;
      v = (t & 6) ? 9 : (uint8)(1 + (h & 7));   /* byte 0: bit 6 = blocked for all, bit 5 = blocked for NPCs only */
      if (cx == px && cy == py) v = 10;
      for (k = 0; k < 4; k++) lk_m_seg(sxx[k], syy[k], sxx[(k + 1) & 3], syy[(k + 1) & 3], v);
      if (b1) {   /* byte 1 = floor type (Player_GroundType, ProcessFloorType $00603C): draw a cross */
        int cl = (b1 >= 1 && b1 <= 4) || b1 == 6 || b1 == 0x26 || b1 == 0x27 ? 11 : (b1 == 5 || b1 == 0xB || b1 == 0xC || b1 == 0xF || b1 == 0x28) ? 12 : (b1 == 7 || b1 == 0x10 || b1 == 0x19 || b1 == 0x29) ? 13 : 14;
        lk_m_seg(sxx[0], syy[0], sxx[2], syy[2], (uint8)cl); lk_m_seg(sxx[1], syy[1], sxx[3], syy[3], (uint8)cl);
      }
    }
  }
  for (a = 0xFF11DE, i = 0; i < LK_M_N; i++, a += 2) {
    int o = LKW(a), b, z, X[4], Y[4], kk;
    lk_m_ent_t *e;
    if (o & 0x8000) break;
    b = 0xFF5400 + o; if (b >= 0xFF5400 + 0x80 * 16) break;
    e = &lk_m_e[lk_m_n++]; e->id = o >> 7;
    e->ax = LKW(b + 0x0E) - 0x80; e->ay = LKW(b + 0x10) - 0x80; e->m_g = LKB(b + 0x0B); e->m_a = LKW(b + 0x24); e->m_f = LKW(b + 0x26);
    z = LKS(b + 0x12); kk = (o == 0) ? 0 : k1;
    X[0] = X[3] = LKS(b + 0x18); X[1] = X[2] = LKS(b + 0x1A); Y[0] = Y[1] = LKS(b + 0x1C); Y[2] = Y[3] = LKS(b + 0x1E);
    for (c = 0; c < 4; c++) { int aa = X[c] - z - cam0, bb = Y[c] - z - cam2; e->gx[c] = aa - bb + 0xA0; e->gy[c] = ((aa + bb + kk) >> 1) + 0x68; }
    if (lk_m_log) { int mx = ((e->gx[0] + e->gx[2]) / 2), my = ((e->gy[0] + e->gy[2]) / 2); fprintf(stderr, "model: slot %2d gfx %02X anim %04X frame %04X game(%d,%d) box centre(%d,%d)\n", e->id, e->m_g, e->m_a, e->m_f, e->ax, e->ay, mx, my); }
  }
}
static void lk_m_px(PIXEL_OUT_T *r, int Wp, int x, int y, int line, uint32 col) { if (y == line && x >= 0 && x < Wp) r[x] = col | (r[x] & 0xFF000000u); }
static void lk_model_row(PIXEL_OUT_T *row, int width) {
  int line = lk_br_line, Wp = bitmap.viewport.w, ox = bitmap.viewport.x, x0, i, c, d;
  static long fr; PIXEL_OUT_T *r;
  lk_m_init();
  if (line == 0) fr++;
  if (!lk_m_on) return;
  if (line == 0) { memcpy(lk_m_dmask, lk_m_mask, sizeof lk_m_mask); memcpy(lk_m_de, lk_m_e, sizeof lk_m_e); lk_m_dn = lk_m_n; }   /* show last frame's snapshot (see above) */
  if (line == 0) { if (!lk_m_log || fr % lk_m_log) { int sv = lk_m_log; lk_m_log = 0; lk_m_snapshot(); lk_m_log = sv; } else lk_m_snapshot(); }
  if (lk_picture || line < 24 || Wp < 320 || width < Wp + 2 * ox) return;   /* the HUD bar (lines 0..23) stays clean */
  r = row + ox; x0 = (Wp - 320) / 2;
  if (lk_m_grid && line < LK_MM_H) { int px; for (px = 0; px < Wp; px++) { int v = lk_m_dmask[line][px - x0 + LK_MM_X0]; if (v) r[px] = lk_m_gcol[v] | (r[px] & 0xFF000000u); } }
  for (i = 0; i < lk_m_dn; i++) {
    const lk_m_ent_t *e = &lk_m_de[i]; uint32 col = lk_m_col[e->id & 15];
    for (c = 0; c < 4; c++) {   /* box diamond: each edge, one span per row (2:1 slope) */
      int xa = e->gx[c], ya = e->gy[c], xb = e->gx[(c + 1) & 3], yb = e->gy[(c + 1) & 3];
      if (ya > yb) { int t = xa; xa = xb; xb = t; t = ya; ya = yb; yb = t; }
      if (line < ya || line > yb) continue;
      if (ya == yb) { int lo = xa < xb ? xa : xb, hi = xa < xb ? xb : xa; for (d = lo; d <= hi; d++) lk_m_px(r, Wp, x0 + d, line, line, col); }
      else { int xl = xa + (xb - xa) * (line - ya) / (yb - ya), xr = xa + (xb - xa) * (line + 1 - ya) / (yb - ya), lo = xl < xr ? xl : xr, hi = xl < xr ? xr : xl;
             if (line == yb) hi = lo = xb; for (d = lo; d <= hi; d++) lk_m_px(r, Wp, x0 + d, line, line, col); }
    }
    for (d = -3; d <= 3; d++) { if (line == e->ay) lk_m_px(r, Wp, x0 + e->ax + d, line, line, col); if (d && line == e->ay + d) lk_m_px(r, Wp, x0 + e->ax, line, line, col); }
    { int v[5] = { e->m_g >> 4, e->m_g & 15, 0, (e->m_a >> 2) & 15, (e->m_f >> 2) & 15 }, ly = line - (e->ay - 12), n;   /* label: gg a f */
      if (ly >= 0 && ly < 5) for (n = 0; n < 5; n++) { int cx = x0 + e->ax - 8 + n * 4; if (n == 2) continue; for (d = 0; d < 3; d++) if (lk_m_font[v[n]][ly] & (4 >> d)) lk_m_px(r, Wp, cx + d, line, line, col); }
    }
  }
}
#undef LKB
#undef LKW
#undef LKS
'''
    s = s.replace(c, module + c, 1)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)

# ---- platform_sdl.c: toggle function with an on-screen hint ---------------------------------------------------
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if "platform_display_toggle_model" not in s:
    a = "static void lk_text_box(const char *t, int x, int y, int px) {"
    assert s.count(a) == 1, "platform_sdl.c: run patch_coords.py first"
    s = s.replace(a, '''/* LK_MODEL v2: model view toggle (R3 / F7, tools/patch_model.py) */
extern int lk_model_toggle(void);
void platform_display_toggle_model(void) {
    int on = lk_model_toggle();
    snprintf(lk_osd_text, sizeof(lk_osd_text), "MODEL VIEW: %s", on == 1 ? "CELLS" : on == 2 ? "BLOCKS" : "OFF"); lk_osd_frames = 100;
}
''' + a, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched: model toggle")

# ---- input.c: R3 / F7 (fixed), LANDSTALKER_MODEL_AT test aid; R3 is not assignable in the Keybindings capture ----
p = os.path.join(root, "src/input.c")
s = open(p).read()
if "platform_display_toggle_model" not in s:
    a = "        if (d[LK_BCOORD] && !prev[LK_BCOORD]) platform_display_toggle_coords();\n"
    assert s.count(a) == 1, "input.c: run patch_keys.py first"
    s = s.replace(a, a + '''        { /* model view: pad R3 (click of the right stick, code 9) or key F7, fixed; test aid LANDSTALKER_MODEL_AT="f1,f2" (LK_MODEL v2) */
            static int mprev; static long mlast = -1; int md = lk_pad_code_down(pads, 9) || keys[SDL_SCANCODE_F7];
            const char *me = getenv("LANDSTALKER_MODEL_AT");
            if (md && !mprev) platform_display_toggle_model();
            mprev = md;
            if (me) { char l[128]; snprintf(l, sizeof l, "%s", me); for (char *t = strtok(l, ","); t; t = strtok(NULL, ",")) if (atol(t) == frame && frame != mlast) { mlast = frame; platform_display_toggle_model(); } }
        }
''', 1)
    b = "extern void platform_display_toggle_coords(void);\n"
    assert s.count(b) == 1
    s = s.replace(b, b + "extern void platform_display_toggle_model(void);\n", 1)
    c = "&& cc != 5) { lk_bind_assign(lk_cap, 1, cc);"
    assert s.count(c) == 1, "input.c: capture rule changed"
    s = s.replace(c, "&& cc != 5 && cc != 9) { lk_bind_assign(lk_cap, 1, cc);", 1)   # R3 stays fixed
    open(p, "w").write(s)
    print("input.c patched: model toggle")
