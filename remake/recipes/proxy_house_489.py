#!/usr/bin/env python3
"""LIGHT SHAPE: the LOG HUT of room 489 = the room 468 hut (remake/recipes/proxy_house_468.py, Massan house B's tiles on a 5 x 5 square) MIRRORED on
the diagonal x <-> y: in 489 the door / shutter are on the E wall and the round window on the S wall (468: door / shutter S, window E); collision
x 18..22 y 22..26 height 64 on ground 16, door cell (22,25) (468: x 35..39 y 27..31, door cell (38,31) -> mirrored (31,38) - (27,35) + (18,22) = (22,25)).
Measured 2026-11-24 (overlay ~/Project-Friday-Test/lktest/lf3/sh489.png, local). Pure Python, no ROM.
Run: python3 remake/recipes/proxy_house_489.py  ->  landstalker/data/proxies/house_489.obj (after proxy_house_468)"""
import os
PROX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "data", "proxies")
X0_468, Y0_468, X0_489, Y0_489 = 35 * 16, 27 * 16, 18 * 16, 22 * 16
with open(os.path.join(PROX, "house_489.obj"), "w") as fo:
    fo.write("# light proxy: log hut of room 489 = the room 468 hut mirrored x <-> y (remake/recipes/proxy_house_489.py). GAME coordinates x east, y south, z up.\n")
    for l in open(os.path.join(PROX, "house_468.obj")):
        if l.startswith("v "):
            x, y, z = map(float, l.split()[1:4]); fo.write("v %g %g %g\n" % (round(y - Y0_468 + X0_489, 3), round(x - X0_468 + Y0_489, 3), z))
        elif l.startswith("f "): fo.write("f " + " ".join(reversed(l.split()[1:])) + "\n")   # a mirror flips the winding
print("proxy_house_489: written")
