**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### New in {VERSION}
- **Sprint (new, On by default):** hold R2 (keyboard Left Shift) and Nigel runs faster on the ground; jumps stay exactly as in the original. Options > Quality of Life: Sprint On / Off, Sprint Key Hold / Toggle. The controls moved for it: **Quick Equip is now R1, Fast Forward L3, Fullscreen R3** (all remappable in Options > Keybindings).
- **Smooth Scrolling (new, On by default):** while sprinting the room scrolls evenly at 1.5 x and stays sharp (the scenery is shifted by whole screen pixels inside the display filter, Nigel, HUD and text boxes stay put). Off = sprint 2 x.
- **Fix for the first start on newer Linux (issue #12, Ubuntu 26.10 / Python 3.14):** the build helper module is now installed into the game's own data folder, so distributions that lock the system Python ("externally-managed-environment") work; your system Python is not touched.
- **Experimental, off by default (still being tuned, feedback welcome):**
  - *Friday Hints* (Options > Quality of Life): press Select and Friday flies out of Nigel's bag and gives a hint where to go next, in her own words.
  - *Dungeon map*: bind a button to "Map" in Options > Keybindings. In a dungeon it pauses the game and shows the rooms you have visited, floor by floor, each room drawn from your ROM, with your position.
- Everything from v1.4.0 is included.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`).

SHA-256 (to check your download, no extra file needed): AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).

Non-commercial use only (Genesis Plus GX and Musashi licences, texts and sources are included). Code written by Claude (AI), tested by the project owner by playing, see the README. Do not share the built game or your ROM.
