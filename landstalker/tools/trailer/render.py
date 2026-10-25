#!/usr/bin/env python3
"""Trailer renderer (90s video game commercial style). Recipe only: input and output live in ~/.landstalker_trailer.

Needs: clips from capture.py, ~/.landstalker_trailer/music/song.mp3 (the user's music), crtpipe (cc -O2 -o ~/.landstalker_trailer/crtpipe crtpipe.c -lm).
  ~/.landstalker_trailer/venv/bin/python render.py [--preview] [--from SEC] [--to SEC]
Output: ~/.landstalker_trailer/trailer.mp4 (preview: trailer_preview.mp4, 960x540 30 fps)
The game picture goes through the game's own display filters (tools/display_core.c via crtpipe), all other effects are drawn here.
"""
import os, sys, glob, math, random, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.expanduser("~/.landstalker_trailer")
SONG = os.path.join(OUT, "music", "song.mp3")
CRTPIPE = os.path.join(OUT, "crtpipe")
FONT_BI = "/usr/share/fonts/noto/NotoSans-BlackItalic.ttf"
FONT_B = "/usr/share/fonts/noto/NotoSans-Black.ttf"
FONT_MONO = "/usr/share/fonts/noto/NotoSansMono-Black.ttf"

PREVIEW = "--preview" in sys.argv
W, H, FPS = (960, 540, 30) if PREVIEW else (1920, 1080, 60)
S = H / 1080.0                       # text scale
SW = 398                             # game picture width (16:9 at 224 lines); 4:3 clips are padded to it
DUR = 85.73
P, PH = 1.4275, 1.23                 # bar length / first bar of the song (measured)


def B(k):
    return PH + k * P


def arg(name, default):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


# ---------------------------------------------------------------- game frames
class Clip:
    def __init__(self, name):
        d = os.path.join(OUT, "clips", name)
        self.win = bool(glob.glob(os.path.join(d, "winshot_*.bmp")))
        fs = glob.glob(os.path.join(d, "winshot_*.bmp" if self.win else "shot_*.png"))
        key = (lambda f: int(os.path.basename(f)[8:-4])) if self.win else (lambda f: int(os.path.basename(f)[5:11]))
        self.files = sorted(fs, key=key)
        if not self.files:
            raise SystemExit(f"clip {name}: no frames, run capture.py clip {name}")
        self.cache = {}

    def __len__(self):
        return len(self.files)

    def get(self, i):
        i = max(0, min(len(self.files) - 1, int(i)))
        if i in self.cache:
            return self.cache[i]
        im = Image.open(self.files[i]).convert("RGB")
        if self.win:                                   # window picture: crop the 16:9 game picture (non-black rows)
            a = np.asarray(im)
            rows = np.where(a.max(axis=(1, 2)) > 0)[0]
            y0 = rows[0] if len(rows) else 0
            h = int(round(a.shape[1] * 9 / 16))
            a = a[y0:y0 + h]
            v = ("win", a)
        else:
            a = np.asarray(im)
            if a.shape[1] < SW:                        # 4:3 picture: black margins
                p = np.zeros((224, SW, 3), np.uint8)
                o = (SW - a.shape[1]) // 2
                p[:, o:o + a.shape[1]] = a
                a = p
            v = ("game", a)
        if len(self.cache) > 64:
            self.cache.clear()
        self.cache[i] = v
        return v


CLIPS = {}


def clip(name):
    if name not in CLIPS:
        CLIPS[name] = Clip(name)
    return CLIPS[name]


