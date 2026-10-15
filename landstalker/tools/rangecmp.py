#!/usr/bin/env python3
"""rangecmp.py REFDIR RECDIR LO HI [first] [last] [step]   (LO/HI = 68K addresses in hex, e.g. FF5480 FF5C80)

Compares one work-RAM range between genrecomp_ref and recompiled --ram-dump files frame by frame (same index) and prints the differing bytes
as 'addr ref->rec' for the first frames where the range differs. Use for sprite structs ($FF5480, 0x80 bytes each; player at $FF5400)."""
import os, sys
ref, rec = sys.argv[1], sys.argv[2]
lo, hi = int(sys.argv[3], 16) & 0xFFFF, (int(sys.argv[4], 16) & 0xFFFF) or 0x10000
first = int(sys.argv[5]) if len(sys.argv) > 5 else 0
last = int(sys.argv[6]) if len(sys.argv) > 6 else 10**9
step = int(sys.argv[7]) if len(sys.argv) > 7 else 1
files = sorted(f for f in os.listdir(ref) if f.startswith('ram_'))
shown = 0
for f in files:
    k = int(f[4:10])
    if k < first or k > last or (k - first) % step: continue
    g = os.path.join(rec, f)
    if not os.path.exists(g): continue
    a = open(os.path.join(ref, f), 'rb').read(65536); b = open(g, 'rb').read(65536)
    # dump byte order: byte at 68K address A is file index A^1
    d = [(i, a[i ^ 1], b[i ^ 1]) for i in range(lo, hi) if a[i ^ 1] != b[i ^ 1]]
    if d:
        print('frame %d: %d bytes differ: %s' % (k, len(d), ' '.join('%06X %02X->%02X' % (0xFF0000 + i, x, y) for i, x, y in d[:14])))
        shown += 1
        if shown >= 25: break
if not shown: print('range identical in all compared frames')
