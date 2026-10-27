#!/usr/bin/env python3
"""roomdata.py ROM ROOM   -- reads one room from the user's ROM (landstalker/tools/romroom.py + romrender.py) and sorts every map cell into what the
remake builds there (no Blender needed; the recipe remake/recipes/room_c.py uses it as a module, the CLI prints the class map for checking).
World cell = height map cell + 12 (docs/FORMATS.md 'Height map = a real height field': world x = 16 * (hx + 12)); heights in 16 unit steps.
Classes of the BLOCKED cell groups (4-connected, same height), by their height above the highest walkable neighbour 'rel' (Massan 592, 2026-10-25):
  house  = a door cell next to it (byte 0 = $20 + height, not blocked, with a door floor type 01..04 in front); one house per door, a group with several
           doors is split between them along the door wall; rel >= 5 = TOWER
  cave   = door cells in front of a cliff (rel >= 4): an opening in the rock
  raised = rel 0 (a blocked edge of a walkable level: terrain only)
  bushes = rel 1 (one shrub per cell, the top is walkable in the original)
  fence  = rel 2 and a thin line (cells <= 1.5 * the longer bbox side)
  grove  = rel 2 and an area (pines)
  cliff  = everything else (rel >= 3 without a door): a rock column
Walkable cells: 'ground' (grass / dirt from the colour of plane B at the cell's top, '?' = no plane B pixel there = taken from the neighbours), 'statue'
(a single walkable cell clearly above all neighbours), and step edges (a walkable cell one step above a walkable neighbour to the south / east)."""
import os, sys
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "tools")
if TOOLS not in sys.path: sys.path.insert(0, TOOLS)
OFF = 12
VOID = 0x4000
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

