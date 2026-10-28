#!/usr/bin/env python3
"""Sound step 4 (2026-10-28, docs/SOUND_PLAN.md): the recompiled Z80 driver inside the GPGX core, SHADOW MODE (LANDSTALKER_SND_SHADOW=1; default off = nothing runs).
Copies tools/z80rt.h and tools/sndnative.c (hand written) into the core, #includes the generated driver (core/z80drv_gen.c, written by build.sh with tools/z80recomp.py from the user's ROM)
and hooks: z80_run (begin / end), z80_reset, the 68K's writes into Z80 RAM, the YM2612 reset, the per frame cycle rebase, and the chip write events of the trace helpers.
Idempotent.  usage: patch_sndnative.py path/to/genrecomp   (after patch_sndtrace.py; needs core/z80drv_gen.c)"""
import os, re, shutil, sys
root = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core"); here = os.path.dirname(os.path.abspath(__file__))
VER = "LK_SNDNATIVE v1"
if not os.path.exists(os.path.join(root, "z80drv_gen.c")):   # no ROM step before (selftest build without a ROM): a stub, the recompiled driver stays unused
    open(os.path.join(root, "z80drv_gen.c"), "w").write('/* stub: no known sound driver image */\n#include "z80rt.h"\nvoid z80drv_step(Z80S *s) { s->bad = 1; }\n'); print("z80drv_gen.c: stub written")
shutil.copy(os.path.join(here, "z80rt.h"), os.path.join(root, "z80rt.h"))
def edit(fname, fn):
    p = os.path.join(root, fname); s = open(p).read()
    if VER in s: print(fname, "already patched:", VER); return
    s = fn(s); open(p, "w").write(s); print(fname, "patched:", VER)
def memz80(s):
    inc = list(re.finditer(r'^#include .*\n', s, re.M))[-1]
    body = open(os.path.join(here, "sndnative.c")).read()
    # the generated file is included after the runtime (it only needs the declarations of z80rt.h)
    return s[:inc.end()] + "/* ---- %s: tools/sndnative.c ---- */\n" % VER + body + "\n#include \"z80drv_gen.c\"\n" + s[inc.end():]
edit("memz80.c", memz80)
def z80c(s):
    a = "void z80_run(unsigned int cycles)\n{"
    assert s.count(a) == 1
    inc = list(re.finditer(r'^#include .*\n', s, re.M))[-1]
    s = s[:inc.end()] + "extern void lk_nat_begin(void), lk_nat_end(void), lk_nat_reset(void);   /* %s */\n" % VER + s[inc.end():]
    s = s.replace(a, "static void z80_run_inner(unsigned int cycles);\nvoid z80_run(unsigned int cycles) { lk_nat_begin(); z80_run_inner(cycles); lk_nat_end(); }\nstatic void z80_run_inner(unsigned int cycles)\n{")
    c = "    Z80.after_ei = FALSE;\n    R++;\n    EXEC_INLINE(op,ROP());"
    assert s.count(c) == 1
    s = s.replace(c, "    Z80.after_ei = FALSE;\n    R++;\n    lk_nat_gstep();   /* %s: debug trace of the GPGX Z80 (LANDSTALKER_SND_SHADOW=3) */\n    EXEC_INLINE(op,ROP());" % VER)
    s = s.replace("extern void lk_nat_begin(void), lk_nat_end(void), lk_nat_reset(void);", "extern void lk_nat_begin(void), lk_nat_end(void), lk_nat_reset(void), lk_nat_gstep(void);", 1)
    b = "void z80_reset(void)\n{\n"
    assert s.count(b) == 1
    return s.replace(b, b + "  lk_nat_reset();   /* %s */\n" % VER)
edit("z80/z80.c", z80c)
def m68k(s):
    old = "      lk_st_zram(m68k.cycles, address & 0x1FFF, data);\n"
    assert s.count(old) == 1
    s = s.replace(old, old + "      lk_nat_ram_w(address & 0x1FFF, data);   /* %s */\n" % VER)
    inc = list(re.finditer(r'^#include .*\n', s, re.M))[-1]
    return s[:inc.end()] + "extern void lk_nat_ram_w(unsigned a, unsigned v);   /* %s */\n" % VER + s[inc.end():]
