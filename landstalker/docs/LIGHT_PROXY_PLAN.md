# Light proxies: invisible 3D shapes for lighting (plan, 2026-11-03)

Status: STEP 1 BUILT 2026-11-03 (user check open, mock-ups `~/Mockups/kulissen1.html`); plan agreed by the user ('klingt sinnvoll'). Rests on `dev` f8e8713 (LK_LIGHTS v7).

## Why
Lighting v5..v7 guesses the 3D shape of every object from the painted picture (layer A) plus the game's
collision height map. Every fix moved the error to the next edge (user recordings 2026-11-03 2114 / 2149 / 2201:
light gaps between houses and shadows, a pine shadow from nowhere, Nigel's shadow climbing the river as if it were
a wall, a raised flower bed darkening Nigel). The root cause is the missing geometry, not a parameter.

HD-2D games (Octopath Traveler, Unreal Engine 4) have real 3D geometry with pixel textures and sprite billboards;
light and shadows come from that geometry, nothing is guessed. We keep the original picture and add only an
INVISIBLE light geometry ("proxies"): it casts and receives light, it is never drawn. The full 3D look belongs to
the remake (`remake/`).

## Model
Per room a list of proxies in world units (same space as the height map, 16 units per cell):
- `box` x0 y0 x1 y1 z0 z1 (walls, low objects)
- `hip` x0 y0 x1 y1 z0 eave ridge (house: walls to `eave`, hip roof to `ridge`; `gable` with an axis later if needed)
- `cone` cx cy r z0 z1 (pine), `blob` cx cy r z0 z1 (round tree / bush)
- `flat` cells (drawn things that cast nothing: flower beds, signs on the ground)
- `water` cells + surface height (river / sea: a floor, never a wall)
Cells without a proxy use the game's height map as today.

## How it is built
1. Automatic proposal per room at room entry (code, from what v7 already measures): buildings -> `hip` with eave /
   ridge from the drawn picture; small objects -> `cone` / `blob` from the drawn width / height; cliffs -> game heights;
   void / water tiles -> `water`.
2. Corrections as DATA: `landstalker/data/light_proxies.json` (our own data, room ids + world coordinates only,
   nothing from the ROM): per room `remove` / `replace` / `add` proxies, `flat` / `water` cells. Loaded at start like
   the language files. Tool `tools/lightproxy.py ROOM` prints the automatic proposal as a starting point.
3. The proxies are rasterised once per room into the fine field the sun already uses (`lk_lt_fh` / `lk_lt_fo`, 4 units,
   ~1 ms); view ray, sun march, early exits, prefetch stay as they are. Performance equal or better than v7 (the
   per column picture analysis goes away).

## Steps (one at a time, user check after each)
1. Proxy shapes + rasteriser + automatic proposal for buildings / small objects; debug view `LANDSTALKER_LIGHTING_DBG=7`
   (proxies drawn as colours over the picture). Mercator 632 / 635 first, compared with v7 on the user's recordings.
2. Correction file + loader + `tools/lightproxy.py`; first entries from the 2201 markers (river = water, flower bed =
   flat, pines, house gap).
3. Remove the v7 guessing code (hull, mirror per part, part splitting) once the proxies cover the test rooms; other
   rooms keep the game heights until they get proxies.
4. Workflow: the user swings the sword where light looks wrong (pad bit $40 in `rec_*.txt`), we add a correction.
5. Later on the same proxies: day / night, light from windows, Nigel's lantern outdoors.

Rules: Lighting Off stays byte-identical; indoor flame rooms only change when they get proxies; nothing ROM-derived in git.

## Step 1 result (2026-11-03, `patch_lights.py`, default on, `LANDSTALKER_LIGHTPROXY=0` = v7 guessed field)
- Proposal per building PART (equal height piece, >= 16 high sub columns, both sides >= 24 units): `hip` over the part's whole
  footprint (the drawn walls stand on its edge; the high sub column box was too small, walls came out dark), eave = median of the measured
  border heights, ridge = max. Small objects: `cone` from the card (drawn foot, half width / 1.41, height capped at 48 + 24 per cell: a pine
  beside a house measured 174 because the run went on into the wall). Then the fine field is cleared for those objects and redrawn from the shapes.
