#!/usr/bin/env python3
"""Timing model, step T1 (2026-10-29, docs/TIMING_PLAN.md): ONE DOOR PER GPGX TIME ACCESS.  No behaviour change.
Every place where GPGX code reads or moves the 68K clock on Landstalker's paths (TIMING_PLAN section 2, G2 .. G9) is called through a function of ours in bus.c.
Each door calls exactly what GPGX did before, notes the clock before / after (lk_t_door[id].before / .after, Z80 clock too) and counts calls and the clock it moved.
T2 / T3 will compute 'ours' next to the GPGX result inside these functions (shadow compare).  The T0 trace hooks (patch_timetrace.py) stay where they were: they run INSIDE the
door's call, so the trace output is byte identical.
  door id        function (bus.c)                      wraps                                                         call sites
  LK_T_STATUS    lk_t_status_r(cycles)                 lk_tt_sr -> vdp_68k_ctrl_r        VDP status ($C00004)           mem68k.c x6
  LK_T_HVC       lk_t_hvc_r(cycles)                    lk_tt_hv -> vdp_hvc_r             HV counter ($C00008)           mem68k.c x3
  LK_T_DMA       lk_t_dma_start(data)                  vdp_68k_ctrl_w                    VDP control write, DMA start   mem68k.c x2
  LK_T_FIFO      lk_t_fifo_w(data)                     vdp_68k_data_w                    VDP data write, FIFO stall     mem68k.c x2
  LK_T_ZAREA     lk_t_zarea(write)                     the '+7' of z80_read_byte / z80_write_byte (68K -> Z80 area)   mem68k.c x2
  LK_T_ZBUS      lk_t_zbus_w(data, cycles)             gen_zbusreq_w                     Z80 bus request ($A11100)      mem68k.c x2
  LK_T_ZRESET    lk_t_zreset_w(data, cycles)           gen_zreset_w                      Z80 reset ($A11200)            mem68k.c x2
  LK_T_ZWAIT     lk_t_zwait(fn)                        z80_request_68k_bus_access        Z80 reads the 68K bus: waits   memz80.c (wrapper of the static function)
  LK_T_PAD       lk_t_pad(port, step, cycles, latency) the TH latency test in gamepad_read                              gamepad.c x1
  LK_T_PADW      lk_t_pad_w(port, cycles)              the 'Latency = cycles + 172' of gamepad_write                    gamepad.c x1
Not wrapped (not used by Landstalker's driver): the Z80-side accesses of membnk.c (Z80 reading VDP ports / writing busreq through the bank window), Sega CD code.
LANDSTALKER_TIMEDOORS=1 prints the per door counters to stderr at exit, =path appends them to that file (one line per door, summable over runs):
  TIMEDOORS <name> calls=N moved_calls=N moved_mclk=N max_mclk=N z80_mclk=N
Also fixes the CYCSTAT 'RAM/ROM' mis-attribution (diagnostic only): bus_advance_inner sets s_expected_cycles right after the block charge.
Idempotent.  usage: patch_timedoors.py path/to/genrecomp   (after patch_timetrace.py)"""
import os, re, sys
ROOT = sys.argv[1]
CORE = os.path.join(ROOT, "ext/Genesis-Plus-GX/core")
VER = "LK_TIMEDOORS v1"

def edit(path, edits):
    t = open(path).read()
    if VER in t:
        print(os.path.basename(path), "already patched:", VER); return
    for old, new, cnt in edits:
        assert t.count(old) == cnt, (path, old[:70], t.count(old))
        t = t.replace(old, new)
    open(path, "w").write(t); print(os.path.basename(path), "patched:", VER)

