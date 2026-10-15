#include <genrecomp/genrecomp.h>
#include <genrecomp/bus.h>
#include <genrecomp/platform.h>
#include <genrecomp/func_table.h>
#include "recomp_funcs.h"
#include <stdio.h>
int main(int argc, char **argv) {
    argc = platform_parse_args(argc, argv);
    if (!genrecomp_init("t", 1)) return 2;
    if (!genrecomp_load_rom(argv[1])) return 3;
    recomp_register_all();
    g_m68k.a[7] = 0xFFFE00;
    func_table_jsr(0x200, 0);
    FILE *f = fopen(argv[2], "wb"); bus_dump_state(f); fclose(f);
    return 0;
}
