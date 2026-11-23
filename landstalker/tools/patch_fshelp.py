#!/usr/bin/env python3
"""Help line in the file select options window (LK_FSHELP v1, 2026-11-23, user: 'the info lines are only in the game menu, not in the start
screen menu ... put the info line down in the bar where Start, Copy etc. is, while one is in the options menu').
While lk_fs_modal (tools/patch_options.py) runs, the bar under the window ('Start Copy Delete Options', no function while the window is open)
shows the help line of the selected row - the same texts as the Start menu (lk_opt_help, in the language, escapes via lk_fs_print), centred in
the bar; rows without help (page entries, key bindings) leave the bar empty.  Closing the window restores the four words (lk_fs_bar_text, as
before).  The bar is drawn when the selected row / page / language changed, BEFORE WaitUntilVBlank, so the text buffer $FF3900 is copied out
before the window rows reuse it.  Needs patch_options / patch_uiwide.  Idempotent.  usage: patch_fshelp.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_FSHELP v1"

def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed (%d): %s" % (s.count(old), old[:100])
    return s.replace(old, new, 1)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
else:
    a = "static void lk_fs_modal(void) {   /* options window in the file select */"
    s = rep(s, a, r'''/* ---- LK_FSHELP v1: help line of the selected row in the file select bar (tools/patch_fshelp.py) ---- */
static int lk_fs_helpid(int pg, int row) {   /* option id whose help line belongs to the row, -1 = none */
    int id;
    if (pg == 0) return LK_ROWVID(row) >= 0 ? LK_ROWVID(row) : -1;   /* root: only the value rows (Language) have help */
    id = lk_win_id(pg, row); return id >= 0 && id < 100 ? id : -1;
}
static long lk_fs_shown = -1;   /* the help key the bar shows */
#define LK_FSH_W 277   /* centre of the visible bar inside the frame (shots: 280 sat 1-2 px right) */
static void lk_fs_help_check(void) {   /* test aid LANDSTALKER_FSHELP_CHECK=1: measure every help line in the current language with the game font, list the ones wider than the bar */
    static int done; int id, n = 0; if (done || !getenv("LANDSTALKER_FSHELP_CHECK")) return; done = 1;
    for (id = 0; id < (int)(sizeof lk_id_name / sizeof lk_id_name[0]); id++) { const char *h = lk_opt_help(id); int w; if (!h || !*h) continue; w = lk_fs_width(h); n++;
        if (w > LK_FSH_W - 4) fprintf(stderr, "fshelp: TOO WIDE id %d '%s' width %d (max %d)\n", id, h, w, LK_FSH_W - 4); }
    fprintf(stderr, "fshelp: %d help lines measured\n", n);
}
static void lk_fs_bar_help(int id) {
    M68kContext sv; lk_fs_help_check(); sv = g_m68k; const char *h = id >= 0 ? lk_opt_help(id) : NULL;
    lk_call(0x00F5F4u);   /* ClearTextBuffer */
    if (h && *h) { int w = lk_fs_width(h), x = (LK_FSH_W - w) / 2; if (x < 2) x = 2; lk_fs_print(h, x); }   /* centred in the bar: text buffer x 2 .. 276 is inside the frame (measured on shots) */
    lk_call(0x00F5DCu);   /* DMACopyTextBuffer */
    g_m68k = sv;
}
''' + a, "modal")
    a = "        lk_fs_relang(&gen0);   /* LK_FSLANGREDRAW v2: any change not caught at its call site */\n"
    s = rep(s, a, a + "        { long key = ((long)lk_lang_gen() << 16) | ((long)pg << 8) | (long)(lk_fs_helpid(pg, row) + 1);   /* " + VER + ": redraw the bar when row / page / language changed */\n"
                      "          if (key != lk_fs_shown) { lk_fs_bar_help(lk_fs_helpid(pg, row)); lk_fs_shown = key; } }\n", "modal loop")
    s = rep(s, "    lk_win_scroll = 0; lk_opt_quitarm = 0; lk_win_page(0, 0); lk_win_on = 1; lk_win_blink = 0;\n",
            "    lk_win_scroll = 0; lk_opt_quitarm = 0; lk_win_page(0, 0); lk_win_on = 1; lk_win_blink = 0;\n    lk_fs_shown = -1;   /* " + VER + ": the bar becomes the help line while the window is open (drawn in the first loop pass) */\n", "modal start")
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)
