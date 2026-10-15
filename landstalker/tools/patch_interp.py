#!/usr/bin/env python3
"""TEMPORARY SAFETY NET (to be phased out, see docs/INDEX.md "Interpreter fallback policy"; it is a discovery tool for missing seeds).
genrecomp runtime: interpreter fallback for ROM code that has no recompiled function (idempotent).
Apply after patch_watchdog.py, patch_unwind.py, patch_calltrace.py (it edits bus.c and func_table.c).

When the dispatcher is asked to call a ROM address ($000000-$3FFFFF) with no generated function ("no function at"),
the code at that address now runs on Genesis Plus GX's own 68K interpreter (already linked, same memory map) until
it executes an RTS that pops the frame's return address. The popped address goes through the normal RTS-mismatch
logic (unwind to an outer frame, tail into a recompiled function, or plain return).
Per instruction: registers are copied to/from g_m68k, the bus clock is advanced (bus_tick_cycles: scanline clock,
VBlank callback, Z80, HInt) and pending VDP DMA is finished (as the recompiled bus does after VDP writes).
Logs "interp: running $XXXXXX ..." once per address (first 200); LANDSTALKER_INTERP_LOG=file appends every distinct address
(hex, one per line) for tools/seed_from_interp.py. LANDSTALKER_NOINTERP=1 disables it.
usage: patch_interp.py path/to/genrecomp
"""
import sys, os
root = sys.argv[1]

def patch(rel, old, new, marker):
    p = os.path.join(root, rel); s = open(p).read()
    if marker in s: print(rel, "already patched:", marker); return
    assert old in s, f"{rel}: layout changed ({old[:60]!r})"
    open(p, "w").write(s.replace(old, new, 1)); print(rel, "patched:", marker)

BUS_CODE = r'''
/* ================================================================
 * LANDSTALKER_INTERP: run ROM code that has no recompiled function on GPGX's 68K interpreter
 * ================================================================ */
static int s_interp_depth;
bool bus_interp_run(uint32_t addr, uint32_t *ret_pc) {
    unsigned int save[19]; int saved = 0;
    if (s_interp_depth > 0) {   /* nested (e.g. from a VBlank callback): keep the outer interpreter state */
        for (int i = 0; i < 8; i++) { save[i] = m68k_get_reg(M68K_REG_D0 + i); save[8 + i] = m68k_get_reg(M68K_REG_A0 + i); }
        save[16] = m68k_get_reg(M68K_REG_PC); save[17] = m68k_get_reg(M68K_REG_SR); saved = 1;
    }
    s_interp_depth++;
    const uint32_t base_sp = g_m68k.a[7];      /* points at the return address the caller pushed */
    m68k_set_reg(M68K_REG_SR, m68k_get_sr() | 0x2000);
    for (int i = 0; i < 8; i++) { m68k_set_reg(M68K_REG_D0 + i, g_m68k.d[i]); m68k_set_reg(M68K_REG_A0 + i, g_m68k.a[i]); }
    m68k_set_reg(M68K_REG_PC, addr);
    unsigned long steps = 0; bool done = false; uint32_t r = 0;
    while (!done) {
        uint32_t pc = m68k_get_reg(M68K_REG_PC) & 0xFFFFFF;
        cpu_memory_map *map = &m68k.memory_map[(pc >> 16) & 0xFF];
        uint16_t op = map->base ? *(uint16 *)(map->base + (pc & 0xFFFF)) : 0x4E71;
        bool is_rts = (op == 0x4E75);
        m68k.int_level = 0;                    /* the recompiled runtime delivers interrupts itself */
        m68k_run(m68k.cycles + 1);             /* exactly one instruction */
        for (int i = 0; i < 8; i++) { g_m68k.d[i] = m68k_get_reg(M68K_REG_D0 + i); g_m68k.a[i] = m68k_get_reg(M68K_REG_A0 + i); }
        g_m68k.pc = m68k_get_reg(M68K_REG_PC) & 0xFFFFFF;
        { unsigned int sr = m68k_get_reg(M68K_REG_SR); m68k_set_sr((uint16_t)sr); }
        if (is_rts && g_m68k.a[7] > base_sp) { r = g_m68k.pc; done = true; break; }
        if (dma_length) bus_finish_dma();
        bus_tick_cycles();                     /* scanline clock, VBlank/HInt callbacks, Z80 */
        if (++steps > 400000000UL) { fprintf(stderr, "interp: giving up in $%06X after %lu steps\n", addr, steps); break; }
    }
    s_interp_depth--;
    if (saved) {
        for (int i = 0; i < 8; i++) { m68k_set_reg(M68K_REG_D0 + i, save[i]); m68k_set_reg(M68K_REG_A0 + i, save[8 + i]); }
        m68k_set_reg(M68K_REG_PC, save[16]); m68k_set_reg(M68K_REG_SR, save[17]);
    }
    *ret_pc = r;
    return done;
}
'''
# bus.c: insert after bus_finish_dma() (needs it) -- before the watch section
patch("src/bus.c",
      "/* ================================================================\n * Write watchpoint:",
      BUS_CODE + "\n/* ================================================================\n * Write watchpoint:",
      "LANDSTALKER_INTERP")

