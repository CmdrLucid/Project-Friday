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
- Fit / check scripts of the first versions are on the Deck in `~/Project-Friday-Test/lktest/<dir>/` (not in git; the numbers they produced are in furniture.py).
- Silhouette rule: the object's OWN pixels (by colour; layer A also holds PAINTED SHADOWS of objects), no part outside the drawing; check by projecting
  the real triangles (e.g. `~/Project-Friday-Test/lktest/angel3/objcheck.py OBJ`). Detail may move along the view ray (1, 1, 1): the game picture stays identical.

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
  niche back wall (x = 371). Projection IoU 0.998 (1204 px, 0 missed, 3 outside). Scripts `~/Project-Friday-Test/lktest/angel3/body2.py`, `build.py`, `objcheck.py`.
- State: LIGHT (v5, 2026-11-10). Near-final try with relief from the drawing's shading (`~/Project-Friday-Test/lktest/angel3/fine.py`, clay previews
  `~/Project-Friday-Test/lktest/angel3/clay_all.png`) = NOT good enough (lumpy, flat wings). TODO near-final: model from parts (head + hair + face, torso, two arms holding
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

- v11 (2026-11-11, `sculpt_v11_mouth.png`, `sculpt_v11_all.png`): face = no shelf beside the mouth (user: 'viel besser'); long parted hair swept back,
  the dress as a polygon lathe with drapery folds (`robe.py`), feathers in three shingle rows from the shoulder. Waiting for the user's look; open: child's face, arms.

- v12 (2026-11-11, `sculpt_v12_scroll.png`): compared 1 : 1 with the sprite in the exact game projection (`gv.sh`): head to the drawn size, NO child but
  an upright SCROLL in both hands (user), arms as the drawn ring, bolder folds / feathers. Open: user's look; mirrored wings vs the drawn ones (light).

- v13 (2026-11-11, `sculpt_v13_facing.png`): the figure faces OUT OF THE WALL (+x), wings on its back as drawn (each its own pixels, completed
  behind the body), folded arms with the scroll lying in them; projection IoU 0.898 (23 px outside, 102 missed). Waiting for the user's look.

- v14 .. v17 (2026-11-11, `sculpt_v17_mirror.png`): wings complete across the back, feathers from the top inner corner in three rows, folded arms with
  the scroll between arms and chest, comparison render lit from the front right; v17 = the right wing is the MIRRORED left one (user), IoU 0.792
  (v16 with each wing as drawn: 0.914). Open: user's look; which variant the light gets.

- v18 (2026-11-11, `sculpt_v18_scroll.png`): the scroll lies in the folded arms, a hand over each end. User's decision: TWO variants = remake model with
  mirrored wings (`params.json`), light model with the wings as drawn (`params_light.json`, IoU 0.914; not built into the light yet).

- LIGHT since 2026-11-11: the sculpt's light variant (`remake/recipes/church_angel_sculpt/light.obj` from `export_light.sh`, written by `furniture_ops.py`;
  `--angel-v5` = CHURCH_ANGEL4 again). Remake model v18 FINISHED (user 'ja'): `~/.landstalker_remake/assets/church_angel/sculpt_v18_remake.obj`.

## Chapel angel statue  (`furniture.ANGEL`, `angel(cx, cy, floor)`; ops by `angels()`)
- Game: chapels, tileset 8, rooms 597 607 736, cell (27, 24) = top block $2EB on the blocked 1-step platform $2EB / $2EC (cells 26..28 x 24), floor 16.
- Reference: room 597, window U0 1184 V0 304 (96 x 112). NOT the church drawing (17 % equal pixels).
- Fit: old method (body lathe with a don't-care wing zone + wing pixel rows in a plate, BACK 6), IoU 0.921, probably includes the painted shadow.
- State: LIGHT since 2026-11-11 = the CHURCH angel's sculpt light variant mirrored at the diagonal (user: the same statue, 'nur unseren vorhandenen fuers
  Licht dort hinstellen'; `furniture_ops.chapel_angel_obj`: axis 5 / 4 in front of the cell centre, matched on the 597 picture; the right wing cut at the wall
  block x = 464). Body + raised wing fit the drawing in the overlay; built, NOT checkable by warp, not played. The old ANGEL lathe: `--angel-v5`.
- Note: chapels cannot be reached with LANDSTALKER_WARP from the test save (black picture) - check in play.

## Church altar  (`furniture.ALTAR`, near-final `plated_mesh(cx, cy, floor, ALTAR)`; ops by `altars()`)
- Game: tileset 3, rooms 613 614 699 700 721, cells (26, 27..28) = $181 over $185, walkable 1 step above the dais floor 16.
- Reference: room 613, window U0 1112 V0 352 (`~/Project-Friday-Test/lktest/pew/a613`). Drawing: dark wooden slab (edge = a lighter band between two black lines) on a grey-olive
  stone body; NO gold trim on the altar itself (the gold belongs to the dais step).
- Shape: body + slab (overhang +x 2, +y 3, thickness 3). The KNEE COVE is a rounded hollow along the WHOLE -x side (the back, hidden in the game view; user
  2026-11-10: 'eine Rundung ... entlang der ganzen Laenge'); the drawing shows it only as the notch at the left silhouette corner, where the back side is
  seen end on. Earlier versions (step niche at the +y end) were wrong.
- State: NEAR-FINAL geometry v2 (2026-11-10): body = the cove profile extruded along y, ends rounded 0.75, flat sharp foot; cove depth D 5 at the foot top
  (4 above the floor), superellipse p 1.5 up to the slab, foot edge rounded 0.75 (`PLATED_FINE["cove"]["x-"]`, fitted by projection,
  `~/Project-Friday-Test/lktest/pult2/fitcove.py`); slab = rounded box r 1.25, grown 0.4 on every side + top so its silhouette keeps the drawn outline. Projection IoU 0.888
  (old box 0.887, same window; the window includes some plane B outline pixels, so only relative), `~/Project-Friday-Test/lktest/pult2/chk.py`. Clay preview
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
- Reference: room 71 cell (21, 15), floor 1 step (16); axis 2 units in front of the cell centre, 19 high, flat top. IoU 0.986 (`~/Project-Friday-Test/lktest/barrel/fitq.py`).
- State: NEAR-FINAL geometry (2026-11-10, `furniture.barrel_mesh()`, `BARREL_HOOPS`): hoops at z 1..3.5 / 9..11.5 / 15.5..17.5 measured from the hoop-grey
  pixels (72,72,72 / 36,36,36) per model height (`~/Project-Friday-Test/lktest/barrel/hoops.py`), wood 0.35 below the hoops, 16 staves with V grooves, chimes at top / bottom,
  top metal rim, lid recessed 1.5 with 4 planks along the screen axis. Projection IoU 0.980 (688 px, 2 outside, 12 missed at the rim back edge / foot),
  `~/Project-Friday-Test/lktest/barrel/objcheck.py`. Clay preview `~/.landstalker_remake/assets/barrel/clay_all.png`. USER OK 2026-11-10 ('Das Fass passt'). Material later (dark wood, grey iron).

## Clay jar  (`furniture.JAR`, lathe; ops by `round_found(.., "jar")`)
- Game: tileset 8 (chapels + wooden houses): 39 jars in 480 526 593 594 595 597 598 599 604 606 607 608 727 728 730 731 732 734 736 741 743 744 745 (picture match).
- Reference: room 597 cell (30, 25), floor 0; axis 3 units in front, 23 high, belly r 8.5, neck 4.7, lip 5.7. IoU 0.986 (`~/Project-Friday-Test/lktest/jar/fitc.py`).
- State: NEAR-FINAL geometry (2026-11-10, `furniture.jar_mesh()` via `revolve()`): open mouth (the drawing is black inside, ~10 px -> inner radius 3.6),
  rolled lip (half round over the top), hollow neck 6 deep, foot bevelled so its front edge stays above picture row 71, outline radii smoothed once (3-tap)
  to remove the drawing's pixel-step ripples. Projection IoU 0.948 (578 px, 4 outside; unsmoothed 0.962 but rippled), `~/Project-Friday-Test/lktest/jar/objcheck.py`.
  Red shoulder band and grey lower body = paint (material later). Clay preview `~/.landstalker_remake/assets/jar/clay_all.png`. USER OK 2026-11-10 ('Ja, passt').

## Vase pair by the hearth  (`furniture.VASE`, lathe; ops by `vase_pairs()`)
- Game: Mercator houses, tileset 2, rooms 670 671 694: $157 (back) over $061 (front), same walkable height, wall west; floor h - 1.
- Reference: room 670 cells (18, 24) / (18, 25); axis 4 units in front, 23 high. IoU 0.965 (`~/Project-Friday-Test/lktest/vase/fit2.py`). Not placed: 685 / 686 (on a shelf
  in void cells, needs the shelf as a carrier like the church niche), 717 / 718 (other arrangement).
