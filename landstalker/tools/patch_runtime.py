#!/usr/bin/env python3
"""Runtime patches for genrecomp (idempotent):
 1. input.c: read an SDL game controller (Steam Deck / any gamepad) as Genesis pad 1
 2. platform_sdl.c: GENRECOMP_AUDIO_DEBUG=1 reports audio device open + sample peaks
usage: patch_runtime.py path/to/genrecomp
"""
import sys, os

root = sys.argv[1]

def patch(rel, old, new, marker):
    p = os.path.join(root, rel)
    s = open(p).read()
    if marker in s:
        print(rel, "already patched"); return
    assert old in s, f"{rel}: layout changed ({old[:40]!r})"
    open(p, "w").write(s.replace(old, new, 1))
    print(rel, "patched")

# ---- 1. game controller -------------------------------------------------
PAD = r'''    /* LANDSTALKER_PAD: SDL game controller -> Genesis pad 1 */
    if (!platform_is_headless()) {
        /* ALL attached controllers are read together (OR of the buttons, strongest axis): with the Deck
           docked an external pad (Xbox etc.) comes after the built-in "Steam Deck Controller" and was ignored */
        static SDL_GameController *pads[8];
        static int scan_countdown;
        int pad = 0;
        for (int k = 0; k < 8; k++)
            if (pads[k] && !SDL_GameControllerGetAttached(pads[k])) {
                printf("input: controller \"%s\" removed\n", SDL_GameControllerName(pads[k]));
                SDL_GameControllerClose(pads[k]); pads[k] = NULL;
            }
        if (scan_countdown-- <= 0) {
            scan_countdown = 120;
            SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");
            for (int i = 0; i < SDL_NumJoysticks(); i++) {
                if (!SDL_IsGameController(i)) continue;
                SDL_JoystickID id = SDL_JoystickGetDeviceInstanceID(i);
                int have = 0, freek = -1;
                for (int k = 0; k < 8; k++) {
                    if (pads[k] && SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(pads[k])) == id) have = 1;
                    if (!pads[k] && freek < 0) freek = k;
                }
                if (!have && freek >= 0 && (pads[freek] = SDL_GameControllerOpen(i)))
                    printf("input: using controller \"%s\"\n", SDL_GameControllerName(pads[freek]));
            }
        }
        for (int k = 0; k < 8; k++) if (pads[k]) pad = 1;
        if (pad) {
#define PB(b) lk_pad_button(pads, SDL_CONTROLLER_BUTTON_##b)
#define PA(a) lk_pad_axis(pads, SDL_CONTROLLER_AXIS_##a)
            if (PB(DPAD_UP)    || PA(LEFTY)  < -16000) buttons |= GEN_BTN_UP;
            if (PB(DPAD_DOWN)  || PA(LEFTY)  >  16000) buttons |= GEN_BTN_DOWN;
            if (PB(DPAD_LEFT)  || PA(LEFTX)  < -16000) buttons |= GEN_BTN_LEFT;
            if (PB(DPAD_RIGHT) || PA(LEFTX)  >  16000) buttons |= GEN_BTN_RIGHT;
            if (PB(X))             buttons |= GEN_BTN_A;
            if (PB(A))             buttons |= GEN_BTN_B;
            if (PB(B))             buttons |= GEN_BTN_C;
            if (PB(START))         buttons |= GEN_BTN_START;
            if (PB(Y))             buttons |= GEN_BTN_X;
            { /* LANDSTALKER_DISPLAY: L1 = scaling mode, R1 = filter (Landstalker does not use the shoulder buttons) */
                static int ls_prev, rs_prev; int ls = PB(LEFTSHOULDER), rs = PB(RIGHTSHOULDER);
                if (ls && !ls_prev) platform_display_cycle_scale();
                if (rs && !rs_prev) platform_display_cycle_filter();
                ls_prev = ls; rs_prev = rs;
            }
            if (PB(BACK))          buttons |= GEN_BTN_MODE;
#undef PB
#undef PA
        }
    }

'''
patch("src/input.c", "    buttons |= platform_scripted_buttons();", PAD + "    buttons |= platform_scripted_buttons();", "LANDSTALKER_PAD")
patch("src/input.c", "#include <string.h>", "#include <string.h>\n#include <stdio.h>", "#include <stdio.h>")
HELP = r'''
/* LANDSTALKER_MULTIPAD: button pressed on any controller / axis value with the largest magnitude */
static int lk_pad_button(SDL_GameController **pads, SDL_GameControllerButton b) {
    for (int k = 0; k < 8; k++) if (pads[k] && SDL_GameControllerGetButton(pads[k], b)) return 1;
    return 0;
}
static int lk_pad_axis(SDL_GameController **pads, SDL_GameControllerAxis a) {
    int best = 0;
    for (int k = 0; k < 8; k++) if (pads[k]) {
        int v = SDL_GameControllerGetAxis(pads[k], a);
        if ((v < 0 ? -v : v) > (best < 0 ? -best : best)) best = v;
    }
    return best;
}

static uint16_t s_pad_state[2];'''
patch("src/input.c", "\nstatic uint16_t s_pad_state[2];", HELP, "LANDSTALKER_MULTIPAD")

# ---- 2. audio probe -----------------------------------------------------
patch("src/platform_sdl.c",
      "    s_audio_dev = SDL_OpenAudioDevice(NULL, 0, &want, &have, 0);\n",
      "    s_audio_dev = SDL_OpenAudioDevice(NULL, 0, &want, &have, 0);\n"
      "    if (getenv(\"GENRECOMP_AUDIO_DEBUG\")) {\n"
      "        if (s_audio_dev > 0) printf(\"audio: device %u opened, %d Hz fmt=%04X ch=%d (driver %s)\\n\", s_audio_dev, have.freq, have.format, have.channels, SDL_GetCurrentAudioDriver());\n"
      "        else printf(\"audio: SDL_OpenAudioDevice FAILED: %s\\n\", SDL_GetError());\n"
      "    }\n",
      "audio: device")
patch("src/platform_sdl.c",
      "void platform_queue_audio(const int16_t *samples, int sample_count) {\n",
      "void platform_queue_audio(const int16_t *samples, int sample_count) {\n"
      "    if (getenv(\"GENRECOMP_AUDIO_DEBUG\") && samples) {\n"
      "        static int calls, peak, total; int pk = 0;\n"
      "        for (int i = 0; i < sample_count * 2; i++) { int v = samples[i] < 0 ? -samples[i] : samples[i]; if (v > pk) pk = v; }\n"
      "        if (pk > peak) peak = pk; total += sample_count;\n"
      "        if (++calls % 60 == 0) { printf(\"audio: frame %d peak=%d samples/frame=%d queued=%u bytes\\n\", calls, peak, total / 60, s_audio_dev > 0 ? SDL_GetQueuedAudioSize(s_audio_dev) : 0u); fflush(stdout); peak = 0; total = 0; }\n"
      "    }\n",
      "audio: frame")
