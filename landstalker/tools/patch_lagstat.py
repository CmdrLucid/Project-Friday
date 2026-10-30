#!/usr/bin/env python3
"""Timing phase 2, measurement (2026-10-30, docs/TIMING_PLAN.md section 16): LAG FRAME counter ('the room stutters').  No behaviour change.
The game's main loop ends every frame in WaitUntilVBlank $000B5E: it sets bit 7 of g_InterruptFlags $FF0F8B and busy-waits until the VBlank
interrupt clears it.  If the bit is NOT set when the VBlank line starts, the main loop has not finished its frame: the game drops a frame
(its logic and sprites update at half rate there = the stutter of busy rooms).
LANDSTALKER_LAGSTAT=path: at every VBlank line bus_advance_inner reads that bit; at exit one line per room is appended to the file:
  LAGSTAT <input script> room <g_RmNum1 $FF1204> frames <N> lag <L> lag_display_off <D> longest_run <R>
(display off = loading / fades, not stutter) plus a TOTAL line.  Without the variable: one test of a global flag per frame.
Idempotent (marker below).  usage: patch_lagstat.py path/to/genrecomp   (after patch_starttime.py)"""
import os, sys
ROOT = sys.argv[1]
VER = "LK_LAGSTAT v1"
BUS = os.path.join(ROOT, "src/bus.c")
t = open(BUS).read()
if VER in t:
    print("bus.c already patched:", VER); sys.exit(0)
HOOK = "        if (vblank_now && s_vblank_cb) { s_since_vb = 0; s_vblank_cb(); lk_clk_pull(); }\n"
assert t.count(HOOK) == 1
CODE = r'''/* ---- LK_LAGSTAT v1 (tools/patch_lagstat.py, TIMING_PLAN section 16): lag frames per room (the main loop missed the VBlank) ---- */
static int lk_lag_on = -1;
static unsigned long lk_lag_f[1024], lk_lag_l[1024], lk_lag_d[1024], lk_lag_run[1024], lk_lag_s[1024], lk_lag_h[1024], lk_lag_cur;   /* s = lag frames in runs of 1..2 (stutter), h = number of runs >= 3 (hitches) */
static int lk_lag_room;
static void lk_lag_dump(void) {
    const char *p = getenv("LANDSTALKER_LAGSTAT"), *s = getenv("GENRECOMP_INPUTSCRIPT"); FILE *f; int r; unsigned long F = 0, L = 0, D = 0;
    if (!p || !(f = fopen(p, "a"))) return;
    for (r = 0; r < 1024; r++) if (lk_lag_f[r]) {
        fprintf(f, "LAGSTAT %s room %d frames %lu lag %lu lag_display_off %lu longest_run %lu stutter_frames %lu hitches %lu\n", s ? s : "-", r, lk_lag_f[r], lk_lag_l[r], lk_lag_d[r], lk_lag_run[r], lk_lag_s[r], lk_lag_h[r]);
        F += lk_lag_f[r]; L += lk_lag_l[r]; D += lk_lag_d[r]; }
    fprintf(f, "LAGSTAT %s TOTAL frames %lu lag %lu lag_display_off %lu\n", s ? s : "-", F, L, D);
    fclose(f);
}
static void lk_lag_vblank(void) {   /* at the VBlank line: is the main loop waiting in WaitUntilVBlank (bit 7 of $FF0F8B set)? */
    int room; uint8_t fl;
    if (lk_lag_on < 0) { const char *p = getenv("LANDSTALKER_LAGSTAT"); lk_lag_on = p && *p; if (lk_lag_on) atexit(lk_lag_dump); }
    if (!lk_lag_on) return;
    room = bus_ram_read16(0x1204) & 1023; fl = bus_ram_read8(0x0F8B);
    lk_lag_f[room]++;
    if ((fl & 0x80) || !(reg[1] & 0x40)) {   /* a run of lag frames ends: 1..2 frames = stutter, longer = a hitch */
        if (lk_lag_cur) { if (lk_lag_cur <= 2) lk_lag_s[lk_lag_room] += lk_lag_cur; else lk_lag_h[lk_lag_room]++; }
        lk_lag_cur = 0;
        if (!(fl & 0x80)) lk_lag_d[room]++;   /* display off: loading / fade, not counted as stutter */
        return;
    }
    lk_lag_l[room]++; lk_lag_room = room; if (++lk_lag_cur > lk_lag_run[room]) lk_lag_run[room] = lk_lag_cur;
}
/* ---- end LK_LAGSTAT ---- */
'''
# the code goes in front of bus_advance_inner's definition (it uses bus_ram_read8/16, declared in bus.h)
ANCH = "/* ---- LK_TIMESTATE v1 (tools/patch_timestate.py"
assert t.count(ANCH) == 1
t = t.replace(ANCH, CODE + ANCH, 1)
t = t.replace(HOOK, "        if (vblank_now) lk_lag_vblank();   /* LK_LAGSTAT v1 */\n" + HOOK, 1)
open(BUS, "w").write(t); print("bus.c patched:", VER)
