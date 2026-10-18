#!/usr/bin/env python3
"""romsprite.py -- sprite (figure) frames straight from the ROM (own Python port of LoadSpriteFrame $004230 / LoadObjectVDPSprites $00460C / LoadSpriteTiles $00473E).
  frame(rom, gfx, anim, frm) -> dict(pieces=[(x, y, w, h)], tiles=bytes (4 bpp, 32 bytes per tile, in piece order), ntiles, ptr)
Tables: SpriteGfxPtrPtr $120000: long base, then 4 bytes per sprite graphic id: word animation table offset (in longs from base), word tile count.
animation pointer = long at base + off * 4 + AnimationIndex (entity +24, bytes, steps of 4); frame pointer = long at animation pointer + AnimationFrame (entity +26).
Frame data: 2 bytes per piece (b1, b2): y = signed ((b1 << 1) & $F8), x = signed ((b2 << 1) & $F8) pixels, width code = b1 & 3, height code = b2 & 3 (VDP sprite sizes: n + 1 tiles),
bit 7 of b2 marks the last piece (at most 8); then tile chunks: word (bit 15 zero fill, bit 13 LZ77 compressed (last), bit 14 last chunk, low 12 bits = length in words), raw data follows."""
import struct, sys
import romgfx

def _s8(v): return v - 256 if v > 127 else v

def frame(rom, gfx, anim, frm):
    base = struct.unpack('>I', rom[0x120000:0x120004])[0]
    off, ntile_decl = struct.unpack('>HH', rom[0x120004 + 4 * gfx: 0x120008 + 4 * gfx])
    a = base + off * 4
    ap = struct.unpack('>I', rom[a + anim: a + anim + 4])[0]
    fp = struct.unpack('>I', rom[ap + frm: ap + frm + 4])[0]
    pos = fp; pieces = []
    while True:
        b1, b2 = rom[pos], rom[pos + 1]; pos += 2
        y = _s8((b1 << 1) & 0xF8); x = _s8((b2 << 1) & 0xF8)   # record order of the game is the VDP sprite order: b1 -> y offset + width, b2 -> x offset + height + last flag
        pieces.append((x, y, (b1 & 3) + 1, (b2 & 3) + 1))
        if b2 & 0x80 or len(pieces) >= 8: break
    tiles = bytearray()
    while True:
        h = struct.unpack('>H', rom[pos:pos + 2])[0]; pos += 2
        n = h & 0x0FFF
        if h & 0x8000: tiles += bytes(n * 2)
        elif h & 0x2000:
            data, _ = romgfx.lz77(rom, pos); tiles += data; break
        else: tiles += rom[pos:pos + n * 2]; pos += n * 2
        if h & 0x4000: break
    need = sum(w * hh for _, _, w, hh in pieces)
    return dict(pieces=pieces, tiles=bytes(tiles), ntiles=need, declared=ntile_decl, ptr=fp)

if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    f = frame(rom, int(sys.argv[2], 0), int(sys.argv[3], 0), int(sys.argv[4], 0))
    print('pieces', f['pieces'], 'tiles', len(f['tiles']) // 32, 'needed by pieces', f['ntiles'], 'declared per sprite', f['declared'])
