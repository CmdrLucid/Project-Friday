/*
 * Landstalker -- statically recompiled with genrecomp.
 *
 * Structure follows sp00nznet/genchaos: entry, stack and VBlank come from the
 * ROM's vector table; the frame is driven from genrecomp's scanline clock.
 * Untested against a real run: see README.md for the bring-up loop.
 */

#include <genrecomp/genrecomp.h>
#include <genrecomp/bus.h>
#include <genrecomp/input.h>
#include <genrecomp/platform.h>
#include <genrecomp/func_table.h>
#include "recomp/recomp_funcs.h"
#include <stdio.h>
#include <stdlib.h>

static int s_frame_count = 0;

/* LANDSTALKER_SHOT=1: print the frame as a 64x28 letter grid + color legend */
static void dump_frame_ascii(void) {
    const uint8_t *fb = genrecomp_get_framebuffer();
    if (!fb) return;
    uint32_t cols[16]; unsigned long cnt[16]; int n = 0;
    char grid[28][65];
    for (int gy = 0; gy < 28; gy++) {
        for (int gx = 0; gx < 64; gx++) {
            const uint8_t *px = fb + ((gy * 8 + 4) * 320 + (gx * 5 + 2)) * 4;
            uint32_t c = px[0] | (px[1] << 8) | (px[2] << 16);
            int k = 0;
            while (k < n && cols[k] != c) k++;
            if (k == n && n < 16) { cols[n] = c; cnt[n] = 0; n++; }
            if (k < n) cnt[k]++;
            grid[gy][gx] = (k < 16) ? (char)('A' + k) : '?';
        }
        grid[gy][64] = 0;
    }
    printf("--- frame %d ---\n", s_frame_count);
    for (int gy = 0; gy < 28; gy++) puts(grid[gy]);
    for (int k = 0; k < n; k++)
        printf("%c = bytes %02X %02X %02X (%lu cells)\n", 'A' + k,
               cols[k] & 255, (cols[k] >> 8) & 255, (cols[k] >> 16) & 255, cnt[k]);
    fflush(stdout);
}

static void landstalker_vblank(void) {
    /* Input first, so the handler reads fresh pad state */
    if (!genrecomp_begin_frame()) {
        printf("\nWindow closed, exiting.\n");
        genrecomp_shutdown();
        exit(0);
    }
    genrecomp_vblank_irq();   /* the game's level-6 handler, context saved */
    genrecomp_end_frame();

    s_frame_count++;
    if (getenv("LANDSTALKER_SHOT") &&
        (s_frame_count == 90 || s_frame_count == 300 || s_frame_count == 540))
        dump_frame_ascii();
    /* LANDSTALKER_STACK=1: where is the main thread, every second */
    if (getenv("LANDSTALKER_STACK") && s_frame_count % 60 == 0) {
        printf("Frame %d (SP=$%08X) ", s_frame_count, g_m68k.a[7]);
        func_table_dump_stack(stdout);
        fflush(stdout);
    }
}

int main(int argc, char *argv[]) {
    argc = platform_parse_args(argc, argv);

    printf("Landstalker -- Static Recompilation\n\n");
    if (!genrecomp_init("Landstalker (Recompiled)", 3)) {
        fprintf(stderr, "Failed to initialize genrecomp\n");
        return 1;
    }

    const char *rom_path = (argc > 1) ? argv[1] : "landstalker.md";
    if (!genrecomp_load_rom(rom_path)) {
        fprintf(stderr, "Failed to load ROM: %s\n", rom_path);
        return 1;
    }

    recomp_register_all();
    bus_set_vblank_callback(landstalker_vblank);

    /* Reset: stack and entry from the vector table, interrupts masked */
    g_m68k.a[7] = bus_read32(0);
    g_m68k.pc = bus_read32(4);
    m68k_set_sr(0x2700);

    func_table_call(g_m68k.pc);

    extern void lk_rts_dump(const char *why);
    lk_rts_dump("entry point returned unexpectedly; last returns:");
    printf("The game's entry point returned unexpectedly\n");
    genrecomp_shutdown();
    return 0;
}
