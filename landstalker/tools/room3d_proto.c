/* room3d_proto.c - experiment: Landstalker room as 3D scene (docs/RENDERER_IDEAS.md, 'the 3D room', 2026-10-24).
 *
 * Input: a room dump written by the game (LANDSTALKER_ROOMDUMP=<dir> LANDSTALKER_ROOMDUMP_ROOM=<n>, tools/patch_own.py lk_o_roomdump):
 *   layerA.rgba / layerB.rgba (2432 x 1216, alpha 0 transparent / 1 low / 2 high priority), heightmap.bin (74 x 74 big endian words), info.txt (cam0 cam2).
 * Local files only (ROM derived pictures never go into git).
 *
 * Idea: the height map is a real height field (floors, house blocks, cliffs).  Its surfaces get their colours by PROJECTIVE texturing from the original
 * camera: a surface point (wx, wy, z) takes the pixel at image position U = wx - wy + 1184, V = (wx + wy) / 2 - z of the room picture (docs/FORMATS.md
 * 'Block map').  Seen from the original camera the result equals the original picture; a tilted / turned camera shows the same scene with real depth.
 * What the height field does not cover in the original view (roof ridges, trees, fence tops) becomes upright one pixel wide CARD STRIPS that stand on the surface
 * point just below them (like HD-2D cards).  Orthographic camera = the original isometric view (pitch 35.26 degrees, x scale sqrt 2) plus yaw / pitch offsets.
 *
 * Usage: room3d_proto DUMPDIR OUT.png [yaw_deg [pitch_delta_deg [scale [flags]]]]    flags: n = no cards, b = no back faces
 * Build: cc -O2 -o room3d_proto room3d_proto.c -lm
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define TW 2432
#define TH 1216
static uint8_t *tex;                 /* composited room picture RGBA (alpha 0 = nothing) */
static int hm[74][74];               /* word: byte 0 = type nibble << 4 | height, byte 1 = floor type; 0x4000 = void */
static int cam0, cam2;

static double Wd, Hd, S = 1.0, YAW, DPHI, fx, fy, fz, ox, oy;
static float *zbuf; static uint32_t *img; static int CW = 1400, CH = 900;
static const double K2 = 1.41421356237;

static void proj(double wx, double wy, double z, double *sx, double *sy, double *w) {
  double dx = wx - fx, dy = wy - fy, c = cos(YAW), s = sin(YAW), xr = dx * c - dy * s, yr = dx * s + dy * c;
  double u = (xr - yr) / K2, dd = (xr + yr) / K2, ph = atan(1.0 / K2) + DPHI, kx = K2, ky = sqrt(1.5);
  *sx = S * kx * u + ox; *sy = S * ky * (dd * sin(ph) - (z - fz) * cos(ph)) + oy; *w = dd * cos(ph) + (z - fz) * sin(ph);
}
typedef struct { double x, y, w, u, v; } vtx;
static void tri(vtx a, vtx b, vtx c, int dark) {
  double minx = fmin(a.x, fmin(b.x, c.x)), maxx = fmax(a.x, fmax(b.x, c.x)), miny = fmin(a.y, fmin(b.y, c.y)), maxy = fmax(a.y, fmax(b.y, c.y));
  double den = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y); int x0, x1, y0, y1, x, y;
  if (fabs(den) < 1e-9) return;
  x0 = (int)floor(minx); x1 = (int)ceil(maxx); y0 = (int)floor(miny); y1 = (int)ceil(maxy);
  if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0; if (x1 >= CW) x1 = CW - 1; if (y1 >= CH) y1 = CH - 1;
  for (y = y0; y <= y1; y++) for (x = x0; x <= x1; x++) {
    double px = x + 0.5, py = y + 0.5, l1 = ((b.y - c.y) * (px - c.x) + (c.x - b.x) * (py - c.y)) / den, l2 = ((c.y - a.y) * (px - c.x) + (a.x - c.x) * (py - c.y)) / den, l3 = 1 - l1 - l2;
    double w, u, v; int tu, tv; const uint8_t *t;
    if (l1 < -1e-6 || l2 < -1e-6 || l3 < -1e-6) continue;
    w = l1 * a.w + l2 * b.w + l3 * c.w; if (w <= zbuf[y * CW + x]) continue;
    u = l1 * a.u + l2 * b.u + l3 * c.u; v = l1 * a.v + l2 * b.v + l3 * c.v; tu = (int)floor(u); tv = (int)floor(v);
    if (tu < 0 || tv < 0 || tu >= TW || tv >= TH) continue;
    t = tex + ((size_t)tv * TW + tu) * 4; if (!t[3]) continue;
    zbuf[y * CW + x] = (float)w; { int r = t[0], g = t[1], bl = t[2]; if (dark) { r = r * 3 / 5; g = g * 3 / 5; bl = bl * 3 / 5; } img[y * CW + x] = 0xFF000000u | (uint32_t)r << 16 | (uint32_t)g << 8 | (uint32_t)bl; }
  }
}
static vtx mk(double wx, double wy, double z) { vtx p; proj(wx, wy, z, &p.x, &p.y, &p.w); p.u = wx - wy + 1184; p.v = (wx + wy) / 2 - z; return p; }
static void quad(vtx a, vtx b, vtx c, vtx d, int dark) { tri(a, b, c, dark); tri(a, c, d, dark); }

