#include <genrecomp/genrecomp.h>
#include <genrecomp/bus.h>
#include <genrecomp/platform.h>
#include <genrecomp/func_table.h>
#include "recomp_funcs.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
    argc = platform_parse_args(argc, argv);
    if (!genrecomp_init("lz", 1)) return 2;
    if (!genrecomp_load_rom("test.bin")) return 3;
    recomp_register_all();
    FILE *f = fopen("orig.bin", "rb"); static uint8_t orig[1 << 16];
    size_t n = fread(orig, 1, sizeof orig, f); fclose(f);
    g_m68k.a[7] = 0xFFFE00;
    g_m68k.a[0] = 0x10000;       /* compressed data in ROM */
    g_m68k.a[1] = 0xFF2000;      /* output buffer in work RAM */
    for (int i = 0; i < 4096; i++) bus_write8(0xFF2000 + i, 0xAA);   /* guard fill */
    func_table_jsr(0x4AB2, 0);
    size_t bad = 0, first = (size_t)-1;
    for (size_t i = 0; i < n; i++)
        if (bus_read8(0xFF2000 + i) != orig[i]) { if (first == (size_t)-1) first = i; bad++; }
    printf("decoded end a1=$%06X (expected $%06zX), a0=$%06X\n", g_m68k.a[1], 0xFF2000 + n, g_m68k.a[0]);
    printf("%zu of %zu bytes differ", bad, n);
    if (bad) printf(" (first at %zu: got %02X want %02X)", first, bus_read8(0xFF2000 + first), orig[first]);
    printf("\n%s\n", bad || g_m68k.a[1] != 0xFF2000 + n ? "FAIL" : "PASS");
    return bad != 0;
}
