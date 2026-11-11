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
# v13 (user: the figure faces out of the wall, 'die Fluegel muessen am Ruecken anliegen, parallel zum Koerper', 'kein Loch ... eine komplette Form'): each
# wing = ITS OWN drawn pixels in the wall plane (no mirroring: the drawing is the reference, also for the light) made COMPLETE: the part the body hides in
# the picture is filled across the back (statue pixels that lie between the two wings in the plane), small notches closed
if g('complete', True):
    YB = AY   # the body's axis in the plane (the figure faces +x, its back on the plane)
    def _pl(p): return _toplane(*p)
    Lw = {p for p in wing if _pl(p)[0] > YB}; Rw = {p for p in wing if _pl(p)[0] <= YB}
    lmin = {}; rmax = {}
    for p in wing:
        y, z = _pl(p); k = int(math.floor(z))
        if y > YB: lmin[k] = min(lmin.get(k, 1e9), y)
        if y <= YB + 2 and p in wing: pass
    for p in wing:
        y, z = _pl(p); k = int(math.floor(z))
        if y < g('wing_rsplit', 446.0): rmax[k] = max(rmax.get(k, -1e9), y)
    zlo = g('fill_zlo', 57.0)
    def _btw(p):
        y, z = _pl(p); k = int(math.floor(z))
        # the bridge across the back up to the shoulders in the middle, rising to the wings' full height from 1.5 to 6 units beside the body's axis:
        # v16 (user: 'der rechte Fluegel wirkt chaotischer'): the head hides the right wing's inner top in the picture; it was a notch with a loose
        # lobe above it, and the feather fan's centre lay outside the wing. Now both wings are complete at the top inner corner.
        zt = g('fill_zhi', 69.5) + (76.0 - g('fill_zhi', 69.5)) * max(0.0, min(1.0, (abs(y - YB) - 1.5) / 4.5))
        if z < zlo or z > zt: return False
        lo = max((rmax.get(k + d, -1e9) for d in (-1, 0, 1)), default=-1e9); hi = min((lmin.get(k + d, 1e9) for d in (-1, 0, 1)), default=1e9)
        if lo < -1e8: lo = min(rmax.values())    # above / below a wing's drawn rows: from its innermost drawn column
        if hi > 1e8: hi = max(lmin.values())
        return lo - 1.5 <= y <= hi + 1.5
    mask1 = mask | {(p[0] + a_, p[1] + b_) for p in mask for a_, b_ in ((1, 0), (-1, 0), (0, 1), (0, -1))}   # + the dark outline pixels between head and wing
    fill = {p for p in mask1 if p not in wing and _btw(p) and (p in mask or _pl(p)[1] > g('fill_zhi', 69.5))}   # the outline pixels only up at the head (below they stuck out beside the waist)
    region = wing | fill
    for _ in range(g('close_n', 1)):   # closing: fill notches / single holes (only with statue pixels: the outline never grows past the drawing)
        grow = {(p[0] + a_, p[1] + b_) for p in region for a_ in (-1, 0, 1) for b_ in (-1, 0, 1)}
        region |= {p for p in grow if p in mask1 and sum(((p[0] + a_, p[1] + b_) in region) for a_, b_ in ((1, 0), (-1, 0), (0, 1), (0, -1))) >= 3}
    if g('mirror_left', True):   # v17 (user: 'der rechte Fluegel sollte gleich sein wie der linke, nur gespiegelt'): the completed LEFT half mirrored at the body's axis
        RL = {p for p in region if _pl(p)[0] >= YB}; us_ = [p[0] for p in mask]; vs_ = [p[1] for p in mask]; region = set(RL)
        for u_ in range(min(us_) - 30, max(us_) + 31):
            for v_ in range(min(vs_) - 20, max(vs_) + 21):
                y, z = _toplane(u_, v_)
                if y < YB and _topix(2 * YB - y, z) in RL: region.add((u_, v_))
    print('complete wings: drawn', len(wing), 'filled', len(region) - len(wing))
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
A0 = g('wr_a', 3.0); Z0 = g('wr_z', 63.0); YM = AY if g('complete', True) else YC   # the fan's root at the SHOULDER BLADE, the same on both sides of the body's axis
def _ins(y, z):
    U = XW - y + 1184.0; Vv = (XW + y) / 2.0 - z; i = int((U - U0 - gu0) * S); j = int((Vv - V0 - gv0) * S)
    return 0 <= i < GW and 0 <= j < GH and inside[j][i]
