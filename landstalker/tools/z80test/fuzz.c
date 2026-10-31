/* fuzz.c -- differential test of the Z80 recompiler (tools/z80recomp.py): every instruction of the generated driver is executed with random register state / memory on BOTH the generated
   code and GPGX's own Z80 core (z80/z80.c), and registers, flags (incl. the undocumented bits), cycles, pc and the list of memory writes are compared.  Usage: fuzz ROM [cases_per_instruction=64] [seed]
   (see tools/z80test/run.sh).  The ROM is read only for the driver image (not committed anywhere). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "shared.h"
#include "z80.h"
#include "z80rt.h"

static uint8_t memG[65536], memR[65536];
typedef struct { uint16_t a; uint8_t v; uint32_t t; } wr_t;
static wr_t wg[16], wrr[16]; static int ng, nr;
static unsigned char rdG(unsigned int a) { return memG[a & 0xFFFF]; }
static void wtG(unsigned int a, unsigned char v) { if (ng < 16) { wg[ng].a = a & 0xFFFF; wg[ng].v = v; wg[ng].t = Z80.cycles / 15; ng++; } memG[a & 0xFFFF] = v; }
uint8_t z80rt_rb(Z80S *s, uint16_t a) { (void)s; return memR[a]; }
void z80rt_wb(Z80S *s, uint16_t a, uint8_t v) { (void)s; if (nr < 16) { wrr[nr].a = a; wrr[nr].v = v; wrr[nr].t = s->cyc; nr++; } memR[a] = v; }
static unsigned char rdport(unsigned int p) { (void)p; return 0xFF; }
static void wrport(unsigned int p, unsigned char v) { (void)p; (void)v; }
static uint32_t rng = 1;
static uint32_t rnd(void) { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return rng; }
extern void z80drv_step(Z80S *s); extern void z80boot_step(Z80S *s); extern const unsigned char z80boot_img[]; extern const int z80boot_len;
int lk_snd_skipping(void) { return 0; } int lk_nat_native_run(unsigned c) { (void)c; return 0; } void lk_nat_loadctx(void) {}   /* hooks of the later patches (sndclock, native run) */
void lk_nat_begin(void) {} void lk_nat_gstep(void) {} void lk_nat_end(void) {} void lk_nat_reset(void) {} void lk_nat_gevent(int k, uint32_t t, int a, int v) {}   /* stubs for the hooks of a patched z80.c (tools/patch_sndnative.py) */

