#!/usr/bin/env python3
"""Gameplay option 'Quick Items' (Options > Gameplay > Quick Items Off / On), user idea 2026-10-14.
On: pad Y (SDL Y -> GEN_X) and B (SDL B -> GEN_Z instead of GEN_C, which is only a duplicate of X = GEN_A) become two quick buttons.
 * Assignment: in the Start menu, Use tab, put the cursor on an item and press Y or B (again on the same item = clear). Only items from LK_Q_ALLOWED
   (EkeEke, Detox Grass, Gaia Statue, Golden Statue, Mind Repair, Anti-Paralyze, Dahl, Restoration) are accepted, anything else = the game's own error sound ($0044).
   The slots are saved in ~/.landstalker_quick ("on slotY slotB", item ids or -1); the icons (16 x 16, shrunk from the menu's 32 x 32 icon tiles that are in VRAM while
   the menu is open) in ~/.landstalker_quick_icons (ROM-derived, stays on the user's machine, never committed).
 * Use: func_table.c wrapper of ProcessActionButton ($0066AC, once per map pass in GameLoop): on a new Y / B press the game's own UseItemDispatch ($0085F2) runs with d0 = item id.
   While it runs (lk_q_active) DrawItemList ($00D4AE, called by ConsumeItem) is a no-op and ItemUseFailMessage ($008614, the text box 'can't use') only records the failure -> error sound.
   Refused (error sound, nothing consumed): empty slot, none left, dialogue / cutscene running ($FF12DE), dead, health already full for EkeEke / Dahl, handler says failure.
 * Display: vdp_render.c, per line of the HUD bar (lines 5..22) after the pixel conversion: when the bar is recognised (white top border) the row is rebuilt: bar stretched to the full picture
   width, the empty gaps right of the health numbers closed as far as needed, and two cells (letter Y / B, 16 px icon, count) drawn at the right end (352+ px: count right of the icon, 320 px: count on the icon).
   The layout analyses the PREVIOUS frame's bar (which columns are empty) so digits are never cut (one frame latency when the gold digits change).
Idempotent.  usage: patch_quick.py path/to/genrecomp   (run after patch_options.py and patch_shadow.py)"""
import os, sys
root = sys.argv[1]
VER = "LK_QUICK v1"

