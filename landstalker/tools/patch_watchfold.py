#!/usr/bin/env python3
"""genrecomp bus.c: GENRECOMP_WATCH also reports writes through the work-RAM mirrors (idempotent).

Genesis work RAM ($FF0000-$FFFFFF) is mirrored every 64K over $E00000-$FFFFFF. bus_watch() compared the exact address, so a write via
a mirror ($F0FFEA instead of $FFFFEA) was invisible: the win23 watch of the stack slot $FFFFEB showed no zeroing write although the
slot was zero when popped. With this patch both addresses are folded to the low 16 bits when they are in the RAM region.
usage: patch_watchfold.py path/to/genrecomp
"""
import sys, os
p = os.path.join(sys.argv[1], "src/bus.c")
s = open(p).read()
if "LANDSTALKER_WATCHFOLD" in s:
    print("bus.c already patched: LANDSTALKER_WATCHFOLD"); sys.exit(0)
old = "    if (s_watch - addr < (uint32_t)size) {\n"
new = ("    if (s_watch - addr < (uint32_t)size ||\n"
       "        (s_watch != 0xFFFFFFFF && addr >= 0xE00000 && s_watch >= 0xE00000 && ((s_watch - addr) & 0xFFFF) < (uint32_t)size)) { /* LANDSTALKER_WATCHFOLD */\n")
assert old in s, "bus.c: bus_watch layout changed"
open(p, "w").write(s.replace(old, new, 1)); print("bus.c patched: LANDSTALKER_WATCHFOLD")
