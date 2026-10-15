# Instruction timing test (reference core vs recompiled) -- INDEX open item 6

`python3 mk.py [simple]` writes `t.bin`/`t.json`: a main loop with mulu/divu/shifts/movem/dbf/Bcc (taken and not
taken)/Scc/jsr/rts/memory ops that counts iterations at `$FF0000`; the VBlank handler counts frames at `$FF0004`.
`simple` leaves out mulu/divu/movem (short instructions only).

    ./run.sh GENRECOMP_DIR BUILD_DIR OUT_DIR [simple]     # needs libsdl2-dev and a built genrecomp (patch chain of build.sh applied)
    # e.g. ./run.sh ../../.deps/genrecomp /tmp/gb /tmp/out simple

`run.sh` generates the C code with the patched `generate.py`, links it with `h.c`, runs `genrecomp_ref` and the
recompiled binary for 600 frames and prints iterations per dump (`cmp.py`). The dump of the recompiled run is taken
right after the VBlank handler, so its frame counter is 1 ahead of the reference.

Results (patch_timing.py):
- old model (28 master clocks per data access only): recompiled loop runs +173 % too fast.
- new model, short instructions: iterations per frame equal within ~0.05 % (346.0 vs 346.15).
- new model with movem/mulu/divu: -0.75 %. Cause: Musashi only inserts the DRAM-refresh stall (2 cycles / 128) once per
  *instruction*, so a 130-cycle `movem` loses refreshes; patch_timing.py charges the refresh arithmetically (hardware-like).
`LANDSTALKER_OLDTIMING=1 ./rec ...` restores the old model.
