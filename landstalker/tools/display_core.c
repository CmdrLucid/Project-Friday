/* LK_DISPLAY_BEGIN: pure display helpers (no SDL). Pasted into platform_sdl.c by tools/patch_display.py; tools/displaytest compiles this file on its own. */
#define LK_SRC_W 320
#define LK_SRC_H 224
#define LK_MAXDIM 4096
enum { LK_SC_FIT, LK_SC_43, LK_SC_INT, LK_SC_FILL, LK_SC_N };
enum { LK_FX_OFF, LK_FX_SCAN, LK_FX_CRT, LK_FX_PRO, LK_FX_CURVE, LK_FX_N };   /* PRO / CURVE (2026-10-13) are ADDITIONAL filters: the three older ones above are unchanged */
typedef struct { int x, y, w, h; } lk_rect;
static int lk_hdn = 1;   /* HD graphics: the source is sw * lk_hdn x 224 * lk_hdn pixels (1 = the normal 1x picture); scanlines / beam / mask stay per GAME line, the horizontal sampling uses the finer source columns */

/* destination rectangle inside an output of ow x oh pixels */
static void lk_calc_rect(int mode, int ow, int oh, int sw, lk_rect *r) {
    int w, h;
    if (ow < 1) ow = 1;
    if (oh < 1) oh = 1;
    if (mode == LK_SC_FILL) { w = ow; h = oh; }
    else if (mode == LK_SC_INT && ow >= sw && oh >= LK_SRC_H) {
        int k = ow / sw; if (oh / LK_SRC_H < k) k = oh / LK_SRC_H;
        w = sw * k; h = LK_SRC_H * k;
    } else {
        /* aspect fit: FIT = sw:224 (square pixels), 4:3 = TV (a wide picture keeps the TV pixel shape: 4:3 * sw/320) */
        int an = (mode == LK_SC_43) ? 4 * sw : sw, ad = (mode == LK_SC_43) ? 3 * LK_SRC_W : LK_SRC_H;
        w = ow; h = (int)((long long)ow * ad / an);
        if (h > oh) { h = oh; w = (int)((long long)oh * an / ad); }
    }
    r->w = w; r->h = h; r->x = (ow - w) / 2; r->y = (oh - h) / 2;
}

/* ---- CRT / scanline filter (CPU) ---- */
static int lk_tab_dw, lk_tab_dh, lk_tab_fx, lk_tab_sw, lk_tab_hn;
static uint16_t lk_tx0[LK_MAXDIM], lk_tx1[LK_MAXDIM], lk_twx[LK_MAXDIM], lk_trow[LK_MAXDIM], lk_twy[LK_MAXDIM];
static uint16_t lk_tmask[3][3];

static void lk_fx_prepare(int dw, int dh, int fx, int sw) {
    if (dw == lk_tab_dw && dh == lk_tab_dh && fx == lk_tab_fx && sw == lk_tab_sw && lk_hdn == lk_tab_hn) return;
    lk_tab_dw = dw; lk_tab_dh = dh; lk_tab_fx = fx; lk_tab_sw = sw; lk_tab_hn = lk_hdn;
    for (int x = 0; x < dw; x++) {
        float f = ((float)x + 0.5f) * (float)sw / (float)dw - 0.5f;
        if (f < 0) f = 0;
        int x0 = (int)f; if (x0 > sw - 1) x0 = sw - 1;
        int x1 = x0 + 1 < sw ? x0 + 1 : sw - 1;
        lk_tx0[x] = (uint16_t)x0; lk_tx1[x] = (uint16_t)x1;
        lk_twx[x] = (fx == LK_FX_CRT) ? (uint16_t)((f - (float)x0) * 256.0f) : 0;   /* SCANLINES keeps the pixels sharp */
    }
    float a = (fx == LK_FX_CRT) ? 0.65f : 0.50f;            /* scanline depth */
    const int whole = (dh % LK_SRC_H) == 0;                  /* integer vertical scale: every source row gets the same pattern, point sampling is exact */
    if (!whole) a *= 0.70f;                                  /* Fit / Fill (e.g. 800 px = 3.57x): the dark lines fall on 1 or 2 rows, a point sample made some of them 0.45 instead of 0.9 (user: darker stripes); a shallower profile averaged over the row keeps them 0.8 - 1.15 */
    float comp = 1.0f / (1.0f - a / 3.0f);                   /* keep the average brightness */
    for (int y = 0; y < dh; y++) {
        float sy = ((float)y + 0.5f) * LK_SRC_H / (float)dh;
        int row = (int)(sy * (float)lk_hdn); if (row > LK_SRC_H * lk_hdn - 1) row = LK_SRC_H * lk_hdn - 1;   /* source row (HD: the finer row inside the game line) */
        lk_trow[y] = (uint16_t)row;
        float wsum = 0.0f; const int ns = whole ? 1 : 8;
        for (int k = 0; k < ns; k++) {                       /* profile averaged over the destination row's footprint (1 sample at its centre for integer scales) */
            float s2 = whole ? sy : ((float)y + ((float)k + 0.5f) / (float)ns) * LK_SRC_H / (float)dh;
            float t = s2 - (float)(int)s2, d = (t - 0.5f) * 2.0f; if (d < 0) d = -d;
            wsum += 1.0f - a * d * d;
        }
        lk_twy[y] = (uint16_t)(256.0f * (wsum / (float)ns) * comp);
    }
    /* RGB phosphor mask (CRT only): the lit channel keeps full strength, the other two 70 %, compensated */
    float m = 0.70f, mc = 1.0f / ((1.0f + 2.0f * m) / 3.0f);
    for (int i = 0; i < 3; i++) for (int c = 0; c < 3; c++)
        lk_tmask[i][c] = (uint16_t)(fx == LK_FX_CRT ? 256.0f * mc * (i == c ? 1.0f : m) : 256.0f);
}

