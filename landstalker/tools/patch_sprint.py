#!/usr/bin/env python3
"""Sprint (2026-10-30, user: 'Sprint umsetzen, Standard auf R2'; idea docs/SPRINT_IDEAS.md).  Hold the binding 'Sprint' (pad R2, keyboard Left Shift;
Options > Keybindings; Options > Quality of Life > Sprint On / Off, default On) and Nigel walks 2 x as fast (even step = smooth scrolling).
How: HandleDirectionalInput $0018C4 sets the step g_ScrollStep $FF1182 to 2 every frame (8 in the debug mode) and ends with a jump through
HandleDirectionalControl $001936 (32 x bra.w, index = d-pad nibble + confusion bit) into the move handlers, which add the step to the hit box,
test collisions only when a cell boundary (bit 3) is crossed and scroll the camera by the same step (the debug mode proves steps up to 8 work).
This patch wraps those 32 table entries (func_table_tail goes through the function table): while Sprint is held and the step is the normal 2,
it becomes the sprint step (4 = 2 x; LANDSTALKER_SPRINT_STEP) for this frame, unless a script plays Nigel (g_PlaybackLock $FF12DE), he is in the air (Player action byte $FF542D
bits 4 fall / 5 jump, JumpRate $FF5421: the jump length stays EXACTLY the original, user decision 2026-10-29), on a ladder or swinging the sword
(action byte $FF542C bits 0..4).  When the last sprint step did not get through (Player X / Y words $FF5414 / $FF5416 moved less than the step:
a wall, a figure, an item that blocks with the whole step taken back), this frame uses the normal step, so Nigel gets as close as in the original
(the gold bag could not be picked up while sprinting, user 2026-10-30).  Without the button nothing changes (bit exact).
Recordings: every press / release is logged next to the quick save events ('p<frame>' / 'r<frame>' in LANDSTALKER_QSLOG, so the recording script
puts them into LANDSTALKER_QSPLAY); while an input script is replayed (GENRECOMP_INPUTSCRIPT) only those events count, never a live button.
An odd step is applied as step+1 / step-1 on alternate frames (3 = 4, 2, 4, 2 ...): the vertical scroll moves by half the step, odd steps made the figures jitter.
Test aid: LANDSTALKER_SPRINTHOLD=a-b holds Sprint from frame a to b; LANDSTALKER_SPRINT_STEP=n (2..8) changes the step.
Needs patch_keys.py (LK_BSPRINT binding), patch_qsrec.py and patch_equip.py before it.  Idempotent.  usage: patch_sprint.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_SPRINT v1"

# ---- input.c: the live button state goes to the platform side once per input poll ----
p = os.path.join(root, "src/input.c")
s = open(p).read()
if VER not in s:
    a = "        dpad[i] = pd; d[i] = kd || pd; any |= d[i];\n    }\n"
    assert s.count(a) == 1, "input.c: run patch_keys.py first (or its layout changed)"
    s = s.replace(a, a + "    { extern void lk_sprint_poll(long frame, int live); lk_sprint_poll(frame, d[LK_BSPRINT]); }   /* LK_SPRINT v1 */\n", 1)
    open(p, "w").write(s)
    print("input.c patched:", VER)

# ---- platform_sdl.c: state, recording / replay of the presses ----
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    old = "    if (f) { fprintf(f, \"%c%ld\\n\", what == 1 ? 's' : 'l', s_frame_no); fflush(f); }\n"
    assert s.count(old) == 1, "platform_sdl.c: run patch_qsrec.py first (or its layout changed)"
    s = s.replace(old, "    if (f) { fprintf(f, \"%c%ld\\n\", what == 1 ? 's' : what == 2 ? 'l' : what == 3 ? 'p' : 'r', s_frame_no); fflush(f); }   /* 3 / 4 = Sprint pressed / released (LK_SPRINT v1) */\n", 1)
    a = "void lk_qs_play(long frame) {"
    assert s.count(a) == 1
    module = r'''/* ---- LK_SPRINT v1: Sprint button state (tools/patch_sprint.py) ---- */
static int lk_sprint_v;
int lk_sprint_held(void) { return lk_sprint_v; }
static int lk_sprint_o = -1;   /* Options > Quality of Life > Sprint (id 42), default On; ~/.landstalker_sprint, env LANDSTALKER_SPRINT=0|1 wins */
int lk_sprint_opt_get(void) { if (lk_sprint_o < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_SPRINT"); char p[512]; FILE *f; int v = 1; snprintf(p, sizeof p, "%s/.landstalker_sprint", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 1; fclose(f); } if (e && *e) v = atoi(e); lk_sprint_o = v ? 1 : 0; } return lk_sprint_o; }
void lk_sprint_opt_set(int v) { const char *h = getenv("HOME"); char p[512]; FILE *f; lk_sprint_opt_get(); lk_sprint_o = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_sprint", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_sprint_o); fclose(f); } }
static void lk_qs_rec(int what);
void lk_sprint_poll(long frame, int live) {
    static int init, replay, n, prev, pos, cur; static long *ev; static char *evk; static long h0 = -1, h1 = -1;
    if (!init) { const char *e = getenv("LANDSTALKER_QSPLAY"), *h = getenv("LANDSTALKER_SPRINTHOLD"); init = 1; replay = getenv("GENRECOMP_INPUTSCRIPT") != NULL;
        if (e) { size_t cap = strlen(e) / 2 + 1; const char *q; ev = (long *)malloc(cap * sizeof *ev); evk = (char *)malloc(cap); for (q = e; *q && ev && evk; q++) if ((*q == 'p' || *q == 'r') && (q == e || q[-1] == ',') && (size_t)n < cap) { evk[n] = *q; ev[n] = atol(q + 1); n++; } }
        if (h && sscanf(h, "%ld-%ld", &h0, &h1) != 2) h0 = h1 = -1; }
    if (replay) { while (pos < n && ev[pos] <= frame) { cur = evk[pos] == 'p'; pos++; } live = cur; }   /* replays: only the recorded presses (events in frame order) */
    if (frame >= h0 && frame <= h1) live = 1;
    live = live ? 1 : 0;
    if (live != prev && !replay) lk_qs_rec(live ? 3 : 4);
    if (live && !prev && !lk_sprint_opt_get()) { snprintf(lk_osd_text, sizeof lk_osd_text, "%s", lk_lang_tr("SPRINT OFF - SEE OPTIONS")); lk_osd_frames = 150; }   /* a press while the option is Off says so, like Quick Save (user 2026-10-30) */
    prev = live; lk_sprint_v = live && lk_sprint_opt_get();   /* the option off = the button does nothing (the press is still recorded) */
}
'''
    s = s.replace(a, module + a, 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

# ---- func_table.c: the 32 entries of HandleDirectionalControl ----
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1
    module = r'''/* ---- LK_SPRINT v1: sprint step (tools/patch_sprint.py) ---- */
extern int lk_sprint_held(void);
static gen_func_t lk_o_dir[32];
static long lk_sprint_frame = -10;
int lk_sprint_active(void) { return platform_frame_number() - lk_sprint_frame <= 1; }   /* the step was raised in this (or the last) frame: the own renderer shows the sprint pose (tools/patch_sprintanim.py) */
static int lk_sprint_alt = 1;   /* LANDSTALKER_SPRINT_ALT=0: an odd step stays odd (test aid) */
static int lk_sprint_step = 4;   /* 2 x the walk: in the 2:1 view only EVEN steps scroll smoothly (vertical = half the step); 1.5 x wobbled, user chose 2 x (2026-10-30) */
static void lk_sprint_dir(int k) {
    static int lstep; static uint16_t lx, ly; uint16_t cx = bus_read16(0xFF5414u), cy = bus_read16(0xFF5416u); int moved, blocked;
    moved = abs((int16_t)(cx - lx)) + abs((int16_t)(cy - ly)); blocked = lstep > 2 && moved < lstep;   /* the last sprint step did not get through (wall, figure, item): */
    lx = cx; ly = cy; lstep = 0;                                                                            /* this frame the normal step, so Nigel gets as close as in the original (pick up the gold bag, talk; user 2026-10-30) */
    if (!blocked && lk_sprint_held() && bus_read16(0xFF1182u) == 2 && bus_read16(0xFF12DEu) == 0 && !(bus_read8(0xFF542Du) & 0x30) && !(bus_read8(0xFF542Cu) & 0x1F) && bus_read8(0xFF5421u) == 0)
        { static int alt; int st = lk_sprint_step; if ((st & 1) && lk_sprint_alt) { st += alt ? 1 : -1; alt ^= 1; }   /* an odd step (3 = 1.5 x) alternates step+1 / step-1 (4 / 2): the camera moves vertically by HALF the step, an odd step made the figures jitter 1 px against the room (user 2026-10-30) */
          bus_write16(0xFF1182u, (uint16_t)st); lk_sprint_frame = platform_frame_number(); lstep = st; }
    lk_o_dir[k]();
}
#define LK_SPD(k) static void lk_h_dir##k(void) { lk_sprint_dir(k); }
LK_SPD(0) LK_SPD(1) LK_SPD(2) LK_SPD(3) LK_SPD(4) LK_SPD(5) LK_SPD(6) LK_SPD(7) LK_SPD(8) LK_SPD(9) LK_SPD(10) LK_SPD(11) LK_SPD(12) LK_SPD(13) LK_SPD(14) LK_SPD(15)
LK_SPD(16) LK_SPD(17) LK_SPD(18) LK_SPD(19) LK_SPD(20) LK_SPD(21) LK_SPD(22) LK_SPD(23) LK_SPD(24) LK_SPD(25) LK_SPD(26) LK_SPD(27) LK_SPD(28) LK_SPD(29) LK_SPD(30) LK_SPD(31)
static void lk_sprint_install(void) {
    static gen_func_t h[32] = { lk_h_dir0, lk_h_dir1, lk_h_dir2, lk_h_dir3, lk_h_dir4, lk_h_dir5, lk_h_dir6, lk_h_dir7, lk_h_dir8, lk_h_dir9, lk_h_dir10, lk_h_dir11, lk_h_dir12, lk_h_dir13, lk_h_dir14, lk_h_dir15,
        lk_h_dir16, lk_h_dir17, lk_h_dir18, lk_h_dir19, lk_h_dir20, lk_h_dir21, lk_h_dir22, lk_h_dir23, lk_h_dir24, lk_h_dir25, lk_h_dir26, lk_h_dir27, lk_h_dir28, lk_h_dir29, lk_h_dir30, lk_h_dir31 };
    static int done; int k, miss = 0; const char *e = getenv("LANDSTALKER_SPRINT_STEP");
    if (done) return;
    done = 1;
    if (e && atoi(e) >= 2 && atoi(e) <= 8) lk_sprint_step = atoi(e);
    { const char *e2 = getenv("LANDSTALKER_SPRINT_ALT"); if (e2 && *e2) lk_sprint_alt = atoi(e2) != 0; }
    for (k = 0; k < 32; k++) { lk_o_dir[k] = func_table_lookup(0x001936u + 4u * (uint32_t)k); if (lk_o_dir[k]) func_table_register(0x001936u + 4u * (uint32_t)k, h[k]); else miss++; }
    if (miss) fprintf(stderr, "sprint: %d of the 32 HandleDirectionalControl entries not found\n", miss);
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_eq_install();   /* LK_EQUIP v1 */\n"
    assert s.count(h) == 1, "func_table.c: run patch_equip.py first"
    s = s.replace(h, h + "        lk_sprint_install();   /* LK_SPRINT v1 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
