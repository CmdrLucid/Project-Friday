# head.py OUT : the goddess head as ONE clean polygon mesh (user 2026-11-10: 'eigenes Kopfmodell'): a sphere grid shaped into a female head by sculpt
# brushes (scale / taper / Gaussian push-pull along the normal) in a head frame (X right, Y forward = the face, Z up; Z 0 = chin, 1 = crown; head height
# H units), then placed on the statue (head axis at the measured place). Proportions: eyes at Z 0.5, brows 0.58, nose base 0.28, mouth 0.19, chin 0.
import json, math, sys
P = json.load(open('/home/deck/Project-Friday-Test/lktest/sculpt/params.json')); g = lambda k, d: P.get(k, d)
NU, NV = g('h_nu', 180), g('h_nv', 140)
def gau(d2, r): return math.exp(-d2 / (r * r))
def sm(a, b, x): t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
# BASE from human head PROFILES (female, head height 1, chin 0 .. crown 1): front profile yf, back profile yb, half width w per height Z; each horizontal
# section = front half a superellipse (flatter face) + back half an ellipse
def lin(tab, x):   # Catmull-Rom through the profile knots (smooth, no terraces)
    xs = [p[0] for p in tab]; ys = [p[1] for p in tab]
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    i = max(k for k in range(len(xs) - 1) if xs[k] <= x); t = (x - xs[i]) / (xs[i + 1] - xs[i])
    p0 = ys[max(0, i - 1)]; p1 = ys[i]; p2 = ys[i + 1]; p3 = ys[min(len(ys) - 1, i + 2)]
    return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
YF = g('prof_front', [(0.0, 0.0), (0.015, 0.13), (0.04, 0.225), (0.08, 0.272), (0.14, 0.298), (0.2, 0.318), (0.27, 0.334), (0.36, 0.343), (0.47, 0.345),
                      (0.55, 0.37), (0.62, 0.38), (0.72, 0.36), (0.82, 0.30), (0.92, 0.2), (0.97, 0.12), (0.995, 0.04), (1.0, 0.0)])
YB = g('prof_back', [(0.0, 0.0), (0.06, -0.10), (0.18, -0.20), (0.3, -0.30), (0.42, -0.42), (0.55, -0.48), (0.7, -0.49), (0.85, -0.40), (0.95, -0.24), (0.985, -0.12), (1.0, 0.0)])
WW = g('prof_width', [(0.0, 0.0), (0.02, 0.07), (0.05, 0.115), (0.12, 0.16), (0.22, 0.215), (0.34, 0.275), (0.48, 0.325), (0.62, 0.335), (0.78, 0.31), (0.9, 0.24), (0.97, 0.14), (0.995, 0.05), (1.0, 0.0)])
PF = g('face_flat', 2.6)
V = []
for j in range(NV + 1):
    Z = 1.0 - j / NV
    for i in range(NU):
        th = 2 * math.pi * i / NU; c, sn = math.cos(th), math.sin(th)            # th 0 = forward (+Y)
        w = lin(WW, Z)
        if c >= 0:   # front half: superellipse |x/w|^p + |y/yf|^p = 1 (flatter at the eyes, rounder at the mouth / chin: no 'Pausbacken')
            e = 2.0 / (2.0 + (PF - 2.0) * sm(0.2, 0.45, Z)); X = w * sn; Y = lin(YF, Z) * abs(c) ** e   # flatter face front; no power on X (a cusp = a crease down the middle)
        else: X = w * sn; Y = lin(YB, Z) * abs(c)
        L = math.hypot(sn, c); V.append([X, Y, Z, sn, c, 0.0])
# normals for the brushes: from the shape (finite differences on the grid)
def fixnormals():
    for j in range(NV + 1):
        for i in range(NU):
            a = V[j * NU + i]; r = V[j * NU + (i + 1) % NU]; l = V[j * NU + (i - 1) % NU]
            u = V[max(0, j - 1) * NU + i]; d = V[min(NV, j + 1) * NU + i]
            tx = [r[k] - l[k] for k in range(3)]; tz = [u[k] - d[k] for k in range(3)]
            n = (tx[1] * tz[2] - tx[2] * tz[1], tx[2] * tz[0] - tx[0] * tz[2], tx[0] * tz[1] - tx[1] * tz[0]); L = math.sqrt(sum(q * q for q in n)) or 1
            a[3], a[4], a[5] = -n[0] / L, -n[1] / L, -n[2] / L   # outward
