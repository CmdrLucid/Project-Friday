#!/usr/bin/env python3
"""bootcol_check.py -- reference + check sheets for the Boot Colors option (tools/patch_bootcol.py, 2026-11-04).
The SEEDS / CUT tables below are the ONE source of the hand fixes: patch_bootcol.py imports them and writes the C table.
  bootcol_check.py sheet ROM OUT.png [FIRST LAST]   numbered pose sheet (Nigel = sprite graphic 0, magenta = boot pixels; the
                                                    numbers are the ones the user names, order of first appearance)
  bootcol_check.py mock ROM OUT.png N,N,.. [KIND,..] poses (1-based numbers) in the boots' colours (0 = original, 5..8, -1 = magenta)
  bootcol_check.py cmp ROM LOG                       compare with a run of the game with LANDSTALKER_BOOTCOL=1 LANDSTALKER_BOOTCOL_DBG=1
                                                    (every 'bootcol: anim A frm F boot px N' line must equal the reference)
Rule (same as the C code): 4-connected areas of the browns 3 / 4 / 5 / 8 of the assembled pose; an area is a boot when its centre lies
in the lowest 30 % of a figure at least 34 px tall, unless it is small (< 20 px) and touches entry 1 / 13 / 14 (scabbard highlight,
sword colours); poses in SEEDS take exactly the areas holding the seed pixels; CUT drops boot pixels above a row; animation $48
frames >= 20 are not Nigel; CUT boxes are never boot (scabbard ends merged into a boot).  Output images stay local (they show ROM graphics)."""
import os, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# (animation, frame) -> seed pixels in pose space (checked with the user on numbered sheets 2026-11-04)
SEEDS = {
    (0x08, 12): [(-1, -7), (-10, -13), (-11, -8), (-12, -6), (-10, 0), (-11, -1)],   # pose 6: walk, raised sole, its rim sat too high
    (0x18, 12): [(-1, -7), (-10, -13), (-11, -8), (-12, -6), (-10, 0), (-11, -1)],   # pose 28 = same picture
    (0x38, 4): [(-4, -12), (-5, -5), (-9, -8), (-2, -6), (1, -5)],                    # pose 54: swing arc (sword colours) touches the boots, back boot
    (0x3C, 4): [(-9, -1), (-10, -9)],                                                 # pose 58: boot cuff above a grey strap
    (0x40, 8): [(-4, -5), (6, -15)],                                                  # lying / falling poses (bed picture and gloves left out)
    (0x44, 4): [(-1, 0)], (0x44, 8): [(-12, -6), (-1, -1)], (0x44, 16): [(-12, -6), (-1, -1)], (0x44, 12): [(-11, -6), (-1, -2)],
    (0x48, 4): [(-1, -10)], (0x48, 8): [(-1, -9), (-10, -12)], (0x48, 16): [(-1, -9), (-10, -12)], (0x48, 12): [(-1, -10), (-9, -12)],
}
# (animation, frame) -> box (x0, y0, x1, y1) or list of boxes of pixels that are never boot: the scabbard end runs into the boot without an outline
CUT = {(0x20, 0): (-128, -128, 127, -8), (0x28, 0): (-128, -128, 127, -8),   # poses 41 / 45 (jump): everything above the boot shaft
       (0x08, 12): (-2, -7, 0, -5), (0x18, 12): (-2, -7, 0, -5),             # poses 6 / 28 (walk): the scabbard end on the right boot
       (0x1C, 4): (12, -9, 14, -8),                                          # pose 34: scabbard end right of the boot top
       (0x40, 0): [(-7, -10, -4, -9), (-9, -8, -5, -8), (-9, -7, -6, -7), (-9, -6, -7, -6)]}                                         # pose 61: scabbard end on the left boot
NOTES = {(0x08, 12): 'walk, raised sole: its rim sat too high for the 30 % rule', (0x38, 4): 'swing: the arc (sword colours) touches the boots',
         (0x3C, 4): 'swing: boot cuff above a grey strap', (0x20, 0): 'jump: the scabbard end runs into the boot shaft without an outline'}   # C comments
BROWN = {3, 4, 5, 8}
BOOTCOL = {0: (0x0ACE, 0x04AE, 0x0048, 0x0024), 5: (0x0ECC, 0x0E88, 0x0A44, 0x0622), 6: (0x0EEE, 0x0AAA, 0x0886, 0x0444),
           7: (0x0AEA, 0x04C4, 0x0282, 0x0040), 8: (0x0A8A, 0x0646, 0x0424, 0x0202)}   # entries 8 / 3 / 4 / 5, must match lk_bc_col

def _boxes(key):
    v = CUT.get(key, [])
    return [v] if isinstance(v, tuple) else list(v)

