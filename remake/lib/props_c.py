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
