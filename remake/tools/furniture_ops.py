#!/usr/bin/env python3
"""furniture_ops.py ROM [--write] [--rooms a,b,..]
RECURRING FURNITURE ON LEGS for the light (user 2026-11-09: table 670 "ja", then "1 und 2"): finds every drawn piece of the TYPES below (tables, benches, side tables, castle tables) in the indoor
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

# FURNITURE TYPES: the layer A top blocks that draw the piece (any of them per cell), the blocks one of which must be in it (else a fragment), the measured shape
def mercator_ok(blk, x0, y0, x1, y1):   # the TOP blocks alone do not tell legs from a solid front ($0A3 is also the top of the shop counter of 668 / 669,
    w, d = x1 - x0 + 1, y1 - y0 + 1    # $030 also tops the solid chest of 618 / 619 / 675): only the arrangements checked on the drawings count
    if blk(x0, y0) == 0x030: return w >= 2 and d >= 2                                   # table on legs, 2 x 2 .. 4 x 3
    if blk(x0, y0) == 0x0A3: return w == 1 and d >= 2 and blk(x1, y1) == 0x04C          # bench on legs: $0A3 run ending in the table corner piece $04C (623 / 624 / 701 / 702)
    if blk(x0, y0) == 0x18A: return w == 1 and d == 1                                   # the side table by the hearth (691 / 692 / 713 / 714)
    return False

# FURNITURE TYPES ON LEGS: the layer A top blocks that draw the piece (any of them per cell), the arrangement check, the measured shape
TYPES = [
    dict(name="mercator table / bench / side table", ts=2, blocks={0x030, 0x04A, 0x04C, 0x04D, 0x06E, 0x06A, 0x0A3, 0x18A, 0x312, 0x313, 0x314}, ok=mercator_ok,
         shape=furniture.MERCATOR_TABLE),   # $312..$314 = the middle row of the 4 x 3 table (722 / 723)
    dict(name="castle table", ts=1, blocks={0x114, 0x115, 0x116, 0x148, 0x149, 0x0EF, 0x119, 0x10B}, ok=lambda blk, x0, y0, x1, y1: blk(x0, y0) == 0x114,
         shape=furniture.CASTLE_TABLE),
]

# PAINTED SHADOWS UNDER THE PIECES (user 2026-11-09: 'der Schatten unterm Tisch ist schon im Sprite drin ... den Teppich unter dem Tisch im normalen
# Gruen zeichnen, so dass der Tisch nur unseren Schatten wirft'): per tileset the plane B tiles the artist drew with the shadow -> the same tile without
# it (checked on the drawings, ~/lktest/unsh/try.py): carpet under the Mercator tables $34C / $34D / $35B / $35C / $35D (green index 14 -> olive 2;
# used NOWHERE else in tileset 2) -> plain carpet $367; stone floor in shadow $04B / $04C / $05C -> plain floor $006 (these three are ALSO the
# shadows of beds / walls elsewhere, so only on a piece's floor footprint).  The game draws them at runtime (LK_GLUNPAINT v1, GPU light only).
UNPAINT_TILES = {2: {0x34C: 0x367, 0x34D: 0x367, 0x35B: 0x367, 0x35C: 0x367, 0x35D: 0x367, 0x04B: 0x006, 0x04C: 0x006, 0x05C: 0x006}}

def unpaint_hits(rom, room, ts, cells, floor):
    """number of plane B cells with a painted shadow tile on the floor footprint of the cells (romrender, the same walk as lk_gl_unpaint)"""
    import romrender
    rep = UNPAINT_TILES.get(ts, {}); pb = romrender.rom_planes(rom, room)[3]; x0, y0, x1, y1 = cells; hit = set()
    for Y in range(16 * y0, 16 * y1 + 16, 2):
        for X in range(16 * x0, 16 * x1 + 16, 2):
            k = ((X - Y + 1184) >> 3, ((X + Y) // 2 - floor) >> 3); t = pb.t.get(k)
            if t and t[0] in rep: hit.add(k)
    return len(hit)

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
    """complete pieces of every TYPE of the room's tileset: a 4-connected group of walkable cells drawn by the type's blocks that fills its bounding
    box, has one equal height h > 0, passes the type's arrangement check and stands one step above the floor ring around it (fragments are skipped)"""
    c = blockcat.cells(rom, room); ts = blockcat.tileset(rom, room)
    hgt = lambda x, y: c[(x, y)][0] if (x, y) in c else 0
    found = []
    for T in TYPES:
        if T["ts"] != ts: continue
        cell = {k for k, v in c.items() if v[2] in T["blocks"] and not v[1]}
        seen = set()
        for k0 in sorted(cell):
            if k0 in seen: continue
            comp, todo = set(), [k0]
            while todo:
                k = todo.pop()
                if k in comp or k not in cell: continue
                comp.add(k); todo += [(k[0] + 1, k[1]), (k[0] - 1, k[1]), (k[0], k[1] + 1), (k[0], k[1] - 1)]
            seen |= comp
            xs = [k[0] for k in comp]; ys = [k[1] for k in comp]; x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            hs = {hgt(*k) for k in comp}; h = hs.pop() if len(hs) == 1 else -1
            ring = [hgt(x, y) for x in range(x0 - 1, x1 + 2) for y in (y0 - 1, y1 + 1)] + [hgt(x, y) for y in range(y0, y1 + 1) for x in (x0 - 1, x1 + 1)]
            floor = collections.Counter(ring).most_common(1)[0][0]
            ok = (len(comp) == (x1 - x0 + 1) * (y1 - y0 + 1) and h > 0 and floor == h - 1 and T["ok"](lambda x, y: c.get((x, y), (0, 0, 0))[2], x0, y0, x1, y1))
            blk = lambda x, y: c.get((x, y), (0, 0, 0))[2]
            arm = None   # the L bench (623 / 624 / 701 / 702): a bench whose back end turns west, corner $144 + arm end $36D at the same height
            if ok and blk(x0, y0) == 0x0A3 and blk(x0, y0 - 1) == 0x144 and blk(x0 - 1, y0 - 1) == 0x36D and hgt(x0, y0 - 1) == h == hgt(x0 - 1, y0 - 1):
                arm = x0 - 1; y0 -= 1
            box = {(x, y) for x in range(x0 if arm is None else arm, x1 + 1) for y in range(y0, y1 + 1)}
            mine = comp | ({(arm, y0), (x0, y0)} if arm is not None else set())
            # a neighbour at the piece's height that is walkable and not part of it = the piece may continue (missed L / fragment): report it
            cont = sorted(k for k in {(x + dx, y + dy) for (x, y) in mine for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))} - mine
                          if k in c and c[k][0] == h and not c[k][1])
            found.append(dict(cells=(x0 if arm is None else arm, y0, x1, y1), h=h, floor=floor, ok=ok, type=T, arm=arm, cont=cont))
    return found

