#!/usr/bin/env python3
"""place_739.py [--write] : the two stone pillars of room 739 (pixel-equal drawings, cells (24,15) and (19,15), blocked $43 on ground 0) as 'mesh'
light ops (one op = one light object per pillar), OBJs landstalker/data/proxies/pillar_739_K.obj. Axis = cell centre + (ox, oy) of params.json."""
import collections, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", "..")
CELLS = [(24, 15), (19, 15)]; GROUND = 0
P = json.load(open(os.path.join(HERE, "params.json")))
tmp = os.path.join(ROOT, "landstalker", "data", "proxies", ".pillar_tmp.obj")
subprocess.run([sys.executable, os.path.join(HERE, "pillar.py"), tmp, os.path.join(HERE, "params.json")], check=True)
src = open(tmp).read().splitlines(); os.remove(tmp)
jp = os.path.join(ROOT, "landstalker", "data", "light_proxies.json"); data = json.load(open(jp), object_pairs_hook=collections.OrderedDict)
ops = [e for e in data["rooms"].get("739", []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/pillar_739_"))]
for k, (cx, cy) in enumerate(CELLS):
    dx, dy = 16 * cx + 8 + P.get("ox", 0), 16 * cy + 8 + P.get("oy", 0); fn = "pillar_739_%d.obj" % k
    with open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w") as f:
        f.write("# stone pillar %d of room 739, cell (%d,%d) (remake/recipes/pillar_739/place_739.py), game coordinates\n" % (k, cx, cy))
        for l in src:
            if l.startswith("v "): x, y, z = map(float, l.split()[1:4]); f.write("v %.3f %.3f %.3f\n" % (x + dx, y + dy, z + GROUND))
            elif l.startswith("f "): f.write(l + "\n")
    ops.append(collections.OrderedDict([("op", "mesh"), ("cells", [cx, cy, cx, cy]), ("file", "proxies/" + fn), ("surface", True),
        ("why", "stone pillar (collision = one 3 step block $43): our parts model remake/recipes/pillar_739 (square plinth / abacus, round shaft, rings, echinus; IoU 0.857 on the drawing), placed by place_739.py; 2026-11-21 built while the user was away, to be checked")]))
    print("room 739: pillar %d at cell (%d,%d) -> %s" % (k, cx, cy, fn))
if "--write" in sys.argv:
    data["rooms"]["739"] = ops
    with open(jp, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False); f.write("\n")
    print("wrote", jp)
