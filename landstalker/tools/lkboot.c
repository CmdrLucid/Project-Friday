/* LK_BOOT: system start of our own (steps 4.2 / 4.3 of the way off the emulator, docs/SOUND_PLAN.md section 13).  #included into GPGX's
 * core/system.c by tools/patch_boot.py.  Mega Drive (NTSC / PAL, cartridge, no TMSS BIOS) only; anything else = GPGX's.
 * LANDSTALKER_BOOT: unset / own = ours (default since step 4.4, user confirmed 3.5 on 2026-11-01), gpgx = GPGX's start (rollback), check = ours, then GPGX's
 * gen_reset + io_reset on top, the touched state compared byte for byte (GPGX's result stays).
 * The chip reset (vdp_reset, step 4.1) and vdp_init are ours in tools/lkvdp.c; sound_reset is already ours (LK_MIX);
 * render_reset / audio_reset (GPGX's picture / output upkeep) and the CPU cores' own resets (m68k_pulse_reset, z80_reset) and the
 * cartridge reset (md_cart_reset: nothing to do for a plain cartridge) are still called as they are.
 * Step 4.3 (LK_BOOT v2): system_init = gen_init (memory maps) + md_cart_init for a plain cartridge (Landstalker), compared the same way. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "eeprom_i2c.h"

static int lkb_mode = -1;
extern void lk_cart_default_time_w(void);   /* md_cart.c (patch_boot.py) */

static void lkb_getmode(void) { if (lkb_mode < 0) { const char *e = getenv("LANDSTALKER_BOOT"); lkb_mode = (e && !strcmp(e, "gpgx")) ? 0 : (e && !strcmp(e, "check")) ? 2 : 1;   /* default ours (step 4.4) */ } }

/* step 4.3: md_cart_init for a plain cartridge = Landstalker (2 MB ROM, battery SRAM above the ROM at $200001-$203FFF odd bytes, no mapper,
 * no SVP, no lock-on / add-on); other ROMs = GPGX's (its database of special cartridges) */
static int lkb_cart_ours(void) { return strstr(rominfo.international, "Landstalker") && cart.romsize <= 0x400000 && !config.lock_on && !config.add_on; }
static void lkb_cart_init(void)
{
  int i; unsigned int size = 0x10000;
  while (cart.romsize > size) size <<= 1;   /* the ROM is mirrored every 2^k bytes, padded with $FF */
  if (cart.romsize < size) memset(cart.rom + cart.romsize, 0xff, size - cart.romsize);
  cart.mask = size - 1; cart.special = 0;
  for (i = 0; i < 0x40; i++)
  {
    m68k.memory_map[i].base = cart.rom + ((i << 16) & cart.mask); m68k.memory_map[i].read8 = NULL; m68k.memory_map[i].read16 = NULL;
    m68k.memory_map[i].write8 = m68k_unused_8_w; m68k.memory_map[i].write16 = m68k_unused_16_w; zbank_memory_map[i].read = NULL; zbank_memory_map[i].write = zbank_unused_w;
  }
  for (i = 0x40; i < 0x80; i++)
  {
    m68k.memory_map[i].base = cart.rom + (i << 16); m68k.memory_map[i].read8 = m68k_read_bus_8; m68k.memory_map[i].read16 = m68k_read_bus_16;
    m68k.memory_map[i].write8 = m68k_unused_8_w; m68k.memory_map[i].write16 = m68k_unused_16_w; zbank_memory_map[i].read = zbank_unused_r; zbank_memory_map[i].write = zbank_unused_w;
  }
  sram_init(); eeprom_i2c_init();   /* backup memory from the header (GPGX's detection) */
  if (sram.on && !sram.type && sram.start >= cart.romsize)
  {
    i = sram.start >> 16;
    m68k.memory_map[i].base = sram.sram; m68k.memory_map[i].read8 = sram_read_byte; m68k.memory_map[i].read16 = sram_read_word;
    m68k.memory_map[i].write8 = sram_write_byte; m68k.memory_map[i].write16 = sram_write_word; zbank_memory_map[i].read = sram_read_byte; zbank_memory_map[i].write = sram_write_byte;
  }
  svp = NULL;
  memset(&cart.hw, 0, sizeof cart.hw);
  if (m68k.memory_map[0x20].base == sram.sram) cart.hw.regs[0] = (0x200000 & cart.mask) >> 16;
  lk_cart_default_time_w();   /* cart.hw.time_w = default_time_w (static in md_cart.c) */
  ggenie_shutdown(); areplay_shutdown();
}