- `LANDSTALKER_LIGHTING_DBG=5` prints 'proxy: room R #n hip x .. y .. z0 eave ridge (object part)' / 'cone at x,y r z..'; `=7` colours each proxy over the picture.
- Mercator (rec_20261103_2201 frames 1377 / 1719): house shadows clean to the wall base (no light gap, no dark walls), pines no stray shapes.
  Still wrong (step 2 data): the long flower beds of room 635 (objects 4 x 14 cells, box 32) get a hip with ridge ~90 from the drawn
  flowers (they darken Nigel); the river is void in the height map (Nigel's shadow on the far bank as a wall).
- Room setup 1.6 / 3.8 ms (635 / 632); Lighting Off and indoor flame rooms byte-identical to the previous build.

## Step 1b (2026-11-03, user recording rec_20261103_2230, markers 747 / 1131 / 1380 / 2144) - intermediate state before the clean-up
- Pixels NOT drawn in layer A are ground: the view ray of such a pixel passes the proxies (table `lk_lt_vg`); ground beside a trunk is no part of the tree (pine shadow starts at the trunk).
- Small objects: LATHE solid (type 3) from the sprite's drawn half width per row (/ 1.41 = world radius), like Blender's screw modifier (user asked about a Blender pine:
  not needed, the lathe follows each sprite); rows hidden by a wall behind take the whole shape of the most alike free standing tree of the room; drawn < 32 high (tulips) = no shape.
  The sun march tests the real profile (branch tiers), the height field is only for the view ray.
- A face turned away from the sun on a LOW box without a proxy (<= 48, ring / flower box) is as lit as the box top just behind its edge (the tulip box stayed bright in a house's shadow);
  first version without the height limit darkened a tall wall without a proxy (frame 732) -> limited.
- Not solved: ponds / river (void), flower beds (hip from drawn flowers) -> correction data.

## Decision 2026-11-03 (user: 'brauchts die Karten dann ueberhaupt noch?' -> 'ja das macht Sinn')
CLEAN-UP next: remove the v6 cards (cliffs / terraces take the game's height map), remove the guessing rules (part splitting, mirror hull as geometry,
special cases); keep: proposal at room entry, ONE pixel rule (layer A on proxies, layer B on the ground), turned-away faces keep their painting, correction file.
User asked about rendering the map in 3D like Octopath: the existing 3D room prototype (2026-10-24, projective texturing) can take the same proxies later;
from the original camera the result equals ours (the picture is the texture), the gain is GPU light / shadow maps and a moving camera. Proxies are the base for both.

## Clean-up done (2026-11-03, after 'Step 1b')
Removed: the v6 per cell cards (cliffs / terraces = game height map, they shade their own lower parts now), the v6 raising of `lk_lt_top`,
`lk_lt_cardsun` + its horizon map, the painted-crown rule, the switch `LANDSTALKER_LIGHTPROXY` (proxies always). The cards survive only as the
measurement of small objects (foot, width, height -> lathe). -71 lines. Results: tree shadows smooth and from the trunk (the game's tree box cast a block
before), houses unchanged; cliff room 603 (rec_20261103_1803 frame 7500) shows thin dark lines along terrain edges (to look at with the correction pass).
Lighting Off and indoor rooms byte-identical. NEXT: step 2 = correction file + mesh proxies from Blender for unique objects (user 2026-11-03: 'und der
Blender-Weg fuer genauere Formen?' -> yes for one-offs like the church / castle tower, built by script on the Deck, referenced per room in the file).

## Recording rec_20261103_2256 (markers 397 church, 1724, 2888, 3239, 3812 in Mercator 632) - automatic rules instead of data
- WATER: a void cell of the height map whose picture is PAINTED (river, pond) is a floor 8 below its lowest neighbour (flood fill, our copy only);
  unpainted void (the black outside) stays void. Room 632: 796 cells. Nigel's shadow lies flat on the river now (climbed the bank 'as if it were a wall'),
  the triangle in the pond is gone, the stone platform shades the water. `DBG=5` prints 'water: room R, n void cells painted -> floor'.
- A small object drawn < 48 high whose footprint is a ROW (1 x 2, 1 x 3 cells: tulip rows) is flat (its lathe was a round blob beside the pond).
- So the correction file is still needed only for real one-offs (flower beds of room 635 with a hip, the church as a Blender mesh).

## Sun along the grid + church stripe (2026-11-03, user: 'Schatten im gleichen Winkel wie die isometrische Ansicht', 'nur der dunkle Streifen vor der Kirche')
- Sun azimuth 90 by default (was 110): exactly from the lower left = world +y, shadows run along the isometric grid up-right; +y faces get the full sun,
  +x faces are edge-on (they keep their painting). Elevation 55 (user choice of 40 / 55 / 65 on `~/Mockups/sonnenhoehe.html`).
- Hip proxies are rasterised only on the part's OWN cells (the part box is a rectangle, the part may not be), without single cells sticking out of
  the part (<= 1 neighbour of the same part: steps / bumps of the collision; room 632 object 8 had two at column 24 = a phantom wall).
- WATER cells (our fill) are no part of any object: the painted border void of room 632 had merged the church with it into one terrain object
  (class 3, no house shape any more). Back to object 4 (94 cells, 5 heights, class 2).
- What stays dark in front of the church now is the shadow of the church's front wing on the flower strip (sun from the lower left) - for the user to judge.

## Step 2 built: the correction file (2026-11-03, user: 'Mach die Korrekturdatei')
- `landstalker/data/light_proxies.json` (our own data: room ids, map cells, heights; nothing from the ROM). Read by `tools/patch_lights.py`
  at BUILD time and compiled in as a C table (`lk_lt_corr`), like the Friday hints; `LANDSTALKER_LIGHTPROXY_JSON=<file>` = a test copy at build time.
  Shipped: `packaging/make_appimage.py` and `make_windows_zip.py` copy `data/*.json` (the game is built on the player's machine).
- ops (cells inclusive, heights in units): `flat [x0,y0,x1,y1]` (no shape in these cells, shapes centred there dropped; the game's box stays),
  `water [x0,y0,x1,y1,h]` (water floor; applied after the automatic water fill), `remove [x0,y0,x1,y1]` (drop shapes centred there),
  `hip [x0,y0,x1,y1,z0,eave,ridge]` (own building shape, object id 1000+). `DBG=5` prints 'correction: room R drops proxy #n / adds hip #n'.
- First entries: room 635 the two long flower beds (cells 43..46 x 26..39 and 43..46 x 47..60) flat: Nigel no longer darkened in the bed
  (rec_20261103_2201 frame 2790), the big triangle at the bed's end gone; the bed's raised edge keeps its small shadow.
- How to add an entry: find the cells with `LANDSTALKER_LIGHTING_PROBE` (position / 16) or the `DBG=5` proxy list, add a line with a `why`, rebuild (13 s).
- Open: `mesh` op for Blender shapes of one-offs (church), the cliff edge lines of room 603.

## Blender shapes for one-offs (2026-11-04, user: 'blender')
- Recipe `remake/recipes/proxy_church_632.py` (run: `python3 remake/tools/build_asset.py proxy_church_632`, Blender Flatpak headless, ~5 s): parts in GAME
  coordinates (hall 240..376 x 800..928 eave 64 hip top 109; yellow house 240..326 x 928..992 eave 64 top 83; entrance gable 340..400 x 833..895 eave 64 ridge 94 along x; refined 2026-11-04, see below),
  measured on the original picture of room 632 (roof flat tops and wall corners, projection U = x - y + 1184, V = (x + y) / 2 - z; overlay: `remake/tools/proxy_overlay.py`).
  Writes `landstalker/data/proxies/church_632.obj` (OUR geometry, committed) + a game-camera preview (`~/.landstalker_remake/assets/proxy_church_632/preview.png`, local).
- Correction op `mesh [x0,y0,x1,y1] + "file"`: the rectangle's automatic shapes go, `patch_lights.py` rasterises the OBJ at BUILD time (top height per 4 unit sub
  column, max over all faces) into a C table (`lk_lt_meshN`); at room entry it is stamped as proxy type 4 (object id 1000+). Room 632: church cells 15..24 x 50..61 (1512 sub columns, 1536 since the refined entrance);
  the tulip garden behind it (same game object, cells 15..23 x 46..49) flat.
- Shared code since 2026-11-04: `remake/lib/proxy.py` (`part_mesh` box / hip / 'hip:N' steep cushion / gable / flat, `build()` writes the OBJ + preview); the church
  recipe uses it (OBJ byte-identical). Measuring: `remake/tools/rom_picture.py ROM ROOM U0 V0 W H DIR`, then `remake/tools/proxy_overlay.py DIR OBJ OUT.png SCALE GROUND_Z`
  with the recipe's OBJ or a hand-made grid OBJ (rung planes every 8 units at a wall line read heights; a 64 unit ground grid reads x / y).
- ROOM 31 (Mercator castle facade, 2026-11-04, user: 'weiter mit den naechsten Formen'): the height map holds the castle only as BLOCKED cells of height 0 (rows 14..28),
  so the automatic proposal made NO facade (its wall pixels were read as ground and the right facade got dark blotches = shadows of things in front, Lighting On) and
  merged stairs + tower + planters into one hip up to 204 (#0..#2 at cells 36..47 x 29..34). `remake/recipes/proxy_castle_31.py` -> `data/proxies/castle_31.obj`, op `mesh`
  cells 21..62 x 14..34 (drops #0..#2, keeps the four planters of rows 40..43 and the statue): facade x 352..992 front y 464 cornice 176 roll to 192 (deep box back to y 224),
  centre tower x 624..720 y 448..496 cornice 228 cushion top 252 (door niche = cells (41, 30), (42, 30); row 31 = free landing), stairs from the height map, the two
  pine planters (cells 36..38 / 45..47, rows 29..32) as hips 32 -> 64. Check (warp test, `LANDSTALKER_WARP=31:42.08,31.08,0030` at 2100 from rec_20261103_1803 frame 2040):
  blotches gone, only the figure shadows remain; Lighting Off byte-identical; church frame unchanged. Sun from +y = the facade's shadow falls behind the castle (invisible).
- ROOM 638 (Mercator fountain court, 2026-11-04, user: 'weiter damit'): the height map has the city wall only as blocked height 0 (column 17) and the round towers
  as single blocked height 9 cells (column 18, rows 26..29 / 38..41 / 50..53); the automatic proposal made a 32 wide strip x 288..320 (= the WALKABLE bank, cells 18..19)
  with a hip up to 247 (Nigel on the bank stood in its shadow) and gave the pines at the north wall (cells 25..27 x 19..20) a hip up to 222. `remake/recipes/proxy_wall_638.py`
  -> `data/proxies/wall_638.obj`: west wall x 272..288 (one cell, face 288) y 272..912 on ground 48, its drawn top FALLS towards the back (forced perspective of the art,
  scanned per picture column: 245 / 236 / 234 / 221 / 212 / 204), three half towers radius 32 on the face (centres y 832 / 640 / 448, tops 257 / 241 / 220, new
  `proxy.cylinder`), north wall y 272..288 x 272..496 top 196, pines hip 48 -> 96. Corrections: `mesh` cells 14..20 x 12..59 (drops the strip + a tower stub) and
  `remove` 24..28 x 18..21 (the pine hip). Check (warp `638:19.08,46.08,0030` / `638:24.08,40.08,0030`): the tower shadow falls up-right along the bank (sun from +y),
  Nigel on the bank is lit except in tower 1's shadow; Lighting Off byte-identical. The two stone pillars in the pool (cells (23, 22), (23, 24), height 5) were right already.
- ROOM 636 (Mercator rocky arch over the river, 2026-11-04, user: 'mach direkt weiter'): the same city wall (height map: column 14 height 3, towers height 12)
  had no wall shape and the towers became small cones (z to 62 / 76, lathes #13 / #15 / #18 / #19); the terraced grass mound bridging the river (cells 18..25 x 38..42,
  walkable heights 2..5) became hips, one up to 142 on a WALKABLE terrace (cells 24..25 x 41..42) = a dark blob on the river next to it.
  `remake/recipes/proxy_arch_636.py` -> `data/proxies/arch_636.obj`: wall x 224..240 y 192..960 top 179 (constant here, merlons 175 / 183), half towers radius 32
  (centres y 446 / 687 / 920, tops 159 / 184 / 188: drawn BELOW the wall top), the mound's terraces copied cell by cell from the height map (their top faces lie exactly
  on the drawn terraces in the overlay), two pine clumps hips 48 -> 72. Corrections: `mesh` 12..16 x 10..62, `remove` 18..25 x 38..40 and 24..25 x 41..42 (the automatic
  pines at cells (23, 41) / (23, 42) / (20, 44) stay). Check: warp `636:24.08,44.08,0010` (NOT onto the mound: `636:21.08,40.08` triggers a transition to room 669);
  the blob on the river is gone; Lighting Off byte-identical.
- ROOM 637 (Mercator north gate, 2026-11-04, user: 'mach direkt weiter'): gate wall, gatehouse, two round towers and the high wall behind were all 'flat' (height map:
  column 15 heights 6 / 8 only; the gate wall stands behind the WALKABLE column 15 of rows 30..41). `remake/recipes/proxy_gate_637.py` -> `data/proxies/gate_637.obj`:
  gate wall face x 240 y 480..672 top 128, gatehouse y 560..608 to 160, left half tower (x 240, centre y 702, top 199), big half tower (face x 256, centre y 476, top 222),
  high wall face x 256 y 288..448 top 232 / 236 / 200 / 192, pine row on cells 16..20 of row 21 (hip 32 -> 96). Correction `mesh` 13..15 x 12..46 (drops nothing; the
  pine L of object 2 keeps its automatic hip, ridge 109 fits the drawn tops). Check: warp `637:19.08,34.08,0020`: the left tower's shadow reaches the path in front of the
  door, the big tower's falls up-right; Lighting Off byte-identical.
- All Mercator outdoor one-offs of the 2026-11-04 survey are done (632 church, 31 castle, 638, 636, 637). Next: other towns' walls / towers on request, the cliff edge lines of room 603.
- SURVEY TOOL `landstalker/tools/proxysurvey.py` (2026-11-04): `--run OUTDIR` warps headless through every outdoor room (DBG=5, batches of 16 warps, replay prefix of rec_20261103_1803, the user's save copied) and ranks the automatic proxies: WALK (hip / lathe over walkable cells), TENT (wall read as roof), FLAT (tall object without shape), WALL0 (blocked height 0 runs). `--log LOG` re-scores a saved log. First full run: top = 488 ROUTE_AFTER_DESTEL_2, 565, 362 KN_LABYRINTH_EXTERIOR, 529, 425, 454, 515, 424, 183 RYUMA_RAFT_PIER; most top hits are FOREST canopy blocks on routes (hips up to ~240 over walkable cells), i.e. a repeating pattern, not town one-offs.

## Bush blocks and trees (2026-11-04, user: 'der Schatten soll nach dem Baum oder Busch aussehen und nicht wie ein Block'; 'das sind Busch-Sprites, keine Baeume, die einstufigen')
- The survey's top rooms are BUSH blocks on the routes (one step high; the user: bush sprites, not trees): a regular grid of painted round bushes, ONE per map cell, short stems visible at the front edge. In the
  height map the block is a WALKABLE slab one step (16) above the ground (room 488: cells at height 9 around ground 8); the automatic proposal read the tall drawn
  area as a building (hips up to 238 over the slab: a big dark block over the path and Nigel).
- New correction ops `bushes` / `pines` [x0,y0,x1,y1] (+ optional `h`, `r`, `base`; `patch_lights.py` proxy type 5): every RAISED cell of the rectangle (game height
  >= base + 8) gets one shape: `bushes` = a sphere radius r (default 6) whose top is the cell's game height (or base + h) + a stem (radius 1.5),
  `pines` = a cone from base + 4 to base + h, radius r (default 7); radius at most 8 (stays inside its cell). In those cells the sun march uses the BASE
  (most common game height on the ring around the rectangle, ties -> the lower; or `base`), not the raised slab: light passes between the stems, the shadow
  outline is the row of bushes. The view ray (where a pixel sits) is unchanged; bush block pixels belong to the bushes' object (no self shadow).
  Measured on room 488 (`remake/tools/proxy_overlay.py` with a test OBJ of silhouette circles): r 6 with the top on the slab matches the painted bushes;
  small pines: cones 30 high.
- Bush block shadows are SHORT (16 high -> ~11 units at sun elevation 55) and fall to -y = behind the bushes as seen by the camera, so a bush block casts almost no
  visible shadow; the gain is that the wrong block shadows are gone. Tall single trees (the big tree in front of the bushes of room 488: `remake/recipes/proxy_tree_488.py`,
  new `proxy.lathe` = stacked frustums from a profile [(z, r), ...] measured on the silhouette: a circle of radius r at height z is widest at
  V = (cx + cy) / 2 - z with half width r * sqrt(2)) use the `mesh` op.
- Room 488 done: bushes 44..58 x 28..33, 26..37 x 33..36, 26..31 x 37..44; pines 32..33 x 37..44, 34..37 x 37..38 (h 30); remove 32,39 (hip #2 up to 218);
  mesh tree_488 (cells 33..38 x 38..43, box up to 271 replaced, drawn tip 212). Check: warp `488:48.08,26.08,0080` (path: block shadow gone),
  `488:39.08,40.08,0080` (big tree); Lighting Off byte-identical; Mercator 632 / 637 frames identical to the previous build. USER CHECK OPEN.
- SUN TEST AID (2026-11-04, user: 'mit dem rechten Stick den Sonnenstand aendern'): pad L5 (or R5) held + right stick (x: azimuth 2 deg / frame, y: elevation 1 deg / frame, 5..89);
  `lk_lt_sun_nudge` -> `lk_lt_step` sets the direction (`lk_lt_sunset`), drops the computed blocks (`lk_lt_free`) and redoes `lk_lt_horizon`, at most every 4th frame;
  headless `LANDSTALKER_SUN_AT="2300:180:30,..."` (frame:azimuth:elevation). The same path is the base of a day / night cycle (then spread the recompute over frames).
- PLAN (2026-11-04, on dev b0da39d; user: 'das macht deutlich mehr Sinn und wuerde dann auch greifen, sollten wir mal Raeume modden'): find bush blocks / pines
  AUTOMATICALLY by their GRAPHICS BLOCKS (the same tiles / blocks in every room of a tileset), not per room data and not by guessing from pixels: learn the bush
  and pine block ids once (room 488), at room entry mark the raised cells drawn with them as `bushes` / `pines`; `data/light_proxies.json` only for exceptions
  (big single trees). Check a few rooms against the original before trusting it. Works for modded rooms too.

## Object catalogue (2026-11-04, user: 'nicht nur eine Bush Detection, generell etwas fuer wiederkehrende Objekte' / 'wuerde dann auch greifen, sollten wir mal Raeume modden')
- `landstalker/data/object_blocks.json` = classes (bush: sphere r 6; pine: cone r 7, h 30) + per TILESET the layer A block ids that draw them. Rooms are built from
  16 x 16 blocks of the tileset's blockset, so an object is the same block id in every room of that tileset (and in modded rooms).
- Runtime (`patch_lights.py`, at room entry after the automatic proposal, before the per room corrections): the block that draws the TOP of cell (x, y) at height h is
  layer A block (x - h, y - h) (`$FF7C02`); of all cells on that view diagonal the highest one owns it. Catalogue hit -> the cell's class (SMALL free standing objects keep
  their sprite lathe). Components of equal class (4-connected): base = most common game height on the ring (ties: lower); bush cells must be raised (>= base + 8: the side
  faces / back edge of a bush block also draw low cells in front / behind), bush top = max(cell height, base + 16), pine top = max(cell height, base + h). Automatic hips
  whose part is >= half catalogue cells are dropped; other proxies skip catalogue cells. Per cell tables `lk_lt_tk / tr / tb / tt / to` (the data ops `bushes` / `pines`
  write the same tables and override). DBG=5: 'catalogue: room R tileset T: n bush cells, m pine cells, k groups' + dropped hips.
- Tool `landstalker/tools/blockcat.py`: `stats [TS]` (top blocks of cell tops per tileset), `sheet TS OUT.png [--ids ..]` (each block alone 4 x + in its picture with a red
  frame; local, ROM-derived), `cells ROOM` (classification preview, without the runtime's raised rule).
- Tileset 17 labelled from three sheets of its 48 most used top blocks (bush 11 ids, pine 15 ids; $064 = back edge overhang, not a bush; $0BD = rope fence, later class).
  Room 488: 178 bush + 50 pine cells, hips #0..#2 dropped; the hand entries `bushes` / `pines` were removed (picture within 67..219 px of the hand version); the big
  tree mesh + remove stay. Before / after (headless, rec_20261103_1803 warps): 490, 525, 529, 362 lose the dark patches over Nigel / the path (`~/Mockups/katalog_raum*_vorher_nachher.png`).
  Lighting Off and Mercator 632 / 637 byte-identical.
- NEXT: label tilesets 0, 7, 12, 13, 14 the same way (sheets), more classes on request (fences, posts, single trees).- ALL SIX outdoor tilesets labelled (2026-11-04 night, `blockcat.py sheet TS OUT --top 120 --green 0.5`: only blocks whose own pixels are mostly green; the filter
  keeps 24 of the 26 hand labels of tileset 17): tileset 0 (Mercator) flowerbed 12 + pine 7, 7 (Massan) pine 17 + bush 2, 12 (Gumi forests) pine 52 + bush 22,
  13 pine 47 + bush 4, 14 pine 25 + bush 13, 17 bush 11 + pine 15 (227 blocks). New class `flowerbed` = shape `flat` (kind 3: no shape, no automatic shape over it,
  like the per room op `flat`). Pines: top = max(cell height, base + h, ridge of the automatic hip that covered the cell) (the proposal measures the drawn
  height; room 637's big pines reach ~109, the default h 30 was measured on small pines).
  Before / after (headless): 425, 454, 630, 447 lose the dark patches over Nigel / the path (`~/Mockups/katalog_raum*_vorher_nachher.png`), Massan 601 nearly
  unchanged (single pines keep their sprite lathe); Lighting Off byte-identical; church 632 frame byte-identical; north gate 637: 328 px differ (shade on the
  paving behind the big tower).
- NEXT: more classes on request (rope fences $0BD in tileset 17, posts, single big trees), user check in play.
- WALKABLE RULE (2026-11-04 night, user: 'continue with the shapes'): the rerun survey (`proxysurvey.py --run`, now minus the hips the catalogue drops) showed the
  rest of the WALK cases are walkable GROUND read as an object (forest clearing 362 hip up to 80 over 108 walkable cells, Ryuma raft pier 183 terraces up to 102,
  565 / 529 / 515 ...). Rule in `patch_lights.py`: an automatic hip (type 1 with a part) stamps no column over a walkable cell (`lk_lt_walk`: height map word not
  `$4x` / `$2x` blocked) whose game height is <= its base z0 (Nigel would stand inside it). Houses (blocked cells) unchanged: Mercator 630 / 632 / 637 frames and
  Lighting Off byte-identical; 183 / 362 lose the wrong dark patches (`~/Mockups/begehbar_raum*_vorher_nachher.png`). The survey no longer scores hip WALK
  (the game leaves those columns out); top score 522 -> 24 (left: lathes on walkable cells, a few TENT, WALL0).
- NEXT: the remaining lathes on walkable cells (447, 570, 474, 454), more catalogue classes on request (rope fences $0BD in tileset 17, posts, single big trees), user check in play.
- (superseded by the plan above if it works) Next: the other bush block rooms of the survey (565, 362, 529, 425, 454, 515, 424, 183, ...): cells from the height map (raised walkable slab) + a look at the picture.
- Packaging copies `data/**/*.json` and `*.obj` (AppImage / Windows zip). Lighting Off / indoor byte-identical; only frame 2100 of rec_20261103_1803 changed (church).
- Refined 2026-11-04 (user: 'verfeinere die 3d Form der Kirche'): the entrance gable was 13 units too high (ridge 107 -> 94, read from the gable apex U 720 / V 538 and the
  eave corners U 688 / V 583, U 750 / V 548 of the picture) and too short at the front (x 392 -> 400 = over the column cells x 24 of the height map). It now starts at x 340 INSIDE the
  hall: its south slope meets the hall's east hip slope in a 45 deg valley, which is the vertical roof line of the picture (the 'cross gable'). Check: overlay of the OBJ edges
  on `remake/tools/rom_picture.py ROM 632 400 360 400 340` with `remake/tools/proxy_overlay.py` (apex, eave corners and valley on the picture's lines). Height map rows 50..61 confirm the footprints (hall 4 = 64,
  house x 15..19, door cell (19, 60) height 1). Result rec_20261103_1803 frame 2100 (lightshots): 1596 pixels changed, only the strip in front of the
  church's south wall and next to the door (a little brighter = shorter gable shadow); Lighting Off byte-identical (0 pixels).

## NEXT BIG STEP (planned 2026-11-08, user: 'vermerk das mal fuers naechste Mal' + 'sollten wir nicht generell so umbauen, dass z. B. die Luft unterm Segel geht?')
Two parts, one rebuild, in a fresh session (delicate: CPU + GLSL lockstep, GL5 compare, full outdoor AND indoor lightedges runs before / after).
1. **Fine field + shapes INDOORS.** Today the 4 unit field (`lk_lt_fh` / `lk_lt_fo`, `lk_lt_rayf`), the proxies (hip / lathe / mesh / catalogue) and `lk_lt_extrude` run only with `lk_lt_sun` (outdoors). Indoors the flames (`lk_lt_term` shadow march), the room light (`lk_lt_aoval`) and the shafts read only the 16 unit height map, so a correction can only raise / lower whole cells (ship 493..497: bow block + sail row as water ops in light_proxies.json). Needed: the view ray, flame shadows, AO and shafts read the fine field indoors too; `mesh` ops then work in any room. First users: the ship 493..497 (round hull and bow, the sail), the floor rim bands of the caves (246 / 250 / 242 / 162: the drawn floor beyond the last room cell as a thin shape), furniture.
2. **OVERHANGS ('air under the sail').** The light stores ONE height per column (16 units in the height map, 4 units in the fine field): anything with air below it is impossible today and was worked around by filling: arch gaps of thin walls (486, `lk_lt_archfill`), door niches (indoor + outdoor), the ship's sail as a solid row, tree crowns as lathes standing on the ground. Idea: a second interval per fine column = one floating SLAB (bottom z, top z) on top of the ground column; the view ray hits the slab's underside / sides / top, shadow marches test both the ground column and the slab. Shapes (mesh ops) would write slabs from their geometry (Blender meshes already have a bottom). Then: the arch over the 486 passage instead of a filled gap, the sail with air below, bridges you walk under, tree crowns with light under them, castle door arches. Cost: one more GPU texture plane, every march does two interval tests (measure the frame time: GL5 block budget, `LANDSTALKER_FRAMESTAT`).
Order: part 1 first (it is the base and fixes the ship / caves), then part 2 on the same fine field. Keep every old path switchable (env test aids) and Off = bit exact.


**Status 2026-11-08 (dev eda2a36, headless verified, user test open):** parts 1 and 2 are built as a base (`LK_LTFINE v1` / `LK_GLFINE v1`). Indoors the fine field is live (`lk_lt_fo == LK_LT_IFO` sub columns replace the cell height, view ray `lk_lt_rayi`); one floating slab per sub column (`lk_lt_sb` .. `lk_lt_st`) is honoured by every shadow march, the view ray (layer A only), the horizon and the room light AO, indoors and outdoors; slanted side faces (codes 4..19) give round shapes without stripes. Data ops in `data/light_proxies.json` (see its `_about`): `box` (world units, indoors), `prism` (poly, top, bottom = slab, floor), `mesh` + `air`. Used for the ship rooms 493 / 494 / 495 / 497 (box, mast prism, sail slab, bow prism). GPU: fine texture 296 x 888, uniforms uIfine / uNslab. Still open: user test of the ship; outdoor slabs (486 arch, tree crowns, bridges); cave floor rims 246 / 250 / 242 / 162 as thin shapes; furniture; outdoor slanted faces (rayf unchanged); faint AO banding on the bow front. Release v1.9.0 postponed by the user until the light is clean. **Update (dev 4dd23a7):** CARVE op (`data/light_proxies.json` op `carve` {cells, bg sea|layera, floor}; `patch_lights.py` lk_lt_bgpix / lk_lt_cvh; user 'die 3D-Formen dem Sprite an sich nachformen'): at room load every sub column is lowered until its top AND its front edge (nearest the camera, scanned once bottom up) land on drawn object pixels (sea = nothing drawn or a water tile; layera = a layer A pixel), slabs keep their heights, then a 3 x 3 median (`LANDSTALKER_LT_CARVEMED=n` passes, default 2); runs from the picture in memory (nothing ROM-derived in git). OUTDOOR CARVE (default on, `LANDSTALKER_LT_CARVEOUT=0` = off; user 'selbiges gilt fuer andere 3D-Formen'): every outdoor sub column of a hip proxy (type 1) or Blender mesh (type 4) is carved to layer A (0.1..0.5 ms per room; trees / bushes / pines keep sprite based shapes); thin eave shadow strips gone (632 / 31 / 635 / 636 / 488). SHIP 493 AS A BLENDER SHAPE (recipe `remake/recipes/proxy_ship_493.py`, `python3 remake/tools/build_asset.py proxy_ship_493` -> `data/proxies/ship_493.obj` + `ship_493_sail.obj` (mesh + air slab 56..232); sea level -22 for all ship water ops; hull, decks at walkable heights, rails, mast (626, 702), figurehead r 7 at (648, 832); replaces the earlier box / prism / carve ops; open: faint dark AO strip behind the figurehead). Slanted face normals from a 7 x 7 window (lk_lt_idiag + GLSL idiag). View rays reach down to -40 (was -16; rooms without such data unchanged, caves 246 / 250 identical). PINES (user 'Lichtform fuer die Kiefer genauer'): kind 2 light shape has the 6 drooping tiers of `remake/lib/kit_c.py` pine(): lk_lt_pinr(f) = (1 - k/6) * (1 - 0.55 t) in sun march + view ray field, GLSL pinr + uniform uPineT (sc[26]); `LANDSTALKER_LT_PINETIER=0` = old cone; rooms 638 / 488 shadows slightly changed. GL5 compare (`LANDSTALKER_GL5CMP=1 LANDSTALKER_GL5=0 LANDSTALKER_DAYNIGHT=0`): view ray / AO / sun / key exact, terms 5 off by 1. lightedges runs are only comparable with the SAME room order and DAYNIGHT=0 (a different warp order gave 146 px in room 250).
**Update 2026-11-08 (dev 7599971, headless, user test open):** SLAB HALO built: per sub column within 2 of a slab the nearest slab sub column + height range (`lk_lt_hk/hb/hs`, GPU fine texture 296 x 1184 with 4th plane); sun march, key light and flame term use the exact horizontal distance (`lk_lt_halocl`) as soft clearance, so slab shadow sides are no longer knife-sharp. ARCADE 486 is ON (measured mesh `proxies/arcade_486.obj` air + water op, background-verified against layer A): lightedges 333 vs 343 (old arch-gap fill) vs 704 (before halo); GL5 compare exact. Bush crowns squashed 0.8 (`LANDSTALKER_LT_BUSHELL`). Open: toothed corbel shadow outline (4 unit slices), tree crowns as slabs, cave rims.

## REAL 3D LIGHT SHAPES (decided 2026-11-08 evening, user: 'echte 3D-Formen brauchen wir doch fuers Remake ohnehin. dann kann das Lichtsystem auch direkt so aufgebaut sein' + 'wir sollten den GPU-Weg einschlagen')
Why: the Blender / remake models are converted into the fine field (one height per 4 unit sub column + one slab, a face direction guessed from the stair in 16 steps).
Everything wrong at the ship 493 came from that conversion: stripes on round hulls (quantized normals, fixed for now by `lk_lt_kslant`), overhangs (raked bow,
forecastle tip, figurehead) become columns down to the sea (`remake/tools/proxy_bgtest.py`: magenta over the drawn water), slabs only catch layer A pixels (the hull is layer B).
Decision: where a model exists the light uses its REAL surfaces; the height map + fine field stay the base for everything without a model (most of the game) and the CPU fallback.
GPU-FIRST (user rule 2026-11-08, memory 'GPU-first'): the new path is GPU only; the CPU keeps today's look (fine field conversion) as fallback; no CPU / GLSL lockstep for the new parts.
Stages (each on the ship 493..497 first; every stage: rooms without models pixel-identical, proxy_bgtest clean, lightedges, user check):
1. SURFACES: at room load the GPU rasterizes the room's model triangles (data/proxies/*.obj of the room's mesh ops) in ROOM PICTURE space (orthographic, U = x - y + 1184,
   V = (x + y) / 2 - z, depth along the view ray) into a model buffer: hit z, smooth normal, model id. The geometry pass (GL5b view ray) takes the model hit when it is
   nearer than the height field hit and the drawn pixel is not background (water tile / not drawn); the light terms get the real normal (a new face code 'model normal'
   + a normal plane in the block textures instead of the 16 slanted codes). Overhangs and the figurehead's air come for free; layer A / B no longer matters for models.
2. SHADOWS: models cast shadows through a SHADOW MAP per directional light (key light per room, sun per Day / Night step): the models rendered from the light direction,
   soft edges by several offset taps (PCF); the height field march stays for the rest; flames first keep the fine field (models as columns) - point light shadow maps later if needed.
3. CLEAN-UP: mesh ops with a model no longer write the fine field on the GPU path (the CPU fallback keeps it); test aids to switch back.
4. MORE MODELS: arcade 486, church 632, gate 637, arch 636, castle 31 ... and every later remake model: the same OBJ / GLB in game coordinates serves light and remake.
Tools: proxy_bgtest.py (background test as the light sees it, LANDSTALKER_LT_DUMPFINE), proxy_overlay.py (edges over the picture), lightedges.py, GL5 view ray compare where it still applies.
