#!/usr/bin/env python3
"""rom_picture.py ROM ROOM U0 V0 W H OUTDIR [--scale2x]
Cuts a window out of the room PICTURE drawn from the user's own ROM (landstalker/tools/romrender.py) and writes, LOCALLY (never into git):
  OUTDIR/layerA.png   RGBA, plane A only = the OBJECTS (houses, trees, fences) as clean cut-outs, alpha 0 where plane A has colour index 0
  OUTDIR/full.png     RGB, both planes composed (reference)
  OUTDIR/window.txt   'U0 V0 W H SCALE' so recipes can map a world point: U = wx - wy + 1184, V = (wx + wy) / 2 - z  (docs/FORMATS.md, 'Height map = a real height field')
--scale2x doubles the pictures with Scale2x (EPX): pixel art stays crisp (no blur), edges get smoother steps ('etwas bessere Aufloesung').
Used by the projection recipes (remake/recipes/massan_house_proj.py): the original pixels 1:1 on 3D geometry."""
import os, struct, sys, zlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "tools"))
import romrender

def png(path, w, h, data, ch):
    raw = b''.join(b'\x00' + bytes(data[y * w * ch:(y + 1) * w * ch]) for y in range(h))
    def c(t, d): x = struct.pack('>I', len(d)) + t + d; return x + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + c(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6 if ch == 4 else 2, 0, 0, 0)) + c(b'IDAT', zlib.compress(raw, 6)) + c(b'IEND', b''))

def layer_a(pa, getpal, tiles, x0, y0, w, h):
    tp = romrender.tile_cache(tiles); out = bytearray(w * h * 4)
    for y in range(h):
        for x in range(w):
            X, Y = x0 + x, y0 + y; t = pa.t.get((X // 8, Y // 8))
            if not t: continue
            i = tp(t[0], t[3], t[4])[Y % 8][X % 8]
            if not i: continue
            o = (y * w + x) * 4; out[o:o + 3] = bytes(getpal(t[1], i)); out[o + 3] = 255
    return out

def scale2x(w, h, px, ch):
    """EPX / Scale2x: every pixel becomes 2 x 2; a corner takes the neighbour colour where two neighbours agree (no new colours, no blur)."""
    W = 2 * w; out = bytearray(W * 2 * h * ch)
    P = lambda x, y: bytes(px[(min(max(y, 0), h - 1) * w + min(max(x, 0), w - 1)) * ch:(min(max(y, 0), h - 1) * w + min(max(x, 0), w - 1)) * ch + ch])
    for y in range(h):
        for x in range(w):
            p, a, b, c, d = P(x, y), P(x, y - 1), P(x + 1, y), P(x - 1, y), P(x, y + 1)
            e0 = a if (c == a and c != d and a != b) else p; e1 = b if (a == b and a != c and b != d) else p
            e2 = c if (d == c and d != b and c != a) else p; e3 = d if (b == d and b != a and d != c) else p
            for (dx, dy), e in (((0, 0), e0), ((1, 0), e1), ((0, 1), e2), ((1, 1), e3)):
                o = ((2 * y + dy) * W + 2 * x + dx) * ch; out[o:o + ch] = e
    return out

if __name__ == '__main__':
    a = [s for s in sys.argv[1:] if not s.startswith('--')]; s2 = '--scale2x' in sys.argv
    rom = open(a[0], 'rb').read(); room = int(a[1]); u0, v0, w, h = map(int, a[2:6]); od = a[6]; os.makedirs(od, exist_ok=True)
    print('room %d: window U %d..%d V %d..%d' % (room, u0, u0 + w, v0, v0 + h), flush=True)
    g, r, pa, pb, getpal = romrender.rom_planes(rom, room)
    A = layer_a(pa, getpal, g['tiles'], u0, v0, w, h)
    F = romrender.compose(pa, pb, getpal, u0, v0, w, h, romrender.md_to_rgb(0), g['tiles'])
    k = 1
    if s2: A = scale2x(w, h, A, 4); F = scale2x(w, h, F, 3); k = 2
    png(os.path.join(od, 'layerA.png'), w * k, h * k, A, 4); png(os.path.join(od, 'full.png'), w * k, h * k, F, 3)
    open(os.path.join(od, 'window.txt'), 'w').write('%d %d %d %d %d\n' % (u0, v0, w, h, k))
    print('written to', od, '(scale %d)' % k)
