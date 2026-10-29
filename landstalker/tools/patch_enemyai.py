#!/usr/bin/env python3
"""Fix: the game hangs in INTRO_141 (2026-10-28, user recordings rec_20261028_2107 / 2123; also in every older build, replays of ~/intro.txt stay in room 141 for good).
Cause (call trace of frame 3152 + the ROM): the three golem statues of room 141 (entity type $8B = SPR_GOLEMSTATUE2) run a behaviour script whose last command is $2B EB_LoadSpecialAI
($018D72: jmp $1A440C -> $1A86D6): that looks the entity's sprite id (+3A & $3FF) up in EnemyTable ($1A8418, 70 ids, $FFFF at the end). $8B is NOT listed, the not-found branch calls OnTick
(j_j_OnTick) for the same entity, whose BehavParam / BehavCmd are unchanged -> the same command again -> endless recursion (the log: '[depth] ABORT: call depth 501 at $1A8ADA'), the room never ends.
How the original gets away with it is not known (the table lookup is translated exactly); this wrapper of $1A440C leaves every listed id to the game and, for an id that is not listed, SKIPS the command
(ProcessNextCmdImmediately_2 $017AC2: LoadNextCmd with 2 + dispatch of the next command, the game's own way to go on with the script).  Idempotent.
usage: patch_enemyai.py path/to/genrecomp   (after patch_carry.py)"""
import os, sys
root = sys.argv[1]
VER = "LK_LSAI v1"
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    h = "        lk_carry_install();   /* LK_CARRY v1 */\n"
    assert s.count(a) == 1 and s.count(h) == 1, "func_table.c: run patch_carry.py first"
    module = r'''/* ---- %s: EB_LoadSpecialAI ($1A440C) for a sprite id that EnemyTable does not list (tools/patch_enemyai.py) ---- */
static gen_func_t lk_o_lsai;
static void lk_h_lsai(void) {
    uint32_t a5 = g_m68k.a[5], p = 0x1A8418u; unsigned id = bus_read16(a5 + 0x3Au) & 0x3FFu; int found = 0, n;
    for (n = 0; n < 200; n++, p += 2) { unsigned v = bus_read16(p); if (v == id) { found = 1; break; } if (v == 0xFFFFu) break; }
    if (found) { lk_o_lsai(); return; }
    { static int said; if (said < 3) { said++; fprintf(stderr, "enemyai: sprite id $%%X is not in EnemyTable: LoadSpecialAI: back to the start script (it would recurse for ever)\n", id); } }
    {   /* back to the entity's own start script (InitBehaviourLUTPtr +72 -> BehaviourLUTPtr +32), first command loaded like at the room load; this tick is over */
        M68kContext sv = g_m68k; uint32_t init = ((uint32_t)bus_read16(a5 + 0x72u) << 16) | bus_read16(a5 + 0x74u);
        bus_write16(a5 + 0x32u, (uint16_t)(init >> 16)); bus_write16(a5 + 0x34u, (uint16_t)init);
        g_m68k.a[5] = a5; g_m68k.d[0] = 0; func_table_jsr(0x017ACAu, 0x0248B2u);   /* LoadNextCmd with d0 = 0 */
        g_m68k = sv;
    }
}
static void lk_lsai_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_lsai = func_table_lookup(0x1A440C);
    if (lk_o_lsai) func_table_register(0x1A440C, lk_h_lsai); else fprintf(stderr, "enemyai: $1A440C not found\n");
}
''' % VER
    s = s.replace(a, module + a, 1)
    s = s.replace(h, h + "        lk_lsai_install();   /* %s */\n" % VER, 1)
    open(p, "w").write(s); print("func_table.c patched:", VER)
