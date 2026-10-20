#!/usr/bin/env python3
"""Own text box tiles (2026-10-20, own renderer step 'dialogue text'): a MIRROR of the game's text tile buffer `g_ScreenBuffer $FF3900` that is built from the game's own print calls
by an own C port, so that the own renderer (tools/patch_own.py) no longer reads the game's buffer / the VDP copy of it.
Hooks (func_table_register wrappers, the original always runs afterwards): PrintCharDirect $0235FE (one glyph: port of PrintChar $023640 / sub_2371A / sub_23702, inputs = char code d0,
text x `$FF1194`, text y `$FF1129`, colour `$FF112A`, font `MainFont` via `MainFontPtr $022E84`; same algorithm as tools/romtext.py), ClearTextboxTiles $023526 (fill $AA: normal dialogue box with 3 text lines $D80 words, with the inventory
window open ($FF0FD4 = $921C) only $900 words), ScrollTextBuffer $02358E (one scroll step; ScrollTextBoxUp $023582 runs 8 of them, each followed by the DMA copy), DMACopyTextboxTiles $02355A (the 'visible' copy = what the game sends to
VRAM $A500; `lk_ot_vis`).  Inventory window open = `g_VDPReg18_WindowVPos $FF0FD4` = $921C.
Exports: lk_ot_buf (the mirror), lk_ot_vis / lk_ot_visn (visible copy and its size in bytes), lk_ot_ok (a DMA copy has happened), lk_ot_check(const uint8_t *vram) -> number of bytes where the visible copy differs from
VRAM $A500 (test aid, `LANDSTALKER_OWN_TEXTLOG`).  Idempotent.
usage: patch_owntext.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_OWNTEXT v1"

p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "lk_bq_install" in s, "func_table.c: run patch_buyqty.py first"
    module = r'''/* ---- LK_OWNTEXT v1: mirror of the text tile buffer, built by an own port of the glyph printer (tools/patch_owntext.py) ---- */
uint8_t lk_ot_buf[0x1B00], lk_ot_vis[0x1B00]; int lk_ot_visn, lk_ot_ok;
static gen_func_t lk_ot_o_pc, lk_ot_o_clr, lk_ot_o_scr, lk_ot_o_dma;
static int lk_ot_inv(void) { return bus_read16(0xFF0FD4u) == 0x921C; }
static void lk_ot_print(int code, int x, int y, int colour) {   /* PrintCharDirect -> PrintChar: one glyph into the mirror */
    uint32_t glyph; int d6 = 14, d1 = colour & 0xFF, d2 = colour & 0xFF, a2, d5 = y & 0xFF, row, i, k;
    if (code == 0) return;
    if (code == 0x7B || code == 0x7C) d6 = 3;
    glyph = bus_read32(0x022E84u) + 30u * (uint32_t)code;
    if (x & 1) d2 = ((d2 << 4) & 0xF0) | 0x0A; else d1 = ((d1 << 4) & 0xF0) | 0x0A;
    a2 = ((const int[]){0, 0x900, 0x1200, 0x1200})[(y & 0x30) >> 4] + (y & 0x0F) * 4 + (x & 0xF8) * 8;
    for (row = 0; row <= d6; row++) {
        int word = bus_read16(glyph + 2u * (uint32_t)row); uint8_t ink[12];
        for (i = 0; i < 12; i++) ink[i] = (x & 1) ? ((i & 1) ? 0xAA : 0x0A) : ((i & 1) ? 0x0A : 0xAA);
        if (word) for (k = 0; k < 12; k++) if (word & (0x8000 >> k)) ink[k] = (k % 2 == 0) ? d1 : d2;
        for (i = 0; i < 12; i++) {
            int d0 = ink[i], e, b, off;
            if (d0 == 0x0A || d0 == 0xAA) continue;
            e = (x & 7) + i; b = e / 2;
            off = a2 + (b < 4 ? b : b < 8 ? 0x40 + b - 4 : 0x80 + b - 8);
            if (off < 0 || off >= (int)sizeof lk_ot_buf) continue;
            if (e % 2 == 0) lk_ot_buf[off] = (uint8_t)d0; else lk_ot_buf[off] = (uint8_t)((lk_ot_buf[off] & 0xF0) | (d0 & 0x0F));
        }
        a2 += 4; d5++;
        if (d5 == 0x10 || d5 == 0x20) a2 += 0x8C4;
    }
}
static void lk_ot_dma(void) { int n = lk_ot_inv() ? 0x1200 : 0x1B00; memcpy(lk_ot_vis, lk_ot_buf, (size_t)n); lk_ot_visn = n; lk_ot_ok = 1; }
static void lk_ot_scroll_step(void) {   /* ScrollTextBuffer $02358E: every 64 byte column block moves up 8 bytes (2 pixel rows), the freed bytes come from the next band, the last band gets $AA */
    int inv = lk_ot_inv(), bands = inv ? 2 : 3, i, b; uint8_t head[8];
    for (i = 0; i < 36; i++) for (b = 0; b < bands; b++) {
        uint8_t *blk = lk_ot_buf + i * 0x40 + b * 0x900;
        if (b + 1 < bands) memcpy(head, blk + 0x900, 8); else memset(head, 0xAA, 8);
        memmove(blk, blk + 8, 56); memcpy(blk + 56, head, 8);
    }
}
static void lk_ot_h_pc(void) { lk_ot_print((int)(g_m68k.d[0] & 0xFFFFu) & 0xFF, bus_read16(0xFF1194u), bus_read8(0xFF1129u), bus_read8(0xFF112Au)); lk_ot_o_pc(); }
static void lk_ot_h_clr(void) { memset(lk_ot_buf, 0xAA, lk_ot_inv() ? 0x1200 : 0x1B00); lk_ot_o_clr(); }
static void lk_ot_h_scr(void) { lk_ot_scroll_step(); lk_ot_o_scr(); }   /* one step: ScrollTextBoxUp $023582 runs it 8 times, each followed by DMACopyTextboxTiles (the hook above) */
static void lk_ot_h_dma(void) { lk_ot_dma(); lk_ot_o_dma(); }
int lk_ot_check(const uint8_t *vram) {   /* bytes of the visible copy that differ from VRAM $A500 (the VDP array is byte swapped: [a ^ 1]) */
    int i, bad = 0; if (!lk_ot_ok) return -1;
    for (i = 0; i < lk_ot_visn; i++) if (lk_ot_vis[i] != vram[(0xA500 + i) ^ 1]) bad++;
    return bad;
}
void lk_ot_dbg(const uint8_t *vram, long frame) {   /* test aid LANDSTALKER_OWN_TEXTLOG=2: mirror vs the game's RAM buffer ($FF3900) and visible copy vs VRAM, first differing offsets */
    int i, nb = 0, nv = 0, fb = -1, fv = -1;
    for (i = 0; i < 0x1B00; i++) if (lk_ot_buf[i] != bus_read8(0xFF3900u + (uint32_t)i)) { if (fb < 0) fb = i; nb++; }
    for (i = 0; i < lk_ot_visn; i++) if (lk_ot_vis[i] != vram[(0xA500 + i) ^ 1]) { if (fv < 0) fv = i; nv++; }
    if (nb || nv) fprintf(stderr, "owntext: frame %ld buf!=RAM %d (first %04X: mine %02X game %02X), vis!=VRAM %d (first %04X: mine %02X vram %02X), visn %04X, text x %d y %d\n", frame, nb, fb < 0 ? 0 : fb, fb < 0 ? 0 : lk_ot_buf[fb], fb < 0 ? 0 : bus_read8(0xFF3900u + (uint32_t)fb), nv, fv < 0 ? 0 : fv, fv < 0 ? 0 : lk_ot_vis[fv], fv < 0 ? 0 : vram[(0xA500 + fv) ^ 1], lk_ot_visn, bus_read16(0xFF1194u), bus_read8(0xFF1129u));
}
static void lk_ot_install(void) {
    static int done;
    if (done) return;
    done = 1; memset(lk_ot_buf, 0xAA, sizeof lk_ot_buf); memset(lk_ot_vis, 0xAA, sizeof lk_ot_vis);
    lk_ot_o_pc = func_table_lookup(0x0235FE); lk_ot_o_clr = func_table_lookup(0x023526); lk_ot_o_scr = func_table_lookup(0x02358E); lk_ot_o_dma = func_table_lookup(0x02355A);
    if (lk_ot_o_pc && lk_ot_o_clr && lk_ot_o_scr && lk_ot_o_dma) {
        func_table_register(0x0235FE, lk_ot_h_pc); func_table_register(0x023526, lk_ot_h_clr); func_table_register(0x02358E, lk_ot_h_scr); func_table_register(0x02355A, lk_ot_h_dma);
    } else fprintf(stderr, "owntext: text routines not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_bq_install();   /* LK_BUYQTY v1 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_ot_install();   /* LK_OWNTEXT v1 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
else:
    print("func_table.c already patched:", VER)
