#!/usr/bin/env python3
"""entitytrack.py REFDIR RECDIR ADDR [first] [last] [maxrows]     (ADDR = entity base in hex, e.g. FF5700)

Per-frame dumps required. Prints, for every frame in which the entity's position changes in ref or rec, its screen position fields (+0x0F x, +0x11 y) and the raw
first bytes (+0x00..+0x07) in ref and rec side by side. Shows whether the two builds walk the same path (maybe shifted by a frame) or different ones."""
import os, sys
ref, rec = sys.argv[1], sys.argv[2]
base = int(sys.argv[3], 16) & 0xFFFF
first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
last = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
maxrows = int(sys.argv[6]) if len(sys.argv) > 6 else 60
def get(b):
    return (b[(base + 0x0F) ^ 1], b[(base + 0x11) ^ 1], bytes(b[(base + i) ^ 1] for i in range(8)).hex())
prev = (None, None); rows = 0
print('frame  ref x,y   raw(+0..+7)        rec x,y   raw(+0..+7)')
for f in sorted(x for x in os.listdir(ref) if x.startswith('ram_')):
    k = int(f[4:10])
    if k < first or k > last: continue
    g = os.path.join(rec, f)
    if not os.path.exists(g): continue
    a = get(open(os.path.join(ref, f), 'rb').read(65536)); b = get(open(g, 'rb').read(65536))
    cur = (a[:2], b[:2])
    if cur != prev:
        print('%5d  %02X,%02X  %s   %02X,%02X  %s%s' % (k, a[0], a[1], a[2], b[0], b[1], b[2], '' if a[:2] == b[:2] else '   <-- differs'))
        rows += 1
        if rows >= maxrows: break
    prev = cur
