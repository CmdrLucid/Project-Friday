#!/usr/bin/env python3
"""Difficulty options (2026-10-15, user wish; Options > Gameplay): 'Damage Taken' (25 / 50 / 75 / 100 / 150 / 200 % of what ENEMIES do to Nigel; RIGHT = more damage) and 'Enemy HP' (50 / 100 / 150 / 200 / 300 %).
 * Damage Taken: wrapper of CalculateEnemyDamageOutput ($0165D0, called by ProcessPlayerDamage only: contact hits, projectiles, traps that use the contact damage); d0 = damage word * percent, at least 1 when the
   game's own value was > 0. Fall damage, poison / status damage and anything else that calls RemoveHealth ($017830) directly are NOT touched (user: no fall damage change).
 * Enemy HP: the game stores the HP of an entity in +$3E and the player's damage comes from CalculatePlayerDamageOutput ($01657E, 14 callers: sword and the other player attacks), so 'x % HP' = the damage Nigel deals
   divided by x % (at least 1): the same fight length as if every enemy and boss had x % of the HP, without touching the spawn code.
Both are saved in ~/.landstalker_difficulty (two PERCENT numbers: damage taken, enemy HP, e.g. '100 100'; an older file with index pairs is ignored), env LANDSTALKER_DIFF="d,h" (percent values) overrides (tests).  Needs patch_options / patch_quicksave before it.  Idempotent.
usage: patch_difficulty.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_DIFF v2"

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_DIFF v2: difficulty settings (tools/patch_difficulty.py) ---- */
static int lk_df[2] = { -1, 1 };   /* 0 damage taken index (25 50 75 100 150 200), 1 enemy HP index (50 100 150 200 300) */
static const int lk_df_dmg[6] = { 25, 50, 75, 100, 150, 200 }, lk_df_hp[5] = { 50, 100, 150, 200, 300 };
static void lk_df_path(char *b, size_t n) { const char *h = getenv("HOME"); snprintf(b, n, "%s/.landstalker_difficulty", h ? h : "."); }
static int lk_df_idx(const int *tab, int n, int pct, int dflt) { int i; for (i = 0; i < n; i++) if (tab[i] == pct) return i; return dflt; }
static void lk_df_load(void) {
    char p[512]; FILE *f; const char *e = getenv("LANDSTALKER_DIFF"); int a, b;
    lk_df[0] = 3; lk_df[1] = 1;
    lk_df_path(p, sizeof p); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d %d", &a, &b) == 2) { lk_df[0] = lk_df_idx(lk_df_dmg, 6, a, 3); lk_df[1] = lk_df_idx(lk_df_hp, 5, b, 1); } fclose(f); }
    if (e && sscanf(e, "%d,%d", &a, &b) == 2) { lk_df[0] = lk_df_idx(lk_df_dmg, 6, a, 3); lk_df[1] = lk_df_idx(lk_df_hp, 5, b, 1); }
}
int lk_diff_get(int which) { if (lk_df[0] < 0) lk_df_load(); return lk_df[which & 1]; }
void lk_diff_set(int which, int v) { char p[512]; FILE *f; lk_diff_get(0); lk_df[which & 1] = v; lk_df_path(p, sizeof p); f = fopen(p, "w"); if (f) { fprintf(f, "%d %d\n", lk_df_dmg[lk_df[0]], lk_df_hp[lk_df[1]]); fclose(f); } }
'''
    s = s.replace(a, module + a, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "lk_qs_install" in s, "func_table.c: run patch_quicksave.py first"
    module = r'''/* ---- LK_DIFF v2: damage taken / enemy HP (tools/patch_difficulty.py) ---- */
extern int lk_diff_get(int which);
static gen_func_t lk_o_ced, lk_o_cpd;
static void lk_scale_d0(int pct) {
    uint32_t d = g_m68k.d[0] & 0xFFFFu, n = d * (uint32_t)pct / 100u;
    if (d && !n) n = 1;
    if (n > 0xFFFFu) n = 0xFFFFu;
    g_m68k.d[0] = (g_m68k.d[0] & 0xFFFF0000u) | n;
}
static int lk_intro_room(void) { unsigned r = bus_read16(0xFF1204u); return r >= 139u && r <= 143u; }   /* INTRO_139..143: the cutscene is written for the original numbers (Enemy HP 300 %% left the golem statues of room 141 alive: the intro never went on, user 2026-10-28) */
static void lk_h_ced(void) {   /* CalculateEnemyDamageOutput: damage an enemy does to Nigel */
    static const int pct[6] = { 25, 50, 75, 100, 150, 200 }; int i;
    lk_o_ced();
    i = lk_diff_get(0);
    if (i != 3 && i >= 0 && i < 6 && !lk_intro_room()) lk_scale_d0(pct[i]);
}
static void lk_h_cpd(void) {   /* CalculatePlayerDamageOutput: damage Nigel does to an enemy; HP x % = damage / x % */
    static const int hp[5] = { 50, 100, 150, 200, 300 }; int i;
    lk_o_cpd();
    i = lk_diff_get(1);
    if (i != 1 && i >= 0 && i < 5 && !lk_intro_room()) lk_scale_d0(10000 / hp[i]);
}
static void lk_diff_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_ced = func_table_lookup(0x0165D0); lk_o_cpd = func_table_lookup(0x01657E);
    if (lk_o_ced && lk_o_cpd) { func_table_register(0x0165D0, lk_h_ced); func_table_register(0x01657E, lk_h_cpd); } else fprintf(stderr, "difficulty: damage functions not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_qs_install();   /* LK_QUICKSAVE v1 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_diff_install();   /* LK_DIFF v2 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
