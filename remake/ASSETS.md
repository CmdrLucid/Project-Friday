# Asset list (order of work; each asset waits for the user's OK before the next one)

| # | Asset | Status | Recipe | Notes |
|---|---|---|---|---|
| 1 | Massan house A (room 592, the lone house west of the statue) | waiting for the user's verdict (2026-10-24 late) | `recipes/massan_house_proj.py` (+ `tools/rom_picture.py`) | ORIGINAL PIXELS projected (Scale2x), hidden sides mirrored; older tries: `recipes/massan_house.py` (own textures, pixel look), `recipes/hut.py` (first hut, superseded) |
| 2 | Pine, bush / hedge | - | - | pixel foliage texture, cone stack with jitter; hedge = low rounded block |
| 3 | Wooden fence: stakes, gate, corner | - | - | |
| 4 | Stone steps and stones | - | - | |
| 5 | Ground: grass, dirt path, cliff wall, water | - | - | tileable pixel materials; cliff = vertical rock face |
| 6 | Props: barrel, crate, sign, well | - | - | |
| 7 | More buildings: church, shop, tower | - | - | |

Approval log: (none yet)

## HD textures (2D, user 2026-10-24: 'nicht 3D, nur HD')
First experiment: pines of the forest room 563. `remake/tools/hd_enhance.py` (de-dither, Lanczos 4x, form light, needle detail; needs the venv `~/hdvenv` with pillow / numpy / scipy) and `remake/tools/hd_pack.py` (cuts the enhanced frame into HD tile pieces by an 'id pack' screenshot: every tile replaced by an image whose RGB encodes tile number + position) -> `~/.landstalker_remake/hd/pack_forest` (use with `LANDSTALKER_TILEPACK=dir LANDSTALKER_HD=1`). Result looks smooth, not pixelated; known flaw: a tile is cut from ONE place on screen, so the grass tiles show a faint grid (their neighbours differ). Verdict of the user: open.

