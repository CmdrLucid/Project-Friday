#!/usr/bin/env python3
"""Sum the LANDSTALKER_VDPCOUNT lines of several runs (tools/patch_vdpcount.py, SOUND_PLAN section 12 step 3.0).
Counters 'a/b/c' are summed per field.  reg<N> = all / value changed / display on / DMA busy; dma_<kind> = chunks / bytes.
usage: tools/vdpcount_sum.py FILE [--per-run]"""
import sys

def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    tot, runs, nz = {}, 0, {}
    for ln in open(sys.argv[1]):
        p = ln.split()
        if not p: continue
        runs += 1
        for kv in p[1:]:
            k, v = kv.split("=", 1); vals = [int(x) for x in v.split("/")]
            t = tot.setdefault(k, [0] * len(vals))
            for i, x in enumerate(vals): t[i] += x
            if vals[0]: nz[k] = nz.get(k, 0) + 1
        if "--per-run" in sys.argv: print(ln.rstrip())
    print("runs:", runs)
    def key(k):
        import re
        m = re.match(r"([a-z_]+?)(\d+)$", k)
        return (m.group(1), int(m.group(2))) if m else (k, -1)
    for k in sorted(tot, key=key):
        print("%-22s %-40s (in %d runs)" % (k, "/".join(str(x) for x in tot[k]), nz.get(k, 0)))

if __name__ == "__main__": main()
