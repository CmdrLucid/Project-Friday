#!/usr/bin/env python3
"""sprint_mock.py [variant]  -- first mock-up of a SPRINT animation for Nigel (idea docs/SPRINT_IDEAS.md, 2026-10-29).

Input: Nigel's walk frames cut from the user's own ROM by nigel_frames.py (~/.landstalker_remake/figures/nigel/a12_f*.png = walk, front view).
Output (LOCAL only, never in git): ~/.landstalker_remake/sprint/ : sheet_<variant>.png (walk row vs sprint row, 6x), sprint_<variant>_f*.png (1x frames),
anim_<variant>.gif (walk and sprint side by side at game speed, 4x).
Method, pixel art only (no new colours, no smoothing): 4 of the 8 walk frames with the widest stride, the upper body sheared row by row
towards the walking direction (lean), a 1 px lift on the push-off frames, a small dust puff behind the back foot in the palette's greys.
Needs Pillow (on the Deck: ~/.landstalker_trailer/venv/bin/python)."""
import os, sys
from PIL import Image

SRC = os.path.expanduser("~/.landstalker_remake/figures/nigel")
OUT = os.path.expanduser("~/.landstalker_remake/sprint")
VARIANTS = {   # lean = px the head moves forward, hip = first row that stays, pick = walk frames used, lift = frames raised by 1 px
    "A": dict(lean=3, hip=30, pick=[0, 1, 4, 5], lift=[1, 3], dust=True),
    "B": dict(lean=2, hip=28, pick=[0, 2, 4, 6], lift=[1, 3], dust=True),
    "C": dict(lean=4, hip=32, pick=[0, 1, 4, 5], lift=[0, 2], dust=False),
    # D: lean in BANDS (whole rows of the head / chest move as blocks, so the drawing stays intact), stride widened on the two stride frames, bigger dust
    "D": dict(bands=[(0, 18, 4), (18, 26, 2)], pick=[0, 1, 4, 5], lift=[1, 3], dust=True, big=True, stride=[0], wide=2),
}
GREY_L, GREY_M = (216, 216, 216, 255), (144, 144, 144, 255)
PAD = 8   # extra canvas around the 32 x 48 frame (lean + dust)


def load(k):
    return Image.open(os.path.join(SRC, "a12_f%d.png" % (4 * k))).convert("RGBA")


def lean(im, px, hip):
    """front view walks towards screen down-left: rows above `hip` move left, the head by `px`, linear down to 0 at the hip"""
    w, h = im.size
    out = Image.new("RGBA", (w + 2 * PAD, h + 2 * PAD), (0, 0, 0, 0))
    for y in range(h):
        dx = -round(px * (hip - y) / hip) if y < hip else 0
        out.paste(im.crop((0, y, w, y + 1)), (PAD + dx, PAD + y))
    return out


def lean_bands(im, bands):
    """rows y0..y1-1 move left by dx as one block (the drawing inside a band stays intact)"""
    w, h = im.size
    out = Image.new("RGBA", (w + 2 * PAD, h + 2 * PAD), (0, 0, 0, 0))
    for y in range(h):
        dx = next((-d for y0, y1, d in bands if y0 <= y < y1), 0)
        out.paste(im.crop((0, y, w, y + 1)), (PAD + dx, PAD + y), im.crop((0, y, w, y + 1)))
    return out


def widen(im, n):
    """longer stride: below the knees the left half moves n px left, the right half n px right (split at the middle of the legs)"""
    w, h = im.size; px = im.load()
    rows = [y for y in range(h) if any(px[x, y][3] for x in range(w))]
    bot = rows[-1]; top = bot - 9
    xs = [x for y in range(top, bot + 1) for x in range(w) if px[x, y][3]]
    mid = (min(xs) + max(xs)) // 2
    out = im.copy(); o = out.load()
    for y in range(top, bot + 1):
        for x in range(w): o[x, y] = (0, 0, 0, 0)
        for x in range(w):
            if px[x, y][3]:
                nx = x - n if x < mid else x + n
                if 0 <= nx < w: o[nx, y] = px[x, y]
        # close the gap at the middle with the neighbour colour so the legs stay connected at the top rows
        if y < top + 3:
            for x in range(mid - n, mid + n):
                if not o[x, y][3] and px[mid, y][3]: o[x, y] = px[mid, y]
    return out


