"""LIGHT PROXY: the big tree of room 488 (ROUTE_AFTER_DESTEL_2; landstalker/docs/LIGHT_PROXY_PLAN.md 'Forests', user 2026-11-04: 'der Schatten soll nach dem Baum
oder Busch aussehen und nicht wie ein Block'). An invisible shape for the lighting only (never drawn). Why: the automatic proposal made a box with a hip roof
(cells 34..36 x 39..41, z 176 .. 271) out of the big tree in front of the forest: 65 too high and square.
Measured on the original picture (remake/tools/rom_picture.py ROM 488 900 320 320 200, layer A silhouette per picture row around the axis U 1104):
the tree stands on the walkable cells 34..37 x 39..42 (axis x 576, y 656, ground 128); a circle of radius r at height z is widest at V = 616 - z with
half width r * sqrt(2), so the drawn half widths 3 / 10 / 28 / 40 / 52 / 61 / 47 at V 412 / 420 / 432 / 444 / 456 / 464..480 / 488 give the profile below
(bushy down to the ground, widest 43 at z 134..152, tip 212 (checked with remake/tools/proxy_overlay.py)).
Run: python3 remake/tools/build_asset.py proxy_tree_488
Output: landstalker/data/proxies/tree_488.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_tree_488/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

PROFILE = [(128, 32), (134, 43), (152, 43), (160, 36), (172, 28), (184, 20), (198, 8), (212, 0)]
proxy.build("tree_488", proxy.lathe("big_tree", 576, 656, PROFILE), "Big tree in front of the forest, room 488",
            {"big_tree_%d" % k: (60, 150, 70) for k in range(8)}, target=(576, 656, 160), ground_z=128, px_per_unit=3, size=(600, 600))
