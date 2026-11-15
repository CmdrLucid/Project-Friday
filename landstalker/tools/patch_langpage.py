#!/usr/bin/env python3
"""Options page 'Language / Region' (2026-11-15, user: 'im Optionsmenue wird Language schon sehr gross ... zusammenfassen').
The root page of the options menu (Start menu tab + file select window, tools/patch_options.py) had three value rows under the pages:
Language, Names (LK_LGNAMES), Items (LK_JPITEMS).  They move into a page of their own, 'Language / Region' (page 8, after Keybindings),
together with the new row Bath Scene (LK_BATH, id 63): root = 8 pages + Quit Game (9 rows, fits the 7-row window with scrolling as before).
A language change inside the page redraws the whole page (labels in the new language), like the old root row did.
Needs patch_options.py, patch_kbdir.py (row count 20 of the Keybindings page) and patch_bath.py (id 63).  Idempotent.  usage: patch_langpage.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_LGPAGE v1"

def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed: " + old[:90]
    return s.replace(old, new, 1)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
else:
    assert "LK_KBDIR v1" in s or "= { 11, 6, 12, 3, 6, 8, 3, 20 };" in s, "func_table.c: run patch_kbdir.py first"
    assert "LK_BATH v1" in s, "func_table.c: run patch_bath.py first"
    s = rep(s, "#define LK_NPG 7", "#define LK_NPG 8   /* " + VER + ": page 8 = Language / Region (Language, Names, Items, Bath Scene) */", "LK_NPG")
    s = rep(s, "#define LK_RLANG 7", "#define LK_RLANG -101   /* " + VER + ": no value rows on the root any more */", "LK_RLANG")
    s = rep(s, "#define LK_RNAMES 8", "#define LK_RNAMES -102", "LK_RNAMES")
    s = rep(s, "#define LK_RITEMS 9", "#define LK_RITEMS -103", "LK_RITEMS")
    s = rep(s, "#define LK_RQUIT 10", "#define LK_RQUIT 8", "LK_RQUIT")
    s = rep(s, "= { 11, 6, 12, 3, 5, 8, 3, 20 };", "= { 9, 6, 12, 3, 5, 8, 3, 20, 4 };   /* " + VER + " */", "lk_pg_cnt")
    s = rep(s, "static const int *const lk_pg_ids[LK_NPG + 1] = {",
            "static const int lk_ids_lang[4] = { 37, 61, 62, 63 };   /* " + VER + ": Language, Names, Items, Bath Scene */\nstatic const int *const lk_pg_ids[LK_NPG + 1] = {", "lk_pg_ids decl")
    s = rep(s, "lk_ids_diff, 0 };", "lk_ids_diff, 0, lk_ids_lang };", "lk_pg_ids")
    s = rep(s, '"Difficulty / Help", "Keybindings" };', '"Difficulty / Help", "Keybindings", "Language / Region" };', "lk_pg_name")
    # the old root value rows: dead code now, removed
    for old in ("    if (lk_opt_row == LK_RLANG) { lk_opt_change(37, 1); lk_opt_page(); return; }\n",
                "    if (lk_opt_row == LK_RNAMES) { lk_opt_change(61, 1); lk_opt_page(); return; }\n",
                "if (lk_opt_row == LK_RITEMS) { lk_opt_change(62, 1); lk_opt_page(); return; }"):
        s = rep(s, old, "", "lk_opt_enter")
    # file select window: a language change inside the page redraws every label
    s = rep(s, "if (wid >= 118) lk_win_page(pg, row); else lk_win_value(pg, row);",
            "if (wid >= 118 || wid == 37) lk_win_page(pg, row); else lk_win_value(pg, row);   /* " + VER + ": Language redraws the page */", "window RIGHT")
    s = rep(s, "if ((e & 4) && pg) { lk_opt_change(lk_win_id(pg, row), -1); blink = 0; lk_win_value(pg, row); lk_snd(0x00FA54u); }",
            "if ((e & 4) && pg) { int wid = lk_win_id(pg, row); lk_opt_change(wid, -1); blink = 0; if (wid == 37) lk_win_page(pg, row); else lk_win_value(pg, row); lk_snd(0x00FA54u); }   /* " + VER + " */", "window LEFT")
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)
