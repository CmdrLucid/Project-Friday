#!/usr/bin/env python3
"""3D room (2026-10-24, optional, Options > Video > 3D Room, Off by default): the room as a 3D scene with a camera that turns with the right stick.
The module itself is tools/room3d_game.c (inserted into src/platform_sdl.c before lk_disp_present, after patch_hd.py's module: it draws through patch_hd's lk_hd_show);
this patch wires it: the present hook (before the HD present), the screenshot hook (LANDSTALKER_HD_SHOT frames also write r3dshot_*.png), the right stick / stick click
readers in src/input.c (lk_rs_x / lk_rs_y / lk_rs_click).  Needs patch_hd.py (LK_HD v3), patch_own.py (lk_o3d_* exports), patch_padthread.py and patch_runtime.py before it.
Idempotent.  usage: patch_room3d.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_R3D v1"
here = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(root, "src/platform_sdl.c")
s = open(p).read()
if VER in s:
    print("platform_sdl.c already patched:", VER)
else:
    assert "LK_HD v3" in s, "platform_sdl.c: run patch_hd.py (LK_HD v3) first"
    module = open(os.path.join(here, "room3d_game.c")).read()
    a = "/* draw the frame: returns after SDL_RenderPresent */\nstatic void lk_disp_present(const uint8_t *framebuffer) {"
    assert s.count(a) == 1, "platform_sdl.c: lk_disp_present layout changed"
    s = s.replace(a, module + "\n" + a, 1)
    h = "    if (lk_hd_active() && lk_hd_present(framebuffer, sw, &r)) {"
    assert s.count(h) == 1, "platform_sdl.c: HD present hook layout changed"
    s = s.replace(h, "    if (lk_r3d_present(framebuffer, sw, &r)) { lk_osd_draw(ow, oh); lk_coords_draw(oh); SDL_RenderPresent(s_renderer); return; }   /* LK_R3D v1 */\n" + h, 1)
    d1 = "    if (!lk_hd_active() && lk_hd_fxany()) framebuffer = (const uint8_t *)lk_hd_dof1x("
    assert s.count(d1) == 1, "platform_sdl.c: dof1x hook layout changed"
    s = s.replace(d1, "    extern int lk_r3d_on(void);\n    if (!lk_hd_active() && lk_hd_fxany() && !lk_r3d_on()) framebuffer = (const uint8_t *)lk_hd_dof1x(", 1)
    c = "static void lk_shot_frame(const uint8_t *framebuffer, long frame) {"
    assert s.count(c) == 1
    s = s.replace(c, "extern int lk_r3d_on(void); extern uint32_t *lk_r3d_assemble(const uint32_t *fb, int sw, int e, int *ow, int *oh);   /* LK_R3D v1 */\n" + c, 1)
    d = '    { const char *hl = getenv("LANDSTALKER_HD_SHOT");   /* LK_HD v1: the HD picture */'
    assert s.count(d) == 1, "platform_sdl.c: HD shot hook layout changed"
    s = s.replace(d, '''    { const char *rl = getenv("LANDSTALKER_HD_SHOT");   /* LK_R3D v1: the 3D room picture */
      if (rl && *rl && lk_r3d_on() && lk_shot_wanted(rl, frame)) { int iw3, ih3; uint32_t *im3 = lk_r3d_assemble((const uint32_t *)framebuffer, 320 + 2 * lk_wide_e, lk_wide_e, &iw3, &ih3); char p3[600]; snprintf(p3, sizeof p3, "%s/r3dshot_%06ld_w%d.png", dir, frame, iw3);
        { struct stat st3; if (stat(dir, &st3) != 0) { { extern int lk_mkdir(const char *); lk_mkdir(dir); } } }
        if (im3) printf("shot: %s %s (%dx%d 3D room)\\n", lk_shot_png(p3, im3, iw3, ih3, 1) ? "wrote" : "FAILED", p3, iw3, ih3); else printf("shot: no 3D picture at frame %ld (scene not ready / not a map frame)\\n", frame); } }
''' + d, 1)
    s = s + "\n/* " + VER + " */\n"
    open(p, "w").write(s)
    print("platform_sdl.c patched:", VER)
# right stick in input.c
pi = os.path.join(root, "src/input.c")
t = open(pi).read()
if "lk_rs_x" in t:
    print("input.c already patched: right stick")
else:
    g = "static uint16_t s_pad_state[2];"
    assert t.count(g) == 1, "input.c: layout changed (s_pad_state)"
    t = t.replace(g, "volatile int lk_rs_x, lk_rs_y, lk_rs_click;   /* right stick / its click: the 3D room camera (tools/patch_room3d.py) */\n" + g, 1)
    k = "    buttons |= platform_scripted_buttons();"
    assert t.count(k) == 1, "input.c: layout changed (scripted buttons)"
    t = t.replace(k, "    { lk_rs_x = lk_pad_axis(lk_pads, SDL_CONTROLLER_AXIS_RIGHTX); lk_rs_y = lk_pad_axis(lk_pads, SDL_CONTROLLER_AXIS_RIGHTY); lk_rs_click = lk_pad_button(lk_pads, SDL_CONTROLLER_BUTTON_RIGHTSTICK); }   /* LK_R3D v1 */\n" + k, 1)
    open(pi, "w").write(t)
    print("input.c patched: right stick")

# camera relative controls: wrapper of HandleDirectionalInput $0018C4 in func_table.c (REMAKE rule layer, first logic change; Off = the original game)
pf = os.path.join(root, "src/func_table.c")
f = open(pf).read()
VER2 = "LK_CAMCTL v1"
if VER2 in f:
    print("func_table.c already patched:", VER2)
else:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert f.count(a) == 1, "func_table.c: layout changed (lk_strip_extend)"
    h = "        lk_gaia_install();   /* LK_GAIA v1 */\n"
    assert f.count(h) == 1, "func_table.c: install chain layout changed (lk_gaia_install)"
    module = r'''/* ---- LK_CAMCTL v1: camera relative controls (tools/patch_room3d.py, rules of the remake option; tools/room3d_game.c lk_camctl_nibble) ---- */
extern int lk_camctl_nibble(int nib);
static gen_func_t lk_o_hdi;
static void lk_h_hdi(void) {   /* HandleDirectionalInput $0018C4: the d-pad nibble of g_Controller1State $FF0F8E is replaced for the duration of the call, never for the menus */
    uint8_t c = bus_read8(0xFF0F8Eu); int nib = c & 0x0F, r;
    if (nib && bus_read16(0xFF12DEu) == 0 && (r = lk_camctl_nibble(nib)) >= 0 && r != nib) {
        bus_write8(0xFF0F8Eu, (uint8_t)((c & 0xF0) | r)); lk_o_hdi(); bus_write8(0xFF0F8Eu, c); return;
    }
    lk_o_hdi();
}
static void lk_camctl_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_o_hdi = func_table_lookup(0x0018C4);
    if (lk_o_hdi) func_table_register(0x0018C4, lk_h_hdi); else fprintf(stderr, "camctl: HandleDirectionalInput not found\n");
}
'''
    f = f.replace(a, module + a, 1)
    f = f.replace(h, h + "        lk_camctl_install();   /* LK_CAMCTL v1 */\n", 1)
    open(pf, "w").write(f)
    print("func_table.c patched:", VER2)
