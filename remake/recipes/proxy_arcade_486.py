"""LIGHT PROXY: the arcade (three piers with stepped corbel brackets) in room 486 (landstalker/docs/LIGHT_PROXY_PLAN.md 'NEXT BIG STEP' part 2, user 2026-11-08:
'koennen wir dann auch die grosse Bruecke mit den Boegen jetzt so machen?'). An invisible shape for the lighting only, in GAME coordinates (x east, y south,
z up, one map cell = 16), precise enough to carry a remake model later.
The height map has the wall as cells x 43..44 (x 688..720) at 240 with two 3 cell passages at the floor (rows 37..39 = y 592..640, rows 52..54 = y 832..880):
the drawn arches. Until now the light filled those gaps to the wall top (lk_lt_archfill): no light through the arches. Here: the piers are solid, above each
opening the wall is a SLAB whose underside follows the arch (op 'mesh' + "air"), so light and shadow pass under it.
Measured on the original picture (remake/tools/rom_picture.py ROM 486 640 150 900 760, proxy_overlay.py): see SPRING / RISE below.
v2 2026-11-18 (user rule: light shapes = near-final 3D models, never boxes): the same measured PROFILE / GAPS, but each pier is ONE closed solid per run:
  its elevation (y, z) = flat top 240, the measured underside through the slice centres (a sloped line inside a corbel course, a vertical step where
  the underside jumps > 12 = the next course), extruded along x 688..720; the caps are ear-clipped triangles (the game's OBJ reader fans n-gons,
  which breaks non-convex outlines). Before: 4 unit flat slabs (stairs under every course).
Run: python3 remake/tools/build_asset.py proxy_arcade_486
Output: landstalker/data/proxies/arcade_486.obj (our own geometry, committed); preview in ~/.landstalker_remake/assets/proxy_arcade_486/ (local)."""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import proxy, blx

X0, X1, TOP = 688, 720, 240       # the arcade wall (cells 43..44) and its top
# MEASURED underside of the wall per 4 unit slice (y of the slice start, z of the lowest drawn layer A pixel on the +x face x 720; user 2026-11-08: 'ungefaehr reicht
# nicht'): the arcade is THREE piers with stepped corbel brackets, open to the top between them (None = no wall: the passages); 0 = the pier stands on the ground;
# single values below 40 between two bracket values were the +y faces of the steps (replaced by the lower neighbour). v2 (user 2026-11-08: 'der gesamte Part links unten geht
# zu weit'): on the +y side of the back / middle piece the scan counts only +x face pixels (dark olive / green; the +y faces are light tan + white joints) and the
# steps rise monotonically towards the gap. v3 (user: 'steht dort immer noch zu weit vor'): the pier FEET measured on their +y end faces (light run left of the
# dark +x face, rows of layerA.png): middle foot +x face y 719..735 (was 724..740), front pier +y face one straight column at y ~ 992 (was 1024). Scanned by a local helper over remake/tools/rom_picture.py layerA.png.
PROFILE = [(484, 0), (488, 0), (492, 0), (496, 0), (500, 56), (504, 61), (508, 65), (512, 69), (516, 120), (520, 125), (524, 129), (528, 133), (532, 169), (536, 172), (540, 177), (544, 181), (548, 197), (552, 198), (556, 205), (560, 205), (564, 213), (568, 214), (572, 221), (576, 224), (580, 224), (584, 225), (588, 225), (592, None), (596, None), (600, None), (604, None), (608, None), (612, None), (616, None), (620, None), (624, None), (628, None), (632, None), (636, None), (640, None), (644, 223), (648, 221), (652, 218), (656, 209), (660, 207), (664, 205), (668, 202), (672, 193), (676, 175), (680, 173), (684, 170), (688, 161), (692, 127), (696, 125), (700, 122), (704, 113), (708, 63), (712, 61), (716, 58), (720, 0), (724, 0), (728, 0), (732, 0), (736, 48), (740, 56), (744, 61), (748, 65), (752, 69), (756, 120), (760, 125), (764, 129), (768, 133), (772, 168), (776, 172), (780, 177), (784, 181), (788, 196), (792, 198), (796, 205), (800, 205), (804, 212), (808, 214), (812, 221), (816, 224), (820, 224), (824, 225), (828, 225), (832, None), (836, None), (840, None), (844, None), (848, None), (852, None), (856, None), (860, None), (864, None), (868, None), (872, None), (876, None), (880, None), (884, 223), (888, 221), (892, 218), (896, 209), (900, 207), (904, 205), (908, 202), (912, 193), (916, 175), (920, 173), (924, 170), (928, 161), (932, 127), (936, 125), (940, 122), (944, 113), (948, 111), (952, 109), (956, 106), (960, 97), (964, 63), (968, 61), (972, 58), (976, 49), (980, 0), (984, 0), (988, 0), (992, 224), (996, 224), (1000, 224), (1004, 226), (1008, 230), (1012, 234), (1016, None), (1020, None)]

