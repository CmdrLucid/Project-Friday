#!/usr/bin/env python3
"""Compare Nigel's state in two --ram-dump directories (reference vs recompiled).

usage: traj.py REFDIR RECDIR [START_FRAME] [END_FRAME]
Columns: X Y Z fall jump ground action (hex). Extra byte addresses can be added with
env TRAJ_EXTRA=FF1234,FF1235 (appended as bytes).  Dumps hold work RAM first,
byte-swapped within words (the byte at 68K address A is file index A^1).
"""
import glob, os, sys

def load(d):
    return {int(os.path.basename(f)[4:10]): f for f in glob.glob(os.path.join(d, 'ram_*.bin'))}

def b(buf, a):
    return buf[(a & 0xFFFF) ^ 1]

def w(buf, a):
    return (b(buf, a) << 8) | b(buf, a + 1)

def row(buf, extra):
    r = [b(buf, 0xFF5400), b(buf, 0xFF5401), w(buf, 0xFF5412), b(buf, 0xFF5420),
         b(buf, 0xFF5421), b(buf, 0xFF5422), w(buf, 0xFF542C)]
    r += [b(buf, a) for a in extra]
    return r

def main():
    ref, rec = load(sys.argv[1]), load(sys.argv[2])
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    end = int(sys.argv[4]) if len(sys.argv) > 4 else 1 << 30
    extra = [int(x, 16) for x in os.environ.get('TRAJ_EXTRA', '').split(',') if x]
    print('frame | REF: X Y Z fall jump gnd act | REC: ...')
    for fr in sorted(set(ref) & set(rec)):
        if fr < start or fr > end:
            continue
        a = row(open(ref[fr], 'rb').read(), extra)
        c = row(open(rec[fr], 'rb').read(), extra)
        fmt = lambda r: ' '.join('%X' % v for v in r)
        print('%5d | %-26s | %-26s%s' % (fr, fmt(a), fmt(c), '' if a == c else ' <-- differs'))

main()
