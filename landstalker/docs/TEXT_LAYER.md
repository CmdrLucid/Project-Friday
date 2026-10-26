# TEXT LAYER (languages) - design, 2026-10-26

Goal: Options > Language (English / Deutsch / later more) for the US and EU ROM with ONE ROM per player. Translations are OUR OWN text (shipped in `lang/*.json`, no ROM content);
everything decoded from a ROM (`tools/stringdump.py`, `~/.landstalker_text/`) stays local. Decision history: HANDOFF 0a120-0a121.
Why not the German ROM as a base / text source: its code differs (1169 routines), its Huffman tables and charset are its own (INDEX status 2026-10-26, FORMATS section 5).

## 1. What is replaced
| Source | Where the game reads it | Format (FORMATS section 5) |
|---|---|---|
| dialogue / messages (2175) | `PrintString $022F26` -> `InitCompString $022FCC` (string id in D0) -> Huffman `GetNextChar $023044` | compressed |
| NPC / special names, item names, menu strings (170) | `LoadUncompressedString $02949A` (A2 = entry, D7 = count - 1 afterwards) | count byte + font codes |
| intro captions, credits, save location names | own routines | later |

## 2. Hooks (wrappers via `func_table_register`, like `lk_h_awpt` in `patch_own.py`)
1. **Dialogue**: wrapper of `InitCompString $022FCC`: run the original; if a translation exists for the id: write the translated WORD STREAM into a RAM buffer, set `dword_FF1844` (alternative character source, already used by the game for inserted names: words = glyph codes, control characters = `~handler` words, `$FFFF` ends the stream, codes `$69/$6A/$6B` hyphen / breaking space / break point are handled in `GetNextChar loc_23094`) and point the Huffman source (`dword_FF1848`, set after `InitCompString` by `PrintString`) to a dummy entry `{02, 00}`: bit 0 = the end marker `$55` right after the start context (VERIFIED with `stringdump.decode_string`: 128 of 256 one-byte streams decode to the empty string). So the game never touches the original compressed text. The end of the string is then the normal `$55` of the dummy.
   Hook point detail to settle: `PrintString` calls `InitHuffmanDecomp` and stores A0 into `dword_FF1848` AFTER `InitCompString`, so the dummy pointer must be set by a second wrapper (e.g. `InitHuffmanDecomp $02469C`) or the stream is prepared there.
2. **Names**: wrapper of `LoadUncompressedString`: after the original, redirect A2 to a RAM copy of the translated entry and set D7 (count - 1).
3. **Glyphs**: the printer reads `MainFontPtr $022E84` (long in the ROM image) + 30 bytes per code, also the own renderer (`patch_owntext.py` line 28 `bus_read32(0x022E84)`). German needs ä ö ü ß Ä Ö Ü: new codes `$6C..$72` (outside the Huffman range: they only travel in the word stream, never in the compressed text), glyphs derived from a o u / S with a diaeresis in the free rows above (checked on the font) and a drawn ß; the extended font (original 0..$6B + new) lives in an EXTRA AREA appended to the in-memory ROM image (beyond 2 MB) and `$022E84` is pointed to it (no change on disk). Widths: advance = widest row, automatic.
4. Line breaking: the game wraps itself at x > `$0114` (`sub_22F66`); explicit `{NewLine}` / `{SoftNewLine}` stay where the translation puts them. German is ~15-25 % longer: text box fit is tuned by playing (8 lines per box).

## 3. Language file `lang/<code>.json` (in git, our text only)
```
{"meta": {"code": "de", "name": "Deutsch", "version": 1},
 "strings": {"0004": {"h": "<first 8 hex digits of sha1 of the ENGLISH source>", "t": "Wally: Miss Kayla ist wunderschoen."}, ...},
 "names": {"item:01": {"h": "...", "t": "Zauber{BreakSpace}Schwert"}, ...},
 "ui": {"yesno_no_x": 168, "yesno_cursor_yes_x": 208, "yesno_cursor_no_x": 296}}
```
`ui` = layout values that depend on the word lengths of the language (defaults = the US values, so English needs none): the Yes / No prompt `YesNoPrompt $024724` prints 'Yes' at x `$50` and 'No' at x `$A0` and moves a cursor sprite between FIXED x positions `$D0` / `$120` (`g_VDPSpr02_X`); the German original build uses `$A8` for the second word and `$128` for the cursor (every position that is compared / set in `loc_247E8` / `loc_24804`). Our hook wraps or patches these constants from `ui`; the same mechanism takes later layout values (Use / Equip choice, menu column widths).
Control codes are written as in `stringdump.py` (`{Speaker}`, `{NewLine}`, `{Item}`, `{Number}`, `{ContinuePrompt}` ...) and must appear in the translation as in the English source (checked). `h` makes sure a translation is only used when the ROM's English text is the one it was written for (US and EU are identical, other versions simply fall back to English).

