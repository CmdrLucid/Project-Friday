"""MASSAN LOG HOUSE builder for the LIGHT variant (as drawn), generalised from remake/lib/massan_a.py (house A, which stays the remake's source):
rectangular footprints, any number of doors / round windows / boarded windows, a ground height z0, ridge sticks or a ridge log bundle, roof vents.
GAME coordinates (x east, y south, z up). One house = a dict:
  planes (X0, X1, Y0, Y1): log FRONT surfaces (cell lines inset 3, house A 291 / 365 / 435 / 509), z0 ground, ze eave (50 above z0), zt thatch top
  (77 above z0); doors [(side, a0, a1, top)], windows [(side, a, z)] round, boards [(side, a0, a1, z0, z1)] boarded windows, posts {side: [a, ...]},
  ridge 'sticks' (crossed sticks, house A) or 'bundle' (logs along the ridge), vents [(x, y)] squat roof vents.
Logs r 4 every 8 units, centres 4 behind the plane, ends 4 past the corner (massan_a); the log just above a door runs over it (user 2026-11-20).
Used inside Blender by remake/recipes/proxy_houses_592.py."""
import math, random
import massan_a as A

RL, EXT, POST_R = A.RL, A.EXT, A.POST_R

def build(M, h, nseg=8, lip=3.5):
    X0, X1, Y0, Y1 = h["planes"]; z0 = h.get("z0", 0.0); ZE = z0 + h.get("ze", 50.0); ZT = z0 + h.get("zt", 77.0)
    CX, CY = (X0 + X1) / 2, (Y0 + Y1) / 2
    G = lambda x, y, z: (x, -y, z)
    rnd = random.Random(5)
    def wall_pos(side, along, out, z):        # a point on the wall plane of a side ('along' = x for N / S, y for E / W), 'out' units in front of it
        if side == "S": return (along, Y1 + out, z)
        if side == "N": return (along, Y0 - out, z)
        if side == "E": return (X1 + out, along, z)
        return (X0 - out, along, z)
    LOG_Z = [z0 - 1.5 + 8 * k for k in range(int((ZE - z0 + 1.5) // 8) + 1)]
    M.box("dark", X0 + RL, X1 - RL, -(Y1 - RL), -(Y0 + RL), z0, ZE - 1)
    doors = h.get("doors", [])
    for side in "NSEW":
        L0, L1 = (X0, X1) if side in "NS" else (Y0, Y1)
        for zc in LOG_Z:
            r = RL * (0.92 if rnd.random() > 0.5 else 0.88)
            cuts = sorted([(a0, a1) for s, a0, a1, top in doors if s == side and zc < z0 + top] +
                          [(a0, a1) for s, a0, a1, zb, zt_, out in h.get("shutters", []) if s == side and z0 + zb < zc < z0 + zt_])
            ne = h.get("noext", ())   # (side, 0 / 1): the logs of this side do NOT stick out past the corner at its start / end (as drawn)
            ex = h.get("ext", {})      # (side, 0 / 1) -> how far the logs stick out past that corner (default EXT 4)
            # noext: the logs end 2 RL INSIDE the crossing wall (behind its logs), so their end grain does not show as a stack of discs at the corner
            e0 = -2 * RL if (side, 0) in ne else ex.get((side, 0), EXT); e1 = -2 * RL if (side, 1) in ne else ex.get((side, 1), EXT)
            segs, a = [], L0 - e0
            for a0, a1 in cuts: segs.append((a, a0)); a = a1
            segs.append((a, L1 + e1))
            for a, b in segs:
                if b - a > 0.5: M.cylinder("bark", G(*wall_pos(side, a, -RL, zc)), G(*wall_pos(side, b, -RL, zc)), r, n=nseg, cap="endgrain", density=1.0)
        for a in h.get("posts", {}).get(side, []):
            top = ZE - 3 + rnd.random() * 1.2
            M.cylinder("post", G(*wall_pos(side, a, POST_R - 0.6, z0 - 1)), G(*wall_pos(side, a, POST_R - 0.6, top)), POST_R, n=nseg, cap="endgrain", density=1.0)
    for s, a0, a1, top in doors:                # open dark doorway set back to the core, lintel log, threshold (massan_a door 'open')
        M.face("dark", [G(*wall_pos(s, a0, -1.2, z0)), G(*wall_pos(s, a1, -1.2, z0)), G(*wall_pos(s, a1, -1.2, z0 + top)), G(*wall_pos(s, a0, -1.2, z0 + top))][::-1 if s in "SE" else 1],
               [(0, 0), (1, 0), (1, 1), (0, 1)])
        M.cylinder("post", G(*wall_pos(s, a0 - 3, 1.2, z0 + top + 2.0)), G(*wall_pos(s, a1 + 3, 1.2, z0 + top + 2.0)), 2.7, n=nseg, cap="endgrain", density=1.0)
        p0 = wall_pos(s, a0 - 1, 3.0, z0); p1 = wall_pos(s, a1 + 1, -2 * RL, z0 + 1.2)
        M.box("post", min(p0[0], p1[0]), max(p0[0], p1[0]), -max(p0[1], p1[1]), -min(p0[1], p1[1]), z0, z0 + 1.2)
    for s, a, z in h.get("windows", []):        # round window: ring + dark hole (massan_a WINDOW R 7.5, r 2, hole 6)
        c0 = G(*wall_pos(s, a, 0.8, z0 + z)); e1 = G(*wall_pos(s, a + 1, 0.8, z0 + z)); e2 = G(*wall_pos(s, a, 0.8, z0 + z + 1))
        M.torus("post", c0, tuple(e1[i] - c0[i] for i in range(3)), tuple(e2[i] - c0[i] for i in range(3)), 7.5, 2.0, n=24, m=8)
        pts = [G(*wall_pos(s, a + 6 * math.cos(2 * math.pi * i / 16), 0.9, z0 + z + 6 * math.sin(2 * math.pi * i / 16))) for i in range(16)]
        M.face("hole", pts[::-1] if s in "SE" else pts, [(0, 0)] * 16)
    def quad_box(c):   # 8 corners (bottom 4 then top 4, game coordinates) -> 6 faces
        P = [G(*q) for q in c]
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            M.face("plank", [P[i] for i in f][::-1], [(0, 0)] * 4)
    for s, a0, a1, zb, zt_, out in h.get("shutters", []):   # window with a SHUTTER hinged at the top and propped out at the bottom (user 2026-11-20)
        M.face("dark", [G(*wall_pos(s, a0, -1.5, z0 + zb)), G(*wall_pos(s, a1, -1.5, z0 + zb)), G(*wall_pos(s, a1, -1.5, z0 + zt_)), G(*wall_pos(s, a0, -1.5, z0 + zt_))][::-1 if s in "SE" else 1], [(0, 0)] * 4)
        th_ = 1.2; zh = z0 + zt_ + 1.0; zl = z0 + zb + 1.0          # hinge line just above the opening, the free edge out by 'out'
        c = []
        for zz, o in ((zl, out), (zh, 0.6)):
            for aa, oo in ((a0, o), (a1, o), (a1, o + th_), (a0, o + th_)): c.append(wall_pos(s, aa, oo, zz))
        quad_box([c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7]])
    for s, a0, a1, za, zb in h.get("boards", []):   # boarded window: a plank panel 1 unit proud of the log fronts
        p0 = wall_pos(s, a0, 0.0, z0 + za); p1 = wall_pos(s, a1, 1.0, z0 + zb)
        M.box("plank", min(p0[0], p1[0]), max(p0[0], p1[0]), -max(p0[1], p1[1]), -min(p0[1], p1[1]), z0 + za, z0 + zb)
    # roof: eave roll + bulging hip roof on a RECTANGLE (half sizes hx, hy = plane half sizes + 4); rings shrink equally on all sides, so a long
    # house ends in a ridge along its long axis (massan_a.rz profile: z = ZE + (ZT - ZE) * (1 - (1 - s) ** 1.25), s = inset / short half size)
    hx, hy = (X1 - X0) / 2 + 4, (Y1 - Y0) / 2 + 4; hs = min(hx, hy)
    def rz(t): s = min(max(t, 0.0), hs) / hs; return ZE + (ZT - ZE) * (1 - (1 - s) ** 1.25)
    def contour(t, rc0=6.0, K=(10, 5)):
        ax, ay = hx - t, hy - t; rc = max(min(rc0 - t, ax - 0.05, ay - 0.05), 0.0); pts = []
        corners = [(ax - rc, ay - rc, 0), (-(ax - rc), ay - rc, 90), (-(ax - rc), -(ay - rc), 180), (ax - rc, -(ay - rc), 270)]
        for ci, (cx, cy, a0) in enumerate(corners):
            for j in range(K[1]):
                a = math.radians(a0 + 90 * j / (K[1] - 1)); pts.append((CX + cx + rc * math.cos(a), CY + cy + rc * math.sin(a)))
            nx, ny, _ = corners[(ci + 1) % 4]; ex, ey = pts[-1]; a = math.radians(a0 + 90)
            tx, ty = CX + nx + rc * math.cos(a), CY + ny + rc * math.sin(a)
            for j in range(1, K[0]): pts.append((ex + (tx - ex) * j / K[0], ey + (ty - ey) * j / K[0]))
        return pts
    rings = []; ze = rz(lip)
    for k in range(7):
        phi = math.radians(-90 + 180 * k / 6); rings.append((contour(lip * (1 - math.cos(phi))), ze - lip + lip * math.sin(phi)))
    for k in range(1, 13):
        t = lip + (hs - 0.8 - lip) * k / 12; rings.append((contour(t), rz(t)))
    for (Ar, za), (Br, zb) in zip(rings, rings[1:]):
        n = len(Ar)
        for i in range(n):
            j = (i + 1) % n
            M.face("thatch", [G(Ar[i][0], Ar[i][1], za), G(Ar[j][0], Ar[j][1], za), G(Br[j][0], Br[j][1], zb), G(Br[i][0], Br[i][1], zb)], [(0, 0)] * 4)
    under, zu = rings[0]; M.face("under", [G(x, y, zu) for x, y in under], [(0, 0)] * len(under))
    top, ztop = rings[-1]; M.face("thatch", [G(x, y, ztop) for x, y in top], [(0, 0)] * len(top))
    if h.get("ridge", "sticks") == "sticks":     # two crossed pairs of short sticks at the top (house A)
        for ax in (0, 1):
            for sgn in (-1, 1):
                dw, dz = 6.5, 5.5
                if ax == 0: p0, p1 = (CX - dw * sgn, CY + 1.4 * sgn, ZT - 3), (CX + dw * sgn, CY + 1.4 * sgn, ZT - 3 + 2 * dz)
                else: p0, p1 = (CX + 1.4 * sgn, CY - dw * sgn, ZT - 3), (CX + 1.4 * sgn, CY + dw * sgn, ZT - 3 + 2 * dz)
                M.cylinder("post", G(*p0), G(*p1), 1.6, n=6, cap="endgrain", density=1.0)
    else:                                        # ridge log bundle along the long axis (house B): three logs on the ridge
        L = abs(hx - hy) + 6
        for dz, off in ((ztop + 1.5, -2.2), (ztop + 1.5, 2.2), (ztop + 4.5, 0.0)):
            if hy >= hx: M.cylinder("post", G(CX + off, CY - L, dz), G(CX + off, CY + L, dz), 2.2, n=nseg, cap="endgrain", density=1.0)
            else: M.cylinder("post", G(CX - L, CY + off, dz), G(CX + L, CY + off, dz), 2.2, n=nseg, cap="endgrain", density=1.0)
    for vx, vy in h.get("vents", []):           # roof vent HOOD (user 2026-11-20: 'eckig, nicht rund'): a flat SQUARE thatch cap 12 x 12 on four short legs
        t = min(vx - (CX - hx), (CX + hx) - vx, vy - (CY - hy), (CY + hy) - vy); zb = rz(t); sv = 6.0
        for dx in (-sv + 1.5, sv - 1.5):
            for dy in (-sv + 1.5, sv - 1.5): M.cylinder("post", G(vx + dx, vy + dy, zb - 3), G(vx + dx, vy + dy, zb + 3), 0.8, n=6, cap="endgrain", density=1.0)
        M.box("thatch", vx - sv, vx + sv, -(vy + sv), -(vy - sv), zb + 3, zb + 6)
