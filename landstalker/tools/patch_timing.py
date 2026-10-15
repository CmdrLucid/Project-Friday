#!/usr/bin/env python3
"""68000 instruction timing for the recompiled code (INDEX open item 6).

Problem: genrecomp's bus.c charged only 28 master clocks per *data* bus access; instruction fetches, ALU,
shift, mul/div and branch costs were free, so the recompiled game ran ~40 frames ahead of the real core.

Fix, two parts:
 1. generate.py: every basic block (run of instructions between labels / control-flow / hardware accesses) is
    preceded by `bus_add_cycles(N)`: N = sum of the per-opcode cycle counts of GPGX's own Musashi table
    (ext/Genesis-Plus-GX/core/m68k/m68ki_cycles.h, the table the reference core uses, so ref and rec agree).
    Dynamic costs are emitted exactly like Musashi: Bcc taken/not taken, DBcc, Scc, MOVEM per register, shifts by
    count, MULU/MULS/DIVU/DIVS (data dependent), TRAP.
 2. bus.c: data bus accesses become free (the opcode table already includes them) and `bus_add_cycles` /
    `bus_add_mclk` advance the same clock through the same scanline/Z80/VBlank machinery as before.
    LANDSTALKER_OLDTIMING=1 restores the old behaviour (28 per access, no block costs) for A/B comparison.

usage: patch_timing.py path/to/genrecomp   (idempotent; run after the other bus.c/generate.py patches)
"""
import os
import sys

root = sys.argv[1]

# ---------------------------------------------------------------- bus.c / bus.h
p = os.path.join(root, "src/bus.c")
s = open(p).read()
if "LANDSTALKER_TIMING" in s:
    print("bus.c timing already patched")
