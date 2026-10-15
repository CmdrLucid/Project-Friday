#!/usr/bin/env python3
"""Sound diagnostics + (later) separate music / effect volumes in the GPGX sound code (2026-10-13).
Phase 2: separate volumes for music and sound effects (0..100 %, default 100 = unchanged output). The driver (Z80 RAM, see docs/FORMATS.md 'Sound driver') keeps 14 channel blocks of 32 bytes
from Z80 $1300: YM1-6, PSG1-3, PSG noise, then the 'type 2' effect channels (they take over hardware FM channels 4-6 and the noise channel). A block with byte +3 == 0 is playing;
its stream pointer (+0/+1) is < $8000 for effects (stream in the driver's own RAM) and >= $8000 for music (banked ROM window). lk_snd_sfx_mask() turns that into a mask of hardware channels
(bits 0-5 FM, 6-9 PSG tone 1-3 / noise) that currently play an effect; YM2612Update scales out_fm[c] and psg_write scales the written volume with the music or effect gain.
Settings: ~/.landstalker_audio ("music effects talk", percent / percent / 0|1), env LANDSTALKER_VOL_MUSIC / _SFX.
Phase 1: LANDSTALKER_SNDLOG=file writes one line per frame: frame, YM2612 key-on mask (bit n = channel n+1 has a slot keyed on),
sum of |output| per FM channel (6 numbers) and the PSG volume registers (4 numbers, 15 = silent); LANDSTALKER_ZRAMDUMP=file appends the 8 KB Z80 RAM of every frame
(to find the sound driver's channel blocks, tools/sndlog.py reads both).
Idempotent.  usage: patch_sndsep.py path/to/genrecomp"""
import os, sys
root = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core/sound")
p = os.path.join(root, "ym2612.c")
s = open(p).read()
if "LK_SNDSEP" not in s:
    a = "void YM2612Update(int *buffer, int length)\n"
    assert s.count(a) == 1, "ym2612.c: YM2612Update layout changed"
    s = s.replace(a, '''/* LK_SNDSEP: diagnostics (tools/patch_sndsep.py) */
long long lk_ym_acc[6];
int lk_ym_keymask(void) { int m = 0; for (int c = 0; c < 6; c++) { if (ym2612.CH[c].SLOT[0].key || ym2612.CH[c].SLOT[1].key || ym2612.CH[c].SLOT[2].key || ym2612.CH[c].SLOT[3].key) m |= 1 << c; } return m; }
''' + a, 1)
    b = "    if (out_fm[0] > 8191) out_fm[0] = 8191;\n"
    assert s.count(b) == 1
    # accumulate after the clamps: find the end of the clamp block (out_fm[5] clamp)
    c = "    else if (out_fm[5] < -8192) out_fm[5] = -8192;\n"
    assert s.count(c) == 1, "ym2612.c: clamp block layout changed"
    s = s.replace(c, c + "    for (int lk_c = 0; lk_c < 6; lk_c++) lk_ym_acc[lk_c] += out_fm[lk_c] < 0 ? -out_fm[lk_c] : out_fm[lk_c];   /* LK_SNDSEP */\n", 1)
    open(p, "w").write(s)
p = os.path.join(root, "psg.c")
s = open(p).read()
if "LK_SNDSEP" not in s:
    a = "static void psg_update(unsigned int clocks);\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "/* LK_SNDSEP */\nint lk_psg_reg(int i) { return psg.regs[i]; }\n", 1)
    open(p, "w").write(s)
