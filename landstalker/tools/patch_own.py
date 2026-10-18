#!/usr/bin/env python3
"""Own renderer, compare mode (2026-10-18, renderer step 'state-driven picture', RENDERER_IDEAS Option B): draws the map picture of the game WITHOUT the VDP planes / sprite table, from
ROM data and game state only, line by line, and compares it with what the VDP produced.  C port of the Python tools romgfx / romrender / romsprite (all verified against RAM dumps,
FORMATS 'Room graphics in the ROM'):
 * tile graphics of the room: `DecompressLZ77Gfx $004AB2` from the ROM (room table $0A0A00, tileset table $044010), animated tiles (`AnimatedTilesetTable $009E04`, state `$FF1134`),
 * both scroll layers from the block arrays in work RAM (BG `$FFA6CA`, FG `$FF7C02`, 74 x 74 words) and the block table `$FF5C02` (4 tile words per block) on the 8 px brick grid
   (block (x, y) = 2 x 2 tiles at tile column 2 (x - y) + 148 / 146, tile row x + y); the screen position uses the camera of the previous pass (the image is unbounded: no plane wrap, no scroll registers),
 * the figures: visible entity list `$FF11DE`, frame pieces and tile graphics from the ROM (`LoadSpriteFrame $004230` port, SpriteGfxPtrPtr `$120000`),
 * colours: built from ROM + state too (player palette + equipment swaps, per-room sprite palette allocation, room palette, fade level inferred from the active palette copy); LANDSTALKER_OWN_PAL=0 uses the VDP's CRAM instead.
State = snapshot of work RAM of the PREVIOUS frame (the picture is one frame behind the RAM, FORMATS 'Scroll registers lag').
Switch: env LANDSTALKER_OWN=1 compare only (console line every LANDSTALKER_OWN_LOG frames, default 60: `own: frame F room R lines 0..223: D of T pixels differ`), =2 the picture shows
the OWN rendering in the map lines 0..223 (HUD / text box / lines below stay the game's).  Off by default (debug aid).  Hook: render_line, before the other row overlays.
usage: patch_own.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_OWN v1"
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    d = "      lk_shadow_darken(lk_row0, lk_w0);   /* LK_SHADOW v7 */\n"
    assert s.count(d) == 1, "vdp_render.c: run patch_shadow.py first"
    s = s.replace(d, "      lk_own_row(lk_row0, lk_w0, line);   /* LK_OWN v1 */\n" + d, 1)
    c = "void render_line(int line)"
    assert s.count(c) == 1
    module = r'''/* ---- LK_OWN v1: own renderer, compare mode (tools/patch_own.py) ---- */
extern uint8_t *bus_get_ram(void);
extern uint8_t bus_read8(uint32_t addr);
extern long platform_frame_number(void);
static int OB(uint32_t a) { return a < 0x200000u ? (int)bus_read8(a) : 0; }   /* ROM only; garbage pointers read 0 */
#define OW(a) ((OB(a) << 8) | OB((a) + 1))
#define OL(a) ((uint32_t)(((uint32_t)OW(a) << 16) | (uint32_t)OW((a) + 2)))
static int lk_o_sprmode = 1;
static int lk_o_mode = -1, lk_o_log = 60, lk_o_room = -1, lk_o_ngrp, lk_o_valid;
static uint8 lk_o_prev[0x10000], lk_o_use[0x10000];
#define UB(a) (lk_o_use[((a) & 0xFFFF) ^ 1])
#define UW(a) ((int)((UB(a) << 8) | UB((a) + 1)))
#define US(a) ((int)(int16_t)UW(a))
static const uint8 *lk_o_sp = lk_o_use;   /* RAM snapshot the figures are built from (LANDSTALKER_OWN_SPR=1 (default): current pass, 0: previous pass; measured: figures come from the CURRENT pass, camera / scenery from the previous one) */
#define SB(a) (lk_o_sp[((a) & 0xFFFF) ^ 1])
#define SW(a) ((int)((SB(a) << 8) | SB((a) + 1)))
static uint8 lk_o_tbase[0x12000], lk_o_tiles[0x12000];
static struct { int dest, words, delay, frames; uint32_t base; } lk_o_grp[8];
static uint32 lk_o_pa[152][304], lk_o_pb[152][304];                  /* layer cells: bit 16 = present, low 16 = tile word */
static uint16 lk_o_spr[224][320];                                    /* pal * 16 + index | 0x100 priority | 0x200 present */
static uint8 lk_o_sprtiles[0x4000];
static uint8 lk_o_hud[0x1000]; static int lk_o_hudn = -1;      /* StatusBarGfx $009242 (HUD tiles, tile numbers $6B4 ..) */
static long lk_o_diff, lk_o_tot; static int lk_o_nspr;
static int lk_o_lz77(uint32_t pos, uint8 *out, int cap) {            /* DecompressLZ77Gfx $004AB2 */
  int n = 0, i, flags;
  for (;;) {
    flags = OB(pos++);
    for (i = 0; i < 8; i++) {
      if ((flags >> (7 - i)) & 1) { if (n < cap) out[n] = (uint8)OB(pos); n++; pos++; }
      else {
        int b1 = OB(pos), b2 = OB(pos + 1), off, len, k; pos += 2;
        off = ((b1 >> 4) << 8) | b2; if (!off) return n;
        len = 18 - (b1 & 15);
        for (k = 0; k < len; k++) { if (n < cap) out[n] = (n - off >= 0 && n - off < cap) ? out[n - off] : 0; n++; }
      }
      if (n > 0x10000) return n;
    }
  }
}
static void lk_o_room_load(int room) {                               /* tile graphics + animated tile groups of a room */
  uint32_t tab = OL(0xA0A00), e = tab + 8u * (uint32_t)room, tp = OL(0x44010);
  int tileset = OB(e + 4) & 0x1F, i; uint32_t tptr;
  tptr = OL(tp + 4u * (uint32_t)tileset);
  memset(lk_o_tbase, 0, sizeof lk_o_tbase);
  lk_o_lz77(tptr, lk_o_tbase, 0x10000);
  lk_o_ngrp = 0;
  for (i = 0; OB(0x9E04 + i) != 0xFF; i++) if (OB(0x9E04 + i) == tileset && lk_o_ngrp < 8) {
    uint32_t a = 0x9E1C + 10u * (uint32_t)i;
    lk_o_grp[lk_o_ngrp].dest = OW(a); lk_o_grp[lk_o_ngrp].words = OW(a + 2); lk_o_grp[lk_o_ngrp].delay = OB(a + 4); lk_o_grp[lk_o_ngrp].frames = OB(a + 5);
    lk_o_grp[lk_o_ngrp].base = OL(OL(a + 6)); lk_o_ngrp++;
  }
  lk_o_room = room;
}

static PIXEL_OUT_T lk_o_pix[64]; static int lk_o_palmode = 1;
static int lk_o_darken(int c, int d3) {                              /* DarkenColour $0009FC with target 0 */
  int b = ((c & 0xE00) - d3) & 0x1E00, g3 = d3 >> 4, g, r3 = g3 >> 4, r;
  if (b >= 0x1000) b = 0;
  g = ((c & 0xE0) - g3) & 0x1E0; if (g >= 0x100) g = 0;
  r = ((c & 0xE) - r3) & 0x1E; if (r >= 0x10) r = 0;
  return b | g | r;
}
static void lk_o_palette(int room) {                                 /* the 64 colours of the picture from ROM data + game state (romsprite.sprite_palettes / romrender.rom_cram) */
  int pal[64], i, j, l, n, typ, ts, k, sword = SB(0xFF114E), armour = SB(0xFF114F), act[64], bestn = 99, bestd = 0;
  uint32_t a, e, pbase;
  memset(pal, 0, sizeof pal);
  for (i = 0; i < 16; i++) pal[32 + i] = OW(0x901C + 2 * i);                                         /* line 2: Nigel */
  for (l = 0; l < 2; l++) {                                                                           /* armour colours 11 / 12, sword colours 13 / 14 */
    uint32_t idx = l ? 0x78F4 : 0x78FA, swaps = l ? 0x7900 : 0x7918; int item = l ? sword : armour;
    for (k = 0; k < 6 && OB(idx + (uint32_t)k) != item; k++) ;
    if (k > 5) k = 5;
    pal[32 + 11 + 2 * l] = OW(swaps + 4u * (uint32_t)k); pal[32 + 12 + 2 * l] = OW(swaps + 4u * (uint32_t)k + 2);
  }
  for (i = 0; i < 5; i++) pal[48 + 10 + i] = OW(0x903C + 2 * i);                                      /* line 3: HUD colours 10..14 */
  a = 0xFF5480;
  for (n = 0; n < 15 && !(SW(a) & 0x8000); n++, a += 0x80) {                                           /* InitSpritePalettes / GetSpritePalette */
    typ = SB(a + 0x3B); ts = SW(a + 6);
    if (!((ts >> 8) & 0x20)) continue;
    for (e = 0x1A453A; OB(e) != 0xFF && e < 0x1A47E0; e += 2) if (OB(e) == typ) {
      int v = OB(e + 1), hi = v & 0x80, idx = v & 0x7F, pal3 = (ts >> 8) & 0x40;
      if (hi) { if (!pal3) for (j = 0; j < 7; j++) pal[16 + 8 + j] = OW(0x1A4BA0 + 14u * (uint32_t)idx + 2u * (uint32_t)j); }
      else { int base = pal3 ? 48 + 2 : 16 + 2; for (j = 0; j < 6; j++) pal[base + j] = OW(0x1A47E0 + 12u * (uint32_t)idx + 2u * (uint32_t)j); }
    }
  }
  pal[56] = SW(0xFF00E0 + 0x10); pal[57] = SW(0xFF00E0 + 0x12); pal[29] = SW(0xFF00A0 + 0x1A); pal[30] = SW(0xFF00A0 + 0x1C);   /* projectile colours: event state */
  pbase = 0x11C926u + 26u * (uint32_t)OB(OL(0xA0A00) + 8u * (uint32_t)room + 5);                      /* line 0: room palette */
  for (i = 0; i < 13; i++) pal[2 + i] = OW(pbase + 2u * (uint32_t)i);
  for (l = 0; l < 4; l++) { pal[16 * l] = 0; pal[16 * l + 1] = 0x0CCC; pal[16 * l + 15] = 0; }
  for (i = 0; i < 64; i++) act[i] = SW(0xFF0ED0 + 2 * i);                                             /* fade level: the one that reproduces the active palette copy best */
  for (j = 0; j < 0x1400; j += 0x200) { int bad = 0; for (i = 0; i < 64; i++) if (lk_o_darken(pal[i], j) != act[i]) bad++; if (bad < bestn) { bestn = bad; bestd = j; } }
  for (i = 0; i < 64; i++) { int c = lk_o_darken(pal[i], bestd); lk_o_pix[i] = pixel_lut[1][((c >> 9) & 7) << 6 | ((c >> 5) & 7) << 3 | ((c >> 1) & 7)]; }
}
static void lk_o_sprpiece(const uint8 *td, int tile0, int sx, int sy, int w, int h, int pal, int prio, int hf, int vf) {
  int px, py;
  for (px = 0; px < w * 8; px++) for (py = 0; py < h * 8; py++) {
    int ox = hf ? (w * 8 - 1 - px) : px, oy = vf ? (h * 8 - 1 - py) : py, t = tile0 + (ox / 8) * h + (oy / 8), a = t * 32 + (oy % 8) * 4 + (ox % 8) / 2, b, idx, X = sx + px, Y = sy + py;
    if (a >= 0x4000) continue;
    b = td[a]; idx = ((ox % 8) % 2 == 0) ? (b >> 4) : (b & 15);
    if (!idx || X < 0 || X >= 320 || Y < 0 || Y >= 224 || (lk_o_spr[Y][X] & 0x200)) continue;
    lk_o_spr[Y][X] = (uint16)(0x200 | (prio ? 0x100 : 0) | (pal * 16 + idx));
  }
}
static void lk_o_build(void) {                                       /* everything of one frame from the snapshot */
  int x, y, k, a, o;
  /* tiles + animation */
  memcpy(lk_o_tiles, lk_o_tbase, sizeof lk_o_tiles);
  for (k = 0; k < lk_o_ngrp; k++) {
    int s0 = 0xFF1134 + 4 * k;
    if (SB(s0) == lk_o_grp[k].delay && SB(s0 + 1) == lk_o_grp[k].frames) {
      int f = SB(s0 + 3) % lk_o_grp[k].frames, n = lk_o_grp[k].words * 2, i; uint32_t src = lk_o_grp[k].base + (uint32_t)(f * n);
      for (i = 0; i < n; i++) if (lk_o_grp[k].dest + i < (int)sizeof lk_o_tiles) lk_o_tiles[lk_o_grp[k].dest + i] = (uint8)OB(src + (uint32_t)i);
    }
  }
  /* layers */
  memset(lk_o_pa, 0, sizeof lk_o_pa); memset(lk_o_pb, 0, sizeof lk_o_pb);
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
    int lay;
    for (lay = 0; lay < 2; lay++) {
      int id = UW((lay ? 0xFF7C02 : 0xFFA6CA) + 148 * y + 2 * x) & 0x3FF, c0 = 2 * (x - y) + (lay ? 146 : 148), r0 = x + y;
      if (!id) continue;
      for (k = 0; k < 4; k++) {
        int w = UW(0xFF5C02 + 2 * (4 * id + k)), cc = c0 + (k & 1), rr = r0 + (k >> 1);
        if (cc >= 0 && cc < 304 && rr >= 0 && rr < 152) (lay ? lk_o_pa : lk_o_pb)[rr][cc] = 0x10000u | (uint32_t)w;
      }
    }
  }
  /* figures */
  memset(lk_o_spr, 0, sizeof lk_o_spr); lk_o_nspr = 0;
  a = 0xFF11DE;
  for (;;) {
    int guard, off = SW(a), b, ax, ay, ts, sgi, anim, frm, hf, pc, pxs[8], pys[8], pws[8], phs[8], np = 0, cum = 0, tl = 0, prio;
    uint32_t base, fp, ap, pos;
    a += 2;
    if ((off & 0x8000) || a > 0xFF11DE + 40) break;
    b = 0xFF5400 + off; ax = SW(b + 0x0E); ay = SW(b + 0x10); ts = SW(b + 6);
    if (ax == 0 && ay == 0) continue;
    if (SB(b + 0x0C) & 0x40) continue;                                  /* Flags2 bit 6 = hidden (the player's hurt blink toggles it every pass) */
    sgi = SB(b + 0x0B); anim = SW(b + 0x24); frm = SW(b + 0x26);
    base = OL(0x120000); { int ofs = OW(0x120004 + 4 * sgi); ap = OL(base + (uint32_t)ofs * 4 + (uint32_t)anim); }
    fp = OL(ap + (uint32_t)frm); pos = fp;
    for (;;) {
      int b1 = OB(pos), b2 = OB(pos + 1), yy = (b1 << 1) & 0xF8, xx = (b2 << 1) & 0xF8; pos += 2;
      if (yy > 127) yy -= 256; if (xx > 127) xx -= 256;
      pxs[np] = xx; pys[np] = yy; pws[np] = (b1 & 3) + 1; phs[np] = (b2 & 3) + 1; np++;
      if ((b2 & 0x80) || np >= 8) break;
    }
    for (guard = 0; guard < 64; guard++) {
      int h = OW(pos), n = h & 0x0FFF, i; pos += 2;
      if (h & 0x8000) { for (i = 0; i < n * 2 && tl + i < 0x4000; i++) lk_o_sprtiles[tl + i] = 0; tl += n * 2; }
      else if (h & 0x2000) { tl += lk_o_lz77(pos, lk_o_sprtiles + tl, 0x4000 - tl); break; }
      else { for (i = 0; i < n * 2 && tl + i < 0x4000; i++) lk_o_sprtiles[tl + i] = (uint8)OB(pos + (uint32_t)i); pos += (uint32_t)n * 2; tl += n * 2; }
      if (h & 0x4000) break;
    }
    lk_o_nspr++;
    hf = (ts >> 11) & 1; prio = SW(0xFF1400 + (off >> 1) + 4) >> 15;
    for (pc = 0; pc < np; pc++) {
      int xx = hf ? (-pxs[pc] - 8 * pws[pc]) : pxs[pc];
      lk_o_sprpiece(lk_o_sprtiles, cum, ax + xx - 128, ay + pys[pc] - 128, pws[pc], phs[pc], (ts >> 13) & 3, prio, hf, (ts >> 12) & 1);
      cum += pws[pc] * phs[pc];
    }
  }
  (void)o;
}
static int lk_o_fetch(uint32 (*pl)[304], int U, int V, int *pal, int *prio) {   /* colour index of one plane pixel at image position (U, V), 0 = transparent */
  int tc = U >> 3, tr = V >> 3, ix = U & 7, iy = V & 7; uint32 c; int w, t, b;
  if (U < 0 || V < 0 || tc >= 304 || tr >= 152) return 0;
  c = pl[tr][tc]; if (!(c & 0x10000)) return 0;
  w = (int)(c & 0xFFFF); if (w & 0x800) ix = 7 - ix; if (w & 0x1000) iy = 7 - iy;
  t = w & 0x7FF; if (t * 32 + 31 >= (int)sizeof lk_o_tiles) return 0;
  b = lk_o_tiles[t * 32 + iy * 4 + ix / 2]; *pal = (w >> 13) & 3; *prio = (w >> 15) & 1;
  return (ix % 2 == 0) ? (b >> 4) : (b & 15);
}

static int lk_o_win(int line, int x, int hint) {                      /* window plane pixel (palette * 16 + index) or -1 = none: HUD rows 0..2, text box rows 20..27 (tilemap in RAM, tiles from ROM / the text tile buffer) */
  int r = line >> 3, w, t, b, ix = x & 7, iy = line & 7;
  if (line < 24) { w = SW(0xFF1C00 + 0x80 * r + 2 * (x >> 3)); }
  else if (line >= 160 && (hint & 0xFF) == 0xA0) { w = SW(0xFF2600 + 0x80 * (r - 20) + 2 * (x >> 3)); }
  else return -1;
  if (w & 0x800) ix = 7 - ix; if (w & 0x1000) iy = 7 - iy;
  t = w & 0x7FF;
  if (t >= 0x6B4 && t < 0x6B4 + 76) b = lk_o_hud[(t - 0x6B4) * 32 + iy * 4 + ix / 2];
  else if (t >= 0x528 && t < 0x528 + 0xD8) b = SB(0xFF3900 + (t - 0x528) * 32 + iy * 4 + ix / 2);
  else b = 0;
  return ((w >> 13) & 3) * 16 + ((ix % 2 == 0) ? (b >> 4) : (b & 15)) + 0x100;     /* bit 8 marks 'window pixel' (index 0 = backdrop) */
}
static int lk_o_unwrap(int p, int base, int size) { int d = (((p - base) % size) + size) % size; if (d >= size / 2) d -= size; return base + d; }
static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {
  static int hint, fr_done = -1, hsA, hsB, vsA, vsB, cam0, cam2, rm; static long fr_n;
  int x;
  if (lk_o_mode < 0) { const char *e = getenv("LANDSTALKER_OWN"), *l = getenv("LANDSTALKER_OWN_LOG"); lk_o_mode = e ? atoi(e) : 0; if (l) lk_o_log = atoi(l); { const char *q = getenv("LANDSTALKER_OWN_SPR"); if (q) lk_o_sprmode = atoi(q); q = getenv("LANDSTALKER_OWN_PAL"); if (q) lk_o_palmode = atoi(q); } }
  if (!lk_o_mode) return;
  if (line == 0) {
    const uint8_t *r = bus_get_ram(); int hsb = (reg[13] & 0x3F) << 10;
    if (!r) return;
    if (lk_o_valid) {                                                 /* state of the previous pass = the picture shown now */
      memcpy(lk_o_use, lk_o_prev, sizeof lk_o_use);
      hsA = ((vram[hsb ^ 1] << 8) | vram[(hsb + 1) ^ 1]); hsB = ((vram[(hsb + 2) ^ 1] << 8) | vram[(hsb + 3) ^ 1]);
      vsA = (vsram[0 ^ 1] << 8) | vsram[1 ^ 1]; vsB = (vsram[2 ^ 1] << 8) | vsram[3 ^ 1];
      cam0 = US(0xFF1200); cam2 = US(0xFF1202); rm = UW(0xFF1204); hint = r[(0xFF0FC5 & 0xFFFF) ^ 1];
      if (rm > 0 && rm < 800) { if (rm != lk_o_room) lk_o_room_load(rm); lk_o_sp = lk_o_sprmode ? r : lk_o_use; lk_o_build(); if (lk_o_palmode) lk_o_palette(rm); fr_done = 1; } else fr_done = 0;
    } else fr_done = 0;
    memcpy(lk_o_prev, r, sizeof lk_o_prev); lk_o_valid = 1;
    fr_n++;
    if (lk_o_diff >= 0 && lk_o_log > 0 && fr_n % lk_o_log == 0) { int ca = 0, cb = 0, tn = 0, i2, j2; for (i2 = 0; i2 < 152; i2++) for (j2 = 0; j2 < 304; j2++) { ca += (lk_o_pa[i2][j2] >> 16) & 1; cb += (lk_o_pb[i2][j2] >> 16) & 1; } for (i2 = 0; i2 < 0x12000; i2++) tn += lk_o_tiles[i2] != 0;
      printf("own: frame %ld room %d lines 0..223: %ld of %ld pixels differ (cells A %d B %d, tile bytes %d, scroll A %d,%d B %d,%d cam %d,%d, player flags2 use %02X cur %02X, sprites %d)\n", platform_frame_number(), rm, lk_o_diff, lk_o_tot, ca, cb, tn, hsA, vsA, hsB, vsB, cam0, cam2, UB(0xFF540C), bus_get_ram()[(0xFF540C & 0xFFFF) ^ 1], lk_o_nspr); }
    lk_o_diff = 0; lk_o_tot = 0;
  }
  if (!fr_done || w != 320) return;
  if (lk_o_hudn < 0) lk_o_hudn = lk_o_lz77(0x9242, lk_o_hud, 0x1000);
  {
    int ubase = 1184 - (cam2 - cam0 + 160), vbase = ((cam0 + cam2) >> 1) - 104 + line;
    int pyA = (line + vsA) & 255, pyB = (line + vsB) & 255;
    for (x = 0; x < 320; x++) {
      int pxA = (x - hsA) & 511, pxB = (x - hsB) & 511, pal, prio, idx, pick = -1, pp, pi, ap = 0, bp = 0, ai, bi, apal = 0, bpal = 0, sp = lk_o_spr[line][x], col;
      int UA = ubase + x, UB_ = ubase + x, VA = vbase, VB = vbase;      /* image coordinates: independent of the VDP planes and their wrap */
      ai = lk_o_fetch(lk_o_pa, UA, VA, &apal, &ap); bi = lk_o_fetch(lk_o_pb, UB_, VB, &bpal, &bp);
      (void)pal; (void)prio; (void)idx; (void)pp; (void)pi;
      if ((sp & 0x200) && (sp & 0x100)) pick = sp & 0x3F;
      else if (ai && ap) pick = apal * 16 + ai;
      else if (bi && bp) pick = bpal * 16 + bi;
      else if (sp & 0x200) pick = sp & 0x3F;
      else if (ai) pick = apal * 16 + ai;
      else if (bi) pick = bpal * 16 + bi;
      else pick = reg[7] & 0x3F;                                       /* backdrop colour */
      { int wp = lk_o_win(line, x, hint); if (wp >= 0 && (wp & 0xF)) pick = wp & 0x3F; else if (line >= 185 && !(line >= 160 && (hint & 0xFF) == 0xA0)) pick = -1; }   /* transparent window pixels show the map */
      col = pick < 0 ? pixel_lut[1][0] : (lk_o_palmode ? lk_o_pix[pick & 0x3F] : pixel[pick & 0x3F]);
      lk_o_tot++; if (row[x] != (PIXEL_OUT_T)col) lk_o_diff++;
      if (lk_o_mode == 2) row[x] = (PIXEL_OUT_T)col;
    }
  }
}

'''
    s = s.replace(c, module + c, 1)
    open(p, "w").write(s)
    print("patched vdp_render.c: " + VER)
else:
    print("vdp_render.c already patched: " + VER)
