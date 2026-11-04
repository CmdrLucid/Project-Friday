"""LIGHT PROXY: Mercator church complex, room 632 (landstalker/docs/LIGHT_PROXY_PLAN.md, user 2026-11-04: 'blender').
An invisible shape for the lighting only (never drawn): church hall with a hip roof, the yellow house in front of it, the entrance gable.
Measured on the original picture of room 632 (projection U = x - y + 1184, V = (x + y) / 2 - z; map cells 15..23 x 50..61 = object 8).
Run: python3 remake/tools/build_asset.py proxy_church_632
Output: landstalker/data/proxies/church_632.obj (GAME coordinates: x east, y south, z up, world units; our own geometry, committed)
        ~/.landstalker_remake/assets/proxy_church_632/preview.png (game camera, local only)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

# parts in game coordinates: (name, x0, y0, x1, y1, z0, eave, ridge, roof, ridge axis), see remake/lib/proxy.py
PARTS = [
    ("hall",   240, 800, 376, 928, 16, 64, 109, "hip", None),
    ("house",  240, 928, 326, 992, 16, 64, 83, "hip", None),
    ("porch",  340, 833, 400, 895, 16, 64, 94, "gable", "x"),    # runs into the hall roof (valley = the cross gable of the picture); front over the columns (cells x 24)
]

proxy.build("church_632", PARTS, "Mercator church complex, room 632", {"hall": (200, 200, 205), "house": (215, 180, 90), "porch": (150, 210, 150)}, target=(312, 896, 60))
