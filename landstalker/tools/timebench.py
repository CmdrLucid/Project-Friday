#!/usr/bin/env python3
"""Timing bench (TIMING_PLAN T0): replays ALL recordings headless and writes ONE result line per recording, so that any later change of the
time path (T1..T7) can be proven bit identical.  Per recording: the build is run with LANDSTALKER_TIMETRACE on, its own fresh copy of the save,
an isolated empty HOME and the WIDE / TALL values of its .cfg.

Result line (key=value, one line per recording; 'time' is NOT part of the comparison):
    <name> frames=N chk=equal|diff@F|none ram=<hash of the dumps every 100 frames>/<count> wav=<hash> trace=<hash> time=S.S exit=0
  chk   = checkpoint log of the replay against the recording's .chk ('none' = no .chk: intro / massan / the two oldest recordings)
  ram   = sha256 over the sha256 of every `--ram-dump DIR:100` file (work RAM + VRAM + CRAM + VSRAM), wav = LANDSTALKER_WAV capture, trace = time trace
Recordings that do not replay exactly (older builds, option files of the live HOME) show chk=diff@F: expected, recorded, not fixed.

usage: tools/timebench.py [--baseline FILE] [--compare FILE] [--jobs N<=4] [--only SUBSTR] [--bin PATH] [--verify-off] [--counts FILE] [--out FILE] [--keep-traces DIR] [--max-frames N] [--home-opts] [--env K=V ...]
  --baseline FILE   write the results as the new baseline (e.g. ~/timebench/baseline.txt; keep it OUTSIDE git)
  --compare FILE    compare this run with a baseline: prints every difference, exit code 1 if there is any (or a recording is missing)
  --verify-off      also run every recording with the trace OFF and require RAM dumps + WAV identical (proof that the trace does not change the time)
  --counts FILE     write the per recording event counts of the trace (kinds, T1 question) to FILE
  --home-opts       copy the ~/.landstalker_* option files into the isolated HOME (a COPY; default: empty HOME)
  --env K=V         extra environment variable for every replay (repeatable; the .cfg values win), e.g. LANDSTALKER_QUICK=1 LANDSTALKER_QUICK_SLOTS=0,19
  --max-frames N    cap the frame count (quick smoke tests; results then differ from a full baseline)"""
import argparse, concurrent.futures as cf, glob, hashlib, os, shlex, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LAND = os.path.dirname(HERE)
ROM = "/home/deck/Documents/NonSteamGames/landstalker/landstalker.md"
AUF = "/home/deck/aufnahmen"
WORK = "/home/deck/timebench/work/%d" % os.getpid()   # one directory per bench process: two benches at the same time must not share a recording's work dir (2026-10-29)
HOME_OPTS = False
EXTRA_ENV = {}

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def last_frame(path):
    last = 0
    with open(path) as f:
        for ln in f:
            p = ln.split()
            if p and p[0].isdigit(): last = int(p[0])
    return last

def read_cfg(path):
    env = {}
    if os.path.exists(path):
        for tok in shlex.split(open(path).read()):
            if "=" in tok:
                k, v = tok.split("=", 1); env[k] = v
    return env

def jobs_list():
    out = []
    for t in sorted(glob.glob(AUF + "/rec_*.txt")):
        base = os.path.basename(t)[:-4]; stem = base[4:]
        d = dict(name=base, script=t, save=AUF + "/save_" + stem + ".srm", cfg=read_cfg(AUF + "/" + base + ".cfg"), chk=AUF + "/" + base + ".chk")
        d["frames"] = (last_frame(d["chk"]) + 1) if os.path.exists(d["chk"]) else last_frame(t) + 120
        if not os.path.exists(d["chk"]): d["chk"] = None
        out.append(d)
    out.append(dict(name="intro", script="/home/deck/intro.txt", save=None, cfg={}, chk=None, frames=12000))
    out.append(dict(name="massan", script=os.path.join(LAND, "docs/replays/massan.txt"), save=None, cfg={}, chk=None, frames=last_frame(os.path.join(LAND, "docs/replays/massan.txt")) + 120))
    return out

def clean_env():
    return {k: v for k, v in os.environ.items() if not (k.startswith("LANDSTALKER_") or k.startswith("GENRECOMP_") or k == "HOME")}

