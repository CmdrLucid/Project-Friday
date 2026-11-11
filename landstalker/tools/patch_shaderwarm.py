#!/usr/bin/env python3
"""LK_SHWARM v1 (2026-11-11, user: 'pruef mal warum manchmal beim Save laden das Spiel sehr sehr lange laedt' -> 'Loesung bauen, notfalls auch einen
Ladescreen der die Shader compiled vor dem eigentlichen Titelscreen'): SHADER WARM-UP before the title screen.

Cause (HANDOFF 0a394): the GPU light programs were compiled on the spot at the first LIT frame after LoadGame: on the Deck with a cold Mesa shader
cache the light block pass ~6 s + bounce ~12.5 s = one frame of 18.5 s; with a warm cache 0.2 s.  The cache is cold after every build that changed
shader text, after SteamOS / Mesa updates and on a tester's first run.

Fix: at the FIRST presented frame (before the SEGA logo / title) every big GPU program is compiled and linked once from the SAME source strings
(GPU light lk_glt_fs, light block pass lk_g5_fs, model buffer lk_gm_*, shadow map lk_gs_*, bounce lk_gb_fs when Bounce Light is On, picture composition
lk_gc_fs) - all started at once without asking for the result (the driver compiles them in its own threads; GL_KHR_parallel_shader_compile tells when
each is done).  When everything is done within 0.25 s (warm cache) nothing is shown; otherwise a LOADING SCREEN (black, 'PREPARING LIGHTING', a bar
growing with the finished programs) is drawn until all are done.  The programs are deleted afterwards: the driver's shader cache now holds them, so the
real initialisations later (first lit frame) take milliseconds.  Nothing in the emulation changes (it runs before the first frame is shown, all
frames identical); only with an OpenGL window, GPU Filters On and Lighting On.  LANDSTALKER_SHWARM=0 switches it off (test aid: the old behaviour); LANDSTALKER_SHWARM_SHOT=file.bmp saves the loading screen
(test aid).
One console line: 'shwarm: N programs ready in X ms (parallel yes|no, loading screen yes|no)'."""
import sys, os

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else ".deps/genrecomp"
    p = os.path.join(root, "src", "platform_sdl.c"); s = open(p).read()
    if "LK_SHWARM v1" in s: print("platform_sdl.c already patched: LK_SHWARM v1"); return
    for need in ("lk_glt_fs", "lk_g5_fs", "lk_gb_fs", "lk_gm_fs", "lk_gs_fs", "lk_gc_fs", "static int lk_gpu_init(void)", "static const uint8_t *lk_glyph(char c)"):
        assert need in s, "platform_sdl.c: %s not found (patch_gpu / patch_gpulight / patch_gpucomp / patch_display first)" % need
    a = "void platform_present_frame(const uint8_t *framebuffer) {\n"
    assert s.count(a) == 1, "platform_sdl.c: platform_present_frame layout changed"
    MODULE = r'''/* ---- LK_SHWARM v1: shader warm-up / loading screen before the title (tools/patch_shaderwarm.py) ---- */
extern int lk_lt_get(void); extern int lk_bl_get(void); extern const char *lk_lang_tr(const char *en);
static void lk_shw_screen(int done, int total) {   /* black screen, 'PREPARING LIGHTING' in the hint font, a bar of done / total */
    int ow = 0, oh = 0, px, n, tw, x0, y0, i, r, c, bw, bh, bx, by; const char *t = lk_lang_tr("PREPARING LIGHTING");
    SDL_GetRendererOutputSize(s_renderer, &ow, &oh); if (ow < 64 || oh < 64) return;
    px = oh / 150; if (px < 2) px = 2; n = (int)strlen(t); tw = (n * 6 - 1) * px; x0 = (ow - tw) / 2; y0 = oh / 2 - 9 * px;
    SDL_SetRenderDrawBlendMode(s_renderer, SDL_BLENDMODE_NONE); SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 255); SDL_RenderClear(s_renderer);
    SDL_SetRenderDrawColor(s_renderer, 230, 222, 200, 255);
    for (i = 0; i < n; i++) { const uint8_t *g = lk_glyph(t[i]);
        for (r = 0; r < 7; r++) for (c = 0; c < 5; c++) if (g[r] & (0x10 >> c)) { SDL_Rect d = { x0 + (i * 6 + c) * px, y0 + r * px, px, px }; SDL_RenderFillRect(s_renderer, &d); } }
    bw = tw; bh = 2 * px; bx = x0; by = y0 + 11 * px;
    { SDL_Rect fr = { bx - px, by - px, bw + 2 * px, bh + 2 * px }; SDL_SetRenderDrawColor(s_renderer, 90, 86, 76, 255); SDL_RenderFillRect(s_renderer, &fr); }
    { SDL_Rect in = { bx, by, bw, bh }; SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 255); SDL_RenderFillRect(s_renderer, &in); }
    { SDL_Rect f = { bx, by, total > 0 ? bw * done / total : 0, bh }; SDL_SetRenderDrawColor(s_renderer, 230, 222, 200, 255); if (f.w > 0) SDL_RenderFillRect(s_renderer, &f); }
    { static int sv; const char *e = getenv("LANDSTALKER_SHWARM_SHOT"); if (e && !sv && done * 2 >= total) { SDL_Surface *sf = SDL_CreateRGBSurfaceWithFormat(0, ow, oh, 32, SDL_PIXELFORMAT_ARGB8888); sv = 1;   /* test aid: the loading screen as BMP */
        if (sf) { SDL_RenderReadPixels(s_renderer, NULL, SDL_PIXELFORMAT_ARGB8888, sf->pixels, sf->pitch); SDL_SaveBMP(sf, e); SDL_FreeSurface(sf); } } }
    SDL_RenderPresent(s_renderer); }
static void lk_shw_boot(void) {
    static int tried; enum { NP = 6 }; static const char *triv = "#version 120\nvoid main() { gl_Position = gl_Vertex; }\n";
    const char *vsrc[NP], *fsrc[NP]; lkGLuint prog[NP], sh[2 * NP]; int np = 0, ns = 0, i, done = 0, par, shown = 0; Uint64 t0, f = SDL_GetPerformanceFrequency(); double ms = 0.0;
    void (*maxthr)(lkGLuint) = 0; void (*delp)(lkGLuint) = 0; void (*dels)(lkGLuint) = 0;
    if (tried) return; tried = 1;
    { const char *e = getenv("LANDSTALKER_SHWARM"); if (e && *e == '0') return; }
    if (!s_renderer || !lk_gpu_get() || !lk_lt_get()) return;
    SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 255); SDL_RenderClear(s_renderer); SDL_RenderFlush(s_renderer);   /* SDL's GL context current */
    if (lk_gpu_st == 0) lk_gpu_st = lk_gpu_init();
    if (lk_gpu_st < 0) return;
    *(void **)&delp = lk_gpu_fn("glDeleteProgram"); *(void **)&dels = lk_gpu_fn("glDeleteShader");
    par = SDL_GL_ExtensionSupported("GL_KHR_parallel_shader_compile") || SDL_GL_ExtensionSupported("GL_ARB_parallel_shader_compile");
    if (par) { *(void **)&maxthr = lk_gpu_fn("glMaxShaderCompilerThreadsKHR"); if (!maxthr) *(void **)&maxthr = lk_gpu_fn("glMaxShaderCompilerThreadsARB"); if (maxthr) maxthr(0xFFFFFFFFu); }
    vsrc[np] = triv; fsrc[np++] = lk_g5_fs;                      /* the biggest first: they start first in the driver's threads */
    if (lk_bl_get()) { vsrc[np] = triv; fsrc[np++] = lk_gb_fs; }   /* bounce only when the option is On (otherwise compiled when switched on) */
    vsrc[np] = triv; fsrc[np++] = lk_glt_fs;
    vsrc[np] = triv; fsrc[np++] = lk_gc_fs;
    vsrc[np] = lk_gm_vs; fsrc[np++] = lk_gm_fs;
    vsrc[np] = lk_gs_vs; fsrc[np++] = lk_gs_fs;
    t0 = SDL_GetPerformanceCounter();
    for (i = 0; i < np; i++) { lkGLuint v = lk_glCreateShader(0x8B31), fs = lk_glCreateShader(0x8B30);
        lk_glShaderSource(v, 1, &vsrc[i], 0); lk_glCompileShader(v); lk_glShaderSource(fs, 1, &fsrc[i], 0); lk_glCompileShader(fs);
        prog[i] = lk_glCreateProgram(); lk_glAttachShader(prog[i], v); lk_glAttachShader(prog[i], fs); lk_glLinkProgram(prog[i]); sh[ns++] = v; sh[ns++] = fs;
        if (!par && (double)(SDL_GetPerformanceCounter() - t0) * 1e3 / (double)f > 250.0 && !shown) { shown = 1; lk_shw_screen(i, np); } }
    if (par) {   /* poll until every program is done; the loading screen only when it takes longer than 0.25 s */
        for (;;) { int d = 0; for (i = 0; i < np; i++) { lkGLint ok = 0; lk_glGetProgramiv(prog[i], 0x91B1, &ok); d += ok ? 1 : 0; }
            done = d; ms = (double)(SDL_GetPerformanceCounter() - t0) * 1e3 / (double)f;
            if (done >= np || ms > 180000.0) break;
            if (ms > 250.0) { shown = 1; lk_shw_screen(done, np); }
            SDL_PumpEvents(); SDL_Delay(30); } }
    for (i = 0; i < np; i++) { lkGLint ok = 0; lk_glGetProgramiv(prog[i], 0x8B82, &ok); if (!ok) printf("shwarm: program %d did not link (the real initialisation reports it)\n", i); }   /* waits for the rest */
    if (shown) lk_shw_screen(np, np);
    ms = (double)(SDL_GetPerformanceCounter() - t0) * 1e3 / (double)f;
    for (i = 0; i < np; i++) if (delp) delp(prog[i]);
    for (i = 0; i < ns; i++) if (dels) dels(sh[i]);
    printf("shwarm: %d programs ready in %.0f ms (parallel %s, loading screen %s)\n", np, ms, par ? "yes" : "no", shown ? "yes" : "no"); }
'''
    s = s.replace(a, MODULE + a + "    lk_shw_boot();   /* LK_SHWARM v1: before the first frame is shown */\n")
    open(p, "w").write(s); print("platform_sdl.c patched: LK_SHWARM v1")

if __name__ == "__main__":
    main()
