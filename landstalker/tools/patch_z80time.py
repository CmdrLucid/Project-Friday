#!/usr/bin/env python3
"""Timing model, step T4 (2026-10-29 night, docs/TIMING_PLAN.md): the Z80 BUS TIMING is ours.  No behaviour change (bit identical to GPGX).
bus.c (block LK_Z80TIME, functions lk_z_*) now does itself what GPGX did with the clocks on the Z80 side:
  - G8 the wait of a Z80 access to the 68K bus (door lk_t_zwait; GPGX z80_request_68k_bus_access): the Z80 waits for a running 68K bus DMA
    (until the DMA end of lk_clk, 'still waiting' bit 4 of zstate when the DMA is not finished), the 68K loses ((Z80 cycle mod 7) + 72) / 7 * 7
    master clocks, the Z80 3 Z80 cycles (45);
  - the Z80 side of a 68K bus DMA (vdp_dma_update: a Z80 that waits for the bus waits until the DMA chunk ends) moves into lk_v_dma_halt (T3);
  - G7 the BUSREQ / RESET handshake ($A11100 / $A11200, doors lk_t_zbus_w / lk_t_zreset_w): our copy of gen_zbusreq_w / gen_zreset_w (Z80 run up
    to the 68K time when it is stopped, Z80 clock re-aligned to 15 master clocks when it restarts, the 68K's window on Z80 RAM opened / closed,
    Z80 + YM2612 reset).  The copy is guarded: the patch refuses to run if GPGX's two functions are not EXACTLY the text it was copied from
    (fingerprint below), so a later change of genesis.c cannot make them drift apart silently.
  - G6 (the +7 of a 68K access to the Z80 area) has been our code since T1 (lk_t_zarea).
Still GPGX (called by our code, not timing decisions): z80_run (the Z80 / native driver run), z80_reset, fm_reset, the Z80 memory map, zstate (global).
Not in T4: the Z80 boot stub of the system start (GPGX's Z80 runs it until the game uploads its driver): moved to T6 (system start).
Modes: default = ours; LANDSTALKER_TIMING=gpgx = GPGX's functions; LANDSTALKER_TIME_SHADOW: the bus wait (G8) is computed both ways (GPGX's applied,
differences counted, exit line 'TIME_SHADOW Z80 ...'); the handshake cannot run twice (it runs the Z80), it is checked by the bench + time trace.
Idempotent (marker below).  usage: patch_z80time.py path/to/genrecomp   (after patch_vdptime.py)"""
import hashlib, os, re, sys
ROOT = sys.argv[1]
VER = "LK_Z80TIME v1"
FP = {"void gen_zbusreq_w(unsigned int data, unsigned int cycles)": "0ab70f492a51",
      "void gen_zreset_w(unsigned int data, unsigned int cycles)": "5b2f9dada5f7"}

def edit(path, edits):
    t = open(path).read()
    if VER in t:
        print(os.path.basename(path), "already patched:", VER); return
    for old, new, cnt in edits:
        assert t.count(old) == cnt, (path, old[:90], t.count(old))
        t = t.replace(old, new)
    open(path, "w").write(t); print(os.path.basename(path), "patched:", VER)

# the guard: GPGX's handshake functions must be the text our copy was made from
G = open(os.path.join(ROOT, "ext/Genesis-Plus-GX/core/genesis.c")).read()
for fn, want in FP.items():
    i = G.index(fn); j = G.index("\n}\n", i) + 3
    got = hashlib.sha1(re.sub(r"\s+", " ", G[i:j]).encode()).hexdigest()[:12]
    assert got == want, "%s changed (fingerprint %s, our copy in patch_z80time.py was made from %s): update the copy lk_z_* first" % (fn, got, want)

VDP = os.path.join(ROOT, "ext/Genesis-Plus-GX/core/vdp_ctrl.c")
VDP_EDITS = [
    ("    if (zstate & 4)\n    {\n      /* force Z80 to wait until end of DMA timeframe */\n",
     "    extern int lk_z_own;\n    if (!(lk_z_own && lk_v_own) && (zstate & 4))   /* LK_Z80TIME v1: own mode = lk_v_dma_halt (bus.c) */\n    {\n      /* force Z80 to wait until end of DMA timeframe */\n", 1),
]