# func_table.c: split func_table_rts so the interpreter can reuse the return-mismatch logic
patch("src/func_table.c",
      "void func_table_rts(void) {\n",
      "static void func_table_rts_r(uint32_t r);\nextern bool bus_interp_run(uint32_t addr, uint32_t *ret_pc);\n"
      "/* LANDSTALKER_RTSDUMP ring: last 64 RTS targets */\n"
      "static struct { uint32_t r, sp; int d; uint32_t top; } s_rts_ring[64]; static unsigned s_rts_n;\n"
      "static void rts_ring_dump(const char *why, uint32_t addr) {\n"
      "    fprintf(stderr, \"rtsdump: %s $%06X sp=$%08X depth=%d; last 64 returns (oldest first: target sp depth shadow-top):\\n\", why, addr, g_m68k.a[7], s_call_depth - 1);\n"
      "    for (unsigned i = s_rts_n > 64 ? s_rts_n - 64 : 0; i < s_rts_n; i++) fprintf(stderr, \"  $%06X sp=$%08X d=%d top=$%06X\\n\", s_rts_ring[i % 64].r, s_rts_ring[i % 64].sp, s_rts_ring[i % 64].d, s_rts_ring[i % 64].top);\n"
      "    { uint32_t base = (g_m68k.a[7] - 0x14) & 0xFFFFFF; fprintf(stderr, \"  stack words from sp-$14 ($%06X; sp is at the 11th word):\", base); for (int i = 0; i < 16; i++) fprintf(stderr, \" %04X\", bus_read16((base + 2 * i) & 0xFFFFFF) & 0xFFFF); fprintf(stderr, \"\\n\"); }\n"
      "}\n"
      "void lk_rts_dump(const char *why) { rts_ring_dump(why, 0); }\n"
      "/* LANDSTALKER_ENTRYDUMP=<hex>: print SP and the top stack words each time that function is entered (max 40) */\n"
      "static void lk_entry_dump(uint32_t a, uint32_t ret) {\n"
      "    static long want = -2; static int n;\n"
      "    if (want == -2) { const char *e = getenv(\"LANDSTALKER_ENTRYDUMP\"); want = e ? (long)strtoul(e, NULL, 16) : -1; }\n"
      "    if (want < 0 || a != (uint32_t)want || n++ >= 40) return;\n"
      "    fprintf(stderr, \"entrydump: enter $%06X depth=%d sp=$%08X expected-ret=$%06X stack words:\", a, s_call_depth, g_m68k.a[7], ret);\n"
      "    for (int i = 0; i < 12; i++) fprintf(stderr, \" %04X\", bus_read16(g_m68k.a[7] + 2 * i) & 0xFFFF);\n"
      "    fprintf(stderr, \"\\n\");\n"
      "}\n"
      "void func_table_rts(void) {\n",
      "func_table_rts_r(uint32_t r);")
