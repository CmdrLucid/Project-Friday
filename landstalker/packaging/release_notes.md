**Project-Friday {VERSION} - Landstalker (Mega Drive) recompiled for Steam Deck / Linux and Windows.**

### Fixed in {VERSION}
- **v1.9.0 was built without the new 3D light shapes:** the light data was in the download but the first start did not use it, so furniture, statues and decorations cast the old box shadows. This hotfix includes it; if you already built v1.9.0, the game rebuilds itself once on the next start (a few minutes).

### New in v1.9.0
**A lot has changed in this version, above all the lighting. Please let me know how it runs for you, especially on Windows: the new lighting has not been tested on a Windows PC yet. Feedback, screenshots and the room where something looks odd are very welcome (Issues or Discussions on GitHub).**

- **Lighting is now On by default** (Options > Graphics): torches, lava, lit windows and the sword light the rooms, figures cast shadows; outdoors a sun casts the shadows of houses, trees and Nigel. It runs on the graphics chip now, smoother on the Steam Deck and with less load on the processor; without working GPU filters it simply stays off.
- **Real 3D shapes for the light:** furniture, statues and decorations cast shadows that follow their real form instead of boxes: tables and benches on legs, beds, barrels, jars, vases, brazier stands, armour stands and knights, the church angel, altar and lectern, shop counters, balustrades, the castle courtyard pines.
- **Day and night outdoors:** the sun moves, shadows get longer in the morning and evening, the light changes colour with the time of day and the windows glow at night.
- **New optional effects (Options > Graphics, each with its own switch):** particles (fireflies, sparks, drops), enemies dissolving, heat haze over lava, water reflections, cloud shadows.
- **Fixes:** no freeze when loading a save with Lighting on; no hitch when entering Mercator; shadows that vanished or sat in the wrong place (castle throne room and main hall, the route north of Destel, issue #14); hard light edges and stripes at torches, stairs, doors and furniture.
- Everything from v1.8.0 is included.

### Downloads
- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage` (make it executable, start it, pick your ROM).
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip` (extract the whole zip, start `Project-Friday.exe`). The new lighting is untested on Windows: if the picture looks wrong, switch Lighting off in Options > Graphics and please let me know.

SHA-256 (to check your download, no extra file needed): AppImage `{SHA256}`, Windows zip `{WSHA256}` (built by GitHub Actions from the tagged source).
