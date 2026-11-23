**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### Language fixes and clearer menus
**New since v1.9.12:**
- **Languages (GitHub #18):** on-screen messages (quick save, fast forward, the key messages for Fullscreen / Scale / Filter / Widescreen ...), the quick-equip overlay and 'Preparing lighting' now appear in Russian, Ukrainian, Korean and Japanese too (before: English), and long messages fit the window (also in German). The translated title stays during the fade-in and after START. 'Modern', 'HUD', the language names (Русский, Українська, ...) and a few more menu words are translated in every language; small fixes found by a check of every menu line in every language (Ukrainian On / Off, French / Spanish / Italian Oui / Sí / Sì, Italian accents, Korean item names, ...).
- **D-Pad help line fixed:** Options > Movement > D-Pad sometimes showed the Widescreen help.
- **Clearer Start menu:** item descriptions (Item Info) and option help lines fill the bar alone and centred, without the menu words and the divider line; the words come back when the cursor is on the bar.
- **Start screen options:** the bar under the options window shows the help line of the selected setting, like the in-game menu.
- **Mod Workshop:** every menu text the game uses is offered (before, texts no language had translated yet were missing, e.g. 'Modern').
- Your settings, save files and mods keep working.

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
