#!/usr/bin/env python3
"""Display pipeline for the SDL platform layer: scaling modes, CRT filter, on-screen hint, saved settings.
 * Scale modes (L1 on the Deck pad, F1 on a keyboard):  FIT (letterbox 320:224, the old behaviour) -> 4:3 (TV aspect) -> INTEGER (largest whole multiple) -> FILL (stretch to the window, 16:10 on the Deck)
 * Filter modes (R1 / F2):  OFF -> SCANLINES (sharp pixels + dark lines between source rows) -> CRT (smooth + scanlines + RGB phosphor mask)
 * A small hint with the new mode is drawn for ~1.7 s. The choice is saved in ~/.landstalker_display ("<scale> <filter>") and reloaded at start.
The filters run on the CPU (320x224 -> window size, ~1 ms on the Deck). The pure helpers sit between LK_DISPLAY_BEGIN/END without SDL calls so that
tools/displaytest can compile and check them in the cloud sandbox. Idempotent. usage: patch_display.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]

# ---- platform.h: prototypes -------------------------------------------------
ph = os.path.join(root, "include/genrecomp/platform.h")
s = open(ph).read()
if "platform_display_cycle_scale" not in s:
    a = "void platform_frame_sync(void);"
    assert a in s, "platform.h layout changed"
    s = s.replace(a, a + "\n/* LANDSTALKER_DISPLAY: cycle the scaling mode / the filter (pad shoulder buttons, F1/F2) */\nvoid platform_display_cycle_scale(void);\nvoid platform_display_cycle_filter(void);\nvoid platform_display_cycle_dither(void);\n/* LANDSTALKER_WIDE run-time switch (pad left trigger L2, F3): 0 -> 16 -> 32 -> 48 -> 0 */\nvoid platform_display_cycle_wide(void);", 1)
    open(ph, "w").write(s)

# ---- input.c: left trigger (L2) = widescreen width ------------------------------
pi = os.path.join(root, "src/input.c")
inp = open(pi).read()
if "platform_display_cycle_wide" not in inp:
    a = "                ls_prev = ls; rs_prev = rs;\n            }\n"
    assert inp.count(a) == 1, "input.c: shoulder button block layout changed"
    inp = inp.replace(a, a + "            { /* LANDSTALKER_WIDE: left trigger (L2) = widescreen width 0/16/32/48 */\n                static int lt_prev; int lt = PA(TRIGGERLEFT) > 16000;\n                if (lt && !lt_prev) platform_display_cycle_wide();\n                lt_prev = lt;\n            }\n", 1)
    open(pi, "w").write(inp)

# ---- platform_sdl.c ----------------------------------------------------------
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if "LANDSTALKER_DISPLAY" in s:
    print("platform_sdl.c already patched: LANDSTALKER_DISPLAY"); sys.exit(0)

PURE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "display_core.c")).read()

SDLPART = r'''
/* LANDSTALKER_DISPLAY: SDL side (see tools/patch_display.py) */
static int lk_scale_mode, lk_fx_mode, lk_disp_loaded, lk_osd_frames;
static int lk_dd_mode, lk_dd_loaded;   /* de-dither: 0 off, 1 light, 2 strong, 3 blend (horizontal CRT-like) (own file ~/.landstalker_dither, tools/display_core.c lk_dedither*) */
static uint32_t *lk_dd_buf; static int lk_dd_cap;
static const char *lk_dd_names[4] = { "OFF", "LIGHT", "STRONG", "BLEND" };
static char lk_osd_text[40];
static SDL_Texture *lk_fx_tex; static int lk_fx_tw, lk_fx_th;
static uint32_t *lk_fx_buf;
static const char *lk_scale_names[LK_SC_N] = { "FIT", "4:3", "INTEGER", "FILL" };
static const char *lk_fx_names[LK_FX_N] = { "OFF", "SCANLINES", "CRT", "CRT PRO", "CRT CURVED" };
static void lk_disp_path(char *out, size_t n) { const char *h = getenv("HOME"); snprintf(out, n, "%s/.landstalker_display", h ? h : "."); }
static void lk_disp_load(void) {
    char path[600]; lk_disp_loaded = 1; lk_disp_path(path, sizeof(path));
    FILE *f = fopen(path, "r");
    if (f) { int a = 0, b = 0; if (fscanf(f, "%d %d", &a, &b) == 2) { if (a >= 0 && a < LK_SC_N) lk_scale_mode = a; if (b >= 0 && b < LK_FX_N) lk_fx_mode = b; } fclose(f); }
}
static void lk_dd_load(void) {
    const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_DEDITHER"); char path[600]; lk_dd_loaded = 1;
    snprintf(path, sizeof(path), "%s/.landstalker_dither", h ? h : ".");
    FILE *f = fopen(path, "r"); if (f) { int a = 0; if (fscanf(f, "%d", &a) == 1 && a >= 0 && a < 4) lk_dd_mode = a; fclose(f); }
    if (e && *e) { int a = atoi(e); if (a >= 0 && a < 4) lk_dd_mode = a; }
}
static void lk_dd_save(void) {
    const char *h = getenv("HOME"); char path[600]; snprintf(path, sizeof(path), "%s/.landstalker_dither", h ? h : ".");
    FILE *f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", lk_dd_mode); fclose(f); }
}
void platform_display_cycle_dither(void) {
    if (!lk_dd_loaded) lk_dd_load();
    lk_dd_mode = (lk_dd_mode + 1) % 4; lk_dd_save();
    snprintf(lk_osd_text, sizeof(lk_osd_text), "DE-DITHER: %s", lk_dd_names[lk_dd_mode]); lk_osd_frames = 100;
}
static void lk_disp_save(void) {
    char path[600]; lk_disp_path(path, sizeof(path));
    extern int lk_wide_e; FILE *f = fopen(path, "w"); if (f) { fprintf(f, "%d %d %d\n", lk_scale_mode, lk_fx_mode, lk_wide_e); fclose(f); }   /* third number = widescreen margin per side (read by vdp_render.c when LANDSTALKER_WIDE is not set) */
}
void platform_display_cycle_scale(void) {
    if (!lk_disp_loaded) lk_disp_load();
    lk_scale_mode = (lk_scale_mode + 1) % LK_SC_N; lk_disp_save();
    snprintf(lk_osd_text, sizeof(lk_osd_text), "SCALE: %s", lk_scale_names[lk_scale_mode]); lk_osd_frames = 100;
}
extern int lk_wide_refill;
extern void lk_wide_refresh(void);
void platform_display_cycle_wide(void) {
    extern int lk_wide_e; static const int steps[4] = { 0, 16, 32, 48 }; int i = 0, old = lk_wide_e;
    for (int j = 0; j < 4; j++) if (steps[j] == lk_wide_e) i = j;
    lk_wide_e = steps[(i + 1) % 4]; lk_wide_refresh();
    if (lk_wide_e > old) lk_wide_refill = 1;   /* load the new outer ring of the map as soon as a map frame runs */
    lk_disp_save();
    snprintf(lk_osd_text, sizeof(lk_osd_text), "WIDE: %d PX", 320 + 2 * lk_wide_e); lk_osd_frames = 100;
}
void platform_display_cycle_filter(void) {
    if (!lk_disp_loaded) lk_disp_load();
    lk_fx_mode = (lk_fx_mode + 1) % LK_FX_N; lk_disp_save();
    snprintf(lk_osd_text, sizeof(lk_osd_text), "FILTER: %s", lk_fx_names[lk_fx_mode]); lk_osd_frames = 100;
}
extern int lk_eq_is_held(void);
extern int lk_quick_icon_rgb(int id, int i);
extern uint8_t bus_read8(uint32_t addr);
static int lk_eq_flash_cat = -1, lk_eq_flash_frames;
void lk_osd_equip_flash(int cat) { lk_eq_flash_cat = cat; lk_eq_flash_frames = 60; }
extern uint8_t lk_eq_own[16];
static void lk_eq_text(int x, int y, const char *t, int sc, int r, int g, int b) {   /* small text with the game's glyphs, sc = pixel size */
    SDL_SetRenderDrawColor(s_renderer, r, g, b, 255);
    for (int i = 0; t[i]; i++) { const uint8_t *gl = lk_glyph(t[i]); for (int rr = 0; rr < 7; rr++) for (int c = 0; c < 5; c++) if (gl[rr] & (0x10 >> c)) { SDL_Rect d = { x + (i * 6 + c) * sc, y + rr * sc, sc, sc }; SDL_RenderFillRect(s_renderer, &d); } }
}
static void lk_eq_icon(int id, int x, int y, int ip, int dim) {
    int any = 0;
    for (int i = 0; i < 256; i++) { int rgb = lk_quick_icon_rgb(id, i); if (rgb < 0) continue; any = 1;
        int r = (rgb >> 16) & 255, g = (rgb >> 8) & 255, b = rgb & 255; if (dim) { r = r / 4 + 20; g = g / 4 + 20; b = b / 4 + 20; }
        SDL_SetRenderDrawColor(s_renderer, r, g, b, 255); SDL_Rect d = { x + (i & 15) * ip, y + (i >> 4) * ip, ip, ip }; SDL_RenderFillRect(s_renderer, &d); }
    if (!any) lk_eq_text(x + 5 * ip, y + 4 * ip, "?", ip * 2, 200, 200, 200);
}
static void lk_eq_frame(SDL_Rect c, int t, int r, int g, int b) {
    SDL_SetRenderDrawColor(s_renderer, r, g, b, 255);
    SDL_Rect b1 = { c.x, c.y, c.w, t }, b2 = { c.x, c.y + c.h - t, c.w, t }, b3 = { c.x, c.y, t, c.h }, b4 = { c.x + c.w - t, c.y, t, c.h };
    SDL_RenderFillRect(s_renderer, &b1); SDL_RenderFillRect(s_renderer, &b2); SDL_RenderFillRect(s_renderer, &b3); SDL_RenderFillRect(s_renderer, &b4);
}
static void lk_eq_overlay(int ow, int oh) {   /* Quick Equip held: the four kinds in a cross (up sword, right armour, down boots, left ring) with the icon + name of what Nigel wears; the kind just changed is framed and its four pieces are shown in a strip (current framed, not owned greyed) */
    static const int cx[4] = { 1, 2, 1, 0 }, cy[4] = { 0, 1, 2, 1 }; static const char *lt = "SABR";
    static const char *nm[4][4] = { { "MAGIC", "THUNDER", "ICE", "GAIA" }, { "STEEL", "CHROME", "SHELL", "HYPER" }, { "HEALING", "FIREPROOF", "IRON", "SPIKE" }, { "SATURN", "MARS", "MOON", "VENUS" } };
    static const uint8_t lay[4][4] = { { 1, 3, 2, 4 }, { 9, 10, 11, 12 }, { 7, 5, 6, 8 }, { 15, 13, 14, 16 } };
    int ip = oh / 200; if (ip < 2) ip = 2;
    int cw = 26 * ip, ch = 24 * ip, px = oh / 120; if (px < 2) px = 2; int ts = ip > 3 ? ip / 2 : 1;   /* text pixel size */
    int m = 2 * px, bh = 9 * px, x0 = m, y0 = oh - bh - 2 * m - 3 * ch - m;
    SDL_SetRenderDrawBlendMode(s_renderer, SDL_BLENDMODE_BLEND);
    for (int k = 0; k < 4; k++) {
        SDL_Rect cell = { x0 + cx[k] * cw, y0 + cy[k] * ch, cw, ch };
        int id = bus_read8(0xFF114Eu + (uint32_t)k), hl = (k == lk_eq_flash_cat && lk_eq_flash_frames > 0), idx = -1;
        for (int q = 0; q < 4; q++) if (lay[k][q] == id) idx = q;
        SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 200); SDL_RenderFillRect(s_renderer, &cell);
        lk_eq_frame(cell, ip, hl ? 255 : 110, hl ? 220 : 110, hl ? 60 : 110);
        { int any = 0; for (int i = 0; i < 256 && !any; i++) if (lk_quick_icon_rgb(id, i) >= 0) any = 1;
          if (any) lk_eq_icon(id, cell.x + (cw - 16 * ip) / 2, cell.y + ip, ip, 0); else lk_eq_text(cell.x + (cw - 6 * ts) / 2, cell.y + 4 * ip, (char[]){ lt[k], 0 }, ip, 255, 255, 255); }
        if (idx >= 0) { int n = (int)strlen(nm[k][idx]); lk_eq_text(cell.x + (cw - n * 6 * ts) / 2, cell.y + ch - 9 * ts, nm[k][idx], ts, 230, 230, 230); }
    }
    if (lk_eq_flash_cat >= 0 && lk_eq_flash_frames > 0) {   /* candidate strip of the changed kind, right of the cross */
        int k = lk_eq_flash_cat, sx = x0 + 3 * cw + 2 * m, sy = y0 + cy[k] * ch, sw = 20 * ip;
        for (int q = 0; q < 4; q++) {
            SDL_Rect c = { sx + q * (sw + ip), sy, sw, ch }; int id = lay[k][q], own = lk_eq_own[k * 4 + q], cur = (bus_read8(0xFF114Eu + (uint32_t)k) == id);
            SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 200); SDL_RenderFillRect(s_renderer, &c);
            lk_eq_frame(c, ip, cur ? 255 : 80, cur ? 220 : 80, cur ? 60 : 80);
            lk_eq_icon(id, c.x + (sw - 16 * ip) / 2, c.y + ip, ip, !own);
            { int n = (int)strlen(nm[k][q]); int sc = n * 6 * ts > sw ? 1 : ts; lk_eq_text(c.x + (sw - n * 6 * sc) / 2, c.y + ch - 9 * ts, nm[k][q], sc, own ? 230 : 110, own ? 230 : 110, own ? 230 : 110); }
        }
    }
    (void)ow;
}
static void lk_osd_draw2(int ow, int oh);
static void lk_win_shot(int ow, int oh) {   /* test aid LANDSTALKER_WINSHOT=frame[,frame]: the window picture with the on-screen hints / overlays (BMP) */
    static const char *e; static int init; extern long platform_frame_number(void); char key[40], l[200];
    if (!init) { init = 1; e = getenv("LANDSTALKER_WINSHOT"); }
    if (!e) return;
    snprintf(l, sizeof l, ",%s,", e); snprintf(key, sizeof key, ",%ld,", platform_frame_number());
    if (strstr(l, key)) { SDL_Surface *sf = SDL_CreateRGBSurfaceWithFormat(0, ow, oh, 32, SDL_PIXELFORMAT_ARGB8888); if (sf) { char pth[300]; SDL_RenderReadPixels(s_renderer, NULL, SDL_PIXELFORMAT_ARGB8888, sf->pixels, sf->pitch); snprintf(pth, sizeof pth, "%s/winshot_%ld.bmp", getenv("LANDSTALKER_WINSHOT_DIR") ? getenv("LANDSTALKER_WINSHOT_DIR") : ".", platform_frame_number()); SDL_SaveBMP(sf, pth); SDL_FreeSurface(sf); } }
}
static void lk_osd_draw(int ow, int oh) {
    lk_osd_draw2(ow, oh); lk_win_shot(ow, oh);
}
static void lk_osd_draw2(int ow, int oh) {
    if (lk_eq_flash_frames > 0) lk_eq_flash_frames--;
    if (lk_eq_is_held()) lk_eq_overlay(ow, oh);
    if (lk_osd_frames <= 0) return;
    lk_osd_frames--;
    int px = oh / 120; if (px < 2) px = 2;
    int n = (int)strlen(lk_osd_text), bw = (n * 6 + 1) * px, bh = 9 * px, m = 2 * px;
    int oy = oh - bh - m;   /* bottom left (user 2026-10-24: the top left was over the HUD) */
    SDL_Rect box = { m, oy, bw, bh };
    SDL_SetRenderDrawBlendMode(s_renderer, SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 190); SDL_RenderFillRect(s_renderer, &box);
    SDL_SetRenderDrawColor(s_renderer, 255, 255, 255, 255);
    for (int i = 0; i < n; i++) {
        const uint8_t *g = lk_glyph(lk_osd_text[i]);
        for (int r = 0; r < 7; r++) for (int c = 0; c < 5; c++)
            if (g[r] & (0x10 >> c)) { SDL_Rect d = { m + px + (i * 6 + c) * px, oy + px + r * px, px, px }; SDL_RenderFillRect(s_renderer, &d); }
    }
    (void)ow;
}
/* the CRT filter runs on up to 4 threads (bands of destination rows); one thread is the caller itself */
typedef struct { const uint32_t *src; uint32_t *dst; int dw, sw, y0, y1, mode; } lk_fx_job;   /* mode 0 = CRT/scanline filter, 1 = exact sharp-bilinear, 2 / 3 = CRT PRO / CURVED horizontal pass (source rows) / vertical pass (destination rows) */
static int lk_fx_job_run(void *p) { lk_fx_job *j = (lk_fx_job *)p; if (j->mode == 2) lk_f2_hrows(j->src, j->sw, j->y0, j->y1); else if (j->mode == 3) lk_f2_vrows(j->dst, j->y0, j->y1); else if (j->mode) lk_sb_render_rows(j->src, j->dst, j->dw, j->sw, j->y0, j->y1); else lk_fx_render_rows(j->src, j->dst, j->dw, j->sw, j->y0, j->y1); return 0; }
static void lk_fx_render_mt(const uint32_t *src, uint32_t *dst, int dw, int dh, int sw, int mode) {
    static int nt;
    if (!nt) { nt = SDL_GetCPUCount(); if (nt > 4) nt = 4; if (nt < 1) nt = 1; if (getenv("LANDSTALKER_FXTHREADS")) nt = atoi(getenv("LANDSTALKER_FXTHREADS")); if (nt < 1) nt = 1; if (nt > 8) nt = 8; }
    lk_fx_job job[8]; SDL_Thread *th[8] = { 0 };
    for (int i = 0; i < nt; i++) { job[i].src = src; job[i].dst = dst; job[i].dw = dw; job[i].sw = sw; job[i].mode = mode; job[i].y0 = dh * i / nt; job[i].y1 = dh * (i + 1) / nt; }
    for (int i = 1; i < nt; i++) { th[i] = SDL_CreateThread(lk_fx_job_run, "lkfx", &job[i]); if (!th[i]) lk_fx_job_run(&job[i]); }
    lk_fx_job_run(&job[0]);
    for (int i = 1; i < nt; i++) if (th[i]) SDL_WaitThread(th[i], NULL);
}
/* de-dither on several threads: bands of source rows */
typedef struct { void (*fn)(void *, int, int); void *ctx; int i, nt; } lk_dd_job;   /* thread i takes the 8-row chunks i, i + nt, ... (busy and empty rows are spread evenly) */
static int lk_dd_job_run(void *p) { lk_dd_job *j = (lk_dd_job *)p; for (int y = j->i * 8; y < LK_SRC_H; y += 8 * j->nt) j->fn(j->ctx, y, y + 8 > LK_SRC_H ? LK_SRC_H : y + 8); return 0; }
static void lk_dd_par_run(void (*fn)(void *, int, int), void *ctx) {
    static int nt;
    if (!nt) { nt = SDL_GetCPUCount(); if (nt > 4) nt = 4; if (nt < 1) nt = 1; if (getenv("LANDSTALKER_FXTHREADS")) nt = atoi(getenv("LANDSTALKER_FXTHREADS")); if (nt < 1) nt = 1; if (nt > 8) nt = 8; }
    lk_dd_job job[8]; SDL_Thread *th[8] = { 0 };
    for (int i = 0; i < nt; i++) { job[i].fn = fn; job[i].ctx = ctx; job[i].i = i; job[i].nt = nt; }
    for (int i = 1; i < nt; i++) { th[i] = SDL_CreateThread(lk_dd_job_run, "lkdd", &job[i]); if (!th[i]) lk_dd_job_run(&job[i]); }
    lk_dd_job_run(&job[0]);
    for (int i = 1; i < nt; i++) if (th[i]) SDL_WaitThread(th[i], NULL);
}
/* draw the frame: returns after SDL_RenderPresent */
static void lk_disp_present(const uint8_t *framebuffer) {
    if (!lk_disp_loaded) lk_disp_load();
    int ow = 0, oh = 0; SDL_GetRendererOutputSize(s_renderer, &ow, &oh);
    extern int lk_wide_e;                               /* LANDSTALKER_WIDE (vdp_render.c): extra pixels per side */
    const int sw = LK_SRC_W + 2 * lk_wide_e;
    if (!lk_dd_loaded) lk_dd_load();
    if (lk_dd_mode) {                                   /* de-dither the 320 / 352 / .. x 224 picture before any scaling or filter */
        lk_dd_par = lk_dd_par_run;
        if (lk_dd_cap < sw * LK_SRC_H) { free(lk_dd_buf); lk_dd_buf = (uint32_t *)malloc((size_t)sw * LK_SRC_H * 4); lk_dd_cap = lk_dd_buf ? sw * LK_SRC_H : 0; }
        if (lk_dd_buf) { if (lk_dd_mode == 3) lk_dedither_blend((const uint32_t *)framebuffer, lk_dd_buf, sw); else if (lk_dd_mode == 2) lk_dedither_strong((const uint32_t *)framebuffer, lk_dd_buf, sw); else lk_dedither((const uint32_t *)framebuffer, lk_dd_buf, sw); framebuffer = (const uint8_t *)lk_dd_buf; }
    }
    lk_rect r; lk_calc_rect(lk_scale_mode, ow, oh, sw, &r);
    SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 255);
    SDL_RenderClear(s_renderer);
    static int lk_sb_env = -1; if (lk_sb_env < 0) { const char *e = getenv("LANDSTALKER_SHARP"); lk_sb_env = !(e && *e == '0'); }
    const int lk_sb_cpu = lk_sb_env && !((r.w % sw == 0) && (r.h % LK_SRC_H == 0));   /* sharp-bilinear needed: filter off and not an exact integer scale */
    if ((lk_fx_mode != LK_FX_OFF || lk_sb_cpu) && r.w <= LK_MAXDIM && r.h <= LK_MAXDIM && r.w >= LK_SRC_W && r.h >= LK_SRC_H) {
        if (!lk_fx_tex || lk_fx_tw != r.w || lk_fx_th != r.h) {
            if (lk_fx_tex) SDL_DestroyTexture(lk_fx_tex);
            free(lk_fx_buf);
            lk_fx_tex = SDL_CreateTexture(s_renderer, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STREAMING, r.w, r.h);   /* same as the window texture (build.sh switches it from RGBX8888): the core writes 0xFFRRGGBB */
            lk_fx_buf = (uint32_t *)malloc((size_t)r.w * r.h * 4); lk_fx_tw = r.w; lk_fx_th = r.h;
        }
        if (lk_fx_tex && lk_fx_buf) {
            if (lk_fx_mode >= LK_FX_PRO) {
                lk_f2_prepare(r.w, r.h, lk_fx_mode, sw);
                if (lk_f2_plane) { lk_fx_render_mt((const uint32_t *)framebuffer, lk_fx_buf, r.w, LK_SRC_H, sw, 2); lk_fx_render_mt((const uint32_t *)framebuffer, lk_fx_buf, r.w, r.h, sw, 3); }
                else { lk_fx_prepare(r.w, r.h, LK_FX_CRT, sw); lk_fx_render_mt((const uint32_t *)framebuffer, lk_fx_buf, r.w, r.h, sw, 0); }   /* out of memory: plain CRT */
            }
            else if (lk_fx_mode != LK_FX_OFF) { lk_fx_prepare(r.w, r.h, lk_fx_mode, sw); lk_fx_render_mt((const uint32_t *)framebuffer, lk_fx_buf, r.w, r.h, sw, 0); }
            else { lk_sb_prepare(r.w, r.h, sw); lk_fx_render_mt((const uint32_t *)framebuffer, lk_fx_buf, r.w, r.h, sw, 1); }   /* exact sharp-bilinear (filter OFF, non-integer scale) */
            SDL_UpdateTexture(lk_fx_tex, NULL, lk_fx_buf, r.w * 4);
            SDL_Rect d = { r.x, r.y, r.w, r.h }; SDL_RenderCopy(s_renderer, lk_fx_tex, NULL, &d);
        }
    } else {
        SDL_Rect sr = { 0, 0, sw, LK_SRC_H };
        SDL_UpdateTexture(s_texture, &sr, framebuffer, sw * 4);
        SDL_Rect d = { r.x, r.y, r.w, r.h };
        /* SHARP-BILINEAR (2026-10-10): with a non-integer scale (widescreen: 384 px -> 1280 = 3.33x, 416 -> 3.08x) nearest-neighbour makes some source columns 3 and others 4 screen pixels wide;
           while scrolling this pattern runs through the picture as a faint 'wave'. So: scale the picture by a whole factor k with nearest into a render target, then stretch that linearly to the window.
           LANDSTALKER_SHARP=0 switches it off (old nearest look); exact integer scales are never touched. */
        static int lk_sb_mode = -1, lk_sb_k, lk_sb_w; static SDL_Texture *lk_sb_tex;
        if (lk_sb_mode < 0) { const char *e = getenv("LANDSTALKER_SHARP"); lk_sb_mode = !(e && *e == '0'); }
        int lk_exact = (r.w % sw == 0) && (r.h % LK_SRC_H == 0);
        if (lk_sb_mode && !lk_exact) {
            int k = (r.w + sw - 1) / sw, ky = (r.h + LK_SRC_H - 1) / LK_SRC_H; if (ky > k) k = ky; if (k < 2) k = 2; if (k > 6) k = 6;
            if (!lk_sb_tex || lk_sb_k != k || lk_sb_w != sw) {
                if (lk_sb_tex) SDL_DestroyTexture(lk_sb_tex);
                lk_sb_tex = SDL_CreateTexture(s_renderer, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_TARGET, sw * k, LK_SRC_H * k);
                if (lk_sb_tex) SDL_SetTextureScaleMode(lk_sb_tex, SDL_ScaleModeLinear);
                SDL_SetTextureScaleMode(s_texture, SDL_ScaleModeNearest);
                lk_sb_k = k; lk_sb_w = sw;
            }
            if (lk_sb_tex && SDL_SetRenderTarget(s_renderer, lk_sb_tex) == 0) {
                SDL_RenderCopy(s_renderer, s_texture, &sr, NULL);
                SDL_SetRenderTarget(s_renderer, NULL);
                SDL_RenderCopy(s_renderer, lk_sb_tex, NULL, &d);
            } else { SDL_SetRenderTarget(s_renderer, NULL); SDL_RenderCopy(s_renderer, s_texture, &sr, &d); }
        } else SDL_RenderCopy(s_renderer, s_texture, &sr, &d);
    }
    lk_osd_draw(ow, oh);
    SDL_RenderPresent(s_renderer);
}

'''

a = "void platform_present_frame(const uint8_t *framebuffer) {\n"
assert s.count(a) == 1, "platform_sdl.c: platform_present_frame layout changed"
s = s.replace(a, PURE + SDLPART + a, 1)

b = "    SDL_UpdateTexture(s_texture, NULL, framebuffer, GEN_RENDER_WIDTH * 4);\n    SDL_RenderClear(s_renderer);\n    SDL_RenderCopy(s_renderer, s_texture, NULL, NULL);\n    SDL_RenderPresent(s_renderer);\n"
assert s.count(b) == 1, "platform_sdl.c: present block layout changed"
s = s.replace(b, "    lk_disp_present(framebuffer);\n", 1)

tx = "        SDL_TEXTUREACCESS_STREAMING,\n        GEN_RENDER_WIDTH, GEN_RENDER_HEIGHT);\n"
assert s.count(tx) == 1, "platform_sdl.c: texture creation layout changed"
s = s.replace(tx, "        SDL_TEXTUREACCESS_STREAMING,\n        GEN_RENDER_WIDTH + 128, GEN_RENDER_HEIGHT);   /* LANDSTALKER_WIDE: room for up to 448 px */\n", 1)
c = "    SDL_RenderSetLogicalSize(s_renderer, GEN_RENDER_WIDTH, GEN_RENDER_HEIGHT);\n"
assert s.count(c) == 1, "platform_sdl.c: logical size layout changed"
s = s.replace(c, "    /* LANDSTALKER_DISPLAY: no logical size, lk_disp_present() computes the destination rectangle */\n", 1)

d = "        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_ESCAPE) return false;\n"
assert s.count(d) == 1, "platform_sdl.c: poll events layout changed"
s = s.replace(d, d + "        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F1) platform_display_cycle_scale();\n        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F2) platform_display_cycle_filter();\n        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F3) platform_display_cycle_wide();\n        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F6) platform_display_cycle_dither();\n", 1)

if "#include <stdlib.h>" not in s:
    s = s.replace("#include <string.h>", "#include <string.h>\n#include <stdlib.h>", 1)
if "#include <math.h>" not in s:
    s = s.replace("#include <string.h>", "#include <string.h>\n#include <math.h>", 1)
open(p, "w").write(s)
print("platform_sdl.c patched: LANDSTALKER_DISPLAY")
