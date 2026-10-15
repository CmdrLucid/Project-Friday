#!/usr/bin/env python3
"""wavcmp.py A.wav [B.wav]  -- lists the sound events of captures made with LANDSTALKER_WAV (recompiled build vs genrecomp_ref, same input replay).
An event = a stretch of 20 ms windows louder than a threshold; per event: start, length, peak loudness (RMS) and a rough pitch from the zero-crossing rate.
Pure Python (no numpy).  Compare the lists of A and B side by side: same number of events, same lengths, same pitches = same sound."""
import array, math, sys, wave

def load(p):
    w = wave.open(p, 'rb'); a = array.array('h'); a.frombytes(w.readframes(w.getnframes()))
    return [(a[i] + a[i+1]) / 65536.0 for i in range(0, len(a) - 1, 2)]

def events(x, sr=44100, win=0.02, thr=0.01):
    hop = int(sr * win); out = []; cur = None
    for i in range(len(x) // hop):
        seg = x[i*hop:(i+1)*hop]; rms = math.sqrt(sum(v*v for v in seg) / hop)
        if rms > thr:
            zc = sum(1 for k in range(1, hop) if (seg[k-1] < 0) != (seg[k] < 0)) * sr / (2.0 * hop)
            if cur is None: cur = [i, i, 0.0, []]
            cur[1] = i; cur[2] = max(cur[2], rms); cur[3].append(zc)
        elif cur is not None: out.append(cur); cur = None
    if cur: out.append(cur)
    return [(e[0]*win, (e[1]-e[0]+1)*win, e[2], sorted(e[3])[len(e[3])//2]) for e in out]

def show(name, ev, lo=0, hi=60):
    print("%s: %d events" % (name, len(ev)))
    for t, l, a, f in ev[lo:hi]: print("   t=%7.2fs  len=%5.0f ms  peak rms=%.3f  pitch~%5.0f Hz" % (t, l*1000, a, f))

if __name__ == '__main__':
    for p in sys.argv[1:3]:
        x = load(p); print("%s: %.1f s of audio" % (p, len(x) / 44100)); show(p, events(x))
