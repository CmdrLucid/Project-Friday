#!/usr/bin/env python3
"""Own sound clock while fast forwarding (2026-10-28, GitHub issue #11 part 2, docs/SOUND_PLAN.md step 6; default ON, env LANDSTALKER_SNDCLOCK=0 = the old way: no audio while fast forwarding).
Fast forward runs N emulated frames per displayed frame. Before, the audio of all frames was dropped. Now the SOUND TIMELINE (Z80 / recompiled driver + FM / PSG chips) advances only on every Nth emulated
frame ('sound frame' = one real 1/60 s): in the other N-1 frames ('skip frames') the Z80 is not run, no VBlank interrupt reaches it, the chips are not rendered, the Z80 / driver clock is put back at the end of
the frame; the audio of the sound frames is played. Music and effects keep their normal speed, the game runs N times faster.
Commands: ProcessSoundCommandQueue ($0013B6, the 68K's mailbox writer, one command per VBlank) does nothing in skip frames, so the game's own 4 entry sound queue ($FF0FA0) holds the commands and the
driver gets one per sound frame, in order (nothing is overwritten). Seamless door fast loads (lk_seam_gap) are not touched (they keep the old ducking). Without fast forward every frame is a sound frame
= bit identical to before. Needs patch_ffwd.py and patch_sndnative.py (tools/sndnative.c lk_nat_pause_save / lk_nat_pause_restore) before it.  Idempotent.  usage: patch_sndclock.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_SNDCLOCK v1"

p = os.path.join(root, "src/platform_sdl.c"); s = open(p).read()
if VER not in s:
    a = "static int lk_ff_n(void) {"
    assert s.count(a) == 1 and "LK_FFWD v1" in s, "platform_sdl.c: run patch_ffwd.py first"
    i = s.index(a); j = s.index("\n", i) + 1
    s = s[:j] + '''/* %s: >= 2 = the sound timeline runs only every Nth emulated frame (user fast forward, not the seamless door gap) */
int lk_ff_sndskip_n(void) { static int on = -1; if (on < 0) { const char *e = getenv("LANDSTALKER_SNDCLOCK"); on = !(e && *e == '0'); } if (!on || lk_seam_gap()) return 1; return lk_ff_n(); }
''' % VER + s[j:]
    old = "    if (lk_ff_n() > 1 && !lk_seam_gap()) return;   /* LK_FFWD v1: no audio while fast forwarding */"
    assert s.count(old) == 1, "platform_sdl.c: ffwd audio line changed"
    s = s.replace(old, "    if (lk_ff_n() > 1 && !lk_seam_gap() && lk_ff_sndskip_n() < 2) return;   /* LK_FFWD v1: no audio while fast forwarding (%s: unless the own sound clock plays the sound frames) */" % VER, 1)
    open(p, "w").write(s); print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/bus.c"); s = open(p).read()
if VER not in s:
    a = "static bool s_in_tick = false;  /* reentrancy guard */\n"
    assert s.count(a) == 1
    s = s.replace(a, a + '''/* %s: own sound clock while fast forwarding (tools/patch_sndclock.py) */
extern int lk_ff_sndskip_n(void);
extern void lk_nat_pause_save(void), lk_nat_pause_restore(void);
static int s_snd_skip, s_snd_ctr;
int lk_snd_skipping(void) { return s_snd_skip; }
static void lk_snd_decide(void) {   /* at the start of every frame: sound frame or skip frame */
    int n = lk_ff_sndskip_n(), skip;
    if (n < 2) { s_snd_ctr = 0; skip = 0; } else { s_snd_ctr++; skip = (s_snd_ctr %% n) != 0; }
    if (skip && !s_snd_skip) lk_nat_pause_save();
    s_snd_skip = skip;
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

p = os.path.join(root, "src/func_table.c"); s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    h = "        lk_carry_install();   /* LK_CARRY v1 */\n"
    assert s.count(a) == 1 and s.count(h) == 1, "func_table.c: run patch_carry.py first"
    module = r'''/* ---- %s: in a skip frame ProcessSoundCommandQueue $0013B6 does nothing: the game's own sound queue keeps the commands (tools/patch_sndclock.py) ---- */
extern int lk_snd_skipping(void);
static gen_func_t lk_o_psq;
static void lk_h_psq(void) { if (lk_snd_skipping()) return; lk_o_psq(); }
static void lk_sndclock_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_psq = func_table_lookup(0x0013B6);
    if (lk_o_psq) func_table_register(0x0013B6, lk_h_psq); else fprintf(stderr, "sndclock: ProcessSoundCommandQueue not found\n");
}
''' % VER
    s = s.replace(a, module + a, 1)
    s = s.replace(h, h + "        lk_sndclock_install();   /* %s */\n" % VER, 1)
    open(p, "w").write(s); print("func_table.c patched:", VER)
