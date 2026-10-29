#!/usr/bin/env python3
"""romroom.py ROM ROOM [DUMP.bin]   -- decodes the map data of one room straight from the ROM (own Python port of DecompressMap1 $00CDAE) and, with a RAM dump
of the same room (per-frame dump of `--ram-dump`, layout RAM 64K | regs | CRAM | VSRAM | VRAM), compares it with the arrays the running game holds.
Room table: long at $0A0A00 = table, 8 bytes per room: map data pointer (long), tileset, palette, height limits, music (`LoadRoomParams $002B4E`).
Map stream = bit stream (MSB first): header (left, top, width - 1, 2 * height - 1 bytes of the stage-1 area), 10 + 10 bit counters, eight 12 bit offsets, then the block layers
as a gamma coded skip / reference / literal scheme (stage 1 marks, stage 2 resolves), then byte aligned RLE of the height map (stage 3).
Use it as a module: `import romroom; r = romroom.decode(rom, room)`  (r['left'], r['top'], r['w'], r['h'], r['layers'], r['hm'])."""
import struct, sys

HM_SIZE = [0, 0]

def decompress(rom, a0):
    pos = a0
    st = {'cur': 0, 'n': 0}
    def bit():
        nonlocal pos
        if st['n'] == 0:
            st['cur'] = rom[pos]; pos += 1; st['n'] = 8
        b = (st['cur'] >> 7) & 1
        st['cur'] = (st['cur'] << 1) & 0xFF; st['n'] -= 1
        return b
    def bits(n):
        v = 0
        for _ in range(n): v = (v << 1) | bit()
        return v
    buf = bytearray(0x10000)
    def W(a): return (buf[a] << 8) | buf[a + 1]
    def SW(a, v): buf[a] = (v >> 8) & 0xFF; buf[a + 1] = v & 0xFF
    hdr0, hdr1, hdr2 = bits(8), bits(8), bits(8)
    d4 = (hdr2 + 1) * 2                                  # row stride in bytes
    x = bits(8); d3 = ((x + 1) >> 1) - 1
    buf[0], buf[1], buf[2], buf[3] = hdr0, hdr1, hdr2, d3 & 0xFF
    total = (d3 + 1) * 2 * d4                            # bytes of the stage-1 area (two layers)
    start = 4; a3 = start + total
    v16 = bits(10); v18 = bits(10)
    tab = [bits(12) for _ in range(8)]
    # ---- stage 1: marks
    a2 = start - 2
    while True:
        k = 0
        while not bit(): k += 1
        n = 1 if k == 0 else (1 << k) + bits(k)
        a2 += 2 * n
        if a2 >= a3: break
        if not bit():
            if not bit():
                d1 = 2 if bit() else 0xFFFF
            else:
                d1 = d4 if bit() else 4
        else:
            if not bit():
                d1 = (d4 + 2) if bit() else 2 * d4
            else:
                d1 = tab[bits(3)] * 2
        d1 &= 0xFFFF
        SW(a2, d1)
        if bit():
            d0 = bit() * 2
            a1 = a2
            while True:
                d3_ = d0 + d4
                while True:
                    a1 += d3_
                    if a1 + 1 < len(buf): SW(a1, d1)
                    if not bit(): break
                if not bit(): break
                d0 ^= 2
    # ---- stage 2: resolve
    a2 = start; a4 = v18; a5 = v16
    SW(a3, 0xFFFF)
    mode = None; d2 = 0
    def literal():
        nonlocal a2, a4, a5
        if not bit():                                      # first bit 0
            if not bit():
                d7 = a4; d0 = 0
                while d7:
                    d0 = (d0 << 1) | bit(); d7 >>= 1
                SW(a2, d0)
            else:
                d7 = a5 - v16; d0 = 0
                while d7:
                    d0 = (d0 << 1) | bit(); d7 >>= 1
                SW(a2, (d0 + v16) & 0xFFFF)
        else:
            if bit(): SW(a2, a5 & 0xFFFF); a5 += 1
            else: SW(a2, a4 & 0xFFFF); a4 += 1
        a2 += 2
    while True:
        d0 = W(a2)
        if d0 == 0:
            if mode is None: raise ValueError('empty slot before any command at %d' % a2)
            if mode == 'lit':
                if a3 <= a2: break
                literal()
            else:
                SW(a2, W(a2 + d2)); a2 += 2
            continue
        if d0 & 0x8000:
            mode = 'lit'
            if a3 <= a2: break
            literal()
        else:
            d2 = -d0; mode = 'copy'
            SW(a2, W(a2 + d2)); a2 += 2
    # ---- stage 3: byte aligned RLE of the height map
    a1 = start + 0x5C94; a2 = a1
    d3 = rom[pos]; pos += 1; d3 -= 1; d4 = d3
    d5 = rom[pos]; pos += 1; d5 -= 1
    HM_SIZE[0:2] = [d3 + 1, d5 + 1]                     # width / height of the height map area (cells beyond it are buffer padding, not room)
    done = False
    while not done:
        d0 = (rom[pos] << 8) | rom[pos + 1]; pos += 2
        d2 = 0
        while True:
            b = rom[pos]; pos += 1; d2 += b
            if b != 0xFF: break
        for _ in range(d2 + 1):
            SW(a2, d0); a2 += 2; d4 -= 1
            if d4 < 0:
                a1 += 0x94; a2 = a1; d4 = d3; d5 -= 1
                if d5 < 0: done = True; break
    return buf, pos

