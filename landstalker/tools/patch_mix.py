#!/usr/bin/env python3
"""Own sound mixer (2026-10-31, docs/SOUND_PLAN.md section 10): Genesis Plus GX's sound glue (core/sound/sound.c: YM2612 sync / BUSY / frame flush,
core/system.c: audio_update) dispatches to tools/lksnd_mix.c.  Env LANDSTALKER_MIX=gpgx = the old glue (reference for the audio capture A/B: sample identical).
Idempotent.  usage: patch_mix.py path/to/genrecomp   (after patch_chips.py; patch_sndsep / patch_sndtrace / patch_sndnative add the hooks it keeps)"""
import os, shutil, sys
core = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core"); here = os.path.dirname(os.path.abspath(__file__))
VER = "LK_MIX v1"
shutil.copy(os.path.join(here, "lksnd_mix.c"), os.path.join(core, "sound", "lksnd_mix.c"))

p = os.path.join(core, "sound", "sound.c"); s = open(p).read()
if VER not in s:
    def rep(a, b):
        global s
        assert s.count(a) == 1, a
        s = s.replace(a, b, 1)
    rep('#include "blip_buf.h"\n', '#include "blip_buf.h"\n#include "lksnd_mix.c"   /* %s: the sound mixer of our own (tools/patch_mix.py) */\n' % VER)
    def hook(sig, body):
        rep(sig, sig + "  if (lk_mix_own()) { " + body + " }   /* " + VER + " */\n")
    hook("static void YM2612_Reset(unsigned int cycles)\n{\n", "lkmix_ym_reset(cycles); return;")
    hook("static void YM2612_Write(unsigned int cycles, unsigned int a, unsigned int v)\n{\n", "lkmix_ym_write(cycles, a, v); return;")
    hook("static unsigned int YM2612_Read(unsigned int cycles, unsigned int a)\n{\n", "return lkmix_ym_read(cycles, a);")
    hook("void sound_reset(void)\n{\n", "lkmix_reset(); return;")
    hook("int sound_update(unsigned int cycles)\n{\n", "return lkmix_frame(cycles);")
    rep("int lk_fm_count(void) { return fm_cycles_count; }", "int lk_fm_count(void) { return lk_mix_own() ? lkmix_count : fm_cycles_count; }   /* %s */" % VER)
    rep("int lk_fm_busy(void) { return fm_cycles_busy; }", "int lk_fm_busy(void) { return lk_mix_own() ? lkmix_busy : fm_cycles_busy; }")
    open(p, "w").write(s); print("sound.c patched:", VER)

p = os.path.join(core, "system.c"); s = open(p).read()
if VER not in s:
    a = "int audio_update(int16 *buffer)\n{\n"
    assert s.count(a) == 1
    s = s.replace(a, "extern int lk_mix_own(void), lkmix_audio(int16 *buffer, unsigned int cycles);   /* %s */\n" % VER + a
                  + "  if (lk_mix_own()) return lkmix_audio(buffer, mcycles_vdp);   /* %s: tools/lksnd_mix.c */\n" % VER, 1)
    open(p, "w").write(s); print("system.c patched:", VER)
