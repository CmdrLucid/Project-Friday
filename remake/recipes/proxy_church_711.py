#!/usr/bin/env python3
"""LIGHT SHAPE: the VERLA church, rooms 711 / 712 (one map $0A669E, tileset 0 = the Mercator tileset). User 2026-11-20: 'die Kirche in Verla sollte
aehnlich sein wie die in Mercator / Ryuma'. It is not only similar, it is the SAME drawing: the church blocks of Mercator 632 (hall with hip roof +
flat top, cross wings, porch with the open entrance) reappear in Verla shifted by 7 cells east, 28 cells north and 6 steps up (picture offset
U +560, V -264: plane A of the church identical where Mercator's yellow house in front does not cover it; height map: the church's collision
block x 22..30 y 22..29 at ground 112 = Mercator's x 15..23 y 50..57 at ground 16). Mercator's yellow house is NOT in Verla (its own model there).
So this recipe copies the measured Mercator model (landstalker/data/proxies/church_632.obj, remake/recipes/proxy_church_632.py, user OK 2026-11-20)
moved by (+112, -448, +96).  Pure Python, no ROM.  Run: python3 remake/recipes/proxy_church_711.py -> landstalker/data/proxies/church_711.obj"""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); PROX = os.path.join(HERE, "..", "..", "landstalker", "data", "proxies")
DX, DY, DZ = 112.0, -448.0, 96.0
src = os.path.join(PROX, "church_632.obj"); dst = os.path.join(PROX, "church_711.obj"); xs, ys = [], []
with open(dst, "w") as fo:
    fo.write("# light proxy: Verla church = the Mercator church model moved by (+112, -448, +96) (remake/recipes/proxy_church_711.py). GAME coordinates x east, y south, z up.\n")
    for l in open(src):
        if l.startswith("v "):
            x, y, z = map(float, l.split()[1:4]); x += DX; y += DY; z += DZ; xs.append(x); ys.append(y)
            fo.write("v %g %g %g\n" % (round(x, 3), round(y, 3), round(z, 3)))
        elif l.startswith("f "): fo.write(l)
print("proxy_church_711: %d vertices -> %s; cells x %d..%d y %d..%d" % (len(xs), dst, int(min(xs)) // 16, int(max(xs)) // 16, int(min(ys)) // 16, int(max(ys)) // 16))
