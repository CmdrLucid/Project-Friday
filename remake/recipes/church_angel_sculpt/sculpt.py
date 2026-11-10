# church angel sculpt v1: parts as metaball elements in game coordinates -> parts.json
import json, math, sys
sys.path.insert(0, '/home/deck/ProjectL/remake/lib'); import furniture as F
A = F.CHURCH_ANGEL4; AX, AY = A['axis']; FLO = 32.0; SQ2 = math.sqrt(2)
RZ = [z for z, c, r in A['rings']]; C = {z: c for z, c, r in A['rings']}; R = {z: r for z, c, r in A['rings']}
def ip(t, z):
    z = max(RZ[0], min(RZ[-1], z)); i = min(int(z // 2), len(RZ) - 2); u = (z - RZ[i]) / 2.0; return t[RZ[i]] + (t[RZ[i + 1]] - t[RZ[i]]) * u
def W(s, f, z): return [AX + (s + f) / SQ2, AY + (f - s) / SQ2, FLO + z]   # s = screen right, f = towards the viewer, z up from the pedestal top
KS = 1 / 0.575   # a lone metaball shows its surface at 0.575 of its radius (threshold 0.6, stiffness 2): radii below are SURFACE radii
def ball(s, f, z, r, neg=False, st=2.0): return dict(type='BALL', co=W(s, f, z), radius=r * KS, neg=neg, stiffness=st)
def caps(p, q, r, neg=False, st=2.0):   # capsule between p and q (local s f z); Blender capsule = along its local x, half length size_x
    a, b = W(*p), W(*q); m = [(a[i] + b[i]) / 2 for i in range(3)]; d = [b[i] - a[i] for i in range(3)]; L = math.sqrt(sum(t * t for t in d)) or 1e-6
    x = [t / L for t in d]; ax = [0.0, -x[2], x[1]]; s = math.sqrt(sum(t * t for t in ax)); c = x[0]   # rotation (1,0,0) -> x
    if s < 1e-9: q4 = [1, 0, 0, 0] if c > 0 else [0, 0, 0, 1]
    else:
        ang = math.atan2(s, c); ax = [t / s for t in ax]; q4 = [math.cos(ang / 2)] + [t * math.sin(ang / 2) for t in ax]
    return dict(type='CAPSULE', co=m, radius=r * KS, size=[L / 2, 0.0, 0.0], quat=q4, neg=neg, stiffness=st)
P = json.load(open('params.json')) if len(sys.argv) > 1 else {}
g = lambda k, d: P.get(k, d)
body = []
# ROBE: one ball per unit of height on the measured ring centres (radius a bit under the ring: metaballs swell where they overlap)
k = g('robe_k', 0.86)
for zi in range(0, 25):
    z = float(zi); body.append(ball(ip(C, z), 0.0, z, ip(R, z) * k))
# spiral FOLDS of the twisted robe: negative capsules winding up (the drawn light stripes run from upper left to lower right)
nf = g('folds', 4); turn = g('fold_turn', 0.55)   # turns over the robe height
for j in range(nf):
    pts = []
    for zi in range(1, 24, 2):
        z = float(zi); th = 2 * math.pi * (j / nf + turn * z / 24.0); r = ip(R, z) + g('fold_out', 0.35)
        pts.append((ip(C, z) + r * math.cos(th), r * math.sin(th), z))
    for p, q in zip(pts, pts[1:]): body.append(caps(p, q, g('fold_r', 0.75), neg=True))
# TORSO under the arms + shoulders
body.append(ball(0.6, -0.6, 27.0, 5.2)); body.append(ball(0.6, -0.8, 32.5, 5.0))
# ARMS: upper arm shoulder -> elbow, forearm elbow -> hands under the child
for sg in (-1, 1):
    sh = (0.6 + sg * 4.6, -0.2, 33.0); el = (0.6 + sg * 6.2, 1.6, 28.0); ha = (0.6 + sg * 1.6, 4.4, 25.6)
    body.append(caps(sh, el, 1.7)); body.append(caps(el, ha, 1.5))
# the CHILD in the arms: swaddled bundle (long axis across the chest) + its head
body.append(caps((-2.8, 3.2, 28.2), (3.6, 3.4, 29.6), 2.5)); body.append(ball(-3.2, 3.6, 29.0, 2.2))
# HEAD under a veil: head, veil behind / over it falling to the shoulders, face recess at the front
body.append(caps((0.9, -0.8, 41.6), (0.9, -1.4, 35.0), 3.5)); body.append(ball(1.0, 1.2, 39.2, 2.5))   # veil (hood falling to the shoulders) + the face under its rim
# WINGS: in the plane x = XW (parallel to the niche's back wall, v5), filled from the drawn wing pixels; a point keeps its picture position when moved along the
# view ray (1, 1, 1) = the CUP (outer feathers come forward, invisible in the game view); feathers = shallow negative grooves fanning out from the wing root
XW = A['wing_x']; AU = AX - AY + 1184.0; V0p = A['v0']
def plane(U, Vp, t=0.0):   # picture point -> the wing plane x = XW, then t along the view ray
    y = XW + 1184.0 - U; z = (XW + y) / 2.0 - Vp; return [XW + t, y + t, z + t]
wing = {(du, v) for du, v in A['wing']}
cup = g('cup', 0.010); wr = g('wing_r', 1.05); wt = g('wing_t', 0.55); step = g('wing_step', 1.0)
for side in ((-1, 1) if g('mb_wings', False) else ()):
    px = [(du, v) for du, v in wing if (du < 0) == (side < 0)]
    # root = the wing pixel nearest the body axis at the wing's middle height
    vm = sum(v for du, v in px) / len(px); root = min(px, key=lambda p: abs(p[0]) + 0.3 * abs(p[1] - vm)); ru, rv = AU + root[0] + 0.5, V0p + root[1] + 0.5
    for du, v in px:
        if (int(du - 0.5) % 2) or (v % 2): continue   # every 2nd pixel: bigger soft elements, smoother surface
        U, Vp = AU + du + 1.0, V0p + v + 1.0; d2 = (U - ru) ** 2 + (Vp - rv) ** 2
        co = plane(U, Vp, cup * d2)
        body.append(dict(type='ELLIPSOID', co=co, radius=wr * KS, size=[wt / wr, 1.0, 1.0], neg=False, stiffness=2.0))
    # the wing grows out of the back: a bridge from the shoulder blade to the wing root (in the plane)
    rw = plane(ru, rv, 0.0); sb = W(0.6 + side * 3.0, -3.2, 32.0)
    for k3 in range(5):
        t3 = k3 / 4.0; co = [sb[i] + (rw[i] - sb[i]) * t3 for i in range(3)]
        body.append(dict(type='BALL', co=co, radius=(1.5 - 0.5 * t3) * KS, neg=False, stiffness=2.0))
    # feather grooves: rays from the root to the far outline points, every ~2.6 units of the outline
    far = sorted(px, key=lambda p: -((AU + p[0] - ru) ** 2 + (V0p + p[1] - rv) ** 2))
    outline = [p for p in px if any((p[0] + a, p[1] + b) not in wing for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    import math as _m
    angs = sorted(set(round(_m.atan2(V0p + p[1] - rv, AU + p[0] - ru) / g('fan', 0.16)) for p in outline if (AU + p[0] - ru) ** 2 + (V0p + p[1] - rv) ** 2 > 36))
    for a in angs:
        th = a * g('fan', 0.16); L = max(((AU + p[0] - ru) ** 2 + (V0p + p[1] - rv) ** 2) ** 0.5 for p in outline if abs(_m.atan2(V0p + p[1] - rv, AU + p[0] - ru) - th) < 0.12)
        p0 = (ru + 0.35 * L * _m.cos(th), rv + 0.35 * L * _m.sin(th)); p1 = (ru + 1.05 * L * _m.cos(th), rv + 1.05 * L * _m.sin(th))
        for k2 in range(6):
            q0 = [p0[i] + (p1[i] - p0[i]) * k2 / 6 for i in range(2)]; q1 = [p0[i] + (p1[i] - p0[i]) * (k2 + 1) / 6 for i in range(2)]
            def fr(q): d2 = (q[0] - ru) ** 2 + (q[1] - rv) ** 2; return plane(q[0], q[1], cup * d2 + wt * 0.9)
            a3, b3 = fr(q0), fr(q1); m3 = [(a3[i] + b3[i]) / 2 for i in range(3)]; dd = [b3[i] - a3[i] for i in range(3)]; LL = sum(t * t for t in dd) ** 0.5 or 1e-6
            x = [t / LL for t in dd]; axv = [0.0, -x[2], x[1]]; sn = sum(t * t for t in axv) ** 0.5; ang = _m.atan2(sn, x[0]); axv = [t / sn for t in axv] if sn > 1e-9 else [0, 0, 1]
            body.append(dict(type='CAPSULE', co=m3, radius=g('groove_r', 0.32) * KS, size=[LL / 2, 0, 0], quat=[_m.cos(ang / 2)] + [t * _m.sin(ang / 2) for t in axv], neg=True, stiffness=2.0))
json.dump(dict(groups=[dict(name='body', elements=body, threshold=0.6)]), open('parts.json', 'w'))
print(len(body), 'elements')
