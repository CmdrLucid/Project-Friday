#!/usr/bin/env python3
"""genrecomp runtime (bus.c): VBlank watchdog + HInt time rebasing (idempotent). Apply after patch_perline.py.

 * Watchdog: if more than 3,000,000 bus accesses pass without a VBlank, print once (max 3x)
   "bus: WATCHDOG ..." with the last address, cycle counters, V counter and the shadow call stack.
   A normal frame needs a few tens of thousands of accesses, so this only fires on a real hang
   (spin loop inside an interrupt handler, a wait for a flag nothing will set, ...).
 * Interrupt rebasing (ALWAYS, not only when >= 1 line ahead: entry_diff=3107 of 3420 + the handler's 16-register
   push already crossed the line end and froze the counter): the H-Int handler (and a pending interrupt released when the SR mask drops) is dispatched from inside the scanline catch-up loop. If the
   emulated CPU is already a full line or more ahead of the scanline clock, GPGX's V counter
   (it only looks one line ahead) reads frozen, and a handler that waits for it to change
   (Landstalker's HandleHBlankInterrupt) would spin forever. Start the handler at the line's own
   time and add the time it used to the CPU clock afterwards.
usage: patch_watchdog.py path/to/genrecomp
"""
import sys, os

p = os.path.join(sys.argv[1], "src/bus.c")
s = open(p).read()
if "LANDSTALKER_WATCHDOG" in s:
    print("bus.c already patched: LANDSTALKER_WATCHDOG"); sys.exit(0)

def rep(old, new, count=1):
    global s
    assert old in s, f"bus.c layout changed: {old[:60]!r}"
    s = s.replace(old, new, count)

rep("static void bus_tick_cycles(void) {\n",
    "/* LANDSTALKER_WATCHDOG */\n"
    "static unsigned long s_since_vb;\n"
    "static int s_wd_trips;\n"
    "static bool s_in_tick;\n" if False else
    "/* LANDSTALKER_WATCHDOG */\n"
    "static unsigned long s_since_vb;\n"
    "static int s_wd_trips;\n"
    "static int s_irq_level, s_irq_rebased;\n"
    "static unsigned int s_irq_diff;\n"
    "__attribute__((constructor)) static void bus_wd_banner(void) {\n"
    "    fprintf(stderr, \"bus: watchdog v2 + interrupt rebasing active\\n\");\n"
    "}\n"
    "static void bus_irq_rebased(int level) {\n"
    "    static int off = -1;\n"
    "    s_irq_level = level; s_irq_diff = m68k.cycles - mcycles_vdp; s_irq_rebased = 0;\n"
    "    if (off < 0) off = getenv(\"LANDSTALKER_NOREBASE\") != NULL;\n"
    "    unsigned int real = m68k.cycles;\n"
    "    if (!off) {  /* always: a handler entered near the END of a line reads a frozen V counter */\n"
    "        unsigned int start = mcycles_vdp + 64;\n"
    "        s_irq_rebased = 1;\n"
    "        m68k.cycles = start;\n"
    "        recomp_m68k_interrupt(level);\n"
    "        m68k.cycles = real + (m68k.cycles - start);\n"
    "    } else {\n"
    "        recomp_m68k_interrupt(level);\n"
    "    }\n"
    "}\n\n"
    "static void bus_tick_cycles(void) {\n"
    "    if (++s_since_vb > 3000000UL && s_wd_trips < 3) {\n"
    "        s_wd_trips++; s_since_vb = 0;\n"
    "        fprintf(stderr, \"bus: WATCHDOG no VBlank for 3M bus accesses: last $%06X cycles=%u mcycles_vdp=%u v=%d inTick=%d pc=$%06X irqpend=%d mask=%d frame=%ld | last irq: level %d entry_diff=%u rebased=%d | hvc_latch=%x reg0=%02X reg1=%02X reg10=%02X lines/frame=%d, \",\n"
    "                s_last_addr, (unsigned)m68k.cycles, (unsigned)mcycles_vdp, (int)v_counter, (int)s_in_tick,\n"
    "                (unsigned)g_m68k.pc, (int)g_m68k_irq_pending, (int)g_m68k.int_mask, platform_frame_number(),\n"
    "                s_irq_level, s_irq_diff, s_irq_rebased, (unsigned)hvc_latch, reg[0], reg[1], reg[10], (int)lines_per_frame);\n"
    "        func_table_dump_stack(stderr);\n"
    "    }\n")
rep("        if (vblank_now && s_vblank_cb) s_vblank_cb();\n",
    "        if (vblank_now && s_vblank_cb) { s_since_vb = 0; s_vblank_cb(); }\n")
# both H-Int dispatch sites in the per-line code
n = s.count("recomp_m68k_interrupt(4);")
assert n >= 2, n
head, tail = s.split("static void bus_tick_cycles(void) {\n", 1)
# only replace inside bus_tick_cycles (after its definition), not inside bus_hint_irq
body_start = tail
body_start = body_start.replace("if (reg[0] & 0x10) recomp_m68k_interrupt(4);", "if (reg[0] & 0x10) bus_irq_rebased(4);")
# the interrupt held back by the SR mask and taken when the mask drops (this one hung the bridge scene)
old_pend = "    if (g_m68k_irq_pending > g_m68k.int_mask)\n        recomp_m68k_interrupt(g_m68k_irq_pending);"
assert old_pend in body_start, "pending-irq site changed"
body_start = body_start.replace(old_pend, "    if (g_m68k_irq_pending > g_m68k.int_mask)\n        bus_irq_rebased(g_m68k_irq_pending);")
s = head + "static void bus_tick_cycles(void) {\n" + body_start
open(p, "w").write(s)
print("bus.c patched: LANDSTALKER_WATCHDOG (", n, "H-Int sites seen )")
