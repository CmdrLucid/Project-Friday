#!/usr/bin/env python3
"""knight.py OUT.obj [params.json] : the ARMOUR KNIGHT of the Mercator houses (tileset 2, top blocks $19C / $2D7: rooms 678 679 695 696 697 719 720) as OUR OWN
3D model from parts (user 2026-11-11 'mach 2 dann' = the armour knights as 3D light shapes). Reference: room 678 cell (30, 26), window U0 1216 V0 392
(64 x 80), the knight's own pixels by colour from layer A (the black blob under the feet is a PAINTED SHADOW, left out). Read on the 1 px grid:
a suit of plate armour with a great helm + yellow crest, yellow collar, round pauldrons, a kite shield with a yellow rim at its left side, a lance
(wooden shaft, steel head, red tassels) standing on the floor in its right hand, fauld, leg armour, sabatons; the painted figure is ~37 units tall.
BODY FRAME: s = the figure's left, f = its front, z up, origin on the floor under the body; it faces `yaw` degrees from +y (south = out of the wall
behind it) towards +x. Pure Python: every part is a small closed polygon mesh (ellipsoid, tapered capsule, lathe, plate). No ROM data in here."""
import json, math, sys
P = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
g = lambda k, d: P.get(k, d)
V, F = [], []
def add(vs, fs): o = len(V); V.extend(vs); F.extend([tuple(i + o for i in f) for f in fs])
def ellipsoid(c, r, nu=20, nv=12, rot=0.0):
    """centre c, radii r (s, f, z), turned `rot` degrees about z"""
    vs = [(c[0], c[1], c[2] + r[2])]; fs = []; ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for j in range(1, nv):
        ph = math.pi * j / nv
        for i in range(nu):
            th = 2 * math.pi * i / nu; a, b = r[0] * math.sin(ph) * math.cos(th), r[1] * math.sin(ph) * math.sin(th)
            vs.append((c[0] + a * ca - b * sa, c[1] + a * sa + b * ca, c[2] + r[2] * math.cos(ph)))
    vs.append((c[0], c[1], c[2] - r[2])); last = len(vs) - 1
    for i in range(nu): fs.append((0, 1 + i, 1 + (i + 1) % nu)); fs.append((last, 1 + (nv - 2) * nu + (i + 1) % nu, 1 + (nv - 2) * nu + i))
    for j in range(nv - 2):
        for i in range(nu): a = 1 + j * nu + i; b = 1 + j * nu + (i + 1) % nu; fs.append((a, a + nu, b + nu, b))
    add(vs, fs)
def _frame(ax):
    ref = (0.0, 0.0, 1.0) if abs(ax[2]) < 0.9 else (1.0, 0.0, 0.0)
    e1 = (ax[1] * ref[2] - ax[2] * ref[1], ax[2] * ref[0] - ax[0] * ref[2], ax[0] * ref[1] - ax[1] * ref[0]); l = math.sqrt(sum(t * t for t in e1)); e1 = tuple(t / l for t in e1)
    e2 = (ax[1] * e1[2] - ax[2] * e1[1], ax[2] * e1[0] - ax[0] * e1[2], ax[0] * e1[1] - ax[1] * e1[0]); return e1, e2
def capsule(p, q, r0, r1=None, nu=16, cap=4, flat=1.0):
    """tapered limb from p (radius r0) to q (radius r1) with round ends; `flat` squashes the section along its second axis"""
    r1 = r0 if r1 is None else r1; ax = tuple(q[i] - p[i] for i in range(3)); L = math.sqrt(sum(t * t for t in ax)); ax = tuple(t / L for t in ax); e1, e2 = _frame(ax)
    rings = [(-r0 * math.cos(math.pi / 2 * k / cap), r0 * math.sin(math.pi / 2 * k / cap)) for k in range(1, cap + 1)]           # (offset along the axis, radius): round start
    rings += [(L * k / 6, r0 + (r1 - r0) * k / 6) for k in range(1, 7)]
    rings += [(L + r1 * math.sin(math.pi / 2 * k / cap), r1 * math.cos(math.pi / 2 * k / cap)) for k in range(1, cap)]
    vs = [tuple(p[i] - ax[i] * r0 for i in range(3))]; fs = []
    for d, r in rings:
        for i in range(nu):
            th = 2 * math.pi * i / nu; vs.append(tuple(p[k] + ax[k] * d + r * (math.cos(th) * e1[k] + flat * math.sin(th) * e2[k]) for k in range(3)))
    vs.append(tuple(q[i] + ax[i] * r1 for i in range(3))); last = len(vs) - 1; n = len(rings)
    for i in range(nu): fs.append((0, 1 + (i + 1) % nu, 1 + i)); fs.append((last, 1 + (n - 1) * nu + i, 1 + (n - 1) * nu + (i + 1) % nu))
    for j in range(n - 1):
        for i in range(nu): a = 1 + j * nu + i; b = 1 + j * nu + (i + 1) % nu; fs.append((a, b, b + nu, a + nu))
    add(vs, fs)
