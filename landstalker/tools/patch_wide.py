#!/usr/bin/env python3
"""Widescreen experiment: render the VDP picture wider than 320 pixels.
LANDSTALKER_WIDE=<e>  (pixels added on EACH side, rounded down to a multiple of 16, 0..48, default 0 = unchanged picture). e=16 -> 352 px (1.57, almost 16:10 = Steam Deck), e=32 -> 384 px (1.71, almost 16:9), e=48 -> 416 px (1.86).
Alternatively a third number in ~/.landstalker_display ("<scale> <filter> <e>"); the environment variable wins. Restart the game to change it.

How it works (GPGX renderer, all of it is a no-op for e = 0):
 * viewport width = 320 + 2e (genrecomp.c sets it every frame; the draw loop and the present buffer allow the larger width)
 * both scroll planes: the horizontal scroll value gets +e, so the original 320 pixels stay in the centre and the planes' neighbouring columns show on both sides
 * sprites: x position + e
 * margins: blanked (border colour) on lines of the window plane (HUD, text boxes) and on every frame that is not the game map (UpdateSprites $0178C8 not run in the last 4 frames: menus, title, cutscenes); LANDSTALKER_WIDE_MAP=always|never|auto:N and LANDSTALKER_WIDE_DEBUG=1 for troubleshooting, FRAGILE heuristic, see docs/DEBUGGING.md 'Widescreen: map-frame detection'
 * window plane (HUD / text boxes if the game uses it): its limits (window_clip) grow by the margin cells and its columns keep their place relative to the original 320 px; its margin cells are empty (transparent).
   Use e = 16 / 32 / 48 (multiples of 16 px) so that the window cells line up exactly with the planes.
 * NOT handled yet: per-column vertical scroll alignment. The game only fills tile columns / sprites for its own 320 px,
   so the new edges show whatever is in the planes there (often stale tiles) and sprites pop in at the edge. This is an experiment to see how much the game already provides.
Invariant checked by tools/widetest: with the same VDP state the centre of the wide picture is pixel-identical to the normal picture.
Idempotent.  usage: patch_wide.py path/to/genrecomp"""
import os, re, sys
root = sys.argv[1]

