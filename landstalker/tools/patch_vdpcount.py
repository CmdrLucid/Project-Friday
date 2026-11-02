#!/usr/bin/env python3
"""VDP data path, step 3.0 (docs/SOUND_PLAN.md section 12): COUNT which paths of GPGX's vdp_ctrl.c the game really uses, before porting them.
Inert unless LANDSTALKER_VDPCOUNT=<file> is set: then one line per run is APPENDED to <file> at exit (name of the input script + key=value counters).
Counted: control port writes (first / second word, latched while a 68K DMA runs), register writes per register (all / value changed / while the
display is on / while a DMA is busy), data port writes per destination code, reads, mode 4 and Z80 side accesses, DMA starts and chunks per kind
(68K ROM / work RAM / io, fill, copy) with bytes, fills triggered by a data write, IRQ acks, the auto increment values (reg 15) used by data writes.
No behaviour change (only counters).  Summary of several runs: tools/vdpcount_sum.py FILE.  Idempotent.  usage: patch_vdpcount.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_ctrl.c")
s = open(p).read()
VER = "LK_VDPCOUNT v1"
if VER in s:
    print("vdp_ctrl.c already patched:", VER); sys.exit(0)

HEAD = r'''/* ---- LK_VDPCOUNT v1 (tools/patch_vdpcount.py, SOUND_PLAN section 12 step 3.0): path counters, inert without LANDSTALKER_VDPCOUNT ---- */
enum { LKVC_CTRL1, LKVC_CTRL2, LKVC_CTRLCACHE, LKVC_DR5, LKVC_DR4, LKVC_DW4, LKVC_Z80, LKVC_FILLTRIG, LKVC_IRQACK, LKVC_DMAUPD,
       LKVC_START_68K, LKVC_START_FILL, LKVC_START_COPY, LKVC_DW_BUSY, LKVC_N };
static const char *const lkvc_name[LKVC_N] = { "ctrl_word1", "ctrl_word2", "ctrl_cached", "data_read_m5", "data_read_m4", "data_write_m4", "z80_side",
       "fill_trigger", "irq_ack", "dma_update", "dma_start_68k", "dma_start_fill", "dma_start_copy", "data_write_dma_busy" };
static int lkvc_on = -1;
static unsigned long long lkvc[LKVC_N], lkvc_reg[32], lkvc_regchg[32], lkvc_regdisp[32], lkvc_regdma[32], lkvc_dw[16], lkvc_dmac[5], lkvc_dmab[5], lkvc_inc[256];
static void lkvc_dump(void)
{
  const char *fn = getenv("LANDSTALKER_VDPCOUNT"), *sc = getenv("GENRECOMP_INPUTSCRIPT"); FILE *f; int i;
  static const char *const dk[5] = { "fill", "copy", "ram", "rom", "io" };
  if (!fn || !(f = fopen(fn, "a"))) return;
  fprintf(f, "%s", sc ? (strrchr(sc, '/') ? strrchr(sc, '/') + 1 : sc) : "-");
  for (i = 0; i < LKVC_N; i++) fprintf(f, " %s=%llu", lkvc_name[i], lkvc[i]);
  for (i = 0; i < 32; i++) if (lkvc_reg[i]) fprintf(f, " reg%d=%llu/%llu/%llu/%llu", i, lkvc_reg[i], lkvc_regchg[i], lkvc_regdisp[i], lkvc_regdma[i]);
  for (i = 0; i < 16; i++) if (lkvc_dw[i]) fprintf(f, " dw_code%X=%llu", i, lkvc_dw[i]);
  for (i = 0; i < 5; i++) if (lkvc_dmac[i]) fprintf(f, " dma_%s=%llu/%llu", dk[i], lkvc_dmac[i], lkvc_dmab[i]);
  for (i = 0; i < 256; i++) if (lkvc_inc[i]) fprintf(f, " inc%d=%llu", i, lkvc_inc[i]);
  fprintf(f, "\n"); fclose(f);
}
static inline int lkvc_active(void)
{
  if (lkvc_on < 0) { const char *e = getenv("LANDSTALKER_VDPCOUNT"); lkvc_on = (e && *e) ? 1 : 0; if (lkvc_on) atexit(lkvc_dump); }
  return lkvc_on;
}
#define LKVC(k) do { if (lkvc_active()) lkvc[k]++; } while (0)
/* ---- end LK_VDPCOUNT ---- */
'''

def ins_after(anchor, text, count=1):
    global s
    assert s.count(anchor) == count, f"vdp_ctrl.c layout changed: {anchor[:70]!r} ({s.count(anchor)}x)"
    s = s.replace(anchor, anchor + text)

decl = "static void vdp_bus_w(unsigned int data);\n"
assert s.count(decl) == 1
s = s.replace(decl, decl + HEAD)

def ins_after_in(func, anchor, text):
    """insert after the first `anchor` inside the function that starts with `func` (the Z80 control port repeats the comments)"""
    global s
    f0 = s.find(func); assert f0 >= 0 and s.count(func) == 1, f"vdp_ctrl.c layout changed: {func[:60]!r}"
    f1 = s.find("\n}\n", f0); i = s.find(anchor, f0)
    assert 0 <= i < f1, f"vdp_ctrl.c layout changed: {anchor[:60]!r} not in {func[:40]!r}"
    s = s[:i + len(anchor)] + text + s[i + len(anchor):]

CW = "void vdp_68k_ctrl_w(unsigned int data)\n{\n"
# control port: first / second word, the latch while a 68K bus DMA runs
ins_after("void vdp_68k_ctrl_w(unsigned int data)\n{\n",
          "  if (lkvc_active()) lkvc[pending ? LKVC_CTRL2 : LKVC_CTRL1]++;   /* LK_VDPCOUNT */\n")
ins_after_in(CW, "        /* Latch second control word for later */\n", "        LKVC(LKVC_CTRLCACHE);   /* LK_VDPCOUNT */\n")
ins_after_in(CW, "            /* DMA Fill */\n", "            LKVC(LKVC_START_FILL);   /* LK_VDPCOUNT */\n")
ins_after_in(CW, "            /* DMA Copy */\n", "            LKVC(LKVC_START_COPY);   /* LK_VDPCOUNT */\n")
ins_after_in(CW, "            /* DMA from 68k bus */\n", "            LKVC(LKVC_START_68K);   /* LK_VDPCOUNT */\n")
# register writes (vdp_reg_w is shared by all modes; the game is mode 5)
ins_after("static void vdp_reg_w(unsigned int r, unsigned int d, unsigned int cycles)\n{\n",
          "  if (lkvc_active()) { lkvc_reg[r & 31]++; if (reg[r & 31] != d) lkvc_regchg[r & 31]++; if (!(status & 8) && (reg[1] & 0x40)) lkvc_regdisp[r & 31]++; if (dma_length || dmafill) lkvc_regdma[r & 31]++; }   /* LK_VDPCOUNT */\n")
# data port
ins_after("static void vdp_68k_data_w_m5(unsigned int data)\n{\n",
          "  if (lkvc_active()) { lkvc_dw[code & 0x0F]++; lkvc_inc[reg[15] & 0xFF]++; if (dma_length) lkvc[LKVC_DW_BUSY]++; }   /* LK_VDPCOUNT */\n")
ins_after("static void vdp_68k_data_w_m4(unsigned int data)\n{\n", "  LKVC(LKVC_DW4);   /* LK_VDPCOUNT */\n")
ins_after("static unsigned int vdp_68k_data_r_m4(void)\n{\n", "  LKVC(LKVC_DR4);   /* LK_VDPCOUNT */\n")
ins_after("static unsigned int vdp_68k_data_r_m5(void)\n{\n", "  LKVC(LKVC_DR5);   /* LK_VDPCOUNT */\n")
ins_after_in("static void vdp_68k_data_w_m5(unsigned int data)\n{\n", "    /* Trigger DMA */\n    vdp_dma_update(m68k.cycles);\n\n    /* Clear DMA Fill pending flag */\n", "    LKVC(LKVC_FILLTRIG);   /* LK_VDPCOUNT */\n")
# Z80 side (never expected in this game)
for fn in ("void vdp_z80_ctrl_w(unsigned int data)\n{\n", "static void vdp_z80_data_w_m4(unsigned int data)\n{\n", "static void vdp_z80_data_w_m5(unsigned int data)\n{\n",
           "static unsigned int vdp_z80_data_r_m4(void)\n{\n", "static unsigned int vdp_z80_data_r_m5(void)\n{\n", "static void vdp_z80_data_w_ms(unsigned int data)\n{\n",
           "static void vdp_z80_data_w_gg(unsigned int data)\n{\n", "static void vdp_z80_data_w_sg(unsigned int data)\n{\n"):
    ins_after(fn, "  LKVC(LKVC_Z80);   /* LK_VDPCOUNT */\n")
# DMA chunks per kind (the lk_vl_dma kinds of patch_vdplog.py: 0 fill, 1 copy, 2 ram, 3 rom (ext), 4 io)
for k in range(5):
    ins_after("  lk_vl_dma(%d, length);   /* LANDSTALKER_VDPLOG */\n" % k,
              "  if (lkvc_active()) { lkvc_dmac[%d]++; lkvc_dmab[%d] += length; }   /* LK_VDPCOUNT */\n" % (k, k))
ins_after("void vdp_dma_update(unsigned int cycles)\n{\n", "  LKVC(LKVC_DMAUPD);   /* LK_VDPCOUNT */\n")
ins_after("int vdp_68k_irq_ack(int int_level)\n{\n", "  LKVC(LKVC_IRQACK);   /* LK_VDPCOUNT */\n")

open(p, "w").write(s)
print("vdp_ctrl.c patched:", VER)
