# Asset list (order of work; each asset waits for the user's OK before the next one)

| # | Asset | Status | Recipe | Notes |
|---|---|---|---|---|
| 1 | Massan house A (room 592, the lone house west of the statue) | 2026-10-25: user not happy with the projection (odd from other angles); THREE STUDIES built; user: 'C am besten bisher, ausser wir kriegen B noch sauberer' -> B redone finer + lit, C got a plank door, the skull centred over it and a roof with overhang (`build(hx, lip, door, door_top)`); user undecided B vs C -> B variants `R_COL=orig / dedither / clean` (B3 clean = pattern per kind in the original palette, no dither noise), sheet `~/.landstalker_remake/assets/massan_house_B_vs_C.png`. DECIDED 2026-10-25: STYLE C. Mix test: Nigel as a pixel billboard in front of the door (`R_FIGURE=~/.landstalker_remake/figures/nigel_a4.png`, cut by `tools/rom_sprite.py ROM 0 4 0 ...`), sheet `massan_house_C_mit_Nigel.png`; waiting for his verdict on the mix | `recipes/massan_house_va.py` / `_vb.py` / `_vc.py` (shared `lib/massan_a.py`) | A = modelled house + tileable pixel swatches cut from the original (stepped light, outlines); B = voxels, 1 voxel = 1 game pixel, seen voxels take the original pixel, hidden ones a mirrored seen voxel; C = smooth toy diorama (procedural materials, AgX, DOF). Comparison sheet: `~/.landstalker_remake/assets/massan_house_varianten.png` (local). Older tries: `recipes/massan_house_proj.py` (projection), `recipes/massan_house.py` (own textures), `recipes/hut.py` |
| 2 | Pine, bush / hedge | APPROVED 2026-10-25 | `recipes/plants_c.py` | style C: pine = trunk + root flare + 6 star-shaped drooping tiers ('needles'); pine approved ('kiefer ist gut'); bushes redone after the user's 'nicht gut' from the front views in rooms 424 / 425: one shrub per map cell = round dark crown on a short Y stem, crown tops at R_HEDGE_H = 16 (the bush rows of room 425 are height-1 cells); Nigel shown standing on them. Sheets `kiefer_hecke_C.png`, `buesche_C_vs_Original.png` |
| 3 | Wooden fence: stakes, gate, corner | APPROVED 2026-10-25 | `recipes/fence_c.py` | style C palisade: sharpened stakes (~3.3 apart, ~22 high + dark point, random lean), binding rails inside, thick end posts with dark tops and stones at an opening; sheet `~/.landstalker_remake/assets/zaun_C.png` |
| 4 | Stone steps and stones | - | - | |
| 5 | Ground: grass, dirt path, cliff wall, water | - | - | tileable pixel materials; cliff = vertical rock face |
| 6 | Props: barrel, crate, sign, well | - | - | |
| 7 | More buildings: church, shop, tower | - | - | |

Approval log:
- 2026-10-25: asset 3 palisade fence in style C (`recipes/fence_c.py`) - user: 'der passt'.
- 2026-10-25: asset 2 pine + bushes in style C (`recipes/plants_c.py`: pine with drooping tiers; bushes = one round shrub per cell on a Y stem, walkable top at 16) - user: 'yes passt'.
- 2026-10-25: asset 1 Massan house A in style C (`recipes/massan_house_vc.py`: open dark doorway, animal skull `lib/props_c.py`, smooth golden thatch with a straw knot, 1:1 the original's size) - user: 'passt'.

## HD textures (2D, user 2026-10-24: 'nicht 3D, nur HD')
First experiment: pines of the forest room 563. `remake/tools/hd_enhance.py` (de-dither, Lanczos 4x, form light, needle detail; needs the venv `~/hdvenv` with pillow / numpy / scipy) and `remake/tools/hd_pack.py` (cuts the enhanced frame into HD tile pieces by an 'id pack' screenshot: every tile replaced by an image whose RGB encodes tile number + position) -> `~/.landstalker_remake/hd/pack_forest` (use with `LANDSTALKER_TILEPACK=dir LANDSTALKER_HD=1`). Result looks smooth, not pixelated; known flaw: a tile is cut from ONE place on screen, so the grass tiles show a faint grid (their neighbours differ). Verdict of the user: open.

