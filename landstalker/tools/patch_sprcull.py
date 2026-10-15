#!/usr/bin/env python3
"""Widescreen: let the game build sprite entries for entities in the margins (NPCs / enemies no longer pop in at the edge).
The game decides per entity in `$004144` (sub_004144, called from LoadSprites -> sub_40F2 for the player and each of the 15 entity slots) whether it
is visible: the screen X of the sprite d2 = (x - y) + $120 (VDP sprite coordinates, screen = $80..$1C0) must lie in [$60, $1E0): only 32 px beyond
the 320 px picture. With margins of e px (LANDSTALKER_WIDE 16/32/48) entities in the margin were not drawn until they crossed that line.
This patch runs on the GENERATED C (src/recomp), after generate.py, and widens the two compares by lk_wide_e:
    lower bound $60 - e,   upper bound $1E0 + e   (no clamp to the 9-bit VDP X: the sprite pieces lie LEFT of the origin d2, so with e = 48 an origin of $200..$20F still shows its left part inside the margin; a clamp at $1F8 made the guard pop in 8 px too late, user report 2026-10-11)
LANDSTALKER_TALL (full-height picture, tools/patch_tall.py) also needs the VERTICAL test widened: the first compare culls an entity when its centre
(x + y) is more than $100 away (half of it in screen px) from the camera centre; the picture used to end 80 px below the centre, the full-height one ends 120 px below it,
so an entity whose centre was past the limit but whose upper body was still in the new bottom band vanished early (user report 2026-10-11: the guard outside the church).
With TALL on the bottom limit grows by $80 (64 px).
With e = 0 and TALL off the generated code behaves exactly as before. Instruction count / cycle charges are unchanged.
Only the sprite builder reads the fields written there (Unk0E/Unk10 of the entity, the sprite attribute table $FF0550); game logic does not.
Known trade-off: more entities may be on screen at once; the sprite tile area ($3A8..$4F4 of VDP RAM) is the game's own budget (16 entities).
Idempotent.  usage: patch_sprcull.py src/recomp"""
import glob, os, sys
d = sys.argv[1]
hit = 0
for p in sorted(glob.glob(os.path.join(d, "*.c"))):
    s = open(p).read()
    i = s.find("void sub_004144(void) {")
    if i < 0:
        continue
    j = s.find("\n}\n", i)
    body = s[i:j]
    if "lk_wide_e" in body:
        print("sprcull: %s already patched" % os.path.basename(p)); hit = 1; continue
    a = "    M68K_CMP16(g_m68k.d[2], 0x60);\n"
    b = "    M68K_CMP16(g_m68k.d[2], 0x1e0);\n"
    v = "    M68K_CMP16(g_m68k.d[0], g_m68k.d[5]);\n"
    assert body.count(a) == 1 and body.count(b) == 1 and body.count(v) == 1, "sub_004144: generated code layout changed"
    k = body.index(v)   # the d0/d5 compare is the vertical (x + y) test
    body = body[:k] + "    { extern int lk_tall_kv(void) __attribute__((weak)); M68K_CMP16(g_m68k.d[0], (uint16_t)g_m68k.d[5] + ((lk_tall_kv && lk_tall_kv() > 0) ? 0x80 : 0)); }   /* LANDSTALKER_TALL: entities in the bottom band (tools/patch_sprcull.py) */\n" + body[k + len(v):]
    body = body.replace(a, "    { extern int lk_wide_e; M68K_CMP16(g_m68k.d[2], 0x60 - lk_wide_e); }   /* LANDSTALKER_WIDE: margin entities (tools/patch_sprcull.py) */\n", 1)
    body = body.replace(b, "    { extern int lk_wide_e; M68K_CMP16(g_m68k.d[2], 0x1e0 + lk_wide_e); }   /* LANDSTALKER_WIDE: margin entities */\n", 1)
    open(p, "w").write(s[:i] + body + s[j:])
    print("sprcull: patched sub_004144 in %s" % os.path.basename(p)); hit = 1
assert hit, "sprcull: sub_004144 not found in generated code (is the function seeded?)"
