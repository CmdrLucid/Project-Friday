# movem / pc-relative-index / adda.w test (reference core vs recompiled)

Same method as `tools/rmwtest`: `python3 mk.py` writes `ref.bin`/`rec.bin`/`r.json`; generate
`rec.bin`, build `../rmwtest/h.c` against it and compare work RAM `$FF3000..` with
`genrecomp_ref`. Result: `movem.w` sign extension, `movem.l`, `move.b d(pc,dN.w)`, `adda.w`
with a negative word all match the real core (these are used by the fall code at `$3270`).
