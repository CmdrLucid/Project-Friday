#!/usr/bin/env python3
"""Checkpoint log for input recordings (idempotent).  GENRECOMP_CHECKLOG=file writes one line every 120 frames, in a live run AND in a replay:
    frame room X.sub Y.sub Z health gold action hash rngseed vblankcounter
where hash covers the game fields (tile X/Y, sub-tile, Z, health) of the player and the 15 entity slots. Compare the .chk of a recording with the .chk of its
replay (`diff`) to find the first frame at which the replay no longer follows the live run. Reads the work RAM through bus_get_ram() (no emulated bus access, no timing change).
usage: patch_checklog.py path/to/genrecomp"""
import sys, os
p = os.path.join(sys.argv[1], "src/input.c")
s = open(p).read()
if "LANDSTALKER_CHECKLOG" in s:
    print("input.c checklog already patched"); sys.exit(0)
old = "    s_pad_state[0] = buttons;\n"
assert s.count(old) == 1, "input.c layout changed"
new = r'''    /* LANDSTALKER_CHECKLOG */
    {
        extern uint8_t *bus_get_ram(void);
        static FILE *cf; static int c_init; static long c_last = -1;
        if (!c_init) { c_init = 1; const char *cp = getenv("GENRECOMP_CHECKLOG"); if (cp) { cf = fopen(cp, "w"); if (cf) printf("input: checkpoints to %s\n", cp); } }
        long cfr = platform_frame_number();
        if (cf && cfr % 120 == 0 && cfr != c_last) {
            const uint8_t *r = bus_get_ram();
#define CKB(a) (r[((a) & 0xFFFF) ^ 1])
#define CKW(a) ((CKB(a) << 8) | CKB((a) + 1))
            unsigned long h = 1469598103u;
            for (int e = 0; e < 16; e++) {
                unsigned a = 0xFF5400u + e * 0x80u;
                static const unsigned off[] = {0, 1, 2, 3, 0x12, 0x13, 0x3E, 0x3F};
                for (unsigned k = 0; k < sizeof off / sizeof off[0]; k++) h = (h ^ CKB(a + off[k])) * 16777619u;
            }
            fprintf(cf, "%ld %d %d.%02X %d.%02X %d %d %d %04X %08lX %04X %04X\n", cfr, CKW(0xFF1204), CKB(0xFF5400), CKB(0xFF5402), CKB(0xFF5401), CKB(0xFF5403),
                    CKW(0xFF5412), CKW(0xFF543E), CKW(0xFF120E), CKW(0xFF542C), h & 0xFFFFFFFFu, CKW(0xFF0FAA), CKW(0xFF0F9C));
            fflush(cf); c_last = cfr;
#undef CKW
#undef CKB
        }
    }
'''
s = s.replace(old, new + old, 1)
open(p, "w").write(s); print("input.c patched: LANDSTALKER_CHECKLOG")
