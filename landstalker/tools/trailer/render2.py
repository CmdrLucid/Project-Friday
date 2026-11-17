#!/usr/bin/env python3
"""Trailer 2.0 renderer (modern style, 2026-11-17). Recipe only: clips (shoot.py) and output live in ~/.landstalker_trailer/v2, never in git.

  ~/.landstalker_trailer/venv/bin/python render2.py [--preview] [--from SEC] [--to SEC] [--out NAME]
Cuts on the bars of the user's song (~/.landstalker_trailer/music/song.mp3: bar 1.4275 s from 1.23 s, measured for trailer 1).
Style: thin letter-spaced captions with an amber accent line, slow push-in on every shot, short light flashes on the cuts of the loud parts,
split screens (original | 2.0) with a sweeping divider, the 4:3 original opening into the 16:9 2.0 picture.
"""
import os, sys, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.expanduser("~/.landstalker_trailer/v2")
SONG = os.path.expanduser("~/.landstalker_trailer/music/song.mp3")
FD = "/usr/share/fonts/noto/"
PREVIEW = "--preview" in sys.argv
W, H, FPS = (960, 540, 30) if PREVIEW else (1920, 1080, 60)
S = H / 1080.0
P, PH = 1.4275, 1.23
DUR = 85.73
AMBER = (245, 179, 66)


def B(k):
    return PH + k * P


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def font(name, size):
    return ImageFont.truetype(FD + name, int(size * S))


# ---------------------------------------------------------------- clip frames (sequential ffmpeg readers)
class Reader:
    def __init__(self, name):
        self.path = os.path.join(OUT, "clips", name + ".mp4")
        if not os.path.exists(self.path):
            raise SystemExit(f"missing clip {name}: run shoot.py {name}")
        self.n = int(subprocess.check_output(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                                              "stream=nb_read_packets", "-of", "csv=p=0", self.path]).decode().strip().split(",")[0])
        self.p = None; self.pos = -1; self.last = None

    def open(self, i):
        if self.p:
            self.p.kill()
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", "%.4f" % (i / 60.0), "-i", self.path, "-vf", f"scale={W}:{H}:flags=lanczos",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.pos = i - 1

    def get(self, i):
        i = max(0, min(self.n - 1, int(i)))
        if self.p is None or i < self.pos or i > self.pos + 90:
            self.open(i)
        while self.pos < i:
            buf = self.p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            self.last = Image.frombytes("RGB", (W, H), buf); self.pos += 1
        return self.last


READERS = {}


def frame(name, i):
    if name not in READERS:
        READERS[name] = Reader(name)
    return READERS[name].get(i)


# ---------------------------------------------------------------- captions
def spaced(draw, xy, text, f, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + track
    return x


def text_w(text, f, track):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    return sum(d.textlength(ch, font=f) + track for ch in text) - track


CAPS = {}


def caption_layer(title, sub):
    key = (title, sub)
    if key in CAPS:
        return CAPS[key]
    ft, fs = font("NotoSans-Light.ttf", 58), font("NotoSans-Regular.ttf", 33)
    tw = text_w(title, ft, 9 * S); sw = text_w(sub, fs, 1.5 * S) if sub else 0
    w = int(max(tw, sw) + 120 * S); h = int(170 * S)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    spaced(d, (40 * S, 18 * S), title, ft, (255, 255, 255, 255), 9 * S)
    if sub:
        spaced(d, (42 * S, 104 * S), sub, fs, (235, 235, 235, 235), 1.5 * S)
    d.rectangle([0, 30 * S, 5 * S, (140 if sub else 92) * S], fill=AMBER + (255,))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(10 * S)).point(lambda v: v * 0.75))
    out = Image.alpha_composite(sh, im)
    CAPS[key] = out
    return out


def put_caption(img, title, sub, t, t0, t1, pos="bl"):
    """slide in from the left + fade (0.35 s), fade out before t1"""
    a_in = min(1.0, max(0.0, (t - t0 - 0.15) / 0.35)); a_out = min(1.0, max(0.0, (t1 - t) / 0.3))
    a = min(a_in, a_out)
    if a <= 0:
        return img
    lay = caption_layer(title, sub)
    e = 1 - (1 - a_in) ** 3
    x = int((70 - 40 * (1 - e)) * S); y = int(H - lay.size[1] - 70 * S) if pos == "bl" else int((H - lay.size[1]) / 2)
    if a < 1:
        lay = lay.copy(); lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    img = img.convert("RGBA"); img.alpha_composite(lay, (x, y))
    return img.convert("RGB")


# ---------------------------------------------------------------- picture helpers
def zoom(img, z, cx=0.5, cy=0.5):
    if abs(z - 1) < 1e-4:
        return img
    w, h = W / z, H / z
    x0 = min(max(cx * W - w / 2, 0), W - w); y0 = min(max(cy * H - h / 2, 0), H - h)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))


def vignette():
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    return np.clip(1.0 - 0.28 * np.clip(r - 0.55, 0, None) ** 1.6, 0, 1)[..., None].astype(np.float32)


VIG = None


