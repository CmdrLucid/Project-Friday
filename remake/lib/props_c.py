"""STYLE C props built from simple shapes (Blender bmesh), one object each, game coordinates via massan_a.G.
animal_skull: the monster / animal skull of the Massan houses (original picture: hangs tilted above the door, long snout pointing down, big eye socket,
lower jaw with fangs, small horn stubs).  Local frame: snout along +x, up +z; placed by position + yaw (direction the snout points, degrees in the
Blender xy plane) + pitch (snout down)."""
import math
import bpy, bmesh, mathutils

def _blob(bm, mat_i, c, s, seg=(20, 12)):
    r = bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=1.0)
    vs = r["verts"]; bmesh.ops.scale(bm, vec=s, verts=vs); bmesh.ops.translate(bm, vec=c, verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.material_index = mat_i
def _cone(bm, mat_i, base, direction, length, r):
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r, radius2=0.02, depth=length)
    vs = res["verts"]; d = mathutils.Vector(direction).normalized()
    bmesh.ops.translate(bm, vec=(0, 0, length / 2), verts=vs)                    # base at the origin, tip along +z
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=d.to_track_quat("Z", "Y").to_matrix(), verts=vs)
    bmesh.ops.translate(bm, vec=base, verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.material_index = mat_i

def animal_skull(pos, bone, dark, scale=1.0, yaw=0.0, pitch=45.0, roll=0.0, length=1.0, name="skull"):
    bm = bmesh.new()
    _blob(bm, 0, (0, 0, 0.2), (2.6, 2.3, 2.3))                  # brain case (rounded back of the head)
    _blob(bm, 0, (1.8, 0, 0.9), (2.2, 2.2, 1.5))                # brow / forehead
    _blob(bm, 0, (3.6, 0, 0.1), (2.2, 1.45, 1.3))               # upper snout
    _blob(bm, 0, (5.3, 0, -0.3), (1.5, 1.05, 1.0))              # snout front, narrower
    _blob(bm, 0, (6.5, 0, -0.5), (0.85, 0.95, 0.85))            # snout tip
    for sy in (-1, 1):
        _blob(bm, 0, (2.3, 1.75 * sy, 0.6), (1.7, 0.75, 1.5))   # cheek bone around the socket
        _blob(bm, 1, (2.3, 2.15 * sy, 0.8), (1.0, 0.45, 0.85))    # dark eye socket
        _blob(bm, 1, (7.1, 0.42 * sy, -0.35), (0.38, 0.28, 0.36))  # nostril
        for k, x in enumerate((4.0, 4.8, 5.6, 6.3)):            # upper teeth, the second one a long fang
            L = 1.9 if k == 1 else 0.8
            _cone(bm, 0, (x, 0.85 * sy * (1 - 0.1 * k), -0.9), (0.1, 0.05 * sy, -1), L, 0.32 if k == 1 else 0.22)
        _cone(bm, 0, (5.2, 0.7 * sy, -2.25), (0.15, 0, 1), 1.2, 0.3)              # lower fang
        _cone(bm, 0, (0.4, 1.7 * sy, 1.8), (-0.6, 0.8 * sy, 0.5), 1.6, 0.55)      # short horn stub
    _blob(bm, 0, (3.9, 0, -2.4), (2.9, 1.05, 0.45))             # lower jaw, a little open
    _blob(bm, 1, (4.1, 0, -1.55), (2.2, 0.85, 0.45))            # dark mouth gap
    M = mathutils.Matrix.Translation(pos) @ mathutils.Matrix.Rotation(math.radians(yaw), 4, "Z") @ mathutils.Matrix.Rotation(math.radians(roll), 4, "X") \
        @ mathutils.Matrix.Rotation(math.radians(pitch), 4, "Y") @ mathutils.Matrix.Scale(scale, 4) \
        @ mathutils.Matrix.Diagonal((length, 1.0, 1.0, 1.0))                          # length < 1 = a shorter skull (back of the head to the snout tip)
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(bone); me.materials.append(dark)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob); return ob

