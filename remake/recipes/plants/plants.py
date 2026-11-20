#!/usr/bin/env python3
"""plants.py ROM [ROOMS] [--write] [--png DIR] [-j N]  -- EVERY drawn pine and bush of the outdoor rooms as a real 3D light model (user 2026-11-20:
'generell sollten alle Kiefern und Buesche ihr 3D-Modell haben'; LIGHT_PROXY_PLAN 'WHOLE ROOMS AS 3D MODELS', HANDOFF -238).

Recipe only: the templates are rebuilt from the ROM on every run, git gets our models + the measured feet (data/plants.json), never pixels.
Models (remake/recipes/plants/params_*.json, user OK 2026-11-20 on the clay previews):
  pine  = the big forest / town pine (pine_court/pine.py, wild, fitted IoU 0.87)
  small = the small pine (the original draws it from the big pine's tiles WITHOUT the middle 16 rows: 32 px instead of 47; room 475 ...)
  bush  = the round bush on its Y stem (bush.py; ONE drawing in every outdoor tileset: what looks different is bushes standing behind each other)
  The other pine colour (tileset 17 forests) has the same shape = the same model; the Mercator castle court pine (rooms 32 / 33) keeps its own trimmed model.
How:
  1. plane A of the room (romrender, layer B = ground left out: the plants are layer A tiles) as palette indices (& 15: the colour line differs per tileset)
  2. lattice scan (feet at fixed U % 16 / V % 8 phases) with the TOP rows of each template (tips stay visible in dense forests, the lower tiers are hidden by
     the pines in front); >= 65 %% of the template's pixels equal
  3. pine or small: both share the tip; rows tip+16..31 equal the big pine's rows 16..31 -> pine, its rows 32..47 -> small; covered -> the nearest decided pine
  4. foot in world units: the view ray through the foot pixel meets the floor of the game's height map (blocked plant cells take the nearest free
     floor, up to 8 cells away: dense forests); plants inside a hand-made tree model's rectangle (pine_cl / pine_court / tree ops in data/light_proxies.json) are left to that model
--write: data/plants.json (feet per room) + data/proxies/plant_{pine,small,bush}.obj (one model each, origin = the drawn foot on the ground).
--png DIR: room picture with the found feet (red pine, blue small, yellow bush) for the eye check."""
import json, math, os, sys, types
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "landstalker", "tools")); sys.path.insert(0, os.path.join(HERE, "..", "pine_cluster")); sys.path.insert(0, os.path.join(HERE, "..", "pine_court")); sys.path.insert(0, HERE)
import romrender as R, proxysurvey as PS, pine_cluster as PC, blockcat as BC, pine, bush

