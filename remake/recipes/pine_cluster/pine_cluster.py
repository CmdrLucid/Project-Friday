#!/usr/bin/env python3
"""pine_cluster.py ROM SURVEY.log [ROOMS] [--write] [--png DIR]   -- PINE CLUSTERS as single pines (HANDOFF -207, user 2026-11-15
'generell bei solchen Gruppen einzelne Tannen').

The automatic outdoor light shapes take a group of drawn pines that touch each other as ONE object = one sprite lathe (room 636 #6:
r 17, one shadow for three pines).  This tool finds every drawn pine of such a group and gives each its own near-final 3D model
(the approved style C pine of remake/recipes/pine_court/pine.py, WILD variant fitted to the forest pine sprite: params_light.json).

How (no ROM data in git: the template is rebuilt from the ROM on every run):
  1. template = the forest pine sprite (palette indices) where >= 6 of 7 free standing pines in rooms 636 / 632 agree (their
     backgrounds differ, the pine does not); 968 pixels, foot pixel = the lathe foot (U = x - y + 1184, V = (x + y) / 2 - z).
  2. candidate groups = lathes (and, since 2026-11-19, solid block domes) of the survey log (tools/proxysurvey.py --run: LANDSTALKER_LIGHTING_DBG=5 'proxy: room R #n lathe at
     X,Y z Z0..Z1 max r RR') that are wider (r >= 13) or taller (>= 56) than one pine (r 11, 47 high).
  3. around each candidate the room picture (tools/romrender.py, no running game) is searched on the CELL LATTICE (pine feet sit at
     U % 16 == 0, V % 8 == 7): a pine is where >= 50 % of the whole template or >= 60 % of its crown top (rows above the widest tier;
     pines half hidden behind the front ones) match.  Feet in world units: the view ray through the foot pixel meets the floor of the
     height map (blocked tree cells take their free neighbours' floor); the foot cell must be a BLOCKED cell raised above that floor
     (the game's collision of the pine: the room data has no 'pine' flag, the collision alone cannot tell a pine from a crate).
  4. pines whose foot cells touch (8 neighbours) form a group; a group of >= 2 near a candidate lathe becomes ONE mesh op
     (data/light_proxies.json, op 'mesh', 'surface': the op drops the automatic lathe(s) whose foot lies in its rectangle).
     Rectangles that would also drop a hip (house / wall shape) are skipped and reported.
--write: OBJs data/proxies/pine_cl_ROOM_K.obj + ops (old 'pine cluster' ops of the room are replaced); without it only a report.
--png DIR: room picture with the found feet (red = group pine, orange = lone pine) and candidate lathes (magenta) for the eye check."""
import json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "landstalker", "tools")); sys.path.insert(0, os.path.join(HERE, "..", "pine_court"))
import romrender as R, proxysurvey as PS, pine

INST = [(636, 463, 543, 16), (636, 463, 863, 16), (636, 239, 959, 16), (632, 431, 991, 16), (632, 495, 991, 16), (632, 639, 991, 16), (632, 719, 991, 16)]   # free standing forest pines (lathe feet from the survey)
TW, TH, FX, FY = 32, 60, 16, 56          # template box, foot pixel inside it
TOPROW = FY - 26                         # crown top part = rows above the widest tier
TAG = "pine cluster"

_planes = {}
def planes(rom, room):
    if room not in _planes: _planes[room] = R.rom_planes(rom, room)
    return _planes[room]

def window(rom, room, x0, y0, w, h):
    g, r, pa, pb, getpal = planes(rom, room)
    R.compose(pa, pb, getpal, x0, y0, w, h, (0, 0, 0), g['tiles'])
    return R.compose.idx

