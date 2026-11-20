#!/usr/bin/env python3
"""find_openings.py ROM ROOM SCENE_fit.json [--png OUT.png] [--dump]
Finds the WINDOWS and DOORS of town houses on the drawn picture (user's own ROM; prints only, the PNG is local). Needs numpy (hdvenv python).
The house walls are drawn from 16 unit wide wall tiles (remake/MODELS.md 'Town house'): every slot of 16 units along a visible wall (+x wall x = x1,
+y wall y = y1 of every wing) and every storey (48 high) is plain wall, a window or a door. Per slot the picture pixels of the slot are sampled on
the wall plane (both planes composed: doors are partly in layer B) where this wall is the nearest model surface (scene from fit_house.py: other
houses / wings in front leave the slot out). Features: black frame pixels and glass greys in the window band (z 37..55 above the storey floor),
black and door wood in the door band (z 18..36). Prints one line per slot: wing, wall, slot range, storey, kind, features."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "tools"))
import romrender, fit_house

def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def main():
    a = [s for i, s in enumerate(sys.argv[1:], 1) if not s.startswith('--') and not (i > 1 and sys.argv[i - 1].startswith('--'))]
    rom = open(a[0], 'rb').read(); room = int(a[1]); sc = json.load(open(a[2]))
    z0 = sc.get('z0', 16); wings = sc['wings']; ties = sc['ties']
    wp = lambda w: list(map(float, w['foot'])) + [float(w.get('z0', z0))] + list(map(float, ties[w['tie']]))
    g, r, pa, pb, getpal = romrender.rom_planes(rom, room)
    U0, V0, Wd, Hd = 0, 0, 2400, 1400
    F = romrender.compose(pa, pb, getpal, U0, V0, Wd, Hd, romrender.md_to_rgb(0), g['tiles'])
    pic = np.frombuffer(bytes(F), np.uint8).reshape(Hd, Wd, 3)
    def frontdepth(U, V):   # nearest model surface depth (x along the view ray) over all wings at picture points
        d = np.full(U.shape, -1e9)
        for w in wings:
            c, dd = fit_house.render(wp(w), U, V); d = np.maximum(d, np.where(c != 0, dd, -1e9))
        return d
    out = []
    for w in wings:
        x0, y0, x1, y1, zz0, ze, zt, ii = wp(w)
        storeys = int(round((ze - zz0) / 48))
        for wall in ('y', 'x'):
            lo, hi = (x0, x1) if wall == 'y' else (y0, y1)
            for s0 in np.arange(lo, hi - 15.9, 16):
                for st in range(storeys):
                    fz = zz0 + 48 * st
                    A, Z = np.meshgrid(np.arange(s0 + 0.5, s0 + 16, 1.0), np.arange(fz + 0.5, fz + 48, 1.0))
                    X, Y = (A, np.full(A.shape, y1)) if wall == 'y' else (np.full(A.shape, x1), A)
                    U = X - Y + 1184; V = (X + Y) / 2 - Z
                    vis = np.abs(frontdepth(U, V) - X) < 0.75
                    Ui = np.clip(U.astype(int), 0, Wd - 1); Vi = np.clip(V.astype(int), 0, Hd - 1); P = pic[Vi, Ui].astype(int)
                    blk = (P.sum(-1) == 0); glass = np.all(P == 216, -1) | np.all(P == 144, -1)
                    rz = Z - fz; ra = A - s0
                    wb = vis & (rz >= 21) & (rz < 39) & (ra >= 3) & (ra < 13); db = vis & (rz >= 2) & (rz < 20) & (ra >= 2) & (ra < 12)
                    if vis.mean() < 0.5: kind = 'hidden'
                    else:
                        g_ = glass[wb].mean() if wb.any() else 0; kw = blk[wb].mean() if wb.any() else 0; kd = blk[db].mean() if db.any() else 0
                        kind = 'door' if kd > 0.12 and g_ < 0.3 else 'window' if g_ > 0.15 and kw > 0.08 else 'wall'
                    feats = (vis.mean(), glass[wb].mean() if wb.any() else 0, blk[wb].mean() if wb.any() else 0, blk[db].mean() if db.any() else 0)
                    box = None
                    if kind in ('window', 'door'):   # the drawn FRAME = bounding box of the black frame columns / rows (game units on the wall plane)
                        band = vis & ((rz >= 22) & (rz < 39) if kind == 'window' else (rz >= 2) & (rz < 46))
                        K = blk & band; cols = np.where(K.sum(0) >= 6)[0]
                        if len(cols):
                            a_lo, a_hi = s0 + cols.min(), s0 + cols.max() + 1
                            sub = K[:, cols.min():cols.max() + 1]; rows = np.where(sub.sum(1) >= 2)[0]
                            if not len(rows): rows = np.where(sub.sum(1) >= 1)[0]   # (Verla E, 2026-11-20: a thin frame left no row with 2 black pixels)
                            box = (float(a_lo), float(a_hi), float(fz + rows.min()), float(fz + rows.max() + 1)) if len(rows) else None
                            if kind == "window" and box and box[3] - fz < 36: kind = "sign"   # a framed board low on the wall (shop sign), drawn flat: no opening
                    out.append((w['name'], wall, s0, st, kind, box) + feats)
                    if kind in ('window', 'door') or '--dump' in sys.argv:
                        print('%-5s +%s wall slot %5.0f..%5.0f storey %d: %-6s frame %s (visible %.2f glass %.2f black %.2f / door band black %.2f)' % ((w['name'], wall, s0, s0 + 16, st, kind, box and '%g..%g z %g..%g' % box) + feats))
    json.dump([o[:6] for o in out if o[4] in ('window', 'door')], open(a[2].replace('.json', '_openings.json'), 'w'))

if __name__ == '__main__':
    main()
