#!/usr/bin/env python3
"""Alternate D-pad layout (2026-11-18, GitHub #22 paul-met, user: 'optional, in the options menu, default off'; same idea as the community
hack romhacking.net 5495).  The game walks along four world axes only; HandleDirectionalInput $0018C4 -> HandleDirectionalControl $001936
gives each d-pad DIAGONAL one axis (UP+RIGHT = NE, DOWN+RIGHT = SE, DOWN+LEFT = SW, UP+LEFT = NW) and lets a PLAIN direction pick one of two
axes by Nigel's facing.  On a modern pad the diagonals are awkward, so the alternate layout gives the plain directions the diagonal axes:
    Up = NE (screen up-right), Down = SW (down-left), Left = NW (up-left), Right = SE (down-right).
Diagonal presses keep the game's own meaning (UP+RIGHT is NE = the same as Up, DOWN+RIGHT is SE = the same as Right ...), so rolling the
thumb over a diagonal never walks somewhere unexpected.

How: a wrapper of HandleDirectionalInput $0018C4 replaces the d-pad nibble of g_Controller1State $FF0F8E (bit 0 up, 1 down, 2 left, 3 right)
for the duration of the call only and restores it afterwards (menus, Quick Equip, the dungeon map never see it), like LK_CAMCTL v1
(tools/patch_room3d.py).  Confusion (status bit -> the second half of the table) still works on the replaced nibble.  Inactive while
$FF12DE (cutscene controller playback) is non-zero.

Option: Options > Movement > D-Pad Original / Alternate (id 64; ~/.landstalker_altpad, env LANDSTALKER_ALTPAD=0|1 wins; default Original).
Original = the wrapper passes the call through untouched = bit exact.
Needs patch_options.py, patch_bath.py (id 63 + install anchor) and patch_langpage.py (row counts).  Idempotent.
usage: patch_altpad.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_ALTPAD v1"


def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed: " + old[:90]
    return s.replace(old, new, 1)


# ---- func_table.c: option storage, the wrapper, the menu row -------------------------------------------------------
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
else:
    assert "LK_BATH v1" in s and "LK_LGPAGE v1" in s, "func_table.c: run patch_bath.py and patch_langpage.py first"
    module = r'''/* ---- ''' + VER + r''': alternate d-pad layout, Up / Down / Left / Right = the diagonal axes (tools/patch_altpad.py, GitHub #22) ---- */
#include <stdio.h>
#include <stdlib.h>
static int lk_altpad_o = -1;
int lk_altpad_get(void) {   /* Options > Movement > D-Pad (id 64): ~/.landstalker_altpad, env LANDSTALKER_ALTPAD wins; default 0 = Original */
    if (lk_altpad_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_ALTPAD"); char pth[512]; FILE *f; int v = 0;
        snprintf(pth, sizeof pth, "%s/.landstalker_altpad", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); }
        if (e && *e) v = atoi(e); lk_altpad_o = v ? 1 : 0; }
    return lk_altpad_o; }
void lk_altpad_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_altpad_get(); lk_altpad_o = v ? 1 : 0;
    snprintf(pth, sizeof pth, "%s/.landstalker_altpad", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%d\n", lk_altpad_o); fclose(f); } }
void lk_altpad_step(void) { lk_altpad_set(!lk_altpad_get()); }
static gen_func_t lk_altpad_o_hdi;
static void lk_altpad_h_hdi(void) {   /* HandleDirectionalInput $0018C4: plain direction -> the diagonal nibble of its axis, for this call only */
    static const uint8_t map[16] = { 0x0, 0x9, 0x6, 0x3, 0x5, 0x5, 0x6, 0x7, 0xA, 0x9, 0xA, 0xB, 0xC, 0xD, 0xE, 0xF };   /* 1 up -> 9 NE, 2 down -> 6 SW, 4 left -> 5 NW, 8 right -> A SE; diagonals + opposite pairs unchanged */
    uint8_t c = bus_read8(0xFF0F8Eu), n;
    if (!lk_altpad_get() || bus_read16(0xFF12DEu) != 0 || (n = map[c & 0x0F]) == (c & 0x0F)) { lk_altpad_o_hdi(); return; }
    bus_write8(0xFF0F8Eu, (uint8_t)((c & 0xF0) | n)); lk_altpad_o_hdi(); bus_write8(0xFF0F8Eu, c);
}
static void lk_altpad_install(void) {   /* once per run (a second wrap would call itself) */
    static int done; if (done) return; done = 1;
    lk_altpad_o_hdi = func_table_lookup(0x0018C4u);
    if (lk_altpad_o_hdi) func_table_register(0x0018C4u, lk_altpad_h_hdi); else fprintf(stderr, "altpad: HandleDirectionalInput not found\n");
}
'''
    a = "void func_table_init(void) {"
    s = rep(s, a, module + a, "func_table.c init")
    h = "        lk_bath_install();   /* LK_BATH v1 */\n"
    s = rep(s, h, h + "        lk_altpad_install();   /* " + VER + " */\n", "func_table.c install hook")
    # options menu (tools/patch_options.py module lives in func_table.c): label, value words, help, Movement page row
    s = rep(s, "static const char *lk_id_name[64] = {", "static const char *lk_id_name[65] = {", "func_table.c lk_id_name size")
    s = rep(s, '"Items", "Bath Scene" };', '"Items", "Bath Scene", "D-Pad" };   /* 64: ' + VER + ' */', "func_table.c lk_id_name")
    s = rep(s, '    if (id == 62) return v ? "Japanese" : "Original";',
            '    if (id == 64) return v ? "Alternate" : "Original";   /* ' + VER + ' */\n    if (id == 62) return v ? "Japanese" : "Original";', "func_table.c value words")
    s = rep(s, 'case 63: return "Kayla\'s bath before the banquet";',
            'case 63: return "Kayla\'s bath before the banquet"; case 64: return "Up/Down/Left/Right go diagonally";', "func_table.c help")
    s = rep(s, "static const int lk_ids_move[5] = { 42, 44, 40, 11, 38 };",
            "static const int lk_ids_move[6] = { 42, 44, 40, 11, 38, 64 };   /* " + VER + ": + D-Pad */", "func_table.c lk_ids_move")
    s = rep(s, "= { 9, 7, 12, 3, 5, 8, 3, 20, 4 };", "= { 9, 7, 12, 3, 6, 8, 3, 20, 4 };   /* " + VER + ": Movement + D-Pad */", "func_table.c lk_pg_cnt")
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)

# ---- platform_sdl.c: option id 64 in platform_option_get / platform_option_step --------------------------------------
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched: " + VER)
else:
    s = rep(s, "extern int lk_bath_get(void); extern void lk_bath_step(void);",
            "extern int lk_bath_get(void); extern void lk_bath_step(void); extern int lk_altpad_get(void); extern void lk_altpad_step(void);   /* " + VER + " */",
            "platform_sdl.c extern")
    s = rep(s, "case 63: return lk_bath_get();", "case 63: return lk_bath_get(); case 64: return lk_altpad_get();", "platform_sdl.c get")
    s = rep(s, "case 63: lk_bath_step(); break;", "case 63: lk_bath_step(); break; case 64: lk_altpad_step(); break;", "platform_sdl.c step")
    open(p, "w").write(s)
    print("platform_sdl.c patched: " + VER)
