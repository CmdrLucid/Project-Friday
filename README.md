# Project-Friday

Static recompilation of **Landstalker** (Sega Mega Drive) to native code for PC and Steam Deck, built with
[genrecomp](https://github.com/sp00nznet/genrecomp). *Friday* is Nigel's fairy companion.
Bring your own ROM: no ROM, game asset or code generated from the ROM is part of this repository (the game is built on your machine from your own ROM).
Non-commercial, open source, a hobby project. Not affiliated with Sega or Climax Entertainment.

## Video

[![Project-Friday on YouTube](https://img.youtube.com/vi/XXYhEBV57Co/hqdefault.jpg)](https://www.youtube.com/watch?v=XXYhEBV57Co)

## Download and start

Get the latest release from the [Releases page](https://github.com/cmdrlucid/Project-Friday/releases):

- **Steam Deck / Linux:** `Project-Friday-x86_64.AppImage`. Make it executable, start it and pick your ROM. The first start builds the game from your ROM (this takes a few minutes); later starts go straight into the game. On the Deck, add it in Desktop mode via *Steam > Add a Non-Steam Game*.
- **Windows 10 / 11 (experimental):** `Project-Friday-windows-x64.zip`. Extract the whole zip and start `Project-Friday.exe`.

You need a supported ROM (US or European version), described under [Compatible ROMs](#compatible-roms).

## How is this different from running the ROM in an emulator?

The game logic is no longer interpreted: the 68000 code of the ROM is translated into C and compiled into a native program on your machine. Video and sound chips are still emulated, using Genesis Plus GX. Because the game code is now ordinary C that we can hook into, the project can change things an emulator cannot: draw a wider picture with real map content, fix old bugs, or add comfort features inside the game's own menus.

With every option switched off, the game plays like the original cartridge. All additions are optional and set in a new **Options** tab in the game's Start menu (next to *Use* / *Equip*; also on the file select screen).

**Video**
- **Widescreen** Off / 16:10 / 16:9: real map content in the side margins, not stretched. The project draws the picture with its own renderer, and sprites, scrolling and effects are handled for the wider view.
- **Full Height:** shows the map in the band at the bottom of the screen that the original leaves empty while you walk.
- **Map Behind Text:** dialogue boxes sit over the map instead of a black band.
- **No Sprite Limit:** draws every figure of a room, without the cartridge's limit of 20 sprites per line and its flicker (off by default = the original look).
- **Filter** (Off, Scanlines, CRT, CRT Pro, CRT Curved), **Scaling** (Fit, 4:3, Integer, Fill), borderless **Fullscreen**.
- **Shadows** (Off / On / Soft): a ground shadow under Nigel and airborne objects, which makes jumps easier to judge.
- **HUD** Original / Modern: the modern HUD drops the status bar and lays hearts, the sword charge, gold and the button icons (sword, Quick Items, with the name of the bound button) over the map, so the room fills the whole screen.

**Audio:** separate music and effect volume; speech blips can be switched off.

**Quality of Life**
- **Quick Save / Quick Load** anywhere, on a button. This uses a hidden extra slot, so your four normal save files are not touched.
- **Quick Items:** put consumable items (e.g. EkeEke) on two buttons, shown in the HUD.
- **Quick Equip:** hold a button (R1) and press a direction to open the strip of swords, armour, boots or rings, then pick a piece with left / right, without opening the menu.
- **Sprint** (On by default): hold R2 (keyboard Left Shift) and Nigel runs faster on the ground (jumps stay exactly as in the original).
- **Smooth Scrolling** (On by default, Quality of Life): the sprint is 1.5 x and the room scrolls evenly (a light quarter line blend of the scenery while sprinting); Off = sprint 2 x, no blend.
- **Native Pace:** busy rooms no longer run in slow motion; the picture waits for the game instead of the game losing frames like on the console.
- **Better Menu:** B in Use / Equip goes back to the menu bar instead of closing the menu.
- **Item Info:** a short description of the item under the cursor.
- **Buy Quantity:** buy several of an item in one go in shops.
- **Fast Forward** 2x / 3x / 4x while a button is held, or as a toggle (Fast Forward Key: Hold / Toggle).
- **Language:** English or Deutsch (menus, items and system messages are translated so far; dialogue is still English).
- **Fix Ride Objects:** Nigel now rides along on an object that stands on a moving platform. In the original he slides off; this is a bug fix.
- **Live Gaia Effect:** the Gaia rocks stay in the world while the screen scrolls.

**Difficulty:** damage taken (25 % to 200 %) and enemy HP (50 % to 300 %).

**Keybindings:** every action can be remapped, for both controller and keyboard.

Defaults for a new install: 16:9, Full Height, CRT Pro filter, Native Pace, and most Quality of Life options on (HUD: Original). Change anything you like in Options.

## Vision and what comes next

The goal is the **definitive way to play Landstalker on PC and Steam Deck**: faithful to the original by default, with modern comfort for those who want it. Planned or being looked at (no promises, this is a hobby project):

- **More comfort features and fixes**, driven by player feedback. Suggestions are welcome in [Discussions](https://github.com/cmdrlucid/Project-Friday/discussions) / Issues.
- **German ROM as a base** (the European and US versions work already). It is a different program revision and needs its own recompilation; Japanese and hacks like *Remix* are further away.
- **Seamless room transitions** (prototype exists, paused) and **HD texture packs** for the 2D picture (tools exist, paused until there are textures).
- **A 3D remake** ([`remake/`](remake/README.md), early stage): the recompiled game stays the logic core, and a new front end draws the world as hand-made 3D models in a "toy diorama" style, with the sprites kept. Assets are made and approved one at a time.
- **Modding groundwork:** thousands of functions, variables and tables are named and documented ([`landstalker/docs/`](landstalker/docs/INDEX.md)). The long-term idea is a mod layer for text, items and scripts.
- **Windows** is built and tested automatically but is still experimental. Reports from real PCs help a lot.

## Compatible ROMs

Two ROMs are supported, both as a raw 2 MB dump (`.md`, `.bin` or `.gen`, 2,097,152 bytes) of *Landstalker: The Treasures of King Nole* for the Mega Drive / Genesis:

| Version | SHA-1 |
|---|---|
| **US** | `24345e29427b000b90df778965dd8834300a9dde` |
| **Europe** | `9fbadc86319936855831ecd096d82d716b304215` |

The European version is the US game with 50 Hz timing constants; the game still runs at the speed of the US version. European support is new and has had less play testing than the US version.

The launcher checks size and SHA-1 at every start and refuses any other file with a message. Not supported (yet): the German and Japanese versions, hacks such as *Landstalker Remix*, other dumps or patched / translated ROMs, `.smd` (interleaved) dumps and ROMs inside zip files (convert / unpack them first). The German version differs in a lot of code and would need its own recompilation; the Japanese version and *Remix* have shifted data.

- Project: [`landstalker/`](landstalker/README.md) (build instructions, tools, documentation)
- Entry point for the documentation: [`landstalker/docs/HANDOFF.md`](landstalker/docs/HANDOFF.md), then `LESSONS.md` and `INDEX.md`
- Workflow: work happens on `dev`; `main` is the last state verified on a Steam Deck
- Formerly called *ProjectL* (the repository and the project were renamed to Project-Friday; GitHub redirects the old address)

## Credits and what is used from whom

This project stands on the work of others. Thank you!

| Project / people | What we use it for |
|---|---|
| **Landstalker** (Climax Entertainment / Sega, 1992) | The game itself. We own none of it; you need your own legal ROM. |
| [**genrecomp**](https://github.com/sp00nznet/genrecomp) by sp00nznet (MIT) | The recompiler: turns the 68000 code of the ROM into C on your machine, plus the runtime around it. `build.sh` downloads it and applies our patches (`landstalker/tools/patch_*.py`); the patched copy is not part of this repo. |
| [**Genesis Plus GX**](https://github.com/ekeeke/Genesis-Plus-GX) by Eke-Eke, Charles MacDonald and others (own non-commercial licence; contains the 68000 core Musashi by Karl Stenerud, also free for non-commercial use only, and code of the MAME team) | Emulation of the Mega Drive chips (video, sound, I/O) inside genrecomp. We patch it (widescreen, filters, sound mixing, timing). **Because of its licence, builds of this project must stay non-commercial.** |
| [**lordmir/landstalker_disasm**](https://github.com/lordmir/landstalker_disasm) | Human-made disassembly: its labels give code / data boundaries and thousands of names (`landstalker/docs/symbols.json`, tier `auto-seq`). Used locally, not copied into the repo. |
| [**lordmir/landstalker_editor**](https://github.com/lordmir/landstalker_editor) | Documentation of data formats (maps, entities, text) as a reference when checking the loaded data. |
| [**Dinopony/landstalker-lib**](https://github.com/Dinopony/landstalker-lib) | Room names, entity types, items, story flags and ROM table offsets (`docs/ROOMS.md`, `ENTITIES.md`, `ITEMS.md`, `FLAGS.md`, imported by `tools/import_rooms.py`, `tools/import_lib_constants.py`). |
| [**SDL2**](https://www.libsdl.org/) (zlib licence) | Window, graphics output, audio and controller input. |
| [**Zig**](https://ziglang.org/) (MIT) | The C compiler that builds the game on your machine from your ROM (bundled in the release packages; `zig cc`, also cross-builds the Windows package). |
| [**Python**](https://www.python.org/) (PSF licence) | Runs the launcher and the patch tools; the Windows package bundles the embeddable distribution. |
| [**Capstone**](https://www.capstone-engine.org/) (BSD 3-clause) | 68000 disassembly in our analysis tools (`tools/disasm.py` and others). |

Details and licence notes: [`landstalker/README.md`](landstalker/README.md). If you think someone is missing here, please open an issue.

## License

The files of this repository (patches, tools, launcher, documentation) are under the [MIT License](LICENSE).
**A built game is non-commercial only:** it contains Genesis Plus GX and Musashi, which are free for non-commercial use only
(see the table above). Landstalker itself belongs to Sega / Climax Entertainment; this repository contains no ROM, no game data
and no code generated from the ROM. The game code is generated locally on your machine from your own ROM when you build and is never committed.

## How AI is used in this project

This project is built with **Claude** (Claude Code, an AI assistant by Anthropic). To be fully transparent:

- **All code is written by Claude:** the recompilation patches, tools, launcher, packaging scripts, test aids and the documentation (including this README). Many commits carry a `Co-Authored-By: Claude` line.
- **CmdrLucid provides the ideas and does the testing:** what should be built, feature wishes, decisions (for example the release approach and the licence), and playing the game on a real Steam Deck to judge look, sound and feel. Claude can only run the game without a screen, so everything that has to be seen or heard is confirmed by CmdrLucid (the documentation says which checks are still open).
- **Limits:** Claude makes mistakes. Results are checked with automated comparisons (RAM dumps against the reference emulator core, replays) and by playing, but the code has not been audited by a human programmer. Please report bugs as issues.
