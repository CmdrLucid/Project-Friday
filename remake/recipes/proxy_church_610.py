#!/usr/bin/env python3
"""LIGHT SHAPE: the RYUMA church, rooms 610 / 611 (one map $0A6F20). Like Verla (proxy_church_711.py) it is the SAME drawing as the Mercator church
(remake/recipes/proxy_church_632.py, user OK 2026-11-20), measured 2026-11-24:
  * picture: plane A of the Mercator church window (U 500..767, V 456..634) found in room 610 at U +288, V -160 (71 % of the plane A pixels equal;
    the rest = the hall's left end, which Mercator's yellow house covers, plus flowers / ground behind); composed picture: hall roof, porch,
    cross wings, entrance pixel-equal;
  * height map: the church's collision block (Mercator x 15..23 y 50..57, 72 cells, blocked height 4) = Ryuma x 16..24 y 33..40, height 6:
    all 72 cells equal -> move (+16, -272, +32), ground 48.
ONE MEASURED DIFFERENCE ('exact over identical', user rule): Mercator's hall -x wall x 238 was derived from the symmetric hip inset because the yellow
house hides that corner; in Ryuma the corner is visible: the front wall's outline column is U 785..786 on the plane y 650 (Ryuma) -> wall x 251.5
= 235.5 in Mercator coordinates (2.5 further west). The flat roof top stays where it was measured (x 285.25), so only the hidden -x hip slope gets
2.5 wider; the eave corner then sits on the drawn roof corner (overlay check ~/Project-Friday-Test/lktest/church610/ovz.png, local).
Pure Python, no ROM.  Run: python3 remake/recipes/proxy_church_610.py -> landstalker/data/proxies/church_610.obj"""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); PROX = os.path.join(HERE, "..", "..", "landstalker", "data", "proxies")
DX, DY, DZ = 16.0, -272.0, 32.0
HALL_X0_OLD, HALL_X0 = 238.0, 235.5        # Mercator coordinates: the four hall wall vertices on x 238 (feet + eave corners), nothing else lies there
src = os.path.join(PROX, "church_632.obj"); dst = os.path.join(PROX, "church_610.obj"); xs, ys = [], []; moved = 0
with open(dst, "w") as fo:
    fo.write("# light proxy: Ryuma church = the Mercator church model moved by (+16, -272, +32), hall -x wall at the measured x 235.5 (remake/recipes/proxy_church_610.py). GAME coordinates x east, y south, z up.\n")
    for l in open(src):
        if l.startswith("v "):
            x, y, z = map(float, l.split()[1:4])
            if abs(x - HALL_X0_OLD) < 1e-6: x = HALL_X0; moved += 1
            x += DX; y += DY; z += DZ; xs.append(x); ys.append(y)
            fo.write("v %g %g %g\n" % (round(x, 3), round(y, 3), round(z, 3)))
        elif l.startswith("f "): fo.write(l)
assert moved == 4, "expected the 4 hall corner vertices on x 238, found %d" % moved
print("proxy_church_610: %d vertices (%d hall corners moved) -> %s; cells x %d..%d y %d..%d" % (len(xs), moved, dst, int(min(xs)) // 16, int(max(xs)) // 16, int(min(ys)) // 16, int(max(ys)) // 16))
