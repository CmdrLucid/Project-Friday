#!/usr/bin/env python3
"""animsurvey.py ROM [OUT_HTML]  -- every animated tile group of the ROM (AnimatedTilesetTable $009E04 / AnimatedTilesetData $009E1C, romgfx.anim_list)
with up to two rooms that use it: the room crop around the animated tiles (marked) played as a GIF, so that light sources (torches, candles, braziers, lava)
can be named by eye (2026-11-02, Lights from the tile origin instead of the pixel colour, user: 'kannst du Lampen, Flammen an sich identifizieren?').
Output: one self-contained HTML page (default ~/Mockups/lichter_survey.html; base64 images, it holds ROM-derived pictures: never commit it) and a
text list on stdout: entry index, tileset, ROM address of frame 0, VRAM tiles, frames, delay, rooms.  Needs Pillow (on the Deck ~/.landstalker_trailer/venv/bin/python)."""
import base64, io, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import romgfx, romroom, romrender
from PIL import Image, ImageDraw

def entries(rom):
    out = []; i = 0
    while rom[0x9E04 + i] != 0xFF:
        e = rom[0x9E1C + 10 * i: 0x9E1C + 10 * i + 10]
        dest, words, delay, frames = struct.unpack('>HHBB', e[:6]); ptr = struct.unpack('>I', e[6:10])[0]
        out.append(dict(idx=i, tileset=rom[0x9E04 + i], dest=dest, words=words, delay=delay, frames=frames, base=struct.unpack('>I', rom[ptr:ptr + 4])[0]))
        i += 1
    return out

def rooms_by_tileset(rom, nrooms=840):
    tab = struct.unpack('>I', rom[0xA0A00:0xA0A04])[0]; by = {}
    for room in range(nrooms):
        e = rom[tab + 8 * room: tab + 8 * room + 8]
        if len(e) < 8: break
        by.setdefault(e[4] & 0x1F, []).append(room)
    return by

def crop_gif(rom, room, ent, size=112, scale=3):
    """GIF of the room crop around the first cells that use the group's tiles (all frames), the cells outlined; None if the room does not show them."""
    try:
        g, r, pa, pb, getpal = romrender.rom_planes(rom, room)
    except Exception:
        return None, 0
    t0 = ent['dest'] // 32; n = max(1, ent['words'] * 2 // 32)
    cells = [c for pl in (pa, pb) for c, t in pl.t.items() if t0 <= (t[0] & 0x7FF) < t0 + n]
    if not cells: return None, 0
    cx = sorted(c[0] for c in cells)[len(cells) // 2]; cy = sorted(c[1] for c in cells)[len(cells) // 2]
    x0 = cx * 8 + 4 - size // 2; y0 = cy * 8 + 4 - size // 2
    groups = g['anim']; k = next((j for j, a in enumerate(groups) if a['dest'] == ent['dest'] and a['base'] == ent['base']), None)
    frames = []
    for f in range(max(1, ent['frames'])):
        tiles = romgfx.apply_anim(romgfx.room_gfx(rom, room)['tiles'], rom, groups, [f if j == k else 0 for j in range(len(groups))]) if k is not None else g['tiles']
        rgb = romrender.compose(pa, pb, getpal, x0, y0, size, size, (0, 0, 0), tiles)
        im = Image.frombytes('RGB', (size, size), bytes(rgb)).resize((size * scale, size * scale), Image.NEAREST)
        d = ImageDraw.Draw(im)
        for (c, rr) in cells:
            X, Y = (c * 8 - x0) * scale, (rr * 8 - y0) * scale
            if -8 * scale < X < size * scale and -8 * scale < Y < size * scale: d.rectangle([X, Y, X + 8 * scale - 1, Y + 8 * scale - 1], outline=(255, 0, 255))
        frames.append(im.convert('P', palette=Image.ADAPTIVE))
    b = io.BytesIO(); ms = max(60, (ent['delay'] + 1) * 17)
    frames[0].save(b, 'GIF', save_all=True, append_images=frames[1:], duration=ms, loop=0)
    return base64.b64encode(b.getvalue()).decode(), len(cells)

def main():
    rom = open(sys.argv[1], 'rb').read(); out = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/Mockups/lichter_survey.html')
    ents = entries(rom); by = rooms_by_tileset(rom)
    html = ["<!doctype html><meta charset=utf-8><title>Animierte Kacheln</title><style>body{background:#222;color:#eee;font:15px sans-serif;padding:16px}"
            "div.e{display:inline-block;vertical-align:top;margin:0 14px 18px 0;background:#2c2c2c;padding:8px;border-radius:6px}img{image-rendering:pixelated;display:block;margin-top:4px}"
            "h3{margin:0 0 4px 0}</style><h2>Alle animierten Kacheln des Spiels</h2><p>Pro Nummer: der Raumausschnitt, in dem die Animation sitzt (magenta umrandet). Bitte sag mir die Nummern der Flammen / Lichtquellen (Fackel, Kerze, Feuerschale, Lava, ...).</p>"]
    for e in ents:
        rooms = by.get(e['tileset'] & 0x1F, []); shown = 0; imgs = []
        for room in rooms:
            if shown >= 2: break
            gif, nc = crop_gif(rom, room, e)
            if gif: imgs.append((room, nc, gif)); shown += 1
        print("entry %2d tileset %2d base $%06X vram tiles %d..%d frames %d delay %d rooms %d (shown %s)" % (e['idx'], e['tileset'], e['base'], e['dest'] // 32, e['dest'] // 32 + e['words'] * 2 // 32 - 1, e['frames'], e['delay'], len(rooms), [r for r, _, _ in imgs]), flush=True)
        html.append("<div class=e><h3>Nr. %d</h3>Tileset %d, %d Bilder, %d Raeume" % (e['idx'], e['tileset'], e['frames'], len(rooms)))
        for room, nc, gif in imgs: html.append("<div>Raum %d</div><img src='data:image/gif;base64,%s'>" % (room, gif))
        if not imgs: html.append("<div>(in keinem Raum gefunden)</div>")
        html.append("</div>")
    open(out, 'w').write("\n".join(html)); print("page:", out)

if __name__ == '__main__':
    main()
