# Mod layer (since 2026-11-22)

User wish (2026-11-22, GitHub #18): natives correct texts without editing our JSON, on a **mod layer** that later takes more layers
(character names, light shapes, ...). Rule from the user: **no local server on the player's computer** - the editor is a page opened from the disk.

Player guide (English, linked from the README and the release notes): `MOD_WORKSHOP.md` in the repository root. Keep it in step with this file.
Removing a mod file: langbuild writes `<out>/<code>.modded` when it builds a language WITH a mod; `modlayer.py sync` rebuilds a language whose `.modded` marker has no mod file any more (else the modded texts stayed after the player deleted the file).

## Where mods live (v3 2026-11-22 night; user rule: NOTHING outside the Project-Friday folder, never place or fetch files elsewhere on a player's computer)
- Windows ZIP: `<unzipped folder>\Mods\` - Windows installer: `<install folder>\Mods\` (`%LOCALAPPDATA%\Programs\Project-Friday`; the
  uninstaller's `RMDir "$INSTDIR"` leaves a non-empty folder, so the mods stay) - AppImage: `Project-Friday Mods` NEXT TO the AppImage file
  (its own folder is a read-only mount; user choice) - Deck dev build: `landstalker/Mods/` in the repository (git-ignored).
- firstrun.py sets `LANDSTALKER_MODS` from `modlayer.mods_for_app(HERE)`; without it `modlayer.mods_dir()` = `<tools>/../Mods` (dev).
  The folder is created only when the game starts. Updates and rebuilds never touch the mod files.
- Inside: `Mod Workshop.html` (the editor, ONE file with all its data) and `lang/` (the mod files).
- **Why one file:** the Deck's browsers are Flatpaks; opened with a double click they may read ONLY the opened file (Firefox: document
  portal, Chrome without the folder's permission), so v1's `workshop/data.js` next to the page was 'missing' although it existed. The page
  is rewritten by every start when an input changed (our language files in an update, the page template, the mods): never edited by hand.
- History: v1 (hidden `<data>/mods`) and v2 (`Documents/Project-Friday Mods` + pickup from Downloads) were never released; v2 was removed
  at once (user: no files placed / moved outside the Project-Friday folder unasked).

## Layer 1: language
- `mods/lang/<code>.json` = ONLY the changed texts, in the blocks of `lang/<code>.json`, as plain strings
  (`strings` / `names` / `item_dialog` / `map_areas` / `ui_text`). Format: `tools/modlayer.py`.
- `tools/langbuild.py` mixes them in for every build (also `--only <code>`, ~3 s). A text that breaks the rules (codes other than the
  layout codes changed, unknown `{code}`, missing brace) is REFUSED and the entry keeps its current translation (never English);
  refused texts go to `mods/lang/<code>.report.json`.
- `firstrun.py` (release packages): at every start `tools/modlayer.py sync ROM lang out/lang` = rebuild every language whose mod file is
  newer than its built file + `tools/modpage.py` (rewrites the page only when an input changed: stamp in line 2).
  On the Deck (dev): `build.sh` runs `modpage.py` after langbuild; the dev launcher `~/Landstalker.sh` runs
  `python3 tools/modlayer.py sync ROM lang build/lang` before every start (since 2026-11-22, user OK; backup `~/Landstalker.sh.bak3`).
- The page holds the original English decoded from the user's OWN ROM (reference column): local only, never in git / packages.

## The page (tools/modpage.html)
Every language lists EVERY moddable entry (2026-11-22, user: English (JP) showed empty filters, it translates only dialogue): names / ui_text =
the keys any language translates, map_areas = langbuild.MAP_AREAS (English column from there), strings = all ROM strings; an entry the language
does not translate shows 'original English' / 'not translated' and takes a mod text like any other (checked: en_tone mod with menu / item /
map area / option -> 3 names + 1 ui text more). Filters without entries for the language are hidden (Items in dialogue: only ru / uk / ko;
Friday hints: not for English / English (JP)).
Left: navigation of the mod layers (Language; Character names = layer 2 since 2026-11-22 evening; user 2026-11-22: nothing else is mentioned yet). Item names warn when longer than the ru / uk item menu allows (2 rows of 9 letters, else empty there). Right: language, filter (all / my changes /
not translated / per block), search, table Id | Original (English) | Current text | New text. Codes are checked while typing
(same rule as langbuild `mod_check`), the build's refused list is shown in red. Unsaved edits stay in the browser (localStorage).
Save: Chrome / Edge write `lang/<code>.json` into the page's folder (File System Access API, the folder chosen once per visit; a warning when
its name is not the mods folder's); Firefox downloads `<code>.json` and the page says where to move it (user: no automatic pickup). Import: a mod file somebody sent (texts become unsaved edits to check).
Sharing back: the modder sends the file (GitHub issue), we merge it into `lang/<code>.json`.

Friday hints: block `friday` {hint id: gentle text} (the level the game shows); fr / es / it / ru / uk / ko come from the language file anyway, de (compiled into the program) takes a file hint when the mod has one (patch_friday.py); English is not moddable (the original).

## Layer 2: character names (2026-11-22, user: per language, Names = Localized only)
- Block `charnames` {lang/names.json key: name} in the SAME mod file `mods/lang/<code>.json` (one file per language, so sync / `.modded` / the reverse path work unchanged; own navigation entry on the page, not an own folder).
- `tools/langbuild.py` build_one: for the local variant the modded names replace `names.json[key][base]` before the `{=name}` placeholders are resolved (dialogue, ui_text, Friday hints incl. her name prefix); the `.jpn.bin` variant (Names = Japanese) is untouched.
- Checks: `mod_check` (key known, no `{ } |`, no outer spaces, at most `NAME_MAX` = 12 letters; the page checks the same) + `names_trial`: builds the language without / with the names (stdout muted, ~1 s each) and refuses every name that adds dropped texts (letters the language's font lacks, e.g. 'ä' in Russian) -> the report shows 'has letters the game cannot show in this language'.
- Longer names: the line breaks were made for ~6 letters (langwrap NAMEW); the runtime word wrap LK_LGWRAP v1 breaks a line that gets too long, so a long name may only add a line.
- Tested headless 2026-11-22: de nigel = Siegfried -> de.bin +1056 bytes (4 letters x 2 bytes x 132 uses), de.jpn.bin identical; ru 'Fräulein' / '{x}' / unknown key refused; mod deleted -> `modlayer sync` rebuilt de byte-identical to the plain build; page (Chrome headless, lone copy) shows 23 names, refused ones red.

## Later layers (ideas)
Only after the user asks (not listed on the page).

## Test without a folder permission (lesson 2026-11-22 night)
v1 was tested with `flatpak run --filesystem=DIR com.google.Chrome ...` on the mods folder itself: that permission hid the missing sibling file.
Test a copy of the page ALONE in a scratch folder (`~/Project-Friday-Test/lktest/<topic>/alone/`, `--filesystem` on that folder only), `--headless=new
--disable-gpu --virtual-time-budget=8000 --dump-dom FILE` with an injected script: stub `showDirectoryPicker` with a fake handle (folder path) and
set it undefined (download path).