DOORS = r'''
/* ---- LK_TIMEDOORS v1 (tools/patch_timedoors.py, docs/TIMING_PLAN.md T1): one door per GPGX access that reads or moves the 68K clock ---- */
enum { LK_T_STATUS, LK_T_HVC, LK_T_DMA, LK_T_FIFO, LK_T_ZAREA, LK_T_ZBUS, LK_T_ZRESET, LK_T_ZWAIT, LK_T_PAD, LK_T_PADW, LK_T_N };
typedef struct { unsigned long long calls, moved_calls, moved, z80moved; unsigned max, before, after, zbefore, zafter; } lk_t_door_t;
lk_t_door_t lk_t_door[LK_T_N];   /* before / after = m68k.cycles (zbefore / zafter = Z80.cycles) around the LAST call: a later shadow compare reads them */
static const char *const lk_t_name[LK_T_N] = { "status_r", "hvc_r", "dma_start", "fifo_w", "zarea", "zbus_w", "zreset_w", "zwait", "pad", "pad_w" };
static inline unsigned lk_t_in(int id) { lk_t_door_t *d = &lk_t_door[id]; d->before = m68k.cycles; d->zbefore = Z80.cycles; return d->before; }
static inline void lk_t_out(int id) {
    lk_t_door_t *d = &lk_t_door[id]; unsigned a = m68k.cycles, za = Z80.cycles;
    d->after = a; d->zafter = za; d->calls++;
    if (a > d->before && a - d->before < 0x10000000u) { unsigned m = a - d->before; d->moved_calls++; d->moved += m; if (m > d->max) d->max = m; }
    if (za > d->zbefore && za - d->zbefore < 0x10000000u) d->z80moved += za - d->zbefore;
}
static void lk_t_dump(void) {
    const char *e = getenv("LANDSTALKER_TIMEDOORS"); FILE *f = stderr; int i;
    if (!e || !*e) return;
    if (strcmp(e, "1") != 0 && !(f = fopen(e, "a"))) return;
    for (i = 0; i < LK_T_N; i++)
        fprintf(f, "TIMEDOORS %s calls=%llu moved_calls=%llu moved_mclk=%llu max_mclk=%u z80_mclk=%llu\n", lk_t_name[i], lk_t_door[i].calls, lk_t_door[i].moved_calls, lk_t_door[i].moved, lk_t_door[i].max, lk_t_door[i].z80moved);
    if (f != stderr) fclose(f);
}
__attribute__((constructor)) static void lk_t_init(void) { const char *e = getenv("LANDSTALKER_TIMEDOORS"); if (e && *e) atexit(lk_t_dump); }
unsigned int lk_t_status_r(unsigned int cycles) { unsigned int v; lk_t_in(LK_T_STATUS); v = lk_tt_sr(cycles); lk_t_out(LK_T_STATUS); return v; }   /* G2 */
unsigned int lk_t_hvc_r(unsigned int cycles)    { unsigned int v; lk_t_in(LK_T_HVC);    v = lk_tt_hv(cycles); lk_t_out(LK_T_HVC);    return v; }   /* G3 */
void lk_t_dma_start(unsigned int data) { lk_t_in(LK_T_DMA); vdp_68k_ctrl_w(data); lk_t_out(LK_T_DMA); }   /* G4: every control port write; the DMA starts here (moved_calls = writes that moved the clock) */
void lk_t_fifo_w(unsigned int data)    { lk_t_in(LK_T_FIFO); vdp_68k_data_w(data); lk_t_out(LK_T_FIFO); }   /* G5 */
void lk_t_zarea(int write) { lk_t_in(LK_T_ZAREA); (void)write; m68k.cycles += 1 * 7; lk_t_out(LK_T_ZAREA); }   /* G6: the access latency of z80_read_byte / z80_write_byte */
void lk_t_zbus_w(unsigned int data, unsigned int cycles)   { lk_t_in(LK_T_ZBUS);   gen_zbusreq_w(data, cycles); lk_t_out(LK_T_ZBUS); }   /* G7 */
void lk_t_zreset_w(unsigned int data, unsigned int cycles) { lk_t_in(LK_T_ZRESET); gen_zreset_w(data, cycles);  lk_t_out(LK_T_ZRESET); }   /* G7 */
void lk_t_zwait(void (*gpgx)(void)) { lk_t_in(LK_T_ZWAIT); gpgx(); lk_t_out(LK_T_ZWAIT); }   /* G8: gpgx = z80_request_68k_bus_access (adds the wait to the 68K and the Z80) */
int lk_t_pad(int port, unsigned int step, unsigned int cycles, unsigned int latency) {   /* G9: TH latency test of gamepad_read (1 = TH state switching has not happened yet) */
    lk_t_door_t *d = &lk_t_door[LK_T_PAD]; (void)port; (void)step;
    d->before = d->after = cycles; d->calls++; return cycles < latency; }
unsigned int lk_t_pad_w(int port, unsigned int cycles) {   /* G9: deadline of the TH 0->1 latency set by gamepad_write */
    lk_t_door_t *d = &lk_t_door[LK_T_PADW]; (void)port;
    d->before = d->after = cycles; d->calls++; return cycles + 172; }
/* ---- end LK_TIMEDOORS ---- */
'''
p = os.path.join(ROOT, "src/bus.c")
edit(p, [
 ("/* ---- end LK_TIMETRACE ---- */\n", "/* ---- end LK_TIMETRACE ---- */\n" + DOORS, 1),
 # CYCSTAT fix: the block charge is added inside bus_advance_inner; nested advances (interrupt entry, Z80 run) must not count it as stolen
 # the Z80 run of the line loop moves the 68K clock (LK_T_ZWAIT): count it as 'IO/Z80' here and keep it out of the next advance's 'stolen'
 ("        else if (zstate == 1) z80_run(mcycles_vdp);\n",
  "        else if (zstate == 1) { unsigned int zc0 = m68k.cycles; z80_run(mcycles_vdp);   /* LK_TIMEDOORS v1 */\n            if (m68k.cycles > zc0 && m68k.cycles - zc0 < 0x10000000u) { s_stolen[1] += m68k.cycles - zc0; s_expected_cycles += m68k.cycles - zc0; } }\n", 1),
 ("    m68k.cycles += mc;\n\n    /* Sync GPGX internal PC with recomp PC.",
  "    m68k.cycles += mc;\n    s_expected_cycles = m68k.cycles;   /* LK_TIMEDOORS v1: the block charge is ours, nested advances must not see it as stolen */\n\n    /* Sync GPGX internal PC with recomp PC.", 1),
])
# s_expected_cycles is declared before bus_advance_inner (line ~179): fine.

