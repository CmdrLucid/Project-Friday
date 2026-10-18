#!/usr/bin/env python3
"""romgfx.py -- decoders for the graphics data of the Landstalker ROM (own Python ports, checked against the running game, see FORMATS 'Room graphics in the ROM'):
  lz77(rom, ptr)        port of DecompressLZ77Gfx $004AB2: the tile graphics of a tileset (4 bits per pixel, 32 bytes per 8x8 tile)
  bigtiles(rom, ptr)    port of DecompBigTiles $00D09C: block definitions, 4 tile words per block (top left, top right, bottom left, bottom right; VDP name table words)
  room_gfx(rom, room)   everything one room needs: tiles (bytes), blocks (list of 4-word tuples), palette line 0 (13 colours) and the other header fields
Tables: TilesetPointers long at $044010 -> table of pointers (tileset = entry byte & $1F); BigTilesListPtr long at $1AF800 -> table indexed by the entry byte (whole byte): a pointer to a list
[primary blockset, secondary blockset 0, 1, ...] (secondary index = entry byte 7 >> 5); the ids of the primary blockset come first, the secondary ones continue after them; RoomPals $11C926, 26 bytes per palette."""
import struct, sys

def lz77(rom, a0, limit=0x10000):
    out = bytearray(); pos = a0
    while True:
        flags = rom[pos]; pos += 1
        for i in range(8):
            if (flags >> (7 - i)) & 1:                     # literal byte
                out.append(rom[pos]); pos += 1
            else:                                          # match: 12 bit offset, 4 bit length code
                b1 = rom[pos]; b2 = rom[pos + 1]; pos += 2
                off = ((b1 >> 4) << 8) | b2
                if off == 0: return bytes(out), pos
                n = 18 - (b1 & 15)
                src = len(out) - off
                for k in range(n): out.append(out[src + k] if src + k >= 0 else 0)
            if len(out) > limit: return bytes(out), pos

class Bits:
    def __init__(self, rom, pos): self.rom, self.pos, self.cur, self.n = rom, pos, 0, 0
    def bit(self):
        if self.n == 0: self.cur = self.rom[self.pos]; self.pos += 1; self.n = 8
        b = (self.cur >> 7) & 1; self.cur = (self.cur << 1) & 0xFF; self.n -= 1; return b
    def bits(self, k):
        v = 0
        for _ in range(k): v = (v << 1) | self.bit()
        return v

