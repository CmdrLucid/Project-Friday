#!/usr/bin/env python3
"""Modern HUD (2026-10-30, user design 'entwurf 9', docs/HUD_IDEAS.md).  Options > Video > HUD: Original / Modern (option id 41, file ~/.landstalker_hud,
env LANDSTALKER_HUD=0|1; the old experiment env LANDSTALKER_NOHUD=1 means Modern too).  Only with the own renderer: in map frames it draws the room in lines 0..23
(LK_NOHUD band of patch_own.py) and lays the HUD over the picture, without boxes:
 * top left: the original hearts (window tile columns 11..22) and below them the sword icon + the original rounded charge gauge (columns 2..10), taken pixel by pixel
   from the HUD tilemap the own renderer rebuilds every frame (lk_o_hudbuild = port of hud.asm), so tiers, charge and fades are the game's own; 1 px dark outline;
 * top right: the buttons in the layout of the pad (Y top, X left, B right, A bottom), round discs in the HUD purple (slightly transparent, white rim, grey inner line);
   the icon of the function bound to that pad button lies over the disc: Quick 1 / Quick 2 = their items (+ count on a dark plate), MD A = the equipped sword
   (EquippedSword $FF114E), MD B = the leather boots (NO_BOOTS $3C) for the jump; a disc without icon shows its letter (the binding label);
   icons come from the quick icon cache (~/.landstalker_quick_icons, captured in the Start menu); a missing icon shows the letter;
 * bottom right: the gold in a small 5 x 7 font with a dark outline (user: the bar's digits looked too large), above the picture's lower edge (185 without full height).
Frames the own map path does not draw (Start menu fades, black room-load frames) show black instead of the old bar in lines 0..23 (user 2026-10-30).
Picture only: the game logic is not touched (replays / timebench unchanged; Original = bit exact).
Needs patch_own.py, patch_quick.py, patch_keys.py and patch_options.py (option row 41) before it.  Idempotent.  usage: patch_modernhud.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_MHUD v1"

# ---- input.c: pad code of a binding (1 + SDL_CONTROLLER_BUTTON_*, 0 = none) -------------------------------
p = os.path.join(root, "src/input.c")
s = open(p).read()
if VER not in s:
    a = "void lk_bind_hudlabel(int i, char *o, size_t n) {"
    assert s.count(a) == 1, "input.c: run patch_keys.py first"
    s = s.replace(a, "int lk_bind_pad_get(int i) { lk_bind_init(); return (i >= 0 && i < LK_NB) ? lk_bind_pad[i] : 0; }   /* LK_MHUD v1: the modern HUD puts each function's icon on its pad button */\n" + a, 1)
    open(p, "w").write(s)
    print("input.c patched:", VER)

# ---- vdp_render.c: option, per frame overlay layer, hooks in the own renderer ---------------------------------
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    old = "static int lk_o_nohud = -1;\nint lk_nohud_get(void) { if (lk_o_nohud < 0) { const char *q = getenv(\"LANDSTALKER_NOHUD\"); lk_o_nohud = (q && *q && atoi(q)) ? 1 : 0; } return lk_o_nohud; }\n"
    assert s.count(old) == 1, "vdp_render.c: run patch_own.py first (LK_NOHUD v0)"
    new = r'''static int lk_o_nohud = -1;   /* LK_MHUD v1: 0 = HUD Original, 1 = Modern (Options > Video > HUD, ~/.landstalker_hud; env LANDSTALKER_HUD or the old LANDSTALKER_NOHUD wins at start) */
static void lk_mh_path(char *b, size_t n) { const char *h = getenv("HOME"); snprintf(b, n, "%s/.landstalker_hud", h ? h : "."); }
int lk_mhud_get(void) {
  if (lk_o_nohud < 0) { char p[512]; FILE *f; int v = 0; const char *q = getenv("LANDSTALKER_HUD"), *q0 = getenv("LANDSTALKER_NOHUD");
    lk_mh_path(p, sizeof p); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); }
    if (q0 && *q0) v = atoi(q0); if (q && *q) v = atoi(q); lk_o_nohud = v ? 1 : 0; }
  return lk_o_nohud;
}
void lk_mhud_set(int v) { char p[512]; FILE *f; lk_mhud_get(); lk_o_nohud = v ? 1 : 0; lk_mh_path(p, sizeof p); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_o_nohud); fclose(f); } }
int lk_nohud_get(void) { return lk_o_nohud < 0 ? lk_mhud_get() : lk_o_nohud; }
static int lk_mh_hit;
static void lk_mh_begin(int w, int e);
static int lk_mh_pix(int line, int i, int *col);
'''
    s = s.replace(old, new, 1)


    a = "static void lk_q_load(void) {"
    assert s.count(a) == 1, "vdp_render.c: run patch_quick.py first"
    s = s.replace(a, "static void lk_qr_fill(void);   /* LK_MHUD v1: item icons from the ROM */\n" + a, 1)
    a = "lk_q_have[id] = 1; } fclose(f); }\n}\n"
    assert s.count(a) == 1, "vdp_render.c: lk_q_load layout changed"
    s = s.replace(a, "lk_q_have[id] = 1; } fclose(f); }\n  lk_qr_fill();   /* LK_MHUD v1: every icon straight from the ROM (no Start menu capture needed) */\n}\n", 1)

    # build the layer once per frame (first own line of the frame)
    a = "    int wlo = 0, whi = w, tb = lk_tbox_get(), nohud = lk_nohud_get(), wline = ((line == 23 && !nohud) || text);"
    assert s.count(a) == 1, "vdp_render.c: own line layout changed"
    k = s.index(a); k = s.index("\n", k) + 1
    s = s[:k] + "    if (nohud) lk_mh_begin(w, e);   /* LK_MHUD v1 */\n" + s[k:]

    # every pixel: the overlay over the final colour (after the seam history, before the row / HD output)
    a = "      lk_vh[line & 7][i] = (PIXEL_OUT_T)col; lk_vhv[line & 7][i] = (src == 0 || black || margin || (col & 0xFFFFFF) == 0) ? 1 : 0;\n"
    assert s.count(a) == 1, "vdp_render.c: own pixel layout changed"
    s = s.replace(a, a + "      lk_mh_hit = nohud ? lk_mh_pix(line, i, &col) : 0;   /* LK_MHUD v1 */\n", 1)
    a = "lk_hd_put(line, x, (uint32_t)col, pi.rep ? &pi : 0);"
    assert s.count(a) == 1, "vdp_render.c: HD put changed"
    s = s.replace(a, "lk_hd_put(line, x, (uint32_t)col, (pi.rep && !lk_mh_hit) ? &pi : 0);", 1)

    # map frames the own path does not draw: no old bar in lines 0..23
    a = "  if (!fr_done || w != 320 + 2 * e || !map) {"
    assert s.count(a) == 1, "vdp_render.c: own frame gate changed"
    s = s.replace(a, "  if (map && !fr_done && w == 320 + 2 * e && line < 24 && lk_nohud_get()) { int k; for (k = 0; k < w; k++) row[k] = (PIXEL_OUT_T)pixel_lut[1][0]; return; }   /* LK_MHUD v1: Modern HUD: black instead of the old bar */\n" + a, 1)

    module = r'''
/* ---- LK_MHUD v1: modern HUD layer (tools/patch_modernhud.py, docs/HUD_IDEAS.md entwurf 9) ---- */
extern int lk_bind_pad_get(int i);
extern void lk_bind_hudlabel(int i, char *o, size_t n);
#define LK_MH_H 240
#define LK_MH_W 464
static PIXEL_OUT_T lk_mh_c[LK_MH_H][LK_MH_W];
static uint8 lk_mh_a[LK_MH_H][LK_MH_W];
static long lk_mh_fr = -1; static int lk_mh_y0 = LK_MH_H, lk_mh_y1 = -1;
static const uint8 lk_mh_font[39][7] = {   /* 5 x 7: A..Z, 0..9, '-', '?', ' ' */
  {14,17,17,31,17,17,17},{30,17,17,30,17,17,30},{14,17,16,16,16,17,14},{30,17,17,17,17,17,30},{31,16,16,30,16,16,31},{31,16,16,30,16,16,16},{14,17,16,23,17,17,15},
  {17,17,17,31,17,17,17},{14,4,4,4,4,4,14},{7,2,2,2,2,18,12},{17,18,20,24,20,18,17},{16,16,16,16,16,16,31},{17,27,21,21,17,17,17},{17,17,25,21,19,17,17},
  {14,17,17,17,17,17,14},{30,17,17,30,16,16,16},{14,17,17,17,21,18,13},{30,17,17,30,20,18,17},{15,16,16,14,1,1,30},{31,4,4,4,4,4,4},{17,17,17,17,17,17,14},
  {17,17,17,17,17,10,4},{17,17,17,21,21,21,10},{17,17,10,4,10,17,17},{17,17,10,4,4,4,4},{31,1,2,4,8,16,31},
  {14,17,19,21,25,17,14},{4,12,4,4,4,4,14},{14,17,1,2,4,8,31},{31,2,4,2,1,17,14},{2,6,10,18,31,2,2},{31,16,30,1,1,17,14},{6,8,16,30,17,17,14},{31,1,2,4,8,8,8},
  {14,17,17,14,17,17,14},{14,17,17,15,1,2,12},{0,0,0,31,0,0,0},{14,17,1,2,4,0,4},{0,0,0,0,0,0,0} };
static int lk_mh_gi(int ch) { if (ch >= 'a' && ch <= 'z') ch -= 32; if (ch >= 'A' && ch <= 'Z') return ch - 'A'; if (ch >= '0' && ch <= '9') return 26 + ch - '0'; if (ch == '-') return 36; if (ch == ' ') return 38; return 37; }
static PIXEL_OUT_T lk_mh_rgb(int pick) { return lk_o_palmode ? lk_o_pix[pick & 0x3F] : pixel[pick & 0x3F]; }
static void lk_mh_put(int x, int y, PIXEL_OUT_T c, int a) {   /* a = 255 opaque, else alpha over what is there (layer pixels blend too) */
  if (x < 0 || y < 0 || x >= LK_MH_W || y >= LK_MH_H || a <= 0) return;
  if (a >= 255 || !lk_mh_a[y][x]) { if (a >= 255 || !lk_mh_a[y][x]) { lk_mh_c[y][x] = c; lk_mh_a[y][x] = (uint8)(a > 255 ? 255 : a); } }
  else { int a0 = lk_mh_a[y][x], an = a + a0 * (255 - a) / 255, sh; PIXEL_OUT_T o = 0, c0 = lk_mh_c[y][x];
    for (sh = 0; sh < 24; sh += 8) { int v1 = (c >> sh) & 255, v0 = (c0 >> sh) & 255; o |= (PIXEL_OUT_T)((v1 * a + v0 * a0 * (255 - a) / 255) / (an ? an : 1)) << sh; }
    lk_mh_c[y][x] = o | (c & 0xFF000000u); lk_mh_a[y][x] = (uint8)an; }
  if (y < lk_mh_y0) lk_mh_y0 = y; if (y > lk_mh_y1) lk_mh_y1 = y;
}
static PIXEL_OUT_T lk_mh_fadec(PIXEL_OUT_T c, PIXEL_OUT_T fill) {   /* an RGB icon pixel follows the fade of the HUD purple (darker below, towards white above), like lk_q_fade */
  int sh; PIXEL_OUT_T o = c & 0xFF000000u;
  if ((fill & 0xFFFFFFu) == 0x442288u) return c;
  for (sh = 0; sh < 24; sh += 8) { int ch = (int)((c >> sh) & 255), f0 = (int)((0x442288u >> sh) & 255), f1 = (int)((fill >> sh) & 255), v;
    if (f1 <= f0) v = f0 ? ch * f1 / f0 : ch; else v = (f1 >= 0xEE || f0 >= 0xEE) ? 0xEE : ch + (0xEE - ch) * (f1 - f0) / (0xEE - f0);
    o |= (PIXEL_OUT_T)(v < 0 ? 0 : v > 255 ? 255 : v) << sh; }
  return o;
}
static uint8 lk_mh_m[64][120];   /* scratch mask for the outline of one crop */
static void lk_mh_crop(int x0, int x1, int ly0, int ly1, int dx, int dy, int fillp, int greyp, int *outw, int *outh, int place) {   /* window pixels x0..x1 / lines ly0..ly1 -> picture (dx, dy), fill / grey transparent, 1 px dark outline */
  int x, y, bx0 = 999, bx1 = -1, by0 = 999, by1 = -1, w, h;
  for (y = ly0; y <= ly1; y++) for (x = x0; x <= x1; x++) { int wp = lk_o_win(y, x, 0); if (wp >= 0 && (wp & 0xF) && (wp & 0x3F) != fillp && (wp & 0x3F) != greyp) { if (x < bx0) bx0 = x; if (x > bx1) bx1 = x; if (y < by0) by0 = y; if (y > by1) by1 = y; } }
  if (bx1 < 0) { *outw = *outh = 0; return; }
  w = bx1 - bx0 + 1; h = by1 - by0 + 1; if (w > 118) w = 118; if (h > 62) h = 62; *outw = w; *outh = h;
  if (!place) return;
  memset(lk_mh_m, 0, sizeof lk_mh_m);
  for (y = 0; y < h; y++) for (x = 0; x < w; x++) { int wp = lk_o_win(by0 + y, bx0 + x, 0); if (wp >= 0 && (wp & 0xF) && (wp & 0x3F) != fillp && (wp & 0x3F) != greyp) lk_mh_m[y + 1][x + 1] = (uint8)(1 + (wp & 0x3F)); }
  for (y = 0; y < h + 2; y++) for (x = 0; x < w + 2; x++) if (!lk_mh_m[y][x]) { int n = 0, i2, j2; for (j2 = -1; j2 <= 1; j2++) for (i2 = -1; i2 <= 1; i2++) { int yy = y + j2, xx = x + i2; if (yy >= 0 && xx >= 0 && yy < 64 && xx < 120 && lk_mh_m[yy][xx]) n = 1; } if (n) lk_mh_put(dx + x - 1, dy + y - 1, 0x0A0814u, 190); }
  for (y = 0; y < h; y++) for (x = 0; x < w; x++) if (lk_mh_m[y + 1][x + 1]) lk_mh_put(dx + x, dy + y, lk_mh_rgb(lk_mh_m[y + 1][x + 1] - 1), 255);
}
static void lk_mh_glyph(int x, int y, int ch, PIXEL_OUT_T c) { int j, i, g = lk_mh_gi(ch); for (j = 0; j < 7; j++) for (i = 0; i < 5; i++) if (lk_mh_font[g][j] & (16 >> i)) lk_mh_put(x + i, y + j, c, 255); }
static void lk_mh_disc(int cx, int cy, int r, PIXEL_OUT_T fill, PIXEL_OUT_T white, PIXEL_OUT_T grey) {
  int x, y; for (y = -r - 1; y <= r + 1; y++) for (x = -r - 1; x <= r + 1; x++) { int d = x * x + y * y;
    if (d > (r + 1) * (r + 1) + r) continue;
    if (d > r * r + r) lk_mh_put(cx + x, cy + y, 0x0A0814u, 170);
    else if (d > (r - 1) * (r - 1) + (r - 1)) lk_mh_put(cx + x, cy + y, white, 235);
    else if (d > (r - 2) * (r - 2) + (r - 2)) { lk_mh_put(cx + x, cy + y, fill, 165); lk_mh_put(cx + x, cy + y, grey, 200); }
    else lk_mh_put(cx + x, cy + y, fill, 165); }
}
static void lk_mh_icon(int cx, int cy, int id, PIXEL_OUT_T fill) {   /* 16 x 16 icon of the quick icon cache centred on the disc, 1 px dark outline */
  int x, y; if (id < 0 || id > 63 || !lk_q_have[id]) return;
  for (y = -1; y <= 16; y++) for (x = -1; x <= 16; x++) { int me = (x >= 0 && y >= 0 && x < 16 && y < 16) && lk_q_mask[id][y * 16 + x], n = 0, i2, j2;
    if (me) continue; for (j2 = -1; j2 <= 1; j2++) for (i2 = -1; i2 <= 1; i2++) { int xx = x + i2, yy = y + j2; if (xx >= 0 && yy >= 0 && xx < 16 && yy < 16 && lk_q_mask[id][yy * 16 + xx]) n = 1; }
    if (n) lk_mh_put(cx - 8 + x, cy - 8 + y, 0x0A0814u, 150); }
  for (y = 0; y < 16; y++) for (x = 0; x < 16; x++) if (lk_q_mask[id][y * 16 + x]) lk_mh_put(cx - 8 + x, cy - 8 + y, lk_mh_fadec(lk_q_px[id][y * 16 + x], fill), 255);
}
static void lk_mh_count(int cx, int cy, int r, int q, PIXEL_OUT_T white) {   /* item count: 5 x 7 digits on a dark plate at the lower right of the disc */
  int two, x0, y0, x, y, wd; if (q < 0) q = 0; if (q > 99) q = 99; two = q >= 10; wd = two ? 11 : 5;
  x0 = cx + r - 4 - (two ? 6 : 0); y0 = cy + r - 6;
  for (y = -1; y <= 7; y++) for (x = -1; x <= wd; x++) lk_mh_put(x0 + x, y0 + y, 0x0A0814u, 215);
  if (two) { lk_mh_glyph(x0, y0, '0' + q / 10, white); lk_mh_glyph(x0 + 6, y0, '0' + q % 10, white); } else lk_mh_glyph(x0, y0, '0' + q, white);
}
static void lk_mh_begin(int w, int e) {
  long fr = platform_frame_number(); int y, x, fillp = -1, greyp = -1, whitep = -1, hw, hh, sw, sh, gw, gh, bottom, cx, cy, o = 16, r = 10, k;
  int top = -1, bot = -1; PIXEL_OUT_T fill, white, grey;
  if (fr == lk_mh_fr) return;
  lk_mh_fr = fr;
  for (y = lk_mh_y0; y <= lk_mh_y1 && y < LK_MH_H; y++) memset(lk_mh_a[y], 0, sizeof lk_mh_a[y]);
  lk_mh_y0 = LK_MH_H; lk_mh_y1 = -1;
  if (!lk_o_hwok || (lk_o_room >= 139 && lk_o_room <= 143)) return;   /* no HUD (intro rooms) */
  { int maj[24], uni[24], votes[64];   /* the bar's colours: per line the commonest window pixel; fill = the commonest of the lines that are NOT uniform (content lines; the lines above the bar and the border lines are one colour) */
    memset(votes, 0, sizeof votes);
    for (y = 0; y < 24; y++) { int c2[64], n = 0; memset(c2, 0, sizeof c2); maj[y] = -1; for (x = 96; x < 300; x += 3) { int wp = lk_o_win(y, x, 0); if (wp >= 0) { c2[wp & 0x3F]++; n++; } }
      for (k = 0; k < 64; k++) if (maj[y] < 0 || c2[k] > c2[maj[y]]) maj[y] = k;
      uni[y] = n == 0 || c2[maj[y]] * 20 >= n * 19; if (!uni[y]) votes[maj[y]]++; }
    for (k = 0; k < 64; k++) if (votes[k] && (fillp < 0 || votes[k] > votes[fillp])) fillp = k;
    if (fillp >= 0) for (y = 0; y < 24; y++) if (maj[y] == fillp) { if (top < 0) top = y; bot = y; }
    if (top > 0) { int ya = top - 1, yb = top - 2;   /* the border lines right above the content: the whiter one is the rim colour, the other the inner grey line */
      int pa = uni[ya] ? maj[ya] : -1, pb = (yb >= 0 && uni[yb]) ? maj[yb] : -1;
      if (pa >= 0 && pb >= 0 && pa != pb) { PIXEL_OUT_T ca = lk_mh_rgb(pa), cb = lk_mh_rgb(pb); int la = (int)(((ca >> 16) & 255) + ((ca >> 8) & 255) + (ca & 255)), lb2 = (int)(((cb >> 16) & 255) + ((cb >> 8) & 255) + (cb & 255)); if (la >= lb2) { whitep = pa; greyp = pb; } else { whitep = pb; greyp = pa; } }
      else if (pa >= 0) greyp = pa; } }
  if (top < 0 || fillp < 0) return;
  { static int dbg = -1, n; if (dbg < 0) dbg = getenv("LANDSTALKER_MHUD_DBG") != NULL; if (dbg && n++ < 3) printf("mhud: frame %ld fill %d (%06X) rim %d grey %d content lines %d..%d\n", fr, fillp, (unsigned)(lk_mh_rgb(fillp) & 0xFFFFFF), whitep, greyp, top, bot); }
  fill = lk_mh_rgb(fillp); white = whitep >= 0 ? lk_mh_rgb(whitep) : 0xEEEEEEu; grey = greyp >= 0 ? lk_mh_rgb(greyp) : 0x666666u;
  /* top left: hearts, below them sword + gauge */
  lk_mh_crop(88, 183, top, bot, 6, 5, fillp, greyp, &hw, &hh, 1);
  lk_mh_crop(15, 87, top, bot, 6, 5 + (hh ? hh : 14) + 4, fillp, greyp, &sw, &sh, 1);
  /* bottom right: gold */
  bottom = lk_tall_keep(200) ? 224 : 185;
  { char gt[8]; int g = SW(0xFF120E) & 0xFFFF, n2, k2, gx, gy, yy, xx; if (g > 9999) g = 9999;   /* gold in the small 5 x 7 font with a dark outline (user: the bar's big digits looked too large) */
    n2 = snprintf(gt, sizeof gt, "%dG", g); gw = n2 * 6 - 1; gh = 7; gx = w - 6 - gw; gy = bottom - 6 - gh;
    for (k2 = 0; k2 < n2; k2++) { int gi = lk_mh_gi(gt[k2]); for (yy = -1; yy <= 7; yy++) for (xx = -1; xx <= 5; xx++) { int on = 0, j2, i2;
        for (j2 = -1; j2 <= 1 && !on; j2++) for (i2 = -1; i2 <= 1 && !on; i2++) { int y3 = yy + j2, x3 = xx + i2; if (y3 >= 0 && y3 < 7 && x3 >= 0 && x3 < 5 && (lk_mh_font[gi][y3] & (16 >> x3))) on = 1; }
        if (on && !(yy >= 0 && yy < 7 && xx >= 0 && xx < 5 && (lk_mh_font[gi][yy] & (16 >> xx)))) lk_mh_put(gx + 6 * k2 + xx, gy + yy, 0x0A0814u, 190); }
      lk_mh_glyph(gx + 6 * k2, gy, gt[k2], white); } }
  /* top right: the pad diamond */
  cx = w - 30; cy = 31;
  { static const int bx[5] = { 0, 0, 1, -1, 0 }, by[5] = { 0, 1, 0, 0, -1 };   /* pad code 1 A bottom, 2 B right, 3 X left, 4 Y top */
    static const char lab[5] = { 0, 'A', 'B', 'X', 'Y' };
    int code, quick = lk_quick_get() > 0;
    for (code = 1; code <= 4; code++) { int dcx = cx + bx[code] * o, dcy = cy + by[code] * o, fn = -1, icon = -1, qslot = -1, f; char lb[16];
      lk_mh_disc(dcx, dcy, r, fill, white, grey);
      for (f = 0; f < 6; f++) if (f != 3 && lk_bind_pad_get(f) == code) { if (f >= 4 && !quick) continue; if (fn < 0 || f >= 4) fn = f; }   /* Quick 1 / 2 win over Button C on a shared button (as input.c does) */
      if (fn == 0) icon = SB(0xFF114E) & 0x3F;   /* MD A: the equipped sword */
      else if (fn == 1) icon = 0x3C;             /* MD B: jump = leather boots */
      else if (fn >= 4) { qslot = fn - 4; icon = lk_quick_slot_get(qslot); }
      if (icon >= 0 && icon < 64 && lk_q_have[icon]) { lk_mh_icon(dcx, dcy, icon, fill); if (qslot >= 0) lk_mh_count(dcx, dcy, r, lk_q_qty[qslot], white); }
      else { lb[0] = lab[code]; lb[1] = 0; if (fn >= 0) { lk_bind_hudlabel(fn, lb, sizeof lb); if (!lb[0] || lb[0] == '-') { lb[0] = lab[code]; lb[1] = 0; } } lk_mh_glyph(dcx - 2, dcy - 3, lb[0], white); }
    } }
  (void)e; (void)sh; (void)sw;
}
static int lk_mh_pix(int line, int i, int *col) {
  int a; PIXEL_OUT_T c, o; int sh;
  if (line < lk_mh_y0 || line > lk_mh_y1 || i < 0 || i >= LK_MH_W) return 0;
  a = lk_mh_a[line][i]; if (!a) return 0;
  c = lk_mh_c[line][i];
  if (a >= 255) { *col = (int)((c & 0xFFFFFFu) | ((PIXEL_OUT_T)*col & 0xFF000000u)); return 1; }
  o = (PIXEL_OUT_T)*col & 0xFF000000u;
  for (sh = 0; sh < 24; sh += 8) { int v1 = (int)((c >> sh) & 255), v0 = (int)(((PIXEL_OUT_T)*col >> sh) & 255); o |= (PIXEL_OUT_T)((v1 * a + v0 * (255 - a)) / 255) << sh; }
  *col = (int)o; return 1;
}
/* item icons straight from the ROM (user 2026-10-30): sprite graphic $23 (the item sprites), animation (id >> 3) * 4, frame (id & 7) * 4 (GetSpriteGfxParams $0046EE / LoadSprite),
   chunk list as LoadSpriteTiles $00473E (zero fill / raw / LZ77), 4 x 4 tiles column-major (tile r + 4 c, as PopulateItemSlot_WriteIcon $00D642 lays them out), palette InvItemPal $007896
   (16 words, CopyPalette to palette line 1 by InitInvDisplay); shrunk to the 16 x 16 cache exactly like lk_quick_capture; the 32 x 32 originals stay in lk_qr_raw (larger icons later) */
static uint8 lk_qr_raw[64][32][32]; static uint8 lk_qr_ok[64];
static int lk_qr_decode(int id) {
  static uint8 t[0x4000]; uint32_t base, ap, fp, pos; int guard, tl = 0, np = 0, r, c, y, x;
  if (id < 0 || id > 63) return 0;
  base = OL(0x120000); { int ofs = OW(0x120004 + 4 * 0x23); ap = OL(base + (uint32_t)ofs * 4 + (uint32_t)(((id >> 3) & 7) * 4)); }
  if (ap >= 0x200000u) return 0;
  fp = OL(ap + (uint32_t)((id & 7) * 4)); if (fp >= 0x200000u) return 0;
  pos = fp; for (;;) { int b2 = OB(pos + 1); pos += 2; np++; if ((b2 & 0x80) || np >= 8) break; }
  for (guard = 0; guard < 64; guard++) { int h = OW(pos), n = h & 0x0FFF, i; pos += 2;
    if (h & 0x8000) { for (i = 0; i < n * 2 && tl + i < 0x4000; i++) t[tl + i] = 0; tl += n * 2; }
    else if (h & 0x2000) { tl += lk_o_lz77(pos, t + tl, 0x4000 - tl); break; }
    else { for (i = 0; i < n * 2 && tl + i < 0x4000; i++) t[tl + i] = (uint8)OB(pos + (uint32_t)i); pos += (uint32_t)n * 2; tl += n * 2; }
    if ((h & 0x4000) || tl >= 0x4000) break; }
  if (tl < 16 * 32) return 0;
  for (r = 0; r < 4; r++) for (c = 0; c < 4; c++) { int k = r + 4 * c; for (y = 0; y < 8; y++) for (x = 0; x < 8; x++) { uint8 bb = t[k * 32 + y * 4 + (x >> 1)]; lk_qr_raw[id][r * 8 + y][c * 8 + x] = (x & 1) ? (bb & 15) : (bb >> 4); } }
  lk_qr_ok[id] = 1; return 1;
}
static PIXEL_OUT_T lk_qr_col(int i) { int c = OW(0x7896 + 2 * (i & 15)); return pixel_lut[1][((c >> 9) & 7) << 6 | ((c >> 5) & 7) << 3 | ((c >> 1) & 7)]; }
static void lk_qr_fill(void) {
  static int done; int id, y, x;
  if (done) return; done = 1;
  for (id = 0; id < 64; id++) {
    int bx0 = 99, by0 = 99, bx1 = -1, by1 = -1, w, h, mx, sw, sh, ox, oy, lit = 0;
    if (!lk_qr_decode(id)) continue;
    for (y = 0; y < 32; y++) for (x = 0; x < 32; x++) if (lk_qr_raw[id][y][x]) { if (x < bx0) bx0 = x; if (x > bx1) bx1 = x; if (y < by0) by0 = y; if (y > by1) by1 = y; }
    if (bx1 < 0) continue;
    w = bx1 - bx0 + 1; h = by1 - by0 + 1; mx = w > h ? w : h;
    sw = (w * 16 + mx / 2) / mx; sh = (h * 16 + mx / 2) / mx; if (sw < 1) sw = 1; if (sh < 1) sh = 1; if (sw > 16) sw = 16; if (sh > 16) sh = 16;
    ox = (16 - sw) / 2; oy = (16 - sh) / 2;
    memset(lk_q_mask[id], 0, 256);
    for (y = 0; y < 16; y++) for (x = 0; x < 16; x++) {
      int ya, yb, xa, xb, yy, xx, n = 0, tot, sr = 0, sg = 0, sb = 0, sa = 0;
      if (x < ox || x >= ox + sw || y < oy || y >= oy + sh) continue;
      ya = by0 + (y - oy) * h / sh; yb = by0 + ((y - oy + 1) * h + sh - 1) / sh; xa = bx0 + (x - ox) * w / sw; xb = bx0 + ((x - ox + 1) * w + sw - 1) / sw;
      if (yb <= ya) yb = ya + 1; if (xb <= xa) xb = xa + 1; tot = (yb - ya) * (xb - xa);
      for (yy = ya; yy < yb && yy < 32; yy++) for (xx = xa; xx < xb && xx < 32; xx++) if (lk_qr_raw[id][yy][xx]) { PIXEL_OUT_T pv = lk_qr_col(lk_qr_raw[id][yy][xx]); n++; sr += (pv >> 16) & 255; sg += (pv >> 8) & 255; sb += pv & 255; sa += (pv >> 24) & 255; }
      if (n * 2 < tot || !n) continue;
      lk_q_px[id][y * 16 + x] = ((PIXEL_OUT_T)(sa / n) << 24) | ((PIXEL_OUT_T)(sr / n) << 16) | ((PIXEL_OUT_T)(sg / n) << 8) | (PIXEL_OUT_T)(sb / n);
      lk_q_mask[id][y * 16 + x] = 1; if (lk_q_px[id][y * 16 + x] & 0xFFFFFF) lit = 1;
    }
    if (lit) lk_q_have[id] = 1; else memset(lk_q_mask[id], 0, 256);
  }
  { const char *e = getenv("LANDSTALKER_ICON_DUMP"); if (e && *e) { FILE *f = fopen(e, "wb"); if (f) { for (id = 0; id < 64; id++) if (lk_q_have[id]) { uint8 b = (uint8)id; fwrite(&b, 1, 1, f); fwrite(lk_q_mask[id], 1, 256, f); fwrite(lk_q_px[id], sizeof(PIXEL_OUT_T), 256, f); } fclose(f); } } }   /* test aid: the icons in the cache file format */
}
/* ---- end LK_MHUD v1 ---- */
'''
    s = s.rstrip("\n") + "\n" + module
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
