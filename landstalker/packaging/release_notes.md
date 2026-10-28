**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- **Language option + German (first part):** Options > Language. Menus, item names, system messages, hints and options are translated; character dialogue is still English for now.
- **Europe ROM supported:** the European Landstalker ROM is accepted too and runs at the right speed (60 Hz).
- **Fast Forward can be a toggle (issue #11):** Options > Quality of Life > Fast Forward Key: Hold or Toggle.
- **No sprite limit (always on):** every figure of a room is drawn, without the cartridge's limit of 20 sprites per line and its flicker (no option row).
- **Native sound (always on):** the sound driver runs recompiled inside the game instead of GPGX's Z80 (audio bit identical to before).
- **Game and sound pause while the window is not in focus (alt+tab, issue #9).**
- **Quick Save and Fast Forward are OFF by default:** turn them on under Options > Quality of Life; pressing their button while off now shows a hint (issue #6). Fast forward: hold Tab / Steam Deck back button R5.
- Everything from v1.0.2 is included (Windows start fix, Quick Equip, Better Menu, Live Gaia Effect, Widescreen ...).

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256: AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
