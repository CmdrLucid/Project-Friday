"""plants_px.py -- pines and bushes EXACTLY where the original draws them (2026-10-27, user: 'es ist fuer spaeter wichtig, dass die wirklich exakt
stehen wie im Original').  In the original, plants are no objects: they are tiles of plane A (the picture) over blocked cells of the height map
(collision).  So:
  pines   = every place where the pine's tip (top TIP_ROWS rows of the pine template) is found in plane A: exact count and screen position; the depth
            comes from the height map (the cell under the trunk foot whose base matches), else (slopes) from the terrain along the view ray
  bushes  = one card per bush cell of the height map (count and place = the collision), cut from plane A: the pixels inside the screen outline of
            that cell's box (front cells own shared pixels, as the original draws front over back) plus leaves sticking up to OVER px above it;
            pixels of found pines are left out
Screen: U = x - y + 1184, V = (x + y) / 2 - z (FORMATS 'Height map = a real height field'); layerA.png pixel (px, py) = (U - U0, V - V0), window.txt.
The original draws a plant's bottom row at the FRONT corner of its cell (V of the cell centre + 8).
numpy only (Blender has it); image I/O through bpy in load() / save()."""
import numpy as np

TIP_ROWS = 10       # rows of the pine tip that must match (lower rows are often covered by the pines in front)
TIP_MATCH = 0.6     # share of the tip's opaque pixels that must be equal (0.6 still finds the tips peeking over roofs, nothing else in Massan)
OVER = 6            # leaves above a bush cell's box top that still belong to it

def load(path):
    import bpy
    im = bpy.data.images.load(path); w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]           # Blender rows are bottom-up
    bpy.data.images.remove(im)
    return np.round(a * 255).astype(np.int32)

def save(a, path):
    import bpy, os
    h, w = a.shape[:2]
    im = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    im.pixels = (a[::-1].astype(np.float32) / 255).ravel().tolist()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.filepath_raw = path; im.file_format = "PNG"; im.save()
    open(os.path.splitext(path)[0] + ".txt", "w").write("0 0 1\n")
    return path

def find_tips(la, tmpl, rows=TIP_ROWS, match=TIP_MATCH):
    """top-left corners (px, py) in la of every pine whose tip (top `rows` rows) matches the template (both RGBA int arrays) by more than `match`."""
    T = tmpl[:rows]; M = T[:, :, 3] > 0; th, tw = T.shape[:2]; H, W = la.shape[:2]
    ys, xs = np.nonzero(M); cols = T[ys, xs, :3]
    score = np.zeros((H - th, W - tw))
    for (y, x), c in zip(zip(ys, xs), cols):
        win = la[y:H - th + y, x:W - tw + x]
        score += (win[:, :, 3] > 0) & (np.abs(win[:, :, :3] - c).sum(2) == 0)
    score /= len(ys)
    hits = []
    for py, px in sorted(zip(*np.nonzero(score > match)), key=lambda p: -score[p]):
        if all(abs(px - qx) > 2 or abs(py - qy) > 2 for qx, qy in hits): hits.append((int(px), int(py)))    # the template is symmetric: +-1 px twins
    return sorted(hits, key=lambda p: (p[1], p[0]))

def pine_mask(la, tmpl, hits):
    """pixels of la that belong to the found pines (template opaque there and the colour equal)."""
    m = np.zeros(la.shape[:2], bool); th, tw = tmpl.shape[:2]; H, W = m.shape
    for px, py in hits:
        h_, w_ = min(th, H - py), min(tw, W - px)
        t = tmpl[:h_, :w_]; win = la[py:py + h_, px:px + w_]
        m[py:py + h_, px:px + w_] |= (t[:, :, 3] > 0) & (np.abs(win[:, :, :3] - t[:, :, :3]).sum(2) == 0)
    return m

def colour_mask(la, tmpls):
    """pixels of la whose colour occurs in one of the templates (the plants' own colours: keeps straw roof / stone pieces out of the bush cards)."""
    cols = {tuple(c) for t in tmpls for c in t[t[:, :, 3] > 0][:, :3]}
    flat = la[:, :, :3].reshape(-1, 3)
    return np.array([tuple(c) in cols for c in flat.tolist()]).reshape(la.shape[:2])

def cell_cards(la, U0, V0, cells, skip=None):
    """cells = {(x, y): (z_base, z_top)} in world units (x, y = cell centre).  Returns {(x, y): (rgba array, bottom-centre (U, V))}: for every cell
    the plane A pixels inside its box outline (front cells first) + up to OVER px of leaves above it, nothing in skip."""
    H, W = la.shape[:2]; own = np.full((H, W), -1, np.int32); keys = list(cells)
    vv, uu = np.mgrid[0:H, 0:W]; U = uu + U0; V = vv + V0
    opaque = la[:, :, 3] > 0
    if skip is not None: opaque &= ~skip
    def region(k, over):
        (x, y), (zb, zt) = k, cells[k]
        d = np.abs(U - (x - y + 1184)); half = (16 - d) / 2.0; vc = (x + y) / 2.0
        return (d < 16) & (V >= vc - zt - half - over) & (V < vc - zb + half)
    order = sorted(range(len(keys)), key=lambda i: -(keys[i][0] + keys[i][1]))   # front (larger x + y) first
    for over in (0, OVER):
        for i in order:
            own[(own < 0) & opaque & region(keys[i], over)] = i
    out = {}
    for i, k in enumerate(keys):
        m = own == i
        if not m.any(): continue
        (x, y), (zb, zt) = k, cells[k]
        uc = x - y + 1184 - U0; vb = int(round((x + y) / 2.0 + 8 - zb - V0))     # bottom row = the cell's front corner
        top_ = int(np.nonzero(m.any(1))[0].min()); hw = 16
        a = np.zeros((vb - top_ + 1, 2 * hw + 1, 4), np.int32)
        sub = m[top_:vb + 1, uc - hw:uc + hw + 1]; src = la[top_:vb + 1, uc - hw:uc + hw + 1]
        a[:sub.shape[0], :sub.shape[1]][sub] = src[sub]
        out[k] = (a, (uc + U0, vb + V0))
    return out
