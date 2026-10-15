# DecompressLZ77Gfx self-test (no game ROM needed)

Hand-assembled copy of the routine at `$4AB2` (from landstalker_disasm
`gamelogic3.asm`), run through genrecomp's recompiler with the same seeds as the
real build, then called on a synthetic compressed stream. Checks the recompiled
`jmp loc_4AD8(pc,d1.w)` copy slots, `dbmi`/`dbpl` and the loop-back.

    cd tools/lz77test
    python3 mkrom.py                                   # test.bin, orig.bin, recomp.json
    python3 ../../.deps/genrecomp/tools/recompiler/generate.py test.bin -o out -c recomp.json
    cmake -S . -B b && cmake --build b --target t
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ./b/t --headless

Expected: `0 of 3003 bytes differ` / `PASS`. Result so far: PASS, so the
decompressor is not the cause of the missing title screens.
