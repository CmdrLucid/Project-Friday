# Room map (MODERN_IDEAS (B), started 2026-10-31)

User wishes: own room map (not the island map), location only (no 'where to go next'), Landstalker style, full resolution. Status: v2 built (dev): v1 hung on the Deck (see v2 below), towns dropped; user check of v2 open.

## How it works
- **Data (build time, from the player's ROM, never in git):** `tools/roommap.py ROM build/roommap` (step of build.sh, also run by firstrun.py; ~2 min on all cores the first time,
  skipped when up to date; thumbnails have their own stamp). Writes `layout.txt` (areas, rooms with floor / grid cell / visited bit / floor bbox, connections, variants) and
  `thumbs.bin` (every room drawn from the ROM by `romrender.py`, shrunk to 112 px wide, RGB565). The game finds it at `<exe dir>/roommap` (`LANDSTALKER_MAPDIR` overrides).
- **Areas:** region = room name prefix from `docs/ROOMS.md` (multi-word prefixes listed in `MULTI`), unnamed rooms take their neighbours' region; area = connected rooms of one region.
- **Why schematic:** placing rooms by their door cells (connection records `$11CEA2`, x1/y1 -> x2/y2) overlaps them badly even with the best +-3 cell shift per door (tested on the
  Swamp Shrine: 8 conflicts, rooms on top of each other). So: 2:1 grid, one cell per room, neighbour in the direction of the exit = the edge of the room's walkable floor
  (height map cells with type nibble != 4) the door cell is on (NE = -y, NW = -x, SE = +x, SW = +y); taken cells: nearest free cell around the wanted one (v2).
- **Floors:** connection extra bits 10 / 20 = staircase, record order = lower room first (Mercator armory 0F -> 1F -> 2F, castle 1F -> 2F hallway, lighthouse 2F -> top).
  Swamp Shrine = 3 floors (13 / 13 / 3 rooms). One floor shown at a time.
- **Visited:** the game's own bits `g_RoomVisitedFlags $FF10C0` (SetRoomVisited `$00293C`, bit number from `RoomVisitedFlagLookup $00C74E`, up to 641; saved with the game).
  Only visited rooms and the current one are drawn.
- **Runtime (`tools/patch_roommap.py`, LK_ROOMMAP v1):** binding 'Map' (Options > Keybindings, pad L4 = PADDLE2, key M). Opens only in a map room (own renderer frames running,
  room known). Modal loop inside platform_poll_events: game + audio paused, D-pad / L / R = floor, B / Start / Esc / M / the binding = close, waits until the closing press is
  released. Drawn into an ARGB buffer at output size (gold-framed dark blue panel, area name, FLOOR n / m, cells with the room pictures 1.5 x the cell, passage bars, stair
  triangles, current room gold, Nigel = blinking red dot from `$FF5400 / $FF5401`), blended over the dimmed game picture before the OSD.
- **Test aids:** `LANDSTALKER_MAPSHOT=frames` (PNG of the map as it would open, also headless; `LANDSTALKER_OSHOT_SIZE`, `LANDSTALKER_MAPSHOT_FLOOR=n`, `LANDSTALKER_MAPSHOT_ALL=1` = all rooms).

## v2 (2026-10-31, after the user's first try)
- **v1 HUNG on the Deck** (user: map opened, could not close, not even leave fullscreen; the process had to be killed): the modal loop waited for SDL controller EVENTS, but
  LK_PADTHREAD switches controller events off (SDL_GameControllerEventState(SDL_IGNORE)) and reads the pads on its worker thread. v2 polls `lk_map_pad()` (input.c: the worker's
  button copy + left stick, kicks the worker every pass; bit 31 = the Map binding's pad code); any new button except up / down / L / R closes; keyboard keys still by events.
- **Dungeons only** (user: 'Mercator wirkt viel zu durcheinander mit den ganzen Innenraeumen, lassen wirs lieber bei Dungeon-Karten'): `DUNGEONS` in roommap.py (Swamp Shrine,
  Mercator dungeon, Knight / Nole areas KN_*, Lake / Waterfall shrines, Thieves' hideout, Destel well, Mir tower, Verla mines, Massan cave, crypt, Greenmaze, Helga's hut, Tibor,
  Ryuma lighthouse): 31 areas, 504 rooms. Elsewhere the button shows 'NO MAP HERE' ('KEINE KARTE HIER') for 1.5 s.
- Headless: mapshot in room 5 (rec_20261024_1818 frame 11645) = Swamp Shrine floor 1 / 3; Mercator = no map. The modal loop itself can only be tried on the Deck.

## v3 / roommap v4 (2026-10-31, user recording rec_20261031_1141, KN_LABYRINTH 355 -> 356)
- User: 'I leave the first room south-east, the map hangs the next one north-east' + 'the picture runs over its box'. Cause 1: the height map cells from romroom.arrays are
  12 cells off the game's cell coordinates (the game puts the height map at (12, 12); connection records and Nigel `$FF5400` use the game's cells), so the exit side was judged
  on a wrong footprint (355: door (30, 25), footprint x 5..18 -> now 17..30 = SE). Fixed in roommap.py footprint() (v4); Nigel's dot uses the same frame now.
  Cause 2: the picture was 1.5 x the cell: now as wide as the cell, its bottom on the cell's bottom corner, clipped to the cell diamond (walls cut at the top, LK_ROOMMAP v3).

## Open / ideas
- User look at it on the Deck (style, size, button). Town interiors are in the town's grid (no 'inside' grouping yet). Mercator outdoors shows as floor 2 / 3 (houses with cellars).
- Area names are the library identifiers (MERCATOR, SWAMP SHRINE); own display names / German later if wanted.
