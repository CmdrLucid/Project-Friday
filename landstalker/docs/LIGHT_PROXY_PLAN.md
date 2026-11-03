# Light proxies: invisible 3D shapes for lighting (plan, 2026-11-03)

Status: PLAN, agreed by the user 2026-11-03 night ('klingt sinnvoll'), nothing built yet. Rests on `dev` f8e8713 (LK_LIGHTS v7).

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
