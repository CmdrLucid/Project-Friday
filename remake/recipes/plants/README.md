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
1. plane A and plane B of the room, each alone (romrender with the other layer empty), palette index & 15. Since 2026-11-21 plane B too: the BACK rows of a
   forest are drawn in plane B with the ground (user: 'ganz viele nicht erkannt', rooms 427 / 566; 10252 -> 14732 pines); a plant found in both keeps plane A.
   `NO_PLANE_B` = rooms whose plane B is a backdrop (34 / 35 Mercator castle tower: the forest far below).
2. lattice scan with the TOP rows of each template (tips stay visible in dense forests) + the bush's lower crown / stem (bushes behind a pine row,
   user 2026-11-20 room 362), >= 65 % equal.
3. pine or small: rows tip+16..31 equal the big pine's rows 16..31 -> pine, its rows 32..47 -> small; covered -> the nearest decided pine.
4. foot: the view ray through the foot pixel meets the floor of the height map (`foot_world`, v3 2026-11-21: bush tops are crowns, a covered trunk continues to the
   next lower floor, a blocked group stands on its group floor). Height map = `heights_full`: the 0000 words inside the room count as floor 0 (LESSONS 86;
   room 561's whole ground). Group floor (`group_floors`): per 4-connected group of blocked cells of one height the LOWEST border floor that is more than a
   stray touch (>= 3 border edges and >= 10 % of the border), plain floors (floor type 0) first (566: pond type $19); never for $4Fxx barriers (height 15)
   or the blocked-0 void around the room (469: the barrier ring touches every floor of the room). Checked with tools/heightview.py --tips.
   Covered trunk in a forest (2026-11-26, bug sweep room 488): when the first floor on the foot ray is the ground of a blocked forest group, the plant stands there (its own neighbours cover the trunk);
   before, the covered-trunk rule pushed back-row pines through their forest and past the shore (13 rooms / 88 pines moved).
   Big round tree (`foot_tree`, 2026-11-21): it stands on its OWN 4 x 4 collision block (4 cells at the ground's height = `TREE_TRUNK`); the foot is that block's centre on the ground
   (the plain ray stopped at the block's side, room 458 z 47 instead of 16: the block stayed a box beside the model). Check: room 488 -> 576,656 z 128 = the measured axis. Room 451's second big tree has another block pattern: kept as before (open).
5. bush cells of the object catalogue (`data/object_blocks.json`) add one bush per cell (dense fields, crowns covering each other), foot one step below the cell top.
6. plants inside a hand tree model's rectangle (`pine_cl`, `pine_court`, `tree_` mesh ops) are left to that model.
`--write`: `landstalker/data/plants.json` ({room: [[model, x, y, z], ...]}) + `landstalker/data/proxies/plant_{pine,small,bush}.obj` (origin = drawn foot).

## Runtime
`tools/patch_lights.py` LK_LTPLANT v1: the models become triangle lists, the instances a table; `lk_lt_objbuild` (LK_LTOBJ) draws every
instance of the room into the object model buffer and skips the old lathe of a catalogue cell / lathe tree with a plant foot in reach.
`LANDSTALKER_LT_PLANTS=0` = the old lathes (test aid). GPU only (as all light).

## Fit tools (local, need the ROM)
`fit_small.py` / `fit_bush.py`: grid search of the recipe parameters against the drawn silhouette (plane A, free side mirrored).

Small pine half hidden (2026-11-21, user, room 484 foot U 1232): the tip was right, the pine / small test was undecided (small 0.33, big 0.10 < 0.45) and
fell back to the big pine; an undecided plant now takes the clearly better class (>= 0.3, margin >= 0.15). The blocked-0 VOID connected to the height map's
edge is no floor for the view ray (it got 144 from the nearest-floor search; the small pine landed in it), unless the ray finds no floor at all behind it
(plants drawn over the void at the room's edge keep the old rule). Pine model refit 2026-11-21 (params_pine.json incl. its seed, user OK).
