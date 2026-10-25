#!/usr/bin/env python3
"""Full-height picture (LANDSTALKER_TALL): fill the black band at the bottom of the map screen with the map.
On the map the game's HInt handler ($001184) switches the display OFF from line ~184 (VDP reg 1 = $8124) and uses that extra
blanking time to flush its VDP write queue; the 40 lines below stay black. In dialogues it instead switches the window plane
to full height from line 160 (reg 18 = $1C) and shows the text box there; that path is not touched.
LANDSTALKER_TALL only changes the RENDERER: on a map frame (lk_map_decide(), the widescreen map rule of tools/patch_wide.py)
a line below 160 whose display was switched off DURING the frame (display on at line 0) is drawn as if the display were on.
The game, its registers, timing and DMA are unchanged (it cannot notice). Frames that are blanked from line 0 (fades, room loads)
and non-map screens (title, menus) keep their black band.
Switch: pad R2 (right trigger; was R4 until 2026-10-11) or F4, saved as 4th number in ~/.landstalker_display; LANDSTALKER_TALL=0|1 wins.
LANDSTALKER_TALL_AT=f,f,.. presses the switch at those frames (headless test, also saves the setting).
Independent of LANDSTALKER_WIDE (works at every width). Idempotent.  usage: patch_tall.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]

# ---- core/vdp_render.c -------------------------------------------------------
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if "lk_tall_track" not in s:
    assert "int lk_map_decide(void)" in s, "vdp_render.c: run patch_wide.py first (lk_map_decide)"
    helper = r'''/* LANDSTALKER_TALL: draw the map below the game's HInt display-off line (see tools/patch_tall.py) */
int lk_tall = -1;
static int lk_tall_on0;
static void lk_tall_load(void)
{
  const char *e = getenv("LANDSTALKER_TALL");
  lk_tall = 1;   /* default Full Height On since 2026-10-25; a saved ~/.landstalker_display or LANDSTALKER_TALL wins */
  if (e && *e) lk_tall = atoi(e) != 0;
  else {
    const char *h = getenv("HOME"); char path[600]; int a = 0, b = 0, c = 0, d = 0;
    snprintf(path, sizeof(path), "%s/.landstalker_display", h ? h : ".");
    FILE *f = fopen(path, "r");
    if (f) { if (fscanf(f, "%d %d %d %d", &a, &b, &c, &d) == 4) lk_tall = d != 0; fclose(f); }
  }
}
static inline void lk_tall_track(int line)
{
  if (lk_tall < 0) lk_tall_load();
  if (line == 0) lk_tall_on0 = reg[1] & 0x40;   /* display on at the top of the frame: a later display-off is the HInt band, not a fade/load */
}
/* extra strip-loader steps below the picture (used by lk_strip_extend in func_table.c, tools/patch_wide.py); LANDSTALKER_TALL_STRIPS overrides */
int lk_tall_kv(void)
{
  static int kv = -1;
  if (lk_tall < 0) lk_tall_load();
  if (kv < 0) { const char *c = getenv("LANDSTALKER_TALL_STRIPS"); kv = c && *c ? atoi(c) : 5; if (kv < 0) kv = 0; if (kv > 6) kv = 6; }
  return lk_tall > 0 ? kv : 0;
}
static inline int lk_tall_line(int line)
{
  return lk_tall > 0 && lk_tall_on0 && line >= 160 && lk_map_decide();
}
int lk_tall_keep(int line) { return lk_tall_line(line); }   /* vdp_ctrl.c: no partial blanking of the HInt line (display switched off mid-line) */

'''
    rl = "void render_line(int line)\n{\n"
    assert s.count(rl) == 1, "vdp_render.c: render_line layout changed"
    i = s.index(rl)
    cd = "  /* Check display status */\n  if (reg[1] & 0x40)\n"
    j = s.index(cd, i)
    assert j - i < 2000, "vdp_render.c: display check not near render_line"
    s = s[:j] + "  lk_tall_track(line);   /* LANDSTALKER_TALL */\n  /* Check display status */\n  if ((reg[1] & 0x40) || lk_tall_line(line))   /* LANDSTALKER_TALL */\n" + s[j + len(cd):]
    s = s[:i] + helper + s[i:]
    open(p, "w").write(s)
    print("vdp_render.c patched: LANDSTALKER_TALL")
else:
    print("vdp_render.c already patched: LANDSTALKER_TALL")

# ---- core/vdp_ctrl.c: display switched off in the middle of a line blanks the rest of it (GPGX); at 320 px this lands in HBLANK,
# in a widescreen picture it shows as a black dash in the right margin of line ~184. Keep the line when LANDSTALKER_TALL draws below it.
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_ctrl.c")
s = open(p).read()
if "lk_tall_keep" not in s:
    a = "            else\n            {\n              blank_line(v_counter, offset, bitmap.viewport.w - offset);\n"
    assert s.count(a) == 1, "vdp_ctrl.c: partial blanking layout changed"
    s = s.replace(a, "            else if (!lk_tall_keep(v_counter))   /* LANDSTALKER_TALL */\n            {\n              blank_line(v_counter, offset, bitmap.viewport.w - offset);\n", 1)
    s = s.replace('#include "shared.h"\n', '#include "shared.h"\nextern int lk_tall_keep(int line);   /* LANDSTALKER_TALL (vdp_render.c) */\n', 1)
    assert "extern int lk_tall_keep" in s, "vdp_ctrl.c: include layout changed"
    open(p, "w").write(s)

# ---- band pre-render: the game flushes the queue for the NEXT frame (scroll, tiles) while the display is off; drawing the band lines
# afterwards would show that half-updated next-frame state (tearing / garbage while scrolling). So when the display is switched off
# in the HInt of a map frame, the remaining lines are rendered at once from the state of the picture above.
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if "lk_tall_prerender" not in s:
    a = "static int lk_tall_on0;"
    assert s.count(a) == 1, "vdp_render.c: lk_tall_on0 layout changed"
    s = s.replace(a, "static int lk_tall_on0, lk_tall_pre, lk_tall_pre_from, lk_tall_bursting;   /* pre-render state of this frame */", 1)
    a = "  if (line == 0) lk_tall_on0 = reg[1] & 0x40;"
    assert s.count(a) == 1, "vdp_render.c: lk_tall_track layout changed"
    s = s.replace(a, "  if (line == 0) { lk_tall_on0 = reg[1] & 0x40; lk_tall_pre = 0; }", 1)
    a = "int lk_tall_keep(int line) { return lk_tall_line(line); }"
    assert s.count(a) == 1, "vdp_render.c: lk_tall_keep layout changed"
    s = s.replace(a, a + """
