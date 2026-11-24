#!/usr/bin/env python3
"""place_739.py [--write] : the STONE PILLARS (one drawing: room 739's two pixel-equal pillars, and the same pillar in other rooms) as 'mesh' light ops
(one op = one light object per pillar), OBJs landstalker/data/proxies/pillar_ROOM_K.obj. Axis = cell centre + (ox, oy) of params.json.
  739: cells (24,15) and (19,15), blocked $43 on ground 0 (2026-11-21).
  426: the two pillars beside the cave mouth below the waterfall, cells (46,43) and (46,48), blocked height 48 on ground 0 (2026-11-24): the same
       outline as 739 in another palette (moss / grass in front: silhouette IoU 0.76 / 0.65 = the grass of layer A and a bush in front of the second
       one's foot), template axis at the cell centre in both rooms (U 1232 V 720 / U 1152 V 760 = cell centre, ground 0)."""
import collections, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", "..")
ROOMS = collections.OrderedDict([
    ("739", ([(24, 15), (19, 15)], 0, "2026-11-21 built while the user was away, to be checked")),
    ("426", ([(46, 43), (46, 48)], 0, "room 426 cave mouth: the 739 pillar drawing (same outline, mossy palette), cells blocked 48 on ground 0; 2026-11-24 built while the user was away, to be checked")),
])
P = json.load(open(os.path.join(HERE, "params.json")))
tmp = os.path.join(ROOT, "landstalker", "data", "proxies", ".pillar_tmp.obj")
subprocess.run([sys.executable, os.path.join(HERE, "pillar.py"), tmp, os.path.join(HERE, "params.json")], check=True)
src = open(tmp).read().splitlines(); os.remove(tmp)
jp = os.path.join(ROOT, "landstalker", "data", "light_proxies.json"); data = json.load(open(jp), object_pairs_hook=collections.OrderedDict)
for room, (cells, ground, note) in ROOMS.items():
    ops = [e for e in data["rooms"].get(room, []) if not (e.get("op") == "mesh" and e.get("file", "").startswith("proxies/pillar_%s_" % room))]
    for k, (cx, cy) in enumerate(cells):
        dx, dy = 16 * cx + 8 + P.get("ox", 0), 16 * cy + 8 + P.get("oy", 0); fn = "pillar_%s_%d.obj" % (room, k)
        with open(os.path.join(ROOT, "landstalker", "data", "proxies", fn), "w") as f:
            f.write("# stone pillar %d of room %s, cell (%d,%d) (remake/recipes/pillar_739/place_739.py), game coordinates\n" % (k, room, cx, cy))
            for l in src:
                if l.startswith("v "): x, y, z = map(float, l.split()[1:4]); f.write("v %.3f %.3f %.3f\n" % (x + dx, y + dy, z + ground))
                elif l.startswith("f "): f.write(l + "\n")
        ops.append(collections.OrderedDict([("op", "mesh"), ("cells", [cx, cy, cx, cy]), ("file", "proxies/" + fn), ("surface", True),
            ("why", "stone pillar (collision = one 3 step block $43): our parts model remake/recipes/pillar_739 (square plinth / abacus, round shaft, rings, echinus; IoU 0.857 on the drawing), placed by place_739.py; " + note)]))
        print("room %s: pillar %d at cell (%d,%d) -> %s" % (room, k, cx, cy, fn))
    if "--write" in sys.argv: data["rooms"][room] = ops
if "--write" in sys.argv:
    with open(jp, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False); f.write("\n")
    print("wrote", jp)
