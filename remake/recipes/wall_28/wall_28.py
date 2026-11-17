#!/usr/bin/env python3
"""NEAR-FINAL BACK WALL of the swamp shrine boss room 28 (light shape; recipe only, no ROM data).
User 2026-11-15 (recording of room 28): 'hier ist doch eine harte Schattenkante' right of the boss statue.  Cause: the game's wall cells (row y 18, x 17..40,
and the pilaster blocks in row 19 at x 21..22 / 36..37; height word $48 = 128) are 48 LOWER than the drawn wall: the drawn top of the ornament band lies on z 176
(remake/tools/rom_picture.py + an overlay of the raised cell tops at 3x / 4x, 2026-11-15), so the light saw the upper third of the wall as the flat TOP of a low
wall; the statue's flames (z 77..109) lit the lower part only = a hard diagonal edge through the red drapes.
Model (measured on the drawing, front faces on the game's cell edges):
  * wall blocks: row 18 (y 288..304) x 272..656 and the pilaster blocks of row 19 (y 304..320) x 336..368 / 576..608, floor 48 .. top 176, edges r 1.5;
  * the ornamented fronts (v2, 5x measure at U 1248): bead rows (r 2.4, every 8 along x) at z 167 / 134 / 102 / 52, a grille of vertical bars
    (every 4, r 0.8) between z 139 and 161 framed by two thin rails; the forward blocks carry two lattice pilasters each (raised frames).
The gargoyle stands in row 19 (height $45 = 80) and the statue niche keep the game's cells (the niche is drawn black, the lintel above it is the wall).
  python3 remake/recipes/wall_28/wall_28.py OUTDIR  -> OUTDIR/wall_28.obj"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "lib")); sys.path.insert(0, os.path.join(HERE, "..", "balustrade"))
import furniture as F, balustrade as B

FLOOR, TOP = 48.0, 176.0
WALL = (272.0, 656.0, 288.0, 304.0)                        # row 18, x 17..40 (the niche part keeps the wall: drawn black, the lintel is wall)
BLOCKS = [(336.0, 368.0, 304.0, 320.0), (576.0, 608.0, 304.0, 320.0)]   # the forward pilaster blocks of row 19 (two lattice pilasters each)
SECTIONS = [(272.0, 336.0), (368.0, 448.0), (528.0, 576.0), (608.0, 656.0)]   # the ornamented wall fronts between blocks and niche (niche x 448..528)
BEADS = [167.0, 134.0, 102.0, 52.0]        # bead rows (centre z), measured at U 1248 (5x): top cornice, under the grille, under the drapes, plinth
BEAD_R, BEAD_STEP = 2.4, 8.0               # the drawn beads sit on the 8 grid along x, ~6 px wide
GRILLE = (139.0, 161.0, 4.0, 0.8)          # vertical bars between the top two bead rows: z0, z1, spacing, radius
RAILS = [(160.5, 162.5), (137.0, 139.0)]   # thin rails framing the grille

def sphere(x, y, z, r):
    return F.lathe(x, y, z - r, 1.0, [(0.0, 0.0)] + [(r - r * __import__("math").cos(__import__("math").pi * k / 8), r * __import__("math").sin(__import__("math").pi * k / 8)) for k in range(1, 8)] + [(2 * r, 0.0)], seg=12)

def build():
    m = [F.rbox(WALL[0], WALL[1], WALL[2], WALL[3], FLOOR, TOP, 1.2, n=2, flat_bottom=True)]
    yf = WALL[3]
    for x0, x1 in SECTIONS:
        for zb in BEADS:
            g = x0 + BEAD_STEP / 2
            while g < x1 - 1: m.append(sphere(g, yf + 0.6, zb, BEAD_R)); g += BEAD_STEP
        for z0, z1 in RAILS: m.append(F.rbox(x0, x1, yf - 1.0, yf + 1.0, z0, z1, 0.6, n=2))
        g = x0 + GRILLE[2] / 2
        while g < x1 - 0.5: m.append(F.tube([(g, yf + 0.4, GRILLE[0]), (g, yf + 0.4, GRILLE[1])], [GRILLE[3], GRILLE[3]], seg=8)); g += GRILLE[2]
    for x0, x1, y0, y1 in BLOCKS:
        m.append(F.rbox(x0, x1, y0, y1, FLOOR, TOP, 1.2, n=2, flat_bottom=True))
        for p0 in (x0, x0 + 16.0):   # each lattice pilaster: a raised frame (1 unit) on the block front
            for a, b, c, d in ((p0 + 1, p0 + 3, FLOOR + 2, TOP - 2), (p0 + 13, p0 + 15, FLOOR + 2, TOP - 2), (p0 + 1, p0 + 15, TOP - 4, TOP - 2), (p0 + 1, p0 + 15, FLOOR + 2, FLOOR + 4)):
                m.append(F.rbox(a, b, y1 - 0.5, y1 + 1.0, c, d, 0.4, n=1))
    return m

if __name__ == "__main__":
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    B.write(build(), os.path.join(out, "wall_28.obj"), "back wall with cornice and bead band, room 28")
    print("wall_28: -> %s/wall_28.obj" % out)