BUS = os.path.join(ROOT, "src/bus.c")
OLD_HALT = "void lk_v_dma_halt(unsigned int end) { m68k.cycles = end; }"
OLD_ZB = "void lk_t_zbus_w(unsigned int data, unsigned int cycles)   { lk_t_in(LK_T_ZBUS);   gen_zbusreq_w(data, cycles); lk_t_out(LK_T_ZBUS); }   /* G7 */\n"
OLD_ZR = "void lk_t_zreset_w(unsigned int data, unsigned int cycles) { lk_t_in(LK_T_ZRESET); gen_zreset_w(data, cycles);  lk_t_out(LK_T_ZRESET); }   /* G7 */\n"
OLD_ZW = "void lk_t_zwait(void (*gpgx)(void)) { lk_t_in(LK_T_ZWAIT); gpgx(); lk_t_out(LK_T_ZWAIT); }   /* G8: gpgx = z80_request_68k_bus_access (adds the wait to the 68K and the Z80) */\n"
Z = r'''/* ---- LK_Z80TIME v1 (tools/patch_z80time.py, docs/TIMING_PLAN.md T4): the Z80 bus timing is ours ---- */
extern void lk_nat_resync(void);
int lk_z_own = 1;     /* 1 = ours (default); LANDSTALKER_TIMING=gpgx -> 0 = GPGX's functions */
static int lk_z_shadow;
static unsigned long long lk_z_chk, lk_z_bad;
static void lk_z_dump(void) {
    FILE *f = lk_clk_open();
    fprintf(f, "TIME_SHADOW Z80 own=%d zwait=%llu/%llu (checks/mismatches)\n", lk_z_own, lk_z_chk, lk_z_bad);
    if (f != stderr) fclose(f);
}
__attribute__((constructor)) static void lk_z_init(void) {
    const char *t = getenv("LANDSTALKER_TIMING"), *s = getenv("LANDSTALKER_TIME_SHADOW");
    if (t && !strcmp(t, "gpgx")) lk_z_own = 0;
    if (lk_z_own && s && *s && strcmp(s, "0")) { lk_z_shadow = 1; atexit(lk_z_dump); }
}
/* G8: a Z80 access to the 68K bus (banked ROM window): m = 68K clock, z = Z80 clock, zs = zstate, all updated */
static void lk_z_wait_calc(unsigned int *m, unsigned int *z, unsigned int *zs) {
    if ((*z < lk_clk.dma_end) && (dma_type < 2)) { *z = lk_clk.dma_end; if (dma_length) *zs |= 4; }   /* a 68K bus DMA owns the bus: wait for its end */
    *m += (((*z % 7) + 72) / 7) * 7;   /* the 68K loses about 11 cycles per Z80 access (GPGX's measured value) */
    *z += (3 * 15);                    /* the Z80 waits 3 Z80 cycles */
}
void lk_t_zwait(void (*gpgx)(void)) {   /* G8 */
    unsigned int m, z, zs, m0, z0;
    lk_t_in(LK_T_ZWAIT);
    if (!lk_z_own) { gpgx(); lk_t_out(LK_T_ZWAIT); return; }
    m = m0 = m68k.cycles; z = z0 = Z80.cycles; zs = zstate;
    lk_z_wait_calc(&m, &z, &zs);
    if (!lk_z_shadow) {
        m68k.cycles = m; Z80.cycles = z; zstate = (uint8)zs;
        if (lk_tt_active) lk_tt_ev('Z', 2, (m68k.cycles - m0), (Z80.cycles - z0), 0, 0, 0);
    } else {
        gpgx(); lk_z_chk++;
        if (m != m68k.cycles || z != Z80.cycles || zs != zstate) {
            if (++lk_z_bad <= 6) {
                FILE *f = lk_clk_open();
                fprintf(f, "TIME_SHADOW Z80 MISMATCH zwait #%llu: frame %ld: 68K ours %u gpgx %u, Z80 ours %u gpgx %u, zstate ours %u gpgx %u (start 68K %u Z80 %u dma_end %u type %d) stack:",
                        lk_z_bad, platform_frame_number(), m, m68k.cycles, z, Z80.cycles, zs, (unsigned)zstate, m0, z0, lk_clk.dma_end, (int)dma_type);
                func_table_dump_stack(f); fprintf(f, "\n"); if (f != stderr) fclose(f);
            }
        }
    }
    lk_t_out(LK_T_ZWAIT);
}
/* G7: the 68K's window on the Z80 bus ($A00000..$A0FFFF): open while the Z80 is stopped (BUSREQ granted) or held in reset */
static void lk_z_map(int open) {
    if (open) { m68k.memory_map[0xa0].read8 = z80_read_byte; m68k.memory_map[0xa0].read16 = z80_read_word; m68k.memory_map[0xa0].write8 = z80_write_byte; m68k.memory_map[0xa0].write16 = z80_write_word; }
    else { m68k.memory_map[0xa0].read8 = m68k_read_bus_8; m68k.memory_map[0xa0].read16 = m68k_read_bus_16; m68k.memory_map[0xa0].write8 = m68k_unused_8_w; m68k.memory_map[0xa0].write16 = m68k_unused_16_w; }
}
/* zstate: bit 0 = /RESET released (Z80 may run), bit 1 = BUSREQ (68K owns the Z80 bus), bit 2 = Z80 waits for the 68K bus at the end of a DMA chunk */
static void lk_z_busreq_w(unsigned int data, unsigned int cycles) {   /* copy of GPGX gen_zbusreq_w */
    if (lk_tt_active) lk_tt_ev('B', 2, data, zstate, 0, 0, 0);
    if (data) {   /* BUSREQ asserted */
        if (zstate == 1) { z80_run(cycles); lk_z_map(1); }   /* the running Z80 stops: first let it catch up with the 68K */
        zstate |= 2;
    } else {      /* BUSREQ released */
        if (zstate == 3) { Z80.cycles = ((cycles + 14) / 15) * 15; lk_nat_resync(); lk_z_map(0); }   /* the Z80 restarts on a Z80 clock edge (15 mclk) */
        zstate &= 1;
    }
}
static void lk_z_reset_w(unsigned int data, unsigned int cycles) {   /* copy of GPGX gen_zreset_w */
    if (lk_tt_active) lk_tt_ev('R', 2, data, zstate, 0, 0, 0);
    if (data) {   /* /RESET released */
        if (zstate == 0) { Z80.cycles = ((cycles + 14) / 15) * 15; lk_nat_resync(); z80_reset(); fm_reset(cycles); }
        else if (zstate == 2) { lk_z_map(1); z80_reset(); fm_reset(cycles); }
        zstate |= 1;
    } else {      /* /RESET asserted */
        if (zstate == 1) z80_run(cycles);
        else if (zstate == 3) lk_z_map(0);
        fm_reset(cycles);   /* the YM2612 is held in reset too */
        zstate &= 2;
    }
}
void lk_t_zbus_w(unsigned int data, unsigned int cycles)   { lk_t_in(LK_T_ZBUS);   if (lk_z_own) lk_z_busreq_w(data, cycles); else gen_zbusreq_w(data, cycles); lk_t_out(LK_T_ZBUS); }   /* G7 */
void lk_t_zreset_w(unsigned int data, unsigned int cycles) { lk_t_in(LK_T_ZRESET); if (lk_z_own) lk_z_reset_w(data, cycles); else gen_zreset_w(data, cycles); lk_t_out(LK_T_ZRESET); }   /* G7 */
/* ---- end LK_Z80TIME ---- */
'''
BUS_EDITS = [
    (OLD_HALT, "void lk_v_dma_halt(unsigned int end) { extern int lk_z_own; m68k.cycles = end; if (lk_z_own && (zstate & 4)) Z80.cycles = end; }   /* LK_Z80TIME v1: + the Z80 waiting for the bus waits until the chunk ends */", 1),
    (OLD_ZB + OLD_ZR + OLD_ZW, Z, 1),
]
edit(VDP, VDP_EDITS)
edit(BUS, BUS_EDITS)
