#!/usr/bin/env python3
"""heightview.py ROM ROOM OUT.png [--plants FILE.json] [--no-cells] [--no-plants] [--tips] [--no-hand]
   --tips: a magenta cross on every model's top with the FOOT HEIGHT beside it (then the foot is only a dot) [--crop U0,V0,U1,V1] [--scale N]
   -- eye check of the light's 3D data on the room picture (user 2026-11-21: 'das brauchen wir', room 458 plant feet).

Draws the room from the ROM (tools/romrender.py, both planes, no sprites) and on top of it:
  * the game's height map: every cell's top as a thin outline in its height colour (16 green, 32 yellow, 48 red, 64 violet, 80 blue, other white),
    blocked cells dashed with a dot in the middle, the height number in walkable cells' centres;
  * the plant models of data/plants.json (or --plants FILE: a room list [[model, x, y, z], ...] or the whole plants.json): silhouette outline of the
    real light mesh (hand-made 'mesh' models of data/light_proxies.json in cyan) (data/proxies/plant_*.obj) + the foot as a dot with its z.
Coordinates: room picture U / V (the same as the GPU light and remake/recipes/plants/plants.py): U = x - y + 1184, V = (x + y) / 2 - z.
Default crop = the drawn part of the room; --scale 2 doubles the pixels (default 2).  Needs Pillow (~/Project-Friday-Test/hdvenv/bin/python3).
The output is ROM-derived: keep it under ~/Project-Friday-Test/lktest/, never in git."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import romrender as R, proxysurvey as PS
from PIL import Image, ImageDraw, ImageChops, ImageFilter

W, H = 2400, 1300
COL = {16: (60, 220, 60), 32: (255, 210, 0), 48: (255, 60, 60), 64: (200, 80, 255), 80: (80, 160, 255)}
def col(z): return COL.get(int(z), (255, 255, 255))
def UV(x, y, z): return (x - y + 1184, (x + y) / 2 - z)

def mesh(path):
    V, F = [], []
    for l in open(path):
        p = l.split()
        if p and p[0] == "v": V.append(tuple(map(float, p[1:4])))
        elif p and p[0] == "f": F.append([int(t.split("/")[0]) - 1 for t in p[1:]])
    return V, F

def main():
    a = sys.argv[1:]
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    rom, room, out = open(a[0], "rb").read(), int(a[1]), a[2]
    sc = int(opt("--scale") or 2)
    g, r, pa, pb, getpal = R.rom_planes(rom, room)
    print("heightview: room %d: drawing the room picture (~15 s)" % room, flush=True)
    img = Image.frombytes("RGB", (W, H), bytes(R.compose(pa, pb, getpal, 0, 0, W, H, (0, 0, 0), g['tiles'])))
    box = img.getbbox() or (0, 0, W, H)
    if opt("--crop"): box = tuple(int(v) for v in opt("--crop").split(","))
    img = img.crop(box).resize(((box[2] - box[0]) * sc, (box[3] - box[1]) * sc), Image.NEAREST)
    P = lambda x, y, z: ((UV(x, y, z)[0] - box[0]) * sc, (UV(x, y, z)[1] - box[1]) * sc)
    dr = ImageDraw.Draw(img)
    if "--no-cells" not in a:
        hm = PS.heights(rom, room)
        for (cx, cy), (h, b) in sorted(hm.items(), key=lambda t: t[0][0] + t[0][1]):
            z = 16 * h; q = [P(16 * cx, 16 * cy, z), P(16 * cx + 16, 16 * cy, z), P(16 * cx + 16, 16 * cy + 16, z), P(16 * cx, 16 * cy + 16, z)]
            c = col(z)
            if b:
                for i in range(4):
                    (x0, y0), (x1, y1) = q[i], q[(i + 1) % 4]
                    for t in range(0, 10, 2): dr.line((x0 + (x1 - x0) * t / 10, y0 + (y1 - y0) * t / 10, x0 + (x1 - x0) * (t + 1) / 10, y0 + (y1 - y0) * (t + 1) / 10), fill=c)
                mx, my = P(16 * cx + 8, 16 * cy + 8, z); dr.ellipse((mx - 1, my - 1, mx + 1, my + 1), fill=c)
            else:
                dr.polygon(q, outline=c)
                if sc >= 2: mx, my = P(16 * cx + 8, 16 * cy + 8, z); dr.text((mx - 6, my - 5), str(z), fill=c)
    if "--no-plants" not in a:
        root = os.path.normpath(os.path.join(HERE, "..")); data = json.load(open(os.path.join(root, "data", "plants.json")))
        pl = data["rooms"].get(str(room), [])
        if opt("--plants"):
            d2 = json.load(open(opt("--plants"))); pl = d2["rooms"].get(str(room), []) if isinstance(d2, dict) else d2
        ms = {n: mesh(os.path.join(root, "data", f)) for n, f in data["models"].items()}
        edge = Image.new("L", img.size, 0)
        for m, x, y, z in pl:
            Vt, F = ms[m]; mk = Image.new("L", img.size, 0); dm = ImageDraw.Draw(mk)
            for f in F: dm.polygon([P(Vt[i][0] + x, Vt[i][1] + y, Vt[i][2] + z) for i in f], fill=255)
            edge = ImageChops.lighter(edge, ImageChops.subtract(mk, mk.filter(ImageFilter.MinFilter(3))))
        img.paste((255, 255, 255), mask=edge)
        if "--no-hand" not in a:   # hand-made light models of data/light_proxies.json (op 'mesh', world coordinates): cyan outline (plants.py leaves their plants to them)
            he = Image.new("L", img.size, 0); nh = 0
            for e in json.load(open(os.path.join(root, "data", "light_proxies.json")))["rooms"].get(str(room), []):
                if e.get("op") != "mesh": continue
                Vt, F = mesh(os.path.join(root, "data", e["file"])); mk = Image.new("L", img.size, 0); dm = ImageDraw.Draw(mk); nh += 1
                for f in F: dm.polygon([P(*Vt[i]) for i in f], fill=255)
                he = ImageChops.lighter(he, ImageChops.subtract(mk, mk.filter(ImageFilter.MinFilter(3))))
                lx, ly = P(16 * e["cells"][0], 16 * e["cells"][1], e.get("floor", 0)); dr.text((lx, ly - 12), os.path.basename(e["file"])[:-4], fill=(0, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))
            img.paste((0, 255, 255), mask=he); print("heightview: %d hand-made models (cyan)" % nh)
        if "--tips" in a:   # the model's top point: every drawn plant should carry exactly one cross (a drawn plant without one = not found)
            for m, x, y, z in pl:
                tz = max(v[2] for v in ms[m][0]); tx, ty = P(x, y, z + tz)
                dr.line((tx - 5, ty, tx + 5, ty), fill=(255, 0, 255), width=2); dr.line((tx, ty - 5, tx, ty + 5), fill=(255, 0, 255), width=2)
                dr.text((tx + 5, ty - 2), str(int(z)), fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))   # the foot height next to the tip (user 2026-11-21: the foot label of a back row lies among the row in front)
        for m, x, y, z in pl:
            fx, fy = P(x, y, z); c = col(z)
            dr.ellipse((fx - 3, fy - 3, fx + 3, fy + 3), fill=c, outline=(0, 0, 0))
            if "--tips" not in a: dr.text((fx + 4, fy - 5), str(int(z)), fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))
        print("heightview: %d plants" % len(pl))
    img.save(out); print("heightview: wrote %s (%d x %d, crop U %d..%d V %d..%d)" % (out, img.size[0], img.size[1], box[0], box[2], box[1], box[3]))

if __name__ == "__main__":
    main()
