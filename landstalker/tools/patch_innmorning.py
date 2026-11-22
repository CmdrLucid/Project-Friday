#!/usr/bin/env python3
"""LK_INNMORNING v1 (GitHub #24, 2026-11-22): a night at the inn ends in the morning.
HandleInnStay $025044 (the innkeeper's 'rest' answer: pay, fade to black, inn music, heal, fade in) calls FadeFromBlack_0 $029ADC once,
after the rest; a wrapper of FadeFromBlack_0 sets the Day / Night clock (lk_dn_t of tools/patch_lights.py) to 07:00 when HandleInnStay is
on the game's call stack, while the picture is still black. Only with Options > Graphics > Day / Night on (the clock does not run
otherwise); the game itself is untouched (bit exact). Console: 'inn: morning (hh:mm -> 07:00)'. Test aid LANDSTALKER_INN_HOUR=h (other hour).
Runs after patch_lights.py and patch_altpad.py. Idempotent.  usage: patch_innmorning.py path/to/genrecomp"""
import os, sys
VER = "LK_INNMORNING v1"
root = sys.argv[1]

def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed: " + old[:90]
    return s.replace(old, new)

# 1. vdp_render.c: set the clock (lk_dn_t / lk_dn_save live there, tools/patch_lights.py)
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER in s:
    print("vdp_render.c already patched: " + VER)
else:
    a = "static void lk_dn_save(void) {"
    i = s.index(a); j = s.index("\n", i) + 1   # after the one-line lk_dn_save
    fn = ("void lk_dn_morning(void) {   /* " + VER + ": the inn rest ends at 07:00 (only with Day / Night on) */\n"
          "  double h = 7.0; const char *e = getenv(\"LANDSTALKER_INN_HOUR\"); double old = lk_dn_t;\n"
          "  if (!lk_dn_get()) return;\n"
          "  if (e && *e) h = fmod(atof(e) + 24.0, 24.0);\n"
          "  if (lk_dn_t < 0.0) old = 9.0;\n"
          "  lk_dn_t = h; lk_dn_save();\n"
          "  printf(\"inn: morning (%02d:%02d -> %02d:%02d)\\n\", (int)old, (int)(fmod(old, 1.0) * 60.0), (int)h, (int)(fmod(h, 1.0) * 60.0)); fflush(stdout);\n"
          "}\n")
    s = s[:j] + fn + s[j:]
    open(p, "w").write(s)
    print("vdp_render.c patched: " + VER)

# 2. func_table.c: the wrapper of FadeFromBlack_0
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
else:
    assert "LK_ALTPAD v1" in s, "func_table.c: run patch_altpad.py first"
    module = r'''/* ---- ''' + VER + r''': a night at the inn ends in the morning (tools/patch_innmorning.py, GitHub #24) ---- */
extern void lk_dn_morning(void);
extern int func_table_depth(void);
extern uint32_t func_table_stack(int k);
static gen_func_t lk_inn_o_ffb;
static void lk_inn_h_ffb(void) {   /* FadeFromBlack_0 $029ADC: inside HandleInnStay $025044 = the fade-in after the rest */
    int i, d = func_table_depth();
    for (i = 0; i < d; i++) if (func_table_stack(i) == 0x025044u) { lk_dn_morning(); break; }
    lk_inn_o_ffb();
}
static void lk_inn_install(void) {   /* once per run (a second wrap would call itself) */
    static int done; if (done) return; done = 1;
    lk_inn_o_ffb = func_table_lookup(0x029ADCu);
    if (lk_inn_o_ffb) func_table_register(0x029ADCu, lk_inn_h_ffb); else fprintf(stderr, "inn: FadeFromBlack_0 not found\n");
}
'''
    a = "void func_table_init(void) {"
    s = rep(s, a, module + a, "func_table.c init")
    h = "        lk_altpad_install();   /* LK_ALTPAD v1 */\n"
    s = rep(s, h, h + "        lk_inn_install();   /* " + VER + " */\n", "func_table.c install hook")
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)
