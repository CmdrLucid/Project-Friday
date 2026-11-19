**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### DRAFT for the next release (new since v1.9.7; merge into the text above when tagging)
- **Waterfall Shrine:** no more bright strip on the wall behind Nigel next to the chest (the lighting took a pit for a door and put a floor there). The same fix applies to pits in other caves and dungeons.
- **Friday Hints:** in the Waterfall Shrine Friday no longer sends you deeper for the Idol Stone (it is not there); she points you back to Gumi.
- **Mercator fountain court:** the round towers of the city wall are round for the lighting too, and in the evening the high wall now shades the court.
- **Striped character shadows fixed** (GitHub #21, thanks paul-met): a memory error in the lighting turned into vertical stripes in the shadows of characters (by sun and by sword light) in the release packages (Windows and AppImage, built with zig / clang); builds made with gcc happened to hide it.
- **Weak or busy GPU:** when the GPU is too slow for the lighting, a message now says so (LIGHTING OFF: GPU TOO SLOW) and the lighting tries again after 30 seconds (before, it switched off silently until the next start, which also looked like a jump from night to day).

### Fixes early in the game (polishing before v2.0)
**New since v1.9.6:**
- **Swamp Shrine entrance (room 0):** the torches give light again, the Modern HUD is shown, and the room now gets the same picture fixes as every other room (the Gaia sword effect there should no longer turn the stones green - please tell me if it still does). The room was never handed to the new renderer because of its number 0; this also fixes the sun and the day / night look on the paths after it.
- **Tibor:** the inside of the tree is now drawn by the new renderer too, with light.
- **Map exits:** no more strange dark shadow on the little strip that marks the way into the next area (a pine shadow the lighting placed there by mistake).
- **Friday Hints:** in Gumi Friday no longer talks about a shut shrine door before you have seen it; she now hints that something in Gumi may open it.
- **Water drops:** only in the Waterfall Shrine, the thieves' hideout, the Destel well and the Lake Shrine, and fewer of them (no more drops in King Nole's Cave, the Verla mines, the Swamp Shrine, Tibor, Helga's hut and the small caves).
- Everything from v1.9.6 is included (Alternate D-pad, lithograph text box, first start without pip, ...). Your settings and save files from v1.x keep working.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM). The first start of a new version builds the game once (a few minutes).
- **Windows 10 / 11 (experimental):** `Project-Friday-Setup.exe` (installer: pick a folder, start Project-Friday from the Start menu; uninstall in Settings > Apps). Windows may warn that the file is unknown (it is not signed): *More info > Run anyway*. Or the same files as `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`). If the picture looks wrong, switch Lighting off in Options > Graphics and please let me know.

SHA-256 (to check your download, no extra file needed): AppImage `{SHA256}`, Windows installer `{ISHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).
