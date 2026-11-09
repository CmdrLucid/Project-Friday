#!/usr/bin/env python3
"""furniture_ops.py ROM [--write] [--rooms a,b,..]
RECURRING FURNITURE for the light (user 2026-11-09: table 670 'ja' + 'auf alle Raeume mit diesem Tisch'): finds every drawn MERCATOR TABLE in the indoor
rooms of tileset 2 by its layer A top blocks (the block that draws a cell's top, tools/blockcat.py cells: back corner $030, right corner $04A,
left corner $04C, front corner $04D or $06E; edges $06A / $04D / $06E) and gives each the measured table of remake/lib/furniture.py
(MERCATOR_TABLE, measured on room 670).  A table counts only as a COMPLETE rectangle: the four corner blocks at the corners of one block of cells
of equal walkable height h (> 0) whose floor around it lies one step lower (h - 1); partial tables at a picture edge are skipped.
Prints one line per room; with --write it writes landstalker/data/proxies/table_ROOM.obj (our own boxes; positions = cell coordinates) and the
op 'mesh' (+ "surface", "air", "floor") into landstalker/data/light_proxies.json (an existing table op of the room is replaced).
Pure Python (no Blender).  Projection check per room: remake/tools/proxy_overlay.py."""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "landstalker", "tools")); sys.path.insert(0, os.path.join(ROOT, "remake", "lib"))
import blockcat, furniture

BACK, RIGHT, LEFT, FRONT = {0x030}, {0x04A}, {0x04C}, {0x04D, 0x06E}
ALL = {0x030, 0x04A, 0x04C, 0x04D, 0x06E, 0x06A}

def boxes_obj(parts, title):
    """flat boxes (proxy part tuples) -> OBJ text, faces outward (as remake/lib/proxy.part_mesh)"""
    v, f = [], []
    for (_n, x0, y0, x1, y1, z0, ze, _zr, _r, _a) in parts:
        b = len(v)
        v += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze)]
        f += [(b, b + 1, b + 5, b + 4), (b + 1, b + 2, b + 6, b + 5), (b + 2, b + 3, b + 7, b + 6), (b + 3, b, b + 4, b + 7), (b, b + 3, b + 2, b + 1), (b + 4, b + 5, b + 6, b + 7)]
    s = "# light proxy: %s (remake/tools/furniture_ops.py, remake/lib/furniture.py). GAME coordinates x east, y south, z up, world units.\n" % title
    s += "# our own geometry (measured table, placed on the cells that draw it); read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n"
    s += "".join("v %g %g %g\n" % p for p in v) + "".join("f " + " ".join(str(k + 1) for k in q) + "\n" for q in f)
    return s

def tables(rom, room):
    c = blockcat.cells(rom, room)
    hgt = lambda x, y: c[(x, y)][0] if (x, y) in c else 0
    found = []
    for (x0, y0), v in c.items():
        if v[2] not in BACK: continue
        x1 = x0
        while c.get((x1 + 1, y0), (0, 0, 0))[2] in ALL: x1 += 1
        y1 = y0
        while c.get((x0, y1 + 1), (0, 0, 0))[2] in ALL: y1 += 1
        h = v[0]
        ok = (c.get((x1, y0), (0, 0, 0))[2] in RIGHT and c.get((x0, y1), (0, 0, 0))[2] in LEFT and c.get((x1, y1), (0, 0, 0))[2] in FRONT and h > 0
              and all(hgt(x, y) == h and not c[(x, y)][1] for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) if (x, y) in c)
              and all((x, y) in c for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)))
        ring = [hgt(x, y) for x in range(x0 - 1, x1 + 2) for y in (y0 - 1, y1 + 1)] + [hgt(x, y) for y in range(y0, y1 + 1) for x in (x0 - 1, x1 + 1)]
        floor = collections.Counter(ring).most_common(1)[0][0]
        found.append(dict(cells=(x0, y0, x1, y1), h=h, floor=floor, ok=ok and floor == h - 1))
    return found

def main():
    a = [s for s in sys.argv[1:] if not s.startswith("--")]
    rom = open(a[0], "rb").read(); write = "--write" in sys.argv
    rooms = [int(r) for r in sys.argv[sys.argv.index("--rooms") + 1].split(",")] if "--rooms" in sys.argv else [r for r in range(816) if blockcat.tileset(rom, r) == 2]
    jp = os.path.join(ROOT, "landstalker", "data", "light_proxies.json"); data = json.load(open(jp), object_pairs_hook=collections.OrderedDict)
    n = 0
    for r in rooms:
        try: ts = tables(rom, r)
        except Exception as e: print("room %d: skipped (%s)" % (r, e)); continue
        good = [t for t in ts if t["ok"]]
        for t in ts: print("room %d: table cells %d..%d x %d..%d height %d floor %d %s" % (r, t["cells"][0], t["cells"][2], t["cells"][1], t["cells"][3], t["h"], t["floor"], "OK" if t["ok"] else "SKIPPED (incomplete / not one step above the floor)"))
        if not good or not write: continue
        parts = []
        for k, t in enumerate(good):
            x0, y0, x1, y1 = t["cells"]
            parts += furniture.table("table%d" % k, 16 * x0, 16 * y0, 16 * x1 + 16, 16 * y1 + 16, 16 * t["floor"], 16 * t["h"], **furniture.MERCATOR_TABLE)
        fn = "table_%d.obj" % r
        open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w").write(boxes_obj(parts, "Mercator table(s), room %d" % r))
        ops = [e for e in data["rooms"].get(str(r), []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/table_"))]
        for t in good:
            x0, y0, x1, y1 = t["cells"]
            ops.append(collections.OrderedDict([("op", "mesh"), ("cells", [x0, y0, x1, y1]), ("file", "proxies/" + fn), ("surface", True), ("air", True), ("floor", 16 * t["floor"]),
                ("why", "table on legs (collision = a solid box): the measured Mercator table (remake/lib/furniture.py MERCATOR_TABLE, room 670), placed by remake/tools/furniture_ops.py; user 2026-11-09 'beides ja'")]))
        data["rooms"][str(r)] = ops; n += 1
    if write:
        data["rooms"] = collections.OrderedDict(sorted(data["rooms"].items(), key=lambda t: int(t[0])))
        open(jp, "w").write(json.dumps(data, indent=2, ensure_ascii=False) + "\n"); print("written: %d rooms" % n)

if __name__ == "__main__":
    main()
