# robe.py OUT : the twisted ROBE below the arms as ONE clean polygon mesh (v11, user: 'schau dir Haare, Gewand und Fluegel nochmal an'; the metaball robe was
# lumpy): a lathe on the measured ring centres of furniture.CHURCH_ANGEL4 (smoothed), its radius modulated by SPIRAL DRAPERY FOLDS (round ridges, narrow
# sharp valleys, a little irregular) winding up from the hem (the drawn light stripes run from upper left to lower right); the folds run out under the
# chest, where the mesh disappears inside the metaball torso. post.py keeps it inside the drawn outline.
import json, math, sys
sys.path.insert(0, '/home/deck/ProjectL/remake/lib'); import furniture as F
P = json.load(open('/home/deck/lktest/sculpt/params.json')); g = lambda k, d: P.get(k, d)
A = F.CHURCH_ANGEL4; AX, AY = A['axis']; FLO = 32.0; SQ2 = math.sqrt(2)
RZ = [z for z, c, r in A['rings']]; C = {z: c for z, c, r in A['rings']}; R = {z: r for z, c, r in A['rings']}
def ip(t, z):
    z = max(RZ[0], min(RZ[-1], z)); i = min(int(z // 2), len(RZ) - 2); u = (z - RZ[i]) / 2.0; return t[RZ[i]] + (t[RZ[i + 1]] - t[RZ[i]]) * u
def smo(t, z, s=2.5):   # gaussian-smoothed ring value (the measured rings carry the folds' bumps)
    a = b = 0.0
    for k in range(-8, 9):
        zz = z + k * 0.75; w = math.exp(-0.5 * (k * 0.75 / s) ** 2); a += w * ip(t, max(0.0, min(22.0, zz))); b += w
    return a / b
def W(s, f, z): return (AX + (s + f) / SQ2, AY + (f - s) / SQ2, FLO + z)
ZT = g('robe_top', 31.0); NZ = int(ZT * 6); NT = 320
NF = g('rfolds', 5); TURN = g('rturn', 0.7); AMP = g('ramp', 0.8); K = g('robe_rk', 0.97); FE = g('fold_end', 19.0)
def fold(th, z):
    x = (NF * th / (2 * math.pi) - NF * TURN * z / 24.0)
    x += 0.10 * math.sin(2 * th + 0.5 * z) + 0.06 * math.sin(5.0 * th - 0.9 * z)     # irregular spacing: cloth, not a screw
    x %= 1.0; x = x ** 1.25                                                              # skewed: each fold leans over the next (the twist)
    ridge = ((math.sin(math.pi * x) ** 2 + 0.02) ** 0.36 - 0.245) / 0.76                  # round ridge, narrow valley (soft bottom: no stairs on the grid)
    fine = 0.12 * math.sin(2 * math.pi * (2 * x + 0.3)) * math.sin(math.pi * x)          # a small secondary crease on the ridge's flank
    return ridge + fine - 0.62
# the drawn outline per picture row -> limits for s (left / right), so a row that would stick out is SQUEEZED as a whole (smoothly along z) instead of
# being cut flat by post.py (flat scars on the sides)
mask = {tuple(p) for p in json.load(open('/home/deck/lktest/angel3/mask.json'))}; U0, V0 = 1064, 280; AU = AX - AY + 1184.0
_rows = {}
for u, v in mask: lo, hi = _rows.get(v, (1e9, -1e9)); _rows[v] = (min(lo, u), max(hi, u + 1))
def lim(Vv):   # s limits at picture row Vv (float), the tighter of the two nearest rows
    v = Vv - V0 - 0.5; out = [-1e9, 1e9]
    for vv in (int(math.floor(v)), int(math.floor(v)) + 1):
        if vv in _rows: lo, hi = _rows[vv]; out = [max(out[0], (U0 + lo - AU) / SQ2), min(out[1], (U0 + hi - AU) / SQ2)]
    return out
V = []; Fc = []; SF = []
for j in range(NZ + 1):
    z = ZT * j / NZ; c = smo(C, z); r0 = smo(R, z) * K
    # above the hips the dress follows the TORSO (the metaball belly ball made a ledge over the robe): wider than deep, centre a little back, up into the shoulders
    tb = max(0.0, min(1.0, (z - 16.0) / 9.0)); tb = tb * tb * (3 - 2 * tb)
    c = c * (1 - tb) + 0.6 * tb; cf = -0.8 * tb; rs = r0 * (1 - tb) + g('torso_rs', 5.0) * tb; rf = r0 * (1 - tb) + g('torso_rf', 4.0) * tb
    fade = max(0.0, min(1.0, (FE + 2.0 - z) / 5.0)); fade = fade * fade * (3 - 2 * fade)
    hem = 0.35 * math.exp(-z / 1.2)                                                      # the hem spreads a little on the pedestal
    amp = AMP * (0.85 + 0.25 * math.sin(0.45 * z + 1.0))
    for i in range(NT):
        th = 2 * math.pi * i / NT; d = hem + amp * fade * fold(th, z)
        SF.append((c + (rs + d) * math.cos(th), cf + (rf + d) * math.sin(th), z, th))
oR = [0.0] * (NZ + 1); oL = [0.0] * (NZ + 1)
for j in range(NZ + 1):
    for i in range(NT):
        s_, f_, z_, th = SF[j * NT + i]; lo, hi = lim((AX + AY) / 2.0 + f_ / SQ2 - (FLO + z_)); oR[j] = max(oR[j], s_ - hi + 0.1); oL[j] = max(oL[j], lo - s_ + 0.1)
def spread(o):   # widen (max over +-0.5 unit) and smooth along z
    n = len(o); m = [max(o[max(0, j - 3):j + 4]) for j in range(n)]; out = []
    for j in range(n):
        a_ = b_ = 0.0
        for k in range(-9, 10):
            w = math.exp(-0.5 * (k / 4.0) ** 2); a_ += w * m[max(0, min(n - 1, j + k))]; b_ += w
        out.append(max(a_ / b_, o[j]))
    return out
oR, oL = spread(oR), spread(oL)
for j in range(NZ + 1):
    for i in range(NT):
        s_, f_, z_, th = SF[j * NT + i]; wr = max(0.0, min(1.0, (math.cos(th) + 0.6) / 0.9)); wl = max(0.0, min(1.0, (-math.cos(th) + 0.6) / 0.9))
        wr = wr * wr * (3 - 2 * wr); wl = wl * wl * (3 - 2 * wl)
        V.append(W(s_ - oR[j] * wr + oL[j] * wl, f_, z_))
for j in range(NZ):
    for i in range(NT):
        a = j * NT + i; b = j * NT + (i + 1) % NT; Fc.append((a, b, b + NT, a + NT))
n0 = len(V); V.append(W(smo(C, 0), 0, 0)); V.append(W(0.6, -0.8, ZT))
for i in range(NT):
    Fc.append((n0, (i + 1) % NT, i)); Fc.append((n0 + 1, NZ * NT + i, NZ * NT + (i + 1) % NT))
with open(sys.argv[1], 'w') as fo:
    for p in V: fo.write('v %.4f %.4f %.4f\n' % p)
    for q in Fc: fo.write('f ' + ' '.join(str(k + 1) for k in q) + '\n')
print('robe', len(V), 'verts')
