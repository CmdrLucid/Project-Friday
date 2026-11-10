# MODELS - every 3D form, its reference in the game and its state

One entry per model (user 2026-11-10: 'notiere zum jeweiligen Modell, welche Referenz im Spiel es ist, damit spaetere Sessions einfacher nacharbeiten
koennen'). RULE (same day): every form is measured EXACTLY on the drawing and its GEOMETRY is built close to the final remake version right away
(materials later); the light uses that geometry (`landstalker/data/proxies/*.obj`, ops in `landstalker/data/light_proxies.json`).

Lessons for the modelling work: `MODELING_LESSONS.md` (read first).

## How to look at a reference
- Picture of a room from your own ROM (local, never in git): `python3 remake/tools/rom_picture.py ROM ROOM U0 V0 W H OUTDIR` -> `full.png` (both planes),
  `layerA.png` (objects with alpha). Picture coordinates: `U = x - y + 1184`, `V = (x + y) / 2 - z` (game units, 1 cell = 16).
- Cell heights / blocks: `landstalker/tools/blockcat.py` (`cells(rom, room)` = {(x, y): (height steps, blocked, top block layer A, layer B)}), cells = height map index + 12.
- Code: shapes in `remake/lib/furniture.py`, placement (finders + light ops) in `remake/tools/furniture_ops.py`
  (`python3 remake/tools/furniture_ops.py ROM --write` rewrites the ops + OBJs; ~2 min, the room pictures are cached in /tmp/lk_furn_pic_*).
- Fit / check scripts of the first versions are on the Deck in `~/lktest/<dir>/` (not in git; the numbers they produced are in furniture.py).
- Silhouette rule: the object's OWN pixels (by colour; layer A also holds PAINTED SHADOWS of objects), no part outside the drawing; check by projecting
  the real triangles (e.g. `~/lktest/angel3/objcheck.py OBJ`). Detail may move along the view ray (1, 1, 1): the game picture stays identical.

## State legend
LIGHT = exact light shape (silhouette measured, geometry simple). NEAR-FINAL = geometry close to the final remake model (details), no material yet.
FINAL = with material, approved by the user.

---

## Church angel statue  (`furniture.CHURCH_ANGEL4`, `church_angel4(floor)`; ops by `church_angels()`)
- Game: churches, tileset 3, rooms 613 614 699 700 721 (pixel-identical there). Stands in a full-height NICHE of the -x wall: niche 1 cell deep
  (x 368..384), 4 wide (cells 23 x 26..29, y 416..480); pedestal 1 x 2 cells (23 x 27..28), 16 high on the dais floor 16, red top.
  These cells are VOID in the height map -> data op `ground` (LK_LTGROUND v1): pedestal 32, niche floor 16.
- Reference: room 613, picture window U0 1064 V0 280 (96 x 112); statue axis (375.75, 449.25), foot on the pedestal top z 32 (foot front at picture V 383).
  Statue colours: gold / brown / black outline; NOT its painted wall shadow (108,108,72 / 72,72,36), not the wall (180,180,144), not the red top (216,36,0).
- Fit: body = rings every 2 units with own centre + radius (left / right edge fit, never outside), wings = drawn wing pixels in a plane parallel to the
  niche back wall (x = 371). Projection IoU 0.998 (1204 px, 0 missed, 3 outside). Scripts `~/lktest/angel3/body2.py`, `build.py`, `objcheck.py`.
- State: LIGHT (v5, 2026-11-10). Near-final try with relief from the drawing's shading (`~/lktest/angel3/fine.py`, clay previews
  `~/lktest/angel3/clay_all.png`) = NOT good enough (lumpy, flat wings). TODO near-final: model from parts (head + hair + face, torso, two arms holding
  the swaddled child, bell robe with spiral folds, wings attached at the shoulder blades, cupped, feather rows), keep the silhouette exact.
- Open: 1 reddish pixel right of the robe foot in the lit picture (613).

