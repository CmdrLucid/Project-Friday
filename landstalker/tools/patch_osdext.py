#!/usr/bin/env python3
"""patch_osdext.py path/to/genrecomp -- LK_OSDEXT v1 (2026-11-18, found with gcc -fsanitize=address while checking GitHub #21):
Genesis Plus GX's load_rom() passes `char extension[4]` to load_archive() (genrecomp src/osd.c), which wrote 16 bytes into it
(strncpy(extension, dot, 15) pads with zeros + extension[15] = 0): a 12 byte stack overflow at ROM load whose effect depends on the
compiler / stack layout (the gcc build of 2026-11-18 lost sync with a user recording, the zig build did not). Now at most 4 bytes
(3 characters + NUL, GPGX's own contract). Idempotent."""
import os, sys
p = os.path.join(sys.argv[1], "src", "osd.c")
s = open(p).read()
if "LK_OSDEXT v1" in s:
    print("osd.c: LK_OSDEXT v1 already applied"); sys.exit(0)
a = "            strncpy(extension, dot, 15);\n            extension[15] = '\\0';\n"
b = "            strcpy(extension, \".bin\");\n"
assert s.count(a) == 1 and s.count(b) == 1, "osd.c: load_archive extension code changed"
s = s.replace(a, "            { size_t n = strlen(filename); memcpy(extension, filename + (n >= 3 ? n - 3 : 0), n >= 3 ? 3 : n); extension[n >= 3 ? 3 : n] = '\\0'; (void)dot; }   /* LK_OSDEXT v1: GPGX's contract = the LAST 3 characters in char[4] ('.md', 'sms', '.gg') */\n", 1)
s = s.replace(b, "            strcpy(extension, \"bin\");   /* LK_OSDEXT v1: 3 characters + NUL fit char[4] */\n", 1)
open(p, "w").write(s); print("osd.c patched: LK_OSDEXT v1 (load_archive writes at most 4 bytes of the extension)")
