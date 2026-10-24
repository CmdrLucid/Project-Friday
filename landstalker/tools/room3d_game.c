/* ---- LK_R3D v1: the room as a 3D scene (tools/patch_room3d.py inserts this file into src/platform_sdl.c; design + proof: tools/room3d_proto.c, docs/RENDERER_IDEAS.md) ----
 *
 * Options > Video > 3D Room (Off / On).  The own renderer's room data is turned into a scene: the height map is a height field (floors, house columns, cliffs), its surfaces take their
 * colours by PROJECTIVE texturing from the original picture (image position U = wx - wy + 1184, V = (wx + wy) / 2 - z, the layer maps are sampled live: palette fades and animated tiles work),
 * houses get fitted gable roofs, what the field does not carry (trees, fences, the statue) becomes upright one pixel strips = cards, figures (Nigel, NPCs, enemies: the sprite pixels of the
 * frame) become billboards at their ground point.  The camera turns with the right stick (R3 = back to the original view); from the original camera the picture is the original one.
 * The scene is built on a worker thread when a room appears (until then the normal picture is shown) from a snapshot of the layer maps; roof fits are cached in ~/.landstalker_r3d. */
#include <math.h>
#include <sys/stat.h>
#include <sys/types.h>
extern int lk_wide_e; extern long lk_hd_gen, lk_hd_dstamp[224]; extern int16_t lk_hd_depth[]; extern uint8_t lk_hd_spr[]; extern uint32_t lk_hd_sprc[];
typedef struct { const uint32_t (*pa)[304]; const uint32_t (*pb)[304]; const uint8_t *tiles; const uint32_t *pix; int u0, v0, room; } lk_o3d_src_t;
extern int lk_o3d_get(lk_o3d_src_t *o); extern int lk_o3d_hm(int x, int y); extern uint32_t lk_o3d_hash(void);
extern int lk_hd_look3d;
extern volatile int lk_rs_x, lk_rs_y, lk_rs_click;   /* right stick (input.c, tools/patch_room3d.py) */

#define R3_TW 2432
#define R3_TH 1216
#define R3_NQ 24000
typedef struct { double X0, X1, Y0, Y1, z0, H, o; int axis; } r3_roof_t;
typedef struct { float wx[4], wy[4], wz[4]; uint8_t mode, dark; } r3_quad_t;       /* mode 0 ground (layer B only), 1 composite, 2 roof */
typedef struct { int U, y, n; float bx, by, bz; } r3_strip_t;
typedef struct {
    uint32_t hash; int nq, ns, nroofs; r3_quad_t *q; r3_strip_t *st; r3_roof_t roofs[64];
    float *hw; uint8_t *cov, *hb;           /* hit position (3 floats) / covered / box flag per picture pixel of the original view */
    uint8_t tiles[0x12000]; uint32_t pa[152][304], pb[152][304], pix[64];   /* the snapshot the scene was built from */
    int hm[74][74]; double zc[74][74]; uint8_t boxc[74][74];
} r3_scene_t;
static r3_scene_t *r3_active, *r3_work; static SDL_Thread *r3_thread; static volatile int r3_busy, r3_done; static uint32_t r3_req_hash; static int r3_on_cache = -1;
static double r3_yaw, r3_pitch, r3_dyaw, r3_dpitch; static int r3_fixed; static uint64_t r3_t[5]; static double r3_acc[4]; static int r3_nacc;
static uint32_t *r3_img, *r3_zbuf_dummy; static float *r3_zb; static int r3_iw, r3_ih;

