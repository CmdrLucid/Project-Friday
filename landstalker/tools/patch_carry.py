#!/usr/bin/env python3
"""Optional fix 'Fix Ride Objects' (2026-10-16, user recording rec_20261016_1946, room 444; Options > Gameplay > Fix Ride Objects Off / On, default Off).
Original behaviour: a carried object (vase) put down on a moving platform rides along (UpdateLinkedEntity $019114 copies the platform's move flags to it for one step and then
RESTORES its own +9), but Nigel standing on the vase is NOT carried: HandlePlayerLinkedEntity ($0017EE) reads the move flags (+9 direction, +2D step bits) of the entity Nigel is linked
to ($FF5430), and the vase has none of its own (+9 = 0, +2D = 0 for the whole ride, measured), so Nigel stays where he is and slides off.
Fix (On): wrapper of $0017EE: when the entity Nigel stands on is itself supported by another entity (its +30 = offset of a slot $80..$780) and has no move flags of its own,
$FF5430 is pointed at that supporting entity for the duration of the call (and restored), so Nigel gets the platform's push.  Chains of one step only.  Off = the original game.
Not handled: vertical platforms with an object on them (SyncPlayerHeightWithLinkedEntity $001858 is not wrapped; not seen in room 444).
Saved in ~/.landstalker_carry, env LANDSTALKER_CARRY=0|1 wins (tests).  Needs patch_difficulty.py before it (insert order).  Idempotent.
usage: patch_carry.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_CARRY v1"

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_CARRY v1: Nigel rides on objects that stand on moving platforms (tools/patch_carry.py) ---- */
static int lk_carry_v = -1;   /* Options > Gameplay > Fix Ride Objects Off / On, default Off; file ~/.landstalker_carry, env LANDSTALKER_CARRY=0|1 wins */
int lk_carry_get(void) {
    if (lk_carry_v < 0) { char p[512]; FILE *f; const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_CARRY"); int v = 1; snprintf(p, sizeof p, "%s/.landstalker_carry", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 1; fclose(f); } if (e) v = atoi(e); lk_carry_v = v ? 1 : 0; }
    return lk_carry_v;
}
void lk_carry_set(int v) { char p[512]; FILE *f; const char *h = getenv("HOME"); lk_carry_get(); lk_carry_v = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_carry", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_carry_v); fclose(f); } }
'''
    s = s.replace(a, module + a, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "lk_diff_install" in s, "func_table.c: run patch_difficulty.py first"
    module = r'''/* ---- LK_CARRY v1: Nigel rides on an object that stands on a moving platform (tools/patch_carry.py) ---- */
extern int lk_carry_get(void);
static gen_func_t lk_o_hple;
static void lk_h_hple(void) {   /* HandlePlayerLinkedEntity $0017EE */
    uint16_t n = bus_read16(0xFF5430u), m;
    if (lk_carry_get() && n < 0x800u && n >= 0x80u && !(n & 0x7Fu)) {
        uint32_t a = 0xFF5400u + n;
        m = bus_read16(a + 0x30u);
        if (m >= 0x80u && m < 0x800u && !(m & 0x7Fu) && m != n && !(bus_read8(a + 9u) & 0xFu)) {   /* the object under Nigel is itself carried by slot m and moves by that slot's flags only */
            bus_write16(0xFF5430u, m); lk_o_hple(); bus_write16(0xFF5430u, n); return;
        }
    }
    lk_o_hple();
}
static void lk_carry_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_hple = func_table_lookup(0x0017EE);
    if (lk_o_hple) func_table_register(0x0017EE, lk_h_hple); else fprintf(stderr, "carry: HandlePlayerLinkedEntity not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_diff_install();   /* LK_DIFF v2 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_carry_install();   /* LK_CARRY v1 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