else:
    old = "static void bus_tick_cycles(void) {"
    assert s.count(old) == 1, "bus.c: bus_tick_cycles layout changed"
    s = s.replace(old, "/* LANDSTALKER_TIMING: cycle sink shared by data accesses and per-block instruction costs */\n"
                       "static void bus_advance_inner(unsigned int mc);\n"
                       "static unsigned int s_expected_cycles; static unsigned long long s_stolen[4]; static unsigned int s_max_jump, s_max_jump_addr;\n"
                       "static void bus_advance(unsigned int mc) {\n"
                       "    unsigned int before = m68k.cycles;\n"
                       "    if (before > s_expected_cycles && before - s_expected_cycles < 0x10000000u) {\n"
                       "        unsigned int d = before - s_expected_cycles;\n"
                       "        unsigned int r = (s_last_addr >> 16) & 0xFF;\n"
                       "        s_stolen[r == 0xC0 ? 0 : (r == 0xA0 || r == 0xA1 || r == 0xA1) ? 1 : (r >= 0xFF || r < 0x40) ? 2 : 3] += d;\n"
                       "        if (d > s_max_jump) { s_max_jump = d; s_max_jump_addr = s_last_addr; }\n"
                       "        { static int rep; if (d > 20000 * 7 && s_expected_cycles && rep++ < 6) {\n"
                       "            fprintf(stderr, \"timing: clock jumped %u cycles behind the bus after $%06X: dma_length=%u dma_type=%d dma_endCycles=%u status=%04X reg1=%02X reg12=%02X v=%d cycles=%u mcycles_vdp=%u expected=%u | \",\n"
                       "                    d / 7, s_last_addr, (unsigned)dma_length, (int)dma_type, (unsigned)dma_endCycles, (unsigned)status, reg[1], reg[12], (int)v_counter, before, (unsigned)mcycles_vdp, s_expected_cycles);\n"
                       "            func_table_dump_stack(stderr); } }\n"
                       "    }\n"
                       "    bus_advance_inner(mc);\n"
                       "    s_expected_cycles = m68k.cycles;\n"
                       "}\n"
                       "static void bus_advance_inner(unsigned int mc) {", 1)
    old = "    m68k.cycles += BUS_CYCLES_PER_ACCESS;\n"
    assert s.count(old) == 1, "bus.c: cycle increment layout changed"
    s = s.replace(old, "    m68k.cycles += mc;\n", 1)
    marker = "/* ================================================================\n * Instant VDP DMA"
    assert s.count(marker) == 1, "bus.c: DMA section marker changed"
    helpers = r'''
/* LANDSTALKER_TIMING: the opcode cycle table (m68ki_cycles) already includes the data accesses of an instruction,
 * so a bus access itself is free unless LANDSTALKER_OLDTIMING=1 (old model: 28 master clocks per access). */
static int s_old_timing = -1;
__attribute__((constructor)) static void bus_timing_banner(void) {
    fprintf(stderr, "timing: patch_timing v4 (block cycles, DMA stall model, jump report) active\n");
}
static int bus_old_timing(void) {
    if (s_old_timing < 0) s_old_timing = getenv("LANDSTALKER_OLDTIMING") != NULL;
    return s_old_timing;
}
static void bus_tick_cycles(void) { bus_advance(bus_old_timing() ? 28 : 0); }
/* The Genesis steals 2 CPU cycles for DRAM refresh every 128 cycles of execution (Musashi: refresh_cycles) */
static unsigned int s_refresh_acc;
int lk_irq_ctx;                                   /* 0 = main thread, else the interrupt level being served */
static unsigned long long s_ctx_mc[8], s_ctx_n[8], s_ctx_instr;
static unsigned int s_max_lead;
static void bus_cycstat(unsigned int mclk) {
    static int on = -1; static long last = -1;
    if (on < 0) on = getenv("LANDSTALKER_CYCSTAT") != NULL;
    if (!on) return;
    s_ctx_mc[lk_irq_ctx & 7] += mclk; s_ctx_n[lk_irq_ctx & 7]++;
    { unsigned int lead = m68k.cycles - mcycles_vdp; if (lead > s_max_lead && lead < 0x10000000u) s_max_lead = lead; }
    long f = platform_frame_number();
    if (f != last && f % 60 == 0) {
        last = f;
        fprintf(stderr, "cycstat frame %ld: 68K cycles/frame main=%llu vint(6)=%llu hint(4)=%llu other=%llu | blocks main=%llu hint=%llu | max lead %u lines | clock jumps/frame behind our back (VDP=%llu IO/Z80=%llu RAM/ROM=%llu other=%llu) biggest %u cycles after $%06X\n", f,
                s_ctx_mc[0] / 7 / 60, s_ctx_mc[6] / 7 / 60, s_ctx_mc[4] / 7 / 60,
                (s_ctx_mc[1] + s_ctx_mc[2] + s_ctx_mc[3] + s_ctx_mc[5] + s_ctx_mc[7]) / 7 / 60, s_ctx_n[0] / 60, s_ctx_n[4] / 60, s_max_lead / 3420,
                s_stolen[0] / 7 / 60, s_stolen[1] / 7 / 60, s_stolen[2] / 7 / 60, s_stolen[3] / 7 / 60, s_max_jump / 7, s_max_jump_addr);
        s_max_lead = 0; s_max_jump = 0; for (int i = 0; i < 4; i++) s_stolen[i] = 0;
        for (int i = 0; i < 8; i++) s_ctx_mc[i] = s_ctx_n[i] = 0;
    }
}
static void bus_charge(unsigned int mclk) {
    unsigned int steal = 0;
    bus_cycstat(mclk);
    s_refresh_acc += mclk;
    while (s_refresh_acc >= 128 * 7) { s_refresh_acc -= 128 * 7; steal += 2 * 7; }
    bus_advance(mclk + steal);
}
void bus_add_cycles(unsigned int cycles) { if (!bus_old_timing()) bus_charge(cycles * 7); }
void bus_add_mclk(unsigned int mclk)     { if (!bus_old_timing()) bus_charge(mclk); }

/* Data dependent 68000 timings, same formulas as Musashi (m68kops.h UseMulu/Muls/Divu/DivsCycles), master clocks */
unsigned int bus_mulu_mclk(uint16_t src) {
    unsigned int mc = 38 * 7;
    while (src) { if (src & 1) mc += 2 * 7; src >>= 1; }
    return mc;
}
unsigned int bus_muls_mclk(int16_t src) {
    unsigned int mc = 38 * 7;
    int32_t tmp = ((int32_t)src << 1);
    tmp = (tmp ^ src) & 0xFFFF;
    while (tmp) { if (tmp & 1) mc += 2 * 7; tmp >>= 1; }
    return mc;
}
unsigned int bus_divu_mclk(uint32_t dst, uint16_t divisor) {
    if (divisor == 0) return 0;                       /* zero-divide exception: not modelled */
    if (dst / divisor >= 0x10000) return 10 * 7;      /* overflow */
    uint32_t src = (uint32_t)divisor << 16;
    unsigned int mc = 76 * 7;
    for (int i = 0; i < 15; i++) {
        if ((int32_t)dst < 0) { dst <<= 1; dst -= src; }
        else { dst <<= 1; mc += 4 * 7; if (dst >= src) { dst -= src; mc -= 2 * 7; } }
    }
    return mc;
}
unsigned int bus_divs_mclk(int32_t dst, int16_t src) {
    if (src == 0) return 0;
    unsigned int mc = 12 * 7;
    if (dst < 0) mc += 2 * 7;
    if ((abs(dst) >> 16) < abs(src)) {
        uint32_t quotient = abs(dst) / abs(src);
        mc += 110 * 7;
        if (src >= 0) { if (dst >= 0) mc -= 2 * 7; else mc += 2 * 7; }
        for (int i = 0; i < 15; i++) { quotient >>= 1; if (!(quotient & 1)) mc += 2 * 7; }
    } else {
        mc += 4 * 7;
    }
    return mc;
}

'''
    s = s.replace(marker, helpers + marker, 1)

    # 68K-bus DMA: GPGX's control-port write handler halts the 68K (m68k.cycles = dma_endCycles) using the current
    # display state and a clock that may be many lines ahead of the VDP -> single stalls of 1+ frames (clock jumps of
    # 187611 cycles after $C00004 on the Deck: textboxes crawled). Restore the pre-write clock and charge only the
    # transfer time at the blanking rate (what the game assumes: it DMAs in VBlank).
    helpers2 = "static unsigned int s_dma_pre; static int s_dma_pre_valid;   /* LANDSTALKER_TIMING */\n"
    s = s.replace("static int s_old_timing = -1;", helpers2 + "static int s_old_timing = -1;", 1)
    for w in ("write16", "write8"):
        old = f"map->{w}(addr, val);"
        assert s.count(old) == 1, f"bus.c: {w} call layout changed"
        s = s.replace(old, f"s_dma_pre = m68k.cycles; s_dma_pre_valid = 1; {old}", 1)
    old = "static void bus_finish_dma(void) {\n    if (!dma_length) return;\n    unsigned int saved_cycles = m68k.cycles;\n"
    assert s.count(old) == 1, "bus.c: bus_finish_dma head changed"
    s = s.replace(old, "static void bus_finish_dma(void) {\n    int pre_ok = s_dma_pre_valid; s_dma_pre_valid = 0;\n"
                       "    unsigned int j0 = 0, rate_used = 1, rate_blank = 1;   /* DMA started by this control-port write: stall GPGX already applied */\n"
                       "    if (pre_ok && !bus_old_timing() && (s_last_addr & 0xFFFFE0) == 0xC00000 && (s_last_addr & 0x1C) == 0x04 && dma_type < 2 &&\n"
                       "        m68k.cycles > s_dma_pre && m68k.cycles - s_dma_pre >= 4 * 7 && m68k.cycles - s_dma_pre < 0x10000000u) {\n"
                       "        int h40 = reg[12] & 1;\n"
                       "        rate_blank = (h40 ? 204 : 166) >> (dma_type & 1);\n"
                       "        rate_used = (((status & 8) || !(reg[1] & 0x40)) ? (h40 ? 204 : 166) : (h40 ? 18 : 16)) >> (dma_type & 1);\n"
                       "        j0 = m68k.cycles - s_dma_pre;\n"
                       "    }\n"
                       "    if (!dma_length) {   /* the whole DMA ran inside the register write */\n"
                       "        if (j0) {\n"
                       "            unsigned int st = (unsigned int)((unsigned long long)j0 * rate_used / rate_blank);\n"
                       "            static int rep; if (j0 > 20000 * 7 && rep++ < 6)\n"
                       "                fprintf(stderr, \"timing: DMA done in write: GPGX stall %u cycles -> %u at blanking rate (status=%04X v=%d reg1=%02X)\\n\", j0 / 7, st / 7, (unsigned)status, (int)v_counter, reg[1]);\n"
                       "            m68k.cycles = s_dma_pre + st;\n"
                       "        }\n"
                       "        return;\n"
                       "    }\n"
                       "    unsigned int dma_len0 = dma_length; int dma_type0 = dma_type;\n"
                       "    unsigned int saved_cycles = m68k.cycles;\n", 1)
    old = "    m68k.cycles = saved_cycles;  /* 68K-bus DMA stalls the CPU; we don't */\n"
    assert s.count(old) == 1, "bus.c: bus_finish_dma tail changed"
    s = s.replace(old, '''    if (bus_old_timing() || !pre_ok) {
        m68k.cycles = saved_cycles;
    } else {
        unsigned int stall = 0;
        if (dma_type0 < 2) {   /* 68K-bus DMA halts the 68K for the transfer time (blanking rate, bytes per line) */
            unsigned int rate = ((reg[12] & 1) ? 204 : 166) >> (dma_type0 & 1);
            stall = (unsigned int)(((unsigned long long)dma_len0 * MCYCLES_PER_LINE) / rate);
        }
        { static int rep; if (stall > 20000 * 7 && rep++ < 6)
              fprintf(stderr, "timing: DMA len=%u type=%d stall=%u cycles status=%04X v=%d reg1=%02X\\n", dma_len0, dma_type0, stall / 7, (unsigned)status, (int)v_counter, reg[1]); }
        if (j0) stall += (unsigned int)((unsigned long long)j0 * rate_used / rate_blank);   /* first chunk, scaled to the blanking rate */
        m68k.cycles = s_dma_pre + stall;
    }
''', 1)
    old = "if (dma_length) bus_finish_dma();"
    assert s.count(old) == 1, "bus.c: interp DMA call changed"
    s = s.replace(old, "s_dma_pre_valid = 0; " + old, 1)   # inside the interpreter the stall is already in m68k.cycles
    open(p, "w").write(s)
    print("bus.c patched: LANDSTALKER_TIMING")

