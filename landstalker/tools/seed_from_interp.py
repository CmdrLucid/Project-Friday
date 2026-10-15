#!/usr/bin/env python3
"""Turn the interpreter's address log into seeds, so the next build compiles those routines natively.

Record:   LANDSTALKER_INTERP_LOG=$HOME/interp.txt ~/Landstalker.sh     (play; one hex address per line)
Convert:  python3 tools/seed_from_interp.py ~/interp.txt [recomp.json]   (also keep the seeds in gen_seeds.py: see --list)
Then rebuild. Goal: a full playthrough with an empty log; then the fallback can be switched off by default.
"""
import json, sys
log = sys.argv[1]
cfgp = sys.argv[2] if len(sys.argv) > 2 else "recomp.json"
addrs = sorted({int(l.strip(), 16) for l in open(log) if l.strip()})
cfg = json.load(open(cfgp))
new = [a for a in addrs if a % 2 == 0 and a < 0x400000 and f"0x{a:06X}" not in cfg["seeds"]]
for a in new:
    cfg["seeds"][f"0x{a:06X}"] = f"sub_{a:06X}"
cfg["seeds"] = dict(sorted(cfg["seeds"].items()))
json.dump(cfg, open(cfgp, "w"), indent=2)
print(f"{len(addrs)} distinct interpreter addresses in {log}; {len(new)} new seeds added to {cfgp}")
print("persist them across ZIP updates: paste into gen_seeds.py as (0x%06X, 2, 1, \"from interp log\") rows or send me the log:" % (new[0] if new else 0))
for a in new: print("   0x%06X" % a)
