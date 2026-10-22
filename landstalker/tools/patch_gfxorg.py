#!/usr/bin/env python3
"""Own renderer, stage 2 groundwork: WHERE DO THE TILES ON THE SCREEN COME FROM (2026-10-22, user plan: HD / 3D assets later).
`DecompressLZ77Gfx $004AB2` (a0 = compressed graphics in the ROM, a1 = destination buffer in work RAM) is wrapped: after it ran, every 32 byte tile of the output is hashed (FNV-1a 64) and
entered in a table  hash -> (ROM address of the compressed block, tile index inside it).  The picture side looks a VRAM tile up by the hash of its 32 bytes (`lk_org_lookup`), so every tile
that came out of the game's compressed graphics (tilesets, figures, HUD, title / menu art ...) has a stable origin id, independent of where the game put it in VRAM and of how it was DMAed.
Content based on purpose: it works for every write path (DMA, copy queue, direct data port) and is the same key a texture pack for the planned HD mode would use.
Exports: int lk_org_lookup(const uint8_t *vram, int tile, uint32_t *rom, int *idx)  (vram = the VDP's array, tile = tile number), int lk_org_count(void).
Test: LANDSTALKER_OWN_ORGLOG=1 (tools/patch_own.py prints, per screen frame, how many of the visible opaque pixels have a known origin).  Needs patch_ownvb.py before it.  Idempotent.
usage: patch_gfxorg.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
VER = "LK_GFXORG v1"
p = os.path.join(root, "src/func_table.c")
s = open(p).read()
if VER not in s:
    a = "static void lk_strip_extend(uint32_t a);\n"
    assert s.count(a) == 1 and "LK_OWNVB v3" in s, "func_table.c: run patch_ownvb.py first"
    module = r'''/* ---- LK_GFXORG v1: origin (ROM block + tile index) of tile graphics, found by content (tools/patch_gfxorg.py) ---- */
typedef struct { uint64_t h; uint32_t rom; uint16_t idx; uint16_t n; } lk_org_t;
#define LK_ORG_N 0x20000
static lk_org_t lk_org[LK_ORG_N]; static int lk_org_used; static gen_func_t lk_org_o;
static uint64_t lk_org_hash(const uint8_t *r, uint32_t a) { uint64_t h = 1469598103934665603ull; int i; for (i = 0; i < 32; i++) { h ^= r[((a + (uint32_t)i) & 0xFFFF) ^ 1]; h *= 1099511628211ull; } return h ? h : 1; }   /* VRAM and work RAM arrays are both byte swapped per 16 bit word */
static void lk_org_add(uint64_t h, uint32_t rom, int idx) {
    uint32_t i = (uint32_t)(h >> 20) & (LK_ORG_N - 1);
    while (lk_org[i].h && lk_org[i].h != h) i = (i + 1) & (LK_ORG_N - 1);
    if (!lk_org[i].h) { if (lk_org_used > LK_ORG_N * 3 / 4) return; lk_org[i].h = h; lk_org[i].rom = rom; lk_org[i].idx = (uint16_t)idx; lk_org_used++; }
    if (lk_org[i].n < 65535) lk_org[i].n++;
}
int lk_org_lookup(const uint8_t *vram, int tile, uint32_t *rom, int *idx) {
    uint64_t h = lk_org_hash(vram, (uint32_t)tile * 32u); uint32_t i = (uint32_t)(h >> 20) & (LK_ORG_N - 1);
    while (lk_org[i].h) { if (lk_org[i].h == h) { if (rom) *rom = lk_org[i].rom; if (idx) *idx = lk_org[i].idx; return 1; } i = (i + 1) & (LK_ORG_N - 1); }
    return 0;
}
int lk_org_count(void) { return lk_org_used; }
extern long platform_frame_number(void);
static void lk_org_h(void) {   /* DecompressLZ77Gfx: a0 = source (ROM), a1 = destination; a1 is the end of the output afterwards.  The function ends in tail jumps, so it is run to completion through func_table_jsr (the original registered for the moment) */
    uint32_t src = g_m68k.a[0], dst = g_m68k.a[1], end, t, ret = bus_read32(g_m68k.a[7]); const uint8_t *r;
    func_table_register(0x004AB2, lk_org_o);
    func_table_jsr(0x004AB2, ret);
    func_table_register(0x004AB2, lk_org_h);
    end = g_m68k.a[1]; r = bus_get_ram();
    { static int lg = -1; if (lg < 0) lg = getenv("LANDSTALKER_GFXORG_LOG") != NULL; if (lg) printf("gfxorg: frame %ld DecompressLZ77Gfx src $%06X dst $%06X end $%06X (%u bytes)\n", platform_frame_number(), src, dst, end, end - dst); }
    if (r && dst >= 0xFF0000u && end > dst && end - dst <= 0x10000u && src < 0x400000u)
        for (t = 0; t + 32 <= end - dst; t += 32) lk_org_add(lk_org_hash(r, (dst + t) & 0xFFFF), src, (int)(t / 32));
    func_table_rts();   /* the replaced function ends with RTS */
}
static void lk_org_install(void) {
    static int done;
    if (done) return;
    done = 1;
    lk_org_o = func_table_lookup(0x004AB2);
    if (lk_org_o) func_table_register(0x004AB2, lk_org_h); else fprintf(stderr, "gfxorg: DecompressLZ77Gfx not found\n");
}
'''
    s = s.replace(a, module + a, 1)
    h = "        lk_vb_install();   /* LK_OWNVB v3 */\n"
    assert s.count(h) == 1
    s = s.replace(h, h + "        lk_org_install();   /* LK_GFXORG v1 */\n", 1)
    open(p, "w").write(s)
    print("func_table.c patched:", VER)
else:
    print("func_table.c already patched:", VER)
