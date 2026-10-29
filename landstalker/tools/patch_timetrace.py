#!/usr/bin/env python3
"""Timing model, step T0 (2026-10-29, docs/TIMING_PLAN.md): the GOLDEN TIME TRACE.
LANDSTALKER_TIMETRACE=file writes one text line per time relevant event the running game produces; with the variable unset every hook is one
test of a global flag (lk_tt_active) and nothing else: no behaviour change.  The hooks only READ the clock (m68k.cycles, mcycles_vdp, v_counter), never move it,
so RAM dumps and the audio capture are identical with the trace on or off (tools/timebench.sh checks that).
Line format (all numbers decimal, clock values in master clocks = 7 per 68K cycle):
    <frame> <line> <cyc> <kind> <args...> [x<count>@<last cyc>]
  frame = platform frame number, line = v_counter, cyc = m68k.cycles - mcycles_vdp at the event (can exceed 3420: the 68K runs ahead of the line loop)
  S status read ($C00004)           value (VDP status word before the open bus bits)           [vdp_68k_ctrl_r, 68K side]
  H HV counter reads ($C00008)      GROUP per frame (written before the E line): count, first value, last value, hash of (line, cyc, value) of all reads (value = V<<8 | H); line / cyc = the first read
  D VDP DMA chunk (GPGX)            type (0 68K>VRAM word, 1 68K>VRAM, 2 fill, 3 copy), bytes, remaining length before, cycles of the chunk, 68K stall mclk, arg cycles
  W our DMA finish (bus_finish_dma) type, length run by us (0 = ran inside the register write), final 68K stall mclk, GPGX's first stall mclk
  F FIFO stall                      mclk the data port write moved the 68K clock
  A 68K access to the Z80 area      0 read / 1 write (+7 mclk latency each; identical neighbours collapsed)
  B Z80 bus request write           data (1 = request), zstate before
  R Z80 reset write                 data (1 = released), zstate before
  Z Z80 accesses to the 68K bus     GROUP per frame (written before the E line): count, sum of mclk added to the 68K clock, sum of Z80 mclk spent (incl. DMA wait + 3 wait states), hash of (line, cyc, delta, z80 delta); line / cyc = the first access
  G pad read (gamepad_read)         port, TH step before the latency test, 1 = TH latency active (cycles < Latency)
  I interrupt taken                 level, interrupted pc (g_m68k.pc), SR mask before
  q interrupt deferred (masked)     level, SR mask
  J clock jumped by someone else    (ONLY with LANDSTALKER_TIMETRACE_J=1, diagnostics: it doubles the A / Z lines)  mclk, last bus address, innermost function (CYCSTAT's 'clock jumps behind our back')
  E frame end                       m68k.cycles, mcycles_vdp, lines_per_frame, Z80.cycles (just before the rebase)
Runs of the same kind with identical arguments on the same line are collapsed into one line (x<count>@<cyc of the last one>), so wait loops do not explode the file.
First line of the file: '# LK_TIMETRACE v1'.  Deterministic: two runs of the same replay give byte identical files.
Idempotent.  usage: patch_timetrace.py path/to/genrecomp   (last of the patches that touch bus.c / the GPGX core)"""
import os, re, sys
ROOT = sys.argv[1]
CORE = os.path.join(ROOT, "ext/Genesis-Plus-GX/core")
VER = "LK_TIMETRACE v1"

def tt(kind, n, *a):
    args = ", ".join(str(x) for x in a)
    full = args + ", 0" * (5 - len(a)) if a else "0, 0, 0, 0, 0"
    return "{ extern int lk_tt_active; extern void lk_tt_ev(int, int, unsigned, unsigned, unsigned, unsigned, unsigned); if (lk_tt_active) lk_tt_ev('%s', %d, %s); } /* %s */" % (kind, n, full, VER)

def edit(path, edits):
    t = open(path).read()
    if VER in t:
        print(os.path.basename(path), "already patched:", VER); return
    for old, new, cnt in edits:
        assert t.count(old) == cnt, (path, old[:60], t.count(old))
        t = t.replace(old, new)
    open(path, "w").write(t); print(os.path.basename(path), "patched:", VER)

