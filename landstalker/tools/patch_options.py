#!/usr/bin/env python3
"""Options tab in the Start menu (the item screen with the bar 'Use  Equip').  Built like the game's own menu, no overlay:
 * The bar is the game's two-choice prompt: LoadYesNoPrompt ($02482C) prints 'Use' / 'Equip' with PrintString_0 at text x $50 / $A0 (this patch prints Use / Equip / Options centred at $28 / $78 / $C8, arrow X $A8 / $F8 / $148),
   the cursor is hardware sprite 79 (SAT $FF07C8.., X $D0 / $120) moved by sub_02488A and its handlers
   (loop copies $02488A/$024898/$0248EE, RIGHT $024916, LEFT $024952, confirm $0248F6, cancel $02498E).
 * This patch overrides those entries (func_table_register after the generated init, originals are called for everything else):
     - LoadYesNoPrompt: after the original, print 'Options' at text x $E4 with the game's own text engine (ProcessChar $0230CA per character,
       character codes as in the CHR enum: space 0, digits 1-10, A-Z from $0B, a-z from $25; DMACopyTextboxTiles $02355A at the end);
     - RIGHT at 'Equip': third position (cursor X $164) and the options page; LEFT at 'Options': back to Equip (the game's own sub_39E redraws the list);
     - the page is the big box's tile map: 36 x 17 tiles at $FF1E04 (row stride $80 bytes), one 8x8 tile per character (tile = $A000 | code, exactly like the
       item names of sub_D5E4), uploaded with QueueInventoryWinTilemapDMA ($00792C) + EnableDMAQueueProcessing ($0002A2); A / C on the tab enter the list (like A on Use / Equip): the golden frame (the four corner pieces of tiles $A8..$B7, drawn as plane tiles around the whole row) marks the
       row, UP / DOWN pick a row, A / C / RIGHT = next value, LEFT = previous value, B goes back to the tab, B on the tab closes the menu as before.
 * Settings (Start menu: first the two entries Video / Audio, A opens the page, B goes back): Video = Widescreen (Off / 352 / 384 / 416), Full Height, Scaling (Fit / 4:3 / Integer / Fill), Filter (Off / Scanlines / CRT / CRT Pro / CRT Curved), De-Dither (Off / Light / Strong), Fullscreen;
   Audio = Music volume, Effects volume (0..100 %), Speech sound (On / Off); Gameplay = Shadow (Off / On: only things in the air, tools/patch_shadow.py), Quick Items (Off / On: pad Y / B use assigned items, tools/patch_quick.py). They call the same functions as the pad
   shortcuts (L2, R2, R1, L4) and are saved the same way; the on-screen hint of those shortcuts is suppressed while the menu is open.
File select (phase B): the bar 'Start Copy Delete' is the generic selector sub_F9D6 (d0 first arrow X $B0, d1 Y $134, d2 step, d3 count; hardware sprite 0) and
 the words are printed by sub_F958 with sub_235FE per character into the text buffer (ClearTextBuffer $00F5F4 / DMACopyTextBuffer $00F5DC). The override
 makes it four entries, centred in the bar with equal gaps (texts at x $12 / $51 / $87 / $CB, arrow X = text x + $88 from a table: the selector is a native copy of the original loop) and 'Options' (index 3) opens a one-line sub-menu in the bar's text line:
 UP / DOWN pick the setting, LEFT / RIGHT / A / C change it, B goes back; the originals are called through a temporary re-registration (they end in RTS).
Only active while CheckForMenuOpen ($007624) is on the call stack; LANDSTALKER_NOOPTIONS=1 switches the tab off.  usage: patch_options.py path/to/genrecomp   (idempotent)"""
import os, sys
root = sys.argv[1]

