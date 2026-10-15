#!/usr/bin/env python3
"""Instruction-level fixes found by the differential instruction fuzz (tools/insnfuzz, Musashi vs recompiled C). Idempotent.
 1. CMPM / ABCD / SBCD (memory form) / NBCD: the generator's temporaries `_s` `_d` `_t` have the same names as the macros' own locals, so `M68K_CMP8(_d, _s)` became
    `uint8_t _s = (uint8_t)(_s)` (self-initialisation = garbage). Renamed.
 2. ASL was translated as LSL (V flag never set). Real ASL macros: V = the sign bit changed at some point during the shift.
 3. ROXL / ROXR: when the count is a non-zero multiple of the width+1 the result is unchanged but C must be X (C was left stale).
 4. capstone decodes `roxr.b Dx,Dy` (opcode $E030 pattern) as `roxr.l #n,Dy`; decode those two bytes ourselves.
 6. M68K_DIVS: INT_MIN / -1 raised SIGFPE on the host (68000: overflow flag, no fault) -> the whole process crashed.
 5. MOVEM with any other effective address (absolute, indexed, pc-relative, d(An) store...) was emitted as a TODO comment (= instruction silently skipped).
usage: patch_insnfix.py path/to/genrecomp"""
import os, sys, re
root = sys.argv[1]
gp = os.path.join(root, "tools/recompiler/generate.py")
hp = os.path.join(root, "include/genrecomp/m68k.h")
g = open(gp).read()
h = open(hp).read()
done = []

if "LANDSTALKER_INSNFIX" not in g:
    # 1. temporaries
    old = "f'uint{size}_t _d = bus_read{size}(g_m68k.a[{x}]); g_m68k.a[{x}] += {n}; '\n                f'M68K_CMP{size}(_d, _s); }}')"
    assert old in g, "cmpm layout changed"
    g = g.replace(old, "f'uint{size}_t _cd = bus_read{size}(g_m68k.a[{x}]); g_m68k.a[{x}] += {n}; '\n                f'M68K_CMP{size}(_cd, _cs); }}')")
    old = "return (f'{{ uint{size}_t _s = bus_read{size}(g_m68k.a[{y}]); g_m68k.a[{y}] += {n}; '"
    assert old in g, "cmpm src layout changed"
    g = g.replace(old, "return (f'{{ uint{size}_t _cs = bus_read{size}(g_m68k.a[{y}]); g_m68k.a[{y}] += {n}; '")
    old = ("return (f'{{ g_m68k.a[{y}] -= 1; uint8_t _s = bus_read8(g_m68k.a[{y}]); '\n"
           "                f'g_m68k.a[{x}] -= 1; uint8_t _t = bus_read8(g_m68k.a[{x}]); '\n"
           "                f'M68K_{op}(_t, _s); bus_write8(g_m68k.a[{x}], _t); }}')")
    assert old in g, "bcd layout changed"
    g = g.replace(old, ("return (f'{{ g_m68k.a[{y}] -= 1; uint8_t _bs = bus_read8(g_m68k.a[{y}]); '\n"
                        "                f'g_m68k.a[{x}] -= 1; uint8_t _bt = bus_read8(g_m68k.a[{x}]); '\n"
                        "                f'M68K_{op}(_bt, _bs); bus_write8(g_m68k.a[{x}], _bt); }}')"))
    old = "return f'{{ uint32_t _ea = {ea_addr}; uint8_t _t = bus_read8(_ea); M68K_NBCD(_t); bus_write8(_ea, _t); }}'"
    assert old in g, "nbcd layout changed"
    g = g.replace(old, "return f'{{ uint32_t _ea = {ea_addr}; uint8_t _bt = bus_read8(_ea); M68K_NBCD(_bt); bus_write8(_ea, _bt); }}'")
    # 2. ASL
    old = "return self._gen_shift('LSL', ops, size)  # ASL == LSL"
    assert old in g
    g = g.replace(old, "return self._gen_shift('ASL', ops, size)")
    # 4. capstone decode fix
    old = "        self.func_start = func_start\n        self.func_end = func_end\n        lines = []\n"
    assert g.count(old) == 1, "translate_instruction layout changed"
    g = g.replace(old, old + ("        if len(raw_bytes) == 2:   # LANDSTALKER_INSNFIX: capstone reads ROXR.B Dx,Dy ($E030 pattern) as ROXR.L #n,Dy\n"
                              "            _op = (raw_bytes[0] << 8) | raw_bytes[1]\n"
                              "            if (_op & 0xF1F8) == 0xE030:\n"
                              "                mnemonic = 'roxr.b'; op_str = 'd%d, d%d' % ((_op >> 9) & 7, _op & 7)\n"), 1)
    # 5. MOVEM generic effective addresses
    old_s = "            return f'/* TODO: movem store to {ea} */'\n"
    old_l = "            return f'/* TODO: movem load from {ea} */'\n"
    assert g.count(old_s) == 1 and g.count(old_l) == 1, "movem TODO layout changed"
    gen_s = ("            base = self._ea_addr(ea)   # LANDSTALKER_INSNFIX: any other control addressing mode\n"
             "            if 'UNHANDLED' in base:\n                return f'/* TODO: movem store to {ea} */'\n"
             "            stmts = [f'{{ uint32_t _addr = {base};']\n"
             "            for r in reglist:\n"
             "                stmts.append(f'{write_fn}(_addr, {self._reg(r)}); _addr += {byte_size};')\n"
             "            stmts.append('}')\n            return ' '.join(stmts)\n")
    gen_l = ("            base = self._ea_addr(ea)   # LANDSTALKER_INSNFIX: any other control addressing mode\n"
             "            if 'UNHANDLED' in base:\n                return f'/* TODO: movem load from {ea} */'\n"
             "            stmts = [f'{{ uint32_t _addr = {base};']\n"
             "            for r in reglist:\n"
             "                reg_c = self._reg(r)\n"
             "                if size == 16:\n"
             "                    stmts.append(f'{reg_c} = (uint32_t)(int32_t)(int16_t){read_fn}(_addr); _addr += {byte_size};')\n"
             "                else:\n"
             "                    stmts.append(f'{reg_c} = {read_fn}(_addr); _addr += {byte_size};')\n"
             "            stmts.append('}')\n            return ' '.join(stmts)\n")
    g = g.replace(old_s, gen_s).replace(old_l, gen_l)
    g = g.replace("class M68KTranslator", "# LANDSTALKER_INSNFIX applied (cmpm/bcd temporaries, ASL, capstone roxr.b, movem addressing modes)\nclass M68KTranslator", 1)
    open(gp, "w").write(g)
    done.append("generate.py")

