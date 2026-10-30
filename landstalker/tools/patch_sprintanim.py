#!/usr/bin/env python3
"""Sprint animation (2026-10-30, user: 'Sprint-Animation fertig machen und an den Sprint haengen'; design = variant G of docs/SPRINT_IDEAS.md,
remake/tools/sprint_mock.py).  While Sprint really moved Nigel in this frame (lk_sprint_active, tools/patch_sprint.py) and he shows a WALK frame
(animation 8 = back view, 12 = front view, frame = frm / 4), the own renderer draws his pieces into a small canvas first and turns that picture
into the sprint pose before it goes into the sprite layer:
 * lean in bands (rows from the top of the frame's piece box, as rom_sprite.py cuts the frames): rows 0..17 move 4 px forward, 18..19 3 px,
   20..22 2 px, 23..26 1 px (the head stays one block, every outline step is 1 px);
 * own cadence: one walk picture per 3 game frames (the game turns them every 2 frames at the sprint step: too hectic, user), the picture loaded
   from the ROM by the renderer's pose override (lk_o_ovr_anim / lk_o_ovr_frm);
 * longer stride (user: 'looks like walking'): frames 0 / 4 the lowest 8 rows split at the middle of the legs, each half 3 px outwards, the frames between 1 px;
 * frames 2 and 6: lifted by 1 px; frames 0 and 4: a dust puff behind the REAR boot (the outermost leg pixels on the backward side, at its sole;
   2 px lower in the back view, where 'behind' is towards the camera; two shapes, the palette's light / middle grey).
Forward = screen left for the front view, right for the back view, swapped when the game mirrors the frame.  The game itself already turns the
walk frames twice as fast at the sprint step.  Only the picture changes (the game logic and the sprite table are untouched); without a sprint
step nothing is different (bit exact).  Not with HD tile packs (the pose would lose its replacement texture).  LANDSTALKER_SPRINTANIM=0 = off.
Needs patch_own.py (lk_o_sprites / lk_o_sprpiece) and patch_sprint.py before it.  Idempotent.  usage: patch_sprintanim.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_SPRINTANIM v1"
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    # 1. capture: while lk_sa_cap is set, sprite pieces go into the canvas instead of the sprite layer
    a = "    if (!idx || X < 0 || X >= 320 + 2 * lk_wide_e || X >= LK_OSW || Y < 0 || Y >= 224 || (lk_o_spr[Y][X] & 0x200)) continue;\n"
    k0 = s.find("static void lk_o_sprpiece(const uint8 *td,"); k1 = s.find(a, k0)
    assert k0 >= 0 and k1 > k0 and s.find("static void lk_o_vpiece(", k0) > k1, "vdp_render.c: lk_o_sprpiece layout changed (run patch_own.py first)"
    s = s[:k1] + "    if (lk_sa_cap) { int cx = X - lk_sa_ox, cy = Y - lk_sa_oy; if (idx && cx >= 0 && cy >= 0 && cx < LK_SA_N && cy < LK_SA_N && !(lk_sa_cv[cy][cx] & 0x200)) lk_sa_cv[cy][cx] = (uint16)(0x200 | (prio ? 0x100 : 0) | (pal * 16 + idx)); continue; }   /* LK_SPRINTANIM v1 */\n" + s[k1:]
    # the module goes in front of lk_o_sprpiece
    a = "static void lk_o_sprpiece(const uint8 *td, int tile0, int sx, int sy, int w, int h, int pal, int prio, int hf, int vf) {\n"
    assert s.count(a) == 1
    module = r'''/* ---- LK_SPRINTANIM v1: sprint pose of Nigel (tools/patch_sprintanim.py) ---- */
#define LK_SA_N 96
extern int lk_sprint_active(void);
static int lk_sa_cap, lk_sa_ox, lk_sa_oy, lk_sa_on = -1;
static uint16 lk_sa_cv[LK_SA_N][LK_SA_N], lk_sa_tmp[LK_SA_N][LK_SA_N];
static int lk_sa_grey(int pal, int want) {   /* palette index of line pal whose colour is the closest grey to `want` (dust) */
  int i, best = 1, bd = 1 << 30;
  for (i = 1; i < 16; i++) { PIXEL_OUT_T c = lk_o_palmode ? lk_o_pix[pal * 16 + i] : pixel[pal * 16 + i]; int r = (int)((c >> 16) & 255), g = (int)((c >> 8) & 255), b = (int)(c & 255), m = (r + g + b) / 3, d = (r - m) * (r - m) + (g - m) * (g - m) + (b - m) * (b - m) + 4 * (m - want) * (m - want); if (d < bd) { bd = d; best = i; } }
  return best;
}
static int lk_sa_index(int gi) {   /* the picture shown: own cadence of 3 game frames per walk picture (user: 'zu hektisch'; the game turns them every 2 frames at the sprint step), starting at the game's picture */
  static long st = -100, last = -100; static int i0; long f = platform_frame_number();
  if (f - last > 2) { st = f; i0 = gi; }
  last = f; return (i0 + (int)((f - st) / 3)) & 7;
}
static void lk_sa_apply(int fwd, int i, int ptop, int pal, int prio, int behind_down) {
  int x, y, bot = -1, top6, mid, x0 = LK_SA_N, x1 = -1, lift = (i == 2 || i == 6) ? 1 : 0;
  memcpy(lk_sa_tmp, lk_sa_cv, sizeof lk_sa_tmp);
  for (y = LK_SA_N - 1; y >= 0 && bot < 0; y--) for (x = 0; x < LK_SA_N; x++) if (lk_sa_cv[y][x]) { bot = y; break; }
  if (bot < 0) return;
  { int wn = (i == 0 || i == 4) ? 3 : (i & 1) ? 1 : 0, wr = wn == 3 ? 8 : 6;   /* longer stride (user: 'sieht wie Gehen aus'): the full-stride frames 0 / 4 3 px per side over the lowest 8 rows, the frames between 1 px over 6 rows */
  if (wn) {
    top6 = bot - (wr - 1);
    for (y = top6; y <= bot; y++) for (x = 0; x < LK_SA_N; x++) if (lk_sa_cv[y][x]) { if (x < x0) x0 = x; if (x > x1) x1 = x; }
    mid = (x0 + x1) / 2;
    for (y = top6; y <= bot; y++) { for (x = 0; x < LK_SA_N; x++) lk_sa_tmp[y][x] = 0;
      for (x = 0; x < LK_SA_N; x++) if (lk_sa_cv[y][x]) { int nx = x < mid ? x - wn : x + wn; if (nx >= 0 && nx < LK_SA_N) lk_sa_tmp[y][nx] = lk_sa_cv[y][x]; }
      if (y < top6 + 3) for (x = mid - wn; x < mid + wn; x++) if (x >= 0 && !lk_sa_tmp[y][x] && lk_sa_cv[y][mid]) lk_sa_tmp[y][x] = lk_sa_cv[y][mid]; }
  } }
  memset(lk_sa_cv, 0, sizeof lk_sa_cv);
  for (y = 0; y < LK_SA_N; y++) { int r = y - ptop, sh = r < 0 ? 0 : r < 18 ? 4 : r < 20 ? 3 : r < 23 ? 2 : r < 27 ? 1 : 0, dy = y - lift;   /* lean in bands, then the lift */
    if (dy < 0) continue;
    for (x = 0; x < LK_SA_N; x++) if (lk_sa_tmp[y][x]) { int nx = x + fwd * sh; if (nx >= 0 && nx < LK_SA_N) lk_sa_cv[dy][nx] = lk_sa_tmp[y][x]; } }
  if (i == 0 || i == 4) {   /* dust right behind the rear foot (big puff of sprint_mock.py, two shapes) */
    static const signed char d0[][2] = { {1,0},{2,0},{3,0},{4,0},{0,-1},{1,-1},{2,-1},{3,-1},{4,-1},{5,-1},{1,-2},{2,-2},{3,-2},{4,-2},{2,-3},{3,-3},{7,-1},{8,-1},{8,-2} };
    static const signed char d1[][2] = { {2,0},{3,0},{4,0},{5,0},{2,-1},{3,-1},{4,-1},{5,-1},{6,-1},{3,-2},{4,-2},{5,-2},{9,-1},{10,-2} };
    const signed char (*sh)[2] = i == 0 ? d0 : d1; int n = i == 0 ? (int)(sizeof d0 / sizeof d0[0]) : (int)(sizeof d1 / sizeof d1[0]), k, b2 = -1, xr = fwd < 0 ? -1 : LK_SA_N;
    int gl = lk_sa_grey(pal, 216), gm = lk_sa_grey(pal, 144);
    int bl = -1, m0 = LK_SA_N, m1 = -1, xm, by = -1;
    for (y = LK_SA_N - 1; y >= 0 && bl < 0; y--) for (x = 0; x < LK_SA_N; x++) if (lk_sa_cv[y][x]) { bl = y; break; }
    for (y = bl - 11; y <= bl; y++) if (y >= 0) for (x = 0; x < LK_SA_N; x++) if (lk_sa_cv[y][x]) { if (x < m0) m0 = x; if (x > m1) m1 = x; }   /* the legs: lowest 12 rows */
    xm = (m0 + m1) / 2;
    for (y = bl - 11; y <= bl; y++) if (y >= 0) for (x = 0; x < LK_SA_N; x++) if (lk_sa_cv[y][x] && (fwd < 0 ? x >= xm : x <= xm)) { if (fwd < 0 ? x > xr : x < xr) xr = x; }   /* the REAR boot = the outermost leg pixels on the backward side */
    for (y = bl; y >= bl - 11 && y >= 0 && by < 0; y--) for (x = (fwd < 0 ? xr - 4 : xr); x <= (fwd < 0 ? xr : xr + 4); x++) if (x >= 0 && x < LK_SA_N && lk_sa_cv[y][x]) { by = y; break; }   /* its sole */
    if (by < 0) by = bl;
    b2 = by + (behind_down ? 2 : 0);   /* running up (back view) 'behind' is towards the camera = lower on screen */
    for (k = 0; k < n; k++) { int xx = fwd < 0 ? xr + 2 + sh[k][0] : xr - 2 - sh[k][0], yy = b2 + sh[k][1];
      if (xx >= 0 && xx < LK_SA_N && yy >= 0 && yy < LK_SA_N && !lk_sa_cv[yy][xx]) lk_sa_cv[yy][xx] = (uint16)(0x200 | (prio ? 0x100 : 0) | (pal * 16 + (sh[k][1] < 0 ? gl : gm))); }
  }
  for (y = 0; y < LK_SA_N; y++) for (x = 0; x < LK_SA_N; x++) { uint16 v = lk_sa_cv[y][x]; int X = lk_sa_ox + x, Y = lk_sa_oy + y;   /* into the sprite layer with the same rules as lk_o_sprpiece */
    if (!v || X < 0 || X >= 320 + 2 * lk_wide_e || X >= LK_OSW || Y < 0 || Y >= 224 || (lk_o_spr[Y][X] & 0x200)) continue;
    lk_o_spr[Y][X] = (uint16)(v | ((lk_o_smk[Y] && lk_o_smk[Y] - 1 <= lk_o_cidx) ? 0x400 : 0)); lk_o_sprd[Y][X] = (int16_t)lk_o_curd; }
}
'''
    s = s.replace(a, module + a, 1)
    # 2. Nigel's piece loop: capture, then turn and draw
    a = "    for (pc = 0; pc < e->np; pc++) {\n      int xx; uint32 key = lk_o_pkey(e, pc, &xx);\n"
    assert s.count(a) == 1, "vdp_render.c: lk_o_sprites piece loop changed"
    pre = r'''    { int sa = 0;   /* LK_SPRINTANIM v1: Nigel in a walk frame while Sprint moved him: draw into the canvas */
      if (lk_sa_on < 0) { const char *q = getenv("LANDSTALKER_SPRINTANIM"); lk_sa_on = (q && *q) ? atoi(q) != 0 : 1; }
      if (draw && lk_sa_on && offs[k] == 0 && (e->anim == 8 || e->anim == 12) && !lk_o_hdwant() && lk_sprint_active()) sa = 1;
      if (sa) { lk_sa_cap = 1; lk_sa_ox = e->ax - 128 + lk_wide_e - LK_SA_N / 3; lk_sa_oy = e->ay - 128 - (2 * LK_SA_N) / 3; memset(lk_sa_cv, 0, sizeof lk_sa_cv); }
'''
    s = s.replace(a, pre + a, 1)
    # after the loop (the loop ends with 'cum += ...' and the closing brace before the outer loop's end)
    a = "      cum += e->pws[pc] * e->phs[pc];\n    }\n"
    assert s.count(a) == 1, "vdp_render.c: lk_o_sprites piece loop end changed"
    post = r'''      if (sa) { int q, ptop = 1 << 30, fwd = (e->anim == 12 ? -1 : 1) * (((e->ts >> 11) & 1) ? -1 : 1), gi = (e->frm / 4) & 7, si = lk_sa_index(gi); lk_o_ent_t *de = e;
        static lk_o_ent_t spe; static uint8 sptiles[0x4000];
        if (si != gi) {   /* the walk picture of the own cadence, loaded from the ROM like the VRAM pose search does; drawn into the canvas instead of the game's picture */
          lk_o_ovr_anim = e->anim; lk_o_ovr_frm = si * 4; lk_o_entload(src, offs[k], &spe, sptiles, 1, 0); lk_o_ovr_anim = -1;
          if (spe.vis && spe.np) { int c2 = 0; de = &spe; memset(lk_sa_cv, 0, sizeof lk_sa_cv);
            for (q = 0; q < de->np; q++) { int xx; (void)lk_o_pkey(de, q, &xx); lk_o_sprpiece(de->tiles, c2, de->ax + xx - 128, de->ay + de->pys[q] - 128, de->pws[q], de->phs[q], (de->ts >> 13) & 3, de->prio, (de->ts >> 11) & 1, (de->ts >> 12) & 1); c2 += de->pws[q] * de->phs[q]; } }
          else si = gi;
        }
        lk_sa_cap = 0;
        for (q = 0; q < de->np; q++) { int yy = de->ay + de->pys[q] - 128 - lk_sa_oy; if (yy < ptop) ptop = yy; }
        lk_sa_apply(fwd, si, ptop, (de->ts >> 13) & 3, de->prio, e->anim == 8); } }
'''
    s = s.replace(a, a + post, 1)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
