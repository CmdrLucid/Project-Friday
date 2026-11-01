/* tools/lkvdp.c: our own VDP data path (docs/SOUND_PLAN.md section 12, the way off the emulator step 3).
 * #included into GPGX core/vdp_ctrl.c (just before vdp_bus_w) by tools/patch_vdpport.py, marker LK_VDPPORT.
 *
 * Step 3.1 (this file, v1): the DATA PORT WRITE = every word the 68K (data port or 68K->VDP DMA) stores into VRAM / CRAM / VSRAM:
 * destination decode (code CD0-CD3), byte swap for odd VRAM addresses, store into our memories lk_vm / lk_cm / lk_vsm (the "mirror"
 * of patch_vdpmirror.py becomes the primary copy), the widescreen hooks (lk_vl_write, lk_nt_count), auto increment by register 15.
 * Step 3.5 (v6): ours by default; the dump reads our memories; LANDSTALKER_OWN_POISON (chip memories = garbage every frame) proves nobody else reads them.
 * Step 3.4 (v5): the data port write wrapper (lkv_data_w: pending, word, fill start); chip reset = step 4.
 * Step 3.3 (v4): the DMA engine (lkv_dma_update: bookkeeping + 68K -> VDP from ROM / RAM + fill; copy / io stay GPGX's, never used).
 * Step 3.2b (v3): the register side effects (lkv_reg_w, below); check mode compares the GPGX state after GPGX's and our write.
 * Step 3.2a (v2): the CONTROL PORT = 2-word command latch (pending, address latch A15/A14, code, address), the register file lkv.reg[]
 * (own copy, written by register writes) and the DMA start decode.  The register SIDE EFFECTS (mode / table bases / IRQ / viewport, our
 * widescreen patches inside) are still GPGX's vdp_reg_w, called from here (step 3.2b), and the DMA engine still GPGX's (step 3.3);
 * DMA end writes registers 19..22 itself (pulled, lkv_pull_dmaregs).  Register 15 / 1 / 23 are read from our register file.
 * GPGX's own state that its remaining code still reads (address, FIFO for fill, chip VRAM / CRAM / VSRAM, sprite table cache, pattern
 * cache, palette) is fed from here (lkv_chip_feed) until step 3.5 proves (poison) nobody needs the chip memories.
 *
 * LANDSTALKER_VDP: unset / own = ours (default since step 3.5), gpgx = GPGX's decode (A/B reference, rollback), check = GPGX runs, ours
 * predicts the same access and both are compared (data word, control word, register write, DMA chunk, data port write).
 * Our memories: lk_vm (VRAM, big endian), lk_cm (CRAM, raw 16 bit words), lk_vsm (VSRAM 0..$4F) + lkv_vsx (VSRAM $50..$7F, never shown).
 * The headless RAM dump (bus_dump_state) is written from them in own mode, in GPGX's layout (lk_vdp_dump_own).
 * Check summary: stderr at exit, and one line appended to LANDSTALKER_VDP_CHECKLOG=<file> (name of the input script + counters). */

static struct { uint16 addr, addr_latch; uint8 code, pending; uint8 reg[32]; } lkv;   /* our command latch + register file */
static struct { int kind; unsigned idx; uint8 b0, b1; uint16 next; } lkv_pred;
static uint8 lkv_vsx[0x30];   /* VSRAM $50..$7F: written like the chip does, never displayed (only for the dump) */   /* check mode: the predicted store of the current word */
static unsigned long long lkv_n_words, lkv_n_bad, lkv_n_sync, lkv_n_ctrl, lkv_n_cbad, lkv_n_csync;
static unsigned long long lkv_n_regw, lkv_n_rbad, lkv_n_fallback;   /* step 3.2b */
static unsigned long long lkv_n_dma, lkv_n_dbad, lkv_n_dfallback;   /* step 3.3 */
static unsigned long long lkv_n_dw, lkv_n_dwbad;   /* step 3.4 */
static void lkv_reg_w(unsigned int r, unsigned int d, unsigned int cycles);
int lk_vdp_ownmem;   /* 1 = own mode: GPGX's sprite parse (vdp_render.c parse_satb_m5) reads lk_vm */
static int lkv_nest;   /* check mode: 1 while GPGX's own vdp_68k_ctrl_w runs (called from our hook) */

static void lkv_report(void)
{
  const char *fn = getenv("LANDSTALKER_VDP_CHECKLOG"), *sc = getenv("GENRECOMP_INPUTSCRIPT"); FILE *f;
  fprintf(stderr, "vdpport check: words=%llu mismatches=%llu sync_misses=%llu ctrl=%llu ctrl_mismatches=%llu ctrl_sync_misses=%llu regw=%llu reg_mismatches=%llu reg_fallbacks=%llu dma=%llu dma_mismatches=%llu dma_fallbacks=%llu dataw=%llu dataw_mismatches=%llu\n",
          lkv_n_words, lkv_n_bad, lkv_n_sync, lkv_n_ctrl, lkv_n_cbad, lkv_n_csync, lkv_n_regw, lkv_n_rbad, lkv_n_fallback, lkv_n_dma, lkv_n_dbad, lkv_n_dfallback, lkv_n_dw, lkv_n_dwbad);
  if (fn && (f = fopen(fn, "a")))
  {
    fprintf(f, "%s words=%llu mismatches=%llu sync_misses=%llu ctrl=%llu ctrl_mismatches=%llu ctrl_sync_misses=%llu regw=%llu reg_mismatches=%llu reg_fallbacks=%llu dma=%llu dma_mismatches=%llu dma_fallbacks=%llu dataw=%llu dataw_mismatches=%llu\n",
            sc ? (strrchr(sc, '/') ? strrchr(sc, '/') + 1 : sc) : "-", lkv_n_words, lkv_n_bad, lkv_n_sync, lkv_n_ctrl, lkv_n_cbad, lkv_n_csync, lkv_n_regw, lkv_n_rbad, lkv_n_fallback, lkv_n_dma, lkv_n_dbad, lkv_n_dfallback, lkv_n_dw, lkv_n_dwbad);
    fclose(f);
  }
}

