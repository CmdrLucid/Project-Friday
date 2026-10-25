#!/usr/bin/env python3
"""Trailer footage capture (recipe only: all output stays in ~/.landstalker_trailer, never in git).

Runs the built game headless with a user recording (input replay + matching save copy) and dumps
frames (LANDSTALKER_SHOT, raw picture without filter) and the audio (LANDSTALKER_WAV).
Settings files come from an isolated HOME (copy of the user's ~/.landstalker_* files) so a run can never change the user's settings.

  capture.py sheet NAME [STEP] [MAXFRAMES]   contact sheet of a source (every STEP frames) -> ~/.landstalker_trailer/sheets/NAME.png
  capture.py clip CLIP                       frames + audio of one clip from CLIPS -> ~/.landstalker_trailer/clips/CLIP/
  capture.py all                             every clip
Run it with the venv python (Pillow): ~/.landstalker_trailer/venv/bin/python
"""
import os, sys, subprocess, shutil, glob, wave

HOME = os.path.expanduser("~")
OUT = os.path.join(HOME, ".landstalker_trailer")
GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROM = "/home/deck/Documents/NonSteamGames/landstalker/landstalker.md"
REC = os.path.join(HOME, "aufnahmen")
REPL = os.path.join(GAME, "docs", "replays")
QUICK = {"LANDSTALKER_QUICK": "1", "LANDSTALKER_QUICK_SLOTS": "0,19"}

# sources: input file, save copy, extra env (as documented in docs/replays/README.md)
SOURCES = {
    "mercator": (f"{REPL}/mercator_doors_menu_gaia.txt", f"{REC}/save_20261016_0039.srm", QUICK),
    "intro":    (f"{REPL}/new_game_intro_shrine_cave.txt", f"{REC}/save_20261012_2106.srm", {}),
    "swords":   (f"{REPL}/all_swords_room166.txt", f"{REC}/save_20261022_0602.srm", QUICK),
    "swordfx":  (f"{REPL}/sword_effects_directions.txt", f"{REC}/save_20261022_0706.srm", QUICK),
    "ryuma":    (f"{REPL}/ryuma_shop_inn_fight.txt", f"{REC}/save_20261012_2057.srm", {}),
    "ship":     (f"{REPL}/ship_band_garbage.txt", f"{REC}/save_20261016_2147.srm", {}),
    "jump430":  (f"{REC}/rec_20261024_1816.txt", f"{REC}/save_20261024_1816.srm", QUICK),
    "room21":   (f"{REC}/rec_20261024_1818.txt", f"{REC}/save_20261024_1818.srm", QUICK),
    "room430":  (f"{REC}/rec_20261024_1739.txt", f"{REC}/save_20261024_1739.srm", QUICK),
    "dwarves":  (f"{REC}/rec_20261024_1659.txt", f"{REC}/save_20261024_1659.srm", QUICK),
    "vase":     (f"{REPL}/vase_platform_room444.txt", f"{REC}/save_20261016_1946.srm", {"LANDSTALKER_QSREQ": "l647", "LANDSTALKER_CARRY": "1"}),
    "waterfall": (f"{REPL}/massan_waterfall_death.txt", f"{REC}/save_20261012_2148.srm", {}),
    "revive":   (f"{REPL}/death_revive_friday.txt", f"{REC}/save_20261012_2204.srm", {}),
    "gaia2":    (f"{REC}/rec_20261019_2044.txt", f"{REC}/save_20261019_2044.srm", QUICK),
    "fahl":     (f"{REC}/rec_20261022_2150.txt", f"{REC}/save_20261022_2150.srm", QUICK),
    "long":     (f"{REC}/rec_20261019_2215.txt", f"{REC}/save_20261019_2215.srm", QUICK),
}

# clips: source, first frame, last frame, widescreen e (0 / 19 / 39), full height, extra env
CLIPS = {}
if os.path.exists(os.path.join(os.path.dirname(__file__), "clips.py")):
    sys.path.insert(0, os.path.dirname(__file__))
    from clips import CLIPS  # noqa


def isolated_home():
    h = os.path.join(OUT, "home")
    os.makedirs(h, exist_ok=True)
    for f in glob.glob(os.path.join(HOME, ".landstalker_*")):
        if os.path.isfile(f):
            shutil.copy(f, h)
    return h