static double cellz(int x, int y) { if (x < 0 || y < 0 || x >= 74 || y >= 74) return -400; if (hm[y][x] == 0x4000) return -400; return 16.0 * ((hm[y][x] >> 8) & 15); }
static int isvoid(int x, int y) { return x < 0 || y < 0 || x >= 74 || y >= 74 || hm[y][x] == 0x4000; }

static void put_png(const char *path, const uint32_t *p, int w, int h) {
  FILE *f = fopen(path, "wb"); size_t rowlen = (size_t)w * 3 + 1, rawlen = rowlen * h, i; uint8_t *raw = (uint8_t *)malloc(rawlen); uint32_t crctab[256], c, a1 = 1, a2 = 0;
  uint8_t *z = (uint8_t *)malloc(rawlen + rawlen / 65535 * 5 + 64); size_t zl = 0, pos = 0; int y, x;
  for (y = 0; y < h; y++) { raw[y * rowlen] = 0; for (x = 0; x < w; x++) { uint32_t q = p[y * w + x]; raw[y * rowlen + 1 + x * 3] = q >> 16; raw[y * rowlen + 2 + x * 3] = q >> 8; raw[y * rowlen + 3 + x * 3] = q; } }
  z[zl++] = 0x78; z[zl++] = 1;
  while (pos < rawlen) { size_t n = rawlen - pos > 65535 ? 65535 : rawlen - pos; z[zl++] = (pos + n == rawlen); z[zl++] = n & 255; z[zl++] = n >> 8; z[zl++] = ~n & 255; z[zl++] = (~n >> 8) & 255; memcpy(z + zl, raw + pos, n); zl += n; pos += n; }
  for (i = 0; i < rawlen; i++) { a1 = (a1 + raw[i]) % 65521; a2 = (a2 + a1) % 65521; }
  z[zl++] = a2 >> 8; z[zl++] = a2; z[zl++] = a1 >> 8; z[zl++] = a1;
  for (i = 0; i < 256; i++) { c = (uint32_t)i; for (y = 0; y < 8; y++) c = c & 1 ? 0xEDB88320u ^ (c >> 1) : c >> 1; crctab[i] = c; }
#define BE32(v) fputc((v) >> 24, f), fputc((v) >> 16, f), fputc((v) >> 8, f), fputc((v), f)
  fwrite("\x89PNG\r\n\x1a\n", 1, 8, f);
  { uint8_t hd[13] = { (uint8_t)(w >> 24), (uint8_t)(w >> 16), (uint8_t)(w >> 8), (uint8_t)w, (uint8_t)(h >> 24), (uint8_t)(h >> 16), (uint8_t)(h >> 8), (uint8_t)h, 8, 2, 0, 0, 0 }; uint32_t cr = 0xFFFFFFFFu; BE32(13u); fwrite("IHDR", 1, 4, f); fwrite(hd, 1, 13, f);
    for (i = 0; i < 4; i++) cr = crctab[(cr ^ "IHDR"[i]) & 255] ^ (cr >> 8); for (i = 0; i < 13; i++) cr = crctab[(cr ^ hd[i]) & 255] ^ (cr >> 8); cr ^= 0xFFFFFFFFu; BE32(cr); }
  { uint32_t cr = 0xFFFFFFFFu; BE32((uint32_t)zl); fwrite("IDAT", 1, 4, f); fwrite(z, 1, zl, f); for (i = 0; i < 4; i++) cr = crctab[(cr ^ "IDAT"[i]) & 255] ^ (cr >> 8); for (i = 0; i < zl; i++) cr = crctab[(cr ^ z[i]) & 255] ^ (cr >> 8); cr ^= 0xFFFFFFFFu; BE32(cr); }
  { uint32_t cr = 0xFFFFFFFFu; BE32(0u); fwrite("IEND", 1, 4, f); for (i = 0; i < 4; i++) cr = crctab[(cr ^ "IEND"[i]) & 255] ^ (cr >> 8); cr ^= 0xFFFFFFFFu; BE32(cr); }
  fclose(f); free(raw); free(z);
}