static void lkv_init(void)
{
  const char *e = getenv("LANDSTALKER_VDP");
  lkv_mode = (e && !strcmp(e, "gpgx")) ? 0 : (e && !strcmp(e, "check")) ? 2 : 1;   /* default ours (step 3.5) */
  lkv_pull(); lk_vdp_ownmem = lkv_mode == 1;
  if (lkv_mode != 1) fprintf(stderr, "vdpport: LK_VDPPORT v6 data port write + control port + register side effects + DMA = %s\n", lkv_mode == 1 ? "own" : "check (GPGX stores, ours compared)");
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
    case 5: if (i < 0x50) { lk_vsm[i] = (uint8)(w >> 8); lk_vsm[i + 1] = (uint8)w; } else { lkv_vsx[i - 0x50] = (uint8)(w >> 8); lkv_vsx[i - 0x4F] = (uint8)w; } break;
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
  if (k == 1) lkv_reg_w(r, d, m68k.cycles);   /* register side effects (step 3.2b; they write GPGX's reg[] copy too) */
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

/* ---- step 3.2b: register side effects ---- */
/* Everything GPGX's vdp_reg_w does for a mode 5 Mega Drive, on GPGX's globals that its remaining code (and our timing / renderer patches)
 * read: table bases, H32 / H40 switch, IRQ line, HV latch, V counter limit, viewport changes, backdrop, window clip.  The calls into GPGX's
 * own renderer (render_line / blank_line / remap_line / color_update / parse_satb, the TALL patch's prerender) only keep its caches fed and
 * are skipped in check mode (lkv_dry).  Rare paths stay GPGX's (counted, lkv_n_fallback): the mode 4 <-> 5 switch (register 1 bit 2,
 * once at boot), register 8 (mode 4 H scroll, its line render can move v_counter) and anything in mode 4. */
extern void *lk_clip_ptr(void); extern int lk_clip_bytes(void);   /* vdp_render.c's window clip state (patch_vdpport.py) */
static int lkv_dry;

/* the rare paths that stay GPGX's: mode 4 (boot, before the game switches to mode 5), the mode 4 <-> 5 switch, register 8 */
static inline int lkv_reg_fallback(unsigned int r, unsigned int d)
{
  return !(reg[1] & 4) || r == 8 || (r == 1 && ((d ^ reg[1]) & 0x04));
}

static void lkv_reg_w(unsigned int r, unsigned int d, unsigned int cycles)
{
  unsigned ch;
  if (lkv_reg_fallback(r, d)) { lkv_n_fallback++; vdp_reg_w(r, d, cycles); return; }
  switch (r)
  {
    case 0:
      ch = d ^ reg[0]; reg[0] = d;
      if (ch & hint_pending) { if (reg[1] & vint_pending) set_irq_line(6); else if (d & 0x10) set_irq_line_delay(4); else set_irq_line(0); }
      if ((ch & 0x04) && !lkv_dry) { int i; color_update_m5(0x00, *(uint16 *)&cram[border << 1]); for (i = 1; i < 0x40; i++) color_update_m5(i, *(uint16 *)&cram[i << 1]); }
      if (ch & 0x02) hvc_latch = (d & 0x02) ? (vdp_hvc_r(cycles) | 0x10000) : 0;   /* HV counter latch (GPGX's HV read; ours is bus.c's lk_v_*) */
      break;
    case 1:
      ch = d ^ reg[1]; reg[1] = d;
      if ((ch & 0x40) && v_counter < bitmap.viewport.h)   /* display enable changed inside the active picture */
      {
        int offset = cycles - mcycles_vdp;
        if (!(d & 0x40) && !lkv_dry) lk_tall_prerender(v_counter);
        if (offset <= 860) { if (!lkv_dry) { if ((d & 0x40) && offset > 360) max_sprite_pixels = 128; render_line(v_counter); } max_sprite_pixels = 256 + ((reg[12] & 1) << 6); }
        else
        {
          offset = (reg[12] & 1) ? ((offset - 860) / 8) + 16 : ((offset - 860) / 10) + 16;
          if (offset < bitmap.viewport.w && !lkv_dry)
          {
            if (d & 0x40) { render_line(v_counter); blank_line(v_counter, 0, offset); }
            else if (!lk_tall_keep(v_counter)) blank_line(v_counter, offset, bitmap.viewport.w - offset);
          }
        }
      }
      if (ch & vint_pending) { if (d & 0x20) set_irq_line_delay(6); else if (reg[0] & hint_pending) set_irq_line(4); else set_irq_line(0); }
      if ((ch & 0x08) && (d & 0x04)) { bitmap.viewport.changed |= 2; vc_max = vc_table[(d >> 2) & 3][vdp_pal]; }   /* 224 <-> 240 lines */
      break;
    case 2:
      reg[2] = d; ntab = (d << 10) & 0xE000;
      if (!lkv_dry && (v_counter < bitmap.viewport.h) && (reg[1] & 0x40) && (cycles <= (mcycles_vdp + 860))) render_line(v_counter);
      break;
    case 3:
      reg[3] = d; ntwb = (reg[12] & 0x01) ? ((d << 10) & 0xF000) : ((d << 10) & 0xF800);
      if (!lkv_dry && (v_counter < bitmap.viewport.h) && (reg[1] & 0x40) && (cycles <= (mcycles_vdp + 860))) render_line(v_counter);
      break;
    case 4:
      reg[4] = d; ntbb = (d << 13) & 0xE000;
      if (!lkv_dry && (v_counter < bitmap.viewport.h) && (reg[1] & 0x40) && (cycles <= (mcycles_vdp + 860))) render_line(v_counter);
      break;
    case 5:
      reg[5] = d; satb = (d << 9) & sat_base_mask;
      if (!lkv_dry && (v_counter < bitmap.viewport.h) && (reg[1] & 0x40) && (cycles <= (mcycles_vdp + 860))) parse_satb(v_counter);
      break;
    case 7:
      reg[7] = d; d &= 0x3F;
      if (d != border)
      {
        border = d;
        if (!lkv_dry) { color_update_m5(0x00, *(uint16 *)&cram[d << 1]); if ((v_counter < bitmap.viewport.h) && (cycles <= (mcycles_vdp + 860))) remap_line(v_counter); }
      }
      break;
    case 11:
      reg[11] = d; hscroll_mask = hscroll_mask_table[d & 0x03];
      render_bg = (d & 0x04) ? (im2_flag ? render_bg_m5_im2_vs : (config.enhanced_vscroll ? render_bg_m5_vs_enhanced : render_bg_m5_vs)) : (im2_flag ? render_bg_m5_im2 : render_bg_m5);
      break;
    case 12:
      ch = d ^ reg[12]; reg[12] = d;
      if (ch & 0x08)   /* shadow / highlight */
      {
        if (!lkv_dry) { int i; color_update_m5(0x00, *(uint16 *)&cram[border << 1]); for (i = 1; i < 0x40; i++) color_update_m5(i, *(uint16 *)&cram[i << 1]); }
        render_obj = (d & 0x08) ? (im2_flag ? render_obj_m5_im2_ste : render_obj_m5_ste) : (im2_flag ? render_obj_m5_im2 : render_obj_m5);
      }
      if (ch & 0x06) bitmap.viewport.changed |= 2;   /* interlace */
      if (ch & 0x01)   /* H32 <-> H40 */
      {
        if (d & 0x01)
        {
          ntwb = (reg[3] << 10) & 0xF000; satb = (reg[5] << 9) & 0xFC00; sat_base_mask = 0xFC00; sat_addr_mask = 0x03FF;
          hctab = cycle2hc40; window_clip(reg[17], 1); max_sprite_pixels = 320; fifo_timing = (int *)fifo_timing_h40;
          vint_cycle = VINT_H40_MCYCLE; hblank_start_cycle = HBLANK_H40_START_MCYCLE; hblank_end_cycle = HBLANK_H40_END_MCYCLE;
        }
        else
        {
          ntwb = (reg[3] << 10) & 0xF800; satb = (reg[5] << 9) & 0xFE00; sat_base_mask = 0xFE00; sat_addr_mask = 0x01FF;
          hctab = cycle2hc32; window_clip(reg[17], 0); max_sprite_pixels = 256; fifo_timing = (int *)fifo_timing_h32;
          vint_cycle = VINT_H32_MCYCLE; hblank_start_cycle = HBLANK_H32_START_MCYCLE; hblank_end_cycle = HBLANK_H32_END_MCYCLE;
        }
        if (v_counter >= bitmap.viewport.h) bitmap.viewport.w = max_sprite_pixels;
        else if (v_counter <= 1) { bitmap.viewport.w = max_sprite_pixels; if (!lkv_dry) { render_line(0); if (v_counter) render_line(1); } }
        else bitmap.viewport.changed |= 2;
      }
      break;
    case 13:
      reg[13] = d; hscb = (d << 10) & 0xFC00;
      break;
    case 16:
      reg[16] = d; playfield_shift = shift_table[d & 3]; playfield_col_mask = col_mask_table[d & 3]; playfield_row_mask = row_mask_table[(d >> 4) & 3];
      break;
    case 17:
      reg[17] = d; window_clip(d, reg[12] & 1);
      break;
    default:
      reg[r] = d;
      break;
  }
}

/* check mode: the GPGX state a register write can change */
typedef struct
{
  uint8 reg[0x20]; uint16 ntab, ntbb, ntwb, satb, hscb, sat_base_mask, sat_addr_mask, vc_max, max_sprite_pixels;
  uint8 hscroll_mask, playfield_shift, playfield_col_mask, border; uint16 playfield_row_mask;
  const uint8 *hctab; int *fifo_timing; uint32 vint_cycle, hvc_latch; int hblank_start, hblank_end, vw, vchanged; unsigned int int_level;
  void (*render_bg)(int); void (*render_obj)(int); void (*parse_satb)(int); void (*pattern)(int); uint8 clip[64];
} lkv_side_t;
static void lkv_side_get(lkv_side_t *t)
{
  memset(t, 0, sizeof *t); memcpy(t->reg, reg, sizeof t->reg);
  t->ntab = ntab; t->ntbb = ntbb; t->ntwb = ntwb; t->satb = satb; t->hscb = hscb; t->sat_base_mask = sat_base_mask; t->sat_addr_mask = sat_addr_mask;
  t->vc_max = vc_max; t->max_sprite_pixels = max_sprite_pixels; t->hscroll_mask = hscroll_mask; t->playfield_shift = playfield_shift;
  t->playfield_col_mask = playfield_col_mask; t->playfield_row_mask = playfield_row_mask; t->border = border; t->hctab = hctab; t->fifo_timing = fifo_timing;
  t->vint_cycle = vint_cycle; t->hvc_latch = hvc_latch; t->hblank_start = hblank_start_cycle; t->hblank_end = hblank_end_cycle;
  t->vw = bitmap.viewport.w; t->vchanged = bitmap.viewport.changed; t->int_level = m68k.int_level;
  t->render_bg = render_bg; t->render_obj = render_obj; t->parse_satb = parse_satb; t->pattern = update_bg_pattern_cache;
  if (lk_clip_bytes() > (int)sizeof t->clip) { fprintf(stderr, "vdpport: clip state too big\n"); abort(); }
  memcpy(t->clip, lk_clip_ptr(), lk_clip_bytes());
}
static void lkv_side_set(const lkv_side_t *t)
{
  memcpy(reg, t->reg, sizeof t->reg);
  ntab = t->ntab; ntbb = t->ntbb; ntwb = t->ntwb; satb = t->satb; hscb = t->hscb; sat_base_mask = t->sat_base_mask; sat_addr_mask = t->sat_addr_mask;
  vc_max = t->vc_max; max_sprite_pixels = t->max_sprite_pixels; hscroll_mask = t->hscroll_mask; playfield_shift = t->playfield_shift;
  playfield_col_mask = t->playfield_col_mask; playfield_row_mask = t->playfield_row_mask; border = t->border; hctab = t->hctab; fifo_timing = t->fifo_timing;
  vint_cycle = t->vint_cycle; hvc_latch = t->hvc_latch; hblank_start_cycle = t->hblank_start; hblank_end_cycle = t->hblank_end;
  bitmap.viewport.w = t->vw; bitmap.viewport.changed = t->vchanged; m68k.int_level = t->int_level;
  render_bg = t->render_bg; render_obj = t->render_obj; parse_satb = t->parse_satb; update_bg_pattern_cache = t->pattern;
  memcpy(lk_clip_ptr(), t->clip, lk_clip_bytes());
}

/* check mode, called instead of GPGX's vdp_reg_w by GPGX's control port: GPGX's write, then ours on the state from before, compared */
static void lkv_reg_check(unsigned int r, unsigned int d, unsigned int cycles)
{
  static lkv_side_t s0, a, b;
  if (lkv_reg_fallback(r, d)) { lkv_n_fallback++; vdp_reg_w(r, d, cycles); return; }   /* GPGX's in both modes */
  lkv_side_get(&s0);
  vdp_reg_w(r, d, cycles);
  lkv_side_get(&a);
  lkv_side_set(&s0);
  lkv_dry = 1; lkv_reg_w(r, d, cycles); lkv_dry = 0;
  lkv_side_get(&b);
  lkv_n_regw++;
  if (memcmp(&a, &b, sizeof a))
  {
    if (lkv_n_rbad++ < 10)
    {
      const uint8 *pa = (const uint8 *)&a, *pb = (const uint8 *)&b; unsigned i, n = 0;
      fprintf(stderr, "vdpport check: REG MISMATCH write %llu r%u=%02X: differing bytes at offsets", lkv_n_regw, r, d);
      for (i = 0; i < sizeof a && n < 12; i++) if (pa[i] != pb[i]) { fprintf(stderr, " %u(%02X/%02X)", i, pa[i], pb[i]); n++; }
      fprintf(stderr, "\n");
    }
  }
  lkv_side_set(&a);   /* GPGX's result stays */
}

/* ---- step 3.3: DMA engine ---- */
/* One DMA chunk (GPGX's vdp_dma_update): the timing is already ours (bus.c lk_v_dma_calc / lk_v_dma_halt, LK_VDPTIME); here the
 * bookkeeping (end cycle, 68K / Z80 halt, busy flag, length, end registers 19..22, cached second control word) and the transfer:
 * 68K -> VDP from ROM / work RAM through our data word write, fill (VRAM / CRAM / VSRAM).  Copy (VRAM -> VRAM) and DMA from the io area
 * never happen in this game (step 3.0): GPGX's functions, counted.  Needs our VDP timing (lk_v_own, not shadow), else GPGX's whole update.
 * GPGX's dma_length / dma_type / dma_src / dmafill / dma_endCycles / status stay the state (bus.c reads them). */
extern int lk_v_own, lk_v_shadow, lk_z_own;
static int lkv_dnest;

static void lkv_fill(unsigned int length)
{
  lk_vl_dma(0, length);   /* LANDSTALKER_VDPLOG */
  switch (lkv.code & 0x0F)
  {
    case 0x01:   /* VRAM: the high byte of the last written FIFO entry, one byte per step (at the odd address of the pair, as the chip does) */
    {
      uint8 data = fifo[(fifo_idx + 3) & 3] >> 8; int name;
      do
      {
        if ((lkv.addr & sat_base_mask) == satb) WRITE_BYTE(sat, (lkv.addr & sat_addr_mask) ^ 1, data);   /* GPGX's caches (until 3.5) */
        lk_vm[lkv.addr ^ 1] = data;   /* big endian: the adjacent byte (was lkv.addr until 2026-11-01: wrong byte, found by the step 3.5 dump) */
        WRITE_BYTE(vram, lkv.addr ^ 1, data); MARK_BG_DIRTY(lkv.addr);
        lkv.addr += lkv.reg[15];
      }
      while (--length);
      break;
    }
    case 0x03:   /* CRAM: the next FIFO entry */
    {
      uint16 raw = fifo[fifo_idx], data = ((raw & 0xE00) >> 3) | ((raw & 0x0E0) >> 2) | ((raw & 0x00E) >> 1);
      do
      {
        uint16 *p = (uint16 *)&cram[lkv.addr & 0x7E];
        if (data != *p) { int index = (lkv.addr >> 1) & 0x3F; *p = data; if (index & 0x0F) color_update_m5(index, data); if (index == border) color_update_m5(0x00, data); }
        lk_cm[lkv.addr & 0x7E] = (uint8)(raw >> 8); lk_cm[(lkv.addr & 0x7E) + 1] = (uint8)raw;
        lkv.addr += lkv.reg[15];
      }
      while (--length);
      break;
    }
    case 0x05:   /* VSRAM: the next FIFO entry */
    {
      uint16 data = fifo[fifo_idx];
      do
      {
        if ((lkv.addr & 0x7E) < 0x50) { lk_vsm[lkv.addr & 0x7E] = (uint8)(data >> 8); lk_vsm[(lkv.addr & 0x7E) + 1] = (uint8)data; }
        else { lkv_vsx[(lkv.addr & 0x7E) - 0x50] = (uint8)(data >> 8); lkv_vsx[(lkv.addr & 0x7E) - 0x4F] = (uint8)data; }
        *(uint16 *)&vsram[lkv.addr & 0x7E] = data;
        lkv.addr += lkv.reg[15];
      }
      while (--length);
      break;
    }
    default:
      lkv.addr += lkv.reg[15] * length;   /* invalid destination: nothing written, the address still moves */
      break;
  }
  addr = lkv.addr;
}

/* 68K -> VDP: source = register 23 (bits 17..23) + dma_src (word address), 128 KB window; rom = external area (memory map), else work RAM */
static void lkv_dma_68k(unsigned int length, int rom)
{
  uint32 source = (lkv.reg[23] << 17) | (dma_src << 1);
  lk_vl_dma(rom ? 3 : 2, length);   /* LANDSTALKER_VDPLOG */
  if (!rom) { extern void lk_shadow_promote(void); if (source == 0xFF0550u) lk_shadow_promote(); }   /* LK_SHADOW v7: sprite table DMA */
  do
  {
    uint16 data;
    if (!rom) data = *(uint16 *)(work_ram + (source & 0xFFFF));
    else if (m68k.memory_map[source >> 16].read16) data = m68k.memory_map[source >> 16].read16(source);
    else data = *(uint16 *)(m68k.memory_map[source >> 16].base + (source & 0xFFFF));
    source = (lkv.reg[23] << 17) | ((source + 2) & 0x1FFFF);
    lkv_bus_w(data);
  }
  while (--length);
  dma_src = (source >> 1) & 0xFFFF;
}

static void lkv_dma_update(unsigned int cycles)
{
  int dma_cycles, dma_bytes; unsigned int start;
  dma_cycles = lk_v_dma_calc(cycles, dma_type, dmafill, dma_length, &dma_bytes, &start);
  dma_endCycles = start + dma_cycles;
  { extern int lk_tt_active; extern void lk_tt_ev(int, int, unsigned, unsigned, unsigned, unsigned, unsigned); if (lk_tt_active) lk_tt_ev('D', 5, dma_type, dma_bytes, dma_length, dma_cycles, ((dma_type < 2 && dma_endCycles > m68k.cycles) ? dma_endCycles - m68k.cycles : 0)); } /* LK_TIMETRACE v1 */
  if (dma_type < 2)
  {
    lk_v_dma_halt(dma_endCycles);                                   /* the 68K waits for its bus */
    if (!(lk_z_own && lk_v_own) && (zstate & 4)) Z80.cycles = dma_endCycles;
  }
  else status |= 0x02;                                              /* busy flag only where the 68K can read it */
  if (dma_bytes <= 0) return;
  dma_length -= dma_bytes;
  switch (lkv.reg[23] >> 4)
  {
    case 0: case 1: case 2: case 3: lkv_dma_68k(dma_bytes, 1); break;
    case 4: case 6: case 7:         lkv_dma_68k(dma_bytes, 0); break;
    case 8: case 9: case 10: case 11: lkv_fill(dma_bytes); break;
    default: lkv_n_dfallback++; dma_func[lkv.reg[23] >> 4](dma_bytes); lkv_pull(); break;   /* io area / copy: never in this game */
  }
  if (!dma_length)
  {
    uint16 end = lkv.reg[21] + (lkv.reg[22] << 8) + lkv.reg[19] + (lkv.reg[20] << 8);   /* source registers advance, length registers count down */
    lkv.reg[21] = end & 0xFF; lkv.reg[22] = end >> 8; lkv.reg[19] = lkv.reg[20] = 0;
    reg[19] = lkv.reg[19]; reg[20] = lkv.reg[20]; reg[21] = lkv.reg[21]; reg[22] = lkv.reg[22];
    if (cached_write >= 0) { vdp_68k_ctrl_w(cached_write); cached_write = -1; }
    zstate &= ~4;
  }
}

/* check mode: what one chunk must leave behind, computed from the state before GPGX runs it */
static struct { int on; unsigned len, src, end, cyc; uint16 addr; uint8 r19, r20, r21, r22, busy; int fillk; unsigned fillv; uint16 fa; unsigned fn; } lkv_dp;
static void lkv_dma_predict(unsigned int cycles)
{
  int b; unsigned st, c = lk_v_dma_calc(cycles, dma_type, dmafill, dma_length, &b, &st), k = lkv.reg[23] >> 4;
  lkv_dp.on = (k < 12 && k != 5);
  lkv_dp.end = st + c; lkv_dp.cyc = (dma_type < 2) ? lkv_dp.end : m68k.cycles; lkv_dp.busy = (dma_type < 2) ? (status & 2) : 2;
  lkv_dp.len = dma_length; lkv_dp.src = dma_src; lkv_dp.addr = lkv.addr; lkv_dp.fillk = 0;
  lkv_dp.r19 = lkv.reg[19]; lkv_dp.r20 = lkv.reg[20]; lkv_dp.r21 = lkv.reg[21]; lkv_dp.r22 = lkv.reg[22];
  if (b <= 0) return;
  lkv_dp.len -= b; lkv_dp.addr = (uint16)(lkv.addr + b * lkv.reg[15]);
  if (k < 8) lkv_dp.src = (dma_src + b) & 0xFFFF;
  else
  {
    lkv_dp.fillk = lkv.code & 0x0F; lkv_dp.fa = lkv.addr; lkv_dp.fn = b;
    lkv_dp.fillv = (lkv_dp.fillk == 1) ? (fifo[(fifo_idx + 3) & 3] >> 8) : fifo[fifo_idx];
  }
  if (!lkv_dp.len)
  {
    uint16 e = lkv.reg[21] + (lkv.reg[22] << 8) + lkv.reg[19] + (lkv.reg[20] << 8);
    lkv_dp.r21 = e & 0xFF; lkv_dp.r22 = e >> 8; lkv_dp.r19 = lkv_dp.r20 = 0;
  }
}
static void lkv_dma_compare(void)
{
  int bad = 0; unsigned i;
  if (!lkv_dp.on) return;
  lkv_n_dma++;
  if (dma_length != lkv_dp.len) bad |= 1;
  if (dma_src != lkv_dp.src) bad |= 2;
  if (addr != lkv_dp.addr) bad |= 4;
  if (dma_endCycles != lkv_dp.end || m68k.cycles != lkv_dp.cyc || (status & 2) != lkv_dp.busy) bad |= 8;
  if (reg[19] != lkv_dp.r19 || reg[20] != lkv_dp.r20 || reg[21] != lkv_dp.r21 || reg[22] != lkv_dp.r22) bad |= 16;
  if (lkv_dp.fillk == 1) { for (i = 0; i < lkv_dp.fn; i++) if (lk_vm[(uint16)((lkv_dp.fa + i * lkv.reg[15]) ^ 1)] != lkv_dp.fillv) { bad |= 32; break; } }
  else if (lkv_dp.fillk == 3 || lkv_dp.fillk == 5)
  {
    const uint8 *m = (lkv_dp.fillk == 3) ? lk_cm : lk_vsm;
    for (i = 0; i < lkv_dp.fn && i < 64; i++) { unsigned a = (lkv_dp.fa + i * lkv.reg[15]) & 0x7E; if ((lkv_dp.fillk == 3 || a < 0x50) && (m[a] != (uint8)(lkv_dp.fillv >> 8) || m[a + 1] != (uint8)lkv_dp.fillv)) { bad |= 32; break; } }
  }
  if (bad && lkv_n_dbad++ < 10)
    fprintf(stderr, "vdpport check: DMA MISMATCH chunk %llu bits=%02X len %u/%u src %04X/%04X addr %04X/%04X end %u/%u cyc %u/%u busy %d/%d regs %02X%02X%02X%02X/%02X%02X%02X%02X\n",
            lkv_n_dma, bad, lkv_dp.len, (unsigned)dma_length, lkv_dp.src, (unsigned)dma_src, lkv_dp.addr, addr, lkv_dp.end, (unsigned)dma_endCycles, lkv_dp.cyc, (unsigned)m68k.cycles,
            lkv_dp.busy, status & 2, lkv_dp.r19, lkv_dp.r20, lkv_dp.r21, lkv_dp.r22, reg[19], reg[20], reg[21], reg[22]);
}

/* hook at the top of vdp_dma_update: 1 = handled */
static int lkv_dma_hook(unsigned int cycles)
{
  if (lkv_mode < 0) lkv_init();
  if (!lk_v_own || lk_v_shadow || lkv_dnest) return 0;   /* GPGX's timing selected: GPGX's whole update */
  if (lkv_mode == 1) { lkv_dma_update(cycles); return 1; }
  if (lkv_mode != 2) return 0;
  lkv_dma_predict(cycles);
  lkv_dnest = 1; vdp_dma_update(cycles); lkv_dnest = 0;
  lkv_dma_compare();
  lkv.addr = addr;
  return 1;
}

/* ---- step 3.4: data port write (the 68K's word to $C00000; GPGX's vdp_68k_data_w_m5) ---- */
/* clears the pending flag, stores the word (the FIFO wait is our timing's: bus.c lk_t_fifo_w), and a pending fill starts now with the
 * length of registers 19 / 20.  Data port READS never happen in this game (step 3.0): GPGX's vdp_68k_data_r_m5 stays.  The chip reset
 * (vdp_reset / vdp_init) belongs to step 4 (system start): we take over its result (lkv_pull at the end of vdp_reset). */
static int lkv_dwnest;

static void lkv_data_w(unsigned int data)
{
  lkv.pending = 0; pending = 0;
  lkv_bus_w(data);
  if (dmafill)
  {
    dma_length = (lkv.reg[20] << 8) | lkv.reg[19]; if (!dma_length) dma_length = 0x10000;
    vdp_dma_update(m68k.cycles);
    dmafill = 0;
  }
}

/* hook at the top of vdp_68k_data_w_m5: 1 = handled */
static int lkv_dataw_hook(unsigned int data)
{
  if (lkv_mode < 0) lkv_init();
  if (!lk_v_own || lk_v_shadow || lkv_dwnest) return 0;   /* GPGX's timing selected: its FIFO step lives in this function */
  if (lkv_mode == 1) { lkv_data_w(data); return 1; }
  if (lkv_mode != 2) return 0;
  lkv_dwnest = 1; vdp_68k_data_w_m5(data); lkv_dwnest = 0;   /* the word itself and the fill chunk are compared by their own hooks */
  lkv_n_dw++;
  if (pending || dmafill || !lkv_ctrl_same())
  {
    if (lkv_n_dwbad++ < 10) lkv_ctrl_show("DATA WRITE MISMATCH after");
    lkv_pull();
  }
  return 1;
}

/* ---- step 3.5: headless RAM dump from our memories (bus.c bus_dump_state), GPGX's layout: reg 32 | CRAM 128 | VSRAM 128 | VRAM 64K, native byte order ---- */
int lk_vdp_dump_own(FILE *f)
{
  static uint8 v[0x10000]; uint16 c[0x40], vs[0x40]; int i;
  if (lkv_mode < 0) lkv_init();
  if (lkv_mode != 1) return 0;
  fwrite(lkv.reg, 1, 0x20, f);
  for (i = 0; i < 0x40; i++) { unsigned w = (lk_cm[2 * i] << 8) | lk_cm[2 * i + 1]; c[i] = ((w & 0xE00) >> 3) | ((w & 0x0E0) >> 2) | ((w & 0x00E) >> 1); }
  for (i = 0; i < 0x40; i++) vs[i] = (2 * i < 0x50) ? ((lk_vsm[2 * i] << 8) | lk_vsm[2 * i + 1]) : ((lkv_vsx[2 * i - 0x50] << 8) | lkv_vsx[2 * i - 0x4F]);
  fwrite(c, 1, 0x80, f); fwrite(vs, 1, 0x80, f);
  for (i = 0; i < 0x10000; i++) v[i ^ 1] = lk_vm[i];   /* (little endian host = GPGX's LSB_FIRST order) */
  fwrite(v, 1, 0x10000, f);
  return 1;
}

/* ---- step 4.1: chip reset (GPGX's vdp_reset), Mega Drive only ---- */
/* LANDSTALKER_BOOT: unset / own = ours (default since step 4.4), gpgx = GPGX's vdp_reset (rollback), check = ours,
 * then GPGX's, all touched state compared (GPGX's result stays).  Ours keeps only the Mega Drive path (no TMSS BIOS, config.bios = 0):
 * other systems / a BIOS = GPGX's.  It sets GPGX's state that its remaining code reads (timing tables, renderer pointers, caches) AND
 * ours (command latch, register file, lk_vm / lk_cm / lk_vsm / lkv_vsx). */
static int lkv_boot = -1, lkv_rnest;

static void lkv_reset(void)
{
  int i;
  memset(sat, 0, sizeof sat); memset(vram, 0, sizeof vram); memset(cram, 0, sizeof cram); memset(vsram, 0, sizeof vsram); memset(reg, 0, sizeof reg);
  addr = addr_latch = 0; code = pending = 0; border = 0; hint_pending = vint_pending = 0; dmafill = 0; dma_src = 0; dma_type = 0; dma_length = 0; dma_endCycles = 0;
  odd_frame = im2_flag = interlaced = 0; fifo_idx = 0; cached_write = -1; fifo_byte_access = 1;
  ntab = ntbb = ntwb = satb = hscb = 0; vscroll = 0;
  hscroll_mask = 0x00; playfield_shift = 6; playfield_col_mask = 0x0F; playfield_row_mask = 0x0FF; sat_base_mask = 0xFE00; sat_addr_mask = 0x01FF;
  bg_list_index = 0; memset(bg_name_dirty, 0, sizeof bg_name_dirty); memset(bg_name_list, 0, sizeof bg_name_list);
  window_clip(0, 0);
  status = vdp_pal;
  bitmap.viewport.w = bitmap.viewport.ow = 256; bitmap.viewport.h = bitmap.viewport.oh = 192;
  hvc_latch = 0x10000; hctab = cycle2hc32; vc_max = vc_table[0][vdp_pal]; v_counter = bitmap.viewport.h; h_counter = 0xff;
  max_sprite_pixels = 256; fifo_timing = (int *)fifo_timing_h32;
  vint_cycle = VINT_H32_MCYCLE; hblank_start_cycle = HBLANK_H32_START_MCYCLE; hblank_end_cycle = HBLANK_H32_END_MCYCLE;
  bitmap.viewport.x = (config.overscan & 2) * 7; bitmap.viewport.y = (config.overscan & 1) * 24 * (vdp_pal + 1);
  update_bg_pattern_cache = update_bg_pattern_cache_m4; render_bg = render_bg_m4; render_obj = render_obj_m4; parse_satb = parse_satb_m4;   /* the chip starts in mode 4 */
  vdp_68k_data_w = vdp_68k_data_w_m4; vdp_68k_data_r = vdp_68k_data_r_m4; vdp_z80_data_w = vdp_z80_data_w_m4; vdp_z80_data_r = vdp_z80_data_r_m4;
  reg[10] = 0xFF;   /* H-Int off at power on */
  for (i = 0; i < 0x20; i++) color_update_m4(i, 0x00);
  color_update_m4(0x40, 0x00);
  /* ours */
  memset(lk_vm, 0, 0x10000); memset(lk_cm, 0, 0x80); memset(lk_vsm, 0, 0x50); memset(lkv_vsx, 0, sizeof lkv_vsx);
  memset(&lkv, 0, sizeof lkv); memcpy(lkv.reg, reg, sizeof lkv.reg);
}

/* check mode: every variable vdp_reset writes, byte for byte */
static size_t lkv_reset_snap(uint8 *o)
{
  size_t n = 0;
#define LKV_S(v) do { memcpy(o + n, &(v), sizeof(v)); n += sizeof(v); } while (0)
  LKV_S(sat); LKV_S(vram); LKV_S(cram); LKV_S(vsram); LKV_S(reg); LKV_S(addr); LKV_S(addr_latch); LKV_S(code); LKV_S(pending); LKV_S(border);
  LKV_S(hint_pending); LKV_S(vint_pending); LKV_S(dmafill); LKV_S(dma_src); LKV_S(dma_type); LKV_S(dma_length); LKV_S(dma_endCycles);
  LKV_S(odd_frame); LKV_S(im2_flag); LKV_S(interlaced); LKV_S(fifo_idx); LKV_S(cached_write); LKV_S(fifo_byte_access);
  LKV_S(ntab); LKV_S(ntbb); LKV_S(ntwb); LKV_S(satb); LKV_S(hscb); LKV_S(vscroll); LKV_S(hscroll_mask); LKV_S(playfield_shift); LKV_S(playfield_col_mask);
  LKV_S(playfield_row_mask); LKV_S(sat_base_mask); LKV_S(sat_addr_mask); LKV_S(bg_list_index); LKV_S(bg_name_dirty); LKV_S(bg_name_list);
  LKV_S(status); LKV_S(bitmap.viewport); LKV_S(hvc_latch); LKV_S(hctab); LKV_S(vc_max); LKV_S(v_counter); LKV_S(h_counter); LKV_S(max_sprite_pixels);
  LKV_S(fifo_timing); LKV_S(vint_cycle); LKV_S(hblank_start_cycle); LKV_S(hblank_end_cycle); LKV_S(update_bg_pattern_cache); LKV_S(render_bg);
  LKV_S(render_obj); LKV_S(parse_satb); LKV_S(vdp_68k_data_w); LKV_S(vdp_68k_data_r); LKV_S(vdp_z80_data_w); LKV_S(vdp_z80_data_r); LKV_S(lkv);
#undef LKV_S
  memcpy(o + n, lk_clip_ptr(), lk_clip_bytes()); n += lk_clip_bytes();
  return n;
}

/* hook at the top of vdp_reset: 1 = handled */
static int lkv_reset_hook(void)
{
  static uint8 a[0x18000], b[0x18000]; size_t na, nb, i, nd = 0;
  if (lkv_rnest) return 0;
  if (lkv_boot < 0) { const char *e = getenv("LANDSTALKER_BOOT"); lkv_boot = (e && !strcmp(e, "gpgx")) ? 0 : (e && !strcmp(e, "check")) ? 2 : 1;   /* default ours (step 4.4) */ }
  if (!lkv_boot || system_hw != SYSTEM_MD || (config.bios & 1)) return 0;
  lkv_reset();
  if (lkv_boot == 1) return 1;
  na = lkv_reset_snap(a);
  lkv_rnest = 1; vdp_reset(); lkv_rnest = 0;   /* GPGX's (it ends with lkv_pull: GPGX's latch / registers into ours) */
  nb = lkv_reset_snap(b);
  for (i = 0; i < na && i < nb; i++) if (a[i] != b[i]) { if (nd < 12) fprintf(stderr, "vdpboot check: RESET MISMATCH at byte %u (%02X/%02X)\n", (unsigned)i, a[i], b[i]); nd++; }
  fprintf(stderr, "vdpboot check: vdp_reset %u bytes compared, %u mismatches\n", (unsigned)na, (unsigned)nd);
  return 1;
}

/* ---- step 4.2: vdp_init (Mega Drive: line count + the 68K interrupt line) ---- */
static int lkv_inest;
static int lkv_init_hook(void)
{
  uint16 lpf; void (*s1)(unsigned int), (*s2)(unsigned int);
  if (lkv_inest) return 0;
  if (lkv_boot < 0) { const char *e = getenv("LANDSTALKER_BOOT"); lkv_boot = (e && !strcmp(e, "gpgx")) ? 0 : (e && !strcmp(e, "check")) ? 2 : 1;   /* default ours (step 4.4) */ }
  if (!lkv_boot || system_hw != SYSTEM_MD) return 0;
  lines_per_frame = vdp_pal ? 313 : 262;
  set_irq_line = m68k_set_irq; set_irq_line_delay = m68k_set_irq_delay;
  if (lkv_boot == 1) return 1;
  lpf = lines_per_frame; s1 = set_irq_line; s2 = set_irq_line_delay;
  lkv_inest = 1; vdp_init(); lkv_inest = 0;
  fprintf(stderr, "vdpboot check: vdp_init %s\n", (lpf == lines_per_frame && s1 == set_irq_line && s2 == set_irq_line_delay) ? "0 mismatches" : "MISMATCH");
  return 1;
}
