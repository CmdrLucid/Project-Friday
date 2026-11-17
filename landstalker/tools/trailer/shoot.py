#!/usr/bin/env python3
"""Trailer 2.0 footage (2026-11-17, modern trailer). Recipe only: every output stays in ~/.landstalker_trailer/v2 (ROM-derived, never commit).

Runs the built game in a HIDDEN full-HD window (the light exists only on the GPU) with LANDSTALKER_PRESENT_SHOT for every frame of a scene,
then packs the pictures into a near-lossless clip  ~/.landstalker_trailer/v2/clips/NAME.mp4  and deletes the PNGs.
Scenes (scenes.py): a user recording as the start (save + the input prefix that loads it), an optional warp (tools/patch_warp.py), own input
lines relative to the warp frame, the option files to override in the isolated HOME, and the frame range to keep.

  shoot.py NAME [NAME..]        shoot scenes      shoot.py probe NAME F1,F2..   single pictures (to place a scene)
  shoot.py list
Input mask bits: UP1 DOWN2 LEFT4 RIGHT8 B10 C20 A40 START80 (C = sword, B = jump, A = talk/use on the default keys).
"""
import os, sys, re, shutil, subprocess, glob, time

HOME = os.path.expanduser("~")
OUT = os.path.join(HOME, ".landstalker_trailer", "v2")
GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROM = "/home/deck/Documents/NonSteamGames/landstalker/landstalker.md"
REC = os.path.join(HOME, "Project-Friday-Test", "aufnahmen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenes import SCENES, BASES  # noqa

KEYS = {"U": 1, "D": 2, "L": 4, "R": 8, "B": 0x10, "C": 0x20, "A": 0x40, "S": 0x80, "M": 0x800}   # M = Mode (Select on the pad: Friday Hints)


def mask(s):
    m = 0
    for ch in s:
        m |= KEYS[ch]
    return m


def rec_env(rec):
    env = {}
    for ln in open(os.path.join(REC, f"rec_{rec}.cfg")):
        for tok in ln.split():
            if tok.startswith("LANDSTALKER_") and "=" in tok:
                k, v = tok.split("=", 1)
                env[k] = v
    if "LANDSTALKER_QSPLAY" in env:
        pass
    return env


def build_input(base, sc, path):
    """prefix of the base recording up to base['cut'], then the scene's own lines: (rel_frame, 'UR') pairs relative to sc['at']."""
    lines = []
    if sc.get("rec"):
        shutil.copy(os.path.join(REC, f"rec_{sc['rec']}.txt"), path)
        return
    for ln in open(os.path.join(REC, f"rec_{base['rec']}.txt")):
        p = ln.split()
        if len(p) == 2 and int(p[0]) < base["cut"]:
            lines.append((int(p[0]), int(p[1], 16)))
    lines.append((base["cut"], 0))
    at = sc.get("at", base["cut"] + 40)
    for rel, keys in sc.get("input", []):
        lines.append((at + rel, mask(keys)))
    lines.sort()
    with open(path, "w") as f:
        for fr, m in lines:
            f.write(f"{fr} {m:04X}\n")


def resolve_warp(w):
    """'ROOM' alone = the room's centre cell (proxysurvey.start_cell), 'ROOM:X,Y' = cell X,Y (decimal) at its floor height, else as patch_warp takes it"""
    sys.path.insert(0, os.path.join(GAME, "tools"))
    import proxysurvey as ps
    room, _, xy = w.partition(":")
    if xy and "." in xy:
        return w
    hm = ps.heights(open(ROM, "rb").read(), int(room))
    if xy:
        x, y = (int(v) for v in xy.replace("/", ",").split(","))
        if (x, y) not in hm:     # a cell without a height word (sand, path): Z 0 there left the room black; keep Nigel's Z, he lands on the floor
            return "%d:%d.08,%d.08" % (int(room), x, y)
        h = hm[(x, y)][0]
    else:
        (x, y), h = ps.start_cell(hm)
    return "%d:%d.08,%d.08,%04X" % (int(room), x, y, 16 * h)


def run(name, frames, outdir):
    sc = SCENES[name]
    base = BASES[sc.get("base", "now")]
    if sc.get("rec"):
        base = {"rec": sc["rec"], "cut": 0}
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(os.path.join(outdir, "home"))
    h = os.path.join(outdir, "home")
    for f in glob.glob(os.path.join(REC, f"opts_{base['rec']}", ".landstalker_*")):
        if os.path.isfile(f) and ".bak" not in f:
            shutil.copy(f, h)
    opts = {"lighting": "1", "gpu": "1"} if sc.get("rec") else {"lighting": "1", "gpu": "1", "dither": "0", "lang": "en"}   # a replay keeps the recording's options (other text = other timing)
    opts.update(sc.get("opts", {}))
    for k, v in opts.items():
        open(os.path.join(h, ".landstalker_" + k), "w").write(v + "\n")
    shutil.copy(os.path.join(REC, f"save_{base['rec']}.srm"), os.path.join(outdir, "s.srm"))
    inp = os.path.join(outdir, "input.txt")
    build_input(base, sc, inp)
    at = sc.get("at", base["cut"] + 40)
    env = {"PATH": os.environ["PATH"], "HOME": h, "GENRECOMP_INPUTSCRIPT": inp, "LANDSTALKER_SAVE": os.path.join(outdir, "s.srm"),
           "LANDSTALKER_SHOT_DIR": outdir, "LANDSTALKER_PRESENT_SHOT": ",".join(str(f) for f in frames),
           "LANDSTALKER_HIDDEN": "1", "LANDSTALKER_NOFOCUSPAUSE": "1", "SDL_AUDIODRIVER": "dummy",
           "LANDSTALKER_WINSIZE": sc.get("size", "1920x1080"), "LANDSTALKER_WIDE": str(sc.get("wide", 39)), "LANDSTALKER_TALL": str(sc.get("tall", 1)),
           "GENRECOMP_CHECKLOG": os.path.join(outdir, "check.chk"), "GENRECOMP_CHECKEVERY": "4",
           "LANDSTALKER_GL5_MAXMS": "1000", "LANDSTALKER_GPULT_MAXMS": "1000"}   # the PNG dump makes frames slow: never let the GPU-time guard switch the light off
    for k in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"):
        if k in os.environ:
            env[k] = os.environ[k]
    if sc.get("rec"):
        env.update(rec_env(sc["rec"]))
        env["LANDSTALKER_WIDE"] = str(sc.get("wide", env.get("LANDSTALKER_WIDE", 39)))
    if "warp" in sc:
        env["LANDSTALKER_WARP"] = sc["warp"] if ";" in sc["warp"] else resolve_warp(sc["warp"])
        env["LANDSTALKER_WARP_AT"] = str(at)
    for k, v in sc.get("env", {}).items():
        env[k] = re.sub(r"r\+(\d+)", lambda m: str(at + int(m.group(1))), v)
    last = max(frames)
    t0 = time.time()
    with open(os.path.join(outdir, "out.log"), "w") as log:
        subprocess.run([os.path.join(GAME, "build", "landstalker"), "--frames", str(last + 3), ROM], env=env, cwd=GAME, stdout=log, stderr=subprocess.STDOUT)
    n = len(glob.glob(os.path.join(outdir, "present_*_gpu.png")))
    bad = "LIGHT OFF!" if "Lighting off" in open(os.path.join(outdir, "out.log"), errors="replace").read() else ""
    print(f"[{name}] {n}/{len(frames)} pictures in {time.time() - t0:.0f} s {bad}", flush=True)
    if sc.get("rec"):   # replay sync against the recording's own checkpoints (every 120 frames)
        ref = {l.split()[0]: l.split()[1:4] for l in open(os.path.join(REC, f"rec_{sc['rec']}.chk"))}
        got = {l.split()[0]: l.split()[1:4] for l in open(os.path.join(outdir, "check.chk")) if int(l.split()[0]) % 120 == 0}
        bad = [f for f in got if f in ref and got[f] != ref[f] and int(f) <= max(frames)]
        print(f"[{name}] replay sync: {'exact' if not bad else 'DIFFERS from frame ' + min(bad, key=int)}", flush=True)
        return at
    check_walk(name, at, frames, outdir)
    return at


def check_walk(name, at, frames, outdir):
    """report frames inside the kept range where a direction is held but Nigel does not move (= walks into a wall), and room changes"""
    sc = SCENES[name]
    held = []   # (abs frame from, keys)
    for rel, keys in sorted(sc.get("input", [])):
        held.append((at + rel, keys))
    def keys_at(f):
        k = ""
        for f0, kk in held:
            if f0 <= f:
                k = kk
        return k
    pos = {}
    try:
        for ln in open(os.path.join(outdir, "check.chk")):
            p = ln.split()
            pos[int(p[0])] = (p[1], p[2], p[3])
    except OSError:
        return
    lo, hi = min(frames), max(frames)
    stuck, rooms, run = [], set(), 0
    fs = sorted(f for f in pos if lo <= f <= hi)
    for a, b in zip(fs, fs[1:]):
        rooms.add(pos[a][0])
        if any(c in keys_at(a) for c in "UDLR") and pos[a] == pos[b]:
            run += 1
            if run == 3:
                stuck.append(a - at)
        else:
            run = 0
    msg = f"[{name}] rooms in range: {sorted(rooms)}"
    if stuck:
        msg += f"  STUCK AT WALL (rel frames): {stuck[:8]}"
    print(msg, flush=True)


def scene_frames(name):
    sc = SCENES[name]
    base = BASES[sc.get("base", "now")]
    at = 0 if sc.get("rec") else sc.get("at", base["cut"] + 40)
    a, b = sc["keep"]
    return at, list(range(at + a, at + b + 1))


def shoot(name):
    at, fr = scene_frames(name)
    d = os.path.join(OUT, "work", name)
    print(f"[{name}] frames {fr[0]}..{fr[-1]} ...", flush=True)
    run(name, fr, d)
    os.makedirs(os.path.join(OUT, "clips"), exist_ok=True)
    o = os.path.join(OUT, "clips", name + ".mp4")
    lst = os.path.join(d, "list.txt")
    files = sorted(glob.glob(os.path.join(d, "present_*_gpu.png")))
    with open(lst, "w") as f:
        for p in files:
            f.write(f"file '{p}'\nduration {1/60:.6f}\n")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", SCENES[name].get("vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2") + ",fps=60",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "10", "-pix_fmt", "yuv444p", o], check=True)
    for p in files:
        os.remove(p)
    print(f"[{name}] -> {o}", flush=True)


def probe(name, fl):
    at, _ = scene_frames(name)
    fr = [at + int(x) for x in fl.split(",")]
    d = os.path.join(OUT, "probe", name)
    run(name, fr, d)
    os.system(f"grep -h 'warp:' {d}/out.log | grep -v armed | head -3")
    from PIL import Image, ImageDraw
    fs = sorted(glob.glob(os.path.join(d, "present_*")))
    cols = 2 if len(fs) <= 4 else 3
    tw, th = 1920 // cols, 1080 // cols
    o = Image.new("RGB", (tw * cols, th * ((len(fs) + cols - 1) // cols)))
    for i, f in enumerate(fs):
        o.paste(Image.open(f).convert("RGB").resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
        ImageDraw.Draw(o).text(((i % cols) * tw + 8, (i // cols) * th + th - 20), "rel %d" % (int(os.path.basename(f)[8:14]) - at), fill=(255, 255, 0))
    o.save(os.path.join(d, "sheet.png"))
    print(os.path.join(d, "sheet.png"))


def survey(rooms, daytime, tag):
    """one picture per room (centre cell), all in one run: survey ROOMS(comma) DAYTIME TAG -> ~/.landstalker_trailer/v2/survey/TAG.png"""
    from PIL import Image, ImageDraw
    rl = [r for r in rooms.split(",")]
    base = BASES["now"]; at0 = base["cut"] + 40
    ats = [at0 + 200 * i for i in range(len(rl))]
    SCENES["_survey"] = {"warp": ";".join(resolve_warp(r) for r in rl), "keep": (0, 0), "env": {"LANDSTALKER_WARP_AT": ",".join(map(str, ats)), "LANDSTALKER_DAYTIME": daytime, "LANDSTALKER_DAYLEN": "100000"}}
    d = os.path.join(OUT, "survey", tag)
    run("_survey", [a + 150 for a in ats], d)
    fs = sorted(glob.glob(os.path.join(d, "present_*")))
    cols = 4; tw, th = 480, 270
    o = Image.new("RGB", (tw * cols, th * ((len(fs) + cols - 1) // cols)))
    for i, f in enumerate(fs):
        o.paste(Image.open(f).convert("RGB").resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
        ImageDraw.Draw(o).text(((i % cols) * tw + 8, (i // cols) * th + th - 18), "room " + rl[i], fill=(255, 255, 0))
    o.save(os.path.join(OUT, "survey", tag + ".png"))
    print(os.path.join(OUT, "survey", tag + ".png"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    if sys.argv[1] == "list":
        for k, v in SCENES.items():
            print(k, v.get("warp", ""), v["keep"], v.get("note", ""))
    elif sys.argv[1] == "survey":
        survey(*sys.argv[2:5])
    elif sys.argv[1] == "probe":
        probe(sys.argv[2], sys.argv[3])
    else:
        for n in sys.argv[1:]:
            shoot(n)
