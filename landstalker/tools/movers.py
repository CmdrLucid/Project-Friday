#!/usr/bin/env python3
"""movers.py REFDIR RECDIR [first] [last]

Per-frame dumps required. The entity structs are taken as 0x40-byte blocks from $FF5400 (n = 0..40); screen position fields at +0x0F (x) and +0x11 (y) as seen in
the ref-vs-rec diffs. For every block: mean movement per frame (|dx|+|dy|) in ref and rec, the number of frames in which the position fields differ between ref and
rec, and the first such frame. The fastest mover in the village is the dog (user observation: 'the dog moves faster than the other sprites')."""
import os, sys
ref, rec = sys.argv[1], sys.argv[2]
first = int(sys.argv[3]) if len(sys.argv) > 3 else 0
last = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
N = 41
def pos(b, n):
    base = 0x5400 + n * 0x40
    return b[(base + 0x0F) ^ 1], b[(base + 0x11) ^ 1]
def step(p, q):
    d = [(q[i] - p[i]) & 0xFF for i in range(2)]
    return sum(x if x < 128 else 256 - x for x in d)
ks = sorted(int(f[4:10]) for f in os.listdir(ref) if f.startswith('ram_') and first <= int(f[4:10]) <= last)
prev = {}; mv = {'ref': [0] * N, 'rec': [0] * N}; ndiff = [0] * N; fdiff = [None] * N; frames = 0
active = [0] * N
for k in ks:
    g = os.path.join(rec, 'ram_%06d.bin' % k)
    if not os.path.exists(g): continue
    a = open(os.path.join(ref, 'ram_%06d.bin' % k), 'rb').read(65536); b = open(g, 'rb').read(65536)
    frames += 1
    for n in range(N):
        pa, pb = pos(a, n), pos(b, n)
        if pa != pb:
            ndiff[n] += 1
            if fdiff[n] is None: fdiff[n] = k
        if 'ref' in prev and (n in prev['ref']):
            mv['ref'][n] += step(prev['ref'][n], pa); mv['rec'][n] += step(prev['rec'][n], pb)
        if pa != (0, 0) or pb != (0, 0): active[n] += 1
    prev['ref'] = {n: pos(a, n) for n in range(N)}; prev['rec'] = {n: pos(b, n) for n in range(N)}
print('%d consecutive dumps; mean movement per dump (|dx|+|dy|), fastest first' % frames)
print('block  address   ref_speed  rec_speed  frames_pos_differs  first_diff  active_frames')
for n in sorted(range(N), key=lambda x: -mv['ref'][x])[:10]:
    if mv['ref'][n] == 0 and mv['rec'][n] == 0: continue
    print('%5d  $FF%04X   %8.2f  %8.2f  %10d  %10s  %8d' % (n, 0x5400 + n * 0x40, mv['ref'][n] / max(frames - 1, 1), mv['rec'][n] / max(frames - 1, 1),
          ndiff[n], fdiff[n], active[n]))
