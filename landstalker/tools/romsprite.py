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

SPRITE_PAL_LUT = 0x1A453A       # SpritePaletteLUT: byte pairs (sprite type, value), $FF ends; value bit 7 = 'high' palette (7 colours), low 7 bits = index
SPRITE_PAL_LO = 0x1A47E0        # SpritePaletteLo: 80 entries of 6 colours (12 bytes)
SPRITE_PAL_HI = 0x1A4BA0        # SpritePaletteHi: entries of 7 colours (14 bytes) = SPRITE_PAL_LO + 80 * 12
DEFAULT_PLAYER_PAL = 0x901C     # DefaultPlayerPal: 16 words = palette line 2 (`LoadPlayerPalette $008FB4`)
STATUS_BAR_PAL = 0x903C         # StatusBarPal: 5 words -> line 3 colours 10..14 (`InitPalettes $008FCC`)
SWORD_SWAP_IDX, SWORD_SWAPS = 0x78F4, 0x7900      # UpdateEquipPal $0078B6: item id list (6 bytes), 4 byte entries -> line 2 colours 13, 14
ARMOUR_SWAP_IDX, ARMOUR_SWAPS = 0x78FA, 0x7918    # -> line 2 colours 11, 12

def sprite_palettes(rom, entities, sword, armour):
    """the 64 CRAM colours (MD format 0BBB0GGG0RRR0) of lines 1..3 as the game builds them (`InitSpritePalettes $1A4422`, `GetSpritePalette $1A4468`, `LoadPlayerPalette`, `InitPalettes`).
    entities = [(sprite type, TileSource word)] of the sprite structs in order; returns a list of 64 words, line 0 left 0 (it is the room palette, see romgfx.room_gfx)."""
    W = lambda a: struct.unpack('>H', rom[a:a + 2])[0]
    pal = [0] * 64
    for i in range(16): pal[32 + i] = W(DEFAULT_PLAYER_PAL + 2 * i)                       # line 2: Nigel
    for lst, swaps, item, col in ((ARMOUR_SWAP_IDX, ARMOUR_SWAPS, armour, 43), (SWORD_SWAP_IDX, SWORD_SWAPS, sword, 45)):
        k = 0
        while k < 6 and rom[lst + k] != item: k += 1
        k = min(k, 5)
        pal[32 + 11 + (0 if col == 43 else 2)] = W(swaps + 4 * k); pal[32 + 12 + (0 if col == 43 else 2)] = W(swaps + 4 * k + 2)
    for i in range(5): pal[48 + 10 + i] = W(STATUS_BAR_PAL + 2 * i)                       # line 3: HUD colours 10..14
    for typ, ts in entities:
        if not (ts >> 8) & 0x20: continue                                                  # palette 1 or 3 only (bit 13 of the tile word)
        a = SPRITE_PAL_LUT
        while rom[a] != 0xFF:
            if rom[a] == typ:
                v = rom[a + 1]; hi = v & 0x80; idx = v & 0x7F; pal3 = (ts >> 8) & 0x40
                if hi:
                    if pal3: pass                                                          # palette 3 high does not exist (the game beeps)
                    else:
                        for j in range(7): pal[16 + 8 + j] = W(SPRITE_PAL_HI + 14 * idx + 2 * j)
                else:
                    base = 48 + 2 if pal3 else 16 + 2
                    for j in range(6): pal[base + j] = W(SPRITE_PAL_LO + 12 * idx + 2 * j)
            a += 2
    return pal

if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    f = frame(rom, int(sys.argv[2], 0), int(sys.argv[3], 0), int(sys.argv[4], 0))
    print('pieces', f['pieces'], 'tiles', len(f['tiles']) // 32, 'needed by pieces', f['ntiles'], 'declared per sprite', f['declared'])