# ---- platform_sdl.c: option accessors ---------------------------------------------------------
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if "platform_option_get" not in s:
    b = "/* ---- coordinate debug overlay (tools/patch_coords.py) ---- */"
    assert s.count(b) == 1 and "platform_display_toggle_fullscreen" in s, "platform_sdl.c: run patch_fullscreen.py first"
    s = s.replace(b, r'''/* ---- options menu accessors (tools/patch_options.py) ---- */
extern int lk_shadow_get(void);
extern void lk_shadow_set(int m);
extern int lk_quick_get(void);
extern int lk_qsave_get(void);   /* quick save / load switch (tools/patch_quicksave.py) */
extern void lk_qsave_set(int v);
extern int lk_carry_get(void);   /* Ride Objects switch (tools/patch_carry.py) */
extern void lk_carry_set(int v);
extern int lk_ii_get(void);   /* Item Info switch (tools/patch_iteminfo.py) */
extern void lk_ii_set(int v);
extern int lk_bq_get(void);   /* Buy Quantity switch (tools/patch_buyqty.py) */
extern void lk_bq_set(int v);
extern void lk_quick_set(int v);
extern int lk_ffwd_get(void);   /* fast forward speed option (tools/patch_ffwd.py) */
extern void lk_ffwd_set(int v);
extern int lk_diff_get(int which);   /* difficulty: 0 = damage taken index, 1 = enemy HP index (tools/patch_difficulty.py) */
extern void lk_diff_set(int which, int v);
extern void lk_snd_get(int *music, int *sfx, int *talk);
extern void lk_snd_set(int music, int sfx, int talk);
int platform_option_get(int id) {   /* 0 widescreen step 0..3, 1 full height 0/1, 2 filter 0..4, 3 fullscreen 0/1, 4 scaling 0..3, 5 de-dither 0..2, 6 music volume %, 7 effects volume %, 8 speech sound 0/1, 9 shadow 0/1, 10 quick items 0/1, 11 fast forward 0..3 (Off, 2x, 3x, 4x), 12 damage taken 0..5 (25 / 50 / 75 / 100 / 150 / 200 %, RIGHT = more), 13 enemy HP 0..4 (50 / 100 / 150 / 200 / 300 %), 14 quick save 0/1 (default Off), 15 ride objects 0/1 (default Off), 16 item info 0/1 (default Off) */
    extern int lk_wide_e, lk_tall; int m, e, t;
    if (!lk_disp_loaded) lk_disp_load();
    if (!lk_dd_loaded) lk_dd_load();
    switch (id) { case 0: return lk_wide_e / 16; case 1: return lk_tall > 0; case 2: return lk_fx_mode; case 3: return lk_fsc_on; case 4: return lk_scale_mode; case 5: return lk_dd_mode;
                  case 6: lk_snd_get(&m, &e, &t); return m; case 7: lk_snd_get(&m, &e, &t); return e; case 8: lk_snd_get(&m, &e, &t); return t; case 9: return lk_shadow_get(); case 10: return lk_quick_get(); case 11: return lk_ffwd_get(); case 12: return lk_diff_get(0); case 13: return lk_diff_get(1); case 14: return lk_qsave_get(); case 15: return lk_carry_get(); case 16: return lk_ii_get(); case 17: return lk_bq_get(); }
    return 0;
}
void platform_option_step(int id) {
    int m, e, t;
    switch (id) { case 0: platform_display_cycle_wide(); break; case 1: platform_display_cycle_tall(); break; case 2: platform_display_cycle_filter(); break; case 3: platform_display_toggle_fullscreen(); break; case 4: platform_display_cycle_scale(); break;
                  case 5: platform_display_cycle_dither(); break;
                  case 6: lk_snd_get(&m, &e, &t); m += 10; if (m > 100) m = 0; lk_snd_set(m, e, t); break;
                  case 7: lk_snd_get(&m, &e, &t); e += 10; if (e > 100) e = 0; lk_snd_set(m, e, t); break;
                  case 8: lk_snd_get(&m, &e, &t); lk_snd_set(m, e, !t); break;
                  case 9: lk_shadow_set(!lk_shadow_get()); break;
                  case 10: lk_quick_set(!lk_quick_get()); break;
                  case 11: lk_ffwd_set((lk_ffwd_get() + 1) % 4); break;
                  case 12: lk_diff_set(0, (lk_diff_get(0) + 1) % 6); break; case 13: lk_diff_set(1, (lk_diff_get(1) + 1) % 5); break; case 14: lk_qsave_set(!lk_qsave_get()); break; case 15: lk_carry_set(!lk_carry_get()); break; case 16: lk_ii_set(!lk_ii_get()); break; case 17: lk_bq_set(!lk_bq_get()); break; }
    lk_osd_frames = 0;   /* the menu shows the value itself */
}
''' + b, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched: option accessors")

# ---- func_table.c: the menu module + hook --------------------------------------------------------
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if "lk_menu_install" in s:
    print("func_table.c already patched: options menu")
    sys.exit(0)
a = "static void lk_strip_extend(uint32_t a);\n"
assert s.count(a) == 1, "func_table.c: layout changed (lk_strip_extend forward declaration)"
module = r'''/* ---- LANDSTALKER options tab in the Start menu (tools/patch_options.py) ---- */
extern int platform_option_get(int id);
extern void platform_option_step(int id);
extern int lk_bind_capturing(void);   /* key bindings (tools/patch_keys.py, input.c): pages 'Buttons' / 'Extras', ids 100.. = actions, 111 = reset */
extern void lk_bind_capture(int i);
extern void lk_bind_reset(void);
extern void platform_request_quit(void);   /* Options > Quit Game (tools/patch_keys.py) */
extern void lk_bind_label(int i, char *o, size_t n);
extern const char *lk_bind_name(int i);
static gen_func_t lk_o_yn, lk_o_upd, lk_o_right, lk_o_left, lk_o_conf, lk_o_cancel;
static int lk_opt_tab, lk_opt_row, lk_opt_sel, lk_prev_state;   /* lk_opt_sel: inside the list (frame visible), like the game's item grid after A */
static int lk_dir_edge(int bit) { return (bus_read8(0xFF0F8Eu) & bit) && !(lk_prev_state & bit); }   /* new in this pass: the pad state before this pass's UpdateControllerInputs is lk_prev_state */
#define LK_OPT_ALL 11
static int lk_opt_pg;   /* 0 = root (Video / Audio / Gameplay), 1 = video page, 2 = audio page, 3 = gameplay page */
static int lk_opt_rootrow, lk_opt_scroll, lk_opt_quitarm;   /* scroll = first visible row of a long page (Keybindings), quitarm = 'Quit Game' waits for the second A */
static int lk_in_menu(void) { int i, d = func_table_depth(); for (i = 0; i < d; i++) if (func_table_stack(i) == 0x007624u) return 1; return 0; }
static int lk_chr(char c) {   /* the game's CHR enum (US) */
    if (c == ' ') return 0;
    if (c >= '0' && c <= '9') return 1 + (c - '0');
    if (c >= 'A' && c <= 'Z') return 0x0B + (c - 'A');
    if (c >= 'a' && c <= 'z') return 0x25 + (c - 'a');
    if (c == '.') return 0x40;
    if (c == ',') return 0x41;   /* guessed (2026-10-16, Item Info texts): the code after '.' */
    if (c == '-') return 0x48;
    if (c == ':') return 0x47;
    if (c == '<') return 0x45;
    if (c == '>') return 0x46;
    return 0;
}
static void lk_call(uint32_t a) { func_table_jsr(a, 0x0248B2u); }
static void lk_snd(uint32_t pc) { M68kContext sv = g_m68k; g_m68k.pc = pc; recomp_m68k_exception(32 + 0); g_m68k = sv; }   /* the game's own trap #0 sound sites: $00FA9E = cursor move, $00FA54 = cursor select */
#define LK_SND_MOVE 0x00FA9Eu
#define LK_SND_SELECT 0x00FA54u
/* print a string into the bottom text box with the game's own text engine (same steps as PrintString_0) */
static void lk_menu_print(const char *t, int x) {
    M68kContext sv = g_m68k;
    bus_write32(0xFF1844, 0); bus_write8(0xFF1155, 0); bus_write8(0xFF1144, 3); bus_write16(0xFF1194, (uint16_t)x);
    for (; *t; t++) { g_m68k.d[0] = (uint32_t)lk_chr(*t); lk_call(0x0230CAu); }   /* ProcessChar */
    lk_call(0x02355Au);   /* DMACopyTextboxTiles */
    g_m68k = sv;
}
static void lk_opt_put_tile(int col, int row, int tile) { bus_write16(0xFF1E04u + (uint32_t)row * 0x80u + (uint32_t)col * 2u, (uint16_t)(0xA000 | tile)); }
static void lk_opt_put(int col, int row, const char *t) { for (; *t; t++, col++) bus_write16(0xFF1E04u + (uint32_t)row * 0x80u + (uint32_t)col * 2u, (uint16_t)(0xA000 | lk_chr(*t))); }
static const char *lk_id_name[18] = { "Widescreen", "Full Height", "Filter", "Fullscreen", "Scaling", "De-Dither", "Music Volume", "Effects Volume", "Speech Sound", "Shadows", "Quick Items", "Fast Forward", "Damage Taken", "Enemy HP", "Quick Save", "Fix Ride Objects", "Item Info", "Buy Quantity" };   /* platform option id -> label */
static const int lk_ids_video[7] = { 0, 1, 4, 2, 5, 3, 9 };
static const int lk_ids_audio[3] = { 6, 7, 8 };
static const int lk_ids_game[6] = { 10, 17, 15, 16, 14, 11 };   /* Quality of Life */
static const int lk_ids_diff[2] = { 12, 13 };   /* Difficulty */
static const int lk_ids_key[12] = { 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111 };   /* Keybindings page: 11 actions + Reset Defaults (scrolls) */
static int lk_opt_capid = -1;
static const char *lk_opt_bindtext(int id) {   /* value column of a binding row: 'pad  key' or the capture prompt */
    static char b[24];
    if (id == 111) return ">";
    if (lk_bind_capturing() && lk_opt_capid == id) return "PRESS KEY";
    lk_bind_label(id - 100, b, sizeof b); return b;
}
static const int lk_ids_all[LK_OPT_ALL] = { 0, 1, 4, 2, 5, 3, 6, 7, 8, 9, 10 };   /* file select sub-menu: one flat list */
static const char *lk_opt_val(int id, int v) {
    static char buf[8];
    static const char *wide[4] = { "Off", "352 px", "384 px", "416 px" }, *onoff[2] = { "Off", "On" }, *filt[5] = { "Off", "Scanlines", "CRT", "CRT Pro", "CRT Curved" }, *scal[4] = { "Fit", "4:3", "Integer", "Fill" }, *dd[4] = { "Off", "Light", "Medium", "Strong" }, *shd[2] = { "Off", "On" }, *ffw[4] = { "Off", "2x", "3x", "4x" }, *dmg[6] = { "25", "50", "75", "100", "150", "200" }, *ehp[5] = { "50", "100", "150", "200", "300" };
    if (id == 0) return wide[v & 3];
    if (id == 4) return scal[v & 3];
    if (id == 2) return filt[v > 4 || v < 0 ? 0 : v];
    if (id == 5) return dd[v > 3 || v < 0 ? 0 : v];
    if (id == 9) return shd[v & 1];
    if (id == 11) return ffw[v & 3];
    if (id == 12) return dmg[v > 5 || v < 0 ? 0 : v];
    if (id == 13) return ehp[v > 4 || v < 0 ? 1 : v];
    if (id == 6 || id == 7) { snprintf(buf, sizeof buf, "%d", v); return buf; }
    return onoff[v & 1];
}
static int lk_opt_nrows(void) { return lk_opt_pg == 0 ? 6 : lk_opt_pg == 1 ? 7 : lk_opt_pg == 2 ? 3 : lk_opt_pg == 3 ? 6 : lk_opt_pg == 4 ? 2 : 12; }
static int lk_opt_vis(void) { int n = lk_opt_nrows(); return n > 7 ? 7 : n; }   /* rows shown at once */
static void lk_opt_fixscroll(void) { int v = lk_opt_vis(); if (lk_opt_row < lk_opt_scroll) lk_opt_scroll = lk_opt_row; if (lk_opt_row >= lk_opt_scroll + v) lk_opt_scroll = lk_opt_row - v + 1; }
static int lk_opt_rowid(int r) { return lk_opt_pg == 1 ? lk_ids_video[r] : lk_opt_pg == 2 ? lk_ids_audio[r] : lk_opt_pg == 3 ? lk_ids_game[r] : lk_opt_pg == 4 ? lk_ids_diff[r] : lk_opt_pg == 5 ? lk_ids_key[r] : -1 - r; }   /* root rows: -1 Video, -2 Audio, -3 Gameplay */
static int lk_opt_rowy(int r) { return (lk_opt_pg == 2 || lk_opt_pg == 4) ? 2 + 3 * r : 2 + 2 * r; }
static const char *lk_opt_rowname(int r) { int id = lk_opt_rowid(r); return id >= 100 ? (id == 111 ? "Reset Defaults" : lk_bind_name(id - 100)) : id >= 0 ? lk_id_name[id] : id == -1 ? "Video" : id == -2 ? "Audio" : id == -3 ? "Quality of Life" : id == -4 ? "Difficulty" : id == -5 ? "Keybindings" : "Quit Game"; }
static int lk_opt_cnt(int id) { static const int c[18] = { 4, 2, 5, 2, 4, 4, 11, 11, 2, 2, 2, 4, 6, 5, 2, 2, 2, 2 }; return c[id]; }
static void lk_opt_change(int id, int dir) {
    int n, k, steps;
    if (id >= 100) { if (dir > 0) { if (id == 111) lk_bind_reset(); else { lk_opt_capid = id; lk_bind_capture(id - 100); } } return; }   /* binding rows: A / RIGHT = wait for the next button / key press */
    n = lk_opt_cnt(id); steps = dir > 0 ? 1 : n - 1; for (k = 0; k < steps; k++) platform_option_step(id); }
/* the golden selection frame of the item lists (tiles $A8..$B7 = MenuCursor2BPP, a 4x4 tile frame that consists of four corner pieces only): a corner piece is
   3 tiles (A8 A9 / AC for the top left, B4 B5 / B0 top right, AA AB / AF bottom left, B6 B7 / B3 bottom right); here the four corners are placed around the whole row */
static void lk_opt_frame(int top, int left, int right, int on) {   /* on = 0: blank tiles at the corner positions (blink phase off); the video page (rows 2 apart) uses a compact 3-row frame without the second vertical tile of each corner */
    int bottom = top + 3;
    if (1) {   /* always the compact frame: its 24 px are centred on the one text line (the full 32 px frame sat 4 px too high on the line, measured 2026-10-16) */
#define LK_FT2(t) (on ? (t) : 0)
        bottom = top + 2;
        lk_opt_put_tile(left, top, LK_FT2(0xA8)); lk_opt_put_tile(left + 1, top, LK_FT2(0xAC)); lk_opt_put_tile(right, top, LK_FT2(0xB4)); lk_opt_put_tile(right - 1, top, LK_FT2(0xB0));
        lk_opt_put_tile(left, bottom, LK_FT2(0xAB)); lk_opt_put_tile(left + 1, bottom, LK_FT2(0xAF)); lk_opt_put_tile(right, bottom, LK_FT2(0xB7)); lk_opt_put_tile(right - 1, bottom, LK_FT2(0xB3));
#undef LK_FT2
        return;
    }
#define LK_FT(t) (on ? (t) : 0)
    lk_opt_put_tile(left, top, LK_FT(0xA8)); lk_opt_put_tile(left, top + 1, LK_FT(0xA9)); lk_opt_put_tile(left + 1, top, LK_FT(0xAC));
    lk_opt_put_tile(right, top, LK_FT(0xB4)); lk_opt_put_tile(right, top + 1, LK_FT(0xB5)); lk_opt_put_tile(right - 1, top, LK_FT(0xB0));
    lk_opt_put_tile(left, bottom - 1, LK_FT(0xAA)); lk_opt_put_tile(left, bottom, LK_FT(0xAB)); lk_opt_put_tile(left + 1, bottom, LK_FT(0xAF));
    lk_opt_put_tile(right, bottom - 1, LK_FT(0xB6)); lk_opt_put_tile(right, bottom, LK_FT(0xB7)); lk_opt_put_tile(right - 1, bottom, LK_FT(0xB3));
#undef LK_FT
}
/* the game's item cursor blinks 16 frames on / 16 frames off (measured: screenshots of the Use list after A); the bar loop runs once per frame */
static int lk_opt_blink;
static void lk_opt_upload(void) { lk_call(0x00792Cu); lk_call(0x0002A2u); }
/* scroll arrows of a long page, the same sprites as in the item list (InventoryMenu_UpdateArrowSprites $00D756): SAT RAM $FF0558 = up arrow (Y $98), $FF0560 = down arrow (Y $120, flipped), tile $80B8 (the game keeps
   the 16 x 16 arrow in VRAM tiles $B8..$BB while the menu is open), X $8E; shown for 32 frames, hidden for 32, restarted by every move so that they are visible right after it */
static uint16_t lk_arrow_ref; static int lk_arrow_on;
static void lk_opt_arrows(void) {
    int on = lk_opt_tab && lk_opt_sel && lk_opt_pg >= 3, up, dn, ph;
    if (!on && !lk_arrow_on) return;
    ph = (int)((uint16_t)(bus_read16(0xFF0F9Cu) - lk_arrow_ref) & 0x3F) < 0x20;
    up = on && lk_opt_scroll > 0 && ph; dn = on && lk_opt_scroll + lk_opt_vis() < lk_opt_nrows() && ph;
    bus_write16(0xFF0558u, up ? 0x98 : 0); bus_write8(0xFF055Au, 5); bus_write16(0xFF055Cu, 0x80B8); bus_write16(0xFF055Eu, 0x8E);
    bus_write16(0xFF0560u, dn ? 0x120 : 0); bus_write8(0xFF0562u, 5); bus_write16(0xFF0564u, 0x90B8); bus_write16(0xFF0566u, 0x8E);
    lk_arrow_on = on;
}
static void lk_opt_page(void) {   /* the whole page: labels, values, and the frame when inside the list; uploaded to the window plane */
    int r, c; M68kContext sv = g_m68k;
    for (r = 0; r < 17; r++) for (c = 0; c < 36; c++) bus_write16(0xFF1E04u + (uint32_t)r * 0x80u + (uint32_t)c * 2u, 0xA000);
    for (r = 0; r < lk_opt_vis(); r++) { int ar = r + lk_opt_scroll, id = lk_opt_rowid(ar); lk_opt_put(3, lk_opt_rowy(r), lk_opt_rowname(ar)); if (id >= 100) lk_opt_put(20, lk_opt_rowy(r), lk_opt_bindtext(id)); else if (id >= 0) lk_opt_put(22, lk_opt_rowy(r), lk_opt_val(id, platform_option_get(id))); else if (id == -6) lk_opt_put(22, lk_opt_rowy(r), lk_opt_quitarm ? "PRESS A" : ""); else lk_opt_put(22, lk_opt_rowy(r), ">"); }
    lk_opt_blink = 0;   /* every redraw (enter, row, value) starts with the frame visible */
    if (lk_opt_sel) lk_opt_frame(lk_opt_rowy(lk_opt_row - lk_opt_scroll) - 1, 1, 34, 1);
    lk_opt_upload(); g_m68k = sv;
}
static void lk_opt_enter(void) {   /* open the page of the selected root row; 'Quit Game' needs a second A */
    if (lk_opt_row == 5) { if (lk_opt_quitarm) platform_request_quit(); else lk_opt_quitarm = 1; lk_opt_page(); return; }
    lk_opt_rootrow = lk_opt_row; lk_opt_pg = 1 + lk_opt_row; lk_opt_row = 0; lk_opt_scroll = 0; lk_arrow_ref = bus_read16(0xFF0F9Cu); lk_opt_page();
}   /* open the Video / Audio page of the selected root row */
static void lk_bar_arrow(uint16_t x) { bus_write16(0xFF07CEu, x); bus_write8(0xFF07CAu, 5); bus_write16(0xFF07CCu, 0x8524); bus_write8(0xFF1800u, 0); }
#define LK_X_USE 0x00A8   /* arrow X = text x + $80; the three words are centred in the bar: text x $28 / $78 / $C8 (the game: $50 / $A0, arrow $D0 / $120) */
#define LK_X_EQ  0x00F8
#define LK_X_OPT 0x0148
static void lk_menu_print_nodma(const char *t, int x) {
    bus_write32(0xFF1844, 0); bus_write8(0xFF1155, 0); bus_write8(0xFF1144, 3); bus_write16(0xFF1194, (uint16_t)x);
    for (; *t; t++) { g_m68k.d[0] = (uint32_t)lk_chr(*t); lk_call(0x0230CAu); }   /* ProcessChar */
}
static int lk_ii_cur = -2;   /* item description shown in the bar (tools/patch_iteminfo.py): item id, -1 = plain bar, -2 = unknown / bar rebuilt */
static void lk_ii_leave(void);
static void lk_h_yn(void) {   /* replaces LoadYesNoPrompt in the Start menu: same steps, three centred words */
    int y;
    if (!lk_in_menu()) { lk_o_yn(); return; }
    { M68kContext sv = g_m68k;
      lk_call(0x024998u); lk_call(0x0234A8u);
      lk_menu_print_nodma("Use", 0x28); lk_menu_print_nodma("Equip", 0x78); lk_menu_print_nodma("Options", 0xC8);
      lk_call(0x02355Au);   /* DMACopyTextboxTiles */
      g_m68k = sv; }
    y = (int)(int8_t)bus_read8(0xFF1129) + 0x134;
    bus_write8(0xFF07CAu, 5); bus_write16(0xFF07CCu, 0x8524); bus_write16(0xFF07CEu, LK_X_USE); bus_write16(0xFF07C8u, (uint16_t)y); bus_write16(0xFF1800u, (uint16_t)y);
    g_m68k.d[1] = (g_m68k.d[1] & 0xFFFF0000u) | (uint32_t)(y & 0xFFFF);
    lk_opt_tab = 0; lk_opt_sel = 0; lk_opt_pg = 0; lk_ii_cur = -1;
    func_table_rts();   /* the replaced function ends with RTS */
}
static int lk_bar_loop(void) {   /* is the bar loop (sub_02488A and its generated copies) the caller? */
    uint32_t c = func_table_stack(1);
    return (c == 0x02488Au || c == 0x024898u || c == 0x0248EEu) && lk_in_menu();
}
/* UpdateControllerInputs ($00033E) is called once per pass of the bar loop; the thunk ends in a tail jump, so the real update runs AFTER this hook:
   at this point the pad RAM still holds the previous pass's state (lk_prev_state for the handlers of this pass). UP / DOWN rows and the blinking row cursor are done here. */
static void lk_h_upd(void) {
    int cur = bus_read8(0xFF0F8Eu);
    if (lk_bar_loop()) {
        static int cap_was;
        lk_ii_leave();
        int e = cur & ~lk_prev_state;
        lk_opt_arrows();
        if (lk_opt_tab && lk_opt_sel && lk_opt_pg == 5) { int cp = lk_bind_capturing(); if (cap_was && !cp) { M68kContext sv = g_m68k; lk_opt_page(); lk_snd(LK_SND_SELECT); g_m68k = sv; } cap_was = cp; }   /* capture finished: show the new binding */   /* edge of the previous pass (one pass late, imperceptible) */
        if (lk_opt_tab && lk_opt_sel) bus_write8(0xFF1800u, 0);   /* inside the list the bar arrow stays lit, like after A on Use / Equip */
        if (lk_opt_tab && lk_opt_sel && (e & 3)) {
            M68kContext sv = g_m68k;
            if (e & 1) lk_opt_row = (lk_opt_row + lk_opt_nrows() - 1) % lk_opt_nrows();
            if (e & 2) lk_opt_row = (lk_opt_row + 1) % lk_opt_nrows();
            lk_opt_fixscroll(); lk_opt_quitarm = 0; lk_arrow_ref = bus_read16(0xFF0F9Cu);
            lk_opt_page(); lk_snd(LK_SND_MOVE); g_m68k = sv;
        } else if (lk_opt_tab && lk_opt_sel && ((++lk_opt_blink) & 0x0F) == 0) {   /* blink: toggle the corners every 16 passes */
            M68kContext sv = g_m68k;
            lk_opt_frame(lk_opt_rowy(lk_opt_row - lk_opt_scroll) - 1, 1, 34, !(lk_opt_blink & 0x10)); lk_opt_upload();
            g_m68k = sv;
        }
    }
    lk_prev_state = cur;
    lk_o_upd();
}
static void lk_bump(void) { bus_write8(0xFF1800u, (uint8_t)(bus_read8(0xFF1800u) + 8)); func_table_tail(0x024898); }   /* same as the game's 'nothing to do' path (loc_0248EE) */
static void lk_goto_tab(uint16_t x, uint32_t draw) { M68kContext sv = g_m68k; lk_bar_arrow(x); if (draw) lk_call(draw); lk_snd(LK_SND_MOVE); g_m68k = sv; func_table_tail(0x024898); }   /* draw: $39E equip list, $398 item list */
static void lk_h_right(void) {
    if (lk_in_menu()) {
        uint16_t x = bus_read16(0xFF07CEu);
        if (!lk_dir_edge(8)) { lk_bump(); return; }   /* a held RIGHT must not slide through the tabs */
        if (lk_opt_sel) { M68kContext sv = g_m68k; if (lk_opt_pg == 0) lk_opt_enter(); else { lk_opt_change(lk_opt_rowid(lk_opt_row), 1); lk_opt_page(); } lk_snd(LK_SND_SELECT); g_m68k = sv; func_table_tail(0x024898); return; }   /* inside the list: next value (root: open the page) */
        if (x == LK_X_USE) { lk_opt_tab = 0; lk_opt_sel = 0; lk_goto_tab(LK_X_EQ, 0x39E); return; }
        if (x == LK_X_EQ) { M68kContext sv = g_m68k; lk_opt_tab = 1; lk_opt_sel = 0; lk_opt_row = 0; lk_opt_scroll = 0; lk_opt_quitarm = 0; lk_opt_pg = 0; lk_bar_arrow(LK_X_OPT); lk_opt_page(); lk_snd(LK_SND_MOVE); g_m68k = sv; func_table_tail(0x024898); return; }
        lk_bump(); return;
    }
    lk_o_right();
}
static void lk_h_left(void) {
    if (lk_in_menu()) {
        uint16_t x = bus_read16(0xFF07CEu);
        if (!lk_dir_edge(4)) { lk_bump(); return; }   /* a held LEFT must not slide through the tabs */
        if (lk_opt_sel) { M68kContext sv = g_m68k; if (lk_opt_pg == 0) { lk_snd(LK_SND_MOVE); g_m68k = sv; func_table_tail(0x024898); return; } lk_opt_change(lk_opt_rowid(lk_opt_row), -1); lk_opt_page(); lk_snd(LK_SND_SELECT); g_m68k = sv; func_table_tail(0x024898); return; }   /* inside the list: previous value (root: nothing) */
        if (x == LK_X_OPT) { lk_opt_tab = 0; lk_goto_tab(LK_X_EQ, 0x39E); return; }   /* sub_39E: the game redraws the Equip list */
        if (x == LK_X_EQ) { lk_goto_tab(LK_X_USE, 0x398); return; }                                     /* sub_398: the game redraws the item list */
        lk_bump(); return;
    }
    lk_o_left();
}
static void lk_keep_edge_mask(void) { g_m68k.d[2] = (g_m68k.d[2] & 0xFFFFFF00u) | (uint32_t)((bus_read8(0xFF0F8Eu) ^ 0x70) & 0xFF); }   /* a held button must not repeat */
static void lk_h_conf(void) {
    if (lk_opt_tab && lk_in_menu()) {
        M68kContext sv = g_m68k;
        if (!lk_opt_sel) { lk_opt_sel = 1; lk_opt_page(); lk_snd(0x0248F8u); }   /* A on the tab: into the list (the game's menu-open sound of the bar confirm) */
        else if (lk_opt_pg == 0) { lk_opt_enter(); lk_snd(0x0248F8u); }
        else { lk_opt_change(lk_opt_rowid(lk_opt_row), 1); lk_opt_page(); lk_snd(LK_SND_SELECT); }
        g_m68k = sv; lk_keep_edge_mask();
        func_table_tail(0x024898); return;
    }
    if (lk_in_menu()) {   /* the original tests the arrow X against its own $D0 (Use): give it its own value for the call and put ours back afterwards (it returns to us) */
        uint16_t x = bus_read16(0xFF07CEu);
        if (x == LK_X_USE) bus_write16(0xFF07CEu, 0x00D0); else if (x == LK_X_EQ) bus_write16(0xFF07CEu, 0x0120);
        lk_o_conf();
        bus_write16(0xFF07CEu, x);
        return;
    }
    lk_o_conf();
}
static void lk_h_cancel(void) {
    if (lk_opt_tab && lk_opt_sel && lk_in_menu()) {   /* B inside the list: back to the tab, like B in the item grid goes back to the bar */
        M68kContext sv = g_m68k;
        if (lk_opt_pg > 0) { lk_opt_pg = 0; lk_opt_row = lk_opt_rootrow; lk_opt_scroll = 0; lk_opt_quitarm = 0; } else lk_opt_sel = 0;   /* B on a page: back to Video / Audio, B on the root: back to the tab */
        lk_opt_page(); g_m68k = sv; lk_keep_edge_mask();
        func_table_tail(0x024898); return;
    }
    lk_opt_tab = 0; lk_opt_sel = 0; lk_opt_pg = 0; lk_opt_arrows();
    lk_o_cancel();
}
/* ---- file select: fourth bar entry 'Options' (phase B) ---- */
static gen_func_t lk_o_fsel, lk_o_fbar;
static int lk_in_fileselect(void) { int i, d = func_table_depth(); for (i = 0; i < d; i++) if (func_table_stack(i) == 0x00EE84u) return 1; return 0; }
static void lk_fs_print(const char *t, int x) { bus_write16(0xFF1194, (uint16_t)x); for (; *t; t++) { g_m68k.d[0] = (uint32_t)lk_chr(*t); lk_call(0x0235FEu); } }
/* words of the bar: measured widths (screen px) Start 39, Copy 30, Delete 44, Options 51; equal gaps of 24 px, equal margins: text x $12 / $51 / $87 / $CB; arrow X = text x + $88 */
#define LK_FS_TX0 0x12
#define LK_FS_TX1 0x51
#define LK_FS_TX2 0x87
#define LK_FS_TX3 0xCB
static const int lk_fs_ax[4] = { LK_FS_TX0 + 0x88, LK_FS_TX1 + 0x88, LK_FS_TX2 + 0x88, LK_FS_TX3 + 0x88 };
static void lk_fs_bar_text(void) {
    M68kContext sv = g_m68k;
    lk_call(0x00F5F4u);   /* ClearTextBuffer */
    lk_fs_print("Start", LK_FS_TX0); lk_fs_print("Copy", LK_FS_TX1); lk_fs_print("Delete", LK_FS_TX2); lk_fs_print("Options", LK_FS_TX3);
    lk_call(0x00F5DCu);   /* DMACopyTextBuffer */
    g_m68k = sv;
}
static void lk_h_fbar(void) {
    if (!lk_in_fileselect()) { lk_o_fbar(); return; }
    lk_fs_bar_text();
    func_table_rts();   /* the replaced sub_F958 ends with RTS */
}
/* options window of the file select (2026-10-15, user wish: a window like the pause menu instead of the one-line bar): the pages are the same as in the Start menu (root Video / Audio / Gameplay, then the rows),
   drawn by the renderer (vdp_render.c LK_WIN v1, tools/patch_overlay.py) over the picture. The row texts are rendered with the game's own text engine (ClearTextBuffer + PrintCharDirect into the buffer
   $FF3900: 36 columns x 2 tile rows, 4bpp, tile = column * 2 + half, index $A = background, $B = glyph) and the glyph pixels are copied to lk_win_row[]. Nothing is written to VRAM. */
extern int lk_win_on, lk_win_sel, lk_win_blink, lk_win_n, lk_win_pitch, lk_win_compact;
extern uint8_t lk_win_row[8][16][288];
extern uint8_t lk_win_cur[32][32];
extern uint8_t lk_win_arrow[16][16];   /* the scroll arrow (up) of the item list, 2bpp from the ROM: indices 0..3 */
extern int lk_win_arr;   /* bit 0 = draw the up arrow, bit 1 = the down arrow */
static uint8_t lk_win_stage[8][16][288];   /* a page is built here and copied in one go, so that no frame shows half of a page */
static void lk_win_text(int k, const char *l, int lx, const char *v, int vx) {
    int x, y; M68kContext sv = g_m68k;
    lk_call(0x00F5F4u);   /* ClearTextBuffer */
    if (l && *l) lk_fs_print(l, lx);
    if (v && *v) lk_fs_print(v, vx);
    for (y = 0; y < 16; y++) for (x = 0; x < 288; x++) {
        uint8_t b = bus_read8(0xFF3900u + (uint32_t)((x / 8) * 2 + y / 8) * 32u + (uint32_t)(y % 8) * 4u + (uint32_t)((x % 8) / 2));
        lk_win_stage[k][y][x] = (uint8_t)((((x & 1) ? (b & 15) : (b >> 4)) != 0xA) ? 1 : 0);
    }
    g_m68k = sv;
}
static const int lk_win_cnt[6] = { 6, 7, 3, 6, 2, 12 };
static int lk_win_scroll;   /* first visible option of a long page */
static int lk_win_vis(int pg) { return lk_win_cnt[pg] > 7 ? 7 : lk_win_cnt[pg]; }   /* the window has room for the title and 7 tight rows (pitch 18) */
static int lk_win_fix(int pg, int row) { int old = lk_win_scroll, v = lk_win_vis(pg); if (row < lk_win_scroll) lk_win_scroll = row; if (row >= lk_win_scroll + v) lk_win_scroll = row - v + 1; return old != lk_win_scroll; }   /* 1 = the visible part changed (the page is rebuilt) */
static int lk_win_id(int pg, int r) { return pg == 1 ? lk_ids_video[r] : pg == 2 ? lk_ids_audio[r] : pg == 3 ? lk_ids_game[r] : pg == 4 ? lk_ids_diff[r] : lk_ids_key[r]; }
static void lk_win_rowtext(int pg, int r) {   /* builds the text of row r (0 = title, 1.. = options) of page pg into lk_win_stage[r] */
    static const char *title[6] = { "Options", "Video", "Audio", "Quality of Life", "Difficulty", "Keybindings" }, *root[6] = { "Video", "Audio", "Quality of Life", "Difficulty", "Keybindings", "Quit Game" };
    if (r == 0) { lk_win_text(0, title[pg], pg == 3 ? 108 : pg ? 125 : 120, NULL, 0); return; }
    if (pg == 0) lk_win_text(r, root[r - 1], 0, r == 6 ? (lk_opt_quitarm ? "PRESS A" : "") : ">", r == 6 ? 200 : 250);
    else { int id = lk_win_id(pg, r - 1 + lk_win_scroll); char buf[40]; if (id >= 100) lk_win_text(r, id == 111 ? "Reset Defaults" : lk_bind_name(id - 100), 0, lk_opt_bindtext(id), 150); else { snprintf(buf, sizeof buf, "< %s >", lk_opt_val(id, platform_option_get(id))); lk_win_text(r, lk_id_name[id], 0, buf, 160); } }
}
static void lk_win_page(int pg, int sel) {   /* pg 0 = root, 1 Video, 2 Audio, 3 Gameplay; sel = selected row (0 based) */
    int r;
    for (r = 0; r <= lk_win_vis(pg); r++) lk_win_rowtext(pg, r);
    lk_win_pitch = (pg == 2 || pg == 4) ? 28 : (pg == 1 || pg == 5) ? 18 : 20; lk_win_compact = 1;   /* only the 3-row Audio page is spread out; the root (5 rows) and the long pages are tight with the compact frame */   /* Video: 6 rows close together + compact frame (as in the Start menu), the others spread out */
    memcpy(lk_win_row, lk_win_stage, sizeof lk_win_row); lk_win_n = lk_win_vis(pg) + 1; lk_win_sel = sel - lk_win_scroll + 1;
}
/* UP / DOWN only move the selection frame (no text work: every text row is printed through the game's own text engine, a whole page = about 100 characters = several frames of emulated time,
   that made the window sluggish); a value change redraws only its own row */
static void lk_win_move(int row) { lk_win_sel = row - lk_win_scroll + 1; }
static void lk_win_value(int pg, int row) { int k = row - lk_win_scroll + 1; lk_win_rowtext(pg, k); memcpy(lk_win_row[k], lk_win_stage[k], sizeof lk_win_row[0]); }
static void lk_fs_modal(void) {   /* options window in the file select */
    int pg = 0, row = 0, rootrow = 0, prev = bus_read8(0xFF0F8Eu), cur, e, blink = 0, cap_was = 0, arrow0 = 0;
    M68kContext sv = g_m68k;
    { int t, r, c; for (t = 0; t < 16; t++) for (r = 0; r < 8; r++) {   /* MenuCursor2BPP $00DF76: 16 tiles of 2bpp (8 rows of 2 bytes), column-major 4 x 4 */
        uint16_t w = bus_read16(0x00DF76u + (uint32_t)t * 16u + (uint32_t)r * 2u);
        for (c = 0; c < 8; c++) lk_win_cur[(t % 4) * 8 + r][(t / 4) * 8 + c] = (uint8_t)((w >> (14 - 2 * c)) & 3); } }
    { int t, r, c; for (t = 0; t < 4; t++) for (r = 0; r < 8; r++) {   /* ArrowGraphic2BPP $00E076: 4 tiles of 2bpp, column-major 2 x 2 */
        uint16_t w = bus_read16(0x00E076u + (uint32_t)t * 16u + (uint32_t)r * 2u);
        for (c = 0; c < 8; c++) lk_win_arrow[(t % 2) * 8 + r][(t / 2) * 8 + c] = (uint8_t)((w >> (14 - 2 * c)) & 3); } }
    lk_win_scroll = 0; lk_opt_quitarm = 0; lk_win_page(0, 0); lk_win_on = 1; lk_win_blink = 0;
    for (;;) {
        bus_write16(0xFF0550u, 0x0134); bus_write8(0xFF0552u, 5); bus_write16(0xFF0554u, 0xA0AA); bus_write16(0xFF0556u, 1);   /* the bar arrow is parked (hidden) while the window is open */
        lk_win_blink = (blink++ & 0x10) ? 1 : 0;
        lk_win_arr = (pg >= 3 && ((blink - arrow0) & 0x3F) < 0x20) ? ((lk_win_scroll > 0 ? 1 : 0) | (lk_win_scroll + lk_win_vis(pg) < lk_win_cnt[pg] ? 2 : 0)) : 0;
        lk_call(0x000272u);   /* WaitUntilVBlank */
        lk_call(0x00033Eu);   /* UpdateControllerInputs (the file select polls the pad itself, sub_F2E2) */
        cur = bus_read8(0xFF0F8Eu); e = cur & ~prev; prev = cur;
        { int cp = lk_bind_capturing(); if (cap_was && !cp) { blink = 0; lk_win_value(pg, row); lk_snd(0x00FA54u); } cap_was = cp; }   /* capture finished: show the new binding */
        if (e & 0x10) {   /* B: page -> root, root -> close */
            if (pg == 0) break;
            pg = 0; row = rootrow; lk_win_scroll = 0; lk_opt_quitarm = 0; blink = 0; lk_win_page(0, row); lk_snd(0x00FA9Eu); continue;
        }
        if (e & 3) {
            if (pg == 0 && lk_opt_quitarm) { lk_opt_quitarm = 0; lk_win_value(0, 5); }   /* moving away disarms 'Quit Game' */
            if (e & 1) row = (row + lk_win_cnt[pg] - 1) % lk_win_cnt[pg]; else row = (row + 1) % lk_win_cnt[pg];
            blink = 0; arrow0 = 0; if (lk_win_fix(pg, row)) lk_win_page(pg, row); else lk_win_move(row);
            lk_snd(0x00FA9Eu);
        }
        if (e & (0x20 | 0x40 | 8)) {   /* A / C / RIGHT: open the page / next value */
            if (pg == 0 && row == 5) { if (lk_opt_quitarm) platform_request_quit(); else { lk_opt_quitarm = 1; lk_win_value(0, 5); } blink = 0; lk_snd(0x00FA54u); }   /* Quit Game: second A */
            else if (pg == 0) { rootrow = row; pg = 1 + row; row = 0; lk_win_scroll = 0; blink = 0; lk_win_page(pg, 0); lk_snd(0x00FA54u); }
            else { lk_opt_change(lk_win_id(pg, row), 1); blink = 0; lk_win_value(pg, row); lk_snd(0x00FA54u); }
        }
        if ((e & 4) && pg) { lk_opt_change(lk_win_id(pg, row), -1); blink = 0; lk_win_value(pg, row); lk_snd(0x00FA54u); }   /* LEFT: previous value */
    }
    lk_win_on = 0; lk_win_arr = 0;
    lk_fs_bar_text();
    g_m68k = sv;
}
/* native selector for the mode bar: replaces sub_F9D6 when it is called with the bar's parameters. Same sequence as the original (sub_90E, WaitUntilVBlank, sub_F306, then the loop
   sub_FA24: sub_F2E2 pad poll with one press per release, LEFT / RIGHT / confirm / B, sub_FABC blink, sub_F8B6, WaitUntilVBlank) but with an arrow position table so that
   the four words can have equal gaps; index 3 ('Options') opens the sub-menu and stays on that entry afterwards. */
static void lk_fs_arrow(int idx, int blink) {
    bus_write16(0xFF0550u, 0x0134); bus_write8(0xFF0552u, 5); bus_write16(0xFF0554u, 0xA0AA);
    bus_write16(0xFF0556u, (blink & 0x10) ? 1 : (uint16_t)lk_fs_ax[idx]);
}
static void lk_h_fsel(void) {
    int idx = 0, blink = 0, c, res = -1;
    if (!(lk_in_fileselect() && (g_m68k.d[0] & 0xFFFF) == 0x00B0 && (g_m68k.d[1] & 0xFFFF) == 0x0134 && (g_m68k.d[2] & 0xFFFF) == 0x0050 && (g_m68k.d[3] & 0xFFFF) == 3)) { lk_o_fsel(); return; }
    lk_fs_arrow(0, 0);
    lk_call(0x00090Eu); lk_call(0x000B5Eu); lk_call(0x00F306u);
    for (;;) {
        lk_call(0x00F2E2u);   /* sub_F2E2: UpdateControllerInputs + one press per release */
        c = bus_read8(0xFF0F8Eu);
        if (c >= 0x10) {   /* B / C / A / START */
            lk_fs_arrow(idx, 0);
            if (c & 0x10) { res = -1; break; }   /* B: cancel, no sound (as the game) */
            lk_snd(LK_SND_SELECT);
            if (idx == 3) {   /* Options: sub-menu, then back to the bar on the same entry */
                int k;
                lk_fs_modal();
                for (k = 0; k < 40; k++) { lk_call(0x000272u); lk_call(0x00033Eu); if (!(bus_read8(0xFF0F8Eu) & 0xF0)) break; }   /* wait until B / A / C are released */
                lk_call(0x00F2E2u); blink = 0;
                continue;
            }
            res = idx; break;
        }
        if (c & 4) { if (idx > 0) { idx--; blink = 0; lk_snd(LK_SND_MOVE); } }
        else if (c & 8) { if (idx < 3) { idx++; blink = 0; lk_snd(LK_SND_MOVE); } }
        blink++; lk_fs_arrow(idx, blink);
        lk_call(0x00F8B6u); lk_call(0x000B5Eu);
    }
    g_m68k.d[0] = (g_m68k.d[0] & 0xFFFF0000u) | (uint32_t)(res & 0xFFFF);
    func_table_rts();   /* the replaced function ends with RTS */
}
static void lk_menu_install(void) {
    static int done;
    if (done) return;
    done = 1;
    if (getenv("LANDSTALKER_NOOPTIONS")) return;   /* A/B tests and a safety valve: the menu is then exactly the game's */
    lk_o_yn = func_table_lookup(0x02482C); lk_o_upd = func_table_lookup(0x00033E); lk_o_right = func_table_lookup(0x024916);
    lk_o_left = func_table_lookup(0x024952); lk_o_conf = func_table_lookup(0x0248F6); lk_o_cancel = func_table_lookup(0x02498E);
    if (!(lk_o_yn && lk_o_upd && lk_o_right && lk_o_left && lk_o_conf && lk_o_cancel)) { fprintf(stderr, "options menu: prompt functions not found, tab disabled\n"); return; }
    lk_o_fsel = func_table_lookup(0x00F9D6); lk_o_fbar = func_table_lookup(0x00F958);
    if (lk_o_fsel && lk_o_fbar) { func_table_register(0x00F9D6, lk_h_fsel); func_table_register(0x00F958, lk_h_fbar); } else fprintf(stderr, "options menu: file select functions not found\n");
    func_table_register(0x02482C, lk_h_yn); func_table_register(0x00033E, lk_h_upd); func_table_register(0x024916, lk_h_right);
    func_table_register(0x024952, lk_h_left); func_table_register(0x0248F6, lk_h_conf); func_table_register(0x02498E, lk_h_cancel);
}
'''
s = s.replace(a, module + a, 1)
h = "        lk_strip_extend(m68k_addr);   /* LANDSTALKER_WIDE_STRIPS */\n"
assert s.count(h) == 1, "func_table.c: strip hook layout changed"
s = s.replace(h, "        lk_menu_install();   /* LANDSTALKER options tab (registers the menu overrides once, after the generated init) */\n" + h, 1)
open(p, "w").write(s)
print("func_table.c patched: options tab in the Start menu")
