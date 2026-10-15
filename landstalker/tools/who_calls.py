#!/usr/bin/env python3
"""who_calls.py ADDR [ADDR..] [-d src/recomp]

Which recompiled functions CALL (jsr/bsr), JUMP to (bra/jmp tail call) or branch out to a given code address? Scans the generated C (src/recomp, built from the
user's ROM, never committed) for func_table_jsr / func_table_call / func_table_tail with that constant. Output per address: caller function, kind and the return
address for calls. Companion of who_touches.py (data addresses). Names and addresses only."""
import re, sys, glob, os, collections
import genc   # generated calls may use named constants (tools/rename_generated.py)
args = [a for a in sys.argv[1:] if not a.startswith('-')]
d = 'src/recomp'
if '-d' in sys.argv: d = sys.argv[sys.argv.index('-d') + 1]; args = [a for a in args if a != d]
addrs = [int(a, 16) & 0xFFFFFF for a in args]
hdr = re.compile(r'^/\* \$([0-9A-F]{6})-\$([0-9A-F]{6})\s+\((\d+) instructions')
fnre = re.compile(r'^void (\w+)\(void\)')
pats = {a: re.compile(r'func_table_(jsr|call|tail)\(\s*0x%06X\b(?:\s*,\s*0x([0-9A-F]{6}))?' % a, re.I) for a in addrs}
res = {a: [] for a in addrs}
ex = genc.expand(d)
for f in sorted(glob.glob(os.path.join(d, 'recomp_*.c'))):
    cur = None; start = None
    for line in open(f, errors='replace'):
        line = ex(line)
        m = hdr.match(line)
        if m: start = int(m.group(1), 16); cur = None; continue
        m = fnre.match(line)
        if m: cur = (m.group(1), start); continue
        if cur is None: continue
        for a in addrs:
            for mm in pats[a].finditer(line):
                res[a].append((cur, mm.group(1), mm.group(2)))
for a in addrs:
    print('=== $%06X is called/jumped to by %d site(s)' % (a, len(res[a])))
    for (name, st), kind, ret in res[a]:
        print('  %-14s $%06X  %s%s' % (name, st, kind, ('  (returns to $%s)' % ret) if ret else ''))
