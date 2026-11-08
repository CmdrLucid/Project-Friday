"""LIGHT PROXY: the ship at the dock, rooms 493 / 494 / 495 / 497 (landstalker/docs/LIGHT_PROXY_PLAN.md 'NEXT BIG STEP', user 2026-11-08:
'mit Blender kannst du die Form des Schiffes doch sicher besser nachmachen als nur in Bauklötzen' + 'mach diese versteckten 3D-Lichtformen schon in der
Genauigkeit, dass wir später echte 3D-Modelle fürs Remake drauf setzen können').
An invisible shape for the lighting only (never drawn), in GAME coordinates (x east, y south, z up, world units, one map cell = 16), so a later remake
model can be placed on exactly this frame. Two OBJs: ship_493.obj (solid hull, decks, rails, mast; op 'mesh' replaces the cell heights indoors) and
ship_493_sail.obj (the sail, op 'mesh' with "air": the light passes under it).
Measured (remake/tools/rom_picture.py ROM 493 860 380 500 440 + the light's heights LANDSTALKER_LT_DUMPFILE):
  decks = the game's walkable heights: stern castle y 528..592 at 32 (rail 64), waist y 592..672 at 0 (bench x 592..608 at 16), step y 672..688 at 16,
          main deck y 688..784 at 32, forecastle y 784..836 at 48; hull width x 576..704 (axis x 640);
  sea level ~ -22: the straight sides stand vertical under the rails (waterline pixels along the +x side give z -22 for x = 704 at U 1140..1230);
  bow: waterline V from (704, 749) to the stem at (642, 804); the stem rakes forward to the figurehead at about (640, 836, 52); both drawn bow rails are straight lines (a V, not a curve);
  sail: x 576..688 just in front of the mast (y ~710), from its lower edge ~56 up to the yard ~232; mast centre (626, 702) (drawn masthead at U 1105).
Run: python3 remake/tools/build_asset.py proxy_ship_493
Output: landstalker/data/proxies/ship_493.obj + ship_493_sail.obj (our own geometry, committed); previews in ~/.landstalker_remake/assets/proxy_ship_493/ (local)."""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

SEA = -22
WL = [(576, 744), (704, 744), (697, 761), (687, 771), (677, 781), (667, 791), (658, 800), (642, 804), (626, 800), (617, 791), (607, 781), (597, 771), (587, 761)]   # waterline of the bow (z = SEA)
D32 = [(576, 744), (704, 744), (704, 784), (694, 791), (683, 799), (672, 807), (661, 814), (640, 829), (619, 814), (608, 807), (597, 799), (586, 791), (576, 784)]   # its outline at the main deck (z = 32): a straight V to the raked stem
FC = [(576, 784), (704, 784), (640, 836)]   # forecastle deck at 48: a straight V from the rail ends to the figurehead (measured: both drawn bow rails are straight lines)

def rail_along(name, pts, w, z0, z1):
    """a rail log as thin boxes along a polyline (outer edge = the points, w units inwards towards the ship's axis)"""
    out = []
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]; dx, dy = bx - ax, by - ay; l = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / l, dx / l
        if (640 - (ax + bx) / 2) * nx + (690 - (ay + by) / 2) * ny < 0: nx, ny = -nx, -ny   # inwards
        out.append({"name": "%s_%d" % (name, i), "poly": [(ax, ay), (bx, by), (bx + nx * w, by + ny * w), (ax + nx * w, ay + ny * w)], "z0": z0, "z1": z1})
    return out

def cyl(name, cx, cy, r, z0, z1, n=12):
    return {"name": name, "poly": [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)], "z0": z0, "z1": z1}

HULL = [
    ("stern", 576, 528, 704, 592, SEA, 32, 32, "flat", None),          # stern castle deck
    ("waist", 576, 592, 704, 672, SEA, 0, 0, "flat", None),            # low waist deck
    ("bench", 592, 592, 608, 672, SEA, 16, 16, "flat", None),          # the bench / steps along the port side of the waist
    ("step", 576, 672, 704, 688, SEA, 16, 16, "flat", None),           # step up to the main deck
    ("main", 576, 688, 704, 744, SEA, 32, 32, "flat", None),           # main deck up to where the bow starts to taper below
    {"name": "bow_low", "poly": WL, "top": D32, "z0": SEA, "z1": 32},  # tapering bow below the main deck, raked stem
    {"name": "forecastle", "poly": FC, "z0": 20, "z1": 48},
    ("rail_stern_b", 576, 528, 704, 540, 32, 64, 64, "flat", None),    # stern castle railing (64 in the height map)
    ("rail_stern_l", 576, 528, 588, 556, 32, 64, 64, "flat", None),   # the upper side rails end with the spiral log about y 556 (user 2026-11-08: 'oben geht es viel zu weit hinaus')
    ("rail_stern_r", 692, 528, 704, 556, 32, 64, 64, "flat", None),
    ("rail_stern_fl", 576, 556, 588, 584, 32, 48, 48, "flat", None),  # below it the front post of the stern castle (48 in the height map)
    ("rail_stern_fr", 692, 556, 704, 584, 32, 48, 48, "flat", None),
    ("rail_waist_l", 576, 584, 588, 784, 0, 44, 44, "flat", None),     # side rail logs (drawn ~12 above the main deck)
    ("rail_waist_r", 692, 584, 704, 784, 0, 44, 44, "flat", None),
    cyl("mast", 626, 702, 6, 32, 248),
]   # the forecastle rail log (deck 48 + ~12) is NOT in the light shape: a thin diagonal rail becomes a stair of 4 unit sub columns with
#   small pockets that the room light shades as vertical stripes; for a remake model: rail_along("rail_bow", [FC[0], FC[2], FC[1]], 10, 48, 60)

SAIL_FRONT = [(576 + 14 * k, 710 + 3.0 * math.sin(math.pi * k / 8)) for k in range(9)]   # the cloth bulges a little towards the bow
SAIL = [{"name": "sail_%d" % k, "poly": [SAIL_FRONT[k], SAIL_FRONT[k + 1], (SAIL_FRONT[k + 1][0], SAIL_FRONT[k + 1][1] - 4), (SAIL_FRONT[k][0], SAIL_FRONT[k][1] - 4)], "z0": 56, "z1": 232} for k in range(8)]   # 4 thick, one convex piece per segment

proxy.build("ship_493", HULL, "ship at the dock, rooms 493..497: hull, decks, rails, mast", target=(640, 690, 40), ground_z=SEA, px_per_unit=2.5)
FIG = [cyl("figurehead", 648, 832, 7, 22, 64)]   # the figurehead stands just starboard of the stem (drawn at U 992..1020): a round body, else the stem ridge cut a hard light edge through it (user 2026-11-08);
#   v2 (user 2026-11-08 'links von der Galionsfigur ist auch noch ein harter Schatten' + background test remake/tools/proxy_bgtest.py): the drawn statue ends at z ~22 (lowest
#   statue pixel V 720 at U ~1005 on the camera side of the body), water is drawn below it; in the solid mesh the body became a column down to the sea = a wall over the drawn
#   water. Now its own OBJ with op 'mesh' + "air" (the statue is drawn in layer A, so the view ray sits on the slab)
proxy.build("ship_493_fig", FIG, "ship at the dock, rooms 493..497: the figurehead (op mesh + air)", target=(648, 832, 40), ground_z=SEA, px_per_unit=4)
proxy.build("ship_493_sail", SAIL, "ship at the dock, rooms 493..497: the sail (op mesh + air)", target=(632, 710, 140), ground_z=SEA, px_per_unit=2.5)
