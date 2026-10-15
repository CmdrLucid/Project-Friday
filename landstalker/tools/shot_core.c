/* LK_SHOT_BEGIN: pure screenshot helpers (no SDL). Pasted into platform_sdl.c by tools/patch_shot.py; tools/shottest compiles this file on its own.
   Pixels are 0xFFRRGGBB (ARGB8888, see LESSONS 9 item 5). PNG output uses uncompressed (stored) deflate blocks: no zlib needed. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t lk_shot_crc_tab[256]; static int lk_shot_crc_init;
static uint32_t lk_shot_crc(uint32_t c, const uint8_t *p, size_t n) {
    if (!lk_shot_crc_init) {
        for (uint32_t i = 0; i < 256; i++) { uint32_t v = i; for (int k = 0; k < 8; k++) v = (v & 1) ? 0xEDB88320u ^ (v >> 1) : v >> 1; lk_shot_crc_tab[i] = v; }
        lk_shot_crc_init = 1;
    }
    c = ~c; while (n--) c = lk_shot_crc_tab[(c ^ *p++) & 0xFF] ^ (c >> 8); return ~c;
}
static void lk_shot_be32(uint8_t *p, uint32_t v) { p[0] = v >> 24; p[1] = v >> 16; p[2] = v >> 8; p[3] = v; }
static int lk_shot_chunk(FILE *f, const char *type, const uint8_t *data, uint32_t len) {
    uint8_t h[8]; lk_shot_be32(h, len); memcpy(h + 4, type, 4);
    uint32_t c = lk_shot_crc(0, h + 4, 4); if (len) c = lk_shot_crc(c, data, len);
    uint8_t t[4]; lk_shot_be32(t, c);
    return fwrite(h, 1, 8, f) == 8 && (!len || fwrite(data, 1, len, f) == len) && fwrite(t, 1, 4, f) == 4;
}
/* write w x h pixels (row stride = w) as an RGB PNG, every pixel repeated scale x scale times; returns 1 on success */
static int lk_shot_png(const char *path, const uint32_t *px, int w, int h, int scale) {
    if (scale < 1) scale = 1;
    int ow = w * scale, oh = h * scale;
    size_t rowb = 1 + (size_t)ow * 3, rawn = rowb * oh;
    uint8_t *raw = (uint8_t *)malloc(rawn); if (!raw) return 0;
    for (int y = 0; y < oh; y++) {
        uint8_t *r = raw + (size_t)y * rowb; *r++ = 0;
        const uint32_t *src = px + (size_t)(y / scale) * w;
        for (int x = 0; x < ow; x++) { uint32_t c = src[x / scale]; *r++ = c >> 16; *r++ = c >> 8; *r++ = c; }
    }
    size_t nblk = (rawn + 65534) / 65535, zn = 2 + rawn + nblk * 5 + 4;
    uint8_t *z = (uint8_t *)malloc(zn); if (!z) { free(raw); return 0; }
    size_t o = 0; z[o++] = 0x78; z[o++] = 0x01;
    uint32_t a = 1, b = 0;
    for (size_t i = 0; i < rawn; i++) { a = (a + raw[i]) % 65521; b = (b + a) % 65521; }
    for (size_t i = 0; i < rawn; i += 65535) {
        size_t n = rawn - i < 65535 ? rawn - i : 65535;
        z[o++] = (i + n >= rawn); z[o++] = n & 0xFF; z[o++] = n >> 8; z[o++] = ~n & 0xFF; z[o++] = (~n >> 8) & 0xFF;
        memcpy(z + o, raw + i, n); o += n;
    }
    lk_shot_be32(z + o, (b << 16) | a); o += 4;
    FILE *f = fopen(path, "wb"); int ok = 0;
    if (f) {
        static const uint8_t sig[8] = { 0x89, 'P', 'N', 'G', 13, 10, 26, 10 };
        uint8_t ihdr[13]; lk_shot_be32(ihdr, ow); lk_shot_be32(ihdr + 4, oh); ihdr[8] = 8; ihdr[9] = 2; ihdr[10] = ihdr[11] = ihdr[12] = 0;
        ok = fwrite(sig, 1, 8, f) == 8 && lk_shot_chunk(f, "IHDR", ihdr, 13) && lk_shot_chunk(f, "IDAT", z, (uint32_t)o) && lk_shot_chunk(f, "IEND", NULL, 0);
        ok = (fclose(f) == 0) && ok;
    }
    free(z); free(raw); return ok;
}
/* is frame number n in the comma separated list? (any length; scans the list, no copy) */
static int lk_shot_wanted(const char *list, long n) {
    const char *p = list;
    while (*p) {
        char *end; long v = strtol(p, &end, 10);
        if (end != p && v == n) return 1;
        p = (end != p) ? end : p + 1;
        while (*p == ',') p++;
    }
    return 0;
}
/* LK_SHOT_END */
