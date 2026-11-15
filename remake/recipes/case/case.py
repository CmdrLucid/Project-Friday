#!/usr/bin/env python3
"""case.py OUT.obj NAME - CASE FURNITURE (wardrobes, racks, shelves) built from remake/lib/cabinet.py by the measured specs below (rooms where the piece
stands, its world box, front face, rows from the bottom up, extras). Each spec was checked by overlay on rom_picture (remake/tools/proxy_overlay.py) and
in the clay preview (remake/tools/clay_preview.py). GAME coordinates x east, y south, z up, units.  `case.py --list` prints the specs."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, os.path.join(HERE, "..", "castle_bench"))
import cabinet
from furniture import rbox, lathe
from castle_bench import write_obj

SPEAR = [(0.0, 0.7), (0.84, 0.6), (0.86, 1.0), (0.9, 1.3), (0.97, 0.8), (1.0, 0.15)]   # shaft, socket, leaf blade, tip
WARDROBE = [("plinth", 2), ("drawers", 5, 1), ("doors", 40, 2)]
SPECS = {
    # the two wardrobes on the west wall of the castle rooms 65 / 66 (tileset 15, cells x 14, y 31..34, 48 high): double doors over a drawer rail
    "castle_wardrobes_65": dict(rooms=[65, 66], cells=[14, 31, 14, 34], floor=0,
                                parts=[("cab", (224, 240, 496, 528, 0, 48), "+x", WARDROBE), ("cab", (224, 240, 528, 560, 0, 48), "+x", WARDROBE)]),
    # the plate rack on the west wall of the castle kitchen 68 / 69 (tileset 15, cells x 13, y 17..21, 48 high): five compartments, drawers at the
    # bottom, bottles in the middle row, upright plates on top
    "castle_plate_rack_68": dict(rooms=[68, 69], cells=[13, 17, 13, 21], floor=0,
                                 parts=[("cab", (208, 224, 272, 352, 0, 48), "+x", [("plinth", 2), ("drawers", 9, 5), ("shelf", 14, 5, "bottles"), ("shelf", 14, 5, "plates")])]),
    # the spear rack of the castle armoury 78 / 79 (tileset 15, cells x 17, y 28..29, 48 high): a plank case open to the east with four spears standing
    # in it (blade tops at z ~39, read from the drawn blades)
    "castle_spear_rack_78": dict(rooms=[78, 79], cells=[17, 28, 17, 29], floor=0,
                                 parts=[("cab", (272, 288, 448, 480, 0, 48), "+x", [("open", 48)])]
                                       + [("lathe", (285.0, y, 0.0, 40.0, SPEAR, 10)) for y in (474.0, 466.7, 458.3, 450.3)]),
    # Mercator inn 623 / 624 / 701 / 702 (tileset 2, cells x 23, y 34..37, floor 0): a GLASS CABINET (y 36..37, 48 high, two glass doors over two)
    # and a low DRESSER (y 34..35, top drawn at 22, collision 16) with a vase, both open to the east
    "inn_cabinet_623": dict(rooms=[623, 624, 701, 702], cells=[23, 34, 23, 37], floor=0,
                            parts=[("cab", (368, 384, 576, 608, 0, 48), "+x", [("plinth", 2), ("glass", 22, 2), ("glass", 22, 2)]),
                                   ("cab", (370, 384, 544, 576, 0, 22), "+x", [("plinth", 2), ("drawers", 9, 2), ("drawers", 9, 2)]),
                                   ("lathe", (382.5, 563.5, 22.0, 10.0, [(0.0, 1.6), (0.3, 2.5), (0.6, 2.2), (0.8, 0.9), (1.0, 1.2)], 12))]),
    # the wardrobe of the castle storeroom 72 (tileset 15, cells x 24..25, y 18, floor 16, 48 high): double doors to the south over a drawer rail
    "castle_wardrobe_72": dict(rooms=[72], cells=[24, 18, 25, 18], floor=16,
                               parts=[("cab", (384, 416, 288, 304, 16, 64), "+y", WARDROBE)]),
}

def build(spec):
    out = []
    for p in spec["parts"]:
        if p[0] == "cab": out += cabinet.cabinet(*p[1], p[2], p[3], **(p[4] if len(p) > 4 else {}))
        elif p[0] == "box": out.append(rbox(*p[1], 0.3, n=1))
        elif p[0] == "lathe": out.append(lathe(*p[1]))
    return out

if __name__ == "__main__":
    if sys.argv[1] == "--list":
        for k, s in SPECS.items(): print(k, s["rooms"], s["cells"])
    else: write_obj(sys.argv[1], build(SPECS[sys.argv[2]]), sys.argv[2])
