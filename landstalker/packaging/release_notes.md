**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- **Quick Save and Fast Forward are switched OFF by default: turn them on under Options > Quality of Life.** Pressing their button while they are off now shows a hint ('QUICK SAVE OFF - SEE OPTIONS' / 'FAST FORWARD OFF - SEE OPTIONS') instead of doing nothing (GitHub issue #6, thanks for the report!). Default controls: quick save L2 / F9, quick load hold L1 / F10, fast forward hold Tab (on the pad the Steam Deck back button R5; a pad without back buttons: bind one under Options > Keybindings).
- **Windows: the game no longer crashes right after the start (exit code `0xC0000005`, GitHub issue #5, thanks for the report!).** The name of the save file (`.srm`) is now worked out before the emulator core starts. The Windows package is also tested on a real Windows machine by GitHub now (start with a test ROM, with and without a save file). Nothing changes for Steam Deck / Linux.
- Included since v1.0.1: the Windows first-build fix (compile step 162 / 163, issue #3).
- Everything from v1.0.0 is included: Quick Equip (hold R2 + direction), Better Menu (B in Use / Equip goes back to the bar), Live Gaia Effect, Widescreen Off / 16:10 / 16:9 in any width, defaults 16:9 + Full Height + CRT Pro, the own renderer always on, and the AppImage first-start fix.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256: AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
