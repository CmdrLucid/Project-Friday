#!/usr/bin/env python3
"""code_extent.py ROM [recomp.json] [src/recomp] [genrecomp-dir]

Where does CERTAIN code live in the ROM?  Runs only the safe part of the genrecomp analyzer (recursive descent from the vectors and the explicit seeds,
no heuristic scans) and prints, per 0x2000-byte ROM block, how many bytes of instructions descent reached. Then it compares with the functions that
the build generated (src/recomp/recomp_*.c): how many of them lie in blocks that descent never reached = functions that only exist because a
heuristic scan (jump-table / address-load / prologue guess) invented them. Those are the 'jt_XXXXXX' / 'sub_XXXXXX' pseudo functions that
check_splits.py reports inside real instructions or data.

Use the result to set "code_ranges" in recomp.json (analyze.py bounds its heuristic scans with it; default is the whole ROM $200-$1000000).
Read-only; prints addresses and counts only."""
import sys, os, re, glob, json, collections

rom_path = sys.argv[1]
cfg_path = sys.argv[2] if len(sys.argv) > 2 else 'recomp.json'
gen_dir = sys.argv[3] if len(sys.argv) > 3 else 'src/recomp'
gr = sys.argv[4] if len(sys.argv) > 4 else '.deps/genrecomp'
sys.path.insert(0, os.path.join(gr, 'tools', 'recompiler'))
from analyze import GenesisROM, M68KAnalyzer

rom = GenesisROM(rom_path)
an = M68KAnalyzer(rom)
cfg = json.load(open(cfg_path))
an.load_config(cfg)
entry = {rom.initial_pc}
for name, addr in rom.vectors.items():
    entry.add(addr)
for addr in an.EXPLICIT_SEEDS:
    entry.add(addr)
funcs = set(entry)
an._descend(entry, funcs)
BLK = 0x2000
cert = collections.Counter()
for a, (_, _, size, _) in an.instructions.items():
    cert[a // BLK] += size
print('descent from %d entry points reached %d instructions; last certain instruction at $%06X' % (len(entry), len(an.instructions), max(an.instructions)))

# generated functions (from the last build)
hdr = re.compile(r'^/\* \$([0-9A-F]{6})-\$([0-9A-F]{6})\s+\((\d+) instructions')
gen = []
for f in glob.glob(os.path.join(gen_dir, 'recomp_*.c')):
    for line in open(f):
        m = hdr.match(line)
        if m: gen.append((int(m.group(1), 16), int(m.group(2), 16)))
genblk = collections.Counter(s // BLK for s, e in gen)
print('%d generated functions' % len(gen))
print('block      certain-code-bytes  generated-functions')
last_cert = max(cert) if cert else 0
for b in range(0, (len(rom.data) + BLK - 1) // BLK):
    c, g = cert.get(b, 0), genblk.get(b, 0)
    if c or g:
        print('$%06X-%06X  %6d %s %6d %s' % (b * BLK, (b + 1) * BLK - 1, c, '#' * min(40, c // 200), g, '' if c else '   <-- generated but NO certain code (heuristic only)'))
none = sum(g for b, g in genblk.items() if not cert.get(b))
print('generated functions in blocks with no certain code at all: %d of %d' % (none, len(gen)))
for end in (0x30000, 0x40000, 0x60000, 0x80000):
    print('  functions starting at or above $%06X: %d' % (end, sum(1 for s, e in gen if s >= end)))
