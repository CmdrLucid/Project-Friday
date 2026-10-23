#!/usr/bin/env python3
"""Own renderer, compare mode (2026-10-18, renderer step 'state-driven picture', RENDERER_IDEAS Option B): draws the map picture of the game WITHOUT the VDP planes / sprite table, from
ROM data and game state only, line by line, and compares it with what the VDP produced.  C port of the Python tools romgfx / romrender / romsprite (all verified against RAM dumps,
FORMATS 'Room graphics in the ROM'):
 * tile graphics of the room: `DecompressLZ77Gfx $004AB2` from the ROM (room table $0A0A00, tileset table $044010), animated tiles (`AnimatedTilesetTable $009E04`, state `$FF1134`),
 * both scroll layers from the block arrays in work RAM (BG `$FFA6CA`, FG `$FF7C02`, 74 x 74 words) and the block table `$FF5C02` (4 tile words per block) on the 8 px brick grid
   (block (x, y) = 2 x 2 tiles at tile column 2 (x - y) + 148 / 146, tile row x + y); the screen position uses the camera of the previous pass (the image is unbounded: no plane wrap, no scroll registers),
 * the figures: visible entity list `$FF11DE`, frame pieces and tile graphics from the ROM (`LoadSpriteFrame $004230` port, SpriteGfxPtrPtr `$120000`),
 * colours: built from ROM + state too (player palette + equipment swaps, per-room sprite palette allocation, room palette, fade level = the game's counters $FF0F50 - $FF0F52 (checked against the active palette copy $FF0ED0, search only as fallback)); LANDSTALKER_OWN_PAL=0 uses the VDP's CRAM instead.
State = snapshot of work RAM of the PREVIOUS frame (the picture is one frame behind the RAM, FORMATS 'Scroll registers lag').
Switch: env LANDSTALKER_OWN=1 compare only (console line every LANDSTALKER_OWN_LOG frames, default 60: `own: frame F room R lines 0..223: D of T pixels differ`), =2 the picture shows
the OWN rendering in the map lines 0..223 (HUD / text box / lines below stay the game's).  On by default (since 2026-10-22); Options > Video > Own Renderer (file ~/.landstalker_own) switches mode 2 on; env LANDSTALKER_OWN wins.  Hook: render_line, before the other row overlays.
usage: patch_own.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_OWN v1"
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
s = open(p).read()
if VER not in s:
    d = "      lk_shadow_darken(lk_row0, lk_w0);   /* LK_SHADOW v7 */\n"
    assert s.count(d) == 1, "vdp_render.c: run patch_shadow.py first"
    s = s.replace(d, "      lk_own_row(lk_row0, lk_w0, line);   /* LK_OWN v1 */\n" + d, 1)
    q = "      lk_quick_hud(lk_row0, lk_w0);   /* LK_QUICK v1 */\n"
    if s.count(q) == 1: s = s.replace(q, q + "      lk_seam_final(lk_row0, lk_w0, line);   /* LK_OWN S3.5 */\n", 1)
    else: s = s.replace(d, d + "      lk_seam_final(lk_row0, lk_w0, line);   /* LK_OWN S3.5 */\n", 1)
    c = "void render_line(int line)"
    assert s.count(c) == 1
    module = r'''/* ---- LK_OWN v1: own renderer, compare mode (tools/patch_own.py) ---- */
extern uint8_t *bus_get_ram(void);
extern uint8_t bus_read8(uint32_t addr);
extern long platform_frame_number(void);
static int OB(uint32_t a) { return a < 0x200000u ? (int)bus_read8(a) : 0; }   /* ROM only; garbage pointers read 0 */
#define OW(a) ((OB(a) << 8) | OB((a) + 1))
#define OL(a) ((uint32_t)(((uint32_t)OW(a) << 16) | (uint32_t)OW((a) + 2)))
static int lk_o_sprmode = 1, lk_o_cammode = 2, lk_o_u0, lk_o_v0, lk_o_vote_room = -1, lk_o_bu, lk_o_bv, lk_o_upred, lk_o_vpred; static float lk_o_vu[64], lk_o_vv[32];
static int lk_o_mode = -1, lk_o_log = 60, lk_o_room = -1, lk_o_ngrp, lk_o_valid;
static int lk_sm_state, lk_sm_nofade, lk_sm_fastload, lk_o_lvl0;   /* S3.5 seamless door transitions (state 0 idle, 1 gap = frozen picture while the game fades / loads, 2 pan, 3 old room dissolves); nofade = the game's fade-in is not shown */
static int lk_o_fx;   /* LANDSTALKER_OWN_FX=0: the visual effects (warp pad, tree warp) stay the game's picture (old way) */
extern int lk_loadroom_on(void); extern int lk_warpfx_kind(void); extern int lk_fadein_on(void);
extern uint8_t lk_vm[], lk_vsm[], lk_cm[]; extern long lk_vm_ops;   /* patch_ownvb.py: own VRAM mirror of the game's DMA queue */
static int lk_o_scrvars;   /* LANDSTALKER_OWN_SCRVARS=1: scroll values from the game's variables $FF0100 / $FF0500 instead of the mirror of what its DMA queue sent */
static int lk_o_vmirror = 1;   /* LANDSTALKER_OWN_VMIRROR=0: sprite tiles compared / drawn from the VDP's VRAM (old way) instead of the own mirror of the game's DMA queue */
static int lk_o_hide0 = 1;   /* LANDSTALKER_OWN_HIDE0=0: figures the game replaced by effect sprites (Fire sword) are drawn as before */
static int lk_o_simple, lk_o_nigelvram = 1;   /* simple mode keeps one VRAM check: Nigel's pose (his animation fields run ahead of the graphic the VDP holds for a frame or two); LANDSTALKER_OWN_NIGELVRAM=0 = none */
static int lk_o_scrram = 1, lk_o_sc_ram, lk_o_seed = 1, lk_o_gshake;   /* LANDSTALKER_OWN_GSHAKE=1: the original Gaia effect reads the VDP scroll */   /* LANDSTALKER_OWN_SEED=0: no exact seed of the camera vote at a room load */
   /* LANDSTALKER_OWN_SCROLL_VDP=1: scroll values from the VDP (old way) */
extern int lk_gaia_shake(void);
extern int func_table_depth(void);
extern uint32_t func_table_stack(int k);
static long lk_o_fl_ok, lk_o_fl_bad; static int lk_o_fl_log;   /* fade level from the game's counters: palette lines where it matched / where the search had to take over (LANDSTALKER_OWN_FADELOG=1 prints the misses) */
static int lk_o_actcram;   /* LANDSTALKER_OWN_ACT_CRAM=1: the fade level is read from the VDP's CRAM (old way) instead of the game's active palette copy $FF0ED0 */
static uint8 lk_o_prev[0x10000], lk_o_use[0x10000], lk_o_good[0x10000]; static int lk_o_goodok, lk_o_fade;
#define UB(a) (lk_o_use[((a) & 0xFFFF) ^ 1])
#define UW(a) ((int)((UB(a) << 8) | UB((a) + 1)))
#define US(a) ((int)(int16_t)UW(a))
static const uint8 *lk_o_sp = lk_o_use;   /* RAM snapshot the figures are built from (LANDSTALKER_OWN_SPR=1 (default): current pass, 0: previous pass; measured: figures come from the CURRENT pass, camera / scenery from the previous one) */
#define SB(a) (lk_o_sp[((a) & 0xFFFF) ^ 1])
#define SW(a) ((int)((SB(a) << 8) | SB((a) + 1)))
static uint8 lk_o_tbase[0x12000], lk_o_tiles[0x12000];
static struct { int dest, words, delay, frames; uint32_t base; } lk_o_grp[8];
static uint32 lk_o_pa[152][304], lk_o_pb[152][304];                  /* layer cells: bit 16 = present, low 16 = tile word */
#define LK_OSW 448
extern int lk_wide_e;                                                /* LANDSTALKER_WIDE (patch_wide.py) */
extern int lk_warpfx(void);                                          /* the warp pad effect runs (patch_wide.py) */
extern int lk_sh_hide;                                               /* set while the Start menu runs (patch_shadow.py) */
extern int lk_map_decide(void);                                      /* the game map is on screen (patch_wide.py) */
extern int lk_tall_kv(void) __attribute__((weak));                  /* LANDSTALKER_TALL: > 0 = full height (the game's visibility test is widened by $80 at the bottom, patch_sprcull.py) */
extern int lk_tall_keep(int line);                                   /* LANDSTALKER_TALL: this line is drawn below the HInt display-off line (patch_tall.py) */
extern int lk_tbox_get(void);                                        /* Map Behind Text (patch_tbox.py) */
static uint16 lk_o_spr[224][LK_OSW];                                 /* by row pixel index (screen x + e): pal * 16 + index | 0x100 priority | 0x200 present */
static uint8 lk_o_sprtiles[0x4000];
extern int lk_org_lookup_raw(const uint8_t *t, uint32_t *rom, int *idx); extern void lk_org_learn(const uint8_t *t, uint32_t rom, int idx);   /* tools/patch_gfxorg.py: origin of a 32 byte tile image in the game's logical byte order */
static void *lk_o_repfor(const uint8 *t32, int pal, int cache); static int lk_o_hdwant(void);   /* HD / tile packs: replacement entry of a tile image (defined with the replacement table) */
static void *lk_o_sprrep[224][LK_OSW]; static uint8 lk_o_sprpx[224][LK_OSW];   /* HD: replacement entry + tile space pixel (ox | oy << 3 | hf << 6 | vf << 7) of every sprite layer pixel */
typedef struct { const uint8 *t; int ix, iy, hf, vf; } lk_o_fi_t;   /* where a plane / window pixel came from: tile image, pixel in tile space (flips applied), flips */
static lk_o_fi_t lk_o_wfi; static int lk_o_dbgsgi = -1, lk_o_dbganim, lk_o_dbgfrm;
static uint8 lk_o_hud[0x1000]; static int lk_o_hudn = -1;      /* StatusBarGfx $009242 (HUD tiles, tile numbers $6B4 ..) */
static int lk_o_disp0, lk_o_blanked, lk_o_firston, lk_o_dprev = 1; static long lk_o_diff, lk_o_tot; static int lk_o_nspr; static const uint8 *lk_o_r, *lk_o_cc, *lk_o_cp;   /* lk_o_r: work RAM of the current pass */
static int lk_o_lz77(uint32_t pos, uint8 *out, int cap) {            /* DecompressLZ77Gfx $004AB2 */
  int n = 0, i, flags;
  for (;;) {
    flags = OB(pos++);
    for (i = 0; i < 8; i++) {
      if ((flags >> (7 - i)) & 1) { if (n < cap) out[n] = (uint8)OB(pos); n++; pos++; }
      else {
        int b1 = OB(pos), b2 = OB(pos + 1), off, len, k; pos += 2;
        off = ((b1 >> 4) << 8) | b2; if (!off) return n;
        len = 18 - (b1 & 15);
        for (k = 0; k < len; k++) { if (n < cap) out[n] = (n - off >= 0 && n - off < cap) ? out[n - off] : 0; n++; }
      }
      if (n > 0x10000) return n;
    }
  }
}
static void lk_o_room_load(int room) {                               /* tile graphics + animated tile groups of a room */
  uint32_t tab = OL(0xA0A00), e = tab + 8u * (uint32_t)room, tp = OL(0x44010);
  int tileset = OB(e + 4) & 0x1F, i; uint32_t tptr;
  tptr = OL(tp + 4u * (uint32_t)tileset);
  memset(lk_o_tbase, 0, sizeof lk_o_tbase);
  lk_o_lz77(tptr, lk_o_tbase, 0x10000);
  lk_o_ngrp = 0;
  for (i = 0; OB(0x9E04 + i) != 0xFF; i++) if (OB(0x9E04 + i) == tileset && lk_o_ngrp < 8) {
    uint32_t a = 0x9E1C + 10u * (uint32_t)i;
    lk_o_grp[lk_o_ngrp].dest = OW(a); lk_o_grp[lk_o_ngrp].words = OW(a + 2); lk_o_grp[lk_o_ngrp].delay = OB(a + 4); lk_o_grp[lk_o_ngrp].frames = OB(a + 5);
    lk_o_grp[lk_o_ngrp].base = OL(OL(a + 6)); lk_o_ngrp++;
  }
  lk_o_room = room;
}

static PIXEL_OUT_T lk_o_pix[64]; static int lk_o_palmode = 1;
static PIXEL_OUT_T lk_o_fxpix[8][64]; static signed char lk_o_fxk[256]; static int lk_o_fxon, lk_o_fxprev, lk_o_fxoff, lk_o_fxhold, lk_o_fxact[56];   /* warp pad effect: 8 darkened palettes and the palette of every line */
static int lk_o_darken(int c, int d3) {                              /* DarkenColour $0009FC with target 0 */
  int b = ((c & 0xE00) - d3) & 0x1E00, g3 = d3 >> 4, g, r3 = g3 >> 4, r;
  if (b >= 0x1000) b = 0;
  g = ((c & 0xE0) - g3) & 0x1E0; if (g >= 0x100) g = 0;
  r = ((c & 0xE) - r3) & 0x1E; if (r >= 0x10) r = 0;
  return b | g | r;
}
extern int lk_gaia_live(void);   /* patch_gaia.py: 1 while the live Gaia effect runs (rocks use the Gaia sword colours) */
#define LK_CMW(i) (((lk_cm[2 * (i)] << 8) | lk_cm[2 * (i) + 1]) & 0xEEE)   /* the CRAM mirror of the DMA queue: what the VDP shows (the game's active palette copy $FF0ED0 can already be changed again, e.g. cleared at the end of the Nole warp while the white palette is still displayed) */
static void lk_o_palette(int room) {                                 /* the 64 colours of the picture from ROM data + game state (romsprite.sprite_palettes / romrender.rom_cram) */
  int direct = 0, pal[64], i, j, l, n, typ, ts, k, sword = lk_gaia_live() ? 4 : SB(0xFF114E), armour = SB(0xFF114F), act[64], bestn = 99, bestd = 0;
  uint32_t a, e, pbase;
  memset(pal, 0, sizeof pal);
  for (i = 0; i < 16; i++) pal[32 + i] = OW(0x901C + 2 * i);                                         /* line 2: Nigel */
  for (l = 0; l < 2; l++) {                                                                           /* armour colours 11 / 12, sword colours 13 / 14 */
    uint32_t idx = l ? 0x78F4 : 0x78FA, swaps = l ? 0x7900 : 0x7918; int item = l ? sword : armour;
    for (k = 0; k < 6 && OB(idx + (uint32_t)k) != item; k++) ;
    if (k > 5) k = 5;
    pal[32 + 11 + 2 * l] = OW(swaps + 4u * (uint32_t)k); pal[32 + 12 + 2 * l] = OW(swaps + 4u * (uint32_t)k + 2);
  }
  for (i = 0; i < 5; i++) pal[48 + 10 + i] = OW(0x903C + 2 * i);                                      /* line 3: HUD colours 10..14 */
  a = 0xFF5480;
  for (n = 0; n < 15 && !(SW(a) & 0x8000); n++, a += 0x80) {                                           /* InitSpritePalettes / GetSpritePalette */
    typ = SB(a + 0x3B); ts = SW(a + 6);
    if (!((ts >> 8) & 0x20)) continue;
    for (e = 0x1A453A; OB(e) != 0xFF && e < 0x1A47E0; e += 2) if (OB(e) == typ) {
      int v = OB(e + 1), hi = v & 0x80, idx = v & 0x7F, pal3 = (ts >> 8) & 0x40;
      if (hi) { if (!pal3) for (j = 0; j < 7; j++) pal[16 + 8 + j] = OW(0x1A4BA0 + 14u * (uint32_t)idx + 2u * (uint32_t)j); }
      else { int base = pal3 ? 48 + 2 : 16 + 2; for (j = 0; j < 6; j++) pal[base + j] = OW(0x1A47E0 + 12u * (uint32_t)idx + 2u * (uint32_t)j); }
    }
  }
  pal[56] = SW(0xFF00E0 + 0x10); pal[57] = SW(0xFF00E0 + 0x12); pal[29] = SW(0xFF00A0 + 0x1A); pal[30] = SW(0xFF00A0 + 0x1C);   /* projectile colours: event state */
  pbase = 0x11C926u + 26u * (uint32_t)OB(OL(0xA0A00) + 8u * (uint32_t)room + 5);                      /* line 0: room palette */
  { uint32_t la;                                                                                       /* dark rooms (LightableRooms $008800, CheckIfRoomIsLit $0087BE): the lantern flag (byte $FF1000 + b, bit) switches the room palette to LabrynthLitPal $002DB4 (SetRoomPal $002D64) */
    for (la = 0x8800; (int16_t)OW(la) >= 0 && la < 0x8840; la += 4) if ((int)OW(la) == room) { if ((SB(0xFF1000 + OB(la + 2)) >> (OB(la + 3) & 7)) & 1) pbase = 0x2DB4u; break; }
  }
  for (i = 0; i < 13; i++) pal[2 + i] = OW(pbase + 2u * (uint32_t)i);
  for (l = 0; l < 4; l++) { pal[16 * l] = 0; pal[16 * l + 1] = 0x0CCC; pal[16 * l + 15] = 0; }
  { static int cmchk = -1; if (cmchk < 0) cmchk = getenv("LANDSTALKER_OWN_CMCHK") != NULL;   /* test aid: compares the CRAM mirror of the DMA queue (patch_ownvb.py) with the VDP's CRAM, prints the frames where they differ */
    if (cmchk) { int bad = 0; for (i = 0; i < 64; i++) { int cw = (cram[(2 * i) ^ 1] << 8) | cram[(2 * i + 1) ^ 1]; int md = ((((cw >> 6) & 7) << 9) | (((cw >> 3) & 7) << 5) | ((cw & 7) << 1)), mm = (lk_cm[2 * i] << 8) | lk_cm[2 * i + 1]; if (md != mm) bad++; } if (bad) printf("owncm: frame %ld %d of 64 CRAM words differ from the DMA mirror\n", platform_frame_number(), bad); } }
  for (i = 0; i < 64; i++) { int cw = (cram[(2 * i) ^ 1] << 8) | cram[(2 * i + 1) ^ 1]; act[i] = (lk_o_firston || !lk_o_actcram) ? SW(0xFF0ED0 + 2 * i) : ((((cw >> 6) & 7) << 9) | (((cw >> 3) & 7) << 5) | ((cw & 7) << 1)); }   /* fade level: the VDP's palette (converted back to MD format), but on the first frame after the display was switched on the game's active copy: the VDP still holds the stale bright palette for that one frame and flashes the HUD */
  for (l = 0; l < 4; l++) {                                                                           /* every palette line has its own fade level (the HUD lines are not faded with the room) */
    bestn = 99; bestd = 0; direct = 0;
    { int L = (int16_t)(SW(0xFF0F50) - SW(0xFF0F52)), bad = 99;   /* the game's own fade level: DarkenPalette darkens with $FF0F50 and then adds the step $FF0F52, so the level of the palette on screen is the difference (fade in ends at 0, fade out at $E00 = black) */
      if (L >= 0 && L < 0x1400 && !(L & 0x1FF)) { bad = 0; for (i = 16 * l; i < 16 * l + 16; i++) { if (l == 3 && i >= 58 && i <= 62) continue; if (lk_o_darken(pal[i], L) != act[i]) bad++; } }
      if (bad == 0) { bestn = 0; bestd = L; lk_o_fl_ok++; }
      else if (lk_o_fx) { lk_o_fl_bad++; direct = 1; bestn = 0; }   /* effects (flashes, tree warp, ...): the game's own active palette is what is shown */
      else { lk_o_fl_bad++;   /* the game set the palette directly (e.g. black right after a quick load, the counters are stale then): search the level as before */
        for (j = 0; j < 0x1400; j += 0x200) { int bad2 = 0; for (i = 16 * l; i < 16 * l + 16; i++) { if (l == 3 && i >= 58 && i <= 62) continue; { int c = lk_o_darken(pal[i], j); if (c != act[i]) bad2++; } } if (bad2 < bestn) { bestn = bad2; bestd = j; } } if (lk_o_fl_log && l == 0) printf("ownfade: frame %ld level %X counters %X - %X: no exact match, search found %X (%d bad)\n", platform_frame_number(), L, SW(0xFF0F50), SW(0xFF0F52), bestd, bestn); }
    }
    if (lk_sm_nofade) { bestd = 0; direct = 0; bestn = 0; }   /* S3.5: no fade during a seamless transition */
    if (l == 0) { lk_o_fade = bestd != 0; lk_o_lvl0 = bestd; }
    if (getenv("LANDSTALKER_OWN_PAL")) { int i2; printf("ownpal: frame %ld room %d line %d level %X bad %d  rom/act:", platform_frame_number(), room, l, bestd, bestn); for (i2 = 16 * l; i2 < 16 * l + 16; i2++) printf(" %03X/%03X", lk_o_darken(pal[i2], bestd), act[i2]); printf("\n"); }
    if (l == 3) {                                                                                     /* (hb > 0: no fade level of the ROM colours reproduces the game's colours, e.g. the intro caption sets colour 11 to white itself: the game's actual colour is used) line 3 is mixed: the sprite colours fade with the room, the HUD colours 10..14 do not (rooms with objects on palette line 3, e.g. 427): own level for them, the line's level when they are all black */
      int hd = bestd, hb = 99, nz = 0;
      for (i = 58; i <= 62; i++) nz += act[i] != 0;
      if (nz) { int Lc = (int16_t)(SW(0xFF0F50) - SW(0xFF0F52)), cand[2], ci; cand[0] = (Lc >= 0 && Lc < 0x1400 && !(Lc & 0x1FF)) ? Lc : 0; cand[1] = 0;   /* the HUD colours are faded by the 64 colour fades only (level from the counters) and not by the 58 colour room fades (level 0); anything else (the intro caption sets colour 11 itself) is the game's own colour */
        for (ci = 0; ci < 2; ci++) { int bad = 0; j = cand[ci]; for (i = 58; i <= 62; i++) if (lk_o_darken(pal[i], j) != act[i]) bad++; if (bad < hb) { hb = bad; hd = j; } } }
      if (lk_sm_nofade) { hd = 0; hb = 0; }
      for (i = 58; i <= 62; i++) { int c = direct ? LK_CMW(i) : (nz && hb > 0 && hb != 99) ? act[i] : lk_o_darken(pal[i], hd); lk_o_pix[i] = pixel_lut[1][((c >> 9) & 7) << 6 | ((c >> 5) & 7) << 3 | ((c >> 1) & 7)]; }
    }
    for (i = 16 * l; i < 16 * l + 16; i++) { if (l == 3 && i >= 58 && i <= 62) continue; { int c = direct ? LK_CMW(i) : lk_o_darken(pal[i], bestd); lk_o_pix[i] = pixel_lut[1][((c >> 9) & 7) << 6 | ((c >> 5) & 7) << 3 | ((c >> 1) & 7)]; } }
  lk_o_fxon = 0;
  if (lk_o_fx && lk_warpfx_kind() == 1) {   /* WarpPadFx $00E154: the game rewrites CRAM colours 0..55 from 8 palettes (the base palette darkened 0..7 levels, g_Buffer) at line thresholds, band i = palette 7 - i; the thresholds are in g_Buffer + $380 = $FF2F80 */
    int k, y, t[8], first = -1, last = -1;
    for (k = 0; k < 8; k++) { t[k] = SB(0xFF2F80 + k) & 0xFF; if (t[k] >= 0x17 && first < 0) first = k; if (t[k] >= 0x17) last = k; }
    for (k = 1; k < 8; k++) if (t[k] < t[k - 1]) { for (k = 0; k < 8; k++) t[k] = 0; first = last = -1; break; }   /* the effect has not computed its table yet (stale g_Buffer): no bands */
    for (k = 0; k < 8; k++) for (i = 0; i < 64; i++) { if (i < 56) { int c = lk_o_darken(pal[i], k * 0x200); lk_o_fxpix[k][i] = pixel_lut[1][((c >> 9) & 7) << 6 | ((c >> 5) & 7) << 3 | ((c >> 1) & 7)]; } else lk_o_fxpix[k][i] = lk_o_pix[i]; }
    for (y = 0; y < 256; y++) { int yy = y > 0xB7 ? 0xB7 : y, b = -1;
      for (k = 0; k < 8; k++) if (t[k] >= 0x17 && t[k] + lk_o_fxoff > yy) { b = k; break; }
      if (b < 0) b = last;
      lk_o_fxk[y] = (signed char)(b < 0 ? lk_o_fxprev : 7 - b);
    }
    { int b = -1; for (k = 0; k < 8; k++) if (t[k] >= 0x17 && t[k] + lk_o_fxoff > 0xB7) { b = k; break; } if (b < 0) b = last; if (b >= 0) lk_o_fxprev = 7 - b; }
    lk_o_fxon = 1; (void)first;
    lk_o_fxhold = 1; for (i = 0; i < 56; i++) lk_o_fxact[i] = act[i];
  } else if (lk_o_fx && lk_o_fxhold) {   /* the effect ended: CRAM keeps the last band's palette until the game fades the room in (its active palette copy changes then) */
    int same = 1, k; for (i = 0; i < 56; i++) if (lk_o_fxact[i] != act[i]) same = 0;
    if (same) { for (k = 0; k < 8; k++) for (i = 0; i < 64; i++) { if (i < 56) { int c = lk_o_darken(pal[i], k * 0x200); lk_o_fxpix[k][i] = pixel_lut[1][((c >> 9) & 7) << 6 | ((c >> 5) & 7) << 3 | ((c >> 1) & 7)]; } else lk_o_fxpix[k][i] = lk_o_pix[i]; }
      for (i = 0; i < 256; i++) lk_o_fxk[i] = (signed char)lk_o_fxprev; lk_o_fxon = 1; }
    else { lk_o_fxhold = 0; lk_o_fxprev = 0; }
  } else lk_o_fxprev = 0;
  }
}
static void lk_o_sprpiece(const uint8 *td, int tile0, int sx, int sy, int w, int h, int pal, int prio, int hf, int vf) {
  int px, py, hd = lk_o_hdwant(), ti; void *rp[16] = { 0 };
  if (hd) for (ti = 0; ti < w * h && ti < 16; ti++) if ((tile0 + ti) * 32 + 31 < 0x4000) rp[ti] = lk_o_repfor(td + (tile0 + ti) * 32, pal, 0);
  for (px = 0; px < w * 8; px++) for (py = 0; py < h * 8; py++) {
    int ox = hf ? (w * 8 - 1 - px) : px, oy = vf ? (h * 8 - 1 - py) : py, t = tile0 + (ox / 8) * h + (oy / 8), a = t * 32 + (oy % 8) * 4 + (ox % 8) / 2, b, idx, X = sx + px + lk_wide_e, Y = sy + py;
    if (a >= 0x4000) continue;
    b = td[a]; idx = ((ox % 8) % 2 == 0) ? (b >> 4) : (b & 15);
    if (!idx || X < 0 || X >= 320 + 2 * lk_wide_e || X >= LK_OSW || Y < 0 || Y >= 224 || (lk_o_spr[Y][X] & 0x200)) continue;
    lk_o_spr[Y][X] = (uint16)(0x200 | (prio ? 0x100 : 0) | (pal * 16 + idx));
    if (hd) { int q = (ox / 8) * h + (oy / 8); lk_o_sprrep[Y][X] = q < 16 ? rp[q] : 0; lk_o_sprpx[Y][X] = (uint8)((ox % 8) | ((oy % 8) << 3) | (hf << 6) | (vf << 7)); }
  }
}
static void lk_o_vpiece(int tile0, int sx, int sy, int w, int h, int pal, int prio, int hf, int vf) {   /* a sprite piece drawn from the game's own VRAM tiles (effects that write the sprite table directly) */
  int px, py, hd = lk_o_hdwant(), ti; void *rp[16] = { 0 };
  if (hd) for (ti = 0; ti < w * h && ti < 16; ti++) { uint8 tt[32]; int a0 = (tile0 + ti) * 32, i2; if (a0 + 31 >= 0x10000) continue; for (i2 = 0; i2 < 32; i2++) tt[i2] = lk_o_vmirror ? lk_vm[a0 + i2] : vram[(a0 + i2) ^ 1]; rp[ti] = lk_o_repfor(tt, pal, 0); }
  for (px = 0; px < w * 8; px++) for (py = 0; py < h * 8; py++) {
    int ox = hf ? (w * 8 - 1 - px) : px, oy = vf ? (h * 8 - 1 - py) : py, t = tile0 + (ox / 8) * h + (oy / 8), a = t * 32 + (oy % 8) * 4 + (ox % 8) / 2, b, idx, X = sx + px + lk_wide_e, Y = sy + py;
    if (a >= 0x10000) continue;
    b = lk_o_vmirror ? lk_vm[a] : vram[a ^ 1]; idx = ((ox % 8) % 2 == 0) ? (b >> 4) : (b & 15);
    if (!idx || X < 0 || X >= 320 + 2 * lk_wide_e || X >= LK_OSW || Y < 0 || Y >= 224 || (lk_o_spr[Y][X] & 0x200)) continue;
    lk_o_spr[Y][X] = (uint16)(0x200 | (prio ? 0x100 : 0) | (pal * 16 + idx));
    if (hd) { int q = (ox / 8) * h + (oy / 8); lk_o_sprrep[Y][X] = q < 16 ? rp[q] : 0; lk_o_sprpx[Y][X] = (uint8)((ox % 8) | ((oy % 8) << 3) | (hf << 6) | (vf << 7)); }
  }
}
static uint32 lk_o_satk[96]; static int lk_o_satt[96], lk_o_satn; static int lk_o_satw[96]; static uint32 lk_o_dk[96]; static int lk_o_dn;   /* lk_o_satw: full attribute word of every sprite table entry; lk_o_dk: keys of the pieces the figures pass drew */   /* the real sprite table: key (x, y, size) and first tile number of every entry */
typedef struct { int vis, ax, ay, ts, sgi, anim, frm, np, pxs[8], pys[8], pws[8], phs[8], prio, off; uint8 *tiles; } lk_o_ent_t;
static uint8 lk_o_sprtiles_b[0x4000], lk_o_sprtiles_c[0x4000], lk_o_sprtiles_p[0x4000]; static int lk_o_ovr_anim = -1, lk_o_ovr_frm;   /* _p: tiles of the pose found by the VRAM search; ovr: that search tries other (animation, frame) pairs */
static void lk_o_entload(const uint8 *src, int off, lk_o_ent_t *e, uint8 *tiles, int decode, int use4e) {   /* one entity of one pass state: pieces + tile graphics from the ROM */
  int b = 0xFF5400 + off, guard, tl = 0; uint32_t base, fp, ap, pos, cstart;
  const uint8 *keep = lk_o_sp; lk_o_sp = src;
  e->off = off; e->tiles = tiles; e->np = 0; e->vis = 0;
  e->ax = SW(b + (use4e ? 0x4E : 0x0E)); e->ay = SW(b + (use4e ? 0x50 : 0x10)); e->ts = SW(b + 6);   /* +4E / +50 = the screen position of the previous pass (sub_40F2 copies +0E there before it recomputes it): the game draws objects there */
  if ((e->ax == 0 && e->ay == 0) || (SB(b + 0x0C) & 0x40)) { lk_o_sp = keep; return; }   /* Flags2 bit 6 = hidden (the player's hurt blink toggles it every pass) */
  e->vis = 1; e->sgi = SB(b + 0x0B); e->anim = SW(b + 0x24); e->frm = SW(b + 0x26); if (lk_o_ovr_anim >= 0) { e->anim = lk_o_ovr_anim; e->frm = lk_o_ovr_frm; } e->prio = SW(0xFF1400 + (off >> 1) + 4) >> 15;
  base = OL(0x120000); { int ofs = OW(0x120004 + 4 * e->sgi); ap = OL(base + (uint32_t)ofs * 4 + (uint32_t)e->anim); }
  fp = OL(ap + (uint32_t)e->frm); pos = fp;
  for (;;) {
    int b1 = OB(pos), b2 = OB(pos + 1), yy = (b1 << 1) & 0xF8, xx = (b2 << 1) & 0xF8; pos += 2;
    if (yy > 127) yy -= 256; if (xx > 127) xx -= 256;
    e->pxs[e->np] = xx; e->pys[e->np] = yy; e->pws[e->np] = (b1 & 3) + 1; e->phs[e->np] = (b2 & 3) + 1; e->np++;
    if ((b2 & 0x80) || e->np >= 8) break;
  }
  cstart = pos;
  if (decode) for (guard = 0; guard < 64; guard++) {
    int h = OW(pos), n = h & 0x0FFF, i; pos += 2;
    if (h & 0x8000) { for (i = 0; i < n * 2 && tl + i < 0x4000; i++) tiles[tl + i] = 0; tl += n * 2; }
    else if (h & 0x2000) { int got = lk_o_lz77(pos, tiles + tl, 0x4000 - tl); tl += got; break; }
    else { for (i = 0; i < n * 2 && tl + i < 0x4000; i++) tiles[tl + i] = (uint8)OB(pos + (uint32_t)i); pos += (uint32_t)n * 2; tl += n * 2; }
    if (h & 0x4000) break;
  }
  if (decode && lk_o_hdwant()) { int k; for (k = 0; (k + 1) * 32 <= tl && (k + 1) * 32 <= 0x4000; k++) lk_org_learn(tiles + 32 * k, cstart, k); }   /* origin of a figure tile = ROM address of the pose's chunk list + tile index in the assembled graphic (the chunks are not tile aligned, so they are no unit of their own) */
  lk_o_sp = keep;
}
static uint32 lk_o_pkey(const lk_o_ent_t *e, int pc, int *xxo) {
  int xx = (((e->ts >> 11) & 1) ? (-e->pxs[pc] - 8 * e->pws[pc]) : e->pxs[pc]); if (xxo) *xxo = xx;
  return (uint32)(((e->ax + xx) & 0x1FF) << 20 | ((e->ay + e->pys[pc]) & 0x3FF) << 8 | (e->pws[pc] - 1) << 2 | (e->phs[pc] - 1));
}
static int lk_o_escore(const lk_o_ent_t *e) {                        /* how well does this entity (in this pass state) agree with the real sprite table: key AND first tile graphic of every piece */
  int pc, j, i, cum = 0, sc = 0;
  for (pc = 0; pc < e->np; pc++) {
    uint32 k = lk_o_pkey(e, pc, 0);
    for (j = 0; j < lk_o_satn; j++) if (lk_o_satk[j] == k) {
      int t = lk_o_satt[j], same = 1, nb = 32 * e->pws[pc] * e->phs[pc];   /* ALL tiles of the piece: poses of one figure share their first tile (Nigel's walk frame vs the one-frame turn pose), only the whole piece tells which graphic the VDP really holds */
      if (nb > 0x4000 - cum * 32) nb = 0x4000 - cum * 32; if (t * 32 + nb > 0x10000) nb = 0x10000 - t * 32;
      for (i = 0; i < nb && same; i++) if ((lk_o_vmirror ? lk_vm[t * 32 + i] : vram[(t * 32 + i) ^ 1]) != e->tiles[cum * 32 + i]) same = 0;
      sc += same ? 2 : 1; break;
    }
    cum += e->pws[pc] * e->phs[pc];
  }
  return sc;
}
static int lk_o_loose(const lk_o_ent_t *e) {                          /* does the real sprite table hold ANY piece of this entity (same size, position within 6 pixels: one pass of lag, the two-pass frames)? */
  int pc, j;
  for (pc = 0; pc < e->np; pc++) {
    uint32 k = lk_o_pkey(e, pc, 0);
    for (j = 0; j < lk_o_satn; j++) {
      int dx = (int)((k >> 20) & 0x1FF) - (int)((lk_o_satk[j] >> 20) & 0x1FF), dy = (int)((k >> 8) & 0x3FF) - (int)((lk_o_satk[j] >> 8) & 0x3FF);
      if ((k & 15) == (lk_o_satk[j] & 15) && dx >= -6 && dx <= 6 && dy >= -6 && dy <= 6) return 1;
    }
  }
  return 0;
}
static int lk_o_near(const lk_o_ent_t *e) {                           /* the sprite table holds a piece of the same size close to one of the entity's pieces (same column, up to 16 lines off) but none that agrees with it: the game replaced the figure by something else (effect sprites); an incomplete table (a pass in the middle of its work) holds nothing near */
  int pc, j;
  for (pc = 0; pc < e->np; pc++) {
    uint32 k = lk_o_pkey(e, pc, 0);
    for (j = 0; j < lk_o_satn; j++) {
      int dx = (int)((k >> 20) & 0x1FF) - (int)((lk_o_satk[j] >> 20) & 0x1FF), dy = (int)((k >> 8) & 0x3FF) - (int)((lk_o_satk[j] >> 8) & 0x3FF);
      if ((k & 15) == (lk_o_satk[j] & 15) && dx >= -4 && dx <= 4 && dy >= -16 && dy <= 16) return 1;
    }
  }
  return 0;
}
static int lk_o_loose4e(const lk_o_ent_t *e) {                        /* the same at the position of the previous pass (+4E / +50): the game draws objects there */
  lk_o_ent_t t = *e; int b = 0xFF5400 + e->off;
  t.ax = SW(b + 0x4E); t.ay = SW(b + 0x50);
  return lk_o_loose(&t);
}
static int lk_o_list(const uint8 *src, int *offs) {                  /* visible entity list $FF11DE of a pass state; when the game is in the middle of a pass at the top of the frame the list is empty (terminator first): the last complete list is used (the entity structs are fresh anyway) */
  int a = 0xFF11DE, n = 0; const uint8 *keep = lk_o_sp; lk_o_sp = (((src[(0xFF11DE & 0xFFFF) ^ 1] << 8) | src[(0xFF11DF & 0xFFFF) ^ 1]) == 0xFFFF && lk_o_goodok && !lk_o_fade) ? lk_o_good : src;
  for (;;) { int off = SW(a); a += 2; if ((off & 0x8000) || a > 0xFF11DE + 40 || n >= 24) break; offs[n++] = off; }
  lk_o_sp = keep; return n;
}
static int lk_o_formula(const uint8 *st, int off, int *ax, int *ay) {   /* the game's own visibility test + screen position (CheckEntityOnScreen sub_4144, 'model overlay') for an entity that is NOT in the game's visible list, from a pass state; the widescreen margin is allowed for */
  const uint8 *keep = lk_o_sp; int b = 0xFF5400 + off, z, cx, cy, c0, c2, kk, a, bb, rx, ry, ok = 0;
  lk_o_sp = st;
  z = (int16_t)SW(b + 0x12); cx = (int16_t)SW(b + 0x14); cy = (int16_t)SW(b + 0x16); c0 = (int16_t)SW(0xFF1200); c2 = (int16_t)SW(0xFF1202); kk = off == 0 ? 0 : ((SW(0xFF1180) ^ 1) & 0xFFFF);
  a = (int16_t)(cx - z - c0); bb = (int16_t)(cy - z - c2);
  if (!(SB(b + 8) & 1) && !(SB(b + 0x0C) & 0x40) && (uint16_t)(a + bb + 0x100) < (uint16_t)(0x200 + ((lk_tall_kv && lk_tall_kv() > 0) ? 0x80 : 0)) && (uint16_t)(a - bb + 0x100) < 0x200) {
    rx = a - bb + 0x120; ry = ((((uint16_t)(a + bb + kk)) >> 1) + 0xE8) & 0x7FF;
    if (rx >= 0x60 - lk_wide_e - 40 && rx < 0x1E0 + lk_wide_e + 40 && ry >= 0x40 && ry < 0x220) { *ax = rx; *ay = ry; ok = 1; }
  }
  lk_o_sp = keep; return ok;
}
static uint32 lk_o_dk2[96]; static int lk_o_dn2, lk_o_exon, lk_o_exnext;   /* sprite table entries no figure accounts for are drawn between the figures at their table position: dk2 = keys the first figure pass drew, exnext = next table index to look at */
static void lk_o_extras_upto(int upto) {                            /* effects that write the sprite table directly (Gaia rocks, the Fire / Thunder / Ice effect at a target): the entries that no figure piece accounts for, from the game's VRAM tiles, in the order of the table (lower index = in front, the figure loop calls this before every figure with that figure's first table index) */
  static int ex = -1; int i2;
  if (ex < 0) { const char *c = getenv("LANDSTALKER_OWN_EXTRA"); ex = c && *c == '0' ? 0 : 1; }
  for (; ex && lk_o_exnext < lk_o_satn && lk_o_exnext < upto; lk_o_exnext++) {
    int j = lk_o_exnext; uint32 k2 = lk_o_satk[j]; int w2 = lk_o_satw[j], covered = 0;
    for (i2 = 0; i2 < lk_o_dn2; i2++) if (lk_o_dk2[i2] == k2) { covered = 1; break; }
    if (getenv("LANDSTALKER_OWN_SAT")) printf("ownsat: frame %ld #%d x %d y %d size %X attr %04X %s\n", platform_frame_number(), j, (int)((k2 >> 20) & 0x1FF), (int)((k2 >> 8) & 0x3FF), (int)(k2 & 15), w2, covered ? "covered" : "EXTRA");
    if (covered) continue;
    lk_o_vpiece(w2 & 0x7FF, (int)((k2 >> 20) & 0x1FF) - 128, (int)((k2 >> 8) & 0x3FF) - 128, (int)((k2 >> 2) & 3) + 1, (int)(k2 & 3) + 1, (w2 >> 13) & 3, (w2 >> 15) & 1, (w2 >> 11) & 1, (w2 >> 12) & 1);
  }
}
static int lk_o_sprites(const uint8 *src, int draw, uint32 *keys, const uint8 *alt) {   /* figures of one pass state: drawn into lk_o_spr and / or as SAT keys (x, y, size) for the choice of the pass; with `alt` every entity of EITHER pass' visible list takes the version (this pass / the other one, or absent) that matches the real sprite table: the game's visibility test flips entities in and out of the list from pass to pass */
  int offs[48], inA[48], inB[48], inF[48], sord[48], n, k, nb = 0, boffs[24], nk = 0, i;
  if (draw) { memset(lk_o_spr, 0, sizeof lk_o_spr); if (lk_o_hdwant()) memset(lk_o_sprrep, 0, sizeof lk_o_sprrep); lk_o_nspr = 0; lk_o_dn = 0; }
  n = lk_o_list(src, offs); for (k = 0; k < n; k++) { inA[k] = 1; inB[k] = 0; inF[k] = 0; }
  if (alt) { nb = lk_o_list(alt, boffs); for (i = 0; i < nb; i++) { for (k = 0; k < n && offs[k] != boffs[i]; k++) ; if (k < n) inB[k] = 1; else if (n < 48) { offs[n] = boffs[i]; inA[n] = 0; inB[n] = 1; inF[n] = 0; n++; } } }
  if (draw && alt) {                                                 /* entities the game's visibility test left out of both lists (it flips objects at the edge of the widened screen in and out from pass to pass = blinking): draw them when the same test, evaluated by us on the previous pass, says visible */
    const uint8 *keep = lk_o_sp; int q2; lk_o_sp = src;
    for (q2 = 1; q2 < 16 && n < 48; q2++) {
      int off = 0x80 * q2, in = 0;
      if (SB(0xFF5400 + off) & 0x80) break;                          /* end of the entity array */
      for (k = 0; k < n; k++) if (offs[k] == off) in = 1;
      if (!in) { offs[n] = off; inA[n] = 0; inB[n] = 0; inF[n] = 1; n++; }
    }
    lk_o_sp = keep;
  }
  { /* draw order = order of the real sprite table (lower index = in front): sort the entities by the first table entry that matches one of their boxes (this pass, previous-pass position or the other snapshot) */
    int ord[48], idx[48], q, r2;
    for (k = 0; k < n; k++) {
      int v, best = 1000 + k;
      for (v = 0; v < 3; v++) {
        lk_o_ent_t t; int pc, j;
        if (inF[k]) continue; if (v == 0 && !inA[k]) continue; if (v == 2 && !(alt && inB[k])) continue; if (v == 1 && !(inA[k] && offs[k] != 0)) continue;
        lk_o_entload(v == 2 ? alt : src, offs[k], &t, lk_o_sprtiles_c, 0, v == 1);
        for (pc = 0; pc < t.np; pc++) { uint32 kk = lk_o_pkey(&t, pc, 0); for (j = 0; j < lk_o_satn; j++) if (lk_o_satk[j] == kk) { if (j < best) best = j; break; } }
      }
      ord[k] = best; idx[k] = k;
    }
    if (draw && (alt || lk_o_simple)) for (q = 1; q < n; q++) for (r2 = q; r2 > 0 && ord[idx[r2]] < ord[idx[r2 - 1]]; r2--) { int t2 = idx[r2]; idx[r2] = idx[r2 - 1]; idx[r2 - 1] = t2; }
    for (k = 0; k < n; k++) sord[k] = ord[idx[k]];
    { int so[48], sf[48], sa[48], sb[48]; for (k = 0; k < n; k++) { so[k] = offs[idx[k]]; sa[k] = inA[idx[k]]; sb[k] = inB[idx[k]]; sf[k] = inF[idx[k]]; } for (k = 0; k < n; k++) { offs[k] = so[k]; inA[k] = sa[k]; inB[k] = sb[k]; inF[k] = sf[k]; } }
  }
  for (k = 0; k < n; k++) {
    lk_o_ent_t e0, e1, e2, e3, *e = 0; int pc, cum = 0, use3 = 0;
    if (inF[k]) {                                                    /* not in the game's lists */
      int fx, fy;
      if (!lk_o_formula(lk_o_use, offs[k], &fx, &fy)) continue;
      lk_o_entload(src, offs[k], &e0, lk_o_sprtiles, 1, 0); if (!e0.vis) continue;
      e0.ax = fx; e0.ay = fy; e = &e0;
    } else
    if (inA[k]) { lk_o_entload(src, offs[k], &e0, lk_o_sprtiles, draw, 0); e = &e0; }
    if (draw && alt && inA[k] && offs[k] != 0) {                      /* objects / NPCs (not the player): three versions, this pass' position, the previous pass' position (+4E), the other snapshot; the one that matches the real sprite table wins, ties go to +4E */
      int s0, s2, s1 = -1;
      lk_o_entload(src, offs[k], &e2, lk_o_sprtiles_c, 1, 1); lk_o_entload(src, offs[k], &e0, lk_o_sprtiles, 1, 0);
      s0 = lk_o_escore(&e0); s2 = lk_o_escore(&e2);
      if (inB[k]) { lk_o_entload(alt, offs[k], &e1, lk_o_sprtiles_b, 1, 0); s1 = lk_o_escore(&e1); }
      e = &e2; if (s0 > s2 && s0 >= s1) e = &e0; if (s1 > s2 && s1 > s0) e = &e1;
      if (e0.vis && e2.vis && (e0.ax != e2.ax || e0.ay != e2.ay)) {   /* the game ran two passes in this frame: the sprite table can be one step AHEAD of both snapshots (e0 + (e0 - e2)); a candidate that matches the real sprite table better than all three wins */
        int j, bs = s0 > s2 ? s0 : s2; if (s1 > bs) bs = s1;
        for (j = 1; j <= 2; j++) { lk_o_ent_t t = e0; int sj; t.ax = e0.ax + j * (e0.ax - e2.ax); t.ay = e0.ay + j * (e0.ay - e2.ay); sj = lk_o_escore(&t); if (sj > bs) { bs = sj; e3 = t; use3 = 1; } }
        if (use3) e = &e3;
      }
      if (getenv("LANDSTALKER_OWN_DBG")) printf("ownent: frame %ld off %02X e0 (%d,%d) %d  e2 (%d,%d) %d  e1 (%d,%d) %d  -> %s\n", platform_frame_number(), offs[k], e0.ax, e0.ay, s0, e2.ax, e2.ay, s2, e1.ax, e1.ay, s1, use3 ? "ahead" : e == &e2 ? "4E" : e == &e0 ? "0E" : "alt");
      if (e->vis == 0 && e0.vis) e = &e0;
    } else if (draw && alt && inB[k]) {
      lk_o_entload(alt, offs[k], &e1, lk_o_sprtiles_b, 1, 0);
      if (!e) e = &e1;
      else if (e0.vis != e1.vis || e0.ax != e1.ax || e0.ay != e1.ay || e0.sgi != e1.sgi || e0.anim != e1.anim || e0.frm != e1.frm || e0.ts != e1.ts) { if (lk_o_escore(&e1) > lk_o_escore(&e0)) e = &e1; }
    }
    if (draw && alt && inA[k] != inB[k] && e) {                       /* in one list only: show it when it agrees with the sprite table */
      if (lk_o_escore(e) == 0) {                                    /* the real sprite table does not draw it in this frame (the game's list flips it in and out): draw it anyway when it is visible */
        int fx, fy; lk_o_ent_t *f = &e2;
        if (offs[k] == 0 || !lk_o_formula(lk_o_use, offs[k], &fx, &fy)) continue;
        lk_o_entload(src, offs[k], f, lk_o_sprtiles_c, 1, 0); if (!f->vis) continue;
        f->ax = fx; f->ay = fy; e = f; cum = 0;
      }
    }
    if (getenv("LANDSTALKER_OWN_ENTS") && draw) printf("ownents: frame %ld off %02X type %02X A%d B%d F%d vis %d at (%d,%d) np %d score %d\n", platform_frame_number(), offs[k], SB(0xFF5400 + offs[k] + 0x3B), inA[k], inB[k], inF[k], e ? e->vis : -1, e ? e->ax : 0, e ? e->ay : 0, e ? e->np : 0, e ? lk_o_escore(e) : -1);
    if (getenv("LANDSTALKER_OWN_ENTS") && draw && e && e->vis && e->np && lk_o_escore(e) == 0) { int q; for (q = 0; q < e->np; q++) { uint32 kk = lk_o_pkey(e, q, 0); printf("   piece %d: x %d y %d w %d h %d anim %X frm %X sgi %02X ts %04X\n", q, (int)((kk >> 20) & 0x1FF), (int)((kk >> 8) & 0x3FF), e->pws[q], e->phs[q], e->anim, e->frm, e->sgi, e->ts); } }
    if (draw && (!lk_o_simple || lk_o_nigelvram) && offs[k] == 0 && e && e->vis && e->np && lk_o_escore(e) < 2 * e->np) {   /* Nigel: for a frame or two the entity's animation / frame fields run ahead of (or behind) the graphic the VDP really holds (one-frame turn flicker while walking in a straight line, rec_20261019_2044): look for the pose whose tiles ARE in VRAM (the same pose appears under several (animation, frame) pairs) */
      static lk_o_ent_t pose; int an, fr, found = 0;
      for (an = 0; an < 64 && !found; an += 4) for (fr = 0; fr < 96 && !found; fr += 4) {
        lk_o_ovr_anim = an; lk_o_ovr_frm = fr; lk_o_entload(src, offs[k], &pose, lk_o_sprtiles_p, 1, 0); lk_o_ovr_anim = -1;
        if (pose.vis && pose.np == e->np && lk_o_escore(&pose) == 2 * pose.np) found = 1;
      }
      if (found) e = &pose;
    }
    if (!e || !e->vis) continue;
    if (draw && lk_o_hide0 && offs[k] != 0 && e->np && lk_o_satn > 0 && !lk_o_loose(e) && !lk_o_loose4e(e) && lk_o_near(e)) { if (getenv("LANDSTALKER_OWN_ENTS")) { int q; printf("ownhide: frame %ld off %02X type %02X at (%d,%d) 4e (%d,%d)\n", platform_frame_number(), offs[k], SB(0xFF5400 + offs[k] + 0x3B), e->ax, e->ay, SW(0xFF5400 + offs[k] + 0x4E), SW(0xFF5400 + offs[k] + 0x50)); for (q = 0; q < e->np; q++) { uint32 kk = lk_o_pkey(e, q, 0); printf("   piece %d: x %d y %d size %X\n", q, (int)((kk >> 20) & 0x1FF), (int)((kk >> 8) & 0x3FF), (int)(kk & 15)); } } continue; }   /* the real sprite table holds none of this entity's pieces: the game draws something else in its place (a burning enemy of the Fire sword is replaced by flame sprites that are written into the table, they come as EXTRA entries) */
    if (draw && lk_o_exon) lk_o_extras_upto(sord[k]);
    lk_o_nspr++;
    for (pc = 0; pc < e->np; pc++) {
      int xx; uint32 key = lk_o_pkey(e, pc, &xx);
      if (keys && nk < 96) keys[nk++] = key;
      if (draw && lk_o_dn < 96) lk_o_dk[lk_o_dn++] = key;
      lk_o_dbgsgi = e->sgi; lk_o_dbganim = e->anim; lk_o_dbgfrm = e->frm;
      if (draw) lk_o_sprpiece(e->tiles, cum, e->ax + xx - 128, e->ay + e->pys[pc] - 128, e->pws[pc], e->phs[pc], (e->ts >> 13) & 3, e->prio, (e->ts >> 11) & 1, (e->ts >> 12) & 1);
      cum += e->pws[pc] * e->phs[pc];
    }
  }
  return nk;
}
static void lk_o_build(void) {                                       /* everything of one frame from the snapshot */
  int x, y, k, a, o;
  const uint8 *chosen = lk_o_sp;                                      /* pass the figures come from */
  lk_o_sp = lk_o_r;                                                   /* tile animation + palettes: current pass */
  /* tiles + animation */
  memcpy(lk_o_tiles, lk_o_tbase, sizeof lk_o_tiles);
  for (k = 0; k < lk_o_ngrp; k++) {
    int s0 = 0xFF1134 + 4 * k;
    if (getenv("LANDSTALKER_OWN_ANIM")) printf("ownanim: frame %ld grp %d state %02X %02X %02X %02X (delay %d frames %d dest %X words %d)\n", platform_frame_number(), k, SB(s0) & 255, SB(s0 + 1) & 255, SB(s0 + 2) & 255, SB(s0 + 3) & 255, lk_o_grp[k].delay, lk_o_grp[k].frames, lk_o_grp[k].dest, lk_o_grp[k].words);
    if (SB(s0) == lk_o_grp[k].delay && SB(s0 + 1) == lk_o_grp[k].frames) {
      int f = SB(s0 + 3) % lk_o_grp[k].frames, n = lk_o_grp[k].words * 2, i; uint32_t src = lk_o_grp[k].base + (uint32_t)(f * n);
      for (i = 0; i < n; i++) if (lk_o_grp[k].dest + i < (int)sizeof lk_o_tiles) lk_o_tiles[lk_o_grp[k].dest + i] = (uint8)OB(src + (uint32_t)i);
    }
  }
  /* layers */
  memset(lk_o_pa, 0, sizeof lk_o_pa); memset(lk_o_pb, 0, sizeof lk_o_pb);
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
    int lay;
    for (lay = 0; lay < 2; lay++) {
      int id = UW((lay ? 0xFF7C02 : 0xFFA6CA) + 148 * y + 2 * x) & 0x3FF, c0 = 2 * (x - y) + (lay ? 146 : 148), r0 = x + y;
      if (!id) continue;
      for (k = 0; k < 4; k++) {
        int w = UW(0xFF5C02 + 2 * (4 * id + k)), cc = c0 + (k & 1), rr = r0 + (k >> 1);
        if (cc >= 0 && cc < 304 && rr >= 0 && rr < 152) (lay ? lk_o_pa : lk_o_pb)[rr][cc] = 0x10000u | (uint32_t)w;
      }
    }
  }
  lk_o_exon = 0; lk_o_sprites(chosen, 1, 0, lk_o_simple ? 0 : chosen == lk_o_cc ? lk_o_cp : lk_o_cc); lk_o_sp = lk_o_r;   /* pass 1: which table entries do the figures account for */
  memcpy(lk_o_dk2, lk_o_dk, sizeof lk_o_dk); lk_o_dn2 = lk_o_dn;
  lk_o_exon = 1; lk_o_exnext = 0; lk_o_sprites(chosen, 1, 0, lk_o_simple ? 0 : chosen == lk_o_cc ? lk_o_cp : lk_o_cc); lk_o_sp = lk_o_r;   /* pass 2: the same figures with the other table entries drawn between them */
  lk_o_extras_upto(1 << 20); lk_o_exon = 0;
  (void)o;
}
static int lk_o_fetch(uint32 (*pl)[304], int U, int V, int *pal, int *prio, lk_o_fi_t *fi) {   /* colour index of one plane pixel at image position (U, V), 0 = transparent */
  int tc = U >> 3, tr = V >> 3, ix = U & 7, iy = V & 7; uint32 c; int w, t, b;
  if (U < 0 || V < 0 || tc >= 304 || tr >= 152) return 0;
  c = pl[tr][tc]; if (!(c & 0x10000)) return 0;
  w = (int)(c & 0xFFFF); if (w & 0x800) ix = 7 - ix; if (w & 0x1000) iy = 7 - iy;
  t = w & 0x7FF; if (t * 32 + 31 >= (int)sizeof lk_o_tiles) return 0;
  b = lk_o_tiles[t * 32 + iy * 4 + ix / 2]; *pal = (w >> 13) & 3; *prio = (w >> 15) & 1;
  if (fi) { fi->t = &lk_o_tiles[t * 32]; fi->ix = ix; fi->iy = iy; fi->hf = (w >> 11) & 1; fi->vf = (w >> 12) & 1; }
  return (ix % 2 == 0) ? (b >> 4) : (b & 15);
}

/* ---- HUD tilemap from the game state (port of hud.asm: RefreshAllHUD $01690A .. UpdateSmallHeartHUD $016B2E, SwordChargeTiles $016CF4), rows 0..2 of the window plane ---- */
static int lk_o_hw[3][64], lk_o_hwok, lk_o_hwmode = 1, lk_o_hwfr, lk_o_hwlast[4], lk_o_hwlog;
static int lk_o_hdig[10];
static void lk_o_b10(long v) { int i, k; static const long p10[10] = {1000000000L, 100000000L, 10000000L, 1000000L, 100000L, 10000L, 1000L, 100L, 10L, 1L};   /* ConvertToBase10 $000FDA: digit + 1, leading zeros (not the last) become 0 */
  for (i = 0; i < 10; i++) { k = 0; do { k++; v -= p10[i]; } while (v >= 0); v += p10[i]; lk_o_hdig[i] = k; }
  for (i = 0; i < 9 && lk_o_hdig[i] == 1; i++) lk_o_hdig[i] = 0; }
static void lk_o_hdraw(int k, int w) { int d = lk_o_hdig[k], t = 0x66BC, b = 0x66BA; if (d) { t = 0x66BF + d; b = t + 0x10; } lk_o_hw[1][w] = t; lk_o_hw[2][w] = b; }   /* GetHUDDigitTiles $01694C + UpdateHUDDigits */
static void lk_o_hhalf(int *a0, int d0) { (*a0)--; lk_o_hw[1][*a0] = d0; lk_o_hw[2][*a0] = d0 + 0x10; }   /* sub_16B22 */
static void lk_o_hudbuild(void) {
  int r, c, i, cur, mx, d0, d2, d3, a0, n, base;
  lk_o_hwok = 0;
  if (!lk_o_hwmode) return;
  for (r = 0; r < 3; r++) for (c = 0; c < 64; c++) lk_o_hw[r][c] = (c < 40) ? (OW(0x9152 + 2 * (r * 40 + c)) | 0x6000) : 0;   /* LoadHUDTiles: StatusBarTilemap from the ROM */
  if (lk_o_room >= 139 && lk_o_room <= 143) { for (r = 0; r < 3; r++) for (c = 0; c < 40; c++) lk_o_hw[r][c] = 0xE6B4; lk_o_hwok = 1; return; }   /* the intro rooms 139..143 (INTRO_139.., LoadHUDTiles blanks the HUD at the start in room $8B and nothing refills it before room 148) have a blank HUD */
  cur = SW(0xFF543E) & 0xFFFF; mx = SW(0xFF547E) & 0xFFFF;
  d2 = (cur ? ((cur + 0x100) & 0xFFFF) : 0) >> 8; d3 = (mx ? ((mx + 0x100) & 0xFFFF) : 0) >> 8;
  lk_o_b10(d2); if (lk_o_hdig[7]) lk_o_hdig[8] = lk_o_hdig[9] = 0x0A; lk_o_hdraw(8, 23); lk_o_hdraw(9, 24);   /* current health (hearts) */
  lk_o_b10(d3); if (lk_o_hdig[7]) lk_o_hdig[8] = lk_o_hdig[9] = 0x0A; lk_o_hdraw(8, 26); lk_o_hdraw(9, 27);   /* max health */
  { int g = SW(0xFF120E) & 0xFFFF; lk_o_b10(g); if (lk_o_hdig[5]) lk_o_hdig[6] = lk_o_hdig[7] = lk_o_hdig[8] = lk_o_hdig[9] = 0x0A; for (i = 0; i < 4; i++) lk_o_hdraw(6 + i, 33 + i); }   /* gold, capped at 9999 */
  { int q = SB(0xFF1040) & 15; q = (q - 1 < 0) ? 0 : q - 1; lk_o_b10(q); if (lk_o_hdig[8]) lk_o_hdig[9] = 0x0A; lk_o_hdraw(9, 31); }   /* EkeEke (item $00: low nibble of the first inventory byte, minus 1) */
  n = SB(0xFF120A); base = 0x16CF4 + n * 7; for (i = 0; i < 7; i++) lk_o_hw[1][4 + i] = OB(base + i) + 0x66B4;   /* sword charge */
  for (i = 0; i < 12; i++) { lk_o_hw[2][11 + i] = 0x66BA; lk_o_hw[1][11 + i] = 0x66BC; }   /* InitHeartHUD */
  { int t = 0x66E3; if (d2 >= 0x33 || d3 >= 0x33) { if (d2 < 0x33) t = 0x66E2;   /* UpdateBigHeartHUD */
      lk_o_hw[1][11] = t; lk_o_hw[1][12] = t | 0x800; lk_o_hw[2][11] = t + 0x10; lk_o_hw[2][12] = (t + 0x10) | 0x800; } }
  a0 = 18; if (d2 >= 0x33) d2 -= 0x32;                                       /* UpdateMediumHeartHUD (the label jumps of the asm are kept) */
  if (d2 >= 0x0B) goto l16AC4;
  if (d3 < 0x0B) goto small;
  lk_o_hhalf(&a0, 0x66E0); d0 = 0x66CB; if (d3 < 0x15) goto l16AC2; d0 = 0x66CD;
l16A9A: lk_o_hhalf(&a0, d0); d0 = 0x66CB; if (d3 < 0x1F) goto l16AC2; d0 = 0x66CD;
l16AAC: lk_o_hhalf(&a0, d0); d0 = 0x66CB; if (d3 < 0x29) goto l16AC2; d0 = 0x66CD;
l16ABC: lk_o_hhalf(&a0, d0); d0 = 0x66CB;
l16AC2: lk_o_hhalf(&a0, d0); goto small;
l16AC4: lk_o_hhalf(&a0, 0x66E1); if (d2 >= 0x15) goto l16AE0; d0 = 0x66CC; if (d3 < 0x15) { lk_o_hhalf(&a0, d0); goto small; } d0 = 0x66CF; goto l16A9A;
l16AE0: lk_o_hhalf(&a0, 0x66CE); if (d2 >= 0x1F) goto l16AFC; d0 = 0x66CC; if (d3 < 0x1F) { lk_o_hhalf(&a0, d0); goto small; } d0 = 0x66CF; goto l16AAC;
l16AFC: lk_o_hhalf(&a0, 0x66CE); if (d2 >= 0x29) goto l16B18; d0 = 0x66CC; if (d3 < 0x29) { lk_o_hhalf(&a0, d0); goto small; } d0 = 0x66CF; goto l16ABC;
l16B18: lk_o_hhalf(&a0, 0x66CE); lk_o_hhalf(&a0, 0x66CC);
small:
  { int k; d0 = (d3 > 10 ? 10 : d3) * 10;                                    /* UpdateSmallHeartHUD */
    for (k = 0; k < 5; k++, d0++) lk_o_hw[1][18 + k] = OB(0x16BCE + d0) + 0x66B4;
    for (k = 0; k < 5; k++, d0++) lk_o_hw[2][18 + k] = OB(0x16BCE + d0) + 0x66B4;
    if (d2) { int rm = d2 % 10, ok = 1; if (!rm) rm = 10; d0 = rm * 10;
      for (k = 0; k < 5 && ok; k++, d0++) { int d1 = OB(0x16BCE + d0); if (d1 < 10) { ok = 0; break; } if (d1 == 0x30 && lk_o_hw[2][18 + k] == 0x66E8) d1 += 2; lk_o_hw[1][18 + k] = d1 + 0x66B5; }
      for (k = 0; k < 5 && ok; k++, d0++) { int d1 = OB(0x16BCE + d0); if (d1 < 10) { ok = 0; break; } lk_o_hw[2][18 + k] = d1 + 0x66B5; } } }
  lk_o_hwok = 1;
  { int diff = 0; for (r = 0; r < 3; r++) for (c = 0; c < 40; c++) if (lk_o_hw[r][c] != SW(0xFF1C00 + 0x80 * r + 2 * c)) { if (!diff) { lk_o_hwlast[0] = r; lk_o_hwlast[1] = c; lk_o_hwlast[2] = lk_o_hw[r][c]; lk_o_hwlast[3] = SW(0xFF1C00 + 0x80 * r + 2 * c); } diff++; }
    if (diff) { lk_o_hwfr++; if (lk_o_hwlog > 1) { static int once; if (once++ < 3) for (r = 1; r < 3; r++) { printf("own: HUD row %d mine :", r); for (c = 4; c < 37; c++) printf(" %04X", lk_o_hw[r][c] & 0xFFFF); printf("\nown: HUD row %d game :", r); for (c = 4; c < 37; c++) printf(" %04X", SW(0xFF1C00 + 0x80 * r + 2 * c) & 0xFFFF); printf("\n"); } } if (lk_o_hwlog) printf("own: HUD differs frame %ld room %d in %d words, first row %d col %d mine %04X game %04X (cur %d max %d)\n", platform_frame_number(), lk_o_room, diff, lk_o_hwlast[0], lk_o_hwlast[1], lk_o_hwlast[2] & 0xFFFF, lk_o_hwlast[3] & 0xFFFF, d2, d3); } }
}
extern uint8_t lk_vb_ram[]; extern int lk_vb_n; extern long lk_vb_frame;   /* VBlank snapshot (patch_ownvb.py) */
static int lk_o_vbmode = 1, lk_o_vblog, lk_o_regvdp;   /* (LANDSTALKER_OWN_SIMPLE=1: the sprites of the snapshot are drawn as they are (no choice between candidate entity states by comparison with the VDP's sprite table / tiles) */   /* LANDSTALKER_OWN_REGS_VDP=1: VDP registers read from the VDP (old way) instead of the game's RAM shadows $FF0FB0 + 2 n */
#define LK_REG(n) (lk_o_regvdp ? reg[n] : bus_get_ram()[(0x0FB1 + 2 * (n)) ^ 1])   /* the LIVE shadow (MaskVDPReg / OrVDPReg keep it equal to the VDP register): the snapshot is taken at the last VBlank, the main code disables the display later (room load) */
#define LK_SATB(o) ((lk_o_vbmode && lk_vb_n) ? lk_vb_ram[((0xFF0550 + (o)) & 0xFFFF) ^ 1] : vram[(base + (o)) ^ 1])   /* sprite table byte: the RAM snapshot (DMA source $FF0550, equal to the VDP's copy in every map frame) or the VDP */   /* LANDSTALKER_OWN_VB=0 = the old two-snapshot way */
extern uint8_t lk_ot_vis[]; extern int lk_ot_ok; extern int lk_ot_check(const uint8_t *vram); extern void lk_ot_dbg(const uint8_t *vram, long frame);   /* own text tile mirror (patch_owntext.py) */
static int lk_o_txmode = 1, lk_o_txlog;
static int lk_o_win(int line, int x, int hint) {                      /* window plane pixel (palette * 16 + index) or -1 = none: HUD rows 0..2, text box rows 20..27 (tilemap in RAM, tiles from ROM / the text tile buffer) */
  int r = line >> 3, w, t, b, ix = x & 7, iy = line & 7;
  if (line < 24) { w = (lk_o_hwok && r < 3) ? lk_o_hw[r][x >> 3] : SW(0xFF1C00 + 0x80 * r + 2 * (x >> 3)); }
  else if (line >= 160 && (hint & 0xFF) == 0xA0) { w = lk_o_txmode ? (OW(0x23900 + 2 * ((r - 20) * 40 + (x >> 3))) | 0x6000) : SW(0xFF2600 + 0x80 * (r - 20) + 2 * (x >> 3)); }   /* LoadTextboxTilemap $0234B2: TextBoxTilemap $023900 | $6000 */
  else return -1;
  if (w & 0x800) ix = 7 - ix; if (w & 0x1000) iy = 7 - iy;
  t = w & 0x7FF; lk_o_wfi.t = 0; lk_o_wfi.ix = ix; lk_o_wfi.iy = iy; lk_o_wfi.hf = (w >> 11) & 1; lk_o_wfi.vf = (w >> 12) & 1;
  if (t >= 0x6B4 && t < 0x6B4 + 76) { b = lk_o_hud[(t - 0x6B4) * 32 + iy * 4 + ix / 2]; lk_o_wfi.t = &lk_o_hud[(t - 0x6B4) * 32]; }
  else if (t >= 0x528 && t < 0x528 + 0xD8) { b = (lk_o_txmode && lk_ot_ok) ? lk_ot_vis[(t - 0x528) * 32 + iy * 4 + ix / 2] : SB(0xFF3900 + (t - 0x528) * 32 + iy * 4 + ix / 2); if (lk_o_txmode && lk_ot_ok) lk_o_wfi.t = &lk_ot_vis[(t - 0x528) * 32]; }
  else b = 0;
  return ((w >> 13) & 3) * 16 + ((ix % 2 == 0) ? (b >> 4) : (b & 15)) + 0x100 + ((w & 0x8000) ? 0x200 : 0);     /* bit 8 marks 'window pixel' (index 0 = backdrop), bit 9 = its priority bit */
}
static int lk_o_unwrap(int p, int base, int size) { int d = (((p - base) % size) + size) % size; if (d >= size / 2) d -= size; return base + d; }

static void lk_o_init(void) {
  lk_o_hide0 = !(getenv("LANDSTALKER_OWN_HIDE0") && *getenv("LANDSTALKER_OWN_HIDE0") == '0'); lk_o_actcram = getenv("LANDSTALKER_OWN_ACT_CRAM") != NULL; lk_o_fl_log = getenv("LANDSTALKER_OWN_FADELOG") != NULL; lk_o_scrram = getenv("LANDSTALKER_OWN_SCROLL_VDP") == NULL; lk_o_regvdp = getenv("LANDSTALKER_OWN_REGS_VDP") != NULL; lk_o_simple = 1; { const char *q3 = getenv("LANDSTALKER_OWN_SIMPLE"); if (q3) lk_o_simple = atoi(q3); } lk_o_scrvars = getenv("LANDSTALKER_OWN_SCRVARS") != NULL; { const char *q4 = getenv("LANDSTALKER_OWN_VMIRROR"); if (q4) lk_o_vmirror = atoi(q4); } { const char *q5 = getenv("LANDSTALKER_OWN_NIGELVRAM"); if (q5) lk_o_nigelvram = atoi(q5); } lk_o_gshake = getenv("LANDSTALKER_OWN_GSHAKE") != NULL; lk_o_fx = 1; { const char *q6 = getenv("LANDSTALKER_OWN_FX"); if (q6) lk_o_fx = atoi(q6); } { const char *q7 = getenv("LANDSTALKER_OWN_FXOFF"); if (q7) lk_o_fxoff = atoi(q7); } { const char *q9 = getenv("LANDSTALKER_OWN_SEED"); if (q9) lk_o_seed = atoi(q9); }
  if (lk_o_mode >= 0) return;
  { const char *e = getenv("LANDSTALKER_OWN"), *l = getenv("LANDSTALKER_OWN_LOG"), *q; int v = 1;   /* default On since 2026-10-22 (user: 'mach den eigenen renderer zum standard'); a saved ~/.landstalker_own wins */
    if (e) lk_o_mode = atoi(e);
    else { char path[512]; FILE *f; const char *h = getenv("HOME"); snprintf(path, sizeof path, "%s/.landstalker_own", h ? h : "."); f = fopen(path, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } lk_o_mode = v ? 2 : 0; }   /* Options > Video > Own Renderer */
    if (l) lk_o_log = atoi(l);
    q = getenv("LANDSTALKER_OWN_HUD"); if (q) lk_o_hwmode = atoi(q); q = getenv("LANDSTALKER_OWN_VB"); if (q) lk_o_vbmode = atoi(q); q = getenv("LANDSTALKER_OWN_VBLOG"); if (q) lk_o_vblog = atoi(q); q = getenv("LANDSTALKER_OWN_TEXT"); if (q) lk_o_txmode = atoi(q); q = getenv("LANDSTALKER_OWN_TEXTLOG"); if (q) lk_o_txlog = atoi(q); q = getenv("LANDSTALKER_OWN_HUDLOG"); if (q) lk_o_hwlog = atoi(q); q = getenv("LANDSTALKER_OWN_SPR"); if (q) lk_o_sprmode = atoi(q); q = getenv("LANDSTALKER_OWN_PAL"); if (q) lk_o_palmode = atoi(q); q = getenv("LANDSTALKER_OWN_CAM"); if (q) lk_o_cammode = atoi(q); }
}
int lk_own_get(void) { lk_o_init(); return lk_o_mode == 2; }
void lk_own_set(int v) {                                             /* Options > Video > Own Renderer On / Off, saved in ~/.landstalker_own */
  char path[512]; FILE *f; const char *h = getenv("HOME");
  lk_o_init(); lk_o_mode = v ? 2 : 0; lk_o_valid = 0;
  snprintf(path, sizeof path, "%s/.landstalker_own", h ? h : "."); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", v ? 1 : 0); fclose(f); }
}
static int lk_hd_saved = -1;
int lk_hd_get(void) {                                               /* Options > Video > HD Graphics: the SAVED setting (~/.landstalker_hd, LANDSTALKER_HD overrides at start); the tile packs and the HD buffers are set up at start, so a change applies at the next start */
  if (lk_hd_saved < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_HD"); char path[512]; FILE *f; int v = 0; snprintf(path, sizeof path, "%s/.landstalker_hd", h ? h : "."); f = fopen(path, "r"); if (f) { if (fscanf(f, "%d", &v) != 1) v = 0; fclose(f); } if (e && *e) v = atoi(e); lk_hd_saved = v ? 1 : 0; }
  return lk_hd_saved;
}
void lk_hd_set(int v) {
  char path[512]; FILE *f; const char *h = getenv("HOME");
  lk_hd_saved = v ? 1 : 0;
  snprintf(path, sizeof path, "%s/.landstalker_hd", h ? h : "."); f = fopen(path, "w"); if (f) { fprintf(f, "%d\n", lk_hd_saved); fclose(f); }
}
/* ---- stage 1: a generic screen renderer (title, menus, island map, credits ...): the picture of a line composed by our own code from the VDP's memory state (planes A / B, window, sprites, priorities, scroll modes, backdrop),
   checked pixel by pixel against the game's picture (LANDSTALKER_OWN_SCREENS: 0 off, 1 compare + log only, 2 draw (default with the own renderer on), LANDSTALKER_OWN_SCRLOG=1 prints the differing pixels of every frame it handled) ---- */
static int lk_scr_mode = -1, lk_scr_log, lk_o_why;   /* lk_o_why: why the own map path did not draw this frame (1 old room still showing, 2 warp effect, 3 Start menu running, 4 display off, 5 no room) */ static long lk_scr_diff, lk_scr_tot, lk_scr_lines;
#define LK_VB(a) vram[((a) & 0xFFFF) ^ 1]
#define LK_VW(a) (((unsigned)LK_VB(a) << 8) | LK_VB((a) + 1))
extern int lk_org_lookup(const uint8_t *vram, int tile, uint32_t *rom, int *idx); extern int lk_org_count(void);   /* tools/patch_gfxorg.py */
static int lk_scr_tc[2048], lk_scr_tpal[2048], lk_scr_curpal, lk_org_log = -1, lk_dump_on; static const char *lk_dump_dir;   /* opaque tile pixels seen this frame per tile (LANDSTALKER_OWN_ORGLOG) */
/* ---- tile replacement (stage 2 test of the HD path): a tile whose ORIGIN (ROM block, tile index, tools/patch_gfxorg.py) has an entry is drawn from the entry instead of the VRAM pixels.
   Only with HD graphics On (LANDSTALKER_HD=1 or ~/.landstalker_hd = 1, default Off).  Entries: LANDSTALKER_TILEPACK=dir (default ~/.landstalker_tilepack): files `XXXXXX_NNNN.rgba` (XXXXXX = hex ROM address of the compressed block, NNNN = decimal tile index in it, 8 x 8 x RGBA = 256 bytes,
   alpha 0 = keep the game's pixel), and the test rule LANDSTALKER_TILETEST="0386E4,03DF8A:12" (a whole block, or one tile `block:index`): the tile is tinted magenta (shading kept).  Screen renderer only. ---- */
#include <dirent.h>
#include <sys/stat.h>
typedef struct { uint32_t key; int kind, nf; uint32_t *tex; uint8_t *raw; uint8_t *idx; } lk_rep_t;   /* kind 3 = palette index image (`.idx`, 64 * nf * nf bytes, 0 = transparent): drawn through the LIVE palette, so fades / flashes / palette animation keep working; idx = resampled to the global scale */   /* kind 1 = test tint, 2 = image: raw = file (nf x nf per pixel of the 8 x 8 tile), tex = ARGB at the global HD scale */
#define LK_REP_N 8192
#define LK_HDW 416   /* HD rows / refs cover the widest picture (320 + 2 * 48); screen column x of the centre 320 is index x + LK_HDO */
#define LK_HDO 48
int lk_hd_n; uint32_t *lk_hd_rows, *lk_hd_ref; long lk_hd_stamp[224], lk_hd_gen;   /* HD graphics: scale (0 = Off), HD pixels of the composed lines [224 * n][320 * n], the 1x pixels they refine, validity stamps (read by platform_sdl.c, tools/patch_hd.py) */
static lk_rep_t *lk_rep_tab[LK_REP_N]; static int lk_rep_on = -1, lk_rep_cnt;
static int lk_scr_rgb = -1;                                          /* set by lk_scr_ci: 24 bit colour of a replaced pixel, or -1 */
static lk_rep_t *lk_scr_prep; static int lk_scr_pox, lk_scr_poy;     /* set by lk_scr_ci: the replacement entry of the tile and the pixel inside the tile (tile space) */
static lk_rep_t *lk_rep_find(uint32_t key) { uint32_t i = (key * 2654435761u) >> 19 & (LK_REP_N - 1); while (lk_rep_tab[i]) { if (lk_rep_tab[i]->key == key) return lk_rep_tab[i]; i = (i + 1) & (LK_REP_N - 1); } return 0; }
static lk_rep_t *lk_rep_add(uint32_t key) { uint32_t i = (key * 2654435761u) >> 19 & (LK_REP_N - 1); lk_rep_t *e; if (lk_rep_cnt > LK_REP_N * 3 / 4) return 0; while (lk_rep_tab[i]) { if (lk_rep_tab[i]->key == key) return lk_rep_tab[i]; i = (i + 1) & (LK_REP_N - 1); } e = (lk_rep_t *)calloc(1, sizeof *e); if (!e) return 0; e->key = key; lk_rep_tab[i] = e; lk_rep_cnt++; return e; }
#define LK_REP_KEY(rom, idx) ((((uint32_t)(rom) & 0xFFFFFF) << 8) ^ ((uint32_t)(idx) & 0xFF) ^ ((uint32_t)(idx) >> 8 << 24))   /* idx < 4096 */
static void lk_rep_init(void) {
  const char *t = getenv("LANDSTALKER_TILETEST"), *d = getenv("LANDSTALKER_TILEPACK"); char path[600], buf[256]; DIR *dir; int maxn = 1, i;
  lk_rep_on = 0;
  { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_HD"); int hd = 0; char hp[512]; FILE *hf;   /* HD graphics is OPTIONAL and Off by default: ~/.landstalker_hd (1 = On) or LANDSTALKER_HD=0|1; Off = no tile pack is read, no replacement happens, the picture stays the original */
    snprintf(hp, sizeof hp, "%s/.landstalker_hd", h ? h : "."); hf = fopen(hp, "r"); if (hf) { if (fscanf(hf, "%d", &hd) != 1) hd = 0; fclose(hf); } if (e && *e) hd = atoi(e);
    if (!hd) return; }
  if (t && *t) { snprintf(buf, sizeof buf, "%s", t); { char *tok, *sv; for (tok = strtok_r(buf, ",", &sv); tok; tok = strtok_r(NULL, ",", &sv)) { unsigned rom = (unsigned)strtoul(tok, NULL, 16); const char *c = strchr(tok, ':'); lk_rep_t *e; if (c) { e = lk_rep_add(LK_REP_KEY(rom, atoi(c + 1))); } else e = lk_rep_add(LK_REP_KEY(rom, 0xFFF)); if (e) { e->kind = 1; lk_rep_on = 1; } } } }
  if (!d || !*d) { const char *h = getenv("HOME"); snprintf(path, sizeof path, "%s/.landstalker_tilepack", h ? h : "."); } else snprintf(path, sizeof path, "%s", d);
  dir = opendir(path);
  if (dir) { struct dirent *de; while ((de = readdir(dir))) { unsigned rom; int idx; if (sscanf(de->d_name, "%6x_%4d.idx", &rom, &idx) == 2 && strstr(de->d_name, ".idx")) { char fp[900]; FILE *f; long sz; snprintf(fp, sizeof fp, "%s/%s", path, de->d_name); f = fopen(fp, "rb"); if (f) { int nf; fseek(f, 0, SEEK_END); sz = ftell(f); fseek(f, 0, SEEK_SET); nf = sz == 64 ? 1 : sz == 256 ? 2 : sz == 1024 ? 4 : sz == 4096 ? 8 : 0;
      if (nf) { lk_rep_t *e = lk_rep_add(LK_REP_KEY(rom, idx)); if (e) { e->raw = (uint8_t *)malloc((size_t)sz); if (e->raw && fread(e->raw, 1, (size_t)sz, f) == (size_t)sz) { e->kind = 3; e->nf = nf; lk_rep_on = 1; if (nf > maxn) maxn = nf; } else { free(e->raw); e->raw = 0; } } } fclose(f); } }
      else if (sscanf(de->d_name, "%6x_%4d.rgba", &rom, &idx) == 2) { char fp[900]; FILE *f; long sz; snprintf(fp, sizeof fp, "%s/%s", path, de->d_name); f = fopen(fp, "rb"); if (f) { int nf; fseek(f, 0, SEEK_END); sz = ftell(f); fseek(f, 0, SEEK_SET); nf = sz == 256 ? 1 : sz == 1024 ? 2 : sz == 4096 ? 4 : sz == 16384 ? 8 : 0;
      if (nf) { lk_rep_t *e = lk_rep_add(LK_REP_KEY(rom, idx)); if (e) { e->raw = (uint8_t *)malloc((size_t)sz); if (e->raw && fread(e->raw, 1, (size_t)sz, f) == (size_t)sz) { e->kind = 2; e->nf = nf; lk_rep_on = 1; if (nf > maxn) maxn = nf; } else { free(e->raw); e->raw = 0; } } } fclose(f); } } } closedir(dir); }
  { const char *sc = getenv("LANDSTALKER_HD_SCALE"); int n = sc ? atoi(sc) : maxn; if (n < 1) n = 1; if (n > 8) n = 8; if (n == 3) n = 2; if (n == 5 || n == 6 || n == 7) n = 4; lk_hd_n = (lk_rep_on || sc) ? n : 0; }   /* the HD picture exists when HD is On and something is to be shown at a higher resolution (a pack) or the scale is asked for */
  for (i = 0; i < LK_REP_N; i++) { lk_rep_t *e = lk_rep_tab[i]; if (e && e->kind == 3 && e->raw) { int N = lk_hd_n ? lk_hd_n : 1, x, y; e->idx = (uint8_t *)malloc((size_t)64 * N * N); if (e->idx) for (y = 0; y < 8 * N; y++) for (x = 0; x < 8 * N; x++) e->idx[y * 8 * N + x] = e->raw[(y * e->nf / N) * 8 * e->nf + (x * e->nf / N)]; }
    if (e && e->kind == 2 && e->raw) { int N = lk_hd_n ? lk_hd_n : 1, x, y; e->tex = (uint32_t *)malloc((size_t)64 * N * N * 4); if (e->tex) for (y = 0; y < 8 * N; y++) for (x = 0; x < 8 * N; x++) { const uint8_t *q = &e->raw[((y * e->nf / N) * 8 * e->nf + (x * e->nf / N)) * 4]; e->tex[y * 8 * N + x] = q[3] ? (0xFF000000u | (uint32_t)q[0] << 16 | (uint32_t)q[1] << 8 | q[2]) : 0; } } }   /* nearest resample to the global scale; alpha 0 = 0 = keep the game's pixel */
  if (lk_hd_n) { lk_hd_rows = (uint32_t *)calloc((size_t)224 * lk_hd_n * LK_HDW * lk_hd_n, 4); lk_hd_ref = (uint32_t *)calloc((size_t)224 * LK_HDW, 4); if (!lk_hd_rows || !lk_hd_ref) lk_hd_n = 0; }
  if (lk_rep_on || lk_hd_n) printf("tile replacement: %d entries, HD scale %d\n", lk_rep_cnt, lk_hd_n);
}
static int lk_scr_cramw(int i);
static void lk_tile_dump(int tile, int pal) {   /* LANDSTALKER_TILEDUMP=dir: authoring aid, writes every tile of known origin once as 8 x 8 RGBA (1x, the palette line of its first use) named like a tile pack entry: `XXXXXX_NNNN.rgba` */
  static uint32_t done[16384]; uint32_t rom; int idx, y, x; uint32_t key, h; char path[900]; uint8_t out[256]; FILE *f;
  if (!lk_org_lookup(vram, tile, &rom, &idx)) return;
  key = LK_REP_KEY(rom, idx) | 1u; h = (key * 2654435761u) >> 18 & 16383;
  while (done[h]) { if (done[h] == key) return; h = (h + 1) & 16383; }
  done[h] = key;
  for (y = 0; y < 8; y++) for (x = 0; x < 8; x++) { int b = LK_VB(tile * 32 + y * 4 + (x >> 1)), ci = (x & 1) ? (b & 15) : (b >> 4); uint32_t c = pixel_lut[1][lk_scr_cramw(pal * 16 + ci)]; uint8_t *q = &out[(y * 8 + x) * 4]; q[0] = (uint8_t)(c >> 16); q[1] = (uint8_t)(c >> 8); q[2] = (uint8_t)c; q[3] = ci ? 255 : 0; }
  snprintf(path, sizeof path, "%s/%06X_%04d.rgba", lk_dump_dir, rom, idx); f = fopen(path, "wb"); if (f) { fwrite(out, 1, 256, f); fclose(f); }
  { uint8_t ix[64]; for (y = 0; y < 8; y++) for (x = 0; x < 8; x++) { int b = LK_VB(tile * 32 + y * 4 + (x >> 1)); ix[y * 8 + x] = (uint8_t)((x & 1) ? (b & 15) : (b >> 4)); }
    snprintf(path, sizeof path, "%s/%06X_%04d.idx", lk_dump_dir, rom, idx); f = fopen(path, "wb"); if (f) { fwrite(ix, 1, 64, f); fclose(f); } }
}
static lk_rep_t *lk_rep_get(int tile) {                              /* replacement entry of a VRAM tile (looked up by the tile's origin), cached for the frame */
  static long fr[2048]; static lk_rep_t *ent[2048]; uint32_t rom; int idx; lk_rep_t *e = 0;
  if (fr[tile] == platform_frame_number() + 1) return ent[tile];
  if (lk_org_lookup(vram, tile, &rom, &idx)) { e = lk_rep_find(LK_REP_KEY(rom, idx)); if (!e) e = lk_rep_find(LK_REP_KEY(rom, 0xFFF)); }
  fr[tile] = platform_frame_number() + 1; ent[tile] = e; return e;
}
static int lk_scr_ci(int tile, int px, int py, int hf, int vf) { int ox = hf ? 7 - px : px, oy = vf ? 7 - py : py, b = LK_VB(tile * 32 + oy * 4 + (ox >> 1)), ci = (ox & 1) ? (b & 15) : (b >> 4); lk_scr_rgb = -1; lk_scr_prep = 0; if (ci && (lk_org_log > 0 || lk_dump_on)) { lk_scr_tc[tile & 0x7FF]++; lk_scr_tpal[tile & 0x7FF] = lk_scr_curpal; }
  if (ci && lk_rep_on) { lk_rep_t *e = lk_rep_get(tile & 0x7FF);
    if (e && e->kind == 1) lk_scr_rgb = (255 << 16) | ((ci * 17) << 8) | (255 - ci * 8);
    else if (e && e->kind == 3 && e->idx) { lk_scr_prep = e; lk_scr_pox = ox; lk_scr_poy = oy; }   /* the 1x pixel stays the game's, only the HD picture differs */
    else if (e && e->kind == 2 && e->tex) { int N = lk_hd_n ? lk_hd_n : 1; uint32_t c = e->tex[(oy * N + N / 2) * 8 * N + ox * N + N / 2]; if (c) { lk_scr_rgb = (int)(c & 0xFFFFFF); lk_scr_prep = e; lk_scr_pox = ox; lk_scr_poy = oy; } } }
  return ci; }
static void lk_tile_dump_raw(const uint8 *t, int pal) {              /* LANDSTALKER_TILEDUMP for the own map path's tiles (room tiles, figures, HUD): same files as lk_tile_dump, colours from the own palette */
  static uint32_t done[16384]; uint32_t rom, key, h; int idx, y, x; char path[900]; uint8_t out[256]; FILE *f;
  if (!lk_org_lookup_raw(t, &rom, &idx)) return;
  key = LK_REP_KEY(rom, idx) | 1u; h = (key * 2654435761u) >> 18 & 16383;
  while (done[h]) { if (done[h] == key) return; h = (h + 1) & 16383; }
  done[h] = key;
  for (y = 0; y < 8; y++) for (x = 0; x < 8; x++) { int b = t[y * 4 + (x >> 1)], ci = (x & 1) ? (b & 15) : (b >> 4); uint32_t c = lk_o_pix[(pal * 16 + ci) & 0x3F]; uint8_t *q = &out[(y * 8 + x) * 4]; q[0] = (uint8_t)(c >> 16); q[1] = (uint8_t)(c >> 8); q[2] = (uint8_t)c; q[3] = ci ? 255 : 0; }
  snprintf(path, sizeof path, "%s/%06X_%04d.rgba", lk_dump_dir, rom, idx); f = fopen(path, "wb"); if (f) { fwrite(out, 1, 256, f); fclose(f); }
  { uint8_t ix[64]; for (y = 0; y < 8; y++) for (x = 0; x < 8; x++) { int b = t[y * 4 + (x >> 1)]; ix[y * 8 + x] = (uint8_t)((x & 1) ? (b & 15) : (b >> 4)); }
    snprintf(path, sizeof path, "%s/%06X_%04d.idx", lk_dump_dir, rom, idx); f = fopen(path, "wb"); if (f) { fwrite(ix, 1, 64, f); fclose(f); } }
}
static long lk_o_orgk, lk_o_orgu, lk_o_sprk, lk_o_spru;                                    /* LANDSTALKER_OWN_ORGLOG for the map path: opaque pixels of the winning layer with / without a known origin, this frame */
static int lk_o_hdwant(void) { return lk_rep_on > 0 || lk_dump_on || lk_org_log > 0; }
static void *lk_o_repfor(const uint8 *t32, int pal, int cache) {    /* replacement entry of a tile image of the own map path (NULL = none); `cache`: the pointer is stable for the frame (plane / window tiles) */
  static struct { const uint8 *p; long fr; void *e; } c[8192]; uint32_t rom; int idx, known; lk_rep_t *e = 0; long fr = platform_frame_number() + 1; size_t ci = ((uintptr_t)t32 >> 5) & 8191;
  if (!t32) return 0;
  if (cache && c[ci].p == t32 && c[ci].fr == fr) return c[ci].e;
  known = lk_org_lookup_raw(t32, &rom, &idx); if (lk_org_log > 0 && !cache) { int z = 1, q; for (q = 0; q < 32; q++) if (t32[q]) { z = 0; break; } if (!z) { if (known) lk_o_sprk++; else { lk_o_spru++; if (getenv("LANDSTALKER_OWN_SPRUNK") && platform_frame_number() % 60 == 0) printf("ownsprunk: frame %ld sgi %d anim %d frm %d tile %02X%02X%02X%02X\n", platform_frame_number(), lk_o_dbgsgi, lk_o_dbganim, lk_o_dbgfrm, t32[0], t32[1], t32[2], t32[3]); } } }
  if (known) { if (lk_rep_on > 0) { e = lk_rep_find(LK_REP_KEY(rom, idx)); if (!e) e = lk_rep_find(LK_REP_KEY(rom, 0xFFF)); } if (lk_dump_on) lk_tile_dump_raw(t32, pal); }
  if (cache) { c[ci].p = t32; c[ci].fr = fr; c[ci].e = e; }
  return e;
}
typedef struct { lk_rep_t *rep; int ox, oy, hf, vf, pal; } lk_pi_t;   /* what the HD picture needs to know about a winning pixel: its replacement entry, the pixel inside the tile (tile space), the flips */
static int lk_scr_phf, lk_scr_pvf;
static int lk_scr_cramw(int i);
static int lk_hd_mapmode;                                            /* 1 while the own map path fills the HD rows (colours of the own palette, fade / warp variants) */
static PIXEL_OUT_T lk_o_colour(int line, int pick) { return lk_o_palmode ? (lk_o_fxon ? lk_o_fxpix[lk_o_fxk[line & 255]][pick & 0x3F] : lk_o_pix[pick & 0x3F]) : pixel[pick & 0x3F]; }
static void lk_hd_put(int line, int x, uint32_t col, const lk_pi_t *pi) {   /* one 1x pixel -> its n x n block of the HD rows: the replacement texture where there is one (alpha 0 = the game's colour), else the colour repeated */
  int N = lk_hd_n, sx, sy; uint32_t *dst = lk_hd_rows + (size_t)(line * N) * LK_HDW * N + (size_t)(x + LK_HDO) * N;
  for (sy = 0; sy < N; sy++) for (sx = 0; sx < N; sx++) { uint32_t c = col; if (pi && pi->rep) { int tp = (pi->oy * N + (pi->vf ? N - 1 - sy : sy)) * 8 * N + pi->ox * N + (pi->hf ? N - 1 - sx : sx); if (pi->rep->kind == 2 && pi->rep->tex) { uint32_t t = pi->rep->tex[tp]; if (t) c = t; } else if (pi->rep->kind == 3 && pi->rep->idx && pi->rep->idx[tp]) c = lk_hd_mapmode ? (uint32_t)lk_o_colour(line, pi->pal * 16 + pi->rep->idx[tp]) : pixel_lut[1][lk_scr_cramw(pi->pal * 16 + pi->rep->idx[tp])]; } dst[(size_t)sy * LK_HDW * N + sx] = c; }
}
static void lk_hd_plain(int line, const PIXEL_OUT_T *out) { int x; if (!lk_hd_n) return; for (x = 0; x < 320; x++) { lk_hd_put(line, x, out[x], 0); lk_hd_ref[line * LK_HDW + x + LK_HDO] = out[x]; } lk_hd_stamp[line] = lk_hd_gen; }
static int lk_scr_cell(int ent, int px, int py, int *prio) { int ci; lk_scr_curpal = (ent >> 13) & 3; ci = lk_scr_ci(ent & 0x7FF, px, py, (ent >> 11) & 1, (ent >> 12) & 1); lk_scr_phf = (ent >> 11) & 1; lk_scr_pvf = (ent >> 12) & 1; *prio = (ent >> 15) & 1; if (ci && lk_scr_rgb >= 0) return 0x1000000 | lk_scr_rgb; return ci ? ((ent >> 13) & 3) * 16 + ci : -1; }   /* bit 24 set = a replaced pixel (24 bit colour) */
static int lk_scr_cramw(int i) { return ((cram[(2 * i) ^ 1] << 8) | cram[(2 * i + 1) ^ 1]) & 0x1FF; }
static int lk_scr_line(int line, PIXEL_OUT_T *out, int e, int dispforce) {                /* returns 0 when the VDP is in a mode this renderer does not do (the game's picture stays) */
  int hm = reg[11] & 3, vm = (reg[11] >> 2) & 1, pwr = reg[16] & 3, phr = (reg[16] >> 4) & 3, pw, ph, x, i, n, cells;
  int baseA = (reg[2] & 0x38) << 10, baseB = (reg[4] & 7) << 13, wbase = (reg[3] & 0x3C) << 10, sat = (reg[5] & 0x7E) << 9;
  int hpos = (reg[17] & 0x1F) * 2, hright = reg[17] & 0x80, vpos = (reg[18] & 0x1F) * 8, vbelow = reg[18] & 0x80, vwin, hsA, hsB, hsb = (reg[13] & 0x3F) << 10, hidx;
  int bgcol = lk_scr_cramw(reg[7] & 0x3F);
  static int sp[320], spp[320]; static lk_pi_t spi[320]; int sl[32], nsl = 0, id, cnt, maxspr = (320 + 2 * e) >> 4;   /* the wide picture allows more sprites / sprite pixels per line (patch_wide: viewport.w >> 4, viewport.w >> 3 cells) */
  if (!(reg[12] & 1) || (reg[12] & 6) || hm == 1 || pwr == 2 || phr == 2 || (reg[1] & 8) || line >= 224) return 0;
  if (!(reg[1] & 0x40) && !dispforce) { for (x = 0; x < 320; x++) out[x] = pixel_lut[1][bgcol]; lk_hd_plain(line, out); return 1; }   /* display off: the backdrop */
  pw = pwr == 0 ? 32 : pwr == 1 ? 64 : 128; ph = phr == 0 ? 32 : phr == 1 ? 64 : 128;
  vwin = vbelow ? line >= vpos : line < vpos;
  hidx = hm == 0 ? 0 : hm == 3 ? line : (line & ~7);
  hsA = LK_VW(hsb + 4 * hidx) & 0x3FF; hsB = LK_VW(hsb + 4 * hidx + 2) & 0x3FF;
  for (x = 0; x < 320; x++) { sp[x] = -1; spi[x].rep = 0; }
  id = 0; cnt = 0; cells = (320 + 2 * e) >> 3;                                       /* sprites: the list in link order (max 80), 20 per line, 40 cells per line */
  for (n = 0; n < 80; n++) {
    int y = (int)(LK_VW(sat + 8 * id) & 0x1FF) - 128, sz = LK_VW(sat + 8 * id + 2), h = ((sz >> 8) & 3) + 1;
    if (line >= y && line < y + 8 * h) { if (nsl >= maxspr || nsl >= 32) break; sl[nsl++] = id; }
    id = sz & 0x7F; if (!id) break;
  }
  { int k, seen = 0, masked = 0;
    for (k = 0; k < nsl && !masked; k++) {
      int j = sl[k], y = (int)(LK_VW(sat + 8 * j) & 0x1FF) - 128, sz = LK_VW(sat + 8 * j + 2), at = LK_VW(sat + 8 * j + 4), xr = LK_VW(sat + 8 * j + 6) & 0x1FF, w = ((sz >> 10) & 3) + 1, h = ((sz >> 8) & 3) + 1, c, py, prio = (at >> 15) & 1, pal = (at >> 13) & 3, hf = (at >> 11) & 1, vf = (at >> 12) & 1;
      if (xr == 0 && seen) { masked = 1; break; }
      if (xr) seen = 1;
      if (cells <= 0) break;
      py = line - y; if (vf) py = 8 * h - 1 - py;
      for (c = 0; c < w && cells > 0; c++, cells--) {
        int col = hf ? w - 1 - c : c, tile = (at & 0x7FF) + col * h + (py >> 3), px;
        for (px = 0; px < 8; px++) { int sx = xr - 128 + c * 8 + px, ci = (lk_scr_curpal = pal, lk_scr_ci(tile, hf ? 7 - px : px, py & 7, 0, 0)); if (sx < 0 || sx >= 320 || !ci || sp[sx] >= 0) continue; sp[sx] = lk_scr_rgb >= 0 ? (0x1000000 | lk_scr_rgb) : pal * 16 + ci; spp[sx] = prio; spi[sx].rep = lk_scr_prep; spi[sx].ox = lk_scr_pox; spi[sx].oy = lk_scr_poy; spi[sx].hf = hf; spi[sx].vf = vf; spi[sx].pal = pal; }
      }
    }
  }
  for (x = 0; x < 320; x++) {
    int cA = -1, pA = 0, cB = -1, pB = 0, sel = -1, cc, xc = x >> 3; lk_pi_t iA, iB; const lk_pi_t *wi = 0; uint32_t col32; iA.rep = iB.rep = 0; iA.ox = iA.oy = iA.hf = iA.vf = iB.ox = iB.oy = iB.hf = iB.vf = 0;
    { int xp = (x - hsB) & (pw * 8 - 1), yp; yp = (line + (((vsram[((vm ? 4 * (x >> 4) : 0) + 2) ^ 1] << 8) | vsram[((vm ? 4 * (x >> 4) : 0) + 3) ^ 1]) & 0x3FF)) & (ph * 8 - 1);
      cB = lk_scr_cell(LK_VW(baseB + 2 * ((yp >> 3) * pw + (xp >> 3))), xp & 7, yp & 7, &pB); iB.rep = lk_scr_prep; iB.ox = lk_scr_pox; iB.oy = lk_scr_poy; iB.hf = lk_scr_phf; iB.vf = lk_scr_pvf; iB.pal = lk_scr_curpal; }
    if (vwin || (hright ? xc >= hpos : xc < hpos)) { cA = lk_scr_cell(LK_VW(wbase + 2 * ((line >> 3) * 64 + xc)), x & 7, line & 7, &pA); iA.rep = lk_scr_prep; iA.ox = lk_scr_pox; iA.oy = lk_scr_poy; iA.hf = lk_scr_phf; iA.vf = lk_scr_pvf; iA.pal = lk_scr_curpal; }
    else { int xp = (x - hsA) & (pw * 8 - 1), yp = (line + (((vsram[(vm ? 4 * (x >> 4) : 0) ^ 1] << 8) | vsram[((vm ? 4 * (x >> 4) : 0) + 1) ^ 1]) & 0x3FF)) & (ph * 8 - 1);
      cA = lk_scr_cell(LK_VW(baseA + 2 * ((yp >> 3) * pw + (xp >> 3))), xp & 7, yp & 7, &pA); iA.rep = lk_scr_prep; iA.ox = lk_scr_pox; iA.oy = lk_scr_poy; iA.hf = lk_scr_phf; iA.vf = lk_scr_pvf; iA.pal = lk_scr_curpal; }
    if (sp[x] >= 0 && spp[x]) { sel = sp[x]; wi = &spi[x]; } else if (cA >= 0 && pA) { sel = cA; wi = &iA; } else if (cB >= 0 && pB) { sel = cB; wi = &iB; }
    else if (sp[x] >= 0) { sel = sp[x]; wi = &spi[x]; } else if (cA >= 0) { sel = cA; wi = &iA; } else if (cB >= 0) { sel = cB; wi = &iB; }
    { static long dbgf = -2; if (dbgf == -2) { const char *q = getenv("LANDSTALKER_OWN_SCRDBG"); dbgf = q ? atol(q) : -1; }
      if (dbgf >= 0 && platform_frame_number() == dbgf && line == 23 && (x == 16 || x == 100)) printf("ownscrdbg: frame %ld line %d x %d: A %d/%d B %d/%d spr %d/%d sel %d hsA %d hsB %d reg18 %02X reg17 %02X reg11 %02X reg1 %02X vwin %d\n", dbgf, line, x, cA, pA, cB, pB, sp[x], spp[x], sel, hsA, hsB, reg[18], reg[17], reg[11], reg[1], vwin); }
    if (sel >= 0x1000000) col32 = 0xFF000000u | (uint32_t)(sel & 0xFFFFFF);   /* replaced pixel (32 bit output) */
    else { cc = sel >= 0 ? lk_scr_cramw(sel) : bgcol; if (x < 8 && (reg[0] & 0x20)) { cc = bgcol; wi = 0; } col32 = pixel_lut[1][cc]; }
    out[x] = (PIXEL_OUT_T)col32;
    if (lk_hd_n) { lk_hd_put(line, x, col32, wi); lk_hd_ref[line * LK_HDW + x + LK_HDO] = col32; }
  }
  if (lk_hd_n) lk_hd_stamp[line] = lk_hd_gen;
  return 1;
}
static void lk_scr_row(PIXEL_OUT_T *row, int e, int line, int map) {
  PIXEL_OUT_T buf[320]; int x, d = 0;
  if (lk_scr_mode < 0) { const char *q = getenv("LANDSTALKER_OWN_SCREENS"), *l = getenv("LANDSTALKER_OWN_SCRLOG"); lk_scr_mode = q ? atoi(q) : 2; lk_rep_init(); lk_scr_log = l ? atoi(l) : 0; { const char *o = getenv("LANDSTALKER_OWN_ORGLOG"); lk_org_log = o ? atoi(o) : 0; lk_dump_dir = getenv("LANDSTALKER_TILEDUMP"); lk_dump_on = lk_dump_dir && *lk_dump_dir; if (lk_dump_on) { struct stat st; extern int mkdir(const char *, unsigned int); if (stat(lk_dump_dir, &st) != 0) mkdir(lk_dump_dir, 0777); } } }
  if (!lk_scr_mode || !lk_scr_line(line, buf, e, lk_tall_keep(line))) return;
  for (x = 0; x < 320; x++) if (row[e + x] != buf[x]) d++;
  lk_scr_diff += d; lk_scr_tot += 320; lk_scr_lines++;
  if (lk_scr_mode == 2 && lk_o_mode == 2) for (x = 0; x < 320; x++) row[e + x] = buf[x];
  if ((lk_org_log > 0 || lk_dump_on) && line == 223) { int t, kn = 0, un = 0, dk = 0, du = 0; for (t = 0; t < 2048; t++) if (lk_scr_tc[t]) { if (lk_dump_on) lk_tile_dump(t, lk_scr_tpal[t]); if (lk_org_lookup(vram, t, 0, 0)) { kn += lk_scr_tc[t]; dk++; } else { un += lk_scr_tc[t]; du++; if (lk_org_log > 0 && getenv("LANDSTALKER_OWN_ORGLIST") && platform_frame_number() % lk_org_log == 0) printf("ownorg: frame %ld unknown tile %d (VRAM $%04X, %d pixels)\n", platform_frame_number(), t, t * 32, lk_scr_tc[t]); } lk_scr_tc[t] = 0; }
    if (lk_org_log > 0 && platform_frame_number() % lk_org_log == 0) printf("ownorg: frame %ld %s: opaque tile pixels with a known ROM origin %d, unknown %d (tiles %d / %d, origin table %d entries)\n", platform_frame_number(), map ? "map-not-own" : "screen", kn, un, dk, du, lk_org_count()); }
  if (lk_scr_log && line == 223) { printf("ownscr: frame %ld %s: %ld of %ld pixels differ in %ld lines\n", platform_frame_number(), map ? "map-not-own" : "screen", lk_scr_diff, lk_scr_tot, lk_scr_lines); lk_scr_diff = 0; lk_scr_tot = 0; lk_scr_lines = 0; }
}
/* ---- S3.5: seamless door transitions (optional: Options / ~/.landstalker_seam = 1 or LANDSTALKER_SEAM=1; docs/STAGE3_INVENTORY.md).  Presentation only, the game's logic runs as always.
   A level door (floor types 01 / 02 / 03 / 04 / 06 on both sides, same floor height, no stairs / closed flag; connection table `$11CEA2`) is crossed like this:
   the moment the game starts its fade out the last bright picture is FROZEN (gap, the emulation runs fast without drawing: the fade out and the room load take ~60 frames), when the new room is
   loaded it is drawn without its fade in while the camera glides from the old room's view to the new one (pan) and the old room's scenery, saved as layer images, stays visible beside it
   (the two rooms share one world: new cell = old cell - (door cell - arrival cell)), then the old room dissolves.  Stairs, ladders, locked doors, warp pads and everything else keep the game's fade. ---- */
#include <time.h>
extern int lk_rm_cell(int room, int x, int y);   /* tools/patch_roommodel.py: height map word of a room's cell from the ROM decoder, -1 = none */
static int lk_sm_opt = -1;
int lk_seam_get(void) {
  if (lk_sm_opt < 0) { const char *h = getenv("HOME"), *e = getenv("LANDSTALKER_SEAM"); char p[512]; FILE *f; int a; lk_sm_opt = 0; snprintf(p, sizeof p, "%s/.landstalker_seam", h ? h : "."); f = fopen(p, "r"); if (f) { if (fscanf(f, "%d", &a) == 1) lk_sm_opt = a ? 1 : 0; fclose(f); } if (e && *e) lk_sm_opt = atoi(e) ? 1 : 0; }
  return lk_sm_opt;
}
void lk_seam_set(int v) { const char *h = getenv("HOME"); char p[512]; FILE *f; lk_sm_opt = v ? 1 : 0; snprintf(p, sizeof p, "%s/.landstalker_seam", h ? h : "."); f = fopen(p, "w"); if (f) { fprintf(f, "%d\n", lk_sm_opt); fclose(f); } }

int lk_seam_gap(void) { return lk_sm_state == 1 || lk_sm_fastload; }   /* run the emulation fast without drawing (platform_sdl.c, patch_ffwd.py) */
static PIXEL_OUT_T lk_sm_rows[224][LK_OSW]; static int lk_sm_roww, lk_sm_rows_ok, lk_sm_capture_now;   /* the last bright picture (final rows, after shadows and the quick item bar) */
static uint32 lk_sm_pa[152][304], lk_sm_pb[152][304]; static uint8 lk_sm_tiles[0x12000]; static PIXEL_OUT_T lk_sm_pix[64], lk_sm_pixsave[64];   /* the old room's layer images, tiles and colours */
static int lk_sm_ocam0, lk_sm_ocam2, lk_sm_ou0, lk_sm_ov0, lk_sm_osave_ok, lk_sm_osave0, lk_sm_osave2, lk_sm_osaveu, lk_sm_osavev;   /* camera and image position of the old room's last bright frame */
static int lk_sm_target, lk_sm_dx, lk_sm_dy, lk_sm_oroom, lk_sm_newroom, lk_sm_prevL, lk_sm_sxn, lk_sm_syn, lk_sm_sxo, lk_sm_syo, lk_sm_alpha = 256, lk_sm_log = -1;
static long lk_sm_t0, lk_sm_pan0, lk_sm_dis0; static struct timespec lk_sm_wall; static int lk_sm_dz, lk_sm_ou, lk_sm_ov;   /* dz: floor height difference of the two doorways in world units (each room has its own zero level); fastload: the black room load of a normal fade is run fast */
#define LK_SM_MAXDZ 64   /* floor height difference of the two doorways (world units) up to which two rooms are one world: a cave / dungeon entrance is far off the neighbour's floor level and keeps the fade */
#define LK_SM_MAXOVERLAP 8   /* cells of the two rooms' maps that may lie on top of each other in the shared world (the door cells themselves coincide) */
#define LK_SM_PAN 24   /* frames of the camera glide */
#define LK_SM_DISSOLVE 45   /* frames the old room needs to dissolve after the glide */
static int lk_sm_door(int t) { return t == 1 || t == 2 || t == 3 || t == 4 || t == 6; }
static int lk_sm_same(int room, int target) { uint32_t a; if (room == target) return 1; for (a = 0xA3D8; a < 0xA61C && OW(a) != 0xFFFF; a += 6) if (OW(a) == target && OW(a + 2) == room) return 1; return 0; }
static int lk_sm_find(int room, int cx, int cy, int *target, int *ax, int *ay, int *flags, int *bx, int *by) {   /* the connection record whose cell in `room` (or the room it is a variant of) is (cx, cy) or one step away (the game warps when Nigel's tile is next to the doorway cell); bx / by = that record cell */
  uint32_t a; int orig = room, best = 9;
  for (a = 0xA3D8; a < 0xA61C && OW(a) != 0xFFFF; a += 6) if (OW(a + 2) == room) { orig = OW(a); break; }
  for (a = 0x11CEA2; a < 0x11EA64 && OW(a) != 0xFFFF; a += 8) {
    int w1 = OW(a), w2 = OW(a + 4), r1 = w1 & 0x3FF, r2 = w2 & 0x3FF, f = ((w1 >> 10) & 63) | ((w2 >> 10) & 63), d;
    if (r1 == room || r1 == orig) { int x = OB(a + 2), y = OB(a + 3); d = abs(x - cx) > abs(y - cy) ? abs(x - cx) : abs(y - cy); if (d <= 1 && d < best) { best = d; *target = r2; *ax = OB(a + 6); *ay = OB(a + 7); *flags = f; *bx = x; *by = y; } }
    if (r2 == room || r2 == orig) { int x = OB(a + 6), y = OB(a + 7); d = abs(x - cx) > abs(y - cy) ? abs(x - cx) : abs(y - cy); if (d <= 1 && d < best) { best = d; *target = r1; *ax = OB(a + 2); *ay = OB(a + 3); *flags = f; *bx = x; *by = y; } }
  }
  return best <= 1;
}
static int lk_sm_fetch(uint32 (*pl)[304], int U, int V, int *pal, int *prio) {   /* lk_o_fetch on the saved old room (its own tile images) */
  int tc = U >> 3, tr = V >> 3, ix = U & 7, iy = V & 7; uint32 c; int w, t, b;
  if (U < 0 || V < 0 || tc >= 304 || tr >= 152) return 0;
  c = pl[tr][tc]; if (!(c & 0x10000)) return 0;
  w = (int)(c & 0xFFFF); if (w & 0x800) ix = 7 - ix; if (w & 0x1000) iy = 7 - iy;
  t = w & 0x7FF; if (t * 32 + 31 >= (int)sizeof lk_sm_tiles) return 0;
  b = lk_sm_tiles[t * 32 + iy * 4 + ix / 2]; *pal = (w >> 13) & 3; *prio = (w >> 15) & 1;
  return (ix % 2 == 0) ? (b >> 4) : (b & 15);
}
/* ---- S3 step 2: NEIGHBOUR ROOMS from the ROM (docs/STAGE3_INVENTORY.md): graphics of any room without the game loading it: tile graphics (`DecompressLZ77Gfx`), block definitions (C port of `DecompBigTiles $00D09C`, tools/romgfx.py `bigtiles`), room map (tools/patch_roommodel.py), room palette; layer images in the same format as lk_o_pa / lk_o_pb ---- */
extern int lk_rm_layer(int room, int layer, int x, int y);
typedef struct { int room, ok, age; uint8 tiles[0x12000]; uint32 pa[152][304], pb[152][304]; PIXEL_OUT_T pix0[16]; int md0[16]; } lk_nb_t;
#define LK_NB_SLOTS 8
static lk_nb_t *lk_nb_slot[LK_NB_SLOTS]; static int lk_nb_clock;
static uint32_t lk_nb_pos; static int lk_nb_cur, lk_nb_n;
static int lk_nb_bit(void) { int b; if (lk_nb_n == 0) { lk_nb_cur = OB(lk_nb_pos++); lk_nb_n = 8; } b = (lk_nb_cur >> 7) & 1; lk_nb_cur = (lk_nb_cur << 1) & 0xFF; lk_nb_n--; return b; }
static int lk_nb_bits(int k) { int v = 0; while (k-- > 0) v = (v << 1) | lk_nb_bit(); return v; }
static int lk_nb_run(void) { int k = 0; while (!lk_nb_bit()) { k++; if (k > 24) return 0; } return k == 0 ? 0 : (1 << k) - 1 + lk_nb_bits(k); }
static int lk_nb_big(uint32_t a0, uint16_t (*blocks)[4], int cap) {   /* DecompBigTiles: returns the number of blocks (-1 = error); blocks[i][k] = the 4 tile words */
  static uint16_t words[4 * 1100]; int count, count4, d7 = 0, d3 = 0, pos = 0, r, n, i, flag, state, skip = 0, head = 0, C[16] = { 0 }; long guard = 0;
  lk_nb_pos = a0; lk_nb_cur = 0; lk_nb_n = 0;
  count = lk_nb_bits(16); if (count > cap || count > 1100) return -1; count4 = count * 4; memset(words, 0, sizeof words);
  r = lk_nb_run(); if (r == 0) { d7 ^= 0x8000; r = lk_nb_run(); n = r + 1; } else n = r;
  for (;;) { for (i = 0; i < n; i++) { if (pos < count4) words[pos] = (uint16_t)d7; pos++; } d3 += n; d7 ^= 0x8000; if (d3 >= count4) break; r = lk_nb_run(); n = r + 1; if (++guard > 100000) return -1; }
  for (flag = 0x1000; flag >= 0x0800; flag >>= 1) {
    pos = 0; d3 = 0; r = lk_nb_run();
    if (r != 0) { skip = r; state = 0; n = 0; } else { r = lk_nb_run(); state = 1; n = r + 1; }
    for (;;) {
      if (++guard > 400000) return -1;
      if (state == 1) { for (i = 0; i < n; i++) { if (pos < count4) words[pos] |= (uint16_t)flag; pos++; } d3 += n; if (d3 >= count4) break; r = lk_nb_run(); skip = r + 1; state = 0; }
      else { pos += skip; d3 += skip; if (d3 >= count4) break; r = lk_nb_run(); n = r + 1; state = 1; }
    }
  }
  for (i = 0; i < count4 / 2; i++) {
    int t, t2, k;
    if (!lk_nb_bit()) { head = (head - 1) & 15; C[head] = lk_nb_bits(11); t = C[head]; }
    else { k = lk_nb_bits(4); if (k == 0) t = C[head]; else { int sel = (head + k) & 15, v = C[sel], j; for (j = k; j > 0; j--) C[(head + j) & 15] = C[(head + j - 1) & 15]; C[head] = v; t = v; } }
    words[2 * i] |= (uint16_t)t;
    if (lk_nb_bit()) { t2 = t & 0x7FF; t2 = (words[2 * i] & 0x0800) ? t2 - 1 : t2 + 1; }
    else { if (!lk_nb_bit()) { head = (head - 1) & 15; C[head] = lk_nb_bits(11); t2 = C[head]; } else { k = lk_nb_bits(4); if (k == 0) t2 = C[head]; else { int sel = (head + k) & 15, v = C[sel], j; for (j = k; j > 0; j--) C[(head + j) & 15] = C[(head + j - 1) & 15]; C[head] = v; t2 = v; } } }
    words[2 * i + 1] |= (uint16_t)t2;
  }
  for (i = 0; i < count; i++) { blocks[i][0] = words[4 * i]; blocks[i][1] = words[4 * i + 1]; blocks[i][2] = words[4 * i + 2]; blocks[i][3] = words[4 * i + 3]; }
  return count;
}
static lk_nb_t *lk_nb_build(int room) {   /* graphics of `room` straight from the ROM (cached, 8 rooms) */
  static uint16_t blocks[1100][4]; uint32_t tab = OL(0xA0A00), e = tab + 8u * (uint32_t)room, tptr, bl, lst, prim, secp; int tileset, pal, sec, n1, n2, x, y, k, i, slot = -1, oldest = 0;
  lk_nb_t *nb;
  for (i = 0; i < LK_NB_SLOTS; i++) if (lk_nb_slot[i] && lk_nb_slot[i]->room == room) { lk_nb_slot[i]->age = ++lk_nb_clock; return lk_nb_slot[i]->ok ? lk_nb_slot[i] : NULL; }
  for (i = 0; i < LK_NB_SLOTS; i++) { if (!lk_nb_slot[i]) { slot = i; break; } if (lk_nb_slot[i]->age < lk_nb_slot[oldest]->age) oldest = i; }
  if (slot < 0) slot = oldest;
  if (!lk_nb_slot[slot]) lk_nb_slot[slot] = (lk_nb_t *)malloc(sizeof(lk_nb_t));
  nb = lk_nb_slot[slot]; if (!nb) return NULL;
  memset(nb, 0, sizeof *nb); nb->room = room; nb->age = ++lk_nb_clock;
  if (room < 0 || room >= 1024 || lk_rm_layer(room, 0, 0, 0) < 0) return NULL;
  tileset = OB(e + 4) & 0x1F; pal = OB(e + 5); sec = OB(e + 7) >> 5;
  tptr = OL(OL(0x44010) + 4u * (uint32_t)tileset); lk_o_lz77(tptr, nb->tiles, 0x10000);
  bl = OL(0x1AF800); lst = OL(bl + 4u * (uint32_t)OB(e + 4)); prim = OL(lst); secp = OL(lst + 4 + 4u * (uint32_t)sec);
  n1 = lk_nb_big(prim, blocks, 1024); if (n1 < 0) return NULL;
  n2 = lk_nb_big(secp, blocks + n1, 1024 - n1); if (n2 < 0) return NULL;
  for (y = 0; y < 74; y++) for (x = 0; x < 74; x++) {
    int lay;
    for (lay = 0; lay < 2; lay++) {   /* lay 0 = FG (layer A, columns 146), 1 = BG (layer B, 148): as lk_o_build */
      int id = lk_rm_layer(room, lay, x, y) & 0x3FF, c0 = 2 * (x - y) + (lay ? 148 : 146), r0 = x + y;
      if (id <= 0 || id >= n1 + n2) continue;
      for (k = 0; k < 4; k++) { int cc = c0 + (k & 1), rr = r0 + (k >> 1); if (cc >= 0 && cc < 304 && rr >= 0 && rr < 152) (lay ? nb->pb : nb->pa)[rr][cc] = 0x10000u | (uint32_t)blocks[id][k]; }
    }
  }
  { uint32_t pb0 = 0x11C926u + 26u * (uint32_t)pal;   /* line 0: colour 0 / 15 = 0, colour 1 = $0CCC, 2..14 = the room palette */
    for (i = 0; i < 16; i++) { int c = i == 1 ? 0x0CCC : (i >= 2 && i <= 14) ? OW(pb0 + 2u * (uint32_t)(i - 2)) : 0; nb->md0[i] = c; nb->pix0[i] = pixel_lut[1][((c >> 9) & 7) << 6 | ((c >> 5) & 7) << 3 | ((c >> 1) & 7)]; } }
  nb->ok = 1; return nb;
}
static int lk_nb_fetch(const lk_nb_t *nb, uint32 (*pl)[304], int U, int V, int *pal, int *prio) {   /* plane pixel of a neighbour room at ITS image position, 0 = transparent */
  int tc = U >> 3, tr = V >> 3, ix = U & 7, iy = V & 7; uint32 c; int w, t, b;
  if (U < 0 || V < 0 || tc >= 304 || tr >= 152) return 0;
  c = pl[tr][tc]; if (!(c & 0x10000)) return 0;
  w = (int)(c & 0xFFFF); if (w & 0x800) ix = 7 - ix; if (w & 0x1000) iy = 7 - iy;
  t = w & 0x7FF; if (t * 32 + 31 >= (int)sizeof nb->tiles) return 0;
  b = nb->tiles[t * 32 + iy * 4 + ix / 2]; *pal = (w >> 13) & 3; *prio = (w >> 15) & 1;
  return (ix % 2 == 0) ? (b >> 4) : (b & 15);
}
static void lk_nb_check(int room) {   /* LANDSTALKER_NB_CHECK=1: the room built from the ROM equals what the own renderer builds from the game's RAM (same layer images, tile graphics) */
  lk_nb_t *nb = lk_nb_build(room); int x, y, da = 0, db = 0, dt = 0, i;
  if (!nb) { printf("nb: room %d: ROM build FAILED\n", room); return; }
  for (y = 0; y < 152; y++) for (x = 0; x < 304; x++) { if (nb->pa[y][x] != lk_o_pa[y][x]) da++; if (nb->pb[y][x] != lk_o_pb[y][x]) db++; }
  for (i = 0; i < 0x10000; i++) if (nb->tiles[i] != lk_o_tbase[i]) dt++;
  printf("nb: room %d ROM build vs the game's RAM: layer A cells differ %d, layer B %d, tile bytes %d\n", room, da, db, dt);
}

typedef struct { int room, ou, ov, dz; lk_nb_t *nb; } lk_nbl_t;   /* ou / ov: pixel offset of the room's image in the current room's image space (16 (dx - dy), 8 (dx + dy) for a door aligned cell offset, plus the fine alignment) */
static lk_nbl_t lk_nbl[6]; static int lk_nb_pending, lk_nbn, lk_nb_room = -1, lk_nb_chk = -1, lk_nb_chk_room = -1; static long lk_nb_roomf;
static void lk_nb_collect(int rm) {   /* the rooms that stay loaded beside room `rm`: connections that are door -> door, no stairs / closed flag, and whose maps do not lie on top of each other in the shared world (same rule as the seamless transition) */
  uint32_t a; int orig = rm, i;
  lk_nbn = 0;
  for (a = 0xA3D8; a < 0xA61C && OW(a) != 0xFFFF; a += 6) if (OW(a + 2) == rm) { orig = OW(a); break; }
  for (a = 0x11CEA2; a < 0x11EA64 && OW(a) != 0xFFFF && lk_nbn < 6; a += 8) {
    int w1 = OW(a), w2 = OW(a + 4), r1 = w1 & 0x3FF, r2 = w2 & 0x3FF, f = ((w1 >> 10) & 63) | ((w2 >> 10) & 63), tx, bx, by, ax, ay, k, dup = 0;
    if (r1 == rm || r1 == orig) { tx = r2; bx = OB(a + 2); by = OB(a + 3); ax = OB(a + 6); ay = OB(a + 7); }
    else if (r2 == rm || r2 == orig) { tx = r1; bx = OB(a + 6); by = OB(a + 7); ax = OB(a + 2); ay = OB(a + 3); }
    else continue;
    if ((f & 0x31) || tx == rm || bx >= 74 || by >= 74) continue;
    for (k = 0; k < lk_nbn; k++) if (lk_nbl[k].room == tx) dup = 1;
    if (dup) continue;
    { int cw = UW(0xFFD192 + 148 * by + 2 * bx), tw = lk_rm_cell(tx, ax, ay), ov = 0, cx, cy;
      if (tw < 0 || !lk_sm_door(cw & 0xFF) || !lk_sm_door(tw & 0xFF)) continue;
      for (cy = 0; cy < 74; cy++) for (cx = 0; cx < 74; cx++) { int va = UW(0xFFD192 + 148 * cy + 2 * cx), wb; if (va == 0 || va == 0x4000) continue; wb = lk_rm_cell(tx, cx - (bx - ax), cy - (by - ay)); if (wb > 0 && wb != 0x4000) ov++; }
      if (ov > LK_SM_MAXOVERLAP || abs(16 * (((cw >> 8) & 15) - ((tw >> 8) & 15))) > LK_SM_MAXDZ) continue;
      lk_nbl[lk_nbn].nb = lk_nb_build(tx);
      if (!lk_nbl[lk_nbn].nb) continue;
      { /* ALIGNMENT (user: "the rooms may overlap so that no black band remains, the exits (what sticks out into the black margin) must overlap 1:1, they only needed to be closer together"): the exits are the path / ground pieces that both rooms draw at the doorway; with the door cells on top of each other they coincide, the grass fields are still apart (a black band).  The neighbour is moved ALONG ONE AXIS (x or y: the exit piece stays collinear with itself), first in whole cells (up to 4), then in 1/8 cell steps (2 x 1 pixels) around the best cell, until the two pictures cover the screen window around the door best (union - 0.5 * overlap - small distance penalty; cells = 8 x 8 tile cells, pixels = colour index != 0 of the layer images); only once the current room's images are built; not kept at all when the two pictures disagree so much where they overlap that this room cannot be a continuation (a cave, a shrine ...) */
        const lk_nb_t *nbq2 = lk_nbl[lk_nbn].nb; int dx0 = bx - ax, dy0 = by - ay, sx, sy, c0 = 2 * (bx - by) + 148, r0 = bx + by, k, ax_, bestax = 0, bestk = 0, ovt0 = 0, m0 = 0, mis0 = 0, ou = 0, ov = 0; float bests = -1e9f, base = 0;
        for (ax_ = 0; ax_ < 2; ax_++) for (k = -4; k <= 4; k++) {
          int ddx, ddy, oc, orr, c, r, u = 0, ovl = 0; float sc;
          if (ax_ == 1 && k == 0) continue;
          sx = ax_ ? k : 0; sy = ax_ ? 0 : k;
          ddx = dx0 + sx; ddy = dy0 + sy; oc = 2 * (ddx - ddy); orr = ddx + ddy;
          for (r = r0 - 9; r < r0 + 19; r++) for (c = c0 - 24; c < c0 + 25; c++) {
            int a2 = 0, b2 = 0, nc = c - oc, nr = r - orr;
            if (c >= 0 && c < 304 && r >= 0 && r < 152) a2 = ((lk_o_pa[r][c] | lk_o_pb[r][c]) & 0x10000) != 0;
            if (nc >= 0 && nc < 304 && nr >= 0 && nr < 152) b2 = ((nbq2->pa[nr][nc] | nbq2->pb[nr][nc]) & 0x10000) != 0;
            if (a2 || b2) u++;
            if (a2 && b2) ovl++;
            if (sx == 0 && sy == 0 && a2 && b2) {   /* the exact door alignment: how much do the pictures agree where they overlap? (palette line + colour index of 8 sample pixels per tile) */
              int q;
              ovt0++;
              for (q = 0; q < 8; q++) {
                int U = c * 8 + ((q * 3) & 7), V = r * 8 + q, apal = 0, ap = 0, bpal = 0, bp = 0, pn = 0, pa = 0, pn2 = 0, pb2 = 0, ia = lk_o_fetch(lk_o_pa, U, V, &apal, &ap, 0), ib = lk_o_fetch(lk_o_pb, U, V, &bpal, &bp, 0),
                    na1 = lk_nb_fetch(nbq2, nbq2->pa, U - 8 * oc, V - 8 * orr, &pn, &pa), ib1 = lk_nb_fetch(nbq2, nbq2->pb, U - 8 * oc, V - 8 * orr, &pn2, &pb2), x1, x2;
                x1 = ia && ap ? apal * 16 + ia : ib && bp ? bpal * 16 + ib : ia ? apal * 16 + ia : ib ? bpal * 16 + ib : 0;
                x2 = na1 && pa ? pn * 16 + na1 : ib1 && pb2 ? pn2 * 16 + ib1 : na1 ? pn * 16 + na1 : ib1 ? pn2 * 16 + ib1 : 0;
                if (x1 && x2) { if (x1 == x2) m0++; else mis0++; }
              }
            }
          }
          sc = (float)u - 0.5f * (float)ovl - 1.5f * (float)abs(k);
          if (k == 0 && ax_ == 0) base = sc;
          if (sc > bests) { bests = sc; bestax = ax_; bestk = k; }
        }
        if (bests - base < 12.0f) { bestk = 0; }
        ou = 16 * (dx0 - dy0); ov = 8 * (dx0 + dy0);
        if (bestk) { if (bestax) { ou += 16 * bestk; ov += 8 * bestk; } else { ou -= 16 * bestk; ov += 8 * bestk; } }
        if (bestk) {   /* fine alignment in 1/8 cell steps (the black seam between two rooms is rarely a whole number of cells thick): pixel level coverage of the window, +-8 steps around the best cell shift */
          int i2, besti = 0; long bestp = -1000000000L;
          for (i2 = -8; i2 <= 8; i2++) {
            int ou2 = ou + (bestax ? 2 * i2 : -2 * i2), ov2 = ov + i2, X, Y; long sc2, cov = 0, ovp = 0;
            for (Y = r0 * 8 - 72; Y < r0 * 8 + 152; Y += 2) for (X = c0 * 8 - 192; X < c0 * 8 + 200; X += 2) {
              int pp = 0, qq = 0, pr = 0, pb3 = 0, pr2 = 0, pb4 = 0, a3, b3;
              a3 = lk_o_fetch(lk_o_pa, X, Y, &pp, &pr, 0) || lk_o_fetch(lk_o_pb, X, Y, &qq, &pb3, 0);
              b3 = lk_nb_fetch(nbq2, nbq2->pa, X - ou2, Y - ov2, &pp, &pr2) || lk_nb_fetch(nbq2, nbq2->pb, X - ou2, Y - ov2, &qq, &pb4);
              if (a3 || b3) cov++;
              if (a3 && b3) ovp++;
            }
            sc2 = cov * 4 - ovp - (long)abs(i2);
            if (sc2 > bestp) { bestp = sc2; besti = i2; }
          }
          ou += bestax ? 2 * besti : -2 * besti; ov += besti;
        }
        if (lk_sm_log) printf("nb: room %d beside room %d: exact overlap %d tiles, %d equal / %d different sample pixels; axis %c shift %d cells (score %.0f, exact %.0f), pixel offset %d,%d (door aligned %d,%d)\n", tx, rm, ovt0, m0, mis0, bestax ? 'x' : 'y', bestk, bests, base, ou, ov, 16 * (dx0 - dy0), 8 * (dx0 + dy0));
        if (ovt0 >= 40 && mis0 * 10 > (m0 + mis0) * 6) { if (lk_sm_log) printf("nb: room %d is NOT a clean continuation of room %d (the overlapping pictures disagree): not kept\n", tx, rm); continue; }
        lk_nbl[lk_nbn].room = tx; lk_nbl[lk_nbn].ou = ou; lk_nbl[lk_nbn].ov = ov;
      }
      lk_nbl[lk_nbn].dz = 16 * (((cw >> 8) & 15) - ((tw >> 8) & 15)); lk_nbn++;
    }
  }
  for (i = 0; i < lk_nbn; i++) if (lk_sm_log) printf("nb: room %d keeps room %d loaded beside it (pixel offset %d,%d dz %d)\n", rm, lk_nbl[i].room, lk_nbl[i].ou, lk_nbl[i].ov, lk_nbl[i].dz);
}
static PIXEL_OUT_T lk_vh[8][LK_OSW]; static uint8 lk_vhv[8][LK_OSW];   /* the last composed rows and whether a pixel was void: a seam between two rooms that is only a few pixels thick is filled from the row above */
static int lk_nb_lookup(int ubase, int vbase, int x, int pick_out[1], const lk_nb_t **nbq_out) {   /* the first neighbour room that has a picture at this pixel: pick = palette line * 16 + colour index, 0 = none */
  int nk;
  for (nk = 0; nk < lk_nbn; nk++) {
    const lk_nbl_t *q = &lk_nbl[nk]; int U = ubase + x - lk_sm_sxn - q->ou, V = vbase - lk_sm_syn - q->ov + q->dz, nA = 0, nB = 0, pA = 0, pB = 0,
        na = lk_nb_fetch(q->nb, q->nb->pa, U, V, &nA, &pA), nbb = lk_nb_fetch(q->nb, q->nb->pb, U, V, &nB, &pB), pk = 0;
    if (na && pA) pk = nA * 16 + na; else if (nbb && pB) pk = nB * 16 + nbb; else if (na) pk = nA * 16 + na; else if (nbb) pk = nB * 16 + nbb;
    if (pk) { pick_out[0] = pk; *nbq_out = q->nb; return 1; }
  }
  return 0;
}
static void lk_sm_shifts(int camn0, int camn2, float s) {   /* screen shift of the new room's picture and of the old room's picture while the camera is at old + s * (new - old) in the shared world */
  float vx = (float)camn0 + (float)lk_sm_ov + (float)lk_sm_ou / 2.0f - (float)lk_sm_dz - (float)lk_sm_ocam0, vy = (float)camn2 + (float)lk_sm_ov - (float)lk_sm_ou / 2.0f - (float)lk_sm_dz - (float)lk_sm_ocam2, an = (1.0f - s) * vx, bn = (1.0f - s) * vy, ao = -s * vx, bo = -s * vy;
  lk_sm_sxn = (int)lroundf(an - bn); lk_sm_syn = (int)lroundf((an + bn) / 2.0f); lk_sm_sxo = (int)lroundf(ao - bo); lk_sm_syo = (int)lroundf((ao + bo) / 2.0f);
}
static void lk_seam_step(int rm, int drawn, int cam0, int cam2, int u0, int v0) {   /* once per frame, after the picture decision of line 0 */
  #define MR16(a) ((((int)lk_o_r[((a) & 0xFFFF) ^ 1]) << 8) | (int)lk_o_r[(((a) + 1) & 0xFFFF) ^ 1])
  int L = (int)(int16_t)(MR16(0xFF0F50) - MR16(0xFF0F52)); long fn = platform_frame_number();
  if (lk_sm_log < 0) { const char *q = getenv("LANDSTALKER_SEAM_LOG"); lk_sm_log = q ? atoi(q) : 0; }
  lk_sm_capture_now = 0; lk_sm_fastload = 0;
  if (lk_nb_chk < 0) { const char *q = getenv("LANDSTALKER_NB_CHECK"); lk_nb_chk = q ? atoi(q) : 0; }
  if (lk_seam_get() && lk_o_mode == 2 && rm == lk_o_room && rm > 0 && lk_o_disp0) {   /* neighbour rooms of the room that is on screen */
    if (rm != lk_nb_room) { lk_nb_room = rm; lk_nb_roomf = fn; lk_nbn = 0; lk_nb_pending = 1; }
    if (lk_nb_pending && fn - lk_nb_roomf >= 2 && (lk_sm_state == 0 || lk_sm_state >= 2)) {   /* two frames after the room appeared: the snapshot holds its height map; and its layer images must be built (the alignment compares them) */
      int y2, cells = 0; for (y2 = 0; y2 < 152; y2 += 4) { int x2; for (x2 = 0; x2 < 304; x2 += 4) cells += (lk_o_pa[y2][x2] | lk_o_pb[y2][x2]) >> 16 & 1; }
      if (cells > 200 || fn - lk_nb_roomf > 30) { lk_nb_pending = 0; lk_nb_collect(rm); }
    }
    if (lk_nb_chk && rm != lk_nb_chk_room && fn - lk_nb_roomf >= 60) { lk_nb_chk_room = rm; lk_nb_check(rm); }
  } else if (!(lk_seam_get() && lk_o_mode == 2)) { lk_nbn = 0; lk_nb_room = -1; }
  { int k, i; for (k = 0; k < lk_nbn; k++) for (i = 0; i < 16; i++) { int c = lk_o_darken(lk_nbl[k].nb->md0[i], lk_sm_nofade ? 0 : lk_o_lvl0); lk_nbl[k].nb->pix0[i] = pixel_lut[1][((c >> 9) & 7) << 6 | ((c >> 5) & 7) << 3 | ((c >> 1) & 7)]; } }
  if (!lk_seam_get() || lk_o_mode != 2 || !lk_o_fx) { lk_sm_state = 0; lk_sm_nofade = 0; lk_sm_prevL = L; return; }
  if (lk_sm_state == 0 && !lk_o_disp0 && L >= 0xE00 && rm != lk_o_room && lk_o_room >= 0 && rm > 0 && rm < 800) { static long fl0; static int was; lk_sm_fastload = 1; if (lk_sm_log && !was) fl0 = fn; was = 1; (void)fl0; }   /* a normal fade: the black room load is run fast (no stutter) */
  { static int was2; static long t2; if (!lk_sm_fastload && was2 && lk_sm_log) printf("seam: frame %ld fast room load ended (%ld frames)\n", fn, fn - t2); if (lk_sm_fastload && !was2) { t2 = fn; if (lk_sm_log) printf("seam: frame %ld fast room load starts\n", fn); } was2 = lk_sm_fastload; }
  if (lk_sm_state == 0) {
    lk_sm_nofade = 0;
    if (L == 0 && drawn && lk_o_disp0 && lk_o_valid && !lk_sh_hide) {   /* a bright map frame: remember it */
      lk_sm_capture_now = 1; lk_sm_osave0 = cam0; lk_sm_osave2 = cam2; lk_sm_osaveu = u0; lk_sm_osavev = v0; lk_sm_osave_ok = 1; memcpy(lk_sm_pixsave, lk_o_pix, sizeof lk_sm_pixsave);
    }
    if (L > 0 && lk_sm_prevL == 0 && rm == lk_o_room && rm > 0 && !lk_sh_hide && lk_sm_rows_ok && lk_sm_osave_ok) {   /* the game starts a fade out */
      int px = UB(0xFF5400), py = UB(0xFF5401), tx = 0, ax = 0, ay = 0, fl = 0, bx = 0, by = 0, cw = 0;
      if (px < 74 && py < 74 && lk_sm_find(rm, px, py, &tx, &ax, &ay, &fl, &bx, &by) && bx < 74 && by < 74 && (cw = UW(0xFFD192 + 148 * by + 2 * bx), lk_sm_door(cw & 0xFF)) && !(fl & 0x31)) {
        int tw = lk_rm_cell(tx, ax, ay), ov = 0, cx, cy;
        if (tw >= 0) for (cy = 0; cy < 74; cy++) for (cx = 0; cx < 74; cx++) {   /* do the two maps lie on top of each other in the shared world (new cell = old cell - D)? interiors inside a building's footprint do, neighbouring outdoor rooms hardly */
          int va = UW(0xFFD192 + 148 * cy + 2 * cx), wb;
          if (va == 0 || va == 0x4000) continue;
          wb = lk_rm_cell(tx, cx - (bx - ax), cy - (by - ay));
          if (wb > 0 && wb != 0x4000) ov++;
        }
        int nk2 = -1, kk; for (kk = 0; kk < lk_nbn; kk++) if (lk_nbl[kk].room == tx) nk2 = kk;
        if (tw >= 0 && lk_sm_door(tw & 0xFF) && ov <= LK_SM_MAXOVERLAP && abs(16 * (((cw >> 8) & 15) - ((tw >> 8) & 15))) <= LK_SM_MAXDZ && nk2 >= 0) {
          lk_sm_state = 1; lk_sm_nofade = 1; lk_sm_t0 = fn; clock_gettime(CLOCK_MONOTONIC, &lk_sm_wall); lk_sm_target = tx; lk_sm_oroom = rm; lk_sm_ou = lk_nbl[nk2].ou; lk_sm_ov = lk_nbl[nk2].ov; lk_sm_dz = lk_nbl[nk2].dz;   /* the neighbour's aligned world offset */ lk_sm_ocam0 = lk_sm_osave0; lk_sm_ocam2 = lk_sm_osave2; lk_sm_ou0 = lk_sm_osaveu; lk_sm_ov0 = lk_sm_osavev;
          memcpy(lk_sm_pa, lk_o_pa, sizeof lk_sm_pa); memcpy(lk_sm_pb, lk_o_pb, sizeof lk_sm_pb); memcpy(lk_sm_tiles, lk_o_tiles, sizeof lk_sm_tiles); memcpy(lk_sm_pix, lk_sm_pixsave, sizeof lk_sm_pix);
          if (lk_sm_log) printf("seam: frame %ld GAP start room %d cell %d,%d -> room %d cell %d,%d (pixel offset %d,%d)\n", fn, rm, px, py, tx, ax, ay, lk_sm_ou, lk_sm_ov);
        } else if (lk_sm_log) printf("seam: frame %ld door %d,%d of room %d -> room %d keeps the fade (cells %04X / %04X, %d map cells would overlap)\n", fn, px, py, rm, tx, cw, tw, ov);
      }
    }
  } else if (lk_sm_state == 1) {
    if (rm == lk_sm_oroom && L == 0 && drawn && lk_o_disp0 && fn - lk_sm_t0 > 2) { lk_sm_state = 0; lk_sm_nofade = 0; if (lk_sm_log) printf("seam: frame %ld GAP aborted (the fade ended in the same room)\n", fn); }
    else if (fn - lk_sm_t0 > 400 || lk_sh_hide || lk_sm_roww == 0) { lk_sm_state = 0; if (lk_sm_log) printf("seam: frame %ld GAP aborted (timeout / menu)\n", fn); }
    else if (rm != lk_sm_oroom && !lk_sm_same(rm, lk_sm_target)) { lk_sm_state = 0; if (lk_sm_log) printf("seam: frame %ld GAP aborted (room %d is not the target %d)\n", fn, rm, lk_sm_target); }
    else if (rm != lk_sm_oroom && lk_o_room == rm && drawn && lk_o_disp0) {
      lk_sm_state = 2; lk_sm_pan0 = fn; lk_sm_newroom = rm; lk_sm_nofade = 1; lk_sm_alpha = 256;
      if (lk_sm_log) { struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts); printf("seam: frame %ld PAN start room %d (gap %ld frames, %.0f ms of computing)\n", fn, rm, fn - lk_sm_t0, (ts.tv_sec - lk_sm_wall.tv_sec) * 1000.0 + (ts.tv_nsec - lk_sm_wall.tv_nsec) / 1e6); }
    }
  }
  if (lk_sm_state >= 2) {
    float s; long t = fn - lk_sm_pan0;
    if (lk_sh_hide || rm != lk_sm_newroom || lk_o_room != rm || (lk_sm_state == 3 && L > 0)) { lk_sm_state = 0; lk_sm_nofade = 0; if (lk_sm_log) printf("seam: frame %ld transition ended early\n", fn); }
    else {
      s = t >= LK_SM_PAN ? 1.0f : (float)t / (float)LK_SM_PAN; s = s * s * (3.0f - 2.0f * s);
      lk_sm_shifts(cam0, cam2, s);
      if (lk_sm_state == 2) { lk_sm_nofade = 1; if (t >= LK_SM_PAN && L == 0) { lk_sm_state = 3; lk_sm_dis0 = fn; lk_sm_nofade = 0; } }
      if (lk_sm_state == 3) { long d = fn - lk_sm_dis0; lk_sm_alpha = 256 - (int)(256 * d / LK_SM_DISSOLVE); if (lk_sm_alpha <= 0) { lk_sm_state = 0; lk_sm_alpha = 256; if (lk_sm_log) printf("seam: frame %ld transition done\n", fn); } }
    }
  }
  if (lk_sm_state == 0) { lk_sm_sxn = lk_sm_syn = lk_sm_sxo = lk_sm_syo = 0; }
  lk_sm_prevL = L;
  #undef MR16
}
static void lk_seam_final(PIXEL_OUT_T *row, int w, int line) {   /* after shadows and the quick item bar: remember the bright picture / replay it during the gap */
  if (line < 0 || line >= 224 || w <= 0 || w > LK_OSW) return;
  if (lk_sm_state == 1) { if (lk_sm_roww == w) memcpy(row, lk_sm_rows[line], (size_t)w * sizeof(PIXEL_OUT_T)); return; }
  if (lk_sm_capture_now) { memcpy(lk_sm_rows[line], row, (size_t)w * sizeof(PIXEL_OUT_T)); if (line == 0) lk_sm_rows_ok = 0; lk_sm_roww = w; if (line == 223) lk_sm_rows_ok = 1; }
}
static void lk_own_row(PIXEL_OUT_T *row, int w, int line) {
  static int hint, fr_done = -1, hsA, hsB, vsA, vsB, cam0, cam2, rm; static long fr_n;
  int x, e, map;
  lk_o_init();
  if (!lk_o_mode) return;
  if (lk_sm_state) lk_sh_row_on = 0;   /* S3.5: the shadow marks of the VDP belong to the unshifted picture */
  if (line == 0) lk_hd_gen++;
  if (line == 0) {
    const uint8_t *r = bus_get_ram(); int hsb = (LK_REG(13) & 0x3F) << 10;
    if (lk_o_vbmode && lk_vb_n) r = lk_vb_ram;                       /* LANDSTALKER_OWN_VB=1: the state as the VDP received it (RAM right after the VBlank handler, patch_ownvb.py) */
    if (!r) return;
    lk_o_r = r;
    if (lk_o_valid) {                                                 /* state of the previous pass = the picture shown now */
      memcpy(lk_o_use, (lk_o_vbmode && lk_vb_n) ? r : lk_o_prev, sizeof lk_o_use);
      if (lk_o_scrram && lk_o_vmirror && !lk_o_scrvars) { hsA = (lk_vm[hsb] << 8) | lk_vm[hsb + 1]; hsB = (lk_vm[hsb + 2] << 8) | lk_vm[hsb + 3]; vsA = (lk_vsm[0] << 8) | lk_vsm[1]; vsB = (lk_vsm[2] << 8) | lk_vsm[3]; lk_o_sc_ram = 1; }   /* what the game's DMA queue sent to the VDP's scroll tables (own mirror, patch_ownvb.py) */
      else if (lk_o_scrram && !(lk_o_gshake && lk_gaia_shake())) { hsA = (r[0x0100 ^ 1] << 8) | r[0x0101 ^ 1]; hsB = (r[0x0102 ^ 1] << 8) | r[0x0103 ^ 1]; vsA = (r[0x0500 ^ 1] << 8) | r[0x0501 ^ 1]; vsB = (r[0x0502 ^ 1] << 8) | r[0x0503 ^ 1]; lk_o_sc_ram = 1; }   /* the game's own scroll variables (equal to the VDP's, except for the stale frames after the Gaia effect) */
      else { hsA = ((vram[hsb ^ 1] << 8) | vram[(hsb + 1) ^ 1]); hsB = ((vram[(hsb + 2) ^ 1] << 8) | vram[(hsb + 3) ^ 1]); vsA = (vsram[0 ^ 1] << 8) | vsram[1 ^ 1]; vsB = (vsram[2 ^ 1] << 8) | vsram[3 ^ 1]; lk_o_sc_ram = 0; }   /* old way (LANDSTALKER_OWN_SCROLL_VDP=1 / LANDSTALKER_OWN_GSHAKE=1) */
      /* the scroll values stay the VDP's registers: they equal the RAM variables $FF0100 / $FF0102 (hscroll A / B) and $FF0500 / $FF0502 (vscroll A / B) except while an effect writes them directly (the Gaia statue shakes VSRAM) */
      cam0 = US(0xFF1200); cam2 = US(0xFF1202); rm = UW(0xFF1204);
      if (lk_o_vblog) { static int ns_; int i9, bad = 0, sb = (LK_REG(5) & 0x7F) << 9; for (i9 = 0; i9 < 640; i9++) if (vram[(sb + i9) ^ 1] != r[((0xFF0550 + i9) & 0xFFFF) ^ 1]) bad++; if (bad && rm > 0 && rm < 800 && ns_++ < lk_o_vblog) printf("ownvb: frame %ld room %d sprite table VRAM vs RAM $FF0550: %d of 640 bytes differ\n", platform_frame_number(), rm, bad); }
      if (lk_o_vblog) { static int nl; int w1 = (int16_t)((r[(0xFF0100 & 0xFFFF) ^ 1] << 8) | r[(0xFF0101 & 0xFFFF) ^ 1]), w2 = (int16_t)((r[(0xFF0102 & 0xFFFF) ^ 1] << 8) | r[(0xFF0103 & 0xFFFF) ^ 1]), v1 = (int16_t)((r[(0xFF0500 & 0xFFFF) ^ 1] << 8) | r[(0xFF0501 & 0xFFFF) ^ 1]), v2 = (int16_t)((r[(0xFF0502 & 0xFFFF) ^ 1] << 8) | r[(0xFF0503 & 0xFFFF) ^ 1]);
        if ((int16_t)hsA != w1 || (int16_t)hsB != w2 || (int16_t)vsA != v1 || (int16_t)vsB != v2) { if (nl++ < lk_o_vblog) printf("ownvb: frame %ld VDP hsA %d hsB %d vsA %d vsB %d | RAM FF0100 %d FF0102 %d FF0500 %d FF0502 %d (snapshot of frame %ld)\n", platform_frame_number(), (int16_t)hsA, (int16_t)hsB, (int16_t)vsA, (int16_t)vsB, w1, w2, v1, v2, lk_vb_frame); } }
      { /* which pass' camera does the VDP show? the vertical scroll is (cam0 + cam2) / 2 - 600 of the pass whose camera the game had written when the picture was built (FORMATS 'Scroll registers lag'):
           take the current pass' camera when it reproduces the VDP's scroll, else the previous one (the VDP's own update timing varies from frame to frame while Nigel moves) */
        int c0 = (int16_t)((r[(0xFF1200 & 0xFFFF) ^ 1] << 8) | r[(0xFF1201 & 0xFFFF) ^ 1]), c2 = (int16_t)((r[(0xFF1202 & 0xFFFF) ^ 1] << 8) | r[(0xFF1203 & 0xFFFF) ^ 1]);
        if (((((c0 + c2) >> 1) - 600) & 0x3FF) == (vsA & 0x3FF) && lk_o_cammode) { cam0 = c0; cam2 = c2; }
      } { const uint8_t *lr = bus_get_ram(); hint = lr[(0xFF0FC5 & 0xFFFF) ^ 1]; }   /* the text box hint line is written by the game's main code right after WaitUntilVBlank (SetVDPForTextbox): the LIVE value, not the snapshot */
      { /* position of the picture in image coordinates. The camera of the previous pass predicts it to a few pixels (sometimes the VDP is one step further); the VDP's own scroll registers give it exactly
           modulo the plane size (U = sx - hs + C mod 512, V = line + vs + C' mod 256), with room dependent constants that are learned: every frame votes for (prediction + hs) and the winner is used */
        int upred = 1184 - (cam2 - cam0 + 160), vpred = ((cam0 + cam2) >> 1) - 104;
        lk_o_u0 = upred; lk_o_v0 = vpred;
        if (lk_o_cammode == 2) {
          int pending, ku = ((((upred + (int16_t)hsA) % 512 + 512) % 512) + 4) / 8 % 64, kv = ((((vpred - (int16_t)vsA) % 256 + 256) % 256) + 4) / 8 % 32, bu = 0, bv = 0, i3, du, dv;
          /* the constants are multiples of 8 (the plane's tile grid); the prediction error of +-2 px is rounded away.  Recent frames count more (decay 0.7): right after a room load the VDP's registers are
             stale for a few frames and vote for a wrong constant, the right one takes over after ~3 frames */
          pending = lk_o_fx && lk_o_room >= 0 && rm != lk_o_room && !lk_o_blanked;   /* the old room is still drawn: the camera variables already belong to the new one, the votes stay as they were */
          { static int pu, pv; int jump = !pending && (abs(upred - pu) > 48 || abs(vpred - pv) > 48); if (!pending) { pu = upred; pv = vpred; }   /* the game re-bases the camera of a looping room (Stairway to Nole, room 421, user recording 2026-10-19): the registers go on smoothly, the constants change at once */
            { int vr = lk_o_fx ? lk_o_room : rm; if (vr != lk_o_vote_room || jump) { memset(lk_o_vu, 0, sizeof lk_o_vu); memset(lk_o_vv, 0, sizeof lk_o_vv); lk_o_vote_room = vr; } } }   /* with the effects the OLD room goes on being drawn until the new one is loaded: the votes belong to the room that is drawn */
          if (((r[0x0FC7 ^ 1] & 3) == 0 || !lk_o_fx) && !pending) { for (i3 = 0; i3 < 64; i3++) lk_o_vu[i3] *= 0.7f; for (i3 = 0; i3 < 32; i3++) lk_o_vv[i3] *= 0.7f; }
          if (((r[0x0FC7 ^ 1] & 3) == 0 || !lk_o_fx) && !pending) { lk_o_vu[ku] += 1.0f; lk_o_vv[kv] += 1.0f; }   /* no votes while the game scrolls per line (tree warp swirl: the first table entry is not the camera any more) */
          if (!pending && (int16_t)hsA == 144 && (int16_t)vsA == -96 && (int16_t)hsB == 144 && (int16_t)vsB == -96 && lk_o_seed) {   /* the scroll registers show the values InitScrollRegs $00906C gives them at a room load: the plane constants are then known exactly from the camera block (x = $FF1124, y = $FF1125): bu = 8 * ((2 (x - y) + 18) mod 64), bv = 8 * ((x + y) mod 32) (checked against the votes of 44 loads in 6 recordings: all equal); the seed wins the vote at once instead of after ~3 frames */
            int x = r[0x1124 ^ 1], y = r[0x1125 ^ 1]; lk_o_vu[((2 * (x - y) + 18) % 64 + 64) % 64] += 8.0f; lk_o_vv[((x + y) % 32 + 32) % 32] += 8.0f; }
          for (i3 = 0; i3 < 64; i3++) if (lk_o_vu[i3] > lk_o_vu[bu]) bu = i3;
          for (i3 = 0; i3 < 32; i3++) if (lk_o_vv[i3] > lk_o_vv[bv]) bv = i3;
          bu *= 8; bv *= 8;
          du = (((bu - (int16_t)hsA - upred) % 512) + 512) % 512; if (du >= 256) du -= 512;
          dv = (((bv + (int16_t)vsA - vpred) % 256) + 256) % 256; if (dv >= 128) dv -= 256;
          lk_o_u0 = upred + du; lk_o_v0 = vpred + dv; lk_o_bu = bu; lk_o_bv = bv; lk_o_upred = upred; lk_o_vpred = vpred;
        }
      }
      lk_o_disp0 = LK_REG(1) & 0x40; lk_o_firston = lk_o_disp0 && !lk_o_dprev; lk_o_dprev = lk_o_disp0 != 0;
      if (rm == lk_o_room && (LK_REG(1) & 0x40)) lk_o_blanked = 0;
      if (!(LK_REG(1) & 0x40)) lk_o_blanked = 1;                         /* the display was switched off since the room number changed: the new room is really loaded */
      { static int seen_rm = -1; static long seen_f; extern long lk_world_frame;   /* the room number changed without the display being switched off (warp pad, tree warp): the new room is loaded when the game's world runs again (UpdateSprites) */
        if (rm != seen_rm) { seen_rm = rm; seen_f = platform_frame_number(); }
        { static int was_loading; int ld = lk_loadroom_on(); if (lk_o_fx && rm != lk_o_room && lk_o_room >= 0 && !lk_o_blanked && (lk_world_frame > seen_f || lk_fadein_on() || (was_loading && !ld))) lk_o_blanked = 1; was_loading = ld; } }   /* LoadRoomPath has returned = the new room is loaded */
      lk_o_why = 0;
      if (rm != lk_o_room && lk_o_room >= 0 && !lk_o_blanked && !lk_o_fx) { fr_done = 0; lk_o_why = 1; }   /* with the effects on the OLD room goes on being drawn (fade out, white fade, warp) until the new one is loaded */   /* the room number changes while the OLD room is still on screen (fade-out): keep the game's picture until the load has blanked the screen */
      else if (lk_warpfx() && !lk_o_fx) { fr_done = 0; lk_o_why = 2; }                                        /* the warp pad (teleport) effect: the game's picture stays (the effect is not ported) */
      else if (lk_sh_hide) { fr_done = 0; lk_o_why = 3; }                                         /* the Start menu is running (CheckForMenuOpen, also its fades): the game's picture stays, the map of RAM is not what is on screen then */
      else if (!(LK_REG(1) & 0x40)) { fr_done = 0; lk_o_why = 4; }                                  /* display switched off at the top of the frame (room load, blackout): the game's black picture stays */
      else if (rm > 0 && rm < 800) { if (rm != lk_o_room && (!lk_o_fx || lk_o_blanked || lk_o_room < 0)) { lk_o_room_load(rm); lk_o_blanked = 0; } { /* which pass are the VDP's sprites from? (the game runs 0, 1 or 2 passes per frame, so the sprite table is sometimes the previous pass' and sometimes the current one): the candidate whose sprite boxes equal the real sprite table's best wins */
        uint32 sat[96], kc[96], kp[96]; int ns = 0, i4 = 0, n4 = 0, nc, np_, mc = 0, mp = 0, i5, j5, base = (LK_REG(5) & 0x7F) << 9;
        for (n4 = 0; n4 < 80 && ns < 96; n4++) { int y = ((LK_SATB(8 * i4) << 8) | LK_SATB(8 * i4 + 1)) & 0x1FF, sz = (LK_SATB(8 * i4 + 2) << 8) | LK_SATB(8 * i4 + 3), x = ((LK_SATB(8 * i4 + 6) << 8) | LK_SATB(8 * i4 + 7)) & 0x1FF;
          lk_o_satw[ns] = (LK_SATB(8 * i4 + 4) << 8) | LK_SATB(8 * i4 + 5); lk_o_satt[ns] = lk_o_satw[ns] & 0x7FF; sat[ns] = (uint32)(x << 20 | y << 8 | ((sz >> 8) & 15)); lk_o_satk[ns] = sat[ns]; ns++; i4 = sz & 0x7F; if (!i4) break; }
        lk_o_satn = ns;
        { const uint8 *rc = r, *rp = lk_o_use; lk_o_cc = rc; lk_o_cp = rp;
        nc = lk_o_sprites(rc, 0, kc, 0); np_ = lk_o_sprites(rp, 0, kp, 0); }
        for (i5 = 0; i5 < nc; i5++) for (j5 = 0; j5 < ns; j5++) if (kc[i5] == sat[j5]) { mc++; break; }
        for (i5 = 0; i5 < np_; i5++) for (j5 = 0; j5 < ns; j5++) if (kp[i5] == sat[j5]) { mp++; break; }
        lk_o_sp = (lk_o_simple || lk_o_sprmode == 2 || (lk_o_sprmode == 1 && (2 * mc - nc) >= (2 * mp - np_))) ? lk_o_cc : lk_o_cp; }
      lk_o_r = r; lk_o_build(); lk_o_hudbuild(); { static long dbgf = -2; if (dbgf == -2) { const char *e = getenv("LANDSTALKER_OWN_DBG"); dbgf = e ? atol(e) : -1; }
      if (dbgf >= 0 && platform_frame_number() == dbgf) { int rr, cc, base = (reg[5] & 0x7F) << 9, i4 = 0, k; printf("owndbg: frame %ld room %d reg1 %02X reg11 %02X reg12 %02X reg17 %02X reg18 %02X reg10 %02X hint RAM %02X vpos RAM %04X\n", dbgf, rm, reg[1], reg[11], reg[12], reg[17], reg[18], reg[10], hint & 0xFF, SW(0xFF0FD4) & 0xFFFF); printf("owndbg: cram0 %04X cram1 %04X act0 %04X act1 %04X pixel40 %08X pixel0 %08X\n", (cram[0 ^ 1] << 8) | cram[1 ^ 1], (cram[2 ^ 1] << 8) | cram[3 ^ 1], SW(0xFF0ED0) & 0xFFFF, SW(0xFF0ED2) & 0xFFFF, (unsigned)pixel[0x40], (unsigned)pixel[0]); printf("owndbg: pix[1] %08X pix[17] %08X pix[33] %08X pix[49] %08X reg7 %02X blanked %d fxon %d fx %d room %d own room %d\n", (unsigned)lk_o_pix[1], (unsigned)lk_o_pix[17], (unsigned)lk_o_pix[33], (unsigned)lk_o_pix[49], LK_REG(7), lk_o_blanked, lk_o_fxon, lk_o_fx, rm, lk_o_room);
        for (rr = 0; rr < 28; rr++) { int nz = 0; for (cc = 0; cc < 40; cc++) { int w = SW(0xFF1C00 + 0x80 * rr + 2 * cc); if (w != 0 && w != 0xE6B4 && w != 0x66B4) nz++; } if (nz) { printf("owndbg: window row %d: %d interesting words:", rr, nz); for (cc = 0; cc < 40; cc++) printf(" %04X", SW(0xFF1C00 + 0x80 * rr + 2 * cc) & 0xFFFF); printf("\n"); } }
        for (k = 0; k < 40; k++) { int y = ((vram[(base + 8 * i4) ^ 1] << 8) | vram[(base + 8 * i4 + 1) ^ 1]) & 0x3FF, sz = (vram[(base + 8 * i4 + 2) ^ 1] << 8) | vram[(base + 8 * i4 + 3) ^ 1], tw = (vram[(base + 8 * i4 + 4) ^ 1] << 8) | vram[(base + 8 * i4 + 5) ^ 1], x = ((vram[(base + 8 * i4 + 6) ^ 1] << 8) | vram[(base + 8 * i4 + 7) ^ 1]) & 0x1FF; printf("owndbg: SAT %d: y %d x %d size %02X tile %04X\n", i4, y - 128, x - 128, (sz >> 8) & 15, tw); i4 = sz & 0x7F; if (!i4) break; } } }
    if (lk_o_txlog && (hint & 0xFF) == 0xA0) { int rr, cc, nd = 0; for (rr = 0; rr < 8; rr++) for (cc = 0; cc < 40; cc++) if ((OW(0x23900 + 2 * (rr * 40 + cc)) | 0x6000) != SW(0xFF2600 + 0x80 * rr + 2 * cc)) nd++; if (nd) printf("own: text box tilemap differs from the game's in %d words, frame %ld room %d\n", nd, platform_frame_number(), rm); } if (lk_o_txlog > 1) lk_ot_dbg(vram, platform_frame_number()); else if (lk_o_txlog) { int bad = lk_ot_check(vram); if (bad > 0) printf("own: text mirror differs from VRAM in %d bytes, frame %ld room %d\n", bad, platform_frame_number(), rm); } if (lk_o_palmode) lk_o_palette(rm); fr_done = 1; } else fr_done = 0;
    } else { fr_done = 0; lk_o_why = 5; }
    { static int sl = -1; if (sl < 0) { const char *q = getenv("LANDSTALKER_SEAM_LOG"); sl = q ? atoi(q) : 0; } if (sl >= 2) printf("seam: frame %ld rm %d drawn %d why %d reg1 %02X L %X cell %d,%d z %d disp0 %d blanked %d\n", platform_frame_number(), rm, lk_o_room, lk_o_why, reg[1], (int)(int16_t)(SW(0xFF0F50) - SW(0xFF0F52)), UB(0xFF5400), UB(0xFF5401), (int)(int16_t)SW(0xFF5412), lk_o_disp0, lk_o_blanked); }   /* LANDSTALKER_SEAM_LOG=1: per frame state of room changes (docs/STAGE3_INVENTORY.md S3.5) */
    lk_seam_step(rm, fr_done, cam0, cam2, lk_o_u0, lk_o_v0);   /* S3.5 */
    memcpy(lk_o_prev, r, sizeof lk_o_prev); lk_o_valid = 1;
    if (((r[(0xFF11DE & 0xFFFF) ^ 1] << 8) | r[(0xFF11DF & 0xFFFF) ^ 1]) == 0) { memcpy(lk_o_good, r, sizeof lk_o_good); lk_o_goodok = 1; }   /* the player is first in a complete visible list: remember the last complete state */
    fr_n++;
    if (lk_o_diff >= 0 && lk_o_log > 0 && fr_n % lk_o_log == 0) { int ca = 0, cb = 0, tn = 0, i2, j2; for (i2 = 0; i2 < 152; i2++) for (j2 = 0; j2 < 304; j2++) { ca += (lk_o_pa[i2][j2] >> 16) & 1; cb += (lk_o_pb[i2][j2] >> 16) & 1; } for (i2 = 0; i2 < 0x12000; i2++) tn += lk_o_tiles[i2] != 0;
      printf("own: frame %ld room %d lines 0..223: %ld of %ld pixels differ (cells A %d B %d, tile bytes %d, scroll A %d,%d B %d,%d cam %d,%d, player flags2 use %02X cur %02X, sprites %d, reg1 %02X fade %d disp0 %d)\n", platform_frame_number(), rm, lk_o_diff, lk_o_tot, ca, cb, tn, hsA, vsA, hsB, vsB, cam0, cam2, UB(0xFF540C), bus_get_ram()[(0xFF540C & 0xFFFF) ^ 1], lk_o_nspr, reg[1], lk_o_fade, lk_o_disp0); }
    lk_o_diff = 0; lk_o_tot = 0;
  }
  e = lk_wide_e; map = lk_map_decide();
  if (line == 0 && map && !fr_done && lk_scr_log >= 2) printf("ownwhy: frame %ld reason %d reg1 %02X\n", platform_frame_number(), lk_o_why, reg[1]);
  if (!fr_done || w != 320 + 2 * e || !map) { if (w == 320 + 2 * e && (!map || (line != 23 && (!fr_done || !(reg[1] & 0x40) || lk_tall_keep(line))))) lk_scr_row(row, e, line, map); return; }   /* map frames: line 23 stays the game's (Map Behind Text draws it twice, tools/patch_tbox.py) */   /* (map frames the own map path does not draw - menu fades, effects the game draws - keep the game's picture: its widened / full-height band does not come from the VDP state) */   /* not the own map picture: the generic screen renderer (title, menus, picture screens, fades) */
  if (lk_o_hudn < 0) lk_o_hudn = lk_o_lz77(0x9242, lk_o_hud, 0x1000);
  {
    int ubase = lk_o_u0, vbase = lk_o_v0 + line, i, text = (line >= 160 && (hint & 0xFF) == 0xA0);
    int black_line = (line >= 185 && !text && !lk_tall_keep(line));   /* below the game's HInt display-off line (full height off) */

    if (lk_o_cammode == 2) {   /* the game may change the scroll registers during the frame: use the values of THIS line */
      int hs2 = 0, vs2 = 0, du, dv;
      if (!lk_o_sc_ram) { int hsb2 = (LK_REG(13) & 0x3F) << 10; hs2 = (int16_t)((vram[hsb2 ^ 1] << 8) | vram[(hsb2 + 1) ^ 1]); vs2 = (int16_t)((vsram[0 ^ 1] << 8) | vsram[1 ^ 1]); }
      if (lk_o_sc_ram) { hs2 = (int16_t)hsA; vs2 = (int16_t)vsA; if (lk_o_fx && line < 224) { int hm = lk_o_r[0x0FC7 ^ 1] & 3, ln = hm == 3 ? line : hm == 2 ? (line & ~7) : 0; { int hb3 = (LK_REG(13) & 0x3F) << 10; hs2 = (lk_o_vmirror && !lk_o_scrvars) ? (int16_t)((lk_vm[hb3 + 4 * ln] << 8) | lk_vm[hb3 + 4 * ln + 1]) : (int16_t)((lk_o_r[(0x0100 + 4 * ln) ^ 1] << 8) | lk_o_r[(0x0101 + 4 * ln) ^ 1]); } } }   /* the game's per-line hscroll table, mode from its shadow of VDP register 11 $FF0FC6 (0 = one entry, 2 = 8 line cells, 3 = per line; the tree warp swirls it) */
      du = (((lk_o_bu - hs2 - lk_o_upred) % 512) + 512) % 512; if (du >= 256) du -= 512;
      dv = (((lk_o_bv + vs2 - lk_o_vpred) % 256) + 256) % 256; if (dv >= 128) dv -= 256;
      ubase = lk_o_upred + du; vbase = lk_o_vpred + dv + line;
    }    int wlo = 0, whi = w, tb = lk_tbox_get(), wline = (line == 23 || text);   /* window lines (HUD row 2's last pixel line, the text box): Map Behind Text keeps only the part between the first and last non-black opaque window pixel, the empty / black ends show the map (patch_tbox.py) */
    if (wline && tb) {
      for (wlo = 0; wlo < w; wlo++) { int x = wlo - e, wp = (x >= 0 && x < 320) ? lk_o_win(line, x, hint) : -1; if (wp >= 0 && (wp & 0xF) && (lk_o_pix[wp & 0x3F] & 0x00FFFFFF)) break; }
      for (whi = w; whi > wlo; whi--) { int x = whi - 1 - e, wp = (x >= 0 && x < 320) ? lk_o_win(line, x, hint) : -1; if (wp >= 0 && (wp & 0xF) && (lk_o_pix[wp & 0x3F] & 0x00FFFFFF)) break; }
    }
    for (i = 0; i < w; i++) {
      int x = i - e, margin = (x < 0 || x >= 320), pick = -1, ap = 0, bp = 0, ai, bi, apal = 0, bpal = 0, sl = line - lk_sm_syn, si = i - lk_sm_sxn, sp = (sl >= 0 && sl < 224 && si >= 0 && si < LK_OSW) ? lk_o_spr[sl][si] : 0, col, black = black_line, src = 0; lk_o_fi_t afi, bfi; const lk_nb_t *nbq = 0;
      if (!black) {
        ai = lk_o_fetch(lk_o_pa, ubase + x - lk_sm_sxn, vbase - lk_sm_syn, &apal, &ap, &afi); bi = lk_o_fetch(lk_o_pb, ubase + x - lk_sm_sxn, vbase - lk_sm_syn, &bpal, &bp, &bfi);   /* image coordinates: independent of the VDP planes and their wrap */
        if ((sp & 0x200) && (sp & 0x100)) { pick = sp & 0x3F; src = 1; }
        else if (ai && ap) { pick = apal * 16 + ai; src = 2; }
        else if (bi && bp) { pick = bpal * 16 + bi; src = 3; }
        else if (sp & 0x200) { pick = sp & 0x3F; src = 1; }
        else if (ai) { pick = apal * 16 + ai; src = 2; }
        else if (bi) { pick = bpal * 16 + bi; src = 3; }
        else { pick = LK_REG(7) & 0x3F;                                   /* backdrop colour */
          if (lk_nbn > 0 && lk_seam_get()) { int pk[1]; const lk_nb_t *nq = 0; if (lk_nb_lookup(ubase, vbase + 0, x, pk, &nq)) { pick = pk[0]; nbq = nq; src = 6; } }   /* step 2: the neighbour rooms that stay loaded fill the void */
          if (src == 0 && lk_sm_state >= 2 && lk_sm_alpha > 0) {           /* S3.5: the old room's scenery behind the new room's void */
            int opA = 0, opB = 0, oqA = 0, oqB = 0, oa = lk_sm_fetch(lk_sm_pa, lk_sm_ou0 + x - lk_sm_sxo, lk_sm_ov0 + line - lk_sm_syo, &opA, &oqA), ob = lk_sm_fetch(lk_sm_pb, lk_sm_ou0 + x - lk_sm_sxo, lk_sm_ov0 + line - lk_sm_syo, &opB, &oqB);
            if (oa && oqA) { pick = opA * 16 + oa; src = 5; } else if (ob && oqB) { pick = opB * 16 + ob; src = 5; } else if (oa) { pick = opA * 16 + oa; src = 5; } else if (ob) { pick = opB * 16 + ob; src = 5; }
          } }
        if (margin) { if (line < 23 || (wline && !tb)) black = 1; }   /* margins next to the HUD bar stay black; next to the text box only with Map Behind Text off */
        else { int wp = lk_o_win(line, x, hint); if (wp >= 0 && (wp & 0xF) && i >= wlo && i < whi) { if (!(text && (sp & 0x200) && (sp & 0x100) && !(wp & 0x200))) { pick = wp & 0x3F; src = 4; } }   /* a sprite is above a low priority window pixel (the yes / no arrow in the text box), a high priority one only above a low window pixel */ else if (wp >= 0 && !tb && wline) black = 1; }   /* transparent window pixels and the black ends of the window line show the map */
      }
      col = black ? (margin ? (lk_o_regvdp ? pixel[0x40] : lk_o_palmode ? lk_o_pix[LK_REG(7) & 0x3F] : pixel_lut[1][0]) : pixel_lut[1][0]) : (lk_o_palmode ? (lk_o_fxon ? lk_o_fxpix[lk_o_fxk[line & 255]][pick & 0x3F] : lk_o_pix[pick & 0x3F]) : pixel[pick & 0x3F]);
      if ((src == 2 || src == 3) && !black && lk_nbn > 0 && (col & 0xFFFFFF) == 0 && lk_seam_get()) {   /* the room's own black edge pixels (the shading of its map edge) are void for the neighbours: a thin black line stayed between two rooms otherwise */
        int pk[1]; const lk_nb_t *nq = 0;
        if (lk_nb_lookup(ubase, vbase, x, pk, &nq)) { PIXEL_OUT_T nc = (pk[0] < 16) ? nq->pix0[pk[0] & 15] : lk_o_pix[pk[0] & 0x3F]; if ((nc & 0xFFFFFF) != 0) { pick = pk[0]; nbq = nq; src = 6; } }
      }
      if ((src == 0 || src == 2 || src == 3) && (col & 0xFFFFFF) == 0 && !black && !margin && lk_nbn > 0 && line > 27 && lk_seam_get()) {   /* a void pixel with picture a few pixels above and below it is a seam between two rooms: fill it with the colour of the row above */
        int d, up = -1, below = 0;
        for (d = 1; d <= 6 && up < 0; d++) if (!lk_vhv[(line - d) & 7][i] && (lk_vh[(line - d) & 7][i] & 0xFFFFFF)) up = d;
        if (up > 0) {
          for (d = 1; d <= 8 && !below; d++) { int ap2 = 0, aq = 0, bp2 = 0, bq = 0, pk2[1]; const lk_nb_t *nq2 = 0;
            if (lk_o_fetch(lk_o_pa, ubase + x - lk_sm_sxn, vbase - lk_sm_syn + d, &ap2, &aq, 0) || lk_o_fetch(lk_o_pb, ubase + x - lk_sm_sxn, vbase - lk_sm_syn + d, &bp2, &bq, 0) || lk_nb_lookup(ubase, vbase + d, x, pk2, &nq2)) below = 1; }
          if (below) { col = lk_vh[(line - up) & 7][i]; src = 7; }
        }
      }
      if (src == 6 && !black && nbq) col = (pick < 16) ? nbq->pix0[pick & 15] : lk_o_pix[pick & 0x3F];   /* a neighbour room: line 0 = its own room palette, lines 1..3 the shared ones */
      if (src == 5 && !black) { PIXEL_OUT_T oc = lk_sm_pix[pick & 0x3F], bg = lk_o_pix[LK_REG(7) & 0x3F]; int a = lk_sm_alpha, ch; PIXEL_OUT_T o = oc & 0xFF000000u;   /* S3.5: the old room's colour, dissolving into the backdrop */
        for (ch = 0; ch < 24; ch += 8) o |= (PIXEL_OUT_T)(((((oc >> ch) & 255) * (unsigned)a + ((bg >> ch) & 255) * (unsigned)(256 - a)) >> 8) & 255) << ch;
        col = o; }
      lk_vh[line & 7][i] = (PIXEL_OUT_T)col; lk_vhv[line & 7][i] = (src == 0 || black || margin || (col & 0xFFFFFF) == 0) ? 1 : 0;
      lk_o_tot++; if (row[i] != (PIXEL_OUT_T)col) lk_o_diff++;
      if (lk_hd_n && x >= -LK_HDO && x < 320 + LK_HDO) {                    /* HD rows (the widescreen margins too): the winning layer's replacement tile (the compositor of the screens does the same) */
        lk_pi_t pi; memset(&pi, 0, sizeof pi);
        if (!black && (pick & 0xF) && lk_o_hdwant()) {
          if (src == 1) { void *rp = lk_o_sprrep[sl][si]; if (rp) { uint8 q = lk_o_sprpx[sl][si]; pi.rep = (lk_rep_t *)rp; pi.ox = q & 7; pi.oy = (q >> 3) & 7; pi.hf = (q >> 6) & 1; pi.vf = q >> 7; pi.pal = (pick >> 4) & 3; } }
          else if (src == 2 || src == 3) { const lk_o_fi_t *f = src == 2 ? &afi : &bfi; pi.rep = (lk_rep_t *)lk_o_repfor(f->t, (pick >> 4) & 3, 1); pi.ox = f->ix; pi.oy = f->iy; pi.hf = f->hf; pi.vf = f->vf; pi.pal = (pick >> 4) & 3; }
          else if (src == 4 && lk_o_wfi.t) { const lk_o_fi_t *f = &lk_o_wfi; pi.rep = (lk_rep_t *)lk_o_repfor(f->t, (pick >> 4) & 3, 1); pi.ox = f->ix; pi.oy = f->iy; pi.hf = f->hf; pi.vf = f->vf; pi.pal = (pick >> 4) & 3; }
          if (lk_org_log > 0) { uint32_t rm2; const uint8 *tp = src == 1 ? 0 : src == 2 ? afi.t : src == 3 ? bfi.t : lk_o_wfi.t; if (tp) { if (lk_org_lookup_raw(tp, &rm2, 0)) lk_o_orgk++; else lk_o_orgu++; } }
        }
        lk_hd_mapmode = 1; lk_hd_put(line, x, (uint32_t)col, pi.rep ? &pi : 0); lk_hd_mapmode = 0; lk_hd_ref[line * LK_HDW + x + LK_HDO] = (uint32_t)col;
      }
      if (lk_o_mode == 2) row[i] = (PIXEL_OUT_T)col;
    }
    if (lk_hd_n) lk_hd_stamp[line] = lk_hd_gen;
    if (line == 223 && lk_org_log > 0 && platform_frame_number() % lk_org_log == 0) { printf("ownorg: frame %ld map (own path): opaque layer pixels with a known ROM origin %ld, unknown %ld; sprite tiles known %ld, unknown %ld (cumulative)\n", platform_frame_number(), lk_o_orgk, lk_o_orgu, lk_o_sprk, lk_o_spru); }
  }
}

'''
    s = s.replace(c, module + c, 1)
    open(p, "w").write(s)
    print("patched vdp_render.c: " + VER)
else:
    print("vdp_render.c already patched: " + VER)
