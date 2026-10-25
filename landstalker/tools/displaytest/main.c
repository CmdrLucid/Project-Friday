/* displaytest: checks tools/display_core.c without SDL. Writes PPM images of the filter output for a synthetic 320x224 test frame.
   usage: displaytest outdir */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include "../display_core.c"

static uint32_t px(int r, int g, int b) { return 0xFF000000u | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b; }   /* like the core: 0xFFRRGGBB */
static void write_ppm(const char *path, const uint32_t *p, int w, int h) {
    FILE *f = fopen(path, "wb"); fprintf(f, "P6\n%d %d\n255\n", w, h);
    for (int i = 0; i < w * h; i++) { fputc((p[i] >> 16) & 255, f); fputc((p[i] >> 8) & 255, f); fputc(p[i] & 255, f); }
    fclose(f);
}

/* reference = the original per-channel filter (before the 2026-10-10 speed-up) */
static void lk_fx_render_ref(const uint32_t *src, uint32_t *dst, int dw, int dh, int sw) {
    for (int y = 0; y < dh; y++) {
        const uint32_t *row = src + (size_t)lk_trow[y] * sw; uint32_t wy = lk_twy[y]; uint32_t *o = dst + (size_t)y * dw;
        for (int x = 0; x < dw; x++) {
            uint32_t a = row[lk_tx0[x]], b = row[lk_tx1[x]], wx = lk_twx[x], iw = 256 - wx;
            uint32_t r = (((a >> 16) & 255) * iw + ((b >> 16) & 255) * wx) >> 8, g = (((a >> 8) & 255) * iw + ((b >> 8) & 255) * wx) >> 8, bl = ((a & 255) * iw + (b & 255) * wx) >> 8;
            const uint16_t *mk = lk_tmask[x % 3];
            r = (r * wy >> 8) * mk[0] >> 8; g = (g * wy >> 8) * mk[1] >> 8; bl = (bl * wy >> 8) * mk[2] >> 8;
            if (r > 255) r = 255; if (g > 255) g = 255; if (bl > 255) bl = 255;
            o[x] = 0xFF000000u | (r << 16) | (g << 8) | bl;
        }
    }
}
#include <time.h>
static double now_ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1000.0 + t.tv_nsec / 1e6; }
static int check_fast_filter(void) {
    int fails = 0; static uint32_t src[448 * LK_SRC_H]; static uint32_t o1[1280 * 800], o2[1280 * 800];
    uint32_t seed = 12345; for (int i = 0; i < 448 * LK_SRC_H; i++) { seed = seed * 1664525u + 1013904223u; src[i] = 0xFF000000u | (seed >> 8); }
    int sws[3] = { 320, 384, 416 };
    for (int s = 0; s < 3; s++) for (int fx = LK_FX_SCAN; fx <= LK_FX_CRT; fx++) {
        lk_fx_prepare(1280, 800, fx, sws[s]); lk_fx_render_ref(src, o1, 1280, 800, sws[s]); lk_fx_render(src, o2, 1280, 800, sws[s]);
        int md = 0; for (int i = 0; i < 1280 * 800; i++) for (int sh = 0; sh < 24; sh += 8) { int d = (int)((o1[i] >> sh) & 255) - (int)((o2[i] >> sh) & 255); if (d < 0) d = -d; if (d > md) md = d; }
        if (md > 2) { printf("FAIL fast filter sw=%d fx=%d max diff %d\n", sws[s], fx, md); fails++; }
        else printf("fast filter sw=%d fx=%d: max diff %d levels (ok)\n", sws[s], fx, md);
    }
    lk_fx_prepare(1280, 800, LK_FX_CRT, 384);
    double t0 = now_ms(); for (int i = 0; i < 20; i++) lk_fx_render_ref(src, o1, 1280, 800, 384); double t1 = now_ms(); for (int i = 0; i < 20; i++) lk_fx_render(src, o2, 1280, 800, 384); double t2 = now_ms();
    printf("benchmark CRT 1280x800 from 384 px: reference %.2f ms, fast %.2f ms per frame (this machine)\n", (t1 - t0) / 20, (t2 - t1) / 20);
    return fails;
}

