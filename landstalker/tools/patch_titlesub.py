#!/usr/bin/env python3
"""Title screen subtitle in the language (release 2.0, 2026-11-14, user: own lettering, 'option 2').
While the final title screen runs (lk_brand_on, WaitForStartGame $039988, tools/patch_overlay.py) and the language is de / fr / ko / ja, the
English 'THE TREASURES OF KING NOLE' is covered in the finished picture and our own lettering (tools/titlefont.py: hand-drawn capitals in
the title's style; Hangul / kanji from Noto Sans CJK KR / JP Bold 17 px, SIL OFL, lang/OFL-NotoSansCJK.txt) is drawn right-aligned where the English line ends; Japanese like the Japanese release (thin serif, near white, lines 113..132 from x 155).  The three greys follow the
picture: they are scaled from the brightness of a pixel of the English letters in the previous frame (fades stay right).  Picture only
(nothing in RAM / VRAM changes); ru / uk since LK_TSCYR v1; English and English (JP) keep the original title.  Test aid: LANDSTALKER_TITLESUB=0 = off.
Needs patch_overlay.py (LK_BRAND v1) and patch_lang.py.  Idempotent.  usage: patch_titlesub.py path/to/genrecomp"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import titlefont as tf
root = sys.argv[1]
VER = "LK_TITLESUB v1"

def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed: " + old[:90]
    return s.replace(old, new, 1)

codes = ("de", "fr", "es", "it", "ru", "uk", "ko", "ja")   # es / it: LK_LGES v1; ru / uk: LK_TSCYR v1 (Cyrillic capitals, Щ with 2 rows below the line)
lay = {c: tf.layout(c) for c in codes}   # rows, left x, first line, brightness of '#' / '+' / '-'
cmap = {".": "0", "#": "1", "+": "2", "-": "3"}
arrays = "".join("static const char lk_ts_%s[%d][%d] = { %s };\n" % (c, len(L[0]), len(L[0][0]) + 1, ", ".join('"%s"' % "".join(cmap[ch] for ch in row) for row in L[0])) for c, L in lay.items())
table = "".join("static const char *lk_ts_row_%s(int y) { return lk_ts_%s[y]; }\n" % (c, c) for c in codes)
table += "#define LK_TS_N %d   /* LK_TSCYR v1 */\n" % len(codes)
table += "static const struct { const char *code; const char *(*row)(int); int w, h, x, top, n1, n2, n3; } lk_ts_tab[%d] = { %s };\n" % (
    len(codes), ", ".join('{ "%s", lk_ts_row_%s, %d, %d, %d, %d, %d, %d, %d }' % ((c, c, len(L[0][0]), len(L[0]), L[1], L[2]) + tuple(L[3])) for c, L in lay.items()))

p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER in s:
    print("vdp_render.c already patched: " + VER)
else:
    a = "      lk_brand_row(lk_row0, lk_w0);   /* LK_BRAND v1 */\n"
    s = rep(s, a, "      lk_ts_row(lk_row0, lk_w0);   /* " + VER + " */\n" + a, "brand call")
    module = "/* ---- " + VER + ": the title subtitle in the language (tools/patch_titlesub.py, lettering tools/titlefont.py) ---- */\n" + arrays + table + r'''extern const char *lk_lang_code_cur(void);   /* tools/patch_titlesub.py (func_table.c): the loaded language ('' = English) */
int lk_ts_on;   /* LK_TSWHOLE: set by func_table.c while DisplayTitleScreen $039848 runs */
static uint32_t lk_ts_ref = 0xCCCCCCu;   /* the English letters' light grey of the previous frame (follows fades) */
#define LK_TS_X0 127   /* the covered box in game pixels: the English subtitle is x 131..287, lines 105..121 */
#define LK_TS_X1 292
#define LK_TS_Y0 102
#define LK_TS_Y1 123
static void lk_ts_row(PIXEL_OUT_T *row, int width) {
  static int off = -1; int line = lk_br_line, Wp = bitmap.viewport.w, ox = bitmap.viewport.x, g0, i, x, y; const char *code; PIXEL_OUT_T *r;
  if (!lk_ts_on) return;   /* LK_TSWHOLE (2026-11-23, GitHub #18): the whole DisplayTitleScreen (sword slash, wait, fade to black), was only WaitForStartGame */
  if (off < 0) { const char *e = getenv("LANDSTALKER_TITLESUB"); off = e && *e && atoi(e) == 0; }
  if (off || line < LK_TS_Y0 || line > 140 || Wp < 320 || width < Wp + 2 * ox) return;
  code = lk_lang_code_cur(); if (!code || !*code) return;
  for (i = 0; i < LK_TS_N; i++) if (!strcmp(code, lk_ts_tab[i].code)) break;   /* LK_TSCYR v1: was i < 4, which hid ko / ja once es / it came in */
  if (i == LK_TS_N) return;
  r = row + ox; g0 = (Wp - 320) / 2;
  if (line == 105) lk_ts_ref = r[g0 + 131] & 0xFFFFFFu;   /* top-left pixel of the English 'T' (light grey), read before it is covered */
  if (line <= LK_TS_Y1) for (x = LK_TS_X0; x <= LK_TS_X1; x++) r[g0 + x] = (r[g0 + x] & 0xFF000000u) | 0;   /* the English line away (black background) */
  y = line - lk_ts_tab[i].top; if (y < 0 || y >= lk_ts_tab[i].h) return;
  { const char *m = lk_ts_tab[i].row(y); int w = lk_ts_tab[i].w, xs = lk_ts_tab[i].x, k;
    int R = (int)((lk_ts_ref >> 16) & 255), G = (int)((lk_ts_ref >> 8) & 255), B = (int)(lk_ts_ref & 255);
    for (k = 0; k < w; k++) { int c = m[k] - '0', num; uint32_t px;
      if (!c) continue;
      num = c == 1 ? lk_ts_tab[i].n1 : c == 2 ? lk_ts_tab[i].n2 : lk_ts_tab[i].n3;   /* brightness relative to the English letters' light grey 204 (tools/titlefont.py layout) */
      { int rr = R * num / 204, gg = G * num / 204, bb = B * num / 204; if (rr > 255) rr = 255; if (gg > 255) gg = 255; if (bb > 255) bb = 255;
        px = ((uint32_t)rr << 16) | ((uint32_t)gg << 8) | (uint32_t)bb; }
      r[g0 + xs + k] = (r[g0 + xs + k] & 0xFF000000u) | px; } }
}
'''
    c = "void render_line(int line)"
    s = rep(s, c, module + c, "render_line")
    open(p, "w").write(s)
    print("vdp_render.c patched: " + VER)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
else:
    a = "static void lk_lang_install(void) {"
    s = rep(s, a, "const char *lk_lang_code_cur(void) { return lk_lg_on ? lk_lg_codes[lk_lg_sel] : \"\"; }   /* " + VER + ": the loaded language for the picture side */\n" + a, "lang install")
    # LK_TSWHOLE: the subtitle for the whole title screen. The English line shows from the end of the sword slash (TitleScreenSwordSlash) and
    # stays during FadeToBlack after START; WaitForStartGame (lk_brand_on) covered only the middle. Hooked: DisplayTitleScreen $039848
    # (TitleScreen $039762 tail-calls it through the table). Our letters follow the English letters' brightness, so they appear with them.
    a = "static void lk_brand_install(void) {"
    s = rep(s, a, """extern int lk_ts_on; static gen_func_t lk_ts_o_disp;   /* LK_TSWHOLE */
static void lk_ts_h_disp(void) { lk_ts_on = 1; lk_ts_o_disp(); lk_ts_on = 0; }
""" + a, "brand install")
    a = "    lk_o_title = func_table_lookup(0x039988);"
    s = rep(s, a, "    lk_ts_o_disp = func_table_lookup(0x039848); if (lk_ts_o_disp) func_table_register(0x039848, lk_ts_h_disp); else fprintf(stderr, \"titlesub: DisplayTitleScreen not found\\n\");   /* LK_TSWHOLE */\n" + a, "brand install body")
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)
