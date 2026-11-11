# wing.py OUT : the two wings as one clean mesh in the plane x = XW (behind the body, joined across the back), built on a 1/4 pixel grid of the wing region
# (wing pixels + the statue's upper body pixels behind which the wings join); thickness tapers to 0 at the smoothed outline; FEATHERS = analytic relief:
# bands fanning out from each wing root (rounded ridges) in two rows (coverts, primaries) with a small step between rows; CUP along the view ray (1, 1, 1)
import json, math, sys
sys.path.insert(0, '/home/deck/ProjectL/remake/lib'); import furniture as F
P = json.load(open('/home/deck/lktest/sculpt/params.json')); g = lambda k, d: P.get(k, d)
A = F.CHURCH_ANGEL4; AX, AY = A['axis']; XW = A['wing_x']; AU = AX - AY + 1184.0; V0p = A['v0']; U0, V0 = 1064, 280
mask = {tuple(p) for p in json.load(open('/home/deck/lktest/angel3/mask.json'))}
wing = {(int(math.floor(AU + du)) - U0, V0p + v - V0) for du, v in A['wing']}   # window pixel coords
# MIRRORED WINGS (user 2026-11-10: 'gespiegelt und parallel zur Wand, links soll gleich sein wie rechts', option 1 = the same height): in the plane x = XW the
# right wing = the left one mirrored at y = YC (the body axis in the plane, 444.5: fits by itself); the template = the left side's statue pixels that also
# lie inside the right side's statue pixels when mirrored (a part behind the head / body is hidden), next to the drawn left wing. The game picture of the
# drawn wings is NOT kept exactly any more (the artist drew the left wing ~6 lower): remake model only, the light keeps CHURCH_ANGEL4.
YC = g('wing_yc', 444.5)
def _toplane(u, v): U = U0 + u + 0.5; Vv = V0 + v + 0.5; y = XW + 1184 - U; return y, (XW + y) / 2 - Vv
def _topix(y, z): U = XW - y + 1184; Vv = (XW + y) / 2 - z; return int(math.floor(U - U0)), int(math.floor(Vv - V0))
def _mir(p): y, z = _toplane(*p); return _topix(2 * YC - y, z)
if g('mirror', True):
    _ax = AU - U0; _Lw = {p for p in wing if p[0] + 0.5 < _ax}
    _aL = {p for p in mask if p[0] + 0.5 < _ax}; _aR = {p for p in mask if p[0] + 0.5 > _ax}; _mR = {_mir(p) for p in _aR}
    _T = {p for p in _aL if p in _mR and any((p[0] + a, p[1] + b) in _Lw for a in (-1, 0, 1) for b in (-1, 0, 1))}
    wing = _T | {_mir(p) for p in _T}
vtop = max(v for u, v in wing)
near = {p for p in mask if p[1] <= g('join_v', 70) and any((p[0] + a, p[1] + b) in wing for a in range(-g('join_d', 3), g('join_d', 3) + 1) for b in range(-2, 3))}
region = wing | near   # the wings join the back only near their roots (v3's straight cut at a row made a rectangular notch, user: 'schlechter')
# each wing continues BEHIND the body down to the shoulder (the drawing hides its lower part behind the head / body): a stem below its root
def _root(side):
    px = [p for p in wing if (p[0] + U0 + 0.5 - AU < 0) == (side < 0)]; vm = sum(p[1] for p in px) / len(px)
    return min(px, key=lambda p: abs(p[0] + U0 + 0.5 - AU) + 0.3 * abs(p[1] - vm))
for sd in (-1, 1):
    ru_, rv_ = _root(sd)
    region |= {p for p in mask if abs(p[0] - ru_) <= g('stem_w', 3) and rv_ <= p[1] <= g('shoulder_v', 66)}
