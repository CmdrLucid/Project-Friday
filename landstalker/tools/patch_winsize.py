#!/usr/bin/env python3
"""Test aid LK_WINSIZE v1: LANDSTALKER_WINSIZE=WxH sets the size of the game window at start (e.g. 1920x1080 with LANDSTALKER_HIDDEN=1
for trailer footage: LANDSTALKER_PRESENT_SHOT then writes full-HD pictures of the GPU-lit game). No effect without the env var. Idempotent.
usage: patch_winsize.py path/to/genrecomp"""
import os, sys
VER = "LK_WINSIZE v1"
p = os.path.join(sys.argv[1], "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched:", VER)
else:
  a = "    int w = GEN_RENDER_WIDTH * scale;\n    int h = GEN_RENDER_HEIGHT * scale;\n"
  assert s.count(a) == 1, "platform_sdl.c: window size lines changed"
  s = s.replace(a, a + "    { const char *e = getenv(\"LANDSTALKER_WINSIZE\"); int ew, eh; if (e && sscanf(e, \"%%dx%%d\", &ew, &eh) == 2 && ew >= 320 && eh >= 224 && ew <= 7680 && eh <= 4320) { w = ew; h = eh; } }   /* %s test aid */\n" % VER)
  open(p, "w").write(s)
  print("platform_sdl.c patched:", VER)

# test aid LK_CKEVERY v1: GENRECOMP_CHECKEVERY=N writes the checkpoint log every N frames instead of 120 (trailer footage: find frames where Nigel
# walks into a wall = position unchanged while a direction is held). No effect without the env var.
q = os.path.join(sys.argv[1], "src/input.c")
s = open(q).read()
if "LK_CKEVERY" in s:
    print("input.c already patched: LK_CKEVERY v1")
else:
    a = "        if (cf && cfr % 120 == 0 && cfr != c_last) {"
    assert s.count(a) == 1, "input.c: checklog interval line changed"
    s = s.replace(a, "        static long lk_ck_n = -1; if (lk_ck_n < 0) { const char *ce = getenv(\"GENRECOMP_CHECKEVERY\"); lk_ck_n = ce && atol(ce) > 0 ? atol(ce) : 120; }   /* LK_CKEVERY v1 test aid */\n"
                  "        if (cf && cfr % lk_ck_n == 0 && cfr != c_last) {")
    open(q, "w").write(s)
    print("input.c patched: LK_CKEVERY v1")

# test aid LK_EQHOLDS v1: LANDSTALKER_EQHOLD may hold several ranges "a-b,c-d,.." (trailer: four sword changes in one run); one range works as before.
s = open(q).read()
if "LK_EQHOLDS" in s:
    print("input.c already patched: LK_EQHOLDS v1")
else:
    a = 'if (eh && frame >= e0 && frame <= e1) { d[LK_BEQ] = 1; any = 1; } }'
    assert s.count(a) == 1, "input.c: EQHOLD test aid line changed"
    s = s.replace(a, 'if (eh) { const char *pp = eh; long r0, r1; int nn; while (sscanf(pp, "%ld-%ld%n", &r0, &r1, &nn) == 2) { if (frame >= r0 && frame <= r1) { d[LK_BEQ] = 1; any = 1; } pp += nn; if (*pp != \',\') break; pp++; } } }   /* LK_EQHOLDS v1 */')
    open(q, "w").write(s)
    print("input.c patched: LK_EQHOLDS v1")
