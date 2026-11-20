#!/usr/bin/env python3
# fit_bush.py LEFT RIGHT OUT.json (half widths per row, top..bottom, -1 = unknown; measured on plane A: room 475 front bush right side, room 601 left side) -- fit the pure-Python style C bush to a drawn bush: half widths per row (top..bottom, free side mirrored)
import sys, json, itertools
sys.path.insert(0, '' + __import__('os').path.dirname(__import__('os').path.abspath(__file__)) + ''); import bush
L = [float(v) for v in sys.argv[1].split(",")]; Rr = [float(v) for v in sys.argv[2].split(",")]; out = sys.argv[3]; hw = L
n = len(hw); FOOT = n - 2      # foot row = second last row (roots spread below)
T = set()
for k, w in enumerate(hw):
    if w < 0: continue
    if Rr[k] < 0: continue
    for dx in range(-int(round(w)), int(round(Rr[k])) + 1): T.add((dx + 24, k - FOOT + 56))
def sil(P, o):
    S = set()
    for part in bush.bush_parts(o, o, 0, P):
        for f in part:
            for k in range(1, len(f) - 1):
                tri = [(p[0] - p[1] + 24, (p[0] + p[1]) / 2 - p[2] + 56) for p in (f[0], f[k], f[k + 1])]
                xs = [t[0] for t in tri]; ys = [t[1] for t in tri]
                (x1, y1), (x2, y2), (x3, y3) = tri; d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
                if abs(d) < 1e-9: continue
                for py in range(int(min(ys)), int(max(ys)) + 1):
                    for px in range(int(min(xs)), int(max(xs)) + 1):
                        cx, cy = px + 0.5, py + 0.5
                        a = ((y2 - y3) * (cx - x3) + (x3 - x2) * (cy - y3)) / d; b = ((y3 - y1) * (cx - x3) + (x1 - x3) * (cy - y3)) / d
                        if a >= 0 and b >= 0 and a + b <= 1: S.add((px, py))
    return S
iou = lambda S: len(S & T) / len(S | T)
best = None
for r, sz, top, lump, lo, o in itertools.product([10, 11, 12], [0.8, 0.9, 1.0], [25, 26, 27], [4.4, 4.8, 5.4, 6.0], [5.8, 6.2, 7.0, 7.8], [-1, 0, 1]):
    P = dict(r=r, sz=sz, top=top, lump=lump, lo=lo, stem=1.0); s = iou(sil(P, o))
    if best is None or s > best[0]: best = (s, P, o)
s, P, o = best; S = sil(P, o)
print('best IoU %.3f' % s, P, 'offset', o, 'outside', len(S - T), 'missing', len(T - S))
json.dump(dict(P, offset=o, iou=round(s, 3)), open(out, 'w'), indent=1)
