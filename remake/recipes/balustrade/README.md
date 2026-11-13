# Balustrade (castle stairwells) - near-final 3D model + light shape, since 2026-11-13

Recipe only (no ROM data). References: room 95 (stairwell rail, cells x 19 rows 19..27 + row 27 x 15..19), room 89 (x 28 rows 19..26), later 62 / 59..61.
`balustrade.py ROOM OUTDIR` -> `rail_ROOM.obj` (plinth, turned balusters every 8 units, posts with ball caps) + `rail_ROOM_rail.obj` (rounded handrail, op `air`).
Measured with remake/tools/proxy_overlay.py at 6x / 10x (outer edge, handrail top, baluster phase on the 8 grid: the model's balusters sit on the drawn ones).
Replaces the box proxies (4 x 4 posts + slab) of 2026-11-12 (user 2026-11-13: 'bitte immer fuer die Lichtformen 3D-Blender-Modelle machen').
Previews (local): `~/.landstalker_remake/assets/balustrade/balustrade_v2_corner_clay.png` (v2: mitred corner as drawn, posts), v1 (crossed bars at the corner: user "wo es um die Ecke geht ... noch nicht gut").

Room 62 (+ 59 / 60 / 61): `hall62.py OUTDIR` writes the six `rail_62_*.obj` (gallery, left / right stair: solid parts + `_rail` handrails) with the same parts
(turned balusters, posts with ball caps (top t + 28 left / t + 24 right), round handrail sloped on the stairs, stepped stone stringer, landing edge).
Gallery posts measured again 2026-11-13 on the whole gallery: x 326 / 410 / 490 / 554 / 634 / 702 (the box proxy had 4). Preview: `balustrade_62_v1_clay.png`.

Bedroom tables (tileset 15, rooms 63 / 64 / 65 / 66 / 67 / 77): `remake/lib/furniture.py castle_room_table_mesh` (thin top 3.5 with rounded edges, straight square
legs under the corners), measured on 67 and 63 (10x). Preview: `~/.landstalker_remake/assets/table15/table15_v1_clay.png`.
