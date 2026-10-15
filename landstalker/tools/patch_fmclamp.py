#!/usr/bin/env python3
"""Genesis Plus GX sound.c: never let fm_update() write past the FM sample buffer (idempotent).

Crash found with gdb (win17): main thread, VBlank handler -> sub_0013B6 -> bus_write16 -> gen_zbusreq_w -> z80_run -> z80_memory_r
-> YM2612_Read -> fm_update -> YM2612Update SEGV on a garbage pointer. fm_update() renders (cycles - fm_cycles_count) / ratio samples
into fm_buffer (only 1080 stereo samples = one frame). When the Z80/68K cycle counter passed to it is far ahead of the frame
(the recompiled build's clock differs from the real core's), it overruns the buffer and trashes the heap/other chip state.
Fix: clamp to the room left in the buffer (a short audio glitch instead of memory corruption) and log the first few clamps,
which also shows how far the clocks diverge.
usage: patch_fmclamp.py path/to/genrecomp
"""
import sys, os
p = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core/sound/sound.c")
s = open(p).read()
if "LANDSTALKER_FMCLAMP" in s:
    print("sound.c already patched: LANDSTALKER_FMCLAMP"); sys.exit(0)
old = "    int samples = (cycles - fm_cycles_count + fm_cycles_ratio - 1) / fm_cycles_ratio;\n"
new = old + '''
    /* LANDSTALKER_FMCLAMP: never write past fm_buffer */
    {
      int room = (int)((fm_buffer + (sizeof(fm_buffer) / sizeof(fm_buffer[0])) - fm_ptr) / 2);
      if (samples > room)
      {
        static int warned;
        if (warned++ < 8)
          fprintf(stderr, "fm_update: clamped %d samples to %d (cycles=%d count=%d ratio=%d)\\n", samples, room, cycles, fm_cycles_count, fm_cycles_ratio);
        if (room <= 0)
        {
          fm_cycles_count = cycles;
          return;
        }
        samples = room;
      }
    }
'''
assert old in s, "sound.c: fm_update layout changed"
open(p, "w").write(s.replace(old, new, 1)); print("sound.c patched: LANDSTALKER_FMCLAMP")
