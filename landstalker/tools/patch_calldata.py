#!/usr/bin/env python3
"""genrecomp: calls whose callee reads inline data after the call (idempotent). Apply after patch_trap.py.

Landstalker's script code does `bsr.w ScriptSleep / dc.w 119 / ...`: the callee reads parameters at the
return address and returns past them (`addq.l #n,N(sp)`), or never returns here at all (pops the return
address: `addq.l #4,sp / rts`). The analyzer decoded the data as instructions and the generated C executed
them (a `ori.w ...(a7,...)` garbage instruction trashed the stack: the "Found <item>" crash).

recomp.json:  "call_data": { "<callee address>": SPEC, ... }   SPEC =
    {"skip": N}        N data bytes follow the call, the callee returns after them
    {"pick": true}     PickValueBasedOnFlags list: (flag,value) word pairs + negative terminator word
    {"terminal": true} the callee never returns to the call site; end the block (data length irrelevant)
  An entry may use {"site": "0x024B0E", ...} instead of a key address: the callee is the target of the
  `bsr.w` at that ROM address. {"op": "48E7", "mask": "8080"} (optional) = first words expected at the callee,
  checked at run time of the generator (mismatch: warning, entry ignored).
Also patches func_table.c: a return address 1..256 bytes past the expected one is accepted silently.
usage: patch_calldata.py path/to/genrecomp/tools/recompiler
"""
import sys, os

d = sys.argv[1]
rt = os.path.join(d, "..", "..", "src", "func_table.c")

def patch(path, old, new, marker):
    s = open(path).read()
    if marker in s:
        print(os.path.basename(path), "already patched:", marker); return
    assert old in s, f"{path}: layout changed ({old[:60]!r})"
    open(path, "w").write(s.replace(old, new, 1))
    print(os.path.basename(path), "patched:", marker)

A = os.path.join(d, "analyze.py")
patch(A,
      "        self.trap_data = {int(k): int(v) for k, v in cfg.get('trap_data', {}).items()}\n",
      "        self.trap_data = {int(k): int(v) for k, v in cfg.get('trap_data', {}).items()}\n"
      "        self._call_data_cfg = cfg.get('call_data', {})  # LANDSTALKER_CALLDATA\n"
      "        self._call_data = None\n"
      "        self._call_data_bytes = set()  # inline data bytes after call_data calls (never code)\n",
      "LANDSTALKER_CALLDATA")

helper = '''
    def _call_skip(self, target, ret):
        """LANDSTALKER_CALLDATA: (data bytes after a call to target, callee-never-returns)"""
        if self._call_data is None:
            self._call_data = {}
            rd = self.rom.data
            for key, spec in self._call_data_cfg.items():
                addr = None
                if 'site' in spec:
                    s = int(spec['site'], 16)
                    if rd[s] == 0x61 and rd[s + 1] == 0x00:
                        disp = (rd[s + 2] << 8) | rd[s + 3]
                        if disp & 0x8000: disp -= 0x10000
                        addr = s + 2 + disp
                    else:
                        print(f"  WARNING call_data: no bsr.w at {spec['site']}"); continue
                else:
                    addr = int(key, 16)
                if 'op' in spec:
                    want = bytes.fromhex(spec['op'] + spec.get('mask', ''))
                    if bytes(rd[addr:addr + len(want)]) != want:
                        print(f"  WARNING call_data: ${addr:06X} does not start with {want.hex()}: ignored"); continue
                self._call_data[addr] = spec
        spec = self._call_data.get(target)
        if not spec:
            return 0, False
        if spec.get('terminal'):
            return 0, True
        if spec.get('pick'):
            rd = self.rom.data; i = ret
            while i + 1 < len(rd):
                w = (rd[i] << 8) | rd[i + 1]
                if w & 0x8000: i += 2; break
                i += 4
            return i - ret, False
        return int(spec.get('skip', 0)), False
'''
patch(A,
      "    def _disassemble_block(self, start_addr):\n",
      helper + "\n    def _disassemble_block(self, start_addr):\n",
      "def _call_skip")

patch(A,
      "                    if target not in self.labels:\n                        self.labels[target] = f\"sub_{target:06X}\"\n                addr += insn.size\n                continue\n",
      "                    if target not in self.labels:\n                        self.labels[target] = f\"sub_{target:06X}\"\n"
      "                    skip, terminal = self._call_skip(target, addr + insn.size)  # LANDSTALKER_CALLDATA\n"
      "                    if terminal:\n"
      "                        break\n"
      "                    self._call_data_bytes.update(range(addr + insn.size, addr + insn.size + skip))\n"
      "                    addr += insn.size + skip\n"
      "                    continue\n"
      "                addr += insn.size\n                continue\n",
      "skip, terminal = self._call_skip")

# Heuristic scans (address tables, lea, prologues) must not start code inside such inline data: a
# 3-longword "table" pointing at $027362/$027366 made the analyzer decode the data words after
# `bsr XS_00B3_0 ($025DEA)` as bset instructions and the seeded function $027358 ran them
# (bset -(a7) wrecked the stack: freeze in a cutscene dialogue, 2026-10-11).
patch(A,
      "    def _plausible(self, t):\n"
      "        if not (0x200 <= t < self.rom.size) or (t & 1):\n"
      "            return False\n",
      "    def _plausible(self, t):\n"
      "        if not (0x200 <= t < self.rom.size) or (t & 1):\n"
      "            return False\n"
      "        if t in self._call_data_bytes:  # LANDSTALKER_CALLDATA_PLAUSIBLE\n"
      "            return False\n",
      "LANDSTALKER_CALLDATA_PLAUSIBLE")

patch(rt,
      "        if (func_table_lookup(r)) s_tail = r;\n        else {\n",
      "        if (func_table_lookup(r)) s_tail = r;\n"
      "        else if (r > e && r - e <= 256) { /* LANDSTALKER_CALLDATA: callee skipped inline data after the call */ }\n"
      "        else {\n",
      "LANDSTALKER_CALLDATA")