edit("mem68k.c", m68k)
def soundc(s):
    old = "static void YM2612_Reset(unsigned int cycles)\n{\n"
    assert s.count(old) == 1
    s = s.replace(old, "extern void lk_nat_ymreset(void), lk_nat_gevent(int kind, unsigned t, int a, int v), lk_nat_gdbg(unsigned t, unsigned v, int c);   /* %s */\n" % VER + old + "  lk_nat_ymreset();\n")
    # the trace helpers pass the Z80's chip writes on to the native comparison
    s = s.replace("void lk_st_ym(int who, unsigned int cycles, unsigned int a, unsigned int v) { if (lk_st_on())", "void lk_st_ym(int who, unsigned int cycles, unsigned int a, unsigned int v) { if (who) lk_nat_gevent('Y', cycles, a & 3, v & 0xFF); if (lk_st_on())")
    s = s.replace("void lk_st_psg(int who, unsigned int cycles, unsigned int v) { if (lk_st_on())", "void lk_st_psg(int who, unsigned int cycles, unsigned int v) { if (who) lk_nat_gevent('P', cycles, 0, v & 0xFF); if (lk_st_on())")
    # the status reads of the Z80 (value as GPGX's chip returns it) for the comparison
    r = "    /* read FM status */\n    if (cycles >= fm_cycles_busy)\n    {\n      /* BUSY flag cleared */\n      return YM2612Read();\n    }\n    else\n    {\n      /* BUSY flag set */\n      return YM2612Read() | 0x80;\n    }\n"
    assert s.count(r) == 1
    s = s.replace(r, "    /* read FM status */\n    { unsigned int lk_v = (cycles >= fm_cycles_busy) ? YM2612Read() : (YM2612Read() | 0x80); lk_nat_gevent('R', cycles, 0, lk_v); lk_nat_gdbg(cycles, lk_v, fm_cycles_count); return lk_v; }   /* LK_SNDNATIVE v1 */\n")
    s = s.replace("void lk_st_ym(int who,", "int lk_fm_count(void) { return fm_cycles_count; }   /* %s */\nint lk_fm_busy(void) { return fm_cycles_busy; }\nvoid lk_st_ym(int who," % VER, 1)
    q = "    fm_cycles_count = fm_cycles_start = time - cycles;\n"
    assert s.count(q) == 1
    s = s.replace(q, "    { extern void lk_nat_gframe(int before, int after); lk_nat_gframe(time, time - cycles); }   /* %s */\n" % VER + q)
    return s
edit("sound/sound.c", soundc)
def systemc(s):
    n = s.count("  Z80.cycles -= mcycles_vdp;\n")
    assert n >= 3, n
    inc = list(re.finditer(r'^#include .*\n', s, re.M))[-1]
    s = s.replace("  Z80.cycles -= mcycles_vdp;\n", "  Z80.cycles -= mcycles_vdp;\n  lk_nat_frame(mcycles_vdp);   /* %s */\n" % VER)
    return s[:inc.end()] + "extern void lk_nat_frame(unsigned mcycles);   /* %s */\n" % VER + s[inc.end():]
edit("system.c", systemc)
# the recompiled bus (genrecomp src/bus.c) runs the frame loop and rebases the Z80 clock itself
pb = os.path.join(sys.argv[1], "src/bus.c"); b = open(pb).read()
if VER not in b:
    old = "            Z80.cycles -= mcycles_vdp;\n            mcycles_vdp = 0;\n"
    assert b.count(old) == 1, "bus.c: frame rebase layout changed"
    b = b.replace(old, "            Z80.cycles -= mcycles_vdp;\n            { extern void lk_nat_frame(unsigned); lk_nat_frame(mcycles_vdp); }   /* %s */\n            mcycles_vdp = 0;\n" % VER)
    open(pb, "w").write(b); print("bus.c patched:", VER)
else: print("bus.c already patched:", VER)
# debug accessor of the chip's timer state (LANDSTALKER_SND_SHADOW=4)
pyc = os.path.join(root, "sound/ym2612.c"); y = open(pyc).read()
if VER not in y:
    a = "void YM2612Update(int *buffer, int length)\n{"
    assert y.count(a) == 1
    y = y.replace(a, "void lk_ym_state(int *v) { v[0] = ym2612.OPN.ST.mode; v[1] = ym2612.OPN.ST.TBC; v[2] = ym2612.OPN.ST.TBL; v[3] = ym2612.OPN.ST.status; v[4] = ym2612.OPN.ST.TAC; v[5] = ym2612.OPN.ST.TAL; }   /* %s */\n" % VER + a)
    open(pyc, "w").write(y); print("ym2612.c patched:", VER)
pm = os.path.join(root, "memz80.c"); m = open(pm).read()
if "LK_SNDNATIVE dbg" not in m:
    a = "static void z80_request_68k_bus_access(void)\n{\n"
    assert m.count(a) == 1
    m = m.replace(a, a + "  { static int dbg = -1; extern long platform_frame_number(void); if (dbg < 0) { const char *e = getenv(\"LANDSTALKER_SND_SHADOW\"); dbg = e && *e == '6'; } if (dbg && platform_frame_number() == 3600 && Z80.cycles > 780000 && Z80.cycles < 900000) fprintf(stderr, \"gpgx buswait now %u dma_end %u type %d\\n\", Z80.cycles, (unsigned)dma_endCycles, (int)dma_type); }   /* LK_SNDNATIVE dbg */\n")
    open(pm, "w").write(m); print("memz80.c patched: LK_SNDNATIVE dbg")
# gen_zbusreq_w / gen_zreset_w set Z80.cycles to the 68K's time when the Z80 restarts (it may be EARLIER than where the Z80 had run to, e.g. after a long DMA wait): the recompiled copy follows
pg = os.path.join(root, "genesis.c"); g = open(pg).read()
if VER not in g:
    old = "      Z80.cycles = ((cycles + 14) / 15) * 15;\n"
    assert g.count(old) == 2, g.count(old)
    g = g.replace(old, old + "      lk_nat_resync();   /* %s */\n" % VER)
    inc = list(re.finditer(r'^#include .*\n', g, re.M))[-1]
    g = g[:inc.end()] + "extern void lk_nat_resync(void);   /* %s */\n" % VER + g[inc.end():]
    open(pg, "w").write(g); print("genesis.c patched:", VER)
