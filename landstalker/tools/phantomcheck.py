#!/usr/bin/env python3
"""phantomcheck.py ROM [ROOMS] [--out DIR] [--top N] [--min-len N]  -- finds PHANTOM BLOCKS: collision cells of the game's height map that stand higher
than the drawing (railing strips, invisible barriers behind walkways, blocked rims), the cause of most hard edges in the light (Kazalt 737, 2026-11-26).

Idea (user 2026-11-26: 'irgendeine Moeglichkeit, das generell auszuschliessen'): a REAL block is drawn with an edge where its top meets its front face
(top and side are painted differently); a phantom block's top edge runs through uninterrupted wall / floor texture.  For every cell that is higher than
its front neighbour (+x or +y, the faces the camera sees) the tool projects the block's top edge into the room picture drawn from the ROM
(romrender.py; U = wx - wy + 1184, V = (wx + wy) / 2 - z, world units), keeps the edge points no nearer cell hides (view ray (+t, +t, +t) through the
height map), and compares the picture a few pixels inside the top with a few pixels down the face (3 x 3 means).  A segment (one cell edge) is WEAK when the
median colour step along it is small.  Weak segments are joined into runs of connected cells; a run of >= --min-len (2) weak segments is a candidate.

ROOMS: comma list / a-b ranges (default all 816).  Only BLOCKED cells (a walkable cell carries Nigel, its height is the drawn floor; --all = every cell), no cell
near a plant foot (data/plants.json: drawn by the plant models), no edge with both sides near black (dungeon void backdrops).  Prints one line per candidate (room, cells, height, face, weak share, median step) and writes, with --out,
DIR/room_R.png (the room picture, weak edges magenta, strong edges green, candidates boxed) for a look.  Cells already covered by a light data op of
data/light_proxies.json (mesh / ground / water / void rectangles) are marked 'handled'.  Local test aid: the pictures are ROM derived (never commit them).
Thresholds: --weak S (colour step, default 28 = sum of |dR|+|dG|+|dB| of the 3 x 3 means), calibrated on room 737 (railing strips / courtyard barrier = weak)."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import romrender, romroom

HERE = os.path.dirname(os.path.abspath(__file__))

def picture(rom, room):
    """the room picture as numpy arrays (plane pixel coordinates = U, V): rgb (H, W, 3) and the plane mask (1 = plane A pixel, 2 = plane B, 0 = backdrop)"""
    g, r, pa, pb, getpal = romrender.rom_planes(rom, room); tp = romrender.tile_cache(g['tiles'])
    W, H = 300 * 8, 152 * 8
    idx = np.zeros((4, H, W), np.uint8); line = np.zeros((4, H, W), np.uint8)   # layers: A high, B high, A low, B low
    for pl, (hi, lo) in ((pa, (0, 2)), (pb, (1, 3))):
        for (tc, tr), t in pl.t.items():
            if tc < 0 or tr < 0 or tc >= 300 or tr >= 152: continue
            px = np.array(tp(t[0], t[3], t[4]), np.uint8); k = hi if t[2] else lo
            idx[k, tr * 8:tr * 8 + 8, tc * 8:tc * 8 + 8] = px; line[k, tr * 8:tr * 8 + 8, tc * 8:tc * 8 + 8] = t[1]
    pal = np.zeros((4, 16, 3), np.uint8)
    for l in range(4):
        for i in range(16): pal[l, i] = getpal(l, i)
    rgb = np.zeros((H, W, 3), np.uint8); mask = np.zeros((H, W), np.uint8); done = np.zeros((H, W), bool)
    for k in range(4):
        m = (idx[k] != 0) & ~done
        rgb[m] = pal[line[k][m], idx[k][m]]; mask[m] = 1 if k in (0, 2) else 2; done |= m
    return rgb, mask

def heights(rom, room):
    """{(world x, world y): (height units, blocked)} for every non-zero height map word (world cell = index + 12, FORMATS 'Height map')"""
    a = romroom.arrays(romroom.decode(rom, room))['HM']
    return {(x + 12, y + 12): (16 * ((v >> 8) & 15), bool((v >> 8) & 0x60)) for (x, y), v in a.items() if v}

def handled_cells(room):
    try: d = json.load(open(os.path.join(HERE, '..', 'data', 'light_proxies.json')))['rooms'].get(str(room), [])
    except Exception: return set()
    out = set()
    for o in d:
        c = o.get('cells')
        if o.get('op') in ('mesh', 'ground', 'water', 'void', 'flat', 'remove') and c and len(c) >= 4:
            for x in range(c[0], c[2] + 1):
                for y in range(c[1], c[3] + 1): out.add((x, y))
    return out

def visible(hm, wx, wy, z, reach=400):
    """the world point is seen by the camera: no cell along the view ray (+t, +t, +t) rises above the ray"""
    t = 1.0
    while t < reach:
        c = hm.get((int((wx + t) // 16), int((wy + t) // 16)))
        if c and c[0] >= z + t: return False
        t += 2.0
    return True

def mean3(rgb, U, V):
    U = int(round(U)); V = int(round(V))
    if U < 1 or V < 1 or V >= rgb.shape[0] - 1 or U >= rgb.shape[1] - 1: return None
    return rgb[V - 1:V + 2, U - 1:U + 2].reshape(-1, 3).astype(float).mean(0)

def edge_step(rgb, mask, hm, X, Y, face, z, d_face=5.0):
    """(colour step, samples) of the AVERAGED vertical profile (13 px) across the cell's top edge line placed at height z: a drawn edge stays a step after
    averaging over the segment, random texture (moss specks) averages out"""
    prof = []
    for s in np.arange(1.0, 16.0, 1.0):
        if face == 'x': wx, wy = 16.0 * (X + 1), 16.0 * Y + s
        else: wx, wy = 16.0 * X + s, 16.0 * (Y + 1)
        if not visible(hm, wx, wy, z + 1) or not visible(hm, wx, wy, z - d_face): continue
        U = int(round(wx - wy + 1184)); V = int(round((wx + wy) / 2 - z))
        if V - 6 < 0 or V + 7 > rgb.shape[0] or U < 0 or U >= rgb.shape[1] or mask[V, U] == 0: continue
        prof.append(rgb[V - 6:V + 7, U].astype(float))
    if len(prof) < 6: return None, len(prof)
    P = np.mean(prof, 0); a, b = P[3:6].mean(0), P[7:10].mean(0)
    if a.mean() < 24 and b.mean() < 24: return None, len(prof)   # both sides near black (void backdrops of the dungeons): nothing to compare
    return float(np.abs(a - b).sum()), len(prof)

def plant_cells(room):
    """cells within 10 units of a plant foot (data/plants.json): the light draws those with the plant models (LK_LTPLANT), their collision boxes are no phantom"""
    try: pl = json.load(open(os.path.join(HERE, '..', 'data', 'plants.json')))['rooms'].get(str(room), [])
    except Exception: return set()
    out = set()
    for _, x, y, _z in pl:
        for cx in range(int((x - 10) // 16), int((x + 10) // 16) + 1):
            for cy in range(int((y - 10) // 16), int((y + 10) // 16) + 1): out.add((cx, cy))
    return out

def segments(rgb, mask, hm, skip=frozenset(), blocked_only=True):
    """every visible top edge segment: (cell, face 'x' | 'y', z, drop, step at z, samples, blocked, best z, step at best z).  best z = the height
    between the front neighbour and the cell (steps of 4) where the drawing shows the strongest edge: a block drawn LOWER than its collision
    (railing strips: the drawn walkway edge 2 steps below) has its best z clearly below z"""
    out = []
    for (X, Y), (z, bl) in hm.items():
        if (blocked_only and not bl) or (X, Y) in skip: continue   # a walkable cell carries Nigel: its height is the drawn floor
        for face, (nx, ny) in (('x', (X + 1, Y)), ('y', (X, Y + 1))):
            n = hm.get((nx, ny)); zn = n[0] if n else 0
            if z - zn < 8 or z == 0: continue
            st, k = edge_step(rgb, mask, hm, X, Y, face, z)
            if st is None: continue
            bz, bs = z, st
            for z2 in range(z - 4, max(zn + 4, z - 64) - 1, -4):
                s2, _ = edge_step(rgb, mask, hm, X, Y, face, z2)
                if s2 is not None and s2 > bs: bz, bs = z2, s2
            out.append(((X, Y), face, z, z - zn, st, k, bl, bz, bs))
    return out

def kind(x, wk):
    """'none': no drawn edge at the collision height (step < wk: an invisible barrier); 'lower': the drawing's edge lies >= 12 below (best step >= 50
    and 1.5 x the step at the collision height: a railing / rim strip standing above the drawn walkway); '' = looks drawn"""
    if x[4] < wk: return 'none'
    if x[2] - x[7] >= 12 and x[8] >= 50 and x[8] >= 1.5 * x[4]: return 'lower'
    return ''

def runs(weak, wk):
    """connected runs of flagged segments: same face, same kind, neighbouring cells ALONG the edge line (face x: y +-1, face y: x +-1), any height (stairs)"""
    left = {(x[0], x[1]): x for x in weak}; out = []
    while left:
        k, v = left.popitem(); grp = [v]; todo = [k]
        while todo:
            (c, f) = todo.pop()
            for d in (((0, 1), (0, -1)) if f == 'x' else ((1, 0), (-1, 0))):
                q = ((c[0] + d[0], c[1] + d[1]), f)
                if q in left and kind(left[q], wk) == kind(v, wk): grp.append(left.pop(q)); todo.append(q)
        out.append(grp)
    return out

def main():
    a = [s for s in sys.argv[1:] if not s.startswith('--')]; opt = {}
    i = 1
    while i < len(sys.argv):
        if sys.argv[i].startswith('--') and i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'): opt[sys.argv[i][2:]] = sys.argv[i + 1]; i += 2
        else: i += 1
    rom = open(a[0], 'rb').read(); rooms = []
    for part in (a[1] if len(a) > 1 else '0-815').split(','):
        if '-' in part: p, q = part.split('-'); rooms += list(range(int(p), int(q) + 1))
        else: rooms.append(int(part))
    wk = float(opt.get('weak', 28)); minlen = int(opt.get('min-len', 2)); out = opt.get('out'); top = int(opt.get('top', 0))
    if out: os.makedirs(out, exist_ok=True)
    allc = []
    for room in rooms:
        try: hm = heights(rom, room); rgb, mask = picture(rom, room)
        except Exception as e: print('room %d: skipped (%s)' % (room, e), flush=True); continue
        seg = segments(rgb, mask, hm, plant_cells(room), '--all' not in sys.argv); hc = handled_cells(room); cand = []
        weak = [x for x in seg if kind(x, wk)]
        for g in runs(weak, wk):
            if len(g) < minlen: continue
            cells = sorted(x[0] for x in g); hd = sum(1 for c in cells if c in hc)
            cand.append((room, cells, g[0][2], g[0][1], len(g), float(np.median([x[4] for x in g])), hd, sum(1 for x in g if x[6]), kind(g[0], wk), int(np.median([x[7] for x in g]))))
        for c in cand:
            print('room %3d  %-5s %-24s z %3d  face +%s  %2d edges (blocked %2d), step %4.0f, drawn edge at z %3d%s' % (c[0], c[8], '%s..%s' % (c[1][0], c[1][-1]), c[2], c[3], c[4], c[7], c[5], c[9], '  handled %d/%d' % (c[6], c[4]) if c[6] else ''), flush=True)
        allc += cand
        if out and seg:
            img = rgb.copy()
            def mark(s, col):
                (X, Y), f = s[0], s[1]
                for t in np.arange(0.0, 16.0, 0.5):
                    wx, wy = (16.0 * (X + 1), 16.0 * Y + t) if f == 'x' else (16.0 * X + t, 16.0 * (Y + 1))
                    U = int(round(wx - wy + 1184)); V = int(round((wx + wy) / 2 - s[2]))
                    if 0 <= V < img.shape[0] and 0 <= U < img.shape[1]: img[V, U] = col
            for s in seg: k = kind(s, wk); mark(s, (0, 255, 0) if not k else (255, 0, 255) if k == 'none' else (255, 160, 0))
            ys, xs = np.nonzero(mask)
            if len(xs):
                crop = img[max(0, ys.min() - 8):ys.max() + 8, max(0, xs.min() - 8):xs.max() + 8]
                romrender.png(os.path.join(out, 'room_%d.png' % room), crop.shape[1], crop.shape[0], crop.tobytes())
    print('phantomcheck: %d candidate runs in %d rooms (%d edges, %d not handled by a light data op)' % (len(allc), len(set(c[0] for c in allc)), sum(c[4] for c in allc), sum(c[4] - c[6] for c in allc)))

if __name__ == '__main__':
    main()