/* src: sw x 224 pixels (rows are sw pixels apart; sw = 320 or 320 + 2e in widescreen mode) as the GPGX core writes them: 0xFFRRGGBB (SDL_PIXELFORMAT_ARGB8888; build.sh switches the window texture to it); dst: dw x dh, same packing.
   Renders the destination rows y0..y1-1 (the SDL side splits the picture into bands for several threads). Speed (2026-10-10): R and B are blended together in one 32-bit multiply, the scanline weight and the phosphor mask are
   folded into 3 weights per row and mask phase; result differs from the plain per-channel formula by at most 2 levels (tools/displaytest checks it). */
static void lk_fx_render_rows(const uint32_t *src, uint32_t *dst, int dw, int sw, int y0, int y1) {
    for (int y = y0; y < y1; y++) {
        const uint32_t *row = src + (size_t)lk_trow[y] * sw;
        uint32_t wy = lk_twy[y], wk[3][3];
        for (int i = 0; i < 3; i++) for (int c = 0; c < 3; c++) wk[i][c] = wy * lk_tmask[i][c] >> 8;
        uint32_t *o = dst + (size_t)y * dw;
        int ph = 0;
        for (int x = 0; x < dw; x++) {
            uint32_t a = row[lk_tx0[x]], b = row[lk_tx1[x]], wx = lk_twx[x], iw = 256 - wx;
            uint32_t rb = (((a & 0x00FF00FFu) * iw + (b & 0x00FF00FFu) * wx) >> 8) & 0x00FF00FFu;
            uint32_t g = (((a >> 8) & 255) * iw + ((b >> 8) & 255) * wx) >> 8;
            const uint32_t *k = wk[ph]; if (++ph == 3) ph = 0;
            uint32_t r = (rb >> 16) * k[0] >> 8, gg = g * k[1] >> 8, bl = (rb & 255) * k[2] >> 8;
            r = r > 255 ? 255 : r; gg = gg > 255 ? 255 : gg; bl = bl > 255 ? 255 : bl;
            o[x] = 0xFF000000u | (r << 16) | (gg << 8) | bl;
        }
    }
}
static void lk_fx_render(const uint32_t *src, uint32_t *dst, int dw, int dh, int sw) { lk_fx_render_rows(src, dst, dw, sw, 0, dh); }


/* ---- CRT PRO / CRT CURVED (2026-10-13; additional filters, the old ones stay) ----
   Works in linear light (gamma 2.2 tables). Pass 1 (lk_f2_hrows): every source row is filtered horizontally with a soft gaussian (4 taps) into a plane of dw pixels (12 bit linear per channel).
   Pass 2 (lk_f2_vrows): each destination pixel looks up its position in a map (flat: identity; CURVE: barrel warp), blends the two nearest source rows with a vertical beam profile whose width grows with
   the brightness of the row (bright lines are fat and nearly touch, dark lines leave visible gaps, like a real electron beam), applies an RGB aperture-grille mask and the vignette/edge gain, and encodes back to 8 bit. */
