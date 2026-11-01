/* tools/lkvdp.c: our own VDP data path (docs/SOUND_PLAN.md section 12, the way off the emulator step 3).
 * #included into GPGX core/vdp_ctrl.c (just before vdp_bus_w) by tools/patch_vdpport.py, marker LK_VDPPORT.
 *
 * Step 3.1 (this file, v1): the DATA PORT WRITE = every word the 68K (data port or 68K->VDP DMA) stores into VRAM / CRAM / VSRAM:
 * destination decode (code CD0-CD3), byte swap for odd VRAM addresses, store into our memories lk_vm / lk_cm / lk_vsm (the "mirror"
 * of patch_vdpmirror.py becomes the primary copy), the widescreen hooks (lk_vl_write, lk_nt_count), auto increment by register 15.
 * Step 3.2a (v2): the CONTROL PORT = 2-word command latch (pending, address latch A15/A14, code, address), the register file lkv.reg[]
 * (own copy, written by register writes) and the DMA start decode.  The register SIDE EFFECTS (mode / table bases / IRQ / viewport, our
 * widescreen patches inside) are still GPGX's vdp_reg_w, called from here (step 3.2b), and the DMA engine still GPGX's (step 3.3);
 * DMA end writes registers 19..22 itself (pulled, lkv_pull_dmaregs).  Register 15 / 1 / 23 are read from our register file.
 * GPGX's own state that its remaining code still reads (address, FIFO for fill, chip VRAM / CRAM / VSRAM, sprite table cache, pattern
 * cache, palette) is fed from here (lkv_chip_feed) until step 3.5 proves (poison) nobody needs the chip memories.
 *
 * LANDSTALKER_VDP: unset / gpgx = GPGX's vdp_bus_w (default until step 3.5), own = ours, check = GPGX stores, ours predicts the same
 * write and both are compared after every word (address + code before, the stored bytes + the new address after).
 * Check summary: stderr at exit, and one line appended to LANDSTALKER_VDP_CHECKLOG=<file> (name of the input script + counters). */

static struct { uint16 addr, addr_latch; uint8 code, pending; uint8 reg[32]; } lkv;   /* our command latch + register file */
static struct { int kind; unsigned idx; uint8 b0, b1; uint16 next; } lkv_pred;   /* check mode: the predicted store of the current word */
static unsigned long long lkv_n_words, lkv_n_bad, lkv_n_sync, lkv_n_ctrl, lkv_n_cbad, lkv_n_csync;
static int lkv_nest;   /* check mode: 1 while GPGX's own vdp_68k_ctrl_w runs (called from our hook) */

static void lkv_report(void)
{
  const char *fn = getenv("LANDSTALKER_VDP_CHECKLOG"), *sc = getenv("GENRECOMP_INPUTSCRIPT"); FILE *f;
  fprintf(stderr, "vdpport check: words=%llu mismatches=%llu sync_misses=%llu ctrl=%llu ctrl_mismatches=%llu ctrl_sync_misses=%llu\n", lkv_n_words, lkv_n_bad, lkv_n_sync, lkv_n_ctrl, lkv_n_cbad, lkv_n_csync);
  if (fn && (f = fopen(fn, "a")))
  {
    fprintf(f, "%s words=%llu mismatches=%llu sync_misses=%llu ctrl=%llu ctrl_mismatches=%llu ctrl_sync_misses=%llu\n", sc ? (strrchr(sc, '/') ? strrchr(sc, '/') + 1 : sc) : "-",
            lkv_n_words, lkv_n_bad, lkv_n_sync, lkv_n_ctrl, lkv_n_cbad, lkv_n_csync);
    fclose(f);
  }
}

static void lkv_init(void)
{
  const char *e = getenv("LANDSTALKER_VDP");
  lkv_mode = (e && !strcmp(e, "own")) ? 1 : (e && !strcmp(e, "check")) ? 2 : 0;
  lkv_pull();
  if (lkv_mode) fprintf(stderr, "vdpport: LK_VDPPORT v2 data port write + control port = %s\n", lkv_mode == 1 ? "own" : "check (GPGX stores, ours compared)");
  if (lkv_mode == 2) atexit(lkv_report);
}

