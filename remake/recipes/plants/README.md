# Plants: every drawn pine and bush as a real 3D light model (since 2026-11-20)

User 2026-11-20: "Generell sollten alle Kiefern und Buesche ihr 3D-Modell haben, weil wir sowieso alle Karten im 3D nachbauen".
Recipe only (no ROM data in git): the templates are rebuilt from the ROM on every run; git gets our models + the measured feet.

## Models (user OK on clay preview + drawing sheet, 2026-11-20)
| model | drawn where | recipe / params | fit (silhouette IoU) |
|---|---|---|---|
| `pine` | town + forest pine (Mercator, Massan, Gumi, all forests; the darker forest colour of tileset 17 has the same shape) | `pine_court/pine.py` wild, `params_pine.json` | 0.87 |
| `small` | small pine (room 475 ...): the original draws it from the BIG pine's tiles without the middle 16 rows (32 px instead of 47) | same recipe, `params_small.json` | 0.867 |
| `bush` | the round bush on its Y stem: ONE drawing in every outdoor tileset (what looks different is bushes standing behind each other) | `bush.py`, `params_bush.json` | 0.90 |
The Mercator castle court pine (rooms 32 / 33) keeps its own trimmed model (`pine_court/`). Tips 14 -> 11 / light segment counts: ~500 triangles per
model (dense forests: 300+ pines per room).

Lessons (2026-11-20): "narrower" pines were pines standing behind others; the "second bush drawing" was the other side of the same slightly
asymmetric bush. Check overlap / sides (plane A alone, both free sides) before declaring a new variant.

## plants.py
`python3 remake/recipes/plants/plants.py ROM [ROOMS] [-j 6] [--write] [--png DIR]`
1. plane A of the room only (romrender with an empty layer B: the plants are layer A tiles, the ground goes away), palette index & 15.
2. lattice scan with the TOP rows of each template (tips stay visible in dense forests) + the bush's lower crown / stem (bushes behind a pine row,
   user 2026-11-20 room 362), >= 65 % equal.
3. pine or small: rows tip+16..31 equal the big pine's rows 16..31 -> pine, its rows 32..47 -> small; covered -> the nearest decided pine.
4. foot: the view ray through the foot pixel meets the floor of the height map (`pine_cluster.foot_world`).
5. bush cells of the object catalogue (`data/object_blocks.json`) add one bush per cell (dense fields, crowns covering each other), foot one step below the cell top.
6. plants inside a hand tree model's rectangle (`pine_cl`, `pine_court`, `tree_` mesh ops) are left to that model.
`--write`: `landstalker/data/plants.json` ({room: [[model, x, y, z], ...]}) + `landstalker/data/proxies/plant_{pine,small,bush}.obj` (origin = drawn foot).

## Runtime
`tools/patch_lights.py` LK_LTPLANT v1: the models become triangle lists, the instances a table; `lk_lt_objbuild` (LK_LTOBJ) draws every
instance of the room into the object model buffer and skips the old lathe of a catalogue cell / lathe tree with a plant foot in reach.
`LANDSTALKER_LT_PLANTS=0` = the old lathes (test aid). GPU only (as all light).

## Fit tools (local, need the ROM)
`fit_small.py` / `fit_bush.py`: grid search of the recipe parameters against the drawn silhouette (plane A, free side mirrored).
