#!/usr/bin/env python3
"""Turn the disassembly's label names into ROM addresses without assembling it.

tools/xrefs.json (made by tools/extract_xrefs.py from the disassembly's cross-reference comments) lists, per named label, the ROM
addresses of instructions that reference it. This tool decodes those instructions in YOUR ROM (bsr/bra/bcc, jsr/jmp abs/pc, lea d16(pc))
and takes the target. A label is accepted when all resolvable references agree. Address-named labels (loc_25400 ...) in the
'calibration' list must resolve to their own address: the hit rate is printed as a self-check (expect ~100%).

usage: symbolize.py ROM [out.json]   (default: docs/symbols_auto.json)  ; merge good ones into docs/symbols.json by hand/with --merge
"""
import json, os, re, sys

here = os.path.dirname(os.path.abspath(__file__))
rom = open(sys.argv[1], "rb").read()
out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "..", "docs", "symbols_auto.json")
X = json.load(open(os.path.join(here, "xrefs.json")))
w = lambda a: (rom[a] << 8) | rom[a + 1]
sx = lambda v, bits: v - (1 << bits) if v & (1 << (bits - 1)) else v

def target(a, kind):
    """address referenced by the instruction at a, or None"""
    if a < 0 or a + 6 > len(rom) or a & 1:
        return None
    op = w(a)
    if op & 0xF000 == 0x6000:                                  # bra/bsr/bcc
        d = op & 0xFF
        if d == 0:
            return a + 2 + sx(w(a + 2), 16)
        if d == 0xFF:
            return a + 2 + sx((w(a + 2) << 16) | w(a + 4), 32)
        return a + 2 + sx(d, 8)
    if op in (0x4EB9, 0x4EF9):                                 # jsr/jmp abs.l
        return (w(a + 2) << 16) | w(a + 4)
    if op in (0x4EB8, 0x4EF8):
        return sx(w(a + 2), 16) & 0xFFFFFF
    if op in (0x4EBA, 0x4EFA) or op & 0xF1FF == 0x41FA:      # jsr/jmp d16(pc), lea d16(pc),An
        return a + 2 + sx(w(a + 2), 16)
    if op & 0xF1FF == 0x41F8:                                   # lea abs.w,An
        return sx(w(a + 2), 16) & 0xFFFFFF
    if op & 0xF1FF == 0x41F9:                                   # lea abs.l,An
        return (w(a + 2) << 16) | w(a + 4)
    if kind == "t" and (op & 0xF1FF in (0x203C, 0x223C, 0x243C) or op in (0x203C, 0x223C, 0x243C, 0x2E3C, 0x23FC, 0x21FC)):
        return (w(a + 2) << 16) | w(a + 4)
    return None

def resolve(refs):
    ts = [target(a, k) for a, k in refs]
    ts = [t for t in ts if t is not None and 0 < t < len(rom) and not t & 1]
    if not ts:
        return None, 0, 0
    best = max(set(ts), key=ts.count)
    return best, ts.count(best), len(ts)

ok = tot = 0
for name, refs in X["calibration"].items():
    m = re.search(r"_([0-9A-F]+)$", name)
    t, n, tot_ref = resolve(refs)
    if t is None or not m:
        continue
    tot += 1
    ok += t == int(m.group(1), 16)
print(f"symbolize: calibration {ok}/{tot} address-named labels resolve to their own address ({100 * ok // max(tot, 1)}%)")

res, conflicts, none = {}, [], 0
for name, refs in X["named"].items():
    t, n, tot_ref = resolve(refs)
    if t is None:
        none += 1
    elif n < tot_ref:
        conflicts.append((name, t, n, tot_ref))
        if n * 2 > tot_ref:
            res["0x%06X" % t] = {"name": name, "refs": n, "of": tot_ref, "confidence": "auto-majority"}
    else:
        res["0x%06X" % t] = {"name": name, "refs": n, "of": tot_ref, "confidence": "auto-all-agree"}
json.dump(dict(sorted(res.items())), open(out_path, "w"), indent=1)
print(f"symbolize: {len(res)} named addresses written to {out_path}; {none} labels unresolved, {len(conflicts)} with disagreeing references")
for c in conflicts[:10]:
    print("  conflict:", c)
for k in ("0x0253F8", "0x0253CA"):
    print(f"symbolize: {k} = {res.get(k, {}).get('name')}")