# ---- Massan statue (2026-10-26, user: 'weiter mit der Statue') ------------------------------------------------------------------------------------------
# Original picture (room 592, cell (15, 25), 3 blocks = 48 high): a weathered stone HUMANOID BEAR like the villagers (user) - broad head with a short
# snout pointing south, round ears, shoulders and arms - its lower half overgrown with green vines, ivy around the foot.  Game coordinates (x east,
# y south, z up), G = massan_a.G; one object with the materials statue_stone / vine / dark.
def _lump(bm, mat_i, c, sq, seed, lump=0.1, sub=3):
    import random
    res = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0); rr = random.Random(seed); ph = [rr.random() * 6 for _ in range(4)]
    for v in res["verts"]:
        n = v.co.normalized(); k = 1 + lump * math.sin(3 * n.x + ph[0]) * math.sin(3 * n.y + ph[1]) + lump * 0.6 * math.sin(5 * n.z + ph[2])
        v.co = mathutils.Vector((c[0] + n.x * sq[0] * k, c[1] + n.y * sq[1] * k, c[2] + n.z * sq[2] * k))
    for f in {f for v in res["verts"] for f in v.link_faces}: f.material_index = mat_i

def massan_statue(cx, cy, z0, seed=7, name="statue", zs=1.25):
    import random
    import cmat
    from massan_a import G
    rr = random.Random(seed); bm = bmesh.new()
    S = lambda x, y, z: G(cx + x, cy + y, z0 + z * zs)                          # local game offsets -> Blender (zs: the picture's statue is ~55 high, above its 48 block)
    # stone: a HUMANOID BEAR like the Massan villagers (user 2026-10-26): short legs, round belly, rounded shoulders, arms with the paws resting on the
    # belly, broad head with a short snout pointing south (+y), round ears, a small tuft on top
    def limb(a, b, r0, r1, sd, n=9):
        for i in range(n):
            t = i / (n - 1); c = tuple(a[j] + (b[j] - a[j]) * t for j in range(3)); r = r0 + (r1 - r0) * t
            _lump(bm, 0, S(*c), (r, r, r / zs), sd * 10 + i, 0.02, sub=3)
    for sx in (-1, 1):
        limb((sx * 3.2, 0.4, 1.8), (sx * 3.0, 0.4, 9.0), 3.4, 3.0, seed + 20 + sx)                  # legs
        _lump(bm, 0, S(sx * 3.3, 2.0, 1.2), (3.0, 4.0, 1.4), seed + 24 + sx, 0.05)                    # feet
        limb((sx * 7.0, 0.4, 26.0), (sx * 8.4, 2.4, 18.5), 2.9, 2.5, seed + 30 + sx)                  # upper arms
        limb((sx * 8.4, 2.4, 18.5), (sx * 3.4, 6.6, 15.5), 2.5, 2.3, seed + 34 + sx)                  # forearms
        _lump(bm, 0, S(sx * 3.0, 7.0, 15.4), (2.4, 2.0, 2.0), seed + 38 + sx, 0.06)                   # paws on the belly
        _lump(bm, 0, S(sx * 6.4, 0.4, 26.4), (3.4, 3.4, 3.0), seed + 42 + sx, 0.06)                   # round shoulders
        _lump(bm, 0, S(sx * 4.8, 0.4, 37.6), (2.3, 1.5, 2.0), seed + 46 + sx, 0.04)                   # round ears (set into the head)
    for c, sq, sd, lp in (((0, 0.6, 18.0), (6.6, 5.8, 10.5), 1, 0.06), ((0, 2.4, 15.0), (5.4, 4.6, 6.5), 2, 0.05),     # torso, belly
                          ((0, 0.6, 27.0), (6.2, 5.2, 3.6), 3, 0.06), ((0, 1.4, 33.5), (7.4, 6.8, 6.0), 4, 0.08),      # neck, head
                          ((0, 7.4, 30.8), (4.8, 4.2, 3.0), 5, 0.06), ((0, 5.0, 36.0), (5.8, 2.6, 1.4), 6, 0.05),      # snout, brow
                          ((-0.8, 0.2, 38.2), (1.6, 1.6, 1.5), 8, 0.05)):                                               # tuft
        _lump(bm, 0, S(*c), (sq[0], sq[1], sq[2]), seed * 10 + sd, lp)
    for sx in (-2.6, 2.6):                                                       # eye hollows and nostrils (dark)
        _lump(bm, 2, S(sx * 1.15, 6.9, 35.0), (1.1, 0.6, 0.8), seed + 40, 0.0, sub=2)
        _lump(bm, 2, S(sx * 0.6, 11.4, 31.2), (0.7, 0.4, 0.5), seed + 41, 0.0, sub=2)
    # vines: strands winding up the trunk to z 8..27, leaves along them
    def body_r(z, aa):                                                          # surface of legs / torso as an ellipse (rx, ry) at height z, + a little
        if z < 9: rx, ry = 6.4, 3.6
        else: f = math.sqrt(max(0.05, 1 - ((z - 18) / 10.5) ** 2)); rx, ry = 6.6 * f, 5.8 * f + (2.0 if math.sin(aa) > 0 else 0.0) * f
        return 1.0 / math.sqrt((math.cos(aa) / rx) ** 2 + (math.sin(aa) / ry) ** 2) + 0.5
    for k in range(16):
        a = 2 * math.pi * k / 16 + rr.uniform(-0.2, 0.2); top = rr.uniform(9, 24); turn = rr.choice((-1, 1)) * rr.uniform(1.6, 3.0); pts = []
        for j in range(13):
            z = top * j / 12; aa = a + turn * j / 12 + 0.25 * math.sin(2.3 * j + k); r = body_r(max(z, 0.5), aa)
            pts.append((r * math.cos(aa), r * math.sin(aa) + 0.6, z))
        for p, q in zip(pts, pts[1:]):
            A = mathutils.Vector(S(*p)); B = mathutils.Vector(S(*q)); d = B - A
            res = bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=0.75 / zs, radius2=0.6 / zs, depth=d.length); vs = res["verts"]
            bmesh.ops.translate(bm, vec=(0, 0, d.length / 2), verts=vs); bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=d.normalized().to_track_quat("Z", "Y").to_matrix(), verts=vs)
            bmesh.ops.translate(bm, vec=A, verts=vs)
            for f in {f for v in vs for f in v.link_faces}: f.material_index = 1
        for j in range(1, 13, 2):                                                # leaves: small lumps pressed flat against the stone beside the strand
            x, y, z = pts[j]; n = math.atan2(y - 0.6, x); sn, cn = abs(math.sin(n)), abs(math.cos(n))
            _lump(bm, 1, S(x + 0.5 * math.cos(n), y + 0.5 * math.sin(n), z + rr.uniform(-0.6, 0.6)), (0.45 + 0.85 * sn, 0.45 + 0.85 * cn, 1.1), rr.randint(0, 999), 0.15, sub=2)
    for k in range(30):                                                          # ivy: an even ring around the foot
        a = 2 * math.pi * k / 30 + rr.uniform(-0.1, 0.1); r = rr.uniform(6.0, 10.5); s = rr.uniform(1.1, 1.9)
        _lump(bm, 1, S(r * math.cos(a), r * math.sin(a) * 0.9 + 0.5, s * 0.35), (s, s, s * 0.45), rr.randint(0, 999), 0.2, sub=2)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    stone = bpy.data.materials.get("statue_stone") or cmat.pmat("statue_stone", (104, 110, 114), (178, 184, 186), scale=0.1, detail=3.0, bump=0.35, rough=0.85)
    vine = bpy.data.materials.get("vine") or cmat.pmat("vine", (8, 70, 26), (60, 170, 56), scale=0.4, detail=6.0, bump=0.6, rough=0.9)
    for m in (stone, vine, cmat.get("dark")): me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o