fixnormals()
BASE = [list(v) for v in V]   # the head without the face features: the hair follows it
def push(c, r, h, aniso=(1, 1, 1), front=True):
    """Gaussian brush along the base normal: centre c (X, Z) on the face (front side), radius r, height h (+ out / - in)"""
    for v in V:
        X, Y, Z, nx, ny, nz = v
        if front and Y <= 0: continue
        d2 = ((X - c[0]) / aniso[0]) ** 2 + ((Z - c[1]) / aniso[2]) ** 2
        if d2 > 9 * r * r: continue
        w = gau(d2, r) * (sm(0.0, 0.25, Y) if front else 1.0); L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
        v[0] += h * w * nx / L; v[1] += h * w * ny / L; v[2] += h * w * nz / L
def pushy(c, r, h, aniso=(1, 1)):
    """brush straight forward (+Y): features on the face front (nose, lips, chin)"""
    for v in V:
        X, Y, Z = v[0], v[1], v[2]
        if Y <= 0.05: continue
        d2 = ((X - c[0]) / aniso[0]) ** 2 + ((Z - c[1]) / aniso[1]) ** 2
        if d2 > 9 * r * r: continue
        v[1] += h * gau(d2, r) * sm(0.05, 0.3, Y)
S = g('h_feat', 1.0)
for sg in (-1, 1):
    push((sg * 0.2, g('cheekbone_z', 0.46)), 0.07, g('cheekbone_h', 0.009) * S, aniso=(1.5, 1, 0.7))   # cheekbones, high
    pushy((sg * g('cheek_x', 0.145), g('cheek_z', 0.37)), g('cheek_r', 0.075), g('cheek_h', 0.014) * S, aniso=(1.0, 0.9))   # full round cheeks (the 'apples') under and outside the eyes
    pushy((sg * 0.075, 0.32), 0.04, g('nasolabial', -0.003) * S, aniso=(0.7, 1.4))   # a soft dip beside the nose wing (no hard fold)
    pushy((sg * 0.125, 0.497), 0.046, -0.05 * S, aniso=(1.4, 0.75))                 # eye socket
    pushy((sg * 0.125, 0.494), 0.033, 0.034 * S, aniso=(1.6, 0.68))                 # the eyeball (almond)
    for k3 in range(7):                                                               # upper lid: an almond arc, a crisp edge
        t3 = k3 / 6.0; xx = sg * (0.072 + 0.106 * t3); zz = 0.506 + 0.018 * math.sin(math.pi * t3) + 0.004 * t3
        pushy((xx, zz), 0.011, 0.009 * S, aniso=(1.5, 0.7))
    for k3 in range(5):                                                               # lower lid, flatter
        t3 = k3 / 4.0; xx = sg * (0.08 + 0.095 * t3); zz = 0.482 - 0.008 * math.sin(math.pi * t3)
        pushy((xx, zz), 0.009, 0.005 * S, aniso=(1.5, 0.7))
    pushy((sg * 0.135, 0.575), 0.026, 0.006 * S, aniso=(3.0, 0.55))                 # fine brow
for k in range(14):                                                                   # NOSE: root -> tip, straight, narrow, small, a little lifted
    t = k / 13.0; z = 0.52 - 0.23 * t; hgt = (0.01 + 0.085 * t ** 1.3) * S; wid = 0.02 + 0.012 * t
    pushy((0.0, z), wid, hgt * 0.3, aniso=(1.0, 1.6))