def lathe(c, prof, nu=28, sq=2.0, rot=0.0):
    """rings around the vertical line through c = (s, f): prof = [(z, rs, rf)], closed with fans; sq = superellipse power of the section"""
    vs, fs = [], []; ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for z, rs, rf in prof:
        for i in range(nu):
            th = 2 * math.pi * i / nu; ct, st = math.cos(th), math.sin(th); e = 2.0 / sq; a, b = rs * math.copysign(abs(ct) ** e, ct), rf * math.copysign(abs(st) ** e, st)
            vs.append((c[0] + a * ca - b * sa, c[1] + a * sa + b * ca, z))
    n = len(prof)
    for j in range(n - 1):
        for i in range(nu): a = j * nu + i; b = j * nu + (i + 1) % nu; fs.append((a, b, b + nu, a + nu))
    vs.append((c[0], c[1], prof[0][0])); vs.append((c[0], c[1], prof[-1][0])); k = len(vs) - 2
    for i in range(nu): fs.append((k, (i + 1) % nu, i)); fs.append((k + 1, (n - 1) * nu + i, (n - 1) * nu + (i + 1) % nu))
    add(vs, fs)
def plate(c, yaw, outline, t, bend=0.0, n=14):
    """a plate (the shield): `outline` = polygon (u across, v up) in its own plane, centre c, its face turned `yaw` degrees from the front (+f) towards the
    left (+s), thickness t, bent about its vertical middle line (the edges `bend` units back at u = +-1 ... scaled by u^2)"""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)); nrm = (sy, cy); acr = (cy, -sy)   # normal / across in (s, f)
    def pt(u, v, w): w2 = w - bend * u * u; return (c[0] + acr[0] * u + nrm[0] * w2, c[1] + acr[1] * u + nrm[1] * w2, c[2] + v)
    m = len(outline); cu = sum(p[0] for p in outline) / m; cv = sum(p[1] for p in outline) / m; vs, fs = [], []
    for side, w in ((0, t / 2), (1, -t / 2)):
        for k in range(n + 1):
            for (u, v) in outline:
                a = k / n; rim = (0.45 * t if 0.84 <= a < 0.999 else 0.0) if side == 0 else 0.0   # a raised rim along the edge (the drawn yellow border)
                vs.append(pt(cu + (u - cu) * a, cv + (v - cv) * a, w + (0.35 * t * (1 - a * a) + rim if side == 0 else 0.0)))   # the face a little domed
    R = (n + 1) * m
    for side in (0, 1):
        o = side * R
        for k in range(n):
            for i in range(m):
                a = o + k * m + i; b = o + k * m + (i + 1) % m; q = (a, b, b + m, a + m); fs.append(q if side == 0 else q[::-1])
    for i in range(m): a = n * m + i; b = n * m + (i + 1) % m; fs.append((a, a + R, b + R, b))   # rim
    add(vs, fs)

