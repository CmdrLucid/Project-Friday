#!/usr/bin/env python3
"""Optional 'Map Behind Text' (2026-10-17, user wish after the recording rec_20261017_1249; Options > Video > Map Behind Text On / Off, default ON).
In a dialogue the game puts the WINDOW plane over the whole bottom of the screen (reg 18 = $1C: from line 160 the window takes the full line); everything outside the text box is
transparent window pixels on an empty background = black.  With the option on, a window line of a map / dialogue frame is drawn twice by the renderer: once as the game has it
and once with the window plane switched off (plane A, plane B and the sprites as the map would show them); every TRANSPARENT pixel of the window line (colour index 0 = backdrop,
and the blanked widescreen margins) is then taken from the second pass.  The text box (frame, purple, text) stays exactly as it is.  Picture only: the game cannot notice (RAM identical).
Lines 0..23 (the HUD bar and the black strip around it) are never touched.  Not applied on frames that are not the game map (menus, title, picture screens: `lk_map_decide()` of tools/patch_wide.py).
File ~/.landstalker_tbox, env LANDSTALKER_TBOX=0|1 wins (tests).  Needs patch_wide.py before it (lk_map_decide, lk_wide_margins).  Idempotent.
usage: patch_tbox.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_TBOX v1"

p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    a = "void render_line(int line)\n{\n"
    assert s.count(a) == 1 and "int lk_map_decide(void)" in s, "vdp_render.c: run patch_wide.py first"
    module = r'''/* ---- LK_TBOX v1: the map shows through the transparent pixels of the dialogue window (tools/patch_tbox.py) ---- */
static int lk_tbox_v = -1;   /* Options > Video > Map Behind Text Off / On, default On; file ~/.landstalker_tbox, env LANDSTALKER_TBOX=0|1 wins */
int lk_tbox_get(void)
{
  if (lk_tbox_v < 0) { char p[512]; FILE *f; const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_TBOX"); int v = 1; snprintf(p, sizeof p, "%s/.landstalker_tbox", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 1; fclose(f); } if (e && *e) v = atoi(e); lk_tbox_v = v ? 1 : 0; }
  return lk_tbox_v;
}
void lk_tbox_set(int v) { char p[512]; FILE *f; const char *h = getenv("HOME"); lk_tbox_get(); lk_tbox_v = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_tbox", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_tbox_v); fclose(f); } }
static void lk_tbox_line(int line)
{
  int a, w, i, i0, i1;
  uint8 save[sizeof linebuf[0]];
  uint8 r18;
  struct clip_t c0, c1;
  if (!lk_tbox_get()) return;
  if (line < 24) return;   /* the HUD bar rows (5..22) and the strip around them keep their black (user: 'da kann es bleiben') */
  if (getenv("LANDSTALKER_TBOX_DEBUG") && line == 200) fprintf(stderr, "tbox: frame %ld line 200 reg18=%02X reg1=%02X clip1.en=%d map=%d\n", platform_frame_number(), reg[18], reg[1], clip[1].enable, lk_map_decide());
  a = (reg[18] & 0x1F) << 3; w = (reg[18] >> 7) & 1;
  if (w != (line >= a)) return;   /* only lines that belong completely to the window plane */
  if (!lk_map_decide()) return;                      /* map / dialogue frames only */
  memcpy(save, linebuf[0], sizeof save);
  r18 = reg[18]; c0 = clip[0]; c1 = clip[1];
  reg[18] = 0; clip[0].left = 0; clip[0].right = bitmap.viewport.w >> 4; clip[0].enable = 1; clip[1].enable = 0;   /* second pass: plane A takes the whole line */
  render_bg(line);
  render_obj(line & 1);
  reg[18] = r18; clip[0] = c0; clip[1] = c1;
  i0 = 0x20 - bitmap.viewport.x; i1 = 0x20 + bitmap.viewport.w + bitmap.viewport.x;
  /* pixels that stay as the window has them: not transparent and not part of the empty (black) run at the left / right end of the line; the box frame, its fill, the text and sprites on top stay */
  { int lo = i0, hi = i1;
    while (lo < i1 && ((save[lo] & 0x0F) == 0 || (pixel[save[lo]] & 0x00FFFFFF) == 0)) lo++;
    while (hi > lo && ((save[hi - 1] & 0x0F) == 0 || (pixel[save[hi - 1]] & 0x00FFFFFF) == 0)) hi--;
    for (i = i0; i < i1; i++) if (i >= lo && i < hi && (save[i] & 0x0F)) linebuf[0][i] = save[i];
  }
}
'''
    s = s.replace(a, module + a, 1)
    b = "    lk_wide_margins(line);   /* LANDSTALKER_WIDE */\n"
    assert s.count(b) == 1
    s = s.replace(b, b + "    lk_tbox_line(line);   /* LK_TBOX v1 */\n", 1)
    open(p, "w").write(s)
    print("vdp_render.c patched:", VER)
