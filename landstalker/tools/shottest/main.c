/* shottest: checks tools/shot_core.c without SDL/ROM. Usage: shottest OUT_DIR  (writes a.png 40x30 scale 1, b.png scale 3; tools/shottest/run.sh decodes them with python zlib) */
#include "../shot_core.c"
int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: shottest OUT_DIR\n"); return 2; }
    static uint32_t px[40 * 30]; char p[600];
    for (int y = 0; y < 30; y++) for (int x = 0; x < 40; x++) px[y * 40 + x] = 0xFF000000u | ((x * 6) << 16) | ((y * 8) << 8) | ((x ^ y) & 0xFF);
    snprintf(p, sizeof p, "%s/a.png", argv[1]); if (!lk_shot_png(p, px, 40, 30, 1)) return 1;
    snprintf(p, sizeof p, "%s/b.png", argv[1]); if (!lk_shot_png(p, px, 40, 30, 3)) return 1;
    /* big image: more than one stored deflate block (> 65535 raw bytes) */
    static uint32_t big[320 * 224]; for (int i = 0; i < 320 * 224; i++) big[i] = 0xFF000000u | (uint32_t)(i * 2654435761u);
    snprintf(p, sizeof p, "%s/c.png", argv[1]); if (!lk_shot_png(p, big, 320, 224, 1)) return 1;
    if (!lk_shot_wanted("5,300,1000", 300) || lk_shot_wanted("5,300,1000", 30) || !lk_shot_wanted("5,300,1000", 5) || !lk_shot_wanted("5,300,1000", 1000)) return 3;
    { static char big[20000]; int o = 0; for (int i = 1000; i < 2300; i++) o += snprintf(big + o, sizeof big - o, "%d,", i); if (!lk_shot_wanted(big, 2299) || lk_shot_wanted(big, 999) || lk_shot_wanted(big, 2300)) return 4; }
    FILE *f = fopen("/dev/null", "w"); (void)f;
    return 0;
}
