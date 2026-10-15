#!/usr/bin/env python3
"""cmp.py REFDIR RECDIR : iteration counter ($FF0000) and frame counter ($FF0004) per dump, ref vs rec"""
import glob, os, sys
def rd32(b, a):
    return int.from_bytes(bytes(b[((a + i) & 0xFFFF) ^ 1] for i in range(4)), 'big')
ref, rec = sys.argv[1], sys.argv[2]
for f in sorted(glob.glob(ref + '/ram_*.bin')):
    g = os.path.join(rec, os.path.basename(f))
    if not os.path.exists(g): continue
    a, b = open(f, 'rb').read(), open(g, 'rb').read()
    ia, ib = rd32(a, 0xFF0000), rd32(b, 0xFF0000)
    fa, fb = rd32(a, 0xFF0004), rd32(b, 0xFF0004)
    print(f'{os.path.basename(f)}: ref iter={ia:7d} frames={fa:4d} | rec iter={ib:7d} frames={fb:4d} | iter diff {100.0*(ib-ia)/max(ia,1):+.2f}%')