# ---------------------------------------------------------------- vdp_render.c
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    a = "void remap_line(int line)\n{\n"
    assert s.count(a) == 1, "vdp_render.c: remap_line layout changed"
    b = "  /* Adjust line offset in framebuffer */\n  line = (line + bitmap.viewport.y) % lines_per_frame;\n"
    assert s.count(b) == 1, "vdp_render.c: remap_line line adjust layout changed"
    s = s.replace(b, "  lk_q_line = line;   /* LK_QUICK v1 */\n" + b, 1)
    d = "      lk_shadow_darken(lk_row0, lk_w0);   /* LK_SHADOW v7 */\n"
    assert s.count(d) == 1, "vdp_render.c: run patch_shadow.py first"
    s = s.replace(d, d + "      lk_quick_hud(lk_row0, lk_w0);   /* LK_QUICK v1 */\n", 1)
    c = "void render_line(int line)"
    assert s.count(c) == 1
    module = r'''/* ---- LK_QUICK v1: quick item cells in the HUD bar (tools/patch_quick.py) ---- */
#include <stdio.h>
#include <stdlib.h>
extern uint8 vram[0x10000];
static int lk_q_line;
static int lk_q_on = -1, lk_q_id[2] = { -1, -1 }, lk_q_qty[2];
static PIXEL_OUT_T lk_q_px[64][256];
static uint8 lk_q_mask[64][256], lk_q_have[64];
static void lk_q_path(char *b, size_t n, const char *f) { const char *h = getenv("HOME"); snprintf(b, n, "%s/%s", h ? h : ".", f); }
static void lk_q_save(void) { char p[512]; FILE *f; lk_q_path(p, sizeof p, ".landstalker_quick"); f = fopen(p, "w"); if (f) { fprintf(f, "%d %d %d\n", lk_q_on, lk_q_id[0], lk_q_id[1]); fclose(f); } }
static void lk_q_icons_save(void) {
  char p[512]; FILE *f; int i; lk_q_path(p, sizeof p, ".landstalker_quick_icons"); f = fopen(p, "wb"); if (!f) return;
  for (i = 0; i < 64; i++) if (lk_q_have[i]) { uint8 id = (uint8)i; fwrite(&id, 1, 1, f); fwrite(lk_q_mask[i], 1, 256, f); fwrite(lk_q_px[i], sizeof(PIXEL_OUT_T), 256, f); }
  fclose(f);
}
static void lk_q_load(void) {
  char p[512]; FILE *f; int on = 0, a = -1, b = -1; uint8 id;
  lk_q_on = 1; lk_q_path(p, sizeof p, ".landstalker_quick");   /* default On since 2026-10-17 (Quality of Life); a saved file wins */ f = fopen(p, "r");
  if (f) { if (fscanf(f, "%d %d %d", &on, &a, &b) >= 1) { lk_q_on = on ? 1 : 0; lk_q_id[0] = a; lk_q_id[1] = b; } fclose(f); }
  { const char *e = getenv("LANDSTALKER_QUICK"); if (e && *e) lk_q_on = atoi(e) ? 1 : 0; }
  { const char *e = getenv("LANDSTALKER_QUICK_SLOTS"); int x, y; if (e && sscanf(e, "%d,%d", &x, &y) == 2) { lk_q_id[0] = x; lk_q_id[1] = y; } }   /* test aid */
  lk_q_path(p, sizeof p, ".landstalker_quick_icons"); f = fopen(p, "rb");
  if (f) { while (fread(&id, 1, 1, f) == 1 && id < 64) { if (fread(lk_q_mask[id], 1, 256, f) != 256 || fread(lk_q_px[id], sizeof(PIXEL_OUT_T), 256, f) != 256) break; lk_q_have[id] = 1; } fclose(f); }
}
int lk_quick_get(void) { if (lk_q_on < 0) lk_q_load(); return lk_q_on; }
void lk_quick_set(int v) { lk_quick_get(); lk_q_on = v ? 1 : 0; lk_q_save(); }
int lk_quick_slot_get(int s) { lk_quick_get(); return lk_q_id[s & 1]; }
void lk_quick_slot_set(int s, int id) { lk_quick_get(); lk_q_id[s & 1] = id; lk_q_save(); }
void lk_quick_set_qty(int s, int q) { lk_q_qty[s & 1] = q; }
/* copy the 32 x 32 icon of item `id` from VRAM (tiles $BC + id * 16, column-major 4 x 4, palette 1 as the menu draws owned items) shrunk to 16 x 16 */
void lk_quick_capture(int id) {
  uint8 raw[32][32]; int r, c, y, x, bx0 = 99, by0 = 99, bx1 = -1, by1 = -1, w, h, mx, sw, sh, ox, oy;
  if (id < 0 || id > 63) return;
  for (r = 0; r < 4; r++) for (c = 0; c < 4; c++) {
    unsigned addr = (unsigned)(0xBC + id * 16 + r + 4 * c) * 32u;
    for (y = 0; y < 8; y++) for (x = 0; x < 8; x++) {
      unsigned o = addr + (unsigned)y * 4u + (unsigned)(x >> 1);
#ifdef LSB_FIRST
      o ^= 1;
#endif
      { uint8 bb = vram[o & 0xFFFF]; raw[r * 8 + y][c * 8 + x] = (x & 1) ? (bb & 15) : (bb >> 4); }
    }
  }
  for (y = 0; y < 32; y++) for (x = 0; x < 32; x++) if (raw[y][x]) { if (x < bx0) bx0 = x; if (x > bx1) bx1 = x; if (y < by0) by0 = y; if (y > by1) by1 = y; }
  if (bx1 < 0) return;
  w = bx1 - bx0 + 1; h = by1 - by0 + 1; mx = w > h ? w : h;
  sw = (w * 16 + mx / 2) / mx; sh = (h * 16 + mx / 2) / mx; if (sw < 1) sw = 1; if (sh < 1) sh = 1; if (sw > 16) sw = 16; if (sh > 16) sh = 16;
  ox = (16 - sw) / 2; oy = (16 - sh) / 2;
  memset(lk_q_mask[id], 0, 256);
  for (y = 0; y < 16; y++) for (x = 0; x < 16; x++) {
    int ya, yb, xa, xb, yy, xx, n = 0, tot, sr = 0, sg = 0, sb = 0, sa = 0;
    if (x < ox || x >= ox + sw || y < oy || y >= oy + sh) continue;
    ya = by0 + (y - oy) * h / sh; yb = by0 + ((y - oy + 1) * h + sh - 1) / sh; xa = bx0 + (x - ox) * w / sw; xb = bx0 + ((x - ox + 1) * w + sw - 1) / sw;
    if (yb <= ya) yb = ya + 1; if (xb <= xa) xb = xa + 1; tot = (yb - ya) * (xb - xa);
    for (yy = ya; yy < yb && yy < 32; yy++) for (xx = xa; xx < xb && xx < 32; xx++) if (raw[yy][xx]) {
      PIXEL_OUT_T pv = pixel[0x10 + raw[yy][xx]]; n++; sr += (pv >> 16) & 255; sg += (pv >> 8) & 255; sb += pv & 255; sa += (pv >> 24) & 255;
    }
    if (n * 2 < tot || !n) continue;
    lk_q_px[id][y * 16 + x] = ((PIXEL_OUT_T)(sa / n) << 24) | ((PIXEL_OUT_T)(sr / n) << 16) | ((PIXEL_OUT_T)(sg / n) << 8) | (PIXEL_OUT_T)(sb / n);
    lk_q_mask[id][y * 16 + x] = 1;
  }
  lk_q_have[id] = 1; lk_q_icons_save();
}
static const char *lk_q_d5[10][7] = {
  { ".111.", "1...1", "1..11", "1.1.1", "11..1", "1...1", ".111." }, { "..1..", ".11..", "..1..", "..1..", "..1..", "..1..", ".111." },
  { ".111.", "1...1", "....1", "...1.", "..1..", ".1...", "11111" }, { ".111.", "1...1", "....1", "..11.", "....1", "1...1", ".111." },
  { "...1.", "..11.", ".1.1.", "1..1.", "11111", "...1.", "...1." }, { "11111", "1....", "1111.", "....1", "....1", "1...1", ".111." },
  { "..11.", ".1...", "1....", "1111.", "1...1", "1...1", ".111." }, { "11111", "....1", "...1.", "..1..", ".1...", ".1...", ".1..." },
  { ".111.", "1...1", "1...1", ".111.", "1...1", "1...1", ".111." }, { ".111.", "1...1", "1...1", ".1111", "....1", "...1.", ".11.." } };
static const char *lk_q_d3[39][5] = {
  { "111", "101", "101", "101", "111" }, { "010", "110", "010", "010", "111" }, { "111", "001", "111", "100", "111" }, { "111", "001", "111", "001", "111" },
  { "101", "101", "111", "001", "001" }, { "111", "100", "111", "001", "111" }, { "111", "100", "111", "101", "111" }, { "111", "001", "010", "010", "010" },
  { "111", "101", "111", "101", "111" }, { "111", "101", "111", "001", "111" }, { "101", "101", "010", "010", "010" } /* Y */, { "110", "101", "110", "101", "110" } /* B */,
  { "010", "101", "111", "101", "101" }, { "110", "101", "110", "101", "110" }, { "011", "100", "100", "100", "011" }, { "110", "101", "101", "101", "110" }, { "111", "100", "110", "100", "111" }, { "111", "100", "110", "100", "100" }, { "011", "100", "101", "101", "011" }, { "101", "101", "111", "101", "101" }, { "111", "010", "010", "010", "111" }, { "001", "001", "001", "101", "010" }, { "101", "101", "110", "101", "101" }, { "100", "100", "100", "100", "111" }, { "101", "111", "111", "101", "101" }, { "111", "101", "101", "101", "101" }, { "010", "101", "101", "101", "010" }, { "110", "101", "110", "100", "100" }, { "010", "101", "101", "111", "011" }, { "110", "101", "110", "101", "101" }, { "011", "100", "010", "001", "110" }, { "111", "010", "010", "010", "010" }, { "101", "101", "101", "101", "111" }, { "101", "101", "101", "101", "010" }, { "101", "101", "111", "111", "101" }, { "101", "101", "010", "101", "101" }, { "101", "101", "010", "010", "010" }, { "111", "001", "010", "100", "111" } /* 12.. = A..Z */, { "000", "000", "111", "000", "000" } /* 38 = - */ };
extern void lk_bind_hudlabel(int i, char *o, size_t n);   /* key bindings (tools/patch_keys.py): the cell letters are the bound pad button (controller connected) or key */
static int lk_q_gi(char c) { return (c >= '0' && c <= '9') ? c - '0' : (c >= 'A' && c <= 'Z') ? 12 + c - 'A' : 38; }
static PIXEL_OUT_T lk_q_cv[16][64];
static uint8 lk_q_cm[16][64];
static void lk_q_px_set(int x, int y, PIXEL_OUT_T c) { if (x >= 0 && x < 64 && y >= 0 && y < 16) { lk_q_cv[y][x] = c; lk_q_cm[y][x] = 1; } }
static void lk_q_g3(int x, int y, int g, PIXEL_OUT_T col, PIXEL_OUT_T blk, int outline) {   /* 3 x 5 glyph with an optional black outline */
  int i, j, di, dj;
  if (g == 10 || g == 11) g = lk_q_gi("YB"[g - 10]);   /* old letter indices: Y / B */
  if (outline) for (j = 0; j < 5; j++) for (i = 0; i < 3; i++) if (lk_q_d3[g][j][i] == '1') for (dj = -1; dj <= 1; dj++) for (di = -1; di <= 1; di++) lk_q_px_set(x + i + di, y + j + dj, blk);
  for (j = 0; j < 5; j++) for (i = 0; i < 3; i++) if (lk_q_d3[g][j][i] == '1') lk_q_px_set(x + i, y + j, col);
}
static void lk_q_g5(int x, int y, int d, PIXEL_OUT_T col) { int i, j; for (j = 0; j < 7; j++) for (i = 0; i < 5; i++) if (lk_q_d5[d][j][i] == '1') lk_q_px_set(x + i, y + j, col); }
static PIXEL_OUT_T lk_q_dim(PIXEL_OUT_T c) { return ((c >> 1) & 0x007F7F7Fu) | (c & 0xFF000000u); }
static void lk_q_label(int x, int y, int slot, PIXEL_OUT_T col, PIXEL_OUT_T blk, int outline) {   /* up to two characters of the binding label of Quick 1 / Quick 2 */
  char b[16]; int n; lk_bind_hudlabel(4 + slot, b, sizeof b); n = (int)strlen(b); if (n > 2) n = 2;
  for (int k = 0; k < n; k++) lk_q_g3(x + 4 * k, y, lk_q_gi(b[k]), col, blk, outline);
}
static void lk_q_cells(int compact, PIXEL_OUT_T white, PIXEL_OUT_T black) {
  int s, i, j;
  memset(lk_q_cm, 0, sizeof lk_q_cm);
  for (s = 0; s < 2; s++) {
    int x0 = compact ? (s ? 20 : 2) : (s ? 32 : 2), id = lk_q_id[s], q = lk_q_qty[s];
    if (id >= 0 && id < 64 && lk_q_have[id]) {
      for (j = 0; j < 16; j++) for (i = 0; i < 16; i++) if (lk_q_mask[id][j * 16 + i]) lk_q_px_set(x0 + i, j, q > 0 ? lk_q_px[id][j * 16 + i] : lk_q_dim(lk_q_px[id][j * 16 + i]));
    }
    if (id >= 0) {
      lk_q_label(x0 + 1, 1, s, white, black, 1);
      if (q < 0) q = 0; if (q > 99) q = 99;
      if (compact) { int two = q >= 10; int xr = x0 + 15 - (two ? 7 : 3); if (two) { lk_q_g3(xr, 10, q / 10, white, black, 1); lk_q_g3(xr + 4, 10, q % 10, white, black, 1); } else lk_q_g3(xr, 10, q, white, black, 1); }
      else { if (q >= 10) { lk_q_g5(x0 + 18, 4, q / 10, white); lk_q_g5(x0 + 24, 4, q % 10, white); } else lk_q_g5(x0 + 18, 4, q, white); }
    } else lk_q_label(x0 + 4, 6, s, lk_q_dim(white), black, 0);   /* empty slot: dim letter only */
  }
}
static int lk_q_hud, lk_q_Lp, lk_q_Wb, lk_q_kn, lk_q_cellw, lk_q_bl, lk_q_fillcol, lk_q_haveprev, lk_q_colmap[512];
static uint8 lk_q_busy[512], lk_q_busyp[512];
'''
    module += r'''static void lk_quick_hud(PIXEL_OUT_T *row, int width) {
  int line = lk_q_line, Wp = bitmap.viewport.w, ox = bitmap.viewport.x, e, bl, x, n;
  PIXEL_OUT_T *r, tmp[512];
  if (line < 5 || line > 22) return;
  if (lk_quick_get() <= 0) return;
  if (Wp < 320 || Wp > 416 || width < Wp + 2 * ox) return;
  r = row + ox; e = (Wp - 320) / 2; bl = 12 + e;   /* the bar is 296 px wide: picture x 12 + e .. 307 + e (rel 0..295; left cap rel 0..2, right cap rel 293..295) */
  if (line == 5) {   /* decide for this frame: bar there? build the column map from the previous frame's empty columns */
    int wc = 0;
    lk_q_hud = 0;
    for (x = bl + 6; x < bl + 287; x++) { PIXEL_OUT_T p = r[x]; if (((p >> 16) & 255) > 200 && ((p >> 8) & 255) > 200 && (p & 255) > 200) wc++; }
    if (wc >= 275 && lk_q_haveprev) {
      int Lp = (Wp == 320) ? 0 : (Wp - 348) / 2, Wb = (Wp == 320) ? 320 : 348,   /* 320: full width; 352 and wider: 348 px (at 352 nearly the full width), centred, so the bar does not stretch over the wide margins */
           compact = 1, cellw = compact ? 36 : 62, need = 296 + cellw - Wb, k, a, b, kn = 0, fc = -1;
      uint8 rm[296];
      PIXEL_OUT_T white = r[bl + 100], black = white & 0xFF000000u;
      memset(rm, 0, sizeof rm);
      for (x = 230; x <= 233; x++) { rm[x] = 1; need--; }   /* the '-' between the bag and the item count (rel 230..233, 4 px; user wish 2026-10-17): dropped, so the count moves left and the gold keeps more distance */
      /* 1. runs of empty columns right of the health numbers (rel 200..296), 2. any empty run right of the sword icon (rel 25..199), keep 3 px of every run */
      { int pass; for (pass = 0; pass < 2 && need > 0; pass++) {
          int lo = pass ? 25 : 200, hi = pass ? 199 : 292;
          for (k = lo; k <= hi && need > 0; ) {
            if (lk_q_busyp[k] || rm[k]) { k++; continue; }
            a = k; while (k <= hi && !lk_q_busyp[k] && !rm[k]) k++;
            b = k - 1;
            for (x = a + 3; x <= b && need > 0; x++) { rm[x] = 1; need--; }
          }
      } }
      if (need > 0) return;   /* not enough room: leave the HUD alone this frame */
      for (k = 40; k <= 292; k++) if (!lk_q_busyp[k] && !rm[k]) { fc = k; break; }
      if (fc < 0) fc = 85;
      for (k = 0; k < 293; k++) if (!rm[k]) lk_q_colmap[kn++] = k;
      if (kn + cellw > Wb - 3) return;
      for (n = kn; n < Wb - 3; n++) lk_q_colmap[n] = -1;
      for (n = 0; n < 3; n++) lk_q_colmap[Wb - 3 + n] = 293 + n;
      lk_q_Lp = Lp; lk_q_Wb = Wb; lk_q_kn = kn; lk_q_cellw = cellw; lk_q_bl = bl; lk_q_fillcol = fc;
      lk_q_cells(compact, white, black);
      lk_q_hud = 1;
    }
  }
  if (line >= 7 && line <= 20) for (x = 3; x < 293; x++) if (((r[bl + x]) & 0xFFFFFF) != 0x442288u) lk_q_busy[x] = 1;
  if (lk_q_hud) {
    int Lp = lk_q_Lp, Wb = lk_q_Wb, kn = lk_q_kn, fc = lk_q_fillcol;
    memcpy(tmp, r, (size_t)Wp * sizeof(PIXEL_OUT_T));
    for (n = 0; n < Wb; n++) { int src = lk_q_colmap[n]; r[Lp + n] = tmp[bl + (src >= 0 ? src : fc)]; }
    if (line >= 6 && line <= 21) for (x = 0; x < lk_q_cellw; x++) if (lk_q_cm[line - 6][x]) r[Lp + kn + x] = lk_q_cv[line - 6][x];
  }
  if (line == 22) { memcpy(lk_q_busyp, lk_q_busy, sizeof lk_q_busy); memset(lk_q_busy, 0, sizeof lk_q_busy); lk_q_haveprev = 1; }
}
'''
    s = s.replace(c, module + c, 1)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)