def c_table():
    """the lk_bc_seed table for patch_bootcol.py"""
    n = max(len(v) for v in SEEDS.values()); keys = sorted(set(SEEDS) | set(CUT)); lines = []
    for i, (a, f) in enumerate(keys):
        sd = SEEDS.get((a, f), [])
        xs = ', '.join(str(x) for x, _ in sd) or '0'; ys = ', '.join(str(y) for _, y in sd) or '0'
        bx = (_boxes((a, f)) + [(1, 1, 0, 0)] * 4)[:4]
        e = '  { 0x%02X, %d, %d, { %s }, { %s }, { %s } }' % (a, f, len(sd), ', '.join('{ %d, %d, %d, %d }' % q for q in bx), xs, ys) + (',' if i < len(keys) - 1 else ' };')
        if (a, f) in NOTES: e += '   /* ' + NOTES[(a, f)] + ' */'
        lines.append(e)
    return ('static const struct { uint8 anim, frm, n; int8_t cut[4][4], x[%d], y[%d]; } lk_bc_seed[] = {   /* from tools/bootcol_check.py SEEDS / CUT: n > 0 = the boot '
            'areas are the ones holding these pixels (pose space); cut = up to 4 boxes x0, y0, x1, y1 of pixels that are never boot (x0 > x1 = none) */\n' % (n, n) + '\n'.join(lines) + '\n')

def _rom_helpers(rom):
    import romsprite
    L = lambda a: struct.unpack('>I', rom[a:a + 4])[0]
    W = lambda a: struct.unpack('>H', rom[a:a + 2])[0]
    return romsprite, L, W

def poses(rom):
    """[(anim, frame, frame pointer)] of sprite graphic 0 in table order, first appearance of each picture first"""
    romsprite, L, W = _rom_helpers(rom)
    base = L(0x120000); a0 = base + W(0x120004) * 4; a1 = base + W(0x120008) * 4
    aps = [L(a) for a in range(a0, a1, 4)]; allap = sorted(set(aps)); out = []; seen = set()
    for ai, ap in enumerate(aps):
        nxt = min([p for p in allap if p > ap] + [ap + 64])
        for k, fa in enumerate(range(ap, nxt, 4)):
            fp = L(fa)
            if fp not in seen: seen.add(fp); out.append((ai * 4, k * 4, fp))
    return [p for p in out if not (p[0] == 0x48 and p[1] >= 20)]

def all_keys(rom):
    romsprite, L, W = _rom_helpers(rom)
    base = L(0x120000); a0 = base + W(0x120004) * 4; a1 = base + W(0x120008) * 4
    aps = [L(a) for a in range(a0, a1, 4)]; allap = sorted(set(aps)); out = {}
    for ai, ap in enumerate(aps):
        nxt = min([p for p in allap if p > ap] + [ap + 64])
        for k, fa in enumerate(range(ap, nxt, 4)): out[(ai * 4, k * 4)] = L(fa)
    return out

