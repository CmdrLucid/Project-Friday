#!/usr/bin/env python3
"""mktilepack.py DUMPDIR PACKDIR [SCALE=2]  -- turns a tile dump (LANDSTALKER_TILEDUMP=dir: for every tile of known origin `XXXXXX_NNNN.idx` (64 palette indices, 0 = transparent) and `.rgba` (8 x 8 RGBA with the palette of its first use)) into an HD tile pack: `.idx` files are enlarged as INDEX images (drawn through the live palette: fades, flashes and palette animation keep working), `.rgba` only when no `.idx` exists for the optional HD graphics
(`~/.landstalker_hd` = 1, pack folder `~/.landstalker_tilepack` or LANDSTALKER_TILEPACK): every tile is enlarged with Scale2x (EPX) once for SCALE 2, twice for 4 (hard pixel edges stay hard, diagonal
steps are smoothed; alpha is kept).  It is a DEMONSTRATION filter: a tile is processed on its own (no neighbours), so seams at tile borders are possible; the real HD art replaces the files one by one
(same names, 8 * SCALE x 8 * SCALE RGBA = 256 * SCALE^2 bytes, alpha 0 = keep the game's pixel).  No ROM data is stored anywhere but the user's own folders.  usage: mktilepack.py DUMP PACK [2|4]"""
import os, sys

def epx(px, w, h):
    out = [[None] * (2 * w) for _ in range(2 * h)]
    def at(x, y):
        return px[min(max(y, 0), h - 1)][min(max(x, 0), w - 1)]
    for y in range(h):
        for x in range(w):
            p = px[y][x]; a = at(x, y - 1); b = at(x + 1, y); c = at(x - 1, y); d = at(x, y + 1)
            o1 = o2 = o3 = o4 = p
            if c == a and c != d and a != b: o1 = a
            if a == b and a != c and b != d: o2 = b
            if d == c and d != b and c != a: o3 = c
            if b == d and b != a and d != c: o4 = d
            out[2 * y][2 * x], out[2 * y][2 * x + 1], out[2 * y + 1][2 * x], out[2 * y + 1][2 * x + 1] = o1, o2, o3, o4
    return out

def main():
    if len(sys.argv) < 3: print(__doc__); sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]; scale = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    assert scale in (2, 4), "scale 2 or 4"
    os.makedirs(dst, exist_ok=True); n = 0
    for f in sorted(os.listdir(src)):
        if not (f.endswith(".rgba") or f.endswith(".idx")): continue
        if f.endswith(".rgba") and os.path.exists(os.path.join(src, f[:-5] + ".idx")): continue   # the index image is the better source (palette aware)
        d = open(os.path.join(src, f), "rb").read()
        idx = f.endswith(".idx")
        if len(d) != (64 if idx else 256): continue
        px = [[(d[y * 8 + x],) if idx else tuple(d[(y * 8 + x) * 4:(y * 8 + x) * 4 + 4]) for x in range(8)] for y in range(8)]
        w = h = 8
        for _ in range(scale // 2):
            px = epx(px, w, h); w *= 2; h *= 2
        open(os.path.join(dst, f), "wb").write(bytes(c for row in px for p in row for c in p)); n += 1
    print("wrote %d tiles at %dx into %s" % (n, scale, dst))
main()