def decode(rom, room):
    tab = struct.unpack('>I', rom[0xA0A00:0xA0A04])[0]
    e = rom[tab + 8 * room: tab + 8 * room + 8]
    ptr = struct.unpack('>I', e[:4])[0]
    buf, end = decompress(rom, ptr)
    sg = lambda b: b - 256 if b > 127 else b
    left, top, w, h2 = sg(buf[0]), sg(buf[1]), buf[2] + 1, buf[3] + 1
    n = w * h2                                           # cells per layer? (h2 rows of w words per layer: two layers = 2 * h2 rows)
    return dict(ptr=ptr, end=end, left=left, top=top, w=w, h=h2, buf=buf, hm_w=HM_SIZE[0], hm_h=HM_SIZE[1], tileset=e[4], palette=e[5], height=e[6], music=e[7])

def extract_inplace(buf, left, top, w, h):
    """ExtractMap $002C4A run exactly as the game does it: IN PLACE in the decoder's buffer (stage area at g_ForegroundBlocks $FF7C02, the 74 x 74 arrays are written
    backwards over it), so the cells the expansion overtakes before they are read come out as 0 (rooms 139 / 142 / 632 / 421: part of the top FG row).  Returns
    ({FG}, {BG}) dicts or None when a pointer leaves the model (then the plain placement is used).  Verified against RAM in rooms 139 / 142 / 632 (0 cells differ)."""
    SZ = 0x5590
    mem = bytearray(SZ); mem[:min(len(buf), SZ)] = buf[:SZ]
    bad = [False]
    def rw(a):
        if a < 0 or a + 1 >= SZ: bad[0] = True; return 0
        return (mem[a] << 8) | mem[a + 1]
    def ww(a, v):
        if a < 0 or a + 1 >= SZ: bad[0] = True; return
        mem[a] = (v >> 8) & 255; mem[a + 1] = v & 255
    def run(a0, a1, d0, d1, d2, d3, d5, d7):
        d4 = 0x48 - d1
        if d4 >= 0:
            for _ in range((d4 + 1) * 0x4A): a1 -= 2; ww(a1, 0)
        d6 = 0x48 - d0; d7 -= 1
        for _ in range(d3 + 1):
            if d6 >= 0:
                for _ in range(d6 + 1): a1 -= 2; ww(a1, 0)
            for _ in range(d2 + 1): a0 -= 2; a1 -= 2; ww(a1, rw(a0))
            if d7 >= 0:
                for _ in range(d7 + 1): a1 -= 2; ww(a1, 0)
        if d5 - 1 >= 0:
            for _ in range(d5 * 0x4A): a1 -= 2; ww(a1, 0)
        return a0
    a0 = 4 + 4 * w * h
    args = (left + w - 1, top + h - 1, w - 1, h - 1, top, left)
    a0 = run(a0, SZ, *args); a0 = run(a0, 0x2AC8, *args)
    if bad[0]: return None
    fg = {(x, y): rw(2 * (y * 74 + x)) for y in range(74) for x in range(74)}
    bg = {(x, y): rw(0x2AC8 + 2 * (y * 74 + x)) for y in range(74) for x in range(74)}
    return fg, bg

