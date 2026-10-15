#!/usr/bin/env python3
"""Test aid: LANDSTALKER_WARP="610:12.08,20.04[,Z]" puts Nigel into a room at a spot, like the game's own cutscene warps do
(CSA_010D: write the room number to g_RmNum1 $FF1204 / $FF1206, the player position to $FF5400.., then WarpToRoom $00620E).
Room and X.sub,Y.sub exactly as the coordinate overlay (R4 / F5) prints them (tile . sub-tile in hex); optional third number Z as the overlay's 'Z xxxx' (hex word,
default: keep the current Z). LANDSTALKER_WARP_AT=frame (default 880, after the load replay prefix of docs/replays/massan.txt): the warp is done the first time the game
loop runs at or after that frame. Several warps: "610:12.08,20.04;603:37.02,36.02" with LANDSTALKER_WARP_AT="880,1500".
Hook: wrapper of the game loop step $001788 (plain function, called once per game loop pass); the original runs afterwards.
Console: `warp: frame F -> room R X x.xx Y y.yy Z zzzz`. No effect without the env var. Idempotent.  usage: patch_warp.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if "LANDSTALKER_WARP" in s:
    print("func_table.c already patched: LANDSTALKER_WARP"); sys.exit(0)
a = "static void lk_strip_extend(uint32_t a);\n"
assert s.count(a) == 1, "func_table.c: layout changed (lk_strip_extend forward declaration)"
module = r'''/* ---- LANDSTALKER_WARP: put Nigel into a room at a spot (tools/patch_warp.py) ---- */
extern long platform_frame_number(void);
extern int lk_wide_refill;
static gen_func_t lk_w_orig;
static int lk_w_n, lk_w_next, lk_w_room[16], lk_w_x[16], lk_w_y[16], lk_w_z[16]; static long lk_w_at[16];
static long lk_refill_at = -1;   /* LANDSTALKER_REFILL_AT=frame: reload the margin / full-height strips once (test: do holes at rest vanish?) */
static void lk_h_warp(void) {
    if (lk_refill_at >= 0 && platform_frame_number() >= lk_refill_at) { lk_refill_at = -1; lk_wide_refill = 1; printf("refill: frame %ld\n", platform_frame_number()); }
    if (lk_w_next < lk_w_n && platform_frame_number() >= lk_w_at[lk_w_next]) {
        int i = lk_w_next++; M68kContext sv = g_m68k;
        bus_write16(0xFF1204u, (uint16_t)lk_w_room[i]); bus_write16(0xFF1206u, (uint16_t)lk_w_room[i]);
        bus_write8(0xFF5400u, (uint8_t)(lk_w_x[i] >> 4)); bus_write8(0xFF5401u, (uint8_t)(lk_w_y[i] >> 4));
        bus_write8(0xFF5402u, (uint8_t)(lk_w_x[i] & 15)); bus_write8(0xFF5403u, (uint8_t)(lk_w_y[i] & 15));
        if (lk_w_z[i] >= 0) bus_write16(0xFF5412u, (uint16_t)lk_w_z[i]);
        printf("warp: frame %ld -> room %d X %d.%02X Y %d.%02X Z %04X\n", platform_frame_number(), lk_w_room[i], lk_w_x[i] >> 4, lk_w_x[i] & 15, lk_w_y[i] >> 4, lk_w_y[i] & 15, bus_read16(0xFF5412u));
        func_table_jsr(0x00620Eu, 0x0016ECu);   /* WarpToRoom: fade out, load, fade in */
        g_m68k = sv;
    }
    lk_w_orig();
}
/* LANDSTALKER_LITHO_AT=frame: shows the lithograph picture the way the game does after 'Found Lithograph.' (CSA_0068 $0136BE: CSA_015A, text $26, DisplayLithograph $03860C, text $27;
   the room transition at its end is left out) from INSIDE UpdateSprites ($0178C8), where cutscene actions run - to test the picture with the widescreen / full-height code without the story trigger */
static gen_func_t lk_l_orig; static long lk_l_at = -1;
static void lk_h_litho(void) {
    if (lk_l_at >= 0 && platform_frame_number() >= lk_l_at) {
        M68kContext sv = g_m68k; lk_l_at = -1;
        printf("litho: frame %ld showing the lithograph picture\n", platform_frame_number());
        func_table_jsr(0x015838u, 0x0178CEu);
        g_m68k.d[0] = 0x26; func_table_jsr(0x012674u, 0x0178CEu);
        bus_write8(0xFF114Bu, 0);
        func_table_jsr(0x03860Cu, 0x0178CEu);
        g_m68k.d[0] = 0x27; func_table_jsr(0x012674u, 0x0178CEu);
        g_m68k = sv;
    }
    lk_l_orig();
}
static void lk_warp_install(void) {
    static int done; const char *e, *at;
    if (done) return;
    done = 1;
    { const char *l = getenv("LANDSTALKER_LITHO_AT"); lk_l_orig = func_table_lookup(0x0178C8);
      if (l && *l && lk_l_orig) { lk_l_at = atol(l); func_table_register(0x0178C8, lk_h_litho); printf("litho: armed at frame %ld\n", lk_l_at); } }
    { const char *r = getenv("LANDSTALKER_REFILL_AT"); if (r && *r && !getenv("LANDSTALKER_WARP")) { lk_refill_at = atol(r); lk_w_orig = func_table_lookup(0x001788); if (lk_w_orig) { func_table_register(0x001788, lk_h_warp); printf("refill: armed at frame %ld\n", lk_refill_at); } return; } else if (r && *r) lk_refill_at = atol(r); }
    e = getenv("LANDSTALKER_WARP");
    if (!e || !*e) return;
    { char buf[512]; char *tok, *sv; long first = 880; snprintf(buf, sizeof(buf), "%s", e);
      at = getenv("LANDSTALKER_WARP_AT"); if (at && *at) first = atol(at);
      for (tok = strtok_r(buf, ";", &sv); tok && lk_w_n < 16; tok = strtok_r(NULL, ";", &sv)) {
          int rm = 0, xt = 0, xs = 0, yt = 0, ys = 0, z = -1; const char *c = strchr(tok, ':');
          if (!c) continue;
          rm = atoi(tok);
          if (sscanf(c + 1, "%d.%x,%d.%x,%x", &xt, &xs, &yt, &ys, &z) >= 4) {
              lk_w_room[lk_w_n] = rm; lk_w_x[lk_w_n] = xt * 16 + (xs & 15); lk_w_y[lk_w_n] = yt * 16 + (ys & 15); lk_w_z[lk_w_n] = z; lk_w_at[lk_w_n] = first; lk_w_n++;
          }
      }
      if (at && *at) { const char *q = at; int k; for (k = 0; k < lk_w_n; k++) { lk_w_at[k] = atol(q); q = strchr(q, ','); if (!q) break; q++; } }
    }
    lk_w_orig = func_table_lookup(0x001788);
    if (lk_w_n && lk_w_orig) { func_table_register(0x001788, lk_h_warp); printf("warp: %d warp(s) armed\n", lk_w_n); }
    else fprintf(stderr, "warp: not armed (bad LANDSTALKER_WARP or $001788 missing)\n");
}
'''
s = s.replace(a, module + a, 1)
h = "        lk_strip_extend(m68k_addr);   /* LANDSTALKER_WIDE_STRIPS */\n"
assert s.count(h) == 1, "func_table.c: strip hook layout changed"
s = s.replace(h, "        lk_warp_install();   /* LANDSTALKER_WARP test aid */\n" + h, 1)
open(p, "w").write(s)
print("func_table.c patched: LANDSTALKER_WARP")
