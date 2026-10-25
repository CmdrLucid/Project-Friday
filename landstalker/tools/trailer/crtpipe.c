/* crtpipe: applies the game's own display filters (tools/display_core.c) to raw frames for the trailer.
   usage: crtpipe SW DW DH FX < frames.bgra > out.bgra   (FX: 0 = sharp-bilinear without filter, 1 Scanlines, 2 CRT, 3 CRT Pro, 4 CRT Curved)
   Input: SW x 224 pixels, 4 bytes each (ffmpeg pix_fmt bgra = 0xAARRGGBB on little endian), output DW x DH in the same format. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include "../display_core.c"
int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: crtpipe SW DW DH FX\n"); return 1; }
    int sw = atoi(argv[1]), dw = atoi(argv[2]), dh = atoi(argv[3]), fx = atoi(argv[4]);
    size_t ns = (size_t)sw * LK_SRC_H, nd = (size_t)dw * dh;
    uint32_t *src = malloc(ns * 4), *dst = malloc(nd * 4);
    long n = 0;
    while (fread(src, 4, ns, stdin) == ns) {
        for (size_t i = 0; i < ns; i++) src[i] |= 0xFF000000u;
        if (fx >= LK_FX_PRO) { lk_f2_prepare(dw, dh, fx, sw); lk_f2_hrows(src, sw, 0, LK_SRC_H); lk_f2_vrows(dst, 0, dh); }
        else if (fx > 0) { lk_fx_prepare(dw, dh, fx, sw); lk_fx_render(src, dst, dw, dh, sw); }
        else { lk_sb_prepare(dw, dh, sw); lk_sb_render_rows(src, dst, dw, sw, 0, dh); }
        fwrite(dst, 4, nd, stdout); fflush(stdout); n++;
    }
    fprintf(stderr, "crtpipe: %ld frames\n", n);
    return 0;
}