/* GPGX changed our state (reset; in gpgx / check mode also its control port, fill, copy): take it over */
static void lkv_pull(void)
{
  if (lkv_mode < 0) { lkv_init(); return; }
  lkv.addr = addr; lkv.code = code; lkv.pending = pending; lkv.addr_latch = addr_latch; memcpy(lkv.reg, reg, sizeof lkv.reg);
}

/* GPGX's DMA engine finished a DMA: it advanced the source registers 21 / 22 and cleared the length 19 / 20 (ours from step 3.3) */
static void lkv_pull_dmaregs(void)
{
  lkv.reg[19] = reg[19]; lkv.reg[20] = reg[20]; lkv.reg[21] = reg[21]; lkv.reg[22] = reg[22];
}

/* the emulator's caches of the same write (chip memories, sprite table cache, pattern cache, palette): only until step 3.5 */
static void lkv_chip_feed(int kind, unsigned a, unsigned data)
{
  int name;
  switch (kind)
  {
    case 1:
    {
      int index = a & 0xFFFE; uint16 *p = (uint16 *)&vram[index];
      if ((index & sat_base_mask) == satb) *(uint16 *)&sat[index & sat_addr_mask] = data;
      if (data != *p) { *p = data; MARK_BG_DIRTY(index); }
      break;
    }
    case 3:
    {
      uint16 *p = (uint16 *)&cram[a & 0x7E];
      data = ((data & 0xE00) >> 3) | ((data & 0x0E0) >> 2) | ((data & 0x00E) >> 1);
      if (data != *p)
      {
        int index = (a >> 1) & 0x3F;
        *p = data;
        if (index & 0x0F) color_update_m5(index, data);
        if (index == border) color_update_m5(0x00, data);
        if ((v_counter < bitmap.viewport.h) && (m68k.cycles <= (mcycles_vdp + 860)) && ((reg[1] & 0x40) || (index == border))) remap_line(v_counter);
      }
      break;
    }
    case 5:
      *(uint16 *)&vsram[a & 0x7E] = data;
      if ((reg[11] & 0x04) && (v_counter < bitmap.viewport.h) && (reg[1] & 0x40) && (m68k.cycles <= (mcycles_vdp + 860))) render_line(v_counter);
      break;
  }
}

/* decode one data word: destination kind (1 VRAM, 3 CRAM, 5 VSRAM, 0 = invalid code, nothing stored), byte index, final word */
static inline int lkv_decode(unsigned data, unsigned *idx, unsigned *word)
{
  switch (lkv.code & 0x0F)
  {
    case 0x01: *idx = lkv.addr & 0xFFFE; *word = (lkv.addr & 1) ? (((data >> 8) | (data << 8)) & 0xFFFF) : (data & 0xFFFF); return 1;
    case 0x03: *idx = lkv.addr & 0x7E; *word = data & 0xFFFF; return 3;
    case 0x05: *idx = lkv.addr & 0x7E; *word = data & 0xFFFF; return 5;
    default:   *idx = 0; *word = 0; return 0;
  }
}

/* own mode: the whole data word write (replaces vdp_bus_w) */
static void lkv_bus_w(unsigned int data)
{
  unsigned i, w; int k = lkv_decode(data, &i, &w);
  fifo[fifo_idx] = data; fifo_idx = (fifo_idx + 1) & 3;   /* GPGX's FIFO: read by its fill (until 3.3) and by our FIFO timing in bus.c (lk_vdp_fifo_idx) */
  switch (k)
  {
    case 1: lk_vl_write(i); lk_nt_count(i); lk_vm[i] = (uint8)(w >> 8); lk_vm[i + 1] = (uint8)w; break;
    case 3: lk_cm[i] = (uint8)(w >> 8); lk_cm[i + 1] = (uint8)w; break;
    case 5: if (i < 0x50) { lk_vsm[i] = (uint8)(w >> 8); lk_vsm[i + 1] = (uint8)w; } break;
  }
  if (k) lkv_chip_feed(k, lkv.addr, w);
  lkv.addr += lkv.reg[15];
  addr = lkv.addr;   /* GPGX's address register follows ours (its fill / copy / status code still read it) */
}

