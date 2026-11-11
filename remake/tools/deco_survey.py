#!/usr/bin/env python3
"""deco_survey.py ROM OUTDIR [--top N] [--todo] [--max N]
SURVEY of recurring decoration objects (vases, barrels, chests, beds, ...) in the INDOOR rooms, for the light proxies (like the tables of furniture_ops.py).
A group = 4-connected cells that are blocked or stand above the room floor (floor = most common walkable height), are not part of the wall (blocked
height-0 cells connected to the rim of the map) and not covered by a 'proxies/table_' mesh op of data/light_proxies.json.  Groups up to 4 x 4 cells, height
<= 4 steps.  Signature = (tileset, top layer A block ids [layer B ids when A is 0], w x d, height).  Writes OUTDIR/survey.txt (ranked list), OUTDIR/sig_N.png
(crop of one example, x3) and OUTDIR/sheet_K.png (contact sheets, rank number drawn in each tile).  Local only; pure Python, no ROM data inside."""
import os, sys, json, collections, zlib, struct
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "landstalker", "tools"))
import blockcat, romrender

D3x5 = {'0': "111101101101111", '1': "010110010010111", '2': "111001111100111", '3': "111001111001111", '4': "101101111001001",
        '5': "111100111001111", '6': "111100111101111", '7': "111001001010010", '8': "111101111101111", '9': "111101111001111", '#': "101111101111101"}

