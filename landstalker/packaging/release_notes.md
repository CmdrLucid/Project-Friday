**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### Fixed since v1.9.11
- **Mods survive updates:** after an update the game was built without the mods already in your Mods folder (your corrected texts were replaced by the plain ones until you saved the mod again). Now the build always uses your Mods folder.

### Language hotfix and the new Mod Workshop: correct texts yourself
**New since v1.9.9:**
- **Russian / Ukrainian file select fixed** (GitHub #18): place names, *New game* and the Yes / No / Copy? / Delete? bar are shown whole. The save slots now follow a language change at once (they kept the old language before).
- **File select in Japanese** (taken from the Japanese original) **and Korean**.
- **Title subtitle in Cyrillic** for Russian and Ukrainian.
- **Russian dialogue revised** (104 lines checked against the Japanese original).
- **Mod Workshop: correct the texts of your language yourself** (see the short guide below). Native speakers: this is the easiest way to send us corrections.
- **Lighting:** the riddle braziers in the crypt now light the room; shadows of figures at the top edge of the screen are no longer cut off.
- Your settings and save files from v1.x keep working.

### Mod Workshop - short guide (full guide: [MOD_WORKSHOP.md](https://github.com/cmdrlucid/Project-Friday/blob/main/MOD_WORKSHOP.md))
1. **Start the game once.** It creates its Mods folder: **Steam Deck / Linux:** `Project-Friday Mods` next to the AppImage file. **Windows:** `Mods` in the Project-Friday folder (installer: in the folder you picked, by default `%LOCALAPPDATA%\Programs\Project-Friday\Mods`; zip: inside the extracted folder).
2. **Open `Mod Workshop.html`** in that folder (double click; Chrome, Edge or Firefox; works offline).
3. **Pick your language**, find the text (search, or a filter: dialogue, names / menus, map areas, items, options, Friday hints) and **type the new text in the right column**. Keep the codes in braces such as `{SoftNewLine}` as in the English text; a text marked red would be refused by the game.
4. **Save.** Chrome / Edge ask once for a folder: choose the Mods folder. Firefox saves `<language>.json` to your Downloads: move it into the `lang` folder inside the Mods folder.
5. **Start the game again:** your texts are in. Updates never change the Mods folder.
6. **Please send us the file** (`lang/<language>.json` in the Mods folder) in a [GitHub issue](https://github.com/cmdrlucid/Project-Friday/issues), so every player gets your correction.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM). The first start of a new version builds the game once (a few minutes).
- **Windows 10 / 11 (experimental):** `Project-Friday-Setup.exe` (installer: pick a folder, start Project-Friday from the Start menu; uninstall in Settings > Apps). Windows may warn that the file is unknown (it is not signed): *More info > Run anyway*. Or the same files as `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`). If the picture looks wrong, switch Lighting off in Options > Graphics and please let me know.

SHA-256 (to check your download, no extra file needed): AppImage `{SHA256}`, Windows installer `{ISHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).
