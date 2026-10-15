#!/usr/bin/env python3
"""Closed-loop navigation for headless tests: LANDSTALKER_GOTO="603:37.02,36.02;603:40.00,30.00" walks Nigel to the waypoints
(room number optional, then X.Y as the coordinate overlay prints them: tile . sub-tile in hex) by reading his position from work RAM every frame
and pressing pad buttons; if he does not move for 12 frames (obstacle) it sidesteps for 40 frames in the next direction and tries again.
The driver works only while the game is in the waypoint's room and from frame LANDSTALKER_GOTO_FROM (default 880, after the load replay prefix).
Console lines: `goto: waypoint N reached at frame F (ROOM R X x.xx Y y.yy)`, `goto: ALL REACHED at frame F`, `goto: giving up at frame F` (LANDSTALKER_GOTO_MAX frames, default 6000).
Pad -> world: UP = (-X,-Y), LEFT = (-X,+Y), RIGHT = (+X,-Y), DOWN = (+X,+Y) (measured 2026-10-11 in room 603; pure axes need two buttons:
-X = UP+LEFT, +X = DOWN+RIGHT, -Y = UP+RIGHT, +Y = DOWN+LEFT). Pad DOWN raises X = screen right-down.
Test aid only (OR-ed into platform_scripted_buttons, no effect without the env var). Idempotent.  usage: patch_goto.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if "LANDSTALKER_GOTO" in s:
    print("platform_sdl.c already patched: LANDSTALKER_GOTO")
    sys.exit(0)
a = "uint16_t platform_scripted_buttons(void) {\n    uint16_t b = 0;\n"
assert s.count(a) == 1, "platform_sdl.c: platform_scripted_buttons layout changed"
code = r'''/* ---- LANDSTALKER_GOTO: closed-loop walk to coordinates (tools/patch_goto.py) ---- */
extern uint8_t *bus_get_ram(void);
static uint16_t lk_goto_buttons(void) {
    static int init, nwp, cur, done, failed; static int wroom[32], wx[32], wy[32];
    static long from = 880, maxf = 6000, lastmove, detour_until; static int lx = -1, ly = -1, detour_n;
    const uint8_t *r = bus_get_ram();
#define LKB(a) (r[((a) & 0xFFFF) ^ 1])
    long f = platform_frame_number();
    int room, fx, fy, dx, dy, sx, sy, k;
    if (!init) {
        const char *e = getenv("LANDSTALKER_GOTO"); init = 1;
        if (e && *e) {
            char buf[1024]; char *tok, *sv; snprintf(buf, sizeof(buf), "%s", e);
            for (tok = strtok_r(buf, ";", &sv); tok && nwp < 32; tok = strtok_r(NULL, ";", &sv)) {
                int rm = -1, xt = 0, xs = 0, yt = 0, ys = 0; const char *c = strchr(tok, ':');
                if (c) { rm = atoi(tok); c++; } else c = tok;
                if (sscanf(c, "%d.%x,%d.%x", &xt, &xs, &yt, &ys) == 4) { wroom[nwp] = rm; wx[nwp] = xt * 16 + xs; wy[nwp] = yt * 16 + ys; nwp++; }
            }
            { const char *v = getenv("LANDSTALKER_GOTO_FROM"); if (v && *v) from = atol(v); v = getenv("LANDSTALKER_GOTO_MAX"); if (v && *v) maxf = atol(v); }
            printf("goto: %d waypoint(s), active from frame %ld\n", nwp, from);
        }
    }
    if (!nwp || done || failed || f < from) return 0;
    if (f > from + maxf) { failed = 1; printf("goto: giving up at frame %ld\n", f); return 0; }
    room = (LKB(0xFF1204) << 8) | LKB(0xFF1205);
    if (wroom[cur] >= 0 && room != wroom[cur]) return 0;
    fx = LKB(0xFF5400) * 16 + (LKB(0xFF5402) & 15); fy = LKB(0xFF5401) * 16 + (LKB(0xFF5403) & 15);
    dx = wx[cur] - fx; dy = wy[cur] - fy;
    if (dx >= -2 && dx <= 2 && dy >= -2 && dy <= 2) {
        printf("goto: waypoint %d reached at frame %ld (ROOM %d X %d.%02X Y %d.%02X)\n", cur, f, room, fx >> 4, fx & 15, fy >> 4, fy & 15);
        if (++cur >= nwp) { done = 1; printf("goto: ALL REACHED at frame %ld\n", f); return 0; }
        lx = -1; return 0;
    }
    if (lx < 0 || f - lastmove >= 12) {   /* progress test: moved at least 3 units (1/16 tile) in the last 12 frames? (1-unit jitter at an obstacle does not count) */
        if (lx >= 0 && f >= detour_until && ((fx - lx) * (fx - lx) + (fy - ly) * (fy - ly)) < 9) { detour_n++; detour_until = f + 40; }
        lx = fx; ly = fy; lastmove = f;
    }
    sx = dx > 2 ? 1 : dx < -2 ? -1 : 0; sy = dy > 2 ? 1 : dy < -2 ? -1 : 0;
    if (f < detour_until) {   /* detour direction: rotate (sx,sy) by 90 degrees (alternately left / right), then reverse */
        static const int rot[4][2] = { { 1, -1 }, { -1, 1 }, { 1, 1 }, { -1, -1 } };
        k = (detour_n - 1) & 3; sx = rot[k][0]; sy = rot[k][1];
    }
    /* world vector -> pad: (-1,-1) UP, (-1,+1) LEFT, (+1,-1) RIGHT, (+1,+1) DOWN, (-1,0) UP+LEFT, (+1,0) DOWN+RIGHT, (0,-1) UP+RIGHT, (0,+1) DOWN+LEFT */
    if (sx < 0 && sy < 0) return 0x1;  if (sx < 0 && sy > 0) return 0x4;  if (sx > 0 && sy < 0) return 0x8;  if (sx > 0 && sy > 0) return 0x2;
    if (sx < 0) return 0x5;  if (sx > 0) return 0xA;  if (sy < 0) return 0x9;  if (sy > 0) return 0x6;
#undef LKB
    return 0;
}

'''
s = s.replace(a, code + a, 1)
b = "    return b;\n}\n\nbool platform_init("
assert s.count(b) == 1, "platform_sdl.c: end of platform_scripted_buttons changed"
s = s.replace(b, "    b |= lk_goto_buttons();   /* LANDSTALKER_GOTO */\n    return b;\n}\n\nbool platform_init(", 1)
open(p, "w").write(s)
print("platform_sdl.c patched: LANDSTALKER_GOTO")