pushy((0.0, 0.29), 0.022, 0.03 * S, aniso=(1.15, 0.85))                               # nose tip
for sg in (-1, 1): pushy((sg * 0.03, 0.276), 0.016, 0.016 * S)                        # nostril wings
pushy((0.0, 0.257), 0.012, -0.008 * S, aniso=(1.6, 1))                                # under the nose
pushy((0.0, 0.235), 0.01, -0.004 * S, aniso=(0.8, 1.6))                               # philtrum
# v11 (user: 'neben dem Mund komisch geformt'): the base front profile no longer carries the lips (that made a shelf across the WHOLE face width at
# mouth height = a muzzle); the mouth sits on a soft LOCAL mound (the dental arch, about as wide as the mouth) that fades into the cheeks
pushy((0.0, g('mound_z', 0.2)), g('mound_r', 0.075), g('mound_h', 0.026) * S, aniso=(1.1, 0.7))
for sg in (-1, 1): pushy((sg * 0.026, 0.212), 0.019, 0.011 * S, aniso=(1.6, 0.55))      # upper lip, cupid's bow
pushy((0.0, 0.198), 0.068, -0.006 * S, aniso=(1.0, 0.065))                             # the mouth line
for sg in (-1, 1): pushy((sg * 0.068, 0.198), 0.013, -0.005 * S)                      # mouth corners (soft)
pushy((0.0, 0.18), 0.024, 0.012 * S, aniso=(2.1, 0.55))                              # full lower lip
pushy((0.0, 0.14), 0.02, -0.008 * S, aniso=(2.0, 0.7))                                # the dip under the lower lip
pushy((0.0, 0.085), 0.055, g('chin_h', 0.006) * S, aniso=(1.3, 1.0))                  # soft round chin
# place: head frame -> local statue frame (s, f, z) -> world (as sculpt.py W)
sys.path.insert(0, '/home/deck/ProjectL/remake/lib'); import furniture as F
A = F.CHURCH_ANGEL4; AX, AY = A['axis']; FLO = 32.0; SQ2 = math.sqrt(2)
H = g('head_h', 6.6); HS, HF, HZ = g('head_s', 0.95), g('head_f', -0.2), g('chin_z', 39.4)
def W(s, f, z): return (AX + (s + f) / SQ2, AY + (f - s) / SQ2, FLO + z)
# v13: the figure FACES OUT OF THE WALL (+x; user: 'die Fluegel muessen am Ruecken anliegen, parallel zum Koerper'), not the camera: the body frame
# (s = its left / right, f = its front) is turned 45 degrees about the body's axis; positions stay where they are in the picture
def WH(dx, dy, z):   # head-frame offsets (right, forward) from the head's axis
    if g('face_x', True): dx, dy = (dx + dy) / SQ2, (dy - dx) / SQ2
    return W(HS + dx, HF + dy, z)
tilt = math.radians(g('head_tilt', 8.0))                                              # a little bowed (looking down at the child)
out = []
for X, Y, Z, *_ in V:   # (rows of the grid: j = 0 the crown)
    Zc = Z - 0.5; Yr = Y * math.cos(tilt) + Zc * math.sin(tilt); Zr = -Y * math.sin(tilt) + Zc * math.cos(tilt) + 0.5
    out.append(WH(X * H, Yr * H, HZ + Zr * H))
# HAIR SHELL (v8): follows the skull: a shell over the base head from the middle parting down, the hairline high on the forehead, lower at the temples
# (framing the face = the drawn hair beside the face), behind the ears down to the nape (the long hair down the back continues as the metaball panel);
# strands = ridges along the meridians from the crown; closed shell (outer + inner surface + rim)
# v11 (user: 'schau dir die Haare nochmal an'; the shell ended at the skull = a cap with a rim, ribs fanning from the crown like a beanie): LONG hair
# parted in the middle: the hairline an arch from the parting over the temples (the face opening = the drawn 'hood'), the sides cover the ears and fall
# as a CURTAIN past the chin onto the shoulders and the back (it leaves the skull at Z = ZK and hangs, flaring a little); strands run from the PARTING
# sideways and down (lines of constant Y over the top), a little wavy and uneven; a parting groove on top
ZB = g('hair_bottom', -0.62); ZK = g('hair_hang', 0.40); NH = g('h_nh', 190)
def hairline(th):   # th = angle around the vertical axis, 0 = the face
    a = abs(((th + math.pi) % (2 * math.pi)) - math.pi)
    return max(ZB, lin([(0.0, g('hl_front', 0.80)), (0.3, 0.765), (0.6, g('hl_temple', 0.65)), (0.85, 0.48), (1.0, 0.30), (1.2, 0.06), (1.5, -0.3), (1.75, ZB), (2.0, ZB), (math.pi, ZB)], a))   # beside the face to the jaw, then swept BACK behind the shoulders (user: 'kein Pagenkopf')
