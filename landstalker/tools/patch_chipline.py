#!/usr/bin/env python3
"""The old renderer's line work off (docs/SOUND_PLAN.md section 14, step 5 of the way off the emulator).  Step 5.1 (marker LK_CHIPLINE v1, default since v2):
when our renderer draws the picture (own renderer On, LK_NOCHIP, no HD tile pack), GPGX's render_line skips its line extras that only
fill the chip's line buffer (widescreen margins, transparent text box composition, left column / border blanking) and remap_line skips the
copy of that buffer into the picture: the row is filled with one colour instead (magenta with LANDSTALKER_CHIPLINE_MARK=1, a test aid:
every pixel our renderer does not draw shows up in a screenshot).  Env LANDSTALKER_CHIPLINE: unset / 0 = off (default since v2,
2026-11-01: screenshots of all 74 recordings every 300 frames + the 8 Map Behind Text recordings every 20 frames identical, timebench
IDENTICAL incl. the time trace), 1 = GPGX's line work as before (rollback).  Idempotent.  usage: patch_chipline.py path/to/genrecomp   (after patch_own.py,
patch_wide.py, patch_tbox.py, patch_shadow.py)"""
import os, sys
core = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core")
VER = "LK_CHIPLINE v2"
p = os.path.join(core, "vdp_render.c"); s = open(p).read()
if VER in s:
    print("vdp_render.c already patched:", VER); sys.exit(0)

def rep(a, b):
    global s
    assert s.count(a) == 1, f"vdp_render.c layout changed: {a[:70]!r} ({s.count(a)}x)"
    s = s.replace(a, b, 1)

# the switch (defined before render_line: lk_own_get and lk_hd_n are known there)
RL = "void render_line(int line)\n{\n"
rep(RL, """/* %s: 1 = the old renderer's line work is skipped (our renderer draws the line) */
static int lk_cl_mode = -1, lk_cl_mark;
static int lk_cl_off(void)
{
  if (lk_cl_mode < 0)
  {
    const char *e = getenv("LANDSTALKER_CHIPLINE"), *n = getenv("LANDSTALKER_OWN_NOCHIP"), *m = getenv("LANDSTALKER_CHIPLINE_MARK");
    lk_cl_mode = !(e && *e == '1') && !(n && *n == '0');   /* default off since v2 */
    lk_cl_mark = m && *m == '1';
  }
  return lk_cl_mode && !lk_hd_n && lk_own_get();
}

""" % VER + RL)
rep("    lk_wide_margins(line);   /* LANDSTALKER_WIDE */\n    lk_tbox_line(line);   /* LK_TBOX v1 */\n",
    "    if (!lk_cl_off()) {   /* %s */\n    lk_wide_margins(line);   /* LANDSTALKER_WIDE */\n    lk_tbox_line(line);   /* LK_TBOX v1 */\n    }\n" % VER)
rep("      PIXEL_OUT_T *lk_row0 = dst; int lk_w0 = width;   /* LK_SHADOW v7 */\n      do\n      {\n        *dst++ = pixel[*src++];\n      }\n      while (--width);\n",
    "      PIXEL_OUT_T *lk_row0 = dst; int lk_w0 = width;   /* LK_SHADOW v7 */\n"
    "      if (lk_cl_off()) { PIXEL_OUT_T c = lk_cl_mark ? (PIXEL_OUT_T)0xFFFF00FFu : pixel[0x40]; do *dst++ = c; while (--width); } else   /* %s: our renderer draws the row */\n"
    "      do\n      {\n        *dst++ = pixel[*src++];\n      }\n      while (--width);\n" % VER)
open(p, "w").write(s)
print("vdp_render.c patched:", VER)
