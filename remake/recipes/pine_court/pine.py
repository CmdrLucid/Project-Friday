#!/usr/bin/env python3
"""pine.py - the courtyard PINE of the Mercator castle (rooms 32 / 33, tileset 14: its own sprite, not in the object catalogue) as a near-final
3D model (the approved style C pine of remake/lib/kit_c.py pine(): star-shaped drooping tiers + trunk with a root flare) in pure Python, and the
light shapes of every drawn pine (memory feedback-precise-light-shapes).
  pine_parts(x, y, z0, P, seed) -> list of closed solids (lists of faces) in GAME coordinates (x east, y south, z up)
  python3 pine.py OUT_PREFIX ROOM feet.json [params.json] -> OUT_PREFIX_ROOM.obj with every pine of the room
params_light.json: fitted to the drawn sprite (silhouette, see README.md): H = crown top above the ground, R = radius of the lowest tier,
zb = bottom of the lowest tier, tiers, droop / notch shape, trunk radius."""
import json, math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def tier_solid(x, y, z0t, r, h, n, rot, rnd, P):
    """one star-shaped tier: tips out and drooping, notches in and up; closed (ring -> mid -> top, ring -> under)"""
    ring, mid = [], []
    for k in range(2 * n):
        a = rot + math.pi * k / n; tip = k % 2 == 0
        rr = r * (1.0 if tip else P['notch']) * (1 + (rnd.random() - 0.5) * 0.10)
        zz = z0t + (-P['droop'] if tip else 0.8) + (rnd.random() - 0.5) * 0.5
        ring.append((x + rr * math.cos(a), y + rr * math.sin(a), zz))
        mid.append((x + 0.55 * r * math.cos(a), y + 0.55 * r * math.sin(a), z0t + h * 0.45))
    top = (x, y, z0t + h); under = (x, y, z0t - 0.5); m = len(ring); F = []
    for k in range(m):
        F.append([ring[k], ring[(k + 1) % m], mid[(k + 1) % m], mid[k]])
        F.append([mid[k], mid[(k + 1) % m], top])
        F.append([ring[(k + 1) % m], ring[k], under])
    return F

def cyl(x, y, z0, z1, r0, r1, seg=12):
    b = [(x + r0 * math.cos(2 * math.pi * k / seg), y + r0 * math.sin(2 * math.pi * k / seg), z0) for k in range(seg)]
    t = [(x + r1 * math.cos(2 * math.pi * k / seg), y + r1 * math.sin(2 * math.pi * k / seg), z1) for k in range(seg)]
    F = [b[::-1], t]
    for k in range(seg): F.append([b[k], b[(k + 1) % seg], t[(k + 1) % seg], t[k]])
    return F

def pine_parts(x, y, z0, P, seed=11):
    rnd = random.Random(seed); parts = []; T = P['tiers']
    for i in range(T):
        f = i / T; z0t = z0 + P['zb'] + f * (P['H'] - P['zb'] - P['th']); r = P['R'] * (1 - P['taper'] * f) + 1.0; h = P['th'] - 3.0 * f
        parts.append(tier_solid(x, y, z0t, r, h, 14 - i, rnd.random() * math.pi, rnd, P))
    parts.append(cyl(x, y, z0 + 1.5, z0 + P['zb'] + 2, P['tr'], P['tr'] * 0.8))       # trunk
    parts.append(cyl(x, y, z0, z0 + 2.0, P['tr'] * 1.7, P['tr']))                       # root flare
    return parts

def write_obj(path, parts, title):
    V, out, vid = [], [], {}
    for pi, F in enumerate(parts):   # vertices shared inside a part (closed solids: every edge has its twin), never across parts
        for f in F:
            idx = []
            for p in f:
                k = (pi, round(p[0], 3), round(p[1], 3), round(p[2], 3))
                if k not in vid: V.append(p); vid[k] = len(V)
                idx.append(vid[k])
            out.append("f " + " ".join(map(str, idx)))
    with open(path, "w") as fo:
        fo.write("# %s (remake/recipes/pine_court/pine.py). GAME coordinates x east, y south, z up, world units.\n" % title)
        fo.write("# our own geometry fitted to the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        for v in V: fo.write("v %.3f %.3f %.3f\n" % v)
        fo.write("\n".join(out) + "\n")
    print("%s: %d faces" % (path, len(out)))

if __name__ == "__main__":
    pre, room, feet = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
    P = json.load(open(sys.argv[4] if len(sys.argv) > 4 else os.path.join(HERE, "params_light.json")))
    parts = []
    for k, (x, y, z) in enumerate(feet[room]): parts += pine_parts(x, y, z, P, seed=11 + k)
    write_obj("%s_%s.obj" % (pre, room), parts, "courtyard pines of room %s" % room)
