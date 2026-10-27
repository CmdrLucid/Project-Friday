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
/* Own mirror of the VDP memories (VRAM / CRAM / VSRAM): see patch_vdpmirror.py (the game queues no longer feed it). */
uint8_t lk_vm[0x10000], lk_vsm[0x50], lk_cm[0x80]; long lk_vm_ops;   /* VRAM / VSRAM / CRAM mirrors: filled at the chip's write sinks by tools/patch_vdpmirror.py (since 2026-10-27; this patch used to apply the game's two queues, which missed direct data port writes) */
static void lk_vb_h(void) { const uint8_t *r; lk_vb_o(); r = bus_get_ram(); if (r) { memcpy(lk_vb_ram, r, sizeof lk_vb_ram); lk_vb_n++; lk_vb_frame = platform_frame_number(); } }
static void lk_vb_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_vb_o = func_table_lookup(0x0011DE);
    if (lk_vb_o) func_table_register(0x0011DE, lk_vb_h); else fprintf(stderr, "ownvb: HandleVBlankInterrupt not found\n");
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
