/* render.c SF2 MIDI OUT.wav [GAIN] : MIDI -> WAV (44100 Hz stereo 16 bit) with TinySoundFont (MIT, schellingb); local test tool */
#define TSF_IMPLEMENTATION
#include "tsf.h"
#define TML_IMPLEMENTATION
#include "tml.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
  if (argc < 4) { fprintf(stderr, "usage: render SF2 MIDI OUT.wav [GAIN]\n"); return 1; }
  tsf *f = tsf_load_filename(argv[1]); tml_message *m = tml_load_filename(argv[2]);
  if (!f || !m) { fprintf(stderr, "load failed\n"); return 1; }
  float gain = argc > 4 ? atof(argv[4]) : 0.0f;
  tsf_channel_set_bank_preset(f, 9, 128, 0); tsf_set_output(f, TSF_STEREO_INTERLEAVED, 44100, gain);
  unsigned int total; tml_get_info(m, NULL, NULL, NULL, NULL, &total);
  double ms = 0; tml_message *p = m; FILE *o = fopen(argv[3], "wb"); unsigned char h[44] = {0}; fwrite(h, 1, 44, o);
  long frames = 0; short buf[2 * 64];
  while (p || ms < total + 4000) {
    for (; p && p->time <= ms; p = p->next) switch (p->type) {
      case TML_PROGRAM_CHANGE: tsf_channel_set_presetnumber(f, p->channel, p->program, p->channel == 9); break;
      case TML_NOTE_ON: tsf_channel_note_on(f, p->channel, p->key, p->velocity / 127.0f); break;
      case TML_NOTE_OFF: tsf_channel_note_off(f, p->channel, p->key); break;
      case TML_PITCH_BEND: tsf_channel_set_pitchwheel(f, p->channel, p->pitch_bend); break;
      case TML_CONTROL_CHANGE: tsf_channel_midi_control(f, p->channel, p->control, p->control_value); break; }
    tsf_render_short(f, buf, 64, 0); fwrite(buf, 2, 128, o); frames += 64; ms += 64 * 1000.0 / 44100.0;
  }
  unsigned int ds = frames * 4, rs = ds + 36, sr = 44100, br = 44100 * 4; unsigned short fmt = 1, chn = 2, ba = 4, bps = 16; unsigned int fl = 16;
  fseek(o, 0, SEEK_SET); fwrite("RIFF", 1, 4, o); fwrite(&rs, 4, 1, o); fwrite("WAVEfmt ", 1, 8, o); fwrite(&fl, 4, 1, o); fwrite(&fmt, 2, 1, o); fwrite(&chn, 2, 1, o);
  fwrite(&sr, 4, 1, o); fwrite(&br, 4, 1, o); fwrite(&ba, 2, 1, o); fwrite(&bps, 2, 1, o); fwrite("data", 1, 4, o); fwrite(&ds, 4, 1, o); fclose(o);
  printf("%s: %.1f s\n", argv[3], frames / 44100.0); return 0;
}
