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
    s = s.replace(d, "      PIXEL_OUT_T *lk_row0 = dst; int lk_w0 = width;   /* LK_SHADOW v7 */\n" + d + "      lk_shadow_darken(lk_row0, lk_w0);   /* LK_SHADOW v7 */\n", 1)
    helper = r'''/* ---- LK_SHADOW v7: ground shadow (tools/patch_shadow.py) ---- */
#include <math.h>
typedef struct { int x, y, rx, ry; } lk_sh_t;
static lk_sh_t lk_sh_act[12], lk_sh_pend[12]; static int lk_sh_nact, lk_sh_npend;
static int lk_shadow_mode = -1;
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
void lk_shadow_add(int x, int y, int rx, int ry) { if (lk_sh_npend < 12) { lk_sh_t *t = &lk_sh_pend[lk_sh_npend++]; t->x = x; t->y = y; t->rx = rx; t->ry = ry; } }
/* called by the VDP when the game DMAs its sprite table ($FF0550) to VRAM: the shadow list of the pass that built that table becomes the one that is drawn (the sprites and the shadows then change in the same frame) */
void lk_shadow_promote(void) { memcpy(lk_sh_act, lk_sh_pend, sizeof lk_sh_act); lk_sh_nact = lk_sh_npend; }
/* before remap_line: mark the ellipse pixels that show background (no sprite pixel on top, not the backdrop) */
int lk_sh_hide;   /* set while the Start menu is open (CheckForMenuOpen $007624 runs): the map is not shown then, the shadows of the last map pass must not be drawn over the menu (user's room 430 recording) */
static void lk_shadow_line(int line) {
  int i, x;
  lk_sh_row_on = 0;
  if (line == 0) { static int dbg = -1; static long fr; if (dbg < 0) { const char *e = getenv("LANDSTALKER_SHADOW_DEBUG"); dbg = e && atoi(e) >= 3; } if (dbg) { fprintf(stderr, "shf: %ld n=%d", fr, lk_sh_nact); for (i = 0; i < lk_sh_nact; i++) fprintf(stderr, " %d,%d", lk_sh_act[i].x, lk_sh_act[i].y); fprintf(stderr, "\n"); } fr++; }   /* LANDSTALKER_SHADOW_DEBUG=3: what is drawn in every frame */
  if (lk_sh_hide) return;
  for (i = 0; i < lk_sh_nact; i++) {
    const lk_sh_t *t = &lk_sh_act[i]; int dy = line - t->y, x0, x1;
    double q;
    if (dy < -t->ry || dy > t->ry) continue;
    q = (double)dy / (double)t->ry; q = 1.0 - q * q; if (q < 0) q = 0;
    x0 = t->x + lk_wide_e - (int)(t->rx * sqrt(q) + 0.5); x1 = t->x + lk_wide_e + (int)(t->rx * sqrt(q) + 0.5);   /* sprites are drawn at xpos - 0x80 + lk_wide_e (widescreen margin) */
    if (x0 < -bitmap.viewport.x) x0 = -bitmap.viewport.x;
    if (x1 > bitmap.viewport.w + bitmap.viewport.x - 1) x1 = bitmap.viewport.w + bitmap.viewport.x - 1;
    if (!lk_sh_row_on) { memset(lk_sh_row, 0, sizeof lk_sh_row); lk_sh_row_on = 1; lk_sh_xa = x0; lk_sh_xb = x1; }
    if (x0 < lk_sh_xa) lk_sh_xa = x0;
    if (x1 > lk_sh_xb) lk_sh_xb = x1;
    for (x = x0; x <= x1; x++)
      if ((linebuf[1][0x20 + x] & 0x0F) == 0 && (linebuf[0][0x20 + x] & 0x0F) != 0) lk_sh_row[x + 0x100] = 1;
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
extern void lk_shadow_add(int x, int y, int rx, int ry);
extern int lk_no_charge;
static gen_func_t lk_o_ls;
/* LoadSprites ($00401C) runs once per game pass: ResetVdpSprites, BuildVisibleEntityList (the on-screen entities as offsets from $FF5400, draw ordered, $FFFF at the end, list at $FF11DE;
   CheckEntityOnScreen stored the screen position in +0E / +10 of each), LoadSpriteFrames. After it the whole list is complete, so the shadows of one pass are collected here at once. */
static void lk_h_ls(void) {
    int mode, k;
    lk_o_ls();   /* the original ends with RTS to our caller's frame, it returns here */
    lk_shadow_reset();
    mode = lk_shadow_get();
    if (!mode) return;
    for (k = 0; k < 16; k++) {
        uint16_t w = bus_read16(0xFF11DEu + 2u * (uint32_t)k);
        uint32_t ent;
        int dist, flr, rx, ry, ext;
        if (w == 0xFFFF) break;
        ent = 0xFF5400u + w;
        if (bus_read8(ent + 8) & 1) continue;                                    /* hidden entity (LoadSpriteFrames skips it too) */
        if (ent != 0xFF5400u && (bus_read8(ent + 0x0C) & 2)) continue;           /* the game draws a shadow of its own for it */
        { M68kContext sv = g_m68k; uint8_t b39 = bus_read8(ent + 0x39); int nc = lk_no_charge;
          g_m68k.a[0] = ent; lk_no_charge = 1; lk_call(0x0032C6u);               /* GetDistanceToGround: d5 = Z - ground, no emulated 68K time */
          lk_no_charge = nc; dist = (int16_t)(g_m68k.d[5] & 0xFFFF);
          flr = bus_read8(ent + 0x39);                                           /* the height-map floor under the entity (the game caches it in +39 before it merges in the entity surfaces) */
          bus_write8(ent + 0x39, b39); g_m68k = sv; }
        if (ent != 0xFF5400u) { dist = (int)(int16_t)bus_read16(ent + 0x12) - flr; if (dist < 0) dist = 0; if (dist > 40) continue; }   /* objects (no shadow when more than 40 px above the floor: the projected ground point of a block high on a cliff falls on a nearer surface far away from it, 'shadows where none can be', user report); objects: shadow on the FLOOR, not on the top of another object that passes below (room 430: moving blocks made the shadows jump onto the other block's top where its sprite hides them = flicker, user report); Nigel keeps the full distance (he stands on blocks) */
        { static uint8_t on[16]; int idx = (w >> 7) & 15;                         /* hysteresis: walking over slopes / steps makes the distance jump by a few units, that must not blink the shadow (user report, room 430) */
          int show = dist >= 6 || (on[idx] && dist >= 2);
          on[idx] = (uint8_t)show;
          { static int d2 = -1; if (d2 < 0) { const char *e = getenv("LANDSTALKER_SHADOW_DEBUG"); d2 = e && atoi(e) >= 2; } if (d2) fprintf(stderr, "shp: ent %06X dist %d show %d\n", (unsigned)ent, dist, show); }
          if (!show) continue; }                                                 /* on the ground (or a tiny hop): no shadow, only things really in the air */
        ext = (int)(int16_t)(bus_read16(ent + 0x1A) - bus_read16(ent + 0x18)) + (int)(int16_t)(bus_read16(ent + 0x1E) - bus_read16(ent + 0x1C));   /* projected width of the box */
        rx = ext / 2; if (rx < 6) rx = 6; if (rx > 9) rx = 9; ry = rx * 45 / 100; if (ry < 3) ry = 3;   /* small: Nigel and platforms were too big at 14 / 20 (user), slimes fitted */
        lk_shadow_add((int)bus_read16(ent + 0x0E) - 0x80, (int)bus_read16(ent + 0x10) + dist - 0x80, rx, ry);
        { static int dbg = -1; static long n; if (dbg < 0) dbg = getenv("LANDSTALKER_SHADOW_DEBUG") != NULL; if (dbg && ++n < 600 && (n % 7) == 1) fprintf(stderr, "shadow: ent %06X dist %d at %d,%d r %d,%d\n", (unsigned)ent, dist, (int)bus_read16(ent + 0x0E) - 0x80, (int)bus_read16(ent + 0x10) + dist - 0x80, rx, ry); }
    }
}
static gen_func_t lk_o_shmenu;
static void lk_h_shmenu(void) { extern int lk_sh_hide; lk_sh_hide = 1; lk_o_shmenu(); lk_sh_hide = 0; }   /* no shadows over the Start menu */
static void lk_shadow_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_ls = func_table_lookup(0x00401C);
    if (!lk_o_ls) { fprintf(stderr, "shadow: LoadSprites not found, option disabled\n"); return; }
    func_table_register(0x00401C, lk_h_ls);
    lk_o_shmenu = func_table_lookup(0x007624);
    if (lk_o_shmenu) func_table_register(0x007624, lk_h_shmenu);
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_menu_install();   /* LANDSTALKER options tab (registers the menu overrides once, after the generated init) */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_shadow_install();   /* LANDSTALKER shadow option */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched: shadow wrapper v7")
