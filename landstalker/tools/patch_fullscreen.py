#!/usr/bin/env python3
"""Borderless windowed fullscreen ("fullscreen desktop") on pad L4 (Steam Deck back button = SDL paddle 2), F11 or Alt+Enter.
SDL_WINDOW_FULLSCREEN_DESKTOP keeps the desktop resolution (no mode switch), so toggling is instant; the picture is scaled by the existing
display pipeline (L1 scaling mode, R1 filter). The state is saved in ~/.landstalker_fullscreen (0/1) and restored at the next start;
LANDSTALKER_FULLSCREEN=0|1 wins (headless runs ignore it). Idempotent.  usage: patch_fullscreen.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]

ph = os.path.join(root, "include/genrecomp/platform.h")
s = open(ph).read()
if "platform_display_toggle_fullscreen" not in s:
    a = "void platform_display_toggle_coords(void);"
    assert a in s, "platform.h: run patch_coords.py first"
    s = s.replace(a, a + "\n/* borderless windowed fullscreen (pad L4 / paddle 2, F11, Alt+Enter) */\nvoid platform_display_toggle_fullscreen(void);", 1)
    open(ph, "w").write(s)

pi = os.path.join(root, "src/input.c")
s = open(pi).read()
if "platform_display_toggle_fullscreen" not in s:
    a = "                p1_prev = p1;\n            }\n"
    assert s.count(a) == 1, "input.c: run patch_coords.py first (R4 block)"
    s = s.replace(a, a + "            { /* borderless windowed fullscreen: L4 (Steam Deck back button = SDL paddle 2) */\n                static int p2_prev; int p2 = PB(PADDLE2);\n                if (p2 && !p2_prev) platform_display_toggle_fullscreen();\n                p2_prev = p2;\n            }\n", 1)
    open(pi, "w").write(s)

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if "platform_display_toggle_fullscreen" not in s:
    b = "/* ---- coordinate debug overlay (tools/patch_coords.py) ---- */"
    assert s.count(b) == 1, "platform_sdl.c: run patch_coords.py first"
    s = s.replace(b, r'''/* ---- borderless windowed fullscreen (tools/patch_fullscreen.py) ---- */
static int lk_fsc_on;
static void lk_fsc_path(char *out, size_t n) { const char *h = getenv("HOME"); snprintf(out, n, "%s/.landstalker_fullscreen", h ? h : "."); }
static void lk_fsc_apply(void) {
    if (s_window) SDL_SetWindowFullscreen(s_window, lk_fsc_on ? SDL_WINDOW_FULLSCREEN_DESKTOP : 0);
}
void platform_display_toggle_fullscreen(void) {
    char path[600]; FILE *f;
    lk_fsc_on = !lk_fsc_on; lk_fsc_apply();
    lk_fsc_path(path, sizeof(path)); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", lk_fsc_on); fclose(f); }
    snprintf(lk_osd_text, sizeof(lk_osd_text), "FULLSCREEN: %s", lk_fsc_on ? "ON" : "OFF"); lk_osd_frames = 100;
}
/* called once after the window exists: restore the saved state (env LANDSTALKER_FULLSCREEN wins) */
static void lk_fsc_init(void) {
    const char *e = getenv("LANDSTALKER_FULLSCREEN"); char path[600]; FILE *f; int v = 0;
    if (e && *e) v = atoi(e) != 0;
    else { lk_fsc_path(path, sizeof(path)); f = fopen(path, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } }
    if (v) { lk_fsc_on = 1; lk_fsc_apply(); }
}
''' + b, 1)
    # init after renderer creation
    c = "    s_renderer = SDL_CreateRenderer(s_window, -1,\n        SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);\n"
    assert s.count(c) == 1, "platform_sdl.c: renderer creation layout changed"
    s = s.replace(c, c + "    { extern void lk_fsc_init_hook(void); lk_fsc_init_hook(); }   /* restore fullscreen state (tools/patch_fullscreen.py) */\n", 1)
    # the hook is defined after the helpers (static lk_fsc_init), forward-declared via a wrapper placed right after them
    d = "static void lk_fsc_init(void) {"
    s = s.replace(d, "void lk_fsc_init_hook(void);\n" + d, 1)
    e2 = "/* ---- coordinate debug overlay (tools/patch_coords.py) ---- */"
    s = s.replace(e2, "void lk_fsc_init_hook(void) { lk_fsc_init(); }\n" + e2, 1)
    k = "        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F5) platform_display_toggle_coords();   /* coordinate overlay */\n"
    assert s.count(k) == 1, "platform_sdl.c: F5 handler layout changed (run patch_coords.py first)"
    s = s.replace(k, k + "        if (ev.type == SDL_KEYDOWN && (ev.key.keysym.sym == SDLK_F11 || (ev.key.keysym.sym == SDLK_RETURN && (ev.key.keysym.mod & KMOD_ALT)))) platform_display_toggle_fullscreen();   /* borderless fullscreen */\n", 1)
    open(p, "w").write(s)
    print("platform_sdl.c / input.c patched: borderless fullscreen (L4 / F11 / Alt+Enter)")
else:
    print("platform_sdl.c already patched: fullscreen")
