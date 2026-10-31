/* lksnd_mix.c -- the sound mixer of our own (2026-10-31, docs/SOUND_PLAN.md section 10, user: 'weiter vom Emulator loesen').
   Replaces Genesis Plus GX's glue in core/sound/sound.c + audio_update() in core/system.c for the Mega Drive:
     * the YM2612 runs in step with the CPU: before every data write / status read it renders the samples up to that M-cycle into the frame buffer;
     * the BUSY flag (32 chip clocks after a data write);
     * at the frame end: PSG to the frame end, FM samples (pre-amplified) as band limited steps into the Blip buffer, frame cut, resampled output.
   The chip cores stay behind their dispatchers (YM2612Update / Write / Read / ResetChip, psg_*): LANDSTALKER_CHIPS still picks ours or GPGX's.
   The band limited step synthesis is blip_buf (Shay Green, LGPL 2.1, a library of its own, not Genesis Plus GX code).
   Not taken over (unused by this game / these settings): Mega CD / cartridge audio streams, the low-pass / 3-band EQ filters (config.filter = 0), mono, YM2413 / Nuked cores.
   Switch: LANDSTALKER_MIX=gpgx = Genesis Plus GX's glue (reference for A/B tests: the audio capture LANDSTALKER_WAV must be sample identical).
   Compiled into sound.c's translation unit by tools/patch_mix.py (needs snd / config / the chip dispatchers). */

#define LKMIX_RATIO (7 * 6 * 24)     /* M-cycles per YM2612 output sample: chip clock = MCLK / 7, one sample per 6 x 24 chip clocks */
#define LKMIX_BUSY  (7 * 6)          /* the BUSY flag counts in units of 6 chip clocks */
#define LKMIX_FMMAX 1080             /* FM samples one frame can hold (a frame has ~889 at 60 Hz) */

static int lkmix_buf[LKMIX_FMMAX * 2];   /* FM samples of the current frame, L / R interleaved */
static int lkmix_n;                      /* samples in lkmix_buf */
static int lkmix_last[2];                /* last FM output of the previous frame (the steps are deltas) */
static int lkmix_start;                  /* M-cycle of the frame's first FM sample (carried over from the previous frame) */
static int lkmix_count;                  /* M-cycle up to which the YM2612 has been rendered */
static int lkmix_busy;                   /* M-cycle at which the BUSY flag clears */
static int lkmix_own_v = -1;

static void lk_snd_log(void);   /* LK_SNDSEP diagnostics (defined further down in sound.c) */
extern void lk_nat_ymreset(void), lk_nat_gevent(int kind, unsigned t, int a, int v), lk_nat_gdbg(unsigned t, unsigned v, int c), lk_nat_gframe(int before, int after);   /* LK_SNDNATIVE v1 */

int lk_mix_own(void) {
  if (lkmix_own_v < 0) { const char *e = getenv("LANDSTALKER_MIX"); lkmix_own_v = !(e && (!strcmp(e, "gpgx") || !strcmp(e, "0"))); if (lkmix_own_v) fprintf(stderr, "mix: the sound mixer is ours (tools/lksnd_mix.c)\n"); }
  return lkmix_own_v;
}

/* render the YM2612 up to M-cycle 'cycles' (whole samples, rounded up) */
static void lkmix_fm_run(int cycles) {
  if (cycles <= lkmix_count) return;
  int n = (cycles - lkmix_count + LKMIX_RATIO - 1) / LKMIX_RATIO, room = LKMIX_FMMAX - lkmix_n;
  if (n > room) {   /* only when the clocks diverge: never write past the buffer */
    static int warned;
    if (warned++ < 8) fprintf(stderr, "lkmix: clamped %d FM samples to %d (cycles=%d count=%d)\n", n, room, cycles, lkmix_count);
    if (room <= 0) { lkmix_count = cycles; return; }
    n = room;
  }
  YM2612Update(lkmix_buf + 2 * lkmix_n, n);
  lkmix_n += n;
  lkmix_count += n * LKMIX_RATIO;
}

static void lkmix_ym_reset(unsigned int cycles) {
  lk_nat_ymreset();
  lkmix_fm_run((int)cycles);
  YM2612ResetChip();
  lkmix_busy = 0;
}

static void lkmix_ym_write(unsigned int cycles, unsigned int a, unsigned int v) {
  if (a & 1) {   /* data port: the chip must be up to date before the register changes */
    lkmix_fm_run((int)cycles);
    if (config.ym2612 < YM2612_ENHANCED) lkmix_busy = (((cycles + LKMIX_BUSY - 1) / LKMIX_BUSY) + 32) * LKMIX_BUSY;
  }
  YM2612Write(a, v);
}

static unsigned int lkmix_ym_read(unsigned int cycles, unsigned int a) {
  if (a != 0 && config.ym2612 <= YM2612_DISCRETE) return 0x00;   /* the discrete chip answers only at (A0, A1) = (0, 0) */
  lkmix_fm_run((int)cycles);
  unsigned int v = YM2612Read();
  if (cycles < (unsigned int)lkmix_busy) v |= 0x80;
  lk_nat_gevent('R', cycles, 0, v); lk_nat_gdbg(cycles, v, lkmix_count);
  return v;
}

static void lkmix_reset(void) {
  fm_reset(0);
  psg_reset();
  psg_config(0, config.psg_preamp, 0xff);
  lkmix_last[0] = lkmix_last[1] = 0;
  lkmix_n = 0;
  lkmix_start = lkmix_count = 0;
}

/* frame end at M-cycle 'cycles': both chips into the Blip buffer, frame cut; returns the output samples available */
static int lkmix_frame(unsigned int cycles) {
  lk_snd_log();
  psg_end_frame(cycles);
  lkmix_fm_run((int)cycles);
  int pl = lkmix_last[0], pr = lkmix_last[1], t = lkmix_start, pre = config.fm_preamp, *p = lkmix_buf;
  do {   /* at least one sample per frame, like the hardware's continuous output */
    int l = p[0] * pre / 100, r = p[1] * pre / 100; p += 2;
    if (config.hq_fm) blip_add_delta(snd.blips[0], t, l - pl, r - pr); else blip_add_delta_fast(snd.blips[0], t, l - pl, r - pr);
    pl = l; pr = r;
    t += LKMIX_RATIO;
  } while ((unsigned int)t < cycles);
  lkmix_n = 0;
  lkmix_last[0] = pl; lkmix_last[1] = pr;
  lk_nat_gframe(t, t - (int)cycles);
  lkmix_count = lkmix_start = t - (int)cycles;
  lkmix_busy = (unsigned int)lkmix_busy > cycles ? lkmix_busy - (int)cycles : 0;
  blip_end_frame(snd.blips[0], cycles);
  return blip_samples_avail(snd.blips[0]);
}

/* audio_update(): the frame's stereo samples into 'buffer' (16 bit, L / R) */
int lkmix_audio(int16 *buffer, unsigned int cycles) {
  int n = lkmix_frame(cycles);
  blip_read_samples(snd.blips[0], buffer, n);
  return n;
}
