#!/usr/bin/env python3
"""genrecomp runtime: GENRECOMP_CALLTRACE=lo:hi logs every function entry (idempotent).

Prints "T <frame> d=<depth> $<addr> ret=$<expected return>" to stderr for frames lo..hi, and
"T <frame> UNWIND ..." when an RTS unwinds abandoned C frames. Apply after patch_unwind.py.
usage: patch_calltrace.py path/to/genrecomp
"""
import sys, os

p = os.path.join(sys.argv[1], "src/func_table.c")
s = open(p).read()
if "GENRECOMP_CALLTRACE" in s:
    print("func_table.c calltrace already patched"); sys.exit(0)

def rep(old, new):
    global s
    assert old in s, f"layout changed: {old[:50]!r}"
    s = s.replace(old, new, 1)

rep("#include <stdio.h>\n",
    "#include <stdio.h>\n#include <stdlib.h>\n#include <genrecomp/platform.h>\n"
    "static int ct_on(void) {\n"
    "    static int init; static long lo = 1, hi = 0;\n"
    "    if (!init) { init = 1; const char *e = getenv(\"GENRECOMP_CALLTRACE\"); if (e) sscanf(e, \"%ld:%ld\", &lo, &hi); }\n"
    "    long f = platform_frame_number();\n"
    "    return f >= lo && f <= hi;\n"
    "}\n")
rep("            if (s_expect[i] == r) { s_unwind_k = i; _longjmp(s_jb[i], 1); }",
    "            if (s_expect[i] == r) {\n"
    "                if (ct_on()) fprintf(stderr, \"T %ld UNWIND depth %d -> %d (rts to $%06X)\\n\", platform_frame_number(), d, i, r);\n"
    "                s_unwind_k = i; _longjmp(s_jb[i], 1);\n"
    "            }")
rep("        s_stack[s_call_depth - 1] = m68k_addr;\n        fn();",
    "        s_stack[s_call_depth - 1] = m68k_addr;\n"
    "        if (ct_on()) fprintf(stderr, \"T %ld d=%d $%06X ret=$%06X\\n\", platform_frame_number(), s_call_depth, m68k_addr, ret);\n"
    "        fn();")
open(p, "w").write(s)
print("func_table.c calltrace patched")
