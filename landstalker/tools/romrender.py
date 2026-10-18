#!/usr/bin/env python3
"""romrender.py ROM ROOM OUT.png [DUMP.bin [NAME]]   -- draws a room from ROM data ONLY (no running game): blocks -> tiles -> pixels with flips, palette and plane priority
(sprites are not drawn). With a RAM dump of the same room it also draws what the VDP planes of that dump show (reference) and reports how many pixels of the 320 x 224 window agree.
Geometry (FORMATS 'Block map'): block (x, y) is 2 x 2 tiles at tile column 2 (x - y) + C and tile row x + y (brick pattern, 16 px steps sideways, 8 px down per diagonal); the FG array sits one block (16 px) further left.
Modules used: romroom.py (map), romgfx.py (tiles, blocks, palette).  Output: PNG written with zlib (no imaging library needed)."""
import struct, sys, zlib
import romroom, romgfx, romsprite

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

def compose(pa, pb, getpal, x0, y0, w, h, backdrop, tiles, spr=None, sprpal=None):
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
            sp = spr.get((x, y)) if spr else None          # (palette line * 16 + index, priority, rgb)
            pick = None; rgb = None
            for p in (('S', sp) if sp and sp[1] else None, ('P', a) if a and a[2] else None, ('P', b) if b and b[2] else None, ('S', sp) if sp and not sp[1] else None,
                      ('P', a) if a and not a[2] else None, ('P', b) if b and not b[2] else None):
                if not p: continue
                if p[0] == 'S': rgb = p[1][2]; pick = (p[1][0] & 15, p[1][0] >> 4); break
                if p[1][0]: pick = p[1]; rgb = getpal(pick[1], pick[0]); break
            if rgb is None: rgb = backdrop
            o = (y * w + x) * 3; out[o:o + 3] = bytes(rgb)
            if pick: idxmap[y * w + x] = pick[1] * 16 + pick[0]
    compose.idx = idxmap
    return out

def rom_planes(rom, room, anim=None, lit=False, pal=None):
    """anim: animation frame numbers (one per animated tile group, see romgfx.anim_list) or None for frame 0; lit: lantern lit state of a dark room (LabrynthLitPal)."""
    g = romgfx.room_gfx(rom, room, lit=lit); r = romroom.decode(rom, room); arr = romroom.arrays(r)
    if g['anim']: g['tiles'] = romgfx.apply_anim(g['tiles'], rom, g['anim'], anim if anim is not None else 0)
    pa, pb = Plane(), Plane()
    for (x, y), v in arr['BG'].items():
        if v & 0x3FF: pb.put(2 * (x - y) + 148, x + y, g['blocks'][v & 0x3FF])
    for (x, y), v in arr['FG'].items():
        if v & 0x3FF: pa.put(2 * (x - y) + 146, x + y, g['blocks'][v & 0x3FF])
    pal0 = [0, 0x0CCC] + g['pal0'] + [0]
    def getpal(line, idx):
        if pal: return md_to_rgb(pal[line * 16 + idx])             # all four lines from rom_cram
        return md_to_rgb(pal0[idx]) if line == 0 else (255, 0, 255)
    return g, r, pa, pb, getpal

def dump_anim(dump, groups):
    """animation frame numbers of a RAM dump: state array at $FF1134, 4 bytes per group (delay, frame count, timer, frame); None for a group whose state does not match (not started)."""
    d = open(dump, 'rb').read(0x10000)
    B = lambda a: d[(a & 0xFFFF) ^ 1]
    return [B(0xFF1134 + 4 * k + 3) if (B(0xFF1134 + 4 * k) == g['delay'] and B(0xFF1134 + 4 * k + 1) == g['frames']) else None for k, g in enumerate(groups)]

