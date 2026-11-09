"""LIGHT PROXY: the big tree of room 488 (ROUTE_AFTER_DESTEL_2; landstalker/docs/LIGHT_PROXY_PLAN.md 'Bush blocks and trees', user 2026-11-04: 'der Schatten soll nach dem Baum
oder Busch aussehen und nicht wie ein Block'). An invisible shape for the lighting only (never drawn). Why: the automatic proposal made a box with a hip roof
(cells 34..36 x 39..41, z 176 .. 271) out of the big tree in front of the bush block: 65 too high and square.
RE-MEASURED 2026-11-09 (HANDOFF 0a356): the profile lives in remake/lib/trees.py (BIG_TREE_488), shared with the remake (one round tree,
reusable from every camera quarter); fitted to all 27 drawn crown rows (the 2026-11-04 profile read the widths at the ring centres only and
hung 22 lower in front); trunk + flat crown underside, roots drawn below it.
Run: python3 remake/tools/build_asset.py proxy_tree_488
Output: landstalker/data/proxies/tree_488.obj (GAME coordinates; our own geometry, committed), preview in ~/.landstalker_remake/assets/proxy_tree_488/ (local)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

import trees
proxy.build("tree_488", [trees.round_tree("big_tree", 576, 656, 128, trees.BIG_TREE_488)], "Big tree in front of the forest, room 488",
            {"big_tree": (60, 150, 70)}, target=(576, 656, 160), ground_z=128, px_per_unit=3, size=(600, 600))
