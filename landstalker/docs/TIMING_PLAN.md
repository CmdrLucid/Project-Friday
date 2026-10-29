# Timing model: getting independent of the emulator (plan, 2026-10-29)

User goal (2026-10-29, '2' = write the plan for the timing model): after the picture (own renderer, stage 2) and the sound (recompiled Z80 driver, own PSG + YM2612), the last place where Genesis Plus GX (GPGX) still drives the game is the TIME: frame / line clock, interrupts, VDP port timing, DMA stall, Z80 bus waits, system start.  This file says what that is today (measured), what is already ours, and the steps.  Same method as `SOUND_PLAN.md`: the GPGX path stays in the build as the reference, ours is switched, acceptance = bit identical results on all recordings.

## 1. Why it is risky (and why the method must be 'bit identical first')
- The game is deterministic only as long as every 68K cycle lands on the same line: one cycle more in a frame can move an interrupt by one instruction, an NPC takes another random direction, and a recording no longer replays (LESSONS 9.y, 9.14).  The 59 recordings in `~/aufnahmen` (57 with `.chk` checkpoints), `~/intro.txt` and `docs/replays/massan.txt` are the test bench of the whole project: they must stay valid.
- Quick saves (`LANDSTALKER_QSAVE`) are snapshots of the GPGX state (`m68k.cycles`, `mcycles_vdp`, `v_counter`, VDP / Z80 variables): our own state needs a place in them, old quick saves must still load.  The battery save (`.srm`) is game data and NOT affected.
- So: phase 1 copies today's behaviour EXACTLY (no improvement, no 'more accurate than GPGX'); improvements towards the real console are phase 2 and only with the user's OK, because they invalidate the recordings (new recordings needed).

