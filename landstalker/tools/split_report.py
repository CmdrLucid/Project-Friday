#!/usr/bin/env python3
"""split_report.py ROM [src/recomp]

Explains every `check_splits.py` finding (a generated function whose successor starts INSIDE its last instruction). Per distinct split address
("tail") it prints, compactly:
  class   R = the ROM jumps/branches/calls to it (jsr/jmp/bsr/bra/bcc), P = only a 32-bit pointer to it (jump/data table), S = only a seed, N = nothing
  A:      the instruction that straddles the address (the decode of the function that is cut)
  B:      the instructions decoded from the address itself (the decode of the function that starts there)
  seed:   matching lines of gen_seeds.py (with their comment)
Reading hints: class R with a sane B decode = a real entry into the middle of A -> A is probably data/misdecoded or an overlapping entry (fix: make the
cut function end before it / drop the bogus A); class P/S/N with a garbage B decode = bogus seed (remove it); both decodes sane = overlapping code.
Read-only, prints only a few instructions per finding."""
import sys, os, re, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_splits import find_bad
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000

rom = open(sys.argv[1], 'rb').read()
d = sys.argv[2] if len(sys.argv) > 2 else 'src/recomp'
total, bad = find_bad(rom, d)
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
tails = {}
for name, start, end, tail, nxt, a in bad:
    tails.setdefault(tail, []).append((name, start, a, nxt))

# cross references to the split addresses
refs = {t: {'code': [], 'ptr': []} for t in tails}
n = len(rom)
for off in range(0, n - 6, 2):
    w = (rom[off] << 8) | rom[off + 1]
    if w in (0x4EB9, 0x4EF9, 0x4EB8, 0x4EF8):                       # jsr/jmp abs.l / abs.w
        t = struct.unpack('>I', rom[off + 2:off + 6])[0] & 0xFFFFFF if w & 1 else struct.unpack('>h', rom[off + 2:off + 4])[0] & 0xFFFFFF
        if t in refs: refs[t]['code'].append(off)
    if 0x60 <= rom[off] <= 0x6F and rom[off + 1] == 0:                # bra/bsr/bcc .w
        t = (off + 2 + struct.unpack('>h', rom[off + 2:off + 4])[0]) & 0xFFFFFF
        if t in refs: refs[t]['code'].append(off)
    if off + 4 <= n:
        v = struct.unpack('>I', rom[off:off + 4])[0]
        if v in refs and w not in (0x4EB9, 0x4EF9): refs[v]['ptr'].append(off)

seedlines = []
for f in ('gen_seeds.py',):
    if os.path.exists(f): seedlines = open(f).read().split('\n')


def dis(addr, count):
    out = []; off = addr
    for _ in range(count):
        ins = list(md.disasm(rom[off:off + 12], off, 1))
        if not ins: out.append('%06X dc.w $%04X' % (off, int.from_bytes(rom[off:off + 2], 'big'))); off += 2; continue
        i = ins[0]; out.append('%06X %s %s' % (off, i.mnemonic, i.op_str)); off += i.size
    return out


print('%d generated functions scanned; %d cut off inside an instruction; %d distinct split addresses' % (total, len(bad), len(tails)))
cnt = {'R': 0, 'P': 0, 'S': 0, 'N': 0}
for t in sorted(tails):
    seeds = [l.strip() for l in seedlines if re.search(r'0x0*%X\b' % t, l, re.I)]
    r = refs[t]
    cls = 'R' if r['code'] else 'P' if r['ptr'] else 'S' if seeds else 'N'
    cnt[cls] += 1
    owners = sorted(set((x[1], x[2]) for x in tails[t]))
    a_addr = owners[0][1]
    A = dis(a_addr, 1)[0]
    print('$%06X class=%s  cut function(s): %s' % (t, cls, ', '.join('$%06X(straddler $%06X)' % o for o in owners)))
    print('   A: %s   [bytes %s]' % (A, rom[a_addr:a_addr + max(2, t - a_addr + 2)].hex()))
    print('   B: %s' % ' ; '.join(x[7:] for x in dis(t, 4)))
    if r['code']: print('   code refs: ' + ' '.join('$%06X' % x for x in r['code'][:6]))
    if r['ptr']: print('   ptr refs : ' + ' '.join('$%06X' % x for x in r['ptr'][:6]))
    for l in seeds[:2]: print('   seed: ' + l[:140])
print('class counts:', cnt)
