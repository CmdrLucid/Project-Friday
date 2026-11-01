/* tools/lkvdp.c: our own VDP data path (docs/SOUND_PLAN.md section 12, the way off the emulator step 3).
 * #included into GPGX core/vdp_ctrl.c (just before vdp_bus_w) by tools/patch_vdpport.py, marker LK_VDPPORT.
 *
 * Step 3.1 (this file, v1): the DATA PORT WRITE = every word the 68K (data port or 68K->VDP DMA) stores into VRAM / CRAM / VSRAM:
 * destination decode (code CD0-CD3), byte swap for odd VRAM addresses, store into our memories lk_vm / lk_cm / lk_vsm (the "mirror"
 * of patch_vdpmirror.py becomes the primary copy), the widescreen hooks (lk_vl_write, lk_nt_count), auto increment by register 15.
 * Step 3.2b (v3): the register side effects (lkv_reg_w, below); check mode compares the GPGX state after GPGX's and our write.
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
static unsigned long long lkv_n_regw, lkv_n_rbad, lkv_n_fallback;   /* step 3.2b */
static void lkv_reg_w(unsigned int r, unsigned int d, unsigned int cycles);
static int lkv_nest;   /* check mode: 1 while GPGX's own vdp_68k_ctrl_w runs (called from our hook) */

static void lkv_report(void)
{
  const char *fn = getenv("LANDSTALKER_VDP_CHECKLOG"), *sc = getenv("GENRECOMP_INPUTSCRIPT"); FILE *f;
  fprintf(stderr, "vdpport check: words=%llu mismatches=%llu sync_misses=%llu ctrl=%llu ctrl_mismatches=%llu ctrl_sync_misses=%llu regw=%llu reg_mismatches=%llu reg_fallbacks=%llu\n",
          lkv_n_words, lkv_n_bad, lkv_n_sync, lkv_n_ctrl, lkv_n_cbad, lkv_n_csync, lkv_n_regw, lkv_n_rbad, lkv_n_fallback);
  if (fn && (f = fopen(fn, "a")))
  {
    fprintf(f, "%s words=%llu mismatches=%llu sync_misses=%llu ctrl=%llu ctrl_mismatches=%llu ctrl_sync_misses=%llu regw=%llu reg_mismatches=%llu reg_fallbacks=%llu\n",
            sc ? (strrchr(sc, '/') ? strrchr(sc, '/') + 1 : sc) : "-", lkv_n_words, lkv_n_bad, lkv_n_sync, lkv_n_ctrl, lkv_n_cbad, lkv_n_csync, lkv_n_regw, lkv_n_rbad, lkv_n_fallback);
    fclose(f);
  }
}

static void lkv_init(void)
{
  const char *e = getenv("LANDSTALKER_VDP");
  lkv_mode = (e && !strcmp(e, "own")) ? 1 : (e && !strcmp(e, "check")) ? 2 : 0;
  lkv_pull();
  if (lkv_mode) fprintf(stderr, "vdpport: LK_VDPPORT v3 data port write + control port + register side effects = %s\n", lkv_mode == 1 ? "own" : "check (GPGX stores, ours compared)");
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
