#!/usr/bin/env python3
"""place_486.py [--write] : the four small stone blocks of room 486 (pixel-equal drawings, isolated walkable 1 step cells, ground 0) as 'mesh'
light ops (one op = one light object per block), OBJs landstalker/data/proxies/stone_cube_486_K.obj. Axis = cell centre + (ox, oy) of params.json."""
import collections, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", "..")
CELLS = [(49, 35), (57, 35), (49, 55), (57, 55)]; GROUND = 0
P = json.load(open(os.path.join(HERE, "params.json")))
tmp = os.path.join(ROOT, "landstalker", "data", "proxies", ".cube_tmp.obj")
subprocess.run([sys.executable, os.path.join(HERE, "stone_cube.py"), tmp, os.path.join(HERE, "params.json")], check=True)
src = open(tmp).read().splitlines(); os.remove(tmp)
jp = os.path.join(ROOT, "landstalker", "data", "light_proxies.json"); data = json.load(open(jp), object_pairs_hook=collections.OrderedDict)
ops = [e for e in data["rooms"].get("486", []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/stone_cube_486_"))]
for k, (cx, cy) in enumerate(CELLS):
    dx, dy = 16 * cx + 8 + P.get("ox", 0), 16 * cy + 8 + P.get("oy", 0); fn = "stone_cube_486_%d.obj" % k
    with open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w") as f:
        f.write("# stone block %d of room 486, cell (%d,%d) (remake/recipes/stone_cube_486/place_486.py), game coordinates\n" % (k, cx, cy))
        for l in src:
            if l.startswith("v "): x, y, z = map(float, l.split()[1:4]); f.write("v %.3f %.3f %.3f\n" % (x + dx, y + dy, z + GROUND))
            elif l.startswith("f "): f.write(l + "\n")
    ops.append(collections.OrderedDict([("op", "mesh"), ("cells", [cx, cy, cx + 1, cy + 1]), ("file", "proxies/" + fn), ("surface", True),   # + the cell in front: the old automatic lathe (37 high) had its centre there (drawn objects sit one cell forward)
        ("why", "small stone block (collision = an isolated walkable 1 step cell): our model remake/recipes/stone_cube_486 (block 16 x 16 x 16 with rounded edges, IoU 0.928 on the drawing; was an automatic lathe 37 high), placed by place_486.py; 2026-11-21 built while the user was away, to be checked")]))
    print("room 486: stone block %d at cell (%d,%d) -> %s" % (k, cx, cy, fn))
if "--write" in sys.argv:
    data["rooms"]["486"] = ops
    with open(jp, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False); f.write("\n")
    print("wrote", jp)
