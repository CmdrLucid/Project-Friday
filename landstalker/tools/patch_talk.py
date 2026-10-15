#!/usr/bin/env python3
"""Speech blips on / off (options menu, ~/.landstalker_audio, env LANDSTALKER_TALK=0|1).
The text engine plays the talk sound of every printed character in ProcessChar_loc_23104 ($023104) with `trap #0` (sound command from $FF1154, symbol ProcessChar_loc_23104).
With the option off the generated C skips only that TRAP; the character is printed as before (the sound queue just gets no entry).
Runs on the GENERATED C (src/recomp) before tools/rename_generated.py.  Idempotent.  usage: patch_talk.py src/recomp"""
import glob, os, re, sys
d = sys.argv[1]
hit = 0
for p in sorted(glob.glob(os.path.join(d, "*.c"))):
    s = open(p).read()
    m = re.search(r"void \w*023104\(void\) \{", s)
    if not m:
        continue
    j = s.find("\n}\n", m.start())
    body = s[m.start():j]
    if "lk_talk_enabled" in body:
        print("talk: %s already patched" % os.path.basename(p)); hit = 1; continue
    a = "    g_m68k.pc = 0x023134; recomp_m68k_exception(32 + 0x0); /* TRAP #0x0 */\n"
    assert body.count(a) == 1, "talk: trap layout of $023104 changed"
    nb = body.replace(a, "    { extern int lk_talk_enabled(void); if (lk_talk_enabled()) {   /* speech blips option */\n    " + a.strip("\n") + "\n    } }\n")
    open(p, "w").write(s[:m.start()] + nb + s[j:])
    print("talk: patched %s" % os.path.basename(p)); hit = 1
assert hit, "talk: function $023104 not found"
