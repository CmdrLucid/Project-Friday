#!/usr/bin/env python3
"""Text layer runtime (docs/TEXT_LAYER.md step 3): loads the language binary built by tools/langbuild.py and replaces dialogue strings, name table entries and the font.
Languages: <exe dir>/lang/index.txt ("code<TAB>name") + <code>.bin (tools/langbuild.py, run by build.sh / firstrun.py); the setting is ~/.landstalker_lang (LANDSTALKER_LANG=<code> overrides), the Options row (Options > Language) calls lk_lang_step() and switches AT ONCE; LANDSTALKER_LANGDIR / LANDSTALKER_LANGBIN=<file> (an extra language 'Test') / LANDSTALKER_LANGLOG=1 (lists every string the game starts) are test aids. English = every hook is a plain pass through.
 * dialogue: InitCompString $022FCC remembers the string id; DecodeChar $0246B2 then returns the translated characters instead of Huffman decoding (control characters as
   $56 + k, end as $55): the game's own GetNextChar / ProcessChar / name insertion ({Item}) keep working; the extended glyphs ($6C..) cannot pass the control table, so DecodeChar
   returns a placeholder control code and the GetNextChar wrapper swaps in the glyph word
 * names: SkipToStringIndex $0294B6 (finds entry d1 of the table at a2) returns the translated entry (A2 / D7)
 * font: copy of MainFont $02A884 (codes 0..$6B) + the new glyphs in extra memory, MainFontPtr $022E84 pointed to it (in the in-memory ROM image)
 * extra memory = 64 KB mapped at $800000 (unused address range of the Mega Drive; 68k read path: bus.c)
Runs on genrecomp src/bus.c + src/func_table.c (needs patch_quicksave.py first).  Idempotent.  usage: patch_lang.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_LANG v1"

p = os.path.join(root, "src/bus.c")
s = open(p).read()
if VER not in s:
    a = "uint8_t bus_read8(uint32_t addr) {\n"
    assert s.count(a) == 1, "bus.c layout changed"
    s = s.replace(a, '''/* ---- ''' + VER + ''' (tools/patch_lang.py): extra memory for the text layer at $800000 (64 KB, 68k word order = native 16-bit stores) ---- */
uint8_t lk_lang_mem[0x10000];
uint8_t lk_font_mem[0x10000];   /* LK_LGFONT v1: the text font of a language file at $820000 (own bank: codes up to $7FF = 2047 glyphs; Korean needs ~1100) */
void lk_lang_map(void) {
    cpu_memory_map *m = &m68k.memory_map[0x80];
    m->base = lk_lang_mem; m->read8 = NULL; m->read16 = NULL; m->write8 = NULL; m->write16 = NULL;
    m = &m68k.memory_map[0x82]; m->base = lk_font_mem; m->read8 = NULL; m->read16 = NULL; m->write8 = NULL; m->write16 = NULL;
}
void lk_lang_rom_patch32(uint32_t addr, uint32_t v) {   /* writes a long into the in-memory ROM image (native 16-bit words, like bus_read16 reads them) */
    cpu_memory_map *m = &m68k.memory_map[(addr >> 16) & 0xFF];
    if (!m->base) return;
    *(uint16 *)(m->base + (addr & 0xFFFF)) = (uint16)(v >> 16); *(uint16 *)(m->base + (addr & 0xFFFF) + 2) = (uint16)v;
}
/* LK_JPITEMS v1: the Japanese item pictures (read at start from the player's Japanese ROM, func_table.c lk_ji_avail) at $810000, same word order */
uint8_t lk_ji_mem[0x10000];
void lk_ji_map(void) {
    cpu_memory_map *m = &m68k.memory_map[0x81];
    m->base = lk_ji_mem; m->read8 = NULL; m->read16 = NULL; m->write8 = NULL; m->write16 = NULL;
}

''' + a, 1)
    open(p, "w").write(s)
    print("bus.c patched: " + VER)
else:
    print("bus.c already patched: " + VER)

p = os.path.join(root, "src/genrecomp.c")   # LK_JPITEMS v1: the runtime looks for the Japanese ROM next to the started ROM
s = open(p).read()
if "lk_rom_file" not in s:
    a = "bool genrecomp_load_rom(const char *path) {\n"
    assert s.count(a) == 1, "genrecomp.c layout changed"
    s = s.replace(a, "char lk_rom_file[1024];   /* LK_JPITEMS v1 (tools/patch_lang.py): path of the started ROM */\n" + a + "    snprintf(lk_rom_file, sizeof lk_rom_file, \"%s\", path);\n", 1)
    open(p, "w").write(s)
    print("genrecomp.c patched: LK_JPITEMS v1")

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER); sys.exit(0)
anchor = "static void lk_qs_install(void) {"
assert s.count(anchor) == 1, "func_table.c: run patch_quicksave.py first"
module = r'''/* ---- ''' + VER + r''': text layer (tools/patch_lang.py, docs/TEXT_LAYER.md) ---- */
extern uint8_t lk_lang_mem[0x10000]; extern uint8_t lk_font_mem[0x10000];   /* LK_LGFONT v1 */
extern void lk_lang_map(void);
extern void lk_lang_rom_patch32(uint32_t addr, uint32_t v);
extern uint8_t lk_ji_mem[0x10000];
extern void lk_ji_map(void);
int lk_items_get(void);
extern uint8_t bus_peek8(uint32_t addr);   /* tools/patch_own.py LK_OWNPEEK (no bus clock) */
#ifdef _WIN32
extern __declspec(dllimport) unsigned long __stdcall GetModuleFileNameA(void *, char *, unsigned long);
#include <io.h>   /* _findfirst: LK_JPITEMS v1 */
#else
#include <unistd.h>
#include <dirent.h>   /* LK_JPITEMS v1 */
#endif
typedef struct { uint16_t id; uint16_t n; const uint8_t *w; } LkLgStr;
typedef struct { uint8_t tab, idx, n; uint32_t addr; } LkLgName;
typedef struct { char *k, *v; } LkLgText;                     /* our own UI text: English key -> translation (umlauts as bytes $80..$86, see patch_options.py lk_chr) */
static LkLgText *lk_lg_text; static int lk_lg_ntext;
static LkLgStr *lk_lg_str; static int lk_lg_nstr;
static LkLgName *lk_lg_name; static int lk_lg_nname;
static const LkLgStr *lk_lg_cur; static int lk_lg_pos, lk_lg_ext, lk_lg_extcode; static int lk_lg_wstart = 1, lk_lg_lstart;   /* LK_LGWRAP v1 */
static uint8_t *lk_lg_data;                                   /* the loaded language file (word streams are read from it) */
static int lk_lg_on, lk_lg_hooked, lk_lg_wide;   /* LK_LGKO v1: lk_lg_wide = language file version 4: name entries hold 16-bit codes (Korean) */ uint8_t lk_vt_gl[128][8]; int lk_vt_on; static int lk_vt_ok;   /* LK_JPMENU v1 (below) */
static uint8_t lk_lg_mg[128], lk_lg_mgl[128][8];   /* menu font glyphs (8x8, 1bpp) of the extra characters, by character code */
static uint16_t lk_lg_ui[8][2]; static int lk_lg_nui;                  /* language file block 'ui': key, value (docs/TEXT_LAYER.md) */
static char lk_lg_codes[8][16], lk_lg_names[8][32]; static int lk_lg_nlang = 1, lk_lg_sel;   /* [0] = English (the original), then the languages of lang/index.txt */
static char lk_lg_dir[512], lk_lg_binfile[512];
static void (*lk_lg_o_dma)(void), (*lk_lg_o_ics)(void), (*lk_lg_o_dc)(void), (*lk_lg_o_gnc)(void), (*lk_lg_o_skip)(void);
static void (*lk_lg_o_pc)(void); static int lk_lg_inpc;   /* LK_JPITEMS v3 (user 2026-11-13: 'in der japanischen Fassung haben die Items sehr wohl Kana-Namen'): inside HandleItemName $0231E2 (the {Item}
   control of the dialogue printer: PopItem, LoadUncompressedString -> SkipToStringIndex; NOT ProcessChar: its control jump table tail-calls the handler after a wrapper returned) the item name is the DIALOGUE one: names with index | $40 (tools/jplang.py,
   Japanese kana names) are used only there; the menus (8x8 menu font, PopulateItemSlot_WriteItemName $00D5E4) keep the normal names */
static void lk_lg_h_pc(void) { int sv = lk_lg_inpc; lk_lg_inpc = 1; lk_lg_o_pc(); lk_lg_inpc = sv; }
static void (*lk_lg_o_cpy)(void);
static void lk_lg_h_cpy(void) {   /* LK_LGKO v1: CopyStringToBuffer $02335C (a2 = name characters, d7 = count - 1 -> words at $FF119E, $FFFF end, $FF1844 = the buffer): our 16-bit names */
    uint32_t a2 = g_m68k.a[2], a1 = 0xFF119Eu; int n, i;
    if (!lk_lg_wide || a2 < 0x808000u || a2 >= 0x810000u) { lk_lg_o_cpy(); return; }
    n = (int)(int16_t)(g_m68k.d[7] & 0xFFFF) + 1;
    bus_write32(0xFF1844u, a1);
    for (i = 0; i < n; i++) { bus_write16(a1, bus_read16(a2)); a1 += 2; a2 += 2; }
    bus_write16(a1, 0xFFFF);
    g_m68k.a[1] = a1; g_m68k.a[2] = a2; g_m68k.d[7] = (g_m68k.d[7] & 0xFFFF0000u) | 0xFFFFu; g_m68k.d[0] &= 0xFFFF0000u;
    func_table_rts();
}
static void lk_lg_put8(uint32_t off, uint8_t v) { lk_lang_mem[off ^ 1] = v; }
static void lk_lg_put16(uint32_t off, uint16_t v) { *(uint16_t *)(lk_lang_mem + off) = v; }
static uint16_t lk_lg_be16(const uint8_t *p) { return (uint16_t)(p[0] << 8 | p[1]); }
static uint32_t lk_lg_be32(const uint8_t *p) { return (uint32_t)p[0] << 24 | p[1] << 16 | p[2] << 8 | p[3]; }
static int lk_lg_cmp(const void *a, const void *b) { return (int)((const LkLgStr *)a)->id - (int)((const LkLgStr *)b)->id; }
static void lk_lg_unload(void) {
    lk_lg_cur = NULL; lk_lg_on = 0; lk_lg_nui = 0; memset(lk_lg_mg, 0, sizeof lk_lg_mg);
    { int t; for (t = 0; t < lk_lg_ntext; t++) { free(lk_lg_text[t].k); free(lk_lg_text[t].v); } free(lk_lg_text); lk_lg_text = NULL; lk_lg_ntext = 0; }
    free(lk_lg_str); lk_lg_str = NULL; lk_lg_nstr = 0; free(lk_lg_name); lk_lg_name = NULL; lk_lg_nname = 0; free(lk_lg_data); lk_lg_data = NULL;
    lk_lang_map(); lk_lang_rom_patch32(0x022E84u, 0x02A884u);   /* the original font */
}
static void lk_lg_load(const char *path) {
    FILE *f = fopen(path, "rb"); long sz; uint8_t *d; int i, ns, nn, nu, ng, nt; const uint8_t *q; uint32_t nameoff = 0x8000;
    lk_lg_unload();
    if (!f) { fprintf(stderr, "lang: cannot open %s\n", path); return; }
    fseek(f, 0, SEEK_END); sz = ftell(f); fseek(f, 0, SEEK_SET); d = malloc((size_t)sz); if (fread(d, 1, (size_t)sz, f) != (size_t)sz) { fclose(f); free(d); return; } fclose(f);
    if (sz < 16 || memcmp(d, "LKLG", 4) || (lk_lg_be16(d + 4) < 2 || lk_lg_be16(d + 4) > 4)) {   /* version 3 (tools/jplang.py): glyph entries with a 16-bit code */ fprintf(stderr, "lang: %s is not a language file (version 2 expected: run tools/langbuild.py again)\n", path); free(d); return; }
    ns = lk_lg_be16(d + 6); nn = lk_lg_be16(d + 8); nu = lk_lg_be16(d + 10); ng = lk_lg_be16(d + 12); nt = lk_lg_be16(d + 14);
    q = d + 16; lk_lg_data = d; lk_lang_map(); memset(lk_lang_mem, 0, sizeof lk_lang_mem);
    lk_lg_wide = lk_lg_be16(d + 4) == 4;
    {   int gs = lk_lg_be16(d + 4) >= 3 ? 40 : 39;   /* glyph entry: (u8 | u16 code) + 30 bytes main font + 8 bytes menu font */
        const uint8_t *se = q, *ne = se + 8 * ns, *ue = ne + 7 * nn, *ge = ue + 4 * nu, *te = ge + gs * ng, *blob = te;
        { const uint8_t *tp = te; int t; lk_lg_text = calloc((size_t)nt + 1, sizeof *lk_lg_text); lk_lg_ntext = nt;
          for (t = 0; t < nt; t++) { int kl = tp[0], vl = tp[1]; lk_lg_text[t].k = malloc((size_t)kl + 1); memcpy(lk_lg_text[t].k, tp + 2, (size_t)kl); lk_lg_text[t].k[kl] = 0; lk_lg_text[t].v = malloc((size_t)vl + 1); memcpy(lk_lg_text[t].v, tp + 2 + kl, (size_t)vl); lk_lg_text[t].v[vl] = 0; tp += 2 + kl + vl; }
          blob = tp; }
        lk_lg_str = calloc((size_t)ns + 1, sizeof *lk_lg_str); lk_lg_name = calloc((size_t)nn + 1, sizeof *lk_lg_name);
        for (i = 0; i < ns; i++) { const uint8_t *e = se + 8 * i; lk_lg_str[i].id = lk_lg_be16(e); lk_lg_str[i].w = blob + lk_lg_be32(e + 2); lk_lg_str[i].n = lk_lg_be16(e + 6); }
        qsort(lk_lg_str, (size_t)ns, sizeof *lk_lg_str, lk_lg_cmp); lk_lg_nstr = ns;
        for (i = 0; i < nn; i++) {
            const uint8_t *e = ne + 7 * i; int n = e[6], k;
            lk_lg_name[i].tab = e[0]; lk_lg_name[i].idx = e[1]; lk_lg_name[i].n = (uint8_t)n; lk_lg_name[i].addr = 0x800000u + nameoff;
            for (k = 0; k < n; k++) lk_lg_put8(nameoff + (uint32_t)k, blob[lk_lg_be32(e + 2) + (uint32_t)k]);
            nameoff += (uint32_t)n + 2;
        }
        lk_lg_nname = nn;
        for (i = 0; i < nu && i < 8; i++) { lk_lg_ui[i][0] = lk_lg_be16(ue + 4 * i); lk_lg_ui[i][1] = lk_lg_be16(ue + 4 * i + 2); } lk_lg_nui = nu < 8 ? nu : 8;
        /* font: the ROM's glyphs 0..$6B (30 bytes each) + the new ones, at $820000 (LK_LGFONT v1, own 64 KB bank); MainFontPtr $022E84 -> there */
        memset(lk_font_mem, 0, sizeof lk_font_mem);
        for (i = 0; i < 0x6C * 30; i += 2) *(uint16_t *)(lk_font_mem + i) = bus_read16(0x02A884u + (uint32_t)i);
        for (i = 0; i < ng; i++) { const uint8_t *g = ge + gs * i; int k, c = gs == 40 ? lk_lg_be16(g) : g[0]; const uint8_t *gd = g + gs - 38;
            if (30u * (uint32_t)c + 30u > 0x10000u) continue;   /* LK_LGFONT v1: codes up to $888 fit the bank */
            for (k = 0; k < 30; k += 2) *(uint16_t *)(lk_font_mem + 30u * (uint32_t)c + (uint32_t)k) = lk_lg_be16(gd + k);
            if (c < 128) { lk_lg_mg[c] = 1; memcpy(lk_lg_mgl[c], gd + 30, 8); } }
        lk_lang_rom_patch32(0x022E84u, 0x820000u);
    }
    fprintf(stderr, "lang: loaded %s: %d strings, %d names, %d glyphs\n", path, ns, nn, ng);
    lk_lg_on = 1;
}
static void lk_lg_h_ics(void) {   /* InitCompString $022FCC: D0 = string id */
    uint16_t id = (uint16_t)g_m68k.d[0]; LkLgStr key, *r = NULL; key.id = id;
    lk_lg_o_ics();
    if (lk_lg_on) { lk_lang_map();
        if (lk_items_get()) { key.id = (uint16_t)(id | 0x8000u); r = bsearch(&key, lk_lg_str, (size_t)lk_lg_nstr, sizeof *lk_lg_str, lk_lg_cmp); key.id = id; }   /* LK_JPITEMS v1: the line that fits the Japanese item */
        if (!r) r = bsearch(&key, lk_lg_str, (size_t)lk_lg_nstr, sizeof *lk_lg_str, lk_lg_cmp); }
    lk_lg_cur = r; lk_lg_pos = 0; lk_lg_ext = 0;
    lk_lg_wstart = 1; lk_lg_lstart = 0;   /* LK_LGWRAP v1 */
    { static int lg_log = -1; if (lg_log < 0) lg_log = getenv("LANDSTALKER_LANGLOG") != NULL; if (lg_log) fprintf(stderr, "lang: string %04X %s at frame %ld\n", id, r ? "TRANSLATED" : "original", (long)platform_frame_number()); }   /* test aid */
}
/* LK_LGWRAP v1 state lk_lg_wstart / lk_lg_lstart: declared with lk_lg_cur; (user 2026-11-13: 'ein Buchstabe, der am Zeilenende stehen sollte, rutscht ganz nach links'): the game checks the line end
   (PrintString_CheckLineWidth $022F66, g_TextXPos > $114) only between words, a word that runs past the 288 px line buffer ((x & $F8) * 8 per 36 tiles) wraps INSIDE the line.
   Before the first letter of every word the real x (word $FF1194) + the word's width (font rule of tools/romtext.py) is checked; if it does not end before LK_LG_XMAX a
   SoftNewLine is sent first.  Works for any speaker name length and every language; LANDSTALKER_LANGWRAP=0 = off */
#define LK_LG_XMAX 284
static int lk_lg_gw(uint16_t c) { int last = -1, r, k; if (c == 0) return 8; for (r = 0; r < 15; r++) { uint16_t v = bus_read16(0x820000u + 30u * c + 2u * (uint32_t)r); for (k = 0; k < 12; k++) if ((v & (0x8000u >> k)) && k > last) last = k; } return last + 3; }
static void lk_lg_h_dc(void) {    /* DecodeChar $0246B2: the next character in the Huffman character domain: glyph < $55, control $56 + k, end $55 */
    if (lk_lg_cur) {
        uint16_t w = lk_lg_pos < lk_lg_cur->n ? lk_lg_be16(lk_lg_cur->w + 2 * lk_lg_pos++) : 0xFFFF; uint8_t ch;
        { static int wr = -1; if (wr < 0) { const char *e = getenv("LANDSTALKER_LANGWRAP"); wr = !(e && atoi(e) == 0); }
          if (wr && w < 0x8000) {
            if (w == 0) lk_lg_wstart = 1;
            else if (lk_lg_wstart) { int i, wd = 0; lk_lg_wstart = 0;
                for (i = lk_lg_pos - 1; i < lk_lg_cur->n; i++) { uint16_t c = lk_lg_be16(lk_lg_cur->w + 2 * i); if (c == 0 || c >= 0x8000) break; wd += lk_lg_gw(c); }
                if (!lk_lg_lstart && (int)bus_read16(0xFF1194u) + wd > LK_LG_XMAX) { lk_lg_pos--; lk_lg_lstart = 1; lk_lg_wstart = 1; g_m68k.d[0] = (g_m68k.d[0] & 0xFFFFFF00u) | 0x57u; func_table_rts(); return; }   /* SoftNewLine (control k = 1) */
                lk_lg_lstart = 0; }
          } else if (w != 0xFFFF) { lk_lg_wstart = 1; lk_lg_lstart = (w == (uint16_t)~0x0Eu || w == (uint16_t)~0x01u); } }   /* a control: a word ends; SoftNewLine / NewLine start a line */
        if (w == 0xFFFF) { ch = 0x55; lk_lg_cur = NULL; }
        else if (w >= 0x8000) { ch = 0x56; /* control: find k from ~handler */
            static const uint8_t hk[19] = {0x15, 0x0E, 0x01, 0x0B, 0x0C, 0x05, 0x07, 0x06, 0x04, 0x03, 0x02, 0x18, 0x0F, 0x0D, 0x08, 0x09, 0x0A, 0x17, 0x19}; int k;
            for (k = 0; k < 19; k++) if ((uint16_t)~hk[k] == w) { ch = (uint8_t)(0x56 + k); break; } }
        else if (w >= 0x56) { lk_lg_ext = 1; lk_lg_extcode = w; ch = 0x56; }   /* extended glyph: placeholder control code k = 0 (D0 = $FFEA), swapped in by the GetNextChar wrapper */
        else ch = (uint8_t)w;
        g_m68k.d[0] = (g_m68k.d[0] & 0xFFFFFF00u) | ch;
        func_table_rts(); return;
    }
    lk_lg_o_dc();
}
static void lk_lg_h_gnc(void) {   /* GetNextChar $023044 */
    lk_lg_o_gnc();
    if (lk_lg_ext) { lk_lg_ext = 0; if ((g_m68k.d[0] & 0xFFFF) == 0xFFEA) g_m68k.d[0] = (g_m68k.d[0] & 0xFFFF0000u) | (uint32_t)lk_lg_extcode; }
}
static void lk_lg_h_skip(void) {  /* SkipToStringIndex $0294B6: A2 = table, D1 = entry index; result A2 = characters, D7 = count - 1 */
    uint32_t tbl = g_m68k.a[2]; int idx = (int)(g_m68k.d[1] & 0xFFFF), tab = -1, i;
    lk_lg_o_skip();
    if (!lk_lg_on) return;
    tab = tbl == 0x029552 ? 0 : tbl == 0x0296E0 ? 1 : tbl == 0x029730 ? 2 : tbl == 0x029732 ? 3 : tbl == 0x029A0A ? 4 : -1;
    if (tab < 0) return;
    lk_lang_map();
    if (tab == 3 && idx < 0x40 && lk_lg_inpc) for (i = 0; i < lk_lg_nname; i++) if (lk_lg_name[i].tab == 3 && lk_lg_name[i].idx == (idx | 0x40)) {   /* LK_JPITEMS v3 */
        g_m68k.a[2] = lk_lg_name[i].addr; g_m68k.d[7] = (g_m68k.d[7] & 0xFFFF0000u) | (uint32_t)((lk_lg_wide ? lk_lg_name[i].n / 2 : lk_lg_name[i].n) - 1); return; }
    if (tab == 3 && idx < 0x80 && lk_items_get()) for (i = 0; i < lk_lg_nname; i++) if (lk_lg_name[i].tab == 3 && lk_lg_name[i].idx == (idx | 0x80)) {   /* LK_JPITEMS v1 */
        g_m68k.a[2] = lk_lg_name[i].addr; g_m68k.d[7] = (g_m68k.d[7] & 0xFFFF0000u) | (uint32_t)((lk_lg_wide ? lk_lg_name[i].n / 2 : lk_lg_name[i].n) - 1); return; }
    for (i = 0; i < lk_lg_nname; i++) if (lk_lg_name[i].tab == tab && lk_lg_name[i].idx == idx) {
        g_m68k.a[2] = lk_lg_name[i].addr; g_m68k.d[7] = (g_m68k.d[7] & 0xFFFF0000u) | (uint32_t)((lk_lg_wide ? lk_lg_name[i].n / 2 : lk_lg_name[i].n) - 1); return; }
}
static void lk_lg_h_dma(void) {   /* QueueDMAOp $000DD6: the menu font (g_Buffer + $84 = $FF2C84, expanded 1bpp -> 4bpp, 32 bytes per tile slot) goes to VRAM $0000: put the extra characters' tiles in first */
    if (lk_lg_on && g_m68k.a[0] == 0xFF2C84u && g_m68k.a[1] == 0 && lk_lg_o_dma) {
        int c, r, q;
        for (c = 0; c < 128; c++) if (lk_lg_mg[c]) for (r = 0; r < 8; r++) for (q = 0; q < 4; q++) {
            uint8_t b = lk_lg_mgl[c][r], l = (b >> (7 - 2 * q)) & 1, rr = (b >> (6 - 2 * q)) & 1;
            bus_write8(0xFF2C84u + 32u * (uint32_t)c + 4u * (uint32_t)r + (uint32_t)q, (uint8_t)(l << 4 | rr)); }
    }
    lk_lg_o_dma();
}
static void lk_lg_home(char *out, size_t n, const char *file) { const char *h = getenv("HOME"); snprintf(out, n, "%s/%s", h ? h : ".", file); }
static void lk_lg_exedir(void) {
    char *sl; ssize_t k = 0;
    { const char *e = getenv("LANDSTALKER_LANGDIR"); if (e && *e) { snprintf(lk_lg_dir, sizeof lk_lg_dir, "%s", e); return; } }
#ifdef _WIN32
    k = (ssize_t)GetModuleFileNameA(NULL, lk_lg_dir, sizeof lk_lg_dir - 8);
#else
    k = readlink("/proc/self/exe", lk_lg_dir, sizeof lk_lg_dir - 8);
#endif
    if (k <= 0) { snprintf(lk_lg_dir, sizeof lk_lg_dir, "lang"); return; }
    lk_lg_dir[k] = 0; sl = strrchr(lk_lg_dir, '/'); { char *bs = strrchr(lk_lg_dir, '\\'); if (bs && (!sl || bs > sl)) sl = bs; }
    if (sl) *sl = 0;
    strcat(lk_lg_dir, "/lang");
}
static int lk_lg_gen;
int lk_lang_gen(void) { return lk_lg_gen; }   /* counts language switches (caches of translated renderings, patch_iteminfo.py) */
static int lk_lg_nmopt = -1;   /* LK_LGNAMES v1 (user 2026-11-13: 'die originalen Namen lassen und auf Wunsch mit extra Option die originalen aus dem Japanischen'): 0 = localized names, 1 = the Japanese originals
   (Options > Names; ~/.landstalker_names, env LANDSTALKER_NAMES): loads <code>.jpn.bin instead of <code>.bin, and for English the generated en.jpn.bin (the original text with the names swapped) */
int lk_names_get(void) {
    if (lk_lg_nmopt < 0) { const char *e = getenv("LANDSTALKER_NAMES"); char path[512], line[16]; FILE *f; lk_lg_nmopt = 0;
        if (e && *e) lk_lg_nmopt = atoi(e) != 0;
        else { lk_lg_home(path, sizeof path, ".landstalker_names"); if ((f = fopen(path, "r"))) { if (fgets(line, sizeof line, f)) lk_lg_nmopt = atoi(line) != 0; fclose(f); } } }
    return lk_lg_nmopt;
}
static int lk_lg_exists(const char *p) { FILE *f = fopen(p, "rb"); if (f) { fclose(f); return 1; } return 0; }
static int lk_vt_ja(void) { return lk_lg_on && !strcmp(lk_lg_codes[lk_lg_sel], "ja"); }   /* LK_JPMENU v1 */
static void lk_lg_apply(int i) {   /* switch the language now: 0 = English (original), others from <exe dir>/lang/<code>.bin */
    char path[600];
    lk_lg_gen++; lk_vt_on = 0;   /* LK_JPMENU v1: set again below for Japanese */
    if (i < 0 || i >= lk_lg_nlang) i = 0;
    lk_lg_sel = i;
    if (i == 0) {   /* English: the original text, or with the Japanese names the generated en.jpn.bin (LK_LGNAMES v1) */
        snprintf(path, sizeof path, "%s/en.jpn.bin", lk_lg_dir);
        if (lk_names_get() && lk_lg_exists(path)) { lk_lg_load(path); lk_lg_sel = 0; return; }
        snprintf(path, sizeof path, "%s/en.items.bin", lk_lg_dir);   /* LK_JPITEMS v1: the original English + the names / lines of the Japanese items */
        if (lk_items_get() && lk_lg_exists(path)) { lk_lg_load(path); lk_lg_sel = 0; return; }
        lk_lg_unload(); return; }
    if (lk_lg_codes[i][0] == '#') snprintf(path, sizeof path, "%s", lk_lg_binfile);   /* LANDSTALKER_LANGBIN test aid */
    else { snprintf(path, sizeof path, "%s/%s.jpn.bin", lk_lg_dir, lk_lg_codes[i]); if (!lk_names_get() || !lk_lg_exists(path)) snprintf(path, sizeof path, "%s/%s.bin", lk_lg_dir, lk_lg_codes[i]); }
    lk_lg_load(path);
    if (!lk_lg_on) lk_lg_sel = 0;
    lk_vt_on = lk_vt_ok && lk_vt_ja();   /* LK_JPMENU v1 */
}
/* LK_JPITEMS v1 (user 2026-11-14: 'am liebsten die Sprites aus der originalen japanischen Fassung'; Options > Items: Original / Japanese, ~/.landstalker_items, env LANDSTALKER_ITEMS):
   four items are different things in the Japanese original (36 Pink Book, 41 T-back, 48 Bunny-chan, 54 bunny suit). Pictures: read at start from the player's own Japanese ROM in the folder
   of the started ROM (nothing shipped; added later = available at the next start) and kept at $810000; their frame pointers (sprite graphic $23, animation (id >> 3) * 4, frame (id & 7) * 4) in the in-memory ROM image point there while
   the option is on and back to the original values when it is off.  Names / lines: language file entries with string id | $8000 and item name index | $80 (tools/langbuild.py
   block 'items_jp') win while the option is on.  Without a Japanese ROM the option stays Original (no half switch: names without pictures). */
static int lk_ji_ok = -1, lk_ji_opt = -1, lk_ji_auto, lk_ji_n; static uint8_t lk_ji_id[8]; static uint32_t lk_ji_slot[8], lk_ji_old[8], lk_ji_new[8];
static uint32_t lk_ji_rd32(uint32_t a) { return (uint32_t)bus_peek8(a) << 24 | (uint32_t)bus_peek8(a + 1) << 16 | (uint32_t)bus_peek8(a + 2) << 8 | bus_peek8(a + 3); }
extern char lk_rom_file[1024];
static uint32_t lk_ji_b32(const uint8_t *r, uint32_t a) { return (uint32_t)r[a] << 24 | (uint32_t)r[a + 1] << 16 | (uint32_t)r[a + 2] << 8 | r[a + 3]; }
static long lk_ji_frame(const uint8_t *r, long sz, int id, uint32_t *start) {   /* bytes of one item frame in a ROM image (pieces + tile chunks; LZ77 = the last chunk, walked to its end): length or -1 */
    uint32_t base, ap, fp, pos; int n = 0, g;
    if (sz < 0x120200) return -1;
    base = lk_ji_b32(r, 0x120000u); ap = base + (uint32_t)(r[0x120004 + 4 * 0x23] << 8 | r[0x120005 + 4 * 0x23]) * 4u + (uint32_t)((id >> 3) & 7) * 4u;
    if (ap + 4 > (uint32_t)sz) return -1;
    ap = lk_ji_b32(r, ap) + (uint32_t)(id & 7) * 4u; if (ap + 4 > (uint32_t)sz) return -1;
    fp = lk_ji_b32(r, ap); pos = fp;
    for (;;) { if (pos + 2 > (uint32_t)sz) return -1; n++; pos += 2; if ((r[pos - 1] & 0x80) || n >= 8) break; }
    for (g = 0; g < 64; g++) { uint32_t h; if (pos + 2 > (uint32_t)sz) return -1; h = (uint32_t)(r[pos] << 8 | r[pos + 1]); pos += 2;
        if (h & 0x8000) { }
        else if (h & 0x2000) { long out = 0; for (;;) { int f, k, end = 0; if (pos >= (uint32_t)sz) return -1; f = r[pos++];   /* LZ77 as tools/romgfx.py lz77: flag bit 1 = literal, 0 = (offset 12 bit, length) pair, offset 0 = end */
                for (k = 0; k < 8 && !end; k++) { if ((f >> (7 - k)) & 1) { pos++; out++; } else { if (pos + 2 > (uint32_t)sz) return -1; if ((((r[pos] >> 4) << 8) | r[pos + 1]) == 0) end = 1; else out += 18 - (r[pos] & 15); pos += 2; } }
                if (end || out > 0x10000) break; }
            break; }
        else pos += (h & 0x0FFFu) * 2u;
        if (h & 0x4000) break; }
    if (pos > (uint32_t)sz || pos - fp > 0x4000u) return -1;
    *start = fp; return (long)(pos - fp);
}
/* LK_JPMENU v1 (user 2026-11-13: 'in der japanischen Fassung haben die Items sehr wohl Kana-Namen' / 'wir sind auf unserem Renderer, keine Mega-Drive-Beschraenkung'): the item names of the
   Start menu lists in Japanese = the original kana names, drawn with the Japanese MENU font.  Both are read at start from the player's Japanese ROM (font $00DBF2: 8x8 1bpp, slot = Japanese
   character code; names: the table after the special names, $2A43A).  The menu row words get VIRTUAL tile numbers $780 + Japanese code: nothing is written to VRAM, the own screen
   renderer (patch_own.py lk_scr_cell) draws those cells from lk_vt_gl (ink = colour 1 like Expand1bppTo4bpp $00DAD8).  Voicing marks ($7B / $7C, stored BEFORE the kana) go into the row
   ABOVE the kana like the Japanese PopulateItemSlot (row 1 of the 9 x 2 slot = marks, row 2 = kana; at most 8 kana).  Other languages: untouched (lk_vt_on = 0). */
static uint8_t lk_vt_nm[64][24], lk_vt_nl[64];
static void lk_vt_load(const uint8_t *r) {
    static const uint8_t sig[8] = { 0x41, 0xF9, 0x00, 0xFF, 0x2C, 0x84, 0x43, 0xFA }; uint32_t p = 0x2A3E4u; int i, c;   /* the special names (15) + the default name (1), then the 64 items at $2A43A */
    if (memcmp(r + 0xD978, sig, 8) || 0xD980 + (int16_t)(r[0xD980] << 8 | r[0xD981]) != 0xDBF2) { fprintf(stderr, "lang: Japanese menu font not where expected: menus stay English\n"); return; }
    for (c = 0; c < 128; c++) memcpy(lk_vt_gl[c], r + 0xDBF2 + 8 * c, 8);
    for (i = 0; i < 15 + 1; i++) p += 1u + r[p];
    for (i = 0; i < 64; i++) { int n = r[p], k, cols = 0; for (k = 0; k < n; k++) if (r[p + 1 + k] != 0x7B && r[p + 1 + k] != 0x7C) cols++;
        if (n < (int)sizeof lk_vt_nm[0] && cols <= 9) { memcpy(lk_vt_nm[i], r + p + 1, (size_t)n); lk_vt_nl[i] = (uint8_t)n; } p += 1u + (uint32_t)n; }
    lk_vt_ok = 1;
}
static void (*lk_vt_o_wn)(void);
static int lk_vt_ja(void);
static void lk_vt_h_wn(void) {   /* PopulateItemSlot_WriteItemName $00D5E4: d0 = string index (< $40 = item), d1 low byte != 0 = highlighted ($C000), a0 = slot (row 1) in the RAM tilemap */
    int idx = (int)(g_m68k.d[0] & 0xFFFF), k, col = 0; uint32_t a1 = g_m68k.a[0]; uint16_t base = (g_m68k.d[1] & 0xFF) ? 0xC000 : 0xA000;
    lk_vt_on = lk_vt_ok && lk_vt_ja();
    if (!lk_vt_on || idx >= 0x40 || !lk_vt_nl[idx]) { lk_vt_o_wn(); return; }
    for (k = 0; k < 9; k++) bus_write16(a1 + 2u * (uint32_t)k, (uint16_t)(base | 0x780));   /* row 1: blank (Japanese space), the marks below */
    for (k = 0; k < lk_vt_nl[idx]; k++) { int c = lk_vt_nm[idx][k] & 0x7F;
        if (c == 0x7B || c == 0x7C) bus_write16(a1 + 2u * (uint32_t)col, (uint16_t)(base | (0x780 + c)));
        else { bus_write16(a1 + 0x48u + 2u * (uint32_t)col, (uint16_t)(base | (0x780 + c))); col++; } }
    for (; col < 9; col++) bus_write16(a1 + 0x48u + 2u * (uint32_t)col, (uint16_t)(base | 0x780));
    g_m68k.a[1] = a1; g_m68k.a[0] = a1 + 0x12u; g_m68k.d[7] = (g_m68k.d[7] & 0xFFFF0000u) | 0xFFFFu;
    func_table_rts();
}
static int lk_ji_try(const char *path) {   /* a Japanese Landstalker ROM (2 MB, header region 'J', name LAND STALKER)? then copy the four item frames to $810000 */
    static const int ids[4] = { 36, 41, 48, 54 }; FILE *f; uint8_t hd[0x200]; uint8_t *r; long sz; uint32_t off = 0; int i, k;
    if (!(f = fopen(path, "rb"))) return 0;
    fseek(f, 0, SEEK_END); sz = ftell(f); fseek(f, 0, SEEK_SET);
    if (sz != 0x200000 || fread(hd, 1, sizeof hd, f) != sizeof hd || hd[0x1F0] != 'J' || hd[0x1F1] != ' ' || memcmp(hd + 0x120, "LAND STALKER", 12)) { fclose(f); return 0; }
    r = malloc((size_t)sz); fseek(f, 0, SEEK_SET); if (!r || fread(r, 1, (size_t)sz, f) != (size_t)sz) { fclose(f); free(r); return 0; } fclose(f);
    {   uint32_t tab = lk_ji_rd32(0x120000u) + (uint32_t)(bus_peek8(0x120004u + 4u * 0x23u) << 8 | bus_peek8(0x120005u + 4u * 0x23u)) * 4u;
        for (i = 0; i < 4; i++) { uint32_t st; long len = lk_ji_frame(r, sz, ids[i], &st); if (len <= 0 || off + (uint32_t)len > 0x10000u) { lk_ji_n = 0; free(r); return 0; }
            for (k = 0; k < len; k++) lk_ji_mem[(off + (uint32_t)k) ^ 1] = r[st + (uint32_t)k];
            lk_ji_id[lk_ji_n] = (uint8_t)ids[i]; lk_ji_slot[lk_ji_n] = lk_ji_rd32(tab + (uint32_t)((ids[i] >> 3) & 7) * 4u) + (uint32_t)(ids[i] & 7) * 4u;
            lk_ji_old[lk_ji_n] = lk_ji_rd32(lk_ji_slot[lk_ji_n]); lk_ji_new[lk_ji_n] = 0x810000u + off; lk_ji_n++; off += ((uint32_t)len + 1u) & ~1u; } }
    lk_vt_load(r);   /* LK_JPMENU v1 */
    free(r); fprintf(stderr, "lang: the Japanese item pictures from %s\n", path); return 1;
}
static int lk_ji_avail(void) {   /* looked up once per start: a Japanese ROM in the folder of the started ROM (LANDSTALKER_JPROM=<file> names one) */
    if (lk_ji_ok < 0) { char dir[1024], path[1300]; const char *e = getenv("LANDSTALKER_JPROM"); char *sl;
        lk_ji_ok = 0;
        if (e && *e) lk_ji_ok = lk_ji_try(e);
        else if (lk_rom_file[0]) {
            snprintf(dir, sizeof dir, "%s", lk_rom_file); sl = strrchr(dir, '/'); { char *bs = strrchr(dir, '\\'); if (bs && (!sl || bs > sl)) sl = bs; }
            if (sl) *sl = 0; else snprintf(dir, sizeof dir, ".");
#ifdef _WIN32
            { struct _finddata_t fd; intptr_t h; snprintf(path, sizeof path, "%s\\*", dir); h = _findfirst(path, &fd);
              if (h != -1) { do { if (!(fd.attrib & _A_SUBDIR) && fd.size == 0x200000) { snprintf(path, sizeof path, "%s\\%s", dir, fd.name); if (lk_ji_try(path)) { lk_ji_ok = 1; break; } } } while (_findnext(h, &fd) == 0); _findclose(h); } }
#else
            { DIR *d = opendir(dir); struct dirent *de; if (d) { while ((de = readdir(d))) { if (de->d_name[0] == '.') continue; snprintf(path, sizeof path, "%s/%s", dir, de->d_name); if (lk_ji_try(path)) { lk_ji_ok = 1; break; } } closedir(d); } }
#endif
        }
    }
    return lk_ji_ok;
}
int lk_items_get(void) {
    if (lk_ji_opt < 0) { const char *e = getenv("LANDSTALKER_ITEMS"); char path[512], line[16]; FILE *f; lk_ji_opt = 0;
        if (e && *e) lk_ji_opt = atoi(e) != 0;
        else { lk_lg_home(path, sizeof path, ".landstalker_items"); if ((f = fopen(path, "r"))) { if (fgets(line, sizeof line, f)) lk_ji_opt = atoi(line) != 0; fclose(f); } } }
    return lk_ji_opt && lk_ji_avail();
}
static void lk_ji_apply(void) { int i, on = lk_items_get(); lk_ji_map(); for (i = 0; i < lk_ji_n; i++) lk_lang_rom_patch32(lk_ji_slot[i], on ? lk_ji_new[i] : lk_ji_old[i]); }
static void lk_ji_set(int v) {
    char path[512]; FILE *f;
    lk_ji_opt = v != 0; lk_lg_home(path, sizeof path, ".landstalker_items"); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", lk_ji_opt); fclose(f); }
    lk_ji_apply(); if (lk_lg_hooked) lk_lg_apply(lk_lg_sel); else lk_lg_gen++;   /* lk_lg_apply counts lk_lg_gen too: the HUD / item info caches redraw the icons and names */
}
void lk_items_step(void) { if (!lk_ji_avail()) return; lk_items_get(); lk_ji_auto = 0; lk_ji_set(!lk_ji_opt); }
void lk_names_step(void) {   /* Options > Names: Localized <-> Japanese, applied at once, saved */
    char path[512]; FILE *f;
    lk_lg_nmopt = !lk_names_get();
    lk_lg_home(path, sizeof path, ".landstalker_names"); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", lk_lg_nmopt); fclose(f); }
    if (lk_lg_hooked) lk_lg_apply(lk_lg_sel);
}
uint32_t lk_lang_ui(int key, uint32_t def) { int i; for (i = 0; i < lk_lg_nui; i++) if (lk_lg_ui[i][0] == key) return lk_lg_ui[i][1]; return def; }   /* layout value of the current language or the original (US) value */
const char *lk_lang_tr(const char *en) {   /* our own UI text: the translation of an English word / phrase of the options menus (or the English text itself) */
    int t; if (!lk_lg_on || !en) return en;
    for (t = 0; t < lk_lg_ntext; t++) if (!strcmp(lk_lg_text[t].k, en)) return lk_lg_text[t].v;
    return en;
}
int lk_lang_count(void) { return lk_lg_nlang; }
const char *lk_lang_name(int i) { return i >= 0 && i < lk_lg_nlang ? lk_lg_names[i] : "?"; }
int lk_lang_get(void) { return lk_lg_sel; }
void lk_lang_step(void) {          /* Options > Language (root row above Quit Game): next language, applied at once and saved in ~/.landstalker_lang */
    char path[512]; FILE *f; int n = (lk_lg_sel + 1) % lk_lg_nlang;
    lk_lg_apply(n);
    { int tone = !strcmp(lk_lg_codes[lk_lg_sel], "en_tone"); lk_items_get();   /* LK_JPITEMS v1: 'English (JP)' sets Items = Japanese when chosen (LEFT / RIGHT pass through it: undone again) */
      if (tone && !lk_ji_opt && lk_ji_avail()) { lk_ji_auto = 1; lk_ji_set(1); } else if (!tone && lk_ji_auto) { lk_ji_auto = 0; lk_ji_set(0); } }
    lk_lg_home(path, sizeof path, ".landstalker_lang"); f = fopen(path, "w"); if (f) { fprintf(f, "%s\n", lk_lg_codes[lk_lg_sel]); fclose(f); }
}
static void lk_lang_install(void) {
    static int done; const char *e; char path[600], line[128]; FILE *f; int i, want = 0;
    if (done) return;
    done = 1;
    snprintf(lk_lg_codes[0], sizeof lk_lg_codes[0], "en"); snprintf(lk_lg_names[0], sizeof lk_lg_names[0], "English");
    lk_lg_exedir();
    snprintf(path, sizeof path, "%s/index.txt", lk_lg_dir);
    if ((f = fopen(path, "r"))) {      /* "code<TAB>name" per line, written by tools/langbuild.py */
        while (lk_lg_nlang < 8 && fgets(line, sizeof line, f)) { char *t = strchr(line, '\t'), *nl; if (!t) continue; *t++ = 0; if ((nl = strpbrk(t, "\r\n"))) *nl = 0;
            if (!strcmp(line, "ja") && !lk_ji_avail()) continue;   /* LK_JPLANG v1: Japanese only while a Japanese ROM lies next to the ROM (user 2026-11-14) */
            snprintf(lk_lg_codes[lk_lg_nlang], sizeof lk_lg_codes[0], "%s", line); snprintf(lk_lg_names[lk_lg_nlang], sizeof lk_lg_names[0], "%s", t); lk_lg_nlang++; }
        fclose(f);
    }
    e = getenv("LANDSTALKER_LANGBIN");                                     /* test aid: an explicit file becomes an extra language called 'Test' */
    if (e && *e && lk_lg_nlang < 8) { snprintf(lk_lg_binfile, sizeof lk_lg_binfile, "%s", e); snprintf(lk_lg_codes[lk_lg_nlang], sizeof lk_lg_codes[0], "#"); snprintf(lk_lg_names[lk_lg_nlang], sizeof lk_lg_names[0], "Test"); want = lk_lg_nlang++; }
    lk_lang_map();
    lk_lg_o_ics = func_table_lookup(0x022FCC); lk_lg_o_dc = func_table_lookup(0x0246B2); lk_lg_o_gnc = func_table_lookup(0x023044); lk_lg_o_skip = func_table_lookup(0x0294B6); lk_lg_o_dma = func_table_lookup(0x000DD6); lk_lg_o_pc = func_table_lookup(0x0231E2);
    if (lk_lg_o_ics && lk_lg_o_dc && lk_lg_o_gnc && lk_lg_o_skip && lk_lg_o_dma) {
        func_table_register(0x022FCC, lk_lg_h_ics); func_table_register(0x0246B2, lk_lg_h_dc); func_table_register(0x023044, lk_lg_h_gnc); func_table_register(0x0294B6, lk_lg_h_skip); func_table_register(0x000DD6, lk_lg_h_dma); if (lk_lg_o_pc) func_table_register(0x0231E2, lk_lg_h_pc); lk_lg_o_cpy = func_table_lookup(0x02335C); if (lk_lg_o_cpy) func_table_register(0x02335C, lk_lg_h_cpy); lk_vt_o_wn = func_table_lookup(0x00D5E4); if (lk_vt_o_wn) func_table_register(0x00D5E4, lk_vt_h_wn); lk_lg_hooked = 1;
    } else { fprintf(stderr, "lang: InitCompString / DecodeChar / GetNextChar / SkipToStringIndex not all found (%p %p %p %p)\n", (void *)lk_lg_o_ics, (void *)lk_lg_o_dc, (void *)lk_lg_o_gnc, (void *)lk_lg_o_skip); lk_lg_nlang = 1; return; }
    if (!want) {                                                            /* LANDSTALKER_LANG=<code> overrides the saved ~/.landstalker_lang */
        char code[16] = "";
        e = getenv("LANDSTALKER_LANG");
        if (e && *e) snprintf(code, sizeof code, "%s", e);
        else { lk_lg_home(path, sizeof path, ".landstalker_lang"); if ((f = fopen(path, "r"))) { if (fgets(line, sizeof line, f)) { char *nl = strpbrk(line, "\r\n"); if (nl) *nl = 0; snprintf(code, sizeof code, "%s", line); } fclose(f); } }
        for (i = 1; i < lk_lg_nlang; i++) if (!strcmp(code, lk_lg_codes[i])) want = i;
    }
    if (want || lk_names_get() || lk_items_get()) lk_lg_apply(want);   /* LK_LGNAMES v1: English with the Japanese names loads en.jpn.bin; LK_JPITEMS v1: en.items.bin */
    if (lk_items_get()) lk_ji_apply();   /* LK_JPITEMS v1: the Japanese item pictures */
}
'''
s = s.replace(anchor, module + anchor, 1)
h = "        lk_qs_install();   /* LK_QUICKSAVE v1 */\n"
assert s.count(h) == 1
s = s.replace(h, h + "        lk_lang_install();   /* " + VER + " */\n", 1)
open(p, "w").write(s)
print("func_table.c patched: " + VER)