/* gen_init, Mega Drive path: CPU cores, the 68K memory map ($800000-$DFFFFF lockup, VDP $C00000-$DFFFFF, work RAM $E00000-$FFFFFF,
 * io $A10000), the Z80 maps, then the cartridge */
static void lkb_gen_init(void)
{
  int i;
  z80_init(0, z80_irq_callback);
  m68k_init(); m68k.aerr_enabled = config.addr_error;
  for (i = 0x80; i < 0xe0; i++)
  {
    m68k.memory_map[i].base = work_ram; m68k.memory_map[i].read8 = m68k_lockup_r_8; m68k.memory_map[i].read16 = m68k_lockup_r_16;
    m68k.memory_map[i].write8 = m68k_lockup_w_8; m68k.memory_map[i].write16 = m68k_lockup_w_16; zbank_memory_map[i].read = zbank_lockup_r; zbank_memory_map[i].write = zbank_lockup_w;
  }
  for (i = 0xc0; i < 0xe0; i += 8)
  {
    m68k.memory_map[i].read8 = vdp_read_byte; m68k.memory_map[i].read16 = vdp_read_word; m68k.memory_map[i].write8 = vdp_write_byte; m68k.memory_map[i].write16 = vdp_write_word;
    zbank_memory_map[i].read = zbank_read_vdp; zbank_memory_map[i].write = zbank_write_vdp;
  }
  for (i = 0xe0; i < 0x100; i++)
  {
    m68k.memory_map[i].base = work_ram; m68k.memory_map[i].read8 = NULL; m68k.memory_map[i].read16 = NULL; m68k.memory_map[i].write8 = NULL; m68k.memory_map[i].write16 = NULL;
    zbank_memory_map[i].read = zbank_unused_r; zbank_memory_map[i].write = NULL;
  }
  m68k.memory_map[0xa1].read8 = ctrl_io_read_byte; m68k.memory_map[0xa1].read16 = ctrl_io_read_word; m68k.memory_map[0xa1].write8 = ctrl_io_write_byte; m68k.memory_map[0xa1].write16 = ctrl_io_write_word;
  zbank_memory_map[0xa1].read = zbank_read_ctrl_io; zbank_memory_map[0xa1].write = zbank_write_ctrl_io;
  for (i = 0; i < 64; i++) z80_readmap[i] = &zram[(i & 7) << 10];
  z80_writemem = z80_memory_w; z80_readmem = z80_memory_r; z80_writeport = z80_unused_port_w; z80_readport = z80_unused_port_r;
  if (lkb_cart_ours()) lkb_cart_init(); else md_cart_init();
}

static size_t lkb_init_snap(uint8 *o)
{
  size_t n = 0;
#define LKB_S(v) do { if (o) memcpy(o + n, &(v), sizeof(v)); n += sizeof(v); } while (0)
  LKB_S(m68k); LKB_S(Z80); LKB_S(zbank_memory_map); LKB_S(z80_readmap); LKB_S(z80_writemem); LKB_S(z80_readmem); LKB_S(z80_writeport); LKB_S(z80_readport);
  LKB_S(cart.base); LKB_S(cart.romsize); LKB_S(cart.mask); LKB_S(cart.special); LKB_S(cart.hw); LKB_S(sram); LKB_S(svp);
#undef LKB_S
  return n;
}
static unsigned long long lkb_romhash(void) { unsigned long long h = 1469598103934665603ULL; size_t i; for (i = 0; i < MAXROMSIZE; i++) h = (h ^ cart.rom[i]) * 1099511628211ULL; return h; }

