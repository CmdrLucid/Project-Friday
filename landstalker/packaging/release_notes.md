**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- **Fast forward keeps the music at normal speed** (the sound runs on its own clock; GitHub issue #11 part 2). Speech blips are thinned so they sound as often as at normal speed.
- **Native sound (always on):** the sound driver runs recompiled inside the game instead of GPGX's Z80 (audio bit identical to before).
- **No sprite limit (always on, no option row):** every figure of a room is drawn, without the cartridge's limit of 20 sprites per line and its flicker. The own renderer got faster at the same time.
- **Shadows fixed:** a shadow no longer lies on a roof or wall in front of Nigel, and no longer goes missing at places on paths / grass; none in the intro rooms and on ladders / vines.
- **Intro fixes:** Enemy HP / Damage Taken settings no longer apply in the intro (with Enemy HP 300 % the golem statues of the third intro scene survived the scripted hit and the intro hung); the third intro scene shows its black scene changes correctly; text boxes are back in all intro scenes.
- **Text box:** figures that the cartridge hides behind a text box (corner, beside the box) are drawn and the box covers them.
- Gaia effect and other sprite effects work again with No Sprite Limit; Europe ROM and the AppImage first run were re-tested.
- Everything from v1.1.0 is included (Language option + German, Europe ROM, Fast Forward toggle, focus pause, ...).

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256: AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
