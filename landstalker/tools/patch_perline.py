#!/usr/bin/env python3
"""genrecomp: render each scanline as the scanline clock passes it and fire
the horizontal interrupt (HInt), like GPGX's system_frame_gen. Without this the
whole frame is drawn once after the VBlank handler, so raster effects (Landstalker's
text-box HInt, status bars) never happen. GENRECOMP_PERLINE=0 restores the old way.
Idempotent.  usage: patch_perline.py path/to/genrecomp
"""
import sys, os

root = sys.argv[1]

def patch(rel, old, new, marker):
    p = os.path.join(root, rel)
    s = open(p).read()
    if marker in s:
        print(rel, "already patched:", marker); return
    assert old in s, f"{rel}: layout changed ({old[:50]!r})"
    open(p, "w").write(s.replace(old, new, 1))
    print(rel, "patched:", marker)

# --- bus.c: per-line render + HInt in the scanline loop ---------------------
patch("src/bus.c",
      "            fifo_cycles[0] = fifo_cycles[1] = fifo_cycles[2] = fifo_cycles[3] = 0;\n        }\n    }\n\n    s_in_tick = false;",
      "            fifo_cycles[0] = fifo_cycles[1] = fifo_cycles[2] = fifo_cycles[3] = 0;\n        }\n"
      "\n"
      "        /* LANDSTALKER_PERLINE: draw this line now and run the H-Int counter */\n"
      "        if (genrecomp_perline()) {\n"
      "            int ah = bitmap.viewport.h > 0 ? bitmap.viewport.h : 224;\n"
      "            if (v_counter == ah) {\n"
      "                /* first VBlank line: an H-Int may still be pending */\n"
      "                if (h_counter == 0) {\n"
      "                    hint_pending = 0x10;\n"
      "                    if (reg[0] & 0x10) recomp_m68k_interrupt(4);\n"
      "                }\n"
      "            } else if (v_counter == 0) {\n"
      "                h_counter = reg[10];\n"
      "                if (reg[1] & 0x40) parse_satb(-1);\n"
      "            }\n"
      "            if (v_counter < ah) {\n"
      "                if ((reg[1] & 0x44) && bitmap.viewport.w > 0 && bitmap.viewport.w <= 320)\n"
      "                    render_line(v_counter);\n"
      "                if (h_counter == 0) {\n"
      "                    h_counter = reg[10];\n"
      "                    hint_pending = 0x10;\n"
      "                    if (reg[0] & 0x10) recomp_m68k_interrupt(4);\n"
      "                } else {\n"
      "                    h_counter--;\n"
      "                }\n"
      "            }\n"
      "        }\n"
      "    }\n\n    s_in_tick = false;",
      "LANDSTALKER_PERLINE")
patch("src/bus.c",
      "#include \"genrecomp/func_table.h\"\n",
      "#include \"genrecomp/func_table.h\"\nint genrecomp_perline(void);\n",
      "int genrecomp_perline(void);")
patch("src/bus.c",
      "/* ================================================================\n * Instant VDP DMA",
      "/* 1 = draw per scanline + HInt (default), 0 = old all-at-once end-of-frame draw */\n"
      "int genrecomp_perline(void) {\n"
      "    static int v = -1;\n"
      "    if (v < 0) { const char *e = getenv(\"GENRECOMP_PERLINE\"); v = !(e && e[0] == '0'); }\n"
      "    return v;\n"
      "}\n\n"
      "/* ================================================================\n * Instant VDP DMA",
      "int genrecomp_perline(void) {")

# --- genrecomp.c: skip the all-at-once draw when drawing per line -------------
patch("src/genrecomp.c",
      "    if ((reg[1] & 0x44) && vp_w > 0 && vp_w <= 320) {",
      "    extern int genrecomp_perline(void);\n"
      "    if (!genrecomp_perline() && (reg[1] & 0x44) && vp_w > 0 && vp_w <= 320) {",
      "genrecomp_perline()")
