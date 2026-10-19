#!/usr/bin/env python3
"""Quick save / quick load anywhere (2026-10-15, user wish).  Pad L2 (left trigger) or key F9 = quick save, pad L1 HELD for half a second or key F10 = quick load.
It uses the GAME'S OWN save routines with a hidden fifth slot (index 4, SRAM $202031..; the file select only shows slots 0..3, the church saves are untouched):
 * save: SaveGame $001592 with $FF0010 (current slot) = 4, then the slot number is put back. Exactly what the Record Book item does ($024FE0 HandleRecordBookUse): the game stores the room, the tile
   position, health, gold, inventory and the story flags (table SaveGameRamPtrs $001628), nothing of the running enemies / cutscene state.
 * load: like the game's own 'game over -> continue' path (EndGame $0004BE: stack to 0, ResetVDPAndClearRAM $000516, ClearAndInitGraphics $00054C) but without logo / title / file select: LoadSavedGame
   $0015C2 with slot 4, the real slot number back in $FF0010, then RunGameLoop $0016CA (LoadGame, StartGame fade-in, GameLoop).
Both run at the START of a GameLoop pass ($0016DC), i.e. never inside a menu, a text box or a cutscene routine (those loops run inside a pass). A request while nothing is saved shows 'NO QUICKSAVE'. A request that no GameLoop pass picks up within 8 frames (menu, text box, cutscene, fade) is refused: low beep + 'NOT NOW', nothing is executed later.
Screen hint (QUICKSAVE / QUICKLOAD) on the picture, the game's select sound. Test aid: LANDSTALKER_QS="s600,l900" = request quick save at frame 600, quick load at frame 900 (headless runs).
Off by default: Options > Gameplay > Quick Save (file ~/.landstalker_quicksave, env LANDSTALKER_QSAVE=0|1); while Off the buttons / keys do nothing.
Needs patch_options / patch_ffwd before it.  Idempotent.  usage: patch_quicksave.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_QUICKSAVE v1"

ph = os.path.join(root, "include/genrecomp/platform.h")
s = open(ph).read()
if "platform_quick_request" not in s:
    a = "void platform_set_ffwd(int hold);"
    assert a in s, "platform.h: run patch_ffwd.py first"
    s = s.replace(a, a + "\n/* quick save (1) / quick load (2) request, executed at the next GameLoop pass */\nvoid platform_quick_request(int what);", 1)
    open(ph, "w").write(s)

pi = os.path.join(root, "src/input.c")
s = open(pi).read()
if VER not in s:
    for old, new in (("/* L2: free (widescreen is in the options menu) */", "if (lt && !lt_prev) platform_quick_request(1);   /* LK_QUICKSAVE v1: L2 = quick save */"),
                     ("/* L1: free (scaling is in the options menu) */", "{ static int lh; if (ls) { if (++lh == 30) platform_quick_request(2); } else lh = 0; }   /* LK_QUICKSAVE v1: L1 held 0.5 s = quick load */")):
        assert s.count(old) == 1, "input.c layout changed: " + old
        s = s.replace(old, new, 1)
    open(pi, "w").write(s)
    print("input.c patched:", VER)

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    a = "void platform_present_frame(const uint8_t *framebuffer) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_QUICKSAVE v1 (tools/patch_quicksave.py) ---- */
static int lk_qs_req; static long lk_qs_req_frame;
static int lk_qsw = -1;   /* Options > Gameplay > Quick Save Off / On, default Off (user wish 2026-10-16); file ~/.landstalker_quicksave, env LANDSTALKER_QSAVE=0|1 wins */
int lk_qsave_get(void) {
    if (lk_qsw < 0) { char p[512]; FILE *f; const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_QSAVE"); int v = 0; snprintf(p, sizeof p, "%s/.landstalker_quicksave", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e) v = atoi(e); lk_qsw = v ? 1 : 0; }
    return lk_qsw;
}
void lk_qsave_set(int v) { char p[512]; FILE *f; const char *h = getenv("HOME"); lk_qsave_get(); lk_qsw = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_quicksave", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_qsw); fclose(f); } }
void platform_quick_request(int what) { if (!lk_qsave_get()) return; lk_qs_req = what; lk_qs_req_frame = s_frame_no; }
static void lk_qs_post(int what) { if (!lk_qsave_get()) return; lk_qs_req = what; lk_qs_req_frame = s_frame_no; }
int lk_qs_take(void) {   /* called by the game side at the start of every GameLoop pass: 0 none, 1 save, 2 load (also the LANDSTALKER_QS test schedule) */
    static const char *sched; static int init; int r = lk_qs_req;
    if (!init) { init = 1; sched = getenv("LANDSTALKER_QS"); }
    if (!r && sched) { char key[24]; snprintf(key, sizeof key, "s%ld,", s_frame_no); { char l[256]; snprintf(l, sizeof l, "%s,", sched); if (strstr(l, key)) r = 1; snprintf(key, sizeof key, "l%ld,", s_frame_no); if (strstr(l, key)) r = 2; } }
    lk_qs_req = 0;
    return r;
}
static void lk_beep(void) {   /* short low tone (own, not the game's sound: the request is refused while the game is inside a menu / text box / cutscene loop) */
    static int16_t b[2 * 4410]; int i;
    if (s_audio_dev <= 0) return;
    for (i = 0; i < 4410; i++) { int16_t v = ((i / 100) & 1) ? 2500 : -2500; b[2 * i] = v; b[2 * i + 1] = v; }
    SDL_QueueAudio(s_audio_dev, b, (uint32_t)sizeof b);
}
static void lk_qs_check(void) {
    static const char *post; static int init;   /* test aid LANDSTALKER_QSREQ="s6220,l6300": post a request at that frame as if a button was pressed (headless); LANDSTALKER_QS_DEBUG=1 reports refusals */
    if (!init) { init = 1; post = getenv("LANDSTALKER_QSREQ"); }
    if (post) { char key[24], l[256]; snprintf(l, sizeof l, "%s,", post); snprintf(key, sizeof key, "s%ld,", s_frame_no); if (strstr(l, key)) lk_qs_post(1); snprintf(key, sizeof key, "l%ld,", s_frame_no); if (strstr(l, key)) lk_qs_post(2); }   /* every presented frame: a request that no GameLoop pass picked up within 8 frames means the game is in a nested loop (menu, dialogue, cutscene, fade) -> refuse */
    if (lk_qs_req && s_frame_no - lk_qs_req_frame >= 8) { if (getenv("LANDSTALKER_QS_DEBUG")) fprintf(stderr, "quicksave: request %d refused at frame %ld (game is inside a menu / dialogue / cutscene loop)\n", lk_qs_req, s_frame_no); lk_qs_req = 0; lk_beep(); snprintf(lk_osd_text, sizeof lk_osd_text, "NOT NOW"); lk_osd_frames = 60; }
}
void lk_osd_say(const char *t) { snprintf(lk_osd_text, sizeof lk_osd_text, "%s", t); lk_osd_frames = 90; }
'''
    s = s.replace(a, module + a, 1)
    f0 = "    lk_fs_present_begin();\n"
    assert s.count(f0) == 1, "present layout changed"
    s = s.replace(f0, f0 + "    lk_qs_check();   /* LK_QUICKSAVE v1 */\n", 1)
    k = "lk_ff_kb = ev.type == SDL_KEYDOWN;   /* LK_FFWD v1: Tab held = fast forward */\n"
    assert s.count(k) == 1, "platform_sdl.c: run patch_ffwd.py first"
    s = s.replace(k, k + "        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F9) lk_qs_post(1);    /* LK_QUICKSAVE v1 */\n        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F10) lk_qs_post(2);\n", 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "lk_brand_install" in s, "func_table.c: run patch_overlay.py first"
    module = r'''/* ---- LK_QUICKSAVE v1: quick save / load anywhere (tools/patch_quicksave.py) ---- */
extern int lk_qs_take(void);
extern void lk_osd_say(const char *t);
extern void lk_gaia_cancel(void);   /* tools/patch_gaia.py: a running live Gaia effect ends before the saved game is loaded */
static gen_func_t lk_o_gloop, lk_o_loadgame;
#define LK_QS_SLOT 4
static int lk_qs_loading, lk_qs_slot0;
static int lk_qs_have(void) { int i; for (i = 0; i < 32; i++) if (bus_read8(0x202031u + 2u * (uint32_t)i)) return 1; return 0; }
/* LoadGame ($0026E8) = ClearPlayerStruct, the whole file select (InitGameSelectScreen, it also calls LoadSavedGame) and then LoadRoomPath / LoadMagicSwordGfx. While a quick load is running
   the same steps are done here without the file select: the saved game of the hidden slot is loaded, everything else is the game's own code. RunGameLoop then calls StartGame and GameLoop as usual. */
static void lk_h_loadgame(void) {
    if (!lk_qs_loading) { lk_o_loadgame(); return; }
    lk_qs_loading = 0;
    lk_gaia_cancel();
    lk_call(0x002726u);   /* ClearPlayerStruct */
    lk_call(0x022EC0u);   /* HideRightArrow */
    lk_call(0x002F3Cu);   /* CheckRAM: the RAM marker the file select expects (it clears $FF0010 when it has to write it) */
    bus_write8(0xFF0010u, LK_QS_SLOT); lk_call(0x0015C2u);   /* LoadSavedGame */
    bus_write8(0xFF0010u, (uint8_t)lk_qs_slot0);
    lk_call(0x0008F2u);   /* EnableDisplayAndInts (SetUpTextDisplay waits for VBlank interrupts; the file select enables them itself) */
    lk_call(0x022EA0u);   /* SetUpTextDisplay */
    lk_call(0x000AE0u);   /* ClearAndRefreshVDPSpriteTableDMA */
    g_m68k.d[0] &= 0xFFFFFF00u; lk_call(0x002824u);   /* LoadRoomPath (d0 = 0: the saved position) */
    lk_call(0x0077A6u);   /* LoadMagicSwordGfx */
    func_table_rts();
}
static void lk_h_gloop(void) {
    int req = lk_qs_take();
    if (req == 1) {
        M68kContext sv = g_m68k; uint8_t slot0 = bus_read8(0xFF0010u);
        bus_write8(0xFF0010u, LK_QS_SLOT); lk_call(0x001592u);   /* SaveGame */
        bus_write8(0xFF0010u, slot0); g_m68k = sv;
        lk_snd(LK_SND_SELECT); lk_osd_say("QUICKSAVE"); if (getenv("LANDSTALKER_QS_DEBUG")) fprintf(stderr, "quicksave: saved\n");
    } else if (req == 2) {
        if (!lk_qs_have()) { lk_snd(LK_SND_MOVE); lk_osd_say("NO QUICKSAVE"); }
        else {
            lk_qs_slot0 = bus_read8(0xFF0010u); lk_qs_loading = 1;
            lk_osd_say("QUICKLOAD"); if (getenv("LANDSTALKER_QS_DEBUG")) fprintf(stderr, "quicksave: loading\n");
            g_m68k.pc = 0x0004E2; recomp_m68k_exception(32 + 0);   /* the game over code's own trap #0 with data $FFFD: music off */
            g_m68k.a[7] = 0;                                        /* lea $0.w,a7 */
            lk_call(0x0009A8u);                                     /* FadeToBlack */
            lk_call(0x0008F6u);                                     /* DisableDisplayAndInts */
            lk_call(0x000516u);                                     /* ResetVDPAndClearRAM */
            lk_call(0x00054Cu);                                     /* ClearAndInitGraphics */
            func_table_tail(0x0016CAu);                             /* RunGameLoop: LoadGame (ours), StartGame, GameLoop */
            return;
        }
    }
    lk_o_gloop();
}
static void lk_qs_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_gloop = func_table_lookup(0x0016DC); lk_o_loadgame = func_table_lookup(0x0026E8);
    if (lk_o_gloop && lk_o_loadgame) { func_table_register(0x0016DC, lk_h_gloop); func_table_register(0x0026E8, lk_h_loadgame); } else fprintf(stderr, "quicksave: GameLoop / LoadGame not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_brand_install();   /* LK_BRAND v1 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_qs_install();   /* LK_QUICKSAVE v1 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
