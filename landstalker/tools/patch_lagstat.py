#!/usr/bin/env python3
"""Timing phase 2, measurement (2026-10-30, docs/TIMING_PLAN.md section 16): LAG FRAME counter ('the room stutters').  No behaviour change.
The game's main loop ends every frame in WaitUntilVBlank $000B5E: it sets bit 7 of g_InterruptFlags $FF0F8B and busy-waits until the VBlank
interrupt clears it.  If the bit is NOT set when the VBlank line starts, the main loop has not finished its frame: the game drops a frame
(its logic and sprites update at half rate there = the stutter of busy rooms).
LANDSTALKER_LAGSTAT=path: at every VBlank line bus_advance_inner reads that bit; at exit one line per room is appended to the file:
  LAGSTAT <input script> room <g_RmNum1 $FF1204> frames <N> lag <L> lag_display_off <D> longest_run <R> stutter_frames <S> hitches <H> loading <G>
v2 (2026-10-30, HANDOFF 0a182): a frame is lag when the wait bit is clear at VBlank (the main loop did not reach WaitUntilVBlank = whole GameLoop
passes dropped), WITH OR WITHOUT display: the game turns the display off in fast uploads while the loop still runs.  lag_display_off = the part of
lag with the display off (genuine overload, already included in lag).  loading = display-off frames with the wait bit clear within LK_LAG_LOADWIN
(90) frames after a room number change: a real room load / fade, NOT counted as lag.  Plus a TOTAL line.  Without the variable: one test of a global flag per frame.
Idempotent (marker below).  usage: patch_lagstat.py path/to/genrecomp   (after patch_starttime.py)"""
import os, sys
ROOT = sys.argv[1]
VER = "LK_LAGSTAT v2"
BUS = os.path.join(ROOT, "src/bus.c")
t = open(BUS).read()
if VER in t:
    print("bus.c already patched:", VER); sys.exit(0)
HOOK = "        if (vblank_now && s_vblank_cb) { s_since_vb = 0; s_vblank_cb(); lk_clk_pull(); }\n"
assert t.count(HOOK) == 1
CODE = r'''/* ---- LK_LAGSTAT v2 (tools/patch_lagstat.py, TIMING_PLAN section 16): lag frames per room (the main loop missed the VBlank) ---- */
static int lk_lag_on = -1;
static unsigned long lk_lag_f[1024], lk_lag_l[1024], lk_lag_d[1024], lk_lag_ld[1024], lk_lag_run[1024], lk_lag_s[1024], lk_lag_h[1024], lk_lag_cur;   /* s = lag frames in runs of 1..2 (stutter), h = number of runs >= 3 (hitches) */
static int lk_lag_tr = -1, lk_lag_room, lk_lag_prev = -1; static unsigned long lk_lag_fr, lk_lag_chg;
#define LK_LAG_LOADWIN 90
static void lk_lag_dump(void) {
    const char *p = getenv("LANDSTALKER_LAGSTAT"), *s = getenv("GENRECOMP_INPUTSCRIPT"); FILE *f; int r; unsigned long F = 0, L = 0, D = 0, G = 0;
    if (!p || !(f = fopen(p, "a"))) return;
    for (r = 0; r < 1024; r++) if (lk_lag_f[r]) {
        fprintf(f, "LAGSTAT %s room %d frames %lu lag %lu lag_display_off %lu longest_run %lu stutter_frames %lu hitches %lu loading %lu\n", s ? s : "-", r, lk_lag_f[r], lk_lag_l[r], lk_lag_d[r], lk_lag_run[r], lk_lag_s[r], lk_lag_h[r], lk_lag_ld[r]);
        F += lk_lag_f[r]; L += lk_lag_l[r]; D += lk_lag_d[r]; G += lk_lag_ld[r]; }
    fprintf(f, "LAGSTAT %s TOTAL frames %lu lag %lu lag_display_off %lu loading %lu\n", s ? s : "-", F, L, D, G);
    fclose(f);
}
static void lk_lag_vblank(void) {   /* at the VBlank line: is the main loop waiting in WaitUntilVBlank (bit 7 of $FF0F8B set)? */
    int room; uint8_t fl;
    if (lk_lag_on < 0) { const char *p = getenv("LANDSTALKER_LAGSTAT"); lk_lag_on = p && *p; if (lk_lag_on) atexit(lk_lag_dump); }
    if (!lk_lag_on) return;
    room = bus_ram_read16(0x1204) & 1023; fl = bus_ram_read8(0x0F8B);
    lk_lag_fr++; if (room != lk_lag_prev) { lk_lag_prev = room; lk_lag_chg = lk_lag_fr; }
    lk_lag_f[room]++;
    if (lk_lag_tr < 0) lk_lag_tr = getenv("LANDSTALKER_LAGSTAT_TRACE") != NULL;
    if (lk_lag_tr) fprintf(stderr, "LAGFRAME %lu room %d wait %d display %d\n", lk_lag_fr, room, (fl >> 7) & 1, (reg[1] >> 6) & 1);   /* debug: one line per frame */
    if (fl & 0x80) goto ok;   /* main loop is waiting in WaitUntilVBlank: frame on time */
    if (!(reg[1] & 0x40) && lk_lag_fr - lk_lag_chg < LK_LAG_LOADWIN) { lk_lag_ld[room]++; goto ok; }   /* room load / fade in progress */
    lk_lag_l[room]++; lk_lag_room = room; if (!(reg[1] & 0x40)) lk_lag_d[room]++;
    if (++lk_lag_cur > lk_lag_run[room]) lk_lag_run[room] = lk_lag_cur;
    return;
ok: if (lk_lag_cur) { if (lk_lag_cur <= 2) lk_lag_s[lk_lag_room] += lk_lag_cur; else lk_lag_h[lk_lag_room]++; }
    lk_lag_cur = 0;
}
/* ---- end LK_LAGSTAT ---- */
'''
# the code goes in front of bus_advance_inner's definition (it uses bus_ram_read8/16, declared in bus.h)
ANCH = "/* ---- LK_TIMESTATE v1 (tools/patch_timestate.py"
assert t.count(ANCH) == 1
t = t.replace(ANCH, CODE + ANCH, 1)
t = t.replace(HOOK, "        if (vblank_now) lk_lag_vblank();   /* LK_LAGSTAT v2 */\n" + HOOK, 1)
open(BUS, "w").write(t); print("bus.c patched:", VER)