# ---------------------------------------------------------------- bus.c: the writer + hooks
HELPER = r'''
/* ---- LK_TIMETRACE v1 (tools/patch_timetrace.py, docs/TIMING_PLAN.md T0) ---- */
int lk_tt_active, lk_tt_j;   /* lk_tt_j: also write the J lines (LANDSTALKER_TIMETRACE_J=1) */
static FILE *lk_tt_f;
static struct { int on, kind, n; long frame; int line, cyc; unsigned a, b, c, d, e; unsigned count; int lastcyc; } lk_tt_p;
static void lk_tt_close(void);
static struct { int on; long frame; int line, cyc; unsigned count, first, last, s1, s2, hash; } lk_tt_acc[2];   /* 0 = H, 1 = Z: one group line per frame, written before the frame end line */
static void lk_tt_accflush(void) {
    int i;
    for (i = 0; i < 2; i++) if (lk_tt_acc[i].on) {
        if (i == 0) fprintf(lk_tt_f, "%ld %d %d H %u %u %u %u\n", lk_tt_acc[i].frame, lk_tt_acc[i].line, lk_tt_acc[i].cyc, lk_tt_acc[i].count, lk_tt_acc[i].first, lk_tt_acc[i].last, lk_tt_acc[i].hash);
        else fprintf(lk_tt_f, "%ld %d %d Z %u %u %u %u\n", lk_tt_acc[i].frame, lk_tt_acc[i].line, lk_tt_acc[i].cyc, lk_tt_acc[i].count, lk_tt_acc[i].s1, lk_tt_acc[i].s2, lk_tt_acc[i].hash);
        lk_tt_acc[i].on = 0;
    }
}
static void lk_tt_flush(void) {
    if (!lk_tt_p.on) return;
    fprintf(lk_tt_f, "%ld %d %d %c", lk_tt_p.frame, lk_tt_p.line, lk_tt_p.cyc, lk_tt_p.kind);
    if (lk_tt_p.n > 0) fprintf(lk_tt_f, " %u", lk_tt_p.a);
    if (lk_tt_p.n > 1) fprintf(lk_tt_f, " %u", lk_tt_p.b);
    if (lk_tt_p.n > 2) fprintf(lk_tt_f, " %u", lk_tt_p.c);
    if (lk_tt_p.n > 3) fprintf(lk_tt_f, " %u", lk_tt_p.d);
    if (lk_tt_p.n > 4) fprintf(lk_tt_f, " %u", lk_tt_p.e);
    if (lk_tt_p.count > 1) fprintf(lk_tt_f, " x%u@%d", lk_tt_p.count, lk_tt_p.lastcyc);
    fputc('\n', lk_tt_f);
    lk_tt_p.on = 0;
}
static void lk_tt_close(void) { lk_tt_flush(); lk_tt_accflush(); if (lk_tt_f) fflush(lk_tt_f); }
__attribute__((constructor)) static void lk_tt_init(void) {
    const char *e = getenv("LANDSTALKER_TIMETRACE");
    if (e && *e && (lk_tt_f = fopen(e, "w"))) {
        static char buf[1 << 20]; setvbuf(lk_tt_f, buf, _IOFBF, sizeof buf);
        fputs("# LK_TIMETRACE v1\n", lk_tt_f); lk_tt_active = 1; atexit(lk_tt_close); { const char *j = getenv("LANDSTALKER_TIMETRACE_J"); lk_tt_j = j && *j == '1'; }
    }
}
static void lk_tt_accflush_pre(void) { lk_tt_flush(); lk_tt_accflush(); }
static unsigned lk_tt_h(unsigned h, unsigned v) { return (h ^ v) * 16777619u; }
void lk_tt_ev(int kind, int n, unsigned a, unsigned b, unsigned c, unsigned d, unsigned e) {
    long fr = platform_frame_number(); int line = (int)v_counter; int cyc = (int)(m68k.cycles - mcycles_vdp);
    if (!lk_tt_f) return;
    if (kind == 'H' || kind == 'Z') {   /* very frequent (HV counter polls, Z80 bank reads): one GROUP line per frame (count, sums / first + last, hash over every event) */
        int i = kind == 'Z';
        if (lk_tt_acc[i].on && lk_tt_acc[i].frame != fr) lk_tt_accflush();
        if (!lk_tt_acc[i].on) { memset(&lk_tt_acc[i], 0, sizeof lk_tt_acc[i]); lk_tt_acc[i].on = 1; lk_tt_acc[i].frame = fr; lk_tt_acc[i].line = line; lk_tt_acc[i].cyc = cyc; lk_tt_acc[i].first = a; lk_tt_acc[i].hash = 2166136261u; }
        lk_tt_acc[i].count++; lk_tt_acc[i].last = a; lk_tt_acc[i].s1 += a; lk_tt_acc[i].s2 += b;
        lk_tt_acc[i].hash = lk_tt_h(lk_tt_h(lk_tt_h(lk_tt_h(lk_tt_acc[i].hash, (unsigned)line), (unsigned)cyc), a), b);
        return;
    }
    if (kind == 'E') lk_tt_accflush_pre();
    if (lk_tt_p.on && lk_tt_p.kind == kind && lk_tt_p.frame == fr && lk_tt_p.line == line && lk_tt_p.n == n &&
        lk_tt_p.a == a && lk_tt_p.b == b && lk_tt_p.c == c && lk_tt_p.d == d && lk_tt_p.e == e && (kind == 'S' || kind == 'G' || kind == 'A')) {
        lk_tt_p.count++; lk_tt_p.lastcyc = cyc; return;
    }
    lk_tt_flush();
    lk_tt_p.on = 1; lk_tt_p.kind = kind; lk_tt_p.n = n; lk_tt_p.frame = fr; lk_tt_p.line = line; lk_tt_p.cyc = cyc;
    lk_tt_p.a = a; lk_tt_p.b = b; lk_tt_p.c = c; lk_tt_p.d = d; lk_tt_p.e = e; lk_tt_p.count = 1; lk_tt_p.lastcyc = cyc;
}
/* the two VDP port reads of the 68K go through here (mem68k.c): same call as before, plus a log line */
unsigned int lk_tt_sr(unsigned int cycles) { unsigned int v = vdp_68k_ctrl_r(cycles); if (lk_tt_active) lk_tt_ev('S', 1, v, 0, 0, 0, 0); return v; }
unsigned int lk_tt_hv(unsigned int cycles) { unsigned int v = vdp_hvc_r(cycles); if (lk_tt_active) lk_tt_ev('H', 1, v, 0, 0, 0, 0); return v; }
/* ---- end LK_TIMETRACE ---- */
'''
p = os.path.join(ROOT, "src/bus.c")
edit(p, [
 ("static uint32_t s_last_addr;  /* previous access, for the warning below */\n",
  "static uint32_t s_last_addr;  /* previous access, for the warning below */\n" + HELPER, 1),
 ("        if (d > s_max_jump) { s_max_jump = d; s_max_jump_addr = s_last_addr; }\n",
  "        if (d > s_max_jump) { s_max_jump = d; s_max_jump_addr = s_last_addr; }\n        if (lk_tt_active && lk_tt_j) { extern uint32_t func_table_stack(int); lk_tt_ev('J', 3, d, s_last_addr, func_table_stack(0), 0, 0); }\n", 1),
 ("        if (v_counter >= lines_per_frame) {\n",
  "        if (v_counter >= lines_per_frame) {\n            if (lk_tt_active) lk_tt_ev('E', 4, m68k.cycles, mcycles_vdp, lines_per_frame, Z80.cycles, 0);\n", 1),
 ("            m68k.cycles = s_dma_pre + st;\n        }\n        return;",
  "            m68k.cycles = s_dma_pre + st;\n            if (lk_tt_active) lk_tt_ev('W', 4, dma_type, 0, st, j0, 0);\n        }\n        return;", 1),
 ("        m68k.cycles = s_dma_pre + stall;\n    }\n}",
  "        m68k.cycles = s_dma_pre + stall;\n        if (lk_tt_active) lk_tt_ev('W', 4, dma_type0, dma_len0, stall, j0, 0);\n    }\n}", 1),
])

