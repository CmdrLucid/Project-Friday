"""cabinet.py - near-final CASE FURNITURE from parts (user 2026-11-12: 'immer gleich echte 3D Formen fuers Licht', also for pieces whose collision box
already fits the drawing): chests of drawers, wardrobes, bookcases, glass cabinets, hearths. Every part is a closed rounded box (furniture.rbox), so the
GPU shadow maps get edge twins. Reliefs are >= 1 unit (drawer gaps, recessed panels, compartments): sub-pixel reliefs make dotted light lines (LESSONS,
0a413). GAME coordinates x east, y south, z up, units.

cabinet(x0, x1, y0, y1, z0, z1, face, rows, ...) builds a case standing in the box x0..x1 / y0..y1 with its FRONT on side `face` ('+x', '+y', '-x', '-y')
and `rows` from the bottom up: ('plinth', h) | ('drawers', h, n) | ('doors', h, n) | ('glass', h, n) | ('shelf', h[, n[, contents]]) (open compartment(s): n compartments with
dividers; contents 'books' (default) / 'bottles' / 'plates' (upright plate stacks) / None) | ('open', h[, n]) (empty compartments). The heights are scaled to fill z0 .. z1 - top."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from furniture import rbox, lathe

def _mapper(x0, x1, y0, y1, face):
    """local (u across the front, v depth from the front plane inwards, z) -> world box"""
    if face == "+y": W, D = x1 - x0, y1 - y0; f = lambda u0, u1, v0, v1: (x0 + u0, x0 + u1, y1 - v1, y1 - v0)
    elif face == "-y": W, D = x1 - x0, y1 - y0; f = lambda u0, u1, v0, v1: (x1 - u1, x1 - u0, y0 + v0, y0 + v1)
    elif face == "+x": W, D = y1 - y0, x1 - x0; f = lambda u0, u1, v0, v1: (x1 - v1, x1 - v0, y0 + u0, y0 + u1)
    else: W, D = y1 - y0, x1 - x0; f = lambda u0, u1, v0, v1: (x0 + v0, x0 + v1, y1 - u1, y1 - u0)
    return W, D, f

BOOKS = [(2.0, 0.86), (1.5, 0.74), (2.5, 0.92), (1.75, 0.8), (2.25, 0.68), (1.5, 0.9), (3.0, 0.78), (2.0, 0.95), (1.75, 0.7), (2.5, 0.84)]   # (width, height share)

def cabinet(x0, x1, y0, y1, z0, z1, face, rows, top=1.5, over=0.8, side=1.2, back=1.0, r=0.35, books=True):
    W, D, M = _mapper(x0, x1, y0, y1, face); out = []
    B = lambda u0, u1, v0, v1, za, zb, rr=r: out.append(rbox(*M(u0, u1, v0, v1), za, zb, min(rr, (u1 - u0) / 2.5, (v1 - v0) / 2.5, (zb - za) / 2.5), n=1))
    zt = z1 - top; B(0.0, W, -over, D, zt, z1, 0.5)                                                       # top slab, overhanging the front
    tot = sum(rw[1] for rw in rows); k = (zt - z0) / tot; z = z0
    B(0.0, side, 1.0, D, z0, zt); B(W - side, W, 1.0, D, z0, zt)                                         # the two side walls (behind the front frame)
    B(side, W - side, D - back, D, z0, zt)                                                               # back panel
    for rw in rows:
        kind, h = rw[0], rw[1] * k; za, zb = z, z + h; z = zb; n = rw[2] if len(rw) > 2 else 1
        if kind == "plinth":
            B(1.0, W - 1.0, 1.0, D - 0.5, za, zb)                                                        # set back 1: a dark line at the foot
            continue
        B(0.0, side, 0.0, 1.0, za, zb); B(W - side, W, 0.0, D * 0 + 1.0, za, zb)                          # front stiles
        if kind == "drawers":
            B(side, W - side, 1.0, D - back, za, zb)                                                     # carcass behind the drawer fronts
            g = 0.9; w = (W - 2 * side - (n + 1) * g) / n
            for i in range(n):
                u = side + g + i * (w + g); B(u, u + w, 0.0, 1.0, za + g * 0.5, zb - g * 0.5, 0.3)        # drawer front, 1 proud of the carcass
        elif kind in ("doors", "glass"):
            B(side, W - side, 1.0 if kind == "doors" else 2.5, D - back, za, zb)                          # carcass (glass: 1.5 further back = the dark glass)
            fw = 1.6; w = (W - 2 * side) / n
            for i in range(n):
                u0 = side + i * w; u1 = u0 + w
                B(u0, u0 + fw, 0.0, 1.0, za, zb); B(u1 - fw, u1, 0.0, 1.0, za, zb)                       # door frame: stiles
                B(u0 + fw, u1 - fw, 0.0, 1.0, za, za + fw); B(u0 + fw, u1 - fw, 0.0, 1.0, zb - fw, zb)   # rails
                if kind == "doors": B(u0 + fw, u1 - fw, 1.0, 1.6, za + fw, zb - fw, 0.2)                 # the panel, 1 recessed
        elif kind in ("shelf", "open") and (n > 1 or (len(rw) > 3 and rw[3] in ("bottles", "plates", None))):
            B(side, W - side, 0.0, D - back, za, za + 1.2)                                               # the shelf board
            cw = (W - 2 * side) / n; what = (rw[3] if len(rw) > 3 else "books") if kind == "shelf" else None
            for i in range(1, n): uu = side + i * cw; B(uu - 0.6, uu + 0.6, 0.0, D - back, za, zb)       # dividers
            for i in range(n):
                ua, ub = side + i * cw + 0.6, side + (i + 1) * cw - 0.6; vm = (D - back) / 2 + 0.5
                if what == "bottles":
                    for t in (0.22, 0.5, 0.78):
                        xa, xb, ya, yb = M(ua + t * (ub - ua), ua + t * (ub - ua), vm, vm); ax, ay = (xa + xb) / 2, (ya + yb) / 2
                        out.append(lathe(ax, ay, za + 1.2, (h - 1.2) * 0.75, [(0.0, 1.1), (0.6, 1.2), (0.75, 0.5), (1.0, 0.5)], seg=10))
                elif what == "plates":
                    B(ua + 0.6, ub - 0.6, vm - 1.0, vm + 1.0, za + 1.2, za + 1.2 + (h - 1.2) * 0.8, 0.8)  # upright plate stack
                elif what == "books":
                    u = ua
                    for j in range(20):
                        bw, bh = BOOKS[(j + i * 3) % len(BOOKS)]
                        if u + bw > ub: break
                        B(u, u + bw, 1.5, D - back - 0.3, za + 1.2, za + 1.2 + (h - 2.4) * bh, 0.2); u += bw
        elif kind in ("shelf", "open"):
            B(side, W - side, 0.0, D - back, za, za + 1.2)                                               # the shelf board
            if kind == "shelf" and books:
                u, j = side + 0.6, 0
                while True:
                    bw, bh = BOOKS[j % len(BOOKS)]; j += 1
                    if u + bw > W - side - 0.4: break
                    B(u, u + bw, 1.5, D - back - 0.3, za + 1.2, za + 1.2 + (h - 2.4) * bh, 0.2); u += bw
    B(0.0, W, 0.0, 1.0, z, zt) if zt - z > 0.3 else None                                                 # front rail under the top
    return out

def hearth(x0, x1, y0, y1, z0, z1, face, open_u=(0.2, 0.75), open_h=0.7, depth=10.0, r=0.6):
    """a brick hearth block with the FIRE OPENING in its front (`face`): open_u = share of the front width (from, to), open_h = share of the height,
    depth = how far the opening goes in; a raised hearth stone in front of the opening's floor"""
    W, D, M = _mapper(x0, x1, y0, y1, face); out = []
    B = lambda u0, u1, v0, v1, za, zb, rr=r: out.append(rbox(*M(u0, u1, v0, v1), za, zb, min(rr, (u1 - u0) / 2.5, (v1 - v0) / 2.5, (zb - za) / 2.5), n=1))
    ua, ub = open_u[0] * W, open_u[1] * W; zo = z0 + open_h * (z1 - z0)
    B(0.0, ua, 0.0, D, z0, z1); B(ub, W, 0.0, D, z0, z1)                                                 # the two jambs
    B(ua, ub, 0.0, D, zo, z1)                                                                            # the lintel and the wall above
    B(ua, ub, depth, D, z0, zo)                                                                          # the back of the fire place
    B(ua, ub, 0.0, depth, z0, z0 + 1.5, 0.3)                                                             # the hearth floor stone
    return out
