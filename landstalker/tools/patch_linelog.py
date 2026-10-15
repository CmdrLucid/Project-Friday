#!/usr/bin/env python3
"""Debug probe (idempotent): GENRECOMP_LINELOG=<frame> prints the VDP register state
used when lines 0,100,207,208,223 of that frame are drawn. Works in genrecomp_ref and
the recompiled build because both draw through GPGX's render_line.
usage: patch_linelog.py path/to/genrecomp
"""
import sys, os
p = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if "GENRECOMP_LINELOG" in s:
    print("vdp_render.c already patched"); sys.exit(0)
old = "void render_line(int line)\n{\n"
assert old in s, "render_line layout changed"
new = old + '''  {
    static const char *e; static int e_init;
    extern long platform_frame_number(void);
    if (!e_init) { e = getenv("GENRECOMP_LINELOG"); e_init = 1; }
    if (e && (line == 0 || line == 100 || line == 207 || line == 208 || line == 223) &&
        platform_frame_number() == atol(e))
      printf("linelog frame %ld line %3d: reg0=%02X reg1=%02X reg2=%02X reg11=%02X reg12=%02X reg13=%02X reg16=%02X reg17=%02X reg18=%02X vs0=%04X h=%d\\n",
             platform_frame_number(), line, reg[0], reg[1], reg[2], reg[11], reg[12], reg[13], reg[16], reg[17], reg[18],
             *(uint16 *)&vsram[0], bitmap.viewport.h);
  }
'''
s = s.replace(old, new, 1)
if "#include <stdlib.h>" not in s:
    s = s.replace('#include "shared.h"', '#include "shared.h"\n#include <stdlib.h>\n#include <stdio.h>', 1)
open(p, "w").write(s)
print("vdp_render.c patched")
