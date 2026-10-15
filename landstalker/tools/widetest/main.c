/* widetest: LANDSTALKER_WIDE invariants of the patched GPGX renderer, no game ROM needed.
   The scene is built through the real VDP ports (control + data) like a game does: H40, two scroll planes with patterns, per-cell hscroll, sprites.
   It renders the same picture normally and with e extra pixels per side and checks
   (1) the centre of the wide picture equals the normal picture pixel for pixel,
   (2) the new side areas are not empty (the planes show their neighbouring columns),
   (3) sprites that are half off-screen in the normal picture show completely in the wide one (the part that was clipped is visible).
   usage: widetest ROM.md [e]      WIDETEST_DUMP=1 writes /tmp/wt_normal.ppm and /tmp/wt_wide.ppm */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "shared.h"
extern void genrecomp_config_default(void);
extern int lk_wide_e;
extern void lk_clean_planes(void);
extern long lk_world_frame;                         /* frame of the last UpdateSprites call: the test pretends to be a game map frame */
#define W 720
static uint32_t buf[W * 576];
static uint32_t A[320 * 224], B[480 * 224];

static void ctrl(unsigned v) { vdp_68k_ctrl_w(v); }
static void setreg(int r, int d) { ctrl(0x8000 | (r << 8) | d); }
static void vram_at(unsigned a) { ctrl(0x4000 | (a & 0x3FFF)); ctrl((a >> 14) & 3); }
static void dw(unsigned v) { vdp_68k_data_w(v & 0xFFFF); }

/* 8x8 tile: a diagonal stripe of colour `c` over colour 1 (4 bits per pixel, 2 words per row) */
static void tile(int index, int c) {
    vram_at(index * 32);
    for (int r = 0; r < 8; r++) {
        unsigned row = 0;
        for (int x = 0; x < 8; x++) { unsigned p = ((x + r) % 8 < 3) ? c : 1; row = (row << 4) | p; }
        dw(row >> 16); dw(row & 0xFFFF);
    }
}
static void render(int e, uint32_t *out) {
    lk_wide_e = e;
    window_clip(reg[17], reg[12] & 1);               /* a real game has the limits computed with the final width setting from the start */
    bitmap.viewport.w = 320 + 2 * e; bitmap.viewport.h = 224; bitmap.viewport.x = 0; bitmap.viewport.y = 0;
    memset(buf, 0, sizeof(buf));
    for (int line = 0; line < 224; line++) { v_counter = line; render_line(line); }
    int w = 320 + 2 * e;
    for (int y = 0; y < 224; y++) memcpy(out + y * w, (uint8_t *)buf + (size_t)y * bitmap.pitch, (size_t)w * 4);
}