# ---------------------------------------------------------------- m68k.c: interrupts
edit(os.path.join(ROOT, "src/m68k.c"), [
 ("        if (level > g_m68k_irq_pending) g_m68k_irq_pending = level;\n        return;",
  "        if (level > g_m68k_irq_pending) g_m68k_irq_pending = level;\n        " + tt('q', 2, "level", "g_m68k.int_mask") + "\n        return;", 1),
 ("    if (g_m68k_irq_pending <= level) g_m68k_irq_pending = 0;\n",
  "    if (g_m68k_irq_pending <= level) g_m68k_irq_pending = 0;\n    " + tt('I', 3, "level", "g_m68k.pc", "g_m68k.int_mask") + "\n", 1),
])

# ---------------------------------------------------------------- GPGX core
d = lambda f: os.path.join(CORE, f)
edit(d("mem68k.c"), [
 ("vdp_68k_ctrl_r(m68k.cycles)", "lk_tt_sr(m68k.cycles)", 3),
 ("vdp_hvc_r(m68k.cycles)", "lk_tt_hv(m68k.cycles)", 3),
 ("unsigned int z80_read_byte(unsigned int address)\n{\n  /* Z80 bus access latency */\n  m68k.cycles += 1 * 7;\n",
  "unsigned int z80_read_byte(unsigned int address)\n{\n  /* Z80 bus access latency */\n  m68k.cycles += 1 * 7;\n  " + tt('A', 1, 0) + "\n", 1),
 ("void z80_write_byte(unsigned int address, unsigned int data)\n{\n  /* Z80 bus access latency (fixes Pacman 2: New Adventures sound engine crashes & Puyo Puyo 2 crash when exiting option menu) */\n  m68k.cycles += 1 * 7;\n",
  "void z80_write_byte(unsigned int address, unsigned int data)\n{\n  /* Z80 bus access latency (fixes Pacman 2: New Adventures sound engine crashes & Puyo Puyo 2 crash when exiting option menu) */\n  m68k.cycles += 1 * 7;\n  " + tt('A', 1, 1) + "\n", 1),
])
# lk_tt_sr / lk_tt_hv need a declaration before their first use in mem68k.c
t = open(d("mem68k.c")).read()
if "unsigned int lk_tt_sr(unsigned int);" not in t:
    inc = list(re.finditer(r'^#include .*\n', t, re.M))[-1]
    t = t[:inc.end()] + "unsigned int lk_tt_sr(unsigned int), lk_tt_hv(unsigned int);   /* LK_TIMETRACE v1 */\n" + t[inc.end():]
    open(d("mem68k.c"), "w").write(t)

