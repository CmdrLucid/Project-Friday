"""STYLE C material library (user 2026-10-25: smooth 'toy diorama' look): soft painted procedural materials for Blender (EEVEE), shared by all recipes.
Every material = two colours (sRGB 0..255, from the original's palette ramps) mixed by object-space noise, a light bump, optional extras:
  stretch  longer blotches along an axis (wood grain, straw), streaks = strands along z (thatch), cells = cobbles / bricks with dark seams (Voronoi),
  strata = horizontal rock layers, gloss = water / wet look (low roughness), alpha.
get(name) builds a library material once (LIB below); pmat(...) makes an ad-hoc one.  modern_look(scene) = the C light: warm low sun, AgX colours, soft shadows."""
import math
import bpy

def srgb(c): return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)

def pmat(name, c1, c2, scale=0.15, detail=4.0, bump=0.3, stretch=(1, 1, 1), rough=0.75, streaks=0.0, cells=0.0, seam=(30, 26, 20), strata=0.0, gloss=False, alpha=1.0, top=None, top_from=0.35, top_to=0.85):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale / stretch[0], scale / stretch[1], scale / stretch[2])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Detail"].default_value = detail
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[0].color = srgb(c1); ramp.color_ramp.elements[1].color = srgb(c2)
    L(tc.outputs["Object"], mp.inputs["Vector"]); L(mp.outputs["Vector"], nz.inputs["Vector"]); L(nz.outputs["Fac"], ramp.inputs["Fac"])
    colour = ramp.outputs["Color"]; height = nz.outputs["Fac"]
    bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = bump
    if streaks:                                                                  # strands along z
        wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"; wv.inputs["Scale"].default_value = streaks; wv.inputs["Distortion"].default_value = 6.0
        mp2 = nt.nodes.new("ShaderNodeMapping"); mp2.inputs["Rotation"].default_value = (0, math.radians(90), 0); L(tc.outputs["Object"], mp2.inputs["Vector"]); L(mp2.outputs["Vector"], wv.inputs["Vector"])
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MULTIPLY"; L(wv.outputs["Fac"], mx.inputs[0]); L(height, mx.inputs[1]); height = mx.outputs[0]
        sc_ = nt.nodes.new("ShaderNodeMix"); sc_.data_type = "RGBA"; sc_.blend_type = "MULTIPLY"; sc_.inputs["Factor"].default_value = 0.45   # dark gaps between strands
        L(colour, sc_.inputs[6]); L(wv.outputs["Color"], sc_.inputs[7]); colour = sc_.outputs[2]
    if strata:                                                                   # horizontal rock layers, slightly wavy
        wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "Z"; wv.inputs["Scale"].default_value = strata; wv.inputs["Distortion"].default_value = 3.0
        L(tc.outputs["Object"], wv.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs["Factor"].default_value = 0.35
        L(colour, mix.inputs[6]); L(wv.outputs["Color"], mix.inputs[7]); colour = mix.outputs[2]
        ad = nt.nodes.new("ShaderNodeMath"); ad.operation = "ADD"; L(wv.outputs["Fac"], ad.inputs[0]); L(height, ad.inputs[1]); height = ad.outputs[0]
    if cells:                                                                    # cobbles / bricks: Voronoi distance to the cell edge = dark seams + rounded stones
        vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.feature = "DISTANCE_TO_EDGE"; vo.inputs["Scale"].default_value = cells
        L(tc.outputs["Object"], vo.inputs["Vector"])
        sr = nt.nodes.new("ShaderNodeMapRange"); sr.inputs["From Min"].default_value = 0.0; sr.inputs["From Max"].default_value = 0.08
        L(vo.outputs["Distance"], sr.inputs["Value"])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.inputs[7].default_value = srgb(seam)
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0; L(sr.outputs["Result"], inv.inputs[1])
        L(inv.outputs[0], mix.inputs["Factor"]); L(colour, mix.inputs[6]); colour = mix.outputs[2]
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; L(sr.outputs["Result"], mul.inputs[0]); L(height, mul.inputs[1]); height = mul.outputs[0]
    if top:                                                                      # faces looking up get another colour (stone tops grey, sides earthy)
        geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); L(geo.outputs["Normal"], sep.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = top_from; mr.inputs["From Max"].default_value = top_to; L(sep.outputs["Z"], mr.inputs["Value"])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; L(mr.outputs["Result"], mix.inputs["Factor"]); L(colour, mix.inputs[6])
        tr = nt.nodes.new("ShaderNodeMix"); tr.data_type = "RGBA"; tr.inputs[6].default_value = srgb(top[0]); tr.inputs[7].default_value = srgb(top[1]); L(nz.outputs["Fac"], tr.inputs["Factor"])
        L(tr.outputs[2], mix.inputs[7]); colour = mix.outputs[2]
    L(colour, b.inputs["Base Color"]); L(height, bm.inputs["Height"]); L(bm.outputs["Normal"], b.inputs["Normal"])
    if gloss:
        b.inputs["Roughness"].default_value = 0.06
        if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = 0.6
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"): m.surface_render_method = "BLENDED"
    L(b.outputs["BSDF"], o.inputs["Surface"])
    return m

# name: (description, pmat arguments).  Colours from the original's ramps (GREEN / BROWN / THATCH of the Massan picture, cliff / ground tones of room 592).
LIB = {
    "bark":     ("mossy log (Massan houses)", dict(c1=(40, 84, 20), c2=(104, 134, 40), scale=0.25, stretch=(5, 1, 1), bump=0.5)),
    "post":     ("light wood: posts, beams", dict(c1=(150, 92, 44), c2=(196, 130, 70), scale=0.2, stretch=(1, 1, 5), bump=0.2)),
    "endgrain": ("cut log ends", dict(c1=(170, 120, 70), c2=(214, 168, 110), scale=0.4, bump=0.1)),
    "plank":    ("dark planks: doors, crates", dict(c1=(92, 58, 28), c2=(128, 84, 44), scale=0.3, stretch=(1, 1, 6), bump=0.4, rough=0.85)),
    "thatch":   ("straw roof", dict(c1=(190, 128, 18), c2=(242, 196, 66), scale=0.35, stretch=(1, 1, 5), bump=1.2, rough=0.9, streaks=4.5)),
    "under":    ("straw underside / shadow", dict(c1=(110, 80, 24), c2=(150, 112, 40), rough=1.0)),
    "dark":     ("openings, inside", dict(c1=(10, 12, 8), c2=(24, 26, 16), rough=1.0)),
    "hole":     ("window hole", dict(c1=(8, 14, 10), c2=(20, 28, 20), rough=1.0)),
    "bone":     ("skull, bones", dict(c1=(226, 220, 200), c2=(246, 242, 230), scale=0.5, bump=0.1, rough=0.5)),
    "cobble":   ("stone path / steps", dict(c1=(126, 120, 106), c2=(176, 168, 148), scale=0.3, bump=0.4, rough=0.85, cells=0.12)),
    "cliff":    ("orange-brown rock face (Massan cliffs)", dict(c1=(150, 96, 64), c2=(206, 150, 110), scale=0.06, detail=6.0, bump=0.8, rough=0.9, strata=0.05)),
    "boulder":  ("grey stones, walls", dict(c1=(110, 108, 100), c2=(168, 164, 150), scale=0.12, detail=6.0, bump=0.6, rough=0.85)),
    "grass":    ("meadow", dict(c1=(62, 112, 28), c2=(112, 152, 44), scale=0.05, detail=8.0, bump=0.3, rough=1.0)),
    "dirt":     ("village ground / path", dict(c1=(120, 90, 46), c2=(166, 128, 72), scale=0.04, detail=8.0, bump=0.2, rough=1.0)),
    "sand":     ("beach", dict(c1=(206, 176, 116), c2=(234, 212, 158), scale=0.06, detail=6.0, bump=0.15, rough=1.0)),
    "water":    ("water", dict(c1=(36, 92, 150), c2=(70, 140, 196), scale=0.03, detail=3.0, bump=0.15, gloss=True)),
    "needles":  ("pine foliage", dict(c1=(22, 104, 42), c2=(96, 178, 66), scale=0.3, stretch=(1, 1, 2), detail=8.0, bump=0.9, rough=0.95)),
    "leaves":   ("hedges, bushes", dict(c1=(36, 104, 28), c2=(98, 150, 40), scale=0.25, detail=8.0, bump=0.9, rough=0.95)),
    "shrub":    ("bush crowns (dark green, lit lumps)", dict(c1=(8, 58, 24), c2=(58, 132, 40), scale=0.3, detail=8.0, bump=0.8, rough=0.95)),
    "stem":     ("bush stems", dict(c1=(118, 78, 34), c2=(168, 118, 58), scale=0.4, stretch=(1, 1, 4), bump=0.2)),
    "stepstone":("rounded step stones: grey-blue tops, earthy sides (Massan steps)", dict(c1=(112, 84, 44), c2=(168, 132, 76), scale=0.25, detail=5.0, bump=0.5, rough=0.85, top=((104, 120, 128), (170, 182, 186)))),
    "stump":    ("upright log steps: ochre bark sides, weathered grey-blue tops (Massan steps)", dict(c1=(132, 90, 40), c2=(190, 140, 70), scale=0.3, stretch=(1, 1, 5), detail=5.0, bump=0.5, rough=0.85, top=((110, 124, 128), (168, 178, 178)), top_from=0.55, top_to=0.8)),
    "earth":    ("packed earth behind stone walls", dict(c1=(70, 52, 28), c2=(104, 80, 44), scale=0.1, detail=6.0, bump=0.3, rough=1.0)),
    "clay":     ("red roof tiles (Mercator)", dict(c1=(156, 68, 40), c2=(204, 104, 62), scale=0.3, bump=0.4, rough=0.8, cells=0.18)),
    "plaster":  ("whitewashed walls (Mercator)", dict(c1=(214, 204, 184), c2=(240, 232, 214), scale=0.08, bump=0.15, rough=0.9)),
}
def rings_mat(name="stumptop", c1=(104, 116, 118), c2=(172, 180, 176), dark=(84, 74, 52), n=5.0):
    """cut log top: grey weathered wood with growth rings around the UV centre (UV 0..1 over the disc), a darker rim and a little noise."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.inputs["Roughness"].default_value = 0.85
    tc = nt.nodes.new("ShaderNodeTexCoord"); sub = nt.nodes.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; L(tc.outputs["UV"], sub.inputs[0]); L(sub.outputs[0], ln.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6.0; L(tc.outputs["UV"], nz.inputs["Vector"])
    wob = nt.nodes.new("ShaderNodeMath"); wob.operation = "MULTIPLY_ADD"; L(nz.outputs["Fac"], wob.inputs[0]); wob.inputs[1].default_value = 0.06; L(ln.outputs["Value"], wob.inputs[2])
    sn = nt.nodes.new("ShaderNodeMath"); sn.operation = "MULTIPLY"; L(wob.outputs[0], sn.inputs[0]); sn.inputs[1].default_value = 2 * math.pi * n
    si = nt.nodes.new("ShaderNodeMath"); si.operation = "SINE"; L(sn.outputs[0], si.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1; mr.inputs["From Max"].default_value = 1; mr.inputs["To Min"].default_value = 0.25; mr.inputs["To Max"].default_value = 0.85; L(si.outputs[0], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.inputs[6].default_value = srgb(c1); mix.inputs[7].default_value = srgb(c2); L(mr.outputs["Result"], mix.inputs["Factor"])
    rim = nt.nodes.new("ShaderNodeMapRange"); rim.inputs["From Min"].default_value = 0.4; rim.inputs["From Max"].default_value = 0.5; L(ln.outputs["Value"], rim.inputs["Value"])
    mx2 = nt.nodes.new("ShaderNodeMix"); mx2.data_type = "RGBA"; L(rim.outputs["Result"], mx2.inputs["Factor"]); L(mix.outputs[2], mx2.inputs[6]); mx2.inputs[7].default_value = srgb(dark)
    bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.25; L(mr.outputs["Result"], bm.inputs["Height"]); L(bm.outputs["Normal"], b.inputs["Normal"])
    L(mx2.outputs[2], b.inputs["Base Color"]); L(b.outputs["BSDF"], o.inputs["Surface"]); return m

def dirt_mat(name="path", base=((156, 98, 38), (204, 140, 66)), speck=(96, 60, 24), streak=(226, 168, 98), speck_amt=0.75, streak_amt=0.6, mask=None, other=None):
    """packed earth like the original's ground (rooms 592 / 424): ochre base in large soft patches, fine dark speckles (grit), light streaks running
    diagonally (drag marks seen in the picture), a little bump.  Object coordinates, 1 unit = 1 game pixel."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.inputs["Roughness"].default_value = 0.95
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.03; n1.inputs["Detail"].default_value = 4.0; L(tc.outputs["Object"], n1.inputs["Vector"])
    r1 = nt.nodes.new("ShaderNodeValToRGB"); r1.color_ramp.elements[0].position = 0.3; r1.color_ramp.elements[1].position = 0.7
    r1.color_ramp.elements[0].color = srgb(base[0]); r1.color_ramp.elements[1].color = srgb(base[1]); L(n1.outputs["Fac"], r1.inputs["Fac"])
    # streaks: stretched noise along the screen diagonal (game x - y)
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, math.radians(45)); mp.inputs["Scale"].default_value = (0.06, 0.6, 1.0); L(tc.outputs["Object"], mp.inputs["Vector"])
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 1.0; n2.inputs["Detail"].default_value = 3.0; L(mp.outputs["Vector"], n2.inputs["Vector"])
    s2 = nt.nodes.new("ShaderNodeMapRange"); s2.inputs["From Min"].default_value = 0.58; s2.inputs["From Max"].default_value = 0.72; L(n2.outputs["Fac"], s2.inputs["Value"])
    f2 = nt.nodes.new("ShaderNodeMath"); f2.operation = "MULTIPLY"; f2.inputs[1].default_value = streak_amt; L(s2.outputs["Result"], f2.inputs[0])
    m2 = nt.nodes.new("ShaderNodeMix"); m2.data_type = "RGBA"; L(f2.outputs[0], m2.inputs["Factor"]); L(r1.outputs["Color"], m2.inputs[6]); m2.inputs[7].default_value = srgb(streak)
    # grit: fine dark speckles
    n3 = nt.nodes.new("ShaderNodeTexNoise"); n3.inputs["Scale"].default_value = 1.1; n3.inputs["Detail"].default_value = 1.0; L(tc.outputs["Object"], n3.inputs["Vector"])
    s3 = nt.nodes.new("ShaderNodeMapRange"); s3.inputs["From Min"].default_value = 0.56; s3.inputs["From Max"].default_value = 0.62; L(n3.outputs["Fac"], s3.inputs["Value"])
    f3 = nt.nodes.new("ShaderNodeMath"); f3.operation = "MULTIPLY"; f3.inputs[1].default_value = speck_amt; L(s3.outputs["Result"], f3.inputs[0])
    m3 = nt.nodes.new("ShaderNodeMix"); m3.data_type = "RGBA"; L(f3.outputs[0], m3.inputs["Factor"]); L(m2.outputs[2], m3.inputs[6]); m3.inputs[7].default_value = srgb(speck)
    bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.25; ad = nt.nodes.new("ShaderNodeMath"); ad.operation = "ADD"
    L(n3.outputs["Fac"], ad.inputs[0]); L(n1.outputs["Fac"], ad.inputs[1]); L(ad.outputs[0], bm.inputs["Height"]); L(bm.outputs["Normal"], b.inputs["Normal"])
    col = m3.outputs[2]
    if mask:                                                                     # blend into another ground (other = (c1, c2)) by a colour attribute (1 = dirt)
        at = nt.nodes.new("ShaderNodeVertexColor"); at.layer_name = mask
        n4 = nt.nodes.new("ShaderNodeTexNoise"); n4.inputs["Scale"].default_value = 0.08; n4.inputs["Detail"].default_value = 6.0; L(tc.outputs["Object"], n4.inputs["Vector"])
        r4 = nt.nodes.new("ShaderNodeValToRGB"); r4.color_ramp.elements[0].color = srgb(other[0]); r4.color_ramp.elements[1].color = srgb(other[1]); L(n4.outputs["Fac"], r4.inputs["Fac"])
        sep = nt.nodes.new("ShaderNodeSeparateColor"); L(at.outputs["Color"], sep.inputs["Color"])
        mk = nt.nodes.new("ShaderNodeMix"); mk.data_type = "RGBA"; L(sep.outputs[0], mk.inputs["Factor"]); L(r4.outputs["Color"], mk.inputs[6]); L(col, mk.inputs[7]); col = mk.outputs[2]
    L(col, b.inputs["Base Color"]); L(b.outputs["BSDF"], o.inputs["Surface"]); return m

def get(name):
    if name in bpy.data.materials: return bpy.data.materials[name]
    return pmat(name, **LIB[name][1])

def modern_look(sc, agx=True):
    """the C light on a scene made by blx.game_view: warm low sun with soft shadows, sky fill, AgX colours."""
    import mathutils
    if agx:
        sc.view_settings.view_transform = "AgX"
        try: sc.view_settings.look = "AgX - Medium High Contrast"
        except Exception: pass
    sun = bpy.data.objects["sun"]; sun.data.energy = 4.5; sun.data.color = (1.0, 0.86, 0.68); sun.data.angle = math.radians(6)
    sun.rotation_euler = (-mathutils.Vector((-0.55, -0.6, 0.55))).to_track_quat("-Z", "Y").to_euler()
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.7, 1.0, 1); sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    if hasattr(sc.eevee, "use_raytracing"): sc.eevee.use_raytracing = True
