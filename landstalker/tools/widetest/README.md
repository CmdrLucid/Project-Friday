# widetest

Checks the widescreen renderer patch (`tools/patch_wide.py`) without a game ROM. It builds a VDP scene through the real control/data ports (two scroll planes,
window plane, per-cell hscroll, sprites), renders it normally and with `e` extra pixels per side, and verifies

1. the centre of the wide picture equals the normal picture pixel for pixel (planes, window, sprites),
2. the new side areas are filled (the planes show their neighbouring columns),
3. a sprite that is half off-screen in the normal picture is visible in the wide one.

The comparison with an independent model of the scene is only informational: GPGX emulates real hardware quirks (the window-edge bug), so a few pixels at the window edge differ from the ideal model in both pictures.

Build (after applying the patch chain of build.sh to .deps/genrecomp and building the libraries with cmake into /tmp/gb):

    G=.deps/genrecomp; INC=$(find $G/ext/Genesis-Plus-GX/core -type d | sed 's/^/-I/')
    gcc -O1 -w -DLSB_FIRST -DUSE_32BPP_RENDERING -DHAVE_NO_SPRITE_LIMIT -I$G/include -I$G/src $INC tools/widetest/main.c \
        -Wl,--start-group /tmp/gb/libgenrecomp.a /tmp/gb/libgenplusgx_hw.a -Wl,--end-group $(sdl2-config --libs) -lm -o /tmp/widetest
    /tmp/widetest tiny.md 32          # tiny.md: any 128 KB file with a Mega Drive header (see DEBUGGING.md), e = 16, 32 or 48

`WIDETEST_DUMP=1` writes /tmp/wt_normal.ppm and /tmp/wt_wide.ppm. Valid `e` are multiples of 16 (the window plane is drawn in whole 16-pixel cells).

Note: the test assumes LANDSTALKER_WIDE_MAP=auto (the default). With `always` or `never` it fails on purpose (non-map margins visible / map margins black), which shows that the overrides work.
