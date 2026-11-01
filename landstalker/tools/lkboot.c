/* LK_BOOT: system start of our own (step 4.2 of the way off the emulator, docs/SOUND_PLAN.md section 13).  #included into GPGX's
 * core/system.c by tools/patch_boot.py.  Mega Drive (NTSC / PAL, cartridge, no TMSS BIOS) only; anything else = GPGX's.
 * LANDSTALKER_BOOT: unset / gpgx = GPGX's system_reset (default until the user confirms), own = ours, check = ours, then GPGX's
 * gen_reset + io_reset on top, the touched state compared byte for byte (GPGX's result stays).
 * The chip reset (vdp_reset, step 4.1) and vdp_init are ours in tools/lkvdp.c; sound_reset is already ours (LK_MIX);
 * render_reset / audio_reset (GPGX's picture / output upkeep) and the CPU cores' own resets (m68k_pulse_reset, z80_reset) and the
 * cartridge hardware (md_cart_reset, step 4.3) are still called as they are. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int lkb_mode = -1;

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
  if (lkb_mode < 0) { const char *e = getenv("LANDSTALKER_BOOT"); lkb_mode = (e && !strcmp(e, "own")) ? 1 : (e && !strcmp(e, "check")) ? 2 : 0; }
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
