#!/usr/bin/env python3
"""who_touches.py ADDR [ADDR..] [-d src/recomp]

Which recompiled functions read or write a RAM / IO address? Scans the generated C (src/recomp, built from the user's ROM, never committed) for
`0xFF1128`-style constants and prints, per address, the functions that contain them (name, range, number of hits and the first matching line, whose read/write
kind is derived from the surrounding call: bus_read* = R, bus_write* = W, other = ?).  A cheap cross-reference for 'who produces / consumes this variable'.
Prints function names, addresses and generated-C snippets only (no ROM bytes)."""
import re, sys, glob, os, collections
args = [a for a in sys.argv[1:] if not a.startswith('-')]
d = 'src/recomp'
if '-d' in sys.argv: d = sys.argv[sys.argv.index('-d') + 1]; args = [a for a in args if a != d]
addrs = [int(a, 16) & 0xFFFFFF for a in args]
hdr = re.compile(r'^/\* \$([0-9A-F]{6})-\$([0-9A-F]{6})\s+\((\d+) instructions')
fnre = re.compile(r'^void (\w+)\(void\)')
res = {a: collections.OrderedDict() for a in addrs}
pats = {a: re.compile(r'0x(?:00)?%06X\b|0x%06x\b' % (a, a), re.I) for a in addrs}
for f in sorted(glob.glob(os.path.join(d, 'recomp_*.c'))):
    cur = None; start = None
    for line in open(f, errors='replace'):
        m = hdr.match(line)
        if m: start = int(m.group(1), 16); cur = None; continue
        m = fnre.match(line)
        if m: cur = (m.group(1), start); continue
        if cur is None: continue
        for a in addrs:
            if pats[a].search(line):
                kind = 'W' if re.search(r'bus_write\w*\(\s*0x', line) else 'R' if re.search(r'bus_read\w*\(\s*0x', line) else '?'
                e = res[a].setdefault(cur, {'R': 0, 'W': 0, '?': 0, 'ex': line.strip()[:110]}); e[kind] += 1
for a in addrs:
    print('=== $%06X: %d function(s)' % (a, len(res[a])))
    for (name, st), e in sorted(res[a].items(), key=lambda kv: -(kv[1]['R'] + kv[1]['W'] + kv[1]['?'])):
        print('  %-14s $%06X  R%d W%d ?%d   %s' % (name, st, e['R'], e['W'], e['?'], e['ex']))
