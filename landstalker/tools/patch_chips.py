#!/usr/bin/env python3
"""Own sound chips (2026-10-29, docs/SOUND_PLAN.md section 9): switches Genesis Plus GX's chip cores for our own (tools/lksnd_psg.c, later lksnd_ym.c).
Env LANDSTALKER_CHIPS = comma list of the cores that are OURS: 'psg' (SN76489), 'ym' (YM2612, tools/lksnd_ym.c); default = see DEFAULT below; 'gpgx' / 'none' = all from GPGX (the old way).
The glue keeps the reference core in place (for A/B tests with the audio capture LANDSTALKER_WAV: the outputs must be sample identical).
Idempotent.  usage: patch_chips.py path/to/genrecomp   (after patch_sndsep.py, which adds the volume hooks lk_snd_unity / lk_snd_gain)"""
import os, re, shutil, sys
root = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core/sound"); here = os.path.dirname(os.path.abspath(__file__))
VER = "LK_CHIPS v2"
DEFAULT = "psg,ym"
shutil.copy(os.path.join(here, "lksnd_psg.c"), os.path.join(root, "lksnd_psg.c")); shutil.copy(os.path.join(here, "lksnd_ym.c"), os.path.join(root, "lksnd_ym.c"))
p = os.path.join(root, "psg.c"); s = open(p).read()
if VER not in s:
    inc = list(re.finditer(r'^#include .*\n', s, re.M))[-1]
    glue = '''
/* ---- %s: own PSG core (tools/lksnd_psg.c) next to the reference one; LANDSTALKER_CHIPS selects (see tools/patch_chips.py) ---- */
#include "lksnd_psg.c"
#include "lksnd_ym.c"   /* the YM2612 core of ours (its public functions are lkym_*) */
static int lk_psg_own_v = -1, lk_ym_own_v = -1;
int lk_ym_own(void) {
  if (lk_ym_own_v < 0) { const char *e = getenv("LANDSTALKER_CHIPS"); const char *l = (e && *e) ? e : "%s"; lk_ym_own_v = strstr(l, "ym") != NULL; if (lk_ym_own_v) fprintf(stderr, "chips: the YM2612 core is ours (tools/lksnd_ym.c)\\n"); }
  return lk_ym_own_v;
}
static int lk_psg_own(void) {
  if (lk_psg_own_v < 0) { const char *e = getenv("LANDSTALKER_CHIPS"); const char *l = (e && *e) ? e : "%s"; lk_psg_own_v = strstr(l, "psg") != NULL; if (lk_psg_own_v) fprintf(stderr, "chips: the PSG core is ours (tools/lksnd_psg.c)\\n"); }
  return lk_psg_own_v;
}
static void lk_psg_sink(unsigned t, int dl, int dr) { if (config.hq_psg) blip_add_delta(snd.blips[0], t, dl, dr); else blip_add_delta_fast(snd.blips[0], t, dl, dr); }
static int lk_psg_gain(int c) { extern int lk_snd_unity(void), lk_snd_gain(int); return lk_snd_unity() ? 256 : lk_snd_gain(c); }
''' % (VER, DEFAULT, DEFAULT)
    s = s[:inc.end()] + glue + s[inc.end():]
    def hook(sig, body):
        global s
        assert s.count(sig) == 1, sig
        s = s.replace(sig, sig + "  if (lk_psg_own()) { " + body + " }   /* " + VER + " */\n", 1)
    hook("void psg_init(PSG_TYPE type)\n{\n", "lkpsg_init(type == PSG_INTEGRATED, lk_psg_sink, lk_psg_gain); return;")
    hook("void psg_reset(void)\n{\n", "lkpsg_reset(); return;")
    hook("int psg_context_save(uint8 *state)\n{\n", "return lkpsg_save(state);")
    hook("int psg_context_load(uint8 *state)\n{\n", "return lkpsg_load(state);")
    hook("void psg_write(unsigned int clocks, unsigned int data)\n{\n", "lkpsg_write(clocks, data); return;")
    hook("void psg_config(unsigned int clocks, unsigned int preamp, unsigned int panning)\n{\n", "lkpsg_config(clocks, preamp, panning); return;")
    hook("void psg_end_frame(unsigned int clocks)\n{\n", "lkpsg_end_frame(clocks); return;")
    a = "int lk_psg_reg(int i) { return psg.regs[i]; }"
    assert s.count(a) == 1
    s = s.replace(a, "int lk_psg_reg(int i) { return lk_psg_own() ? lkpsg_reg(i) : psg.regs[i]; }   /* " + VER + " */")
    open(p, "w").write(s); print("psg.c patched:", VER)
else:
    print("psg.c already patched:", VER)

p = os.path.join(root, "ym2612.c"); s = open(p).read()
if VER not in s:
    inc = list(re.finditer(r'^#include .*\n', s, re.M))[-1]
    s = s[:inc.end()] + "extern int lk_ym_own(void);   /* %s */\nextern void lkym_init(void), lkym_reset(void), lkym_config(int), lkym_update(int *, int), lkym_write(unsigned int, unsigned int), lkym_state(int *);\nextern unsigned int lkym_read(void);\nextern int lkym_load(unsigned char *), lkym_save(unsigned char *), lkym_keymask(void);\n" % VER + s[inc.end():]
    def hook(sig, body):
        global s
        assert s.count(sig) == 1, sig
        s = s.replace(sig, sig + "  if (lk_ym_own()) { " + body + " }   /* " + VER + " */\n", 1)
    hook("void YM2612Init(void)\n{\n", "lkym_init(); return;")
    hook("void YM2612ResetChip(void)\n{\n", "lkym_reset(); return;")
    hook("void YM2612Write(unsigned int a, unsigned int v)\n{\n", "lkym_write(a, v); return;")
    hook("unsigned int YM2612Read(void)\n{\n", "return lkym_read();")
    hook("void YM2612Update(int *buffer, int length)\n{\n", "lkym_update(buffer, length); return;")
    hook("void YM2612Config(int type)\n{\n", "lkym_config(type); return;")
    hook("int YM2612LoadContext(unsigned char *state)\n{\n", "return lkym_load(state);")
    hook("int YM2612SaveContext(unsigned char *state)\n{\n", "return lkym_save(state);")
    for a, b in (("int lk_ym_keymask(void) { ", "if (lk_ym_own()) return lkym_keymask(); "), ("void lk_ym_state(int *v) { ", "if (lk_ym_own()) { lkym_state(v); return; } ")):
        assert s.count(a) == 1, a
        s = s.replace(a, a + b, 1)
    open(p, "w").write(s); print("ym2612.c patched:", VER)