def run_one(job, binary, trace_on, tag, max_frames, keep):
    wd = os.path.join(WORK, job["name"] + tag)
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(wd + "/home"); os.makedirs(wd + "/d")
    if HOME_OPTS:   # copy (never the original) of the option files of the real HOME: the recordings were made with them
        for f in glob.glob("/home/deck/.landstalker_*"):
            if os.path.isfile(f): shutil.copy(f, wd + "/home/")
    opts = os.path.join(AUF, "opts_" + job["name"][4:])   # option files saved by the recording script v2 (tools/Landstalker_Aufnahme.sh) win over --home-opts
    if os.path.isdir(opts):
        for f in glob.glob(opts + "/.landstalker_*"):
            if os.path.isfile(f): shutil.copy(f, wd + "/home/")
    srm = wd + "/s.srm"
    if job["save"] and os.path.exists(job["save"]): shutil.copy(job["save"], srm)
    env = clean_env(); env.update(EXTRA_ENV); env.update(job["cfg"])
    env.update(HOME=wd + "/home", LANDSTALKER_SAVE=srm, GENRECOMP_INPUTSCRIPT=job["script"], GENRECOMP_CHECKLOG=wd + "/chk.txt", LANDSTALKER_WAV=wd + "/a.wav")
    if trace_on: env["LANDSTALKER_TIMETRACE"] = wd + "/trace.txt"
    frames = min(job["frames"], max_frames) if max_frames else job["frames"]
    t0 = time.time()
    try:
        r = subprocess.run([binary, "--headless", "--frames", str(frames), "--ram-dump", wd + "/d:100", ROM], env=env, cwd=LAND,
                           stdout=open(wd + "/out.log", "w"), stderr=subprocess.STDOUT, timeout=1800)
        rc = r.returncode
    except subprocess.TimeoutExpired:
        rc = 124
    dt = time.time() - t0
    res = dict(name=job["name"], frames=frames, exit=rc, time=dt)
    # checkpoints
    if job["chk"]:
        a = open(job["chk"]).read().splitlines(); b = open(wd + "/chk.txt").read().splitlines() if os.path.exists(wd + "/chk.txt") else []
        n = min(len(a), len(b)); first = None
        for i in range(n):
            if a[i] != b[i]: first = a[i].split()[0]; break
        if first is None and len(a) != len(b) and not max_frames: first = (a[n] if n < len(a) else b[n]).split()[0]
        res["chk"] = "equal" if first is None else "diff@" + first
    else:
        res["chk"] = "none"
    dumps = sorted(glob.glob(wd + "/d/ram_*.bin"))
    h = hashlib.sha256()
    for p in dumps: h.update(sha(p).encode())
    res["ram"] = "%s/%d" % (h.hexdigest()[:16], len(dumps))
    res["wav"] = sha(wd + "/a.wav")[:16] if os.path.exists(wd + "/a.wav") else "none"
    counts = None
    if trace_on and os.path.exists(wd + "/trace.txt"):
        res["trace"] = sha(wd + "/trace.txt")[:16]
        counts = {}
        with open(wd + "/trace.txt") as f:
            for ln in f:
                if ln[0] == "#": continue
                p = ln.split(); k = p[3]; c = 1
                if k in "HZ": c = int(p[4])          # group lines: the first argument is the number of events
                elif p[-1][0] == "x": c = int(p[-1][1:].split("@")[0])
                e = counts.setdefault(k, [0, 0]); e[0] += 1; e[1] += c
        if keep: shutil.copy(wd + "/trace.txt", os.path.join(keep, job["name"] + ".trace"))
    else:
        res["trace"] = "off"
    shutil.rmtree(wd, ignore_errors=True)
    return res, counts

def fmt(r):
    return "%s frames=%d chk=%s ram=%s wav=%s trace=%s time=%.1f exit=%d" % (r["name"], r["frames"], r["chk"], r["ram"], r["wav"], r["trace"], r["time"], r["exit"])

