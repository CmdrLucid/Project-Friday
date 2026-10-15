#!/usr/bin/env python3
"""entitydump.py REFDIR RECDIR ADDR FRAME [FRAME ...]     (ADDR = entity base in hex, e.g. FF5700)

Prints the 0x80 bytes of one entity at the given frames in ref and rec side by side, 16 bytes per row, differing bytes marked with '*'.
Used to find which entity fields (position +18/+1A/+1C/+1E, height +12, ground +22, flags ...) differ between the two builds."""
import os, sys
ref, rec = sys.argv[1], sys.argv[2]
base = int(sys.argv[3], 16) & 0xFFFF
def ent(d, k):
    b = open(os.path.join(d, 'ram_%06d.bin' % k), 'rb').read(65536)
    return bytes(b[(base + i) ^ 1] for i in range(0x80))
for k in map(int, sys.argv[4:]):
    try: a, b = ent(ref, k), ent(rec, k)
    except FileNotFoundError: print('frame %d: dump missing' % k); continue
    print('--- frame %d  entity $FF%04X ---' % (k, base))
    print('off   ref                                                rec')
    for r in range(0, 0x80, 16):
        ra, rb = a[r:r + 16], b[r:r + 16]
        mark = ''.join('*' if x != y else ' ' for x, y in zip(ra, rb))
        if ra != rb or r < 0x30:
            print('+%02X  %s   %s   %s' % (r, ra.hex(' '), rb.hex(' '), mark))
