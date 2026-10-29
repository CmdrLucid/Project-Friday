#!/usr/bin/env python3
"""Gameplay option 'Shadow' (2026-10-13): a round shadow on the ground under Nigel (and, in mode 'All', under objects / enemies that are in the air) so that jumps in the isometric view are easier to judge.
Modes (~/.landstalker_gameplay, env LANDSTALKER_SHADOW=0|1): 0 off, 1 on = a shadow under everything that is in the air (Nigel jumping / falling, floating objects and enemies without a shadow of their own); things standing on the ground get none.
How it works (no game state is changed, only the picture):
 * func_table.c: a wrapper of BuildEntitySpriteEntries ($00437A, called for every visible entity right after CheckEntityOnScreen stored its screen position in +0E (X) / +10 (Y), VDP sprite coordinates, 128 = screen 0).
   After the original it asks the game's own GetDistanceToGround ($0032C6, a0 = entity, d5 = Z - ground under the entity: height map and platform-like entities) and records a shadow at (X, Y + d5): one Z unit is one screen pixel
   (CheckEntityOnScreen: screen Y = (x + y - 2 z) / 2). The size comes from the entity's box (+18..+1E). GetDistanceToGround writes the cache byte +39 of the entity: it is saved and restored.
 * vdp_render.c: lk_shadow_line() runs in render_line right before remap_line: for the ellipse pixels that are not covered by a sprite pixel (linebuf[1]) and are not backdrop it sets bit 7 of the final VDP pixel,
   and color_update_m5 now fills pixel[0x80 | index] with a darkened colour (in normal, non shadow/highlight mode bit 7 was never used). The snapshot recorded during the game's sprite pass becomes active at line 0 of the next frame.
Idempotent.  usage: patch_shadow.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]

# ---- vdp_render.c ----
import re
_ids = []
_deny = re.compile(r"platform|switch|cube|block|gate|door|barrier|spawner|projectile|fireball|(?:^|_)ink(?:_|$)|item_box|raft|crate|money_bag|chest|ball|signpost|sign_post|rock|spikeball|spinner|(?:^|_)wall(?:_|$)")
for _l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'ENTITIES.md')):   # entity types that are NOT creatures / bodies standing on the ground (docs/ENTITIES.md names): no contact shadow for them
    _c = [x.strip() for x in _l.split('|')]
    if len(_c) > 5 and _c[1].isdigit() and _deny.search(_c[3]): _ids.append(int(_c[1]))
FIGTAB = 'static int lk_sh_figure(int t) { static const unsigned char d[] = { ' + ', '.join(str(i) for i in _ids) + ' }; unsigned k; if (t >= 173) return 0; for (k = 0; k < sizeof d; k++) if (d[k] == t) return 0; return 1; }   /* everything that is not on the deny list (platforms, switches, gates, projectiles ... by name in docs/ENTITIES.md) gets a contact shadow */'
VER = "LK_SHADOW v7"
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if "LK_SHADOW" in s and VER not in s:   # strip an older version first (v1 .. v3)
    i = s.find("/* ---- LK_SHADOW"); j = s.find("void render_line(int line)")
    if i >= 0: s = s[:i] + s[j:]
    s = "".join(l for l in s.splitlines(True) if "/* LK_SHADOW" not in l)
    m = re.search(r"    pixel\[0x80 \| index\] = \(\(data >> 1\).*?LK_SHADOW.*?\n", s)
    if m: s = s[:m.start()] + "    pixel[0x80 | index] = data;\n" + s[m.end():]
    s = s.replace("      PIXEL_OUT_T *lk_row0 = dst; int lk_w0 = width;\n", "")
    assert "LK_SHADOW" not in s and "lk_shadow" not in s, "vdp_render.c: could not strip the old shadow patch"
if VER not in s:
    b = "  /* Pixel color remapping */\n  remap_line(line);\n}\n"
    assert s.count(b) == 1, "vdp_render.c: render_line end layout changed"
    s = s.replace(b, "  lk_shadow_line(line);   /* LK_SHADOW v7 */\n" + b, 1)
    c = "void render_line(int line)"
    assert s.count(c) == 1, "vdp_render.c: render_line signature changed"
    d = "      do\n      {\n        *dst++ = pixel[*src++];\n      }\n      while (--width);\n"
    assert s.count(d) == 1, "vdp_render.c: remap_line loop layout changed"
    s = s.replace(d, "      PIXEL_OUT_T *lk_row0 = dst; int lk_w0 = width;   /* LK_SHADOW v7 */\n" + d + "      lk_shadow_finish(line);   /* LK_SHADOW v7: after the own renderer drew the line (it is inserted before this line) */\n      lk_shadow_darken(lk_row0, lk_w0);   /* LK_SHADOW v7 */\n", 1)
    helper = r'''/* ---- LK_SHADOW v7: ground shadow (tools/patch_shadow.py) ---- */
#include <math.h>
typedef struct { int x, y, rx, ry; int poly, soft; double str, feather, vx[4], vy[4]; } lk_sh_t;   /* soft: contact shadow of a figure on the ground, HD picture only (not in the 1x mask); str = strength relative to the full shadow, feather = width of the soft edge in game pixels */   /* poly: the shadow is the projected footprint of the object's box (platforms, crates), vx / vy = corners relative to the centre in screen pixels; else an ellipse rx / ry */
static lk_sh_t lk_sh_act[12], lk_sh_pend[12]; static int lk_sh_nact, lk_sh_npend;
static int lk_shadow_mode = -1;
static uint8 lk_sh_fl[224][0x400]; static lk_sh_t lk_sh_snap[12]; static int lk_sh_nsnap;   /* per frame record for the HD picture (tools/patch_hd.py): bit 0 = this pixel was darkened, bit 1 = it shows background and lies within one pixel of a shadow ellipse (eligible); the ellipses of the frame; index = picture x + 0x100 */
static uint8 lk_sh_row[0x400]; static int lk_sh_row_on, lk_sh_xa, lk_sh_xb;   /* pixels of the current line that get darkened (index = screen x + 0x100) */
static void lk_shadow_path(char *buf, size_t n) { const char *h = getenv("HOME"); snprintf(buf, n, "%s/.landstalker_gameplay", h ? h : "."); }
int lk_shadow_get(void) {
  if (lk_shadow_mode < 0) {
    char path[512]; const char *e = getenv("LANDSTALKER_SHADOW"); FILE *f; int a;
    lk_shadow_mode = 0; lk_shadow_path(path, sizeof path); f = fopen(path, "r");
    if (f) { if (fscanf(f, "%d", &a) == 1 && a >= 0 && a <= 1) lk_shadow_mode = a; fclose(f); }
    if (e && *e) { a = atoi(e); if (a >= 0 && a <= 1) lk_shadow_mode = a; }
  }
  return lk_shadow_mode;
}
void lk_shadow_set(int m) {
  char path[512]; FILE *f; lk_shadow_mode = m < 0 ? 0 : m > 1 ? 1 : m; lk_shadow_path(path, sizeof path);
  f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", lk_shadow_mode); fclose(f); }
}
void lk_shadow_reset(void) { lk_sh_npend = 0; }
/* the LIGHT (stage 3, user 2026-10-23): one direction + strength that every shadow is computed from; the default is the original overhead light (no offset, full strength).  LANDSTALKER_LIGHT=lx,ly[,strength] (test aid): lx / ly = screen pixels the shadow moves per unit of height above the floor, strength 0..1 scales the HD shadows.  A later lighting model only has to set these values. */
static double lk_light_x, lk_light_y, lk_light_s = 1.0; static int lk_light_init;
static void lk_light_get(void) { if (!lk_light_init) { const char *e = getenv("LANDSTALKER_LIGHT"); double a, b, c; lk_light_init = 1; if (e && sscanf(e, "%lf,%lf,%lf", &a, &b, &c) == 3) { lk_light_x = a; lk_light_y = b; lk_light_s = c; } else if (e && sscanf(e, "%lf,%lf", &a, &b) == 2) { lk_light_x = a; lk_light_y = b; } } }
static int lk_soft_mode = -1;   /* contact shadows under figures on the ground: HD picture only, ~/.landstalker_softshadow = 1 or LANDSTALKER_SHADOW_SOFT=1 */
int lk_shadow_soft_get(void) {
  if (lk_soft_mode < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_SHADOW_SOFT"); char path[512]; FILE *f; int a; lk_soft_mode = 0; snprintf(path, sizeof path, "%s/.landstalker_softshadow", h ? h : "."); f = fopen(path, "r"); if (f) { if (fscanf(f, "%d", &a) == 1) lk_soft_mode = a ? 1 : 0; fclose(f); } if (e && *e) lk_soft_mode = atoi(e) ? 1 : 0; }
  return lk_soft_mode;
}
void lk_shadow_soft_set(int m) { char path[512]; const char *h = getenv("HOME"); FILE *f; lk_soft_mode = m ? 1 : 0; snprintf(path, sizeof path, "%s/.landstalker_softshadow", h ? h : "."); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", lk_soft_mode); fclose(f); } }
static void lk_sh_shift(int *x, int *y, int h) { lk_light_get(); if (h > 0) { *x += (int)floor(h * lk_light_x + 0.5); *y += (int)floor(h * lk_light_y + 0.5); } }
void lk_shadow_add(int x, int y, int rx, int ry, int h) { if (lk_sh_npend < 12) { lk_sh_t *t = &lk_sh_pend[lk_sh_npend++]; lk_sh_shift(&x, &y, h); t->x = x; t->y = y; t->rx = rx; t->ry = ry; t->poly = 0; t->soft = 0; t->str = lk_light_s; t->feather = 1.0; } }
void lk_shadow_add_soft(int x, int y, int rx, int ry) { if (lk_sh_npend < 12) { lk_sh_t *t = &lk_sh_pend[lk_sh_npend++]; lk_light_get(); t->x = x; t->y = y; t->rx = rx; t->ry = ry; t->poly = 0; t->soft = 1; t->str = 0.85 * lk_light_s; t->feather = 2.0; } }
/* the footprint of an object's box (wx x wy world units) at scale sc: isometric screen X = x - y, Y = (x + y) / 2 of the four corners (+-a, +-b) */
void lk_shadow_addp(int x, int y, int wx, int wy, double sc, int h) {
  if (lk_sh_npend < 12) { lk_sh_t *t = &lk_sh_pend[lk_sh_npend++]; double a = wx * sc / 2.0, b = wy * sc / 2.0; lk_sh_shift(&x, &y, h); t->soft = 0; t->str = lk_light_s; t->feather = 1.0; t->x = x; t->y = y; t->rx = (int)(a + b + 1); t->ry = (int)((a + b) / 2 + 1); t->poly = 1;
    t->vx[0] = a - b; t->vy[0] = (a + b) / 2; t->vx[1] = a + b; t->vy[1] = (a - b) / 2; t->vx[2] = b - a; t->vy[2] = -(a + b) / 2; t->vx[3] = -a - b; t->vy[3] = (b - a) / 2; }
}
/* called by the VDP when the game DMAs its sprite table ($FF0550) to VRAM: the shadow list of the pass that built that table becomes the one that is drawn (the sprites and the shadows then change in the same frame) */
void lk_shadow_promote(void) { memcpy(lk_sh_act, lk_sh_pend, sizeof lk_sh_act); lk_sh_nact = lk_sh_npend; }
/* polygon shadow: pixels whose centre lies inside the convex footprint (continuous coordinates, pixel cell x covers [x, x + 1)) */
static int lk_sh_pspan(const lk_sh_t *t, int line, int *x0, int *x1) {
  double yc = line + 0.5, xl = 1e9, xr = -1e9, cx = t->x + lk_wide_e + 0.5, cy = t->y + 0.5; int k;
  for (k = 0; k < 4; k++) { int n = (k + 1) & 3; double ya = cy + t->vy[k], yb = cy + t->vy[n], xa = cx + t->vx[k], xb = cx + t->vx[n];
    if ((ya <= yc && yc <= yb) || (yb <= yc && yc <= ya)) { double xx = ya == yb ? xa : xa + (xb - xa) * (yc - ya) / (yb - ya); if (xx < xl) xl = xx; if (xx > xr) xr = xx; if (ya == yb) { if (xb < xl) xl = xb; if (xb > xr) xr = xb; } } }
  if (xl > xr) return 0;
  *x0 = (int)ceil(xl - 0.5); *x1 = (int)floor(xr - 0.5); return *x0 <= *x1;
}
/* before remap_line: mark the ellipse pixels that show background (no sprite pixel on top, not the backdrop) */
int lk_sh_mapfade;   /* set while the map fades in at the end of the Start menu (InitVDPAndFadeIn): shadows are shown again */
int lk_sh_hide;   /* set while the Start menu is open (CheckForMenuOpen $007624 runs): the map is not shown then, the shadows of the last map pass must not be drawn over the menu (user's room 430 recording) */
extern uint8 lk_o_shok[]; extern int lk_o_shline;   /* the own renderer's per pixel verdict for the line it just drew (tools/patch_own.py): 1 = a plain ground pixel (no sprite pixel, a plane A / B pixel of LOW priority) */
static int lk_sh_sp[12][2], lk_sh_nsp, lk_sh_pend_fin;
/* can the shadow lie on this pixel? The chip's line buffers are NOT filled any more (the own renderer draws the picture, LK_NOCHIP) -> its own verdict; without it (the chip drew the line) the old test: no sprite pixel, background not transparent.  A high priority tile (the roof of a house in front of Nigel) never takes a shadow. */
static int lk_sh_elig(int line, int x) { if (lk_o_shline == line) return lk_o_shok[x + bitmap.viewport.x]; return (linebuf[1][0x20 + x] & 0x0F) == 0 && (linebuf[0][0x20 + x] & 0x0F) != 0; }
static void lk_shadow_line(int line) {
  int i, x;
  lk_sh_row_on = 0; lk_sh_nsp = 0; lk_sh_pend_fin = 0;
  if (line == 0) { memcpy(lk_sh_snap, lk_sh_act, sizeof lk_sh_snap); lk_sh_nsnap = (lk_sh_hide && !lk_sh_mapfade) ? 0 : lk_sh_nact; }
  if (line >= 0 && line < 224) memset(lk_sh_fl[line], 0, 0x400);
  if (line == 0) { static int dbg = -1; static long fr; if (dbg < 0) { const char *e = getenv("LANDSTALKER_SHADOW_DEBUG"); dbg = e && atoi(e) >= 3; } if (dbg) { fprintf(stderr, "shf: %ld n=%d", fr, lk_sh_nact); for (i = 0; i < lk_sh_nact; i++) fprintf(stderr, " %d,%d%s", lk_sh_act[i].x, lk_sh_act[i].y, lk_sh_act[i].poly ? "p" : ""); fprintf(stderr, "\n"); } fr++; }   /* LANDSTALKER_SHADOW_DEBUG=3: what is drawn in every frame */
  if (lk_sh_hide && !lk_sh_mapfade) return;
  for (i = 0; i < lk_sh_nact; i++) {
    const lk_sh_t *t = &lk_sh_act[i]; int dy = line - t->y, x0, x1;
    double q;
    if (t->soft) continue;   /* HD only */
    if (t->poly) { if (!lk_sh_pspan(t, line, &x0, &x1)) continue; }
    else {
    if (dy < -t->ry || dy > t->ry) continue;
    q = (double)dy / (double)t->ry; q = 1.0 - q * q; if (q < 0) q = 0;
    x0 = t->x + lk_wide_e - (int)(t->rx * sqrt(q) + 0.5); x1 = t->x + lk_wide_e + (int)(t->rx * sqrt(q) + 0.5); }   /* sprites are drawn at xpos - 0x80 + lk_wide_e (widescreen margin) */
    if (x0 < -bitmap.viewport.x) x0 = -bitmap.viewport.x;
    if (x1 > bitmap.viewport.w + bitmap.viewport.x - 1) x1 = bitmap.viewport.w + bitmap.viewport.x - 1;
    if (!lk_sh_row_on) { memset(lk_sh_row, 0, sizeof lk_sh_row); lk_sh_row_on = 1; lk_sh_xa = x0; lk_sh_xb = x1; }
    if (x0 < lk_sh_xa) lk_sh_xa = x0;
    if (x1 > lk_sh_xb) lk_sh_xb = x1;
    if (lk_sh_nsp < 12) { lk_sh_sp[lk_sh_nsp][0] = x0; lk_sh_sp[lk_sh_nsp][1] = x1; lk_sh_nsp++; }   /* the pixels are tested in lk_shadow_finish, after the own renderer drew the line */
  }
  lk_sh_pend_fin = 1;
}
/* after the own renderer drew the line (before lk_shadow_darken): the shadow pixels */
static void lk_shadow_finish(int line) {
  int i, x, k;
  if (!lk_sh_pend_fin) return;
  lk_sh_pend_fin = 0;
  if (lk_sh_row_on) for (k = 0; k < lk_sh_nsp; k++) for (x = lk_sh_sp[k][0]; x <= lk_sh_sp[k][1]; x++)
    if (lk_sh_elig(line, x)) { lk_sh_row[x + 0x100] = 1; if (line >= 0 && line < 224) lk_sh_fl[line][x + 0x100] |= 1; }
  if (line >= 0 && line < 224) for (i = 0; i < lk_sh_nact; i++) {   /* eligible pixels (background, no sprite on top) in the bounding box of every ellipse + 1 pixel: the HD picture shades them with a smooth edge */
    const lk_sh_t *t = &lk_sh_act[i]; int mg = t->soft ? 3 : 1, xa = t->x + lk_wide_e - t->rx - mg, xb = t->x + lk_wide_e + t->rx + mg;
    if (line < t->y - t->ry - mg || line > t->y + t->ry + mg) continue;
    if (xa < -bitmap.viewport.x) xa = -bitmap.viewport.x;
    if (xb > bitmap.viewport.w + bitmap.viewport.x - 1) xb = bitmap.viewport.w + bitmap.viewport.x - 1;
    for (x = xa; x <= xb; x++) if (lk_sh_elig(line, x)) lk_sh_fl[line][x + 0x100] |= 2;
  }
}
/* after the pixel conversion of remap_line: darken the marked pixels (56 % brightness); row = first pixel of the line = screen x -viewport.x */
static void lk_shadow_darken(PIXEL_OUT_T *row, int width) {
  int x;
  if (!lk_sh_row_on) return;
  lk_sh_row_on = 0;
  for (x = lk_sh_xa; x <= lk_sh_xb; x++) {
    int k = x + bitmap.viewport.x;
    if (k >= 0 && k < width && lk_sh_row[x + 0x100]) { uint32 c = row[k]; row[k] = ((c >> 1) & 0x007F7F7Fu) + ((c >> 4) & 0x000F0F0Fu) + (c & 0xFF000000u); }
  }
}
/* HD picture (tools/patch_hd.py): flags of the last rendered frame at picture pixel (x, y): bit 0 darkened at 1x, bit 1 eligible; 0 when none */
int lk_shadow_hdflags(int x, int y) { return (x >= -0x100 && x < 0x300 && y >= 0 && y < 224 && lk_sh_nsnap) ? lk_sh_fl[y][x + 0x100] : 0; }
/* shadow strength 0..255 at the sub pixel (sx, sy) of an n x n block of pixel (x, y): the shadow ellipse as a continuous shape (centre of the pixel grid + 0.5, radii + 0.5 = the cells of the 1x ellipse), soft edge one game pixel wide */
int lk_shadow_hdalpha(int x, int y, int sx, int sy, int n) {
  int i, best = 0;
  double px = x + (sx + 0.5) / n, py = y + (sy + 0.5) / n;
  for (i = 0; i < lk_sh_nsnap; i++) {
    const lk_sh_t *t = &lk_sh_snap[i];
    if (t->poly) {   /* signed distance to the convex footprint (positive inside; the winding decides the sign), soft edge one game pixel wide */
      double cx = t->x + lk_wide_e + 0.5, cy = t->y + 0.5, dmin = 1e9, ar = 0, a; int k;
      for (k = 0; k < 4; k++) { int n = (k + 1) & 3; ar += t->vx[k] * t->vy[n] - t->vx[n] * t->vy[k]; }
      for (k = 0; k < 4; k++) { int n = (k + 1) & 3; double ex = t->vx[n] - t->vx[k], ey = t->vy[n] - t->vy[k], len = sqrt(ex * ex + ey * ey), d;
        if (len < 1e-9) continue; d = (ex * (py - cy - t->vy[k]) - ey * (px - cx - t->vx[k])) / len; if (ar < 0) d = -d; if (d < dmin) dmin = d; }
      a = dmin / t->feather + 0.5; if (a < 0) a = 0; if (a > 1) a = 1; a *= t->str; if ((int)(a * 255 + 0.5) > best) best = (int)(a * 255 + 0.5);
      continue;
    }
    double cx = t->x + lk_wide_e + 0.5, cy = t->y + 0.5, rx = t->rx + 0.5, ry = t->ry + 0.5, u = (px - cx) / rx, v = (py - cy) / ry, f = sqrt(u * u + v * v), g, d, a;
    if (f > 2.0) continue;
    g = sqrt((u / rx) * (u / rx) + (v / ry) * (v / ry));
    d = g > 1e-9 ? (1.0 - f) * f / g : 1e9;   /* distance to the edge in game pixels, positive inside */
    a = d / t->feather + 0.5; if (a < 0) a = 0; if (a > 1) a = 1; a *= t->str;
    if ((int)(a * 255 + 0.5) > best) best = (int)(a * 255 + 0.5);
  }
  return best;
}

'''
    s = s.replace(c, helper + c, 1)
    open(p, "w").write(s)
    print("vdp_render.c patched: LK_SHADOW v7")

# ---- vdp_ctrl.c: promote the shadows when the sprite table is DMA'd ----
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_ctrl.c")
s = open(p).read()
if "LK_SHADOW" in s and VER not in s:
    s = "".join(l for l in s.splitlines(True) if "LK_SHADOW" not in l)
if VER not in s:
    h = s.find("static void vdp_dma_68k_ram(unsigned int length)\n{")
    assert h >= 0, "vdp_ctrl.c: vdp_dma_68k_ram not found"
    src = "  uint32 source = (reg[23] << 17) | (dma_src << 1);\n"
    k = s.find(src, h)
    assert k > h and k - h < 400, "vdp_ctrl.c: vdp_dma_68k_ram layout changed"
    k += len(src)
    s = s[:k] + "  { extern void lk_shadow_promote(void); if (source == 0xFF0550u) lk_shadow_promote(); }   /* LK_SHADOW v7: sprite table DMA */\n" + s[k:]
    open(p, "w").write(s)
    print("vdp_ctrl.c patched: LK_SHADOW v7")

# ---- func_table.c: wrapper of LoadSprites ----
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if "lk_shadow_install" in s and VER not in s:   # strip the older per-entity version
    i = s.find("/* ---- LANDSTALKER 'Shadow' gameplay option"); j = s.find("static void lk_strip_extend(uint32_t a);\n", i)
    assert i >= 0 and j > i
    s = s[:i] + s[j:]
    s = s.replace("        lk_shadow_install();   /* LANDSTALKER shadow option */\n", "")
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "lk_menu_install" in s, "func_table.c: run patch_options.py first"
    module = r'''/* ---- LANDSTALKER 'Shadow' gameplay option, LK_SHADOW v7 (tools/patch_shadow.py) ---- */
extern int lk_shadow_get(void);
extern void lk_shadow_reset(void);
extern void lk_shadow_add(int x, int y, int rx, int ry, int h);
extern void lk_shadow_add_soft(int x, int y, int rx, int ry);
extern int lk_shadow_soft_get(void);
extern int lk_hd_n;
extern void lk_shadow_addp(int x, int y, int wx, int wy, double sc, int h);
/*FIGTAB*/
static int lk_sh_angular(int t) { return t == 21 || t == 22 || t == 53 || t == 76 || t == 83 || (t >= 86 && t <= 95) || t == 113 || t == 114; }   /* entity types (byte +0B, ENTITIES.md ids) with a box shaped body: platforms, crate, raft, concrete block (ENTITIES.md) */
extern int lk_no_charge;
static int lk_sh_surface(uint32_t ent, int z) {   /* the top of the highest entity below (z) whose box contains the CENTRE of this entity (the game's FindEntitySurfaceBelow $00338C counts any overlap of the boxes, even a touch: Nigel next to a platform got its top as 'ground', user recording room 430), +1 like the game; 0 = none */
    int cx = (int)(int16_t)bus_read16(ent + 0x14), cy = (int)(int16_t)bus_read16(ent + 0x16), best = 0, k;
    for (k = 0; k < 16; k++) {
        uint32_t o = 0xFF5400u + 0x80u * (uint32_t)k; int top;
        if (k && (bus_read8(o) & 0x80)) break;
        if (o == ent || bus_read8(o + 8)) continue;
        if (cx < (int)(int16_t)bus_read16(o + 0x18) || cx > (int)(int16_t)bus_read16(o + 0x1A) || cy < (int)(int16_t)bus_read16(o + 0x1C) || cy > (int)(int16_t)bus_read16(o + 0x1E)) continue;
        top = (int)(int16_t)bus_read16(o + 0x54);
        if (top >= z) continue;
        if (top + 1 > best) best = top + 1;
    }
    return best;
}
static gen_func_t lk_o_ls;
/* LoadSprites ($00401C) runs once per game pass: ResetVdpSprites, BuildVisibleEntityList (the on-screen entities as offsets from $FF5400, draw ordered, $FFFF at the end, list at $FF11DE;
   CheckEntityOnScreen stored the screen position in +0E / +10 of each), LoadSpriteFrames. After it the whole list is complete, so the shadows of one pass are collected here at once. */
static void lk_h_ls(void) {
    int mode, soft, k;
    lk_o_ls();   /* the original ends with RTS to our caller's frame, it returns here */
    lk_shadow_reset();
    mode = lk_shadow_get();
    soft = lk_hd_n > 0 && lk_shadow_soft_get();   /* contact shadows of figures on the ground: HD picture only */
    if (!mode && !soft) return;
    { int room = bus_read16(0xFF1204u); if (room >= 139 && room <= 143) return; }   /* the intro rooms (INTRO_139..143, ROOMS.md): floating platforms and a vine in front of a backdrop, there is no ground the shadow could fall on (user, rec_20261028_2054) */
    for (k = 0; k < 16; k++) {
        uint16_t w = bus_read16(0xFF11DEu + 2u * (uint32_t)k);
        uint32_t ent;
        int dist, flr, rx, ry, ext;
        if (w == 0xFFFF) break;
        ent = 0xFF5400u + w;
        if (bus_read8(ent + 8) & 1) continue;                                    /* hidden entity (LoadSpriteFrames skips it too) */
        if (ent == 0xFF5400u && (bus_read16(ent + 0x2C) & 0x1000)) continue;      /* Nigel climbs a ladder / vine (Action bit 12): he hangs on a wall, there is no ground below him to fall on */
        if (ent != 0xFF5400u && (bus_read8(ent + 0x0C) & 2)) continue;           /* the game draws a shadow of its own for it */
        { M68kContext sv = g_m68k; uint8_t b39 = bus_read8(ent + 0x39); int nc = lk_no_charge;
          g_m68k.a[0] = ent; lk_no_charge = 1; lk_call(0x0032C6u);               /* GetDistanceToGround: d5 = Z - ground, no emulated 68K time */
          lk_no_charge = nc; dist = (int16_t)(g_m68k.d[5] & 0xFFFF);
          flr = bus_read8(ent + 0x39);                                           /* the height-map floor under the entity (the game caches it in +39 before it merges in the entity surfaces) */
          bus_write8(ent + 0x39, b39); g_m68k = sv; }
        { int z = (int)(int16_t)bus_read16(ent + 0x12), g = flr, ang = ent != 0xFF5400u && lk_sh_angular(bus_read8(ent + 0x3B));
          if (ent == 0xFF5400u || ang) { int su = lk_sh_surface(ent, z); if (su > g) g = su; dist = z - g; }   /* Nigel and platforms / blocks: the floor is the height map or a platform really under the centre (a shadow falls on a platform below, not on one next to it) */
          else dist = z - flr;                                                   /* other objects: the height-map floor only (a block passing under another made the shadow jump) */
          if (dist < 0) dist = 0;
          if (ent != 0xFF5400u && dist > (ang ? 160 : 40)) continue; }   /* objects far above the floor get no shadow, except platforms (user, room 430: every platform casts its shadow on the grass / the platform below) */
        { static uint8_t on[16]; int idx = (w >> 7) & 15;                         /* hysteresis: walking over slopes / steps makes the distance jump by a few units, that must not blink the shadow (user report, room 430) */
          int show = dist >= 6 || (on[idx] && dist >= 2) || (dist >= 2 && ent != 0xFF5400u && lk_sh_angular(bus_read8(ent + 0x3B)));   /* platforms and blocks: a low floating one has a visible rim of shadow too (user, room 21) */
          on[idx] = (uint8_t)show;
          { static int d2 = -1; if (d2 < 0) { const char *e = getenv("LANDSTALKER_SHADOW_DEBUG"); d2 = e && atoi(e) >= 2; } if (d2) fprintf(stderr, "shp: ent %06X dist %d show %d type %d raw %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X %02X\n", (unsigned)ent, dist, show, bus_read8(ent + 0x3B), bus_read8(ent), bus_read8(ent+1), bus_read8(ent+2), bus_read8(ent+3), bus_read8(ent+4), bus_read8(ent+5), bus_read8(ent+6), bus_read8(ent+7), bus_read8(ent+8), bus_read8(ent+9), bus_read8(ent+0xA), bus_read8(ent+0xB)); }
          if (!show || !mode) {                                                 /* on the ground (or Shadow Off): a contact shadow under a figure (creatures only: Nigel, enemies, NPCs), HD picture only */
              if (soft && (ent == 0xFF5400u || lk_sh_figure(bus_read8(ent + 0x3B)))) {
                  int ex = (int)(int16_t)(bus_read16(ent + 0x1A) - bus_read16(ent + 0x18)) + (int)(int16_t)(bus_read16(ent + 0x1E) - bus_read16(ent + 0x1C)), cr = ex * 70 / 100; if (cr < 6) cr = 6; if (cr > 13) cr = 13;
                  lk_shadow_add_soft((int)bus_read16(ent + 0x0E) - 0x80, (int)bus_read16(ent + 0x10) + dist - 0x80, cr, cr * 45 / 100 < 3 ? 3 : cr * 45 / 100);
              }
              continue; } }                                                 /* on the ground (or a tiny hop): no shadow, only things really in the air */
        ext = (int)(int16_t)(bus_read16(ent + 0x1A) - bus_read16(ent + 0x18)) + (int)(int16_t)(bus_read16(ent + 0x1E) - bus_read16(ent + 0x1C));   /* projected width of the box */
        if (ent != 0xFF5400u && lk_sh_angular(bus_read8(ent + 0x3B))) {      /* platforms, crates, blocks: the shadow is their own footprint (user: angular platforms must not cast a round shadow) */
            int wx = (int)(int16_t)(bus_read16(ent + 0x1A) - bus_read16(ent + 0x18)), wy = (int)(int16_t)(bus_read16(ent + 0x1E) - bus_read16(ent + 0x1C));
            if (mode) lk_shadow_addp((int)bus_read16(ent + 0x0E) - 0x80, (int)bus_read16(ent + 0x10) + dist - 0x80, wx, wy, 1.0, dist);   /* the full footprint of the box (the platform's legs are see-through, a smaller shadow hid behind them: 'too small' and 'above the platform', user, room 21) */
            continue;
        }
        rx = ext / 2; if (rx < 6) rx = 6; if (rx > 9) rx = 9; ry = rx * 45 / 100; if (ry < 3) ry = 3;   /* small: Nigel and platforms were too big at 14 / 20 (user), slimes fitted */
        lk_shadow_add((int)bus_read16(ent + 0x0E) - 0x80, (int)bus_read16(ent + 0x10) + dist - 0x80, rx, ry, dist);
        { static int dbg = -1; static long n; if (dbg < 0) dbg = getenv("LANDSTALKER_SHADOW_DEBUG") != NULL; if (dbg && ++n < 600 && (n % 7) == 1) fprintf(stderr, "shadow: ent %06X dist %d at %d,%d r %d,%d\n", (unsigned)ent, dist, (int)bus_read16(ent + 0x0E) - 0x80, (int)bus_read16(ent + 0x10) + dist - 0x80, rx, ry); }
    }
}
static gen_func_t lk_o_shmenu;
static gen_func_t lk_o_shfade;
static void lk_h_shmenu(void) { extern int lk_sh_hide; lk_sh_hide = 1; lk_o_shmenu(); lk_sh_hide = 0; }   /* no shadows over the Start menu */
static void lk_h_shfade(void) { extern int lk_sh_mapfade; int keep = lk_sh_mapfade; lk_sh_mapfade = 1; lk_o_shfade(); lk_sh_mapfade = keep; }   /* InitVDPAndFadeIn $008E9C: the map fades in again (end of the Start menu): the shadows fade in with it, not at the end of the fade (user: shadows pop up when the menu is left) */
static void lk_shadow_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_ls = func_table_lookup(0x00401C);
    if (!lk_o_ls) { fprintf(stderr, "shadow: LoadSprites not found, option disabled\n"); return; }
    func_table_register(0x00401C, lk_h_ls);
    lk_o_shmenu = func_table_lookup(0x007624);
    if (lk_o_shmenu) func_table_register(0x007624, lk_h_shmenu);
    lk_o_shfade = func_table_lookup(0x008E9C);
    if (lk_o_shfade) func_table_register(0x008E9C, lk_h_shfade);
}
'''
    module = module.replace("/*FIGTAB*/", FIGTAB)
    s = s.replace(a, module + a, 1)
    h = "        lk_menu_install();   /* LANDSTALKER options tab (registers the menu overrides once, after the generated init) */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_shadow_install();   /* LANDSTALKER shadow option */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched: shadow wrapper v7")