int main(int argc, char **argv) {
  char path[600]; FILE *f; uint8_t *A, *B; int x, y, i, nocards = 0, noback = 0, ncards = 0;
  static float hitwx[TH][TW]; static float hitwy[TH][TW], hitz[TH][TW]; static uint8_t cov[TH][TW];
  if (argc < 3) { fprintf(stderr, "usage: %s DUMPDIR OUT.png [yaw_deg [pitch_delta_deg [scale [flags n b]]]]\n", argv[0]); return 1; }
  YAW = (argc > 3 ? atof(argv[3]) : 0) * M_PI / 180; DPHI = (argc > 4 ? atof(argv[4]) : 0) * M_PI / 180; S = argc > 5 ? atof(argv[5]) : 1.0;
  if (argc > 6) { nocards = strchr(argv[6], 'n') != NULL; noback = strchr(argv[6], 'b') != NULL; }
  A = (uint8_t *)malloc((size_t)TW * TH * 4); B = (uint8_t *)malloc((size_t)TW * TH * 4); tex = (uint8_t *)malloc((size_t)TW * TH * 4);
  snprintf(path, sizeof path, "%s/layerA.rgba", argv[1]); f = fopen(path, "rb"); if (!f || fread(A, 1, (size_t)TW * TH * 4, f) != (size_t)TW * TH * 4) { fprintf(stderr, "layerA\n"); return 1; } fclose(f);
  snprintf(path, sizeof path, "%s/layerB.rgba", argv[1]); f = fopen(path, "rb"); if (!f || fread(B, 1, (size_t)TW * TH * 4, f) != (size_t)TW * TH * 4) { fprintf(stderr, "layerB\n"); return 1; } fclose(f);
  snprintf(path, sizeof path, "%s/heightmap.bin", argv[1]); f = fopen(path, "rb"); if (!f) return 1;
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int hi = fgetc(f), lo = fgetc(f); hm[y][x] = hi << 8 | lo; } fclose(f);
  for (i = 0; i < TW * TH; i++) {                       /* priority order of the VDP: A high, B high, A low, B low */
    const uint8_t *a = A + i * 4, *b = B + i * 4, *s = NULL;
    if (a[3] == 2) s = a; else if (b[3] == 2) s = b; else if (a[3]) s = a; else if (b[3]) s = b;
    if (s) { tex[i * 4] = s[0]; tex[i * 4 + 1] = s[1]; tex[i * 4 + 2] = s[2]; tex[i * 4 + 3] = 255; } else { tex[i * 4] = tex[i * 4 + 1] = tex[i * 4 + 2] = 0; tex[i * 4 + 3] = 0; }
  }
  { int x0 = 99, x1 = -1, y0 = 99, y1 = -1; for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) if (hm[y][x] != 0x4000) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    fx = 16.0 * (x0 + x1 + 1) / 2; fy = 16.0 * (y0 + y1 + 1) / 2; fz = 0; }
  ox = CW / 2.0; oy = CH / 2.0 + 20;
  zbuf = (float *)malloc((size_t)CW * CH * 4); img = (uint32_t *)malloc((size_t)CW * CH * 4);
  for (i = 0; i < CW * CH; i++) { zbuf[i] = -1e9f; img[i] = 0xFF101018u; }

  /* pass 1: the height field seen from the ORIGINAL camera, to find what it covers: per picture pixel the world position of the nearest surface (along a view ray wx + wy + z grows towards the viewer) */
  memset(cov, 0, sizeof cov);
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {   /* direct rasterisation of the original view: top quads + visible side quads, writing the hit world position per picture pixel */
    int k;
    if (isvoid(x, y)) continue;
    for (k = 0; k < 3; k++) {
      double z0, z1, wx[4], wy[4], zz[4]; int n = 4, q;
      if (k == 0) { z0 = cellz(x, y); wx[0] = 16 * x; wy[0] = 16 * y; wx[1] = 16 * x + 16; wy[1] = 16 * y; wx[2] = 16 * x + 16; wy[2] = 16 * y + 16; wx[3] = 16 * x; wy[3] = 16 * y + 16; zz[0] = zz[1] = zz[2] = zz[3] = z0; }
      else if (k == 1) { z0 = cellz(x, y); z1 = cellz(x + 1, y); if (z1 >= z0) continue; wx[0] = wx[1] = wx[2] = wx[3] = 16 * x + 16; wy[0] = 16 * y; wy[1] = 16 * y + 16; wy[2] = 16 * y + 16; wy[3] = 16 * y; zz[0] = z0; zz[1] = z0; zz[2] = z1; zz[3] = z1; }
      else { z0 = cellz(x, y); z1 = cellz(x, y + 1); if (z1 >= z0) continue; wy[0] = wy[1] = wy[2] = wy[3] = 16 * y + 16; wx[0] = 16 * x; wx[1] = 16 * x + 16; wx[2] = 16 * x + 16; wx[3] = 16 * x; zz[0] = z0; zz[1] = z0; zz[2] = z1; zz[3] = z1; }
      for (q = 0; q < 2; q++) {                      /* two triangles */
        int ia = 0, ib = q ? 2 : 1, ic = q ? 3 : 2; double U[3], V[3], P[3][3]; int idx[3] = { ia, ib, ic }, j, px, py;
        for (j = 0; j < 3; j++) { int t = idx[j]; U[j] = wx[t] - wy[t] + 1184; V[j] = (wx[t] + wy[t]) / 2 - zz[t]; P[j][0] = wx[t]; P[j][1] = wy[t]; P[j][2] = zz[t]; }
        { double mnx = fmin(U[0], fmin(U[1], U[2])), mxx = fmax(U[0], fmax(U[1], U[2])), mny = fmin(V[0], fmin(V[1], V[2])), mxy = fmax(V[0], fmax(V[1], V[2]));
          double den = (V[1] - V[2]) * (U[0] - U[2]) + (U[2] - U[1]) * (V[0] - V[2]);
          if (fabs(den) < 1e-9) continue;
          for (py = (int)floor(mny); py <= (int)ceil(mxy); py++) for (px = (int)floor(mnx); px <= (int)ceil(mxx); px++) {
            double qx = px + 0.5, qy = py + 0.5, l1 = ((V[1] - V[2]) * (qx - U[2]) + (U[2] - U[1]) * (qy - V[2])) / den, l2 = ((V[2] - V[0]) * (qx - U[2]) + (U[0] - U[2]) * (qy - V[2])) / den, l3 = 1 - l1 - l2;
            if (px < 0 || py < 0 || px >= TW || py >= TH || l1 < -1e-6 || l2 < -1e-6 || l3 < -1e-6) continue;
            { double hz = l1 * P[0][2] + l2 * P[1][2] + l3 * P[2][2], hwx = l1 * P[0][0] + l2 * P[1][0] + l3 * P[2][0], hwy = l1 * P[0][1] + l2 * P[1][1] + l3 * P[2][1];
              if (!cov[py][px] || hwx + hwy + hz > hitwx[py][px] + hitwy[py][px] + hitz[py][px]) { hitwx[py][px] = (float)hwx; hitwy[py][px] = (float)hwy; hitz[py][px] = (float)hz; cov[py][px] = 1; } }
          } }
      }
      (void)n;
    }
  }

  /* pass 2: draw the scene with the chosen camera */
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
    double z = cellz(x, y), x0 = 16.0 * x, y0 = 16.0 * y, x1 = x0 + 16, y1 = y0 + 16;
    if (isvoid(x, y)) continue;
    quad(mk(x0, y0, z), mk(x1, y0, z), mk(x1, y1, z), mk(x0, y1, z), 0);
    { double zn = cellz(x + 1, y); if (zn < z) quad(mk(x1, y0, z), mk(x1, y1, z), mk(x1, y1, zn), mk(x1, y0, zn), 0); }
    { double zn = cellz(x, y + 1); if (zn < z) quad(mk(x0, y1, z), mk(x1, y1, z), mk(x1, y1, zn), mk(x0, y1, zn), 0); }
    if (!noback) {
      { double zn = cellz(x - 1, y); if (zn < z) quad(mk(x0, y0, z), mk(x0, y1, z), mk(x0, y1, zn), mk(x0, y0, zn), 1); }
      { double zn = cellz(x, y - 1); if (zn < z) quad(mk(x0, y0, z), mk(x1, y0, z), mk(x1, y0, zn), mk(x0, y0, zn), 1); }
    }
  }
  if (!nocards) {                                        /* card strips: opaque picture pixels the height field does not cover, standing on the surface point just below */
    int U;
    for (U = 0; U < TW; U++) for (y = TH - 2; y >= 0; y--) {
      int n = 0, v;
      if (!cov[y + 1][U] || cov[y][U] || !tex[((size_t)y * TW + U) * 4 + 3]) continue;
      for (v = y; v >= 0 && !cov[v][U] && tex[((size_t)v * TW + U) * 4 + 3]; v--) n++;
      { double bx = hitwx[y + 1][U], by = hitwy[y + 1][U], bz = hitz[y + 1][U], c = cos(0.0), r0 = 1 / K2, r1 = -1 / K2, hw = 0.5 / K2;   /* strips keep the ORIGINAL right axis (1, -1): neighbouring strips stay joined into cards (a strip that turned about its own anchor would leave gaps) */
        vtx a, b, cc, d; (void)c;
        if (n >= 110) {                                 /* a long uncovered run is a surface that goes on towards the back (water, far cliff tops), not an upright thing: lay it flat at the height of the surface below */
          a = mk(bx - r0 * hw, by - r1 * hw, bz); b = mk(bx + r0 * hw, by + r1 * hw, bz); cc = mk(bx + r0 * hw - n, by + r1 * hw - n, bz); d = mk(bx - r0 * hw - n, by - r1 * hw - n, bz);
        } else {
          a = mk(bx - r0 * hw, by - r1 * hw, bz); b = mk(bx + r0 * hw, by + r1 * hw, bz); cc = mk(bx + r0 * hw, by + r1 * hw, bz + n); d = mk(bx - r0 * hw, by - r1 * hw, bz + n);
        }
        /* texture: the pixel column U, rows y + 1 .. y - n + 1 (texture v from the hit row upwards) */
        a.u = b.u = U + 0.5; cc.u = d.u = U + 0.5; a.v = b.v = y + 1.0; cc.v = d.v = y + 1.0 - n; quad(a, b, cc, d, 0); ncards++; }
      y = v + 1;
    }
  }
  put_png(argv[2], img, CW, CH);
  fprintf(stderr, "room3d_proto: yaw %.1f pitch %+.1f scale %.2f, %d card strips -> %s\n", YAW * 180 / M_PI, DPHI * 180 / M_PI, S, ncards, argv[2]);
  return 0;
}
