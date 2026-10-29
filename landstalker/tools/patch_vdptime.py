#!/usr/bin/env python3
"""Timing model, step T3 (2026-10-30, docs/TIMING_PLAN.md): the VDP PORT TIMING is ours.  No behaviour change (bit identical to GPGX's results).
What bus.c now computes itself (block LK_VDPTIME, functions lk_v_*), from our clock state lk_clk (T2) and our own tables:
  - the status read ($C00004, door lk_t_status_r): DMA busy clear, FIFO empty / full, VBlank (display off), the cycle exact VINT and HBLANK flags;
  - the HV counter read ($C00008, door lk_t_hvc_r): H counter tables H32 / H40 written down fresh (lk_v_hc, run lengths below), V counter wrap;
  - the DMA timing (vdp_dma_update: rate, cycles to the end of the line / VBlank, bytes per chunk, DMA end = the 68K halt of a 68K bus DMA;
    the final DMA stall stays the patch_timing formula of bus_finish_dma, which only rescales this first chunk);
  - the FIFO stall of a data port write ($C00000, door lk_t_fifo_w, mode 5 writer): FIFO full -> 68K waits, next FIFO slot.
GPGX keeps the register / data path (what a write DOES to VRAM / CRAM / registers, the DMA copy itself, pending flag) and its own timing code stays
in the build for LANDSTALKER_TIMING=gpgx (rollback, as in T2) and for the shadow compare.
Hardware tables (written fresh, checked once at start against GPGX's tables; on any difference the VDP timing falls back to GPGX's code with a message):
  H counter H32: 20 master clocks per step, $00-$93 then $E9-$FF; H40: 16 per step, $00-$B6 then $E4-$FF, the HSYNC steps $B6 / $E4 short (8) and
  $E6-$F7 stretched (17 .. 20, the slower dot clock during HSYNC); phase: $85 (H32) / $A5 (H40) at the line start of the cycle model.
  FIFO access slots per line (H32 16, H40 18 slots + the next line), DMA bytes per line (active 16 / 18, blanking 166 / 204, 161 / 198 for CRAM /
  VSRAM when the display is off), VINT at 770 / 788, HBLANK flag 280..860 / 228..872 master clocks into the line.
Remaining GPGX inputs (VDP state, not timing): reg[], status register non-timing bits, dma_length / dma_type, hvc_latch, vc_max, interlaced, im2_flag,
fifo_idx / fifo_byte_access (static: read through lk_vdp_* getters added at the end of vdp_ctrl.c), m68k_cycles() (Musashi's last-opcode time added
to a status read; a GPGX quirk kept for bit identity, see TIMING_PLAN section 11).
Modes: default = ours decides and GPGX's timing code is not run; LANDSTALKER_TIMING=gpgx = GPGX's code (with T2's rollback);
LANDSTALKER_TIME_SHADOW=1|path = both computed, GPGX's result applied, every difference counted, the first 6 per kind printed with frame / line /
call stack, one summary line 'TIME_SHADOW VDP ...' at exit (also checks that our H32 / H40 mode equals GPGX's current tables).
Idempotent (marker below).  usage: patch_vdptime.py path/to/genrecomp   (after patch_timestate.py)"""
import os, sys
ROOT = sys.argv[1]
VER = "LK_VDPTIME v1"

def edit(path, edits, append=""):
    t = open(path).read()
    if VER in t:
        print(os.path.basename(path), "already patched:", VER); return
    for old, new, cnt in edits:
        assert t.count(old) == cnt, (path, old[:90], t.count(old))
        t = t.replace(old, new)
    t += append
    open(path, "w").write(t); print(os.path.basename(path), "patched:", VER)