if "LANDSTALKER_DIVS" not in h:
    old = "    int32_t _q = _d / (int32_t)_s; \\\n    int32_t _rem = _d % (int32_t)_s; \\\n"
    assert h.count(old) == 1, "M68K_DIVS layout changed"
    new = "    /* LANDSTALKER_DIVS: INT_MIN / -1 traps on the host CPU (SIGFPE); on the 68000 it is just an overflow */ \\\n    if (_s == -1 && _d == INT32_MIN) { g_m68k.flag_V = true; g_m68k.flag_C = false; break; } \\\n    int32_t _q = (_s == -1) ? -_d : _d / (int32_t)_s; \\\n    int32_t _rem = (_s == -1) ? 0 : _d % (int32_t)_s; \\\n"
    h = h.replace(old, new)
    open(hp, "w").write(h)
    done.append("m68k.h(divs)")
    h = open(hp).read()

if "M68K_ASL8" not in h:
    # 3. ROX carry
    n = h.count("if (!((count) & 63)) g_m68k.flag_C = g_m68k.flag_X;")
    assert n == 6, "expected 6 ROX carry lines, found %d" % n
    h = h.replace("if (!((count) & 63)) g_m68k.flag_C = g_m68k.flag_X;", "if (_cnt == 0) g_m68k.flag_C = g_m68k.flag_X;")
    # 2. ASL macros
    asl = ""
    for w, t, msb in ((8, "uint8_t", "0x80u"), (16, "uint16_t", "0x8000u"), (32, "uint32_t", "0x80000000u")):
        keep = {8: "((dst) & ~0xFFu) | (uint8_t)(_d)", 16: "((dst) & ~0xFFFFu) | (uint16_t)(_d)", 32: "_d"}[w]
        asl += f'''#define M68K_ASL{w}(dst, count) do {{ \\
    uint8_t _cnt = (uint8_t)((count) & 63); \\
    {t} _d = ({t})(dst); \\
    bool _v = false, _c = false; \\
    for (uint8_t _i = 0; _i < _cnt; _i++) {{ \\
        _c = (_d & {msb}) != 0; \\
        {t} _n = ({t})(_d << 1); \\
        if ((_n ^ _d) & {msb}) _v = true; \\
        _d = _n; \\
    }} \\
    if (_cnt == 0) {{ g_m68k.flag_C = false; }} else {{ g_m68k.flag_C = g_m68k.flag_X = _c; }} \\
    g_m68k.flag_V = _v; \\
    m68k_update_nz{w}(_d); \\
    (dst) = {keep}; \\
}} while(0)

'''
    marker = "/* --- SWAP (swap halves of data register) --- */"
    assert marker in h
    h = h.replace(marker, "/* --- ASL (Arithmetic Shift Left): like LSL but V = sign bit changed during the shift (LANDSTALKER_INSNFIX) --- */\n" + asl + marker, 1)
    open(hp, "w").write(h)
    done.append("m68k.h")

# signed-shift UB found with UBSan (2026-10-15): `(uint16_t)_rem << 16` promotes to int and overflows for remainders >= 0x8000;
# the result is the same on every real compiler today, but it is undefined behaviour (clang could optimise on it)
h = open(hp).read()
old = "uint32_t _res = ((uint16_t)_rem << 16) | ((uint16_t)_q & 0xFFFF); \\\n"
if old in h:
    h = h.replace(old, "uint32_t _res = ((uint32_t)(uint16_t)_rem << 16) | ((uint16_t)_q & 0xFFFF); /* LANDSTALKER_SHIFT */ \\\n")
    open(hp, "w").write(h)
    done.append("m68k.h(divs shift)")
print("patch_insnfix:", ", ".join(done) if done else "already applied")
