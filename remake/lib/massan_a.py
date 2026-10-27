"""MASSAN HOUSE A (room 592, the lone house west of the statue): shared measurements + geometry for the three 'modern remake' variants
(user 2026-10-25: 'wie wuerdest du das Haus in einem modernen Remake darstellen? ... mach mal alle 3 Varianten zur Ansicht'):
  va = modelled 3D house + pixel textures cut from the original picture (tileable swatches, not projected), stepped light, outlines (HD-2D style)
  vb = voxel house: 1 voxel = 1 game pixel, the visible voxels take the original pixel, hidden ones a matching voxel of the visible side
  vc = smooth 'toy diorama' (no pixels): soft materials, rounded logs, tilt-shift depth of field
All in GAME coordinates (x east, y south, z up; 1 unit = 1 game pixel); G() converts to Blender (x, -y, z).  Measured on the user's picture
(remake/tools/rom_picture.py ROM 592 936 248 208 216 ~/.landstalker_remake/rooms/592_houseA --scale2x; rectified walls, brightness profiles 2026-10-25):
log front surface y 509 (south) / x 365 (east), logs radius 4 every 8 units (seams at z 2.5 + 8k, top light at the centre + 2), posts in pairs 9 / 16 units
from each corner, round window south at x 322 z 27, door east at y 466..482 up to z 35, skull sign above it, eave z 50 at the cell edge, thatch top z 77."""
import math, os
import numpy as np

X0, X1, Y0, Y1 = 291.0, 365.0, 435.0, 509.0          # log front surfaces (wall planes)
CX, CY = (X0 + X1) / 2, (Y0 + Y1) / 2
RL = 4.0                                             # log radius; centres 4 units behind the wall plane
LOG_Z = [-1.5 + 8 * k for k in range(7)]             # log centre heights (the lowest is half in the ground, the top one under the eave)
EXT = 4.0                                            # logs stick out past the corner
ZE, ZT = 50.0, 77.0                                  # eave (at the cell edge) and thatch top
HX = 41.0                                            # roof half size (edge 287..369)
POST_R = 2.2; POST_TOP = 47.0
POSTS = {"S": [300, 307, 349, 356], "N": [300, 307, 349, 356], "E": [445, 452, 464, 484, 492, 499], "W": [445, 452, 492, 499]}
DOOR = dict(side="E", a0=466.0, a1=482.0, top=35.0)
WINDOW = dict(side="S", a=322.0, z=27.0, R=7.5, r=2.0, hole=6.0)
SIGN = dict(side="E", a0=462.0, a1=478.0, z0=32.0, z1=48.0)

def G(x, y, z): return (x, -y, z)
def rz(t):
    """thatch height at inset t from the roof edge (bulging hip roof)."""
    s = min(max(t, 0.0), HX) / HX; return ZE + (ZT - ZE) * (1 - (1 - s) ** 1.25)
def wall_pos(side, along, out, z):
    """point on / in front of a wall: out = distance in front of the log front surface."""
    if side == "S": return (along, Y1 + out, z)
    if side == "N": return (along, Y0 - out, z)
    if side == "E": return (X1 + out, along, z)
    return (X0 - out, along, z)

# ---- the user's picture (local, from his ROM) -------------------------------------------------------------------------------------------------------
class Picture:
    def __init__(self, folder, name="layerA.png"):
        import bpy
        self.U0, self.V0, self.PW, self.PH, self.K = map(int, open(os.path.join(folder, "window.txt")).read().split())
        img = bpy.data.images.load(os.path.join(folder, name)); w, h = img.size
        self.a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]     # row 0 = top; values = sRGB / 255
        self.w, self.h = w, h
    def uv(self, x, y, z): return ((x - y + 1184 - self.U0) * self.K, ((x + y) / 2 - z - self.V0) * self.K)
    def at_many(self, x, y, z):
        """vectorised at(): arrays of world points -> (n, 4) colours (alpha 0 outside the picture)."""
        u = np.floor((x - y + 1184 - self.U0) * self.K).astype(int); v = np.floor(((x + y) / 2 - z - self.V0) * self.K).astype(int)
        ok = (u >= 0) & (u < self.w) & (v >= 0) & (v < self.h); c = self.a[np.clip(v, 0, self.h - 1), np.clip(u, 0, self.w - 1)].copy(); c[~ok] = 0; return c
    def at(self, x, y, z):
        u, v = self.uv(x, y, z); u, v = int(math.floor(u)), int(math.floor(v))
        if 0 <= u < self.w and 0 <= v < self.h: return self.a[v, u]
        return np.array((0, 0, 0, 0), np.float32)

def fold(v, lo, hi):
    """mirror-repeat v into [lo, hi] (tileable without a jump)."""
    L = hi - lo
    if L <= 0: return lo
    k = (v - lo) % (2 * L); return lo + (k if k <= L else 2 * L - k)

