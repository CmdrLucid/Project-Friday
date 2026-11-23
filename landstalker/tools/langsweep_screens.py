#!/usr/bin/env python3
"""langsweep_screens.py [lang ...]  -- per-language picture sweep of everything OUTSIDE the options menu that shows our own text
(title subtitle during fades, file select, on-screen messages / equipment words, room map hint).  Python 3 stdlib + PIL: run it with
~/Project-Friday-Test/hdvenv/bin/python3 (that venv has PIL; system python has not).  Needs build/landstalker (current build).
Works ONLY on a copy of the ROM + save in ~/Project-Friday-Test/lktest/langsweep/rom2/ (never touches the user's save).
Output: ~/Project-Friday-Test/lktest/langsweep/screens/<lang>/ (shots), screens/sheet_<lang>_{a,b,c}.png (title+file select, OSD, map), ../screens.html (all).
Steps per language (LANDSTALKER_LANG=<code>, SDL dummy video + audio):
  a) title strip: headless, game-picture shots every 10 frames 780..1000, Start pressed at 950 (input script), subtitle row checked for
     any visible subtitle pixels (en / en_tone keep the English one)
  b) file select: shots 1010..1100 after Start
  c) OSD messages: window shots (no --headless) with LANDSTALKER_OSDSAY, one key per 15 frames, bottom-left box cropped
  d) room map: LANDSTALKER_MAPSHOT (only works when the save is inside a dungeon room; skipped quietly otherwise)
Languages: en de fr es it ru uk ko en_tone (+ ja if build/lang/ja.bin exists)."""
import os, sys, subprocess, shutil, glob, html, time
from PIL import Image, ImageDraw

HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, "ProjectL/landstalker")
EXE = os.path.join(ROOT, "build/landstalker")
W = os.path.join(HOME, "Project-Friday-Test/lktest/langsweep")
RDIR = os.path.join(W, "rom2")
OUT = os.path.join(W, "screens")   # own subfolder (other sweeps share langsweep/)
SRC = "/home/deck/Documents/NonSteamGames/landstalker/"
LANGS = ["en", "de", "fr", "es", "it", "ru", "uk", "ko", "en_tone"]
if os.path.exists(os.path.join(ROOT, "build/lang/ja.bin")): LANGS.append("ja")
if len(sys.argv) > 1: LANGS = sys.argv[1:]
KEYS = ["QUICKSAVE", "QUICKLOAD", "NO QUICKSAVE", "NOT NOW", "NO MAP HERE", "FAST FORWARD OFF - SEE OPTIONS", "QUICK SAVE OFF - SEE OPTIONS",
        "SPRINT OFF - SEE OPTIONS", "PREPARING LIGHTING", "SWORD", "ARMOUR", "BOOTS", "RING", "MAGIC", "THUNDER", "ICE", "GAIA", "STEEL", "CHROME", "SHELL",
        "HYPER", "HEALING", "FIREPROOF", "IRON", "SPIKE", "SATURN", "MARS", "MOON", "VENUS", "BROAD SWORD", "LEATHER BREAST", "LEATHER BOOTS", "NONE"]

def say(*a): print(*a, flush=True)

