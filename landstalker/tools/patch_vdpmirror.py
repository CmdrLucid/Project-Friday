#!/usr/bin/env python3
"""Own renderer, stage 2: A COMPLETE MIRROR OF EVERYTHING THE GAME WRITES TO THE VDP MEMORIES (2026-10-27, user: 'ich will sauber geloest sein vom emulator').
The mirror of tools/patch_ownvb.py only knew the game's two queues (DMA ops, VRAM copy queue); the direct data port writes of the title / intro / file select loaders and the DMA fill / copy
were missing, so the generic screen renderer could not leave the chip's VRAM.  This patch stores every write that reaches VRAM / CRAM / VSRAM (data port + 68k DMA through vdp_bus_w, DMA fill,
DMA copy) into the same mirror arrays (lk_vm natural byte order, lk_cm = the raw 16 bit colour words of the bus, lk_vsm) at the point where the chip decodes it.  Step B (later): replace the decode by an own
port model.  Check: LANDSTALKER_OWN_VMDIFF=<n> (tools/patch_own.py) lists VRAM bytes where mirror and chip differ.  Z80-side VDP modes are not touched (the game does not use them).
Idempotent.  usage: patch_vdpmirror.py path/to/genrecomp"""
import os, sys
root = sys.argv[1]
p = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_ctrl.c")
s = open(p).read()
VER = "LK_VDPMIRROR v1"
V2 = "LK_VDPMIRROR v2"
if VER in s and V2 in s:
    print("vdp_ctrl.c already patched:", V2); sys.exit(0)

# plain helper: replace the n-th occurrence (0 based)
def rep_nth(old, new, nth):
    global s
    idx = -1
    for _ in range(nth + 1):
        idx = s.find(old, idx + 1)
        assert idx >= 0, f"vdp_ctrl.c layout changed: {old[:60]!r} (#{nth})"
    s = s[:idx] + new + s[idx + len(old):]

if VER not in s:
    decl = "static void vdp_bus_w(unsigned int data);\n"
    assert s.count(decl) == 1
    s = s.replace(decl, "/* " + VER + " (tools/patch_vdpmirror.py) */\nextern uint8_t lk_vm[0x10000], lk_vsm[0x50], lk_cm[0x80];\n" + decl)

    # vdp_bus_w: VRAM word (data is already byte swapped for an odd address, like the chip's own store)
    rep_nth("      /* Only write unique data to VRAM */\n      if (data != *p)\n",
            "      lk_vm[index] = (uint8)(data >> 8); lk_vm[index + 1] = (uint8)data;   /* LK_VDPMIRROR */\n      /* Only write unique data to VRAM */\n      if (data != *p)\n", 0)
    # CRAM: raw bus word (the pack comment appears in vdp_bus_w first, then in the fill)
    pack = "      /* Pack 16-bit bus data (BBB0GGG0RRR0) to 9-bit CRAM data (BBBGGGRRR) */\n"
    rep_nth(pack, "      lk_cm[addr & 0x7E] = (uint8)(data >> 8); lk_cm[(addr & 0x7E) + 1] = (uint8)data;   /* LK_VDPMIRROR */\n" + pack, 0)
    rep_nth(pack, "      unsigned lk_raw = data;   /* LK_VDPMIRROR */\n" + pack, 1)
    rep_nth("        /* Increment CRAM address */\n",
            "        lk_cm[addr & 0x7E] = (uint8)(lk_raw >> 8); lk_cm[(addr & 0x7E) + 1] = (uint8)lk_raw;   /* LK_VDPMIRROR */\n        /* Increment CRAM address */\n", 0)
    # VSRAM
    rep_nth("      *(uint16 *)&vsram[addr & 0x7E] = data;\n",
            "      if ((addr & 0x7E) < 0x50) { lk_vsm[addr & 0x7E] = (uint8)(data >> 8); lk_vsm[(addr & 0x7E) + 1] = (uint8)data; }   /* LK_VDPMIRROR */\n      *(uint16 *)&vsram[addr & 0x7E] = data;\n", 0)
    rep_nth("        *(uint16 *)&vsram[addr & 0x7E] = data;\n",
            "        if ((addr & 0x7E) < 0x50) { lk_vsm[addr & 0x7E] = (uint8)(data >> 8); lk_vsm[(addr & 0x7E) + 1] = (uint8)data; }   /* LK_VDPMIRROR */\n        *(uint16 *)&vsram[addr & 0x7E] = data;\n", 0)
    # DMA copy / fill (VRAM)
    rep_nth("      /* Write byte to adjacent VRAM destination address */\n      WRITE_BYTE(vram, addr ^ 1, data);\n",
            "      lk_vm[(uint16)addr] = lk_vm[source];   /* LK_VDPMIRROR: from the mirror itself */\n      /* Write byte to adjacent VRAM destination address */\n      WRITE_BYTE(vram, addr ^ 1, data);\n", 0)
    rep_nth("        /* Write byte to adjacent VRAM address */\n        WRITE_BYTE(vram, addr ^ 1, data);\n",
            "        lk_vm[(uint16)addr] = data;   /* LK_VDPMIRROR */\n        /* Write byte to adjacent VRAM address */\n        WRITE_BYTE(vram, addr ^ 1, data);\n", 0)

