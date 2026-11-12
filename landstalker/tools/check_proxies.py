#!/usr/bin/env python3
"""check_proxies.py [-v]  -- RULE (user, 3 times, last 2026-11-13; CLAUDE.md + LESSONS top): every light shape OBJ in data/proxies/ must be a real
near-final 3D model, never boxes.  This check flags an OBJ whose every face is an axis-aligned rectangle (= only boxes / slabs / 4 x 4 posts).
Old box proxies that are still to be replaced are listed in LEGACY with the reason; do not add new names there - build the real model instead.
Run by the pre-commit hook; exit 1 = a box-only OBJ that is not in LEGACY."""
import glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); PROX = os.path.join(HERE, "..", "data", "proxies")
LEGACY = {   # box proxies made before the rule was enforced: TO BE REPLACED by real models (HANDOFF NEXT)
    "rail_62_gallery.obj", "rail_62_gallery_rail.obj", "rail_62_left.obj", "rail_62_left_rail.obj", "rail_62_right.obj", "rail_62_right_rail.obj",
    "rail_95.obj", "rail_95_rail.obj", "rail_89.obj", "rail_89_rail.obj",
    "table_63.obj", "table_64.obj", "table_65.obj", "table_66.obj", "table_67.obj", "table_77.obj",   # tileset 15 tables (2026-11-12): to become real models
    "arcade_486.obj", "wall_638.obj",   # architecture (user approved 2026-11-09); boxy by nature, review when the remake builds them
}
def boxy(path):
    V = []; faces = 0
    for line in open(path):
        t = line.split()
        if not t: continue
        if t[0] == "v": V.append(tuple(float(a) for a in t[1:4]))
        elif t[0] == "f":
            idx = [int(a.split("/")[0]) - 1 for a in t[1:]]; faces += 1
            if len(idx) != 4: return False
            P = [V[i] for i in idx]
            if not any(len({round(p[k], 3) for p in P}) == 1 for k in range(3)): return False   # not in an axis plane
    return faces > 0
bad = []; legacy = []
for p in sorted(glob.glob(os.path.join(PROX, "*.obj"))):
    n = os.path.basename(p)
    if boxy(p): (legacy if n in LEGACY else bad).append(n)
if "-v" in sys.argv: print("check_proxies: legacy box proxies still to replace: %s" % (", ".join(legacy) or "none"))
if bad:
    print("check_proxies: BOX-ONLY light shape(s): %s\n  -> build a real near-final 3D model (CLAUDE.md 'LIGHT SHAPES = REAL 3D MODELS', LESSONS top)" % ", ".join(bad)); sys.exit(1)
print("check_proxies: ok (%d legacy box proxies to replace)" % len(legacy))