class CRT:
    procs = {}

    @classmethod
    def render(cls, a, fx):
        if fx not in cls.procs:
            cls.procs[fx] = subprocess.Popen([CRTPIPE, str(SW), str(W), str(H), str(fx)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        p = cls.procs[fx]
        bgra = np.empty((224, SW, 4), np.uint8)
        bgra[..., 0], bgra[..., 1], bgra[..., 2], bgra[..., 3] = a[..., 2], a[..., 1], a[..., 0], 255
        p.stdin.write(bgra.tobytes()); p.stdin.flush()
        o = np.frombuffer(p.stdout.read(W * H * 4), np.uint8).reshape(H, W, 4)
        return o[..., 2::-1].copy()


def picture(v, fx):
    kind, a = v
    if kind == "game":
        return CRT.render(a, fx)
    im = Image.fromarray(a).resize((W, H), Image.NEAREST)  # window picture (overlays): scale up, light scanlines
    o = np.asarray(im).astype(np.uint16)
    o[1::3] = o[1::3] * 3 // 4
    return o.astype(np.uint8)


# ---------------------------------------------------------------- effects
rng = np.random.default_rng(7)
NOISE = [rng.integers(0, 255, (H // 4, W // 4), dtype=np.uint8) for _ in range(8)]


def vhs(img, t, k=1.0):
    o = img.astype(np.int16)
    sh = max(1, int(6 * S * k))
    o[..., 0] = np.roll(o[..., 0], sh, axis=1)            # chroma bleed
    o[..., 2] = np.roll(o[..., 2], -sh, axis=1)
    n = np.kron(NOISE[int(t * 30) % 8], np.ones((4, 4), np.uint8))[:H, :W].astype(np.int16) - 128
    o += (n[..., None] * 0.10 * k).astype(np.int16)
    yb = int((t * 0.37 % 1.0) * H * 1.4) - int(H * 0.2)   # tracking band rolling down
    for y in range(max(0, yb), min(H, yb + int(40 * S))):
        o[y] = np.roll(o[y], int(10 * S * k * math.sin(y * 0.7 + t * 40)), axis=0)
        o[y] += int(25 * k)
    o = o * np.array([1.04, 1.0, 0.92])                    # warm, a bit washed out
    return np.clip(o, 0, 255).astype(np.uint8)


def rgbsplit(img, px):
    o = img.copy()
    o[..., 0] = np.roll(img[..., 0], px, axis=1)
    o[..., 2] = np.roll(img[..., 2], -px, axis=1)
    return o


def zoom(img, z, cx=0.5, cy=0.5):
    if abs(z - 1.0) < 1e-3:
        return img
    im = Image.fromarray(img)
    w, h = W / z, H / z
    x0, y0 = (W - w) * cx, (H - h) * cy
    return np.asarray(im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h)))


def flash(img, a, col=(255, 255, 255)):
    if a <= 0:
        return img
    return (img * (1 - a) + np.array(col) * a).astype(np.uint8)


def dim(img, a):
    return (img * a).astype(np.uint8)


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def beat_punch(t, t0, t1, every=1.0, amount=0.035):
    """zoom punch on every bar (or half bar) inside [t0, t1)"""
    if not (t0 <= t < t1):
        return 1.0
    k = (t - PH) / (P * every)
    f = k - math.floor(k)
    return 1.0 + amount * math.exp(-f * P * every * 9)


# ---------------------------------------------------------------- text
GRAD = {
    "chrome": [(0.0, (255, 255, 255)), (0.45, (140, 190, 255)), (0.52, (30, 30, 90)), (0.60, (255, 230, 150)), (1.0, (255, 140, 20))],
    "fire":   [(0.0, (255, 255, 160)), (0.5, (255, 190, 0)), (1.0, (230, 30, 0))],
    "neon":   [(0.0, (120, 255, 255)), (0.5, (60, 140, 255)), (1.0, (255, 60, 220))],
    "white":  [(0.0, (255, 255, 255)), (1.0, (220, 220, 230))],
    "green":  [(0.0, (230, 255, 120)), (0.5, (60, 230, 60)), (1.0, (0, 120, 40))],
}
_tcache = {}


def gradient(h, stops):
    ys = np.linspace(0, 1, h)
    out = np.zeros((h, 3))
    for c in range(3):
        out[:, c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])
    return out.astype(np.uint8)


def text_img(text, size, grad="chrome", font=FONT_BI, outline=None, shadow=True, glow=None):
    key = (text, size, grad, font, outline, shadow, glow)
    if key in _tcache:
        return _tcache[key]
    size = int(size * S)
    f = ImageFont.truetype(font, size)
    ol = int((outline if outline is not None else size * 0.09))
    l, t, r, b = f.getbbox(text, stroke_width=ol)
    pad = ol + int(size * 0.25)
    w, h = r - l + 2 * pad, b - t + 2 * pad
    org = (pad - l, pad - t)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text(org, text, font=f, fill=255)
    stroke = Image.new("L", (w, h), 0)
    ImageDraw.Draw(stroke).text(org, text, font=f, fill=255, stroke_width=ol, stroke_fill=255)
    tb = mask.getbbox() or (0, 0, w, h)
    g = gradient(tb[3] - tb[1], GRAD[grad])
    fill = np.zeros((h, w, 3), np.uint8)
    fill[tb[1]:tb[3]] = g[:, None, :]
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if glow:
        gl = stroke.filter(ImageFilter.GaussianBlur(size * 0.12))
        out.paste(Image.new("RGBA", (w, h), glow + (255,)), (0, 0), gl)
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", (w, h), (0, 0, 0, 200)), (int(size * 0.07), int(size * 0.07)), stroke)
        out = Image.alpha_composite(out, sh)
    out.paste(Image.new("RGBA", (w, h), (10, 10, 30, 255)), (0, 0), stroke)
    out.paste(Image.fromarray(fill).convert("RGBA"), (0, 0), mask)
    _tcache[key] = out
    return out


def star_img(text, size=150, rot=-14):
    key = ("star", text, size)
    if key in _tcache:
        return _tcache[key]
    r = int(size * S)
    im = Image.new("RGBA", (2 * r + 8, 2 * r + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = []
    for i in range(32):
        a = math.pi * 2 * i / 32
        rr = r if i % 2 == 0 else r * 0.78
        pts.append((r + 4 + rr * math.cos(a), r + 4 + rr * math.sin(a)))
    d.polygon(pts, fill=(255, 230, 0, 255), outline=(200, 0, 0, 255), width=max(2, int(6 * S)))
    t = text_img(text, size * 0.42, "fire", FONT_B, shadow=False)
    t = t.rotate(rot, Image.BICUBIC, expand=True)
    im.alpha_composite(t, (r + 4 - t.width // 2, r + 4 - t.height // 2))
    _tcache[key] = im
    return im


def place(frame, im, x, y, scale=1.0, alpha=1.0, rot=0.0, anchor="mm"):
    if alpha <= 0.01 or scale <= 0.01:
        return
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    ax = {"l": 0, "m": 0.5, "r": 1}[anchor[0]]
    ay = {"t": 0, "m": 0.5, "b": 1}[anchor[1]]
    frame.alpha_composite(im, (int(x * W - im.width * ax), int(y * H - im.height * ay)))


def pop(t, t0, t1, fade=0.15):
    """scale / alpha of a label shown from t0 to t1: overshoot pop in, quick fade out"""
    if t < t0 or t >= t1:
        return 0.0, 0.0
    a = (t - t0) / 0.18
    sc = 1.0 + 0.5 * math.exp(-a * 3.5) * math.cos(a * 4) if a < 3 else 1.0
    al = min(1.0, (t - t0) / 0.06) * min(1.0, (t1 - t) / fade)
    return sc, al


def slide(t, t0, t1, frm=-0.6):
    """x offset of a label sliding in from the side"""
    a = ease((t - t0) / 0.22)
    b = ease((t1 - t) / 0.18)
    return frm * (1 - a) + (-frm) * (1 - b) if t < t1 else 9


# ---------------------------------------------------------------- timeline
FEATURES = [  # (bar, clip, title, subtitle, grad)
    (23, "quickgaia", "QUICK ITEMS!", "ITEMS ON THE Y AND B BUTTONS", "fire"),
    (25.5, "livegaia", "LIVE GAIA EFFECT!", "THE ACTION NEVER STOPS", "neon"),
    (28, "qequip", "QUICK EQUIP!", "SWAP SWORDS ON THE FLY", "chrome"),
    (31, "ffwd", "FAST FORWARD!", "UP TO 4X SPEED", "fire"),
]
MONTAGE = [("m_jypta", 3), ("m_forest", 2), ("m_beach", 2), ("m_ryuma", 3), ("m_fight", 2), ("m_stream", 2), ("m_woods", 3), ("m_ruins", 2), ("harbour", 3)]
MORE = ["QUICK SAVE & QUICK LOAD", "REAL DROP SHADOWS", "DIFFICULTY SETTINGS", "REMAPPABLE CONTROLS", "MUSIC & EFFECTS VOLUME", "FULLSCREEN & SCALING MODES", "MAP BEHIND TEXT BOXES", "ITEM INFO IN THE MENU"]


def src_index(t, t0, speed=1.0, offset=0):
    return offset + (t - t0) * 60 * speed


def frame_at(t):
    """returns a PIL RGBA frame for time t"""
    lab = []          # (callable(frame)) overlays
    fx = 3            # CRT Pro (the game's default)
    punch = 1.0
    fl = 0.0

    # ---- S0 / S1: VHS opening, original 4:3 picture
    if t < B(0):
        img = np.zeros((H, W, 3), np.uint8)
        n = np.kron(NOISE[int(t * 60) % 8], np.ones((4, 4), np.uint8))[:H, :W]
        img[:] = (n[..., None] * 0.8).astype(np.uint8)
        img = vhs(img, t, 1.5)
        lab.append(lambda fr: place(fr, text_img("PLAY ▶", 60, "white", FONT_MONO, shadow=False, outline=4), 0.06, 0.08, anchor="lt"))
    elif t < B(6):
        c = clip("jypta_o")
        img = picture(c.get(src_index(t, B(0))), 0)
        img = vhs(img, t, 0.8)
        img = flash(img, max(0, 1 - (t - B(0)) / 0.5) * 0.8, (0, 0, 0))
        if t < B(0) + 2.5:
            lab.append(lambda fr: place(fr, text_img("PLAY ▶", 60, "white", FONT_MONO, shadow=False, outline=4), 0.06, 0.08, anchor="lt"))
        lines = [(B(0), B(2), "1992.", None), (B(2), B(4), "A LEGEND WAS BORN", "ON THE SEGA MEGA DRIVE"), (B(4), B(6), "...BUT IT WAS STUCK", "IN A 4:3 BOX")]
        for a0, a1, l1, l2 in lines:
            if a0 <= t < a1:
                sc, al = pop(t, a0, a1)
                lab.append(lambda fr, l1=l1, sc=sc, al=al: place(fr, text_img(l1, 120, "white", FONT_B), 0.5, 0.13, sc, al))
                if l2:
                    sc2, al2 = pop(t, a0 + 0.35, a1)
                    lab.append(lambda fr, l2=l2, sc2=sc2, al2=al2: place(fr, text_img(l2, 70, "chrome"), 0.5, 0.25, sc2, al2))
    # ---- S2: the slow 4:3 -> 16:9 -> full height reveal
    elif t < B(11):
        i = src_index(t, B(6))
        _, w = clip("ryuma_w").get(i)
        _, o = clip("ryuma_o").get(i)
        m = int(round(39 * ease((t - B(7)) / (P * 1.6))))          # margins open over ~2.3 s
        yr = int(150 + 74 * ease((t - B(8.8)) / (P * 0.9)))   # then the band at the bottom fills
        a = w.copy()
        a[:, :39 - m] = 0
        a[:, SW - 39 + m:] = 0
        a[yr:] = o[yr:]
        k = ease((t - B(7)) / (P * 1.2))
        if k < 1:
            img = vhs(picture(("game", a), 0), t, 0.8 * (1 - k))
            if k > 0:
                img = (img * (1 - k) + picture(("game", a), 3) * k).astype(np.uint8)
        else:
            img = picture(("game", a), 3)
        if B(6) <= t < B(7):
            sc, al = pop(t, B(6), B(7))
            lab.append(lambda fr: place(fr, text_img("UNTIL NOW.", 150, "chrome"), 0.5, 0.5, sc, al))
        if B(7.6) <= t < B(9.4):
            sc, al = pop(t, B(7.6), B(9.4))
            lab.append(lambda fr: place(fr, text_img("WIDESCREEN 16:9!", 135, "chrome"), 0.5, 0.8, sc, al, rot=4))
            lab.append(lambda fr: place(fr, star_img("NEW!"), 0.86, 0.22, sc, al))
        if B(9.4) <= t < B(11):
            sc, al = pop(t, B(9.4), B(11))
            lab.append(lambda fr: place(fr, text_img("FULL HEIGHT!", 135, "fire"), 0.5, 0.8, sc, al, rot=4))
            lab.append(lambda fr: place(fr, text_img("NO MORE BLACK BARS", 60, "white", FONT_B), 0.5, 0.93, 1, al))
        fl = max(0, 1 - (t - B(7.6)) / 0.25) * 0.5 if t >= B(7.6) else 0
    # ---- S3: title slam
    elif t < B(13):
        img = dim(picture(clip("title").get(src_index(t, B(11))), 3), 0.45)
        punch = 1.0 + 0.08 * math.exp(-(t - B(11)) * 4)
        fl = max(0, 1 - (t - B(11)) / 0.35)
        sc, al = pop(t, B(11), B(13) + 0.2)
        lab.append(lambda fr: place(fr, text_img("PROJECT FRIDAY", 210, "chrome", glow=(255, 60, 200)), 0.5, 0.42, sc, al, rot=3))
        sc2, al2 = pop(t, B(11.5), B(13) + 0.2)
        lab.append(lambda fr: place(fr, text_img("LANDSTALKER – RECOMPILED!", 80, "fire"), 0.5, 0.64, sc2, al2))
    # ---- S4: the CRT filters, one per bar
    elif t < B(17):
        k = int((t - B(13)) / P)
        modes = [(1, "SCANLINES"), (2, "CRT"), (3, "CRT PRO"), (4, "CRT CURVED")]
        fx, name = modes[min(k, 3)]
        img = picture(clip("crt").get(src_index(t, B(13))), fx)
        x = t - B(13 + k)
        if x < 0.12 and k > 0:                                   # wipe from the previous mode
            prev = picture(clip("crt").get(src_index(t, B(13))), modes[k - 1][0])
            cut = int(W * x / 0.12)
            img[:, cut:] = prev[:, cut:]
            img[:, max(0, cut - int(8 * S)):cut] = 255
        punch = beat_punch(t, B(13), B(17), 1.0, 0.03)
        sc, al = pop(t, B(13), B(17))
        lab.append(lambda fr: place(fr, text_img("CRT FILTERS!", 120, "neon"), 0.04, 0.1, 1, al, anchor="lt"))
        sc2, al2 = pop(t, B(13 + k), B(14 + k))
        lab.append(lambda fr: place(fr, text_img(name, 100, "chrome"), 0.5, 0.84, sc2, al2, rot=3))
    # ---- S5: quality of life (calm part of the song)
    elif t < B(23):
        k = int((t - B(17)) / (2 * P))
        cl, title, sub = [("options", "ALL-NEW OPTIONS MENU", "VIDEO • AUDIO • GAMEPLAY • CONTROLS"),
                          ("buyqty", "BUY IN BULK!", "CHOOSE HOW MANY YOU WANT"),
                          ("menu", "SMARTER MENUS!", "BACK WITH B • ITEM INFO")][min(k, 2)]
        t0 = B(17 + 2 * k)
        img = picture(clip(cl).get(src_index(t, t0) + (120 if cl == "options" else 0)), 3)
        img = zoom(img, 1.0 + 0.06 * (t - t0) / (2 * P))
        fl = max(0, 1 - (t - t0) / 0.2) * 0.6
        if t < B(17) + 1.2:
            sc0, al0 = pop(t, B(17), B(17) + 1.2)
            lab.append(lambda fr: place(fr, text_img("QUALITY OF LIFE", 130, "green"), 0.5, 0.5, sc0, al0))
        else:
            sc, al = pop(t, max(t0, B(17) + 1.2), t0 + 2 * P)
            lab.append(lambda fr: place(fr, text_img(title, 110, "chrome"), 0.5, {"menu": 0.82, "options": 0.60}.get(cl, 0.13), sc, al, rot=3))
            lab.append(lambda fr: place(fr, text_img(sub, 52, "white", FONT_B), 0.5, {"menu": 0.94, "options": 0.72}.get(cl, 0.25), 1, al))
    # ---- S6: action features, two bars each
    elif t < B(33):
        k = max(j for j, f in enumerate(FEATURES) if t >= B(f[0]))
        bar, cl, title, sub, gr = FEATURES[k]
        t0 = B(bar)
        t1 = B(FEATURES[k + 1][0]) if k + 1 < len(FEATURES) else B(33)
        sp = 4.0 if cl == "ffwd" else 1.0
        img = picture(clip(cl).get(src_index(t, t0, sp)), 3)
        fl = max(0, 1 - (t - t0) / 0.2) * 0.7
        if cl == "ffwd":
            img = rgbsplit(img, int(4 * S))
            lab.append(lambda fr: place(fr, text_img("▶▶ 4X", 90, "white", FONT_MONO, outline=5), 0.95, 0.12, 1, 1 if int(t * 4) % 2 == 0 else 0.4, anchor="rt"))
        sc, al = pop(t, t0, t1)
        xo = slide(t, t0, t1, -0.7 if k % 2 == 0 else 0.7)
        ty = 0.17 if cl == "qequip" else 0.78
        lab.append(lambda fr: place(fr, text_img(title, 125, gr), 0.5 + xo, ty, 1, al, rot=4))
        lab.append(lambda fr: place(fr, text_img(sub, 54, "white", FONT_B), 0.5 - xo, ty + 0.13, 1, al))
        if k == 2:
            lab.append(lambda fr: place(fr, star_img("NEW!"), 0.88, 0.22, sc, al))
    # ---- S7: ...and more (calm part)
    elif t < B(38):
        img = dim(picture(clip("harbour").get(src_index(t, B(33))), 3), 0.55)
        sc, al = pop(t, B(33), B(38))
        lab.append(lambda fr: place(fr, text_img("...AND MORE!", 120, "fire"), 0.5, 0.15, sc, al, rot=3))
        n = len(MORE)
        for j, line in enumerate(MORE):
            tj = B(33) + 0.35 + j * (5 * P - 0.8) / n
            if t >= tj:
                xo = (1 - ease((t - tj) / 0.25)) * (-0.8 if j % 2 == 0 else 0.8)
                lab.append(lambda fr, line=line, j=j, xo=xo: place(fr, text_img("• " + line, 58, "chrome"), 0.5 + xo, 0.29 + j * 0.083, 1, al))
    # ---- S8: montage on the beat
    elif t < B(49):
        hb = (t - B(38)) / (P / 2)
        acc = 0
        for cl, d in MONTAGE:
            if hb < acc + d:
                break
            acc += d
        t0 = B(38) + acc * P / 2
        img = picture(clip(cl).get(src_index(t, t0)), 3)
        punch = 1.0 + 0.05 * math.exp(-(t - t0) * 7)
        fl = max(0, 1 - (t - t0) / 0.12) * 0.6
        if t - t0 < 0.07:
            img = rgbsplit(img, int(14 * S))
        punches = [(38, 40.5, "STATICALLY RECOMPILED!", "68000 MACHINE CODE TURNED INTO C", "chrome"),
                   (40.5, 43, "BUILT FROM YOUR OWN ROM!", "NO GAME DATA INCLUDED", "fire"),
                   (43, 46, "STEAM DECK • LINUX • WINDOWS", "ONE APPIMAGE. ONE ZIP.", "neon"),
                   (46, 49, "THE ADVENTURE IS BACK!", None, "chrome")]
        for a0, a1, l1, l2, gr in punches:
            if B(a0) <= t < B(a1):
                sc, al = pop(t, B(a0), B(a1))
                lab.append(lambda fr, l1=l1, gr=gr, sc=sc, al=al: place(fr, text_img(l1, 115, gr), 0.5, 0.80, sc, al, rot=3))
                if l2:
                    lab.append(lambda fr, l2=l2, al=al: place(fr, text_img(l2, 52, "white", FONT_B), 0.5, 0.92, 1, al))
    # ---- S9: end card
    else:
        img = dim(picture(clip("end").get(src_index(t, B(49), 0.5)), 3), 0.42)   # slow motion
        fl = max(0, 1 - (t - B(49)) / 0.4)
        sc, al = pop(t, B(49), 99)
        lab.append(lambda fr: place(fr, text_img("PROJECT FRIDAY", 200, "chrome", glow=(255, 60, 200)), 0.5, 0.30, sc, al, rot=3))
        sc2, al2 = pop(t, B(50), 99)
        lab.append(lambda fr: place(fr, text_img("LANDSTALKER FOR PC & STEAM DECK", 70, "fire"), 0.5, 0.49, sc2, al2))
        sc3, al3 = pop(t, B(51), 99)
        lab.append(lambda fr: place(fr, text_img("BRING YOUR OWN ROM", 64, "green"), 0.5, 0.62, sc3, al3))
        lab.append(lambda fr: place(fr, text_img("github.com/cmdrlucid/Project-Friday", 58, "white", FONT_B), 0.5, 0.71, sc3, al3))
        sc4, al4 = pop(t, B(52), 99)
        fine = ["Fan project, non-commercial. Requires your own Landstalker ROM - no game data is included.",
                "Not affiliated with or endorsed by SEGA or Climax Entertainment. Landstalker © SEGA 1992. Windows build experimental.",
                "Music: \"Let's Go on an Adventure\" by Motoaki Takenouchi from the original Landstalker soundtrack."]
        for j, line in enumerate(fine):
            lab.append(lambda fr, line=line, j=j: place(fr, text_img(line, 24, "white", FONT_B, outline=2, shadow=False), 0.5, 0.86 + j * 0.035, 1, al4 * 0.85))

    img = zoom(img, punch)
    img = flash(img, fl)
    fr = Image.fromarray(img).convert("RGBA")
    for f in lab:
        f(fr)
    if t > DUR - 2.3:                                            # fade out with the music
        a = ease((DUR - t) / 2.3)
        fr = Image.fromarray(dim(np.asarray(fr.convert("RGB")), a)).convert("RGBA")
    return fr


def main():
    t_from, t_to = arg("--from", 0.0), arg("--to", DUR)
    name = "trailer_preview.mp4" if PREVIEW else "trailer.mp4"
    if "--from" in sys.argv or "--to" in sys.argv:
        name = name.replace(".mp4", f"_{int(t_from)}-{int(t_to)}.mp4")
    out = os.path.join(OUT, name)
    noise = os.path.join(OUT, "work", "static.wav")                # tape noise for the first bar
    os.makedirs(os.path.dirname(noise), exist_ok=True)
    with wave.open(noise, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
        n = int(44100 * B(0))
        env = np.minimum(1, np.linspace(1.0, 0, n) * 1.6)
        s = (np.random.default_rng(1).normal(0, 0.18, n) * env * 32767).astype(np.int16)
        w.writeframes(np.repeat(s, 2).tobytes())
    ff = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
          "-ss", str(t_from), "-t", str(t_to - t_from), "-i", SONG, "-ss", str(t_from), "-i", noise,
          "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=first:normalize=0[a]", "-map", "0:v", "-map", "[a]",
          "-c:v", "libx264", "-preset", "medium" if not PREVIEW else "veryfast", "-crf", "17" if not PREVIEW else "23", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(ff, stdin=subprocess.PIPE)
    n0, n1 = int(t_from * FPS), int(t_to * FPS)
    for n in range(n0, n1):
        t = n / FPS
        p.stdin.write(frame_at(t).convert("RGB").tobytes())
        if (n - n0) % (FPS * 5) == 0:
            print(f"[render] {t:5.1f} s / {t_to:.1f} s", flush=True)
    p.stdin.close(); p.wait()
    print("[render] wrote", out)


if __name__ == "__main__":
    main()
