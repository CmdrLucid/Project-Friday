# Balustrade (castle stairwells) - near-final 3D model + light shape, since 2026-11-13

Recipe only (no ROM data). References: room 95 (stairwell rail, cells x 19 rows 19..27 + row 27 x 15..19), room 89 (x 28 rows 19..26), later 62 / 59..61.
`balustrade.py ROOM OUTDIR` -> `rail_ROOM.obj` (plinth, turned balusters every 8 units, posts with ball caps) + `rail_ROOM_rail.obj` (rounded handrail, op `air`).
Measured with remake/tools/proxy_overlay.py at 6x / 10x (outer edge, handrail top, baluster phase on the 8 grid: the model's balusters sit on the drawn ones).
Replaces the box proxies (4 x 4 posts + slab) of 2026-11-12 (user 2026-11-13: 'bitte immer fuer die Lichtformen 3D-Blender-Modelle machen').
Previews (local): `~/.landstalker_remake/assets/balustrade/balustrade_v1_detail_clay.png`, `balustrade_95_v1_clay.png`.