GAPS = [(592, 640), (832, 880)]   # the passages of the height map (rows 37..39, 52..54) = where the piers end: the scan saw the drawn +y END FACE of a pier
#   (it faces the camera) as wall for the last 16 units before a gap (user 2026-11-08: 'sind die Mitte und rechts nicht zu breit?')
def runs():
    """contiguous wall runs [(y, bottom), ...] between the passages / open slices"""
    out, cur = [], []
    for (y, b) in PROFILE:
        if b is None or any(g0 <= y < g1 for g0, g1 in GAPS):
            if cur: out.append(cur); cur = []
            continue
        cur.append((y, b))
    if cur: out.append(cur)
    return out

def outline(run):
    """elevation polygon (y, z) of one run: top left -> top right -> underside back (slice centres, vertical steps between courses)"""
    y0, y1 = run[0][0], run[-1][0] + 4
    under = [(float(y0), float(run[0][1]))]
    for k, (y, b) in enumerate(run):
        if k and abs(b - run[k - 1][1]) > 12: under += [(float(y), float(run[k - 1][1])), (float(y), float(b))]
        if b == 0: under += [(float(y), 0.0), (float(y + 4), 0.0)]
        else: under.append((y + 2.0, float(b)))
    under.append((float(y1), float(run[-1][1])))
    clean = []
    for q in under:
        if not clean or abs(q[0] - clean[-1][0]) > 1e-6 or abs(q[1] - clean[-1][1]) > 1e-6: clean.append(q)
    return [(float(y0), float(TOP)), (float(y1), float(TOP))] + clean[::-1]

def earclip(poly):
    """triangles (index triples, polygon order) of a simple polygon"""
    n = len(poly); idx = list(range(n))
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n)); sgn = 1.0 if area > 0 else -1.0
    cross = lambda a, b, c: ((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) * sgn
    def inside(p, a, b, c): return cross(a, b, p) >= -1e-9 and cross(b, c, p) >= -1e-9 and cross(c, a, p) >= -1e-9
    tris = []; guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if cross(a, b, c) <= 1e-9: continue
            if any(inside(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2)): continue
            tris.append((i0, i1, i2)); idx.pop(k); break
        else: break
    if len(idx) == 3: tris.append(tuple(idx))
    return tris

parts = []
for r, run in enumerate(runs()):
    prof = outline(run)
    ext = proxy.extrude_x("pier%d" % r, X0, X1, prof)   # its side faces; the two n-gon caps are replaced by triangles
    n = len(prof); P = [(v[1], v[2]) for v in ext["verts"][:n]]   # the (possibly reversed) profile extrude_x used
    side = ext["faces"][:n]; tri = earclip(P)
    assert len(tri) == n - 2, "ear clipping failed for run %d" % r
    faces = side + [tuple(t) for t in tri] + [tuple(n + i for i in t[::-1]) for t in tri]
    parts.append({"name": "pier%d" % r, "verts": ext["verts"], "faces": faces})
proxy.build("arcade_486", parts, "arcade of room 486: three piers with stepped corbel brackets, one solid per run (op mesh + air), v2", target=(704, 750, 120), ground_z=0, px_per_unit=1.5)
import bpy   # clay previews of the middle pier (MODELING_LESSONS 1)
sc = bpy.context.scene; out = os.environ.get("R_OUT", "/tmp/proxy_arcade_486"); sc.camera.data.ortho_scale = 340
sc.render.resolution_x, sc.render.resolution_y = 700, 700
for tag, yaw, el in (("game", 0, 30), ("turn_m50", -50, 15), ("turn_p50", 50, 15), ("side", 45, 2)):
    blx.orbit(sc.camera, (704, -740, 120), yaw, el_deg=el, dist=1500); sc.render.filepath = os.path.join(out, "close_%s.png" % tag); bpy.ops.render.render(write_still=True)
