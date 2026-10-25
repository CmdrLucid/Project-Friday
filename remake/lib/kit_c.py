"""STYLE C kit: the APPROVED assets as placeable builders (2026-10-25), so that a whole room (recipes/room_c.py) can be assembled from them.
The geometry code is the one of the asset recipes (moved here unchanged; the recipes call these functions with their own random generator, so their
preview renders stay the same):  pine / bushes (asset 2, recipes/plants_c.py), palisade / end_post / stones (asset 3, recipes/fence_c.py),
rock / stump_row / step_row (asset 4, recipes/steps_c.py), house_a (asset 1, recipes/massan_house_vc.py).
All positions in GAME coordinates (x east, y south, z up; massan_a.G converts); z0 = height of the ground the object stands on (object location)."""
import math, random
import bpy, bmesh, mathutils
import cmat
from massan_a import G

def link(name, bm, mats, smooth=True, z0=0.0):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]): me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.location.z = z0; return o

# ---- asset 2: pine, bushes ------------------------------------------------------------------------------------------------------------------------------
def pine(x, y, height=42.0, radius=13.0, tiers=6, name="pine", rnd=None, z0=0.0):
    """game position of the trunk foot (x, y); height / radius of the crown."""
    rnd = rnd or random.Random(11)
    bm = bmesh.new()
    # crown: star-shaped tiers, tips out and drooping, notches in and up
    for i in range(tiers):
        f = i / tiers; z0t = 7.0 + f * (height - 13.0); r = radius * (1 - 0.78 * f) + 1.5; h = 10.0 - 3.0 * f
        n = 14 - i; rot = rnd.random() * math.pi; ring = []
        for k in range(2 * n):
            a = rot + math.pi * k / n; tip = k % 2 == 0
            rr = r * (1.0 if tip else 0.62) * (1 + (rnd.random() - 0.5) * 0.12); zz = z0t + (-1.6 if tip else 0.8) + (rnd.random() - 0.5) * 0.6
            ring.append(bm.verts.new(G(x + rr * math.cos(a), y + rr * math.sin(a), zz)))
        mid = [bm.verts.new(G(x + 0.55 * r * math.cos(rot + math.pi * k / n), y + 0.55 * r * math.sin(rot + math.pi * k / n), z0t + h * 0.45)) for k in range(0, 2 * n, 1)]
        top = bm.verts.new(G(x, y, z0t + h)); under = bm.verts.new(G(x, y, z0t - 0.5))
        m2 = len(ring)
        for k in range(m2):
            bm.faces.new([ring[k], ring[(k + 1) % m2], mid[(k + 1) % m2], mid[k]])
            bm.faces.new([mid[k], mid[(k + 1) % m2], top])
            bm.faces.new([ring[(k + 1) % m2], ring[k], under])
    crown = link(name, bm, cmat.get("needles"), z0=z0)
    bm = bmesh.new()                                                            # trunk + root flare (the round stump of the picture)
    r1 = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=3.0, radius2=2.4, depth=12.0)
    bmesh.ops.translate(bm, vec=(0, 0, 6.0), verts=r1["verts"])
    r2 = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=5.2, radius2=3.0, depth=3.0)
    bmesh.ops.translate(bm, vec=(0, 0, 1.5), verts=r2["verts"])
    bmesh.ops.translate(bm, vec=G(x, y, 0), verts=bm.verts)
    trunk = link(name + "_trunk", bm, cmat.get("post"), z0=z0)
    return crown, trunk

