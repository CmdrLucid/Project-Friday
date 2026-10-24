# Ideas: modern look, own renderer, voxel remake (THEORY ONLY, nothing built)

**Written 2026-10-10 (evening), session ccr-70fb8174-wtrh4v, from a design discussion with the user. Based on knowledge at `dev` commit `fad9a7f`**
(widescreen experiment up to `LANDSTALKER_WIDE_STRIPS`, VDP queue + map loader analysis, `symbols.json` as of this date, build input checksum not re-measured).
Nothing here is implemented or verified on the Deck. Treat every claim as a plan or hypothesis unless marked "known". Re-check against the code/docs
of the day before acting; if the facts below changed, update this file and keep the old date visible.

## Known facts this is based on (all documented elsewhere, see DEBUGGING.md "map loader", "VDP write queue", "Widescreen")
- The recompiled game still draws through the GPGX VDP software renderer; the game writes VRAM/CRAM/VSRAM/DMA like on hardware.
- The room map is a 2D array of 16-bit block indices (148 bytes = 74 blocks per row, base `$FF7C02`, background `$FFA6CA`); a block = 16x16 px = 2x2 tiles.
  `BlockToTiles` ($00A748) turns blocks into VDP queue entries (`$FF3900`), flushed in VBlank by `$002686`. The height map (`$FFD192`) has the same stride.
- The map is isometric: a screen rectangle is a diamond in map coordinates (strip loaders load strips of 12 blocks around the camera `$FF1124/$FF1125`).
- Entities have x/y/z (player struct `$FF5400`, Z word at +$12, sprites 0x80 bytes from `$FF5480`). Game logic is already "3D-ish".
- Widescreen currently = widened GPGX viewport + extended strip loaders + a heuristic "is this the map?" signal (`UpdateSprites` recent or `$028FD8` on the stack).

## Option A: HD / modern look on the existing recomp (realistic, incremental)
Hook at the VDP boundary (like texture packs in Dolphin/PCSX2):
1. **Own renderer for the final picture**: arbitrary resolution, GPU (SDL/GL/Vulkan) instead of scanline software, shaders (CRT exists already), lighting/shadows, widescreen for free.
2. **Tile/sprite replacement**: hash tile data at upload (DMA/VRAM write) -> replacement texture. Problem: per-8x8-tile replacement looks patched together because
   Landstalker builds rooms from 16x16 blocks and sprites from fragments loaded dynamically. Better key: **room block** (index in the block table `$FF5C02`) and **sprite frame** (from entity + animation state), not raw tiles.
3. Needs: block/sprite tables understood and named (symbols.json), a stable "what is on screen" model (see Option B step 1).
4. Legal/repo rule stays: only mapping logic in the repo; replacement assets and ROM data stay outside (no ROM-derived binaries in git).
Limits: palette/CRAM tricks (fades, water, flashes) must still work with replaced textures; AI upscaling changes style, hand rework is the real cost.

## Option B: own renderer driven by game state (cleaner than patching VRAM) - stepping stone to C
1. Read the world from game RAM instead of from the VDP planes: room id (`g_RmNum1 $FF1204`), map (`$FF7C02/$FFA6CA`), block table (`$FF5C02`), height map (`$FFD192`), entity list/sprite frames.
2. Draw the isometric map from block indices at any size -> no margin/stale-column problem, no widescreen loader hacks, no "is this the map" heuristic (the game state says it).
3. UI/menus/text boxes stay on the VDP path (or are composited from the VDP window plane) until replaced.
4. The widescreen work is the learning phase for this: the map-loader analysis (diamond, strip loaders, cell-index arithmetic) and the screen classification carry over almost 1:1;
   only the `UpdateSprites` time heuristic is a stopgap that a state-driven renderer removes.

## Option C: 3D voxel remake (a new game that uses the original as specification)
- **Why plausible**: heightmap + block grid per room can be extruded to a voxel grid automatically; entity x/y/z, collision, physics constants, AI, scripts, dialogue, items/flags are
  reusable *logic*. The recomp is a **differential-test oracle**: same inputs -> compare positions, flags, room changes against the original behaviour.