def finish(img, flash=0.0, fade=1.0):
    global VIG
    if VIG is None:
        VIG = vignette()
    a = np.asarray(img).astype(np.float32) * VIG
    if flash > 0:
        a = a + (255 - a) * flash
    if fade < 1:
        a = a * fade
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- timeline
# shot: (t0, t1, kind, args); kind 'clip' = (name, first clip frame, title, sub, zoom0, zoom1, flash)
TL = []


def shot(k0, k1, name, start, title="", sub="", z=(1.0, 1.07), flash=True, cx=0.5, cy=0.5, speed=1.0, dip=0.0):
    TL.append((B(k0), B(k1), "clip", dict(name=name, start=start, title=title, sub=sub, z=z, flash=flash, cx=cx, cy=cy, speed=speed, dip=dip)))


# opening (user 2026-11-17: teaser montage): one bar per shot on the quiet intro of the song, short dips to black, then the title on black
TL.append((0.0, B(0), "black", {}))
shot(0, 1, "lava", 150, z=(1.12, 1.04), flash=False, dip=0.25)
shot(1, 2, "m_night", 90, z=(1.0, 1.08), flash=False, dip=0.25)
shot(2, 3, "swords_n", 205, z=(1.35, 1.45), flash=False, dip=0.25, cx=0.52, cy=0.44)
shot(3, 4, "church", 60, z=(1.1, 1.0), flash=False, dip=0.25)
shot(4, 5, "tlapse", 420, z=(1.0, 1.06), flash=False, dip=0.25)
TL.append((B(5), B(7), "title", {}))
# loud part 1: light
shot(7, 9, "castle", 20, "DYNAMIC LIGHTING", "torches, lava and your sword light the world")
shot(9, 11, "church", 30, "REAL 3D SHADOWS", "statues, benches and tables cast their true shape")
shot(11, 13, "lava", 60, "HEAT HAZE  ·  LIGHT SHAFTS", "")
shot(13, 15, "water", 30, "WATER REFLECTIONS", "")
shot(15, 17, "intro_n", 330, "SUN SHADOWS", "every house, tree and figure", z=(1.08, 1.0))
# calm part 1: day and night
shot(17, 20, "tlapse", 20, "DAY  &  NIGHT", "the sun moves across the sky, windows glow after dark", z=(1.0, 1.04), flash=False, speed=1.9)
shot(20, 23, "m_night", 60, "NIGHT LIGHTS", "lamp-lit doors and windows", flash=False)


# loud part 2: the four swords, original | 2.0 (same input, swords_o = no light / no effects, swords_n = 2.0); a charged swing per sword
for k, (nm, sub) in enumerate((("ICE SWORD", "Sword Effects: coloured arcs, sparks and light"), ("THUNDER SWORD", ""), ("FIRE SWORD", ""), ("GAIA SWORD", ""))):
    TL.append((B(23 + 2 * k), B(25 + 2 * k), "split", dict(left="swords_o", right="swords_n", start=190 + 330 * k, crop=(700, 788), cx=1000, cy=470, title=nm, sub=sub)))


def render_intro(t):
    """B0..B4: original 4:3 small and centred (caption '1992'); B4..B5.5: it opens to 16:9 and blends into 2.0; B6: title"""
    if t < B(0) - 0.4:
        return Image.new("RGB", (W, H))
    i = int(max(0.0, t - B(0) + 0.4) * 60)
    fo, fn = frame("intro_o", i), frame("intro_n", i)
    # the original picture inside its clip frame (measured bounding box at 1920x1080: the game's own original display incl. the status bar)
    bx = [v * W / 1920 for v in (188, 21, 1731, 894)]
    org_full = fo.crop(bx)
    u = min(1.0, max(0.0, (t - B(4)) / (1.5 * P)))
    e = u * u * (3 - 2 * u)
    s0 = 0.58                                      # box width share at the start
    bw = W * (s0 + (1 - s0) * e)
    asp = (bx[2] - bx[0]) / (bx[3] - bx[1]); asp = asp + (W / H - asp) * e
    bh = bw / asp
    canvas = Image.new("RGB", (W, H), (8, 8, 10))
    org = org_full.resize((int(bw), int(bh)), Image.BICUBIC)
    box = org
    if e > 0:
        cw = H * bw / bh
        src = fn.crop(((W - cw) / 2, 0, (W + cw) / 2, H)).resize((int(bw), int(bh)), Image.BICUBIC)
        box = Image.blend(org, src, min(1.0, e * 1.3))
    canvas.paste(box, (int((W - bw) / 2), int((H - bh) / 2)))
    a0 = min(1.0, max(0.0, (t - B(0) + 0.4) / 0.8))
    img = finish(canvas, fade=a0)
    if t < B(4):
        img = put_caption(img, "LANDSTALKER", "Mega Drive, 1992", t, B(0) + 0.6, B(4) - 0.2)
    if t >= B(5.2):
        img = title_card(img, t - B(5.2))
    return img


