**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### Windows installer, lighting fixes and the Japanese ROM check
**New since v1.9.7:**
- **Windows: one installer file.** `Project-Friday-Setup.exe` replaces unpacking a zip: pick any folder (by default your user folder, no admin rights needed; Program Files works too, Windows then asks once for admin rights), Start menu entry, optional desktop shortcut, uninstall in Settings > Apps. The built game and your settings stay in %LOCALAPPDATA%\Project-Friday; save files next to your ROM are never touched. The zip is still offered for now.
- **Striped character shadows fixed** (GitHub #21, thanks paul-met): a memory error in the lighting turned into vertical stripes in the shadows of characters (by sun and by sword light) in the release packages (Windows and AppImage); builds made with gcc happened to hide it.
- **Weak or busy GPU:** when the GPU is too slow for the lighting, a message now says so (LIGHTING OFF: GPU TOO SLOW) and the lighting tries again after 30 seconds (before, it switched off silently until the next start).
- **Gumi and river areas:** Nigel no longer turns dark and loses his shadow on the walkway above the river in Gumi; the lighting had raised the painted river far above its real height (an invisible wall). The same mistake is fixed in about 25 outdoor rooms.
- **Shadows:** groups of pines cast the shadows of single pines in nine more forest rooms; the diamond-shaped box shadow on the forest path below the cliff is gone (three rooms with the same map); Swamp Shrine torch statues give figure shadows again (also after coming from Gumi); no dark box on the wall in the Swamp Shrine; no bright strip on the wall in the Waterfall Shrine; round towers and the evening shade in the Mercator fountain court.
- **Water:** reflections in the Waterfall Shrine pools, cleaner pool rim corners.
- **Effects:** defeated enemies burst apart with the camera instead of drifting sideways while you walk; the wooden platform in the Swamp Shrine stays visible at the top edge in 16:9.
- **Friday Hints:** the Waterfall Shrine no longer sends you deeper for the Idol Stone (it lies in Gumi); the shrine door is mentioned only after you have heard that it is shut.
- **Japanese text and items:** only the known Japanese ROM dump is used (SHA-1 in the README); another file with a Japanese header is ignored with a message instead of giving broken text. As before, just put it next to your ROM, no rebuild.
- **Options:** the *Language / Region* row is translated in every language and keeps the English word, e.g. *ことば (Language)*, so you always find it again after switching to a language you cannot read.
- Gumi skull sign door at night, plus everything from v1.9.7 (Swamp Shrine entrance light, Tibor, map exits, water drops). Your settings and save files from v1.x keep working.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM). The first start of a new version builds the game once (a few minutes).
- **Windows 10 / 11 (experimental):** `Project-Friday-Setup.exe` (installer: pick a folder, start Project-Friday from the Start menu; uninstall in Settings > Apps). Windows may warn that the file is unknown (it is not signed): *More info > Run anyway*. Or the same files as `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`). If the picture looks wrong, switch Lighting off in Options > Graphics and please let me know.

SHA-256 (to check your download, no extra file needed): AppImage `{SHA256}`, Windows installer `{ISHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).
