# Mod layer (since 2026-11-22)

User wish (2026-11-22, GitHub #18): natives correct texts without editing our JSON, on a **mod layer** that later takes more layers
(character names, light shapes, ...). Rule from the user: **no local server on the player's computer** - the editor is a page opened from the disk.

## Where mods live
- Linux / Steam Deck: `~/.local/share/project-friday/mods/` (XDG_DATA_HOME respected) - Windows: `%LOCALAPPDATA%\Project-Friday\mods\`
- `LANDSTALKER_MODS=<folder>` overrides (tests). Updates and rebuilds never touch this folder.

## Layer 1: language
- `mods/lang/<code>.json` = ONLY the changed texts, in the blocks of `lang/<code>.json`, as plain strings
  (`strings` / `names` / `item_dialog` / `map_areas` / `ui_text`). Format: `tools/modlayer.py`.
- `tools/langbuild.py` mixes them in for every build (also `--only <code>`, ~3 s). A text that breaks the rules (codes other than the
  layout codes changed, unknown `{code}`, missing brace) is REFUSED and the entry keeps its current translation (never English);
  refused texts go to `mods/lang/<code>.report.json`.
- `firstrun.py` (release packages): at every start a language whose mod file is newer than its built file is rebuilt; then
  `tools/modpage.py` rewrites `mods/Mod Workshop.html` + `mods/workshop/data.js` when an input changed.
  On the Deck (dev): `build.sh` runs `tools/modpage.py` after langbuild; the dev launcher does NOT rebuild at start (run build.sh, or
  `python3 tools/langbuild.py ROM lang build/lang --only ru`).
- `data.js` holds the original English decoded from the user's OWN ROM (reference column): local only, never in git / packages.

## The page (tools/modpage.html)
Left: navigation of the mod layers (Language; later layers shown as "(later)"). Item names warn when longer than the ru / uk item menu allows (2 rows of 9 letters, else empty there). Right: language, filter (all / my changes /
not translated / per block), search, table Id | Original (English) | Current text | New text. Codes are checked while typing
(same rule as langbuild `mod_check`), the build's refused list is shown in red. Unsaved edits stay in the browser (localStorage).
Save: Chrome / Edge write `mods/lang/<code>.json` into the chosen mods folder (File System Access API); other browsers (Firefox)
download the file with a note where to put it. Import: a mod file somebody sent (texts become unsaved edits to check).
Sharing back: the modder sends the file (GitHub issue), we merge it into `lang/<code>.json`.

Friday hints: block `friday` {hint id: gentle text} (the level the game shows); fr / es / it / ru / uk / ko come from the language file anyway, de (compiled into the program) takes a file hint when the mod has one (patch_friday.py); English is not moddable (the original).

## Later layers (ideas)
Character names (`lang/names.json`), Friday hints, light shapes / remake assets - each its own block of the navigation and its own folder in `mods/`.
