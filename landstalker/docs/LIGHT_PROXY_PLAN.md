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
- Candidates not done yet (DBG=5 survey 2026-11-04): room 638 (fountain court: city wall x 288..320 became a hip with ridge 247, the round towers are no shapes),
  636 (rocky arch over the river), 637 (north gate).
- Packaging copies `data/**/*.json` and `*.obj` (AppImage / Windows zip). Lighting Off / indoor byte-identical; only frame 2100 of rec_20261103_1803 changed (church).
- Refined 2026-11-04 (user: 'verfeinere die 3d Form der Kirche'): the entrance gable was 13 units too high (ridge 107 -> 94, read from the gable apex U 720 / V 538 and the
  eave corners U 688 / V 583, U 750 / V 548 of the picture) and too short at the front (x 392 -> 400 = over the column cells x 24 of the height map). It now starts at x 340 INSIDE the
  hall: its south slope meets the hall's east hip slope in a 45 deg valley, which is the vertical roof line of the picture (the 'cross gable'). Check: overlay of the OBJ edges
  on `remake/tools/rom_picture.py ROM 632 400 360 400 340` with `remake/tools/proxy_overlay.py` (apex, eave corners and valley on the picture's lines). Height map rows 50..61 confirm the footprints (hall 4 = 64,
  house x 15..19, door cell (19, 60) height 1). Result rec_20261103_1803 frame 2100 (lightshots): 1596 pixels changed, only the strip in front of the
  church's south wall and next to the door (a little brighter = shorter gable shadow); Lighting Off byte-identical (0 pixels).

