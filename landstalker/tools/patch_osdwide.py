#!/usr/bin/env python3
"""Hint font (on-screen messages, quick-equip overlay, 'PREPARING LIGHTING', room map hint, text boxes) in Cyrillic / Hangul / kana
(LK_OSDWIDE v1, 2026-11-23, GitHub #18 paul-met: 'the translation of system messages is not displayed, names remain in their original form').
Before: these drawers use the 5x7 hint font (lk_glyph: A-Z, digits, : - / . and the German umlaut bytes) and asked lk_lang_tr, which gives the
ENGLISH text for an escaped translation (tools/uiwide.py) - so in ru / uk / ko / ja every message and every equipment name stayed English, and
the two texts with printf fields (FAST FORWARD %dX, NO OTHER %s) were not even built for those languages.
Now: one decoder lk_hf_glyph (ASCII / umlaut byte -> the 5x7 glyph as before, advance 6; an escape -> the language's 8x8 menu glyph from the
glyph table, rows 1..7, advance = its width + 1) used by every hint-font drawer; their callers ask lk_lang_trw (translation with escapes).
English and the Latin languages: only ASCII / umlaut bytes = the same pixels as before.  tools/uiwide.py keeps entries with % now (an escape is
never a '%' byte, so snprintf formats them unchanged).  Needs patch_display / patch_equip / patch_lights / patch_roommap / patch_ffwd /
patch_quicksave / patch_uiwide first.  Idempotent.  usage: patch_osdwide.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_OSDWIDE v1"

def rep(s, old, new, what, n=1):
    assert s.count(old) == n, what + " layout changed (%d): %s" % (s.count(old), old[:100])
    return s.replace(old, new)

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched: " + VER)
else:
    a = "      unsigned char u = (unsigned char)c; if (u == 0x80 || u == 0x84) return au; if (u == 0x81 || u == 0x85) return ou; if (u == 0x82 || u == 0x86) return uu; if (u == 0x83) return sz; }\n    return blank;\n}\n"
    s = rep(s, a, a + r'''/* ---- LK_OSDWIDE v1: the hint font with the language's own glyphs (tools/patch_osdwide.py) ---- */
extern const char *lk_lang_trw(const char *en); extern int lk_lang_cp(const char **t); extern const uint8_t *lk_lang_g8(int gi);
static int lk_hf_glyph(const char **t, uint8_t g[7]) {   /* next character -> 7 rows (bit $80 = column 0), returns the advance in hint pixels */
    int c = lk_lang_cp(t), r, w = 0;
    if (c < 0x10000) { const uint8_t *a = lk_glyph((char)c); for (r = 0; r < 7; r++) g[r] = (uint8_t)(a[r] << 3); return 6; }
    { const uint8_t *e = lk_lang_g8(c - 0x10000); for (r = 0; r < 7; r++) { int k; g[r] = e[r + 1]; for (k = 0; k < 8; k++) if ((g[r] & (0x80 >> k)) && k + 1 > w) w = k + 1; } }
    return w ? w + 1 : 4;   /* the 8x8 menu glyph (row 0 is free), its own width + 1 px gap; an empty one = a space */
}
static int lk_hf_w(const char *t) { int w = 0; uint8_t g[7]; while (*t) w += lk_hf_glyph(&t, g); return w; }   /* width in hint pixels (6 per ASCII character, as before) */
static void lk_hf_draw(const char *t, int x, int y, int px) {   /* in the current draw colour */
    int cx = 0; uint8_t g[7];
    while (*t) { int a = lk_hf_glyph(&t, g), r, c; for (r = 0; r < 7; r++) for (c = 0; c < 8; c++) if (g[r] & (0x80 >> c)) { SDL_Rect d = { x + (cx + c) * px, y + r * px, px, px }; SDL_RenderFillRect(s_renderer, &d); } cx += a; }
}
''', "lk_glyph end")
    # quick-equip overlay (R2): names
    s = rep(s, "    for (int i = 0; t[i]; i++) { const uint8_t *gl = lk_glyph(t[i]); for (int rr = 0; rr < 7; rr++) for (int c = 0; c < 5; c++) if (gl[rr] & (0x10 >> c)) { SDL_Rect d = { x + (i * 6 + c) * sc, y + rr * sc, sc, sc }; SDL_RenderFillRect(s_renderer, &d); } }\n",
            "    lk_hf_draw(t, x, y, sc);   /* " + VER + " */\n", "lk_eq_text")
    s = rep(s, "{ const char *nn = lk_lang_tr(idx >= 0 ? nm[k][idx] : dn[k]); int n = (int)strlen(nn), sc = n * 6 * ts > cw - 2 ? 1 : ts; lk_eq_text(cell.x + (cw - n * 6 * sc) / 2,",
            "{ const char *nn = lk_lang_trw(idx >= 0 ? nm[k][idx] : dn[k]); int n = lk_hf_w(nn), sc = n * ts > cw - 2 ? 1 : ts; lk_eq_text(cell.x + (cw - n * sc) / 2,", "eq overlay name 1")
    s = rep(s, "const char *nn = lk_lang_tr(q ? nm[k][q - 1] : dn[k]);", "const char *nn = lk_lang_trw(q ? nm[k][q - 1] : dn[k]);   /* " + VER + " */", "eq overlay name 2")
    s = rep(s, "if (own) { int n = (int)strlen(nn); int sc = n * 6 * ts > sw ? 1 : ts; lk_eq_text(c.x + (sw - n * 6 * sc) / 2,",
            "if (own) { int n = lk_hf_w(nn); int sc = n * ts > sw ? 1 : ts; lk_eq_text(c.x + (sw - n * sc) / 2,", "eq overlay name 2 width")
    # text box (coordinates and debug boxes)
    s = rep(s, "    int n = (int)strlen(t);\n    SDL_Rect box = { x, y, (n * 6 + 1) * px, 9 * px };",
            "    int n = lk_hf_w(t);   /* " + VER + " */\n    SDL_Rect box = { x, y, (n + 1) * px, 9 * px };", "lk_text_box width")
    s = rep(s, "    for (int i = 0; i < n; i++) {\n        const uint8_t *g = lk_glyph(t[i]);\n        for (int rr = 0; rr < 7; rr++) for (int c = 0; c < 5; c++)\n            if (g[rr] & (0x10 >> c)) { SDL_Rect d = { x + px + (i * 6 + c) * px, y + px + rr * px, px, px }; SDL_RenderFillRect(s_renderer, &d); }\n    }\n",
            "    lk_hf_draw(t, x + px, y + px, px);\n", "lk_text_box loop")
    # on-screen message (bottom left)
    s = rep(s, "    int n = (int)strlen(lk_osd_text), bw = (n * 6 + 1) * px, bh = 9 * px, m = 2 * px;",
            "    int n = lk_hf_w(lk_osd_text), bw = (n + 1) * px, bh = 9 * px, m = 2 * px;   /* " + VER + " */", "osd width")
    s = rep(s, "    for (int i = 0; i < n; i++) {\n        const uint8_t *g = lk_glyph(lk_osd_text[i]);\n        for (int r = 0; r < 7; r++) for (int c = 0; c < 5; c++)\n            if (g[r] & (0x10 >> c)) { SDL_Rect d = { m + px + (i * 6 + c) * px, oy + px + r * px, px, px }; SDL_RenderFillRect(s_renderer, &d); }\n    }\n",
            "    lk_hf_draw(lk_osd_text, m + px, oy + px, px);\n", "osd loop")
    # test aid LANDSTALKER_OSDSAY="frame:KEY;frame:KEY" = lk_osd_say(KEY) at that frame (the per-language picture sweep; window shots LANDSTALKER_WINSHOT)
    s = rep(s, "    if (lk_osd_frames <= 0) return;\n    lk_osd_frames--;\n",
            "    { static const char *e; static int init; if (!init) { init = 1; e = getenv(\"LANDSTALKER_OSDSAY\"); }   /* " + VER + " test aid */\n"
            "      if (e) { char key[24]; const char *p; extern void lk_osd_say(const char *t); snprintf(key, sizeof key, \"%ld:\", platform_frame_number());\n"
            "        for (p = e; p && *p; p = strchr(p, ';') ? strchr(p, ';') + 1 : NULL) if (!strncmp(p, key, strlen(key))) { char t[96]; const char *q = p + strlen(key); size_t n = strcspn(q, \";\"); if (n >= sizeof t) n = sizeof t - 1; memcpy(t, q, n); t[n] = 0; lk_osd_say(t); } } }\n"
            "    if (lk_osd_frames <= 0) return;\n    lk_osd_frames--;\n", "osd test aid")
    s = rep(s, "static char lk_osd_text[40];", "static char lk_osd_text[128];   /* " + VER + ": was 40 (an escaped character takes 2 bytes) */", "osd buffer")
    s = rep(s, 'void lk_osd_say(const char *t) { snprintf(lk_osd_text, sizeof lk_osd_text, "%s", lk_lang_tr(t));',
            'void lk_osd_say(const char *t) { snprintf(lk_osd_text, sizeof lk_osd_text, "%s", lk_lang_trw(t));   /* ' + VER + ' */', "lk_osd_say")
    for k in ("FAST FORWARD OFF - SEE OPTIONS", "QUICK SAVE OFF - SEE OPTIONS", "SPRINT OFF - SEE OPTIONS", "NO MAP HERE"):
        s = rep(s, '"%s", lk_lang_tr("' + k + '"))', '"%s", lk_lang_trw("' + k + '"))', "osd " + k)
    s = rep(s, 'snprintf(lk_osd_text, sizeof lk_osd_text, lk_lang_tr("FAST FORWARD %dX"), n);', 'snprintf(lk_osd_text, sizeof lk_osd_text, lk_lang_trw("FAST FORWARD %dX"), n);', "osd ffwd")
    # 'PREPARING LIGHTING'
    s = rep(s, 'const char *t = lk_lang_tr("PREPARING LIGHTING");', 'const char *t = lk_lang_trw("PREPARING LIGHTING");   /* ' + VER + ' */', "shw text")
    s = rep(s, "n = (int)strlen(t); tw = (n * 6 - 1) * px;", "n = lk_hf_w(t); tw = (n - 1) * px;", "shw width")
    s = rep(s, "    for (i = 0; i < n; i++) { const uint8_t *g = lk_glyph(t[i]);\n        for (r = 0; r < 7; r++) for (c = 0; c < 5; c++) if (g[r] & (0x10 >> c)) { SDL_Rect d = { x0 + (i * 6 + c) * px, y0 + r * px, px, px }; SDL_RenderFillRect(s_renderer, &d); } }\n",
            "    lk_hf_draw(t, x0, y0, px); (void)i; (void)r; (void)c;\n", "shw loop")
    # room map hint line (own buffer, shadowed)
    s = rep(s, "    for (int i = 0; t[i]; i++) { char ch = t[i] == '_' ? ' ' : t[i]; if (ch >= 'a' && ch <= 'z') ch = (char)(ch - 32); const uint8_t *gl = lk_glyph(ch); for (int r = 0; r < 7; r++) for (int k = 0; k < 5; k++) if (gl[r] & (0x10 >> k)) { lk_rm_fill(x + (i * 6 + k) * sc + sc / 2 + 1, y + r * sc + sc / 2 + 1, sc, sc, 0xFF000000u); lk_rm_fill(x + (i * 6 + k) * sc, y + r * sc, sc, sc, c); } }\n",
            "    int cx = 0; while (*t) { uint8_t gl[7]; int a; if (*t == '_') { const char *sp = \" \"; a = lk_hf_glyph(&sp, gl); t++; } else a = lk_hf_glyph(&t, gl);   /* " + VER + " (lk_glyph knows a..z as capitals already) */\n"
            "        for (int r = 0; r < 7; r++) for (int k = 0; k < 8; k++) if (gl[r] & (0x80 >> k)) { lk_rm_fill(x + (cx + k) * sc + sc / 2 + 1, y + r * sc + sc / 2 + 1, sc, sc, 0xFF000000u); lk_rm_fill(x + (cx + k) * sc, y + r * sc, sc, sc, c); }\n"
            "        cx += a; }\n", "lk_rm_text")
    s = rep(s, 'const char *lg = lk_lang_tr("SAME NUMBER: CONNECTED DOORS"); lk_rm_text(px0 + pw / 2 - (int)strlen(lg) * 3 * (sc - 1),',
            'const char *lg = lk_lang_trw("SAME NUMBER: CONNECTED DOORS"); lk_rm_text(px0 + pw / 2 - lk_hf_w(lg) / 2 * (sc - 1),', "room map hint")
    open(p, "w").write(s)
    print("platform_sdl.c patched: " + VER)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
else:
    s = rep(s, "j = -1; char t[48];", "j = -1; char t[128];   /* " + VER + ": escaped characters take 2 bytes */", "quick equip buffer")
    s = rep(s, 'snprintf(t, sizeof t, "%s: %s", lk_lang_tr(kind[cat]), lk_lang_tr(j ? nm[cat][j - 1] : dnm[cat])); lk_osd_say(t);',
            'snprintf(t, sizeof t, "%s: %s", lk_lang_trw(kind[cat]), lk_lang_trw(j ? nm[cat][j - 1] : dnm[cat])); lk_osd_say(t);   /* ' + VER + ' */', "quick equip message")
    s = rep(s, 'snprintf(t, sizeof t, lk_lang_tr("NO OTHER %s"), lk_lang_tr(kind[cat]));',
            'snprintf(t, sizeof t, lk_lang_trw("NO OTHER %s"), lk_lang_trw(kind[cat]));   /* ' + VER + ' */', "no other message")
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)