DECL = ("unsigned int lk_tt_sr(unsigned int), lk_tt_hv(unsigned int);   /* LK_TIMETRACE v1 */\n",
        "unsigned int lk_t_status_r(unsigned int), lk_t_hvc_r(unsigned int); void lk_t_dma_start(unsigned int), lk_t_fifo_w(unsigned int), lk_t_zarea(int), lk_t_zbus_w(unsigned int, unsigned int), lk_t_zreset_w(unsigned int, unsigned int);   /* LK_TIMEDOORS v1 */\n")
edit(os.path.join(CORE, "mem68k.c"), [
 (DECL[0], DECL[0] + DECL[1], 1),
  ("lk_tt_sr(m68k.cycles)", "lk_t_status_r(m68k.cycles)", 3),
 ("lk_tt_hv(m68k.cycles)", "lk_t_hvc_r(m68k.cycles)", 3),
 ("vdp_68k_data_w(", "lk_t_fifo_w(", 2),
 ("vdp_68k_ctrl_w(", "lk_t_dma_start(", 2),
 ("gen_zbusreq_w(", "lk_t_zbus_w(", 2),
 ("gen_zreset_w(", "lk_t_zreset_w(", 2),
 ("unsigned int z80_read_byte(unsigned int address)\n{\n  /* Z80 bus access latency */\n  m68k.cycles += 1 * 7;\n",
  "unsigned int z80_read_byte(unsigned int address)\n{\n  /* Z80 bus access latency */\n  lk_t_zarea(0);\n", 1),
 ("  /* Z80 bus access latency (fixes Pacman 2: New Adventures sound engine crashes & Puyo Puyo 2 crash when exiting option menu) */\n  m68k.cycles += 1 * 7;\n",
  "  /* Z80 bus access latency (fixes Pacman 2: New Adventures sound engine crashes & Puyo Puyo 2 crash when exiting option menu) */\n  lk_t_zarea(1);\n", 1),
])
edit(os.path.join(CORE, "memz80.c"), [
 ("static void z80_request_68k_bus_access(void)\n{\n",
  "static void z80_request_68k_bus_access_gpgx(void);   /* LK_TIMEDOORS v1 */\nextern void lk_t_zwait(void (*)(void));\nstatic void z80_request_68k_bus_access(void) { lk_t_zwait(z80_request_68k_bus_access_gpgx); }\nstatic void z80_request_68k_bus_access_gpgx(void)\n{\n", 1),
])
g = os.path.join(CORE, "input_hw/gamepad.c")
t = open(g).read()
edit(g, [
 ("  if (cycles < gamepad[port].Latency)\n  {\n    /* TH internal state switching has not occured yet (Decap Attack) */",
  "  if (lk_t_pad(port, step, cycles, gamepad[port].Latency))   /* LK_TIMEDOORS v1 */\n  {\n    /* TH internal state switching has not occured yet (Decap Attack) */", 1),
 ("      gamepad[port].Latency = cycles + 172;\n", "      gamepad[port].Latency = lk_t_pad_w(port, cycles);\n", 1),
])
t = open(g).read()
if "int lk_t_pad(int" not in t:
    inc = list(re.finditer(r'^#include .*\n', t, re.M))[-1]
    t = t[:inc.end()] + "extern int lk_t_pad(int, unsigned int, unsigned int, unsigned int); extern unsigned int lk_t_pad_w(int, unsigned int);   /* LK_TIMEDOORS v1 */\n" + t[inc.end():]
    open(g, "w").write(t)
