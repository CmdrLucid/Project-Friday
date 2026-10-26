/* CI smoke test (no ROM, no game code): initialise genrecomp, load the dummy ROM (tools/make_dummy_rom.py), run a few frames and shut down,
 * so that the battery RAM file (<rom>.srm) is written on the first run and read again on the second. Built by `zigbuild.py --smoke`. */
#include "genrecomp/genrecomp.h"
#include <stdio.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
/* a crash prints WHERE (fault address, nearest known function below it, address that was accessed) instead of only the exit code */
extern int load_rom(), audio_init(), system_init(), system_reset(), md_cart_init(), md_cart_reset(), io_init(), vdp_init(), sound_init(), gen_init(), gen_reset(),
    vdp_reset(), io_reset(), sound_reset(), recomp_m68k_reset(), m68k_init(), m68k_pulse_reset(), sram_init();
#define FN(f) { #f, (void *)f }
static const struct { const char *n; void *a; } s_fn[] = { FN(load_rom), FN(audio_init), FN(system_init), FN(system_reset), FN(md_cart_init), FN(md_cart_reset), FN(io_init),
    FN(vdp_init), FN(sound_init), FN(gen_init), FN(gen_reset), FN(vdp_reset), FN(io_reset), FN(sound_reset), FN(recomp_m68k_reset), FN(m68k_init), FN(m68k_pulse_reset),
    FN(sram_init), FN(genrecomp_load_rom), FN(genrecomp_init) };
static LONG WINAPI crash_filter(EXCEPTION_POINTERS *e) {
    unsigned i, best = 0; char *fa = (char *)e->ExceptionRecord->ExceptionAddress;
    fprintf(stderr, "smoke: CRASH code 0x%lX at %p, %s address %p\n", e->ExceptionRecord->ExceptionCode, (void *)fa,
            e->ExceptionRecord->ExceptionInformation[0] == 0 ? "reading" : e->ExceptionRecord->ExceptionInformation[0] == 1 ? "writing" : "executing",
            (void *)e->ExceptionRecord->ExceptionInformation[1]);
    for (i = 0; i < sizeof s_fn / sizeof s_fn[0]; i++) {
        fprintf(stderr, "smoke:   %-20s %p\n", s_fn[i].n, s_fn[i].a);
        if ((char *)s_fn[i].a <= fa && (!best || (char *)s_fn[i].a > (char *)s_fn[best - 1].a)) best = i + 1;
    }
    if (best) fprintf(stderr, "smoke: nearest function below the crash: %s + 0x%lX\n", s_fn[best - 1].n, (unsigned long)(fa - (char *)s_fn[best - 1].a));
    fflush(stderr);
    return EXCEPTION_EXECUTE_HANDLER;
}
#endif

int main(int argc, char *argv[]) {
    int i;
#ifdef _WIN32
    SetUnhandledExceptionFilter(crash_filter);
#endif
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc < 2) { fprintf(stderr, "usage: smoke rom\n"); return 2; }
    fprintf(stderr, "smoke: init\n");
    if (!genrecomp_init("smoke", 1)) { fprintf(stderr, "smoke: init failed\n"); return 3; }
    fprintf(stderr, "smoke: load rom %s\n", argv[1]);
    if (!genrecomp_load_rom(argv[1])) { fprintf(stderr, "smoke: load failed\n"); return 4; }
    fprintf(stderr, "smoke: rom loaded\n");
    for (i = 0; i < 130; i++) { if (!genrecomp_begin_frame()) break; genrecomp_end_frame(); }
    fprintf(stderr, "smoke: frames ok\n");
    genrecomp_shutdown();
    fprintf(stderr, "smoke: ok\n");
    return 0;
}
