#!/usr/bin/env python3
"""Timing phase 2 option (2026-10-30, user: 'phase 2 fuer die Raeume die ruckeln', docs/TIMING_PLAN.md section 16): NO 68K WAIT FOR THE VDP.
LANDSTALKER_VDPWAIT=0: the 68K is not halted for a 68K-bus DMA (bus_finish_dma charges no stall) and not stalled by a full VDP FIFO
(lk_t_fifo_w); the DMA / FIFO data path is unchanged (same VRAM / CRAM / VSRAM contents), only the 68K gets the time back for the game.
Default (unset or 1) = original timing, bit identical (the bench must stay IDENTICAL).  Only in the own timing mode (LANDSTALKER_TIMING=gpgx
ignores it).  Changes the game's timing on purpose: recordings made without it do not replay with it.
Idempotent (marker below).  usage: patch_vdpwait.py path/to/genrecomp   (after patch_lagstat.py)"""
import os, sys
ROOT = sys.argv[1]
VER = "LK_VDPWAIT v1"
BUS = os.path.join(ROOT, "src/bus.c")
t = open(BUS).read()
if VER in t:
    print("bus.c already patched:", VER); sys.exit(0)
E = [
    ("/* ---- LK_VDPTIME v1 (tools/patch_vdptime.py",
     "/* ---- LK_VDPWAIT v1 (tools/patch_vdpwait.py, TIMING_PLAN section 16): LANDSTALKER_VDPWAIT=0 = the 68K never waits for the VDP (phase 2 option, off by default) ---- */\n"
     "static int lk_vw_off = -1;\n"
     "static inline int lk_vw_nowait(void) { if (lk_vw_off < 0) { const char *e = getenv(\"LANDSTALKER_VDPWAIT\"), *t = getenv(\"LANDSTALKER_TIMING\"); lk_vw_off = e && !strcmp(e, \"0\") && !(t && !strcmp(t, \"gpgx\")); if (lk_vw_off) fprintf(stderr, \"timing: LANDSTALKER_VDPWAIT=0, the 68K does not wait for the VDP (DMA / FIFO stall off)\\n\"); } return lk_vw_off; }\n"
     "/* ---- LK_VDPTIME v1 (tools/patch_vdptime.py", 1),
    ("            if (r.stalled) { unsigned int c0 = m68k.cycles; m68k.cycles = r.cyc;",
     "            if (r.stalled && !lk_vw_nowait()) { unsigned int c0 = m68k.cycles; m68k.cycles = r.cyc;   /* LK_VDPWAIT v1 */", 1),
    ("            m68k.cycles = s_dma_pre + st;\n", "            m68k.cycles = s_dma_pre + (lk_vw_nowait() ? 0 : st);   /* LK_VDPWAIT v1 */\n", 1),
    ("        m68k.cycles = s_dma_pre + stall;\n", "        m68k.cycles = s_dma_pre + (lk_vw_nowait() ? 0 : stall);   /* LK_VDPWAIT v1 */\n", 1),
]
for old, new, cnt in E:
    assert t.count(old) == cnt, (old[:80], t.count(old))
    t = t.replace(old, new)
open(BUS, "w").write(t); print("bus.c patched:", VER)
