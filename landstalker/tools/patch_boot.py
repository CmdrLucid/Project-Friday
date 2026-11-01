#!/usr/bin/env python3
"""System start of our own (docs/SOUND_PLAN.md section 13, step 4 of the way off the emulator): GPGX's core/system.c gets
tools/lkboot.c (#included just before system_init) and a hook at the top of system_reset.  Marker LK_BOOT v1 = step 4.2: gen_reset /
io_reset ours for the Mega Drive cartridge path; LK_BOOT v2 = + step 4.3: system_init (gen_init memory maps + md_cart_init for a
plain cartridge); LK_BOOT v3 = step 4.4: default ours (vdp_init / vdp_reset: tools/lkvdp.c, patch_vdpport.py).
Env LANDSTALKER_BOOT: unset / own = ours (default since step 4.4), gpgx = GPGX's start (rollback), check = both compared (stderr
'vdpboot check: ...').  Idempotent.  usage: patch_boot.py path/to/genrecomp   (after patch_vdpport.py)"""
import os, shutil, sys
core = os.path.join(sys.argv[1], "ext/Genesis-Plus-GX/core"); here = os.path.dirname(os.path.abspath(__file__))
VER = "LK_BOOT v3"
shutil.copy(os.path.join(here, "lkboot.c"), os.path.join(core, "lkboot.c"))
p = os.path.join(core, "system.c"); s = open(p).read()
if VER in s:
    print("system.c already patched:", VER); sys.exit(0)

def rep(a, b):
    global s
    assert s.count(a) == 1, f"system.c layout changed: {a[:70]!r} ({s.count(a)}x)"
    s = s.replace(a, b, 1)

SI = "void system_init(void)\n{\n"
rep(SI, '#include "lkboot.c"   /* %s */\n\n' % VER + SI + "  if (lkb_init_hook()) return;   /* %s */\n" % VER)
SR = "void system_reset(void)\n{\n"
rep(SR, SR + "  if (lkb_reset_hook()) return;   /* %s */\n" % VER)
open(p, "w").write(s)
print("system.c patched:", VER)

# step 4.3: the cartridge's default $A130xx write handler is static in md_cart.c
p = os.path.join(core, "cart_hw", "md_cart.c"); s = open(p).read()
if VER not in s:
    a = "static void default_time_w(uint32 address, uint32 data);\n"
    assert s.count(a) == 1, "md_cart.c layout changed"
    s = s.replace(a, a + "void lk_cart_default_time_w(void) { cart.hw.time_w = default_time_w; }   /* %s */\n" % VER, 1)
    open(p, "w").write(s); print("md_cart.c patched:", VER)
