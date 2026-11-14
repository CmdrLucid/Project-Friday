# Friday hints (Select key): story checkpoints

Status 2026-10-31: rewritten from the game's own progress function; nothing here is verified on the Deck yet. The machine-readable twin is `lang/friday_hints.json` (the build reads it; generated from the same data as the checkpoint list below).

**Purpose.** Pressing Select makes Friday say where to go next. Two levels: L1 = gentle direction, L2 = clear what / where (shown when the player asks again). Texts are our own wording (no game dialogue copied). German: du-form, slightly cheeky; max 2 lines of 34 characters per level and language.

## 1. How the game measures story progress (source of truth)

`GetFlagProgress` ($025318, `code/script/en/scriptflagcheck.asm`) fills three bytes with `PickValueBasedOnFlags`: each list is (flag number, value) pairs checked TOP-DOWN, the first flag that is set gives the value.

| RAM | list | meaning |
|---|---|---|
| $FF1906 | list 1 | main story stage 0..31 (`stage>=N` in the json, decimal) |
| $FF1907 | list 2 | `sub2` 1..3: shop-keeper side quest (flags $A0 / $152 / $154); not used by the hints |
| $FF1908 | list 3 | `sub3` 1..3: Helga / dog Bell side quest (flags $124 / $13C / $13F); not used by the hints |

`HandleProgressDependentDialogue` additionally keeps a high-water mark ($FF190E..), so NPC stages never go down. Flag number n = byte n>>3, bit n&7 at $FF1000 (`$BB.b` below; same numbering as FLAGS.md). Stage values are hex in the asm; this document and the json use decimal.

## 2. The 32 stages (list 1) and what comes next

`$BB.b` = byte.bit; `0xNNN` = flag number as in the list; NAME from FLAGS.md where known. "Next" = the action that sets the NEXT stage flag. Evidence = NPC dialogue gated on `Params 00,NN` in `script_characters.asm` plus cutscene text (understanding only).

| stage | flag | what happened | NEXT step (flag that follows) |
|---|---|---|---|
| 0 | none | game start, Nigel wakes in Massan | villager warns about the broken bridge ($02.0) |
| 1 | 0x010 = $02.0 MASSAN_VILLAGER_WARNED_BRIDGE_IS_BROKEN | bridge smashed by Gumi | talk to Prospero (his stage>=1 branch sets $00.0) |
| 2 | 0x000 = $00.0 FARA_KIDNAPPED | Fara taken by Gumi tribe | go to Gumi, watch the ritual ($02.4) |
| 3 | 0x014 = $02.4 SPIED_ON_GUMI_RITUAL | ritual seen; Swamp Shrine door shut | get IDOL_STONE (item $31), use it at the statue, beat the Orc Kings, free Fara ($02.5) |
| 4 | 0x015 = $02.5 | Fara rescued (cutscene: come to my house) | Massan mayor: RED_JEWEL (sets $04.2) |
| 5 | 0x022 = $04.2 | Red Jewel received; landslide road cleared | walk to Ryuma, find the hidden villager ($02.7) |
| 6 | 0x017 = $02.7 TALKED_WITH_HIDDEN_VILLAGER_RYUMA | Ryuma knows about the thieves | town elders ask for help ($04.0) |
| 7 | 0x020 = $04.0 ALLOWED_TO_GO_IN_THIEVES_HIDEOUT | hideout is on a cape, reach by raft (room 183 pier) | clear the hideout, free the mayor ($04.1) |
| 8 | 0x021 = $04.1 | gang beaten, mayor free | mayor in Ryuma gives SAFETY_PASS (sets $04.3) |
| 9 | 0x023 = $04.3 | SAFETY_PASS + 100 golds | Mercator: find a way into the castle ($05.4 / $05.5) |
| 10 | 0x02C = $05.4 | UNSURE meaning (no dedicated dialogue) | castle backdoor, Arthur seen ($05.5) |
| 11 | (never set) | the list has no entry for 11 | - |
| 12 | 0x02D = $05.5 SAW_ARTHUR_AT_CASTLE_BACKDOOR | Arthur seen sneaking | Madame Yard's upstairs girl hints at the fortune-teller ($05.6) |
| 13 | 0x02E = $05.6 TALKED_WITH_MADAME_YARD_GIRL_HINTING_FORTUNE_TELLER | trick known | fortune-teller casts the spell (sets $03.4) |
| 14 | 0x01C = $03.4 | spell cast | door at Madame Yard's, Arthur gives access ($03.5) |
| 15 | 0x01D = $03.5 ARTHUR_GAVE_ACCESS_TO_CASTLE | castle gate guards let Nigel in | meet the duke ($03.7), he leaves ($12.1) |
| 16 | 0x091 = $12.1 DUKE_LEFT_ROOM_AFTER_FIRST_ENCOUNTER | duke gone | servant shows the bedroom ($12.2) |
| 17 | 0x092 = $12.2 SERVANT_BORUGHT_US_TO_BEDROOM | in the castle, free to roam | butler / kitchen woman: dinner ready ($12.3) |
| 18 | 0x093 = $12.3 TALKED_WITH_KITCHEN_WOMAN_BEFORE_BANQUET | party is ready | banquet room, room 85 ($12.4) |
| 19 | 0x094 = $12.4 ASSISTED_TO_MERCATOR_BANQUET | duke sends Nigel against Mir | sleep in room 97 ($14.0) |
| 20 | 0x0A0 = $14.0 SLEPT_AT_MERCATOR_AFTER_BANQUET | next day; Mir's tower is behind a barrier | crypt (Mercator motel, rooms 646-659): riddles ($16.3), armlet ($14.6) |
| 21 | 0x0B3 = $16.3 | UNSURE: crypt riddle part done | get the ARMLET (item $1F, room 651) |
| 22 | 0x0A6 = $14.6 | armlet gained (UNSURE flag meaning) | Mir's tower (rooms 750-784), purple jewel ($17.6), Mir talk ($17.7) |
| 23 | 0x0BF = $17.7 | Mir met, he is innocent | report to the duke: betrayal, jewels taken, dungeon ($13.0, $13.1, $20.4) |
| 24 | 0x105 = $20.5 ZAK_FLEW_OFF_MERCATOR_DUNGEON | escaped; castle invaded by armored soldiers | help Arthur ($20.6), then Greenmaze / dog |
| 25 | 0x124 = $24.4 | dog (Einstein) cured with an EkeEke (also sub3 = 1) | whistle, Greenmaze, SUN_STONE (item $1E), lighthouse |
| 26 | 0x131 = $26.1 | lighthouse lit again, free ship to Verla (docks 641-644) | Verla Mines (227-269): knights ($26.3, $26.4), Dex ($26.7), Marley ($28.0) |
| 27 | 0x140 = $28.0 MARLEY_KILLED | miners free, tunnel to Destel open | Destel (726-736), duke on raft ($28.7), Destel Well (270-290) |
| 28 | 0x150 = $2A.0 SAW_DUKE_ENTERING_LAKE_SHRINE | duke went into the Lake Shrine | Lake Shrine (291-354), boss ($2A.5) |
| 29 | 0x155 = $2A.5 FINISHED_LAKE_SHRINE | Lake Shrine done | UNSURE: back to Mercator ($2A.6) |
| 30 | 0x156 = $2A.6 | UNSURE (no name, no dialogue) | Mercator teleporter opens ($27.1) |
| 31 | 0x139 = $27.1 OPENED_MERCATOR_TELEPORTER_TO_KNC | route to King Nole's Cave open | after stage 31 see section 4 |

Side flags used as sub-checkpoints: $12.x (castle day), $13.0 / $13.1 / $20.4 (dungeon), $17.6 TOOK_PURPLE_JEWEL_IN_MIR_TOWER, $20.6 TALKED_WITH_ARTHUR_REVEALING_DUKE_ESCAPE, $26.7 DEX_KILLED, $28.7 SAW_DUKE_MERCATOR_ON_RAFT_NEAR_DESTEL, $2B.1 SECOND_RAFT_PLACED_IN_KNL, $2B.7 SAW_DUKE_TAUNTING_IN_SHELL_BREAST_ROOM. Items: IDOL_STONE $31, ARMLET $1F, EINSTEIN_WHISTLE $20, SUN_STONE $1E.

## 3. How to read the checkpoint list

The runtime picks the LAST entry whose `when` conditions ALL hold, so entries run from early to late. Room entries ("in_...") come right after the generic entry of their stage and are only shown while the player stands in that room range; the next stage's generic entry (no room condition) always overrides them. Conditions: `stage>=N`, `sub2>=N`, `sub3>=N`, `flag:BB.b` / `!flag:BB.b` (byte BB hex), `item:XX` / `!item:XX` (hex id), `room:A-B` (decimal range). Characters allowed in texts: A-Z a-z 0-9 space . , ? ! ' - : ( ) and German umlauts.

## 4. After stage 31 (no further list-1 values)

The list ends at stage 31; the rest of the game is covered by room ranges plus flags $2B.1 / $2B.7 and items: King Nole's Cave (rooms 144-172, teleporter to Kazalt = room 170), Kazalt (737-749, shop 747, church 749), the Labyrinth (355-423, exterior 362, tree with logs 415, ice path to the palace 388, stairway to Nole 421), the Palace (115-138), pillar hallway 114, Nole arena 111, Gola arena 112 / 113. Gola is slain in cutscene $144 and the ending follows. UNSURE: no story flag exists in FLAGS.md for entering Kazalt or beating the Labyrinth; the hints there depend on the current room only.

## 4b. Runtime (LK_FRIDAY v2, 2026-10-31, user wishes)
Only the gentle level (L1) is shown (the user: 'nur die vagen Hinweise'); L2 stays in the data. The text box starts with her name on its own line ('Friday:', German 'Flora:'), plays her speech blip (g_TalkSoundEffect $FF1154 = SpecialCharacterSfxList $02913E entry 1) and she flies out of Nigel's bag while she talks (g_FridayAnimState $FF114B = 1, next state $FF114D = $11, then $31 = back into the bag after the text, as the cutscene actions do). Headless-verified (screenshots, rec_20261029_1729 frame 15000, German).

