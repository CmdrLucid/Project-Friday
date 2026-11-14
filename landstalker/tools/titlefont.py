#!/usr/bin/env python3
"""titlefont.py: the title screen subtitle ('THE TREASURES OF KING NOLE') in the other languages (release 2.0, 2026-11-14, user: own lettering = option 2).
OUR OWN pixel lettering in the style of the title (narrow capitals 17 px high, 2 px strokes, three greys in horizontal bands like a metal
bar), drawn here by hand; no picture data of the ROM.  Korean / Japanese characters are Noto Sans CJK KR / JP Bold rendered at 17 px without smoothing (SIL OFL 1.1; 2 px strokes like the
title), shaded the same way; the bitmaps are stored below (KO17 / JA17) so no font file is needed.
render(code) -> list of rows (strings of '.', '#' light, '+' middle, '-' dark), 20 rows high (3 rows above the letters for accents / dots).
tools/patch_titlesub.py turns them into C arrays; `titlefont.py --preview OUT.png TITLE.png` draws all languages over a title screenshot.
Texts: de = the German release's title 'Die Schaetze von Koenig Nolo', fr = the French release's 'Le Tresor du Roi Nole', ko = the King Nole
of lang/ko.json ('노르 왕의 보물', Noto Sans CJK KR Bold 17 px, KO17), ja = the Japanese original's subtitle (皇帝の財宝, 'Koutei no Zaihou', drawn with Noto Sans CJK JP Bold 17 px, SIL OFL, stored below as JA17)."""
import sys

TEXT = {"de": "DIE SCHÄTZE VON KÖNIG NOLO", "fr": "LE TRÉSOR DU ROI NOLE", "ko": "노르 왕의 보물", "ja": "皇帝の財宝"}
H, TOP = 20, 3   # map height, rows above the letter body (accents, umlaut dots)

def _g(top0, top1, up, mid6, mid7, low, bot15, bot16, up2=None, low2=None):
    """17 rows: 0-1 top bar, 2-5 upper part (up2 = rows 4-5 when different), 6-7 middle, 8-14 lower part (low2 = rows 13-14 when different), 15-16 bottom"""
    return [top0, top1, up, up, up2 or up, up2 or up, mid6, mid7] + [low] * 5 + [low2 or low] * 2 + [bot15, bot16]

L = {
    "A": _g(".####.", "######", "##..##", "######", "######", "##..##", "##..##", "##..##"),
    "C": _g(".####.", "######", "##..##", "##....", "##....", "##....", "######", ".####.", up2="##....", low2="##..##"),
    "D": _g("#####.", "######", "##..##", "##..##", "##..##", "##..##", "######", "#####."),
    "E": _g("######", "######", "##....", "#####.", "#####.", "##....", "######", "######"),
    "G": _g(".####.", "######", "##..##", "##.###", "##.###", "##..##", "######", ".####.", up2="##...."),
    "H": _g("##..##", "##..##", "##..##", "######", "######", "##..##", "##..##", "##..##"),
    "I": ["##"] * 17,
    "K": ["##..##"] * 4 + ["##.###", "##.##.", "#####.", "######"] + ["##..##"] * 9,
    "L": ["##...."] * 15 + ["######", "######"],
    "N": ["##..##"] * 3 + ["###.##", "###.##", "######", "######", "######", "##.###", "##.###"] + ["##..##"] * 7,
    "O": _g(".####.", "######", "##..##", "##..##", "##..##", "##..##", "######", ".####."),
    "R": _g("#####.", "######", "##..##", "######", "#####.", "##..##", "##..##", "##..##"),
    "S": [".####.", "######", "##..##", "##..##", "##....", "##....", "######", ".#####"] + ["....##"] * 5 + ["##..##", "##..##", "######", ".####."],
    "T": ["######", "######"] + ["..##.."] * 15,
    "U": ["##..##"] * 15 + ["######", ".####."],
    "V": ["##..##"] * 11 + ["##..##", "##..##", ".####.", ".####.", "..##..", "..##.."],
    "Z": ["######", "######", "....##", "....##", "...##.", "...##.", "..##..", "..##..", ".##...", ".##..."] + ["##...."] * 5 + ["######", "######"],
}
ACC = {"Ä": ("A", ["##..##", "##..##", "......"]), "Ö": ("O", ["##..##", "##..##", "......"]), "É": ("E", ["...##.", "..##..", "......"])}

# Noto Sans CJK JP Bold at 17 px, no smoothing (SIL OFL 1.1; user 2026-11-14: the Galmuri kanji were too small): 17 rows, 2 px strokes already
JA17 = {
"皇": ["......###......", "..############.", "..############.", "..##.......###.", "..############.", "..##.......###.", "..##.......###.", "..############.", "..############.", ".#############.", ".#############.", ".......##......", "..###########..", "..###########..", ".......##......", "###############", "###############"],
"帝": ["......###......", "......###......", ".#############.", ".#############.", "...###....##...", "###############", "###############", "##...........##", "##....##.....##", "..###########..", "..###########..", "..##..##...##..", "..##..##...##..", "..##..##...##..", "..##..##.####..", "..##..##..##...", "......##......."],
"の": ["...............", "...............", ".....######....", "...#########...", "..####.##.###..", ".###..###..###.", ".##...###...##.", "###...##....###", "##....##....###", "##...###....###", "##...##.....###", "###..##.....##.", ".######....###.", ".#####....###..", "..###..#####...", "........###....", "..............."],
"財": ["............##..", "#######.....##..", "#######.....##..", "##...##.....##..", "################", "################", "##...##....###..", "##...##...####..", "#######...####..", "##...##..##.##..", "##...##..##.##..", "#######.##..##..", "##########..##..", ".##.##..#...##..", ".##..##.....##..", "##...##...####..", "#.........###..."],
"宝": ["......###......", "......###......", "###############", "###############", "##...........##", "##...........##", "###############", "..###########..", "......##.......", "......##.......", "..###########..", "..###########..", "......##.###...", "......##...##..", "###############", "###############", "..............."],
}

