#!/usr/bin/env python3
"""LIGHT PROXY: the grand piano of room 85 (MERCATOR_CASTLE_BANQUET_ROOM; user rec_20261111_2006 frame ~5449, 2026-11-12: 'Klavier als 3D-Form, wie die Betten').
The collision holds it as a 32 high box over cells x 14..16, y 22..24 (without the corner 16 / 24). The drawing: a grand piano turned about -28 deg
(long axis from the keyboard end, screen left, to the round tail, screen right), the spine (straight) at the back, the BENTSIDE in front as an S curve
(user: 'Achtung, hier macht das eine Art S-Kurve'), the keyboard sticking out at the keyboard end, the lid hinged on the spine and propped open in front.
params_light.json = the fit against the drawn layer A pixels (rom_picture.py ROM 85 970 180 170 170, painted floor shadow (36, 36, 0) below y 127 left out;
coordinate descent on the silhouette IoU, local script): IoU 0.908 (125 model px outside, 173 drawn px missed: the lid's top rim and the prop stick, 1..2 px).
  cx / cy / th: centre and turn of the long axis u (v towards the front); L / W: length / width; c0..c1: case bottom / top; tr: tail radius;
  s1 / s2 / s3 / kb: the S curve (cubic Bezier from the tail to the front corner kb in from the keyboard end); kd / kz0..kz1: keyboard depth / heights;
  lh: the lid's front edge above the case top (hinge on the spine); l1 / l2: the two front legs (the back leg is hidden).
Writes TWO OBJs (game coordinates): OUT_case.obj = case + keyboard, SOLID down to the floor (the drawing has a dark painted shadow under it) and
OUT_lid.obj = the lid only; the lid goes into a second op with "air" so it floats over what the case op shaped (one column + one slab per 4 unit sub column).
Run: python3 remake/recipes/piano/piano.py landstalker/data/proxies/piano_85 [params.json]"""
import json, math, os, sys

def bez(p0, p1, p2, p3, n=10):
    return [tuple((1 - t) ** 3 * p0[i] + 3 * (1 - t) ** 2 * t * p1[i] + 3 * (1 - t) * t * t * p2[i] + t ** 3 * p3[i] for i in (0, 1)) for t in [k / n for k in range(n + 1)]]

def plan(P):
    L, W = P['L'], P['W']; a, b = -L / 2, L / 2; vb, vf = -W / 2, W / 2
    pts = [(a + P.get('su0', 0.0), vb + P.get('sp0', 0.0)), (b - P['tr'], vb)]   # su0 / sp0: the spine's keyboard end corner moved (the drawn keyboard end is not square)
    for k in range(1, 6):
        t = k / 6 * math.pi / 2; pts.append((b - P['tr'] + P['tr'] * math.sin(t), vb + P['tr'] - P['tr'] * math.cos(t)))
    tail = (b, vb + P['tr'])
    if 'front' in P:   # the front edge MEASURED: stations (u, v) from the tail to the keyboard end, read off the drawn bottom edge of the case
        b = P['L'] / 2; st = [tail] + [tuple(q) for q in P['front']]
        ext = [st[0]] + st + [st[-1]]
        for i in range(1, len(ext) - 2):
            p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
            for k in range(1 if i > 1 else 0, 5):
                t = k / 4
                pts.append(tuple(0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                                        + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t ** 3) for c in (0, 1)))
        return pts
    if 'fs' in P:   # S curve as a smooth curve (Catmull-Rom) through stations evenly spaced along u from the tail to the front corner kb
        n = len(P['fs']) - 1; u0, u1 = b, a + P['kb']
        st = [tail] + [(u0 + (u1 - u0) * j / n, vf - P['fs'][j]) for j in range(n + 1)] + [(a, vf)]
        ext = [st[0]] + st + [st[-1]]
        for i in range(1, len(ext) - 2):
            p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
            for k in range(1 if i > 1 else 0, 5):
                t = k / 4
                pts.append(tuple(0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                                        + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * t ** 3) for c in (0, 1)))
        return pts[:-1] + [(a, vf)]
    pts += bez(tail, (b, vb + P['tr'] + P['s1'] * W), (a + P['kb'] + P['s2'] * L, vf - P['s3'] * W), (a + P['kb'], vf))[1:]
    return pts + [(a, vf)]

