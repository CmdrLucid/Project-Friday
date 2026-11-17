#!/usr/bin/env python3
"""Automatic sprint / smooth scrolling test (2026-11-17, user: 'warum haben wir dieses Zitterproblem immer wieder'): replays user recordings with
sprint passages through the GPU light path at the Steam Deck size (hidden 1280 x 800 window, sharp filter) and checks, frame by frame, that every
part of the picture moves like the world: the picture is cut into 48 x 48 tiles, each tile's shift to the next frame is found (best match, +-14 px);
the world shift of the frame = the most common non-zero shift. A tile that moves neither like the world nor stays still (Nigel, HUD) = JITTER;
the HUD box must not move at all; the world itself must move evenly (step change <= 1 px between frames = no 1 / 2 line wobble).
Recording-local test aid (ROM + recordings stay on the Deck); needs Pillow + numpy (~/.landstalker_trailer/venv/bin/python or hdvenv).
  sprinttest.py [CASE ...]         default: all cases below      sprinttest.py --list
Exit code 0 = all cases pass. Run it after every change to the picture path (renderer, light, filters, sprint, HUD)."""
import os, sys, subprocess, glob, collections
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); GAME = os.path.dirname(HERE)
REC = os.path.expanduser("~/Project-Friday-Test/aufnahmen")
OUT = os.path.expanduser("~/Project-Friday-Test/lktest/sprinttest")
# case: recording, first frame, last frame (a sprint passage), what it guards
CASES = {
    "shrine177": ("20261117_1737", 2890, 2915, "room 177 statues while sprinting past (user 2026-11-17)"),
    "shrine179": ("20261117_1737", 17700, 17725, "room 179 sprint on the platform in the light shaft"),
    "shrine180": ("20261117_1737", 22940, 22965, "room 180 sprint (user: jitter / light on the crate)"),
    "church700": ("20261116_2023", None, None, "church 700 books on the counter (0a459), frames from the recording's first sprint"),
}
HUD = (0, 0, 260, 72)   # Modern HUD hearts / sword bar at 1280 x 800 (must not move)
HUDZONES = ((0, 0, 300, 135), (1060, 0, 1280, 140), (1120, 740, 1280, 800))   # tiles touching the HUD (hearts + sword bar, item discs, gold) mix still and moving pixels: not judged


def sprint_ranges(rec):
    q = ""
    for ln in open(os.path.join(REC, "rec_%s.cfg" % rec)):
        if "QSPLAY=" in ln: q = ln.split("QSPLAY=", 1)[1].split()[0]
    ev = [(int(t[1:]), t[0]) for t in q.split(",") if t[:1] in "pr" and t[1:].isdigit()]
    out = []; start = None
    for f, k in ev:
        if k == "p": start = f
        elif start is not None: out.append((start, f)); start = None
    return out


