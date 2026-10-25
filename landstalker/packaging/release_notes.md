**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- **Windows: the first build from your ROM works again.** v1.0.0 stopped at the last compile step (162 / 163) on Windows because two places used a Linux-only form of `mkdir` (GitHub issue #3, thanks for the log!). Nothing changes for Steam Deck / Linux.
- Everything from v1.0.0 is included: Quick Equip (hold R2 + direction), Better Menu (B in Use / Equip goes back to the bar), Live Gaia Effect, Widescreen Off / 16:10 / 16:9 in any width, defaults 16:9 + Full Height + CRT Pro, the own renderer always on, and the AppImage first-start fix.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256: AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
