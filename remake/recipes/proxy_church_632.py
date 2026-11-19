"""LIGHT PROXY: Mercator church complex, room 632 (landstalker/docs/LIGHT_PROXY_PLAN.md, user 2026-11-04: 'blender').
An invisible shape for the lighting only (never drawn): church hall with a hip roof, the yellow house in front of it, the entrance gable.
Measured on the original picture of room 632 (projection U = x - y + 1184, V = (x + y) / 2 - z; map cells 15..23 x 50..61 = object 8).
Run: python3 remake/tools/build_asset.py proxy_church_632
Output: landstalker/data/proxies/church_632.obj (GAME coordinates: x east, y south, z up, world units; our own geometry, committed)
        ~/.landstalker_remake/assets/proxy_church_632/preview.png (game camera, local only)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

# parts in game coordinates: (name, x0, y0, x1, y1, z0, eave, ridge, roof, ridge axis), see remake/lib/proxy.py
# RE-MEASURED 2026-11-09 (remake/tools/fit_foot.py + the grey roof terraces / gable profile on the drawn picture; HANDOFF 0a349):
#   hall: front wall foot y 922 (59 of 59 columns), +x wall x 378 (front and back), back corner y 797, eave = wall top under the roof 60,
#         flat grey terrace corners -> 45 deg hip up to 107.5 (inset 47.25 on all four sides: x 238 from the symmetric inset);
#   house: front y 992, left x 240, right x 319, eave 64; terrace corners -> top 79.5, 17 in on every side (-> back y 928);
#   porch (cross gable, entrance in its +x gable wall): gable wall foot x 394.5, front y 890, gable profile 45 deg from eave 60 to
#         the apex under the cross (y 856.5, z 93.5) -> y 823..890; it runs into the hall roof (x0 inside the hall).
# RE-MEASURED 2026-11-20 (user marks: 'das Schraegdach oben nicht ganz richtig' + the hall's right edge): the porch gable's drawn roof edge per
#   picture column on the front plane x 394.5: left slope z = 60 + (890 - y), right slope z = y - 770 (45 deg both) -> apex y 860 z 90 (was 856.5 / 93.5),
#   right eave corner y 830 (was 823); the hall's +x wall foot line (gold strip) and its olive right edge at U 767.5 -> back corner y 794.5 (was 797).
PARTS = [
    ("hall",   238, 794.5, 378, 922, 16, 60, 107.5, "hip", None),
    # the yellow house in front (x 240..320, y 928..992) is its OWN building (user 2026-11-20): town house 9 in proxy_houses_632.py
    # the two CROSS WINGS beside the porch (user 2026-11-20: 'die anderen zwei Giebel im Dach'): gable end walls on the hall's +x wall x 378
    # (the olive walls with the round arched windows), roof edge per picture column: left 45 deg from z 58 at y 922 to the apex y 907.5 z 72.5
    # down to y 893; right from z 56 at y 795 to the apex y 811 z 72 down to y 827; ridges along x run into the hall's hip roof
    ("wing_l", 340, 893, 378, 922, 16, 58, 72.5, "gable", "x"),
    ("wing_r", 340, 795, 378, 827, 16, 56, 72, "gable", "x"),
]
# OPEN ENTRANCE (user 2026-11-20: 'der Kircheneingang hat keine Tuere, sondern ist ein offener Eingang hinein ... das muesste man ausgeschnitten
# noch in der Form haben'; 'im Original eckig und nicht rund'): the front 12.5 units of the porch (x 382..394.5) are a wall slice with a
# RECTANGULAR opening, measured on the porch front plane x 394.5 (picture pixels mapped to (y, z)): the pilasters end at y 841 / start at
# y 878 -> jambs y 842 and 877; the lintel's underside = the dark line at z 58 over the doorway; behind it the drawn dark doorway at x 382
# (the recess back = the porch body's front face); floor = ground 16 (walkable cells 24 x 53..54).
J0, J1, LINTEL = 842.0, 877.0, 58.0
def porch_front():
    # one CORNER BLOCK in each top corner of the opening (user 2026-11-20: 'diese zwei zusaetzlich eingezeichneten Steinecken am Eingang' ...
    # 'es ist genau ein Eck'): the user's marks on the front plane x 394.5: left block y 866..877, right block y 842..853, underside z ~50,
    # up to the lintel z 58 (taken symmetric: 11 wide, underside 50); a plain rectangular corner each, through the slice
    CW, CZ = 11.0, 50.0
    left = [(J0, CZ), (J0 + CW, CZ), (J0 + CW, LINTEL)]; right = [(J1 - CW, LINTEL), (J1 - CW, CZ), (J1, CZ)]
    # the right pier stands 4 out beyond the measured eave y 830 (user: 'die eine Saeule ist ein bisschen weiter rechts raus', outline y 826);
    # no extra corner (user: 'das Dach muss so anschliessen, dass da kein extra Eck rechts im Pfeiler ist'): the right roof slope runs on at
    # its measured 45 deg down to the pier edge y 826 (eave z 56 there), so the porch is one gable y 826..890
    prof = [(826, 16), (J0, 16)] + left + right + [(J1, 16)] + OUTER
    return proxy.extrude_x_solid("porch_front", 382, 394.5, prof)
OUTER = [(890, 16), (890, 60), (860, 90), (826, 56)]   # porch gable outline from the left foot over the apex to the right eave
PARTS.append(proxy.extrude_x_solid("porch", 340, 382, [(826, 16)] + OUTER))   # the porch body (runs into the hall roof), same outline
PARTS.append(porch_front())

proxy.build("church_632", PARTS, "Mercator church complex, room 632", {"hall": (200, 200, 205), "porch": (150, 210, 150), "porch_front": (150, 210, 150), "wing_l": (200, 200, 205), "wing_r": (200, 200, 205)}, target=(312, 896, 60))
