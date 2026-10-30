#!/usr/bin/env python3
"""Timing model, step T6 (2026-10-29 night, docs/TIMING_PLAN.md): the POWER-ON TIME is ours.  No behaviour change.
Right after GPGX's system_init / system_reset (before the first bus access: lk_sram_load already advances the line clock) bus.c sets the whole time state itself (lk_time_power_on, block LK_STARTTIME):
  68K clock (+ the 40 cycles of the reset exception): the console starts the 68K at a fixed point of the VDP frame: (lines - 192 + 159 - 27 * PAL) lines + 1004 master clocks after the
  start of the emulated frame (which begins on line 192 = the default 192 line viewport), rounded down to 7 (68K clock edge); Z80 clock = the
  same rounded down to 15; Musashi's refresh counter = the next 128 * 7 boundary; line clock: base 0, line 192, 262 / 313 lines, VDP timing
  status bits 0, H-Int counter $FF, no interrupt pending, Z80 irq line clear, no DMA, FIFO empty, Z80 bus state 0 (Z80 held in reset, 68K window
  closed), pad deadlines 0.
Every value is compared once with what GPGX's reset left behind; a difference is printed ('LK_STARTTIME: ... differs') and our value is used
(so a difference shows up in the bench at once).  LANDSTALKER_TIMING=gpgx: GPGX's values stay.  With LANDSTALKER_TIME_SHADOW one summary
line 'TIME_SHADOW START own=1 fields=N mismatches=M'.
Quick saves need NO timing block: this build's quick save / quick load is the game's own save / load code (no GPGX state snapshot is ever
saved or loaded; grep state_save / state_load in src: none), and T2's lk_clk_resync re-reads the clock state at every quick load.
Not here: the Z80 boot stub (the game's init uploads a small Z80 program that GPGX's Z80 interpreter runs until InitZ80Driver uploads the
sound driver): that is Z80 CODE, not timing; moved to SOUND_PLAN (recompile it like the driver).
Idempotent (marker below).  usage: patch_starttime.py path/to/genrecomp   (after patch_padtime.py)"""
import os, sys
ROOT = sys.argv[1]
VER = "LK_STARTTIME v1"

def edit(path, edits):
    t = open(path).read()
    if VER in t:
        print(os.path.basename(path), "already patched:", VER); return
    for old, new, cnt in edits:
        assert t.count(old) == cnt, (path, old[:90], t.count(old))
        t = t.replace(old, new)
    open(path, "w").write(t); print(os.path.basename(path), "patched:", VER)

GEN = os.path.join(ROOT, "src/genrecomp.c")
GEN_EDITS = [("    system_reset();\n    lk_sram_load();\n",   # right after the reset, BEFORE the first bus access (lk_sram_load) advances the clock
              "    system_reset();\n    { extern void lk_time_power_on(void); lk_time_power_on(); }   /* LK_STARTTIME v1: the power-on time state is ours */\n    lk_sram_load();\n", 1)]

BUS = os.path.join(ROOT, "src/bus.c")
START = r'''/* ---- end LK_PADTIME ---- */

/* ---- LK_STARTTIME v1 (tools/patch_starttime.py, docs/TIMING_PLAN.md T6): the power-on time state is ours ---- */
#define LK_S_START_LINE 192   /* the emulated frame starts on line 192 (default viewport height before the game sets mode 5) */
void lk_time_power_on(void) {
    const char *t = getenv("LANDSTALKER_TIMING"), *s = getenv("LANDSTALKER_TIME_SHADOW");
    unsigned int lpf = vdp_pal ? 313 : 262, m, z, rf, i; int bad = 0, n = 0;
    struct { const char *name; unsigned int ours, gpgx; } f[24];
    if (t && !strcmp(t, "gpgx")) return;
    m = ((lpf - LK_S_START_LINE + 159 - (27 * vdp_pal)) * MCYCLES_PER_LINE) + 1004;   /* fixed power-on point of the 68K in the VDP frame */
    m = (m / 7) * 7;                     /* 68K clock edge */
    z = (m / 15) * 15;                   /* Z80 clock edge */
    m += 40 * 7;                         /* the 68000's reset exception takes 40 cycles (Musashi m68k_pulse_reset) */
    rf = ((m / (128 * 7)) * (128 * 7)) + 128 * 7;   /* Musashi's DRAM refresh counter: next 128-cycle boundary (after the reset exception, as in Musashi) */
#define LKS(nm, o, g) { f[n].name = nm; f[n].ours = (unsigned)(o); f[n].gpgx = (unsigned)(g); n++; }
    LKS("m68k.cycles", m, m68k.cycles) LKS("Z80.cycles", z, Z80.cycles) LKS("m68k.refresh_cycles", rf, m68k.refresh_cycles)
    LKS("mcycles_vdp", 0, mcycles_vdp) LKS("v_counter", LK_S_START_LINE, v_counter) LKS("viewport.h", LK_S_START_LINE, bitmap.viewport.h)
    LKS("lines_per_frame", lpf, lines_per_frame) LKS("status&8A", 0, status & LK_CLK_BITS) LKS("h_counter", 0xFF, h_counter)
    LKS("hint_pending", 0, hint_pending) LKS("vint_pending", 0, vint_pending) LKS("Z80.irq_state", CLEAR_LINE, Z80.irq_state)
    LKS("dma_endCycles", 0, dma_endCycles) LKS("dma_length", 0, dma_length)
    LKS("fifo0", 0, fifo_cycles[0]) LKS("fifo1", 0, fifo_cycles[1]) LKS("fifo2", 0, fifo_cycles[2]) LKS("fifo3", 0, fifo_cycles[3]) LKS("zstate", 0, zstate)
#undef LKS
    for (i = 0; i < (unsigned)n; i++) if (f[i].ours != f[i].gpgx) { bad++; fprintf(stderr, "LK_STARTTIME: %s differs: ours %u, GPGX's reset %u (ours used)\n", f[i].name, f[i].ours, f[i].gpgx); }
    /* our values everywhere: the GPGX globals, then the clock struct (T2) and the pad deadlines (T5) from them */
    m68k.cycles = m; Z80.cycles = z; m68k.refresh_cycles = rf;
    mcycles_vdp = 0; v_counter = LK_S_START_LINE; lines_per_frame = (uint16)lpf; status &= (uint16)~LK_CLK_BITS; h_counter = 0xFF;
    hint_pending = 0; vint_pending = 0; Z80.irq_state = CLEAR_LINE; dma_endCycles = 0;
    fifo_cycles[0] = fifo_cycles[1] = fifo_cycles[2] = fifo_cycles[3] = 0; zstate = 0;
    lk_clk_ready = 1; lk_clk_pull();
    for (i = 0; i < 8; i++) lk_p_lat[i] = 0;
    if (s && *s && strcmp(s, "0")) { FILE *fp = lk_clk_open(); fprintf(fp, "TIME_SHADOW START own=1 fields=%d mismatches=%d\n", n, bad); if (fp != stderr) fclose(fp); }
}
/* ---- end LK_STARTTIME ---- */
'''
BUS_EDITS = [("/* ---- end LK_PADTIME ---- */\n", START, 1)]
edit(GEN, GEN_EDITS)
edit(BUS, BUS_EDITS)
