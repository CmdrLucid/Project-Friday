#!/usr/bin/env python3
"""proxy_overlay.py PIC_DIR OBJ OUT.png [SCALE=3] [GROUND_Z=16]
Draws the edges of a light proxy OBJ (GAME coordinates x east, y south, z up; landstalker/data/proxies/*.obj) over a window of the room picture
cut by remake/tools/rom_picture.py (PIC_DIR/full.png + window.txt), so a recipe's measurements can be checked against the original art:
magenta = edges above the ground, cyan = ground edges (z <= GROUND_Z). Projection: U = x - y + 1184, V = (x + y) / 2 - z (docs/FORMATS.md).
Example (room 632, church): python3 remake/tools/rom_picture.py ROM 632 400 360 400 340 /tmp/pic
                            python3 remake/tools/proxy_overlay.py /tmp/pic landstalker/data/proxies/church_632.obj /tmp/ov.png 2
The output is a local check picture (ROM-derived): never commit it."""
import struct, sys, zlib

def read_png(p):
    """8 bit RGB / RGBA PNG with filter 0 (as rom_picture.py writes it) -> w, h, channels, rows"""
    d = open(p, 'rb').read(); i = 8; idat = b''; w = h = ct = 0
    while i < len(d):
        n, = struct.unpack('>I', d[i:i + 4]); t = d[i + 4:i + 8]
        if t == b'IHDR': w, h, _, ct = struct.unpack('>IIBB', d[i + 8:i + 18])
        if t == b'IDAT': idat += d[i + 8:i + 8 + n]
        i += 12 + n
    c = 4 if ct == 6 else 3; r = zlib.decompress(idat); s = 1 + c * w
    return w, h, c, [r[y * s + 1:(y + 1) * s] for y in range(h)]

def write_png(p, w, h, rows):
    def ch(t, b): return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b))
    open(p, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                        + ch(b'IDAT', zlib.compress(b''.join(b'\0' + bytes(r) for r in rows))) + ch(b'IEND', b''))

def main():
    if len(sys.argv) < 4: print(__doc__); sys.exit(1)
    d, obj, out = sys.argv[1:4]; K = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    ZG = float(sys.argv[5]) + .5 if len(sys.argv) > 5 else 16.5   # ground height of the room (cyan edges)
    U0, V0 = map(int, open(d + '/window.txt').read().split()[:2])
    w, h, c, rows = read_png(d + '/full.png')
    img = [bytearray(b''.join(bytes(r[c * (x // K):c * (x // K) + 3]) for x in range(w * K))) for r in rows for _ in range(K)]
    V, F = [], []
    for l in open(obj):
        p = l.split()
        if p and p[0] == 'v': V.append(tuple(map(float, p[1:4])))
        if p and p[0] == 'f': F.append([int(q.split('/')[0]) - 1 for q in p[1:]])
    pr = lambda v: ((v[0] - v[1] + 1184 - U0) * K, ((v[0] + v[1]) / 2 - v[2] - V0) * K)
    edges = {(min(a, b), max(a, b)) for f in F for a, b in zip(f, f[1:] + f[:1])}
    for a, b in edges:
        (x0, y0), (x1, y1) = pr(V[a]), pr(V[b]); n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        col = bytes((0, 255, 255) if V[a][2] <= ZG and V[b][2] <= ZG else (255, 0, 255))
        for i in range(n + 1):
            x, y = int(round(x0 + (x1 - x0) * i / n)), int(round(y0 + (y1 - y0) * i / n))
            if 0 <= x < w * K and 0 <= y < h * K: img[y][3 * x:3 * x + 3] = col
    write_png(out, w * K, h * K, img)
    print("proxy_overlay: %d edges of %s over room picture U %d V %d -> %s" % (len(edges), obj, U0, V0, out))

if __name__ == '__main__':
    main()