NA = 240
def _mk(sd):
    def _reach(th):
        r = 45.0   # from far out inwards: the LAST wing point on the ray (a notch on the way must not end the feather)
        while r > 3.0 and not _ins(YM + sd * (A0 + r * math.cos(th)), Z0 + r * math.sin(th)): r -= 0.25
        return r
    L_ = [_reach(-math.pi + 2 * math.pi * k / NA) for k in range(NA)]
    return [sum(L_[(k + d) % NA] * w for d, w in ((-3, 1), (-2, 2), (-1, 3), (0, 4), (1, 3), (2, 2), (3, 1))) / 16.0 for k in range(NA)]   # smoothed
_LS = {1: _mk(1), -1: _mk(-1)}
def reach(th, sd): x = (th + math.pi) / (2 * math.pi) * NA; k = int(math.floor(x)); t = x - k; L_ = _LS[sd]; return L_[k % NA] * (1 - t) + L_[(k + 1) % NA] * t
sm_ = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
def blade(x, wu=3.0):   # cross-section of one feather, x 0 .. 1 across it: rounded, tilted like a shingle, a fine shaft
    gr = -g('groove', 0.45) * (math.exp(-(x * wu / 0.4) ** 2) + math.exp(-((1.0 - x) * wu / 0.4) ** 2))   # v14: a narrow dark groove between two feathers (the drawn dark lines)
    return gr + 0.55 * math.sqrt(max(0.0, 1.0 - (2 * x - 1) ** 2)) + 0.45 * (1.0 - x) * sm_(x * wu / 1.1) + 0.14 * math.exp(-((x - 0.5) * wu / 0.22) ** 2)   # wu = the feather's width in units: the step and the shaft keep an absolute width (no stairs on the grid)
ROWS = g('rows3', [0.34, 0.62]); NB = g('fan3', 0.2); TIP = g('tip', 0.09); FH = g('feather_h', 0.55); RS = g('row_step', 0.38)
def relief(cu, cv):   # in the plane, mirrored about y = YC: the same feathers on both sides
    y, z = _toplane(cu - 0.5, cv - 0.5); a = abs(y - YM); dx, dy = a - A0, z - Z0; rr = math.hypot(dx, dy); th = math.atan2(dy, dx); L = reach(th, 1 if y > YM else -1); q = rr / L
    fade = sm_((a - 1.0) / 3.0) * sm_((rr - 4.0) / 5.0)   # smooth at the shoulder blade (the converging feathers made a star-shaped pit)   # the feathers fade in away from the body and the root (no cliff)
    h = 0.0; k = 0
    for k in range(len(ROWS) + 1):
        nb = NB; x = (th / nb + 0.5 * k) % 1.0
        if k == len(ROWS): h = FH * blade(x, nb * rr) - RS * k; break
        end = ROWS[k] + TIP * (1.0 - (2 * x - 1) ** 2)            # the rounded tip: the middle of the feather reaches further
        if q < end:
            t = sm_((end - q) * L / 1.2)                           # the step at the tip (0.5 units wide), down onto the next row
            nb2 = NB; x2 = (th / nb2 + 0.5 * (k + 1)) % 1.0; below = FH * blade(x2, nb * rr) - RS * (k + 1)
            h = below + t * (FH * blade(x, nb * rr) - RS * k - below); break
    return fade * (h + RS * len(ROWS)), rr
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
    _y, _z = _toplane(cu - 0.5, cv - 0.5); _yy = YC - abs(_y - YC); cupt = g('cup', 0.012) * ((abs(_y - AY) - 3.0) ** 2 + (_z - 63.0) ** 2) if g('complete', True) else (g('cup', 0.012) * ((_yy - PR[0]) ** 2 + (_z - PR[1]) ** 2) if abs(_y - YC) > 1.0 else 0.0)
    T = cupt + off   # along the view ray: the picture point stays; but thickness should be along x (the plane normal): use x for the thickness, ray for the cup
    if g('mirror', True) or g('complete', True): p = (XW + g('cupn', 0.004) * (cupt / g('cup', 0.012)) + off, y, z)   # MIRRORED (true 3D symmetry): depth along the plane normal x, a small cup (tips ~2 forward)
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
    for zz in range(80, 48, -1): print('%3d ' % zz + ''.join('#' if _ins(YM + aa + 0.5, zz + 0.5) else '.' for aa in range(30, -31, -1)))
