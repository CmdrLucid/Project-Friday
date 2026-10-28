/* sndnative.c -- runtime of the recompiled Z80 sound driver inside the GPGX core (pasted into core/memz80.c by tools/patch_sndnative.py; docs/SOUND_PLAN.md step 4).
   Hand written, contains no game code: the driver itself is tools/z80recomp.py's output (core/z80drv_gen.c, generated from the user's ROM at build time).
   SHADOW MODE (env LANDSTALKER_SND_SHADOW=1): the recompiled driver runs next to GPGX's Z80 on the same inputs (68K mailbox writes, clock, bus request pauses) and every chip write it
   makes is compared with the one GPGX's Z80 makes (same kind, time, port, value) and Z80 RAM is compared after every run.  Nothing of it reaches the chips yet. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "z80rt.h"
extern uint8 zram[0x2000];
extern long platform_frame_number(void);

#define LKN_Q 4096
typedef struct { uint8_t kind; uint32_t t; uint8_t a, v; int x; } lkn_ev_t;     /* kind: 'Y' YM2612 write (a = port 0..3), 'P' PSG write */
static lkn_ev_t lkn_g[LKN_Q], lkn_n[LKN_Q]; static int lkn_gh, lkn_gt, lkn_nh, lkn_nt;   /* GPGX events / native events (ring buffers: head = next read, tail = next write) */
static long lkn_match, lkn_mismatch, lkn_ramdiff; static int lkn_on = -1, lkn_dead, lkn_native;   /* lkn_native: DEFAULT since 2026-10-28 (LANDSTALKER_SND=gpgx = GPGX's Z80 again; LANDSTALKER_SND_SHADOW=n = shadow test), the recompiled driver REPLACES GPGX's Z80 */
static Z80S lkn_z; static uint8_t lkn_ram[0x2000]; static uint32_t lkn_zbank;
/* YM2612 timers / busy flag, same arithmetic as GPGX's MAME OPN2 core (sound/ym2612.c, sound.c): sample = 1008 master cycles, timer B period (256 - v) * 16 samples, timer A 1024 - v */
static struct { int mode, ta, tal, tac, tb, tbl, tbc, status, addr; int64_t count, busy, start; } lkn_ym;   /* start: the sample grid's origin in this frame (GPGX fm_cycles_start) */
static void lkn_ymreset(void) { lkn_ym.mode = 0; lkn_ym.ta = 0; lkn_ym.tal = 1024; lkn_ym.tac = 0; lkn_ym.tb = 0; lkn_ym.tbl = 256 << 4; lkn_ym.tbc = 0; lkn_ym.status = 0; lkn_ym.busy = 0; }
static void lkn_ymsync(int64_t t) {
    if (t > lkn_ym.count) {
        int n = (int)((t - lkn_ym.count + 1007) / 1008), i;
        lkn_ym.count += (int64_t)n * 1008;
        for (i = 0; i < n; i++) if (lkn_ym.mode & 1) { if (--lkn_ym.tac <= 0) { if (lkn_ym.mode & 4) lkn_ym.status |= 1; lkn_ym.tac = lkn_ym.tal; } }
        if (lkn_ym.mode & 2) { lkn_ym.tbc -= n; if (lkn_ym.tbc <= 0) { if (lkn_ym.mode & 8) lkn_ym.status |= 2; do lkn_ym.tbc += lkn_ym.tbl; while (lkn_ym.tbc <= 0); } }
    }
}
static void lkn_push(int kind, uint32_t t, int a, int v) { lkn_ev_t *e = &lkn_n[lkn_nt % LKN_Q]; e->kind = (uint8_t)kind; e->t = t; e->a = (uint8_t)a; e->v = (uint8_t)v; e->x = kind == 'R' ? lkn_ym.tbc : 0; lkn_nt++; }
static uint32_t lkn_now(Z80S *s) { return s->cyc * 15 + s->wait; }
extern uint32 dma_endCycles; extern uint8 dma_type;
static void lkn_buswait(Z80S *s) {   /* a Z80 access to the 68K bus (banked ROM window, VDP area): waits for a running VDP DMA, then 3 Z80 cycles (memz80.c z80_request_68k_bus_access) */
    uint32_t now = lkn_now(s);
    { static int dbg = -1; if (dbg < 0) { const char *e = getenv("LANDSTALKER_SND_SHADOW"); dbg = e && *e == '6'; } if (dbg && platform_frame_number() == 3600 && now > 780000 && now < 900000) fprintf(stderr, "native buswait now %u dma_end %u type %d\n", now, (unsigned)dma_endCycles, (int)dma_type); }
    if (now < dma_endCycles && dma_type < 2) s->wait += dma_endCycles - now;
    s->wait += 3 * 15;
}
extern unsigned char z80_memory_r(unsigned int address); extern void z80_memory_w(unsigned int address, unsigned char data);
static int lkn_active;
uint8_t z80rt_rb(Z80S *s, uint16_t a) {
    if (lkn_native) {   /* native mode: RAM is GPGX's zram, everything else goes through GPGX's own Z80 memory map with Z80.cycles = this Z80's time (chip writes / reads, bank register, PSG, the 68K bus wait states and the 68K stall are then exactly GPGX's) */
        uint32_t now; uint8_t v;
        if (a < 0x4000) return zram[a & 0x1FFF];
        now = lkn_now(s); Z80.cycles = now; v = z80_memory_r(a); s->wait += Z80.cycles - now; return v;
    }
    if (a < 0x4000) return lkn_ram[a & 0x1FFF];
    if (a < 0x6000) { if ((a & 3) == 0) { uint8_t v; lkn_ymsync(lkn_now(s)); v = (uint8_t)(lkn_ym.status | (lkn_now(s) >= lkn_ym.busy ? 0 : 0x80)); lkn_push('R', lkn_now(s), 0, v); return v; } return 0; }
    if (a < 0x8000) { if (a >= 0x7F00) lkn_buswait(s); return 0xFF; }
    lkn_buswait(s);
    { uint32_t ra = lkn_zbank | (a & 0x7FFF); return ra < 0x400000 ? cart.rom[ra ^ 1] : 0xFF;   /* GPGX keeps the ROM byte swapped (LSB_FIRST) */ }
}
void z80rt_wb(Z80S *s, uint16_t a, uint8_t v) {
    uint32_t t;
    if (lkn_native) {
        uint32_t now;
        if (a < 0x4000) { zram[a & 0x1FFF] = v; return; }
        now = lkn_now(s); Z80.cycles = now; z80_memory_w(a, v); s->wait += Z80.cycles - now; return;
    }
    if (a >= 0x8000 || a >= 0x7F00) lkn_buswait(s);
    t = lkn_now(s);
    if (a < 0x4000) { lkn_ram[a & 0x1FFF] = v; return; }
    if (a < 0x6000) {
        int port = a & 3; lkn_push('Y', t, port, v);
        if (port & 1) {   /* data port: the chip is synchronised, the busy flag starts */
            lkn_ymsync(t); lkn_ym.busy = (((int64_t)t + 41) / 42 + 32) * 42;
            switch (lkn_ym.addr & 0x1FF) {
                case 0x24: lkn_ym.ta = (lkn_ym.ta & 3) | (v << 2); lkn_ym.tal = 1024 - lkn_ym.ta; break;
                case 0x25: lkn_ym.ta = (lkn_ym.ta & 0x3FC) | (v & 3); lkn_ym.tal = 1024 - lkn_ym.ta; break;
                case 0x26: lkn_ym.tb = v; lkn_ym.tbl = (256 - v) << 4; break;
                case 0x27: if ((v & 1) && !(lkn_ym.mode & 1)) lkn_ym.tac = lkn_ym.tal; if ((v & 2) && !(lkn_ym.mode & 2)) lkn_ym.tbc = lkn_ym.tbl; lkn_ym.status &= (~v >> 4); lkn_ym.mode = v; break;
                default: break;
            }
        } else lkn_ym.addr = (port == 0 ? 0 : 0x100) | v;
        return;
    }
    if (a >= 0x6000 && a < 0x6100) { lkn_zbank = ((lkn_zbank >> 1) | ((uint32_t)(v & 1) << 23)) & 0xFF8000; return; }
    if (a >= 0x7F10 && a <= 0x7F17 && (a & 1)) { lkn_push('P', t, 0, v); return; }
}
/* ---- hooks called by the GPGX core ---- */
static int lkn_enabled(void) { if (lkn_on < 0) { const char *e = getenv("LANDSTALKER_SND_SHADOW"), *nv = getenv("LANDSTALKER_SND"); lkn_native = nv ? !strcmp(nv, "native") : !(e && *e && *e != '0'); lkn_on = lkn_native || (e && *e && *e != '0'); if (lkn_on) { memset(&lkn_z, 0, sizeof lkn_z); lkn_ymreset(); lkn_ym.count = 0; fprintf(stderr, lkn_native ? "sndnative: NATIVE sound: the recompiled Z80 driver replaces the GPGX Z80\n" : "sndnative: shadow mode on (recompiled Z80 driver next to the GPGX Z80)\n"); } } return lkn_on; }
extern void lk_ym_state(int *v);
void lk_nat_gdbg(unsigned t, unsigned v, int cnt) { static int dbg = -1; if (dbg < 0) { const char *e = getenv("LANDSTALKER_SND_SHADOW"); dbg = e && *e == '4'; } if (dbg && platform_frame_number() == 66 && t > 130000 && t < 150000) { int st[6]; lk_ym_state(st); fprintf(stderr, "gpgx read t=%u v=%02X mode %02X tbc %d tbl %d status %02X gpgx count %d | native count %lld tbc %d\n", t, v, st[0], st[1], st[2], st[3], cnt, (long long)lkn_ym.count, lkn_ym.tbc); } }
void lk_nat_gframe(int before, int after) { static int dbg = -1; if (dbg < 0) { const char *e = getenv("LANDSTALKER_SND_SHADOW"); dbg = e && *e == '5'; } if (dbg && platform_frame_number() >= 62 && platform_frame_number() <= 66) { int st[6]; extern void lk_ym_state(int *v); lk_ym_state(st); fprintf(stderr, "gpgx frame %ld: end time %d new count %d tbc %d mode %02X | native count %lld tbc %d\n", platform_frame_number(), before, after, st[1], st[0], (long long)lkn_ym.count, lkn_ym.tbc); } }
void lk_nat_gevent(int kind, uint32_t t, int a, int v) { if (!lkn_enabled() || lkn_native) return; lkn_ev_t *e = &lkn_g[lkn_gt % LKN_Q]; e->kind = (uint8_t)kind; e->t = t; e->a = (uint8_t)a; e->v = (uint8_t)v; if (kind == 'R') { int st[6]; extern void lk_ym_state(int *v); lk_ym_state(st); e->x = st[1]; } else e->x = 0; lkn_gt++; }
void lk_nat_ram_w(unsigned a, unsigned v) { if (lkn_enabled()) lkn_ram[a & 0x1FFF] = (uint8_t)v; }
static unsigned lkn_dbgfrom(void) { const char *e = getenv("LANDSTALKER_SND_DBGFROM"); return e ? (unsigned)atol(e) : 0; }
/* (lkn_active is declared above) the recompiled driver runs only while the Z80 RAM holds the game's driver (not during the boot stub of the system init) */
void lk_nat_reset(void) {
    static const uint8_t sig[6] = { 0xF3, 0x31, 0xF0, 0x1F, 0xAF, 0x32 };
    if (!lkn_enabled()) return;
    lkn_active = memcmp(zram, sig, 6) == 0 && lkn_on == 1;
    if (!lkn_active) return;
    memcpy(lkn_ram, zram, sizeof lkn_ram);   /* the boot stub of the system init wrote into Z80 RAM too: start from the real contents */
    lkn_z.a = Z80.af.b.h; lkn_z.f = Z80.af.b.l; lkn_z.b = Z80.bc.b.h; lkn_z.c = Z80.bc.b.l; lkn_z.d = Z80.de.b.h; lkn_z.e = Z80.de.b.l; lkn_z.h = Z80.hl.b.h; lkn_z.l = Z80.hl.b.l;   /* a Z80 reset keeps the registers */
    lkn_z.a2 = Z80.af2.b.h; lkn_z.f2 = Z80.af2.b.l; lkn_z.b2 = Z80.bc2.b.h; lkn_z.c2 = Z80.bc2.b.l; lkn_z.d2 = Z80.de2.b.h; lkn_z.e2 = Z80.de2.b.l; lkn_z.h2 = Z80.hl2.b.h; lkn_z.l2 = Z80.hl2.b.l;
    lkn_z.ix = Z80.ix.w.l; lkn_z.iy = Z80.iy.w.l; lkn_z.sp = Z80.sp.w.l; lkn_z.pc = 0; lkn_z.iff1 = lkn_z.iff2 = 0; lkn_z.bad = 0;
    { extern int lk_fm_count(void), lk_fm_busy(void); lkn_ym.start = lkn_ym.count = lk_fm_count(); lkn_ym.busy = (uint32_t)lk_fm_busy(); }   /* same sample grid and busy flag as the chip model */
    lkn_z.cyc = 0; lkn_gh = lkn_gt; lkn_nh = lkn_nt = lkn_gt;   /* start in step */
    fprintf(stderr, "sndnative: the game's Z80 driver starts, recompiled copy starts with it\n");
}
void lk_nat_ymreset(void) { if (lkn_enabled()) lkn_ymreset(); }
void lk_nat_frame(unsigned mcycles) { if (!lkn_enabled() || !lkn_active) return; if (lkn_on == 1) { static int dbg = -1; if (dbg < 0) { const char *e = getenv("LANDSTALKER_SND_SHADOW"); dbg = e && *e == '5'; } if (dbg && platform_frame_number() >= 62 && platform_frame_number() <= 66) fprintf(stderr, "native frame %ld: before sync count %lld tbc %d\n", platform_frame_number(), (long long)lkn_ym.count, lkn_ym.tbc); }
 lkn_ymsync(mcycles);   /* GPGX's sound_update() runs the FM chip to the end of the frame before it rebases the counters: the chip is then up to one sample AHEAD of the Z80's time */
  { uint32_t t = lkn_now(&lkn_z); t = t > mcycles ? t - mcycles : 0; lkn_z.cyc = t / 15; lkn_z.wait = t % 15; } { int64_t k = (mcycles - lkn_ym.start + 1007) / 1008, te; if (k < 1) k = 1; te = lkn_ym.start + k * 1008; lkn_ym.count = te - mcycles; lkn_ym.start = lkn_ym.count; }   /* GPGX sound_update(): the new count is the grid point after the frame's end minus the frame length, even when a status read at the very end of the frame already ran the chip one sample further (that sample is then run again) */
  if (lkn_ym.busy > mcycles) lkn_ym.busy -= mcycles; else lkn_ym.busy = 0; }
