# Sound: getting independent of the emulator (plan, 2026-10-28)

User goal (2026-10-28): 'sound' = after the picture (stage 2, done), also the sound should not depend on the GPGX emulator.  Facts measured today, then the options.

## 1. What the sound side is today
- 68K -> Z80 interface is tiny: command byte at Z80 RAM `$1FFF`, arguments `$1FFC` / `$1FFD`, bank register, bus request (FORMATS 'Sound driver').  In the two recordings `20261012_2106` (6000 frames) and `20261016_0039` (4730 frames) the 68K wrote 174 / 64 mailbox bytes (170 / 59 commands, 15 / 14 distinct ids).
- The Z80 runs the game's sound driver (disassembly `~/landstalker_disasm/code/audio/sounddrv.asm`, music / sfx data in the ROM, streams read through the banked window `$8000`) and writes the chips: YM2612 (FM + one DAC channel) and the SN76489 (PSG).
- GPGX emulates: Z80 CPU, Z80 bus / banking, YM2612, PSG, the mixer; the 68K side is already native.

## 2. Golden trace (built today: `tools/patch_sndtrace.py`, `tools/sndtrace.py`, env `LANDSTALKER_SNDTRACE=file`)
One text line per YM2612 write (`Y frame who cycles port value`), PSG write (`P`), 68K mailbox write (`M`), count of driver upload writes (`U`).  Measured:
- the trace is DETERMINISTIC: two runs of the same recording give byte identical files (1.28 M lines in 6000 frames of the intro recording).
- 90 % (intro) / 74 % (Mercator walk) of all YM2612 data writes are the DAC register `$2A` = the drum samples streamed one byte at a time by the Z80; the rest is about 4000 writes per FM register over the run (note changes, key on / off, instrument loads), plus 26 381 PSG writes in the intro (speech blips, noise effects).
- all YM writes come from the Z80 (the 68K never touches the chips directly).

## 3. Options
A. **Native port of the Z80 driver (recommended).**  Port `sounddrv.asm` (the driver is a few hundred lines of Z80 code plus data tables) to C: a function `snd_command(id, arg)` called by the 68K side's mailbox write and `snd_tick()` once per driver tick (the driver runs on the Z80's VBlank / timer interrupt), writing the YM2612 and PSG through a small chip interface.  Keep the chip models (YM2612 core, SN76489 core) as libraries: they are the hardware, not the system emulator.  Verification by differential test: run the Z80 emulation and the port side by side on the same commands and compare the register write sequence with the golden trace (same method that found the 68K translation bugs).  What it gives: no Z80 CPU emulation, the sound clock is ours (music at normal speed during fast forward = GitHub issue #11 part 2, no catch-up speed at alt+tab, easy music replacement for modding).  Cost: the DAC sample streaming (90 % of the writes) has to be modelled as PCM mixed directly instead of byte writes with Z80 timing; the exact cycle timing of every write is not needed for FM / PSG notes, but the DAC pitch must be exact.
B. **High level music engine** (own sequencer, own synthesis or sampled instruments): freedom for HD sound, but no longer the cartridge's sound; needs the music format fully understood and a lot of listening checks.
C. **Keep GPGX for sound** and only decouple its clock (run it on its own thread at normal speed): smallest step, solves issue #11 part 2 but not the emulator question.

## 4. Proposed steps for A
1. (done) golden trace + summary tool.
2. Read the driver: channel blocks (FORMATS), command ids -> music / sfx, tick structure; write the command table (id, kind, channels) into `docs/symbols.json` names + FORMATS.
3. Port the YM / PSG part of one tick (instrument load, note on / off, frequency, volume, envelope macros) for the music channels; compare against the trace for the title music (first command in the intro).
4. Sound effects and the type-1 / type-2 channel stealing rules; speech blip.
5. DAC samples as a PCM mixer.
6. Switch: `LANDSTALKER_SND=native` next to the GPGX path, A/B on all recordings (trace + WAV compare), then default.