def world(P, uv):
    cu, su = math.cos(P['th']), math.sin(P['th'])
    return [(P['cx'] + u * cu - v * su, P['cy'] + u * su + v * cu) for (u, v) in uv]

ORIENT = 1

def prism(F, pl, z0, z1):
    F.append([(x, y, z0) for x, y in reversed(pl)]); F.append([(x, y, z1) for x, y in pl])
    for i in range(len(pl)):
        (x1, y1), (x2, y2) = pl[i], pl[(i + 1) % len(pl)]; F.append([(x1, y1, z0), (x2, y2, z0), (x2, y2, z1), (x1, y1, z1)])

def box(F, cx, cy, r, z0, z1):
    prism(F, [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)][::-1 if ORIENT < 0 else 1], z0, z1)

def legs(P):   # the two drawn legs (keyboard end front, tail side; foot points read off the picture) + the hidden one at the keyboard end's spine side
    W = P['W']; hid = world(P, [(-P['L'] / 2 + 1.5, -W / 2 + 2.5)])[0]
    return [(P['l1x'], P['l1y']), (P['l2x'], P['l2y']), hid]

def case_faces(P, floor=None):
    """floor None: the case FLOATS from c0 (the drawing: only painted shadow under it, user 2026-11-12 'da ist nur Schatten drunter') on three legs;
    a number: solid down to that height (the old variant / the picture compare)."""
    F = []; z0 = P['c0'] if floor is None else floor
    prism(F, world(P, plan(P)), z0, P['c1'])
    W = P['W']; kf = P['front'][-1][1] if 'front' in P else W / 2
    kv0 = P.get('kv0', -W / 2 + 1); kv1 = P.get('kv1', kf)
    kb = world(P, [(-P['L'] / 2 - P['kd'], kv0), (-P['L'] / 2 + 0.5, kv0), (-P['L'] / 2 + 0.5, kv1), (-P['L'] / 2 - P['kd'], kv1)])
    if P['kd'] > 0: prism(F, kb, max(z0, P.get('kz0', z0)) if floor is None else z0, P['kz1'])   # the keyboard (kz0 .. kz1, v kv0 .. kv1)
    if floor is None:
        for (x, y) in legs(P): box(F, x, y, P.get('lr', 1.5), 0, P['c0'])
    return F

def lid_faces(P, thick=2.0):
    W = P['W']; ang = math.asin(max(-1.0, min(1.0, P['lh'] / W))); top, bot = [], []
    li = P.get('li', 0.0); pl = plan(P); mu = sum(q[0] for q in pl) / len(pl)
    for (u, v) in pl:
        u = mu + (u - mu) * (1 - li); v = -W / 2 + (v + W / 2) * (1 - li)   # li: the lid a bit smaller than the case (inside the drawn lid: no lit rim on the wall behind)
        d = v + W / 2; x, y = world(P, [(u, -W / 2 + d * math.cos(ang))])[0]; z = P['c1'] + d * math.sin(ang)
        top.append((x, y, z + thick)); bot.append((x, y, z))
    F = [list(reversed(bot)), top]
    for i in range(len(top)):
        j = (i + 1) % len(top); F.append([bot[i], bot[j], top[j], top[i]])
    return F

def write_obj(path, F, title):
    V, out = [], []
    for f in F:
        idx = []
        for p in f: V.append(p); idx.append(len(V))
        out.append("f " + " ".join(map(str, idx)))
    with open(path, "w") as fo:
        fo.write("# light proxy: %s (remake/recipes/piano/piano.py). GAME coordinates x east, y south, z up, world units.\n" % title)
        fo.write("# our own geometry fitted to the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        for p in V: fo.write("v %.2f %.2f %.2f\n" % p)
        fo.write("\n".join(out) + "\n")
    print("%s: %d faces" % (path, len(F)))

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    P = json.load(open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "params_light.json")))
    write_obj(sys.argv[1] + "_case.obj", case_faces(P), "grand piano case + keyboard, solid, room 85")
    write_obj(sys.argv[1] + "_lid.obj", lid_faces(P), "grand piano lid (propped open), room 85")
