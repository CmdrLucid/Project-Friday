#!/usr/bin/env python3
"""Interpreter-fallback test (reference core vs recompiled), see tools/patch_interp.py.
$600 (A) and $620 (B) and $640 (C, terminal) are never referenced statically (addresses computed at run time) and are
outside code_ranges, so the generator has no function for them. Expected RAM (real core):
FF0000=AA FF0001=07 FF0003=DD FF0010=1234 FF0012=5678 FF0014=0001 FF0016=9999 FF0002 stays 00 (skipped by C)."""
import json, struct
W = lambda *ws: b''.join(struct.pack('>H', w & 0xFFFF) for w in ws)
L = lambda v: struct.pack('>I', v)
def bsr(at, to): return W(0x6100, (to - (at + 2)) & 0xFFFF)
rom = bytearray(0x10000)
def put(a, b): rom[a:a+len(b)] = b
m = 0x200; main = b''
# a0 = $5F0 + $10 computed
main += W(0x203C) + L(0x5F0) + W(0xD0BC) + L(0x10) + W(0x2040) + W(0x4E90)          # move.l #$5F0,d0 / add.l #$10,d0 / movea.l d0,a0 / jsr (a0)
main += W(0x13FC, 0x00AA, 0x00FF, 0x0000)                                              # move.b #$AA,$FF0000
main += W(0x13C0, 0x00FF, 0x0001)                                                      # move.b d0,$FF0001  (d0 = 7 from routine B)
a = m + len(main); main += bsr(a, 0x400)                                                # bsr sub (calls terminal routine C)
main += W(0x13FC, 0x00DD, 0x00FF, 0x0003)                                              # move.b #$DD,$FF0003
put(m, main); end = m + len(main)
put(0x400, W(0x203C) + L(0x630) + W(0xD0BC) + L(0x10) + W(0x2040, 0x4E90) + W(0x13FC, 0x00EE, 0x00FF, 0x0002) + W(0x4E75))  # sub: jsr C; move.b #$EE,$FF0002 (must be skipped); rts
put(0x600, W(0x33FC, 0x1234, 0x00FF, 0x0010) + W(0x203C) + L(0x610) + W(0xD0BC) + L(0x10) + W(0x2040, 0x4E90) + W(0x33FC, 0x5678, 0x00FF, 0x0012, 0x4E75))  # A
put(0x620, W(0x5279, 0x00FF, 0x0014, 0x7007, 0x4E75))                                  # B: addq.w #1,$FF0014 / moveq #7,d0 / rts   (A calls $620 via a0=$610+$10)
put(0x640, W(0x588F, 0x33FC, 0x9999, 0x00FF, 0x0016, 0x4E75))                           # C: addq.l #4,sp / move.w #$9999,$FF0016 / rts (returns to sub's caller)
def build(path, tail):
    r = bytearray(rom)
    r[0:8] = struct.pack('>II', 0x00FFFE00, 0x200)
    for v in range(2, 64): r[v*4:v*4+4] = struct.pack('>I', 0x700)
    r[0x700:0x702] = W(0x60FE)
    r[0x100:0x110] = b'SEGA MEGA DRIVE '
    r[end:end+len(tail)] = tail
    open(path, 'wb').write(r)
build('ref.bin', W(0x60FE)); build('rec.bin', W(0x4E75))
json.dump({'title': 't', 'offset_tables': [], 'seeds': {'0x000200': 't_main', '0x000400': 't_sub'},
           'code_ranges': [['0x200', '0x420']]}, open('r.json', 'w'))
print("wrote ref.bin rec.bin r.json")
