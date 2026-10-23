# Stage 3 inventory: room / entity / camera model and seamless room transitions (2026-10-23, dev)

Purpose: before any code, what the own renderer + tools already have, what is missing for a game-state model that is independent of the VDP and of the 68K's RAM layout, and the proposed order. Nothing here changes the picture. Status letters as in FORMATS: V verified, R read in code / docs only, ? open.

## 1. What exists (inputs the own renderer uses today)

| Part | Where it comes from now | Verified | Notes |
|---|---|---|---|
| Room tiles, blocks, palette, animated tiles | ROM (room table `$0A0A00`, tileset table `$044010`, blockset groups `$1AF800`, `RoomPals $11C926`), C port in `patch_own.py` (`lk_o_room_load`, `lk_o_lz77`), Python twins `romgfx.py` / `romrender.py` | V (34 of 39 rooms >= 99 %) | Loaded when the room number changes. |
| Room map (FG / BG block ids, height map) | the game's RAM arrays (`$FF7C02`, `$FFA6CA`, `$FFD192`, 74 x 74 words, same cell index) | V | ROM decoder exists ONLY in Python (`romroom.py`, 35 of 39 rooms bit exact; 4 differ by game changes: rooms 139 / 142 / 632 top row, 454 scripted blocks). No C port yet. |
| Height map cell | byte 0 = floor height (low nibble, x 16) + flags (bit 6 blocked, bit 5 NPC blocked), byte 1 = floor type `00..2E` (doors 01..04, stairs 05, warp pad 08, ...) | V | Table in FORMATS 'Height map cells'. |
| Camera | `$FF1200` / `$FF1202` (previous pass); screen pos of block (x, y): `sx = 16 (x - y) + (cam2 - cam0 + 160)`, `sy = 8 (x + y) - (cam0 + cam2) / 2 + 104`; plane constants seeded exactly at a room load | V | We READ the camera, we do not compute it. The rules that move it (follows Nigel's X / Y / Z, 1 px per Z unit, stops at room edges?) are in `ScrollCameraPlus / Minus $002242 / $002326` and the `Handle*_MoveAndScroll` routines: not analysed. |
| Entities | visible list `$FF11DE` + sprite table snapshot of the VBlank (`patch_ownvb.py`), pieces / tiles from ROM (`lk_o_sprites`, `romsprite.py`); screen position = `+4E / +50` of the PREVIOUS pass (player `+0E / +10`) | V | The renderer works from the sprite table, not from a clean entity model. Entity struct fields known: X / Y tile `+00 / +01`, sub `+02 / +03`, Z `+12`, centre `+14 / +16`, box `+18 / +1A / +1C / +1E`, `+0B` SpriteGraphic, `+24 / +26` animation / frame, `+28` height map pointer, `+30` supporting entity, `+3B` SpriteType (see 3). |
| Entity -> screen | `a = CentreX - Z - cam0`, `b = CentreY - Z - cam2`, `x = a - b + $A0`, `y = ((a + b) >> 1) + $68` | V | One Z unit = one screen pixel up. |
| Footprint / ground | box corners projected = parallelogram; `GetDistanceToGround $0032C6`; used by the shadow code (HD, angular, contact) | V | Shadow code now has ONE light object (`lk_light_*`). |
| HD layer | tile / sprite origins by content hash (`patch_gfxorg.py`), n x n blocks per game pixel, HD HUD, HD shadows | V (headless) | 1x picture stays the reference. |
| Visual effects | tree warp, warp pad, Nole / Kazalt warp, room-change fades from the game's counters (`$FF0F50..52`) | V (headless) | Effects are screen effects of the 2D picture. |
| Room placement tables | room entities `$01B932-$022E80`, entity offsets `$01B090-$01B6F0`, room connections / exits `$11CEA2-$11EA64` | addresses V (two sources), formats ? | NOT parsed by any tool of ours. landstalker-lib / `landstalker_disasm` / the editor have the formats. |
| Id tables | `ROOMS.md`, `ENTITIES.md` (type id = entity byte `+3B`), `ITEMS.md`, `FLAGS.md` | V | |

## 2. What the game does at a room change (R, from names and past sessions)

Door / exit floor cell (`ProcessFloorType $00603C`, types 01..04 `HandleFloorDoorNE / SE / SW / NW`) or script -> `WarpToRoom` -> `LoadRoomParams` / `GetTilemap` / `LoadRoom $002996` -> fade out, VRAM / RAM arrays rebuilt, entities of the new room spawned (`ResetPlayerStateForRoomLoad $002A46`), fade in. The own renderer draws the OLD room until `LoadRoomPath` returned, then the new room (INDEX status 2026-10-21 'mach den rest'). There is exactly ONE room in RAM at any time; the 68K logic cannot run two rooms.

## 3. Correction found while doing this inventory

The entity TYPE id (ENTITIES.md) is the byte at `+3B` (`Player_SpriteType` in `ram.inc`); `+0B` is the SpriteGraphic id (graphic ids are a different table). The first version of the angular / contact shadows read `+0B` and classified by the wrong table (the vase in room 444 looked like a platform, the people in room 615 like statues). Fixed in `patch_shadow.py` (reads `+3B`; verified: room 444 platforms = type 21, vase = 17, room 615 priest 16, women 79). FORMATS / ENTITIES text corrected.

## 4. Gaps for a real model (what stage 3 needs)

1. **A room object independent of RAM**: ROM decoder in C (port of `romroom.py`), cached per room number; arrays: FG, BG, height map (+ floor type), tileset / palette ids, offsets. Needed for seamless transitions (the neighbour room must exist before the game loads it) and for any non-isometric view.
2. **A clean entity list**: read the entity structs directly (`$FF5400 + n * $80`) each frame (type `+3B`, graphic `+0B`, position, Z, box, animation), instead of reconstructing from the sprite table. The sprite-table lag logic (`+4E / +50`, double pass frames) is a workaround for not having this.
3. **A camera model**: reproduce the game's camera from Nigel + room bounds (and later free it: smooth follow, rotation). Needs analysis of `ScrollCameraPlus / Minus` and the callers; verify against `$FF1200 / $FF1202` over all replays.
4. **Room graph**: parse exits (`$11CEA2`: which cell leads to which room, arrival position) and entity placements (`$01B932`): gives the neighbour of a door and where Nigel appears, which is the geometry a seamless transition has to line up.
5. **Transition rules**: decide what a seamless transition means for gameplay (the neighbour room's entities are static / frozen until the game really loads it; collisions and triggers stay the 68K's). Pure presentation: no change to the game logic, the exact `WarpToRoom` still runs, only the fade is replaced by a scroll / cross-fade.
6. **3D / rotation (later)**: height map -> voxel columns is automatic; the block art is 2D (needs new assets or the HD pack), figures are 2D sprites (billboards), shadows already take a light.

## 4b. Progress (2026-10-23)
- S3.1 and S3.2 are DONE (INDEX status 's3.1 und s3.2 machen ja', `tools/patch_roommodel.py`): C room decoder exact in 31 rooms, per frame model with the projection check exact for the player. Open: S3.3 onwards. User decisions (2026-10-23): stairs / dungeon entrances keep the CURRENT fade out / fade in; seamless only where it is possible (same level, neighbouring room); game logic stays the 68K recomp, the model is a presentation layer, goal = graphics + quality of life.

- S3.3 is DONE (INDEX status 'ja s3.3'): the camera is simply the player's (CentreX - Z, CentreY - Z), so the 'unknown camera rules' risk is gone; a free camera needs no game change. The camera analysis in section 4 item 3 is answered.

## 5. Proposed order (each step: no visible change, compare against the current picture, then the next)

- **S3.1** C room decoder + cache; compare with the RAM arrays at every room load in compare mode (35 of 39 rooms exact is the bar; list the 4 known differences).
- **S3.2** `lk_model`: one struct per frame (room id, camera, entity list with `+3B` types) filled from RAM; check that the renderer's current inputs equal the model's (assert in a debug mode), still no picture change. Moves the shadow classification and future effects onto it.
- **S3.3** Camera analysis + reproduction (verify on every replay), then a free-camera option in a debug mode only.
- **S3.4** Parse exits + entity placements; tool `tools/roomgraph.py` first (Python, offline, checked against ROOMS.md and the replays' room sequences), then C.
- **S3.5** Transition prototype behind an option (HD only first): draw the old room, scroll / blend into the new one using S3.1 / S3.4, game logic untouched.
- **S3.6** Decide with the user: how far (door slides, camera pans, no fade at all), and the 3D question.

Risks: the camera rules (S3.3) are unknown and the largest unknown; the 4 rooms where the game edits its own map; doors that are scripts instead of floor cells; rooms whose arrival position depends on story flags. Cost of S3.1 / S3.2 is moderate (the Python twins and the checks already exist), S3.5 depends on S3.3 / S3.4.

## 6. Decisions needed from the user

- Start with S3.1 + S3.2 (invisible groundwork, recommended)?
- What should a seamless transition look like when the neighbour room does not line up (stairs, doors on different heights): a slide, a camera pan, or a quick cross-fade?
- Should the model stay a pure presentation layer (game logic = the 68K recomp, recommended) or become the place where game logic is rewritten one day?