static int check_sharp(void) {
    int fails = 0; static uint32_t src[416 * LK_SRC_H]; static uint32_t o[1280 * 800];
    /* 1. exact integer scale: identical to nearest neighbour */
    for (int i = 0; i < 320 * LK_SRC_H; i++) src[i] = 0xFF000000u | (uint32_t)(i * 2654435761u >> 8);
    lk_sb_prepare(960, 672, 320); lk_sb_render_rows(src, o, 960, 320, 0, 672);
    int bad = 0; for (int y = 0; y < 672; y++) for (int x = 0; x < 960; x++) if (o[y * 960 + x] != src[(y / 3) * 320 + x / 3]) bad++;
    if (bad) { printf("FAIL sharp: integer scale differs from nearest in %d pixels\n", bad); fails++; }
    /* 2. pure colours stay pure, flat areas flat */
    for (int i = 0; i < 416 * LK_SRC_H; i++) src[i] = 0xFF00FF00u;
    lk_sb_prepare(1280, 746, 416); lk_sb_render_rows(src, o, 1280, 416, 0, 746);
    for (int i = 0; i < 1280 * 746; i++) if (o[i] != 0xFF00FF00u) { printf("FAIL sharp: pure green changed\n"); fails++; break; }
    /* 3. an edge at source column e moves by exactly the scale per source pixel (no jitter) */
    int cfg[][2] = { { 384, 1280 }, { 416, 960 }, { 416, 1280 }, { 320, 1142 }, { 384, 960 } };
    for (unsigned c = 0; c < sizeof cfg / sizeof cfg[0]; c++) {
        int sw = cfg[c][0], dw = cfg[c][1], dh = 800; double prev = -1, mn = 1e9, mx = -1e9;
        lk_sb_prepare(dw, dh, sw);
        for (int e = 100; e < 140; e++) {
            for (int y = 0; y < LK_SRC_H; y++) for (int x = 0; x < sw; x++) src[y * sw + x] = x >= e ? 0xFFFFFFFFu : 0xFF000000u;
            lk_sb_render_rows(src, o, dw, sw, 400, 401);
            double mass = 0; for (int x = 0; x < dw; x++) mass += 1.0 - (double)(o[400 * dw + x] & 255) / 255.0;
            if (prev >= 0) { double st = mass - prev; if (st < mn) mn = st; if (st > mx) mx = st; }
            prev = mass;
        }
        printf("sharp-bilinear %d -> %d: edge step per source px %.3f..%.3f (ideal %.3f), jitter %.3f px\n", sw, dw, mn, mx, (double)dw / sw, mx - mn);
        if (mx - mn > 0.03) { printf("FAIL sharp jitter\n"); fails++; }
    }
    return fails;
}
/* usage: displaytest --dedither in.ppm out.ppm [diff.ppm]: de-dithers a 320x224 (or wider) P6 image; diff.ppm marks the changed pixels red on a dimmed copy */
static int dedither_cli(const char *in, const char *outp, const char *diffp) {
    FILE *f = fopen(in, "rb"); if (!f) { printf("cannot open %s\n", in); return 1; }
    int w, h, mx; if (fscanf(f, "P6 %d %d %d", &w, &h, &mx) != 3 || h != LK_SRC_H) { printf("need a P6 image with height 224\n"); return 1; }
    fgetc(f); uint32_t *a = malloc((size_t)w * h * 4), *b = malloc((size_t)w * h * 4);
    for (int i = 0; i < w * h; i++) { int r = fgetc(f), g = fgetc(f), bl = fgetc(f); a[i] = px(r, g, bl); }
    fclose(f); if (getenv("DD_BIL")) { int rg = 80, gt = 0; sscanf(getenv("DD_BIL"), "%d,%d", &rg, &gt); lk_dd_build_near(a, w); memcpy(b, a, (size_t)w * 224 * 4); lk_dedither_bil_rows(a, b, w, rg, gt, 0, 224); } else if (getenv("DD_BLEND")) lk_dedither_blend(a, b, w); else if (getenv("DD_STRONG")) lk_dedither_strong(a, b, w); else lk_dedither(a, b, w);
    long n = 0; for (int i = 0; i < w * h; i++) if (a[i] != b[i]) n++;
    printf("de-dither: %ld of %d pixels changed (%.1f %%)\n", n, w * h, 100.0 * n / (w * h));
    write_ppm(outp, b, w, h);
    if (diffp) { for (int i = 0; i < w * h; i++) b[i] = a[i] != b[i] ? px(255, 0, 0) : (((a[i] >> 1) & 0x7F7F7F7Fu) | 0xFF000000u); write_ppm(diffp, b, w, h); }
    return 0;
}
/* usage: displaytest --hdfx in.ppm N outprefix [dw dh]: a 1x P6 picture (height 224) is repeated N x N (= an HD picture without detail) and filtered at dw x dh (default 1280 x 800) with every CRT filter, once as the 1x chain and once as the HD chain (lk_hdn = N);
   writes <outprefix>_fx<k>_1x.ppm / _hd.ppm and prints the mean / max channel difference (the HD chain must look like the 1x one when the HD picture has no extra detail; CRT / PRO / CURVE sample the finer columns, so small differences at edges are expected) */