- **What is genuinely new work**: all models/voxel sprites/animations/textures (pixel sprites do not convert to good voxels automatically - art or AI-assisted authoring),
  camera/rendering/lighting, fine room detail (stairs, pillars, decoration come from tile blocks and may need hand modelling), a modern engine (Godot/Unity or custom voxel mesher) and audio port.
- **Data path**: extractor from the user's ROM at runtime/dev-time (same model as now: no ROM data in the repo) -> modern data (rooms, heightmaps, entity tables, scripts, text) -> engine.
- **Prerequisite knowledge** (this is where `symbols.json` pays off): room/block/heightmap formats, entity struct fields, sprite behaviour table, script/cutscene tables, item/flag tables, text format, save format.
- Effort: very large; only worth it once logic and data formats are understood well enough to describe them without the 68K code.

## Recommended order (user agreed to the direction on 2026-10-10, nothing scheduled)
1. Finish compat work (interpreter fallback -> empty log -> opt-in).
2. Widescreen as is (experiment) -> display pipeline polish. Treat it as research for B.
3. State-driven "what is on screen" model (B step 1-2) in a debug overlay first; compare with the VDP picture.
4. Tile/sprite replacement layer (A) on top, keyed by block/sprite-frame.
5. Keep naming everything: **every learned address goes into `docs/symbols.json` in the same commit** (rule applies to all future work).
6. Remake (C) only after 3-5, with the recomp as test oracle.

## Open questions (to answer from the code before committing to any option)
- How are sprites (player, NPCs, enemies) uploaded: fixed VRAM slots per room or dynamic per frame? (decides the sprite-frame key for replacement)
- Does any screen use plane content that is not derivable from RAM state (compressed/decompressed art caches, island map, intro scenes)?
- Per-room extents: how are rooms narrower than the picture handled in a state-driven renderer (black? repeat?)
- Is the block table `$FF5C02` filled from ROM by a decompressor we can reproduce (LZ77 gfx, `DecompressLZ77Gfx_CopySlots`)?

## Asset pipeline ideas (added 2026-10-10, late evening; same knowledge state as above, plus the session discussion; NOTHING TESTED)
Discussed with the user in session ccr-70fb8174-wtrh4v. All quality statements are expectations, not results.

### Roles
- **Magnific (AI, MCP tools connected in some sessions)**: raw material. Upscale, restyle, remove background, PBR maps (for HD textures, Option A); image-to-3D / text-to-3D, remesh, retexture, rig, animate (for models, Option C).
  Weak spots: style drift between images (needs a fixed style reference + prompt recipe), credits per image (check cost with the simulate/cost tool before a batch), animations for dozens of characters, palette effects (water, flashes, fades).
- **Blender, headless (`blender -b -P script.py`), scripted by Claude**: processing and rendering with identical settings for every asset (the cure for style drift).
  - voxelize meshes (voxel remesh) -> real blocky models,
  - build room geometry procedurally from heightmap + block data (Python API),
  - **pre-render 3D models from the game's isometric angle into HD sprite frames** (one image per animation frame and direction): consistent lighting, usable for Option A without a 3D game,
  - rig/animate once on a skeleton and reuse, bake normal/other maps.
  Runs on the Steam Deck (Flatpak via Discover or the blender.org tarball; check the current install route). Viewport work/rendering is slow there; headless scripting is the useful mode. Modeling/animating by hand needs skills the user does not have; judging the look stays a human job.
- **MagicaVoxel** (voxel editor): targets Windows/macOS, would need Wine on the Deck (unknown if it works).
- **Game engine (e.g. Godot, runs on Linux/Deck)**: only for Option C, much later.

### Recommended first experiment (small, judge by eye)
1. Export one or two sprite frames and one room block from the user's own ROM (needs the headless frame/screenshot dump = first Deck task in HANDOFF).
2. HD path: upscale + restyle with one fixed prompt; look at the result in the game's palette/context.
3. 3D path: one character -> Magnific image-to-3D -> Blender headless: voxelize + isometric pre-render of 4 directions.
4. The user judges the style; decide then whether to build a pipeline.

