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
VER = "LK_ROOMMAP v7"   # v7 (2026-10-31): numbered badge on the door itself + legend   # v6 (2026-10-31): numbered door pairs as stub + round badge (roommap v8: boxes sized by door count)   # v5 (2026-10-31): schematic slabs instead of the room pictures, numbered door pairs where doors do not meet (user)   # v4 (2026-10-31): rooms drawn as boxes of their size, connectors at the doors (tools/roommap.py v5)   # v3: room picture clipped to its cell   # v2 (2026-10-31): pad read through the pad thread (v1 hung: controller events are off, LK_PADTHREAD); dungeons only

p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    module = r'''/* ---- LK_ROOMMAP v7: room map (tools/patch_roommap.py) ---- */
typedef struct { int room, area, floor, gx, gy, vbit, hl, ht, hw, hh, W, H, tw, th; const uint16_t *px; } lk_rm_t;
static lk_rm_t *lk_rm_r; static int lk_rm_n, lk_rm_loaded, lk_rm_ok, lk_rm_nar;
static short lk_rm_idx[1024], lk_rm_var[1024]; static int lk_rm_afl[256]; static char lk_rm_anm[256][28];
static int (*lk_rm_e)[7]; static int lk_rm_ne; static uint8_t *lk_rm_blob;
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
    int cap = 1024, ecap = 2048; lk_rm_r = (lk_rm_t *)calloc(cap, sizeof *lk_rm_r); lk_rm_e = (int (*)[7])calloc(ecap, sizeof *lk_rm_e);
    while (lk_rm_r && lk_rm_e && fgets(l, sizeof l, f)) {
        int a, b, c, d, e2, g, h, i2, j, k, W, H, q1, q2, q3, q4; char nm[64];
        if (l[0] == 'A' && sscanf(l + 2, "%d %d %63s", &a, &b, nm) == 3 && a >= 0 && a < 256) { lk_rm_afl[a] = b; snprintf(lk_rm_anm[a], sizeof lk_rm_anm[a], "%s", nm); if (a + 1 > lk_rm_nar) lk_rm_nar = a + 1; }
        else if (l[0] == 'R' && sscanf(l + 2, "%d %d %d %d %d %d %d %d %d %d %d %d", &a, &b, &c, &d, &e2, &g, &h, &i2, &j, &k, &W, &H) == 12 && a >= 0 && a < 1024 && lk_rm_n < cap) {
            lk_rm_t *r = &lk_rm_r[lk_rm_n]; r->room = a; r->area = b; r->floor = c; r->gx = d; r->gy = e2; r->vbit = g; r->hl = h; r->ht = i2; r->hw = j; r->hh = k; r->W = W; r->H = H; lk_rm_idx[a] = (short)lk_rm_n++; }
        else if (l[0] == 'E' && sscanf(l + 2, "%d %d %d %d %d %d %d", &a, &b, &c, &q1, &q2, &q3, &q4) == 7 && lk_rm_ne < ecap) { int *e = lk_rm_e[lk_rm_ne++]; e[0] = a; e[1] = b; e[2] = c; e[3] = q1; e[4] = q2; e[5] = q3; e[6] = q4; }
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
    /* rooms of this floor that are shown: visited or current (v4: boxes of W x H grid units, tools/roommap.py v5) */
    double umin = 1e9, umax = -1e9, vmin = 1e9, vmax = -1e9; int any = 0;
    for (int i = 0; i < lk_rm_n; i++) { const lk_rm_t *r = &lk_rm_r[i]; if (r->area != area || r->floor != floor || !(i == cur || lk_rm_visited(r))) continue;
        double u0 = r->gx - (r->gy + r->H), u1 = (r->gx + r->W) - r->gy, v0 = r->gx + r->gy, v1 = r->gx + r->W + r->gy + r->H;
        if (u0 < umin) umin = u0; if (u1 > umax) umax = u1; if (v0 < vmin) vmin = v0; if (v1 > vmax) vmax = v1; any = 1; }
    if (!any) { lk_rm_text(px0 + pw / 2 - 21 * sc, py0 + ph / 2, "?", sc * 3, GOLDD); return; }
    int top = py0 + 24 * sc, aw = pw - 10 * sc, ah = ph - 30 * sc;
    double S = aw / (umax - umin + 0.4); { double s2 = 2.0 * ah / (vmax - vmin + 0.4); if (s2 < S) S = s2; } if (S > 110) S = 110; if (S < 5) S = 5;
    double ox = px0 + pw / 2.0 - (umin + umax) * S / 2.0, oy = top + ah / 2.0 - (vmin + vmax) * S / 4.0;
#define LK_RM_PX(u, v) (ox + ((u) - (v)) * S)
#define LK_RM_PY(u, v) (oy + ((u) + (v)) * S / 2.0)
    const double gap = 0.09; const int depth = (int)(S * 0.16) > 2 ? (int)(S * 0.16) : 2;
    for (int pass = 0; pass < 2; pass++) for (int i = 0; i < lk_rm_n; i++) {   /* v5: schematic slabs (user: the room pictures looked pixelated): pass 0 = the darker side under every slab, pass 1 = the top */
        const lk_rm_t *r = &lk_rm_r[i]; if (r->area != area || r->floor != floor || !(i == cur || lk_rm_visited(r))) continue;
        int here = i == cur; double u0 = r->gx + gap, v0 = r->gy + gap, u1 = r->gx + r->W - gap, v1 = r->gy + r->H - gap, fr = 2.0 / S;
        int x0 = (int)LK_RM_PX(u0, v1) - 1, x1 = (int)LK_RM_PX(u1, v0) + 1, y0 = (int)LK_RM_PY(u0, v0) - 1, y1 = (int)LK_RM_PY(u1, v1) + 1 + depth;
        uint32_t top = here ? 0xFFB08838u : 0xFF5C6488u, edge = here ? 0xFFF0C860u : 0xFF8890B8u, side = here ? 0xFF6A4C1Cu : 0xFF2C3048u;
        for (int y = y0; y <= y1; y++) for (int x = x0; x <= x1; x++) {
            double dx = (x - ox) / S, dy = 2.0 * ((pass ? y : y - depth) - oy) / S, u = (dy + dx) / 2.0, v = (dy - dx) / 2.0;
            if (u < u0 || u > u1 || v < v0 || v > v1) continue;
            if (!pass) { lk_rm_px(x, y, side); continue; }
            lk_rm_px(x, y, (u < u0 + fr || v < v0 + fr) ? edge : (u > u1 - fr || v > v1 - fr) ? side : top);   /* light back edges, dark front edges: a raised tile */
        }
    }
    int nlab = 0;
    { int lab = 0; for (int e = 0; e < lk_rm_ne; e++) {   /* doors: connector where both doors meet, otherwise the same small number at both doors; stairs = white triangle; doors to rooms not visited yet are not shown */
        int a = lk_rm_lookup(lk_rm_e[e][0]), b = lk_rm_lookup(lk_rm_e[e][1]); if (a < 0 || b < 0) continue;
        const lk_rm_t *ra = &lk_rm_r[a], *rb = &lk_rm_r[b]; if (ra->area != area || rb->area != area) continue;
        int va = a == cur || lk_rm_visited(ra), vb = b == cur || lk_rm_visited(rb), sa = ra->floor == floor && va, sb = rb->floor == floor && vb;
        double au = ra->gx + lk_rm_e[e][3] / 10.0, av = ra->gy + lk_rm_e[e][4] / 10.0, bu = rb->gx + lk_rm_e[e][5] / 10.0, bv = rb->gy + lk_rm_e[e][6] / 10.0;
        int hgt = (int)(S / 5) > 4 ? (int)(S / 5) : 4, th = (int)(S / 12) > 2 ? (int)(S / 12) : 2;
        if (lk_rm_e[e][2]) {   /* stairs: shown in the room you can see once the other end is known */
            if (sa && vb) { int tx = (int)LK_RM_PX(au, av), ty = (int)LK_RM_PY(au, av) - hgt; for (int k = 0; k <= hgt; k++) for (int dx = -k; dx <= k; dx++) lk_rm_px(tx + dx, ty + k, 0xFFFFFFFFu); }
            if (sb && va) { int tx = (int)LK_RM_PX(bu, bv), ty = (int)LK_RM_PY(bu, bv) - hgt; for (int k = 0; k <= hgt; k++) for (int dx = -k; dx <= k; dx++) lk_rm_px(tx + dx, ty + hgt - k, 0xFFFFFFFFu); }
            continue;
        }
        if (!sa || !sb) continue;
        int x0 = (int)LK_RM_PX(au, av), y0 = (int)LK_RM_PY(au, av), x1 = (int)LK_RM_PX(bu, bv), y1 = (int)LK_RM_PY(bu, bv);
        if (fabs(au - bu) + fabs(av - bv) <= 0.6) {   /* doors that meet (or nearly: a short door piece, two badges on one spot were unreadable) */ int n = abs(x1 - x0) > abs(y1 - y0) ? abs(x1 - x0) : abs(y1 - y0); if (n < 1) n = 1; for (int k = 0; k <= n; k++) lk_rm_diamond(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, th + 1, 0xFFE8C068u); continue; }
        { char t[8]; int ls = sc >= 3 ? 2 : 1, rad = 5 * ls + 2; snprintf(t, sizeof t, "%d", ++lab); nlab = lab;   /* doors that do not meet on the grid (loops): a round badge with the same number ON both doors (v7: no stub; legend at the bottom) */
          for (int end = 0; end < 2; end++) {   /* the badge sits a little inside its own room (two doors on one spot stay readable, and it shows whose door it is) */
              const lk_rm_t *rr = end ? rb : ra; double lu = lk_rm_e[e][end ? 5 : 3] / 10.0, lv = lk_rm_e[e][end ? 6 : 4] / 10.0, iu = 0, iv = 0;
              if (lu < 0.01) iu = 1; else if (lu > rr->W - 0.01) iu = -1; else if (lv < 0.01) iv = 1; else if (lv > rr->H - 0.01) iv = -1;
              double gu = rr->gx + lu + iu * 0.35, gv = rr->gy + lv + iv * 0.35; int ex = (int)LK_RM_PX(gu, gv), ey = (int)LK_RM_PY(gu, gv);
              lk_rm_diamond(end ? x1 : x0, end ? y1 : y0, th + 1, 0xFFE8C068u);
              for (int dy = -rad; dy <= rad; dy++) for (int dx = -rad; dx <= rad; dx++) { int q = dx * dx + dy * dy; if (q <= rad * rad) lk_rm_px(ex + dx, ey + dy, q >= (rad - 2) * (rad - 2) ? 0xFFE8C068u : 0xFF201810u); }
              lk_rm_text(ex - (int)strlen(t) * 3 * ls + 1, ey - 3 * ls - ls / 2, t, ls, 0xFFFFF0C0u); } }
    } }
    if (nlab) { extern const char *lk_lang_tr(const char *en); const char *lg = lk_lang_tr("SAME NUMBER: CONNECTED DOORS"); lk_rm_text(px0 + pw / 2 - (int)strlen(lg) * 3 * (sc - 1), py0 + ph - 11 * sc, lg, sc - 1 > 0 ? sc - 1 : 1, 0xFFA09070u); }   /* legend for the numbered doors */
    if (blink) {   /* Nigel: his cell inside the current room's box */
        const lk_rm_t *r = &lk_rm_r[cur];
        if (r->floor == floor && r->hw > 0 && r->hh > 0) { double u = r->gx + (lk_rm_nx - r->hl + 0.5) / r->hw * r->W, v = r->gy + (lk_rm_ny - r->ht + 0.5) / r->hh * r->H;
            int nx = (int)LK_RM_PX(u, v), ny = (int)LK_RM_PY(u, v); lk_rm_diamond(nx, ny, sc * 4 + 2, 0xFFFFFFFFu); lk_rm_diamond(nx, ny, sc * 4 - 1, 0xFFE02828u); }
    }
#undef LK_RM_PX
#undef LK_RM_PY
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
    s = s.replace(a, a + "    lk_rm_lastfb = framebuffer; lk_rm_note_frame(); lk_map_shot(s_frame_no);   /* LK_ROOMMAP v7 */\n", 1)
    a = "    lk_ssh_d = 0;   /* LK_SSHARP v1 */\n    lk_osd_draw(ow, oh);\n"
    assert s.count(a) == 1, "platform_sdl.c: run patch_subpix.py first"
    s = s.replace(a, "    lk_ssh_d = 0;   /* LK_SSHARP v1 */\n    lk_map_draw(ow, oh);   /* LK_ROOMMAP v7 */\n    lk_osd_draw(ow, oh);\n", 1)
    a = "static void lk_disp_present(const uint8_t *framebuffer) {\n"
    assert s.count(a) == 1
    s = s.replace(a, "static void lk_map_draw(int ow, int oh);   /* LK_ROOMMAP v7 */\n" + a, 1)
    a = "    while (SDL_PollEvent(&ev)) {\n        if (ev.type == SDL_QUIT) return false;\n"
    assert s.count(a) == 1
    s = s.replace(a, "    if (lk_rm_req) { lk_rm_req = 0; if (!lk_map_modal()) return false; }   /* LK_ROOMMAP v7: the map button was pressed */\n" + a, 1)
    a = "static bool s_headless = false;\n"
    assert s.count(a) == 1
    s = s.replace(a, a + "static volatile int lk_rm_req;   /* LK_ROOMMAP v7 (defined with the map code below) */\n", 1)
    s = s.replace("static volatile int lk_rm_req; static const uint8_t *lk_rm_lastfb;", "static const uint8_t *lk_rm_lastfb;", 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

p = os.path.join(root, "src/input.c")
s = open(p).read()
if VER not in s:
    a = "uint16_t recomp_input_read_pad(int port) {\n"
    assert s.count(a) == 1 and "LK_KEYS v1" in s and "LK_PADTHREAD" in s, "input.c: run patch_keys.py / patch_padthread.py first"
    s = s.replace(a, r'''/* LK_ROOMMAP v7: the room map's input while the game is paused in its loop: bit b = SDL controller button b on any pad (the pad thread's copy; the worker is kicked
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
