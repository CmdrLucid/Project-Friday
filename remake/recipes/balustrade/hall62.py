#!/usr/bin/env python3
"""NEAR-FINAL BALUSTRADES of the castle hall, room 62 (also used by 59 / 60 / 61: height map + blocks identical): the gallery rail on the landing and
the two stair rails.  Same parts as balustrade.py (turned ribbed balusters, posts with ball caps, round handrail) on the positions MEASURED for the
first light proxy (remake/recipes/proxy_rail_62.py, 2026-11-11, proxy_overlay at 4..6x; its numbers are reused here):
  stairs: step fronts y 400 / 432 / 464 / 496 / 528, tread height behind each front 96 / 80 / 64 / 48 / 32, hall floor 16;
  LEFT rail: posts at x 324..328, y front .. front + 4, from the upper tread t to t + 17 (handrail top at the post) + ball; handrail falling 16 per 32;
  RIGHT rail: posts x 700..704, y front - 8 .. front - 4, from t - 4, handrail top t + 13 at the post (+ ball);
  gallery: rail along x at y 356..360 on the landing floor 96, posts x 324 / 488 / 552 / 700, handrail top 113; level connectors from the gallery corners
  to the stair tops (y 360 .. 368); stone stringer under each stair rail with the stair's stepped height (step at front + 4 left, front - 4 right).
Writes landstalker/data/proxies/rail_62_{gallery,left,right}.obj (solid: stringer / landing edge, posts, balusters) + *_rail.obj (handrails, op 'air').
User 2026-11-13: 'Raum 62 Gelaender' as a real 3D model (the box proxy of 2026-11-11 replaced).
  python3 remake/recipes/balustrade/hall62.py OUTDIR"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, HERE)
import furniture as F, balustrade as B

STEPS = [(400, 96), (432, 80), (464, 64), (496, 48), (528, 32)]
FLOOR = 16
GY, GZ, GRAIL = 358.0, 96, 113
GPOSTS = [326.0, 410.0, 490.0, 554.0, 634.0, 702.0]   # measured 2026-11-13 on the whole gallery (3x): the 2026-11-11 proxy had only 324 / 488 / 552 / 700
HR = 1.4                     # handrail radius (drawn as a thin line, ~3 px)
SPACE = 8.0

def baluster(x, y, z0, z1):
    s = (z1 - z0) / B.BAL_H
    return F.lathe(x, y, z0, 1.0, [(z * s, r) for z, r in B.BAL], seg=12)

def post(x, y, z0, ztop, w=4.0):
    return [F.rbox(x - w / 2, x + w / 2, y - w / 2, y + w / 2, z0, ztop - 3.6, 0.5, n=2, flat_bottom=True),
            F.lathe(x, y, ztop - 3.8, 1.0, [(0.0, 1.5), (0.5, 2.0), (1.4, 2.2), (2.3, 1.9), (3.0, 1.2), (3.4, 0.5), (3.6, 0.0)], seg=16)]

def rail(p0, p1):
    return F.tube([p0, p1], [HR, HR], seg=10)

def gallery():
    solid, rails = [F.rbox(320, 704, 352, 368, FLOOR, GZ, 0.6, n=2, flat_bottom=True)], []    # the landing's front edge (stone)
    for x in GPOSTS: solid += post(x, GY, GZ, GRAIL + 9.0)   # ball like the stair posts (rail top + 11 - 2)
    for a, b in zip(GPOSTS, GPOSTS[1:]):
        rails.append(rail((a, GY, GRAIL - HR), (b, GY, GRAIL - HR)))
        g = math.ceil((a + 4) / SPACE) * SPACE
        while g < b - 3:
            solid.append(baluster(g, GY, GZ, GRAIL - 2 * HR)); g += SPACE
    for x in (GPOSTS[0], GPOSTS[-1]): rails.append(rail((x, GY, GRAIL - HR), (x, 368.0, GRAIL - HR)))   # level connectors to the stair tops
    return solid, rails

def stair(side):
    solid, rails = [], []
    if side == "left": px, dy, dz, rh, cx0, cx1, y_top, step_at = 326.0, 2.0, 0, 17, 320, 336, 368, (lambda yf: yf + 4)
    else: px, dy, dz, rh, cx0, cx1, y_top, step_at = 702.0, -6.0, -4, 13, 688, 704, 368, (lambda yf: yf - 4)
    edges = [y_top] + [step_at(yf) for yf, t in STEPS] + [step_at(STEPS[-1][0]) + 4]
    for i, (yf, t) in enumerate(STEPS):   # stone stringer: the stair's stepped height
        y0, y1 = edges[i], edges[i + 1]
        if y1 > y0: solid.append(F.rbox(cx0, cx1, y0, y1, FLOOR, t, 0.5, n=2, flat_bottom=True))
    tops = []
    for i, (yf, t) in enumerate(STEPS):
        py = yf + dy; ztop = t + dz + rh
        solid += post(px, py, t + dz, t + dz + 28.0); tops.append((px, py, ztop - HR))   # ball top t + 28 (left) / t + 24 (right), measured 2026-11-11
    for (x0, y0, z0), (x1, y1, z1) in zip(tops, tops[1:]):   # sloped handrail between the posts + balusters on the 8 grid standing on the stepped stringer
        rails.append(rail((x0, y0, z0), (x1, y1, z1)))
        g = math.ceil((y0 + 3) / SPACE) * SPACE
        while g < y1 - 3:
            zr = z0 + (z1 - z0) * (g - y0) / (y1 - y0) - HR
            foot = next(t for (yf, t), e1 in zip(STEPS, edges[1:]) if g < e1) if g < edges[-1] else FLOOR + 16
            solid.append(baluster(px, g, foot, zr)); g += SPACE
    # level piece from the gallery connector (y 368) to the top post
    rails.append(rail((px, y_top, GRAIL - HR), (px, tops[0][1], GRAIL - HR)))
    g = math.ceil((y_top + 3) / SPACE) * SPACE
    while g < tops[0][1] - 3: solid.append(baluster(px, g, GZ, GRAIL - 2 * HR)); g += SPACE
    return solid, rails

if __name__ == "__main__":
    out = sys.argv[1]
    for name, (s, r) in (("gallery", gallery()), ("left", stair("left")), ("right", stair("right"))):
        B.write(s, os.path.join(out, "rail_62_%s.obj" % name), "%s balustrade of the castle hall (stringer / landing edge, posts, turned balusters), room 62" % name)
        B.write(r, os.path.join(out, "rail_62_%s_rail.obj" % name), "%s balustrade handrail (round, sloped on the stairs), room 62" % name)
    print("hall62: 6 OBJs -> %s" % out)