## 2. What it is today (read 2026-10-29 in `.deps/genrecomp/src/bus.c` after all patches, GPGX `core/`)
Already OURS (genrecomp + our patches):
- the 68K cycle count: per basic block from GPGX's Musashi table (`patch_timing.py` / generator `bus_add_cycles`), data dependent MUL / DIV / shifts / MOVEM / Bcc, DRAM refresh (2 of every 128 cycles), `lk_no_charge` / `lk_free_mclk` for our extras;
- the line loop `bus_advance_inner` (a copy of GPGX's `system_frame_gen`): 3420 master clocks per line, VBlank at the viewport height, the Z80 run per line, frame end at `lines_per_frame`, the rebase of all counters, the per-line draw + H-Int counter (`GENRECOMP_PERLINE`), the interrupt delivery `bus_irq_rebased`;
- the DMA: run to completion at once (`bus_finish_dma`) with our own stall formula (blanking rate, LESSONS 2: GPGX's active display rate stalled 187 000 cycles);
- the sound clock while fast forwarding (`patch_sndclock.py`), the Z80 driver (recompiled, `sndnative.c`), both chips.

Still GPGX (every place that READS or MOVES the 68K clock, from `grep m68k.cycles core/`):
| # | Where | What it does with the time | Used by Landstalker? |
|---|-------|----------------------------|----------------------|
| G1 | state variables `mcycles_vdp`, `v_counter`, `lines_per_frame`, `status`, `h_counter`, `hint_pending`, `vint_pending`, `Z80.irq_state` | our line loop runs ON these globals | yes, all |
| G2 | `vdp_68k_ctrl_r` (status `$C00004`) | VBlank / HBlank / FIFO empty / DMA busy flags from `m68k.cycles` | yes (wait loops) |
| G3 | `vdp_hvc_r` (`$C00008`) | H / V counter from `m68k.cycles` (H40 table) | yes: `HandleHBlankInterrupt $001184` polls it (full height band, `patch_own.py lk_h_hint`); `tools/scan_hv.py` lists all readers |
| G4 | `vdp_68k_ctrl_w` -> `vdp_dma_update` | DMA start sets `dma_endCycles` and `m68k.cycles = dma_endCycles` (68K halted); our `bus_finish_dma` then re-writes the stall | yes, every DMA |
| G5 | `vdp_68k_data_w` FIFO | `fifo_cycles[]` slots, a full FIFO stalls the 68K | yes (direct data port writes) |
| G6 | `mem68k.c` Z80 area (`$A00000..$A0FFFF`) | `m68k.cycles += 7` per access, YM / PSG writes time-stamped with `m68k.cycles` | rarely (68K writes the mailbox + busreq) |
| G7 | `gen_zbusreq_w` / `gen_zreset_w` (`$A11100` / `$A11200`) | Z80 bus handshake, sets `Z80.cycles` from `m68k.cycles` | yes (every mailbox write) |
| G8 | `z80_request_68k_bus_access` (Z80 reads the banked ROM window) | adds wait cycles to the 68K | yes, through the native driver (SOUND_PLAN section 6) |
| G9 | `input_hw/gamepad.c` | TH line latency from `m68k.cycles` | yes, every pad read |
| G10 | frame end: `audio_update` (mixer, `blip_buf`), `input_end_frame` | mixes the frame's samples, latches pad timing | yes |
| G11 | system start: `load_rom`, `system_init`, `system_reset` (`gen_reset`: power-on clock `((262 - 192 + 159) * 3420) + 1004`, rounded to 7 / 15), the Z80 boot stub until the game's driver starts | the starting phase of everything | once |
| G12 | `m68k_poll_detect`, `m68k.cycle_end` lockups | sets `m68k.cycles = cycle_end` (0): our guard 'cycle counter went backwards' | NOT seen (0 warnings in the run below); Sega CD only |

## 3. Measured 2026-10-29 (`LANDSTALKER_CYCSTAT=1`, recording `rec_20261016_0039`, 4700 frames, WIDE 16 TALL 1, headless 14 s)
- 68K cycles per frame: main 115 600 .. 122 300, VBlank handler ~1 380, H-Int handler 930 .. 6 750 (full height band) = about 128 000 = one NTSC frame (896 040 master clocks / 7).
- Clock moved BEHIND our back by GPGX per frame: VDP 1 350 .. 2 500 cycles (1 - 2 %, nearly all after `$C00004` = DMA start / FIFO), Z80 / IO 0 .. 46, 'RAM/ROM' 48 .. 127 (attributed to the access before; to be explained in T1).  Biggest single jumps: 1 532 cycles (normal DMA), 16 553 (our corrected stall of the 187 611 cycle GPGX stall), 22 000 .. 72 000 at room loads (big DMAs).
- No watchdog, no 'went backwards', no `ncguard` line.  So the GPGX side that really matters for time is small: G2 .. G5 (VDP), G7 / G8 (Z80 bus), G9 (pad), plus the state globals G1.

## 4. Steps (each ends with the acceptance of section 5; nothing changes for the player until T7)
- **T0 golden trace** (`tools/patch_timetrace.py`, env `LANDSTALKER_TIMETRACE=file`): one line per time-relevant event: frame, line, cycle in line, kind (status read + value, HV read + value, DMA start + length + stall, FIFO stall, busreq / reset, Z80 wait added, interrupt taken + level + pc, frame end cycles).  Must be deterministic (two runs = same file).  Plus a script `tools/timebench.sh` that replays ALL recordings with their `.cfg` and save copies (isolated HOME, LESSONS 9.33 / 93) and writes per recording: `.chk` compare, RAM dump hashes every 100 frames, WAV hash, trace hash.  This bench is the acceptance tool of every later step.
- **T1 one door per access** (no behaviour change): every G2 .. G9 call goes through a function of ours in `bus.c` (`lk_t_status_r`, `lk_t_hvc_r`, `lk_t_dma_start`, `lk_t_fifo_w`, `lk_t_zbus_w`, `lk_t_zwait`, `lk_t_pad`) that still calls GPGX.  Count per recording which doors are used how often; explain the 'RAM/ROM' jumps of section 3.
- **T2 own clock state**: our struct (frame cycle, line, cycle in line, VBlank / HBlank flags, H-Int counter, pending interrupts, DMA end, FIFO slots) is the master; the GPGX globals of G1 are written FROM it once per line / access (GPGX code that still reads them keeps working).  Shadow compare against GPGX's values on the bench.
- **T3 VDP port timing ours**: status flags, HV counter (H40 / H32 counter tables are hardware facts, written down fresh from the documentation and checked against GPGX's results), DMA stall (one formula: today's `bus_finish_dma` without GPGX's first writing `m68k.cycles = dma_endCycles`), FIFO stall.  Shadow mode `LANDSTALKER_TIME_SHADOW=1`: ours and GPGX's computed side by side on every access, first mismatch printed with the call stack (as the sound shadow did).  The DMA DATA path (`vdp_dma_update` copying into VRAM) stays GPGX's for now (own renderer already mirrors it; a separate step).
- **T4 Z80 bus ours**: the 68K waits of G6 / G8, the busreq / reset handshake of G7 move into `sndnative.c` (the native driver already uses GPGX's functions with its own time, SOUND_PLAN section 8); the Z80 boot stub of the system start is replaced by starting the recompiled driver directly at the point where the game uploads it (`InitZ80Driver $0006FA`).
- **T5 pad and frame end**: TH latency (G9) and `input_end_frame` ours; the mixer (G10) is the separate 'own mixer' item (SOUND_PLAN section 9 NEXT): the frame end only calls a function of ours that, until then, still calls GPGX's `audio_update`.
- **T6 system start + quick saves**: power-on values (G11) from our init; the quick save gets a versioned block with our clock state; loading an OLD quick save fills our state from the GPGX fields it contains (test: quick saves made with v1.2.0 still load).
- **T7 switch**: `LANDSTALKER_TIMING=own` becomes the default after the bench is clean on all recordings + intro US / EU + quick save / load + fast forward + Seamless Doors + WIDE / TALL variants; `=gpgx` stays as the rollback for at least one release.  Only then the user plays ('fuehlt sich gleich an?').
- **Phase 2 (optional, user's call, invalidates recordings):** things where today's model (= GPGX + our DMA fix) is known or suspected to differ from the console: DMA in active display (charged at the blanking rate, an assumption), Musashi's refresh quirk (0.75 % in long MOVEM loops), interrupt latency.  Only with a reason the user sees (a game bug, a feel difference) and new recordings afterwards.

## 5. Acceptance (every step)
1. `tools/timebench.sh`: for every recording the `.chk` checkpoints equal, RAM dumps every 100 frames byte identical, audio capture (`LANDSTALKER_WAV`) sample identical, time trace identical to the GPGX path; also `~/intro.txt` (US + EU clone `~/ProjectL_eu`), a quick save / load run (`LANDSTALKER_QSREQ`), fast forward, `LANDSTALKER_SEAMLESS` on.
2. `LANDSTALKER_CYCSTAT=1`: per frame totals unchanged; after T3 the 'clock jumps behind our back' must read 0 (nothing outside our code moves the clock any more).
3. Run time not worse (bench: 4700 frames = 14 s today).
4. The AppImage first-run test (LESSONS 106) and the Windows cross build before a release.

## 6. Estimate and order of work
T0 + T1: one session (tooling, no risk).  T2 + T3: the core, one or two sessions, the shadow mode finds the details.  T4 + T5: one session (most of it exists in `sndnative.c`).  T6 + T7: one session incl. the release tests.  After T7 the remaining GPGX code in the game is: the VDP's register / DMA data path (mirrored by the own renderer, not timing) and the mixer.
