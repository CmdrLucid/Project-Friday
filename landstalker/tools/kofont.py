#!/usr/bin/env python3
"""kofont.py Galmuri11.bdf lang/ko_glyphs.dat -- the Hangul syllables for the language 'Korean' (user 2026-11-13).

Source: the pixel font Galmuri 11 by Lee Minseo (SIL Open Font License 1.1, lang/OFL-Galmuri.txt; https://github.com/quiple/galmuri).
Its Hangul syllables are 11 px high and at most 11 px wide, the same as the capitals of the game's text font (rows 0..10 of the 12 x 15 glyph).
Output: 'KOGL' + u16 count (11172) + for every syllable U+AC00..U+D7A3: 11 big-endian u16 rows (bit $8000 = column 0), baseline = row 10.
tools/langbuild.py builds the glyphs of a Korean language file from it (only the syllables the text uses)."""
import re, struct, sys

def main():
    bdf, out = sys.argv[1], sys.argv[2]
    t = open(bdf, encoding='latin-1').read()
    g = {}
    for m in re.finditer(r'ENCODING (\d+)\n(.*?)ENDCHAR', t, re.S):
        cp = int(m.group(1))
        if not 0xAC00 <= cp <= 0xD7A3: continue
        b = m.group(2)
        w, h, xo, yo = map(int, re.search(r'BBX (-?\d+) (-?\d+) (-?\d+) (-?\d+)', b).groups())
        rows = re.search(r'BITMAP\n(.*)', b, re.S).group(1).split()
        top = 11 - h - yo                                  # row of the glyph's first bitmap row (baseline at row 10: yo = 0 -> bottom row 10)
        r = [0] * 11
        for i, hexrow in enumerate(rows):
            y = top + i
            if not 0 <= y < 11: continue
            v = int(hexrow, 16); n = len(hexrow) * 4
            for x in range(w):
                if v >> (n - 1 - x) & 1 and 0 <= x + xo < 12: r[y] |= 0x8000 >> (x + xo)
        g[cp] = r
    data = b'KOGL' + struct.pack('>H', 11172)
    for cp in range(0xAC00, 0xD7A4): data += b''.join(struct.pack('>H', v) for v in g.get(cp, [0] * 11))
    open(out, 'wb').write(data)
    print('kofont: %d of 11172 syllables -> %s (%d bytes)' % (len(g), out, len(data)))

if __name__ == '__main__':
    main()
