/* lksnd_psg.c -- own SN76489 (PSG) core of Project-Friday (written 2026-10-29, docs/SOUND_PLAN.md section 9).
   Behaviour of the Mega Drive's integrated PSG: 3 tone channels + 1 noise channel, 4 bit attenuation per channel, 15 bit noise LFSR (integrated chip),
   tone value 0 behaves like 1.  The core runs in MASTER cycles (one PSG clock = 15 * 16 master cycles) and reports every change of the output level as
   an event (time, delta left, delta right) to a sink; the host turns events into samples (GPGX: band limited step synthesis, blip_buf).
   Self contained (no emulator headers).  The constants (volume table, noise taps, update order) are the chip's as measured by the Genesis Plus GX
   project, so that the output is sample identical to its core (checked in the game by comparing audio captures, LANDSTALKER_WAV).
   The functions mirror Genesis Plus GX's psg.h so that the glue (tools/patch_chips.py) can switch between the two. */
#include <stdint.h>
#include <string.h>

typedef void (*lkpsg_sink_t)(unsigned time, int dl, int dr);
typedef struct {
    int clocks, latch, zero_inc, noise_width, noise_mask, shift;
    int regs[8], freq_inc[4], freq_cnt[4], polarity[4];
    int pend[4][2], out[4][2], amp[4][2];
} lkpsg_t;

#define LKPSG_RATIO (15 * 16)      /* master cycles per PSG clock */
#define LKPSG_MAX 2800             /* loudest channel (balance with the FM part, as in the reference core) */

static const uint16_t lkpsg_vol[16] = {
    LKPSG_MAX, LKPSG_MAX * 0.794328234, LKPSG_MAX * 0.630957344, LKPSG_MAX * 0.501187233, LKPSG_MAX * 0.398107170, LKPSG_MAX * 0.316227766,
    LKPSG_MAX * 0.251188643, LKPSG_MAX * 0.199526231, LKPSG_MAX * 0.158489319, LKPSG_MAX * 0.125892541, LKPSG_MAX * 0.1, LKPSG_MAX * 0.079432823,
    LKPSG_MAX * 0.063095734, LKPSG_MAX * 0.050118723, LKPSG_MAX * 0.039810717, 0 };
static const uint8_t lkpsg_width[2] = { 14, 15 };   /* LFSR width: discrete chip, integrated chip */
static const uint8_t lkpsg_mask[2] = { 0x6, 0x9 };  /* feedback taps */
static const uint8_t lkpsg_fb[10] = { 0, 1, 1, 0, 1, 0, 0, 1, 1, 0 };   /* parity of the tapped bits (index = shift register & mask) */

static lkpsg_t lkpsg;
static lkpsg_sink_t lkpsg_sink;
static int (*lkpsg_gain)(int c);   /* per channel gain 0..256 of the volume sliders (channel 6..8 tones, 9 noise); NULL = unity */

static void lkpsg_run(unsigned until);
static void lkpsg_sync(unsigned clocks) {   /* bring the chip to the time stamp of an access */
    if (clocks > (unsigned)lkpsg.clocks) {
        lkpsg_run(clocks);
        lkpsg.clocks += ((clocks - lkpsg.clocks + LKPSG_RATIO - 1) / LKPSG_RATIO) * LKPSG_RATIO;
    }
}

int lkpsg_reg(int i) { return lkpsg.regs[i]; }

void lkpsg_init(int integrated, lkpsg_sink_t sink, int (*gain)(int)) {
    int i;
    memset(&lkpsg, 0, sizeof lkpsg);
    lkpsg_sink = sink; lkpsg_gain = gain;
    for (i = 0; i < 4; i++) lkpsg.amp[i][0] = lkpsg.amp[i][1] = 100;
    lkpsg.zero_inc = (integrated ? 0x1 : 0x400) * LKPSG_RATIO;
    lkpsg.noise_width = lkpsg_width[integrated ? 1 : 0]; lkpsg.noise_mask = lkpsg_mask[integrated ? 1 : 0];
}

void lkpsg_reset(void) {
    int i;
    for (i = 0; i < 4; i++) {
        lkpsg.regs[i * 2] = lkpsg.regs[i * 2 + 1] = 0;
        lkpsg.freq_inc[i] = (i < 3) ? lkpsg.zero_inc : 16 * LKPSG_RATIO;
        lkpsg.freq_cnt[i] = 0; lkpsg.polarity[i] = -1;
        lkpsg.pend[i][0] = lkpsg.pend[i][1] = 0; lkpsg.out[i][0] = lkpsg.out[i][1] = 0;
    }
    lkpsg.latch = 3;                                 /* power on: tone 2 attenuation latched */
    lkpsg.shift = 1 << lkpsg.noise_width;            /* noise output low */
    lkpsg.clocks = 0;
}

