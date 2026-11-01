#!/usr/bin/env python3
"""VDP data path of our own (docs/SOUND_PLAN.md section 12, step 3 of the way off the emulator): GPGX's core/vdp_ctrl.c dispatches to
tools/lkvdp.c (copied next to it and #included just before vdp_bus_w).  Marker LK_VDPPORT v1 = step 3.1: data port write
(store into lk_vm / lk_cm / lk_vsm, auto increment, widescreen hooks; GPGX's caches fed until step 3.5).
Env LANDSTALKER_VDP: unset / gpgx = GPGX (default until step 3.5), own = ours, check = both, compared after every data word
(summary on stderr + LANDSTALKER_VDP_CHECKLOG=<file>).  Idempotent.  usage: patch_vdpport.py path/to/genrecomp   (after patch_vdpmirror.py)"""
import os, shutil, sys
core = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core"); here = os.path.dirname(os.path.abspath(__file__))
VER = "LK_VDPPORT v1"
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
rep(decl, decl + "static int lkv_mode = -1; static void lkv_pull(void); static int lkv_bus_hook(unsigned int data); static void lkv_check_post(void);" + TAG)
BW = "static void vdp_bus_w(unsigned int data)\n{\n"
rep(BW, '#include "lkvdp.c"' + TAG + BW + "  if (lkv_mode && lkv_bus_hook(data)) return;" + TAG)
ins_in(BW, "  /* Increment address register */\n  addr += reg[15];\n", "  if (lkv_mode == 2) lkv_check_post();" + TAG)
# GPGX changed address / code: our copy follows (control port both words, fill, copy, reset)
CW = "void vdp_68k_ctrl_w(unsigned int data)\n{\n"
ins_in(CW, "    code = ((code & 0x3C) | ((data >> 14) & 0x03));\n", "    if (lkv_mode) lkv_pull();" + TAG)
ins_in(CW, "    code = ((code & 0x03) | ((data >> 2) & 0x3C));\n", "    if (lkv_mode) lkv_pull();" + TAG)
for fn in ("static void vdp_dma_fill(unsigned int length)\n{\n", "static void vdp_dma_copy(unsigned int length)\n{\n", "void vdp_reset(void)\n{\n"):
    at_end(fn, "  if (lkv_mode) lkv_pull();" + TAG)
open(p, "w").write(s)
print("vdp_ctrl.c patched:", VER)