def rom_cram(rom, dump, room, lit=False):
    """the 64 CRAM colours of the picture built from ROM data and the game state in a dump (equipment, sprite structs): line 0 = room palette (colour 1 = $0CCC, 0 and 15 = 0),
    lines 1..3 = romsprite.sprite_palettes.  Returns MD format words."""
    d = open(dump, 'rb').read(0x10000)
    B = lambda a: d[(a & 0xFFFF) ^ 1]; W = lambda a: (B(a) << 8) | B(a + 1)
    ents = []; a = 0xFF5480
    for _ in range(15):
        if W(a) & 0x8000: break
        ents.append((B(a + 0x3B), W(a + 6))); a += 0x80
    pal = romsprite.sprite_palettes(rom, ents, B(0xFF114E), B(0xFF114F))
    g = romgfx.room_gfx(rom, room, lit=lit)
    for i, a in ((56, 0xFF00E0 + 0x10), (57, 0xFF00E0 + 0x12), (29, 0xFF00A0 + 0x1A), (30, 0xFF00A0 + 0x1C)): pal[i] = W(a)   # projectile colours (LoadProjectilePalette $1AC?: set when an enemy fires): event state, read from the work RAM palette copies
    for l in range(4): pal[16 * l] = 0; pal[16 * l + 1] = 0x0CCC; pal[16 * l + 15] = 0       # InitPalettes $008FCC: colour 0 / 15 black, colour 1 light grey in every line
    for i, c in enumerate(g['pal0']): pal[2 + i] = c
    # fade (FadeToBlack / FadeInFromDarkness, `DarkenPalette $0009CE` / `DarkenColour $0009FC`): the level is game state ($FF0F50 steps) that runs ahead of / behind the palette in CRAM, so it is
    # inferred as the level whose darkened palette equals the game's active palette copy ($FF0ED0, 64 words) best
    act = [W(0xFF0ED0 + 2 * i) for i in range(64)]
    best = None
    for d3 in range(0, 0x1400, 0x200):
        p = [darken(c, d3) for c in pal]; n = sum(1 for i in range(64) if p[i] != act[i])
        if best is None or n < best[0]: best = (n, p)
    return best[1]

def darken(c, d3, d7=0):
    """one colour darkened by d3 (blue units of $0200; green d3 >> 4, red d3 >> 8), as `DarkenColour $0009FC`: a channel that wraps below zero becomes d7."""
    b = ((c & 0xE00) - d3) & 0x1E00
    if b >= 0x1000: b = d7
    g3 = d3 >> 4; g = ((c & 0xE0) - g3) & 0x1E0
    if g >= 0x100: g = d7
    r3 = g3 >> 4; r = ((c & 0xE) - r3) & 0x1E
    if r >= 0x10: r = d7
    return b | g | r