static uint16_t lk_f2_dec[256], lk_f2_hw[256][4], lk_f2_wt[64][32];   /* gamma decode, horizontal tap weights per 1/256 fraction (sum 256), beam weight [distance 0..63][brightness 0..31] */
static uint8_t lk_f2_enc[4096];
static uint16_t lk_f2_mask[3][3];
static uint16_t *lk_f2_plane, *lk_f2_mx, *lk_f2_my; static uint8_t *lk_f2_gain;
static int lk_f2_dw, lk_f2_dh, lk_f2_sw, lk_f2_fx, lk_f2_hn;
static void lk_f2_prepare(int dw, int dh, int fx, int sw) {
    if (dw == lk_f2_dw && dh == lk_f2_dh && sw == lk_f2_sw && fx == lk_f2_fx && lk_hdn == lk_f2_hn && lk_f2_plane) return;
    lk_f2_dw = dw; lk_f2_dh = dh; lk_f2_sw = sw; lk_f2_fx = fx; lk_f2_hn = lk_hdn;
    for (int i = 0; i < 256; i++) lk_f2_dec[i] = (uint16_t)(4095.0 * pow(i / 255.0, 2.2) + 0.5);
    for (int i = 0; i < 4096; i++) { double v = pow(i / 4095.0, 1.0 / 2.2) * 255.0 + 0.5; lk_f2_enc[i] = (uint8_t)(v > 255.0 ? 255 : v); }
    for (int f = 0; f < 256; f++) {                         /* taps at source pixels x0-1, x0, x0+1, x0+2, the sample point is x0 + f/256 */
        double w[4], sum = 0, sg = 0.42;
        for (int k = 0; k < 4; k++) { double d = (double)f / 256.0 - (double)(k - 1); w[k] = exp(-d * d / (2 * sg * sg)); sum += w[k]; }
        int tot = 0; for (int k = 0; k < 4; k++) { lk_f2_hw[f][k] = (uint16_t)(256.0 * w[k] / sum + 0.5); tot += lk_f2_hw[f][k]; }
        lk_f2_hw[f][1] = (uint16_t)(lk_f2_hw[f][1] + 256 - tot);
    }
    for (int d = 0; d < 64; d++) for (int b = 0; b < 32; b++) {   /* vertical beam: sigma 0.20 (dark) .. 0.42 (bright) rows */
        double dist = (d + 0.5) / 64.0, sg = 0.20 + 0.22 * (b / 31.0);
        lk_f2_wt[d][b] = (uint16_t)(256.0 * exp(-dist * dist / (2 * sg * sg)) + 0.5);
    }
    const double lit = 1.38, oth = 0.62 * 1.38;               /* aperture grille in linear light: lit channel boosted, the other two dimmer (average ~ 0.85 * ... compensates the beam gaps) */
    for (int i = 0; i < 3; i++) for (int c = 0; c < 3; c++) lk_f2_mask[i][c] = (uint16_t)(256.0 * (i == c ? lit : oth));
    free(lk_f2_plane); free(lk_f2_mx); free(lk_f2_my); free(lk_f2_gain);
    lk_f2_plane = (uint16_t *)malloc((size_t)LK_SRC_H * dw * 4 * 2);
    lk_f2_mx = (uint16_t *)malloc((size_t)dw * dh * 2); lk_f2_my = (uint16_t *)malloc((size_t)dw * dh * 2); lk_f2_gain = (uint8_t *)malloc((size_t)dw * dh);
    if (!lk_f2_plane || !lk_f2_mx || !lk_f2_my || !lk_f2_gain) { free(lk_f2_plane); free(lk_f2_mx); free(lk_f2_my); free(lk_f2_gain); lk_f2_plane = 0; lk_f2_mx = lk_f2_my = 0; lk_f2_gain = 0; return; }
    const double k = (fx == LK_FX_CURVE) ? 0.025 : 0.0, z = 1.0 / (1.0 + k);   /* barrel warp; z shrinks the picture so that the corners stay inside */
    for (int y = 0; y < dh; y++) for (int x = 0; x < dw; x++) {
        double u = 2.0 * (x + 0.5) / dw - 1.0, v = 2.0 * (y + 0.5) / dh - 1.0, g = 1.0;
        double uu = u * z * (1.0 + k * v * v), vv = v * z * (1.0 + k * u * u);
        if (fx == LK_FX_CURVE) {
            double ex = (1.0 - fabs(uu)) * dw * 0.5, ey = (1.0 - fabs(vv)) * dh * 0.5, e = ex < ey ? ex : ey;   /* distance to the screen edge in output pixels: 1.5 px soft edge */
            g = e <= 0 ? 0.0 : e >= 1.5 ? 1.0 : e / 1.5;
            g *= 1.0 - 0.28 * (uu * uu + vv * vv) * 0.5;                                                      /* vignette */
        }
        double px = (uu + 1.0) * 0.5 * dw, sy = ((vv + 1.0) * 0.5 * LK_SRC_H) - 0.5;                          /* plane column, source row (row centres at integers) */
        if (px < 0) px = 0; if (px > dw - 1) px = dw - 1; if (sy < 0) sy = 0; if (sy > LK_SRC_H - 1) sy = LK_SRC_H - 1;
        size_t i = (size_t)y * dw + x;
        lk_f2_mx[i] = (uint16_t)px; lk_f2_my[i] = (uint16_t)(sy * 256.0 + 0.5); lk_f2_gain[i] = (uint8_t)(g * 255.0 + 0.5);
    }
}
static void lk_f2_hrows(const uint32_t *src, int sw, int y0, int y1) {   /* source rows y0..y1-1 -> plane (4 x uint16 per pixel: r g b 0) */
    const int dw = lk_f2_dw;
    for (int y = y0; y < y1; y++) {
        const uint32_t *row = src + (size_t)y * lk_hdn * sw; uint16_t *o = lk_f2_plane + (size_t)y * dw * 4; const int hn = lk_hdn;   /* HD: the hn source rows of the game line y are averaged (linear light) */
        for (int x = 0; x < dw; x++) {
            int p = (int)(((int64_t)(2 * x + 1) * sw * 128) / dw) - 128;   /* source position * 256 of the plane pixel centre, pixel centres at integers */
            if (p < 0) p = 0;
            int x0 = p >> 8, f = p & 255; if (x0 > sw - 1) { x0 = sw - 1; f = 0; }
            const uint16_t *w = lk_f2_hw[f]; uint32_t r = 0, g = 0, b = 0;
            for (int k = 0; k < 4; k++) {
                int xs = x0 + k - 1; if (xs < 0) xs = 0; if (xs > sw - 1) xs = sw - 1;
                if (hn == 1) { uint32_t c = row[xs]; r += lk_f2_dec[(c >> 16) & 255] * w[k]; g += lk_f2_dec[(c >> 8) & 255] * w[k]; b += lk_f2_dec[c & 255] * w[k]; }
                else { uint32_t ar = 0, ag = 0, ab = 0; for (int j = 0; j < hn; j++) { uint32_t c = row[(size_t)j * sw + xs]; ar += lk_f2_dec[(c >> 16) & 255]; ag += lk_f2_dec[(c >> 8) & 255]; ab += lk_f2_dec[c & 255]; } r += ar / hn * w[k]; g += ag / hn * w[k]; b += ab / hn * w[k]; }
            }
            o[x * 4] = (uint16_t)(r >> 8); o[x * 4 + 1] = (uint16_t)(g >> 8); o[x * 4 + 2] = (uint16_t)(b >> 8); o[x * 4 + 3] = 0;
        }
    }
}
static void lk_f2_vrows(uint32_t *dst, int y0, int y1) {
    const int dw = lk_f2_dw;
    for (int y = y0; y < y1; y++) {
        uint32_t *o = dst + (size_t)y * dw; const size_t base = (size_t)y * dw;
        for (int x = 0; x < dw; x++) {
            const uint32_t gn = lk_f2_gain[base + x];
            if (!gn) { o[x] = 0xFF000000u; continue; }
            const int sy = lk_f2_my[base + x], r0 = sy >> 8, fr = sy & 255, r1 = r0 + 1 < LK_SRC_H ? r0 + 1 : r0, mx = lk_f2_mx[base + x];
            const uint16_t *a = lk_f2_plane + ((size_t)r0 * dw + mx) * 4, *b = lk_f2_plane + ((size_t)r1 * dw + mx) * 4;
            uint32_t la = (a[0] * 54u + a[1] * 183u + a[2] * 19u) >> 8, lb = (b[0] * 54u + b[1] * 183u + b[2] * 19u) >> 8;   /* linear luminance, 12 bit */
            uint32_t wa = lk_f2_wt[fr >> 2][lk_f2_enc[la] >> 3], wb = lk_f2_wt[(255 - fr) >> 2][lk_f2_enc[lb] >> 3];
            const uint16_t *m = lk_f2_mask[x % 3]; uint32_t c[3];
            for (int ch = 0; ch < 3; ch++) {
                uint32_t v = (a[ch] * wa + b[ch] * wb) >> 8;            /* beam sum, 12 bit linear */
                v = (v * m[ch] >> 8) * gn / 255u;
                c[ch] = lk_f2_enc[v > 4095 ? 4095 : v];
            }
            o[x] = 0xFF000000u | (c[0] << 16) | (c[1] << 8) | c[2];
        }
    }
}