S = g('wgrid', 6); SIG = g('wsig', 0.7)
us = [p[0] for p in region]; vs = [p[1] for p in region]; gu0, gv0 = min(us) - 3, min(vs) - 3; GW, GH = (max(us) - gu0 + 7) * S, (max(vs) - gv0 + 7) * S
base = [[1.0 if (gu0 + i // S, gv0 + j // S) in region else 0.0 for i in range(GW)] for j in range(GH)]
R = int(3 * SIG * S) + 1; ker = [math.exp(-0.5 * (k / (SIG * S)) ** 2) for k in range(-R, R + 1)]; ks = sum(ker); ker = [k / ks for k in ker]
tmp = [[sum(ker[k + R] * row[min(GW - 1, max(0, i + k))] for k in range(-R, R + 1)) for i in range(GW)] for row in base]
fld = [[sum(ker[k + R] * tmp[min(GH - 1, max(0, j + k))][i] for k in range(-R, R + 1)) for i in range(GW)] for j in range(GH)]
inside = [[fld[j][i] >= 0.5 for i in range(GW)] for j in range(GH)]
# distance to the outline (in pixels) by a simple chamfer pass on the grid
INF = 1e9; dist = [[(INF if inside[j][i] else 0.0) for i in range(GW)] for j in range(GH)]
for _ in range(2):
    for j in range(GH):
        for i in range(GW):
            if dist[j][i]:
                for a, b, w in ((-1, 0, 1), (0, -1, 1), (-1, -1, 1.414), (1, -1, 1.414)):
                    if 0 <= i + a < GW and 0 <= j + b < GH: dist[j][i] = min(dist[j][i], dist[j + b][i + a] + w)
    for j in range(GH - 1, -1, -1):
        for i in range(GW - 1, -1, -1):
            if dist[j][i]:
                for a, b, w in ((1, 0, 1), (0, 1, 1), (1, 1, 1.414), (-1, 1, 1.414)):
                    if 0 <= i + a < GW and 0 <= j + b < GH: dist[j][i] = min(dist[j][i], dist[j + b][i + a] + w)
# wing roots (picture coords) at the shoulders, one per side
def _proot():   # the left wing root in plane coordinates (y, z); the right one is its mirror
    px = [p for p in wing if p[0] + U0 + 0.5 - AU < 0]; vm = sum(p[1] for p in px) / len(px)
    q = min(px, key=lambda p: abs(p[0] + U0 + 0.5 - AU) + 0.3 * abs(p[1] - vm)); return _toplane(*q)
PR = _proot(); AXC = AU - U0
RT = {-1: _topix(*PR), 1: _topix(2 * YC - PR[0], PR[1])}
# v11 FEATHERS (user: 'schau dir die Fluegel nochmal an'; soft radial bands on a thin sheet read as a scallop shell): a fan from the wing root in three
# rows like a real wing (short COVERTS at the root on top, then SECONDARIES, then the long PRIMARIES to the outline); every feather = a rounded blade
# lying like a SHINGLE over its neighbour (high edge -> low edge, then a crisp step up), a fine shaft down its middle, a ROUNDED TIP that ends with a
# step down onto the next row; the rows follow the wing's own reach in every direction (root -> outline), not circles
A0 = g('wr_a', 3.0); Z0 = g('wr_z', 62.0)   # the fan's root at the SHOULDER (the measured 'root' lies in the middle of the wing: a fan around it read as a shell)
def _ins(y, z):
    U = XW - y + 1184.0; Vv = (XW + y) / 2.0 - z; i = int((U - U0 - gu0) * S); j = int((Vv - V0 - gv0) * S)
    return 0 <= i < GW and 0 <= j < GH and inside[j][i]
_side = 1 if PR[0] > YC else -1
def _reach(th):
    r = 1.0
    while r < 60 and (_ins(YC + _side * (A0 + r * math.cos(th)), Z0 + r * math.sin(th)) or r < 3.0): r += 0.25
    return r
NA = 240; _L = [_reach(-math.pi + 2 * math.pi * k / NA) for k in range(NA)]
_L = [sum(_L[(k + d) % NA] * w for d, w in ((-3, 1), (-2, 2), (-1, 3), (0, 4), (1, 3), (2, 2), (3, 1))) / 16.0 for k in range(NA)]   # smoothed
def reach(th): x = (th + math.pi) / (2 * math.pi) * NA; k = int(math.floor(x)); t = x - k; return _L[k % NA] * (1 - t) + _L[(k + 1) % NA] * t
sm_ = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
def blade(x, wu=3.0):   # cross-section of one feather, x 0 .. 1 across it: rounded, tilted like a shingle, a fine shaft
    return 0.55 * math.sqrt(max(0.0, 1.0 - (2 * x - 1) ** 2)) + 0.45 * (1.0 - x) * sm_(x * wu / 0.7) + 0.14 * math.exp(-((x - 0.5) * wu / 0.22) ** 2)   # wu = the feather's width in units: the step and the shaft keep an absolute width (no stairs on the grid)
ROWS = g('rows3', [0.34, 0.62]); NB = g('fan3', 0.2); TIP = g('tip', 0.09); FH = g('feather_h', 0.55); RS = g('row_step', 0.38)
def relief(cu, cv):   # in the plane, mirrored about y = YC: the same feathers on both sides
    y, z = _toplane(cu - 0.5, cv - 0.5); a = abs(y - YC); dx, dy = a - A0, z - Z0; rr = math.hypot(dx, dy); th = math.atan2(dy, dx); L = reach(th); q = rr / L
    fade = sm_((a - 2.5) / 3.0) * sm_((rr - 2.0) / 4.0)   # the feathers fade in away from the body and the root (no cliff)
    h = 0.0; k = 0
    for k in range(3):
        nb = NB; x = (th / nb + 0.5 * k) % 1.0
        if k == 2: h = FH * blade(x, nb * rr) - RS * k; break
        end = ROWS[k] + TIP * (1.0 - (2 * x - 1) ** 2)            # the rounded tip: the middle of the feather reaches further
        if q < end:
            t = sm_((end - q) * L / 0.8)                           # the step at the tip (0.5 units wide), down onto the next row
            nb2 = NB; x2 = (th / nb2 + 0.5 * (k + 1)) % 1.0; below = FH * blade(x2, nb * rr) - RS * (k + 1)
            h = below + t * (FH * blade(x, nb * rr) - RS * k - below); break
    return fade * (h + RS * 2), rr
def thick(d): return min(g('wing_t', 1.3), 0.03 + d * 0.55 / S) if d > 0 else 0.0
verts = []; idx = {}
def vid(i, j, side):
    k = (i, j, side)
    if k in idx: return idx[k]
    cu = gu0 + (i + 0.5) / S; cv = gv0 + (j + 0.5) / S; d = dist[j][i]; t = thick(d) / 2
    rel, rr = relief(cu, cv)
    off = side * t + (rel if side > 0 else -g('back_rel', 0.6) * rel) * min(1.0, d / (2 * S))   # feathers on both faces (the back a bit flatter)
    if d <= 1.5:   # boundary vertex: slide onto the smoothed outline (field 0.5) along the field gradient
        for _ in range(6):
            fx = (cu - gu0) * S - 0.5; fy = (cv - gv0) * S - 0.5; ii = min(GW - 2, max(0, int(fx))); jj = min(GH - 2, max(0, int(fy))); a_ = fx - ii; b_ = fy - jj
            fv = (fld[jj][ii] * (1 - a_) + fld[jj][ii + 1] * a_) * (1 - b_) + (fld[jj + 1][ii] * (1 - a_) + fld[jj + 1][ii + 1] * a_) * b_
            gx = ((fld[jj][ii + 1] - fld[jj][ii]) * (1 - b_) + (fld[jj + 1][ii + 1] - fld[jj + 1][ii]) * b_) * S; gy = ((fld[jj + 1][ii] - fld[jj][ii]) * (1 - a_) + (fld[jj + 1][ii + 1] - fld[jj][ii + 1]) * a_) * S
            gl = (gx * gx + gy * gy) ** 0.5
            if gl < 1e-6: break
            st = max(-0.3, min(0.3, (0.5 - fv) / gl)); cu += st * gx / gl; cv += st * gy / gl
    U = U0 + cu; Vp = V0 + cv; y = XW + 1184.0 - U; z = (XW + y) / 2.0 - Vp
    _y, _z = _toplane(cu - 0.5, cv - 0.5); _yy = YC - abs(_y - YC); cupt = g('cup', 0.012) * ((_yy - PR[0]) ** 2 + (_z - PR[1]) ** 2) if abs(_y - YC) > 1.0 else 0.0
    T = cupt + off   # along the view ray: the picture point stays; but thickness should be along x (the plane normal): use x for the thickness, ray for the cup
    if g('mirror', True): p = (XW + g('cupn', 0.004) * (cupt / g('cup', 0.012)) + off, y, z)   # MIRRORED (true 3D symmetry): depth along the plane normal x, a small cup (tips ~2 forward)
    else: p = (XW + T, y + T, z + T)   # thickness, feather relief and cup all along the view ray: the game picture stays exactly the drawn wing
    idx[k] = len(verts); verts.append(p); return idx[k]
faces = []
for j in range(GH - 1):
    for i in range(GW - 1):
        if inside[j][i] and inside[j][i + 1] and inside[j + 1][i] and inside[j + 1][i + 1]:
            faces.append((vid(i, j, 1), vid(i + 1, j, 1), vid(i + 1, j + 1, 1), vid(i, j + 1, 1)))
            faces.append((vid(i, j, -1), vid(i, j + 1, -1), vid(i + 1, j + 1, -1), vid(i + 1, j, -1)))
# side walls along the boundary of the quad region
cells = {(i, j) for j in range(GH - 1) for i in range(GW - 1) if inside[j][i] and inside[j][i + 1] and inside[j + 1][i] and inside[j + 1][i + 1]}
for (i, j) in cells:
    for (ni, nj), (a, b) in (((i, j - 1), ((i, j), (i + 1, j))), ((i + 1, j), ((i + 1, j), (i + 1, j + 1))), ((i, j + 1), ((i + 1, j + 1), (i, j + 1))), ((i - 1, j), ((i, j + 1), (i, j)))):
        if (ni, nj) not in cells: faces.append((vid(a[0], a[1], 1), vid(a[0], a[1], -1), vid(b[0], b[1], -1), vid(b[0], b[1], 1)))
with open(sys.argv[1], 'w') as fo:
    for p in verts: fo.write('v %.4f %.4f %.4f\n' % p)
    for q in faces: fo.write('f ' + ' '.join(str(i + 1) for i in q) + '\n')
print('wing', len(verts), 'verts', len(faces), 'faces', 'roots', RT)
if len(sys.argv) > 2:   # debug: the wing region in plane coordinates (a = distance from the axis, z), one char per unit
    print('root a0 %.1f z0 %.1f' % (A0, Z0))
    for zz in range(88, 50, -1): print('%3d ' % zz + ''.join('#' if _ins(YC + _side * (aa + 0.5), zz + 0.5) else '.' for aa in range(0, 36)))
