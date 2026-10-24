# remake/ - the Landstalker remake (3D, own assets)

Goal: the whole world as real 3D models with PIXEL textures in the style of the original (1 texel = 1 game pixel, nearest sampling, stepped light); only the figures stay sprite billboards.
The recompiled game (`landstalker/`) stays the LOGIC CORE; the remake draws its state (plan: docs in `landstalker/docs/RENDERER_IDEAS.md`, 'Godot front end'). Logic changes are allowed in the remake only, as switchable hooks; with the remake off the original stays bit exact.

## Rules
- Assets are made ONE AT A TIME and shown to the user for approval before they are placed (the user's wish 2026-10-24). The list and its order: `ASSETS.md`.
- Only RECIPES, helper code and docs live in git. Everything generated (textures, GLB models, previews, room dumps) stays on the user's machine in `~/.landstalker_remake/` and is never committed. Textures are produced by our own generators (no ROM art); room data from the user's own ROM is local too.
- Units: 1 unit = 1 pixel of the original = 1/16 of a map cell; x east, y south, z up (`landstalker/docs/FORMATS.md`, 'Height map = a real height field').

## Tools
- Blender (Flatpak) headless: `python3 remake/tools/build_asset.py <name>` runs `remake/recipes/<name>.py` with `remake/lib/blx.py` (pixel texture generator, mesh builder with planar 1 texel = 1 unit UVs, EEVEE preview renders, GLB export) -> `~/.landstalker_remake/assets/<name>/` (`<name>.glb`, `preview_*.png`).
- Node + kiln / loom / pxl / vex in `~/remake_tools` (INDEX 'remake toolchain') for quick props; Godot comes with the front end.
