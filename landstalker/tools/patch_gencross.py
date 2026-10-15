#!/usr/bin/env python3
"""genrecomp generate.py: stop silently dropping unresolved call targets.

generate_all() splits functions at every address that generated code calls, but
_build_functions() ignores entries the analyzer never decoded as instructions, so
after the 10-pass limit some call targets (116 in Landstalker, e.g. $002458) never
become functions -> "func_table: no function at $XXXXXX" at run time.

 * decode such a target on the spot (analyzer._disassemble_block) before rebuilding
 * after the loop, list every target that is still not a function and why

Idempotent.  usage: patch_gencross.py path/to/genrecomp/tools/recompiler
"""
import sys, os

p = os.path.join(sys.argv[1], "generate.py")
s = open(p).read()
if "LANDSTALKER_GENCROSS" in s:
    print("generate.py already patched: LANDSTALKER_GENCROSS"); sys.exit(0)

old1 = "            for addr in unregistered:\n                if addr not in self.analyzer.labels:\n                    self.analyzer.labels[addr] = f'loc_{addr:06X}'\n"
new1 = ("            for addr in unregistered:\n"
        "                if addr not in self.analyzer.labels:\n"
        "                    self.analyzer.labels[addr] = f'loc_{addr:06X}'\n"
        "                # LANDSTALKER_GENCROSS: decode call targets the analyzer never reached\n"
        "                if addr not in self.analyzer.instructions and addr not in self.analyzer.visited:\n"
        "                    self.analyzer._disassemble_block(addr)\n")
assert old1 in s, "generate_all loop layout changed"
s = s.replace(old1, new1, 1)

old2 = "        # Generate registration header\n        self._generate_registration(functions)\n"
new2 = ("        # LANDSTALKER_GENCROSS: report call targets that still are not functions\n"
        "        left = sorted(a for a in (self.cross_func_targets - set(f['start'] for f in functions))\n"
        "                      if 0x200 <= a < self.rom.size)\n"
        "        if left:\n"
        "            print(f'  WARNING: {len(left)} call targets are not functions (they will fail at run time):')\n"
        "            ins = self.analyzer.instructions\n"
        "            starts = sorted(ins)\n"
        "            import bisect\n"
        "            for a in left[:60]:\n"
        "                if a & 1:\n"
        "                    why = 'odd address'\n"
        "                elif a in ins:\n"
        "                    why = 'decoded but not split'\n"
        "                else:\n"
        "                    i = bisect.bisect_right(starts, a) - 1\n"
        "                    why = (f'inside instruction at ${starts[i]:06X}' if i >= 0 and starts[i] + ins[starts[i]][2] > a\n"
        "                           else 'not decoded as code')\n"
        "                print(f'    ${a:06X}  {why}')\n"
        "        # Generate registration header\n        self._generate_registration(functions)\n")
assert old2 in s, "registration layout changed"
s = s.replace(old2, new2, 1)
open(p, "w").write(s)
print("generate.py patched: LANDSTALKER_GENCROSS")
