#!/usr/bin/env python3
"""VDP data path of our own (docs/SOUND_PLAN.md section 12, step 3 of the way off the emulator): GPGX's core/vdp_ctrl.c dispatches to
tools/lkvdp.c (copied next to it and #included just before vdp_bus_w).  Step 3.1: data port write (store into lk_vm / lk_cm / lk_vsm,
auto increment, widescreen hooks; GPGX's caches fed until step 3.5); marker LK_VDPPORT v2 = + step 3.2a: control port (command latch,
register file, DMA start decode); LK_VDPPORT v3 = + step 3.2b: register side effects (lkv_reg_w);
LK_VDPPORT v4 = + step 3.3: DMA engine (lkv_dma_update; needs our VDP timing).
Env LANDSTALKER_VDP: unset / gpgx = GPGX (default until step 3.5), own = ours, check = both, compared after every data word / control word
(summary on stderr + LANDSTALKER_VDP_CHECKLOG=<file>).  Idempotent.  usage: patch_vdpport.py path/to/genrecomp   (after patch_vdpmirror.py)"""
import os, shutil, sys
core = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core"); here = os.path.dirname(os.path.abspath(__file__))
VER = "LK_VDPPORT v4"
shutil.copy(os.path.join(here, "lkvdp.c"), os.path.join(core, "lkvdp.c"))
p = os.path.join(core, "vdp_ctrl.c"); s = open(p).read()
if VER in s:
    print("vdp_ctrl.c already patched:", VER); sys.exit(0)
TAG = "   /* %s */\n" % VER

def rep(a, b):
    global s
    assert s.count(a) == 1, f"vdp_ctrl.c layout changed: {a[:70]!r} ({s.count(a)}x)"
    s = s.replace(a, b, 1)

def func_span(func):
    f0 = s.find(func); assert f0 >= 0 and s.count(func) == 1, f"vdp_ctrl.c layout changed: {func[:60]!r}"
    return f0, s.find("\n}\n", f0) + 1      # the closing brace of the function (inner braces are indented)

def ins_in(func, anchor, text):
    """insert text after every `anchor` inside the function starting with `func` (at least once)"""
    global s
    f0, f1 = func_span(func); body = s[f0:f1]
    assert anchor in body, f"vdp_ctrl.c layout changed: {anchor[:60]!r} not in {func[:40]!r}"
    s = s[:f0] + body.replace(anchor, anchor + text) + s[f1:]

def at_end(func, text):
    global s
    f0, f1 = func_span(func)
    s = s[:f1] + text + s[f1:]

decl = "static void vdp_bus_w(unsigned int data);\n"
rep(decl, decl + "static int lkv_mode = -1; static void lkv_pull(void), lkv_pull_dmaregs(void), lkv_check_post(void); static int lkv_bus_hook(unsigned int data), lkv_ctrl_hook(unsigned int data);" + TAG)
BW = "static void vdp_bus_w(unsigned int data)\n{\n"
rep(BW, '#include "lkvdp.c"' + TAG + BW + "  if (lkv_mode && lkv_bus_hook(data)) return;" + TAG)
ins_in(BW, "  /* Increment address register */\n  addr += reg[15];\n", "  if (lkv_mode == 2) lkv_check_post();" + TAG)
# control port: ours (own mode) or GPGX's + ours compared (check mode)
CW = "void vdp_68k_ctrl_w(unsigned int data)\n{\n"
rep(CW, CW + "  if (lkv_mode && lkv_ctrl_hook(data)) return;" + TAG)
# GPGX changed address / code / registers outside the ports: our copy follows (fill, copy, reset)
for fn in ("static void vdp_dma_fill(unsigned int length)\n{\n", "static void vdp_dma_copy(unsigned int length)\n{\n", "void vdp_reset(void)\n{\n"):
    at_end(fn, "  if (lkv_mode) lkv_pull();" + TAG)
# DMA engine: ours (own mode) or GPGX's + ours predicted and compared (check mode)
DU = "void vdp_dma_update(unsigned int cycles)\n{\n"
rep(DU, DU + "  if (lkv_mode && lkv_dma_hook(cycles)) return;" + TAG)
# DMA end: GPGX's engine advanced the source / cleared the length registers (until step 3.3)
ins_in("void vdp_dma_update(unsigned int cycles)\n{\n", "      reg[19] = reg[20] = 0;\n", "      if (lkv_mode) lkv_pull_dmaregs();" + TAG)
# pending is cleared by a data write and by a status read
ins_in("static void vdp_68k_data_w_m5(unsigned int data)\n{\n", "  /* Clear pending flag */\n  pending = 0;\n", "  lkv.pending = 0;" + TAG)
rep("void lk_vdp_status_ack(void) { pending = 0; }", "void lk_vdp_status_ack(void) { pending = 0; lkv.pending = 0; }   /* LK_VDPPORT v2 */")
# check mode: GPGX's control port calls our comparing wrapper instead of vdp_reg_w for the 68K register writes
f0, f1 = func_span(CW); body = s[f0:f1]
a = "      vdp_reg_w((data >> 8) & 0x1F, data & 0xFF, m68k.cycles);\n"
s = s[:f0] + body.replace(a, "      if (lkv_mode == 2) lkv_reg_check((data >> 8) & 0x1F, data & 0xFF, m68k.cycles); else" + TAG + a) + s[f1:]
rep("static int lkv_bus_hook(unsigned int data), lkv_ctrl_hook(unsigned int data);", "static int lkv_bus_hook(unsigned int data), lkv_ctrl_hook(unsigned int data); static void lkv_reg_check(unsigned int r, unsigned int d, unsigned int cycles); static int lkv_dma_hook(unsigned int cycles);")
open(p, "w").write(s)
print("vdp_ctrl.c patched:", VER)

# the window clip state of GPGX's renderer, for the check mode snapshot
p = os.path.join(core, "vdp_render.c"); s = open(p).read()
if VER not in s:
    a = "void window_clip(unsigned int data, unsigned int sw)\n"
    assert s.count(a) == 1
    s = s.replace(a, "void *lk_clip_ptr(void) { return clip; }   /* %s */\nint lk_clip_bytes(void) { return (int)sizeof clip; }\n" % VER + a, 1)
    open(p, "w").write(s); print("vdp_render.c patched:", VER)
