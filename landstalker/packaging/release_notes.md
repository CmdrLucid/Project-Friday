**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

**You need your own legal Landstalker ROM.** Nothing from the game is included in these downloads and nothing generated from it. On the first start the program asks for your ROM, checks it, and builds the game on your own computer (about 1 to 5 minutes, up to 25 on slow machines, one time only). The ROM is checked at every start. The ROM must be a raw 2 MB `.md` / `.bin` / `.gen` dump with SHA-1 `24345e29427b000b90df778965dd8834300a9dde`.

### What is new in {VERSION}
- **Key bindings** for pad and keyboard: Options > Keybindings (Button A / B / C, Start, Quick 1 / 2, Quick Save / Load, Fast Forward, Fullscreen, Coordinates); the quick item letters in the HUD follow your choice.
- **De-Dither** rebuilt (Options > Video: Light / Medium / Strong): smooths the dither noise of water, grass and carpets, keeps sprites, outlines and text sharp.
- **Options:** new *Quick Save* switch (off by default), Enemy HP down to 50 %, *Quit Game*, scrolling lists with the game's own arrows, golden frames centred on the text.
- README: list of compatible ROMs (currently only the US version).

### Steam Deck / Linux x86-64: `Project-Friday-x86_64.AppImage`
1. Download it and make it executable (`chmod +x`, or right-click > Properties > Permissions > allow executing).
2. Start it. A file dialog asks for your ROM, a progress bar shows the build. Afterwards it starts the game directly.
3. Add it to Steam via "Add a Non-Steam Game" for Game Mode.

Needs `python3` and the system SDL2 library (both present on SteamOS and most desktop Linux). The built game, settings and the remembered ROM path live in `~/.local/share/project-friday` (delete the folder to start fresh).

### Windows 10 / 11 (64 bit): `Project-Friday-windows-x64.zip`  (experimental: please report problems)
1. Extract the **whole** zip file to a folder (for example on the desktop), do not run it from inside the zip.
2. Double-click `Project-Friday.exe`. A file dialog asks for your ROM; the first build prints its progress in the console window.
3. Afterwards the same exe starts the game directly.

Everything needed (Python, C compiler, SDL2) is inside the zip, nothing to install. Windows SmartScreen or a virus scanner may warn about the unsigned program ("More info" > "Run anyway"). The built game, settings and the remembered ROM path live in `%LOCALAPPDATA%\Project-Friday` (delete that folder to start fresh).

### Checksums (SHA-256)
- AppImage: `{SHA256}`
- Windows zip: `{WSHA256}`

(built by GitHub Actions from the tagged source, see the workflow run).

### Notes
- Tested on a Steam Deck. The Windows package was checked by running the cross-built game headless under Wine (identical game state to the Linux build) but is new on real Windows PCs; ARM is not available.
- Non-commercial use only (Genesis Plus GX and Musashi licences). The packages contain the complete source of all parts and the licence texts (`usr/share/licenses/project-friday` in the AppImage, `licenses` in the zip).
- The code is written by Claude (AI) and tested by the project owner by playing; see the README ("How AI is used in this project").
- Do not share the built game or your ROM.
