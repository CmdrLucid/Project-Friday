"""rockwall.py -- closed ROCK solids for the light (op 'mesh' + "surface") from a room's barrier lines and its drawn outline (barrier wall pass 2026-11-27).

Used by remake/recipes/proxy_rock_<room>.py. Game coordinates (x east, y south, z up; one map cell = 16), projection U = x - y + 1184, V = (x + y) / 2 - z.
  * FOOTPRINT: a list of cell RECTANGLES (inclusive) that hold only the rock's own cells (void / barrier): an outdoor surface model owns its whole op rectangle
    (LK_GLROOM clean-up flattens uncovered raised cells in it), so every rectangle becomes its own piece / OBJ / op; the cut faces between pieces lie inside.
  * TOP: z(x, y) = min(s / 2 - Vsil(U), cap(U)), s = x + y: the drawn OUTLINE extruded along the view ray (1, 1, 1) = seen edge-on (no visible top face,
    each front face ends at the drawn top edge), optionally capped by a measured flat top (a drawn plateau: its grass top is a real, visible top face).
    Where the top falls below `ground` the solid ends (back cut).
  * the solid is built in screen strips (u = x - y): exact planar faces on every rectangle edge (no cell staircase on a straight wall).
Writes triangles only (the game's OBJ reader fans n-gons), counter-clockwise around the outward normal (right-handed in game coordinates)."""

def envelope(pts, w=2):
    """pixel outline [(U, V), ...] -> {U: V}: upper envelope (smallest V) over +-w columns, then a 3 tap mean (covers the drawn rock, no 1 px jitter)"""
    d = dict(pts); us = sorted(d)
    e = {u: min(d[v] for v in range(u - w, u + w + 1) if v in d) for u in us}
    return {u: (e.get(u - 1, e[u]) + e[u] + e.get(u + 1, e[u])) / 3.0 for u in us}

