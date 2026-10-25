#!/usr/bin/env python3
"""Quick Equip (2026-10-24, user wish: 'quick equip items', 'Equip auf R2'): hold the binding 'Quick Equip' (the game stands still meanwhile) (pad R2, keyboard Q; Options > Keybindings) and press a direction:
UP = next sword, RIGHT = next armour, DOWN = next boots, LEFT = next ring (cycles through the pieces of that kind that Nigel owns).  While it is held the directions do not move Nigel.
How: tools/patch_keys.py (input.c) calls platform_equip_request(category) on a new direction press; this patch (func_table.c) wraps ProcessActionButton ($0066AC, once per map pass, like Quick Items):
the request is taken there when no dialogue / cutscene runs ($FF12DE = 0) and Nigel lives ($FF543E != 0), else it is dropped after 8 frames with the error sound.
Applying a piece = what the Equip menu does when it closes: the cursor nibble of the category in $FF1BF0 (index 1..4 into EquipInventoryLayout $00ECE0) and the equipped byte $FF114E + category;
sword: charge counter $FF120A = 0 and the HUD refresh (j_RefreshSwordChargeHUD / MarkHUDForUpdate / RefreshHUD), UpdateEquipPal $0078B6 and LoadMagicSwordGfx $0077A6 (the sword graphics);
armour: UpdatePlayerDefence $0076EC.  Ownership = GetItemQtyAndMaxQty $022ED0 (quantity > 0).  A short on-screen text names the piece (lk_osd_say).  Test aid: LANDSTALKER_EQREQ="f:c,f:c" posts category c at frame f.
Needs patch_quick.py and patch_quicksave.py before it.  Idempotent.  usage: patch_equip.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_EQUIP v1"
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_EQUIP v1: quick equip request (tools/patch_equip.py) ---- */
static int lk_eq_req = -1; static long lk_eq_req_frame;
static long lk_eq_stamp = -100;
void lk_eq_stamp_now(void) { lk_eq_stamp = platform_frame_number(); }
int lk_eq_active(void) { return platform_frame_number() - lk_eq_stamp < 4; }   /* the game's map pass ran a moment ago = a save is loaded and nothing blocks (no title / menu / dialogue): the overlay shows only then */
void platform_equip_request(int cat) { lk_eq_req = cat; lk_eq_req_frame = platform_frame_number(); }
int lk_eq_take(void) {   /* called by the game side once per map pass: -1 none, 0..3 = sword / armour / boots / ring; requests older than 8 frames are dropped (the game was inside a menu / text box) */
    static const char *sched; static int init; int r = lk_eq_req; long f = platform_frame_number();
    if (!init) { init = 1; sched = getenv("LANDSTALKER_EQREQ"); }
    if (r < 0 && sched) { char l[256], key[32]; int c; snprintf(l, sizeof l, ",%s,", sched); for (c = 0; c < 4; c++) { snprintf(key, sizeof key, ",%ld:%d,", f, c); if (strstr(l, key)) r = c; } }
    lk_eq_req = -1;
    if (r >= 0 && lk_eq_req_frame && f - lk_eq_req_frame >= 8) r = -2;
    return r;
}
'''
    s = s.replace(a, module + a, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1
    module = r'''/* ---- LK_EQUIP v1: quick equip (tools/patch_equip.py) ---- */
extern int lk_eq_take(void);
extern void lk_eq_stamp_now(void);
extern int lk_eq_is_held(void);
extern void lk_quick_capture(int id);
extern int lk_quick_icon_have(int id);
extern void lk_osd_equip_flash(int cat);
extern int lk_osd_equip_armed(int cat);
extern void lk_osd_equip_disarm(void);
static gen_func_t lk_o_cur_eq;
extern void lk_osd_say(const char *t);
static gen_func_t lk_o_pab_eq;
static int lk_eq_owned(int id) { M68kContext sv = g_m68k; int q, nc = lk_no_charge; g_m68k.d[0] = (uint32_t)id; lk_no_charge = 1; lk_call(0x022ED0u); lk_no_charge = nc; q = (int16_t)(g_m68k.d[1] & 0xFFFF); g_m68k = sv; return q > 0; }
static void lk_eq_apply(int cat) {
    static const uint8_t lay[4][4] = { { 1, 3, 2, 4 }, { 9, 10, 11, 12 }, { 7, 5, 6, 8 }, { 15, 13, 14, 16 } };   /* EquipInventoryLayout $00ECE0 without its header byte: Magic Thunder Ice Gaia / Steel Chrome Shell Hyper / Healing Fireproof Iron Spike / Saturn Mars Moon Venus */
    static const char *nm[4][4] = { { "MAGIC", "THUNDER", "ICE", "GAIA" }, { "STEEL", "CHROME", "SHELL", "HYPER" }, { "HEALING", "FIREPROOF", "IRON", "SPIKE" }, { "SATURN", "MARS", "MOON", "VENUS" } };
    static const char *kind[4] = { "SWORD", "ARMOUR", "BOOTS", "RING" };
    int cur = bus_read8(0xFF114Eu + (uint32_t)cat), idx = -1, k, j = -1; char t[48];
    if (!lk_osd_equip_armed(cat)) { lk_osd_equip_flash(cat); return; }   /* first press of a direction only shows the pieces (user: switched by accident too often), the second press switches */
    for (k = 0; k < 4; k++) if (lay[cat][k] == cur) idx = k;
    for (k = 1; k <= 4 && j < 0; k++) { int c = (idx + k + 4) % 4; if (lay[cat][c] != cur && lk_eq_owned(lay[cat][c])) j = c; }
    if (j < 0) { lk_snd(0x00DBBEu); snprintf(t, sizeof t, "NO OTHER %s", kind[cat]); lk_osd_say(t); return; }
    { uint16_t w = bus_read16(0xFF1BF0u); w = (uint16_t)((w & ~(0xFu << (4 * cat))) | ((uint16_t)(j + 1) << (4 * cat))); bus_write16(0xFF1BF0u, w); }
    bus_write8(0xFF114Eu + (uint32_t)cat, lay[cat][j]);
    { M68kContext sv = g_m68k;
      if (cat == 0) { bus_write16(0xFF120Au, 0); lk_call(0x0103AEu); lk_call(0x01036Cu); lk_call(0x010340u); }
      if (cat == 1) lk_call(0x0076ECu);
      lk_call(0x0078B6u);                                    /* UpdateEquipPal: the sword / armour colours of Nigel's sprite in the base palette */
      if (cat == 0) lk_call(0x0077A6u);                      /* LoadMagicSwordGfx */
      lk_call(0x000242u);                                    /* CopyBasePalleteToActivePalette: without it the old colours stay on screen (user: 'sieht noch aus wie Gaia') */
      lk_call(0x0002A8u);                                    /* FlushDMACopyQueue */
      g_m68k = sv; }
    lk_osd_equip_flash(cat);
    lk_snd(LK_SND_SELECT);
    snprintf(t, sizeof t, "%s: %s", kind[cat], nm[cat][j]); lk_osd_say(t);
    if (getenv("LANDSTALKER_EQ_DEBUG")) fprintf(stderr, "equip: category %d -> item %d (index %d)\n", cat, lay[cat][j], j + 1);
}
uint8_t lk_eq_own[16];   /* ownership of the 16 equipment pieces (sword 0..3, armour 4..7, boots 8..11, ring 12..15 in layout order), refreshed by the game side; read by the overlay */
static const uint8_t lk_eq_ids[16] = { 1, 3, 2, 4, 9, 10, 11, 12, 7, 5, 6, 8, 15, 13, 14, 16 };
static void lk_eq_scan(void) { int k; for (k = 0; k < 16; k++) lk_eq_own[k] = (uint8_t)lk_eq_owned(lk_eq_ids[k]); }
static void lk_eq_capture_missing(void) {   /* the Start menu is open and bright: take the icons of the owned pieces from VRAM (once, saved in ~/.landstalker_quick_icons) */
    int k; for (k = 0; k < 16; k++) if (!lk_quick_icon_have(lk_eq_ids[k]) && lk_eq_owned(lk_eq_ids[k])) lk_quick_capture(lk_eq_ids[k]);
}
static gen_func_t lk_o_wuv_eq;
static void lk_h_wuv_eq(void) {   /* WaitUntilVBlank $000B5E: while the Start menu is open every ~half second try to take the icons (the cursor hook alone missed them when the menu was only scrolled) */
    extern int lk_sh_hide; static int n;
    if (lk_sh_hide && (++n & 31) == 0) { int miss = 0, k; for (k = 0; k < 16; k++) if (!lk_quick_icon_have(lk_eq_ids[k])) miss = 1; if (miss) lk_eq_capture_missing(); }
    lk_o_wuv_eq();
}
static void lk_h_cur_eq(void) {   /* InventoryMenu_UpdateCursorAt $00D714: the Start menu is open and bright: take the icons of the owned equipment from VRAM once (the overlay of Quick Equip shows them) */
    lk_eq_capture_missing();
    lk_o_cur_eq();
}
static void lk_h_pab_eq(void) {
    int c = lk_eq_take(), ok = bus_read16(0xFF12DEu) == 0 && bus_read16(0xFF543Eu) != 0, guard = 0;
    if (ok) lk_eq_stamp_now();
    if (lk_eq_is_held()) lk_eq_scan();
    for (;;) {
        if (c == -2) lk_snd(0x00DBBEu);
        else if (c >= 0) { if (ok) lk_eq_apply(c); else lk_snd(0x00DBBEu); }
        /* the game stands still while Quick Equip is held (a small menu: nobody gets hit while choosing); the VBlank handler goes on reading the pad, so the requests keep coming */
        if (!ok || !lk_eq_is_held() || ++guard > 36000) break;
        lk_call(0x000B5Eu);   /* WaitUntilVBlank */
        lk_eq_stamp_now();
        c = lk_eq_take();
    }
    lk_osd_equip_disarm();
    lk_o_pab_eq();
}
static void lk_eq_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_pab_eq = func_table_lookup(0x0066AC);
    lk_o_wuv_eq = func_table_lookup(0x000B5E); if (lk_o_wuv_eq) func_table_register(0x000B5E, lk_h_wuv_eq);
    lk_o_cur_eq = func_table_lookup(0x00D714); if (lk_o_cur_eq) func_table_register(0x00D714, lk_h_cur_eq);
    if (lk_o_pab_eq) func_table_register(0x0066AC, lk_h_pab_eq); else fprintf(stderr, "equip: ProcessActionButton not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_qs_install();   /* LK_QUICKSAVE v1 */\n"
    assert s.count(h) == 1, "func_table.c: run patch_quicksave.py first"
    s = s.replace(h, h + "        lk_eq_install();   /* LK_EQUIP v1 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
