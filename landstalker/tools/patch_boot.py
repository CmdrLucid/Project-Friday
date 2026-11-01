#!/usr/bin/env python3
"""System start of our own (docs/SOUND_PLAN.md section 13, step 4 of the way off the emulator): GPGX's core/system.c gets
tools/lkboot.c (#included just before system_init) and a hook at the top of system_reset.  Marker LK_BOOT v1 = step 4.2: gen_reset /
io_reset ours for the Mega Drive cartridge path (vdp_init / vdp_reset: tools/lkvdp.c, patch_vdpport.py).
Env LANDSTALKER_BOOT: unset / gpgx = GPGX's start (default until the user confirms), own = ours, check = both compared (stderr
'vdpboot check: ...').  Idempotent.  usage: patch_boot.py path/to/genrecomp   (after patch_vdpport.py)"""
import os, shutil, sys
core = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core"); here = os.path.dirname(os.path.abspath(__file__))
VER = "LK_BOOT v1"
shutil.copy(os.path.join(here, "lkboot.c"), os.path.join(core, "lkboot.c"))
p = os.path.join(core, "system.c"); s = open(p).read()
if VER in s:
    print("system.c already patched:", VER); sys.exit(0)

def rep(a, b):
    global s
    assert s.count(a) == 1, f"system.c layout changed: {a[:70]!r} ({s.count(a)}x)"
    s = s.replace(a, b, 1)

SI = "void system_init(void)\n{\n"
rep(SI, '#include "lkboot.c"   /* %s */\n\n' % VER + SI)
SR = "void system_reset(void)\n{\n"
rep(SR, SR + "  if (lkb_reset_hook()) return;   /* %s */\n" % VER)
open(p, "w").write(s)
print("system.c patched:", VER)
