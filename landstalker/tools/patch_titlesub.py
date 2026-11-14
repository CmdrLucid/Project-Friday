#!/usr/bin/env python3
"""Title screen subtitle in the language (release 2.0, 2026-11-14, user: own lettering, 'option 2').
While the final title screen runs (lk_brand_on, WaitForStartGame $039988, tools/patch_overlay.py) and the language is de / fr / ko / ja, the
English 'THE TREASURES OF KING NOLE' is covered in the finished picture and our own lettering (tools/titlefont.py: hand-drawn capitals in
the title's style; Hangul / kanji from Noto Sans CJK KR / JP Bold 17 px, SIL OFL, lang/OFL-NotoSansCJK.txt) is drawn right-aligned where the English line ends.  The three greys follow the
picture: they are scaled from the brightness of a pixel of the English letters in the previous frame (fades stay right).  Picture only
(nothing in RAM / VRAM changes); English and English (JP) keep the original title.  Test aid: LANDSTALKER_TITLESUB=0 = off.
Needs patch_overlay.py (LK_BRAND v1) and patch_lang.py.  Idempotent.  usage: patch_titlesub.py path/to/genrecomp"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import titlefont as tf
root = sys.argv[1]
VER = "LK_TITLESUB v1"

def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed: " + old[:90]
    return s.replace(old, new, 1)

codes = ("de", "fr", "ko", "ja")
maps = {c: tf.render(c) for c in codes}
cmap = {".": "0", "#": "1", "+": "2", "-": "3"}
arrays = "".join("static const char lk_ts_%s[%d][%d] = { %s };\n" % (c, tf.H, len(m[0]) + 1, ", ".join('"%s"' % "".join(cmap[ch] for ch in row) for row in m)) for c, m in maps.items())
table = "".join("static const char *lk_ts_row_%s(int y) { return lk_ts_%s[y]; }\n" % (c, c) for c in codes)
table += "static const struct { const char *code; const char *(*row)(int); int w; } lk_ts_tab[%d] = { %s };\n" % (
    len(codes), ", ".join('{ "%s", lk_ts_row_%s, %d }' % (c, c, len(maps[c][0])) for c in codes))

p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER in s:
    print("vdp_render.c already patched: " + VER)
else:
    a = "      lk_brand_row(lk_row0, lk_w0);   /* LK_BRAND v1 */\n"
    s = rep(s, a, "      lk_ts_row(lk_row0, lk_w0);   /* " + VER + " */\n" + a, "brand call")
    module = "/* ---- " + VER + ": the title subtitle in the language (tools/patch_titlesub.py, lettering tools/titlefont.py) ---- */\n" + arrays + table + r'''extern const char *lk_lang_code_cur(void);   /* tools/patch_titlesub.py (func_table.c): the loaded language ('' = English) */
static uint32_t lk_ts_ref = 0xCCCCCCu;   /* the English letters' light grey of the previous frame (follows fades) */
#define LK_TS_X0 127   /* the covered box in game pixels: the English subtitle is x 131..287, lines 105..121 */
#define LK_TS_X1 292
#define LK_TS_Y0 102
#define LK_TS_Y1 123
#define LK_TS_RIGHT 287
#define LK_TS_TOP (105 - 3)   /* first map row = 3 rows above the letters (accents) */
static void lk_ts_row(PIXEL_OUT_T *row, int width) {
  static int off = -1; int line = lk_br_line, Wp = bitmap.viewport.w, ox = bitmap.viewport.x, g0, i, x, y; const char *code; PIXEL_OUT_T *r;
  if (!lk_brand_on) return;
  if (off < 0) { const char *e = getenv("LANDSTALKER_TITLESUB"); off = e && *e && atoi(e) == 0; }
  if (off || line < LK_TS_Y0 || line > LK_TS_Y1 || Wp < 320 || width < Wp + 2 * ox) return;
  code = lk_lang_code_cur(); if (!code || !*code) return;
  for (i = 0; i < 4; i++) if (!strcmp(code, lk_ts_tab[i].code)) break;
  if (i == 4) return;
  r = row + ox; g0 = (Wp - 320) / 2;
  if (line == 105) lk_ts_ref = r[g0 + 131] & 0xFFFFFFu;   /* top-left pixel of the English 'T' (light grey), read before it is covered */
  for (x = LK_TS_X0; x <= LK_TS_X1; x++) r[g0 + x] = (r[g0 + x] & 0xFF000000u) | 0;   /* the English line away (black background) */
  y = line - LK_TS_TOP; if (y < 0 || y >= 20) return;
  { const char *m = lk_ts_tab[i].row(y); int w = lk_ts_tab[i].w, xs = LK_TS_RIGHT - w + 1, k;
    int R = (int)((lk_ts_ref >> 16) & 255), G = (int)((lk_ts_ref >> 8) & 255), B = (int)(lk_ts_ref & 255);
    for (k = 0; k < w; k++) { int c = m[k] - '0', num; uint32_t px;
      if (!c) continue;
      num = c == 1 ? 204 : c == 2 ? 170 : 136;   /* the three greys of the title letters, relative to the light one */
      px = ((uint32_t)(R * num / 204) << 16) | ((uint32_t)(G * num / 204) << 8) | (uint32_t)(B * num / 204);
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
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)
