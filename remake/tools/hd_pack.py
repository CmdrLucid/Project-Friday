#!/usr/bin/env python3
"""hd_pack.py FRAME_1x.png IDSHOT.png TILENAMES.json DUMPDIR PACKDIR [SCALE=4]  -- HD tile pack for the tiles visible in ONE game frame (2D HD experiment, user 2026-10-24).
FRAME_1x = screenshot of the frame at 1x (LANDSTALKER_SHOT); IDSHOT = HD screenshot (scale 2) of the SAME frame made with an 'id pack' (every tile of the dump replaced by an image whose
colour encodes tile number + position in the tile, see remake/ASSETS.md 'HD pack'); the id map tells for every screen pixel which tile (and flipped how) is drawn there.  The whole frame is enhanced
with hd_enhance (same code), then every tile gets the piece of the enhanced picture where it is drawn most completely; alpha 0 where the original tile is transparent (the game's pixel stays).
Output: PACKDIR/XXXXXX_NNNN.rgba (8 * SCALE square RGBA).  Local files only (derived from the user's ROM): never committed."""
import sys, os, json, collections, subprocess, numpy as np
from PIL import Image
f1, ids, names_p, dump, pack = sys.argv[1:6]; S = int(sys.argv[6]) if len(sys.argv) > 6 else 4
names = json.load(open(names_p)); os.makedirs(pack, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__))
pre = "/tmp/hdp_frame"
subprocess.check_call([sys.executable, os.path.join(here, "hd_enhance.py"), f1, pre, str(S)])
hd = np.array(Image.open(pre + "_hd.png").convert("RGB"))
idm = np.array(Image.open(ids).convert("RGB")).astype(int); H2, W2, _ = idm.shape
R, G, B = idm[..., 0], idm[..., 1], idm[..., 2]; tid = R | (G << 8); tx = ((B >> 7) & 1) * 8 + ((B >> 3) & 7); ty = ((B >> 6) & 1) * 8 + (B & 7)
valid = (tid >= 1) & (tid <= len(names))
inst = collections.Counter()
for Y in range(H2 - 1):
    for X in range(W2 - 1):
        if not valid[Y, X]: continue
        i = tid[Y, X]
        if tid[Y, X + 1] != i or tid[Y + 1, X] != i: continue
        dx = tx[Y, X + 1] - tx[Y, X]; dy = ty[Y + 1, X] - ty[Y, X]
        if abs(dx) != 1 or abs(dy) != 1: continue
        fx = 0 if dx == 1 else 1; fy = 0 if dy == 1 else 1
        ox = X - tx[Y, X] if fx == 0 else X + tx[Y, X] - 15; oy = Y - ty[Y, X] if fy == 0 else Y + ty[Y, X] - 15
        inst[(int(i), fx, fy, int(ox), int(oy))] += 1
best = {}
for (i, fx, fy, ox, oy), c in inst.items():
    if ox < 0 or oy < 0 or ox + 16 > W2 or oy + 16 > H2: continue
    if i not in best or c > best[i][0]: best[i] = (c, fx, fy, ox, oy)
n = 0
for i, (c, fx, fy, ox, oy) in best.items():
    if c < 60: continue
    gx, gy = ox // 2, oy // 2                                   # game pixel origin of the tile (the id shot is at 2x)
    piece = hd[gy * S:(gy + 8) * S, gx * S:(gx + 8) * S].copy()
    if piece.shape[:2] != (8 * S, 8 * S): continue
    if fx: piece = piece[:, ::-1]
    if fy: piece = piece[::-1, :]
    idx = open(os.path.join(dump, names[i - 1] + ".idx"), "rb").read()
    a = np.repeat(np.repeat((np.frombuffer(idx, np.uint8).reshape(8, 8) != 0).astype(np.uint8) * 255, S, 0), S, 1)
    rgba = np.dstack([piece, a]).astype(np.uint8)
    open(os.path.join(pack, names[i - 1] + ".rgba"), "wb").write(rgba.tobytes()); n += 1
print("tiles in the pack:", n, "of", len(best), "seen")
