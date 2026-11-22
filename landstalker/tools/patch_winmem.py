#!/usr/bin/env python3
"""LK_WINMEM v1 (GitHub #25, 2026-11-22): the game window remembers its size and position.
The windowed size / position (and 'maximized') is saved in ~/.landstalker_window ("w h x y maximized") when the game quits and right
before it switches to fullscreen (in fullscreen SDL reports the desktop size, so nothing is saved there); the next start opens the window
with it. A saved position is used only when the window would still lie on a connected display (otherwise centred), the size is clamped
to the display's usable area. LANDSTALKER_WINSIZE (test aid, tools/patch_winsize.py) wins; headless runs have no window and save nothing.
Runs after patch_fullscreen.py and patch_winsize.py. Idempotent.  usage: patch_winmem.py path/to/genrecomp"""
import os, sys
VER = "LK_WINMEM v1"
p = os.path.join(sys.argv[1], "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched:", VER); sys.exit(0)

# 1. helpers before the window creation function: load / save
helpers = r'''/* ---- LK_WINMEM v1: remember the window size / position (tools/patch_winmem.py, GitHub #25) ---- */
static int lk_wm_x = SDL_WINDOWPOS_CENTERED, lk_wm_y = SDL_WINDOWPOS_CENTERED, lk_wm_max;
static void lk_wm_path(char *out, size_t n) { const char *h = getenv("HOME"); snprintf(out, n, "%s/.landstalker_window", h ? h : "."); }
static void lk_wm_load(int *w, int *h) {
    char path[600]; FILE *f; int sw, sh, sx, sy, sm = 0, i, nd;
    { const char *e = getenv("LANDSTALKER_WINSIZE"); if (e && *e) return; }   /* the test aid wins */
    lk_wm_path(path, sizeof(path)); f = fopen(path, "r"); if (!f) return;
    i = fscanf(f, "%d %d %d %d %d", &sw, &sh, &sx, &sy, &sm); fclose(f);
    if (i < 2 || sw < 320 || sh < 224 || sw > 16384 || sh > 16384) return;
    nd = SDL_GetNumVideoDisplays();
    if (i >= 4) for (int d = 0; d < nd; d++) {   /* the saved position only if the window's top left area lies on a display */
        SDL_Rect r; if (SDL_GetDisplayUsableBounds(d, &r) != 0) continue;
        if (sx + 64 > r.x && sx < r.x + r.w - 64 && sy + 32 > r.y && sy < r.y + r.h - 32) {
            if (sw > r.w) sw = r.w; if (sh > r.h) sh = r.h; lk_wm_x = sx; lk_wm_y = sy; break; } }
    if (lk_wm_x == SDL_WINDOWPOS_CENTERED && nd > 0) { SDL_Rect r; if (SDL_GetDisplayUsableBounds(0, &r) == 0) { if (sw > r.w) sw = r.w; if (sh > r.h) sh = r.h; } }
    *w = sw; *h = sh; lk_wm_max = i >= 5 && sm;
}
static void lk_wm_save(void) {   /* only while windowed (not fullscreen, not minimised) */
    char path[600]; FILE *f; int w, h, x, y; Uint32 fl;
    if (!s_window) return;
    fl = SDL_GetWindowFlags(s_window);
    if (fl & (SDL_WINDOW_FULLSCREEN | SDL_WINDOW_FULLSCREEN_DESKTOP | SDL_WINDOW_MINIMIZED | SDL_WINDOW_HIDDEN)) return;
    if (fl & SDL_WINDOW_MAXIMIZED) {   /* keep the last normal size, only mark 'maximized' */
        int ow = 0, oh = 0, ox = 0, oy = 0, om; lk_wm_path(path, sizeof(path)); f = fopen(path, "r");
        if (f) { if (fscanf(f, "%d %d %d %d %d", &ow, &oh, &ox, &oy, &om) < 4) ow = 0; fclose(f); }
        if (ow < 320) { SDL_GetWindowSize(s_window, &ow, &oh); SDL_GetWindowPosition(s_window, &ox, &oy); }
        f = fopen(path, "w"); if (f) { fprintf(f, "%d %d %d %d 1\n", ow, oh, ox, oy); fclose(f); }
        return;
    }
    SDL_GetWindowSize(s_window, &w, &h); SDL_GetWindowPosition(s_window, &x, &y);
    if (w < 320 || h < 224) return;
    lk_wm_path(path, sizeof(path)); f = fopen(path, "w"); if (f) { fprintf(f, "%d %d %d %d 0\n", w, h, x, y); fclose(f); }
}
void lk_wm_save_hook(void) { lk_wm_save(); }
'''
a = "    int w = GEN_RENDER_WIDTH * scale;\n    int h = GEN_RENDER_HEIGHT * scale;\n"
assert s.count(a) == 1, "platform_sdl.c: window size lines changed"
i = s.index(a)
fn = s.rindex("\nbool ", 0, i)   # start of the init function that creates the window
s = s[:fn + 1] + helpers + s[fn + 1:]

# 2. use the saved size / position at creation (after the LANDSTALKER_WINSIZE line of patch_winsize.py)
a2 = "/* LK_WINSIZE v1 test aid */\n"
assert s.count(a2) == 1, "platform_sdl.c: run patch_winsize.py first"
s = s.replace(a2, a2 + "    lk_wm_load(&w, &h);   /* " + VER + " */\n")
a3 = "        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,\n        w, h,\n"
assert s.count(a3) == 1, "platform_sdl.c: SDL_CreateWindow call changed"
k = s.index(a3); s = s[:k] + "        lk_wm_x, lk_wm_y,   /* " + VER + " */\n        w, h,\n" + s[k + len(a3):]
k2 = s.index("SDL_WINDOW_RESIZABLE", k)   # the flags of this SDL_CreateWindow call (patch_gpulight.py may have changed the line)
s = s[:k2] + "SDL_WINDOW_RESIZABLE | (lk_wm_max ? SDL_WINDOW_MAXIMIZED : 0)" + s[k2 + len("SDL_WINDOW_RESIZABLE"):]

# 3. save before going fullscreen and when the game quits
a4 = "    if (s_window) SDL_SetWindowFullscreen(s_window, lk_fsc_on ? SDL_WINDOW_FULLSCREEN_DESKTOP : 0);\n"
assert s.count(a4) == 1, "platform_sdl.c: run patch_fullscreen.py first"
s = s.replace(a4, "    if (lk_fsc_on) { extern void lk_wm_save_hook(void); lk_wm_save_hook(); }   /* " + VER + ": the windowed size before fullscreen */\n" + a4)
a5 = "    if (s_window)   { SDL_DestroyWindow(s_window);     s_window   = NULL; }\n"
assert s.count(a5) == 1, "platform_sdl.c: platform_shutdown changed"
s = s.replace(a5, "    lk_wm_save();   /* " + VER + " */\n" + a5)
open(p, "w").write(s)
print("platform_sdl.c patched:", VER)
