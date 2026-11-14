#!/usr/bin/env python3
"""Kayla's bath scene of the Japanese version (2026-11-15, user: 'Ich wuerde diese Szene gerne restaurieren').
Mercator castle, first visit: Japan lets Nigel into Kayla's bathroom (room 101, entity $6F kayla_in_bath, cutscene XS_005E) in the time
between the maid's banquet announcement and the banquet itself; the US / EU releases keep every byte of the scene (sprite, behaviour,
cutscene, texts $0627 / $0628 / $062D / $062E, all translated in lang/*.json) but DROPPED one 6-byte record of the OneTimeEventFlags
table ($01A974, read by CheckOneTimeEventFlags $01A3D8): `00 5E 92 60 12 06` = 'room 94 ($5E, castle 2F hallway): hide entity 0 (the
maid woman_3 standing ON the door cell (15,28) to Kayla's room 98) while story flag $12 bit 3 is set and $12 bit 6 is clear'.
(Compared with the Japanese ROM: entity tables, maps, visibility masks, behaviours and scripts of rooms 94 / 98 / 100 / 101 are identical,
only this record is missing; docs/DEBUGGING.md 'Kayla bath scene'.)  Entity 2 of room 94 is a second, identical maid shown only after the
banquet (flag $12.4), so the restored scene stays a pre-banquet window exactly like in Japan.

Option: Options > Language / Region > Bath Scene Off / On (id 63; ~/.landstalker_bath, env LANDSTALKER_BATH=0|1 wins; default Off).
Off = the game's own table only = bit exact.  On = a wrapper of CheckOneTimeEventFlags runs the game's table first and then applies the
Japanese record in C (same effect as the table entry: HideSpriteAtD0 $01A30A with d0 = 0, a5 = EntitySlot_1 $FF5480).
Needs patch_options.py (platform_sdl.c option switch) and patch_friday.py (install hook anchor).  Idempotent.  usage: patch_bath.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_BATH v1"

def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed: " + old[:90]
    return s.replace(old, new, 1)

# ---- func_table.c: option storage + the wrapper -------------------------------------------------------------------
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
else:
    assert "LK_FRIDAY v3" in s, "func_table.c: run patch_friday.py first"
    module = r'''/* ---- ''' + VER + r''': Kayla's bath scene of the Japanese version (tools/patch_bath.py) ---- */
#include <stdio.h>
#include <stdlib.h>
static int lk_bath_o = -1;
int lk_bath_get(void) {   /* Options > Language / Region > Bath Scene (id 63): ~/.landstalker_bath, env LANDSTALKER_BATH wins; default Off */
    if (lk_bath_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_BATH"); char pth[512]; FILE *f; int v = 0;
        snprintf(pth, sizeof pth, "%s/.landstalker_bath", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); }
        if (e && *e) v = atoi(e); lk_bath_o = v ? 1 : 0; }
    return lk_bath_o; }
void lk_bath_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_bath_get(); lk_bath_o = v ? 1 : 0;
    snprintf(pth, sizeof pth, "%s/.landstalker_bath", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%d\n", lk_bath_o); fclose(f); } }
void lk_bath_step(void) { lk_bath_set(!lk_bath_get()); }
static gen_func_t lk_bath_o_chk;
static void lk_bath_h_chk(void) {   /* CheckOneTimeEventFlags $01A3D8: the game's table first, then the record Japan has and the West dropped */
    uint8_t f;
    lk_bath_o_chk();
    if (!lk_bath_get() || bus_read16(0xFF1204u) != 0x005Eu) return;   /* g_RmNum1 = room 94, castle 2F hallway */
    f = bus_read8(0xFF1012u);   /* story flag byte $12 (g_Flags $FF1000) */
    if (!(f & 0x08) || (f & 0x40)) return;   /* `00 5E 92 60 12 06`: $12 bit 3 set (banquet announced) and $12 bit 6 clear (bath scene chain not done) */
    { uint32_t a0 = g_m68k.a[0], a1 = g_m68k.a[1];   /* like CheckOneTimeEventFlags_loc5 $01A426: movem.l a0-a1 around HideSpriteAtD0 */
      g_m68k.d[0] &= 0xFFFFFF00u;   /* d0.b = entity 0 = the maid on the door cell (15,28) */
      g_m68k.a[5] = 0xFF5480u;   /* EntitySlot_1 (Sprite1_X) */
      func_table_jsr(0x01A30Au, 0x01A440u);   /* HideSpriteAtD0 (restores a5 itself) */
      g_m68k.a[0] = a0; g_m68k.a[1] = a1; }
    fprintf(stderr, "bath: maid hidden in room 94 (flags $12 = %02X)\n", f);
}
static void lk_bath_install(void) {   /* once per run (a second wrap would call itself) */
    static int done; if (done) return; done = 1;
    lk_bath_o_chk = func_table_lookup(0x01A3D8u);
    if (lk_bath_o_chk) func_table_register(0x01A3D8u, lk_bath_h_chk); else fprintf(stderr, "bath: CheckOneTimeEventFlags not found\n");
}
'''
    a = "void func_table_init(void) {"
    s = rep(s, a, module + a, "func_table.c init")
    h = "        lk_fh_install();   /* LK_FRIDAY v3 */\n"
    s = rep(s, h, h + "        lk_bath_install();   /* " + VER + " */\n", "func_table.c install hook")
    # options menu (tools/patch_options.py module lives in func_table.c): label + help of id 63
    s = rep(s, "static const char *lk_id_name[63] = {", "static const char *lk_id_name[64] = {", "func_table.c lk_id_name size")
    s = rep(s, '"Names", "Items" };', '"Names", "Items", "Bath Scene" };   /* 63: ' + VER + ' */', "func_table.c lk_id_name")
    s = rep(s, 'case 62: return "Four items as in the Japanese original";',
            'case 62: return "Four items as in the Japanese original"; case 63: return "Kayla\'s bath before the banquet";', "func_table.c help")
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)

# ---- platform_sdl.c: option id 63 in platform_option_get / platform_option_step --------------------------------------
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched: " + VER)
else:
    s = rep(s, "extern int lk_items_get(void); extern void lk_items_step(void);",
            "extern int lk_items_get(void); extern void lk_items_step(void); extern int lk_bath_get(void); extern void lk_bath_step(void);   /* " + VER + " */",
            "platform_sdl.c extern")
    s = rep(s, "case 62: return lk_items_get();", "case 62: return lk_items_get(); case 63: return lk_bath_get();", "platform_sdl.c get")
    s = rep(s, "case 62: lk_items_step(); break;", "case 62: lk_items_step(); break; case 63: lk_bath_step(); break;", "platform_sdl.c step")
    open(p, "w").write(s)
    print("platform_sdl.c patched: " + VER)