/* save state: the same fields in the same order as the reference core, so that quick saves stay compatible */
int lkpsg_save(uint8_t *s) {
    int n = 0;
#define LKP_PUT(x) { memcpy(s + n, &(x), sizeof(x)); n += sizeof(x); }
    LKP_PUT(lkpsg.clocks) LKP_PUT(lkpsg.latch) LKP_PUT(lkpsg.shift) LKP_PUT(lkpsg.regs) LKP_PUT(lkpsg.freq_inc) LKP_PUT(lkpsg.freq_cnt)
    LKP_PUT(lkpsg.polarity) LKP_PUT(lkpsg.out)
#undef LKP_PUT
    return n;
}

int lkpsg_load(uint8_t *s) {
    int delta[2], i, n = 0;
    delta[0] = delta[1] = 0;
    if (lkpsg.shift & 1) { delta[0] = -lkpsg.out[3][0]; delta[1] = -lkpsg.out[3][1]; }   /* output of the old state, taken back ... */
    for (i = 0; i < 3; i++) if (lkpsg.polarity[i] > 0) { delta[0] -= lkpsg.out[i][0]; delta[1] -= lkpsg.out[i][1]; }
#define LKP_GET(x) { memcpy(&(x), s + n, sizeof(x)); n += sizeof(x); }
    LKP_GET(lkpsg.clocks) LKP_GET(lkpsg.latch) LKP_GET(lkpsg.shift) LKP_GET(lkpsg.regs) LKP_GET(lkpsg.freq_inc) LKP_GET(lkpsg.freq_cnt)
    LKP_GET(lkpsg.polarity) LKP_GET(lkpsg.out)
#undef LKP_GET
    if (lkpsg.shift & 1) { delta[0] += lkpsg.out[3][0]; delta[1] += lkpsg.out[3][1]; }   /* ... and the new state's output added */
    for (i = 0; i < 3; i++) if (lkpsg.polarity[i] > 0) { delta[0] += lkpsg.out[i][0]; delta[1] += lkpsg.out[i][1]; }
    if (lkpsg_sink) lkpsg_sink(lkpsg.clocks, delta[0], delta[1]);
    return n;
}

void lkpsg_write(unsigned clocks, unsigned data) {
    int index;
    lkpsg_sync(clocks);
    if (data & 0x80) lkpsg.latch = index = (data >> 4) & 7;   /* 1rrrdddd: latch the register, low data bits */
    else index = lkpsg.latch;                                  /* 0-dddddd: data for the latched register */
    switch (index) {
    case 0: case 2: case 4: {                                  /* tone frequency (10 bit) */
        if (data & 0x80) data = (lkpsg.regs[index] & 0x3F0) | (data & 0x0F);
        else data = (lkpsg.regs[index] & 0x00F) | ((data & 0x3F) << 4);
        lkpsg.freq_inc[index >> 1] = data ? (int)data * LKPSG_RATIO : lkpsg.zero_inc;
        if (index == 4 && (lkpsg.regs[6] & 3) == 3) lkpsg.freq_inc[3] = lkpsg.freq_inc[2];   /* noise follows tone 3 */
        break; }
    case 6: {                                                  /* noise control */
        int rate = data & 3;
        if (rate == 3) { lkpsg.freq_inc[3] = lkpsg.freq_inc[2]; lkpsg.freq_cnt[3] = lkpsg.freq_cnt[2]; }
        else lkpsg.freq_inc[3] = (0x10 << rate) * LKPSG_RATIO;
        if (lkpsg.shift & 1) { lkpsg.pend[3][0] -= lkpsg.out[3][0]; lkpsg.pend[3][1] -= lkpsg.out[3][1]; }   /* high -> low at the next update */
        lkpsg.shift = 1 << lkpsg.noise_width;                  /* the register is reset: output low */
        break; }
    case 7: {                                                  /* noise attenuation */
        int o[2];
        data = lkpsg_vol[data & 15];
        if (lkpsg_gain) data = data * lkpsg_gain(9) >> 8;
        o[0] = (data * lkpsg.amp[3][0]) / 100; o[1] = (data * lkpsg.amp[3][1]) / 100;
        if (lkpsg.shift & 1) { lkpsg.pend[3][0] += o[0] - lkpsg.out[3][0]; lkpsg.pend[3][1] += o[1] - lkpsg.out[3][1]; }
        lkpsg.out[3][0] = o[0]; lkpsg.out[3][1] = o[1];
        break; }
    default: {                                                 /* tone attenuation (index 1, 3, 5) */
        int o[2], i = index >> 1;
        data = lkpsg_vol[data & 15];
        if (lkpsg_gain) data = data * lkpsg_gain(6 + i) >> 8;
        o[0] = (data * lkpsg.amp[i][0]) / 100; o[1] = (data * lkpsg.amp[i][1]) / 100;
        if (lkpsg.polarity[i] > 0) { lkpsg.pend[i][0] += o[0] - lkpsg.out[i][0]; lkpsg.pend[i][1] += o[1] - lkpsg.out[i][1]; }
        lkpsg.out[i][0] = o[0]; lkpsg.out[i][1] = o[1];
        break; }
    }
    lkpsg.regs[index] = data;
}

