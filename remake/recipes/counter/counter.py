#!/usr/bin/env python3
"""counter.py - the SHOP COUNTER of the Mercator special shop (rooms 695 / 696 / 697, tileset 2) as a near-final 3D model = light shape
(memory feedback-precise-light-shapes). The game's collision (walkable height 1 = 16 units) already sits on the drawing (overlay checked):
  top    = a thick plank top z 13.6 .. 16 with rounded edges over the whole footprint;
  body   = a core 0.8 in from the top's edge + vertical BOARDS (pitch 8, 7 wide, 0.5 proud) on every side not at a wall;
  cloth  = (island only) a small cloth lying on the top at the back end (22 x 22, measured on the drawing; first read as glass, user: a cloth).
  counter_parts(x0, x1, y0, y1, walls, cloth) -> list of (vertices, faces) closed solids in GAME coordinates; walls: sides at a wall 'n' / 's' / 'w' / 'e'
  python3 counter.py OUT.obj x0 x1 y0 y1 [walls] [cloth x0 x1 y0 y1] [--light]"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
from furniture import rbox

TOP0, TOP1, INSET, PITCH, BOARD, PROUD = 13.6, 16.0, 0.8, 8.0, 7.0, 0.5

def boards(x0, x1, y0, y1, side):
    out = []
    if side in ('n', 's'):
        y = y0 + INSET if side == 'n' else y1 - INSET; ya, yb = (y - PROUD, y) if side == 'n' else (y, y + PROUD)
        n = max(1, int(round((x1 - x0 - 2 * INSET) / PITCH))); p = (x1 - x0 - 2 * INSET) / n
        for k in range(n): a = x0 + INSET + k * p + (p - BOARD * p / PITCH) / 2; out.append(rbox(a, a + BOARD * p / PITCH, ya, yb, 0.0, TOP0 - 0.2, 0.2, n=1, flat_bottom=True))
    else:
        x = x0 + INSET if side == 'w' else x1 - INSET; xa, xb = (x - PROUD, x) if side == 'w' else (x, x + PROUD)
        n = max(1, int(round((y1 - y0 - 2 * INSET) / PITCH))); p = (y1 - y0 - 2 * INSET) / n
        for k in range(n): a = y0 + INSET + k * p + (p - BOARD * p / PITCH) / 2; out.append(rbox(xa, xb, a, a + BOARD * p / PITCH, 0.0, TOP0 - 0.2, 0.2, n=1, flat_bottom=True))
    return out

def counter_parts(x0, x1, y0, y1, walls="", cloth=None, light=False):
    """light=True: the LIGHT variant without the sub-pixel details (the light keeps depths in 1/8 units: a 0.1 cloth and 0.5 board relief toggled
    pixel by pixel = dotted dark lines, 2026-11-12): the core flush with the top's edge (= the drawn front), no boards, no cloth"""
    if light: return [rbox(x0, x1, y0, y1, 0.0, TOP0 + 0.1, 0.3, n=1, flat_bottom=True), rbox(x0, x1, y0, y1, TOP0, TOP1, 0.8, n=2)]   # flush with the drawn front (an inset core let the bottom pixel row alternate floor / body)
    P = [rbox(x0 + INSET, x1 - INSET, y0 + INSET, y1 - INSET, 0.0, TOP0 + 0.1, 0.3, n=1, flat_bottom=True)]   # body core
    for s in "nswe":
        if s not in walls: P += boards(x0, x1, y0, y1, s)
    P.append(rbox(x0, x1, y0, y1, TOP0, TOP1, 0.8, n=2))
    if cloth:   # a small cloth lying on the top (user 2026-11-12: 'da liegt eigentlich nur quasi ein Deckchen auf der Ladentheke im Sprite'), size measured on the drawing
        cx0, cx1, cy0, cy1 = cloth
        P.append(rbox(cx0, cx1, cy0, cy1, TOP1 - 0.05, TOP1 + 0.12, 0.06, n=1, flat_bottom=True))
    return P

def counter_light2(x0, x1, y0, y1, walls="", cloth=None, phase=0.0):
    """LIGHT variant v2 (2026-11-13, user rule: every light shape a real model, reliefs >= 1 unit or flush): sharp-edged plank top 13 .. 16 flush with
    the drawn front, the boards flush with it too, separated by GROOVES 1 wide / 1 deep on the drawn dark lines (pitch 8, phase measured), a core 1 behind
    the boards; the cloth 1 unit thick.  No sub-unit relief (0a413: 0.1 .. 0.8 details gave dotted lines)."""
    def box(a, b, c, d, e, f): return rbox(a, b, c, d, e, f, 0.0001, n=1, flat_bottom=True)
    P = [box(x0, x1, y0, y1, 13.0, 16.0), box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, 0.0, 13.0)]
    for side in "nswe":
        if side in walls: continue
        if side in "ns":
            ya, yb = (y0, y0 + 1) if side == "n" else (y1 - 1, y1); g = math.floor((x0 - phase) / PITCH) * PITCH + phase
            edges = [x0] + [v for v in [g + PITCH * k for k in range(1, 64)] if x0 + 0.5 < v < x1 - 0.5] + [x1]
            for a, b in zip(edges, edges[1:]): P.append(box(a + (0.5 if a > x0 else 0), b - (0.5 if b < x1 else 0), ya, yb, 0.0, 13.0))
        else:
            xa, xb = (x0, x0 + 1) if side == "w" else (x1 - 1, x1); g = math.floor((y0 - phase) / PITCH) * PITCH + phase
            edges = [y0] + [v for v in [g + PITCH * k for k in range(1, 64)] if y0 + 0.5 < v < y1 - 0.5] + [y1]
            for a, b in zip(edges, edges[1:]): P.append(box(xa, xb, a + (0.5 if a > y0 else 0), b - (0.5 if b < y1 else 0), 0.0, 13.0))
    if cloth: cx0, cx1, cy0, cy1 = cloth; P.append(box(cx0, cx1, cy0, cy1, 16.0, 17.0))
    return P

def write_obj(path, parts, title):
    with open(path, "w") as fo:
        fo.write("# %s (remake/recipes/counter/counter.py). GAME coordinates x east, y south, z up, world units.\n" % title)
        fo.write("# our own geometry fitted to the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        b = 0
        for V, F in parts:
            for v in V: fo.write("v %.3f %.3f %.3f\n" % v)
            for f in F: fo.write("f " + " ".join(str(i + 1 + b) for i in f) + "\n")
            b += len(V)
    print("%s: %d parts" % (path, len(parts)))

if __name__ == "__main__":
    a = sys.argv; x0, x1, y0, y1 = map(float, a[2:6]); walls = a[6] if len(a) > 6 and a[6] != "-" else ""
    light = "--light" in a; a = [t for t in a if t != "--light"]
    cloth = tuple(map(float, a[7:11])) if len(a) > 10 else None
    write_obj(a[1], counter_parts(x0, x1, y0, y1, walls, cloth, light), "shop counter" + (" (light variant)" if light else ""))
