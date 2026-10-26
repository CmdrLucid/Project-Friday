#!/usr/bin/env python3
"""Focus pause (issue #9, 2026-10-26): while the window has no focus or is minimized (alt+tab, Steam overlay) the game stops completely:
the audio device is paused and its queue cleared (no distorted music), the emulation waits inside platform_poll_events, the frame timer is restarted on return.
LANDSTALKER_NOFOCUSPAUSE=1 switches it off (test aid / background play).  Idempotent.  usage: patch_focuspause.py path/to/genrecomp"""
import os, sys
p = os.path.join(sys.argv[1], "src/platform_sdl.c")
s = open(p).read()
if "LK_FOCUSPAUSE" in s:
    print("platform_sdl.c already patched: LK_FOCUSPAUSE"); sys.exit(0)
a = "    while (SDL_PollEvent(&ev)) {\n        if (ev.type == SDL_QUIT) return false;\n"
assert s.count(a) == 1, "platform_sdl.c: platform_poll_events loop layout changed"
new = r'''    { /* LK_FOCUSPAUSE v1 (tools/patch_focuspause.py): no focus / minimized = whole game paused */
        static int lk_fp_off = -1;
        if (lk_fp_off < 0) { const char *e = getenv("LANDSTALKER_NOFOCUSPAUSE"); lk_fp_off = e && *e && *e != '0'; }
        if (!lk_fp_off && s_window && (SDL_GetWindowFlags(s_window) & (SDL_WINDOW_MINIMIZED | SDL_WINDOW_HIDDEN | SDL_WINDOW_INPUT_FOCUS)) != SDL_WINDOW_INPUT_FOCUS) {
            printf("focus pause: window lost focus, game paused\n");
            if (s_audio_dev > 0) { SDL_PauseAudioDevice(s_audio_dev, 1); SDL_ClearQueuedAudio(s_audio_dev); }
            while ((SDL_GetWindowFlags(s_window) & (SDL_WINDOW_MINIMIZED | SDL_WINDOW_HIDDEN | SDL_WINDOW_INPUT_FOCUS)) != SDL_WINDOW_INPUT_FOCUS) {
                if (SDL_WaitEventTimeout(&ev, 50)) {
                    if (ev.type == SDL_QUIT) return false;
                    if (ev.type == SDL_WINDOWEVENT && ev.window.event == SDL_WINDOWEVENT_EXPOSED) SDL_RenderPresent(s_renderer);
                }
            }
            if (s_audio_dev > 0) SDL_PauseAudioDevice(s_audio_dev, 0);
            s_frame_start = SDL_GetPerformanceCounter();
            printf("focus pause: focus back, game continues\n");
        }
    }
'''
s = s.replace(a, new + a, 1)
open(p, "w").write(s)
print("platform_sdl.c patched: LK_FOCUSPAUSE")