# ROUND OBJECTS (lathes of remake/lib/furniture.py): finder per arrangement (checked on the drawings, ~/lktest/vase/outline.py) -> list of axes + floor
def vase_pairs(rom, room):
    """the vase pair by the hearth of the Mercator houses 670 / 671 / 694: $157 (back) over $061 (front) at the same walkable height h, the wall
    (blocked, height 0) west of them; the vases stand on the floor h - 1.  NOT 685 / 686 (the same blocks on a shelf: drawn lower) and 717 / 718
    ($157 next to $2A0): other arrangements, not measured yet"""
    if blockcat.tileset(rom, room) != 2: return []
    c = blockcat.cells(rom, room); out = []
    for (x, y), v in sorted(c.items()):
        w = c.get((x, y + 1)); wall = c.get((x - 1, y))
        if v[2] == 0x157 and not v[1] and v[0] > 0 and w and w[2] == 0x061 and w[0] == v[0] and not w[1] and wall and wall[1] and wall[0] == 0:
            out.append(dict(cells=(x, y, x, y + 1), floor=v[0] - 1))
    return out

def brazier_stands(rom, room):
    """the castle's brazier stands (tileset 1, top block $027 / $041 / $043, flame $098AAA): a stand cell (blocked or not) h steps high whose walkable
    neighbour gives 2 (short stand) or 4 (tall stand) steps; outlines checked on the drawings (~/lktest/braz/ov.py: 51 52 53 54 55 56 57 58 59 60 61
    62 86 87).  NOT the wall candle of 680 / 707 (same top block, no walkable neighbour)"""
    if blockcat.tileset(rom, room) != 1: return []
    c = blockcat.cells(rom, room); out = []
    for (x, y), v in sorted(c.items()):
        if v[2] not in (0x027, 0x041, 0x043): continue
        fl = sorted({n[0] for n in (c.get((x + dx, y + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) if n and not n[1] and v[0] - n[0] in (2, 4)})
        if fl: out.append(dict(cell=(x, y), floor=fl[-1], steps=v[0] - fl[-1]))
    return out

ROMPATH = [None]
_pics = {}
def _picture(room):
    """the whole room picture from the user's ROM (remake/tools/rom_picture.py into /tmp, never into git)"""
    if room not in _pics:
        import subprocess, proxy_overlay
        d = "/tmp/lk_furn_pic_%d" % room
        if not os.path.exists(d + "/full.png"):
            subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "rom_picture.py"), ROMPATH[0], str(room), "0", "0", "2432", "1216", d], capture_output=True, check=True)
        _pics[room] = proxy_overlay.read_png(d + "/full.png")
    return _pics[room]