class Rock:
    def __init__(self, vsil, u_left, u_right, cap=None, ground=16):
        """vsil(U) -> V of the drawn outline; the solid lives in the screen columns u_left..u_right (U = u + 1184); cap(U) -> flat top z or None"""
        self.vsil, self.ul, self.ur, self.cap, self.ground = vsil, u_left, u_right, cap, ground

    def ztop(self, u, s):
        z = s / 2.0 - self.vsil(u + 1184)
        c = self.cap(u + 1184) if self.cap else None
        return min(z, c) if c is not None else z

    def s_range(self, u, r):
        x0, y0, x1, y1 = 16 * r[0], 16 * r[1], 16 * r[2] + 16, 16 * r[3] + 16
        lo = max(2 * x0 - u, 2 * y0 + u, 2 * (self.vsil(u + 1184) + self.ground))   # back cut: the edge-on top below the ground
        hi = min(2 * x1 - u, 2 * y1 + u)
        return lo, hi

    def piece(self, r, step=2, zb=0.0):
        """one closed piece over cell rectangle r; zb > 0 = a LINTEL that starts at that height (a door below it stays open)"""
        x0, y0, x1, y1 = 16 * r[0], 16 * r[1], 16 * r[2] + 16, 16 * r[3] + 16
        ua, ub = max(self.ul, x0 - y1), min(self.ur, x1 - y0)
        if ua >= ub: return [], []
        brk = {x0 - y0, x1 - y1, ua, ub}
        if self.cap:   # the cap switches on / off at its own screen columns: sample them exactly
            prev = None
            for u in range(int(ua), int(ub) + 1):
                c = self.cap(u + 1184) is None
                if prev is not None and c != prev: brk.add(u)
                prev = c
        us = sorted(set([float(u) for u in range(int(ua), int(ub) + 1, step) if ua <= u <= ub] + [float(b) for b in brk if ua <= b <= ub]))
        V, F = [], []
        def vid(p): V.append(p); return len(V) - 1
        runs, cur = [], []
        for u in us:
            lo, hi = self.s_range(u, r)
            if hi - lo < 0.01:
                if cur: runs.append(cur); cur = []
                continue
            xy = lambda s: ((s + u) / 2.0, (s - u) / 2.0)
            (xf, yf), (xb, yb) = xy(hi), xy(lo)
            zf, zbk = self.ztop(u, hi), self.ztop(u, lo)
            if min(zf, zbk) <= zb + 0.5:   # the top falls to the lintel bottom: no lintel here
                if cur: runs.append(cur); cur = []
                continue
            cur.append((vid((xf, yf, zf)), vid((xb, yb, zbk)), vid((xf, yf, float(zb))), vid((xb, yb, float(zb))), u, hi, lo))
        if cur: runs.append(cur)
        for col in runs:
            ms = [self._mid(c, vid) for c in col]   # kink vertex on the top of every strip end (edge-on behind, cap in front), or the front / back point
            for (c0, m0), (c1, m1) in zip(zip(col, ms), zip(col[1:], ms[1:])):
                tf0, tb0, bf0, bb0 = c0[:4]; tf1, tb1, bf1, bb1 = c1[:4]
                if m0 in (tf0, tb0) and m1 in (tf1, tb1) and (m0 == tf0) == (m1 == tf1):
                    F += [(tb0, tf0, tf1), (tb0, tf1, tb1)]          # top: one plane piece (all edge-on or all cap)
                else:
                    F += [(m0, tf0, tf1), (m0, tf1, m1), (tb0, m0, m1), (tb0, m1, tb1)]   # cap part in front of the kink, edge-on part behind
                F += [(bf0, bb0, bb1), (bf0, bb1, bf1)]          # bottom
                F += [(tf0, bf0, bf1), (tf0, bf1, tf1)]          # front side (outward +s)
                F += [(bb0, tb0, tb1), (bb0, tb1, bb1)]          # back side (outward -s)
            (tf, tb, bf, bb), m = col[0][:4], ms[0]
            F += [(tf, tb, bb), (tf, bb, bf)] if m in (tf, tb) else [(bf, tf, m), (bf, m, tb), (bf, tb, bb)]    # left end (outward -u)
            (tf, tb, bf, bb), m = col[-1][:4], ms[-1]
            F += [(tb, tf, bf), (tb, bf, bb)] if m in (tf, tb) else [(bb, tb, m), (bb, m, tf), (bb, tf, bf)]    # right end (outward +u)
        F = [(a, c, b) for a, b, c in F]   # written in screen order above; flipped = counter-clockwise around the outward normal
        def area(t):
            a, b, c = (V[i] for i in t)
            n = ((b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]), (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]), (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
            return sum(q * q for q in n) ** .5
        return V, [t for t in F if area(t) > 1e-6]

    def _mid(self, c, vid):
        """the top's kink on this strip end: a new vertex where the edge-on top meets the cap inside the interval; else the front point (all edge-on)
        or the back point (all cap = flat from back to front)"""
        tf, tb, u, hi, lo = c[0], c[1], c[4], c[5], c[6]
        cap = self.cap(u + 1184) if self.cap else None
        if cap is None: return tf
        sk = 2 * (cap + self.vsil(u + 1184))   # s / 2 - vsil = cap
        if sk >= hi - 0.01: return tf
        if sk <= lo + 0.01: return tb
        return vid(((sk + u) / 2.0, (sk - u) / 2.0, float(cap)))

    def orient_bad(self, V, F, r):
        """triangles whose right-handed normal points INTO their own piece (0.3 probe); slivers at kinks may count a few"""
        bad = 0
        for f in F:
            a, b, c = (V[i] for i in f)
            n = ((b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]), (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]), (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
            L = sum(t * t for t in n) ** .5; m = [(a[i] + b[i] + c[i]) / 3 for i in range(3)]
            p = [m[i] + n[i] / L * 0.3 for i in range(3)]; u, s = p[0] - p[1], p[0] + p[1]
            if not (self.ul < u < self.ur): continue
            lo, hi = self.s_range(u, r)
            if lo < s < hi and 0 < p[2] < self.ztop(u, s): bad += 1
        return bad

def write_obj(path, V, F, title):
    with open(path, "w") as f:
        f.write("# %s\n" % title)
        for v in V: f.write("v %.3f %.3f %.3f\n" % v)
        for t in F: f.write("f %d %d %d\n" % (t[0] + 1, t[1] + 1, t[2] + 1))
