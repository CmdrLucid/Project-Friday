# Trailer 2.0 scenes (see shoot.py). base: a user recording that loads its save (input prefix up to 'cut'); at = warp frame (default cut + 40);
# input = (frame relative to 'at', keys); keep = (first, last) frame relative to 'at'; opts = option files in the isolated HOME (.landstalker_<k>).
BASES = {
    "now": {"rec": "20261117_0811", "cut": 250},     # Mercator 700 at frame 240, the user's progress of 2026-11-17
    "lit": {"rec": "20261103_1803", "cut": 2040},    # the lightedges sweep base
}
ORIG = {"lighting": "0", "hud": "0", "swordfx": "0", "bootcol": "0", "daynight": "0"}
DAY = {"LANDSTALKER_DAYLEN": "100000"}          # time of day stands still (with LANDSTALKER_DAYTIME)
WALK = [(60, "R"), (250, "D"), (330, "L"), (520, "U"), (600, "R"), (700, "")]   # a loop in Massan (x 21..40, y 38..41)
# every scene: warp at 'at', the light settles ~2 s (no shadow build-up on screen), Nigel moves only inside free cells (shoot.py reports STUCK AT WALL)
SCENES = {
    "castle":   {"warp": "55:48,17", "keep": (130, 330), "input": [(170, "L"), (238, "")], "note": "castle entrance hall 55: along the arched wall towards the guards"},
    "church":   {"warp": "700", "keep": (120, 330), "input": [(170, "R"), (225, "")]},
    "lava":     {"warp": "267:13,58", "keep": (120, 420), "input": [(150, "U"), (362, "")]},
    "water":    {"warp": "283", "keep": (120, 330), "input": [(150, "L"), (170, "")]},
    "sun":      {"warp": "592:20,38", "keep": (120, 330), "input": [(150, "R"), (306, "")], "env": dict(DAY, LANDSTALKER_DAYTIME="16.5")},
    "m_night":  {"warp": "592:20,38", "keep": (120, 330), "input": [(150, "R"), (306, "")], "env": dict(DAY, LANDSTALKER_DAYTIME="22.5")},
    "tlapse":   {"warp": "632", "keep": (40, 560), "input": [], "env": {"LANDSTALKER_DAYTIME": "14.8", "LANDSTALKER_DAYLEN": "0.5"}},
}
# swords: the same input twice (swordfx 0 | 1) for the split screen; Quick Equip by test aid (hold R2 = EQHOLD, direction taps = EQDIR frame:dir 0 up 1 right 2 down 3 left)
SW_EQ = "r+150-r+175,r+420-r+445,r+690-r+715,r+960-r+985"
SW_SEGS = [200, 530, 860, 1190]   # per sword: Quick Equip one step LEFT at s, charged swing at s+170, plain swing at s+250
SCENES["swords_o"] = {"warp": "95:18,33", "keep": (120, 1520), "input": [(140, 'D'), (144, ''), (370, 'C'), (374, ''), (450, 'C'), (454, ''), (700, 'C'), (704, ''), (780, 'C'), (784, ''), (1030, 'C'), (1034, ''), (1110, 'C'), (1114, ''), (1360, 'C'), (1364, ''), (1440, 'C'), (1444, '')], "opts": dict(ORIG, hud="1"),
                     "env": {"LANDSTALKER_EQHOLD": "r+200-r+225,r+530-r+555,r+860-r+885,r+1190-r+1215", "LANDSTALKER_EQDIR": "r+205:0,r+215:3,r+535:0,r+545:3,r+865:0,r+875:3,r+1195:0,r+1205:3,r+1211:3"}}
SCENES["swords_n"] = dict(SCENES["swords_o"], opts={"swordfx": "1"})
