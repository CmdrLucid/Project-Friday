#!/usr/bin/env python3
"""Boot colours (2026-11-04, user: 'wenn Nigel Schwert oder Ruestung wechselt passt sich sein Sprite an, nur bei seinen Schuhen nicht;
als optionalen Punkt unter Graphics').  The game shows the equipped sword and armour on Nigel through palette line 2 (UpdateEquipPal
$0078B6: colours 43 / 44 armour, 45 / 46 sword), but his boots are painted with the same four browns as his hair, gloves and shoulder
plates (line 2 entries 8 / 3 / 4 / 5 = colours 40 / 35 / 36 / 37: highlight, light, mid, dark), so a palette swap is impossible.
The own map renderer recolours only the BOOT pixels instead:
 * boot mask per pose (Nigel = sprite graphic 0, entity slot 0): the pose is assembled from its pieces (the tiles the renderer already
   decoded from the ROM), the 4-connected areas of the four browns are found (the black outline separates boots / gloves / hair);
   an area is a boot when its centre lies in the lowest 30 % of the figure (figures at least 34 px tall) and it is not a small (< 20 px)
   piece touching the scabbard highlight (entry 1) or the sword colours (13 / 14: the scabbard end hangs at boot height); the lying / falling poses
   (animations $40 / $44 / $48) and the walk pose with the raised sole ($08 / $18 frame 12) use hand picked seed pixels, the jump poses
   ($20 / $28 frame 0, scabbard end merged into the boot shaft) a row cut (lk_bc_seed, checked with the user on 2026-11-04 on numbered
   pose sheets: bed picture, gloves in the lying poses, raised sole rim of pose 6, scabbard end of pose 41);
   animation $48 frames >= 20 (not Nigel) get no mask.  Masks are cached per (animation, frame), in tile space (64 bits per tile),
   so flips need nothing extra.
 * colours per boots (EquippedBoots $FF1150; from the item icons, InvItemPal $007896): 5 Fireproof blue-violet, 6 Iron steel grey,
   7 Healing green, 8 Spike dark violet; none ($3C) = the original brown.  The current brightness of the pixel (palette fades,
   flash bands) is kept: boot colour x (current colour / the default colour of that entry, DefaultPlayerPal $00901C).
 * applied before Lighting, so flames / sun shade the new colour like the rest of Nigel.
Picture only, the game state is untouched (option Off = bit exact).  Not on screens drawn by the screen renderer (file select).
Option: Options > Graphics > Boot Colors Off / On (id 48, ~/.landstalker_bootcol, env LANDSTALKER_BOOTCOL=0|1), default Off.
Test aid: LANDSTALKER_BOOTCOL_KIND=5..8 = show those boots whatever is equipped (option on); LANDSTALKER_BOOTCOL_DBG=1 prints the boot pixel
count of every pose when its mask is built.
Needs patch_own.py, patch_swordfx.py, patch_lights.py before it.  Idempotent.
usage: patch_bootcol.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_BOOTCOL v1"
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER in s:
    print("vdp_render.c already patched:", VER); sys.exit(0)

def rep(a, b, cnt=1):
    global s
    assert s.count(a) == cnt, f"vdp_render.c layout changed: {a[:70]!r} ({s.count(a)}x)"
    s = s.replace(a, b, 1)

GLOBALS = r'''/* ---- @VER@: boot colours (tools/patch_bootcol.py) ---- */
static int lk_bc_o = -1, lk_bc_kind;
int lk_bc_get(void) { if (lk_bc_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_BOOTCOL"); char pth[512]; FILE *f; int v = 0; snprintf(pth, sizeof pth, "%s/.landstalker_bootcol", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); lk_bc_o = v ? 1 : 0; } return lk_bc_o; }
void lk_bc_set(int v) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_bc_get(); lk_bc_o = v ? 1 : 0; snprintf(pth, sizeof pth, "%s/.landstalker_bootcol", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%d\n", lk_bc_o); fclose(f); } }
static const uint64_t *lk_bc_cur;                 /* boot mask (per tile, bit = y * 8 + x) of the figure lk_o_sprpiece is drawing, 0 = none */
static uint16 lk_bc_st[224][LK_OSW]; static uint16 lk_bc_stamp = 1;   /* sprite layer pixel is a boot pixel when its stamp = the current draw's */
static int lk_bc_curkind(void) {                  /* 5..8 = boots to show, 0 = nothing to do */
  static int tk = -1; int b;
  if (!lk_bc_get()) return 0;
  if (tk < 0) { const char *e = getenv("LANDSTALKER_BOOTCOL_KIND"); tk = (e && *e) ? atoi(e) : 0; }
  if (tk >= 5 && tk <= 8) return tk;
  b = bus_read8(0xFF1150u);                       /* EquippedBoots */
  return (b >= 5 && b <= 8) ? b : 0;
}
'''

MASK = r'''/* @VER@: boot mask of one of Nigel's poses */
typedef struct { uint8 done, any; uint64_t m[64]; } lk_bc_mask_t;
static lk_bc_mask_t lk_bc_cache[19 * 32];
static const struct { uint8 anim, frm, n; int8_t cut, x[5], y[5]; } lk_bc_seed[] = {   /* n > 0: the boot areas are the ones holding these pixels (pose space); cut: boot pixels only from this row down (-128 = all) */
  { 0x08, 12, 5, -128, { -1, -10, -11, -12, -10 }, { -7, -13, -8, -6, 0 } },   /* walk, raised boot seen from below: its rim sat too high for the 30 % rule */
  { 0x18, 12, 5, -128, { -1, -10, -11, -12, -10 }, { -7, -13, -8, -6, 0 } },
  { 0x20, 0, 0, -7, { 0 }, { 0 } }, { 0x28, 0, 0, -7, { 0 }, { 0 } },   /* jump: the scabbard end runs into the boot shaft without an outline */
  { 0x40, 8, 2, -128, { -4, 6 }, { -5, -15 } }, { 0x44, 4, 1, -128, { -1 }, { 0 } }, { 0x44, 8, 2, -128, { -12, -1 }, { -6, -1 } }, { 0x44, 16, 2, -128, { -12, -1 }, { -6, -1 } },
  { 0x44, 12, 2, -128, { -11, -1 }, { -6, -2 } }, { 0x48, 4, 1, -128, { -1 }, { -10 } }, { 0x48, 8, 2, -128, { -1, -10 }, { -9, -12 } }, { 0x48, 16, 2, -128, { -1, -10 }, { -9, -12 } },
  { 0x48, 12, 2, -128, { -1, -9 }, { -10, -12 } } };
#define LK_BC_G 128
#define LK_BC_OX 64
#define LK_BC_OY 96
static int lk_bc_brown(int v) { return v == 3 || v == 4 || v == 5 || v == 8; }
static const uint64_t *lk_bc_mask(const lk_o_ent_t *e) {
  static int16_t gt[LK_BC_G][LK_BC_G]; static uint8 gc[LK_BC_G][LK_BC_G]; static int16_t lab[LK_BC_G][LK_BC_G]; static int16_t stk[LK_BC_G * LK_BC_G][2];
  int ai = e->anim / 4, fi = e->frm / 4, pc, cum = 0, x, y, top = 1 << 20, bot = -(1 << 20), nc = 0, si = -1, k, cut = -1000;
  lk_bc_mask_t *c;
  if (e->sgi != 0 || (e->anim & 3) || (e->frm & 3) || ai < 0 || ai >= 19 || fi < 0 || fi >= 32 || !e->tiles) return 0;
  c = &lk_bc_cache[ai * 32 + fi];
  if (c->done) return c->any ? c->m : 0;
  c->done = 1; c->any = 0; memset(c->m, 0, sizeof c->m);
  if (e->anim == 0x48 && e->frm >= 20) return 0;
  for (k = 0; k < (int)(sizeof lk_bc_seed / sizeof lk_bc_seed[0]); k++) if (lk_bc_seed[k].anim == e->anim && lk_bc_seed[k].frm == e->frm) { if (lk_bc_seed[k].n) si = k; if (lk_bc_seed[k].cut != -128) cut = lk_bc_seed[k].cut + LK_BC_OY; }
  memset(gc, 0, sizeof gc); memset(lab, 0, sizeof lab);
  for (pc = 0; pc < e->np; pc++) {                /* assemble the pose like lk_o_sprpiece (tiles column-major per piece, no flip) */
    int w = e->pws[pc], h = e->phs[pc], cx, cy, px, py;
    for (cx = 0; cx < w; cx++) for (cy = 0; cy < h; cy++) {
      int t = cum + cx * h + cy;
      for (py = 0; py < 8; py++) for (px = 0; px < 8; px++) {
        int a = t * 32 + py * 4 + px / 2, v, X = e->pxs[pc] + cx * 8 + px + LK_BC_OX, Y = e->pys[pc] + cy * 8 + py + LK_BC_OY;
        if (t >= 64 || a >= 0x4000 || X < 0 || X >= LK_BC_G || Y < 0 || Y >= LK_BC_G) continue;
        v = (px % 2 == 0) ? (e->tiles[a] >> 4) : (e->tiles[a] & 15);
        if (!v) continue;
        gc[Y][X] = (uint8)v; gt[Y][X] = (int16_t)(t * 64 + py * 8 + px);
        if (Y < top) top = Y; if (Y > bot) bot = Y;
      }
    }
    cum += w * h;
  }
  if (bot < top) return 0;
  for (y = 0; y < LK_BC_G; y++) for (x = 0; x < LK_BC_G; x++) {   /* 4-connected areas of the four browns */
    int n = 0, sp = 0, take = 0, nsw = 0; long sumy = 0;
    if (!lk_bc_brown(gc[y][x]) || lab[y][x]) continue;
    if (++nc > 30000) return 0;
    lab[y][x] = (int16_t)nc; stk[sp][0] = (int16_t)x; stk[sp][1] = (int16_t)y; sp++;
    while (sp > 0) {
      int qx, qy, d; sp--; qx = stk[sp][0]; qy = stk[sp][1]; n++; sumy += qy;
      for (d = 0; d < 9; d++) { int rx = qx + d % 3 - 1, ry = qy + d / 3 - 1, v2 = (rx >= 0 && rx < LK_BC_G && ry >= 0 && ry < LK_BC_G) ? gc[ry][rx] : 0; if (v2 == 1 || v2 == 13 || v2 == 14) nsw = 1; }   /* touches the scabbard highlight / sword colours */
      if (si >= 0) for (k = 0; k < lk_bc_seed[si].n; k++) if (qx == lk_bc_seed[si].x[k] + LK_BC_OX && qy == lk_bc_seed[si].y[k] + LK_BC_OY) take = 1;
      for (d = 0; d < 4; d++) { int rx = qx + (d == 0) - (d == 1), ry = qy + (d == 2) - (d == 3);
        if (rx >= 0 && rx < LK_BC_G && ry >= 0 && ry < LK_BC_G && !lab[ry][rx] && lk_bc_brown(gc[ry][rx])) { lab[ry][rx] = (int16_t)nc; stk[sp][0] = (int16_t)rx; stk[sp][1] = (int16_t)ry; sp++; } }
    }
    if (si < 0) { int H = bot - top + 1; take = H >= 34 && 10 * sumy >= (long)n * (10 * bot - 3 * H) && !(n < 20 && nsw); }   /* centre in the lowest 30 %; small brown bits at the scabbard / sword (its end, the hilt) are no boot */
    if (take) { int x2, y2; for (y2 = top; y2 <= bot; y2++) for (x2 = 0; x2 < LK_BC_G; x2++) if (lab[y2][x2] == nc && y2 >= cut) { int g = gt[y2][x2]; c->m[g >> 6] |= 1ull << (g & 63); c->any = 1; } }
  }
  if (getenv("LANDSTALKER_BOOTCOL_DBG")) { int q, nb = 0; for (q = 0; q < 64; q++) nb += __builtin_popcountll(c->m[q]); printf("bootcol: anim %X frm %X boot px %d\n", e->anim, e->frm, nb); }   /* test aid: compare with the Python check */
  return c->any ? c->m : 0;
}
static PIXEL_OUT_T lk_bc_md(int c) { return pixel_lut[1][((c >> 9) & 7) << 6 | ((c >> 5) & 7) << 3 | ((c >> 1) & 7)]; }
static const uint16 lk_bc_col[4][4] = {           /* entries 8 / 3 / 4 / 5 (highlight, light, mid, dark) per boots 5..8, MD colour words */
  { 0x0ECC, 0x0E88, 0x0A44, 0x0622 },             /* 5 Fireproof: blue-violet like its icon */
  { 0x0EEE, 0x0AAA, 0x0886, 0x0444 },             /* 6 Iron: steel grey */
  { 0x0AEA, 0x04C4, 0x0282, 0x0040 },             /* 7 Healing: green */
  { 0x0A8A, 0x0646, 0x0424, 0x0202 } };           /* 8 Spike: dark violet */
static int lk_bc_linebegin(void) { lk_bc_kind = lk_bc_curkind(); return lk_bc_kind != 0; }
static PIXEL_OUT_T lk_bc_pix(int sl, int si, int sp, PIXEL_OUT_T col) {   /* one composed map pixel won by a sprite pixel */
  static const int ent[4] = { 8, 3, 4, 5 }; int k, ch; uint32_t b, o, r = (uint32_t)col & 0xFF000000u; unsigned sb = 0, sc = 0;
  if (sl < 0 || sl >= 224 || si < 0 || si >= LK_OSW || lk_bc_st[sl][si] != lk_bc_stamp || lk_bc_kind < 5 || lk_bc_kind > 8) return col;
  switch (sp & 0x3F) { case 40: k = 0; break; case 35: k = 1; break; case 36: k = 2; break; case 37: k = 3; break; default: return col; }
  b = (uint32_t)lk_bc_md(OW(0x901C + 2 * ent[k])); o = (uint32_t)lk_bc_md(lk_bc_col[lk_bc_kind - 5][k]);   /* DefaultPlayerPal entry / the boots' colour */
  for (ch = 0; ch < 24; ch += 8) { sb += (b >> ch) & 255; sc += ((uint32_t)col >> ch) & 255; }
  if (!sb) return col;
  for (ch = 0; ch < 24; ch += 8) { unsigned v = (((o >> ch) & 255) * sc + sb / 2) / sb; r |= (uint32_t)(v > 255 ? 255 : v) << ch; }   /* keep the current brightness (fades, flash bands) */
  return (PIXEL_OUT_T)r;
}

'''.replace("@VER@", VER)

# 1. globals before the sprite piece drawer
a = "static void lk_o_sprpiece(const uint8 *td, int tile0, int sx, int sy, int w, int h, int pal, int prio, int hf, int vf) {\n"
rep(a, GLOBALS.replace("@VER@", VER) + a)
# 2. mark boot pixels in lk_o_sprpiece only (lk_o_vpiece has the same line)
k0 = s.find(a); k1 = s.find("static void lk_o_vpiece(", k0)
seg = s[k0:k1]
b = "lk_lt_spre[Y][X] = (uint8)lk_lt_ecur; /*LK_LT_ENT*/\n"
assert seg.count(b) == 1, "lk_o_sprpiece layout changed"
seg = seg.replace(b, b + "    if (lk_bc_cur && t < 64 && ((lk_bc_cur[t] >> ((oy % 8) * 8 + (ox % 8))) & 1)) lk_bc_st[Y][X] = lk_bc_stamp;   /* " + VER + " */\n", 1)
s = s[:k0] + seg + s[k1:]
# 3. mask code after the entity type
rep("static int lk_o_sprites(const uint8 *src, int draw, uint32 *keys, const uint8 *alt) {", MASK + "static int lk_o_sprites(const uint8 *src, int draw, uint32 *keys, const uint8 *alt) {")
# 4. a new stamp per drawn sprite layer
rep("  if (draw) { memset(lk_o_spr, 0, sizeof lk_o_spr);", "  if (draw && ++lk_bc_stamp == 0) { memset(lk_bc_st, 0, sizeof lk_bc_st); lk_bc_stamp = 1; }   /* %s */\n  if (draw) { memset(lk_o_spr, 0, sizeof lk_o_spr);" % VER)
# 5. Nigel's pieces carry the mask
a = "      if (draw) lk_o_sprpiece(e->tiles, cum, e->ax + xx - 128, e->ay + e->pys[pc] - 128, e->pws[pc], e->phs[pc], (e->ts >> 13) & 3, e->prio, (e->ts >> 11) & 1, (e->ts >> 12) & 1);\n"
rep(a, "      if (draw) { lk_bc_cur = (offs[k] == 0 && lk_bc_curkind()) ? lk_bc_mask(e) : 0;   /* %s */\n" % VER +
       "        lk_o_sprpiece(e->tiles, cum, e->ax + xx - 128, e->ay + e->pys[pc] - 128, e->pws[pc], e->phs[pc], (e->ts >> 13) & 3, e->prio, (e->ts >> 11) & 1, (e->ts >> 12) & 1); lk_bc_cur = 0; }\n")
# 6. the composed pixel, before Lighting
rep("int lk_sfx_ln = lk_sfx_linebegin(line);", "int lk_sfx_ln = lk_sfx_linebegin(line); int lk_bc_ln = lk_bc_linebegin();   /* %s */" % VER)
a = "      if (lk_lt_ln && !black && (src == 1 || src == 2 || src == 3)) col = lk_lt_pix("
rep(a, "      if (lk_bc_ln && !black && src == 1) col = lk_bc_pix(sl, si, sp, col);   /* %s */\n" % VER + a)
open(p, "w").write(s)
print("vdp_render.c patched:", VER)
