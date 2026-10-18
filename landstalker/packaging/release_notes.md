**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- New: **Own Renderer** (Options > Video, default Off, experimental): the picture is drawn from the ROM data instead of the console's video memory (rooms, figures, HUD, text, effects). The groundwork for shadows, lighting and texture replacement.
- Fix: micro stutter in desktop mode on the Steam Deck (the controller driver blocked the game for ~8 ms every 3.4 s).
- Fix: Start menu: no blue band when closing, widescreen / full height margins no longer come back late.
- Fix (own renderer): NPCs and chests no longer jump, HUD fade-in, falling stones of the Statue of Gaia, signs at the bottom edge.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256: AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
