#!/usr/bin/env python3
"""Fast forward (2026-10-15, user wish): HOLD pad R2 (right trigger) or keyboard Tab = the game runs 2x / 3x / 4x as fast (Options > Gameplay > Fast Forward: Off / 2x / 3x / 4x, file ~/.landstalker_ffwd,
env LANDSTALKER_FFWD=0..3, test aid LANDSTALKER_FFWD_HOLD=1 = as if the button were held). While it is held only every Nth emulated frame is drawn, the audio of the skipped frames is dropped (no chipmunk sound), the frame pacing waits 1/N of a frame, the game itself is
untouched (the emulation just runs without waiting). A hint 'FAST FORWARD 3x' is shown on screen.
The shoulder buttons L1 / R1 / L2 (and the old R2 = full height) no longer trigger display functions: everything of that is in the options menu (the F1..F6 keys and L4 / R4 keep working).
Needs patch_display / patch_wide / patch_tall / patch_options / patch_fullscreen before it.  Idempotent.  usage: patch_ffwd.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_FFWD v1"

ph = os.path.join(root, "include/genrecomp/platform.h")
s = open(ph).read()
if "platform_set_ffwd" not in s:
    a = "void platform_display_cycle_tall(void);"
    assert a in s
    s = s.replace(a, a + "\n/* fast forward: hold (right trigger) */\nvoid platform_set_ffwd(int hold);", 1)
    open(ph, "w").write(s)

pi = os.path.join(root, "src/input.c")
s = open(pi).read()
if VER not in s:
    for old, new in (("if (ls && !ls_prev) platform_display_cycle_scale();", "/* L1: free (scaling is in the options menu) */"),
                     ("if (rs && !rs_prev) platform_display_cycle_filter();", "/* R1: free (filter is in the options menu) */"),
                     ("if (lt && !lt_prev) platform_display_cycle_wide();", "/* L2: free (widescreen is in the options menu) */"),
                     ("if (rt && !rt_prev) platform_display_cycle_tall();", "platform_set_ffwd(rt);   /* LK_FFWD v1: R2 held = fast forward */")):
        assert s.count(old) == 1, "input.c layout changed: " + old
        s = s.replace(old, new, 1)
    open(pi, "w").write(s)
    print("input.c patched:", VER)

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_FFWD v1: fast forward (tools/patch_ffwd.py) ---- */
static int lk_ff_opt = -1, lk_ff_pad, lk_ff_kb;   /* option 0 off, 1 = 2x, 2 = 3x, 3 = 4x; hold flags */
static void lk_ff_path(char *b, size_t n) { const char *h = getenv("HOME"); snprintf(b, n, "%s/.landstalker_ffwd", h ? h : "."); }
static void lk_ff_load(void) {
    char p[512]; FILE *f; const char *e = getenv("LANDSTALKER_FFWD"); lk_ff_opt = 0;   /* default Off (user wish 2026-10-15); Options > Gameplay > Fast Forward turns it on */
    lk_ff_path(p, sizeof p); f = fopen(p, "r"); if (f) { int a; if (fscanf(f, "%d", &a) == 1 && a >= 0 && a < 4) lk_ff_opt = a; fclose(f); }
    if (e && *e) { int a = atoi(e); if (a >= 0 && a < 4) lk_ff_opt = a; }
}
int lk_ffwd_get(void) { if (lk_ff_opt < 0) lk_ff_load(); return lk_ff_opt; }
void lk_ffwd_set(int v) { char p[512]; FILE *f; lk_ffwd_get(); lk_ff_opt = v & 3; lk_ff_path(p, sizeof p); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_ff_opt); fclose(f); } }
void platform_set_ffwd(int hold) { lk_ff_pad = hold ? 1 : 0; }
static int lk_ff_n(void) { static int always = -1; if (always < 0) always = getenv("LANDSTALKER_FFWD_HOLD") != NULL; return ((lk_ff_pad || lk_ff_kb || always) && lk_ffwd_get() > 0) ? lk_ff_opt + 1 : 1; }   /* emulated frames per displayed frame */
'''
    s = s.replace(a, module + a, 1)
    # skip drawing
    b = "    if (!s_texture || !s_renderer) return;\n\n    lk_disp_present(framebuffer);\n}"
    assert s.count(b) == 1, "present layout changed"
    s = s.replace(b, "    if (!s_texture || !s_renderer) return;\n    { int n = lk_ff_n(); if (n > 1) { static int c; snprintf(lk_osd_text, sizeof lk_osd_text, \"FAST FORWARD %dX\", n); lk_osd_frames = 3; if (++c % n) return; } }   /* LK_FFWD v1: draw every Nth frame */\n\n    lk_disp_present(framebuffer);\n}", 1)
    # audio
    c = "void platform_queue_audio(const int16_t *samples, int sample_count) {\n"
    assert s.count(c) == 1
    s = s.replace(c, c + "    if (lk_ff_n() > 1) return;   /* LK_FFWD v1: no audio while fast forwarding */\n", 1)
    # sync
    d = "    uint64_t target = s_frame_start + freq / 60;\n"
    assert s.count(d) == 1
    s = s.replace(d, "    uint64_t target = s_frame_start + freq / (60 * (uint64_t)lk_ff_n());   /* LK_FFWD v1 */\n", 1)
    # keyboard
    k = "        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F6) platform_display_cycle_dither();\n"
    assert s.count(k) == 1
    s = s.replace(k, k + "        if ((ev.type == SDL_KEYDOWN || ev.type == SDL_KEYUP) && ev.key.keysym.sym == SDLK_TAB) lk_ff_kb = ev.type == SDL_KEYDOWN;   /* LK_FFWD v1: Tab held = fast forward */\n", 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)