# ---- core/vdp_render.c ---------------------------------------------------------
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if "LANDSTALKER_WIDE" not in s:
    a = '#include "shared.h"\n'
    assert s.count(a) == 1, "vdp_render.c: include layout changed"
    ctor = r'''
/* LANDSTALKER_WIDE: extra picture width in pixels per side (see tools/patch_wide.py) */
#include <stdlib.h>
#include <stdio.h>
int lk_wide_e = 0;
__attribute__((constructor)) static void lk_wide_init(void)
{
  int v = 0;
  const char *e = getenv("LANDSTALKER_WIDE");
  if (e && *e) v = atoi(e);
  else {
    const char *h = getenv("HOME"); char path[600]; int a = 0, b = 0, c = 0;
    snprintf(path, sizeof(path), "%s/.landstalker_display", h ? h : ".");
    FILE *f = fopen(path, "r");
    if (f) { if (fscanf(f, "%d %d %d", &a, &b, &c) == 3) v = c; fclose(f); }
  }
  if (v < 0) v = 0;
  if (v > 48) v = 48;
  lk_wide_e = v & ~15;   /* whole 16 px cells: the window plane only lines up with the planes then */
}
/* window plane column (16 px cells) for a screen cell: the window keeps its place relative to the original 320 px, its margin cells are empty (transparent) */
static inline int lk_wmargin(int c)
{
  if (!(reg[12] & 1) || !lk_wide_e) return 0;
  c -= lk_wide_e >> 4;
  return c < 0 || c > 19;
}
'''
    s = s.replace(a, a + ctor, 1)
    pat = re.compile(r"^(\s*uint32 xscroll\s*=\s*\*\(uint32 \*\)&vram\[hscb \+ \(\(line & hscroll_mask\) << 2\)\];)\s*$", re.M)
    n1 = len(pat.findall(s))
    assert n1 >= 5, "vdp_render.c: expected the xscroll fetch in the render_bg variants, found %d" % n1
    s = pat.sub(lambda m: m.group(1) + "\n  xscroll = (((xscroll >> 16) + (uint32)lk_wide_e) << 16) | ((xscroll + (uint32)lk_wide_e) & 0xFFFFu);   /* LANDSTALKER_WIDE: both planes shift right by e; each 16-bit half separately (a plain += carried from the plane B half into plane A when B was in -e..-1: plane A 1 px off at the map corners, user report 2026-10-11) */", s)
    pw = re.compile(r"^(\s*)atbuf = nt\[column\];\s*\n(\s*)(DRAW_COLUMN(?:_IM2)?)\(atbuf, v_line\)", re.M)
    n3 = len(pw.findall(s))
    assert n3 >= 5, "vdp_render.c: expected the window column fetch, found %d" % n3
    s = pw.sub(lambda m: m.group(1) + "if (lk_wmargin(column)) { *dst++ = 0; *dst++ = 0; *dst++ = 0; *dst++ = 0; }   /* LANDSTALKER_WIDE: empty margin cell */\n" + m.group(1) + "else { atbuf = nt[column - (lk_wide_e >> 4) * ((reg[12] & 1) ? 1 : 0)];\n" + m.group(2) + m.group(3) + "(atbuf, v_line) }", s)
    wc_old = "  sw = 16 + (sw << 2);\n"
    assert s.count(wc_old) == 1, "vdp_render.c: window_clip layout changed"
    wc_new = "  int lk_m = 0, lk_x = 0;   /* LANDSTALKER_WIDE: margin cells on the left / extra cells in total */\n  if (sw && lk_wide_e) { lk_m = lk_wide_e >> 4; lk_x = lk_wide_e >> 3; }\n" + wc_old
    s = s.replace(wc_old, wc_new, 1)
    i0 = s.index("void window_clip(unsigned int data, unsigned int sw)")
    i1 = s.index("void render_init(void)")
    body = s[i0:i1]
    assert body.count("clip[w].right = sw;") == 1 and body.count("clip[a].right = sw;") == 2 and body.count("clip[a].left = clip[w].right = hp;") == 1, "window_clip statements changed"
    body = body.replace("clip[w].right = sw;", "clip[w].right = sw + lk_x;").replace("clip[a].right = sw;", "clip[a].right = sw + lk_x;").replace("clip[a].left = clip[w].right = hp;", "clip[a].left = clip[w].right = hp + lk_m;")
    s = s[:i0] + body + s[i1:]
    # black margins: on screens that are not the game map and on lines where the window plane (HUD, text boxes) is active
    clean = r'''/* LANDSTALKER_WIDE_CLEAN=1 | <hex,hex..>: called when the game enters ClearScrollPlanes ($000B38) / LoadRoom ($002996) (or the listed functions): empty the WHOLE name tables of plane A and B (the game may clear only part of them,
   which would leave columns of the previous room in the new margins). Size = rows x row stride from the plane layout registers (64x32 -> 0x1000 each). */
void lk_clean_planes(void)
{
  unsigned int size = (((unsigned int)playfield_row_mask + 1) >> 3) << playfield_shift;
  if (size > 0x2000) size = 0x2000;
  if (size && ntab + size <= 0x10000) memset(&vram[ntab], 0, size);
  if (size && ntbb + size <= 0x10000) memset(&vram[ntbb], 0, size);
}

'''
    rl = "void render_line(int line)\n{\n"
    assert s.count(rl) == 1, "vdp_render.c: render_line layout changed"
    helper2 = r'''/* LANDSTALKER_WIDE: margins are blanked (border colour) on lines that belong to the window plane and on every frame that is not the game map.
   Map frame = UpdateSprites ($0178C8) ran within the last 4 frames (lk_world_frame is set in func_table.c at every call of it) OR the text-box routine $028FD8 is on the call stack (NPC dialogue: UpdateSprites is not called during dialogues, or the call that started the dialogue is still on the stack) OR WarpToRoom ($00620E) or UpdateSprites itself is on the call stack (cutscene scripts run inside UpdateSprites and wait there between text boxes); 30-frame hold after the last stack hit.
   LANDSTALKER_WIDE_DIALOG_FN=<hex> changes the dialogue marker function (0 = rule off).
   LANDSTALKER_WIDE_MAP=auto (default) | always (treat every frame as map: margins show plane content everywhere, except window lines) | never (all margins black)
   LANDSTALKER_WIDE_MAP=auto:N  changes the frame threshold (default 4)
   LANDSTALKER_WIDE_DEBUG=1 prints every switch between "map" and "not map" and (while not map) a sample every ~1.5 s, each with the game's call stack and the number of plane tiles written since the last report (max 400 lines).  See docs/DEBUGGING.md "Widescreen: map-frame detection". */
extern long platform_frame_number(void);
extern long lk_world_frame;
extern int lk_picture;
extern int lk_load_fade;   /* func_table.c (lk_strip_extend): the fade-in after a save was loaded runs (FadeFromBlack $00098A after the LoadRoom path) */
extern unsigned long lk_nt_writes;                     /* vdp_ctrl.c: writes to the nametables of plane A / B */
extern void func_table_dump_stack(FILE *f);
static unsigned long lk_nt_last;
static long lk_map_sample;
extern int func_table_depth(void);
extern uint32_t func_table_stack(int k);
static long lk_dlg_fn = 0x028FD8;                       /* text-box print routine: on the call stack during every NPC dialogue (US ROM) */
static long lk_dlg_frame = -1, lk_dlg_last = -100000; static int lk_dlg, lk_fm; static int lk_wfx;   /* the warp pad effect (HandleFloorWarpPad $0062EA / WarpPadFx $00E154) is on the call stack: the own renderer does not draw it, the game's picture stays */
static int lk_menu_seen;   /* an inner call of CheckForMenuOpen $007624 into the inventory code ($00D000..$00FFFF: item / equip screen) ran since the map was last on screen: a menu screen was shown */   /* lk_fm: the map is fading out into / in from the Start menu (no grace period) */   /* lk_dlg_last: last frame with the text-box routine on the stack (grace period after the dialogue, see DEBUGGING.md 'flicker after dialogue') */
static int lk_map_mode = -1, lk_map_frames = 4, lk_map_prev = -1, lk_map_dbg, lk_map_lines; static int lk_map_dbgint = 90;   /* LANDSTALKER_WIDE_DBGINT=N: sample interval (frames) of the 'not map' debug lines */
static void lk_map_init(void)
{
  const char *m = getenv("LANDSTALKER_WIDE_MAP");
  lk_map_mode = 0;
  if (m && !strncmp(m, "always", 6)) lk_map_mode = 1;
  else if (m && !strncmp(m, "never", 5)) lk_map_mode = 2;
  else if (m && !strncmp(m, "auto:", 5) && atoi(m + 5) > 0) lk_map_frames = atoi(m + 5);
  { const char *d = getenv("LANDSTALKER_WIDE_DIALOG_FN"); if (d && *d) lk_dlg_fn = strtol(d, NULL, 16); }   /* 0 = dialogue rule off */
  lk_map_dbg = getenv("LANDSTALKER_WIDE_DEBUG") != NULL;
  { const char *di = getenv("LANDSTALKER_WIDE_DBGINT"); if (di && atoi(di) > 0) lk_map_dbgint = atoi(di); }
}
/* map-frame decision (shared with LANDSTALKER_TALL, tools/patch_tall.py) */
int lk_map_decide(void)
{
  int map;
  if (lk_map_mode < 0) lk_map_init();
  if (platform_frame_number() != lk_dlg_frame)                                      /* once per frame: is the text-box routine on the game's call stack? */
  {
    int i, d = func_table_depth();
    lk_dlg_frame = platform_frame_number(); lk_dlg = 0; lk_wfx = 0;
    if (lk_dlg_fn > 0) for (i = 0; i < d; i++) { uint32_t fnx = func_table_stack(d - 1 - i); if (fnx == (uint32_t)lk_dlg_fn || fnx == 0x00620Eu || fnx == 0x0178C8u || fnx == 0x0066ACu || fnx == 0x010ACEu || fnx == 0x00610Au || fnx == 0x00613Eu || fnx == 0x006184u || fnx == 0x0061CAu || fnx == 0x016712u || ((fnx == 0x0062EAu || fnx == 0x00E154u) ? (lk_wfx = 1) : 0) || fnx == 0x0062EAu || fnx == 0x00E154u || (lk_load_fade && (fnx == 0x00098Au || fnx == 0x0009AAu))) { lk_dlg = 1; break; } }   /* FadeFromBlack $00098A (its fade loop $0009AA is entered by a bra, so the stack shows that one) right after loading a save (lk_load_fade): the start room fades in, it is a map (otherwise the full-height band / margins popped in at the end of the fade, 2026-10-11 night) */   /* LoadPlayerSpecialAnimation $010ACE: the death / Friday revive animation (user report 2026-10-12: margins went black for ~145 frames while dying) */   /* ProcessActionButton $0066AC: opening a chest / item pickup text ('Found X.'), user report 2026-10-11: margins went black */   /* text box OR WarpToRoom ($00620E: fade out / load / fade in of a room change: the picture is a real map, so the margins must not be black during the fade-in, user report 2026-10-10) OR still INSIDE UpdateSprites ($0178C8: a cutscene script started by an entity waits between its text boxes, e.g. the intro of a fresh game; it never returns to the game loop, so 'called within 4 frames' runs out, user report 2026-10-10 night) */
    lk_fm = 0;   /* Start menu: FadeOutToDarkness inside CheckForMenuOpen $007624 = the map fades out (still the map), FadeInFromDarkness inside $007766 = the map fades in again after the menu */
    for (i = 0; i + 1 < d; i++) { uint32_t a0 = func_table_stack(d - 1 - i), a1 = func_table_stack(d - 2 - i); if (a0 == 0x0016DCu && a1 == 0x0009A8u) { lk_fm = 1; break; } if (a0 == 0x0016DCu && a1 == 0x008EB4u) { lk_dlg = 1; break; } if (a0 == 0x007624u && a1 == 0x008EF4u) { lk_fm = !lk_menu_seen; break; } if (a0 == 0x007624u && a1 >= 0x00D000u && a1 < 0x010000u) lk_menu_seen = 1; if ((a0 == 0x007766u || a0 == 0x00776Eu) && a1 == 0x008EB4u) { lk_dlg = 1; lk_menu_seen = 0; break; } }   /* the menu's own fade-out (after the item / equip screen was shown: lk_menu_seen) is NOT the map any more: the margins stay black (no blue window band over them); the fade-in after the menu is called from $00776E in this build (the old $007766 never matched: the margins came 20 frames late) */
    if (platform_frame_number() - lk_world_frame <= lk_map_frames) lk_menu_seen = 0;   /* fade-out: no grace period (the menu follows); fade-in: with the grace period (the first UpdateSprites pass comes 2 frames after the fade returns) */
    if (lk_dlg) lk_dlg_last = lk_dlg_frame;
  }
  map = (lk_map_mode == 1) ? 1 : (lk_map_mode == 2 || lk_picture) ? 0 : (lk_dlg || lk_fm || platform_frame_number() - lk_dlg_last <= 30 || platform_frame_number() - lk_world_frame <= lk_map_frames);
  return map;
}
int lk_warpfx(void) { lk_map_decide(); return lk_wfx; }   /* tools/patch_own.py */
static void lk_wide_margins(int line)
{
  int e = lk_wide_e, w = bitmap.viewport.w, mk, map;
  if (!e || !(reg[12] & 1) || w < 320 + 2 * e) return;
  map = lk_map_decide();
  if (lk_map_dbg && lk_map_lines < 400 && (map != lk_map_prev || (!map && line == 0 && platform_frame_number() - lk_map_sample >= lk_map_dbgint) || (map && lk_dlg && line == 0 && platform_frame_number() - lk_map_sample >= 300)))
  {
    /* transition, or (while not map) a sample about every 1.5 s: which game function is running (shadow call stack) and how many plane tiles were written since the last line */
    lk_map_lines++; lk_map_sample = platform_frame_number();
    printf("widemap: frame %ld line %d: %s%s%s (last UpdateSprites at frame %ld, plane-tile writes since last report %lu, reg11=%02X reg18=%02X) ", platform_frame_number(), line, map ? "MAP" : "not map", lk_dlg ? " [dialogue]" : "", map == lk_map_prev ? " [sample]" : "", lk_world_frame, lk_nt_writes - lk_nt_last, reg[11], reg[18]);
    lk_nt_last = lk_nt_writes;
    func_table_dump_stack(stdout);
    fflush(stdout);
  }
  lk_map_prev = map;
  if (!map) mk = 3;                                                                /* menu, title, cutscene ...: the margins stay black */
  else
  {
    int a = (reg[18] & 0x1F) << 3, wv = (reg[18] >> 7) & 1;
    if (wv == (line >= a)) mk = 3;                                                 /* window takes the whole line */
    else mk = clip[1].enable ? ((clip[1].left == 0 ? 1 : 0) | (clip[1].right >= 20 + (e >> 3) ? 2 : 0)) : 0;   /* window shares the line: its side gets a black margin */
  }
  if (mk & 1) memset(&linebuf[0][0x20], 0x40, e);
  if (mk & 2) memset(&linebuf[0][0x20 + w - e], 0x40, e);
}

'''
    s = s.replace(rl, clean + helper2 + rl, 1)
    ro = "    /* Render sprite layer */\n    render_obj(line & 1);\n"
    assert s.count(ro) == 1, "vdp_render.c: render_obj call layout changed"
    s = s.replace(ro, ro + "    lk_wide_margins(line);   /* LANDSTALKER_WIDE */\n", 1)
    n2 = s.count("xpos = xpos - 0x80;")
    assert n2 >= 3, "vdp_render.c: expected the sprite x offset in render_obj, found %d" % n2
    s = s.replace("xpos = xpos - 0x80;", "xpos = xpos - 0x80 + lk_wide_e;   /* LANDSTALKER_WIDE */")
    open(p, "w").write(s)
    print("vdp_render.c patched: LANDSTALKER_WIDE (%d scroll fetches, %d window column fetches, %d sprite offsets)" % (n1, n3, n2))