void lkpsg_config(unsigned clocks, unsigned preamp, unsigned panning) {
    int i;
    lkpsg_sync(clocks);
    for (i = 0; i < 4; i++) {
        int volume = lkpsg.regs[i * 2 + 1];
        lkpsg.amp[i][0] = preamp * ((panning >> (i + 4)) & 1);
        lkpsg.amp[i][1] = preamp * ((panning >> (i + 0)) & 1);
        if (i < 3) {
            if (lkpsg.polarity[i] > 0) { lkpsg.pend[i][0] += ((volume * lkpsg.amp[i][0]) / 100) - lkpsg.out[i][0]; lkpsg.pend[i][1] += ((volume * lkpsg.amp[i][1]) / 100) - lkpsg.out[i][1]; }
        } else if (lkpsg.shift & 1) { lkpsg.pend[3][0] += ((volume * lkpsg.amp[3][0]) / 100) - lkpsg.out[3][0]; lkpsg.pend[3][1] += ((volume * lkpsg.amp[3][1]) / 100) - lkpsg.out[3][1]; }
        lkpsg.out[i][0] = (volume * lkpsg.amp[i][0]) / 100; lkpsg.out[i][1] = (volume * lkpsg.amp[i][1]) / 100;
    }
}

void lkpsg_end_frame(unsigned clocks) {
    int i;
    if (clocks > (unsigned)lkpsg.clocks) {
        lkpsg_run(clocks);
        lkpsg.clocks += ((clocks - lkpsg.clocks + LKPSG_RATIO - 1) / LKPSG_RATIO) * LKPSG_RATIO;
    }
    lkpsg.clocks -= clocks;                                     /* the time stamps of the next frame start at 0 */
    for (i = 0; i < 4; i++) lkpsg.freq_cnt[i] -= clocks;
}

static void lkpsg_run(unsigned clocks) {
    int i, ts, pol;
    for (i = 0; i < 4; i++) {
        if (lkpsg.pend[i][0] | lkpsg.pend[i][1]) {              /* volume changes of this channel, applied at the chip's own clock */
            lkpsg_sink(lkpsg.clocks, lkpsg.pend[i][0], lkpsg.pend[i][1]);
            lkpsg.pend[i][0] = lkpsg.pend[i][1] = 0;
        }
        ts = lkpsg.freq_cnt[i]; pol = lkpsg.polarity[i];
        if (i < 3) {                                            /* tone: the output flips every period */
            while ((unsigned)ts < clocks) { pol = -pol; lkpsg_sink(ts, pol * lkpsg.out[i][0], pol * lkpsg.out[i][1]); ts += lkpsg.freq_inc[i]; }
        } else {                                                /* noise: the LFSR is shifted on the rising edge of its clock */
            int sv = lkpsg.shift;
            while ((unsigned)ts < clocks) {
                pol = -pol;
                if (pol > 0) {
                    int out = sv & 1;
                    if (lkpsg.regs[6] & 4) sv = (sv >> 1) | (lkpsg_fb[sv & lkpsg.noise_mask] << lkpsg.noise_width);   /* white noise */
                    else sv = (sv >> 1) | (out << lkpsg.noise_width);                                                   /* periodic noise */
                    out = (sv & 1) - out;
                    lkpsg_sink(ts, out * lkpsg.out[3][0], out * lkpsg.out[3][1]);
                }
                ts += lkpsg.freq_inc[3];
            }
            lkpsg.shift = sv;
        }
        lkpsg.freq_cnt[i] = ts; lkpsg.polarity[i] = pol;
    }
}
