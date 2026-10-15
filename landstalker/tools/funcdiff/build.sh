#!/bin/bash
# build.sh -- builds build/funcdiff from the object files of a finished ./build.sh (no recompilation of the generated code).
cd "$(dirname "$0")/../.." || exit 1
G=.deps/genrecomp
# only objects whose generated source still exists (old builds leave stale .o files with other function ranges -> "multiple definition")
OBJS=""
for o in build/CMakeFiles/landstalker.dir/src/recomp/*.o; do
    [ -f "src/recomp/$(basename "${o%.o}")" ] && OBJS="$OBJS $o"
done
[ -n "$OBJS" ] || { echo "no objects in build/CMakeFiles/landstalker.dir/src/recomp -- run ./build.sh first"; exit 1; }
INC=$(find $G/ext/Genesis-Plus-GX/core -type d | sed 's/^/-I/')
SDL=$( (sdl2-config --libs 2>/dev/null) || (pkg-config --libs sdl2 2>/dev/null) || echo "-lSDL2")
gcc -O1 -w -DLSB_FIRST -DUSE_32BPP_RENDERING -DHAVE_NO_SPRITE_LIMIT -I$G/include -I$G/src -Isrc/recomp $INC tools/funcdiff/funcdiff.c $OBJS \
    -o build/funcdiff build/genrecomp_build/libgenrecomp.a build/genrecomp_build/libgenplusgx_hw.a $SDL -lm && echo "built build/funcdiff"
