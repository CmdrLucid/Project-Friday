#!/usr/bin/env python3
"""model3d.py OUT [params.json] - the grand piano of room 85 as a NEAR-FINAL 3D model (remake-ready geometry, style C; materials later) that is
also the LIGHT shape (memory feedback-precise-light-shapes: 'die Vorgabe war doch immer gleich remake ready machen'; user 2026-11-12 'bau es als echtes 3D').
Built on the MEASURED plan of piano.py (params_light.json: the front S curve read off the drawn case bottom, case z c0..c1, legs at the drawn feet):
  case   = a shell swept along the plan: plinth chamfer at the bottom, straight side, a small moulded lip at the rim, rim top, inner wall down to
           the soundboard (c1 - 3): the case is OPEN (the drawing shows the inside with the gold frame);
  frame  = the cast iron plate on the soundboard (inset outline) + three struts along the strings;
  keys   = key bed, key slab (white keys on top), the fallboard behind, two cheek blocks at the ends;
  legs   = three turned legs (taper, collar, brass foot / caster) under the case;
  lid    = the measured lid (hinged on the spine, propped open) with a rounded edge + the prop stick from the rim (the drawn rod).
Writes OUT_case.obj (case, frame, keys, legs) and OUT_lid.obj (lid + stick) in GAME coordinates (x east, y south, z up, units); groups
'wood' / 'brass' / 'iron' / 'keys' for later materials. Every part is a closed outward solid (the GPU shadow maps need edge twins)."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import piano

def area(pl): return sum(pl[i][0] * pl[(i + 1) % len(pl)][1] - pl[(i + 1) % len(pl)][0] * pl[i][1] for i in range(len(pl))) / 2

def clean(pl, eps=0.05):
    out = []
    for p in pl:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > eps: out.append(p)
    if math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= eps: out.pop()
    return out

def offset(pl, d):
    """inward offset by d (d < 0 = outward) of a CCW polygon (interior on the left), miter limited"""
    n = len(pl); out = []
    for i in range(n):
        a, v, b = pl[i - 1], pl[i], pl[(i + 1) % n]
        e1 = (v[0] - a[0], v[1] - a[1]); e2 = (b[0] - v[0], b[1] - v[1]); l1 = math.hypot(*e1); l2 = math.hypot(*e2)
        n1 = (-e1[1] / l1, e1[0] / l1); n2 = (-e2[1] / l2, e2[0] / l2); m = (n1[0] + n2[0], n1[1] + n2[1]); lm = math.hypot(*m)
        m = (m[0] / lm, m[1] / lm); c = max(0.5, m[0] * n1[0] + m[1] * n1[1])
        out.append((v[0] + m[0] * d / c, v[1] + m[1] * d / c))
    return out

def earclip(pl):
    """triangles (index triples) of a simple CCW polygon"""
    idx = list(range(len(pl))); tris = []
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    def inside(p, a, b, c): return cross(a, b, p) >= -1e-9 and cross(b, c, p) >= -1e-9 and cross(c, a, p) >= -1e-9
    guard = 0
    while len(idx) > 3 and guard < 100000:
        guard += 1; n = len(idx); done = False
        for k in range(n):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % n]; a, b, c = pl[i0], pl[i1], pl[i2]
            if cross(a, b, c) <= 1e-9: continue
            if any(inside(pl[j], a, b, c) for j in idx if j not in (i0, i1, i2)): continue
            tris.append((i0, i1, i2)); idx.pop(k); done = True; break
        if not done: break
    if len(idx) == 3: tris.append(tuple(idx))
    return tris

class Mesh:
    def __init__(self): self.V = []; self.F = []; self.G = []
    def loft(self, rings, group, cap0=True, cap1=True):
        """rings: lists of (x, y, z) with the same count, in CCW order seen from above; caps triangulated in plan"""
        m = len(rings[0]); b = len(self.V)
        for r in rings: self.V += r
        for i in range(len(rings) - 1):
            for j in range(m):
                self.F.append([b + i * m + j, b + i * m + (j + 1) % m, b + (i + 1) * m + (j + 1) % m, b + (i + 1) * m + j]); self.G.append(group)
        if cap0:
            for t in earclip([(p[0], p[1]) for p in rings[0]]): self.F.append([b + t[2], b + t[1], b + t[0]]); self.G.append(group)
        if cap1:
            L = b + (len(rings) - 1) * m
            for t in earclip([(p[0], p[1]) for p in rings[-1]]): self.F.append([L + t[0], L + t[1], L + t[2]]); self.G.append(group)
    def fix(self):
        """flip every part (connected by shared vertex ids) to positive volume"""
        parent = list(range(len(self.F))); vf = {}
        def find(i):
            while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
            return i
        for fi, f in enumerate(self.F):
            for v in f:
                if v in vf: parent[find(fi)] = find(vf[v])
                else: vf[v] = fi
        vol = {}
        for fi, f in enumerate(self.F):
            a = self.V[f[0]]
            for k in range(1, len(f) - 1):
                b, c = self.V[f[k]], self.V[f[k + 1]]
                vol[find(fi)] = vol.get(find(fi), 0) + (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
        for fi in range(len(self.F)):
            if vol[find(fi)] < 0: self.F[fi] = self.F[fi][::-1]
    def faces(self): return [[self.V[i] for i in f] for f in self.F]
    def write(self, path, title):
        self.fix()
        with open(path, "w") as fo:
            fo.write("# %s (remake/recipes/piano/model3d.py). GAME coordinates x east, y south, z up, world units.\n" % title)
            fo.write("# our own geometry fitted to the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
            for v in self.V: fo.write("v %.3f %.3f %.3f\n" % v)
            g = None
            for f, gg in zip(self.F, self.G):
                if gg != g: fo.write("g %s\n" % gg); g = gg
                fo.write("f " + " ".join(str(i + 1) for i in f) + "\n")
        print("%s: %d vertices, %d faces" % (path, len(self.V), len(self.F)))

def ccw(pl): return pl if area(pl) > 0 else pl[::-1]

def rrect(u0, u1, v0, v1, r, n=3):
    pts = []
    for (cu, cv, a0) in ((u1 - r, v0 + r, -90), (u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n); pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts

def obox(M, P, u0, u1, v0, v1, z0, z1, r, bev, group):
    """an oriented rounded box in the piano's (u, v) frame, bevelled top and bottom edges"""
    def ring(d, z): return [(x, y, z) for (x, y) in ccw(piano.world(P, offset(ccw(rrect(u0, u1, v0, v1, r)), d)))]
    b = min(bev, (z1 - z0) / 3)
    M.loft([ring(b, z0), ring(0, z0 + b), ring(0, z1 - b), ring(b, z1)], group)

