# scroll.py OUT : the SCROLL held upright against the chest (v12, user: 'eher eine Schriftrolle'): a rolled sheet = a cylinder whose radius grows a little
# around (a spiral: the loose edge is a small step down its length), rounded rims, the end faces a little hollow with the spiral's centre
import json, math, sys
sys.path.insert(0, '/home/deck/ProjectL/remake/lib'); import furniture as F
P = json.load(open('/home/deck/lktest/sculpt/params.json')); g = lambda k, d: P.get(k, d)
A = F.CHURCH_ANGEL4; AX, AY = A['axis']; FLO = 32.0; SQ2 = math.sqrt(2)
# v13: the figure FACES OUT OF THE WALL (+x; user: 'die Fluegel muessen am Ruecken anliegen, parallel zum Koerper'), not the camera: the body frame
# (s = its left / right, f = its front) is turned 45 degrees about the body's axis; positions stay where they are in the picture
def W(s, f, z):
    if g('face_x', True): ds, df = s - 0.7, f; s, f = 0.7 + (ds + df) / SQ2, (df - ds) / SQ2
    return (AX + (s + f) / SQ2, AY + (f - s) / SQ2, FLO + z)
B = g('scroll_b', [0.7, 4.6, 27.4]); T = g('scroll_t', [0.7, 3.7, 34.6]); R = g('scroll_r', 1.2)
ax = [T[i] - B[i] for i in range(3)]; L = math.sqrt(sum(t * t for t in ax)); ax = [t / L for t in ax]
e1 = [1.0, 0.0, 0.0]; e2 = [ax[1] * e1[2] - ax[2] * e1[1], ax[2] * e1[0] - ax[0] * e1[2], ax[0] * e1[1] - ax[1] * e1[0]]; n2 = math.sqrt(sum(t * t for t in e2)); e2 = [t / n2 for t in e2]
NT = 96; prof = []   # (distance along the axis, radius factor): hollow end, rounded rim, shaft, rounded rim, hollow end
for k in range(5): prof.append((0.35 - 0.35 * k / 4, 0.12 + 0.6 * k / 4))            # bottom hollow -> rim
for k in range(1, 7): a = math.pi / 2 * k / 6; prof.append((0.25 - 0.25 * math.cos(a) * 1.0 + 0.0, 0.72 + 0.28 * math.sin(a)))
for k in range(1, 30): prof.append((0.25 + (L - 0.5) * k / 30, 1.0))
for k in range(0, 7): a = math.pi / 2 * (1 - k / 6); prof.append((L - 0.25 + 0.25 * math.cos(a), 0.72 + 0.28 * math.sin(a)))
for k in range(1, 5): prof.append((L - 0.35 * k / 4, 0.72 - 0.6 * k / 4))
V = []; Fc = []
for d, rf in prof:
    for i in range(NT):
        th = 2 * math.pi * i / NT; t = i / NT; r = R * rf * (0.9 + 0.1 * t) if rf > 0.5 else R * rf    # the spiral: the radius grows around, a step at th = 0
        V.append(W(*[B[k] + ax[k] * d + r * (math.cos(th) * e1[k] + math.sin(th) * e2[k]) for k in range(3)]))
n = len(prof)
for j in range(n - 1):
    for i in range(NT):
        a = j * NT + i; b = j * NT + (i + 1) % NT; Fc.append((a, b, b + NT, a + NT))
c0 = len(V); V.append(W(*[B[k] + ax[k] * 0.4 for k in range(3)])); V.append(W(*[B[k] + ax[k] * (L - 0.4) for k in range(3)]))
for i in range(NT): Fc.append((c0, (i + 1) % NT, i)); Fc.append((c0 + 1, (n - 1) * NT + i, (n - 1) * NT + (i + 1) % NT))
with open(sys.argv[1], 'w') as fo:
    for p in V: fo.write('v %.4f %.4f %.4f\n' % p)
    for q in Fc: fo.write('f ' + ' '.join(str(k + 1) for k in q) + '\n')
print('scroll', len(V), 'verts')