def template(rom):
    from collections import Counter
    crops = [window(rom, room, X - Y + 1184 - FX, (X + Y) // 2 - Z - FY, TW, TH) for room, X, Y, Z in INST]
    m = {}
    for i in range(TW * TH):
        v, c = Counter(cr[i] for cr in crops).most_common(1)[0]
        if v and c >= 6: m[i] = v
    return m

def lathes(log, room):
    out = []
    for l in open(log):
        mm = re.search(r"proxy: room %d #(\d+) lathe at (\d+),(\d+) z (-?\d+)\.\.(-?\d+) max r (\d+)" % room, l)
        if mm: out.append(tuple(map(int, mm.groups())))
        md = re.search(r"proxy: room %d #(\d+) solid block dome at (\d+),(\d+) z (-?\d+)\.\.(-?\d+) r (\d+)" % room, l)   # 2026-11-19 (room 453: a 2 x 2 pine group on a blocked block became ONE dome, r 16): domes are candidates too
        if md: out.append(tuple(map(int, md.groups())))
    return list(dict.fromkeys(out))

def hips(log, room):
    out = []
    for l in open(log):
        mm = re.search(r"proxy: room %d #(\d+) hip x (-?\d+)\.\.(-?\d+) y (-?\d+)\.\.(-?\d+)" % room, l)
        if mm: n, x0, x1, y0, y1 = map(int, mm.groups()); out.append((n, ((x0 + x1) // 2) >> 4, ((y0 + y1) // 2) >> 4))
    return list(dict.fromkeys(out))

def find_pines(rom, room, mask, U0, V0, thr=0.5, tthr=0.6):
    """pines whose foot pixel lies in U0 +- 64, V0 - 96 .. V0 + 72 (lattice points only) -> [(U, V, full, top)]"""
    top = {k: v for k, v in mask.items() if k // TW <= TOPROW}
    x0, y0, w, h = U0 - 64 - FX, V0 - 96 - FY, 128 + TW, 168 + TH
    img = window(rom, room, x0, y0, w, h); hits = []
    for V in range(V0 - 96, V0 + 73):
        if V % 8 != 7: continue
        for U in range(U0 - 64, U0 + 65):
            if U % 16: continue
            bx, by = U - FX - x0, V - FY - y0
            f = sum(1 for k, v in mask.items() if img[(by + k // TW) * w + bx + k % TW] == v) / len(mask)
            t = sum(1 for k, v in top.items() if img[(by + k // TW) * w + bx + k % TW] == v) / len(top)
            if f >= thr or t >= tthr: hits.append((U, V, f, t))
    return hits

def foot_world(hm, U, V):
    def floor(c):
        h, b = hm.get(c, (None, True))
        if h is None: return None
        if not b: return 16 * h
        nb = [hm[(c[0] + a, c[1] + d)][0] for a in (-1, 0, 1) for d in (-1, 0, 1) if (c[0] + a, c[1] + d) in hm and not hm[(c[0] + a, c[1] + d)][1]]
        return 16 * min(nb) if nb else 16 * h
    D = U - 1184
    for z in range(255, -16, -1):
        X = V + z + D / 2; Y = V + z - D / 2; c = (int(X // 16), int(Y // 16)); f = floor(c)
        if f is not None and z <= f: return X, Y, z, c
    return None

def groups(feet):
    left = list(range(len(feet))); out = []
    while left:
        st = [left.pop(0)]; g = []
        while st:
            i = st.pop(); g.append(i)
            for j in left[:]:
                if max(abs(feet[i][3][0] - feet[j][3][0]), abs(feet[i][3][1] - feet[j][3][1])) <= 1: left.remove(j); st.append(j)
        out.append(sorted(g))
    return out

def is_cand(l):
    """a lathe that is wider or taller than ONE pine (r 11, 47 high) but still tree like (flat discs r 28 / 1 high and trunk stubs r 2 are no clusters)"""
    n, X, Y, z0, z1, rr = l; h = z1 - z0
    return rr >= 8 and h >= 30 and (rr >= 13 or h >= 56)

def survey_room(rom, log, room, mask):
    L = lathes(log, room); cand = [l for l in L if is_cand(l)]
    if not cand: return [], [], L
    hm = PS.heights(rom, room); seen = {}; per = []
    for l in cand:
        n, X, Y, z0, z1, rr = l; lc = (X >> 4, Y >> 4); mine = []
        for U, V, f, t in find_pines(rom, room, mask, X - Y + 1184, (X + Y) // 2 - z0):
            w = foot_world(hm, U, V)
            if not w or max(abs(w[3][0] - lc[0]), abs(w[3][1] - lc[1])) > 2: continue   # only the pines of THIS lathe's drawn group (its foot = the group's front)
            hb = hm.get(w[3])
            if not hb or not hb[1] or 16 * hb[0] <= w[2]: continue   # ROOM DATA CHECK (user 2026-11-16): a pine stands on a BLOCKED cell of the height map, raised above its foot (636: the 2 x 2 group = 4 blocked cells, height 48 on floor 16); a drawn match on a free cell is a shifted copy
            if (U, V) not in seen: seen[(U, V)] = (w[0], w[1], w[2], w[3], max(f, t), U, V, f)
            mine.append((U, V))
        if len(mine) >= 2: per.append([l, set(mine)])
    merged = []
    for l, m in per:   # candidates sharing a pine = one group
        for g in merged:
            if g[1] & m: g[0].append(l); g[1] |= m; break
        else: merged.append([[l], set(m)])
    res = []
    for ls, m in merged:
        pts = [seen[k] for k in sorted(m)]
        full = [p for p in pts if p[7] >= 0.45]
        if not any(p[7] >= 0.7 for p in full) or len(pts) < 2: continue   # a real group shows at least one whole pine clearly (dense forest floors of 461 / 564 / 571 match only crown tops)
        strong = [q for q in pts if q[7] >= 0.7]
        pts = [p for p in pts if p[7] >= 0.7 or any(abs(q[5] - p[5]) <= 16 and 8 <= q[6] - p[6] <= 24 for q in strong)]   # a weakly matched pine (crown top only) must stand right BEHIND a whole one that hides its trunk; a weak match with nothing in front is a shifted copy of a neighbour (row of 475)
        bycell = {}
        for q in pts:
            if q[3] not in bycell or q[4] > bycell[q[3]][4]: bycell[q[3]] = q
        if len(bycell) < len(pts): print("room %d: group at cell %d,%d left out (two drawn pines map onto one cell: a forest edge on a step, not a cluster)" % (room, pts[0][3][0], pts[0][3][1])); continue
        far = [l for l in ls if not any(abs((l[1] - l[2] + 1184) - q[5]) <= 24 and -64 <= ((l[1] + l[2]) // 2 - l[3]) - q[6] <= 24 for q in pts)]
        if far: print("room %d: group at cell %d,%d left out (lathe %s stands away from the pines: it is something else, e.g. a bush)" % (room, pts[0][3][0], pts[0][3][1], ",".join("#%d" % l[0] for l in far))); continue
        if len(pts) > 8: print("room %d: group of %d pines at cell %d,%d left out (forest, not a cluster)" % (room, len(pts), pts[0][3][0], pts[0][3][1])); continue
        xs = [p[3][0] for p in pts] + [l[1] >> 4 for l in ls]; ys = [p[3][1] for p in pts] + [l[2] >> 4 for l in ls]
        rect = [min(xs), min(ys), max(xs), max(ys)]
        drop = [l for l in L if rect[0] <= l[1] >> 4 <= rect[2] and rect[1] <= l[2] >> 4 <= rect[3]]
        res.append(dict(pines=pts, lathes=drop, rect=rect))
    return res, list(seen.values()), L

def main():
    args = sys.argv[1:]; write = "--write" in args
    pngdir = args[args.index("--png") + 1] if "--png" in args else None
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and not (i and args[i - 1] == "--png")]
    rom = open(pos[0], "rb").read(); log = pos[1]
    rooms = [int(r) for r in pos[2].split(",")] if len(pos) > 2 else sorted({int(m) for m in re.findall(r"proxy: room (\d+) #\d+ lathe", open(log).read())})
    P = json.load(open(os.path.join(HERE, "params_light.json"))); off = P["offset"]
    mask = template(rom); print("pine_cluster: template %d pixels from %d free standing pines" % (len(mask), len(INST)), flush=True)
    lp_path = os.path.join(ROOT, "landstalker", "data", "light_proxies.json"); LP = json.load(open(lp_path)); total = 0
    for room in rooms:
        res, feet, L = survey_room(rom, log, room, mask)
        H = hips(log, room); ops = []
        for k, gr in enumerate(res):
            x0, y0, x1, y1 = gr["rect"]
            bad = [h for h in H if x0 <= h[1] <= x1 and y0 <= h[2] <= y1]
            print("room %d group %d: %d pines, cells %d..%d x %d..%d, drops lathe %s%s" % (room, k, len(gr["pines"]), x0, x1, y0, y1,
                  ",".join("#%d(r %d, %d high)" % (l[0], l[5], l[4] - l[3]) for l in gr["lathes"]), ("  SKIPPED: would drop hip " + ",".join("#%d" % h[0] for h in bad)) if bad else ""))
            for p in gr["pines"]: print("    pine foot %.0f,%.0f z %d (cell %d,%d) match %.2f" % (p[0], p[1], p[2], p[3][0], p[3][1], p[4]))
            if bad: continue
            if write:
                parts = []
                for i, p in enumerate(gr["pines"]): parts += pine.pine_parts(p[0] + off, p[1] + off, p[2], P, seed=room * 7 + 31 * k + i)
                f = "proxies/pine_cl_%d_%d.obj" % (room, k)
                pine.write_obj(os.path.join(ROOT, "landstalker", "data", f), parts, "pine cluster %d of room %d as single pines (remake/recipes/pine_cluster)" % (k, room))
                ops.append({"op": "mesh", "cells": [x0, y0, x1, y1], "file": f, "surface": True, "floor": min(p[2] for p in gr["pines"]),
                            "why": "%s: %d drawn pines detected as one lathe object (one shadow); each pine its own style C pine model, feet by template match (remake/recipes/pine_cluster, user 2026-11-15 'generell bei solchen Gruppen einzelne Tannen')" % (TAG, len(gr["pines"]))})
        total += len(ops)
        if write and (ops or any(TAG in e.get("why", "") for e in LP["rooms"].get(str(room), []))):
            keep = [e for e in LP["rooms"].get(str(room), []) if not e.get("why", "").startswith(TAG)]
            LP["rooms"][str(room)] = keep + ops
        if pngdir and res:
            g, r, pa, pb, getpal = planes(rom, room); cells = list(pb.t) + list(pa.t)
            c0 = min(c for c, _ in cells) * 8; r0 = min(q for _, q in cells) * 8; W = (max(c for c, _ in cells) + 1) * 8 - c0; Hh = (max(q for _, q in cells) + 1) * 8 - r0
            rgb = bytearray(R.compose(pa, pb, getpal, c0, r0, W, Hh, (0, 0, 0), g['tiles']))
            def dot(U, V, col, n=2):
                for a in range(-n, n + 1):
                    for b in range(-n, n + 1):
                        x, y = U - c0 + a, V - r0 + b
                        if 0 <= x < W and 0 <= y < Hh: rgb[(y * W + x) * 3:(y * W + x) * 3 + 3] = bytes(col)
            gp = {(p[5], p[6]) for gr in res for p in gr["pines"]}
            for p in feet: dot(p[5], p[6], (255, 0, 0) if (p[5], p[6]) in gp else (255, 160, 0))
            for l in L:
                if is_cand(l): dot(l[1] - l[2] + 1184, (l[1] + l[2]) // 2 - l[3], (255, 0, 255), 3)
            os.makedirs(pngdir, exist_ok=True); R.png(os.path.join(pngdir, "pines_%d.png" % room), W, Hh, rgb)
    if write:
        with open(lp_path, "w") as fo: fo.write(json.dumps(LP, indent=2, ensure_ascii=False) + "\n")
        print("pine_cluster: %d ops written to %s" % (total, lp_path))

if __name__ == "__main__":
    main()