p = os.path.join(root, "sound.c")
s = open(p).read()
if "LK_SNDSEP" not in s:
    a = "int sound_update(unsigned int cycles)\n{\n"
    assert s.count(a) == 1
    helper = '''/* LK_SNDSEP: LANDSTALKER_SNDLOG / LANDSTALKER_ZRAMDUMP (tools/patch_sndsep.py) */
#include <stdio.h>
#include <stdlib.h>
extern long long lk_ym_acc[6]; extern int lk_ym_keymask(void); extern int lk_psg_reg(int i);
extern uint8 zram[0x2000];
static void lk_snd_log(void) {
    static FILE *lf, *zf; static int init; static long frame;
    if (!init) { const char *e = getenv("LANDSTALKER_SNDLOG"), *z = getenv("LANDSTALKER_ZRAMDUMP"); init = 1; if (e && *e) lf = fopen(e, "w"); if (z && *z) zf = fopen(z, "wb"); }
    frame++;
    if (lf) {
        fprintf(lf, "%ld k=%02X", frame, lk_ym_keymask());
        for (int i = 0; i < 6; i++) { fprintf(lf, " %lld", lk_ym_acc[i]); lk_ym_acc[i] = 0; }
        fprintf(lf, " psg"); for (int i = 1; i < 8; i += 2) fprintf(lf, " %d", lk_psg_reg(i));
        fprintf(lf, "\\n"); fflush(lf);
    }
    if (zf) { fwrite(zram, 1, 0x2000, zf); fflush(zf); }
}
'''
    s = s.replace(a, helper + a + "  lk_snd_log();   /* LK_SNDSEP */\n", 1)
    open(p, "w").write(s)

# ---- phase 2: volumes ----
p = os.path.join(root, "sound.c")
t = open(p).read()
if "LK_SNDSEP2" not in t:
    a = "/* LK_SNDSEP: LANDSTALKER_SNDLOG"
    assert a in t
    vol = r'''/* LK_SNDSEP2: separate music / effect volumes (tools/patch_sndsep.py) */
#include <stdio.h>
#include <stdlib.h>
int lk_vol_music = 100, lk_vol_sfx = 100, lk_talk_on = 1;   /* percent; talk: speech blips on (checked by the 68K hook) */
static int lk_vol_loaded;
static void lk_vol_path(char *buf, size_t n) { const char *h = getenv("HOME"); snprintf(buf, n, "%s/.landstalker_audio", h ? h : "."); }
static void lk_vol_load(void) {
    if (lk_vol_loaded) return; lk_vol_loaded = 1;
    char path[512]; lk_vol_path(path, sizeof path); FILE *f = fopen(path, "r");
    if (f) { int a, b, c; if (fscanf(f, "%d %d %d", &a, &b, &c) == 3) { lk_vol_music = a < 0 ? 0 : a > 100 ? 100 : a; lk_vol_sfx = b < 0 ? 0 : b > 100 ? 100 : b; lk_talk_on = c != 0; } fclose(f); }
    const char *e = getenv("LANDSTALKER_VOL_MUSIC"); if (e && *e) lk_vol_music = atoi(e) < 0 ? 0 : atoi(e) > 100 ? 100 : atoi(e);
    e = getenv("LANDSTALKER_VOL_SFX"); if (e && *e) lk_vol_sfx = atoi(e) < 0 ? 0 : atoi(e) > 100 ? 100 : atoi(e);
    e = getenv("LANDSTALKER_TALK"); if (e && *e) lk_talk_on = atoi(e) != 0;
}
void lk_snd_get(int *music, int *sfx, int *talk) { lk_vol_load(); *music = lk_vol_music; *sfx = lk_vol_sfx; *talk = lk_talk_on; }
void lk_snd_set(int music, int sfx, int talk) {
    lk_vol_loaded = 1; lk_vol_music = music < 0 ? 0 : music > 100 ? 100 : music; lk_vol_sfx = sfx < 0 ? 0 : sfx > 100 ? 100 : sfx; lk_talk_on = talk != 0;
    char path[512]; lk_vol_path(path, sizeof path); FILE *f = fopen(path, "w"); if (f) { fprintf(f, "%d %d %d\n", lk_vol_music, lk_vol_sfx, lk_talk_on); fclose(f); }
}
int lk_talk_enabled(void) { lk_vol_load(); return lk_talk_on; }
/* hardware channels (bit 0-5 FM, 6-8 PSG tone 1-3, 9 PSG noise) that are currently played by a sound effect */
int lk_snd_sfx_mask(void) {
    const uint8 *b = zram + 0x1300; int m = 0;
    #define LK_BLK(i) (b + (i) * 0x20)
    #define LK_ACT(i) (LK_BLK(i)[3] == 0)
    #define LK_PTR(i) (LK_BLK(i)[0] | (LK_BLK(i)[1] << 8))
    #define LK_SFXPTR(i) (LK_ACT(i) && LK_PTR(i) != 0 && LK_PTR(i) < 0x8000)
    for (int c = 0; c < 3; c++) if (LK_SFXPTR(c)) m |= 1 << c;
    for (int c = 3; c < 6; c++) if ((LK_ACT(10 + c - 3) && LK_PTR(10 + c - 3) != 0) || LK_SFXPTR(c)) m |= 1 << c;
    for (int c = 0; c < 3; c++) if (LK_SFXPTR(6 + c)) m |= 1 << (6 + c);
    if (LK_SFXPTR(9) || (LK_PTR(13) != 0 && LK_ACT(13))) m |= 1 << 9;
    return m;
}
/* gain 0..256 for hardware channel hw (0-5 FM, 6-9 PSG) right now */
int lk_snd_gain(int hw) { lk_vol_load(); int v = (lk_snd_sfx_mask() >> hw) & 1 ? lk_vol_sfx : lk_vol_music; return v * 256 / 100; }
int lk_snd_unity(void) { lk_vol_load(); return lk_vol_music == 100 && lk_vol_sfx == 100; }
'''
    t = t.replace(a, vol + a, 1)
    t = t.replace('extern uint8 zram[0x2000];\nstatic void lk_snd_log', 'extern uint8 zram[0x2000];\nstatic void lk_snd_log', 1)
    # the log line gets the effect mask
    b = '        fprintf(lf, " psg"); for (int i = 1; i < 8; i += 2) fprintf(lf, " %d", lk_psg_reg(i));\n'
    assert b in t
    t = t.replace(b, b + '        fprintf(lf, " sfx=%03X", lk_snd_sfx_mask());\n', 1)
    open(p, "w").write(t)
    # zram is declared after the volume block: move the extern up
    t = open(p).read()
    t = t.replace("/* LK_SNDSEP2: separate", "extern uint8 zram[0x2000];\n/* LK_SNDSEP2: separate", 1)
    open(p, "w").write(t)
