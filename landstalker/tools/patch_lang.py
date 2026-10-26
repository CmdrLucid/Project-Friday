#!/usr/bin/env python3
"""Text layer runtime (docs/TEXT_LAYER.md step 3): loads the language binary built by tools/langbuild.py and replaces dialogue strings, name table entries and the font.
LANDSTALKER_LANGBIN=<file> loads it (test aid; the Options row and the saved setting come later); without it every hook is a plain pass through (English = bit exact).
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
void lk_lang_map(void) {
    cpu_memory_map *m = &m68k.memory_map[0x80];
    m->base = lk_lang_mem; m->read8 = NULL; m->read16 = NULL; m->write8 = NULL; m->write16 = NULL;
}
void lk_lang_rom_patch32(uint32_t addr, uint32_t v) {   /* writes a long into the in-memory ROM image (native 16-bit words, like bus_read16 reads them) */
    cpu_memory_map *m = &m68k.memory_map[(addr >> 16) & 0xFF];
    if (!m->base) return;
    *(uint16 *)(m->base + (addr & 0xFFFF)) = (uint16)(v >> 16); *(uint16 *)(m->base + (addr & 0xFFFF) + 2) = (uint16)v;
}

''' + a, 1)
    open(p, "w").write(s)
    print("bus.c patched: " + VER)
else:
    print("bus.c already patched: " + VER)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER); sys.exit(0)
anchor = "static void lk_qs_install(void) {"
assert s.count(anchor) == 1, "func_table.c: run patch_quicksave.py first"
module = r'''/* ---- ''' + VER + r''': text layer (tools/patch_lang.py, docs/TEXT_LAYER.md) ---- */
extern uint8_t lk_lang_mem[0x10000];
extern void lk_lang_map(void);
extern void lk_lang_rom_patch32(uint32_t addr, uint32_t v);
typedef struct { uint16_t id; uint16_t n; const uint8_t *w; } LkLgStr;
typedef struct { uint8_t tab, idx, n; uint32_t addr; } LkLgName;
static LkLgStr *lk_lg_str; static int lk_lg_nstr;
static LkLgName *lk_lg_name; static int lk_lg_nname;
static const LkLgStr *lk_lg_cur; static int lk_lg_pos, lk_lg_ext, lk_lg_extcode;
static int lk_lg_on;
static void (*lk_lg_o_ics)(void), (*lk_lg_o_dc)(void), (*lk_lg_o_gnc)(void), (*lk_lg_o_skip)(void);
static void lk_lg_put8(uint32_t off, uint8_t v) { lk_lang_mem[off ^ 1] = v; }
static void lk_lg_put16(uint32_t off, uint16_t v) { *(uint16_t *)(lk_lang_mem + off) = v; }
static uint16_t lk_lg_be16(const uint8_t *p) { return (uint16_t)(p[0] << 8 | p[1]); }
static uint32_t lk_lg_be32(const uint8_t *p) { return (uint32_t)p[0] << 24 | p[1] << 16 | p[2] << 8 | p[3]; }
static int lk_lg_cmp(const void *a, const void *b) { return (int)((const LkLgStr *)a)->id - (int)((const LkLgStr *)b)->id; }
static void lk_lg_load(const char *path) {
    FILE *f = fopen(path, "rb"); long sz; uint8_t *d; int i, ns, nn, nu, ng; const uint8_t *q; uint32_t nameoff = 0x8000;
    if (!f) { fprintf(stderr, "lang: cannot open %s\n", path); return; }
    fseek(f, 0, SEEK_END); sz = ftell(f); fseek(f, 0, SEEK_SET); d = malloc((size_t)sz); if (fread(d, 1, (size_t)sz, f) != (size_t)sz) { fclose(f); free(d); return; } fclose(f);
    if (sz < 14 || memcmp(d, "LKLG", 4) || lk_lg_be16(d + 4) != 1) { fprintf(stderr, "lang: %s is not a language file\n", path); free(d); return; }
    ns = lk_lg_be16(d + 6); nn = lk_lg_be16(d + 8); nu = lk_lg_be16(d + 10); ng = lk_lg_be16(d + 12);
    q = d + 14;
    {   const uint8_t *se = q, *ne = se + 8 * ns, *ue = ne + 8 * nn, *ge = ue + 4 * nu, *blob = ge + 31 * ng;
        lk_lg_str = calloc((size_t)ns + 1, sizeof *lk_lg_str); lk_lg_name = calloc((size_t)nn + 1, sizeof *lk_lg_name);
        for (i = 0; i < ns; i++) { const uint8_t *e = se + 8 * i; lk_lg_str[i].id = lk_lg_be16(e); lk_lg_str[i].w = blob + lk_lg_be32(e + 2); lk_lg_str[i].n = lk_lg_be16(e + 6); }
        qsort(lk_lg_str, (size_t)ns, sizeof *lk_lg_str, lk_lg_cmp); lk_lg_nstr = ns;
        for (i = 0; i < nn; i++) {
            const uint8_t *e = ne + 8 * i; int n = e[7], k;
            lk_lg_name[i].tab = e[0]; lk_lg_name[i].idx = e[1]; lk_lg_name[i].n = (uint8_t)n; lk_lg_name[i].addr = 0x800000u + nameoff;
            for (k = 0; k < n; k++) lk_lg_put8(nameoff + (uint32_t)k, blob[lk_lg_be32(e + 2) + (uint32_t)k]);
            nameoff += (uint32_t)n + 2;
        }
        lk_lg_nname = nn;
        /* font: the ROM's glyphs 0..$6B (30 bytes each) + the new ones, at $801000; MainFontPtr $022E84 -> there */
        for (i = 0; i < 0x6C * 30; i += 2) lk_lg_put16(0x1000u + (uint32_t)i, bus_read16(0x02A884u + (uint32_t)i));
        for (i = 0; i < ng; i++) { const uint8_t *g = ge + 31 * i; int k; for (k = 0; k < 30; k += 2) lk_lg_put16(0x1000u + 30u * g[0] + (uint32_t)k, lk_lg_be16(g + 1 + k)); }
        lk_lang_rom_patch32(0x022E84u, 0x801000u);
    }
    fprintf(stderr, "lang: loaded %s: %d strings, %d names, %d glyphs\n", path, ns, nn, ng);
    lk_lg_on = 1;   /* the blob stays allocated (word streams are read from it) */
}
static void lk_lg_h_ics(void) {   /* InitCompString $022FCC: D0 = string id */
    uint16_t id = (uint16_t)g_m68k.d[0]; LkLgStr key, *r; key.id = id;
    lk_lang_map();
    lk_lg_o_ics();
    r = bsearch(&key, lk_lg_str, (size_t)lk_lg_nstr, sizeof *lk_lg_str, lk_lg_cmp);
    lk_lg_cur = r; lk_lg_pos = 0; lk_lg_ext = 0;
}
static void lk_lg_h_dc(void) {    /* DecodeChar $0246B2: the next character in the Huffman character domain: glyph < $55, control $56 + k, end $55 */
    if (lk_lg_cur) {
        uint16_t w = lk_lg_pos < lk_lg_cur->n ? lk_lg_be16(lk_lg_cur->w + 2 * lk_lg_pos++) : 0xFFFF; uint8_t ch;
        if (w == 0xFFFF) { ch = 0x55; lk_lg_cur = NULL; }
        else if (w >= 0x8000) { ch = (uint8_t)(0x56 + (w == 0xFFEA ? 0 : 0)); /* control: find k from ~handler */
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
    lk_lang_map();
    lk_lg_o_skip();
    tab = tbl == 0x029552 ? 0 : tbl == 0x0296E0 ? 1 : tbl == 0x029730 ? 2 : tbl == 0x029732 ? 3 : tbl == 0x029A0A ? 4 : -1;
    if (tab < 0) return;
    for (i = 0; i < lk_lg_nname; i++) if (lk_lg_name[i].tab == tab && lk_lg_name[i].idx == idx) {
        g_m68k.a[2] = lk_lg_name[i].addr; g_m68k.d[7] = (g_m68k.d[7] & 0xFFFF0000u) | (uint32_t)(lk_lg_name[i].n - 1); return; }
}
static void lk_lang_install(void) {
    static int done; const char *e;
    if (done) return;
    done = 1;
    e = getenv("LANDSTALKER_LANGBIN");
    if (!e || !*e) return;
    lk_lang_map();
    lk_lg_load(e);
    if (!lk_lg_on) return;
    lk_lg_o_ics = func_table_lookup(0x022FCC); lk_lg_o_dc = func_table_lookup(0x0246B2); lk_lg_o_gnc = func_table_lookup(0x023044); lk_lg_o_skip = func_table_lookup(0x0294B6);
    if (lk_lg_o_ics && lk_lg_o_dc && lk_lg_o_gnc && lk_lg_o_skip) {
        func_table_register(0x022FCC, lk_lg_h_ics); func_table_register(0x0246B2, lk_lg_h_dc); func_table_register(0x023044, lk_lg_h_gnc); func_table_register(0x0294B6, lk_lg_h_skip);
    } else fprintf(stderr, "lang: InitCompString / DecodeChar / GetNextChar / SkipToStringIndex not all found (%p %p %p %p)\n", (void *)lk_lg_o_ics, (void *)lk_lg_o_dc, (void *)lk_lg_o_gnc, (void *)lk_lg_o_skip);
}
'''
s = s.replace(anchor, module + anchor, 1)
h = "        lk_qs_install();   /* LK_QUICKSAVE v1 */\n"
assert s.count(h) == 1
s = s.replace(h, h + "        lk_lang_install();   /* " + VER + " */\n", 1)
open(p, "w").write(s)
print("func_table.c patched: " + VER)
