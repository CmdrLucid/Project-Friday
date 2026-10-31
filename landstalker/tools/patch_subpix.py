#!/usr/bin/env python3
"""Smooth sub-pixel scrolling (2026-10-30, docs/MODERN_IDEAS.md (A); user: the sprint should be 1.5 x, 2 x is too fast, but 1.5 x wobbled).
Why it wobbled (measured on rec_20261030_2020, step 3): in the 2:1 view the planes move by HALF the camera step vertically; the VDP's vertical scroll is
floor((cam0 + cam2) / 2) of the camera words $FF1200 / $FF1202, so with an odd camera sum the room (and every other figure: their screen rows round the same way)
is drawn half a line too low, with an even sum exactly; Nigel's own screen spot stays still.  At step 3 the sum changes by 3 every frame -> 1 / 2 line alternation.
What this does (picture only, the game state is untouched): while the camera sum changed by an ODD amount in this frame, the final 1x picture gets a quarter line
vertical blend on every 'world' pixel (planes, backdrop, the other figures): odd sum -> 3/4 own + 1/4 the line below (= sampled 1/4 line lower, lifting the half line
error), even sum -> 3/4 own + 1/4 the line above.  Both frames are equally soft, the mean offset is zero, and the room now moves 1.5 lines EVERY frame.  Not blended:
the Modern HUD's pixels (lk_mh_hit, user 2026-10-31 'das HUD wird beim Sprinten unscharf und zittert'), Nigel's pixels (marked while the own renderer draws entity offset 0), window pixels (HUD, text box), black margins, and any pixel something drew over the
compositor's output afterwards (overlays, menus: the pixel must equal what the compositor wrote, the HD path's rule).  Applied at the top of
platform_present_frame, so screenshots (LANDSTALKER_SHOT) show it too.  Inert with the HD picture (lk_hd_n) and outside the own map path.
Switch: Options > Quality of Life > Smooth Scrolling (id 43, last row; user 2026-10-30 'passt alles, einbauen'), default ON; ~/.landstalker_smooth, env LANDSTALKER_SMOOTH=0|1 wins.
While it is On the sprint step is 3 (1.5 x, constant: no 4 / 2 alternation; read every frame) unless LANDSTALKER_SPRINT_STEP is set; Off = sprint 2 x and no blend.
Without the Sprint button the game state never changes (the blend is picture only).
Needs patch_own.py, patch_sprint.py and patch_sprintanim.py before it.  Idempotent.  usage: patch_subpix.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_SUBPIX v3"   # v3 (2026-10-31): blend direction from the scroll steps

# ---- vdp_render.c (own renderer): mark Nigel's sprite pixels, remember the world pixels the compositor wrote, the frame's blend direction ----
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    a = "static uint16 lk_o_spr[224][LK_OSW];"
    assert s.count(a) == 1, "vdp_render.c: run patch_own.py first"
    s = s.replace(a, r'''/* ---- LK_SUBPIX v3: smooth sub-pixel scrolling (tools/patch_subpix.py) ---- */
static uint8 lk_ss_nig[224][LK_OSW]; static int lk_ss_cur;   /* 1 = the sprite pixel belongs to Nigel (entity offset 0) */
uint8_t lk_ss_w[224][LK_OSW]; uint32_t lk_ss_ref[224][LK_OSW]; long lk_ss_lgen[224], lk_ss_gen; int lk_ss_frac;   /* world pixel flag + the colour the compositor wrote; line stamps; blend: -1 = with the line above, +1 = below, 0 = none */
extern int lk_smooth_get(void);
static int lk_ss_vs;   /* test aid: the VDP's vertical scroll of plane A this frame */
static void lk_ss_update(int sum, int rm) {   /* once per own map frame, with the camera the picture is drawn from */
  static int psum, prm = -1, pvs, pdv; int d = sum - psum, dv = ((lk_ss_vs - pvs + 512) & 1023) - 512;
  lk_ss_gen++;
  /* v3 (2026-10-31, user: 'after a menu it jitters again'): the direction comes from the VDP's own vertical scroll, not from the camera parity.  At 1.5 x the scroll moves 1, 2, 1, 2 lines;
     the frame after the SMALLER step is half a line behind the even motion (behind = content too low while the scroll grows, too high while it shrinks), the frame after the larger one half a line ahead.  The parity rule
     (odd camera sum = too low) held only while the game rounds the scroll down: after a room reload (closing the Start menu, LoadRoomPath) the scroll can round the other way, and the old rule
     blended in the wrong direction = twice the jitter until the next reload (measured on rec_20261031_0756: vs - sum / 2 alternated before the menu visit, constant after it). */
  lk_ss_frac = (lk_smooth_get() && rm == prm && (d & 1) && d >= -16 && d <= 16 && !lk_hd_n && dv && pdv && (dv > 0) == (pdv > 0) && abs(dv - pdv) == 1) ? ((abs(dv) < abs(pdv)) == (dv > 0) ? 1 : -1) : 0;   /* behind the even motion: scrolling down (dv > 0) = vs too small = content too low (+1), scrolling up = content too high (-1) */
  pvs = lk_ss_vs; pdv = dv;
  { static int lg = -1; if (lg < 0) lg = getenv("LANDSTALKER_SS_LOG") != NULL; if (lg) { const uint8_t *lr = bus_get_ram(); int px = (int16_t)((lr[(0x5414) ^ 1] << 8) | lr[(0x5415) ^ 1]), py = (int16_t)((lr[(0x5416) ^ 1] << 8) | lr[(0x5417) ^ 1]); fprintf(stderr, "ss: gen %ld sum %d d %d room %d frac %d px %d py %d vs %d\n", lk_ss_gen, sum, d, rm, lk_ss_frac, px, py, lk_ss_vs); } }   /* test aid: one line per own map frame */
  psum = sum; prm = rm;
}
''' + a, 1)
    a = "lk_o_sprd[Y][X] = (int16_t)lk_o_curd;"
    assert s.count(a) == 3, "vdp_render.c: sprite pixel writers changed (patch_own / patch_sprintanim)"
    s = s.replace(a, a + " lk_ss_nig[Y][X] = (uint8)lk_ss_cur;")
    a = "  if (draw) { memset(lk_o_spr, 0, sizeof lk_o_spr);"
    assert s.count(a) == 1
    s = s.replace(a, "  if (draw) memset(lk_ss_nig, 0, sizeof lk_ss_nig);   /* LK_SUBPIX v3 */\n" + a, 1)
    a = "    if (draw && lk_o_exon) lk_o_extras_upto(sord[k]);\n    lk_o_nspr++;\n"
    assert s.count(a) == 1
    s = s.replace(a, "    lk_ss_cur = 0;\n" + a + "    lk_ss_cur = offs[k] == 0;   /* LK_SUBPIX v3: Nigel's pieces (also the sprint pose canvas) */\n", 1)
    a = "  }\n  return nk;\n}\nstatic void lk_o_build(void) {"
    assert s.count(a) == 1
    s = s.replace(a, "  }\n  lk_ss_cur = 0;\n  return nk;\n}\nstatic void lk_o_build(void) {", 1)
    a = "int upred = 1184 - (cam2 - cam0 + 160), vpred = ((cam0 + cam2) >> 1) - 104;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "        lk_ss_vs = (int16_t)vsA; lk_ss_update(cam0 + cam2, rm);   /* LK_SUBPIX v3 */\n", 1)
    a = "      if (lk_o_mode == 2) row[i] = (PIXEL_OUT_T)col;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "      if (lk_ss_frac) { lk_ss_w[line][i] = (uint8_t)(!black && src != 4 && !lk_mh_hit && !(src == 1 && sl >= 0 && sl < 224 && si >= 0 && si < LK_OSW && lk_ss_nig[sl][si])); lk_ss_ref[line][i] = (uint32_t)col; }   /* LK_SUBPIX v3 */\n", 1)
    a = "    lk_hd_dstamp[line] = lk_hd_gen;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "    if (lk_ss_frac) lk_ss_lgen[line] = lk_ss_gen;   /* LK_SUBPIX v3 */\n", 1)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)

# ---- platform_sdl.c: the switch and the blend of the final picture ----
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {\n"
    assert s.count(a) == 1
    module = r'''/* ---- LK_SUBPIX v3: smooth sub-pixel scrolling (tools/patch_subpix.py) ---- */
static int lk_smooth_o = -1;
int lk_smooth_get(void) { if (lk_smooth_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_SMOOTH"); char p[512]; FILE *f; int v = 1; snprintf(p, sizeof p, "%s/.landstalker_smooth", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 1; fclose(f); } if (e && *e) v = atoi(e); lk_smooth_o = v ? 1 : 0; } return lk_smooth_o; }   /* Options > Quality of Life > Smooth Scrolling (id 43), default On (user 2026-10-30: 'passt alles, einbauen'); ~/.landstalker_smooth, env LANDSTALKER_SMOOTH=0|1 wins */
void lk_smooth_set(int v) { const char *h = getenv("HOME"); char p[512]; FILE *f; lk_smooth_get(); lk_smooth_o = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_smooth", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_smooth_o); fclose(f); } }
extern uint8_t lk_ss_w[224][448]; extern uint32_t lk_ss_ref[224][448]; extern long lk_ss_lgen[224], lk_ss_gen; extern int lk_ss_frac;
static int lk_ss_wt = -1;   /* LANDSTALKER_SS_WEIGHT=1..8 (16ths); default 5 (2026-10-31: measured on screenshots, 4 left 1.29 / 1.73 lines per frame, 5 gives 1.48 / 1.56, 6 overshoots) */
static const uint8_t *lk_ss_apply(const uint8_t *fb) {
    if (lk_ss_wt < 0) { const char *e = getenv("LANDSTALKER_SS_WEIGHT"); lk_ss_wt = e && atoi(e) >= 1 && atoi(e) <= 8 ? atoi(e) : 5; }
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
            o[x] = (a & 0xFF000000u) | ((((a >> 16 & 255) * (16 - lk_ss_wt) + (b >> 16 & 255) * lk_ss_wt + 8) >> 4) << 16) | ((((a >> 8 & 255) * (16 - lk_ss_wt) + (b >> 8 & 255) * lk_ss_wt + 8) >> 4) << 8) | (((a & 255) * (16 - lk_ss_wt) + (b & 255) * lk_ss_wt + 8) >> 4);   /* weight of the neighbour line in 16ths (4 = the quarter blend) */
        }
    }
    { static int lg = -1; if (lg < 0) lg = getenv("LANDSTALKER_SS_LOG") != NULL; if (lg) { long nb = 0, nw = 0, nr = 0, nl = 0; for (y = 0; y < 224; y++) { if (lk_ss_lgen[y] == lk_ss_gen) nl++; for (x = 0; x < sw; x++) { if (buf[(size_t)y * sw + x] != src[(size_t)y * sw + x]) nb++; if (lk_ss_w[y][x]) { nw++; if (src[(size_t)y * sw + x] != lk_ss_ref[y][x]) nr++; } } } fprintf(stderr, "ssa: gen %ld blended %ld world %ld changed-after %ld lines %ld\n", lk_ss_gen, nb, nw, nr, nl); } }   /* test aid */
    return (const uint8_t *)buf;
}
'''
    s = s.replace(a, module + a + "    framebuffer = lk_ss_apply(framebuffer);   /* LK_SUBPIX v3 */\n", 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

# ---- func_table.c: sprint step 3 (1.5 x, constant) while smooth scrolling is On ----
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "    if (e && atoi(e) >= 2 && atoi(e) <= 8) lk_sprint_step = atoi(e);\n"
    assert s.count(a) == 1, "func_table.c: run patch_sprint.py first"
    s = s.replace(a, "    if (e && atoi(e) >= 2 && atoi(e) <= 8) lk_ss_envstep = 1;   /* LK_SUBPIX v3 */\n" + a, 1)
    a = "        { static int alt; int st = lk_sprint_step; if ((st & 1) && lk_sprint_alt) {"
    assert s.count(a) == 1
    s = s.replace(a, "        { static int alt; int sm = lk_smooth_get() && !lk_ss_envstep, st = sm ? 3 : lk_sprint_step; if ((st & 1) && lk_sprint_alt && !sm) {", 1)   # Smooth Scrolling On = 1.5 x, constant (no 4 / 2 alternation); read every frame, so the options row works at once
    a = "static long lk_sprint_frame = -10;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "extern int lk_smooth_get(void); static int lk_ss_envstep;   /* LK_SUBPIX v3: LANDSTALKER_SPRINT_STEP set = that step wins over Smooth Scrolling */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)

# ---- LK_SSHARP v1 (2026-10-31, MODERN_IDEAS (A2), user: 'scharfes weiches scrollen'): instead of the blend, the WORLD pixels are drawn shifted by
#      k OUTPUT pixels (k = a quarter game line at the output scale, nearest, nothing mixed) inside the display filters (CRT Pro / Curved, CRT, Scanlines, no filter).
#      The frames alternate +k / -k like the blend's +1/4 / -1/4 line, so the room moves 1.5 lines every frame and stays sharp; Nigel, figures drawn by Nigel's
#      pieces, HUD, text box, overlays are unshifted.  A world pixel is only shifted when the pixel it is shifted onto is a world pixel too (no smear of Nigel's edge).
#      Falls back to the blend where it cannot work: headless, picture lower than 2 x 224 (k < 1), HD / 3D room, CPU filter path not possible.
#      LANDSTALKER_SS_SHARP=0 = the blend (v3) again; LANDSTALKER_SS_SHIFT = the shift in 1/256 game lines (default 64 = a quarter line).
#      Test aid: LANDSTALKER_OSHOT=f1,f2,.. (+ LANDSTALKER_OSHOT_SIZE=1280x800, default 1280x800) writes the FILTERED output picture of those frames, also headless
#      (dir LANDSTALKER_SHOT_DIR, oshot_FRAME.png): the sharp shift exists only there.
SHARP = "LK_SSHARP v1"
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if SHARP not in s:
    assert "LK_SUBPIX v3" in s
    # globals + helpers before the CPU filters
    a = "/* ---- CRT / scanline filter (CPU) ---- */\n"
    assert s.count(a) == 1, "platform_sdl.c: run patch_display.py first"
    s = s.replace(a, r'''/* ---- LK_SSHARP v1: sharp smooth scrolling (tools/patch_subpix.py) ---- */
static int lk_ssh_pend;   /* set by lk_ss_apply for the frame being presented: +1 / -1 = shift the world pixels down / up by lk_ssh_k output rows (sample from the lower / upper row), 0 = none */
static int lk_ssh_d, lk_ssh_k;   /* in use while lk_disp_present runs the CPU filters (0 everywhere else, e.g. the HD path) */
static int lk_ssh_amt = -1;      /* LANDSTALKER_SS_SHIFT, 1/256 game lines, default 64 */
static uint8_t lk_ssh_ok[224][448];   /* 1 = world pixel nobody drew over (filled by lk_ss_apply) */
static uint16_t lk_ssh_cx[LK_MAXDIM], lk_ssh_ry[LK_MAXDIM]; static int lk_ssh_tw, lk_ssh_th, lk_ssh_ts;   /* output column -> source column, output row -> source row (nearest) */
static int lk_ssh_amount(void) { if (lk_ssh_amt < 0) { const char *e = getenv("LANDSTALKER_SS_SHIFT"); lk_ssh_amt = e && atoi(e) >= 1 && atoi(e) <= 255 ? atoi(e) : 64; } return lk_ssh_amt; }
static int lk_ssh_kfor(int dh) { int k = (int)((double)lk_ssh_amount() * dh / (224.0 * 256.0) + 0.5); return k; }   /* the shift in output rows for a picture dh rows high */
static int lk_ssh_setup(int dw, int dh, int sw) {   /* main thread, before the filter bands run */
    if (dw > LK_MAXDIM || dh > LK_MAXDIM || sw > 448) return 0;
    if (dw != lk_ssh_tw || dh != lk_ssh_th || sw != lk_ssh_ts) {
        for (int x = 0; x < dw; x++) { int c = (int)(((int64_t)(2 * x + 1) * sw) / (2 * dw)); lk_ssh_cx[x] = (uint16_t)(c > sw - 1 ? sw - 1 : c); }
        for (int y = 0; y < dh; y++) { int r = (int)(((int64_t)(2 * y + 1) * 224) / (2 * dh)); lk_ssh_ry[y] = (uint16_t)(r > 223 ? 223 : r); }
        lk_ssh_tw = dw; lk_ssh_th = dh; lk_ssh_ts = sw;
    }
    lk_ssh_k = lk_ssh_kfor(dh); return lk_ssh_k >= 1;
}
static inline int lk_ssh_y2(int y, int dh) { int y2 = y + lk_ssh_d * lk_ssh_k; return y2 < 0 ? 0 : y2 > dh - 1 ? dh - 1 : y2; }   /* the output row whose sampling a shifted world pixel of row y uses */
''' + a, 1)

    # SCANLINES / CRT
    a = """        uint32_t *o = dst + (size_t)y * dw;
        int ph = 0;
        for (int x = 0; x < dw; x++) {
            uint32_t a = row[lk_tx0[x]], b = row[lk_tx1[x]], wx = lk_twx[x], iw = 256 - wx;"""
    assert s.count(a) == 1
    s = s.replace(a, """        uint32_t *o = dst + (size_t)y * dw;
        int ph = 0;
        if (lk_ssh_d) {   /* LK_SSHARP v1: world pixels take row / scanline weight of the output row y2 */
            const int y2 = lk_ssh_y2(y, lk_tab_dh); const uint32_t *row2 = src + (size_t)lk_trow[y2] * sw; uint32_t wk2[3][3], wy2 = lk_twy[y2];
            const uint8_t *mn = lk_ssh_ok[lk_ssh_ry[y]], *ms = lk_ssh_ok[lk_ssh_ry[y2]];
            for (int i = 0; i < 3; i++) for (int c = 0; c < 3; c++) wk2[i][c] = wy2 * lk_tmask[i][c] >> 8;
            for (int x = 0; x < dw; x++) {
                const int cc = lk_ssh_cx[x], sh = mn[cc] & ms[cc]; const uint32_t *rr = sh ? row2 : row;
                uint32_t a = rr[lk_tx0[x]], b = rr[lk_tx1[x]], wx = lk_twx[x], iw = 256 - wx;
                uint32_t rb = (((a & 0x00FF00FFu) * iw + (b & 0x00FF00FFu) * wx) >> 8) & 0x00FF00FFu;
                uint32_t g = (((a >> 8) & 255) * iw + ((b >> 8) & 255) * wx) >> 8;
                const uint32_t *k = sh ? wk2[ph] : wk[ph]; if (++ph == 3) ph = 0;
                uint32_t r = (rb >> 16) * k[0] >> 8, gg = g * k[1] >> 8, bl = (rb & 255) * k[2] >> 8;
                r = r > 255 ? 255 : r; gg = gg > 255 ? 255 : gg; bl = bl > 255 ? 255 : bl;
                o[x] = 0xFF000000u | (r << 16) | (gg << 8) | bl;
            }
            continue;
        }
""" + a[a.index("        for (int x"):], 1)

    # CRT PRO flat rows
    a = """            const uint8_t *enc = lk_f2_enc; int ph = 0;
            for (int x = 0; x < dw; x++, a += 4, b += 4) {"""
    assert s.count(a) == 1
    s = s.replace(a, """            const uint8_t *enc = lk_f2_enc; int ph = 0;
            if (lk_ssh_d) {   /* LK_SSHARP v1: world pixels take the source rows / beam weights of the output row y2 */
                const int y2 = lk_ssh_y2(y, lk_f2_dh), sy2 = lk_f2_my[(size_t)y2 * dw], q0 = sy2 >> 8, qf = sy2 & 255, q1 = q0 + 1 < LK_SRC_H ? q0 + 1 : q0;
                const uint16_t *wtA2 = lk_f2_wt[qf >> 2], *wtB2 = lk_f2_wt[(255 - qf) >> 2], *a2 = lk_f2_plane + (size_t)q0 * dw * 4, *b2 = lk_f2_plane + (size_t)q1 * dw * 4;
                const uint8_t *mn = lk_ssh_ok[lk_ssh_ry[y]], *ms = lk_ssh_ok[lk_ssh_ry[y2]];
                for (int x = 0; x < dw; x++) {
                    const int cc = lk_ssh_cx[x], sh = mn[cc] & ms[cc];
                    const uint16_t *pa = (sh ? a2 : a) + (size_t)x * 4, *pb = (sh ? b2 : b) + (size_t)x * 4;
                    const uint32_t wa = (sh ? wtA2 : wtA)[pa[3]], wb = (sh ? wtB2 : wtB)[pb[3]]; const uint16_t *m = lk_f2_mask[ph]; if (++ph == 3) ph = 0;
                    uint32_t v0 = ((pa[0] * wa + pb[0] * wb) >> 8) * m[0] >> 8, v1 = ((pa[1] * wa + pb[1] * wb) >> 8) * m[1] >> 8, v2 = ((pa[2] * wa + pb[2] * wb) >> 8) * m[2] >> 8;
                    o[x] = 0xFF000000u | ((uint32_t)enc[v0 > 4095 ? 4095 : v0] << 16) | ((uint32_t)enc[v1 > 4095 ? 4095 : v1] << 8) | enc[v2 > 4095 ? 4095 : v2];
                }
                continue;
            }
            for (int x = 0; x < dw; x++, a += 4, b += 4) {""", 1)

    # CRT PRO general path (Curved)
    a = "            const int sy = lk_f2_my[base + x], r0 = sy >> 8, fr = sy & 255, r1 = r0 + 1 < LK_SRC_H ? r0 + 1 : r0, mx = lk_f2_mx[base + x];"
    assert s.count(a) == 1
    s = s.replace(a, "            const int ssh2 = lk_ssh_d ? lk_ssh_y2(y, lk_f2_dh) : y, ssw = lk_ssh_d && (lk_ssh_ok[lk_ssh_ry[y]][lk_ssh_cx[x]] & lk_ssh_ok[lk_ssh_ry[ssh2]][lk_ssh_cx[x]]);   /* LK_SSHARP v1 */\n"
                      "            const int sy = lk_f2_my[(ssw ? (size_t)ssh2 * dw : base) + x], r0 = sy >> 8, fr = sy & 255, r1 = r0 + 1 < LK_SRC_H ? r0 + 1 : r0, mx = lk_f2_mx[base + x];", 1)

    # no filter: sharp-bilinear
    a = """        const uint32_t *ra = src + (size_t)lk_sby0[y] * sw, *rb = src + (size_t)lk_sby1[y] * sw;
        uint32_t wy = lk_sbwy[y]; uint32_t *o = dst + (size_t)y * dw;
"""
    assert s.count(a) == 1
    s = s.replace(a, a + """        if (lk_ssh_d) {   /* LK_SSHARP v1 */
            const int y2 = lk_ssh_y2(y, lk_sbt_dh); const uint32_t *ra2 = src + (size_t)lk_sby0[y2] * sw, *rb2 = src + (size_t)lk_sby1[y2] * sw; const uint32_t wy2 = lk_sbwy[y2];
            const uint8_t *mn = lk_ssh_ok[lk_ssh_ry[y]], *ms = lk_ssh_ok[lk_ssh_ry[y2]];
            for (int x = 0; x < dw; x++) {
                const int cc = lk_ssh_cx[x], sh = mn[cc] & ms[cc]; const uint32_t *pa = sh ? ra2 : ra, *pb = sh ? rb2 : rb, w2 = sh ? wy2 : wy;
                uint32_t wx = lk_sbwx[x]; int xa = lk_sbx0[x], xb = lk_sbx1[x];
                uint32_t top = lk_sb_mix(pa[xa], pa[xb], wx);
                uint32_t v = w2 ? lk_sb_mix(top, lk_sb_mix(pb[xa], pb[xb], wx), w2) : top;
                o[x] = 0xFF000000u | v;
            }
            continue;
        }
""", 1)

    # lk_disp_present: switch the shift on for the CPU filter path only, force the CPU path while it is on
    a = "    const int lk_sb_cpu = lk_sb_env && !((r.w % sw == 0) && (r.h % LK_SRC_H == 0));"
    assert s.count(a) == 1
    s = s.replace(a, "    lk_ssh_d = 0; if (lk_ssh_pend && lk_ssh_setup(r.w, r.h, sw)) lk_ssh_d = lk_ssh_pend;   /* LK_SSHARP v1 */\n"
                      "    const int lk_sb_cpu = (lk_sb_env && !((r.w % sw == 0) && (r.h % LK_SRC_H == 0))) || lk_ssh_d;   /* (LK_SSHARP: the shift needs the CPU path, at an exact scale it is plain nearest) */", 1)
    a = "    lk_osd_draw(ow, oh);\n    lk_coords_draw(oh);\n    SDL_RenderPresent(s_renderer);\n}\n"
    assert s.count(a) == 1
    s = s.replace(a, "    lk_ssh_d = 0;   /* LK_SSHARP v1 */\n" + a, 1)

    # lk_ss_apply: sharp instead of blend when the output path can do it
    a = "    if (!d || done == lk_ss_gen || sw > 448) return fb;\n"
    assert s.count(a) == 1
    s = s.replace(a, """    lk_ssh_pend = 0;
    if (d && sw <= 448 && lk_ssh_can(sw)) {   /* LK_SSHARP v1: no blend, the display filters shift the world pixels */
        static long mdone = -1; extern int lk_wide_e;
        if (mdone != lk_ss_gen) { mdone = lk_ss_gen; for (y = 0; y < 224; y++) { const uint32_t *r0 = src + (size_t)y * sw; uint8_t *m = lk_ssh_ok[y]; if (lk_ss_lgen[y] != lk_ss_gen) { memset(m, 0, 448); continue; } for (x = 0; x < sw; x++) m[x] = (uint8_t)(lk_ss_w[y][x] && r0[x] == lk_ss_ref[y][x]); } }
        lk_ssh_pend = d; return fb;
    }
""" + a, 1)
    a = "static const uint8_t *lk_ss_apply(const uint8_t *fb) {\n"
    assert s.count(a) == 1
    s = s.replace(a, r'''static int lk_ssh_outsize(int *ow, int *oh) {   /* LK_SSHARP v1: the output size the display path will use (headless: only for LANDSTALKER_OSHOT) */
    if (s_renderer) { SDL_GetRendererOutputSize(s_renderer, ow, oh); return *ow > 0 && *oh > 0; }
    { const char *q = getenv("LANDSTALKER_OSHOT"), *z = getenv("LANDSTALKER_OSHOT_SIZE"); if (!q || !*q) return 0; *ow = 1280; *oh = 800; if (z) sscanf(z, "%dx%d", ow, oh); return 1; }
}
static int lk_ssh_can(int sw) {   /* LK_SSHARP v1: will lk_disp_present run the CPU filters on the 1x picture? */
    static int env = -1; int ow = 0, oh = 0; lk_rect r; extern int lk_r3d_on(void), lk_hd_active(void);
    if (env < 0) { const char *e = getenv("LANDSTALKER_SS_SHARP"); env = !(e && *e == '0'); }
    if (!env || !lk_ssh_outsize(&ow, &oh)) return 0;
    if (!lk_disp_loaded) lk_disp_load();
    if (lk_r3d_on() || lk_hd_active()) return 0;
    lk_calc_rect(lk_scale_mode, ow, oh, sw, &r);
    return r.w <= LK_MAXDIM && r.h <= LK_MAXDIM && r.w >= LK_SRC_W && r.h >= LK_SRC_H && lk_ssh_kfor(r.h) >= 1;
}
''' + a, 1)

    # test aid LANDSTALKER_OSHOT: the filtered output picture (same CPU calls as lk_disp_present), also headless
    a = "    lk_shot_frame(framebuffer, s_frame_no);\n"
    assert s.count(a) == 1
    s = s.replace(a, a + r'''    { static int on = -1; static const char *ol; if (on < 0) { ol = getenv("LANDSTALKER_OSHOT"); on = ol && *ol; }   /* LK_SSHARP v1 test aid */
      if (on && lk_shot_wanted(ol, s_frame_no)) {
        extern int lk_wide_e; const int sw = LK_SRC_W + 2 * lk_wide_e; int ow = 1280, oh = 800; lk_rect r; const uint8_t *fb = framebuffer; static uint32_t *ob; static size_t oc;
        lk_ssh_outsize(&ow, &oh); if (!lk_disp_loaded) lk_disp_load(); if (!lk_dd_loaded) lk_dd_load();
        { const char *fx = getenv("LANDSTALKER_OSHOT_FX"); if (fx && *fx) lk_fx_mode = atoi(fx) % LK_FX_N; }
        if (lk_dd_mode) { lk_dd_par = lk_dd_par_run; if (lk_dd_cap < sw * LK_SRC_H) { free(lk_dd_buf); lk_dd_buf = (uint32_t *)malloc((size_t)sw * LK_SRC_H * 4); lk_dd_cap = lk_dd_buf ? sw * LK_SRC_H : 0; } if (lk_dd_buf) { if (lk_dd_mode == 3) lk_dedither_blend((const uint32_t *)fb, lk_dd_buf, sw); else if (lk_dd_mode == 2) lk_dedither_strong((const uint32_t *)fb, lk_dd_buf, sw); else lk_dedither((const uint32_t *)fb, lk_dd_buf, sw); fb = (const uint8_t *)lk_dd_buf; } }
        lk_calc_rect(lk_scale_mode, ow, oh, sw, &r);
        if ((size_t)r.w * r.h > oc) { free(ob); oc = (size_t)r.w * r.h; ob = (uint32_t *)malloc(oc * 4); }
        lk_ssh_d = 0; if (lk_ssh_pend && lk_ssh_setup(r.w, r.h, sw)) lk_ssh_d = lk_ssh_pend;
        if (ob) { const uint64_t tq0 = SDL_GetPerformanceCounter(); double tms;
            if (lk_fx_mode >= LK_FX_PRO) { lk_f2_prepare(r.w, r.h, lk_fx_mode, sw); if (lk_f2_plane) { lk_fx_render_mt((const uint32_t *)fb, ob, r.w, LK_SRC_H, sw, 2); lk_fx_render_mt((const uint32_t *)fb, ob, r.w, r.h, sw, 3); } }
            else if (lk_fx_mode != LK_FX_OFF) { lk_fx_prepare(r.w, r.h, lk_fx_mode, sw); lk_fx_render_mt((const uint32_t *)fb, ob, r.w, r.h, sw, 0); }
            else { lk_sb_prepare(r.w, r.h, sw); lk_fx_render_mt((const uint32_t *)fb, ob, r.w, r.h, sw, 1); }
            tms = (double)(SDL_GetPerformanceCounter() - tq0) * 1000.0 / (double)SDL_GetPerformanceFrequency();
            { const char *dir = getenv("LANDSTALKER_SHOT_DIR"); char path[700]; snprintf(path, sizeof path, "%s/oshot_%06ld.png", dir && *dir ? dir : "shots", s_frame_no); printf("oshot: %s %s (%dx%d fx %d shift %d x %d, filter %.2f ms)\n", lk_shot_png(path, ob, r.w, r.h, 1) ? "wrote" : "FAILED", path, r.w, r.h, lk_fx_mode, lk_ssh_d, lk_ssh_k, tms); }
        }
        lk_ssh_d = 0;
      } }
''', 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", SHARP)
