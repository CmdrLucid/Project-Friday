#!/usr/bin/env python3
"""fit_house.py ROM ROOM SCENE.json [--png OUT.png] [--fixed]   (scene format: see main())
MEASURES one TOWN HOUSE (box walls + hip roof with a flat top, the Mercator / Ryuma house type) on the drawn picture of the user's own ROM.
Needs numpy (run with ~/Project-Friday-Test/hdvenv/bin/python). Writes nothing but the optional overlay PNG (local, ROM-derived: never into git).

Model (game units, x east, y south, z up): walls x0..x1 / y0..y1 from the ground z0 up to the eave ze; four roof slopes from the eave edge up to a
flat top at zt that starts i units in from the walls (i = zt - ze is a 45 deg roof). Every model pixel is found by casting the view ray
(1, 1, 1) through the picture pixel (U = x - y + 1184, V = (x + y) / 2 - z) and taking the nearest face (wall / roof / top).
Picture classes come from layer A (the objects plane): roof = red / orange, top = light greys, black outline and dark dots = don't care.
Score = matching pixels - 3 x model pixels on empty picture - mismatched classes - 0.5 x house pixels the model misses (inside the window).
Coordinate descent over (ze, zt, i) and, with --free foot, the footprint (start = the given cells' walls; walls are usually on cell lines).
--mask: houses in FRONT (already measured): their pixels are left out of the score (they hide parts of this one).
Prints the best parameters, the share of the model's pixels that match and the pixels outside the drawing."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "tools"))
import romrender, rom_picture

def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

ROOF = {(144, 0, 0), (252, 108, 0), (180, 36, 0), (216, 72, 0)}
TOP = {(144, 144, 144), (216, 216, 216)}
DONT = {(0, 0, 0), (72, 72, 36)}
if os.environ.get("FIT_PALETTE") == "destel":   # Destel log houses (room 726, 2026-11-20): orange thatch (its light highlights are thatch too), no flat top
    ROOF = {(216, 108, 36), (144, 72, 0), (252, 180, 0), (216, 216, 216)}; TOP = set()
E, W, R, T, D = 0, 1, 2, 3, 4

def faces(x0, y0, x1, y1, z0, ze, zt, i):
    """visible faces as (class, polygon) in game coordinates (back walls never face the camera)"""
    i = min(i, (x1 - x0) / 2 - 0.5, (y1 - y0) / 2 - 0.5)
    a, b, c, d = (x0 + i, y0 + i, zt), (x1 - i, y0 + i, zt), (x1 - i, y1 - i, zt), (x0 + i, y1 - i, zt)
    return [(W, [(x1, y0, z0), (x1, y1, z0), (x1, y1, ze), (x1, y0, ze)]),
            (W, [(x0, y1, z0), (x1, y1, z0), (x1, y1, ze), (x0, y1, ze)]),
            (R, [(x1, y0, ze), (x1, y1, ze), c, b]), (R, [(x0, y1, ze), (x1, y1, ze), c, d]),
            (R, [(x0, y0, ze), (x1, y0, ze), b, a]), (R, [(x0, y0, ze), (x0, y1, ze), d, a]),
            (T, [a, b, c, d])]

def render(params, U, V):
    """class map + depth for the pixel grids U, V"""
    cls = np.zeros(U.shape, np.int8); dep = np.full(U.shape, -1e9)
    A = U - 1184.0
    for k, poly in faces(*params):
        P = np.array(poly, float); n = np.cross(P[1] - P[0], P[2] - P[0])
        if np.linalg.norm(n) < 1e-9: continue
        s = n[0] + n[1] + n[2]
        if abs(s) < 1e-9: continue                      # face seen edge on
        cst = n @ P[0]
        x = (cst + n[1] * A + n[2] * (A / 2 + V)) / s   # ray point (x, x - A, x - A / 2 - V)
        y = x - A; z = x - A / 2 - V
        ax = int(np.argmax(np.abs(n))); u_, v_ = [q for q in range(3) if q != ax]
        Q = np.stack([x, y, z]); inside = np.ones(U.shape, bool); sign = None
        for j in range(len(P)):
            p, q = P[j], P[(j + 1) % len(P)]
            cr = (q[u_] - p[u_]) * (Q[v_] - p[v_]) - (q[v_] - p[v_]) * (Q[u_] - p[u_])
            if sign is None: sign = np.sign((P[(j + 2) % len(P)][v_] - p[v_]) * (q[u_] - p[u_]) - (P[(j + 2) % len(P)][u_] - p[u_]) * (q[v_] - p[v_]))
            inside &= cr * sign >= -1e-6
        hit = inside & (x > dep)
        dep[hit] = x[hit]; cls[hit] = k
    return cls, dep

def window(params, pad=8):
    x0, y0, x1, y1, z0, ze, zt, i = params
    us = [x - y + 1184 for x in (x0, x1) for y in (y0, y1)]
    vs = [(x + y) / 2 - z for x in (x0, x1) for y in (y0, y1) for z in (z0, zt)]
    return int(min(us)) - pad, int(min(vs)) - pad, int(max(us)) + pad, int(max(vs)) + pad

def load_pic(rom, room, U0, V0, U1, V1):
    g, r, pa, pb, getpal = romrender.rom_planes(rom, room)
    Wd, Hd = U1 - U0, V1 - V0
    Ab = rom_picture.layer_a(pa, getpal, g['tiles'], U0, V0, Wd, Hd)
    pic = np.zeros((Hd, Wd), np.int8); rgb = np.zeros((Hd, Wd, 3), np.uint8)
    for yy in range(Hd):
        for xx in range(Wd):
            o = (yy * Wd + xx) * 4
            if not Ab[o + 3]: continue
            c = tuple(Ab[o:o + 3]); rgb[yy, xx] = c
            pic[yy, xx] = R if c in ROOF else T if c in TOP else D if c in DONT else W
    return pic, rgb

def main():
    """scene mode: fit_house.py ROM ROOM SCENE.json [--png OUT.png] [--fixed]
    SCENE = {"z0": 16, "wings": [{"name": "h6", "foot": [x0, y0, x1, y1], "tie": "h6", "free": "foot"}, ...],
             "ties": {"h6": [ze, zt, i], ...}}: wings with the same tie share eave / top / inset; the union of all wings is rendered
    (the nearest front face of every convex wing = where the view ray enters the union), so houses hide each other correctly."""
    import json
    a = [s for i, s in enumerate(sys.argv[1:], 1) if not s.startswith('--') and not (i > 1 and sys.argv[i - 1].startswith('--'))]
    rom = open(a[0], 'rb').read(); room = int(a[1]); sc = json.load(open(a[2]))
    z0 = sc.get('z0', 16); wings = sc['wings']; ties = {k: list(map(float, v)) for k, v in sc['ties'].items()}
    def wp(w): t = ties[w['tie']]; return list(map(float, w['foot'])) + [float(w.get('z0', z0))] + t
    allw = [window(wp(w), 10) for w in wings]
    U0, V0 = min(q[0] for q in allw) - 20, min(q[1] for q in allw) - 20; U1, V1 = max(q[2] for q in allw) + 20, max(q[3] for q in allw) + 20
    pic, rgb = load_pic(rom, room, U0, V0, U1, V1)
    V, U = np.mgrid[V0:V1, U0:U1].astype(float); U += 0.5; V += 0.5
    cache = {}
    def wrender(k):
        q = tuple(wp(wings[k]))
        if cache.get(k, (None,))[0] != q:
            x0_, y0_, x1_, y1_ = window(list(q), 2); sub = (slice(max(0, y0_ - V0), max(0, y1_ - V0)), slice(max(0, x0_ - U0), max(0, x1_ - U0)))
            c, d = render(list(q), U[sub], V[sub]); cache[k] = (q, sub, c, d)
        return cache[k]
    def compose():
        cls = np.zeros(U.shape, np.int8); dep = np.full(U.shape, -1e9)
        for k in range(len(wings)):
            q, sub, c, d = wrender(k); cs, ds = cls[sub], dep[sub]
            hit = (c != E) & (d > ds); cs[hit] = c[hit]; ds[hit] = d[hit]
        return cls
    def score():
        m = compose(); pc = pic
        good = ((m != E) & ((pc == m) | (pc == D) | ((m == W) & (pc == T)))).sum()
        out = ((m != E) & (pc == E)).sum()
        bad = ((m != E) & (pc != E) & (pc != m) & (pc != D) & ~((m == W) & (pc == T))).sum()
        miss = ((m == E) & (pc != E)).sum()
        return good - 3 * out - bad - 0.5 * miss, good, out, bad, (m != E).sum()
    best = score()
    if '--fixed' not in sys.argv:
        for step in (4, 2, 1, 0.5):
            moved = True
            while moved:
                moved = False
                knobs = [('t', t, j) for t in ties for j in range(3)] + [('w', k, j) for k, w in enumerate(wings) if w.get('free') == 'foot' for j in range(4)]
                for kind, key, j in knobs:
                    for dlt in (step, -step):
                        tgt = ties[key] if kind == 't' else wings[key]['foot']
                        old = tgt[j]; tgt[j] = old + dlt
                        if kind == 't' and not (tgt[1] > tgt[0] and tgt[2] >= 0): tgt[j] = old; continue
                        s_ = score()
                        if s_[0] > best[0]: best, moved = s_, True
                        else: tgt[j] = old
        cache.clear()
    for t, v in ties.items():
        print('tie %-6s eave %.1f top %.1f inset %.1f (slope %.0f deg)' % (t, v[0], v[1], v[2], np.degrees(np.arctan2(v[1] - v[0], max(v[2], 1e-6)))))
    for w in wings: print('wing %-6s x %g..%g y %g..%g (%s)' % (w['name'], w['foot'][0], w['foot'][2], w['foot'][1], w['foot'][3], w['tie']))
    print('score %.1f: model pixels %d, matching %d (%.1f %%), outside the drawing %d, other class %d' % (best[0], best[4], best[1], 100.0 * best[1] / max(best[4], 1), best[2], best[3]))
    json.dump(dict(sc, ties=ties), open(a[2].replace('.json', '_fit.json'), 'w'), indent=1)
    if '--png' in sys.argv:
        mc = compose(); img = rgb.copy() // 2 + 64
        col = {W: (255, 255, 0), R: (255, 0, 0), T: (0, 255, 255)}
        edge = np.zeros(mc.shape, bool); edge[1:, :] |= mc[1:, :] != mc[:-1, :]; edge[:, 1:] |= mc[:, 1:] != mc[:, :-1]
        for k, cc in col.items(): img[edge & (mc == k)] = cc
        img[(mc != E) & (pic == E)] = (255, 0, 255)
        from PIL import Image
        Image.fromarray(img).resize(((U1 - U0) * 2, (V1 - V0) * 2), Image.NEAREST).save(opt('--png', ''))

if __name__ == '__main__':
    main()