else:
    print("vdp_render.c already patched: LANDSTALKER_WIDE")

# ---- src/genrecomp.c and src/bus.c (the viewport width is latched in several places: per frame, per line) ----------
def add_extern(s):
    if "extern int lk_wide_e;" in s: return s
    idx = [m.end() for m in re.finditer(r"^#include [^\n]*\n", s, re.M)]
    assert idx, "no #include found"
    return s[:idx[-1]] + "extern int lk_wide_e;   /* LANDSTALKER_WIDE (vdp_render.c) */\n" + s[idx[-1]:]

for rel in ("src/genrecomp.c", "src/bus.c"):
    p = os.path.join(root, rel)
    s = open(p).read()
    if "lk_wide_e" in s:
        print(rel, "already patched: LANDSTALKER_WIDE"); continue
    n_a = s.count("(reg[12] & 0x01) ? 320 : 256")
    s = s.replace("(reg[12] & 0x01) ? 320 : 256", "(reg[12] & 0x01) ? 320 + 2 * lk_wide_e : 256")
    n_b = len(re.findall(r"(viewport\.w|vp_w) <= 320\b", s))
    s = re.sub(r"(viewport\.w|vp_w) <= 320\b", r"\1 <= 320 + 2 * lk_wide_e", s)
    if rel == "src/genrecomp.c":
        assert n_a >= 1 and n_b >= 1, "genrecomp.c: expected the width latch and the draw-loop condition (%d, %d)" % (n_a, n_b)
        def rep(old, new):
            global s
            assert s.count(old) == 1, "genrecomp.c layout changed: %r" % old[:60]
            s = s.replace(old, new, 1)
        rep("static uint8_t s_present_buf[GEN_RENDER_WIDTH * GEN_RENDER_HEIGHT * 4];", "static uint8_t s_present_buf[(GEN_RENDER_WIDTH + 128) * GEN_RENDER_HEIGHT * 4];   /* LANDSTALKER_WIDE: up to 448 px */")
        rep("int copy_w = (vp_w > GEN_RENDER_WIDTH) ? GEN_RENDER_WIDTH : vp_w;", "const int lk_stride = GEN_RENDER_WIDTH + 2 * lk_wide_e;\n    int copy_w = (vp_w > lk_stride) ? lk_stride : vp_w;")
        rep("if (copy_w < GEN_RENDER_WIDTH) memset(", "if (copy_w < lk_stride) memset(")
        rep("memcpy(s_present_buf + y * GEN_RENDER_WIDTH * 4,", "memcpy(s_present_buf + y * lk_stride * 4,")
    else:
        assert n_a >= 1 and n_b >= 1, "bus.c: expected the width latch and the draw condition (%d, %d)" % (n_a, n_b)
    s = add_extern(s)
    open(p, "w").write(s)
    print(rel, "patched: LANDSTALKER_WIDE (%d width latches, %d width conditions)" % (n_a, n_b))


