# church angel sculpt v1: parts as metaball elements in game coordinates -> parts.json
import json, math, sys
sys.path.insert(0, '/home/deck/ProjectL/remake/lib'); import furniture as F
A = F.CHURCH_ANGEL4; AX, AY = A['axis']; FLO = 32.0; SQ2 = math.sqrt(2)
RZ = [z for z, c, r in A['rings']]; C = {z: c for z, c, r in A['rings']}; R = {z: r for z, c, r in A['rings']}
def ip(t, z):
    z = max(RZ[0], min(RZ[-1], z)); i = min(int(z // 2), len(RZ) - 2); u = (z - RZ[i]) / 2.0; return t[RZ[i]] + (t[RZ[i + 1]] - t[RZ[i]]) * u
# v13: the figure FACES OUT OF THE WALL (+x; user: 'die Fluegel muessen am Ruecken anliegen, parallel zum Koerper'), not the camera: the body frame
# (s = its left / right, f = its front) is turned 45 degrees about the body's axis; positions stay where they are in the picture
_P = json.load(open('params.json')); _ROT = _P.get('face_x', True); _S0 = 0.7
def W(s, f, z):
    if _ROT: ds, df = s - _S0, f; s, f = _S0 + (ds + df) / SQ2, (df - ds) / SQ2
    return [AX + (s + f) / SQ2, AY + (f - s) / SQ2, FLO + z]   # s = screen right, f = towards the viewer, z up from the pedestal top
KS = 1 / 0.575   # a lone metaball shows its surface at 0.575 of its radius (threshold 0.6, stiffness 2): radii below are SURFACE radii
def ks(st): return 1.0 / math.sqrt(1.0 - (0.6 / st) ** (1.0 / 3.0))   # surface share sqrt(1 - (threshold / stiffness)^(1/3)); stiffer = less blending
ST = 2.0   # default stiffness; the upper body parts use STU (crisper parts)
def ball(s, f, z, r, neg=False, st=None): st = st or ST; return dict(type='BALL', co=W(s, f, z), radius=r * ks(st), neg=neg, stiffness=st)
def ellip(s, f, z, rs, rf, rz, neg=False, st=None):   # ellipsoid with its axes along s / f / z (local frame turned -45 degrees about z)
    st = st or ST; c = math.cos(math.radians(-22.5)); sn = math.sin(math.radians(-22.5)); k = ks(st)
    return dict(type='ELLIPSOID', co=W(s, f, z), radius=k, size=[rs, rf, rz], quat=[c, 0.0, 0.0, sn], neg=neg, stiffness=st)
def caps(p, q, r, neg=False, st=None):
    st = st or ST   # capsule between p and q (local s f z); Blender capsule = along its local x, half length size_x
    a, b = W(*p), W(*q); m = [(a[i] + b[i]) / 2 for i in range(3)]; d = [b[i] - a[i] for i in range(3)]; L = math.sqrt(sum(t * t for t in d)) or 1e-6
    x = [t / L for t in d]; ax = [0.0, -x[2], x[1]]; s = math.sqrt(sum(t * t for t in ax)); c = x[0]   # rotation (1,0,0) -> x
    if s < 1e-9: q4 = [1, 0, 0, 0] if c > 0 else [0, 0, 0, 1]
    else:
        ang = math.atan2(s, c); ax = [t / s for t in ax]; q4 = [math.cos(ang / 2)] + [t * math.sin(ang / 2) for t in ax]
    return dict(type='CAPSULE', co=m, radius=r * ks(st), size=[L / 2, 0.0, 0.0], quat=q4, neg=neg, stiffness=st)
P = json.load(open('params.json')) if len(sys.argv) > 1 else {}
g = lambda k, d: P.get(k, d)
body = []
# ROBE: one ball per unit of height on the measured ring centres (radius a bit under the ring: metaballs swell where they overlap)
k = g('robe_k', 0.86)
for zi in range(g('robe_from', 0), 25):   # v11: robe_from 18 = the robe below is the polygon mesh of robe.py (params: folds 0)
    z = float(zi); body.append(ball(ip(C, z), 0.0, z, ip(R, z) * k))
# spiral FOLDS of the twisted robe (v3, user: 'Gewand wie du sagst'): deep grooves (negative capsules) and rounded ridges between them winding up;
# the drawn light stripes run from upper left to lower right
nf = g('folds', 5); turn = g('fold_turn', 0.6)
for j in range(nf):
    for kind in ('groove', 'ridge'):
        pts = []
        ph = 0.0 if kind == 'groove' else 0.5
        for zi in range(2, 43):                                                    # every half unit: a smooth groove, no bead chain; ends below the chest
            z = zi * 0.5; th = 2 * math.pi * ((j + ph) / nf + turn * z / 24.0)
            r = ip(R, z) * k + (g('fold_out', 0.05) if kind == 'groove' else -g('ridge_in', 0.55))
            pts.append((ip(C, z) + r * math.cos(th), r * math.sin(th), z))
        for p, q in zip(pts, pts[1:]):
            fade = max(0.0, min(1.0, (g('fold_end', 19.0) - q[2]) / 4.0))   # the folds run out under the chest (local z above the pedestal)
            if fade <= 0.05: continue
            if kind == 'groove': body.append(caps(p, q, g('fold_r', 0.8) * fade, neg=True))
            else: body.append(caps(p, q, g('ridge_r', 0.8) * fade))
# UPPER BODY (v2, user: 'Hals/Kopf Uebergang noch zu dick', 'die Haare ... wie im Sprite', child 'ich tendiere zum Kind'): read on the 1 px grid of 613:
# head rows 54..61 (centre z ~42 at the axis), a small face at its lower middle, HAIR parted in the middle falling in two locks beside the face to the
# shoulders; the chest RING right under the chin = the swaddling cloth around the child's face (light rim = cloth, dark centre = face), held upright
ST = g('stu', 5.0)
if g('torso', True): body.append(ball(0.6, -0.8, 27.0, 5.0))                                   # torso under the arms
body.append(ball(0.6, -0.9, g('shoulder_z', 33.6), g('shoulder_r', 4.4)))                  # shoulders
if g('traps', True):   # v11: sloping shoulders into the neck (the neck stood on the shoulder dome like a post with a rim)
    tz = g('trap_z', 37.6)
    for sg in (-1, 1): body.append(caps((0.8 + sg * 0.7, -0.5, tz), (0.6 + sg * 3.7, -0.5, tz - 2.6), g('trap_r', 1.25), st=2.5))
    body.append(caps((0.8, -0.2, g('neck_z0', 35.0)), (0.9, 0.0, g('neck_z1', 39.2)), g('neck_r', 1.35), st=2.5))   # the neck also in the body group: it blends into the shoulders (the head group's copy alone left a rim)
HEAD0 = len(body)   # the head is its own metaball group at a finer resolution (the face is ~4 units)
body.append(caps((0.8, -0.2, g('neck_z0', 35.0)), (0.9, 0.0, g('neck_z1', 39.2)), g('neck_r', 1.35)))   # thin neck
if not g('head_mesh', True): body.append(ball(0.9, -0.1, 42.2, g('skull_r', 2.9)))   # skull (the polygon head of head.py replaces it)
# HAIR (v5, user: 'Haare sind kein Pagenkopf, die gehen im Sprite hinter die Statue'): from the middle parting over the crown, framing the face at the sides
# (the drawn lobes beside the face) and then falling BACK and down behind the head and the shoulders (long hair down the back, hidden in the game view)
HC = (0.9, g('hair_f', -0.4), g('crown_z', 42.8)); HR = g('hair_r', 2.95)
if g('hair_mb', False):   # v5 metaball hair (v8: the hair shell of head.py; only the panel down the back stays)
    body.append(ball(HC[0], HC[1], HC[2], HR))                                              # crown
    for sg in (-1, 1):                                                                       # the sides beside the face, sweeping back
        body.append(caps((0.9 + sg * 2.35, g('side_f', -0.2), 42.6), (0.9 + sg * 2.4, -1.4, 40.4), g('side_r', 1.3))); body.append(caps((0.9 + sg * 2.4, -1.4, 40.4), (0.9 + sg * 1.5, -2.6, 37.8), g('side_r', 1.3) * 0.95))   # framing the face at the temples, into the back hair
    body.append(caps((0.9, -1.6, 42.0), (0.9, -2.6, 37.5), g('back_r1', 2.9)))              # the hair down the back: over the nape ...
    body.append(caps((0.9, -2.6, 37.5), (0.9, -3.1, g('back_z', 30.5)), g('back_r2', 3.1)))  # ... behind the shoulders, a little wider
    NS = g('hstrands', 9)
    for sg in (-1, 1):                                                                       # strands from the parting over the crown, then back and down
        for i in range(NS):
            t = i / (NS - 1.0); ff = (2.0 - 4.2 * t) * 0.75; R0 = math.sqrt(max(0.5, HR * HR - (ff - HC[1]) ** 2)) + g('ridge_out', -0.15); pts = []
            for k3 in range(0, 5):
                a3 = math.radians(90 - 15 * k3); pts.append((HC[0] + sg * R0 * math.cos(a3), ff, HC[2] + R0 * math.sin(a3)))
            last = pts[-1]
            for k3 in range(1, 5):                                                           # sweeping back and down behind the ear
                pts.append((last[0] + sg * 0.15 * k3, last[1] - 0.75 * k3 - 0.2 * t * k3, last[2] - 1.1 * k3))
            for p, q in zip(pts, pts[1:]): body.append(caps(p, q, g('ridge_hr', 0.45), st=g('ridge_hst', 6.0)))
    for j in range(-3, 4):                                                                   # strands down the back of the head and the back
        ss = 0.9 + 0.8 * j; pts = []
        for k3 in range(0, 6):
            a3 = math.radians(90 + 18 * k3); R0 = math.sqrt(max(0.5, HR * HR - (0.8 * j) ** 2)) + g('ridge_out', -0.15)
            pts.append((ss, HC[1] + R0 * math.cos(a3), HC[2] + R0 * math.sin(a3)))
        last = pts[-1]
        for k3 in range(1, 5): pts.append((ss + 0.15 * j * k3 / 4, last[1] - 0.2 * k3 - 0.15, last[2] - 2.0 * k3))
        for p, q in zip(pts, pts[1:]): body.append(caps(p, q, g('ridge_hr', 0.45), st=g('ridge_hst', 6.0)))
    body.append(caps((0.9, 2.0, HC[2] + HR + 0.1), (0.9, -2.6, HC[2] + HR - 0.4), 0.26, neg=True, st=6.0))   # the middle parting

else:
    body.append(caps((0.9, -2.0, 41.0), (0.9, -2.6, 37.5), g('back_r1', 2.0))); body.append(caps((0.9, -2.6, 37.5), (0.9, -3.1, g('back_z', 30.5)), g('back_r2', 2.6)))   # the hair down the back
if not g('head_mesh', True):
    # FACE (v6, user: 'das muss schon menschlich aussehen'): built from the parts of a human face in a face frame (origin O = the middle of the face oval,
    # s right, f forward, z up; units; chin to hairline ~4): oval, forehead, cheekbones, jaw + chin, eye sockets with eyeballs and lids, brow ridge,
    # nose bridge / tip / wings, lips with a mouth line; stiff parts (little blending) at the head group's fine resolution
    O = (1.0, g('face_f', 1.25), g('face_z', 41.5)); FS = g('face_scale', 1.0)
    def Fp(s3, f3, z3): return (O[0] + s3 * FS, O[1] + f3 * FS, O[2] + z3 * FS)
    FST = g('face_st', 3.0)
    # v7 (user: 'das ist eine Goettinnen-Statue, das Gesicht sollte weiblicher sein'): a narrower oval tapering softly to a small delicate chin, high soft
    # cheeks, no brow ridge but fine high arched brows, larger almond eyes, a small narrow nose with a slightly lifted tip, full but narrow lips; softer blends
    body.append(ellip(*Fp(0, 0.1, 0.05), 1.15 * FS, 1.1 * FS, 1.7 * FS, st=2.6))              # the face oval (narrower)
    body.append(ball(*Fp(0, 0.3, 0.95), 1.05 * FS, st=2.6))                                    # forehead, smooth and round
    for sg in (-1, 1):
        body.append(ball(*Fp(sg * 0.62, 0.72, -0.05), 0.55 * FS, st=FST))                       # high soft cheeks
        body.append(caps(Fp(sg * 0.72, 0.4, -0.55), Fp(sg * 0.22, 0.8, -1.38), 0.36 * FS, st=FST))   # jaw tapering to the chin (V)
    body.append(ball(*Fp(0, 0.92, -1.45), 0.3 * FS, st=FST))                                   # small delicate chin
    for sg in (-1, 1):                                                                          # larger almond eyes: socket, eyeball, lids
        body.append(ellip(*Fp(sg * 0.48, 1.24, 0.3), g('sock_rs', 0.3) * FS, 0.2 * FS, g('sock_rz', 0.2) * FS, neg=True, st=5.0))
        body.append(ellip(*Fp(sg * 0.48, g('eyeball_f', 1.0), 0.28), 0.33 * FS, 0.22 * FS, 0.21 * FS, st=6.0))
        for k3, (a0, a1) in enumerate(((0.2, 0.48), (0.48, 0.8))):                                # upper lid, almond arc, outer end a little lifted
            body.append(caps(Fp(sg * a0, 1.1, 0.4 + 0.05 * (1 - k3)), Fp(sg * a1, 1.06, 0.42 + 0.03 * k3), 0.065 * FS, st=6.0))
        body.append(caps(Fp(sg * 0.24, 1.06, 0.17), Fp(sg * 0.76, 1.02, 0.22), 0.04 * FS, st=6.0))   # lower lid
        for k3, (a0, a1, z0, z1) in enumerate(((0.14, 0.5, 0.7, 0.82), (0.5, 0.9, 0.82, 0.7))):     # fine, high arched brows
            body.append(caps(Fp(sg * a0, 1.1, z0), Fp(sg * a1, 0.98, z1), 0.07 * FS, st=5.0))
    body.append(caps(Fp(0, 1.16, 0.45), Fp(0, 1.42, -0.2), 0.12 * FS, st=5.0))                # nose bridge (narrow)
    body.append(ball(*Fp(0, 1.47, -0.24), 0.16 * FS, st=5.0))                                  # small nose tip, a little lifted
    for sg in (-1, 1): body.append(ball(*Fp(sg * 0.15, 1.3, -0.32), 0.11 * FS, st=5.0))        # narrow nose wings
    body.append(ball(*Fp(0, 1.3, -0.5), 0.07 * FS, neg=True, st=6.0))                           # philtrum dip
    for sg in (-1, 1):                                                                          # full upper lip with a cupid's bow, narrow
        body.append(caps(Fp(sg * 0.03, 1.23, -0.7), Fp(sg * 0.15, 1.22, -0.66), 0.09 * FS, st=4.0))
        body.append(caps(Fp(sg * 0.15, 1.22, -0.66), Fp(sg * 0.29, 1.14, -0.74), 0.06 * FS, st=4.0))
    body.append(ellip(*Fp(0, 1.15, -0.88), 0.21 * FS, 0.11 * FS, 0.1 * FS, st=4.0))            # full lower lip
    body.append(caps(Fp(-0.31, 1.33, -0.79), Fp(0.31, 1.33, -0.79), 0.04 * FS, neg=True, st=6.0))   # the line between the lips
    for sg in (-1, 1): body.append(ball(*Fp(sg * 0.34, 1.16, -0.8), 0.05 * FS, neg=True, st=6.0))   # mouth corners (soft)

HEAD1 = len(body)
# v12 (user: 'das Kind in den Armen ist glaub ich eher eine Schriftrolle', 'das 3D Modell dem Sprite moeglichst aehnlich'): read on the 1 px grid, the
# drawing shows a RING under the chin (14 px wide, 9 rows: shoulders on top, the elbows at the sides, the forearms / hands meeting in front below) and in
# its dark middle a small object with a bright top and a brown body (4 x 5 px) = a SCROLL held upright against the chest in both hands (scroll.py).
# The arms: shoulder -> elbow (out and down) -> wrist (forward, in to the middle), wide sleeves hanging under the forearms (the ring's lower arc)
if g('scroll', True) and g('folded', True):
    # v13 (user: 'eher verschraenkte Arme, in denen die Schriftrolle liegt, nicht aufrecht gehalten'): the arms FOLDED across the chest (each forearm
    # across the front, the hand at the other elbow, one forearm over the other), wide sleeves hanging under them; the scroll lies in them (scroll.py)
    for sg, zf, ff in ((-1, 30.7, 4.6), (1, 28.7, 4.1)):   # the s- arm lies on top / in front (v15: further apart + stiffer blending: no bulge where they cross)
        sh = (0.7 + sg * 4.0, -0.2, g('sh_z', 33.5)); el = (0.7 + sg * 5.0, 1.7, zf - 0.6); mid = (0.7 + sg * 1.2, ff - 0.3, zf - 0.1); ha = (0.7 - sg * 2.9, ff, zf)
        # v14 (user: 'die Unterarme sind zu knubbelig'): one even limb (no elbow ball, no separate sleeve roll, no hand ball): upper arm, a forearm that
        # tapers a little to the wrist, a small flat hand; soft blending
        ar = g('uarm_r', 1.4); fr = g('farm_r', 1.2)
        body.append(caps(sh, el, ar, st=2.4)); body.append(caps(el, mid, fr, st=4.5)); body.append(caps(mid, ha, fr * 0.88, st=4.5))
        body.append(ellip(ha[0] - sg * 0.7, ha[1] + 0.05, ha[2], 0.85, 0.5, 0.7, st=3.0))                               # the hand, flat on the other arm
elif g('scroll', True):
    for sg in (-1, 1):
        sh = (0.7 + sg * 4.0, -0.3, g('sh_z', 33.5)); el = (0.7 + sg * 5.0, 1.3, 30.3); wr = (0.7 + sg * 1.7, 4.3, 28.4)
        body.append(caps(sh, el, g('uarm_r', 1.45), st=3.0)); body.append(caps(el, wr, g('farm_r', 1.2), st=3.0))
        body.append(ball(*el, 1.5, st=3.0))                                                                          # the elbow under the cloth
        body.append(caps((0.7 + sg * 4.3, 1.9, 29.0), (0.7 + sg * 1.9, 4.2, 27.3), g('sleeve_r', 0.95), st=2.5))      # the sleeve hanging under the forearm
        body.append(ball(0.7 + sg * 1.0, 4.6, 28.7, 0.95, st=3.0))                                                    # the hand around the scroll
else:
    for sg in (-1, 1):
        sh = (0.6 + sg * 4.2, -0.4, 34.0); el = (0.6 + sg * 5.6, 1.4, 28.6 + (1.2 if sg < 0 else 0.0)); ha = (0.6 - sg * 1.2, 4.6, 27.2 + (2.2 if sg > 0 else 0.0))
        body.append(caps(sh, el, 1.55)); body.append(caps(el, ha, 1.4))
    CH = (g('ch_s', -0.6), 3.9, g('ch_z', 33.0)); CF = (g('cf_s', 4.0), 3.0, g('cf_z', 27.2))   # child's head / feet (held diagonally, user)
    body.append(caps(((CH[0] + CF[0]) / 2 * 0.5 + CH[0] * 0.5, 3.6, (CH[2] + CF[2]) / 2 * 0.5 + CH[2] * 0.5), CF, g('bundle_r', 2.3)))
    body.append(ball(CH[0], CH[1], CH[2], g('chood_r', 2.35)))
    body.append(ball(CH[0] - 0.25, CH[1] + 1.9, CH[2] + 0.15, g('cface_r', 1.15), neg=True))
    body.append(ball(CH[0] - 0.2, CH[1] + 1.2, CH[2] + 0.1, 0.9))                       # the child's little face inside the hood
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
json.dump(dict(groups=[dict(name='body', elements=body[:HEAD0] + body[HEAD1:], threshold=0.6), dict(name='head', elements=body[HEAD0:HEAD1], threshold=0.6, res=g('head_res', 0.07))]), open('parts.json', 'w'))
print(len(body), 'elements')
