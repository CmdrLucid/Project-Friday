#!/usr/bin/env python3
"""Seed every script entry point from the ROM's script tables and the disassembly's list of script jump targets (replaces the interpreter-fallback whack-a-mole).

Landstalker's cutscene and character script tables are arrays of words, one per ID. An odd word is text-script data
(ScriptID); an even word is `ScriptJump`: 68K code at tablebase+word (run by RunTextCmd with `jsr (a0,d0.w)`). Those code
targets are only reached through a computed jump, so the analyzer never finds them.

tools/script_tables.json (made from the lordmir disassembly, contains no ROM data) lists per table the entry kinds
(I/J string) and anchor entries (index, known target). The table base is located in the ROM by requiring
word[base+2*idx] == (target-base) mod 65536 for every anchor; then all J entries are read and added to recomp.json seeds.

usage: script_tables.py ROM recomp.json   (idempotent; prints what it did)
"""
import json, os, sys

rom = open(sys.argv[1], "rb").read()
cfg = json.load(open(sys.argv[2]))
tabs = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "script_tables.json")))
seeds = cfg["seeds"]
w = lambda a: (rom[a] << 8) | rom[a + 1]
added = 0
extra = tabs.pop("_extra_targets", [])
for name, t in tabs.items():
    kinds, anchors = t["kinds"], t["anchors"]
    found = []
    i0, t0 = anchors[0]
    for b in range(0, len(rom) - 2 * len(kinds), 2):
        if w(b + 2 * i0) != (t0 - b) & 0xFFFF:
            continue
        if all(w(b + 2 * i) == (tg - b) & 0xFFFF for i, tg in anchors):
            found.append(b)
    if len(found) != 1:
        print(f"script_tables: {name}: table base not found uniquely ({[hex(x) for x in found]}); skipped")
        continue
    b = found[0]
    n = 0
    bad = 0
    for i, k in enumerate(kinds):
        v = w(b + 2 * i)
        if k == "J":
            tg = b + (v - 0x10000 if v & 0x8000 else v)   # jsr (a0,d0.w): word is sign-extended
            if v & 1 or tg < 0 or tg >= len(rom):
                bad += 1
                continue
            key = "0x%06X" % tg
            if key not in seeds:
                seeds[key] = "sub_%06X" % tg
                added += 1
            n += 1
        elif not v & 1:
            bad += 1
    print(f"script_tables: {name} table at ${b:06X}: {n} code entry points, {bad} entries inconsistent with kinds")
# every `Jump to address 0x...` named in the disassembly's script tables (also shop / special-item tables, which have no fixed layout)
n_extra = 0
for tg in extra:
    key = "0x%06X" % tg
    if tg & 1 or tg <= 0 or tg >= len(rom) or key in seeds:
        continue
    seeds[key] = "sub_%06X" % tg
    added += 1
    n_extra += 1
print(f"script_tables: {n_extra} more entry points from the disassembly's script jump list ({len(extra)} listed)")
cfg["seeds"] = dict(sorted(seeds.items()))
json.dump(cfg, open(sys.argv[2], "w"), indent=2)
print(f"script_tables: {added} new seeds")