# ---- src/func_table.c: shadow call stack accessors (shared with patch_vdplog.py) ----------------------------------------
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
anchor = "void func_table_dump_stack(FILE *f) {"
assert s.count(anchor) == 1, "func_table.c layout changed"
if "uint32_t func_table_stack(" not in s:
    s = s.replace(anchor, "/* LANDSTALKER_WIDE / VDPLOG: k-th entry from the top of the shadow call stack (0 = innermost), 0 if none */\nuint32_t func_table_stack(int k) { int i = s_call_depth - 1 - k; return (i >= 0 && i < 512) ? s_stack[i] : 0; }\n\n" + anchor, 1)
if "int func_table_depth(" not in s:
    s = s.replace(anchor, "int func_table_depth(void) { return s_call_depth < 512 ? s_call_depth : 512; }\n\n" + anchor, 1)
open(p, "w").write(s)

# ---- src/func_table.c: UpdateSprites ($0178C8) marks "game map frame" ------------------------------------------------
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if "lk_world_frame" not in s:
    a = "        lk_entry_dump(m68k_addr, ret); /* LANDSTALKER_ENTRYDUMP */\n"
    assert s.count(a) == 1, "func_table.c: entry hook layout changed"
    s = s.replace(a, "        if (m68k_addr == 0x0389D4 || m68k_addr == 0x03E654 || m68k_addr == 0x09EBE0) lk_picture = 1; else if (m68k_addr == 0x002996 || m68k_addr == 0x00620E || m68k_addr == 0x006212 || m68k_addr == 0x0178C8) lk_picture = 0;   /* $006212 = WarpToRoom+4: CSA_00D3 (island map -> ship) enters there, UpdateSprites is already on the stack, so the picture flag stayed set for ~45 frames of the ship fade-in (margins / band black, no band reload; user recording 2026-10-16) */   /* LANDSTALKER_WIDE: full-screen picture (DisplayLithograph $0389D4, DisplayIslandMap $03E654) until the next room load or the next UpdateSprites pass (the cutscene that showed it has ended) */\n        if (m68k_addr == 0x0178C8) lk_world_frame = platform_frame_number();   /* LANDSTALKER_WIDE: UpdateSprites runs only on game map frames */\n        { static int nclean = -1; static uint32_t cleanfn[6]; if (nclean < 0) { const char *c = getenv(\"LANDSTALKER_WIDE_CLEAN\"); nclean = 0; if (c && *c) { if (c[0] == '1' && !c[1]) { cleanfn[nclean++] = 0x000B38; cleanfn[nclean++] = 0x002996; } else { char *e2; while (*c && nclean < 6) { cleanfn[nclean++] = (uint32_t)strtoul(c, &e2, 16); if (*e2 != ',') break; c = e2 + 1; } } } } for (int ci = 0; ci < nclean; ci++) if (m68k_addr == cleanfn[ci]) { lk_clean_planes(); break; } }   /* LANDSTALKER_WIDE_CLEAN=1 (= $000B38 ClearScrollPlanes + $002996 LoadRoom) or a comma separated hex list of function entries */\n" + a, 1)
    s = s.replace("static uint32_t s_tail;", "extern void lk_clean_planes(void);\nstatic uint32_t s_tail;", 1)
    b = "static uint32_t s_tail;"
    assert s.count(b) == 1, "func_table.c: anchor layout changed"
    s = s.replace(b, "long lk_world_frame = -1000;   /* frame of the last UpdateSprites call (LANDSTALKER_WIDE margins) */\nint lk_picture;   /* a full-screen picture (lithograph, island map) is shown: never a map frame (tools/patch_wide.py) */\n" + b, 1)
    open(p, "w").write(s)
    print("func_table.c patched: lk_world_frame")
