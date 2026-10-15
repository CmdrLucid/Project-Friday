# Project-Friday

Static recompilation of **Landstalker** (Sega Mega Drive) to native code for PC and Steam Deck, built with
[genrecomp](https://github.com/sp00nznet/genrecomp). *Friday* is Nigel's fairy companion.
Bring your own ROM: no ROM, asset or generated code is part of this repository.
Non-commercial, open source, a hobby project. Not affiliated with Sega or Climax Entertainment.

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
and no code generated from the game.

## How AI is used in this project

This project is built with **Claude** (Claude Code, an AI assistant by Anthropic). To be fully transparent:

- **All code is written by Claude:** the recompilation patches, tools, launcher, packaging scripts, test aids and the documentation (including this README). Many commits carry a `Co-Authored-By: Claude` line.
- **The human project owner provides the ideas and does the testing:** what should be built, feature wishes, decisions (for example the release approach and the licence), and playing the game on a real Steam Deck to judge look, sound and feel. Claude can only run the game without a screen, so everything that has to be seen or heard is confirmed by the owner (the documentation says which checks are still open).
- **Limits:** Claude makes mistakes. Results are checked with automated comparisons (RAM dumps against the reference emulator core, replays) and by playing, but the code has not been audited by a human programmer. Please report bugs as issues.
- **Claude's output is not used as game content:** no AI-generated art or sound is in the game. An attempt to generate title lettering with an image AI was rejected and dropped.
