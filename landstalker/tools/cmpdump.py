#!/usr/bin/env python3
"""Compare two directories of genrecomp --ram-dump files frame by frame.
usage: cmpdump.py REF_DIR RECOMP_DIR
Layout: work RAM 64K | VDP regs 32 | CRAM 128 | VSRAM 128 | VRAM 64K."""
import os, sys

def split(d):
    return {"ram": d[:0x10000], "reg": d[0x10000:0x10020], "cram": d[0x10020:0x100A0],
            "vsram": d[0x100A0:0x10120], "vram": d[0x10120:0x20120]}

def ranges(a, b, gap=16, limit=6):
    out, start, last = [], None, None
    for i in range(len(a)):
        if a[i] != b[i]:
            if start is None: start = i
            elif i - last > gap:
                out.append((start, last)); start = i
            last = i
    if start is not None: out.append((start, last))
    return [f"${s:04X}-${e:04X}" for s, e in out[:limit]] + (["..."] if len(out) > limit else [])

ref_dir, rec_dir = sys.argv[1:3]
START = int(sys.argv[3]) if len(sys.argv) > 3 else 0
names = [n for n in sorted(set(os.listdir(ref_dir)) & set(os.listdir(rec_dir))) if int(n[4:10]) >= START]
first_bad = None
first_gfx = None
for n in names:
    r = split(open(os.path.join(ref_dir, n), "rb").read())
    c = split(open(os.path.join(rec_dir, n), "rb").read())
    diffs = {k: sum(x != y for x, y in zip(r[k], c[k])) for k in r}
    tag = "same" if not any(diffs.values()) else "DIFF"
    print(f"{n}: {tag}  " + "  ".join(f"{k}={v}" for k, v in diffs.items()))
    if tag == "DIFF" and first_bad is None:
        first_bad = n
        print("   regs differ at:", [f"{i:02d}: ref {r['reg'][i]:02X} recomp {c['reg'][i]:02X}"
                                      for i in range(32) if r['reg'][i] != c['reg'][i]][:8])
        tiles = [t for t in range(0, 0x10000, 32) if r["vram"][t:t+32] != c["vram"][t:t+32]]
        print(f"   VRAM tiles differing: {len(tiles)}; first: {[hex(t // 32) for t in tiles[:12]]}")
        print("   VRAM byte ranges:", ranges(r["vram"], c["vram"]))
        print("   work RAM ranges :", ranges(r["ram"], c["ram"]))
        print("   CRAM first diffs:", [(i // 2, r["cram"][i:i+2].hex(), c["cram"][i:i+2].hex())
                                       for i in range(0, 128, 2) if r["cram"][i:i+2] != c["cram"][i:i+2]][:6])
    if first_gfx is None and (diffs["vram"] or diffs["cram"] or diffs["vsram"]):
        first_gfx = n
        print(f"   >>> FIRST GRAPHICS DIFFERENCE in {n}")
        tiles = [t for t in range(0, 0x10000, 32) if r["vram"][t:t+32] != c["vram"][t:t+32]]
        print(f"   VRAM tiles differing: {len(tiles)}; first: {[hex(t // 32) for t in tiles[:12]]}")
        print("   VRAM byte ranges:", ranges(r["vram"], c["vram"]))
        print("   CRAM diffs:", [(i // 2, "ref", r["cram"][i:i+2].hex(), "recomp", c["cram"][i:i+2].hex()) for i in range(0, 128, 2) if r["cram"][i:i+2] != c["cram"][i:i+2]][:6])
        rd = [(i, r["ram"][i], c["ram"][i]) for i in range(0x10000) if r["ram"][i] != c["ram"][i]]
        print(f"   work RAM differs in {len(rd)} bytes; ranges:", ranges(r["ram"], c["ram"], gap=8, limit=12))
        print("   first RAM diffs (addr ref recomp):", [f"{0xFF0000 + a:06X} {x:02X} {y:02X}" for a, x, y in rd[:16]])
        if tiles:
            t = tiles[0]
            print(f"   tile {t // 32:#x} ref   : {r['vram'][t:t+32].hex()}")
            print(f"   tile {t // 32:#x} recomp: {c['vram'][t:t+32].hex()}")
print("first differing dump:", first_bad or "none", " first graphics diff:", first_gfx or "none")