def ground_colour(pb, tp, getpal, x, y, h):
    """mean colour of plane B around the top centre of height map cell (x, y) at height h (None = no plane B pixel there)."""
    wx = 16 * (x + OFF) + 8; wy = 16 * (y + OFF) + 8; U = wx - wy + 1184; V = (wx + wy) // 2 - 16 * h
    cs = []
    for du in (-6, -3, 0, 3, 6):
        for dv in (-3, 0, 3):
            t = pb.t.get(((U + du) // 8, (V + dv) // 8))
            if not t: continue
            i = tp(t[0], t[3], t[4])[(V + dv) % 8][(U + du) % 8]
            if i: cs.append(getpal(t[1], i))
    if not cs: return None
    return tuple(sum(c[k] for c in cs) / len(cs) for k in range(3))

def object_colour(pa, tp, getpal, x, y, z0, z1):
    """mean colour of plane A (objects) in the column above height map cell (x, y) from z0 to z1 (None = nothing drawn there)."""
    wx = 16 * (x + OFF) + 8; wy = 16 * (y + OFF) + 8; U = wx - wy + 1184; cs = []
    for z in range(z0, z1, 2):
        V = (wx + wy) // 2 - z
        for du in (-4, 0, 4):
            t = pa.t.get(((U + du) // 8, V // 8))
            if not t: continue
            i = tp(t[0], t[3], t[4])[V % 8][(U + du) % 8]
            if i: cs.append(getpal(t[1], i))
    if not cs: return None
    return tuple(sum(c[k] for c in cs) / len(cs) for k in range(3))

def kind_of(c):
    if c is None: return "?"
    r, g, b = c
    if b > r + 20 and b > g: return "water"
    return "grass" if g > r + 10 else "dirt"

def load(rom_path, room):
    import romroom, romrender
    rom = open(rom_path, "rb").read()
    g, r, pa, pb, getpal = romrender.rom_planes(rom, room)
    tp = romrender.tile_cache(g["tiles"])
    hm = romroom.arrays(r)["HM"]
    cells = {}
    for (x, y), v in hm.items():
        if v == VOID: continue
        cells[(x, y)] = dict(h=(v >> 8) & 15, blk=bool(v & 0x4000), npc=bool(v & 0x2000) and not v & 0x4000, ft=v & 0xFF)
    cells = {k: c for k, c in cells.items() if k[0] < r["hm_w"] and k[1] < r["hm_h"]}   # beyond the stream's height map area = buffer padding
    for (x, y), c in cells.items():
        c["col"] = ground_colour(pb, tp, getpal, x, y, c["h"])
    for c in cells.values(): c["kind"] = kind_of(c["col"])
    return dict(rom=rom, room=room, cells=cells, planes=(g, r, pa, pb, getpal))

def classify(R):
    cells = R["cells"]
    walk = {k for k, c in cells.items() if not c["blk"]}
    doors = [k for k, c in cells.items() if c["npc"] and any(cells.get((k[0] + dx, k[1] + dy), {}).get("ft", 0) in (1, 2, 3, 4) for dx, dy in N4)]
    # blocked groups
    seen = set(); groups = []
    for k in sorted(cells, key=lambda k: (k[1], k[0])):
        c = cells[k]
        if not c["blk"] or k in seen: continue
        st = [k]; comp = []; seen.add(k)
        while st:
            p = st.pop(); comp.append(p)
            for dx, dy in N4:
                q = (p[0] + dx, p[1] + dy)
                if q in cells and cells[q]["blk"] and q not in seen and cells[q]["h"] == c["h"]: seen.add(q); st.append(q)
        nb = {cells[q]["h"] for p in comp for dx, dy in N4 for q in [(p[0] + dx, p[1] + dy)] if q in walk}
        hi = max(nb) if nb else 0
        xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
        gd = [d for d in doors if any(abs(d[0] - p[0]) + abs(d[1] - p[1]) == 1 for p in comp)]
        rel = c["h"] - hi
        rect = len(comp) >= 0.75 * (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)
        if gd and rect and rel < 8 and min(max(xs) - min(xs), max(ys) - min(ys)) >= 2: cls = "house"
        elif gd: cls = "cave"
        elif rel <= 0: cls = "raised"
        elif rel <= 2: cls = "small"                                             # bushes / pines / fence: decided per cell below
        else: cls = "cliff"
        groups.append(dict(cls=cls, h=c["h"], base=hi if cls in ("house", "small") else c["h"], rel=rel, cells=comp, doors=gd))
    # a group without a walkable neighbour (Massan: the bush row at y 2 behind the pine row, between pines and the map edge) gets its base from the
    # neighbouring groups that have one, so its height above the ground counts (else rel = its absolute height = 'cliff')
    gof = {p: gr for gr in groups for p in gr["cells"]}
    for gr in groups:
        if gr["cls"] != "cliff" or any(q in walk for p in gr["cells"] for dx, dy in N4 for q in [(p[0] + dx, p[1] + dy)]): continue
        nbg = {id(gof[q]): gof[q] for p in gr["cells"] for dx, dy in N4 for q in [(p[0] + dx, p[1] + dy)] if q in gof and gof[q] is not gr and gof[q]["cls"] == "small"}
        if not nbg: continue
        hi = max(g_["base"] for g_ in nbg.values()); rel = gr["h"] - hi
        if 0 < rel <= 2: gr.update(cls="small", base=hi, rel=rel)
    # a group with several doors = several houses: every cell goes to the nearest door along the door wall
    out = []
    for gr in groups:
        if gr["cls"] != "house" or len(gr["doors"]) < 2: out.append(gr); continue
        for d in gr["doors"]:
            part = [p for p in gr["cells"] if min(gr["doors"], key=lambda e: (abs(e[1] - p[1]) + abs(e[0] - p[0]) * 0.01, e)) == d]
            out.append(dict(gr, cells=part, doors=[d]))
    for gr in out:
        if gr["cls"] == "house":
            gr["cls"] = "tower" if gr["rel"] >= 5 else "house"
            d = gr["doors"][0]; xs = [p[0] for p in gr["cells"]]; ys = [p[1] for p in gr["cells"]]
            gr["door_side"] = "E" if d[0] >= max(xs) and min(ys) <= d[1] <= max(ys) else "W" if d[0] <= min(xs) and min(ys) <= d[1] <= max(ys) else "S" if d[1] >= max(ys) else "N"
            gr["cells"] = sorted(set(gr["cells"]) | {d})                         # the doorway cell is part of the house
            gr["box"] = (min(xs + [d[0]]), max(xs + [d[0]]), min(ys + [d[1]]), max(ys + [d[1]]))
    g, r, pa, pb, getpal = R["planes"]
    import romrender
    tp = romrender.tile_cache(g["tiles"])
    for gr in out:
        if gr["cls"] != "small": continue
        obj = {}
        for p in gr["cells"]:
            c = object_colour(pa, tp, getpal, p[0], p[1], 16 * gr["base"], 16 * gr["base"] + 44)
            obj[p] = None if c is None else ("pine" if c[1] > 110 and c[1] > c[0] + 60 else "bush" if c[1] < 110 and c[1] > c[0] + 30 else
                                            "fence" if c[0] > c[1] - 10 and c[0] > 80 and c[0] < 130 and c[2] < c[1] else None)
        known = [v for v in obj.values() if v]
        thin = len(gr["cells"]) <= 1.5 * max(max(p[0] for p in gr["cells"]) - min(p[0] for p in gr["cells"]) + 1, max(p[1] for p in gr["cells"]) - min(p[1] for p in gr["cells"]) + 1)
        if thin and gr["rel"] == 2:                                              # a thin line of height 2 is a fence (colours there mix with the slope behind) ...
            obj = {p: "pine" if v == "pine" else "fence" for p, v in obj.items()}; known = ["fence"]   # ... except clear pines (Massan: the pine row east of the houses at y 3 is joined to the palisade)
        fill = max(set(known), key=known.count) if known else ("fence" if thin and gr["rel"] == 2 else "bush" if gr["rel"] == 1 else "pine")
        if gr["rel"] == 1 and fill == "fence": fill = "bush"
        for p in obj:
            if obj[p] is None: obj[p] = fill
        others = [v for v in obj.values() if v != "fence"]
        for p in [p for p, v in obj.items() if v == "fence" and others]:          # a lone 'fence' cell among plants = brown stems / trunks (Massan (5, 18) under the
            if not any(obj.get((p[0] + dx, p[1] + dy)) == "fence" for dx, dy in N4): # round bush): the most common plant of the group
                obj[p] = max(set(others), key=others.count)
        gr["obj"] = obj
        kinds = set(obj.values()); gr["cls"] = kinds.pop() if len(kinds) == 1 else "mixed"
    # walkable details
    statues = [k for k in walk if cells[k]["h"] >= 2 and all(cells.get((k[0] + dx, k[1] + dy), {"h": 99})["h"] <= cells[k]["h"] - 2 for dx, dy in N4)]
    steps = []                                                                   # (cell, edge 'S' / 'E') where the next walkable cell is exactly one step lower
    for k in walk:
        if k in statues: continue
        for e, (dx, dy) in (("S", (0, 1)), ("E", (1, 0))):
            q = (k[0] + dx, k[1] + dy)
            if q in walk and q not in statues and cells[q]["h"] == cells[k]["h"] - 1: steps.append((k, e))
    # ground kind for '?' cells and blocked cells: majority of the neighbours (repeated)
    for _ in range(8):
        for k, c in cells.items():
            if c["kind"] != "?": continue
            ks = [cells[q]["kind"] for dx, dy in N4 for q in [(k[0] + dx, k[1] + dy)] if q in cells and cells[q]["kind"] != "?"]
            if ks: c["kind"] = max(set(ks), key=ks.count)
    for c in cells.values():
        if c["kind"] == "?": c["kind"] = "dirt"
    R.update(groups=out, statues=statues, steps=steps, doors=doors)
    R["pines"] = cliff_pines(R, tp)
    return R

def window(R, bottom=-160):
    """the picture window (U0, V0, W, H) that shows every cell top and the room's faces down to z = bottom."""
    U = []; V = []
    for (x, y), c in R["cells"].items():
        for a in (0, 16):
            for b in (0, 16):
                wx, wy = 16 * (x + OFF) + a, 16 * (y + OFF) + b; U.append(wx - wy + 1184)
                V += [(wx + wy) / 2 - 16 * c["h"], (wx + wy) / 2 - bottom]
    U0, U1, V0, V1 = int(min(U)) - 24, int(max(U)) + 24, int(min(V)) - 64, int(max(V)) + 8
    return U0, V0, U1 - U0, V1 - V0

def visible_index(pa, pb, tp, U, V):
    """(palette line, colour index) of the picture pixel at (U, V): plane A high, B high, A low, B low (FORMATS 'Room graphics')."""
    for pl, pri in ((pa, 1), (pb, 1), (pa, 0), (pb, 0)):
        t = pl.t.get((U // 8, V // 8))
        if not t or t[2] != pri: continue
        i = tp(t[0], t[3], t[4])[V % 8][U % 8]
        if i: return (t[1], i)
    return None

def cliff_pines(R, tp, colour=(0, 7)):
    """single pines drawn on cliffs / slopes (not in the height map): blobs of the pines' bright green (palette 0 colour 7 in Massan) of one tree's
    size (16..24 x 28..34 px; larger blobs = groves, smaller = crowns behind roofs), foot = crown top + 36 px, cast along the view ray onto the
    height field (the first cell the ray meets coming from the viewer, on its top or on a rock face).  Feet on house / object cells are skipped (those trees exist already)."""
    g, r, pa, pb, getpal = R["planes"]; C = R["cells"]
    U0, V0, W, H = window(R)
    mask = {(u, v) for v in range(V0, V0 + H) for u in range(U0, U0 + W) if visible_index(pa, pb, tp, u, v) == colour}
    seen = set(); out = []; grp = {p: gr for gr in R["groups"] for p in gr["cells"]}
    top = {k: 16 * c["h"] for k, c in C.items()}
    for p in mask:
        if p in seen: continue
        st = [p]; seen.add(p); b = []
        while st:
            q = st.pop(); b.append(q)
            for du in (-2, -1, 0, 1, 2):
                for dv in (-2, -1, 0, 1, 2):
                    n = (q[0] + du, q[1] + dv)
                    if n in mask and n not in seen: seen.add(n); st.append(n)
        us = [q[0] for q in b]; vs = [q[1] for q in b]; w = max(us) - min(us) + 1; h = max(vs) - min(vs) + 1
        if not (16 <= w <= 24 and 28 <= h <= 34): continue
        U = (min(us) + max(us)) // 2; V = min(vs) + 36; d = U - 1184
        for s_ in range(4000, -400, -1):
            z = s_ / 2 - V; wx = (s_ + d) / 2; wy = (s_ - d) / 2; k = (int(wx // 16) - OFF, int(wy // 16) - OFF)
            if k in top and z <= top[k]:
                gr = grp.get(k)
                if gr is None or gr["cls"] in ("cliff", "cave", "raised"): out.append((wx, wy, z, k))      # z < top: the ray met a rock face (a slope in the picture)
                break
    return out

def text_map(R):
    cells = R["cells"]; ch = {}
    sym = dict(house="H", tower="T", cave="C", raised="r", bush="b", fence="f", pine="p", cliff="#")
    for gr in R["groups"]:
        for p in gr["cells"]: ch[p] = sym[gr["obj"][p]] if "obj" in gr else sym[gr["cls"]]
    for k in R["statues"]: ch[k] = "S"
    for k, e in R["steps"]: ch.setdefault(k, "=")
    xs = [k[0] for k in cells]; ys = [k[1] for k in cells]; rows = []
    for y in range(min(ys), max(ys) + 1):
        row = ""
        for x in range(min(xs), max(xs) + 1):
            k = (x, y)
            if k not in cells: row += " "; continue
            row += ch.get(k, {"grass": ",", "dirt": ".", "water": "~"}[cells[k]["kind"]])
        rows.append("%2d %s" % (y, row))
    return "\n".join(rows)

if __name__ == "__main__":
    R = classify(load(sys.argv[1], int(sys.argv[2])))
    print(text_map(R))
    for gr in R["groups"]:
        xs = [p[0] for p in gr["cells"]]; ys = [p[1] for p in gr["cells"]]
        print("%-6s h%2d base %2d rel %2d n%3d x%2d-%2d y%2d-%2d %s" % (gr["cls"], gr["h"], gr["base"], gr["rel"], len(gr["cells"]), min(xs), max(xs), min(ys), max(ys), gr.get("door_side", "")))
    print("statues", R["statues"], "steps", len(R["steps"]), "cliff pines", [p[3] for p in R["pines"]])