int lk_r3d_on(void) {
    if (r3_on_cache < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_R3D"); char path[512]; FILE *f; int v = 0; snprintf(path, sizeof path, "%s/.landstalker_room3d", h ? h : "."); f = fopen(path, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); r3_on_cache = v < 0 ? 0 : v > 2 ? 2 : v; }   /* 0 Off, 1 On = 2 x 2 pixels per game pixel, 2 = 1 x 1 (fast) */
    return r3_on_cache;
}
int lk_r3d_get(void) { return lk_r3d_on(); }
void lk_r3d_set(int v) { const char *h = getenv("HOME"); char path[512]; FILE *f; r3_on_cache = v < 0 ? 0 : v > 2 ? 2 : v; snprintf(path, sizeof path, "%s/.landstalker_room3d", h ? h : "."); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", r3_on_cache); fclose(f); } }

/* ---- sampling the layer maps (same as the own renderer's lk_o_fetch) ---- */
static inline int r3_fetch(const uint32_t (*pl)[304], const uint8_t *tiles, int U, int V, int *pal, int *prio) {
    int tc = U >> 3, tr = V >> 3, ix = U & 7, iy = V & 7, w, t, b; uint32_t c;
    if (U < 0 || V < 0 || tc >= 304 || tr >= 152) return 0;
    c = pl[tr][tc]; if (!(c & 0x10000)) return 0;
    w = (int)(c & 0xFFFF); if (w & 0x800) ix = 7 - ix; if (w & 0x1000) iy = 7 - iy;
    t = w & 0x7FF; if (t * 32 + 31 >= 0x12000) return 0;
    b = tiles[t * 32 + iy * 4 + ix / 2]; *pal = (w >> 13) & 3; *prio = (w >> 15) & 1;
    return (ix % 2 == 0) ? (b >> 4) : (b & 15);
}
/* mode 0 = ground (layer B only), 1 = composite (priority order A high, B high, A low, B low), 3 = layer A only; returns an opaque ARGB colour or 0 */
static inline uint32_t r3_samp(const uint32_t (*pa)[304], const uint32_t (*pb)[304], const uint8_t *tiles, const uint32_t *pix, int mode, int U, int V) {
    int pal_a = 0, pr_a = 0, pal_b = 0, pr_b = 0, ia = 0, ib = 0, pick;
    if (mode != 0) ia = r3_fetch(pa, tiles, U, V, &pal_a, &pr_a);
    if (mode != 3) ib = r3_fetch(pb, tiles, U, V, &pal_b, &pr_b);
    if (ia && pr_a) pick = (pal_a << 4) | ia; else if (ib && pr_b) pick = (pal_b << 4) | ib; else if (ia) pick = (pal_a << 4) | ia; else if (ib) pick = (pal_b << 4) | ib; else return 0;
    return (pix[pick & 0x3F] & 0xFFFFFFu) | 0xFF000000u;
}

/* ---- scene building (worker thread, works on the snapshot inside the scene) ---- */
typedef void (*r3_cb_t)(int px, int py, double wx, double wy, double z, void *ud);
static void r3_rast(const double P[3][3], int step, r3_cb_t f, void *ud) {
    double U[3], V[3]; int j, px, py;
    for (j = 0; j < 3; j++) { U[j] = P[j][0] - P[j][1] + 1184; V[j] = (P[j][0] + P[j][1]) / 2 - P[j][2]; }
    { double mnx = fmin(U[0], fmin(U[1], U[2])), mxx = fmax(U[0], fmax(U[1], U[2])), mny = fmin(V[0], fmin(V[1], V[2])), mxy = fmax(V[0], fmax(V[1], V[2]));
      double den = (V[1] - V[2]) * (U[0] - U[2]) + (U[2] - U[1]) * (V[0] - V[2]); int x0 = (int)floor(mnx), y0 = (int)floor(mny);
      if (fabs(den) < 1e-9) return;
      if (step > 1) { x0 -= ((x0 % step) + step) % step; y0 -= ((y0 % step) + step) % step; }
      for (py = y0; py <= (int)ceil(mxy); py += step) for (px = x0; px <= (int)ceil(mxx); px += step) {
          double qx = px + 0.5, qy = py + 0.5, l1 = ((V[1] - V[2]) * (qx - U[2]) + (U[2] - U[1]) * (qy - V[2])) / den, l2 = ((V[2] - V[0]) * (qx - U[2]) + (U[0] - U[2]) * (qy - V[2])) / den, l3 = 1 - l1 - l2;
          if (px < 0 || py < 0 || px >= R3_TW || py >= R3_TH || l1 < -1e-6 || l2 < -1e-6 || l3 < -1e-6) continue;
          f(px, py, l1 * P[0][0] + l2 * P[1][0] + l3 * P[2][0], l1 * P[0][1] + l2 * P[1][1] + l3 * P[2][1], l1 * P[0][2] + l2 * P[1][2] + l3 * P[2][2], ud);
      }
    }
}
typedef struct { r3_scene_t *sc; int box; uint8_t *th, *rmask; int s_in, s_out; } r3_ctx_t;
static void r3_hit_cb(int px, int py, double wx, double wy, double z, void *ud) {
    r3_ctx_t *c = (r3_ctx_t *)ud; size_t i = (size_t)py * R3_TW + px; float *h = c->sc->hw + i * 3;
    if (!c->sc->cov[i] || wx + wy + z > h[0] + h[1] + h[2]) { h[0] = (float)wx; h[1] = (float)wy; h[2] = (float)z; c->sc->cov[i] = 1; c->sc->hb[i] = (uint8_t)c->box; }
}
static void r3_mask_cb(int px, int py, double wx, double wy, double z, void *ud) {
    r3_ctx_t *c = (r3_ctx_t *)ud; size_t i = (size_t)py * R3_TW + px; (void)wx; (void)wy; (void)z;
    if (!c->rmask[i]) { c->rmask[i] = 1; if (c->th[i]) c->s_in++; else c->s_out++; }
}
static int r3_roof_tris(const r3_roof_t *r, double T[6][3][3]) {
    double xm = (r->X0 + r->X1) / 2, ym = (r->Y0 + r->Y1) / 2, z = r->z0, zr = r->z0 + r->H; int n = 0;
#define R3TRI(a0, a1, a2, b0, b1, b2, c0, c1, c2) do { T[n][0][0] = a0; T[n][0][1] = a1; T[n][0][2] = a2; T[n][1][0] = b0; T[n][1][1] = b1; T[n][1][2] = b2; T[n][2][0] = c0; T[n][2][1] = c1; T[n][2][2] = c2; n++; } while (0)
    if (r->axis == 0) {
        R3TRI(r->X0, r->Y0, z, r->X1, r->Y0, z, r->X1, ym, zr); R3TRI(r->X0, r->Y0, z, r->X1, ym, zr, r->X0, ym, zr);
        R3TRI(r->X0, ym, zr, r->X1, ym, zr, r->X1, r->Y1, z); R3TRI(r->X0, ym, zr, r->X1, r->Y1, z, r->X0, r->Y1, z);
        R3TRI(r->X1, r->Y0, z, r->X1, r->Y1, z, r->X1, ym, zr); R3TRI(r->X0, r->Y0, z, r->X0, r->Y1, z, r->X0, ym, zr);
    } else {
        R3TRI(r->X0, r->Y0, z, r->X0, r->Y1, z, xm, r->Y1, zr); R3TRI(r->X0, r->Y0, z, xm, r->Y1, zr, xm, r->Y0, zr);
        R3TRI(xm, r->Y0, zr, xm, r->Y1, zr, r->X1, r->Y1, z); R3TRI(xm, r->Y0, zr, r->X1, r->Y1, z, r->X1, r->Y0, z);
        R3TRI(r->X0, r->Y1, z, r->X1, r->Y1, z, xm, r->Y1, zr); R3TRI(r->X0, r->Y0, z, r->X1, r->Y0, z, xm, r->Y0, zr);
    }
    return n;
}
static int r3_fit_roof(r3_ctx_t *c, int x0, int x1, int y0, int y1, double z0, r3_roof_t *out, int *have_out) {   /* best gable roof of a footprint: ridge axis, height, overhang; scores thatch pixels (step 2 sampling) */
    double bs = -1e18; int axis, hi, oi, have = 0;
    for (axis = 0; axis < 2; axis++) for (hi = 1; hi <= 5; hi++) for (oi = 0; oi <= 2; oi++) {
        r3_roof_t r; double T[6][3][3], mnU = 1e9, mxU = -1e9, mnV = 1e9, mxV = -1e9, score; int t, nt, j, bx0, bx1, by0, by1, px, py, outy = 0;
        r.o = 8.0 * oi; r.H = 8.0 * hi; r.axis = axis; r.z0 = z0; r.X0 = 16.0 * x0 - r.o; r.X1 = 16.0 * (x1 + 1) + r.o; r.Y0 = 16.0 * y0 - r.o; r.Y1 = 16.0 * (y1 + 1) + r.o;
        nt = r3_roof_tris(&r, T); c->s_in = c->s_out = 0;
        for (t = 0; t < nt; t++) r3_rast(T[t], 2, r3_mask_cb, c);
        for (t = 0; t < nt; t++) for (j = 0; j < 3; j++) { double U = T[t][j][0] - T[t][j][1] + 1184, V = (T[t][j][0] + T[t][j][1]) / 2 - T[t][j][2]; if (U < mnU) mnU = U; if (U > mxU) mxU = U; if (V < mnV) mnV = V; if (V > mxV) mxV = V; }
        bx0 = (int)mnU - 16; bx1 = (int)mxU + 16; by0 = (int)mnV - 16; by1 = (int)mxV + 16; if (bx0 < 0) bx0 = 0; if (by0 < 0) by0 = 0; if (bx1 >= R3_TW) bx1 = R3_TW - 1; if (by1 >= R3_TH) by1 = R3_TH - 1;
        for (py = by0; py <= by1; py += 2) for (px = bx0; px <= bx1; px += 2) if (!c->rmask[(size_t)py * R3_TW + px] && c->th[(size_t)py * R3_TW + px]) outy++;
        for (py = by0; py <= by1; py++) memset(c->rmask + (size_t)py * R3_TW + bx0, 0, (size_t)(bx1 - bx0 + 1));
        score = c->s_in - 1.5 * c->s_out - 0.6 * outy;
        if (score > bs) { bs = score; *out = r; have = c->s_in; }
    }
    *have_out = have; return (int)bs;
}
static void r3_find_roofs(r3_scene_t *sc, r3_ctx_t *c) {
    static uint8_t rem[74][74]; int x, y; char path[600]; FILE *cf; const char *home = getenv("HOME");
    snprintf(path, sizeof path, "%s/.landstalker_r3d/roofs_%08x.txt", home ? home : ".", sc->hash);
    cf = fopen(path, "r");
    if (cf) { r3_roof_t r; sc->nroofs = 0; while (sc->nroofs < 64 && fscanf(cf, "%lf %lf %lf %lf %lf %lf %lf %d", &r.X0, &r.X1, &r.Y0, &r.Y1, &r.z0, &r.H, &r.o, &r.axis) == 8) sc->roofs[sc->nroofs++] = r; fclose(cf); return; }
    sc->nroofs = 0;
    c->th = (uint8_t *)calloc((size_t)R3_TW * R3_TH, 1); c->rmask = (uint8_t *)calloc((size_t)R3_TW * R3_TH, 1);
    if (!c->th || !c->rmask) { free(c->th); free(c->rmask); c->th = c->rmask = NULL; return; }
    for (y = 0; y < R3_TH; y++) for (x = 0; x < R3_TW; x++) {   /* thatch: mustard yellow / brown dither / white highlights of layer A */
        uint32_t q = r3_samp(sc->pa, sc->pb, sc->tiles, sc->pix, 3, x, y); int r = (q >> 16) & 255, g = (q >> 8) & 255, b = q & 255;
        c->th[(size_t)y * R3_TW + x] = (uint8_t)(q && ((b <= 40 && r >= 120 && g >= 90 && r > g) || (r >= 190 && g >= 190 && b >= 190)));
    }
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) rem[y][x] = (uint8_t)(sc->boxc[y][x] && sc->zc[y][x] >= 32);
    for (;;) {
        int bx0 = 0, bx1 = 0, by0 = 0, by1 = 0, bsc = 0, bth = 0, found = 0, x0, x1, y0, y1; r3_roof_t br;
        if (sc->nroofs >= 64) break;
        for (y0 = 0; y0 < 74; y0++) for (x0 = 0; x0 < 74; x0++) {
            if (!rem[y0][x0]) continue;
            for (y1 = y0 + 1; y1 < y0 + 8 && y1 < 74; y1++) for (x1 = x0 + 1; x1 < x0 + 8 && x1 < 74; x1++) {
                int cx, cy, in = 0, tot = (x1 - x0 + 1) * (y1 - y0 + 1), sco, th; double z0 = sc->zc[y0][x0]; r3_roof_t r;
                for (cy = y0; cy <= y1; cy++) for (cx = x0; cx <= x1; cx++) if (rem[cy][cx] && sc->zc[cy][cx] == z0) in++;
                if (in * 100 < tot * 85 || !rem[y1][x1]) continue;
                sco = r3_fit_roof(c, x0, x1, y0, y1, z0, &r, &th);
                if (th >= 40 && sco > bsc) { bsc = sco; bth = th; br = r; bx0 = x0; bx1 = x1; by0 = y0; by1 = y1; found = 1; }
            }
        }
        if (!found || bsc < 30) break;
        sc->roofs[sc->nroofs++] = br; (void)bth;
        for (y = by0; y <= by1; y++) for (x = bx0; x <= bx1; x++) rem[y][x] = 0;
    }
    free(c->th); free(c->rmask); c->th = c->rmask = NULL;
    { char dir[600]; snprintf(dir, sizeof dir, "%s/.landstalker_r3d", home ? home : "."); mkdir(dir, 0777); }
    cf = fopen(path, "w");
    if (cf) { int r; for (r = 0; r < sc->nroofs; r++) fprintf(cf, "%.3f %.3f %.3f %.3f %.3f %.3f %.3f %d\n", sc->roofs[r].X0, sc->roofs[r].X1, sc->roofs[r].Y0, sc->roofs[r].Y1, sc->roofs[r].z0, sc->roofs[r].H, sc->roofs[r].o, sc->roofs[r].axis); fclose(cf); }
}
static void r3_addq(r3_scene_t *sc, int mode, int dark, double x0, double y0, double z0, double x1, double y1, double z1, double x2, double y2, double z2, double x3, double y3, double z3) {
    r3_quad_t *q; if (sc->nq >= R3_NQ) return; q = &sc->q[sc->nq++]; q->mode = (uint8_t)mode; q->dark = (uint8_t)dark;
    q->wx[0] = (float)x0; q->wy[0] = (float)y0; q->wz[0] = (float)z0; q->wx[1] = (float)x1; q->wy[1] = (float)y1; q->wz[1] = (float)z1; q->wx[2] = (float)x2; q->wy[2] = (float)y2; q->wz[2] = (float)z2; q->wx[3] = (float)x3; q->wy[3] = (float)y3; q->wz[3] = (float)z3;
}
static double r3_cz(const r3_scene_t *sc, int x, int y) { return (x < 0 || y < 0 || x >= 74 || y >= 74 || sc->hm[y][x] == 0x4000) ? -400 : sc->zc[y][x]; }
static int r3_isvoid(const r3_scene_t *sc, int x, int y) { return x < 0 || y < 0 || x >= 74 || y >= 74 || sc->hm[y][x] == 0x4000; }
static int r3_opaque(const r3_scene_t *sc, int U, int V) { int p = 0, r = 0; return r3_fetch(sc->pa, sc->tiles, U, V, &p, &r) || r3_fetch(sc->pb, sc->tiles, U, V, &p, &r); }
static int r3_opaqueA(const r3_scene_t *sc, int U, int V) { int p = 0, r = 0; return r3_fetch(sc->pa, sc->tiles, U, V, &p, &r); }

static void r3_build(r3_scene_t *sc) {
    int x, y, dx, dy; r3_ctx_t c; memset(&c, 0, sizeof c); c.sc = sc;
    /* heights: isolated single cell columns (the statue, single trees) are props: they take the ground height around them and are drawn as cards */
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) sc->zc[y][x] = sc->hm[y][x] == 0x4000 ? -400 : 16.0 * ((sc->hm[y][x] >> 8) & 15);
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
        double z = 16.0 * ((sc->hm[y][x] >> 8) & 15), lo = 1e9; int same = 0, nn = 0;
        if (sc->hm[y][x] == 0x4000) continue;
        for (dy = -1; dy <= 1; dy++) for (dx = -1; dx <= 1; dx++) { int X = x + dx, Y = y + dy; double zn; if (!dx && !dy) continue; if (X < 0 || Y < 0 || X >= 74 || Y >= 74 || sc->hm[Y][X] == 0x4000) continue; zn = 16.0 * ((sc->hm[Y][X] >> 8) & 15); nn++; if (zn == z) same++; if (zn < lo) lo = zn; }
        if (nn >= 5 && !same && lo < z) sc->zc[y][x] = lo;
    }
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) sc->boxc[y][x] = (uint8_t)(sc->hm[y][x] != 0x4000 && (sc->hm[y][x] & 0x4000) && sc->zc[y][x] == 16.0 * ((sc->hm[y][x] >> 8) & 15));
    r3_find_roofs(sc, &c);
    /* the geometry as quads + the coverage of the original view */
    sc->hw = (float *)calloc((size_t)R3_TW * R3_TH * 3, 4); sc->cov = (uint8_t *)calloc((size_t)R3_TW * R3_TH, 1); sc->hb = (uint8_t *)calloc((size_t)R3_TW * R3_TH, 1); sc->q = (r3_quad_t *)malloc(sizeof(r3_quad_t) * R3_NQ);
    if (!sc->hw || !sc->cov || !sc->hb || !sc->q) return;
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
        double z = r3_cz(sc, x, y), x0 = 16.0 * x, y0 = 16.0 * y, x1 = x0 + 16, y1 = y0 + 16; int mode = sc->boxc[y][x] ? 1 : 0, k;
        if (r3_isvoid(sc, x, y)) continue;
        r3_addq(sc, mode, mode == 0 ? 2 : 0, x0, y0, z, x1, y0, z, x1, y1, z, x0, y1, z);   /* dark 2 = ground top face: soil colour where the picture has none */
        { double zn = r3_cz(sc, x + 1, y); if (zn < z) r3_addq(sc, mode, 0, x1, y0, z, x1, y1, z, x1, y1, zn, x1, y0, zn); }
        { double zn = r3_cz(sc, x, y + 1); if (zn < z) r3_addq(sc, mode, 0, x0, y1, z, x1, y1, z, x1, y1, zn, x0, y1, zn); }
        for (k = 0; k < sc->nq; k++) (void)k;
    }
    for (y = 0; y < sc->nq; y++) {   /* coverage pass from the original camera (quads -> triangles) */
        const r3_quad_t *q = &sc->q[y]; int t;
        for (t = 0; t < 2; t++) { int idx[3] = { 0, t ? 2 : 1, t ? 3 : 2 }, j; double P[3][3]; for (j = 0; j < 3; j++) { P[j][0] = q->wx[idx[j]]; P[j][1] = q->wy[idx[j]]; P[j][2] = q->wz[idx[j]]; } c.box = q->mode == 1; r3_rast(P, 1, r3_hit_cb, &c); }
    }
    { int r; for (r = 0; r < sc->nroofs; r++) { double T[6][3][3]; int t, nt = r3_roof_tris(&sc->roofs[r], T); c.box = 1; for (t = 0; t < nt; t++) r3_rast(T[t], 1, r3_hit_cb, &c); } }
    /* card strips: opaque picture pixels the box geometry does not carry (uncovered, or layer A pixels on plain ground), anchored at the foot of their run, one depth per card */
    {
        int32_t *lab = (int32_t *)calloc((size_t)R3_TW * R3_TH, 4); int *stk = (int *)malloc(sizeof(int) * R3_TW * 4); int U, nl = 0, nr = 0, cap = 40000; typedef struct { int U, y, n, lab; float bx, by, bz; } run_t; run_t *runs = (run_t *)malloc(sizeof(run_t) * cap);
        int *cnt, *off; float *dpool;
#define R3NEED(X, Y) (r3_opaque(sc, (X), (Y)) && (!sc->cov[(size_t)(Y) * R3_TW + (X)] || (!sc->hb[(size_t)(Y) * R3_TW + (X)] && r3_opaqueA(sc, (X), (Y)))))
        if (!lab || !stk || !runs) { free(lab); free(stk); free(runs); return; }
        for (y = 0; y < R3_TH; y++) for (U = 0; U < R3_TW; U++) {
            int sp = 0;
            if (lab[(size_t)y * R3_TW + U] || !R3NEED(U, y)) continue;
            nl++; lab[(size_t)y * R3_TW + U] = nl; stk[sp++] = y * R3_TW + U;
            while (sp > 0) { int c0 = stk[--sp], cx = c0 % R3_TW, cy = c0 / R3_TW, k; static const int dxs[4] = { 1, -1, 0, 0 }, dys[4] = { 0, 0, 1, -1 };
                for (k = 0; k < 4; k++) { int X = cx + dxs[k], Y = cy + dys[k]; if (X < 0 || Y < 0 || X >= R3_TW || Y >= R3_TH || lab[(size_t)Y * R3_TW + X] || !R3NEED(X, Y)) continue; lab[(size_t)Y * R3_TW + X] = nl; if (sp < R3_TW * 4 - 1) stk[sp++] = Y * R3_TW + X; } }
        }
        for (U = 0; U < R3_TW; U++) for (y = R3_TH - 2; y >= 0; y--) {
            int n = 0, v, yb = y;
            if (!R3NEED(U, y) || R3NEED(U, y + 1)) continue;
            for (v = y; v >= 0 && R3NEED(U, v); v--) n++;
            if (!sc->cov[(size_t)yb * R3_TW + U]) { if (!sc->cov[(size_t)(yb + 1) * R3_TW + U]) { y = v + 1; continue; } yb = yb + 1; }
            if (nr >= cap) { cap *= 2; runs = (run_t *)realloc(runs, sizeof(run_t) * cap); if (!runs) return; }
            { const float *h = sc->hw + ((size_t)yb * R3_TW + U) * 3; runs[nr].U = U; runs[nr].y = yb - 1; runs[nr].n = n; runs[nr].lab = lab[(size_t)y * R3_TW + U]; runs[nr].bx = h[0]; runs[nr].by = h[1]; runs[nr].bz = h[2]; nr++; }
            y = v + 1;
        }
        cnt = (int *)calloc(nl + 2, sizeof(int)); off = (int *)calloc(nl + 2, sizeof(int));
        { int r, tot = 0, l; for (r = 0; r < nr; r++) if (runs[r].n >= 8 && runs[r].n < 110) cnt[runs[r].lab]++;
          for (l = 0; l <= nl; l++) { off[l] = tot; tot += cnt[l]; } dpool = (float *)malloc((tot + 1) * 4); memset(cnt, 0, (nl + 2) * sizeof(int));
          for (r = 0; r < nr; r++) if (runs[r].n >= 8 && runs[r].n < 110) { l = runs[r].lab; dpool[off[l] + cnt[l]++] = runs[r].bx + runs[r].by; }
          for (l = 1; l <= nl; l++) { int k, m; if (!cnt[l]) continue; for (k = 1; k < cnt[l]; k++) { float t = dpool[off[l] + k]; m = k - 1; while (m >= 0 && dpool[off[l] + m] > t) { dpool[off[l] + m + 1] = dpool[off[l] + m]; m--; } dpool[off[l] + m + 1] = t; } dpool[off[l]] = dpool[off[l] + cnt[l] / 2]; } }
        sc->st = (r3_strip_t *)malloc(sizeof(r3_strip_t) * (nr + 1)); sc->ns = 0;
        if (sc->st) { int r; for (r = 0; r < nr; r++) {
            double bx = runs[r].bx, by = runs[r].by, bz = runs[r].bz; int n = runs[r].n;
            if (n < 110 && cnt[runs[r].lab] > 0 && fabs(dpool[off[runs[r].lab]] - (bx + by)) <= 40) { double D = dpool[off[runs[r].lab]], t = (D - (bx + by)) / 2; bx += t; by += t; bz += t; }   /* one depth per card, along the view ray: the original picture does not change */
            sc->st[sc->ns].U = runs[r].U; sc->st[sc->ns].y = runs[r].y; sc->st[sc->ns].n = n; sc->st[sc->ns].bx = (float)bx; sc->st[sc->ns].by = (float)by; sc->st[sc->ns].bz = (float)bz; sc->ns++; } }
        free(cnt); free(off); free(dpool); free(lab); free(stk); free(runs);
    }
}
static int r3_worker(void *u) {
    r3_scene_t *sc = (r3_scene_t *)u; uint64_t t0 = SDL_GetPerformanceCounter();
    r3_build(sc);
    if (getenv("LANDSTALKER_R3D_LOG")) printf("r3d: scene built in %.0f ms: %d quads, %d roofs, %d card strips (hash %08x)\n", (double)(SDL_GetPerformanceCounter() - t0) * 1e3 / (double)SDL_GetPerformanceFrequency(), sc->nq, sc->nroofs, sc->ns, sc->hash);
    r3_done = 1; return 0;
}
static void r3_free(r3_scene_t *sc) { if (!sc) return; free(sc->hw); free(sc->cov); free(sc->hb); free(sc->q); free(sc->st); free(sc); }
static int r3_bright(const uint32_t *pix) { int i, best = 0; for (i = 1; i < 64; i++) { int s = ((pix[i] >> 16) & 255) + ((pix[i] >> 8) & 255) + (pix[i] & 255); if (s > best) best = s; } return best >= 500; }   /* not in a fade */
static void r3_request(const lk_o3d_src_t *src, uint32_t hash) {
    int x, y, cells = 0; r3_scene_t *sc;
    if (r3_thread && r3_done) { SDL_WaitThread(r3_thread, NULL); r3_thread = NULL; r3_done = 0; r3_busy = 0; r3_free(r3_active); r3_active = r3_work; r3_work = NULL; }   /* hand over */
    if (r3_busy || hash == r3_req_hash || !r3_bright(src->pix)) return;
    for (y = 0; y < 152; y += 4) for (x = 0; x < 304; x += 4) cells += (src->pa[y][x] | src->pb[y][x]) >> 16 & 1;
    if (cells < 20) return;                                   /* no room picture (load / black frame) */
    sc = (r3_scene_t *)calloc(1, sizeof *sc); if (!sc) return;
    sc->hash = hash; memcpy(sc->tiles, src->tiles, sizeof sc->tiles); memcpy(sc->pa, src->pa, sizeof sc->pa); memcpy(sc->pb, src->pb, sizeof sc->pb); memcpy(sc->pix, src->pix, sizeof sc->pix);
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) sc->hm[y][x] = lk_o3d_hm(x, y);
    r3_work = sc; r3_req_hash = hash; r3_busy = 1; r3_done = 0;
    if (getenv("LANDSTALKER_R3D_SYNC")) { r3_worker(sc); r3_thread = NULL; r3_done = 0; r3_busy = 0; r3_free(r3_active); r3_active = sc; r3_work = NULL; return; }   /* test aid: build now (headless screenshots) */
    r3_thread = SDL_CreateThread(r3_worker, "lk_r3d", sc);
    if (!r3_thread) { r3_busy = 0; r3_work = NULL; r3_free(sc); }
}