def run(lang, d, extra_env, args, headless):
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", LANDSTALKER_LANG=lang,
               LANDSTALKER_SAVE=os.path.join(RDIR, "landstalker.srm"), LANDSTALKER_NOFOCUSPAUSE="1")
    env.update(extra_env)
    cmd = [EXE, os.path.join(RDIR, "landstalker.md")] + (["--headless"] if headless else []) + args
    r = subprocess.run(cmd, env=env, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    open(os.path.join(d, "run.log"), "ab").write(r.stdout)

def sheet(items, out, cols, cw, ch, title):
    """items = [(label, PIL image)]"""
    rows = (len(items) + cols - 1) // cols
    im = Image.new("RGB", (cols * (cw + 6) + 6, rows * (ch + 18) + 24), (30, 30, 36))
    dr = ImageDraw.Draw(im); dr.text((6, 5), title, fill=(255, 255, 255))
    for i, (lab, t) in enumerate(items):
        t = t.copy(); t.thumbnail((cw, ch))
        x = 6 + (i % cols) * (cw + 6); y = 24 + (i // cols) * (ch + 18)
        im.paste(t, (x, y)); dr.text((x, y + ch + 3), lab[:int(cw / 6)], fill=(200, 220, 255))
    im.save(out)

def sub_rows(im):
    """subtitle band of the title picture: bright pixels in the lower third (below the logo) -> count"""
    g = im.convert("L"); w, h = g.size
    reg = g.crop((0, int(h * 0.80), w, int(h * 0.95)))
    return sum(1 for p in reg.getdata() if p > 120)

def main():
    os.makedirs(RDIR, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    import glob as _g; jp = [os.path.basename(g) for g in _g.glob(SRC + "*(Japan)*.md")][:1]   # the Japanese ROM next to the ROM = the ja language (tools/jplang.py)
    for f in ["landstalker.md", "landstalker.srm"] + jp:
        if not os.path.exists(os.path.join(RDIR, f)): shutil.copy(SRC + f, RDIR)
    html_parts = []; report = []
    for lang in LANGS:
        d = os.path.join(OUT, lang); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        t0 = time.time(); say("== %s ==" % lang)
        inp = os.path.join(d, "in.txt"); open(inp, "w").write("0 0000\n950 0080\n958 0000\n")
        # a) + b) title + file select
        fr_t = list(range(780, 1001, 10)); fr_f = list(range(1010, 1101, 10))
        sd = os.path.join(d, "title"); os.makedirs(sd)
        say(" title + file select ..."); run(lang, d, dict(GENRECOMP_INPUTSCRIPT=inp, LANDSTALKER_SHOT=",".join(map(str, fr_t + fr_f)), LANDSTALKER_SHOT_DIR=sd), ["--frames", "1110"], True)
        shots = {}
        for f in glob.glob(os.path.join(sd, "shot_*.png")):
            shots[int(os.path.basename(f)[5:].split("_")[0])] = Image.open(f).convert("RGB")
        items = [("t%d" % k, shots[k]) for k in fr_t if k in shots]
        counts = [(k, sub_rows(shots[k])) for k in fr_t if k in shots]
        items += [("fs%d" % k, shots[k]) for k in fr_f if k in shots]
        say(" shots:", len(shots), " subtitle pixel counts:", " ".join("%d:%d" % c for c in counts))
        report.append((lang, "subtitle pixels per frame", counts))
        # c) OSD
        od = os.path.join(d, "osd"); os.makedirs(od)
        say(" OSD messages ...")
        sayenv = ";".join("%d:%s" % (200 + 15 * i, k) for i, k in enumerate(KEYS))
        ws = ",".join(str(200 + 15 * i + 5) for i in range(len(KEYS)))
        run(lang, d, dict(LANDSTALKER_OSDSAY=sayenv, LANDSTALKER_WINSHOT=ws, LANDSTALKER_WINSHOT_DIR=od), ["--frames", str(200 + 15 * len(KEYS) + 20)], False)
        osd = []
        for i, k in enumerate(KEYS):
            p = os.path.join(od, "winshot_%d.bmp" % (200 + 15 * i + 5))
            if os.path.exists(p):
                im = Image.open(p).convert("RGB"); w, h = im.size
                c = im.crop((0, int(h * 0.88), w, h)); bb = c.convert('L').point(lambda v: 255 if v > 40 else 0).getbbox(); c = c.crop((0, 0, min(w, bb[2] + 12), c.size[1])) if bb else c; c.save(os.path.join(od, "crop_%02d.png" % i)); osd.append((k, c))
        say(" osd crops:", len(osd), "of", len(KEYS))
        # d) map
        md = os.path.join(d, "map"); os.makedirs(md)
        run(lang, d, dict(LANDSTALKER_MAPSHOT="300", LANDSTALKER_SHOT_DIR=md), ["--frames", "320"], True)
        maps = [("map", Image.open(f).convert("RGB")) for f in glob.glob(os.path.join(md, "mapshot_*.png"))]
        say(" map shots:", len(maps))
        sheet(items, os.path.join(OUT, "sheet_%s_a.png" % lang), 5, 256, 224, "%s: title strip 780..1000 (step 10) + file select 1010..1100" % lang)
        sheet(osd, os.path.join(OUT, "sheet_%s_b.png" % lang), 3, 640, 90, "%s: on-screen messages (bottom-left crop)" % lang)
        if maps: sheet(maps, os.path.join(OUT, "sheet_%s_c.png" % lang), 1, 900, 560, "%s: room map" % lang)
        html_parts.append("<h2>%s</h2>%s" % (lang, "".join('<img src="screens/sheet_%s_%s.png" style="max-width:100%%"><br>' % (lang, s) for s in "abc" if os.path.exists(os.path.join(OUT, "sheet_%s_%s.png" % (lang, s))))))
        say(" done in %ds" % (time.time() - t0))
    open(os.path.join(W, "screens.html"), "w").write("<html><body style='background:#222;color:#eee'><h1>language sweep</h1>%s</body></html>" % "".join(html_parts))
    say("wrote", os.path.join(W, "screens.html"))

main()
