"""STYLE C material library (user 2026-10-25: smooth 'toy diorama' look): soft painted procedural materials for Blender (EEVEE), shared by all recipes.
Every material = two colours (sRGB 0..255, from the original's palette ramps) mixed by object-space noise, a light bump, optional extras:
  stretch  longer blotches along an axis (wood grain, straw), streaks = strands along z (thatch), cells = cobbles / bricks with dark seams (Voronoi),
  strata = horizontal rock layers, gloss = water / wet look (low roughness), alpha.
get(name) builds a library material once (LIB below); pmat(...) makes an ad-hoc one.  modern_look(scene) = the C light: warm low sun, AgX colours, soft shadows."""
import math
import bpy

def srgb(c): return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)

def pmat(name, c1, c2, scale=0.15, detail=4.0, bump=0.3, stretch=(1, 1, 1), rough=0.75, streaks=0.0, cells=0.0, seam=(30, 26, 20), strata=0.0, gloss=False, alpha=1.0):
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
    "thatch":   ("straw roof", dict(c1=(176, 126, 30), c2=(240, 200, 90), scale=0.25, stretch=(1, 1, 4), bump=1.0, rough=0.9, streaks=3.0)),
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
    "needles":  ("pine foliage", dict(c1=(16, 72, 36), c2=(56, 126, 48), scale=0.3, stretch=(1, 1, 2), detail=8.0, bump=0.9, rough=0.95)),
    "leaves":   ("hedges, bushes", dict(c1=(36, 104, 28), c2=(98, 150, 40), scale=0.25, detail=8.0, bump=0.9, rough=0.95)),
    "clay":     ("red roof tiles (Mercator)", dict(c1=(156, 68, 40), c2=(204, 104, 62), scale=0.3, bump=0.4, rough=0.8, cells=0.18)),
    "plaster":  ("whitewashed walls (Mercator)", dict(c1=(214, 204, 184), c2=(240, 232, 214), scale=0.08, bump=0.15, rough=0.9)),
}
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
