#!/usr/bin/env python3
"""Item Info / option help in the Start menu bar like the start screen (LK_IICENTER v1, 2026-11-23, user: 'can we do that for the game
menu too, at least with Item Info on? a much clearer way than now with the divider line under it' + 'also on the options pages, exactly like
the start screen menu'; mock-up ~/Project-Friday-Test/lktest/titlesub/menu/mock_iteminfo.png OK'd).
Before: the bar box showed the three words (Use / Equip / Options), a 1 px divider and the description in the second text line.
Now: while a description / help line is shown (cursor in the item list, the Equip grid or on an options row) the box holds ONLY that text,
centred horizontally and moved up one tile row between the two text lines (printed into line 2, then its tiles shifted: a glyph printed across the lines lost a pixel row); no words, no divider.  With the cursor on the bar itself (no description) the
three words come back exactly as before.  The sliced drawing (a few characters per frame) and the per-item cache of tools/patch_iteminfo.py
stay; a description job now starts from the cleared box (step 0) instead of the cached word bar.  Item Info Off: the item list shows the
plain bar as before (the options help is always on, as before).  Needs patch_iteminfo / patch_options / patch_uiwide (runs after them).
Idempotent.  usage: patch_iicenter.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_IICENTER v1"

def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed (%d): %s" % (s.count(old), old[:100])
    return s.replace(old, new, 1)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
else:
    a = "static void lk_ii_job_run0(void);\n"
    s = rep(s, a, a + "/* ---- " + VER + ": the description alone in the bar, centred (tools/patch_iicenter.py) ---- */\n"
               "#define LK_II_W 288   /* the bar's text width in pixels (36 tile columns; the old divider ran over columns 1..34) */\n"
               "#define LK_II_DY 0x10   /* printed into the second text line (a glyph printed across the two lines lost a pixel row = a line through the text, user 2026-11-23), then moved up one tile row (lk_ii_up8) */\n"
               "static void lk_ii_up8(int y0) {   /* the box = 2 text lines of $900 bytes (36 columns x 2 tiles of 32 bytes, 4bpp): tiles of line 2 move up one tile row (B <- C, C <- D, D <- empty) = 8 px, centred */\n"
               "    uint32_t b1 = 0xFF3900u + (uint32_t)y0 / 16u * 0x900u, b2 = b1 + 0x900u, cx, k;\n"
               "    for (cx = 0; cx < 36; cx++) for (k = 0; k < 32; k++) {\n"
               "        uint8_t c = bus_read8(b2 + cx * 64u + k), d = bus_read8(b2 + cx * 64u + 32u + k), a = bus_read8(b1 + cx * 64u + k);   /* a: tile A, empty after the clear */\n"
               "        bus_write8(b1 + cx * 64u + 32u + k, c); bus_write8(b2 + cx * 64u + k, d); bus_write8(b2 + cx * 64u + 32u + k, a); } }\n"
               "static uint8_t *lk_ii_blank; static uint8_t lk_ii_y0b;   /* the cleared box (step 0 calls the game's clear routines = slow; later descriptions start from this copy) */\n"
               "static int lk_ii_cx(const char *t) { int w = lk_fs_width(t), x = (LK_II_W - w) / 2; return x < 8 ? 8 : x; }   /* lk_fs_width: the game font widths incl. escaped glyphs (t is already translated) */\n", "job_run0 decl")
    s = rep(s, "        case 0: lk_call(0x024998u); lk_call(0x0234A8u); lk_ii_job.y0 = bus_read8(0xFF1129u); lk_ii_job.step = 1; budget -= 4; break;",
            "        case 0: lk_call(0x024998u); lk_call(0x0234A8u); lk_ii_job.y0 = bus_read8(0xFF1129u); lk_ii_job.step = t ? 4 : 1; if (t) { uint32_t i; lk_ii_job.pos = 0; lk_ii_job.x = lk_ii_cx(t); if (!lk_ii_blank) lk_ii_blank = (uint8_t *)malloc(LK_II_BUF); if (lk_ii_blank) { for (i = 0; i < LK_II_BUF; i++) lk_ii_blank[i] = bus_read8(0xFF3900u + i); lk_ii_y0b = lk_ii_job.y0; } } budget -= 4; break;   /* " + VER + ": a description goes into the cleared box without the words; the cleared box is kept (lk_ii_blank) */", "step 0")
    s = rep(s, "bus_write16(0xFF1194, (uint16_t)lk_ii_job.x); bus_write8(0xFF1129u, (uint8_t)(y0 + 0x10));",
            "bus_write16(0xFF1194, (uint16_t)lk_ii_job.x); bus_write8(0xFF1129u, (uint8_t)(y0 + LK_II_DY));   /* " + VER + " */", "step 4 y")
    s = rep(s, "        case 5: lk_ii_line(); lk_ii_job.step = 6; break;", "        case 5: lk_ii_up8(lk_ii_job.y0); lk_ii_job.step = 6; (void)lk_ii_line; break;   /* " + VER + ": no divider; the text moves up 8 px (centred) */", "step 5")
    s = rep(s, "    if (want >= 0 && lk_ii_cache[0x40]) {   /* start from the cached plain bar: only the description has to be rendered */\n        memcpy(lk_ii_work, lk_ii_cache[0x40], LK_II_BUF);\n        lk_ii_job.y0 = lk_ii_y0s; lk_ii_job.step = 4; lk_ii_job.x = 0x10;",
            "    if (want >= 0 && lk_ii_blank) {   /* " + VER + ": start from the cleared box (no words under a description any more) */\n        memcpy(lk_ii_work, lk_ii_blank, LK_II_BUF);\n        lk_ii_job.y0 = lk_ii_y0b; lk_ii_job.step = 4; lk_ii_job.x = lk_ii_cx(t);", "plain bar shortcut")
    s = rep(s, "static void lk_ii_leave(void) { lk_ii_job.on = 0; if (lk_ii_cur >= 0) lk_ii_draw(-1); }",
            "static void lk_ii_leave(void) { if (lk_ii_job.on && lk_ii_job.id >= 0) lk_ii_job.on = 0; if (lk_ii_cur >= 0 || lk_ii_job.on) lk_ii_draw(-1); }   /* " + VER + ": a running plain-bar job continues (it was restarted every pass and never finished once descriptions stopped caching the word bar) */", "leave")
    s = rep(s, "static void lk_ii_draw(int id);   /* tools/patch_iteminfo.py */\n", "static void lk_ii_draw(int id);   /* tools/patch_iteminfo.py */\nstatic uint16_t lk_ii_ax;   /* " + VER + ": X of the bar arrow before it was parked under a description */\n", "ax decl")
    # options pages: the bar arrow stood at 'Options' (lk_bar_arrow) and now floated in the help text: parked (X 1 = off screen) while a help line
    # is shown, back on 'Options' as soon as the bar shows the words again (SAT RAM entry $FF07C8: Y, $FF07CE: X)
    # item lists too (user shots 2026-11-23: the arrow pointed at 'Use' / 'Equip', with the words gone it floated in the description): lk_ii_draw parks it
    # under a description and remembers where it stood (lk_ii_ax); an empty slot or the bar loop (cursor back on the bar, B) puts it back
    s = rep(s, "    int want = t ? id : -1;\n", "    int want = t ? id : -1;\n"
            "    { uint16_t ax = bus_read16(0xFF07CEu); if (want >= 0) { if (ax != 1) { lk_ii_ax = ax; bus_write16(0xFF07CEu, 1); } } else if (ax == 1 && lk_ii_ax) bus_write16(0xFF07CEu, lk_ii_ax); }   /* " + VER + ": bar arrow parked under a description */\n", "draw arrow")
    s = rep(s, "        lk_opt_helpbar();\n", "        lk_opt_helpbar();\n        if (!(lk_opt_tab && lk_opt_sel) && bus_read16(0xFF07CEu) == 1 && lk_ii_ax) bus_write16(0xFF07CEu, lk_ii_ax);   /* " + VER + ": back on the bar: the arrow returns */\n", "bar loop arrow")
    s = rep(s, "    if (id >= 0 && id < 100 && lk_opt_help(id) && !lk_bind_capturing()) lk_ii_draw(0x100 + id); else lk_ii_leave(); }",
            "    if (id >= 0 && id < 100 && lk_opt_help(id) && !lk_bind_capturing()) { lk_ii_draw(0x100 + id); bus_write16(0xFF07CEu, 1); }   /* " + VER + ": arrow parked under the help */\n"
            "    else { lk_ii_leave(); if (lk_opt_tab && bus_read16(0xFF07CEu) == 1) bus_write16(0xFF07CEu, (uint16_t)LK_X_OPT); } }", "opt helpbar arrow")
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)
