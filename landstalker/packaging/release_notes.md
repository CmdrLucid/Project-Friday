**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- **Native Pace (new option, Options > Quality of Life, default Off):** busy rooms no longer run in slow motion (e.g. the swamp shrine). The picture waits for the game instead of the game losing a frame like on the console.
- **Own timing model:** line / frame clock, interrupts, VDP, Z80 bus and pad timing are now our own code instead of the emulator core's (the game plays exactly as before).
- **Own sound chips:** the PSG and YM2612 sound now come from our own cores (sound identical to before).
- **Smoother picture with CRT Pro:** the filter got much cheaper, the micro stutter on long walks is gone.
- **Friday's wake-up flash** is visible again with the own renderer.
- Everything from v1.2.0 is included.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256: AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