/* ---- exact sharp-bilinear scaling (CPU, no filter) ----
   Each destination pixel blends the two nearest source pixels (per axis) with a weight that changes only within ONE destination pixel around the boundary between two source pixels:
   pixel interiors stay flat, boundaries sit at the exact fractional position, so scrolling is smooth at any scale (nearest neighbour: columns 3 / 4 px wide = 'wave'; GPU prescale: up to 0.3 px edge jitter). */
static int lk_sbt_dw, lk_sbt_dh, lk_sbt_sw;
static uint16_t lk_sbx0[LK_MAXDIM], lk_sbx1[LK_MAXDIM], lk_sbwx[LK_MAXDIM], lk_sby0[LK_MAXDIM], lk_sby1[LK_MAXDIM], lk_sbwy[LK_MAXDIM];
static void lk_sb_axis(int dn, int sn, uint16_t *i0t, uint16_t *i1t, uint16_t *wt) {
    float S = (float)dn / (float)sn;
    for (int x = 0; x < dn; x++) {
        float p = ((float)x + 0.5f) * (float)sn / (float)dn - 0.5f;
        int i0 = (int)(p >= 0 ? p : p - 1.0f); if (p < 0 && (float)(int)p == p) i0 = (int)p;   /* floor */
        float f = p - (float)i0, w = (f - 0.5f) * S + 0.5f; if (w < 0) w = 0; if (w > 1) w = 1;
        int a = i0 < 0 ? 0 : i0 > sn - 1 ? sn - 1 : i0, b = i0 + 1 < 0 ? 0 : i0 + 1 > sn - 1 ? sn - 1 : i0 + 1;
        i0t[x] = (uint16_t)a; i1t[x] = (uint16_t)b; wt[x] = (uint16_t)(w * 256.0f + 0.5f);
    }
}
static void lk_sb_prepare(int dw, int dh, int sw) {
    if (dw == lk_sbt_dw && dh == lk_sbt_dh && sw == lk_sbt_sw) return;
    lk_sbt_dw = dw; lk_sbt_dh = dh; lk_sbt_sw = sw;
    lk_sb_axis(dw, sw, lk_sbx0, lk_sbx1, lk_sbwx);
    lk_sb_axis(dh, LK_SRC_H, lk_sby0, lk_sby1, lk_sbwy);
}
static inline uint32_t lk_sb_mix(uint32_t a, uint32_t b, uint32_t w) {      /* w = 0..256 weight of b, packed 0xFFRRGGBB (alpha forced to FF by the caller) */
    uint32_t rb = (((a & 0x00FF00FFu) * (256 - w) + (b & 0x00FF00FFu) * w) >> 8) & 0x00FF00FFu;
    uint32_t g = (((a & 0x0000FF00u) * (256 - w) + (b & 0x0000FF00u) * w) >> 8) & 0x0000FF00u;
    return rb | g;
}
static void lk_sb_render_rows(const uint32_t *src, uint32_t *dst, int dw, int sw, int y0, int y1) {
    for (int y = y0; y < y1; y++) {
        const uint32_t *ra = src + (size_t)lk_sby0[y] * sw, *rb = src + (size_t)lk_sby1[y] * sw;
        uint32_t wy = lk_sbwy[y]; uint32_t *o = dst + (size_t)y * dw;
        for (int x = 0; x < dw; x++) {
            uint32_t wx = lk_sbwx[x]; int xa = lk_sbx0[x], xb = lk_sbx1[x];
            uint32_t top = lk_sb_mix(ra[xa], ra[xb], wx);
            uint32_t v = wy ? lk_sb_mix(top, lk_sb_mix(rb[xa], rb[xb], wx), wy) : top;
            o[x] = 0xFF000000u | v;
        }
    }
}


/* ---- de-dither (2026-10-13, optional, independent of the filters) ----
   Many Mega Drive games (Landstalker: ground, water, shadows) fake extra colours with a pixel-by-pixel chequerboard / stripe pattern that a TV blurred into a mixed colour.
   A pixel is replaced by the mix of itself and its two horizontal neighbours when the row really alternates around it: both neighbours are (nearly) the same colour and differ from the pixel,
   and the pattern goes on at least 2 pixels to one side (pixel two to the left OR right equals the pixel again), so single 1-pixel lines / dots / text strokes on a flat background stay sharp.
   Chequerboards alternate in every row, so the horizontal test is enough for them. src and dst: sw x 224 pixels, 0xFFRRGGBB. */
