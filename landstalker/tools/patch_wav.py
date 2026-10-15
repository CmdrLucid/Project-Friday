#!/usr/bin/env python3
"""Audio capture for sound debugging: LANDSTALKER_WAV=<file.wav> writes everything the core produces (44100 Hz, 16 bit, stereo) to a WAV file, one block per emulated frame,
in the recompiled build (platform_queue_audio) AND in genrecomp_ref (which otherwise throws its audio away), with or without --headless. Compare the two with tools/wavcmp.py.
Idempotent.  usage: patch_wav.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if "LANDSTALKER_WAV" not in s:
    a = "void platform_queue_audio(const int16_t *samples, int sample_count) {\n"
    assert s.count(a) == 1, "platform_sdl.c: platform_queue_audio layout changed"
    helper = r'''/* LANDSTALKER_WAV: audio capture (see tools/patch_wav.py). The header is rewritten after every block so a killed process still leaves a valid file. */
static FILE *lk_wav; static int lk_wav_init; static uint32_t lk_wav_bytes;
void platform_wav_write(const int16_t *samples, int sample_count) {
    if (!lk_wav_init) { const char *e = getenv("LANDSTALKER_WAV"); lk_wav_init = 1; if (e && *e) { lk_wav = fopen(e, "wb"); if (lk_wav) { uint8_t h[44] = {0}; fwrite(h, 1, 44, lk_wav); } } }
    if (!lk_wav || !samples || sample_count <= 0) return;
    fwrite(samples, 4, (size_t)sample_count, lk_wav); lk_wav_bytes += (uint32_t)sample_count * 4;
    uint8_t h[44]; uint32_t v;
    memcpy(h, "RIFF", 4); v = 36 + lk_wav_bytes; memcpy(h + 4, &v, 4); memcpy(h + 8, "WAVEfmt ", 8); v = 16; memcpy(h + 16, &v, 4);
    h[20] = 1; h[21] = 0; h[22] = 2; h[23] = 0; v = 44100; memcpy(h + 24, &v, 4); v = 44100 * 4; memcpy(h + 28, &v, 4); h[32] = 4; h[33] = 0; h[34] = 16; h[35] = 0;
    memcpy(h + 36, "data", 4); v = lk_wav_bytes; memcpy(h + 40, &v, 4);
    long pos = ftell(lk_wav); fseek(lk_wav, 0, SEEK_SET); fwrite(h, 1, 44, lk_wav); fseek(lk_wav, pos, SEEK_SET);
}

'''
    s = s.replace(a, helper + a + "    platform_wav_write(samples, sample_count);   /* LANDSTALKER_WAV */\n", 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched: LANDSTALKER_WAV")
else:
    print("platform_sdl.c already patched: LANDSTALKER_WAV")
ph = os.path.join(root, "include/genrecomp/platform.h")
h = open(ph).read()
if "platform_wav_write" not in h:
    a = "bool platform_poll_events(void);"
    assert a in h
    h = h.replace(a, a + "\n/* LANDSTALKER_WAV: audio capture (also used by genrecomp_ref) */\nvoid platform_wav_write(const int16_t *samples, int sample_count);", 1)
    open(ph, "w").write(h)
pr = os.path.join(root, "tools/ref_runner/main.c")
r = open(pr).read()
if "platform_wav_write" not in r:
    a = "        audio_update(audio);\n"
    assert r.count(a) == 1, "ref_runner/main.c: audio_update layout changed"
    r = r.replace(a, "        { int lk_n = audio_update(audio); platform_wav_write(audio, lk_n); }   /* LANDSTALKER_WAV */\n", 1)
    open(pr, "w").write(r)
    print("ref_runner patched: LANDSTALKER_WAV")
