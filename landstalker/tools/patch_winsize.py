#!/usr/bin/env python3
"""Test aid LK_WINSIZE v1: LANDSTALKER_WINSIZE=WxH sets the size of the game window at start (e.g. 1920x1080 with LANDSTALKER_HIDDEN=1
for trailer footage: LANDSTALKER_PRESENT_SHOT then writes full-HD pictures of the GPU-lit game). No effect without the env var. Idempotent.
usage: patch_winsize.py path/to/genrecomp"""
import os, sys
VER = "LK_WINSIZE v1"
p = os.path.join(sys.argv[1], "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched:", VER); sys.exit(0)
a = "    int w = GEN_RENDER_WIDTH * scale;\n    int h = GEN_RENDER_HEIGHT * scale;\n"
assert s.count(a) == 1, "platform_sdl.c: window size lines changed"
s = s.replace(a, a + "    { const char *e = getenv(\"LANDSTALKER_WINSIZE\"); int ew, eh; if (e && sscanf(e, \"%%dx%%d\", &ew, &eh) == 2 && ew >= 320 && eh >= 224 && ew <= 7680 && eh <= 4320) { w = ew; h = eh; } }   /* %s test aid */\n" % VER)
open(p, "w").write(s)
print("platform_sdl.c patched:", VER)
