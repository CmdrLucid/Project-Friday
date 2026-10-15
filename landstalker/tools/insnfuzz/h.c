/* Differential instruction test: GPGX Musashi interpreter vs recompiled C. See mk.py / README.md. */
#include <genrecomp/genrecomp.h>
#include <genrecomp/bus.h>
#include <genrecomp/platform.h>
#include <genrecomp/func_table.h>
#include "recomp_funcs.h"
#include "shared.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint64_t rs = 88172645463325252ULL;
static uint64_t rnd64(void) { rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }
static uint8_t pool[1 << 20];
static uint8_t dummy[65536];
static void nop_w8(unsigned int a, unsigned int d) { (void)a; (void)d; }
static void nop_w16(unsigned int a, unsigned int d) { (void)a; (void)d; }

typedef struct { uint32_t d[8], a[8]; uint8_t ccr; } Regs;
typedef struct { Regs r; uint8_t ram[65536]; uint8_t dum[65536]; } Snap;

static uint32_t pick(int even) {
    uint32_t v;
    switch (rnd64() % 5) {
    case 0: v = (uint32_t)rnd64(); break;
    case 1: v = (uint32_t)(rnd64() % 256); break;
    case 2: { static const uint32_t e[] = {0, 1, 0x7F, 0x80, 0xFF, 0x7FFF, 0x8000, 0xFFFF, 0x7FFFFFFF, 0x80000000u, 0xFFFFFFFFu, 0xFFFF0000u, 0x10000};
              v = e[rnd64() % (sizeof(e) / sizeof(e[0]))]; break; }
    case 3: v = (uint32_t)(rnd64() & 0xFFFF); break;
    default: v = (uint32_t)(int32_t)(int8_t)(rnd64() & 0xFF); break;
    }
    return even ? (v & ~1u) : v;
}

static void make_state(Snap *s, int memop) {
    for (int i = 0; i < 8; i++) s->r.d[i] = pick(memop);
    for (int i = 0; i < 7; i++) s->r.a[i] = 0xFF8000 + (((int32_t)(rnd64() % 0x4000) - 0x2000) & ~1);
    s->r.a[7] = 0xFFE000;
    s->r.ccr = (uint8_t)(rnd64() & 0x1F);
    uint32_t off = (uint32_t)(rnd64() % (sizeof(pool) - 131072)) & ~1u;
    memcpy(s->ram, pool + off, 65536);
    memcpy(s->dum, pool + off + 65536, 65536);
}
static void load_mem(const Snap *s) { memcpy(bus_get_ram(), s->ram, 65536); memcpy(dummy, s->dum, 65536); }
static void save_mem(Snap *s) { memcpy(s->ram, bus_get_ram(), 65536); memcpy(s->dum, dummy, 65536); }

static int g_lenmismatch;
static int run_interp(const Snap *in, Snap *out, uint32_t pc, uint32_t next) {
    load_mem(in);
    m68k_set_reg(M68K_REG_SR, 0x2700 | in->r.ccr);
    for (int i = 0; i < 8; i++) { m68k_set_reg(M68K_REG_D0 + i, in->r.d[i]); m68k_set_reg(M68K_REG_A0 + i, in->r.a[i]); }
    m68k_set_reg(M68K_REG_PC, pc);
    m68k.int_level = 0; m68k.stopped = 0;   /* an earlier double fault would leave the interpreter halted */
    unsigned int c0 = m68k.cycles; m68k_run(m68k.cycles + 1);
    { static int dd; if (m68k_get_reg(M68K_REG_PC) == pc && dd++ < 4) fprintf(stderr, "no progress: cycles %u -> %u cycle_end=%u stopped=%d pc=%06X\n", c0, m68k.cycles, m68k.cycle_end, (int)m68k.stopped, pc); }
    if ((m68k_get_reg(M68K_REG_PC) & 0xFFFFFF) != next) {   /* exception (address error, zero divide, ...) */
        uint32_t npc = m68k_get_reg(M68K_REG_PC) & 0xFFFFFF;
        if (npc != 0x300) { g_lenmismatch = 1; static int dbg; if (dbg++ < 8) fprintf(stderr, "length mismatch: pc=%06X expected %06X at %06X\n", npc, next, pc); }
        return 0;
    }
    for (int i = 0; i < 8; i++) { out->r.d[i] = m68k_get_reg(M68K_REG_D0 + i); out->r.a[i] = m68k_get_reg(M68K_REG_A0 + i); }
    out->r.ccr = (uint8_t)(m68k_get_reg(M68K_REG_SR) & 0x1F);
    save_mem(out);
    return 1;
}
static void run_rec(const Snap *in, Snap *out, uint32_t pc) {
    load_mem(in);
    for (int i = 0; i < 8; i++) { g_m68k.d[i] = in->r.d[i]; g_m68k.a[i] = in->r.a[i]; }
    m68k_set_sr(0x2700 | in->r.ccr);
    func_table_jsr(pc, 0x000002);
    for (int i = 0; i < 8; i++) { out->r.d[i] = g_m68k.d[i]; out->r.a[i] = g_m68k.a[i]; }
    out->r.ccr = (uint8_t)(m68k_get_sr() & 0x1F);
    save_mem(out);
    memcpy(out->ram + 0xDFFC, in->ram + 0xDFFC, 4);   /* undo the return address pushed by func_table_jsr */
}

