#!/usr/bin/env python3
# fit_small.py ROM OUT.json -- fit the style C pine (pine_court/pine.py) to the SMALL pine sprite (room 475 front pine, plane A, right side mirrored)
import sys, json, itertools, types
HERE = __import__('os').path.dirname(__import__('os').path.abspath(__file__)); sys.path.insert(0, HERE + '/../pine_court'); sys.path.insert(0, HERE + '/../../../landstalker/tools')
import pine, romrender as R
rom = open(sys.argv[1], 'rb').read()
g, r, pa, pb, getpal = R.rom_planes(rom, 475); E = types.SimpleNamespace(t={})
AX, TIPV = 832, 689
W, H = 64, 48; x0, y0 = AX - 32, TIPV - 2
R.compose(pa, E, getpal, x0, y0, W, H, (0, 0, 0), g['tiles']); idx = R.compose.idx
ax = AX - x0; rows = {}
for y in range(H):
    if not idx[y * W + ax]: continue
    x = ax
    while x < W - 1 and idx[y * W + x + 1]: x += 1
    rows[y] = x - ax
last = max(rows); FOOT = last - 2          # drawn foot ~2 rows above the trunk bottom (as the big template: trunk rows below FY)
T = set((dx + 16, y - FOOT + 56) for y, hw in rows.items() for dx in range(-hw, hw + 1))
print('rows', [rows[y] for y in sorted(rows)], 'height px', last - min(rows) + 1, 'max half width', max(rows.values()))
def sil(P, ox, oy):
    S = set()
    for part in pine.pine_parts(ox, oy, 0, P, seed=11):
        for f in part:
            for k in range(1, len(f) - 1):
                tri = [(p[0] - p[1] + 16, (p[0] + p[1]) / 2 - p[2] + 56) for p in (f[0], f[k], f[k + 1])]
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
base = json.load(open(HERE + '/../pine_cluster/params_light.json')); base.pop('_about'); base.pop('offset')
best = None
for Hh, Rr, zb, tiers, tp, o in itertools.product([30, 31, 32, 33], [8, 9, 10, 11], [9, 10, 11, 12, 13], [3, 4], [0.7, 0.8, 0.9], [0, -1, -2]):
    P = dict(base, H=Hh, R=Rr, zb=zb, tiers=tiers, taper=tp); s = iou(sil(P, o, o))
    if best is None or s > best[0]: best = (s, P, o); print('%.3f H %s R %s zb %s tiers %s taper %s o %s' % (s, Hh, Rr, zb, tiers, tp, o), flush=True)
s, P, o = best; S = sil(P, o, o)
print('best', round(s, 3), 'outside', len(S - T), 'missing', len(T - S))
json.dump(dict(P, offset=o, iou=round(s, 3)), open(sys.argv[2], 'w'), indent=1)
