#!/usr/bin/env python3
"""Option 'Enemy Dissolve' (2026-11-05 night, user: modern effects list item 6 'Gegner zerfallen beim Besiegen in Partikel'; 'auch den Rest immer optional').
When an enemy's health (entity +$3E, FORMATS 'Entity struct') drops to 0, its sprite pixels of that frame (own renderer: lk_o_spr + lk_lt_spre entity tag)
burst into small particles in the enemy's own colours that fly apart, rise a little and fade (the game's own death animation still plays).
Picture only: no game state is read for anything but the trigger, nothing is written.  Screen-space particles (follow the camera by its pixel position $FF1200 / $FF1202).
Option: Options > Graphics > Enemy Dissolve (id 50, ~/.landstalker_dissolve, env LANDSTALKER_DISSOLVE=0|1 wins), default On.
Test aid: LANDSTALKER_DISSOLVE_DBG=1 prints every health change of an enemy slot and every burst.
Needs patch_own.py, patch_subpix.py, patch_swordfx.py, patch_lights.py (lk_lt_spre) before it.  Idempotent.  usage: patch_dissolve.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_DISSOLVE v1"

p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
def rep(a, b):
    global s
    assert s.count(a) == 1, ("vdp_render.c: anchor not found once", a[:80])
    s = s.replace(a, b)

if VER not in s:
    MODULE = r'''/* ---- %s: enemies burst into particles when defeated (tools/patch_dissolve.py) ---- */
static int lk_dz_o = -1;
int lk_dz_get(void) { if (lk_dz_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_DISSOLVE"); char pth[512]; FILE *f; int v = 1; snprintf(pth, sizeof pth, "%%s/.landstalker_dissolve", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%%d", &v) != 1) v = 1; fclose(f); } if (e) v = atoi(e); lk_dz_o = v ? 1 : 0; } return lk_dz_o; }
void lk_dz_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_dz_get(); lk_dz_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%%s/.landstalker_dissolve", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%%d\n", lk_dz_o); fclose(f); } }
#define LK_DZ_N 1400
typedef struct { float x, y, vx, vy; uint32_t rgb; uint8 age, life, big; } lk_dz_p;
static lk_dz_p lk_dz_ps[LK_DZ_N]; static int lk_dz_np; static long lk_dz_frame = -1; static uint32_t lk_dz_rng = 777u;
static uint32_t lk_dz_buf[224][LK_OSW]; static uint8 lk_dz_line[224];
static int16_t lk_dz_hp[64]; static uint8 lk_dz_en[64]; static int lk_dz_room = -1, lk_dz_cx, lk_dz_cy;
static float lk_dz_rnd(void) { lk_dz_rng = lk_dz_rng * 1664525u + 1013904223u; return (float)((lk_dz_rng >> 8) & 0xFFFF) / 65536.0f; }
static void lk_dz_put(int x, int y, uint32_t rgb, float a) {
  if (y < 0 || y >= 224 || x < 0 || x >= LK_OSW || a <= 0.0f) return;
  if (a > 1.0f) a = 1.0f;
  { uint32_t al = (uint32_t)(a * 255.0f); if ((lk_dz_buf[y][x] >> 24) < al) lk_dz_buf[y][x] = (al << 24) | (rgb & 0xFFFFFF); lk_dz_line[y] = 1; } }
static void lk_dz_burst(int tag) {   /* the pixels of entity tag (offset / 0x80 + 1) of this frame's sprite picture -> particles */
  int x, y, n = 0, sx = 0, sy = 0, k; float cx, cy;
  for (y = 0; y < 224; y++) for (x = 0; x < LK_OSW; x++) if ((lk_o_spr[y][x] & 0x200) && lk_lt_spre[y][x] == tag) { n++; sx += x; sy += y; }
  if (!n) return;
  cx = (float)sx / (float)n; cy = (float)sy / (float)n; k = 0;
  for (y = 0; y < 224; y++) for (x = 0; x < LK_OSW; x++) if ((lk_o_spr[y][x] & 0x200) && lk_lt_spre[y][x] == tag) {
    lk_dz_p *P; float dx, dy, d, sp;
    if ((k++ %% (n > 500 ? 3 : n > 250 ? 2 : 1)) || lk_dz_np >= LK_DZ_N) continue;   /* at most ~250 particles per enemy */
    P = &lk_dz_ps[lk_dz_np++]; dx = (float)x - cx; dy = (float)y - cy; d = sqrtf(dx * dx + dy * dy) + 0.5f; sp = 0.25f + lk_dz_rnd() * 0.75f;
    P->x = (float)x + 0.5f; P->y = (float)y + 0.5f; P->vx = dx / d * sp + (lk_dz_rnd() - 0.5f) * 0.3f; P->vy = dy / d * sp * 0.6f - 0.35f - lk_dz_rnd() * 0.5f;
    P->rgb = (uint32_t)lk_o_pix[lk_o_spr[y][x] & 0x3F] & 0xFFFFFFu; P->age = 0; P->life = (uint8)(18 + (int)(lk_dz_rnd() * 22.0f)); P->big = lk_dz_rnd() < 0.2f; }
  if (getenv("LANDSTALKER_DISSOLVE_DBG")) printf("dissolve: frame %%ld tag %%d burst %%d pixels\n", platform_frame_number(), tag, n);
}
static void lk_dz_step(void) {   /* once per map frame (first composed line) */
  int y, k, keep, cxn, cyn, room; long fr = platform_frame_number(); uint32_t a;
  lk_dz_frame = fr;
  for (y = 0; y < 224; y++) if (lk_dz_line[y]) { memset(lk_dz_buf[y], 0, sizeof lk_dz_buf[y]); lk_dz_line[y] = 0; }
  room = SW(0xFF1204); cxn = SW(0xFF1200); cyn = SW(0xFF1202);
  if (room != lk_dz_room) { lk_dz_room = room; lk_dz_np = 0; memset(lk_dz_en, 0, sizeof lk_dz_en); }
  for (k = 0; k < lk_dz_np; k++) { lk_dz_ps[k].x -= (float)(cxn - lk_dz_cx); lk_dz_ps[k].y -= (float)(cyn - lk_dz_cy); }   /* the camera moved: keep the particles where they were in the room */
  lk_dz_cx = cxn; lk_dz_cy = cyn;
  for (k = 1, a = 0xFF5480; k < 64; k++, a += 0x80) {   /* entity slots: $FF ends the list, $7F = unused (FORMATS 'Slot list') */
    int f0 = SB(a), hp, en;
    if (f0 == 0xFF) break;
    if (f0 == 0x7F) { lk_dz_en[k] = 0; continue; }
    hp = (int16_t)SW(a + 0x3E); en = (SB(a + 0x0C) & 0x82) == 0x80;   /* enemy: +$0C & $82 = $80 (HandleAttack_EnemyLoop) */
    if (getenv("LANDSTALKER_DISSOLVE_DBG") && hp != lk_dz_hp[k]) printf("dissolve: frame %%ld slot %%d hp %%d -> %%d flags0C %%02X en %%d (before %%d)\n", fr, k, lk_dz_hp[k], hp, SB(a + 0x0C), en, lk_dz_en[k]);
    if (lk_dz_en[k] && lk_dz_hp[k] > 0 && hp <= 0) lk_dz_burst(k + 1);   /* enemy in the frame BEFORE (the flags are cleared on the death frame; +$3E then counts the death animation) */
    lk_dz_en[k] = (uint8)en; lk_dz_hp[k] = (int16_t)hp; }
  for (k = 0, keep = 0; k < lk_dz_np; k++) { lk_dz_p *P = &lk_dz_ps[k]; float t;
    if (++P->age >= P->life) continue;
    t = 1.0f - (float)P->age / (float)P->life;
    P->x += P->vx; P->y += P->vy; P->vx *= 0.96f; P->vy = P->vy * 0.96f - 0.012f;   /* drift apart, float up */
    lk_dz_put((int)P->x, (int)P->y, P->rgb, t * 0.95f);
    if (P->big && t > 0.4f) { lk_dz_put((int)P->x + 1, (int)P->y, P->rgb, t * 0.6f); lk_dz_put((int)P->x, (int)P->y + 1, P->rgb, t * 0.6f); }
    lk_dz_ps[keep++] = *P; }
  lk_dz_np = keep; }
static int lk_dz_linebegin(int line) {
  if (!lk_dz_get()) return 0;
  if (lk_dz_frame != platform_frame_number()) lk_dz_step();
  return line >= 0 && line < 224 && lk_dz_line[line];
}
static int lk_dz_pix(int line, int i, int col) { uint32_t b; if (i < 0 || i >= LK_OSW) return col; b = lk_dz_buf[line][i]; if (!(b >> 24)) return col; return lk_sfx_mix(col, b, b >> 24); }

''' % VER
    a = "static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {\n"
    rep(a, MODULE + a)
    a = "    int lk_lt_ln = lk_lt_linebegin();   /* LK_LIGHTS v8 */\n"
    rep(a, a + "    int lk_dz_ln = lk_dz_linebegin(line);   /* %s */\n" % VER)
    a = "      if (lk_sfx_ln && !black && src != 4) col = lk_sfx_pix(line, i, src == 1 ? sp : 0, col);   /* LK_SWORDFX v1 */\n"
    rep(a, a + "      if (lk_dz_ln && !black && src != 4) col = lk_dz_pix(line, i, col);   /* %s */\n" % VER)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
else:
    print("vdp_render.c already patched:", VER)