patch("src/func_table.c",
      "    uint32_t r = bus_read32(g_m68k.a[7]) & 0xFFFFFF;\n    g_m68k.a[7] += 4;\n    int d = s_call_depth - 1;\n",
      "    uint32_t r = bus_read32(g_m68k.a[7]) & 0xFFFFFF;\n    g_m68k.a[7] += 4;\n    func_table_rts_r(r);\n}\n\n"
      "static void func_table_rts_r(uint32_t r) {\n    int d = s_call_depth - 1;\n",
      "func_table_rts_r(r);\n}")
patch("src/func_table.c",
      "        if (!fn) {\n            if (s_miss_count < 20",
      "        if (!fn && m68k_addr < 0x400000) {  /* LANDSTALKER_INTERP */\n"
      "            static int s_off = -1, s_logged;\n"
      "            if (s_off < 0) s_off = getenv(\"LANDSTALKER_NOINTERP\") != NULL;\n"
      "            if (!s_off) {\n"
      "                { /* record each address once: console (first 200) and LANDSTALKER_INTERP_LOG=file (for tools/seed_from_interp.py) */\n"
      "                    static uint32_t seen[8192]; static int nseen; int dup = 0;\n"
      "                    for (int i = 0; i < nseen; i++) if (seen[i] == m68k_addr) { dup = 1; break; }\n"
      "                    if (!dup && nseen < 8192) {\n"
      "                        seen[nseen++] = m68k_addr;\n"
      "                        if (getenv(\"LANDSTALKER_RTSDUMP\")) rts_ring_dump(\"interp starts at\", m68k_addr);\n"
      "                        if (s_logged < 200) { s_logged++; fprintf(stderr, \"interp: running $%06X on the 68K interpreter (no recompiled function)\\n\", m68k_addr); }\n"
      "                        const char *lf = getenv(\"LANDSTALKER_INTERP_LOG\");\n"
      "                        if (lf) { FILE *f = fopen(lf, \"a\"); if (f) { fprintf(f, \"%06X\\n\", m68k_addr); fclose(f); } }\n"
      "                    }\n"
      "                }\n"
      "                s_stack[s_call_depth - 1] = m68k_addr;\n"
      "                uint32_t r;\n"
      "                if (bus_interp_run(m68k_addr, &r)) func_table_rts_r(r);\n"
      "                m68k_addr = s_tail;\n"
      "                continue;\n"
      "            }\n"
      "        }\n"
      "        if (!fn) {\n            if (s_miss_count < 20",
      "LANDSTALKER_INTERP")

# diagnostics: ring buffer of the last 64 RTS targets; LANDSTALKER_RTSDUMP=<hex addr> dumps it plus 12 stack words when that
# address is returned to (used to find who leaves a stale return address on the stack)
patch("src/func_table.c",
      "static void func_table_rts_r(uint32_t r) {\n    int d = s_call_depth - 1;\n",
      "static void func_table_rts_r(uint32_t r) {\n    int d = s_call_depth - 1;\n"
      "    { /* LANDSTALKER_RTSDUMP */\n"
      "        static long want = -2;\n"
      "        if (want == -2) { const char *e = getenv(\"LANDSTALKER_RTSDUMP\"); want = e ? (long)strtoul(e, NULL, 16) : -1; }\n"
      "        s_rts_ring[s_rts_n % 64].r = r; s_rts_ring[s_rts_n % 64].sp = g_m68k.a[7]; s_rts_ring[s_rts_n % 64].d = d; s_rts_ring[s_rts_n % 64].top = d >= 0 ? s_stack[d] : 0; s_rts_n++;\n"
      "        if (want > 0 && r == (uint32_t)want) rts_ring_dump(\"RTS to\", r);\n"
      "    }\n",
      "s_rts_n++;")

# call the entry hook next to the calltrace line in the dispatch loop
patch("src/func_table.c",
      "        if (ct_on()) fprintf(stderr, \"T %ld d=%d $%06X ret=$%06X\\n\", platform_frame_number(), s_call_depth, m68k_addr, ret);\n",
      "        if (ct_on()) fprintf(stderr, \"T %ld d=%d $%06X ret=$%06X\\n\", platform_frame_number(), s_call_depth, m68k_addr, ret);\n"
      "        lk_entry_dump(m68k_addr, ret); /* LANDSTALKER_ENTRYDUMP */\n",
      "LANDSTALKER_ENTRYDUMP */")
