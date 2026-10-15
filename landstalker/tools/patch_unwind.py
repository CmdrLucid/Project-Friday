#!/usr/bin/env python3
"""genrecomp runtime: let RTS unwind abandoned C call frames (idempotent).

68K code sometimes drops its own return address (movem.l (sp)+,d0 / addq #4,sp)
and jumps back into the caller (Landstalker's text printer does this). The RTS
that finally runs then returns to an OUTER caller's pushed address. If that
address matches the return address an outer C frame is waiting for, longjmp to
that frame so it "returns" and everything above it is discarded.

usage: patch_unwind.py path/to/genrecomp
"""
import sys, os

p = os.path.join(sys.argv[1], "src/func_table.c")
s = open(p).read()
if "s_unwind_k" in s:
    print("func_table.c already patched"); sys.exit(0)

def rep(old, new):
    global s
    assert old in s, f"layout changed: {old[:50]!r}"
    s = s.replace(old, new, 1)

rep("#include <stdio.h>\n", "#include <stdio.h>\n#include <setjmp.h>\n")
rep("static uint32_t s_expect[512];\n",
    "static uint32_t s_expect[512];\n"
    "static jmp_buf s_jb[512];     /* where each frame's call can be unwound to */\n"
    "static int s_unwind_k;\n")
rep("    if (e && r != e) {\n        if (func_table_lookup(r)) s_tail = r;",
    "    if (e && r != e) {\n"
    "        /* r is an outer frame's return address: that frame's callee was\n"
    "         * abandoned (return address dropped), unwind the C stack to it */\n"
    "        for (int i = d - 1; i >= 0 && i < 512; i--) {\n"
    "            if (s_expect[i] == r) { s_unwind_k = i; _longjmp(s_jb[i], 1); }\n"
    "        }\n"
    "        if (func_table_lookup(r)) s_tail = r;")
rep("    bool found = true;\n    do {\n        s_tail = 0;",
    "    bool found = true;\n"
    "    if (s_call_depth <= 512 && _setjmp(s_jb[s_call_depth - 1]) != 0) {\n"
    "        /* unwound to this frame by func_table_rts: this call has returned */\n"
    "        s_tail = 0;\n"
    "        s_call_depth = s_unwind_k;\n"
    "        return true;\n"
    "    }\n"
    "    do {\n        s_tail = 0;")
open(p, "w").write(s)
print("func_table.c patched")