p = os.path.join(root, "include/genrecomp/bus.h")
h = open(p).read()
if "bus_add_cycles" not in h:
    decl = '''
/* LANDSTALKER_TIMING: instruction timing emitted by the recompiler */
void bus_add_cycles(unsigned int cycles);   /* 68000 cycles */
void bus_add_mclk(unsigned int mclk);       /* master clocks (cycles * 7) */
unsigned int bus_mulu_mclk(uint16_t src);
unsigned int bus_muls_mclk(int16_t src);
unsigned int bus_divu_mclk(uint32_t dst, uint16_t divisor);
unsigned int bus_divs_mclk(int32_t dst, int16_t src);
'''
    anchor = "/* Get pointer to ROM data */"
    assert anchor in h, "bus.h layout changed"
    h = h.replace(anchor, decl.lstrip("\n") + "\n" + anchor, 1)
    open(p, "w").write(h)
    print("bus.h patched")

# interrupt entry: 44 cycles (Musashi CYC_EXCEPTION for autovectors); the handler's RTE is charged as an instruction
p = os.path.join(root, "src/m68k.c")
m = open(p).read()
if "LANDSTALKER_TIMING" not in m:
    old = "    func_table_call(bus_read32((uint32_t)(24 + level) * 4));\n"
    assert m.count(old) == 1, "m68k.c: interrupt entry layout changed"
    m = m.replace(old, "    bus_add_cycles(44);  /* LANDSTALKER_TIMING: interrupt acknowledge + stacking */\n"
                       "    extern int lk_irq_ctx; int lk_prev_ctx = lk_irq_ctx; lk_irq_ctx = level;\n" + old +
                       "    lk_irq_ctx = lk_prev_ctx;\n", 1)
    if '#include "genrecomp/bus.h"' not in m:
        m = m.replace('#include "genrecomp/m68k.h"', '#include "genrecomp/m68k.h"\n#include "genrecomp/bus.h"', 1)
    open(p, "w").write(m)
    print("m68k.c patched: interrupt cost")

