#!/usr/bin/env python3
"""Fix genrecomp's recompiler: memory-destination read-modify-write instructions
(or/and/eor/add/sub/addq/subq/neg/not/shifts/bit ops/Scc ...) with a (An)+ or
-(An) destination never updated An. e.g. `or.w d0,(a1)+` left a1 unchanged.

usage: patch_generate.py path/to/genrecomp/tools/recompiler/generate.py  (idempotent)
"""
import sys

p = sys.argv[1]
s = open(p).read()
if "_apply_ea_adjust" in s:
    print("generate.py already patched")
    sys.exit(0)

# 1. record the addressing mode when an effective *address* is taken
old_post = """        m = re.match(r'^\\(a([0-7])\\)\\+$', op, re.I)
        if m:
            return f'g_m68k.a[{m.group(1)}]'

        # -(An) — for _ea_addr in RMW context, pre-decrement is caller's job
        m = re.match(r'^-\\(a([0-7])\\)$', op, re.I)
        if m:
            return f'g_m68k.a[{m.group(1)}]'
"""
new_post = """        m = re.match(r'^\\(a([0-7])\\)\\+$', op, re.I)
        if m:
            self.__dict__.setdefault('_ea_adjust', []).append(('post', int(m.group(1))))
            return f'g_m68k.a[{m.group(1)}]'

        # -(An) — pre-decrement is applied by translate_instruction (_apply_ea_adjust)
        m = re.match(r'^-\\(a([0-7])\\)$', op, re.I)
        if m:
            self.__dict__.setdefault('_ea_adjust', []).append(('pre', int(m.group(1))))
            return f'g_m68k.a[{m.group(1)}]'
"""
assert old_post in s, "_ea_addr layout changed"
s = s.replace(old_post, new_post, 1)

# 2. apply it around the translated statement
old_disp = """        # Dispatch to handler
        c_code = self._translate(addr, base_mnem, mnemonic, op_str, size, raw_bytes)
"""
new_disp = """        # Dispatch to handler
        self._ea_adjust = []
        c_code = self._translate(addr, base_mnem, mnemonic, op_str, size, raw_bytes)
        if c_code and self._ea_adjust:
            c_code = self._apply_ea_adjust(c_code, base_mnem, size)
"""
assert old_disp in s, "translate_instruction layout changed"
s = s.replace(old_disp, new_disp, 1)

method = '''    _BYTE_MEM_OPS = {'bset', 'bclr', 'bchg', 'btst', 'nbcd', 'tas',
                     'st', 'sf', 'shi', 'sls', 'scc', 'scs', 'sne', 'seq', 'svc', 'svs',
                     'spl', 'smi', 'sge', 'slt', 'sgt', 'sle', 'shs', 'slo'}

    def _apply_ea_adjust(self, c_code, base, size):
        """Apply (An)+ / -(An) side effects that _ea_addr users skip (RMW destinations)."""
        if base in self._BYTE_MEM_OPS:
            size = 8
        pre, post = [], []
        for kind, n in self._ea_adjust:
            step = 2 if (size == 8 and n == 7) else size // 8
            (pre if kind == 'pre' else post).append(f'g_m68k.a[{n}] {"-" if kind == "pre" else "+"}= {step};')
        self._ea_adjust = []
        return ' '.join(pre + [c_code] + post)

    def _translate(self, addr, base, mnemonic, op_str, size, raw_bytes):'''
old_t = "    def _translate(self, addr, base, mnemonic, op_str, size, raw_bytes):"
assert old_t in s
s = s.replace(old_t, method, 1)
open(p, "w").write(s)
print("patched generate.py")
