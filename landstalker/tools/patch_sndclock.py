#!/usr/bin/env python3
"""Own sound clock while fast forwarding (2026-10-28, GitHub issue #11 part 2, docs/SOUND_PLAN.md step 6; default ON, env LANDSTALKER_SNDCLOCK=0 = the old way: no audio while fast forwarding).
Fast forward runs N emulated frames per displayed frame. Before, the audio of all frames was dropped. Now the SOUND TIMELINE (Z80 / recompiled driver + FM / PSG chips) advances only on every Nth emulated
frame ('sound frame' = one real 1/60 s): in the other N-1 frames ('skip frames') the Z80 is not run, no VBlank interrupt reaches it, the chips are not rendered, the Z80 / driver clock is put back at the end of
the frame; the audio of the sound frames is played. Music and effects keep their normal speed, the game runs N times faster.
Commands: the 68K's sound routine ($0013B6, one command per VBlank, game queue of only 4 entries) keeps running every emulated frame, but its writes to the driver's mailbox (Z80 RAM $1FFC / $1FFD
argument, $1FFF command) are caught in a host FIFO of 256 entries while skip frames run (or the FIFO is not empty); at the start of every sound frame ONE entry is written to the driver's RAM, only when the driver
has taken the previous command (it clears $1FFF = NEW_OPERATION). So no command is lost or overwritten at any speed and the order stays. z80_run() does nothing in a skip frame (the 68K's bus request must not
run the driver). Seamless door fast loads (lk_seam_gap) are not touched (they keep the old ducking). Without fast forward every frame is a sound frame = bit identical to before.
Needs patch_ffwd.py and patch_sndnative.py (tools/sndnative.c lk_nat_pause_save / lk_nat_pause_restore) before it.  Idempotent.  usage: patch_sndclock.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_SNDCLOCK v4"

p = os.path.join(root, "src/platform_sdl.c"); s = open(p).read()
if VER not in s:
    a = "static int lk_ff_n(void) {"
    assert s.count(a) == 1 and "LK_FFWD v1" in s, "platform_sdl.c: run patch_ffwd.py first"
    i = s.index(a); j = s.index("\n", i) + 1
    s = s[:j] + '''/* %s: >= 2 = the sound timeline runs only every Nth emulated frame (user fast forward, not the seamless door gap) */
int lk_ff_sndskip_n(void) { static int on = -1; if (on < 0) { const char *e = getenv("LANDSTALKER_SNDCLOCK"); on = !(e && *e == '0'); } if (!on || lk_seam_gap()) return 1; return lk_ff_n(); }
/* v3: WHEN is a sound frame due? by the audio device, not by a counter: a sound frame whenever fewer than LANDSTALKER_SNDCLOCK_Q (default 5) frames of audio are queued, so the music runs at exactly 1x whatever speed the emulation reaches (the Deck does not make 4x; a counter gave slow, choppy music). -1 = no fast forward, -2 = no audio device (headless: use the counter) */
int lk_ff_sound_due(void) {
    static int q = -1; int n = lk_ff_sndskip_n();
    if (n < 2) return -1;
    if (s_audio_dev <= 0) return -2;
    if (q < 0) { const char *e = getenv("LANDSTALKER_SNDCLOCK_Q"); q = e && *e ? atoi(e) : 5; if (q < 2) q = 2; if (q > 9) q = 9; }
    return SDL_GetQueuedAudioSize(s_audio_dev) < (uint32_t)q * 736u * 4u ? 1 : 0;
}
''' % VER + s[j:]
    old = "    if (lk_ff_n() > 1 && !lk_seam_gap()) return;   /* LK_FFWD v1: no audio while fast forwarding */"
    assert s.count(old) == 1, "platform_sdl.c: ffwd audio line changed"
    s = s.replace(old, "    if (lk_ff_n() > 1 && !lk_seam_gap() && lk_ff_sndskip_n() < 2) return;   /* LK_FFWD v1: no audio while fast forwarding (%s: unless the own sound clock plays the sound frames) */" % VER, 1)
    c = "        SDL_QueueAudio(s_audio_dev, samples, (uint32_t)(sample_count * 2 * sizeof(int16_t)));\n"
    assert s.count(c) == 1, "platform_sdl.c: audio queue line changed"
    s = s.replace(c, """        {   /* %s v4: underrun guard. The device takes 1024 samples at a time; when the queue has run dry (a slow frame, e.g. entering a room) one frame of silence rebuilds a cushion instead of crackling on every later hiccup; LANDSTALKER_SNDCLOCK_LOG=1 counts the empty queues */
            static int calls, empty, lg = -1; uint32_t q = SDL_GetQueuedAudioSize(s_audio_dev); static int16_t sil1[736 * 2]; static long last_pad = -1000;
            if (lg < 0) lg = getenv("LANDSTALKER_SNDCLOCK_LOG") != NULL;
            calls++; if (q == 0) empty++;
            if (lg) { static uint32_t lt; uint32_t t = SDL_GetTicks(); if (lt && t - lt > 40) fprintf(stderr, "sndclock: slow sound frame %%d: %%u ms since the last one (queued %%u)\\n", calls, t - lt, q); lt = t; }
            if (q < 2u * 736u * 4u && calls - last_pad > 20 && !lk_seam_gap()) { SDL_QueueAudio(s_audio_dev, sil1, (uint32_t)sizeof sil1); last_pad = calls; }
            if (lg && !(calls %% 600)) fprintf(stderr, "sndclock: audio queue ran empty %%d times in %%d frames (queued %%u bytes)\\n", empty, calls, q);
        }
