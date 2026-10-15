#!/usr/bin/env python3
"""disasm.py ROM ADDR [count=60] [-n NAME_JSON]

Disassembles `count` instructions of the ROM from ADDR (hex) with capstone (68000), one per line:  ADDR  bytes  mnemonic operands.
Branch/call targets are annotated with names from docs/symbols.json / docs/symbols_auto.json when known. Read-only; prints no ROM data besides the code the user asked for."""
import sys, json, os
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
rom = open(sys.argv[1], 'rb').read()
addr = int(sys.argv[2], 16)
count = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 60
names = {}
here = os.path.dirname(os.path.abspath(__file__))
for f in ('symbols.json', 'symbols_auto.json'):
    p = os.path.join(here, '..', 'docs', f)
    if os.path.exists(p):
        try:
            d = json.load(open(p))
            if isinstance(d, dict) and 'symbols' in d:
                for s in d['symbols']: names[int(s['addr'], 16)] = s['name']
            elif isinstance(d, dict):
                for k, v in d.items():
                    try: names[int(k, 16) if isinstance(k, str) else k] = (v['name'] if isinstance(v, dict) else v)
                    except ValueError: pass
        except Exception:
            pass
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
md.detail = False
# --follow: if the code at ADDR is a jump stub (jmp $xxxxxx.l / bra), print it and continue at its target (up to 3 hops)
if '--follow' in sys.argv:
    for _ in range(3):
        ins = list(md.disasm(rom[addr:addr + 12], addr, 1))
        if ins and ins[0].mnemonic in ('jmp', 'bra', 'bra.w', 'bra.b') and ins[0].op_str.startswith('$'):
            t = int(ins[0].op_str.lstrip('$').split('.')[0], 16)
            print('%06X  stub: %s %s  -> %06X' % (addr, ins[0].mnemonic, ins[0].op_str, t)); addr = t
        else:
            break
n = 0
off = addr
while n < count and off < len(rom) - 2:
    got = False
    for i in md.disasm(rom[off:off + 12], off, 1):
        got = True
        note = ''
        for tok in i.op_str.replace(',', ' ').replace('(', ' ').replace(')', ' ').split():
            if tok.startswith('$'):
                try:
                    t = int(tok.lstrip('$').split('.')[0], 16)
                    if t in names: note = '   ; ' + names[t]
                except ValueError: pass
        lab = ('%s:\n' % names[off]) if off in names else ''
        print('%s%06X  %-14s %-8s %s%s' % (lab, off, bytes(i.bytes).hex(), i.mnemonic, i.op_str, note))
        off += i.size; n += 1
    if not got:
        print('%06X  %-14s dc.w     $%04X' % (off, rom[off:off + 2].hex(), int.from_bytes(rom[off:off + 2], 'big')))
        off += 2; n += 1
