#!/bin/bash
# ROM-free test of tools/shot_core.c: compile, write PNGs, decode them with Python (zlib + CRC check) and compare with the expected pixels.
set -eu
cd "$(dirname "$0")"
OUT="${1:-$(mktemp -d)}"; mkdir -p "$OUT"
gcc -O1 -Wall -o "$OUT/shottest" main.c
"$OUT/shottest" "$OUT"
python3 -I - "$OUT" <<'PY'
import sys, zlib, struct
out = sys.argv[1]
def dec(path):
    d = open(path, "rb").read(); assert d[:8] == b"\x89PNG\r\n\x1a\n"; i = 8; idat = b""; w = h = 0
    while i < len(d):
        n, = struct.unpack(">I", d[i:i+4]); t = d[i+4:i+8]; body = d[i+8:i+8+n]; crc, = struct.unpack(">I", d[i+8+n:i+12+n])
        assert zlib.crc32(t + body) == crc, "bad CRC in " + t.decode()
        if t == b"IHDR": w, h = struct.unpack(">II", body[:8]); assert body[8:10] == b"\x08\x02"
        if t == b"IDAT": idat += body
        i += 12 + n
    raw = zlib.decompress(idat); assert len(raw) == h * (1 + 3 * w)
    return w, h, [raw[y*(1+3*w)+1:(y+1)*(1+3*w)] for y in range(h)]
w, h, rows = dec(out + "/a.png"); assert (w, h) == (40, 30)
for y in range(30):
    for x in range(40):
        assert tuple(rows[y][3*x:3*x+3]) == ((x*6) & 255, (y*8) & 255, (x ^ y) & 255), (x, y)
w, h, rows = dec(out + "/b.png"); assert (w, h) == (120, 90)
assert tuple(rows[89][357:360]) == ((39*6) & 255, (29*8) & 255, (39 ^ 29) & 255)
w, h, rows = dec(out + "/c.png"); assert (w, h) == (320, 224)
print("shottest: OK (PNG structure, CRC, zlib stream, pixels, scale, multi-block)")
PY
