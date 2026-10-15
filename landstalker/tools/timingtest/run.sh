#!/bin/bash
# usage: run.sh GENRECOMP_DIR BUILD_DIR OUT_DIR [simple]   (needs libsdl2-dev; builds t.bin test, prints ref vs rec)
set -e
G=$1; B=$2; D=$3
cd "$(dirname "$0")"
python3 mk.py ${4:-}
rm -rf out && python3 $G/tools/recompiler/generate.py t.bin -o out -c t.json > /dev/null
gcc -O2 -DLSB_FIRST -DUSE_32BPP_RENDERING -I$G/include -Iout h.c out/*.c -o $D/rec $B/libgenrecomp.a $B/libgenplusgx_hw.a $(sdl2-config --libs) -lm
rm -rf $D/tref $D/trec; mkdir -p $D/tref $D/trec
$B/genrecomp_ref --headless --frames 600 --ram-dump $D/tref:120 t.bin > /dev/null 2>&1
$D/rec --headless --frames 600 --ram-dump $D/trec:120 t.bin > /dev/null 2>&1
python3 cmp.py $D/tref $D/trec