""" % VER + c, 1)
    open(p, "w").write(s); print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/bus.c"); s = open(p).read()
if VER not in s:
    a = "static bool s_in_tick = false;  /* reentrancy guard */\n"
    assert s.count(a) == 1
    s = s.replace(a, a + '''/* %s: own sound clock while fast forwarding (tools/patch_sndclock.py) */
extern int lk_ff_sndskip_n(void), lk_ff_sound_due(void);
extern void lk_nat_pause_save(void), lk_nat_pause_restore(void), lk_snd_deliver(void);
static int s_snd_skip, s_snd_ctr;
int lk_snd_skipping(void) { return s_snd_skip; }
static void lk_snd_decide(void) {   /* at the start of every frame: sound frame or skip frame */
    int n = lk_ff_sndskip_n(), skip, due = lk_ff_sound_due();
    if (n < 2 || due == -1) { s_snd_ctr = 0; skip = 0; }
    else if (due >= 0) skip = !due;   /* the audio device wants more */
    else { s_snd_ctr++; skip = (s_snd_ctr %% n) != 0; }
    if (skip && !s_snd_skip) lk_nat_pause_save();
    s_snd_skip = skip;
    if (!skip) lk_snd_deliver();   /* one queued mailbox command to the driver */
}
''' % VER, 1)
    old = "        if (zstate == 1) z80_run(mcycles_vdp);\n        else Z80.cycles = mcycles_vdp;\n"
    assert s.count(old) == 1, "bus.c: z80 line layout changed"
    s = s.replace(old, "        if (s_snd_skip) { /* %s: the Z80 does not run in a skip frame */ }\n        else if (zstate == 1) z80_run(mcycles_vdp);\n        else Z80.cycles = mcycles_vdp;\n" % VER, 1)
    old = "            int n = audio_update(s_samples);\n            if (n > 0) platform_queue_audio(s_samples, n);\n"
    assert s.count(old) == 1, "bus.c: audio layout changed"
    s = s.replace(old, "            if (!s_snd_skip) {   /* %s */\n                int n = audio_update(s_samples);\n                if (n > 0) platform_queue_audio(s_samples, n);\n            }\n" % VER, 1)
    old = "            Z80.cycles -= mcycles_vdp;\n            { extern void lk_nat_frame(unsigned); lk_nat_frame(mcycles_vdp); }   /* LK_SNDNATIVE v1 */\n            mcycles_vdp = 0;\n"
    assert s.count(old) == 1, "bus.c: rebase layout changed"
    s = s.replace(old, "            if (s_snd_skip) lk_nat_pause_restore();   /* %s: the sound timeline stands still */\n            else {\n                Z80.cycles -= mcycles_vdp;\n                { extern void lk_nat_frame(unsigned); lk_nat_frame(mcycles_vdp); }   /* LK_SNDNATIVE v1 */\n            }\n            mcycles_vdp = 0;\n            lk_snd_decide();\n" % VER, 1)
    open(p, "w").write(s); print("bus.c patched:", VER)

core = os.path.join(root, "ext/Genesis-Plus-GX/core")
p = os.path.join(core, "mem68k.c"); s = open(p).read()
if VER not in s:
    old = "      lk_st_zram(m68k.cycles, address & 0x1FFF, data);\n"
    assert s.count(old) == 1, "mem68k.c: run patch_sndnative.py first"
    s = s.replace(old, "      { extern int lk_snd_zw(unsigned a, unsigned v); if (lk_snd_zw(address & 0x1FFF, data)) return; }   /* %s: mailbox FIFO */\n" % VER + old, 1)
    open(p, "w").write(s); print("mem68k.c patched:", VER)
p = os.path.join(core, "z80/z80.c"); s = open(p).read()
if VER not in s:
    old = "void z80_run(unsigned int cycles) { if (lk_nat_native_run(cycles)) return;"
    assert s.count(old) == 1, "z80.c: run patch_sndnative.py first"
    s = s.replace(old, "extern int lk_snd_skipping(void);\nvoid z80_run(unsigned int cycles) { if (lk_snd_skipping()) return; /* %s: no Z80 in a skip frame */ if (lk_nat_native_run(cycles)) return;" % VER, 1)
    open(p, "w").write(s); print("z80.c patched:", VER)