HT = g('hair_t', 0.07); NSTR = g('h_strands', 46); RH = g('strand_h', 0.018)
def base_pt(Z, th):   # the base head surface at height Z, angle th (as the grid) + its outward normal (finite differences)
    def P(Z, th):
        w = lin(WW, Z); c, sn = math.cos(th), math.sin(th)
        if c >= 0: e = 2.0 / (2.0 + (PF - 2.0) * sm(0.2, 0.45, Z)); return (w * sn, lin(YF, Z) * abs(c) ** e, Z)
        return (w * sn, lin(YB, Z) * abs(c), Z)
    p = P(Z, th); a = P(Z, th + 1e-3); b = P(Z, th - 1e-3); u = P(min(1.0, Z + 1e-3), th); d = P(max(0.0, Z - 1e-3), th)
    tx = [a[k] - b[k] for k in range(3)]; tz = [u[k] - d[k] for k in range(3)]
    n = (tx[1] * tz[2] - tx[2] * tz[1], tx[2] * tz[0] - tx[0] * tz[2], tx[0] * tz[1] - tx[1] * tz[0]); L = math.sqrt(sum(q * q for q in n)) or 1
    n = [-q / L for q in n]
    if n[0] * p[0] + n[1] * p[1] + n[2] * (p[2] - 0.5) < 0: n = [-q for q in n]
    return p, n
YE_F, YE_B = lin(YF, 0.6), lin(YB, 0.6)
def strand_u(p, Z, th):   # the strand coordinate: over the top (Z >= 0.6) the angle where the line of constant Y meets the head's widest ring, below = th
    a = abs(((th + math.pi) % (2 * math.pi)) - math.pi)
    if Z < 0.6: return a
    if p[1] >= 0: e = 2.0 / PF; return math.acos(max(0.0, min(1.0, p[1] / YE_F)) ** (1.0 / e))
    return math.pi - math.acos(max(0.0, min(1.0, p[1] / YE_B)))
NUH = g('h_nuh', 360)   # the hair's own finer grid around (a strand = ~8 columns; 180 columns under-sampled the strands = terraces)
def hv(j, i, outer):
    th = 2 * math.pi * i / NUH; hl = hairline(th); Zh = 1.0 - (1.0 - ZB) * j / NH; Z = max(Zh, hl)   # vertices below the hairline slide up onto it: a smooth hair edge
    Zs = ZK + 0.5 * ((Z - ZK) + math.sqrt((Z - ZK) ** 2 + 0.01)); p, n = base_pt(min(1.0, Zs), th)   # smooth max(Z, ZK): no crease where the hair leaves the skull
    dh = (hairline(th + 0.02) - hairline(th - 0.02)) / 0.04
    edge = max(0.0, min(1.0, (Z - hl) / math.sqrt(1.0 + (dh / 0.33) ** 2) / 0.06))   # the shell thins out to the hairline by the true distance to it (a band by height alone made terraces along its steep part)
    edge = edge * edge * (3 - 2 * edge)
    u = strand_u(p, Zs, th); ph = NSTR * (u + 0.02 * math.sin(7 * u) + 0.012 * math.sin(17 * u + 1.0)) + 0.7 * math.sin(4.0 * Z + 3.0 * u)   # uneven strand widths, a little wavy
    kk = math.floor(ph / (2 * math.pi)); ak = 0.55 + 0.45 * math.sin(12.9898 * kk + 4.1) ** 2
    rid = RH * (ak * (0.5 + 0.5 * math.cos(ph)) ** 0.8 + 0.25 * (0.5 + 0.5 * math.cos(2.0 * ph + 1.0)))
    a_ = abs(((th + math.pi) % (2 * math.pi)) - math.pi); vol = lin([(0.0, g('hv_front', 0.05)), (0.7, g('hv_temple', 0.12)), (1.3, g('hv_side', 0.17)), (2.2, g('hv_back', 0.13)), (math.pi, 0.12)], a_)
    vol *= 1.0 - 0.85 * sm(0.7, 1.0, Zs)
    part = -g('part_d', 0.022) * math.exp(-(p[0] / 0.02) ** 2) * sm(0.62, 0.75, Zs) * sm(-0.42, -0.25, p[1])   # the middle parting (from the forehead over the crown)
    t = (vol * (0.3 + 0.7 * edge) + rid * edge + part * edge) if outer else -0.004
    q = [p[0] + t * n[0], p[1] + t * n[1], p[2] + t * n[2]]
    if Zs > Z:   # the curtain: hangs from the skull's ring at ZK, flaring a little outward and back
        d = Zs - Z; hl_ = math.hypot(n[0], n[1]) or 1.0; fl = g('hair_flare', 0.05) * d + g('hair_bulge', 0.03) * math.sin(math.pi * min(1.0, d / (ZK - ZB)))
        q = [q[0] + fl * n[0] / hl_, q[1] + fl * n[1] / hl_ - g('hair_backd', 0.16) * d, Z]
    return q
