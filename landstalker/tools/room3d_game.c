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
extern int lk_o3d_blk(int layer, int x, int y); extern int lk_o3d_get(lk_o3d_src_t *o); extern int lk_o3d_hm(int x, int y); extern uint32_t lk_o3d_hash(void);
extern int lk_hd_look3d;
extern volatile int lk_rs_x, lk_rs_y, lk_rs_click;   /* right stick (input.c, tools/patch_room3d.py) */

static const double R3K2 = 1.41421356237;
#define R3_TW 2432
#define R3_TH 1216
#define R3_NQ 24000
typedef struct { double X0, X1, Y0, Y1, z0, H, o; int axis; int cx0, cx1, cy0, cy1; } r3_roof_t;   /* eave rectangle incl. overhang, wall top z0, ridge height H, ridge axis; cx0..cy1 = the footprint in cells */
typedef struct { float x[3], y[3], z[3]; uint8_t mat, r, g, b, sw, ax; } r3_ht_t;      /* house model triangle: mat 1 = coloured by the room picture (projective), 8 = flat colour (r g b, already shaded), 10 = TEXTURED with a pixel swatch cut from the room's own art (sw = swatch, ax = planar axis, r = stepped shade) */
typedef struct { float wx[4], wy[4], wz[4]; uint8_t mode, dark; } r3_quad_t;       /* mode 0 ground (layer B only), 1 composite, 2 roof */
typedef struct { int U, y, n; float bx, by, bz; } r3_strip_t;
typedef struct {
    uint32_t hash, base_hash; int nq, ns, nroofs; r3_quad_t *q; r3_strip_t *st; r3_roof_t roofs[64];
    float *hw; uint8_t *cov, *hb;           /* hit position (3 floats) / covered / box flag per picture pixel of the original view */
    uint8_t tiles[0x12000]; uint32_t pa[152][304], pb[152][304], pix[64];   /* the snapshot the scene was built from */
    int hm[74][74]; double zc[74][74]; uint8_t boxc[74][74]; uint8_t repl[74][74];   /* repl: cells inside a house model (their column quads are not drawn) */
    uint32_t swpx[6][256]; uint8_t swok[6];   /* pixel swatches (16 x 16, opaque) cut from layer A blocks: 1 thatch, 2 wood, 3 foliage, 4 logs */
    r3_ht_t *ht; int nht, nht_cap, houses, objects, trees; uint8_t *gm; int fgb[74][74]; int ntrees; int tree[3000][4]; int nfence; int fence[3000][3];   /* gm: picture pixels of the tree blocks (the card strips skip them); fgb: layer A block id per cell */
    int light; float *smap; int smw, smh; double sma, smb; uint8_t *gmask;   /* gmask: shadow of every horizontal face per world unit (1184 x 1184), 255 = lit */   /* shadow map of the static scene: highest light depth per light space texel */
} r3_scene_t;
static int r3_houses_cache = -1;
int lk_r3d_houses_get(void) { if (r3_houses_cache < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_R3D_HOUSES"); char path[512]; FILE *f; int v = 0; snprintf(path, sizeof path, "%s/.landstalker_houses", h ? h : "."); f = NULL; /* PAUSED 2026-10-24: the saved file is ignored, only the env variable switches it on (test aid) */ if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); r3_houses_cache = v < 0 ? 0 : v > 2 ? 2 : v; } return r3_houses_cache; }
void lk_r3d_houses_set(int v) { const char *h = getenv("HOME"); char path[512]; FILE *f; r3_houses_cache = v < 0 ? 0 : v > 2 ? 2 : v; snprintf(path, sizeof path, "%s/.landstalker_houses", h ? h : "."); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", r3_houses_cache); fclose(f); } }   /* Options > Video > 3D Houses */
/* ---- 3D Light: cast shadows of the static scene (sun direction, shadow map built with the scene), applied to ground / box faces; lit areas keep the picture's colours (the art already has its own light) ---- */
static int r3_light_cache = -1; static const r3_scene_t *r3_shsc;
static double r3_Lx, r3_Ly, r3_Lz, r3_e1x, r3_e1y, r3_e2x, r3_e2y, r3_e2z;
int lk_r3d_light_get(void) { if (r3_light_cache < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_R3D_LIGHT"); char path[512]; FILE *f; int v = 0; snprintf(path, sizeof path, "%s/.landstalker_r3dlight", h ? h : "."); f = NULL; /* PAUSED 2026-10-24: the saved file is ignored, only the env variable switches it on (test aid) */ if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); r3_light_cache = v ? 1 : 0; } return r3_light_cache; }
void lk_r3d_light_set(int v) { const char *h = getenv("HOME"); char path[512]; FILE *f; r3_light_cache = v ? 1 : 0; snprintf(path, sizeof path, "%s/.landstalker_r3dlight", h ? h : "."); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", r3_light_cache); fclose(f); } }
static void r3_sun_init(void) {   /* the sun: from the north west, rather high; shadows fall towards the viewer's lower right, where they are seen */
    double lx = -0.62, ly = -0.38, lz = 0.58, ln = sqrt(lx * lx + ly * ly + lz * lz), e1n; lx /= ln; ly /= ln; lz /= ln;
    r3_Lx = lx; r3_Ly = ly; r3_Lz = lz; e1n = sqrt(ly * ly + lx * lx); r3_e1x = ly / e1n; r3_e1y = -lx / e1n;
    r3_e2x = ly * 0 - lz * r3_e1y; r3_e2y = lz * r3_e1x - lx * 0; r3_e2z = lx * r3_e1y - ly * r3_e1x;   /* l x e1 */
}
static r3_scene_t *r3_active, *r3_work; static SDL_Thread *r3_thread; static volatile int r3_busy, r3_done; static uint32_t r3_req_hash; static int r3_on_cache = -1;
static long r3_last_frame = -100; static int r3_camctl_cache = -1;
static double r3_yaw, r3_pitch, r3_dyaw, r3_dpitch; static int r3_fixed; static uint64_t r3_t[5]; static double r3_acc[4]; static int r3_nacc;
static uint32_t *r3_img, *r3_zbuf_dummy; static float *r3_zb; static int r3_iw, r3_ih;

int lk_r3d_on(void) {
    if (r3_on_cache < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_R3D"); char path[512]; FILE *f; int v = 0; snprintf(path, sizeof path, "%s/.landstalker_room3d", h ? h : "."); f = NULL; /* PAUSED 2026-10-24: the saved file is ignored, only the env variable switches it on (test aid) */ if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); r3_on_cache = v < 0 ? 0 : v > 2 ? 2 : v; }   /* 0 Off, 1 On = 2 x 2 pixels per game pixel, 2 = 1 x 1 (fast) */
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
    snprintf(path, sizeof path, "%s/.landstalker_r3d/roofs2_%08x.txt", home ? home : ".", sc->base_hash);
    cf = NULL; /* PAUSED 2026-10-24: the saved file is ignored, only the env variable switches it on (test aid) */
    if (cf) { r3_roof_t r; sc->nroofs = 0; while (sc->nroofs < 64 && fscanf(cf, "%lf %lf %lf %lf %lf %lf %lf %d %d %d %d %d", &r.X0, &r.X1, &r.Y0, &r.Y1, &r.z0, &r.H, &r.o, &r.axis, &r.cx0, &r.cx1, &r.cy0, &r.cy1) == 12) sc->roofs[sc->nroofs++] = r; fclose(cf); return; }
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
        br.cx0 = bx0; br.cx1 = bx1; br.cy0 = by0; br.cy1 = by1; sc->roofs[sc->nroofs++] = br; (void)bth;
        for (y = by0; y <= by1; y++) for (x = bx0; x <= bx1; x++) rem[y][x] = 0;
    }
    free(c->th); free(c->rmask); c->th = c->rmask = NULL;
    { char dir[600]; snprintf(dir, sizeof dir, "%s/.landstalker_r3d", home ? home : "."); mkdir(dir, 0777); }
    cf = fopen(path, "w");
    if (cf) { int r; for (r = 0; r < sc->nroofs; r++) fprintf(cf, "%.3f %.3f %.3f %.3f %.3f %.3f %.3f %d %d %d %d %d\n", sc->roofs[r].X0, sc->roofs[r].X1, sc->roofs[r].Y0, sc->roofs[r].Y1, sc->roofs[r].z0, sc->roofs[r].H, sc->roofs[r].o, sc->roofs[r].axis, sc->roofs[r].cx0, sc->roofs[r].cx1, sc->roofs[r].cy0, sc->roofs[r].cy1); fclose(cf); }
}
static void r3_addq(r3_scene_t *sc, int mode, int dark, double x0, double y0, double z0, double x1, double y1, double z1, double x2, double y2, double z2, double x3, double y3, double z3) {
    r3_quad_t *q; if (sc->nq >= R3_NQ) return; q = &sc->q[sc->nq++]; q->mode = (uint8_t)mode; q->dark = (uint8_t)dark;
    q->wx[0] = (float)x0; q->wy[0] = (float)y0; q->wz[0] = (float)z0; q->wx[1] = (float)x1; q->wy[1] = (float)y1; q->wz[1] = (float)z1; q->wx[2] = (float)x2; q->wy[2] = (float)y2; q->wz[2] = (float)z2; q->wx[3] = (float)x3; q->wy[3] = (float)y3; q->wz[3] = (float)z3;
}
static double r3_cz(const r3_scene_t *sc, int x, int y) { return (x < 0 || y < 0 || x >= 74 || y >= 74 || sc->hm[y][x] == 0x4000) ? -400 : sc->zc[y][x]; }
static int r3_isvoid(const r3_scene_t *sc, int x, int y) { return x < 0 || y < 0 || x >= 74 || y >= 74 || sc->hm[y][x] == 0x4000; }
static int r3_opaque(const r3_scene_t *sc, int U, int V) { int p = 0, r = 0; return r3_fetch(sc->pa, sc->tiles, U, V, &p, &r) || r3_fetch(sc->pb, sc->tiles, U, V, &p, &r); }
static int r3_opaqueA(const r3_scene_t *sc, int U, int V) { int p = 0, r = 0; return r3_fetch(sc->pa, sc->tiles, U, V, &p, &r); }

/* ---- object models (trees, bushes, rocks): `.r3m` files made by tools/remake_assets.py (kiln -> GLB -> r3m) in ~/.landstalker_remake/models; Options > Video > 3D Objects ---- */
typedef struct { int n; float *v; uint8_t *c; float ymin, ymax; } r3_model_t;
static r3_model_t r3_models[3]; static int r3_models_loaded; static int r3_objects_cache = -1;
static int r3_trees_cache = -1;
int lk_r3d_trees_get(void) { if (r3_trees_cache < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_R3D_TREES"); char path[512]; FILE *f; int v = 0; snprintf(path, sizeof path, "%s/.landstalker_r3dtrees", h ? h : "."); f = NULL; /* PAUSED 2026-10-24: the saved file is ignored, only the env variable switches it on (test aid) */ if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); r3_trees_cache = v ? 1 : 0; } return r3_trees_cache; }
void lk_r3d_trees_set(int v) { const char *h = getenv("HOME"); char path[512]; FILE *f; r3_trees_cache = v ? 1 : 0; snprintf(path, sizeof path, "%s/.landstalker_r3dtrees", h ? h : "."); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", r3_trees_cache); fclose(f); } }   /* Options > Video > 3D Trees (models instead of the tree sprites / cards) */
int lk_r3d_objects_get(void) { if (r3_objects_cache < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_R3D_OBJECTS"); char path[512]; FILE *f; int v = 0; snprintf(path, sizeof path, "%s/.landstalker_r3dobjects", h ? h : "."); f = NULL; /* PAUSED 2026-10-24: the saved file is ignored, only the env variable switches it on (test aid) */ if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); r3_objects_cache = v ? 1 : 0; } return r3_objects_cache; }
void lk_r3d_objects_set(int v) { const char *h = getenv("HOME"); char path[512]; FILE *f; r3_objects_cache = v ? 1 : 0; snprintf(path, sizeof path, "%s/.landstalker_r3dobjects", h ? h : "."); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", r3_objects_cache); fclose(f); } }
static void r3_models_load(void) {
    static const char *nm[3] = { "pine", "bush", "rock" }; const char *h = getenv("HOME"); int k;
    if (r3_models_loaded) return; r3_models_loaded = 1;
    for (k = 0; k < 3; k++) {
        char path[600]; FILE *f; uint32_t n; char magic[4]; r3_model_t *md = &r3_models[k];
        snprintf(path, sizeof path, "%s/.landstalker_remake/models/%s.r3m", h ? h : ".", nm[k]); f = fopen(path, "rb"); if (!f) continue;
        if (fread(magic, 1, 4, f) != 4 || memcmp(magic, "R3M1", 4) || fread(&n, 4, 1, f) != 1 || n == 0 || n > 20000) { fclose(f); continue; }
        md->v = (float *)malloc(sizeof(float) * 9 * n); md->c = (uint8_t *)malloc(4 * n);
        if (md->v && md->c) { uint32_t i; md->ymin = 1e9f; md->ymax = -1e9f; for (i = 0; i < n; i++) { int j; if (fread(md->v + 9 * i, 4, 9, f) != 9 || fread(md->c + 4 * i, 1, 4, f) != 4) { n = i; break; } for (j = 0; j < 3; j++) { float y = md->v[9 * i + 3 * j + 1]; if (y < md->ymin) md->ymin = y; if (y > md->ymax) md->ymax = y; } } md->n = (int)n; }
        fclose(f);
    }
}
/* ---- house models: real geometry per house (walls, roof with overhang and gables, ridge beam, corner posts); the picture-coloured parts (mat 1) keep the original art from the original camera, the new parts (mat 8) have their own colour and light ---- */
/* ---- pixel swatches: 16 x 16 opaque pieces of the room's own art (layer A blocks that are full), by colour class; the most common matching block of the room wins ---- */
static void r3_find_swatches(r3_scene_t *sc);
static void r3_find_swatches_dummy(void) {}
static void r3_find_swatches(r3_scene_t *sc) {
    static int cnt[1024]; static float fr[1024][5]; static uint8_t seen[1024]; static int px[1024], py[1024]; int x, y, b, c; float bestv[5] = { 0, 0, 0, 0, 0 }; int bestb[5] = { -1, -1, -1, -1, -1 };
    memset(cnt, 0, sizeof cnt); memset(seen, 0, sizeof seen); memset(sc->swok, 0, sizeof sc->swok);
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
        int bl = sc->fgb[y][x]; if (!bl) continue; cnt[bl]++;
        if (!seen[bl]) {
            int U0 = 16 * (x - y) + 1184 - 16, V0 = 8 * (x + y), dx, dy, op = 0, k[5] = { 0, 0, 0, 0, 0 }; seen[bl] = 1; px[bl] = U0; py[bl] = V0;
            for (dy = 0; dy < 16; dy++) for (dx = 0; dx < 16; dx++) { uint32_t q = r3_samp(sc->pa, sc->pb, sc->tiles, sc->pix, 3, U0 + dx, V0 + dy); int r, g, bb; if (!q) continue; op++; r = (q >> 16) & 255; g = (q >> 8) & 255; bb = q & 255;
                if (r >= 160 && g >= 120 && bb <= 100 && r > g && g > bb) k[1]++;                                                 /* thatch */
                else if (r >= 110 && r <= 215 && g >= 65 && g <= 150 && bb >= 20 && bb <= 100 && r > g && g > bb && g * 100 < r * 80) k[2]++;   /* wood */
                if (g > r + 14 && g > bb + 8 && g >= 110) k[3]++;                                                                  /* foliage */
                if (g >= r && g > bb && r <= 130 && g < 110) k[4]++; }                                                             /* logs: dark olive */
            for (c = 1; c <= 4; c++) fr[bl][c] = op == 256 ? k[c] / 256.0f : 0.0f;
        }
    }
    for (b = 1; b < 1024; b++) if (seen[b]) for (c = 1; c <= 4; c++) { float need = c == 1 ? 0.50f : c == 2 ? 0.30f : c == 3 ? 0.40f : 0.45f, v = fr[b][c]; if (v >= need) { float s = v * 100.0f + (cnt[b] > 20 ? 20 : cnt[b]); if (s > bestv[c]) { bestv[c] = s; bestb[c] = b; } } }
    for (c = 1; c <= 4; c++) if (bestb[c] >= 0) { int dx, dy; for (dy = 0; dy < 16; dy++) for (dx = 0; dx < 16; dx++) sc->swpx[c][dy * 16 + dx] = r3_samp(sc->pa, sc->pb, sc->tiles, sc->pix, 3, px[bestb[c]] + dx, py[bestb[c]] + dy); sc->swok[c] = 1; }
    if (getenv("LANDSTALKER_R3D_LOG")) { for (c = 1; c <= 4; c++) { float bv = 0; int bi = -1, bo = 0; for (b = 1; b < 1024; b++) if (seen[b] && fr[b][c] > bv) { bv = fr[b][c]; bi = b; bo = cnt[b]; } printf("r3d: class %d best block %d fraction %.2f (cells %d)\n", c, bi, bv, bo); } }
    if (getenv("LANDSTALKER_R3D_LOG")) printf("r3d: swatches thatch %d wood %d foliage %d logs %d (block ids)\n", bestb[1], bestb[2], bestb[3], bestb[4]);
}
static int r3_cur_sw;   /* swatch for the triangles the generators add next (0 = flat colours); falls back to the flat colour when the room has no such swatch */
static void r3_ht_add(r3_scene_t *sc, int mat, const uint8_t *rgb, const double *p0, const double *p1, const double *p2, double nx, double ny, double nz) {
    r3_ht_t *t; double ax = p1[0] - p0[0], ay = p1[1] - p0[1], az = p1[2] - p0[2], bx = p2[0] - p0[0], by = p2[1] - p0[1], bz = p2[2] - p0[2], gx = ay * bz - az * by, gy = az * bx - ax * bz, gz = ax * by - ay * bx, ln, sh;
    if (sc->nht >= sc->nht_cap) { sc->nht_cap = sc->nht_cap ? sc->nht_cap * 2 : 512; sc->ht = (r3_ht_t *)realloc(sc->ht, sizeof(r3_ht_t) * sc->nht_cap); if (!sc->ht) { sc->nht = 0; sc->nht_cap = 0; return; } }
    t = &sc->ht[sc->nht++]; t->mat = (uint8_t)mat;
    t->x[0] = (float)p0[0]; t->y[0] = (float)p0[1]; t->z[0] = (float)p0[2]; t->x[1] = (float)p1[0]; t->y[1] = (float)p1[1]; t->z[1] = (float)p1[2]; t->x[2] = (float)p2[0]; t->y[2] = (float)p2[1]; t->z[2] = (float)p2[2];
    ln = sqrt(gx * gx + gy * gy + gz * gz); if (ln < 1e-9) ln = 1; gx /= ln; gy /= ln; gz /= ln; if ((nx != 0 || ny != 0 || nz != 0) && gx * nx + gy * ny + gz * nz < 0) { gx = -gx; gy = -gy; gz = -gz; }   /* the outward direction decides which side is lit */
    sh = 0.50 + 0.50 * fmax(0.0, gx * 0.15 + gy * 0.45 + gz * 0.85);   /* light from above, a little from the south: (0.15, 0.45, 0.85) */
    t->sw = 0; t->ax = 0;
    if (mat == 8 && r3_cur_sw > 0 && r3_cur_sw < 6 && sc->swok[r3_cur_sw]) {   /* textured: stepped light (three bands), planar mapping along the axis the face looks along */
        double q = sh > 0.86 ? 1.0 : sh > 0.68 ? 0.80 : 0.62, ax = fabs(gx), ay = fabs(gy), az = fabs(gz);
        t->mat = 10; t->sw = (uint8_t)r3_cur_sw; t->r = (uint8_t)(q * 255); t->g = t->b = 0; t->ax = (uint8_t)(az >= ax && az >= ay ? 0 : ax >= ay ? 1 : 2);
    } else if (rgb) { t->r = (uint8_t)(rgb[0] * sh); t->g = (uint8_t)(rgb[1] * sh); t->b = (uint8_t)(rgb[2] * sh); } else t->r = t->g = t->b = 0;
}
static void r3_ht_quad(r3_scene_t *sc, int mat, const uint8_t *rgb, double a[3], double b[3], double c[3], double d[3], double nx, double ny, double nz) { r3_ht_add(sc, mat, rgb, a, b, c, nx, ny, nz); r3_ht_add(sc, mat, rgb, a, c, d, nx, ny, nz); }
static void r3_ht_box(r3_scene_t *sc, const uint8_t *rgb, double x0, double x1, double y0, double y1, double z0, double z1) {
    double p[8][3] = { { x0, y0, z0 }, { x1, y0, z0 }, { x1, y1, z0 }, { x0, y1, z0 }, { x0, y0, z1 }, { x1, y0, z1 }, { x1, y1, z1 }, { x0, y1, z1 } };
    r3_ht_quad(sc, 8, rgb, p[4], p[5], p[6], p[7], 0, 0, 1); r3_ht_quad(sc, 8, rgb, p[0], p[1], p[5], p[4], 0, -1, 0); r3_ht_quad(sc, 8, rgb, p[2], p[3], p[7], p[6], 0, 1, 0);
    r3_ht_quad(sc, 8, rgb, p[1], p[2], p[6], p[5], 1, 0, 0); r3_ht_quad(sc, 8, rgb, p[3], p[0], p[4], p[7], -1, 0, 0);
}
/* ---- FULL house model (3D Houses = Model): log walls, corner posts, door and windows, layered thatch roof with ridge cap and crossed ridge poles, own colours and light (no picture colours) ---- */
static void r3_ht_boxf(r3_scene_t *sc, const uint8_t *rgb, double x0, double x1, double y0, double y1, double z0, double z1) { int s = r3_cur_sw; r3_cur_sw = 0; r3_ht_box(sc, rgb, x0, x1, y0, y1, z0, z1); r3_cur_sw = s; }   /* a flat coloured box (door openings, glass) */
static void r3_ht_beam(r3_scene_t *sc, const uint8_t *rgb, const double *a, const double *b, double w);
static void r3_ht_beamw(r3_scene_t *sc, int sw, const uint8_t *rgb, const double *a, const double *b, double w) { int s = r3_cur_sw; r3_cur_sw = sw; r3_ht_beam(sc, rgb, a, b, w); r3_cur_sw = s; }
static void r3_ht_beam(r3_scene_t *sc, const uint8_t *rgb, const double *a, const double *b, double w) {   /* a square beam between two points */
    double d[3] = { b[0] - a[0], b[1] - a[1], b[2] - a[2] }, u[3], v[3], ln, h = w / 2; double P[8][3]; int i;
    ln = sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]); if (ln < 1e-6) return; d[0] /= ln; d[1] /= ln; d[2] /= ln;
    u[0] = d[1]; u[1] = -d[0]; u[2] = 0; if (fabs(u[0]) + fabs(u[1]) < 1e-6) { u[0] = 1; u[1] = 0; u[2] = 0; }
    ln = sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2]); u[0] /= ln; u[1] /= ln; u[2] /= ln;
    v[0] = d[1] * u[2] - d[2] * u[1]; v[1] = d[2] * u[0] - d[0] * u[2]; v[2] = d[0] * u[1] - d[1] * u[0];
    for (i = 0; i < 8; i++) { const double *e = (i & 4) ? b : a; double su = (i & 1) ? h : -h, sv = (i & 2) ? h : -h; P[i][0] = e[0] + u[0] * su + v[0] * sv; P[i][1] = e[1] + u[1] * su + v[1] * sv; P[i][2] = e[2] + u[2] * su + v[2] * sv; }
    r3_ht_quad(sc, 8, rgb, P[0], P[1], P[3], P[2], -d[0], -d[1], -d[2]); r3_ht_quad(sc, 8, rgb, P[4], P[5], P[7], P[6], d[0], d[1], d[2]);
    r3_ht_quad(sc, 8, rgb, P[0], P[1], P[5], P[4], -v[0], -v[1], -v[2]); r3_ht_quad(sc, 8, rgb, P[2], P[3], P[7], P[6], v[0], v[1], v[2]);
    r3_ht_quad(sc, 8, rgb, P[0], P[2], P[6], P[4], -u[0], -u[1], -u[2]); r3_ht_quad(sc, 8, rgb, P[1], P[3], P[7], P[5], u[0], u[1], u[2]);
}
static void r3_make_house_full(r3_scene_t *sc, const r3_roof_t *r, double zb, int doorside, double dooroff) {   /* doorside: 0 none, 1 north (-y), 2 east (+x), 3 south (+y), 4 west (-x); dooroff = the door's centre along the wall (world units) */
    static const uint8_t logA[3] = { 62, 94, 42 }, logB[3] = { 86, 118, 54 }, core[3] = { 44, 68, 32 }, post[3] = { 120, 80, 44 }, dark[3] = { 30, 22, 14 }, frame[3] = { 112, 74, 40 }, glass[3] = { 26, 34, 50 };
    static const uint8_t thatch[3][3] = { { 216, 182, 48 }, { 206, 172, 44 }, { 194, 160, 38 } }, ridge[3] = { 140, 104, 30 }, eaveb[3] = { 150, 116, 32 }, under[3] = { 72, 52, 26 }, gable[3] = { 72, 100, 46 };
    double fx0 = 16.0 * r->cx0, fx1 = 16.0 * (r->cx1 + 1), fy0 = 16.0 * r->cy0, fy1 = 16.0 * (r->cy1 + 1), z0 = r->z0, zr = r->z0 + r->H, xm = (r->X0 + r->X1) / 2, ym = (r->Y0 + r->Y1) / 2, lh = 6.0; int nl = (int)((z0 - zb) / lh + 0.5), k, i, j;
    if (nl < 2) nl = 2; lh = (z0 - zb) / nl;
    r3_cur_sw = 4;                                                                                           /* walls: the log texture of the room's own art (flat olive without it) */
    { double a[3] = { fx0, fy0, zb }, b[3] = { fx1, fy0, zb }, c[3] = { fx1, fy0, z0 }, d[3] = { fx0, fy0, z0 }; r3_ht_quad(sc, 8, logA, a, b, c, d, 0, -1, 0); }
    { double a[3] = { fx0, fy1, zb }, b[3] = { fx1, fy1, zb }, c[3] = { fx1, fy1, z0 }, d[3] = { fx0, fy1, z0 }; r3_ht_quad(sc, 8, logA, a, b, c, d, 0, 1, 0); }
    { double a[3] = { fx0, fy0, zb }, b[3] = { fx0, fy1, zb }, c[3] = { fx0, fy1, z0 }, d[3] = { fx0, fy0, z0 }; r3_ht_quad(sc, 8, logA, a, b, c, d, -1, 0, 0); }
    { double a[3] = { fx1, fy0, zb }, b[3] = { fx1, fy1, zb }, c[3] = { fx1, fy1, z0 }, d[3] = { fx1, fy0, z0 }; r3_ht_quad(sc, 8, logA, a, b, c, d, 1, 0, 0); }
    (void)logB; (void)core; (void)nl; (void)lh; (void)k;
    r3_cur_sw = 2;                                                                                           /* posts, door frames: the wood texture */
    { double cx[2] = { fx0, fx1 }, cy[2] = { fy0, fy1 }; for (i = 0; i < 2; i++) for (j = 0; j < 2; j++) r3_ht_box(sc, post, cx[i] - 3.2, cx[i] + 3.2, cy[j] - 3.2, cy[j] + 3.2, zb, z0 + 3); }   /* corner posts */
    { int s; for (s = 1; s <= 4; s++) {                                                                            /* door (dark, framed) or a window on each of the four walls */
        double cxw = (s == 2 ? fx1 : s == 4 ? fx0 : (s == 1 || s == 3) ? (doorside == s ? dooroff : (fx0 + fx1) / 2) : 0), cyw = (s == 1 ? fy0 : s == 3 ? fy1 : (doorside == s ? dooroff : (fy0 + fy1) / 2)), wl = (s == 1 || s == 3) ? 0 : 1; (void)wl;
        if (s == 2 || s == 4) cyw = (doorside == s) ? dooroff : (fy0 + fy1) / 2;
        { double pr = 4.0, sx = (s == 2) ? 1 : (s == 4) ? -1 : 0, sy = (s == 3) ? 1 : (s == 1) ? -1 : 0;           /* outward direction */
          double ax = (s == 1 || s == 3) ? 1 : 0, ay = (s == 2 || s == 4) ? 1 : 0;                                  /* along the wall */
          if (doorside == s) {
              double dw = 6.5, dh = 27.0;
              r3_ht_boxf(sc, dark, cxw + sx * 0.5 - ax * dw - (sx ? 0 : 0) + (sx > 0 ? 0 : sx * 0) - (sx != 0 ? 0 : 0), cxw + sx * pr + ax * dw, cyw + sy * 0.5 - ay * dw, cyw + sy * pr + ay * dw, zb, zb + dh);
              r3_ht_box(sc, frame, cxw - ax * (dw + 3) + (sx > 0 ? 0 : 0), cxw + sx * (pr + 1) - ax * dw, cyw - ay * (dw + 3), cyw + sy * (pr + 1) - ay * dw, zb, zb + dh + 3);
              r3_ht_box(sc, frame, cxw + ax * dw, cxw + sx * (pr + 1) + ax * (dw + 3), cyw + ay * dw, cyw + sy * (pr + 1) + ay * (dw + 3), zb, zb + dh + 3);
              r3_ht_box(sc, frame, cxw - ax * (dw + 3), cxw + sx * (pr + 1) + ax * (dw + 3), cyw - ay * (dw + 3), cyw + sy * (pr + 1) + ay * (dw + 3), zb + dh, zb + dh + 3.5);
          } else if (r->axis == 0 ? (s == 1 || s == 3) : (s == 2 || s == 4)) {                                      /* windows on the long walls */
              double wz = zb + (z0 - zb) * 0.55, ws = 6.5;
              r3_ht_box(sc, frame, cxw + sx * 0.2 - ax * (ws + 2), cxw + sx * (pr + 0.5) + ax * (ws + 2), cyw + sy * 0.2 - ay * (ws + 2), cyw + sy * (pr + 0.5) + ay * (ws + 2), wz - ws - 2, wz + ws + 2);
              r3_ht_boxf(sc, glass, cxw + sx * 0.4 - ax * ws, cxw + sx * (pr + 1.2) + ax * ws, cyw + sy * 0.4 - ay * ws, cyw + sy * (pr + 1.2) + ay * ws, wz - ws, wz + ws);
          } } } }
    /* roof: layered thatch slopes (bands that alternate in colour and stand out a little), eave bundles, ridge cap, crossed ridge poles, gables, the dark underside of the eaves */
    r3_cur_sw = 1;                                                                                           /* roof: the thatch texture */
    { int nb = 1; double e0, e1, rg, ea[3], eb[3]; (void)e0; (void)e1; (void)rg; (void)ea; (void)eb;
      for (j = 0; j < 2; j++) for (k = 0; k < nb; k++) {
          double t0 = (double)k / nb, t1 = (double)(k + 1) / nb, off = (k & 1) ? 0.8 : 0.0; const uint8_t *c = thatch[(k + j) % 3];
          double A0[3], A1[3], B1[3], B0[3];                    /* along the eave line (a0 -> a1) and the ridge line (b0 -> b1) */
          if (r->axis == 0) { double ey = j ? r->Y1 : r->Y0; A0[0] = r->X0; A0[1] = ey + (ym - ey) * t0; A0[2] = z0 + (zr - z0) * t0; A1[0] = r->X1; A1[1] = A0[1]; A1[2] = A0[2]; B0[0] = r->X0; B0[1] = ey + (ym - ey) * t1; B0[2] = z0 + (zr - z0) * t1; B1[0] = r->X1; B1[1] = B0[1]; B1[2] = B0[2];
              off *= 1; A0[2] += off; A1[2] += off; B0[2] += off; B1[2] += off; r3_ht_quad(sc, 8, c, A0, A1, B1, B0, 0, j ? 0.6 : -0.6, 0.8); }
          else { double ex = j ? r->X1 : r->X0; A0[0] = ex + (xm - ex) * t0; A0[1] = r->Y0; A0[2] = z0 + (zr - z0) * t0; A1[0] = A0[0]; A1[1] = r->Y1; A1[2] = A0[2]; B0[0] = ex + (xm - ex) * t1; B0[1] = r->Y0; B0[2] = z0 + (zr - z0) * t1; B1[0] = B0[0]; B1[1] = r->Y1; B1[2] = B0[2];
              A0[2] += off; A1[2] += off; B0[2] += off; B1[2] += off; r3_ht_quad(sc, 8, c, A0, A1, B1, B0, j ? 0.6 : -0.6, 0, 0.8); }
      } }
    if (r->axis == 0) {
        double a[3] = { r->X0 - 2, ym, zr + 1.2 }, b[3] = { r->X1 + 2, ym, zr + 1.2 }; r3_ht_beam(sc, ridge, a, b, 6.5);                          /* ridge cap */
        r3_ht_beam(sc, eaveb, (double[3]){ r->X0, r->Y0 - 0.5, z0 + 0.5 }, (double[3]){ r->X1, r->Y0 - 0.5, z0 + 0.5 }, 3.5); r3_ht_beam(sc, eaveb, (double[3]){ r->X0, r->Y1 + 0.5, z0 + 0.5 }, (double[3]){ r->X1, r->Y1 + 0.5, z0 + 0.5 }, 3.5);   /* eave bundles */
        for (i = 0; i < 2; i++) { double xe = i ? r->X1 - 4 : r->X0 + 4; r3_ht_beamw(sc, 2, post, (double[3]){ xe, ym - 8, zr + 15 }, (double[3]){ xe, ym + 8, zr - 3 }, 2.6); r3_ht_beamw(sc, 2, post, (double[3]){ xe, ym + 8, zr + 15 }, (double[3]){ xe, ym - 8, zr - 3 }, 2.6); }   /* crossed ridge poles */
        { double g[2] = { fx0, fx1 }; for (i = 0; i < 2; i++) { double p0[3] = { g[i], fy0, z0 }, p1[3] = { g[i], fy1, z0 }, p2[3] = { g[i], ym, zr - 1 }; { int s0 = r3_cur_sw; r3_cur_sw = 4; r3_ht_add(sc, 8, gable, p0, p1, p2, i ? 1 : -1, 0, 0); r3_cur_sw = s0; } } }
        { double q0[3] = { r->X0, r->Y0, z0 - 0.5 }, q1[3] = { r->X1, r->Y0, z0 - 0.5 }, q2[3] = { r->X1, fy0, z0 - 0.5 }, q3[3] = { r->X0, fy0, z0 - 0.5 }; { int s0 = r3_cur_sw; r3_cur_sw = 0; r3_ht_quad(sc, 8, under, q0, q1, q2, q3, 0, 0, -1); r3_cur_sw = s0; } }
        { double q0[3] = { r->X0, fy1, z0 - 0.5 }, q1[3] = { r->X1, fy1, z0 - 0.5 }, q2[3] = { r->X1, r->Y1, z0 - 0.5 }, q3[3] = { r->X0, r->Y1, z0 - 0.5 }; { int s0 = r3_cur_sw; r3_cur_sw = 0; r3_ht_quad(sc, 8, under, q0, q1, q2, q3, 0, 0, -1); r3_cur_sw = s0; } }
    } else {
        double a[3] = { xm, r->Y0 - 2, zr + 1.2 }, b[3] = { xm, r->Y1 + 2, zr + 1.2 }; r3_ht_beam(sc, ridge, a, b, 6.5);
        r3_ht_beam(sc, eaveb, (double[3]){ r->X0 - 0.5, r->Y0, z0 + 0.5 }, (double[3]){ r->X0 - 0.5, r->Y1, z0 + 0.5 }, 3.5); r3_ht_beam(sc, eaveb, (double[3]){ r->X1 + 0.5, r->Y0, z0 + 0.5 }, (double[3]){ r->X1 + 0.5, r->Y1, z0 + 0.5 }, 3.5);
        for (i = 0; i < 2; i++) { double ye = i ? r->Y1 - 4 : r->Y0 + 4; r3_ht_beamw(sc, 2, post, (double[3]){ xm - 8, ye, zr + 15 }, (double[3]){ xm + 8, ye, zr - 3 }, 2.6); r3_ht_beamw(sc, 2, post, (double[3]){ xm + 8, ye, zr + 15 }, (double[3]){ xm - 8, ye, zr - 3 }, 2.6); }
        { double g[2] = { fy0, fy1 }; for (i = 0; i < 2; i++) { double p0[3] = { fx0, g[i], z0 }, p1[3] = { fx1, g[i], z0 }, p2[3] = { xm, g[i], zr - 1 }; { int s0 = r3_cur_sw; r3_cur_sw = 4; r3_ht_add(sc, 8, gable, p0, p1, p2, 0, i ? 1 : -1, 0); r3_cur_sw = s0; } } }
        { double q0[3] = { r->X0, r->Y0, z0 - 0.5 }, q1[3] = { fx0, r->Y0, z0 - 0.5 }, q2[3] = { fx0, r->Y1, z0 - 0.5 }, q3[3] = { r->X0, r->Y1, z0 - 0.5 }; { int s0 = r3_cur_sw; r3_cur_sw = 0; r3_ht_quad(sc, 8, under, q0, q1, q2, q3, 0, 0, -1); r3_cur_sw = s0; } }
        { double q0[3] = { fx1, r->Y0, z0 - 0.5 }, q1[3] = { r->X1, r->Y0, z0 - 0.5 }, q2[3] = { r->X1, r->Y1, z0 - 0.5 }, q3[3] = { fx1, r->Y1, z0 - 0.5 }; { int s0 = r3_cur_sw; r3_cur_sw = 0; r3_ht_quad(sc, 8, under, q0, q1, q2, q3, 0, 0, -1); r3_cur_sw = s0; } }
    }
    r3_cur_sw = 0;
}
static void r3_make_house(r3_scene_t *sc, const r3_roof_t *r) {
    static const uint8_t beam[3] = { 112, 74, 38 }, post[3] = { 122, 84, 46 };
    double fx0 = 16.0 * r->cx0, fx1 = 16.0 * (r->cx1 + 1), fy0 = 16.0 * r->cy0, fy1 = 16.0 * (r->cy1 + 1), z0 = r->z0, zr = r->z0 + r->H, zb = 1e9, xm = (r->X0 + r->X1) / 2, ym = (r->Y0 + r->Y1) / 2; int x, y;
    for (x = r->cx0 - 1; x <= r->cx1 + 1; x++) for (y = r->cy0 - 1; y <= r->cy1 + 1; y++) { if (x >= r->cx0 && x <= r->cx1 && y >= r->cy0 && y <= r->cy1) continue; if (!r3_isvoid(sc, x, y) && sc->zc[y][x] < zb) zb = sc->zc[y][x]; }
    if (zb > z0) zb = z0 - 0; if (zb > 1e8) zb = 0;
    for (y = r->cy0; y <= r->cy1; y++) for (x = r->cx0; x <= r->cx1; x++) sc->repl[y][x] = 1;
    if (sc->houses == 2) {   /* the full model: the door = a low cell of the footprint on its edge (height map: the NPC-blocked cell in front of the house) */
        int ds = 0; double doff = 0;
        for (y = r->cy0; y <= r->cy1; y++) for (x = r->cx0; x <= r->cx1; x++) { if (sc->boxc[y][x] && sc->zc[y][x] == z0) continue; if (ds) continue;
            if (x == r->cx1) { ds = 2; doff = 16.0 * y + 8; } else if (x == r->cx0) { ds = 4; doff = 16.0 * y + 8; } else if (y == r->cy1) { ds = 3; doff = 16.0 * x + 8; } else if (y == r->cy0) { ds = 1; doff = 16.0 * x + 8; } }
        r3_make_house_full(sc, r, zb, ds, doff); return;
    }
    { double a[3] = { fx0, fy0, zb }, b[3] = { fx1, fy0, zb }, c[3] = { fx1, fy0, z0 }, d[3] = { fx0, fy0, z0 }; r3_ht_quad(sc, 1, NULL, a, b, c, d, 0, -1, 0); }      /* walls: picture coloured */
    { double a[3] = { fx0, fy1, zb }, b[3] = { fx1, fy1, zb }, c[3] = { fx1, fy1, z0 }, d[3] = { fx0, fy1, z0 }; r3_ht_quad(sc, 1, NULL, a, b, c, d, 0, 1, 0); }
    { double a[3] = { fx0, fy0, zb }, b[3] = { fx0, fy1, zb }, c[3] = { fx0, fy1, z0 }, d[3] = { fx0, fy0, z0 }; r3_ht_quad(sc, 1, NULL, a, b, c, d, -1, 0, 0); }
    { double a[3] = { fx1, fy0, zb }, b[3] = { fx1, fy1, zb }, c[3] = { fx1, fy1, z0 }, d[3] = { fx1, fy0, z0 }; r3_ht_quad(sc, 1, NULL, a, b, c, d, 1, 0, 0); }
    { double T[6][3][3]; int t, nt = r3_roof_tris(r, T); for (t = 0; t < nt; t++) r3_ht_add(sc, 1, NULL, T[t][0], T[t][1], T[t][2], 0, 0, 1); }   /* roof slopes + gables: picture coloured (the normal only matters for flat parts) */
    (void)xm; (void)ym; (void)beam; (void)zr;   /* Picture mode: the house is made of the ORIGINAL ART only (the flat coloured ridge beam and corner posts of the first version broke the pixel look); the full flat coloured model is 3D Houses = Model */
    (void)post;
}

static void r3_place(r3_scene_t *sc, int model, double X, double Y, double Z, double height, double rotdeg) {   /* a model with its base centre at the world point, scaled to `height` units, turned about the vertical axis */
    const r3_model_t *md = &r3_models[model]; double s, cr = cos(rotdeg * M_PI / 180), sr = sin(rotdeg * M_PI / 180); int t;
    if (md->n <= 0 || md->ymax <= md->ymin) return;
    s = height / (md->ymax - md->ymin);
    for (t = 0; t < md->n; t++) {
        double P[3][3]; int j; uint8_t rgb[3];
        for (j = 0; j < 3; j++) { double xg = md->v[9 * t + 3 * j], yg = md->v[9 * t + 3 * j + 1], zg = md->v[9 * t + 3 * j + 2]; P[j][0] = X + s * (xg * cr - zg * sr); P[j][1] = Y + s * (xg * sr + zg * cr); P[j][2] = Z + s * (yg - md->ymin); }   /* glTF (x, y up, z front) -> world (x east, y south, z up) */
        rgb[0] = md->c[4 * t]; rgb[1] = md->c[4 * t + 1]; rgb[2] = md->c[4 * t + 2];
        r3_cur_sw = (rgb[1] > rgb[0] + 8) ? 3 : (rgb[0] > rgb[1] + 10 ? 2 : 0);   /* greens = foliage swatch, browns = wood swatch (flat colour when the room has none) */
        r3_ht_add(sc, 8, rgb, P[0], P[2], P[1], 0, 0, 0);   /* (the axis swap mirrors the model: the vertex order is turned back) */
    }
    r3_cur_sw = 0;
}
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
    /* OBJECTS: tree blocks = layer A blocks whose opaque pixels are >= 55 % green; a stack of them along the screen vertical (x - 1, y - 1) is one tree; its bottom cell gets a model, the cells become plain ground
       (no box column, no card strips) */
    sc->ntrees = 0;
    if (sc->trees) {
        static int8_t cls[1024]; static int16_t opq[1024]; int x2, y2, k; r3_models_load();
        if (r3_models[0].n > 0) {
            memset(cls, -1, sizeof cls);
            sc->gm = (uint8_t *)calloc((size_t)R3_TW * R3_TH, 1);
            for (y2 = 0; y2 < 74; y2++) for (x2 = 0; x2 < 74; x2++) {
                int b = sc->fgb[y2][x2];
                if (!b) continue;
                if (cls[b] < 0) {
                    int U0 = 16 * (x2 - y2) + 1184 - 16, V0 = 8 * (x2 + y2), dx, dy, op = 0, gr = 0;
                    for (dy = 0; dy < 16; dy++) for (dx = 0; dx < 16; dx++) { uint32_t q = r3_samp(sc->pa, sc->pb, sc->tiles, sc->pix, 3, U0 + dx, V0 + dy); if (q) { int r = (q >> 16) & 255, g = (q >> 8) & 255, bl = q & 255; op++; if (g > r + 14 && g > bl + 8) gr++; } }
                    cls[b] = (op >= 30 && gr * 100 >= op * 55) ? 1 : 0; opq[b] = (int16_t)op;
                }
                if (cls[b] == 1 && sc->gm) {
                    int U0 = 16 * (x2 - y2) + 1184 - 16, V0 = 8 * (x2 + y2), dx, dy;
                    for (dy = 0; dy < 16; dy++) for (dx = 0; dx < 16; dx++) if (U0 + dx >= 0 && U0 + dx < R3_TW && V0 + dy >= 0 && V0 + dy < R3_TH) sc->gm[(size_t)(V0 + dy) * R3_TW + U0 + dx] = 1;
                }
            }
            for (y2 = 0; y2 < 74; y2++) for (x2 = 0; x2 < 74; x2++) {   /* bottom cell of every stack: the next cell down the screen (x + 1, y + 1) is not a tree block */
                int b = sc->fgb[y2][x2], cnt = 1;
                if (!b || cls[b] != 1) continue;
                if (x2 + 1 < 74 && y2 + 1 < 74 && sc->fgb[y2 + 1][x2 + 1] && cls[sc->fgb[y2 + 1][x2 + 1]] == 1) continue;
                for (k = 1; x2 - k >= 0 && y2 - k >= 0 && sc->fgb[y2 - k][x2 - k] && cls[sc->fgb[y2 - k][x2 - k]] == 1 && cnt < 4; k++) cnt++;
                { int topb = sc->fgb[y2 - (cnt - 1)][x2 - (cnt - 1)]; int pine = cnt >= 2 && opq[topb] < 150;   /* a pine ends in a tip (a partly filled top block), a hedge is made of full blocks */
                  if (sc->ntrees < 3000) { sc->tree[sc->ntrees][0] = x2; sc->tree[sc->ntrees][1] = y2; sc->tree[sc->ntrees][2] = cnt; sc->tree[sc->ntrees][3] = pine; sc->ntrees++; } }
            }
            for (k = 0; k < sc->ntrees; k++) {   /* the tree cells become plain ground at the height of their lowest neighbour (no box column) */
                int cx2 = sc->tree[k][0], cy2 = sc->tree[k][1], c, dxx, dyy;
                for (c = 0; c < sc->tree[k][2]; c++) { int X = cx2 - c, Y = cy2 - c; double lo = 1e9; if (X < 0 || Y < 0 || sc->hm[Y][X] == 0x4000) continue;
                    for (dyy = -1; dyy <= 1; dyy++) for (dxx = -1; dxx <= 1; dxx++) { int XX = X + dxx, YY = Y + dyy; if ((dxx || dyy) && XX >= 0 && YY >= 0 && XX < 74 && YY < 74 && sc->hm[YY][XX] != 0x4000 && sc->zc[YY][XX] < lo) lo = sc->zc[YY][XX]; }
                    if (lo < 1e8 && lo < sc->zc[Y][X]) sc->zc[Y][X] = lo; sc->boxc[Y][X] = 0; }
            }
        }
    }
    r3_find_swatches(sc);
    r3_find_roofs(sc, &c);
    if (sc->houses) { int r; for (r = 0; r < sc->nroofs; r++) r3_make_house(sc, &sc->roofs[r]); }
    /* FENCES (3D Objects): layer A blocks that are wood coloured (>= 28 % brown, < 10 % green, nearly full) outside the houses; each such cell gets stakes + rails along its axis (neighbouring fence cells decide: along x if (x +- 1, y) is one, else along y) */
    sc->nfence = 0;
    if (sc->objects) {
        static int8_t fc[1024]; int x2, y2; memset(fc, -1, sizeof fc);
        for (y2 = 0; y2 < 74; y2++) for (x2 = 0; x2 < 74; x2++) {
            int b = sc->fgb[y2][x2];
            if (!b || sc->repl[y2][x2]) continue;
            if (fc[b] < 0) {
                int U0 = 16 * (x2 - y2) + 1184 - 16, V0 = 8 * (x2 + y2), dx, dy, op = 0, wd = 0, gr = 0;
                for (dy = 0; dy < 16; dy++) for (dx = 0; dx < 16; dx++) { uint32_t q = r3_samp(sc->pa, sc->pb, sc->tiles, sc->pix, 3, U0 + dx, V0 + dy); if (q) { int r = (q >> 16) & 255, g = (q >> 8) & 255, bl = q & 255; op++; if (r >= g && g >= bl && r >= 110 && r - bl >= 40 && g <= 150) wd++; if (g > r + 14 && g > bl + 8) gr++; } }
                fc[b] = (op >= 100 && wd * 100 >= op * 28 && gr * 100 < op * 10) ? 1 : 0;
            }
            if (fc[b] == 1 && sc->nfence < 3000) { sc->fence[sc->nfence][0] = x2; sc->fence[sc->nfence][1] = y2; sc->nfence++; }
        }
        if (sc->nfence > 0) {
            int k; if (!sc->gm) sc->gm = (uint8_t *)calloc((size_t)R3_TW * R3_TH, 1);
            for (k = 0; k < sc->nfence; k++) {
                int cx2 = sc->fence[k][0], cy2 = sc->fence[k][1], ax = 0, dxx, dyy, X = cx2, Y = cy2; double lo = 1e9;
                { int isf = 0, ixp = 0, iyp = 0, j; for (j = 0; j < sc->nfence; j++) { int fx = sc->fence[j][0], fy = sc->fence[j][1]; if (fy == cy2 && (fx == cx2 + 1 || fx == cx2 - 1)) ixp = 1; if (fx == cx2 && (fy == cy2 + 1 || fy == cy2 - 1)) iyp = 1; } (void)isf; ax = (ixp || !iyp) ? 0 : 1; }
                sc->fence[k][2] = ax;
                for (dyy = -1; dyy <= 1; dyy++) for (dxx = -1; dxx <= 1; dxx++) { int XX = X + dxx, YY = Y + dyy; if ((dxx || dyy) && XX >= 0 && YY >= 0 && XX < 74 && YY < 74 && sc->hm[YY][XX] != 0x4000 && !(sc->hm[YY][XX] & 0x4000) && sc->zc[YY][XX] < lo) lo = sc->zc[YY][XX]; }   /* the fence stands on the lowest walkable neighbour */
                if (sc->hm[Y][X] != 0x4000 && lo < 1e8) { sc->zc[Y][X] = lo; sc->boxc[Y][X] = 0; }
                if (sc->gm) { int U0 = 16 * (cx2 - cy2) + 1184 - 16, V0 = 8 * (cx2 + cy2), dx, dy; for (dy = 0; dy < 16; dy++) for (dx = 0; dx < 16; dx++) if (U0 + dx >= 0 && U0 + dx < R3_TW && V0 + dy >= 0 && V0 + dy < R3_TH) sc->gm[(size_t)(V0 + dy) * R3_TW + U0 + dx] = 1; }
            }
            r3_cur_sw = 2;   /* wood swatch */
            for (k = 0; k < sc->nfence; k++) {   /* the models: stakes with pointed tops, two rails */
                int cx2 = sc->fence[k][0], cy2 = sc->fence[k][1], ax = sc->fence[k][2], i; double z = sc->hm[cy2][cx2] == 0x4000 ? 0 : sc->zc[cy2][cx2];
                static const uint8_t wood[3][3] = { { 192, 140, 80 }, { 170, 122, 68 }, { 206, 152, 90 } }, rail[3] = { 152, 106, 58 };
                double mid = ax ? 16.0 * cx2 + 8 : 16.0 * cy2 + 8, s0 = ax ? 16.0 * cy2 : 16.0 * cx2;
                for (i = 0; i < 5; i++) {
                    double s = s0 + 1.6 + 3.2 * i, h = 24 + ((cx2 * 7 + cy2 * 5 + i * 3) % 7), wx = ax ? mid : s, wy = ax ? s : mid, w = 2.6; const uint8_t *c = wood[(i + cx2 + cy2) % 3];
                    double a[3] = { wx, wy, z }, b[3] = { wx, wy, z + h }, tip[3] = { wx, wy, z + h + 4.5 }, q0[3] = { wx - w / 2, wy - w / 2, z + h }, q1[3] = { wx + w / 2, wy - w / 2, z + h }, q2[3] = { wx + w / 2, wy + w / 2, z + h }, q3[3] = { wx - w / 2, wy + w / 2, z + h };
                    r3_ht_beam(sc, c, a, b, w);
                    r3_ht_add(sc, 8, c, q0, q1, tip, 0, -1, 0.6); r3_ht_add(sc, 8, c, q1, q2, tip, 1, 0, 0.6); r3_ht_add(sc, 8, c, q2, q3, tip, 0, 1, 0.6); r3_ht_add(sc, 8, c, q3, q0, tip, -1, 0, 0.6);
                }
                { double p0[3], p1[3], p2[3], p3[3]; double off = ax ? 1.8 : 1.8;   /* two horizontal rails on one side */
                  p0[2] = p1[2] = z + 8; p2[2] = p3[2] = z + 17;
                  if (ax) { p0[0] = p1[0] = p2[0] = p3[0] = mid + off; p0[1] = p2[1] = s0; p1[1] = p3[1] = s0 + 16; } else { p0[1] = p1[1] = p2[1] = p3[1] = mid + off; p0[0] = p2[0] = s0; p1[0] = p3[0] = s0 + 16; }
                  r3_ht_beam(sc, rail, p0, p1, 1.8); r3_ht_beam(sc, rail, p2, p3, 1.8); }
            }
            r3_cur_sw = 0;
        }
    }
    /* the geometry as quads + the coverage of the original view */
    sc->hw = (float *)calloc((size_t)R3_TW * R3_TH * 3, 4); sc->cov = (uint8_t *)calloc((size_t)R3_TW * R3_TH, 1); sc->hb = (uint8_t *)calloc((size_t)R3_TW * R3_TH, 1); sc->q = (r3_quad_t *)malloc(sizeof(r3_quad_t) * R3_NQ);
    if (!sc->hw || !sc->cov || !sc->hb || !sc->q) return;
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
        double z = r3_cz(sc, x, y), x0 = 16.0 * x, y0 = 16.0 * y, x1 = x0 + 16, y1 = y0 + 16; int mode = sc->boxc[y][x] ? 1 : 0, k;
        if (r3_isvoid(sc, x, y) || sc->repl[y][x]) continue;
        r3_addq(sc, mode, mode == 0 ? 2 : 3, x0, y0, z, x1, y0, z, x1, y1, z, x0, y1, z);   /* dark 2 = ground top face: soil colour where the picture has none; 3 = top of a box column (horizontal faces take their shadow from gmask) */
        { double zn = r3_cz(sc, x + 1, y); if (zn < z) r3_addq(sc, mode, 0, x1, y0, z, x1, y1, z, x1, y1, zn, x1, y0, zn); }
        { double zn = r3_cz(sc, x, y + 1); if (zn < z) r3_addq(sc, mode, 0, x0, y1, z, x1, y1, z, x1, y1, zn, x0, y1, zn); }
        for (k = 0; k < sc->nq; k++) (void)k;
    }
    for (y = 0; y < sc->nq; y++) {   /* coverage pass from the original camera (quads -> triangles) */
        const r3_quad_t *q = &sc->q[y]; int t;
        for (t = 0; t < 2; t++) { int idx[3] = { 0, t ? 2 : 1, t ? 3 : 2 }, j; double P[3][3]; for (j = 0; j < 3; j++) { P[j][0] = q->wx[idx[j]]; P[j][1] = q->wy[idx[j]]; P[j][2] = q->wz[idx[j]]; } c.box = q->mode == 1; r3_rast(P, 1, r3_hit_cb, &c); }
    }
    if (!sc->houses) { int r; for (r = 0; r < sc->nroofs; r++) { double T[6][3][3]; int t, nt = r3_roof_tris(&sc->roofs[r], T); c.box = 1; for (t = 0; t < nt; t++) r3_rast(T[t], 1, r3_hit_cb, &c); } }
    else { int t; c.box = 1; for (t = 0; t < sc->nht; t++) { double P[3][3]; int j; for (j = 0; j < 3; j++) { P[j][0] = sc->ht[t].x[j]; P[j][1] = sc->ht[t].y[j]; P[j][2] = sc->ht[t].z[j]; } r3_rast(P, 1, r3_hit_cb, &c); } }
    /* card strips: opaque picture pixels the box geometry does not carry (uncovered, or layer A pixels on plain ground), anchored at the foot of their run, one depth per card */
    {
        int32_t *lab = (int32_t *)calloc((size_t)R3_TW * R3_TH, 4); int *stk = (int *)malloc(sizeof(int) * R3_TW * 4); int U, nl = 0, nr = 0, cap = 40000; typedef struct { int U, y, n, lab; float bx, by, bz; } run_t; run_t *runs = (run_t *)malloc(sizeof(run_t) * cap);
        int *cnt, *off; float *dpool; 
#define R3NEED0(X, Y) (r3_opaque(sc, (X), (Y)) && (!sc->cov[(size_t)(Y) * R3_TW + (X)] || (!sc->hb[(size_t)(Y) * R3_TW + (X)] && r3_opaqueA(sc, (X), (Y)))))
#define R3NEED(X, Y) (R3NEED0((X), (Y)) && !(sc->gm && sc->gm[(size_t)(Y) * R3_TW + (X)]))   /* tree block pixels are carried by models */
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
        if (sc->trees && sc->ntrees > 0) { int k; for (k = 0; k < sc->ntrees; k++) {   /* a model on the ground of the stack's bottom cell */
            int cx2 = sc->tree[k][0], cy2 = sc->tree[k][1], cnt = sc->tree[k][2]; double X = 16.0 * cx2 + 8, Y = 16.0 * cy2 + 8, Z = (sc->hm[cy2][cx2] == 0x4000) ? 0 : sc->zc[cy2][cx2]; int pine = sc->tree[k][3], kind = pine ? 0 : 1; double h = pine ? 10 + 14.0 * cnt : 8 + 7.0 * cnt;
            if (r3_models[kind].n > 0) r3_place(sc, kind, X, Y, Z, h, (double)((cx2 * 53 + cy2 * 17) % 360)); } }
        free(cnt); free(off); free(dpool); free(lab); free(stk); free(runs);
    }
}

static inline float r3_shadow_tap(const r3_scene_t *sc, double a, double b, double d) {
    int ia = (int)(a - sc->sma), ib = (int)(b - sc->smb);
    if (ia < 0 || ib < 0 || ia >= sc->smw || ib >= sc->smh) return 1.0f;
    return d < sc->smap[(size_t)ib * sc->smw + ia] - 2.0 ? 0.0f : 1.0f;
}
static inline float r3_shadow_at(const r3_scene_t *sc, double X, double Y, double Z) {
    double d = X * r3_Lx + Y * r3_Ly + Z * r3_Lz, a = X * r3_e1x + Y * r3_e1y, b = X * r3_e2x + Y * r3_e2y + Z * r3_e2z;
    return r3_shadow_tap(sc, a, b, d);
}
static inline float r3_shadow_pcf(const r3_scene_t *sc, double X, double Y, double Z) {   /* 5 taps, for the pre computed ground mask */
    double d = X * r3_Lx + Y * r3_Ly + Z * r3_Lz, a = X * r3_e1x + Y * r3_e1y, b = X * r3_e2x + Y * r3_e2y + Z * r3_e2z;
    return 0.2f * (r3_shadow_tap(sc, a, b, d) + r3_shadow_tap(sc, a + 1, b + 1, d) + r3_shadow_tap(sc, a - 1, b + 1, d) + r3_shadow_tap(sc, a + 1, b - 1, d) + r3_shadow_tap(sc, a - 1, b - 1, d));
}
static void r3_sh_tri(r3_scene_t *sc, const double P[3][3]) {   /* one occluder triangle into the shadow map: max light depth per texel */
    double a[3], b[3], d[3]; int j, x0, x1, y0, y1, x, y;
    for (j = 0; j < 3; j++) { a[j] = P[j][0] * r3_e1x + P[j][1] * r3_e1y - sc->sma; b[j] = P[j][0] * r3_e2x + P[j][1] * r3_e2y + P[j][2] * r3_e2z - sc->smb; d[j] = P[j][0] * r3_Lx + P[j][1] * r3_Ly + P[j][2] * r3_Lz; }
    { double den = (b[1] - b[2]) * (a[0] - a[2]) + (a[2] - a[1]) * (b[0] - b[2]), idn;
      if (fabs(den) < 1e-9) return;
      idn = 1.0 / den; x0 = (int)floor(fmin(a[0], fmin(a[1], a[2]))); x1 = (int)ceil(fmax(a[0], fmax(a[1], a[2]))); y0 = (int)floor(fmin(b[0], fmin(b[1], b[2]))); y1 = (int)ceil(fmax(b[0], fmax(b[1], b[2])));
      if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0; if (x1 >= sc->smw) x1 = sc->smw - 1; if (y1 >= sc->smh) y1 = sc->smh - 1;
      for (y = y0; y <= y1; y++) for (x = x0; x <= x1; x++) {
          double px = x + 0.5, py = y + 0.5, l1 = ((b[1] - b[2]) * (px - a[2]) + (a[2] - a[1]) * (py - b[2])) * idn, l2 = ((b[2] - b[0]) * (px - a[2]) + (a[0] - a[2]) * (py - b[2])) * idn, l3 = 1 - l1 - l2, dd;
          if (l1 < -1e-6 || l2 < -1e-6 || l3 < -1e-6) continue;
          dd = l1 * d[0] + l2 * d[1] + l3 * d[2];
          if (dd > sc->smap[(size_t)y * sc->smw + x]) sc->smap[(size_t)y * sc->smw + x] = (float)dd;
      } }
}
static void r3_sh_build(r3_scene_t *sc) {
    double mina = 1e30, maxa = -1e30, minb = 1e30, maxb = -1e30; int i, cx, cy, cz;
    r3_sun_init();
    for (cx = 0; cx < 2; cx++) for (cy = 0; cy < 2; cy++) for (cz = 0; cz < 2; cz++) { double X = cx ? 1184 : 0, Y = cy ? 1184 : 0, Z = cz ? 300 : -400, a = X * r3_e1x + Y * r3_e1y, b = X * r3_e2x + Y * r3_e2y + Z * r3_e2z; if (a < mina) mina = a; if (a > maxa) maxa = a; if (b < minb) minb = b; if (b > maxb) maxb = b; }
    sc->sma = mina; sc->smb = minb; sc->smw = (int)(maxa - mina) + 2; sc->smh = (int)(maxb - minb) + 2;
    sc->smap = (float *)malloc((size_t)sc->smw * sc->smh * sizeof(float)); if (!sc->smap) { sc->light = 0; return; }
    for (i = 0; i < sc->smw * sc->smh; i++) sc->smap[i] = -1e30f;
    for (i = 0; i < sc->nq; i++) { const r3_quad_t *q = &sc->q[i]; double P[3][3]; int t; for (t = 0; t < 2; t++) { int idx[3] = { 0, t ? 2 : 1, t ? 3 : 2 }, j; for (j = 0; j < 3; j++) { P[j][0] = q->wx[idx[j]]; P[j][1] = q->wy[idx[j]]; P[j][2] = q->wz[idx[j]]; } r3_sh_tri(sc, P); } }
    for (i = 0; i < sc->nht; i++) { double P[3][3]; int j; for (j = 0; j < 3; j++) { P[j][0] = sc->ht[i].x[j]; P[j][1] = sc->ht[i].y[j]; P[j][2] = sc->ht[i].z[j]; } r3_sh_tri(sc, P); }
    if (!sc->houses) for (i = 0; i < sc->nroofs; i++) { double T[6][3][3]; int t, nt = r3_roof_tris(&sc->roofs[i], T); for (t = 0; t < nt; t++) r3_sh_tri(sc, T[t]); }
    for (i = 0; i < sc->ns; i++) {   /* cards: upright strips (the flat ones are ground) */
        const r3_strip_t *s = &sc->st[i]; double bx = s->bx, by = s->by, bz = s->bz, h = 0.5 / R3K2 * 1.35, r = 1 / R3K2, P[3][3]; int n = s->n;
        if (n >= 110) continue;
        P[0][0] = bx - r * h; P[0][1] = by + r * h; P[0][2] = bz; P[1][0] = bx + r * h; P[1][1] = by - r * h; P[1][2] = bz; P[2][0] = bx + r * h; P[2][1] = by - r * h; P[2][2] = bz + n; r3_sh_tri(sc, P);
        P[1][0] = bx - r * h; P[1][1] = by + r * h; P[1][2] = bz + n; r3_sh_tri(sc, P);
    }
    sc->gmask = (uint8_t *)malloc(1184 * 1184); if (sc->gmask) memset(sc->gmask, 255, 1184 * 1184);
    if (sc->gmask) for (i = 0; i < sc->nq; i++) {   /* horizontal faces: the shadow per world unit, soft */
        const r3_quad_t *q = &sc->q[i]; int tx, ty; double X0, Y0;
        if (!(q->wz[0] == q->wz[1] && q->wz[1] == q->wz[2] && q->wz[2] == q->wz[3])) continue;
        X0 = fmin(fmin(q->wx[0], q->wx[1]), fmin(q->wx[2], q->wx[3])); Y0 = fmin(fmin(q->wy[0], q->wy[1]), fmin(q->wy[2], q->wy[3]));
        for (ty = 0; ty < 16; ty++) for (tx = 0; tx < 16; tx++) { int X = (int)X0 + tx, Y = (int)Y0 + ty; if (X >= 0 && Y >= 0 && X < 1184 && Y < 1184) sc->gmask[(size_t)Y * 1184 + X] = (uint8_t)(r3_shadow_pcf(sc, X + 0.5, Y + 0.5, q->wz[0] + 0.01) * 255.0f); }
    }
}
static int r3_worker(void *u) {
    r3_scene_t *sc = (r3_scene_t *)u; uint64_t t0 = SDL_GetPerformanceCounter();
    r3_build(sc);
    if (sc->light && sc->q) r3_sh_build(sc);
    if (getenv("LANDSTALKER_R3D_LOG")) printf("r3d: scene built in %.0f ms: %d quads, %d roofs, %d card strips (hash %08x)\n", (double)(SDL_GetPerformanceCounter() - t0) * 1e3 / (double)SDL_GetPerformanceFrequency(), sc->nq, sc->nroofs, sc->ns, sc->hash);
    r3_done = 1; return 0;
}
static void r3_free(r3_scene_t *sc) { if (!sc) return; free(sc->gm); free(sc->gmask); free(sc->smap); free(sc->ht); free(sc->hw); free(sc->cov); free(sc->hb); free(sc->q); free(sc->st); free(sc); }
static int r3_bright(const uint32_t *pix) { int i, best = 0; for (i = 1; i < 64; i++) { int s = ((pix[i] >> 16) & 255) + ((pix[i] >> 8) & 255) + (pix[i] & 255); if (s > best) best = s; } return best >= 500; }   /* not in a fade */
static void r3_request(const lk_o3d_src_t *src, uint32_t hash, uint32_t base) {
    int x, y, cells = 0; r3_scene_t *sc;
    if (r3_thread && r3_done) { SDL_WaitThread(r3_thread, NULL); r3_thread = NULL; r3_done = 0; r3_busy = 0; r3_free(r3_active); r3_active = r3_work; r3_work = NULL; }   /* hand over */
    if (r3_busy || hash == r3_req_hash || !r3_bright(src->pix)) return;
    for (y = 0; y < 152; y += 4) for (x = 0; x < 304; x += 4) cells += (src->pa[y][x] | src->pb[y][x]) >> 16 & 1;
    if (cells < 20) return;                                   /* no room picture (load / black frame) */
    sc = (r3_scene_t *)calloc(1, sizeof *sc); if (!sc) return;
    sc->hash = hash; sc->base_hash = base; sc->houses = lk_r3d_houses_get(); sc->objects = lk_r3d_objects_get(); sc->trees = lk_r3d_trees_get(); sc->light = lk_r3d_light_get(); memcpy(sc->tiles, src->tiles, sizeof sc->tiles); memcpy(sc->pa, src->pa, sizeof sc->pa); memcpy(sc->pb, src->pb, sizeof sc->pb); memcpy(sc->pix, src->pix, sizeof sc->pix);
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { sc->hm[y][x] = lk_o3d_hm(x, y); sc->fgb[y][x] = lk_o3d_blk(0, x, y); }
    r3_work = sc; r3_req_hash = hash; r3_busy = 1; r3_done = 0;
    if (getenv("LANDSTALKER_R3D_SYNC")) { r3_worker(sc); r3_thread = NULL; r3_done = 0; r3_busy = 0; r3_free(r3_active); r3_active = sc; r3_work = NULL; return; }   /* test aid: build now (headless screenshots) */
    r3_thread = SDL_CreateThread(r3_worker, "lk_r3d", sc);
    if (!r3_thread) { r3_busy = 0; r3_work = NULL; r3_free(sc); }
}

/* ---- rendering ---- */
typedef struct { double x, y, w, u, v, X, Y, Z; } r3_vtx;   /* screen x, y, view depth w, picture position u, v, world position X, Y, Z */
static double r3_fx, r3_fy, r3_ox, r3_oy, r3_S, r3_cy, r3_sy, r3_cp, r3_sp;   /* focus, screen offset, scale, yaw cos / sin, pitch cos / sin */
static void r3_proj(double wx, double wy, double z, double *sx, double *sy, double *w) {
    double dx = wx - r3_fx, dy = wy - r3_fy, xr = dx * r3_cy - dy * r3_sy, yr = dx * r3_sy + dy * r3_cy, u = (xr - yr) / R3K2, dd = (xr + yr) / R3K2;
    *sx = r3_S * R3K2 * u + r3_ox; *sy = r3_S * 1.22474487139 * (dd * r3_sp - z * r3_cp) + r3_oy; *w = dd * r3_cp + z * r3_sp;
}
static uint32_t r3_flat; static const uint32_t *r3_tex; static int r3_texax, r3_texq;   /* mode 10: the swatch, its planar axis and the stepped shade (of 255) */
static r3_vtx r3_mk(double wx, double wy, double z) { r3_vtx p; r3_proj(wx, wy, z, &p.x, &p.y, &p.w); p.u = wx - wy + 1184; p.v = (wx + wy) / 2 - z; p.X = wx; p.Y = wy; p.Z = z; return p; }
static void r3_tri(r3_vtx a, r3_vtx b, r3_vtx c, int mode, int dark, const lk_o3d_src_t *src) {   /* scanline rasteriser: spans from the edges, w / u / v by their gradients */
    double den = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y), idn, ymin = fmin(a.y, fmin(b.y, c.y)), ymax = fmax(a.y, fmax(b.y, c.y)), xmin3 = fmin(a.x, fmin(b.x, c.x)), xmax3 = fmax(a.x, fmax(b.x, c.x));
    double dl1x, dl1y, dl2x, dl2y, dwx, dwy, dux, duy, dvx, dvy, dXx, dYx, dZx; int y0, y1, y, lit = r3_shsc && (mode == 0 || mode == 1 || mode == 8 || mode == 10), horiz = dark == 2 || dark == 3, needw;
    if (fabs(den) < 1e-9 || xmax3 < 0 || xmin3 > r3_iw || ymax < 0 || ymin > r3_ih) return;
    idn = 1.0 / den; dl1x = (b.y - c.y) * idn; dl1y = (c.x - b.x) * idn; dl2x = (c.y - a.y) * idn; dl2y = (a.x - c.x) * idn;
    dwx = dl1x * (a.w - c.w) + dl2x * (b.w - c.w); dwy = dl1y * (a.w - c.w) + dl2y * (b.w - c.w);
    dux = dl1x * (a.u - c.u) + dl2x * (b.u - c.u); duy = dl1y * (a.u - c.u) + dl2y * (b.u - c.u);
    dvx = dl1x * (a.v - c.v) + dl2x * (b.v - c.v); dvy = dl1y * (a.v - c.v) + dl2y * (b.v - c.v);
    dXx = dl1x * (a.X - c.X) + dl2x * (b.X - c.X); dYx = dl1x * (a.Y - c.Y) + dl2x * (b.Y - c.Y); dZx = dl1x * (a.Z - c.Z) + dl2x * (b.Z - c.Z);
    needw = lit || mode == 10;
    y0 = (int)ceil(ymin - 0.5); y1 = (int)floor(ymax - 0.5); if (y0 < 0) y0 = 0; if (y1 >= r3_ih) y1 = r3_ih - 1;
    for (y = y0; y <= y1; y++) {
        double py = y + 0.5, xl = 1e30, xr = -1e30, l1, l2, w, u, v, X = 0, Y = 0, Z = 0; int xs, xe, x, k; const r3_vtx *P[3] = { &a, &b, &c };
        for (k = 0; k < 3; k++) { const r3_vtx *p = P[k], *q = P[(k + 1) % 3]; if ((p->y <= py && q->y > py) || (q->y <= py && p->y > py)) { double xx = p->x + (py - p->y) * (q->x - p->x) / (q->y - p->y); if (xx < xl) xl = xx; if (xx > xr) xr = xx; } }
        if (xl > xr) continue;
        xs = (int)ceil(xl - 0.5); xe = (int)floor(xr - 0.5); if (xs < 0) xs = 0; if (xe >= r3_iw) xe = r3_iw - 1; if (xs > xe) continue;
        l1 = ((b.y - c.y) * (xs + 0.5 - c.x) + (c.x - b.x) * (py - c.y)) * idn; l2 = ((c.y - a.y) * (xs + 0.5 - c.x) + (a.x - c.x) * (py - c.y)) * idn;
        w = c.w + l1 * (a.w - c.w) + l2 * (b.w - c.w); u = c.u + l1 * (a.u - c.u) + l2 * (b.u - c.u); v = c.v + l1 * (a.v - c.v) + l2 * (b.v - c.v);
        if (needw) { X = c.X + l1 * (a.X - c.X) + l2 * (b.X - c.X); Y = c.Y + l1 * (a.Y - c.Y) + l2 * (b.Y - c.Y); Z = c.Z + l1 * (a.Z - c.Z) + l2 * (b.Z - c.Z); }
        { float *zr = r3_zb + (size_t)y * r3_iw; uint32_t *ir = r3_img + (size_t)y * r3_iw;
          for (x = xs; x <= xe; x++, w += dwx, u += dux, v += dvx, X += dXx, Y += dYx, Z += dZx) {
            uint32_t col; int tu, tv;
            if (w <= zr[x]) continue;
            tu = (int)(u + 4096.0) - 4096; tv = (int)(v + 4096.0) - 4096;   /* floor for the small negative values at the edges */
            if (mode == 10) { double pa, pb; int su, sv; uint32_t tx, k = (uint32_t)r3_texq;
                if (r3_texax == 0) { pa = X; pb = Y; } else if (r3_texax == 1) { pa = Y; pb = -Z; } else { pa = X; pb = -Z; }
                su = ((int)(pa + 4096.0) - 4096) & 15; sv = ((int)(pb + 4096.0) - 4096) & 15; tx = r3_tex[sv * 16 + su];
                col = 0xFF000000u | ((((tx >> 16) & 255) * k / 255) << 16) | ((((tx >> 8) & 255) * k / 255) << 8) | (((tx & 255) * k / 255)); }   /* a texel of the room's own art, one texel = one world unit = one game pixel */
            else if (mode == 8) col = r3_flat;
            else if (mode == 9) { if (tu < 0 || tv < 0 || tu >= 416 || tv >= 224) continue; col = lk_hd_sprc[tv * 416 + tu]; if (!col) continue; }   /* figure strip: u = column + 48, v = row of the 1x frame */
            else { col = r3_samp(src->pa, src->pb, src->tiles, src->pix, mode == 0 ? 0 : 1, tu, tv); if (!col) { if (mode == 0 && dark == 2) col = 0xFF483422u; else continue; } }
            if (lit) { float f = (horiz && r3_shsc->gmask) ? ((X >= 0 && Y >= 0 && X < 1184 && Y < 1184) ? r3_shsc->gmask[(size_t)(int)Y * 1184 + (int)X] * (1.0f / 255.0f) : 1.0f) : r3_shadow_at(r3_shsc, X, Y, Z); if (f < 1.0f) { float k2 = 1.0f - f; uint32_t r = (col >> 16) & 255, g = (col >> 8) & 255, bl = col & 255; r = (uint32_t)(r * (1.0f - 0.52f * k2)); g = (uint32_t)(g * (1.0f - 0.47f * k2)); bl = (uint32_t)(bl * (1.0f - 0.30f * k2)); col = 0xFF000000u | (r << 16) | (g << 8) | bl; } }   /* shadow: darker, a little blue */
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
    lk_o3d_src_t src; const int N = lk_r3d_on() == 2 ? 1 : 2; int W = sw * N, H = 224 * N, x, y, ok, i; uint32_t hash, base; const r3_scene_t *sc;
    if (!lk_r3d_on()) return NULL;
    ok = lk_o3d_get(&src); hash = ok ? lk_o3d_hash() : 0; base = hash;
    if (ok && lk_r3d_houses_get()) hash ^= 0x5bd1e995u;
    if (ok && lk_r3d_light_get()) hash ^= 0x3c6ef372u;
    if (ok && lk_r3d_objects_get()) hash ^= 0x7a3b19c5u;
    if (ok && lk_r3d_trees_get()) hash ^= 0x2c91d7e3u;   /* the scene differs with 3D Houses on */
    if (ok) r3_request(&src, hash, base);
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
    { double Uc = src.u0 + sw / 2 - e, Vc = src.v0 + 112, zoom = 1; { const char *ez = getenv("LANDSTALKER_R3D_ZOOM"), *ef = getenv("LANDSTALKER_R3D_FOCUS"); double fu = 0, fv = 0; if (ez) zoom = atof(ez); if (ef && sscanf(ef, "%lf,%lf", &fu, &fv) == 2) { Uc += fu; Vc += fv; } }   /* test aids: zoom out / pan to look at a whole village */            /* the ground point at the middle of the screen is the centre of the turn */
      r3_fx = (Uc - 1184 + 2 * Vc) / 2; r3_fy = (2 * Vc - (Uc - 1184)) / 2; r3_S = N * zoom; r3_ox = W / 2.0; r3_oy = H / 2.0; r3_cy = cos(r3_yaw); r3_sy = sin(r3_yaw); r3_cp = cos(atan(1.0 / R3K2) + r3_pitch); r3_sp = sin(atan(1.0 / R3K2) + r3_pitch); }
    r3_t[0] = SDL_GetPerformanceCounter(); r3_shsc = (sc->light && sc->smap) ? sc : NULL; if (r3_shsc) r3_sun_init();
    for (i = 0; i < sc->nq; i++) {
        const r3_quad_t *q = &sc->q[i]; r3_vtx v[4]; int k;
        for (k = 0; k < 4; k++) v[k] = r3_mk(q->wx[k], q->wy[k], q->wz[k]);
        r3_tri(v[0], v[1], v[2], q->mode, q->dark, &src); r3_tri(v[0], v[2], v[3], q->mode, q->dark, &src);
    }
    for (i = 0; i < sc->nht; i++) { const r3_ht_t *t = &sc->ht[i]; r3_vtx a = r3_mk(t->x[0], t->y[0], t->z[0]), b = r3_mk(t->x[1], t->y[1], t->z[1]), c = r3_mk(t->x[2], t->y[2], t->z[2]); if (t->mat == 10) { r3_tex = sc->swpx[t->sw]; r3_texax = t->ax; r3_texq = t->r; r3_tri(a, b, c, 10, 0, &src); } else if (t->mat == 8) { r3_flat = 0xFF000000u | ((uint32_t)t->r << 16) | ((uint32_t)t->g << 8) | t->b; r3_tri(a, b, c, 8, 0, &src); } else r3_tri(a, b, c, 1, 0, &src); }
    if (!sc->houses) for (i = 0; i < sc->nroofs; i++) { double T[6][3][3]; int t, nt = r3_roof_tris(&sc->roofs[i], T); for (t = 0; t < nt; t++) r3_tri(r3_mk(T[t][0][0], T[t][0][1], T[t][0][2]), r3_mk(T[t][1][0], T[t][1][1], T[t][1][2]), r3_mk(T[t][2][0], T[t][2][1], T[t][2][2]), 1, 0, &src); }
    r3_shsc = NULL;
    r3_t[1] = SDL_GetPerformanceCounter();
    r3_cards_sprites(sc, &src, sw, e);
    r3_t[2] = SDL_GetPerformanceCounter();
    for (y = 0; y < 224; y++) for (x = 0; x < sw; x++) {                    /* game pixels outside the map (HUD, text box, black lines of the full height band) keep the final 1x pixel */
        int cx = x - e, in3d = y >= 23 && lk_hd_dstamp[y] == lk_hd_gen && cx >= -48 && cx < 368 && !(lk_hd_spr[y * 416 + cx + 48] & 4); int sy, sx;
        if (!in3d) for (sy = 0; sy < N; sy++) for (sx = 0; sx < N; sx++) r3_img[(size_t)(y * N + sy) * W + x * N + sx] = fb[(size_t)y * sw + x];
    }
    r3_last_frame = platform_frame_number();
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

/* ---- REMAKE RULE LAYER, first change of the game's behaviour: camera relative controls (Options > Video > Camera Controls Off / On, `~/.landstalker_camctl`, env LANDSTALKER_CAMCTL) ----
 * The game moves along its four world axes only (NE = -Y, SE = +X, SW = +Y, NW = -X); the d-pad combinations UP+RIGHT / DOWN+RIGHT / DOWN+LEFT / UP+LEFT select one axis each (HandleDirectionalControl $001936),
 * the plain directions pick one of two axes by Nigel's facing.  With the 3D camera turned, the axis that LOOKS closest to the pressed screen direction is chosen instead: the wrapper of
 * HandleDirectionalInput $0018C4 (tools/patch_room3d.py, func_table.c) replaces the d-pad nibble by the diagonal nibble of that axis for the duration of the call.  Inactive when the option is Off,
 * the 3D picture is not shown, the camera is within 3 degrees of the original, or a cutscene plays the controller (g_ControllerPlayback $FF12DE). */
int lk_camctl_get(void) {
    if (r3_camctl_cache < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_CAMCTL"); char path[512]; FILE *f; int v = 0; snprintf(path, sizeof path, "%s/.landstalker_camctl", h ? h : "."); f = NULL; /* PAUSED 2026-10-24: the saved file is ignored, only the env variable switches it on (test aid) */ if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); r3_camctl_cache = v ? 1 : 0; }
    return r3_camctl_cache;
}
void lk_camctl_set(int v) { const char *h = getenv("HOME"); char path[512]; FILE *f; r3_camctl_cache = v ? 1 : 0; snprintf(path, sizeof path, "%s/.landstalker_camctl", h ? h : "."); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", r3_camctl_cache); fclose(f); } }
int lk_camctl_nibble(int nib) {   /* -1 = leave the input alone, else the d-pad nibble (bit 0 up, 1 down, 2 left, 3 right) to use */
    static const int wdx[4] = { 0, 1, 0, -1 }, wdy[4] = { -1, 0, 1, 0 }, code[4] = { 0x9, 0xA, 0x6, 0x5 };   /* NE (-Y), SE (+X), SW (+Y), NW (-X) and their diagonal d-pad nibbles */
    static int prev = -1; double vx, vy, ln, c, s, best = -2, sc[4]; int a, pick = -1;
    if (!lk_camctl_get() || !lk_r3d_on() || platform_frame_number() - r3_last_frame > 3 || fabs(r3_yaw) < 0.052) return -1;
    vx = ((nib >> 3) & 1) - ((nib >> 2) & 1); vy = ((nib >> 1) & 1) - (nib & 1);
    if (vx == 0 && vy == 0) return -1;
    ln = sqrt(vx * vx + vy * vy); vx /= ln; vy /= ln; c = cos(r3_yaw); s = sin(r3_yaw);
    for (a = 0; a < 4; a++) {                                    /* how the world axis looks on the screen with the turned camera (same projection as the picture) */
        double xr = wdx[a] * c - wdy[a] * s, yr = wdx[a] * s + wdy[a] * c, u = (xr - yr) / R3K2, dd = (xr + yr) / R3K2, sx = R3K2 * u, sy = 0.70711 * dd, l = sqrt(sx * sx + sy * sy);
        sc[a] = (sx * vx + sy * vy) / l; if (sc[a] > best) { best = sc[a]; pick = a; }
    }
    if (prev >= 0 && sc[prev] > best - 0.03) pick = prev;       /* ties (the plain directions between two axes): keep the last axis, like the original keeps the facing */
    if (getenv("LANDSTALKER_CAMCTL_LOG")) printf("camctl: yaw %.1f pad %X -> axis %d nibble %X\n", r3_yaw * 180 / M_PI, nib, pick, code[pick]);
    prev = pick; return code[pick];
}

/* ---- REMAKE master switch (Options > Video > Remake Off / On, `~/.landstalker_remake`): a preset that writes the single switches of the remake: 3D Room, 3D Houses, Camera Controls (and 3D Light, see below);
 * Off writes them back to Off.  The single rows stay for experiments.  Remake Off + all rows Off = the original game, bit exact. ---- */
static int r3_remake_cache = -1;
int lk_remake_get(void) {
    if (r3_remake_cache < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_REMAKE"); char path[512]; FILE *f; int v = 0; snprintf(path, sizeof path, "%s/.landstalker_remake", h ? h : "."); f = NULL; /* PAUSED 2026-10-24: the saved file is ignored, only the env variable switches it on (test aid) */ if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); r3_remake_cache = v ? 1 : 0; }
    return r3_remake_cache;
}
extern void lk_r3d_light_set(int v);
void lk_remake_set(int v) {
    const char *h = getenv("HOME"); char path[512]; FILE *f; r3_remake_cache = v ? 1 : 0;
    snprintf(path, sizeof path, "%s/.landstalker_remake", h ? h : "."); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", r3_remake_cache); fclose(f); }
    lk_r3d_set(v ? 1 : 0); lk_r3d_houses_set(v ? 2 : 0); lk_camctl_set(v ? 1 : 0); lk_r3d_light_set(v ? 1 : 0); lk_r3d_objects_set(v ? 1 : 0); lk_r3d_trees_set(v ? 1 : 0);   /* the pixel art stays: houses = the original art on real geometry ('Picture'), trees / fences / figures stay sprites; the flat coloured models (3D Houses = Model, 3D Trees, 3D Objects) are experiments, off */
}