# Noto Sans CJK KR Bold at 17 px, no smoothing (SIL OFL 1.1): the Korean subtitle the same size as the Japanese (2026-11-14)
KO17 = {
"노": ["..............", ".###..........", ".###..........", ".###..........", ".###..........", ".###..........", ".###..........", ".###########..", ".###########..", "......##......", "......##......", "......##......", "......##......", "##############", "##############", "..............", ".............."],
"르": ["..............", ".###########..", ".###########..", "..........##..", "..........##..", ".###########..", ".###########..", ".###..........", ".###..........", ".############.", ".############.", "..............", "..............", "##############", "##############", "..............", ".............."],
"왕": ["..........##..", "..#####...##..", ".#######..##..", "###...##..##..", ".##...##..####", ".#######..####", "...###....##..", "...###....##..", "#########.##..", "########..##..", "..........##..", "....######....", "..##########..", "..##......##..", "..##......##..", "..##########..", "....######...."],
"의": ["...........##", "...####....##", ".#######...##", ".##...###..##", "###....##..##", "###....##..##", "###....##..##", ".##...###..##", ".#######...##", "...####....##", "...........##", ".........#.##", "##########.##", "#######....##", "...........##", "...........##", "...........##"],
"보": ["..............", ".##.......##..", ".##.......##..", ".##.......##..", ".###########..", ".###########..", ".##.......##..", ".##.......##..", ".###########..", ".###########..", "......##......", "......##......", "......##......", "##############", "##############", "..............", ".............."],
"물": ["..............", ".###########..", ".###########..", ".###......##..", ".###########..", ".###########..", "..............", "##############", "##############", "......##......", ".###########..", ".###########..", ".###########..", ".###########..", ".###..........", ".############.", ".############."],
}

# shade per row 0..16 (measured on the title's letters): first pixel of a stroke / the other pixels; '#' light, '+' middle, '-' dark
BAND = ["##", "##", "#+", "#+", "++", "+-", "+-", "--", "--", "--", "+-", "+-", "++", "#+", "#+", "##", "##"]
def _shade(rows):
    """mask rows (17 high) -> shaded rows"""
    out = []
    for y, r in enumerate(rows):
        out.append("".join("." if c != "#" else BAND[y][0 if x == 0 or r[x - 1] != "#" else 1] for x, c in enumerate(r)))
    return out

def render(code):
    """the subtitle of language code -> H rows of '.', '#', '+', '-'"""
    cols = [[] for _ in range(H)]
    def put(mask, extra=None):
        w = len(mask[0]); sh = _shade(mask)
        for y in range(H):
            if y < TOP: cols[y].append(extra[y] if extra else "." * w)
            else: cols[y].append(sh[y - TOP])
    text = TEXT[code]
    for i, ch in enumerate(text):
        if i and text[i - 1] != " " and ch != " ": [c.append(".") for c in cols]   # 1 px between letters
        if ch == " ": [c.append("......" if any(t in JA17 or t in KO17 for t in text) else "...") for c in cols]; continue   # word gap 3 px (as the title), 6 px between CJK words
        if ch in JA17 or ch in KO17:   # Japanese / Korean (Noto 17 px): 3 px between the characters
            if i and (text[i - 1] in JA17 or text[i - 1] in KO17): [c.append("..") for c in cols]
            put(JA17.get(ch) or KO17[ch]); continue
        if ch in ACC:
            b, top = ACC[ch]; m = L[b]; put(m, [t.replace("#", "#") for t in top]); continue
        put(L[ch])
    return ["".join(c) for c in cols]

COLOURS = {"#": (204, 204, 204), "+": (170, 170, 170), "-": (136, 136, 136)}

def preview(out, title):
    from PIL import Image
    base = Image.open(title).convert("RGB"); W, Ht = base.size
    sheet = Image.new("RGB", (W * 2, Ht * 2))
    for i, code in enumerate(("de", "fr", "ko", "ja")):
        im = base.copy(); px = im.load()
        for y in range(102, 124):
            for x in range(166, 332): px[x, y] = (0, 0, 0)   # the English subtitle away (preview only)
        rows = render(code); w = len(rows[0]); x0, y0 = 326 - w + 1, 105 - TOP
        for y, r in enumerate(rows):
            for x, c in enumerate(r):
                if c in COLOURS: px[x0 + x, y0 + y] = COLOURS[c]
        sheet.paste(im, ((i % 2) * W, (i // 2) * Ht))
    sheet.resize((W * 4, Ht * 4), Image.NEAREST).save(out)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--preview": preview(sys.argv[2], sys.argv[3])
    else:
        for c in TEXT: print(c); print("\n".join(render(c)))