def _lathe_sil(prof):
    """picture offsets (du, dv) covered by a lathe standing at the picture point of its axis foot"""
    import math
    top = prof[-1][0]; out = []
    def rad(z):
        for (z0, r0), (z1, r1) in zip(prof, prof[1:]):
            if z0 <= z <= z1: return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return -1
    for dv in range(-int(top) - 24, 14):
        for du in range(-18, 19):
            for zi in range(0, int(top * 4) + 1):
                z = zi / 4.0; x = (2 * (dv + 0.5) + 2 * z + du + 0.5) / 2; y = (2 * (dv + 0.5) + 2 * z - du - 0.5) / 2
                if math.hypot(x, y) <= rad(z): out.append((du, dv)); break
    return out
def _sample(room, cx, cy, fl, sil, dx, dy):
    w, h, c, F = _picture(room); ax, ay = 16 * cx + 8 + dx, 16 * cy + 8 + dy; U = int(round(ax - ay + 1184)); V = int(round((ax + ay) / 2 - fl))
    return [tuple(F[V + dv][(U + du) * c:(U + du) * c + 3]) if 0 <= V + dv < h and 0 <= U + du < w else None for du, dv in sil]

# ROUND OBJECTS FOUND BY A PICTURE MATCH: kind -> tileset, shape (remake/lib/furniture.py), the reference copy (room, cell x, y, floor steps), rooms seen
ROUND = collections.OrderedDict([
    ("barrel", dict(ts=15, shape="BARREL", ref=(71, 21, 15, 1), seen="65 66 68 69 71 72 78 79")),   # cellars / storerooms
    ("jar", dict(ts=8, shape="JAR", ref=(597, 30, 25, 0), seen="597 607 736")),                      # chapel jar by the angel statue
])
def round_found(rom, room, kind):
    """every walkable cell whose picture, with the object standing on the floor one step below the cell's top, matches the reference copy in >= 50 % of
    the object's silhouette pixels (2026-11-10 barrels: real copies 0.56 (half hidden behind the cupboard of 72) .. 1.00, everything else <= 0.39; top
    block ids alone missed the barrels drawn against a wall: 71 (14, 15) $062, (14, 19) $0C2).  Outlines checked on the drawings (~/lktest/barrel/ov.py)"""
    K = ROUND[kind]
    if blockcat.tileset(rom, room) != K["ts"]: return []
    B = getattr(furniture, K["shape"])
    if ("sil", kind) not in _pics: _pics[("sil", kind)] = _lathe_sil(B["prof"]); r0, x0, y0, f0 = K["ref"]; _pics[("ref", kind)] = _sample(r0, x0, y0, 16 * f0, _pics[("sil", kind)], B["dx"], B["dy"])
    sil, ref, out = _pics[("sil", kind)], _pics[("ref", kind)], []
    for (x, y), v in sorted(blockcat.cells(rom, room).items()):
        if v[1] or v[0] < 1: continue
        s = _sample(room, x, y, 16 * (v[0] - 1), sil, B["dx"], B["dy"])
        if sum(1 for a, b in zip(s, ref) if a == b) >= 0.5 * len(ref): out.append(dict(cell=(x, y), floor=v[0] - 1))
    return out

