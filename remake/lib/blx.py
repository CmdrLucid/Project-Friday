"""Remake asset helpers for Blender (run through tools/build_asset.py: flatpak blender -b -P recipe.py).
World units: 1 unit = 1 pixel of the original game (a map cell = 16 units); x east, y south, z up (like docs/FORMATS.md 'Height map = a real height field').
Textures are generated here (no ROM art): 32 x 32 tileable PIXEL textures, nearest sampling, palettes in the game's colour range.  One texel = one unit = one game pixel."""
import bpy, bmesh, math, random, os, sys

TEX = 32
PIXEL = False        # recipes set blx.PIXEL = True for the pixel-art look (toon materials, game_view without anti-aliasing + outlines)
def px_image(name, fn, w=TEX, h=TEX):
    img = bpy.data.images.new(name, w, h, alpha=False)
    buf = []
    for y in range(h - 1, -1, -1):          # bpy images are bottom-up: row 0 of fn is the TOP row
        for x in range(w):
            r, g, b = fn(x, h - 1 - y)
            buf.extend((r / 255.0, g / 255.0, b / 255.0, 1.0))
    img.pixels = buf; img.pack(); img.colorspace_settings.name = "sRGB"
    return img

# PIXEL-ART LOOK (user 2026-10-24: 'es sollte immer noch aussehen wie Pixelart, auch als 3D-Modell'): stepped light instead of smooth shading.
# Light value of a white diffuse surface (sun + sky, shadows included) -> constant ramp steps -> times the texel colour; the shadow step is a little cool.
TOON = [(0.0, (0.50, 0.50, 0.56)), (0.30, (0.70, 0.70, 0.74)), (0.62, (0.88, 0.88, 0.88)), (1.0, (1.0, 1.0, 1.0)), (1.6, (1.08, 1.07, 1.03))]
def toon_material(name, img):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    out = nt.nodes.new("ShaderNodeOutputMaterial"); tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = "Closest"; tex.extension = "REPEAT"
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse"); dif.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new("ShaderNodeShaderToRGB"); bw = nt.nodes.new("ShaderNodeRGBToBW"); mp = nt.nodes.new("ShaderNodeMapRange")
    mp.inputs["From Min"].default_value = 0.0; mp.inputs["From Max"].default_value = 2.0; mp.clamp = True
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    while len(els) > 1: els.remove(els[-1])
    sc = 1 / 1.1
    for i, (pos, c) in enumerate(TOON):
        e = els[0] if i == 0 else els.new(pos / 2.0); e.position = pos / 2.0; e.color = (c[0] * sc, c[1] * sc, c[2] * sc, 1)
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.1
    L(dif.outputs["BSDF"], s2r.inputs["Shader"]); L(s2r.outputs["Color"], bw.inputs["Color"]); L(bw.outputs["Val"], mp.inputs["Value"]); L(mp.outputs["Result"], ramp.inputs["Fac"])
    L(tex.outputs["Color"], mul.inputs[6]); L(ramp.outputs["Color"], mul.inputs[7]); L(mul.outputs[2], em.inputs["Color"]); L(em.outputs["Emission"], out.inputs["Surface"])
    return m

