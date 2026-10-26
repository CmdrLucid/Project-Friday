"""STYLE C house kit (2026-10-25, user: 'Turm und Haeuser'): the Massan log house of asset 1 made PARAMETRIC, so every house of a room gets its own
footprint, door side, windows and roof instead of a stretched copy of house A.  Same construction as lib/massan_a.py build() (logs every 8 units with a
dark core behind them, post pairs at the corners and beside the door, eave roll + bulging hip roof, ridge sticks), generalised to:
  rectangles (hip roof: the inset contour degenerates into a ridge along the long side), any door side, several round / boarded windows,
  roof hatches (the pale raised smoke-hole covers of the picture), several storeys (the tower: tall walls, a banner and a sign board).
Measures from house A / the picture: logs r 4, eave z 50 for one storey, thatch top 77 (house A) or flatter (the other houses ~66).
Spec (game coordinates, all optional except the box):  house(spec) with spec = dict(X0, X1, Y0, Y1  wall planes (log front surfaces),
  ZE eave, ZT thatch top, door=dict(side, a0, a1, top), windows=[dict(side, a, z, R)], boards=[dict(side, a, z)], hatches=[(x, y)],
  banner=dict(side, a, z), sign=dict(side, a, z), sticks=True, overhang=1.5, lip=3.5, seed)."""
import math, random
import bpy
import blx, cmat
from massan_a import G
RL = 4.0; EXT = 4.0; POST_R = 2.2
CORNER_IN = 7.5; WIN_GAP = 15.0                                                   # post places (user feedback 4, 2026-10-26)