# ---- swatch textures cut from the picture (variant A) ------------------------------------------------------------------------------------------------
def bark_texture(pic, den=2, length=72):
    """one log, unrolled: x = along the log (repeated stretch x 309..345 of the south wall, between the posts, below the window),
    y = one turn (row 0 = top of the log, the front half from the picture, the back half mirrored)."""
    H = int(round(2 * math.pi * RL * den)); W = length * den; zc = LOG_Z[1]
    def f(tx, ty):
        x = 308.5 + (tx / den) % 33.0; a = 2 * math.pi * (ty + 0.5) / H
        if a > math.pi: a = 2 * math.pi - a                                   # back half = front half
        c = pic.at(x, Y1, zc + 3.0 - 7.0 * a / math.pi)                       # top of the log = its lit upper edge, bottom = the seam (as the picture draws it)
        return tuple(int(round(v * 255)) for v in c[:3])
    return f, W, H

def thatch_texture(pic, den=2):
    """top planar roof texture over the whole roof (texel 0,0 = north west corner of the roof edge): every roof face takes the straw of the
    SOUTH face of the picture at the same inset from the edge, mirror-repeated along the edge;
    inset beyond 30 (the ridge sticks) is folded back so the sticks are not painted on the roof."""
    N = int(2 * HX * den)
    def f(tx, ty):
        x = CX - HX + (tx + 0.5) / den; y = CY - HX + (ty + 0.5) / den
        dx, dy = HX - abs(x - CX), HX - abs(y - CY)
        south = dy <= dx; t = dy if south else dx; a = x if south else y; c0 = CX if south else CY
        along = fold(a, c0 - HX + t + 2, c0 + HX - t - 2) if t < HX - 4 else c0
        t = fold(t, 3.0, 17.0)
        for k in range(6):                                                     # every face takes the SOUTH face's straw (the east face has the sign); skip non-straw pixels
            c = pic.at(along if south else CX + (along - CY), CY + HX - t, rz(t))
            r, g, b = c[0], c[1], c[2]
            if c[3] > 0.5 and not (g > r + 0.08): break
            t = max(3.0, t - 3.0)
        return tuple(int(round(v * 255)) for v in c[:3])
    return f, N, N

def ground_texture(pic_full, n=64):
    """dirt: a patch of the picture's ground (plane B, both planes composed in full.png) south west of the house, mirror-repeated."""
    def f(tx, ty):
        u = int(fold(30 + tx, 30, 120)); v = int(fold(390 + ty, 390, 428))
        c = pic_full.a[v, u]; return tuple(int(round(q * 255)) for q in c[:3])
    return f, n, n

# ---- modelled geometry (variants A and C) ---------------------------------------------------------------------------------------------------------
def contour(t, rc0=6.0, K=(24, 5), hx0=HX):
    hx = hx0 - t; rc = max(rc0 - t, 0.0); pts = []
    corners = [(hx - rc, hx - rc, 0), (-(hx - rc), hx - rc, 90), (-(hx - rc), -(hx - rc), 180), (hx - rc, -(hx - rc), 270)]
    for ci, (cx, cy, a0) in enumerate(corners):
        for j in range(K[1]):
            a = math.radians(a0 + 90 * j / (K[1] - 1)); pts.append((CX + cx + rc * math.cos(a), CY + cy + rc * math.sin(a)))
        nx, ny, _ = corners[(ci + 1) % 4]; ex, ey = pts[-1]; a = math.radians(a0 + 90)
        tx, ty = CX + nx + rc * math.cos(a), CY + ny + rc * math.sin(a)
        for j in range(1, K[0]): pts.append((ex + (tx - ex) * j / K[0], ey + (ty - ey) * j / K[0]))
    return pts