def material(name, img, rough=1.0):
    if PIXEL: return toon_material(name, img)
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
        self.fixed = self.bm.faces.layers.int.new("fixed_uv"); self.size = {m.name: img_size(m) for m in mats}; self.density = 1.0
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
    def face(self, mat, pts, uvs):
        """face with EXPLICIT uvs given in TEXELS of the material's image (converted in finish); pts in Blender coordinates."""
        v = [self.bm.verts.new(p) for p in pts]; f = self.bm.faces.new(v); f.material_index = self.idx[mat]
        for l, uv in zip(f.loops, uvs): l[self.uv].uv = uv
        f[self.fixed] = 1; return f
    def cylinder(self, mat, a, b, r, n=10, cap=None, density=2.0, v_turn=True, roll=0.0):
        """round log / post from a to b (radius r, n sides): u = texels along the axis, v = one full turn of the image height (v_turn)
        so a log texture is painted 'around' (row 0 = the side that faces +z or, for vertical axes, the side that faces roll)."""
        import mathutils
        A = mathutils.Vector(a); B = mathutils.Vector(b); d = B - A; ln = d.length; d.normalize()
        up = mathutils.Vector((0, 0, 1)) if abs(d.z) < 0.9 else mathutils.Vector((math.cos(roll), math.sin(roll), 0))
        u = up - d * up.dot(d); u.normalize(); w = d.cross(u)
        ring = lambda P, i: P + (u * math.cos(2 * math.pi * i / n) + w * math.sin(2 * math.pi * i / n)) * r
        H = self.size[mat][1]
        for i in range(n):
            p = [ring(A, i), ring(A, i + 1), ring(B, i + 1), ring(B, i)]
            vv = (H * i / n, H * (i + 1) / n) if v_turn else (2 * math.pi * r * density * i / n, 2 * math.pi * r * density * (i + 1) / n)
            self.face(mat, [tuple(q) for q in p], [(0, vv[0]), (0, vv[1]), (ln * density, vv[1]), (ln * density, vv[0])])
        if cap:
            cw, ch = self.size[cap]
            for P, s in ((A, -1), (B, 1)):
                pts = [ring(P, i) for i in range(n)][::(1 if s > 0 else -1)]
                self.face(cap, [tuple(q) for q in pts], [(cw / 2 + cw / 2 * math.cos(2 * math.pi * i / n * s), ch / 2 + ch / 2 * math.sin(2 * math.pi * i / n * s)) for i in range(n)])
    def torus(self, mat, c, u, w, R, r, n=24, m=8):
        """closed ring around centre c in the plane spanned by the unit vectors u, w (Blender coords); welded, so it gets ONE outline, not one per piece."""
        import mathutils
        C = mathutils.Vector(c); U = mathutils.Vector(u); Wv = mathutils.Vector(w); N = U.cross(Wv)
        tw, th = self.size[mat]
        def P(i, j):
            a = 2 * math.pi * i / n; b = 2 * math.pi * j / m; rad = U * math.cos(a) + Wv * math.sin(a)
            return tuple(C + rad * (R + r * math.cos(b)) + N * (r * math.sin(b)))
        for i in range(n):
            for j in range(m):
                self.face(mat, [P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)],
                          [(tw * i / n * 3, th * j / m), (tw * (i + 1) / n * 3, th * j / m), (tw * (i + 1) / n * 3, th * (j + 1) / m), (tw * i / n * 3, th * (j + 1) / m)])
    uv_ridge = {}     # material name -> (z at the eave, sin of the slope angle): faces of that material get u = x, v = distance along the slope (straw runs along the ridge on both sides)
    def finish(self):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)   # weld: one surface = one piece (outlines only at real edges, smooth light steps)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:                     # planar UVs: 1 unit = self.density texels (explicit face uvs are in texels)
            sw, sh = self.size[self.mats[f.material_index].name]
            if f[self.fixed]:
                for l in f.loops: uv = l[self.uv].uv; l[self.uv].uv = (uv[0] / sw, uv[1] / sh)
                continue
            n = f.normal; ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
            nm = self.mats[f.material_index].name
            for l in f.loops:
                p = l.vert.co
                if nm in self.uv_ridge and az > 0.2 and az < 0.98: u, v = p.x, (p.z - self.uv_ridge[nm][0]) / self.uv_ridge[nm][1]
                elif az >= ax and az >= ay: u, v = p.x, p.y
                elif ax >= ay: u, v = p.y, p.z
                else: u, v = p.x, p.z
                l[self.uv].uv = (u * self.density / sw, v * self.density / sh)
        me = bpy.data.meshes.new(self.name); bm.to_mesh(me); bm.free()
        for m in self.mats: me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me); bpy.context.scene.collection.objects.link(ob)
        for p in me.polygons: p.use_smooth = False
        return ob

def img_size(m):
    if m.use_nodes:
        for nd in m.node_tree.nodes:
            if nd.type == "TEX_IMAGE" and nd.image: return tuple(nd.image.size)
    return (TEX, TEX)