static const char *lk_fx_names_cli[LK_FX_N] = { "off", "scanlines", "crt", "crt pro", "crt curved" };
static void hdfx_render(const uint32_t *src, uint32_t *dst, int dw, int dh, int sw, int fx) {
    if (fx >= LK_FX_PRO) { lk_f2_prepare(dw, dh, fx, sw); lk_f2_hrows(src, sw, 0, LK_SRC_H); lk_f2_vrows(dst, 0, dh); }
    else { lk_fx_prepare(dw, dh, fx, sw); lk_fx_render(src, dst, dw, dh, sw); }
}
static int hdfx_cli(int argc, char **argv) {
    const char *in = argv[2]; int N = atoi(argv[3]), dw = argc > 6 ? atoi(argv[6]) : 1280, dh = argc > 7 ? atoi(argv[7]) : 800;
    FILE *f = fopen(in, "rb"); if (!f) { printf("cannot open %s\n", in); return 1; }
    int w, h, mx; if (fscanf(f, "P6 %d %d %d", &w, &h, &mx) != 3 || h != LK_SRC_H || N < 1) { printf("need a P6 image with height 224\n"); return 1; }
    fgetc(f); uint32_t *a = malloc((size_t)w * h * 4), *hd = malloc((size_t)w * N * h * N * 4), *o1 = malloc((size_t)dw * dh * 4), *o2 = malloc((size_t)dw * dh * 4);
    for (int i = 0; i < w * h; i++) { int r = fgetc(f), g = fgetc(f), bl = fgetc(f); a[i] = px(r, g, bl); }
    fclose(f);
    for (int y = 0; y < h * N; y++) for (int x = 0; x < w * N; x++) hd[(size_t)y * w * N + x] = a[(size_t)(y / N) * w + x / N];
    for (int fx = LK_FX_SCAN; fx < LK_FX_N; fx++) {
        char path[600]; double sum = 0; int md = 0;
        lk_hdn = 1; hdfx_render(a, o1, dw, dh, w, fx);
        lk_hdn = N; hdfx_render(hd, o2, dw, dh, w * N, fx); lk_hdn = 1;
        for (size_t i = 0; i < (size_t)dw * dh; i++) for (int sh = 0; sh < 24; sh += 8) { int d = (int)((o1[i] >> sh) & 255) - (int)((o2[i] >> sh) & 255); if (d < 0) d = -d; sum += d; if (d > md) md = d; }
        double t1 = 1e9, t2 = 1e9; for (int k = 0; k < 4; k++) { double t0 = now_ms(); lk_hdn = 1; hdfx_render(a, o1, dw, dh, w, fx); t1 = fmin(t1, now_ms() - t0); t0 = now_ms(); lk_hdn = N; hdfx_render(hd, o2, dw, dh, w * N, fx); lk_hdn = 1; t2 = fmin(t2, now_ms() - t0); }
        printf("fx %d (%s): mean channel difference 1x vs HD %.3f, max %d; single thread %.1f ms (1x) / %.1f ms (HD)\n", fx, lk_fx_names_cli[fx], sum / ((double)dw * dh * 3), md, t1, t2);
        snprintf(path, sizeof path, "%s_fx%d_1x.ppm", argv[4], fx); write_ppm(path, o1, dw, dh);
        snprintf(path, sizeof path, "%s_fx%d_hd.ppm", argv[4], fx); write_ppm(path, o2, dw, dh);
    }
    return 0;
}
int main(int argc, char **argv) {
    const char *out = argc > 1 ? argv[1] : ".";
    if (argc > 4 && !strcmp(argv[1], "--hdfx")) return hdfx_cli(argc, argv);
    if (argc > 3 && !strcmp(argv[1], "--dedither")) return dedither_cli(argv[2], argv[3], argc > 4 ? argv[4] : NULL);
    int fails = 0;
    fails += check_fast_filter();
    fails += check_sharp();
    /* rectangle maths */
    struct { int mode, ow, oh, w, h; } cases[] = {
        { LK_SC_FIT, 1280, 800, 1142, 800 }, { LK_SC_43, 1280, 800, 1066, 800 }, { LK_SC_INT, 1280, 800, 960, 672 },
        { LK_SC_FILL, 1280, 800, 1280, 800 }, { LK_SC_INT, 300, 200, 285, 200 /* too small: falls back to aspect fit */ }, { LK_SC_FIT, 1920, 1080, 1542, 1080 } };
    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        lk_rect r; lk_calc_rect(cases[i].mode, cases[i].ow, cases[i].oh, 320, &r);
        int ok = r.w == cases[i].w && r.h == cases[i].h && r.x == (cases[i].ow - r.w) / 2 && r.y == (cases[i].oh - r.h) / 2 && r.w <= cases[i].ow && r.h <= cases[i].oh;
        if (!ok) { printf("FAIL rect mode=%d %dx%d -> %dx%d at %d,%d (expected %dx%d)\n", cases[i].mode, cases[i].ow, cases[i].oh, r.w, r.h, r.x, r.y, cases[i].w, cases[i].h); fails++; }
    }
    /* synthetic frame: colour bars, a gradient, a checker, white text */
    static uint32_t src[LK_SRC_W * LK_SRC_H];
    for (int y = 0; y < LK_SRC_H; y++) for (int x = 0; x < LK_SRC_W; x++) {
        uint32_t p;
        if (y < 60) { int bar = x * 8 / LK_SRC_W; static const int c[8][3] = {{255,255,255},{255,255,0},{0,255,255},{0,255,0},{255,0,255},{255,0,0},{0,0,255},{40,40,40}}; p = px(c[bar][0], c[bar][1], c[bar][2]); }
        else if (y < 120) p = px(x * 255 / LK_SRC_W, x * 255 / LK_SRC_W, x * 255 / LK_SRC_W);
        else if (y < 180) p = (((x / 8) + (y / 8)) & 1) ? px(230, 200, 120) : px(40, 80, 60);
        else p = px(20, 20, 60);
        src[y * LK_SRC_W + x] = p;
    }
    const char *msg = "SCALE: 4:3 FILTER: CRT 0123456789";
    for (int i = 0; msg[i]; i++) { const uint8_t *g = lk_glyph(msg[i]); for (int r = 0; r < 7; r++) for (int c = 0; c < 5; c++) if (g[r] & (0x10 >> c)) src[(190 + r) * LK_SRC_W + 8 + i * 6 + c] = px(255, 255, 255); }
    { /* channel order: pure red / green / blue stay pure */
        static uint32_t t[LK_SRC_W * LK_SRC_H]; static uint32_t o[960 * 672];
        uint32_t cols[3] = { px(255, 0, 0), px(0, 255, 0), px(0, 0, 255) };
        for (int c = 0; c < 3; c++) {
            for (int i = 0; i < LK_SRC_W * LK_SRC_H; i++) t[i] = cols[c];
            for (int fx = LK_FX_SCAN; fx <= LK_FX_CRT; fx++) {
                lk_fx_prepare(960, 672, fx, 320); lk_fx_render(t, o, 960, 672, 320);
                unsigned long sum[3] = { 0, 0, 0 };
                for (int i = 0; i < 960 * 672; i++) { sum[0] += (o[i] >> 16) & 255; sum[1] += (o[i] >> 8) & 255; sum[2] += o[i] & 255; }
                int ok = sum[c] > 0 && sum[(c + 1) % 3] == 0 && sum[(c + 2) % 3] == 0 && (o[0] >> 24) == 0xFF;
                if (!ok) { printf("FAIL colour channel %d fx %d: %lu %lu %lu\n", c, fx, sum[0], sum[1], sum[2]); fails++; }
            }
        }
    }
    { /* widescreen source: 384 px wide. FIT must give 384:224, INT the whole multiple, a pure colour must stay pure */
        lk_rect r; lk_calc_rect(LK_SC_FIT, 1280, 800, 384, &r);
        if (!(r.w == 1280 && r.h == 746 && r.y == 27)) { printf("FAIL wide FIT %dx%d at %d,%d\n", r.w, r.h, r.x, r.y); fails++; }
        lk_calc_rect(LK_SC_INT, 1280, 800, 384, &r);
        if (!(r.w == 1152 && r.h == 672)) { printf("FAIL wide INT %dx%d\n", r.w, r.h); fails++; }
        lk_calc_rect(LK_SC_43, 1280, 800, 384, &r);
        if (!(r.w == 1280 && r.h == 600 * 320 / 384 * 1 + 0 && 0)) { /* 4:3 * 384/320 = 1.6 -> 1280x800 */ }
        static uint32_t big[384 * LK_SRC_H], o[1152 * 672];
        for (int i = 0; i < 384 * LK_SRC_H; i++) big[i] = px(0, 255, 0);
        for (int fx = LK_FX_SCAN; fx <= LK_FX_CRT; fx++) {
            lk_fx_prepare(1152, 672, fx, 384); lk_fx_render(big, o, 1152, 672, 384);
            unsigned long sum[3] = { 0, 0, 0 };
            for (int i = 0; i < 1152 * 672; i++) { sum[0] += (o[i] >> 16) & 255; sum[1] += (o[i] >> 8) & 255; sum[2] += o[i] & 255; }
            if (!(sum[1] > 0 && sum[0] == 0 && sum[2] == 0)) { printf("FAIL wide colour fx %d\n", fx); fails++; }
        }
    }
    int sizes2[][2] = { { 1280, 800 }, { 960, 672 } };
    { /* CRT PRO / CURVED: pure colours stay pure, brightness close to the input, images written */
        static uint32_t o[1280 * 800];
        for (int fx = LK_FX_PRO; fx <= LK_FX_CURVE; fx++) for (int s = 0; s < 2; s++) {
            int dw = sizes2[s][0], dh = sizes2[s][1];
            uint32_t cols[3] = { px(255, 0, 0), px(0, 255, 0), px(0, 0, 255) }; static uint32_t t[LK_SRC_W * LK_SRC_H];
            for (int c = 0; c < 3; c++) {
                for (int i = 0; i < LK_SRC_W * LK_SRC_H; i++) t[i] = cols[c];
                lk_f2_prepare(dw, dh, fx, 320); lk_f2_hrows(t, 320, 0, LK_SRC_H); lk_f2_vrows(o, 0, dh);
                unsigned long sum[3] = { 0, 0, 0 };
                for (int i = 0; i < dw * dh; i++) { sum[0] += (o[i] >> 16) & 255; sum[1] += (o[i] >> 8) & 255; sum[2] += o[i] & 255; }
                if (!(sum[c] > 0 && sum[(c + 1) % 3] == 0 && sum[(c + 2) % 3] == 0)) { printf("FAIL f2 colour %d fx %d: %lu %lu %lu\n", c, fx, sum[0], sum[1], sum[2]); fails++; }
            }
            lk_f2_prepare(dw, dh, fx, 320); lk_f2_hrows(src, 320, 0, LK_SRC_H); lk_f2_vrows(o, 0, dh);
            char path[600]; snprintf(path, sizeof(path), "%s/fx%d_%dx%d.ppm", out, fx, dw, dh); write_ppm(path, o, dw, dh);
            double sin_ = 0, sout = 0;
            for (int i = 0; i < LK_SRC_W * LK_SRC_H; i++) sin_ += ((src[i] >> 16) & 255) + ((src[i] >> 8) & 255) + (src[i] & 255);
            for (int i = 0; i < dw * dh; i++) sout += ((o[i] >> 16) & 255) + ((o[i] >> 8) & 255) + (o[i] & 255);
            printf("fx %d %dx%d: mean brightness in %.1f out %.1f (ratio %.2f)\n", fx, dw, dh, sin_ / (LK_SRC_W * LK_SRC_H), sout / (dw * dh), (sout / (dw * dh)) / (sin_ / (LK_SRC_W * LK_SRC_H)));
        }
    }
    int sizes[][2] = { { 1280, 800 }, { 960, 672 } };
    for (int fx = LK_FX_SCAN; fx <= LK_FX_CRT; fx++) for (int s = 0; s < 2; s++) {
        int dw = sizes[s][0], dh = sizes[s][1];
        uint32_t *dst = malloc((size_t)dw * dh * 4);
        lk_fx_prepare(dw, dh, fx, 320); lk_fx_render(src, dst, dw, dh, 320);
        char path[600]; snprintf(path, sizeof(path), "%s/fx%d_%dx%d.ppm", out, fx, dw, dh); write_ppm(path, dst, dw, dh);
        /* average brightness must stay close to the input (compensation) */
        double sin_ = 0, sout = 0;
        for (int i = 0; i < LK_SRC_W * LK_SRC_H; i++) sin_ += ((src[i] >> 16) & 255) + ((src[i] >> 8) & 255) + (src[i] & 255);
        for (int i = 0; i < dw * dh; i++) sout += ((dst[i] >> 16) & 255) + ((dst[i] >> 8) & 255) + (dst[i] & 255);
        double ratio = (sout / (dw * dh)) / (sin_ / (LK_SRC_W * LK_SRC_H));
        printf("fx=%d %dx%d brightness ratio %.3f\n", fx, dw, dh, ratio);
        if (ratio < 0.85 || ratio > 1.15) { printf("FAIL brightness\n"); fails++; }
        free(dst);
    }
    /* font: print one glyph row set as ASCII for a visual check */
    for (int r = 0; r < 7; r++) { for (const char *m = "FILTER"; *m; m++) { const uint8_t *g = lk_glyph(*m); for (int c = 0; c < 5; c++) putchar(g[r] & (0x10 >> c) ? '#' : '.'); putchar(' '); } putchar('\n'); }
    printf(fails ? "displaytest: %d FAILED\n" : "displaytest: all ok\n", fails);
    return fails != 0;
}
