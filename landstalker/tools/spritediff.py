#!/usr/bin/env python3
"""spritediff.py REFDIR RECDIR [first] [last] [slots]

Per sprite slot ($FF5400 player, then $FF5480 + n*$80): in how many dumped frames does the slot differ between ref and rec, and in which frame did it differ first?
Sorted by first difference. Shows which entities diverge first and when (dumps need not be per-frame; use --ram-dump DIR:5 for a long replay).
For the first differing frame the bytes of the slot are listed (ref -> rec) so the moving fields (position, direction) can be read off."""
import os, sys, collections
ref, rec = sys.argv[1], sys.argv[2]
first = int(sys.argv[3]) if len(sys.argv) > 3 else 0
last = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
slots = int(sys.argv[5]) if len(sys.argv) > 5 else 24
base = 0x5400
def slot_range(n):  # n = 0 player, 1.. sprites
    return (0x5400, 0x5480) if n == 0 else (0x5480 + (n - 1) * 0x80, 0x5480 + n * 0x80)
files = sorted(f for f in os.listdir(ref) if f.startswith('ram_'))
first_diff = {}; count = collections.Counter(); detail = {}; total = 0
for f in files:
    k = int(f[4:10])
    if k < first or k > last: continue
    g = os.path.join(rec, f)
    if not os.path.exists(g): continue
    a = open(os.path.join(ref, f), 'rb').read(65536); b = open(g, 'rb').read(65536)
    total += 1
    for n in range(slots + 1):
        lo, hi = slot_range(n)
        d = [(i, a[i ^ 1], b[i ^ 1]) for i in range(lo, hi) if a[i ^ 1] != b[i ^ 1]]
        if d:
            count[n] += 1
            if n not in first_diff:
                first_diff[n] = k
                detail[n] = d
print('%d dumped frames compared' % total)
print('slot  address   frames_differing  first_diff_frame  bytes_at_first_diff (offset in slot: ref->rec)')
for n in sorted(first_diff, key=lambda x: first_diff[x]):
    lo, _ = slot_range(n)
    print('%4d  $FF%04X  %6d/%d        %6d            %s' % (n, lo, count[n], total, first_diff[n],
          ' '.join('+%02X:%02X->%02X' % (i - lo, x, y) for i, x, y in detail[n][:10]) + (' ...' if len(detail[n]) > 10 else '')))
if not first_diff: print('all slots identical in all compared frames')
