**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### The last big update before v2.0
**This is the last release with major new features before v2.0. From now until 2.0 the work is polishing: optimising, fixing and improving what is there. So this is the best moment to try everything and tell me what you notice (Issues or Discussions on GitHub), especially about the translations and about Windows.**

**New since v1.9.1:**
- **Landstalker in your language** (new options page Language / Region):
  - **Deutsch:** every line of dialogue, with the names of the original German release (Niels, Flora, Merkator, ...) and the intro captions of the German release.
  - **English (JP):** every line rewritten in the tone of the Japanese original (its jokes, the characters' voices, the scenes the Western release toned down).
  - **Français** and **Korean:** translated in the Japanese original's tone (Korean with the Galmuri font, including the options menu).
  - **Japanese:** the original Japanese text, available as soon as you put your own Japanese ROM in the same folder as your ROM (nothing of it is in the download).
  - **Names:** localized or the Japanese original names. **Items:** the four items that are different things in the Japanese original (needs the Japanese ROM in the same folder too).
  - **Title screen:** the subtitle in your language.
  - **Bath Scene** (on by default): restores the scene in Kayla's room that the Western releases block with a maid at the door. **Not tested in play yet** - it needs a save from before the banquet in Mercator castle. If you get there, please tell me whether it works.
  - The translations were written with Claude and not all have been read by native speakers yet: corrections are very welcome.
- **Friday Hints** (now on by default): press Select and Friday tells you where to go next. The hints follow your progress, only mention what Nigel has actually been told, and get more precise when you listened to an optional character. In every language.
- **Dungeon map, redesigned** (now on by default: right stick click R3, keyboard M): turned like the game's view, the whole floor at once, a selection on the D-pad, A sets a flag and the map shows the way there, L1 / R1 switch floors. Fullscreen moved off R3 (F11 / Alt+Enter stay).
- **Night lights:** windows, doors and church glass glow at night in Massan, Mercator and Destel, with light falling out of the open doors; fireflies give off a faint glow.
- **Light and shadows:** groups of pine trees cast one shadow per tree, more furniture with real 3D shapes, fewer stray light edges.
- **Sprint:** sprinting through doors keeps the speed, and the sprint no longer switches the light off.
- **De-Dither** is back on the Display page (Filter). It now runs on the graphics chip and keeps the HUD sharp.
- **Keyboard:** the directions can be remapped too; one row switches to W A S D.
- **Fixes:** after the priest's "continue? no" the file select shows the save slots again (#20); item info shows the right text after scrolling (#17); big figures (the boulder in the castle basement) no longer get light streaks; Yes / No choices in Korean and Japanese.
- Everything from v1.9.1 is included. Your settings and save files from v1.x keep working.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM). The first start of a new version builds the game once (a few minutes).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`). If the picture looks wrong, switch Lighting off in Options > Graphics and please let me know.

SHA-256 (to check your download, no extra file needed): AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).