/* check mode, before GPGX's vdp_bus_w: our state must equal GPGX's, then predict the store */
static void lkv_check_pre(unsigned int data)
{
  unsigned i, w;
  lkv_n_words++;
  if (lkv.addr != addr || lkv.code != code || lkv.reg[15] != reg[15])
  {
    if (lkv_n_sync++ < 10) fprintf(stderr, "vdpport check: SYNC MISS word %llu own addr=%04X code=%02X gpgx addr=%04X code=%02X\n", lkv_n_words, lkv.addr, lkv.code, addr, code);
    lkv.addr = addr; lkv.code = code;
  }
  lkv_pred.kind = lkv_decode(data, &i, &w);
  lkv_pred.idx = i; lkv_pred.b0 = (uint8)(w >> 8); lkv_pred.b1 = (uint8)w;
  lkv_pred.next = (uint16)(lkv.addr + lkv.reg[15]);
}

/* check mode, after GPGX's vdp_bus_w: compare the stored bytes and the new address */
static void lkv_check_post(void)
{
  const uint8 *m = 0; int bad = 0;
  switch (lkv_pred.kind) { case 1: m = lk_vm; break; case 3: m = lk_cm; break; case 5: m = (lkv_pred.idx < 0x50) ? lk_vsm : 0; break; }
  if (m && (m[lkv_pred.idx] != lkv_pred.b0 || m[lkv_pred.idx + 1] != lkv_pred.b1)) bad |= 1;
  if (addr != lkv_pred.next) bad |= 2;
  if (bad && lkv_n_bad++ < 10)
    fprintf(stderr, "vdpport check: MISMATCH word %llu kind=%d idx=%04X own=%02X%02X gpgx=%02X%02X next own=%04X gpgx=%04X\n", lkv_n_words, lkv_pred.kind, lkv_pred.idx,
            lkv_pred.b0, lkv_pred.b1, m ? m[lkv_pred.idx] : 0, m ? m[lkv_pred.idx + 1] : 0, lkv_pred.next, addr);
  lkv.addr = addr;
}

/* hook at the top of vdp_bus_w: 1 = handled (own mode) */
static int lkv_bus_hook(unsigned int data)
{
  if (lkv_mode < 0) lkv_init();
  if (lkv_mode == 1) { lkv_bus_w(data); return 1; }
  if (lkv_mode == 2) lkv_check_pre(data);
  return 0;
}

/* ---- step 3.2a: control port ---- */

/* one control word on a latch state: returns 1 = register write (*r, *d), 2 = DMA start (second word with CD5 and DMA enabled), 0 = else */
static int lkv_ctrl_decode(unsigned int data, unsigned *r, unsigned *d)
{
  if (!lkv.pending)
  {
    lkv.addr = lkv.addr_latch | (data & 0x3FFF);
    lkv.code = (lkv.code & 0x3C) | ((data >> 14) & 0x03);
    if ((data & 0xC000) == 0x8000)
    {
      *r = (data >> 8) & 0x1F; *d = data & 0xFF;
      if ((lkv.reg[1] & 4) || *r <= 10) lkv.reg[*r] = *d;   /* registers 11..23 are locked in mode 4 (vdp_reg_w) */
      /* (mode 4 only: GPGX's vdp_reg_w can clear register 1 bit 2 again; the game never leaves mode 5, check mode would see it) */
      return 1;
    }
    lkv.pending = lkv.reg[1] & 4;
    return 0;
  }
  lkv.pending = 0;
  lkv.addr_latch = (data & 3) << 14;
  lkv.addr = lkv.addr_latch | (lkv.addr & 0x3FFF);
  lkv.code = (lkv.code & 0x03) | ((data >> 2) & 0x3C);
  return ((lkv.code & 0x20) && (lkv.reg[1] & 0x10)) ? 2 : 0;
}