def render(rom, fp):
    """pose pixels {(x, y): palette entry} (pieces in order, tiles column-major per piece, like lk_o_sprpiece)"""
    romsprite, L, W = _rom_helpers(rom)
    s8 = lambda v: v - 256 if v > 127 else v
    pos = fp; pieces = []
    while True:
        b1, b2 = rom[pos], rom[pos + 1]; pos += 2
        pieces.append((s8((b2 << 1) & 0xF8), s8((b1 << 1) & 0xF8), (b1 & 3) + 1, (b2 & 3) + 1))
        if b2 & 0x80 or len(pieces) >= 8: break
    tiles = bytearray()
    while True:
        h = W(pos); pos += 2; n = h & 0xFFF
        if h & 0x8000: tiles += bytes(n * 2)
        elif h & 0x2000: tiles += romsprite.romgfx.lz77(rom, pos)[0]; break
        else: tiles += rom[pos:pos + n * 2]; pos += n * 2
        if h & 0x4000: break
    pix = {}; t = 0
    for (x, y, w, hh) in pieces:
        for cx in range(w):
            for cy in range(hh):
                td = tiles[t * 32:(t + 1) * 32]; t += 1
                if len(td) < 32: continue
                for py in range(8):
                    for px in range(8):
                        b = td[py * 4 + px // 2]; c = (b >> 4) if px % 2 == 0 else b & 15
                        if c: pix[(x + cx * 8 + px, y + cy * 8 + py)] = c
    return pix

def comps(pix):
    seen = set(); out = []
    for p, c in pix.items():
        if c not in BROWN or p in seen: continue
        st = [p]; seen.add(p); cc = []
        while st:
            q = st.pop(); cc.append(q)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                r = (q[0] + d[0], q[1] + d[1])
                if r not in seen and pix.get(r) in BROWN: seen.add(r); st.append(r)
        out.append(cc)
    return out

def boots(pix, key):
    if (key[0] == 0x48 and key[1] >= 20) or not pix: return set()
    res = set()
    if key in SEEDS:
        for cc in comps(pix):
            if any(s in cc for s in SEEDS[key]): res |= set(cc)
    else:
        ys = [y for _, y in pix]; bot = max(ys); H = bot - min(ys) + 1
        for cc in comps(pix):
            if H < 34 or sum(y for _, y in cc) * 10 < len(cc) * (10 * bot - 3 * H): continue
            if len(cc) < 20 and any(pix.get((x + dx, y + dy)) in (1, 13, 14) for x, y in cc for dx in (-1, 0, 1) for dy in (-1, 0, 1)): continue
            res |= set(cc)
    for x0, y0, x1, y1 in _boxes(key): res = {q for q in res if not (x0 <= q[0] <= x1 and y0 <= q[1] <= y1)}
    return res

def _png(path, buf, S):
    rows = []
    for r in buf:
        rr = b''.join(bytes(px) * S for px in r)
        rows += [rr] * S
    raw = b''.join(b'\0' + r for r in rows)
    ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', len(buf[0]) * S, len(rows), 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))

def _pal(rom):
    import romsprite
    return romsprite.sprite_palettes(rom, [], 0, 0)

def _rgb(w): return (((w >> 1) & 7) * 36, ((w >> 5) & 7) * 36, ((w >> 9) & 7) * 36)

DIG = {'0': '111101101101111', '1': '010110010010111', '2': '111001111100111', '3': '111001111001111', '4': '101101111001001',
       '5': '111100111001111', '6': '111100111101111', '7': '111001010010010', '8': '111101111101111', '9': '111101111001111'}

def sheet(rom, out, first=1, last=None):
    pal = _pal(rom); ps = poses(rom); last = last or len(ps); sel = list(range(first - 1, last))
    cols, cw, chh = 12, 58, 70; nrows = (len(sel) + cols - 1) // cols
    buf = [[(40, 40, 48)] * (cols * cw) for _ in range(nrows * chh)]
    for j, k in enumerate(sel):
        bx, by = (j % cols) * cw, (j // cols) * chh
        for i, ch in enumerate(str(k + 1)):
            for q, v in enumerate(DIG[ch]):
                if v == '1': buf[by + 2 + q // 3][bx + 2 + i * 4 + q % 3] = (255, 255, 0)
        a, f, fp = ps[k]; pix = render(rom, fp); m = boots(pix, (a, f))
        for (x, y), c in pix.items():
            X, Y = bx + cw // 2 + x, by + chh - 8 + y
            if bx <= X < bx + cw and by + 8 <= Y < by + chh: buf[Y][X] = (255, 0, 255) if (x, y) in m else _rgb(pal[32 + c])
    _png(out, buf, 4)

def mock(rom, out, nums, kinds):
    pal = _pal(rom); ps = poses(rom); order = [8, 3, 4, 5]; cw, chh = 60, 64
    buf = [[(40, 40, 48)] * (len(nums) * cw) for _ in range(chh * len(kinds))]
    for vi, v in enumerate(kinds):
        for j, n in enumerate(nums):
            a, f, fp = ps[n - 1]; pix = render(rom, fp); m = boots(pix, (a, f))
            for (x, y), c in pix.items():
                X, Y = j * cw + cw // 2 + x, vi * chh + chh - 12 + y
                if not (0 <= X < len(nums) * cw and vi * chh <= Y < (vi + 1) * chh): continue
                w = pal[32 + c]
                if v < 0 and (x, y) in m: buf[Y][X] = (255, 0, 255); continue
                if v > 0 and (x, y) in m and c in order: w = BOOTCOL[v][order.index(c)]
                buf[Y][X] = _rgb(w)
    _png(out, buf, 6)

def cmp(rom, log):
    import re
    keys = all_keys(rom); got = {}
    for l in open(log, errors='replace'):
        m = re.search(r'bootcol: anim (\w+) frm (\w+) boot px (\d+)', l)
        if m: got[(int(m[1], 16), int(m[2], 16))] = int(m[3])
    bad = 0
    for k, v in sorted(got.items()):
        ref = len(boots(render(rom, keys[k]), k)) if k in keys else -1
        if ref != v: bad += 1; print('MISMATCH anim %X frm %d: game %d, reference %d' % (k[0], k[1], v, ref))
    print('%d poses compared, %d mismatches' % (len(got), bad))
    return bad

if __name__ == '__main__':
    if len(sys.argv) < 4: print(__doc__); sys.exit(1)
    cmd, rom = sys.argv[1], open(sys.argv[2], 'rb').read()
    if cmd == 'sheet': sheet(rom, sys.argv[3], *(int(v) for v in sys.argv[4:6]))
    elif cmd == 'mock': mock(rom, sys.argv[3], [int(v) for v in sys.argv[4].split(',')], [int(v) for v in (sys.argv[5] if len(sys.argv) > 5 else '0,-1').split(',')])
    elif cmd == 'cmp': sys.exit(1 if cmp(rom, sys.argv[3]) else 0)
    else: print(__doc__); sys.exit(1)
