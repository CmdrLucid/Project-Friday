#!/usr/bin/env python3
"""scan_hv.py ROM [context_bytes]

Finds every place in the ROM that reads the VDP HV counter ($C00008/$C00009, absolute long 00C0 0008/0009) or the VDP status ($C00004) and prints the disassembly
around it (capstone m68k). Purpose: find out whether the game derives random numbers (NPC walk directions) from the raster counter, which would make NPC
behaviour depend on exact cycle timing. The HV-counter reads are the interesting ones."""
import sys, struct
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
rom = open(sys.argv[1], 'rb').read()
ctx = int(sys.argv[2]) if len(sys.argv) > 2 else 24
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
targets = {0x00C00008: 'HV counter (word/byte)', 0x00C00009: 'HV counter low byte'}
hits = []
for a in range(0, len(rom) - 4, 2):
    v = struct.unpack('>I', rom[a:a + 4])[0]
    if v in targets:
        hits.append((a, v))
print('%d absolute references to $C00008/9 found' % len(hits))
for a, v in hits:
    start = max(0, a - ctx) & ~1
    print('\n== ref to $%06X at ROM $%06X ==' % (v, a))
    shown = 0
    for i in md.disasm(rom[start:a + ctx + 8], start):
        print('  %06X  %-8s %s%s' % (i.address, i.mnemonic, i.op_str, '   <==' if i.address <= a < i.address + i.size else ''))
        shown += 1
        if shown > 24: break