def lecterns(rom, room):
    """the chapel lectern (tileset 8, top block $2EF, walkable one step above the floor): 597 607 736 (same cell 27, 26)"""
    if blockcat.tileset(rom, room) != 8: return []
    return [dict(cell=(x, y), floor=v[0] - 1) for (x, y), v in sorted(blockcat.cells(rom, room).items()) if v[2] == 0x2EF and not v[1] and v[0] >= 1]

def altars(rom, room):
    """the church altar (tileset 3: $181 over $185 at the same walkable height, one step above the floor): 613 614 699 700 721"""
    if blockcat.tileset(rom, room) != 3: return []
    c = blockcat.cells(rom, room)
    return [dict(cell=(x, y), floor=v[0] - 1) for (x, y), v in sorted(c.items()) if v[2] == 0x181 and not v[1] and v[0] >= 1 and c.get((x, y + 1), (0, 1, 0))[2] == 0x185 and c[(x, y + 1)][0] == v[0]]

def angels(rom, room):
    """the chapel angel statue (tileset 8, top block $2EB on the blocked 1 step platform $2EB / $2EC): 597 607 736 (cell 27, 24); stands ON the platform"""
    if blockcat.tileset(rom, room) != 8: return []
    return [dict(cell=(x, y), floor=v[0]) for (x, y), v in sorted(blockcat.cells(rom, room).items()) if v[2] == 0x2EB and v[1] and v[0] >= 1]

def church_angels(rom, room):
    """the church angel statue in its wall niche (tileset 3): the picture of the statue + pedestal window equal to the one of 613 (>= 95 %% of the pixels;
    613 614 699 700 721 are pixel-identical there) and the pedestal cells 23 x 27..28 + niche 23 x 26..29 void in the height map -> the pedestal (op "ground", height 32)
    + the statue (furniture.CHURCH_ANGEL on the pedestal's corner cell 22, 27)"""
    if blockcat.tileset(rom, room) != 3: return []
    a = blockcat.arrays(rom, room)
    if not a or any(a["HM"].get((x - 12, y - 12)) != 0x4000 for x in (23,) for y in (26, 27, 28, 29)): return []
    ref, pic = _picture(613), _picture(room)
    same = sum(1 for v in range(320, 400) for u in range(1064, 1150) if ref[3][v][u * 3:u * 3 + 3] == pic[3][v][u * 3:u * 3 + 3])
    return [dict(cell=(22, 27), floor=2)] if same >= 0.95 * 80 * 86 else []

def lathe_obj(meshes, title):
    """[(vertices, faces), ..] -> OBJ text"""
    s = "# light proxy: %s (remake/tools/furniture_ops.py, remake/lib/furniture.py). GAME coordinates x east, y south, z up, world units.\n" % title
    s += "# our own geometry (measured lathe, placed on the cells that draw it); read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n"
    vs, fs, b = [], [], 0
    for v, f in meshes:
        vs += v; fs += [tuple(i + b for i in q) for q in f]; b += len(v)
    return s + "".join("v %.3f %.3f %.3f\n" % p for p in vs) + "".join("f " + " ".join(str(i + 1) for i in q) + "\n" for q in fs)