if V2 not in s:
    # direct VRAM edits of the widescreen patch (patch_wide.py): the strip queue's word write and the name table clean-up
    old = "  data &= 0xFFFF;\n  if ((index & sat_base_mask) == satb) *(uint16 *) &sat[index & sat_addr_mask] = data;\n"
    assert s.count(old) == 1, "lk_vram_put_word layout changed"
    s = s.replace(old, "  data &= 0xFFFF;\n  lk_vm[index] = (uint8)(data >> 8); lk_vm[index + 1] = (uint8)data;   /* " + V2 + " */\n  if ((index & sat_base_mask) == satb) *(uint16 *) &sat[index & sat_addr_mask] = data;\n")
open(p, "w").write(s)
print("vdp_ctrl.c patched:", VER)
print("vdp_ctrl.c patched:", V2)

# the widescreen name table clean-up (vdp_render.c lk_clean_planes) clears the chip's tables: clear the mirror's too
pr = os.path.join(root, "ext/Genesis-Plus-GX/core/vdp_render.c")
r = open(pr).read()
if "LK_VDPMIRROR v2" not in r:
    old = "  if (size && ntbb + size <= 0x10000) memset(&vram[ntbb], 0, size);\n"
    assert r.count(old) == 1, "vdp_render.c: lk_clean_planes layout changed"
    r = r.replace(old, old + "  { extern uint8_t lk_vm[]; if (size && ntab + size <= 0x10000) memset(&lk_vm[ntab], 0, size); if (size && ntbb + size <= 0x10000) memset(&lk_vm[ntbb], 0, size); }   /* LK_VDPMIRROR v2 */\n")
    open(pr, "w").write(r); print("vdp_render.c patched: LK_VDPMIRROR v2")

# LK_NOCHIP v1: the chip's own line composition (render_bg / render_obj) can be skipped: the own renderer draws every line from the mirror (test aid and option LANDSTALKER_OWN_NOCHIP=0 puts the chip back, default ON since 2026-10-27; always on with HD graphics)
r = open(pr).read()
if "LK_NOCHIP v1" not in r:
    old = "    /* Render BG layer(s) */\n    render_bg(line);\n\n    /* Render sprite layer */\n    render_obj(line & 1);\n    lk_wide_margins(line);"
    assert r.count(old) == 1, "vdp_render.c: render_line layout changed (nochip)"
    new = ("    /* LK_NOCHIP v1 */\n    { static int lk_nochip = -1; if (lk_nochip < 0) lk_nochip = !(getenv(\"LANDSTALKER_OWN_NOCHIP\") && *getenv(\"LANDSTALKER_OWN_NOCHIP\") == '0');\n"
           "      if (!lk_nochip || lk_hd_n) {\n    /* Render BG layer(s) */\n    render_bg(line);\n\n    /* Render sprite layer */\n    render_obj(line & 1);\n      } }\n    lk_wide_margins(line);")
    r = r.replace(old, new); open(pr, "w").write(r); print("vdp_render.c patched: LK_NOCHIP v1")
