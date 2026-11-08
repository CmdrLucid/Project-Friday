#!/usr/bin/env python3
"""lightedges.py ROM ROOMS --run OUTDIR [--top N]   -- finds HARD EDGES in the lighting (user 2026-11-05: 'bei Lichtquellen nach scharfen Kanten als potenziellen Fehler suchen')
   lightedges.py ROM ROOMS --dir OUTDIR             -- re-score the shots of an earlier --run
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

REC = os.path.expanduser("~/aufnahmen/rec_20261103_1803"); T = "20261103_1803"
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

def run(rom_path, rooms, out, batch=16, jobs=4):
    rom = open(rom_path, "rb").read(); procs = []; plan = []
    qs = next((l.split("=", 1)[1].strip() for l in open(REC + ".cfg") if "QSPLAY" in l), "")
    for b in range(0, len(rooms), batch):
        warps, ats, shots, fr, part = [], [], [], 2100, []
        for r in rooms[b:b + batch]:
            s = ps.start_cell(ps.heights(rom, r))
            if not s: continue
            (x, y), h = s; warps.append("%d:%d.08,%d.08,%04X" % (r, x, y, 16 * h)); ats.append(str(fr)); shots.append(str(fr + 100)); part.append((r, fr + 100)); fr += 160
        for light in (0, 1):
            d = os.path.join(out, "b%02d_%d" % (b // batch, light)); os.makedirs(os.path.join(d, "home"), exist_ok=True)
            subprocess.run("cp ~/aufnahmen/opts_%s/.landstalker_* %s/home/ 2>/dev/null; echo %d > %s/home/.landstalker_lighting; cp ~/aufnahmen/save_%s.srm %s/s.srm" % (T, d, light, d, T, d), shell=True)
            with open(REC + ".txt") as f, open(os.path.join(d, "in.txt"), "w") as o:
                for l in f:
                    if int(l.split()[0]) < 2040: o.write(l)
                o.write("2040 0000\n")
            env = dict(PATH=os.environ["PATH"], HOME=os.path.join(d, "home"), LANDSTALKER_WIDE="19", LANDSTALKER_TALL="1", LANDSTALKER_NATIVEPACE="1",
                       LANDSTALKER_QSPLAY=qs, GENRECOMP_INPUTSCRIPT=os.path.join(d, "in.txt"), LANDSTALKER_SAVE=os.path.join(d, "s.srm"),
                       LANDSTALKER_WARP=";".join(warps), LANDSTALKER_WARP_AT=",".join(ats), LANDSTALKER_SHOT=",".join(shots), LANDSTALKER_SHOT_SCALE="1", LANDSTALKER_SHOT_DIR=d)
            env.update({k: v for k, v in os.environ.items() if k.startswith("LANDSTALKER_LT_") or k.startswith("LANDSTALKER_LIGHTING_") or k.startswith("LANDSTALKER_DAY") or k.startswith("LANDSTALKER_CLOUD")})   # test aids pass through (e.g. LANDSTALKER_LT_AMB, LANDSTALKER_DAYTIME=15 = time of day)
            while len([p for p in procs if p.poll() is None]) >= jobs: procs[0].wait(); procs = [p for p in procs if p.poll() is None]
            print("lightedges: batch %d lighting %d: %d warps" % (b // batch, light, len(warps)), flush=True)
            procs.append(subprocess.Popen([os.path.join(HERE, "build", "landstalker"), "--headless", "--frames", str(fr + 20), rom_path], env=env,
                                          stdout=open(os.path.join(d, "out.log"), "w"), stderr=subprocess.STDOUT, cwd=HERE))
        plan += [(r, f, b // batch) for r, f in part]
    for p in procs: p.wait()
    with open(os.path.join(out, "plan.txt"), "w") as f:
        for r, fr, bi in plan: f.write("%d %d %d\n" % (r, fr, bi))

def score(out):
    rows = []
    for l in open(os.path.join(out, "plan.txt")):
        r, fr, bi = map(int, l.split())
        po, pn = [os.path.join(out, "b%02d_%d" % (bi, k), "shot_%06d_w358.png" % fr) for k in (0, 1)]
        if not (os.path.isfile(po) and os.path.isfile(pn)): rows.append((-1, r, "no shot")); continue
        w, h, ch, A = rd(po); _, _, ch2, B = rd(pn)
        L = lambda D, c, i: 0.3 * D[i * c] + 0.59 * D[i * c + 1] + 0.11 * D[i * c + 2]
        lo = [L(A, ch, i) for i in range(w * h)]; ln = [L(B, ch2, i) for i in range(w * h)]
        R = [(ln[i] + 4.0) / (lo[i] + 4.0) for i in range(w * h)]
        mark = bytearray(); n = 0
        for i in range(w * h): mark += bytes(B[i * ch2:i * ch2 + 3])
        for y in range(24, h - 1):
            for x in range(0, w - 1):
                if (x > w - 62 and y < 52) or (x > w - 70 and y > h - 22): continue   # HUD corners
                i = y * w + x; hit = False
                for j in (i + 1, i + w):
                    if lo[i] > 10 and lo[j] > 10 and abs(R[i] - R[j]) > 0.25 and abs(lo[i] - lo[j]) < 12: hit = True
                if hit: n += 1; mark[i * 3:i * 3 + 3] = b'\xff\x00\xff'
        wr(os.path.join(out, "edges_%d.png" % r), w, h, mark); rows.append((n, r, ""))
    return sorted(rows, reverse=True)

if __name__ == "__main__":
    a = sys.argv[1:]; rom_path = a[0]
    rooms = list(range(51, 98)) if a[1] == "castle" else [int(v) for v in a[1].split(",")]
    top = int(a[a.index("--top") + 1]) if "--top" in a else 40
    if "--run" in a: out = a[a.index("--run") + 1]; run(rom_path, rooms, out)
    else: out = a[a.index("--dir") + 1]
    print("edge px  room   (pictures: %s/edges_ROOM.png, magenta = hard light edge without a picture edge)" % out)
    for n, r, note in score(out)[:top]: print("%7d  %4d  %s" % (n, r, note))
