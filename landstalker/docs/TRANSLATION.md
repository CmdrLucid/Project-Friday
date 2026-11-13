# TRANSLATION - style guide for the German text and the English 'original tone' text (2026-11-13)

Technique: `docs/TEXT_LAYER.md` (hooks, language file format, langbuild). This file = HOW we write.
Our own text only: no Japanese / German / English ROM text is copied into git (names are the exception: they are needed as data).

## 1. Decisions (user, 2026-11-13)
- Languages: **Deutsch** (`lang/de.json`) and later **English (original tone)** (`lang/en_tone.json`, a separate menu language; the original English stays the untouched default).
- **Tone and personality come from the JAPANESE original** (the first version of the game); content and the split into strings follow the English release, because the game calls the English string ids. Free translation is fine when the feeling stays; not 1:1.
- **Names**: German = the names of the German release 'Die Schätze von König Nolo' (Niels, Flora, Nolo, Herzog / Dux, Merkator, Kasalt, Zack, Juna, Geier, Taler ...); English = the English release names. Option **Names: Localized / Japanese** (LK_LGNAMES v1) swaps in the Japanese originals (Ryle, Kara, Goose ...), table `lang/names.json`.
- **Mixed case** (the German release printed dialogue in capitals only, its font had no lower case); capitals only where the English uses them (shouts, signs).
- **No dialect** in German (the Japanese villagers of Massan speak a strong rural dialect; maybe later a separate fun variant). Old men may sound old-fashioned.
- **System texts**: take the cheekier Japanese variants where they fit better (e.g. trying to make Friday WEAR an item, the island progress told by 'Bunny-chan').

## 2. Characters (from reading the Japanese text; how they should sound)
| Character | Japanese original | English release | German direction |
|---|---|---|---|
| Friday / Flora | childlike, girlish, very emotional; easily offended, jealous, sulks and sticks her tongue out; hates being called 'little one' ('My name is Friday!'); calls the hero by his plain name | tough, sassy American ('The name's Friday, sister!'), outbursts toned down | spontaneous, cheeky, emotional; 'Bäh!', 'Hmpf!', 'Niels, du Blödmann!' allowed; never cool-adult |
| Nigel / Niels | silent hero; others' forms of address show the relation (Mr, young master, big brother, little one) | almost always just 'Nigel' | keep the relation in the address: 'Herr Niels', 'junger Herr', 'großer Bruder', 'Kleiner' |
| Duke Mercator / Herzog | theatrical, condescending, constant creepy chuckle, talks down to the hero | arrogant, chuckle mostly gone | 'Hehehe...', gönnerhaft ('mein lieber Niels'), theatralisch |
| Kayla | diva, high lady laugh 'Ohohoho', calls the hero 'sonny', shrill tantrums | sassy, less over the top | 'Ohohoho!', 'Kleiner', zickig ('Wie ätzend! Kiiih!') |
| Wally / Ink | comic echo duo ('Miss Kayla is beautiful~' / '...beautiful~') | same | keep the echo, drawn-out endings |
| Massan villagers | rural dialect, the boy calls the hero 'big brother' | plain | plain, warm, simple words; the boy says 'großer Bruder' |
| old men (priests, mayors, Gol) | old-man speech, formal address | neutral | gemütlich-altmodisch ('junger Freund', 'so ist es') |
| court people (castle) | very polite | 'thy' style | 'Ihr / Euch / Euer' to the hero |
Everyone else: du to Niels, Sie / Ihr only for nobles and formal staff.

## 3. Glossary (German)
gold = Taler; Duke = Herzog (speaker name Dux); Mercator = Merkator; Kazalt = Kasalt; King Nole = König Nolo; Greenmaze = Grünes Labyrinth; Lake Shrine = Seeschrein; Mir's Tower = Mirs Turm; Swamp Shrine = Sumpfschrein; Pockets = Geier; Teller = Wahrsager; Butler = Diener; Cutter = Waldstein; Royal Guard = Königliche Wache; Princess Lara of Maple = Prinzessin Lara von Ahorn; Greenpea's Playhouse = Grihnpies Spielhaus; Orc King = Ork-König; Twinkle Village = Zwinkerdorf; Diet Dahl = Diät-Dahl; Ekenol Punch = Ekenol-Punsch; Casino Arthurlier = Arthurisches Kasino; lithograph = Steintafel; Golan / Gola Emerald = Golan-Smaragd; Gehenna's Gatekeepers = Torwächter der Hölle; crypt names: Betty Ross, Ruby Stille, Hans Luftläufer, Maria Hysteria, Tim Hell, Lars E., Dirk der Dunkle, Wodini, Sack und Gasse (German release); Dahl = Dahl; EkeEke = Eke-Eke; items: `lang/de.json` names (the German release's item names).

## 4. Writing rules (technical)
- Control codes other than layout (`{Speaker}`, `{Item}`, `{Number}`, `{ContinuePrompt}`, `{WaitInput}` ...) must appear as in the English source (langbuild drops the entry otherwise); `{SoftNewLine}`, `{NewLine}`, pauses are free.
- Names of the cast as placeholders: `{=nigel}`, `{=friday}`, `{=kayla:gen}` (German genitive), keys in `lang/names.json`. Place names are written out.
- `~` in a source line = a fixed space (langwrap keeps it, never breaks there): spaced-out letters (King Nole's ghost 0860..0862), signposts with gaps ('↖~GRÜNES~LABYRINTH~~~DORF~MASSAN~↘'), and sign texts whose first line has no speaker name (Mir's tower 012C..0133 carry {Speaker} but print no name: glue the first line, compare with the English widths).
- Line width: continuation lines <= ~250 px of the text font (letters 5..11 px, space 8), the first line after a speaker name shorter (the name and ': ' come first). Aim for <= 3 lines per page; a 4th / 5th line scrolls smoothly (tested 2026-11-13) but should be rare.
- Item sentences: name first, participle after it (`{Item} gefunden.`), no article before an inserted name (TEXT_LAYER section 6).
- Each entry: `"XXXX": {"h": <sha1[:8] of the English source>, "t": "..."}` (the English source: `~/.landstalker_text/strings_us.json`, local).

## 5. Sources for the translator (local, ROM-derived, never commit)
- English: `~/.landstalker_text/strings_us.json` (tools/stringdump.py).
- Japanese / German release text: `~/Project-Friday-Test/lktest/lang/strings_jp.json`, `strings_de.json` (scratch decoders `tools/jpdump.py` / `tools/dedump.py` there; they read the disassembly's packed assets in `~/Project-Friday-Test/landstalker_disasm`; Japanese voicing marks stand BEFORE the kana in the stream).
- Matching a scene: the string order of JP and EN is similar but not equal (JP 2026 strings, EN 2175: the English split long texts); search by content, `tools/cmp.py` / `align.py` (scratch) pair the script labels.

## 6. Process
Area by area (Massan + Gumi first): read the Japanese scene, note tone / jokes, write the German line and (later) the English 'original tone' line; build; the user plays the area in German and marks what does not fit.
