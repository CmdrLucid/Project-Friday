#!/usr/bin/env python3
"""Timing model, step T2 (2026-10-29, docs/TIMING_PLAN.md): OUR OWN CLOCK STATE is the master.  No behaviour change.
bus.c gets a struct `lk_clk` (frame base = mcycles_vdp, cycle mirror of m68k.cycles, line, lines per frame, the timing bits of the VDP status (DMA busy 0x02, VBlank 0x08,
VINT 0x80), H-Int counter, H-Int / V-Int pending, Z80 irq line, DMA end, FIFO slots).  The line loop of bus_advance_inner (the copy of GPGX's system_frame_gen) now reads and
changes ONLY the struct.  The GPGX globals (mcycles_vdp, v_counter, lines_per_frame, status bits, h_counter, hint_pending, vint_pending, Z80.irq_state, dma_endCycles,
fifo_cycles[]) are written FROM the struct (lk_clk_push) at every point where GPGX code still reads them (before the Z80 run, render_line, the VBlank callback, an
interrupt entry = the interrupt acknowledge, the frame end), and what GPGX changes inside its code is read back into the struct (lk_clk_pull) right after every T1 door
(lk_t_out), after bus_finish_dma, after an interrupt entry, after the VBlank callback and the Z80 run, after an interpreter step.
m68k.cycles itself stays the one shared counter (GPGX code adds to it in 40 places); the struct keeps a mirror (clk.cyc) that the shadow compares.
Shadow check: LANDSTALKER_TIME_SHADOW=1 (stderr) or =path (appended): at EVERY door entry (outermost door only) and at the start of every line step the struct is compared with
the GPGX globals; the first mismatches are printed with frame / line / door / call stack (func_table_dump_stack), the summary 'TIME_SHADOW checks=N mismatches=M' at exit.
After a mismatch the struct is refilled from the globals (no cascade).  Without the variable: one test of a global flag per door.
Rollback: LANDSTALKER_TIMING=gpgx = the GPGX globals are the master again (the struct is refilled from them at the top of every bus_advance_inner; the loop is the same code).
Quick load: the quick load of this build is the game's own load code (no GPGX state load); lk_clk_resync("quick load") at its start refills the struct from the globals and
reports (shadow only) how many fields differed.  A real state load (T6) must call lk_clk_resync too.
Idempotent (marker below).  usage: patch_timestate.py path/to/genrecomp   (after patch_timedoors.py)"""
import os, sys
ROOT = sys.argv[1]
VER = "LK_TIMESTATE v1"

def edit(path, edits):
    t = open(path).read()
    if VER in t:
        print(os.path.basename(path), "already patched:", VER); return
    for old, new, cnt in edits:
        assert t.count(old) == cnt, (path, old[:90], t.count(old))
        t = t.replace(old, new)
    open(path, "w").write(t); print(os.path.basename(path), "patched:", VER)