W, H = 2400, 1300
E = types.SimpleNamespace(t={})
ROM = None
LIFT = {"pine": 47, "small": 29, "bush": 33, "bigtree": 80}          # tip row above the foot row
REF = {"pine": (632, 431 - 991 + 1184, (431 + 991) // 2 - 16),   # reference instances (room, foot U, foot V): pine_cluster INST[3] (Mercator), room 475 front pine / bush
       "small": (475, 832, 718), "bush": (475, 736, 765),
       "bigtree": (488, 1104, 488)}   # the BIG ROUND TREE of room 488 (axis x 576 y 656 on ground 128, remake/recipes/proxy_tree_488.py); user 2026-11-20 leftover list: the same drawing stands in 424 / 451 / 454 / 474 ...
BOX = {"pine": (-9, 9, 16), "small": (0, 15, 14), "bush": (0, 15, 14), "bigtree": (-14, 14, 20)}   # detection box: columns dx0..dx1 (small / bush: right half, the left one is hidden by the neighbour), top rows
TREE_OPS = ("pine_cl", "pine_court", "tree_")

def planeA(room):
    g, r, pa, pb, getpal = R.rom_planes(ROM, room)
    R.compose(pa, E, getpal, 0, 0, W, H, (0, 0, 0), g['tiles'])
    return [v & 15 if v else 0 for v in R.compose.idx]

_ref = {}
def refidx(room):
    if room not in _ref: _ref[room] = planeA(room)
    return _ref[room]

def tmpl(name, dx0, dx1, y0, rows):
    room, U, V = REF[name]; idx = refidx(room)
    return {(dx, dy): idx[(V + dy) * W + U + dx] for dy in range(y0, y0 + rows) for dx in range(dx0, dx1 + 1) if idx[(V + dy) * W + U + dx]}

def templates():
    T = {n: tmpl(n, BOX[n][0], BOX[n][1], -LIFT[n], BOX[n][2]) for n in REF}
    T["bushlow"] = tmpl("bush", -7, 7, -12, 13)   # user 2026-11-20 (room 362): bushes BEHIND a row of pines show only their lower crown + Y stem
    big = tmpl("pine", -15, 15, -47, 48)
    return T, {(dx, dy + 47): v for (dx, dy), v in big.items()}, tmpl("small", 0, 15, -29, 30)

def tree_rects(room):
    d = json.load(open(os.path.join(ROOT, "landstalker", "data", "light_proxies.json")))["rooms"].get(str(room), [])
    return [e["cells"][:4] for e in d if e["op"] == "mesh" and os.path.basename(e["file"]).startswith(TREE_OPS)]

_cat = None
def catalogue_bushes(room):
    """bush cells of the object catalogue (data/object_blocks.json, the same rule as the runtime LK_LTOBJ / lk_lt_tk): one bush per raised cell drawn with a bush
    block, standing at the cell centre one step below the cell's top. Dense bush fields (user 2026-11-20, room 362: the
    crowns overlap each other, the picture match misses them) come from here."""
    global _cat
    if _cat is None: _cat = json.load(open(os.path.join(ROOT, "landstalker", "data", "object_blocks.json")))
    ids = set(int(b, 16) for b in _cat["tilesets"].get(str(BC.tileset(ROM, room)), {}).get("bush", []))
    if not ids: return []
    c = BC.cells(ROM, room)
    # one bush per cell drawn with a bush block, foot one step (16) below the cell's top: raised blocked bush blocks (room 488: top = base + 16) and walkable
    # bush fields whose top is the bushes' crowns (room 362, height 3 between pines of height 4) alike
    return [("bush", 16 * k[0] + 8.0, 16 * k[1] + 8.0, 16 * v[0] - 16) for k, v in sorted(c.items()) if v[2] in ids and v[0] >= 1]

def survey(room, T, BIG, SMALL, thr=0.65):
    idx = planeA(room); hits = []
    for name, t in T.items():
        ref = REF["bush" if name == "bushlow" else name]; ph, phu = ref[2] % 8, ref[1] % 16; lim = len(t) * (1 - thr)
        for V in range(80 + ph, H - 8, 8):
            for U in range(48 + phu, W - 48, 16):
                miss = 0
                for (dx, dy), v in t.items():
                    if idx[(V + dy) * W + U + dx] != v:
                        miss += 1
                        if miss > lim: break
                else: hits.append(("bush" if name == "bushlow" else name, U, V))
    out = sorted(set(h for h in hits if h[0] in ("bush", "bigtree"))); tips = []
    for name, U, V in hits:
        if name in ("bush", "bigtree"): continue
        tv = V - LIFT[name]
        if not any(k[0] == U and abs(k[1] - tv) <= 2 for k in tips): tips.append((U, tv))
    dec = []
    for U, tv0 in tips:
        best = None
        for tv in range(tv0 - 3, tv0 + 4):
            sb = ss = n = 0
            for (dx, r), v in BIG.items():
                if 16 <= r < 32:
                    q = idx[(tv + r) * W + U + dx]; n += 1; sb += q == v; ss += BIG.get((dx, r + 16)) == q
            sb /= max(n, 1); ss /= max(n, 1)
            kind = "pine" if sb >= 0.45 and sb > ss + 0.15 else "small" if ss >= 0.45 and ss > sb + 0.15 else None
            if best is None or max(sb, ss) > best[3]: best = [U, tv, kind, max(sb, ss)]
        dec.append(best)
    for d in dec:
        if d[2] is None:
            near = sorted((abs(e[0] - d[0]) + abs(e[1] - d[1]), e[2]) for e in dec if e[2])
            d[2] = near[0][1] if near and near[0][0] <= 48 else "pine"
        if d[2] == "pine": out.append(("pine", d[0], d[1] + 47))
        else:   # the small pine's own foot row: best match of its template around tip + 29
            sc = []
            for V in range(d[1] + 26, d[1] + 33):
                sc.append((sum(1 for (dx, dy), v in SMALL.items() if idx[(V + dy) * W + d[0] + dx] == v), V))
            out.append(("small", d[0], max(sc)[1]))
    hm = PS.heights(ROM, room); rects = tree_rects(room); res = []; drop = 0
    for name, U, V in out:
        w = foot_world(hm, U, V)
        if not w: continue
        X, Y, z, c = w
        if any(r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3] for r in rects): drop += 1; continue
        res.append([name, round(X, 1), round(Y, 1), int(z), U, V])
    ncat = 0
    for name, X, Y, z in catalogue_bushes(room):
        c = (int(X) >> 4, int(Y) >> 4)
        if any(r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3] for r in rects): continue
        if any(abs(q[1] - X) < 10 and abs(q[2] - Y) < 10 and (q[0] == "bush" or (abs(q[1] - X) < 6 and abs(q[2] - Y) < 6)) for q in res): continue
        res.append([name, X, Y, int(z), int(X - Y + 1184), int((X + Y) / 2 - z) + 8]); ncat += 1
    if ncat: print("room %d: %d bushes from the catalogue cells (dense fields)" % (room, ncat), flush=True)
    return res, drop

