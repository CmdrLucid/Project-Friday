#!/usr/bin/env python3
"""genrecomp_ref (the reference runner) never loaded the battery save, so replays that start from the user's church save ran from an EMPTY slot in the reference
and from the real save in the recompiled build (win42: room $0255 at frame 160 in rec, room 0 in ref -> every later comparison meaningless).
This patch loads `<rom>.srm` (or $LANDSTALKER_SAVE) into GPGX's sram after system_reset(), read-only: the reference never writes the file. Idempotent.
usage: patch_refsram.py path/to/genrecomp"""
import os, sys
p = os.path.join(sys.argv[1], "tools/ref_runner/main.c")
s = open(p).read()
if "LANDSTALKER_REFSRAM" in s:
    print("ref_runner already patched: LANDSTALKER_REFSRAM"); sys.exit(0)
old = "    system_reset();\n"
assert s.count(old) == 1, "ref_runner/main.c: system_reset layout changed"
new = old + r'''    { /* LANDSTALKER_REFSRAM: load the battery save like the recompiled build does (read-only) */
        char sp[MAXPATHLEN + 8];
        const char *e = getenv("LANDSTALKER_SAVE");
        if (e && *e) snprintf(sp, sizeof(sp), "%s", e);
        else {
            snprintf(sp, sizeof(sp), "%s", path);
            char *dot = strrchr(sp, '.'), *sl = strrchr(sp, '/');
            if (dot && (!sl || dot > sl)) *dot = 0;
            strncat(sp, ".srm", 5);
        }
        FILE *sf = sram.on ? fopen(sp, "rb") : NULL;
        if (sf) { size_t n = fread(sram.sram, 1, 0x10000, sf); fclose(sf); fprintf(stderr, "ref: SRAM loaded from %s (%zu bytes)\n", sp, n); }
        else fprintf(stderr, "ref: no SRAM loaded (%s)\n", sram.on ? sp : "cartridge has no battery RAM");
    }
'''
s = s.replace(old, new, 1)
if "#include <stdlib.h>" not in s:
    s = s.replace("#include <string.h>\n", "#include <string.h>\n#include <stdlib.h>\n", 1)
open(p, "w").write(s)
print("ref_runner patched: LANDSTALKER_REFSRAM")
