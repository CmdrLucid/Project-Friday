# Trailer 2.0 scenes (see shoot.py). base: a user recording that loads its save (input prefix up to 'cut'); at = warp frame (default cut + 40);
# input = (frame relative to 'at', keys); keep = (first, last) frame relative to 'at'; opts = option files in the isolated HOME (.landstalker_<k>).
BASES = {
    "now": {"rec": "20261117_0811", "cut": 250},     # Mercator 700 at frame 240, the user's progress of 2026-11-17
    "lit": {"rec": "20261103_1803", "cut": 2040},    # the lightedges sweep base
}
ORIG = {"lighting": "0", "hud": "0", "swordfx": "0", "bootcol": "0", "daynight": "0"}
DAY = {"LANDSTALKER_DAYLEN": "100000"}          # time of day stands still (with LANDSTALKER_DAYTIME)
WALK = [(60, "R"), (250, "D"), (330, "L"), (520, "U"), (600, "R"), (700, "")]   # a loop in Massan (x 21..40, y 38..41)
SCENES = {
    # intro: the same walk twice, original picture (4:3, no light, old HUD) and the 2.0 picture
    "intro_o":  {"warp": "592:20,38", "keep": (40, 700), "input": WALK, "opts": ORIG, "wide": 0, "tall": 0, "size": "1440x1080", "env": dict(DAY, LANDSTALKER_DAYTIME="16.5")},
    "intro_n":  {"warp": "592:20,38", "keep": (40, 700), "input": WALK, "env": dict(DAY, LANDSTALKER_DAYTIME="16.5")},
    "castle":   {"warp": "55:35,19", "keep": (40, 260), "input": [(60, "R"), (250, "")], "note": "castle entrance hallway: walk along the torch wall"},
    "m_night":  {"warp": "592:20,38", "keep": (40, 400), "input": [(60, "R"), (380, "")], "env": dict(DAY, LANDSTALKER_DAYTIME="22.5")},
    "tlapse":   {"warp": "632", "keep": (40, 560), "input": [], "env": {"LANDSTALKER_DAYTIME": "14.8", "LANDSTALKER_DAYLEN": "0.5"}},
    "flies2":   {"warp": "636", "keep": (40, 400), "input": [(80, "D"), (330, "")], "env": dict(DAY, LANDSTALKER_DAYTIME="23")},
    "flies":    {"warp": "430:31,30", "keep": (40, 400), "input": [], "env": dict(DAY, LANDSTALKER_DAYTIME="23")},
    "lava":     {"warp": "267:13,58", "keep": (40, 400), "input": [(60, "U"), (390, "")]},
    "church":   {"warp": "700", "keep": (40, 240), "input": [(70, "R"), (125, "")]},
    "water":    {"warp": "283", "keep": (40, 360), "input": [(60, "L"), (200, "")]},
}