## Chapel angel statue  (`furniture.ANGEL`, `angel(cx, cy, floor)`; ops by `angels()`)
- Game: chapels, tileset 8, rooms 597 607 736, cell (27, 24) = top block $2EB on the blocked 1-step platform $2EB / $2EC (cells 26..28 x 24), floor 16.
- Reference: room 597, window U0 1184 V0 304 (96 x 112). NOT the church drawing (17 % equal pixels).
- Fit: old method (body lathe with a don't-care wing zone + wing pixel rows in a plate, BACK 6), IoU 0.921, probably includes the painted shadow.
- State: LIGHT, OUTDATED. TODO: redo like the church angel (colour mask, ring stack, wings parallel to the wall behind), then near-final.
- Note: chapels cannot be reached with LANDSTALKER_WARP from the test save (black picture) - check in play.

## Church altar  (`furniture.ALTAR`, `plated_box(cx, cy, floor, ALTAR)`; ops by `altars()`)
- Game: tileset 3, rooms 613 614 699 700 721, cells (26, 27..28) = $181 over $185, walkable 1 step above the dais floor 16.
- Reference: room 613, window around U 1112 V 352 (`~/lktest/pew/a613`). Box body + top plate (overhang +x 2, +y 3, thickness 3) + KNEE NICHE at the +y end
  (end face set back 4 from 4 above the floor up to the plate, read from the pixels `~/lktest/pult/grid_a.png`). IoU 0.969.
- State: LIGHT. TODO near-final: gold trim lines along the plate and the body edges (drawn), the niche's inner edges.

## Chapel lectern  (`furniture.LECTERN`, `plated_box(..., LECTERN)`; ops by `lecterns()`)
- Game: tileset 8, rooms 597 607 736, cell (27, 26) = $2EF, walkable 1 step.
- Reference: room 597, window U0 1152 V0 368 (96 x 88). Body + sloped top plate (0.15 per unit towards +y, thickness 5.5, overhang +x 2, +y 1) + knee niche
  at the -y end (set back 4, from 4 up). IoU 0.943 (`~/lktest/pult/grid_p.png`).
- State: LIGHT. TODO near-final: book-rest lip at the low edge of the plate, carved panel lines.

## Barrel  (`furniture.BARREL`, lathe; ops by `round_found(.., "barrel")`)
- Game: cellars / storerooms, tileset 15: 23 barrels in rooms 65 66 68 69 71 72 78 79; found by a PICTURE MATCH against the reference (>= 50 % of the
  silhouette pixels identical; barrels drawn against a wall have other top blocks, e.g. 71 (14, 15) $062).
- Reference: room 71 cell (21, 15), floor 1 step (16); axis 2 units in front of the cell centre, 19 high, flat top. IoU 0.986 (`~/lktest/barrel/fitq.py`).
- State: NEAR-FINAL geometry (2026-11-10, `furniture.barrel_mesh()`, `BARREL_HOOPS`): hoops at z 1..3.5 / 9..11.5 / 15.5..17.5 measured from the hoop-grey
  pixels (72,72,72 / 36,36,36) per model height (`~/lktest/barrel/hoops.py`), wood 0.35 below the hoops, 16 staves with V grooves, chimes at top / bottom,
  top metal rim, lid recessed 1.5 with 4 planks along the screen axis. Projection IoU 0.980 (688 px, 2 outside, 12 missed at the rim back edge / foot),
  `~/lktest/barrel/objcheck.py`. Clay preview `~/.landstalker_remake/assets/barrel/clay_all.png`. User OK open. Material later (dark wood, grey iron).

## Clay jar  (`furniture.JAR`, lathe; ops by `round_found(.., "jar")`)
- Game: tileset 8 (chapels + wooden houses): 39 jars in 480 526 593 594 595 597 598 599 604 606 607 608 727 728 730 731 732 734 736 741 743 744 745 (picture match).
- Reference: room 597 cell (30, 25), floor 0; axis 3 units in front, 23 high, belly r 8.5, neck 4.7, lip 5.7. IoU 0.986 (`~/lktest/jar/fitc.py`).
- State: LIGHT. TODO near-final: OPEN mouth (hollow neck), rolled lip, painted band as a slight groove?

## Vase pair by the hearth  (`furniture.VASE`, lathe; ops by `vase_pairs()`)
- Game: Mercator houses, tileset 2, rooms 670 671 694: $157 (back) over $061 (front), same walkable height, wall west; floor h - 1.
- Reference: room 670 cells (18, 24) / (18, 25); axis 4 units in front, 23 high. IoU 0.965 (`~/lktest/vase/fit2.py`). Not placed: 685 / 686 (on a shelf
  in void cells, needs the shelf as a carrier like the church niche), 717 / 718 (other arrangement).
- State: LIGHT. TODO near-final: open mouth, lip; recheck the fit with the colour mask (painted shadow?).

## Brazier stand  (`furniture.BRAZIER_FOOT / BRAZIER_HEAD`, `brazier_prof(steps)`; ops by `brazier_stands()`)
- Game: castle, tileset 1, flame $098AAA (Tileset02Anim01); top blocks $027 / $041 / $043; 36 stands in 51..62, 86, 87. Short (2 steps) and tall (4 steps):
  same foot and head, stem 4 vs 28. Not placed: 55..58 (29, 24) / (42, 24) (in void cells, needs a carrier), 680 / 707 (wall candle, other object).
- Reference: room 51 (27, 44) short (IoU 0.942), room 59 (29, 28) tall (0.955); axis 1 unit in front of the cell centre. The flame light sits on the axis
  5 above the bowl and ignores its own stand (data `carrier`, LK_GLCARRIER v1).
- State: LIGHT. TODO near-final: the prongs around the bowl, hollow bowl, knobs on the stem (drawn).

## Tables, benches, side tables, castle tables, L bench  (`furniture.MERCATOR_TABLE / CASTLE_TABLE`, `table()`, `top_on_legs()`, `l_bench()`; ops by `tables()`)
- Game: tileset 2 Mercator tables / benches / side tables (top blocks $030 $04A $04C $04D $06E $06A $0A3 $18A $312..$314) and tileset 1 castle tables
  ($114 back corner ...): 40 pieces in 32 rooms (HANDOFF 0a360); L bench 623 624 701 702 (0a361); side tables 691 692 713 714.
- Reference: Mercator table room 670 (HANDOFF 0a360 / 0a362: top thickness 3 = the drawn edge band), castle table room 96 (3 x 3 cells, gold rim, thickness 8),
  L bench room 623 (legs measured on the olive leg colours, `~/lktest/bench/legs.py`).
- The painted shadows under them are replaced at runtime (LK_GLUNPAINT, `UNPAINT_TILES`).
- State: LIGHT (boxes + legs). TODO near-final: leg shapes as drawn (turned / curved), plank lines, rims.
