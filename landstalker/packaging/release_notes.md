**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- **About a third less CPU load** (measured on the Steam Deck: 23.7 s -> 15.1 s for the same 6000-frame test recording): cooler and quieter Deck, longer battery life. The project's own renderer got faster, and the leftover work of the old emulator renderer is gone.
- **Less emulator inside, nothing to see or hear:** the video chip's data path (writes, registers, DMA) and the system start-up now run on the project's own code; Genesis Plus GX's renderer is only kept as a test picture. Every step was checked against the old way on all 74 test recordings (identical game state, sound and picture).
- Everything from v1.6.0 is included (rebuilt dungeon map, Modern HUD life numbers, Sprint, Smooth Scrolling, experimental Friday Hints).

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256 (to check your download, no extra file needed): AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
