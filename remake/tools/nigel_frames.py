#!/usr/bin/env python3
"""nigel_frames.py ROM  -- Nigel's standing and walking frames for the walk demo (remake/play), cut from the user's own ROM with rom_sprite.py
into ~/.landstalker_remake/figures/nigel/ (LOCAL only) plus frames.json (image, anchor ox / oy per frame).
Animations of SpriteGraphic 0 (disassembly sprites/spriteanimationframes.asm, AnimationIndex in steps of 4):
 0 = Frame00 standing, back view;  4 = Frame01 standing, front view;  8 = Frames 02..09 walking, back view;  12 = Frames 10..17 walking, front view.
Unflipped the front view looks down-left on screen (game +y), the back view up-right (game -y); the game flips them for +x / -x."""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.expanduser("~/.landstalker_remake/figures/nigel")
SETS = dict(stand_back=(0, 1), stand_front=(4, 1), walk_back=(8, 8), walk_front=(12, 8))


def main():
    rom = sys.argv[1]; os.makedirs(OUT, exist_ok=True); res = {}
    for name, (anim, n) in SETS.items():
        res[name] = []
        for f in range(n):
            png = os.path.join(OUT, "a%d_f%d.png" % (anim, 4 * f))
            subprocess.run([sys.executable, os.path.join(HERE, "rom_sprite.py"), rom, "0", str(anim), str(4 * f), png], check=True, stdout=subprocess.DEVNULL)
            ox, oy = [float(v) for v in open(png[:-4] + ".txt").read().split()[:2]]
            res[name].append(dict(img=os.path.basename(png), ox=ox, oy=oy))
        print(name, len(res[name]), "frames", flush=True)
    json.dump(res, open(os.path.join(OUT, "frames.json"), "w"), indent=1)
    print("->", os.path.join(OUT, "frames.json"))


if __name__ == "__main__":
    main()
