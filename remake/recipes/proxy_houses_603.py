"""LIGHT SHAPES (= near-final geometry, the AS-DRAWN variant): the LOG HOUSES of GUMI, rooms 601 / 602 / 603 (one map, tileset 7 = the Massan house
type; HANDOFF -240 'then Gumi / Destel house types', 2026-11-20). Ground 96 (height map 6). Every house was compared pixel by pixel with the Massan
houses of remake/recipes/proxy_houses_592.py (same wall tiles): where the drawing is the same tile set, the Massan measurement is reused, shifted:
  T (cells 39..43 x 30..33, tall)  = Massan G + (256, 256, 64): E wall 89 % identical (rest = the cloth, knot holes); NO cloth here, the small upper
                                     window is open (dark z 183..194 = G's opening 89.5..100 above the ground)
  S (41..45 x 42..48, south house) = Massan B + (112, 208, 96): S wall 99.7 % identical, E wall differs only where bushes stand in front
  W (25..29 x 48..52, skull sign)  = Massan A + (112, 336, 96) (A re-measured the same day), plus one more E post (A coords 490.5)
  P (25..29 x 30..34)  measured: S door 414..430, G's cloth tile 48 lower on the S wall (drawn x 441..461, top z 138) over a small window under the eave,
                       posts S 410.5 / 433.5 / 442.5 / 465.5, E 545.5, one stick crossing in the middle
  Q (31..35 x 30..34)  measured: S door 510..526, Massan D's top-hinged shutter tile at x 541..552, posts S 506.5 / 529.5, E 545.5, centre sticks, vent
                       hood (cap top centre drawn at U 1174.4 V 372.5 -> 533.5 / 543)
Rules as in 592: flush mitred corners, back eaves 3 in (back_in), measuring rule post = dark edge + 4.5, door = dark span +- 1.
Run: python3 remake/tools/build_asset.py proxy_houses_603  ->  landstalker/data/proxies/house_603_{p,q,t,s,w}.obj"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
import blx, massan_a as H, log_house as L
blx.PIXEL = False
PROX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "data", "proxies")

def export(ob, name, title, off=(0.0, 0.0, 0.0)):
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.transform(ob.matrix_world); bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)
    bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.verts.index_update()
    path = os.path.join(PROX, name + ".obj")
    with open(path, "w") as fo:
        fo.write("# light proxy: %s (remake/recipes/proxy_houses_603.py). GAME coordinates x east, y south, z up, world units.\n" % title)
        fo.write("# our own geometry measured on the original picture; read by landstalker/tools/patch_lights.py via data/light_proxies.json (op 'mesh').\n")
        for v in bm.verts: fo.write("v %g %g %g\n" % (round(v.co.x + off[0], 2), round(-v.co.y + off[1], 2), round(v.co.z + off[2], 2)))
        for f in bm.faces: fo.write("f " + " ".join(str(v.index + 1) for v in reversed(f.verts)) + "\n")
    print("proxy_houses_603: %s: %d vertices, %d triangles -> %s" % (name, len(bm.verts), len(bm.faces), path))

mats = [blx.flat_material(n, (150, 150, 150)) for n in ("bark", "post", "endgrain", "dark", "hole", "thatch", "under", "plank")]
Z = 96
HOUSES = {
    "p": dict(planes=(403, 477, 483, 557), z0=Z, back_in=3.0, corners="mitre", doors=[("S", 414, 430, 35)],
              openings=[("S", 446, 462, 41.5, 49)],                             # G's window tile (opening = drawn cloth start + 5 .. end + 1), cut by the eave
              cloths=[("S", 442.2, 462.2, 42, 24.8, 20.3, 0.8, 1.6)],          # G's cloth 48 lower (drawn top z 138, sides ~120, middle ~116; + out / 2)
              posts={"S": [410.5, 433.5, 442.5, 465.5], "E": [545.5]}, ridge="sticks", stick_r=2.6),
    "q": dict(planes=(499, 573, 483, 557), z0=Z, back_in=3.0, corners="mitre", doors=[("S", 510, 526, 35)],
              shutters=[("S", 541, 552, 22, 38, 6)],                            # D's shutter tile: hinge drawn x 541..551 at z ~134, lower edge 535..546 at ~115
              posts={"S": [506.5, 529.5], "E": [545.5]}, ridge="sticks", stick_r=2.6, vents=[(533.5, 543)]),
    "t": dict(planes=(627, 701, 483, 541), z0=Z, ze=114, zt=141, back_in=3.0, corners="mitre", doors=[("E", 510, 526, 35)],
              openings=[("E", 510, 526, 89.5, 100)], boards=[("E", 509, 525, 44, 60.5)],
              windows=[("S", 656.5, 59), ("S", 656.5, 91)], posts={"E": [506.5, 529.5], "S": [634.5, 682.5]},
              ridge="sticks_ends", sticks_shift=(3.5, -4.25), stick_r=2.6),
    "s": dict(planes=(659, 733, 675, 781), z0=Z, back_in=3.0, corners="mitre", doors=[("S", 702, 718, 35)],
              windows=[("E", 738, 28)], shutters=[("S", 669, 681, 24, 38, 3)],
              posts={"S": [698.5, 721.5], "N": [668, 675, 717, 724], "E": [684, 691, 765, 772], "W": [684, 691]},
              noext=[("W", 1)], ext={("S", 0): 1.5}, ridge="bundle", vents=[(718, 743), (720, 710)]),
}
TITLES = {"p": "house P (blue cloth)", "q": "house Q (shutter, vent)", "t": "tall house T", "s": "south house S"}
for k, h in HOUSES.items():
    M = blx.Mesh("house_603_" + k, mats); M.density = 1.0
    L.build(M, h)
    export(M.finish(), "house_603_" + k, "Gumi log %s, rooms 601 / 602 / 603" % TITLES[k])

# W = Massan A (built by massan_a at A's own place, moved on export), with A's re-measured posts / door + the extra E post 490.5 Gumi draws
H.POSTS = dict(H.POSTS, S=[298.5, 305.5, 346.5, 353.5], N=[298.5, 305.5, 346.5, 353.5], E=[442.5, 449.5, 458.5, 481.5, 490.5, 497.5], W=[442.5, 449.5, 489.5, 496.5])
H.DOOR = dict(H.DOOR, a0=462.0, a1=478.0)
M = blx.Mesh("house_603_w", mats); M.density = 1.0
H.build(M, nseg=8, den=1.0, roof_jitter=0.0, hx=H.HX, lip=3.5, door="open", ridge_knot=False, log_over_door=True, mitre=True, back_in=3.0)
export(M.finish(), "house_603_w", "Gumi log house W (skull sign = Massan A), rooms 601 / 602 / 603", off=(112.0, 336.0, 96.0))