else:
    print("func_table.c already patched: lk_world_frame")

# ---- vdp_ctrl.c: count writes to the plane nametables (LANDSTALKER_WIDE_DEBUG evidence) ----------------------------------
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_ctrl.c")
s = open(p).read()
if "lk_nt_writes" not in s:
    a = "static void vdp_bus_w(unsigned int data)\n{\n"
    assert s.count(a) == 1, "vdp_ctrl.c: vdp_bus_w layout changed"
    s = s.replace(a, "/* LANDSTALKER_WIDE: number of VRAM writes into the plane A / plane B name tables (cheap counter for the map-frame diagnostics) */\nunsigned long lk_nt_writes;\nstatic inline void lk_nt_count(int index)\n{\n  if ((index >= ntab && index < ntab + 0x2000) || (index >= ntbb && index < ntbb + 0x2000)) lk_nt_writes++;\n}\n\n" + a, 1)
    b = "      /* VRAM address */\n      int index = addr & 0xFFFE;\n"
    i0 = s.index("static void vdp_bus_w(unsigned int data)\n{\n")
    i1 = s.index(b, i0)
    s = s[:i1] + b + "      lk_nt_count(index);   /* LANDSTALKER_WIDE */\n" + s[i1 + len(b):]
    open(p, "w").write(s)
    print("vdp_ctrl.c patched: lk_nt_writes")
else:
    print("vdp_ctrl.c already patched: lk_nt_writes")

# native VRAM word write used by the private strip queue (LANDSTALKER_WIDE_STRIPS): same effect as a 68K data port word write into VRAM, but without FIFO / CPU stall / cycles
s = open(p).read()
if "lk_vram_put_word" not in s:
    a2 = "static void vdp_bus_w(unsigned int data)\n{\n"
    assert s.count(a2) == 1, "vdp_ctrl.c: vdp_bus_w layout changed (put_word)"
    fn = ("/* LANDSTALKER_WIDE_STRIPS: write one 16-bit word into VRAM like vdp_bus_w does (no FIFO, no stall) */\n"
          "void lk_vram_put_word(unsigned int a, unsigned int data)\n{\n"
          "  int index = a & 0xFFFE; int name; uint16 *p = (uint16 *)&vram[index];\n"
          "  data &= 0xFFFF;\n"
          "  if ((index & sat_base_mask) == satb) *(uint16 *) &sat[index & sat_addr_mask] = data;\n"
          "  if (data != *p) { *p = data; MARK_BG_DIRTY (index); }\n"
          "  lk_nt_count(index);\n}\n\n")
    s = s.replace(a2, fn + a2, 1)
    fn2 = ("/* LANDSTALKER_WIDE (runtime switch): recompute the window plane clipping with the current width (it is normally only computed when the game writes registers 12/17) */\n"
           "void lk_wide_refresh(void)\n{\n  window_clip(reg[17], reg[12] & 1);\n}\n\n")
    s = s.replace(a2, fn2 + a2, 1)
    open(p, "w").write(s)
    print("vdp_ctrl.c patched: lk_vram_put_word")

