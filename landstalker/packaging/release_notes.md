**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- **Quick Equip** (Options > Quality of Life, On by default): hold R2 (keyboard Q) and press a direction - up sword, right armour, down boots, left ring. The first press only shows the pieces of that kind (icons, owned ones in colour, others as black silhouettes), the second press switches; the starting equipment (Broad Sword, Leather Breast, Leather Boots, no ring) is part of the cycle. The game pauses while R2 is held. Fast Forward moved to R5 by default.
- **Better Menu** (Options > Quality of Life, On by default): B in the Use list or the Equip grid goes back to Use / Equip / Options instead of closing the whole menu; START still closes it.
- **Live Gaia Effect** is On by default: the falling rocks no longer freeze the game and stay in the world; no second Gaia use while they fall.
- **Widescreen in any width**: Options > Video > Widescreen is now Off / 16:10 / 16:9 (any width works, no longer multiples of 16 only). New defaults for a fresh install: 16:9, Full Height On, CRT Pro, Scaling Fit, Map Behind Text On.
- The own renderer is always on (its Options row is gone); the HD Graphics and De-Dither rows are hidden for now.
- Fixes: figures are hidden behind the text box like on the original hardware (dwarves), the ending credits are visible again, shadows (no pop-up after the Start menu, every platform casts one, Nigel's ground), two stray grey pixels in the HUD bar next to the gold, Options page hang with LEFT on some rows, and **the first start from the AppImage** (a missing file made the first build fail on a clean system).
- Everything from v0.9.6 is included.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256: AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
