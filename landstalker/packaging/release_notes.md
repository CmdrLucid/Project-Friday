**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- Own renderer (Options > Video > Own Renderer, still Off by default): the HUD (hearts, health, gold, EkeEke, sword gauge), the dialogue text and the text box frame are now drawn from the game state instead of copied from the game's buffers; the picture of every frame is built from the state the game handed to the video chip (fewer position glitches).
- Fix: with the own renderer the intro captions are white again and the text boxes (statue, dialogues) in the intro and the first cave are visible.
- Everything from v0.9.3 (end credits, Quick Item HUD in fades, stairs of the Stairway to Nole) is included.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256: AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
