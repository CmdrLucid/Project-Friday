"""LIGHT PROXIES: the ROCK WALLS of the barrier wall rooms (barrier wall pass 2026-11-27, user: 'mach die Raeume durch'), one spec per room.
Same method as room 503 / 465 (remake/recipes/proxy_rock_503.py, proxy_rock_465.py), built by remake/lib/rockwall.py:
  * the rock is drawn over VOID / invisible BARRIER ($4F) cells; the light's void painter made them a low water floor = a hole (no sword glow on the wall);
  * FOOTPRINT = the cells BEHIND the walkable ground up to the barrier lines (the game's collision follows the drawn wall foot), as rectangles that hold only
    rock cells (an outdoor surface model owns its whole op rectangle: one piece / OBJ / op per rectangle); the void IN FRONT of a walkway (a cliff below it)
    is not part of it (own class, not done);
  * TOP = the drawn outline (rock_outlines.json, measured per picture column) extruded along the view ray = seen edge-on, optionally capped by a drawn
    plateau height (caps: [(U from, U to, z)]).
Run: python3 remake/recipes/proxy_rock_rooms.py [ROOM ...]   -> landstalker/data/proxies/rock_<room>_<piece>.obj (our own geometry, committed);
     prints the light_proxies.json ops (--ops) for the rooms."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import rockwall as RW

# room: pieces (cells x0 y0 x1 y1 inclusive, only void / barrier cells), screen columns U of the solid, plateau caps, the rooms sharing the map, notes
SPECS = {
    469: dict(pieces=[(12, 25, 26, 31), (12, 32, 21, 59), (22, 12, 28, 24), (12, 12, 21, 24)], u=(577, 1247),
              note="narrow path cut into the cliff, descending along y (x 22..23, 10 -> 0 steps); wall = barrier x 20..21 (face x 352) and rows 28..31, top edge x 352 at z ~272"),
    504: dict(pieces=[(12, 12, 29, 48), (30, 12, 42, 31), (30, 34, 31, 48)], u=(912, 1358),
              note="rock bowl with the cave door: back wall barrier row 31 behind the 240 terrace, left wall barrier x 31 (rows 34..48)"),
    505: dict(pieces=[(12, 12, 53, 22), (12, 23, 24, 27), (25, 23, 27, 25)], u=(1153, 1630),
              note="path descending along x in front of a wall: barrier row 22 (face y 368), barrier x 27 rows 22..25"),
    470: dict(pieces=[(12, 12, 17, 47), (18, 12, 35, 24), (18, 25, 21, 35), (22, 25, 23, 29), (22, 30, 22, 34), (24, 25, 24, 26), (25, 25, 25, 25),
                      (26, 25, 35, 26), (18, 36, 18, 45), (19, 36, 19, 36)], u=(704, 1343),
              note="rock bowl with the cave door (25, 26): barrier rows 25..26 and the left wall x 18..23 stepping down to the stairs"),
    502: dict(pieces=[(12, 12, 44, 21), (12, 22, 22, 37), (23, 22, 25, 22), (26, 22, 44, 22), (23, 25, 25, 35)], u=(1024, 1551),
              note="rock wall behind the walkway: barrier row 22; left behind the blocked 176 rock ledge (x 26..28)"),
    508: dict(pieces=[(12, 12, 32, 15), (35, 12, 39, 15), (12, 16, 20, 60), (21, 16, 23, 28), (21, 50, 23, 60)], u=(496, 1566), also=[483],
              note="long left rock wall (x <= 20, barrier x 21..23 rows 16..28 / 50..60 beside the terraces) and the back wall (rows <= 15) with the gap of the back exit (33..34 x 13..15); room 483 = the same map and picture"),
    486: dict(pieces=[(12, 12, 63, 26), (12, 27, 42, 29), (45, 27, 48, 29), (49, 27, 49, 28), (50, 27, 56, 29), (57, 27, 57, 28), (58, 27, 63, 29),
                      (12, 30, 29, 63),
                      (49, 29, 49, 29, 160), (57, 29, 57, 29, 160)],
              extra=[{"op": "ground", "cells": [30, 30, 31, 34, 336], "replace": True, "why": "room 486 left wall around the door (31, 33) and the tower side above the 240 wall walk (cells 30..31 x 30..34) as HEIGHT-MAP columns at the drawn top 336 (outline: 337 all along), not a mesh: a mesh piece next to the 240 wall-walk columns (31, 35+) in the same wall plane x 512 left a dark seam (user 2026-11-27: 'immer noch ein schwarzer Streifen'); the door is closed for the light (its drawn opening stays black)"}], u=(641, 1695),
              note="walled garden with the arcade: ivy rock back wall (rows <= 29) with the 240 passage (43..44 x 27..29) and the two doors (49, 29) / (57, 29) "
                   "behind the 160 walkway on the stone block (user marked it), left wall (barrier x 30..31 rows 30..34, door (31, 33)); the doors are closed for the light from their floor up (128 / 160; user 2026-11-27: a black stripe beside the door = a cell-wide niche beside the narrower drawn arch; the drawn opening stays black anyway); the 240 passage stays open"),
    518: dict(pieces=[(12, 12, 61, 23), (31, 24, 61, 26), (33, 27, 61, 32)], u=(1281, 1647),
              note="terraced mountain with forest: the big rock peak behind the terraces (rows <= 32, x >= 33), the barrier strip x 31..34 between the 208 terraces lies left of the peak (trees above it: not done), "
                   "the back above the exit (29..30 x 24..26) stays open; the void left of the lower terraces is no wall (left out); the solid starts at the peak's left flank U 1281 (left of it the outline is the terrace trees)"),
    # class A tested 2026-11-27 and NOT kept: 426 (the light already lit the waterfall wall: no change), 492 (diagonal cliff on a one-row cell staircase:
    # a lit band with hard sides), 498 (a fall / climb room: no test spot holds Nigel); 737 (the light paints its void at walkway level: the wall mesh made the glow dimmer)
    524: dict(pieces=[(23, 12, 45, 19), (46, 12, 49, 16), (50, 12, 55, 19), (27, 20, 38, 22)], u=(1232, 1887),
              extra=[{"op": "ground", "cells": [35, 23, 36, 23, 112], "replace": True, "why": "room 524: the rest of the game's 160 rock box in front of the rock piece d (rows 20..22) gets the floor of its neighbours (37..38, 23) = 112 (one front edge for the rock: the first try with a second step at row 23 lit as a box beside the pines, GPU 2026-11-27)"}],
              note="lake shrine room: the big sand rock face behind the walkway / lava path (barrier row 19, face y 320) with the cave door (42, 18..19) and the back passage x 46..49 rows 17..20 left open; "
                   "LEFT of the pines it stands forward to row 22 (the game's 160 box x 35..39 rows 19..23: at floor height the drawing there shows rock face, no floor); one front edge only (a second step at row 23 lit as a box); the small void x 54..55 rows 20..21 stays out (a piece there made a hard lit band on the lava path); "
                   "the pines x 40 rows 20..22 and the phantom-fixed floor (39, 20..23) / (37..38, 23) stay; user 2026-11-27 marked the hard sword-glow box + shadow of the 160 box"),
    514: dict(pieces=[(36, 12, 41, 12), (44, 12, 44, 19), (38, 13, 43, 13), (45, 13, 45, 20), (39, 14, 43, 14), (46, 14, 47, 21), (40, 15, 43, 15), (48, 15, 48, 22), (41, 16, 43, 16), (49, 16, 50, 22), (42, 17, 43, 17), (51, 17, 51, 22), (43, 18, 43, 18), (52, 18, 52, 22)], u=(848, 1743),
              note="the right back cliff (class A, deep hole)"),
}

def rock(room):
    o = json.load(open(os.path.join(HERE, "rock_outlines.json")))["rooms"][str(room)]
    u0, vs = o["u0"], o["v"]; s = SPECS[room]
    pts = [(u0 + i, v) for i, v in enumerate(vs) if v < 9999 and s["u"][0] <= u0 + i <= s["u"][1]]
    E = RW.envelope(pts); lo, hi = min(E), max(E)
    def vsil(U):
        U = min(max(U, lo), hi); a = int(U); f = U - a
        return E[a] * (1 - f) + E[min(a + 1, hi)] * f
    caps = s.get("caps")
    cap = (lambda U: next((z for a, b, z in caps if a <= U <= b), None)) if caps else None
    return RW.Rock(vsil, s["u"][0] - 1184, s["u"][1] - 1184, cap=cap)

def names(room):
    return [chr(ord('a') + i) for i in range(len(SPECS[room]["pieces"]))]

def build(room):
    R = rock(room); out = []
    for k, r in zip(names(room), SPECS[room]["pieces"]):
        V, F = R.piece(r[:4], step=4, zb=r[4] if len(r) > 4 else 0.0)   # a 5th number = lintel bottom (door below)
        if not F: print("proxy_rock_rooms %d %s: EMPTY piece %s" % (room, k, r)); continue
        p = os.path.join(HERE, "..", "..", "landstalker", "data", "proxies", "rock_%d_%s.obj" % (room, k))
        RW.write_obj(p, V, F, "room %d rock piece %s (cells %d..%d x %d..%d)" % (room, k, r[0], r[2], r[1], r[3]) + (", lintel from z %d" % r[4] if len(r) > 4 else "") + ", light proxy (remake/recipes/proxy_rock_rooms.py), game coordinates")
        zs = [v[2] for v in V]
        print("proxy_rock_rooms %d %s: %d triangles, z %.0f..%.0f, inward %d" % (room, k, len(F), min(zs), max(zs), R.orient_bad(V, F, r[:4])))
        out.append((k, r[:4]))
    return out

def ops(room, built, for_room=None):
    why = ("room %d ROCK WALL piece %%s (barrier wall pass 2026-11-27): rock drawn over VOID / BARRIER ($4F) cells (void painter: a water hole, no sword glow on the wall); "
           "solid behind the walkway up to the barrier lines, top = drawn outline seen edge-on; remake/recipes/proxy_rock_rooms.py: %s") % (room, SPECS[room]["note"])
    return [{"op": "mesh", "cells": list(r), "file": "proxies/rock_%d_%s.obj" % (room, k), "surface": True, "why": why % k} for k, r in built] + SPECS[room].get("extra", [])

if __name__ == "__main__":
    rooms = [int(a) for a in sys.argv[1:] if a.isdigit()] or sorted(SPECS)
    allops = {}
    for room in rooms:
        b = build(room); allops[room] = ops(room, b)
        for other in SPECS[room].get("also", []): allops[other] = [dict(o, why=o["why"].replace("room %d ROCK" % room, "room %d (same map / picture as %d) ROCK" % (other, room))) for o in allops[room]]
    if "--ops" in sys.argv: print(json.dumps({str(k): v for k, v in allops.items()}))
