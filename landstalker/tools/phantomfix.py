#!/usr/bin/env python3
"""phantomfix.py ROM CANDIDATES.json OUTDIR [--min-edges N]  -- turns phantomcheck.py candidates into PROPOSED light data ops + test spots (2026-11-26).

CANDIDATES.json: list of {room, kind, c0, c1, z, face, n, bz} (the runs of phantomcheck.py, already filtered: not handled by a data op).
Per cell of a run the proposed light height is
  - the BACK neighbour's height (the cell behind the face: the walkway / stair step the railing posts stand on) when it is walkable and lower, else
  - the nearest walkable cell within 3 cells that is lower (an invisible barrier: the floor around it), else no proposal.
Writes OUTDIR/ops.json ({room: [ground replace ops]}, one op per row of equal height, "why" names the run) and OUTDIR/cells.txt ('room x y' lines:
one walkable cell next to the middle of every run = where tools/lightedges.py with LIGHTEDGES_CELLS puts Nigel for the sword glow / daylight pictures).
Our own data only (room ids and cell coordinates)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phantomcheck as P

def main():
    a = [s for s in sys.argv[1:] if not s.startswith('--')]; mine = int(sys.argv[sys.argv.index('--min-edges') + 1]) if '--min-edges' in sys.argv else 2
    rom = open(a[0], 'rb').read(); cand = json.load(open(a[1])); out = a[2]; os.makedirs(out, exist_ok=True)
    ops = {}; cells = []; hmc = {}; nprop = 0; nrun = 0
    for r in cand:
        if r['n'] < mine: continue
        room = r['room']; hm = hmc.setdefault(room, P.heights(rom, room)); f = r['face']
        (x0, y0), (x1, y1) = r['c0'], r['c1']
        run = [(x0, y) for y in range(y0, y1 + 1)] if f == 'x' else [(x, y0) for x in range(x0, x1 + 1)]
        walk = lambda c: c in hm and not hm[c][1]
        prop = []
        for (X, Y) in run:
            if (X, Y) not in hm: continue
            z = hm[(X, Y)][0]; b = (X - 1, Y) if f == 'x' else (X, Y - 1)
            if walk(b) and hm[b][0] < z: prop.append(((X, Y), hm[b][0])); continue
            best = None
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    c = (X + dx, Y + dy)
                    if walk(c) and hm[c][0] < z and (best is None or dx * dx + dy * dy < best[0]): best = (dx * dx + dy * dy, hm[c][0])
            if best: prop.append(((X, Y), best[1]))
        if not prop: continue
        nrun += 1; nprop += len(prop)
        why = "phantomcheck %s run %s..%s z %d face +%s (%d edges): collision above the drawing -> the walkable neighbour's height (tools/phantomfix.py proposal)" % (r['kind'], tuple(r['c0']), tuple(r['c1']), r['z'], f, r['n'])
        k = 0
        while k < len(prop):   # rows of equal height along the run -> one op each
            j = k
            while j + 1 < len(prop) and prop[j + 1][1] == prop[k][1]: j += 1
            (ax, ay), (bx, by) = prop[k][0], prop[j][0]
            ops.setdefault(str(room), []).append({"op": "ground", "cells": [min(ax, bx), min(ay, by), max(ax, bx), max(ay, by), prop[k][1]], "replace": True, "why": why})
            k = j + 1
        mx, my = run[len(run) // 2]; spot = None
        for d in range(1, 4):   # a walkable cell beside the run's middle, the face side first (the glow lights the face)
            for c in ((mx + d, my), (mx, my + d), (mx - d, my), (mx, my - d), (mx + d, my + d)):
                if walk(c): spot = c; break
            if spot: break
        if spot: cells.append((room, spot[0], spot[1]))
    json.dump(ops, open(os.path.join(out, 'ops.json'), 'w'), indent=1)
    with open(os.path.join(out, 'cells.txt'), 'w') as fo:
        for c in cells: fo.write('%d %d %d\n' % c)
    print('phantomfix: %d runs -> %d cells proposed in %d rooms, %d test spots' % (nrun, nprop, len(ops), len(cells)))

if __name__ == '__main__':
    main()