## 4c. Knowledge review 2026-11-14 (user rule; Opus 5.5 lead + 3 Sonnet review agents)
User (2026-11-14): 'Friday weiss an dem Punkt nichts von einem Gelehrten und Nigel auch nicht' -> RULE: a hint may only name persons / places / items / facts that Nigel and Friday KNOW when it can show = told by a MANDATORY event before its condition holds (the stage flag's own event, a cutscene, an obligatory talk); things only an optional NPC says are not allowed unless a flag in `when` proves that talk; no spoilers (next event's content, a twist, a boss before it appears); no internal room numbers. Every hint was checked against the dialogue (string ids) and the flag setters; 45 hints rewritten in lang/friday_hints.json (the json is the source now; the EN / DE lines in section 5 below are the OLD 2026-10-31 texts, the evidence notes still apply unless corrected here).
Corrected facts (evidence in the disassembly, verified by the lead):
- stage 25 ($24.4) is set by CSA_00C6 (the scene that gives Einstein's whistle), not by curing the dog: `stage25_dog` (needed !item:20) could never show -> deleted.
- stage 29 ($2A.5) comes with Mir's rescue talk after the Lake Shrine (spell that cuts the sacred trees; north gate of the castle, mountains northwest of Mercator); the old 'duke back at his castle' was wrong.
- stage 30 ($2A.6) = PostUseGolasEye (Gola's Eye used); nothing says 'castle'. Where the stage 31 teleporter is seen stays UNSURE.
- The Idol Stone is not consumed; PostUseIdolStone sets $00.6 (swamp shrine door open): `stage03_have_stone` gets `!flag:00.6`, new entry `stage03_door_open` (`flag:00.6`).
- Mir's barrier / armlet / crypt are told only by optional castle people: the stage 20..22 hints no longer claim them as known.
- The bridge villager (stage 1) only says Gumi smashed it and to tell the mayor; no scholar.
Still UNSURE (to check while playing): stage 2 window before the mayor tells about Fara (hint now names only Gumi), when $17.7 (stage 23) is set relative to the purple jewel (stage22_purple may never show), stage 10 flag meaning, stage 31 teleporter place.

## 4e. Flag-gated precise hints (2026-11-14)
Rule (extends 4c): a hint may name what an OPTIONAL NPC said only behind a flag that proves that talk (SetFlagBitOnTalking / text opcode / cutscene setter; every flag below has exactly one setter, checked over all six setter kinds: talk words, $14xx text opcodes, SetFlagBit calls, bset on g_Flags, sprite behaviour EB_SetFlag $41, room flag tables). The precise variant is a separate entry with the base entry's conditions plus the flag, placed right AFTER its vague base and BEFORE the room / item / next-stage entries that must still override it (the runtime shows the LAST match). Evidence: `~/Project-Friday-Test/lktest/friday_flags/verified.md`.

| hint id | flag | NPC + room | from stage | fact the hint may state |
|---|---|---|---|---|
| stage02_fara_seen | $02.2 | Massan villager cutscene $0D (room 592, walking into Massan after Prospero) | 2 | Gumi thugs kidnapped Fara; the bridge is fixed (NOT the Marsh Shrine) |
| stage20_tower_dexzak | $1A.1 | Arthur, room 83 (castle armory 1F), day 2 | 20 | Dexter and Zak asked how to break the barrier and went to the crypt; an armlet is there |
| stage20_tower_arthur | $19.7 | Arthur, room 83, only settable at stage 19 | 20 | barrier at the tower entrance; an armlet breaks it; crypt next to the church; traps |
| stage20_in_crypt_dexzak | $1A.1 | Arthur, room 83 | 20 (in the crypt) | the monsters are clever; the sword alone will not win the armlet |
| stage20_have_armlet_arthur | $19.7 | Arthur, room 83 | 20 (armlet owned) | the armlet breaks the barrier at Mir's tower entrance |
| stage22_to_mir_arthur | $19.7 | Arthur, room 83 | 22 | same |
| stage23_dungeon_lara | $1A.0 | dungeon women, rooms 43 / 45 | 23 (in the dungeon) | the duke holds Princess Lara prisoner down here; find her |
| stage25_whistle_gol | $1A.7 | Old Gol, room 561 (Greenmaze) | 25 (whistle, no Sun Stone) | Sun Stone in the northeast of the forest; the gnomes changed the paths |
| stage31_labyrinth_father | $1C.0 | old dwarf, room 406 | 31 (Labyrinth, logs not taken) | a raft is needed for the river; find his son, get logs |
| stage31_labyrinth_son | $1C.1 | his son (cutscene XS_012B) | 31 (Labyrinth, logs not taken) | go up and cut the tree to make a raft |

Rejected: $19.2 (butler, stage 17: 'an evil magician torments the duke, more at the party') adds nothing actionable beyond `stage17_roam` / `stage18_party` and the banquet itself tells it one stage later. part_a flags: $02.1 (meeting Prospero, part of the mandatory visit, no new fact), $02.7 (it IS the stage 6 flag), $04.7 (Mercator gate opened = mandatory stage-9 entry), $05.0 (Julie / wall-jumper flavour), $05.1 (scared boy flavour).
Open point: is the $02.2 cutscene (Massan villager, room 592, TA_09 Player_Y $30) unavoidable on the way to Gumi? If it is, its fact belongs into the base `stage02_fara` and the 4c UNSURE 'stage 2 window' is closed; until checked on the Deck it stays a flag-gated variant.

## 4d. 'heard' conditions (LK_FRIDAY v3, 2026-11-14; lead + user: precise hints only after the player READ an optional NPC)
Most optional talks set no story flag, so the runtime keeps its own record of the lines the player has seen. Conditions: `heard:XXXX` (XXXX = 4-hex string id = key of lang/en_tone.json / de.json) is true when that line was printed in this game; `!heard:XXXX` when not; alternatives `heard:0178|017B|0182` = ANY of them, `!heard:A|B` = NONE of them (up to 16 ids per condition; the conditions of one entry stay AND-combined). Compiled into `lk_fh_h[]` (the ids) + the condition (first, count).
- **Hook:** the InitCompString wrapper `lk_lg_h_ics` (patch_lang.py) of `InitCompString $022FCC` (D0 = string id). Its only caller is `PrintString` / `PrintString_0` (`$022F1C` / `PrintString_Start $022F2C`), the single entry of every compressed string the game prints (NPC talk, signs, also chest / shop messages: harmless, a hint only asks for the ids it names). Name tables / item names (`SkipToStringIndex $0294B6`) and menu texts (`LoadUncompressedString`) never pass it; Friday's own stream (carrier id $16, `lk_fh_force`) is explicitly skipped (verified: the hint press prints string 0016, no 'heard 0016').
- **Bitmap:** 512 bytes (4096 ids; the game has 2175), bit n = byte n >> 3, bit n & 7. OURS only, the game never reads it: Hints Off = bit exact. Collected also while Hints are Off, so switching them on mid-game knows the past.
- **Per save slot, following the game:** `SaveGame $001592` stores the current map into slot `g_SaveSlot $FF0010` (church book, Record Book, quick save = hidden slots 4..7 of patch_quicksave.py, one per file slot); `LoadSavedGame $0015C2` takes it back (the file select also loads every slot for its preview; the last load = the chosen slot); `CopySaveGame $0015E6` (d0 = source, d1 = destination) copies it; `EraseSaveslot $001552` and `GetCurrentSaveSlot $00154C` (which falls through into the erase = the file select's Delete) clear it; a new game (`StartGame $008D84` in the intro room $8B, the same test as patch_quick.py) starts empty and clears that file slot's quick save map (like `lk_qs_wipe`). Game over -> continue reloads the slot like the game's own data.
- **File:** `<save>.friday` next to the .srm (`lk_sram_file()` in genrecomp.c = the runtime's .srm path, `LANDSTALKER_SAVE` included; `LANDSTALKER_FRIDAY_HEARD=path` wins); layout in FORMATS section 6. Written whole whenever a slot map changes; a missing / bad file = empty maps; no battery RAM = memory only.
- **Test aids:** `LANDSTALKER_FRIDAY_LOG=1` also prints `friday: heard XXXX at frame N` when a bit is first set and `heard file ... written`; re-running patch_friday.py on a patched tree swaps only the hint tables (`LANDSTALKER_FRIDAY_JSON=test.json python3 tools/patch_friday.py .deps/genrecomp && cmake --build build`, ~5 s).
- **Headless results (2026-11-14, copy of the user's .srm, scratch HOME, replay massan.txt + Mode held in a window, test json in ~/Project-Friday-Test/lktest/friday_heard/):** the replay prints strings 0066 (frame 4440) and 005B (4831) -> both bits set. Press at 4101 -> `t_base`; at 4651 -> `t_0066_not005B` (heard:0066 + !heard:005B|0001); at 13301 (after 005B) -> `t_or` (heard:0001|005B|0FFF; the !heard:005B|0001 entry no longer holds); Friday's own press printed string 0016 without setting a bit. Quick save at 13300 wrote `s.srm.friday` (4104 bytes, slot 4 = {005B, 0066}, slots 0..3 empty); a fresh run with that .srm + .friday, quick load at 3800 (room 632) and a press at 4301 (no line printed in that run) -> `t_or`; the same run without the .friday file -> `t_base` (persistence works). Bit exact: Hints Off, 14 RAM dumps (every 1000 frames, 0..13000) of the replay identical before / after the change.

## 4f. Heard-gated precise hints (2026-11-14)
Rule (extends 4c / 4e, uses the `heard:` conditions of 4d): a hint may state what an OPTIONAL NPC said only behind `heard:` of the string id that carries the fact; gate = the LAST text box of that NPC line that holds the fact in EN AND DE (a ContinuePrompt chain is printed box by box, so the last id implies the earlier ones; German often splits the sentence differently, e.g. 042D/042E, 04C7/04C8). Each id was grepped over code/script/en: printed by exactly one NPC (repeats only in other branches of the same NPC), no cutscene prints them. `heard` persists, so 'from stage' = the first stage the line can be heard; the variant sits right AFTER its base and BEFORE the entries that must still override it (LAST match wins). Texts use only the facts below, no names the NPC did not say. Evidence: `~/Project-Friday-Test/lktest/friday_heard/verified.md` (script lines in the checkpoint blocks of section 5).

| hint id | heard | NPC + room | from stage | fact the hint may state |
|---|---|---|---|---|
| stage01_prospero_oldman | 0178\|017B\|0182 | Massan villagers (rooms 599, 600 ...) | 0 (hint at 1) | an old sage lives in the Waterfall Shrine and knows more (no name) |
| stage02_fara_prospero | 01C5 | Prospero, Waterfall Shrine (room 180) | 2 | the Orcs trick the Gumi; Fara is in danger (no boss, no shrine name) |
| stage03_need_stone_item | 016C | farmer, rooms 425 / 433 / 595 | 3 | the Gumi opened the door with something strange (no stone named) |
| stage05_to_ryuma_fork | 01A0 | Massan villager, room 592 | 0 | past Gumi the road splits at the sea; left = Ryuma, right = Mercator |
| stage06_elders_meeting | 024C\|024D | Ryuma house, room 622 | 5 (hint at 6) | people hold a meeting in that house (mayor part only in 024D: not used) |
| stage18_party_floor | 040D\|0413\|044E\|0474 | castle maids, rooms 55 / 68 / 70 / 85 / 88 | 18 | the banquet hall is upstairs |
| stage20_tower_barrier_seen | 02FD\|0451\|067F | townsman 673, library 74, tower door message | 20 | a barrier blocks the door of Mir's tower |
| stage20_tower_barrier | 042E | butler, rooms 51 / 55 / 85 | 19 (hint at 20) | barrier at Mir's tower door; General Arthur knows about breaking it |
| stage20_tower_crypt | 03B1 | Mercator townsman, room 630 | 20 | Zak and Dexter went down into the crypt |
| stage25_whistle_jump | 0264 | Ryuma, room 622 | 24 | the Sun Stone needs good balance and good jumping |
| stage26_verla_mountains | 04C8 | fisherman, room 499 | 26 | soldiers dragged the townspeople off to the mountains |
| stage26_mines_forks | 04D3 | miner, rooms 255 / 713 | 26 | the mine forks into three tunnels; more captives in the other two |
| stage27_destel_west | 04EB | captive, rooms 242 / 711 | 26 | a village lies west of the mine; the duke marched there with soldiers |
| stage27_destel_tunnel | 04FA | rooms 243 / 722 | 27 | the only way to Destel is the tunnel in the mine |
| stage27_destel_duke | 04DF | rooms 269 / 724 | 27 | the duke and his soldiers went to Destel |
| stage27_destel_well | 0511 (+ flag:28.7) | Destel dwarf, room 726 | 27 | the well is the entrance to an ancient monster cave |
| stage31_kazalt_gatekeepers / stage31_labyrinth_gatekeepers | 052B | Kazalt dwarf, room 744 | 31 | three monsters in the labyrinth must be beaten to reach the palace |

Note: stage27_destel_west uses 04EB instead of verified.md's 04EA: the duke / soldiers half of the fact ends in 04EB in both languages (same NPC chain, 04EB printed nowhere else).
Rejected: stage-0 twin of stage01_prospero_oldman (stage 0 points to the bridge first; Prospero has no stage-0 branch); stage13_teller_famous 0380 (no place, the fortune-teller is known from the stage-13 event); stage19_sleep_room 040F|0414 (the own bedroom is known from the stage-17 event); stage27_destel_well before $28.7 (would point to the well before the raft scene); 01C6 (shrine name DE only); 0156 / 0157 (only 'door won't open' = base); 034F / 03EB / 035B / 0350 (EN / DE differ or no gain); 04CD priest (weaker than 04C8).
Ungated sharpenings (a MANDATORY line tells it, no gate needed): `stage14_spell` L1 names Madame Yard's (05EC, cutscene 0x49 always follows the spell); `stage07_raft` hideout = cave on the cape, reached by raft (025D printed by both $04.0 setters); `stage18_party` banquet room (all $12.3 setters).
4c fixes of existing base texts: `stage18_party` L2 'second floor' removed (now in stage18_party_floor); `stage05_to_ryuma` L2 no longer names the fork / Ryuma (now in stage05_to_ryuma_fork); `stage07_raft` L2 'Ryuma's pier' removed (not in 025D).
Open points: CLOSED 2026-11-14: stage 24 / 25 is handled by the flag-gated variant `stage25_whistle_arthur` (`flag:20.6`, no proof of order $20.6 vs $24.4 needed: it shows only when both hold, and Gol's heard line `stage25_whistle_gol` stays later in the list and wins); 067F (barrier message at the tower door) is already an alternative in `stage20_tower_barrier_seen`. Still open: $26.5 (gate of the miner's lines) has no name in FLAGS.md. All heard: entries need the v3 runtime to mark every box of a ContinuePrompt chain (4d hook = every PrintString call: yes).

## 5. Checkpoint list (same data as the json)

Format: id, `when`, evidence, then EN / DE (L1, L2; `|` = line break).

### `stage00_start`
- when: `stage>=0`
- evidence: Start of game; Nigel in Massan. Next flag: $02.0 (villager warns, stage 1).
- EN L1: Wake up, hero! Chat with / the villagers first.
- EN L2: Talk to everyone in Massan. / Someone mentions a bridge.
- DE L1: Aufwachen, Held! Red erstmal / mit den Dörflern.
- DE L2: Sprich mit allen in Massan. / Einer erzählt was von der Brücke.

### `stage00_cave` (added by the lead 2026-10-31 after the first headless test)
- when: `stage>=0`, `room:144-172`
- evidence: headless test (rec_20261029_1729, frame 15000): a new game starts in King Nole's Cave (room 148, goddess statue) at stage 0, so `stage00_start` (Massan) was wrong there.
- EN L1: Treasure first, chat later! / This cave must lead somewhere.
- EN L2: Fight your way through the cave / and look for the way onward.
- DE L1: Erst der Schatz, dann reden! / Die Höhle führt sicher weiter.
- DE L2: Kämpf dich durch die Höhle und / such den Weg nach draußen.

### `stage01_prospero`
- when: `stage>=1`
- evidence: $02.0 = $10 MASSAN_VILLAGER_WARNED_BRIDGE_IS_BROKEN. Next: talk to Prospero (his dialogue at stage>=1 sets $00.0 FARA_KIDNAPPED = stage 2).
- EN L1: The bridge is smashed. Maybe / the scholar knows more.
- EN L2: Visit Prospero's house in / Massan and ask about Nole.
- DE L1: Die Brücke ist hin. Vielleicht / weiß der Gelehrte mehr.
- DE L2: Besuch Prosperos Haus in / Massan und frag nach Nole.

### `stage02_fara`
- when: `stage>=2`
- evidence: $00.0 = $00 FARA_KIDNAPPED. Next: Gumi, watch the ritual (cutscene sets $02.4 SPIED_ON_GUMI_RITUAL = stage 3).
- EN L1: Fara is gone! The tribe in the / south is up to something.
- EN L2: Head south to Gumi and find / where they hold their ritual.
- DE L1: Fara ist weg! Der Stamm im / Süden führt was im Schilde.
- DE L2: Geh nach Gumi im Süden und / such ihren Ritualplatz.

### `stage02_fara_seen` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=2, flag:02.2`
- evidence: $02.2 BRIDGE_TO_GUMI_REPAIRED: behaviour 121 of the Massan villager (room 592, visible while $00.0 set) waits for TA_09 (Player_Y $30, code/scripthandling/triggeractions.asm:152-157) and runs CSA_0003 = cutscene $0D: Gumi thugs marched in after the bridge was fixed and kidnapped Fara (code/script/script_cutscenetable.asm:61-65). Proves only 'Gumi thugs kidnapped Fara'; Prospero's Marsh Shrine line (CS_0008_1 code/script/en/characters/script_characters.asm:629-640) needs a second talk without a flag -> the shrine is NOT named. UNSURE: whether the cutscene is unavoidable (section 4e).
- EN L1: Gumi thugs took Fara! / After them, Nigel - to Gumi!
- EN L2: Gumi thugs kidnapped Fara. / Cross the bridge to Gumi!
- DE L1: Die Gumi haben Fara / entführt! Hinterher, Niels!
- DE L2: Gumi-Schläger haben Fara / entführt. Über die Brücke!

### `stage02_in_gumi`
- when: `stage>=2, room:601-607`
- evidence: In Gumi town while still looking for the ritual.
- EN L1: Gumi feels creepy. Look around / quietly, don't make a scene.
- EN L2: Find the place where they chant / and watch from nearby.
- DE L1: Gumi ist gruselig. Schau dich / leise um, keine Szene machen.
- DE L2: Such den Platz, wo sie singen, / und beobachte aus der Nähe.

### `stage03_need_stone`
- when: `stage>=3, !item:31`
- evidence: $02.4 = $14 SPIED_ON_GUMI_RITUAL. The Swamp Shrine door is shut; needs IDOL_STONE (item $31, used at the statue). UNSURE: where the stone is (Waterfall Shrine rooms 174-182 assumed).
- EN L1: The shrine door stays shut. But / there is a key-like stone.
- EN L2: Get the Idol Stone (try the / Waterfall Shrine near Massan).
- DE L1: Die Tür bleibt zu. Aber es gibt / einen passenden Schlüsselstein.
- DE L2: Hol den Idol-Stein (versuch den / Wasserfall-Schrein bei Massan).

### `stage03_in_waterfall`
- when: `stage>=3, !item:31, room:174-182`
- evidence: UNSURE: Idol Stone assumed to be in the Waterfall Shrine.
- EN L1: Keep climbing. Shrines hide / their best bits deep inside.
- EN L2: Look for the Idol Stone in the / deepest part of this shrine.
- DE L1: Klettere weiter. Schreine / verstecken Gutes ganz hinten.
- DE L2: Such den Idol-Stein im tiefsten / Teil dieses Schreins.

### `stage03_have_stone`
- when: `stage>=3, item:31`
- evidence: IDOL_STONE owned: use it at the statue in front of the Swamp Shrine (ItemUseIdolStone, cutscene $11).
- EN L1: Nice stone. Doors in the swamp / like shiny things.
- EN L2: Use the Idol Stone on the statue / at the Swamp Shrine entrance.
- DE L1: Netter Stein. Sumpftüren / stehen auf so was.
- DE L2: Benutz den Idol-Stein an der / Statue am Sumpf-Schrein.

### `stage03_in_swamp`
- when: `stage>=3, room:0-30`
- evidence: Swamp Shrine rooms 0-30 (28 boss, 30 before boss). Orc Kings (cutscene $13/$14).
- EN L1: Fara is at the far end. Watch / your step and keep moving.
- EN L2: Fight through to the boss room. / Orc Kings hit hard, dodge!
- DE L1: Fara ist ganz hinten. Pass auf / und bleib in Bewegung.
- DE L2: Kämpf dich zum Bossraum durch. / Die Orkkönige hauen fest zu!

### `stage04_thanks`
- when: `stage>=4`
- evidence: $02.5 = $15 (Fara rescued; cutscene $15, Fara: come to my house). Next: the Massan mayor (stage>=4 branch gives RED_JEWEL and sets $04.2 = $22).
- EN L1: Fara is safe. Her family wants / to thank you.
- EN L2: Go to the mayor's house in Massan / and collect your reward.
- DE L1: Fara ist gerettet. Ihre Familie / will dir danken.
- DE L2: Geh zum Haus des Bürgermeisters / in Massan: Belohnung abholen.

### `stage05_to_ryuma`
- when: `stage>=5`
- evidence: $04.2 = $22 (mayor gave RED_JEWEL; road repair crew clears the landslide, cutscenes $16-$18). Ryuma dialogues start at stage 5.
- EN L1: Massan is done. The road west / is clear now.
- EN L2: Go through Gumi and west. Take / the fork to Ryuma.
- DE L1: Massan ist erledigt. Der Weg / nach Westen ist frei.
- DE L2: Durch Gumi und nach Westen. An / der Gabelung nach Ryuma.

### `stage05_in_ryuma`
- when: `stage>=5, room:610-629`
- evidence: In Ryuma. Next flag $02.7 = $17 TALKED_WITH_HIDDEN_VILLAGER_RYUMA (CS_00A8 hides, afraid of thieves). UNSURE: exact spot.
- EN L1: Ryuma is scared. Someone is / hiding in a corner.
- EN L2: Find the hidden villager in town / and talk to him.
- DE L1: Ryuma hat Angst. Einer versteckt / sich irgendwo in der Stadt.
- DE L2: Finde den versteckten Dörfler / und sprich mit ihm.

### `stage06_elders`
- when: `stage>=6`
- evidence: $02.7 = $17. Next: the town elders (CS_00A6 branch _1/_2 asks for help and sets $04.0 ALLOWED_TO_GO_IN_THIEVES_HIDEOUT = stage 7). UNSURE: which house.
- EN L1: Now the town elders can use / your help.
- EN L2: Talk to the Ryuma elders until / they bring up the thieves.
- DE L1: Jetzt brauchen die Ältesten / deine Hilfe.
- DE L2: Sprich in Ryuma mit den Ältesten, / bis sie die Räuber erwähnen.

### `stage07_raft`
- when: `stage>=7`
- evidence: $04.0 = $20 ALLOWED_TO_GO_IN_THIEVES_HIDEOUT. Raft pier room 183 (RYUMA_RAFT_PIER); hideout rooms 184-226. Next flag $04.1 = $21 (gang beaten).
- EN L1: The thieves hide on a cape. / You need a ride there.
- EN L2: Take the raft at Ryuma's pier / to the thieves' hideout.
- DE L1: Die Räuber hausen auf einer / Landzunge. Du brauchst Transport.
- DE L2: Nimm das Floß am Pier von Ryuma / zum Räuberversteck.

### `stage07_in_hideout`
- when: `stage>=7, room:184-226`
- evidence: Hideout rooms (Pockets cell 191, treasure room 224/225, summit 226).
- EN L1: Levers and doors everywhere. / Keep pushing deeper.
- EN L2: Free the captured mayor, then / beat whoever leads this gang.
- DE L1: Überall Hebel und Türen. Dring / immer weiter vor.
- DE L2: Befreie den Bürgermeister, dann / besiege den Anführer.

### `stage08_mayor`
- when: `stage>=8`
- evidence: $04.1 = $21 (gang beaten, mayor free). Next: mayor in Ryuma gives SAFETY_PASS + 100 golds (cutscene $21, sets $04.3 = $23 = stage 9).
- EN L1: The gang is history. The mayor / is waiting for you.
- EN L2: Back to Ryuma, talk to the mayor. / He has a pass for you.
- DE L1: Die Bande ist Geschichte. Der / Bürgermeister wartet.
- DE L2: Zurück nach Ryuma, red mit ihm. / Er hat einen Pass für dich.

### `stage09_mercator`
- when: `stage>=9`
- evidence: $04.3 = $23 SAFETY_PASS received. Mercator gate (cutscene $36 tests $23). Route room 454 ROUTE_GUMI_RYUMA_MERCATOR_GATES.
- EN L1: The pass opens a big, rich / town to you.
- EN L2: Go to Mercator: back at the fork / west of Gumi, take the other path.
- DE L1: Mit dem Pass kommst du in eine / große, reiche Stadt.
- DE L2: Geh nach Mercator: zurück zur / Gabelung, anderer Weg.

### `stage09_in_mercator`
- when: `stage>=9, room:630-710`
- evidence: In Mercator town. The castle is closed until Arthur's help (stage 15).
- EN L1: Mercator is huge. Listen to / gossip, look around the castle.
- EN L2: The front gate is closed to you. / Look for another way in.
- DE L1: Mercator ist riesig. Hör dich / um und schau ums Schloss.
- DE L2: Das Haupttor ist zu. Such / einen anderen Weg hinein.

### `stage10_castle_back`
- when: `stage>=10`
- evidence: $05.4 = $2C (UNSURE meaning; no dialogue of its own; stage 11 does not exist). Next: $05.5 = $2D SAW_ARTHUR_AT_CASTLE_BACKDOOR (rooms 639 back court, 640 button room).
- EN L1: The castle is well guarded. Take / a look at its back side.
- EN L2: Behind the castle is a court with / a button room. Someone sneaks.
- DE L1: Das Schloss ist gut bewacht. / Schau dir die Rückseite an.
- DE L2: Hinterm Schloss liegt ein Hof mit / Knopfraum. Dort schleicht wer.

### `stage12_arthur`
- when: `stage>=12`
- evidence: $05.5 = $2D SAW_ARTHUR_AT_CASTLE_BACKDOOR. Next: Madame Yard's (room 680 entrance, 707-710); the upstairs girl hints at the fortune-teller and sets $05.6 = $2E (stage 13).
- EN L1: You saw Arthur sneaking about. / Others know a trick for you.
- EN L2: Ask at Madame Yard's place. They / know how to get ahead.
- DE L1: Du hast Arthur schleichen sehen. / Andere kennen einen Trick.
- DE L2: Frag bei Madame Yard's nach. Die / wissen, wie man weiterkommt.

### `stage13_teller`
- when: `stage>=13`
- evidence: $05.6 = $2E TALKED_WITH_MADAME_YARD_GIRL_HINTING_FORTUNE_TELLER. Next: fortune-teller casts a spell (cutscene $48 sets $03.4 = $1C = stage 14). UNSURE: what the spell does.
- EN L1: A fortune-teller in town can / cast a spell for you.
- EN L2: Find her house and let her cast / it. Then try Madame Yard's.
- DE L1: Eine Wahrsagerin in der Stadt / kann dich verzaubern.
- DE L2: Such ihr Haus, lass sie zaubern. / Dann zu Madame Yard's.

### `stage14_spell`
- when: `stage>=14`
- evidence: $03.4 = $1C (spell cast). Teller: just open the door and go in. Next: $03.5 = $1D ARTHUR_GAVE_ACCESS_TO_CASTLE (stage 15).
- EN L1: The spell is cast. Shut doors / may open for you now.
- EN L2: Go through the door at Madame / Yard's and see who is inside.
- DE L1: Der Zauber wirkt. Verschlossene / Türen gehen jetzt vielleicht auf.
- DE L2: Geh bei Madame Yard's durch die / Tür und sieh, wer drin ist.

### `stage15_castle`
- when: `stage>=15`
- evidence: $03.5 = $1D ARTHUR_GAVE_ACCESS_TO_CASTLE. Gate guard (CS_00E5, stage>=F) lets you in. Next: first duke encounter ($03.7), then $12.1 = $91 (stage 16).
- EN L1: Arthur put in a word. The castle / gate lets you pass now.
- EN L2: Walk to Mercator Castle and go / in to meet the duke.
- DE L1: Arthur hat ein Wort eingelegt. / Das Schlosstor lässt dich durch.
- DE L2: Geh zum Schloss von Mercator und / triff den Herzog.

### `stage15_in_castle`
- when: `stage>=15, room:51-62`
- evidence: Throne room 51-54, entrance hallway 55-58, main hall 59-62.
- EN L1: Find the man in charge. Think / big room, big chair.
- EN L2: The duke is in the throne room. / Walk up and talk to him.
- DE L1: Such den Chef des Hauses. Denk / an großen Raum, großen Stuhl.
- DE L2: Der Herzog sitzt im Thronsaal. / Geh hin und sprich mit ihm.

### `stage16_duke_left`
- when: `stage>=16`
- evidence: $12.1 = $91 DUKE_LEFT_ROOM_AFTER_FIRST_ENCOUNTER. Next: servant takes you to the bedroom ($12.2 = $92, stage 17).
- EN L1: The duke has left. The staff / will look after you.
- EN L2: Follow the servant who offers to / show you a room.
- DE L1: Der Herzog ist gegangen. Das / Personal kümmert sich um dich.
- DE L2: Folge dem Diener, der dir ein / Zimmer zeigen will.

### `stage17_roam`
- when: `stage>=17`
- evidence: $12.2 = $92 SERVANT_BROUGHT_US_TO_BEDROOM. Next: butler / kitchen woman says dinner is ready (sets $12.3 = $93, stage 18).
- EN L1: Make yourself at home. Roam / the castle, chat with staff.
- EN L2: Talk to the butler and the kitchen / crew until dinner is announced.
- DE L1: Fühl dich wie zu Hause. Geh / durchs Schloss, red mit Leuten.
- DE L2: Sprich mit Butler und Küche, bis / das Essen angesagt wird.

### `stage18_party`
- when: `stage>=18`
- evidence: $12.3 = $93 TALKED_WITH_KITCHEN_WOMAN_BEFORE_BANQUET (CS_001E_2 / CS_0112_1). Banquet room = room 85 (2nd floor). Next: $12.4 = $94.
- EN L1: Dinner is ready. Don't be / fashionably late, hero!
- EN L2: Go to the banquet room on the / second floor of the castle.
- DE L1: Das Essen ist fertig. Komm nicht / zu spät, Held!
- DE L2: Geh zum Bankettsaal im zweiten / Stock des Schlosses.

### `stage19_sleep`
- when: `stage>=19`
- evidence: $12.4 = $94 ASSISTED_TO_MERCATOR_BANQUET (duke asks you to take down Mir). Next: go to bed in room 97 (cutscene $69, sets $14.0 = $A0 SLEPT_AT_MERCATOR_AFTER_BANQUET = stage 20).
- EN L1: Full belly, big plans. Rest up / before the big day.
- EN L2: Go to your bedroom in the castle / and go to sleep.
- DE L1: Voller Bauch, große Pläne. Ruh / dich vor dem großen Tag aus.
- DE L2: Geh in dein Schlafzimmer im / Schloss und leg dich hin.

### `stage20_tower`
- when: `stage>=20`
- evidence: $14.0 = $A0 SLEPT_AT_MERCATOR_AFTER_BANQUET. Mir's tower is sealed by a barrier; the armlet (item $1F, crypt room 651) proves worth. Zak and Dexter went to the crypt.
- EN L1: Next job: the wizard Mir. His / tower is sealed by magic.
- EN L2: Find a way past the barrier. The / crypt in Mercator looks promising.
- DE L1: Nächster Job: der Magier Mir. / Sein Turm ist magisch versiegelt.
- DE L2: Such einen Weg an der Sperre / vorbei. Die Gruft hilft dir.

### `stage20_tower_dexzak` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=20, !item:1F, flag:1A.1`
- evidence: $1A.1 = Arthur's day-2 talk (char $1E, room 83 MERCATOR_CASTLE_ARMORY_1F), SetFlagBitOnTalking CS_001E_4 code/script/en/characters/script_characters.asm:3413-3425, branch $14 = stages 20-23 (code/script/en/characters/script_characters.asm:3359): Dexter and Zak asked him how to break the barrier and went to the crypt; the crypt monsters are clever; the armlet is not won by the sword alone. No crypt location in this text.
- EN L1: Dexter and Zak beat us / to the crypt! Hurry, Nigel!
- EN L2: A barrier guards Mir's tower. / An armlet waits in the crypt.
- DE L1: Dexter und Zack sind / längst in der Gruft! Los!
- DE L2: Vor Mirs Turm ist eine Sperre. / Ein Armreif ist in der Gruft.

### `stage20_tower_arthur` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=20, !item:1F, flag:19.7`
- evidence: $19.7 = Arthur's talk at stage 19 only (branch $13, code/script/en/characters/script_characters.asm:3356), CS_001E_3 code/script/en/characters/script_characters.asm:3396-3410, room 83: magic barrier at the tower entrance, the armlet breaks it, it is in the underground crypt next to the church, traps guard it. Placed after the $1A.1 variant: with both flags the more exact one wins.
- EN L1: An armlet breaks Mir's / barrier! It's in the crypt.
- EN L2: Get the armlet from the crypt / next to the church. Traps!
- DE L1: Ein Armreif bricht die / Sperre! Er liegt in der Gruft.
- DE L2: Hol den Armreif aus der Gruft / neben der Kirche. Fallen!

### `stage20_in_crypt`
- when: `stage>=20, !item:1F, room:646-659`
- evidence: Crypt rooms 646-659 (651 = armlet room). Riddle rooms; $28.6 = $146 SAW_DEXTER_DIE_IN_CRYPT.
- EN L1: Think before you step. Riddle / rooms punish wrong answers.
- EN L2: Solve the riddle rooms, cross the / river and reach the armlet room.
- DE L1: Denk nach, bevor du gehst. / Rätselräume bestrafen Fehler.
- DE L2: Löse die Rätsel, quere den Fluss / und finde den Armreif-Raum.

### `stage20_in_crypt_dexzak` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=20, !item:1F, room:646-659, flag:1A.1`
- evidence: $1A.1 as `stage20_tower_dexzak` (CS_001E_4 code/script/en/characters/script_characters.asm:3413-3425; DE code/script/de/characters/script_characters.asm:3230-3231): the monsters down there are clever, the sword alone will never get the armlet. Overridden at stage 21 by `stage21_crypt_deeper` like its base.
- EN L1: Clever monsters here! / Use your head, not just steel!
- EN L2: The sword alone won't get you / the armlet. Think it through.
- DE L1: Schlaue Monster hier! / Erst denken, dann zuschlagen!
- DE L2: Mit dem Schwert allein findest / du den Armreif nie. Denk nach!

### `stage21_crypt_deeper`
- when: `stage>=21, !item:1F`
- evidence: $16.3 = $B3 (UNSURE: riddle part of the crypt done; Mercator motel guy: 'good practice'). Armlet next.
- EN L1: The riddles are behind you. / The prize is close.
- EN L2: Keep going in the crypt until / you hold the armlet.
- DE L1: Die Rätsel hast du hinter dir. / Der Preis ist nah.
- DE L2: Geh in der Gruft weiter, bis du / den Armreif hast.

### `stage20_have_armlet`
- when: `stage>=20, item:1F`
- evidence: ARMLET (item $1F) owned; stage may still be 20/21.
- EN L1: Nice bracelet! That should talk / the barrier into opening.
- EN L2: Take the armlet to Mir's tower / south of Mercator.
- DE L1: Schickes Armband! Damit gibt die / Sperre sicher nach.
- DE L2: Bring den Armreif zu Mirs Turm / südlich von Mercator.

### `stage20_have_armlet_arthur` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=20, item:1F, flag:19.7`
- evidence: $19.7 (CS_001E_3 code/script/en/characters/script_characters.asm:3396-3410): the armlet breaks the barrier at Mir's tower entrance.
- EN L1: We've got the armlet! / Now break Mir's barrier!
- EN L2: The armlet breaks the barrier / at Mir's tower entrance.
- DE L1: Der Armreif ist unser! / Jetzt weg mit Mirs Sperre!
- DE L2: Der Armreif bricht die Sperre / vor dem Eingang von Mirs Turm.

### `stage22_to_mir`
- when: `stage>=22`
- evidence: $14.6 = $A6 (armlet gained; Mercator man: 'Is that the armlet?'). Tower: rooms 750-784 (784 boss arena), approach 464-465 / 475. Next: $17.3 SAW_MIRO_CLOSE_KEYDOOR, $17.6 TOOK_PURPLE_JEWEL, then $17.7 = $BF (stage 23).
- EN L1: The barrier gives way to the / armlet. Go and meet Mir.
- EN L2: Mir's tower is south of Mercator. / Hold the armlet up at the door.
- DE L1: Die Sperre weicht dem Armreif. / Geh und triff Mir.
- DE L2: Mirs Turm liegt südlich von / Mercator. Halt den Armreif hoch.

### `stage22_to_mir_arthur` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=22, flag:19.7`
- evidence: $19.7 (CS_001E_3 code/script/en/characters/script_characters.asm:3396-3410): same fact as `stage20_have_armlet_arthur`; `stage22_in_tower` (room entry) still overrides it inside the tower.
- EN L1: Arthur said the armlet / breaks the barrier. Go!
- EN L2: Walk to Mir's tower door. The / armlet breaks the barrier.
- DE L1: Laut Arthur bricht der / Armreif die Sperre. Los!
- DE L2: Geh zur Tür von Mirs Turm. Der / Armreif bricht die Sperre.

### `stage22_in_tower`
- when: `stage>=22, room:750-784`
- evidence: Mir tower interior (traps, falling spike balls room 761, boss arena 784).
- EN L1: Traps galore. Climb carefully / and save jumps for solid ground.
- EN L2: Reach the top of the tower and / talk to Mir. He may surprise you.
- DE L1: Fallen über Fallen. Klettere / vorsichtig und spring mit Bedacht.
- DE L2: Komm oben im Turm an und sprich / mit Mir. Er überrascht dich.

### `stage22_purple`
- when: `stage>=22, flag:17.6`
- evidence: $17.6 = $BE TOOK_PURPLE_JEWEL_IN_MIR_TOWER. Next: stage 23 = $17.7 = $BF.
- EN L1: Purple jewel in the bag. Time to / leave this tower behind.
- EN L2: Head back to Mercator and report / to the duke in the castle.
- DE L1: Das lila Juwel ist im Beutel. / Zeit, den Turm zu verlassen.
- DE L2: Geh zurück nach Mercator und melde / dich beim Herzog im Schloss.

### `stage23_report`
- when: `stage>=23`
- evidence: $17.7 = $BF (Mir met). Castle staff: go up and see the duke. Betrayal follows (cutscenes $8C-$91, red and purple jewels taken, dungeon $13.0).
- EN L1: The wizard was not the villain. / Back to the castle with you.
- EN L2: The duke waits upstairs in the / castle. Take the jewels along.
- DE L1: Der Magier war nicht der Böse. / Zurück ins Schloss mit dir.
- DE L2: Der Herzog wartet oben im Schloss. / Bring die Juwelen mit.

### `stage23_dungeon`
- when: `stage>=23, flag:13.0`
- evidence: $13.0 = $98 THREW_IN_DUNGEON_BY_DUKE. Dungeon rooms 107-110, 36-37; princess room 108.
- EN L1: Locked up! Typical duke. Find / a way out of the dungeon.
- EN L2: Search cells and corridors. The / princess is held down here too.
- DE L1: Eingesperrt! Typisch Herzog. Such / einen Weg aus dem Verlies.
- DE L2: Durchsuch Zellen und Gänge. Die / Prinzessin sitzt hier auch fest.

### `stage23_dungeon_lara` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=23, flag:13.0, flag:1A.0`
- evidence: $1A.0 = char $11E, CS_011E code/script/en/characters/script_characters.asm:4522-4532 (no progress gate): the women in rooms 43 / 45 (area MERCATOR_DUNGEON) say the duke holds Miss Lara, a princess, prisoner down here; go on and find her. `stage23_princess` ($20.4) overrides it.
- EN L1: Lara's locked up here! / Let's find her, Nigel!
- EN L2: The duke holds Princess Lara / down here. Go on, find her!
- DE L1: Lara sitzt hier auch! / Suchen wir sie, Niels!
- DE L2: Der Herzog hält Prinzessin / Lara hier fest. Finde sie!

### `stage23_princess`
- when: `stage>=23, flag:20.4`
- evidence: $20.4 = $104 SAW_PRINCESS_LARA_IN_MERCATOR_DUNGEON. Next: $20.5 = $105 ZAK_FLEW_OFF (stage 24).
- EN L1: You found the princess. Now find / the way up and out.
- EN L2: Follow the dungeon corridors on to / the tower exit (room 110).
- DE L1: Du hast die Prinzessin gefunden. / Jetzt: nach oben und raus.
- DE L2: Folge den Verliesgängen zum / Turmausgang (Raum 110).

### `stage24_armor`
- when: `stage>=24`
- evidence: $20.5 = $105 ZAK_FLEW_OFF_MERCATOR_DUNGEON (stage 24). Castle is invaded by armored soldiers, Arthur fights alone (CS_00FB). Next: $20.6 = $106 TALKED_WITH_ARTHUR_REVEALING_DUKE_ESCAPE.
- EN L1: Armored invaders storm the / castle! Arthur needs help.
- EN L2: Fight through the castle floors / and find General Arthur.
- DE L1: Gepanzerte Eindringlinge stürmen / das Schloss! Arthur braucht Hilfe.
- DE L2: Kämpf dich durchs Schloss und / finde General Arthur.

### `stage24_duke_fled`
- when: `stage>=24, flag:20.6`
- evidence: $20.6 = $106 TALKED_WITH_ARTHUR_REVEALING_DUKE_ESCAPE. Ryuma lighthouse is dark (Sun Stone stolen by the apprentice, thrown into Greenmaze, room 564 GREENMAZE_SUNSTONE). Greenmaze via tunnel room 645 north of the castle. Dog (Einstein) needs an EkeEke.
- EN L1: The duke sailed off. But no ship / sails with a dark lighthouse.
- EN L2: Sun Stone is in Greenmaze, north / of the castle. Bring EkeEke.
- DE L1: Der Herzog ist weg. Aber ohne / Leuchtturm fährt kein Schiff.
- DE L2: Der Sonnenstein liegt im Irrgarten / nördlich des Schlosses. EkeEke!

### `stage25_dog`
- when: `stage>=25, !item:20, !item:1E`
- evidence: $24.4 = $124 (dog cured with EkeEke, cutscene $A5; also sub3 = 1). Whistle (item $20) comes from the dog's owner (CS_0038, CSA_00C6). UNSURE: owner location.
- EN L1: Dog saved! Its owner is sure / to be thankful.
- EN L2: Visit the dog's owner. The / reward is a handy whistle.
- DE L1: Hund gerettet! Sein Besitzer ist / sicher dankbar.
- DE L2: Besuch den Besitzer für eine / Belohnung: eine Pfeife.

### `stage25_whistle`
- when: `stage>=25, item:20, !item:1E`
- evidence: EINSTEIN_WHISTLE owned. Greenmaze (rooms about 545-596, UNSURE), Sun Stone room 564, $28.5 SAW_KAYLA_CUTSCENE_IN_GREENMAZE.
- EN L1: Whistle in hand. Greenmaze is a / maze of trees and ledges.
- EN L2: Walk Greenmaze and whistle where / stuck. The dog leads to the stone.
- DE L1: Pfeife in der Hand. Der Irrgarten / ist ein Wirrwarr aus Bäumen.
- DE L2: Geh durch den Irrgarten und pfeif, / wenn du hängst. Der Hund hilft.

### `stage25_whistle_arthur` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=25, item:20, !item:1E, flag:20.6`
- evidence: $20.6 = TALKED_WITH_ARTHUR_REVEALING_DUKE_ESCAPE (Arthur's cutscene 0xA0, see stage24_duke_fled): the Ryuma lighthouse is dark because the Sun Stone was stolen and thrown into Greenmaze; Greenmaze is reached through the tunnel north of the castle. No direction inside Greenmaze (that is Gol's line, stage25_whistle_gol, which comes later in the list and wins).
- EN L1: Dark lighthouse? Blame / the thief, Nigel!
- EN L2: The Sun Stone is in Greenmaze, / north of the castle.
- DE L1: Leuchtturm dunkel? Der / Dieb war's, Niels!
- DE L2: Sonnenstein: Grünes Labyrinth, / nördlich vom Schloss.

### `stage25_whistle_gol` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=25, item:20, !item:1E, flag:1A.7`
- evidence: $1A.7 = Old Gol (char $3A, room 561, Greenmaze), CS_003A code/script/en/characters/script_characters.asm:5502-5546, only while the Sun Stone is not owned (5503-5505): keeper of Greenmaze, the gnomes changed the routes, and BOTH yes / no answers end with 'the Sun Stone is in the northeast sector of this forest' (5539, 5542; HandleYesNoPrompt code/scripthandling/scriptfuncs4.asm:54-70). The tree-top / underpass tips come only on 'yes' -> not used.
- EN L1: Gol said: northeast! / The gnomes moved the paths...
- EN L2: The Sun Stone lies in the / northeast part of Greenmaze.
- DE L1: Gol sagt: Nordosten! / Die Zwerge verlegen die Wege!
- DE L2: Im Grünen Labyrinth liegt der / Sonnenstein im Nordosten.

### `stage25_sunstone`
- when: `stage>=25, item:1E`
- evidence: SUN_STONE (item $1E) owned. Keeper in Ryuma lighthouse (rooms 625-629); cutscene $BB. Next: $26.1 = $131 (stage 26).
- EN L1: Sun Stone found! Ryuma's light / needs it badly.
- EN L2: Bring it to the lighthouse keeper / in Ryuma.
- DE L1: Sonnenstein gefunden! Ryumas Licht / braucht ihn dringend.
- DE L2: Bring ihn zum Leuchtturmwärter / in Ryuma.

### `stage26_ship`
- when: `stage>=26`
- evidence: $26.1 = $131 (lighthouse lit; cutscene $C1: free ship to Verla). Docks rooms 641-644. $28.4 TOOK_BOAT_TO_VERLA.
- EN L1: The lighthouse shines again! A / free ship ride is yours.
- EN L2: Take the ship to Verla at the / Mercator docks south of town.
- DE L1: Der Leuchtturm strahlt wieder! / Freie Überfahrt für dich.
- DE L2: Nimm das Schiff nach Verla am / Hafen südlich von Mercator.

### `stage26_verla`
- when: `stage>=26, room:711-721`
- evidence: Verla town (711 empty / 712 saved variant); people were taken to the mines (rooms 227-269).
- EN L1: Verla is empty. Soldiers took / everyone to the mines.
- EN L2: Head to the Verla Mines and free / the villagers.
- DE L1: Verla ist leer. Soldaten haben / alle in die Minen gebracht.
- DE L2: Geh in die Minen von Verla und / befreie die Dorfbewohner.

### `stage26_mines`
- when: `stage>=26, room:227-269`
- evidence: Verla Mines. Flags in order of room numbers (UNSURE): $26.3 white knights, $26.4 golden knight, $26.7 = $137 DEX_KILLED (arena 242), Marley rooms 264-267 ($28.0 = $140 = stage 27).
- EN L1: Knights, jars, lava: the mines / are a long puzzle.
- EN L2: Push through. The boss Marley / waits at the far end.
- DE L1: Ritter, Krüge, Lava: die Minen / sind ein langes Rätsel.
- DE L2: Kämpf dich durch. Boss Marley / wartet ganz hinten.

### `stage26_dex_down`
- when: `stage>=26, flag:26.7, room:227-269`
- evidence: $26.7 = $137 DEX_KILLED; Marley is deeper.
- EN L1: Dex is down. One more big / enemy lurks deeper in.
- EN L2: Go on to the lava rooms. Marley / is the last boss here.
- DE L1: Dex ist besiegt. Ein großer / Gegner lauert noch tiefer.
- DE L2: Weiter zu den Lavaräumen. Marley / ist der letzte Boss hier.

### `stage27_destel`
- when: `stage>=27`
- evidence: $28.0 = $140 MARLEY_KILLED (miners free, tunnel to Destel usable; $27.5 = $13D PRISONERS_OPENED_UNFINISHED_TUNNEL). Destel = rooms 726-736, well 270-290.
- EN L1: The miners are free! The duke / went on to Destel.
- EN L2: Follow the mine tunnel west to / the dwarf village, Destel.
- DE L1: Die Bergleute sind frei! Der / Herzog zog nach Destel weiter.
- DE L2: Folge dem Minentunnel nach Westen / zum Zwergendorf Destel.

### `stage27_in_destel`
- when: `stage>=27, room:726-736`
- evidence: Destel village. Well entrance there.
- EN L1: Quiet village, angry dwarves. / Something rumbles underground.
- EN L2: The well in Destel leads to an old / cave. Climb down and go on.
- DE L1: Ruhiges Dorf, wütende Zwerge. / Unten rumort es.
- DE L2: Der Brunnen in Destel führt zu / einer alten Höhle. Steig hinab.

### `stage27_duke_raft`
- when: `stage>=27, flag:28.7`
- evidence: $28.7 = $147 SAW_DUKE_MERCATOR_ON_RAFT_NEAR_DESTEL (cutscene $D7-$D9). Well rooms 270-290.
- EN L1: The duke floats off on a raft. / Time to find another way.
- EN L2: Go down the well beneath Destel / to follow him to the lake.
- DE L1: Der Herzog treibt auf einem Floß / davon. Such einen anderen Weg.
- DE L2: Steig in Destel den Brunnen hinab / und folge ihm zum See.

### `stage27_in_well`
- when: `stage>=27, room:270-290`
- evidence: Destel Well (283 watery hub, 287 room before boss).
- EN L1: The well is deep and wet. Look / for paths, ledges, switches.
- EN L2: Fight your way through and out / to the lake on the other side.
- DE L1: Der Brunnen ist tief und nass. / Such Wege, Absätze, Schalter.
- DE L2: Kämpf dich durch und hinaus zum / See auf der anderen Seite.

### `stage28_lake`
- when: `stage>=28`
- evidence: $2A.0 = $150 SAW_DUKE_ENTERING_LAKE_SHRINE. Lake exterior rooms 523/524, shrine 291-354.
- EN L1: The duke went into the lake / shrine. Follow him in.
- EN L2: Enter the Lake Shrine and work up / to the boss at the top.
- DE L1: Der Herzog ging in den Seeschrein. / Folge ihm hinein.
- DE L2: Betritt den Seeschrein und arbeite / dich zum Boss ganz oben vor.

### `stage28_in_shrine`
- when: `stage>=28, room:291-354`
- evidence: Lake Shrine (305 save room, 306 keydoor 0F, 308 entrance). Zak on the bridge: $2A.7 = $157.
- EN L1: Big shrine, many floors, many / keys. Save when you can.
- EN L2: Look for switches and keys to open / the way upward. Be patient.
- DE L1: Großer Schrein, viele Etagen, / viele Schlüssel. Speicher oft.
- DE L2: Such Schalter und Schlüssel für / den Weg nach oben. Hab Geduld.

### `stage29_done`
- when: `stage>=29`
- evidence: $2A.5 = $155 FINISHED_LAKE_SHRINE. UNSURE: what exactly follows; the Mercator teleporter ($27.1) is the next stage-list flag.
- EN L1: Shrine done. The duke's trail / leads back to Mercator.
- EN L2: Go back to Mercator Castle. It / has changed since you left.
- DE L1: Schrein geschafft. Die Spur des / Herzogs führt nach Mercator.
- DE L2: Geh zurück ins Schloss von / Mercator. Dort hat sich was getan.

### `stage30_castle_tele`
- when: `stage>=30`
- evidence: $2A.6 = $156 (UNSURE: unnamed). Mercator Castle tower/passage rooms 34-37 (UNSURE which holds the teleporter).
- EN L1: A hidden way is about to open / in Mercator Castle.
- EN L2: Check the castle tower and the / passage rooms for a teleporter.
- DE L1: In Mercators Schloss öffnet sich / bald ein verborgener Weg.
- DE L2: Schau im Schlossturm und in den / Gängen nach einem Teleporter.

### `stage31_knc`
- when: `stage>=31`
- evidence: $27.1 = $139 OPENED_MERCATOR_TELEPORTER_TO_KNC. King Nole's Cave rooms 144-172, teleporter to Kazalt = room 170.
- EN L1: A new way is open in Mercator. / King Nole's cave awaits.
- EN L2: Use the teleporter in Mercator / Castle to reach King Nole's cave.
- DE L1: In Mercator ist ein Weg offen. / Die Höhle von König Nole ruft.
- DE L2: Nimm den Teleporter im Schloss von / Mercator zur Höhle von König Nole.

### `stage31_in_cave`
- when: `stage>=31, room:144-172`
- evidence: King Nole's Cave. Teleporter to Kazalt = room 170 (KN_CAVE_TELEPORTER_TO_KAZALT).
- EN L1: The cave is full of golems and / traps. Mind your footing.
- EN L2: Work to the teleporter at the end. / It takes you to Kazalt.
- DE L1: Die Höhle ist voller Golems und / Fallen. Achte auf deinen Schritt.
- DE L2: Arbeite dich zum Teleporter am / Ende. Er bringt dich nach Kazalt.

### `stage31_kazalt`
- when: `stage>=31, room:737-749`
- evidence: Kazalt rooms 737-749 (shop 747, church 749). Labyrinth exterior = room 362.
- EN L1: Last town of the trip. Heal, / save and stock up here.
- EN L2: Then head on to the labyrinth of / King Nole. It is a long one.
- DE L1: Letzte Stadt der Reise. Heilen, / speichern, Vorräte kaufen.
- DE L2: Dann weiter zum Labyrinth von / König Nole. Es ist lang.

### `stage31_labyrinth`
- when: `stage>=31, room:355-423`
- evidence: King Nole's Labyrinth (355-423). Logs (item $2F) from the tree in room 415 for rafts; $2B.1 = $159 SECOND_RAFT_PLACED_IN_KNL; ice path to the palace = room 388; stairway to Nole = 421.
- EN L1: A huge maze. Rivers need rafts, / rafts need logs from trees.
- EN L2: Cut a tree for logs, then place a / raft. Keep an eye on the map.
- DE L1: Ein riesiges Labyrinth. Flüsse / brauchen Flöße, Flöße Holz.
- DE L2: Fäll einen Baum für Holz und lege / ein Floß. Nutze die Karte.

### `stage31_labyrinth_father` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=31, room:355-423, flag:1C.0, !flag:29.5`
- evidence: $1C.0 = the old dwarf (char $142, room 406), CS_0142 code/script/en/characters/script_characters.asm:5608-5618, text opcode $14E0 on the first talk: you need a raft to go down the river; find his son and get logs. Stale once the logs are taken ($29.5, behaviour 752 in room 415) -> `!flag:29.5`.
- EN L1: A raft for the river! / Find the dwarf's son first.
- EN L2: Find the old dwarf's son and / get logs to build a raft.
- DE L1: Ein Floß muss her! / Such erst den Sohn des Zwergs.
- DE L2: Finde den Sohn des alten / Zwergs und hol Holzstämme.

### `stage31_labyrinth_son` (added 2026-11-14, flag-gated, section 4e)
- when: `stage>=31, room:355-423, flag:1C.1, !flag:29.5`
- evidence: $1C.1 = the son, cutscene XS_012B code/script/en/cutscenes/script_cutscenes.asm:1265-1305 (via CSA_0138 code/scripthandling/dialogueactions.asm:3892-3897), sets $1C.1 at XS:1287 only if $1C.0 is set: go on up and cut the tree to make a raft. He does not hand over the logs (room 415 does, $29.5) -> `!flag:29.5`; `stage31_raft2` / `stage31_taunt` still override.
- EN L1: Up we go! That tree / will make a fine raft!
- EN L2: Climb up and cut down the / tree to make a raft.
- DE L1: Hoch mit uns! Der Baum / gibt ein prima Floß!
- DE L2: Klettere hoch und fäll den / Baum für ein Floß.

### `stage31_raft2`
- when: `stage>=31, flag:2B.1, room:355-423`
- evidence: $2B.1 = $159 SECOND_RAFT_PLACED_IN_KNL.
- EN L1: The second raft is in place. / The way on is open.
- EN L2: Follow the maze towards the ice / path that leads to the palace.
- DE L1: Das zweite Floß liegt bereit. / Der Weg ist frei.
- DE L2: Folge dem Labyrinth zum Eispfad, / der zum Palast führt.

### `stage31_taunt`
- when: `stage>=31, flag:2B.7, room:355-423`
- evidence: $2B.7 = $15F SAW_DUKE_TAUNTING_IN_SHELL_BREAST_ROOM.
- EN L1: The duke is just ahead, and he / loves to gloat. Chase him.
- EN L2: Keep going. The palace stairway / is near. Heal before it.
- DE L1: Der Herzog ist dicht vor dir und / gibt an. Jag ihm nach.
- DE L2: Weiter so. Die Palasttreppe ist / nah. Heile dich vorher.

### `stage31_palace`
- when: `stage>=31, room:115-138`
- evidence: King Nole's Palace rooms 115-138; pillar hallway 114, Nole arena 111, Gola arena 112 (113 cinematic).
- EN L1: Nole's palace. The end is near. / Don't rush, check every room.
- EN L2: Find the way to the pillar hallway / that leads to the arenas.
- DE L1: Noles Palast. Das Ende naht. / Nicht hetzen, jeden Raum prüfen.
- DE L2: Such den Weg zum Säulengang, der / zu den Arenen führt.

### `stage31_final`
- when: `stage>=31, room:111-114`
- evidence: Pillar hallway 114, Nole arena 111, Gola arena 112/113: the last fights. Gola was slain in cutscene $144.
- EN L1: Final stretch. Heal up, eat / an EkeEke, then go.
- EN L2: Beat the guardian in the arena. / You can do it, Nigel!
- DE L1: Endspurt. Heil dich, iss einen / EkeEke und los.
- DE L2: Besiege den Wächter in der Arena. / Du schaffst das, Nigel!

### `stage01_prospero_oldman` (heard-gated, 4f)
- when: `stage>=1, heard:0178|017B|0182`
- evidence: 0178 CS_007F code/script/en/characters/script_characters.asm:210-214 / 017B CS_0080 code/script/en/characters/script_characters.asm:229-232 (Massan, stage 0 only), 0182 'Pockets' CS_0003_1 code/script/en/characters/script_characters.asm:246-251 + 280-286 (stage 0-2): a sage / old man lives in the Waterfall Shrine and will know (DE 'der Alte' / 'der Weise im Wasserfallschrein'). Room 180 holds Prospero (ROOMS.md:159), his stage-1 branch sets $00.0 (code/script/en/characters/script_characters.asm:570-576). Prospero is NOT named; no Idol Stone. Placed after stage01_prospero, stage02_fara overrides.
- EN L1: The Waterfall Shrine! / Its old sage may know more.
- EN L2: Visit the old sage in the / Waterfall Shrine and ask him.
- DE L1: Der Wasserfallschrein! / Der weise Alte dort weiß Rat!
- DE L2: Geh zum Weisen im / Wasserfallschrein. Frag ihn!

### `stage02_fara_prospero` (heard-gated, 4f)
- when: `stage>=2, heard:01C5`
- evidence: 01C5 Prospero CS_0008_1 code/script/en/characters/script_characters.asm:630-636 (needs $02.2) / CS_0008 branch $0003 code/script/en/characters/script_characters.asm:581-585: the Gumi are tricked by the Orcs, Fara is in danger (DE 'von den Orks getäuscht'). Not 01C6 (shrine name DE only), no boss name. Placed after stage02_fara_seen.
- EN L1: Orcs fool the Gumi?! / Poor Fara is in danger!
- EN L2: Orcs trick the Gumi and Fara / is in danger. On to Gumi!
- DE L1: Orks täuschen Gumi?! / Fara ist in großer Gefahr!
- DE L2: Die Orks täuschen die Gumi, / Fara ist in Gefahr. Nach Gumi!

### `stage03_need_stone_item` (heard-gated, 4f)
- when: `stage>=3, !item:31, heard:016C`
- evidence: 016C farmer CS_007D branch $0003 code/script/en/characters/script_characters.asm:165-167 (stage 3 only): they used something strange to open the door (DE 'irgendwas Komisches'). No stone named. stage03_have_stone / stage03_door_open still override.
- EN L1: A strange thing opens / that door! Let's find it.
- EN L2: The Gumi used something odd / to open that door. Find it!
- DE L1: Was Komisches öffnet / die Tür! Suchen wir es!
- DE L2: Die Gumi öffneten die Tür mit / irgendwas Komischem. Such es!

### `stage05_to_ryuma_fork` (heard-gated, 4f)
- when: `stage>=5, heard:01A0`
- evidence: 019E-01A0 CS_0083 code/script/en/characters/script_characters.asm:383-397 (Massan room 592, stages 0-1 and 4+; one ContinuePrompt chain, gate = last box 01A0): past Gumi the road splits at the sea, right = Mercator, left = Ryuma (harbour, lighthouse). Carries the fork / Ryuma fact the base stage05_to_ryuma L2 lost (4c).
- EN L1: To Ryuma, Nigel! Past / Gumi, left at the sea.
- EN L2: Past Gumi the road splits at / the sea. Left goes to Ryuma.
- DE L1: Auf nach Ryuma! Hinter / Gumi am Meer links, Niels!
- DE L2: Hinter Gumi teilt sich der Weg / am Meer: links nach Ryuma.

### `stage06_elders_meeting` (heard-gated, 4f)
- when: `stage>=6, heard:024C|024D`
- evidence: 024C CS_00A4 branch $0005 code/script/en/characters/script_characters.asm:1267-1272 / 024D (+024E) branch $0006 code/script/en/characters/script_characters.asm:1273-1277, Ryuma room 622: people hold a meeting in that house (024C); the mandatory request is CS_00A6_1 in the same room (code/script/en/characters/script_characters.asm:1360-1369). The text uses only the 024C fact (the mayor part is in 024D/024E only). `!flag:04.0` dropped (stage07_raft comes later).
- EN L1: That house with the / meeting! Let's go back.
- EN L2: Talk again to the people / holding a meeting in Ryuma.
- DE L1: Die Leute mit der / Besprechung! Nochmal hin!
- DE L2: Sprich nochmal mit den Leuten / der Besprechung in Ryuma.

### `stage18_party_floor` (heard-gated, 4f)
- when: `stage>=18, heard:040D|0413|044E|0474`
- evidence: maids 040D CS_00FC code/script/en/characters/script_characters.asm:3906-3908, 0413 CS_00FD code/script/en/characters/script_characters.asm:3933-3935 (room 55), 044E CS_0109 code/script/en/characters/script_characters.asm:4192-4194 (room 88), 0474 CS_0112 code/script/en/characters/script_characters.asm:4370-4372 (rooms 68/70/85), all branch $0012 = stage 18: the banquet hall is upstairs (common to all four in EN + DE; 'second floor' only in some), so the text says 'upstairs' / 'oben'. stage19_sleep overrides.
- EN L1: Banquet's upstairs! / Come on, I'm starving!
- EN L2: The banquet room is upstairs / in the castle.
- DE L1: Das Bankett ist oben! / Komm, ich verhungere!
- DE L2: Der Bankettsaal ist oben / im Schloss.

### `stage20_tower_barrier_seen` (heard-gated, 4f)
- when: `stage>=20, !item:1F, heard:02FD|0451|067F`
- evidence: 02FD CS_00C3 code/script/en/characters/script_characters.asm:2264-2266 (room 673, stage 20-22), 0451 CS_010A code/script/en/characters/script_characters.asm:4210-4212 (library 74, stage 20-23), 067F = system message at the tower door (cutscene 0x07B, code/script/en/cutscenes/script_cutscenetable.asm:471-472): a barrier blocks the tower door. No Arthur, no armlet.
- EN L1: A barrier blocks Mir's / tower! How do we break it?
- EN L2: A barrier blocks the door of / Mir's tower. Find a way past.
- DE L1: Eine Barriere vor Mirs / Turm! Wie kriegen wir die weg?
- DE L2: Eine Barriere sperrt die Tür / von Mirs Turm. Such einen Weg.

### `stage20_tower_barrier` (heard-gated, 4f)
- when: `stage>=20, !item:1F, heard:042E`
- evidence: 042D/042E butler CS_0021 branch $0013 code/script/en/characters/script_characters.asm:4061-4066 (rooms 51/55/85, stage 19+); gate 042E = last box (DE: barrier in 042D, 'General Arthur hat einen Weg gefunden, sie zu brechen' needs 042E; EN 'was seekin' a way to break through it'): barrier at Mir's tower door, Arthur knows about breaking it -> ask him.
- EN L1: Arthur knows about the / barrier! Let's ask him.
- EN L2: A barrier seals Mir's tower. / Ask General Arthur about it.
- DE L1: Arthur weiß was über / die Barriere! Frag ihn!
- DE L2: Mirs Turm hat eine Barriere. / Frag General Arthur danach.

### `stage20_tower_crypt` (heard-gated, 4f)
- when: `stage>=20, !item:1F, heard:03B1`
- evidence: 03B1 CS_00E2 branch $0014 code/script/en/characters/script_characters.asm:3190-3194 (room 630, stage 20+): Zak and Dexter went down into the crypt (DE 'in die Gruft runtergegangen'). Names known from the banquet (cutscene text 061B/061C). No location, no armlet. Flag variants $1A.1 / $19.7, crypt room and armlet entries come later and override.
- EN L1: Zak and Dexter are in / the crypt! After them!
- EN L2: Zak and Dexter went down / into the crypt. Find it!
- DE L1: Zack und Dexter sind / in der Gruft! Hinterher!
- DE L2: Zack und Dexter sind in die / Gruft gestiegen. Finde sie!

### `stage25_whistle_jump` (heard-gated, 4f)
- when: `stage>=25, item:20, !item:1E, heard:0264`
- evidence: 0263/0264 Ryuma CS_00A6 branch $0018 code/script/en/characters/script_characters.asm:1344-1351 (room 622, stage 24-25); gate 0264 (DE 'springen' only there): reaching the Sun Stone needs good balance and good jumping. stage25_whistle_gol ($1A.7, location) still wins.
- EN L1: Sun Stone? Balance and / good jumps, Nigel!
- EN L2: Reaching the Sun Stone takes / balance and good jumping.
- DE L1: Zum Sonnenstein? Gut / balancieren und springen!
- DE L2: Zum Sonnenstein brauchst du / Gleichgewicht und Sprungkraft.

### `stage26_verla_mountains` (heard-gated, 4f)
- when: `stage>=26, heard:04C8`
- evidence: 04C7/04C8 fisherman CS_011F branch $001A code/script/en/characters/script_characters.asm:4538-4542 (room 499, stage 26); gate 04C8 (DE soldiers + mountains only there): strange soldiers suddenly dragged the townspeople off to the mountains. No room condition: also beats stage26_verla / stage26_ship; the mines room entries and stage 27 override.
- EN L1: Soldiers took everyone / to the mountains?!
- EN L2: Soldiers dragged the townsfolk / off to the mountains.
- DE L1: Soldaten haben alle in / die Berge verschleppt?!
- DE L2: Seltsame Soldaten schleppten / alle Leute in die Berge.

### `stage26_mines_forks` (heard-gated, 4f)
- when: `stage>=26, room:227-269, heard:04D3`
- evidence: 04D2/04D3 miner CS_0120_1 code/script/en/characters/script_characters.asm:4590-4602 (needs $26.5; rooms 255 / 713, stage 26); gate 04D3 (DE 'den beiden anderen'): the mine forks into three tunnels, the other captives are in the other two. stage26_dex_down overrides.
- EN L1: Three tunnels! More / captives in the other two.
- EN L2: The mine forks into three / tunnels. Search the other two.
- DE L1: Drei Stollen! In den / anderen stecken noch Leute.
- DE L2: Die Mine teilt sich in drei / Stollen. Such in den anderen!

### `stage27_destel_west` (heard-gated, 4f)
- when: `stage>=27, heard:04EB`
- evidence: 04EA/04EB captive CS_0126_1 code/script/en/characters/script_characters.asm:4745-4749 (needs $26.7; rooms 242/711, stage 26): a small village lies west of the mine, the duke marched there with his soldiers. Gate = 04EB (not 04EA as in verified.md): the marching / soldiers part ends in 04EB in EN and DE (DE 04EA stops at 'wie Herzog Merkator'); 04EB is printed only by this NPC (code/script/en/characters/script_characters.asm:4748, same chain).
- EN L1: A village west of the / mine! The duke went there.
- EN L2: The duke marched his soldiers / to a village west of the mine.
- DE L1: Ein Dorf westlich der / Mine! Der Herzog zog hin.
- DE L2: Der Herzog zog mit Soldaten / ins Dorf westlich der Mine.

### `stage27_destel_tunnel` (heard-gated, 4f)
- when: `stage>=27, heard:04FA`
- evidence: 04FA CS_012A code/script/en/characters/script_characters.asm:4841-4843 (rooms 243/722, stage 27): the only way to Destel is through (the tunnel in) the mine.
- EN L1: Destel? Only through / the mine's tunnel!
- EN L2: The only way to Destel is / the tunnel in the mine.
- DE L1: Nach Destel? Nur durch / den Minentunnel!
- DE L2: Nach Destel kommt man nur / durch den Tunnel in der Mine.

### `stage27_destel_duke` (heard-gated, 4f)
- when: `stage>=27, heard:04DF`
- evidence: 04DF CS_0123 code/script/en/characters/script_characters.asm:4664-4668 (rooms 269/724, stage 27): the duke and his soldiers went to Destel. The 'peaceful dwarves' part is in 04E0 and not used. Order west < tunnel < duke = the most precise wins.
- EN L1: To Destel! The duke / and his soldiers went there.
- EN L2: The duke and his soldiers / went to Destel. Follow them!
- DE L1: Ab nach Destel, Niels! / Der Herzog zog dorthin.
- DE L2: Der Herzog und seine Soldaten / zogen nach Destel. Hinterher!

### `stage27_destel_well` (heard-gated, 4f)
- when: `stage>=27, flag:28.7, heard:0511`
- evidence: 0511 Destel dwarf CS_0131 branch $001B code/script/en/characters/script_characters.asm:4958-4960 (room 726, stage 27): the well is the entrance to an ancient cave where monsters live (EN tone 'The chief sealed it!' is not in DE nor the original: not used). Only after the raft scene ($28.7), else it would point too early. stage27_in_well overrides.
- EN L1: That well leads to an / old cave! Monsters, eek!
- EN L2: The well in Destel leads into / an ancient monster cave.
- DE L1: Der Brunnen führt in / eine alte Höhle! Monster!
- DE L2: Der Brunnen in Destel ist der / Eingang zu einer Monsterhöhle.

### `stage31_kazalt_gatekeepers` (heard-gated, 4f)
- when: `stage>=31, room:737-749, heard:052B`
- evidence: 052A/052B Kazalt dwarf CS_0138 code/script/en/characters/script_characters.asm:5079-5084 (room 744, no stage gate); gate 052B ('beat them to reach the palace' / DE 'öffnet sich das Tor zum Palast'): three monsters live in the labyrinth. Named only generically (EN 'Gehenna's Gatekeepers' / DE 'Torwächter der Hölle' differ).
- EN L1: Beat three monsters in / the maze to reach the palace!
- EN L2: Beat the maze's three monsters / to reach the palace.
- DE L1: Drei Monster hausen im / Labyrinth. Besieg sie!
- DE L2: Erst die drei Monster im / Labyrinth, dann der Palast!

### `stage31_labyrinth_gatekeepers` (heard-gated, 4f)
- when: `stage>=31, room:355-423, heard:052B`
- evidence: same as stage31_kazalt_gatekeepers (052B, code/script/en/characters/script_characters.asm:5079-5084), shown inside the Labyrinth. stage31_labyrinth_father / _son, stage31_raft2, stage31_taunt override.
- EN L1: Monsters in this maze! / Beat all three, Nigel!
- EN L2: Beat all three monsters here / to reach the palace.
- DE L1: Drei Monster! Besieg / alle, dann zum Palast!
- DE L2: Besieg alle drei Monster hier, / dann geht das Palasttor auf.

### `stage14_spell` (texts changed 2026-11-14, 4f ungated sharpening)
- when: `stage>=14`
- evidence: CSA_003D (code/scripthandling/dialogueactions.asm:832-847) runs cutscene 0x48 (sets $03.4 = stage 14) and, when the spell was accepted, always cutscene 0x49 (script_cutscenetable.asm:278-281): 05EC 'Now you can get into the Madame Yard's of your dreams!' / DE 'Jetzt kommst du bei Madame Yard hinein!' -> L1 may name Madame Yard's. L2 unchanged.
- EN L1: Madame Yard's lets us / in now! Let's go, Nigel!
- EN L2: Go through the door at Madame / Yard's and see who is inside.
- DE L1: Bei Madame Yard kommen / wir jetzt rein, Niels!
- DE L2: Geh bei Madame Yard's durch die / Tür und sieh, wer drin ist.

### `stage07_raft` (texts changed 2026-11-14, 4f ungated sharpening + 4c fix)
- when: `stage>=7`
- evidence: both and only $04.0 setters print 025D right after the flag (CS_00A6_1 code/script/en/characters/script_characters.asm:1360-1369, CS_00A6_2 code/script/en/characters/script_characters.asm:1380-1383): 'Their hideout's the cave on the cape. Cross by raft' / DE 'Ihr Versteck ist die Höhle am Kap. Mit dem Floß...'. The old L2 'Ryuma's pier' is NOT in 025D -> removed.
- EN L1: A cave on the cape! / Raft over there, Nigel!
- EN L2: The thieves hide in the cave / on the cape. Cross by raft.
- DE L1: Die Höhle am Kap! Mit / dem Floß rüber, Niels!
- DE L2: Die Diebe hausen in der Höhle / am Kap. Mit dem Floß rüber!

### `stage18_party` (texts changed 2026-11-14, 4f 4c fix)
- when: `stage>=18`
- evidence: all $12.3 setters (Arthur CS_001E_2 code/script/en/characters/script_characters.asm:3386-3388, maid CS_0112_1 code/script/en/characters/script_characters.asm:4385-4387, XS_005D script_cutscenes.asm:494-501) name the banquet hall, none the floor -> 'second floor' removed from the base L2; it lives in stage18_party_floor ('upstairs').
- EN L1: The banquet's ready! / Come on, I'm starving!
- EN L2: Go to the banquet room / in the castle.
- DE L1: Das Bankett beginnt! / Komm, ich verhungere!
- DE L2: Geh zum Bankettsaal / im Schloss.

### `stage05_to_ryuma` (L2 changed 2026-11-14, 4f 4c fix)
- when: `stage>=5`
- evidence: the fork / Ryuma are told only by the optional CS_0083 (01A0); the stage-5 event is the Red Jewel -> base L2 no longer names the fork or Ryuma (stage05_to_ryuma_fork carries them). L1 unchanged.
- EN L1: Massan is done! West, Nigel, the treasure won't wait!
- EN L2: Go through Gumi and follow / the road west.
- DE L1: Massan ist erledigt! Nach Westen, der Schatz wartet nicht!
- DE L2: Geh durch Gumi und folg / dem Weg nach Westen.


## 6. UNSURE list (to verify on the Deck, see the id in the json)

1. `stage03_need_stone`: where the IDOL_STONE comes from. The Waterfall Shrine (rooms 174-182) is assumed (Massan villagers send you to the sage there); the stone could also be in Gumi.
2. `stage06_elders`: which Ryuma NPC sets $04.0 (CS_00A6 branches _1/_2 are the elders' request).
3. `stage10_castle_back`: meaning of $05.4 (0x02C); stage 11 does not exist.
4. `stage13_teller` / `stage14_spell`: what the fortune-teller spell does and which door follows (Madame Yard's, rooms 680 / 707-710).
5. `stage21_crypt_deeper`: $16.3 (0x0B3) assumed to be the end of the riddle part of the crypt (motel owner: "good practice").
6. `stage22_to_mir`: $14.6 (0x0A6) assumed to be the armlet; tower location "south of Mercator" from a townsperson line.
7. `stage24_armor` / `stage24_duke_fled`: order $20.5 -> Arthur ($20.6) -> Ryuma lighthouse / Greenmaze; dog location (tunnel room 645 side) not confirmed.
8. `stage25_dog`: the whistle comes from the dog's owner (CS_0038); owner location unknown.
9. `stage25_whistle`: Greenmaze room range not named in ROOMS.md (only 564 GREENMAZE_SUNSTONE), so no room refinement was added there.
10. `stage26_mines`: order of knights / Dex / Marley in the mines (by room numbers only).
11. `stage29_done` / `stage30_castle_tele`: what $2A.6 (0x156) marks and where the Mercator teleporter stands (rooms 34-37 guessed).
12. `stage31_*`: Kazalt, Labyrinth and Palace hints use room ranges only; the Gola relic items (nail $37, horn $38, fang $39, eye $2B) were not tied to any step.
