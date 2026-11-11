#!/usr/bin/env python3
"""bed.py OUT.obj [params.json] - the BED of the Mercator / Ryuma houses (tileset 2) as our own parts model (pure Python), for the light and the remake.
Reference: room 623 cells x 23..25, y 23..24 (3 x 2 cells, collision 1 step), head at the west wall; fitted to the drawn pixels (README.md).
Shape in cell-box coordinates (u along the bed from the head wall, w across, z up from the floor), all from the fit:
  frame  = a board on four square legs under the whole bed, the head end free (one pillow lies on it);
  cover  = the blanket over the foot part: a thick rounded slab whose sides hang down to the hem (z HEM) on the foot end and both long sides.
params: x0, y0 (game units: the cell box corner at the head wall, min x / min y), floor (units), orient "x" (head at the west wall, the bed runs
east, 3 x 2 cells) or "y" (head at the north wall, runs south, 2 x 3 cells = the same bed mirrored at the diagonal), umin / wmin (walls at the head end /
along the back: the model slides along the view ray out of them), wmax (clip on the open side),
tilt (units; the LIGHT variant: the drawing shows the top raised towards the back wall, 0 at the open side, tilt at the back, scaled
down to 0 at the floor; the remake model = 0 = level). Groups 'wood' / 'cloth' (for chk_cls.py). GAME coordinates x east, y south, z up."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib"))
from furniture import rbox

L, W = 48.0, 32.0          # the cell box: 3 cells long, 2 wide
B = dict(   # fitted 2026-11-11 on 623 with tilt 3 (chk_cls.py; README.md); frame bottom / legs set by eye (the fit fills the black under the board)
    frame=(1.5, 47.0, 0.5, 32.0, 10.0, 14.0, 1.0),    # u0 u1 w0 w1 z0 z1 r  (board; front face 4 high as drawn)
    leg=2.5,                                          # square legs at the board's corners, floor .. board
    cover=(13.0, 51.5, 0.5, 35.5, 3.5, 16.0, 3.0),    # the blanket: u from the pillow end to 4.5 past the foot, w 3.5 past the open side, hem z 3.5, top 16
    pillow=(3.0, 12.0, 7.0, 31.0, 14.0, 19.0, 2.5),   # ONE pillow across the head end, on the board (user 2026-11-11: 'nur 1 Kissen'; the brown
)                                                     # patch at its open-side end is its shaded end, not a second cushion)

def parts(P):
    out = []
    f = B["frame"]; out.append(("wood", f))
    lg = B["leg"]
    for u in (f[0], f[1] - lg):
        for w in (f[2], f[3] - lg): out.append(("wood", (u, u + lg, w, w + lg, 0.0, f[4] + 0.5, 0.6)))
    out += [("cloth", B["cover"]), ("cloth", B["pillow"])]
    return out

def main():
    P = dict(x0=368.0, y0=368.0, floor=0.0, orient="x")
    if len(sys.argv) > 2: P.update(json.load(open(sys.argv[2])))
    wmin, wmax = P.get("wmin", -1e9), P.get("wmax", 1e9)
    umin = P.get("umin", -1e9)   # walls at the head end (u < umin) / along the back (w < wmin): vertices there SLIDE ALONG THE VIEW RAY (1, 1, 1) out of
    s = "# bed (remake/recipes/bed/bed.py), %s. GAME coordinates x east, y south, z up, world units.\n" % json.dumps(P)
    nv = 0
    for g, (u0, u1, w0, w1, z0, z1, r) in parts(P):
        V, F = rbox(u0, u1, w0, w1, z0, z1, r, n=P.get("n", 3), flat_bottom=(z0 <= 0.0))   # the wall (same game picture, as knight.py)
        s += "g %s\n" % g
        for (u, w, z) in V:
            z += P.get("tilt", 0.0) * max(0.0, min(1.0, (W - w) / W)) * min(z, 16.0) / 16.0   # light variant: the top drawn tilted up towards the back
            d = max(umin - u, wmin - w, 0.0); u, w, z = u + d, w + d, z + d
            w = min(w, wmax)
            x, y = (u, w) if P["orient"] == "x" else (w, u)
            s += "v %.3f %.3f %.3f\n" % (P["x0"] + x, P["y0"] + y, P["floor"] + z)
        for q in F:
            q = q if P["orient"] == "x" else tuple(reversed(q))   # the diagonal mirror flips the winding
            s += "f " + " ".join(str(nv + i + 1) for i in q) + "\n"
        nv += len(V)
    open(sys.argv[1], "w").write(s)

if __name__ == "__main__":
    main()
