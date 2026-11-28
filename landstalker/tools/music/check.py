# check.py NOTES.json ORIG.wav : render all chip notes neutral (piano) and compare the pitch-class content (chroma) with the original per 0.25 s
import os, sys, json, subprocess, numpy as np, scipy.io.wavfile as wf, scipy.signal as ss, mido
d = json.load(open(sys.argv[1]))["notes"]; TPB, BPM = 480, 120.0
mid = mido.MidiFile(ticks_per_beat=TPB); tr = mido.MidiTrack(); mid.tracks.append(tr); tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM)))
ev = []
for n in d:
    if not isinstance(n["p"], float) or n["ch"] == "fm4": continue
    p = int(round(n["p"])); t0 = n["t0"]; t1 = max(n["t1"], t0 + 0.08)
    ev += [(int(t0 * 2 * TPB), 1, p), (int(t1 * 2 * TPB), 0, p)]
ev.sort(); now = 0
for t, on, p in ev: tr.append(mido.Message("note_on" if on else "note_off", note=p, velocity=80 if on else 0, time=t - now)); now = t
mid.save("chk.mid"); subprocess.run([os.path.join(os.path.dirname(os.path.abspath(__file__)), "render"), "GeneralUser-GS.sf2", "chk.mid", "chk.wav", "-6"], capture_output=True)
def chroma(path, n_sec):
    sr, x = wf.read(path); x = x.astype(np.float32).mean(1)[: int(n_sec * sr)]
    f, t, Z = ss.stft(x, sr, nperseg=8192, noverlap=8192 - 2205); A = np.abs(Z)
    C = np.zeros((12, A.shape[1])); ok = (f > 90) & (f < 3000)
    pc = (np.round(12 * np.log2(f[ok] / 440.0)) + 69).astype(int) % 12
    for k in range(12): C[k] = A[ok][pc == k].sum(0)
    C /= C.sum(0, keepdims=True) + 1e-9; return t, C
t, Co = chroma(sys.argv[2], 64); _, Cn = chroma("chk.wav", 64); n = min(Co.shape[1], Cn.shape[1]) - 40
best = max(range(-20, 21), key=lambda L: np.nanmean([np.corrcoef(Co[:, i + 20], Cn[:, i + 20 + L])[0, 1] for i in range(0, n - 40, 3)]))
print("best lag %.2f s" % (best * 0.05)); Cn = np.roll(Cn, -best, axis=1)
r = np.array([np.corrcoef(Co[:, i], Cn[:, i])[0, 1] for i in range(n)])
print("chroma correlation per 0.05 s frame: median %.2f, share > 0.7: %.0f %%, share < 0.3: %.0f %%" % (np.nanmedian(r), 100 * np.mean(r > 0.7), 100 * np.mean(r < 0.3)))
bad = [round(t[i], 1) for i in range(n) if r[i] < 0.3]; print("weak moments (s):", bad[:25])