#define LK_DD_SKIP_TOP 24   /* the HUD bar (y 5..22) is never touched: its frame / gauge / hearts are drawn with deliberate pixel patterns */
static inline int lk_dd_nearT(uint32_t a, uint32_t b, int tol) {
    int dr = (int)((a >> 16) & 255) - (int)((b >> 16) & 255), dg = (int)((a >> 8) & 255) - (int)((b >> 8) & 255), db = (int)(a & 255) - (int)(b & 255);
    return dr <= tol && dr >= -tol && dg <= tol && dg >= -tol && db <= tol && db >= -tol;
}
static inline int lk_dd_eq(uint32_t a, uint32_t b) { return ((a ^ b) & 0x00FFFFFFu) == 0; }   /* the Mega Drive palette steps are 34 per channel, so 'within 6' means 'equal' on the original picture (fast path of the smoothing pass) */
static inline uint32_t lk_dd_mix2(uint32_t a, uint32_t b) { return 0xFF000000u | ((((a & 0x00FEFEFEu) >> 1) + ((b & 0x00FEFEFEu) >> 1)) & 0x00FFFFFFu); }
/* Pattern test (2026-10-15, replaces the old horizontal-only rule and the 3x3 blur of 'strong', which smeared real texture and the HUD):
   a pixel is part of a dither pattern only when the pattern is confirmed in two dimensions:
   - checkerboard: the four orthogonal neighbours agree with each other and differ from the pixel, and at least 3 of the 4 diagonal neighbours equal the pixel;
   - vertical stripes (columns alternate): left and right agree, differ from the pixel, the pixel above AND below equal the pixel (the column goes on) and the column two further to a side equals it again (a lone 1-pixel line stays sharp);
   - horizontal stripes: the same turned by 90 degrees.
   The pixel becomes the mix of itself and the neighbour colour (for a 2-colour pattern that is exactly the colour the TV blended). Both pixel kinds of the pattern are found, so the whole area ends up flat.
   tol = colour tolerance for 'equal' (light 6 = only exact-ish patterns, strong 20 = also the sloppy dithers of the ground). */
#define LK_DD_UI_PURPLE 0x00442288u
static inline int lk_dd_ui(uint32_t c) { c &= 0x00FFFFFFu; return c == LK_DD_UI_PURPLE || c == 0x00EEEEEEu; }
/* UI protection (2026-10-15, user: the filter ate the letters of the pause menu and of speech boxes): a pixel is skipped when the window purple $442288 or the text white $EEEEEE is within 3 pixels
   (window bodies, their text, the HUD); flat floors and sprites are not affected by that */
static uint8_t *lk_dd_near; static int lk_dd_nearcap;   /* per pixel: 1 when a UI colour lies within 3 px (computed once per frame, separable) */
static void lk_dd_build_near(const uint32_t *src, int sw) {
    size_t n = (size_t)sw * LK_SRC_H;
    if (lk_dd_nearcap < (int)n) { free(lk_dd_near); lk_dd_near = (uint8_t *)malloc(n * 2); lk_dd_nearcap = lk_dd_near ? (int)n : 0; }
    if (!lk_dd_near) return;
    uint8_t *row = lk_dd_near, *tmp = lk_dd_near + n;
    for (int y = 0; y < LK_SRC_H; y++) {   /* horizontal dilation by 3 */
        const uint32_t *r = src + (size_t)y * sw; uint8_t *o = tmp + (size_t)y * sw; int last = -100;
        for (int x = 0; x < sw; x++) { if (lk_dd_ui(r[x])) last = x; o[x] = (x - last) <= 3 ? 1 : 0; }
        last = 1000000; for (int x = sw - 1; x >= 0; x--) { if (lk_dd_ui(r[x])) last = x; if (last - x <= 3) o[x] = 1; }
    }
    for (int x = 0; x < sw; x++) {   /* any set pixel of tmp within +-3 rows */
        int cnt = 0;
        for (int y = 0; y < LK_SRC_H + 3; y++) {
            if (y < LK_SRC_H && tmp[(size_t)y * sw + x]) cnt++;
            if (y - 7 >= 0 && tmp[(size_t)(y - 7) * sw + x]) cnt--;
            { int yy = y - 3; if (yy >= 0 && yy < LK_SRC_H) row[(size_t)yy * sw + x] = cnt > 0; }
        }
    }
}
static inline int lk_dd_uinear(const uint32_t *src, int sw, int x, int y) { (void)src; return lk_dd_near ? lk_dd_near[(size_t)y * sw + x] : 0; }
static void lk_dedither_tol_rows(const uint32_t *src, uint32_t *dst, int sw, int tol, int y0, int y1) {
    for (int y = y0 < LK_DD_SKIP_TOP ? LK_DD_SKIP_TOP : y0; y < (y1 > LK_SRC_H - 1 ? LK_SRC_H - 1 : y1); y++) {
        for (int x = 1; x < sw - 1; x++) {
            const uint32_t *r = src + (size_t)y * sw + x, c = r[0];
            uint32_t W = r[-1], E = r[1], N = r[-sw], S = r[sw];
            if (lk_dd_nearT(c, W, tol) && lk_dd_nearT(c, E, tol) && lk_dd_nearT(c, N, tol) && lk_dd_nearT(c, S, tol)) continue;   /* flat */
            if (lk_dd_uinear(src, sw, x, y)) continue;
            if (lk_dd_nearT(W, E, tol) && lk_dd_nearT(N, S, tol) && lk_dd_nearT(W, N, tol) && !lk_dd_nearT(c, W, tol)) {
                int d = lk_dd_nearT(r[-sw - 1], c, tol) + lk_dd_nearT(r[-sw + 1], c, tol) + lk_dd_nearT(r[sw - 1], c, tol) + lk_dd_nearT(r[sw + 1], c, tol);
                if (d >= 3) { dst[(size_t)y * sw + x] = lk_dd_mix2(c, lk_dd_mix2(W, N)); continue; }
            }
            if (lk_dd_nearT(W, E, tol) && !lk_dd_nearT(c, W, tol) && lk_dd_nearT(N, c, tol) && lk_dd_nearT(S, c, tol) && ((x >= 2 && lk_dd_nearT(r[-2], c, tol)) || (x + 2 < sw && lk_dd_nearT(r[2], c, tol)))) { dst[(size_t)y * sw + x] = lk_dd_mix2(c, lk_dd_mix2(W, E)); continue; }
            if (y + 2 < LK_SRC_H && lk_dd_nearT(N, S, tol) && !lk_dd_nearT(c, N, tol) && lk_dd_nearT(W, c, tol) && lk_dd_nearT(E, c, tol) && (lk_dd_nearT(r[-2 * sw], c, tol) || lk_dd_nearT(r[2 * sw], c, tol))) { dst[(size_t)y * sw + x] = lk_dd_mix2(c, lk_dd_mix2(N, S)); continue; }
        }
    }
}
static void lk_dedither_tol(const uint32_t *src, uint32_t *dst, int sw, int tol) { memcpy(dst, src, (size_t)sw * LK_SRC_H * 4); lk_dedither_tol_rows(src, dst, sw, tol, 0, LK_SRC_H); }
/* smoothing of dither-like TEXTURE (the floors of Mercator / Massan: two or three close brown / grey tones scattered pixel by pixel): 3x3 kernel 1 2 1 / 2 4 2 / 1 2 1, but only where the whole 3x3 window stays within `range`
   of the centre in every channel (outlines, sprites against dark edges and text never qualify), at least 3 of the 8 neighbours differ from the centre by more than the tolerance and at least 2 are equal to it (not an isolated dot).
   UI protection (2026-10-15, user: the filter ate the letters of the pause menu and of speech boxes): a pixel is skipped when the window purple $442288 or the text white $EEEEEE is anywhere within 3 pixels
   (window bodies, their text, the HUD) - flat floors are not affected by that. */
