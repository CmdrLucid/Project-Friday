#!/usr/bin/env python3
"""Timing model, step T5 (2026-10-29 night, docs/TIMING_PLAN.md): the PAD TIMING and the input part of the FRAME END are ours.  No behaviour change.
The TH latency of a pad (a pad whose TH pin is switched from output to input answers with the old TH state for 172 master clocks; GPGX
gamepad.c 'Decap Attack' fix) was decided by our doors since T1 (lk_t_pad: 'cycles < deadline', lk_t_pad_w: deadline = cycles + 172), but the
deadline itself lived in GPGX's gamepad[port].Latency and GPGX moved it at the frame end (input_end_frame -> gamepad_end_frame).
Now bus.c keeps the deadline per port (lk_p_lat[8], block LK_PADTIME): set by lk_t_pad_w, cleared where GPGX clears it (gamepad_reset and a TH
output write: hook lk_t_pad_clr), rebased at the frame end by lk_t_input_end (replaces the input_end_frame call of bus_advance_inner), and
lk_t_pad compares against OUR deadline.  GPGX's own field stays as a mirror for LANDSTALKER_TIMING=gpgx and the shadow compare.
The rest of the frame end (rebase of the clocks, DMA / FIFO reset, H-Int / V-Int) has been ours since T2; the mixer (audio_update) stays the
separate 'own mixer' item (SOUND_PLAN section 9).
Landstalker never switches TH to input (lk_t_pad_w 0 calls on all 62 bench runs), so the deadline is always 0: the step is about ownership.
Modes: default ours; LANDSTALKER_TIMING=gpgx = GPGX's deadline + input_end_frame; LANDSTALKER_TIME_SHADOW: both, GPGX's result used, exit line
'TIME_SHADOW PAD own=1 pad=checks/mismatches'.
Idempotent (marker below).  usage: patch_padtime.py path/to/genrecomp   (after patch_z80time.py)"""
import os, sys
ROOT = sys.argv[1]
VER = "LK_PADTIME v1"

def edit(path, edits):
    t = open(path).read()
    if VER in t:
        print(os.path.basename(path), "already patched:", VER); return
    for old, new, cnt in edits:
        assert t.count(old) == cnt, (path, old[:90], t.count(old))
        t = t.replace(old, new)
    open(path, "w").write(t); print(os.path.basename(path), "patched:", VER)

PAD = os.path.join(ROOT, "ext/Genesis-Plus-GX/core/input_hw/gamepad.c")
PAD_EDITS = [
    ("\n  gamepad[port].Latency = 0;\n",   # gamepad_reset
     "\n  gamepad[port].Latency = 0;\n  { extern void lk_t_pad_clr(int); lk_t_pad_clr(port); }   /* LK_PADTIME v1: our deadline too */\n", 1),
    ("    gamepad[port].Latency = 0;\n\n    /* 6-Buttons",   # TH configured as output
     "    gamepad[port].Latency = 0;\n    { extern void lk_t_pad_clr(int); lk_t_pad_clr(port); }   /* LK_PADTIME v1 */\n\n    /* 6-Buttons", 1),
]

BUS = os.path.join(ROOT, "src/bus.c")
OLD_PAD = '''int lk_t_pad(int port, unsigned int step, unsigned int cycles, unsigned int latency) {   /* G9: TH latency test of gamepad_read (1 = TH state switching has not happened yet) */
    lk_t_door_t *d = &lk_t_door[LK_T_PAD]; (void)port; (void)step;
    d->before = d->after = cycles; d->calls++; return cycles < latency; }
unsigned int lk_t_pad_w(int port, unsigned int cycles) {   /* G9: deadline of the TH 0->1 latency set by gamepad_write */
    lk_t_door_t *d = &lk_t_door[LK_T_PADW]; (void)port;
    d->before = d->after = cycles; d->calls++; return cycles + 172; }
'''
NEW_PAD = r'''/* ---- LK_PADTIME v1 (tools/patch_padtime.py, docs/TIMING_PLAN.md T5): the pad TH latency deadline is ours ---- */
static unsigned int lk_p_lat[8];   /* per port: master clock (in this frame) until which a pad still answers with the old TH state; 0 = none */
static int lk_p_own = 1, lk_p_shadow;
static unsigned long long lk_p_chk, lk_p_bad;
static void lk_p_dump(void) { FILE *f = lk_clk_open(); fprintf(f, "TIME_SHADOW PAD own=%d pad=%llu/%llu (checks/mismatches)\n", lk_p_own, lk_p_chk, lk_p_bad); if (f != stderr) fclose(f); }
__attribute__((constructor)) static void lk_p_init(void) {
    const char *t = getenv("LANDSTALKER_TIMING"), *s = getenv("LANDSTALKER_TIME_SHADOW");
    if (t && !strcmp(t, "gpgx")) lk_p_own = 0;
    if (lk_p_own && s && *s && strcmp(s, "0")) { lk_p_shadow = 1; atexit(lk_p_dump); }
}
void lk_t_pad_clr(int port) { if (port >= 0 && port < 8) lk_p_lat[port] = 0; }   /* pad reset / TH switched to output */
int lk_t_pad(int port, unsigned int step, unsigned int cycles, unsigned int latency) {   /* G9: TH latency test of gamepad_read (1 = TH state switching has not happened yet) */
    lk_t_door_t *d = &lk_t_door[LK_T_PAD]; int ours = (port >= 0 && port < 8) ? (cycles < lk_p_lat[port]) : 0; (void)step;
    d->before = d->after = cycles; d->calls++;
    if (!lk_p_own) return cycles < latency;
    if (lk_p_shadow) {
        lk_p_chk++;
        if (ours != (cycles < latency) || (port >= 0 && port < 8 && lk_p_lat[port] != latency))
            if (++lk_p_bad <= 6) { FILE *f = lk_clk_open(); fprintf(f, "TIME_SHADOW PAD MISMATCH #%llu: frame %ld port %d cycles %u deadline ours %u gpgx %u\n", lk_p_bad, platform_frame_number(), port, cycles, (port >= 0 && port < 8) ? lk_p_lat[port] : 0, latency); if (f != stderr) fclose(f); }
        return cycles < latency;
    }
    return ours;
}
unsigned int lk_t_pad_w(int port, unsigned int cycles) {   /* G9: TH switched to input while low: the 0->1 switch shows 172 master clocks later */
    lk_t_door_t *d = &lk_t_door[LK_T_PADW];
    d->before = d->after = cycles; d->calls++;
    if (port >= 0 && port < 8) lk_p_lat[port] = cycles + 172;
    return cycles + 172;   /* GPGX's field keeps a copy (rollback / shadow) */
}
static void lk_t_input_end(unsigned int cycles) {   /* frame end: the deadlines move into the next frame's clock (GPGX gamepad_end_frame) */
    int i;
    if (!lk_p_own || lk_p_shadow) input_end_frame(cycles);
    if (!lk_p_own) return;
    for (i = 0; i < 8; i++) lk_p_lat[i] = (lk_p_lat[i] > cycles) ? lk_p_lat[i] - cycles : 0;
}
/* ---- end LK_PADTIME ---- */
'''
BUS_EDITS = [
    (OLD_PAD, NEW_PAD, 1),
    ("            input_end_frame(lk_clk.base);\n", "            lk_t_input_end(lk_clk.base);   /* LK_PADTIME v1 */\n", 1),
]
edit(PAD, PAD_EDITS)
edit(BUS, BUS_EDITS)
