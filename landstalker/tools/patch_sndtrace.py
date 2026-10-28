#!/usr/bin/env python3
"""Sound, step S0 (2026-10-28, user: 'sound' = get the sound side independent of the emulator): the GOLDEN TRACE.
LANDSTALKER_SNDTRACE=file writes one text line for everything that reaches the sound hardware, as the running game produces it:
  Y <frame> <who> <cycles> <port 0-3> <value>      YM2612 write (who: 68 = 68000, Z8 = Z80; cycles = that CPU's master cycle counter at the write)
  P <frame> <who> <cycles> <value>                 PSG (SN76489) write
  M <frame> 68 <cycles> <zram addr hex> <value>    68000 write into Z80 RAM at $1FF0..$1FFF (the command mailbox: command $1FFF, arguments $1FFC / $1FFD) or the bank register ($6000: 'B')
  U <frame> <count>                                number of 68000 writes into Z80 RAM below $1FF0 since the last line (the driver upload)
Any replacement of the Z80 sound driver (own C port of tools/../sounddrv.asm) must produce the same Y / P lines for the same M lines: this is the oracle.  No effect without the variable.
Idempotent.  usage: patch_sndtrace.py path/to/genrecomp   (after patch_sndsep.py)"""
import os, sys
root = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core")
VER = "LK_SNDTRACE v1"

# shared helper in sound.c
p = os.path.join(root, "sound/sound.c"); s = open(p).read()
if VER not in s:
    a = "static void YM2612_Write(unsigned int cycles, unsigned int a, unsigned int v)\n{\n"
    assert s.count(a) == 1
    helper = r'''/* ---- LK_SNDTRACE v1 (tools/patch_sndtrace.py) ---- */
#include <stdio.h>
#include <stdlib.h>
extern long platform_frame_number(void);
static FILE *lk_st_f; static int lk_st_init; static long lk_st_upl;
static int lk_st_on(void) { if (!lk_st_init) { const char *e = getenv("LANDSTALKER_SNDTRACE"); lk_st_init = 1; if (e && *e) lk_st_f = fopen(e, "w"); } return lk_st_f != NULL; }
void lk_st_ym(int who, unsigned int cycles, unsigned int a, unsigned int v) { if (lk_st_on()) fprintf(lk_st_f, "Y %ld %s %u %u %02X\n", platform_frame_number(), who ? "Z8" : "68", cycles, a & 3, v & 0xFF); }
void lk_st_psg(int who, unsigned int cycles, unsigned int v) { if (lk_st_on()) fprintf(lk_st_f, "P %ld %s %u %02X\n", platform_frame_number(), who ? "Z8" : "68", cycles, v & 0xFF); }
void lk_st_zram(unsigned int cycles, unsigned int addr, unsigned int v) {
    if (!lk_st_on()) return;
    if (addr < 0x1FF0) { lk_st_upl++; return; }
    if (lk_st_upl) { fprintf(lk_st_f, "U %ld %ld\n", platform_frame_number(), lk_st_upl); lk_st_upl = 0; }
    fprintf(lk_st_f, "M %ld 68 %u %04X %02X\n", platform_frame_number(), cycles, addr, v & 0xFF);
}
void lk_st_bank(unsigned int cycles, unsigned int v) { if (lk_st_on()) fprintf(lk_st_f, "M %ld 68 %u B %02X\n", platform_frame_number(), cycles, v & 0xFF); }
'''
    s = s.replace(a, helper + a, 1)
    open(p, "w").write(s)
    print("sound.c patched:", VER)
else:
    print("sound.c already patched:", VER)

import re
decl = "/* LK_SNDTRACE v1 */\nextern void lk_st_ym(int who, unsigned int cycles, unsigned int a, unsigned int v), lk_st_psg(int who, unsigned int cycles, unsigned int v), lk_st_zram(unsigned int cycles, unsigned int addr, unsigned int v), lk_st_bank(unsigned int cycles, unsigned int v);\n"
def hook(fname, edits):
    p = os.path.join(root, fname); t = open(p).read()
    if VER in t: print(fname, "already patched:", VER); return
    # declaration after the last #include
    inc = list(re.finditer(r'^#include .*\n', t, re.M))[-1]
    t = t[:inc.end()] + decl + t[inc.end():]
    for pat, rep in edits:
        t, n = re.subn(pat, rep, t)
        assert n >= 1, (fname, pat)
    open(p, "w").write(t); print(fname, "patched:", VER)
hook("memz80.c", [(r'fm_write\((Z80\.cycles), ([^,]+), ([^)]+)\);', r'(lk_st_ym(1, \1, \2, \3), fm_write(\1, \2, \3));'),
                  (r'psg_write\((Z80\.cycles), ([^)]+)\);', r'(lk_st_psg(1, \1, \2), psg_write(\1, \2));')])
hook("mem68k.c", [(r'fm_write\((m68k\.cycles), ([^,]+), ([^)]+)\);', r'(lk_st_ym(0, \1, \2, \3), fm_write(\1, \2, \3));'),
                  (r'psg_write\((m68k\.cycles), ([^)]+)\);', r'(lk_st_psg(0, \1, \2), psg_write(\1, \2));'),
                  (r'      zram\[address & 0x1FFF\] = data;\n      return;', r'      lk_st_zram(m68k.cycles, address & 0x1FFF, data);\n      zram[address & 0x1FFF] = data;\n      return;'),
                  (r'(        case 0x60:  /\* Bank register \*/\n        \{\n)', r'\1          lk_st_bank(m68k.cycles, data);\n')])
hook("membnk.c", [(r'psg_write\((Z80\.cycles), ([^)]+)\);', r'(lk_st_psg(1, \1, \2), psg_write(\1, \2));')])   # the Z80's PSG writes ($7F11) arrive here through the bank / VDP area
