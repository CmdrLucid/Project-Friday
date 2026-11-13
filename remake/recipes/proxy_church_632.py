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
PARTS = [
    ("hall",   238, 797, 378, 922, 16, 60, 107.5, "hip", None),
    ("house",  240, 928, 319, 992, 16, 64, 79.5, "hip:17", None),
    ("porch",  340, 823, 394.5, 890, 16, 60, 93.5, "gable", "x"),
]

proxy.build("church_632", PARTS, "Mercator church complex, room 632", {"hall": (200, 200, 205), "house": (215, 180, 90), "porch": (150, 210, 150)}, target=(312, 896, 60))
