#!/usr/bin/env python3
"""Yes / No prompt layout from the language file (docs/TEXT_LAYER.md 'ui', 2026-10-26).  YesNoPrompt $024724 prints 'Yes' at x $50 and 'No' at x $A0 and moves a cursor sprite
(x $FF0566) between the FIXED positions $D0 / $120; the German build moved the second word and the cursor by 8.  In the GENERATED C of the prompt (entry points $024724 $024778
$0247CC $0247D4 $0247E8 $024804 $024822, every entry repeats the shared code) the three constants become lk_lang_ui(key, default) calls (patch_lang.py, language file block 'ui':
1 = text x of the second word, 3 = cursor x on it); without a language file the defaults are returned.  Runs on src/recomp before tools/rename_generated.py.  Idempotent.
usage: patch_yesno.py src/recomp"""
import glob, os, re, sys
d = sys.argv[1]
ENTRIES = ("024724", "024778", "0247CC", "0247D4", "0247E8", "024804", "024822")
RULES = (("{ uint16_t _mv = (uint16_t)(0xa0); bus_write16(0xFF1194, _mv);", "{ uint16_t _mv = (uint16_t)(LKUI(1, 0xa0)); bus_write16(0xFF1194, _mv);"),
         ("M68K_CMP16(bus_read16(0xFF0566), 0x120);", "M68K_CMP16(bus_read16(0xFF0566), LKUI(3, 0x120));"),
         ("{ uint16_t _mv = (uint16_t)(0x120); bus_write16(0xFF0566, _mv);", "{ uint16_t _mv = (uint16_t)(LKUI(3, 0x120)); bus_write16(0xFF0566, _mv);"))
HELPER = "#define LKUI(k, def) ({ extern uint32_t lk_lang_ui(int, uint32_t); lk_lang_ui((k), (def)); })   /* LK_YESNO v1 (tools/patch_yesno.py) */\n"
hit = 0
for p in sorted(glob.glob(os.path.join(d, "*.c"))):
    s = open(p).read()
    changed = False
    for e in ENTRIES:
        m = re.search(r"void \w*%s\(void\) \{" % e, s)
        if not m:
            continue
        j = s.find("\n}\n", m.start())
        body = s[m.start():j]
        nb = body
        for a, b in RULES:
            nb = nb.replace(a, b)
        if nb != body:
            s = s[:m.start()] + nb + s[j:]
            changed = True
            hit += 1
    if changed:
        if "LK_YESNO v1" not in s:
            k = s.index("\n/*") if "\n/*" in s else 0
            s = s[:k + 1] + HELPER + s[k + 1:]
        open(p, "w").write(s)
        print("yesno: patched %s" % os.path.basename(p))
print("yesno: %d entry functions changed" % hit)
assert hit or any("LK_YESNO v1" in open(q).read() for q in glob.glob(os.path.join(d, "*.c"))), "yesno: YesNoPrompt not found"
