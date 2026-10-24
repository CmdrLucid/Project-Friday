#!/usr/bin/env python3
"""Optional 'Gaia Effect' (2026-10-19, user wish: the Statue of Gaia / Gaia Sword freeze the whole game for ~2 s; keep the effect but keep playing).
Original: HandleAttack ($015C1C) damages every enemy of the room first (no screen test), then GaiaEffect ($016712) runs an endless loop of its own (sub_016794:
shake VSRAM, move ~41 falling rock sprites in the sprite table, FlushDMACopyQueue, leave when all rocks are gone) -> GameLoop does not run: Nigel and the enemies stand still.
Option 'Live' (Options > Gameplay > Gaia Effect, default Off = original): the wrapper of GaiaEffect does the same set-up (Gaia sword graphics + palette for the rocks, rumble sound)
but returns at once; the rocks live in a C array and are moved / written into the sprite table by a wrapper of LoadSprites ($00401C) after every game pass
(into the first free slots >= 16, chained between slot 15 and the entity sprites exactly like the original); the VSRAM shake is left out on purpose (it made the picture stutter while walking).
The effect ends like the original (all rocks cleared after two cycles) or at once on a room change / Start menu / new use. Graphics + palette are restored at the end.
Saved in ~/.landstalker_gaia, env LANDSTALKER_GAIA=0|1 wins (tests).  Needs patch_carry.py before it (insert order).  Idempotent.
usage: patch_gaia.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_GAIA v1"

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_GAIA v1: Gaia effect without freezing the game (tools/patch_gaia.py) ---- */
static int lk_gaia_v = -1;   /* Options > Gameplay > Gaia Effect Original / Live, default Original; file ~/.landstalker_gaia, env LANDSTALKER_GAIA=0|1 wins */
int lk_gaia_get(void) {
    if (lk_gaia_v < 0) { char p[512]; FILE *f; const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_GAIA"); int v = 0; snprintf(p, sizeof p, "%s/.landstalker_gaia", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e) v = atoi(e); lk_gaia_v = v ? 1 : 0; }
    return lk_gaia_v;
}
void lk_gaia_set(int v) { char p[512]; FILE *f; const char *h = getenv("HOME"); lk_gaia_get(); lk_gaia_v = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_gaia", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_gaia_v); fclose(f); } }
'''
    s = s.replace(a, module + a, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "lk_carry_install" in s, "func_table.c: run patch_carry.py first"
    module = r'''/* ---- LK_GAIA v1: Gaia effect (falling rocks) runs beside the game instead of freezing it (tools/patch_gaia.py) ---- */
extern int lk_gaia_get(void);
extern long platform_frame_number(void);
#define LK_G_N 41                                  /* rock sprites (the original takes d7 = $28 -> 41 entries) */
static struct {
    int active, cycle, step, n_fit;
    int16_t y[LK_G_N]; uint16_t x[LK_G_N], tile[LK_G_N];
    uint16_t room; uint8_t sword;
    int16_t hs0, vs0;   /* plane A scroll at the use: the rocks stay where they were spawned in the WORLD (the screen scrolls under them) */
    uint32_t rng;
} lk_g;
static gen_func_t lk_o_gaia, lk_o_lspr, lk_o_cfmo, lk_o_hatk, lk_o_igs;
static uint32_t lk_g_rand(uint32_t range) { lk_g.rng = lk_g.rng * 1664525u + 1013904223u; return (lk_g.rng >> 8) % range; }   /* own RNG: the game's seed stays untouched */
static void lk_g_gfx(void) {   /* sword graphics + palette for the equipped sword (original GaiaEffect end sequence) */
    func_table_jsr(0x000464, 0x016782); func_table_jsr(0x00046A, 0x016788); func_table_jsr(0x000242, 0x01678E);
}
static void lk_g_end(int restore) {
    if (!lk_g.active) return;
    lk_g.active = 0;
    bus_write8(0xFF05CBu, 0x10); bus_write8(0xFF07C3u, 0x4F);   /* slot 15 -> 16, slot 78 -> 79 as the original leaves them */
    if (restore) { lk_g_gfx(); func_table_jsr(0x0002A8, 0x01678E); }
}
static void lk_h_gaia(void) {   /* GaiaEffect $016712 */
    int i, d1 = 0; uint16_t d0 = 0xC78C; M68kContext sv;
    if (!lk_gaia_get()) { lk_o_gaia(); return; }
    sv = g_m68k;
    if (!lk_g.active) {   /* first use: Gaia graphics for the rocks (the sword byte is put back at once: damage / animations must keep the real sword) */
        lk_g.sword = bus_read8(0xFF114Eu);
        bus_write8(0xFF114Eu, 0x04);
        lk_g_gfx();
        bus_write8(0xFF114Eu, lk_g.sword);
        lk_g.room = bus_read16(0xFF1204u);
    }
    lk_g.hs0 = (int16_t)bus_read16(0xFF0100u); lk_g.vs0 = (int16_t)bus_read16(0xFF0500u);
    lk_snd(0x016748);   /* TRAP #0, inline word SND_Rumble (the original call) */
    lk_g.rng = 0x2545F491u ^ (uint32_t)platform_frame_number();
    for (i = 0; i < LK_G_N; i++) {   /* sub_0167D6 */
        lk_g.y[i] = (int16_t)((int)lk_g_rand(0xE0) - 0x60);
        lk_g.tile[i] = d0;
        lk_g.x[i] = (uint16_t)(lk_g_rand(0x140) + 0x80);
        d0 = (uint16_t)(d0 + 0x10); d1++;
        if (d1 >= 3) { d1 = 0; d0 = (uint16_t)(d0 - 0x30); }
    }
    lk_g.y[LK_G_N - 1] = 1;   /* the last rock is the cycle timer */
    lk_g.cycle = 0; lk_g.step = 0; lk_g.active = 1;
    g_m68k = sv;
    func_table_rts();   /* the replaced function ends with RTS */
}
static void lk_g_step(void) {   /* once per game pass, after LoadSprites has rebuilt the sprite table */
    int i, k, d3 = -1, n, alive = 0, dh, dv; uint32_t a;
    if (bus_read16(0xFF1204u) != lk_g.room) { lk_g_end(1); return; }
    lk_g.step++;
    for (i = 0; i < LK_G_N; i++) {   /* sub_01685E */
        int d;
        if (!lk_g.tile[i] && !lk_g.x[i]) continue;
        d = lk_g.tile[i] == 0xC78C ? 7 : (lk_g.tile[i] == 0xC79C ? 5 : 3);
        lk_g.y[i] = (int16_t)(lk_g.y[i] + d);
        if (lk_g.y[i] < 0 || (uint16_t)lk_g.y[i] < 0x138) continue;
        if (lk_g.cycle == 2) { lk_g.y[i] = 0; lk_g.tile[i] = 0; lk_g.x[i] = 0; }
        else { lk_g.y[i] = 0x88; lk_g.x[i] = (uint16_t)(lk_g_rand(0x140) + 0x80); }
    }
    if ((uint16_t)lk_g.y[LK_G_N - 1] >= 0xF8) {
        lk_g.y[LK_G_N - 1] = 1; lk_g.cycle++;
        if (lk_g.cycle >= 2) { lk_g.y[LK_G_N - 1] = 0; lk_g.tile[LK_G_N - 1] = 0; lk_g.x[LK_G_N - 1] = 0; }
    }
    for (i = 0; i < LK_G_N; i++) if (lk_g.tile[i]) alive = 1;   /* sub_0168F4 */
    if (!alive) { lk_g_end(1); return; }
    for (k = 16; k < 80; k++) if (bus_read16(0xFF05D0u + 8u * (uint32_t)(k - 16)) == 0) { d3 = k; break; }   /* first free sprite slot (sub_016794 scan) */
    if (d3 < 0) return;
    n = 80 - d3; if (n > LK_G_N) n = LK_G_N;
    dh = (int16_t)((int16_t)bus_read16(0xFF0100u) - lk_g.hs0); dv = (int16_t)((int16_t)bus_read16(0xFF0500u) - lk_g.vs0);
    bus_write8(0xFF05CBu, (uint8_t)d3);   /* slot 15 -> rocks ... last rock -> slot 16 (entities) */
    for (i = 0; i < n; i++) {
        a = 0xFF05D0u + 8u * (uint32_t)(d3 + i - 16);
        int ty = (int)lk_g.y[i] - dv, tx = (int)lk_g.x[i] + dh;   /* screen position = the rock's own position in the world (the fall) moved by the scroll since the use */
        if (!lk_g.tile[i]) { ty = 0; tx = 1; }
        else if (ty < -200 || ty > 400 || tx <= 0 || tx >= 0x1FF) { ty = 0; tx = 1; }   /* out of the screen: parked above it (x = 0 would be the VDP's sprite mask) */
        bus_write16(a, (uint16_t)ty); bus_write8(a + 2, 0x0F); bus_write8(a + 3, (uint8_t)(i == n - 1 ? 0x10 : d3 + i + 1));
        bus_write16(a + 4, lk_g.tile[i]); bus_write16(a + 6, (uint16_t)tx);
    }
}
static void lk_h_igs(void) {   /* ItemUseGaiaStatue $00873A: no second statue while the rocks fall (the item is not used up: the usual 'cannot use' answer) */
    if (lk_gaia_get() && lk_g.active) { gen_func_t f = func_table_lookup(0x008BC0); if (f) { f(); return; } }
    lk_o_igs();
}
static void lk_h_hatk(void) {   /* HandleAttack $015C1C: the Gaia sword's charged hit (state $FF12E5 = 4, charge $0B) does not fire while the rocks fall: no damage, no new effect (a plain hit instead) */
    uint8_t st = bus_read8(0xFF12E5u);
    if (lk_gaia_get() && lk_g.active && st == 4 && bus_read8(0xFF113Fu) == 0x0B) {
        bus_write8(0xFF12E5u, 0xFF);
        lk_o_hatk();
        if (bus_read8(0xFF12E5u) == 0xFF) bus_write8(0xFF12E5u, st);
        return;
    }
    lk_o_hatk();
}
static void lk_h_lspr(void) {   /* LoadSprites $00401C */
    lk_o_lspr();
    if (lk_g.active) { M68kContext sv = g_m68k; lk_g_step(); g_m68k = sv; }
}
static void lk_g_hide(void) {   /* take the rocks out of the sprite table (the pass writes them again after LoadSprites) */
    int k; uint32_t a;
    for (k = 16; k < 80; k++) {
        a = 0xFF05D0u + 8u * (uint32_t)(k - 16);
        if (bus_read8(a + 2) == 0x0F && (bus_read16(a + 4) & 0xFFF0u) >= 0xC780u && (bus_read16(a + 4) & 0xFFF0u) <= 0xC7B0u) { bus_write16(a, 0); bus_write8(a + 2, 0); bus_write16(a + 4, 0); bus_write16(a + 6, 0); }
    }
    bus_write8(0xFF05CBu, 0x10);
}
static void lk_h_cfmo(void) {   /* CheckForMenuOpen $007624: START opens the Start menu, which loads its own graphics: end the effect cleanly first (the state the original game is in after the effect) */
    if (lk_g.active && (bus_read8(0xFF0F8Eu) & 0x80)) { M68kContext sv = g_m68k; lk_g_hide(); lk_g_end(1); g_m68k = sv; }
    lk_o_cfmo();
}
void lk_gaia_cancel(void) { lk_g_end(0); }
int lk_gaia_shake(void) {   /* the original GaiaEffectLoop $016794 shakes VSRAM directly (the own renderer then reads the VDP's scroll values, not the game's variables) */
    int i, d = func_table_depth();
    for (i = 0; i < d; i++) if (func_table_stack(i) == 0x016794u) return 1;
    return lk_g.active;
}
int lk_gaia_live(void) { return lk_g.active; }   /* the own renderer takes the Gaia sword palette while the rocks fall (the sword byte itself stays the real one) */
static void lk_gaia_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_gaia = func_table_lookup(0x016712); lk_o_lspr = func_table_lookup(0x00401C); lk_o_cfmo = func_table_lookup(0x007624); lk_o_hatk = func_table_lookup(0x015C1C); lk_o_igs = func_table_lookup(0x00873A);
    if (lk_o_gaia && lk_o_lspr && lk_o_cfmo && lk_o_hatk && lk_o_igs) { func_table_register(0x016712, lk_h_gaia); func_table_register(0x00401C, lk_h_lspr); func_table_register(0x007624, lk_h_cfmo); func_table_register(0x015C1C, lk_h_hatk); func_table_register(0x00873A, lk_h_igs); }
    else fprintf(stderr, "gaia: GaiaEffect / LoadSprites / menu entry not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_carry_install();   /* LK_CARRY v1 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_gaia_install();   /* LK_GAIA v1 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