def build(M, nseg=10, den=2.0, sign_uv=None, roof_jitter=1.4, hx=HX, lip=3.5, door="dark", door_top=None, course=0.0, step=0.0, ridge_knot=False):
    """adds the house to a blx.Mesh with materials bark, post, endgrain, dark, hole, thatch, under (+ 'sign' if sign_uv is given:
    function (x, y, z) -> texel uv of the sign image).  hx > HX = more roof overhang (the slope continues down past the picture's eave),
    lip = eave roll radius; door = 'dark' (opening as in the picture), 'open' (dark opening in a frame: jambs, lintel, threshold) or 'planks'
    (the frame + a plank door leaf + handle; needs material 'plank').  course / step > 0: the thatch is laid in overlapping courses (each course
    'course' units long down the slope, its butt end 'step' units proud of the one below); ridge_knot: a straw bundle at the top holding the sticks."""
    import random
    rnd = random.Random(5)
    # dark core: the seams between the logs show black like the original
    M.box("dark", X0 + RL, X1 - RL, -(Y1 - RL), -(Y0 + RL), 0, ZE - 1)      # behind the log centres
    for side in "NSEW":
        ns = side in "NS"; L0, L1 = (X0, X1) if ns else (Y0, Y1)
        for i, zc in enumerate(LOG_Z):
            r = RL * (0.92 if rnd.random() > 0.5 else 0.88)
            segs = [(L0 - EXT, L1 + EXT)]
            if side == DOOR["side"] and zc - r < (door_top or DOOR["top"]) + (1.0 if door_top else 0.0): segs = [(L0 - EXT, DOOR["a0"]), (DOOR["a1"], L1 + EXT)]
            for a, b in segs:
                pa = G(*wall_pos(side, a, -RL, zc)); pb = G(*wall_pos(side, b, -RL, zc))
                M.cylinder("bark", pa, pb, r, n=nseg, cap="endgrain", density=den)
        for i, a in enumerate(POSTS[side]):
            top = POST_TOP + rnd.random() * 1.2
            M.cylinder("post", G(*wall_pos(side, a, POST_R - 0.6, -1)), G(*wall_pos(side, a, POST_R - 0.6, top)), POST_R, n=nseg, cap="endgrain", density=den)
            M.cylinder("post", G(*wall_pos(side, a, POST_R - 0.6, top)), G(*wall_pos(side, a, POST_R - 0.6, top + 1.6)), POST_R * 0.7, n=nseg, cap="endgrain", density=den)
    # door: dark opening (or a plank door in a frame), lintel, threshold
    d = dict(DOOR, top=door_top or DOOR["top"]); s = d["side"]
    if door in ("planks", "open"):
        wd = d["a1"] - d["a0"]; inset = -2.6                                       # leaf: in front of the dark core (x 361), behind the log fronts
        for sgn, a in (((-1, d["a0"]), (1, d["a1"])) if door == "planks" else ()):  # jambs: square posts in the opening (the open doorway has none, like the picture)
            p = [wall_pos(s, a - sgn * 0.0, 1.2, 0), wall_pos(s, a - sgn * 2.2, -2 * RL + 0.5, d["top"] + 0.5)]
            M.box("post", min(p[0][0], p[1][0]), max(p[0][0], p[1][0]), -max(p[0][1], p[1][1]), -min(p[0][1], p[1][1]), 0, d["top"] + 0.5)
        if door == "open":                                                         # the dark opening, set back to the core like in the picture
            M.face("dark", [G(*wall_pos(s, d["a0"], -1.2, 0)), G(*wall_pos(s, d["a1"], -1.2, 0)), G(*wall_pos(s, d["a1"], -1.2, d["top"])), G(*wall_pos(s, d["a0"], -1.2, d["top"]))][::-1], [(0, 0), (16, 0), (16, 16), (0, 16)])
        n = 4 if door == "planks" else 0; pw = (wd - 4.4) / 4
        for k in range(n):                                                         # vertical planks, small gaps, slightly uneven tops
            a0 = d["a0"] + 2.2 + k * pw + 0.15; a1 = a0 + pw - 0.3; zt = d["top"] - 0.3 - rnd.random() * 0.6
            p0 = wall_pos(s, a0, inset - 1.0, 0); p1 = wall_pos(s, a1, inset, zt)
            M.box("plank", min(p0[0], p1[0]), max(p0[0], p1[0]), -max(p0[1], p1[1]), -min(p0[1], p1[1]), 0.2, zt)
        for zb in ((7.0, d["top"] - 8.0) if door == "planks" else ()):           # two battens across the planks
            p0 = wall_pos(s, d["a0"] + 2.6, inset, zb); p1 = wall_pos(s, d["a1"] - 2.6, inset + 0.8, zb + 2.2)
            M.box("post", min(p0[0], p1[0]), max(p0[0], p1[0]), -max(p0[1], p1[1]), -min(p0[1], p1[1]), zb, zb + 2.2)
        zh = d["top"] * 0.5
        if door == "planks":
            hc = G(*wall_pos(s, d["a1"] - 4.5, inset + 1.4, zh)); e1 = G(*wall_pos(s, d["a1"] - 3.5, inset + 1.4, zh)); e2 = G(*wall_pos(s, d["a1"] - 4.5, inset + 1.4, zh + 1))
            M.torus("dark", hc, tuple(e1[i] - hc[i] for i in range(3)), tuple(e2[i] - hc[i] for i in range(3)), 1.3, 0.35, n=16, m=6)
        M.cylinder("post", G(*wall_pos(s, d["a0"] - 3, 1.2, d["top"] + 2.0)), G(*wall_pos(s, d["a1"] + 3, 1.2, d["top"] + 2.0)), 2.7, n=nseg, cap="endgrain", density=den)
        p0 = wall_pos(s, d["a0"] - 1, 3.0, 0); p1 = wall_pos(s, d["a1"] + 1, -2 * RL, 1.2)       # stone-ish step
        M.box("post", min(p0[0], p1[0]), max(p0[0], p1[0]), -max(p0[1], p1[1]), -min(p0[1], p1[1]), 0, 1.2)
    elif door == "dark":
        M.face("dark", [G(*wall_pos(s, d["a0"], -RL, 0)), G(*wall_pos(s, d["a1"], -RL, 0)), G(*wall_pos(s, d["a1"], -RL, d["top"])), G(*wall_pos(s, d["a0"], -RL, d["top"]))][::-1], [(0, 0), (16, 0), (16, 16), (0, 16)])
        M.cylinder("post", G(*wall_pos(s, d["a0"] - 3, 1.0, d["top"] + 1.5)), G(*wall_pos(s, d["a1"] + 3, 1.0, d["top"] + 1.5)), 2.2, n=nseg, cap="endgrain", density=den)
        M.cylinder("post", G(*wall_pos(s, d["a0"] - 1, 0.5, 0.8)), G(*wall_pos(s, d["a1"] + 1, 0.5, 0.8)), 1.0, n=6, density=den)
    # round window: ring + dark hole
    w = WINDOW; c0 = G(*wall_pos(w["side"], w["a"], 0.8, w["z"])); e1 = G(*wall_pos(w["side"], w["a"] + 1, 0.8, w["z"])); e2 = G(*wall_pos(w["side"], w["a"], 0.8, w["z"] + 1))
    M.torus("post", c0, tuple(e1[i] - c0[i] for i in range(3)), tuple(e2[i] - c0[i] for i in range(3)), w["R"], w["r"], n=max(24, nseg * 2), m=8)
    pts = [G(*wall_pos(w["side"], w["a"] + w["hole"] * math.cos(2 * math.pi * i / 16), 0.9, w["z"] + w["hole"] * math.sin(2 * math.pi * i / 16))) for i in range(16)]
    M.face("hole", pts[::-1], [(8 + 8 * math.cos(2 * math.pi * i / 16), 8 + 8 * math.sin(2 * math.pi * i / 16)) for i in range(16)][::-1])
    # sign above the door (a flat board carrying the skull)
    if sign_uv:
        g = SIGN; q = [wall_pos(g["side"], g["a1"], 1.5, g["z0"]), wall_pos(g["side"], g["a0"], 1.5, g["z0"]), wall_pos(g["side"], g["a0"], 1.5, g["z1"]), wall_pos(g["side"], g["a1"], 1.5, g["z1"])]
        M.face("sign", [G(*p) for p in q], [sign_uv(*p) for p in q])
    # roof: eave roll + bulging hip roof up to the top (with hx > HX the slope runs on down past the picture's eave)
    off = hx - HX; LIP = lip; rings = []
    def rzz(t): return rz(t - off) if t >= off else ZE - (off - t) * 0.62
    ze = rzz(LIP)
    for k in range(7):
        phi = math.radians(-90 + 180 * k / 6); pts = contour(LIP * (1 - math.cos(phi)), hx0=hx); jit = math.cos(phi) * roof_jitter
        pts = [(x + (rnd.random() - 0.5) * jit, y + (rnd.random() - 0.5) * jit) for x, y in pts]
        rings.append((pts, ze - LIP + LIP * math.sin(phi)))
    if course > 0:                                                             # thatch courses: z = slope + step * (1 - position in the course), a butt edge at every course start
        tmax = hx - 0.8; c0 = LIP
        while c0 < tmax - 0.5:
            c1 = min(c0 + course, tmax); fade = 1 - c0 / hx                     # the steps get smaller towards the top
            for k in range(7):
                t = c0 + (c1 - c0) * k / 6; pts = contour(t, hx0=hx); jit = 1.1 if k == 0 else 0.35          # ragged butt edge, rougher straw
                pts = [(x + (rnd.random() - 0.5) * jit + 0.5 * jit * math.sin(0.7 * (x + y) + c0), y + (rnd.random() - 0.5) * jit) for x, y in pts]
                if k == 6: pts = contour(t, hx0=hx)                              # the next course's butt edge starts on this exact ring (no gaps)
                rings.append((pts, rzz(t) + step * fade * (1 - k / 6)))
            c0 = c1
    else:
        for k in range(1, 17):
            t = LIP + (hx - 0.8 - LIP) * k / 16; rings.append((contour(t, hx0=hx), rzz(t)))
    tex = lambda x, y: ((x - (CX - hx)) * den, ((CY + hx) - y) * den)
    for (A, za), (B, zb) in zip(rings, rings[1:]):
        n = len(A)
        for i in range(n):
            j = (i + 1) % n
            M.face("thatch", [G(A[i][0], A[i][1], za), G(A[j][0], A[j][1], za), G(B[j][0], B[j][1], zb), G(B[i][0], B[i][1], zb)],
                   [tex(*A[i]), tex(*A[j]), tex(*B[j]), tex(*B[i])])
    under, zu = rings[0]; M.face("under", [G(x, y, zu) for x, y in under], [(x * den, y * den) for x, y in under])
    top, zt = rings[-1]; M.face("thatch", [G(x, y, zt) for x, y in top], [tex(x, y) for x, y in top])
    if ridge_knot:                                                             # straw bundle at the top: a squat rounded cap, tied with a band
        for k in range(10):
            a0 = 2 * math.pi * k / 10; a1 = 2 * math.pi * (k + 1) / 10
            for j in range(6):
                p = lambda a, jj: (CX + 5.5 * math.cos(a) * math.cos(math.pi / 2 * jj / 6), CY + 5.5 * math.sin(a) * math.cos(math.pi / 2 * jj / 6), ZT - 2.5 + 4.5 * math.sin(math.pi / 2 * jj / 6))
                q = [p(a0, j), p(a1, j), p(a1, j + 1), p(a0, j + 1)]
                M.face("thatch", [G(*v) for v in q], [tex(v[0], v[1]) for v in q])
        M.torus("post", G(CX, CY, ZT - 1.2), (1, 0, 0), (0, 1, 0), 5.3, 0.6, n=24, m=6)
    # ridge: two crossed pairs of short sticks at the top
    for ax in (0, 1):
        for sgn in (-1, 1):
            dw, dz = 6.5, 5.5
            if ax == 0: p0, p1 = (CX - dw * sgn, CY + 1.4 * sgn, ZT - 3), (CX + dw * sgn, CY + 1.4 * sgn, ZT - 3 + 2 * dz)
            else: p0, p1 = (CX + 1.4 * sgn, CY - dw * sgn, ZT - 3), (CX + 1.4 * sgn, CY + dw * sgn, ZT - 3 + 2 * dz)
            M.cylinder("post", G(*p0), G(*p1), 1.6, n=max(8, nseg - 2), cap="endgrain", density=den)