/* vdp_ctrl.c, display switched off at 'line' (reg 1 write): render the rest of the picture now, before the game's queue flush changes VRAM/VSRAM */
void lk_tall_prerender(int line)
{
  int l, saved = v_counter;
  if (lk_tall <= 0 || lk_tall_pre || line + 1 >= bitmap.viewport.h || !lk_tall_line(line + 1)) return;
  lk_tall_pre = 1; lk_tall_pre_from = line + 1; lk_tall_bursting = 1;
  for (l = line + 1; l < bitmap.viewport.h; l++) { v_counter = l; render_line(l); }
  lk_tall_bursting = 0; v_counter = saved;
}
""", 1)
    a = "  lk_tall_track(line);   /* LANDSTALKER_TALL */\n"
    assert s.count(a) == 1, "vdp_render.c: render_line hook layout changed"
    s = s.replace(a, a + "  if (lk_tall_pre && !lk_tall_bursting && line >= lk_tall_pre_from) return;   /* LANDSTALKER_TALL: already drawn by lk_tall_prerender */\n", 1)
    open(p, "w").write(s)
    print("vdp_render.c patched: LANDSTALKER_TALL band pre-render")

p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_ctrl.c")
s = open(p).read()
if "lk_tall_prerender" not in s:
    a = "      /* Display status (modified during active display) */\n"
    assert s.count(a) == 1, "vdp_ctrl.c: display status layout changed"
    s = s.replace(a, "      if ((r & 0x40) && !(d & 0x40) && v_counter < bitmap.viewport.h) lk_tall_prerender(v_counter);   /* LANDSTALKER_TALL */\n" + a, 1)
    s = s.replace("extern int lk_tall_keep(int line);", "extern void lk_tall_prerender(int line);\nextern int lk_tall_keep(int line);", 1)
    assert "extern void lk_tall_prerender" in s
    open(p, "w").write(s)

# ---- platform.h: prototype ------------------------------------------------------
ph = os.path.join(root, "include/genrecomp/platform.h")
s = open(ph).read()
if "platform_display_cycle_tall" not in s:
    a = "void platform_display_cycle_wide(void);"
    assert a in s, "platform.h: run patch_display.py first"
    s = s.replace(a, a + "\n/* LANDSTALKER_TALL run-time switch (pad R2 / right trigger, F4): map in the bottom band on/off */\nvoid platform_display_cycle_tall(void);", 1)
    open(ph, "w").write(s)

# ---- input.c: R2 (right trigger) ------------------------------------------------
pi = os.path.join(root, "src/input.c")
s = open(pi).read()
if "platform_display_cycle_tall" not in s:
    a = "                lt_prev = lt;\n            }\n"
    assert s.count(a) == 1, "input.c: run patch_display.py first (L2 block)"
    s = s.replace(a, a + "            { /* LANDSTALKER_TALL: right trigger (R2) = map in the bottom band on/off */\n                static int rt_prev; int rt = PA(TRIGGERRIGHT) > 16000;\n                if (rt && !rt_prev) platform_display_cycle_tall();\n                rt_prev = rt;\n            }\n", 1)
    open(pi, "w").write(s)

# ---- platform_sdl.c: switch, save, F4, test presses ------------------------------
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if "platform_display_cycle_tall" not in s:
    a = 'fprintf(f, "%d %d %d\\n", lk_scale_mode, lk_fx_mode, lk_wide_e);'
    assert s.count(a) == 1, "platform_sdl.c: settings save layout changed"
    s = s.replace(a, 'extern int lk_tall; fprintf(f, "%d %d %d %d\\n", lk_scale_mode, lk_fx_mode, lk_wide_e, lk_tall > 0);   /* 4th number = LANDSTALKER_TALL */', 1)
    b = "static void lk_osd_draw(int ow, int oh) {"
    assert s.count(b) == 1, "platform_sdl.c: osd layout changed"
    s = s.replace(b, '''void platform_display_cycle_tall(void) {
    extern int lk_tall;
    if (!lk_disp_loaded) lk_disp_load();
    lk_tall = lk_tall > 0 ? 0 : 1; lk_disp_save();
    if (lk_tall) lk_wide_refill = 1;   /* load the band below the picture as soon as a map frame runs (lk_strip_extend) */
    snprintf(lk_osd_text, sizeof(lk_osd_text), "FULL HEIGHT: %s", lk_tall ? "ON" : "OFF"); lk_osd_frames = 100;
}
''' + b, 1)
    k = "        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F3) platform_display_cycle_wide();\n"
    assert s.count(k) == 1, "platform_sdl.c: F3 handler layout changed"
    s = s.replace(k, k + "        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F4) platform_display_cycle_tall();   /* LANDSTALKER_TALL */\n", 1)
    open(p, "w").write(s)
    print("platform_sdl.c / input.c patched: LANDSTALKER_TALL switch (R2 / F4)")
else:
    print("platform_sdl.c already patched: LANDSTALKER_TALL")

# ---- test presses at given frames (headless), next to LANDSTALKER_WIDE_AT -------------
ps = os.path.join(root, "src/platform_sdl.c")
s = open(ps).read()
if "LANDSTALKER_TALL_AT" not in s:
    a = '    { const char *wa = getenv("LANDSTALKER_WIDE_AT");'
    assert s.count(a) == 1, "platform_sdl.c: run patch_shot.py first (LANDSTALKER_WIDE_AT)"
    s = s.replace(a, '''    { const char *ta = getenv("LANDSTALKER_TALL_AT");   /* LANDSTALKER_TALL_AT=f1,f2,.. presses the full-height switch at those frames */
      if (ta) for (const char *q = ta; *q; ) { if (atol(q) == frame) platform_display_cycle_tall(); while (*q && *q != ',') q++; if (*q) q++; } }
''' + a, 1)
    open(ps, "w").write(s)
