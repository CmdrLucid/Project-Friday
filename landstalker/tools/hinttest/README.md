# HInt + HV-counter wait test

`python3 mk.py` writes ref.bin / rec.bin / r.json: a main loop that floods the VDP data port with
HInt every line; the handler waits for the V counter ($C00008) to change (like Landstalker's
HandleHBlankInterrupt) and counts at $FF0000. `h.c` is a minimal host (build like tools/rmwtest/h.c;
seed names must not be `main`). Result with the patched runtime: ref 8998 HInts, rec 8774 (no hang,
no false WATCHDOG). The simple flood did NOT reproduce the freeze seen in the game, so the HInt
rebasing in patch_watchdog.py is precautionary. Replacing the handler with `move.w $FF0010,d0 / bra.s *`
shows the WATCHDOG line and its call stack.