# ---- the figure ---------------------------------------------------------------------------------------------------------------------------------------
H = g('scale', 1.0)
# The drawing follows the sprite convention (a figure 'facing south-west' is drawn with level shoulders): the LEGS face `yaw` (default 20 degrees from +y
# towards the camera) with the feet turned out, the UPPER BODY (torso, shoulders, arms, helm) is turned `twist` degrees further towards the camera.
TW = g('twist', 25.0); _c, _s = math.cos(math.radians(-TW)), math.sin(math.radians(-TW))
def T(p): return (p[0] * _c - p[1] * _s, p[0] * _s + p[1] * _c, p[2])   # upper-body point -> body frame (turned towards +s... the camera side)
# v2 (user 'ja' on the blockout): the DETAILS of plate armour: pointed sabatons, greaves with a shin ridge, winged knee cops, cuisses, a fauld of three
# hoops, a breastplate with a keel and a belt, a collar, a great helm with a brow rim, eye slit ledge, breaths ridge and a comb of plumes, pauldrons of
# three lames, couters, flared gauntlet cuffs with a fist, the lance (butt, shaft, two tassel tufts, a leaf head with a midrib), the kite shield with a rim
for sg in (-1, 1):
    # the two feet point in different directions in the drawing: the right one out to its side, the left one forward
    hip = (sg * 3.2, 0.0, 16.5); knee = (-3.8, 1.6, 9.3) if sg < 0 else (2.5, 1.8, 9.3); ank = (-3.9, 2.0, 2.6) if sg < 0 else (1.7, 2.2, 2.6)
    sp = math.radians(-g('splay_r', 45.0) if sg < 0 else g('splay_l', 30.0)); fd = (math.sin(sp), math.cos(sp))   # the foot's direction (s, f)
    heel = (ank[0] - 1.2 * fd[0], ank[1] - 1.2 * fd[1], 1.5); toe = (ank[0] + 5.6 * fd[0], ank[1] + 5.6 * fd[1], 0.95)
    capsule(heel, toe, 2.1, 0.9, flat=0.75)                                          # sabaton with a pointed toe
    capsule((ank[0] + 0.6 * fd[0], ank[1] + 0.6 * fd[1], 2.7), (ank[0] + 3.0 * fd[0], ank[1] + 3.0 * fd[1], 2.0), 1.35, 1.0)   # the instep plates
    capsule(ank, knee, 1.8, 2.2)                                                      # greave
    capsule((ank[0], ank[1] + 1.5, ank[2] + 0.6), (knee[0], knee[1] + 1.6, knee[2] - 1.2), 0.5, 0.6, nu=8, cap=2)              # its shin ridge
    ellipsoid((knee[0], knee[1] + 1.0, knee[2] + 0.2), (2.15, 1.8, 2.0))              # knee cop
    ellipsoid((knee[0] + sg * 1.9, knee[1] + 0.3, knee[2] + 0.2), (0.9, 1.5, 1.5))    # its side wing
    capsule(knee, hip, 2.3, 2.85)                                                     # cuisse
lathe((0.0, 0.2), [(12.6, 6.1, 4.8), (13.4, 6.2, 4.9), (14.2, 5.9, 4.6), (14.3, 5.75, 4.5), (15.2, 5.85, 4.6), (16.0, 5.55, 4.35), (16.1, 5.4, 4.25), (17.0, 5.5, 4.3), (17.8, 5.2, 4.1), (18.6, 4.8, 3.8)], sq=2.3)   # fauld: three hoops
TC = T((0.0, 0.3, 0))[:2]
lathe(TC, [(18.0, 4.9, 3.9), (18.5, 5.1, 4.1), (19.0, 4.9, 3.9), (19.2, 4.55, 3.65), (20.0, 4.6, 3.75), (21.5, 5.3, 4.4), (23.8, 5.9, 4.85), (25.8, 5.75, 4.5), (27.4, 4.7, 3.7), (28.3, 3.3, 3.0)], sq=2.3, rot=-TW)   # belt, waist, breastplate
# (v3, user: 'diese 2 vertikalen Linien sind noch komisch': the keel down the breastplate and the ridge down the helm's face were stuck-on rods: removed)
lathe(T((0.0, 0.2, 0))[:2], [(27.7, 4.0, 3.7), (28.4, 4.35, 4.0), (29.1, 4.2, 3.9), (29.6, 3.6, 3.4)], sq=2.0, rot=-TW)                                    # the collar (yellow)
HZ = g('helm_z', 28.9); HC = T((-0.5, 0.5, 0))[:2]
lathe(HC, [(HZ, 3.9, 4.2), (HZ + 0.8, 4.6, 4.9), (HZ + 2.9, 4.85, 5.2), (HZ + 4.4, 4.85, 5.2), (HZ + 5.3, 4.7, 5.05),
           (HZ + 6.8, 4.1, 4.4), (HZ + 7.9, 2.9, 3.1), (HZ + 8.6, 1.4, 1.5), (HZ + 8.8, 0.3, 0.3)], sq=2.0, rot=-TW)                                         # great helm: a smooth skull (v5: the eye slit is NOT a groove all around any more; it is cut into the visor's front only, as drawn)
