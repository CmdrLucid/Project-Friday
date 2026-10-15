#!/bin/bash
# usage: run.sh GENRECOMP_DIR BUILD_DIR OUT_DIR [trials]
set -e
G=$1; B=$2; D=$3; T=${4:-3000}
cd "$(dirname "$0")"
python3 mk.py "${LANDSTALKER_ROM:-/home/deck/Documents/NonSteamGames/landstalker/landstalker.md}"
rm -rf out && python3 $G/tools/recompiler/generate.py rom.bin -o out -c rom.json > $D/fd_gen.log 2>&1 || { tail -5 $D/fd_gen.log; exit 1; }
INC=$(find $G/ext/Genesis-Plus-GX/core -type d | sed 's/^/-I/')
gcc -O1 -w -DLSB_FIRST -DUSE_32BPP_RENDERING -DHAVE_NO_SPRITE_LIMIT -I$G/include -I$G/src -Iout $INC ../funcdiff.c out/*.c -o $D/funcdiff $B/libgenrecomp.a $B/libgenplusgx_hw.a $(sdl2-config --libs) -lm
ENT=FF5700
# put an entity record into the RAM image: the collision routines only read +12,+14..+1E and +22 of the entity (funcdiff randomises them)
$D/funcdiff --headless rom.bin ram.bin $ENT 380 386 38C 392 --trials $T --seed 3 2>&1 | grep -v "^bus:\|^timing:\|^genrecomp:\|^\[depth\]"