# ---------------------------------------------------------------- generate.py
p = os.path.join(root, "tools/recompiler/generate.py")
g = open(p).read()
if "LANDSTALKER_TIMING" in g:
    print("generate.py timing already patched")
    sys.exit(0)

# 1. helpers (module level, before the translator class)
anchor = "class M68KTranslator"
assert g.count(anchor) == 1, "generate.py: class layout changed"
helpers = r'''# ---- LANDSTALKER_TIMING: per-instruction 68000 cycle counts (see tools/patch_timing.py) ----
import os as _os, re as _re
_CYC_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', 'ext', 'Genesis-Plus-GX',
                          'core', 'm68k', 'm68ki_cycles.h')
_CYC = [int(x) for x in _re.findall(r'(\d+)\*7', open(_CYC_PATH).read())]
assert len(_CYC) == 0x10000, "m68ki_cycles.h layout changed"
_CC = ('t', 'f', 'hi', 'ls', 'cc', 'hs', 'cs', 'lo', 'ne', 'eq', 'vc', 'vs', 'pl', 'mi', 'ge', 'lt', 'gt', 'le')
_SHIFTS = ('asl', 'asr', 'lsl', 'lsr', 'rol', 'ror', 'roxl', 'roxr')
_IO_RE = _re.compile(r'\$(?:c0|c8|a0|a1)[0-9a-f]{4}', _re.I)   # VDP / Z80 / IO: keep the clock exact there
_FLOW_RE = _re.compile(r'return;|goto |func_table_|longjmp')


def _timing_extra(base, mnemonic, op_str, raw, tr):
    """-> (static cycles, dynamic pre-statement or None, transform for the code line or None)"""
    mn = mnemonic.split('.')[0]
    sz = mnemonic.split('.')[1] if '.' in mnemonic else 'w'
    ops = tr._split_operands(op_str) if op_str else []
    if mn == 'trap':
        return 34, None
    if mn == 'movem' and len(ops) == 2:
        rl = ops[0] if _re.match(r'^[da][0-7]', ops[0].strip().lower()) and '(' not in ops[0] else ops[1]
        try:
            n = len(tr._parse_reglist(rl))
        except Exception:
            n = 0
        return base + n * (8 if sz == 'l' else 4), None
    if mn in _SHIFTS and len(ops) == 2:
        c = ops[0].strip().lower()
        if c.startswith('#'):
            try:
                n = int(c[1:].replace('$', '0x'), 0)
            except ValueError:
                n = 1
            return base + 2 * (n or 8), None
        r = tr._reg(c)
        if r:
            return base, f'bus_add_cycles(2u * ({r} & 63u));'
    return base, None


def _timing_code(mnemonic, c, raw, tr):
    """Rewrite one generated statement with its dynamic cost; returns (code, own_cost_inside)"""
    mn = mnemonic.split('.')[0]
    # Bcc: table = taken (10); not taken 8 (.s) / 12 (.w)
    if mn.startswith('b') and mn[1:] in _CC[2:] :
        t = 10
        nt = 8 if len(raw) == 2 else 12
        m = _re.match(r'^(\s*)if \((.+?)\) (goto \w+;|\{ func_table_call\(.*\})$', c)
        if m:
            return (f'{m.group(1)}if ({m.group(2)}) {{ bus_add_cycles({t}); {m.group(3)} }} else {{ bus_add_cycles({nt}); }}', True)
        return c, False
    if mn.startswith('db') and (mn[2:] in _CC or mn == 'dbra'):
        c2 = _re.sub(r'if \(_cnt != -1\) (goto \w+;)', r'if (_cnt != -1) { bus_add_cycles(10); \1 } bus_add_cycles(14);', c)
        c2 = _re.sub(r'if \(_cnt != -1\) \{ (func_table_call\(0x[0-9A-F]+\); return;) \}',
                     r'if (_cnt != -1) { bus_add_cycles(10); \1 } bus_add_cycles(14);', c2)
        if c2 != c:
            if mn not in ('dbf', 'dbra'):
                c2 = c2 + ' else bus_add_cycles(12);'
            return c2, True
        return c, False
    if mn in ('mulu', 'muls', 'divu', 'divs'):
        m = _re.match(r'^(\s*)M68K_(MULU|MULS|DIVU|DIVS)\((g_m68k\.d\[\d\]), (.*)\);$', c)
        if m:
            ind, op, reg, src = m.groups()
            ty = 'int16_t' if op.endswith('S') else 'uint16_t'
            fn = f'bus_{op.lower()}_mclk(' + (f'{reg}, _ts)' if op.startswith('DIV') else '_ts)')
            return (f'{ind}{{ {ty} _ts = ({ty})({src}); bus_add_mclk({fn}); M68K_{op}({reg}, _ts); }}', False)
        return c, False
    if mn.startswith('s') and mn[1:] in _CC:
        m = _re.search(r'\| \((.+?) \? 0xFFu : 0x00u\);', c)
        if m:
            return c + f' if ({m.group(1)}) bus_add_cycles(2);', False
    return c, False


'''
g = g.replace(anchor, helpers + anchor, 1)