def clump(bm, c, r, sz, seed):
    """one leaf clump: an icosphere with bumpy surface, squashed by sz in z."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
    rr = random.Random(seed)
    for v in res["verts"]:
        n = v.co.normalized(); bump = 1 + 0.10 * math.sin(7 * n.x + seed) * math.sin(6 * n.y + 2 * seed) + (rr.random() - 0.5) * 0.06
        v.co = mathutils.Vector((n.x * r * bump, n.y * r * bump, n.z * r * bump * sz))
    bmesh.ops.translate(bm, vec=c, verts=res["verts"])

def bushes(cells, Hh=16.0, name="bushes", rnd=None, z0=0.0):
    """the Massan / route bushes (rooms 424 / 425 seen from the front, 2026-10-25): ONE small shrub per 16 x 16 map cell (cells = their NW corners in
    game units), a round dark green crown on a short Y-shaped brown stem; neighbouring crowns touch, so a row reads as one walkable top at Hh."""
    rnd = rnd or random.Random(11)
    bm = bmesh.new(); bs = bmesh.new(); seed = 100
    for (cx, cy) in cells:
        seed += 1; x = cx + 8 + (rnd.random() - 0.5) * 1.2; y = cy + 8 + (rnd.random() - 0.5) * 1.2
        r = 7.2 + rnd.random() * 0.4; sz = 0.8; zc = Hh + 1.0 - r * sz          # rounder crown like the original
        clump(bm, G(x, y, zc), r, sz, seed)                                     # the crown
        for k in range(5):                                                      # leaf lumps on the crown: a rounder, leafy outline
            seed += 1; a = 2 * math.pi * k / 5 + rnd.random(); rr = 2.8 + rnd.random() * 1.0
            clump(bm, G(x + 4.4 * math.cos(a), y + 4.4 * math.sin(a), zc + 0.3 + rnd.random() * 0.8), rr, 0.95, seed)
        zb = zc - r * sz + 1.0                                                  # bottom of the crown
        for (a, b, rad) in (                                          # Y fork: the main pair spreads across the game camera's view (game x = -y), a thinner pair the other way
                ((0, 0, -0.5), (0, 0, 1.3), 0.85), ((0, 0, 0.9), (-3.4, 3.4, zb + 2.2), 0.75), ((0, 0, 0.9), (3.4, -3.4, zb + 2.2), 0.75), ((0, 0, 1.6), (2.0, 2.0, zb + 1.8), 0.45), ((0, 0, 1.6), (-2.0, -2.0, zb + 1.8), 0.45)):
            pa = G(x + a[0], y + a[1], a[2]); pb = G(x + b[0], y + b[1], b[2])
            A = mathutils.Vector(pa); B = mathutils.Vector(pb); d = B - A
            res = bmesh.ops.create_cone(bs, cap_ends=True, segments=8, radius1=rad, radius2=rad * 0.75, depth=d.length)
            vs = res["verts"]; bmesh.ops.translate(bs, vec=(0, 0, d.length / 2), verts=vs)
            bmesh.ops.rotate(bs, cent=(0, 0, 0), matrix=d.normalized().to_track_quat("Z", "Y").to_matrix(), verts=vs); bmesh.ops.translate(bs, vec=A, verts=vs)
    crowns = link(name, bm, cmat.get("shrub"), z0=z0); stems = link(name + "_stems", bs, cmat.get("stem"), z0=z0); return crowns, stems

# ---- asset 3: palisade -------------------------------------------------------------------------------------------------------------------------------
def fence_mats():
    if "stake" in bpy.data.materials: return [bpy.data.materials["stake"], bpy.data.materials["stake_tip"]]
    return [cmat.pmat("stake", (142, 88, 44), (196, 136, 78), scale=0.3, stretch=(1, 1, 6), bump=0.4, rough=0.85),
            cmat.pmat("stake_tip", (52, 38, 20), (88, 64, 34), scale=0.4, bump=0.2, rough=0.9)]

def cyl(bm, a, b, r1, r2, seg=10, mat_i=0):
    A = mathutils.Vector(a); B = mathutils.Vector(b); d = B - A
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=d.length)
    vs = res["verts"]; bmesh.ops.translate(bm, vec=(0, 0, d.length / 2), verts=vs)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=d.normalized().to_track_quat("Z", "Y").to_matrix(), verts=vs); bmesh.ops.translate(bm, vec=A, verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.material_index = mat_i

def stake(bm, x, y, h, r, lean):
    """one sharpened stake: shaft (wood) + point (dark tip), leaning by lean = (dx, dy) per unit of height."""
    top = (x + lean[0] * h, y + lean[1] * h, h); tip = (x + lean[0] * (h + 3.5), y + lean[1] * (h + 3.5), h + 3.5)
    cyl(bm, G(x, y, -1.0), G(*top), r, r * 0.92, 10, 0)
    cyl(bm, G(*top), G(*tip), r * 0.92, 0.12, 10, 1)

def palisade(bm, p0, p1, inner, spacing=3.3, rnd=None, rails=True):
    """stakes from p0 to p1 (game x, y); inner = unit vector to the inside (for the binding rail)."""
    L = math.dist(p0, p1); n = max(2, int(L / spacing)); ux, uy = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L
    for k in range(n + 1):
        t = k / n; x = p0[0] + (p1[0] - p0[0]) * t + (rnd.random() - 0.5) * 0.5; y = p0[1] + (p1[1] - p0[1]) * t + (rnd.random() - 0.5) * 0.5
        h = 21.0 + rnd.random() * 3.0; r = 1.2 + rnd.random() * 0.3
        lean = ((rnd.random() - 0.5) * 0.06, (rnd.random() - 0.5) * 0.06)
        stake(bm, x, y, h, r, lean)
    if not rails: return
    for z in (6.0, 15.0):                                                        # binding rail on the inner side
        a = (p0[0] + inner[0] * 1.6, p0[1] + inner[1] * 1.6, z); b = (p1[0] + inner[0] * 1.6, p1[1] + inner[1] * 1.6, z)
        cyl(bm, G(*a), G(*b), 0.6, 0.6, 8, 0)

def end_post(bm, x, y):
    cyl(bm, G(x, y, -1.0), G(x, y, 25.0), 2.6, 2.4, 14, 0)
    cyl(bm, G(x, y, 25.0), G(x, y, 26.2), 2.45, 2.2, 14, 1)                      # dark flat top

def stones(x, y, n=3, rnd=None, z0=0.0):
    bm = bmesh.new()
    for k in range(n):
        res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0); r = 1.6 + rnd.random() * 1.2
        rr = random.Random(k + int(x))
        for v in res["verts"]: v.co = mathutils.Vector((v.co.x * r * (1 + (rr.random() - 0.5) * 0.3), v.co.y * r * (1 + (rr.random() - 0.5) * 0.3), v.co.z * r * 0.65))
        bmesh.ops.translate(bm, vec=G(x + (rnd.random() - 0.5) * 6, y + 3 + rnd.random() * 3, r * 0.3), verts=res["verts"])
    return link("stones", bm, cmat.get("boulder"), z0=z0)

# ---- asset 4: steps ----------------------------------------------------------------------------------------------------------------------------------
def rock(bm, c, r, sq=(1, 1, 1), seed=0, lump=0.12):
    res = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0); rr = random.Random(seed)
    ph = [rr.random() * 6 for _ in range(4)]
    for v in res["verts"]:
        n = v.co.normalized(); k = 1 + lump * math.sin(3 * n.x + ph[0]) * math.sin(3 * n.y + ph[1]) + lump * 0.6 * math.sin(5 * n.z + ph[2])
        v.co = mathutils.Vector((n.x * r * sq[0] * k, n.y * r * sq[1] * k, n.z * r * sq[2] * k))
    bmesh.ops.translate(bm, vec=c, verts=res["verts"])

def stump_row(bm, bm_body, x0, x1, y_front, depth, h, seed, rnd=None):
    """Massan variant (user 2026-10-25: 'sieht eher nach Baumstaemmen im Boden aus'): the step is rows of UPRIGHT LOG STUMPS set in the ground,
    tops at h (+-0.7, slightly domed, weathered grey), rows 7.5 apart and staggered, radius ~3.6.  Front edge y_front (south), x0..x1 along x."""
    bmesh.ops.create_cube(bm_body, size=1.0); vs = bm_body.verts[-8:]
    bmesh.ops.scale(bm_body, vec=(x1 - x0 - 8, depth - 7, h - 3), verts=vs); bmesh.ops.translate(bm_body, vec=G((x0 + x1) / 2, y_front - 3.5 - (depth - 7) / 2, (h - 3) / 2), verts=vs)   # core behind the stump centres
    rows = max(1, int(depth / 7.5))
    for j in range(rows):
        y0 = y_front - 3.7 - j * 7.5; x = x0 + 2.5 + (3.0 if j % 2 else 0.0) * rnd.random()
        while x < x1 - 2.5:
            seed += 1; r = 3.1 + rnd.random() * 1.1                               # irregular like the original: sizes, heights, lean, slanted cuts
            xc = x + r; x = xc + r + rnd.random() * 0.6
            if xc > x1 - 1.5: break
            top = h - 0.4 + (rnd.random() - 0.5) * 0.4                                 # same height for all stumps, like the original
            res = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r * (1.0 + rnd.random() * 0.1), radius2=r * (0.88 + rnd.random() * 0.1), depth=top + 1.0)
            vs = res["verts"]; bmesh.ops.translate(bm, vec=(0, 0, (top + 1.0) / 2 - 1.0), verts=vs)
            sa, sb = (rnd.random() - 0.5) * 0.08, (rnd.random() - 0.5) * 0.08   # slanted, uneven top cut
            for v in vs:
                if v.co.z > top - 0.01:
                    v.co.z += sa * v.co.x + sb * v.co.y + (0.9 if math.hypot(v.co.x, v.co.y) < 0.01 else (rnd.random() - 0.5) * 0.5)
                v.co.x *= 1 + (rnd.random() - 0.5) * 0.08; v.co.y *= 1 + (rnd.random() - 0.5) * 0.08
            uvl = bm.loops.layers.uv.verify()                                    # the top cap: own material (growth rings) with a disc UV
            for f in {f for v in vs for f in v.link_faces}:
                if f.normal.z > 0.7:
                    f.material_index = 1
                    for l in f.loops: l[uvl].uv = (0.5 + l.vert.co.x / (2 * r), 0.5 + l.vert.co.y / (2 * r))
            lean = mathutils.Euler(((rnd.random() - 0.5) * 0.04, (rnd.random() - 0.5) * 0.04, rnd.random() * 6.28)).to_matrix()
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=lean, verts=vs)
            bmesh.ops.translate(bm, vec=G(xc, y0 + (rnd.random() - 0.5) * 1.4, 0), verts=vs)
    return seed

def step_row(bm_st, bm_body, x0, x1, y_front, depth, h, seed, rnd=None):
    """one step: cells from x0 to x1 (game x), front edge at y_front (south), 'depth' units deep to the north, top at h."""
    # earth body (hidden behind the stones, closes the gaps)
    bmesh.ops.create_cube(bm_body, size=1.0); vs = bm_body.verts[-8:]
    bmesh.ops.scale(bm_body, vec=(x1 - x0, depth, h - 1), verts=vs); bmesh.ops.translate(bm_body, vec=G((x0 + x1) / 2, y_front - depth / 2 - 1.5, (h - 1) / 2), verts=vs)
    n = int((x1 - x0) / 7.6)
    for k in range(n):                                                          # two courses of stones on the front face
        x = x0 + (k + 0.5) * (x1 - x0) / n
        for (zc, rz, off) in ((h - 4.6, 4.4, 0.0), (h - 12.0, 4.2, 0.5)):
            if zc - rz < -2: continue
            seed += 1; xx = x + off * 3.8 + (rnd.random() - 0.5) * 1.2
            rock(bm_st, G(xx, y_front - 2.8, zc), 4.0 + rnd.random() * 0.6, (1.0, 0.85, rz / 4.4 * 0.95), seed)
    for k in range(n):                                                          # cap stones on top (walking surface: tops at h .. h + 1)
        for j, yy in enumerate((y_front - 4.0, y_front - 11.5)):
            if y_front - yy > depth - 2: continue
            seed += 1; x = x0 + (k + 0.5 + 0.5 * (j % 2)) * (x1 - x0) / n
            if x > x1 - 2: continue
            r = 4.0 + rnd.random() * 0.5; sz = 0.45
            rock(bm_st, G(x + (rnd.random() - 0.5) * 1.5, yy + (rnd.random() - 0.5) * 1.5, h + 1.0 - r * sz), r, (1.0, 1.0, sz), seed)
    return seed

# ---- asset 5d: cave mouth in a rock slope ----------------------------------------------------------------------------------------------------------
def cave_mouth(p0, across, upslope, normal, into, half_w, height, rock, dark, seed=3, name="cave"):
    """a cave entrance lying IN a slope (user 2026-10-25: the dark oval cut by the rock facets 'sieht seltsam aus'): p0 = middle of the opening's
    foot on the ground (game coordinates), across / upslope / normal = unit vectors of the slope plane, into = horizontal direction into the
    mountain; a dark half-elliptic opening, a short dark tunnel going in (depth from oblique views) and an angular rock arch around it."""
    V = mathutils.Vector; p0 = V(p0); A, B, Nn, I = V(across), V(upslope), V(normal), V(into); rr = random.Random(seed)
    bmd = bmesh.new(); outline = []
    for k in range(17):
        t = math.pi * k / 16; outline.append(p0 + A * (half_w * math.cos(t)) + B * (height * math.sin(t)) + Nn * 0.3)
    back = [q + I * 16.0 - Nn * 0.0 for q in outline]                            # the tunnel: the outline pushed 16 into the mountain
    vo = [bmd.verts.new(G(*q)) for q in outline]; vb = [bmd.verts.new(G(*q)) for q in back]
    for k in range(16): bmd.faces.new([vo[k], vo[k + 1], vb[k + 1], vb[k]])
    bmd.faces.new(vb[::-1]); bmd.faces.new([vo[0], vb[0], vb[-1], vo[-1]])       # back wall, floor
    for f in bmd.faces: f.normal_update()
    od = link(name + "_hole", bmd, dark, smooth=False)
    bmr = bmesh.new()                                                            # the rock arch: an angular tube along the outline
    ring = []
    for k in range(17):
        t = math.pi * k / 16; c = p0 + A * ((half_w + 2.5 + rr.random() * 1.5) * math.cos(t)) + B * ((height + 2.5 + rr.random() * 1.5) * math.sin(t)) + Nn * (rr.random() * 1.6 - 0.4)
        if k in (0, 16): c = c - B * 2.0                                         # the ends go into the ground
        tang = (-A * math.sin(t) * half_w + B * math.cos(t) * height).normalized(); side = tang.cross(Nn).normalized()
        r = 2.4 + rr.random() * 2.6 + 1.5 * math.sin(t) ** 2; ring.append([bmr.verts.new(G(*(c + (Nn * math.cos(2 * math.pi * j / 6) + side * math.sin(2 * math.pi * j / 6)) * r * (0.8 + rr.random() * 0.4)))) for j in range(6)])
    for k in range(16):
        for j in range(6): bmr.faces.new([ring[k][j], ring[k][(j + 1) % 6], ring[k + 1][(j + 1) % 6], ring[k + 1][j]])
    bmr.faces.new(ring[0][::-1]); bmr.faces.new(ring[-1])
    for f in bmr.faces: f.normal_update()
    orr = link(name + "_arch", bmr, rock, smooth=False)
    return od, orr

# ---- asset 1: Massan house A -------------------------------------------------------------------------------------------------------------------------
def house_a(name="massan_house_vc"):
    """builds the approved house A in style C at its own place (lib/massan_a.py: walls X0..X1 / Y0..Y1, door east) and returns its objects."""
    import blx, props_c, massan_a as H
    mats = [cmat.get(n) for n in ("bark", "post", "endgrain", "dark", "hole", "thatch", "under", "bone", "plank")]
    M = blx.Mesh(name, mats); M.density = 1.0
    # 1:1 the original (user 2026-10-25: 'mach es mal 1:1 wie im Original'): the picture's heights (door 35 > Nigel's 31), only a little more eave
    H.POSTS = dict(H.POSTS, E=[445, 452, 462.5, 485.5, 492, 499])               # the door posts stand just beside the opening (picture), not in it
    H.build(M, nseg=20, den=1.0, roof_jitter=0.5, hx=H.HX + 1.5, lip=3.5, door="open", ridge_knot=True)      # open dark doorway like the original
    ob = M.finish()
    for p in ob.data.polygons: p.use_smooth = True
    ya = (H.DOOR["a0"] + H.DOOR["a1"]) / 2                                       # the animal skull of the original, hanging tilted over the doorway
    sk = props_c.animal_skull(H.G(H.X1 + 2.6, ya + 1.0, 40.5), bpy.data.materials["bone"], bpy.data.materials["dark"], scale=1.9, yaw=0.0, pitch=25.0, roll=0.0, length=0.6)
    return [ob, sk]

def place_copy(objs, centre_from, centre_to, yaw_deg=0.0, scale=(1, 1, 1), z0=0.0, name="copy"):
    """linked copies of objs (sharing mesh data) moved from centre_from to centre_to (game x, y), turned by yaw (degrees, counter-clockwise seen from
    above in game coordinates = Blender), scaled in the object's own x / y / z first."""
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e)
    e.location = (centre_to[0], -centre_to[1], z0); e.rotation_euler = (0, 0, math.radians(yaw_deg)); e.scale = scale
    out = []
    for o in objs:
        c = o.copy(); bpy.context.scene.collection.objects.link(c)
        c.parent = e; c.location = (o.location.x - centre_from[0], o.location.y + centre_from[1], o.location.z); out.append(c)
    return e, out
