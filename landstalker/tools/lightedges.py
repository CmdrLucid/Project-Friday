#!/usr/bin/env python3
"""lightedges.py ROM ROOMS --run OUTDIR [--spots] [--sword] (--sword: also night sword-swing pictures with / without the glow; score them with --dir OUTDIR --swordscore) [--headless] [--top N]   (--spots: a grid of positions per room so every part of it is in a picture, not only the centre)   (GPU hidden window by default since 2026-11-12; --headless = unlit, useless for light)   -- finds HARD EDGES in the lighting (user 2026-11-05: 'bei Lichtquellen nach scharfen Kanten als potenziellen Fehler suchen')
   lightedges.py ROM ROOMS --dir OUTDIR             -- re-score the shots of an earlier --run
LIGHTEDGES_BIN=path runs another binary (e.g. a copy of the build before a change, for before / after pictures).
LIGHTEDGES_JOBS (4) runs in parallel, LIGHTEDGES_BATCH (16) warps per run; LIGHTEDGES_SWORD (1) glow colour, LIGHTEDGES_SWTIME (22) time of day of the --sword passes. Each run writes b??_?/interp.txt (interpreter fallback log, only if something ran there).
ROOMS: comma list of room numbers, or 'castle' (the Mercator castle interior rooms 51..97).
Per room a headless warp (replay prefix of rec_20261103_1803 up to Mercator, the user's save copied, never touched; Nigel at the walkable cell nearest the room's
centre, tools/proxysurvey.py start_cell) and one screenshot with Lighting Off and one with Lighting On (batches of 16 warps). Light ratio R = (On + 4) / (Off + 4)
per pixel (luminance); an EDGE pixel = R jumps by more than 0.25 to the right / lower neighbour while the Off picture itself has no edge there (luminance step < 12):
real light is soft, so such edges are almost always bugs (a light box around a torch = background on a collision column, frayed 16 x 16 shadow steps, pixel-jagged
figure shadows, a shadow block without a visible caster). Prints one line per room, most edge pixels first, and writes OUTDIR/edges_ROOM.png (On picture, edge
pixels magenta) for a look. HUD corners are left out. Local test aid: ROM-derived pictures stay in OUTDIR (never commit them)."""
import os, struct, subprocess, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proxysurvey as ps

REC = os.path.expanduser("~/Project-Friday-Test/aufnahmen/rec_20261103_1803"); T = "20261103_1803"
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

def rd(p):
    d = open(p, 'rb').read(); i = 8; idat = b''
    while i < len(d):
        n, = struct.unpack('>I', d[i:i + 4]); t = d[i + 4:i + 8]; c = d[i + 8:i + 8 + n]; i += 12 + n
        if t == b'IHDR': w, h, bd, ct = struct.unpack('>IIBB', c[:10])
        elif t == b'IDAT': idat += c
    ch = {2: 3, 6: 4}[ct]; raw = zlib.decompress(idat); s = w * ch; out = bytearray(); prev = bytearray(s); p = 0
    for y in range(h):
        f = raw[p]; line = bytearray(raw[p + 1:p + 1 + s]); p += 1 + s
        for x in range(s):
            a = line[x - ch] if x >= ch else 0; b = prev[x]; c = prev[x - ch] if x >= ch else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + b) & 255
            elif f == 3: line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c); pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c); line[x] = (line[x] + pr) & 255
        out += line; prev = line
    return w, h, ch, out

