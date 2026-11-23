#!/home/deck/Project-Friday-Test/hdvenv/bin/python3
"""langsweep_options.py -- headless language sweep of the OPTIONS MENU (every language, every page, every row with its help line).

Run it with the venv interpreter (it has PIL, needed for the contact sheets):
    ~/Project-Friday-Test/hdvenv/bin/python3 landstalker/tools/langsweep_options.py [lang ...] [--jobs N] [--shots-only | --sheets-only]
(the shebang already points at it, so  landstalker/tools/langsweep_options.py  works too).  Python 3 + PIL, nothing else.

What it does (all inside ~/Project-Friday-Test/lktest/langsweep/, nothing outside is written, the user's save is never touched):
 1. copies the ROM + save from ~/Documents/NonSteamGames/landstalker/ into langsweep/rom/ (once) and runs the game ONLY from that copy,
    with a private HOME (langsweep/home) so no ~/.landstalker_* setting of the user is read or written (clean default settings);
 2. per language (en de fr es it ru uk ko en_tone; ja only when named explicitly; LANDSTALKER_LANG=<code>) runs build/landstalker headless
    (SDL dummy video / audio) with an input script: the first part of the Massan replay (Nigel walks free in the church, up to frame 4600),
    then Start (menu), RIGHT x2 (tab 'Options'), A (enter the list), and for every root row / every page / every row: DOWN, wait, screenshot
    (LANDSTALKER_SHOT).  Pad bits: UP 1 DOWN 2 LEFT 4 RIGHT 8 B 10 C 20 A 40 START 80 (tools/patch_inputlog.py).  Quit Game row of the root is only looked at (never pressed);
 3. writes langsweep/<lang>/shot_*.png, one labelled contact sheet langsweep/sheet_<lang>.png per language and langsweep/index.html.
The row structure (pages, row counts, page names) is parsed from the generated .deps/genrecomp/src/func_table.c (lk_pg_cnt / lk_pg_name, so patch_altpad / patch_kbdir / patch_lang changes count); PAGES has a fallback.  Runtime about 40 s per language, 4 in parallel about 2 min in all."""
import os, shutil, subprocess, sys, html, glob
from concurrent.futures import ThreadPoolExecutor

HOME = os.path.expanduser("~")
LS = os.path.join(HOME, "ProjectL/landstalker")
BIN = os.path.join(LS, "build/landstalker")
SRC = os.path.join(HOME, "Documents/NonSteamGames/landstalker")
WORK = os.path.join(HOME, "Project-Friday-Test/lktest/langsweep")
MASSAN = os.path.join(HOME, "Project-Friday-Test/massan.txt")
LANGS = ["en", "de", "fr", "es", "it", "ru", "uk", "ko", "en_tone", "ja"]   # ja: needs the Japanese ROM next to the ROM (copied by setup)
# ja is NOT in the default list: it needs a Japanese ROM next to the ROM (patch_lang.py LK_JPLANG), without it the menu stays English; run `langsweep_options.py ja` explicitly if one is there

def read_pages():
    """pages + row counts from the generated source (.deps/genrecomp/src/func_table.c, includes patch_altpad / patch_kbdir / patch_lang changes);
    fallback = the table known on 2026-11-23.  -> [(name, rows), ...] for the pages (root excluded), root row count"""
    import re
    names = ["Display", "Graphics", "Audio", "Movement", "Comfort", "Difficulty / Help", "Keybindings", "Language / Region"]; cnt = [9, 7, 12, 3, 6, 8, 3, 20, 4]
    try:
        t = open(os.path.join(LS, ".deps/genrecomp/src/func_table.c")).read()
        cnt = [int(x) for x in re.search(r"lk_pg_cnt\[LK_NPG \+ 1\] = \{([^}]*)\}", t).group(1).split(",")]
        names = re.search(r"lk_pg_name\[LK_NPG \+ 1\] = \{([^}]*)\}", t).group(1).replace('"', "").split(",")[1:]
        names = [n.strip() for n in names]
    except Exception as e: print("warning: could not parse func_table.c (%s), using the built-in table" % e)
    return list(zip(names, cnt[1:])), cnt[0]
PAGES, ROOTN = read_pages()   # root rows: the pages, then Quit Game (the last root row is only looked at, never pressed)
UP, DOWN, LEFT, RIGHT, B, C, A, START = 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80
STEP = 16   # frames per action (press 4 frames, shot 12 frames after the press)

