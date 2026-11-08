"""LIGHT PROXY: the arcade (three piers with stepped corbel brackets) in room 486 (landstalker/docs/LIGHT_PROXY_PLAN.md 'NEXT BIG STEP' part 2, user 2026-11-08:
'koennen wir dann auch die grosse Bruecke mit den Boegen jetzt so machen?'). An invisible shape for the lighting only, in GAME coordinates (x east, y south,
z up, one map cell = 16), precise enough to carry a remake model later.
The height map has the wall as cells x 43..44 (x 688..720) at 240 with two 3 cell passages at the floor (rows 37..39 = y 592..640, rows 52..54 = y 832..880):
the drawn arches. Until now the light filled those gaps to the wall top (lk_lt_archfill): no light through the arches. Here: the piers are solid, above each
opening the wall is a SLAB whose underside follows the arch (op 'mesh' + "air"), so light and shadow pass under it.
Measured on the original picture (remake/tools/rom_picture.py ROM 486 640 150 900 760, proxy_overlay.py): see SPRING / RISE below.
Run: python3 remake/tools/build_asset.py proxy_arcade_486
Output: landstalker/data/proxies/arcade_486.obj (our own geometry, committed); preview in ~/.landstalker_remake/assets/proxy_arcade_486/ (local)."""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy

X0, X1, TOP = 688, 720, 240       # the arcade wall (cells 43..44) and its top
# MEASURED underside of the wall per 4 unit slice (y of the slice start, z of the lowest drawn layer A pixel on the +x face x 720; user 2026-11-08: 'ungefaehr reicht
# nicht'): the arcade is THREE piers with stepped corbel brackets, open to the top between them (None = no wall: the passages); 0 = the pier stands on the ground;
# single values below 40 between two bracket values were the +y faces of the steps (replaced by the lower neighbour). v2 (user 2026-11-08: 'der gesamte Part links unten geht
# zu weit'): on the +y side of the back / middle piece the scan counts only +x face pixels (dark olive / green; the +y faces are light tan + white joints) and the
# steps rise monotonically towards the gap. v3 (user: 'steht dort immer noch zu weit vor'): the pier FEET measured on their +y end faces (light run left of the
# dark +x face, rows of layerA.png): middle foot +x face y 719..735 (was 724..740), front pier +y face one straight column at y ~ 992 (was 1024). Scanned by a local helper over remake/tools/rom_picture.py layerA.png.
PROFILE = [(484, 0), (488, 0), (492, 0), (496, 0), (500, 48), (504, 51), (508, 51), (512, 51), (516, 64), (520, 67), (524, 67), (528, 67), (532, 67), (536, 130), (540, 135), (544, 135), (548, 135), (552, 178), (556, 183), (560, 183), (564, 183), (568, 210), (572, 215), (576, 218), (580, 224), (584, 225), (588, 225), (592, 225), (596, 228), (600, 232), (604, 235), (608, 240), (612, None), (616, None), (620, None), (624, None), (628, None), (632, None), (636, None), (640, None), (644, 223), (648, 221), (652, 218), (656, 209), (660, 207), (664, 205), (668, 202), (672, 193), (676, 175), (680, 173), (684, 170), (688, 161), (692, 127), (696, 125), (700, 122), (704, 113), (708, 63), (712, 61), (716, 58), (720, 0), (724, 0), (728, 0), (732, 0), (736, 48), (740, 48), (744, 51), (748, 51), (752, 51), (756, 64), (760, 67), (764, 67), (768, 67), (772, 128), (776, 130), (780, 135), (784, 135), (788, 176), (792, 178), (796, 183), (800, 183), (804, 208), (808, 210), (812, 215), (816, 218), (820, 224), (824, 225), (828, 225), (832, 225), (836, 228), (840, 232), (844, 235), (848, 240), (852, None), (856, None), (860, None), (864, None), (868, None), (872, None), (876, None), (880, None), (884, 223), (888, 221), (892, 218), (896, 209), (900, 207), (904, 205), (908, 202), (912, 193), (916, 175), (920, 173), (924, 170), (928, 161), (932, 127), (936, 125), (940, 122), (944, 113), (948, 111), (952, 109), (956, 106), (960, 97), (964, 63), (968, 61), (972, 58), (976, 49), (980, 0), (984, 0), (988, 0), (992, 224), (996, 224), (1000, 224), (1004, 224), (1008, 224), (1012, 224), (1016, 224), (1020, 224)]

GAPS = [(592, 640), (832, 880)]   # the passages of the height map (rows 37..39, 52..54) = where the piers end: the scan saw the drawn +y END FACE of a pier
#   (it faces the camera) as wall for the last 16 units before a gap (user 2026-11-08: 'sind die Mitte und rechts nicht zu breit?')
parts = []
for (y, b) in PROFILE:
    if b is None or any(g0 <= y < g1 for g0, g1 in GAPS): continue
    parts.append(("s%04d" % y, X0, y, X1, y + 4, b, TOP, TOP, "flat", None))   # b 0 = pier (solid, the light's ground there is 0 by data), else a bracket slab b..240
proxy.build("arcade_486", parts, "arcade of room 486: three piers with stepped corbel brackets (op mesh + air)", target=(704, 750, 120), ground_z=0, px_per_unit=1.5)
