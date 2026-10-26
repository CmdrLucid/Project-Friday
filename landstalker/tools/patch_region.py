#!/usr/bin/env python3
"""Region (2026-10-26, Europe ROM test): the core auto-detects the region from the ROM header; a Europe ROM ('E') became PAL (50 Hz, 313 lines, 882 audio samples per frame)
while the platform layer paces 60 frames per second -> music and game ran 20 % too fast.  Now the core is forced to NTSC (region USA, 60 Hz) for every ROM
(identical to the auto-detect result for the US ROM).  LANDSTALKER_PAL=1 keeps the auto-detect (test aid).  Idempotent.  usage: patch_region.py path/to/genrecomp"""
import os, sys
p = os.path.join(sys.argv[1], "src/osd.c")
s = open(p).read()
if "LK_REGION" in s:
    print("osd.c already patched: LK_REGION"); sys.exit(0)
old = "    config.region_detect = 0;       /* 0 = auto-detect */\n"
assert s.count(old) == 1, "osd.c: config.region_detect layout changed"
new = "    { extern char *getenv(const char *); const char *lk_pal = getenv(\"LANDSTALKER_PAL\"); config.region_detect = (lk_pal && *lk_pal && *lk_pal != '0') ? 0 : 1; }   /* LK_REGION v1 (tools/patch_region.py): 1 = USA / NTSC 60 Hz for every ROM, LANDSTALKER_PAL=1 = auto-detect */\n"
open(p, "w").write(s.replace(old, new, 1))
print("osd.c patched: LK_REGION")