def png(path, w, h, rgb):
    raw = b''.join(b'\x00' + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    def c(t, d): x = struct.pack('>I', len(d)) + t + d; return x + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + c(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + c(b'IDAT', zlib.compress(raw, 6)) + c(b'IEND', b''))

def scale(w, h, px, k):
    out = bytearray(w * k * h * k * 3)
    for y in range(h * k):
        for x in range(w * k):
            o = (y * w * k + x) * 3; q = ((y // k) * w + x // k) * 3; out[o:o + 3] = px[q:q + 3]
    return out

def label(img, W, x0, y0, text, k=3):
    for n, ch in enumerate(text):
        g = D3x5[ch]
        for i in range(15):
            if g[i] == '1':
                for dy in range(k):
                    for dx in range(k):
                        o = ((y0 + (i // 3) * k + dy) * W + x0 + n * 4 * k + (i % 3) * k + dx) * 3; img[o:o + 3] = b'\xff\xff\x00'

def table_cells(data, r):
    s = set()
    for e in data["rooms"].get(str(r), []):
        if e.get("op") == "mesh" and (ALLMESH or e.get("file", "").startswith("proxies/table_")):   # --todo: every mesh op counts as done
            x0, y0, x1, y1 = e["cells"][:4]; s |= {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}
    return s

ALLMESH = "--todo" in sys.argv   # --todo: leave out the cells of EVERY mesh op (what is still without a light shape)
MAXG = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 4   # --max N: groups up to N x N cells (default 4; 8 also finds counters, shelves, hearths)
BL = []   # (tileset, room, [(cell, h, top block)], floor) of every kept group, for the per-block ranking

def groups(rom, r, tabs):
    c = blockcat.cells(rom, r)
    if not c: return []
    xs = [k[0] for k in c]; ys = [k[1] for k in c]; X0, X1, Y0, Y1 = min(xs), max(xs), min(ys), max(ys)
    # NOTE blockcat.cells() omits cells whose height-map word is 0 = plain walkable floor at height 0: they count as floor h 0 here
    walk = collections.Counter(v[0] for v in c.values() if not v[1]); walk[0] += sum(1 for x in range(X0, X1 + 1) for y in range(Y0, Y1 + 1) if (x, y) not in c)
    floor = walk.most_common(1)[0][0]
    # wall = blocked height-0 cells connected to the rim (cells missing from the map count as rim)
    wallc = {k for k, v in c.items() if v[1] and v[0] == 0}
    wall, todo = set(), [k for k in wallc if k[0] in (X0, X1) or k[1] in (Y0, Y1)]
    while todo:
        k = todo.pop()
        if k in wall or k not in wallc: continue
        wall.add(k); todo += [(k[0] + 1, k[1]), (k[0] - 1, k[1]), (k[0], k[1] + 1), (k[0], k[1] - 1)]
    cand = {k for k, v in c.items() if (v[1] or v[0] > floor) and k not in wall and k not in tabs}
    out, seen = [], set()
    for k0 in sorted(cand):
        if k0 in seen: continue
        comp, todo = set(), [k0]
        while todo:
            k = todo.pop()
            if k in comp or k not in cand: continue
            comp.add(k); todo += [(k[0] + 1, k[1]), (k[0] - 1, k[1]), (k[0], k[1] + 1), (k[0], k[1] - 1)]
        seen |= comp
        xs = [k[0] for k in comp]; ys = [k[1] for k in comp]; w = max(xs) - min(xs) + 1; d = max(ys) - min(ys) + 1
        hh = max(c[k][0] for k in comp) - floor
        if w > MAXG or d > MAXG or hh > 4 or hh < 1: continue
        A = sorted({c[k][2] for k in comp if c[k][2]}); B = sorted({c[k][3] for k in comp}) if not A else []
        sig = (blockcat.tileset(rom, r), tuple(A), tuple(B), w, d, hh)
        BL.append((blockcat.tileset(rom, r), r, [(k, c[k][0], c[k][2] or c[k][3]) for k in sorted(comp)], floor))
        out.append((sig, r, min(xs), min(ys), len(comp), floor, bool(any((k[0] + dx, k[1] + dy) in wall for k in comp for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))))))
    return out

def main():
    a = [s for s in sys.argv[1:] if not s.startswith("--")]; top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 40
    if "--top" in sys.argv: a = [s for s in a if s != str(top)]
    if "--max" in sys.argv: a = [s for s in a if s != str(MAXG)] if len(a) > 2 else a
    rom = open(a[0], "rb").read(); od = a[1]; os.makedirs(od, exist_ok=True)
    data = json.load(open(os.path.join(ROOT, "landstalker", "data", "light_proxies.json")))
    outdoor = set(blockcat.outdoor_rooms(rom)); sigs = collections.defaultdict(list)
    for r in range(816):
        if r in outdoor: continue
        try: g = groups(rom, r, table_cells(data, r))
        except Exception as e: print("room %d skipped (%s)" % (r, e)); continue
        for sig, rr, x, y, n, fl, tw in g: sigs[sig].append((rr, x, y, n, fl, tw))
    rank = sorted(sigs.items(), key=lambda t: (-len({e[0] for e in t[1]}), -len(t[1])))[:top]
    tiles = []
    with open(os.path.join(od, "survey.txt"), "w") as f:
        for n, (sig, ex) in enumerate(rank, 1):
            rooms = sorted({e[0] for e in ex}); e0 = sorted(ex, key=lambda e: e[3] != max(x[3] for x in ex))[0]
            line = "%2d ts%d A=%s B=%s %dx%dx%d rooms=%d total=%d ex=room %d cell %d,%d cells=%d touchwall=%s rooms:%s" % (n, sig[0], "/".join("%03X" % b for b in sig[1]), "/".join("%03X" % b for b in sig[2]), sig[3], sig[4], sig[5], len(rooms), len(ex), e0[0], e0[1], e0[2], e0[3], e0[5], ",".join(map(str, rooms[:12])))
            print(line); f.write(line + "\n")
            r, x, y, fl = e0[0], e0[1], e0[2], e0[4]; hh = sig[5]
            cx, cy = x + (sig[3] - 1) / 2.0, y + (sig[4] - 1) / 2.0   # window centred on the group's middle (floor level + half the height)
            u = int(16 * (cx - cy) + 1184 + 8 - 48); v = int(8 * (cx + cy) + 8 - 16 * (fl + hh) - 8 - 48)
            g, rr, pa, pb, getpal = romrender.rom_planes(rom, r)
            px = romrender.compose(pa, pb, getpal, u, v, 96, 96, romrender.md_to_rgb(0), g['tiles'])
            img = scale(96, 96, px, 3); W = 288; label(img, W, 3, 3, str(n))
            png(os.path.join(od, "sig_%02d.png" % n), W, W, img); tiles.append(img)
    sheets(od, tiles, "sheet")
    # per-BLOCK ranking: how many rooms draw this top block (alone or in a group) inside kept groups; sheet_b: one example cell each
    cnt = collections.defaultdict(list)
    for ts, r, cs, fl in BL:
        for (k, h, b) in cs: cnt[(ts, b)].append((r, k, h, fl))
    rb = sorted(cnt.items(), key=lambda t: (-len({e[0] for e in t[1]}), -len(t[1])))[:top]; bt = []
    with open(os.path.join(od, "survey_blocks.txt"), "w") as f:
        for n, ((ts, b), ex) in enumerate(rb, 1):
            r, k, h, fl = ex[len(ex) // 2]; line = "%2d ts%d block $%03X cells=%d rooms=%d ex=room %d cell %d,%d h=%d(+%d)" % (n, ts, b, len(ex), len({e[0] for e in ex}), r, k[0], k[1], h, fl); print(line); f.write(line + "\n")
            u = int(16 * (k[0] - k[1]) + 1184 + 8 - 48); v = int(8 * (k[0] + k[1]) + 8 - 16 * h - 8 - 48)
            g, rr, pa, pb, getpal = romrender.rom_planes(rom, r)
            img = scale(96, 96, romrender.compose(pa, pb, getpal, u, v, 96, 96, romrender.md_to_rgb(0), g['tiles']), 3); label(img, 288, 3, 3, str(n)); bt.append(img)
    sheets(od, bt, "sheet_b")
    print("done: %d signatures ranked, sheets in %s" % (len(rank), od))

def sheets(od, tiles, name):
    per = 12; cols = 4; W = 288
    for s in range(0, len(tiles), per):
        part = tiles[s:s + per]; rows = (len(part) + cols - 1) // cols; SW, SH = cols * (W + 4), rows * (W + 4); sheet = bytearray(b'\x20' * SW * SH * 3)
        for k, t in enumerate(part):
            ox, oy = (k % cols) * (W + 4), (k // cols) * (W + 4)
            for yy in range(W): sheet[((oy + yy) * SW + ox) * 3:((oy + yy) * SW + ox + W) * 3] = t[yy * W * 3:(yy + 1) * W * 3]
        png(os.path.join(od, "%s_%d.png" % (name, s // per + 1)), SW, SH, sheet)

if __name__ == "__main__":
    main()