# ---------------------------------------------------------------- vdp_ctrl.c (GPGX): hooks + getters for the static VDP state
VDP = os.path.join(ROOT, "ext/Genesis-Plus-GX/core/vdp_ctrl.c")
DECL = r'''/* LK_VDPTIME v1 (tools/patch_vdptime.py, docs/TIMING_PLAN.md T3): the VDP timing is computed in bus.c (lk_v_*); this code = LANDSTALKER_TIMING=gpgx + shadow */
extern int lk_v_own, lk_v_shadow;
extern int lk_v_dma_calc(unsigned int cycles, int type, int fill, unsigned int length, int *bytes, unsigned int *start);
extern void lk_v_dma_check(unsigned int in, int oc, int ob, unsigned int os, int gc, int gb, unsigned int gs);
extern void lk_v_dma_halt(unsigned int end);
void vdp_dma_update(unsigned int cycles)
{
'''
VDP_EDITS = [
    ("void vdp_dma_update(unsigned int cycles)\n{\n", DECL, 1),
    ("  unsigned int rate = dma_timing[(status & 8) || !(reg[1] & 0x40)][reg[12] & 1];",
     "  int lk_oc = 0, lk_ob = 0; unsigned int lk_os = 0, lk_in = cycles;   /* LK_VDPTIME v1: ours (lk_v_dma_calc) decides; GPGX's block below = rollback / shadow */\n"
     "  if (lk_v_own) lk_oc = lk_v_dma_calc(cycles, dma_type, dmafill, dma_length, &lk_ob, &lk_os);\n"
     "  if (lk_v_own && !lk_v_shadow) { dma_cycles = lk_oc; dma_bytes = lk_ob; cycles = lk_os; goto lk_v_dma_done; }\n"
     "  {\n"
     "  unsigned int rate = dma_timing[(status & 8) || !(reg[1] & 0x40)][reg[12] & 1];", 1),
    ("  /* Set DMA end cycle */\n  dma_endCycles = cycles + dma_cycles;",
     "  }\n"
     "  if (lk_v_own && lk_v_shadow) lk_v_dma_check(lk_in, lk_oc, lk_ob, lk_os, dma_cycles, dma_bytes, cycles);   /* LK_VDPTIME v1 */\n"
     "lk_v_dma_done:\n"
     "  /* Set DMA end cycle */\n  dma_endCycles = cycles + dma_cycles;", 1),
    ("    m68k.cycles = dma_endCycles;\n",
     "    if (lk_v_own) lk_v_dma_halt(dma_endCycles); else m68k.cycles = dma_endCycles;   /* LK_VDPTIME v1: the 68K halt is set by our code */\n", 1),
    ("static void vdp_68k_data_w_m5(unsigned int data)\n{\n  /* Clear pending flag */\n  pending = 0;\n\n  /* Restricted VDP writes during active display */\n  if (!(status & 8) && (reg[1] & 0x40))",
     "static void vdp_68k_data_w_m5(unsigned int data)\n{\n  /* Clear pending flag */\n  pending = 0;\n\n  /* Restricted VDP writes during active display */\n"
     "  if ((!lk_v_own || lk_v_shadow) && !(status & 8) && (reg[1] & 0x40))   /* LK_VDPTIME v1: own mode = the FIFO step ran in bus.c (lk_t_fifo_w) */", 1),
]
VDP_APPEND = r'''

/* ---- LK_VDPTIME v1: read access to the static VDP state for bus.c (lk_v_*); no behaviour ---- */
int lk_vdp_fifo_idx(void) { return fifo_idx; }
int lk_vdp_fifo_byte(void) { return fifo_byte_access; }
int lk_vdp_is_m5(void) { return vdp_68k_data_w == vdp_68k_data_w_m5; }
int lk_vdp_pending(void) { return pending; }
void lk_vdp_status_ack(void) { pending = 0; }   /* the register side effect of a status read (the status bits are written by bus.c) */
const uint8 *lk_vdp_hctab_gpgx(int h40) { return h40 ? cycle2hc40 : cycle2hc32; }
const uint8 *lk_vdp_hctab_cur(void) { return hctab; }
const int *lk_vdp_fifo_tab_gpgx(int h40, int *n) { *n = h40 ? (int)(sizeof fifo_timing_h40 / sizeof fifo_timing_h40[0]) : (int)(sizeof fifo_timing_h32 / sizeof fifo_timing_h32[0]); return h40 ? fifo_timing_h40 : fifo_timing_h32; }
const int *lk_vdp_fifo_tab_cur(void) { return fifo_timing; }
int lk_vdp_hblank_start(void) { return hblank_start_cycle; }
int lk_vdp_hblank_end(void) { return hblank_end_cycle; }
unsigned int lk_vdp_dma_timing(int blank, int h40) { return dma_timing[blank][h40]; }
/* ---- end LK_VDPTIME ---- */
'''

