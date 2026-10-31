# Room map (MODERN_IDEAS (B), started 2026-10-31)

User wishes: own room map (not the island map), location only (no 'where to go next'), Landstalker style, full resolution. Status: step 1 built (dev), user check on the Deck open.

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

## Open / ideas
- User look at it on the Deck (style, size, button). Town interiors are in the town's grid (no 'inside' grouping yet). Mercator outdoors shows as floor 2 / 3 (houses with cellars).
- Area names are the library identifiers (MERCATOR, SWAMP SHRINE); own display names / German later if wanted.