HV, HF_ = [], []; idxh = {}
def hid(j, i, o):
    k = (j, i % NUH, o)
    if k not in idxh: idxh[k] = len(HV); HV.append(hv(j, i % NUH, o))
    return idxh[k]
inh = [[(1.0 - (1.0 - ZB) * j / NH) >= hairline(2 * math.pi * i / NUH) for i in range(NUH)] for j in range(NH + 1)]
cells = {(j, i) for j in range(NH) for i in range(NUH) if inh[j][i] or inh[j][(i + 1) % NUH] or inh[j + 1][i] or inh[j + 1][(i + 1) % NUH]}
for (j, i) in cells:
    HF_.append((hid(j, i, 1), hid(j, i + 1, 1), hid(j + 1, i + 1, 1), hid(j + 1, i, 1)))
    HF_.append((hid(j, i, 0), hid(j + 1, i, 0), hid(j + 1, i + 1, 0), hid(j, i + 1, 0)))
for (j, i) in cells:   # rim along the region boundary
    for (nj, ni), (a0, a1) in (((j - 1, i), ((j, i), (j, i + 1))), ((j, i + 1), ((j, i + 1), (j + 1, i + 1))), ((j + 1, i), ((j + 1, i + 1), (j + 1, i))), ((j, i - 1), ((j + 1, i), (j, i)))):
        if (nj, ni % NUH) not in cells: HF_.append((hid(a0[0], a0[1], 1), hid(a0[0], a0[1], 0), hid(a1[0], a1[1], 0), hid(a1[0], a1[1], 1)))
F_ = []
for j in range(NV):
    for i in range(NU):
        a = j * NU + i; b = j * NU + (i + 1) % NU; c = (j + 1) * NU + (i + 1) % NU; d = (j + 1) * NU + i
        F_.append((a, b, c, d))
with open(sys.argv[1], 'w') as fo:
    for p in out: fo.write('v %.4f %.4f %.4f\n' % p)
    for q in F_: fo.write('f ' + ' '.join(str(k + 1) for k in q) + '\n')
if len(sys.argv) > 2:
    with open(sys.argv[2], 'w') as fo:
        for X, Y, Z in HV:
            Zc = Z - 0.5; Yr = Y * math.cos(tilt) + Zc * math.sin(tilt); Zr = -Y * math.sin(tilt) + Zc * math.cos(tilt) + 0.5
            fo.write('v %.4f %.4f %.4f\n' % WH(X * H, Yr * H, HZ + Zr * H))
        for q in HF_: fo.write('f ' + ' '.join(str(k + 1) for k in q) + '\n')
print('head', len(out), 'verts', 'hair', len(HV))
