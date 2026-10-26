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
# Original picture (room 592, cell (15, 25), 3 blocks = 48 high): a weathered grey-blue stone animal bust on a rounded trunk - a broad head with a short
# snout pointing south, two small ears and a knob on top - its lower half overgrown with green vines, ivy around the foot.  Game coordinates (x east,
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
    # stone: trunk, shoulders, head, snout, brow, ears, knob (snout towards +y = south)
    for c, sq, sd, lp in (((0, 0, 13), (7.0, 6.4, 14.5), 1, 0.08), ((0, 0.6, 24), (7.6, 6.6, 5.0), 2, 0.10), ((0, 1.4, 33.5), (7.6, 7.0, 6.0), 3, 0.08),
                          ((0, 7.4, 30.8), (5.2, 4.4, 3.0), 4, 0.06), ((0, 5.0, 36.0), (6.0, 2.6, 1.4), 5, 0.05),
                          ((-4.2, 0.4, 39.6), (1.9, 1.5, 2.6), 6, 0.05), ((4.2, 0.4, 39.6), (1.9, 1.5, 2.6), 7, 0.05), ((-1.2, -0.4, 41.0), (1.8, 1.8, 2.8), 8, 0.05)):
        _lump(bm, 0, S(*c), (sq[0], sq[1], sq[2]), seed * 10 + sd, lp)
    for sx in (-2.6, 2.6):                                                       # eye hollows and nostrils (dark)
        _lump(bm, 2, S(sx * 1.15, 6.9, 35.0), (1.1, 0.6, 0.8), seed + 40, 0.0, sub=2)
        _lump(bm, 2, S(sx * 0.6, 11.6, 31.2), (0.7, 0.4, 0.5), seed + 41, 0.0, sub=2)
    # vines: strands winding up the trunk to z 8..27, leaves along them
    def trunk_r(z): return 7.0 * math.sqrt(max(0.0, 1 - ((z - 13) / 14.5) ** 2)) + 0.5
    for k in range(16):
        a = 2 * math.pi * k / 16 + rr.uniform(-0.2, 0.2); top = rr.uniform(9, 24); turn = rr.uniform(-1.4, 1.4); pts = []
        for j in range(13):
            z = top * j / 12; aa = a + turn * j / 12; r = trunk_r(max(z, 0.5)) * 1.03
            pts.append((r * math.cos(aa), r * math.sin(aa) * 0.92 + 0.3, z))
        for p, q in zip(pts, pts[1:]):
            A = mathutils.Vector(S(*p)); B = mathutils.Vector(S(*q)); d = B - A
            res = bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=0.75 / zs, radius2=0.6 / zs, depth=d.length); vs = res["verts"]
            bmesh.ops.translate(bm, vec=(0, 0, d.length / 2), verts=vs); bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=d.normalized().to_track_quat("Z", "Y").to_matrix(), verts=vs)
            bmesh.ops.translate(bm, vec=A, verts=vs)
            for f in {f for v in vs for f in v.link_faces}: f.material_index = 1
        for j in range(2, 13, 2):                                                # leaves: small flat lumps beside the strand
            x, y, z = pts[j]; n = math.atan2(y, x); o = rr.choice((-1, 1)) * 0.25
            _lump(bm, 1, S(x + 0.8 * math.cos(n + o), y + 0.8 * math.sin(n + o), z + rr.uniform(-0.5, 0.5)), (1.5, 1.5, 0.7), rr.randint(0, 999), 0.15, sub=2)
    for k in range(30):                                                          # ivy: an even ring around the foot
        a = 2 * math.pi * k / 30 + rr.uniform(-0.1, 0.1); r = rr.uniform(6.0, 10.5); s = rr.uniform(1.1, 1.9)
        _lump(bm, 1, S(r * math.cos(a), r * math.sin(a) * 0.9 + 0.5, s * 0.35), (s, s, s * 0.45), rr.randint(0, 999), 0.2, sub=2)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    stone = bpy.data.materials.get("statue_stone") or cmat.pmat("statue_stone", (80, 88, 96), (196, 202, 204), scale=0.25, detail=6.0, bump=0.7, rough=0.85)
    vine = bpy.data.materials.get("vine") or cmat.pmat("vine", (8, 70, 26), (60, 170, 56), scale=0.4, detail=6.0, bump=0.6, rough=0.9)
    for m in (stone, vine, cmat.get("dark")): me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o