### Legal / policy notes
- The inputs would be Sega's original artwork sent to third-party services; outputs are derivative. Personal use on the user's own Deck is much less problematic than distributing a texture pack or a remake: get proper advice before releasing anything.
- Repo rules stay: no ROM-derived images, generated textures/models or other assets in git; keep them local (e.g. `~/landstalker_assets/`, outside the repo) and ship only mapping logic/tools.
- Record the recipe (prompts, model names, Blender script, settings) in the repo, but not the images, so results are reproducible by someone who owns the ROM.

## Option D: HD-2D look (Octopath-Traveler style) - added 2026-10-10, late evening (same knowledge state as above; THEORY, NOTHING TESTED)
Idea from the user. Assessment (Claude, expectation not result): probably the most pragmatic route to a "modern look", better suited than a full voxel remake.
- **What it is**: 2D sprites standing in a 3D scene; the look comes from lighting and camera: tilt-shift/depth of field, bloom, dynamic lights + shadows, particles, water/fog shaders. No 3D character models needed.
- **Why it fits Landstalker**: the game is already isometric and has real heights (height map `g_HeightMap $FFD192`, entity x/y/z) = a ready-made **depth buffer** for depth of field, shadows and lights. Art effort is far smaller than a voxel remake: HD sprites for characters/enemies/items + new textures for the room blocks; animations stay 2D (about the original frame counts). Sprites from the Blender pre-render / Magnific pipeline (section above) can feed this directly.
- **Stages** (each gives a visible result, each builds on the previous):
  1. **Effects only on the existing picture**: own GPU renderer (Option B step 1-2, state-driven) adds depth of field, light, bloom, shadows over the isometric image, depth from height map + entity positions. Smallest step.
  2. **Replace sprites and blocks with HD versions** (Option A), still in the original isometric view.
  3. **Real 3D scene with camera**: rooms as geometry from height map + blocks, sprites as billboards (this is the actual HD-2D look; overlaps with Option C but without 3D characters).
- **Hard part**: the original block art is pre-drawn isometric pixels. Real 3D geometry needs separate top and side textures per block; the finished pixel blocks cannot simply be re-projected -> redraw or generate them. Stages 1 and 2 avoid this problem.
- **Open questions**: how to derive a per-pixel depth for the existing isometric picture (per block from the map + per entity from z, ordering of overlapping sprites as the game does it - see sprite priority in the VDP); whether sprites and planes can be separated cleanly in the renderer; performance of the effects on the Deck.
- **Legal notes**: same as the asset pipeline section (personal use vs. distribution).
- **Order in the recommended plan**: after step 3 of "Recommended order" (state-driven "what is on screen" model) - stage 1 can start as soon as that model exists.

## Rules for the future own renderer: alignment and byte access (2026-10-15, dev b252139)
Evidence: the clang (zig cc) release build crashed (SIGSEGV, aligned vector load) because GPGX defines `vram` with `ALIGNED_(4)` but declares it without alignment (LESSONS 9.35, `tools/patch_align.py`). When pixel / tile code is written ourselves:
1. State an alignment ONCE, in the header declaration every file sees (`alignas` / `_Alignas`), never only on the definition.
2. No casts of byte arrays to wider pointer types (`uint8*` -> `uint32*`); use `memcpy` or byte reads (same speed after optimisation).
3. Keep the byte-order trick (`o ^= 1` under LSB_FIRST) in ONE accessor function.
4. Compare every new renderer change on BOTH compilers (gcc build and the zig build of `firstrun.py`) with RAM dumps / screenshots, and try a `-fsanitize=undefined` test build (not done yet).

## Answers to the open questions (2026-10-17, dev; see FORMATS.md 'Sprite upload' and 'Screens without a room')
 * Sprites: VRAM slots are dynamic per game pass; the stable key is (SpriteGraphic +0B, AnimationIndex +24, AnimationFrame +26), measured on two replays (`tools/spritetrack.py`). Tile bases move only at room loads / text boxes.
 * Island map, logos, title, menus: self-contained screens with ROM assets, no room map; keep them on the VDP path. Intro story rooms are normal rooms.
 * Consequence: Option B (state-driven renderer) only has to cover 'a room is loaded and no text box / menu owns the screen'; the room number / game state tells which.

