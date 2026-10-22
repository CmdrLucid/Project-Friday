#!/usr/bin/env python3
"""Own renderer: the game state AS THE VDP RECEIVES IT (2026-10-20, step 'remove the VDP dependencies').
The game hands everything the picture needs to the VDP inside its VBlank handler (HandleVBlankInterrupt $0011DE: sprite table DMA, queued DMA ops, scroll, palette).  A wrapper of that
handler copies the 64 KB work RAM right AFTER it ran: that snapshot is exactly the state the chip shows during the next frame (the game's passes that run later in the same frame are
NOT in it).  The own renderer builds its picture from this snapshot instead of guessing which of two later snapshots the VDP shows (tools/patch_own.py, LANDSTALKER_OWN_VB).
Exports: lk_vb_ram (64 KB, same byte order as bus_get_ram()), lk_vb_n (number of snapshots taken), lk_vb_frame (frame number of the last one).  Idempotent.
usage: patch_ownvb.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_OWNVB v3"
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "LK_OWNTEXT v1" in s, "func_table.c: run patch_owntext.py first"
    module = r'''/* ---- LK_OWNVB v3: RAM snapshot taken right after the VBlank handler = the state the VDP shows next (tools/patch_ownvb.py) ---- */
extern uint8_t *bus_get_ram(void); extern const uint8_t *bus_get_rom(uint32_t *size_out);
extern long platform_frame_number(void);
uint8_t lk_vb_ram[0x10000]; int lk_vb_n; long lk_vb_frame = -1;
static gen_func_t lk_vb_o;
/* Own mirror of the VRAM bytes the game sends through its DMA queue (QueueDMAOp -> g_DMAOpQueue $FF07D0, 16 bytes per op: $8F02, $94 len hi, $93 len lo, $96 / $95 / $97 source, command word 1 $4000 | dest & $3FFF, command word 2 ($80 | dest >> 14); ProcessQueuedDMAOps $001340 runs them all at the VBlank): the sprite tiles (and their poses) can be read without the VDP.  Applied BEFORE the original processes the queue (RAM sources are read at that moment, like the DMA does). */
uint8_t lk_vm[0x10000], lk_vsm[0x50], lk_cm[0x80]; long lk_vm_ops;   /* VRAM / VSRAM / CRAM mirrors of the DMA queue */
static gen_func_t lk_pq_o, lk_vc_o;
/* ProcessVRAMCopyQueue $00126C: the direct VRAM writes of the VBlank (hscroll table, nametable strips, ...): g_VRAMCopyQueue $FF0CD0, per entry: word 1 = length - 1 (bit 15 set = increment $40, bits 15 + 14 = $80, else 2), word 2 = VRAM address, then the data words; count in $FF0F8C, flag bit 0 of $FF0F8B */
static void lk_vc_h(void) {
    const uint8_t *r = bus_get_ram();
    if (r && (r[0x0F8B ^ 1] & 1) && r[0x0F8C ^ 1]) {
        int n = r[0x0F8C ^ 1], i; uint32_t p = 0x0CD0;
#define LK_W(o) (((uint32_t)r[((o) & 0xFFFF) ^ 1] << 8) | r[(((o) & 0xFFFF) + 1) ^ 1])
        for (i = 0; i < n && p < 0x0F00; i++) {
            uint32_t w0 = LK_W(p), addr = LK_W(p + 2), len = (w0 & 0x3FFF) + 1, inc = !(w0 & 0x8000) ? 2 : !(w0 & 0x4000) ? 0x40 : 0x80, k; p += 4;
            for (k = 0; k < len && p < 0x10000; k++) { uint32_t d = LK_W(p); p += 2; lk_vm[addr & 0xFFFF] = (uint8_t)(d >> 8); lk_vm[(addr + 1) & 0xFFFF] = (uint8_t)d; addr += inc; }
        }
#undef LK_W
    }
    lk_vc_o();
}
static void lk_pq_h(void) {
    const uint8_t *r = bus_get_ram(); uint32_t rsz = 0; const uint8_t *rom = bus_get_rom(&rsz);
    if (r && rom && (r[0x0F8B ^ 1] & 8) && r[0x0F8D ^ 1]) {
        int n = r[0x0F8D ^ 1], i;
        for (i = 0; i < n && i < 40; i++) {
            const uint8_t *o = r + 0x07D0 + 16 * i; uint32_t len, src, dst, k;
#define LK_OB(x) o[(x) ^ 1]
            len = ((uint32_t)LK_OB(3) << 8) | LK_OB(5); src = ((uint32_t)(LK_OB(11) & 0x7F) << 17) | ((uint32_t)LK_OB(7) << 9) | ((uint32_t)LK_OB(9) << 1);
            dst = (((uint32_t)LK_OB(12) << 8 | LK_OB(13)) & 0x3FFF) | ((((uint32_t)LK_OB(14) << 8 | LK_OB(15)) & 3) << 14);
            { uint32_t c1 = ((uint32_t)LK_OB(12) << 8) | LK_OB(13), c2 = ((uint32_t)LK_OB(14) << 8) | LK_OB(15), cd = (c1 >> 14) | ((c2 >> 2) & 0x1C);   /* command code: 1 = VRAM write, 5 = VSRAM write, 3 = CRAM write */
              uint8_t *tgt = cd == 1 ? lk_vm : cd == 5 ? lk_vsm : cd == 3 ? lk_cm : 0; uint32_t mask = cd == 1 ? 0xFFFF : cd == 5 ? 0x7F : 0x7F, lim = cd == 1 ? 0x10000 : cd == 5 ? 0x50 : 0x80;
              if (!len) len = 0x10000;
              if (tgt) for (k = 0; k < len * 2; k++) { uint8_t b; uint32_t d = (cd == 1 ? dst : (c1 & 0x7F)) + k; if (src >= 0xFF0000u) b = r[((src + k) & 0xFFFF) ^ 1]; else if (src + k < rsz) b = rom[(src + k) ^ 1]; else break; if (cd == 1) tgt[d & mask] = b; else if (d < lim) tgt[d] = b; } }
#undef LK_OB
            lk_vm_ops++;
        }
    }
    lk_pq_o();
}
static void lk_vb_h(void) { const uint8_t *r; lk_vb_o(); r = bus_get_ram(); if (r) { memcpy(lk_vb_ram, r, sizeof lk_vb_ram); lk_vb_n++; lk_vb_frame = platform_frame_number(); } }
static void lk_vb_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_vb_o = func_table_lookup(0x0011DE);
    if (lk_vb_o) func_table_register(0x0011DE, lk_vb_h); else fprintf(stderr, "ownvb: HandleVBlankInterrupt not found\n");
    lk_vc_o = func_table_lookup(0x00126C); if (lk_vc_o) func_table_register(0x00126C, lk_vc_h); else fprintf(stderr, "ownvb: ProcessVRAMCopyQueue not found\n");
    lk_pq_o = func_table_lookup(0x001340); if (lk_pq_o) func_table_register(0x001340, lk_pq_h); else fprintf(stderr, "ownvb: ProcessQueuedDMAOps not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_ot_install();   /* LK_OWNTEXT v1 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_vb_install();   /* LK_OWNVB v3 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
else:
    print("func_table.c already patched:", VER)
