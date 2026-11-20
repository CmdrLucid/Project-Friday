#!/usr/bin/env python3
"""pure-Python style C bush (as remake/lib/kit_c.py bushes(): round crown squashed + 5 leaf lumps on a Y-shaped stem), for the light (no bpy)."""
import math, random
def ellipsoid(cx, cy, cz, r, sz, seg=12, ring=8):
    V = [[(cx + r * math.sin(math.pi * i / ring) * math.cos(2 * math.pi * j / seg), cy + r * math.sin(math.pi * i / ring) * math.sin(2 * math.pi * j / seg), cz + r * sz * math.cos(math.pi * i / ring)) for j in range(seg)] for i in range(ring + 1)]
    F = []
    for i in range(ring):
        for j in range(seg):
            a, b, c, d = V[i][j], V[i][(j + 1) % seg], V[i + 1][(j + 1) % seg], V[i + 1][j]
            if i == 0: F.append([a, d, c])
            elif i == ring - 1: F.append([a, d, b])
            else: F.append([a, d, c, b])
    return F
def cyl(A, B, r0, r1, seg=6):
    d = [B[k] - A[k] for k in range(3)]; L = math.sqrt(sum(q * q for q in d)); w = [q / L for q in d]
    t = (1, 0, 0) if abs(w[0]) < 0.9 else (0, 1, 0)
    u = [w[1] * t[2] - w[2] * t[1], w[2] * t[0] - w[0] * t[2], w[0] * t[1] - w[1] * t[0]]; ul = math.sqrt(sum(q * q for q in u)); u = [q / ul for q in u]
    v = [w[1] * u[2] - w[2] * u[1], w[2] * u[0] - w[0] * u[2], w[0] * u[1] - w[1] * u[0]]
    ring = lambda C, r: [tuple(C[k] + r * (math.cos(2 * math.pi * j / seg) * u[k] + math.sin(2 * math.pi * j / seg) * v[k]) for k in range(3)) for j in range(seg)]
    a, b = ring(A, r0), ring(B, r1); F = [[a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]] for j in range(seg)]
    F.append(list(reversed(a))); F.append(list(b)); return F
def bush_parts(x, y, z0, P, seed=11):
    """P: r (crown radius), sz (squash), top (crown top height above z0), lump (lump radius), lo (lump offset), stem (stem radius)"""
    rnd = random.Random(seed); parts = []
    r, sz = P['r'], P['sz']; zc = z0 + P['top'] - r * sz
    parts.append(ellipsoid(x, y, zc, r, sz))
    for k in range(5):
        a = 2 * math.pi * k / 5 + rnd.random(); rr = P['lump'] * (0.85 + 0.3 * rnd.random())
        parts.append(ellipsoid(x + P['lo'] * math.cos(a), y + P['lo'] * math.sin(a), zc + 0.3 + rnd.random() * 0.8, rr, 0.95, 8, 4))
    zb = zc - r * sz + 1.0; s = P['stem']
    for (a, b, rad) in (((0, 0, -0.5), (0, 0, 1.3), 1.0), ((0, 0, 0.9), (-3.4, 3.4, zb - z0 + 2.2), 0.85), ((0, 0, 0.9), (3.4, -3.4, zb - z0 + 2.2), 0.85),
                        ((0, 0, 1.6), (2.0, 2.0, zb - z0 + 1.8), 0.5), ((0, 0, 1.6), (-2.0, -2.0, zb - z0 + 1.8), 0.5)):
        parts.append(cyl((x + a[0], y + a[1], z0 + a[2]), (x + b[0], y + b[1], z0 + b[2]), s * rad, s * rad * 0.75))
    return parts
