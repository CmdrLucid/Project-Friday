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
- NEAR-FINAL SCULPT in progress (2026-11-10, `remake/recipes/church_angel_sculpt/`, README there): body = metaballs (robe on the measured rings with
  smooth spiral folds, torso, arms, child, head, hair, face) kept inside a smoothed drawing outline (post.py); wings = own clean mesh (wing.py).
  Versions / user decisions (previews `~/.landstalker_remake/assets/church_angel/sculpt_v1..v5.png`):
  v1 first blockout; v2 'Kind' (swaddled child, the drawn chest ring = the cloth around its face), thin neck, 'Haare wie im Sprite';
  v3 child held DIAGONALLY ('schraeg gehalten'), robe folds, face; v4 'orientier dich am Sprite' (read the head on the 1 px grid), right wing fixed
  ('schlechter': cliff at the root, sharp row steps, rectangular notch from cutting the join at a row, floating wing -> fade-in, smooth steps, stem
  behind the body to the shoulder); v5: WINGS MIRRORED in the wall plane at the same height (user 'gespiegelt und parallel zur Wand, links gleich
  wie rechts', option 1 of `wings_mirror.png`: mirror axis = the body axis y 444.5; the artist drew the left wing ~6 lower, so the game picture is
  no longer exact: IoU 0.848, 42 px outside = REMAKE MODEL ONLY, the light keeps CHURCH_ANGEL4), depth along the wall normal, feathers on both faces;
  HAIR not a bob ('die gehen im Sprite hinter die Statue'): from the parting over the crown, beside the face and back down behind the head / shoulders.
  v6..v7 metaball faces ('menschlich', 'weiblicher'): not good enough -> v8 OWN POLYGON HEAD (user choice over an AI generator): `head.py` = a grid
  shaped by female head profiles (front / back / width per height, Catmull-Rom; face section a superellipse 2.6 at the eyes, 2.0 at the mouth) +
  sculpt brushes (almond eyes with lids, sockets, high cheekbones, small straight nose, cupid's bow lips, round chin) + a HAIR SHELL that follows
  the skull (hairline on a smooth curve, volume at the sides, fine strands); the metaball hair is gone except the panel down the back. v9 chin
  rounder ('Kinn ist noch komisch'), v10 no 'Pausbacken' (narrower beside the mouth, cheekbones higher). User on v10: 'etwas besser, aber da
  muessen wir spaeter nochmal ran'. Previews `sculpt_v6_face .. sculpt_v10_cheeks.png`. Next: the face again, then the child's face and the arms.
- Open: 1 reddish pixel right of the robe foot in the lit picture (613).

## Chapel angel statue  (`furniture.ANGEL`, `angel(cx, cy, floor)`; ops by `angels()`)
- Game: chapels, tileset 8, rooms 597 607 736, cell (27, 24) = top block $2EB on the blocked 1-step platform $2EB / $2EC (cells 26..28 x 24), floor 16.
- Reference: room 597, window U0 1184 V0 304 (96 x 112). NOT the church drawing (17 % equal pixels).
- Fit: old method (body lathe with a don't-care wing zone + wing pixel rows in a plate, BACK 6), IoU 0.921, probably includes the painted shadow.
- State: LIGHT, OUTDATED. TODO: redo like the church angel (colour mask, ring stack, wings parallel to the wall behind), then near-final.
- Note: chapels cannot be reached with LANDSTALKER_WARP from the test save (black picture) - check in play.

## Church altar  (`furniture.ALTAR`, near-final `plated_mesh(cx, cy, floor, ALTAR)`; ops by `altars()`)
- Game: tileset 3, rooms 613 614 699 700 721, cells (26, 27..28) = $181 over $185, walkable 1 step above the dais floor 16.
- Reference: room 613, window U0 1112 V0 352 (`~/lktest/pew/a613`). Drawing: dark wooden slab (edge = a lighter band between two black lines) on a grey-olive
  stone body; NO gold trim on the altar itself (the gold belongs to the dais step).
- Shape: body + slab (overhang +x 2, +y 3, thickness 3). The KNEE COVE is a rounded hollow along the WHOLE -x side (the back, hidden in the game view; user
  2026-11-10: 'eine Rundung ... entlang der ganzen Laenge'); the drawing shows it only as the notch at the left silhouette corner, where the back side is
  seen end on. Earlier versions (step niche at the +y end) were wrong.
- State: NEAR-FINAL geometry v2 (2026-11-10): body = the cove profile extruded along y, ends rounded 0.75, flat sharp foot; cove depth D 5 at the foot top
  (4 above the floor), superellipse p 1.5 up to the slab, foot edge rounded 0.75 (`PLATED_FINE["cove"]["x-"]`, fitted by projection,
  `~/lktest/pult2/fitcove.py`); slab = rounded box r 1.25, grown 0.4 on every side + top so its silhouette keeps the drawn outline. Projection IoU 0.888
  (old box 0.887, same window; the window includes some plane B outline pixels, so only relative), `~/lktest/pult2/chk.py`. Clay preview
  `~/.landstalker_remake/assets/altar/clay_all.png` (original | game view + 60 / 120 / 180). User saw v2 2026-11-10 (no change asked). Material later.

## Chapel lectern  (`furniture.LECTERN`, near-final `plated_mesh(..., LECTERN)`; ops by `lecterns()`)
- Game: tileset 8, rooms 597 607 736, cell (27, 26) = $2EF, walkable 1 step.
- Reference: room 597, window U0 1152 V0 368 (96 x 88). Drawing: thick sloped wooden slab (its side faces = the lighter dither band) on a wooden body.
- Shape: body + slab sloped 0.15 per unit rising towards +y, thickness 5.5, overhang +x 2, +y 1; rounded KNEE COVE along the whole -y side (seen as the
  notch at the right silhouette corner).
- State: NEAR-FINAL geometry v2 (2026-11-10): as the altar, cove D 3, foot 3, p 2 (`PLATED_FINE["cove"]["y-"]`), the slab sheared to the slope.
  IoU 0.957 (old box 0.947). Book ledge tried in v1 and REMOVED (user: 'buchleiste weg'); no carved panels (not in the drawing).
  Clay preview `~/.landstalker_remake/assets/lectern/clay_all.png`, both: `.../lectern/pult_altar.png`.

## Barrel  (`furniture.BARREL`, lathe; ops by `round_found(.., "barrel")`)
- Game: cellars / storerooms, tileset 15: 23 barrels in rooms 65 66 68 69 71 72 78 79; found by a PICTURE MATCH against the reference (>= 50 % of the
  silhouette pixels identical; barrels drawn against a wall have other top blocks, e.g. 71 (14, 15) $062).
- Reference: room 71 cell (21, 15), floor 1 step (16); axis 2 units in front of the cell centre, 19 high, flat top. IoU 0.986 (`~/lktest/barrel/fitq.py`).
- State: NEAR-FINAL geometry (2026-11-10, `furniture.barrel_mesh()`, `BARREL_HOOPS`): hoops at z 1..3.5 / 9..11.5 / 15.5..17.5 measured from the hoop-grey
  pixels (72,72,72 / 36,36,36) per model height (`~/lktest/barrel/hoops.py`), wood 0.35 below the hoops, 16 staves with V grooves, chimes at top / bottom,
  top metal rim, lid recessed 1.5 with 4 planks along the screen axis. Projection IoU 0.980 (688 px, 2 outside, 12 missed at the rim back edge / foot),
  `~/lktest/barrel/objcheck.py`. Clay preview `~/.landstalker_remake/assets/barrel/clay_all.png`. USER OK 2026-11-10 ('Das Fass passt'). Material later (dark wood, grey iron).

## Clay jar  (`furniture.JAR`, lathe; ops by `round_found(.., "jar")`)
- Game: tileset 8 (chapels + wooden houses): 39 jars in 480 526 593 594 595 597 598 599 604 606 607 608 727 728 730 731 732 734 736 741 743 744 745 (picture match).
- Reference: room 597 cell (30, 25), floor 0; axis 3 units in front, 23 high, belly r 8.5, neck 4.7, lip 5.7. IoU 0.986 (`~/lktest/jar/fitc.py`).
- State: NEAR-FINAL geometry (2026-11-10, `furniture.jar_mesh()` via `revolve()`): open mouth (the drawing is black inside, ~10 px -> inner radius 3.6),
  rolled lip (half round over the top), hollow neck 6 deep, foot bevelled so its front edge stays above picture row 71, outline radii smoothed once (3-tap)
  to remove the drawing's pixel-step ripples. Projection IoU 0.948 (578 px, 4 outside; unsmoothed 0.962 but rippled), `~/lktest/jar/objcheck.py`.
  Red shoulder band and grey lower body = paint (material later). Clay preview `~/.landstalker_remake/assets/jar/clay_all.png`. USER OK 2026-11-10 ('Ja, passt').

## Vase pair by the hearth  (`furniture.VASE`, lathe; ops by `vase_pairs()`)
- Game: Mercator houses, tileset 2, rooms 670 671 694: $157 (back) over $061 (front), same walkable height, wall west; floor h - 1.
- Reference: room 670 cells (18, 24) / (18, 25); axis 4 units in front, 23 high. IoU 0.965 (`~/lktest/vase/fit2.py`). Not placed: 685 / 686 (on a shelf
  in void cells, needs the shelf as a carrier like the church niche), 717 / 718 (other arrangement).
- State: NEAR-FINAL geometry (2026-11-10, `furniture.vase_mesh()` = `vessel_mesh()` with `VASE_PROF2`): outline REFITTED with the vase's own pixels
  (the black painted floor shadow under the foot left out) on the left half of the front vase, knots every 2 units, never outside (`~/lktest/vase2/fitv.py`:
  foot 3.5, belly 8.5 at z 8..10, neck 5.25, lip 5.5, top 22.5), Catmull-Rom through the knots (no kinks); open mouth (dark inside, ri 4.2), rolled lip,
  hollow neck 7. Both vases projected: IoU 0.971 (956 px, 8 outside at the back vase's lower right edge, 20 missed at the lip back edges), `~/lktest/vase2/chk.py`.
  In-game 670 (`~/lktest/vase2/zoom.png`): the bright lip streak between the two vases (HANDOFF 0a364..0a367) is GONE. White glaze pattern = paint.
  Clay preview `~/.landstalker_remake/assets/vase/clay_all.png`. USER OK 2026-11-10 ('Passt ja').

## Brazier stand  (`furniture.BRAZIER_FOOT / BRAZIER_HEAD`, `brazier_prof(steps)`; ops by `brazier_stands()`)
- Game: castle, tileset 1, flame $098AAA (Tileset02Anim01); top blocks $027 / $041 / $043; 36 stands in 51..62, 86, 87. Short (2 steps) and tall (4 steps):
  same foot and head, stem 4 vs 28. Not placed: 55..58 (29, 24) / (42, 24) (in void cells, needs a carrier), 680 / 707 (wall candle, other object).
- Reference: room 51 (27, 44) short (IoU 0.942), room 59 (29, 28) tall (0.955); axis 1 unit in front of the cell centre. The flame light sits on the axis
  5 above the bowl and ignores its own stand (data `carrier`, LK_GLCARRIER v1).
- State: NEAR-FINAL geometry v3 (2026-11-10, `furniture.brazier_mesh(ax, ay, floor, steps)`, `BRAZIER_PRONGS`). History: v1 prongs wrong; v2 6 petals
  ('die Krone stimmt noch gar nicht', then 'es sind nur 4'); unequal claws fitted the picture best (0.956) but looked wrong from other sides -> user chose
  '1' = FOUR EQUAL CLAWS like a real crown; v4: 'nicht so abrupt abgeknickt - die Zacke ist fast gerade, nur der Haken am Ende macht die Kurve'. Now: bowl rim z 32 of the short stand (18 above the stem top, the dark ellipse around the flame's foot), r 6.0,
  open 2.5 deep; four identical claws on the diagonals (45 / 135 / 225 / 315 deg from the screen-right axis), rooted at the rim (r 5.0): a nearly
  STRAIGHT shaft L 7 leaning out 20 deg (v5, user: 'flacherer Winkel', then '2' = rooted at the rim, not deep in the bowl), only the last 40 % bends out
  on a smooth arc by 45 deg (the hook), radius 1.3 until the hook then a point (taper 3), parallel-transport tube. v6 ('die Verbindung von Klaue zu Schale
  muss sauberer werden'): each claw GROWS out of the bowl's outer wall (4 lead-in points hugging the wall half sunk in, from 2.6 below the rim). The front pair reads as the tall prongs
  beside the flame, the back pair as the side claws. Projection IoU 0.920 short (room 51) / 0.937 tall (59) (`~/lktest/braz/chk.py`, grids `gridc7.py` .. `gridc11.py`).
  In-game 59 light unchanged (152). Previews `~/.landstalker_remake/assets/brazier/` (crown_both.png sprite vs model + 4 views, crown_all.png, clay_all.png,
  zoom_crown_game.png). USER OK 2026-11-10 ('yes passt'). Material later (grey iron foot / bowl / claws, gold stem and knob).

## Mercator table  (`furniture.MERCATOR_FINE`, near-final `mercator_table_mesh(x0, y0, x1, y1, floor, top, thick)`; ops by `tables()` for pieces with $030 at the back corner)
- Game: tileset 2, 2 x 2 .. 4 x 3 cells, walkable 1 step: 477 620 621 622 670 671 677 687 688 691 692 694 698 713 714 717 718 722 723 724 725 (21 pieces).
- Reference: room 670 cells 22..24 x 22..23 (x 352..400, y 352..384), floor 0, top 16; window U0 1150 V0 300 96 x 96 (`~/lktest/table2/w670`).
  Drawing: top with ROUNDED corners, light rim band + black line + dark field (= paint, NOT a recess: user 2026-11-10 'eine grade Platte'), side ~3, four
  ROUND legs ~4 wide (dark / black line / light / dark shading), rounded feet. Layer A holds no painted shadow here.
- State: NEAR-FINAL geometry v3 (2026-11-10): flat slab swept along a rounded rectangle (corner radius 2, TOP edges rounded 0.75, the BOTTOM outer edge
  SHARP, thickness 3 kept from the light fix 0a362), plan = the cell box grown 1 on the back sides (the drawn outline) and EXACTLY the cell box at the
  front (v2 grown 1 + rounded bottom gave bright carpet half rows under the edge in play, user; MODELING_LESSONS 4); legs radius 2, centres 1.625 in from the back sides (x0 / y0) and 3.125 from the front
  sides (670 feet: spacing 43.25 x 27.25; the back / front split read from the feet's picture rows). Projection IoU 0.983 in 670 (2 px outside, 32 missed = every 2nd pixel of the black outline stair under the front edges, as the old
  boxes; v2 0.999 but the strip; old boxes 0.929), all 11 sizes / rooms checked 0.896 .. 0.999 with 2 px outside each (misses = things on / beside the table),
  `~/lktest/table2/tablechk.py` / `allchk.py`. Clay preview `~/.landstalker_remake/assets/table/clay_all.png`. USER OK 2026-11-10 ('yes').
  v1 had a raised rim + recessed field: user 'Mittelfeld nicht vertieft'. Material later (orange-brown wood, darker top paint, olive legs).

## Mercator bench, side table, L bench  (`mercator_table_mesh` for the bench $0A3 1 x 3 and the side table $18A 1 x 1; `l_bench_mesh` for the L bench)
- Game: bench 623 624 701 702 (32, 30..32); side table 691 692 713 714 (13, 15); L bench 623 624 701 702 (long arm 25 x 34..37, short arm west to 24 at 34).
- Reference: bench room 623 (`~/lktest/bench2/w623`), side table 691 (`~/lktest/bench2/w691`), L bench 623 (`~/lktest/lbench/w623`). Drawn like the table
  (rounded corners, painted rim, round legs): the table shape with the SAME numbers fits the bench and the side table exactly (no drawn pixel missed in
  their own area). The L bench's short arm is partly drawn on plane B: its mask = the bench colours on the full picture (`~/lktest/lbench/fitarm.py`).
- State: NEAR-FINAL v1 (2026-11-10, USER OK 'passt'): L bench = flat slab swept along the L outline (`sweep_poly`: convex corners and the inner corner
  rounded 2, back sides +1, fronts on the cells, bottom edge sharp), five round legs (none at the inner corner, as drawn); short arm 16 deep (fit:
  16 / 18 equal). IoU 0.891 (old boxes 0.875; misses = the black outline line under the front edge, as the old boxes). Clay preview
  `~/.landstalker_remake/assets/benches/clay_all.png`. In-game 623 / 691 before / after: no strips, near identical.

## Castle table  (`furniture.CASTLE_FINE`, near-final `castle_table_mesh(x0, y0, x1, y1, floor, top, thick)`; ops by `tables()` for tileset 1)
- Game: tileset 1, top block $114 at the back corner: 3 x 3 in 96 97 103 708 710, 3 x 2 in 88 89; walkable 1 step.
- Reference: room 96 cells 20..22 x 21..23 (x 320..368, y 336..384), top 16; window U0 1110 V0 296 112 x 100 (`~/lktest/ctable/w96`). Drawing: nearly
  POINTED corners, thick top whose side shows gold / olive / dark bands (= paint), dark red field (paint), short CURVED legs (6 px wide at the top, a
  narrow ankle 4, the foot 6 turned out). Layer A also holds the painted shadow under the table: the mask drops carpet colours and shadow red next to
  carpet (`~/lktest/ctable/chk.py`).
- State: NEAR-FINAL v1 (2026-11-10, USER OK 'passt'): flat slab thickness 8 (from 0a362), corner radius 1.5 (0.75 left a column outside at the side
  corners), top edges rounded 0.75, bottom edge sharp, back +1, fronts on the cells; legs = `ring_stack` (rings with own centres: top r 2.7, ankle 1.7,
  foot 2.6 shifted 1.3 out towards the corner), back / front legs 2.5 in from the corner, the two side legs 4 in along x / 1 along y (mirrored; fitted on
  the drawn feet). IoU 0.915 (old boxes 0.883; 24 px outside at the feet; most misses = the dais step below). Clay preview
  `~/.landstalker_remake/assets/castle_table/clay_all.png`. Material later (gold rim + bands, dark red inlay, olive legs).
- All pieces on legs: the painted shadows under them are replaced at runtime (LK_GLUNPAINT, `furniture_ops.UNPAINT_TILES`, tileset 2 only).