def run(src, frames, shots, wide=39, tall=1, extra=None, wav=None, shotdir=None, winshot=None, video=False):
    inp, save, env0 = SOURCES[src]
    work = os.path.join(OUT, "work")
    os.makedirs(work, exist_ok=True)
    sv = os.path.join(work, "save.srm")
    if os.path.exists(save):
        shutil.copy(save, sv)
    elif os.path.exists(sv):
        os.remove(sv)
    env = dict(os.environ)
    env.update({"HOME": isolated_home(), "LANDSTALKER_SAVE": sv, "GENRECOMP_INPUTSCRIPT": inp,
                "LANDSTALKER_WIDE": str(wide), "LANDSTALKER_TALL": str(tall)})
    env.update(env0)
    env.update(extra or {})
    if shots:
        env["LANDSTALKER_SHOT"] = ",".join(str(f) for f in shots)
        env["LANDSTALKER_SHOT_DIR"] = shotdir
    if wav:
        env["LANDSTALKER_WAV"] = wav
    if winshot:
        env["LANDSTALKER_WINSHOT"] = ",".join(str(f) for f in winshot)
        env["LANDSTALKER_WINSHOT_DIR"] = shotdir
        env["SDL_VIDEODRIVER"] = "dummy"
    cmd = [os.path.join(GAME, "build", "landstalker"), ROM, "--frames", str(frames)]
    if not winshot:
        cmd.insert(2, "--headless")
    with open(os.path.join(work, "log.txt"), "w") as log:
        subprocess.run(cmd, env=env, cwd=GAME, stdout=log, stderr=subprocess.STDOUT)


def sheet(name, step=60, maxf=None):
    from PIL import Image, ImageDraw
    inp = SOURCES[name][0]
    last = int(open(inp).read().split()[-2]) + 300
    maxf = int(maxf) if maxf else last
    d = os.path.join(OUT, "sheets", name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    fr = list(range(0, maxf, int(step)))
    print(f"[sheet] {name}: {len(fr)} pictures up to frame {maxf} ...", flush=True)
    run(name, maxf, fr, shotdir=d)
    files = sorted(glob.glob(os.path.join(d, "shot_*.png")))
    cols, tw, th = 8, 199, 112
    per = 64
    for page in range(0, len(files), per):
        part = files[page:page + per]
        rows = (len(part) + cols - 1) // cols
        im = Image.new("RGB", (cols * tw, rows * (th + 12)), (40, 40, 40))
        dr = ImageDraw.Draw(im)
        for i, f in enumerate(part):
            p = Image.open(f).convert("RGB").resize((tw, th))
            x, y = (i % cols) * tw, (i // cols) * (th + 12)
            im.paste(p, (x, y + 12))
            dr.text((x + 2, y), os.path.basename(f)[5:11].lstrip("0") or "0", fill=(255, 255, 0))
        o = os.path.join(OUT, "sheets", f"{name}_{page // per}.png")
        im.save(o)
        print("[sheet] wrote", o)


def clip(name):
    c = CLIPS[name]
    src, a, b = c["src"], c["a"], c["b"]
    d = os.path.join(OUT, "clips", name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    wav = os.path.join(d, "full.wav")
    print(f"[clip] {name}: {src} frames {a}..{b} wide {c.get('wide', 39)} tall {c.get('tall', 1)} ...", flush=True)
    fr = list(range(a, b + 1))
    if c.get("win"):   # LANDSTALKER_WINSHOT reads at most ~200 characters of the list: several identical runs, one chunk each
        chunk = []
        for f in fr + [None]:
            if f is None or len(",".join(str(x) for x in chunk + [f])) > 190:
                run(src, b + 2, None, c.get("wide", 39), c.get("tall", 1), c.get("env"), wav, d, winshot=chunk)
                chunk = []
            if f is not None:
                chunk.append(f)
    else:
        run(src, b + 2, fr, c.get("wide", 39), c.get("tall", 1), c.get("env"), wav, d)
    n = len(glob.glob(os.path.join(d, "shot_*.png")) + glob.glob(os.path.join(d, "winshot_*.bmp")))
    # audio of the clip: the WAV holds every emulated frame from 0; cut by the average samples per frame of this run
    with wave.open(wav) as w:
        total = w.getnframes()
        data = w.readframes(total)
        rate = w.getframerate()
    spf = total / (b + 2)
    s0, s1 = int(a * spf), int((b + 1) * spf)
    with wave.open(os.path.join(d, "clip.wav"), "wb") as o:
        o.setnchannels(2); o.setsampwidth(2); o.setframerate(rate)
        o.writeframes(data[s0 * 4:s1 * 4])
    os.remove(wav)
    print(f"[clip] {name}: {n} pictures, audio {(s1 - s0) / rate:.1f} s", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    if sys.argv[1] == "sheet":
        sheet(*sys.argv[2:])
    elif sys.argv[1] == "clip":
        clip(sys.argv[2])
    elif sys.argv[1] == "all":
        for k in CLIPS:
            clip(k)