# v4 (user: 'das sieht mir noch nicht nach einem Helm mit Visier aus'): a VISOR as its own plate over the face: it stands out from the helm, a blunt
# snout (deepest a little below its middle, front centre), its upper edge under the eye slit (the slit = the dark gap between the visor and the brow rim),
# hinged at the temples (round pivots); a row of breath slots as small sunk dents is too fine for this size: left out. Plus a low comb over the skull.
def visor(c, rs, rf, z0, z1, depth, half=78.0, nphi=36, nz=40, t=0.35, slit=(0.68, 0.84), slit_half=52.0):
    """shell over the helm's front: angles -half .. +half degrees around the vertical axis through c (0 = the front), heights z0 .. z1. Below the EYE
    SLIT it is the snout (stands `t` + up to `depth` in front of the helm, deepest front centre a little below its middle), above the slit a brow plate;
    the slit itself (the share `slit` of the height, only within +-slit_half degrees = over the eyes, user: 'nur bei der Augenpartie') lies sunk to the
    helm's surface = a dark gap in the front only"""
    vs, fs = [], []; sm = lambda a, b, x: (lambda q: q * q * (3 - 2 * q))(max(0.0, min(1.0, (x - a) / (b - a))))
    def P(i, j, outer):
        ph = math.radians(-half + 2 * half * i / nphi); v = j / nz; z = z0 + (z1 - z0) * v
        w = math.cos(math.radians(90.0) * (ph / math.radians(half))) ** 1.7                       # 1 at the front centre, 0 at the pivots: a pointed snout, flat cheeks
        vv = min(1.0, v / slit[0]); prof = math.sin(math.pi * min(1.0, max(0.0, (vv + 0.12) / 1.12)) ** 0.8)   # the snout's height profile (below the slit)
        r = t + (depth * w * (0.25 + 0.75 * prof) if v <= slit[0] else 0.2 + 0.45 * w)             # snout / brow plate
        inslit = sm(slit[0] - 0.03, slit[0] + 0.02, v) * (1 - sm(slit[1] - 0.02, slit[1] + 0.03, v)) * (1 - sm(slit_half - 8.0, slit_half, abs(math.degrees(ph))))
        r = r * (1 - inslit) + 0.02 * inslit
        if not outer: r = -0.15
        return T((HCU[0] + (rs + r) * math.sin(ph), HCU[1] + (rf + r) * math.cos(ph), z))
    for outer in (1, 0):
        for j in range(nz + 1):
            for i in range(nphi + 1): vs.append(P(i, j, outer))
    R = (nz + 1) * (nphi + 1); idx = lambda i, j, o: (0 if o else R) + j * (nphi + 1) + i
    for j in range(nz):
        for i in range(nphi):
            fs.append((idx(i, j, 1), idx(i + 1, j, 1), idx(i + 1, j + 1, 1), idx(i, j + 1, 1))); fs.append((idx(i, j, 0), idx(i, j + 1, 0), idx(i + 1, j + 1, 0), idx(i + 1, j, 0)))
    for i in range(nphi):   # lower / upper edge
        fs.append((idx(i, 0, 1), idx(i, 0, 0), idx(i + 1, 0, 0), idx(i + 1, 0, 1))); fs.append((idx(i, nz, 1), idx(i + 1, nz, 1), idx(i + 1, nz, 0), idx(i, nz, 0)))
    for j in range(nz):     # the two ends
        fs.append((idx(0, j, 1), idx(0, j + 1, 1), idx(0, j + 1, 0), idx(0, j, 0))); fs.append((idx(nphi, j, 1), idx(nphi, j, 0), idx(nphi, j + 1, 0), idx(nphi, j + 1, 1)))
    add(vs, fs)
