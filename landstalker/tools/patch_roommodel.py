#!/usr/bin/env python3
"""Stage 3, steps S3.1 + S3.2 (2026-10-23, docs/STAGE3_INVENTORY.md): the game-state MODEL, invisible groundwork (no picture change).
 * S3.1 `lk_rm_get(room)`: C port of the ROM room decoder (`tools/romroom.py` = port of `DecompressMap1 $00CDAE`): FG / BG block ids and the height map (74 x 74 words each, the game's cell index) of ANY room
   straight from the ROM, cached per room number.  Check (env LANDSTALKER_SMODEL_CHECK=1): 90 frames after every room change the decoded arrays are compared with the game's RAM arrays
   (`$FF7C02`, `$FFA6CA`, `$FFD192`) and one line `model: room R decode FG a BG b HM c cells differ` is printed (known game edits: rooms 139 / 142 / 632 top row, 454 scripted blocks).
 * S3.2 `lk_smodel`: one struct per frame filled from the RAM snapshot the own renderer draws from: room id, camera (`$FF1200` / `$FF1202`), the visible entities (`$FF11DE` list; type `+3B`, graphic `+0B`,
   tile / centre / Z, box, animation, flags, stored screen position `+0E / +10` and `+4E / +50`, supporting entity `+30`, health `+3E`).  Check: the model's own projection of the player
   (a = CentreX - Z - cam0, b = CentreY - Z - cam2, x = a - b + $120, y = ((a + b) >> 1) + $E8, FORMATS 'Entity -> screen projection') must equal the stored `+0E / +10`; the periodic line
   `model: frame F room R cam C0,C2 ents N player projection: equal A / different B (frames with a stored position; C without)` counts it.
S3.3 (camera): `$FF1200` / `$FF1202` equal the player's (CentreX - Z, CentreY - Z) exactly, `lk_smodel.mcam0 / mcam2` computes them and the check counts equal / different frames.
Everything is read only.  usage: patch_roommodel.py path/to/genrecomp   (run after patch_own.py).  Idempotent."""
import os, sys
root = sys.argv[1]
VER = "LK_SMODEL v1"
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER in s:
    print("vdp_render.c already patched:", VER); sys.exit(0)
