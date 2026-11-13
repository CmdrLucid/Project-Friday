"""LIGHT PROXY: the table on legs of room 670 (MERCATOR_HOUSE_NEAR_WELL_FIRST_FLOOR; HANDOFF 0a358, user 2026-11-09: 'dann mit Tischen etc. weiter').
The collision holds the table as a solid 16 high box (cells 22..24 x 22..23): no light under it, no shadow of the legs. Here: the measured table of
remake/lib/furniture.py (top 11..16 over the whole collision footprint, four 4 unit legs 1 in from the corners), op 'mesh' with "air" (the top is
a slab) and "floor": 0 (between the legs = the room floor).  Projection U = x - y + 1184, V = (x + y) / 2 - z: corners U 1152 / 1184 / 1232 / 1200
match the drawing (8x zoom, ~/Project-Friday-Test/lktest/m670).
Run: python3 remake/tools/build_asset.py proxy_table_670
Output: landstalker/data/proxies/table_670.obj (our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_table_670/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy, furniture

PARTS = furniture.table("table", 352, 352, 400, 384, 0, 16, **furniture.MERCATOR_TABLE)
proxy.build("table_670", PARTS, "Table on legs, room 670", {}, target=(376, 368, 8), ground_z=0, px_per_unit=6, size=(600, 500))
