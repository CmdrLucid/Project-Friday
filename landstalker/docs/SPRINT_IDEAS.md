# Ideas: real sprinting for Nigel (THEORY ONLY, nothing built)

**Written 2026-10-29 night, Deck session, from a short discussion with the user. Based on `dev` commit `451750e`.**
The user's wording: "koenntest du ggf auch mit Magnific eine zusaetzliche Animation fuer Nigels Sprite machen? z.B. Sprint?", then, after the two options were explained: **"mittelfristig echtes Sprinten."** Not started; a later session decides when.
Nothing here is implemented or verified. Re-check against the code / docs of the day before acting.

## Goal (user)
- Real sprinting: hold a button and Nigel runs faster, with its own sprint animation in the original pixel style.
- Medium term (after the current work: timing model T3..T7).

## Constraints (project rules)
- Gameplay change = an Options switch (Gameplay page), Off by default; Off must keep the original bit exact (the timing bench `tools/timebench.py --compare` stays IDENTICAL with the option Off). Same rule as the remake (CLAUDE.md: logic changes switchable).
- Recordings made with Sprint On replay only with Sprint On (like Seamless Doors, LESSONS 'Seamless Doors time-free load'); the recording script must freeze the option (like WIDE / TALL in `rec_*.cfg`).
- The sprint frames are derived from Nigel's ROM graphics: generated on the player's machine by a script in the repo (like `langbuild.py` / the remake recipes), the images themselves are NEVER committed. Magnific (an AI upscaler) is not reachable from Claude's tools and does not draw frame-consistent pixel animation; the frames are made by script from the existing walk frames (lean, longer stride, maybe a dust puff), palette-indexed so fades / flashes still work (LESSONS 76: `.idx` images drawn through the live palette).

## Open questions for the first research session
1. Where the player speed comes from (player movement routine, speed per frame, sub-pixel handling) and whether doubling it breaks collision (blocks test collision only at tile boundary crossings, LESSONS 2 / HANDOFF section 6), stairs / slopes, jumps (jump length would grow), ladders, ice / conveyor floors, room exits and door triggers (the door delay timer `$FF12DF`, LESSONS 90).
2. Which button (pad layout is full: quick items Y / B, fast forward; key binding table `lk_keys_step`, LESSONS 46) and whether sprint should be hold or toggle.
3. Sprint frames: how Nigel's walk cycle is stored (sprite records / pose graphics, FORMATS 'Sprite upload'), how many directions are mirrored, and how the own renderer can show a replacement pose (HD / tile pack mechanism `patch_own.py`).
4. Limits: no sprint in cutscenes, dialogues, the intro rooms 139..143, on ladders (Action bit 12), maybe not while carrying an object.

## First steps when the user says go
1. Research (headless, a recording of Nigel walking): find the speed source, write it into FORMATS / symbols.
2. A mock-up of 2 - 3 sprint frames for ONE direction next to the original walk frames, shown to the user (one asset at a time, LESSONS 98).
3. Prototype the speed change behind the option, test collision / doors / jumps with recordings, bench IDENTICAL with the option Off.

## Status 2026-10-29 night: animation mock-up (dev `23414ba`)
- `remake/tools/sprint_mock.py [A..G]` (Pillow; on the Deck `~/.landstalker_trailer/venv/bin/python`) builds sprint frames from Nigel's FRONT walk frames (`~/.landstalker_remake/figures/nigel/a12_f*.png`, cut by `nigel_frames.py` from the user's ROM); output only in `~/.landstalker_remake/sprint/` (sheets, 1x frames, GIF; self-contained HTML pages with base64 images, because the desktop browser does not load images from the hidden folder).
- User verdicts: 4 frames (A..D) 'zu wenig'; 8 frames played at 2x the walk speed (E) 'wirkt am besten, braucht cleanup'; cleaned variant **G** (head as one block shifted 4 px, below it the lean drops by 1 px per band so outlines stay connected; stride widening only on the boots of frame 0; 1 px lift on frames 2 / 6; dust puff on frames 0 / 4; 3 game frames per picture) = **'behalten wir mal so'**, to be judged IN THE GAME later.
- Open: back view (`a8_f*`, walk back) with the same recipe; the 4 screen directions come from mirroring front / back; arms / legs keep the walk poses (real sprint poses would need hand-made pixel edits).
- (user, 2026-10-29 night) **A jump out of a sprint must look different too**: own 'running jump' frames (same recipe as the sprint: Nigel's jump frames leaned forward, legs stretched, maybe dust at take-off), and the gameplay side: does the jump get longer at sprint speed (jump arc from the horizontal speed?), which gaps / platforms that are meant to be impossible would become reachable (sequence breaks, story flags), landing on edges / slopes. Research together with open question 1; mock-up only after the sprint itself is seen in the game.
