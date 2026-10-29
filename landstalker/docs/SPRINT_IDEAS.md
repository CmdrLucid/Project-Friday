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