def main():
    a = [s for s in sys.argv[1:] if not s.startswith("--")]
    rom = open(a[0], "rb").read(); write = "--write" in sys.argv; ROMPATH[0] = a[0]
    rooms = [int(r) for r in sys.argv[sys.argv.index("--rooms") + 1].split(",")] if "--rooms" in sys.argv else [r for r in range(816) if blockcat.tileset(rom, r) in {T["ts"] for T in TYPES} | {1, 2, 3, 8} | {K["ts"] for K in ROUND.values()}]   # + the round shapes' tilesets (braziers 1, vases 2, ROUND)
    jp = os.path.join(ROOT, "landstalker", "data", "light_proxies.json"); data = json.load(open(jp), object_pairs_hook=collections.OrderedDict)
    n = 0
    for r in rooms:
        try: ts = tables(rom, r)
        except Exception as e: print("room %d: skipped (%s)" % (r, e)); continue
        good = [t for t in ts if t["ok"]]
        vases = vase_pairs(rom, r)
        for t in vases: print("room %d: vase pair cells %d..%d x %d..%d floor %d OK" % (r, t["cells"][0], t["cells"][2], t["cells"][1], t["cells"][3], t["floor"]))
        if write and vases:
            ops0 = [e for e in data["rooms"].get(str(r), []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/vase_"))]
            k = 0
            for t in vases:   # ONE op (= one light object) PER VASE: the light never shades an object by itself (own object rule), so a pair in one op let the
                x0, y0, x1, y1 = t["cells"]; V = furniture.VASE   # hearth shine through the back vase onto the front one (a bright streak, user 2026-11-09)
                for yy in (y0, y1):
                    ms = [furniture.lathe(16 * x0 + 8 + V["dx"], 16 * yy + 8 + V["dy"], 16 * t["floor"], V["h"], V["prof"])]
                    fn = "vase_%d.obj" % r if k == 0 else "vase_%d_%d.obj" % (r, k); k += 1
                    open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w").write(lathe_obj(ms, "vase, room %d" % r))
                    ops0.append(collections.OrderedDict([("op", "mesh"), ("cells", [x0, yy, x0, yy]), ("file", "proxies/" + fn), ("surface", True), ("floor", 16 * t["floor"]),
                        ("why", "vase pair by the hearth (collision = a 16 high box): the fitted lathe of remake/lib/furniture.py VASE, placed by remake/tools/furniture_ops.py; user 2026-11-09 'Objekte wie diese Vasen als echte 3D-Form fuers Licht'")]))
            data["rooms"][str(r)] = ops0; n += 1
        stands = brazier_stands(rom, r)
        for t in stands: print("room %d: brazier stand cell %d,%d floor %d steps %d OK" % (r, t["cell"][0], t["cell"][1], t["floor"], t["steps"]))
        if write and stands:
            ops0 = [e for e in data["rooms"].get(str(r), []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/brazier_"))]
            for k, t in enumerate(stands):   # one op per stand (own object rule)
                (x, y), P = t["cell"], furniture.brazier_prof(t["steps"]); top = P[-1][0]
                ms = [furniture.lathe(16 * x + 8 + furniture.BRAZIER["dx"], 16 * y + 8 + furniture.BRAZIER["dy"], 16 * t["floor"], top, [(z / top, rr) for z, rr in P])]
                fn = "brazier_%d.obj" % r if k == 0 else "brazier_%d_%d.obj" % (r, k)
                open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w").write(lathe_obj(ms, "brazier stand (%s), room %d" % ("short" if t["steps"] == 2 else "tall", r)))
                ops0.append(collections.OrderedDict([("op", "mesh"), ("cells", [x, y, x, y]), ("file", "proxies/" + fn), ("surface", True), ("floor", 16 * t["floor"]), ("carrier", collections.OrderedDict([("r", 12), ("axis", [16 * x + 8 + int(furniture.BRAZIER["dx"]), 16 * y + 8 + int(furniture.BRAZIER["dy"])]), ("z", int(round(16 * t["floor"] + top + 5)))])),
                    ("why", "brazier stand (collision = a %d high box): the fitted lathe of remake/lib/furniture.py BRAZIER, placed by remake/tools/furniture_ops.py; user 2026-11-09 'next forms'" % (16 * t["steps"]))]))
            data["rooms"][str(r)] = ops0; n += 1
        for kind, finder, shape, h in (("lectern", lecterns, "LECTERN", 0), ("altar", altars, "ALTAR", 1)):   # h: extra cells along y
            got = finder(rom, r)
            for t in got: print("room %d: %s cell %d,%d floor %d OK" % (r, kind, t["cell"][0], t["cell"][1], t["floor"]))
            if write and got:
                ops0 = [e for e in data["rooms"].get(str(r), []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/%s_" % kind))]
                for k, t in enumerate(got):
                    (x, y) = t["cell"]; fn = "%s_%d.obj" % (kind, r) if k == 0 else "%s_%d_%d.obj" % (kind, r, k)
                    open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w").write(lathe_obj(furniture.plated_box(x, y, 16 * t["floor"], getattr(furniture, shape)), "%s, room %d" % (kind, r)))
                    ops0.append(collections.OrderedDict([("op", "mesh"), ("cells", [x, y, x, y + h]), ("file", "proxies/" + fn), ("surface", True), ("air", True), ("floor", 16 * t["floor"]),
                        ("why", "%s (collision = a box): the fitted body + top plate + knee niche ('air': the plate over the niche = a slab) of remake/lib/furniture.py %s, placed by remake/tools/furniture_ops.py; user 2026-11-10 'baenke statue und pult'" % (kind, shape))]))
                data["rooms"][str(r)] = ops0; n += 1
        ang = angels(rom, r)
        for t in ang: print("room %d: angel statue cell %d,%d floor %d OK" % (r, t["cell"][0], t["cell"][1], t["floor"]))
        if write and ang:
            ops0 = [e for e in data["rooms"].get(str(r), []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/angel_"))]
            for k, t in enumerate(ang):
                (x, y) = t["cell"]; fn = "angel_%d.obj" % r if k == 0 else "angel_%d_%d.obj" % (r, k)
                open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w").write(lathe_obj(furniture.angel(x, y, 16 * t["floor"]), "angel statue, room %d" % r))
                ops0.append(collections.OrderedDict([("op", "mesh"), ("cells", [x, y, x, y]), ("file", "proxies/" + fn), ("surface", True), ("air", True), ("floor", 16 * t["floor"]),
                    ("why", "angel statue on its platform (collision = the platform only): body lathe + wing plate of remake/lib/furniture.py ANGEL ('air': the wings float = slabs), placed by remake/tools/furniture_ops.py; user 2026-11-10 'baenke statue und pult'")]))
            data["rooms"][str(r)] = ops0; n += 1
        cang = church_angels(rom, r)
        for t in cang: print("room %d: church angel statue + pedestal 23 x 27..28 + niche 23 x 26..29 OK" % r)
        if write and cang:
            ops0 = [e for e in data["rooms"].get(str(r), []) if not ((e.get("op") == "mesh" and e.get("file", "").startswith("proxies/church_angel_")) or e.get("op") == "ground")]
            fn = "church_angel_%d.obj" % r
            open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w").write(lathe_obj(furniture.church_angel4(32), "church angel statue (exact light model v4), room %d" % r))
            ops0.append(collections.OrderedDict([("op", "ground"), ("cells", [23, 27, 23, 28, 32]),
                ("why", "the statue's pedestal (1 x 2 cells) in the wall niche: void in the game's height map (the light saw a wall up to the room top), drawn as a 16 high box on the dais floor 16 (LK_LTGROUND v1; user 2026-11-10 'Sockel und Statuen in den Kirchen ja')")]))
            ops0.append(collections.OrderedDict([("op", "ground"), ("cells", [23, 26, 23, 29, 16]),
                ("why", "the niche floor beside the pedestal (the niche is 1 cell deep, x 368..384, and 4 cells wide, y 416..480, read from its drawn corners; the ground op fills only cells still void after the pedestal)")]))
            ops0.append(collections.OrderedDict([("op", "mesh"), ("cells", [23, 27, 23, 28]), ("file", "proxies/" + fn), ("surface", True), ("air", True), ("floor", 32),
                ("why", "church angel statue on its pedestal: exact light model of remake/lib/furniture.py CHURCH_ANGEL4 = rings with own centres + wing pixel sheets ('air': the wings float = slabs), placed by remake/tools/furniture_ops.py; user 2026-11-10 'Sockel und Statuen in den Kirchen ja'")]))
            data["rooms"][str(r)] = ops0; n += 1
        for kind, K in ROUND.items():
            found = round_found(rom, r, kind)
            for t in found: print("room %d: %s cell %d,%d floor %d OK" % (r, kind, t["cell"][0], t["cell"][1], t["floor"]))
            if write and found:
                ops0 = [e for e in data["rooms"].get(str(r), []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/%s_" % kind))]
                for k, t in enumerate(found):   # one op per object (own object rule)
                    (x, y), B = t["cell"], getattr(furniture, K["shape"]); top = B["prof"][-1][0]
                    if kind == "barrel": ms = furniture.barrel_mesh(16 * x + 8 + B["dx"], 16 * y + 8 + B["dy"], 16 * t["floor"])   # near-final (remake/MODELS.md)
                    else: ms = [furniture.lathe(16 * x + 8 + B["dx"], 16 * y + 8 + B["dy"], 16 * t["floor"], top, [(z / top, rr) for z, rr in B["prof"]])]
                    fn = "%s_%d.obj" % (kind, r) if k == 0 else "%s_%d_%d.obj" % (kind, r, k)
                    open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w").write(lathe_obj(ms, "%s, room %d" % (kind, r)))
                    ops0.append(collections.OrderedDict([("op", "mesh"), ("cells", [x, y, x, y]), ("file", "proxies/" + fn), ("surface", True), ("floor", 16 * t["floor"]),
                        ("why", "%s (collision = a 16 high box): the fitted lathe of remake/lib/furniture.py %s, found by a picture match in remake/tools/furniture_ops.py; user 2026-11-10 'weiter' (next forms)" % (kind, K["shape"]))]))
                data["rooms"][str(r)] = ops0; n += 1
        for t in ts: print("room %d: %s cells %d..%d x %d..%d height %d floor %d %s%s%s" % (r, t["type"]["name"] if t["arm"] is None else "L bench", t["cells"][0], t["cells"][2], t["cells"][1], t["cells"][3], t["h"], t["floor"],
                                 "OK" if t["ok"] else "SKIPPED (fragment / not one step above the floor)", "" if not t["ok"] or not t["cont"] else "  CHECK: neighbours at its height " + " ".join("%d,%d" % k for k in t["cont"]),
                                 ""))
        if not good or not write: continue
        ops = [e for e in data["rooms"].get(str(r), []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/table_")) and e.get("op") != "unpaint"]
        for k, t in enumerate(good):   # ONE OBJ per piece: every mesh op loads its file as a model of its own (two ops on one file = every triangle twice)
            x0, y0, x1, y1 = t["cells"]; sh = t["type"]["shape"]
            if t["arm"] is None: parts = furniture.table("table0", 16 * x0, 16 * y0, 16 * x1 + 16, 16 * y1 + 16, 16 * t["floor"], 16 * t["h"], **sh)
            else: parts = furniture.l_bench("lbench0", 16 * (t["arm"] + 1), 16 * y0, 16 * x1 + 16, 16 * y1 + 16, 16 * t["arm"], 16 * t["floor"], 16 * t["h"], **sh)
            fn = "table_%d.obj" % r if k == 0 else "table_%d_%d.obj" % (r, k)
            open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w").write(boxes_obj(parts, "%s, room %d" % (t["type"]["name"] if t["arm"] is None else "L bench", r)))
            ops.append(collections.OrderedDict([("op", "mesh"), ("cells", [x0, y0, x1, y1]), ("file", "proxies/" + fn), ("surface", True), ("air", True), ("floor", 16 * t["floor"]),
                ("why", "%s on legs (collision = a solid box): the measured shape of remake/lib/furniture.py, placed by remake/tools/furniture_ops.py; user 2026-11-09 'beides ja' / '1 und 2'" % t["type"]["name"])]))
        for t in good:   # LK_GLUNPAINT v1: the painted shadow on the piece's floor footprint goes while the GPU light shades the model
            x0, y0, x1, y1 = t["cells"]; nh = unpaint_hits(rom, r, t["type"]["ts"], t["cells"], 16 * t["floor"])
            if nh: ops.append(collections.OrderedDict([("op", "unpaint"), ("cells", [x0, y0, x1, y1]), ("floor", 16 * t["floor"]),
                ("why", "%d painted shadow tiles under the %s (furniture_ops.py UNPAINT_TILES; user 2026-11-09 'so dass der Tisch nur unseren Schatten wirft')" % (nh, t["type"]["name"] if t["arm"] is None else "L bench"))]))
        data["rooms"][str(r)] = ops; n += 1
    if write:
        data["unpaint_tiles"] = collections.OrderedDict([("_about", "LK_GLUNPAINT v1: per tileset [painted shadow tile, the same tile without the shadow] (hex tile numbers), used by op 'unpaint'; written by remake/tools/furniture_ops.py UNPAINT_TILES")]
            + [(str(ts), [["%03X" % f, "%03X" % t] for f, t in sorted(m.items())]) for ts, m in sorted(UNPAINT_TILES.items())])
        data["rooms"] = collections.OrderedDict(sorted(data["rooms"].items(), key=lambda t: int(t[0])))
        open(jp, "w").write(json.dumps(data, indent=2, ensure_ascii=False) + "\n"); print("written: %d rooms" % n)

if __name__ == "__main__":
    main()
