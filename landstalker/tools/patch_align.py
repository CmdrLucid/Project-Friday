#!/usr/bin/env python3
"""Align the VDP memories to 64 bytes (found 2026-10-15: crash of the zig / clang build in lk_quick_capture).

Genesis Plus GX defines `uint8 ALIGNED_(4) vram[0x10000]` but declares it `extern uint8 vram[0x10000]` in the header. clang assumes
the x86-64 ABI default (arrays of 16+ bytes are 16-byte aligned) for the extern declaration and auto-vectorises loops with ALIGNED
loads (vmovdqa); the linker may place the array at 8 mod 16 -> segfault.  gcc does not make that assumption, so the gcc build never
crashed.  Fix: give the definitions a real alignment of 64.   usage: patch_align.py path/to/genrecomp   (idempotent)
"""
import os, re, sys
root = sys.argv[1]
core = os.path.join(root, "ext/Genesis-Plus-GX/core")
n = 0
for fn in ("vdp_ctrl.c", "vdp_render.c"):
    p = os.path.join(core, fn)
    s = open(p).read()
    t = re.sub(r"ALIGNED_\(4\)( \w+\[)", r"ALIGNED_(64)\1", s)
    if t != s:
        n += len(re.findall(r"ALIGNED_\(64\)", t)) - len(re.findall(r"ALIGNED_\(64\)", s))
        t = "/* LK_ALIGN v1: arrays aligned to 64 bytes (tools/patch_align.py) */\n" + t
        open(p, "w").write(t)
print("patch_align: %d array definitions aligned" % n)
