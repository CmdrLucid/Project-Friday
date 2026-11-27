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
                      (12, 30, 29, 63), (30, 30, 30, 34), (31, 30, 31, 32), (31, 34, 31, 34)], u=(641, 1695),
              note="walled garden with the arcade: ivy rock back wall (rows <= 29) with the 240 passage (43..44 x 27..29) and the two doors (49, 29) / (57, 29) "
                   "behind the 160 walkway on the stone block (user marked it), left wall (barrier x 30..31 rows 30..34, door (31, 33)); every gap stays open"),
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
        V, F = R.piece(r, step=4)
        if not F: print("proxy_rock_rooms %d %s: EMPTY piece %s" % (room, k, r)); continue
        p = os.path.join(HERE, "..", "..", "landstalker", "data", "proxies", "rock_%d_%s.obj" % (room, k))
        RW.write_obj(p, V, F, "room %d rock piece %s (cells %d..%d x %d..%d), light proxy (remake/recipes/proxy_rock_rooms.py), game coordinates" % (room, k, r[0], r[2], r[1], r[3]))
        zs = [v[2] for v in V]
        print("proxy_rock_rooms %d %s: %d triangles, z %.0f..%.0f, inward %d" % (room, k, len(F), min(zs), max(zs), R.orient_bad(V, F, r)))
        out.append((k, r))
    return out

def ops(room, built, for_room=None):
    why = ("room %d ROCK WALL piece %%s (barrier wall pass 2026-11-27): rock drawn over VOID / BARRIER ($4F) cells (void painter: a water hole, no sword glow on the wall); "
           "solid behind the walkway up to the barrier lines, top = drawn outline seen edge-on; remake/recipes/proxy_rock_rooms.py: %s") % (room, SPECS[room]["note"])
    return [{"op": "mesh", "cells": list(r), "file": "proxies/rock_%d_%s.obj" % (room, k), "surface": True, "why": why % k} for k, r in built]

if __name__ == "__main__":
    rooms = [int(a) for a in sys.argv[1:] if a.isdigit()] or sorted(SPECS)
    allops = {}
    for room in rooms:
        b = build(room); allops[room] = ops(room, b)
        for other in SPECS[room].get("also", []): allops[other] = [dict(o, why=o["why"].replace("room %d ROCK" % room, "room %d (same map / picture as %d) ROCK" % (other, room))) for o in allops[room]]
    if "--ops" in sys.argv: print(json.dumps({str(k): v for k, v in allops.items()}))