CLK = r'''
/* ---- LK_TIMESTATE v1 (tools/patch_timestate.py, docs/TIMING_PLAN.md T2): our own clock state, the master of the line loop ---- */
typedef struct {
    unsigned base;      /* start of the current line in the frame's master clocks (GPGX mcycles_vdp) */
    unsigned cyc;       /* mirror of m68k.cycles (the shared counter, GPGX adds to it), synced at every door / bus_advance exit */
    unsigned line;      /* current line (v_counter) */
    unsigned lpf;       /* lines per frame */
    unsigned status;    /* the timing bits of the VDP status: 0x02 DMA busy, 0x08 VBlank, 0x80 VINT (LK_CLK_BITS) */
    unsigned hcount;    /* H-Int counter (h_counter) */
    unsigned hint, vint;/* H-Int / V-Int pending (hint_pending 0x10, vint_pending) */
    unsigned zirq;      /* Z80 irq line (Z80.irq_state) */
    unsigned dma_end;   /* dma_endCycles */
    unsigned fifo[4];   /* fifo_cycles[] */
} lk_clk_t;
lk_clk_t lk_clk;
#define LK_CLK_BITS 0x008Au
static int lk_clk_own = 1, lk_clk_shadow, lk_clk_depth;   /* own = master (default); LANDSTALKER_TIMING=gpgx -> 0 */
static int lk_clk_ready;   /* the struct is filled from the GPGX globals (system_init / system_reset) at the first use */
static unsigned long long lk_clk_checks, lk_clk_mism, lk_clk_fields, lk_clk_resyncs;
static inline void lk_clk_push(void) {   /* struct -> GPGX globals (what GPGX code reads) */
    mcycles_vdp = lk_clk.base; v_counter = (uint16)lk_clk.line; lines_per_frame = (uint16)lk_clk.lpf;
    status = (uint16)((status & ~LK_CLK_BITS) | (lk_clk.status & LK_CLK_BITS));
    h_counter = (uint8)lk_clk.hcount; hint_pending = (uint8)lk_clk.hint; vint_pending = (uint8)lk_clk.vint; Z80.irq_state = (uint8)lk_clk.zirq;
    dma_endCycles = lk_clk.dma_end; fifo_cycles[0] = lk_clk.fifo[0]; fifo_cycles[1] = lk_clk.fifo[1]; fifo_cycles[2] = lk_clk.fifo[2]; fifo_cycles[3] = lk_clk.fifo[3];
}
static inline void lk_clk_pull(void) {   /* GPGX globals -> struct (what GPGX changed inside a door) */
    lk_clk.base = mcycles_vdp; lk_clk.cyc = m68k.cycles; lk_clk.line = v_counter; lk_clk.lpf = lines_per_frame; lk_clk.status = status & LK_CLK_BITS;
    lk_clk.hcount = h_counter; lk_clk.hint = hint_pending; lk_clk.vint = vint_pending; lk_clk.zirq = Z80.irq_state;
    lk_clk.dma_end = dma_endCycles; lk_clk.fifo[0] = fifo_cycles[0]; lk_clk.fifo[1] = fifo_cycles[1]; lk_clk.fifo[2] = fifo_cycles[2]; lk_clk.fifo[3] = fifo_cycles[3];
}
typedef struct { const char *n; unsigned a, g; } lk_clk_df_t;
static int lk_clk_diff(lk_clk_df_t *df) {   /* the fields where the struct and the GPGX globals differ */
    int nd = 0;
#define LKC(name, ours, gp) if ((unsigned)(ours) != (unsigned)(gp)) { df[nd].n = name; df[nd].a = (unsigned)(ours); df[nd].g = (unsigned)(gp); nd++; }
    LKC("base/mcycles_vdp", lk_clk.base, mcycles_vdp) LKC("cyc/m68k.cycles", lk_clk.cyc, m68k.cycles) LKC("line/v_counter", lk_clk.line, v_counter)
    LKC("lpf/lines_per_frame", lk_clk.lpf, lines_per_frame) LKC("status&8A", lk_clk.status, status & LK_CLK_BITS) LKC("hcount/h_counter", lk_clk.hcount, h_counter)
    LKC("hint/hint_pending", lk_clk.hint, hint_pending) LKC("vint/vint_pending", lk_clk.vint, vint_pending) LKC("zirq/Z80.irq_state", lk_clk.zirq, Z80.irq_state)
    LKC("dma_end/dma_endCycles", lk_clk.dma_end, dma_endCycles) LKC("fifo0", lk_clk.fifo[0], fifo_cycles[0]) LKC("fifo1", lk_clk.fifo[1], fifo_cycles[1])
    LKC("fifo2", lk_clk.fifo[2], fifo_cycles[2]) LKC("fifo3", lk_clk.fifo[3], fifo_cycles[3])
#undef LKC
    return nd;
}
static inline void lk_clk_ensure(void) { if (!lk_clk_ready) { lk_clk_ready = 1; lk_clk_pull(); } }
static FILE *lk_clk_open(void) { const char *e = getenv("LANDSTALKER_TIME_SHADOW"); FILE *f; if (!e || !*e || !strcmp(e, "1")) return stderr; f = fopen(e, "a"); return f ? f : stderr; }
static void lk_clk_check(const char *where) {   /* shadow: the struct must equal the GPGX globals here */
    lk_clk_df_t df[16]; int nd, i; lk_clk_checks++;
    if (!(nd = lk_clk_diff(df))) return;
    lk_clk_mism++; lk_clk_fields += nd;
    if (lk_clk_mism <= 6) {
        FILE *f = lk_clk_open();
        fprintf(f, "TIME_SHADOW MISMATCH #%llu at %s: frame %ld line %u (v_counter %u) cyc-in-line %d:", lk_clk_mism, where, platform_frame_number(), lk_clk.line, (unsigned)v_counter, (int)(m68k.cycles - mcycles_vdp));
        for (i = 0; i < nd; i++) fprintf(f, " %s ours=%u gpgx=%u;", df[i].n, df[i].a, df[i].g);
        fprintf(f, " stack:"); func_table_dump_stack(f); fprintf(f, "\n");
        if (f != stderr) fclose(f);
    }
    lk_clk_pull();   /* no cascade: continue with GPGX's values */
}
void lk_clk_resync(const char *why) {   /* the struct is refilled from the GPGX globals (state load / quick load) */
    lk_clk_df_t df[16]; int nd, i; lk_clk_ensure(); nd = lk_clk_diff(df); lk_clk_resyncs++;
    lk_clk_pull();
    if (lk_clk_shadow) {
        FILE *f = lk_clk_open();
        fprintf(f, "TIME_SHADOW RESYNC (%s) frame %ld: struct refilled from the GPGX globals: line=%u base=%u cyc=%u lpf=%u status=%02X hcount=%u hint=%u vint=%u zirq=%u dma_end=%u; %d field(s) had differed; checks so far %llu mismatches %llu\n",
                why, platform_frame_number(), lk_clk.line, lk_clk.base, lk_clk.cyc, lk_clk.lpf, lk_clk.status, lk_clk.hcount, lk_clk.hint, lk_clk.vint, lk_clk.zirq, lk_clk.dma_end, nd, lk_clk_checks, lk_clk_mism);
        for (i = 0; i < nd; i++) fprintf(f, "TIME_SHADOW RESYNC differed: %s struct=%u gpgx=%u\n", df[i].n, df[i].a, df[i].g);
        if (f != stderr) fclose(f);
    }
}
static void lk_clk_dump(void) {
    FILE *f = lk_clk_open();
    fprintf(f, "TIME_SHADOW checks=%llu mismatches=%llu fields=%llu resyncs=%llu\n", lk_clk_checks, lk_clk_mism, lk_clk_fields, lk_clk_resyncs);
    if (f != stderr) fclose(f);
}
__attribute__((constructor)) static void lk_clk_init(void) {
    const char *t = getenv("LANDSTALKER_TIMING"), *s = getenv("LANDSTALKER_TIME_SHADOW");
    if (t && !strcmp(t, "gpgx")) { lk_clk_own = 0; fprintf(stderr, "timing: LANDSTALKER_TIMING=gpgx, the GPGX globals are the clock master (T2 rollback)\n"); }
    if (s && *s && strcmp(s, "0")) { lk_clk_shadow = 1; atexit(lk_clk_dump); }
}
/* ---- end LK_TIMESTATE (struct) ---- */

'''

