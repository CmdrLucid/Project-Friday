/* funcdiff: run one ROM function on GPGX's Musashi interpreter and as recompiled C, on the same RAM image, and compare the results.
 *
 *   funcdiff ROM RAMDUMP ENTITY_HEX ADDR_HEX [ADDR_HEX ...] [--trials N] [--seed S] [--mode collision|move|plain]
 *   mode move: like collision, plus a random facing direction (+04 bits 7-6) so the walking step (e.g. $17B50) goes through all four direction blocks.
 *
 * RAMDUMP = a --ram-dump file (first 64 KB = work RAM). ENTITY = the entity struct address (a5 = a0 = ENTITY on entry).
 * mode collision: the entity's position/height fields are randomised before every trial (+12 height, +14/+16 centre, +18/+1A x extent, +1C/+1E y extent)
 *   inside the room's height map, so the collision routines see many different situations. Compared afterwards: d0-d7, a0-a7, X N Z V C, all of work RAM.
 * Build with tools/funcdiff/build.sh (needs the objects of a finished ./build.sh). */
#include <genrecomp/genrecomp.h>
#include <genrecomp/bus.h>
#include <genrecomp/platform.h>
#include <genrecomp/func_table.h>
#include "shared.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "recomp_funcs.h"

static uint64_t rs = 88172645463325252ULL;
static uint64_t rnd64(void) { rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }
#define SENTINEL 0x000FF0u

typedef struct { uint32_t d[8], a[8]; uint8_t ccr; uint8_t ram[65536]; } Snap;

static void put16(uint8_t *ram, uint32_t a, uint16_t v) { ram[(a & 0xFFFF) ^ 1] = (uint8_t)(v >> 8); ram[((a + 1) & 0xFFFF) ^ 1] = (uint8_t)v; }
static uint16_t get16(const uint8_t *ram, uint32_t a) { return (uint16_t)((ram[(a & 0xFFFF) ^ 1] << 8) | ram[((a + 1) & 0xFFFF) ^ 1]); }

static int run_interp(const Snap *in, Snap *out, uint32_t pc) {
    memcpy(bus_get_ram(), in->ram, 65536);
    m68k_set_reg(M68K_REG_SR, 0x2700 | in->ccr);
    for (int i = 0; i < 8; i++) { m68k_set_reg(M68K_REG_D0 + i, in->d[i]); m68k_set_reg(M68K_REG_A0 + i, in->a[i]); }
    /* push the sentinel return address like JSR would */
    uint32_t sp = in->a[7] - 4;
    bus_write32(sp, SENTINEL);
    m68k_set_reg(M68K_REG_A7, sp);
    m68k_set_reg(M68K_REG_PC, pc);
    m68k.int_level = 0; m68k.stopped = 0;
    for (long steps = 0; steps < 2000000; steps++) {
        if ((m68k_get_reg(M68K_REG_PC) & 0xFFFFFF) == SENTINEL) break;
        m68k_run(m68k.cycles + 1);
        if (m68k.stopped) return 0;
    }
    if ((m68k_get_reg(M68K_REG_PC) & 0xFFFFFF) != SENTINEL) return 0;
    for (int i = 0; i < 8; i++) { out->d[i] = m68k_get_reg(M68K_REG_D0 + i); out->a[i] = m68k_get_reg(M68K_REG_A0 + i); }
    out->ccr = (uint8_t)(m68k_get_reg(M68K_REG_SR) & 0x1F);
    memcpy(out->ram, bus_get_ram(), 65536);
    return 1;
}
static void run_rec(const Snap *in, Snap *out, uint32_t pc) {
    memcpy(bus_get_ram(), in->ram, 65536);
    for (int i = 0; i < 8; i++) { g_m68k.d[i] = in->d[i]; g_m68k.a[i] = in->a[i]; }
    m68k_set_sr(0x2700 | in->ccr);
    func_table_jsr(pc, SENTINEL);
    for (int i = 0; i < 8; i++) { out->d[i] = g_m68k.d[i]; out->a[i] = g_m68k.a[i]; }
    out->ccr = (uint8_t)(m68k_get_sr() & 0x1F);
    memcpy(out->ram, bus_get_ram(), 65536);
}

