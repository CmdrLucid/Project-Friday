#!/usr/bin/env python3
"""Key bindings for pad AND keyboard (2026-10-16, user wish; menu pages are added by patch_options.py: Options > 'Buttons' / 'Extras').
One table of 12 actions, each with a pad binding and a keyboard binding (0 = none), saved in ~/.landstalker_keys (lines 'name padcode scancode').
 * Game buttons (what the Mega Drive pad sends): Button A / B / C, Start, Quick 1 (the item on 'Y'), Quick 2 (the item on 'B'; only while Quick Items is On)
 * Extras: Quick Save, Quick Load (pad: hold 0.5 s), Fast Forward (hold), Fullscreen, Coordinates, Quick Equip (hold + direction, tools/patch_equip.py)
Not rebindable (kept as they are): directions (D-pad, left stick, arrow keys), Back = Mode, Esc = quit, F1-F4 / F6 display keys, Alt+Enter, S = MD Y.
Pad codes: 1 + SDL_CONTROLLER_BUTTON_*, 100 = left trigger, 101 = right trigger.  Capture: the menu calls lk_bind_capture(i); the next NEW press (any pad or the keyboard) is assigned (Esc cancels),
a code already used by another action in the same device is swapped; the game sees no buttons while capturing and until everything is released again.
Test aid: LANDSTALKER_RAWPRESS="frame:k:NAME,frame:p:N" simulates one raw press for the capture only (k = SDL scancode name, p = pad code number).
Replaces the hard-coded keyboard / pad lines of input.c and the F5 / F9 / F10 / F11 / Tab key events of platform_sdl.c.  Needs ALL other input patches before it.  Idempotent.  usage: patch_keys.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_KEYS v1"

# ---- platform_sdl.c: remove the fixed key events; Esc does not quit while a capture is running ------------------
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    for old, new in (
        ("        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_ESCAPE) return false;\n",
         "        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_ESCAPE && !lk_bind_capturing()) return false;   /* LK_KEYS v1 */\n"),
        ("        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F5) platform_display_toggle_coords();   /* coordinate overlay */\n", ""),
        ("        if ((ev.type == SDL_KEYDOWN || ev.type == SDL_KEYUP) && ev.key.keysym.sym == SDLK_TAB) lk_ff_kb = ev.type == SDL_KEYDOWN;   /* LK_FFWD v1: Tab held = fast forward */\n", ""),
        ("        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F9) lk_qs_post(1);    /* LK_QUICKSAVE v1 */\n", ""),
        ("        if (ev.type == SDL_KEYDOWN && ev.key.keysym.sym == SDLK_F10) lk_qs_post(2);\n", ""),
        ("(ev.key.keysym.sym == SDLK_F11 || (ev.key.keysym.sym == SDLK_RETURN && (ev.key.keysym.mod & KMOD_ALT)))", "((ev.key.keysym.sym == SDLK_RETURN && (ev.key.keysym.mod & KMOD_ALT)))"),
    ):
        assert s.count(old) == 1, "platform_sdl.c layout changed: " + old
        s = s.replace(old, new, 1)
    a = "bool platform_poll_events(void) {"
    assert s.count(a) == 1
    s = s.replace(a, "/* " + VER + ": key bindings (tools/patch_keys.py), the table itself lives in input.c */\nextern int lk_bind_capturing(void);\nstatic int lk_quit_req;\nvoid platform_request_quit(void) { lk_quit_req = 1; }   /* Options > Quit Game */\n\n" + a + "\n    if (lk_quit_req) return false;   /* LK_KEYS v1: Options > Quit Game */", 1)
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

# ---- input.c: the binding table, capture and the translation to Mega Drive buttons / extras ---------------------
p = os.path.join(root, "src/input.c")
s = open(p).read()
if VER not in s:
    module = r'''/* ---- LK_KEYS v1: key bindings (tools/patch_keys.py) ---- */
static SDL_GameController *lk_pads[8];
#define LKP(b) (1 + (int)(b))
#define LK_PT_L 100
#define LK_PT_R 101
enum { LK_BA, LK_BB, LK_BC, LK_BSTART, LK_BQ1, LK_BQ2, LK_BQSAVE, LK_BQLOAD, LK_BFF, LK_BFS, LK_BCOORD, LK_BEQ, LK_BSPRINT, LK_BMAP, LK_NB };
static const char *lk_bind_nm[LK_NB] = { "Button A", "Button B", "Button C", "Start", "Quick 1", "Quick 2", "Quick Save", "Quick Load", "Fast Forward", "Fullscreen", "Coordinates", "Quick Equip", "Sprint", "Map" };
static const char *lk_bind_id[LK_NB] = { "a", "b", "c", "start", "q1", "q2", "qsave", "qload", "ff", "fs", "coords", "eq", "sprint", "map" };
static int lk_bind_pad[LK_NB], lk_bind_key[LK_NB], lk_bind_loaded;
static int lk_bind_defpad(int i) {
    switch (i) { case LK_BA: return LKP(SDL_CONTROLLER_BUTTON_X); case LK_BB: return LKP(SDL_CONTROLLER_BUTTON_A); case LK_BC: return LKP(SDL_CONTROLLER_BUTTON_B); case LK_BSTART: return LKP(SDL_CONTROLLER_BUTTON_START);
                 case LK_BQ1: return LKP(SDL_CONTROLLER_BUTTON_Y); case LK_BQ2: return LKP(SDL_CONTROLLER_BUTTON_B); case LK_BQSAVE: return LK_PT_L; case LK_BQLOAD: return LKP(SDL_CONTROLLER_BUTTON_LEFTSHOULDER);
                 case LK_BFF: return LKP(SDL_CONTROLLER_BUTTON_LEFTSTICK); case LK_BFS: return LKP(SDL_CONTROLLER_BUTTON_RIGHTSTICK); case LK_BCOORD: return LKP(SDL_CONTROLLER_BUTTON_PADDLE1); case LK_BEQ: return LKP(SDL_CONTROLLER_BUTTON_RIGHTSHOULDER); case LK_BSPRINT: return LK_PT_R; case LK_BMAP: return 0; }   /* Map: no default button while it is experimental (release v1.5.0, user 2026-10-31); the user binds it in Options > Keybindings */   /* 2026-10-30 (user): Sprint on R2, Quick Equip moved to R1, Fast Forward to L3 */
    return 0;
}
static int lk_bind_defkey(int i) {
    switch (i) { case LK_BA: return SDL_SCANCODE_Z; case LK_BB: return SDL_SCANCODE_X; case LK_BC: return SDL_SCANCODE_C; case LK_BSTART: return SDL_SCANCODE_RETURN; case LK_BQ1: return SDL_SCANCODE_A; case LK_BQ2: return SDL_SCANCODE_D;
                 case LK_BQSAVE: return SDL_SCANCODE_F9; case LK_BQLOAD: return SDL_SCANCODE_F10; case LK_BFF: return SDL_SCANCODE_TAB; case LK_BFS: return SDL_SCANCODE_F11; case LK_BCOORD: return SDL_SCANCODE_F5; case LK_BEQ: return SDL_SCANCODE_Q; case LK_BSPRINT: return SDL_SCANCODE_LSHIFT; case LK_BMAP: return 0; }
    return 0;
}
static void lk_bind_path(char *b, size_t n) { const char *h = getenv("HOME"); snprintf(b, n, "%s/.landstalker_keys", h ? h : "."); }
static void lk_bind_defaults(void) { for (int i = 0; i < LK_NB; i++) { lk_bind_pad[i] = lk_bind_defpad(i); lk_bind_key[i] = lk_bind_defkey(i); } }
static void lk_bind_save(void) {
    char p[512]; FILE *f; lk_bind_path(p, sizeof p); f = fopen(p, "w");
    if (f) { for (int i = 0; i < LK_NB; i++) fprintf(f, "%s %d %d\n", lk_bind_id[i], lk_bind_pad[i], lk_bind_key[i]); fclose(f); }
}
static void lk_bind_load(void) {
    char p[512], l[128], nm[32]; FILE *f; int a, b;
    lk_bind_loaded = 1; lk_bind_defaults(); lk_bind_path(p, sizeof p); f = fopen(p, "r");
    if (!f) return;
    int seen[LK_NB]; memset(seen, 0, sizeof seen);
    while (fgets(l, sizeof l, f)) if (sscanf(l, "%31s %d %d", nm, &a, &b) == 3) for (int i = 0; i < LK_NB; i++) if (!strcmp(nm, lk_bind_id[i]) && a >= 0 && a < 200 && b >= 0 && b < SDL_NUM_SCANCODES) { lk_bind_pad[i] = a; lk_bind_key[i] = b; seen[i] = 1; }
    fclose(f);
    for (int i = 0; i < LK_NB; i++) if (!seen[i]) for (int j = 0; j < LK_NB; j++) if (j != i && seen[j]) { if (lk_bind_pad[i] && lk_bind_pad[i] == lk_bind_pad[j]) lk_bind_pad[i] = 0; if (lk_bind_key[i] && lk_bind_key[i] == lk_bind_key[j]) lk_bind_key[i] = 0; }   /* an action added later (Quick Equip) never steals a button from the saved ones */
}
static void lk_bind_init(void) { if (!lk_bind_loaded) lk_bind_load(); }
int lk_bind_count(void) { return LK_NB; }
const char *lk_bind_name(int i) { return lk_bind_nm[i]; }
void lk_bind_reset(void) { lk_bind_init(); lk_bind_defaults(); lk_bind_save(); }
/* short labels for the menu (the game font has capitals and digits only) */
static void lk_bind_padlabel(int c, char *o, size_t n) {
    static const char *nm[] = { "A", "B", "X", "Y", "BACK", "GUIDE", "START", "L3", "R3", "L1", "R1", "UP", "DOWN", "LEFT", "RIGHT", "MISC", "R4", "L4", "L5", "R5", "TOUCH" };
    if (c == LK_PT_L) snprintf(o, n, "L2"); else if (c == LK_PT_R) snprintf(o, n, "R2");
    else if (c >= 1 && c <= (int)(sizeof nm / sizeof nm[0])) snprintf(o, n, "%s", nm[c - 1]);   /* SDL: PADDLE1 = R4, PADDLE2 = L4 (Steam Deck back buttons) */
    else snprintf(o, n, "-");
}
static void lk_bind_keylabel(int sc, char *o, size_t n) {
    const char *nm = sc ? SDL_GetScancodeName((SDL_Scancode)sc) : ""; size_t k = 0;
    if (!nm || !*nm) { snprintf(o, n, "-"); return; }
    if (!strcmp(nm, "Return")) nm = "Enter"; else if (!strcmp(nm, "Left Shift")) nm = "LShift"; else if (!strcmp(nm, "Right Shift")) nm = "RShift"; else if (!strcmp(nm, "Left Ctrl")) nm = "LCtrl"; else if (!strcmp(nm, "Right Ctrl")) nm = "RCtrl";
    else if (!strcmp(nm, "Left Alt")) nm = "LAlt"; else if (!strcmp(nm, "Right Alt")) nm = "RAlt"; else if (!strcmp(nm, "Backspace")) nm = "BkSp"; else if (!strcmp(nm, "Space")) nm = "Space";
    for (; *nm && k + 1 < n && k < 6; nm++) { char c = *nm; if (c >= 'a' && c <= 'z') c = (char)(c - 32); if (c == ' ') continue; o[k++] = c; }
    o[k] = 0;
}
void lk_bind_label(int i, char *o, size_t n) { char a[16], b[16]; lk_bind_init(); lk_bind_padlabel(lk_bind_pad[i], a, sizeof a); lk_bind_keylabel(lk_bind_key[i], b, sizeof b); snprintf(o, n, "%s  %s", a, b); }
void lk_bind_hudlabel(int i, char *o, size_t n) {   /* label for the quick item cells in the HUD: the pad button while a controller is connected, else the key (the other one if that is unbound) */
    char a[16], b[16]; int pad = 0; lk_bind_init();
    for (int k = 0; k < 8; k++) if (lk_pads[k]) pad = 1;
    lk_bind_padlabel(lk_bind_pad[i], a, sizeof a); lk_bind_keylabel(lk_bind_key[i], b, sizeof b);
    snprintf(o, n, "%s", (pad ? strcmp(a, "-") : !strcmp(b, "-")) ? a : b);
}

/* capture */
static int lk_cap = -1, lk_cap_block;
static uint8_t lk_cap_pk[SDL_NUM_SCANCODES]; static uint8_t lk_cap_pp[200];
int lk_bind_capturing(void) { return lk_cap >= 0; }
void lk_bind_capture(int i) { lk_bind_init(); lk_cap = i; lk_cap_block = 1; memset(lk_cap_pk, 1, sizeof lk_cap_pk); memset(lk_cap_pp, 1, sizeof lk_cap_pp); }   /* everything held right now counts as old */
void lk_bind_cancel(void) { lk_cap = -1; }
static int lk_raw_k = -1, lk_raw_p = -1;   /* test aid: simulated raw press for the capture */
static void lk_bind_assign(int i, int pad, int code) {
    int *tab = pad ? lk_bind_pad : lk_bind_key, old = tab[i];
    for (int j = 0; j < LK_NB; j++) if (j != i && tab[j] == code) tab[j] = old;   /* swap with the action that had it */
    tab[i] = code; lk_bind_save();
}
/* pad state of a code */
static int lk_pad_code_down(SDL_GameController **pads, int c) {
    if (c == LK_PT_L) return lk_pad_axis(pads, SDL_CONTROLLER_AXIS_TRIGGERLEFT) > 16000;
    if (c == LK_PT_R) return lk_pad_axis(pads, SDL_CONTROLLER_AXIS_TRIGGERRIGHT) > 16000;
    return c > 0 && c < 100 && lk_pad_button(pads, (SDL_GameControllerButton)(c - 1));
}

extern int lk_quick_get(void);   /* LK_QUICK: with 'Quick Items' on, Quick 2 is a button (GEN_Z) and its pad button no longer acts as Button C */
extern void platform_set_ffwd(int hold);
extern void platform_quick_request(int what);
extern void platform_display_toggle_coords(void);
extern void platform_display_toggle_fullscreen(void);
extern void platform_equip_request(int cat);   /* LK_EQUIP v1 */
static int lk_eq_heldv;
extern int lk_qeq_get(void);   /* Options > Quality of Life > Quick Equip */
int lk_eq_is_held(void) { return lk_eq_heldv; }   /* the game side pauses while it is held */

static void lk_keys_step(const uint8_t *keys, SDL_GameController **pads, uint16_t *buttons) {
    static const uint16_t gen[6] = { GEN_BTN_A, GEN_BTN_B, GEN_BTN_C, GEN_BTN_START, GEN_BTN_X, GEN_BTN_Z };   /* LK_BA, LK_BB, LK_BC, LK_BSTART, LK_BQ1, LK_BQ2 */
    static int prev[LK_NB], hold_pad_ql; int d[LK_NB], dpad[LK_NB], any = 0, quick = lk_quick_get() > 0;
    long frame = platform_frame_number(); lk_bind_init();
    { /* test aid: one simulated raw press per listed frame */
        const char *e = getenv("LANDSTALKER_RAWPRESS"); lk_raw_k = lk_raw_p = -1;
        if (e) { char l[256]; snprintf(l, sizeof l, "%s", e); for (char *t = strtok(l, ","); t; t = strtok(NULL, ",")) { long f; char kind; char nm[32]; if (sscanf(t, "%ld:%c:%31s", &f, &kind, nm) == 3 && f == frame) { if (kind == 'k') lk_raw_k = (int)SDL_GetScancodeFromName(nm); else lk_raw_p = atoi(nm); } } }
    }
    for (int i = 0; i < LK_NB; i++) {
        int kd = lk_bind_key[i] > 0 && keys[lk_bind_key[i]], pd = lk_pad_code_down(pads, lk_bind_pad[i]);
        dpad[i] = pd; d[i] = kd || pd; any |= d[i];
    }
    { static const char *eh; static int ehi; static long e0, e1; if (!ehi) { ehi = 1; eh = getenv("LANDSTALKER_EQHOLD"); if (eh && sscanf(eh, "%ld-%ld", &e0, &e1) != 2) eh = 0; } if (eh && frame >= e0 && frame <= e1) { d[LK_BEQ] = 1; any = 1; } }   /* test aid: Quick Equip held from frame a to b */
    if (lk_cap >= 0) {   /* capture: first NEW press from the keyboard or any pad */
        int got = 0;
        if (lk_raw_k > 0) { if (lk_raw_k == SDL_SCANCODE_ESCAPE) { lk_cap = -1; got = 1; } else { lk_bind_assign(lk_cap, 0, lk_raw_k); lk_cap = -1; got = 1; } }
        else if (lk_raw_p > 0) { lk_bind_assign(lk_cap, 1, lk_raw_p); lk_cap = -1; got = 1; }
        for (int sc = 4; !got && sc < SDL_NUM_SCANCODES; sc++) {
            if (keys[sc] && !lk_cap_pk[sc]) { if (sc == SDL_SCANCODE_ESCAPE) lk_cap = -1; else { lk_bind_assign(lk_cap, 0, sc); lk_cap = -1; } got = 1; }
            lk_cap_pk[sc] = keys[sc];
        }
        for (int c = 1; !got && c < 102; c++) {
            int cc = c; if (c > 21 && c < 100) continue;
            { int dn = lk_pad_code_down(pads, cc); if (dn && !lk_cap_pp[c] && !(cc >= 12 && cc <= 15) && cc != 5) { lk_bind_assign(lk_cap, 1, cc); lk_cap = -1; got = 1; } lk_cap_pp[c] = (uint8_t)dn; }   /* the D-pad (codes 12..15) and Back (5) stay fixed */
        }
        *buttons = 0; memset(prev, 0, sizeof prev); for (int i = 0; i < LK_NB; i++) prev[i] = d[i]; return;
    }
    if (lk_cap_block) { if (any) { for (int i = 0; i < LK_NB; i++) prev[i] = d[i]; *buttons = 0; return; } lk_cap_block = 0; }   /* wait until everything is released after a capture (the press must not act in the menu) */
    for (int i = 0; i < 6; i++) {
        int on = d[i];
        if (i == LK_BC && quick && lk_bind_pad[LK_BC] && lk_bind_pad[LK_BC] == lk_bind_pad[LK_BQ2]) on = lk_bind_key[LK_BC] > 0 && keys[lk_bind_key[LK_BC]];   /* same pad button as Quick 2: Quick 2 wins while Quick Items is On */
        if (i == LK_BQ2 && !quick) on = lk_bind_key[LK_BQ2] > 0 && keys[lk_bind_key[LK_BQ2]];   /* its pad button only counts while Quick Items is On (keyboard always, as before) */
        if (on) *buttons |= gen[i];
    }
    { /* extras: edge triggered (save, coordinates, fullscreen), hold (fast forward, pad quick load 0.5 s) */
        int kq = lk_bind_key[LK_BQLOAD] > 0 && keys[lk_bind_key[LK_BQLOAD]], pq = dpad[LK_BQLOAD];
        if (d[LK_BQSAVE] && !prev[LK_BQSAVE]) platform_quick_request(1);
        if (kq && !(prev[LK_BQLOAD] & 2)) platform_quick_request(2);
        if (pq) { if (++hold_pad_ql == 30) platform_quick_request(2); } else hold_pad_ql = 0;
        platform_set_ffwd(d[LK_BFF]);
        if (d[LK_BFS] && !prev[LK_BFS]) platform_display_toggle_fullscreen();
        if (d[LK_BCOORD] && !prev[LK_BCOORD]) platform_display_toggle_coords();
        if (d[LK_BMAP] && !prev[LK_BMAP]) { extern void lk_map_request(void); lk_map_request(); }   /* room map (tools/patch_roommap.py, 2026-10-31) */
        { /* LK_EQUIP v1: Quick Equip held = the directions pick a kind of equipment instead of moving Nigel (UP sword, RIGHT armour, DOWN boots, LEFT ring) */
          static uint16_t pdir; static int ocat = -1; extern void lk_osd_equip_flash(int cat); const uint16_t dm = GEN_BTN_UP | GEN_BTN_DOWN | GEN_BTN_LEFT | GEN_BTN_RIGHT;
          { static const char *ed2; static int edi; if (!edi) { edi = 1; ed2 = getenv("LANDSTALKER_EQDIR"); } if (ed2) { char l[200], key[40]; snprintf(l, sizeof l, ",%s,", ed2); for (int q = 0; q < 4; q++) for (int t = 0; t < 4; t++) { snprintf(key, sizeof key, ",%ld:%d,", frame - t, q); if (strstr(l, key)) *buttons |= (q == 0 ? GEN_BTN_UP : q == 1 ? GEN_BTN_RIGHT : q == 2 ? GEN_BTN_DOWN : GEN_BTN_LEFT); } } }   /* test aid LANDSTALKER_EQDIR="frame:q" (q 0 up 1 right 2 down 3 left), pressed for 4 frames */
          uint16_t dn = (uint16_t)(*buttons & dm), ed = (uint16_t)(dn & ~pdir);
          lk_eq_heldv = lk_qeq_get() && d[LK_BEQ] && (lk_bind_pad[LK_BEQ] || lk_bind_key[LK_BEQ]);
          if (lk_eq_heldv) {
              if (ocat < 0) { int c = (ed & GEN_BTN_UP) ? 0 : (ed & GEN_BTN_RIGHT) ? 1 : (ed & GEN_BTN_DOWN) ? 2 : (ed & GEN_BTN_LEFT) ? 3 : -1; if (c >= 0) { ocat = c; platform_equip_request(c + 12); } }   /* the first direction opens the strip of that kind (user 2026-10-30) */
              else { if (ed & GEN_BTN_RIGHT) platform_equip_request(ocat + 4); else if (ed & GEN_BTN_LEFT) platform_equip_request(ocat + 8); lk_osd_equip_flash(ocat); }   /* then LEFT / RIGHT step inside it; the strip stays while held */
              *buttons = (uint16_t)(*buttons & ~dm); pdir = dn;
          } else { pdir = 0; ocat = -1; } }
        for (int i = 0; i < LK_NB; i++) prev[i] = d[i];
        prev[LK_BQLOAD] = kq ? 2 : 0;
    }
}

'''
    a = "extern int lk_quick_get(void);   /* LK_QUICK: with 'Quick Items' on, SDL B is a quick button (GEN_Z) instead of the duplicate C button */\n"
    assert s.count(a) == 1, "input.c: quick patch marker missing"
    s = s.replace(a, "", 1)
    b = "static uint16_t s_pad_state[2];\n"
    assert s.count(b) == 1
    s = s.replace(b, b + module, 1)
    for old, new in (
        ("    if (keys[SDL_SCANCODE_Z])      buttons |= GEN_BTN_A;\n    if (keys[SDL_SCANCODE_X])      buttons |= GEN_BTN_B;\n    if (keys[SDL_SCANCODE_C])      buttons |= GEN_BTN_C;\n    if (keys[SDL_SCANCODE_RETURN]) buttons |= GEN_BTN_START;\n    if (keys[SDL_SCANCODE_A])      buttons |= GEN_BTN_X;\n",
         "    /* Z X C Return A D: key bindings, see lk_keys_step (LK_KEYS v1) */\n"),
        ("    if (keys[SDL_SCANCODE_S])      buttons |= GEN_BTN_Y;\n    if (keys[SDL_SCANCODE_D])      buttons |= GEN_BTN_Z;\n", "    if (keys[SDL_SCANCODE_S])      buttons |= GEN_BTN_Y;\n"),
        ("        static SDL_GameController *pads[8];\n", "        SDL_GameController **pads = lk_pads;\n"),
        ("            if (PB(X))             buttons |= GEN_BTN_A;\n            if (PB(A))             buttons |= GEN_BTN_B;\n            if (PB(B))             buttons |= (lk_quick_get() > 0 ? GEN_BTN_Z : GEN_BTN_C);\n            if (PB(START))         buttons |= GEN_BTN_START;\n            if (PB(Y))             buttons |= GEN_BTN_X;\n", ""),
    ):
        assert s.count(old) == 1, "input.c layout changed: " + old[:60]
        s = s.replace(old, new, 1)
    # drop the shoulder / trigger / paddle blocks (now handled by the bindings)
    i0 = s.index("            { /* LANDSTALKER_DISPLAY: L1 = scaling mode")
    i1 = s.index("            if (PB(BACK))          buttons |= GEN_BTN_MODE;")
    s = s[:i0] + s[i1:]
    c = "    buttons |= platform_scripted_buttons();\n"
    assert s.count(c) == 1
    s = s.replace(c, "    lk_keys_step(keys, lk_pads, &buttons);   /* LK_KEYS v1 */\n" + c, 1)
    open(p, "w").write(s)
    print("input.c patched:", VER)