p = os.path.join(ROOT, "src/bus.c")
edit(p, [
 ("\n/* ---- LK_TIMEDOORS v1 (tools/patch_timedoors.py", CLK + "/* ---- LK_TIMEDOORS v1 (tools/patch_timedoors.py", 1),
 # doors: shadow check at the entry of the outermost door, read back after every door
 ("static inline unsigned lk_t_in(int id) { lk_t_door_t *d = &lk_t_door[id]; d->before = m68k.cycles;",
  "static inline unsigned lk_t_in(int id) { lk_t_door_t *d = &lk_t_door[id]; lk_clk_ensure(); if (lk_clk_depth++ == 0 && lk_clk_shadow) lk_clk_check(lk_t_name[id]); d->before = m68k.cycles;", 1),
 ("    lk_t_door_t *d = &lk_t_door[id]; unsigned a = m68k.cycles, za = Z80.cycles;\n",
  "    lk_t_door_t *d = &lk_t_door[id]; unsigned a = m68k.cycles, za = Z80.cycles;\n    lk_clk_depth--; lk_clk_pull();   /* LK_TIMESTATE v1: what GPGX changed inside the door goes back into our struct */\n", 1),
 # interrupt entry
 ("static void bus_irq_rebased(int level) {\n    static int off = -1;\n    s_irq_level = level; s_irq_diff = m68k.cycles - mcycles_vdp; s_irq_rebased = 0;\n",
  "static void bus_irq_rebased(int level) {\n    static int off = -1;\n    lk_clk_ensure(); lk_clk_push();   /* LK_TIMESTATE v1: the interrupt acknowledge (vdp_68k_irq_ack) and the handler read the GPGX globals */\n    s_irq_level = level; s_irq_diff = m68k.cycles - lk_clk.base; s_irq_rebased = 0;\n", 1),
 ("        unsigned int start = mcycles_vdp + 64;\n        s_irq_rebased = 1;\n        m68k.cycles = start;\n        recomp_m68k_interrupt(level);\n        m68k.cycles = real + (m68k.cycles - start);\n    } else {\n        recomp_m68k_interrupt(level);\n    }\n}",
  "        unsigned int start = lk_clk.base + 64;\n        s_irq_rebased = 1;\n        m68k.cycles = start; lk_clk.cyc = start;\n        recomp_m68k_interrupt(level);\n        m68k.cycles = real + (m68k.cycles - start);\n    } else {\n        recomp_m68k_interrupt(level);\n    }\n    lk_clk_pull();   /* LK_TIMESTATE v1: the acknowledge cleared hint_pending / vint_pending / status 0x80 */\n}", 1),
 # bus_advance wrapper + inner
 ("    bus_advance_inner(mc);\n    s_expected_cycles = m68k.cycles;\n",
  "    bus_advance_inner(mc);\n    s_expected_cycles = m68k.cycles; lk_clk.cyc = m68k.cycles;\n", 1),
 ("static void bus_advance_inner(unsigned int mc) {\n    lk_guard_check(\"tick start\");\n",
  "static void bus_advance_inner(unsigned int mc) {\n    lk_guard_check(\"tick start\");\n    lk_clk_ensure(); if (!lk_clk_own) lk_clk_pull();   /* LK_TIMESTATE v1 rollback (LANDSTALKER_TIMING=gpgx): the GPGX globals are the master */\n", 1),
 ("    if (m68k.cycles < mcycles_vdp) {\n        static int s_warned = 0;", "    if (m68k.cycles < lk_clk.base) {\n        static int s_warned = 0;", 1),
 ("        m68k.cycles = mcycles_vdp;\n    }\n    m68k.cycles += mc;\n    s_expected_cycles = m68k.cycles;   /* LK_TIMEDOORS v1: the block charge is ours, nested advances must not see it as stolen */\n",
  "        m68k.cycles = lk_clk.base;\n    }\n    m68k.cycles += mc;\n    s_expected_cycles = m68k.cycles;   /* LK_TIMEDOORS v1: the block charge is ours, nested advances must not see it as stolen */\n    lk_clk.cyc = m68k.cycles;\n", 1),
 ("    status &= ~0x0002;\n", "    status &= ~0x0002; lk_clk.status &= ~0x0002u;   /* LK_TIMESTATE v1 */\n", 1),
 # the line loop: the struct is the master
 ("    while ((m68k.cycles - mcycles_vdp) >= MCYCLES_PER_LINE) {\n        mcycles_vdp += MCYCLES_PER_LINE;\n        v_counter++;\n",
  "    while ((m68k.cycles - lk_clk.base) >= MCYCLES_PER_LINE) {\n        if (lk_clk_shadow) lk_clk_check(\"line step\");   /* LK_TIMESTATE v1 */\n        lk_clk.base += MCYCLES_PER_LINE;\n        lk_clk.line++;\n", 1),
 ("        bool vblank_now = (v_counter == vblank_line);\n        if (vblank_now) {\n            status |= 0x08;\n            Z80.irq_state = ASSERT_LINE;\n        }\n",
  "        bool vblank_now = ((int)lk_clk.line == vblank_line);\n        if (vblank_now) {\n            lk_clk.status |= 0x08;\n            lk_clk.zirq = ASSERT_LINE;\n        }\n        lk_clk_push();   /* the Z80 run, the VBlank callback, sound_update and the trace read the GPGX globals */\n", 1),
 ("z80_run(mcycles_vdp);   /* LK_TIMEDOORS v1 */\n", "z80_run(lk_clk.base); lk_clk_pull();   /* LK_TIMEDOORS v1 */\n", 1),
 ("        else Z80.cycles = mcycles_vdp;\n        Z80.irq_state = CLEAR_LINE;\n\n        if (vblank_now && s_vblank_cb) { s_since_vb = 0; s_vblank_cb(); }\n",
  "        else Z80.cycles = lk_clk.base;\n        lk_clk.zirq = CLEAR_LINE; Z80.irq_state = CLEAR_LINE;\n\n        if (vblank_now && s_vblank_cb) { s_since_vb = 0; s_vblank_cb(); lk_clk_pull(); }\n", 1),
 ("        if (v_counter >= lines_per_frame) {\n            if (lk_tt_active) lk_tt_ev('E', 4, m68k.cycles, mcycles_vdp, lines_per_frame, Z80.cycles, 0);\n",
  "        if (lk_clk.line >= lk_clk.lpf) {\n            if (lk_tt_active) lk_tt_ev('E', 4, m68k.cycles, lk_clk.base, lk_clk.lpf, Z80.cycles, 0);\n", 1),
 ("            v_counter = 0;\n            status &= ~0x08;\n", "            lk_clk.line = 0; lk_clk.status &= ~0x08u; lk_clk_push();\n", 1),
 ("            input_end_frame(mcycles_vdp);\n            m68k.cycles -= mcycles_vdp;\n", "            input_end_frame(lk_clk.base);\n            m68k.cycles -= lk_clk.base;\n", 1),
 ("                Z80.cycles -= mcycles_vdp;\n                { extern void lk_nat_frame(unsigned); lk_nat_frame(mcycles_vdp); }   /* LK_SNDNATIVE v1 */\n            }\n            mcycles_vdp = 0;\n            lk_snd_decide();\n            dma_endCycles = 0;\n            fifo_cycles[0] = fifo_cycles[1] = fifo_cycles[2] = fifo_cycles[3] = 0;\n        }\n",
  "                Z80.cycles -= lk_clk.base;\n                { extern void lk_nat_frame(unsigned); lk_nat_frame(lk_clk.base); }   /* LK_SNDNATIVE v1 */\n            }\n            lk_clk.base = 0; lk_clk.cyc = m68k.cycles; lk_clk_push();\n            lk_snd_decide();\n            lk_clk.dma_end = 0; lk_clk.fifo[0] = lk_clk.fifo[1] = lk_clk.fifo[2] = lk_clk.fifo[3] = 0; lk_clk_push();\n        }\n", 1),
 ("        if (v_counter == 0) { if (reg[1] & 0x04) {", "        if (lk_clk.line == 0) { if (reg[1] & 0x04) {", 1),
 ("            if (v_counter == ah) {\n                /* first VBlank line: an H-Int may still be pending */\n                if (h_counter == 0) {\n                    hint_pending = 0x10;\n                    if (reg[0] & 0x10) bus_irq_rebased(4);\n                }\n            } else if (v_counter == 0) {\n                h_counter = reg[10];\n                if (reg[1] & 0x40) parse_satb(-1);\n            }\n            if (v_counter < ah) {\n                if ((reg[1] & 0x44) && bitmap.viewport.w > 0 && bitmap.viewport.w <= 320 + 2 * lk_wide_e)\n                    render_line(v_counter);\n                if (h_counter == 0) {\n                    h_counter = reg[10];\n                    hint_pending = 0x10;\n                    if (reg[0] & 0x10) bus_irq_rebased(4);\n                } else {\n                    h_counter--;\n                }\n            }\n",
  "            if ((int)lk_clk.line == ah) {\n                /* first VBlank line: an H-Int may still be pending */\n                if (lk_clk.hcount == 0) {\n                    lk_clk.hint = 0x10;\n                    if (reg[0] & 0x10) bus_irq_rebased(4);   /* pushes the struct first, reads it back after */\n                    else lk_clk_push();\n                }\n            } else if (lk_clk.line == 0) {\n                lk_clk.hcount = reg[10]; lk_clk_push();\n                if (reg[1] & 0x40) parse_satb(-1);\n            }\n            if ((int)lk_clk.line < ah) {\n                if ((reg[1] & 0x44) && bitmap.viewport.w > 0 && bitmap.viewport.w <= 320 + 2 * lk_wide_e)\n                    render_line(lk_clk.line);\n                if (lk_clk.hcount == 0) {\n                    lk_clk.hcount = reg[10];\n                    lk_clk.hint = 0x10;\n                    if (reg[0] & 0x10) bus_irq_rebased(4);\n                    else lk_clk_push();\n                } else {\n                    lk_clk.hcount--; lk_clk_push();\n                }\n            }\n", 1),
 # DMA finish: GPGX changes dma_endCycles / status / m68k.cycles inside
 ("static void bus_finish_dma(void) {\n    int pre_ok = s_dma_pre_valid;", "static void bus_finish_dma_gpgx(void);\nstatic void bus_finish_dma(void) { bus_finish_dma_gpgx(); lk_clk_pull(); }   /* LK_TIMESTATE v1 */\nstatic void bus_finish_dma_gpgx(void) {\n    int pre_ok = s_dma_pre_valid;", 1),
 ("        m68k_run(m68k.cycles + 1);             /* exactly one instruction */\n", "        m68k_run(m68k.cycles + 1); lk_clk_pull();   /* exactly one instruction (LK_TIMESTATE v1: GPGX's CPU moved the clock) */\n", 1),
])
edit(os.path.join(ROOT, "src/func_table.c"), [
 ("lk_qs_slot0 = bus_read8(0xFF0010u); lk_qs_loading = 1;",
  "lk_qs_slot0 = bus_read8(0xFF0010u); lk_qs_loading = 1; { extern void lk_clk_resync(const char *); lk_clk_resync(\"quick load\"); }   /* LK_TIMESTATE v1 */", 1),
])
