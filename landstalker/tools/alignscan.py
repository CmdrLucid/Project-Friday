#!/usr/bin/env python3
"""alignscan.py REFDIR RECDIR [first_frame] [last_frame] [maxshift]

Per-frame dumps (--ram-dump DIR:1) of genrecomp_ref and the recompiled build: for every frame k print how many work-RAM bytes differ between ref[k] and
rec[k+shift] for shift -maxshift..maxshift (default 2) and mark the best shift. Shows whether the two runs are merely offset by whole frames
(then the best shift is stable and its diff small) or really diverge (diff grows for every shift)."""
import os, sys
ref, rec = sys.argv[1], sys.argv[2]
lo = int(sys.argv[3]) if len(sys.argv) > 3 else 0
hi = int(sys.argv[4]) if len(sys.argv) > 4 else 60
ms = int(sys.argv[5]) if len(sys.argv) > 5 else 2
def load(d, k):
    p = os.path.join(d, 'ram_%06d.bin' % k)
    return open(p, 'rb').read(65536) if os.path.exists(p) else None
print('frame ' + ' '.join('shift%+d' % s for s in range(-ms, ms + 1)) + '   best')
for k in range(lo, hi + 1):
    a = load(ref, k)
    if a is None: break
    row = []
    for s in range(-ms, ms + 1):
        b = load(rec, k + s)
        row.append(None if b is None else sum(1 for x, y in zip(a, b) if x != y))
    vals = [(v, s) for v, s in zip(row, range(-ms, ms + 1)) if v is not None]
    best = min(vals)[1] if vals else None
    print('%5d ' % k + ' '.join('%8s' % ('-' if v is None else v) for v in row) + '   %+d' % best if best is not None else '')
