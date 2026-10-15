#!/usr/bin/env python3
"""Audio buffer (crackle fix, 2026-10-10): the SDL audio queue used to hold only ~1.5 emulated frames (about 25 ms) and the device takes 1024-sample blocks (23 ms),
so a frame that is a few ms late ran the queue dry (crackle, 'strange' short sound effects, worse with WIDE=48 where a frame costs more).
 * start-up: LANDSTALKER_AUDIO_PREFILL=<frames> of silence are queued before the first block (default 3 = ~50 ms extra latency; 0 = old behaviour)
 * safety valve: if more than LANDSTALKER_AUDIO_MAXQ=<frames> (default 10) of audio are waiting the new block is dropped (the queue cannot grow without bound if the device runs slower than the emulation)
Idempotent.  usage: patch_audiobuf.py path/to/genrecomp"""
import os, sys
p = os.path.join(sys.argv[1], "src/platform_sdl.c")
s = open(p).read()
if "LANDSTALKER_AUDIO_PREFILL" in s:
    print("platform_sdl.c already patched: LANDSTALKER_AUDIO_PREFILL"); sys.exit(0)
old = "    if (s_audio_dev > 0 && samples) {\n        SDL_QueueAudio(s_audio_dev, samples, (uint32_t)(sample_count * 2 * sizeof(int16_t)));\n    }\n"
assert s.count(old) == 1, "platform_sdl.c: SDL_QueueAudio layout changed"
new = r'''    if (s_audio_dev > 0 && samples) {
        static int lk_ab_init, lk_ab_prefill = 3, lk_ab_maxq = 10;   /* LANDSTALKER_AUDIO_PREFILL / _MAXQ, in emulated frames of 736 samples */
        if (!lk_ab_init) {
            const char *e = getenv("LANDSTALKER_AUDIO_PREFILL"), *m = getenv("LANDSTALKER_AUDIO_MAXQ");
            if (e && *e) lk_ab_prefill = atoi(e); if (m && *m) lk_ab_maxq = atoi(m);
            if (lk_ab_prefill < 0) lk_ab_prefill = 0; if (lk_ab_prefill > 20) lk_ab_prefill = 20;
            lk_ab_init = 1;
            if (lk_ab_prefill > 0) { static int16_t sil[736 * 2]; SDL_QueueAudio(s_audio_dev, sil, (uint32_t)(sizeof sil)); for (int i = 1; i < lk_ab_prefill; i++) SDL_QueueAudio(s_audio_dev, sil, (uint32_t)(sizeof sil)); }
        }
        if (lk_ab_prefill > 0 && SDL_GetQueuedAudioSize(s_audio_dev) > (uint32_t)lk_ab_maxq * 736u * 4u) return;   /* valve: device slower than the emulation */
        SDL_QueueAudio(s_audio_dev, samples, (uint32_t)(sample_count * 2 * sizeof(int16_t)));
    }
'''
s = s.replace(old, new, 1)
open(p, "w").write(s)
print("platform_sdl.c patched: LANDSTALKER_AUDIO_PREFILL")
