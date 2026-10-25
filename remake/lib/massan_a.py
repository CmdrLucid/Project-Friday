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
def contour(t, rc0=6.0, K=(24, 5)):
    hx = HX - t; rc = max(rc0 - t, 0.0); pts = []
    corners = [(hx - rc, hx - rc, 0), (-(hx - rc), hx - rc, 90), (-(hx - rc), -(hx - rc), 180), (hx - rc, -(hx - rc), 270)]
    for ci, (cx, cy, a0) in enumerate(corners):
        for j in range(K[1]):
            a = math.radians(a0 + 90 * j / (K[1] - 1)); pts.append((CX + cx + rc * math.cos(a), CY + cy + rc * math.sin(a)))
        nx, ny, _ = corners[(ci + 1) % 4]; ex, ey = pts[-1]; a = math.radians(a0 + 90)
        tx, ty = CX + nx + rc * math.cos(a), CY + ny + rc * math.sin(a)
        for j in range(1, K[0]): pts.append((ex + (tx - ex) * j / K[0], ey + (ty - ey) * j / K[0]))
    return pts

def build(M, nseg=10, den=2.0, sign_uv=None, roof_jitter=1.4, smooth_roof=False):
    """adds the house to a blx.Mesh with materials bark, post, endgrain, dark, hole, thatch, under (+ 'sign' if sign_uv is given:
    function (x, y, z) -> texel uv of the sign image)."""
    import random
    rnd = random.Random(5)
    # dark core: the seams between the logs show black like the original
    M.box("dark", X0 + RL, X1 - RL, -(Y1 - RL), -(Y0 + RL), 0, ZE - 1)      # behind the log centres
    for side in "NSEW":
        ns = side in "NS"; L0, L1 = (X0, X1) if ns else (Y0, Y1)
        for i, zc in enumerate(LOG_Z):
            r = RL * (0.92 if rnd.random() > 0.5 else 0.88)
            segs = [(L0 - EXT, L1 + EXT)]
            if side == DOOR["side"] and zc - r < DOOR["top"]: segs = [(L0 - EXT, DOOR["a0"]), (DOOR["a1"], L1 + EXT)]
            for a, b in segs:
                pa = G(*wall_pos(side, a, -RL, zc)); pb = G(*wall_pos(side, b, -RL, zc))
                M.cylinder("bark", pa, pb, r, n=nseg, cap="endgrain", density=den)
        for i, a in enumerate(POSTS[side]):
            top = POST_TOP + rnd.random() * 1.2
            M.cylinder("post", G(*wall_pos(side, a, POST_R - 0.6, -1)), G(*wall_pos(side, a, POST_R - 0.6, top)), POST_R, n=nseg, cap="endgrain", density=den)
            M.cylinder("post", G(*wall_pos(side, a, POST_R - 0.6, top)), G(*wall_pos(side, a, POST_R - 0.6, top + 1.6)), POST_R * 0.7, n=nseg, cap="endgrain", density=den)
    # door: dark opening, lintel, threshold
    d = DOOR; s = d["side"]
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
    # roof: eave roll + bulging hip roof up to the top
    LIP = 3.5; rings = []
    for k in range(7):
        phi = math.radians(-90 + 180 * k / 6); pts = contour(LIP * (1 - math.cos(phi))); jit = math.cos(phi) * roof_jitter
        pts = [(x + (rnd.random() - 0.5) * jit, y + (rnd.random() - 0.5) * jit) for x, y in pts]
        rings.append((pts, ZE - LIP + LIP * math.sin(phi)))
    for k in range(1, 15):
        t = LIP + (HX - 0.8 - LIP) * k / 14; rings.append((contour(t), rz(t)))
    tex = lambda x, y: ((x - (CX - HX)) * den, ((CY + HX) - y) * den)
    for (A, za), (B, zb) in zip(rings, rings[1:]):
        n = len(A)
        for i in range(n):
            j = (i + 1) % n
            M.face("thatch", [G(A[i][0], A[i][1], za), G(A[j][0], A[j][1], za), G(B[j][0], B[j][1], zb), G(B[i][0], B[i][1], zb)],
                   [tex(*A[i]), tex(*A[j]), tex(*B[j]), tex(*B[i])])
    under, zu = rings[0]; M.face("under", [G(x, y, zu) for x, y in under], [(x * den, y * den) for x, y in under])
    top, zt = rings[-1]; M.face("thatch", [G(x, y, zt) for x, y in top], [tex(x, y) for x, y in top])
    # ridge: two crossed pairs of short sticks at the top
    for ax in (0, 1):
        for sgn in (-1, 1):
            dw, dz = 6.5, 5.5
            if ax == 0: p0, p1 = (CX - dw * sgn, CY + 1.4 * sgn, ZT - 3), (CX + dw * sgn, CY + 1.4 * sgn, ZT - 3 + 2 * dz)
            else: p0, p1 = (CX + 1.4 * sgn, CY - dw * sgn, ZT - 3), (CX + 1.4 * sgn, CY + dw * sgn, ZT - 3 + 2 * dz)
            M.cylinder("post", G(*p0), G(*p1), 1.6, n=max(8, nseg - 2), cap="endgrain", density=den)