HCU = (-0.5, 0.5)
visor(HCU, 4.85, 5.2, HZ + 0.5, HZ + 5.4, g('visor_depth', 2.4))
for sg in (-1, 1): ellipsoid(T((HCU[0] + sg * 5.15, HCU[1] + 0.9, HZ + 3.0)), (0.45, 0.85, 0.85), nu=12, nv=8, rot=-TW)   # the visor's pivots at the temples
capsule(T((HCU[0], HCU[1] + 3.6, HZ + 7.3)), T((HCU[0], HCU[1] - 3.8, HZ + 7.5)), 0.55, 0.5, nu=8, cap=3)                # a low comb over the skull
# v6 (user: 'oben am Helm sind es Federn ... sieht im Sprite wie 2 Stueck aus'): TWO FEATHERS as drawn: a short upright one at the front of the top and a
# long one sweeping over to the figure's left / back with a drooping tip. A feather = a thin curved blade (quill at the base, the vane widest before the
# middle, a pointed tip, a raised shaft down its middle, a little cupped), its flat side turned to the game camera (the drawing shows their full width)
def feather(path, wmax, n=26, m=9, thick=0.16):
    pts = [T(p) for p in path]                                         # in the placed body frame (= world offsets at yaw 0)
    def at(a):                                                         # Catmull-Rom through the path points
        x = a * (len(pts) - 1); i = min(int(x), len(pts) - 2); u = x - i
        p0, p1, p2, p3 = pts[max(0, i - 1)], pts[i], pts[i + 1], pts[min(len(pts) - 1, i + 2)]
        return tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * u + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * u * u + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * u ** 3) for k in range(3))
    view = (0.577, 0.577, 0.577); vs, fs = [], []
    for j in range(n + 1):
        a = j / n; p = at(a); q = at(min(1.0, a + 0.02)); o = at(max(0.0, a - 0.02)); t = tuple(q[k] - o[k] for k in range(3)); l = math.sqrt(sum(x * x for x in t)); t = tuple(x / l for x in t)
        wd = (t[1] * view[2] - t[2] * view[1], t[2] * view[0] - t[0] * view[2], t[0] * view[1] - t[1] * view[0]); l = math.sqrt(sum(x * x for x in wd)); wd = tuple(x / l for x in wd)
        nr = (wd[1] * t[2] - wd[2] * t[1], wd[2] * t[0] - wd[0] * t[2], wd[0] * t[1] - wd[1] * t[0])   # towards the camera
        w = 0.22 + (wmax - 0.22) * (max(0.0, math.sin(math.pi * min(1.0, max(0.0, (a - 0.08) / 0.92)) ** 0.75)) ** 0.8)   # a bare quill, then the vane
        if a > 0.97: w *= (1.0 - a) / 0.03 * 0.8 + 0.2
        for side in (1, -1):
            for i in range(m + 1):
                u = -1.0 + 2.0 * i / m; h = thick * (1 - u * u) + (0.2 * math.exp(-(u / 0.16) ** 2) if side > 0 else 0.0) + 0.0; cup = -0.22 * u * u * w / wmax
                vs.append(tuple(p[k] + wd[k] * u * w / 2 + nr[k] * (side * h + cup) for k in range(3)))
    R = 2 * (m + 1)
    for j in range(n):
        for i in range(m):
            a_ = j * R + i; fs.append((a_, a_ + 1, a_ + R + 1, a_ + R)); b_ = j * R + (m + 1) + i; fs.append((b_, b_ + R, b_ + R + 1, b_ + 1))
    for i in range(m): fs.append((i, (m + 1) + i, (m + 1) + i + 1, i + 1)); e = n * R; fs.append((e + i, e + i + 1, e + (m + 1) + i + 1, e + (m + 1) + i))
    V.extend(vs); F.extend([tuple(x + len(V) - len(vs) for x in f) for f in fs])   # already placed: bypass T again (see RAW below)
    RAW.update(range(len(V) - len(vs), len(V)))
RAW = set()
feather(g('feather1', [(-0.6, 1.0, HZ + 8.2), (-0.8, 1.2, HZ + 9.4), (-0.9, 1.3, HZ + 10.5), (-0.7, 1.2, HZ + 11.4)]), 1.8, n=16)
feather(g('feather2', [(0.2, 0.2, HZ + 8.3), (0.9, -0.5, HZ + 9.4), (2.3, -1.5, HZ + 9.8), (3.7, -2.4, HZ + 9.1), (4.6, -3.0, HZ + 7.7)]), 2.5, n=30)
for sg, sx in ((-1, -6.4), (1, 6.9)):                                                                                                                       # pauldrons: a cap + two lames down the arm
    ellipsoid(T((sx, 0.1, 26.6 if sg < 0 else 27.3)), (3.2 if sg < 0 else 3.5, 3.4, 2.5 if sg < 0 else 2.9), rot=-TW)
    ellipsoid(T((sx + sg * 0.7, 0.1, 25.0)), (2.75, 2.9, 1.5), rot=-TW); ellipsoid(T((sx + sg * 1.0, 0.1, 23.8)), (2.45, 2.6, 1.3), rot=-TW)
