#!/usr/bin/env python3
"""entitywatch.py DIR ADDR [first] [last] [max_changes_per_offset] [size]     (ADDR = entity base in hex, size default 0x80)

Per-frame dumps of ONE run (ref or rec). Lists the rarely changing fields of an entity struct: for every byte offset that changes at most `max_changes_per_offset`
times (default 12) in the window, every change as 'frame: +off old->new'. Fields that change nearly every frame (positions, animation counters) are skipped,
so state transitions (direction, timers, targets, flags) stand out. Run it on ref and on rec and compare."""
import os, sys, collections
d = sys.argv[1]
base = int(sys.argv[2], 16) & 0xFFFF
first = int(sys.argv[3]) if len(sys.argv) > 3 else 0
last = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
mx = int(sys.argv[5]) if len(sys.argv) > 5 else 12
size = int(sys.argv[6], 0) if len(sys.argv) > 6 else 0x80
prev = None; changes = collections.defaultdict(list); frames = 0
for f in sorted(x for x in os.listdir(d) if x.startswith('ram_')):
    k = int(f[4:10])
    if k < first or k > last: continue
    b = open(os.path.join(d, f), 'rb').read(65536)
    cur = bytes(b[(base + i) ^ 1] for i in range(size))
    frames += 1
    if prev is not None:
        for i in range(size):
            if cur[i] != prev[i]: changes[i].append((k, prev[i], cur[i]))
    prev = cur
print('%d frames; offsets with 1..%d changes:' % (frames, mx))
ev = []
for i, lst in changes.items():
    if len(lst) <= mx:
        for k, o, n in lst: ev.append((k, i, o, n))
for k, i, o, n in sorted(ev):
    print('%5d: +%02X %02X->%02X' % (k, i, o, n))
busy = sorted(((len(l), i) for i, l in changes.items() if len(l) > mx), reverse=True)
print('busy offsets (changes every few frames, skipped):', ' '.join('+%02X(%d)' % (i, n) for n, i in busy[:14]))
