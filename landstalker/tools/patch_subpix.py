#!/usr/bin/env python3
"""Smooth sub-pixel scrolling (2026-10-30, docs/MODERN_IDEAS.md (A); user: the sprint should be 1.5 x, 2 x is too fast, but 1.5 x wobbled).
Why it wobbled (measured on rec_20261030_2020, step 3): in the 2:1 view the planes move by HALF the camera step vertically; the VDP's vertical scroll is
floor((cam0 + cam2) / 2) of the camera words $FF1200 / $FF1202, so with an odd camera sum the room (and every other figure: their screen rows round the same way)
is drawn half a line too low, with an even sum exactly; Nigel's own screen spot stays still.  At step 3 the sum changes by 3 every frame -> 1 / 2 line alternation.
What this does (picture only, the game state is untouched): while the camera sum changed by an ODD amount in this frame, the final 1x picture gets a quarter line
vertical blend on every 'world' pixel (planes, backdrop, the other figures): odd sum -> 3/4 own + 1/4 the line below (= sampled 1/4 line lower, lifting the half line
error), even sum -> 3/4 own + 1/4 the line above.  Both frames are equally soft, the mean offset is zero, and the room now moves 1.5 lines EVERY frame.  Not blended:
Nigel's pixels (marked while the own renderer draws entity offset 0), window pixels (HUD, text box), black margins, and any pixel something drew over the
compositor's output afterwards (overlays, menus: the pixel must equal what the compositor wrote, the HD path's rule).  Applied at the top of
platform_present_frame, so screenshots (LANDSTALKER_SHOT) show it too.  Inert with the HD picture (lk_hd_n) and outside the own map path.
Switch: Options > Quality of Life > Smooth Scrolling (id 43, last row; user 2026-10-30 'passt alles, einbauen'), default ON; ~/.landstalker_smooth, env LANDSTALKER_SMOOTH=0|1 wins.
While it is On the sprint step is 3 (1.5 x, constant: no 4 / 2 alternation; read every frame) unless LANDSTALKER_SPRINT_STEP is set; Off = sprint 2 x and no blend.
Without the Sprint button the game state never changes (the blend is picture only).
Needs patch_own.py, patch_sprint.py and patch_sprintanim.py before it.  Idempotent.  usage: patch_subpix.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_SUBPIX v2"

# ---- vdp_render.c (own renderer): mark Nigel's sprite pixels, remember the world pixels the compositor wrote, the frame's blend direction ----
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    a = "static uint16 lk_o_spr[224][LK_OSW];"
    assert s.count(a) == 1, "vdp_render.c: run patch_own.py first"
    s = s.replace(a, r'''/* ---- LK_SUBPIX v2: smooth sub-pixel scrolling (tools/patch_subpix.py) ---- */
static uint8 lk_ss_nig[224][LK_OSW]; static int lk_ss_cur;   /* 1 = the sprite pixel belongs to Nigel (entity offset 0) */
uint8_t lk_ss_w[224][LK_OSW]; uint32_t lk_ss_ref[224][LK_OSW]; long lk_ss_lgen[224], lk_ss_gen; int lk_ss_frac;   /* world pixel flag + the colour the compositor wrote; line stamps; blend: -1 = with the line above, +1 = below, 0 = none */
extern int lk_smooth_get(void);
static void lk_ss_update(int sum, int rm) {   /* once per own map frame, with the camera the picture is drawn from */
  static int psum, prm = -1; int d = sum - psum;
  lk_ss_gen++;
  lk_ss_frac = (lk_smooth_get() && rm == prm && (d & 1) && d >= -16 && d <= 16 && !lk_hd_n) ? ((sum & 1) ? 1 : -1) : 0;
  { static int lg = -1; if (lg < 0) lg = getenv("LANDSTALKER_SS_LOG") != NULL; if (lg) fprintf(stderr, "ss: gen %ld sum %d d %d room %d frac %d\n", lk_ss_gen, sum, d, rm, lk_ss_frac); }   /* test aid: one line per own map frame */
  psum = sum; prm = rm;
}
''' + a, 1)
    a = "lk_o_sprd[Y][X] = (int16_t)lk_o_curd;"
    assert s.count(a) == 3, "vdp_render.c: sprite pixel writers changed (patch_own / patch_sprintanim)"
    s = s.replace(a, a + " lk_ss_nig[Y][X] = (uint8)lk_ss_cur;")
    a = "  if (draw) { memset(lk_o_spr, 0, sizeof lk_o_spr);"
    assert s.count(a) == 1
    s = s.replace(a, "  if (draw) memset(lk_ss_nig, 0, sizeof lk_ss_nig);   /* LK_SUBPIX v2 */\n" + a, 1)
    a = "    if (draw && lk_o_exon) lk_o_extras_upto(sord[k]);\n    lk_o_nspr++;\n"
    assert s.count(a) == 1
    s = s.replace(a, "    lk_ss_cur = 0;\n" + a + "    lk_ss_cur = offs[k] == 0;   /* LK_SUBPIX v2: Nigel's pieces (also the sprint pose canvas) */\n", 1)
    a = "  }\n  return nk;\n}\nstatic void lk_o_build(void) {"
    assert s.count(a) == 1
    s = s.replace(a, "  }\n  lk_ss_cur = 0;\n  return nk;\n}\nstatic void lk_o_build(void) {", 1)
    a = "int upred = 1184 - (cam2 - cam0 + 160), vpred = ((cam0 + cam2) >> 1) - 104;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "        lk_ss_update(cam0 + cam2, rm);   /* LK_SUBPIX v2 */\n", 1)
    a = "      if (lk_o_mode == 2) row[i] = (PIXEL_OUT_T)col;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "      if (lk_ss_frac) { lk_ss_w[line][i] = (uint8_t)(!black && src != 4 && !(src == 1 && sl >= 0 && sl < 224 && si >= 0 && si < LK_OSW && lk_ss_nig[sl][si])); lk_ss_ref[line][i] = (uint32_t)col; }   /* LK_SUBPIX v2 */\n", 1)
    a = "    lk_hd_dstamp[line] = lk_hd_gen;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "    if (lk_ss_frac) lk_ss_lgen[line] = lk_ss_gen;   /* LK_SUBPIX v2 */\n", 1)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)

# ---- platform_sdl.c: the switch and the blend of the final picture ----
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {\n"
    assert s.count(a) == 1
    module = r'''/* ---- LK_SUBPIX v2: smooth sub-pixel scrolling (tools/patch_subpix.py) ---- */
static int lk_smooth_o = -1;
int lk_smooth_get(void) { if (lk_smooth_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_SMOOTH"); char p[512]; FILE *f; int v = 1; snprintf(p, sizeof p, "%s/.landstalker_smooth", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 1; fclose(f); } if (e && *e) v = atoi(e); lk_smooth_o = v ? 1 : 0; } return lk_smooth_o; }   /* Options > Quality of Life > Smooth Scrolling (id 43), default On (user 2026-10-30: 'passt alles, einbauen'); ~/.landstalker_smooth, env LANDSTALKER_SMOOTH=0|1 wins */
void lk_smooth_set(int v) { const char *h = getenv("HOME"); char p[512]; FILE *f; lk_smooth_get(); lk_smooth_o = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_smooth", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_smooth_o); fclose(f); } }
extern uint8_t lk_ss_w[224][448]; extern uint32_t lk_ss_ref[224][448]; extern long lk_ss_lgen[224], lk_ss_gen; extern int lk_ss_frac;
static const uint8_t *lk_ss_apply(const uint8_t *fb) {
    static uint32_t *buf; static int cap; static long done = -1; extern int lk_wide_e; const int sw = 320 + 2 * lk_wide_e; const uint32_t *src = (const uint32_t *)fb; int y, x, d = lk_ss_frac;
    if (!d || done == lk_ss_gen || sw > 448) return fb;
    done = lk_ss_gen;
    if (cap < sw * 224) { free(buf); buf = (uint32_t *)malloc((size_t)sw * 224 * 4); cap = buf ? sw * 224 : 0; }
    if (!buf) return fb;
    memcpy(buf, src, (size_t)sw * 224 * 4);
    for (y = 0; y < 224; y++) {
        int n = y + d; const uint32_t *r0 = src + (size_t)y * sw, *r1; uint32_t *o = buf + (size_t)y * sw;
        if (n < 0 || n >= 224 || lk_ss_lgen[y] != lk_ss_gen || lk_ss_lgen[n] != lk_ss_gen) continue;
        r1 = src + (size_t)n * sw;
        for (x = 0; x < sw; x++) {
            uint32_t a = r0[x], b = r1[x];
            if (a == b || !lk_ss_w[y][x] || !lk_ss_w[n][x] || a != lk_ss_ref[y][x] || b != lk_ss_ref[n][x]) continue;   /* only world pixels nobody drew over, both lines */
            o[x] = (a & 0xFF000000u) | ((((a >> 16 & 255) * 3 + (b >> 16 & 255) + 2) >> 2) << 16) | ((((a >> 8 & 255) * 3 + (b >> 8 & 255) + 2) >> 2) << 8) | (((a & 255) * 3 + (b & 255) + 2) >> 2);
        }
    }
    { static int lg = -1; if (lg < 0) lg = getenv("LANDSTALKER_SS_LOG") != NULL; if (lg) { long nb = 0, nw = 0, nr = 0, nl = 0; for (y = 0; y < 224; y++) { if (lk_ss_lgen[y] == lk_ss_gen) nl++; for (x = 0; x < sw; x++) { if (buf[(size_t)y * sw + x] != src[(size_t)y * sw + x]) nb++; if (lk_ss_w[y][x]) { nw++; if (src[(size_t)y * sw + x] != lk_ss_ref[y][x]) nr++; } } } fprintf(stderr, "ssa: gen %ld blended %ld world %ld changed-after %ld lines %ld\n", lk_ss_gen, nb, nw, nr, nl); } }   /* test aid */
    return (const uint8_t *)buf;
}
'''
    s = s.replace(a, module + a + "    framebuffer = lk_ss_apply(framebuffer);   /* LK_SUBPIX v2 */\n", 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

# ---- func_table.c: sprint step 3 (1.5 x, constant) while smooth scrolling is On ----
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "    if (e && atoi(e) >= 2 && atoi(e) <= 8) lk_sprint_step = atoi(e);\n"
    assert s.count(a) == 1, "func_table.c: run patch_sprint.py first"
    s = s.replace(a, "    if (e && atoi(e) >= 2 && atoi(e) <= 8) lk_ss_envstep = 1;   /* LK_SUBPIX v2 */\n" + a, 1)
    a = "        { static int alt; int st = lk_sprint_step; if ((st & 1) && lk_sprint_alt) {"
    assert s.count(a) == 1
    s = s.replace(a, "        { static int alt; int sm = lk_smooth_get() && !lk_ss_envstep, st = sm ? 3 : lk_sprint_step; if ((st & 1) && lk_sprint_alt && !sm) {", 1)   # Smooth Scrolling On = 1.5 x, constant (no 4 / 2 alternation); read every frame, so the options row works at once
    a = "static long lk_sprint_frame = -10;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "extern int lk_smooth_get(void); static int lk_ss_envstep;   /* LK_SUBPIX v2: LANDSTALKER_SPRINT_STEP set = that step wins over Smooth Scrolling */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
