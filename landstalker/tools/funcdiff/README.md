# funcdiff

Runs ROM functions on GPGX Musashi and as recompiled C on the same RAM image and compares registers, flags and all of work RAM.

    ./build.sh ROM                 # normal build first
    bash tools/funcdiff/build.sh   # links build/funcdiff from the existing objects
    build/funcdiff --headless ROM RAMDUMP ENTITY ADDR... [--trials N] [--seed S] [--mode collision|plain]

`selftest/run.sh GENRECOMP_DIR BUILD_DIR OUT_DIR` rebuilds the Landstalker collision routines (150 bytes read from YOUR ROM at run time, `LANDSTALKER_ROM`; no game code is stored in the repository since 2026-10-15) and checks the harness and the translation in the cloud sandbox (no ROM).
