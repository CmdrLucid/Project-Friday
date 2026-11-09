#!/usr/bin/env python3
"""fit_foot.py ROM ROOM U0 V0 W H [--z0 16] [--rgb R,G,B[;R,G,B...]] [--tol 12] [--full] [--colors] [--minrun 4] [--eave]
MEASURES the ground footprint of ONE box shaped building on the drawn picture (light shapes / remake recipes, LIGHT_PROXY_PLAN rule
'measure with a point of known height': the wall FOOT stands on the ground at z0, so every foot pixel fixes x and y exactly).
The window U0 V0 W H (room picture coordinates, as rom_picture.py) must hold only that building (plus ground). Its layer A pixels
(optionally only those near the --rgb wall colours) give, per picture column, the lowest building pixel = the foot line:
  left of the front corner the +y wall:  Y1 = V - U / 2 + 592 + z0      right of it the +x wall:  X1 = V + U / 2 - 592 + z0
(projection U = x - y + 1184, V = (x + y) / 2 - z, docs/FORMATS.md); the leftmost / rightmost foot columns give X0 = U - 1184 + Y1 and
Y0 = X1 - U + 1184.  Prints the footprint (game units) and how many columns agree (+-1), so a recipe part can be checked or corrected.
Local measuring tool: reads the user's own ROM, writes nothing."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "landstalker", "tools"))
import romrender, rom_picture

def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

a = [s for i, s in enumerate(sys.argv[1:], 1) if not s.startswith('--') and not (i > 1 and sys.argv[i - 1].startswith('--'))]
rom = open(a[0], 'rb').read(); room = int(a[1]); U0, V0, W, H = map(int, a[2:6])
z0 = int(opt('--z0', '16')); tol = int(opt('--tol', '12'))
cols = [tuple(int(v) for v in c.split(',')) for c in opt('--rgb', '').split(';') if c]
g, r, pa, pb, getpal = romrender.rom_planes(rom, room)
full = '--full' in sys.argv   # the composed picture (both planes; needs --rgb): walls drawn partly in layer B
if full: F = romrender.compose(pa, pb, getpal, U0, V0, W, H, romrender.md_to_rgb(0), g['tiles']); A = bytearray(W * H * 4); A[0::4], A[1::4], A[2::4], A[3::4] = F[0::3], F[1::3], F[2::3], bytes([255]) * (W * H)
else: A = rom_picture.layer_a(pa, getpal, g['tiles'], U0, V0, W, H)
def ok(x, y):
    o = (y * W + x) * 4
    if not A[o + 3]: return False
    if not cols: return True
    return any(abs(A[o] - c[0]) + abs(A[o + 1] - c[1]) + abs(A[o + 2] - c[2]) <= tol for c in cols)
foot = {}
minrun = int(opt('--minrun', '4'))
for x in range(W):   # per column the LONGEST run of building pixels (gaps of 1 allowed); its lower end + 1 = where the wall meets the ground
    best, cur, start, gap = None, 0, None, 0       # (single bright dots in the grass share the wall colours: a lone pixel is no wall)
    for y in range(H):
        if ok(x, y):
            if start is None: start = y
            cur = y; gap = 0
        elif start is not None:
            gap += 1
            if gap > 1:
                if best is None or cur - start > best[1] - best[0]: best = (start, cur)
                start, gap = None, 0
    if start is not None and (best is None or cur - start > best[1] - best[0]): best = (start, cur)
    if best and best[1] - best[0] + 1 >= minrun: foot[U0 + x] = V0 + best[1] + 1
if '--colors' in sys.argv:   # list the most common colours of the window (to pick the wall colours for --rgb)
    c = collections.Counter(tuple(A[(y * W + x) * 4:(y * W + x) * 4 + 3]) for y in range(H) for x in range(W) if A[(y * W + x) * 4 + 3])
    print(' '.join('%d,%d,%d:%d' % (k[0], k[1], k[2], n) for k, n in c.most_common(24))); sys.exit(0)
if len(foot) < 4: print('fit_foot: too few building columns in the window'); sys.exit(1)
us = sorted(foot); uc = max(us, key=lambda u: (foot[u], -abs(u - (us[0] + us[-1]) / 2)))   # the front corner = the lowest foot point
ly = collections.Counter(foot[u] - u / 2 + 592 + z0 for u in us if u < uc - 2)
rx = collections.Counter(foot[u] + u / 2 - 592 + z0 for u in us if u > uc + 2)
def best(c): return max(c.items(), key=lambda t: t[1]) if c else (None, 0)
Y1, ny = best(ly); X1, nx = best(rx)
gy = sum(n for v, n in ly.items() if Y1 is not None and abs(v - Y1) <= 1); gx = sum(n for v, n in rx.items() if X1 is not None and abs(v - X1) <= 1)
print('room %d window U %d..%d V %d..%d, %d foot columns, front corner U %d V %d' % (room, U0, U0 + W, V0, V0 + H, len(us), uc, foot[uc]))
if Y1 is not None: print('  +y wall (left of the corner):  Y1 = %.1f  (%d of %d columns within 1)' % (Y1, gy, sum(ly.values())))
if X1 is not None: print('  +x wall (right of the corner): X1 = %.1f  (%d of %d columns within 1)' % (X1, gx, sum(rx.values())))
if Y1 is not None:   # the +y wall's own ends: the longest run of columns on its foot line (robust when the +x wall is hidden)
    run, best_run = [], []
    for u in us:
        if abs(foot[u] - (u / 2 - 592 + Y1 - z0)) <= 1 and (not run or u == run[-1] + 1): run.append(u)
        elif abs(foot[u] - (u / 2 - 592 + Y1 - z0)) <= 1: run = [u]
        else: run = []
        if len(run) > len(best_run): best_run = list(run)
    if best_run: print('  +y wall foot runs U %d..%d -> X0 = %.1f, X1 = %.1f (its right end = the front corner)' % (best_run[0], best_run[-1], best_run[0] - 1184 + Y1, best_run[-1] + 1 - 1184 + Y1))
if X1 is not None:
    run, best_run = [], []
    for u in us:
        if abs(foot[u] - (X1 - u / 2 + 592 - z0)) <= 1 and (not run or u == run[-1] + 1): run.append(u)
        elif abs(foot[u] - (X1 - u / 2 + 592 - z0)) <= 1: run = [u]
        else: run = []
        if len(run) > len(best_run): best_run = list(run)
    if best_run: print('  +x wall foot runs U %d..%d -> Y1 = %.1f, Y0 = %.1f' % (best_run[0], best_run[-1], X1 - (best_run[0] - 1184), X1 - (best_run[-1] + 1 - 1184)))
tops = {}
for x in range(W):   # --eave: per foot column the top of the same wall run (first non-wall pixel above it) = the wall's visible top (eave / roof edge)
    u = U0 + x
    if u not in foot: continue
    y = foot[u] - V0 - 1; gap = 0
    while y > 0:
        if ok(x, y - 1): y -= 1; gap = 0
        elif gap < 1 and y > 1 and ok(x, y - 2): y -= 2
        else: break
    tops[u] = V0 + y
def ztop(u, wall):   # height of the wall top at column u (foot fixes x / y on that wall)
    if wall == 'y': x, yy = u + Y1 - 1184, Y1
    else: x, yy = X1, X1 - (u - 1184)
    return (x + yy) / 2 - tops[u]
if '--eave' in sys.argv:
    for wall, line in (('y', Y1), ('x', X1)):
        if line is None: continue
        f = (lambda u: abs(foot[u] - (u / 2 - 592 + Y1 - z0)) <= 1) if wall == 'y' else (lambda u: abs(foot[u] - (X1 - u / 2 + 592 - z0)) <= 1)
        zs = sorted(ztop(u, wall) for u in us if u in tops and f(u))
        if zs: print('  %s wall top (eave): median z %.1f over %d columns (min %.1f max %.1f)' % ('+y' if wall == 'y' else '+x', zs[len(zs) // 2], len(zs), zs[0], zs[-1]))
if Y1 is not None: print('  leftmost foot U %d  -> X0 = %.1f' % (us[0], us[0] - 1184 + Y1))
if X1 is not None: print('  rightmost foot U %d -> Y0 = %.1f' % (us[-1], X1 - us[-1] + 1184))
if '-v' in sys.argv: print('  foot V per U:', ' '.join('%d:%d' % (u, foot[u]) for u in us))