/* independent model of the scene: pixel (x, y) of a picture whose planes are shifted right by `off` extra pixels (0 = normal picture, e = wide picture) */
static uint32_t model_px(int x, int y, int off) {
    static const unsigned pal12[8] = { 0x000, 0x444, 0x00E, 0x0E0, 0xE00, 0x0EE, 0xE0E, 0xEE0 };
    int cell = y / 8, sA = 40 + cell * 3 + off, sB = 5 + cell * 7 + off;
    int XA = ((x - sA) % 512 + 512) % 512, XB = ((x - sB) % 512 + 512) % 512, col;
    int ci = 0, row = y % 8, mL = off >> 4;
    if (y < 32 || x / 16 >= 5 + mL) {                 /* window: top 4 cell rows over the whole line, below that everything from cell 5 to the right edge */
        int c = x / 16 - mL;
        if (c < 0 || c > 19) return 0xFF000000u;           /* margins next to the window are blank (border colour = black) */
        int tc = 2 * c + ((x % 16) / 8), tw = 1 + ((tc + y / 8) % 6);
        if (y / 8 < 4) {                                   /* only rows 0..3 of the window name table are written; the rest is tile 0 (transparent) */
            ci = (((x % 8) + row) % 8 < 3) ? tw : 1;
            unsigned c12 = pal12[ci], r0 = c12 & 0xF, g0 = (c12 >> 4) & 0xF, b0 = (c12 >> 8) & 0xF;
            return 0xFF000000u | ((r0 * 17u) << 16) | ((g0 * 17u) << 8) | (b0 * 17u);
        }
        goto plane_b;                                       /* transparent window tile: plane B shows (plane A is not drawn under the window) */
    }
    col = XA / 8; { int na = ((col * 3 + cell) % 5 == 0) ? 4 + (col % 3) : 0; if (na) ci = (((XA % 8) + row) % 8 < 3) ? na : 1; }
plane_b:
    if (!ci) { col = XB / 8; int nb = 1 + ((col + cell) % 3); ci = (((XB % 8) + row) % 8 < 3) ? nb : 1; }
    unsigned c = pal12[ci], r = (c & 0xF) , g = (c >> 4) & 0xF, b = (c >> 8) & 0xF;   /* 12 bit BGR as written to CRAM */
    return 0xFF000000u | ((r * 17u) << 16) | ((g * 17u) << 8) | (b * 17u);
}
static int in_sprite(int x, int y, int off) {   /* the three sprites (16x16) and a margin, in the picture coordinates of a frame with `off` */
    static const int sp[3][2] = { { 100, 60 }, { -8, 100 }, { 316, 140 } };
    for (int i = 0; i < 3; i++) if (x >= sp[i][0] + off - 1 && x < sp[i][0] + off + 17 && y >= sp[i][1] - 1 && y < sp[i][1] + 17) return 1;
    return 0;
}
int main(int argc, char **argv) {
    int e = argc > 2 ? atoi(argv[2]) : 24, fails = 0;
    lk_world_frame = 0;
    genrecomp_config_default();
    memset(&bitmap, 0, sizeof(bitmap)); bitmap.width = W; bitmap.height = 576; bitmap.pitch = W * 4; bitmap.data = (uint8 *)buf;
    if (!load_rom(argv[1])) { printf("load_rom failed\n"); return 2; }
    audio_init(44100, 0);
    input.system[0] = SYSTEM_GAMEPAD; input.system[1] = SYSTEM_GAMEPAD;
    system_init(); system_reset();
    bitmap.data = (uint8 *)buf;

    /* registers: mode 5, display on, H40, plane A 0xC000, window 0xF000, plane B 0xE000, sprites 0xD800, hscroll table 0xFC00 (per cell), 64x32 planes, auto increment 2 */
    static const int regs[][2] = { {0, 0x04}, {1, 0x04}, {2, 0x30}, {3, 0x3C}, {4, 0x07}, {5, 0x6C}, {7, 0x00}, {10, 0xFF}, {11, 0x02}, {12, 0x81}, {13, 0x3F}, {15, 0x02}, {16, 0x01}, {17, 0x85}, {18, 0x04} };
    for (unsigned i = 0; i < sizeof(regs) / sizeof(regs[0]); i++) setreg(regs[i][0], regs[i][1]);

    ctrl(0xC000); ctrl(0x0000);                        /* palette: line 0 */
    static const unsigned pal[8] = { 0x000, 0x444, 0x00E, 0x0E0, 0xE00, 0x0EE, 0xE0E, 0xEE0 };
    for (int i = 0; i < 64; i++) dw(pal[i % 8]);
    vram_at(0); for (int i = 0; i < 16; i++) dw(0);        /* tile 0: fully transparent (colour 0) */
    for (int t = 1; t <= 7; t++) tile(t, t);
    /* plane A at 0xC000 (sparse), plane B at 0xE000 (dense); entries are words: tile number in the low bits */
    for (int plane = 0; plane < 2; plane++) {
        vram_at(plane ? 0xE000 : 0xC000);
        for (int y = 0; y < 32; y++) for (int x = 0; x < 64; x++)
            dw(plane ? (1 + ((x + y) % 3)) : (((x * 3 + y) % 5 == 0) ? 4 + (x % 3) : 0));
    }
    for (int row = 0; row < 4; row++) {                  /* window plane at 0xF000: rows 0..3 */
        vram_at(0xF000 + row * 128);
        for (int c = 0; c < 64; c++) dw(1 + ((c + row) % 6));
    }
    /* horizontal scroll, per 8-line cell row: plane A then plane B */
    vram_at(0xFC00);
    for (int cell = 0; cell < 28; cell++) { dw(40 + cell * 3); dw(5 + cell * 7); for (int pad = 0; pad < 14; pad++) dw(0); }
    /* sprites at 0xD800: #0 on screen, #1 half off the left edge (x=-8), #2 half off the right edge (x=316); 2x2 cells, linked 0 -> 1 -> 2 */
    static const int sp[3][3] = { { 100, 60, 5 }, { -8, 100, 6 }, { 316, 140, 7 } };
    vram_at(0xD800);
    for (int i = 0; i < 3; i++) {
        dw(sp[i][1] + 0x80); dw(0x0500 | (i < 2 ? i + 1 : 0)); dw(sp[i][2]); dw(sp[i][0] + 0x80);
    }
    for (int i = 3; i < 80; i++) { dw(0); dw(0); dw(0); dw(0); }

    setreg(1, 0x64);                                   /* display on (the setup above ran with the display off, like a game does) */
    render(0, A);
    render(e, B);
    int w = 320 + 2 * e, diff = 0, first = -1;
    if (getenv("WIDETEST_DUMP")) {
        FILE *f = fopen("/tmp/wt_normal.ppm", "wb"); fprintf(f, "P6\n320 224\n255\n"); for (int i = 0; i < 320 * 224; i++) { fputc((A[i] >> 16) & 255, f); fputc((A[i] >> 8) & 255, f); fputc(A[i] & 255, f); } fclose(f);
        f = fopen("/tmp/wt_wide.ppm", "wb"); fprintf(f, "P6\n%d 224\n255\n", w); for (int i = 0; i < w * 224; i++) { fputc((B[i] >> 16) & 255, f); fputc((B[i] >> 8) & 255, f); fputc(B[i] & 255, f); } fclose(f);
    }
    for (int y = 0; y < 224; y++) for (int x = 0; x < 320; x++) if (A[y * 320 + x] != B[y * w + e + x]) {
        if (first < 0) first = y * 320 + x;
        if (++diff <= 6) printf("  diff x=%d y=%d normal %08X wide %08X\n", x, y, A[y * 320 + x], B[y * w + e + x]);
    }
    printf("centre: %d of %d pixels differ%s\n", diff, 320 * 224, diff ? "" : " (identical)");
    if (diff) fails++;
    { /* both frames against the model (outside the sprite boxes) */
        int badn = 0, badw = 0, cnt = 0, firstn = -1, firstw = -1;
        for (int y = 0; y < 224; y++) for (int x = 0; x < 320; x++) if (!in_sprite(x, y, 0)) {
            cnt++; if (A[y * 320 + x] != model_px(x, y, 0)) { if (firstn < 0) firstn = y * 320 + x; badn++; }
        }
        for (int y = 0; y < 224; y++) for (int x = 0; x < w; x++) if (!in_sprite(x, y, e)) {
            if (B[y * w + x] != model_px(x, y, e)) { if (firstw < 0) firstw = y * w + x; badw++; }
        }
        printf("model check: normal picture %d wrong of %d pixels, wide picture %d wrong of %d\n", badn, cnt, badw, w * 224);
        if (firstn >= 0) printf("  first wrong in normal: x=%d y=%d got %08X expected %08X\n", firstn % 320, firstn / 320, A[firstn], model_px(firstn % 320, firstn / 320, 0));
        if (firstw >= 0) printf("  first wrong in wide: x=%d y=%d got %08X expected %08X\n", firstw % w, firstw / w, B[firstw], model_px(firstw % w, firstw / w, e));
    }
    int nonbg = 0, total = 0;
    for (int y = 0; y < 224; y++) for (int x = 0; x < e; x++) {
        total += 2;
        nonbg += (B[y * w + x] != 0xFF000000u) + (B[y * w + w - 1 - x] != 0xFF000000u);
    }
    printf("side areas: %d of %d pixels are not black\n", nonbg, total);
    if (e > 0 && nonbg == 0) { printf("FAIL side areas empty\n"); fails++; }
    /* sprite #1 sits at x=-8..8 in the normal picture (left half clipped). In the wide picture its left half lies at wide x = e-8 .. e-1 and must contain sprite colours (tile 6 = colour 6 stripes) */
    int spr = 0;
    for (int y = 100; y < 116; y++) for (int x = e - 8; x < e; x++) if (B[y * w + x] == 0xFFEE00EEu) spr++;
    printf("sprite at the left edge: %d sprite-coloured pixels in the new area [e-8, e)\n", spr);
    if (e > 0 && spr == 0) { printf("FAIL left sprite not visible in the wide picture\n"); fails++; }
    int sprr = 0;
    for (int y = 140; y < 156; y++) for (int x = e + 320; x < w; x++) if (B[y * w + x] != 0xFF000000u) sprr++;
    printf("right margin next to the window: %d non-black pixels at y 140..155 (must be 0: blanked)\n", sprr);
    if (e > 0 && sprr) { printf("FAIL right margin not blanked\n"); fails++; }
    int top = 0;
    for (int y = 0; y < 32; y++) for (int x = 0; x < e; x++) top += B[y * w + x] != 0xFF000000u;
    printf("top (full-line window) left margin: %d non-black pixels (must be 0)\n", top);
    if (e > 0 && top) { printf("FAIL window rows margin not blanked\n"); fails++; }
    lk_world_frame = -1000;                                        /* a frame that is not the game map: all margins black */
    render(e, B);
    int menu = 0;
    for (int y = 0; y < 224; y++) for (int x = 0; x < e; x++) menu += (B[y * w + x] != 0xFF000000u) + (B[y * w + w - 1 - x] != 0xFF000000u);
    printf("non-map frame: %d non-black margin pixels (must be 0)\n", menu);
    if (e > 0 && menu) { printf("FAIL non-map margins not blanked\n"); fails++; }
    {   /* lk_clean_planes: both name tables become empty, sprite table / window / hscroll table stay */
        extern unsigned short ntab, ntbb, ntwb, satb, hscb;
        int a_ok = 1, b_ok = 1, keep = 0;
        lk_clean_planes();
        for (int i = 0; i < 0x1000; i++) { if (vram[ntab + i]) a_ok = 0; if (vram[ntbb + i]) b_ok = 0; }
        for (int i = 0; i < 0x200; i++) if (vram[satb + i] || vram[hscb + i]) keep++;
        for (int i = 0; i < 0x200; i++) if (vram[ntwb + i]) keep++;
        printf("lk_clean_planes: plane A %s, plane B %s, other tables %s\n", a_ok ? "empty" : "NOT EMPTY", b_ok ? "empty" : "NOT EMPTY", keep ? "kept" : "ALSO CLEARED");
        if (!a_ok || !b_ok || !keep) { printf("FAIL lk_clean_planes\n"); fails++; }
    }
    printf(fails ? "widetest: %d FAILED\n" : "widetest: all ok\n", fails);
    return fails != 0;
}
