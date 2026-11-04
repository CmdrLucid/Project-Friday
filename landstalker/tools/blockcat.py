#!/usr/bin/env python3
"""blockcat.py ROM stats [TILESET] [--top N]            -- which layer A (object) blocks draw the TOP of map cells, per outdoor tileset
   blockcat.py ROM sheet TILESET OUT.png [--top N] [--ids a,b,..]  -- contact sheet: every block alone (4 x, grey = transparent) + in its picture (red frame), 4 per row, order printed
   blockcat.py ROM cells ROOM                             -- per cell of a room: the class from data/object_blocks.json (text grid, for checks)
Catalogue of RECURRING OBJECTS for the light proxies (docs/LIGHT_PROXY_PLAN.md 'Object catalogue', user 2026-11-04: 'nicht nur eine Bush detection, generell
etwas fuer wiederkehrende Objekte'): rooms are built from 16 x 16 graphics blocks; the blockset belongs to the TILESET (room table byte 4 & $1F), so the
same object (bush, pine, ...) is the same block id in every room of a tileset. The block that draws the top of cell (x, y) at height h (in steps) is the
layer A block at (x - h, y - h) (FORMATS 'Block map': block (x, y) at picture U = 16 (x - y) + 1168, V = 8 (x + y); a cell top at U = 16 (x - y) + 1184,
V = 8 (x + y) - 16 h).  Local test aid: ROM pictures stay on the Deck (never commit the sheets)."""
import collections, json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import romroom, romrender

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = os.path.join(HERE, "..", "data", "object_blocks.json")
OUTDOOR = (0, 7, 12, 13, 14, 17)

def room_table(rom):
    return struct.unpack('>I', rom[0xA0A00:0xA0A04])[0]

def tileset(rom, room):
    return rom[room_table(rom) + 8 * room + 4] & 0x1F

def outdoor_rooms(rom, ts=None):
    return [r for r in range(816) if tileset(rom, r) in OUTDOOR and (ts is None or tileset(rom, r) == ts) and not (139 <= r <= 143) and r not in (148, 643)]

_arr = {}
def arrays(rom, room):
    if room not in _arr:
        try: _arr[room] = romroom.arrays(romroom.decode(rom, room))
        except Exception: _arr[room] = None
    return _arr[room]

def cells(rom, room):
    """{(x, y): (h steps, blocked, top layer A block id, top layer B block id)} in world cells (= RAM index, height map index + 12)"""
    a = arrays(rom, room)
    if not a: return {}
    out, claim = {}, {}
    for (x, y), v in a['HM'].items():
        if not v: continue
        X, Y, h = x + 12, y + 12, (v >> 8) & 15
        out[(X, Y)] = [h, bool((v >> 8) & 0x60), 0, 0]
        k = (X - h, Y - h)   # several cells lie on the same view diagonal: the block shows the top of the one nearest the viewer (the highest)
        if k not in claim or h > out[claim[k]][0]: claim[k] = (X, Y)
    for (bx, by), c in claim.items():
        out[c][2] = a['FG'].get((bx, by), 0) & 0x3FF; out[c][3] = a['BG'].get((bx, by), 0) & 0x3FF
    return {k: tuple(v) for k, v in out.items()}

def stats(rom, ts, top):
    cnt = collections.Counter(); raised = collections.Counter(); blocked = collections.Counter(); rooms = collections.defaultdict(set); ex = {}
    for r in outdoor_rooms(rom, ts):
        c = cells(rom, r)
        for (x, y), (h, b, fa, fb) in c.items():
            if not fa: continue
            nb = [c[(x + dx, y + dy)][0] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, y + dy) in c]
            cnt[fa] += 1; rooms[fa].add(r)
            if b: blocked[fa] += 1
            if nb and h > min(nb): raised[fa] += 1
            ex.setdefault(fa, collections.Counter())[(r, x, y, h)] += 0
    rows = [(n, i, raised[i], blocked[i], len(rooms[i])) for i, n in cnt.most_common(top)]
    return rows, ex

