# Interpreter fallback test

`python3 mk.py` writes ref.bin/rec.bin/r.json (use tools/rmwtest/h.c as host, build like there). Routines at $600/$640 are
unreachable for the generator (addresses computed at run time), so the recompiled build has no function for them.
With patch_interp.py the runtime runs them on GPGX's 68K interpreter and RAM equals the real core
(including a routine that pops its own return address); `LANDSTALKER_NOINTERP=1` gives `no function at` and wrong RAM.
