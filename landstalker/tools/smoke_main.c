/* CI smoke test (no ROM, no game code): initialise genrecomp, load the dummy ROM (tools/make_dummy_rom.py), run a few frames and shut down,
 * so that the battery RAM file (<rom>.srm) is written on the first run and read again on the second. Built by `zigbuild.py --smoke`. */
#include "genrecomp/genrecomp.h"
#include <stdio.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#include <dbghelp.h>
/* a crash prints WHERE (fault address, nearest known function below it, address that was accessed) instead of only the exit code */
extern int load_rom(), audio_init(), system_init(), system_reset(), md_cart_init(), md_cart_reset(), io_init(), vdp_init(), sound_init(), gen_init(), gen_reset(),
    vdp_reset(), io_reset(), sound_reset(), m68k_init(), m68k_pulse_reset(), sram_init();
#define FN(f) { #f, (void *)f }
static const struct { const char *n; void *a; } s_fn[] = { FN(load_rom), FN(audio_init), FN(system_init), FN(system_reset), FN(md_cart_init), FN(md_cart_reset), FN(io_init),
    FN(vdp_init), FN(sound_init), FN(gen_init), FN(gen_reset), FN(vdp_reset), FN(io_reset), FN(sound_reset), FN(recomp_m68k_reset), FN(m68k_init), FN(m68k_pulse_reset),
    FN(sram_init), FN(genrecomp_load_rom), FN(genrecomp_init) };
/* call stack of the crash (dbghelp.dll loaded at run time, no extra link flag; names only when the program carries COFF symbols, else module + offset) */
static void print_stack(CONTEXT *c0) {
    typedef BOOL (WINAPI *init_t)(HANDLE, PCSTR, BOOL);
    typedef BOOL (WINAPI *walk_t)(DWORD, HANDLE, HANDLE, LPSTACKFRAME64, PVOID, PREAD_PROCESS_MEMORY_ROUTINE64, PFUNCTION_TABLE_ACCESS_ROUTINE64, PGET_MODULE_BASE_ROUTINE64, PTRANSLATE_ADDRESS_ROUTINE64);
    typedef BOOL (WINAPI *sym_t)(HANDLE, DWORD64, PDWORD64, PSYMBOL_INFO);
    HMODULE d = LoadLibraryA("dbghelp.dll"); HANDLE pr = GetCurrentProcess(), th = GetCurrentThread();
    init_t init; walk_t walk; sym_t sym; PFUNCTION_TABLE_ACCESS_ROUTINE64 fta; PGET_MODULE_BASE_ROUTINE64 gmb; CONTEXT c = *c0; STACKFRAME64 sf; int n;
    if (!d) { fprintf(stderr, "smoke: no dbghelp.dll\n"); return; }
    init = (init_t)GetProcAddress(d, "SymInitialize"); walk = (walk_t)GetProcAddress(d, "StackWalk64"); sym = (sym_t)GetProcAddress(d, "SymFromAddr");
    fta = (PFUNCTION_TABLE_ACCESS_ROUTINE64)GetProcAddress(d, "SymFunctionTableAccess64"); gmb = (PGET_MODULE_BASE_ROUTINE64)GetProcAddress(d, "SymGetModuleBase64");
    if (!init || !walk || !sym || !fta || !gmb) { fprintf(stderr, "smoke: dbghelp functions missing\n"); return; }
    init(pr, NULL, TRUE);
    memset(&sf, 0, sizeof sf);
    sf.AddrPC.Offset = c.Rip; sf.AddrFrame.Offset = c.Rsp; sf.AddrStack.Offset = c.Rsp;
    sf.AddrPC.Mode = sf.AddrFrame.Mode = sf.AddrStack.Mode = AddrModeFlat;
    for (n = 0; n < 24 && walk(IMAGE_FILE_MACHINE_AMD64, pr, th, &sf, &c, NULL, fta, gmb, NULL); n++) {
        char buf[sizeof(SYMBOL_INFO) + 256]; SYMBOL_INFO *si = (SYMBOL_INFO *)buf; DWORD64 disp = 0, a = sf.AddrPC.Offset, mb = gmb(pr, a); char mn[260] = "?";
        HMODULE m = (HMODULE)(size_t)mb; if (m) GetModuleFileNameA(m, mn, sizeof mn);
        memset(buf, 0, sizeof buf); si->SizeOfStruct = sizeof(SYMBOL_INFO); si->MaxNameLen = 255;
        if (sym(pr, a, &disp, si)) fprintf(stderr, "smoke: #%d %s+0x%llX  [%s]\n", n, si->Name, (unsigned long long)disp, strrchr(mn, '\\') ? strrchr(mn, '\\') + 1 : mn);
        else fprintf(stderr, "smoke: #%d %p  [%s +0x%llX]\n", n, (void *)(size_t)a, strrchr(mn, '\\') ? strrchr(mn, '\\') + 1 : mn, (unsigned long long)(a - mb));
        if (!sf.AddrReturn.Offset) break;
    }
}

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
    { HMODULE m = NULL; char nm[260] = "?";
      if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, fa, &m) && m) GetModuleFileNameA(m, nm, sizeof nm);
      fprintf(stderr, "smoke: crash is in module %s (base %p, offset 0x%lX)\n", nm, (void *)m, (unsigned long)(fa - (char *)m)); }
    print_stack(e->ContextRecord);
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