- State: NEAR-FINAL geometry (2026-11-10, `furniture.vase_mesh()` = `vessel_mesh()` with `VASE_PROF2`): outline REFITTED with the vase's own pixels
  (the black painted floor shadow under the foot left out) on the left half of the front vase, knots every 2 units, never outside (`~/Project-Friday-Test/lktest/vase2/fitv.py`:
  foot 3.5, belly 8.5 at z 8..10, neck 5.25, lip 5.5, top 22.5), Catmull-Rom through the knots (no kinks); open mouth (dark inside, ri 4.2), rolled lip,
  hollow neck 7. Both vases projected: IoU 0.971 (956 px, 8 outside at the back vase's lower right edge, 20 missed at the lip back edges), `~/Project-Friday-Test/lktest/vase2/chk.py`.
  In-game 670 (`~/Project-Friday-Test/lktest/vase2/zoom.png`): the bright lip streak between the two vases (HANDOFF 0a364..0a367) is GONE. White glaze pattern = paint.
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
  beside the flame, the back pair as the side claws. Projection IoU 0.920 short (room 51) / 0.937 tall (59) (`~/Project-Friday-Test/lktest/braz/chk.py`, grids `gridc7.py` .. `gridc11.py`).
  In-game 59 light unchanged (152). Previews `~/.landstalker_remake/assets/brazier/` (crown_both.png sprite vs model + 4 views, crown_all.png, clay_all.png,
  zoom_crown_game.png). USER OK 2026-11-10 ('yes passt'). Material later (grey iron foot / bowl / claws, gold stem and knob).

## Mercator table  (`furniture.MERCATOR_FINE`, near-final `mercator_table_mesh(x0, y0, x1, y1, floor, top, thick)`; ops by `tables()` for pieces with $030 at the back corner)
- Game: tileset 2, 2 x 2 .. 4 x 3 cells, walkable 1 step: 477 620 621 622 670 671 677 687 688 691 692 694 698 713 714 717 718 722 723 724 725 (21 pieces).
- Reference: room 670 cells 22..24 x 22..23 (x 352..400, y 352..384), floor 0, top 16; window U0 1150 V0 300 96 x 96 (`~/Project-Friday-Test/lktest/table2/w670`).
  Drawing: top with ROUNDED corners, light rim band + black line + dark field (= paint, NOT a recess: user 2026-11-10 'eine grade Platte'), side ~3, four
  ROUND legs ~4 wide (dark / black line / light / dark shading), rounded feet. Layer A holds no painted shadow here.
- State: NEAR-FINAL geometry v3 (2026-11-10): flat slab swept along a rounded rectangle (corner radius 2, TOP edges rounded 0.75, the BOTTOM outer edge
  SHARP, thickness 3 kept from the light fix 0a362), plan = the cell box grown 1 on the back sides (the drawn outline) and EXACTLY the cell box at the
  front (v2 grown 1 + rounded bottom gave bright carpet half rows under the edge in play, user; MODELING_LESSONS 4); legs radius 2, centres 1.625 in from the back sides (x0 / y0) and 3.125 from the front
  sides (670 feet: spacing 43.25 x 27.25; the back / front split read from the feet's picture rows). Projection IoU 0.983 in 670 (2 px outside, 32 missed = every 2nd pixel of the black outline stair under the front edges, as the old
  boxes; v2 0.999 but the strip; old boxes 0.929), all 11 sizes / rooms checked 0.896 .. 0.999 with 2 px outside each (misses = things on / beside the table),
  `~/Project-Friday-Test/lktest/table2/tablechk.py` / `allchk.py`. Clay preview `~/.landstalker_remake/assets/table/clay_all.png`. USER OK 2026-11-10 ('yes').
  v1 had a raised rim + recessed field: user 'Mittelfeld nicht vertieft'. Material later (orange-brown wood, darker top paint, olive legs).

## Mercator bench, side table, L bench  (`mercator_table_mesh` for the bench $0A3 1 x 3 and the side table $18A 1 x 1; `l_bench_mesh` for the L bench)
- Game: bench 623 624 701 702 (32, 30..32); side table 691 692 713 714 (13, 15); L bench 623 624 701 702 (long arm 25 x 34..37, short arm west to 24 at 34).
- Reference: bench room 623 (`~/Project-Friday-Test/lktest/bench2/w623`), side table 691 (`~/Project-Friday-Test/lktest/bench2/w691`), L bench 623 (`~/Project-Friday-Test/lktest/lbench/w623`). Drawn like the table
  (rounded corners, painted rim, round legs): the table shape with the SAME numbers fits the bench and the side table exactly (no drawn pixel missed in
  their own area). The L bench's short arm is partly drawn on plane B: its mask = the bench colours on the full picture (`~/Project-Friday-Test/lktest/lbench/fitarm.py`).
- State: NEAR-FINAL v1 (2026-11-10, USER OK 'passt'): L bench = flat slab swept along the L outline (`sweep_poly`: convex corners and the inner corner
  rounded 2, back sides +1, fronts on the cells, bottom edge sharp), five round legs (none at the inner corner, as drawn); short arm 16 deep (fit:
  16 / 18 equal). IoU 0.891 (old boxes 0.875; misses = the black outline line under the front edge, as the old boxes). Clay preview
  `~/.landstalker_remake/assets/benches/clay_all.png`. In-game 623 / 691 before / after: no strips, near identical.

## Castle table  (`furniture.CASTLE_FINE`, near-final `castle_table_mesh(x0, y0, x1, y1, floor, top, thick)`; ops by `tables()` for tileset 1)
- Game: tileset 1, top block $114 at the back corner: 3 x 3 in 96 97 103 708 710, 3 x 2 in 88 89; walkable 1 step.
- Reference: room 96 cells 20..22 x 21..23 (x 320..368, y 336..384), top 16; window U0 1110 V0 296 112 x 100 (`~/Project-Friday-Test/lktest/ctable/w96`). Drawing: nearly
  POINTED corners, thick top whose side shows gold / olive / dark bands (= paint), dark red field (paint), short CURVED legs (6 px wide at the top, a
  narrow ankle 4, the foot 6 turned out). Layer A also holds the painted shadow under the table: the mask drops carpet colours and shadow red next to
  carpet (`~/Project-Friday-Test/lktest/ctable/chk.py`).
- State: NEAR-FINAL v1 (2026-11-10, USER OK 'passt'): flat slab thickness 8 (from 0a362), corner radius 1.5 (0.75 left a column outside at the side
  corners), top edges rounded 0.75, bottom edge sharp, back +1, fronts on the cells; legs = `ring_stack` (rings with own centres: top r 2.7, ankle 1.7,
  foot 2.6 shifted 1.3 out towards the corner), back / front legs 2.5 in from the corner, the two side legs 4 in along x / 1 along y (mirrored; fitted on
  the drawn feet). IoU 0.915 (old boxes 0.883; 24 px outside at the feet; most misses = the dais step below). Clay preview
  `~/.landstalker_remake/assets/castle_table/clay_all.png`. Material later (gold rim + bands, dark red inlay, olive legs).
- All pieces on legs: the painted shadows under them are replaced at runtime (LK_GLUNPAINT, `furniture_ops.UNPAINT_TILES`, tileset 2 only).

## Armour knight  (`remake/recipes/knight/knight.py`; not in the light yet)
- Game: Mercator houses, tileset 2, top blocks $19C / $2D7: rooms 678 679 (cells 30 / 33, 26), 695 696 697 719 720 (34, 23 and 23, 23); all one drawing.
- Reference: room 678 cell (30, 26), window U0 1216 V0 392 (64 x 80); own pixels by colour from layer A (painted shadow under the feet left out).
- State: LIGHT + remake model v7 FINISHED for now (user 2026-11-11 'dann done'): plate details, a helm with a visor (eye slit in the front only), two
  barbed feathers from one holder; IoU 0.823, ~16000 faces; 14 knights in 7 rooms through `furniture_ops.knights()`; checked headless in 695, not played.
- The castle's dark armour on a stand: next section.

## Armour on a stand  (`remake/recipes/knight/stand.py`)
- Game: castle, tileset 15, top block $0B5 (blocked cells): rooms 63 64 (19, 25 / 28 / 31), 83 84 (15, 21 / 24 / 27), 93 (30, 27).
- Reference: room 63 cell (19, 28) on floor 32, window U0 1008 V0 280 (72 x 110), layer A component.
- State: TWO VARIANTS (user 2026-11-11): REMAKE model v3 = symmetric real 3D (shoulders lowered, fauld + hip tassets, stand visible in the game view;
  IoU 0.780); LIGHT = `"variant": "light"`, as drawn (IoU 0.905), 12 stands in 63 64 83 84 through `furniture_ops.armour_stands()` (93 left out);
  checked headless in 63 / 83, not played.


## Bed  (`remake/recipes/bed/bed.py`; ops by `furniture_ops.beds()`)
- Tileset 2 houses, 51 beds in 30 rooms (3 x 2 head west / 2 x 3 head north, mirrored). Board on four legs, ONE pillow, blanket hanging to z 3.5.
- Two variants: remake = level (`tilt` 0); light = as drawn, top tilted up 3 towards the back wall (IoU 0.948). Details: `remake/recipes/bed/README.md`.

## Grand piano  (`remake/recipes/piano/model3d.py` on the measured plan of `piano.py`; room 85 only)
- Reference: room 85 MERCATOR_CASTLE_BANQUET_ROOM, cells x 13..16, y 21..25 (`rom_picture.py ROM 85 970 180 170 170`).
- Plan MEASURED: the front S curve from the drawn case bottom edge (each bottom pixel at z 7 -> one floor point), case z 7..20, legs at the drawn feet.
- Near-final geometry (user 2026-11-12 'ja, passt'): open case (plinth chamfer, rim lip, soundboard 3 below the rim), iron plate + 3 struts, key bed /
  keys / fallboard / cheeks, three turned legs with brass feet, lid hinged on the spine with rounded edge (inset 0.1 to stay inside the drawn lid) +
  prop stick. Same model in the light (no separate variant: the drawing is consistent). Silhouette IoU 0.912, 44 px outside the drawing. No music desk (not drawn).

## Courtyard pine  (`remake/recipes/pine_court/pine.py`; rooms 32 / 33)
- The left Mercator castle court's own pine sprite; the approved style C pine (asset 2) in a TRIMMED variant (even tiers, short regular tips, no jitter: a gardener's tree, user 2026-11-12 'ja, passt'), fitted to it (IoU 0.93), 15 pines placed by a template match
  of the sprite (`feet.json`). Same model in the light (`surface`). Details: `remake/recipes/pine_court/README.md`.