# ---- voxel occupancy (variant B) ------------------------------------------------------------------------------------------------------------------
MAT = dict(empty=0, core=1, log=2, post=3, roof=4, stick=5, ring=6, hole=7, door=8, sign=9)
def voxels(vs=1.0):
    """occupancy grid, voxel edge vs units (1 = one game pixel); returns (mat [x, y, z] uint8, side of the log voxels [x, y, z] uint8
    (1 S, 2 N, 3 E, 4 W), origin (x, y, z) of voxel 0, 0, 0)."""
    ox, oy, oz = 278, 422, 0; nx, ny, nz = int(102 / vs), int(102 / vs), int(92 / vs)
    xs = (ox + vs * (0.5 + np.arange(nx))).astype(np.float32); ys = (oy + vs * (0.5 + np.arange(ny))).astype(np.float32); zs = (oz + vs * (0.5 + np.arange(nz))).astype(np.float32)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij"); V = np.zeros((nx, ny, nz), np.uint8); LS = np.zeros((nx, ny, nz), np.uint8)
    def seg_dist(p0, p1):
        p0 = np.array(p0); d = np.array(p1) - p0; L2 = d @ d
        t = np.clip(((X - p0[0]) * d[0] + (Y - p0[1]) * d[1] + (Z - p0[2]) * d[2]) / L2, 0, 1)
        return np.sqrt((X - p0[0] - t * d[0]) ** 2 + (Y - p0[1] - t * d[1]) ** 2 + (Z - p0[2] - t * d[2]) ** 2)
    # roof: solid from z 46 up to the bulging surface
    t = np.minimum.reduce([X - (CX - HX), (CX + HX) - X, Y - (CY - HX), (CY + HX) - Y])
    zt = ZE + (ZT - ZE) * (1 - (1 - np.clip(t, 0, HX) / HX) ** 1.25)
    jag = ((np.floor(X * 0.7) * 7 + np.floor(Y * 0.7) * 13) % 5 == 0)                       # a few straw tips hang lower at the edge
    V[(t >= 0) & (Z < zt) & (Z > ZE - 4 - jag * (t < 2) * 1.5)] = MAT["roof"]
    V[(X > X0 + RL) & (X < X1 - RL) & (Y > Y0 + RL) & (Y < Y1 - RL) & (Z < ZE)] = MAT["core"]
    # logs (front surface at the wall plane)
    for zc in LOG_Z:
        r2 = (RL - 0.3) ** 2
        for side in "NSEW":
            if side in "NS":
                yc = Y1 - RL if side == "S" else Y0 + RL; m = ((Y - yc) ** 2 + (Z - zc) ** 2 < r2) & (X > X0 - EXT) & (X < X1 + EXT)
            else:
                xc = X1 - RL if side == "E" else X0 + RL; m = ((X - xc) ** 2 + (Z - zc) ** 2 < r2) & (Y > Y0 - EXT) & (Y < Y1 + EXT)
            V[m & (Z < ZE - 1)] = MAT["log"]; LS[m & (Z < ZE - 1)] = "SNEW".index(side) + 1
    # door (carved, dark back)
    d = DOOR; dm = (X > X1 - 2 * RL - 1) & (Y > d["a0"]) & (Y < d["a1"]) & (Z < d["top"])
    V[dm] = 0; V[dm & (X < X1 - 2 * RL)] = MAT["door"]
    # posts
    for side, alist in POSTS.items():
        for a in alist:
            cx, cy, _ = wall_pos(side, a, POST_R - 0.6, 0)
            rr = (X - cx) ** 2 + (Y - cy) ** 2
            V[(rr < POST_R ** 2) & (Z < POST_TOP)] = MAT["post"]; V[(rr < (POST_R * 0.7) ** 2) & (Z < POST_TOP + 1.6)] = MAT["post"]
    # lintel
    V[seg_dist(wall_pos("E", d["a0"] - 3, 1.0, d["top"] + 1.5), wall_pos("E", d["a1"] + 3, 1.0, d["top"] + 1.5)) < 2.2] = MAT["post"]
    # window: carve a hole, dark back, ring
    w = WINDOW; wy = Y1 + 0.8; dd = np.sqrt((X - w["a"]) ** 2 + (Z - w["z"]) ** 2)
    hole = (dd < w["hole"]) & (Y > Y1 - 2 * RL)
    V[hole & (V == MAT["log"])] = 0; V[(dd < w["hole"] + 0.5) & (Y > Y1 - 2 * RL - 1) & (Y < Y1 - 2 * RL)] = MAT["hole"]
    V[((dd - w["R"]) ** 2 + (Y - wy) ** 2) < w["r"] ** 2] = MAT["ring"]
    # sign board (only the voxels that show the skull in the picture survive, see vb recipe)
    g = SIGN; V[(X > X1 + 0.5) & (X < X1 + 2.5) & (Y > g["a0"]) & (Y < g["a1"]) & (Z > g["z0"]) & (Z < g["z1"])] = MAT["sign"]
    # ridge sticks
    for ax in (0, 1):
        for sgn in (-1, 1):
            dw, dz = 6.5, 5.5
            if ax == 0: p0, p1 = (CX - dw * sgn, CY + 1.4 * sgn, ZT - 3), (CX + dw * sgn, CY + 1.4 * sgn, ZT - 3 + 2 * dz)
            else: p0, p1 = (CX + 1.4 * sgn, CY - dw * sgn, ZT - 3), (CX + 1.4 * sgn, CY + dw * sgn, ZT - 3 + 2 * dz)
            V[seg_dist(p0, p1) < 1.7] = MAT["stick"]
    return V, LS, (ox, oy, oz)

