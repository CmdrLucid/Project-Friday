#!/usr/bin/env python3
"""entscan.py DUMPDIR FRAME  -- decode the entity table (player + slots at $FF5400, stride $80) of one work-RAM dump written by `--ram-dump DIR:1` (every frame) and
print the fields that matter for hit / overlap questions: tile X/Y, box x1 x2 y1 y2 (+18..+1E), Z (+12) and top Z (+54), health (+3E), type (+3B), flags (+C), action (+2C).
Import it (`import entscan; r = entscan.load(dir, frame); entscan.ents(r)`) for scans over many frames; example in docs/DEBUGGING.md 'Hitbox question'.
Record every frame of a replay range:  GENRECOMP_DUMPRANGE=900:2100 build/landstalker --headless --frames 2101 --ram-dump DIR:1 ROM  (needs the matching save copy + GENRECOMP_INPUTSCRIPT)."""
import sys


def load(d, f):
    return open('%s/ram_%06d.bin' % (d, f), 'rb').read()[:0x10000]


def B(r, a): return r[(a & 0xFFFF) ^ 1]


def W(r, a): return (B(r, a) << 8) | B(r, a + 1)


def ents(r):
    out = []
    for k in range(16):
        b = 0xFF5400 + 0x80 * k
        if B(r, b) == 0xFF: break
        out.append(dict(k=k, id=B(r, b), fl=B(r, b + 0xC), typ=B(r, b + 0x3B), x1=W(r, b + 0x18), x2=W(r, b + 0x1A), y1=W(r, b + 0x1C), y2=W(r, b + 0x1E),
                        z=W(r, b + 0x12), top=W(r, b + 0x54), hp=W(r, b + 0x3E), tx=B(r, b), ty=B(r, b + 1), act=W(r, b + 0x2C), beh=W(r, b + 0x2A)))
    return out


if __name__ == '__main__':
    r = load(sys.argv[1], int(sys.argv[2]))
    for e in ents(r):
        print({k: (hex(v) if k in ('x1', 'x2', 'y1', 'y2', 'z', 'top', 'act', 'beh') else v) for k, v in e.items()})