edit(d("vdp_ctrl.c"), [
 ("  dma_endCycles = cycles + dma_cycles;\n",
  "  dma_endCycles = cycles + dma_cycles;\n  " + tt('D', 5, "dma_type", "dma_bytes", "dma_length", "dma_cycles", "((dma_type < 2 && dma_endCycles > m68k.cycles) ? dma_endCycles - m68k.cycles : 0)") + "\n", 1),
 ("        m68k.cycles = (((fifo_cycles[fifo_idx] + 6) / 7) * 7);\n",
  "        m68k.cycles = (((fifo_cycles[fifo_idx] + 6) / 7) * 7);\n        " + tt('F', 1, "(m68k.cycles - (unsigned)cycles)") + "\n", 2),
])
edit(d("genesis.c"), [
 ("void gen_zbusreq_w(unsigned int data, unsigned int cycles)\n{\n",
  "void gen_zbusreq_w(unsigned int data, unsigned int cycles)\n{\n  " + tt('B', 2, "data", "zstate") + "\n", 1),
 ("void gen_zreset_w(unsigned int data, unsigned int cycles)\n{\n",
  "void gen_zreset_w(unsigned int data, unsigned int cycles)\n{\n  " + tt('R', 2, "data", "zstate") + "\n", 1),
])
edit(d("memz80.c"), [
 ("static void z80_request_68k_bus_access(void)\n{\n",
  "static void z80_request_68k_bus_access(void)\n{\n  unsigned int lk_tt_m0 = m68k.cycles, lk_tt_z0 = Z80.cycles;   /* LK_TIMETRACE v1 */\n", 1),
 ("  Z80.cycles += (3 * 15);\n}",
  "  Z80.cycles += (3 * 15);\n  " + tt('Z', 2, "(m68k.cycles - lk_tt_m0)", "(Z80.cycles - lk_tt_z0)") + "\n}", 1),
])
edit(d("input_hw/gamepad.c"), [
 ("  /* TH direction switching latency */\n  if (cycles < gamepad[port].Latency)\n  {\n    /* TH internal state switching has not occured yet (Decap Attack) */\n    step &= ~1;",
  "  " + tt('G', 3, "port", "step", "(cycles < gamepad[port].Latency)") + "\n  /* TH direction switching latency */\n  if (cycles < gamepad[port].Latency)\n  {\n    /* TH internal state switching has not occured yet (Decap Attack) */\n    step &= ~1;", 1),
])