class House:
    def __init__(s, sp):
        s.sp = sp; s.X0, s.X1, s.Y0, s.Y1 = sp["X0"], sp["X1"], sp["Y0"], sp["Y1"]
        s.CX, s.CY = (s.X0 + s.X1) / 2, (s.Y0 + s.Y1) / 2
        s.ZE = sp.get("ZE", 50.0); s.ZT = sp.get("ZT", 77.0)
        e = sp.get("eave_out", 4.0)
        s.HXx = (s.X1 - s.X0) / 2 + e; s.HXy = (s.Y1 - s.Y0) / 2 + e           # roof half sizes (house A: 41 = 37 + 4)
        s.rnd = random.Random(sp.get("seed", 5))
    def wall_pos(s, side, along, out, z):
        if side == "S": return (along, s.Y1 + out, z)
        if side == "N": return (along, s.Y0 - out, z)
        if side == "E": return (s.X1 + out, along, z)
        return (s.X0 - out, along, z)
    def span(s, side): return (s.X0, s.X1) if side in "NS" else (s.Y0, s.Y1)
    def rz(s, t, hmin):
        f = s.sp.get("flat", 0.0)                                                # flat > 0: the roof reaches its top after f * the half size and stays flat
        if f: q = min(max(t, 0.0) / (f * hmin), 1.0); return s.ZE + (s.ZT - s.ZE) * (1 - (1 - q) ** 2.2)
        q = min(max(t, 0.0), hmin) / hmin; return s.ZE + (s.ZT - s.ZE) * (1 - (1 - q) ** 1.25)
    def contour(s, t, hx, hy, rc0=6.0, K=(24, 5)):
        """the roof ring at inset t: a rounded rectangle (hx - t, hy - t); point count fixed so that the rings can be joined."""
        ax = max(hx - t, 0.0); ay = max(hy - t, 0.0); rc = min(max(rc0 - t, 0.0), ax, ay); pts = []
        corners = [(ax - rc, ay - rc, 0), (-(ax - rc), ay - rc, 90), (-(ax - rc), -(ay - rc), 180), (ax - rc, -(ay - rc), 270)]
        for ci, (cx, cy, a0) in enumerate(corners):
            for j in range(K[1]):
                a = math.radians(a0 + 90 * j / (K[1] - 1)); pts.append((s.CX + cx + rc * math.cos(a), s.CY + cy + rc * math.sin(a)))
            nx, ny, _ = corners[(ci + 1) % 4]; ex, ey = pts[-1]; a = math.radians(a0 + 90)
            tx, ty = s.CX + nx + rc * math.cos(a), s.CY + ny + rc * math.sin(a)
            for j in range(1, K[0]): pts.append((ex + (tx - ex) * j / K[0], ey + (ty - ey) * j / K[0]))
        return pts
    def roof_z(s, x, y):
        """thatch height above a ground point (for hatches / sticks)."""
        hx = s.HXx + s.sp.get("overhang", 1.5); hy = s.HXy + s.sp.get("overhang", 1.5); off = s.sp.get("overhang", 1.5)
        t = min(hx - abs(x - s.CX), hy - abs(y - s.CY)); return s.rz(t - off, min(s.HXx, s.HXy))

    def build(s, M, nseg=20, den=1.0, roof_jitter=0.5):
        sp = s.sp; rnd = s.rnd; d = sp.get("door")
        logs = [-1.5 + 8 * k for k in range(int((s.ZE - 3.5) / 8) + 1)]
        M.box("dark", s.X0 + RL, s.X1 - RL, -(s.Y1 - RL), -(s.Y0 + RL), 0, s.ZE - 1)
        holes = ([(d["side"], d["a0"], d["a1"], -9, d["top"])] if d else []) + \
                [(q["side"], q["a"] - q.get("w", 10) / 2, q["a"] + q.get("w", 10) / 2, q["z"] - q.get("h", 12) / 2, q["z"] + q.get("h", 12) / 2) for q in sp.get("squares", [])]
        for side in "NSEW":
            L0, L1 = s.span(side)
            for zc in logs:
                r = RL * (0.92 if rnd.random() > 0.5 else 0.88); segs = [(L0 - EXT, L1 + EXT)]
                for (hs, a0, a1, z0, z1) in holes:                               # logs crossing an opening are cut (door, square windows)
                    if hs != side or not (z0 - 2.0 < zc < z1 + 2.0): continue          # only logs whose CENTRE lies in the opening (else the door / window grew by half a log)
                    segs = [q for a, b in segs for q in ((a, min(b, a0)), (max(a, a1), b)) if q[1] - q[0] > 1.0]
                for a, b in segs:
                    M.cylinder("bark", G(*s.wall_pos(side, a, -RL, zc)), G(*s.wall_pos(side, b, -RL, zc)), r, n=nseg, cap="endgrain", density=den)
            # posts like the picture of houses B..F (user 2026-10-25: the pairs were 'zu viel und falsch platziert'): ONE post at each corner, one on
            # each side of every door / window opening, one more only on a long blank stretch; forked (Y) tops carrying the eave
            ops = [(d["a0"], d["a1"])] if d and side == d["side"] else []
            ops += [(q["a"] - q.get("w", 10) / 2, q["a"] + q.get("w", 10) / 2) for q in sp.get("squares", []) if q["side"] == side]
            rws = [(q["a"] - q.get("R", 7.5) - 1, q["a"] + q.get("R", 7.5) + 1) for q in sp.get("windows", []) + sp.get("boards", []) if q["side"] == side]
            # user 2026-10-26 (feedback 4, tower): the posts of two walls met IN the corner edge -> corner posts stand CORNER_IN in from the corner (the log ends
            # interlock at the edge as in the picture) and are left out when an opening's post is closer than 20; round / boarded windows keep WIN_GAP to their
            # posts (picture of the tower: posts ~24 from the window centre), doors and square windows 3.5
            opost = [a0 - 3.5 for a0, a1 in ops] + [a1 + 3.5 for a0, a1 in ops] + [a0 - WIN_GAP for a0, a1 in rws] + [a1 + WIN_GAP for a0, a1 in rws]
            ops += rws
            posts = [c for c in (L0 + CORNER_IN, L1 - CORNER_IN) if all(abs(c - o) >= 20 for o in opost)] + [o for o in opost if L0 + 4 < o < L1 - 4]
            if sp.get("post_pairs"): posts = [L0 + 9, L0 + 16, L1 - 16, L1 - 9] + ([d["a0"] - 3.5, d["a1"] + 3.5] if d and side == d["side"] else [])
            posts = sorted(posts); extra = []
            for p0, p1 in zip(posts, posts[1:]):
                if p1 - p0 > 46: extra.append((p0 + p1) / 2)
            for a in sorted(posts + extra):
                if any(a0 - 2 < a < a1 + 2 for a0, a1 in ops): continue
                top = s.ZE - 3 + rnd.random() * 1.2; po = POST_R - 0.6
                M.cylinder("post", G(*s.wall_pos(side, a, po, -1)), G(*s.wall_pos(side, a, po, top - 5)), POST_R, n=nseg, cap="endgrain", density=den)
                for sg in (-1, 1):                                               # the fork: two short branches spreading along the wall under the eave
                    M.cylinder("post", G(*s.wall_pos(side, a, po, top - 5.5)), G(*s.wall_pos(side, a + sg * 2.6, po + 0.3, top + 1.0)), POST_R * 0.62, n=max(8, nseg // 2), cap="endgrain", density=den)
        if d:                                                                    # open dark doorway (house A 'open'), lintel, step
            sd = d["side"]
            M.face("dark", [G(*s.wall_pos(sd, d["a0"], -1.2, 0)), G(*s.wall_pos(sd, d["a1"], -1.2, 0)), G(*s.wall_pos(sd, d["a1"], -1.2, d["top"])), G(*s.wall_pos(sd, d["a0"], -1.2, d["top"]))][::-1] if sd in "ES" else
                   [G(*s.wall_pos(sd, d["a0"], -1.2, 0)), G(*s.wall_pos(sd, d["a1"], -1.2, 0)), G(*s.wall_pos(sd, d["a1"], -1.2, d["top"])), G(*s.wall_pos(sd, d["a0"], -1.2, d["top"]))], [(0, 0), (16, 0), (16, 16), (0, 16)])
        for (hs, a0, a1, z0, z1) in holes[1 if d else 0:]:                       # square windows: dark opening set back like the door (picture)
            q = [G(*s.wall_pos(hs, a0, -1.2, z0)), G(*s.wall_pos(hs, a1, -1.2, z0)), G(*s.wall_pos(hs, a1, -1.2, z1)), G(*s.wall_pos(hs, a0, -1.2, z1))]
            M.face("dark", q[::-1] if hs in "ES" else q, [(0, 0), (16, 0), (16, 16), (0, 16)])
        for w in sp.get("windows", []):                                          # round window: ring + dark hole
            R = w.get("R", 7.5); c0 = G(*s.wall_pos(w["side"], w["a"], 0.8, w["z"])); e1 = G(*s.wall_pos(w["side"], w["a"] + 1, 0.8, w["z"])); e2 = G(*s.wall_pos(w["side"], w["a"], 0.8, w["z"] + 1))
            M.torus("post", c0, tuple(e1[i] - c0[i] for i in range(3)), tuple(e2[i] - c0[i] for i in range(3)), R, 2.0, n=max(24, nseg * 2), m=8)
            pts = [G(*s.wall_pos(w["side"], w["a"] + (R - 1.5) * math.cos(2 * math.pi * i / 16), 0.9, w["z"] + (R - 1.5) * math.sin(2 * math.pi * i / 16))) for i in range(16)]
            M.face("hole", pts[::-1] if w["side"] in "ES" else pts, [(8 + 8 * math.cos(2 * math.pi * i / 16), 8 + 8 * math.sin(2 * math.pi * i / 16)) for i in range(16)][::-1])
        for b in sp.get("boards", []):                                           # boarded window: dark hole + three slanted planks nailed over it
            a, z = b["a"], b["z"]
            pts = [G(*s.wall_pos(b["side"], a + dx, 0.6, z + dz)) for dx, dz in ((-6, -6), (6, -6), (6, 6), (-6, 6))]
            M.face("hole", pts[::-1] if b["side"] in "ES" else pts, [(0, 0), (16, 0), (16, 16), (0, 16)])
            for k in (-4.0, 0.0, 4.0):
                M.cylinder("plank", G(*s.wall_pos(b["side"], a + k - 4.5, 1.6, z - 7)), G(*s.wall_pos(b["side"], a + k + 4.5, 1.6, z + 7)), 1.5, n=6, density=den)
        for bn in [sp["banner"]] if sp.get("banner") else []:                    # tower: a blue cloth hanging in two swags under a rod
            a, z = bn["a"], bn["z"]; hw = bn.get("w", 9.0)                         # a blue cloth hanging out of a window: over the sill, down the wall
            for k in range(8):
                u0, u1 = -hw + 2 * hw * k / 8, -hw + 2 * hw * (k + 1) / 8
                drop = lambda u: 14.0 + 4.0 * math.cos(math.pi * u / hw) + 1.5 * math.sin(3.1 * u)
                for (o0, z0_, o1, z1_) in ((-1.5, z + 0.8, 1.8, z + 0.8), (1.8, z + 0.8, 2.4, z - 3.0)):          # over the sill
                    q = [s.wall_pos(bn["side"], a + u0, o0, z0_), s.wall_pos(bn["side"], a + u1, o0, z0_), s.wall_pos(bn["side"], a + u1, o1, z1_), s.wall_pos(bn["side"], a + u0, o1, z1_)]
                    M.face("cloth", [G(*p) for p in (q[::-1] if bn["side"] in "ES" else q)], [(0, 0), (1, 0), (1, 1), (0, 1)])
                q = [s.wall_pos(bn["side"], a + u0, 2.4, z - 3.0), s.wall_pos(bn["side"], a + u1, 2.4, z - 3.0), s.wall_pos(bn["side"], a + u1, 2.0, z - 3.0 - drop(u1)), s.wall_pos(bn["side"], a + u0, 2.0, z - 3.0 - drop(u0))]
                M.face("cloth", [G(*p) for p in (q[::-1] if bn["side"] in "ES" else q)], [(0, 0), (1, 0), (1, 1), (0, 1)])
        for sg in [sp["sign"]] if sp.get("sign") else []:                        # tower: a grey metal plate with a pale animal head HANGING on a cord from a nail
            a, z, sd_ = sg["a"], sg["z"], sg["side"]; W2, H2 = 7.5, 8.5
            def bx(mat, u0, u1, v0, v1, o0, o1):
                p0 = s.wall_pos(sd_, a + u0, o0, z + v0); p1 = s.wall_pos(sd_, a + u1, o1, z + v1)
                M.box(mat, min(p0[0], p1[0]), max(p0[0], p1[0]), -max(p0[1], p1[1]), -min(p0[1], p1[1]), z + v0, z + v1)
            bx("signframe", -W2, W2, -H2, H2, 1.6, 2.6)                          # darker rim
            bx("signplate", -W2 + 1.3, W2 - 1.3, -H2 + 1.3, H2 - 1.3, 2.6, 2.9)      # grey plate
            for (u0, u1, v0, v1) in ((-2.0, 2.2, -4.5, 1.5), (-3.2, 3.4, 0.5, 3.0), (-4.6, -2.6, 2.6, 4.6), (2.8, 4.8, 2.6, 4.6), (-1.2, 1.4, -6.0, -4.5)):
                bx("bone", u0, u1, v0, v1, 2.9, 3.3)                             # the animal head: snout, brow, ears / horns, chin
            M.cylinder("dark", G(*s.wall_pos(sd_, a, 1.0, z + H2 + 7.0)), G(*s.wall_pos(sd_, a, 2.4, z + H2 + 7.0)), 0.7, n=6, density=den)   # the nail
            for sg_ in (-1, 1):                                                  # the cord to both upper corners
                M.cylinder("dark", G(*s.wall_pos(sd_, a, 2.2, z + H2 + 7.0)), G(*s.wall_pos(sd_, a + sg_ * (W2 - 1.5), 2.4, z + H2 - 0.5)), 0.35, n=5, density=den)
        # roof: eave roll + bulging hip roof
        off = sp.get("overhang", 1.5); hx = s.HXx + off; hy = s.HXy + off; hmin = min(s.HXx, s.HXy); LIP = sp.get("lip", 3.5); rings = []
        def rzz(t): return s.rz(t - off, hmin) if t >= off else s.ZE - (off - t) * 0.62
        ze = rzz(LIP)
        for k in range(7):
            phi = math.radians(-90 + 180 * k / 6); pts = s.contour(LIP * (1 - math.cos(phi)), hx, hy); jit = math.cos(phi) * roof_jitter
            pts = [(x + (rnd.random() - 0.5) * jit, y + (rnd.random() - 0.5) * jit) for x, y in pts]
            rings.append((pts, ze - LIP + LIP * math.sin(phi)))
        tmax = min(hx, hy) - 0.8
        for k in range(1, 17):
            t = LIP + (tmax - LIP) * k / 16; rings.append((s.contour(t, hx, hy), rzz(t)))
        tex = lambda x, y: ((x - (s.CX - hx)) * den, ((s.CY + hy) - y) * den)
        for (A, za), (B, zb) in zip(rings, rings[1:]):
            n = len(A)
            for i in range(n):
                j = (i + 1) % n
                M.face("thatch", [G(A[i][0], A[i][1], za), G(A[j][0], A[j][1], za), G(B[j][0], B[j][1], zb), G(B[i][0], B[i][1], zb)], [tex(*A[i]), tex(*A[j]), tex(*B[j]), tex(*B[i])])
        under, zu = rings[0]; M.face("under", [G(x, y, zu) for x, y in under], [(x * den, y * den) for x, y in under])
        top, zt = rings[-1]; M.face("thatch", [G(x, y, zt) for x, y in top], [tex(x, y) for x, y in top])
        for (hxp, hyp) in sp.get("hatches", []):                                 # smoke-hole cover: a pale thatch cap on four short legs
            zr = s.roof_z(hxp, hyp)
            M.box("thatch", hxp - 7, hxp + 7, -(hyp + 5), -(hyp - 5), zr + 2.0, zr + 4.2)
            M.box("under", hxp - 5, hxp + 5, -(hyp + 3.5), -(hyp - 3.5), zr - 1.0, zr + 2.0)
        if sp.get("knot", True):                                                 # straw bundle on the top tied with a band (house A, ridge_knot)
            kx, ky = s.CX, s.CY; zk = s.roof_z(kx, ky)
            for k in range(10):
                a0 = 2 * math.pi * k / 10; a1 = 2 * math.pi * (k + 1) / 10
                for j in range(6):
                    p = lambda a, jj: (kx + 5.5 * math.cos(a) * math.cos(math.pi / 2 * jj / 6), ky + 5.5 * math.sin(a) * math.cos(math.pi / 2 * jj / 6), zk - 2.5 + 4.5 * math.sin(math.pi / 2 * jj / 6))
                    q = [p(a0, j), p(a1, j), p(a1, j + 1), p(a0, j + 1)]
                    M.face("thatch", [G(*v) for v in q], [tex(v[0], v[1]) for v in q])
            M.torus("post", G(kx, ky, zk - 1.2), (1, 0, 0), (0, 1, 0), 5.3, 0.6, n=24, m=6)
        if sp.get("sticks", True):                                               # crossed pairs of short sticks on the ridge (at both ridge ends if long)
            long_x = s.HXx >= s.HXy; ridge = abs(s.HXx - s.HXy)
            spots = [(s.CX, s.CY)]
            for (sx, sy) in spots:
                zr = s.roof_z(sx, sy)
                for ax in (0, 1):
                    for sgn in (-1, 1):
                        dw, dz = 6.5, 5.5
                        if ax == 0: p0, p1 = (sx - dw * sgn, sy + 1.4 * sgn, zr - 3), (sx + dw * sgn, sy + 1.4 * sgn, zr - 3 + 2 * dz)
                        else: p0, p1 = (sx + 1.4 * sgn, sy - dw * sgn, zr - 3), (sx + 1.4 * sgn, sy + dw * sgn, zr - 3 + 2 * dz)
                        M.cylinder("post", G(*p0), G(*p1), 1.6, n=max(8, nseg - 2), cap="endgrain", density=den)

def materials():
    names = ("bark", "post", "endgrain", "dark", "hole", "thatch", "under", "bone", "plank")
    ms = [cmat.get(n) for n in names]
    cl = bpy.data.materials.get("cloth") or cmat.pmat("cloth", (24, 60, 140), (70, 120, 200), scale=0.3, bump=0.2, rough=0.8)
    sp = bpy.data.materials.get("signplate") or cmat.pmat("signplate", (128, 132, 136), (170, 174, 176), scale=0.4, bump=0.1, rough=0.45)
    sf = bpy.data.materials.get("signframe") or cmat.pmat("signframe", (60, 62, 66), (90, 92, 96), scale=0.4, bump=0.1, rough=0.5)
    return ms + [cl, sp, sf]

def house(spec, name="house", z0=0.0):
    """builds one house and returns its object (placed on ground z0)."""
    M = blx.Mesh(name, materials()); M.density = 1.0
    House(spec).build(M)
    ob = M.finish()
    for p in ob.data.polygons: p.use_smooth = True
    ob.location.z = z0; return ob
