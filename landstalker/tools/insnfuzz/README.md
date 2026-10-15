# Differential instruction fuzz (Musashi vs recompiled C)

`./run.sh GENRECOMP_DIR BUILD_DIR OUT_DIR [count] [trials] [seed]` -- random single instructions run on GPGX's 68K interpreter and on the recompiled C with identical random registers,
flags and RAM; any difference is a translation bug (or an undefined-flag case). Memory regions 0x10-0xDF are one shared dummy buffer, ROM writes are ignored, interpreter
exceptions (odd addresses, zero divide) are skipped. Needs no ROM. See mk.py for the instruction filter.
