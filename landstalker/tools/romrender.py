#!/usr/bin/env python3
"""romrender.py ROM ROOM OUT.png [DUMP.bin [NAME]]   -- draws a room from ROM data ONLY (no running game): blocks -> tiles -> pixels with flips, palette and plane priority
(sprites are not drawn). With a RAM dump of the same room it also draws what the VDP planes of that dump show (reference) and reports how many pixels of the 320 x 224 window agree.
Geometry (FORMATS 'Block map'): block (x, y) is 2 x 2 tiles at tile column 2 (x - y) + C and tile row x + y (brick pattern, 16 px steps sideways, 8 px down per diagonal); the FG array sits one block (16 px) further left.
Modules used: romroom.py (map), romgfx.py (tiles, blocks, palette).  Output: PNG written with zlib (no imaging library needed)."""
import struct, sys, zlib
import romroom, romgfx

def png(path, w, h, rgb):
    raw = b''.join(b'\x00' + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    def ch(t, d): c = struct.pack('>I', len(d)) + t + d; return c + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw, 6)) + ch(b'IEND', b''))

def md_to_rgb(c):                                           # Mega Drive colour word 0BBB0GGG0RRR0
    return (((c >> 1) & 7) * 36, ((c >> 5) & 7) * 36, ((c >> 9) & 7) * 36)
def c9_to_rgb(c):                                           # GPGX 9 bit colour (B << 6 | G << 3 | R)
    return ((c & 7) * 36, ((c >> 3) & 7) * 36, ((c >> 6) & 7) * 36)

def tile_pixels(tiles, t, hflip, vflip):
    """8 x 8 colour indices of tile t (4 bpp, high nibble = left pixel)."""
    base = t * 32; rows = []
    for y in range(8):
        sy = 7 - y if vflip else y
        row = []
        for x in range(4):
            b = tiles[base + sy * 4 + x] if base + sy * 4 + x < len(tiles) else 0
            row += [b >> 4, b & 15]
        rows.append(row[::-1] if hflip else row)
    return rows

class Plane:
    """one scroll plane on the 8 x 8 tile grid: dict (tile col, tile row) -> (tile index, palette line, priority, hflip, vflip).
    A block (x, y) of the map occupies 2 x 2 tiles at tile column 2 * (x - y) + C, tile row x + y (a brick pattern: neighbours never overlap)."""
    def __init__(self): self.t = {}
    def put(self, tc, tr, words):
        for k, w in enumerate(words):
            self.t[(tc + (k & 1), tr + (k >> 1))] = (w & 0x7FF, (w >> 13) & 3, (w >> 15) & 1, (w >> 11) & 1, (w >> 12) & 1)

def tile_cache(tiles):
    cache = {}
    def get(t, hf, vf):
        k = (t, hf, vf)
        if k not in cache: cache[k] = tile_pixels(tiles, t, hf, vf)
        return cache[k]
    return get

