"""Asset 1: THATCHED HUT (Massan style): log walls, thatch roof with overhang + ridge cap + crossed ridge poles, door, windows, corner posts.
Run: python3 remake/tools/build_asset.py hut   (needs Blender, INDEX 'remake toolchain').  Output: ~/.landstalker_remake/assets/hut/{hut.glb, preview_*.png}
Size: footprint 80 x 64 units (5 x 4 cells), wall 48, ridge +26, overhang 10; ridge along x; door on the south (+y) wall."""
import bpy, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")); import blx
out = os.environ.get("R_OUT", "/tmp/hut")
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
R = blx.pixel_rng(7)
def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
# ---- pixel textures (32 x 32, tileable) --------------------------------------------------------------------------------------------------------
THATCH = [(150, 112, 28), (176, 140, 32), (200, 164, 40), (218, 184, 48), (238, 208, 90)]
def thatch(x, y):
    r = blx.pixel_rng(x * 131 + y * 7919 + 3); streak = blx.pixel_rng(y * 31 + 11).random()      # horizontal straw courses: each row leans to a tone
    base = int(streak * 3.2) + 1; d = r.random()
    k = base + (1 if d > 0.82 else -1 if d < 0.2 else 0) + (1 if (x + y * 3) % 11 == 0 else 0)
    return THATCH[max(0, min(4, k))]
LOGS = [(34, 52, 26), (58, 90, 40), (74, 106, 48), (90, 124, 56)]
def logs(x, y):
    row = y % 8; log = y // 8; r = blx.pixel_rng(x * 17 + y * 101 + log * 7)
    if row == 0 or row == 7: return LOGS[0]                                                    # seams between the logs
    if row == 1: return LOGS[3] if (x + log * 5) % 7 else LOGS[2]                              # light top edge
    if row == 6: return LOGS[1]
    d = r.random(); return LOGS[2] if d > 0.18 else (LOGS[1] if d > 0.07 else LOGS[3])
WOOD = [(60, 40, 22), (104, 70, 36), (122, 84, 44), (144, 100, 52)]
def wood(x, y):
    col = x % 8; r = blx.pixel_rng(x * 53 + (y // 3) * 29)
    if col == 0: return WOOD[0]
    d = r.random(); return WOOD[2] if d > 0.3 else (WOOD[3] if d > 0.08 else WOOD[1])
def dark(x, y): return (26, 20, 14) if (x + y) % 5 else (34, 26, 18)
mats = [blx.material("thatch", blx.px_image("thatch", thatch)), blx.material("logs", blx.px_image("logs", logs)), blx.material("wood", blx.px_image("wood", wood)), blx.material("dark", blx.px_image("dark", dark)),
        blx.flat_material("glass", (22, 30, 46))]
M = blx.Mesh("hut", mats)
import math
# ---- geometry -------------------------------------------------------------------------------------------------------------------------------
W, D, ZT, H, O = 80.0, 64.0, 48.0, 26.0, 10.0
x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2; zr = ZT + H
P = lambda x, y, z: (x, y, z)
M.quad("logs", P(x0, y0, 0), P(x1, y0, 0), P(x1, y0, ZT), P(x0, y0, ZT))             # north wall
M.quad("logs", P(x1, y1, 0), P(x0, y1, 0), P(x0, y1, ZT), P(x1, y1, ZT))             # south wall
M.quad("logs", P(x0, y1, 0), P(x0, y0, 0), P(x0, y0, ZT), P(x0, y1, ZT))             # west wall
M.quad("logs", P(x1, y0, 0), P(x1, y1, 0), P(x1, y1, ZT), P(x1, y0, ZT))             # east wall
M.tri("logs", P(x0, y1, ZT), P(x0, y0, ZT), P(x0, 0, zr - 1)); M.tri("logs", P(x1, y0, ZT), P(x1, y1, ZT), P(x1, 0, zr - 1))     # gables
for cx in (x0, x1):
    for cy in (y0, y1): M.box("wood", cx - 3.2, cx + 3.2, cy - 3.2, cy + 3.2, 0, ZT + 3)                                        # corner posts
# door (south wall, left of the middle) and windows
dx = -16.0
M.box("dark", dx - 7, dx + 7, y1, y1 + 1.2, 0, 27); M.box("wood", dx - 10, dx - 7, y1, y1 + 3, 0, 30); M.box("wood", dx + 7, dx + 10, y1, y1 + 3, 0, 30); M.box("wood", dx - 10, dx + 10, y1, y1 + 3, 27, 30.5)
for wx in (20.0,):
    M.box("wood", wx - 9, wx + 9, y1, y1 + 3, 22, 40); M.box("glass", wx - 7, wx + 7, y1 + 3, y1 + 3.6, 24, 38)
M.box("wood", x1, x1 + 3, -9, 9, 22, 40); M.box("glass", x1 + 3, x1 + 3.6, -7, 7, 24, 38)
# roof: two thatch slabs (thickness 4) with overhang
for s in (-1, 1):
    ye = s * (D / 2 + O); xa, xb = x0 - O, x1 + O
    top_e = (ye, ZT); top_r = (0, zr)                                            # eave line / ridge line (y, z)
    thick = 4.0
    M.quad("thatch", P(xa, ye, ZT), P(xb, ye, ZT), P(xb, 0, zr), P(xa, 0, zr), flip=(s < 0))                                    # upper surface
    M.quad("wood", P(xa, ye, ZT - thick), P(xa, 0, zr - thick), P(xb, 0, zr - thick), P(xb, ye, ZT - thick), flip=(s < 0))      # underside
    M.quad("thatch", P(xa, ye, ZT - thick), P(xb, ye, ZT - thick), P(xb, ye, ZT), P(xa, ye, ZT), flip=(s < 0))                  # eave edge (thick bundle)
    M.quad("thatch", P(xa, ye, ZT), P(xa, ye, ZT - thick), P(xa, 0, zr - thick), P(xa, 0, zr), flip=(s > 0))                    # left edge
    M.quad("thatch", P(xb, ye, ZT - thick), P(xb, ye, ZT), P(xb, 0, zr), P(xb, 0, zr - thick), flip=(s > 0))                    # right edge
M.box("thatch", x0 - O - 2, x1 + O + 2, -4.5, 4.5, zr - 1.5, zr + 4)                                                          # ridge cap
for xe in (x0 - O + 4, x1 + O - 4):                                                                                           # crossed ridge poles
    M.beam("wood", (xe, -9, zr + 16), (xe, 9, zr - 4), 3.0); M.beam("wood", (xe, 9, zr + 16), (xe, -9, zr - 4), 3.0)
M.uv_ridge["thatch"] = (ZT, H / math.hypot(H, D / 2 + O))
ob = M.finish()
# ---- export + previews ---------------------------------------------------------------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); bpy.context.view_layer.objects.active = ob
blx.export_glb(os.path.join(out, "hut.glb")) if False else None
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "hut.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
blx.ground_plane((124, 92, 52), 260)
sc, co = blx.setup_render(os.path.join(out, "preview.png"), (900, 700), yaw_deg=0, dist=500, target=(0, 0, 30), ortho_scale=185)
blx.render_views(sc, co, os.path.join(out, "preview.png"), [0, -50, 50, 180], pitch_deg=35.264, dist=500, target=(0, 0, 30))
print("hut done ->", out)
