"""Asset 1 (second try, 2026-10-24): MASSAN HOUSE, built to look like the original as closely as possible at twice the texel resolution.
Run: python3 remake/tools/build_asset.py massan_house   (Blender, INDEX 'remake toolchain').  Output: ~/.landstalker_remake/assets/massan_house/
House = env R_HOUSE (default A).  Sizes from the room 592 height map (FORMATS 'Height map = a real height field'): walls 48 units high,
A = the lone house west of the statue (5 x 5 cells, door east, round window south), B = the house in the south (5 x 7 cells, door south, window east, roof vents).
What the original shows (looked at in tools/romrender.py ROM 592, 4x zoom) and how it is built here:
  walls  = horizontal ROUND LOGS (green moss, brown / orange top edge, black seams), log-cabin corners: the logs of the two walls alternate by half a log and
           stick out past the corner with brown end grain;  posts = round brown posts in front of the wall (near the corners, every ~2 cells, beside doors);
  roof   = thick, bulging HIP ROOF of thatch (yellow, white tips, ochre shadow, a cool grey-blue in the deep shadow), the straw runs down every roof face
           in staggered bundles ('fish scales'), the eave is a rounded roll;  ridge = crossed short logs;  windows = round wooden rings with a dark hole;
  doors  = dark openings with a lintel log.
Units: game pixels, game coordinates g(x east, y south, z up) -> Blender (x, -y, z) (blx.game_view).  Colours: the game's own palette ramps plus in-between tones."""
import bpy, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx
out = os.environ.get("R_OUT", "/tmp/massan_house"); os.makedirs(out, exist_ok=True)
HOUSE = os.environ.get("R_HOUSE", "A")
bpy.ops.wm.read_factory_settings(use_empty=True)
blx.PIXEL = os.environ.get("R_SMOOTH", "") != "1"                # pixel-art look (default); R_SMOOTH=1 = the old smooth render
DEN = 2.0                                                   # texels per game pixel ('etwas bessere Aufloesung')
def h(*k):                                                  # deterministic hash noise 0..1
    v = 2166136261
    for x in k: v = ((v ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    v ^= v >> 13; v = (v * 1274126177) & 0xFFFFFFFF; return ((v >> 8) & 0xFFFF) / 65536.0
def G(x, y, z): return (x, -y, z)

# ---- houses (game units; x0..x1 / y0..y1 = wall planes) --------------------------------------------------------------------------------------
HOUSES = {
    "A": dict(w=64, d=64, door=("E", 0.5), windows=[("S", 0.3, 30, "round")], vents=[]),
    "B": dict(w=64, d=96, door=("S", 0.75), windows=[("E", 0.55, 30, "round"), ("S", 0.22, 30, "shutter")], vents=[(0.32, 0.30), (0.62, 0.58)]),
}
# w / d = wall planes; the height map cells (5 x 5 = 80 x 80) end where the log ends end (EXT on each side)
P = HOUSES[HOUSE]; W, D = P["w"], P["d"]; x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2
ZW = 48.0                                                   # wall height
NL = 7; RL = ZW / NL / 2                                    # logs per wall, log radius (3.43)
EXT = 3.5                                                   # logs stick out past the corner
POST_R = 1.8; POST_OFF = RL + POST_R - 1.0                  # posts stand in front of the wall plane
ZE = 50.0; LIP = 4.0; OV = 7.0                             # top of the eave roll (start of the slope), roll radius, overhang past the wall plane
RISE = 24.0                                                 # ridge height above ZE (measured: apex ~75, eave tip ~47 px above the ground in the picture)

# ---- pixel textures (generated; game palette + in-between tones) ---------------------------------------------------------------------------
GREEN = [(0, 32, 16), (0, 72, 36), (30, 96, 18), (60, 126, 0), (84, 144, 18)]
BROWN = [(40, 32, 14), (72, 72, 36), (110, 86, 30), (144, 108, 36), (182, 126, 54), (216, 144, 72), (232, 176, 110)]
def bark(x, y):                         # 96 x 44: x along the log, y = one turn (y 0 = top of the log, 11 = front, 22 = bottom, 33 = back)
    """like the original: fine mottled MOSS GREEN, a thin orange edge on top, dark green towards the seam, rare light specks."""
    a = (y / 44.0) * 2 * math.pi; up = math.cos(a)
    n = h(x, y, 1); m = h(x // 2, y // 2, 2); g = h(x // 4 + y * 13, 3)
    if up > 0.93: return BROWN[5] if n > 0.25 else BROWN[6] if n > 0.1 else BROWN[4]        # thin lit edge
    if up > 0.80: return BROWN[4] if n > 0.55 else GREEN[3] if n > 0.25 else BROWN[5]
    if up < -0.55: return GREEN[1] if n > 0.3 else GREEN[0]                                  # towards the black seam
    if n > 0.975: return BROWN[6] if up > 0 else BROWN[5]                                    # rare light specks
    if n > 0.94 and g > 0.5: return BROWN[4]
    k = (m * 0.6 + n * 0.4) + up * 0.25
    return GREEN[4] if k > 0.72 else GREEN[3] if k > 0.42 else GREEN[2] if k > 0.2 else GREEN[1]
def post(x, y):                         # 96 x 36: x along the post, y = one turn: light orange wood, a white stripe on the lit side, darker back
    n = h(x // 2, y, 5); a = y / 36.0 * 2 * math.pi; s = math.cos(a)
    if 4 <= y <= 6: return (232, 228, 210) if n > 0.2 else BROWN[6]                         # highlight stripe
    if s > -0.2: return BROWN[5] if n > 0.2 else BROWN[6]
    return BROWN[4] if n > 0.3 else BROWN[3]
def endgrain(x, y):                     # 16 x 16 round cut: rings
    r = math.hypot(x - 7.5, y - 7.5)
    if r > 7.2: return BROWN[1]
    if r > 6.0: return BROWN[3]
    return BROWN[5] if int(r) % 2 == 0 else BROWN[4]
def dark(x, y): return (0, 0, 0) if h(x, y, 8) > 0.15 else (0, 30, 14)
def hole(x, y): return (0, 20, 10) if h(x, y, 9) > 0.2 else (0, 40, 20)
def plank(x, y):
    col = x % 10; n = h(x // 10, y // 3, 10)
    return BROWN[1] if col == 0 else BROWN[5] if col in (1, 2) else BROWN[4] if n > 0.4 else BROWN[3]
THATCH = [(72, 56, 0), (108, 80, 0), (144, 108, 0), (180, 144, 0), (216, 180, 0), (232, 200, 40), (216, 216, 216), (240, 236, 210)]
COOL = (108, 144, 144)
HX = W / 2 + OV; HY = D / 2 + OV; RC = 6.0                  # roof outer half sizes, corner rounding
def roof_inset(x, y):
    """(inset t from the outer roof edge, coordinate along that edge, which face): hip roof = nearest edge wins."""
    dx, dy = HX - abs(x), HY - abs(y)
    if dx < dy: return dx, y + (1000 if x > 0 else 2000), "EW"
    return dy, x + (3000 if y > 0 else 4000), "NS"
def thatch_px(tx, ty):                  # texel of the roof texture (top planar, DEN texels per unit, origin at the roof's north west corner)
    x = tx / DEN - HX; y = ty / DEN - HY; t, a, f = roof_inset(x, y)
    COURSE = 6.0
    wob = 1.3 * math.sin(a * 1.1 + h(int(a // 9), 31) * 6) + 0.8 * math.sin(a * 2.7 + t * 0.3)          # wavy, irregular course lines
    tc = t + wob; c_i = math.floor(tc / COURSE); fr = tc / COURSE - c_i                                  # fr 0 = lower tip of the course
    bw = 3.5 + 3.0 * h(c_i, int(a // 6), 32)
    sa = math.floor(a * DEN / 1.0); strand = h(sa, c_i, math.floor(tc * DEN / 3), 11); n = h(tx, ty, 12); m = h(tx // 3, ty // 3, 33)   # strand: short strokes down the slope
    tip = fr < 0.18 + 0.25 * h(sa // 2, c_i, 34)
    if fr > 0.82: k = 3 if n > 0.45 else 2                                                      # shadow under the next course
    elif tip: k = 6 if strand > 0.5 else 4 if strand > 0.2 else 5                              # sunlit straw tips
    else: k = 6 if strand > 0.93 else 4 if strand > 0.25 else 3
    if n > 0.985: k = 6
    if m > 0.9 and k > 3: k -= 1
    if t < 1.0: k = min(k, 2) if n > 0.5 else 1                                                 # dark eave edge (shadowed underside of the roll)
    elif t < LIP + 5 and n < 0.55 * (1 - (t - 1) / (LIP + 4)) + 0.15: k = max(1, min(k, 3) - 1)  # the lower roof darkens towards the eave (ochre dither)
    c = THATCH[k]
    if k == 2 and t > 2 * LIP and h(tx // 2, ty // 2, 13) > 0.72: c = COOL                                      # the original's cool grey-blue in deep shadow
    return c
def thatch_under(x, y): return THATCH[1] if h(x // 2, y, 14) > 0.3 else THATCH[0]
def dirt(x, y):
    n = h(x // 2, y // 2, 15); m = h(x // 6, y // 6, 16)
    return BROWN[5] if n > 0.93 else BROWN[3] if n > 0.35 else BROWN[2] if m > 0.4 else (126, 96, 34)
RW, RH = int(2 * HX * DEN), int(2 * HY * DEN)
mats = [blx.material("bark", blx.px_image("bark", bark, 96, 44)), blx.material("post", blx.px_image("post", post, 96, 36)),
        blx.material("endgrain", blx.px_image("endgrain", endgrain, 16, 16)), blx.material("dark", blx.px_image("dark", dark, 16, 16)),
        blx.material("hole", blx.px_image("hole", hole, 16, 16)), blx.material("plank", blx.px_image("plank", plank, 40, 40)),
        blx.material("thatch", blx.px_image("thatch_" + HOUSE, thatch_px, RW, RH)), blx.material("under", blx.px_image("under", thatch_under, 32, 32))]
M = blx.Mesh("massan_house_" + HOUSE, mats); M.density = DEN

# ---- walls: dark core + log courses with alternating corners ---------------------------------------------------------------------------------
def opening(side):
    """door gap (along-wall interval, top z) on this side or None."""
    s, f = P["door"]
    if s != side: return None
    L = W if side in "NS" else D; c = -L / 2 + f * L
    return (c - 8.5, c + 8.5, 33.0)
M.box("dark", x0 + 1.5, x1 - 1.5, -(y1 - 1.5), -(y0 + 1.5), 0, ZW + 4)                         # core: the seams between the logs show black like the original
def wall_logs(side):
    ns = side in "NS"; L0, L1 = (x0, x1) if ns else (y0, y1); fixed = (y1 if side == "S" else y0) if ns else (x1 if side == "E" else x0)
    off = 0.0 if ns else RL                                                                  # the E / W logs sit half a log higher (log-cabin corner)
    gap = opening(side)
    for i in range(NL + (0 if ns else 0)):
        zc = RL + 2 * RL * i + off
        if zc > ZW + 1: continue
        r = RL * (0.82 if h(i, ord(side), 20) > 0.5 else 0.78)                       # gaps: the black core shows as the seams
        segs = [(L0 - EXT, L1 + EXT)]
        if gap and zc - r < gap[2]: segs = [(L0 - EXT, gap[0]), (gap[1], L1 + EXT)]
        for a, b in segs:
            pa = G(a, fixed, zc) if ns else G(fixed, a, zc); pb = G(b, fixed, zc) if ns else G(fixed, b, zc)
            M.cylinder("bark", pa, pb, r, n=10, cap="bark", density=DEN)
    if not ns and off:                                                                       # half log at the foot of the E / W walls
        pa, pb = G(fixed, L0 - EXT, RL * 0.45), G(fixed, L1 + EXT, RL * 0.45)
        if not gap: M.cylinder("bark", pa, pb, RL * 0.7, n=10, cap="endgrain", density=DEN)
        else:
            M.cylinder("bark", G(fixed, L0 - EXT, RL * 0.45), G(fixed, gap[0], RL * 0.45), RL * 0.7, n=10, cap="endgrain", density=DEN)
            M.cylinder("bark", G(fixed, gap[1], RL * 0.45), G(fixed, L1 + EXT, RL * 0.45), RL * 0.7, n=10, cap="endgrain", density=DEN)
for sd in "NSEW": wall_logs(sd)

# ---- posts, door, windows ----------------------------------------------------------------------------------------------------------------
def wall_point(side, along, out, z):
    if side == "S": return G(along, y1 + out, z)
    if side == "N": return G(along, y0 - out, z)
    if side == "E": return G(x1 + out, along, z)
    return G(x0 - out, along, z)
def posts(side):
    L = W if side in "NS" else D; xs = [-L / 2 + 6, L / 2 - 6]                                 # a pair at every corner (one on each wall)
    if L > 90: xs.append(0.0)
    gap = opening(side)
    if gap: xs = [x for x in xs if not (gap[0] - 4 < x < gap[1] + 4)] + [gap[0] - POST_R + 0.5, gap[1] + POST_R - 0.5]
    for i, a in enumerate(xs):
        top = ZE - LIP - 3.0 + h(i, ord(side), 21) * 1.5
        M.cylinder("post", wall_point(side, a, POST_OFF, 0), wall_point(side, a, POST_OFF, top), POST_R, n=10, cap="endgrain", density=DEN)
        M.cylinder("post", wall_point(side, a, POST_OFF, top), wall_point(side, a, POST_OFF, top + 1.6), POST_R * 0.7, n=10, cap="endgrain", density=DEN)
for sd in "NSEW": posts(sd)
gap = opening(P["door"][0])
if gap:
    s = P["door"][0]
    pa, pb = wall_point(s, gap[0] - 3, RL + 1.2, gap[2] + 1.8), wall_point(s, gap[1] + 3, RL + 1.2, gap[2] + 1.8)
    M.cylinder("post", pa, pb, 2.2, n=8, cap="endgrain", density=DEN)                        # lintel
    c = (gap[0] + gap[1]) / 2
    q = [wall_point(s, gap[0], 0.2, 0), wall_point(s, gap[1], 0.2, 0), wall_point(s, gap[1], 0.2, gap[2]), wall_point(s, gap[0], 0.2, gap[2])]
    M.face("dark", q, [(0, 0), (16, 0), (16, 16), (0, 16)])                                  # the dark doorway
    M.cylinder("plank", wall_point(s, gap[0] - 1, RL + 2.0, 0.8), wall_point(s, gap[1] + 1, RL + 2.0, 0.8), 1.0, n=6, density=DEN)   # threshold
for side, f, z, kind in P["windows"]:
    L = W if side in "NS" else D; a = -L / 2 + f * L
    if kind == "round":
        import mathutils
        rr = 8.0
        c0 = wall_point(side, a, RL + 0.8, z); e1 = wall_point(side, a + 1, RL + 0.8, z); e2 = wall_point(side, a, RL + 0.8, z + 1)
        M.torus("post", c0, tuple(e1[i] - c0[i] for i in range(3)), tuple(e2[i] - c0[i] for i in range(3)), rr, 2.2, n=24, m=8)
        pts = [wall_point(side, a + (rr - 1.0) * math.cos(2 * math.pi * i / 16), RL + 0.9, z + (rr - 1.0) * math.sin(2 * math.pi * i / 16)) for i in range(16)]
        if side in "SW": pts.reverse()
        M.face("hole", pts, [(8 + 8 * math.cos(2 * math.pi * i / 16), 8 + 8 * math.sin(2 * math.pi * i / 16)) for i in range(16)])
    else:                                                                                    # shutter: a small plank board leaning on the wall
        q = [wall_point(side, a - 7, RL + 1.0, z - 9), wall_point(side, a + 7, RL + 1.0, z - 9), wall_point(side, a + 9, RL + 3.0, z + 9), wall_point(side, a - 5, RL + 3.0, z + 9)]
        if side in "SW": q.reverse()
        M.face("plank", q, [(0, 0), (28, 0), (28, 36), (0, 36)])

# ---- roof: rings of the rounded outer rectangle, inset step by step up to the ridge -------------------------------------------------------
def contour(t, K=(28, 5)):
    """points of the outer rounded rectangle inset by t (fixed count): edges get K[0] points, corners K[1]; returns list of (x, y)."""
    hx, hy, rc = HX - t, HY - t, max(RC - t, 0.0)
    pts = []
    corners = [(hx - rc, hy - rc, 0), (-(hx - rc), hy - rc, 90), (-(hx - rc), -(hy - rc), 180), (hx - rc, -(hy - rc), 270)]
    for ci, (cx, cy, a0) in enumerate(corners):
        for j in range(K[1]):
            a = math.radians(a0 + 90 * j / (K[1] - 1)); pts.append((cx + rc * math.cos(a), cy + rc * math.sin(a)))
        nx, ny, _ = corners[(ci + 1) % 4]
        ex, ey = pts[-1]
        a = math.radians(a0 + 90); tx, ty = nx + rc * math.cos(a), ny + rc * math.sin(a)
        for j in range(1, K[0]): pts.append((ex + (tx - ex) * j / K[0], ey + (ty - ey) * j / K[0]))
    return pts
TMAX = min(HX, HY) - 0.6
def roof_z(t):                          # bulging profile from the top of the roll (t = LIP) to the ridge: steep near the eave, rounder near the top
    s = max(0.0, (t - LIP) / (TMAX - LIP)); return ZE + RISE * (1 - (1 - s) ** 1.12)
ring_pts = []
for k in range(9):                      # eave roll: quarter circles from under the eave (phi -90) over the outermost point (0) to the top (90)
    phi = math.radians(-90 + 180 * k / 8)
    pts = contour(LIP * (1 - math.cos(phi))); jit = math.cos(phi) * 1.6                           # straw ends: the outline of the eave is uneven
    pts = [(x + (h(i, 41) - 0.5) * jit * (abs(x) > abs(y) or 0.4), y + (h(i, 42) - 0.5) * jit * (abs(y) >= abs(x) or 0.4)) for i, (x, y) in enumerate(pts)]
    ring_pts.append((pts, ZE - LIP + LIP * math.sin(phi) - (h(len(ring_pts), 43) * 0.0)))
steps = 16
for k in range(1, steps + 1):
    t = LIP + (TMAX - LIP) * k / steps; ring_pts.append((contour(t), roof_z(t)))
def tex_uv(x, y): return ((x + HX) * DEN, (HY - y) * DEN)        # top planar texel coordinates (texture row 0 = north edge)
for (A, za), (B, zb) in zip(ring_pts, ring_pts[1:]):
    n = len(A)
    for i in range(n):
        j = (i + 1) % n
        q = [G(A[i][0], A[i][1], za), G(A[j][0], A[j][1], za), G(B[j][0], B[j][1], zb), G(B[i][0], B[i][1], zb)]
        M.face("thatch", q, [tex_uv(*A[i]), tex_uv(*A[j]), tex_uv(*B[j]), tex_uv(*B[i])])
under = ring_pts[0][0]; zu = ring_pts[0][1]
M.face("under", [G(x, y, zu) for x, y in under], [(x * DEN, y * DEN) for x, y in under])       # underside (dark straw)
top, zt = ring_pts[-1]
M.face("thatch", [G(x, y, zt) for x, y in top], [tex_uv(x, y) for x, y in top])
# ridge: a thatch roll along the ridge line + crossed short logs ('X' pairs) along it
ridge_half = abs(HX - HY); along_x = HX > HY
zr = roof_z(TMAX) + 0.8
if ridge_half > 1:
    a, b = (G(-ridge_half - 4, 0, zr), G(ridge_half + 4, 0, zr)) if along_x else (G(0, -ridge_half - 4, zr), G(0, ridge_half + 4, zr))
    M.cylinder("thatch", a, b, 3.2, n=10, density=DEN)
npairs = max(2, int((2 * ridge_half) / 14) + 1)
for k in range(npairs):
    c = -ridge_half + (2 * ridge_half) * k / (npairs - 1) if npairs > 1 else 0
    for sgn in (-1, 1):
        L = 8.0; ang = math.radians(40)
        dz, dw = L * math.sin(ang), L * math.cos(ang)
        if along_x: p0, p1 = G(c + sgn * 1.2, -dw, zr - 3), G(c + sgn * 1.2, dw, zr - 3 + 2 * dz) if sgn > 0 else G(c + sgn * 1.2, -dw, zr - 3 + 2 * dz)
        else: p0, p1 = G(-dw, c + sgn * 1.2, zr - 3), G(dw, c + sgn * 1.2, zr - 3 + 2 * dz)
        if sgn < 0:
            if along_x: p0, p1 = G(c + sgn * 1.2, dw, zr - 3), G(c + sgn * 1.2, -dw, zr - 3 + 2 * dz)
            else: p0, p1 = G(dw, c + sgn * 1.2, zr - 3), G(-dw, c + sgn * 1.2, zr - 3 + 2 * dz)
        M.cylinder("post", p0, p1, 1.5, n=8, cap="endgrain", density=DEN)
if ridge_half <= 1:                                                                          # pyramid roof: a second X pair across
    for sgn in (-1, 1):
        L = 8.0; ang = math.radians(40); dz, dw = L * math.sin(ang), L * math.cos(ang)
        M.cylinder("post", G(-dw * sgn, 1.2 * sgn, zr - 3), G(dw * sgn, 1.2 * sgn, zr - 3 + 2 * dz), 1.5, n=8, cap="endgrain", density=DEN)
for vx, vy in P["vents"]:                                                                    # roof vents: small thatch hoods with a dark mouth (house B)
    px, py = -HX + 2 * HX * vx, -HY + 2 * HY * vy; t, _, f = roof_inset(px, py); z = roof_z(min(t, TMAX))
    M.cylinder("thatch", G(px - 6, py, z + 1.5), G(px + 6, py, z + 1.5), 4.0, n=10, density=DEN)
    M.face("dark", [G(px - 4.5, py + 4.2, z - 0.5), G(px + 4.5, py + 4.2, z - 0.5), G(px + 4.5, py + 4.2, z + 3.5), G(px - 4.5, py + 4.2, z + 3.5)][::-1], [(0, 0), (16, 0), (16, 16), (0, 16)])
ob = M.finish()

# ---- export + previews ---------------------------------------------------------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "massan_house_%s.glb" % HOUSE), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
gm = blx.material("dirt", blx.px_image("dirt", dirt, 64, 64))
me = bpy.data.meshes.new("ground"); import bmesh; bm = bmesh.new(); s = 220; uvl = bm.loops.layers.uv.new("UV")
f = bm.faces.new([bm.verts.new(p) for p in ((-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0))])
for l in f.loops: l[uvl].uv = (l.vert.co.x * DEN / 64, l.vert.co.y * DEN / 64)
bm.to_mesh(me); bm.free(); me.materials.append(gm); g = bpy.data.objects.new("ground", me); bpy.context.scene.collection.objects.link(g)
view = os.environ.get("R_VIEW", "game")
px = float(os.environ.get("R_PX", "2" if blx.PIXEL else "4"))          # pixel look: 2 render pixels per game pixel = 1 per texel (shown enlarged with nearest)
sc, co = blx.game_view(os.path.join(out, "game_%s.png" % HOUSE), px_per_unit=px, size=(int(170 * px), int(140 * px)), target=G(0, 0, 24))
bpy.ops.render.render(write_still=True)
for i, yaw in enumerate((-40, 40, 180)):
    blx.orbit(co, (0, 0, 24 * math.sqrt(2 / 3)), yaw, 30); sc.render.filepath = os.path.join(out, "turn_%s_%d.png" % (HOUSE, i)); bpy.ops.render.render(write_still=True)
print("massan_house %s done ->" % HOUSE, out)
