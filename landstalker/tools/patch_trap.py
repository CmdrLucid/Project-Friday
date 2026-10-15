#!/usr/bin/env python3
"""Fix genrecomp's TRAP handling for games whose trap handlers read inline data
after the TRAP instruction (Landstalker: trap #0 sound IDs, trap #1/#2 text IDs).

 * generate.py: push the real return address (the stale g_m68k.pc was used)
 * analyze.py : `trap_data` in recomp.json = {"0": 1, ...} number of data words
                following `trap #N`; the analyzer skips them instead of decoding
                them as instructions.
usage: patch_trap.py path/to/genrecomp/tools/recompiler   (idempotent)
"""
import sys, os

d = sys.argv[1]

def patch(fn, old, new, marker):
    p = os.path.join(d, fn)
    s = open(p).read()
    if marker in s:
        print(fn, "already patched:", marker); return
    assert old in s, f"{fn}: layout changed ({old[:50]!r})"
    open(p, "w").write(s.replace(old, new, 1))
    print(fn, "patched:", marker)

patch("generate.py",
      "return f'recomp_m68k_exception(32 + {trap_num}); /* TRAP #{trap_num} */'",
      "return f'g_m68k.pc = 0x{self._ret:06X}; recomp_m68k_exception(32 + {trap_num}); /* TRAP #{trap_num} */'",
      "g_m68k.pc = 0x{self._ret:06X}; recomp_m68k_exception")

patch("analyze.py",
      "        self.EXPLICIT_SEEDS = {int(k, 16): v for k, v in cfg.get('seeds', {}).items()}\n",
      "        self.EXPLICIT_SEEDS = {int(k, 16): v for k, v in cfg.get('seeds', {}).items()}\n"
      "        # trap_data: {\"0\": 1} = `trap #0` is followed by 1 inline data word\n"
      "        self.trap_data = {int(k): int(v) for k, v in cfg.get('trap_data', {}).items()}\n",
      "self.trap_data = {int(k)")

patch("analyze.py",
      "            else:\n                addr += insn.size\n\n        return targets\n",
      "            elif base == 'trap':\n"
      "                m = re.search(r'#(\\$?)([0-9a-fA-F]+)', op_str)\n"
      "                n = int(m.group(2), 16 if m.group(1) else 10) if m else -1\n"
      "                _td = 2 * self.__dict__.get('trap_data', {}).get(n, 0)\n"
      "                if hasattr(self, '_call_data_bytes'): self._call_data_bytes.update(range(addr + insn.size, addr + insn.size + _td))  # inline data words are never code\n"
      "                addr += insn.size + _td\n"
      "                continue\n\n"
      "            else:\n                addr += insn.size\n\n        return targets\n",
      "elif base == 'trap':")