# ---------------------------------------------------------------- input.c: SDL B -> GEN_Z while the option is on
p = os.path.join(root, "src/input.c")
s = open(p).read()
if "lk_quick_get" not in s:
    a = "static uint16_t s_pad_state[2];\n"
    assert s.count(a) == 1, "input.c layout changed"
    s = s.replace(a, "extern int lk_quick_get(void);   /* LK_QUICK: with 'Quick Items' on, SDL B is a quick button (GEN_Z) instead of the duplicate C button */\n" + a, 1)
    b = "            if (PB(B))             buttons |= GEN_BTN_C;\n"
    assert s.count(b) == 1, "input.c: PB(B) mapping changed"
    s = s.replace(b, "            if (PB(B))             buttons |= (lk_quick_get() > 0 ? GEN_BTN_Z : GEN_BTN_C);\n", 1)
    open(p, "w").write(s)
    print("input.c patched: SDL B -> GEN_Z with Quick Items")

# ---------------------------------------------------------------- func_table.c: logic
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if "lk_quick_install" not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "lk_menu_install" in s and "lk_shadow_install" in s, "func_table.c: run patch_options.py and patch_shadow.py first"
    module = r'''/* ---- LANDSTALKER 'Quick Items' (tools/patch_quick.py) ---- */
#include <genrecomp/input.h>
extern int lk_quick_get(void);
extern int lk_quick_slot_get(int s);
extern void lk_quick_slot_set(int s, int id);
extern void lk_quick_set_qty(int s, int q);
extern void lk_quick_capture(int id);
extern int lk_no_charge;
static gen_func_t lk_o_pab, lk_o_dil, lk_o_ifm, lk_o_rpr;
static int lk_q_active, lk_q_failed;
static const uint8_t lk_q_allowed[] = { 0x00, 0x12, 0x13, 0x14, 0x15, 0x1C, 0x2D, 0x2E };   /* EkeEke, Detox Grass, Gaia Statue, Golden Statue, Mind Repair, Anti-Paralyze, Dahl, Restoration */
static int lk_q_ok(int id) { unsigned k; for (k = 0; k < sizeof lk_q_allowed; k++) if (lk_q_allowed[k] == id) return 1; return 0; }
static int lk_q_count(int id) {   /* GetItemQtyAndMaxQty ($022ED0): d1 = quantity (<= 0: none) */
    M68kContext sv = g_m68k; int q, nc = lk_no_charge;
    g_m68k.d[0] = (uint32_t)id; lk_no_charge = 1; lk_call(0x022ED0u); lk_no_charge = nc;
    q = (int16_t)(g_m68k.d[1] & 0xFFFF); g_m68k = sv;
    return q;
}
static void lk_q_beep(void) { lk_snd(0x00DBBEu); }   /* the menu's own error sound ($0044) */
static int lk_q_health_full(void) {   /* player health >= max health (GetMaxHealth $0103C8 with a5 = player) */
    M68kContext sv = g_m68k; int mx, nc = lk_no_charge;
    g_m68k.a[5] = 0xFF5400u; lk_no_charge = 1; lk_call(0x0103C8u); lk_no_charge = nc;
    mx = (int)(g_m68k.d[0] & 0xFFFF); g_m68k = sv;
    return (int)bus_read16(0xFF543Eu) >= mx;
}
static void lk_q_refresh_counts(void) { int s; for (s = 0; s < 2; s++) { int id = lk_quick_slot_get(s); lk_quick_set_qty(s, id >= 0 ? lk_q_count(id) : 0); } }
static void lk_q_use(int slot) {
    int id = lk_quick_slot_get(slot), q;
    if (id < 0 || !lk_q_ok(id)) { lk_q_beep(); return; }
    q = lk_q_count(id);
    if (q <= 0) { lk_q_beep(); return; }
    if ((id == 0x00 || id == 0x2D) && lk_q_health_full()) { lk_q_beep(); return; }
    { M68kContext sv = g_m68k;
      lk_q_active = 1; lk_q_failed = 0;
      g_m68k.d[0] = (uint32_t)id; lk_call(0x0085F2u);   /* UseItemDispatch: stores the id at $FF1152, jumps to the handler (ends in RTS) */
      lk_q_active = 0; g_m68k = sv; }
    if (lk_q_failed) lk_q_beep();
    lk_q_refresh_counts();
}
static void lk_h_pab(void) {
    static uint16_t prev;
    if (lk_quick_get() > 0) {
        uint16_t pad = recomp_input_read_pad(0), ed = (uint16_t)(pad & ~prev);
        prev = pad;
        lk_q_refresh_counts();
        if ((ed & (GEN_BTN_X | GEN_BTN_Z)) && bus_read16(0xFF12DEu) == 0 && bus_read16(0xFF543Eu) != 0) {
            if (ed & GEN_BTN_X) lk_q_use(0);
            if (ed & GEN_BTN_Z) lk_q_use(1);
        }
    }
    lk_o_pab();
}
static void lk_h_dil(void) { if (lk_q_active) { func_table_rts(); return; } lk_o_dil(); }       /* DrawItemList: menu drawing, not on the map */
static void lk_h_ifm(void) { if (lk_q_active) { lk_q_failed = 1; func_table_rts(); return; } lk_o_ifm(); }   /* ItemUseFailMessage: text box of the menu */
/* the Use tab of the Start menu: Y / B on the item under the cursor assign it to the slot (again on the same item = clear) */
static void lk_h_rpr(void) {
    static uint16_t prev;
    int i, d = func_table_depth(), inlist = 0;
    lk_o_rpr();
    if (lk_quick_get() <= 0) { prev = recomp_input_read_pad(0); return; }
    for (i = 0; i < d; i++) { uint32_t f = func_table_stack(i); if (f == 0x00D3C6u || f == 0x00D3BEu) inlist = 1; }
    { uint16_t pad = recomp_input_read_pad(0), ed = (uint16_t)(pad & ~prev);
      prev = pad;
      if (inlist && (ed & (GEN_BTN_X | GEN_BTN_Z))) {
        int slot = (ed & GEN_BTN_X) ? 0 : 1, row = (int)(bus_read16(0xFF2C06u) >> 2) + (int)bus_read16(0xFF2C0Cu), idx = (int)bus_read16(0xFF2C0Au) + row * 2, id = bus_read8(0xFF2C5Cu + (uint32_t)idx);
        if (!lk_q_ok(id)) lk_q_beep();
        else if (lk_quick_slot_get(slot) == id) { lk_quick_slot_set(slot, -1); lk_snd(LK_SND_MOVE); }
        else {
            unsigned k;
            if (lk_quick_slot_get(slot ^ 1) == id) lk_quick_slot_set(slot ^ 1, -1);
            lk_quick_slot_set(slot, id);
            for (k = 0; k < sizeof lk_q_allowed; k++) lk_quick_capture(lk_q_allowed[k]);
            lk_snd(LK_SND_SELECT);
        }
        lk_q_refresh_counts();
      } }
}
static void lk_quick_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_pab = func_table_lookup(0x0066AC); lk_o_dil = func_table_lookup(0x00D4AE); lk_o_ifm = func_table_lookup(0x008614); lk_o_rpr = func_table_lookup(0x00D88A);
    if (!(lk_o_pab && lk_o_dil && lk_o_ifm && lk_o_rpr)) { fprintf(stderr, "quick items: game functions not found, option disabled\n"); return; }
    func_table_register(0x0066AC, lk_h_pab); func_table_register(0x00D4AE, lk_h_dil); func_table_register(0x008614, lk_h_ifm); func_table_register(0x00D88A, lk_h_rpr);
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_shadow_install();   /* LANDSTALKER shadow option */\n"
    assert s.count(h) == 1, "func_table.c: shadow install hook layout changed"
    s = s.replace(h, h + "        lk_quick_install();   /* LANDSTALKER quick items */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched: quick items")
