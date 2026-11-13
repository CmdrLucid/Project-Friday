#!/usr/bin/env python3
"""check_proxies.py [-v]  -- RULE (user, 3 times, last 2026-11-13; CLAUDE.md + LESSONS top): every light shape OBJ in data/proxies/ must be a real
near-final 3D model, never boxes.  This check flags an OBJ whose every face is an axis-aligned rectangle (= only boxes / slabs / 4 x 4 posts).
Old box proxies that are still to be replaced are listed in LEGACY with the reason; do not add new names there - build the real model instead.
Run by the pre-commit hook; exit 1 = a box-only OBJ that is not in LEGACY."""
import glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); PROX = os.path.join(HERE, "..", "data", "proxies")
LEGACY = {   # box proxies made before the rule was enforced: TO BE REPLACED by real models (HANDOFF NEXT)
    "arcade_486.obj", "wall_638.obj",   # architecture (user approved 2026-11-09); boxy by nature, review when the remake builds them
}
RECTILINEAR = {   # objects DRAWN as straight boxes whose model is made of axis-aligned parts on purpose (grooves / boards >= 1 unit): name -> why.
    # Only with the user's OK; rounding below 1 unit gave dotted light lines (HANDOFF 0a413).
    "counter_island.obj": "shop counter: plank top + boards with 1 x 1 grooves + cloth 1 thick (user OK 2026-11-13: 'das passt')",
    "counter_wall.obj": "shop wall counter: as the island (user OK 2026-11-13: 'das passt')",
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
    if boxy(p) and n not in RECTILINEAR: (legacy if n in LEGACY else bad).append(n)
if "-v" in sys.argv: print("check_proxies: legacy box proxies still to replace: %s" % (", ".join(legacy) or "none"))
if bad:
    print("check_proxies: BOX-ONLY light shape(s): %s\n  -> build a real near-final 3D model (CLAUDE.md 'LIGHT SHAPES = REAL 3D MODELS', LESSONS top)" % ", ".join(bad)); sys.exit(1)
print("check_proxies: ok (%d legacy box proxies to replace)" % len(legacy))