## Pine clusters  (`remake/recipes/pine_cluster/pine_cluster.py`; rooms 183 / 425 / 430 / 433 / 453 / 474 / 484 / 514 / 636; since 2026-11-19 also solid block DOMES as candidates, room 453)
- Groups of drawn forest pines that the automatic shapes took as one object: every pine its own WILD style C pine (the courtyard pine's
  recipe, trim 0), fitted to the forest pine sprite (IoU 0.87), feet by template match + the game's collision cells (user 2026-11-16 clay
  preview of the 636 group 'ja'). Same model in the light (`surface`). Details: `remake/recipes/pine_cluster/README.md`.

## Shop counter  (`remake/recipes/counter/counter.py`; rooms 695 / 696 / 697 / 719 / 720; REMAKE ONLY)
- Island 2 x 6 with a small cloth on the top, wall counter 6 x 1: plank top, vertical boards. Not a light shape: the collision box is the drawing,
  sub-pixel details only made dotted lines in the light (README).

## Castle bed + bench  (`remake/recipes/castle_bed/castle_bed.py`, `remake/recipes/castle_bench/castle_bench.py`; tileset 15)
- Bed: legs, frame rail, blanket, pillow, headboard (rooms 63 / 64 x2, 67, 77, 108). Bench: padded seat on four cabriole legs (67, 77; 72's short one open).
  Same model in the light (`surface` + `air`). Measured on room 67 (README).

## Mercator fountain court city wall with round towers  (`remake/recipes/proxy_wall_638.py` -> `landstalker/data/proxies/wall_638.obj`; room 638 only)
- Reference: room 638, west wall column 17 (blocked height 0), towers = collision column 18 rows 26..29 / 38..41 / 50..53 (height 9), north wall row 17; window `rom_picture.py ROM 638 480 0 900 620`.
- Light variant v2 (2026-11-18, user chose 'C' on the overlay, 'Raum 638 ok'): towers drawn ROUND (curved brick rows) but the foot sits on the collision edge x 304 with grass drawn in front -> half cylinder r 32 on the wall face (288, cy) CLIPPED at x 304 (round flanks, flat front). Left edge U 608 exact, right edge U 684 (drawing 688), foot on the drawn grass line. Door niches 4 deep: towers y cy-15..cy-1, z 48..120; wooden wall door y 336..352, z 48..90. Tops flat at the measured heights (the picture cuts them).
- Light check: lightedges 638 --spots 0 edge px old / new (noon and 17 h); noon practically unchanged, at 17 h the west wall now shades the court (the old box proxy did not; cause not traced).
- Remake: build symmetric real round towers separately ('remake vs light variant'); the full half cylinder would stand in the drawn grass.
- STATE: light variant done (user OK 2026-11-18).

## Arcade of room 486  (`remake/recipes/proxy_arcade_486.py` -> `landstalker/data/proxies/arcade_486.obj`; room 486 only)
- Reference: room 486, wall cells x 43..44 (688..720) at 240 with the passages rows 37..39 / 52..54; window `rom_picture.py ROM 486 820 300 700 600`.
- Light variant v2 (2026-11-18): three piers with stepped corbel brackets and a flat lintel; per run ONE closed solid: elevation = top 240 + the measured underside (PROFILE of v1..v3, user corrections 2026-11-08) through the slice centres, vertical steps between courses, extruded along x; caps ear-clipped (the game's OBJ reader fans n-gons). Overlay on the drawing: outline on the drawn edges.
- Light check: lightedges 486 --spots 0 edge px old / new at 13 h and 17 h; only thin lines at the course edges change (the old 4 unit stair shadows under the courses are gone).
- STATE: light variant done (2026-11-18). Remake: real stones / rounded courses later.

## Town house (Mercator type)  (`remake/recipes/proxy_houses_632.py` -> `landstalker/data/proxies/house_632_<n>.obj`; room 632 houses 1 2 4 5 6 7 8 9; first recurring object type of HANDOFF NEXT -238)
- Reference: room 632 (map $0D2104), houses = blocked height map components of height 4 (one storey) / 7 (two storeys), the 1 cell strip of height 2 behind them is collision only; picture `rom_picture.py ROM 632 0 0 2400 1400`.
- Measured 2026-11-20 with `remake/tools/fit_house.py` (scene fit of ALL houses at once on layer A, union of wings rendered with the view ray (1, 1, 1), walls free): every wall on the map cell lines; one storey walls 16 -> eave 64, flat grey top 86.5 starting 25.5 in (41 deg); two storeys eave 112, top 134.5, 26 in; 90.4 % of the model pixels match (rest = layer B doors / windows, pines in front). L / long houses = UNION of wings with the same heights (valleys), Blender boolean.
- Openings with `remake/tools/find_openings.py`: walls are 16 unit wall tiles, windows / doors are the SAME tile in every slot: window frame slot + 3..16, storey floor + 22..38, recess 1.5, sill slot + 0..16, floor + 16..21, 1 out; door slot + 4..16, z 19..59, recess 2.5; one small window (house 8 +y x 791..796 z 40..53); the framed shop sign on house 6 is flat. Stone plinth FLUSH (user 2026-11-20).
- Light check (lightedges 632 --spots, 23 spots, GPU): 0 edge px old and new; windows: no bright strips (at most +3 levels), recesses / sills up to -15 (soft shade); the old guessed hips (z0 = collision 64) left a wrong dark band on house 6's wall and a dark blotch behind the planter of house 2: gone.
- RYUMA 610 / 611 (one map, 2026-11-20, `remake/recipes/proxy_houses_610.py`, builder `remake/lib/town_house.py` shared with 632): 6 houses on terraces (own ground z0 16 / 32 / 48 / 112), walls 48, top 24 above the eave, 24.5 in (44 deg, 1.5 higher than Mercator); 'left', 'pb', 'pf' drawn in layer B (heights from the Ryuma value, pb / pf small top read on the composed picture); small corner window x 591..596 z 40..53 on pb / pf. lightedges 610,611 --spots: same 53 / 54 edge px old and new (spot 5, not the houses); the old hip over the hill house (ridge 222) cast a wrong shadow on the path in front: gone. Church, lighthouse, stone stairs of Ryuma: one-offs, later.
- STATE: NEAR-FINAL light variant (user OK on the clay previews and the detail level 2026-11-20; 632 confirmed in play 'Lichtformen sehen gut aus'). Next: the same type in the other towns (list in ~/Project-Friday-Test/lktest/Platzhalter_Aussenkarten.md), the big building of 632 (cells 15..20 x 24..41) as a one-off.

## Mercator church complex  (`remake/recipes/proxy_church_632.py` -> `landstalker/data/proxies/church_632.obj`; room 632)
- Hall (hip) with two CROSS WINGS beside the porch (gable end walls on x 378 with the arched windows: left y 893..922 eave 58 apex 72.5, right y 795..827 eave 56 apex 72, measured per picture column), porch (cross gable). The yellow house in front is its own building since 2026-11-20 (town house 9, footprint / roof from the 2026-11-09 fit, right wall x 320). 2026-11-20 (user marks): the porch ENTRANCE is an open rectangular opening (jambs y 842 / 877, lintel z 58, recess 12.5 to the dark doorway at x 382) with ONE rectangular corner block in each top corner (11 wide, underside z 50); the porch gable re-measured per picture column on the front plane x 394.5: 45 deg both sides, apex y 860 z 90 (was 856.5 / 93.5), right slope runs on at 45 deg to the right pier's outline y 826 (eave 56 there, no extra corner, user), was 823; hall back corner y 794.5 (was 797). Check picture: `edge_overlay` (model edges incl. silhouettes over the drawing).
- STATE: light variant, user check of the entrance open.

## Massan log house  (`remake/recipes/proxy_houses_592.py` -> `landstalker/data/proxies/house_592_a.obj`, `house_592_b.obj`; builders `remake/lib/massan_a.py` (house A, also the remake's source) and `remake/lib/log_house.py` (light variant, any house); room 592)
- Light variant = AS DRAWN (memory 'remake vs light variant'): round logs r 4 every 8, planes = cell lines inset 3, ground 0 (A, B), eave 50, bulging thatch top 77, posts, open dark doorways with lintel log and the log above running over the door (user 2026-11-20).
- A: massan_a geometry with hx = HX (the drawn eave; remake +1.5), nseg 8, no skull / ridge knot (7164 triangles); silhouette on the drawing.
- B (5 x 7, ridge along y): ridge log bundle, two SQUARE vent hoods 12 x 12 on four legs (user: 'eckig'), window S x 557..569 z 24..38 behind a top-hinged shutter propped out 3, door S 590..606 up to 35, S posts only beside the door (586.5 / 609.5), no W posts at the S end, W logs end behind the S logs at the SW corner, S logs stick out 1.5 there; round window E y 530 z 28 (3762 triangles). Several user rounds with marks (shutter spacing corner -> shutter ~10, shutter -> door ~16).
- C / D (west pair, cells 23..27 x 18..21 / 22..25, ground 32) and E / F (east pair, 32..36 x 16..19 / 20..24): two houses each, wall to wall with their own walls and roofs (front roof over the back one); doors = B's tile on the E side, posts = dark edge of the drawn post + 4.5, D: top-hinged shutter S 397..408 out 6, F: plain open window S 540..557 z 25..34.5 ('openings'); roofs: 5 x 4 = one stick crossing at EACH ridge end ('sticks_ends', shifted x +3.5 / z -4.25 to the drawn bindings, r 2.6), F square = one crossing in the middle, vent hoods back-projected from the drawn cap centres (C 405.5 / 338, F 576 / 359).
- G (tall house, 23..27 x 14..17, ground 32): eave 114 / top 141 above the ground (collision top 144 + 2 as the others), E door + sign board + SMALL upper window (only the dark strip above the cloth, user) with a blue cloth hanging out over the sill down the wall ('cloths'), S two round windows (A's tile) at z 59 / 91, full-height posts.
- CORNERS (user 2026-11-20, all houses incl. A / B): FLUSH mitred corners ('corners': 'mitre', massan_a.build(mitre=True) in the light recipe only): the drawing shows the logs of both walls meeting in a chevron, no stack of end discs (B's SW corner keeps the user's marks).
- STATE: A..G user OK on the clay / drawing comparisons 2026-11-20; in data/light_proxies.json (room 592 = the only room on this map) since 2026-11-20, GPU lightedges before / after: see DEBUGGING.

## Gumi log houses  (`remake/recipes/proxy_houses_603.py` -> `landstalker/data/proxies/house_603_{p,q,t,s,w}.obj`; rooms 601 / 602 / 603, one map, ground 96)
- Same tiles as Massan (pixel comparisons 2026-11-20): T (39..43 x 30..33) = G + (256, 256, 64) without the cloth (small upper window open); S (41..45 x 42..48) = B + (112, 208, 96); W (25..29 x 48..52, skull sign) = A + (112, 336, 96) + one more E post (A coords 490.5); P (25..29 x 30..34): S door 414..430, G's cloth tile 48 lower over a small window under the eave; Q (31..35 x 30..34): S door 510..526, D's shutter tile at 541..552, vent 533.5 / 543. Corners mitred, back_in 3 (back eaves checked 0 px).
- Massan A re-measured the same day (door 462..478, posts S 298.5 / 305.5 / 346.5 / 353.5, E 442.5 / 449.5 / 458.5 / 481.5 / 497.5; the kit numbers were 1.5..4 off), light variant only.
- STATE: in data/light_proxies.json (601-603); user check open (HANDOFF -244).

## Verla town houses  (`remake/recipes/proxy_houses_711.py` -> `landstalker/data/proxies/house_711_{b,c,d,e}.obj`; rooms 711 / 712, one map $0A669E)
- Same type as Mercator / Ryuma (remake/lib/town_house.py). Collision height of a town house cell = its eave (Ryuma checked), ground 48 below. B (42..47 x 26..32) and D (43..47 x 41..45) fitted in layer A (fit_house: cell lines, eave + 24 top, inset 24.5 = Ryuma); C (22..28 x 33..37) and E (22..28 x 41..45, ground 48) drawn in layer B: cell lines + type heights. Openings by find_openings (E's small flat plaque and the shop sign are no openings). Church = one-off, later.
- STATE: in data/light_proxies.json (711 / 712); user check open (HANDOFF -245).

## Plants: pine, small pine, bush  (`remake/recipes/plants/` -> `landstalker/data/proxies/plant_{pine,small,bush}.obj` + `landstalker/data/plants.json`; 133 outdoor rooms, 2026-11-20)
- pine = the wild style C pine fitted to the forest / town pine (IoU 0.87); small = the same recipe on the small pine (the big pine's tiles without the middle 16 rows; IoU 0.867); bush = round crown + 5 lumps on a Y stem (`bush.py`, IoU 0.90, ONE bush drawing in every tileset). User OK on clay preview + drawing sheet. Placed by `plants.py` (plane A template match + height map, README there), drawn by LK_LTPLANT v1 as instances. Light variant = as drawn; the remake can use richer versions of the same recipes.

## Destel log houses  (`remake/recipes/proxy_houses_726.py` -> `landstalker/data/proxies/house_726_{a,b,c1,c2,d1,d2,e}.obj`; room 726, 2026-11-20)
- The log house builder (`lib/log_house.py`) with Destel's details: plain hip / pointed thatch (ridge 'none'), thick SE corner post, door jamb stubs, arched windows (rectangular openings for now), tilted shutter (B), two framed signs (D2). Footprints = collision blocks inset 3; eave 50, top 77 / 84 (fit_house FIT_PALETTE=destel, 93.5 %). Waiting for the user's OK (HANDOFF -248).

## Verla church  (`remake/recipes/proxy_church_711.py` -> `landstalker/data/proxies/church_711.obj`; rooms 711 / 712, 2026-11-20)
- The SAME drawing as the Mercator church (plane A identical, 7 / -28 cells, 6 steps up; no yellow house in front): the confirmed `church_632.obj` moved by (+112, -448, +96).

## Ryuma church  (`remake/recipes/proxy_church_610.py` -> `landstalker/data/proxies/church_610.obj`; rooms 610 / 611, 2026-11-24)
- The SAME drawing as the Mercator church again (plane A window found at U +288 V -160, the composed picture of roof / porch / wings pixel-equal; the 72 cell collision block equal in every cell): `church_632.obj` moved by (+16, -272, +32), ground 48.
- ONE measured change: the hall's -x wall (hidden behind the yellow house in Mercator, guessed 238 from the symmetric hip) is visible in Ryuma: outline column U 785..786 -> x 235.5 (Mercator coordinates); the flat roof top stays measured, only the hidden -x hip gets 2.5 wider. Overlay ~/Project-Friday-Test/lktest/church610/ovz2.png (local). Built while the user was away; Mercator / Verla keep 238 (could take 235.5 too after the user's OK).

## Stone face  (`remake/recipes/stone_face/` -> `landstalker/data/proxies/stone_face_433_{0..5}.obj` via `place_433.py`; room 433, 2026-11-21)
- Six pixel-equal copies on single blocked cells `$43` (top 48, ground 16): (19,22) (28,22) (33,22) (19,30) (28,30) (33,30); reference (19,22), base centre x 312 y 360 (U 1136 V 320). Drawn ~38 high (collision 32).
- Smooth head: foot radius 7.5 -> widest 8.2 (smoothstep), elliptic dome from 63 % of the height, deeper towards the face (sx 1.21), face to +x turned 15 deg towards +y, flattened face side, mouth recess (47..71 % of the height), brow ledge. Fit on the silhouette (holes filled, covered - 12 x outside): IoU 0.911, 1 px out.
- User 2026-11-21 'passt als Lichtform' (asked whether the facets of the lower part give edges: no, the light smooths normals within 35 deg; GPU shots of 433 smooth, lightedges 0 at 10 spots). Remake: materials / the carved face details later.

## Dead swamp twigs  (`remake/recipes/dead_twig/auto_twigs.py` -> `landstalker/data/proxies/twig_ROOM_K.obj`; swamp rooms 431 432 433 436 443 444, 2026-11-21)
- Nearly every twig is its own drawing (only the big twig of 432 / 436 repeats), so the light shapes are built STRAIGHT FROM THE DRAWING (user: 'automatisch'): stems by bark colour away from the grass, thin and free standing; the whole twig over bark + outline colours; Zhang-Suen skeleton (staircase pixels and spurs < 3 px removed) -> chains -> tubes (12 sides, radius (bark width + 2) / 2.83, 60 % at the tips) in the picture plane through the foot (view ray). Board walk posts / nail heads, cliff streaks, roots and bush trunks (feet within 24 of a plants.json foot) are left out; other tileset 13 rooms gave only false hits (statue, vines). 62 twigs.
- The hand version (`dead_twig.py` + `variants.json` 'big', fitted IoU 0.728) agrees with the automatic one; the automatic one is placed. Built while the user was away, sheet ~/Project-Friday-Test/Mockups/sumpfzweige_alle.png. Remake variant (3D spread crown) later.

## Stone pillar  (`remake/recipes/pillar_739/` -> `landstalker/data/proxies/pillar_{739,426}_{0,1}.obj` via `place_739.py`; rooms 739 (2026-11-21) and 426 (2026-11-24))
- Two pixel-equal copies on blocked `$43` cells (24,15) / (19,15), ground 0: square plinth (12.2), round base ring, round shaft (r 5.2 -> 4.35, slight entasis), neck ring, echinus, square abacus (12.5), top ~50. Fit IoU 0.857 (the black inner pixels and the moss in front of the plinth are the rest). Open for the remake: the drawn abacus top has a recessed inner diamond. Built while the user was away, sheet Mockups/saeulen_739.png.
- Room 564 (Greenmaze, Sunstone shrine passage, 2026-11-24): the same pillar on cells (47,21) / (47,23), blocked 64 on ground 16 (template axis at the cell centres, IoU 0.81 / 0.63); replaces an automatic lathe up to 103.
- Room 426 (cave mouth below the waterfall): the same pillar outline in a mossy palette on cells (46,43) / (46,48), blocked 48 on ground 0, axis at the cell centre like 739 (overlay fits; silhouette IoU 0.76 / 0.65 only because of grass in layer A and a bush in front of the second foot).

## Rustic log fence  (`remake/recipes/fence_426/fence_426.py` -> `landstalker/data/proxies/fence_426.obj`; room 426 by the waterfall, 2026-11-24)
- Collision: 8 blocked cells height 48 on ground 0 (L: x 27..28 y 34..38). Six round tapered posts (r 2.1, worn domed tops; tops 38..62 as drawn, B and E short) on three runs: front y 621 (A, B), side x 464 (B C D F, feet seen at V 540 / 534 / 518 / ~504), back y 546 (E, F).
- 14 rail logs (r 2.0, domed ends): each drawn rail's centre line (two picture points) lifted onto its run's vertical plane, so slopes / free ends / the upper rail over the short post B are as drawn; an end within 7.5 of a post on its run (hidden behind it in the drawing) is continued to the post axis (first clay preview: rails floated between the posts). Clay preview ~/Project-Friday-Test/Mockups/gelaender_426_clay.png, overlay lktest/r426/ovf.png. Built while the user was away, to be checked.

## Rope railings of Kazalt  (`remake/recipes/railing_737/` -> `landstalker/data/proxies/railing_737_*.obj`; room 737 outside, 2026-11-26)
- Collision: 2 step blocked strips (height 9 on walkways of 7; 8 on the inner courtyard's) along every railing = solid boxes in the light (bug sweep: a saw tooth edge through the sword glow on the path).
- 73 posts found by a template of one drawn post (7 x 27 px, mirrored copies too; `measure.py` -> `params.json`, our measurements only): round shaft r 1.75 x 16, dark neck, teal ring r 2.7 x 4 (the rope runs through it), ellipsoid cap r 2.1 x 3, 27 high. Axis = the drawn shaft's middle incl. its dark rims (first version 4 px right: the template window started at the shaft's light core; user 'die Pfaehle liegen noch nicht gut drauf', fixed, median offset 0.14 px).
- Feet: the view ray through the foot pixel stops at the first floor (a railing strip counts as the walkway it borders); a ray meeting a step's side (height off the 16 grid) -> the stair step beside the void. 70 sagging ropes (r 0.9, ring height 19.5, sag 3.3 per 32 unit span, ~ span^2) between neighbouring posts (a post nearly on the way = a corner / stair link).
- Light ops: 6 straight runs (floor 112 = the walkway under posts and rope: air below the rope) + 15 stair posts as single ops on their step. User OK on the clay preview + overlay sheet (~/Project-Friday-Test/Mockups/gelaender_737_blatt.png). Sword glow edges in 737: 309 / 153 / 84 / 52 px -> 0; daylight unchanged.

## Small stone block  (`remake/recipes/stone_cube_486/` -> `landstalker/data/proxies/stone_cube_486_{0..3}.obj` via `place_486.py`; room 486, 2026-11-21)
- Four pixel-equal copies on isolated walkable 1 step cells (49,35) (57,35) (49,55) (57,55), ground 0 (the automatic lathe was 37 high): block 16.3 x 16.3, 16.3 high, rounded vertical edges, rounded top edge. Fit IoU 0.928 (the moss in front of its foot left out). Built while the user was away.

## Mooring post  (`remake/recipes/bollard_641/` -> `landstalker/data/proxies/bollard_{641,642,644}_{0,1,2}.obj` via `place.py`; Mercator docks, 2026-11-21)
- Three pixel-equal copies per room (641 / 642 / 644 = one map) on walkable 2 step cells (25,37) (35,30) (57,26), ground 16: a stone mushroom (flared foot r 6.3, waist r 5.3, cap underside to the rim r 7.7 at z 11.2, elliptic dome to 18). Built as a PROFILE with a few clear measures (`params.json` 'profile', turned by `lathe.py`): IoU 0.923, 0 px out. Two free ring fits before were rejected in self-review (a cone tip; a lampshade top, neck too thick). Open: the drawn foot has small flared corners the round profile does not reach. Built while the user collects feedback.

## Dock log hut  (`remake/recipes/pavilion_641/pavilion.py` -> `landstalker/data/proxies/pavilion_{641,642,644}.obj`; Mercator docks, 2026-11-21)
- First read from plane A alone as an open pavilion on three posts = WRONG; with both planes (user: 'nicht alles auf der Ebene'): a LOG HUT on stilts, two open front sides (big openings, the sill on the floor), dark interior with the closed back walls (plane B). Pixel-equal in 641 / 642 / 644; collision only 3 single high cells, footprint measured on the drawing (mask = plane A drawn OR composite black, water out, pier cut): half side 31.8 at x 751.2 y 559.0, four log-crib corners 10 x 10, back walls of round logs, floor deck 17.5, round stilts r 3.5 down to the water 8, eave 76.5 + thatch 2.2, fascia 5.9, convex thatch (bulge 4.4) to 102, knob. IoU 0.947, 12 px out.
- Open: the drawn corners look a bit stronger (fit at its lower bound 10); the knob is drawn as a straw bundle with spikes.

## Dock crate shed  (`remake/recipes/crate_shed_641/crates.py` -> `landstalker/data/proxies/crate_shed_{641,642,644}.obj` + `crate_{641,642,644}.obj`; 2026-11-21)
- FINAL (2026-11-21 late, user 'passt', after many rounds: draft pictures first, then build). Crates 16 x 16 x 16 with raised frames (corner posts chamfered 1 unit ONLY on the inner edge, so the stack's outer corners stay straight lines in the silhouette; rails, middle band, boards sunk 1), stacked per cell on ground 16. HEIGHTS = THE COLLISION MAP (outside the roof it is exactly the crate height: 58,19 = 4 -> 3 crates, 58,20 = 3 -> 2, 59,19 / y 21 singles = 2 -> 1; the wall cells = 5 -> FOUR crates): back row y 19 x 49 + 52..57 four; front row y 20 four EXCEPT x 53 = two and x 55 = one (their lids show under the eave); x 50 / 51 an empty alcove; x 58 three / two, x 59 one, singles x 49..51 and 57 in row 21. Only ~3 rows are visible in front: the 4th sits right under the roof, half hidden by the eave (user: 'es gibt 4 Kistenreihen, die 4. ist direkt unterm Dach').
- ROOF (params roof): hipped thatch, a solid body whose underside lies ON the 4th crate row: front eave z 80 at y 352 (overhang), back eave z 72 at y 296 (same picture as the crate's back-top corner (928, 304, 80); keeps the back slope visible like the drawing's thatch strip above the crosses), back corners 8 left of the front ones (x1_back 920, x0_back 777) so both END EDGES run iso-parallel to the crate edges (user: 'Winkel nicht im selben isometrischen Ansicht'), x 785..928, ridge 86 at y 322 (ridge_y), hips 11 / 3, the front-left corner cut back to (785, 343) with the eave from x 800 (the drawn thatch tapers in at the left tip), crate tops under the roof ends CUT to the roof surface (clip_to_roof; also the 49 crates just left of the roof along the continued left hip; user: 'die letzte Reihe oben abschneiden'). Ridge: Massan style crossed logs, small (L 4, 20 deg, r 1) so they stay inside the drawn top line. Checked by silhouette overlay (top edge within ~1 px over the whole length; sides straight).
- History / mistakes (MODELING_LESSONS-worthy): (1) a stack at x 48 that is pine collision; (2) 3 instead of 4 rows because collision 5 was taken as 'crates + roof'; (3) the roof floated (eave read 8 too high: every drawn edge is ambiguous along the view ray (x+d, y+d, z+d)) and then got a separate slab ('lid under the roof'), raised end corners (a kink in the front eave), hips cutting through crates; (4) painter-sorted clay previews lied, a z-buffer render (scratch zb.py) and an edge overlay of every crate (scratch full.py / draft.py) settled it. Discussing a DRAFT picture before building stopped the loop (user: 'mach erst einen Entwurf, dann reden wir drüber').

## Dock stone buildings  (`remake/recipes/stone_buildings_641/buildings.py` + `params_left.json` / `params_right.json` -> `landstalker/data/proxies/stone_buildings_{left,right}_{641,642,644}.obj`; 2026-11-21)
- SPLIT 2026-11-21 late: one model + one op rectangle per house (22..29 / 33..39 x 19..28): a single rectangle over both covered the pine row between them, and 'surface' mesh ops hide plants in their cells; the three 48 blocks at 43..45 x 19 were pine collision (removed).
- The buildings ARE the collision blocks (height overlay: towers 96 at x 26..28 y 19..24 and x 36..38 y 19..21, wings 48, step blocks 32); the automatic shapes put hip roofs on them (wrong: flat tops). Model: the towers as one block each with chamfered vertical edges (1.5), the other cells as boxes per row run from z 10 to their height, a ring of cornice stones (4 wide every 8, proud 1.5, the outer top edge weathered down 1) on the tower tops, the wooden door of the left tower (face x 464, y 321..336, z 48..88; the cell (28,20) is only 48 high = the doorstep) as a recess with frame. The blue-green wall foot = wet stones (the brick pattern continues), no openings. IoU 0.84 on plane A (rest: wall foot below the ground / pines). Open (remake): masonry relief, the blue-green wet course as material.

## Mercator 632 details  (2026-11-21, built while the user was away, to be checked)
- WELL (`remake/recipes/well_632/well.py` -> `well_632.obj`): a stone rim walkable at 32 around a water hole (the collision; the blue was taken for a canal at first) carries a wooden hoist (post to z 59, crossbar over both sides, brace on the back side, rope with two weights into the well) and a staved tub (r 5.9 -> 6.6, 16 high) on cell (16,20). Op (14,18)-(18,24) also drops the automatic hip over the rim and the lathe (first read as a lantern on a wall).
- DRAWBRIDGE CHAINS (`remake/recipes/drawbridge_632/chains.py` -> `drawbridge_chains_632.obj`): the deck is walkable floor (x 37..40, y 16..19, 16); two chains of links (every 2.6, turned in turn) from the deck's outer end (x 656 / 592, y 320, z 25) to the castle wall face (y 224, z 69), both ends measured on the deck edge.
- GRANITE BLOCK on a lawn patch (`stone_cube_486/stone_cube.py` + `params_632.json` -> `stone_block_632.obj`, cell (35,29)): IoU 0.917, sharper edges than the 486 blocks.
- Removed: the hip over the raised flower bed by the moat (blocked 32, flat top). Left: the red tile roof #4 (a real building, own task).

## Fluted column of 524 / 525  (`remake/recipes/pillar_739/pillar.py` + `params_524.json` -> `pillar_524_{0,1}.obj`, `pillar_525_0.obj`; 2026-11-21)
- Square capital (abacus 15.9) with volutes (not modelled), round fluted shaft r 7.8 -> 7.6, on walkable 5 step cells (80) on the floor 32: 524 cells (29,54) / (38,54), 525 cell (40,25) (pixel-equal drawing). The fit mask held wall bits, the column itself is covered except a 1 px rim.

## House of room 441  (`landstalker/data/proxies/house_441.obj`; 2026-11-21)
- The drawing is the Destel house B (pixel search: 81 % equal at picture offset (-64, +208); the rest = three blue cloths and neighbours): `house_726_b.obj` (remake/recipes/proxy_houses_726.py) moved by (-256, -320, -80) onto the collision block x 14..18 y 16..20 (blocked 80, ground 32; E door = the walkable cell (18,18)). Open: the three blue cloths (S wall two, E wall one) for a 441 variant of the recipe (log_house cloths).

## Watchtower canopies of room 454  (`remake/recipes/awning_454/awning.py` -> `awning_454_{0,1}.obj`; 2026-11-21)
- Two copies (y 192 apart, 96 % equal): a red cloth (side 40, edge z 123, sagging 3 in the middle, 1 thick) with a fringe band (4) on four poles from the tower top (collision blocked 112), an A-frame over it (apex z 170) with a banner plate (9 wide, z 145..164) facing the viewer. Centres (288.25, 467.75) / (288.25, 659.75). The tower is the collision.

## Ryuma lighthouse  (`remake/recipes/lighthouse_611/lighthouse.py` -> `lighthouse_{610,611}.obj`; 2026-11-21)
- Collision x 15..17 y 56..58 blocked 192 (= the roof eave), door niche east at the walkable cell (17,57), ground 32. Model: stone body (chamfered) to 150, parapet ring (3 thick) to 159, four corner posts (4 x 4) with arch brackets, beam ring, tile pyramid roof (overhang 1) from 192 to the apex 214 (both read on the drawing), beacon box 10 x 10 x 20 with a flame cone. Open: the arches as real arches, roof tiles relief.

## Town house of room 442  (`remake/recipes/proxy_houses_442.py` -> `house_442.obj`; 2026-11-21)
- Ryuma town house type (the Ryuma 'fr' front walls 90 % equal, but 442's house is square 80 x 80 and the door sits in the second slot): town_house builder, walls 272..352 x 272..352 on the ground 48 (collision blocked 96, door = walkable cell (18,21)), eave 96, flat top 120, inset 24.5, door +y slot 288, windows +x slots 288 / 320. The hips over the planter / the low block beside it removed.

## Log hut of room 468  (`remake/recipes/proxy_house_468.py` -> `landstalker/data/proxies/house_468.obj`; room 468, 2026-11-24)
- NOT its own type (0a496 said so): Massan house B's wall tiles in a greener palette on a 5 x 5 square (collision x 35..39 y 27..31, 64 on ground 16 = B's S five rows moved (+16, -64, +16), picture U +80 V -40). B's door / shutter / S posts / E round window moved; N / W posts at B's distance from the N corner; square thatch with one stick crossing (as Gumi Q). lib/log_house.py. Silhouette 96 % on the drawing; clay ~/Project-Friday-Test/Mockups/huette_468_clay.png. Built while the user was away.

## Big apple tree of the tree-warp map  (`remake/recipes/warp_tree_510/warp_tree.py ROM` -> `landstalker/data/proxies/warp_tree_510.obj`; rooms 510..513, 533..539 = map $11759C, 2026-11-24)
- Trunk collision blocked 160 (x 29..32 y 27..28 + x 29..30 y 29..30), island walkable 0. Trunk: drawn constant 60 px wide -> r 21, axis x 493.75 y 462.25, root flare + 6 flat buttress roots (~26 long, drawn roots reach ~30 beyond the trunk).
- Crown: drawn U 984..1455 x V 296..446 around the trunk axis -> envelope = ellipsoid (half axes 166 along the screen, 63.6 deep, 60 high, centre z 107; a ROUND crown of that width would be >= 234 px high in the picture, the drawing is an iso cheat, light variant = as drawn) scaled per screen direction to the drawn, smoothed (+-12 deg) crown outline; filled with a core (0.8 of the envelope) + 47 leaf clumps (spheres r 30..40 reaching the envelope). v1 = one smooth ellipsoid looked like a mushroom cap with a dent at the pole (pole not corrected) -> rejected in self-review.
- GPU (510 spot 2): island mean brightness unchanged (59.2 / 59.2), the trunk now round-shaded with a soft shadow; lightedges 0. Checked 2026-11-24 that ALL 11 rooms show this drawing (one GPU shot each: the same island; LESSONS 'one map, several drawings'). Clay ~/Project-Friday-Test/Mockups/warpbaum_510_clay.png. Built while the user was away.

## Room 362 hole (labyrinth entrance)  (NO model, user decision 2026-11-24)
- The 2 x 2 cells at height 0 in the 32 clearing (x 26..27 y 19..20) are a HOLE drawn like a rock bump; user: 'das ist ein Loch, lass mal aus' -> no light shape (do not list it as a leftover again).

## Log hut of room 489  (`remake/recipes/proxy_house_489.py` -> `landstalker/data/proxies/house_489.obj`; room 489, 2026-11-24)
- The room 468 hut MIRRORED x <-> y (door / shutter on the E wall, round window S); collision x 18..22 y 22..26, 64 on ground 16, door cell (22,25). Silhouette 96 % on the drawing; GPU: soft roof, lightedges 0.

## Mercator docks: room 643  (2026-11-24)
- 643 = the docks while the Sunstone is not yet in the Ryuma lighthouse (user) = the same map as 641 / 642 / 644 but it had NO models and no plants: all 641 ops (crates, crate shed, stone buildings, hut on stilts, mooring posts, plantcells, removes) copied, they use the 641 OBJ files (identical to 642 / 644's); the 30 plants of 641 copied in data/plants.json (the template match would miss them in the dark palette). GPU: the crate shed is shaded like in 641, lightedges 0.

## Mercator town house 3  (`remake/recipes/proxy_house_632_3.py` -> `landstalker/data/proxies/house_632_3.obj`; room 632, 2026-11-24)
- The one-off in the upper left (cells 15..20 x 29..41) left out by proxy_houses_632.py: right wing x 240..320 y 464..544 + left wing x 240..304 y 544..672 (both TWO: eave 112, top 134.5, 26 in; fit_house), one-storey annex x 304..336 y 544..624 with a walkable ROOF TERRACE (floor 64) behind a U-shaped stone parapet 12 thick up to 80, the upper doorway onto it one cell deep (walkable cell 18,36), small wing x 304..336 y 624..672 with a pointed hip 64 -> 84; openings = the standard tiles (find_openings). Clay ~/Project-Friday-Test/Mockups/haus3_632_clay.png. GPU 632 spots: lightedges 0. Built while the user was away.

## Ryuma lighthouse lantern room close-up  (`remake/recipes/lantern_627/lantern.py` -> `landstalker/data/proxies/lantern_627.obj`; room 627, 2026-11-24)
- The map ($0B02C9, rooms 627 / 628 / 629?) holds TWO drawings; the room decides which lies over the cells: 627 = the closed lantern room (right drawing: two glass cylinders), 628 BROKEN = the cut-away drawing (floating roof, dome lamp; picture U - 512, V + 32 against 627, floor grid match 2311 / 2400). 628 got its own model the same day: `lantern_628.py` -> `lantern_628.obj` (no outer roof / front post, three posts cut at 102, a small floating pyramid 106 wide 127 -> 182 with a hanging arch housing 62..127, the dome lamp r 14 in a crown of 12 glass petals; GPU 628 spots: lightedges 0, floor softly shaded under the roof). Room 629 REPAIRED (same map) shows the CLOSED drawing (GPU shot): it uses lantern_627 too. Review 2026-11-24 (user: real 3D forms, not boxes): the roofs are TILE COURSES (one every 4 units of height = the drawn 8 px rows) with ridge caps on the four hips, the posts got a base and a capital; 628's lamp is a broken GLASS BOWL (smooth wall r 12 -> 27, only the rim jagged) instead of 12 spikes (user: 'im Original sind doch da keine Stacheln').
- Floor 16 inside a 16 rim (room x / y 320..496), four corner posts 15 wide with concave arch brackets, eave band 158..167, tile pyramid to 253 (its apex projects onto the drawn back roof corner; first read the back corner as the plate top 181 -> corrected), two hanging glass cylinders r 8 + lamp base, curb, tower body below the floor. GPU: floor darker under the roof, posts round-shaded, lightedges 0. It replaces an automatic block over the whole room up to 215.

## Mir's tower base  (`remake/recipes/mir_tower_475/tower.py` -> `landstalker/data/proxies/mir_tower_475.obj`; room 475 MIR_TOWER_EXTERIOR, 2026-11-24)
- The collision holds only an 80 high block (x 16..27 y 16..25); the DRAWN blue tower is wider (front corner where the scale pattern turns U 1213 -> (442.5, 413.5); front wall from U 865, right wall to U 1405 -> x 97..442.5 y 221.5..413.5) and runs beyond the picture top: body to 440 (the light used to know only the lower 80). First built on the collision rectangle: corner 13 px off, corrected.
- Arched doorway one cell deep (x 339.5..361.5, 32..92) with threshold, a step slab with rounded front corners (first read as a half circle).
- v2 (user: 'hast du es als echte 3D-Form gemacht?'): the walls carry the drawn SCALE RELIEF (16 x 16 stone shingles, autocorrelation peaks 16 / 32 both ways; flush at the top, 1.5 out at the rounded lower edge; only up to the picture top), rounded step top.
- GRIFFIN HEAD over the door (`griffin.py`, metaball sculpt + explicit feather blades, generated into ~/.landstalker_remake/assets/griffin_475/, decimated to ~6000 triangles; placed in tower.py by a silhouette fit on the drawn carving: scale 0.85, width x 2.0, centre x 353 z 100, IoU 0.73). Rounds with the user: 'Statuenkopf' -> 'Vogel-Greif, keine runde Nase' -> a tube beak 'sieht aus wie ein Wasserhahn' -> proportions as drawn -> an image relief from the 28 drawn pixels was only noise (dropped) -> sculpt with a feathered neck; the neck first rose high into the wall ('nicht so nach oben weg'), final: out of the wall at about head height, a gentle arch, the head upright looking out; user: 'mach es so, dass es fuer die Lichtform passt und auf der Zeichnung liegt'.
- Wall LANTERNS (user 2026-11-24, two rounds of marks): they sit IN niches of the wall (14 wide, 6 deep); only the two GOLD parts stand out ~3: the holder on top (z 72..94) and the round knob below (34..56); the glass between them (56..72) lies inside the wall face. Clay ~/Project-Friday-Test/Mockups/mirturm_475_clay.png; GPU 475 spots: lightedges 0.


## Mercator house furniture, indoor survey  (`remake/recipes/case/case.py` specs `merc_*` -> `landstalker/data/proxies/merc_<name>_<room>.obj`; tileset 2 houses, 2026-11-24)
- Found by `remake/tools/deco_survey.py ROM OUT --todo --max 8` (groups that still had no light shape): 34 groups in tileset 2; 24 pieces built in 23 rooms (616 617 618 619 622 668 669 673 674 675 677 683 684 685 686 687 688 689 690 698 704 717 718 722 723),
  from the parts of `remake/lib/cabinet.py`: chests of drawers, bookcases, glass cabinets, nightstands, low open wooden boxes (`tray`), brick hearths with a cloth top, wall shelves with plate stacks, clay jars, vases / flasks / bottles / frames / boxes on top, the crystal ball of 685 / 686.
- Second pass the same day (user marks: crystal ball, 689 jar + shelf, all jars): every piece checked ZOOMED against the drawn plane A outline (`~/Project-Friday-Test/lktest/innen/merc/sil.py`, model silhouette yellow); corrected 675 / 677 chests (36) + bookcases (33), 683 bookcase (45), 689 cabinet + shelf (33.5 / 47), 722 chest (33) + shelf (x from 288), items on top. CLAY JARS: one tile drawing; profile fitted on the fully visible jar of 683 (`JAR_T` / `JARFIT` in case.py: h 24.12, radii 5.43 8.10 8.79 5.36 5.74 5.15), the others placed by the template-match shift (677 / 683 / 689 / 717 x 2 / 722). Crystal ball 685 after four user rounds: low block with a groove per face, plate with rim, flat holder ring, ball r 5.0 = only the blue pixels.
- LIGHT VARIANT rules found in the light test (user marks): glass rows = 'glassflat' (flush front, no stripes); hearth openings as wide / high as the DRAWN fire and only 1 deep (else the fire stays dark: the flame light sits in front of the face its view ray hits). The same fix went into `remake/recipes/house_hearth/house_hearth.py` (691 / 692 / 713 / 714: opening u 0.3..0.79, h 0.75, depth 1; it had a dark fire + 96 edge px).
- Measured on rom_picture: the drawn TOP CORNERS of each piece (leftmost top point = (x0, y1, z), rightmost = (x1, y0, z): U = x - y + 1184, V = (x + y) / 2 - z) give depth and height; many tops are lower than the collision box (it includes the things on top: 618 chest 32 under a 48 box, 673 cabinet + bookcase 36). Checked with the exact game projection (z buffer, depth x + y + z) blended over the picture (`~/Project-Friday-Test/lktest/innen/merc/proj.py`), sheets `~/Project-Friday-Test/Mockups/moebel_mercator_1.png` / `_2.png`.
- Also: the 673 / 674 2 x 2 table (furniture_ops FORCE_TABLES: its back corner cell draws another block) and the 698 bed (six BLOCKED cells; beds() now takes blocked beds too, picture match 0.99).
- NOT built (yet): the counters of 615 / 678 / 704 (the collision box is the drawing; the shop counter recipe stays remake only, see 'Shop counter'), the store room 667 (one 7 x 5 group: wall shelf, bookcase, long chest, box, jars), the armour heaps of 698 / 717 and the cello of 683 (organic). The 668 / 669 white square (first listed as a bed) = a table under a cloth: `merc_cloth_668`.

## Log house bed of tileset 8  (`remake/recipes/case/case.py` BOATBED / BOATBED_Y, specs `boat_bed_*` -> `landstalker/data/proxies/boat_bed_<room>.obj`; 2026-11-25)
- Reference: room 491 / 735 (boatman's house after Destel, same map), cells 15..17 x 14..15, collision 16 walkable, head at the west, back at the north wall; rom_picture 491 window U 1060 V 140.
- Shape (all read on the drawing, user OK on the clay sheet ~/Project-Friday-Test/Mockups/bett_491_blatt.png): a plank box exactly on the 3 x 2 collision box; lower plank 0..8 + upper course 8..16 (the drawn seam), upper course = 1 thick front / foot boards to the top, bare head boards; the mattress lies FLUSH in the frame (drawn without thickness; head edge 17.5 from the head end), its rounded rim = the drawn dark outline; one flat pillow 8 x 12 x 2.5 (drawn outline U 1180..1199, V 221..233). The drawing itself is a plank box: no more form to read.
- Copies (cell top blocks $05E..$062, overlay checked each): 517 cells 25..27 x 17..18, 732 two beds (14..16 x 14..15 and 14..16 x 17..18), 728 MIRRORED (BOATBED_Y, head at the north wall, cells 14..15 x 14..16).
- GPU lightedges --spots 491 / 735 / 517 / 732 / 728: 0 before and after; changes only on the beds.

## Boatman's house furniture 491 / 735  (`remake/recipes/case/case.py` specs `boat_books_491`, `boat_cab_491`, `boat_table_491`, `boat_sack_491` -> `landstalker/data/proxies/boat_<name>_{491,735}.obj`; tileset 8, 2026-11-25)
- Room 491 ROUTE_AFTER_DESTEL_BOATMAN_HOUSE = 735 (same map data, other palette). One piece at a time, user OK on each clay / overlay sheet in ~/Project-Friday-Test/Mockups (`regale_` / `schrank_` / `tisch_` / `sack_491_blatt.png`); the bed: see 'Log house bed of tileset 8'.
- West bookcase row (cells 14 x 14..20, 48): three open bookcases (cabinet.py, fronts +x, plinth + 3 book shelves) y 224..256 / 256..304 / 304..336; on top: TS8JAR (furniture.JAR, the tileset 8 clay jar, at its usual cell offset +3 / +3) x 2 on the front case, a grey idol (body + round head, simplified), two lying book stacks, a bottle and a round flask; the plank side panel stays drawn.
- Small bookcase right of the bed (cells 18..19 x 14, 32): open to the south, 2 book shelves; book stack, vase (body 10 + flower 8, smaller than the Mercator VASE) and a small ball at the front corner.
- Table (cells 17..19 x 19..20, 16): furniture.mercator_table_mesh with rc 0.6 (pointed corners), top 2.5, legs r 1.3 1.5 in; candle on a holder, open book (raised pages), lantern, cup, green bottle (the 2 px orange item left out). Painted table shadow off: unpaint op + unpaint_tiles '8' ($26F / $278 / $279 / $288 / $289 -> carpet $0CA; furniture_ops UNPAINT_TILES).
- Sack (cell 20 x 14, 16): lathe belly r 8.8 (drawn 25 px wide) flattened on the floor, 1.3 into the void wall; neck + mouth = case.TILTLATHE (a lathe with a leaning axis) tied at the bottom and flaring to the open mouth on the upper west side; fitted by IoU on the drawn sack pixels (~/Project-Friday-Test/remake_tools/lighttest/fitsack.py: belly alone 0.67 -> 0.79) after the user marked the missing mouth.
- GPU lightedges --spots 491 / 735 per piece before / after: 0 except the unpainted table carpet (method artifact, LESSONS 2026-11-25; checked by eye: soft shadow, no edge).

## Rock mountain of room 503  (`remake/recipes/proxy_rock_503.py` -> `landstalker/data/proxies/rock_503_{a,b,c,d}.obj`; room 503, 2026-11-27, barrier wall pass)
- Reference: the big rock massif over VOID (#0) and invisible BARRIER ($4F) cells; walkable: the 176 walkway (row 31 x 23..32, x 30..32 y 23..33), the 128 / 80 ledges (x 22..23), floor 16. Before: the void painter made the rock a water floor at 8 (a hole: no sword glow on the wall). Per-cell heights were rejected (daylight bands, LESSONS 2026-11-27).
- Footprint = the barrier lines: +x faces x 352 (y 576..752), x 368 (y 496..576), x 480 (y 432..496), x 496 (y 416..432); +y faces y 496 (x 368..480), steps y 576 / 432. Ends on the screen columns U 784 / 1264 (edge-on).
- Top = the drawn outline extruded along the view ray (1, 1, 1): z = (x + y) / 2 - Vsil(U). Outline measured per picture column: V = 623 - U / 2 (U 812..1055, = the x 368 face at z 336 / the x 352 face at z 320, straight to the pixel) and V = U / 2 - 432 (U 1056..1220, the y 496 face at z 336), rocky shoulders U 784..812 / 1220..1264 as pixel outline (upper envelope). The top is never seen (edge-on); the back looks like a ramp in the clay sheet on purpose (light variant = as drawn).
- FOUR pieces with their own op rectangles (a 12..21 x 12..46, b 22 x 12..35, c 23..29 x 12..30, d 30 x 12..26): an outdoor surface model owns its whole rectangle (LK_GLROOM clean-up flattens uncovered raised cells to the ground; with one big rectangle the 176 walkway and the 128 ledge vanished for the light = the hard glow edge the user marked).
- GPU checks (11 spots, old / new, lightedges + 2x zoom): daylight unchanged (vertical ratio runs 19 / 19, lightedges 0 / 0); sword: the wall lights softly everywhere; remaining marks are pre-existing (the lit rectangle on the small 80 ledge front by the cave door) or physical (the +y step face at y 576 behind the 128 ledge faces away from Nigel). User OK 2026-11-27 ('ok').

## Rock wall / plateau of room 465  (`remake/recipes/proxy_rock_465.py` -> `landstalker/data/proxies/rock_465_{a,b,b2,c,c2,d,d2,e,g}.obj`; room 465, 2026-11-27, barrier wall pass, built by `remake/lib/rockwall.py`)
- Reference: the cliff path above the river: 128 walkway x 22..29 rows 43..62, 176 ledge x 26..27 rows 35..42 (lamp post), 96 / 112 path x 28..35 rows 20..36; the cliff behind them over VOID / BARRIER cells.
- Footprint = barrier lines (+x faces x 544 / 480 / 416 / 400 / 384 / 368 / 352 by rows), 9 rectangles of rock cells only (160 bushes, 144 / 176 steps, walkway outside). Cells 23..24 x 61..62 (void beside the exit, no barrier) left out.
- Top = outline seen edge-on, capped by the PLATEAU at 240 for U >= 736: measured on three drawn edges (the y 448 face Y - Z = 208, the x 544 face, the grass edge on the y 560 face behind the 176 ledge) = the barrier height 15 x 16. Left peak (U 560..735) V = 640 - U / 2 = x 352 face at z 304; right end shoulder down to ~100 at U 1406.
- GPU checks (11 spots, old / new): daylight unchanged (vertical ratio runs 47 / 38); sword: the wall lights softly, the hard lit box by the lamp post is gone (spot 24,46). Left: the 176 ledge front face by the lamp is lit with hard sides (pre-existing), a thin vertical line at the notch behind the ledge (cells 25,38..39 = collision corner), the cliff BELOW the walkway down to the river is still the old water floor (own class). User OK 2026-11-27 ('ja').
