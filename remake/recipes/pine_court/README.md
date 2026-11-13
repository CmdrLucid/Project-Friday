# Courtyard pine (Mercator castle, rooms 32 / 33) - light shapes + remake model, since 2026-11-12

Recipe only (no ROM data). The left castle court (32 = 33 in layer A, pixel identical) has its OWN pine sprite (tileset 14 blocks $3C7 / $3CA..$3CF /
$39A / $39F, partly shared with rock in 464 / 470, so NOT added to data/object_blocks.json); the automatic objects made them flat / a hip box
(user 2026-11-12: 'nicht alle Baeume werfen Schatten', 'andere Tannen-Sprites').

- `pine.py`: the approved style C pine (remake/lib/kit_c.py pine(): 6 star tiers with drooping tips + trunk with root flare) in pure Python,
  with a TRIMMED variant (`trim`: no random jitter, 22 short even tips per tier, notch 0.86, droop 0.5, tiers turned half a tip in turn; user
  2026-11-12: 'die Tannen im Schlosshof sind getrimmter als alle anderen, weil sich da quasi ein Gaertner drum kuemmert'). `params_light.json`
  = the trimmed pine fitted to the drawn sprite (silhouette IoU 0.93 on the free standing pine, 25 px outside; the wild one 0.88): it is the
  remake model AND the light shape. Clay preview wild | trimmed: ~/.landstalker_remake/assets/pine_court/ (local).
- `feet.json`: the trunk feet (game units, ground z 0) of all 15 pines, found by a TEMPLATE MATCH of the free standing pine (layer A pixels,
  >= 0.36 of its pixels equal: hidden ones in the groups score 0.39), foot = template bottom row - 2, minus the fit offset (1.87, 2.0);
  groups a..e = the op rectangles (cells) = the game's collision cells of the pines (the feet sit 3/4 into those cells).
- Writes `landstalker/data/proxies/pine_court_a..e.obj` (closed parts, shared vertices); ops in light_proxies.json rooms 32 + 33 (`surface`).