# 2. function generation loop
old = """        for addr in insn_addrs:
            if addr not in self.analyzer.instructions:
                continue
            mnemonic, op_str, size, raw = self.analyzer.instructions[addr]
            c_lines = self.translator.translate_instruction(addr, mnemonic, op_str, raw, reg_start, reg_end)
            lines.extend(c_lines)
"""
new = """        pending = 0   # LANDSTALKER_TIMING: 68000 cycles of the current straight-line run
        def _flush_cycles():
            nonlocal pending
            if pending:
                lines.append(f'    bus_add_cycles({pending});')
                pending = 0
        for addr in insn_addrs:
            if addr not in self.analyzer.instructions:
                continue
            mnemonic, op_str, size, raw = self.analyzer.instructions[addr]
            c_lines = self.translator.translate_instruction(addr, mnemonic, op_str, raw, reg_start, reg_end)
            # a branch target starts a new run: the cost of the previous run belongs before the label
            if c_lines and c_lines[0].endswith(':') and not c_lines[0].lstrip().startswith(('/*', '//')):
                _flush_cycles()
                lines.append(c_lines[0])
                c_lines = c_lines[1:]
            opcode = (raw[0] << 8) | raw[1]
            cyc, pre = _timing_extra(_CYC[opcode], mnemonic, op_str, raw, self.translator)
            body = []
            own_inside = False
            for cl in c_lines:
                cl2, inside = _timing_code(mnemonic, cl, raw, self.translator)
                own_inside = own_inside or inside
                body.append(cl2)
            text = '\\n'.join(body)
            flow = bool(_FLOW_RE.search(text))
            if flow or _IO_RE.search(op_str or ''):
                if not own_inside:
                    pending += cyc
                _flush_cycles()
                if pre:
                    lines.append(f'    {pre}')
            else:
                pending += cyc
                if pre:
                    _flush_cycles()
                    lines.append(f'    {pre}')
            lines.extend(body)
        _flush_cycles()
"""
assert old in g, "generate.py: _generate_function loop layout changed"
g = g.replace(old, new, 1)
open(p, "w").write(g)
print("generate.py patched: LANDSTALKER_TIMING")