def sprite_piece(spr, tiledata, tile0, sx, sy, w, h, pal, prio, hf, vf, C):
    """draw one sprite piece (w x h tiles, column-major tile order, 4 bpp from `tiledata` starting at tile number tile0) into spr {(screen x, y): (pal * 16 + index, priority, rgb)};
    earlier pieces win (lower SAT index = in front)."""
    for px in range(w * 8):
        for py in range(h * 8):
            ox = (w * 8 - 1 - px) if hf else px; oy = (h * 8 - 1 - py) if vf else py
            t = tile0 + (ox // 8) * h + (oy // 8)
            a = t * 32 + (oy % 8) * 4 + (ox % 8) // 2
            b = tiledata[a] if a < len(tiledata) else 0
            idx = (b >> 4) if (ox % 8) % 2 == 0 else (b & 15)
            if not idx: continue
            X, Y = sx + px, sy + py
            if 0 <= X < 320 and 0 <= Y < 224 and (X, Y) not in spr: spr[(X, Y)] = (pal * 16 + idx, prio, c9_to_rgb(C[pal * 16 + idx]))

def vdp_sprites(dump):
    """the VDP sprite layer of a dump (sprite attribute table in VRAM at reg 5 * $200, linked list), screen coordinates."""
    d = open(dump, 'rb').read()
    reg, cram, vram = d[0x10000:0x10020], d[0x10020:0x100A0], d[0x10120:0x20120]
    VW = lambda a: (vram[a ^ 1] << 8) | vram[(a + 1) ^ 1]
    C = [(cram[2 * i ^ 1] << 8) | cram[(2 * i + 1) ^ 1] for i in range(64)]
    base = (reg[5] & 0x7F) << 9; spr = {}; i = 0; n = 0
    vt = bytes(vram[k ^ 1] for k in range(0x10000))
    while n < 80:
        a = base + 8 * i; y = VW(a) & 0x3FF; sz = VW(a + 2); at = VW(a + 4); x = VW(a + 6) & 0x1FF
        sprite_piece(spr, vt, at & 0x7FF, x - 128, y - 128, ((sz >> 10) & 3) + 1, ((sz >> 8) & 3) + 1, (at >> 13) & 3, at >> 15, (at >> 11) & 1, (at >> 12) & 1, C)
        i = sz & 0x7F; n += 1
        if i == 0: break
    return spr, C

def rom_sprites(rom, dump, pal=None):
    """the sprites of the entities of a RAM dump drawn from ROM data only (frame pieces and tile graphics decoded by romsprite.py; entity state, palette lines of CRAM)."""
    d = open(dump, 'rb').read(); r = d[:0x10000]; cram = d[0x10020:0x100A0]
    B = lambda a: r[(a & 0xFFFF) ^ 1]; W = lambda a: (B(a) << 8) | B(a + 1)
    C = [(cram[2 * i ^ 1] << 8) | cram[(2 * i + 1) ^ 1] for i in range(64)]
    if pal: C = [((c >> 9) & 7) << 6 | ((c >> 5) & 7) << 3 | ((c >> 1) & 7) for c in pal]   # colours from rom_cram instead of the dump's CRAM
    spr = {}; a = 0xFF11DE
    while True:
        o = W(a); a += 2
        if o & 0x8000 or a > 0xFF11DE + 40: break
        b = 0xFF5400 + o
        ax, ay, ts = W(b + 0x0E), W(b + 0x10), W(b + 6)
        if ax == 0 and ay == 0: continue
        f = romsprite.frame(rom, B(b + 0x0B), W(b + 0x24), W(b + 0x26))
        hf = (ts >> 11) & 1; cum = 0
        for k, (px, py, w, h) in enumerate(f['pieces']):
            x = (-px - 8 * w) if hf else px
            prio = W(0xFF1400 + (o >> 1) + 4) >> 15   # the game's depth test against the scenery (sub_44C4) leaves bit 15 in the tile word of the FIRST piece record of the entity; BuildEntitySpriteEntries gives it to all pieces
            sprite_piece(spr, f['tiles'], cum, ax + x - 128, ay + py - 128, w, h, (ts >> 13) & 3, prio, hf, (ts >> 12) & 1, C)
            cum += w * h
    return spr

def vdp_window(dump, sprites=False):
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
    spr = vdp_sprites(dump)[0] if sprites else {}
    for sy in range(224):
        for sx in range(320):
            a = pix(baseA, hsA, vsA, sx, sy); b = pix(baseB, hsB, vsB, sx, sy)
            sp = spr.get((sx, sy)); pick = None; rgb = None
            for p in (('S', sp) if sp and sp[1] else None, ('P', a) if a[2] else None, ('P', b) if b[2] else None, ('S', sp) if sp and not sp[1] else None,
                      ('P', a) if not a[2] else None, ('P', b) if not b[2] else None):
                if not p: continue
                if p[0] == 'S': pick = (p[1][0] & 15, p[1][0] >> 4); rgb = p[1][2]; break
                if p[1][0]: pick = p[1]; rgb = c9_to_rgb(C[pick[1] * 16 + pick[0]]); break
            if rgb is None: rgb = c9_to_rgb(C[0])
            o = (sy * 320 + sx) * 3; out[o:o + 3] = bytes(rgb)
            if pick: idxmap[sy * 320 + sx] = pick[1] * 16 + pick[0]
    vdp_window.idx = idxmap
    cam0 = (lambda a: ((d[(a & 0xFFFF) ^ 1] << 8) | d[((a + 1) & 0xFFFF) ^ 1]))(0xFF1200)
    cam2 = (lambda a: ((d[(a & 0xFFFF) ^ 1] << 8) | d[((a + 1) & 0xFFFF) ^ 1]))(0xFF1202)
    s = lambda v: v - 65536 if v >= 32768 else v
    return out, s(cam0), s(cam2)

if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read(); room = int(sys.argv[2]); outp = sys.argv[3]
    backdrop = md_to_rgb(0)
    if len(sys.argv) > 4:
        g0 = romgfx.room_gfx(rom, room)
        cr = rom_cram(rom, sys.argv[4], room)
        g, r, pa, pb, getpal = rom_planes(rom, room, anim=dump_anim(sys.argv[4], g0['anim']), pal=cr)
        ref0, cam0, cam2 = vdp_window(sys.argv[4])               # planes only: the offset search needs no sprites (fast)
        ref, _, _ = vdp_window(sys.argv[4], sprites=True)
        spr = rom_sprites(rom, sys.argv[4], pal=cr)
        png(outp.replace('.png', '_vdp.png'), 320, 224, ref)
        # predicted window origin in image coordinates: image U = 16 * (x - y + 74), V = 16 * ((x + y) >> 1);  screen = U - 1184 + cam2 - cam0 + 160, V - (cam0 + cam2) // 2 + 104
        px0 = 1184 - (cam2 - cam0 + 160); py0 = (cam0 + cam2) // 2 - 104     # image U = 16 (x - y) + 1184, V = 8 (x + y)
        best = None
        for dy in range(-10, 11):
            for dx in range(-6, 7):
                out = compose(pa, pb, getpal, px0 + dx, py0 + dy, 320, 224, backdrop, g['tiles'])
                same = sum(1 for i in range(0, len(out), 3) if ref0[i:i + 3] != b'\x00\x00\x00' and out[i:i + 3] == ref0[i:i + 3])
                if best is None or same > best[0]: best = (same, dx, dy)
        out = compose(pa, pb, getpal, px0 + best[1], py0 + best[2], 320, 224, backdrop, g['tiles'], spr)
        same = sum(1 for i in range(0, len(out), 3) if ref[i:i + 3] != b'\x00\x00\x00' and out[i:i + 3] == ref[i:i + 3])
        best = (same, best[1], best[2], out)
        loaded = sum(1 for i in range(0, len(ref), 3) if ref[i:i + 3] != b'\x00\x00\x00')
        print('window of the VDP planes vs ROM render: %d of %d loaded (non-black) VDP pixels equal (%.1f %%) at offset (%d, %d) from the predicted origin; window %d px, loaded %d px' % (best[0], loaded, 100.0 * best[0] / max(loaded, 1), best[1], best[2], 320 * 224, loaded))
        png(outp, 320, 224, best[3])
    else:
        g, r, pa, pb, getpal = rom_planes(rom, room)
        # whole room: bounding box of the used cells
        cells = list(pb.t) + list(pa.t)
        c0 = min(c for c, rr in cells); c1 = max(c for c, rr in cells); r0 = min(rr for c, rr in cells); r1 = max(rr for c, rr in cells)
        w, h = (c1 - c0 + 1) * 8, (r1 - r0 + 1) * 8
        png(outp, w, h, compose(pa, pb, getpal, c0 * 8, r0 * 8, w, h, backdrop, g['tiles']))
        print('room %d: %d x %d px written to %s' % (room, w, h, outp))
