# MUSIC_ORCHESTRA - orchestral remix of the soundtrack (experiment, learnings)

Started 2026-11-28 (user: 'Koenntest du den Soundtrack als Orchesterversion remixen?'), rests on dev `be27f86`.
State: EXPERIMENT on one piece (Massan, room 592), five versions; the user is not happy with the sound yet (v1 'zu hallig, zu durcheinander',
v2 'Violine penetrant, Hintergrund unruhig', v3 'teilweise schief', v4 'Piepen alle paar Sekunden'); v5 not judged yet. Nothing of the
music is in git (only our tools and this file).

## 1. Pipeline (no MCP needed, all code)
1. **Capture**: the game's own sound trace `LANDSTALKER_SNDTRACE=file` (`tools/patch_sndtrace.py`, in every build) writes every YM2612 /
   PSG write (`Y frame who cycles port value`, `P frame who cycles value`; cycles = position inside the frame, 896040 master cycles per
   frame). Headless run: replay prefix of `rec_20261103_1803` to frame 2040, `LANDSTALKER_WARP=592:20.08,30.08,0010` at 2100, `--frames 6000`,
   plus `LANDSTALKER_WAV` for the original sound (same env as `tools/proxysurvey.py run()`). The music starts at frame 2100 (35.05 s in the WAV).
2. **Notes**: `tools/music/trace2notes.py TRACE OUT.json 2100` -> notes per channel (fm0..fm5, psg0..psg3) with pitch, start, end,
   loudness (carrier TL / PSG attenuation) and the FM patch id. No need to decode the driver's music format.
3. **Arrangement**: `tools/music/arrange.py NOTES.json OUT.mid PRESET` (presets v1..v5 = the versions below): per source channel a GM
   instrument, octave, velocity range, length mode (legato / ring / short / hold / sustain).
4. **Render**: `tools/music/render.c` = a 40 line MIDI -> WAV player on TinySoundFont (`tsf.h` + `tml.h`, MIT, schellingb/TinySoundFont,
   downloaded next to it: `gcc -O2 -o render render.c -lm`) with the SoundFont GeneralUser GS v2.0.3 (32 MB, free also in software
   projects, mrbumpy409/GeneralUser-GS). The pip packages tinysoundfont / pyfluidsynth do not build here (no wheel for Python 3.13,
   CMake error; no system fluidsynth on SteamOS).
5. **Hall**: `tools/music/mix.py DRY.wav OUT.wav DECAY WET DRY` (noise tail + early reflections, convolution). v1 2.2 s / wet 0.55 was
   'zu hallig'; since v2 1.1 s / 0.22.
6. **Check**: `tools/music/check.py NOTES.json ORIG.wav` renders all chip notes as piano and compares the pitch-class content (chroma)
   with the original per 0.05 s (best lag first). A fix must raise it (fm3 fix: 'good' frames 42 % -> 49 %, 'bad' 10 % -> 7 %; the FM
   overtones keep it below 100 % anyway).
Scratch (local, never in git): `~/Project-Friday-Test/lktest/orch` (capture, MIDI, WAV), listening copies `~/Project-Friday-Test/Musik/*.ogg`.

## 2. Learnings (do not re-learn)
- **Key on BEFORE the pitch**: some channels (Massan fm3) write key on ($28) and set the frequency ($A4/$A0) ~0.25 ms later. Reading the
  pitch at the key on gave the PREVIOUS note's pitch for 223 of 258 notes (the accompaniment one note behind = 'schief'). Now: a pitch set
  within 4 ms after the key on is the note's pitch; a later change of more than 0.5 semitone without a new key on starts a new note.
- **Echo channels**: the driver doubles voices 0.12 s later and softer: Massan fm4 = echo of fm0 (129 of 132 notes), psg1 = echo of psg0
  (94 %). Find them automatically (pairwise: same pitch class at a lag of 0.02..0.3 s). An orchestra drops them (the hall does that job);
  kept, they doubled the 'Piepen'.
- **Channels change ROLE inside a piece**: Massan psg0 plays low chord pulses most of the time but a high trill descant (G6 / A6, up to C7)
  at 23..26 s. Held as string pads that was a shrill beep (v4). Split by pitch (v5: below MIDI 76 = held strings, above = short soft piccolo).
- **Do not guess chords**: triads from the accompaniment failed: Massan has a chromatic bass line under held chords (C B A G# G under F)
  and chromatic inner voices (D C# C B) -> 'A major', 'Db major' that are not in the piece. Use the REAL accompaniment tones (held) instead.
- The PSG plays its notes as short pulses with a software volume envelope (attenuation changes every frame): one note = same pitch while
  attenuation < 15 (else ~3 times too many notes).
- Pitch comes out ~0.2 semitone sharp (YM clock 7670453 Hz, the game's tuning); rounding is right.
- GM instrument choices with GeneralUser GS: the string section (48 / 49) has a slow attack and smears fast melodies; the solo violin (40)
  was 'penetrant'; flute (73) / clarinet (71) / contrabass (43) / slow strings (49) are calmer. Busy harp arpeggios + pizzicato pulses =
  'unruhig'. Fewer voices (5 instead of 9) were clearer.
- Massan roles: fm0 melody, fm4 its echo, fm1 bass (chromatic lines), fm2 counter melody from 7.8 s, fm3 arpeggios (pitch after key on),
  psg0 pulses + high trills, psg1 its echo; ~125 BPM; no DAC drums in this piece.

## 3. Versions (presets in arrange.py)
v1 9 parts (strings + flute octave melody, oboe, harp, contrabass + pizz cellos, pizz pulses x2, horn pad), long hall. v2 5 parts (solo
violin melody, oboe, harp, contrabass, one pizz pulse), short hall. v3 flute melody, clarinet, contrabass, GUESSED string chords (wrong,
see 2). v4 real accompaniment tones held (psg0 + psg1 as strings: trills became beeps, echo doubled). v5 = v4 without psg1, psg0 split
(strings low, piccolo high). All with the fm3 fix from v3/v4 on.

## 4. Sound library / licence / release
- Better samples: **VSCO 2 Community Edition** (Versilian Studios, CC0, ~2.2 GB, SFZ, github sgossner/VSCO-2-CE) played by **sfizz**
  (BSD-2, `sfizz_render` renders MIDI with SFZ; build from source). Not tried yet (user asked first about the release size).
- Release rule (same as the game): the FINISHED pieces and even the note files are derived from the copyrighted composition -> never in
  git / the AppImage. Allowed: our tools + our 'translation' data (per piece / channel: instrument, octave, loudness, mode; a few KB).
  The player's machine captures from HIS ROM, arranges and renders (like firstrun builds the game), output in the Project-Friday folder.
- Samples: bundling VSCO 2 would grow the AppImage from ~100 MB to > 2 GB -> recommended: download on demand when the option
  'Orchester-Soundtrack' is switched on (or a trimmed, recompressed CC0 subset); after rendering the samples can be deleted (the
  finished soundtrack ~50..100 MB). Original music stays the default (remake rule: off = original).

## 5. Next steps (user decides)
1. User listens to v5 (notes and roles should be right now; remaining complaints are probably the sound of GeneralUser GS).
2. If the sound is the problem: VSCO 2 CE + sfizz test on Massan.
3. Then: capture of all pieces (sound test / driver command mailbox $1FFF instead of walking), per piece role detection (echo / role
   switch / pitch-after-key-on rules above), the translation data per piece, an option row + firstrun / on-demand render.
