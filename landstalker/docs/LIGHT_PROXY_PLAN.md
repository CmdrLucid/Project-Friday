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

