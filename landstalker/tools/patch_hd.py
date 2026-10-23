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
static void lk_bbox(const uint32_t *s, uint32_t *d, uint32_t *t, int w, int h, int R) {   /* box blur of radius R (edges replicated), per channel, sliding window */
    int x, y, c;
    for (c = 0; c <= 16; c += 8) {
        for (y = 0; y < h; y++) {
            const uint32_t *r = s + (size_t)y * w; uint32_t *o = t + (size_t)y * w; int k, sum = 0;
            for (k = -R; k <= R; k++) sum += (r[k < 0 ? 0 : k >= w ? w - 1 : k] >> c) & 255;
            for (x = 0; x < w; x++) {
                int a = x + R + 1, b = x - R; if (a >= w) a = w - 1; if (b < 0) b = 0;
                o[x] = (o[x] & ~(255u << c)) | ((uint32_t)(sum / (2 * R + 1)) << c);
                sum += ((r[a] >> c) & 255) - ((r[b] >> c) & 255);
            }
        }
        for (x = 0; x < w; x++) {
            int k, sum = 0;
            for (k = -R; k <= R; k++) sum += (t[(size_t)(k < 0 ? 0 : k >= h ? h - 1 : k) * w + x] >> c) & 255;
            for (y = 0; y < h; y++) {
                int a = y + R + 1, b = y - R; if (a >= h) a = h - 1; if (b < 0) b = 0;
                d[(size_t)y * w + x] = (d[(size_t)y * w + x] & ~(255u << c)) | ((uint32_t)(sum / (2 * R + 1)) << c);
                sum += ((t[(size_t)a * w + x] >> c) & 255) - ((t[(size_t)b * w + x] >> c) & 255);
            }
        }
    }
}
/* depth blur (HD only): blur radius grows with the distance of a pixel's ground point from Nigel's (screen rows, lk_hd_depth / lk_hd_focus); the sharp HD picture is mixed with a bilinear upsample of a blurred 1x copy */
static void lk_hd_dof(uint32_t *img, int W, int H, int N, int sw, int e, const int16_t *sc) {
    static const float K[4] = { 0, 0.03f, 0.045f, 0.06f }, DZ[4] = { 0, 40, 32, 24 }; static const int RM[4] = { 0, 2, 3, 4 };
    static float *rr; static uint32_t *lv[5], *tmp, *bb; static size_t cap; static int *xi, *xf, *yi, *yf, xcap, ycap; static int dbg = -1;
    int S = lk_dof_get(), x, y, k, any = 0; size_t n = (size_t)sw * 224;
    if (dbg < 0) { const char *d = getenv("LANDSTALKER_HD_DEPTHDBG"); dbg = d && atoi(d); }
    if (S <= 0 && !dbg) return;
    if (S < 0) S = 0; if (S > 3) S = 3;
    if (cap < n) { free(rr); free(tmp); free(bb); for (k = 0; k < 5; k++) { free(lv[k]); lv[k] = (uint32_t *)malloc(n * 4); } rr = (float *)malloc(n * 4); tmp = (uint32_t *)malloc(n * 4); bb = (uint32_t *)malloc(n * 4); cap = n; }
    if (xcap < W) { free(xi); free(xf); xi = (int *)malloc(W * sizeof(int)); xf = (int *)malloc(W * sizeof(int)); xcap = W; }
    if (ycap < H) { free(yi); free(yf); yi = (int *)malloc(H * sizeof(int)); yf = (int *)malloc(H * sizeof(int)); ycap = H; }
    if (!rr || !tmp || !bb || !xi || !xf || !yi || !yf || !lv[0] || !lv[4]) return;
    for (y = 0; y < 224; y++) for (x = 0; x < sw; x++) {
        float r = 0; int cx = sc[(size_t)y * sw + x] - e;
        if (y >= 23 && lk_hd_dstamp[y] == lk_hd_gen && cx >= -48 && cx < 368) { int d = lk_hd_depth[y * 416 + cx + 48]; if (d != 0x7FFF) { float dist = (float)abs(d - lk_hd_focus) - DZ[S ? S : 2]; if (dist > 0) { r = dist * K[S ? S : 2]; if (r > RM[S ? S : 2]) r = (float)RM[S ? S : 2]; } if (dbg) { int g = 128 + (d - lk_hd_focus); if (g < 0) g = 0; if (g > 255) g = 255; rr[(size_t)y * sw + x] = -(float)(g + 1); continue; } } }
        rr[(size_t)y * sw + x] = S ? r : 0;
    }
    if (dbg) { for (y = 0; y < H; y++) for (x = 0; x < W; x++) { float v = rr[(size_t)(y / N) * sw + x / N]; if (v < 0) { int g = (int)(-v) - 1; img[(size_t)y * W + x] = 0xFF000000u | (g << 16) | (g << 8) | g; } else img[(size_t)y * W + x] = 0xFF800000u; } return; }
    for (k = 0; k < (int)n; k++) if (rr[k] > 0) { any = 1; break; }
    if (!any) return;
    for (y = 0; y < 224; y++) for (x = 0; x < sw; x++) {   /* lv[0] = the 1x copy (mean of each N x N block) */
        unsigned a = 0, b = 0, c = 0; int sy, sx;
        int st = N >= 4 ? 2 : 1;   /* (every other pixel of a big block is enough for the blurred copy) */
        for (sy = 0; sy < N; sy += st) { const uint32_t *p = img + (size_t)(y * N + sy) * W + x * N; for (sx = 0; sx < N; sx += st) { uint32_t q = p[sx]; a += q & 255; b += (q >> 8) & 255; c += (q >> 16) & 255; } }
        { unsigned nn = (unsigned)((N / st) * (N / st)); lv[0][(size_t)y * sw + x] = 0xFF000000u | ((c / nn) << 16) | ((b / nn) << 8) | (a / nn); }
    }
    for (k = 1; k <= RM[S]; k++) lk_bbox(lv[0], lv[k], tmp, sw, 224, k);
    for (k = 0; k < (int)n; k++) {                          /* bb = the blurred copy: radius r between the box levels */
        float r = rr[k]; int f; float t; uint32_t A, B, o = 0xFF000000u; int c;
        if (r <= 0) { bb[k] = lv[0][k]; continue; }
        f = (int)r; t = r - f; if (f < 0) f = 0; if (f >= RM[S]) { f = RM[S]; t = 0; }
        A = lv[f][k]; B = lv[f < RM[S] ? f + 1 : f][k];
        for (c = 0; c <= 16; c += 8) o |= (uint32_t)((((A >> c) & 255) * (1 - t) + ((B >> c) & 255) * t) + 0.5f) << c;
        bb[k] = o;
    }
    for (x = 0; x < W; x++) { int u = (2 * x + 1 - N) * 128 / N; int i0 = u >> 8; xi[x] = i0; xf[x] = u & 255; }   /* bilinear sample position of an HD pixel in the 1x copy */
    for (y = 0; y < H; y++) { int u = (2 * y + 1 - N) * 128 / N; int i0 = u >> 8; yi[y] = i0; yf[y] = u & 255; }
    for (y = 0; y < H; y++) {
        int y0 = yi[y], y1 = y0 + 1, fy = yf[y]; if (y0 < 0) y0 = 0; if (y1 < 0) y1 = 0; if (y0 > 223) y0 = 223; if (y1 > 223) y1 = 223;
        for (x = 0; x < W; x++) {
            float r = rr[(size_t)(y / N) * sw + x / N]; int x0, x1, fx, c, wgt; uint32_t o = 0xFF000000u, s0 = img[(size_t)y * W + x];
            if (r <= 0) continue;
            x0 = xi[x]; x1 = x0 + 1; fx = xf[x]; if (x0 < 0) x0 = 0; if (x1 < 0) x1 = 0; if (x0 >= sw) x0 = sw - 1; if (x1 >= sw) x1 = sw - 1;
            wgt = r >= 0.5f ? 256 : (int)(r * 512);
            { const uint32_t p00 = bb[(size_t)y0 * sw + x0], p01 = bb[(size_t)y0 * sw + x1], p10 = bb[(size_t)y1 * sw + x0], p11 = bb[(size_t)y1 * sw + x1];
              for (c = 0; c <= 16; c += 8) { int top = (int)((p00 >> c) & 255) * (256 - fx) + (int)((p01 >> c) & 255) * fx, bot = (int)((p10 >> c) & 255) * (256 - fx) + (int)((p11 >> c) & 255) * fx, v = (top * (256 - fy) + bot * fy) >> 16, sv = (int)((s0 >> c) & 255); o |= (uint32_t)((sv * (256 - wgt) + v * wgt) >> 8) << c; } }
            img[(size_t)y * W + x] = o;
        }
    }
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
    lk_hd_dof(lk_hd_img, W, H, N, sw, e, sc);
    *ow = W; *oh = H; return lk_hd_img;
}
static int lk_hd_present(const uint8_t *framebuffer, int sw, const lk_rect *r) {
    int iw, ih; uint32_t *img = lk_hd_assemble((const uint32_t *)framebuffer, sw, lk_wide_e, &iw, &ih);
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
            lk_hdn = 1;
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
b = "    SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 255);\n    SDL_RenderClear(s_renderer);\n    static int lk_sb_env = -1;"
assert s.count(b) == 1, "platform_sdl.c: lk_disp_present body layout changed"
s = s.replace(b, "    SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 255);\n    SDL_RenderClear(s_renderer);\n    if (lk_hd_active() && lk_hd_present(framebuffer, sw, &r)) { lk_osd_draw(ow, oh); lk_coords_draw(oh); SDL_RenderPresent(s_renderer); return; }   /* LK_HD v1 */\n    static int lk_sb_env = -1;", 1)
# screenshot of the HD picture
c = "static void lk_shot_frame(const uint8_t *framebuffer, long frame) {"
assert s.count(c) == 1, "platform_sdl.c: run patch_shot.py first"
s = s.replace(c, "extern int lk_hd_n; extern int lk_hd_active(void); extern int lk_wide_e; uint32_t *lk_hd_assemble(const uint32_t *fb, int sw, int e, int *ow, int *oh);   /* LK_HD v1 */\n" + c, 1)
d = "    if (!list || !*list || !lk_shot_wanted(list, frame)) return;"
assert s.count(d) == 1
s = s.replace(d, '''    { const char *hl = getenv("LANDSTALKER_HD_SHOT");   /* LK_HD v1: the HD picture */
      if (hl && *hl && lk_hd_active() && lk_shot_wanted(hl, frame)) { int iw, ih; uint32_t *img = lk_hd_assemble((const uint32_t *)framebuffer, 320 + 2 * lk_wide_e, lk_wide_e, &iw, &ih); char path[600]; snprintf(path, sizeof path, "%s/hdshot_%06ld_w%d.png", dir, frame, iw);
        { struct stat st; if (stat(dir, &st) != 0) { mkdir(dir, 0777); } }
        if (img) printf("shot: %s %s (%dx%d HD)\\n", lk_shot_png(path, img, iw, ih, 1) ? "wrote" : "FAILED", path, iw, ih); } }
''' + d, 1)
s = s + "\n/* " + VER + " */\n"
open(p, "w").write(s)
print("platform_sdl.c patched:", VER)