static void lk_dedither_smooth_rows(const uint32_t *src, uint32_t *dst, int sw, int range, int ncl, int hmode, int y0, int y1) {
    /* masked: only neighbours within `range` of the centre take part (a pixel next to a sprite outline is smoothed from its own texture, so there is no unsmoothed ring around Nigel on the carpet);
       at least 4 neighbours must qualify, 2 of them differ from the centre by more than the tolerance and 1 equals it (pure dots, lines and outlines have no such neighbourhood).
       Dither test: of the pixels of the 5x5 window that are within `range` of the centre (>= 12 of them) at most `ncl` colour clusters (tolerance 6) cover >= 90 % - a floor / carpet / wall made of 2..3 tones,
       but not the shading of a sprite or a picture with many colours. */
    for (int y = y0 < LK_DD_SKIP_TOP ? LK_DD_SKIP_TOP : y0; y < (y1 > LK_SRC_H - 3 ? LK_SRC_H - 3 : y1); y++) for (int x = 3; x < sw - 3; x++) {
        const uint32_t c = src[(size_t)y * sw + x]; int diff = 0, same = 0, in = 0;
        uint32_t r = 0, g = 0, b = 0, wsum = 0;
        { const uint32_t *q = src + (size_t)y * sw + x; if (lk_dd_eq(c, q[-1]) && lk_dd_eq(c, q[1]) && lk_dd_eq(c, q[-sw]) && lk_dd_eq(c, q[sw])) continue; }   /* flat: nothing to do (most of the picture) */
        for (int dy = -1; dy <= 1; dy++) for (int dx = -1; dx <= 1; dx++) {
            uint32_t n = src[(size_t)(y + dy) * sw + x + dx], w = (dx ? 1u : 2u) * (dy ? 1u : 2u);
            if (dx || dy) {
                if (!lk_dd_nearT(n, c, range)) continue;
                in++; if (lk_dd_eq(n, c)) same++; else diff++;
            } else w = 4;
            r += ((n >> 16) & 255) * w; g += ((n >> 8) & 255) * w; b += (n & 255) * w; wsum += w;
        }
        if (in < 4 || diff < 2 || same < 1) continue;
        {   /* 5x5 cluster test: clusters by exact colour (fast), then only the cluster colours are range-checked against the centre */
            uint32_t rep[25]; int cnt[25], ncluster = 0, tot = 0, k, m;
            for (int dy = -2; dy <= 2; dy++) {
                int yy = y + dy; if (yy < 0 || yy >= LK_SRC_H) continue;
                const uint32_t *row = src + (size_t)yy * sw + x;
                for (int dx = -2; dx <= 2; dx++) {
                    uint32_t n; if (x + dx < 0 || x + dx >= sw) continue;
                    n = row[dx];
                    for (k = 0; k < ncluster; k++) if (lk_dd_eq(n, rep[k])) { cnt[k]++; break; }
                    if (k == ncluster) { rep[ncluster] = n; cnt[ncluster++] = 1; if (ncluster > 9) goto nodither; }
                }
            }
            { int inr = 0, cov; int cc[25];
              for (k = 0; k < ncluster; k++) if (lk_dd_nearT(rep[k], c, range)) { cc[inr++] = cnt[k]; tot += cnt[k]; }
              if (tot < 12) continue;
              for (k = 0; k < inr; k++) for (m = k + 1; m < inr; m++) if (cc[m] > cc[k]) { int t = cc[k]; cc[k] = cc[m]; cc[m] = t; }
              cov = 0; for (k = 0; k < inr && k < ncl; k++) cov += cc[k];
              if (cov * 10 < tot * 9) continue; }
            goto okdither;
            nodither: continue;
            okdither:;
        }
        if (lk_dd_uinear(src, sw, x, y)) continue;
        if (hmode) {   /* 'Blend' (CRT-like): the beam smears the pixels along the line, so the pattern is blended horizontally only (5 taps 1 4 6 4 1, in-range pixels only) and a trace of it stays */
            static const unsigned hw[5] = { 1, 4, 6, 4, 1 };
            r = g = b = wsum = 0;
            for (int dx = -2; dx <= 2; dx++) {
                uint32_t n = src[(size_t)y * sw + x + dx];
                if (dx && !lk_dd_nearT(n, c, range)) continue;
                r += ((n >> 16) & 255) * hw[dx + 2]; g += ((n >> 8) & 255) * hw[dx + 2]; b += (n & 255) * hw[dx + 2]; wsum += hw[dx + 2];
            }
        }
        dst[(size_t)y * sw + x] = 0xFF000000u | ((r / wsum) << 16) | ((g / wsum) << 8) | (b / wsum);
    }
}
/* Edge-preserving smoothing ('Smooth' mode, 2026-10-16, user: Light / Strong / Blend are still not good): 5x5 weighted mean where the weight is (spatial gaussian) x (colour similarity): neighbours within `range`
   (max channel difference) of the centre count, the more alike the more, brighter sparkles, outlines and text are far away in colour and keep their own value. A dither noise of 2..3 close tones (water, grass, floors)
   becomes a smooth gradient, no clusters / patterns have to be recognised. `gate` = minimum number of the 8 neighbours that differ from the centre (0 = every pixel, higher = only noisy places, sprite shading stays sharper). */