static void lkn_compare(void) {
    while (lkn_gh < lkn_gt && lkn_nh < lkn_nt) {
        lkn_ev_t *g = &lkn_g[lkn_gh % LKN_Q], *n = &lkn_n[lkn_nh % LKN_Q];
        if (g->kind == n->kind && g->t == n->t && g->a == n->a && g->v == n->v && g->x == n->x) lkn_match++;
        else { lkn_mismatch++; if (lkn_mismatch <= 12) fprintf(stderr, "sndnative: MISMATCH frame %ld: gpgx %c t=%u a=%u v=%02X x=%d | native %c t=%u a=%u v=%02X x=%d (match so far %ld)\n", platform_frame_number(), g->kind, g->t, g->a, g->v, g->x, n->kind, n->t, n->a, n->v, n->x, lkn_match); }
        lkn_gh++; lkn_nh++;
    }
    if (lkn_gt - lkn_nt > LKN_Q / 2 || lkn_nt - lkn_gt > LKN_Q / 2) { if (!lkn_dead) fprintf(stderr, "sndnative: event queues out of step (gpgx %d native %d), comparison stopped\n", lkn_gt, lkn_nt); lkn_dead = 1; lkn_gh = lkn_gt; lkn_nh = lkn_nt; }
}
void lk_nat_gstep(void) { static int dbg = -1, n; if (dbg < 0) { const char *e = getenv("LANDSTALKER_SND_SHADOW"); dbg = e && *e == '3'; } if (dbg && lkn_active && n < 4000 && Z80.cycles >= lkn_dbgfrom()) { n++; fprintf(stderr, "gpgx pc %04X cyc %u a %02X b %02X de %02X%02X hl %02X%02X sp %04X\n", Z80.pc.w.l, Z80.cycles, Z80.af.b.h, Z80.bc.b.h, Z80.de.b.h, Z80.de.b.l, Z80.hl.b.h, Z80.hl.b.l, Z80.sp.w.l); } }
void lk_nat_resync(void) { if (!lkn_enabled() || !lkn_active) return; lkn_z.cyc = Z80.cycles / 15; lkn_z.wait = 0; }   /* the Z80 restarts at the 68K's time (may be earlier than where it had run to) */
void lk_nat_begin(void) {   /* start of a z80_run(): skip the time the Z80 was stopped (bus request / reset) */
    if (!lkn_enabled() || !lkn_active) return;
    { static int dbg = -1, n; if (dbg < 0) { const char *e = getenv("LANDSTALKER_SND_SHADOW"); dbg = e && *e == '2'; } if (dbg && n++ < 8) fprintf(stderr, "sndnative: begin gpgx cyc %u pc %04X halt %d zram[0..7] %02X%02X%02X%02X%02X%02X%02X%02X native cyc %u pc %04X\n", Z80.cycles, Z80.pc.w.l, Z80.halt, zram[0], zram[1], zram[2], zram[3], zram[4], zram[5], zram[6], zram[7], lkn_z.cyc * 15, lkn_z.pc); }
    if (lkn_now(&lkn_z) < Z80.cycles) { lkn_z.cyc = Z80.cycles / 15; lkn_z.wait = 0; }
}
void lk_nat_end(void) {     /* end of a z80_run(): run the recompiled driver up to the same time and compare */
    if (!lkn_enabled() || !lkn_active) return;
    { static int dbg3 = -1, n3; if (dbg3 < 0) { const char *e = getenv("LANDSTALKER_SND_SHADOW"); dbg3 = e && *e == '3'; } if (dbg3) while (lkn_now(&lkn_z) < Z80.cycles && !lkn_z.bad) { if (n3 < 4000 && lkn_now(&lkn_z) >= lkn_dbgfrom() && ++n3) fprintf(stderr, "nat pc %04X cyc %u a %02X b %02X de %02X%02X hl %02X%02X sp %04X\n", lkn_z.pc, lkn_now(&lkn_z), lkn_z.a, lkn_z.b, lkn_z.d, lkn_z.e, lkn_z.h, lkn_z.l, lkn_z.sp); z80drv_step(&lkn_z); } }
    while (lkn_now(&lkn_z) < Z80.cycles && !lkn_z.bad) z80drv_step(&lkn_z);
    if (lkn_z.bad) { if (lkn_on == 1) fprintf(stderr, "sndnative: recompiled driver left the known code at pc %04X\n", lkn_z.pc); lkn_on = 2; return; }
    { static int dbg = -1, n; if (dbg < 0) { const char *e = getenv("LANDSTALKER_SND_SHADOW"); dbg = e && *e == '2'; } if (dbg && n++ < 60) fprintf(stderr, "sndnative: end %d gpgx cyc %u pc %04X | native cyc %u pc %04X\n", n, Z80.cycles, Z80.pc.w.l, lkn_z.cyc * 15, lkn_z.pc); }
    { static int dbg = -1; if (dbg < 0) { const char *e = getenv("LANDSTALKER_SND_SHADOW"); dbg = e && *e == '7'; } if (dbg && platform_frame_number() >= 3599 && platform_frame_number() <= 3600 && Z80.cycles > 700000) fprintf(stderr, "end f%ld gpgx cyc %u pc %04X sp %04X | native now %u pc %04X sp %04X\n", platform_frame_number(), Z80.cycles, Z80.pc.w.l, Z80.sp.w.l, lkn_now(&lkn_z), lkn_z.pc, lkn_z.sp); }
    lkn_compare();
    if (memcmp(lkn_ram, zram, 0x2000)) { if (lkn_ramdiff++ < 3) { int i; for (i = 0; i < 0x2000 && lkn_ram[i] == zram[i]; i++) ; fprintf(stderr, "sndnative: Z80 RAM differs at %04X (native %02X gpgx %02X) frame %ld\n", i, lkn_ram[i], zram[i], platform_frame_number()); } }
    { static long lastf; long f = platform_frame_number(); if (f / 600 != lastf / 600) { lastf = f; fprintf(stderr, "sndnative: frame %ld events matched %ld mismatched %ld RAM differences %ld\n", f, lkn_match, lkn_mismatch, lkn_ramdiff); } }
}

