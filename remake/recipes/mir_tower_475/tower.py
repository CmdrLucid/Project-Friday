#!/usr/bin/env python3
"""tower.py [OUT.obj] : the base of MIR'S TOWER seen from outside, room 475 MIR_TOWER_EXTERIOR, as a light shape (near-final 3D, as drawn).
The collision holds the tower as a block only 80 high (cells x 16..27 y 16..25, ground 16), the drawing's blue walls run on beyond the top of the
picture (front corner (432, 416) at V 408, picture top V 88 -> at least z 336): the light knew only the lower 80 and lit the wall above it with the
ground behind. Measured 2026-11-24 on the room picture (U = x - y + 1184, V = (x + y) / 2 - z) + collision:
  body: the DRAWN tower is much wider than its collision block (that is only where you stand at it): front corner = where the scale pattern
  turns, U 1213, its foot V 412 -> (442.5, 413.5); the front wall's left end U 865 and the right wall's back end U 1405 -> x 97..442.5,
  y 221.5..413.5 (first built on the collision 256..432 / 256..416: corner 13 px off, corrected), z 16..440 (above the picture everywhere),
  the vertical corner edges slightly chamfered (1.5);
  doorway in the +y wall: dark opening U 1110..1132 -> x 339.5..361.5, from the threshold 32 to the arch top ~92 (arched: the top 11 a half circle),
  one cell deep (the blocked 32 cells (21,25) / (22,25)); a GRIFFIN head over it (drawn U 1104..1132, V 271..296; sculpt of griffin.py, see GRIFFIN HEAD);
  a STEP slab in front (walkable 32 cells (21,26) / (22,26); drawn as a block with rounded front corners, first read as a half circle): x 334.5..366.5, y 413.5..432, z 16..32;
  two wall LANTERNS (drawn centres U 1079 and ~1161 -> x 308.5 and 390.5 on the +y wall, z 38..90) IN NICHES of the wall (user 2026-11-24: 'die sind
  in der Wand und stehen nur ein bisschen vor'; first built standing 7 in front): niche 14 wide 6 deep; the glass (z 56..72) inside the wall face, the gold holder (72..94) and the round gold knob (34..56) stand out ~3 (user marked
  exactly these two parts).
  v2 (user: 'hast du es als echte 3D-Form gemacht?'): the walls carry the drawn SCALE RELIEF (16 x 16 stone shingles, flush at the top, 1.5 out
  at the rounded lower edge), the step got a rounded top band, the panel over the door is a STATUE HEAD (user: 'das ist eigentlich ein Statuenkopf'), a GRIFFIN ('eher der Kopf eines Vogel Greifs', no round
  nose): mane disc, skull, an EAGLE beak (broad root, rounded top, narrow cutting edge, hooked tip; a round
  tube first looked like a water tap), heavy brows, two feather tufts swept back.
Pure Python, no ROM (the griffin head comes from griffin.py).  Run: python3 remake/recipes/mir_tower_475/griffin.py, then python3 remake/recipes/mir_tower_475/tower.py"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "landstalker", "data", "proxies", "mir_tower_475.obj")
X0, Y0, X1, Y1, ZG, ZT = 97.0, 221.5, 442.5, 413.5, 16.0, 440.0
V, F = [], []
def poly_prism(pts, z0, z1):
    """closed prism over a polygon (counter-clockwise seen from above in game x / y = clockwise on screen ...: orientation fixed by the signed area)"""
    n = len(pts); a = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    if a < 0: pts = pts[::-1]
    o = len(V); V.extend([(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts])
    for i in range(n): F.append((o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i))
    F.append(tuple(o + i for i in range(n - 1, -1, -1))); F.append(tuple(o + n + i for i in range(n)))
def cbox(x0, y0, z0, x1, y1, z1, c=1.0):
    poly_prism([(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)], z0, z1)
def lathe(cx, cy, prof, n=16):
    o = len(V)
    for z, r in prof:
        for i in range(n): a = 2 * math.pi * i / n; V.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    for j in range(len(prof) - 1):
        for i in range(n): a = o + j * n + i; b = o + j * n + (i + 1) % n; F.append((a, b, b + n, a + n))
    F.append(tuple(o + i for i in reversed(range(n)))); last = o + (len(prof) - 1) * n; F.append(tuple(last + i for i in range(n)))
# body: the +y wall has the door recess as a notch in its footprint up to the arch; above the arch the wall is solid
D0, D1, DZ0, DZT, DEEP = 339.5, 361.5, 32.0, 92.0, 16.0
cb = 1.5
LX = (308.5, 390.5); NW, ND = 7.0, 6.0                                         # lantern NICHES in the +y wall (user 2026-11-24: the lanterns sit IN the wall,
                                                                               # standing out only a little): 14 wide as drawn, 6 deep, z ZG..92 notch (lantern 36..92)
def notch(x0, x1, d): return [(x1, Y1), (x1, Y1 - d), (x0, Y1 - d), (x0, Y1)]
foot = [(X0 + cb, Y0), (X1 - cb, Y0), (X1, Y0 + cb), (X1, Y1 - cb), (X1 - cb, Y1)] + notch(LX[1] - NW, LX[1] + NW, ND) + notch(D0, D1, DEEP) \
       + notch(LX[0] - NW, LX[0] + NW, ND) + [(X0 + cb, Y1), (X0, Y1 - cb), (X0, Y0 + cb)]
poly_prism(foot, ZG, DZT)                                                      # lower part with the doorway notch
cbox(X0, Y0, DZT, X1, Y1, ZT, cb)                                              # the tower above the doorway
cbox(D0, Y1 - DEEP, ZG, D1, Y1, DZ0, 0.0)                                      # threshold block in the doorway (up to 32)
R = (D1 - D0) / 2; cx = (D0 + D1) / 2; k = 8                                    # arch: fill the corners of the recess above the half circle
for side in (-1, 1):
    pts = [(cx + side * R, DZT - R)] + [(cx + side * R * math.cos(math.pi / 2 * i / k), DZT - R + R * math.sin(math.pi / 2 * i / k)) for i in range(k + 1)] + [(cx + side * R, DZT)]
    # extrude this (x, z) profile through the recess depth
    n = len(pts); o = len(V)
    V.extend([(x, Y1 - DEEP, z) for x, z in pts] + [(x, Y1, z) for x, z in pts])
    a = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)); flip = (a > 0) == (side > 0)
    for i in range(n):
        q = (o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i); F.append(q[::-1] if flip else q)
    capA, capB = tuple(o + i for i in range(n)), tuple(o + n + i for i in range(n)); F.append(capA if flip else capA[::-1]); F.append(capB[::-1] if flip else capB)
rs = 4.0; sx0, sx1, sy1 = 334.5, 366.5, 432.0                                   # step: a slab before the door with rounded front corners
step = [(sx1, Y1)] + [(sx1 - rs + rs * math.cos(math.pi / 2 * i / 4), sy1 - rs + rs * math.sin(math.pi / 2 * i / 4)) for i in range(5)] \
       + [(sx0 + rs - rs * math.sin(math.pi / 2 * i / 4), sy1 - rs + rs * math.cos(math.pi / 2 * i / 4)) for i in range(5)] + [(sx0, Y1)]
poly_prism(step, ZG, 29.5)
step_top = [(x + (0 if abs(y - Y1) < 0.1 else 0), y) for x, y in step]                # rounded top edge: a 2.5 high inset band on top
cx_, cy_ = (sx0 + sx1) / 2, (Y1 + sy1) / 2
poly_prism([(cx_ + (x - cx_) * 0.88, Y1 + (y - Y1) * 0.88) for x, y in step], 29.5, 32.0)
for lx in LX:                                                                  # lanterns (user marks 2026-11-24: the two GOLD parts stand out a little,
                                                                               # the glass between them sits in the wall); measured on the right lantern:
                                                                               # gold holder V 308..330 -> z 72..94, glass V 330..346 -> z 56..72, round knob z 34..56, ~14 wide
    cbox(lx - NW, Y1 - ND, ZG, lx + NW, Y1, 34.0, 0.0)                         # niche floor up to the knob
    lathe(lx, Y1 - 3.0, [(34.0, 1.5), (37.0, 5.0), (45.0, 6.5), (53.0, 5.0), (56.0, 2.0)], 14)   # round gold knob, ~3.5 out
    cbox(lx - 5.0, Y1 - ND, 56.0, lx + 5.0, Y1 - 0.5, 72.0, 1.0)               # glass, inside the wall face
    cbox(lx - 6.5, Y1 - ND, 72.0, lx + 6.5, Y1 + 3.0, 90.0, 1.2)               # gold holder, 3 out
    cbox(lx - 4.0, Y1 - 1.0, 90.0, lx + 4.0, Y1 + 2.5, 94.0, 1.0)              # its top finial
    cbox(lx - NW, Y1 - ND, 90.0, lx + NW, Y1 - 1.0, 92.0, 0.0)                 # close the niche top behind the finial
# SCALE RELIEF of the walls (user 2026-11-24 'als echte 3D-Form'): the drawing repeats every 16 along the wall and every 16 up (autocorrelation
# of the rectified +y face: peaks 16 / 32 both ways), one stone shingle per tile: flush with the wall at its top, standing out 1.5 at its rounded
# lower edge (corner radius 4); only where the picture shows the wall (z up to the picture top V 88 + 16)
def shingle(face, a0, z0):
    # face 'y' = the +y wall (a = x), 'x' = the +x wall (a = y); tile a0..a0+16, z0..z0+16; outline in (a, z) with rounded lower corners
    r = 4.0; w = 15.0; h = 15.0; pts = [(a0 + 0.5, z0 + h)]
    for k in range(5): t = math.pi / 2 * k / 4; pts.append((a0 + 0.5 + r - r * math.cos(t), z0 + 0.5 + r - r * math.sin(t)))
    for k in range(5): t = math.pi / 2 * k / 4; pts.append((a0 + 0.5 + w - r + r * math.sin(t), z0 + 0.5 + r - r * math.cos(t)))
    pts.append((a0 + 0.5 + w, z0 + h))
    n = len(pts); o = len(V)
    def P3(a, z, d): return (a, Y1 + d, z) if face == 'y' else (X1 + d, a, z)
    for a, z in pts: V.append(P3(a, z, -0.2))
    for a, z in pts: V.append(P3(a, z, 1.5 * (z0 + h - z) / h + 0.05))
    for i in range(n): F.append((o + i, o + (i + 1) % n, o + n + (i + 1) % n, o + n + i))
    F.append(tuple(o + i for i in range(n))); F.append(tuple(o + n + i for i in reversed(range(n))))
skip = lambda a0, z0: (D0 - 8 <= a0 + 8 <= D1 + 8 and z0 < DZT + 4) or any(abs(a0 + 8 - lx) < 12 and z0 < 96 for lx in LX) or (322 < a0 + 8 < 384 and 80 < z0 + 8 < 116)
for a0 in range(int(X0) + 1, int(X1) - 15, 16):                                # +y wall
    ztop = (a0 + 8 + Y1) / 2 - 88 + 16
    for z0 in range(int(ZG), int(min(ztop, ZT - 16)), 16):
        if not skip(a0, z0): shingle('y', float(a0), float(z0))
for a0 in range(int(Y0) + 1, int(Y1) - 15, 16):                                # +x wall
    ztop = (X1 + a0 + 8) / 2 - 88 + 16
    for z0 in range(int(ZG), int(min(ztop, ZT - 16)), 16):
        shingle('x', float(a0), float(z0))
# every closed part with outward normals: parts are disjoint vertex ranges; a part with a negative signed volume is turned
par = list(range(len(V)))
def fd(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
for fc in F:
    for vi in fc[1:]: par[fd(vi)] = fd(fc[0])
vol = {}
for fc in F:
    c = fd(fc[0])
    for i in range(1, len(fc) - 1):
        a, b, d = V[fc[0]], V[fc[i]], V[fc[i + 1]]
        vol[c] = vol.get(c, 0.0) + a[0] * (b[1] * d[2] - b[2] * d[1]) - a[1] * (b[0] * d[2] - b[2] * d[0]) + a[2] * (b[0] * d[1] - b[1] * d[0])
F = [fc[::-1] if vol[fd(fc[0])] < 0 else fc for fc in F]
# GRIFFIN HEAD over the door (user 2026-11-24, several rounds: 'Statuenkopf', 'Kopf eines Vogel Greifs', looking straight out of the wall, a
# curved feathered neck, 'mach es so, dass es fuer die Lichtform passt und auf der Zeichnung liegt'): the metaball sculpt of griffin.py (light
# version, local frame x right / y out of the wall / z up) placed by a silhouette fit on the drawn carving (IoU 0.73 over a 0.5 px search:
# scale 0.85, width x 2.0 (the drawn head is broad), centre x 353 z 100 on the wall). Appended after the outward fix (its own winding is right).
GH = os.path.expanduser("~/.landstalker_remake/assets/griffin_475/griffin_head_light.obj"); GS, GSX, GX, GZ = 0.85, 2.0, 353.0, 100.0
if not os.path.exists(GH): sys.exit("run remake/recipes/mir_tower_475/griffin.py first (makes %s)" % GH)
go = len(V)
for l in open(GH):
    if l.startswith("v "):
        lx, ly, lz = map(float, l.split()[1:4]); V.append((GX + GS * GSX * lx, Y1 + GS * ly, GZ + GS * lz))
    elif l.startswith("f "): F.append(tuple(go + int(t) - 1 for t in l.split()[1:]))
with open(OUT, "w") as f:
    f.write("# light proxy: base of Mir's tower, room 475 (remake/recipes/mir_tower_475/tower.py). GAME coordinates x east, y south, z up.\n")
    for v in V: f.write("v %.3f %.3f %.3f\n" % v)
    for fc in F: f.write("f " + " ".join(str(i + 1) for i in fc) + "\n")
print("mir_tower_475: %d vertices, %d faces -> %s" % (len(V), len(F), OUT))