static void lk_dedither_bil_rows(const uint32_t *src, uint32_t *dst, int sw, int range, int gate, int y0, int y1) {
    static const int sp[3][3] = { { 16, 11, 8 }, { 11, 8, 4 }, { 8, 4, 3 } };   /* [|dy|][|dx|]: gaussian in the distance */
    for (int y = y0 < LK_DD_SKIP_TOP ? LK_DD_SKIP_TOP : y0; y < (y1 > LK_SRC_H - 2 ? LK_SRC_H - 2 : y1); y++) for (int x = 2; x < sw - 2; x++) {
        const uint32_t c = src[(size_t)y * sw + x]; const int cr = (c >> 16) & 255, cg = (c >> 8) & 255, cb = c & 255;
        unsigned r = 0, g = 0, b = 0, wsum = 0; int diff = 0;
        { const uint32_t *q = src + (size_t)y * sw + x; if (lk_dd_eq(c, q[-1]) && lk_dd_eq(c, q[1]) && lk_dd_eq(c, q[-sw]) && lk_dd_eq(c, q[sw]) && lk_dd_eq(c, q[-sw - 1]) && lk_dd_eq(c, q[-sw + 1]) && lk_dd_eq(c, q[sw - 1]) && lk_dd_eq(c, q[sw + 1])) continue; }   /* flat 3x3: nothing to do (fast path) */
        if (lk_dd_uinear(src, sw, x, y)) continue;
        for (int dy = -2; dy <= 2; dy++) for (int dx = -2; dx <= 2; dx++) {
            const uint32_t n = src[(size_t)(y + dy) * sw + x + dx]; const int nr = (n >> 16) & 255, ng = (n >> 8) & 255, nb = n & 255;
            int d = abs(nr - cr), e = abs(ng - cg), f = abs(nb - cb), w;
            if (e > d) d = e; if (f > d) d = f;
            if (d >= range) continue;
            if ((dx | dy) && d && dy >= -1 && dy <= 1 && dx >= -1 && dx <= 1) diff++;
            w = sp[abs(dy)][abs(dx)] * ((range - d) * 16 / range);
            r += (unsigned)nr * (unsigned)w; g += (unsigned)ng * (unsigned)w; b += (unsigned)nb * (unsigned)w; wsum += (unsigned)w;
        }
        if (diff < gate || !wsum) continue;
        dst[(size_t)y * sw + x] = 0xFF000000u | ((r / wsum) << 16) | ((g / wsum) << 8) | (b / wsum);
    }
}
/* optional parallel runner (tools/patch_display.py sets it): calls fn(ctx, y0, y1) for bands of source rows on several threads */
static void (*lk_dd_par)(void (*fn)(void *, int, int), void *ctx);
typedef struct { const uint32_t *src; uint32_t *dst; int sw, tol, range, ncl, hmode, phase; } lk_dd_ctx;
static void lk_dd_band(void *p, int y0, int y1) { lk_dd_ctx *c = (lk_dd_ctx *)p; if (c->phase == 0) lk_dedither_tol_rows(c->src, c->dst, c->sw, c->tol, y0, y1); else if (c->phase == 1) lk_dedither_smooth_rows(c->src, c->dst, c->sw, c->range, c->ncl, c->hmode, y0, y1); else lk_dedither_bil_rows(c->src, c->dst, c->sw, c->range, 0, y0, y1); }
static void lk_dd_run(lk_dd_ctx *c) { if (lk_dd_par) lk_dd_par(lk_dd_band, c); else lk_dd_band(c, 0, LK_SRC_H); }
static void lk_dedither_both(const uint32_t *src, uint32_t *dst, int sw, int tol, int range, int ncl, int hmode) {
    static uint32_t *tmp; static int cap;
    lk_dd_ctx c = { src, dst, sw, tol, range, ncl, hmode, 0 };
    static uint32_t *last_in, *last_out; static int last_cap, last_key = -1, last_sw;   /* still pictures (menus, dialogues, title): the result of the previous call is reused */
    const size_t bytes = (size_t)sw * LK_SRC_H * 4; const int key = tol * 1000003 + range * 1009 + ncl * 7 + hmode;
    if (last_cap >= (int)bytes && last_key == key && last_sw == sw && last_in && !memcmp(last_in, src, bytes)) { memcpy(dst, last_out, bytes); return; }
    lk_dd_build_near(src, sw);
    memcpy(dst, src, (size_t)sw * LK_SRC_H * 4);
    if (tol > 0) lk_dd_run(&c);
    if (cap < sw * LK_SRC_H) { free(tmp); tmp = (uint32_t *)malloc((size_t)sw * LK_SRC_H * 4); cap = tmp ? sw * LK_SRC_H : 0; }
    if (!tmp) return;
    memcpy(tmp, dst, (size_t)sw * LK_SRC_H * 4);
    c.src = tmp; c.phase = 1; lk_dd_run(&c);
    if (last_cap < (int)bytes) { free(last_in); free(last_out); last_in = (uint32_t *)malloc(bytes); last_out = (uint32_t *)malloc(bytes); last_cap = (last_in && last_out) ? (int)bytes : 0; }
    if (last_cap >= (int)bytes) { memcpy(last_in, src, bytes); memcpy(last_out, dst, bytes); last_key = key; last_sw = sw; }
}
/* The three user-visible strengths (2026-10-16): the edge-preserving smoothing above with colour range 90 / 120 / 150 (the older pattern detectors lk_dedither_both stay in the file for the test tool, the game no longer uses them).
   Same plumbing as lk_dedither_both: UI guard mask, bands on several threads, an unchanged picture (menus, dialogues) reuses the previous result. */
