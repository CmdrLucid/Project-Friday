#!/usr/bin/env python3
"""Timing phase 2 option (2026-10-30, user: 'wir wollen ja gar keine CPU mehr nachbauen, sondern nativ laufen', docs/TIMING_PLAN.md section 16):
NATIVE PACE = the frame waits for the game instead of the game losing a frame.
The game's main loop ends every pass in WaitUntilVBlank $000B5E (sets bit 7 of g_InterruptFlags $FF0F8B, waits for the VBlank handler
HandleVBlankInterrupt $0011DE to clear it).  In busy rooms (room 5 SWAMP_SHRINE_5, HANDOFF 0a182) a pass needs more than the 68K cycles of
one frame, the VBlank arrives before the pass is done and the game runs that pass at half rate (slow motion).  Our code runs natively and
is far faster than the console, so only the COUNTED clock is the limit.
LANDSTALKER_NATIVEPACE=1: when the line clock is about to enter the VBlank line and the wait bit is still clear, the clock is held at the end
of the last visible line (the extra cycles are not counted) until the main loop reaches WaitUntilVBlank; then the VBlank comes at once.
Safety cap (code that waits for VBlank without the wait bit, room loads): at most LANDSTALKER_NATIVEPACE_CAP lines (default 262 = one frame)
are held per frame, then the VBlank comes anyway.  LANDSTALKER_NATIVEPACE_STAT=1 prints held frames / lines per second to stderr.
Menu (v2, 2026-10-30): Options > Quality of Life > Native Pace Off / On, saved in ~/.landstalker_nativepace ('0' / '1'), read live (no restart).
Default (2026-10-30 later, user: 'Nativ-Tempo standardmaessig an'): On when ~/.landstalker_nativepace does not exist; Off while GENRECOMP_INPUTSCRIPT is set (replays of older recordings, timebench);
the recording script v2 writes the value used live as LANDSTALKER_NATIVEPACE=<0|1> into rec_<t>.cfg (the env wins in the replay).
The env var, if set (also '0'), wins over the menu value (test launchers, headless tests).
Default (Off, no env) = original timing, bit identical.  Only in the own timing mode (LANDSTALKER_TIMING=gpgx ignores it).  Changes the game's
timing on purpose: recordings made without it do not replay with it.
Idempotent (marker below).  usage: patch_nativepace.py path/to/genrecomp   (after patch_vdpwait.py)"""
import os, sys
ROOT = sys.argv[1]
VER = "LK_NATIVEPACE v2"
BUS = os.path.join(ROOT, "src/bus.c")
t = open(BUS).read()
if VER in t:
    print("bus.c already patched:", VER); sys.exit(0)
OLD = "LK_NATIVEPACE v1" in t
if OLD:   # upgrade a v1 tree: cut the old block, the hooks only get the new marker
    a = t.index("/* ---- LK_NATIVEPACE v1"); b = t.index("/* ---- end LK_NATIVEPACE ---- */\n") + len("/* ---- end LK_NATIVEPACE ---- */\n")
    t = t[:a] + "@@NPCODE@@" + t[b:]
