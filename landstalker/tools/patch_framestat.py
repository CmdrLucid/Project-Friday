#!/usr/bin/env python3
"""Frame pacing diagnostics for the SDL platform layer (microstutter hunting).
Per frame the platform does: emulation (68K + VDP render + audio mix) -> platform_present_frame (SDL_RenderPresent, blocks for vsync) -> platform_frame_sync
(busy-wait until 1/60 s after the previous frame). Two pacers (vsync + busy-wait at exactly 60.000 Hz while the display/real console run 60.0/59.92 Hz) can beat against
each other and skip a vblank now and then (one 33 ms frame = visible micro stutter).
LANDSTALKER_FRAMESTAT=1  prints once per second:  framestat: n=60 emu avg/max=..ms present avg/max=..ms sync avg/max=..ms frame max=..ms >20ms=N >30ms=N
LANDSTALKER_NOSYNC=1     skips the busy-wait (vsync only) for an A/B test
Idempotent.  usage: patch_framestat.py path/to/genrecomp"""
import os, sys
p = os.path.join(sys.argv[1], "src/platform_sdl.c")
s = open(p).read()
if "LANDSTALKER_FRAMESTAT" in s:
    print("platform_sdl.c already patched: LANDSTALKER_FRAMESTAT"); sys.exit(0)
a = "void platform_present_frame(const uint8_t *framebuffer) {\n"
assert s.count(a) == 1, "platform_sdl.c: platform_present_frame layout changed"
helpers = r'''/* LANDSTALKER_FRAMESTAT: wall-clock frame statistics (see tools/patch_framestat.py) */
static int lk_fs_on = -1, lk_fs_nosync = -1;
static uint64_t lk_fs_pres0, lk_fs_prev_end, lk_fs_win0;
static int lk_fs_havepres, lk_fs_n, lk_fs_gt20, lk_fs_gt30;
static double lk_fs_emu_sum, lk_fs_emu_max, lk_fs_pr_sum, lk_fs_pr_max, lk_fs_sy_sum, lk_fs_sy_max, lk_fs_iv_max;
static double lk_fs_ms(uint64_t a, uint64_t b) { return (double)(b - a) * 1000.0 / (double)SDL_GetPerformanceFrequency(); }
static void lk_fs_init(void) {
    if (lk_fs_on < 0) { lk_fs_on = getenv("LANDSTALKER_FRAMESTAT") != NULL; lk_fs_nosync = getenv("LANDSTALKER_NOSYNC") != NULL; }
}
static void lk_fs_present_begin(void) {
    lk_fs_init();
    if (!lk_fs_on) return;
    uint64_t t = SDL_GetPerformanceCounter();
    if (lk_fs_prev_end) { double e = lk_fs_ms(lk_fs_prev_end, t); lk_fs_emu_sum += e; if (e > lk_fs_emu_max) lk_fs_emu_max = e; }
    lk_fs_pres0 = t; lk_fs_havepres = 1;
}
static uint64_t lk_fs_sync_begin(void) {
    lk_fs_init();
    if (!lk_fs_on) return 0;
    uint64_t t = SDL_GetPerformanceCounter();
    if (lk_fs_havepres) { double d = lk_fs_ms(lk_fs_pres0, t); lk_fs_pr_sum += d; if (d > lk_fs_pr_max) lk_fs_pr_max = d; }
    lk_fs_havepres = 0;
    return t;
}
static void lk_fs_sync_end(uint64_t t0) {
    if (!lk_fs_on || !t0) return;
    uint64_t t = SDL_GetPerformanceCounter();
    double sy = lk_fs_ms(t0, t);
    lk_fs_sy_sum += sy; if (sy > lk_fs_sy_max) lk_fs_sy_max = sy;
    if (lk_fs_prev_end) {
        double iv = lk_fs_ms(lk_fs_prev_end, t);
        if (iv > lk_fs_iv_max) lk_fs_iv_max = iv;
        if (iv > 20.0) lk_fs_gt20++;
        if (iv > 30.0) lk_fs_gt30++;
    }
    lk_fs_prev_end = t; lk_fs_n++;
    if (!lk_fs_win0) lk_fs_win0 = t;
    if (lk_fs_ms(lk_fs_win0, t) >= 1000.0) {
        int n = lk_fs_n ? lk_fs_n : 1;
        printf("framestat: n=%d emu avg/max=%.1f/%.1fms present avg/max=%.1f/%.1fms sync avg/max=%.1f/%.1fms frame max=%.1fms >20ms=%d >30ms=%d%s\n",
               lk_fs_n, lk_fs_emu_sum / n, lk_fs_emu_max, lk_fs_pr_sum / n, lk_fs_pr_max, lk_fs_sy_sum / n, lk_fs_sy_max, lk_fs_iv_max, lk_fs_gt20, lk_fs_gt30,
               lk_fs_nosync ? " (NOSYNC)" : "");
        fflush(stdout);
        lk_fs_win0 = t; lk_fs_n = lk_fs_gt20 = lk_fs_gt30 = 0;
        lk_fs_emu_sum = lk_fs_emu_max = lk_fs_pr_sum = lk_fs_pr_max = lk_fs_sy_sum = lk_fs_sy_max = lk_fs_iv_max = 0;
    }
}

'''
s = s.replace(a, helpers + a + "    lk_fs_present_begin();\n", 1)
b = "    if (s_headless) return;\n    uint64_t now = SDL_GetPerformanceCounter();\n    uint64_t freq = SDL_GetPerformanceFrequency();\n    uint64_t target = s_frame_start + freq / 60;\n\n    while (SDL_GetPerformanceCounter() < target) {\n        SDL_Delay(0);\n    }\n\n    s_frame_start = SDL_GetPerformanceCounter();\n"
assert s.count(b) == 1, "platform_sdl.c: platform_frame_sync layout changed"
nb = "    if (s_headless) return;\n    uint64_t lk_fs_t0 = lk_fs_sync_begin();\n    uint64_t now = SDL_GetPerformanceCounter();\n    uint64_t freq = SDL_GetPerformanceFrequency();\n    uint64_t target = s_frame_start + freq / 60;\n\n    while (!lk_fs_nosync && SDL_GetPerformanceCounter() < target) {\n        SDL_Delay(0);\n    }\n\n    s_frame_start = SDL_GetPerformanceCounter();\n    lk_fs_sync_end(lk_fs_t0);\n"
s = s.replace(b, nb, 1)
open(p, "w").write(s)
print("platform_sdl.c patched: LANDSTALKER_FRAMESTAT")
