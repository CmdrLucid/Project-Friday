"""LIGHT PROXY: the big ROCK MOUNTAIN of room 503 (barrier wall pass 2026-11-27, user: 'muss halt wirklich genau drauflegen').
An invisible shape for the lighting (op 'mesh' + "surface"), GAME coordinates (x east, y south, z up, one map cell = 16), near-final geometry.

Why: the mountain is drawn over VOID cells (height map #0) and the game's invisible BARRIER cells ($4F); the light's void painter filled them as a low water
floor (8) = a hole: the view rays went through the drawn rock to a floor far behind, the sword glow never lit the wall. Per-cell heights (ground replace,
even 'exactly measured' per cell) gave vertical light bands in daylight (a jagged cell front; LESSONS 2026-11-27). Here the rock is ONE closed solid:

FOOTPRINT = the barrier lines of the height map (the game's collision follows the drawn wall foot):
  +x face x 352 for y 576..752 (barrier column x 21, rows 36..46), x 368 for y 496..576 (barrier x 21..22, rows 30..35, the 176 walkway row 31 starts at x 23),
  +y face y 496 for x 368..480 (barrier row 30 behind the 176 walkway), +x face x 480 for y 432..496 (barrier x 29, rows 26..29, the x 30..32 walkway),
  x 496 for y 416..432 (barrier (30, 26)); the two short steps between them face +y. Left / right ends on the vertical screen lines U 784 (the drawn
  picture's left border) and U 1264 (the shoulder meets the walkway): sides seen exactly edge-on.
TOP = the drawn OUTLINE extruded along the view direction (1, 1, 1): z(x, y) = (x + y) / 2 - Vsil(U), U = x - y + 1184 (docs/FORMATS.md projection).
  Every point of the top projects onto the drawn silhouette, so the camera sees the top only edge-on (no visible top face) and each front face ends exactly
  at the drawn top edge. MEASURED on the room picture (topmost drawn pixel per picture column, local helper over tools/romrender.py):
    U 812..1055  V = 623 - U / 2   (a straight line to the pixel: the top edge of the x 368 face at z 336, x 352 face at z 320)
    U 1056..1220 V = U / 2 - 432   (the y 496 face at z 336; on the x 480 face z = y - 160)
    U 784..812 / 1220..1264: the rounded rocky shoulders (pixel outline, upper envelope over 5 columns = the rock is covered, a few sky pixels at most).
  Behind the front the top falls below the ground (z < 16) near the right shoulder: the solid ends there (back cut).
Bottom z 0 (the void cells; every walkable / blocked cell of the height map stays outside the footprint).
Output: landstalker/data/proxies/rock_503_a..d.obj (four pieces, see PIECES; our own geometry, committed). Run: python3 remake/recipes/proxy_rock_503.py"""
import os

# measured shoulder outline (U, V of the topmost drawn pixel), room 503
LEFT = [(784, 280), (785, 280), (786, 281), (787, 275), (788, 273), (789, 272), (790, 271), (791, 269), (792, 269), (793, 262), (794, 261), (795, 258),
        (796, 257), (797, 258), (798, 257), (799, 256), (800, 240), (801, 240), (802, 241), (803, 235), (804, 233), (805, 232), (806, 231), (807, 229),
        (808, 229), (809, 222), (810, 221), (811, 218), (812, 217)]
RIGHT = [(1220, 178), (1221, 179), (1222, 180), (1223, 181), (1224, 181), (1225, 183), (1226, 184), (1227, 185), (1228, 187), (1229, 193), (1230, 192),
         (1231, 192), (1232, 208), (1233, 209), (1234, 210), (1235, 209), (1236, 210), (1237, 213), (1238, 214), (1239, 221), (1240, 221), (1241, 223),
         (1242, 224), (1243, 225), (1244, 227), (1245, 233), (1246, 232), (1247, 232), (1248, 248), (1249, 249), (1250, 250), (1251, 249), (1252, 250),
         (1253, 253), (1254, 254), (1255, 261), (1256, 261), (1257, 263), (1258, 264), (1259, 265), (1260, 267), (1261, 273), (1262, 275), (1263, 279),
         (1264, 280)]
U_L, U_R = 784, 1264
FRONT = [(352, 752), (352, 576), (368, 576), (368, 496), (480, 496), (480, 432), (496, 432), (496, 416)]   # wall foot polyline, left -> right (x, y)
BACK_X, BACK_Y = 192, 192   # the map's back edges (cells 12)
GROUND = 16

def envelope(pts, w=2):
    """upper envelope (smallest V) over +-w columns, then a 3 tap mean: covers the rocky outline without its 1 px jitter"""
    d = dict(pts); us = sorted(d)
    e = {u: min(d[v] for v in us if abs(v - u) <= w) for u in us}
    return {u: (e.get(u - 1, e[u]) + e[u] + e.get(u + 1, e[u])) / 3.0 for u in us}

EL, ER = envelope(LEFT), envelope(RIGHT)
def vsil(U):
    if U <= 812:
        a = int(U); f = U - a; return EL[min(a, 812)] * (1 - f) + EL[min(a + 1, 812)] * f
    if U <= 1055.5: return 623.0 - U / 2.0
    if U <= 1220: return U / 2.0 - 432.0
    a = int(U); f = U - a; return ER[min(a, 1264)] * (1 - f) + ER[min(a + 1, 1264)] * f

def front_s(u):
    """s = x + y of the wall foot on the screen column u = x - y"""
    for (x0, y0), (x1, y1) in zip(FRONT, FRONT[1:]):
        ua, ub = x0 - y0, x1 - y1
        if min(ua, ub) - 1e-9 <= u <= max(ua, ub) + 1e-9:
            return 2 * x0 - u if x0 == x1 else 2 * y0 + u
    raise ValueError(u)

