#!/usr/bin/env python3
"""genrecomp bus.c: LANDSTALKER_GUARD=<hexaddr>:<hexvalue32> -- find who changes a 32-bit RAM value behind the bus's back (idempotent).

Armed when the 32-bit value at <hexaddr> (a work-RAM address like FFFFE8) equals <hexvalue32>; every bus tick compares it, and each change
is reported (first 8): old -> new, the previous bus access address (the access that caused the change), and the call stack.
Used for the stack slot of sub_24A78 ($FFFFE8 = $0001895E, return into the sprite code) that is zero when popped although no bus write
(not even through the work-RAM mirrors, see patch_watchfold.py) touched it.
usage: patch_guard.py path/to/genrecomp
"""
import sys, os
p = os.path.join(sys.argv[1], "src/bus.c")
s = open(p).read()
if "LANDSTALKER_GUARD" in s:
    print("bus.c already patched: LANDSTALKER_GUARD"); sys.exit(0)
old = "static void bus_tick_cycles(void) {\n"
assert old in s, "bus.c: bus_tick_cycles layout changed"
helper = r'''/* LANDSTALKER_GUARD=<hexaddr>:<hexvalue32> */
static void lk_guard_check(const char *where) {
    static long want = -2; static uint32_t armval, last; static int armed, reports;
    if (want == -2) {
        const char *e = getenv("LANDSTALKER_GUARD");
        want = -1;
        if (e) { char *c; want = (long)strtoul(e, &c, 16) & 0xFFFFFF; armval = (*c == ':') ? (uint32_t)strtoul(c + 1, NULL, 16) : 0; }
    }
    if (want < 0 || reports >= 8) return;
    cpu_memory_map *m = &m68k.memory_map[(want >> 16) & 0xFF];
    if (!m->base && !m->read16) return;
    uint32_t off = (uint32_t)want & 0xFFFF;
    uint32_t v = m->read16 ? (((uint32_t)m->read16(want) << 16) | (m->read16(want + 2) & 0xFFFF))
                           : (((uint32_t)*(uint16 *)(m->base + off) << 16) | *(uint16 *)(m->base + off + 2)); /* same read as bus_read16 (READ_WORD is endian-dependent) */
    { static int shown; if (!shown++) fprintf(stderr, "guard: watching $%06lX for %08X (now %08X, map base=%p read16=%p)\n", want, armval, v, (void *)m->base, (void *)m->read16); }
    if (!armed) { if (v == armval) { armed = 1; last = v; static int msg; if (msg++ < 3) fprintf(stderr, "guard: armed at $%06lX = %08X [%s]; ", want, v, where), func_table_dump_stack(stderr); } return; }
    if (v != last) {
        fprintf(stderr, "guard: $%06lX %08X -> %08X noticed at [%s]; previous bus access $%06X; vdp: dma_length=%u dma_type=%d status=%04X regs:", want, last, v, where, s_last_addr, (unsigned)dma_length, (int)dma_type, (unsigned)status);
        for (int i = 0; i < 24; i++) fprintf(stderr, " %02X", reg[i]);
        fprintf(stderr, "; ");
        func_table_dump_stack(stderr);
        last = v; reports++;
        if (v != armval && v != 0) { /* a legitimate new push: re-arm only on the original value */ armed = 0; }
    }
}

'''
s = s.replace(old, helper + old + "    lk_guard_check(\"tick start\");\n", 1)
# bracket the write handlers: handler itself vs. bus_finish_dma vs. the following tick
for w, bits in (("write16", "val"), ("write8", "val")):
    o = f"        map->{w}(addr, val);\n        if (region >= 0xC0 && region <= 0xDF) bus_finish_dma();\n"
    assert o in s, f"bus.c: {w} layout changed"
    s = s.replace(o, f"        lk_guard_check(\"before {w} handler\");\n        map->{w}(addr, val);\n        lk_guard_check(\"after {w} handler\");\n        if (region >= 0xC0 && region <= 0xDF) {{ bus_finish_dma(); lk_guard_check(\"after bus_finish_dma\"); }}\n", 1)
open(p, "w").write(s); print("bus.c patched: LANDSTALKER_GUARD")