/* ---- native mode (LANDSTALKER_SND=native): called by z80_run() instead of GPGX's Z80 loop ---- */
static void lkn_to_ctx(void) {   /* the recompiled Z80's registers into GPGX's Z80 struct, so a save state (quick save) carries them */
    Z80.af.b.h = lkn_z.a; Z80.af.b.l = lkn_z.f; Z80.bc.b.h = lkn_z.b; Z80.bc.b.l = lkn_z.c; Z80.de.b.h = lkn_z.d; Z80.de.b.l = lkn_z.e; Z80.hl.b.h = lkn_z.h; Z80.hl.b.l = lkn_z.l;
    Z80.af2.b.h = lkn_z.a2; Z80.af2.b.l = lkn_z.f2; Z80.bc2.b.h = lkn_z.b2; Z80.bc2.b.l = lkn_z.c2; Z80.de2.b.h = lkn_z.d2; Z80.de2.b.l = lkn_z.e2; Z80.hl2.b.h = lkn_z.h2; Z80.hl2.b.l = lkn_z.l2;
    Z80.ix.w.l = lkn_z.ix; Z80.iy.w.l = lkn_z.iy; Z80.sp.w.l = lkn_z.sp; Z80.pc.w.l = lkn_z.pc;
}
static void lkn_from_ctx(void) {
    lkn_z.a = Z80.af.b.h; lkn_z.f = Z80.af.b.l; lkn_z.b = Z80.bc.b.h; lkn_z.c = Z80.bc.b.l; lkn_z.d = Z80.de.b.h; lkn_z.e = Z80.de.b.l; lkn_z.h = Z80.hl.b.h; lkn_z.l = Z80.hl.b.l;
    lkn_z.a2 = Z80.af2.b.h; lkn_z.f2 = Z80.af2.b.l; lkn_z.b2 = Z80.bc2.b.h; lkn_z.c2 = Z80.bc2.b.l; lkn_z.d2 = Z80.de2.b.h; lkn_z.e2 = Z80.de2.b.l; lkn_z.h2 = Z80.hl2.b.h; lkn_z.l2 = Z80.hl2.b.l;
    lkn_z.ix = Z80.ix.w.l; lkn_z.iy = Z80.iy.w.l; lkn_z.sp = Z80.sp.w.l; lkn_z.pc = Z80.pc.w.l;
}
static unsigned lkn_ps_z80; static uint32_t lkn_ps_cyc, lkn_ps_wait;   /* own sound clock (tools/patch_sndclock.py): the sound timeline is put back at the end of a skip frame */
void lk_nat_pause_save(void) { lkn_ps_z80 = Z80.cycles; lkn_ps_cyc = lkn_z.cyc; lkn_ps_wait = lkn_z.wait; }
void lk_nat_pause_restore(void) { Z80.cycles = lkn_ps_z80; lkn_z.cyc = lkn_ps_cyc; lkn_z.wait = lkn_ps_wait; }
/* own sound clock, mailbox FIFO (tools/patch_sndclock.py): the 68K's writes to $1FFC / $1FFD / $1FFF are queued while the sound timeline skips frames; one entry per sound frame goes to the driver once it has taken the last command */
extern int lk_snd_skipping(void);
typedef struct { uint8_t ha, hb, a, b, cmd; } LknCmd;
static LknCmd lkq[256]; static int lkq_n, lkq_head, lkq_ha, lkq_hb, lkq_pa, lkq_pb, lkq_max, lkq_pushed, lkq_given, lkq_dropped;   /* stats: LANDSTALKER_SNDCLOCK_LOG=1 */
int lk_snd_zw(unsigned a, unsigned v) {
    if (a != 0x1FFC && a != 0x1FFD && a != 0x1FFF) return 0;
    if (!lk_snd_skipping() && !lkq_n) return 0;
    if (a == 0x1FFC) { lkq_pa = v; lkq_ha = 1; return 1; }
    if (a == 0x1FFD) { lkq_pb = v; lkq_hb = 1; return 1; }
    lkq_pushed++; if (lkq_n >= 256) lkq_dropped++;
    if (lkq_n < 256) { LknCmd *c = &lkq[(lkq_head + lkq_n++) & 255]; if (lkq_n > lkq_max) lkq_max = lkq_n; c->ha = lkq_ha; c->hb = lkq_hb; c->a = lkq_pa; c->b = lkq_pb; c->cmd = v; }
    lkq_ha = lkq_hb = 0;
    return 1;
}
void lk_snd_deliver(void) {
    static int blocked; LknCmd *c; if (!lkq_n) { blocked = 0; return; }
    if (zram[0x1FFF] && ++blocked < 4) return;   /* the driver has not taken the last command yet; after 3 sound frames overwrite it as the original 68K would */
    blocked = 0; lkq_given++;
    { static int lg = -1; if (lg < 0) lg = getenv("LANDSTALKER_SNDCLOCK_LOG") != NULL; if (lg && !(lkq_given % 20)) fprintf(stderr, "sndclock: commands queued %d delivered %d dropped %d deepest queue %d\n", lkq_pushed, lkq_given, lkq_dropped, lkq_max); }
    c = &lkq[lkq_head]; lkq_head = (lkq_head + 1) & 255; lkq_n--;
    if (c->ha) { lk_nat_ram_w(0x1FFC, c->a); zram[0x1FFC] = c->a; }
    if (c->hb) { lk_nat_ram_w(0x1FFD, c->b); zram[0x1FFD] = c->b; }
    lk_nat_ram_w(0x1FFF, c->cmd); zram[0x1FFF] = c->cmd;
}
void lk_nat_loadctx(void) { if (lkn_native && lkn_active) { lkn_from_ctx(); lkn_z.cyc = Z80.cycles / 15; lkn_z.wait = 0; lkn_z.bad = 0; } lk_nat_pause_save(); lkq_n = lkq_head = lkq_ha = lkq_hb = 0; }   /* after z80_set_context (quick load) */
int lk_nat_native_run(unsigned cycles) {
    if (!lkn_enabled() || !lkn_native || !lkn_active) return 0;
    if (lkn_now(&lkn_z) < Z80.cycles) { lkn_z.cyc = Z80.cycles / 15; lkn_z.wait = 0; }   /* skip the time the Z80 was stopped (bus request / reset) */
    while (lkn_now(&lkn_z) < cycles && !lkn_z.bad) z80drv_step(&lkn_z);
    if (lkn_z.bad) { static int w; if (!w++) fprintf(stderr, "sndnative: recompiled driver left the known code at pc %04X, sound stops\n", lkn_z.pc); lkn_active = 0; return 1; }
    Z80.cycles = lkn_now(&lkn_z); lkn_to_ctx();
    return 1;
}
