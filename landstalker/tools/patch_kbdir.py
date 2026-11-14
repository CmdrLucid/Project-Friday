#!/usr/bin/env python3
"""Keyboard directions are rebindable + one-press WASD layout (2026-11-14, question from a player via the user: 'remap movement from arrows to WASD?'; user: 'one press for WASD would be nice').
Options > Keybindings gets 4 rows Up / Down / Left / Right (keyboard only: the pad's D-pad and left stick stay fixed, the pad column shows 'DPAD'), a row 'WASD Keys'
(one press: W A S D = directions, J K L = Button A B C, U I = Quick 1 / 2, the rest as it is) and 'Reset Defaults' moves to the end (ids: 114..117 directions,
118 WASD Keys, 119 Reset Defaults).  Defaults stay the arrow keys, so nothing changes for players who do not touch it (old ~/.landstalker_keys files load unchanged:
the new actions never steal a key from the saved ones).
Safety net: an arrow key that no OTHER action uses always moves too, so a keyboard player can never lose movement (e.g. after binding Map onto a direction key, which
swaps the direction to Map's empty key).  The old fixed key S = Mega Drive Y (unused by Landstalker) is removed so S can be a direction.
The room map (patch_roommap.py) follows the bound direction keys as well (+ the arrows, nothing else uses them there).
Needs patch_options.py, patch_keys.py and patch_roommap.py before it.  Idempotent.  usage: patch_kbdir.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_KBDIR v1"

def rep(s, old, new, what):
    assert s.count(old) == 1, what + " layout changed: " + old[:80]
    return s.replace(old, new, 1)

# ---- input.c: 4 direction actions, keyboard -> MD directions, WASD preset ------------------------------------------
p = os.path.join(root, "src/input.c")
s = open(p).read()
if VER not in s:
    assert "LK_KEYS v1" in s and "LK_ROOMMAP v13" in s, "input.c: run patch_keys.py / patch_roommap.py first"
    s = rep(s, "LK_BSPRINT, LK_BMAP, LK_NB };", "LK_BSPRINT, LK_BMAP, LK_BUP, LK_BDOWN, LK_BLEFT, LK_BRIGHT, LK_NB };   /* " + VER + ": keyboard directions */", "input.c enum")
    s = rep(s, '"Sprint", "Map" };', '"Sprint", "Map", "Up", "Down", "Left", "Right" };', "input.c names")
    s = rep(s, '"sprint", "map" };', '"sprint", "map", "up", "down", "left", "right" };', "input.c ids")
    s = rep(s, "case LK_BSPRINT: return SDL_SCANCODE_LSHIFT; case LK_BMAP: return 0; }",
            "case LK_BSPRINT: return SDL_SCANCODE_LSHIFT; case LK_BMAP: return 0;\n                 case LK_BUP: return SDL_SCANCODE_UP; case LK_BDOWN: return SDL_SCANCODE_DOWN; case LK_BLEFT: return SDL_SCANCODE_LEFT; case LK_BRIGHT: return SDL_SCANCODE_RIGHT; }", "input.c defkey")
    # pad column of a direction row: the D-pad / stick, fixed
    s = rep(s, "void lk_bind_label(int i, char *o, size_t n) { char a[16], b[16]; lk_bind_init(); lk_bind_padlabel(lk_bind_pad[i], a, sizeof a);",
            "void lk_bind_label(int i, char *o, size_t n) { char a[16], b[16]; lk_bind_init(); lk_bind_padlabel(lk_bind_pad[i], a, sizeof a); if (i >= LK_BUP) snprintf(a, sizeof a, \"DPAD\");", "input.c label")
    # capture: a direction row takes keyboard keys only (pad presses are ignored, the capture keeps waiting)
    s = rep(s, "        else if (lk_raw_p > 0) { lk_bind_assign(lk_cap, 1, lk_raw_p); lk_cap = -1; got = 1; }",
            "        else if (lk_raw_p > 0 && lk_cap < LK_BUP) { lk_bind_assign(lk_cap, 1, lk_raw_p); lk_cap = -1; got = 1; }", "input.c rawpad")
    s = rep(s, "if (dn && !lk_cap_pp[c] && !(cc >= 12 && cc <= 15) && cc != 5) {",
            "if (dn && !lk_cap_pp[c] && !(cc >= 12 && cc <= 15) && cc != 5 && lk_cap < LK_BUP) {", "input.c cappad")
    # helpers (after lk_bind_assign)
    a = "/* pad state of a code */\n"
    s = rep(s, a, r'''/* LK_KBDIR v1: keyboard directions */
static int lk_kbdir_key(const uint8_t *keys, int dir) {   /* dir 0..3 = up, down, left, right: the bound key, or the arrow if no other action (direction or not) uses it */
    static const int arrow[4] = { SDL_SCANCODE_UP, SDL_SCANCODE_DOWN, SDL_SCANCODE_LEFT, SDL_SCANCODE_RIGHT };
    int k = lk_bind_key[LK_BUP + dir], free_arrow = 1;
    if (k > 0 && keys[k]) return 1;
    for (int j = 0; j < LK_NB; j++) if (j != LK_BUP + dir && lk_bind_key[j] == arrow[dir]) free_arrow = 0;
    return free_arrow && keys[arrow[dir]];
}
static uint16_t lk_kbdir_buttons(const uint8_t *keys) {
    uint16_t b = 0; lk_bind_init();
    if (lk_kbdir_key(keys, 0)) b |= GEN_BTN_UP;
    if (lk_kbdir_key(keys, 1)) b |= GEN_BTN_DOWN;
    if (lk_kbdir_key(keys, 2)) b |= GEN_BTN_LEFT;
    if (lk_kbdir_key(keys, 3)) b |= GEN_BTN_RIGHT;
    return b;
}
int lk_kbdir_down(int dir) { const uint8_t *ks = SDL_GetKeyboardState(NULL); lk_bind_init(); return ks && lk_kbdir_key(ks, dir); }   /* room map */
void lk_bind_wasd(void) {   /* Options > Keybindings > WASD Keys: one press; each key is taken with the swap rule, so whatever had it gets the old key of the new owner */
    static const int act[9] = { LK_BUP, LK_BLEFT, LK_BDOWN, LK_BRIGHT, LK_BA, LK_BB, LK_BC, LK_BQ1, LK_BQ2 };
    static const int key[9] = { SDL_SCANCODE_W, SDL_SCANCODE_A, SDL_SCANCODE_S, SDL_SCANCODE_D, SDL_SCANCODE_J, SDL_SCANCODE_K, SDL_SCANCODE_L, SDL_SCANCODE_U, SDL_SCANCODE_I };
    lk_bind_init();
    for (int i = 0; i < 9; i++) { int old = lk_bind_key[act[i]]; for (int j = 0; j < LK_NB; j++) if (j != act[i] && lk_bind_key[j] == key[i]) lk_bind_key[j] = old; lk_bind_key[act[i]] = key[i]; }
    lk_bind_save();
}
''' + a, "input.c helpers")
    # the fixed keyboard lines: arrows -> bindings, S (MD Y) removed
    s = rep(s, "    if (keys[SDL_SCANCODE_UP])     buttons |= GEN_BTN_UP;\n    if (keys[SDL_SCANCODE_DOWN])   buttons |= GEN_BTN_DOWN;\n    if (keys[SDL_SCANCODE_LEFT])   buttons |= GEN_BTN_LEFT;\n    if (keys[SDL_SCANCODE_RIGHT])  buttons |= GEN_BTN_RIGHT;\n",
            "    buttons |= lk_kbdir_buttons(keys);   /* " + VER + ": bound keyboard directions (Options > Keybindings) */\n", "input.c arrows")
    s = rep(s, "    if (keys[SDL_SCANCODE_S])      buttons |= GEN_BTN_Y;\n", "", "input.c S")
    open(p, "w").write(s)
    print("input.c patched:", VER)

# ---- platform_sdl.c: the room map's selection follows the bound direction keys --------------------------------------
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER not in s:
    s = rep(s, "int L = (cur >> SDL_CONTROLLER_BUTTON_DPAD_LEFT & 1) || ks[SDL_SCANCODE_LEFT], R = (cur >> SDL_CONTROLLER_BUTTON_DPAD_RIGHT & 1) || ks[SDL_SCANCODE_RIGHT], U = (cur >> SDL_CONTROLLER_BUTTON_DPAD_UP & 1) || ks[SDL_SCANCODE_UP], D = (cur >> SDL_CONTROLLER_BUTTON_DPAD_DOWN & 1) || ks[SDL_SCANCODE_DOWN];",
            "extern int lk_kbdir_down(int dir);   /* " + VER + " */\n            int L = (cur >> SDL_CONTROLLER_BUTTON_DPAD_LEFT & 1) || ks[SDL_SCANCODE_LEFT] || lk_kbdir_down(2), R = (cur >> SDL_CONTROLLER_BUTTON_DPAD_RIGHT & 1) || ks[SDL_SCANCODE_RIGHT] || lk_kbdir_down(3), U = (cur >> SDL_CONTROLLER_BUTTON_DPAD_UP & 1) || ks[SDL_SCANCODE_UP] || lk_kbdir_down(0), D = (cur >> SDL_CONTROLLER_BUTTON_DPAD_DOWN & 1) || ks[SDL_SCANCODE_DOWN] || lk_kbdir_down(1);",
            "platform_sdl.c roommap")
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)

# ---- func_table.c: the Keybindings page (Start menu tab + file select window) --------------------------------------
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    s = rep(s, "static const int lk_ids_key[15] = { 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114 };",
            "extern void lk_bind_wasd(void);   /* " + VER + " */\nstatic const int lk_ids_key[20] = { 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119 };   /* " + VER + ": + Up / Down / Left / Right 114..117, WASD Keys 118, Reset Defaults 119 */", "func_table.c ids")
    s = rep(s, "static const int lk_pg_cnt[LK_NPG + 1] = { 11, 6, 12, 3, 6, 8, 3, 15 };", "static const int lk_pg_cnt[LK_NPG + 1] = { 11, 6, 12, 3, 6, 8, 3, 20 };", "func_table.c count")
    s = rep(s, "    if (id == 114) return \">\";", "    if (id >= 118) return \">\";", "func_table.c bindtext")
    s = rep(s, "return id >= 100 ? (id == 114 ? \"Reset Defaults\" : lk_bind_name(id - 100))", "return id >= 100 ? (id == 119 ? \"Reset Defaults\" : id == 118 ? \"WASD Keys\" : lk_bind_name(id - 100))", "func_table.c rowname")
    s = rep(s, "if (id == 114) lk_bind_reset(); else {", "if (id == 119) lk_bind_reset(); else if (id == 118) lk_bind_wasd(); else {", "func_table.c change")
    s = rep(s, "lk_win_text(r, id == 114 ? \"Reset Defaults\" : lk_bind_name(id - 100),", "lk_win_text(r, id == 119 ? \"Reset Defaults\" : id == 118 ? \"WASD Keys\" : lk_bind_name(id - 100),", "func_table.c wintext")
    s = rep(s, "            else { lk_opt_change(lk_win_id(pg, row), 1); blink = 0; lk_win_value(pg, row); lk_snd(0x00FA54u); }",
            "            else { int wid = lk_win_id(pg, row); lk_opt_change(wid, 1); blink = 0; if (wid >= 118) lk_win_page(pg, row); else lk_win_value(pg, row); lk_snd(0x00FA54u); }   /* " + VER + ": WASD Keys / Reset change many rows */", "func_table.c winchange")
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
