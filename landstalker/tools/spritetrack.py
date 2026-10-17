#!/usr/bin/env python3
"""spritetrack.py DUMPDIR FRAME [FRAME2 ...]   -- which figures are on screen in one frame, decoded from per-frame work-RAM dumps (`--ram-dump DIR:1`).

Per visible entity (list at g_VisibleEntityList $FF11DE, offsets from Player_X $FF5400, $FFFF ends it): slot, type (+3B), SpriteGraphic (+0B), AnimationIndex (+24),
AnimationFrame (+26), TileSource (+06, low 11 bits = first VDP tile), screen x/y (+10 / +0E), then the VDP sprite entries of the RAM mirror g_VDPSpr16_Y $FF05D0
(8 bytes: y, size|link, attr word with tile, x) that use tiles in the entity's range. Shows that the sprite key (graphic, animation, frame) is stable while the VRAM tile
slot moves (RENDERER_IDEAS.md, FORMATS.md 'Sprite upload'). Record dumps as in entscan.py."""
import sys
from entscan import load, B, W

BASE = 0xFF5400
def ents(r):
    out, a = [], 0xFF11DE
    while len(out) < 17:
        o = W(r, a)
        if o & 0x8000: break
        out.append(o); a += 2
    return out

def sat(r):
    res = []
    for i in range(80):
        a = 0xFF05D0 + 8 * i
        y, sl, at, x = W(r, a), W(r, a + 2), W(r, a + 4), W(r, a + 6)
        res.append((y, sl, at, x))
    return res

def frame(d, f):
    r = load(d, f)
    print('--- frame %d' % f)
    es = ents(r)
    spr = sat(r)
    for o in es:
        b = BASE + o
        ts = W(r, b + 6) & 0x7FF
        print('slot %2d type %02X gfx %02X anim %04X frame %04X tile %03X  scr x=%4d y=%4d  fl1=%02X fl2=%02X' % (
            o // 0x80, B(r, b + 0x3B), B(r, b + 0xB), W(r, b + 0x24), W(r, b + 0x26), ts, W(r, b + 0x10), W(r, b + 0x0E), B(r, b + 8), B(r, b + 0xC)))
    print('SAT mirror entries in use:')
    for i, (y, sl, at, x) in enumerate(spr):
        if y == 0 and at == 0 and x == 0: break
        print('  #%2d y=%4d x=%4d size=%X link=%02X tile=%03X pal=%d prio=%d' % (i, y, x, sl >> 8 & 15, sl & 0x7F, at & 0x7FF, at >> 13 & 3, at >> 15))

if __name__ == '__main__':
    for f in sys.argv[2:]: frame(sys.argv[1], int(f))
