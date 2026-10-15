#!/usr/bin/env python3
"""Run generate.py until no call target is left without a function.

generate.py (with tools/patch_gencross.py) prints
    WARNING: N call targets are not functions (they will fail at run time):
        $002458  decoded but not split
Each such target becomes a seed in recomp.json and generation is repeated (max 6 rounds).
Only targets reported "decoded but not split" are seeded. "not decoded as code" / odd / inside-instruction
entries are data or false positives of the jump-table scan (a real build listed 851, seeding 44 of them changed nothing).

usage: seed_missing.py ROM recomp.json generate.py outdir
"""
import json, re, subprocess, sys

rom, cfgp, gen, out = sys.argv[1:5]
pat = re.compile(r"^\s+\$([0-9A-Fa-f]{6})\s+(.*)$")

for rnd in range(1, 7):
    print(f"[seed_missing] round {rnd}: generating...", flush=True)
    p = subprocess.Popen([sys.executable, gen, rom, "-o", out, "-c", cfgp],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    left = []
    for line in p.stdout:
        print(line, end="", flush=True)
        m = pat.match(line)
        if m:
            left.append((int(m.group(1), 16), m.group(2).strip()))
    if p.wait() != 0:
        sys.exit("generate.py failed")
    cfg = json.load(open(cfgp))
    new = [a for a, why in left if why == "decoded but not split"
           and f"0x{a:06X}" not in cfg["seeds"]]
    skipped = [(a, why) for a, why in left if why != "decoded but not split"]
    for a, why in skipped:
        pass  # false positives, not listed (too many)
    if not new:
        print(f"[seed_missing] done after {rnd} round(s); {len(left)} listed target(s) not seeded (data/false positives; the real signal is the runtime log)")
        break
    for a in new:
        cfg["seeds"][f"0x{a:06X}"] = f"sub_{a:06X}"
    cfg["seeds"] = dict(sorted(cfg["seeds"].items()))
    json.dump(cfg, open(cfgp, "w"), indent=2)
    print(f"[seed_missing] seeded {len(new)} missing call target(s): "
          + " ".join(f"${a:06X}" for a in new[:20]), flush=True)
