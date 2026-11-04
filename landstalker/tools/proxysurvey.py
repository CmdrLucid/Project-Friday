#!/usr/bin/env python3
"""proxysurvey.py ROM [ROOMS] [--run OUTDIR] [--log LOG] [--top N]   -- ranks the outdoor rooms whose AUTOMATIC light proxies look wrong
(docs/LIGHT_PROXY_PLAN.md 'Blender shapes'), so the next Blender one-offs can be picked without walking there.
--run: headless runs of build/landstalker (batches of 16 warps, 4 in parallel) that warp through all ROOMS (default: every outdoor room of lk_lt_isout = tilesets 0 / 7 / 12 / 13 / 14 / 17)
       with LANDSTALKER_LIGHTING_DBG=5 (replay prefix of a user recording that ends in Mercator; the user's save is copied, never touched); --log: reuse such a log.
Per room it reads the 'proxy: room R #n hip / lathe' and 'object N flat (drawn H high)' lines and the room's height map (tools/romroom.py) and scores:
  WALK   a hip / lathe standing over WALKABLE cells (free height map cells; for a hip only the cells of its part = height z0) more than 24 units above\n         their floor = Nigel walks inside a shape (worst kind);
  TENT   a hip whose ridge is far above its eave on a narrow box (ridge - eave > 2 x the short side): usually a wall or tower read as a roof;
  FLAT   an object left flat although it is drawn >= 60 high (walls, towers, gates without any shape);
  WALL0  long runs of blocked height 0 cells next to walkable floor (walls the height map does not hold; check the picture).
Prints one line per room, worst first. Local test aid: ROM, logs and pictures stay on the Deck."""
import os, re, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import romroom

ROM_DEF = "/home/deck/Documents/NonSteamGames/landstalker/landstalker.md"
REC = os.path.expanduser("~/aufnahmen/rec_20261103_1803")   # a recording that reaches Mercator 632 by frame 2040 (any loaded game works)

def outdoor_rooms(rom):
    tab = struct.unpack('>I', rom[0xA0A00:0xA0A04])[0]
    return [r for r in range(816) if (rom[tab + 8 * r + 4] & 0x1F) in (0, 7, 12, 13, 14, 17) and not (139 <= r <= 143) and r not in (148, 643)]

def heights(rom, room):
    """{(cell x, cell y): (height step, blocked)} in WORLD cells (height map index + 12, FORMATS 'Height map')"""
    a = romroom.arrays(romroom.decode(rom, room))['HM']
    return {(x + 12, y + 12): ((v >> 8) & 15, bool((v >> 8) & 0x60)) for (x, y), v in a.items() if v}

def start_cell(hm):
    free = [(c, h) for c, (h, b) in hm.items() if not b]
    if not free: return None
    cx = sum(c[0] for c, _ in free) / len(free); cy = sum(c[1] for c, _ in free) / len(free)
    return min(free, key=lambda t: (t[0][0] - cx) ** 2 + (t[0][1] - cy) ** 2)

