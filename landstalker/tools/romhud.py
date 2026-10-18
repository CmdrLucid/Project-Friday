#!/usr/bin/env python3
"""romhud.py -- HUD (window plane rows 0..2) and text box (rows 20..27) of a RAM dump.
  vdp_rows(dump, rows)   reference: the window plane as the VDP holds it (nametable $F000 + tiles of VRAM)
  The game keeps the window plane tilemap in RAM too: g_HUD_Row1..3 $FF1C00 / $FF1C80 / $FF1D00 (rows 0..2), g_TextBoxLine1..8 $FF2600 + $80 * n (rows 20..27), 64 words per row."""
import sys
import romrender as R, romgfx

STATUS_BAR_GFX = 0x9242        # StatusBarGfx: LZ77, 76 tiles, loaded to VRAM $D680 = tile $6B4 (`LoadStatusBarGfx $008F34`)
HUD_TILE0 = 0x6B4
TEXT_TILE0 = 0x528            # VRAM $A500: DMA copy of the text tile buffer g_TextTiles $FF3900

def window_vdp(dump, rows):
    """{row: 40 x 8 px picture as list of (rgb)} of the given nametable rows from VRAM (reference)."""
    d = open(dump, 'rb').read(); cram = d[0x10020:0x100A0]; vram = d[0x10120:0x20120]
    VW = lambda a: (vram[a ^ 1] << 8) | vram[(a + 1) ^ 1]
    C = [(cram[2 * i ^ 1] << 8) | cram[(2 * i + 1) ^ 1] for i in range(64)]
    out = {}
    for r in rows:
        img = [[(0, 0, 0)] * 320 for _ in range(8)]
        for c in range(40):
            w = VW(0xF000 + 0x80 * r + 2 * c)
            for y in range(8):
                for x in range(8):
                    tx, ty = (7 - x if w & 0x800 else x), (7 - y if w & 0x1000 else y)
                    b = vram[((w & 0x7FF) * 32 + ty * 4 + tx // 2) ^ 1]
                    idx = (b >> 4) if tx % 2 == 0 else (b & 15)
                    img[y][c * 8 + x] = R.c9_to_rgb(C[((w >> 13) & 3) * 16 + idx]) if idx else R.c9_to_rgb(C[0])
        out[r] = img
    return out

def ram_window(rom, dump, rows, pal, text_tiles=None, words=None, textbuf=None):
    """the same rows built without the VDP: tilemap words from the RAM buffers (g_HUD_Row1..3 $FF1C00, g_TextBoxLine1..8 $FF2600; row r >= 20 -> $FF2600 + $80 (r - 20)),
    HUD tile graphics from the ROM (StatusBarGfx), colours from `pal` (64 MD words, romrender.rom_cram); text tiles from `text_tiles` {tile number: 32 bytes} (not yet: blank)."""
    d = open(dump, 'rb').read(0x10000)
    W = lambda a: (d[(a & 0xFFFF) ^ 1] << 8) | d[((a + 1) & 0xFFFF) ^ 1]
    hud, _ = romgfx.lz77(rom, STATUS_BAR_GFX)
    tiles = {HUD_TILE0 + i: hud[32 * i:32 * i + 32] for i in range(len(hud) // 32)}
    # text box tiles: VRAM $A500 (tile $528) is a DMA copy of the text tile buffer $FF3900 (see FORMATS 'text box'), 0x0D80 words at most
    class TextTiles(dict):
        def get(self, k, default=None):
            if k in self: return self[k]
            if k >= TEXT_TILE0 and k < TEXT_TILE0 + 0xD8:
                o = 32 * (k - TEXT_TILE0)
                if textbuf is not None: return bytes(textbuf[o:o + 32])               # buffer built by romtext.text_buffer instead of the game's
                o += 0xFF3900; return bytes(d[((o + i) & 0xFFFF) ^ 1] for i in range(32))
            return default
    tiles = TextTiles(tiles)
    out = {}
    for r in rows:
        base = 0xFF1C00 + 0x80 * r if r < 3 else 0xFF2600 + 0x80 * (r - 20)
        img = [[(0, 0, 0)] * 320 for _ in range(8)]
        for c in range(40):
            w = words[r][c] if words and r in words else W(base + 2 * c); t = tiles.get(w & 0x7FF, bytes(32))
            for y in range(8):
                for x in range(8):
                    tx, ty = (7 - x if w & 0x800 else x), (7 - y if w & 0x1000 else y)
                    b = t[ty * 4 + tx // 2]; idx = (b >> 4) if tx % 2 == 0 else (b & 15)
                    img[y][c * 8 + x] = R.md_to_rgb(pal[((w >> 13) & 3) * 16 + idx]) if idx else R.md_to_rgb(pal[0])
        out[r] = img
    return out

def diff(a, b):
    """number of differing pixels between two {row: image} dicts."""
    return sum(1 for r in a for y in range(8) for x in range(320) if a[r][y][x] != b[r][y][x])

def save(path, rowimgs):
    h = sum(len(v) for v in rowimgs); buf = bytearray()
    for im in rowimgs:
        for line in im:
            for px in line: buf += bytes(px)
    R.png(path, 320, h, buf)

if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read(); dump, outp = sys.argv[2], sys.argv[3]
    rows = [0, 1, 2] + list(range(20, 28))
    ref = window_vdp(dump, rows)
    d = open(dump, 'rb').read(0x10000); room = (d[0xFF1204 & 0xFFFF ^ 1] << 8) | d[0xFF1205 & 0xFFFF ^ 1]
    mine = ram_window(rom, dump, rows, R.rom_cram(rom, dump, room))
    print('HUD rows 0..2: %d of %d pixels differ; text box rows 20..27: %d of %d' % (diff({r: ref[r] for r in (0, 1, 2)}, {r: mine[r] for r in (0, 1, 2)}), 3 * 8 * 320, diff({r: ref[r] for r in range(20, 28)}, {r: mine[r] for r in range(20, 28)}), 8 * 8 * 320))
    save(outp, [mine[r] for r in sorted(mine)])
