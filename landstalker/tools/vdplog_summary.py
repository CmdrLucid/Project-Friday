#!/usr/bin/env python3
"""vdplog_summary.py LOGFILE   -- summarises `LANDSTALKER_VDPLOG=1` output: per plane and per writing function the number of frames / writes, the column and row ranges
and a few example lines, so the scroll / column loader of the game stands out. Prints only addresses and counts."""
import re, sys, collections
pat = re.compile(r'vdplog f=(\d+)(.*?)\| hs=(\d+),(\d+) vs=(\d+),(\d+)')
seg = re.compile(r'([ABW]):(\d+) cols (\d+)-(\d+) rows (\d+)-(\d+) by((?: \$[0-9A-F]{6}\(\$[0-9A-F]{6}\)x\d+)+)(?: rs((?: \d+:\d+-\d+)*))?')
spans = collections.Counter(); narrow = collections.Counter(); wide_ = collections.Counter()
by = collections.defaultdict(lambda: dict(frames=0, writes=0, c0=99, c1=-1, r0=99, r1=-1, ex=[]))
frames = 0; hs_prev = None; dh = collections.Counter()
for line in open(sys.argv[1], errors='replace'):
    m = pat.search(line)
    if not m: continue
    frames += 1
    f, body, hsa, hsb = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
    if hs_prev is not None and f - hs_prev[0] <= 2:
        dh[(hsa - hs_prev[1]) % 1024 if (hsa - hs_prev[1]) % 1024 < 512 else (hsa - hs_prev[1]) % 1024 - 1024] += 1
    hs_prev = (f, hsa)
    for s in seg.finditer(body + '|'):
        pl, n, c0, c1, r0, r1, bys = s.group(1), int(s.group(2)), int(s.group(3)), int(s.group(4)), int(s.group(5)), int(s.group(6)), s.group(7)
        for rs in re.finditer(r'(\d+):(\d+)-(\d+)', s.group(8) or ''):
            spans[(pl, int(rs.group(2)), int(rs.group(3)))] += 1
        widths = [int(r.group(3)) - int(r.group(2)) + 1 for r in re.finditer(r'(\d+):(\d+)-(\d+)', s.group(8) or '')]
        for fn in re.finditer(r'\$([0-9A-F]{6})\(\$([0-9A-F]{6})\)x(\d+)', bys):
            if widths and min(widths) <= 2 and pl in 'AB' and int(fn.group(3)) < 400: narrow[(pl, fn.group(1), fn.group(2))] += 1
            if widths and max(widths) >= 40 and pl in 'AB' and int(fn.group(3)) < 400: wide_[(pl, fn.group(1), fn.group(2))] += 1
            d = by[(pl, fn.group(1), fn.group(2))]
            d['frames'] += 1; d['writes'] += int(fn.group(3)); d['c0'] = min(d['c0'], c0); d['c1'] = max(d['c1'], c1); d['r0'] = min(d['r0'], r0); d['r1'] = max(d['r1'], r1)
            if len(d['ex']) < 3: d['ex'].append('f%d cols %d-%d rows %d-%d hsA=%d' % (f, c0, c1, r0, r1, hsa))
dma = collections.Counter()
for line in open(sys.argv[1], errors='replace'):
    m = re.match(r'vdpdma (\S+) f=(\d+) code=(\w+) addr=(\w+) len=(\d+) by (\$\w+\(\$\w+\))', line)
    if m: dma[(m.group(1), m.group(3), m.group(4), int(m.group(5)), m.group(6))] += 1
print('%d frames with nametable writes' % frames)
print('DMA operations (kind, code, VRAM address, length, by function): count')
for (k, c, a, n, f), cnt in dma.most_common(16): print('   %-9s code=%s addr=%s len=%d by %s : %d' % (k, c, a, n, f, cnt))
for (pl, fn, par), d in sorted(by.items(), key=lambda kv: -kv[1]['writes'])[:25]:
    print('plane %s  fn $%s (caller $%s): %d frames, %d writes, cols %d-%d rows %d-%d' % (pl, fn, par, d['frames'], d['writes'], d['c0'], d['c1'], d['r0'], d['r1']))
    for e in d['ex']: print('      ' + e)
print('column spans written per tile row (plane, first col - last col): count')
for (pl, c0, c1), n in spans.most_common(14): print('   %s cols %d-%d (%d wide): %d rows' % (pl, c0, c1, c1 - c0 + 1, n))
print('narrow (<= 2 columns) spans: which function wrote them (frames with such a span / total):')
for (pl, fn, par), n in narrow.most_common(10): print('   plane %s by $%s (caller $%s): %d frames' % (pl, fn, par, n))
print('wide (>= 40 columns) spans: which function wrote them:')
for (pl, fn, par), n in wide_.most_common(8): print('   plane %s by $%s (caller $%s): %d frames' % (pl, fn, par, n))
print('hscroll A step between neighbouring logged frames:', dict(dh.most_common(8)))
