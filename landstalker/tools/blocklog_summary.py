#!/usr/bin/env python3
"""blocklog_summary.py LOGFILE   -- summarises `LANDSTALKER_BLOCKLOG=1` output (map loader geometry).
Per calling strip loader / caller: how many blocks, the offset of the map block to the camera, the step between consecutive blocks of a strip (map vs plane cell),
and WHERE ON THE SCREEN the written plane cells appear: x = (col*16 + hscrollA) mod 512, y = (row*16 - vscrollA) mod 256 (cell pixel position of the 16x16 block; the
visible window is x in [0,320) and y in [0,224), a widescreen picture adds e pixels on each side). Names and numbers only."""
import re, sys, collections
pat = re.compile(r'blk f=(\d+) by=\$(\w+) cam=(\d+),(\d+) a6=(\w+) map=(\d+),(\d+) d2=(\w+) cell=(\d+),(\d+) hs=(\d+) vs=(\d+)')
spat = re.compile(r'strip f=(\d+) fn=\$(\w+) by=\$(\w+) cam=(\d+),(\d+) phase=(\d+) hs=(\d+) vs=(\d+)')
rows = []; strips = collections.Counter()
for line in open(sys.argv[1], errors='replace'):
    m = pat.search(line)
    if m: rows.append((int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4)), int(m.group(6)), int(m.group(7)), int(m.group(9)), int(m.group(10)), int(m.group(11)), int(m.group(12)))); continue
    s = spat.search(line)
    if s: strips[(s.group(2), s.group(3))] += 1
print('%d BlockToTiles calls, %d strip-loader entries' % (len(rows), sum(strips.values())))
print('strip loader entries (fn, caller): count'); [print('   $%s by $%s : %d' % (k[0], k[1], n)) for k, n in strips.most_common(14)]
g = collections.defaultdict(list)
for r in rows: g[r[1]].append(r)
for by, rs in sorted(g.items(), key=lambda kv: -len(kv[1]))[:10]:
    dx = collections.Counter((r[4] - r[2], r[5] - r[3]) for r in rs)
    sx = [((r[6] * 16 + r[8]) % 512) for r in rs]; sy = [((r[7] * 16 - r[9]) % 256) for r in rs]
    print('--- called from $%s: %d blocks' % (by, len(rs)))
    print('    map block minus camera (dx,dy) most common:', dict(dx.most_common(6)))
    print('    screen x of the 16x16 cells: %d..%d   y: %d..%d   (visible 0..319 / 0..223)' % (min(sx), max(sx), min(sy), max(sy)))
    # steps inside one strip (consecutive rows of the same frame)
    st = collections.Counter()
    for a, b in zip(rs, rs[1:]):
        if a[0] == b[0]: st[(b[4] - a[4], b[5] - a[5], (b[6] - a[6]) % 32, (b[7] - a[7]) % 16)] += 1
    print('    step between consecutive blocks (dmapx,dmapy,dcol,drow):', dict(st.most_common(4)))
    for r in rs[:2]: print('    e.g. f=%d cam=%d,%d map=%d,%d cell=%d,%d hs=%d vs=%d' % (r[0], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9]))
