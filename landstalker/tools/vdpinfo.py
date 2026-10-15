#!/usr/bin/env python3
"""Summarise a genrecomp --ram-dump file: VDP registers, palette, VRAM use.
Layout: work RAM 64K | VDP regs 32 | CRAM 128 | VSRAM 128 | VRAM 64K."""
import sys

d = open(sys.argv[1], "rb").read()
ram, reg, cram, vsram, vram = d[:0x10000], d[0x10000:0x10020], \
    d[0x10020:0x100A0], d[0x100A0:0x10120], d[0x10120:0x20120]

print(f"file {sys.argv[1]}  ({len(d)} bytes)")
print("VDP regs:", " ".join(f"{i:02d}={b:02X}" for i, b in enumerate(reg[:24])))
r = reg
print(f"display {'ON' if r[1] & 0x40 else 'OFF'}, vint {'on' if r[1] & 0x20 else 'off'}, "
      f"dma {'on' if r[1] & 0x10 else 'off'}, 28-row {bool(r[1] & 8)}, "
      f"40-col {bool(r[12] & 0x81)}, backdrop pal/idx={r[7] >> 4 & 3}/{r[7] & 15}")
print(f"plane A ${(r[2] & 0x38) << 10:04X}  window ${(r[3] & 0x3E) << 10:04X}  "
      f"plane B ${(r[4] & 7) << 13:04X}  sprites ${(r[5] & 0x7F) << 9:04X}  hscroll ${(r[13] & 0x3F) << 10:04X}")

def colors(order):
    out = []
    for i in range(0, 128, 2):
        w = int.from_bytes(cram[i:i + 2], order)
        out.append(w)
    return out

for order in ("big", "little"):
    cs = colors(order)
    nz = [(i, f"{w:04X}") for i, w in enumerate(cs) if w]
    print(f"CRAM as {order}-endian words: {len(nz)} non-zero: {nz[:20]}")

nzb = sum(1 for b in vram if b)
tiles = sum(1 for t in range(0, 0x10000, 32) if any(vram[t:t + 32]))
print(f"VRAM: {nzb} non-zero bytes, {tiles}/2048 tiles non-empty")
for name, base, size in (("plane A", (r[2] & 0x38) << 10, 0x2000), ("plane B", (r[4] & 7) << 13, 0x2000),
                         ("sprites", (r[5] & 0x7F) << 9, 0x280)):
    n = sum(1 for b in vram[base:base + size] if b)
    print(f"  {name} table @ ${base:04X}: {n} non-zero of {size}")
print("VSRAM first 8 bytes:", vsram[:8].hex(" "))
print("work RAM non-zero bytes:", sum(1 for b in ram if b))