static void lk_dedither_bil(const uint32_t *src, uint32_t *dst, int sw, int range) {
    static uint32_t *last_in, *last_out; static int last_cap, last_key = -1, last_sw;
    lk_dd_ctx c = { src, dst, sw, 0, range, 0, 0, 2 };
    const size_t bytes = (size_t)sw * LK_SRC_H * 4; const int key = 5000 + range;
    if (last_cap >= (int)bytes && last_key == key && last_sw == sw && last_in && !memcmp(last_in, src, bytes)) { memcpy(dst, last_out, bytes); return; }
    lk_dd_build_near(src, sw);
    memcpy(dst, src, bytes);
    lk_dd_run(&c);
    if (last_cap < (int)bytes) { free(last_in); free(last_out); last_in = (uint32_t *)malloc(bytes); last_out = (uint32_t *)malloc(bytes); last_cap = (last_in && last_out) ? (int)bytes : 0; }
    if (last_cap >= (int)bytes) { memcpy(last_in, src, bytes); memcpy(last_out, dst, bytes); last_key = key; last_sw = sw; }
}
static void lk_dedither(const uint32_t *src, uint32_t *dst, int sw) { lk_dedither_bil(src, dst, sw, 90); }          /* Light */
static void lk_dedither_strong(const uint32_t *src, uint32_t *dst, int sw) { lk_dedither_bil(src, dst, sw, 120); }   /* Medium (mode 2) */
static void lk_dedither_blend(const uint32_t *src, uint32_t *dst, int sw) { lk_dedither_bil(src, dst, sw, 150); }    /* Strong (mode 3) */

/* ---- 5x7 font for the on-screen hint (rows of 5 bits, top row first) ---- */
static const uint8_t *lk_glyph(char c) {
    static const uint8_t blank[7] = { 0, 0, 0, 0, 0, 0, 0 };
    static const uint8_t digits[10][7] = {
        {14,17,19,21,25,17,14}, {4,12,4,4,4,4,14}, {14,17,1,2,4,8,31}, {30,1,1,14,1,1,30}, {2,6,10,18,31,2,2},
        {31,16,30,1,1,17,14}, {6,8,16,30,17,17,14}, {31,1,2,4,8,8,8}, {14,17,17,14,17,17,14}, {14,17,17,15,1,2,12} };
    static const uint8_t letters[26][7] = {
        {14,17,17,31,17,17,17}, {30,17,17,30,17,17,30}, {14,17,16,16,16,17,14}, {30,17,17,17,17,17,30}, {31,16,16,30,16,16,31},
        {31,16,16,30,16,16,16}, {14,17,16,23,17,17,15}, {17,17,17,31,17,17,17}, {14,4,4,4,4,4,14}, {7,2,2,2,2,18,12},
        {17,18,20,24,20,18,17}, {16,16,16,16,16,16,31}, {17,27,21,21,17,17,17}, {17,25,21,19,17,17,17}, {14,17,17,17,17,17,14},
        {30,17,17,30,16,16,16}, {14,17,17,17,21,18,13}, {30,17,17,30,20,18,17}, {15,16,16,14,1,1,30}, {31,4,4,4,4,4,4},
        {17,17,17,17,17,17,14}, {17,17,17,17,17,10,4}, {17,17,17,21,21,21,10}, {17,17,10,4,10,17,17}, {17,17,10,4,4,4,4},
        {31,1,2,4,8,16,31} };
    static const uint8_t colon[7] = { 0, 4, 4, 0, 4, 4, 0 }, dash[7] = { 0, 0, 0, 31, 0, 0, 0 }, slash[7] = { 1, 1, 2, 4, 8, 16, 16 }, dot[7] = { 0, 0, 0, 0, 0, 12, 12 };
    if (c >= '0' && c <= '9') return digits[c - '0'];
    if (c >= 'A' && c <= 'Z') return letters[c - 'A'];
    if (c >= 'a' && c <= 'z') return letters[c - 'a'];
    if (c == ':') return colon;
    if (c == '-') return dash;
    if (c == '/') return slash;
    if (c == '.') return dot;
    { static const uint8_t au[7] = { 10, 0, 14, 17, 31, 17, 17 }, ou[7] = { 10, 0, 14, 17, 17, 17, 14 }, uu[7] = { 10, 0, 17, 17, 17, 17, 14 }, sz[7] = { 12, 18, 18, 22, 17, 17, 22 };   /* ä Ä / ö Ö / ü Ü / ß (UI bytes $80..$86, tools/langbuild.py UI_BYTES); the hint font has capitals only */
      unsigned char u = (unsigned char)c; if (u == 0x80 || u == 0x84) return au; if (u == 0x81 || u == 0x85) return ou; if (u == 0x82 || u == 0x86) return uu; if (u == 0x83) return sz; }
    return blank;
}
/* LK_DISPLAY_END */
