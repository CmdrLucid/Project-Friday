# Ideas: Boss Rush started by an NPC (THEORY ONLY, nothing built)

**Written 2026-10-26, cloud session (no ROM), from a feasibility discussion with the user. Based on `dev` commit `e35a30a`.**
The user's wording: "Haben wir in der Raumliste die Locations fuer alle Bosse und koennten wir daraus einen Boss-Rush-Mode bauen? Eher ein NPC im Spiel,
der das Ganze startet, statt einer weiteren Option ... irgendwo in Mercator, vielleicht im Casino." Then: "vielleicht einfach eine Kopie des Bosses in
einen Raum stellen, statt direkt den Boss, der die Story Flag ausloest". Then: **"noch nicht anfangen", only document for a later session.**
Nothing here is implemented or verified. Re-check against the code / docs of the day before acting.

## Goal (user)
- A Boss Rush mode: fight the bosses one after another.
- Started by an **NPC in Mercator** (no new Options row; the user would not know where to put it). Casino of Mercator suggested; "another room" was an idea.
- Preferred variant (user, second message): fight **copies** of the bosses that we place ourselves, not the real story bosses, so no story flag is touched.

## What we already have (known)
- Boss entity types: `docs/ENTITIES.md` (from landstalker-lib): miro_1 `$00`, duke `$70`, mir `$7C`, zak `$85`, spinner_white `$9D`, miro_2 `$9F`,
  firedemon (Ifrit) `$A0`, gola `$A2`, nole `$A5`, quake_gray / quake_gold `$A7` / `$AB`, spinner_red `$AA`, golems `$92..$94`, knights `$1D..$1F`.
  landstalker-lib `patches/engine_improvements/patch_normalize_bosses_hp.hpp` treats exactly these as the real bosses: miro_1, duke, mir, zak,
  spinner_white, miro_2, gola, nole. It also documents that the game kills bosses by HP threshold checks in room / cutscene code (thresholds `$6400` / `$100`),
  and that the enemy kill path is at `HandleEnemyHit $016248` (+$14 in landstalker-lib's patch).
- Boss rooms named in `docs/ROOMS.md` (landstalker-lib names): 28 SWAMP_SHRINE_BOSS_ROOM, 111 NOLE_ARENA, 112 GOLA_ARENA (113 cinematic variant),
  242 VERLA_MINES_DEX_ARENA, 255 VERLA_MINES_SLASHER_ARENA, 264 VERLA_MINES_MARLEY_LAVA_ROOM_MOVING_PLATFORMS (Marley sector), 784 MIR_TOWER_BOSS_ARENA.
  **Missing:** the rooms of Miro 1 / 2, Duke, Zak, Spinner, Ifrit, Quake, golem fights. Story flags with boss names: `docs/FLAGS.md` (DEX_KILLED,
  MARLEY_KILLED, VERLA_*_KNIGHT(S)_KILLED, ZAK_FLEW_OFF_MERCATOR_DUNGEON, Duke encounters ...).
- Room change by code: test aid `LANDSTALKER_WARP="room:x,y"` (`patch_goto.py` / warp via `WarpToRoom $00620E`), used for many headless tests.
- Snapshot / restore of the whole game state: Quick Save / Quick Load (`patch_quicksave.py`, hidden SRAM slot): save the player's game before the rush, restore it after.
- Own text / Yes-No windows with the game's routines: Options tab (`patch_options.py`), Item Info (`patch_iteminfo.py`); the game's own prompt `j_LoadYesNoPrompt $022E88`.
- Entity slots in RAM: player `$FF5400`, slots `EntitySlot_1 $FF5480` ..., `$80` bytes each (fields in `docs/FORMATS.md`, lordmir `ram.inc` Sprite<n>_*);
  the room's entity list is turned into slots by `InitialiseSprites $01953A` at room load.

## Variant A: the real boss rooms with their scripts (first idea, harder)
- Warp into each boss room in turn with a fixed loadout.
- Problems: bosses depend on story flags (a beaten boss does not appear again, encounter flags); every fight ends in story cutscenes / own room changes
  (Gola and Nole = the ending + credits) that must be intercepted per boss; flags must be set before and restored after each fight.

## Variant B: boss COPIES placed by us (user's preferred idea, recommended)
- Inject the boss entity ourselves (same mechanism as the NPC below: add an entity when a room loads, C hook around `InitialiseSprites $01953A`), and
  handle its defeat ourselves (HP below the threshold -> remove it, short pause, next boss). Story flags and the room scripts are not used.
- Open questions to test per boss:
  1. **Graphics / palette:** sprite graphics and palettes are loaded per room for the room's entity list; a boss in a foreign room may show wrong
     colours / broken tiles. Easiest: the copy in its OWN arena room with the room's script suppressed, or load the boss palette ourselves.
  2. **Space:** big bosses need their arena; several bosses at once in one room (e.g. the casino) will fail on VRAM tile budget / palettes. One at a time.
  3. **Scripted bosses:** Zak flies off at low HP, Duke flees, Mir teleports, Gola / Nole are tied to the ending: their AI is partly interwoven with
     cutscenes -> intercept the escape / cutscene, or leave them out at first.
  4. Expected to work almost as plain enemies (to verify): Miro, Spinner, Ifrit, Quake, golems, knights, Dex, Slasher, Marley.

## The NPC in Mercator
- A completely NEW room (casino annex) needs own map data: very expensive, not planned.
- An extra NPC in an EXISTING room: inject one entity at room load, catch the talk action, own text ("Willst du dich allen Bossen stellen?") + Yes / No.
  Candidate: the Mercator casino (room number not in landstalker-lib's list; find it on the Deck with the coordinate overlay, pad R4 / F5).
- Unlock idea: the NPC offers only the bosses already beaten in the current save (no spoilers; the NPC is the switch, no Options row).
- Rule conflict to settle with the user: until now "everything off = original". The NPC changes a room; option: show him only after the first boss
  win or after finishing the game.

## Fair loadout
- Landstalker has no XP: strength = hearts, swords, armour. The rush should set a fixed loadout (full hearts, all swords, some EkeEke) in RAM
  (`g_Inventory $FF1040`, `EquippedSword $FF114E` ..., `Player_MaxHealth $FF547E`) and give the player's own back afterwards (Quick Save snapshot).

## Plan if the user says go (estimate)
1. **Research on the Deck (1 session, needs the ROM):** small reader for the room entity lists in the ROM (format: lordmir/landstalker_editor,
   landstalker-lib `io/`), table of every boss: room, position, entity type, flags, scripts; write it into this file / ROOMS.md / FORMATS.md.
   Try the copy idea per boss quickly (colours, AI, death).
2. **Prototype without NPC (1-2 sessions):** test switch (env variable) that chains the bosses with a fixed loadout. The USER plays each fight
   (Claude cannot play fights headless); start with the simple bosses.
3. **NPC in Mercator (1 session):** figure, text, Yes / No, return to the own save afterwards.
4. **Polish:** timer, result screen, return after the last boss instead of the credits.
Biggest risk: 2-3 scripted bosses (Duke, Zak, Nole) may only work with limits or be left out at first.
