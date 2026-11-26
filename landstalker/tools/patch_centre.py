#!/usr/bin/env python3
"""Nigel centred with Full Height (2026-11-26, YouTube comment 'Can we get Nigel's sprite centered? It feels weird with him so high up there';
user: 'j schau dir das an').

Why he is high: the game centres the player in ITS map picture (lines 0..~184; HInt switches the display off below); Full Height
(tools/patch_tall.py) fills the 40 lines BELOW, so in the 224-line picture his body sits ~24 px above the centre.
How: the game's camera g_CameraPixelX/Y $FF1200/$FF1202 (+ g_CameraBlockX/Y $FF1124/25 = word >> 4, sub-block bytes $FF1126/27 = word & 15)
is computed from the player ONLY in CalcPlayerFlattenedCoords $002DCE (room load: camera = player centre - Player_Z $FF5412); every move /
jump afterwards changes camera and player by the same step (FORMATS 'CAMERA = PLAYER').  A wrapper of $002DCE adds D to Player_Z for that
one call: the camera starts D units (both iso axes) lower = everything is drawn D screen px LOWER, and the game keeps the offset by itself
(strip loading, scroll registers, sprite positions are all camera relative).  The map strips the game loads cover its own picture; the
extra strips of lk_strip_extend (tools/patch_wide.py) then need more steps at the TOP and fewer at the bottom (patched here).
Switching without a room change: InitVDP $008EA0 (run when the Start menu closes: LoadRoom + InitVDPAndFadeIn, also after shops / some
dialogue actions) rebuilds scroll registers + all blocks from the camera; a wrapper moves the camera words / blocks / sub bytes by the
difference first.  (Full Height switched by key during play: the offset changes at the next room load / menu close.)
Option: Options > Display > Centered View (id 67, ~/.landstalker_centre 0|1, default Off = the original camera = bit exact; only with Full
Height on).  Env: LANDSTALKER_CENTRE=0|1 or D (screen px > 1, even), LANDSTALKER_CENTRE_TOP / _BOT = extra strip steps (default 5 / 2),
LANDSTALKER_CENTRE_DEBUG=1 prints every camera change, LANDSTALKER_CENTRE_AT=frame flips the option once (test aid; the camera follows at the next rebuild).
Measured (2026-11-26, ~/Project-Friday-Test/lktest/nigelmitte): D = 24 puts Nigel's body on line ~110 of 224; 20000 frames of a user
recording (16:9, several rooms / dungeon) without holes at the top; game state the same apart from tiny timing jitter; GPU light and sword
glow move with the picture.
Needs patch_wide.py (lk_strip_extend), patch_tall.py, patch_altpad.py + patch_jumpsnd.py (ids / install anchor).  Idempotent.
usage: patch_centre.py .deps/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_CENTRE v1"


def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed: " + old[:90]
    return s.replace(old, new, 1)


p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER in s:
    print("func_table.c already patched: " + VER)
    s = None
if s is not None:
    module = r'''/* ---- ''' + VER + r''': Nigel centred with Full Height (tools/patch_centre.py) ---- */
#include <stdio.h>
#include <stdlib.h>
extern int lk_tall_kv(void) __attribute__((weak));
static int lk_ctr_d = -1, lk_ctr_t = -1, lk_ctr_b = -1, lk_ctr_opt = -1;
static void lk_ctr_load(void) { const char *e, *h; char pth[512]; FILE *f; int v = 0; if (lk_ctr_d >= 0) return;
    h = getenv("HOME"); snprintf(pth, sizeof pth, "%s/.landstalker_centre", h ? h : "."); f = fopen(pth, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); }
    lk_ctr_d = 24; e = getenv("LANDSTALKER_CENTRE"); if (e && *e) { v = atoi(e); if (v > 1) { lk_ctr_d = v & ~1; if (lk_ctr_d > 48) lk_ctr_d = 48; } }
    lk_ctr_opt = v ? 1 : 0;
    e = getenv("LANDSTALKER_CENTRE_TOP"); lk_ctr_t = e && *e ? atoi(e) : 5;
    e = getenv("LANDSTALKER_CENTRE_BOT"); lk_ctr_b = e && *e ? atoi(e) : 2; }
int lk_ctr_get(void) { lk_ctr_load(); return lk_ctr_opt; }   /* Options > Display > Centered View (id 67) */
void lk_ctr_step(void) { const char *h = getenv("HOME"); char pth[512]; FILE *f; lk_ctr_load(); lk_ctr_opt = !lk_ctr_opt;
    snprintf(pth, sizeof pth, "%s/.landstalker_centre", h ? h : "."); f = fopen(pth, "w"); if (f) { fprintf(f, "%d\n", lk_ctr_opt); fclose(f); } }
static int lk_ctr_want(void) {
    { static long at = -2; if (at == -2) { const char *e = getenv("LANDSTALKER_CENTRE_AT"); at = e && *e ? atol(e) : -1; }   /* test aid: flip the option once at that frame */
      if (at >= 0 && platform_frame_number() >= at) { at = -1; lk_ctr_load(); lk_ctr_opt = !lk_ctr_opt; printf("centre: option flipped to %d at frame %ld (test aid)\n", lk_ctr_opt, platform_frame_number()); } }
    lk_ctr_load(); return lk_ctr_opt && lk_tall_kv && lk_tall_kv() > 0 ? lk_ctr_d : 0; }   /* the camera offset the next rebuild should have */
static int lk_ctr_cur;   /* the offset the camera has now (the game keeps it until the next load / rebuild) */
int lk_ctr_top(void) { return lk_ctr_cur ? lk_ctr_t : 0; }   /* extra strip steps above the picture (lk_strip_extend) */
int lk_ctr_bot(int kv) { return lk_ctr_cur ? lk_ctr_b : kv; }   /* extra strip steps below */
static gen_func_t lk_ctr_o_cpf, lk_ctr_o_ivdp;
static void lk_ctr_h_cpf(void) {   /* CalcPlayerFlattenedCoords $002DCE: camera = player - Z; with the offset: - (Z + D) */
    uint16_t z = bus_read16(0xFF5412u);
    lk_ctr_cur = lk_ctr_want();
    if (!lk_ctr_cur) { lk_ctr_o_cpf(); return; }
    bus_write16(0xFF5412u, (uint16_t)(z + lk_ctr_cur)); lk_ctr_o_cpf(); bus_write16(0xFF5412u, z);
    if (getenv("LANDSTALKER_CENTRE_DEBUG")) printf("centre: room load, camera offset %d (cam %d,%d) frame %ld\n", lk_ctr_cur, (int16_t)bus_read16(0xFF1200u), (int16_t)bus_read16(0xFF1202u), platform_frame_number());
}
static void lk_ctr_h_ivdp(void) {   /* InitVDP $008EA0 (menu close, shops, ...): rebuilds scroll + blocks from the camera -> move the camera to the wanted offset first */
    int w = lk_ctr_want(), dlt = w - lk_ctr_cur, ax;
    if (dlt) {
        for (ax = 0; ax < 2; ax++) {   /* the same split as CalcPlayerFlattenedCoords: word, sub = word & 15, block = word >> 4 */
            int16_t c = (int16_t)(bus_read16(0xFF1200u + 2u * ax) - dlt);
            bus_write16(0xFF1200u + 2u * ax, (uint16_t)c); bus_write8(0xFF1126u + ax, (uint8_t)(c & 15)); bus_write8(0xFF1124u + ax, (uint8_t)(c >> 4));
        }
        if (getenv("LANDSTALKER_CENTRE_DEBUG")) printf("centre: rebuild, camera offset %d -> %d frame %ld\n", lk_ctr_cur, w, platform_frame_number());
        lk_ctr_cur = w;
    }
    lk_ctr_o_ivdp();
}
static void lk_ctr_install(void) { static int done; if (done) return; done = 1;
    lk_ctr_o_cpf = func_table_lookup(0x002DCEu);
    if (lk_ctr_o_cpf) func_table_register(0x002DCEu, lk_ctr_h_cpf); else fprintf(stderr, "centre: CalcPlayerFlattenedCoords not found\n");
    lk_ctr_o_ivdp = func_table_lookup(0x008EA0u);
    if (lk_ctr_o_ivdp) func_table_register(0x008EA0u, lk_ctr_h_ivdp); else fprintf(stderr, "centre: InitVDP not found\n"); }
'''
    a = "void func_table_init(void) {"
    s = rep(s, a, module + a, "func_table.c init")
    h = "        lk_altpad_install();   /* LK_ALTPAD v1 */\n"
    s = rep(s, h, h + "        lk_ctr_install();   /* " + VER + " */\n", "func_table.c install hook")
    # lk_strip_extend: bottom steps from lk_ctr_bot, top steps (top edge pushed up, left / right strips shifted up by (-j,-j)) from lk_ctr_top
    s = rep(s, "static void lk_strip_extend(uint32_t a);\nstatic int32_t lk_blk_delta;",
            "static void lk_strip_extend(uint32_t a);\nint lk_ctr_top(void); int lk_ctr_bot(int kv);   /* " + VER + " */\nstatic int32_t lk_blk_delta;", "func_table.c ctr decl")
    old = "        if (a == 0x00A698) { for (j = k + 1; j <= kv && ns < 30; j++) for (v = 0; v < 2; v++) { sx[ns] = dx[v] * j; sy[ns] = dy[v] * j; ns++; } }\n" \
          "        else if (a == 0x00A6B0 || a == 0x00A730) for (j = 1; j <= (kv + 1) / 2; j++) {\n" \
          "            if (ns < 31) { sx[ns] = j; sy[ns] = j; ns++; }\n" \
          "            for (m = 0; m < n0 && ns < 31; m++) { sx[ns] = sx[m] + j; sy[ns] = sy[m] + j; ns++; }\n" \
          "        }\n"
    new = "        int kb = lk_ctr_bot(kv), kt = lk_ctr_top();   /* " + VER + ": centred camera = fewer steps below, some above */\n" \
          "        if (a == 0x00A698) { for (j = k + 1; j <= kb && ns < 30; j++) for (v = 0; v < 2; v++) { sx[ns] = dx[v] * j; sy[ns] = dy[v] * j; ns++; } }\n" \
          "        else if (a == 0x00A61C) { for (j = k + 1; j <= kt && ns < 30; j++) for (v = 0; v < 2; v++) { sx[ns] = dx[v] * j; sy[ns] = dy[v] * j; ns++; } }\n" \
          "        else if (a == 0x00A6B0 || a == 0x00A730) { for (j = 1; j <= (kb + 1) / 2; j++) {\n" \
          "            if (ns < 31) { sx[ns] = j; sy[ns] = j; ns++; }\n" \
          "            for (m = 0; m < n0 && ns < 31; m++) { sx[ns] = sx[m] + j; sy[ns] = sy[m] + j; ns++; }\n" \
          "        }\n" \
          "          for (j = 1; j <= (kt + 1) / 2; j++) {\n" \
          "            if (ns < 31) { sx[ns] = -j; sy[ns] = -j; ns++; }\n" \
          "            for (m = 0; m < n0 && ns < 31; m++) { sx[ns] = sx[m] - j; sy[ns] = sy[m] - j; ns++; }\n" \
          "        } }\n"
    s = rep(s, old, new, "func_table.c lk_strip_extend tall steps")
    # options menu: Display page row after Full Height
    s = rep(s, "static const char *lk_id_name[67] = {", "static const char *lk_id_name[68] = {", "func_table.c lk_id_name size")
    s = rep(s, '"Jump Sound", "Landing Sound" };', '"Jump Sound", "Landing Sound", "Centered View" };   /* 67: ' + VER + ' */', "func_table.c lk_id_name")
    s = rep(s, 'case 66: return "Sound when landing";', 'case 66: return "Sound when landing"; case 67: return "Full Height: hero in the middle";', "func_table.c help")
    s = rep(s, "static const int lk_ids_video[7] = { 0, 1, 4, 2, 5, 55, 3 };", "static const int lk_ids_video[8] = { 0, 1, 67, 4, 2, 5, 55, 3 };   /* " + VER + ": + Centered View */", "func_table.c lk_ids_video")
    s = rep(s, "= { 9, 7, 12, 5, 6, 8, 3, 20, 4 };", "= { 9, 8, 12, 5, 6, 8, 3, 20, 4 };   /* " + VER + ": Display + Centered View */", "func_table.c lk_pg_cnt")
    new2 = new.replace("ns < 30", "ns < 62").replace("ns < 31", "ns < 63")
    s = s.replace(new, new2, 1)
    s = rep(s, "sx[32], sy[32], kv = lk_tall_kv", "sx[64], sy[64], kv = lk_tall_kv", "func_table.c strip arrays")   # more steps fit (16:9 + top + bottom)
    open(p, "w").write(s)
    print("func_table.c patched: " + VER)

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched: " + VER)
else:
    a = "extern int lk_jsnd_on(int); extern void lk_jsnd_step(int);"
    s = rep(s, a, a + " extern int lk_ctr_get(void); extern void lk_ctr_step(void);   /* " + VER + " */", "platform_sdl.c extern")
    s = rep(s, "case 66: return lk_jsnd_on(1);", "case 66: return lk_jsnd_on(1); case 67: return lk_ctr_get();", "platform_sdl.c get")
    s = rep(s, "case 66: lk_jsnd_step(1); break;", "case 66: lk_jsnd_step(1); break; case 67: lk_ctr_step(); break;", "platform_sdl.c step")
    open(p, "w").write(s)
    print("platform_sdl.c patched: " + VER)
