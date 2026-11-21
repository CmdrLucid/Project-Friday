#!/usr/bin/env python3
"""place_433.py [--write] : the six stone faces of room 433 as 'mesh' light ops (one op = one light object per copy) with their OBJs in
landstalker/data/proxies/stone_face_433_K.obj. All six drawings are pixel equal to the reference cell (19,22) (checked 2026-11-21), so each copy is the
same model on its own cell: base centre = cell centre + (ox, oy) of params.json, on the ground 16. User 2026-11-21: 'passt als Lichtform'."""
import collections, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", "..")
CELLS = [(19, 22), (28, 22), (33, 22), (19, 30), (28, 30), (33, 30)]; GROUND = 16
P = json.load(open(os.path.join(HERE, "params.json")))
tmp = os.path.join(ROOT, "landstalker", "data", "proxies", ".stone_face_tmp.obj")
subprocess.run([sys.executable, os.path.join(HERE, "stone_face.py"), tmp, os.path.join(HERE, "params.json")], check=True)
src = open(tmp).read().splitlines(); os.remove(tmp)
jp = os.path.join(ROOT, "landstalker", "data", "light_proxies.json"); data = json.load(open(jp), object_pairs_hook=collections.OrderedDict)
ops = [e for e in data["rooms"].get("433", []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/stone_face_"))]
for k, (cx, cy) in enumerate(CELLS):
    dx, dy = 16 * cx + 8 + P["ox"], 16 * cy + 8 + P["oy"]; fn = "stone_face_433_%d.obj" % k
    with open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w") as f:
        f.write("# stone face %d of room 433, cell (%d,%d) (remake/recipes/stone_face/place_433.py), game coordinates\n" % (k, cx, cy))
        for l in src:
            if l.startswith("v "): x, y, z = map(float, l.split()[1:4]); f.write("v %.3f %.3f %.3f\n" % (x + dx, y + dy, z + GROUND))
            elif l.startswith("f "): f.write(l + "\n")
    ops.append(collections.OrderedDict([("op", "mesh"), ("cells", [cx, cy, cx, cy]), ("file", "proxies/" + fn), ("surface", True),
        ("why", "stone face of the swamp (collision = one 2 step block $43): our model remake/recipes/stone_face (smooth head, face + mouth to +x, IoU 0.911 on the drawing), placed by place_433.py; user 2026-11-21 'passt als Lichtform'")]))
    print("room 433: stone face %d at cell (%d,%d) -> %s" % (k, cx, cy, fn))
if "--write" in sys.argv:
    data["rooms"]["433"] = ops
    with open(jp, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False); f.write("\n")
    print("wrote", jp)
