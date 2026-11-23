**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### Mod Workshop fixes, character names, light and widescreen polish
**New since v1.9.11:**
- **Mod Workshop: rename characters** for your language (left: *Character names*). The new name is used in every text where the character appears (Options > Names = Localized).
- **Mod Workshop: saving in several steps no longer loses texts** (GitHub #18): the page remembers your last save, also when you reopen it before starting the game or before moving a Firefox download into the folder. The search finds a sentence as the game shows it (with character names and line breaks).
- **Mod Workshop is more robust:** a broken or wrongly named mod file (e.g. `ru(1).json`, a second browser download) is shown in red on the page; letters your language's font does not have get an orange hint while you type, and such texts keep the translation instead of turning English; one bad file can no longer stop the game from building its languages.
- **Mods survive updates:** an update no longer builds the game without the mods already in your Mods folder.
- **Widescreen:** map pieces the game keeps outside a room (for example next to the house above the Mercator crypt) and figures parked outside the room are no longer drawn.
- **Lighting:** the Massan statue and the Duke's statue are lit like figures and cast a figure shadow; no more dark stripes in the water at the Mercator docks pavilion; no more thin shadow streaks from the books in the churches.
- Your settings, save files and mods from v1.x keep working.

### Mod Workshop - short guide (full guide: [MOD_WORKSHOP.md](https://github.com/cmdrlucid/Project-Friday/blob/main/MOD_WORKSHOP.md))
1. **Start the game once.** It creates its Mods folder: **Steam Deck / Linux:** `Project-Friday Mods` next to the AppImage file. **Windows:** `Mods` in the Project-Friday folder (installer: in the folder you picked, by default `%LOCALAPPDATA%\Programs\Project-Friday\Mods`; zip: inside the extracted folder).
2. **Open `Mod Workshop.html`** in that folder (double click; Chrome, Edge or Firefox; works offline).
3. **Pick your language**, find the text (search, or a filter: dialogue, names / menus, map areas, items, options, Friday hints) and **type the new text in the right column** (*Character names* on the left: new names for the characters). Keep the codes in braces such as `{SoftNewLine}` as in the English text; a text marked red would be refused by the game.
4. **Save.** Chrome / Edge ask once for a folder: choose the Mods folder. Firefox saves `<language>.json` to your Downloads: move it into the `lang` folder inside the Mods folder.
5. **Start the game again:** your texts are in. Updates never change the Mods folder.
6. **Please send us the file** (`lang/<language>.json` in the Mods folder) in a [GitHub issue](https://github.com/cmdrlucid/Project-Friday/issues), so every player gets your correction.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM). The first start of a new version builds the game once (a few minutes).
- **Windows 10 / 11 (experimental):** `Project-Friday-Setup.exe` (installer: pick a folder, start Project-Friday from the Start menu; uninstall in Settings > Apps). Windows may warn that the file is unknown (it is not signed): *More info > Run anyway*. Or the same files as `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`). If the picture looks wrong, switch Lighting off in Options > Graphics and please let me know.

SHA-256 (to check your download, no extra file needed): AppImage `{SHA256}`, Windows installer `{ISHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).
