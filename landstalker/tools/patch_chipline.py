#!/usr/bin/env python3
"""The old renderer's line work off (docs/SOUND_PLAN.md section 14, step 5 of the way off the emulator).  Step 5.1 (marker LK_CHIPLINE v1, default since v2):
when our renderer draws the picture (own renderer On, LK_NOCHIP, no HD tile pack), GPGX's render_line skips its line extras that only
fill the chip's line buffer (widescreen margins, transparent text box composition, left column / border blanking) and remap_line skips the
copy of that buffer into the picture: the row is filled with one colour instead (magenta with LANDSTALKER_CHIPLINE_MARK=1, a test aid:
every pixel our renderer does not draw shows up in a screenshot).  Env LANDSTALKER_CHIPLINE: unset / 0 = off (default since v2,
2026-11-01: screenshots of all 74 recordings every 300 frames + the 8 Map Behind Text recordings every 20 frames identical, timebench
IDENTICAL incl. the time trace), 1 = GPGX's line work as before (rollback).  Idempotent.  usage: patch_chipline.py path/to/genrecomp   (after patch_own.py,
patch_wide.py, patch_tbox.py, patch_shadow.py).
Step 5.2 (LK_CHIPLINE v3): parse_satb_m5 -> only the sprite overflow status from our SAT cache (LANDSTALKER_SPRSTAT=own|gpgx|check);
v4: per-line sprite counts, rebuilt only when the SAT cache / width changed."""
import os, sys
core = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core")
VER = "LK_CHIPLINE v4"
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
# step 5.2 (v3): the sprite overflow status (bit 6) from our SAT cache; GPGX's object list is skipped (render_obj does not run)
PS = "void parse_satb_m5(int line)\n{\n"
rep(PS, """/* %s step 5.2: parse_satb_m5's only effect that is still used when our renderer draws = the sprite overflow flag (status bit 6):
   more than MODE5_MAX_SPRITES_PER_LINE sprites on the next line.  Same walk as GPGX (y / size / link from the internal SAT cache), from our
   copy lk_sat16 (tools/lkvdp.c).  LANDSTALKER_SPRSTAT: unset / own = ours when our VDP path + our line work run, gpgx = GPGX's parse,
   check = GPGX's parse, then ours compared (status bit 6 + the cache words it read); summary on stderr at exit. */
extern uint16 lk_sat16[0x200]; extern int lk_vdp_ownmem; static int lk_cl_off(void);
static int lk_ss_mode = -1; static unsigned long long lk_ss_n, lk_ss_bad, lk_ss_ovf;
static void lk_ss_report(void) { const char *fn = getenv("LANDSTALKER_SPRSTAT_LOG"), *sc = getenv("GENRECOMP_INPUTSCRIPT"); FILE *f; fprintf(stderr, "sprstat check: parses=%%llu overflows=%%llu mismatches=%%llu\\n", lk_ss_n, lk_ss_ovf, lk_ss_bad); if (fn && (f = fopen(fn, "a"))) { fprintf(f, "%%s parses=%%llu overflows=%%llu mismatches=%%llu\\n", sc ? (strrchr(sc, '/') ? strrchr(sc, '/') + 1 : sc) : "-", lk_ss_n, lk_ss_ovf, lk_ss_bad); fclose(f); } }
static uint8 lk_ss_cnt[512]; static int lk_ss_vw = -1, lk_ss_tot = -1; extern int lk_sat_dirty;
static void lk_ss_build(void)   /* visible sprites per line position (y + 0x81 space) along the link chain, at most max_sprite_pixels / 4 entries, as GPGX walks it */
{
  int link = 0, total = max_sprite_pixels >> 2, y, h, k;
  memset(lk_ss_cnt, 0, sizeof lk_ss_cnt);
  do
  {
    y = lk_sat16[link] & 0x1FF; h = 8 + (((lk_sat16[link + 1] >> 8) & 3) << 3);
    for (k = 0; k < h && y + k < 512; k++) if (lk_ss_cnt[y + k] < 255) lk_ss_cnt[y + k]++;
    link = (lk_sat16[link + 1] & 0x7F) << 2;
    if ((link == 0) || (link >= bitmap.viewport.w)) break;
  }
  while (--total);
  lk_sat_dirty = 0; lk_ss_vw = bitmap.viewport.w; lk_ss_tot = max_sprite_pixels;
}
static int lk_spr_ovf(int line)   /* 1 = overflow on the line after `line`: more visible sprites than MODE5_MAX_SPRITES_PER_LINE (rebuilt only when the SAT cache or the width changed) */
{
  int L = line + 0x81;
  if (lk_sat_dirty || lk_ss_vw != bitmap.viewport.w || lk_ss_tot != max_sprite_pixels) lk_ss_build();
  return L >= 0 && L < 512 && lk_ss_cnt[L] > MODE5_MAX_SPRITES_PER_LINE;
}
""" % VER + PS + """  if (lk_ss_mode < 0) { const char *e = getenv("LANDSTALKER_SPRSTAT"); lk_ss_mode = (e && !strcmp(e, "gpgx")) ? 0 : (e && !strcmp(e, "check")) ? 2 : 1; if (lk_ss_mode == 2) atexit(lk_ss_report); }
  if (lk_ss_mode == 1 && lk_vdp_ownmem && lk_cl_off()) { if (lk_spr_ovf(line)) status |= 0x40; return; }   /* %s */
  if (lk_ss_mode == 2 && lk_vdp_ownmem)
  {
    static int nest; uint16 s0 = status; int o, i, cb = 0;
    if (!nest)
    {
      nest = 1; parse_satb_m5(line); nest = 0;
      o = lk_spr_ovf(line); lk_ss_n++; lk_ss_ovf += o;
      for (i = 0; i < 0x200; i++) if (lk_sat16[i] != *(uint16 *)&sat[i << 1]) { cb = 1; break; }
      if (((status & 0x40) != ((s0 & 0x40) | (o ? 0x40 : 0))) || cb) { if (lk_ss_bad++ < 10) fprintf(stderr, "sprstat check: MISMATCH line %%d status %%04X->%%04X ours %%d cache %%s\\n", line, s0, status, o, cb ? "differs" : "same"); }
      return;
    }
  }
""" % VER)
open(p, "w").write(s)
print("vdp_render.c patched:", VER)
