#!/usr/bin/env python3
"""HD graphics, display side (2026-10-22, optional, Off by default): the own renderer's screen compositor (tools/patch_own.py) keeps, for every line it composed, an n times
enlarged copy (lk_hd_rows: replacement textures of the tile pack at n x n pixels per game pixel, everything else repeated) and the 1x pixels it produced (lk_hd_ref).
This patch builds the HD picture from the final 1x frame: where the final pixel equals the compositor's pixel (no overlay such as the options menu, Item Info or the quick items drew
over it) the HD block is used, anywhere else the final pixel is repeated n x n.  Lines the compositor did not do (the map) are repeated too, so the picture never changes character.
Present: with HD on, the HD picture (sw * n x 224 * n) is drawn into the usual destination rectangle: filter Off = linear scaling, Scanlines / CRT / CRT Pro / CRT Curved = the same
filters run on the HD picture (display_core.c `lk_hdn`: scanline period, beam and mask stay per GAME line, the horizontal sampling uses the finer columns); de-dither is 1x only and is skipped with HD on.  Screenshots: LANDSTALKER_HD_SHOT=<frame>,.. writes hdshot_<frame>_w<width>.png into LANDSTALKER_SHOT_DIR.  Everything is inert unless HD graphics is On
(`~/.landstalker_hd` = 1 or LANDSTALKER_HD=1).  Needs patch_shot.py and patch_own.py before it.  Idempotent.  usage: patch_hd.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_HD v2"
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched:", VER); sys.exit(0)
a = "/* draw the frame: returns after SDL_RenderPresent */\nstatic void lk_disp_present(const uint8_t *framebuffer) {"
assert s.count(a) == 1, "platform_sdl.c: lk_disp_present layout changed"
module = r'''/* ---- LK_HD v1: HD picture from the compositor's n x n blocks (tools/patch_hd.py) ---- */
extern int lk_hd_n; extern uint32_t *lk_hd_rows, *lk_hd_ref; extern long lk_hd_stamp[224], lk_hd_gen; extern int lk_wide_e; extern int lk_quick_hdcol(int x); extern int lk_shadow_hdflags(int x, int y), lk_shadow_hdalpha(int x, int y, int sx, int sy, int n);
static uint32_t lk_hd_dark(uint32_t c) { return ((c >> 1) & 0x007F7F7Fu) + ((c >> 4) & 0x000F0F0Fu) + (c & 0xFF000000u); }   /* the Shadow option's 1x darkening (patch_shadow.py) */
static uint32_t *lk_hd_img; static int lk_hd_iw, lk_hd_ih; static SDL_Texture *lk_hd_tex; static int lk_hd_tw, lk_hd_th;
static SDL_Texture *lk_hd_ftex; static int lk_hd_fw, lk_hd_fh; static uint32_t *lk_hd_fbuf;   /* filtered HD picture (destination size) */

extern int lk_hd_active(void); extern int16_t lk_hd_depth[]; extern long lk_hd_dstamp[224]; extern int lk_hd_focus; extern int lk_dof_get(void);
/* depth blur (HD only): blur radius grows with the distance of a pixel's ground point from Nigel's (screen rows, lk_hd_depth / lk_hd_focus).  A 1x copy of the picture (mean of each N x N block) gets a summed-area table; every game pixel then takes
   a box average of its own radius (two box sizes mixed for the fraction, O(1) per pixel); the HD picture is mixed with a bilinear upsample of that.  All passes run on up to 4 threads (bands of rows). */
static struct { uint32_t *img; int W, H, N, sw, nt, C, ws, hs; } lk_dd_c;
static uint16_t *lk_dd_r16, *lk_dd_rs; static uint32_t *lk_dd_lv0, *lk_dd_bb; static int32_t *lk_dd_ii[3]; static int lk_dd_recip[100]; static int lk_dd_rm; static int *lk_dd_xi, *lk_dd_xf, *lk_dd_yi, *lk_dd_yf;
typedef struct { int phase, y0, y1; } lk_dd2_job;
/* the blurred copy ('small') has one cell per C x C output pixels: C = N for the HD picture (= the 1x resolution), 2 for the 1x picture (half resolution: the blurred part needs no more) */
static int lk_dd2_run(void *pv) {
    lk_dd2_job *jb = (lk_dd2_job *)pv; int sw = lk_dd_c.sw, N = lk_dd_c.N, W = lk_dd_c.W, H = lk_dd_c.H, C = lk_dd_c.C, ws = lk_dd_c.ws, hs = lk_dd_c.hs, y, x, c; int st = C >= 4 ? 2 : 1, ii_w = ws + 1;
    if (jb->phase == 0) {                                   /* small copy of rows y0..y1: mean of each C x C block */
        for (y = jb->y0; y < jb->y1; y++) for (x = 0; x < ws; x++) {
            unsigned a = 0, b = 0, cc = 0, cnt = 0; int sy, sx;
            for (sy = 0; sy < C; sy += st) { int yy = y * C + sy; if (yy >= H) break; { const uint32_t *p = lk_dd_c.img + (size_t)yy * W; for (sx = 0; sx < C; sx += st) { int xx = x * C + sx; uint32_t q; if (xx >= W) break; q = p[xx]; a += q & 255; b += (q >> 8) & 255; cc += (q >> 16) & 255; cnt++; } } }
            if (!cnt) cnt = 1;
            lk_dd_lv0[(size_t)y * ws + x] = 0xFF000000u | ((cc / cnt) << 16) | ((b / cnt) << 8) | (a / cnt);
        }
    } else if (jb->phase == 1) {                            /* box average of the radius of each small pixel, rows y0..y1 */
        for (y = jb->y0; y < jb->y1; y++) for (x = 0; x < ws; x++) {
            int r16 = lk_dd_rs[(size_t)y * ws + x], R0 = r16 >> 4, fr = r16 & 15; uint32_t o = 0xFF000000u, px = lk_dd_lv0[(size_t)y * ws + x];
            if (r16 == 0) { lk_dd_bb[(size_t)y * ws + x] = px; continue; }
            if (R0 >= lk_dd_rm) { R0 = lk_dd_rm; fr = 0; }
            for (c = 0; c < 3; c++) {
                int v0, v1 = 0; const int32_t *ii = lk_dd_ii[c];
                if (R0 == 0) v0 = (int)((px >> (8 * c)) & 255);
                else { int x0 = x - R0 < 0 ? 0 : x - R0, x1 = x + R0 >= ws ? ws - 1 : x + R0, y0 = y - R0 < 0 ? 0 : y - R0, y1 = y + R0 >= hs ? hs - 1 : y + R0; v0 = (int)(((int64_t)(ii[(y1 + 1) * ii_w + x1 + 1] - ii[y0 * ii_w + x1 + 1] - ii[(y1 + 1) * ii_w + x0] + ii[y0 * ii_w + x0]) * lk_dd_recip[(x1 - x0 + 1) * (y1 - y0 + 1)]) >> 16); }
              { int R1 = R0 + 1, x0 = x - R1 < 0 ? 0 : x - R1, x1 = x + R1 >= ws ? ws - 1 : x + R1, y0 = y - R1 < 0 ? 0 : y - R1, y1 = y + R1 >= hs ? hs - 1 : y + R1; if (fr == 0) v1 = v0; else v1 = (int)(((int64_t)(ii[(y1 + 1) * ii_w + x1 + 1] - ii[y0 * ii_w + x1 + 1] - ii[(y1 + 1) * ii_w + x0] + ii[y0 * ii_w + x0]) * lk_dd_recip[(x1 - x0 + 1) * (y1 - y0 + 1)]) >> 16); }
                o |= (uint32_t)((v0 * (16 - fr) + v1 * fr) >> 4) << (8 * c);
            }
            lk_dd_bb[(size_t)y * ws + x] = o;
        }
    } else {                                                /* output rows y0..y1: sharp pixel mixed with the bilinear upsample of the blurred copy */
        for (y = jb->y0; y < jb->y1; y++) {
            int ya = lk_dd_yi[y], yb = ya + 1, fy = lk_dd_yf[y]; const uint16_t *rrow = lk_dd_r16 + (size_t)(y / N) * sw; uint32_t *row = lk_dd_c.img + (size_t)y * W;
            if (ya < 0) ya = 0; if (yb < 0) yb = 0; if (ya >= hs) ya = hs - 1; if (yb >= hs) yb = hs - 1;
            for (x = 0; x < W; x++) {
                int r16 = rrow[x / N], xa, xb, fx, wgt; uint32_t o = 0xFF000000u, s0, pa, pb, pc, pd;
                if (!r16) continue;
                xa = lk_dd_xi[x]; xb = xa + 1; fx = lk_dd_xf[x]; if (xa < 0) xa = 0; if (xb < 0) xb = 0; if (xa >= ws) xa = ws - 1; if (xb >= ws) xb = ws - 1;
                wgt = r16 >= 8 ? 256 : r16 * 32; s0 = row[x];
                pa = lk_dd_bb[(size_t)ya * ws + xa]; pb = lk_dd_bb[(size_t)ya * ws + xb]; pc = lk_dd_bb[(size_t)yb * ws + xa]; pd = lk_dd_bb[(size_t)yb * ws + xb];
                for (c = 0; c < 24; c += 8) { int top = (int)((pa >> c) & 255) * (256 - fx) + (int)((pb >> c) & 255) * fx, bot = (int)((pc >> c) & 255) * (256 - fx) + (int)((pd >> c) & 255) * fx, v = (top * (256 - fy) + bot * fy) >> 16, sv = (int)((s0 >> c) & 255); o |= (uint32_t)((sv * (256 - wgt) + v * wgt) >> 8) << c; }
                row[x] = o;
            }
        }
    }
    return 0;
}
static void lk_dd2_par(int phase, int rows) {
    lk_dd2_job job[4]; SDL_Thread *th[4] = { 0 }; int i, nt = lk_dd_c.nt; if (rows < 16 || lk_dd_c.W * lk_dd_c.H < 200000) nt = 1;   /* (the 1x picture is too small to pay for the threads) */
    for (i = 0; i < nt; i++) { job[i].phase = phase; job[i].y0 = rows * i / nt; job[i].y1 = rows * (i + 1) / nt; }
    for (i = 1; i < nt; i++) { th[i] = SDL_CreateThread(lk_dd2_run, "lkdof", &job[i]); if (!th[i]) lk_dd2_run(&job[i]); }
    lk_dd2_run(&job[0]);
    for (i = 1; i < nt; i++) if (th[i]) SDL_WaitThread(th[i], NULL);
}
static void lk_hd_dof(uint32_t *img, int W, int H, int N, int sw, int e, const int16_t *sc) {
    static const int FD[4] = { 1, 80, 70, 60 }, DZ[4] = { 0, 44, 40, 36 }, RM[4] = { 0, 2, 3, 4 };   /* sharp zone (rows around Nigel's ground row), rows beyond it until the full radius, full radius (game px) */
    static size_t cap, ncap; static int dbg = -1, nt0, lutS = -1; static uint16_t lut[128];
    int S = lk_dof_get(), x, y, k, any = 0, C = N == 1 ? 2 : N, ws = (W + C - 1) / C, hs = (H + C - 1) / C; size_t n = (size_t)sw * 224;
    if (dbg < 0) { const char *d = getenv("LANDSTALKER_HD_DEPTHDBG"); dbg = d && atoi(d); }
    if (S <= 0 && !dbg) return;
    if (S < 0) S = 0; if (S > 3) S = 3;
    if (!nt0) { nt0 = SDL_GetCPUCount(); if (nt0 > 4) nt0 = 4; if (nt0 < 1) nt0 = 1; if (getenv("LANDSTALKER_FXTHREADS")) nt0 = atoi(getenv("LANDSTALKER_FXTHREADS")); if (nt0 < 1) nt0 = 1; if (nt0 > 4) nt0 = 4; for (k = 1; k < 100; k++) lk_dd_recip[k] = 65536 / k; }
    if (lutS != S) { int d; for (d = 0; d < 128; d++) { int dist = d - DZ[S ? S : 2], r = 0; if (dist > 0) { int t = dist >= FD[S ? S : 2] ? 256 : dist * 256 / FD[S ? S : 2]; int sm = (t * t * (768 - 2 * t)) >> 16; r = (sm * RM[S ? S : 2] * 16 + 128) >> 8; } lut[d] = (uint16_t)r; } lutS = S; }   /* radius (1/16 game px) by distance in rows: smoothstep, no visible start line */
    if (cap < n) { free(lk_dd_r16); free(lk_dd_rs); free(lk_dd_lv0); free(lk_dd_bb); for (k = 0; k < 3; k++) { free(lk_dd_ii[k]); lk_dd_ii[k] = (int32_t *)malloc((size_t)(sw + 1) * 226 * 4); } lk_dd_r16 = (uint16_t *)malloc(n * 2); lk_dd_rs = (uint16_t *)malloc(n * 2); lk_dd_lv0 = (uint32_t *)malloc(n * 4); lk_dd_bb = (uint32_t *)malloc(n * 4); cap = n; }
    if (ncap < (size_t)(W > H ? W : H)) { size_t m = W > H ? W : H; free(lk_dd_xi); free(lk_dd_xf); free(lk_dd_yi); free(lk_dd_yf); lk_dd_xi = (int *)malloc(m * sizeof(int)); lk_dd_xf = (int *)malloc(m * sizeof(int)); lk_dd_yi = (int *)malloc(m * sizeof(int)); lk_dd_yf = (int *)malloc(m * sizeof(int)); ncap = m; }
    if (!lk_dd_r16 || !lk_dd_rs || !lk_dd_lv0 || !lk_dd_bb || !lk_dd_ii[0] || !lk_dd_ii[1] || !lk_dd_ii[2] || !lk_dd_xi || !lk_dd_xf || !lk_dd_yi || !lk_dd_yf) return;
    for (y = 0; y < 224; y++) for (x = 0; x < sw; x++) {   /* radius per game pixel (1/16 px); debug: 0x8000 | grey */
        int r16 = 0, cx = sc[(size_t)y * sw + x] - e;
        if (y >= 23 && lk_hd_dstamp[y] == lk_hd_gen && cx >= -48 && cx < 368) { int d = lk_hd_depth[y * 416 + cx + 48]; if (d != 0x7FFF) { int ad = abs(d - lk_hd_focus); if (dbg) { int g = 128 + (d - lk_hd_focus); if (g < 0) g = 0; if (g > 255) g = 255; lk_dd_r16[(size_t)y * sw + x] = (uint16_t)(0x8000 | g); continue; } r16 = lut[ad > 127 ? 127 : ad]; } }
        lk_dd_r16[(size_t)y * sw + x] = (uint16_t)r16;
    }
    if (dbg) { for (y = 0; y < H; y++) for (x = 0; x < W; x++) { int v = lk_dd_r16[(size_t)(y / N) * sw + x / N]; if (v & 0x8000) { int g = v & 255; img[(size_t)y * W + x] = 0xFF000000u | (g << 16) | (g << 8) | g; } else img[(size_t)y * W + x] = 0xFF800000u; } return; }
    for (k = 0; k < (int)n; k++) if (lk_dd_r16[k]) { any = 1; break; }
    if (!any) return;
    for (y = 0; y < hs; y++) for (x = 0; x < ws; x++) {      /* radius of a small cell: the largest of the game pixels it covers, in small pixels */
        int gx0 = x * C / N, gx1 = ((x + 1) * C - 1) / N, gy0 = y * C / N, gy1 = ((y + 1) * C - 1) / N, gx, gy, m = 0;
        if (gx1 >= sw) gx1 = sw - 1; if (gy1 > 223) gy1 = 223;
        for (gy = gy0; gy <= gy1; gy++) for (gx = gx0; gx <= gx1; gx++) { int v = lk_dd_r16[(size_t)gy * sw + gx]; if (v > m) m = v; }
        lk_dd_rs[(size_t)y * ws + x] = (uint16_t)((m * N + C / 2) / C);
    }
    lk_dd_c.img = img; lk_dd_c.W = W; lk_dd_c.H = H; lk_dd_c.N = N; lk_dd_c.sw = sw; lk_dd_c.nt = nt0; lk_dd_c.C = C; lk_dd_c.ws = ws; lk_dd_c.hs = hs; lk_dd_rm = (RM[S] * N + C - 1) / C;
    lk_dd2_par(0, hs);
    for (y = 0; y <= hs; y++) { /* summed-area tables of the three channels (one pass) */ }
    { int ii_w = ws + 1; int32_t *i0 = lk_dd_ii[0], *i1 = lk_dd_ii[1], *i2 = lk_dd_ii[2];
      for (x = 0; x <= ws; x++) i0[x] = i1[x] = i2[x] = 0;
      for (y = 0; y < hs; y++) { int32_t r0 = 0, r1 = 0, r2 = 0; i0[(y + 1) * ii_w] = i1[(y + 1) * ii_w] = i2[(y + 1) * ii_w] = 0;
        for (x = 0; x < ws; x++) { uint32_t q = lk_dd_lv0[(size_t)y * ws + x]; r0 += q & 255; r1 += (q >> 8) & 255; r2 += (q >> 16) & 255; i0[(y + 1) * ii_w + x + 1] = i0[y * ii_w + x + 1] + r0; i1[(y + 1) * ii_w + x + 1] = i1[y * ii_w + x + 1] + r1; i2[(y + 1) * ii_w + x + 1] = i2[y * ii_w + x + 1] + r2; } } }
    lk_dd2_par(1, hs);
    for (x = 0; x < W; x++) { int u = (2 * x + 1 - C) * 128 / C; lk_dd_xi[x] = u >> 8; lk_dd_xf[x] = u & 255; }
    for (y = 0; y < H; y++) { int u = (2 * y + 1 - C) * 128 / C; lk_dd_yi[y] = u >> 8; lk_dd_yf[y] = u & 255; }
    lk_dd2_par(2, H);
}
/* depth blur without a tile pack: on the 1x picture (the blurred part needs no finer resolution) before the CRT filters, which then run at the normal cost */
static const uint32_t *lk_hd_dof1x(const uint32_t *fb, int sw, int e) {
    static uint32_t *buf; static int16_t *sc; static int bw;
    if (bw != sw) { free(buf); free(sc); buf = (uint32_t *)malloc((size_t)sw * 224 * 4); sc = (int16_t *)malloc((size_t)sw * 224 * 2); bw = sw; if (sc) { int x, y; for (y = 0; y < 224; y++) for (x = 0; x < sw; x++) sc[(size_t)y * sw + x] = (int16_t)x; } }
    if (!buf || !sc) return fb;
    { static double tt; static int cnt; Uint64 t0 = SDL_GetPerformanceCounter(); memcpy(buf, fb, (size_t)sw * 224 * 4);
    lk_hd_dof(buf, sw, 224, 1, sw, e, sc);
    tt += (double)(SDL_GetPerformanceCounter() - t0) * 1e3 / (double)SDL_GetPerformanceFrequency(); if (++cnt % 300 == 0 && getenv("LANDSTALKER_HD_TIME")) printf("hdtime: 1x depth blur %.2f ms per frame (avg over %d)\n", tt / cnt, cnt); }
    return buf;
}
uint32_t *lk_hd_assemble(const uint32_t *fb, int sw, int e, int *ow, int *oh) {
    int N = lk_hd_n, W = sw * N, H = 224 * N, y, x, sx, sy;
    static uint8_t *m; static int16_t *sc; static size_t mcap;
    if (N <= 0 || !lk_hd_rows || !lk_hd_ref) return NULL;
    if (!lk_hd_img || lk_hd_iw != W || lk_hd_ih != H) { free(lk_hd_img); lk_hd_img = (uint32_t *)malloc((size_t)W * H * 4); lk_hd_iw = W; lk_hd_ih = H; }
    if (mcap < (size_t)sw * 224) { free(m); free(sc); m = (uint8_t *)malloc((size_t)sw * 224); sc = (int16_t *)malloc((size_t)sw * 224 * 2); mcap = (m && sc) ? (size_t)sw * 224 : 0; }
    if (!lk_hd_img || !m || !sc || !mcap) return NULL;
    for (y = 0; y < 224; y++) {                             /* m = the final pixel is the compositor's pixel (no overlay drew here); sc = the picture column the pixel comes from (the quick item bar moves the columns of the HUD lines 5..22: the HD block moves with them) */
        const uint32_t *src = fb + (size_t)y * sw; int ok = lk_hd_stamp[y] == lk_hd_gen;
        for (x = 0; x < sw; x++) { int sx0 = (y >= 5 && y <= 22) ? lk_quick_hdcol(x) : x, cx = sx0 - e; sc[(size_t)y * sw + x] = (int16_t)sx0; m[(size_t)y * sw + x] = ok && sx0 >= 0 && sx0 < sw && cx >= -48 && cx < 320 + 48 && (src[x] == lk_hd_ref[y * 416 + cx + 48] || ((lk_shadow_hdflags(x, y) & 1) && src[x] == lk_hd_dark(lk_hd_ref[y * 416 + cx + 48]))); }
    }
    for (y = 0; y < 224; y++) {
        const uint32_t *src = fb + (size_t)y * sw;
        for (x = 0; x < sw; x++) {                          /* an HD block is only used where the whole 3 x 3 neighbourhood is the compositor's: overlays that move pixels around (Item Info, the text box line, the quick item cells) keep equal colours by chance at their edges, and an enlarged tile cut from a neighbourhood that is not there shows as specks */
            int cx = sc[(size_t)y * sw + x] - e, use = m[(size_t)y * sw + x], dy, dx; int shf = lk_shadow_hdflags(x, y) & 3;
            for (dy = -1; dy <= 1 && use; dy++) for (dx = -1; dx <= 1; dx++) { int yy = y + dy, xx = x + dx; if (yy < 0 || yy > 223 || xx < 0 || xx >= sw) continue; if (!m[(size_t)yy * sw + xx]) { use = 0; break; } }
            for (sy = 0; sy < N; sy++) {
                uint32_t *dst = lk_hd_img + (size_t)(y * N + sy) * W;
                if (use) { const uint32_t *hb = lk_hd_rows + (size_t)(y * N + sy) * 416 * N + (size_t)(cx + 48) * N; for (sx = 0; sx < N; sx++) dst[x * N + sx] = hb[sx];
                    if (shf) for (sx = 0; sx < N; sx++) { int a = lk_shadow_hdalpha(x, y, sx, sy, N); if (a) { uint32_t c = dst[x * N + sx], k = 255 - (a * 112 + 127) / 255;   /* shadow: 56 % brightness at full strength (the 1x darkening), per pixel at the HD resolution, the HD texture stays */ dst[x * N + sx] = (c & 0xFF000000u) | ((((c >> 16) & 255) * k / 255) << 16) | ((((c >> 8) & 255) * k / 255) << 8) | ((c & 255) * k / 255); } } }
                else for (sx = 0; sx < N; sx++) dst[x * N + sx] = src[x];
            }
        }
    }
    { static double t0, t1, t2; static int cnt; Uint64 a = SDL_GetPerformanceCounter(), b; double c = 0; lk_hd_dof(lk_hd_img, W, H, N, sw, e, sc); b = SDL_GetPerformanceCounter(); t1 += (double)(b - a) * 1e3 / (double)SDL_GetPerformanceFrequency(); if (++cnt % 300 == 0 && getenv("LANDSTALKER_HD_TIME")) printf("hdtime: dof %.2f ms avg over %d\n", t1 / cnt, cnt); (void)t0; (void)t2; (void)c; }
    *ow = W; *oh = H; return lk_hd_img;
}
static double lk_hd_ms(Uint64 a) { return (double)(SDL_GetPerformanceCounter() - a) * 1e3 / (double)SDL_GetPerformanceFrequency(); }
static double lk_hd_tasm, lk_hd_tfil; static int lk_hd_tcnt;
static int lk_hd_present(const uint8_t *framebuffer, int sw, const lk_rect *r) {
    int iw, ih; Uint64 t0 = SDL_GetPerformanceCounter(); uint32_t *img = lk_hd_assemble((const uint32_t *)framebuffer, sw, lk_wide_e, &iw, &ih); lk_hd_tasm += lk_hd_ms(t0); t0 = SDL_GetPerformanceCounter();
    if (!img) return 0;
    if (!lk_hd_tex || lk_hd_tw != iw || lk_hd_th != ih) {
        if (lk_hd_tex) SDL_DestroyTexture(lk_hd_tex);
        lk_hd_tex = SDL_CreateTexture(s_renderer, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STREAMING, iw, ih);
        if (lk_hd_tex) SDL_SetTextureScaleMode(lk_hd_tex, SDL_ScaleModeLinear);
        lk_hd_tw = iw; lk_hd_th = ih;
    }
    if (!lk_hd_tex) return 0;
    if (lk_fx_mode != LK_FX_OFF && r->w <= LK_MAXDIM && r->h <= LK_MAXDIM && r->w >= LK_SRC_W && r->h >= LK_SRC_H) {   /* the CRT filters on the HD picture: scanlines / beam / mask per GAME line (lk_hdn), sampling from the finer HD columns */
        if (!lk_hd_ftex || lk_hd_fw != r->w || lk_hd_fh != r->h) {
            if (lk_hd_ftex) SDL_DestroyTexture(lk_hd_ftex);
            free(lk_hd_fbuf);
            lk_hd_ftex = SDL_CreateTexture(s_renderer, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STREAMING, r->w, r->h);
            lk_hd_fbuf = (uint32_t *)malloc((size_t)r->w * r->h * 4); lk_hd_fw = r->w; lk_hd_fh = r->h;
        }
        if (lk_hd_ftex && lk_hd_fbuf) {
            lk_hdn = lk_hd_n;
            if (lk_fx_mode >= LK_FX_PRO) {
                lk_f2_prepare(r->w, r->h, lk_fx_mode, iw);
                if (lk_f2_plane) { lk_fx_render_mt(img, lk_hd_fbuf, r->w, LK_SRC_H, iw, 2); lk_fx_render_mt(img, lk_hd_fbuf, r->w, r->h, iw, 3); }
                else { lk_fx_prepare(r->w, r->h, LK_FX_CRT, iw); lk_fx_render_mt(img, lk_hd_fbuf, r->w, r->h, iw, 0); }
            } else { lk_fx_prepare(r->w, r->h, lk_fx_mode, iw); lk_fx_render_mt(img, lk_hd_fbuf, r->w, r->h, iw, 0); }
            lk_hdn = 1; lk_hd_tfil += lk_hd_ms(t0); if (++lk_hd_tcnt % 300 == 0 && getenv("LANDSTALKER_HD_TIME")) { printf("hdtime: assemble(incl. dof) %.2f ms, filter %.2f ms per frame\n", lk_hd_tasm / lk_hd_tcnt, lk_hd_tfil / lk_hd_tcnt); }
            SDL_UpdateTexture(lk_hd_ftex, NULL, lk_hd_fbuf, r->w * 4);
            { SDL_Rect d = { r->x, r->y, r->w, r->h }; SDL_RenderCopy(s_renderer, lk_hd_ftex, NULL, &d); }
            return 1;
        }
    }
    SDL_UpdateTexture(lk_hd_tex, NULL, img, iw * 4);
    { SDL_Rect d = { r->x, r->y, r->w, r->h }; SDL_RenderCopy(s_renderer, lk_hd_tex, NULL, &d); }
    return 1;
}
'''
s = s.replace(a, module + a, 1)
dd = "    if (lk_dd_mode) {                                   /* de-dither"
assert s.count(dd) == 1, "platform_sdl.c: de-dither block layout changed"
s = s.replace(dd, "    extern int lk_hd_active(void);\n    if (lk_dd_mode && !lk_hd_active()) {                 /* (HD picture: no de-dither, it would change the 1x pixels the HD blocks are matched against) */   /* de-dither", 1)
hk = "    lk_rect r; lk_calc_rect(lk_scale_mode, ow, oh, sw, &r);\n"
assert s.count(hk) == 1, "platform_sdl.c: lk_disp_present rect layout changed"
s = s.replace(hk, "    if (!lk_hd_active() && lk_dof_get() > 0) framebuffer = (const uint8_t *)lk_hd_dof1x((const uint32_t *)framebuffer, sw, lk_wide_e);   /* depth blur on the 1x picture (no tile pack) */\n" + hk, 1)
b = "    SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 255);\n    SDL_RenderClear(s_renderer);\n    static int lk_sb_env = -1;"
assert s.count(b) == 1, "platform_sdl.c: lk_disp_present body layout changed"
s = s.replace(b, "    SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 255);\n    SDL_RenderClear(s_renderer);\n    if (lk_hd_active() && lk_hd_present(framebuffer, sw, &r)) { lk_osd_draw(ow, oh); lk_coords_draw(oh); SDL_RenderPresent(s_renderer); return; }   /* LK_HD v1 */\n    static int lk_sb_env = -1;", 1)
# screenshot of the HD picture
c = "static void lk_shot_frame(const uint8_t *framebuffer, long frame) {"
assert s.count(c) == 1, "platform_sdl.c: run patch_shot.py first"
s = s.replace(c, "extern int lk_hd_n; extern int lk_hd_active(void); extern int lk_dof_get(void); extern int lk_wide_e; uint32_t *lk_hd_assemble(const uint32_t *fb, int sw, int e, int *ow, int *oh);   /* LK_HD v1 */\n" + c, 1)
d = "    if (!list || !*list || !lk_shot_wanted(list, frame)) return;"
assert s.count(d) == 1
s = s.replace(d, '''    { const char *hl = getenv("LANDSTALKER_HD_SHOT");   /* LK_HD v1: the HD picture */
      if (hl && *hl && !lk_hd_active() && lk_dof_get() > 0 && lk_shot_wanted(hl, frame)) { int sw1 = 320 + 2 * lk_wide_e; const uint32_t *img1 = lk_hd_dof1x((const uint32_t *)framebuffer, sw1, lk_wide_e); char path1[600]; snprintf(path1, sizeof path1, "%s/dofshot_%06ld_w%d.png", dir, frame, sw1); { struct stat st1; if (stat(dir, &st1) != 0) { mkdir(dir, 0777); } } printf("shot: %s %s (1x depth blur)\\n", lk_shot_png(path1, img1, sw1, 224, 1) ? "wrote" : "FAILED", path1); }
      if (hl && *hl && lk_hd_active() && lk_shot_wanted(hl, frame)) { int iw, ih; uint32_t *img = lk_hd_assemble((const uint32_t *)framebuffer, 320 + 2 * lk_wide_e, lk_wide_e, &iw, &ih); char path[600]; snprintf(path, sizeof path, "%s/hdshot_%06ld_w%d.png", dir, frame, iw);
        { struct stat st; if (stat(dir, &st) != 0) { mkdir(dir, 0777); } }
        if (img) printf("shot: %s %s (%dx%d HD)\\n", lk_shot_png(path, img, iw, ih, 1) ? "wrote" : "FAILED", path, iw, ih); } }
''' + d, 1)
s = s + "\n/* " + VER + " */\n"
open(p, "w").write(s)
print("platform_sdl.c patched:", VER)
