#!/usr/bin/env python3
"""uiwide.py: our own UI text (options pages, help lines, bar words) in Korean / Japanese (release 2.0, LK_UIWIDE v1).
The UI text block of a language file holds byte strings (tools/langbuild.py 'ui_text'): ASCII = the game's menu / text font as before; a
character outside ASCII becomes a 2-byte ESCAPE: lead byte 1 + (gi >> 7) (1..8), then $80 | (gi & $7F)  (never 0, so the C side keeps
using strlen / snprintf).  gi indexes the glyph table appended to the file:
    'UIWG' + u16 n + n * (u16 text font code, u8 advance px, 8 bytes 8x8 menu tile rows, bit $80 = column 0)
    footer at the very end of the file: 'UIW1' + u32 offset of 'UIWG' + 'UIW1'
The text font code is the glyph code of the language's own text font (ProcessChar: help line, bar words, file select window); the 8x8 rows
are drawn as virtual tiles by the own renderer on the option rows (tools/patch_uiwide.py).  Galmuri 7 (SIL OFL, lang/OFL-Galmuri.txt):
lang/ko_glyphs7.dat (Hangul), lang/ja_glyphs7.dat (kana, tools/kofont.py --menu-ja).  Library only."""
import os, re, struct

HERE = os.path.dirname(os.path.abspath(__file__))
LANG = os.path.join(HERE, "..", "lang")


def glyph8(ch):
    """8x8 rows of a Hangul syllable / kana from Galmuri 7 (row 0 free like the menu letters), None if the font has none"""
    cp = ord(ch)
    if 0xAC00 <= cp <= 0xD7A3:
        d = open(os.path.join(LANG, "ko_glyphs7.dat"), "rb").read(); k = cp - 0xAC00
        return bytes([0]) + d[6 + 7 * k:13 + 7 * k]
    if 0x3040 <= cp <= 0x30FF:
        d = open(os.path.join(LANG, "ja_glyphs7.dat"), "rb").read(); k = cp - 0x3040
        r = d[8 + 7 * k:15 + 7 * k]
        return bytes([0]) + r if any(r) else None
    return None


def build(ui_text, code_of, adv_of):
    """ui_text {English: translation} -> ([(key bytes, value bytes)], trailer bytes incl. footer); code_of(ch) / adv_of(ch) = text font code /
    advance of a non-ASCII character (None = not in the font: the entry stays English).  Entries with printf fields (%) stay English."""
    gl, gi, texts, skipped = [], {}, [], []
    for k, v in ui_text.items():
        if "%" in v or "%" in k: skipped.append(k); continue
        out = bytearray(); ok = True
        for ch in v:
            if ord(ch) < 0x80: out.append(ord(ch)); continue
            if ch not in gi:
                g8, c, a = glyph8(ch), code_of(ch), adv_of(ch)
                if g8 is None or c is None: ok = False; break
                gi[ch] = len(gl); gl.append((c, a, g8))
            i = gi[ch]; out += bytes([1 + (i >> 7), 0x80 | (i & 0x7F)])
        if not ok or len(out) > 255 or len(k) > 255: skipped.append(k); continue
        texts.append((k.encode("ascii"), bytes(out)))
    assert len(gl) <= 1024, "uiwide: more than 1024 glyphs"
    tr = b"UIWG" + struct.pack(">H", len(gl)) + b"".join(struct.pack(">HB", c, max(0, min(255, a))) + g8 for c, a, g8 in gl)
    return texts, tr, skipped


def footer(offset):
    return b"UIW1" + struct.pack(">I", offset) + b"UIW1"
