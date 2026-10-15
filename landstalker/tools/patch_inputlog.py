#!/usr/bin/env python3
"""Record and replay controller input (idempotent).

  GENRECOMP_INPUTLOG=file    every frame where the pad state changes, append "frame hexmask"
  GENRECOMP_INPUTSCRIPT=file replay such a file (works headless, in genrecomp_ref too)

The mask uses the Genesis pad bits (UP 1 DOWN 2 LEFT 4 RIGHT 8 B 10 C 20 A 40 START 80 ...).
usage: patch_inputlog.py path/to/genrecomp
"""
import sys, os
root = sys.argv[1]

def patch(rel, old, new, marker):
    p = os.path.join(root, rel); s = open(p).read()
    if marker in s: print(rel, "already patched:", marker); return
    assert old in s, f"{rel}: layout changed ({old[:50]!r})"
    open(p, "w").write(s.replace(old, new, 1)); print(rel, "patched:", marker)

# --- replay: platform_scripted_buttons() also reads GENRECOMP_INPUTSCRIPT ------
patch("src/platform_sdl.c",
      "uint16_t platform_scripted_buttons(void) {\n    uint16_t b = 0;\n",
      "uint16_t platform_scripted_buttons(void) {\n    uint16_t b = 0;\n"
      "    /* LANDSTALKER_INPUTSCRIPT */\n"
      "    {\n"
      "        static long sf[200000]; static uint16_t sm[200000]; static int n, idx = -1, loaded;\n"
      "        if (!loaded) {\n"
      "            loaded = 1;\n"
      "            const char *path = getenv(\"GENRECOMP_INPUTSCRIPT\");\n"
      "            FILE *f = path ? fopen(path, \"r\") : NULL;\n"
      "            long fr; unsigned m;\n"
      "            while (f && n < 200000 && fscanf(f, \"%ld %x\", &fr, &m) == 2) { sf[n] = fr; sm[n] = (uint16_t)m; n++; }\n"
      "            if (f) { fclose(f); printf(\"input: replaying %d changes from %s\\n\", n, path); }\n"
      "        }\n"
      "        while (idx + 1 < n && sf[idx + 1] <= s_frame_no) idx++;\n"
      "        if (idx >= 0) b |= sm[idx];\n"
      "    }\n",
      "LANDSTALKER_INPUTSCRIPT")

# --- record: log the final pad state whenever it changes ---------------------
patch("src/input.c",
      "    s_pad_state[0] = buttons;\n",
      "    /* LANDSTALKER_INPUTLOG */\n"
      "    {\n"
      "        static FILE *lf; static int lf_init; static int prev = -1;\n"
      "        if (!lf_init) { lf_init = 1; const char *p = getenv(\"GENRECOMP_INPUTLOG\"); if (p) { char bak[1024]; snprintf(bak, sizeof bak, \"%s.bak\", p); rename(p, bak); lf = fopen(p, \"w\"); if (lf) printf(\"input: logging to %s\\n\", p); } }\n"
      "        if (lf && (int)buttons != prev) { fprintf(lf, \"%ld %04X\\n\", platform_frame_number(), buttons); fflush(lf); prev = buttons; }\n"
      "    }\n"
      "    s_pad_state[0] = buttons;\n",
      "LANDSTALKER_INPUTLOG")
