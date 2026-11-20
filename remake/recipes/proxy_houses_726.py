"""LIGHT SHAPES (= near-final geometry, the AS-DRAWN variant): the LOG HOUSES of DESTEL, room 726 (HANDOFF -245 / -246 'Destel 726 log houses as their
own variant', 2026-11-20). Same log house idea as Massan / Gumi (remake/lib/log_house.py) with Destel's own details: plain pointed / hip thatch roofs
(no sticks: ridge 'none'), a THICK round post at every corner (the logs end in it), door frames of stacked log stubs (jambs), arched windows, a tilted shutter,
two framed signs, roof windows on the long houses = the flat square Massan roof vents (user 2026-11-20 'flache Dachfenster wie Massan'; the drawn centre cast onto the roof profile = 17..18 in from the eave).
Measured 2026-11-20:
  footprints = the game's collision blocks (3 steps above the ground) inset 3 (the Massan / Gumi rule: walls 3 inside the cell lines);
  eave / top = remake/tools/fit_house.py scene fit of all houses on layer A (FIT_PALETTE=destel, 93.5 %% of the model pixels match): eave 49..51
  above the ground for all, top 77 (B, C, D) / 84 (the long houses A, E);
  doors, windows, shutter, signs, posts = rectified wall pictures (lktest/destel726/wand.py, 4 px per unit): doors 16 / 17 wide, dark up to 35,
  jamb stub columns 7.5 wide beside them (centre 3.75 out); arched windows 11.5 .. 12.5 wide, z 15 .. 42 above the ground (openings + an arch frame: round top, side sticks, sill);
  the thick corner post ~10 wide.
Houses: A long house on the upper terrace (ground 144), B shutter house (112), C1 / C2 joined pair (ground 80, 5 + 4 cells), D1 / D2 joined pair
(80, 5 + 5 cells), E long house by the lower river (16).
Run: python3 remake/tools/build_asset.py proxy_houses_726  ->  landstalker/data/proxies/house_726_{a,b,c1,c2,d1,d2,e,f}.obj"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
import blx, log_house as L
blx.PIXEL = False
PROX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "data", "proxies")

def export(ob, name, title):
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.transform(ob.matrix_world); bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)
    bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.verts.index_update()
    path = os.path.join(PROX, name + ".obj")
    with open(path, "w") as fo:
        fo.write("# light proxy: %s (remake/recipes/proxy_houses_726.py). GAME coordinates x east, y south, z up, world units.\n" % title)
        fo.write("# our own geometry measured on the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        for v in bm.verts: fo.write("v %g %g %g\n" % (round(v.co.x, 2), round(-v.co.y, 2), round(v.co.z, 2)))
        for f in bm.faces: fo.write("f " + " ".join(str(v.index + 1) for v in reversed(f.verts)) + "\n")
    print("proxy_houses_726: %s: %d vertices, %d triangles -> %s" % (name, len(bm.verts), len(bm.faces), path))

mats = [blx.flat_material(n, (150, 150, 150)) for n in ("bark", "post", "endgrain", "dark", "hole", "thatch", "under", "plank")]
COMMON = dict(back_in=3.0, arch_frames=True, corners="post", corner_r=5.5, corner_in=4.0, ridge="none", jambs=3.75, ze=50)   # corners: user 2026-11-20 'die Ecken nicht' -> the corner is a thick round post (drawn ~10 wide; centre on the logs' corner axis 4 inside, r 5.5 so the log ends vanish in it and it stands 1.5 proud of the walls)
WIN = (15, 42)   # arched windows: bottom / arch top above the ground
def wins(side, *spans): return [(side, a0, a1, WIN[0], WIN[1]) for a0, a1 in spans]
HOUSES = {
    "a":  dict(COMMON, planes=(355, 429, 499, 653), z0=144, zt=84, doors=[("S", 383, 399, 35), ("E", 525, 542, 35)],
               openings=wins("E", (558, 571.5), (574, 589), (605, 619), (621, 636.5)), posts={"E": [592]},
               vents=[(415.5, 614.5), (415.9, 567.4), (415.5, 534.5)]),
    "b":  dict(COMMON, planes=(483, 557, 579, 653), z0=112, zt=77, doors=[("E", 605, 622, 35)], shutters=[("S", 503, 520, 18, 40, 5)]),
    "c1": dict(COMMON, planes=(691, 765, 707, 781), z0=80, zt=77, doors=[("E", 733, 750, 35)]),
    "c2": dict(COMMON, planes=(691, 765, 787, 845), z0=80, zt=77, doors=[("E", 797, 813, 35)], openings=wins("S", (702, 713.5), (733.5, 746))),
    "d1": dict(COMMON, planes=(387, 461, 851, 925), z0=80, zt=79, openings=wins("S", (398, 409.5), (429.5, 441))),
    "d2": dict(COMMON, planes=(467, 541, 851, 925), z0=80, zt=79, doors=[("E", 877, 894, 35)], openings=wins("S", (494.5, 506)),
               boards=[("E", 853.5, 867, 16, 32), ("E", 901, 916, 16, 32)]),
    "e":  dict(COMMON, planes=(867, 941, 547, 685), z0=16, zt=84, doors=[("S", 893, 910, 35)],
               openings=wins("E", (558, 569.5), (589.5, 601), (605.5, 617), (637, 648), (653, 664.5)), posts={"E": [575.5, 624.5]},
               vents=[(927.1, 644.8), (927.7, 580.5)]),
}
TITLES = {"a": "long house A (upper terrace)", "b": "shutter house B", "c1": "joined pair C, north house", "c2": "joined pair C, south house",
          "d1": "joined pair D, west house", "d2": "joined pair D, east house (signs)", "e": "long house E (lower river)"}
for k, h in HOUSES.items():
    M = blx.Mesh("house_726_" + k, mats); M.density = 1.0
    L.build(M, h)
    export(M.finish(), "house_726_" + k, "Destel log %s, room 726" % TITLES[k])

# F = the house FRONT built into the cliff (top right, user 2026-11-20 'ja, sollten dazu'): only its south log wall shows, flush in the cliff face
# y = 400 (the height map's cliff row 24 / terrace row 25 boundary), ground 144 (terrace cells x 44..49 y 25..27 at height 9). Measured on the rectified
# wall (walls/F_S.png): logs x 704..785, z 144..196, top beam ~197, stub columns at both ends and beside the door 738..755 (dark up to 37), framed
# sign x 712.5..726 z 16..34.5 above the ground.
def facade(M):
    G = lambda x, y, z: (x, -y, z); Y, Z0, X0, X1 = 400.0, 144.0, 704.0, 785.0; D0, D1 = 738.0, 755.0; R = 4.0
    for k in range(7):
        zc = Z0 + 2.5 + 8 * k
        if zc > Z0 + 52: break
        segs = [(X0 + 3, D0 - 3.75), (D1 + 3.75, X1 - 3)] if zc < Z0 + 37 + 4 else [(X0 + 3, X1 - 3)]
        for a, b in segs: M.cylinder("bark", G(a, Y - 0.5, zc), G(b, Y - 0.5, zc), R * 0.9, n=8, cap="endgrain", density=1.0)
    for ax in (X0 + 3.5, X1 - 3.5, D0 - 3.75, D1 + 3.75):   # stub columns (as the door jambs of the houses)
        top = 196.0 if ax in (X0 + 3.5, X1 - 3.5) else Z0 + 37 + 6
        z = Z0 + 4
        while z < top:
            M.cylinder("post", G(ax, Y - 2.0, z), G(ax, Y + 2.4, z), 3.0, n=8, cap="endgrain", density=1.0); z += 8
    M.cylinder("post", G(X0 - 1, Y + 1.0, 198.0), G(X1 + 1, Y + 1.0, 198.0), 2.8, n=8, cap="endgrain", density=1.0)   # top beam
    M.cylinder("post", G(D0 - 3, Y + 1.2, Z0 + 39.0), G(D1 + 3, Y + 1.2, Z0 + 39.0), 2.7, n=8, cap="endgrain", density=1.0)   # lintel
    M.face("dark", [G(D0, Y - 1.2, Z0), G(D1, Y - 1.2, Z0), G(D1, Y - 1.2, Z0 + 37), G(D0, Y - 1.2, Z0 + 37)][::-1], [(0, 0), (1, 0), (1, 1), (0, 1)])
    M.box("plank", 712.5, 726.0, -(Y + 1.5), -(Y + 0.5), Z0 + 16, Z0 + 34.5)   # framed sign
    M.box("dark", X0, X1, -(Y - 1.0), -(Y - 9.0), Z0, 208.0)   # the core up to the cliff top 208 (closes the logs against the cliff; keeps the cliff columns at their height)

M = blx.Mesh("house_726_f", mats); M.density = 1.0
facade(M)
export(M.finish(), "house_726_f", "Destel house front in the cliff F, room 726")
