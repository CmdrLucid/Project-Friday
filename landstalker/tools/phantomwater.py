#!/usr/bin/env python3
"""phantomwater.py DUMPDIR [RADIUS]  -- finds PHANTOM WATER: light cells (LANDSTALKER_LT_DUMPFILE dump, 'height[w]:word' per cell) raised >= 32 above the
NEAREST lower light water within RADIUS (12) cells whose cell diamond shows DRAWN water (blue) in the room picture (romrender via phantomcheck.picture)
both at its light height and at that water level: the light's void painter copied a rock / walkway / barrier height into a lake / river / sea
(482, 2026-11-28 survey: 183 465 468 475 489 490 501 523 525 737).  Such blocks are invisible but cast box shadows / sword-glow edges on the water.
Prints 'room R: N cells (x,y)H->L[G] ...' (G = a height map cell, not filled void: usually a waterfall or a blue wall, check by eye).
False hits: waterfalls (blue at every height: 426 478 481 568) and blue walls (475 Mir's tower).  Make the dumps with
  LANDSTALKER_LT_DUMPFILE=DIR/lt python3 tools/proxysurvey.py ROM [ROOMS] --run OUTDIR   (proxysurvey passes the LANDSTALKER_LT_* test aids through)
and fix the cells with data/light_proxies.json 'water' ops [x, y, x, y, L]; re-dump and repeat until 0 (a block can be wider than the first pass shows).
Local test aid: reads the ROM, writes nothing."""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phantomcheck, numpy as np
ROM = open(os.environ.get('LANDSTALKER_ROM', '/home/deck/Documents/NonSteamGames/landstalker/landstalker.md'), 'rb').read()
d = sys.argv[1]; R = int(sys.argv[2]) if len(sys.argv) > 2 else 12
def frac(rgb, x, y, z):
    n = b = 0
    for i in np.linspace(.15, .85, 5):
        for j in np.linspace(.15, .85, 5):
            u = int(16 * ((x + i) - (y + j)) + 1184); v = int(8 * ((x + i) + (y + j)) - z)
            if not (0 <= v < rgb.shape[0] and 0 <= u < rgb.shape[1]): continue
            r, g, bb = rgb[v, u].astype(int); n += 1; b += bb > r + 40 and bb > g
    return b / n if n else 0
for fn in sorted(os.listdir(d), key=lambda f: int(re.findall(r'\d+', f)[-1])):
    room = int(re.findall(r'\d+', fn)[-1]); D = [l.split() for l in open(os.path.join(d, fn)) if l.strip()]
    H = {}; W = set()
    for y, row in enumerate(D):
        for x, c in enumerate(row):
            h = c.split(':')[0]
            if h != '-32768': H[(x, y)] = int(h.rstrip('w')); (h.endswith('w') and W.add((x, y)))
    rgb = None; hits = []
    for (x, y), h in H.items():
        low = sorted((max(abs(i), abs(j)), H[(x + i, y + j)]) for i in range(-R, R + 1) for j in range(-R, R + 1) if (x + i, y + j) in W and H[(x + i, y + j)] <= h - 32)
        if not low: continue
        L = min(l for dd, l in low if dd == low[0][0])   # the NEAREST lower water (its level)
        if rgb is None: rgb = phantomcheck.picture(ROM, room)[0]
        a = frac(rgb, x, y, L); b = frac(rgb, x, y, h)
        if a >= .5 and b >= .5: hits.append((x, y, h, L, a, b, (x, y) in W))
    if hits:
        print('room %d: %d cells' % (room, len(hits)), ' '.join('(%d,%d)%d->%d%s' % (x, y, h, L, '' if w else 'G') for x, y, h, L, a, b, w in sorted(hits, key=lambda t: (t[1], t[0]))))
