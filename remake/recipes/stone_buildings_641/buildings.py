#!/usr/bin/env python3
"""buildings.py OUT.obj PARAMS.json : the two STONE BUILDINGS of the Mercator docks (rooms 641 / 642 / 644) as OUR OWN 3D model (2026-11-21).
Read with both planes + the height overlay: each building = a tall block (towers: collision height 6 = 96, flat top) and a lower wing (48, flat walkable
top) with small step blocks (32) at the front; the blue-green stones at the wall foot are wet stones (the brick pattern continues), NOT openings. The
automatic light shapes put hip roofs on them (wrong). Model: one box per cell column up to its collision height (`cells`: [x, y, height units]),
merged visually into the blocks; on the TOWER top edges a ring of protruding cornice stones (`cornice`: list of tower rects [x0, y0, x1, y1, ztop] in
cells, stones `cs` wide every `cstep`, proud `cp`); the door (`doors`: [x, y, z0, z1, face, width] world units) = a recess `dd` deep with a frame.
Pure Python, no ROM data (cells / heights are our reading of the collision, like data/light_proxies.json)."""
import json, sys
P = json.load(open(sys.argv[2])); Z0 = P.get("base", 0.0); V, F = [], []
def box(x0, y0, z0, x1, y1, z1):
    o = len(V); V.extend([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
    F.extend([(o, o + 3, o + 2, o + 1), (o + 4, o + 5, o + 6, o + 7), (o, o + 1, o + 5, o + 4), (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7)])
def cbox(x0, y0, z0, x1, y1, z1, c):
    """a block whose four vertical edges are chamfered by c (>= 1 unit), flat top"""
    pts = [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]; o = len(V); n = 8
    V.extend([(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts])
    for i in range(n): F.append((o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i))
    F.append(tuple(o + i for i in range(n - 1, -1, -1))); F.append(tuple(o + n + i for i in range(n)))
towers = [(x0, y0, x1, y1, zt) for x0, y0, x1, y1, zt in P.get("cornice", [])]
intower = lambda x, y: any(t[0] <= x <= t[2] and t[1] <= y <= t[3] for t in towers)
for x0, y0, x1, y1, zt in towers: cbox(16 * x0, 16 * y0, Z0, 16 * (x1 + 1), 16 * (y1 + 1), zt, P.get("tower_chamfer", 1.5))   # the towers as one block each
# merge the other cells of one height into row runs (fewer boxes, no inner seams on a flat top)
rows = {}
for x, y, h in P["cells"]:
    if not intower(x, y): rows.setdefault((y, h), []).append(x)
for (y, h), xs in rows.items():
    xs.sort(); a = xs[0]; b = a
    for x in xs[1:] + [None]:
        if x is not None and x == b + 1: b = x; continue
        box(16 * a, 16 * y, Z0, 16 * (b + 1), 16 * (y + 1), h); a = b = x
CS, CSTEP, CP, CH = P.get("cs", 4.0), P.get("cstep", 8.0), P.get("cp", 1.5), P.get("ch", 3.0)
def stone(x0, y0, z0, x1, y1, z1, face):
    """a cornice stone whose outer top edge is weathered: the top slopes down by 1 unit towards the outside"""
    o = len(V); d = 1.0
    # corners in order (x0,y1) (x0,y0) (x1,y0) (x1,y1) for the top heights below
    tops = {"-y": (z1, z1 - d, z1 - d, z1), "+y": (z1 - d, z1, z1, z1 - d), "-x": (z1 - d, z1 - d, z1, z1), "+x": (z1, z1, z1 - d, z1 - d)}[face]
    V.extend([(x0, y1, z0), (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, tops[0]), (x0, y0, tops[1]), (x1, y0, tops[2]), (x1, y1, tops[3])])
    F.extend([(o, o + 3, o + 2, o + 1), (o + 4, o + 5, o + 6, o + 7), (o, o + 1, o + 5, o + 4), (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7)])
for x0, y0, x1, y1, zt in P.get("cornice", []):   # protruding stones along the four top edges of a tower, their tops flush with the roof
    X0, Y0, X1, Y1 = 16 * x0, 16 * y0, 16 * (x1 + 1), 16 * (y1 + 1)
    t = X0 + 1
    while t + CS <= X1 - 1:
        stone(t, Y0 - CP, zt - CH, t + CS, Y0 + 0.5, zt + 0.5, "-y"); stone(t, Y1 - 0.5, zt - CH, t + CS, Y1 + CP, zt + 0.5, "+y"); t += CSTEP
    t = Y0 + 1
    while t + CS <= Y1 - 1:
        stone(X0 - CP, t, zt - CH, X0 + 0.5, t + CS, zt + 0.5, "-x"); stone(X1 - 0.5, t, zt - CH, X1 + CP, t + CS, zt + 0.5, "+x"); t += CSTEP
DD = P.get("dd", 2.0)
for x, y, z0, z1, face, w in P.get("doors", []):   # face '+x': the door sits in the wall plane x = const, centred at y, width w; a frame proud 1
    if face == "+x":
        box(x - DD, y - w / 2, z0, x + 0.3, y + w / 2, z1)          # the recess shell (dark door leaves at its back, sunk by dd)
        for s in (-1, 1): box(x, y + s * (w / 2 + 0.5) - 0.75, z0, x + 1.0, y + s * (w / 2 + 0.5) + 0.75, z1 + 1.5)   # frame posts
        box(x, y - w / 2 - 1.25, z1, x + 1.0, y + w / 2 + 1.25, z1 + 1.5)   # lintel
with open(sys.argv[1], "w") as f:
    f.write("# stone buildings of the Mercator docks (remake/recipes/stone_buildings_641/buildings.py), game coordinates\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
