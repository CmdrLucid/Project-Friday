# Trailer tools (2026-10-25)

Builds the English 90s-style commercial for Project-Friday from the user's own recordings. Only the recipe is in git:
footage, music, frames and the video stay in `~/.landstalker_trailer/` (ROM-derived, never commit).

1. `cc -O2 -o ~/.landstalker_trailer/crtpipe crtpipe.c -lm`: applies the game's own display filters (`tools/display_core.c`: sharp, Scanlines, CRT, CRT Pro, CRT Curved) to raw frames.
2. `~/.landstalker_trailer/venv/bin/python capture.py sheet <source> [step]`: contact sheet of a recording (find frame ranges).
   `capture.py all` / `capture.py clip <name>`: frames of every clip in `clips.py` (headless replay of `~/aufnahmen` / `docs/replays` recordings with their save copies,
   isolated HOME so the user's settings never change; `LANDSTALKER_SHOT` frames, Quick Equip via `LANDSTALKER_WINSHOT` + `LANDSTALKER_EQHOLD` / `_EQDIR`).
3. `render.py [--preview] [--from S --to S]`: composes the trailer at 1920x1080 / 60 fps on the bars of the music (`~/.landstalker_trailer/music/song.mp3`,
   bar 1.4275 s from 1.23 s, measured), writes `~/.landstalker_trailer/trailer.mp4`.

Venv: `python3 -m venv ~/.landstalker_trailer/venv && ~/.landstalker_trailer/venv/bin/pip install pillow numpy`.
Pitfalls: `LANDSTALKER_WINSHOT` only reads ~200 characters of its frame list (capture.py runs several identical replays); old recordings desync on the
current build (footage only, check the contact sheets); the opening uses WIDE 0 / TALL 0, the reveal composes the same frames captured twice (0/0 and 39/1).
