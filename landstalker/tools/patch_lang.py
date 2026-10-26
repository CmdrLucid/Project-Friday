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
#ifdef _WIN32
extern __declspec(dllimport) unsigned long __stdcall GetModuleFileNameA(void *, char *, unsigned long);
#else
#include <unistd.h>
#endif
typedef struct { uint16_t id; uint16_t n; const uint8_t *w; } LkLgStr;
typedef struct { uint8_t tab, idx, n; uint32_t addr; } LkLgName;
static LkLgStr *lk_lg_str; static int lk_lg_nstr;
static LkLgName *lk_lg_name; static int lk_lg_nname;
static const LkLgStr *lk_lg_cur; static int lk_lg_pos, lk_lg_ext, lk_lg_extcode;
static uint8_t *lk_lg_data;                                   /* the loaded language file (word streams are read from it) */
static int lk_lg_on, lk_lg_hooked;
static uint8_t lk_lg_mg[128], lk_lg_mgl[128][8];   /* menu font glyphs (8x8, 1bpp) of the extra characters, by character code */
static uint16_t lk_lg_ui[8][2]; static int lk_lg_nui;                  /* language file block 'ui': key, value (docs/TEXT_LAYER.md) */
static char lk_lg_codes[8][16], lk_lg_names[8][32]; static int lk_lg_nlang = 1, lk_lg_sel;   /* [0] = English (the original), then the languages of lang/index.txt */
static char lk_lg_dir[512], lk_lg_binfile[512];
static void (*lk_lg_o_dma)(void), (*lk_lg_o_ics)(void), (*lk_lg_o_dc)(void), (*lk_lg_o_gnc)(void), (*lk_lg_o_skip)(void);
static void lk_lg_put8(uint32_t off, uint8_t v) { lk_lang_mem[off ^ 1] = v; }
static void lk_lg_put16(uint32_t off, uint16_t v) { *(uint16_t *)(lk_lang_mem + off) = v; }
static uint16_t lk_lg_be16(const uint8_t *p) { return (uint16_t)(p[0] << 8 | p[1]); }
static uint32_t lk_lg_be32(const uint8_t *p) { return (uint32_t)p[0] << 24 | p[1] << 16 | p[2] << 8 | p[3]; }
static int lk_lg_cmp(const void *a, const void *b) { return (int)((const LkLgStr *)a)->id - (int)((const LkLgStr *)b)->id; }
static void lk_lg_unload(void) {
    lk_lg_cur = NULL; lk_lg_on = 0; lk_lg_nui = 0; memset(lk_lg_mg, 0, sizeof lk_lg_mg);
    free(lk_lg_str); lk_lg_str = NULL; lk_lg_nstr = 0; free(lk_lg_name); lk_lg_name = NULL; lk_lg_nname = 0; free(lk_lg_data); lk_lg_data = NULL;
    lk_lang_map(); lk_lang_rom_patch32(0x022E84u, 0x02A884u);   /* the original font */
}
static void lk_lg_load(const char *path) {
    FILE *f = fopen(path, "rb"); long sz; uint8_t *d; int i, ns, nn, nu, ng; const uint8_t *q; uint32_t nameoff = 0x8000;
    lk_lg_unload();
    if (!f) { fprintf(stderr, "lang: cannot open %s\n", path); return; }
    fseek(f, 0, SEEK_END); sz = ftell(f); fseek(f, 0, SEEK_SET); d = malloc((size_t)sz); if (fread(d, 1, (size_t)sz, f) != (size_t)sz) { fclose(f); free(d); return; } fclose(f);
    if (sz < 14 || memcmp(d, "LKLG", 4) || lk_lg_be16(d + 4) != 1) { fprintf(stderr, "lang: %s is not a language file\n", path); free(d); return; }
    ns = lk_lg_be16(d + 6); nn = lk_lg_be16(d + 8); nu = lk_lg_be16(d + 10); ng = lk_lg_be16(d + 12);
    q = d + 14; lk_lg_data = d; lk_lang_map(); memset(lk_lang_mem, 0, sizeof lk_lang_mem);
    {   const uint8_t *se = q, *ne = se + 8 * ns, *ue = ne + 7 * nn, *ge = ue + 4 * nu, *blob = ge + 39 * ng;
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
        /* font: the ROM's glyphs 0..$6B (30 bytes each) + the new ones, at $801000; MainFontPtr $022E84 -> there */
        for (i = 0; i < 0x6C * 30; i += 2) lk_lg_put16(0x1000u + (uint32_t)i, bus_read16(0x02A884u + (uint32_t)i));
        for (i = 0; i < ng; i++) { const uint8_t *g = ge + 39 * i; int k; for (k = 0; k < 30; k += 2) lk_lg_put16(0x1000u + 30u * g[0] + (uint32_t)k, lk_lg_be16(g + 1 + k)); lk_lg_mg[g[0]] = 1; memcpy(lk_lg_mgl[g[0]], g + 31, 8); }
        lk_lang_rom_patch32(0x022E84u, 0x801000u);
    }
    fprintf(stderr, "lang: loaded %s: %d strings, %d names, %d glyphs\n", path, ns, nn, ng);
    lk_lg_on = 1;
}
static void lk_lg_h_ics(void) {   /* InitCompString $022FCC: D0 = string id */
    uint16_t id = (uint16_t)g_m68k.d[0]; LkLgStr key, *r = NULL; key.id = id;
    lk_lg_o_ics();
    if (lk_lg_on) { lk_lang_map(); r = bsearch(&key, lk_lg_str, (size_t)lk_lg_nstr, sizeof *lk_lg_str, lk_lg_cmp); }
    lk_lg_cur = r; lk_lg_pos = 0; lk_lg_ext = 0;
    { static int lg_log = -1; if (lg_log < 0) lg_log = getenv("LANDSTALKER_LANGLOG") != NULL; if (lg_log) fprintf(stderr, "lang: string %04X %s at frame %ld\n", id, r ? "TRANSLATED" : "original", (long)platform_frame_number()); }   /* test aid */
}
static void lk_lg_h_dc(void) {    /* DecodeChar $0246B2: the next character in the Huffman character domain: glyph < $55, control $56 + k, end $55 */
    if (lk_lg_cur) {
        uint16_t w = lk_lg_pos < lk_lg_cur->n ? lk_lg_be16(lk_lg_cur->w + 2 * lk_lg_pos++) : 0xFFFF; uint8_t ch;
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
    for (i = 0; i < lk_lg_nname; i++) if (lk_lg_name[i].tab == tab && lk_lg_name[i].idx == idx) {
        g_m68k.a[2] = lk_lg_name[i].addr; g_m68k.d[7] = (g_m68k.d[7] & 0xFFFF0000u) | (uint32_t)(lk_lg_name[i].n - 1); return; }
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
static void lk_lg_apply(int i) {   /* switch the language now: 0 = English (original), others from <exe dir>/lang/<code>.bin */
    char path[600];
    if (i < 0 || i >= lk_lg_nlang) i = 0;
    lk_lg_sel = i;
    if (i == 0) { lk_lg_unload(); return; }
    if (lk_lg_codes[i][0] == '#') snprintf(path, sizeof path, "%s", lk_lg_binfile);   /* LANDSTALKER_LANGBIN test aid */
    else snprintf(path, sizeof path, "%s/%s.bin", lk_lg_dir, lk_lg_codes[i]);
    lk_lg_load(path);
    if (!lk_lg_on) lk_lg_sel = 0;
}
uint32_t lk_lang_ui(int key, uint32_t def) { int i; for (i = 0; i < lk_lg_nui; i++) if (lk_lg_ui[i][0] == key) return lk_lg_ui[i][1]; return def; }   /* layout value of the current language or the original (US) value */
int lk_lang_count(void) { return lk_lg_nlang; }
const char *lk_lang_name(int i) { return i >= 0 && i < lk_lg_nlang ? lk_lg_names[i] : "?"; }
int lk_lang_get(void) { return lk_lg_sel; }
void lk_lang_step(void) {          /* Options > Language (root row above Quit Game): next language, applied at once and saved in ~/.landstalker_lang */
    char path[512]; FILE *f; int n = (lk_lg_sel + 1) % lk_lg_nlang;
    lk_lg_apply(n);
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
            snprintf(lk_lg_codes[lk_lg_nlang], sizeof lk_lg_codes[0], "%s", line); snprintf(lk_lg_names[lk_lg_nlang], sizeof lk_lg_names[0], "%s", t); lk_lg_nlang++; }
        fclose(f);
    }
    e = getenv("LANDSTALKER_LANGBIN");                                     /* test aid: an explicit file becomes an extra language called 'Test' */
    if (e && *e && lk_lg_nlang < 8) { snprintf(lk_lg_binfile, sizeof lk_lg_binfile, "%s", e); snprintf(lk_lg_codes[lk_lg_nlang], sizeof lk_lg_codes[0], "#"); snprintf(lk_lg_names[lk_lg_nlang], sizeof lk_lg_names[0], "Test"); want = lk_lg_nlang++; }
    lk_lang_map();
    lk_lg_o_ics = func_table_lookup(0x022FCC); lk_lg_o_dc = func_table_lookup(0x0246B2); lk_lg_o_gnc = func_table_lookup(0x023044); lk_lg_o_skip = func_table_lookup(0x0294B6); lk_lg_o_dma = func_table_lookup(0x000DD6);
    if (lk_lg_o_ics && lk_lg_o_dc && lk_lg_o_gnc && lk_lg_o_skip && lk_lg_o_dma) {
        func_table_register(0x022FCC, lk_lg_h_ics); func_table_register(0x0246B2, lk_lg_h_dc); func_table_register(0x023044, lk_lg_h_gnc); func_table_register(0x0294B6, lk_lg_h_skip); func_table_register(0x000DD6, lk_lg_h_dma); lk_lg_hooked = 1;
    } else { fprintf(stderr, "lang: InitCompString / DecodeChar / GetNextChar / SkipToStringIndex not all found (%p %p %p %p)\n", (void *)lk_lg_o_ics, (void *)lk_lg_o_dc, (void *)lk_lg_o_gnc, (void *)lk_lg_o_skip); lk_lg_nlang = 1; return; }
    if (!want) {                                                            /* LANDSTALKER_LANG=<code> overrides the saved ~/.landstalker_lang */
        char code[16] = "";
        e = getenv("LANDSTALKER_LANG");
        if (e && *e) snprintf(code, sizeof code, "%s", e);
        else { lk_lg_home(path, sizeof path, ".landstalker_lang"); if ((f = fopen(path, "r"))) { if (fgets(line, sizeof line, f)) { char *nl = strpbrk(line, "\r\n"); if (nl) *nl = 0; snprintf(code, sizeof code, "%s", line); } fclose(f); } }
        for (i = 1; i < lk_lg_nlang; i++) if (!strcmp(code, lk_lg_codes[i])) want = i;
    }
    if (want) lk_lg_apply(want);
}
'''
s = s.replace(anchor, module + anchor, 1)
h = "        lk_qs_install();   /* LK_QUICKSAVE v1 */\n"
assert s.count(h) == 1
s = s.replace(h, h + "        lk_lang_install();   /* " + VER + " */\n", 1)
open(p, "w").write(s)
print("func_table.c patched: " + VER)
