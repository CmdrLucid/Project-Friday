#!/usr/bin/env python3
"""genrecomp: keep the display height/width in step with the VDP registers.

GPGX latches bitmap.viewport.h/w from reg 1 / reg 12 once per frame inside
system_frame_gen(), which genrecomp never runs. Right after reset the viewport is
the 192-line Master System size, so the recompiled build drew only 192 lines (the
bottom of every screen was black) and fired VBlank at line 192 instead of 224.
This applies the latch at the start of each frame and in genrecomp_end_frame().

Run AFTER patch_perline.py.  Idempotent.  usage: patch_viewport.py path/to/genrecomp
"""
import sys, os

root = sys.argv[1]
LATCH = ("if (reg[1] & 0x04) { bitmap.viewport.h = (reg[1] & 0x08) ? 240 : 224; "
         "bitmap.viewport.w = (reg[12] & 0x01) ? 320 : 256; } else { bitmap.viewport.h = 192; }")

def patch(rel, old, new, marker):
    p = os.path.join(root, rel)
    s = open(p).read()
    if marker in s:
        print(rel, "already patched:", marker); return
    assert old in s, f"{rel}: layout changed ({old[:50]!r})"
    open(p, "w").write(s.replace(old, new, 1))
    print(rel, "patched:", marker)

# start of each frame (line 0), before ah is used
patch("src/bus.c",
      "        if (genrecomp_perline()) {\n            int ah = bitmap.viewport.h > 0 ? bitmap.viewport.h : 224;\n",
      "        if (v_counter == 0) { " + LATCH + " /* LANDSTALKER_VIEWPORT */ }\n"
      "        if (genrecomp_perline()) {\n            int ah = bitmap.viewport.h > 0 ? bitmap.viewport.h : 224;\n",
      "LANDSTALKER_VIEWPORT")
# old all-at-once path / present
patch("src/genrecomp.c",
      "    int active_lines = bitmap.viewport.h;",
      "    " + LATCH + " /* LANDSTALKER_VIEWPORT */\n    int active_lines = bitmap.viewport.h;",
      "LANDSTALKER_VIEWPORT")