def run(rom, rooms, out, batch=16, jobs=4):
    """headless runs of build/landstalker (patch_warp.py arms at most 16 warps per run: batches, `jobs` in parallel) -> one combined log"""
    T = os.path.basename(REC)[4:]; here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    qs = next((l.split("=", 1)[1].strip() for l in open(REC + ".cfg") if "QSPLAY" in l), "")
    procs, logs = [], []
    for b in range(0, len(rooms), batch):
        d = os.path.join(out, "b%02d" % (b // batch)); os.makedirs(os.path.join(d, "home"), exist_ok=True)
        subprocess.run("cp ~/aufnahmen/opts_%s/.landstalker_* %s/home/ 2>/dev/null; echo 1 > %s/home/.landstalker_lighting; cp ~/aufnahmen/save_%s.srm %s/s.srm" % (T, d, d, T, d), shell=True)
        with open(REC + ".txt") as f, open(os.path.join(d, "in.txt"), "w") as o:
            for l in f:
                if int(l.split()[0]) < 2040: o.write(l)
            o.write("2040 0000\n")
        warps, ats, fr = [], [], 2100
        for r in rooms[b:b + batch]:
            s = start_cell(heights(rom, r))
            if not s: continue
            (x, y), h = s; warps.append("%d:%d.08,%d.08,%04X" % (r, x, y, 16 * h)); ats.append(str(fr)); fr += 160
        env = dict(PATH=os.environ["PATH"], HOME=os.path.join(d, "home"), LANDSTALKER_WIDE="19", LANDSTALKER_TALL="1", LANDSTALKER_NATIVEPACE="1",
                   LANDSTALKER_QSPLAY=qs, GENRECOMP_INPUTSCRIPT=os.path.join(d, "in.txt"), LANDSTALKER_SAVE=os.path.join(d, "s.srm"),
                   LANDSTALKER_WARP=";".join(warps), LANDSTALKER_WARP_AT=",".join(ats), LANDSTALKER_LIGHTING_DBG="5")
        log = os.path.join(d, "survey.log"); logs.append(log)
        while len([p for p in procs if p.poll() is None]) >= jobs: procs[0].wait(); procs = [p for p in procs if p.poll() is None]
        print("proxysurvey: batch %d: %d warps -> %s" % (b // batch, len(warps), log), flush=True)
        procs.append(subprocess.Popen([os.path.join(here, "build", "landstalker"), "--headless", "--frames", str(fr + 20), rom_path], env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT, cwd=here))
    for p in procs: p.wait()
    allp = os.path.join(out, "survey.log")
    with open(allp, "w") as o:
        for l in logs: o.write(open(l, errors="replace").read())
    return allp

def score(rom, log):
    per = {}
    hip = re.compile(r"proxy: room (\d+) #(\d+) hip x (\d+)\.\.(\d+) y (\d+)\.\.(\d+) z0 (-?\d+) eave (-?\d+) ridge (-?\d+)")
    lat = re.compile(r"proxy: room (\d+) #(\d+) lathe at (\d+),(\d+) z (-?\d+)\.\.(-?\d+) max r (\d+)")
    flt = re.compile(r"proxy: room (\d+) object (\d+) flat \(drawn (\d+) high\)")
    seen = set()
    for l in open(log, errors="replace"):
        m = hip.search(l) or lat.search(l) or flt.search(l)
        if not m: continue
        key = (m.re.pattern[:20],) + m.groups()
        if key in seen: continue
        seen.add(key); per.setdefault(int(m.group(1)), []).append((m.re, m.groups()))
    rows = []
    for room, items in per.items():
        hm = heights(rom, room); walk = tent = flat = 0; notes = []
        for rx, g in items:
            if rx is hip:
                x0, x1, y0, y1, z0, ze, zr = map(int, g[2:])
                # the game stamps a hip only on its PART's own cells (equal height cells of the object = height z0), not on the whole box
                bad = [(cx, cy) for cx in range(x0 // 16, (x1 + 15) // 16) for cy in range(y0 // 16, (y1 + 15) // 16)
                       if (cx, cy) in hm and not hm[(cx, cy)][1] and 16 * hm[(cx, cy)][0] == z0 and zr - z0 > 24]
                if bad: walk += len(bad); notes.append("WALK hip #%s x %d..%d y %d..%d ridge %d over %d walkable cells" % (g[1], x0, x1, y0, y1, zr, len(bad)))
                if zr - ze > 2 * min(x1 - x0, y1 - y0): tent += 1; notes.append("TENT hip #%s x %d..%d y %d..%d eave %d ridge %d" % (g[1], x0, x1, y0, y1, ze, zr))
            elif rx is lat:
                x, y, za, zb, r = map(int, g[2:]); c = (x // 16, y // 16)
                if c in hm and not hm[c][1] and zb - 16 * hm[c][0] > 24: walk += 1; notes.append("WALK lathe #%s at %d,%d top %d on a walkable cell" % (g[1], x, y, zb))
            else:
                if int(g[2]) >= 60: flat += 1; notes.append("FLAT object %s drawn %s high" % (g[1], g[2]))
        free = {c for c, (h, b) in hm.items() if not b}
        wall0 = sum(1 for c, (h, b) in hm.items() if b and h == 0 and any((c[0] + dx, c[1] + dy) in free for dx, dy in ((1, 0), (0, 1))))
        rows.append((3 * walk + 2 * tent + 2 * flat + wall0 // 40, room, walk, tent, flat, wall0, notes))
    return sorted(rows, reverse=True)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    pos = [a for i, a in enumerate(args) if not a.startswith("-") and not (i and args[i - 1] in ("--run", "--log", "--top"))]   # positionals, not option values
    rom_path = pos[0] if pos else ROM_DEF
    rom = open(rom_path, "rb").read()
    rooms = [int(r) for r in pos[1].split(",")] if len(pos) > 1 else outdoor_rooms(rom)
    top = int(args[args.index("--top") + 1]) if "--top" in args else 40
    log = args[args.index("--log") + 1] if "--log" in args else run(rom, rooms, args[args.index("--run") + 1] if "--run" in args else "/tmp/proxysurvey")
    rows = score(rom, log)
    try: names = {int(l.split("|")[1]): l.split("|")[3].strip() for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "ROOMS.md")) if l.startswith("| ") and l.split("|")[1].strip().isdigit()}
    except OSError: names = {}
    try: import json; done = set(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "light_proxies.json")))["rooms"])
    except (OSError, ValueError): done = set()
    print("score room  WALK TENT FLAT WALL0  name   (* = room already has corrections in data/light_proxies.json; the log shows the automatic shapes before them)")
    for s, room, walk, tent, flat, wall0, notes in rows[:top]:
        print("%5d %4d%s %4d %4d %4d %5d  %s" % (s, room, "*" if str(room) in done else " ", walk, tent, flat, wall0, names.get(room, "")))
        for n in notes[:6]: print("            " + n)