# ---------------------------------------------------------------- bus.c: our VDP timing
BUS = os.path.join(ROOT, "src/bus.c")
OLD_ST = "unsigned int lk_t_status_r(unsigned int cycles) { unsigned int v; lk_t_in(LK_T_STATUS); v = lk_tt_sr(cycles); lk_t_out(LK_T_STATUS); return v; }   /* G2 */\n"
OLD_HV = "unsigned int lk_t_hvc_r(unsigned int cycles)    { unsigned int v; lk_t_in(LK_T_HVC);    v = lk_tt_hv(cycles); lk_t_out(LK_T_HVC);    return v; }   /* G3 */\n"
OLD_FI = "void lk_t_fifo_w(unsigned int data)    { lk_t_in(LK_T_FIFO); vdp_68k_data_w(data); lk_t_out(LK_T_FIFO); }   /* G5 */\n"
V = r'''/* ---- LK_VDPTIME v1 (tools/patch_vdptime.py, docs/TIMING_PLAN.md T3): the VDP port timing is computed HERE from lk_clk + our own tables ---- */
#include <stdarg.h>
extern int m68k_cycles(void);
extern int lk_vdp_fifo_idx(void), lk_vdp_fifo_byte(void), lk_vdp_is_m5(void), lk_vdp_pending(void), lk_vdp_hblank_start(void), lk_vdp_hblank_end(void);
extern void lk_vdp_status_ack(void);
extern const uint8 *lk_vdp_hctab_gpgx(int h40), *lk_vdp_hctab_cur(void);
extern const int *lk_vdp_fifo_tab_gpgx(int h40, int *n), *lk_vdp_fifo_tab_cur(void);
extern unsigned int lk_vdp_dma_timing(int blank, int h40);
int lk_v_own = 1;     /* 1 = our VDP timing decides (default); LANDSTALKER_TIMING=gpgx or a table mismatch at start -> 0 = GPGX's code */
int lk_v_shadow;      /* LANDSTALKER_TIME_SHADOW: both computed, GPGX's result applied, differences counted */
static uint8 lk_v_hc[2][MCYCLES_PER_LINE];   /* H counter per master clock of the line: [0] H32, [1] H40 (built in lk_v_init) */
/* FIFO access slots (master clock in the line at which the VDP takes the next FIFO entry; second half = the next line) */
static const int lk_v_fifo_h32[] = { 230, 510, 810, 970, 1130, 1450, 1610, 1770, 2090, 2250, 2410, 2730, 2890, 3050, 3350, 3370,
    3420 + 230, 3420 + 510, 3420 + 810, 3420 + 970, 3420 + 1130, 3420 + 1450, 3420 + 1610, 3420 + 1770, 3420 + 2090, 3420 + 2250, 3420 + 2410, 3420 + 2730 };
static const int lk_v_fifo_h40[] = { 352, 820, 948, 1076, 1332, 1460, 1588, 1844, 1972, 2100, 2356, 2484, 2612, 2868, 2996, 3124, 3364, 3380,
    3420 + 352, 3420 + 820, 3420 + 948, 3420 + 1076, 3420 + 1332, 3420 + 1460, 3420 + 1588, 3420 + 1844, 3420 + 1972, 3420 + 2100, 3420 + 2356, 3420 + 2484 };
#define LK_V_NFIFO(h40) ((h40) ? (int)(sizeof lk_v_fifo_h40 / sizeof lk_v_fifo_h40[0]) : (int)(sizeof lk_v_fifo_h32 / sizeof lk_v_fifo_h32[0]))
static const unsigned int lk_v_dma_rate[2][2] = { { 16, 18 }, { 166, 204 } };   /* DMA bytes per line: [active / blanking][H32 / H40] */
#define LK_V_VINT(h40) ((h40) ? 788u : 770u)    /* VINT flag / interrupt point in the line */
#define LK_V_HBS(h40)  ((h40) ? 228u : 280u)    /* HBLANK flag set */
#define LK_V_HBE(h40)  ((h40) ? 872u : 860u)    /* HBLANK flag clear */
static inline int lk_v_h40(void) { return reg[12] & 1; }   /* RS1: the width register switches every table at once (GPGX vdp_reg_w r12) */
enum { LK_V_ST, LK_V_HV, LK_V_DMA, LK_V_FIFO, LK_V_MODE, LK_V_N };
static const char *const lk_v_kn[LK_V_N] = { "status", "hvc", "dma", "fifo", "mode" };
static unsigned long long lk_v_chk[LK_V_N], lk_v_bad[LK_V_N], lk_v_m4, lk_v_slot_over;
static void lk_v_bad_report(int k, const char *fmt, ...) {
    va_list ap; FILE *f;
    if (++lk_v_bad[k] > 6) return;
    f = lk_clk_open();
    fprintf(f, "TIME_SHADOW VDP MISMATCH %s #%llu: frame %ld line %u cyc-in-line %d: ", lk_v_kn[k], lk_v_bad[k], platform_frame_number(), lk_clk.line, (int)(m68k.cycles - lk_clk.base));
    va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
    fprintf(f, " stack:"); func_table_dump_stack(f); fprintf(f, "\n");
    if (f != stderr) fclose(f);
}
static void lk_v_mode_check(void) {   /* shadow: our H32 / H40 decision equals the tables GPGX switched to */
    int h40 = lk_v_h40(), n; lk_v_chk[LK_V_MODE]++;
    if (lk_vdp_hctab_cur() != lk_vdp_hctab_gpgx(h40) || lk_vdp_fifo_tab_cur() != lk_vdp_fifo_tab_gpgx(h40, &n) || vint_cycle != LK_V_VINT(h40) ||
        (unsigned)lk_vdp_hblank_start() != LK_V_HBS(h40) || (unsigned)lk_vdp_hblank_end() != LK_V_HBE(h40))
        lk_v_bad_report(LK_V_MODE, "reg12=%02X ours h40=%d, GPGX tables differ (vint_cycle %u hblank %d..%d)", reg[12], h40, (unsigned)vint_cycle, lk_vdp_hblank_start(), lk_vdp_hblank_end());
}
static void lk_v_dump(void) {
    FILE *f = lk_clk_open(); int k;
    fprintf(f, "TIME_SHADOW VDP own=%d", lk_v_own);
    for (k = 0; k < LK_V_N; k++) fprintf(f, " %s=%llu/%llu", lk_v_kn[k], lk_v_chk[k], lk_v_bad[k]);
    fprintf(f, " m4_writes=%llu slot_overrun=%llu (checks/mismatches)\n", lk_v_m4, lk_v_slot_over);
    if (f != stderr) fclose(f);
}
__attribute__((constructor)) static void lk_v_init(void) {
    static const struct { uint8 v, len; } stretch[] = {   /* H40 steps that are not 16 master clocks long (HSYNC) */
        { 0xB6, 8 }, { 0xE4, 8 }, { 0xE6, 17 }, { 0xE7, 20 }, { 0xE8, 20 }, { 0xE9, 20 }, { 0xEA, 18 }, { 0xEB, 20 }, { 0xEC, 20 }, { 0xED, 20 },
        { 0xEE, 19 }, { 0xEF, 19 }, { 0xF0, 20 }, { 0xF1, 20 }, { 0xF2, 20 }, { 0xF3, 18 }, { 0xF4, 20 }, { 0xF5, 20 }, { 0xF6, 20 }, { 0xF7, 17 } };
    const char *t = getenv("LANDSTALKER_TIMING"), *s = getenv("LANDSTALKER_TIME_SHADOW");
    int c, i, n, bad = 0; unsigned v;
    for (c = 0; c < MCYCLES_PER_LINE; c++) { int st = c / 20; lk_v_hc[0][c] = (uint8)(st < 15 ? 0x85 + st : st < 38 ? 0xE9 + (st - 15) : st - 38); }
    for (c = 0, v = 0xA5; c < MCYCLES_PER_LINE; v = (v == 0xB6) ? 0xE4 : ((v + 1) & 0xFF)) {
        int len = 16;
        for (i = 0; i < (int)(sizeof stretch / sizeof stretch[0]); i++) if (stretch[i].v == v) len = stretch[i].len;
        for (n = 0; n < len && c < MCYCLES_PER_LINE; n++) lk_v_hc[1][c++] = (uint8)v;
    }
    for (i = 0; i < 2; i++) {   /* our tables against GPGX's (once) */
        const uint8 *g = lk_vdp_hctab_gpgx(i); const int *gf = lk_vdp_fifo_tab_gpgx(i, &n); const int *of = i ? lk_v_fifo_h40 : lk_v_fifo_h32;
        for (c = 0; c < MCYCLES_PER_LINE; c++) if (lk_v_hc[i][c] != g[c]) { if (!bad) fprintf(stderr, "LK_VDPTIME: H counter %s differs at mclk %d: ours %02X GPGX %02X\n", i ? "H40" : "H32", c, lk_v_hc[i][c], g[c]); bad++; }
        if (n != LK_V_NFIFO(i)) bad++; else for (c = 0; c < n; c++) if (of[c] != gf[c]) bad++;
        if (lk_v_dma_rate[0][i] != lk_vdp_dma_timing(0, i) || lk_v_dma_rate[1][i] != lk_vdp_dma_timing(1, i)) bad++;
    }
    if (t && !strcmp(t, "gpgx")) lk_v_own = 0;
    if (bad) { lk_v_own = 0; fprintf(stderr, "LK_VDPTIME: %d difference(s) between our VDP timing tables and GPGX's: the VDP timing falls back to GPGX's code\n", bad); }
    if (lk_v_own && s && *s && strcmp(s, "0")) { lk_v_shadow = 1; atexit(lk_v_dump); }
}

/* status read ($C00004): value + the new status register, no side effects (GPGX vdp_68k_ctrl_r, same C types so the same wraps) */
static unsigned int lk_v_status_calc(unsigned int cycles, unsigned int *st_out) {
    unsigned int temp, st = (status & ~LK_CLK_BITS) | (lk_clk.status & LK_CLK_BITS);   /* non-timing bits (SOVR, SCOL, odd frame, PAL) = GPGX's register */
    int h40 = lk_v_h40(), idx = lk_vdp_fifo_idx();
    cycles += m68k_cycles();   /* GPGX: 'cycle-accurate' read adds Musashi's time of its last opcode (kept for bit identity) */
    if (st & 2) { if (!dma_length && (cycles >= lk_clk.dma_end)) st &= 0xFFFD; }   /* DMA (fill / copy) finished */
    temp = st;
    st &= 0xFF9F;   /* a read clears SOVR / SCOL */
    if (cycles >= lk_clk.fifo[(idx + 3) & 3]) temp |= 0x200;   /* FIFO empty */
    else if (cycles < lk_clk.fifo[idx]) temp |= 0x100;          /* FIFO full */
    if (!(reg[1] & 0x40)) temp |= 0x08;                          /* display off reads as VBlank */
    cycles -= lk_clk.base;
    if ((lk_clk.line == (unsigned)bitmap.viewport.h) && (cycles >= LK_V_VINT(h40))) { if (lk_clk.zirq != ASSERT_LINE) temp |= 0x80; }   /* VINT flag just before the interrupt */
    if ((cycles >= LK_V_HBS(h40)) && (cycles < LK_V_HBE(h40))) temp |= 0x04;   /* HBLANK */
    *st_out = st & 0xFFFF;
    return temp;
}
/* HV counter read ($C00008) (GPGX vdp_hvc_r) */
static unsigned int lk_v_hvc_calc(unsigned int cycles) {
    int vc; unsigned int data = hvc_latch;
    if (data) { if (reg[1] & 0x04) return (data & 0xffff); data &= 0xff; }   /* latched (mode 5: both frozen; mode 4: H frozen) */
    else data = lk_v_hc[lk_v_h40()][cycles % MCYCLES_PER_LINE];
    vc = (int)lk_clk.line;
    if ((cycles - lk_clk.base) >= MCYCLES_PER_LINE) vc = (vc + 1) % (int)lk_clk.lpf;   /* already on the next line */
    if (vc > vc_max) vc -= (int)lk_clk.lpf;   /* V counter wraps ($EA -> $E5 on NTSC 224) */
    if (interlaced) { vc <<= im2_flag; vc = (vc & ~1) | ((vc >> 8) & 1); }
    return data | ((vc & 0xff) << 8);
}
/* DMA chunk timing (GPGX vdp_dma_update): returns the cycles of this chunk, *bytes = bytes done in it, *start = start cycle (DMA fill: after the first data write) */
int lk_v_dma_calc(unsigned int cycles, int type, int fill, unsigned int length, int *bytes, unsigned int *start) {
    int dma_cycles, dma_bytes, h40 = reg[12] & 1;
    unsigned int rate = lk_v_dma_rate[(lk_clk.status & 8) || !(reg[1] & 0x40)][h40];
    rate = rate >> (type & 1);   /* 68K -> VRAM: one word = 2 accesses; copy: read + write */
    if (type == 0) { if (rate == 166) rate = 161; else if (rate == 204) rate = 198; }   /* CRAM / VSRAM, display off: refresh slots */
    else if (fill) cycles += (2 * (MCYCLES_PER_LINE / rate));   /* fill starts after the data port write */
    if (lk_clk.status & 8) dma_cycles = (((int)lk_clk.lpf - bitmap.viewport.h - 1) * MCYCLES_PER_LINE) - cycles;   /* until the end of VBlank */
    else dma_cycles = (lk_clk.base + MCYCLES_PER_LINE) - cycles;   /* until the end of the line */
    dma_bytes = (dma_cycles * rate) / MCYCLES_PER_LINE;
    if (length < dma_bytes) { dma_bytes = length; dma_cycles = (dma_bytes * MCYCLES_PER_LINE) / rate; }   /* finishes in this chunk (unsigned compare as in GPGX) */
    *bytes = dma_bytes; *start = cycles;
    return dma_cycles;
}
void lk_v_dma_check(unsigned int in, int oc, int ob, unsigned int os, int gc, int gb, unsigned int gs) {
    lk_v_chk[LK_V_DMA]++; lk_v_mode_check();
    if (oc != gc || ob != gb || os != gs)
        lk_v_bad_report(LK_V_DMA, "start %u type %d len %u: cycles ours %d gpgx %d, bytes ours %d gpgx %d, start ours %u gpgx %u", in, (int)dma_type, (unsigned)dma_length, oc, gc, ob, gb, os, gs);
}
void lk_v_dma_halt(unsigned int end) { m68k.cycles = end; }   /* a 68K bus DMA halts the 68K until the chunk's end (bus_finish_dma then charges the whole DMA) */
/* FIFO step of a mode 5 data port write (GPGX vdp_68k_data_w_m5 head) */
typedef struct { int active, stalled, idx; unsigned int cyc, slot_cyc; } lk_v_fifo_t;
static void lk_v_fifo_calc(lk_v_fifo_t *r) {
    r->active = r->stalled = 0; r->idx = lk_vdp_fifo_idx(); r->cyc = m68k.cycles; r->slot_cyc = 0;
    if (!(lk_clk.status & 8) && (reg[1] & 0x40)) {   /* only during active display */
        int h40 = lk_v_h40(), n = LK_V_NFIFO(h40), slot = 0, idx = r->idx, fb = lk_vdp_fifo_byte();
        const int *ft = h40 ? lk_v_fifo_h40 : lk_v_fifo_h32;
        int cycles = m68k.cycles;
        r->active = 1;
        if (cycles < lk_clk.fifo[(idx + 3) & 3]) {   /* FIFO not empty */
            if (cycles < lk_clk.fifo[idx]) { r->cyc = (((lk_clk.fifo[idx] + 6) / 7) * 7); r->stalled = 1; }   /* FIFO full: the 68K waits for the oldest entry */
            cycles = lk_clk.fifo[(idx + 3) & 3];
        }
        cycles -= lk_clk.base;
        while (slot < n && cycles >= ft[slot]) slot++;
        if (slot + fb >= n) { lk_v_slot_over++; slot = n - 1 - fb; }   /* past the table (GPGX would read beyond it); counted, never seen */
        r->slot_cyc = lk_clk.base + ft[slot + fb];
    }
}
unsigned int lk_t_status_r(unsigned int cycles) {   /* G2 */
    unsigned int v, st; lk_t_in(LK_T_STATUS);
    if (!lk_v_own) v = lk_tt_sr(cycles);
    else if (!lk_v_shadow) {
        v = lk_v_status_calc(cycles, &st);
        status = (uint16)st; lk_clk.status = st & LK_CLK_BITS; lk_vdp_status_ack();
        if (lk_tt_active) lk_tt_ev('S', 1, v, 0, 0, 0, 0);
    } else {
        unsigned int ov = lk_v_status_calc(cycles, &st);
        v = lk_tt_sr(cycles); lk_v_chk[LK_V_ST]++; lk_v_mode_check();
        if (ov != v || st != status || lk_vdp_pending())
            lk_v_bad_report(LK_V_ST, "value ours %04X gpgx %04X, status after ours %04X gpgx %04X, pending %d", ov, v, st, (unsigned)status, lk_vdp_pending());
    }
    lk_t_out(LK_T_STATUS); return v;
}
unsigned int lk_t_hvc_r(unsigned int cycles) {   /* G3 */
    unsigned int v; lk_t_in(LK_T_HVC);
    if (!lk_v_own) v = lk_tt_hv(cycles);
    else if (!lk_v_shadow) { v = lk_v_hvc_calc(cycles); if (lk_tt_active) lk_tt_ev('H', 1, v, 0, 0, 0, 0); }
    else {
        unsigned int ov = lk_v_hvc_calc(cycles);
        v = lk_tt_hv(cycles); lk_v_chk[LK_V_HV]++;
        if (ov != v) lk_v_bad_report(LK_V_HV, "value ours %04X gpgx %04X (h40 %d)", ov, v, lk_v_h40());
    }
    lk_t_out(LK_T_HVC); return v;
}
void lk_t_fifo_w(unsigned int data) {   /* G5 */
    lk_v_fifo_t r; lk_t_in(LK_T_FIFO);
    if (lk_v_own && !lk_vdp_is_m5()) lk_v_m4++;   /* mode 4 writer: GPGX's own FIFO code (Landstalker runs in mode 5) */
    else if (lk_v_own && !lk_v_shadow) {
        lk_v_fifo_calc(&r);
        if (r.active) {
            if (r.stalled) { unsigned int c0 = m68k.cycles; m68k.cycles = r.cyc; if (lk_tt_active) lk_tt_ev('F', 1, (m68k.cycles - c0), 0, 0, 0, 0); }
            lk_clk.fifo[r.idx] = r.slot_cyc; fifo_cycles[r.idx] = r.slot_cyc;   /* both: lk_t_out pulls the globals back into the struct */
        }
    } else if (lk_v_own) {
        unsigned int f0[4]; int i; lk_v_fifo_calc(&r);
        for (i = 0; i < 4; i++) f0[i] = fifo_cycles[i];
        if (r.active) f0[r.idx] = r.slot_cyc;
        vdp_68k_data_w(data); lk_v_chk[LK_V_FIFO]++; lk_v_mode_check();
        if (m68k.cycles != r.cyc || f0[0] != fifo_cycles[0] || f0[1] != fifo_cycles[1] || f0[2] != fifo_cycles[2] || f0[3] != fifo_cycles[3])
            lk_v_bad_report(LK_V_FIFO, "idx %d active %d: 68K ours %u gpgx %u, slot ours %u gpgx %u", r.idx, r.active, r.cyc, m68k.cycles, r.slot_cyc, fifo_cycles[r.idx]);
        lk_t_out(LK_T_FIFO); return;
    }
    vdp_68k_data_w(data);
    lk_t_out(LK_T_FIFO);
}
/* ---- end LK_VDPTIME ---- */
'''
BUS_EDITS = [
    (OLD_ST + OLD_HV, V, 1),
    (OLD_FI, "", 1),
    ("    status |= 0x08;  /* blanking rate: largest chunk per call */\n",
     "    status |= 0x08;  /* blanking rate: largest chunk per call */\n    unsigned lk_v_sv = lk_clk.status; lk_clk.status |= 0x08u;   /* LK_VDPTIME v1: lk_v_dma_calc reads the struct */\n", 1),
    ("    status = (status & ~0x0A) | saved_vblank;\n",
     "    status = (status & ~0x0A) | saved_vblank;\n    lk_clk.status = lk_v_sv;   /* LK_VDPTIME v1 (the wrapper pulls the globals afterwards) */\n", 1),
]

edit(VDP, VDP_EDITS, VDP_APPEND)
edit(BUS, BUS_EDITS)
