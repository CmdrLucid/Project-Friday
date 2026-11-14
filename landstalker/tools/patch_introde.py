#!/usr/bin/env python3
"""German intro captions (2026-11-14, release 2.0, user: translate what is missing per language).
The intro captions ('GAMUL DATE 312 / JYPTA RUINS', 'SEGA ENTERPRISES PRESENTS', 'A KAN NAITO PROGRAM', 'KALVA HARBOR') are drawn by
CheckAndDisplayIntroString $00C46A from the table IntroStrings $00C59E (string id = g_IntroStringId $FF1159 - 1; per string 5 words: line 1 x / y,
line 2 x / y, display time -> $FF12EE; then 32 characters, 16 per line, 0 = space, 1..26 = A..Z, 27..35 = 1..9, 36 = 0, $FF = end) through
CopyIntroStringToVDP $00C4E2 -> GetNextIntroChar $00C51C (move.b (a2)+, d0) and LoadIntroStringLine1 / 2Sprites $00C56E / $00C57A.
The German release ('Die Schaetze von Koenig Nolo') translated four of them; the French and even the Japanese release kept the English captions,
so only Language = Deutsch gets new captions (the wording of the German release; staff names and LANDSTALKER stay).
Wrapper of CheckAndDisplayIntroString: when the language is 'de' and the call would show a string that has a German text, the display branch runs
in C with our text (GetNextIntroChar serves it while lk_id_on is set) and each line re-centred on the centre of the original English line
(read from the ROM table at run time).  Every other case = the original function = bit exact.  Needs patch_lang.py + patch_bath.py (install anchor).
Idempotent.  usage: patch_introde.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_INTRODE v1"

def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed: " + old[:90]
    return s.replace(old, new, 1)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
else:
    assert "LK_BATH v1" in s, "func_table.c: run patch_bath.py first"
    module = r'''/* ---- ''' + VER + r''': German intro captions (tools/patch_introde.py) ---- */
static const char *const lk_id_de[13][2] = {   /* [string id] = line 1, line 2 (A-Z, 0-9, space; at most 16 each); NULL = the original */
    { 0, 0 }, { "GAMUL DATUM 312", "JYPTA RUINEN" }, { "SEGA ENTERPRISES", "" }, { 0, 0 }, { "EIN PROGRAMM VON", "KAN NAITO" }, { "KALVA HAFEN", "" } };
static uint8_t lk_id_buf[33]; static int lk_id_on, lk_id_pos;
static gen_func_t lk_id_o_show, lk_id_o_next;
static int lk_id_code(char c) { return c >= 'A' && c <= 'Z' ? c - 'A' + 1 : c >= '1' && c <= '9' ? c - '1' + 27 : c == '0' ? 36 : 0; }   /* the intro font: 1..9 = 27..35, 0 = 36 (US 'GAMUL DATE 312' = 29 27 28) */
static int lk_id_len(uint32_t a) { int n = 16; while (n > 0 && bus_read8(a + (uint32_t)n - 1u) == 0) n--; return n; }   /* drawn length of an original line (trailing spaces off) */
static void lk_id_h_next(void) {   /* GetNextIntroChar $00C51C: move.b (a2)+, d0 */
    if (!lk_id_on) { lk_id_o_next(); return; }
    { uint8_t c = lk_id_pos < 32 ? lk_id_buf[lk_id_pos++] : 0xFF; g_m68k.d[0] = (g_m68k.d[0] & 0xFFFFFF00u) | c; g_m68k.a[2]++; M68K_TST8(c);
      bus_add_cycles(24); func_table_rts(); } }
static void lk_id_h_show(void) {   /* CheckAndDisplayIntroString $00C46A */
    int id = bus_read8(0xFF1159u), l, k; uint32_t a; int16_t x1, y1, x2, y2, t, c1, c2;
    if (id <= 0 || id >= 13 || !lk_id_de[id][0] || bus_read16(0xFF12EEu) != 0 || !lk_lg_on || strcmp(lk_lg_codes[lk_lg_sel], "de")) { lk_id_o_show(); return; }
    a = bus_read32(0x00C59Eu + 4u * (uint32_t)(id - 1));   /* IntroStrings: the original entry (positions, time, English text) */
    x1 = (int16_t)bus_read16(a); y1 = (int16_t)bus_read16(a + 2u); x2 = (int16_t)bus_read16(a + 4u); y2 = (int16_t)bus_read16(a + 6u); t = (int16_t)bus_read16(a + 8u);
    c1 = (int16_t)(x1 + 4 * lk_id_len(a + 10u)); c2 = (int16_t)(x2 + 4 * lk_id_len(a + 26u));   /* centres of the English lines (8 px per letter) */
    if (lk_id_len(a + 26u) == 0) c2 = c1;
    memset(lk_id_buf, 0, sizeof lk_id_buf);
    for (l = 0; l < 2; l++) { const char *w = lk_id_de[id][l]; for (k = 0; k < 16 && w[k]; k++) lk_id_buf[16 * l + k] = (uint8_t)lk_id_code(w[k]); }
    x1 = (int16_t)(c1 - 4 * (int)strlen(lk_id_de[id][0])); x2 = (int16_t)(c2 - 4 * (int)strlen(lk_id_de[id][1]));
    bus_write16(0xFF12EEu, (uint16_t)t);
    g_m68k.a[2] = a + 10u; lk_id_on = 1; lk_id_pos = 0;
    func_table_jsr(0x00C4E2u, 0x00C4A2u);   /* CopyIntroStringToVDP (reads our text through GetNextIntroChar) */
    lk_id_on = 0;
    g_m68k.d[0] = (g_m68k.d[0] & 0xFFFF0000u) | (uint16_t)x1; g_m68k.d[1] = (g_m68k.d[1] & 0xFFFF0000u) | (uint16_t)y1;
    func_table_jsr(0x00C56Eu, 0x00C4AAu);   /* LoadIntroStringLine1Sprites */
    g_m68k.d[0] = (g_m68k.d[0] & 0xFFFF0000u) | (uint16_t)x2; g_m68k.d[1] = (g_m68k.d[1] & 0xFFFF0000u) | (uint16_t)y2;
    g_m68k.d[2] = (g_m68k.d[2] & 0xFFFF0000u) | (uint16_t)x2; g_m68k.d[3] = (g_m68k.d[3] & 0xFFFF0000u) | (uint16_t)y2;
    func_table_jsr(0x00C57Au, 0x00C4B2u);   /* LoadIntroStringLine2Sprites */
    if (getenv("LANDSTALKER_INTRODE_LOG")) fprintf(stderr, "introde: string %d German (x %d / %d)\n", id, x1, x2);
    bus_add_cycles(16); func_table_rts(); }
static void lk_id_install(void) {   /* once per run */
    static int done; if (done) return; done = 1;
    lk_id_o_show = func_table_lookup(0x00C46Au); lk_id_o_next = func_table_lookup(0x00C51Cu);
    if (lk_id_o_show && lk_id_o_next) { func_table_register(0x00C46Au, lk_id_h_show); func_table_register(0x00C51Cu, lk_id_h_next); }
    else fprintf(stderr, "introde: intro string routines not found\n");
}
'''
    a = "static void lk_lang_install(void) {"   # after the language module (lk_lg_on / lk_lg_codes / lk_lg_sel)
    s = rep(s, a, module + a, "func_table.c lang install")
    h = "        lk_bath_install();   /* LK_BATH v1 */\n"
    s = rep(s, h, h + "        lk_id_install();   /* " + VER + " */\n", "func_table.c install hook")
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)
