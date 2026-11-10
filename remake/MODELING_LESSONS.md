# MODELING LESSONS - what we learned building 3D forms on the original drawings

Own file for the modelling work (user 2026-11-10: 'vielleicht brauchen wir auch eine eigene Lessons fuer die Modellierungen?'). Read it before building or
changing a model; add every new lesson at the end of its section with the date. The models themselves and their game references: `MODELS.md`.
General project lessons stay in `landstalker/docs/LESSONS.md`.

## 1. Goal and standard (user decisions)
- Every form is measured EXACTLY on the drawing ('ungefaehr reicht nicht', 2026-11-08) and its GEOMETRY is close to the final remake version right away;
  materials can come later ('sonst gehen wir ueber alles mehrmals drueber', 2026-11-10). The light uses that same geometry.
- Show the user clay previews (game view + turned 60 / 120 / 180 degrees) and wait for the OK before the next model. One model at a time.
- Record every model in `MODELS.md` (game reference: rooms, cells, blocks, reference window; code; fit numbers; state; open points).

## 2. Measuring
- **Take the object's OWN pixels by COLOUR.** Plane A (layer A) also holds PAINTED SHADOWS of objects (church angel: dark olive 108,108,72 / 72,72,36 on the
  wall) and neighbouring parts (pedestal rims, red tops). A silhouette fit on the raw layer A mask grows into the drawn shadow (user caught it twice, 2026-11-10).
- **Look at the INNER LINES on a 1 px grid, not only the outline.** Concave details do not show in the silhouette: the knee niche of lectern / altar
  ('keine 4ecke', 2026-11-10), hoops of a barrel (read them from the grey hoop pixels per model height), lids, openings.
- **Anchor the position on a visible contact point** (the foot on the pedestal top, the waterline, a wall foot): the picture cannot tell depth from height
  (moving along the view ray (1, 1, 1) changes nothing). Without an anchor the fit wanders (church angel d -13 .. -35).
- **Measure the CARRIER first** (niche, pedestal, shelf) from its drawn corner lines when the object stands in void / blocked height-0 cells: the light treats
  void as a wall up to the room top. Church angel: niche 1 cell deep and 4 wide, pedestal 1 x 2 (first guessed 2 x 2 = wrong), data op `ground`.
- A free profile fit can prefer a WRONG shape that matches pixels better (barrel / jar top as a cone, IoU 0.994 vs flat 0.986): fix the physically right
  class first (flat top, symmetric barrel), then refine.
- Find all copies of a decoration by a PICTURE MATCH against a reference copy, not by top block ids (objects against a wall get other blocks).
- The warp test aid (LANDSTALKER_WARP) does not reach every room from the test save (chapels, cellars stay black): a black shot is no result.

## 3. Fitting the shape
- **Never outside the drawing**: score = covered - 12 x outside, grow from thin rings; then nothing sticks out (the user sees every pixel that does).
- A round body that is not round about one axis (twisted robe): rings with their OWN centre and radius, fitted by moving the LEFT and RIGHT edge of each ring
  from the measured row edges (moving centre / radius separately gets stuck).
- Check the result by PROJECTING THE REAL TRIANGLES into the game picture (U = x - y + 1184, V = (x + y) / 2 - z) and counting outside / missed pixels;
  ray-march estimates differ by up to half a pixel at the edges.
- Keep every part INSIDE its carrier: the church angel's wings first swept back along the screen axis and reached into the niche's back-wall cells; the light
  then cut the wall (hard edges, user 2026-11-10). Wings parallel to the back wall fit. Check the x / y range of the mesh against the carrier.
- Fitted outline radii carry the drawing's PIXEL STEPS (ripples on a jar neck / belly); a real turned object is smooth: smooth the radii once (3-tap) and
  accept a few edge pixels (jar 0.962 -> 0.948, 4 px outside) instead of modelling the stairs (2026-11-10).
- Detail can be moved ALONG THE VIEW RAY (1, 1, 1) without changing the game picture (depth of wings, relief, lid recess) - but relief taken from the
  drawing's shading alone gives lumps, not real parts (church angel try 2026-11-10): figures need real parts (head, arms, child, folds, feathers).

## 4. Light side effects (every model is also a light shape)
- A shape under or next to a FLAME moves the flame light (its position comes from the view ray of the flame's picture centre): check the light list
  (LANDSTALKER_LIGHTING_DBG=1) before / after. Stands carry their flame (`carrier` data: light on the axis above the bowl, no self shadow).
- A mesh op stamps EVERY sub column it covers as a solid column from the ground, also outside its cells: floating parts need `"air": true`, and nothing may
  reach over void / back-wall cells.
- One light object per physical object (the light never shades an object by itself): one op per vase / barrel / stand.
- Compare lit shots only with the same LANDSTALKER_LIGHTING_DBG setting; check zoomed before / after pictures for hard edges (user rule: hard edges = bugs).

## 5. Tools and paths
- Blender (Flatpak) needs `--filesystem=home` for scripts / files outside the sandbox; an ortho camera at distance > 100 needs `clip_end` raised; point the
  camera with a TRACK_TO constraint.
- Montage of PNGs: `ffmpeg -i a.png -i b.png -filter_complex hstack=inputs=2 out.png` (remake/tools/proxy_overlay.read_png does not read Blender's PNGs).
- Generated models / previews: `~/.landstalker_remake/assets/<name>/` (never in git); our measured numbers + builders: `remake/lib/furniture.py`.
