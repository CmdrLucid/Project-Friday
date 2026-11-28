# mix.py DRY.wav OUT.wav DECAY_S WET DRY : convolution hall (noise tail + early reflections), normalised
import sys, numpy as np, scipy.io.wavfile as wf, scipy.signal as ss
src, out, decay, wetg, dryg = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
sr, x = wf.read(src); x = x.astype(np.float32) / 32768
rng = np.random.default_rng(1); n = int(decay * 1.2 * sr); t = np.arange(n) / sr; ir = np.zeros((n, 2), np.float32)
lp = ss.butter(2, 5000 / (sr / 2), 'low', output='sos')
for c in range(2):
    ir[:, c] = ss.sosfilt(lp, rng.standard_normal(n)) * np.exp(-t / (decay / 4.0)) * (1 - np.exp(-t / 0.01))
    for dt, g in [(0.011, .5), (0.017, .4), (0.023, .35), (0.031, .3)]: ir[int((dt + 0.003 * c) * sr), c] += g
ir /= np.sqrt((ir ** 2).sum(0))
wet = np.stack([ss.fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)
y = dryg * x + wetg * wet; y = y / np.abs(y).max() * 0.89
wf.write(out, sr, (y * 32767).astype(np.int16)); print(out)