def game_view(out_png, px_per_unit=4, size=(680, 560), target=(0, 0, 24), sun=(-0.3, -0.8, 0.9), sun_energy=2.6, sky=0.55, squash=True):
    """camera that reproduces the ORIGINAL GAME's projection (2:1 dimetric, FORMATS 'Screen projection'): screen x = x - y, y = (x + y) / 2 - z in game pixels.
    = orthographic view from the south east at 30 deg elevation, with heights shown at sqrt(2/3) (the game draws one z unit as one pixel).
    BLENDER COORDINATES: x east, y NORTH (= minus game y), z up, so nothing is mirrored and the GLB comes out x east, y up, z south.
    squash=True scales every mesh object's z by sqrt(2/3) for this render only (call before rendering; GLB export must happen before)."""
    import mathutils
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x, sc.render.resolution_y = size; sc.render.filepath = out_png; sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    if hasattr(sc, "eevee"):
        for k, v in (("use_gtao", not PIXEL), ("gtao_distance", 6.0), ("taa_render_samples", 1 if PIXEL else 32), ("use_shadows", True), ("shadow_ray_count", 1 if PIXEL else 2),
                     ("use_shadow_jitter_viewport", False)):
            if hasattr(sc.eevee, k): setattr(sc.eevee, k, v)
    sc.render.filter_size = 0.0
    if PIXEL and hasattr(sc.render, "use_freestyle"):           # 1 pixel dark outlines (silhouettes, borders, sharp creases) like the original's black contours
        sc.render.use_freestyle = True; sc.render.line_thickness_mode = "ABSOLUTE"; sc.render.line_thickness = 1.0
        vl = sc.view_layers[0]; vl.use_freestyle = True; fs = vl.freestyle_settings; fs.crease_angle = math.radians(120)
        ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new("lines")
        ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True
        lst = ls.linestyle or bpy.data.linestyles.new("outline"); ls.linestyle = lst; lst.color = (0.07, 0.05, 0.02); lst.thickness = 1.0; lst.alpha = 1.0
        if hasattr(lst, "use_chaining"): lst.use_chaining = True
    w = bpy.data.worlds.new("w"); w.use_nodes = True; bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.78, 0.82, 1.0, 1); bg.inputs[1].default_value = sky; sc.world = w
    ld = bpy.data.lights.new("sun", "SUN"); ld.energy = sun_energy; ld.angle = 0.0 if PIXEL else math.radians(3)
    lo = bpy.data.objects.new("sun", ld); sc.collection.objects.link(lo); lo.rotation_euler = (-mathutils.Vector(sun)).to_track_quat("-Z", "Y").to_euler()
    cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"; cd.ortho_scale = size[0] / px_per_unit * math.sqrt(0.5); cd.clip_end = 5000
    co = bpy.data.objects.new("cam", cd); sc.collection.objects.link(co); sc.camera = co
    zs = math.sqrt(2.0 / 3.0) if squash else 1.0
    if squash:
        for ob in sc.objects:
            if ob.type == "MESH": ob.scale.z *= zs
    T = mathutils.Vector((target[0], target[1], target[2] * zs)); el = math.radians(30)
    co.location = T + mathutils.Vector((math.cos(el) * math.sqrt(0.5), -math.cos(el) * math.sqrt(0.5), math.sin(el))) * 2000
    co.rotation_euler = (T - co.location).to_track_quat("-Z", "Y").to_euler()
    return sc, co

def orbit(co, target, yaw_deg, el_deg=30, dist=2000):
    """turn the game_view camera around the target (yaw 0 = the game's view from the south east)."""
    import mathutils
    a = math.radians(-45 + yaw_deg); el = math.radians(el_deg); T = mathutils.Vector(target)
    co.location = T + mathutils.Vector((math.cos(el) * math.cos(a), math.cos(el) * math.sin(a), math.sin(el))) * dist
    co.rotation_euler = (T - co.location).to_track_quat("-Z", "Y").to_euler()

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