mark = "/* ---- LK_OWN v1: own renderer, compare mode (tools/patch_own.py) ---- */"
assert s.count(mark) == 1, "vdp_render.c: run patch_own.py first"
call = "lk_o_r = r; lk_o_build(); lk_o_hudbuild();"
assert s.count(call) == 1, "vdp_render.c: own renderer frame call layout changed"
module = r'''/* ---- LK_SMODEL v1: room decoder + frame model (tools/patch_roommodel.py, docs/STAGE3_INVENTORY.md S3.1 / S3.2) ---- */
#include <stdio.h>
#include <stdlib.h>
extern uint8_t bus_read8(uint32_t addr);
extern long platform_frame_number(void);
static int MRB(uint32_t a) { return a < 0x200000u ? (int)bus_read8(a) : 0; }
static uint32_t MRL(uint32_t a) { return ((uint32_t)MRB(a) << 24) | ((uint32_t)MRB(a + 1) << 16) | ((uint32_t)MRB(a + 2) << 8) | (uint32_t)MRB(a + 3); }
typedef struct { int ok, left, top, w, h, tileset, palette, height, music; uint32_t ptr; uint16_t fg[74 * 74], bg[74 * 74], hm[74 * 74]; } lk_rm_t;
static lk_rm_t *lk_rm_cache[1024];
static uint8_t lk_rm_buf[0x10000];
static int lk_rm_hmw, lk_rm_hmh;   /* size of the stream's height map (stage 3 header bytes) */
static uint32_t lk_rm_pos; static int lk_rm_cur, lk_rm_n, lk_rm_a2, lk_rm_a4, lk_rm_a5, lk_rm_v16;
static int lk_rm_bit(void) { int b; if (lk_rm_n == 0) { lk_rm_cur = MRB(lk_rm_pos++); lk_rm_n = 8; } b = (lk_rm_cur >> 7) & 1; lk_rm_cur = (lk_rm_cur << 1) & 0xFF; lk_rm_n--; return b; }
static int lk_rm_bits(int n) { int v = 0; while (n-- > 0) v = (v << 1) | lk_rm_bit(); return v; }
static int lk_rm_w(int a) { return (a >= 0 && a + 1 < 0x10000) ? (lk_rm_buf[a] << 8) | lk_rm_buf[a + 1] : 0; }
static void lk_rm_sw(int a, int v) { if (a >= 0 && a + 1 < 0x10000) { lk_rm_buf[a] = (uint8_t)((v >> 8) & 255); lk_rm_buf[a + 1] = (uint8_t)(v & 255); } }
static void lk_rm_literal(void) {   /* stage 2: a literal word */
  int d7, d0 = 0;
  if (!lk_rm_bit()) {
    if (!lk_rm_bit()) { d7 = lk_rm_a4; while (d7) { d0 = (d0 << 1) | lk_rm_bit(); d7 >>= 1; } lk_rm_sw(lk_rm_a2, d0); }
    else { d7 = lk_rm_a5 - lk_rm_v16; while (d7 > 0) { d0 = (d0 << 1) | lk_rm_bit(); d7 >>= 1; } lk_rm_sw(lk_rm_a2, (d0 + lk_rm_v16) & 0xFFFF); }
  } else {
    if (lk_rm_bit()) { lk_rm_sw(lk_rm_a2, lk_rm_a5 & 0xFFFF); lk_rm_a5++; }
    else { lk_rm_sw(lk_rm_a2, lk_rm_a4 & 0xFFFF); lk_rm_a4++; }
  }
  lk_rm_a2 += 2;
}
static int lk_rm_decompress(uint32_t a0) {   /* port of DecompressMap1 $00CDAE (tools/romroom.py `decompress`); 0 = stream error */
  int hdr0, hdr1, hdr2, d4, x, d3, total, start, a3, v18, tab[8], a1, a2, i, mode = 0, d2 = 0, d5, done = 0; long guard = 0;
  memset(lk_rm_buf, 0, sizeof lk_rm_buf); lk_rm_pos = a0; lk_rm_cur = 0; lk_rm_n = 0;
  hdr0 = lk_rm_bits(8); hdr1 = lk_rm_bits(8); hdr2 = lk_rm_bits(8);
  d4 = (hdr2 + 1) * 2; x = lk_rm_bits(8); d3 = ((x + 1) >> 1) - 1;
  lk_rm_buf[0] = (uint8_t)hdr0; lk_rm_buf[1] = (uint8_t)hdr1; lk_rm_buf[2] = (uint8_t)hdr2; lk_rm_buf[3] = (uint8_t)(d3 & 255);
  total = (d3 + 1) * 2 * d4; start = 4; a3 = start + total;
  if (total <= 0 || a3 > 0xF000) return 0;
  lk_rm_v16 = lk_rm_bits(10); v18 = lk_rm_bits(10);
  for (i = 0; i < 8; i++) tab[i] = lk_rm_bits(12);
  a2 = start - 2;
  for (;;) {   /* stage 1: marks */
    int k = 0, nn, d1;
    if (++guard > 4000000L) return 0;
    while (!lk_rm_bit()) { k++; if (k > 24) return 0; }
    nn = k == 0 ? 1 : (1 << k) + lk_rm_bits(k);
    a2 += 2 * nn; if (a2 >= a3) break;
    if (!lk_rm_bit()) { if (!lk_rm_bit()) d1 = lk_rm_bit() ? 2 : 0xFFFF; else d1 = lk_rm_bit() ? d4 : 4; }
    else { if (!lk_rm_bit()) d1 = lk_rm_bit() ? d4 + 2 : 2 * d4; else d1 = tab[lk_rm_bits(3)] * 2; }
    d1 &= 0xFFFF; lk_rm_sw(a2, d1);
    if (lk_rm_bit()) {
      int d0 = lk_rm_bit() * 2; a1 = a2;
      for (;;) {
        int d3b = d0 + d4;
        for (;;) { if (++guard > 4000000L) return 0; a1 += d3b; if (a1 + 1 < 0x10000) lk_rm_sw(a1, d1); if (!lk_rm_bit()) break; }
        if (!lk_rm_bit()) break;
        d0 ^= 2;
      }
    }
  }
  lk_rm_a2 = start; lk_rm_a4 = v18; lk_rm_a5 = lk_rm_v16; lk_rm_sw(a3, 0xFFFF);
  for (;;) {   /* stage 2: resolve */
    int d0 = lk_rm_w(lk_rm_a2);
    if (++guard > 4000000L) return 0;
    if (d0 == 0) {
      if (mode == 0) return 0;
      if (mode == 1) { if (a3 <= lk_rm_a2) break; lk_rm_literal(); }
      else { lk_rm_sw(lk_rm_a2, lk_rm_w(lk_rm_a2 + d2)); lk_rm_a2 += 2; }
      continue;
    }
    if (d0 & 0x8000) { mode = 1; if (a3 <= lk_rm_a2) break; lk_rm_literal(); }
    else { d2 = -d0; mode = 2; lk_rm_sw(lk_rm_a2, lk_rm_w(lk_rm_a2 + d2)); lk_rm_a2 += 2; }
  }
  a1 = start + 0x5C94; a2 = a1;   /* stage 3: byte aligned RLE of the height map */
  d3 = MRB(lk_rm_pos++) - 1; d4 = d3; d5 = MRB(lk_rm_pos++) - 1; lk_rm_hmw = d3 + 1; lk_rm_hmh = d5 + 1;
  while (!done) {
    int d0 = (MRB(lk_rm_pos) << 8) | MRB(lk_rm_pos + 1), b, rep; lk_rm_pos += 2; d2 = 0;
    for (;;) { b = MRB(lk_rm_pos++); d2 += b; if (b != 0xFF) break; if (++guard > 4000000L) return 0; }
    for (rep = 0; rep < d2 + 1; rep++) {
      lk_rm_sw(a2, d0); a2 += 2; d4--;
      if (d4 < 0) { a1 += 0x94; a2 = a1; d4 = d3; d5--; if (d5 < 0) { done = 1; break; } }
      if (++guard > 4000000L) return 0;
    }
  }
  return 1;
}
const lk_rm_t *lk_rm_get(int room) {   /* the room's arrays as the game's GetTilemap / ExtractMap build them (FORMATS 'Room map data in the ROM'); NULL = not a decodable room */
  uint32_t tab, e; lk_rm_t *r; int x, y, w, h, base;
  if (room < 0 || room >= 1024) return NULL;
  if (lk_rm_cache[room]) return lk_rm_cache[room]->ok ? lk_rm_cache[room] : NULL;
  r = (lk_rm_t *)calloc(1, sizeof *r); if (!r) return NULL;
  lk_rm_cache[room] = r;
  tab = MRL(0xA0A00); e = tab + 8u * (uint32_t)room;
  r->ptr = MRL(e); r->tileset = MRB(e + 4); r->palette = MRB(e + 5); r->height = MRB(e + 6); r->music = MRB(e + 7);
  if (r->ptr < 0x1000 || r->ptr >= 0x200000 || !lk_rm_decompress(r->ptr)) return NULL;
  r->left = (int8_t)lk_rm_buf[0]; r->top = (int8_t)lk_rm_buf[1]; w = r->w = lk_rm_buf[2] + 1; h = r->h = lk_rm_buf[3] + 1;
  for (base = 0; base < 2; base++) {
    uint16_t *dst = base ? r->bg : r->fg; int b0 = 4 + (base ? 2 * w * h : 0);
    for (y = 0; y < h; y++) for (x = 0; x < w; x++) { int xx = x + r->left, yy = y + r->top; if (xx >= 0 && xx < 74 && yy >= 0 && yy < 74) dst[yy * 74 + xx] = (uint16_t)lk_rm_w(b0 + 2 * (y * w + x)); }
  }
  for (x = 0; x < 74 * 74; x++) r->hm[x] = 0x4000;   /* GetTilemap clears the whole array to $4000; the stream's rectangle (stage 3 header: width x height) is copied as it is (0 stays 0) */
  for (y = 0; y < lk_rm_hmh && y < 62; y++) for (x = 0; x < lk_rm_hmw && x < 62; x++) { int v = lk_rm_w(4 + 0x5C94 + 148 * y + 2 * x); r->hm[(y + 12) * 74 + x + 12] = (uint16_t)v; }   /* the stream's height map lands at offset (12, 12) (room 610: 1187 of 1187 non-void cells) */
  r->ok = 1; return r;
}
/* ---- S3.2: the per frame model ---- */
typedef struct { int idx; uint32_t addr; int type, graphic, tx, ty, z, cx, cy, bx0, bx1, by0, by1, anim, frame, flags8, flagsC, sx, sy, psx, psy, support, hp; } lk_sme_t;
typedef struct { long frame; int room, cam0, cam2, mcam0, mcam2, n;   /* cam0 / cam2 = the game's `$FF1200` / `$FF1202`, mcam0 / mcam2 = the camera computed from the player (S3.3: CentreX - Z, CentreY - Z) */
   lk_sme_t e[32]; const lk_rm_t *rm; } lk_smodel_t;
lk_smodel_t lk_smodel;
static int lk_smdl_chk = -1;
void lk_sm_update(const uint8 *r, int room) {
  #define MRR8(a) ((int)r[((a) & 0xFFFF) ^ 1])
  #define MRR16(a) ((MRR8(a) << 8) | MRR8((a) + 1))
  static int cur = -1, checked; static long since, pframes, pok, poff, pnone; int k;
  lk_smodel_t *m = &lk_smodel;
  if (lk_smdl_chk < 0) { const char *e = getenv("LANDSTALKER_SMODEL_CHECK"); lk_smdl_chk = e ? atoi(e) : 0; }
  { static long lastf = -1; if (platform_frame_number() == lastf) return; lastf = platform_frame_number(); }   /* once per frame (the renderer calls this from its line hook) */
  m->frame = platform_frame_number(); m->room = room; m->cam0 = (int16_t)MRR16(0xFF1200); m->cam2 = (int16_t)MRR16(0xFF1202);
  if (room != cur) { cur = room; since = m->frame; checked = 0; m->rm = lk_rm_get(room); }
  { int pz = (int16_t)MRR16(0xFF5412), pcx = (int16_t)MRR16(0xFF5414), pcy = (int16_t)MRR16(0xFF5416); m->mcam0 = pcx - pz; m->mcam2 = pcy - pz; }   /* S3.3: the camera IS the player's flattened position */
  { static long ceq, cdf; if (m->mcam0 == m->cam0 && m->mcam2 == m->cam2) ceq++; else cdf++; if (lk_smdl_chk && m->frame % 600 == 0) printf("model: camera = player (CentreX - Z, CentreY - Z): equal %ld / different %ld (frames)\n", ceq, cdf); }
  m->n = 0;
  for (k = 0; k < 32; k++) {
    int w = MRR16(0xFF11DE + 2 * k); uint32_t a; lk_sme_t *e;
    if (w == 0xFFFF || w >= 0x1000) break;
    a = 0xFF5400u + (uint32_t)w; e = &m->e[m->n++];
    e->idx = w / 0x80; e->addr = a; e->type = MRR8(a + 0x3B); e->graphic = MRR8(a + 0x0B); e->tx = MRR8(a); e->ty = MRR8(a + 1); e->z = (int16_t)MRR16(a + 0x12);
    e->cx = (int16_t)MRR16(a + 0x14); e->cy = (int16_t)MRR16(a + 0x16); e->bx0 = (int16_t)MRR16(a + 0x18); e->bx1 = (int16_t)MRR16(a + 0x1A); e->by0 = (int16_t)MRR16(a + 0x1C); e->by1 = (int16_t)MRR16(a + 0x1E);
    e->anim = MRR16(a + 0x24); e->frame = MRR16(a + 0x26); e->flags8 = MRR8(a + 8); e->flagsC = MRR8(a + 0x0C); e->sx = MRR16(a + 0x0E); e->sy = MRR16(a + 0x10); e->psx = MRR16(a + 0x4E); e->psy = MRR16(a + 0x50);
    e->support = (int16_t)MRR16(a + 0x30); e->hp = MRR16(a + 0x3E);
  }
  if (!lk_smdl_chk) return;
  for (k = 0; k < m->n; k++) if (m->e[k].addr == 0xFF5400u) {   /* the player: the model's projection must equal the stored screen position */
    const lk_sme_t *e = &m->e[k]; int a = e->cx - e->z - m->cam0, b = e->cy - e->z - m->cam2, px = a - b + 0x120, py = ((a + b) >> 1) + 0xE8;
    if (e->sx == 0) { pnone++; continue; }
    if (lk_smdl_chk == 4) printf("cam: %ld %d %d %d %d %d %d %d %d %d\n", m->frame, room, e->cx, e->cy, e->z, m->cam0, m->cam2, e->sx, e->sy, MRR16(0xFF1204));   /* no screen position stored (fade / load frames, entity off screen) */
    pframes++; if (px == e->sx && py == e->sy) pok++; else poff++;
    if (lk_smdl_chk == 2 && e->sx != 0 && (px != e->sx || py != e->sy)) { static int nn; if (nn++ < 25) printf("model: P OFF frame %ld stored %d,%d model %d,%d d %d,%d cx %d cy %d z %d cam %d,%d\n", m->frame, e->sx, e->sy, px, py, e->sx - px, e->sy - py, e->cx, e->cy, e->z, m->cam0, m->cam2); }
    if (lk_smdl_chk == 2 && m->frame % 4000 == 0) printf("model: P frame %ld stored %d,%d model %d,%d cx %d cy %d z %d cam %d,%d\n", m->frame, e->sx, e->sy, px, py, e->cx, e->cy, e->z, m->cam0, m->cam2);
  }
  if ((checked == 0 && m->frame - since >= 90 || checked == 2 && m->frame - since >= 400) && m->rm) {
    int fgd = 0, bgd = 0, hmd = 0, x, y;
    checked = checked == 0 ? 1 : 3;
    if (lk_smdl_chk == 5) { int i; printf("ents %d:", room); for (i = 0; i < 16; i++) { uint32_t ea = 0xFF5400u + 0x80u * (uint32_t)i; printf(" %d/%d,%d/%d", MRR8(ea + 0x3B), MRR8(ea), MRR8(ea + 1), MRR8(ea + 0x0A)); } printf("\n"); }
    for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
      if (m->rm->fg[y * 74 + x] != MRR16(0xFF7C02 + 148 * y + 2 * x)) fgd++;
      if (m->rm->bg[y * 74 + x] != MRR16(0xFFA6CA + 148 * y + 2 * x)) bgd++;
      if (m->rm->hm[y * 74 + x] != MRR16(0xFFD192 + 148 * y + 2 * x)) { if (hmd < 6 && lk_smdl_chk == 3) printf("model:   HM diff (%d,%d) rom %04X ram %04X\n", x, y, m->rm->hm[y * 74 + x], MRR16(0xFFD192 + 148 * y + 2 * x)); hmd++; }
    }
    { int dx, dy, best = -1, bdx = 0, bdy = 0, tot = 0;   /* HM: which shift of the stream's cells equals the RAM array (non-void cells) */
      for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int v = m->rm->hm[y * 74 + x]; if (v != 0 && v != 0x4000) tot++; }
      for (dy = -20; dy <= 20; dy++) for (dx = -20; dx <= 20; dx++) { int mm = 0; for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) { int v = m->rm->hm[y * 74 + x], xx = x + dx, yy = y + dy; if (v == 0 || v == 0x4000) continue; if (xx >= 0 && xx < 74 && yy >= 0 && yy < 74 && MRR16(0xFFD192 + 148 * yy + 2 * xx) == v) mm++; } if (mm > best) { best = mm; bdx = dx; bdy = dy; } }
      printf("model: room %d decode FG %d BG %d HM %d cells differ (of 5476; frame %ld); HM best shift (%d, %d): %d of %d non-void cells equal%s\n", room, fgd, bgd, hmd, m->frame, bdx, bdy, best, tot, fgd + bgd + hmd ? " DIFFERENT" : " exact"); if (fgd + bgd + hmd && checked == 1) checked = 2; }
  } else if (checked == 0 && m->frame - since >= 90 && !m->rm) { checked = 3; printf("model: room %d: ROM decode FAILED\n", room); }
  if (m->frame % 600 == 0) printf("model: frame %ld room %d cam %d,%d ents %d player projection: equal %ld / different %ld (frames with a stored position; %ld without)\n", m->frame, room, m->cam0, m->cam2, m->n, pok, poff, pnone);
  #undef MRR8
  #undef MRR16
}
'''
s = s.replace(mark, module + mark, 1)
s = s.replace(call, "lk_sm_update(r, rm); " + call, 1)
s = s + "\n/* " + VER + " */\n"
open(p, "w").write(s)
print("vdp_render.c patched:", VER)
