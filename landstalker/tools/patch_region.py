#!/usr/bin/env python3
"""Video standard (2026-10-26, Europe ROM test): the core auto-detects the region from the ROM header; a Europe ROM ('E') became PAL (50 Hz, 313 lines, 882 audio samples per frame)
while the platform layer paces 60 frames per second -> music and game ran 20 % too fast.  First try (region forced to USA) showed the ROM's own RegionCheck ($11EA64:
'developed for use only with PAL and French SECAM Mega Drive systems'), because the version register ($A10001) lost its PAL bit.  Now only the VIDEO STANDARD is forced to
NTSC / 60 Hz (config.vdp_mode = 1) and the master clock to NTSC (config.master_clock = 1: otherwise the sound chips run on the PAL clock, ~0.9 % lower pitch); the region stays auto-detected, so the version register still says 'Europe' and the ROM's check passes.
Identical to the auto-detect result for the US ROM.  LANDSTALKER_PAL=1 keeps the auto-detect video standard (test aid).  Idempotent.  usage: patch_region.py path/to/genrecomp"""
import os, sys
p = os.path.join(sys.argv[1], "src/osd.c")
s = open(p).read()
if "LK_REGION" in s:
    print("osd.c already patched: LK_REGION"); sys.exit(0)
old = "    config.vdp_mode      = 0;       /* 0 = auto-detect */\n"
assert s.count(old) == 1, "osd.c: config.vdp_mode layout changed"
old2 = "    config.master_clock  = 0;       /* 0 = auto-detect */\n"
assert s.count(old2) == 1, "osd.c: config.master_clock layout changed"
s = s.replace(old2, "    config.master_clock  = 0;       /* LK_REGION v3: set together with vdp_mode below */\n", 1)
new = "    { extern char *getenv(const char *); const char *lk_pal = getenv(\"LANDSTALKER_PAL\"); int lk_n = !(lk_pal && *lk_pal && *lk_pal != '0'); config.vdp_mode = lk_n ? 1 : 0; config.master_clock = lk_n ? 1 : 0; }   /* LK_REGION v2 (tools/patch_region.py): video standard NTSC 60 Hz for every ROM, region (version register) stays auto, LANDSTALKER_PAL=1 = auto-detect */\n"
open(p, "w").write(s.replace(old, new, 1))
print("osd.c patched: LK_REGION")