def lathe(M, x, y, prof, group, seg=16):
    rings = [[(x + r * math.cos(2 * math.pi * k / seg), y + r * math.sin(2 * math.pi * k / seg), z) for k in range(seg)] for (r, z) in prof]
    M.loft(rings, group)

def build(P):
    c0, c1 = P['c0'], P['c1']; plan = clean(piano.plan(P)); W = P['W']; a = -P['L'] / 2
    wp = ccw(clean(piano.world(P, plan)))
    case = Mesh()
    def ring(d, z): return [(x, y, z) for (x, y) in offset(wp, d)]
    sb = c1 - 3.0   # soundboard
    case.loft([ring(0.6, c0), ring(0.0, c0 + 0.8), ring(0.0, c1 - 1.3), ring(-0.35, c1 - 0.9), ring(-0.35, c1 - 0.15), ring(0.0, c1), ring(1.1, c1), ring(1.25, c1 - 0.3), ring(1.25, sb)], 'wood')
    # cast iron plate on the soundboard + three struts (along u, the strings' direction)
    plate = Mesh(); pr = offset(wp, 2.0)
    plate.loft([[(x, y, sb) for x, y in pr], [(x, y, sb + 0.5) for x, y in offset(wp, 2.3)]], 'iron')
    for vv in (-0.45, -0.05, 0.3):
        v0 = -W / 2 + 2.5 + (W - 5) * (vv + 0.5); obox(plate, P, a + 3.5, P['L'] / 2 - 7 - 10 * (vv + 0.5), v0 - 0.6, v0 + 0.6, sb, sb + 1.6, 0.5, 0.3, 'iron')
    # keyboard: key bed, key slab, fallboard, cheeks
    kv0, kv1, kd = P['kv0'], P['kv1'], P['kd']; k0 = P['kz0']; k1 = P['kz1']
    keys = Mesh()
    obox(keys, P, a - kd, a + 0.5, kv0 + 1.4, kv1 - 1.4, k0, k0 + 1.4, 0.4, 0.3, 'wood')                 # key bed (the key slip at its front)
    obox(keys, P, a - kd + 0.8, a - 1.2, kv0 + 1.5, kv1 - 1.5, k0 + 1.4, k1, 0.25, 0.2, 'keys')           # the keys
    obox(keys, P, a - 1.4, a + 0.5, kv0 + 1.4, kv1 - 1.4, k1 - 0.3, k1 + 2.2, 0.4, 0.3, 'wood')           # fallboard / name board
    for vv in (kv0, kv1 - 1.4):
        obox(keys, P, a - kd, a + 1.0, vv, vv + 1.4, k0, k1 + 1.2, 0.5, 0.35, 'wood')                       # cheek blocks
    # legs: turned, tapering to a brass foot
    legs = Mesh()
    for (x, y) in piano.legs(P):
        lathe(legs, x, y, [(1.1, 0.0), (1.35, 0.6), (1.2, 1.4), (0.85, 1.6)], 'brass')
        lathe(legs, x, y, [(0.85, 1.6), (1.05, 2.0), (1.25, 3.4), (1.45, 5.2), (1.9, 5.6), (1.9, c0 + 0.3)], 'wood')
    lid = Mesh(); ang = math.asin(max(-1.0, min(1.0, P['lh'] / W))); li = P.get('li', 0.0); mu = sum(q[0] for q in plan) / len(plan)
    def lidpt(u, v, dz):
        u = mu + (u - mu) * (1 - li); v = -W / 2 + (v + W / 2) * (1 - li); d = v + W / 2
        x, y = piano.world(P, [(u, -W / 2 + d * math.cos(ang))])[0]; return (x, y, c1 + d * math.sin(ang) + dz)
    lp = plan if area(piano.world(P, plan)) > 0 else plan[::-1]
    def lring(dd, dz):
        q = offset(lp, dd) if area(piano.world(P, lp)) > 0 else offset(lp[::-1], dd)[::-1]
        return [lidpt(u, v, dz) for (u, v) in q]
    t = 1.2
    rings = [lring(0.35, 0.0), lring(0.0, 0.35), lring(0.0, t - 0.35), lring(0.35, t)]
    if area([(p[0], p[1]) for p in rings[0]]) < 0: rings = [r[::-1] for r in rings]
    lid.loft(rings, 'wood')
    # the prop stick: from the rim to the lid's underside at the drawn rod (picture x ~62, rim at y ~117 of rom_picture 970 180)
    sx, sy = P.get('stick', (241.0, 392.5)); su = ((sx - P['cx']) * math.cos(P['th']) + (sy - P['cy']) * math.sin(P['th']))
    sv = (-(sx - P['cx']) * math.sin(P['th']) + (sy - P['cy']) * math.cos(P['th']))
    best = min(((abs(lidpt(su, v, 0)[0] - sx) + abs(lidpt(su, v, 0)[1] - sy), v) for v in [(-W / 2) + k * 0.25 for k in range(int(W * 4))]))[1]
    top = lidpt(su, best, 0.0)
    lathe(lid, top[0], top[1], [(0.45, c1 - 0.2), (0.45, top[2] + 0.3)], 'wood', seg=10)
    return [case, plate, keys, legs], lid

def merge(ms):
    M = Mesh()
    for m in ms:
        b = len(M.V); M.V += m.V; M.F += [[i + b for i in f] for f in m.F]; M.G += m.G
    return M

if __name__ == "__main__":
    P = json.load(open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "params_light.json")))
    parts, lid = build(P)
    merge(parts).write(sys.argv[1] + "_case.obj", "grand piano: case, frame, keys, legs - room 85")
    lid.write(sys.argv[1] + "_lid.obj", "grand piano: lid + prop stick - room 85")
