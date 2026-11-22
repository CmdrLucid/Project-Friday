#!/usr/bin/env python3
"""cyrfont.py Galmuri11.bdf PublicPixel.ttf  -- the Cyrillic glyphs for Russian / Ukrainian (LK_LGCYR v1, user 2026-11-22: Galmuri 11 for the
dialogue font, the Public Pixel font for the 8x8 menu tiles: two fonts like the original game, thin tall text + bold 8x8 menu).
Sources: Galmuri 11 by Lee Minseo (SIL Open Font License 1.1, lang/OFL-Galmuri.txt; https://github.com/quiple/galmuri) and Public Pixel by
GGBotNet (CC0 1.0, lang/CC0-PublicPixel.txt; https://ggbot.itch.io/public-pixel-font).
Output (both for U+0400..U+04FF, 256 entries; an entry without a glyph is all zero):
  lang/cyr_glyphs.dat  = 'CYGL' + u16 first code point + u16 count + per glyph 15 big-endian u16 rows of the 12 x 15 text font cell
                          (bit $8000 = column 0, capitals rows 0..10 like the game font, baseline row 10, descenders rows 11..12;
                          capitals with marks taller than the line (Ї Ґ Й Ё) lose a repeated middle row, like the derived Ä / É)
  lang/cyr_glyphs7.dat = 'CYG7' + u16 first + u16 count + per glyph 8 bytes (8x8 menu tile rows, bit $80 = column 0; row 0 free like the
                          game's menu letters)
Needs PIL for the .ttf (run once on the developer machine; the .dat files are shipped)."""
import re, struct, sys, os

FIRST, COUNT = 0x400, 0x100
HERE = os.path.dirname(os.path.abspath(__file__)); LANG = os.path.join(HERE, "..", "lang")


def text_glyphs(bdf):
    t = open(bdf, encoding="latin-1").read(); out = {}
    for m in re.finditer(r"ENCODING (\d+)\n(.*?)ENDCHAR", t, re.S):
        cp = int(m.group(1))
        if not FIRST <= cp < FIRST + COUNT: continue
        b = m.group(2); w, h, xo, yo = map(int, re.search(r"BBX (-?\d+) (-?\d+) (-?\d+) (-?\d+)", b).groups())
        rows = re.search(r"BITMAP\n(.*)", b, re.S).group(1).split(); top = 10 - (h + yo) + 1
        while top < 0:   # taller than the line: drop a row that repeats the next one, from the middle first
            k = next((i for i in range(len(rows) // 2, len(rows) - 1) if rows[i] == rows[i + 1]), None)
            if k is None: k = next((i for i in range(1, len(rows) - 1) if rows[i] == rows[i + 1]), len(rows) // 2)
            rows.pop(k); top += 1
        g = [0] * 15
        for i, hx in enumerate(rows):
            y = top + i; v = int(hx, 16); n = len(hx) * 4
            if 0 <= y < 15:
                for x in range(w):
                    if v >> (n - 1 - x) & 1 and 0 <= x + xo < 12: g[y] |= 0x8000 >> (x + xo)
        out[cp] = g
    return out


def menu_glyphs(ttf):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(ttf, 8); out = {}
    for cp in range(FIRST, FIRST + COUNT):
        ch = chr(cp)
        if f.getmask(ch).getbbox() is None: continue
        g = Image.new("1", (8, 8), 0); ImageDraw.Draw(g).text((0, 0), ch, font=f, fill=1)
        out[cp] = bytes(sum(0x80 >> x for x in range(8) if g.getpixel((x, y))) for y in range(8))
    return out


def main():
    tg = text_glyphs(sys.argv[1]); mg = menu_glyphs(sys.argv[2])
    a = b"CYGL" + struct.pack(">HH", FIRST, COUNT) + b"".join(struct.pack(">15H", *tg.get(cp, [0] * 15)) for cp in range(FIRST, FIRST + COUNT))
    b = b"CYG7" + struct.pack(">HH", FIRST, COUNT) + b"".join(mg.get(cp, bytes(8)) for cp in range(FIRST, FIRST + COUNT))
    open(os.path.join(LANG, "cyr_glyphs.dat"), "wb").write(a); open(os.path.join(LANG, "cyr_glyphs7.dat"), "wb").write(b)
    print("cyrfont: %d text glyphs, %d menu glyphs -> lang/cyr_glyphs.dat (%d bytes), lang/cyr_glyphs7.dat (%d bytes)" % (len(tg), len(mg), len(a), len(b)))


if __name__ == "__main__":
    main()
