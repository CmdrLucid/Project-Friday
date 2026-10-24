"""Remake asset helpers for Blender (run through tools/build_asset.py: flatpak blender -b -P recipe.py).
World units: 1 unit = 1 pixel of the original game (a map cell = 16 units); x east, y south, z up (like docs/FORMATS.md 'Height map = a real height field').
Textures are generated here (no ROM art): 32 x 32 tileable PIXEL textures, nearest sampling, palettes in the game's colour range.  One texel = one unit = one game pixel."""
import bpy, bmesh, math, random, os, sys

TEX = 32
def px_image(name, fn, w=TEX, h=TEX):
    img = bpy.data.images.new(name, w, h, alpha=False)
    buf = []
    for y in range(h - 1, -1, -1):          # bpy images are bottom-up: row 0 of fn is the TOP row
        for x in range(w):
            r, g, b = fn(x, h - 1 - y)
            buf.extend((r / 255.0, g / 255.0, b / 255.0, 1.0))
    img.pixels = buf; img.pack(); img.colorspace_settings.name = "sRGB"
    return img

def material(name, img, rough=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img; tex.interpolation = "Closest"; tex.extension = "REPEAT"
    bsdf.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in bsdf.inputs: bsdf.inputs["Specular IOR Level"].default_value = 0.0
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"]); nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m

def flat_material(name, rgb, rough=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF"); b.inputs["Base Color"].default_value = (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1); b.inputs["Roughness"].default_value = rough
    return m

class Mesh:
    """One object, many material slots; faces get planar UVs (1 texel = 1 unit) along the axis the face looks along."""
    def __init__(self, name, mats):
        self.name = name; self.mats = mats; self.bm = bmesh.new(); self.uv = self.bm.loops.layers.uv.new("UV"); self.idx = {m.name: i for i, m in enumerate(mats)}
    def quad(self, mat, p0, p1, p2, p3, flip=False):
        v = [self.bm.verts.new(p) for p in (p0, p1, p2, p3)]
        if flip: v.reverse()
        f = self.bm.faces.new(v); f.material_index = self.idx[mat]; return f
    def tri(self, mat, p0, p1, p2):
        f = self.bm.faces.new([self.bm.verts.new(p) for p in (p0, p1, p2)]); f.material_index = self.idx[mat]; return f
    def box(self, mat, x0, x1, y0, y1, z0, z1):
        P = lambda x, y, z: (x, y, z)
        self.quad(mat, P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1))                       # top
        self.quad(mat, P(x0, y0, z0), P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0))                       # bottom
        self.quad(mat, P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1))                       # north (-y)
        self.quad(mat, P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1))                       # south (+y)
        self.quad(mat, P(x0, y1, z0), P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1))                       # west (-x)
        self.quad(mat, P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1))                       # east (+x)
    def beam(self, mat, a, b, w):
        import mathutils
        A = mathutils.Vector(a); B = mathutils.Vector(b); d = (B - A); ln = d.length; d.normalize()
        u = d.cross(mathutils.Vector((0, 0, 1)))
        if u.length < 1e-4: u = mathutils.Vector((1, 0, 0))
        u.normalize(); v = d.cross(u); v.normalize(); h = w / 2
        c = [(A + u * (-h) + v * (-h)), (A + u * h + v * (-h)), (A + u * h + v * h), (A + u * (-h) + v * h)]; e = [p + d * ln for p in c]
        for i in range(4):
            j = (i + 1) % 4
            self.quad(mat, tuple(c[i]), tuple(c[j]), tuple(e[j]), tuple(e[i]))
        self.quad(mat, tuple(c[3]), tuple(c[2]), tuple(c[1]), tuple(c[0])); self.quad(mat, tuple(e[0]), tuple(e[1]), tuple(e[2]), tuple(e[3]))
    uv_ridge = {}     # material name -> (z at the eave, sin of the slope angle): faces of that material get u = x, v = distance along the slope (straw runs along the ridge on both sides)
    def finish(self):
        bm = self.bm; bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:                     # planar UVs: 1 unit = 1 texel
            n = f.normal; ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
            nm = self.mats[f.material_index].name
            for l in f.loops:
                p = l.vert.co
                if nm in self.uv_ridge and az > 0.2 and az < 0.98: u, v = p.x, (p.z - self.uv_ridge[nm][0]) / self.uv_ridge[nm][1]
                elif az >= ax and az >= ay: u, v = p.x, p.y
                elif ax >= ay: u, v = p.y, p.z
                else: u, v = p.x, p.z
                l[self.uv].uv = (u / TEX, v / TEX)
        me = bpy.data.meshes.new(self.name); bm.to_mesh(me); bm.free()
        for m in self.mats: me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me); bpy.context.scene.collection.objects.link(ob)
        for p in me.polygons: p.use_smooth = False
        return ob

def pixel_rng(seed): return random.Random(seed)

def setup_render(out_png, size=(960, 720), yaw_deg=30, pitch_deg=35.264, dist=400, target=(0, 0, 20), ortho_scale=190, sun=(-0.62, -0.38, 0.58)):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x, sc.render.resolution_y = size; sc.render.filepath = out_png; sc.render.image_settings.file_format = "PNG"
    sc.render.filter_size = 0.0
    w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.20, 0.22, 0.28, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0; sc.world = w
    ld = bpy.data.lights.new("sun", "SUN"); ld.energy = 3.2; ld.angle = 0.05
    lo = bpy.data.objects.new("sun", ld); sc.collection.objects.link(lo)
    import mathutils
    d = mathutils.Vector(sun); lo.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"; cd.ortho_scale = ortho_scale
    co = bpy.data.objects.new("cam", cd); sc.collection.objects.link(co); sc.camera = co
    aim(co, yaw_deg, pitch_deg, dist, target)
    return sc, co

def aim(co, yaw_deg, pitch_deg=35.264, dist=400, target=(0, 0, 20)):
    import mathutils
    yaw = math.radians(yaw_deg); pit = math.radians(pitch_deg)
    # the game looks from the south east: camera at (+x, +y, +z) looking at the target
    ang = math.radians(45) + yaw
    co.location = (target[0] + dist * math.cos(pit) * math.cos(ang), target[1] + dist * math.cos(pit) * math.sin(ang), target[2] + dist * math.sin(pit))
    co.rotation_euler = (mathutils.Vector(target) - co.location).to_track_quat("-Z", "Y").to_euler()

def render_views(sc, co, base_png, yaws, **kw):
    for i, y in enumerate(yaws):
        aim(co, y, **kw); sc.render.filepath = base_png.replace(".png", "_%d.png" % i); bpy.ops.render.render(write_still=True)

def ground_plane(rgb=(120, 86, 48), size=400):
    m = flat_material("ground", rgb, 1.0)
    me = bpy.data.meshes.new("ground"); bm = bmesh.new(); s = size / 2
    f = bm.faces.new([bm.verts.new(p) for p in ((-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0))]); bm.to_mesh(me); bm.free(); me.materials.append(m)
    ob = bpy.data.objects.new("ground", me); bpy.context.scene.collection.objects.link(ob); return ob

def export_glb(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, use_selection=False, export_image_format="AUTO", export_yup=True)