def back_s(u):
    s = BACK_X * 2 - u if u < BACK_X - BACK_Y else BACK_Y * 2 + u
    return max(s, 2 * (vsil(u + 1184) + GROUND))   # the edge-on top falls below the ground: the solid ends there

def ztop(u, s): return s / 2.0 - vsil(u + 1184)

# The light gives an outdoor surface model its WHOLE op rectangle (LK_GLROOM clean-up: raised collision cells in it that no model covers are set to the
# ground), so the solid is cut into four pieces whose rectangles hold only mountain cells (void / barrier); the cut faces between them lie inside the rock.
PIECES = {"a": (12, 12, 21, 46), "b": (22, 12, 22, 35), "c": (23, 12, 29, 30), "d": (30, 12, 30, 26)}   # cells x0 y0 x1 y1 (inclusive)

def s_range(u, r):
    """the s interval of the screen column u inside piece rectangle r (world units), cut by the mountain's back / outline"""
    x0, y0, x1, y1 = 16 * r[0], 16 * r[1], 16 * r[2] + 16, 16 * r[3] + 16
    lo = max(2 * x0 - u, 2 * y0 + u, back_s(u)); hi = min(2 * x1 - u, 2 * y1 + u, front_s(u))
    return lo, hi

def build(r):
    x0, y0, x1, y1 = 16 * r[0], 16 * r[1], 16 * r[2] + 16, 16 * r[3] + 16
    ua, ub = max(U_L - 1184, x0 - y1), min(U_R - 1184, x1 - y0)
    brk = {x - y for x, y in FRONT} | {0, x0 - y0, x1 - y1, x0 - y1, x1 - y0}
    us = sorted(set([float(u) for u in range(int(ua), int(ub) + 1, 2) if ua <= u <= ub] + [float(b) for b in brk if ua <= b <= ub] + [float(ua), float(ub)]))
    V, F = [], []
    def vid(p): V.append(p); return len(V) - 1
    runs, cur = [], []
    for u in us:
        lo, hi = s_range(u, r)
        if hi - lo < 0.01:
            if cur: runs.append(cur); cur = []
            continue
        xy = lambda s: ((s + u) / 2.0, (s - u) / 2.0)
        (xf, yf), (xb, yb) = xy(hi), xy(lo)
        cur.append((vid((xf, yf, ztop(u, hi))), vid((xb, yb, ztop(u, lo))), vid((xf, yf, 0.0)), vid((xb, yb, 0.0))))
    if cur: runs.append(cur)
    for col in runs:
        for (tf0, tb0, bf0, bb0), (tf1, tb1, bf1, bb1) in zip(col, col[1:]):
            F += [(tb0, tf0, tf1), (tb0, tf1, tb1)]          # top (seen edge-on)
            F += [(bf0, bb0, bb1), (bf0, bb1, bf1)]          # bottom
            F += [(tf0, bf0, bf1), (tf0, bf1, tf1)]          # front side (outward = +s)
            F += [(bb0, tb0, tb1), (bb0, tb1, bb1)]          # back side (outward = -s)
        tf, tb, bf, bb = col[0]; F += [(tf, tb, bb), (tf, bb, bf)]       # left end (outward -u)
        tf, tb, bf, bb = col[-1]; F += [(tb, tf, bf), (tb, bf, bb)]      # right end (outward +u)
    F = [(a, c, b) for a, b, c in F]   # (written in screen order above; flipped = counter-clockwise around the outward normal)
    def area(t):
        a, b, c = (V[i] for i in t)
        n = ((b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]), (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]), (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
        return sum(q * q for q in n) ** .5
    return V, [t for t in F if area(t) > 1e-6]

def orient_check(V, F, r):
    """every triangle's right-handed normal must point away from the solid: probe a point 0.5 along it and 0.5 against it (ray parity in s)"""
    bad = 0
    for f in F:
        a, b, c = (V[i] for i in f)
        n = ((b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1]), (b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]), (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
        L = sum(t * t for t in n) ** .5
        if L < 1e-9: continue
        m = [(a[i] + b[i] + c[i]) / 3 for i in range(3)]
        p = [m[i] + n[i] / L * 0.5 for i in range(3)]
        u, s = p[0] - p[1], p[0] + p[1]
        if U_L - 1184 < u < U_R - 1184 and 0 < p[2]:
            lo, hi = s_range(u, r); inside = lo < s < hi and p[2] < ztop(u, s)   # inside its OWN piece (a cut face probes into the neighbour piece)
            if inside: bad += 1
    return bad

if __name__ == "__main__":
    for k, r in PIECES.items():
        V, F = build(r)
        bad = orient_check(V, F, r)
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "data", "proxies", "rock_503_%s.obj" % k)
        with open(out, "w") as f:
            f.write("# room 503 rock mountain piece %s (cells %d..%d x %d..%d), light proxy (remake/recipes/proxy_rock_503.py), game coordinates\n" % (k, r[0], r[2], r[1], r[3]))
            for v in V: f.write("v %.3f %.3f %.3f\n" % v)
            for t in F: f.write("f %d %d %d\n" % (t[0] + 1, t[1] + 1, t[2] + 1))
        zs = [v[2] for v in V]
        print("proxy_rock_503 %s: %d vertices, %d triangles, z %.1f..%.1f, inward-facing triangles: %d -> %s" % (k, len(V), len(F), min(zs), max(zs), bad, os.path.normpath(out)))
