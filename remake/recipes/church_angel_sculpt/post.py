# post.py IN OUT [blur] : keep the sculpt inside the drawing along a SMOOTH outline: the statue's pixel mask blurred (gaussian, sigma `blur` px) and cut at 0.5
# = the pixel outline with rounded stairs; vertices below the pedestal top -> on it; a vertex outside is moved WITHOUT depth change
# (dx = dU / 2, dy = -dU / 2, dz = -dV keeps x + y) up the field's gradient until it reaches the 0.5 level
import json, sys, math
exec(open('/home/deck/lktest/sculpt/chk.py').read().split("if __name__")[0])
V, Fc = load(sys.argv[1]); FLO = 32.0; SIG = float(sys.argv[3]) if len(sys.argv) > 3 else 0.7
S = 4   # field samples per pixel
us = [p[0] for p in mask]; vs = [p[1] for p in mask]; gu0, gv0 = min(us) - 4, min(vs) - 4; GW, GH = (max(us) - gu0 + 9) * S, (max(vs) - gv0 + 9) * S
base = [[1.0 if (gu0 + i // S, gv0 + j // S) in mask else 0.0 for i in range(GW)] for j in range(GH)]
R = int(3 * SIG * S) + 1; ker = [math.exp(-0.5 * (k / (SIG * S)) ** 2) for k in range(-R, R + 1)]; ks = sum(ker); ker = [k / ks for k in ker]
tmp = [[sum(ker[k + R] * row[min(GW - 1, max(0, i + k))] for k in range(-R, R + 1)) for i in range(GW)] for row in base]
fld = [[sum(ker[k + R] * tmp[min(GH - 1, max(0, j + k))][i] for k in range(-R, R + 1)) for i in range(GW)] for j in range(GH)]
def f(cu, cv):   # cu, cv in window pixel coordinates
    x = (cu - gu0) * S - 0.5; y = (cv - gv0) * S - 0.5; i = int(math.floor(x)); j = int(math.floor(y))
    if i < 0 or j < 0 or i >= GW - 1 or j >= GH - 1: return 0.0
    a = x - i; b = y - j; return (fld[j][i] * (1 - a) + fld[j][i + 1] * a) * (1 - b) + (fld[j + 1][i] * (1 - a) + fld[j + 1][i + 1] * a) * b
moved = 0
for n, p in enumerate(V):
    x, y, z = p
    if z < FLO: z = FLO
    U, Vv = proj((x, y, z)); cu, cv = U - U0, Vv - V0; it = 0
    while f(cu, cv) < 0.5 and it < 80:
        h = 0.1; gx = (f(cu + h, cv) - f(cu - h, cv)) / (2 * h); gy = (f(cu, cv + h) - f(cu, cv - h)) / (2 * h); gl = math.hypot(gx, gy)
        if gl < 1e-6: break
        st = min(0.25, (0.5 - f(cu, cv)) / gl + 0.02); cu += st * gx / gl; cv += st * gy / gl; it += 1
    if it:
        dU, dV = cu - (U - U0), cv - (Vv - V0); x += dU / 2; y -= dU / 2; z -= dV; moved += 1
    V[n] = (x, y, z)
with open(sys.argv[2], 'w') as fo:
    for p in V: fo.write('v %.4f %.4f %.4f\n' % p)
    for q in Fc: fo.write('f ' + ' '.join(str(i + 1) for i in q) + '\n')
print('moved', moved, 'of', len(V))