p = os.path.join(root, "ym2612.c")
t = open(p).read()
if "LK_SNDSEP2" not in t:
    a = "    else if (out_fm[5] < -8192) out_fm[5] = -8192;\n"
    assert t.count(a) == 1
    t = t.replace(a, a + "    if (lk_gain_on) { for (int lk_c = 0; lk_c < 6; lk_c++) out_fm[lk_c] = out_fm[lk_c] * lk_gain[lk_c] >> 8; }   /* LK_SNDSEP2 */\n", 1)
    a = "void YM2612Update(int *buffer, int length)\n{\n  int i;\n  int lt,rt;\n"
    assert t.count(a) == 1
    t = t.replace(a, a + "  extern int lk_snd_unity(void), lk_snd_gain(int hw); int lk_gain[6], lk_gain_on = !lk_snd_unity();   /* LK_SNDSEP2 */\n  if (lk_gain_on) for (int lk_c = 0; lk_c < 6; lk_c++) lk_gain[lk_c] = lk_snd_gain(lk_c);\n", 1)
    open(p, "w").write(t)
p = os.path.join(root, "psg.c")
t = open(p).read()
if "LK_SNDSEP2" not in t:
    a = "      data = chanVolume[data & 0x0f];\n"
    assert t.count(a) == 2
    parts = t.split(a)
    # first occurrence = tone channels (i = index >> 1 is defined above it), second = noise; the file order is noise first (case 7) then default: check by context
    first_is_noise = "case 7" in parts[0].rsplit("switch (index)", 1)[-1]
    assert first_is_noise
    t = parts[0] + a + "      { extern int lk_snd_unity(void), lk_snd_gain(int); if (!lk_snd_unity()) data = data * lk_snd_gain(9) >> 8; }   /* LK_SNDSEP2 */\n" + parts[1] + a + "      { extern int lk_snd_unity(void), lk_snd_gain(int); if (!lk_snd_unity()) data = data * lk_snd_gain(6 + i) >> 8; }   /* LK_SNDSEP2 */\n" + parts[2]
    open(p, "w").write(t)
print("sound code patched: LK_SNDSEP phase 1 + 2")
