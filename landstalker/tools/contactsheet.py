#!/usr/bin/env python3
"""contactsheet.py DIR OUT_PREFIX [per_sheet=6] [cols=2]  -- tiles the PNGs written by LANDSTALKER_SHOT (DIR/shot_*.png) into contact sheets OUT_PREFIX_<n>.png (view them with the Read tool).
Also: contactsheet.py --diff A.png B.png  -> number of differing pixels in the common centre 320 px (use to compare WIDE=0 and WIDE=n runs). Needs only the Python standard library."""
import glob, os, struct, sys, zlib

def dec(p):
    d = open(p, 'rb').read(); i = 8; idat = b''; w = h = 0
    while i < len(d):
        n, = struct.unpack('>I', d[i:i+4]); t = d[i+4:i+8]
        if t == b'IHDR': w, h = struct.unpack('>II', d[i+8:i+16])
        if t == b'IDAT': idat += d[i+8:i+8+n]
        i += 12 + n
    r = zlib.decompress(idat); s = 1 + 3 * w
    return w, h, [r[y*s+1:(y+1)*s] for y in range(h)]

def write(p, w, h, rows):
    def ch(t, b): return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b))
    open(p, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(b''.join(b'\0' + r for r in rows))) + ch(b'IEND', b''))

if len(sys.argv) >= 4 and sys.argv[1] == '--diff':
    wa, h, a = dec(sys.argv[2]); wb, _, b = dec(sys.argv[3]); oa, ob = (wa - 320) // 2, (wb - 320) // 2
    print(sum(1 for y in range(h) for x in range(320) if a[y][3*(x+oa):3*(x+oa)+3] != b[y][3*(x+ob):3*(x+ob)+3]))
    sys.exit(0)
d, out = sys.argv[1], sys.argv[2]
per = int(sys.argv[3]) if len(sys.argv) > 3 else 6; cols = int(sys.argv[4]) if len(sys.argv) > 4 else 2
fs = sorted(glob.glob(d + '/shot_*.png'))
for n in range(0, len(fs), per):
    ims = [dec(f) for f in fs[n:n+per]]; w, h = ims[0][0], ims[0][1]; rows = []
    for r in range(0, len(ims), cols):
        row = ims[r:r+cols]
        for y in range(h): rows.append(b''.join(i[2][y] for i in row) + b'\xff\x00\xff' * (w * (cols - len(row))))
        rows += [b'\xff\x00\xff' * (w * cols)] * 2
    write('%s_%d.png' % (out, n // per), w * cols, len(rows), rows)
    print('%s_%d.png' % (out, n // per), [os.path.basename(f)[5:11] for f in fs[n:n+per]])
