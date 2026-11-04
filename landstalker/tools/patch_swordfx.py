#!/usr/bin/env python3
"""Sword effects (2026-11-02, user: 'dezenter Effekt je Schwert: Flammen beim Feuerschwert, Blitze beim Donnerschwert ... nicht uebertreiben',
then 'etwas staerker', 'Gaia gruen', 'Partikel noch staerker' = mock-up 4 `~/Mockups/schwerteffekte4.html`).  While Nigel swings a sword
(Player_ActionHigh $FF542C bits 0..3 = 1..4) the own map renderer tints the swing arc + blade and lets a few 1-2 px particles come off it:
 * the arc / blade pixels are the sprite pixels of colour 45 / 46 (palette line 2, entries 13 / 14): UpdateEquipPal $0078B6 copies the
   sword's two colours there (SwordPalSwaps $007900: none grey, Magic orange / red, Ice blue, Thunder violet / white, Gaia brown);
 * per sword (EquippedSword $FF114E): 1 Magic = warm arc + embers rising (yellow -> orange -> red), 2 Ice = light blue arc + frost glitter
   drifting down (some twinkle as a small +), 3 Thunder = yellow arc + short zig-zag bolts every 2nd frame, 4 Gaia = GREEN arc (user) +
   green light motes rising; no / basic sword = nothing;
 * particles live in screen space (8..18 frames), a deterministic random stream seeded by the frame number: picture only, the game state
   and the sound are untouched (option Off = bit exact).
Option: Options > Video > Sword Effects Off / On (id 46, ~/.landstalker_swordfx, env LANDSTALKER_SWORDFX=0|1), default ON since 2026-11-05 (was Off).
Screens (file select, user 2026-11-05: the Gaia sword of save 1 stayed brown while Nigel swings it there; then 'Partikeleffekte auch im File Select'): lk_sfx_scrpix
tints the sword colours 45 / 46 of sprites in the screen renderer (patch_own.py lk_scr_line) with the equipped sword's effect colour and spawns the same particles
from those pixels (collected while drawing, used the next frame).
Test aid: LANDSTALKER_SWORDFX_KIND=1..4 = draw another sword's effect (while any of the four swords is equipped).
Map path of lk_own_row only (swings happen on the map).  Needs patch_own.py and patch_modernhud.py before it.  Idempotent.
usage: patch_swordfx.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_SWORDFX v1"
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER in s:
    print("vdp_render.c already patched:", VER); sys.exit(0)

def rep(a, b):
    global s
    assert s.count(a) == 1, f"vdp_render.c layout changed: {a[:70]!r} ({s.count(a)}x)"
    s = s.replace(a, b, 1)

MODULE = r'''/* ---- %s: sword effects (tools/patch_swordfx.py) ---- */
static int lk_sfx_o = -1;
int lk_sfx_get(void) { if (lk_sfx_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_SWORDFX"); char pth[512]; FILE *f; int v = 1;   /* default ON since 2026-11-05 (user: 'Sword Effects standardmaessig an') */ snprintf(pth, sizeof pth, "%%s/.landstalker_swordfx", h ? h : "."); v = 1; f = fopen(pth, "r"); if (f) { if (fscanf(f, "%%d", &v) != 1) v = 1; fclose(f); } if (e && *e) v = atoi(e); lk_sfx_o = v ? 1 : 0; } return lk_sfx_o; }
void lk_sfx_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_sfx_get(); lk_sfx_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_swordfx", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_sfx_o); fclose(f); } }
typedef struct { float x, y, vx, vy, g; uint8 age, life, big, nb; int16_t bx[10], by[10]; } lk_sfx_p;
#define LK_SFX_N 160
static lk_sfx_p lk_sfx_ps[LK_SFX_N]; static int lk_sfx_np, lk_sfx_kind;   /* kind: 0 none, 1 fire, 2 ice, 3 thunder, 4 gaia */
static long lk_sfx_frame = -1; static uint32_t lk_sfx_rng;
static uint32_t lk_sfx_buf[224][LK_OSW]; static uint8 lk_sfx_line[224];   /* particle colour (alpha in the top byte) per screen pixel, lines in use */
static uint8 lk_sfx_act;   /* 1 = a swing is on in this frame (the arc tint applies) */
static uint32_t lk_sfx_tint[5][2] = { { 0, 0 }, { 0xF56E14u, 0xAA320Au }, { 0x78BEF5u, 0x326EBEu }, { 0xF0DC46u, 0x968214u }, { 0x3CBE5Au, 0x146E32u } };   /* colour 45 (lighter) / 46 (darker) per sword */
static float lk_sfx_rnd(void) { lk_sfx_rng = lk_sfx_rng * 1664525u + 1013904223u; return (float)((lk_sfx_rng >> 8) & 0xFFFF) / 65536.0f; }
static int lk_sfx_ri(int a, int b) { return a + (int)(lk_sfx_rnd() * (float)(b - a + 1)); }
static void lk_sfx_put(int x, int y, uint32_t rgb, float a) {
  if (y < 0 || y >= 224 || x < 0 || x >= LK_OSW || a <= 0.0f) return;
  if (a > 1.0f) a = 1.0f;
  { uint32_t al = (uint32_t)(a * 255.0f); if ((lk_sfx_buf[y][x] >> 24) < al) lk_sfx_buf[y][x] = (al << 24) | (rgb & 0xFFFFFF); lk_sfx_line[y] = 1; }
}
static int lk_sfx_scrm; static int16_t lk_sfx_sax[4096], lk_sfx_say[4096]; static int lk_sfx_sna;   /* screens (file select): the frame is drawn by the screen renderer; sword pixels collected while drawing (spawn points of the next frame) */
static void lk_sfx_step(void) {   /* once per frame (first composed line): swing state, spawn from this frame's arc pixels, move + draw the particles */
  static int16_t ax[4096], ay[4096]; int na = 0, x, y, k, w = 320 + 2 * lk_wide_e, sw = SB(0xFF114E) & 0xFF, ph = SB(0xFF542C) & 0x0F;
  long fr = platform_frame_number(); int keep;
  lk_sfx_frame = fr; lk_sfx_rng = (uint32_t)fr * 2654435761u + 12345u;
  for (y = 0; y < 224; y++) if (lk_sfx_line[y]) { memset(lk_sfx_buf[y], 0, sizeof lk_sfx_buf[y]); lk_sfx_line[y] = 0; }
  { static int tk = -1; if (tk < 0) { const char *e = getenv("LANDSTALKER_SWORDFX_KIND"); tk = (e && *e) ? atoi(e) : 0; } if (tk >= 1 && tk <= 4 && sw >= 1 && sw <= 4) sw = tk; }   /* test aid: the effect of another sword (picture only) */
  lk_sfx_kind = (sw >= 1 && sw <= 4) ? sw : 0;
  lk_sfx_act = lk_sfx_kind && (lk_sfx_scrm ? lk_sfx_sna > 0 : (ph >= 1 && ph <= 4));
  if (!lk_sfx_kind) lk_sfx_np = 0;
  if (lk_sfx_scrm) { for (k = 0; k < lk_sfx_sna; k++) { ax[na] = lk_sfx_sax[k]; ay[na] = lk_sfx_say[k]; na++; } lk_sfx_sna = 0; }   /* screens: the sword pixels of the frame before */
  else if (lk_sfx_act) for (y = 0; y < 224 && na < 4096; y++) for (x = 0; x < w && x < LK_OSW && na < 4096; x++) { uint16 v = lk_o_spr[y][x]; if ((v & 0x200) && ((v & 0x3F) == 45 || (v & 0x3F) == 46)) { ax[na] = (int16_t)x; ay[na] = (int16_t)y; na++; } }
  if (na) {   /* spawn (mock-up 4 rates) */
    int n = lk_sfx_kind == 1 ? lk_sfx_ri(3, 5) : lk_sfx_kind == 3 ? ((fr & 1) == 0) : lk_sfx_ri(2, 4);
    for (k = 0; k < n && lk_sfx_np < LK_SFX_N; k++) {
      lk_sfx_p *q = &lk_sfx_ps[lk_sfx_np++]; int i = lk_sfx_ri(0, na - 1);
      memset(q, 0, sizeof *q); q->x = (float)ax[i] + 0.5f; q->y = (float)ay[i] + 0.5f; q->big = lk_sfx_rnd() < 0.5f;
      if (lk_sfx_kind == 1) { q->vx = lk_sfx_rnd() * 0.3f - 0.15f; q->vy = -0.4f - lk_sfx_rnd() * 0.3f; q->life = (uint8)lk_sfx_ri(8, 13); }
      else if (lk_sfx_kind == 2) { q->vx = lk_sfx_rnd() * 0.2f - 0.1f; q->vy = 0.15f + lk_sfx_rnd() * 0.2f; q->life = (uint8)lk_sfx_ri(10, 18); }
      else if (lk_sfx_kind == 4) { q->vx = lk_sfx_rnd() * 0.5f - 0.25f; q->vy = -0.25f - lk_sfx_rnd() * 0.3f; q->life = (uint8)lk_sfx_ri(12, 18); }
      else { int bx = ax[i], by = ay[i], d = lk_sfx_rnd() < 0.5f ? -1 : 1, j, m = lk_sfx_ri(5, 9); q->life = 3; q->bx[0] = (int16_t)bx; q->by[0] = (int16_t)by; q->nb = 1;
        for (j = 0; j < m && q->nb < 10; j++) { bx += d * lk_sfx_ri(1, 2); by += (lk_sfx_rnd() < 0.5f ? -1 : 1) * lk_sfx_ri(1, 2); q->bx[q->nb] = (int16_t)bx; q->by[q->nb] = (int16_t)by; q->nb++; } }
    }
  }
  for (k = 0, keep = 0; k < lk_sfx_np; k++) {
    lk_sfx_p *q = &lk_sfx_ps[k]; float a = 1.0f - (float)q->age / (float)q->life, al = a * 1.15f; uint32_t c; int px = (int)q->x, py = (int)q->y;
    if (lk_sfx_kind == 3) {
      int j; c = q->age == 0 ? 0xFFFFC8u : 0x96BEFFu;
      for (j = 0; j + 1 < q->nb; j++) { int x0 = q->bx[j], y0 = q->by[j], x1 = q->bx[j + 1], y1 = q->by[j + 1], dn = abs(x1 - x0) > abs(y1 - y0) ? abs(x1 - x0) : abs(y1 - y0), t; if (!dn) dn = 1;
        for (t = 0; t <= dn; t++) lk_sfx_put(x0 + (x1 - x0) * t / dn, y0 + (y1 - y0) * t / dn, c, 0.85f * a); }
    } else {
      if (lk_sfx_kind == 1) c = q->age < 2 ? 0xFFE678u : q->age < 5 ? 0xFF9628u : 0xC83C14u;
      else if (lk_sfx_kind == 2) c = ((q->age >> 1) & 1) ? 0xA0D2FFu : 0xEBFAFFu;
      else c = q->age < 3 ? 0xC8FFAAu : q->age < 9 ? 0x5ADC6Eu : 0x289646u;
      lk_sfx_put(px, py, c, al);
      if (q->big && (lk_sfx_kind == 1 || lk_sfx_kind == 4) && q->age < 7) { lk_sfx_put(px + 1, py, c, al); lk_sfx_put(px, py + 1, c, al); lk_sfx_put(px + 1, py + 1, c, al); }
      if (q->big && lk_sfx_kind == 2 && !((q->age >> 1) & 1)) { lk_sfx_put(px - 1, py, c, al); lk_sfx_put(px + 1, py, c, al); lk_sfx_put(px, py - 1, c, al); lk_sfx_put(px, py + 1, c, al); }
      q->x += q->vx; q->y += q->vy; q->vy += q->g;
    }
    q->age++;
    if (q->age < q->life) lk_sfx_ps[keep++] = *q;
  }
  lk_sfx_np = keep;
}
static inline int lk_sfx_mix(int col, uint32_t rgb, unsigned a) {   /* a = 0..255 */
  uint32_t c = (uint32_t)col, o = c & 0xFF000000u; int ch;
  for (ch = 0; ch < 24; ch += 8) o |= ((((c >> ch) & 255) * (255 - a) + ((rgb >> ch) & 255) * a) / 255) << ch;
  return (int)o;
}
static int lk_sfx_linebegin(int line) {   /* once per composed line: 1 = this line needs the per-pixel call (option on and a swing / particles) */
  if (!lk_sfx_get()) return 0;
  if (lk_sfx_frame != platform_frame_number()) { lk_sfx_scrm = 0; lk_sfx_step(); }
  return lk_sfx_act || (line >= 0 && line < 224 && lk_sfx_line[line]);
}
int lk_sfx_scrpix(int line, int x, int ci, int col) {   /* every pixel of the screen renderer: ci = palette entry of a winning sprite pixel, else -1 */   /* screen renderer (file select): a sprite pixel of the sword colours 45 / 46 -> the equipped sword's effect colour, like the swing arc on the map
     (the file select loads the slot's equipment: GameSelect_LoadSlotAndPalette $00FAF0 -> EquippedSword $FF114E and the sword palette) */
  int sw, i = x + lk_wide_e;
  if (!lk_sfx_get()) return col;
  if (lk_sfx_frame != platform_frame_number()) { lk_sfx_scrm = 1; lk_sfx_step(); }   /* a frame of the screen renderer: particles from the sword pixels (user 2026-11-05: 'Partikeleffekte auch im File Select') */
  { static long dbg = -2, cur = -1; static int cnt[64]; long fr = platform_frame_number();   /* test aid: LANDSTALKER_SFX_SCRDBG=frame prints the palette entries of the sprite pixels of that frame */
    if (dbg == -2) { const char *e = getenv("LANDSTALKER_SFX_SCRDBG"); dbg = e ? (strcmp(e, "all") ? atol(e) : -9) : -1; }
    if (dbg == -9) { static long lf = -1; static int n45; if (fr != lf) { if (lf >= 0 && n45) printf("sfx scr: frame %%ld %%d sword-colour pixels, sword %%d\n", lf, n45, SB(0xFF114E) & 0xFF); lf = fr; n45 = 0; } if (ci == 45 || ci == 46) n45++; }
    if (dbg >= 0) { if (fr == dbg) { cnt[ci & 63]++; cur = fr; } else if (cur >= 0) { int k; printf("sfx scr: frame %%ld sprite colours:", cur); for (k = 0; k < 64; k++) if (cnt[k]) printf(" %%d:%%d", k, cnt[k]); printf(" sword %%d\n", SB(0xFF114E) & 0xFF); cur = -1; } } }
  if (ci == 45 || ci == 46) { sw = SB(0xFF114E) & 0xFF; { static int tk = -1; if (tk < 0) { const char *e = getenv("LANDSTALKER_SWORDFX_KIND"); tk = (e && *e) ? atoi(e) : 0; } if (tk >= 1 && tk <= 4 && sw >= 1 && sw <= 4) sw = tk; }
    if (sw >= 1 && sw <= 4) { col = lk_sfx_mix(col, lk_sfx_tint[sw][ci - 45], 217);
      if (line >= 0 && line < 224 && i >= 0 && i < LK_OSW && lk_sfx_sna < 4096) { lk_sfx_sax[lk_sfx_sna] = (int16_t)i; lk_sfx_say[lk_sfx_sna] = (int16_t)line; lk_sfx_sna++; } } }
  if (line >= 0 && line < 224 && lk_sfx_line[line] && i >= 0 && i < LK_OSW) { uint32_t b = lk_sfx_buf[line][i]; if (b >> 24) col = lk_sfx_mix(col, b, b >> 24); }
  return col;
}
static int lk_sfx_pix(int line, int i, int sp, int col) {   /* one composed map pixel: sp = the winning sprite pixel (0 when a plane / window won) */
  if (lk_sfx_act && (sp & 0x200)) { int pk = sp & 0x3F; if (pk == 45 || pk == 46) col = lk_sfx_mix(col, lk_sfx_tint[lk_sfx_kind][pk - 45], 217); }   /* 85 %% the sword colour */
  if (line >= 0 && line < 224 && lk_sfx_line[line] && i >= 0 && i < LK_OSW) { uint32_t b = lk_sfx_buf[line][i]; if (b >> 24) col = lk_sfx_mix(col, b, b >> 24); }
  return col;
}

''' % VER

a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
rep(a, MODULE + a)
rep("    lk_o_shline = line;\n", "    lk_o_shline = line; int lk_sfx_ln = lk_sfx_linebegin(line);   /* %s */\n" % VER)
rep("      lk_mh_hit = nohud ? lk_mh_pix(line, i, &col) : 0;   /* LK_MHUD v3 */\n",
    "      if (lk_sfx_ln && !black && src != 4) col = lk_sfx_pix(line, i, src == 1 ? sp : 0, col);   /* %s */\n" % VER +
    "      lk_mh_hit = nohud ? lk_mh_pix(line, i, &col) : 0;   /* LK_MHUD v3 */\n")
open(p, "w").write(s)
print("vdp_render.c patched:", VER)
# screen renderer hook (file select): forward declaration + the call on the winning sprite pixel
rep("static int lk_scr_line(int line, PIXEL_OUT_T *out, int e, int dispforce) {", "int lk_sfx_scrpix(int line, int x, int ci, int col);   /* %s */\nstatic int lk_scr_line(int line, PIXEL_OUT_T *out, int e, int dispforce) {" % VER)
rep("    else { cc = sel >= 0 ? lk_scr_cramw(sel) : bgcol; if (x + ex < 8 && (lk_rg[0] & 0x20)) { cc = bgcol; wi = 0; } col32 = pixel_lut[1][cc]; }\n",
    "    else { cc = sel >= 0 ? lk_scr_cramw(sel) : bgcol; if (x + ex < 8 && (lk_rg[0] & 0x20)) { cc = bgcol; wi = 0; } col32 = pixel_lut[1][cc];\n"
    "      col32 = (uint32_t)lk_sfx_scrpix(line, x, (sel >= 0 && sel < 0x1000000 && wi == &spi[x + 48]) ? (sel & 0x3F) : -1, (int)col32); }   /* %s: sword colours + particles on screens (file select) */\n" % VER)
open(p, "w").write(s)
print("vdp_render.c patched: screen sword tint")

