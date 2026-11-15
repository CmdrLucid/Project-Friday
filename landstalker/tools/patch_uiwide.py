#!/usr/bin/env python3
"""Options menu in Korean / Japanese (release 2.0, 2026-11-14, user: 'translate what is missing in each language's menu').
Our own UI text of ko / ja is stored as escaped byte strings + a glyph table at the end of the language file (tools/uiwide.py, LK_UIWIDE v1):
a 2-byte escape (lead 1..8, then $80 | low 7 bits) = glyph gi with (text font code, advance, 8x8 Galmuri 7 rows).
Runtime (func_table.c):
 * patch_lang module: the footer 'UIW1' is found at load; lk_lang_trw(en) = the translation with escapes (only callers that decode them),
   lk_lang_tr(en) stays plain (an escaped value -> the English text: OSD / overlay / map fonts know no Hangul / kana);
   lk_lang_cp(&t) reads one character (ASCII or $10000 + gi), lk_lang_gcode / gadv / g8 = the glyph's data.
 * option rows (lk_opt_put, 8x8 window tiles): a glyph gets a virtual tile slot (vi 0..255 = tiles $600..$67F / $700..$77F, drawn by the own
   renderer from lk_vt_gl, patch_own.py lk_scr_cell); the pool restarts at every page redraw (lk_opt_page).  Korean item names use the same
   slots (LK_LGKOMENU v1): they are restored from a copy before the item list draws again (lk_vt_dirty).
 * ProcessChar printers (help line / item info job, bar words, file select window, lk_fs_width): ASCII via lk_chr as before, a glyph = its
   text font code; widths from the glyph table.
Other languages: no escapes in their files = every path does exactly what it did before.  Needs patch_lang / patch_options / patch_iteminfo /
patch_langpage.  Idempotent.  usage: patch_uiwide.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_UIWIDE v1"   # + v2 line (2026-11-15): item descriptions of Item Info in ko / ja

def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed (%d): %s" % (s.count(old), old[:100])
    return s.replace(old, new, 1)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER); sys.exit(0)

# ---- patch_lang module: footer, lk_lang_trw / cp / glyph data, KOMN copy for the restore ----
s = rep(s, "static int lk_lg_on, lk_lg_hooked, lk_lg_wide;",
        "static const uint8_t *lk_uw_g; static int lk_uw_n; static uint8_t lk_vt_kgb[256][8]; int lk_vt_dirty;   /* " + VER + ": glyph table of the UI text, copy of the Korean item glyphs */\n"
        "static int lk_lg_on, lk_lg_hooked, lk_lg_wide;", "lang statics")
s = rep(s, "    lk_lg_cur = NULL; lk_lg_on = 0; lk_vt_ko = 0; lk_lg_wide = 0;   /* LK_LGKOMENU v1 */\n",
        "    lk_lg_cur = NULL; lk_lg_on = 0; lk_vt_ko = 0; lk_lg_wide = 0;   /* LK_LGKOMENU v1 */\n    lk_uw_g = NULL; lk_uw_n = 0;   /* " + VER + " */\n", "lang unload")
s = rep(s, "                for (g = 0; g < ng && g < 0x100; g++) memcpy(lk_vt_gl[g], t + 8 * g, 8);\n",
        "                for (g = 0; g < ng && g < 0x100; g++) { memcpy(lk_vt_gl[g], t + 8 * g, 8); memcpy(lk_vt_kgb[g], t + 8 * g, 8); }   /* " + VER + ": + the copy */\n", "KOMN copy")
s = rep(s, "    lk_lg_wide = lk_lg_be16(d + 4) == 4;\n",
        "    lk_lg_wide = lk_lg_be16(d + 4) == 4;\n"
        "    if (sz >= 18 && !memcmp(d + sz - 12, \"UIW1\", 4) && !memcmp(d + sz - 4, \"UIW1\", 4)) {   /* " + VER + ": glyph table of the UI text (tools/uiwide.py) */\n"
        "        uint32_t uo = lk_lg_be32(d + sz - 8);\n"
        "        if (uo + 6u <= (uint32_t)sz && !memcmp(d + uo, \"UIWG\", 4)) { int un = lk_lg_be16(d + uo + 4); if (uo + 6u + 11u * (uint32_t)un <= (uint32_t)sz - 12u) { lk_uw_g = d + uo + 6; lk_uw_n = un; } } }\n",
        "lang load footer")
a = "const char *lk_lang_tr(const char *en) {   /* our own UI text: the translation of an English word / phrase of the options menus (or the English text itself) */\n"
s = rep(s, a,
        "static int lk_uw_esc(const char *t) { for (; *t; t++) if ((unsigned char)*t >= 1 && (unsigned char)*t <= 8) return 1; return 0; }\n"
        "const char *lk_lang_trw(const char *en);\n" + a, "lk_lang_tr head")
a = "    for (t = 0; t < lk_lg_ntext; t++) if (!strcmp(lk_lg_text[t].k, en)) return lk_lg_text[t].v;\n    return en;\n}\n"
s = rep(s, a,
        "    for (t = 0; t < lk_lg_ntext; t++) if (!strcmp(lk_lg_text[t].k, en)) return lk_uw_esc(lk_lg_text[t].v) ? en : lk_lg_text[t].v;   /* " + VER + ": escaped (Hangul / kana) -> English for the plain fonts */\n    return en;\n}\n"
        "const char *lk_lang_trw(const char *en) {   /* " + VER + ": the translation WITH escapes (callers that decode them with lk_lang_cp) */\n"
        "    int t; if (!lk_lg_on || !en) return en;\n"
        "    for (t = 0; t < lk_lg_ntext; t++) if (!strcmp(lk_lg_text[t].k, en)) return lk_lg_text[t].v;\n    return en;\n}\n"
        "int lk_lang_cp(const char **t) {   /* one character: ASCII byte, or $10000 + glyph index of an escape */\n"
        "    unsigned char c = (unsigned char)**t;\n"
        "    if (c >= 1 && c <= 8 && ((unsigned char)(*t)[1] & 0x80)) { int gi = ((c - 1) << 7) | ((unsigned char)(*t)[1] & 0x7F); *t += 2; return 0x10000 + gi; }\n"
        "    (*t)++; return c; }\n"
        "int lk_lang_gcode(int gi) { return gi >= 0 && gi < lk_uw_n ? lk_lg_be16(lk_uw_g + 11 * gi) : 0; }   /* text font code of glyph gi */\n"
        "int lk_lang_gadv(int gi) { return gi >= 0 && gi < lk_uw_n ? lk_uw_g[11 * gi + 2] : 8; }   /* its advance in px */\n"
        "const uint8_t *lk_lang_g8(int gi) { static const uint8_t z[8]; return gi >= 0 && gi < lk_uw_n ? lk_uw_g + 11 * gi + 3 : z; }   /* its 8x8 menu tile rows */\n",
        "lk_lang_tr body")
# Korean item names: restore their glyphs after an options page used the slots
s = rep(s, "    if (lk_vt_ko && !lk_vt_ja()) {   /* LK_LGKOMENU v1: Korean: one 7x7 syllable per tile in row 1, row 2 blank */\n",
        "    if (lk_vt_dirty) { memcpy(lk_vt_gl, lk_vt_kgb, sizeof lk_vt_kgb); lk_vt_dirty = 0; }   /* " + VER + ": an options page used the slots */\n"
        "    if (lk_vt_ko && !lk_vt_ja()) {   /* LK_LGKOMENU v1: Korean: one 7x7 syllable per tile in row 1, row 2 blank */\n", "item restore")

# ---- options module ----
a = "extern const char *lk_lang_tr(const char *en);   /* our own UI text in the selected language (tools/patch_lang.py): the English text itself when there is no translation */\n"
s = rep(s, a, a +
        "extern const char *lk_lang_trw(const char *en); extern int lk_lang_cp(const char **t); extern int lk_lang_gcode(int gi); extern int lk_lang_gadv(int gi); extern const uint8_t *lk_lang_g8(int gi);   /* " + VER + " */\n"
        "extern uint8_t lk_vt_gl[384][8]; extern int lk_vt_dirty;\n"
        "static int lk_uv_gi[256], lk_uv_n;   /* " + VER + ": virtual tile slot -> glyph of the current options page */\n"
        "static int lk_uv_tile(int gi) {   /* the window tile of glyph gi (a virtual tile, drawn by the own renderer) */\n"
        "    int i; for (i = 0; i < lk_uv_n; i++) if (lk_uv_gi[i] == gi) break;\n"
        "    if (i == lk_uv_n) { if (lk_uv_n >= 256) lk_uv_n = 0; i = lk_uv_n++; lk_uv_gi[i] = gi; memcpy(lk_vt_gl[i], lk_lang_g8(gi), 8); lk_vt_dirty = 1; }\n"
        "    return i < 0x80 ? 0x600 + i : 0x700 + i - 0x80; }\n"
        "", "options externs")
s = rep(s, "static void lk_call(uint32_t a) { func_table_jsr(a, 0x0248B2u); }\n",
        "static int lk_txc(const char **t) { int c = lk_lang_cp(t); return c >= 0x10000 ? lk_lang_gcode(c - 0x10000) : lk_chr((char)c); }   /* " + VER + ": ProcessChar code of the next character */\n"
        "static void lk_call(uint32_t a) { func_table_jsr(a, 0x0248B2u); }\n", "lk_txc")
s = rep(s, "    for (; *t; t++) { g_m68k.d[0] = (uint32_t)lk_chr(*t); lk_call(0x0230CAu); }   /* ProcessChar */\n    lk_call(0x02355Au);   /* DMACopyTextboxTiles */\n",
        "    while (*t) { g_m68k.d[0] = (uint32_t)lk_txc(&t); lk_call(0x0230CAu); }   /* ProcessChar; " + VER + " */\n    lk_call(0x02355Au);   /* DMACopyTextboxTiles */\n", "lk_menu_print")
s = rep(s, "static void lk_opt_put(int col, int row, const char *t) { t = lk_lang_tr(t); for (; *t; t++, col++) bus_write16(0xFF1E04u + (uint32_t)row * 0x80u + (uint32_t)col * 2u, (uint16_t)(0xA000 | lk_chr(*t))); }",
        "static void lk_opt_put(int col, int row, const char *t) { t = lk_lang_trw(t); while (*t) { int c = lk_lang_cp(&t); bus_write16(0xFF1E04u + (uint32_t)row * 0x80u + (uint32_t)col * 2u, (uint16_t)(0xA000 | (c >= 0x10000 ? lk_uv_tile(c - 0x10000) : lk_chr((char)c)))); col++; } }   /* " + VER + " */",
        "lk_opt_put")
s = rep(s, "static const char *lk_opt_val(int id, int v) { return lk_lang_tr(lk_opt_val0(id, v)); }",
        "static const char *lk_opt_val(int id, int v) { return lk_lang_trw(lk_opt_val0(id, v)); }   /* " + VER + ": escapes kept (lk_opt_put / lk_fs_print decode them) */", "lk_opt_val")
s = rep(s, "    int r, c; M68kContext sv = g_m68k;\n    for (r = 0; r < 17; r++) for (c = 0; c < 36; c++) bus_write16(0xFF1E04u",
        "    int r, c; M68kContext sv = g_m68k;\n    lk_uv_n = 0;   /* " + VER + ": a new page = a new slot pool */\n    for (r = 0; r < 17; r++) for (c = 0; c < 36; c++) bus_write16(0xFF1E04u", "lk_opt_page pool")
s = rep(s, "    t = lk_lang_tr(t);\n    bus_write32(0xFF1844, 0); bus_write8(0xFF1155, 0); bus_write8(0xFF1144, 3); bus_write16(0xFF1194, (uint16_t)x);\n    for (; *t; t++) { g_m68k.d[0] = (uint32_t)lk_chr(*t); lk_call(0x0230CAu); }   /* ProcessChar */\n",
        "    t = lk_lang_trw(t);\n    bus_write32(0xFF1844, 0); bus_write8(0xFF1155, 0); bus_write8(0xFF1144, 3); bus_write16(0xFF1194, (uint16_t)x);\n    while (*t) { g_m68k.d[0] = (uint32_t)lk_txc(&t); lk_call(0x0230CAu); }   /* ProcessChar; " + VER + " */\n", "lk_menu_print_nodma")
s = rep(s, "static void lk_fs_print(const char *t, int x) { t = lk_lang_tr(t); bus_write16(0xFF1194, (uint16_t)x); for (; *t; t++) { g_m68k.d[0] = (uint32_t)lk_chr(*t); lk_call(0x0235FEu); } }",
        "static void lk_fs_print(const char *t, int x) { t = lk_lang_trw(t); bus_write16(0xFF1194, (uint16_t)x); while (*t) { g_m68k.d[0] = (uint32_t)lk_txc(&t); lk_call(0x0235FEu); } }   /* " + VER + " */", "lk_fs_print")
s = rep(s, "    for (t = lk_lang_tr(t); *t; t++) {\n        int c = lk_chr(*t), k = 0, row;\n",
        "    for (t = lk_lang_trw(t); *t; ) {\n        int c, k = 0, row, cp = lk_lang_cp(&t);   /* " + VER + " */\n        if (cp >= 0x10000) { w += lk_lang_gadv(cp - 0x10000); continue; }\n        c = lk_chr((char)cp);\n", "lk_fs_width")
s = rep(s, "lk_win_text(0, title, 142 - lk_fs_width(lk_lang_tr(title)) / 2, NULL, 0);", "lk_win_text(0, title, 142 - lk_fs_width(title) / 2, NULL, 0);", "window title width")

# ---- item info module (help lines, bar words) ----
s = rep(s, "static void lk_ii_putchars(const char *t, int n) { int i; for (i = 0; i < n; i++) { g_m68k.d[0] = (uint32_t)lk_chr(t[i]); lk_call(0x0230CAu); } }",
        "static void lk_ii_putchars(const char *t, int n) { const char *e = t + n; while (t < e && *t) { g_m68k.d[0] = (uint32_t)lk_txc(&t); lk_call(0x0230CAu); } }   /* ProcessChar; " + VER + ": n = bytes (an escape is 2) */", "lk_ii_putchars")
s = rep(s, "static void lk_ii_print_at(const char *t, int x) { t = lk_lang_tr(t);", "static void lk_ii_print_at(const char *t, int x) { t = lk_lang_trw(t);", "lk_ii_print_at")
s = rep(s, "return h ? lk_lang_tr(h) : NULL; }", "return h ? lk_lang_trw(h) : NULL; }   /* " + VER + " */", "lk_ii_text")
s = rep(s, "if (lk_ii_tab[i].id == id) return lk_lang_tr(lk_ii_tab[i].txt);", "if (lk_ii_tab[i].id == id) return lk_lang_trw(lk_ii_tab[i].txt);   /* LK_UIWIDE v2 (2026-11-15): the ITEM descriptions too (they stayed English in ko / ja) */", "lk_ii_text items")
s = rep(s, "            if (n > budget) n = budget;\n",
        "            if (n > budget) n = budget;\n            if (n > 0 && n < (int)strlen(t) - lk_ii_job.pos && (unsigned char)t[lk_ii_job.pos + n - 1] >= 1 && (unsigned char)t[lk_ii_job.pos + n - 1] <= 8) n++;   /* " + VER + ": never split an escape */\n",
        "lk_ii job split")
s = rep(s, "(uint32_t)cx * 64u + 14u * 4u + (uint32_t)k,", "(uint32_t)cx * 64u + (lk_vt_ja() ? 15u : 14u) * 4u + (uint32_t)k,", "lk_ii_line row")   # Japanese: the kana reach row 14
open(p, "w").write(s)
print("func_table.c patched: " + VER)
