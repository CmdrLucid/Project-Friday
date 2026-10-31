**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- **Dungeon map, rebuilt (still experimental, off by default):** bind a button to "Map" in Options > Keybindings. In a dungeon it pauses the game and shows a schematic map of the rooms you have visited: every door sits on the wall the game itself gives it, doors that meet are joined by corridors, the rest carry matching numbers; river / raft passages are drawn blue. Scroll with the D-pad / stick, change floors with **L1 / R1** (shown at the top right).
- **Modern HUD:** the life numbers (e.g. 55/78) are back next to the hearts.
- **Less emulator inside, nothing to hear:** the sound mixer and the Z80's start-up program now run on the project's own code instead of Genesis Plus GX (checked sample for sample against the old way on every test recording).
- Everything from v1.5.0 is included (Sprint, Smooth Scrolling, the first-start fix for newer Linux, experimental Friday Hints).

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256 (to check your download, no extra file needed): AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