CODE = r'''/* ---- LK_NATIVEPACE v2 (tools/patch_nativepace.py, TIMING_PLAN section 16): the frame waits for the game's main loop ---- */
static int lk_np_init, lk_np_env = -1, lk_np_gpgx, lk_np_menu_v = -1; static unsigned long lk_np_cap, lk_np_used, lk_np_stat, lk_np_frames, lk_np_held, lk_np_lines, lk_np_capped;
static void lk_np_path(char *b, size_t n) { const char *h = getenv("HOME"); snprintf(b, n, "%s/.landstalker_nativepace", h ? h : "."); }
int lk_np_menu_get(void) {   /* Options > Quality of Life > Native Pace (platform_option_get id 40); default On (user 2026-10-30), but Off while an input script is replayed (old recordings / bench were made without it) */
    if (lk_np_menu_v < 0) { char p[512]; FILE *f; int v; lk_np_menu_v = getenv("GENRECOMP_INPUTSCRIPT") ? 0 : 1; lk_np_path(p, sizeof p); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) == 1) lk_np_menu_v = v == 1; fclose(f); } }
    return lk_np_menu_v;
}
void lk_np_menu_set(int v) { char p[512]; FILE *f; lk_np_menu_get(); lk_np_menu_v = v ? 1 : 0; lk_np_path(p, sizeof p); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_np_menu_v); fclose(f); } }
static inline int lk_np_enabled(void) {   /* env LANDSTALKER_NATIVEPACE (set, also 0) wins, else the menu value; LANDSTALKER_TIMING=gpgx never */
    if (!lk_np_init) {
        const char *e = getenv("LANDSTALKER_NATIVEPACE"), *t = getenv("LANDSTALKER_TIMING"), *c = getenv("LANDSTALKER_NATIVEPACE_CAP"), *s = getenv("LANDSTALKER_NATIVEPACE_STAT");
        lk_np_init = 1; lk_np_gpgx = t && !strcmp(t, "gpgx"); lk_np_env = e && *e ? (strcmp(e, "0") != 0) : -1;
        lk_np_cap = (c && *c ? strtoul(c, NULL, 10) : 262UL) * MCYCLES_PER_LINE; lk_np_stat = s && *s && strcmp(s, "0");
        if (lk_np_env > 0 && !lk_np_gpgx) fprintf(stderr, "timing: LANDSTALKER_NATIVEPACE=1, the frame waits for the main loop (cap %lu lines)\n", lk_np_cap / MCYCLES_PER_LINE);
    }
    return !lk_np_gpgx && (lk_np_env >= 0 ? lk_np_env : lk_np_menu_get());   /* Off: one test per call, the call is made at the VBlank line only */
}
/* called at the top of the line loop: 1 = hold the clock (do not step into the VBlank line yet) */
static int lk_np_hold(int next_line, int vblank_line) {
    unsigned int end, ex;
    if (next_line != vblank_line || !lk_np_enabled()) return 0;
    if (bus_ram_read8(0x0F8B) & 0x80) return 0;   /* the main loop waits in WaitUntilVBlank: VBlank may come */
    end = lk_clk.base + MCYCLES_PER_LINE - 1; ex = m68k.cycles - end;
    if (lk_np_used + ex > lk_np_cap) { lk_np_capped++; return 0; }
    if (!lk_np_used) lk_np_held++;
    lk_np_used += ex; m68k.cycles = end; lk_clk.cyc = end; s_expected_cycles = end;
    return 1;
}
static void lk_np_vblank(void) {   /* at the VBlank line */
    if (!lk_np_init || !lk_np_enabled()) { lk_np_used = 0; return; }
    lk_np_lines += lk_np_used / MCYCLES_PER_LINE; lk_np_used = 0;
    if (lk_np_stat && ++lk_np_frames >= 60) {
        fprintf(stderr, "nativepace: 60 frames, held %lu, extra lines %lu, cap hit %lu\n", lk_np_held, lk_np_lines, lk_np_capped);
        lk_np_frames = lk_np_held = lk_np_lines = lk_np_capped = 0;
    }
}
/* ---- end LK_NATIVEPACE ---- */
'''
E = [
    # the code goes in front of the cycle sink (it uses s_expected_cycles, lk_clk, bus_ram_read8)
    ("static void bus_advance(unsigned int mc) {\n",
     CODE + "static void bus_advance(unsigned int mc) {\n", 1),
    ("    while ((m68k.cycles - lk_clk.base) >= MCYCLES_PER_LINE) {\n        if (lk_clk_shadow) lk_clk_check(\"line step\");   /* LK_TIMESTATE v1 */\n",
     "    while ((m68k.cycles - lk_clk.base) >= MCYCLES_PER_LINE) {\n"
     "        if (lk_np_hold((int)lk_clk.line + 1, bitmap.viewport.h > 0 ? bitmap.viewport.h : 224)) break;   /* LK_NATIVEPACE v2 */\n"
     "        if (lk_clk_shadow) lk_clk_check(\"line step\");   /* LK_TIMESTATE v1 */\n", 1),
    ("        if (vblank_now && s_vblank_cb) {", "        if (vblank_now) lk_np_vblank();   /* LK_NATIVEPACE v2 */\n        if (vblank_now && s_vblank_cb) {", 1),
]
if OLD:   # hooks of v1 are in place: only the new block and the markers
    t = t.replace("@@NPCODE@@", CODE).replace("/* LK_NATIVEPACE v1 */", "/* LK_NATIVEPACE v2 */"); E = []
for old, new, cnt in E:
    assert t.count(old) == cnt, (old[:80], t.count(old))
    t = t.replace(old, new)
open(BUS, "w").write(t); print("bus.c patched:", VER)