def wr(p, w, h, data):
    raw = b''.join(b'\x00' + bytes(data[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    def c(t, d): x = struct.pack('>I', len(d)) + t + d; return x + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    open(p, 'wb').write(b'\x89PNG\r\n\x1a\n' + c(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + c(b'IDAT', zlib.compress(raw)) + c(b'IEND', b''))

def spots(hm, all_spots):
    """the warp cells of a room: one at the centre (old sweep), or (--spots, 2026-11-15: the one-picture sweep missed room 66's far door) a grid in PICTURE space
    (u = x - y: 16 px per cell across, v = x + y: 8 px per cell down; the GPU picture shows ~22 x 25 cells) every 14 u / 20 v, each the free cell nearest the grid point"""
    c = ps.start_cell(hm)
    if not c or not all_spots: return [c] if c else []
    x0 = min(q[0] for q in hm); x1 = max(q[0] for q in hm); y0 = min(q[1] for q in hm); y1 = max(q[1] for q in hm); g = lambda q: hm.get(q, (0, False))   # (heights() leaves out the 0 words = free floor at height 0)
    seen = {c[0]}; todo = [c[0]]   # only cells Nigel can WALK to from the centre cell (free, height step <= 2): free cells outside the drawn room (behind walls, doorways) gave black pictures
    while todo:
        x, y = todo.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if x0 <= n[0] <= x1 and y0 <= n[1] <= y1 and n not in seen and not g(n)[1] and abs(g(n)[0] - g((x, y))[0]) <= 2: seen.add(n); todo.append(n)
    trig = {q for q, (h, bl) in hm.items() if not bl and h == 0}   # a non-zero word with height 0 = a door / trigger cell (room 66: the warp onto the door changed the room = black picture)
    free = [(xy, g(xy)[0]) for xy in seen if not any((xy[0] + dx, xy[1] + dy) in trig for dx in (-1, 0, 1) for dy in (-1, 0, 1))] or [(xy, g(xy)[0]) for xy in seen]
    us = [x - y for (x, y), _ in free]; vs = [x + y for (x, y), _ in free]; out = []
    for gu in range(min(us), max(us) + 14, 14):
        for gv in range(min(vs), max(vs) + 20, 20):
            best = min(free, key=lambda t: ((t[0][0] - t[0][1]) - gu) ** 2 + (((t[0][0] + t[0][1]) - gv) * 0.7) ** 2)
            if abs((best[0][0] - best[0][1]) - gu) <= 10 and abs((best[0][0] + best[0][1]) - gv) <= 14 and best not in out: out.append(best)
    return out or [c]

def run(rom_path, rooms, out, batch=int(os.environ.get("LIGHTEDGES_BATCH", "16")), jobs=int(os.environ.get("LIGHTEDGES_JOBS", "4")), gpu=False, all_spots=False, sword=False):
    rom = open(rom_path, "rb").read(); procs = []; plan = []
    assert batch <= 64, "LIGHTEDGES_BATCH > 64: LANDSTALKER_WARP takes at most 64 warps per run"
    jobs_all = []
    for r in rooms:
        for k, ((x, y), h) in enumerate(spots(ps.heights(rom, r), all_spots)): jobs_all.append((r, k, (x, y), h))
    print("lightedges: %d rooms, %d pictures" % (len(rooms), len(jobs_all)), flush=True)
    rooms = jobs_all
    qs = next((l.split("=", 1)[1].strip() for l in open(REC + ".cfg") if "QSPLAY" in l), "")
    for b in range(0, len(rooms), batch):
        warps, ats, shots, fr, part = [], [], [], 2100, []
        for r, sk, (x, y), h in jobs_all[b:b + batch]:
            warps.append("%d:%d.08,%d.08,%04X" % (r, x, y, 16 * h)); ats.append(str(fr)); shots.append(str(fr + 100)); part.append((r, fr + 100, sk)); fr += 160
        for light in ((0, 1, 2, 3) if sword else (0, 1)):   # --sword: 2 / 3 = night (LANDSTALKER_DAYTIME=22) and a sword swing per spot, 2 with the glow forced (LANDSTALKER_LIGHTING_SWORD), 3 without any glow (-1): same frames, only the glow differs
            d = os.path.join(out, "b%02d_%d" % (b // batch, light)); os.makedirs(os.path.join(d, "home"), exist_ok=True)
            subprocess.run("cp ~/Project-Friday-Test/aufnahmen/opts_%s/.landstalker_* %s/home/ 2>/dev/null; echo %d > %s/home/.landstalker_lighting; echo '0 0 19 1' > %s/home/.landstalker_display; cp ~/Project-Friday-Test/aufnahmen/save_%s.srm %s/s.srm" % (T, d, light, d, d, T, d), shell=True)   # 2026-11-15: CRT filter 0 (the CRT Pro scanlines turned soft light gradients into rows of false edges)
            with open(REC + ".txt") as f, open(os.path.join(d, "in.txt"), "w") as o:
                for l in f:
                    if int(l.split()[0]) < 2040: o.write(l)
                o.write("2040 0000\n")
                if light >= 2:
                    for _, f, _ in part: o.write("%d 0040\n%d 0000\n" % (f + 32, f + 36))   # attack button 8 frames before the swing picture f + 40 (0a396)
            env = dict(PATH=os.environ["PATH"], HOME=os.path.join(d, "home"), LANDSTALKER_WIDE="19", LANDSTALKER_TALL="1", LANDSTALKER_NATIVEPACE="1",
                       LANDSTALKER_QSPLAY=qs, GENRECOMP_INPUTSCRIPT=os.path.join(d, "in.txt"), LANDSTALKER_SAVE=os.path.join(d, "s.srm"),
                       LANDSTALKER_WARP=";".join(warps), LANDSTALKER_WARP_AT=",".join(ats), LANDSTALKER_SHOT=",".join(shots), LANDSTALKER_SHOT_SCALE="1", LANDSTALKER_SHOT_DIR=d,
                       LANDSTALKER_INTERP_LOG=os.path.join(d, "interp.txt"))   # 2026-11-25 bug sweep: every run logs interpreter fallback addresses
            if light >= 2:
                env.update(LANDSTALKER_DAYTIME=os.environ.get("LIGHTEDGES_SWTIME", "22"), LANDSTALKER_LIGHTING_SWORD=os.environ.get("LIGHTEDGES_SWORD", "1") if light == 2 else "-1")
                env["LANDSTALKER_SHOT"] = ",".join("%d" % (f + 40) for _, f, _ in part)
                with open(os.path.join(d, "home", ".landstalker_lighting"), "w") as q: q.write("1\n")
            if gpu:   # --gpu (2026-11-12): the GPU light the user plays with: a hidden window, the presented picture (present_FRAME_gpu.png)
                ps_ = env.pop("LANDSTALKER_SHOT"); env.update(LANDSTALKER_PRESENT_SHOT=ps_ if light >= 2 else ",".join(shots), LANDSTALKER_HIDDEN="1", LANDSTALKER_NOFOCUSPAUSE="1", SDL_AUDIODRIVER="dummy")
                env.update({k: os.environ[k] for k in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR") if k in os.environ})
            env.update({k: v for k, v in os.environ.items() if k.startswith("LANDSTALKER_LT_") or k.startswith("LANDSTALKER_LIGHTING_") or k.startswith("LANDSTALKER_DAY") or k.startswith("LANDSTALKER_CLOUD") or k.startswith("LANDSTALKER_WATER") or k.startswith("LANDSTALKER_DN") or k.startswith("LANDSTALKER_GPUCOMP") or k.startswith("LANDSTALKER_GL5")})   # test aids pass through (+ LANDSTALKER_GL5* GPU light debug views, 2026-11-24) (+ LANDSTALKER_DN* door light aids, e.g. LANDSTALKER_DN_PIDUMP, 2026-11-18) (e.g. LANDSTALKER_LT_AMB, LANDSTALKER_DAYTIME=15 = time of day)
            while len([p for p in procs if p.poll() is None]) >= jobs: procs[0].wait(); procs = [p for p in procs if p.poll() is None]
            print("lightedges: batch %d lighting %d: %d warps" % (b // batch, light, len(warps)), flush=True)
            procs.append(subprocess.Popen([os.environ.get("LIGHTEDGES_BIN") or os.path.join(HERE, "build", "landstalker")] + ([] if gpu else ["--headless"]) + ["--frames", str(fr + 20), rom_path], env=env,
                                          stdout=open(os.path.join(d, "out.log"), "w"), stderr=subprocess.STDOUT, cwd=HERE))
        plan += [(r, f, b // batch, k) for r, f, k in part]
    for p in procs: p.wait()
    with open(os.path.join(out, "plan.txt"), "w") as f:
        for r, fr, bi, k in plan: f.write("%d %d %d %d\n" % (r, fr, bi, k))

try:
    import numpy as np; from PIL import Image
except ImportError:
    np = None
MINRUN = int(os.environ.get('LIGHTEDGES_MINRUN', '40'))
RGBEDGE = os.environ.get('LIGHTEDGES_RGBEDGE', '0') == '1'   # 2026-11-25: 'no picture edge' checked per colour channel, not only on the luminance (red / black cushion patterns are flat in luminance)
MINABS = float(os.environ.get('LIGHTEDGES_MINABS', '0'))   # 2026-11-25: the added light must also jump by this much in luminance (8: dark patterns, e.g. the castle bench cushions, gave ratio 'edges' nobody can see)   # GPU pictures are 960 wide (2.7 px per game pixel): 40 px = a line of ~15 game pixels

def edges(po, pn, outp):
    """edge pixel count of the light ratio pn / po (po = reference picture), marked picture to outp"""
    if True:
        if np is not None:   # fast path (numpy + PIL, e.g. ~/Project-Friday-Test/hdvenv/bin/python): same rule as below
            A = np.asarray(Image.open(po).convert('RGB'), dtype=np.float32); B = np.asarray(Image.open(pn).convert('RGB'), dtype=np.float32); h, w = A.shape[:2]
            lo = A @ np.float32([0.3, 0.59, 0.11]); ln = B @ np.float32([0.3, 0.59, 0.11]); R = (ln + 4.0) / (lo + 4.0); hitm = np.zeros((h, w), bool)
            for dy, dx in ((0, 1), (1, 0)):
                a, b = (slice(0, h - dy), slice(0, w - dx)), (slice(dy, h), slice(dx, w))
                hitm[a] |= (lo[a] > 10) & (lo[b] > 10) & (lo[a] < 170) & (lo[b] < 170) & (np.abs(R[a] - R[b]) > 0.25) & (np.abs(lo[a] - lo[b]) < 12) & (np.abs((ln[a] - lo[a]) - (ln[b] - lo[b])) >= MINABS) & ((not RGBEDGE) | (np.abs(A[a] - A[b]).max(axis=-1) < 12))   # (< 170: flames / glowing sprites are bright already without the light: false alarms)
            k = w / 358.0; yy, xx = np.mgrid[0:h, 0:w]
            hitm &= ~((yy < 34 * k) | ((xx > w - 62 * k) & (yy < 52 * k)) | ((xx > w - 70 * k) & (yy > h - 22 * k))); hitm[h - 1, :] = False; hitm[:, w - 1] = False
            try:
                from scipy import ndimage   # 2026-11-25: connected components in C (the set walk below took ~2 s per picture: 5000+ pictures in the all-room sweep)
            except ImportError:
                ndimage = None
            if ndimage is not None:
                lab, nl = ndimage.label(hitm, structure=np.ones((3, 3), bool)); sz = np.bincount(lab.ravel()); sz[0] = 0
                keep = (sz >= MINRUN)[lab]; n = int(keep.sum()); M = B.astype(np.uint8).copy(); M[keep] = (255, 0, 255)
                Image.fromarray(M).save(outp, compress_level=1); return n
            hits = set((np.flatnonzero(hitm)).tolist()); mark = bytearray(B.astype(np.uint8).tobytes()); n = 0; seen = set()
            for i0 in hits:
                if i0 in seen: continue
                comp = [i0]; seen.add(i0); q = [i0]
                while q:
                    i = q.pop()
                    for d in (1, -1, w, -w, w + 1, w - 1, -w + 1, -w - 1):
                        j = i + d
                        if j in hits and j not in seen: seen.add(j); comp.append(j); q.append(j)
                if len(comp) >= MINRUN:
                    n += len(comp)
                    for i in comp: mark[i * 3:i * 3 + 3] = b'\xff\x00\xff'
            wr(outp, w, h, mark); return n
        w, h, ch, A = rd(po); _, _, ch2, B = rd(pn)
        L = lambda D, c, i: 0.3 * D[i * c] + 0.59 * D[i * c + 1] + 0.11 * D[i * c + 2]
        lo = [L(A, ch, i) for i in range(w * h)]; ln = [L(B, ch2, i) for i in range(w * h)]
        R = [(ln[i] + 4.0) / (lo[i] + 4.0) for i in range(w * h)]
        mark = bytearray(); n = 0; hits = set()
        for i in range(w * h): mark += bytes(B[i * ch2:i * ch2 + 3])
        for y in range(0, h - 1):
            for x in range(0, w - 1):
                k = w / 358.0
                if y < 24 * k or (x > w - 62 * k and y < 52 * k) or (x > w - 70 * k and y > h - 22 * k): continue   # HUD corners (scaled for the 960 wide GPU pictures)
                i = y * w + x; hit = False
                for j in (i + 1, i + w):
                    if lo[i] > 10 and lo[j] > 10 and abs(R[i] - R[j]) > 0.25 and abs(lo[i] - lo[j]) < 12: hit = True
                if hit: hits.add(i)
        n = 0; seen = set()   # 2026-11-15: only CONNECTED edge pixels count (>= MINRUN in one 8-neighbour cluster = a line); single specks on patterned walls near flames were false alarms
        for i0 in hits:
            if i0 in seen: continue
            comp = [i0]; seen.add(i0); q = [i0]
            while q:
                i = q.pop()
                for d in (1, -1, w, -w, w + 1, w - 1, -w + 1, -w - 1):
                    j = i + d
                    if j in hits and j not in seen: seen.add(j); comp.append(j); q.append(j)
            if len(comp) >= MINRUN:
                n += len(comp)
                for i in comp: mark[i * 3:i * 3 + 3] = b'\xff\x00\xff'
        wr(outp, w, h, mark); return n


def score(out, sword=False):
    """rows (edge px, room, spot, note); sword=True (--swordscore): the --sword pairs (night, during a swing: b??_3 without, b??_2 with the glow), pictures swedges_ROOM_SPOT.png"""
    rows = []
    for l in open(os.path.join(out, "plan.txt")):
        v = list(map(int, l.split())); r, fr, bi = v[:3]; sp = v[3] if len(v) > 3 else 0
        if sword:
            po, pn = [os.path.join(out, "b%02d_%d" % (bi, k), "present_%06d_gpu.png" % (fr + 40)) for k in (3, 2)]   # without / with the glow, same frame
        else:
            po, pn = [os.path.join(out, "b%02d_%d" % (bi, k), "shot_%06d_w358.png" % fr) for k in (0, 1)]
            if not os.path.isfile(po): po, pn = [os.path.join(out, "b%02d_%d" % (bi, k), "present_%06d_gpu.png" % fr) for k in (0, 1)]   # --gpu runs
        if not (os.path.isfile(po) and os.path.isfile(pn)): rows.append((-1, r, sp, "no shot")); continue
        rows.append((edges(po, pn, os.path.join(out, ("swedges_%d_%d.png" if sword else "edges_%d_%d.png") % (r, sp) if sword or sp else "edges_%d.png" % r)), r, sp, ""))
    return sorted(rows, reverse=True)

if __name__ == "__main__":
    a = sys.argv[1:]; rom_path = a[0]
    rooms = list(range(51, 98)) if a[1] == "castle" else [int(v) for v in a[1].split(",")]
    top = int(a[a.index("--top") + 1]) if "--top" in a else 40
    if "--run" in a: out = a[a.index("--run") + 1]; run(rom_path, rooms, out, gpu="--headless" not in a, all_spots="--spots" in a, sword="--sword" in a)   # GPU (hidden window) by default since 2026-11-12 (the CPU light is gone: headless = unlit); --gpu still accepted
    else: out = a[a.index("--dir") + 1]
    if "--run" in a and np is None:   # 2026-11-25: the pure Python scoring takes ~10 s per picture; score with a numpy Python (e.g. ~/Project-Friday-Test/hdvenv/bin/python ... --dir OUTDIR)
        print("lightedges: shots done; no numpy here: score them with ~/Project-Friday-Test/hdvenv/bin/python tools/lightedges.py ROM ROOMS --dir %s" % out); sys.exit(0)
    print("edge px  room spot  (pictures: %s/edges_ROOM[_SPOT].png, magenta = hard light edge without a picture edge)" % out)
    for n, r, k, note in score(out, "--swordscore" in a)[:top]: print("%7d  %4d  %3d  %s" % (n, r, k, note))
