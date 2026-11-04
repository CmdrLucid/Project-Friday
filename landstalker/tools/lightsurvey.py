#!/usr/bin/env python3
"""lightsurvey.py ROM [OUT_HTML]  -- candidate STATIC light tiles (painted torches, sconces, candles that are not animated, e.g. the wall torches of the
waterfall shrine room 177, user report 2026-11-03): for every tileset one or two rooms are drawn from ROM data (romrender) and every 8 x 8 plane tile
with at least 5 bright flame-coloured pixels (red >= 200, green >= 120, blue <= 110, red - blue >= 120) is a candidate; candidates are grouped per
(tileset, tile index) and shown as a room crop (the tile outlined) so that the real light sources can be named by eye.  The confirmed list goes into
tools/patch_lights.py (lk_lt_static).  Output: one self-contained HTML page (default ~/Mockups/lichter_statisch.html, ROM-derived pictures: never commit)
and a text list on stdout.  Needs Pillow (on the Deck ~/.landstalker_trailer/venv/bin/python)."""
import base64, io, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import romgfx, romrender, animsurvey
from PIL import Image, ImageDraw

def flame_px(rgb):
    r, g, b = rgb
    return r >= 200 and g >= 120 and b <= 110 and r - b >= 120

def main():
    rom = open(sys.argv[1], 'rb').read(); out = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/Mockups/lichter_statisch.html')
    by = animsurvey.rooms_by_tileset(rom); cands = {}
    for ts in sorted(by):
        for room in by[ts][:3]:
            try:
                g, r, pa, pb, getpal = romrender.rom_planes(rom, room)
            except Exception:
                continue
            tp = romrender.tile_cache(g['tiles']); anim = set()
            for a in g['anim']:
                for t in range(a['dest'] // 32, a['dest'] // 32 + a['words'] * 2 // 32): anim.add(t)
            for pl in (pa, pb):
                for (c, rr), t in pl.t.items():
                    ti = t[0] & 0x7FF
                    if ti in anim: continue
                    px = tp(t[0], t[3], t[4]); n = 0
                    for y in range(8):
                        for x in range(8):
                            i = px[y][x]
                            if i and flame_px(getpal(t[1], i)): n += 1
                    if n >= 5:
                        k = (ts, ti); e = cands.setdefault(k, dict(n=0, room=room, cell=(c, rr), pix=n))
                        e['n'] += 1
    html = ["<!doctype html><meta charset=utf-8><title>Statische Lichtkacheln</title><style>body{background:#222;color:#eee;font:15px sans-serif;padding:16px}"
            "div.e{display:inline-block;vertical-align:top;margin:0 12px 16px 0;background:#2c2c2c;padding:8px;border-radius:6px}img{image-rendering:pixelated;display:block;margin-top:4px}</style>"
            "<h2>Feste (nicht animierte) Kacheln mit Flammenfarben</h2><p>Magenta umrandet = die Kachel. Bitte sag mir die Buchstaben der echten Lichtquellen (Fackel, Kerze ...); Gold, Muenzen, Blumen usw. gehoeren nicht dazu.</p>"]
    # one entry per tileset + neighbouring tile ids (a torch is 2..4 tiles)
    groups = []
    for (ts, ti), e in sorted(cands.items()):
        if groups and groups[-1]['ts'] == ts and ti - groups[-1]['tiles'][-1] <= 3: groups[-1]['tiles'].append(ti); groups[-1]['n'] += e['n']; continue
        groups.append(dict(ts=ts, tiles=[ti], n=e['n'], room=e['room'], cell=e['cell']))
    for gi, gr in enumerate(groups):
        name = chr(65 + gi % 26) + (str(gi // 26) if gi >= 26 else '')
        g, r, pa, pb, getpal = romrender.rom_planes(rom, gr['room'])
        c, rr = gr['cell']; S = 72; x0, y0 = c * 8 + 4 - S // 2, rr * 8 + 4 - S // 2
        im = Image.frombytes('RGB', (S, S), bytes(romrender.compose(pa, pb, getpal, x0, y0, S, S, (0, 0, 0), g['tiles']))).resize((S * 3, S * 3), Image.NEAREST)
        d = ImageDraw.Draw(im)
        for pl in (pa, pb):
            for (cc, r2), t in pl.t.items():
                if (t[0] & 0x7FF) in gr['tiles']:
                    X, Y = (cc * 8 - x0) * 3, (r2 * 8 - y0) * 3
                    if -24 < X < S * 3 and -24 < Y < S * 3: d.rectangle([X, Y, X + 23, Y + 23], outline=(255, 0, 255))
        b = io.BytesIO(); im.save(b, 'PNG')
        print("%s tileset %2d tiles %s uses %d (room %d)" % (name, gr['ts'], gr['tiles'], gr['n'], gr['room']), flush=True)
        html.append("<div class=e><b>%s</b> Tileset %d, Kacheln %s<br>Raum %d<img src='data:image/png;base64,%s'></div>" % (name, gr['ts'], ",".join(map(str, gr['tiles'])), gr['room'], base64.b64encode(b.getvalue()).decode()))
    open(out, 'w').write("\n".join(html)); print("page:", out)

if __name__ == '__main__':
    main()