def bigtiles(rom, a0):
    B = Bits(rom, a0)
    count4 = B.bits(16) * 4                                # tile words (4 per block)
    words = [0] * count4
    def run():                                             # sub_D1A4: k zero bits, a one, k bits: 2^k - 1 + value
        k = 0
        while not B.bit(): k += 1
        return 0 if k == 0 else (1 << k) - 1 + B.bits(k)
    # phase 1: alternating runs, bit 15 (priority) set in every second run
    d7 = 0; d3 = 0; pos = 0
    r = run()
    if r == 0: d7 ^= 0x8000; r = run(); n = r + 1
    else: n = r
    while True:
        for _ in range(n):
            if pos < count4: words[pos] = d7
            pos += 1
        d3 += n; d7 ^= 0x8000
        if d3 >= count4: break
        r = run(); n = r + 1
    # phases 2 and 3: skip / or runs (bit 12 = vertical flip, bit 11 = horizontal flip)
    for flag in (0x1000, 0x0800):
        pos = 0; d3 = 0
        r = run()
        if r != 0:
            skip = r; state = 'skip'
        else:
            r = run(); state = 'or'; n = r + 1
        while True:
            if state == 'or':
                for _ in range(n):
                    if pos < count4: words[pos] |= flag
                    pos += 1
                d3 += n
                if d3 >= count4: break
                r = run(); skip = r + 1; state = 'skip'
            else:
                pos += skip; d3 += skip
                if d3 >= count4: break
                r = run(); n = r + 1; state = 'or'
    # phase 4: tile words through a 16 entry move-to-front ring
    C = [0] * 16; head = 0                                 # head in words (the asm uses bytes 0..30)
    def tile():
        nonlocal head
        if B.bit() == 0:                                   # new literal: 11 bits, the head moves back one slot
            head = (head - 1) & 15
            C[head] = B.bits(11)
            return C[head]
        k = B.bits(4)
        if k == 0: return C[head]
        sel = (head + k) & 15; v = C[sel]
        for j in range(k, 0, -1): C[(head + j) & 15] = C[(head + j - 1) & 15]
        C[head] = v
        return v
    for i in range(count4 // 2):
        t = tile(); words[2 * i] |= t
        if B.bit():
            t2 = t & 0x7FF
            t2 = t2 - 1 if (words[2 * i] & 0x0800) else t2 + 1
        else:
            t2 = tile()
        words[2 * i + 1] |= t2
    return [tuple(words[4 * i:4 * i + 4]) for i in range(count4 // 4)], B.pos

def anim_list(rom, tileset):
    """animated tile groups of a tileset (`LoadAnimTiles $009D36`): list of dict(dest=VRAM byte address, words=DMA length in words, delay, frames, base=ROM address of frame 0).
    Index list `AnimatedTilesetTable $009E04` (one byte per entry, `$FF` ends), entries of `AnimatedTilesetData $009E1C` (10 bytes: dest word, length word, delay byte, frame count byte, long pointer to a long = data address).
    Frame f lives at base + f * words * 2; the game copies one frame per `delay` + 1 passes by DMA (`sub_9DBC`)."""
    out = []; i = 0
    while rom[0x9E04 + i] != 0xFF:
        if rom[0x9E04 + i] == tileset:
            e = rom[0x9E1C + 10 * i: 0x9E1C + 10 * i + 10]
            dest, words, delay, frames = struct.unpack('>HHBB', e[:6]); ptr = struct.unpack('>I', e[6:10])[0]
            base = struct.unpack('>I', rom[ptr:ptr + 4])[0]
            out.append(dict(dest=dest, words=words, delay=delay, frames=frames, base=base))
        i += 1
    return out

LIGHTABLE = 0x8800            # LightableRooms: 4 byte entries (room word, flag byte offset, bit), word < 0 ends
LIT_PAL = 0x2DB4              # LabrynthLitPal: palette used when the room is lit (lantern), same 13 colour format as RoomPals

def room_lightable(rom, room):
    """(flag byte offset, bit) of the lantern flag for a dark room, else None (`CheckIfRoomIsLit $0087BE`)."""
    a = LIGHTABLE
    while True:
        w = struct.unpack('>h', rom[a:a + 2])[0]
        if w < 0: return None
        if w == room: return rom[a + 2], rom[a + 3]
        a += 4

def apply_anim(tiles, rom, groups, frame):
    """tile bytes with animation frame number `frame` (modulo the frame count of each group) copied over the tiles."""
    t = bytearray(tiles)
    need = max([g['dest'] + g['words'] * 2 for g in groups] + [len(t)])
    t += bytes(need - len(t))
    for k, g in enumerate(groups):
        f = frame if isinstance(frame, int) else frame[k]
        if f is None: continue                             # group not active (the game did not start it)
        f %= g['frames']
        src = g['base'] + f * g['words'] * 2
        t[g['dest']:g['dest'] + g['words'] * 2] = rom[src:src + g['words'] * 2]
    return bytes(t)

def room_gfx(rom, room, lit=False):
    tab = struct.unpack('>I', rom[0xA0A00:0xA0A04])[0]
    e = rom[tab + 8 * room: tab + 8 * room + 8]
    tileset, palidx, sec = e[4] & 0x1F, e[5], e[7] >> 5
    tp = struct.unpack('>I', rom[0x44010:0x44014])[0]
    tptr = struct.unpack('>I', rom[tp + 4 * tileset: tp + 4 * tileset + 4])[0]
    tiles, _ = lz77(rom, tptr)
    bl = struct.unpack('>I', rom[0x1AF800:0x1AF804])[0]
    lst = struct.unpack('>I', rom[bl + 4 * e[4]: bl + 4 * e[4] + 4])[0]
    prim = struct.unpack('>I', rom[lst: lst + 4])[0]
    secp = struct.unpack('>I', rom[lst + 4 + 4 * sec: lst + 8 + 4 * sec])[0]
    b1, _ = bigtiles(rom, prim); b2, _ = bigtiles(rom, secp)
    pbase = (LIT_PAL if (lit and room_lightable(rom, room)) else 0x11C926 + 26 * palidx)
    pal = [struct.unpack('>H', rom[pbase + 2 * i: pbase + 2 * i + 2])[0] for i in range(13)]
    return dict(anim=anim_list(rom, tileset), lightable=room_lightable(rom, room), tiles=tiles, blocks=b1 + b2, primary=len(b1), secondary=len(b2), pal0=pal, tileset=tileset, palette=palidx, sec=sec, entry=e)

if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read(); room = int(sys.argv[2])
    g = room_gfx(rom, room)
    print('room %d: tileset %d (%d bytes = %d tiles), blocks %d primary + %d secondary, palette %d, secondary idx %d' % (room, g['tileset'], len(g['tiles']), len(g['tiles']) // 32, g['primary'], g['secondary'], g['palette'], g['sec']))
