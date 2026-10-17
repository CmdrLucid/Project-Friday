#!/usr/bin/env python3
"""Model overlay (2026-10-17, renderer groundwork, RENDERER_IDEAS Option B step 1): draws what the game STATE says is on screen over the normal picture, so the two can be compared.
For every visible entity (list g_VisibleEntityList $FF11DE) it draws, from work RAM only (picture only, nothing is written to the game):
 * a cross at the position the game stored for the sprite (+0E x / +10 y, minus $80) in a colour per slot,
 * the diamond of the hit box (+18 x1, +1A x2, +1C y1, +1E y2) on the floor under the entity at its Z, projected with OUR copy of the game's formula
   (CheckEntityOnScreen $004144: a = X - Z - cam$FF1200, b = Y - Z - cam$FF1202, screen x = a - b + $A0, screen y = ((a + b + k) >> 1) + $68, k = 0 for the player else word $FF1180 ^ 1),
 * a tiny label: sprite graphic id, animation / 4, frame / 4 in hex (the stable sprite key, FORMATS.md 'Sprite upload').
Env LANDSTALKER_MODEL=1 switches it on (off by default, debug aid); LANDSTALKER_MODEL_LOG=N prints, every N frames, per entity the game's screen position and the model's (they must agree).
Hidden while a full-screen picture is shown (lk_picture).  Needs patch_wide.py and patch_overlay.py first.  Idempotent.  usage: patch_model.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_MODEL v1"
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    d = "      lk_win_draw(lk_row0, lk_w0);   /* LK_WIN v1 */\n"
    assert s.count(d) == 1, "vdp_render.c: run patch_overlay.py first"
    s = s.replace(d, d + "      lk_model_row(lk_row0, lk_w0);   /* LK_MODEL v1 */\n", 1)
    c = "void render_line(int line)"
    assert s.count(c) == 1
    module = r'''/* ---- LK_MODEL v1: state-driven model overlay (tools/patch_model.py) ---- */
extern uint8_t *bus_get_ram(void);
extern int lk_picture;
#define LK_M_N 16
typedef struct { int ax, ay, gx[4], gy[4], id, m_g, m_a, m_f; } lk_m_ent_t;
static lk_m_ent_t lk_m_e[LK_M_N]; static int lk_m_n, lk_m_on = -1, lk_m_log;
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
  if (lk_m_on < 0) { const char *e = getenv("LANDSTALKER_MODEL"), *l = getenv("LANDSTALKER_MODEL_LOG"); lk_m_on = e && atoi(e) != 0; lk_m_log = l ? atoi(l) : 0; }
  if (!lk_m_on) return;
  if (line == 0) { fr++; if (!lk_m_log || fr % lk_m_log) { int sv = lk_m_log; lk_m_log = 0; lk_m_snapshot(); lk_m_log = sv; } else lk_m_snapshot(); }
  if (lk_picture || Wp < 320 || width < Wp + 2 * ox) return;
  r = row + ox; x0 = (Wp - 320) / 2;
  for (i = 0; i < lk_m_n; i++) {
    const lk_m_ent_t *e = &lk_m_e[i]; uint32 col = lk_m_col[e->id & 15];
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