## Evaluation of the `*_ref` repos and the 3D room question (2026-10-24, Sonnet 5.5, user: 'wie generieren wir den 3d raum? repos kiln / loom / pxl / vex in ~, evaluieren'; THEORY + repo reading, nothing run)
All four are MIT, written by the same author (uilianks; pxl = fork of crsolver/claude-pxl), JavaScript DSLs for AI agents, **Node >= 22.18 + `npm install` needed (node / npm / Blender are NOT installed on the Deck; network to nodejs.org / npm works)**. They are OFFLINE asset generators (files out: PNG / GLB / GIF), none of them is a runtime. Assets stay local (repo rule: no generated assets in git), only recipes / mapping logic go to the repo.
- **kiln** (low-poly / voxel 3D as code, GLB export, `terrain()` from a heightmap, `voximg()` pixel PNG -> voxels, point / spot lights, Blender renders optional): useful LATER for 3D props (torches, chests, crates, trees, pillars) as replacement objects; needs a GLB loader in C (cgltf, MIT, single header). NOT useful for the room itself (that comes from the ROM's height map / blocks, we have the decoder). Value now: medium-low.
- **loom** (seamless PBR textures: albedo, normal, height, roughness, ORM, emissive): good for HD floor / wall materials (stone, grass, wood, water) with REAL normal maps, which our real lights could use; style risk (smooth procedural vs hand-dithered pixel art; pixelate / palette-quantize). Value: medium for stage 2 (HD blocks), none for stage 1.
- **pxl** (pixel art as code): its `image()` op quantizes any PNG (e.g. a render) to a palette with dither, `pxl lint` flags orphan pixels / jaggies; `lighting.md` is a 2D light grid (we have our own lights). Value: low, maybe as the 'make HD renders look like pixel art' step.
- **vex** (vector art + skeletal animation, atlas + JSON): HD sprites would mean hand-coding 100+ characters with 4 directions and many frames: far too much art work for the gain and a style break. Better for sprites: scale the originals (Scale2x pack exists) or an upscaler. Value: low.
**How to get the 3D room (proposal, needs the user's OK):** no asset generation is needed for a first version. The room is already two full layer pictures (BG = floor, FG = things standing on it: walls, trees, pillars; `lk_o_pa / pb`, S3.1 decoder) plus a height map. (1) FLOOR = geometry from the height map (one top quad per cell at its height, wall faces between different heights), textured with the ORIGINAL picture by PROJECTIVE texturing from the original camera: a surface point's texture coordinate is simply its screen position in the 1x picture, so from the original camera the result is pixel identical to today and a small camera tilt / rotation (the Octopath camera is mostly fixed anyway) only stretches the picture a little. (2) FG things = vertical cut-out CARDS (billboards) standing on their cell, sorted by ground depth, exactly like HD-2D draws trees and houses. (3) Sprites (Nigel, enemies, NPCs) = billboards as now. (4) Rendering: orthographic is affine, so `SDL_RenderGeometry` (SDL 2.32 here) with textured triangles and depth sorting is enough for a first version, no OpenGL context needed; real depth / shadows / lights then come from the geometry (the depth map we fake today becomes exact, lights get real normals). Unknowns to check first: how well the FG / BG split matches objects with their own height (tall walls spanning several cells), what a tilted camera shows behind walls (unseen faces: fill with the nearest picture colour), sorting of overlapping cards, speed on the Deck. First experiment (small): one room (e.g. 592 Massan or the shrine 177) built as height-map floor + FG cards, drawn with a camera that tilts 0 -> 15 degrees, headless screenshots; judge by eye. Assets (loom materials, kiln props, HD sprites) only come after this works.

### RESULT of the first 3D room experiment (2026-10-24, room 592 Massan, `tools/room3d_proto.c` + `lk_o_roomdump` in `tools/patch_own.py`; headless, offline, judged by eye)
**It works: the proposal above (height field + projective texturing from the original picture + card strips) gives a convincing 3D Massan.** Seen from the original camera the render is the original picture (same pixels, only the cards / gaps differ); turned by 20..30 degrees and tilted by +-15 degrees the houses become real 3D blocks (roofs, walls, doors keep their art), fences, cliffs, paths and the stone steps sit at their heights, trees stand as upright cards.
- **Key finding: the height map holds REAL heights for blocked cells too** (`$FFD192`, low nibble of byte 0 = height in 16 unit steps; `$40` bit only means blocked): the houses of Massan are columns of height 3 (48 units), the cliff plateaus 10..11, the rampart fence 4, so the whole room is a true height field (houses, cliffs, fences included) and only void cells (`$4000`) are empty. The image position of a surface point is `U = wx - wy + 1184`, `V = (wx + wy) / 2 - z` (checked: the picture is reproduced).
- **Method as built:** top quad per non-void cell at its height, east / south side quads where the neighbour is lower (void neighbours = down to -400), back faces darkened (optional), z-buffer; pass 1 renders the height field from the original camera into a coverage + hit-position buffer; every opaque picture pixel NOT covered (roof ridges, trees, tops of fences, water) becomes a one pixel wide strip that stands on the surface point just below it (runs >= 110 px are laid FLAT instead: water / far cliff tops), strips keep the original right axis so neighbours join into cards. Orthographic camera = the original isometric view (pitch 35.26 degrees, x scale sqrt 2) + yaw + pitch offsets; 0.1 s for a 1400 x 900 frame including loading (CPU, unoptimised; the scene is ~1000 cells + ~500 strips = a few thousand triangles, easy for the GPU).
- **Known flaws:** (1) objects that are not box shaped but sit in blocked cells (the stone statue in Massan = a column of height 3) look wrong when turned (their picture is painted on a box); (2) runs of 100 px or less at the water edge become upright walls (dark diagonal gaps in the water); (3) back faces / void cliff sides show the picture behind (no real texture there: darkened or unseen); (4) strips are fixed to the original axis = cards turn edge-on at +-45 degrees yaw (keep the yaw range small, Octopath does); (5) no sprites yet (Nigel, NPCs would be billboards at their position, needs their pixels); (6) the room edge / far cliff has no geometry beyond the map.
- **Next steps (not done):** per room tuning of the flat / upright rule (water by tile type), a card with one anchor per object (connected components) instead of per column, the sprites as billboards with real depth, then feed the GPU (`SDL_RenderGeometry`: textured triangles, depth sorted; or an OpenGL pass) and the lights / shadows from the geometry; HD replacements (loom floors, kiln props) only after that.
- **Test aids:** `LANDSTALKER_ROOMDUMP=<dir> LANDSTALKER_ROOMDUMP_ROOM=<n> [LANDSTALKER_ROOMDUMP_FRAME=<f>]` writes `layerA.rgba`, `layerB.rgba` (2432 x 1216, alpha 0 / 1 / 2 = transparent / low / high priority), `heightmap.bin`, `player.bin`, `info.txt` once the room is shown (replay: `docs/replays/massan_waterfall_death.txt`, room 592 = frames 961..1320, dump at 1200); `cc -O2 -o room3d room3d_proto.c -lm; ./room3d DIR out.png yaw pitch_delta scale [nb]` (flags n = no cards, b = no back faces). The dumps and the renders are ROM derived: keep them outside the repo (`~/lt/d592`).

**Update the same day (user: 'doppelte Daecher und Statue?'):** roofs were never doubled (checked in enlarged crops), the stone statue WAS (and its lower half smeared over the ground when turned). Causes and fixes in `tools/room3d_proto.c`: (1) the two layers of the dump separate cleanly: **layer A = objects** (houses, trees, fences, the statue, as clean cut-outs), **layer B = ground** (floors, cliffs, water; holes only under houses). The ground faces are now textured from layer B only (soil colour where B has no picture, top faces only), box columns (blocked cells) from the composite picture; (2) isolated single cell columns (the statue) are PROPS: they take the ground height around them and are drawn as cards (flag `p` keeps the old box); (3) a card pixel = an opaque picture pixel that the box geometry does not carry: uncovered, or a layer A pixel on plain ground; its anchor is the ground point at the FOOT of the run (hit of the lowest pixel), strips are 1.35 pixels wide so that turned cards have no seams; (4) one depth per card = the median anchor depth of its tall runs (>= 8 px; grass tufts at the foot do not count), the anchor moves along the view ray so the original-camera picture does not change (first tries: depth of the cell centre = bars when turned, depth per component incl. decals = no effect). Result (Massan, yaw -25, pitch +5): one statue, one roof per house, trees as cards. Still open: the water bands (runs < 110 px), soil colour patches where a house stood on missing ground, no sprites yet.
