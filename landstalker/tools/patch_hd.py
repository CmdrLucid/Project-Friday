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
VER = "LK_HD v1"
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched:", VER); sys.exit(0)
a = "/* draw the frame: returns after SDL_RenderPresent */\nstatic void lk_disp_present(const uint8_t *framebuffer) {"
assert s.count(a) == 1, "platform_sdl.c: lk_disp_present layout changed"
module = r'''/* ---- LK_HD v1: HD picture from the compositor's n x n blocks (tools/patch_hd.py) ---- */
extern int lk_hd_n; extern uint32_t *lk_hd_rows, *lk_hd_ref; extern long lk_hd_stamp[224], lk_hd_gen; extern int lk_wide_e; extern int lk_quick_hdcol(int x);
static uint32_t *lk_hd_img; static int lk_hd_iw, lk_hd_ih; static SDL_Texture *lk_hd_tex; static int lk_hd_tw, lk_hd_th;
static SDL_Texture *lk_hd_ftex; static int lk_hd_fw, lk_hd_fh; static uint32_t *lk_hd_fbuf;   /* filtered HD picture (destination size) */
uint32_t *lk_hd_assemble(const uint32_t *fb, int sw, int e, int *ow, int *oh) {
    int N = lk_hd_n, W = sw * N, H = 224 * N, y, x, sx, sy;
    static uint8_t *m; static int16_t *sc; static size_t mcap;
    if (N <= 0 || !lk_hd_rows || !lk_hd_ref) return NULL;
    if (!lk_hd_img || lk_hd_iw != W || lk_hd_ih != H) { free(lk_hd_img); lk_hd_img = (uint32_t *)malloc((size_t)W * H * 4); lk_hd_iw = W; lk_hd_ih = H; }
    if (mcap < (size_t)sw * 224) { free(m); free(sc); m = (uint8_t *)malloc((size_t)sw * 224); sc = (int16_t *)malloc((size_t)sw * 224 * 2); mcap = (m && sc) ? (size_t)sw * 224 : 0; }
    if (!lk_hd_img || !m || !sc || !mcap) return NULL;
    for (y = 0; y < 224; y++) {                             /* m = the final pixel is the compositor's pixel (no overlay drew here); sc = the picture column the pixel comes from (the quick item bar moves the columns of the HUD lines 5..22: the HD block moves with them) */
        const uint32_t *src = fb + (size_t)y * sw; int ok = lk_hd_stamp[y] == lk_hd_gen;
        for (x = 0; x < sw; x++) { int sx0 = (y >= 5 && y <= 22) ? lk_quick_hdcol(x) : x, cx = sx0 - e; sc[(size_t)y * sw + x] = (int16_t)sx0; m[(size_t)y * sw + x] = ok && sx0 >= 0 && sx0 < sw && cx >= -48 && cx < 320 + 48 && src[x] == lk_hd_ref[y * 416 + cx + 48]; }
    }
    for (y = 0; y < 224; y++) {
        const uint32_t *src = fb + (size_t)y * sw;
        for (x = 0; x < sw; x++) {                          /* an HD block is only used where the whole 3 x 3 neighbourhood is the compositor's: overlays that move pixels around (Item Info, the text box line, the quick item cells) keep equal colours by chance at their edges, and an enlarged tile cut from a neighbourhood that is not there shows as specks */
            int cx = sc[(size_t)y * sw + x] - e, use = m[(size_t)y * sw + x], dy, dx;
            for (dy = -1; dy <= 1 && use; dy++) for (dx = -1; dx <= 1; dx++) { int yy = y + dy, xx = x + dx; if (yy < 0 || yy > 223 || xx < 0 || xx >= sw) continue; if (!m[(size_t)yy * sw + xx]) { use = 0; break; } }
            for (sy = 0; sy < N; sy++) {
                uint32_t *dst = lk_hd_img + (size_t)(y * N + sy) * W;
                if (use) { const uint32_t *hb = lk_hd_rows + (size_t)(y * N + sy) * 416 * N + (size_t)(cx + 48) * N; for (sx = 0; sx < N; sx++) dst[x * N + sx] = hb[sx]; }
                else for (sx = 0; sx < N; sx++) dst[x * N + sx] = src[x];
            }
        }
    }
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
s = s.replace(dd, "    extern int lk_hd_n;\n    if (lk_dd_mode && !(lk_hd_n > 0)) {                 /* (HD picture: no de-dither, it would change the 1x pixels the HD blocks are matched against) */   /* de-dither", 1)
b = "    SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 255);\n    SDL_RenderClear(s_renderer);\n    static int lk_sb_env = -1;"
assert s.count(b) == 1, "platform_sdl.c: lk_disp_present body layout changed"
s = s.replace(b, "    SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 255);\n    SDL_RenderClear(s_renderer);\n    if (lk_hd_n > 0 && lk_hd_present(framebuffer, sw, &r)) { lk_osd_draw(ow, oh); lk_coords_draw(oh); SDL_RenderPresent(s_renderer); return; }   /* LK_HD v1 */\n    static int lk_sb_env = -1;", 1)
# screenshot of the HD picture
c = "static void lk_shot_frame(const uint8_t *framebuffer, long frame) {"
assert s.count(c) == 1, "platform_sdl.c: run patch_shot.py first"
s = s.replace(c, "extern int lk_hd_n; extern int lk_wide_e; uint32_t *lk_hd_assemble(const uint32_t *fb, int sw, int e, int *ow, int *oh);   /* LK_HD v1 */\n" + c, 1)
d = "    if (!list || !*list || !lk_shot_wanted(list, frame)) return;"
assert s.count(d) == 1
s = s.replace(d, '''    { const char *hl = getenv("LANDSTALKER_HD_SHOT");   /* LK_HD v1: the HD picture */
      if (hl && *hl && lk_hd_n > 0 && lk_shot_wanted(hl, frame)) { int iw, ih; uint32_t *img = lk_hd_assemble((const uint32_t *)framebuffer, 320 + 2 * lk_wide_e, lk_wide_e, &iw, &ih); char path[600]; snprintf(path, sizeof path, "%s/hdshot_%06ld_w%d.png", dir, frame, iw);
        { struct stat st; if (stat(dir, &st) != 0) { mkdir(dir, 0777); } }
        if (img) printf("shot: %s %s (%dx%d HD)\\n", lk_shot_png(path, img, iw, ih, 1) ? "wrote" : "FAILED", path, iw, ih); } }
''' + d, 1)
s = s + "\n/* " + VER + " */\n"
open(p, "w").write(s)
print("platform_sdl.c patched:", VER)
