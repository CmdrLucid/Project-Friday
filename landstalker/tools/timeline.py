#!/usr/bin/env python3
"""timeline.py REFDIR RECDIR [first] [last] [every]

Per dump: room number (g_RmNum1 $FF1204, word) and Nigel's X/Y ($FF5400/$FF5401) for ref and rec, printed whenever the room changes or the position differs,
and at least every `every` dumps. Use it to find when the church is left (room change) before choosing a frame window for per-frame dumps."""
import os, sys
ref, rec = sys.argv[1], sys.argv[2]
first = int(sys.argv[3]) if len(sys.argv) > 3 else 0
last = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
every = int(sys.argv[5]) if len(sys.argv) > 5 else 40
def rd(b, a): return b[a ^ 1]
def word(b, a): return (rd(b, a) << 8) | rd(b, a + 1)
prev = None; n = 0
print('frame   room(ref/rec)   X,Y ref      X,Y rec')
for f in sorted(x for x in os.listdir(ref) if x.startswith('ram_')):
    k = int(f[4:10])
    if k < first or k > last: continue
    g = os.path.join(rec, f)
    if not os.path.exists(g): continue
    a = open(os.path.join(ref, f), 'rb').read(65536); b = open(g, 'rb').read(65536)
    cur = (word(a, 0x1204), word(b, 0x1204), rd(a, 0x5400), rd(a, 0x5401), rd(b, 0x5400), rd(b, 0x5401))
    n += 1
    if prev is None or cur[0] != prev[0] or cur[1] != prev[1] or n % every == 0:
        print('%5d   %04X / %04X     %02X,%02X       %02X,%02X%s' % (k, cur[0], cur[1], cur[2], cur[3], cur[4], cur[5], '   <-- room change' if prev and (cur[0] != prev[0] or cur[1] != prev[1]) else ''))
    prev = cur