def compose(pa, pb, getpal, x0, y0, w, h, backdrop, tiles):
    """colour of every pixel of the window: priority order A high, B high, A low, B low, backdrop."""
    out = bytearray(w * h * 3); tp = tile_cache(tiles); idxmap = [0] * (w * h)
    for y in range(h):
        for x in range(w):
            X, Y = x0 + x, y0 + y; tcr = (X // 8, Y // 8); ix, iy = X % 8, Y % 8
            cand = []
            for pl in (pa, pb):
                t = pl.t.get(tcr)
                cand.append((tp(t[0], t[3], t[4])[iy][ix], t[1], t[2]) if t else None)
            a, b = cand
            pick = None
            for p in (a if a and a[2] else None, b if b and b[2] else None, a if a and not a[2] else None, b if b and not b[2] else None):
                if p and p[0]: pick = p; break
            rgb = getpal(pick[1], pick[0]) if pick else backdrop
            o = (y * w + x) * 3; out[o:o + 3] = bytes(rgb)
            if pick: idxmap[y * w + x] = pick[1] * 16 + pick[0]
    compose.idx = idxmap
    return out

def rom_planes(rom, room):
    g = romgfx.room_gfx(rom, room); r = romroom.decode(rom, room); arr = romroom.arrays(r)
    pa, pb = Plane(), Plane()
    for (x, y), v in arr['BG'].items():
        if v & 0x3FF: pb.put(2 * (x - y) + 148, x + y, g['blocks'][v & 0x3FF])
    for (x, y), v in arr['FG'].items():
        if v & 0x3FF: pa.put(2 * (x - y) + 146, x + y, g['blocks'][v & 0x3FF])
    pal0 = [0, 0x0CCC] + g['pal0'] + [0]
    def getpal(line, idx): return md_to_rgb(pal0[idx]) if line == 0 else (255, 0, 255)
    return g, r, pa, pb, getpal

def vdp_window(dump):
    """320 x 224 picture of the two scroll planes of a dump (no sprites), as GPGX would show them."""
    d = open(dump, 'rb').read()
    reg, cram, vs, vram = d[0x10000:0x10020], d[0x10020:0x100A0], d[0x100A0:0x10120], d[0x10120:0x20120]
    VW = lambda a: (vram[a ^ 1] << 8) | vram[(a + 1) ^ 1]
    C = [(cram[2 * i ^ 1] << 8) | cram[(2 * i + 1) ^ 1] for i in range(64)]
    hsb = (reg[13] & 0x3F) << 10; hsA, hsB = VW(hsb), VW(hsb + 2)
    vsA = (vs[0 ^ 1] << 8) | vs[1 ^ 1]; vsB = (vs[2 ^ 1] << 8) | vs[3 ^ 1]
    baseA, baseB = (reg[2] & 0x38) << 10, (reg[4] & 7) << 13
    def pix(base, hs, vsv, sx, sy):
        px = (sx - hs) % 512; py = (sy + vsv) % 256
        w = VW(base + 2 * ((py // 8) * 64 + px // 8)); tx, ty = px % 8, py % 8
        if w & 0x800: tx = 7 - tx
        if w & 0x1000: ty = 7 - ty
        a = (w & 0x7FF) * 32 + ty * 4 + tx // 2; b = vram[a ^ 1]
        idx = (b >> 4) if tx % 2 == 0 else (b & 15)
        return idx, (w >> 13) & 3, (w >> 15) & 1
    out = bytearray(320 * 224 * 3); idxmap = [0] * (320 * 224)
    for sy in range(224):
        for sx in range(320):
            a = pix(baseA, hsA, vsA, sx, sy); b = pix(baseB, hsB, vsB, sx, sy)
            pick = None
            for p in (a if a[2] else None, b if b[2] else None, a if not a[2] else None, b if not b[2] else None):
                if p and p[0]: pick = p; break
            rgb = c9_to_rgb(C[pick[1] * 16 + pick[0]]) if pick else c9_to_rgb(C[0])
            o = (sy * 320 + sx) * 3; out[o:o + 3] = bytes(rgb)
            if pick: idxmap[sy * 320 + sx] = pick[1] * 16 + pick[0]
    vdp_window.idx = idxmap
    cam0 = (lambda a: ((d[(a & 0xFFFF) ^ 1] << 8) | d[((a + 1) & 0xFFFF) ^ 1]))(0xFF1200)
    cam2 = (lambda a: ((d[(a & 0xFFFF) ^ 1] << 8) | d[((a + 1) & 0xFFFF) ^ 1]))(0xFF1202)
    s = lambda v: v - 65536 if v >= 32768 else v
    return out, s(cam0), s(cam2)

if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read(); room = int(sys.argv[2]); outp = sys.argv[3]
    g, r, pa, pb, getpal = rom_planes(rom, room)
    backdrop = md_to_rgb(0)
    if len(sys.argv) > 4:
        ref, cam0, cam2 = vdp_window(sys.argv[4])
        png(outp.replace('.png', '_vdp.png'), 320, 224, ref)
        # predicted window origin in image coordinates: image U = 16 * (x - y + 74), V = 16 * ((x + y) >> 1);  screen = U - 1184 + cam2 - cam0 + 160, V - (cam0 + cam2) // 2 + 104
        px0 = 1184 - (cam2 - cam0 + 160); py0 = (cam0 + cam2) // 2 - 104     # image U = 16 (x - y) + 1184, V = 8 (x + y)
        best = None
        for dy in range(-10, 11):
            for dx in range(-6, 7):
                out = compose(pa, pb, getpal, px0 + dx, py0 + dy, 320, 224, backdrop, g['tiles'])
                same = sum(1 for i in range(0, len(out), 3) if ref[i:i + 3] != b'\x00\x00\x00' and out[i:i + 3] == ref[i:i + 3])
                if best is None or same > best[0]: best = (same, dx, dy, out)
        loaded = sum(1 for i in range(0, len(ref), 3) if ref[i:i + 3] != b'\x00\x00\x00')
        print('window of the VDP planes vs ROM render: %d of %d loaded (non-black) VDP pixels equal (%.1f %%) at offset (%d, %d) from the predicted origin; window %d px, loaded %d px' % (best[0], loaded, 100.0 * best[0] / max(loaded, 1), best[1], best[2], 320 * 224, loaded))
        png(outp, 320, 224, best[3])
    else:
        # whole room: bounding box of the used cells
        cells = list(pb.t) + list(pa.t)
        c0 = min(c for c, rr in cells); c1 = max(c for c, rr in cells); r0 = min(rr for c, rr in cells); r1 = max(rr for c, rr in cells)
        w, h = (c1 - c0 + 1) * 8, (r1 - r0 + 1) * 8
        png(outp, w, h, compose(pa, pb, getpal, c0 * 8, r0 * 8, w, h, backdrop, g['tiles']))
        print('room %d: %d x %d px written to %s' % (room, w, h, outp))