def plan(lang):
    """-> (script lines, [(frame, label)])"""
    lines = [l.strip() for l in open(MASSAN) if l.strip() and int(l.split()[0]) < 4600]
    t = [4700]; last = [0]
    def press(m, hold=4, wait=STEP):
        last[0] = t[0]; lines.append("%d %04X" % (t[0], m)); lines.append("%d 0000" % (t[0] + hold)); t[0] += wait
    shots = []
    def shot(label): shots.append((last[0] + 12 + (16 if label.endswith(' 1/%s' % label.split('/')[-1]) else 0), label))
    press(START, 4, 100); press(RIGHT, 4, 50); press(RIGHT, 4, 50)   # menu opens (fade), tab Options
    press(A, 4, 60)                                                   # enter the root list
    for p, (name, n) in enumerate(PAGES):
        if p: press(DOWN)
        shot("root row %d: %s" % (p + 1, name))
        press(A, 4, 40)                                               # enter page
        shot("%s 1/%d" % (name, n))
        for r in range(1, n):
            press(DOWN); shot("%s %d/%d" % (name, r + 1, n))
        press(B, 4, 40)
    press(DOWN); shot("root row %d: %s" % (len(PAGES) + 1, "Quit Game"))   # (after the last page the cursor is on its row; one DOWN more = Quit Game)
    return lines, shots, t[0] + 20

def setup():
    rom = os.path.join(WORK, "rom"); os.makedirs(rom, exist_ok=True)
    os.makedirs(os.path.join(WORK, "home"), exist_ok=True)
    jp = [os.path.basename(g) for g in glob.glob(os.path.join(SRC, "*(Japan)*.md"))][:1]   # the Japanese ROM next to the ROM = the ja language (tools/jplang.py, LK_JPLANG)
    for f in ["landstalker.md", "landstalker.srm"] + jp:
        if not os.path.exists(os.path.join(rom, f)): shutil.copy(os.path.join(SRC, f), rom)
    return rom

def run_lang(lang, rom):
    d = os.path.join(WORK, lang); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    lines, shots, last = plan(lang)
    open(os.path.join(d, "input.txt"), "w").write("\n".join(lines) + "\n")
    open(os.path.join(d, "shots.txt"), "w").write("\n".join("%d\t%s" % s for s in shots) + "\n")
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", LANDSTALKER_LANG=lang, HOME=os.path.join(WORK, "home"),
               LANDSTALKER_SAVE=os.path.join(rom, "landstalker.srm"), GENRECOMP_INPUTSCRIPT=os.path.join(d, "input.txt"),
               LANDSTALKER_SHOT=",".join(str(f) for f, _ in shots), LANDSTALKER_SHOT_DIR=d)
    r = subprocess.run([BIN, "--headless", "--frames", str(last), os.path.join(rom, "landstalker.md")], env=env, capture_output=True, text=True, cwd=LS)
    open(os.path.join(d, "log.txt"), "w").write(r.stdout + r.stderr)
    n = len(glob.glob(os.path.join(d, "shot_*.png")))
    print("[%s] game done (rc %d), %d / %d shots" % (lang, r.returncode, n, len(shots)), flush=True)

def sheet(lang):
    from PIL import Image, ImageDraw
    d = os.path.join(WORK, lang)
    shots = [l.rstrip("\n").split("\t") for l in open(os.path.join(d, "shots.txt"))]
    cols, cw, ch, lab = 4, 330, 224, 14
    rows = (len(shots) + cols - 1) // cols
    im = Image.new("RGB", (cols * cw, rows * (ch + lab)), (30, 30, 30)); dr = ImageDraw.Draw(im)
    for i, (f, label) in enumerate(shots):
        x, y = (i % cols) * cw, (i // cols) * (ch + lab)
        p = glob.glob(os.path.join(d, "shot_%06d_*.png" % int(f)))
        if p:
            s = Image.open(p[0]).convert("RGB"); w = s.size[0]; x0 = (w - 320) // 2
            im.paste(s.crop((x0, 0, x0 + 320, ch)), (x + 5, y + lab))
        else: dr.text((x + 10, y + lab + 10), "MISSING", fill=(255, 80, 80))
        dr.text((x + 5, y + 1), "%s  [f%s]" % (label, f), fill=(255, 255, 0))
    out = os.path.join(WORK, "sheet_%s.png" % lang); im.save(out); print("[%s] sheet %s" % (lang, out), flush=True)

def index(langs):
    h = ["<!doctype html><meta charset=utf-8><title>Options language sweep</title><body style='background:#222;color:#eee;font:14px sans-serif'><h1>Options language sweep</h1>"]
    for l in langs:
        h.append("<h2 id=%s>%s</h2><a href='sheet_%s.png'><img src='sheet_%s.png' style='max-width:100%%'></a>" % (l, html.escape(l), l, l))
    open(os.path.join(WORK, "index.html"), "w").write("".join(h) + "</body>")
    print("index: %s" % os.path.join(WORK, "index.html"))

def main():
    a = sys.argv[1:]; jobs = 2
    if "--jobs" in a: i = a.index("--jobs"); jobs = int(a[i + 1]); del a[i:i + 2]
    shots_only, sheets_only = "--shots-only" in a, "--sheets-only" in a
    a = [x for x in a if not x.startswith("--")]; langs = a or LANGS
    rom = setup()
    if not sheets_only:
        with ThreadPoolExecutor(jobs) as ex: list(ex.map(lambda l: run_lang(l, rom), langs))
    if not shots_only:
        for l in langs: sheet(l)
        index(langs)

if __name__ == "__main__": main()
