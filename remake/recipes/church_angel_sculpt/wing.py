# wing.py OUT : the two wings as one clean mesh in the plane x = XW (behind the body, joined across the back), built on a 1/4 pixel grid of the wing region
# (wing pixels + the statue's upper body pixels behind which the wings join); thickness tapers to 0 at the smoothed outline; FEATHERS = analytic relief:
# bands fanning out from each wing root (rounded ridges) in two rows (coverts, primaries) with a small step between rows; CUP along the view ray (1, 1, 1)
import json, math, sys
sys.path.insert(0, '/home/deck/ProjectL/remake/lib'); import furniture as F
P = json.load(open('/home/deck/lktest/sculpt/params.json')); g = lambda k, d: P.get(k, d)
A = F.CHURCH_ANGEL4; AX, AY = A['axis']; XW = A['wing_x']; AU = AX - AY + 1184.0; V0p = A['v0']; U0, V0 = 1064, 280
mask = {tuple(p) for p in json.load(open('/home/deck/lktest/angel3/mask.json'))}
wing = {(int(math.floor(AU + du)) - U0, V0p + v - V0) for du, v in A['wing']}   # window pixel coords
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
def root(side):
    px = [p for p in wing if (p[0] + U0 + 0.5 - AU < 0) == (side < 0)]; vm = sum(p[1] for p in px) / len(px)
    q = min(px, key=lambda p: abs(p[0] + U0 + 0.5 - AU) + 0.3 * abs(p[1] - vm)); return (q[0] + 0.5, q[1] + 0.5)
RT = {-1: root(-1), 1: root(1)}; AXC = AU - U0
def relief(cu, cv):
    side = -1 if cu < AXC else 1; ru, rv = RT[side]; dx, dy = cu - ru, cv - rv; rr = math.hypot(dx, dy); th = math.atan2(dy, dx)
    fade = max(0.0, min(1.0, ((cu - AXC) * side - 2.0) / 4.0))   # the feathers fade in away from the body (no cliff at the root)
    nb = g('fan', 0.17); rows = g('rows', [0.38, 0.66]); Lmax = g('Lmax', 26.0)
    sm = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
    row = sum(sm((rr - r0 * Lmax) / 1.2 + 0.5) for r0 in rows)               # smooth step between the feather rows
    stagger = (th / nb + 0.5 * row) % 1.0; ridge = math.sin(math.pi * stagger) ** g('ridge_pow', 1.0)
    return fade * (g('feather_h', 0.35) * ridge - g('row_step', 0.25) * row), rr
def thick(d): return min(g('wing_t', 1.3), 0.03 + d * 0.55 / S) if d > 0 else 0.0
verts = []; idx = {}
def vid(i, j, side):
    k = (i, j, side)
    if k in idx: return idx[k]
    cu = gu0 + (i + 0.5) / S; cv = gv0 + (j + 0.5) / S; d = dist[j][i]; t = thick(d) / 2
    rel, rr = relief(cu, cv) if side > 0 else (0.0, 0.0)
    off = side * t + (rel * min(1.0, d / (2 * S)) if side > 0 else 0.0)
    if d <= 1.5:   # boundary vertex: slide onto the smoothed outline (field 0.5) along the field gradient
        for _ in range(6):
            fx = (cu - gu0) * S - 0.5; fy = (cv - gv0) * S - 0.5; ii = min(GW - 2, max(0, int(fx))); jj = min(GH - 2, max(0, int(fy))); a_ = fx - ii; b_ = fy - jj
            fv = (fld[jj][ii] * (1 - a_) + fld[jj][ii + 1] * a_) * (1 - b_) + (fld[jj + 1][ii] * (1 - a_) + fld[jj + 1][ii + 1] * a_) * b_
            gx = ((fld[jj][ii + 1] - fld[jj][ii]) * (1 - b_) + (fld[jj + 1][ii + 1] - fld[jj + 1][ii]) * b_) * S; gy = ((fld[jj + 1][ii] - fld[jj][ii]) * (1 - a_) + (fld[jj + 1][ii + 1] - fld[jj][ii + 1]) * a_) * S
            gl = (gx * gx + gy * gy) ** 0.5
            if gl < 1e-6: break
            st = max(-0.3, min(0.3, (0.5 - fv) / gl)); cu += st * gx / gl; cv += st * gy / gl
    U = U0 + cu; Vp = V0 + cv; y = XW + 1184.0 - U; z = (XW + y) / 2.0 - Vp
    sd = -1 if cu < AXC else 1; ru, rv = RT[sd]; cupt = g('cup', 0.012) * ((cu - ru) ** 2 + (cv - rv) ** 2) if (cu - AXC) * sd > 0 else 0.0
    T = cupt + off   # along the view ray: the picture point stays; but thickness should be along x (the plane normal): use x for the thickness, ray for the cup
    p = (XW + T, y + T, z + T)   # thickness, feather relief and cup all along the view ray: the game picture stays exactly the drawn wing
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
