#!/usr/bin/env python3
"""LANDSTALKER_LOCKDISPLAY=1 makes the switches for the widescreen width (pad L2 / F3) and the full height (R2 / F4) do nothing (idempotent).
Widescreen width and full height change the game behaviour slightly (entities in the margins become active earlier), so a recording
(~/Landstalker_Aufnahme.sh) must not change them half way. Must run AFTER patch_wide.py / patch_tall.py (they create the functions).
usage: patch_lockdisplay.py path/to/genrecomp"""
import os, sys
pp = os.path.join(sys.argv[1], "src/platform_sdl.c")
ps = open(pp).read()
if "LANDSTALKER_LOCKDISPLAY" in ps:
    print("platform_sdl.c lockdisplay already patched"); sys.exit(0)
for fn in ("platform_display_cycle_wide", "platform_display_cycle_tall"):
    h = "void %s(void) {\n" % fn
    assert ps.count(h) == 1, "platform_sdl.c layout changed: " + fn
    ps = ps.replace(h, h + "    { const char *lk = getenv(\"LANDSTALKER_LOCKDISPLAY\"); if (lk && *lk == '1') return; }   /* LANDSTALKER_LOCKDISPLAY */\n", 1)
open(pp, "w").write(ps); print("platform_sdl.c patched: LANDSTALKER_LOCKDISPLAY")
