#!/usr/bin/env python3
"""Headless/normal screenshot dump of the final picture (widescreen margins included, display filter/scaling NOT applied).
LANDSTALKER_SHOT=<frame>,<frame>,...   frame numbers as in --frames / GENRECOMP_ASCII (the frame that is just being presented)
LANDSTALKER_SHOT_DIR=<dir>             output folder (default ./shots, created if missing)
LANDSTALKER_SHOT_SCALE=<n>             repeat every pixel n x n times (default 1)
Files: <dir>/shot_<frame, 6 digits>_w<picture width>.png  (width = 320 + 2 * LANDSTALKER_WIDE), one console line per file: "shot: wrote ...".
Works with the recompiled build and with genrecomp_ref (both go through platform_present_frame), with or without --headless.
The pure PNG writer is tools/shot_core.c (tested ROM-free by tools/shottest/run.sh). Idempotent. usage: patch_shot.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if "LANDSTALKER_SHOT" in s:
    print("platform_sdl.c already patched: LANDSTALKER_SHOT"); sys.exit(0)
core = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shot_core.c")).read()
sdl = r'''
/* LANDSTALKER_SHOT: SDL-free side (see tools/patch_shot.py) */
#include <sys/stat.h>
#ifdef _WIN32
#include <direct.h>
#endif
int lk_mkdir(const char *d) {   /* portable: Windows (MinGW) mkdir takes ONE argument; the 2-argument POSIX calls elsewhere in the patches broke the Windows first build (GitHub issue #3, v1.0.0) */
#ifdef _WIN32
    return _mkdir(d);
#else
    return mkdir(d, 0777);
#endif
}
static void lk_shot_frame(const uint8_t *framebuffer, long frame) {
    static const char *list; static int init; static const char *dir; static int scale;
    if (!init) {
        list = getenv("LANDSTALKER_SHOT"); dir = getenv("LANDSTALKER_SHOT_DIR"); const char *sc = getenv("LANDSTALKER_SHOT_SCALE");
        if (!dir || !*dir) dir = "shots"; scale = sc ? atoi(sc) : 1; if (scale < 1) scale = 1; if (scale > 8) scale = 8;
        init = 1;
    }
    { const char *wa = getenv("LANDSTALKER_WIDE_AT");   /* test switch: LANDSTALKER_WIDE_AT=f1,f2,.. presses the widescreen button at those frames (headless test of the run-time switch) */
      if (wa && *wa && lk_shot_wanted(wa, frame)) platform_display_cycle_wide(); }
    if (!list || !*list || !lk_shot_wanted(list, frame)) return;
    extern int lk_wide_e;                               /* LANDSTALKER_WIDE (vdp_render.c) */
    int w = 320 + 2 * lk_wide_e, h = 224; char path[700];
#ifdef _WIN32
    _mkdir(dir);
#else
    mkdir(dir, 0755);
#endif
    snprintf(path, sizeof path, "%s/shot_%06ld_w%d.png", dir, frame, w);
    printf("shot: %s %s (%dx%d, scale %d)\n", lk_shot_png(path, (const uint32_t *)framebuffer, w, h, scale) ? "wrote" : "FAILED", path, w, h, scale);
    fflush(stdout);
}

'''
a = "void platform_present_frame(const uint8_t *framebuffer) {\n"
assert s.count(a) == 1, "platform_sdl.c: platform_present_frame layout changed"
s = s.replace(a, core + sdl + a, 1)
b = "    s_frame_no++;\n    if (s_max_frames && s_frame_no >= s_max_frames) {\n"
assert s.count(b) == 1, "platform_sdl.c: frame counter layout changed"
s = s.replace(b, "    lk_shot_frame(framebuffer, s_frame_no);\n" + b, 1)
open(p, "w").write(s)
print("platform_sdl.c patched: LANDSTALKER_SHOT")