int main(int argc, char **argv) {
    FILE *f = fopen(argv[1], "rb"); static uint8_t rom[0x200000]; int cases = argc > 2 ? atoi(argv[2]) : 64; long bad = 0, tot = 0; int pcs[0x2000], npc = 0, i, k;
    if (argc > 3) rng = (uint32_t)atol(argv[3]) | 1;
    if (!f || fread(rom, 1, sizeof rom, f) < 0x1F7F80) { fprintf(stderr, "ROM?\n"); return 2; } fclose(f);
    uint8_t img[0x1F80]; memcpy(img, rom + 0x1F6000, 0x1F80);
    /* the instruction addresses: ask the generated switch (z80drv_step with bad flag for unknown pcs) */
    for (i = 0; i < 0x2000; i++) { Z80S t; memset(&t, 0, sizeof t); t.pc = (uint16_t)i; memset(memR, 0, 65536); memcpy(memR, img, 0x1F80); z80drv_step(&t); if (!t.bad) pcs[npc++] = i; }
    printf("instructions in the generated driver: %d\n", npc);
    z80_init(0, 0); z80_readmem = rdG; z80_writemem = wtG; z80_readport = rdport; z80_writeport = wrport;
    for (i = 0; i < 64; i++) z80_readmap[i] = &memG[i * 1024];
    for (i = 0; i < npc; i++) {
        for (k = 0; k < cases; k++) {
            Z80S s; int j; memset(&s, 0, sizeof s);
            for (j = 0; j < 65536; j++) memG[j] = (uint8_t)rnd();
            memcpy(memG, img, 0x1F80);
            if (k & 1) { for (j = 0x1F80; j < 0x2000; j++) memG[j] = (uint8_t)(rnd() & 0x3); }   /* small values: more likely loops / zero results */
            memcpy(memR, memG, 65536);
            s.a = rnd(); s.f = rnd(); s.b = rnd(); s.c = rnd(); s.d = rnd(); s.e = rnd(); s.h = rnd(); s.l = rnd(); s.a2 = rnd(); s.f2 = rnd(); s.b2 = rnd(); s.c2 = rnd(); s.d2 = rnd(); s.e2 = rnd(); s.h2 = rnd(); s.l2 = rnd();
            s.ix = rnd(); s.iy = rnd(); s.sp = (rnd() & 1) ? 0x1F00 + (rnd() & 0xFE) : rnd(); s.pc = (uint16_t)pcs[i];
            if (k % 5 == 0) { s.a = (k & 2) ? 0 : 0x80; s.b = (k & 4) ? 1 : s.b; }   /* edge values */
            /* GPGX state */
            z80_reset(); memset(&Z80.af, 0, 0); Z80.af.b.h = s.a; Z80.af.b.l = s.f; Z80.bc.b.h = s.b; Z80.bc.b.l = s.c; Z80.de.b.h = s.d; Z80.de.b.l = s.e; Z80.hl.b.h = s.h; Z80.hl.b.l = s.l;
            Z80.af2.b.h = s.a2; Z80.af2.b.l = s.f2; Z80.bc2.b.h = s.b2; Z80.bc2.b.l = s.c2; Z80.de2.b.h = s.d2; Z80.de2.b.l = s.e2; Z80.hl2.b.h = s.h2; Z80.hl2.b.l = s.l2;
            Z80.ix.w.l = s.ix; Z80.iy.w.l = s.iy; Z80.sp.w.l = s.sp; Z80.pc.w.l = s.pc; Z80.cycles = 0; Z80.iff1 = Z80.iff2 = 0; Z80.irq_state = 0;
            ng = 0; nr = 0;
            z80_run(1); z80drv_step(&s);
            int diff = 0;
            #define CMP(name, gv, rv) if ((unsigned)(gv) != (unsigned)(rv)) { diff = 1; if (bad < 25) printf("  %04X: %s differs: gpgx %X recomp %X\n", pcs[i], name, (unsigned)(gv), (unsigned)(rv)); }
            CMP("A", Z80.af.b.h, s.a); CMP("F", Z80.af.b.l, s.f); CMP("B", Z80.bc.b.h, s.b); CMP("C", Z80.bc.b.l, s.c); CMP("D", Z80.de.b.h, s.d); CMP("E", Z80.de.b.l, s.e); CMP("H", Z80.hl.b.h, s.h); CMP("L", Z80.hl.b.l, s.l);
            CMP("A'", Z80.af2.b.h, s.a2); CMP("F'", Z80.af2.b.l, s.f2); CMP("B'", Z80.bc2.b.h, s.b2); CMP("C'", Z80.bc2.b.l, s.c2); CMP("D'", Z80.de2.b.h, s.d2); CMP("E'", Z80.de2.b.l, s.e2); CMP("H'", Z80.hl2.b.h, s.h2); CMP("L'", Z80.hl2.b.l, s.l2);
            CMP("IX", Z80.ix.w.l, s.ix); CMP("IY", Z80.iy.w.l, s.iy); CMP("SP", Z80.sp.w.l, s.sp); CMP("PC", Z80.pc.w.l, s.pc); CMP("cycles", Z80.cycles / 15, s.cyc);
            CMP("nwrites", ng, nr);
            if (ng == nr) for (j = 0; j < ng; j++) { CMP("write addr", wg[j].a, wrr[j].a); CMP("write val", wg[j].v, wrr[j].v); if (wg[j].a >= 0x4000) CMP("write time", wg[j].t, wrr[j].t); }
            tot++; if (diff) bad++;
        }
    }
    printf("cases %ld, differing %ld\n", tot, bad);
    /* ---- the SEGA boot stub (z80boot_step, 2026-10-31): every instruction with random state, then the whole program from a reset to its jp (hl) loop ---- */
    { long btot = 0, bbad = 0; int bp[64], nb = 0;
      for (i = 0; i < z80boot_len && z80boot_len > 1; i++) { Z80S t; memset(&t, 0, sizeof t); t.pc = (uint16_t)i; memset(memR, 0, 65536); memcpy(memR, z80boot_img, z80boot_len); z80boot_step(&t); if (!t.bad) bp[nb++] = i; }
      printf("instructions in the boot stub: %d\n", nb);
      #define BCMP(name, gv, rv) if ((unsigned)(gv) != (unsigned)(rv)) { diff = 1; if (bbad < 25) printf("  boot %04X: %s differs: gpgx %X recomp %X\n", s.pc, name, (unsigned)(gv), (unsigned)(rv)); }
      for (int run = 0; run <= nb * cases; run++) {
          Z80S s; int j, diff = 0, whole = run == nb * cases; memset(&s, 0, sizeof s);
          if (whole) { memset(memG, 0, 65536); memcpy(memG, z80boot_img, z80boot_len); }
          else { for (j = 0; j < 65536; j++) memG[j] = (uint8_t)rnd(); memcpy(memG, z80boot_img, z80boot_len); s.pc = (uint16_t)bp[run / cases]; }
          memcpy(memR, memG, 65536);
          z80_reset();
          if (!whole) { Z80.af.b.h = s.a = rnd(); Z80.af.b.l = s.f = rnd(); Z80.bc.b.h = s.b = rnd(); Z80.bc.b.l = s.c = rnd(); Z80.de.b.h = s.d = rnd(); Z80.de.b.l = s.e = rnd(); Z80.hl.b.h = s.h = rnd(); Z80.hl.b.l = s.l = rnd();
              if (run & 1) { Z80.bc.b.h = s.b = 0; Z80.bc.b.l = s.c = 1 + (rnd() & 1); }   /* LDIR: last and second last transfer */
              Z80.af2.b.h = s.a2 = rnd(); Z80.af2.b.l = s.f2 = rnd(); Z80.bc2.w.l = 0; s.b2 = s.c2 = 0; Z80.de2.b.h = s.d2 = rnd(); Z80.de2.b.l = s.e2 = rnd(); Z80.hl2.b.h = s.h2 = rnd(); Z80.hl2.b.l = s.l2 = rnd();
              Z80.ix.w.l = s.ix = rnd(); Z80.iy.w.l = s.iy = rnd(); Z80.sp.w.l = s.sp = (uint16_t)rnd(); Z80.pc.w.l = s.pc; }
          else { s.a = Z80.af.b.h; s.f = Z80.af.b.l; s.b = Z80.bc.b.h; s.c = Z80.bc.b.l; s.d = Z80.de.b.h; s.e = Z80.de.b.l; s.h = Z80.hl.b.h; s.l = Z80.hl.b.l; s.a2 = Z80.af2.b.h; s.f2 = Z80.af2.b.l; s.b2 = Z80.bc2.b.h; s.c2 = Z80.bc2.b.l;
              s.d2 = Z80.de2.b.h; s.e2 = Z80.de2.b.l; s.h2 = Z80.hl2.b.h; s.l2 = Z80.hl2.b.l; s.ix = Z80.ix.w.l; s.iy = Z80.iy.w.l; s.sp = Z80.sp.w.l; s.pc = Z80.pc.w.l; s.i = Z80.i; s.im = Z80.im; }
          Z80.cycles = 0; Z80.iff1 = Z80.iff2 = 0; Z80.irq_state = 0; s.iff1 = s.iff2 = 0; ng = nr = 0;
          if (whole) { z80_run(200000 * 15); while (s.cyc < Z80.cycles / 15 && !s.bad) z80boot_step(&s); }   /* clears 8 KB (~170 000 cycles), then loops on the written jp (hl) */
          else { z80_run(1); z80boot_step(&s); }
          BCMP("A", Z80.af.b.h, s.a); BCMP("F", Z80.af.b.l, s.f); BCMP("BC", Z80.bc.w.l, (s.b << 8) | s.c); BCMP("DE", Z80.de.w.l, (s.d << 8) | s.e); BCMP("HL", Z80.hl.w.l, (s.h << 8) | s.l);
          BCMP("AF'", Z80.af2.w.l, (s.a2 << 8) | s.f2); BCMP("BC'", Z80.bc2.w.l, (s.b2 << 8) | s.c2); BCMP("DE'", Z80.de2.w.l, (s.d2 << 8) | s.e2); BCMP("HL'", Z80.hl2.w.l, (s.h2 << 8) | s.l2);
          BCMP("IX", Z80.ix.w.l, s.ix); BCMP("IY", Z80.iy.w.l, s.iy); BCMP("SP", Z80.sp.w.l, s.sp); BCMP("PC", Z80.pc.w.l, s.pc); BCMP("I", Z80.i, s.i); BCMP("IM", Z80.im, s.im); BCMP("cycles", Z80.cycles / 15, s.cyc); BCMP("bad", 0, s.bad);
          if (whole) { BCMP("memory", 0, memcmp(memG, memR, 65536) != 0); printf("whole boot stub from reset: %u cycles, pc %04X, sp %04X, mem[0] %02X: %s\n", s.cyc, s.pc, s.sp, memR[0], diff ? "DIFFERS" : "same as GPGX"); }
          else { BCMP("nwrites", ng, nr); if (ng == nr) for (j = 0; j < ng; j++) { BCMP("write addr", wg[j].a, wrr[j].a); BCMP("write val", wg[j].v, wrr[j].v); } }
          btot++; if (diff) bbad++;
      }
      printf("boot stub cases %ld, differing %ld\n", btot, bbad); bad += bbad; }
    return bad ? 1 : 0;
}
