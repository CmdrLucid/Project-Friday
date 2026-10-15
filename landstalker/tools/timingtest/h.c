#include <genrecomp/genrecomp.h>
#include <genrecomp/bus.h>
#include <genrecomp/platform.h>
#include <genrecomp/func_table.h>
#include "recomp_funcs.h"
#include <stdio.h>
#include <stdlib.h>
static void vb(void) {
    if (!genrecomp_begin_frame()) { genrecomp_shutdown(); exit(0); }
    genrecomp_vblank_irq();
    genrecomp_end_frame();
}
int main(int argc, char **argv) {
    argc = platform_parse_args(argc, argv);
    if (!genrecomp_init("t", 1)) return 2;
    if (!genrecomp_load_rom(argv[1])) return 3;
    recomp_register_all();
    bus_set_vblank_callback(vb);
    g_m68k.a[7] = bus_read32(0); g_m68k.pc = bus_read32(4); m68k_set_sr(0x2700);
    func_table_call(g_m68k.pc);
    return 0;
}
