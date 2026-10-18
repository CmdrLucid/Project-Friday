#!/usr/bin/env python3
"""romscreen.py ROM DUMP out.png [LINE1 [LINE2 [LINE3]]]   -- the whole 320 x 224 picture of a RAM dump drawn WITHOUT the VDP: room (romrender, ROM data + tile animation), figures (romsprite), all four palette
lines (romrender.rom_cram), HUD (rows 0..2) and text box (rows 20..27) from the window plane buffers in RAM + ROM tiles (romhud).  Compared with the picture the VDP holds. With text lines the text box is built from these strings (ROM font, `romtext.py`) instead of the game's buffer.
Raster layout (reg 10 `g_HIntLineReg $FF0FC4`): $8AB8 = map from line 24 to 183, display off below (the game switches it off in the HInt); $8AA0 = text box visible from line 160."""
import sys
import romrender as R, romgfx, romhud as H, romtext

def screen(rom, dump, reference=False, lines=None):
    d = open(dump, 'rb').read(0x10000); room = (d[0xFF1204 & 0xFFFF ^ 1] << 8) | d[0xFF1205 & 0xFFFF ^ 1]
    hint = (d[0xFF0FC4 & 0xFFFF ^ 1] << 8) | d[0xFF0FC5 & 0xFFFF ^ 1]
    g0 = romgfx.room_gfx(rom, room)
    if reference: ref0, cam0, cam2 = R.vdp_window(dump); img = bytearray(R.vdp_window(dump, sprites=True)[0]); win = H.window_vdp(dump, [0, 1, 2] + list(range(20, 28)))
    else:
        cr = R.rom_cram(rom, dump, room)
        g, r, pa, pb, getpal = R.rom_planes(rom, room, anim=R.dump_anim(dump, g0['anim']), pal=cr)
        spr = R.rom_sprites(rom, dump, pal=cr)
        ref0, cam0, cam2 = R.vdp_window(dump)
        px0 = 1184 - (cam2 - cam0 + 160); py0 = (cam0 + cam2) // 2 - 104
        best = None
        for dy in range(-10, 11):
            for dx in range(-6, 7):
                out = R.compose(pa, pb, getpal, px0 + dx, py0 + dy, 320, 64, R.md_to_rgb(0), g['tiles'])      # 64 rows are enough to find the offset
                same = sum(1 for i in range(0, len(out), 3) if ref0[i:i + 3] != b'\x00\x00\x00' and out[i:i + 3] == ref0[i:i + 3])
                if best is None or same > best[0]: best = (same, dx, dy)
        img = bytearray(R.compose(pa, pb, getpal, px0 + best[1], py0 + best[2], 320, 224, R.md_to_rgb(0), g['tiles'], spr))
        if lines:                                                   # text box built from strings (romtext: ROM font), not from the game's buffer
            tb = romtext.textbox_words(); win = H.ram_window(rom, dump, [0, 1, 2] + list(range(20, 28)), cr, words={20 + i: tb[i] for i in range(8)}, textbuf=romtext.text_buffer(rom, lines))
            hint = 0x8AA0
        else: win = H.ram_window(rom, dump, [0, 1, 2] + list(range(20, 28)), cr)
    def put(row, y0):
        for y in range(8):
            for x in range(320): img[((y0 + y) * 320 + x) * 3:((y0 + y) * 320 + x) * 3 + 3] = bytes(win[row][y][x])
    for r in (0, 1, 2): put(r, 8 * r)
    if (hint & 0xFF) == 0xA0:
        for r in range(20, 28): put(r, 8 * r)
    else:
        for y in range(184, 224):
            for x in range(320): img[(y * 320 + x) * 3:(y * 320 + x) * 3 + 3] = b'\x00\x00\x00'
    return img

if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read(); a = screen(rom, sys.argv[2], lines=sys.argv[4:] or None); b = screen(rom, sys.argv[2], reference=True)
    n = sum(1 for i in range(0, len(a), 3) if a[i:i + 3] != b[i:i + 3])
    print('whole picture: %d of %d pixels differ from the VDP picture (%.2f %%)' % (n, 320 * 224, 100.0 * n / (320 * 224)))
    R.png(sys.argv[3], 320, 224, a); R.png(sys.argv[3].replace('.png', '_vdp.png'), 320, 224, b)