## 4. Build step
`tools/langbuild.py ROM lang/de.json out.bin` (runs in `build.sh` / `firstrun.py` on the player's machine): decodes the ROM's strings, drops translations whose hash does not match, converts the text to word streams / name entries and writes a compact binary (id -> offset) plus the extended font. The game loads it at start (`LANDSTALKER_LANG` / `~/.landstalker_lang`, Options > Language row). English = the original path, bit exact (hooks do nothing).

## 4b. Binary format (DONE, `tools/langbuild.py`)
`'LKLG' u16 version(1) u16 n_str u16 n_name u16 n_ui u16 n_glyph`, then `n_str x {u16 id, u32 blob offset, u16 words}`, `n_name x {u8 table, u8 index, u32 offset, u8 bytes}` (tables: 0 char, 1 special, 2 default, 3 item, 4 menu), `n_ui x {u16 key, u16 value}` (1 yesno_no_x, 2 yesno_cursor_yes_x, 3 yesno_cursor_no_x), `n_glyph x {u8 code, 30 bytes}`, then the blob (strings as u16 words incl. `$FFFF`, names as bytes). All big endian. Control codes become `~HANDLER[k] & $FFFF` (table `HANDLER` in langbuild = the game's `ControlChars` table). Entries whose English hash or control codes do not match are dropped with a message (US and EU give identical output). Extended glyphs: lower case umlauts = a / o / u + dots in row 2 (free rows above the x height), capitals lose one middle row and get the dots in row 0, sharp s drawn; preview with `--preview out.png` (checked by eye 2026-10-26, user has not judged them yet).

## 5. Steps
1. DONE: string / name decoder (`stringdump.py`).
2. DONE (offline part): `lang/de.json` (10 test strings + 3 names + ui, hashes of the English source only), `tools/langbuild.py`; still to do: load the binary in the game and look at it headless (`LANDSTALKER_LANG=de`, text box screenshots) = step 3.
3. DONE headless 2026-10-26 (`tools/patch_lang.py`, `LANDSTALKER_LANGBIN=<file>`, `LANDSTALKER_LANGLOG=1`): the design changed in two points: (a) the dialogue hook is a wrapper of `DecodeChar $0246B2` (returns the translated characters in the Huffman character domain: glyph < $55, control $56 + k, end $55) instead of the `FF1844` word stream: the game's own `GetNextChar` keeps handling name insertion ({Item}) and the end of the string, a word stream would have been lost after an inserted name (the game falls back to the Huffman source); extended glyphs ($6C..) cannot pass the control table, so `DecodeChar` returns the placeholder control code k = 0 (`$FFEA`) and a `GetNextChar` wrapper swaps in the glyph word; (b) names: wrapper of `SkipToStringIndex $0294B6` (A2 = table, D1 = index) returns the translated entry. Extra memory: 64 KB at `$800000` (`bus.c` `lk_lang_mem`, memory_map region $80), font copy at `$801000`, `MainFontPtr $022E84` is rewritten in the in-memory ROM image (`lk_lang_rom_patch32`). Verified with screenshots (EU build in `~/ProjectL_eu`, US and EU identical strings): file select 'Neues Spiel' (menu name), intro dialogue (Owner / Nigel, German text, inserted item name, umlauts Ä Ö Ü ä ö ü ß in the text box); with the env variable unset nothing is registered (English = original path). Not done: ui values (Yes / No positions), the Options row + saved setting, build integration (`build.sh` / `firstrun.py` run `langbuild.py`), widescreen text box width.
4. Options row Language, saved setting.
5. The translation itself (Claude writes, the user corrects while playing), per area.
6. Intro captions, credits, save location names; manual / readme; release notes.
Risks: strings that the game builds by code (numbers, names inserted), scripts that compare text lengths, the Yes/No prompt spacing (`YesNoPrompt` has a German special case in the DE build: x `$A8` instead of `$A0`), speech blips per character (fine), widescreen text box width.
