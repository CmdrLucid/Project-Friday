#!/bin/bash
# usage: tools/z80test/run.sh ROM [cases] [seed]   -- builds the generated Z80 driver from the ROM + GPGX's z80.c and fuzzes every instruction (needs .deps/genrecomp, see build.sh)
set -e
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd); G=$ROOT/.deps/genrecomp/ext/Genesis-Plus-GX/core; OUT=${Z80TEST_OUT:-/tmp/z80test}; mkdir -p "$OUT"
INC=""; for d in $(find "$G" -type d); do INC="$INC -I$d"; done
python3 "$ROOT/tools/z80recomp.py" "$1" "$OUT/z80drv.c"
gcc -O1 -w -DLSB_FIRST -DUSE_32BPP_RENDERING $INC -I"$ROOT/tools" -I"$ROOT/.deps/genrecomp/src" -I"$ROOT/.deps/genrecomp/include" "$HERE/fuzz.c" "$OUT/z80drv.c" "$G/z80/z80.c" -o "$OUT/fuzz"
"$OUT/fuzz" "$1" "${2:-64}" "${3:-1}"