def arrays(r):
    """the three 74 x 74 arrays as the game builds them (GetTilemap / ExtractMap): FG layer (RAM $FF7C02), BG layer ($FFA6CA), height map ($FFD192); dict of {(x, y): word}."""
    buf, w, h, left, top = r['buf'], r['w'], r['h'], r['left'], r['top']
    Wd = lambda a: (buf[a] << 8) | buf[a + 1]
    out = {'FG': {}, 'BG': {}, 'HM': {}}
    fgb = extract_inplace(buf, left, top, w, h)
    if fgb:
        out['FG'], out['BG'] = fgb
    else:
      for name, base in (('FG', 4), ('BG', 4 + 2 * w * h)):
        for y in range(h):
            for x in range(w):
                v = Wd(base + 2 * (y * w + x))
                xx, yy = x + left, y + top
                if 0 <= xx < 74 and 0 <= yy < 74: out[name][(xx, yy)] = v
    for y in range(74):
        for x in range(74):
            out['HM'][(x, y)] = Wd(4 + 0x5C94 + 148 * y + 2 * x)
    return out

def compare(r, dump):
    ram = open(dump, 'rb').read()[:0x10000]
    RW = lambda a: (ram[(a & 0xFFFF) ^ 1] << 8) | ram[((a + 1) & 0xFFFF) ^ 1]
    arr = arrays(r)
    res = {}
    for name, base in (('FG', 0xFF7C02), ('BG', 0xFFA6CA)):
        same = diff = 0; ex = []
        for y in range(74):
            for x in range(74):
                a = arr[name].get((x, y), 0); b = RW(base + 148 * y + 2 * x)
                if a == b: same += 1
                else:
                    diff += 1
                    if len(ex) < 5: ex.append((x, y, '%04X' % a, '%04X' % b))
        res[name] = (same, diff, ex)
    # height map: try the placement offsets
    best = None
    for dy in range(-30, 31):
        for dx in range(-30, 31):
            m = t = 0
            for (x, y), v in arr['HM'].items():
                if v == 0 or v == 0x4000: continue
                t += 1
                xx, yy = x + dx, y + dy
                if 0 <= xx < 74 and 0 <= yy < 74 and RW(0xFFD192 + 148 * yy + 2 * xx) == v: m += 1
            if t and (best is None or m > best[0]): best = (m, t, dx, dy)
    res['HM'] = best
    return res

if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read(); room = int(sys.argv[2])
    r = decode(rom, room)
    if len(sys.argv) > 3:
        res = compare(r, sys.argv[3])
        for k in ('FG', 'BG'): print('%s layer: %d of 5476 cells equal the RAM array, %d differ  %s' % (k, res[k][0], res[k][1], res[k][2]))
        print('height map (non-void cells matching at the best offset): %s of %s at offset (%s, %s)' % res['HM'])
    print('room %d: map data at $%06X (%d bytes of stream), header left %d top %d w %d h(per layer) %d, tileset %d palette %d' % (room, r['ptr'], r['end'] - r['ptr'], r['left'], r['top'], r['w'], r['h'], r['tileset'], r['palette']))
