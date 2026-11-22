# Mod layer (since 2026-11-22)

User wish (2026-11-22, GitHub #18): natives correct texts without editing our JSON, on a **mod layer** that later takes more layers
(character names, light shapes, ...). Rule from the user: **no local server on the player's computer** - the editor is a page opened from the disk.

## Where mods live (v2 2026-11-22 night, user: the hidden folder was not user friendly)
- Linux / Steam Deck: `~/Documents/Project-Friday Mods/` (the XDG documents folder) - Windows: `Documents\Project-Friday Mods\` (known folder, also on OneDrive)
- Inside: `Mod Workshop.html` (the editor, ONE file with all its data) and `lang/` (the mod files). `LANDSTALKER_MODS=<folder>` overrides (tests).
  Updates and rebuilds never touch the mod files. The v1 folder (`<data>/mods`, hidden) is moved once by `modlayer.py migrate()`.
- **Why one file:** the Deck's browsers are Flatpaks; opened with a double click they may read ONLY the opened file (Firefox: document
  portal, Chrome without the folder's permission), so v1's `workshop/data.js` next to the page was 'missing' although it existed.
- **Saving without finding a folder:** the page always saves a DOWNLOAD `Project-Friday-mod-<code>.json` (every browser, no folder
  permission); the next start (`modlayer.py sync` in firstrun.py, `modlayer.py pickup` in build.sh) moves it from the Downloads folder into
  `lang/<code>.json` (newest copy per language wins, `... (1).json` copies are removed; only files with `meta.code` + `format` 1 are touched).

## Layer 1: language
- `mods/lang/<code>.json` = ONLY the changed texts, in the blocks of `lang/<code>.json`, as plain strings
  (`strings` / `names` / `item_dialog` / `map_areas` / `ui_text`). Format: `tools/modlayer.py`.
- `tools/langbuild.py` mixes them in for every build (also `--only <code>`, ~3 s). A text that breaks the rules (codes other than the
  layout codes changed, unknown `{code}`, missing brace) is REFUSED and the entry keeps its current translation (never English);
  refused texts go to `mods/lang/<code>.report.json`.
- `firstrun.py` (release packages): at every start `tools/modlayer.py sync ROM lang out/lang` = migrate + pickup + rebuild every language
  whose mod file is newer than its built file + `tools/modpage.py` (rewrites the page only when an input changed: stamp in line 2).
  On the Deck (dev): `build.sh` runs `modlayer.py pickup` before langbuild and `modpage.py` after it; the dev launcher `~/Landstalker.sh`
  does NOT sync at start (run `python3 tools/modlayer.py sync ROM lang build/lang`, or build.sh).
- The page holds the original English decoded from the user's OWN ROM (reference column): local only, never in git / packages.

## The page (tools/modpage.html)
Left: navigation of the mod layers (Language; Character names shown as "(later)"; user 2026-11-22: nothing else is mentioned yet). Item names warn when longer than the ru / uk item menu allows (2 rows of 9 letters, else empty there). Right: language, filter (all / my changes /
not translated / per block), search, table Id | Original (English) | Current text | New text. Codes are checked while typing
(same rule as langbuild `mod_check`), the build's refused list is shown in red. Unsaved edits stay in the browser (localStorage).
Save: a download `Project-Friday-mod-<code>.json` in every browser (v1's folder picker removed), picked up at the next start. Import: a mod file somebody sent (texts become unsaved edits to check).
Sharing back: the modder sends the file (GitHub issue), we merge it into `lang/<code>.json`.

Friday hints: block `friday` {hint id: gentle text} (the level the game shows); fr / es / it / ru / uk / ko come from the language file anyway, de (compiled into the program) takes a file hint when the mod has one (patch_friday.py); English is not moddable (the original).

## Later layers (ideas)
Character names (`lang/names.json`) next; later layers only after the user asks (not listed on the page) - each its own block of the navigation and its own folder.

## Test without a folder permission (lesson 2026-11-22 night)
v1 was tested with `flatpak run --filesystem=DIR com.google.Chrome ...`: that permission hid the bug. Test the page as the player opens it:
a copy ALONE in a folder the browser may read without extra permission (`~/Downloads/<test>/`), `flatpak run com.google.Chrome --headless=new
--disable-gpu --virtual-time-budget=8000 --dump-dom FILE` with an injected test script, and `flatpak run org.mozilla.firefox --headless --screenshot`.
