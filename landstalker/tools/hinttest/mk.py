#!/usr/bin/env python3
"""HInt + HV-counter wait test (reference core vs recompiled).

Main loop floods the VDP data port (so the recompiled CPU runs ahead of the scanline
clock), HInt fires every line; the handler does what Landstalker's HandleHBlankInterrupt
does: wait until the V counter ($C00008) changes, then bump a counter at $FF0000.
Without patch_hintime.py the recompiled build hangs inside the handler.
  python3 mk.py  -> ref.bin (bra.s *-style loop, same code) rec.bin r.json
"""
import json, struct
W = lambda *ws: b''.join(struct.pack('>H', w & 0xFFFF) for w in ws)
main = W(0x33FC, 0x8004, 0x00C0, 0x0004,      # reg0 = 04
         0x33FC, 0x8164, 0x00C0, 0x0004,      # reg1 = 64 (display, vint, mode 5)
         0x33FC, 0x8A00, 0x00C0, 0x0004,      # reg10 = 0 (HInt every line)
         0x33FC, 0x8014, 0x00C0, 0x0004,      # reg0 = 14 (HInt on)
         0x46FC, 0x2000,                      # move #$2000,sr
         0x23FC, 0x4000, 0x0000, 0x00C0, 0x0004,   # VRAM write address 0
         0x41F9, 0x00C0, 0x0000,              # lea $C00000,a0
         0x303C, 0x1234,                      # loop: move.w #$1234,d0
         0x7263,                              # moveq #99,d1
         0x3080,                              # w: move.w d0,(a0)
         0x51C9, 0xFFFC,                      # dbf d1,w
         0x60F2)                              # bra.s loop
hint = W(0x48E7, 0xFFFE,                      # movem.l d0-a6,-(sp)  (the game's handler does this first)
         0x1039, 0x00C0, 0x0008,              # move.b $C00008,d0
         0xB039, 0x00C0, 0x0008,              # w2: cmp.b $C00008,d0
         0x67F8,                              # beq.s w2
         0x52B9, 0x00FF, 0x0000,              # addq.l #1,$FF0000
         0x4CDF, 0x7FFF,                      # movem.l (sp)+,d0-a6
         0x4E73)                              # rte
rom = bytearray(0x10000)
rom[0:8] = struct.pack('>II', 0x00FFFE00, 0x200)
for v in range(2, 64): rom[v*4:v*4+4] = struct.pack('>I', 0x3F0)
rom[30*4:30*4+4] = struct.pack('>I', 0x300)   # level 6 (VBlank)
rom[28*4:28*4+4] = struct.pack('>I', 0x400)   # level 4 autovector (HInt)
rom[0x100:0x110] = b'SEGA MEGA DRIVE '
rom[0x200:0x200+len(main)] = main
# VInt (level 6) handler: 20000 nested RAM reads = ~560k cycles = ~160 lines, so the CPU clock ends up
# many lines ahead of the scanline clock when the next H-Ints are dispatched.
heavy = W(0x303C, 0x4E1F, 0x1239, 0x00FF, 0x0020, 0x51C8, 0xFFF8, 0x4E73)
rom[0x300:0x300+len(heavy)] = heavy
rom[0x3F0:0x3F2] = W(0x4E73)                   # rte for every other vector
rom[0x400:0x400+len(hint)] = hint
open('ref.bin', 'wb').write(rom); open('rec.bin', 'wb').write(rom)
json.dump({'title': 't', 'seeds': {'0x000200': 't_main', '0x000300': 't_vint', '0x0003F0': 't_rte', '0x000400': 't_hint'},
           'offset_tables': [], 'code_ranges': [['0x200', '0x420']]}, open('r.json', 'w'))
print("wrote ref.bin rec.bin r.json")
