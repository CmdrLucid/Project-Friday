# RMW addressing-mode test (reference core vs recompiled)

Builds two ROMs from the same ~25 instructions (`or/and/add/sub/eor/addq/subq/neg/not/lsl/bset/st/ori/andi/addi`
with `(An)+` / `-(An)` destinations, plus A7 byte cases). `ref.bin` ends in
`bra.s *` for `genrecomp_ref`; `rec.bin` ends in `rts` and goes through
`generate.py`. Compare work RAM at `$FF3000-$FF3FFF` and `$FFF000-$FFF0FF`.

    python3 mk.py        # ref.bin, rec.bin, r.json (prints the disassembly)
    # recompiled: generate.py rec.bin -o out -c r.json ; build h.c with out/*.c
    # reference : genrecomp_ref --headless --frames 3 --ram-dump DIR:1 ref.bin

Keep accesses aligned: a real 68000 raises an address error on odd word/long
accesses, which the recompiled code does not.