def foot_world(hm, U, V):
    """pine_cluster.foot_world with the floor of a blocked cell = the NEAREST free floor (ring by ring up to 8 cells away): inside a dense forest every
    cell is blocked (room 425 rows 15..17: the old rule took the cell's own top and put the back pines 2 rows forward)"""
    def floor(c):
        h, b = hm.get(c, (None, True))
        if h is None: return None
        if not b: return 16 * h
        for d in range(1, 9):
            nb = [hm[q][0] for q in ((c[0] + a, c[1] + e) for a in range(-d, d + 1) for e in range(-d, d + 1) if max(abs(a), abs(e)) == d) if q in hm and not hm[q][1]]
            if nb: return 16 * min(nb)
        return 16 * h
    D = U - 1184
    for z in range(255, -16, -1):
        X = V + z + D / 2; Y = V + z - D / 2; c = (int(X // 16), int(Y // 16)); f = floor(c)
        if f is not None and z <= f: return X, Y, z, c
    return None

def write_models():
    src = os.path.join(ROOT, "landstalker", "data", "proxies", "tree_488.obj")   # the measured big tree (proxy_tree_488.py), moved to the origin (= its foot)
    with open(os.path.join(ROOT, "landstalker", "data", "proxies", "plant_bigtree.obj"), "w") as fo:
        fo.write("# bigtree light model = landstalker/data/proxies/tree_488.obj (remake/recipes/proxy_tree_488.py) moved by (-576, -656, -128): origin = its foot on the ground (remake/recipes/plants/plants.py)\n")
        for l in open(src):
            if l.startswith("v "): x, y, z = map(float, l.split()[1:4]); fo.write("v %g %g %g\n" % (round(x - 576, 3), round(y - 656, 3), round(z - 128, 3)))
            elif l.startswith("f "): fo.write(l)
    for name, P in (("pine", "params_pine.json"), ("small", "params_small.json"), ("bush", "params_bush.json")):
        P = json.load(open(os.path.join(HERE, P))); o = P["offset"]
        parts = pine.pine_parts(o, o, 0, P, seed=11) if name != "bush" else bush.bush_parts(o, o, 0, P, seed=11)
        pine.write_obj(os.path.join(ROOT, "landstalker", "data", "proxies", "plant_%s.obj" % name), parts,
                       "%s light model (remake/recipes/plants/plants.py), origin = the drawn foot on the ground" % name)

def work(room):
    global ROM
    if ROM is None: ROM = open(sys.argv[1], "rb").read()
    T, BIG, SMALL = templates()
    try: res, drop = survey(room, T, BIG, SMALL)
    except Exception as e: return room, None, str(e)
    return room, res, drop

def main():
    global ROM
    a = [x for x in sys.argv[2:] if not x.startswith("-")]; ROM = open(sys.argv[1], "rb").read()
    jn = int(sys.argv[sys.argv.index("-j") + 1]) if "-j" in sys.argv else 6
    if "-j" in sys.argv: a = [x for x in a if x != sys.argv[sys.argv.index("-j") + 1]]
    png = sys.argv[sys.argv.index("--png") + 1] if "--png" in sys.argv else None
    if png: a = [x for x in a if x != png]
    rooms = [int(x) for x in a] or [r for r in BC.outdoor_rooms(ROM) if r not in (32, 33)]
    import multiprocessing as mp
    with mp.Pool(jn) as pool: results = pool.map(work, rooms)
    path = os.path.join(ROOT, "landstalker", "data", "plants.json")
    data = json.load(open(path)) if os.path.isfile(path) else {}
    data.setdefault("rooms", {}); tot = {}
    for room, res, drop in results:
        if res is None: print("room %d: error %s" % (room, drop)); continue
        cnt = {k: sum(1 for r in res if r[0] == k) for k in ("pine", "small", "bush", "bigtree")}
        for k, v in cnt.items(): tot[k] = tot.get(k, 0) + v
        print("room %d: %d pines, %d small, %d bushes, %d big trees%s" % (room, cnt["pine"], cnt["small"], cnt["bush"], cnt["bigtree"], (", %d left to hand tree models" % drop) if drop else ""), flush=True)
        if res: data["rooms"][str(room)] = [r[:4] for r in sorted(res, key=lambda r: (r[2], r[1]))]
        else: data["rooms"].pop(str(room), None)
        if png:
            os.makedirs(png, exist_ok=True); g, rr, pa, pb, getpal = R.rom_planes(ROM, room)
            rgb = bytearray(R.compose(pa, pb, getpal, 0, 0, W, H, (0, 0, 0), g['tiles']))
            col = {"pine": (255, 0, 0), "small": (0, 160, 255), "bush": (255, 255, 0), "bigtree": (255, 0, 255)}
            for name, X, Y, z, U, V in res:
                for k in range(LIFT[name] + 1):
                    o = ((V - k) * W + U) * 3; rgb[o:o + 3] = bytes(col[name])
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1): o = ((V + dy) * W + U + dx) * 3; rgb[o:o + 3] = bytes(col[name])
            R.png(os.path.join(png, "plants_%d.png" % room), W, H, rgb)
    print("total: %s in %d rooms" % (tot, sum(1 for r in results if r[1])))
    if "--write" in sys.argv:
        data["_about"] = ("every drawn pine / bush of the outdoor rooms as a light model instance [model, x, y, z] (world units, foot on the ground); written by "
                          "remake/recipes/plants/plants.py (template match on the ROM picture + the game's height map; README there). Models: data/proxies/plant_*.obj")
        data["models"] = {"pine": "proxies/plant_pine.obj", "small": "proxies/plant_small.obj", "bush": "proxies/plant_bush.obj", "bigtree": "proxies/plant_bigtree.obj"}
        with open(path, "w") as f:
            f.write("{\n \"_about\": %s,\n \"models\": %s,\n \"rooms\": {\n" % (json.dumps(data["_about"]), json.dumps(data["models"])))
            ks = sorted(data["rooms"], key=int)
            for i, k in enumerate(ks): f.write("  %s: %s%s\n" % (json.dumps(k), json.dumps(data["rooms"][k]), "," if i + 1 < len(ks) else ""))
            f.write(" }\n}\n")
        write_models(); print("wrote", path)

if __name__ == "__main__":
    main()
