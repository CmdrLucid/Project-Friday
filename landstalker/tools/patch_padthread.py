#!/usr/bin/env python3
"""Controller handling on its own thread (micro stutter fix, user's Steam Deck, 2026-10-18).
Measured: every 202 frames (3.37 s) the main thread stalled for ~8 ms (frame emulation part 3 ms -> 11 ms, one 19 ms frame = visible micro stutter), in every
room, with or without the own renderer / CRT filter.  strace of the main thread: three HID feature report ioctls on the Steam Deck controller
(HIDIOCSFEATURE 1.7 ms, HIDIOCSFEATURE 3.0 ms, HIDIOCGFEATURE 2.9 ms) at exactly that period: SDL's HIDAPI Steam Deck driver re-sends the 'disable lizard mode'
reports from inside SDL_PumpEvents / SDL_GameControllerUpdate (sdl2-compat over SDL3 on SteamOS).  SDL_JOYSTICK_HIDAPI_STEAMDECK=0 removes the stall but also the
controller in desktop mode.  A worker thread that only called SDL_GameControllerUpdate was not enough: the main thread waits for SDL's joystick lock whenever it
reads a button while the worker sits in the stall (spikes became irregular, not gone).  So the WORKER owns everything that touches SDL's joystick code: update,
removal check, scan / open every ~0.5 s, and a copy of all buttons / axes; the main thread (lk_pad_button / lk_pad_axis, the pad-present test) only reads that
copy.  Joystick / controller EVENTS are switched off so SDL_PumpEvents never updates the controllers.
The worker is also PHASE-LOCKED to the main thread: it only updates right after the main thread's SDL_PollEvent loop (semaphore posted at the end of platform_poll_events), so
its ~8 ms stall falls into the time the main thread spends emulating and never overlaps the next SDL_PumpEvents (which takes the same joystick lock): without that
the spikes only became irregular (measured: 12 spikes in 1900 frames instead of 9 regular ones).
LANDSTALKER_PADTHREAD=0 = old behaviour.  Idempotent.   usage: patch_padthread.py path/to/genrecomp"""
import os, sys
p = os.path.join(sys.argv[1], "src/input.c")
s = open(p).read()
if "LK_PADTHREAD" in s:
    print("input.c already patched: LK_PADTHREAD"); sys.exit(0)

def rep(s, a, b):
    assert s.count(a) == 1, "input.c: layout changed: " + a[:60]
    return s.replace(a, b, 1)

# 1. state shared with the readers
s = rep(s, "#include <stdio.h>\n", r'''#include <stdio.h>
/* LK_PADTHREAD v3 (tools/patch_padthread.py): all controller work on a worker thread, the Steam Deck HIDAPI driver blocks ~8 ms every 3.4 s */
static volatile int lk_pt_run; static SDL_Thread *lk_pt; static SDL_sem *lk_pt_sem;
static volatile int lk_pc_btn[8][SDL_CONTROLLER_BUTTON_MAX], lk_pc_axis[8][SDL_CONTROLLER_AXIS_MAX], lk_pc_have;
''')
# 2. the readers use the copy
s = rep(s, "static int lk_pad_button(SDL_GameController **pads, SDL_GameControllerButton b) {\n",
        "static int lk_pad_button(SDL_GameController **pads, SDL_GameControllerButton b) {\n    if (lk_pt_run) { for (int k = 0; k < 8; k++) if (lk_pc_btn[k][b]) return 1; return 0; }   /* LK_PADTHREAD */\n")
s = rep(s, "static int lk_pad_axis(SDL_GameController **pads, SDL_GameControllerAxis a) {\n    int best = 0;\n",
        "static int lk_pad_axis(SDL_GameController **pads, SDL_GameControllerAxis a) {\n    int best = 0;\n    if (lk_pt_run) { for (int k = 0; k < 8; k++) { int v = lk_pc_axis[k][a]; if ((v < 0 ? -v : v) > (best < 0 ? -best : best)) best = v; } return best; }   /* LK_PADTHREAD */\n")
