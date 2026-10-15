#!/usr/bin/env python3
"""Fix genrecomp's recompiler: 68000 absolute SHORT addresses ($XXXX.w) are sign-extended to 32 bits ($8000..$FFFF -> $FFFF8000..$FFFFFFFF = the top 32 KB of work RAM
and the I/O area), but the generator used the 16-bit value as a plain unsigned address, so e.g. `move.w ($D192).w,d0` read ROM $00D192 instead of RAM $FFD192.
Found by the differential instruction fuzz (tools/insnfuzz): `lea.l $8de0.w,a3` gave $00008DE0 instead of $FFFF8DE0. Idempotent.
usage: patch_absw.py path/to/genrecomp/tools/recompiler/generate.py"""
import sys
p = sys.argv[1]
s = open(p).read()
if "_abs_val" in s:
    print("generate.py already patched: _abs_val"); sys.exit(0)
helper = '''def _abs_val(m):
    """68000 absolute short addresses are sign-extended to 32 bits (LANDSTALKER_ABSW)"""
    v = int(m.group(1), 16)
    if (m.group(2) or '').lower() == 'w' and (v & 0x8000) and v <= 0xFFFF:
        v |= 0xFFFF0000
    return v


'''
anchor = "class M68KTranslator"
assert s.count(anchor) == 1, "generate.py layout changed"
s = s.replace(anchor, helper + anchor, 1)
old_a = "            addr_val = int(m.group(1), 16)\n"
assert s.count(old_a) == 4, "expected 4 absolute read/write sites, found %d" % s.count(old_a)
s = s.replace(old_a, "            addr_val = _abs_val(m)\n")
old_b = "            return f'0x{int(m.group(1), 16):06X}'\n"
assert s.count(old_b) == 2, "expected 2 absolute address sites, found %d" % s.count(old_b)
s = s.replace(old_b, "            return f'0x{_abs_val(m):06X}'\n")
open(p, "w").write(s)
print("generate.py patched: LANDSTALKER_ABSW (absolute short addresses sign-extended)")
