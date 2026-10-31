#!/usr/bin/env python3
"""Room map (2026-10-31, user wish 'eigene Raumkarte, nur Standort', MODERN_IDEAS (B), docs/MAP.md): the binding 'Map' (pad L4 = PADDLE2, keyboard M; Options > Keybindings)
opens a full-resolution map of the current AREA over the paused game: one cell per room on a 2:1 grid (schematic, tools/roommap.py), each cell shows the room drawn from
the ROM, bars = passages, triangles = stairs up / down, the current room has a golden frame and a blinking dot for Nigel.  Only rooms the game marked as visited
(its own flags `$FF10C0`, SetRoomVisited `$00293C`, bit per room from `RoomVisitedFlagLookup $00C74E`) and the current room are shown.  One floor at a time:
D-pad / stick up and down (or L / R) change the floor; B, Start, Esc or the Map binding close it.
v2 (user 2026-10-31: v1 hung on the Deck, could not close; 'Mercator zu durcheinander, nur Dungeon-Karten'): controller EVENTS are off (LK_PADTHREAD), so the loop polls
lk_map_pad() (input.c: the pad thread's copy, kicks the worker every pass) instead of waiting for SDL controller events; outside a dungeon the button shows 'NO MAP HERE' for a moment.  While it is open the game is paused completely (like the focus pause:
emulation waits in platform_poll_events, audio paused, the frame timer restarts afterwards) and it waits until every button is released before the game continues.
Data: <exe dir>/roommap/layout.txt + thumbs.bin (built from the player's ROM by tools/roommap.py in build.sh / firstrun.py); LANDSTALKER_MAPDIR overrides.  No data or not in a
map room = the button does nothing.  Picture only: the game state is untouched (Off = bit exact by construction).
Test aid: LANDSTALKER_MAPSHOT=f1,f2,.. writes the map as it would open at those frames (LANDSTALKER_SHOT_DIR/mapshot_FRAME.png, size LANDSTALKER_OSHOT_SIZE or 1280x800), also headless;
LANDSTALKER_MAPSHOT_FLOOR=n shows floor n instead of the current one.
Needs patch_keys.py (LK_BMAP), patch_display.py, patch_subpix.py (lk_ss_gen = own map frames) before it.  Idempotent.  usage: patch_roommap.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_ROOMMAP v3"   # v3: room picture clipped to its cell   # v2 (2026-10-31): pad read through the pad thread (v1 hung: controller events are off, LK_PADTHREAD); dungeons only

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    module = r'''/* ---- LK_ROOMMAP v3: room map (tools/patch_roommap.py) ---- */
typedef struct { int room, area, floor, gx, gy, vbit, hl, ht, hw, hh, tw, th; const uint16_t *px; } lk_rm_t;
static lk_rm_t *lk_rm_r; static int lk_rm_n, lk_rm_loaded, lk_rm_ok, lk_rm_nar;
static short lk_rm_idx[1024], lk_rm_var[1024]; static int lk_rm_afl[256]; static char lk_rm_anm[256][28];
static int (*lk_rm_e)[3]; static int lk_rm_ne; static uint8_t *lk_rm_blob;
static volatile int lk_rm_req; static const uint8_t *lk_rm_lastfb;
static int lk_rm_open, lk_rm_area, lk_rm_floor, lk_rm_cur, lk_rm_nx, lk_rm_ny, lk_rm_blink; static long lk_rm_seen_gen = -1, lk_rm_gen_frame = -1000;
static uint32_t *lk_rm_buf; static int lk_rm_bw, lk_rm_bh, lk_rm_dirty = 1; static SDL_Texture *lk_rm_tex; static int lk_rm_tw, lk_rm_th;
void lk_map_request(void) { lk_rm_req = 1; }
static void lk_rm_load(void) {
    char dir[700], path[760]; FILE *f; char l[256];
    lk_rm_loaded = 1;
    for (int i = 0; i < 1024; i++) { lk_rm_idx[i] = -1; lk_rm_var[i] = -1; }
    { const char *e = getenv("LANDSTALKER_MAPDIR"); if (e && *e) snprintf(dir, sizeof dir, "%s", e); else { char *b = SDL_GetBasePath(); snprintf(dir, sizeof dir, "%sroommap", b ? b : "./"); if (b) SDL_free(b); } }
    snprintf(path, sizeof path, "%s/layout.txt", dir); f = fopen(path, "r");
    if (!f) { printf("roommap: no map data (%s): the Map button does nothing (tools/roommap.py)\n", path); return; }
    int cap = 1024, ecap = 2048; lk_rm_r = (lk_rm_t *)calloc(cap, sizeof *lk_rm_r); lk_rm_e = (int (*)[3])calloc(ecap, sizeof *lk_rm_e);
    while (lk_rm_r && lk_rm_e && fgets(l, sizeof l, f)) {
        int a, b, c, d, e2, g, h, i2, j, k; char nm[64];
        if (l[0] == 'A' && sscanf(l + 2, "%d %d %63s", &a, &b, nm) == 3 && a >= 0 && a < 256) { lk_rm_afl[a] = b; snprintf(lk_rm_anm[a], sizeof lk_rm_anm[a], "%s", nm); if (a + 1 > lk_rm_nar) lk_rm_nar = a + 1; }
        else if (l[0] == 'R' && sscanf(l + 2, "%d %d %d %d %d %d %d %d %d %d", &a, &b, &c, &d, &e2, &g, &h, &i2, &j, &k) == 10 && a >= 0 && a < 1024 && lk_rm_n < cap) {
            lk_rm_t *r = &lk_rm_r[lk_rm_n]; r->room = a; r->area = b; r->floor = c; r->gx = d; r->gy = e2; r->vbit = g; r->hl = h; r->ht = i2; r->hw = j; r->hh = k; lk_rm_idx[a] = (short)lk_rm_n++; }
        else if (l[0] == 'E' && sscanf(l + 2, "%d %d %d", &a, &b, &c) == 3 && lk_rm_ne < ecap) { lk_rm_e[lk_rm_ne][0] = a; lk_rm_e[lk_rm_ne][1] = b; lk_rm_e[lk_rm_ne][2] = c; lk_rm_ne++; }
        else if (l[0] == 'V' && sscanf(l + 2, "%d %d", &a, &b) == 2 && a >= 0 && a < 1024) lk_rm_var[a] = (short)b;
    }
    fclose(f);
    snprintf(path, sizeof path, "%s/thumbs.bin", dir); f = fopen(path, "rb");
    if (f) {
        long sz; fseek(f, 0, SEEK_END); sz = ftell(f); fseek(f, 0, SEEK_SET);
        lk_rm_blob = (uint8_t *)malloc((size_t)sz);
        if (lk_rm_blob && fread(lk_rm_blob, 1, (size_t)sz, f) == (size_t)sz && sz > 9 && !memcmp(lk_rm_blob, "LKRM1", 5)) {
            uint32_t n = lk_rm_blob[5] | lk_rm_blob[6] << 8 | lk_rm_blob[7] << 16 | (uint32_t)lk_rm_blob[8] << 24; const uint8_t *ix = lk_rm_blob + 9, *body = ix + 10 * n;
            for (uint32_t i = 0; i < n && body <= lk_rm_blob + sz; i++, ix += 10) {
                int room = ix[0] | ix[1] << 8, w = ix[2] | ix[3] << 8, h = ix[4] | ix[5] << 8; uint32_t off = ix[6] | ix[7] << 8 | ix[8] << 16 | (uint32_t)ix[9] << 24;
                if (room < 1024 && lk_rm_idx[room] >= 0 && body + off + (size_t)w * h * 2 <= lk_rm_blob + sz) { lk_rm_t *r = &lk_rm_r[lk_rm_idx[room]]; r->tw = w; r->th = h; r->px = (const uint16_t *)(body + off); }
            }
        }
        fclose(f);
    }
    lk_rm_ok = lk_rm_n > 0;
    printf("roommap: %d rooms, %d areas, %d connections loaded from %s\n", lk_rm_n, lk_rm_nar, lk_rm_ne, dir);
}
static int lk_rm_lookup(int room) { if (room < 0 || room >= 1024) return -1; if (lk_rm_idx[room] >= 0) return lk_rm_idx[room]; if (lk_rm_var[room] >= 0 && lk_rm_var[room] < 1024) return lk_rm_idx[lk_rm_var[room]]; return -1; }
static int lk_rm_all = -1;   /* test aid LANDSTALKER_MAPSHOT_ALL=1: every room of the area, visited or not */
static int lk_rm_visited(const lk_rm_t *r) { const uint8_t *m = bus_get_ram(); if (lk_rm_all < 0) { const char *e = getenv("LANDSTALKER_MAPSHOT_ALL"); lk_rm_all = e && *e == '1'; } if (lk_rm_all) return 1; int b = r->vbit; return (b >= 0 && b < 8 * 200) && (m[((0xFF10C0 + (b >> 3)) & 0xFFFF) ^ 1] >> (b & 7) & 1); }
static int lk_rm_state(void) {   /* current room / Nigel's cell; 1 = the map can open (own map frames are running, the room is known) */
    const uint8_t *m = bus_get_ram(); extern long lk_ss_gen;
    if (!lk_rm_loaded) lk_rm_load();
    if (!lk_rm_ok) return 0;
    int room = (m[0x1204 ^ 1] << 8) | m[0x1205 ^ 1], i = lk_rm_lookup(room);
    lk_rm_nx = m[0x5400 ^ 1]; lk_rm_ny = m[0x5401 ^ 1];
    if (i < 0) return 0;
    lk_rm_cur = i;
    return lk_ss_gen != lk_rm_seen_gen || platform_frame_number() - lk_rm_gen_frame < 8;
}
static void lk_rm_note_frame(void) { extern long lk_ss_gen; if (lk_ss_gen != lk_rm_seen_gen) { lk_rm_seen_gen = lk_ss_gen; lk_rm_gen_frame = platform_frame_number(); } }
/* ---- drawing into an ARGB buffer (alpha used: the game picture shows dimmed behind it) ---- */
static inline void lk_rm_px(int x, int y, uint32_t c) { if ((unsigned)x < (unsigned)lk_rm_bw && (unsigned)y < (unsigned)lk_rm_bh) lk_rm_buf[(size_t)y * lk_rm_bw + x] = c; }
static void lk_rm_fill(int x0, int y0, int w, int h, uint32_t c) { for (int y = y0; y < y0 + h; y++) for (int x = x0; x < x0 + w; x++) lk_rm_px(x, y, c); }
static void lk_rm_diamond(int cx, int cy, int hw, uint32_t c) { int hh = hw / 2; for (int dy = -hh; dy <= hh; dy++) { int w = hw - 2 * abs(dy); for (int dx = -w; dx <= w; dx++) lk_rm_px(cx + dx, cy + dy, c); } }
static void lk_rm_text(int x, int y, const char *t, int sc, uint32_t c) {
    for (int i = 0; t[i]; i++) { char ch = t[i] == '_' ? ' ' : t[i]; if (ch >= 'a' && ch <= 'z') ch = (char)(ch - 32); const uint8_t *gl = lk_glyph(ch); for (int r = 0; r < 7; r++) for (int k = 0; k < 5; k++) if (gl[r] & (0x10 >> k)) { lk_rm_fill(x + (i * 6 + k) * sc + sc / 2 + 1, y + r * sc + sc / 2 + 1, sc, sc, 0xFF000000u); lk_rm_fill(x + (i * 6 + k) * sc, y + r * sc, sc, sc, c); } }
}
static uint32_t lk_rm_565(uint16_t v, int dim) { uint32_t r = (v >> 11) & 31, g = (v >> 5) & 63, b = v & 31; r = r * 255 / 31; g = g * 255 / 63; b = b * 255 / 31; if (dim) { r = r * 2 / 5; g = g * 2 / 5; b = b * 2 / 5; } return 0xFF000000u | r << 16 | g << 8 | b; }
static void lk_rm_render(int W, int H, int cur, int floor, int blink) {
    if (lk_rm_bw != W || lk_rm_bh != H) { free(lk_rm_buf); lk_rm_buf = (uint32_t *)malloc((size_t)W * H * 4); lk_rm_bw = lk_rm_buf ? W : 0; lk_rm_bh = lk_rm_buf ? H : 0; }
    if (!lk_rm_buf) return;
    const lk_rm_t *cr = &lk_rm_r[cur]; const int area = cr->area, nfl = lk_rm_afl[area] > 0 ? lk_rm_afl[area] : 1;
    const uint32_t GOLD = 0xFFD8A848u, GOLDD = 0xFF6E5424u, PANEL = 0xF8101430u;
    for (size_t i = 0; i < (size_t)W * H; i++) lk_rm_buf[i] = 0xA0000008u;   /* the game dimmed behind */
    int m = H / 22, px0 = m, py0 = m, pw = W - 2 * m, ph = H - 2 * m, sc = H >= 600 ? 3 : 2;
    lk_rm_fill(px0, py0, pw, ph, PANEL);
    for (int t = 0; t < 3; t++) { uint32_t c = t == 1 ? GOLD : GOLDD; lk_rm_fill(px0 + t, py0 + t, pw - 2 * t, 1, c); lk_rm_fill(px0 + t, py0 + ph - 1 - t, pw - 2 * t, 1, c); lk_rm_fill(px0 + t, py0 + t, 1, ph - 2 * t, c); lk_rm_fill(px0 + pw - 1 - t, py0 + t, 1, ph - 2 * t, c); }
    { char t[80]; extern const char *lk_lang_tr(const char *en); snprintf(t, sizeof t, "%s", lk_rm_anm[area]); lk_rm_text(px0 + 6 * sc, py0 + 5 * sc, t, sc, GOLD);
      if (nfl > 1) { snprintf(t, sizeof t, "%s %d / %d", lk_lang_tr("FLOOR"), floor + 1, nfl); lk_rm_text(px0 + pw - 6 * sc - (int)strlen(t) * 6 * sc, py0 + 5 * sc, t, sc, floor == cr->floor ? 0xFFF0E0B0u : 0xFFA09070u);
                    for (int k = 0; k < nfl && k < 12; k++) lk_rm_fill(px0 + pw - 6 * sc - (nfl - k) * 4 * sc, py0 + 15 * sc, 3 * sc, 2 * sc, k == floor ? GOLD : GOLDD); } }
    /* rooms of this floor that are shown: visited or current */
    int gx0 = 1 << 30, gx1 = -(1 << 30), gy0 = 1 << 30, gy1 = -(1 << 30), any = 0;
    for (int i = 0; i < lk_rm_n; i++) { const lk_rm_t *r = &lk_rm_r[i]; if (r->area != area || r->floor != floor || !(i == cur || lk_rm_visited(r))) continue; int u = r->gx - r->gy, v = r->gx + r->gy; if (u < gx0) gx0 = u; if (u > gx1) gx1 = u; if (v < gy0) gy0 = v; if (v > gy1) gy1 = v; any = 1; }
    if (!any) { lk_rm_text(px0 + pw / 2 - 21 * sc, py0 + ph / 2, "?", sc * 3, GOLDD); return; }
    int top = py0 + 22 * sc, aw = pw - 8 * sc, ah = ph - 26 * sc;
    int C = aw / (gx1 - gx0 + 2); { int c2 = 2 * ah / (gy1 - gy0 + 3); if (c2 < C) C = c2; } if (C > 150) C = 150; if (C < 12) C = 12;
    int ox = px0 + pw / 2 - (gx0 + gx1) * C / 2, oy = top + ah / 2 - (gy0 + gy1) * C / 4;
#define LK_RM_CX(r) (ox + ((r)->gx - (r)->gy) * C)
#define LK_RM_CY(r) (oy + ((r)->gx + (r)->gy) * C / 2)
    for (int e = 0; e < lk_rm_ne; e++) {   /* passages: bars between the two cells */
        int a = lk_rm_lookup(lk_rm_e[e][0]), b = lk_rm_lookup(lk_rm_e[e][1]); if (a < 0 || b < 0) continue;
        const lk_rm_t *ra = &lk_rm_r[a], *rb = &lk_rm_r[b];
        if (ra->area != area || rb->area != area || ra->floor != floor || rb->floor != floor) continue;
        if (!(a == cur || lk_rm_visited(ra)) || !(b == cur || lk_rm_visited(rb))) continue;
        int x0 = LK_RM_CX(ra), y0 = LK_RM_CY(ra), x1 = LK_RM_CX(rb), y1 = LK_RM_CY(rb), n = abs(x1 - x0) > abs(y1 - y0) ? abs(x1 - x0) : abs(y1 - y0); if (n < 1) n = 1;
        for (int k = 0; k <= n; k += 2) lk_rm_diamond(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, C / 9 > 3 ? C / 9 : 3, 0xFFA88848u);
    }
    for (int pass = 0; pass < 2; pass++) for (int d = gy0; d <= gy1; d++) for (int i = 0; i < lk_rm_n; i++) {   /* back to front; pass 1 = the current room's frame + Nigel on top */
        const lk_rm_t *r = &lk_rm_r[i]; if (r->area != area || r->floor != floor || r->gx + r->gy != d || !(i == cur || lk_rm_visited(r))) continue;
        if (pass == 1 && i != cur) continue;
        int cx = LK_RM_CX(r), cy = LK_RM_CY(r), here = i == cur;
        if (pass == 0) { lk_rm_diamond(cx, cy, C * 9 / 10, here ? GOLD : 0xFF3C3858u); lk_rm_diamond(cx, cy, C * 9 / 10 - 3, 0xFF080814u); }
        if (r->px && r->tw > 0) {   /* the room picture: as wide as the cell, bottom on the cell's bottom corner (the floor diamond of the picture = the cell), clipped to the cell (v3, user: it ran over its box) */
            int hw = C * 9 / 10 - 3, hh = hw / 2, dw = 2 * hw, dh = r->th * dw / r->tw, top = cy + hh - dh;
            if (pass == 0 && hw > 2) for (int y = 0; y < dh; y++) { int yy = top + y - cy; if (yy < -hh || yy > hh) continue; int lim = hw - 2 * abs(yy); const uint16_t *row = r->px + (size_t)(y * r->th / dh) * r->tw; for (int x = 0; x < dw; x++) { int xx = x - hw; if (xx < -lim || xx > lim) continue; uint16_t v = row[x * r->tw / dw]; if (v) lk_rm_px(cx + xx, top + y, lk_rm_565(v, 0)); } }
            if (here && pass == 1 && blink) {   /* Nigel: his cell relative to the floor's centre, on the cell's 2:1 projection */
                double k = (double)dw / (double)(r->hw + r->hh), X = lk_rm_nx - (r->hl + r->hw / 2.0), Y = lk_rm_ny - (r->ht + r->hh / 2.0);
                int nx = cx + (int)((X - Y) * k), ny = cy + (int)((X + Y) * k / 2);
                lk_rm_diamond(nx, ny, sc * 4 + 2, 0xFFFFFFFFu); lk_rm_diamond(nx, ny, sc * 4 - 1, 0xFFE02828u);
            }
        }
        if (pass == 0) for (int e = 0; e < lk_rm_ne; e++) {   /* stairs: white triangle up (this room is the lower one) / down */
            if (!lk_rm_e[e][2]) continue; int a = lk_rm_lookup(lk_rm_e[e][0]), b = lk_rm_lookup(lk_rm_e[e][1]); if (a != i && b != i) continue;
            int up = a == i, tx = cx + C * 11 / 20, ty = cy - C / 6, hgt = C / 7 > 4 ? C / 7 : 4;
            for (int k = 0; k <= hgt; k++) for (int dx = -k; dx <= k; dx++) { lk_rm_px(tx + dx, ty + (up ? k : hgt - k), 0xFFFFFFFFu); }
        }
    }
#undef LK_RM_CX
#undef LK_RM_CY
}
static void lk_map_draw(int ow, int oh) {   /* called by lk_disp_present before the OSD while the map is open */
    if (!lk_rm_open || !s_renderer) return;
    if (lk_rm_dirty || lk_rm_bw != ow || lk_rm_bh != oh) { lk_rm_render(ow, oh, lk_rm_cur, lk_rm_floor, lk_rm_blink); lk_rm_dirty = 0;
        if (!lk_rm_tex || lk_rm_tw != ow || lk_rm_th != oh) { if (lk_rm_tex) SDL_DestroyTexture(lk_rm_tex); lk_rm_tex = SDL_CreateTexture(s_renderer, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STREAMING, ow, oh); lk_rm_tw = ow; lk_rm_th = oh; if (lk_rm_tex) SDL_SetTextureBlendMode(lk_rm_tex, SDL_BLENDMODE_BLEND); }
        if (lk_rm_tex && lk_rm_buf) SDL_UpdateTexture(lk_rm_tex, NULL, lk_rm_buf, ow * 4); }
    if (lk_rm_tex) SDL_RenderCopy(s_renderer, lk_rm_tex, NULL, NULL);
}
static int lk_map_modal(void) {   /* the map is open: returns 0 when the window was closed (quit) */
    extern uint32_t lk_map_pad(void); SDL_Event ev; int closing = 0; Uint32 t0 = SDL_GetTicks(), tb = t0, tclose = 0; uint32_t prev;
    if (!lk_rm_state() || !lk_rm_lastfb) {   /* not in a dungeon: a short note */
        if (lk_rm_ok) { extern const char *lk_lang_tr(const char *en); snprintf(lk_osd_text, sizeof lk_osd_text, "%s", lk_lang_tr("NO MAP HERE")); lk_osd_frames = 90; }
        return 1;
    }
    lk_rm_area = lk_rm_r[lk_rm_cur].area; lk_rm_floor = lk_rm_r[lk_rm_cur].floor; lk_rm_open = 1; lk_rm_blink = 1; lk_rm_dirty = 1;
    printf("roommap: open (room %d, area %s, floor %d)\n", lk_rm_r[lk_rm_cur].room, lk_rm_anm[lk_rm_area], lk_rm_floor);
    if (s_audio_dev > 0) { SDL_PauseAudioDevice(s_audio_dev, 1); SDL_ClearQueuedAudio(s_audio_dev); }
    lk_disp_present(lk_rm_lastfb);
    prev = lk_map_pad();   /* the opening press is still held: only NEW presses count */
    for (;;) {
        int redraw = 0, nfl = lk_rm_afl[lk_rm_area], kdown = -1;
        while (SDL_PollEvent(&ev)) {   /* keyboard / window only (controller events are switched off by LK_PADTHREAD) */
            if (ev.type == SDL_QUIT) { lk_rm_open = 0; if (s_audio_dev > 0) SDL_PauseAudioDevice(s_audio_dev, 0); return 0; }
            if (ev.type == SDL_KEYDOWN && !ev.key.repeat) kdown = ev.key.keysym.scancode;
            if (ev.type == SDL_WINDOWEVENT) redraw = 1;
        }
        uint32_t cur = lk_map_pad(), ed = cur & ~prev; prev = cur;
#define LKMB(b) (ed & (1u << SDL_CONTROLLER_BUTTON_##b))
        if (!closing) {
            if (LKMB(DPAD_UP) || LKMB(RIGHTSHOULDER) || kdown == SDL_SCANCODE_UP || kdown == SDL_SCANCODE_PAGEUP) { if (lk_rm_floor + 1 < nfl) { lk_rm_floor++; redraw = 1; } }
            else if (LKMB(DPAD_DOWN) || LKMB(LEFTSHOULDER) || kdown == SDL_SCANCODE_DOWN || kdown == SDL_SCANCODE_PAGEDOWN) { if (lk_rm_floor > 0) { lk_rm_floor--; redraw = 1; } }
            else if (ed || kdown == SDL_SCANCODE_ESCAPE || kdown == SDL_SCANCODE_M || kdown == SDL_SCANCODE_RETURN || kdown == SDL_SCANCODE_X) { closing = 1; tclose = SDL_GetTicks(); }   /* any other new button closes (B, A, Start, the Map binding, ..) */
        }
#undef LKMB
        if (SDL_GetTicks() - tb > 400) { tb = SDL_GetTicks(); lk_rm_blink ^= 1; redraw = 1; }
        if (closing) { const Uint8 *ks = SDL_GetKeyboardState(NULL); int anyk = 0; for (int i = 4; i < SDL_NUM_SCANCODES && !anyk; i++) anyk = ks[i]; if ((!cur && !anyk) || SDL_GetTicks() - tclose > 1500) break; }   /* the game must not see the closing press */
        if (redraw) { lk_rm_dirty = 1; lk_disp_present(lk_rm_lastfb); } else SDL_Delay(15);
    }
    lk_rm_open = 0;
    if (s_audio_dev > 0) SDL_PauseAudioDevice(s_audio_dev, 0);
    s_frame_start = SDL_GetPerformanceCounter();
    printf("roommap: closed after %.1f s\n", (SDL_GetTicks() - t0) / 1000.0);
    return 1;
}
static void lk_map_shot(long frame) {   /* test aid LANDSTALKER_MAPSHOT */
    static int on = -1; static const char *ml; if (on < 0) { ml = getenv("LANDSTALKER_MAPSHOT"); on = ml && *ml; }
    if (!on || !lk_shot_wanted(ml, frame)) return;
    int ow = 1280, oh = 800; { const char *z = getenv("LANDSTALKER_OSHOT_SIZE"); if (z) sscanf(z, "%dx%d", &ow, &oh); }
    if (!lk_rm_state()) { { const uint8_t *m = bus_get_ram(); extern long lk_ss_gen; int room = (m[0x1204 ^ 1] << 8) | m[0x1205 ^ 1]; printf("mapshot: frame %ld: map not available (room %d, known %d, own map frame %ld frames ago)\n", frame, room, lk_rm_lookup(room) >= 0, platform_frame_number() - lk_rm_gen_frame); } return; }
    int fl = lk_rm_r[lk_rm_cur].floor; { const char *e = getenv("LANDSTALKER_MAPSHOT_FLOOR"); if (e && *e) fl = atoi(e); }
    lk_rm_render(ow, oh, lk_rm_cur, fl, 1);
    { extern int lk_wide_e; const int sw = 320 + 2 * lk_wide_e; const uint32_t *g = (const uint32_t *)lk_rm_lastfb; uint32_t *img = (uint32_t *)malloc((size_t)ow * oh * 4);   /* over the 1x game picture, nearest */
      if (img) { for (int y = 0; y < oh; y++) for (int x = 0; x < ow; x++) { uint32_t o = lk_rm_buf[(size_t)y * ow + x], a = o >> 24, b = g ? g[(size_t)(y * 224 / oh) * sw + x * sw / ow] : 0; uint32_t r = (((o >> 16) & 255) * a + ((b >> 16) & 255) * (255 - a)) / 255, gg = (((o >> 8) & 255) * a + ((b >> 8) & 255) * (255 - a)) / 255, bb = ((o & 255) * a + (b & 255) * (255 - a)) / 255; img[(size_t)y * ow + x] = 0xFF000000u | r << 16 | gg << 8 | bb; }
        const char *dir = getenv("LANDSTALKER_SHOT_DIR"); char path[700]; snprintf(path, sizeof path, "%s/mapshot_%06ld.png", dir && *dir ? dir : "shots", frame);
        printf("mapshot: %s %s (room %d, area %s, floor %d, Nigel %d,%d)\n", lk_shot_png(path, img, ow, oh, 1) ? "wrote" : "FAILED", path, lk_rm_r[lk_rm_cur].room, lk_rm_anm[lk_rm_r[lk_rm_cur].area], fl, lk_rm_nx, lk_rm_ny); free(img); } }
}
'''
    a = "void platform_present_frame(const uint8_t *framebuffer) {\n"
    assert s.count(a) == 1
    s = s.replace(a, module + a, 1)
    a = "    lk_shot_frame(framebuffer, s_frame_no);\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "    lk_rm_lastfb = framebuffer; lk_rm_note_frame(); lk_map_shot(s_frame_no);   /* LK_ROOMMAP v3 */\n", 1)
    a = "    lk_ssh_d = 0;   /* LK_SSHARP v1 */\n    lk_osd_draw(ow, oh);\n"
    assert s.count(a) == 1, "platform_sdl.c: run patch_subpix.py first"
    s = s.replace(a, "    lk_ssh_d = 0;   /* LK_SSHARP v1 */\n    lk_map_draw(ow, oh);   /* LK_ROOMMAP v3 */\n    lk_osd_draw(ow, oh);\n", 1)
    a = "static void lk_disp_present(const uint8_t *framebuffer) {\n"
    assert s.count(a) == 1
    s = s.replace(a, "static void lk_map_draw(int ow, int oh);   /* LK_ROOMMAP v3 */\n" + a, 1)
    a = "    while (SDL_PollEvent(&ev)) {\n        if (ev.type == SDL_QUIT) return false;\n"
    assert s.count(a) == 1
    s = s.replace(a, "    if (lk_rm_req) { lk_rm_req = 0; if (!lk_map_modal()) return false; }   /* LK_ROOMMAP v3: the map button was pressed */\n" + a, 1)
    a = "static bool s_headless = false;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "static volatile int lk_rm_req;   /* LK_ROOMMAP v3 (defined with the map code below) */\n", 1)
    s = s.replace("static volatile int lk_rm_req; static const uint8_t *lk_rm_lastfb;", "static const uint8_t *lk_rm_lastfb;", 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/input.c")
s = open(p).read()
if VER not in s:
    a = "uint16_t recomp_input_read_pad(int port) {\n"
    assert s.count(a) == 1 and "LK_KEYS v1" in s and "LK_PADTHREAD" in s, "input.c: run patch_keys.py / patch_padthread.py first"
    s = s.replace(a, r'''/* LK_ROOMMAP v3: the room map's input while the game is paused in its loop: bit b = SDL controller button b on any pad (the pad thread's copy; the worker is kicked
   every call, it only runs after platform_poll_events otherwise), left stick up / down = D-pad, bit 31 = the Map binding's pad code (triggers too) */
uint32_t lk_map_pad(void) {
    extern void lk_pad_kick(void); uint32_t m = 0;
    lk_bind_init(); lk_pad_kick();
    if (!lk_pt_run) SDL_GameControllerUpdate();
    for (int b = 0; b < SDL_CONTROLLER_BUTTON_MAX && b < 31; b++) if (lk_pad_button(lk_pads, (SDL_GameControllerButton)b)) m |= 1u << b;
    { int ly = lk_pad_axis(lk_pads, SDL_CONTROLLER_AXIS_LEFTY); if (ly < -20000) m |= 1u << SDL_CONTROLLER_BUTTON_DPAD_UP; if (ly > 20000) m |= 1u << SDL_CONTROLLER_BUTTON_DPAD_DOWN; }
    if (lk_bind_pad[LK_BMAP] && lk_pad_code_down(lk_pads, lk_bind_pad[LK_BMAP])) m |= 1u << 31;
    return m;
}
''' + a, 1)
    open(p, "w").write(s)
    print("input.c patched:", VER)