# 3. the worker, after the controller table
s = rep(s, "static SDL_GameController *lk_pads[8];\n", r'''static SDL_GameController *lk_pads[8];
static int lk_pt_fn(void *u) {
    int scan = 0; (void)u;
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");
    while (lk_pt_run) {
        SDL_SemWaitTimeout(lk_pt_sem, 100);                           /* posted by the main thread right after its event pump (lk_pad_kick) */
        if (!lk_pt_run) break;
        SDL_GameControllerUpdate();                                   /* the part that may block for ~8 ms */
        for (int k = 0; k < 8; k++)
            if (lk_pads[k] && !SDL_GameControllerGetAttached(lk_pads[k])) {
                printf("input: controller \"%s\" removed\n", SDL_GameControllerName(lk_pads[k]));
                SDL_GameController *c = lk_pads[k]; lk_pads[k] = NULL; SDL_GameControllerClose(c);
            }
        if (scan-- <= 0) {
            scan = 30;
            for (int i = 0; i < SDL_NumJoysticks(); i++) {
                if (!SDL_IsGameController(i)) continue;
                SDL_JoystickID id = SDL_JoystickGetDeviceInstanceID(i);
                int have = 0, freek = -1;
                for (int k = 0; k < 8; k++) {
                    if (lk_pads[k] && SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(lk_pads[k])) == id) have = 1;
                    if (!lk_pads[k] && freek < 0) freek = k;
                }
                if (!have && freek >= 0) {
                    SDL_GameController *c = SDL_GameControllerOpen(i);
                    if (c) { lk_pads[freek] = c; printf("input: using controller \"%s\"\n", SDL_GameControllerName(c)); }
                }
            }
        }
        for (int k = 0; k < 8; k++) {
            if (lk_pads[k]) {
                for (int b = 0; b < SDL_CONTROLLER_BUTTON_MAX; b++) lk_pc_btn[k][b] = SDL_GameControllerGetButton(lk_pads[k], (SDL_GameControllerButton)b);
                for (int a = 0; a < SDL_CONTROLLER_AXIS_MAX; a++) lk_pc_axis[k][a] = SDL_GameControllerGetAxis(lk_pads[k], (SDL_GameControllerAxis)a);
            } else {
                for (int b = 0; b < SDL_CONTROLLER_BUTTON_MAX; b++) lk_pc_btn[k][b] = 0;
                for (int a = 0; a < SDL_CONTROLLER_AXIS_MAX; a++) lk_pc_axis[k][a] = 0;
            }
        }
    }
    return 0;
}
void lk_pad_kick(void) { if (lk_pt_run && lk_pt_sem && SDL_SemValue(lk_pt_sem) < 1) SDL_SemPost(lk_pt_sem); }   /* main thread: after the event pump */
static void lk_pad_thread_start(void) {
    static int done; const char *e;
    if (done) return;
    done = 1;
    e = getenv("LANDSTALKER_PADTHREAD"); if (e && *e == '0') return;
    if (!SDL_WasInit(SDL_INIT_GAMECONTROLLER)) return;
    SDL_GameControllerEventState(SDL_IGNORE); SDL_JoystickEventState(SDL_IGNORE);
    lk_pt_sem = SDL_CreateSemaphore(0);
    lk_pt_run = 1; lk_pt = SDL_CreateThread(lk_pt_fn, "lk_pad", NULL);
    printf("input: controller handling on its own thread\n");
}
''')
# 4. the main thread leaves removal / scan to the worker
s = rep(s, "        int pad = 0;\n        for (int k = 0; k < 8; k++)\n            if (pads[k] && !SDL_GameControllerGetAttached(pads[k])) {",
        "        int pad = 0;\n        lk_pad_thread_start();   /* LK_PADTHREAD */\n        for (int k = 0; !lk_pt_run && k < 8; k++)\n            if (pads[k] && !SDL_GameControllerGetAttached(pads[k])) {")
s = rep(s, "        if (scan_countdown-- <= 0) {", "        if (!lk_pt_run && scan_countdown-- <= 0) {")
open(p, "w").write(s)
pp = os.path.join(sys.argv[1], "src/platform_sdl.c")
t = open(pp).read()
anchor = "    return true;\n}\n\nvoid platform_frame_sync(void) {"
assert t.count(anchor) == 1, "platform_sdl.c: platform_poll_events layout changed"
t = t.replace(anchor, "    { extern void lk_pad_kick(void); lk_pad_kick(); }   /* LK_PADTHREAD v3: controller worker runs after the event pump */\n" + anchor, 1)
open(pp, "w").write(t)
print("input.c + platform_sdl.c patched: LK_PADTHREAD v3")
