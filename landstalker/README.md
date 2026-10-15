# Landstalker via genrecomp (scaffold)

Statically recompiles the Mega Drive 68000 code of Landstalker to native C with
[genrecomp](https://github.com/sp00nznet/genrecomp). Bring your own ROM; no ROM,
asset or generated code belongs in this repo (`.gitignore` enforces it).

    ./build.sh path/to/landstalker.md
    build/landstalker path/to/landstalker.md

## Steam Deck AppImage

Build on any x86-64 Linux machine (Ubuntu 22.04 is a safe choice for glibc
compatibility; SteamOS has no compiler by default), then copy the file over:

    packaging/build_appimage.sh path/to/landstalker.md   # -> Landstalker-x86_64.AppImage

On the Deck: copy the AppImage and your ROM into the same folder (named
`landstalker*.md/.bin/.gen`), `chmod +x`, and add the AppImage in Desktop mode
via Steam > Add a Non-Steam Game. If no ROM is found it asks with a file
picker. The ROM is not bundled, and the AppImage contains ROM-derived code, so
keep it to yourself.

## Status

Start with [docs/INDEX.md](docs/INDEX.md) (status, rules, bug catalog, tools, playbook);
evidence log in [docs/DEBUGGING.md](docs/DEBUGGING.md).

## Using the other projects

- [lordmir/landstalker_disasm](https://github.com/lordmir/landstalker_disasm):
  its labels give exact code/data boundaries and jump-table locations. Building
  it yields a `.sym` listing for your region; use that to fill `seeds`,
  `offset_tables` and `code_ranges` instead of guessing. (Assembling needs
  `wine`; the disassembly repo itself contains the packed game data, so only
  build from it if you are entitled to the game.)
- [lordmir/landstalker_editor](https://github.com/lordmir/landstalker_editor):
  documents the data formats (maps, entities, text); useful when checking that
  rooms and tables loaded correctly.

- [Dinopony/landstalker-lib](https://github.com/Dinopony/landstalker-lib):
  source of the room names ([docs/ROOMS.md](docs/ROOMS.md)), entity types,
  items, story flags ([docs/ENTITIES.md](docs/ENTITIES.md), ITEMS.md, FLAGS.md)
  and the ROM table offsets (imported by `tools/import_rooms.py` and
  `tools/import_lib_constants.py`).

## Licensing

Our own files are under the MIT License (see ../LICENSE). Binaries built with genrecomp are non-commercial (Genesis Plus GX, Musashi). Do not
redistribute ROMs or ROM-derived output.
