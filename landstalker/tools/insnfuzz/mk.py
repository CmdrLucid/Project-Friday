#!/usr/bin/env python3
"""insnfuzz/mk.py [count] [seed]  -> fuzz.bin fuzz.json tests.txt

Random single 68000 instructions (decoded and filtered with capstone), each in its own tiny function  `insn; rts`  at 0x1000 + i*0x20.
h.c runs every one on GPGX's own Musashi interpreter and on the recompiled C with identical random registers / flags / RAM and compares the result.
Skipped: control flow, privileged / SR / USP, stack tricks (a7, link, unlk, pea), chk, tas, stop, reset, trap."""
import json, random, struct, sys
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
count = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
rnd = random.Random(seed)
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
SKIP = ('dc', 'bra', 'bsr', 'jmp', 'jsr', 'rts', 'rte', 'rtr', 'trap', 'trapv', 'chk', 'stop', 'reset', 'illegal', 'link', 'unlk', 'pea', 'tas', 'nop')
def skipped(i):
    m = i.mnemonic.split('.')[0]
    if m in SKIP or (m.startswith('b') and m not in ('bchg', 'bclr', 'bset', 'btst')) or m.startswith('db'):
        return True
    t = (i.mnemonic + ' ' + i.op_str).lower()
    return any(w in t for w in ('a7', 'sp', 'sr', 'usp', 'unhandled', '[', 'invalid', '*', 'pc'))   # '[' '*' = 68020 addressing modes; pc-relative needs the real ROM position
import re
_IDX = re.compile(r'[ad]\d\.[wl]\)|\(\w+\.[wl]\)')
def full_format(i):
    """68020 full extension word (bit 8 set) in an indexed operand: the 68000 ignores bits 10-8, capstone does not -> the two decoders disagree"""
    if not _IDX.search(i.op_str): return False
    b = bytes(i.bytes)[2:]
    return any(((b[k] << 8 | b[k + 1]) & 0x0700) for k in range(0, len(b) - 1, 2))
def small_ext():
    # bias extension words to small even values so effective addresses stay near the register-held RAM pointers
    r = rnd.random()
    if r < 0.6: return rnd.randrange(-0x80, 0x80) * 2 & 0xFFFF
    if r < 0.8: return rnd.randrange(0, 0x10000) & 0xFFFE
    return rnd.randrange(0, 0x10000)
tests = []
rom = bytearray(0x100000)
rom[0:8] = struct.pack('>II', 0x00FFFE00, 0x200)
for v in range(2, 64): rom[v * 4:v * 4 + 4] = struct.pack('>I', 0x300)
rom[0x300:0x302] = struct.pack('>H', 0x60FE)
rom[0x100:0x110] = b'SEGA MEGA DRIVE '
tries = 0
while len(tests) < count and tries < count * 400:
    tries += 1
    op = rnd.randrange(0, 0x10000)
    data = struct.pack('>H', op) + b''.join(struct.pack('>H', small_ext()) for _ in range(4))
    ins = None
    for i in md.disasm(data, 0, 1): ins = i
    if ins is None or skipped(ins) or full_format(ins): continue
    addr = 0x1000 + len(tests) * 0x20
    rom[addr:addr + ins.size] = bytes(ins.bytes)
    rom[addr + ins.size:addr + ins.size + 2] = struct.pack('>H', 0x4E75)
    memop = ('(' in ins.op_str) or ('$' in ins.op_str and '#' not in ins.op_str.split(',')[0] or ',$' in ins.op_str)
    tests.append((addr, ins.size, 1 if memop else 0, '%s %s' % (ins.mnemonic, ins.op_str), bytes(ins.bytes).hex()))
open('fuzz.bin', 'wb').write(rom)
end = 0x1000 + len(tests) * 0x20
json.dump({'title': 't', 'seeds': {'0x%06X' % t[0]: 'f_%05d' % n for n, t in enumerate(tests)}, 'offset_tables': [],
           'code_ranges': [['0x1000', hex(end)]]}, open('fuzz.json', 'w'))
with open('tests.txt', 'w') as f:
    for n, t in enumerate(tests):
        f.write('%d %X %d %d %s | %s\n' % (n, t[0], t[1], t[2], t[4], t[3]))
print('wrote fuzz.bin fuzz.json tests.txt with %d instructions' % len(tests))
