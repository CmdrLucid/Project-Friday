#!/usr/bin/env python3
"""VDP nametable write diagnostics: which game function writes which tile columns / rows of the scroll planes (widescreen work: find the scroll/column loader).
LANDSTALKER_VDPLOG=1 prints, once per frame that wrote to plane A / plane B / window, one line:
  vdplog f=<frame> A:<n> cols <c0>-<c1> rows <r0>-<r1> by $<fn>($<parent>)x<count> ... | B:... | hs=<hscroll A,B first entry> vs=<vsram A,B>
Columns/rows are tile units inside the 64x32 plane; `by` lists the innermost game function (and its caller) from the shadow call stack with the number of writes.
Idempotent.  usage: patch_vdplog.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]

# func_table.c: accessor for the shadow call stack
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if "uint32_t func_table_stack(" not in s:
    a = "void func_table_dump_stack(FILE *f) {"
    assert s.count(a) == 1, "func_table.c layout changed"
    s = s.replace(a, "/* LANDSTALKER_VDPLOG: k-th entry from the top of the shadow call stack (0 = innermost), 0 if none */\nuint32_t func_table_stack(int k) { int i = s_call_depth - 1 - k; return (i >= 0 && i < 512) ? s_stack[i] : 0; }\n\n" + a, 1)
    open(p, "w").write(s)
    print("func_table.c patched: func_table_stack")

p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_ctrl.c")
s = open(p).read()
if "LANDSTALKER_VDPLOG" in s:
    print("vdp_ctrl.c already patched: LANDSTALKER_VDPLOG"); sys.exit(0)
a = "static void vdp_bus_w(unsigned int data)\n{\n"
assert s.count(a) == 1, "vdp_ctrl.c: vdp_bus_w layout changed"
helper = r'''/* LANDSTALKER_VDPLOG (tools/patch_vdplog.py) */
#include <stdlib.h>
#include <stdio.h>
extern uint32_t func_table_stack(int k);
extern long platform_frame_number(void);
typedef struct { int n, c0, c1, r0, r1, nby; uint32_t fn[4], par[4]; int cnt[4]; short rmin[64], rmax[64]; } lk_vl_t;
static lk_vl_t lk_vl[3];       /* A, B, window */
static long lk_vl_frame = -1;
static int lk_vl_on = -1, lk_vl_lines;
static void lk_vl_flush(void)
{
  int any = 0, i;
  for (i = 0; i < 3; i++) if (lk_vl[i].n) any = 1;
  if (any && lk_vl_lines < 6000)
  {
    static const char nm[3] = { 'A', 'B', 'W' };
    printf("vdplog f=%ld", lk_vl_frame);
    for (i = 0; i < 3; i++) if (lk_vl[i].n)
    {
      int k; printf(" %c:%d cols %d-%d rows %d-%d by", nm[i], lk_vl[i].n, lk_vl[i].c0, lk_vl[i].c1, lk_vl[i].r0, lk_vl[i].r1);
      for (k = 0; k < lk_vl[i].nby; k++) printf(" $%06X($%06X)x%d", lk_vl[i].fn[k], lk_vl[i].par[k], lk_vl[i].cnt[k]);
      { int shown = 0, rr; printf(" rs"); for (rr = 0; rr < 64 && shown < 6; rr++) if (lk_vl[i].rmax[rr] >= lk_vl[i].rmin[rr] && lk_vl[i].rmax[rr] >= 0) { printf(" %d:%d-%d", rr, lk_vl[i].rmin[rr], lk_vl[i].rmax[rr]); shown++; } }
      printf(" |");
    }
    printf(" hs=%d,%d vs=%d,%d\n", *(uint16 *)&vram[hscb] & 0x3FF, *(uint16 *)&vram[hscb + 2] & 0x3FF, *(uint16 *)&vsram[0] & 0x3FF, *(uint16 *)&vsram[2] & 0x3FF);
    fflush(stdout); lk_vl_lines++;
  }
  memset(lk_vl, 0, sizeof(lk_vl));
  for (i = 0; i < 3; i++) { int rr; for (rr = 0; rr < 64; rr++) { lk_vl[i].rmin[rr] = 99; lk_vl[i].rmax[rr] = -1; } }
}
static int lk_dma_lines;
static void lk_vl_dma(int kind, unsigned int length)
{
  static const char *nm[5] = { "fill", "vram-copy", "68k-ram", "68k-rom", "68k-io" };
  if (lk_vl_on < 0) lk_vl_on = getenv("LANDSTALKER_VDPLOG") != NULL;
  if (!lk_vl_on || lk_dma_lines >= 4000) return;
  lk_dma_lines++;
  printf("vdpdma %s f=%ld code=%02X addr=%04X len=%u by $%06X($%06X)\n", nm[kind], platform_frame_number(), code & 0x0F, addr, length, func_table_stack(0), func_table_stack(1));
  fflush(stdout);
}
static void lk_vl_write(int index)
{
  int pl, base, d, w, c, r, k; uint32_t fn, par;
  if (lk_vl_on < 0) lk_vl_on = getenv("LANDSTALKER_VDPLOG") != NULL;
  if (!lk_vl_on) return;
  { static int reg_exit; if (!reg_exit) { reg_exit = 1; atexit(lk_vl_flush); } }
  if (index >= ntab && index < ntab + 0x2000) { pl = 0; base = ntab; }
  else if (index >= ntbb && index < ntbb + 0x2000) { pl = 1; base = ntbb; }
  else if (index >= ntwb && index < ntwb + 0x1000) { pl = 2; base = ntwb; }
  else return;
  if (platform_frame_number() != lk_vl_frame) { lk_vl_flush(); lk_vl_frame = platform_frame_number(); }
  d = index - base; w = 1 << (playfield_shift - 1);       /* tiles per row (64 for the 64x32 layout) */
  c = (d >> 1) & (w - 1); r = d >> playfield_shift;
  { lk_vl_t *v = &lk_vl[pl];
    if (!v->n) { v->c0 = v->c1 = c; v->r0 = v->r1 = r; } else { if (c < v->c0) v->c0 = c; if (c > v->c1) v->c1 = c; if (r < v->r0) v->r0 = r; if (r > v->r1) v->r1 = r; }
    v->n++;
    if (r >= 0 && r < 64) { if (v->rmin[r] == 0 && v->rmax[r] == 0 && v->n == 1) { } if (c < v->rmin[r] || v->rmax[r] < 0) { if (v->rmax[r] < 0) v->rmin[r] = 99; } if (c < v->rmin[r]) v->rmin[r] = c; if (c > v->rmax[r]) v->rmax[r] = c; }
    fn = func_table_stack(0); par = func_table_stack(1);
    for (k = 0; k < v->nby; k++) if (v->fn[k] == fn && v->par[k] == par) break;
    if (k == v->nby && k < 4) { v->fn[k] = fn; v->par[k] = par; v->cnt[k] = 0; v->nby++; }
    if (k < 4) v->cnt[k]++; }
}

'''
s = s.replace(a, helper + a, 1)
for kind, fn in ((0, "vdp_dma_fill"), (1, "vdp_dma_copy"), (2, "vdp_dma_68k_ram"), (3, "vdp_dma_68k_ext"), (4, "vdp_dma_68k_io")):
    hdr = "static void %s(unsigned int length)\n{\n" % fn
    assert s.count(hdr) == 1, "vdp_ctrl.c: %s layout changed" % fn
    s = s.replace(hdr, hdr + "  lk_vl_dma(%d, length);   /* LANDSTALKER_VDPLOG */\n" % kind, 1)
b = "      /* VRAM address */\n      int index = addr & 0xFFFE;\n"
assert s.count(b) >= 1, "vdp_ctrl.c: VRAM write layout changed"
i0 = s.index(a) if False else s.index("static void vdp_bus_w(unsigned int data)\n{\n")
i1 = s.index(b, i0)
s = s[:i1] + b + "      lk_vl_write(index);   /* LANDSTALKER_VDPLOG */\n" + s[i1 + len(b):]
open(p, "w").write(s)
print("vdp_ctrl.c patched: LANDSTALKER_VDPLOG")


# ---- src/func_table.c: LANDSTALKER_BLOCKLOG (map loader geometry, see docs/DEBUGGING.md "map loader") ----------------------
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if "LANDSTALKER_BLOCKLOG" in s:
    print("func_table.c already patched: LANDSTALKER_BLOCKLOG")
else:
    anchor = "static uint32_t s_tail;"
    assert s.count(anchor) == 1, "func_table.c: anchor layout changed"
    helper = r'''/* LANDSTALKER_BLOCKLOG=1: log the map loader. BlockToTiles ($00A748) turns one map block into queue entries: print camera ($FF1124/$FF1125 bytes), the map block
   (a6 = $FF7C02 + 148*y + 2*x -> x,y), the plane cell index d2 (row = d2>>5, col = d2&31), the hscroll / vscroll of plane A and the calling strip loader;
   strip loaders ($00A61C/$00A698/$00A6B0/$00A730) log their entry. tools/blocklog_summary.py turns the log into screen positions. */
extern unsigned short hscb;
extern unsigned char vram[0x10000];
extern unsigned char vsram[0x80];
static void lk_blocklog(uint32_t a)
{
    static int on = -1, n;
    if (on < 0) on = getenv("LANDSTALKER_BLOCKLOG") != NULL;
    if (!on || n > 12000) return;
    int hs = *(uint16_t *)&vram[hscb] & 0x3FF, vs = *(uint16_t *)&vsram[0] & 0x3FF;
    int cx = bus_read8(0xFF1124), cy = bus_read8(0xFF1125);
    if (a == 0x00A748) {
        uint32_t a6 = g_m68k.a[6] & 0xFFFFFF, off = a6 - 0xFF7C02; int d2 = g_m68k.d[2] & 0xFFFF;
        n++;
        printf("blk f=%ld by=$%06X cam=%d,%d a6=%06X map=%d,%d d2=%03X cell=%d,%d hs=%d vs=%d\n", platform_frame_number(), s_call_depth >= 2 ? s_stack[s_call_depth - 2] : 0, cx, cy, a6, (int)((off % 148) / 2), (int)(off / 148), d2, d2 & 31, d2 >> 5, hs, vs);
    } else if (a == 0x00A61C || a == 0x00A698 || a == 0x00A6B0 || a == 0x00A730) {
        n++;
        printf("strip f=%ld fn=$%06X by=$%06X cam=%d,%d phase=%d hs=%d vs=%d\n", platform_frame_number(), a, s_call_depth >= 2 ? s_stack[s_call_depth - 2] : 0, cx, cy, bus_read16(0xFF1184) & 0xFFFF, hs, vs);
    }
}

'''
    s = s.replace(anchor, helper + anchor, 1)
    a2 = "        lk_entry_dump(m68k_addr, ret); /* LANDSTALKER_ENTRYDUMP */\n"
    assert s.count(a2) == 1, "func_table.c: entry hook layout changed"
    s = s.replace(a2, "        lk_blocklog(m68k_addr);   /* LANDSTALKER_BLOCKLOG */\n" + a2, 1)
    open(p, "w").write(s)
    print("func_table.c patched: LANDSTALKER_BLOCKLOG")


# ---- vdp_render.c: LANDSTALKER_PLANEMAP=<N> (text map of the scroll planes: which 16x16 cells have content, where the visible window is) -------------------
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if "LANDSTALKER_PLANEMAP" in s:
    print("vdp_render.c already patched: LANDSTALKER_PLANEMAP")
else:
    rl = "void render_line(int line)\n{\n"
    assert s.count(rl) == 1, "vdp_render.c: render_line layout changed"
    helper = r'''/* LANDSTALKER_PLANEMAP=<N>: every N frames (max 8 dumps) print for plane A and plane B one character per 16x16 cell:
   '#' content inside the original 320x224 window, '+' content in the widescreen margin, 'x' content outside the window,
   ':' EMPTY inside the original window (a hole), ',' empty in the margin, '.' empty outside. Window = where the scroll registers put the screen on the plane. */
extern long platform_frame_number(void);
static int lk_ring_overlap(int a0, int al, int b0, int bl, int m)
{
  return ((b0 - a0 + m) % m) < al || ((a0 - b0 + m) % m) < bl;
}
static void lk_planemap_dump(void)
{
  int tw = 1 << (playfield_shift - 1), th = (playfield_row_mask + 1) >> 3, cw = tw >> 1, ch = th >> 1, pw = tw * 8, ph = th * 8;
  int e = (reg[12] & 1) ? lk_wide_e : 0, pl, r, c;
  for (pl = 0; pl < 2; pl++)
  {
    int base = pl ? ntbb : ntab;
    int hs = *(uint16 *)&vram[hscb + 2 * pl] & 0x3FF, vs = *(uint16 *)&vsram[2 * pl] & 0x3FF;
    int ox = ((-hs) % pw + pw) % pw, oy = vs % ph;                 /* plane position of screen pixel (0,0) */
    int ex = ((ox - e) % pw + pw) % pw;                            /* left edge of the widescreen window */
    printf("pm f=%ld plane %c hs=%d vs=%d e=%d  original window: plane x %d..%d (mod %d), y %d..%d (mod %d)  cells %dx%d\n", platform_frame_number(), pl ? 'B' : 'A', hs, vs, e, ox, (ox + 319) % pw, pw, oy, (oy + 223) % ph, ph, cw, ch);
    for (r = 0; r < ch; r++)
    {
      char row[80];
      for (c = 0; c < cw && c < 79; c++)
      {
        int i, nz = 0, inside, margin;
        for (i = 0; i < 4; i++)
        {
          int tx = 2 * c + (i & 1), ty = 2 * r + (i >> 1);
          if (*(uint16 *)&vram[base + ((ty * tw + tx) << 1)]) nz = 1;
        }
        inside = lk_ring_overlap(16 * c, 16, ox, 320, pw) && lk_ring_overlap(16 * r, 16, oy, 224, ph);
        margin = e && !inside && lk_ring_overlap(16 * c, 16, ex, 320 + 2 * e, pw) && lk_ring_overlap(16 * r, 16, oy, 224, ph);
        row[c] = inside ? (nz ? '#' : ':') : margin ? (nz ? '+' : ',') : (nz ? 'x' : '.');
      }
      row[c] = 0;
      printf("pm %c r%02d %s\n", pl ? 'B' : 'A', r, row);
    }
  }
  fflush(stdout);
}
static void lk_pm_check(int line)
{
  static long every = -2; static int count;
  if (every == -2) { const char *e = getenv("LANDSTALKER_PLANEMAP"); every = e ? atol(e) : 0; }
  if (every <= 0 || line != 0 || count >= 8 || !(reg[1] & 0x40)) return;
  if (platform_frame_number() > 0 && platform_frame_number() % every == 0) { count++; lk_planemap_dump(); }
}

'''
    s = s.replace(rl, helper + rl + "  lk_pm_check(line);   /* LANDSTALKER_PLANEMAP */\n", 1)
    open(p, "w").write(s)
    print("vdp_render.c patched: LANDSTALKER_PLANEMAP")