/* hook at the top of system_init: 1 = handled */
static int lkb_init_hook(void)
{
  static int nest; uint8 *a, *b; size_t n, i, nd = 0; unsigned long long ha;
  if (nest) return 0;
  lkb_getmode();
  if (!lkb_mode || system_hw != SYSTEM_MD) return 0;
  lkb_gen_init(); io_init(); vdp_init(); render_init(); sound_init();
  if (lkb_mode == 1) return 1;
  fprintf(stderr, "vdpboot check: cartridge path %s\n", lkb_cart_ours() ? "ours (plain cartridge)" : "GPGX's md_cart_init");
  n = lkb_init_snap(NULL); a = malloc(n); b = malloc(n); if (!a || !b) abort();
  lkb_init_snap(a); ha = lkb_romhash();
  nest = 1; gen_init(); nest = 0;
  lkb_init_snap(b);
  for (i = 0; i < n; i++) if (a[i] != b[i]) { if (nd < 12) fprintf(stderr, "vdpboot check: SYSTEM INIT MISMATCH at byte %u (%02X/%02X)\n", (unsigned)i, a[i], b[i]); nd++; }
  if (ha != lkb_romhash()) { fprintf(stderr, "vdpboot check: SYSTEM INIT MISMATCH in the ROM area (padding)\n"); nd++; }
  fprintf(stderr, "vdpboot check: gen_init %u bytes + ROM area compared, %u mismatches\n", (unsigned)n, (unsigned)nd);
  free(a); free(b);
  return 1;
}

/* gen_reset(1), Mega Drive cartridge path */
static void lkb_gen_reset(void)
{
  m68k.cycles = ((lines_per_frame - 192 + 159 - (27 * vdp_pal)) * MCYCLES_PER_LINE) + 1004;   /* the 68K starts at a fixed point of the frame */
  memset(work_ram, 0x00, sizeof work_ram);
  memset(zram, 0x00, sizeof zram);
  m68k.cycles = (m68k.cycles / 7) * 7;
  Z80.cycles = (m68k.cycles / 15) * 15;
  md_cart_reset(1);
  m68k.memory_map[0xa0].read8 = m68k_read_bus_8; m68k.memory_map[0xa0].read16 = m68k_read_bus_16;   /* Z80 area: bus released, Z80 in reset */
  m68k.memory_map[0xa0].write8 = m68k_unused_8_w; m68k.memory_map[0xa0].write16 = m68k_unused_16_w;
  zstate = 0; zbank = 0;
  m68k_pulse_reset();
  z80_reset();
}

/* io_reset, Mega Drive: version register (region, no CD unit) + port registers */
static void lkb_io_reset(void)
{
  static const uint8 v[0x10] = { 0, 0, 0, 0, 0, 0, 0, 0xFF, 0, 0, 0xFF, 0, 0, 0xFB, 0, 0 };
  memcpy(io_reg, v, sizeof v);
  io_reg[0x00] = region_code | 0x20;
  input_reset();   /* the pads (GPGX input.c) */
}

static size_t lkb_snap(uint8 *o)
{
  size_t n = 0;
#define LKB_S(v) do { if (o) memcpy(o + n, &(v), sizeof(v)); n += sizeof(v); } while (0)
  LKB_S(m68k); LKB_S(Z80); LKB_S(work_ram); LKB_S(zram); LKB_S(io_reg); LKB_S(zstate); LKB_S(zbank);
  LKB_S(cart.base); LKB_S(cart.romsize); LKB_S(cart.mask); LKB_S(cart.special); LKB_S(cart.hw);
#undef LKB_S
  return n;
}

/* hook at the top of system_reset: 1 = handled */
static int lkb_reset_hook(void)
{
  static int nest; uint8 *a, *b; size_t n, i, nd = 0;
  if (nest) return 0;
  lkb_getmode();
  if (!lkb_mode || system_hw != SYSTEM_MD || (config.bios & 1)) return 0;
  lkb_gen_reset(); lkb_io_reset(); render_reset(); vdp_reset(); sound_reset(); audio_reset();
  if (lkb_mode == 1) return 1;
  n = lkb_snap(NULL); a = malloc(n); b = malloc(n); if (!a || !b) abort();
  lkb_snap(a);
  nest = 1; gen_reset(1); io_reset(); nest = 0;
  lkb_snap(b);
  for (i = 0; i < n; i++) if (a[i] != b[i]) { if (nd < 12) fprintf(stderr, "vdpboot check: SYSTEM RESET MISMATCH at byte %u (%02X/%02X)\n", (unsigned)i, a[i], b[i]); nd++; }
  fprintf(stderr, "vdpboot check: gen_reset + io_reset %u bytes compared, %u mismatches\n", (unsigned)n, (unsigned)nd);
  free(a); free(b);
  return 1;
}
