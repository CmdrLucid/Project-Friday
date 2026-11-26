#!/usr/bin/env python3
"""Jump / landing sound on / off (2026-11-26, YouTube comment by a player: 'an option to remove the jumping sound effect';
user: 'nur der Sprung-Sound, ggf. optional auch den Lande-Sound').
The game plays its sounds with `trap #0` + an inline sound word (Trap00Handler):
  * JUMP:    HandleJump $003F92 (player only) -> trap at $003FCA, word SND_Jump $53 at $003FCC (symbol HandleJump_JumpSoundId)
  * LANDING: CheckForLadderClimb $002178 (GameLoop+$1C) -> trap at $0021A0, word $5E at $0021A2 (symbol CheckForLadderClimb_LandSoundId),
    played when Player_Unk2F bit 4 is set = the frame Nigel touches the ground after a jump or fall (sound trace: every jump $53 is
    followed by $5E 20 frames later). The disassembly calls $5E 'SND_LadderClimb' and $5D 'SND_JumpLand', but $5D (traps $001B00 /
    $002020 in HandleDirectionalControl, every 4th frame, and CheckPickUpEntity) never follows a jump; those are NOT touched.
With an option Off the generated C skips only that TRAP (like tools/patch_talk.py for the speech blips); everything else runs as before.
On (default) = the trap runs = bit exact.
Option rows: Options > Audio > Jump Sound (id 65), Landing Sound (id 66); ~/.landstalker_jumpsnd ("jump landing", 0|1 each, default "1 1"),
env LANDSTALKER_JUMPSND=0|1 / LANDSTALKER_LANDSND=0|1 win.
Two steps (build.sh):
  patch_jumpsnd.py menu .deps/genrecomp   option storage + menu rows (after patch_altpad.py: ids 65 / 66 follow its id 64)
  patch_jumpsnd.py gen src/recomp         the trap guards in the GENERATED C (before tools/rename_generated.py, like patch_talk.py)
Idempotent."""
import glob, os, re, sys
VER = "LK_JUMPSND v1"
mode, root = sys.argv[1], sys.argv[2]


def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed: " + old[:90]
    return s.replace(old, new, 1)


if mode == "gen":
    # pc value after the trap (= address of the inline sound word) -> which option guards it
    guards = {"0x003FCC": 0, "0x0021A2": 1}
    hits = {k: 0 for k in guards}
    for p in sorted(glob.glob(os.path.join(root, "*.c"))):
        s = open(p).read(); n = s
        for pc, w in guards.items():
            a = "    g_m68k.pc = %s; recomp_m68k_exception(32 + 0x0); /* TRAP #0x0 */\n" % pc
            b = "    { extern int lk_jsnd_on(int); if (lk_jsnd_on(%d)) {   /* %s: %s sound option */\n    %s\n    } }\n" % (w, VER, "jump" if w == 0 else "landing", a.strip("\n"))
            n = n.replace(a, b)
            hits[pc] += n.count(b)   # guarded now (this run or an earlier one)
        if n != s:
            open(p, "w").write(n); print("jumpsnd: patched %s" % os.path.basename(p))
    for pc, c in hits.items():
        assert c, "jumpsnd: trap with pc %s not found (generated layout changed)" % pc
    print("jumpsnd: generated C ok (" + ", ".join("%s" % k for k in hits) + ")")
    sys.exit(0)

assert mode == "menu", "usage: patch_jumpsnd.py menu .deps/genrecomp | gen src/recomp"
# ---- func_table.c: option storage + the menu rows -----------------------------------------------------------------------
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
else:
    assert "LK_ALTPAD v1" in s, "func_table.c: run patch_altpad.py first (id 64)"
    module = r'''/* ---- ''' + VER + r''': jump / landing sound on / off (tools/patch_jumpsnd.py) ---- */
#include <stdio.h>
#include <stdlib.h>
static int lk_jsnd_o[2] = { -1, -1 };
static void lk_jsnd_load(void) {   /* ~/.landstalker_jumpsnd "jump landing"; env LANDSTALKER_JUMPSND / LANDSTALKER_LANDSND win; default 1 1 = original */
    const char *h = getenv("HOME"), *e; char pth[512]; FILE *f; int a = 1, b = 1;
    if (lk_jsnd_o[0] >= 0) return;
    snprintf(pth, sizeof pth, "%s/.landstalker_jumpsnd", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%d %d", &a, &b) != 2) a = b = 1; fclose(f); }
    if ((e = getenv("LANDSTALKER_JUMPSND")) && *e) a = atoi(e);
    if ((e = getenv("LANDSTALKER_LANDSND")) && *e) b = atoi(e);
    lk_jsnd_o[0] = a ? 1 : 0; lk_jsnd_o[1] = b ? 1 : 0; }
int lk_jsnd_on(int w) { lk_jsnd_load(); return lk_jsnd_o[w & 1]; }   /* called by the guarded traps in the generated C */
void lk_jsnd_step(int w) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_jsnd_load(); lk_jsnd_o[w & 1] = !lk_jsnd_o[w & 1];
    snprintf(pth, sizeof pth, "%s/.landstalker_jumpsnd", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%d %d\n", lk_jsnd_o[0], lk_jsnd_o[1]); fclose(f); } }
'''
    a = "void func_table_init(void) {"
    s = rep(s, a, module + a, "func_table.c init")
    s = rep(s, "static const char *lk_id_name[65] = {", "static const char *lk_id_name[67] = {", "func_table.c lk_id_name size")
    s = rep(s, '"Bath Scene", "D-Pad" };', '"Bath Scene", "D-Pad", "Jump Sound", "Landing Sound" };   /* 65, 66: ' + VER + ' */', "func_table.c lk_id_name")
    s = rep(s, 'case 64: return "Up/Down/Left/Right go diagonally";',
            'case 64: return "Up/Down/Left/Right go diagonally"; case 65: return "Nigel\'s sound when he jumps"; case 66: return "Nigel\'s sound when he lands";',
            "func_table.c help")
    s = rep(s, "static const int lk_ids_audio[3] = { 6, 7, 8 };",
            "static const int lk_ids_audio[5] = { 6, 7, 8, 65, 66 };   /* " + VER + ": + Jump Sound, Landing Sound */", "func_table.c lk_ids_audio")
    s = rep(s, "= { 9, 7, 12, 3, 6, 8, 3, 20, 4 };", "= { 9, 7, 12, 5, 6, 8, 3, 20, 4 };   /* " + VER + ": Audio + 2 rows */", "func_table.c lk_pg_cnt")
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)

# ---- platform_sdl.c: option ids 65 / 66 in platform_option_get / platform_option_step ----------------------------------
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched: " + VER)
else:
    a = "extern int lk_altpad_get(void); extern void lk_altpad_step(void);"
    s = rep(s, a, a + " extern int lk_jsnd_on(int); extern void lk_jsnd_step(int);   /* " + VER + " */", "platform_sdl.c extern")
    s = rep(s, "case 64: return lk_altpad_get();", "case 64: return lk_altpad_get(); case 65: return lk_jsnd_on(0); case 66: return lk_jsnd_on(1);", "platform_sdl.c get")
    s = rep(s, "case 64: lk_altpad_step(); break;", "case 64: lk_altpad_step(); break; case 65: lk_jsnd_step(0); break; case 66: lk_jsnd_step(1); break;", "platform_sdl.c step")
    open(p, "w").write(s)
    print("platform_sdl.c patched: " + VER)