# ---- shared preview set ---------------------------------------------------------------------------------------------------------------------------
VIEWS = [("game", None), ("turn_l", -35), ("turn_r", 35), ("back", 150), ("side", 200)]
FIG_PX = 1 / math.sqrt(2)      # world units per sprite pixel on a camera-facing card: the game projection shows 1 world unit across the screen as sqrt(2) pixels
FIG_FWD = 7.5 * math.sqrt(2)  # the sprite's bottom row = the FRONT corner of the 15 x 15 box: the card stands this far towards the camera from the box centre
def add_figure(png_path, game_pos, light=0.55):
    """a pixel figure (rom_sprite.py cut-out) as a camera-facing billboard; game_pos = centre of its collision box on the ground.
    Size (measured 2026-10-25 on the Massan replay, entity +12 Z / +54 top / +18..+1E box): Nigel is 31 units high with a 15 x 15 box; his 47 px sprite
    = 31 + the depth of the box drawn in the 2:1 view.  So one sprite pixel = FIG_PX units on the card (head at ~33) and the card's bottom row stands at
    the box's front corner (face_camera moves it FIG_FWD towards the camera): in the game view the figure covers exactly the pixels of the original.
    Lit a little by the scene (HD-2D style), casts a shadow.  render_set(figures=...) turns it to every camera."""
    import bpy, bmesh
    img = bpy.data.images.load(png_path); img.colorspace_settings.name = "sRGB"; w, h = img.size
    k = 1.0
    txt = os.path.splitext(png_path)[0] + ".txt"
    if os.path.exists(txt): k = float(open(txt).read().split()[2])
    W, Hh = w / k * FIG_PX, h / k * FIG_PX
    me = bpy.data.meshes.new("figure"); b = bmesh.new(); uvl = b.loops.layers.uv.new("UV")
    f = b.faces.new([b.verts.new(p) for p in ((-W / 2, 0, 0), (W / 2, 0, 0), (W / 2, 0, Hh), (-W / 2, 0, Hh))])
    for l, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): l[uvl].uv = uv
    b.to_mesh(me); b.free()
    m = bpy.data.materials.new("figure"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    o = nt.nodes.new("ShaderNodeOutputMaterial"); t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; t.interpolation = "Closest"
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.inputs["Roughness"].default_value = 0.9
    L(t.outputs["Color"], bs.inputs["Base Color"]); L(t.outputs["Alpha"], bs.inputs["Alpha"])
    if "Emission Color" in bs.inputs: L(t.outputs["Color"], bs.inputs["Emission Color"]); bs.inputs["Emission Strength"].default_value = light
    L(bs.outputs["BSDF"], o.inputs["Surface"])
    if hasattr(m, "surface_render_method"): m.surface_render_method = "DITHERED"
    me.materials.append(m); ob = bpy.data.objects.new("figure", me); bpy.context.scene.collection.objects.link(ob)
    ob.location = G(*game_pos); ob["base"] = G(*game_pos); return ob

def face_camera(ob, co, upright=True, game=False):
    import bpy, mathutils
    bpy.context.view_layer.update()                                          # the camera was just moved: refresh its matrix first
    d = co.matrix_world.to_quaternion() @ mathutils.Vector((0, 0, 1))          # towards the camera (orthographic: the view direction)
    if co.data.type == "PERSP": d = co.location - ob.location
    if upright: d.z = 0
    ob.rotation_euler = d.normalized().to_track_quat("-Y", "Z").to_euler()
    if "base" in ob:
        h = mathutils.Vector((d.x, d.y, 0)).normalized(); ob.location = mathutils.Vector(ob["base"]) + h * FIG_FWD
        if not game and "base_q" in ob: ob.location = mathutils.Vector(ob["base_q"])   # pixel plants (room_c.py): in the middle of their cell when turned

def sort_cards(cards, solids, co, margin=1.0):
    """2D sorting for pixel cards (user 2026-10-27: a bush in front of a house was cut by the house wall in a turned view; it must lie WHOLLY in front
    of the house in that view and wholly behind it where the house is in front).  A camera-facing card has one depth (its foot); tall walls just behind
    the foot are nearer than that, so the depth test cuts the card.  The camera is orthographic: sliding a card along the view ray changes neither its
    screen place nor its size, so every card is slid towards the camera until it is in front of every solid (house) that stands BEHIND its foot
    (footprint rule as in 2D games) and overlaps it on screen, but stays behind solids in FRONT of its foot; cards keep their order among themselves.
    The shadow stays where it was (a hidden twin at the old place casts it).  Call after face_camera for every view."""
    import bpy, mathutils
    import numpy as np
    bpy.context.view_layer.update()
    for ob in [o for o in bpy.data.objects if o.get("shadow_twin")]: bpy.data.objects.remove(ob, do_unlink=True)
    M = co.matrix_world; cam = M.translation; d = (M.to_quaternion() @ mathutils.Vector((0, 0, 1))).normalized()
    ax = (M.to_quaternion() @ mathutils.Vector((1, 0, 0))).normalized(); ay = (M.to_quaternion() @ mathutils.Vector((0, 1, 0))).normalized()
    A = np.array([ax[:], ay[:], d[:]])
    def cs(P): P = np.asarray(P) - np.array(cam[:]); return P @ A.T                # columns: screen x, screen y, -depth (bigger = nearer)
    sol = []
    for ob in solids:
        mw = np.array(ob.matrix_world)
        V = np.array([v.co[:] for v in ob.data.vertices]); V = V @ mw[:3, :3].T + mw[:3, 3]
        sol.append((V[:, 0].min(), V[:, 0].max(), V[:, 1].min(), V[:, 1].max(), cs(V)))
    vx, vy = -d.x, -d.y                                                          # horizontal view direction (into the scene)
    def side(F, s):                                                              # +1 foot in front of the solid, -1 behind, 0 unclear (inside / beside)
        x0, x1, y0, y1 = s[:4]
        fx = (F.x <= x0 + margin) if vx > 1e-6 else (F.x >= x1 - margin) if vx < -1e-6 else False
        fy = (F.y <= y0 + margin) if vy > 1e-6 else (F.y >= y1 - margin) if vy < -1e-6 else False
        bx = (F.x >= x1 - margin) if vx > 1e-6 else (F.x <= x0 + margin) if vx < -1e-6 else False
        by = (F.y >= y1 - margin) if vy > 1e-6 else (F.y <= y0 + margin) if vy < -1e-6 else False
        if (fx or fy) and not (bx or by): return 1
        if (bx or by) and not (fx or fy): return -1
        return 0
    info = []
    for c in cards:
        mw = np.array(c.matrix_world); V = np.array([v.co[:] for v in c.data.vertices]) @ mw[:3, :3].T + mw[:3, 3]; S = cs(V)
        info.append(dict(ob=c, F=c.location.copy(), r=(S[:, 0].min(), S[:, 0].max(), S[:, 1].min(), S[:, 1].max()), z=float(S[:, 2].mean())))
    def inside(S, r): return (S[:, 0] >= r[0]) & (S[:, 0] <= r[1]) & (S[:, 1] >= r[2]) & (S[:, 1] <= r[3])
    done = []; moved = 0
    for c in sorted(info, key=lambda c: c["z"]):                                 # far cards first
        need, cap = c["z"], 1e9
        for s in sol:
            k = side(c["F"], s)
            if k == 0: continue
            S = s[4][inside(s[4], c["r"])]
            if not len(S): continue
            if k > 0: need = max(need, float(S[:, 2].max()) + 0.5)               # in front of every point of the house it overlaps
            else: cap = min(cap, float(S[:, 2].min()) - 0.5)                     # behind every point of a house in front of it
        for e in done:                                                           # keep the order among overlapping cards
            if e["z0"] < c["z"] and not (e["r"][1] < c["r"][0] or c["r"][1] < e["r"][0] or e["r"][3] < c["r"][2] or c["r"][3] < e["r"][2]):
                need = max(need, e["z"] + 0.01)
        if need > cap: print("sort_cards: conflict for", c["ob"].name, round(need - cap, 1)); need = max(c["z"], cap)
        c["z0"] = c["z"]
        if need > c["z"] + 1e-3:
            tw = c["ob"].copy(); tw["shadow_twin"] = 1; bpy.context.scene.collection.objects.link(tw); tw.visible_camera = False
            c["ob"].visible_shadow = False; c["ob"].location = c["ob"].location + d * (need - c["z"]); c["z"] = need; moved += 1
        else: c["ob"].visible_shadow = True
        done.append(c)
    print("sort_cards: %d of %d cards moved towards the camera" % (moved, len(cards)), flush=True)

def render_set(out, px=2.0, dof=False, squash_game=True, outlines=True, modern=False, figures=(), quarter=False, tz=38, fh=190, sun_spec=1.0):
    """game view (the original's projection, heights squashed like the game) + turned views and a low perspective 'hero' shot (true heights).
    Needs the scene filled; uses blx.game_view (sets light / world).  Files: out/<view>.png"""
    import bpy, mathutils, blx
    T = G(CX, CY, tz); size = (int(208 * px), int(fh * px))
    sc, co = blx.game_view(os.path.join(out, "game.png"), px_per_unit=px, size=size, target=T, squash=squash_game)
    if not outlines: sc.render.use_freestyle = False
    for f in figures: f.scale = (1, 1, 1); face_camera(f, co, upright=False, game=True)   # game view: the figure faces the screen like the original sprite
    if modern:                                                                 # the style C light (lib/cmat.py); modern="std" keeps the game's colours
        import cmat; cmat.modern_look(sc, agx=(modern != "std")); bpy.data.objects["sun"].data.specular_factor = sun_spec
        bpy.ops.render.render(write_still=True)
    if quarter:                                                                # the remake camera (user 2026-10-25): game projection, turned in 90 degree steps only
        zs = math.sqrt(2.0 / 3.0) if squash_game else 1.0
        for q in (1, 2, 3):
            blx.orbit(co, (T[0], T[1], T[2] * zs), 90 * q, 30)
            for f in figures: face_camera(f, co, upright=False)
            sc.render.filepath = os.path.join(out, "q%d.png" % q); bpy.ops.render.render(write_still=True)
    if squash_game:
        for ob in sc.objects:
            if ob.type == "MESH": ob.scale.z /= math.sqrt(2.0 / 3.0)
    for f in figures: f.scale = (1, 1, 1)
    Tt = (T[0], T[1], 34)
    for name, yaw in ([] if quarter else VIEWS[1:]):
        blx.orbit(co, Tt, yaw, 28)
        for f in figures: face_camera(f, co)
        sc.render.filepath = os.path.join(out, name + ".png"); bpy.ops.render.render(write_still=True)
    cd = co.data; cd.type = "PERSP"; cd.lens = 35; cd.clip_start = 1
    a = math.radians(-45 + 25); el = math.radians(9); dist = 175
    co.location = mathutils.Vector(Tt) + mathutils.Vector((math.cos(el) * math.cos(a), math.cos(el) * math.sin(a), math.sin(el))) * dist
    co.location.z = max(co.location.z, 14)
    co.rotation_euler = (mathutils.Vector((Tt[0], Tt[1], 30)) - co.location).to_track_quat("-Z", "Y").to_euler()
    if dof:
        cd.dof.use_dof = True; cd.dof.focus_distance = (mathutils.Vector(Tt) - co.location).length * 0.9; cd.dof.aperture_fstop = 0.04
    for f in figures: face_camera(f, co)
    sc.render.filepath = os.path.join(out, "hero.png"); bpy.ops.render.render(write_still=True)
