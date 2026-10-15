#!/usr/bin/env python3
"""Instruction timing test (reference core vs recompiled), see README.md.
python3 mk.py  -> t.bin t.json   (same ROM runs on genrecomp_ref and on the recompiled code)
Main loop: mixed instructions (mulu/divu/shifts/movem/dbf/Bcc taken+not taken/Scc/jsr/rts/memory ops) counting
iterations at $FF0000; VBlank handler counts frames at $FF0004. If timing is right both runners reach (nearly) the
same iterations-per-frame."""
import json, struct, sys
SIMPLE = len(sys.argv) > 1 and sys.argv[1] == 'simple'   # no mul/div/movem: only short instructions
W = lambda *ws: b''.join(struct.pack('>H', w & 0xFFFF) for w in ws)
init = W(0x33FC, 0x8164, 0x00C0, 0x0004,      # VDP reg1 = $64: display on, VBlank irq on
         0x46FC, 0x2000)                      # move #$2000,sr
loop = W(0x7605,                              # moveq #5,d3
         0x383C, 0x04D2,                      # move.w #1234,d4
         ) + (b'' if SIMPLE else W(
         0xC6C4,                              # mulu.w d4,d3
         0x2A3C, 0x0001, 0x86A0,              # move.l #100000,d5
         0x8AFC, 0x0007)) + W(                # divu.w #7,d5
         0x7403,                              # moveq #3,d2
         0xE5AE,                              # lsl.l d2,d6
         0xE54E,                              # lsl.w #2,d6
         ) + (b'' if SIMPLE else W(
         0x48E7, 0xFFFE,                      # movem.l d0-a6,-(sp)
         0x4CDF, 0x7FFF)) + W(                # movem.l (sp)+,d0-a6
         0x720A,                              # moveq #10,d1
         0x5240,                              # w: addq.w #1,d0
         0x51C9, 0xFFFC,                      # dbf d1,w
         0x4A44,                              # tst.w d4
         0x6702, 0x4E71,                      # beq.s +2 (not taken); nop
         0x6602, 0x4E71,                      # bne.s +2 (taken); nop (skipped)
         0x56C0,                              # sne d0
         0xD3B9, 0x00FF, 0x0100,              # add.l d1,($FF0100).l
         0x41F9, 0x00FF, 0x0200,              # lea $FF0200,a0
         0x30D8,                              # move.w (a0)+,(a0)+
         0x4EB9, 0x0000, 0x0280,              # jsr $280
         0x52B9, 0x00FF, 0x0000)              # addq.l #1,$FF0000
bra = W(0x6000, 0)
disp = -(len(loop) + 2)                       # bra.w back to the loop start (displacement is relative to the ext word)
bra = W(0x6000, disp)
main = init + loop + bra
rom = bytearray(0x10000)
rom[0:8] = struct.pack('>II', 0x00FFFE00, 0x200)
for v in range(2, 64): rom[v*4:v*4+4] = struct.pack('>I', 0x3F0)
rom[30*4:30*4+4] = struct.pack('>I', 0x300)   # level 6 (VBlank)
rom[0x100:0x110] = b'SEGA MEGA DRIVE '
rom[0x200:0x200+len(main)] = main
rom[0x280:0x284] = W(0x4E71, 0x4E75)          # sub: nop; rts
rom[0x300:0x308] = W(0x52B9, 0x00FF, 0x0004, 0x4E73)   # addq.l #1,$FF0004 ; rte
rom[0x3F0:0x3F2] = W(0x4E73)
open('t.bin', 'wb').write(rom)
json.dump({'title': 't', 'seeds': {'0x000200': 't_main', '0x000280': 't_sub', '0x000300': 't_vint', '0x0003F0': 't_rte'},
           'offset_tables': [], 'code_ranges': [['0x200', '0x310']]}, open('t.json', 'w'))
print("wrote t.bin t.json; loop length", len(loop), "bytes")
