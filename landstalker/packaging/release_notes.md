**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux PC.**

**You need your own legal Landstalker ROM.** Nothing from the game is included in this download and nothing generated from it. On the first start the program asks for your ROM, checks it, and builds the game on your own computer (about 1 to 5 minutes, up to 25 on slow machines, one time only). The ROM is checked at every start.

### How to use (Steam Deck / Linux x86-64)
1. Download `Project-Friday-x86_64.AppImage`, make it executable (`chmod +x`, or right-click > Properties > Permissions > allow executing).
2. Start it. A file dialog asks for your ROM (a raw 2 MB `.md` / `.bin` / `.gen` dump, SHA-1 `24345e29427b000b90df778965dd8834300a9dde`). A progress bar shows the build.
3. Afterwards it starts the game directly. Add it to Steam via "Add a Non-Steam Game" for Game Mode.

Needs `python3` and the system SDL2 library (both present on SteamOS and most desktop Linux). The built game, settings and the remembered ROM path live in `~/.local/share/project-friday` (delete the folder to start fresh).

### Checksum
SHA-256 `{SHA256}` (built by GitHub Actions from the tagged source, see the workflow run).

### Notes
- Tested on a Steam Deck only; Windows and ARM are not available yet.
- Non-commercial use only (Genesis Plus GX and Musashi licences). The package contains the complete source of all parts and the licence texts (`usr/share/licenses/project-friday`).
- The code is written by Claude (AI) and tested by the project owner by playing; see the README ("How AI is used in this project").
- Do not share the built game or your ROM.
