#!/usr/bin/env python3
"""Optional 'Item Info' (2026-10-16, user wish; Options > Gameplay > Item Info Off / On, default Off): while the cursor is on an item in the Start menu's Use or Equip list, the
second line of the bottom bar box shows a short description (the original game has none).  Draw = the game's own text engine (like the Options tab): the bar is rebuilt
(`$024998` + `$0234A8`, the words Use / Equip / Options) and the description is printed one text line lower (`$FF1129` + $10).  Hooks: wrapper of InventoryMenu_UpdateCursorAt
`$00D714` (Use list: item = byte `$FF2C5C + (scroll `$FF2C06` + row `$FF2C0C`) * 2 + column `$FF2C0A`) and of `$00EDAA` (Equip grid: column `$FF2C18`, row `$FF2C1A`, item id = ROM
EquipInventoryLayout `$00ECE0` + row * 5 + column, bit 7 = 'nothing').  The bar is cleaned again when the bar loop runs (back from the list) (`lk_ii_leave` in patch_options.py).
Texts: facts READ FROM THE GAME CODE (2026-10-16), swords / wording (confusion) from https://shrines.rpgclassics.com/genesis/landstalker/equipment.shtml (user's tip; the page says Mars = poison only, the code also covers paralysis, effect 2; armour there '2x..5x', the code table is 90 / 80 / 70 / 50 % damage): armour = ArmourDefence table `$00770E` (damage x $E6 / $CC / $B3 / $80 / 256), boots = HandleLava `$006446` (Fireproof), HandleFloorSpikes
`$006456` (Iron), ice `$006598..` (Spike), `$016696` (Healing: while walking), rings = AddStatusEffect `$017776` (Mars: effects 0 poison and 2 paralysis; the font has no '%' so armour reads 'Enemy damage x0.9', Moon: effect 1 = the reversed-controls status, Mind Repair cures it) and
IncrementSwordCharge `$017858` (charge step `$20` normal, Saturn `$40`, Venus `$60`), cure items = the use handlers' status bit tests (Detox Grass bit 0, Mind Repair bit 1, Anti-Paralyze bit 2).
File ~/.landstalker_iteminfo, env LANDSTALKER_ITEMINFO=0|1 wins, LANDSTALKER_ITEMINFO_DEBUG=1 prints the item ids.  Needs patch_options.py and patch_difficulty.py before it.  Idempotent.
usage: patch_iteminfo.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_ITEMINFO v3"

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_ITEMINFO v3: item descriptions in the Start menu (tools/patch_iteminfo.py) ---- */
static int lk_ii_v = -1;   /* Options > Gameplay > Item Info Off / On, default Off; file ~/.landstalker_iteminfo, env LANDSTALKER_ITEMINFO=0|1 wins */
int lk_ii_get(void) {
    if (lk_ii_v < 0) { char p[512]; FILE *f; const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_ITEMINFO"); int v = 0; snprintf(p, sizeof p, "%s/.landstalker_iteminfo", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e) v = atoi(e); lk_ii_v = v ? 1 : 0; }
    return lk_ii_v;
}
void lk_ii_set(int v) { char p[512]; FILE *f; const char *h = getenv("HOME"); lk_ii_get(); lk_ii_v = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_iteminfo", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_ii_v); fclose(f); } }
'''
    s = s.replace(a, module + a, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "lk_carry_install" in s and "lk_ii_cur" in s, "func_table.c: run patch_options.py / patch_carry.py first"
    module = r'''/* ---- LK_ITEMINFO v3: item descriptions in the bar box (tools/patch_iteminfo.py) ---- */
extern int lk_ii_get(void);
extern long platform_frame_number(void);
static gen_func_t lk_o_ii_use, lk_o_ii_eq;
static const struct { uint8_t id; const char *txt; } lk_ii_tab[] = {   /* only what the game code does (see the patch header); max ~34 characters */
    { 0x00, "Restores HP, Friday revives you" },
    { 0x01, "Charged: flames engulf the enemy" }, { 0x02, "Charged: ice whirlwind freezes" }, { 0x03, "Charged: lightning bolt" }, { 0x04, "Charged: earthquake hurts all" },
    { 0x05, "No damage from lava" }, { 0x06, "No damage from spiked floors" }, { 0x07, "Heals you while you walk" }, { 0x08, "No slipping on ice" },
    { 0x09, "Enemy damage x0.9" }, { 0x0A, "Enemy damage x0.8" }, { 0x0B, "Enemy damage x0.7" }, { 0x0C, "Enemy damage x0.5" },
    { 0x0D, "Immune to poison and paralysis" }, { 0x0E, "Immune to confusion" }, { 0x0F, "Sword charges 2x faster" }, { 0x10, "Sword charges 3x faster" },
    { 0x12, "Cures poison" }, { 0x15, "Cures confusion" }, { 0x1C, "Cures paralysis" }, { 0x2E, "Cures poison and paralysis" }, { 0x2D, "Restores HP completely" },
    { 0x13, "Earthquake hurts monsters in range" }, { 0x14, "Fills the sword meter for a while" },
    { 0x16, "Entry to the Casino" }, { 0x17, "Cuts down discolored trees" }, { 0x1A, "Lights up dark rooms" }, { 0x1B, "Makes Miro run from Nigel" },
    { 0x1E, "Powers the Lighthouse light" }, { 0x1F, "Breaks the Mir Tower barrier" }, { 0x20, "Calls Einstein, talks to dogs" },
    { 0x19, "Lets you buy from the warehouse" }, { 0x21, "Jewel for the Gola Eye" }, { 0x22, "Jewel for the Gola Eye" }, { 0x28, "Jewel for the Gola Eye" }, { 0x2A, "Jewel for the Gola Eye" }, { 0x34, "Jewel for the Gola Eye" },
    { 0x27, "Shows where the 5 jewels are" }, { 0x29, "Trade HP for gold, only once" }, { 0x2B, "Opens King Nole Cave again" }, { 0x2C, "Random effects, bad or good" },
    { 0x2F, "Used to make a raft" }, { 0x30, "Shows how much you have done" }, { 0x31, "Opens the Swamp Shrine door" }, { 0x32, "Opens locked doors" },
    { 0x33, "Allows entry to Mercator" }, { 0x35, "Rings near a Life Stock" }, { 0x36, "Makes Friday happy or mad" },
    { 0x37, "Gola treasure for the Palace" }, { 0x38, "Gola treasure for the Palace" }, { 0x39, "Gola treasure for the Palace" },
};
static int lk_ii_menu(void) {   /* the Start menu: CheckForMenuOpen $007624, or its item branches (stack seen in the Use list: GameLoop -> $00774A -> $00D3BE ...) */
    int i, d = func_table_depth();
    for (i = 0; i < d; i++) { uint32_t c = func_table_stack(i); if (c == 0x007624u || c == 0x00774Au || c == 0x0076CAu || c == 0x0076C4u) return 1; }
    return 0;
}
static int lk_ii_tabdraw(void) {   /* the bar is switching tabs (MenuBarRight $024916 / MenuBarLeft $024952 redraw the list and call the cursor update): no description then, else it flickers (user recording 2026-10-16 22:45) */
    int i, d = func_table_depth();
    for (i = 0; i < d; i++) { uint32_t c = func_table_stack(i); if (c == 0x024916u || c == 0x024952u) return 1; }
    return 0;
}
extern int lk_lang_gen(void);   /* tools/patch_lang.py: counts language changes (the cached bars are in the old language) */
static const char *lk_ii_text(int id) { unsigned i; for (i = 0; i < sizeof lk_ii_tab / sizeof lk_ii_tab[0]; i++) if (lk_ii_tab[i].id == id) return lk_lang_tr(lk_ii_tab[i].txt); return NULL; }
/* Drawing is SLICED and CACHED (user report: the game hung briefly when the cursor landed on an item with a description): the game's text engine costs ~0.14 ms per character here (a whole bar with a
   description ~6 ms on a PC, more on the Deck), so one draw in one frame was a visible hitch.  A job renders the bar box (clear, the three words, the description, the divider line) into the text buffer
   $FF3900 a few characters per call (every call = one cursor update = about one frame; nothing is DMA'd before the end), then the finished buffer is cached; a cached item is applied with a plain copy +
   queued DMA.  The last DMA is only QUEUED (DMACopyTextboxTiles ends in FlushDMACopyQueue = a wait for the next VBlank, one more frame). */
#define LK_II_WORDS 0x0900u   /* DMA size of the text box with the inventory open (QueueDMAOp counts WORDS: 4608 bytes = two 16 pixel lines of $900; $0D80 = three lines is the normal dialogue box) */
#define LK_II_BUF (LK_II_WORDS * 2u)
#define LK_II_BUDGET 12
#include <time.h>
static uint8_t *lk_ii_cache[0x41];
static struct { int on, id, step, pos, x; uint8_t y0; } lk_ii_job;
static uint8_t lk_ii_y0s;   /* text y of the first line, remembered with the plain bar */
/* The list of the Use screen lives in the game's g_Buffer ($FF2C00 + $84, row stride $48, 4 tile rows per item row) and runs on into the text tile buffer $FF3900 from about the 11th item row on
   (user: garbage icons when scrolling down the Use list with Item Info On).  The text engine only draws into $FF3900, so the bar is built there ONLY while it runs: lk_ii_grab saves the game's bytes,
   the bar lives in lk_ii_work between slices, and lk_ii_release puts the game's bytes back once the queued DMA has been done by the VBlank handler (wrapper of ProcessQueuedDMAOps below). */
static uint8_t lk_ii_work[LK_II_BUF], lk_ii_save[LK_II_BUF];
static int lk_ii_dirty, lk_ii_inslice;   /* inslice: the game's own text functions called by a slice wait for VBlanks, the buffer must stay ours then */
static void lk_ii_grab(void) { uint32_t i; if (lk_ii_dirty) return; for (i = 0; i < LK_II_BUF; i++) lk_ii_save[i] = bus_read8(0xFF3900u + i); lk_ii_dirty = 1; }
static void lk_ii_release(void) { uint32_t i; if (!lk_ii_dirty) return; for (i = 0; i < LK_II_BUF; i++) bus_write8(0xFF3900u + i, lk_ii_save[i]); lk_ii_dirty = 0; }
static int lk_ii_slot(int id) { return id < 0 ? 0x40 : (id & 0x3F); }
static void lk_ii_dma(void) {   /* queue the text box tiles for the next VBlank */
    M68kContext sv = g_m68k;
    g_m68k.d[0] = (g_m68k.d[0] & 0xFFFF0000u) | LK_II_WORDS; g_m68k.a[0] = 0xFF3900u; g_m68k.a[1] = 0x00A500u; lk_call(0x0002C6u); lk_call(0x0002A2u);   /* QueueDMAOp, EnableDMAQueueProcessing */
    g_m68k = sv;
}
static void lk_ii_putchars(const char *t, int n) { int i; for (i = 0; i < n; i++) { g_m68k.d[0] = (uint32_t)lk_chr(t[i]); lk_call(0x0230CAu); } }   /* ProcessChar */
static void lk_ii_print_at(const char *t, int x) { t = lk_lang_tr(t); bus_write32(0xFF1844, 0); bus_write8(0xFF1155, 0); bus_write8(0xFF1144, 3); bus_write16(0xFF1194, (uint16_t)x); lk_ii_putchars(t, (int)strlen(t)); }
static void lk_ii_line(void) {   /* divider: a 1 pixel line between the words and the description, straight into the tile buffer (4 bpp: a 16 pixel text line = 8 pixel columns of two tiles = 64 bytes, line stride $900, pixel row r at r * 4) */
    const char *e = getenv("LANDSTALKER_ITEMINFO_LINE"); uint8_t col = e ? (uint8_t)atoi(e) : 0x0B;   /* palette nibble $B = white, like the box border */
    int cx, k;
    for (cx = 1; cx < 35; cx++) for (k = 0; k < 4; k++) bus_write8(0xFF3900u + (uint32_t)lk_ii_job.y0 / 16u * 0x900u + (uint32_t)cx * 64u + 14u * 4u + (uint32_t)k, (uint8_t)((col << 4) | col));
}
static void lk_ii_apply(int id) {   /* a finished buffer from the cache */
    uint32_t i; const uint8_t *c = lk_ii_cache[lk_ii_slot(id)];
    lk_ii_grab();
    for (i = 0; i < LK_II_BUF; i++) bus_write8(0xFF3900u + i, c[i]);
    lk_ii_dma(); lk_ii_cur = id;
}
static void lk_ii_job_run0(void);
static void lk_ii_job_run(void) {   /* one slice, with the bar loaded into $FF3900 only while it runs; timing (LANDSTALKER_ITEMINFO_DEBUG): the longest slice */
    int pend = lk_ii_dirty; uint32_t i;
    lk_ii_grab(); lk_ii_inslice = 1;
    for (i = 0; i < LK_II_BUF; i++) bus_write8(0xFF3900u + i, lk_ii_work[i]);
    if (getenv("LANDSTALKER_ITEMINFO_DEBUG")) { struct timespec a, b; long us; static long mx; clock_gettime(CLOCK_MONOTONIC, &a); lk_ii_job_run0(); clock_gettime(CLOCK_MONOTONIC, &b); us = (long)((b.tv_sec - a.tv_sec) * 1000000L + (b.tv_nsec - a.tv_nsec) / 1000L); if (us > mx) { mx = us; printf("iteminfo: slice %ld us (max)\n", us); } }
    else lk_ii_job_run0();
    lk_ii_inslice = 0;
    if (lk_ii_job.on) { for (i = 0; i < LK_II_BUF; i++) lk_ii_work[i] = bus_read8(0xFF3900u + i); if (!pend) lk_ii_release(); }   /* not finished: the bar waits in lk_ii_work; finished: the DMA is queued and the game's bytes come back after it */
}
static void lk_ii_job_run0(void) {   /* one slice of the current job */
    int budget = LK_II_BUDGET; const char *t = lk_ii_job.id >= 0 ? lk_ii_text(lk_ii_job.id) : NULL;
    M68kContext sv = g_m68k;
    while (budget > 0 && lk_ii_job.on) {
        switch (lk_ii_job.step) {
        case 0: lk_call(0x024998u); lk_call(0x0234A8u); lk_ii_job.y0 = bus_read8(0xFF1129u); lk_ii_job.step = 1; budget -= 4; break;
        case 1: lk_ii_print_at("Use", lk_bar_tx[0]); lk_ii_job.step = 2; budget -= 3; break;
        case 2: lk_ii_print_at("Equip", lk_bar_tx[1]); lk_ii_job.step = 3; budget -= 5; break;
        case 3: {
            uint32_t i; uint8_t *c = lk_ii_cache[0x40];
            lk_ii_print_at("Options", lk_bar_tx[2]); lk_ii_job.step = t ? 4 : 6; budget -= 7; lk_ii_job.pos = 0; lk_ii_job.x = 0x10;
            if (!c) c = lk_ii_cache[0x40] = (uint8_t *)malloc(LK_II_BUF);   /* the plain bar (words only) is kept: later descriptions start from it */
            if (c) { for (i = 0; i < LK_II_BUF; i++) c[i] = bus_read8(0xFF3900u + i); lk_ii_y0s = lk_ii_job.y0; }
            break; }
        case 4: {   /* the description, a few characters per slice (the x of the next character is kept in the job) */
            int n = (int)strlen(t) - lk_ii_job.pos, y0 = lk_ii_job.y0;
            if (n > budget) n = budget;
            bus_write32(0xFF1844, 0); bus_write8(0xFF1155, 0); bus_write8(0xFF1144, 3); bus_write16(0xFF1194, (uint16_t)lk_ii_job.x); bus_write8(0xFF1129u, (uint8_t)(y0 + 0x10));
            lk_ii_putchars(t + lk_ii_job.pos, n);
            lk_ii_job.x = (int)bus_read16(0xFF1194); bus_write8(0xFF1129u, (uint8_t)y0);
            lk_ii_job.pos += n; budget -= n;
            if (lk_ii_job.pos >= (int)strlen(t)) lk_ii_job.step = 5;
            break; }
        case 5: lk_ii_line(); lk_ii_job.step = 6; break;
        default: {   /* finished: show it and remember it */
            uint32_t i; uint8_t *c = lk_ii_cache[lk_ii_slot(lk_ii_job.id)];
            if (!c) c = lk_ii_cache[lk_ii_slot(lk_ii_job.id)] = (uint8_t *)malloc(LK_II_BUF);
            if (c) for (i = 0; i < LK_II_BUF; i++) c[i] = bus_read8(0xFF3900u + i);
            lk_ii_dma(); lk_ii_cur = lk_ii_job.id; lk_ii_job.on = 0;
            if (getenv("LANDSTALKER_ITEMINFO_DEBUG")) printf("iteminfo: drawn %d frame %ld\n", lk_ii_cur, platform_frame_number());
            break; }
        }
    }
    g_m68k = sv;
}
static void lk_ii_draw(int id) {   /* id < 0: the plain bar; called by the cursor hooks at every update */
    { static int seen; int g = lk_lang_gen(), i; if (g != seen) { seen = g; lk_ii_job.on = 0; lk_ii_cur = -2; for (i = 0; i < 0x41; i++) { free(lk_ii_cache[i]); lk_ii_cache[i] = NULL; } } }   /* language changed: rebuild every bar */
    const char *t = id >= 0 ? lk_ii_text(id) : NULL;
    int want = t ? id : -1;
    if (lk_ii_job.on && lk_ii_job.id == want) { lk_ii_job_run(); return; }   /* continue */
    if (!lk_ii_job.on && want == lk_ii_cur) return;                           /* already shown */
    lk_ii_job.on = 0;
    if (lk_ii_cache[lk_ii_slot(want)]) { lk_ii_apply(want); if (getenv("LANDSTALKER_ITEMINFO_DEBUG")) printf("iteminfo: cached %d frame %ld\n", want, platform_frame_number()); return; }
    lk_ii_job.on = 1; lk_ii_job.id = want; lk_ii_job.step = 0; lk_ii_job.pos = 0;
    if (want >= 0 && lk_ii_cache[0x40]) {   /* start from the cached plain bar: only the description has to be rendered */
        memcpy(lk_ii_work, lk_ii_cache[0x40], LK_II_BUF);
        lk_ii_job.y0 = lk_ii_y0s; lk_ii_job.step = 4; lk_ii_job.x = 0x10;
    }
    lk_ii_job_run();
}
static void lk_ii_leave(void) { lk_ii_job.on = 0; if (lk_ii_cur >= 0) lk_ii_draw(-1); }
static void lk_ii_dbg(const char *w, int id) { static int last = -99; if (getenv("LANDSTALKER_ITEMINFO_DEBUG") && id != last) { printf("iteminfo: %s item $%02X\n", w, id & 0xFF); last = id; } }
static void lk_h_ii_use(void) {   /* InventoryMenu_UpdateCursorAt: Use list; the bar is drawn BEFORE the original, whose wait for the VBlank runs the queued DMA and gives the game's list bytes back (lk_h_ii_pq) */
    if (lk_ii_get() && lk_ii_menu() && !lk_ii_tabdraw()) {
        int idx = ((int)bus_read16(0xFF2C06u) + (int)bus_read16(0xFF2C0Cu)) * 2 + (int)bus_read16(0xFF2C0Au);
        int id = idx >= 0 && idx < 64 ? bus_read8(0xFF2C5Cu + (uint32_t)idx) : 0xFF;
        lk_ii_dbg("use", id);
        lk_ii_draw(id == 0xFF || (id & 0x80) ? -1 : id);
    }
    lk_o_ii_use();
}
static int lk_ii_owned(int id) {   /* GetItemQtyAndMaxQty $022ED0: d1 < 0 = the player does not have the item (the Equip grid only draws owned items) */
    M68kContext sv = g_m68k; int r;
    g_m68k.d[0] = (uint32_t)id; lk_call(0x022ED0u); r = (int16_t)(g_m68k.d[1] & 0xFFFFu);
    g_m68k = sv; return r >= 0;
}
static void lk_h_ii_eq(void) {   /* $00EDAA: Equip grid cursor update (same order as the Use list) */
    if (lk_ii_get() && lk_ii_menu() && !lk_ii_tabdraw()) {
        int col = (int)bus_read16(0xFF2C18u), row = (int)bus_read16(0xFF2C1Au), id = 0xFF;
        if (col >= 0 && col < 5 && row >= 0 && row < 4) id = bus_read8(0x00ECE0u + (uint32_t)(row * 5 + col));
        lk_ii_dbg("equip", id);
        lk_ii_draw((id & 0x80) || !lk_ii_owned(id) ? -1 : id);
    }
    lk_o_ii_eq();
}
static void (*lk_o_ii_pq)(void);
static void lk_h_ii_pq(void) {   /* ProcessQueuedDMAOps $001340 (VBlank): after the whole queue is done the text tile buffer may be given back to the game's list */
    lk_o_ii_pq();
    if (lk_ii_dirty && !lk_ii_inslice && bus_read8(0xFF0F8Du) == 0) lk_ii_release();
}
static void lk_ii_install(void) {
    static int done;
    if (done) return;
    done = 1;
    memset(lk_ii_work, 0xAA, sizeof lk_ii_work);   /* the text engine's background (ClearTextBuffer fills $AAAAAAAA) */
    lk_o_ii_pq = func_table_lookup(0x001340); if (lk_o_ii_pq) func_table_register(0x001340, lk_h_ii_pq); else fprintf(stderr, "iteminfo: ProcessQueuedDMAOps not found\n");
    lk_o_ii_use = func_table_lookup(0x00D714); lk_o_ii_eq = func_table_lookup(0x00EDAA);
    if (lk_o_ii_use && lk_o_ii_eq) { func_table_register(0x00D714, lk_h_ii_use); func_table_register(0x00EDAA, lk_h_ii_eq); } else fprintf(stderr, "iteminfo: cursor functions not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_carry_install();   /* LK_CARRY v1 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_ii_install();   /* LK_ITEMINFO v3 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
