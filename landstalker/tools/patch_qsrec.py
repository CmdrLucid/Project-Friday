#!/usr/bin/env python3
"""Quick save / quick load in input recordings (2026-10-30).  The input log (GENRECOMP_INPUTLOG) only holds the Mega Drive pad bits; a quick save (L2 / F9) or
quick load (L1 held / F10) is not a pad bit, so a replay of a recording with a quick load stayed in the old room (HANDOFF 0a177 point 2, rec_20261030_0536: live
quick load at frame 360 Mercator -> room 454).
 * LANDSTALKER_QSLOG=file      every quick request that reaches platform_quick_request (option On) appends "s<frame>" / "l<frame>" (frame = platform_frame_number()
                               at the input poll; all pad AND keyboard requests come through lk_keys_step since patch_keys.py)
 * LANDSTALKER_QSPLAY="l360,s900"  replay: the request is posted at the SAME place (input poll of that frame), whatever the Quick Save option says
                               (the recording script writes this line into rec_<time>.cfg).
LANDSTALKER_QSREQ (patch_quicksave.py) stays as it was: it posts at the frame END, which is one step later than a real press (not exact for replays).
Needs patch_quicksave.py and patch_keys.py before it.  Idempotent.  usage: patch_qsrec.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_QSREC v1"

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    old = "void platform_quick_request(int what) { if (!lk_qsave_get()) { lk_qs_off_hint(); return; } lk_qs_req = what; lk_qs_req_frame = s_frame_no; }\n"
    assert s.count(old) == 1, "platform_sdl.c: run patch_quicksave.py first (or its layout changed)"
    new = r'''static void lk_qs_rec(int what) {   /* LK_QSREC v1: LANDSTALKER_QSLOG = file of quick requests for the recording ("s<frame>" / "l<frame>") */
    static FILE *f; static int init;
    if (!init) { const char *e = getenv("LANDSTALKER_QSLOG"); init = 1; if (e) f = fopen(e, "w"); }
    if (f) { fprintf(f, "%c%ld\n", what == 1 ? 's' : 'l', s_frame_no); fflush(f); }
}
void platform_quick_request(int what) { if (!lk_qsave_get()) { lk_qs_off_hint(); return; } lk_qs_req = what; lk_qs_req_frame = s_frame_no; lk_qs_rec(what); }
void lk_qs_play(long frame) {   /* LK_QSREC v1: LANDSTALKER_QSPLAY="l360,s900" = the recorded requests, posted at the input poll like the live press (parsed once, any length: other event letters such as Sprint p / r are skipped) */
    static int init, n; static long *ev; static char *evk;
    if (!init) { const char *e = getenv("LANDSTALKER_QSPLAY"), *q; init = 1;
        if (e) { size_t cap = strlen(e) / 2 + 1; ev = (long *)malloc(cap * sizeof *ev); evk = (char *)malloc(cap); for (q = e; *q && ev && evk; q++) if ((*q == 's' || *q == 'l') && (q == e || q[-1] == ',') && (size_t)n < cap) { evk[n] = *q; ev[n] = atol(q + 1); n++; } } }
    for (int k = 0; k < n; k++) if (ev[k] == frame) { lk_qs_req = evk[k] == 's' ? 1 : 2; lk_qs_req_frame = s_frame_no; }
}
'''
    s = s.replace(old, new, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/input.c")
s = open(p).read()
if VER not in s:
    old = "        if (pq) { if (++hold_pad_ql == 30) platform_quick_request(2); } else hold_pad_ql = 0;\n"
    assert s.count(old) == 1, "input.c: run patch_keys.py first (or its layout changed)"
    s = s.replace(old, old + "        { extern void lk_qs_play(long frame); lk_qs_play(frame); }   /* LK_QSREC v1: recorded quick save / load of a replay */\n", 1)
    open(p, "w").write(s)
    print("input.c patched:", VER)
