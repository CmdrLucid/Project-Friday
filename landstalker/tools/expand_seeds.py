#!/usr/bin/env python3
"""Expand seeds that sit inside a jump table of consecutive `bra.w` (0x6000 dddd)
entries into the whole table, by reading the ROM. Computed jumps like
`jmp Table(pc,d0.w)` into such a table are invisible to the analyzer, and one
"no function at $XXXXXX" line only names one entry; this seeds the rest.

usage: expand_seeds.py ROM recomp.json   (rewrites recomp.json, idempotent)
"""
import json, sys

rom = open(sys.argv[1], "rb").read()
cfg = json.load(open(sys.argv[2]))
seeds = cfg["seeds"]

def is_bra_w(a):
    return a >= 0 and a % 2 == 0 and a + 4 <= len(rom) and rom[a] == 0x60 and rom[a + 1] == 0x00

added = 0
for key in list(seeds):
    a = int(key, 16)
    if not is_bra_w(a):
        continue
    lo = a
    while is_bra_w(lo - 4):
        lo -= 4
    hi = a
    while is_bra_w(hi + 4):
        hi += 4
    if hi - lo + 4 < 8:
        continue                           # a lone bra.w is ordinary code
    for t in range(lo, hi + 4, 4):
        k = f"0x{t:06X}"
        if k not in seeds:
            seeds[k] = f"sub_{t:06X}"; added += 1
    print(f"table ${lo:06X}-${hi + 3:06X}: {(hi - lo) // 4 + 1} bra.w entries (from seed {key})")
cfg["seeds"] = dict(sorted(seeds.items()))
json.dump(cfg, open(sys.argv[2], "w"), indent=2)
print(f"expand_seeds: +{added} seeds, {len(seeds)} total")
