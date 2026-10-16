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
VER = "LK_ITEMINFO v1"

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_ITEMINFO v1: item descriptions in the Start menu (tools/patch_iteminfo.py) ---- */
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
    module = r'''/* ---- LK_ITEMINFO v1: item descriptions in the bar box (tools/patch_iteminfo.py) ---- */
extern int lk_ii_get(void);
extern long platform_frame_number(void);
static gen_func_t lk_o_ii_use, lk_o_ii_eq;
static const struct { uint8_t id; const char *txt; } lk_ii_tab[] = {   /* only what the game code does (see the patch header); max ~34 characters */
    { 0x00, "Restores health" },
    { 0x01, "Charged: flames engulf the enemy" }, { 0x02, "Charged: ice whirlwind freezes" }, { 0x03, "Charged: lightning bolt" }, { 0x04, "Charged: earthquake hurts all" },
    { 0x05, "No damage from lava" }, { 0x06, "No damage from spiked floors" }, { 0x07, "Heals you while you walk" }, { 0x08, "No slipping on ice" },
    { 0x09, "Enemy damage x0.9" }, { 0x0A, "Enemy damage x0.8" }, { 0x0B, "Enemy damage x0.7" }, { 0x0C, "Enemy damage x0.5" },
    { 0x0D, "Immune to poison and paralysis" }, { 0x0E, "Immune to confusion" }, { 0x0F, "Sword charges 2x faster" }, { 0x10, "Sword charges 3x faster" },
    { 0x12, "Cures poison" }, { 0x15, "Cures confusion" }, { 0x1C, "Cures paralysis" },
};
static int lk_ii_menu(void) {   /* the Start menu: CheckForMenuOpen $007624, or its item branches (stack seen in the Use list: GameLoop -> $00774A -> $00D3BE ...) */
    int i, d = func_table_depth();
    for (i = 0; i < d; i++) { uint32_t c = func_table_stack(i); if (c == 0x007624u || c == 0x00774Au || c == 0x0076CAu || c == 0x0076C4u) return 1; }
    return 0;
}
static const char *lk_ii_text(int id) { unsigned i; for (i = 0; i < sizeof lk_ii_tab / sizeof lk_ii_tab[0]; i++) if (lk_ii_tab[i].id == id) return lk_ii_tab[i].txt; return NULL; }
static void lk_ii_draw(int id) {   /* id < 0: the plain bar */
    const char *t = id >= 0 ? lk_ii_text(id) : NULL;
    int want = t ? id : -1;
    M68kContext sv;
    if (want == lk_ii_cur) return;
    lk_ii_cur = want;
    sv = g_m68k;
    lk_call(0x024998u); lk_call(0x0234A8u);
    lk_menu_print_nodma("Use", 0x28); lk_menu_print_nodma("Equip", 0x78); lk_menu_print_nodma("Options", 0xC8);
    if (t) { uint8_t y0 = bus_read8(0xFF1129u); bus_write8(0xFF1129u, (uint8_t)(y0 + 0x10)); lk_menu_print_nodma(t, 0x08); bus_write8(0xFF1129u, y0); }
    lk_call(0x02355Au);   /* DMACopyTextboxTiles */
    g_m68k = sv;
}
static int lk_ii_owned(int id) {   /* GetItemQtyAndMaxQty $022ED0: d1 < 0 = the player does not have the item (the Equip grid only draws owned items) */
    M68kContext sv = g_m68k; int r;
    g_m68k.d[0] = (uint32_t)id; lk_call(0x022ED0u); r = (int16_t)(g_m68k.d[1] & 0xFFFFu);
    g_m68k = sv; return r >= 0;
}
static void lk_ii_leave(void) { if (lk_ii_cur >= 0) { if (getenv("LANDSTALKER_ITEMINFO_DEBUG")) printf("iteminfo: leave frame %ld\n", platform_frame_number()); lk_ii_draw(-1); } }
static void lk_ii_dbg(const char *w, int id) { static int last = -99; if (getenv("LANDSTALKER_ITEMINFO_DEBUG") && id != last) { printf("iteminfo: %s item $%02X\n", w, id & 0xFF); last = id; } }
static void lk_h_ii_use(void) {   /* InventoryMenu_UpdateCursorAt: Use list */
    lk_o_ii_use();
    if (getenv("LANDSTALKER_ITEMINFO_DEBUG")) { static int n2; if (n2++ < 3 && !lk_ii_menu()) { printf("iteminfo: not in menu, stack: "); func_table_dump_stack(stdout); } }
    if (lk_ii_get() && lk_ii_menu()) {
        int idx = ((int)bus_read16(0xFF2C06u) + (int)bus_read16(0xFF2C0Cu)) * 2 + (int)bus_read16(0xFF2C0Au);
        int id = idx >= 0 && idx < 64 ? bus_read8(0xFF2C5Cu + (uint32_t)idx) : 0xFF;
        if (getenv("LANDSTALKER_ITEMINFO_DEBUG")) { static int n; if (n++ < 40) printf("iteminfo: use idx %d id $%02X scroll %d row %d col %d frame %ld\n", idx, id & 0xFF, (int)bus_read16(0xFF2C06u), (int)bus_read16(0xFF2C0Cu), (int)bus_read16(0xFF2C0Au), platform_frame_number()); }
        lk_ii_dbg("use", id);
        lk_ii_draw(id == 0xFF || (id & 0x80) ? -1 : id);
    }
}
static void lk_h_ii_eq(void) {   /* $00EDAA: Equip grid cursor update */
    lk_o_ii_eq();
    if (getenv("LANDSTALKER_ITEMINFO_DEBUG")) { static int n3; if (n3++ < 2) { printf("iteminfo: equip hook, menu=%d stack: ", lk_ii_menu()); func_table_dump_stack(stdout); } }
    if (lk_ii_get() && lk_ii_menu()) {
        int col = (int)bus_read16(0xFF2C18u), row = (int)bus_read16(0xFF2C1Au), id = 0xFF;
        if (col >= 0 && col < 5 && row >= 0 && row < 4) id = bus_read8(0x00ECE0u + (uint32_t)(row * 5 + col));
        lk_ii_dbg("equip", id);
        lk_ii_draw((id & 0x80) || !lk_ii_owned(id) ? -1 : id);
    }
}
static void lk_ii_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_ii_use = func_table_lookup(0x00D714); lk_o_ii_eq = func_table_lookup(0x00EDAA);
    if (lk_o_ii_use && lk_o_ii_eq) { func_table_register(0x00D714, lk_h_ii_use); func_table_register(0x00EDAA, lk_h_ii_eq); } else fprintf(stderr, "iteminfo: cursor functions not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_carry_install();   /* LK_CARRY v1 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_ii_install();   /* LK_ITEMINFO v1 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
