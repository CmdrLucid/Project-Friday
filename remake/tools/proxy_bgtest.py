#!/usr/bin/env python3
"""proxy_bgtest.py ROM ROOM FINE_DUMP U0 V0 W H OUT.png [--sea SX,SY,SW,SH] [--seaz Z] [--scale N]
BACKGROUND TEST for an INDOOR light shape as the LIGHT sees it (user 2026-11-08, ship 493: 'wo scheint beim Drueberlegen Hintergrund durch?'):
every picture pixel's view ray goes down through the light's fine heights (4 unit sub columns, written by the game with
LANDSTALKER_LT_DUMPFINE=prefix -> prefix_ROOM.txt) like the game's own view ray (lk_lt_rayi); slabs are skipped (only layer A pixels sit on them).
A pixel is WRONG when
  - the ray hits the shape (hit z > sea + 3) but the picture shows SEA there      -> magenta ('model over background': the shape is too big there)
  - the ray reaches the sea floor but the picture shows something else (not sea)  -> yellow  ('background over model': the shape is too small)
Sea = the picture's colour indices found in the reference rectangle --sea (window coordinates, default: the window's top left 40 x 40) plus the
light water / foam colours seen next to them.  Prints the counts and, per wrong pixel cluster, the world position of the hit (so the recipe can be fixed),
writes OUT.png (picture, wrong pixels coloured, scaled).  Local check picture (ROM-derived): never commit it.
Projection (docs/FORMATS.md): U = x - y + 1184, V = (x + y) / 2 - z."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "tools"))
import romrender
from PIL import Image

def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

a = [s for i, s in enumerate(sys.argv[1:], 1) if not s.startswith('--') and not (i > 1 and sys.argv[i - 1].startswith('--'))]
rom = open(a[0], 'rb').read(); room = int(a[1]); fine = a[2]; U0, V0, W, H = map(int, a[3:7]); out = a[7]
SEAZ = float(opt('--seaz', '-22')); SC = int(opt('--scale', '3'))
sx0, sy0, sw, sh = map(int, opt('--sea', '0,0,40,40').split(','))

# the light's fine heights (slabs ignored: sea pixels are layer B)
rows = [l.split() for l in open(fine)]
FH = np.array([[int(c.split('/')[0]) for c in r] for r in rows], dtype=np.int32)
N = FH.shape[0]

# the picture + colour indices
g, r, pa, pb, getpal = romrender.rom_planes(rom, room)
rgb = romrender.compose(pa, pb, getpal, U0, V0, W, H, (0, 0, 0), g['tiles'])
idx = np.array(romrender.compose.idx, dtype=np.int32).reshape(H, W)
pic = np.frombuffer(bytes(rgb), np.uint8).reshape(H, W, 3)
sea_set = set(np.unique(idx[sy0:sy0 + sh, sx0:sx0 + sw]).tolist())
sea = np.isin(idx, list(sea_set))

# view rays: for every pixel step z down from high above; x - y = D, x + y = 2 (V + z)
Us = U0 + np.arange(W)[None, :] + 0.5; Vs = V0 + np.arange(H)[:, None] + 0.5
D = np.broadcast_to(Us - 1184.0, (H, W)); Vv = np.broadcast_to(Vs, (H, W))
hitz = np.full((H, W), np.nan); hx = np.zeros((H, W)); hy = np.zeros((H, W))
todo = np.ones((H, W), bool)
for z in np.arange(400.0, SEAZ - 1.0, -0.5):
    xs = (2 * (Vv + z) + D) / 2; ys = (2 * (Vv + z) - D) / 2
    sxi = np.floor(xs / 4).astype(int); syi = np.floor(ys / 4).astype(int)
    ok = (sxi >= 0) & (syi >= 0) & (sxi < N) & (syi < N)
    h = np.full((H, W), -32768); h[ok] = FH[syi[ok], sxi[ok]]
    hit = todo & (z <= h)
    hitz[hit] = z; hx[hit] = xs[hit]; hy[hit] = ys[hit]; todo &= ~hit
    if not todo.any(): break
onship = ~np.isnan(hitz) & (hitz > SEAZ + 3)
over = onship & sea                     # shape over background
under = ~onship & ~sea & ~np.isnan(hitz) & (hitz <= SEAZ + 3)   # drawn ship, light sees the sea
print('room %d window U %d..%d V %d..%d: sea colours %s' % (room, U0, U0 + W, V0, V0 + H, sorted(sea_set)))
print('shape over background (magenta): %d px; background over shape (yellow): %d px' % (over.sum(), under.sum()))
# clusters of 'over' pixels by sub column of the hit
if over.any():
    keys = {}
    for yy, xx in zip(*np.nonzero(over)):
        k = (int(hx[yy, xx] // 4), int(hy[yy, xx] // 4)); keys.setdefault(k, []).append((xx, yy, hitz[yy, xx]))
    print('sub columns seen over background (world x0..x1, y0..y1, light height, pixels, max hit z):')
    for (kx, ky), v in sorted(keys.items(), key=lambda t: -len(t[1]))[:40]:
        print('  x %4d..%4d y %4d..%4d  h %4d  %3d px  z<=%.0f' % (4 * kx, 4 * kx + 4, 4 * ky, 4 * ky + 4, FH[ky, kx], len(v), max(p[2] for p in v)))
img = pic.copy()
img[over] = (255, 0, 255); img[under] = (255, 255, 0)
Image.fromarray(img).resize((W * SC, H * SC), Image.NEAREST).save(out)
print('written', out)
