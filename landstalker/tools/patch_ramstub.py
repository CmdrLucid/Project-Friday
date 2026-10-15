#!/usr/bin/env python3
"""genrecomp runtime: follow `jmp (xxx).l` / `jmp (xxx).w` stubs the game writes
into RAM (Landstalker copies a 6-byte jmp to QueueDMAOp/DoDMACopy into
JmpInstr1 = $FF1850 and then does `jsr (JmpInstr1).l`). Idempotent.

usage: patch_ramstub.py path/to/genrecomp
"""
import sys, os

p = os.path.join(sys.argv[1], "src/func_table.c")
s = open(p).read()
if "RAM stub" in s:
    print("func_table.c ram stub already patched"); sys.exit(0)
old = "        gen_func_t fn = func_table_lookup(m68k_addr);\n        if (!fn) {"
new = ("        gen_func_t fn = func_table_lookup(m68k_addr);\n"
       "        if (!fn && m68k_addr >= 0xE00000) {\n"
       "            /* RAM stub written by the game: follow jmp (xxx).l / (xxx).w */\n"
       "            uint16_t op = bus_read16(m68k_addr);\n"
       "            if (op == 0x4EF9) { m68k_addr = bus_read32(m68k_addr + 2) & 0xFFFFFF; continue; }\n"
       "            if (op == 0x4EF8) { m68k_addr = (uint32_t)(int32_t)(int16_t)bus_read16(m68k_addr + 2) & 0xFFFFFF; continue; }\n"
       "        }\n"
       "        if (!fn) {")
assert old in s, "func_table.c layout changed"
open(p, "w").write(s.replace(old, new, 1))
print("func_table.c ram stub patched")
