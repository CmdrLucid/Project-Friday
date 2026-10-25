#!/usr/bin/env python3
"""rom_sprite.py ROM GFX ANIM FRAME OUT.png [--scale2x]
One figure frame from the user's own ROM as an RGBA cut-out (LOCAL only, never into git): frame pieces + tiles by landstalker/tools/romsprite.py
(port of LoadSpriteFrame $004230), colours = DefaultPlayerPal $901C (palette line of Nigel; other figures need their own palette).
GFX = SpriteGraphic (entity +0B; Nigel 0), ANIM = AnimationIndex (entity +24, steps of 4), FRAME = AnimationFrame (entity +26, steps of 4).
Writes OUT.png and OUT.txt ('ox oy' = pixel of the image that sits on the figure's anchor, the piece origin 0,0).
Used by the remake previews to stand a figure billboard next to an asset (remake/recipes/*: R_FIGURE)."""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "tools"))
import romsprite
from rom_picture import png

def scale2x(w, h, px):
    out = [None] * (4 * w * h); g = lambda x, y: px[min(max(y, 0), h - 1) * w + min(max(x, 0), w - 1)]
    for y in range(h):
        for x in range(w):
            P = g(x, y); A, B, C, D = g(x, y - 1), g(x + 1, y), g(x - 1, y), g(x, y + 1)
            e0 = A if (C == A and C != D and A != B) else P; e1 = B if (A == B and A != C and B != D) else P
            e2 = C if (D == C and D != B and C != A) else P; e3 = D if (B == D and B != A and D != C) else P
            o = (2 * y) * 2 * w + 2 * x; out[o], out[o + 1], out[o + 2 * w], out[o + 2 * w + 1] = e0, e1, e2, e3
    return 2 * w, 2 * h, out

def main():
    rom = open(sys.argv[1], 'rb').read(); gfx, anim, frm = (int(v, 0) for v in sys.argv[2:5]); outp = sys.argv[5]
    f = romsprite.frame(rom, gfx, anim, frm)
    pal = [struct.unpack('>H', rom[romsprite.DEFAULT_PLAYER_PAL + 2 * i: romsprite.DEFAULT_PLAYER_PAL + 2 * i + 2])[0] for i in range(16)]
    rgb = [(((c >> 1) & 7) * 36, ((c >> 5) & 7) * 36, ((c >> 9) & 7) * 36) for c in pal]
    x0 = min(x for x, y, w, h in f['pieces']); y0 = min(y for x, y, w, h in f['pieces'])
    x1 = max(x + w * 8 for x, y, w, h in f['pieces']); y1 = max(y + h * 8 for x, y, w, h in f['pieces'])
    W, H = x1 - x0, y1 - y0; img = [None] * (W * H); t0 = 0
    for x, y, w, h in f['pieces']:
        for px in range(w * 8):
            for py in range(h * 8):
                t = t0 + (px // 8) * h + (py // 8); a = t * 32 + (py % 8) * 4 + (px % 8) // 2
                b = f['tiles'][a] if a < len(f['tiles']) else 0; idx = (b >> 4) if px % 2 == 0 else (b & 15)
                o = (y - y0 + py) * W + (x - x0 + px)
                if idx and img[o] is None: img[o] = rgb[idx]
        t0 += w * h
    k = 1
    if '--scale2x' in sys.argv: W, H, img = scale2x(W, H, img); k = 2
    data = bytearray()
    for p in img: data += bytes(p + (255,)) if p else bytes(4)
    png(outp, W, H, data, 4)
    open(os.path.splitext(outp)[0] + '.txt', 'w').write('%d %d %d\n' % (-x0 * k, -y0 * k, k))
    print(outp, W, H, 'pieces', len(f['pieces']))

if __name__ == '__main__': main()