def feet(im):
    """lowest opaque row and the x range of the rearmost foot (the right-most opaque pixels of the bottom rows: front view runs left)"""
    w, h = im.size; px = im.load()
    rows = [y for y in range(h) if any(px[x, y][3] for x in range(w))]
    bot = rows[-1]
    xs = [x for y in range(bot - 3, bot + 1) for x in range(w) if px[x, y][3]]
    return bot, max(xs)


def dust(im, phase, big=False):
    """a small puff right behind the back foot, two sizes alternating (big: a 7 px cloud plus a trailing speck)"""
    px = im.load(); bot, xr = feet(im)
    if big:
        shape = ([(1, 0), (2, 0), (3, 0), (4, 0), (0, -1), (1, -1), (2, -1), (3, -1), (4, -1), (5, -1), (1, -2), (2, -2), (3, -2), (4, -2), (2, -3), (3, -3), (7, -1), (8, -1), (8, -2)]
                 if phase == 0 else [(2, 0), (3, 0), (4, 0), (5, 0), (2, -1), (3, -1), (4, -1), (5, -1), (6, -1), (3, -2), (4, -2), (5, -2), (9, -1), (10, -2)])
    else:
      shape = [(1, 0), (2, 0), (0, -1), (1, -1), (2, -1), (3, -1), (1, -2), (2, -2)] if phase == 0 else [(1, 0), (2, 0), (3, 0), (1, -1), (2, -1)]
    for dx, dy in shape:
        x, y = xr + 2 + dx, bot + dy
        if 0 <= x < im.size[0] and 0 <= y < im.size[1] and not px[x, y][3]:
            px[x, y] = GREY_L if dy < 0 else GREY_M
    return im


def make(v):
    p = VARIANTS[v]; frames = []
    for i, k in enumerate(p["pick"]):
        src = load(k)
        if i in p.get("stride", []): src = widen(src, p["wide"])
        f = lean_bands(src, p["bands"]) if "bands" in p else lean(src, p["lean"], p["hip"])
        if i in p["lift"]:
            g = Image.new("RGBA", f.size, (0, 0, 0, 0)); g.paste(f, (0, -1)); f = g
        if p["dust"] and i in (0, 2):
            f = dust(f, (i // 2) % 2, p.get("big", False))
        frames.append(f)
    return frames


def main():
    v = sys.argv[1] if len(sys.argv) > 1 else "A"
    os.makedirs(OUT, exist_ok=True)
    walk = [load(k) for k in range(8)]
    sprint = make(v)
    for i, f in enumerate(sprint):
        f.save(os.path.join(OUT, "sprint_%s_f%d.png" % (v, i)))
    S, BG = 6, (70, 100, 60, 255)
    cw, ch = 32 + 2 * PAD, 48 + 2 * PAD
    sheet = Image.new("RGBA", (cw * 8 * S, ch * 2 * S), BG)
    for k, f in enumerate(walk):
        c = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); c.paste(f, (PAD, PAD))
        sheet.alpha_composite(c.resize((cw * S, ch * S), Image.NEAREST), (k * cw * S, 0))
    for k, f in enumerate(sprint):
        sheet.alpha_composite(f.resize((cw * S, ch * S), Image.NEAREST), (k * cw * S, ch * S))
    sheet.save(os.path.join(OUT, "sheet_%s.png" % v))
    # animation: walk (8 frames, 6 game frames each) next to sprint (4 frames, 4 game frames each), 4x, 60 Hz game frames -> GIF in 10 ms units
    A = 4; gif = []
    for t in range(0, 48, 2):
        c = Image.new("RGBA", (cw * 2 * A, ch * A), BG)
        wf = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); wf.paste(walk[(t // 6) % 8], (PAD, PAD))
        c.alpha_composite(wf.resize((cw * A, ch * A), Image.NEAREST), (0, 0))
        c.alpha_composite(sprint[(t // 4) % 4].resize((cw * A, ch * A), Image.NEAREST), (cw * A, 0))
        gif.append(c.convert("RGB"))
    gif[0].save(os.path.join(OUT, "anim_%s.gif" % v), save_all=True, append_images=gif[1:], duration=33, loop=0)
    print("->", os.path.join(OUT, "sheet_%s.png" % v), os.path.join(OUT, "anim_%s.gif" % v))


if __name__ == "__main__":
    main()
