# Armour knight (Mercator houses, tileset 2) - light shape + remake model, work in progress since 2026-11-11

Recipe only (no ROM data). Reference: room 678 cell (30, 26); `remake/tools/rom_picture.py ROM 678 1216 392 64 80 DIR`; the knight's own pixels =
the layer A component at the breastplate, black pixels only next to a coloured one (the black blob under the feet is a painted shadow) -> a local
`mask678.json` (never in git). Cells: top block $19C (678 679: 30 / 33, 26; 695 696 697 719 720: 34, 23) and $2D7 (695 696 697 719 720: 23, 23), all the
same drawing. The castle's dark armour on a stand (tileset 15, $0B5: 63 64 83 84 93) is ANOTHER object (no legs, a pole with a round foot): later.

- `knight.py OUT.obj [params.json]`: the figure from parts in pure Python (ellipsoids, tapered capsules, lathes, a bent plate): sabatons, greaves, knee
  cops, cuisses, fauld, breastplate, collar, great helm + crest, pauldrons, arms, gauntlet on the lance, lance (shaft, tassel, leaf head), kite shield.
  The lance and the shield are placed by their measured room offsets from the cell centre; the body by `body`, `yaw` (legs), `twist` (upper body), `splay`.
- `chk.py OBJ MASK.json U0 V0`: projection check + character map. Exact game view beside the sprite: `../church_angel_sculpt/gameview.py` with
  GV_U0 1216 GV_V0 392 GV_W 64 GV_H 80.
- v1 (2026-11-11): blockout, IoU 0.824 (71 px outside, 108 missed), yaw 0 (it faces +y, out of the wall), twist 25, feet turned out 22. Read from the
  fit: the drawing follows the sprite convention (level shoulders, feet pointing in two directions), so no single facing fits everything.
  Preview `~/.landstalker_remake/assets/knight/knight_v1.png`. Waiting for the user's look before the details (plates, visor, hands, shield rim).
- v2 / v3 (2026-11-11, user 'ja', then 'diese 2 vertikalen Linien sind noch komisch'): plate-armour details (pointed sabatons, shin ridges, winged knee
  cops, fauld of three hoops, belt, collar, helm with brow rim and eye-slit ledge, ONE plume falling to the side, pauldron lames, couters, gauntlet cuff +
  fist, lance with butt / tassel tufts / socket / leaf head, shield with a raised rim); the stuck-on keel and nasal ridge removed. The feet point in two
  directions as drawn (`splay_r` 45, `splay_l` 30). IoU 0.817 (71 outside, 115 missed), ~10000 faces.
- IN THE LIGHT since 2026-11-11: `remake/tools/furniture_ops.py` knights() / knight_obj() -> `data/proxies/knight_ROOM[_k].obj` (14 knights, 7 rooms).
  A wall block west / east of the cell: `xmin` / `xmax` -> the lance / shield SLIDE ALONG THE VIEW RAY to the cell's edge (same game picture, nothing
  inside the wall). 678 is not reachable by warp (black); checked in 695 (`695:27.08,27.08,0010`): no boxes or cut walls; edge pixels at the corner
  knight 415 -> 563 (shading on the figure where the model and the drawing differ), whole picture 3699 -> 3826.