int main(int argc, char **argv) {
    argc = platform_parse_args(argc, argv);
    if (argc < 3) { fprintf(stderr, "usage: fuzz rom.bin tests.txt [trials] [seed]\n"); return 2; }
    int trials = argc > 3 ? atoi(argv[3]) : 6;
    if (argc > 4) rs ^= (uint64_t)atoll(argv[4]) * 0x9E3779B97F4A7C15ULL;
    if (!genrecomp_init("t", 1)) return 2;
    if (!genrecomp_load_rom(argv[1])) return 3;
    recomp_register_all();
    for (int r = 0x10; r < 0xE0; r++) { m68k.memory_map[r].base = dummy; m68k.memory_map[r].read8 = NULL; m68k.memory_map[r].read16 = NULL; m68k.memory_map[r].write8 = NULL; m68k.memory_map[r].write16 = NULL; }
    for (int r = 0; r < 0x10; r++) { m68k.memory_map[r].write8 = nop_w8; m68k.memory_map[r].write16 = nop_w16; }
    for (size_t i = 0; i < sizeof(pool); i += 8) { uint64_t v = rnd64(); memcpy(pool + i, &v, 8); }
    FILE *f = fopen(argv[2], "r");
    if (!f) return 4;
    static Snap in, a, b;
    char line[512]; int tested = 0, skipped = 0, bad = 0, badtests = 0;
    while (fgets(line, sizeof line, f)) {
        unsigned idx, addr, len, memop;
        if (sscanf(line, "%u %x %u %u", &idx, &addr, &len, &memop) != 4) continue;
        int tbad = 0; g_lenmismatch = 0;
        for (int t = 0; t < trials && !g_lenmismatch; t++) {
            make_state(&in, (int)memop);
            if (!run_interp(&in, &a, addr, addr + len)) { skipped++; continue; }
            run_rec(&in, &b, addr);
            tested++;
            char msg[400]; msg[0] = 0; int n = 0;
            for (int i = 0; i < 8; i++) {
                if (a.r.d[i] != b.r.d[i]) n += snprintf(msg + n, sizeof msg - n, " d%d %08X/%08X", i, a.r.d[i], b.r.d[i]);
                if (a.r.a[i] != b.r.a[i]) n += snprintf(msg + n, sizeof msg - n, " a%d %08X/%08X", i, a.r.a[i], b.r.a[i]);
            }
            if (a.r.ccr != b.r.ccr) n += snprintf(msg + n, sizeof msg - n, " ccr(XNZVC) %02X/%02X", a.r.ccr, b.r.ccr);
            if (memcmp(a.ram, b.ram, 65536)) { for (int i = 0; i < 65536; i++) if (a.ram[i] != b.ram[i]) { n += snprintf(msg + n, sizeof msg - n, " ram[%04X] %02X/%02X", i ^ 1, a.ram[i], b.ram[i]); break; } }
            if (memcmp(a.dum, b.dum, 65536)) { for (int i = 0; i < 65536; i++) if (a.dum[i] != b.dum[i]) { n += snprintf(msg + n, sizeof msg - n, " dummy[%04X] %02X/%02X", i ^ 1, a.dum[i], b.dum[i]); break; } }
            if (n) {
                printf("MISMATCH %u in:d=%08X,%08X,%08X,%08X,%08X,%08X,%08X,%08X a=%08X,%08X,%08X,%08X,%08X,%08X,%08X ccr=%02X |%s  (interp/rec)\n", idx, in.r.d[0], in.r.d[1], in.r.d[2], in.r.d[3], in.r.d[4], in.r.d[5], in.r.d[6], in.r.d[7], in.r.a[0], in.r.a[1], in.r.a[2], in.r.a[3], in.r.a[4], in.r.a[5], in.r.a[6], in.r.ccr, msg);
                bad++; tbad = 1;
            }
        }
        badtests += tbad;
    }
    printf("SUMMARY tested=%d skipped(exception)=%d mismatching_trials=%d mismatching_instructions=%d\n", tested, skipped, bad, badtests);
    return 0;
}
