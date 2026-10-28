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
extern void z80drv_step(Z80S *s);
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
    return bad ? 1 : 0;
}
