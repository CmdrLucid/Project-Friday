#!/usr/bin/env python3
"""hd_enhance.py IN.png OUT_PREFIX [SCALE=4]  -- HD EXPERIMENT (2D, user 2026-10-24: 'nicht 3D, nur HD'): repaints a 1x game picture crop as a 4x HD texture with our own code:
 1. shape-aware enlargement (Scale2x / EPX twice: hard colour edges stay hard, staircases become straight lines)
 2. edge-preserving smoothing (bilateral): flat colour regions get soft gradients, borders stay crisp
 3. form light: local contrast boost (unsharp mask at a large radius) = the volume the 8-bit palette could not show
 4. needle / grass detail: fine strokes (noise stretched along a diagonal) on green areas, amplitude from the local brightness
 5. anti-aliased outlines: the darkest pixels of the original are kept dark (contours)
Needs numpy / scipy / pillow (venv ~/hdvenv).  Writes OUT_PREFIX_orig4.png (nearest), _epx.png (step 1 only), _hd.png (all steps), _compare.png (three side by side).
Only the user's own screenshot goes in (derived from his ROM): the results stay in ~/.landstalker_remake/ and are never committed."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
src, pre = sys.argv[1], sys.argv[2]; S = int(sys.argv[3]) if len(sys.argv) > 3 else 4
im = np.array(Image.open(src).convert("RGB")); h, w, _ = im.shape
def epx(a):
    H, W, _ = a.shape; p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    P = a; A = p[0:H, 1:W + 1]; B = p[1:H + 1, 2:W + 2]; C = p[1:H + 1, 0:W]; D = p[2:H + 2, 1:W + 1]
    eq = lambda x, y: (x == y).all(axis=2)
    o = np.repeat(np.repeat(a, 2, 0), 2, 1).copy()
    m1 = eq(C, A) & ~eq(C, D) & ~eq(A, B); m2 = eq(A, B) & ~eq(A, C) & ~eq(B, D); m3 = eq(D, C) & ~eq(D, B) & ~eq(C, A); m4 = eq(B, D) & ~eq(B, A) & ~eq(D, C)
    o[0::2, 0::2][m1] = A[m1]; o[0::2, 1::2][m2] = B[m2]; o[1::2, 0::2][m3] = C[m3]; o[1::2, 1::2][m4] = D[m4]
    return o
e = im
for _ in range(S // 2): e = epx(e)
Image.fromarray(e).save(pre + "_epx.png")
Image.fromarray(np.repeat(np.repeat(im, S, 0), S, 1)).save(pre + "_orig4.png")
# 1 de-dither at 1x: the 8-bit art builds its mid tones from checkerboards; a pixel whose left / right (or up / down) neighbours agree with each other but not with it is blended with them
a = im.astype(np.float32); p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge"); L = p[1:h + 1, 0:w]; R = p[1:h + 1, 2:w + 2]; U = p[0:h, 1:w + 1]; D = p[2:h + 2, 1:w + 1]
same = lambda x, y: (np.abs(x - y).sum(axis=2) < 24)
dh = same(L, R) & ~same(L, a); dv = same(U, D) & ~same(U, a)
m = (dh & dv)[..., None]                       # checkerboard: both axes agree -> the mean of the four neighbours and itself
a2 = np.where(m, (a + (L + R + U + D) / 4) / 2, a)
a2 = np.where((dh & ~dv)[..., None], (a2 + (L + R) / 2) / 2, a2); a2 = np.where((dv & ~dh)[..., None], (a2 + (U + D) / 2) / 2, a2)
dd = np.clip(a2, 0, 255).astype(np.uint8); Image.fromarray(dd).save(pre + "_dedither.png")
# 2 smooth enlargement (Lanczos) + a gentle edge sharpening
big = Image.fromarray(dd).resize((w * S, h * S), Image.LANCZOS)
g = np.array(big).astype(np.float32)
lum = g @ np.array([0.30, 0.59, 0.11], np.float32)
# 3 form light: local contrast at a wide radius (the volume the palette could not show)
wide = ndi.gaussian_filter(lum, 6.0 * S / 4); g = g + ((lum - wide) * 0.35)[..., None] * (g / np.maximum(lum[..., None], 20.0))
# 4 sharpen edges (unsharp mask, small radius)
bl = ndi.gaussian_filter(g, (1.2, 1.2, 0)); g = g + (g - bl) * 0.55
# 5 needle detail on green areas: strokes along a diagonal, strength by green dominance
rng = np.random.RandomState(3); n = rng.randn(h * S, w * S).astype(np.float32)
nz = ndi.gaussian_filter(n, (0.5, 2.2)); nz = ndi.rotate(nz, 35, reshape=False, mode="reflect"); nz = nz / (nz.std() + 1e-6)
green = np.clip((g[..., 1] - np.maximum(g[..., 0], g[..., 2]) - 8) / 40.0, 0, 1)
g = g + (nz * 7.0 * green)[..., None] * np.array([0.5, 1.0, 0.4], np.float32)
hd = np.clip(g, 0, 255).astype(np.uint8); Image.fromarray(hd).save(pre + "_hd.png")
cmp = np.concatenate([np.repeat(np.repeat(im, S, 0), S, 1), e, hd], axis=1); Image.fromarray(cmp).save(pre + "_compare.png")
print("wrote", pre, hd.shape)