LX, LY = g('lance', [-8.5, 2.5]); SX, SY, SZ = g('shield', [10.0, -0.5, 16.2]); YAW = g('yaw', 0.0)
ct, st = math.cos(math.radians(YAW)), math.sin(math.radians(YAW)); BX, BY = g('body', [1.8, -0.5])
def tobody(wx, wy): dx, dy = wx - BX, wy - BY; return (dx * ct - dy * st, dx * st + dy * ct)   # world offset -> (s, f)
ls, lf = tobody(LX, LY)
capsule((ls, lf, 0.5), (ls, lf, 1.6), 1.25, 1.0, nu=10, cap=2)                                      # the lance: butt cap
capsule((ls, lf, 0.6), (ls, lf, 27.2), 1.0, 0.95, nu=12, cap=2)                                     # shaft
for dz, rr in ((25.2, 1.6), (26.6, 1.75)): ellipsoid((ls, lf, dz), (rr, rr, 1.0), nu=14, nv=8)       # two tufts of the tassel
capsule((ls, lf, 27.4), (ls, lf, 28.6), 1.1, 0.8, nu=10, cap=2)                                     # the socket
capsule((ls, lf, 29.0), (ls, lf, 37.2), 1.95, 0.25, nu=12, cap=2, flat=0.34)                        # the leaf-shaped head
capsule((ls, lf, 28.8), (ls, lf, 36.4), 0.5, 0.2, nu=8, cap=2)                                      # its midrib
hand = (ls + 0.6, lf - 0.3, 15.6); el = T((-6.9, 1.3, 20.4))
capsule(T((-6.6, 0.1, 25.4)), el, 1.75, 1.6); ellipsoid(el, (1.9, 2.0, 1.8))                        # right upper arm, couter
capsule(el, (hand[0], hand[1], hand[2] + 2.6), 1.65, 1.5)                                           # forearm
capsule((hand[0], hand[1], hand[2] + 3.2), (hand[0], hand[1], hand[2] + 1.2), 2.1, 1.7, nu=14, cap=2)   # the gauntlet's flared cuff
ellipsoid((ls + 0.1, lf + 0.1, hand[2] - 0.2), (2.0, 2.0, 1.75))                                    # the fist around the shaft
ss, sf = tobody(SX, SY); el2 = T((8.2, 0.6, 20.8))
capsule(T((6.9, 0.1, 25.4)), el2, 1.85, 1.7); ellipsoid(el2, (2.0, 2.1, 1.9)); capsule(el2, (ss - 1.2, sf + 0.6, SZ + 1.0), 1.65, 1.45)   # left arm behind the shield
KITE = [(-4.3, 8.0), (-3.2, 8.5), (-1.6, 8.8), (0.0, 8.9), (1.6, 8.8), (3.2, 8.5), (4.3, 8.0), (4.6, 6.0), (4.6, 4.0), (4.5, 2.0), (4.2, 0.0), (3.6, -2.3), (2.8, -4.5), (1.5, -7.0), (0.0, -9.2),
        (-1.5, -7.0), (-2.8, -4.5), (-3.6, -2.3), (-4.2, 0.0), (-4.5, 2.0), (-4.6, 4.0), (-4.6, 6.0)]
plate((ss, sf, SZ), g('shield_yaw', 72.0) - YAW, KITE, 1.1, bend=0.035)

# ---- placement: body frame -> world (the figure's left L = (cos yaw, -sin yaw), its front = (sin yaw, cos yaw)) ---------------------------------------
CX, CY, FLO = g('cx', 488.0), g('cy', 424.0), g('floor', 0.0)
XMIN, XMAX, YMIN = g('xmin', -1e9), g('xmax', 1e9), g('ymin', CY - 7.9)
def W(p):
    """body frame -> world. Nothing may enter a wall block beside / behind the cell (the light treats such cells as wall up to the room's top): a vertex
    beyond xmin / xmax / ymin SLIDES ALONG THE VIEW RAY (1, 1, 1) back to the bound, so the game picture of the model stays the same"""
    s, f, z = p; x, y, z = CX + BX + s * ct + f * st, CY + BY - s * st + f * ct, FLO + max(0.0, z) * H
    if x > XMAX: d = x - XMAX; x, y, z = x - d, y - d, z - d
    if x < XMIN: d = XMIN - x; x, y, z = x + d, y + d, z + d
    if y < YMIN: d = YMIN - y; x, y, z = x + d, y + d, z + d
    return (x, y, max(FLO, z))
with open(sys.argv[1], 'w') as fo:
    fo.write("# armour knight (remake/recipes/knight/knight.py): our own geometry from parts. GAME coordinates x east, y south, z up, world units.\n")
    for p in V: fo.write('v %.3f %.3f %.3f\n' % W(p))
    for q in F: fo.write('f ' + ' '.join(str(i + 1) for i in q) + '\n')
print('knight', len(V), 'verts', len(F), 'faces')
