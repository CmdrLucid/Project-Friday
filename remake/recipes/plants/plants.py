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
TREE_OPS = ("pine_court", "tree_")   # pine_cl (hand-made 4 pine groups) dropped 2026-11-21, user: 'die Vierergruppen ... auch das eine Tannenmodell'

NOT_PLANTS = {r: {("bush", 536, 392), ("bush", 536, 408), ("bush", 712, 424), ("bush", 536, 440), ("bush", 392, 488)} for r in (641, 642, 643, 644)}   # false template hits on the docks' PAVED PATH (blue-green stone floor, not water; user 2026-11-21: 'da ist kein Busch', 'das ist ein normaler Weg'), dropped
NO_PLANE_B = {34, 35}   # Mercator castle tower: plane B paints the forest far BELOW the tower (backdrop, not the room's ground)

def planeB(room):
    """plane B alone (the ground + the back rows of a forest), palette index & 15"""
    g, r, pa, pb, getpal = R.rom_planes(ROM, room)
    R.compose(E, pb, getpal, 0, 0, W, H, (0, 0, 0), g['tiles'])
    return [v & 15 if v else 0 for v in R.compose.idx]

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
    # v3 (2026-11-21, room 458 meadow islands): only a bush cell HIGHER than its lowest neighbour is a raised bush block; one at the ground's height stands on it
    def low(k): return min([c[q][0] for q in ((k[0] + 1, k[1]), (k[0] - 1, k[1]), (k[0], k[1] + 1), (k[0], k[1] - 1)) if q in c] or [c[k][0] - 1])
    return [("bush", 16 * k[0] + 8.0, 16 * k[1] + 8.0, 16 * v[0] - 16 * (low(k) < v[0])) for k, v in sorted(c.items()) if v[2] in ids and v[0] >= 1]

