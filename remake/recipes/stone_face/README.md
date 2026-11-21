# Stone face (swamp, room 433) - light model / remake form (2026-11-21, WAITS for the user's OK on the clay sheet)

Six copies in room 433 on single blocked cells `$43` (top 48 on ground 16): cells (19,22) (28,22) (33,22) (19,30) (28,30) (33,30); until now catalogue lathes.
Reference copy: cell (19,22), base centre x 312 y 360 z 16 (picture U 1136 V 320). Drawn ~38 units tall (taller than its 32 high collision), face (open mouth) to +x, turned ~15 deg towards +y.

`python3 stone_face.py OUT.obj params.json` - smooth head profile (foot radius -> widest radius, elliptic dome), deeper towards the face (`sx`),
face side flattened, mouth = recess, brow ledge. `params.json` = fit on the drawn silhouette (holes filled; score = covered - 12 x outside):
IoU 0.911, 1 px outside, 90 px missed (a 1 px rim). Fit / sheet tools are local (~/Project-Friday-Test/lktest/swamp: fit.py, map.py; sheet Mockups/steingesicht_433.png).
Not yet in data/light_proxies.json.