def title_card(img, dt):
    a = min(1.0, dt / 0.6)
    ft = font("NotoSans-Thin.ttf", 132); fb = font("NotoSans-Medium.ttf", 132); fs = font("NotoSans-Regular.ttf", 30)
    t1, t2 = "PROJECT FRIDAY ", "2.0"
    tr = 14 * S
    w = text_w(t1, ft, tr) + text_w(t2, fb, tr)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    x0 = (W - w) / 2; y0 = H / 2 - 110 * S
    x = spaced(d, (x0, y0), t1, ft, (255, 255, 255, 255), tr)
    spaced(d, (x, y0), t2, fb, AMBER + (255,), tr)
    sub = "LANDSTALKER  ·  RECOMPILED  ·  REIMAGINED"
    spaced(d, ((W - text_w(sub, fs, 6 * S)) / 2, y0 + 175 * S), sub, fs, (230, 230, 230, 255), 6 * S)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(18 * S)).point(lambda v: v * 0.9))
    lay = Image.alpha_composite(sh, lay)
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    dim = Image.new("RGBA", (W, H), (0, 0, 0, int(110 * a)))
    img = img.convert("RGBA"); img.alpha_composite(dim); img.alpha_composite(lay)
    return img.convert("RGB")


def render_clip(t, t0, t1, a):
    i = a["start"] + (t - t0) * 60 * a["speed"]
    img = frame(a["name"], i)
    u = (t - t0) / (t1 - t0); z0, z1 = a["z"]
    img = zoom(img, z0 + (z1 - z0) * (u * u * (3 - 2 * u) * 0.4 + u * 0.6), a["cx"], a["cy"])
    fl = max(0.0, 1 - (t - t0) / 0.12) * 0.55 if a["flash"] else 0.0
    fd = 1.0
    if a.get("dip"):
        fd = min(1.0, (t - t0) / a["dip"], (t1 - t) / a["dip"])
    img = finish(img, flash=fl, fade=fd)
    if a["title"]:
        img = put_caption(img, a["title"], a["sub"], t, t0, t1)
    return img


def label(img, text, x, y, a=1.0, f="NotoSans-Regular.ttf", size=30, track=8, color=(255, 255, 255)):
    fo = font(f, size)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    w = text_w(text, fo, track * S)
    spaced(d, (x - w / 2, y), text, fo, color + (int(255 * a),), track * S)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(8 * S)).point(lambda v: v * 0.8))
    img = img.convert("RGBA"); img.alpha_composite(sh); img.alpha_composite(lay)
    return img.convert("RGB")


def render_split(t, t0, t1, a):
    """two clips of the same input side by side, each cropped around Nigel (cx, cy in 1920 x 1080 clip pixels), divider + labels + sword name"""
    i = a["start"] + (t - t0) * 60
    zw, zh = a["crop"]
    cx, cy = a["cx"] * W / 1920, a["cy"] * H / 1080
    zw, zh = zw * W / 1920, zh * H / 1080
    box = (cx - zw / 2, cy - zh / 2, cx + zw / 2, cy + zh / 2)
    half = W // 2
    out = Image.new("RGB", (W, H))
    for k, name in enumerate((a["left"], a["right"])):
        im = frame(name, i).resize((half, H), Image.BICUBIC, box=box)
        out.paste(im, (k * half, 0))
    fl = max(0.0, 1 - (t - t0) / 0.12) * 0.45
    out = finish(out, flash=fl)
    d = ImageDraw.Draw(out)
    d.rectangle([half - int(2 * S), 0, half + int(2 * S), H], fill=AMBER)
    ain = min(1.0, (t - t0) / 0.3)
    out = label(out, "ORIGINAL", half / 2, 60 * S, ain, size=30)
    out = label(out, "PROJECT FRIDAY 2.0", half * 1.5, 60 * S, ain, size=30, color=AMBER)
    if a.get("title"):
        out = put_caption(out, a["title"], a.get("sub", ""), t, t0, t1)
    return out


def render(t):
    for t0, t1, kind, a in TL:
        if t0 <= t < t1:
            if kind == "black":
                return Image.new("RGB", (W, H))
            if kind == "title":
                return title_card(Image.new("RGB", (W, H)), t - t0)
            if kind == "split":
                return render_split(t, t0, t1, a)
            return render_intro(t) if kind == "intro" else render_clip(t, t0, t1, a)
    return Image.new("RGB", (W, H))


def main():
    ta = float(arg("--from", 0)); tb = float(arg("--to", TL[-1][1]))
    name = arg("--out", "preview" if PREVIEW else "trailer2")
    o = os.path.join(OUT, name + ".mp4")
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-ss", str(ta), "-t", str(tb - ta), "-i", SONG, "-af", f"afade=t=out:st={max(0, tb - ta - 1.0)}:d=1.0",
                            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "256k", "-shortest", o], stdin=subprocess.PIPE)
    n = int((tb - ta) * FPS)
    for k in range(n):
        t = ta + k / FPS
        enc.stdin.write(render(t).tobytes())
        if k % (FPS * 2) == 0:
            print(f"[render] {t:5.1f} s / {tb:.1f} s", flush=True)
    enc.stdin.close(); enc.wait()
    print("[render] ->", o)


if __name__ == "__main__":
    main()
