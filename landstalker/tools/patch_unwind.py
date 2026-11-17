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

rep("#include <stdio.h>\n", "#include <stdio.h>\n#include <setjmp.h>\n#ifdef _WIN32   /* mingw: _setjmp takes a frame argument, plain setjmp / longjmp are fine there */\n#define LK_SETJMP(b) setjmp(b)\n#define LK_LONGJMP(b, v) longjmp(b, v)\n#else\n#define LK_SETJMP(b) _setjmp(b)\n#define LK_LONGJMP(b, v) _longjmp(b, v)\n#endif\n")
rep("static uint32_t s_expect[512];\n",
    "static uint32_t s_expect[512];\n"
    "static jmp_buf s_jb[512];     /* where each frame's call can be unwound to */\n"
    "static int s_unwind_k;\n"
    "static uint32_t s_reset_to;   /* LK_RESETUNWIND v1: pending stack-reset target while unwinding to the bottom frame */\n")
rep("    if (e && r != e) {\n        if (func_table_lookup(r)) s_tail = r;",
    "    if (e && r != e) {\n"
    "        /* r is an outer frame's return address: that frame's callee was\n"
    "         * abandoned (return address dropped), unwind the C stack to it */\n"
    "        for (int i = d - 1; i >= 0 && i < 512; i--) {\n"
    "            if (s_expect[i] == r) { s_unwind_k = i; LK_LONGJMP(s_jb[i], 1); }\n"
    "        }\n"
    "        if (func_table_lookup(r)) s_tail = r;")
rep("    bool found = true;\n    do {\n        s_tail = 0;",
    "    bool found = true;\n"
    "    if (s_call_depth <= 512 && LK_SETJMP(s_jb[s_call_depth - 1]) != 0) {\n"
    "        if (s_reset_to) {   /* LK_RESETUNWIND v1: unwound to the bottom frame by a stack reset, run the reset code here */\n"
    "            m68k_addr = s_reset_to; s_reset_to = 0; s_tail = 0; s_call_depth = s_unwind_k + 1; found = true;\n"
    "        } else {\n"
    "        /* unwound to this frame by func_table_rts: this call has returned */\n"
    "        s_tail = 0;\n"
    "        s_call_depth = s_unwind_k;\n"
    "        return true;\n"
    "        }\n"
    "    }\n"
    "    do {\n        s_tail = 0;\n"
    "        if (s_call_depth > 1 && s_call_depth <= 512 && (m68k_addr == 0x0004B8u || m68k_addr == 0x0004BEu || m68k_addr == 0x0004DCu)) {\n"
    "            /* LK_RESETUNWIND v1 (2026-11-17, GitHub #20): ResetAll $0004B8 / EndGame $0004BE / GameOver $0004DC start with lea (ResetSP).w,sp: every 68K\n"
    "             * frame is gone, so the C frames are dropped too (bottom frame, then the reset code runs there). Without it EndGame from the priest's\n"
    "             * 'continue? no' (script $0250xx) ran the file select inside the old dialogue frames: the shadow call stack still held the text box routine,\n"
    "             * the renderer kept treating the frames as map / dialogue (Modern HUD drawn, save slots missing). The 68K state is not touched. */\n"
    "            s_reset_to = m68k_addr; s_unwind_k = 0; LK_LONGJMP(s_jb[0], 1);\n"
    "        }")
open(p, "w").write(s)
print("func_table.c patched")
