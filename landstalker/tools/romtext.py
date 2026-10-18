#!/usr/bin/env python3
"""romtext.py -- the text box font printed from the ROM (own Python port of `PrintCharDirect $0235FE` / `PrintChar $023640` with `sub_2371A`, `sub_237AC`, `sub_23702`, `sub_236CC`).
The game prints into the text tile buffer `g_ScreenBuffer $FF3900` (4 bpp tiles, 8 px columns of two tiles = 64 bytes, text line stride $900), which is DMA copied to VRAM tile $528.
Font `MainFont $02A884` (long at `MainFontPtr $022E84`): 30 bytes per character code = 15 rows of one word; the 12 high bits of a row word are the pixels.
Each pixel is stored as a byte (colour << 4 | $A: the pixel on the left, shadow colour $A on its right); the bytes are merged into the buffer at nibble position (x & 7) + k
(even position: whole byte, odd position: low nibble).
  print_char(buf, rom, code, x, y, colour) -> new x          buf = bytearray(0x1B00) (the buffer starting at $FF3900)
  print_string(buf, rom, codes, x, y, colour) -> new x"""
import struct

def font_base(rom): return struct.unpack('>I', rom[0x22E84:0x22E88])[0]

def print_char(buf, rom, code, x, y, colour):
    if code == 0: return x + 8
    d6 = 14; back = False
    if code in (0x7B, 0x7C): d6 = 3; back = True
    glyph = font_base(rom) + 30 * code
    d1 = colour; d2 = colour
    if x & 1: d2 = ((d2 << 4) & 0xF0) | 0x0A
    else: d1 = ((d1 << 4) & 0xF0) | 0x0A
    a2 = [0, 0x900, 0x1200][(y & 0x30) >> 4] + (y & 0x0F) * 4 + (x & 0xF8) * 8
    d4 = 0; d5 = y
    for row in range(d6 + 1):
        word = struct.unpack('>H', rom[glyph + 2 * row:glyph + 2 * row + 2])[0]
        ink = bytearray([0xAA, 0x0A] * 6) if not (x & 1) else bytearray([0x0A, 0xAA] * 6)
        if word:
            for k in range(12):
                if word & (0x8000 >> k): ink[k] = d1 if k % 2 == 0 else d2
            for i in range(12):
                d0 = ink[i]
                if d0 in (0x0A, 0xAA): continue
                e = (x & 7) + i; b = e // 2
                off = a2 + (b if b < 4 else 0x40 + b - 4 if b < 8 else 0x80 + b - 8)
                if off >= len(buf): continue
                if e % 2 == 0: buf[off] = d0
                else: buf[off] = (buf[off] & 0xF0) | (d0 & 0x0F)
        # width of this row (sub_236CC): 13 - trailing blank bytes of the ink buffer
        w = 13
        for i in range(11, -1, -1):
            if ink[i] in (0x0A, 0xAA): w -= 1
            else: break
        if d4 < w: d4 = w
        a2 += 4; d5 += 1
        if d5 in (0x10, 0x20): a2 += 0x8C4
    d4 += 1
    x += d4
    if back: x -= 7
    return x

def print_string(buf, rom, codes, x, y, colour):
    for c in codes: x = print_char(buf, rom, c, x, y, colour)
    return x

def encode(text):
    """ASCII text -> game character codes: ' ' 0, digits 1..10, A..Z 11..36, a..z 37..62, '*' 63, '.' 64, ',' 65, '?' 66, '!' 67, ':' 71, '-' 72 (measured by matching glyph pixels with a dump of the text box)."""
    punct = {' ': 0, '*': 63, '.': 64, ',': 65, '?': 66, '!': 67, ':': 71, '-': 72}
    out = []
    for c in text:
        if c in punct: out.append(punct[c])
        elif c.isdigit(): out.append(1 + int(c))
        elif 'A' <= c <= 'Z': out.append(11 + ord(c) - 65)
        elif 'a' <= c <= 'z': out.append(37 + ord(c) - 97)
        else: raise ValueError('no glyph known for %r' % c)
    return out

def text_buffer(rom, lines, colour=0xB, x0=1):
    """the text tile buffer ($FF3900, 0x1B00 bytes, background colour $A) after printing up to three lines (line n at y = 1 + 16 n)."""
    buf = bytearray([0xAA]) * 0x1B00
    for n, t in enumerate(lines[:3]): print_string(buf, rom, encode(t), x0, 1 + 16 * n, colour)
    return buf

def textbox_words():
    """window plane rows 20..27 (40 words each) of an open text box: frame tiles from the status bar graphics ($6B4 ..), text area = tiles $528 + ... in column pairs."""
    rows = []
    for r in range(20, 28):
        row = [0x66B4] * 40
        if r == 20 or r == 27:
            f = 0x0000 if r == 20 else 0x1000
            row[0] = 0x66B4 + f; row[1] = 0x66B5 + f
            for c in range(2, 38): row[c] = 0x66B6 + f
            row[38] = 0x6EB5 + f; row[39] = 0x66B4
        else:
            row[1] = 0x66B7; row[38] = 0x6EB7
            for c in range(2, 38): row[c] = 0x6528 + 0x48 * ((r - 21) // 2) + 2 * (c - 2) + (r - 21) % 2
        rows.append(row)
    return rows
