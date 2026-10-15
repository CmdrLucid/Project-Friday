#!/usr/bin/env python3
"""shiftscan.py REFDIR RECDIR LO HI [first] [last] [maxshift]    (LO/HI = 68K addresses in hex)

Needs per-frame dumps (--ram-dump DIR:1, e.g. GENRECOMP_DUMPRANGE=300:700). For every frame k: number of differing bytes in LO..HI between ref[k] and
rec[k+s] for s in -maxshift..maxshift, and the best shift. A constant best shift with 0 differences = the runs are identical but offset by that many frames
(rec ahead if the best shift is positive). Ends with a histogram of the best shifts."""
import os, sys, collections
ref, rec = sys.argv[1], sys.argv[2]
lo, hi = int(sys.argv[3], 16) & 0xFFFF, (int(sys.argv[4], 16) & 0xFFFF) or 0x10000
first = int(sys.argv[5]) if len(sys.argv) > 5 else 0
last = int(sys.argv[6]) if len(sys.argv) > 6 else 10**9
ms = int(sys.argv[7]) if len(sys.argv) > 7 else 4
cache = {}
def load(d, k):
    key = (d, k)
    if key not in cache:
        p = os.path.join(d, 'ram_%06d.bin' % k)
        cache[key] = None
        if os.path.exists(p):
            b = open(p, 'rb').read(65536)
            cache[key] = bytes(b[i ^ 1] for i in range(lo, hi))
        if len(cache) > 64: cache.pop(next(iter(cache)))
    return cache[key]
hist = collections.Counter(); shown = 0
ks = sorted(int(f[4:10]) for f in os.listdir(ref) if f.startswith('ram_'))
print('frame ' + ' '.join('s%+d' % s for s in range(-ms, ms + 1)) + '  best')
for k in ks:
    if k < first or k > last: continue
    a = load(ref, k)
    row = []
    for s in range(-ms, ms + 1):
        b = load(rec, k + s)
        row.append(None if b is None else sum(1 for x, y in zip(a, b) if x != y))
    vals = [(v, abs(s), s) for v, s in zip(row, range(-ms, ms + 1)) if v is not None]
    if not vals: continue
    best = min(vals)
    hist[(best[2], best[0] == 0)] += 1
    if (k - first) % 10 == 0 or best[0] != 0 and shown < 40:
        print('%5d ' % k + ' '.join('%6s' % ('-' if v is None else v) for v in row) + '  %+d (%s)' % (best[2], 'exact' if best[0] == 0 else '%d bytes' % best[0]))
        shown += 1
print('best shifts (shift, exact?) -> frames:', sorted(hist.items()))
