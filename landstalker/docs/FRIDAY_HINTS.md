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

### `stage20_in_crypt`
- when: `stage>=20, !item:1F, room:646-659`
- evidence: Crypt rooms 646-659 (651 = armlet room). Riddle rooms; $28.6 = $146 SAW_DEXTER_DIE_IN_CRYPT.
- EN L1: Think before you step. Riddle / rooms punish wrong answers.
- EN L2: Solve the riddle rooms, cross the / river and reach the armlet room.
- DE L1: Denk nach, bevor du gehst. / Rätselräume bestrafen Fehler.
- DE L2: Löse die Rätsel, quere den Fluss / und finde den Armreif-Raum.

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

### `stage22_to_mir`
- when: `stage>=22`
- evidence: $14.6 = $A6 (armlet gained; Mercator man: 'Is that the armlet?'). Tower: rooms 750-784 (784 boss arena), approach 464-465 / 475. Next: $17.3 SAW_MIRO_CLOSE_KEYDOOR, $17.6 TOOK_PURPLE_JEWEL, then $17.7 = $BF (stage 23).
- EN L1: The barrier gives way to the / armlet. Go and meet Mir.
- EN L2: Mir's tower is south of Mercator. / Hold the armlet up at the door.
- DE L1: Die Sperre weicht dem Armreif. / Geh und triff Mir.
- DE L2: Mirs Turm liegt südlich von / Mercator. Halt den Armreif hoch.

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