def survey(room, T, BIG, SMALL, thr=0.65):
    # 2026-11-21 (user, rooms 427 / 566: 'ganz viele nicht erkannt'): the back rows of a forest are drawn in plane B (with the ground), not only in
    # plane A: scan both planes; a plant found in both keeps plane A
    idxs = [planeA(room)] + ([] if room in NO_PLANE_B else [planeB(room)]); hits = []
    for li, idx in enumerate(idxs):
        for name, t in T.items():
            ref = REF["bush" if name == "bushlow" else name]; ph, phu = ref[2] % 8, ref[1] % 16; lim = len(t) * (1 - thr)
            for V in range(80 + ph, H - 8, 8):
                for U in range(48 + phu, W - 48, 16):
                    miss = 0
                    for (dx, dy), v in t.items():
                        if idx[(V + dy) * W + U + dx] != v:
                            miss += 1
                            if miss > lim: break
                    else: hits.append(("bush" if name == "bushlow" else name, U, V, li))
    out = []
    for h in sorted(set(h for h in hits if h[0] in ("bush", "bigtree")), key=lambda h: h[3]):
        if not any(o[:3] == h[:3] for o in out): out.append(h)
    tips = []
    for name, U, V, li in sorted(hits, key=lambda h: h[3]):
        if name in ("bush", "bigtree"): continue
        tv = V - LIFT[name]
        if not any(k[0] == U and abs(k[1] - tv) <= 2 for k in tips): tips.append((U, tv, li))
    dec = []
    for U, tv0, li in tips:
        best = None; idx = idxs[li]
        for tv in range(tv0 - 3, tv0 + 4):
            sb = ss = n = 0
            for (dx, r), v in BIG.items():
                if 16 <= r < 32:
                    q = idx[(tv + r) * W + U + dx]; n += 1; sb += q == v; ss += BIG.get((dx, r + 16)) == q
            sb /= max(n, 1); ss /= max(n, 1)
            kind = "pine" if sb >= 0.45 and sb > ss + 0.15 else "small" if ss >= 0.45 and ss > sb + 0.15 else None
            if best is None or max(sb, ss) > best[3]: best = [U, tv, kind, max(sb, ss), li, sb, ss]
        if best[2] is None and max(best[5], best[6]) >= 0.3 and abs(best[5] - best[6]) >= 0.15:   # partly covered (user 2026-11-21, room 484 foot U 1232: a small pine
            best[2] = "pine" if best[5] > best[6] else "small"                                       # half hidden at a cliff edge, small 0.33 / big 0.10 -> was the default big pine)
        dec.append(best)
    for d in dec:
        if d[2] is None:
            near = sorted((abs(e[0] - d[0]) + abs(e[1] - d[1]), e[2]) for e in dec if e[2])
            d[2] = near[0][1] if near and near[0][0] <= 48 else "pine"
        if d[2] == "pine": out.append(("pine", d[0], d[1] + 47, d[4]))
        else:   # the small pine's own foot row: best match of its template around tip + 29
            sc = []
            for V in range(d[1] + 26, d[1] + 33):
                sc.append((sum(1 for (dx, dy), v in SMALL.items() if idxs[d[4]][(V + dy) * W + d[0] + dx] == v), V))
            out.append(("small", d[0], max(sc)[1], d[4]))
    hm = heights_full(room); rects = tree_rects(room); res = []; drop = 0; bushes = bush_cells(room)
    _gfc.clear(); _vc.clear(); _ftype.clear(); _ftype[id(hm)] = floor_types(room)   # caches are keyed by id(hm): clear per room (a pool worker surveys several rooms and Python reuses ids)
    for name, U, V, li in out:
        w = foot_tree(hm, U, V) if name == "bigtree" else foot_world(hm, U, V, bushes, trunk_seen(idxs[li], T, BIG, SMALL, name, U, V))
        if not w and name != "bigtree": w = foot_world(hm, U, V, bushes, trunk_seen(idxs[li], T, BIG, SMALL, name, U, V), skipvoid=False)   # drawn over the void at the room's edge: no floor behind it -> as before (the void's nearest floor)
        if not w: continue
        X, Y, z, c = w
        if any(r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3] for r in rects): drop += 1; continue
        res.append([name, round(X, 1), round(Y, 1), int(z), U, V])
    ncat = 0
    for name, X, Y, z in catalogue_bushes(room):
        c = (int(X) >> 4, int(Y) >> 4)
        if any(r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3] for r in rects): continue
        if any(abs(q[1] - X) < 10 and abs(q[2] - Y) < 10 and (q[0] == "bush" or (abs(q[1] - X) < 6 and abs(q[2] - Y) < 6)) for q in res): continue
        Ub, Vb = X - Y + 1184, (X + Y) / 2 - z - 14   # the bush crown's centre in the picture
        if any(q[0] in ("pine", "small") and abs(q[4] - Ub) <= 12 and q[5] - LIFT[q[0]] - 2 <= Vb <= q[5] - 30 for q in res): continue   # its crown would lie in the UPPER part of a found pine = that pine's tiles, nothing of a bush can show there (user 2026-11-21, room 458 islands: 'da ist kein Busch'). A bush whose crown sits at a pine's lower part stays: it stands behind the pine and peeks out (rooms 425 / 446, user: 'kann durchaus mal vorkommen')
        res.append([name, X, Y, int(z), int(X - Y + 1184), int((X + Y) / 2 - z) + 8]); ncat += 1
    if ncat: print("room %d: %d bushes from the catalogue cells (dense fields)" % (room, ncat), flush=True)
    return res, drop

def bush_cells(room):
    """cells drawn with a catalogue bush block (walkable bush tops: their height is the CROWN, the ground lies one step lower; user 2026-11-21 'auf den Bueschen kann man laufen')"""
    global _cat
    if _cat is None: _cat = json.load(open(os.path.join(ROOT, "landstalker", "data", "object_blocks.json")))
    ids = set(int(b, 16) for b in _cat["tilesets"].get(str(BC.tileset(ROM, room)), {}).get("bush", []))
    if not ids: return set()
    c = BC.cells(ROM, room)
    return set(k for k, v in c.items() if v[2] in ids and v[0] >= 1 and min([c[q][0] for q in ((k[0] + 1, k[1]), (k[0] - 1, k[1]), (k[0], k[1] + 1), (k[0], k[1] - 1)) if q in c] or [v[0]]) < v[0])   # only RAISED bush cells

def trunk_seen(idx, T, BIG, SMALL, name, U, V, thr=0.5):
    """is the plant's LOWER part (trunk / stem) drawn at its foot row? (user 2026-11-21, room 458: 'die 48er-Tannen stehen hinter der Erhoehung, sonst waere das ganze
    Sprite zu sehen'): a covered trunk = the plant stands BEHIND what covers it (lower, further back on the same view ray)"""
    if name == "pine": t = {(dx, r - 47): v for (dx, r), v in BIG.items() if r >= 36}
    elif name == "small": t = {(dx, r - 29): v for (dx, r), v in SMALL.items() if r >= 22}
    else: t = T["bushlow"]
    if not t: return True
    ok = sum(1 for (dx, dy), v in t.items() if 0 <= V + dy < H and 0 <= U + dx < W and idx[(V + dy) * W + U + dx] == v)
    return ok >= thr * len(t)