def example(rom, ts, bid):
    """a (room, x, y, h) whose top block is bid, from the room of this tileset that uses it most"""
    best = None
    for r in outdoor_rooms(rom, ts):
        hits = [(x, y, h) for (x, y), (h, b, fa, fb) in cells(rom, r).items() if fa == bid]
        if hits and (best is None or len(hits) > best[0]): best = (len(hits), r, hits[len(hits) // 2])
    return (best[1],) + best[2] if best else None

_pl = {}
def alone(rom, room, bx, by, S=4):
    """the layer A block by itself (16 x 16, S times), grey where it is transparent"""
    if room not in _pl: _pl[room] = romrender.rom_planes(rom, room)
    g, r, pa, pb, getpal = _pl[room]
    pix = romrender.compose(pa, romrender.Plane(), getpal, 16 * (bx - by) + 1168, 8 * (bx + by), 16, 16, (90, 90, 90), g['tiles'])
    out = bytearray(16 * S * 16 * S * 3)
    for y in range(16 * S):
        for x in range(16 * S):
            q = ((y // S) * 16 + x // S) * 3; o = (y * 16 * S + x) * 3; out[o:o + 3] = pix[q:q + 3]
    return out

def crop(rom, room, bx, by, W=64, S=2):
    if room not in _pl: _pl[room] = romrender.rom_planes(rom, room)
    g, r, pa, pb, getpal = _pl[room]
    u = 16 * (bx - by) + 1168 + 8 - W // 2; v = 8 * (bx + by) + 8 - W // 2
    pix = romrender.compose(pa, pb, getpal, u, v, W, W, romrender.md_to_rgb(0), g['tiles'])
    out = bytearray(W * S * W * S * 3)
    for y in range(W * S):
        for x in range(W * S):
            q = ((y // S) * W + x // S) * 3; c = pix[q:q + 3]
            fx, fy = x // S - (W // 2 - 8), y // S - (W // 2 - 8)   # the block's own 16 x 16 square: red frame
            if (fx in (-1, 16) and -1 <= fy <= 16) or (fy in (-1, 16) and -1 <= fx <= 16): c = b'\xff\x30\x30'
            o = (y * W * S + x) * 3; out[o:o + 3] = c
    return out, W * S

def sheet(rom, ts, path, ids):
    tiles = []
    for i, bid in enumerate(ids):
        e = example(rom, ts, bid)
        if not e: continue
        room, x, y, h = e
        ctx, s = crop(rom, room, x - h, y - h); one = alone(rom, room, x - h, y - h)
        img = bytearray(b'\x20' * (s + 68) * s * 3)   # the block alone (4 x) at the left, its picture around it (2 x, red frame) at the right
        for yy in range(s):
            o = yy * (s + 68) * 3
            if yy < 64: img[o:o + 64 * 3] = one[yy * 64 * 3:(yy + 1) * 64 * 3]
            img[o + 68 * 3:o + (68 + s) * 3] = ctx[yy * s * 3:(yy + 1) * s * 3]
        tiles.append((bid, room, x, y, h, img, s))
        print("%2d  block $%03X  room %d cell %d,%d height %d" % (len(tiles) - 1, bid, room, x, y, h), flush=True)
    cols = 4; s = tiles[0][6] if tiles else 128; tw = s + 68; pad = 6; rowsn = (len(tiles) + cols - 1) // cols
    Wt, Ht = cols * (tw + pad), rowsn * (s + pad); out = bytearray(b'\x20' * Wt * Ht * 3)
    for k, t in enumerate(tiles):
        ox, oy = (k % cols) * (tw + pad), (k // cols) * (s + pad)
        for y in range(s):
            o = ((oy + y) * Wt + ox) * 3; out[o:o + tw * 3] = t[5][y * tw * 3:(y + 1) * tw * 3]
    romrender.png(path, Wt, Ht, out)
    print("blockcat: %d blocks -> %s" % (len(tiles), path))

def classify(rom, room):
    cat = json.load(open(CAT)); ts = str(tileset(rom, room)); m = {}
    for cls, ids in cat.get("tilesets", {}).get(ts, {}).items():
        for i in ids: m[int(i, 16) if isinstance(i, str) else i] = cls
    return {k: m.get(v[2]) for k, v in cells(rom, room).items()}

if __name__ == "__main__":
    a = sys.argv[1:]
    rom = open(a[0], "rb").read(); cmd = a[1]
    top = int(a[a.index("--top") + 1]) if "--top" in a else 40
    if cmd == "stats":
        for ts in ([int(a[2])] if len(a) > 2 and not a[2].startswith("-") else OUTDOOR):
            rows, _ = stats(rom, ts, top)
            print("tileset %d (%d rooms): block  cells  raised  blocked  rooms" % (ts, len(outdoor_rooms(rom, ts))))
            for n, i, ra, bl, nr in rows: print("   $%03X  %5d  %6d  %7d  %5d" % (i, n, ra, bl, nr))
    elif cmd == "sheet":
        ts = int(a[2]); ids = [int(v, 16) for v in a[a.index("--ids") + 1].split(",")] if "--ids" in a else [i for _, i, _, _, _ in stats(rom, ts, top)[0]]
        sheet(rom, ts, a[3], ids)
    elif cmd == "cells":
        room = int(a[2]); c = classify(rom, room); ab = {"bush": "B", "pine": "P", "tree": "T", "flat": "f"}
        xs = [k[0] for k in c]; ys = [k[1] for k in c]
        for y in range(min(ys), max(ys) + 1):
            print("%2d " % y + "".join(ab.get(c.get((x, y)), "." if (x, y) in c else " ") if c.get((x, y)) is None or c.get((x, y)) in ab else "?" for x in range(min(xs), max(xs) + 1)))