int main(int argc, char **argv) {
    argc = platform_parse_args(argc, argv);
    if (argc < 5) { fprintf(stderr, "usage: funcdiff ROM RAMDUMP ENTITY ADDR... [--trials N] [--seed S] [--mode collision|plain]\n"); return 2; }
    int trials = 2000; const char *mode = "collision"; uint32_t addrs[32]; int na = 0;
    uint32_t ent = (uint32_t)strtoul(argv[3], NULL, 16);
    for (int i = 4; i < argc; i++) {
        if (!strcmp(argv[i], "--trials") && i + 1 < argc) trials = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--seed") && i + 1 < argc) rs ^= (uint64_t)atoll(argv[++i]) * 0x9E3779B97F4A7C15ULL;
        else if (!strcmp(argv[i], "--mode") && i + 1 < argc) mode = argv[++i];
        else if (na < 32) addrs[na++] = (uint32_t)strtoul(argv[i], NULL, 16);
    }
    if (!genrecomp_init("t", 1)) return 2;
    if (!genrecomp_load_rom(argv[1])) return 3;
    recomp_register_all();
    static Snap base, in, a, b;
    FILE *f = fopen(argv[2], "rb");
    if (!f || fread(base.ram, 1, 65536, f) != 65536) { fprintf(stderr, "cannot read RAM dump %s\n", argv[2]); return 4; }
    fclose(f);
    int move = !strcmp(mode, "move");
    int collision = !strcmp(mode, "collision") || move;
    for (int k = 0; k < na; k++) {
        int tested = 0, bad = 0, skipped = 0, blocked = 0;
        for (int t = 0; t < trials; t++) {
            in = base;
            in.ccr = (uint8_t)(rnd64() & 0x1F);
            for (int i = 0; i < 8; i++) in.d[i] = (uint32_t)rnd64() & ((rnd64() & 1) ? 0xFFFF : 0xFFFFFFFF);
            for (int i = 0; i < 7; i++) in.a[i] = 0xFF8000;
            in.a[5] = ent; in.a[0] = ent; in.a[7] = 0xFFE000;
            in.d[0] = ent - 0xFF5400;   /* $3A4 expects the entity offset in d0 */
            if (collision) {
                uint32_t x = (uint32_t)(rnd64() % 0x3C0) + 0x10, y = (uint32_t)(rnd64() % 0x3C0) + 0x10, z = (uint32_t)(rnd64() % 0x400);
                uint32_t w = (rnd64() % 3) ? 0xE : (uint32_t)(rnd64() % 0x20);
                put16(in.ram, ent + 0x12, (uint16_t)z);
                put16(in.ram, ent + 0x14, (uint16_t)(x + w / 2)); put16(in.ram, ent + 0x16, (uint16_t)(y + w / 2));
                put16(in.ram, ent + 0x18, (uint16_t)x); put16(in.ram, ent + 0x1A, (uint16_t)(x + w));
                put16(in.ram, ent + 0x1C, (uint16_t)y); put16(in.ram, ent + 0x1E, (uint16_t)(y + w));
                if (move) in.ram[(ent + 4) & 0xFFFF ^ 1] = (uint8_t)((in.ram[(ent + 4) & 0xFFFF ^ 1] & 0x3F) | ((rnd64() & 3) << 6));   /* random facing direction */
                if (rnd64() & 1) in.ram[(ent + 0x22 + 0) & 0xFFFF ^ 1] &= (uint8_t)~0x10;   /* keep bit 4 of +22 clear most of the time (it disables the test) */
            }
            if (!run_interp(&in, &a, addrs[k])) { skipped++; continue; }
            run_rec(&in, &b, addrs[k]);
            tested++;
            if (!(a.ccr & 1)) { /* carry clear = free */ } else blocked++;
            char msg[512]; int n = 0; msg[0] = 0;
            for (int i = 0; i < 8; i++) {
                if (a.d[i] != b.d[i]) n += snprintf(msg + n, sizeof msg - n, " d%d %08X/%08X", i, a.d[i], b.d[i]);
                if (a.a[i] != b.a[i]) n += snprintf(msg + n, sizeof msg - n, " a%d %08X/%08X", i, a.a[i], b.a[i]);
            }
            if (a.ccr != b.ccr) n += snprintf(msg + n, sizeof msg - n, " ccr %02X/%02X", a.ccr, b.ccr);
            if (memcmp(a.ram, b.ram, 65536)) for (int i = 0; i < 65536; i++) if (a.ram[i] != b.ram[i]) { n += snprintf(msg + n, sizeof msg - n, " ram[%04X] %02X/%02X", i ^ 1, a.ram[i], b.ram[i]); break; }
            if (n) {
                if (bad < 6) printf("MISMATCH at $%06X: x=%04X..%04X y=%04X..%04X z=%04X +22=%02X |%s  (interp/rec)\n", addrs[k],
                    get16(in.ram, ent + 0x18), get16(in.ram, ent + 0x1A), get16(in.ram, ent + 0x1C), get16(in.ram, ent + 0x1E), get16(in.ram, ent + 0x12), in.ram[(ent + 0x22) & 0xFFFF ^ 1], msg);
                bad++;
            }
        }
        printf("SUMMARY $%06X: tested=%d skipped=%d blocked(carry set)=%d mismatching=%d\n", addrs[k], tested, skipped, blocked, bad);
    }
    return 0;
}