/* ---- rendering ---- */
typedef struct { double x, y, w, u, v; } r3_vtx;
static double r3_fx, r3_fy, r3_ox, r3_oy, r3_S, r3_cy, r3_sy, r3_cp, r3_sp;   /* focus, screen offset, scale, yaw cos / sin, pitch cos / sin */
static const double R3K2 = 1.41421356237;
static void r3_proj(double wx, double wy, double z, double *sx, double *sy, double *w) {
    double dx = wx - r3_fx, dy = wy - r3_fy, xr = dx * r3_cy - dy * r3_sy, yr = dx * r3_sy + dy * r3_cy, u = (xr - yr) / R3K2, dd = (xr + yr) / R3K2;
    *sx = r3_S * R3K2 * u + r3_ox; *sy = r3_S * 1.22474487139 * (dd * r3_sp - z * r3_cp) + r3_oy; *w = dd * r3_cp + z * r3_sp;
}
static r3_vtx r3_mk(double wx, double wy, double z) { r3_vtx p; r3_proj(wx, wy, z, &p.x, &p.y, &p.w); p.u = wx - wy + 1184; p.v = (wx + wy) / 2 - z; return p; }
static void r3_tri(r3_vtx a, r3_vtx b, r3_vtx c, int mode, int dark, const lk_o3d_src_t *src) {   /* scanline rasteriser: spans from the edges, w / u / v by their gradients */
    double den = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y), idn, ymin = fmin(a.y, fmin(b.y, c.y)), ymax = fmax(a.y, fmax(b.y, c.y)), xmin3 = fmin(a.x, fmin(b.x, c.x)), xmax3 = fmax(a.x, fmax(b.x, c.x));
    double dl1x, dl1y, dl2x, dl2y, dwx, dwy, dux, duy, dvx, dvy; int y0, y1, y;
    if (fabs(den) < 1e-9 || xmax3 < 0 || xmin3 > r3_iw || ymax < 0 || ymin > r3_ih) return;
    idn = 1.0 / den; dl1x = (b.y - c.y) * idn; dl1y = (c.x - b.x) * idn; dl2x = (c.y - a.y) * idn; dl2y = (a.x - c.x) * idn;
    dwx = dl1x * (a.w - c.w) + dl2x * (b.w - c.w); dwy = dl1y * (a.w - c.w) + dl2y * (b.w - c.w);
    dux = dl1x * (a.u - c.u) + dl2x * (b.u - c.u); duy = dl1y * (a.u - c.u) + dl2y * (b.u - c.u);
    dvx = dl1x * (a.v - c.v) + dl2x * (b.v - c.v); dvy = dl1y * (a.v - c.v) + dl2y * (b.v - c.v);
    y0 = (int)ceil(ymin - 0.5); y1 = (int)floor(ymax - 0.5); if (y0 < 0) y0 = 0; if (y1 >= r3_ih) y1 = r3_ih - 1;
    for (y = y0; y <= y1; y++) {
        double py = y + 0.5, xl = 1e30, xr = -1e30, l1, l2, w, u, v; int xs, xe, x, k; const r3_vtx *P[3] = { &a, &b, &c };
        for (k = 0; k < 3; k++) { const r3_vtx *p = P[k], *q = P[(k + 1) % 3]; if ((p->y <= py && q->y > py) || (q->y <= py && p->y > py)) { double xx = p->x + (py - p->y) * (q->x - p->x) / (q->y - p->y); if (xx < xl) xl = xx; if (xx > xr) xr = xx; } }
        if (xl > xr) continue;
        xs = (int)ceil(xl - 0.5); xe = (int)floor(xr - 0.5); if (xs < 0) xs = 0; if (xe >= r3_iw) xe = r3_iw - 1; if (xs > xe) continue;
        l1 = ((b.y - c.y) * (xs + 0.5 - c.x) + (c.x - b.x) * (py - c.y)) * idn; l2 = ((c.y - a.y) * (xs + 0.5 - c.x) + (a.x - c.x) * (py - c.y)) * idn;
        w = c.w + l1 * (a.w - c.w) + l2 * (b.w - c.w); u = c.u + l1 * (a.u - c.u) + l2 * (b.u - c.u); v = c.v + l1 * (a.v - c.v) + l2 * (b.v - c.v);
        { float *zr = r3_zb + (size_t)y * r3_iw; uint32_t *ir = r3_img + (size_t)y * r3_iw;
          for (x = xs; x <= xe; x++, w += dwx, u += dux, v += dvx) {
            uint32_t col; int tu, tv;
            if (w <= zr[x]) continue;
            tu = (int)(u + 4096.0) - 4096; tv = (int)(v + 4096.0) - 4096;   /* floor for the small negative values at the edges */
            if (mode == 9) { if (tu < 0 || tv < 0 || tu >= 416 || tv >= 224) continue; col = lk_hd_sprc[tv * 416 + tu]; if (!col) continue; }   /* figure strip: u = column + 48, v = row of the 1x frame */
            else { col = r3_samp(src->pa, src->pb, src->tiles, src->pix, mode == 0 ? 0 : 1, tu, tv); if (!col) { if (mode == 0 && dark == 2) col = 0xFF483422u; else continue; } }
            if (dark == 1) col = 0xFF000000u | ((((col >> 16) & 255) * 3 / 5) << 16) | ((((col >> 8) & 255) * 3 / 5) << 8) | (((col & 255) * 3 / 5));
            zr[x] = (float)w; ir[x] = col;
          } }
        (void)dwy; (void)duy; (void)dvy;
    }
}
static void r3_cards_sprites(const r3_scene_t *sc, const lk_o3d_src_t *src, int sw, int e) {
    int i;
    for (i = 0; i < sc->ns; i++) {                      /* map cards: strips keep the original right axis, a little wider than a picture pixel */
        const r3_strip_t *s = &sc->st[i]; double bx = s->bx, by = s->by, bz = s->bz, r0 = 1 / R3K2, r1 = -1 / R3K2, hw = 0.5 / R3K2 * 1.35; int n = s->n; r3_vtx a, b, c, d;
        if (n >= 110) { a = r3_mk(bx - r0 * hw, by - r1 * hw, bz); b = r3_mk(bx + r0 * hw, by + r1 * hw, bz); c = r3_mk(bx + r0 * hw - n, by + r1 * hw - n, bz); d = r3_mk(bx - r0 * hw - n, by - r1 * hw - n, bz); }
        else { a = r3_mk(bx - r0 * hw, by - r1 * hw, bz); b = r3_mk(bx + r0 * hw, by + r1 * hw, bz); c = r3_mk(bx + r0 * hw, by + r1 * hw, bz + n); d = r3_mk(bx - r0 * hw, by - r1 * hw, bz + n); }
        a.u = b.u = c.u = d.u = s->U + 0.5; a.v = b.v = s->y + 1.0; c.v = d.v = s->y + 1.0 - n;
        r3_tri(a, b, c, 1, 0, src); r3_tri(a, c, d, 1, 0, src);
    }
    /* figures: runs of sprite pixels per screen column with the same ground row, joined across columns; a rigid billboard per figure that faces the camera */
    {
        enum { MAXR = 6000 }; static struct { int x, yt, yb, d, fig; } rn[MAXR]; static int figx0[MAXR], figx1[MAXR]; int nr = 0, nf = 0, prev0 = 0, prev1 = 0, x, y, r;
        for (x = -e; x < 320 + e && x + 48 < 416; x++) {
            int cur0 = nr; y = 23;
            while (y < 224 && nr < MAXR) {
                int idx = y * 416 + x + 48, d, yt, yb;
                if (!(lk_hd_spr[idx] & 1) || (lk_hd_depth[idx] == 0x7FFF) || lk_hd_dstamp[y] != lk_hd_gen) { y++; continue; }
                d = lk_hd_depth[idx]; yt = y; while (y < 224 && (lk_hd_spr[y * 416 + x + 48] & 1) && lk_hd_depth[y * 416 + x + 48] == d) y++; yb = y - 1;
                rn[nr].x = x; rn[nr].yt = yt; rn[nr].yb = yb; rn[nr].d = d; rn[nr].fig = -1;
                for (r = prev0; r < prev1; r++) if (rn[r].fig >= 0 && abs(rn[r].d - d) <= 1 && rn[r].yt <= yb + 1 && rn[r].yb >= yt - 1) { rn[nr].fig = rn[r].fig; break; }
                if (rn[nr].fig < 0 && nf < MAXR) { rn[nr].fig = nf; figx0[nf] = x; figx1[nf] = x; nf++; }
                if (rn[nr].fig >= 0) figx1[rn[nr].fig] = x;
                nr++;
            }
            prev0 = cur0; prev1 = nr;
        }
        for (r = 0; r < nr; r++) {
            int f = rn[r].fig, xc, ptu, ptv, found = 0, dd; double ax = 0, ay = 0, az = 0, ru0, ru1, hw, off, zb2, zt2; r3_vtx a, b, c, d;
            if (f < 0) continue;
            xc = (figx0[f] + figx1[f]) / 2; ptu = src->u0 + xc; ptv = src->v0 + rn[r].d;   /* the ground point of the figure's middle: the first surface along the view ray through (xc, ground row) */
            for (dd = 0; dd <= 6 && !found; dd++) { int k; for (k = -1; k <= 1 && !found; k += 2) { int py = ptv + dd * k; if (ptu >= 0 && ptu < R3_TW && py >= 0 && py < R3_TH && sc->cov[(size_t)py * R3_TW + ptu]) { const float *h = sc->hw + ((size_t)py * R3_TW + ptu) * 3; ax = h[0]; ay = h[1]; az = h[2] - (py - ptv); found = 1; } } }
            if (!found) continue;
            ru0 = (r3_cy - r3_sy) / R3K2; ru1 = (-r3_sy - r3_cy) / R3K2; hw = 0.5 * 0.70711 * 1.35; off = (rn[r].x - xc) * 0.70711;   /* camera right axis in the world, one picture pixel = 0.7071 world units */
            zb2 = az + (rn[r].d - (rn[r].yb + 1)); zt2 = az + (rn[r].d - rn[r].yt);
            { double cx = ax + ru0 * off, cyy = ay + ru1 * off;
              a = r3_mk(cx - ru0 * hw, cyy - ru1 * hw, zb2); b = r3_mk(cx + ru0 * hw, cyy + ru1 * hw, zb2); c = r3_mk(cx + ru0 * hw, cyy + ru1 * hw, zt2); d = r3_mk(cx - ru0 * hw, cyy - ru1 * hw, zt2); }
            a.u = b.u = c.u = d.u = rn[r].x + 48 + 0.5; a.v = b.v = rn[r].yb + 1.0; c.v = d.v = rn[r].yt;
            { double bias = 0.6; a.w += bias; b.w += bias; c.w += bias; d.w += bias; }   /* figures stand a little in front of the ground they touch */
            r3_tri(a, b, c, 9, 0, src); r3_tri(a, c, d, 9, 0, src);
        }
    }
    (void)sw;
}
static uint32_t *r3_assemble(const uint32_t *fb, int sw, int e, int *ow, int *oh);
uint32_t *lk_r3d_assemble(const uint32_t *fb, int sw, int e, int *ow, int *oh) {
    static double acc; static int cnt; uint64_t t0 = SDL_GetPerformanceCounter(); uint32_t *r = r3_assemble(fb, sw, e, ow, oh);
    if (r && getenv("LANDSTALKER_R3D_LOG")) { acc += (double)(SDL_GetPerformanceCounter() - t0) * 1e3 / (double)SDL_GetPerformanceFrequency(); if (++cnt % 120 == 0) printf("r3d: %.2f ms per frame (avg of %d): ground+roofs %.2f, cards+figures %.2f, compose %.2f, look %.2f\n", acc / cnt, cnt, r3_acc[0] / r3_nacc, r3_acc[1] / r3_nacc, r3_acc[2] / r3_nacc, r3_acc[3] / r3_nacc); }
    return r;
}
static uint32_t *r3_assemble(const uint32_t *fb, int sw, int e, int *ow, int *oh) {
    lk_o3d_src_t src; const int N = lk_r3d_on() == 2 ? 1 : 2; int W = sw * N, H = 224 * N, x, y, ok, i; uint32_t hash; const r3_scene_t *sc;
    if (!lk_r3d_on()) return NULL;
    ok = lk_o3d_get(&src); hash = ok ? lk_o3d_hash() : 0;
    if (ok) r3_request(&src, hash);
    sc = r3_active;
    if (!ok || !sc || sc->hash != hash || !sc->q || !sc->hw) return NULL;
    { const char *ey = getenv("LANDSTALKER_R3D_YAW"), *ep = getenv("LANDSTALKER_R3D_PITCH");   /* fixed camera (test aid) */
      if (ey || ep) { r3_yaw = (ey ? atof(ey) : 0) * M_PI / 180; r3_pitch = (ep ? atof(ep) : 0) * M_PI / 180; r3_fixed = 1; }
      if (!r3_fixed) {                                   /* right stick: left / right turns, up / down tilts; the click resets; keys [ ] and - = as a fallback */
        double sx = lk_rs_x / 32768.0, sy2 = lk_rs_y / 32768.0; const Uint8 *ks = SDL_GetKeyboardState(NULL);
        if (fabs(sx) < 0.25) sx = 0; if (fabs(sy2) < 0.25) sy2 = 0;
        if (ks[SDL_SCANCODE_RIGHTBRACKET]) sx = 1; if (ks[SDL_SCANCODE_LEFTBRACKET]) sx = -1; if (ks[SDL_SCANCODE_EQUALS]) sy2 = 1; if (ks[SDL_SCANCODE_MINUS]) sy2 = -1;
        r3_yaw += sx * 70.0 * M_PI / 180 / 60.0; r3_pitch += sy2 * 40.0 * M_PI / 180 / 60.0;
        if (lk_rs_click || ks[SDL_SCANCODE_BACKSPACE]) { r3_yaw = 0; r3_pitch = 0; }
        if (r3_yaw > 0.87) r3_yaw = 0.87; if (r3_yaw < -0.87) r3_yaw = -0.87; if (r3_pitch > 0.44) r3_pitch = 0.44; if (r3_pitch < -0.17) r3_pitch = -0.17;
      } }
    if (!r3_img || r3_iw != W || r3_ih != H) { free(r3_img); free(r3_zb); r3_img = (uint32_t *)malloc((size_t)W * H * 4); r3_zb = (float *)malloc((size_t)W * H * 4); r3_iw = W; r3_ih = H; }
    if (!r3_img || !r3_zb) return NULL;
    for (i = 0; i < W * H; i++) { r3_img[i] = 0xFF000000u; r3_zb[i] = -1e30f; }
    { double Uc = src.u0 + sw / 2 - e, Vc = src.v0 + 112;            /* the ground point at the middle of the screen is the centre of the turn */
      r3_fx = (Uc - 1184 + 2 * Vc) / 2; r3_fy = (2 * Vc - (Uc - 1184)) / 2; r3_S = N; r3_ox = W / 2.0; r3_oy = H / 2.0; r3_cy = cos(r3_yaw); r3_sy = sin(r3_yaw); r3_cp = cos(atan(1.0 / R3K2) + r3_pitch); r3_sp = sin(atan(1.0 / R3K2) + r3_pitch); }
    r3_t[0] = SDL_GetPerformanceCounter();
    for (i = 0; i < sc->nq; i++) {
        const r3_quad_t *q = &sc->q[i]; r3_vtx v[4]; int k;
        for (k = 0; k < 4; k++) v[k] = r3_mk(q->wx[k], q->wy[k], q->wz[k]);
        r3_tri(v[0], v[1], v[2], q->mode, q->dark, &src); r3_tri(v[0], v[2], v[3], q->mode, q->dark, &src);
    }
    for (i = 0; i < sc->nroofs; i++) { double T[6][3][3]; int t, nt = r3_roof_tris(&sc->roofs[i], T); for (t = 0; t < nt; t++) r3_tri(r3_mk(T[t][0][0], T[t][0][1], T[t][0][2]), r3_mk(T[t][1][0], T[t][1][1], T[t][1][2]), r3_mk(T[t][2][0], T[t][2][1], T[t][2][2]), 1, 0, &src); }
    r3_t[1] = SDL_GetPerformanceCounter();
    r3_cards_sprites(sc, &src, sw, e);
    r3_t[2] = SDL_GetPerformanceCounter();
    for (y = 0; y < 224; y++) for (x = 0; x < sw; x++) {                    /* game pixels outside the map (HUD, text box, black lines of the full height band) keep the final 1x pixel */
        int cx = x - e, in3d = y >= 23 && lk_hd_dstamp[y] == lk_hd_gen && cx >= -48 && cx < 368 && !(lk_hd_spr[y * 416 + cx + 48] & 4); int sy, sx;
        if (!in3d) for (sy = 0; sy < N; sy++) for (sx = 0; sx < N; sx++) r3_img[(size_t)(y * N + sy) * W + x * N + sx] = fb[(size_t)y * sw + x];
    }
    *ow = W; *oh = H; r3_t[3] = SDL_GetPerformanceCounter();
    { static int16_t *ident; static int iw0; if (iw0 != sw) { free(ident); ident = (int16_t *)malloc((size_t)sw * 224 * 2); iw0 = sw; if (ident) for (y = 0; y < 224; y++) for (x = 0; x < sw; x++) ident[(size_t)y * sw + x] = (int16_t)x; }
      if (ident) { lk_hd_look3d = 1; lk_hd_look(r3_img, W, H, N, sw, e, ident); lk_hd_look3d = 0; } }   /* bloom / vignette / colour grade of Options > Video on the 3D picture */
    r3_t[4] = SDL_GetPerformanceCounter(); { int q; for (q = 0; q < 4; q++) r3_acc[q] += (double)(r3_t[q + 1] - r3_t[q]) * 1e3 / (double)SDL_GetPerformanceFrequency(); r3_nacc++; }
    return r3_img;
}
static int lk_r3d_present(const uint8_t *framebuffer, int sw, const lk_rect *r) {
    int iw, ih; uint32_t *img;
    if (!lk_r3d_on()) return 0;
    img = lk_r3d_assemble((const uint32_t *)framebuffer, sw, lk_wide_e, &iw, &ih);
    if (!img) return 0;
    return lk_hd_show(img, iw, ih, iw / sw, r);
}
