#!/usr/bin/env python3
"""place.py [--write] : the stone MOORING POSTS of the Mercator docks (rooms 641 / 642 / 644 = one map; three pixel-equal copies per room on walkable
2 step cells (25,37) (35,30) (57,26), ground 16) as 'mesh' light ops, one per post: data/proxies/bollard_ROOM_K.obj. The profile (params.json
'profile': flared foot, waist, cap underside with rim, elliptic dome; fitted on the drawing: IoU 0.923, 0 px outside) is turned by lathe.py."""
import collections, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..", "..")
CELLS = [(25, 37), (35, 30), (57, 26)]; ROOMS = (641, 642, 644); GROUND = 16   # room 643 (docks before the Sunstone is in the lighthouse, same map) uses the 641 files: its ops were copied from 641 on 2026-11-24 (all docks models)
P = json.load(open(os.path.join(HERE, "params.json")))
jp = os.path.join(ROOT, "landstalker", "data", "light_proxies.json"); data = json.load(open(jp), object_pairs_hook=collections.OrderedDict)
for room in ROOMS:
    ops = [e for e in data["rooms"].get(str(room), []) if not e.get("file", "").startswith("proxies/bollard_")]
    for k, (cx, cy) in enumerate(CELLS):
        Q = dict(P); Q["axis"] = [16 * cx + 8, 16 * cy + 8]; Q["ground"] = GROUND; Q["name"] = "mooring post %d of room %d" % (k, room)
        tmp = os.path.join(ROOT, "landstalker", "data", "proxies", ".bollard.json"); json.dump(Q, open(tmp, "w"))
        fn = "bollard_%d_%d.obj" % (room, k)
        if "--write" in sys.argv: subprocess.run([sys.executable, os.path.join(HERE, "lathe.py"), os.path.join(ROOT, "landstalker", "data", "proxies", fn), tmp], check=True)
        os.remove(tmp)
        ops.append(collections.OrderedDict([("op", "mesh"), ("cells", [cx, cy, cx, cy]), ("file", "proxies/" + fn), ("surface", True),
            ("why", "stone mooring post of the docks (collision = a walkable 2 step cell): our lathe remake/recipes/bollard_641 (flared foot, waist, mushroom cap; IoU 0.923, 0 px out), placed by place.py; 2026-11-21 built while the user collects feedback, to be checked")]))
        print("room %d: mooring post %d at cell (%d,%d) -> %s" % (room, k, cx, cy, fn))
    if "--write" in sys.argv: data["rooms"][str(room)] = ops
if "--write" in sys.argv:
    with open(jp, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False); f.write("\n")
    print("wrote", jp)