_gfc, _ftype = {}, {}
def heights_full(room):
    """PS.heights + the 0000 words inside the room's rectangle as plain floor of height 0 (LESSONS 86: 0000 is FLOOR, not void; PS.heights drops them).
    2026-11-21 room 561: its whole ground is 0000 (forest blocks $42 / $43): without them the view ray fell through the ground (pines on 16 / the forest group's other floors)"""
    hm = PS.heights(ROM, room)
    if not hm: return hm
    xs = [c[0] for c in hm]; ys = [c[1] for c in hm]
    for x in range(min(xs), max(xs) + 1):
        for y in range(min(ys), max(ys) + 1): hm.setdefault((x, y), (0, False))
    return hm

def floor_types(room):
    """{cell: floor type} = the height map word's LOW byte (LESSONS 86: 0 = plain floor; water / triggers have their own type, e.g. room 566's pond = $19)"""
    a = PS.romroom.arrays(PS.romroom.decode(ROM, room))['HM']
    return {(x + 12, y + 12): v & 255 for (x, y), v in a.items() if v}

_vc = {}
def void_cells(hm):
    """the blocked-0 cells connected (4 neighbours, through blocked-0 cells) to the edge of the height map's rectangle = the void around the room"""
    key = id(hm)
    if key in _vc: return _vc[key]
    xs = [c[0] for c in hm]; ys = [c[1] for c in hm]; x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    isv = lambda c: c in hm and hm[c][1] and hm[c][0] == 0
    st = [c for c in hm if isv(c) and (c[0] in (x0, x1) or c[1] in (y0, y1))]; out = set(st)
    while st:
        c = st.pop()
        for q in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
            if q not in out and isv(q): out.add(q); st.append(q)
    _vc[key] = out
    return out

def group_floors(hm, bushes):
    """{blocked cell: floor} - every 4-connected group of blocked cells of one height gets the LOWEST free floor touching it (bush tops one step lower; only floors
    not above the group's top). User 2026-11-21 (room 458): forest blocks stand on the ground at their foot, a raised path or a bush strip beside them is not that ground."""
    key = id(hm)
    if key in _gfc: return _gfc[key]
    out, seen = {}, set()
    for c0, (h0, b0) in hm.items():
        if not b0 or c0 in seen or h0 in (0, 15): continue   # 2026-11-21: never a $4Fxx barrier (blocked + 15, LESSONS 2) nor the blocked-0 void ($40xx) around the room: the barrier ring / the void is ONE group touching every floor of the room (469: bushes on the barrier cliff -> z 0 in the void row); forest blocks are raised (561 $42 / $43, 458 $43)
        grp, st = [], [c0]; seen.add(c0)
        while st:
            c = st.pop(); grp.append(c)
            for q in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
                if q not in seen and q in hm and hm[q][1] and hm[q][0] == h0: seen.add(q); st.append(q)
        fl = [hm[q][0] - (q in bushes) for c in grp for q in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)) if q in hm and not hm[q][1]]
        fl = [f for f in fl if f <= h0]
        ft = _ftype.get(key, {})
        fp = [hm[q][0] - (q in bushes) for c in grp for q in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)) if q in hm and not hm[q][1] and not ft.get(q, 0)]
        fp = [f for f in fp if f <= h0]
        if fp: fl = fp   # 2026-11-21: only PLAIN floors (type 0) are a forest's ground when there are any: room 566's pond (type $19, height 0) beside the forest is not where its pines stand (path 16)
        if fl:   # the LOWEST floor that is more than a stray touch (>= 3 border edges and >= 10 % of the border): 2026-11-21 room 566 = one forest group over
                 # the whole room touching 2 pond corner cells (0) -> all its pines sank to 0 instead of the paths' 16; the plain lowest floor stays the rule (458:
                 # raised path 48 / bush strip on one side, ground 16 = the forest's ground, user); the most common floor put 509 / 506 pines on raised paths
            from collections import Counter
            cnt = Counter(fl); need = max(3, 0.1 * len(fl))
            m = min([f for f, n in cnt.items() if n >= need] or [max(cnt.items(), key=lambda t: (t[1], -t[0]))[0]])
            for c in grp: out[c] = 16 * m
    _gfc[key] = out
    return out