def shots(rec, a, b, d):
    if os.environ.get("SPRINTTEST_REUSE") and glob.glob(os.path.join(d, "present_*_gpu.png")): return sorted(glob.glob(os.path.join(d, "present_*_gpu.png")))   # analysis only (test aid)
    env = dict(os.environ, EXTRA="LANDSTALKER_WINSIZE=1280x800", NOCRT="1")
    subprocess.run([os.path.join(HERE, "lightshots.sh"), os.path.join(REC, "rec_" + rec), d, ",".join(str(f) for f in range(a, b + 1))],
                   env=env, cwd=GAME, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return sorted(glob.glob(os.path.join(d, "present_*_gpu.png")))


def shift(a, b, x0, y0, x1, y1, r=14):
    p = a[y0:y1, x0:x1]; best = None
    if p.std() < 6: return None   # flat tile (black void, plain colour): no information
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if y0 + dy < 0 or x0 + dx < 0 or y1 + dy > b.shape[0] or x1 + dx > b.shape[1]: continue
            s = np.abs(p - b[y0 + dy:y1 + dy, x0 + dx:x1 + dx]).mean()
            if best is None or s < best[0]: best = (s, dx, dy)
    return best


def check(name):
    rec, a, b, what = CASES[name]
    if a is None:
        rs = [r for r in sprint_ranges(rec) if r[1] - r[0] >= 40]
        if not rs: return name, None, "no sprint passage in the recording"
        a = rs[0][0] + 10; b = a + 25
    d = os.path.join(OUT, name)
    fs = shots(rec, a, b, d)
    if len(fs) < b - a + 1: return name, False, "only %d pictures (replay out of sync?)" % len(fs)
    L = [np.asarray(Image.open(f).convert("L")).astype(np.float32) for f in fs]
    T = 48; H, W = L[0].shape; bad = []; steps = []; hudmove = 0; res = {}   # res[tile][frame] = movement minus the world movement
    def sad(A, B2, x, y, dx, dy):
        if y + dy < 0 or x + dx < 0 or y + T + dy > H or x + T + dx > W: return 1e9
        return float(np.abs(A[y:y + T, x:x + T] - B2[y + dy:y + T + dy, x + dx:x + T + dx]).mean())
    for i in range(len(L) - 1):
        A, B2 = L[i], L[i + 1]
        cnt = collections.Counter()
        for (x, y) in ((W // 4, H // 4), (3 * W // 4, H // 4), (W // 4, 3 * H // 4), (3 * W // 4, 3 * H // 4), (W // 2, H - 140)):
            m = shift(A, B2, x, y, x + T, y + T)
            if m and m[0] < 12 and (m[1], m[2]) != (0, 0): cnt[(m[1], m[2])] += 1
        if not cnt: continue
        world = cnt.most_common(1)[0][0]; steps.append(world)
        cand = [(world[0] + ex, world[1] + ey) for ex in (-2, -1, 0, 1, 2) for ey in (-2, -1, 0, 1, 2)] + [(0, 0)]
        for y in range(80, H - T - 16, T):
            for x in range(16, W - T - 16, T):
                if A[y:y + T, x:x + T].std() < 6 or any(x < z[2] and x + T > z[0] and y < z[3] and y + T > z[1] for z in HUDZONES): continue
                sc = sorted((sad(A, B2, x, y, dx, dy), (dx, dy)) for dx, dy in cand)
                v = sc[0][1]
                if sc[0][0] < 12 and v != (0, 0) and (v == world or sc[0][0] < 0.85 * sad(A, B2, x, y, *world)): res.setdefault((x, y), {})[i] = (v[0] - world[0], v[1] - world[1])
        h = shift(A, B2, *HUD, r=3)
        if h and (h[1], h[2]) != (0, 0) and h[0] < 12: hudmove += 1
    # JITTER = a tile whose deviation from the world flips back and forth (+1 / -1 / +1 ...) over consecutive frames; a figure that really moves (platform,
    # enemy) deviates steadily and is no jitter
    for k, rr in res.items():
        flips = 0
        for i in sorted(rr):
            if i + 1 in rr:
                p, q = rr[i], rr[i + 1]
                if (p[1] * q[1] < 0) or (p[0] * q[0] < 0): flips += 1
        if flips >= 3: bad.append((a + min(rr) + 1, k, rr[min(rr)], flips))
    wob = sum(1 for s0, s1 in zip(steps[2:], steps[3:]) if abs(s1[1] - s0[1]) > 1 or abs(s1[0] - s0[0]) > 1)   # (the first frames may still accelerate)
    ok = not bad and wob == 0 and hudmove == 0
    msg = "frames %d..%d: %d jitter tiles, world wobble %d, HUD moved %d; world steps %s" % (a, b, len(bad), wob, hudmove, " ".join("%+d,%+d" % s for s in steps[:8]))
    if bad: msg += "; first jitter tile %s (deviation %s, %d flips); jitter tiles by picture row (y): %s" % (bad[0][1], bad[0][2], bad[0][3], dict(sorted(collections.Counter(t[1][1] for t in bad).items())))
    return name, ok, msg


if __name__ == "__main__":
    if "--list" in sys.argv:
        for k, v in CASES.items(): print(k, v)
        sys.exit(0)
    names = [n for n in sys.argv[1:] if n in CASES] or list(CASES)
    fail = 0
    for n in names:
        name, ok, msg = check(n)
        print("%-10s %s  %s" % (name, "PASS" if ok else ("SKIP" if ok is None else "FAIL"), msg), flush=True)
        fail += ok is False
    sys.exit(1 if fail else 0)