/* DMA start, as GPGX's control port does it (fill waits for the next data write; copy and 68K->VDP start at once); the engine is GPGX's until 3.3 */
static void lkv_dma_start(void)
{
  switch (lkv.reg[23] >> 6)
  {
    case 2:
      dma_type = 2; dmafill = 1; status |= 0x02; dma_endCycles = 0xffffffff;
      break;
    case 3:
      dma_type = 3;
      dma_length = (lkv.reg[20] << 8) | lkv.reg[19]; if (!dma_length) dma_length = 0x10000;
      dma_src = (lkv.reg[22] << 8) | lkv.reg[21];
      vdp_dma_update(m68k.cycles);
      break;
    default:
      dma_type = (lkv.code & 0x06) ? 0 : 1;
      dma_length = (lkv.reg[20] << 8) | lkv.reg[19]; if (!dma_length) dma_length = 0x10000;
      dma_src = (lkv.reg[22] << 8) | lkv.reg[21];
      vdp_dma_update(m68k.cycles);   /* (GPGX's Sega CD / SVP one-word delay case does not exist on a plain Mega Drive) */
      break;
  }
}

/* own mode: the whole control port write (replaces vdp_68k_ctrl_w) */
static void lkv_ctrl_w(unsigned int data)
{
  unsigned r = 0, d = 0; int k;
  if (!lkv.pending && dma_length && dma_type < 2) { cached_write = data; return; }   /* second word of a long write that started a 68K DMA: after the DMA (never seen in this game) */
  k = lkv_ctrl_decode(data, &r, &d);
  addr = lkv.addr; code = lkv.code; pending = lkv.pending; addr_latch = lkv.addr_latch;   /* GPGX's copies: its DMA engine, status read and logs still read them */
  if (k == 1) vdp_reg_w(r, d, m68k.cycles);   /* register side effects: GPGX until step 3.2b (it writes reg[] itself) */
  else if (k == 2) lkv_dma_start();
  fifo_byte_access = (lkv.code & 0x06) ? 0 : 1;
}

/* check mode: everything of the latch + register file equal? */
static int lkv_ctrl_same(void)
{
  return lkv.addr == addr && lkv.code == code && lkv.pending == pending && lkv.addr_latch == addr_latch && !memcmp(lkv.reg, reg, 24);
}
static void lkv_ctrl_show(const char *what)
{
  int i;
  fprintf(stderr, "vdpport check: %s ctrl %llu own addr=%04X code=%02X pend=%d latch=%04X gpgx addr=%04X code=%02X pend=%d latch=%04X regs", what, lkv_n_ctrl,
          lkv.addr, lkv.code, lkv.pending, lkv.addr_latch, addr, code, pending, addr_latch);
  for (i = 0; i < 24; i++) if (lkv.reg[i] != reg[i]) fprintf(stderr, " r%d own=%02X gpgx=%02X", i, lkv.reg[i], reg[i]);
  fprintf(stderr, "\n");
}

/* hook at the top of vdp_68k_ctrl_w: 1 = handled */
static int lkv_ctrl_hook(unsigned int data)
{
  unsigned r, d;
  if (lkv_mode < 0) lkv_init();
  if (lkv_mode == 1) { lkv_ctrl_w(data); return 1; }
  if (lkv_mode != 2 || lkv_nest) return 0;
  lkv_n_ctrl++;
  if (!lkv_ctrl_same()) { if (lkv_n_csync++ < 10) lkv_ctrl_show("SYNC MISS before"); lkv_pull(); }
  if (!(!lkv.pending && dma_length && dma_type < 2)) lkv_ctrl_decode(data, &r, &d);
  lkv_nest = 1; vdp_68k_ctrl_w(data); lkv_nest = 0;   /* GPGX's control port on the same word */
  if (!lkv_ctrl_same()) { if (lkv_n_cbad++ < 10) lkv_ctrl_show("MISMATCH after"); lkv_pull(); }
  return 1;
}