def foot_world(hm, U, V, bushes=(), seen=True, skipvoid=True):
    """pine_cluster.foot_world with the floor of a blocked cell = the NEAREST free floor (ring by ring up to 8 cells away): inside a dense forest every
    cell is blocked (room 425 rows 15..17: the old rule took the cell's own top and put the back pines 2 rows forward); only free floors not above a raised (height >= 1)
    blocked cell's top count (tree-top paths, room 458)"""
    gf = group_floors(hm, bushes); void = void_cells(hm) if skipvoid else ()
    def floor(c):
        if c in ZFLOOR: return ZFLOOR[c]   # 2026-11-28: a CLASS B zone of the light data (ditch / ledge / deep floor, remake/recipes/proxy_cliff_rooms.py) is the drawn floor there (475 forest ditches at -40, 469 forest ledge)
        h, b = hm.get(c, (None, True))
        if h is None: return None
        if c in bushes: h -= 1   # LK_LTPLANT v3 feet (2026-11-21): a bush top is not ground (room 458: the bush strip of height 2 gave pines z 32 / 34 / 18)
        if not b: return 16 * h
        if c in void: return None   # 2026-11-21: the blocked-0 void around the room is nothing, not a floor (484: the ring search gave the void 144 -> a small pine landed in it); a tree's own blocked-0 cell inside a ground-0 room stays (711 / 601 / 475)
        if c in gf: return gf[c]   # v3: the lowest free floor around the whole blocked group (room 458: the forest behind the raised path stands on 16, not on the path's 48)
        for d in range(1, 9):
            nb = [hm[q][0] - (q in bushes) for q in ((c[0] + a, c[1] + e) for a in range(-d, d + 1) for e in range(-d, d + 1) if max(abs(a), abs(e)) == d) if q in hm and not hm[q][1] and (hm[q][0] <= h or h < 1)]   # only floors NOT ABOVE the block's top (2026-11-21, room 458: walkable tree-top paths of height 4 / 5 inside the forest gave pines feet at 64 / 80 above a bed of 48 on ground 16)
            if nb: return 16 * min(nb)
        return 16 * h
    D = U - 1184; first = None; pf = None; pc = None
    for z in range(255, min([-16] + [v - 1 for v in ZFLOOR.values()]), -1):   # down to the lowest CLASS B zone floor (475 ditches at -40)
        X = V + z + D / 2; Y = V + z - D / 2; c = (int(X // 16), int(Y // 16)); f = floor(c)
        if f is None: continue
        if first is None:
            if z <= f:
                first = (X, Y, z, c)
                if seen and z == f: return first   # the trunk is drawn and the ray meets a floor's TOP: it stands there
                if seen and pf is not None and pf < z and pc in ZDEEP:   # 2026-11-28: ... unless that floor is a CLASS B cliff INTO THE DEEP (475 front): the plant is drawn on the cliff's top edge, it stands on the top
                    Xf = V + f + D / 2; Yf = V + f - D / 2; return Xf, Yf, f, (int(Xf // 16), int(Yf // 16))
                if seen and pf is not None and pf < z: return X, Y, pf, c   # drawn, but the ray met a wall's SIDE: it stands in front of that wall on the floor it came from (room 458 bush z 18 -> 16)
                if not seen and c in gf and z == f: return first   # 2026-11-26 (bug sweep, room 488 / 490 at night: a pine's collision cell stayed a BOX in the sword light): the first floor is the ground of a
                                                       # blocked FOREST group = the plant stands in its own forest, its trunk is covered by the pines in FRONT of it; 'covered -> behind' took it through the forest
                                                       # and past the shore (488: 863,351 z 112 under the sand ridge instead of 866,403 z 128). A raised path in front (458) is a free floor: not affected
            else: pf = f; pc = c
        elif z == f and f < first[2] and c not in ZFLOOR: return X, Y, z, c   # (2026-11-28: never into a CLASS B zone behind: 475 pit pines landed in the rock wedge across the path) covered trunk / the ray met a wall's side: the next LOWER floor top behind it (user 2026-11-21)
        elif c in gf and gf[c] < first[2] and z < gf[c]: return X, Y, gf[c], c   # ... or it passed below a raised path into a blocked group: that group's ground (458: pines behind the 2 cell wide path, z 48 -> 16)
    return first

TREE_TRUNK = {(3, 1), (3, 2), (1, 3), (2, 3)}   # the big round tree's collision: a 4 x 4 block of one height with these 4 cells at the ground's height (rooms 424 451 454 458 474 484 488 501 561 564)

def foot_tree(hm, U, V):
    """bigtree foot (2026-11-21, user recording rec_20261120_1940 room 458: 'Nigels Schatten bricht beim grossen Baum um wie an einer Wand'): the big round
    tree stands on its OWN collision block (4 x 4 cells, TREE_TRUNK cells low). foot_world stopped at that block's side (458: 495,335 z 47 = half a block too
    far back and up: the block stayed as a box beside the model). Here: the block with that pattern next to the ray's hit cell; foot = its centre on the
    ground (= the trunk cells' height). Check: room 488 gives 576,656 z 128 = proxy_tree_488.py's measured axis. No such block -> foot_world."""
    w = foot_world(hm, U, V)
    if not w: return None
    cx, cy = w[3]; best = None
    for y0 in range(cy - 6, cy + 3):
        for x0 in range(cx - 6, cx + 3):
            cells = [(x0 + i, y0 + j) for i in range(4) for j in range(4)]
            if any(c not in hm for c in cells): continue
            top = {hm[(x0 + i, y0 + j)][0] for i in range(4) for j in range(4) if (i, j) not in TREE_TRUNK}
            low = {hm[(x0 + i, y0 + j)][0] for (i, j) in TREE_TRUNK}
            if len(top) == 1 and len(low) == 1 and min(top) > min(low):
                X, Y, z = 16.0 * x0 + 32, 16.0 * y0 + 32, 16 * min(low); d = abs(X - Y + 1184 - U) + abs((X + Y) / 2 - z - V)
                if best is None or d < best[0]: best = (d, X, Y, z, (x0 + 2, y0 + 2))
    return best[1:] if best and best[0] <= 24 else w

def write_models():
    src = os.path.join(ROOT, "landstalker", "data", "proxies", "tree_488.obj")   # the measured big tree (proxy_tree_488.py), moved to the origin (= its foot)
    with open(os.path.join(ROOT, "landstalker", "data", "proxies", "plant_bigtree.obj"), "w") as fo:
        fo.write("# bigtree light model = landstalker/data/proxies/tree_488.obj (remake/recipes/proxy_tree_488.py) moved by (-576, -656, -128): origin = its foot on the ground (remake/recipes/plants/plants.py)\n")
        for l in open(src):
            if l.startswith("v "): x, y, z = map(float, l.split()[1:4]); fo.write("v %g %g %g\n" % (round(x - 576, 3), round(y - 656, 3), round(z - 128, 3)))
            elif l.startswith("f "): fo.write(l)
    for name, P in (("pine", "params_pine.json"), ("small", "params_small.json"), ("bush", "params_bush.json")):
        P = json.load(open(os.path.join(HERE, P))); o = P["offset"]
        parts = pine.pine_parts(o, o, 0, P, seed=P.get("seed", 11)) if name != "bush" else bush.bush_parts(o, o, 0, P, seed=P.get("seed", 11))
        pine.write_obj(os.path.join(ROOT, "landstalker", "data", "proxies", "plant_%s.obj" % name), parts,
                       "%s light model (remake/recipes/plants/plants.py), origin = the drawn foot on the ground" % name)

ZFLOOR = {}; ZDEEP = set()
def classb_floors(room):
    """cells of the CLASS B ground ops (zones of proxy_cliff_rooms.py) -> their floor level"""
    d = json.load(open(os.path.join(ROOT, "landstalker", "data", "light_proxies.json")))["rooms"].get(str(room), [])
    out = {}
    for e in d:
        if e["op"] == "ground" and "CLASS B" in e.get("why", ""):
            x0, y0, x1, y1, z = e["cells"][:5]
            for x in range(x0, x1 + 1):
                for y in range(y0, y1 + 1):
                    out[(x, y)] = z
                    if "INTO THE DEEP" in e["why"]: ZDEEP.add((x, y))
    return out

def work(room):
    global ROM, ZFLOOR
    if ROM is None: ROM = open(sys.argv[1], "rb").read()
    ZDEEP.clear(); ZFLOOR = classb_floors(room)
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
        res = [r for r in res if (r[0], int(r[1]), int(r[2])) not in NOT_PLANTS.get(room, ())]   # NOT_PLANTS: hand-checked false hits
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