def parse(path):
    d = {}
    for ln in open(path):
        p = ln.split()
        if not p or p[0][0] == "#": continue
        d[p[0]] = {kv.split("=", 1)[0]: kv.split("=", 1)[1] for kv in p[1:]}
    return d

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline"); ap.add_argument("--compare"); ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only"); ap.add_argument("--bin", default=os.path.join(LAND, "build/landstalker")); ap.add_argument("--verify-off", action="store_true")
    ap.add_argument("--counts"); ap.add_argument("--out"); ap.add_argument("--keep-traces"); ap.add_argument("--max-frames", type=int, default=0); ap.add_argument("--home-opts", action="store_true"); ap.add_argument("--env", action="append", default=[])
    a = ap.parse_args()
    a.jobs = max(1, min(a.jobs, 4))
    global HOME_OPTS; HOME_OPTS = a.home_opts
    for kv in a.env: EXTRA_ENV[kv.split("=", 1)[0]] = kv.split("=", 1)[1]
    jobs = [j for j in jobs_list() if not a.only or a.only in j["name"]]
    if a.keep_traces: os.makedirs(a.keep_traces, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    import atexit; atexit.register(shutil.rmtree, WORK, True)
    print("timebench: %d recordings, %d jobs, binary %s" % (len(jobs), a.jobs, a.bin), flush=True)
    t_all = time.time(); results = {}; allcounts = {}; offbad = []
    def task(j):
        r, c = run_one(j, a.bin, True, "", a.max_frames, a.keep_traces)
        if a.verify_off:
            r2, _ = run_one(j, a.bin, False, "_off", a.max_frames, None)
            r["off"] = "same" if (r2["ram"] == r["ram"] and r2["wav"] == r["wav"] and r2["chk"] == r["chk"]) else "DIFFERENT"
        return r, c
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(task, j): j for j in jobs}
        done = 0
        for f in cf.as_completed(futs):
            r, c = f.result(); done += 1
            results[r["name"]] = r; allcounts[r["name"]] = c
            extra = (" trace-off=" + r["off"]) if "off" in r else ""
            if r.get("off") == "DIFFERENT": offbad.append(r["name"])
            print("[%2d/%d] %s%s" % (done, len(jobs), fmt(r), extra), flush=True)
    lines = [fmt(results[k]) for k in sorted(results)]
    text = "# timebench %s binary=%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), a.bin) + "\n".join(lines) + "\n"
    if a.out: open(a.out, "w").write(text)
    if a.baseline:
        os.makedirs(os.path.dirname(os.path.abspath(a.baseline)), exist_ok=True); open(a.baseline, "w").write(text); print("baseline written:", a.baseline)
    if a.counts:
        kinds = sorted({k for c in allcounts.values() if c for k in c})
        with open(a.counts, "w") as f:
            f.write("# name " + " ".join(kinds) + "   (lines/events per kind)\n")
            for n in sorted(allcounts):
                c = allcounts[n] or {}
                f.write(n + " " + " ".join("%s=%d/%d" % (k, c.get(k, [0, 0])[0], c.get(k, [0, 0])[1]) for k in kinds) + "\n")
        print("counts written:", a.counts)
    ok_chk = sum(1 for r in results.values() if r["chk"] == "equal"); n_chk = sum(1 for r in results.values() if r["chk"] != "none")
    print("summary: %d recordings, %d of %d with .chk replay exactly, %d bad exits, total %.0f s wall" %
          (len(results), ok_chk, n_chk, sum(1 for r in results.values() if r["exit"] != 0), time.time() - t_all))
    rc = 0
    if offbad: print("TRACE CHANGES THE RESULT in:", " ".join(offbad)); rc = 1
    if a.compare:
        base = parse(a.compare); cur = parse_text(text)
        diffs = 0
        for n in sorted(set(base) | set(cur)):
            if a.only and a.only not in n: continue
            if n not in base or n not in cur: print("COMPARE: %s missing in %s" % (n, "baseline" if n not in base else "this run")); diffs += 1; continue
            for k in ("frames", "chk", "ram", "wav", "trace", "exit"):
                if base[n].get(k) != cur[n].get(k): print("COMPARE: %s %s: baseline %s, now %s" % (n, k, base[n].get(k), cur[n].get(k))); diffs += 1
        print("compare with %s: %s" % (a.compare, "IDENTICAL" if not diffs else "%d differences" % diffs))
        if diffs: rc = 1
    return rc

def parse_text(text):
    d = {}
    for ln in text.splitlines():
        p = ln.split()
        if not p or p[0][0] == "#": continue
        d[p[0]] = {kv.split("=", 1)[0]: kv.split("=", 1)[1] for kv in p[1:]}
    return d

if __name__ == "__main__":
    sys.exit(main())