# ---- voxel occupancy (variant B) ------------------------------------------------------------------------------------------------------------------
MAT = dict(empty=0, core=1, log=2, post=3, roof=4, stick=5, ring=6, hole=7, door=8, sign=9)
def voxels():
    """occupancy grid, 1 voxel = 1 unit; returns (mat array [x, y, z] uint8, origin (x, y, z) of voxel 0, 0, 0)."""
    ox, oy, oz = 278, 422, 0; nx, ny, nz = 102, 102, 92
    xs = ox + 0.5 + np.arange(nx); ys = oy + 0.5 + np.arange(ny); zs = oz + 0.5 + np.arange(nz)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij"); V = np.zeros((nx, ny, nz), np.uint8)
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
            V[m & (Z < ZE - 1)] = MAT["log"]
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
    return V, (ox, oy, oz)

# ---- shared preview set ---------------------------------------------------------------------------------------------------------------------------
VIEWS = [("game", None), ("turn_l", -35), ("turn_r", 35), ("back", 150), ("side", 200)]
def render_set(out, px=2.0, dof=False, squash_game=True, outlines=True, modern=False):
    """game view (the original's projection, heights squashed like the game) + turned views and a low perspective 'hero' shot (true heights).
    Needs the scene filled; uses blx.game_view (sets light / world).  Files: out/<view>.png"""
    import bpy, mathutils, blx
    T = G(CX, CY, 38); size = (int(208 * px), int(190 * px))
    sc, co = blx.game_view(os.path.join(out, "game.png"), px_per_unit=px, size=size, target=T, squash=squash_game)
    if not outlines: sc.render.use_freestyle = False
    if modern:                                                                 # warm low sun, filmic colours, soft shadows (variant C)
        sc.view_settings.view_transform = "AgX"
        try: sc.view_settings.look = "AgX - Medium High Contrast"
        except Exception: pass
        sun = bpy.data.objects["sun"]; sun.data.energy = 4.5; sun.data.color = (1.0, 0.86, 0.68); sun.data.angle = math.radians(6)
        sun.rotation_euler = (-mathutils.Vector((-0.55, -0.6, 0.55))).to_track_quat("-Z", "Y").to_euler()
        sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.7, 1.0, 1); sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
        if hasattr(sc.eevee, "use_raytracing"): sc.eevee.use_raytracing = True
        bpy.ops.render.render(write_still=True)
    bpy.ops.render.render(write_still=True)
    if squash_game:
        for ob in sc.objects:
            if ob.type == "MESH": ob.scale.z /= math.sqrt(2.0 / 3.0)
    Tt = (T[0], T[1], 34)
    for name, yaw in VIEWS[1:]:
        blx.orbit(co, Tt, yaw, 28); sc.render.filepath = os.path.join(out, name + ".png"); bpy.ops.render.render(write_still=True)
    cd = co.data; cd.type = "PERSP"; cd.lens = 35; cd.clip_start = 1
    a = math.radians(-45 + 25); el = math.radians(9); dist = 175
    co.location = mathutils.Vector(Tt) + mathutils.Vector((math.cos(el) * math.cos(a), math.cos(el) * math.sin(a), math.sin(el))) * dist
    co.location.z = max(co.location.z, 14)
    co.rotation_euler = (mathutils.Vector((Tt[0], Tt[1], 30)) - co.location).to_track_quat("-Z", "Y").to_euler()
    if dof:
        cd.dof.use_dof = True; cd.dof.focus_distance = (mathutils.Vector(Tt) - co.location).length * 0.9; cd.dof.aperture_fstop = 0.04
    sc.render.filepath = os.path.join(out, "hero.png"); bpy.ops.render.render(write_still=True)
