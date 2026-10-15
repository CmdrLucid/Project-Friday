#!/usr/bin/env python3
"""GPGX m68kcpu.c: m68k_set_irq_delay() must not execute a CPU instruction (idempotent).

Root cause of the inn-map crash (win28-win31, gdb watchpoint): a VDP control-port write that changes the interrupt enables ends in
vdp_reg_w -> m68k_set_irq_delay(), which "finishes executing the current instruction" of GPGX's own Musashi core:
`REG_IR = m68ki_read_imm_16(); m68ki_instruction_jump_table[REG_IR]();`. The recompiled build never runs Musashi, so its PC/registers are stale
(it sits near the reset vector and creeps forward with every call); the instruction it executes there (here `movem.l regs,-(a7)`) writes the
Musashi registers (zeros) to Musashi's stack = the top of the game's work RAM -> the return address of the running function became 0.
The recompiled runtime delivers interrupts itself, so only the level is recorded, like m68k_set_irq().
usage: patch_irqdelay.py path/to/genrecomp
"""
import sys, os
p = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core/m68k/m68kcpu.c")
s = open(p).read()
if "LANDSTALKER_IRQDELAY" in s:
    print("m68kcpu.c already patched: LANDSTALKER_IRQDELAY"); sys.exit(0)
old = "void m68k_set_irq_delay(unsigned int int_level)\n{\n"
assert old in s, "m68kcpu.c: m68k_set_irq_delay layout changed"
new = old + ("  /* LANDSTALKER_IRQDELAY: never execute an instruction of the (idle) Musashi core here */\n"
             "  CPU_INT_LEVEL = int_level << 8;\n"
             "  return;\n")
open(p, "w").write(s.replace(old, new, 1)); print("m68kcpu.c patched: LANDSTALKER_IRQDELAY")
