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
def plate(c, yaw, outline, t, bend=0.0, n=10):
    """a plate (the shield): `outline` = polygon (u across, v up) in its own plane, centre c, its face turned `yaw` degrees from the front (+f) towards the
    left (+s), thickness t, bent about its vertical middle line (the edges `bend` units back at u = +-1 ... scaled by u^2)"""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)); nrm = (sy, cy); acr = (cy, -sy)   # normal / across in (s, f)
    def pt(u, v, w): w2 = w - bend * u * u; return (c[0] + acr[0] * u + nrm[0] * w2, c[1] + acr[1] * u + nrm[1] * w2, c[2] + v)
    m = len(outline); cu = sum(p[0] for p in outline) / m; cv = sum(p[1] for p in outline) / m; vs, fs = [], []
    for side, w in ((0, t / 2), (1, -t / 2)):
        for k in range(n + 1):
            for (u, v) in outline: a = k / n; vs.append(pt(cu + (u - cu) * a, cv + (v - cv) * a, w + (0.35 * t * (1 - a * a) if side == 0 else 0.0)))   # the face a little domed
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
for sg in (-1, 1):
    hip = (sg * 3.2, 0.0, 16.5); knee = (sg * 3.8, 0.9, 9.3); ank = (sg * 3.9, 0.2, 2.6)
    ellipsoid((sg * 4.0, 2.9, 1.5), (1.9, 4.2, 1.5), rot=-sg * g('splay', 22.0))                 # sabaton, the toe forward
    capsule(ank, knee, 1.75, 2.15)                                                    # greave
    ellipsoid((knee[0], knee[1] + 0.9, knee[2] + 0.2), (2.0, 1.7, 1.9))               # knee cop
    capsule(knee, hip, 2.25, 2.75)                                                    # cuisse
lathe((0.0, 0.2), [(13.2, 5.9, 4.6), (14.2, 6.0, 4.7), (16.5, 5.5, 4.3), (18.6, 4.9, 3.9)], sq=2.3)                                  # fauld (the skirt of plates)
lathe(T((0.0, 0.3, 0))[:2], [(18.2, 4.6, 3.6), (19.5, 4.6, 3.7), (21.5, 5.3, 4.3), (24.0, 5.9, 4.7), (26.0, 5.7, 4.4), (27.6, 4.6, 3.6), (28.4, 3.2, 2.9)], sq=2.3, rot=-TW)   # waist, breastplate, shoulders
lathe(T((0.0, 0.2, 0))[:2], [(27.8, 3.9, 3.6), (28.6, 4.1, 3.8), (29.4, 3.6, 3.4)], sq=2.0, rot=-TW)                                                     # the collar (yellow)
HZ = g('helm_z', 28.9)
lathe(T((-0.5, 0.5, 0))[:2], [(HZ, 3.9, 4.2), (HZ + 0.8, 4.6, 4.9), (HZ + 3.0, 4.9, 5.2), (HZ + 5.2, 4.7, 5.0), (HZ + 6.8, 4.0, 4.3), (HZ + 7.9, 2.8, 3.0), (HZ + 8.6, 1.3, 1.4), (HZ + 8.8, 0.3, 0.3)], sq=2.0, rot=-TW)   # great helm
capsule(T((-0.5, 5.3, HZ + 3.7)), T((-0.5, 5.5, HZ + 1.6)), 0.55, 0.45)                                                                        # the nose ridge of the visor
for k in range(6):                                                                                                                     # the crest: a plume from the top sweeping back
    a = k / 5.0; ellipsoid(T((-0.5, 2.0 - 7.5 * a, HZ + 9.2 + 2.1 * math.sin(math.pi * (0.25 + 0.6 * a)) - 0.9 * a)), (0.9, 1.9, 1.6 - 0.4 * a), nu=12, nv=8, rot=-TW)
ellipsoid(T((-6.4, 0.2, 26.6)), (3.1, 3.3, 2.5), rot=-TW); ellipsoid(T((6.9, 0.0, 26.5)), (3.4, 3.4, 2.6), rot=-TW)   # pauldrons: the left one (over the shield arm) is the big yellow-rimmed plate                                                                   # pauldrons
# the lance and the shield are measured in the ROOM (offsets from the cell centre): here they come in body-frame terms through the placement below
LX, LY = g('lance', [-8.5, 2.5]); SX, SY, SZ = g('shield', [10.7, -0.5, 16.2]); YAW = g('yaw', 0.0)
ct, st = math.cos(math.radians(YAW)), math.sin(math.radians(YAW)); BX, BY = g('body', [1.8, -0.5])
def tobody(wx, wy): dx, dy = wx - BX, wy - BY; return (dx * ct - dy * st, dx * st + dy * ct)   # world offset -> (s, f)
ls, lf = tobody(LX, LY)
capsule((ls, lf, 0.6), (ls, lf, 27.0), 1.2, 1.2, nu=10, cap=2)                                    # the lance's shaft
ellipsoid((ls, lf, 26.0), (2.0, 2.0, 1.6), nu=12, nv=8)                                             # the tassel
capsule((ls, lf, 27.8), (ls, lf, 37.2), 1.9, 0.3, nu=10, cap=2, flat=0.38)                        # the leaf-shaped head
hand = (ls + 0.7, lf - 0.4, 15.6); el = T((-7.5, 0.9, 20.6))
capsule(T((-6.9, 0.1, 25.8)), el, 1.9, 1.75); capsule(el, hand, 1.7, 1.55); ellipsoid(hand, (2.2, 2.1, 2.3))   # right arm down to the gauntlet on the shaft
ss, sf = tobody(SX, SY); el2 = T((8.2, 0.6, 20.8))
capsule(T((6.9, 0.1, 25.8)), el2, 1.9, 1.75); capsule(el2, (ss - 1.2, sf + 0.6, SZ + 1.0), 1.7, 1.5)             # left arm behind the shield
KITE = [(-4.3, 8.0), (-2.0, 8.7), (0.0, 8.9), (2.0, 8.7), (4.3, 8.0), (4.6, 4.0), (4.2, 0.0), (2.8, -4.5), (0.0, -9.2), (-2.8, -4.5), (-4.2, 0.0), (-4.6, 4.0)]
plate((ss, sf, SZ), g('shield_yaw', 72.0) - YAW, KITE, 1.0, bend=0.03)

# ---- placement: body frame -> world (the figure's left L = (cos yaw, -sin yaw), its front = (sin yaw, cos yaw)) ---------------------------------------
CX, CY, FLO = g('cx', 488.0), g('cy', 424.0), g('floor', 0.0)
def W(p): s, f, z = p; return (CX + BX + s * ct + f * st, CY + BY - s * st + f * ct, FLO + max(0.0, z) * H)
with open(sys.argv[1], 'w') as fo:
    fo.write("# armour knight (remake/recipes/knight/knight.py): our own geometry from parts. GAME coordinates x east, y south, z up, world units.\n")
    for p in V: fo.write('v %.3f %.3f %.3f\n' % W(p))
    for q in F: fo.write('f ' + ' '.join(str(i + 1) for i in q) + '\n')
print('knight', len(V), 'verts', len(F), 'faces')
