#!/usr/bin/env python3
"""Debug overlay with Nigel's coordinates (pad R4 = Steam Deck back button / SDL paddle 1, or F5).
Shows room number, tile X/Y (+ sub-tile), height Z and the camera block X/Y of the game, read straight from work RAM (no emulated cycles, the game cannot notice).
Not saved: the overlay is off at every start (debug aid). LANDSTALKER_COORDS=1 switches it on at start,
LANDSTALKER_COORDS_LOG=N prints the same values every N frames to the console (headless tests).
RAM: g_RmNum1 $FF1204 (word), Player $FF5400: X +0, Y +1, sub-tile +2/+3, Z word +$12 ; camera $FF1124/$FF1125.
Idempotent.  usage: patch_coords.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]

# ---- platform.h --------------------------------------------------------------
ph = os.path.join(root, "include/genrecomp/platform.h")
s = open(ph).read()
if "platform_display_toggle_coords" not in s:
    a = "void platform_display_cycle_tall(void);"
    assert a in s, "platform.h: run patch_tall.py first"
    s = s.replace(a, a + "\n/* coordinate debug overlay (pad R4 / paddle 1, F5) */\nvoid platform_display_toggle_coords(void);", 1)
    open(ph, "w").write(s)

# ---- input.c: R4 (SDL paddle 1) ---------------------------------------------
pi = os.path.join(root, "src/input.c")
s = open(pi).read()
if "platform_display_toggle_coords" not in s:
    a = "                rt_prev = rt;\n            }\n"
    assert s.count(a) == 1, "input.c: run patch_tall.py first (R2 block)"
    s = s.replace(a, a + "            { /* coordinate overlay: R4 (Steam Deck back button = SDL paddle 1) */\n                static int p1_prev; int p1 = PB(PADDLE1);\n                if (p1 && !p1_prev) platform_display_toggle_coords();\n                p1_prev = p1;\n            }\n", 1)
    open(pi, "w").write(s)

# ---- platform_sdl.c: overlay text, F5, headless log ---------------------------
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if "platform_display_toggle_coords" not in s:
    b = "static void lk_osd_draw(int ow, int oh) {"
    assert s.count(b) == 1, "platform_sdl.c: osd layout changed"
    s = s.replace(b, r'''/* ---- coordinate debug overlay (tools/patch_coords.py) ---- */
static int lk_coords_on = -1;
extern uint8_t *bus_get_ram(void);
static void lk_coords_text(char *l1, size_t n1, char *l2, size_t n2) {
    const uint8_t *r = bus_get_ram();
#define LKB(a) (r[((a) & 0xFFFF) ^ 1])
    int room = (LKB(0xFF1204) << 8) | LKB(0xFF1205), z = (LKB(0xFF5412) << 8) | LKB(0xFF5413);
    snprintf(l1, n1, "ROOM %d  X %d.%02X  Y %d.%02X", room, LKB(0xFF5400), LKB(0xFF5402), LKB(0xFF5401), LKB(0xFF5403));
    snprintf(l2, n2, "Z %04X  CAM %d/%d", z, LKB(0xFF1124), LKB(0xFF1125));
#undef LKB
}
void platform_display_toggle_coords(void) {
    if (lk_coords_on < 0) lk_coords_on = 0;
    lk_coords_on = !lk_coords_on;
    snprintf(lk_osd_text, sizeof(lk_osd_text), "COORDINATES: %s", lk_coords_on ? "ON" : "OFF"); lk_osd_frames = 100;
}
static void lk_text_box(const char *t, int x, int y, int px) {
    int n = (int)strlen(t);
    SDL_Rect box = { x, y, (n * 6 + 1) * px, 9 * px };
    SDL_SetRenderDrawBlendMode(s_renderer, SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(s_renderer, 0, 0, 0, 190); SDL_RenderFillRect(s_renderer, &box);
    SDL_SetRenderDrawColor(s_renderer, 255, 255, 80, 255);
    for (int i = 0; i < n; i++) {
        const uint8_t *g = lk_glyph(t[i]);
        for (int rr = 0; rr < 7; rr++) for (int c = 0; c < 5; c++)
            if (g[rr] & (0x10 >> c)) { SDL_Rect d = { x + px + (i * 6 + c) * px, y + px + rr * px, px, px }; SDL_RenderFillRect(s_renderer, &d); }
    }
}
static void lk_coords_draw(int oh) {
    char l1[48], l2[48]; int px = oh / 120, m;
    if (lk_coords_on < 0) { const char *e = getenv("LANDSTALKER_COORDS"); lk_coords_on = e && *e && atoi(e) != 0; }
    if (!lk_coords_on) return;
    if (px < 2) px = 2; m = 2 * px;
    lk_coords_text(l1, sizeof(l1), l2, sizeof(l2));
    lk_text_box(l1, m, m + 12 * px, px);
    lk_text_box(l2, m, m + 22 * px, px);
}
''' + b, 1)
    # call after the normal OSD
    c = "    lk_osd_draw(ow, oh);\n"
    assert s.count(c) == 1, "platform_sdl.c: lk_osd_draw call layout changed"
    s = s.replace(c, c + "    lk_coords_draw(oh);\n", 1)
    k = "        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F4) platform_display_cycle_tall();   /* LANDSTALKER_TALL */\n"
    assert s.count(k) == 1, "platform_sdl.c: F4 handler layout changed (run patch_tall.py first)"
    s = s.replace(k, k + "        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F5) platform_display_toggle_coords();   /* coordinate overlay */\n", 1)
    open(p, "w").write(s)
    print("platform_sdl.c / input.c patched: coordinate overlay (R4 / F5)")
else:
    print("platform_sdl.c already patched: coordinate overlay")

# ---- console log for headless tests -----------------------------------------------
s = open(p).read()
if "LANDSTALKER_COORDS_LOG" not in s:
    a = '    { const char *ta = getenv("LANDSTALKER_TALL_AT");'
    assert s.count(a) == 1, "platform_sdl.c: run patch_tall.py first (LANDSTALKER_TALL_AT)"
    s = s.replace(a, '''    { static long every = -1; if (every < 0) { const char *cl = getenv("LANDSTALKER_COORDS_LOG"); every = cl && *cl ? atol(cl) : 0; }   /* LANDSTALKER_COORDS_LOG=N: print the overlay values every N frames */
      if (every > 0 && frame % every == 0) { char l1[48], l2[48]; lk_coords_text(l1, sizeof(l1), l2, sizeof(l2)); printf("coords f%ld: %s | %s\\n", (long)frame, l1, l2); } }
''' + a, 1)
    open(p, "w").write(s)
