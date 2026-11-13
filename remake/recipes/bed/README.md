# Bed (Mercator / Ryuma houses, tileset 2) - light shape + remake model, since 2026-11-11

Recipe only (no ROM data). Reference: room 623 cells x 23..25, y 23..24 (3 x 2 cells, collision 1 step, head at the west wall);
`remake/tools/rom_picture.py ROM 623 1144 340 96 76 DIR`, the bed = the layer A component clipped to U 1154..1232 (local `bed623.json`, never in git).

- `bed.py OUT.obj [params.json]`: parts from rounded boxes (`furniture.rbox`): a board on four square legs, ONE pillow across the head end
  (user 2026-11-11: 'es ist nur 1 Kissen'; the brown patch at its open-side end is its shaded end), the blanket over the foot part hanging down to
  z 3.5 on the foot end and both long sides. `orient` "x" (head west, 3 x 2) / "y" (head north, 2 x 3 = mirrored at the diagonal).
- TWO VARIANTS (rule of 0a391): `tilt` 0 = the REMAKE model (level); `tilt` 3 = the LIGHT variant AS DRAWN: the artist drew the top raised towards the
  back wall (a uniform 3 px band along the whole back edge was missed by a level model; the right corner did not move, so it is a z tilt, not a
  wider bed). Level IoU 0.883, tilted 0.948 (50 px outside, 90 missed; the misses = the black under the board between the legs = painted shadow).
- `chk_cls.py OBJ PICDIR MASK.json [--map]`: z-buffered projection along the view ray (1, 1, 1) with classes (groups 'wood' / 'cloth' vs the
  drawn browns / rest); the fit used it (coordinate descent, local script) with a penalty for model pixels outside the drawing.
- IN THE LIGHT (2026-11-11): `remake/tools/furniture_ops.py` beds() / bed_obj(): every 3 x 2 / 2 x 3 block of walkable cells of one height whose
  picture matches the reference of its orientation (`BED_REF`: 623 for x, 620 for y - the mirrored beds are shaded on their own) in >= 60 % of the
  model's silhouette pixels -> `data/proxies/bed_ROOM[_k].obj`, 51 beds in 30 rooms (ratios 0.78 .. 1.00, the low ones checked by eye: partly hidden
  behind a cupboard 683 / a desk 623 (23, 32) / a crate 477 / a vase 616; nothing between 0.40 and 0.78).
  Headless lightedges (before -> after): 623 101 -> 359, 701 93 -> 371, 675 102 -> 264, 620 44 -> 112: the new edge pixels lie on the blanket's
  fold (lit top / shaded hanging side) and the pillow's shadow on the board = real shading of the shape; no boxes, no cut walls. Not played.
- Previews (local): `~/.landstalker_remake/assets/bed/bed_v1_clay.png` (old, with the dropped bolster); `bed_v2.png` (game view + clay, one pillow), `bed_v2_licht_623.png` (light before | after).
- Open for the remake model: hem with folds / scallops (the drawing has vertical streaks), a softer blanket, a head board? (none drawn).