# ---- bus.c: the widescreen strip extension must not cost emulated 68K time (LANDSTALKER_FREECYCLES) -------------------------------------
# Without this the extra loader runs (and the extra blocks the game's own FlushVdpWriteQueue copies in VBlank) slow the GAME down while scrolling (user: WIDE=32/48 clearly slower than WIDE=0).
# lk_no_charge: bus_charge() ignores everything (set around the extension run); lk_free_mclk: credit that the next charges consume first (refund for the flush of the extra blocks).
p = os.path.join(root, "src/bus.c")
b = open(p).read()
if "lk_no_charge" not in b:
    old = "static void bus_charge(unsigned int mclk) {\n    unsigned int steal = 0;\n"
    assert b.count(old) == 1, "bus.c: bus_charge layout changed (patch_timing must run first)"
    new = "int lk_no_charge; unsigned int lk_free_mclk;   /* LANDSTALKER_FREECYCLES (patch_wide.py) */\nstatic void bus_charge(unsigned int mclk) {\n    unsigned int steal = 0;\n    if (lk_no_charge) return;\n    if (lk_free_mclk) { unsigned int t = mclk < lk_free_mclk ? mclk : lk_free_mclk; lk_free_mclk -= t; mclk -= t; if (!mclk) return; }\n"
    b = b.replace(old, new, 1)
    open(p, "w").write(b)
    print("bus.c patched: LANDSTALKER_FREECYCLES")

# ---- func_table.c: LANDSTALKER_WIDE_STRIPS -- widen the isometric map loader ---------------------------------------------
# The game streams map blocks only in a diamond of radius 11 around the camera ($FF1124/$FF1125, strips $00A61C top, $00A698 bottom, $00A6B0 left, $00A730 right).
# Every time one of the four strip loaders is entered we additionally run it k = LANDSTALKER_WIDE_STRIPS times (default e/16) with the camera shifted outward
# (two shifts per step, one per axis, so the whole edge of the bigger diamond is covered). Registers/flags are saved and restored. 0 = off.
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if "lk_strip_extend" in s:
    print("func_table.c already patched: lk_strip_extend")
