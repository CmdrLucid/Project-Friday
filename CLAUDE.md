# Project-Friday (formerly ProjectL; the local folder on the Deck is still ~/ProjectL, GitHub: cmdrlucid/Project-Friday)

`landstalker/` = static recompilation of Landstalker (Mega Drive) for PC/Steam Deck via genrecomp.
**Before doing anything there read `landstalker/docs/HANDOFF.md` (state + next steps + how the user works), then `landstalker/docs/LESSONS.md`, then `landstalker/docs/INDEX.md`** (status, Deck paths, rules, bug catalog,
tool cheat sheet, debug playbook). Details: `landstalker/docs/DEBUGGING.md`.

Hard rules: never commit ROMs, generated C or ROM-derived binaries; user has only a Steam Deck (commands are pasted
into Konsole, always print progress); **branch workflow: all work goes to `dev`; `main` = last state verified on the Deck, merged from `dev` only when the user asks (PR dev -> main)**; (if a session instruction names another branch, merge/rebase it into `dev` at the end); no PR unless asked;
update the Status block in INDEX.md and the bug catalog whenever something is learned.

The interpreter fallback (`tools/patch_interp.py`) is TEMPORARY: it logs every address it runs so we can seed them natively;
the goal is an empty log, then opt-in only (INDEX.md section 1 item 8 + "Interpreter fallback policy").

Symbols: record every learned address with a human name in `landstalker/docs/symbols.json` (see INDEX.md 'Symbol rule'); never document with bare addresses only (future modding goal).
**Look names up with `python3 landstalker/tools/sym.py <addr|text>` (one line per hit; `--near N`, `-v`); never read `symbols.json` whole (5000+ entries, sorted by address, one entry per line). Overview by area: `landstalker/docs/CODE_MAP.md`. Tools that write symbols.json use `tools/symfile.py` (`python3 tools/symfile.py` repairs the format; `check_docs.py` enforces it).**

Ids (room numbers, entity types, items, story flags) and ROM table addresses: look them up in `landstalker/docs/ROOMS.md`, `ENTITIES.md`, `ITEMS.md`, `FLAGS.md` (from Dinopony/landstalker-lib, see INDEX.md section 6) before guessing; add new sightings there via the import tools.

Before the last push of a session run `python3 landstalker/tools/check_docs.py -v` (0 errors) and follow the end-of-session checklist in `landstalker/docs/HANDOFF.md` (section 3b). Enable the hook in a fresh clone: `git config core.hooksPath .githooks`.