else:
    helper = r'''extern int lk_wide_e;
extern int lk_picture;   /* full-screen picture shown (lithograph, island map): the FadeIn strip hack must not overwrite it */
extern bool func_table_jsr(uint32_t m68k_addr, uint32_t ret);
extern void lk_vram_put_word(unsigned int a, unsigned int data);   /* vdp_ctrl.c */
extern int lk_no_charge;                                           /* bus.c: bus_charge ignores everything while set */
extern int lk_tall_kv(void) __attribute__((weak));                /* LANDSTALKER_TALL (vdp_render.c, tools/patch_tall.py) */
/* LANDSTALKER_WIDE_STRIPS (see tools/patch_wide.py): run the map strip loaders for a bigger diamond.
   The extra strips must not influence the GAME at all (user: slower game, different NPC/player timing), so:
   - the loader runs with lk_no_charge (no emulated 68K time),
   - the entries it appends to the game's VDP write queue ($FF3900.., pointer $FF1840, count byte $FF1128) are MOVED into a private buffer and the pointer / count are restored,
   - the private buffer is written natively into VRAM when the game enters FlushVdpWriteQueue ($002686), i.e. right before its own entries (same order as before). */
int lk_load_fade;   /* FadeFromBlack $00098A after a save load is running (map-frame rule, vdp_render.c) */
int lk_wide_refill;   /* set by platform_display_cycle_wide() when the width grows */
static void lk_strip_extend(uint32_t a);
static int32_t lk_blk_delta;
static int lk_d2_shift, lk_d2_shift_x, lk_d2_shift_y;
#define LK_EXT_CAP 600000                                          /* words (1.2 MB); one extension call with k=4 adds 4*2*12 blocks * 12 words = 1152; a room load calls the strip loaders hundreds of times without a flush (24000 was too small: margins stayed black after a room change) */
static uint16_t lk_ext_w[LK_EXT_CAP]; static int lk_ext_n;
static void lk_ext_apply(void)   /* apply the private strip entries (word = VRAM command high word, then two tile words) */
{
    int i;
    for (i = 0; i + 2 < lk_ext_n; i += 3) {
        unsigned hi = lk_ext_w[i];
        if ((hi >> 14) != 1) continue;                         /* only VRAM writes */
        unsigned addr = (hi & 0x3FFF) | 0xC000;                /* the second command word is always $0003 in the game's flush loop */
        lk_vram_put_word(addr, lk_ext_w[i + 1]); lk_vram_put_word((addr + 2) & 0xFFFF, lk_ext_w[i + 2]);
    }
    lk_ext_n = 0;
}
static void lk_strip_extend(uint32_t a)
{
    static int busy, kenv = -2; int k;
    int dx[2], dy[2], j, v, ns = 0, sx[32], sy[32], kv = lk_tall_kv ? lk_tall_kv() : 0;   /* kv: LANDSTALKER_TALL extra steps below the picture (tools/patch_tall.py; weak, 0 when absent or off) */
    { static int pending;   /* LANDSTALKER_TALL: the band below the picture is not covered by the room load; reload the extra strips when the fade-in STARTS, so it is complete before anything is visible.
         Room change: FadeInFromDarkness $008EB4 (always, as before). Start from the file select: StartGame ends in FadeFromBlack $00098A (it never calls $008EB4; black rectangles until the first step, user report 2026-10-11, church of save 1); only after a LoadRoom-path entry $002824 (pending), FadeFromBlack has other callers.
         (2026-10-11 night: a reload 10 frames after the first UpdateSprites pass fixed the file-select start but was too late for room changes: holes during every fade-in, user report.) */
      if (getenv("LANDSTALKER_TALL_DEBUG") && (a == 0x002824 || a == 0x008EB4 || a == 0x00098A)) printf("tall: hook $%06X frame %ld picture=%d pending=%d\n", a, platform_frame_number(), lk_picture, pending);
      if (a == 0x002824 && !lk_picture) { pending = 1; return; }
      if (a == 0x0178C8) lk_load_fade = 0;
      if (a == 0x0178C8 && pending && kv > 0 && !lk_picture) { pending = 0; lk_wide_refill = 1; if (getenv("LANDSTALKER_TALL_DEBUG")) printf("tall: reload at the first map frame after a room load without fade-in hook (tree warp) frame %ld\n", platform_frame_number()); }   /* the tree warp ($00E30E) loads the room but fades in with its own palette code: neither $008EB4 nor $00098A runs (user recording rec_20261017_1338, room 537 -> 539: one frame of garbage in the band) */
      if (a == 0x00098A && pending) lk_load_fade = 1;
      if (a == 0x008EB4 || a == 0x00098A) { if (!pending && a == 0x00098A) kv = 0; pending = 0; }
      if ((a == 0x008EB4 || a == 0x00098A) && kv > 0 && !lk_picture) { lk_wide_refill = 0; if (getenv("LANDSTALKER_TALL_DEBUG")) printf("tall: reload at fade-in $%06X frame %ld\n", a, platform_frame_number());
        lk_strip_extend(0x00A61C); lk_strip_extend(0x00A698); lk_strip_extend(0x00A6B0); lk_strip_extend(0x00A730); return; } }
    if (a == 0x0178C8 && kv > 0) {   /* full height: UpdateSprites did not run for a while (dialogue / cutscene text box over the map) -> the band below the picture may hold stale rows when the map comes back (user recording 2026-10-16, ship after the island map: garbage ~28 frames until the first scroll load) -> reload all strips with the first map pass */
        static long last_us = -1000; long now = platform_frame_number();
        if (now - last_us > 12 && !lk_picture) lk_wide_refill = 1;
        last_us = now;
    }
    if (a == 0x0178C8 && lk_wide_refill) {   /* UpdateSprites (game map frame): the width was raised at run time: load the new outer ring of the map diamond now (the same extra strips a scroll step would load) */
        lk_wide_refill = 0;
        lk_strip_extend(0x00A61C); lk_strip_extend(0x00A698); lk_strip_extend(0x00A6B0); lk_strip_extend(0x00A730);
        lk_ext_apply();   /* at once: the band is drawn from the state before this frame's flush (tree warp, rec_20261017_1338: one frame of garbage) */
        return;
    }
    if (a == 0x002686 && lk_ext_n) { lk_ext_apply(); return; }   /* FlushVdpWriteQueue: apply the private strip entries */
    if (a == 0x00C37E && lk_d2_shift) {   /* MapPtrAndCellFromXY leaves d2 (start cell, from $FF1184 via a table) alone: shift it like the camera: row' = (row + dy) mod 16, col' = (col + dx + 16 * floor((row + dy) / 16)) mod 32 (measured with BLOCKLOG: 0 mismatches in 9773 block pairs; the first formula (x + 0x20*y + K) mod 0x210 was wrong for 32 % of the cells) */
        int d = (int)(g_m68k.d[2] & 0xFFFF), row = (d >> 5) + lk_d2_shift_y, w = row >= 0 ? row / 16 : -((15 - row) / 16);   /* w = floor(row / 16) */
        int L = (row - 16 * w) * 32 + (((d & 31) + lk_d2_shift_x + 16 * w) % 32 + 32) % 32;
        g_m68k.d[2] = (g_m68k.d[2] & 0xFFFF0000u) | (uint32_t)L;
        lk_d2_shift = 0; return;
    }
    if (a == 0x00A748 && busy && kv > 0) {   /* BlockToTiles during one of OUR extra strips: a block address outside the 74 x 74 block map (x or y beyond the room array) reads other RAM (height map, entity table...) and shows as a lone garbage tile in the full-height band (room 632, brick stub, user recording 2026-10-16) -> use the empty cell 0,0 instead. BlockToTiles does not change a6, but the loader steps a6 relative to it, so the difference is added back at the next call */
        uint32_t a6 = g_m68k.a[6] + (uint32_t)lk_blk_delta;
        lk_blk_delta = 0; g_m68k.a[6] = a6;
        if (a6 < 0xFF7C02u || a6 >= 0xFF7C02u + 0x2AC8u) { lk_blk_delta = (int32_t)(a6 - 0xFF7C02u); g_m68k.a[6] = 0xFF7C02u; if (getenv("LANDSTALKER_TALL_DEBUG")) printf("tall: block outside the map a6=$%06X frame %ld\n", a6, platform_frame_number()); }
        return;
    }
    if (a != 0x00A61C && a != 0x00A698 && a != 0x00A6B0 && a != 0x00A730) return;
    if (busy) return;
    if (kenv == -2) { const char *c = getenv("LANDSTALKER_WIDE_STRIPS"); kenv = c && *c ? atoi(c) : -1; }
    k = kenv >= 0 ? kenv : lk_wide_e / 16; if (k > 4) k = 4;   /* default k = e/16, follows the run-time width switch */
    if (k <= 0 && kv <= 0) return;
    if (a == 0x00A61C)      { dx[0] = -1; dy[0] =  0; dx[1] =  0; dy[1] = -1; }   /* top    edge x+y = -11 */
    else if (a == 0x00A698) { dx[0] =  1; dy[0] =  0; dx[1] =  0; dy[1] =  1; }   /* bottom edge x+y = +11 */
    else if (a == 0x00A6B0) { dx[0] = -1; dy[0] =  0; dx[1] =  0; dy[1] =  1; }   /* left   edge y-x = +11 */
    else                    { dx[0] =  1; dy[0] =  0; dx[1] =  0; dy[1] = -1; }   /* right  edge x-y = +11 */
    for (j = 1; j <= k; j++) for (v = 0; v < 2; v++) { sx[ns] = dx[v] * j; sy[ns] = dy[v] * j; ns++; }   /* widescreen: k steps outward (unchanged order) */
    if (kv > 0) {   /* LANDSTALKER_TALL: screen-down = x+y; push the bottom edge kv steps down and run the left/right edge strips (and their widescreen copies) shifted down by (j,j) */
        int n0 = ns, m;
        if (a == 0x00A698) { for (j = k + 1; j <= kv && ns < 30; j++) for (v = 0; v < 2; v++) { sx[ns] = dx[v] * j; sy[ns] = dy[v] * j; ns++; } }
        else if (a == 0x00A6B0 || a == 0x00A730) for (j = 1; j <= (kv + 1) / 2; j++) {
            if (ns < 31) { sx[ns] = j; sy[ns] = j; ns++; }
            for (m = 0; m < n0 && ns < 31; m++) { sx[ns] = sx[m] + j; sy[ns] = sy[m] + j; ns++; }
        }
    }
    if (ns <= 0) return;
    if (lk_ext_n + ns * 12 * 12 > LK_EXT_CAP) return;                          /* private buffer full (cannot happen between two flushes in practice) */
    busy = 1; lk_no_charge = 1;
    {
        M68kContext sv = g_m68k;
        int cx = bus_read8(0xFF1124), cy = bus_read8(0xFF1125);
        uint32_t qp0 = ((uint32_t)bus_read16(0xFF1840) << 16) | bus_read16(0xFF1842); int qc0 = bus_read8(0xFF1128);
        { uint32_t room = (qp0 >= 0xFF3900u && qp0 < 0xFF5400u) ? (0xFF5400u - qp0) / 288u : 0u; if ((uint32_t)ns > room) ns = (int)room; }   /* never let the extra entries reach the player struct at $FF5400: drop the farthest strips instead (12 blocks x 24 bytes per strip) */
        static uint16_t lk_q_save[32 * 12 * 12 * 2]; int nsave = 0;   /* LANDSTALKER_TALL: the RAM behind the queue end the extra entries pass through (more than with widescreen alone: up to $FF50A0) is restored afterwards */
        if (kv > 0 && qp0 >= 0xFF3900u && qp0 < 0xFF5400u) { uint32_t q; for (q = qp0; q < 0xFF5400u && nsave < ns * 12 * 12 * 2; q += 2) lk_q_save[nsave++] = bus_read16(q); }
        for (j = 0; j < ns; j++) {
                int nx = cx + sx[j], ny = cy + sy[j];
                if (nx < 0 || ny < 0 || nx > 73 || ny > 73) continue;
                bus_write8(0xFF1124, (uint8_t)nx); bus_write8(0xFF1125, (uint8_t)ny);
                lk_d2_shift = 1; lk_d2_shift_x = sx[j]; lk_d2_shift_y = sy[j];
                lk_blk_delta = 0;
                func_table_jsr(a, 0x000001);
                lk_blk_delta = 0; g_m68k = sv;
            }
        lk_d2_shift = 0; bus_write8(0xFF1124, (uint8_t)cx); bus_write8(0xFF1125, (uint8_t)cy);
        g_m68k = sv;
        {   /* move what the loaders appended to the game's queue into the private buffer and restore pointer + count */
            uint32_t qp1 = ((uint32_t)bus_read16(0xFF1840) << 16) | bus_read16(0xFF1842), p;
            if (qp1 > qp0 && qp1 - qp0 <= (uint32_t)(LK_EXT_CAP - lk_ext_n) * 2u && ((qp1 - qp0) % 6) == 0)
                for (p = qp0; p < qp1; p += 2) lk_ext_w[lk_ext_n++] = bus_read16(p);
            bus_write16(0xFF1840, (uint16_t)(qp0 >> 16)); bus_write16(0xFF1842, (uint16_t)qp0); bus_write8(0xFF1128, (uint8_t)qc0);
            { int i2; for (i2 = 0; i2 < nsave; i2++) bus_write16(qp0 + 2u * (uint32_t)i2, lk_q_save[i2]); }
        }
    }
    lk_no_charge = 0; busy = 0;
}

'''
    b = "static uint32_t s_tail;"
    assert s.count(b) == 1, "func_table.c: anchor layout changed (strip extend)"
    s = s.replace(b, helper + b, 1)
    a = "        lk_entry_dump(m68k_addr, ret); /* LANDSTALKER_ENTRYDUMP */\n"
    assert s.count(a) == 1
    s = s.replace(a, "        lk_strip_extend(m68k_addr);   /* LANDSTALKER_WIDE_STRIPS */\n" + a, 1)
    open(p, "w").write(s)
    print("func_table.c patched: lk_strip_extend")
