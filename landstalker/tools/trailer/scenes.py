# Trailer 2.0 scenes (see shoot.py). base: a user recording that loads its save (input prefix up to 'cut'); at = warp frame (default cut + 40);
# input = (frame relative to 'at', keys); keep = (first, last) frame relative to 'at'; opts = option files in the isolated HOME (.landstalker_<k>).
BASES = {
    "now": {"rec": "20261117_0811", "cut": 250},     # Mercator 700 at frame 240, the user's progress of 2026-11-17
    "lit": {"rec": "20261103_1803", "cut": 2040},    # the lightedges sweep base
}
ORIG = {"lighting": "0", "hud": "0", "swordfx": "0", "bootcol": "0", "daynight": "0"}
DAY = {"LANDSTALKER_DAYLEN": "100000"}          # time of day stands still (with LANDSTALKER_DAYTIME)
WALK = [(60, "R"), (250, "D"), (330, "L"), (520, "U"), (600, "R"), (700, "")]   # a loop in Massan (x 21..40, y 38..41)
# directions with the user's key file: D / R = +X, U / L = -X, DL = +Y, UR = -Y (shoot.py check.chk columns 3 / 4)
# every scene: warp at 'at', the light settles ~2 s (no shadow build-up on screen), Nigel moves only inside free cells (shoot.py reports STUCK AT WALL)
SCENES = {
    "castle":   {"warp": "55:48,17", "keep": (130, 330), "input": [(170, "L"), (238, "")], "note": "castle entrance hall 55: along the arched wall towards the guards"},
    "church":   {"warp": "700", "keep": (120, 330), "input": [(170, "R"), (225, "")]},
    "lava":     {"warp": "267:13,58", "keep": (120, 420), "input": [(150, "U"), (362, "")]},
    "water":    {"warp": "474:32,28", "keep": (120, 360), "input": [(150, "DL"), (205, "")], "env": dict(DAY, LANDSTALKER_DAYTIME="10.5"), "note": "Verla shore pier: water in front of Nigel = his reflection is on the water"},
    "beach":    {"rec": "20261117_1210", "keep": (2150, 2700), "wide": 19, "size": "1920x1200", "vf": "crop=1916:1078:0:61,scale=1920:1080", "note": "user recording 2026-11-17: beach room 455, Nigel in the shallow water = reflection (user pick)"},
    "castle2":  {"rec": "20261117_1209", "keep": (1800, 2010), "wide": 19, "size": "1920x1200", "vf": "crop=1916:1078:0:61,scale=1920:1080", "note": "user recording 2026-11-17: castle main hall 62, last run top-left -> bottom-right facing the camera (user pick for Dynamic Lighting)"},
    "sun":      {"warp": "592:22,38", "keep": (120, 330), "input": [(150, "R"), (290, "")], "env": dict(DAY, LANDSTALKER_DAYTIME="16.5")},
    "m_night":  {"warp": "592:22,38", "keep": (120, 400), "input": [(150, "R"), (290, "")], "env": dict(DAY, LANDSTALKER_DAYTIME="22.5")},
    "tlapse":   {"warp": "632", "keep": (40, 560), "input": [], "env": {"LANDSTALKER_DAYTIME": "14.8", "LANDSTALKER_DAYLEN": "0.5"}},
}
# swords: the same input twice (swordfx 0 | 1) for the split screen; Quick Equip by test aid (hold R2 = EQHOLD, direction taps = EQDIR frame:dir 0 up 1 right 2 down 3 left)
SW_EQ = "r+150-r+175,r+420-r+445,r+690-r+715,r+960-r+985"
SW_SEGS = [200, 530, 860, 1190]   # per sword: Quick Equip one step LEFT at s, charged swing at s+170, plain swing at s+250
SCENES["swords_o"] = {"warp": "95:18,33", "keep": (120, 1520), "input": [(140, 'D'), (144, ''), (370, 'C'), (374, ''), (450, 'C'), (454, ''), (700, 'C'), (704, ''), (780, 'C'), (784, ''), (1030, 'C'), (1034, ''), (1110, 'C'), (1114, ''), (1360, 'C'), (1364, ''), (1440, 'C'), (1444, '')], "opts": dict(ORIG, hud="1"),
                     "env": {"LANDSTALKER_EQHOLD": "r+200-r+225,r+530-r+555,r+860-r+885,r+1190-r+1215", "LANDSTALKER_EQDIR": "r+205:0,r+215:3,r+535:0,r+545:3,r+865:0,r+875:3,r+1195:0,r+1205:3,r+1211:3"}}
SCENES["swords_n"] = dict(SCENES["swords_o"], opts={"swordfx": "1"})
SCENES["lava_off"] = dict(SCENES["lava"], opts={"lighting": "0"})   # spike ball shadow bug: the same run without light
SCENES["lava_chip"] = dict(SCENES["lava"], opts={"lighting": "0"}, env={"LANDSTALKER_OWN": "0", "LANDSTALKER_OWN_NOCHIP": "0"})
# boot colours: Quick Equip DOWN (boots) one step LEFT every 130 frames, Nigel faces the camera in the quiet room 95
SCENES["boots"] = {"warp": "95:18,33", "keep": (180, 720), "input": [(140, 'D'), (144, '')], "opts": {"bootcol": "1"},
                  "env": {"LANDSTALKER_EQHOLD": "r+200-r+225,r+330-r+355,r+460-r+485,r+590-r+615", "LANDSTALKER_EQDIR": "r+205:2,r+215:3,r+335:2,r+345:3,r+465:2,r+475:3,r+595:2,r+605:3"}}
SCENES["fftest"] = {"warp": "458", "keep": (120, 600), "input": [], "env": dict(DAY, LANDSTALKER_DAYTIME="23")}
SCENES["fridaytest"] = {"warp": "632", "keep": (120, 700), "input": [(180, "M"), (184, ""), (300, "C"), (304, ""), (400, "C"), (404, ""), (500, "C"), (504, "")], "opts": {"friday": "1"}}
SCENES["talktest"] = {"warp": "700", "keep": (120, 700), "input": [(160, "U"), (163, ""), (180, "C"), (184, ""), (330, "C"), (334, "")], "opts": {"lang": "de"}}
SCENES["priest"] = {"rec": "20261117_0810", "keep": (240, 1680), "wide": 19, "size": "1920x1200", "vf": "crop=1916:1078:0:61,scale=1920:1080"}
for _l in ("en", "de", "en_tone", "fr", "ko", "ja"):   # languages montage: the priest's first text box (user rec_20261117_0810, box opens ~640)
    SCENES["lang_" + _l] = dict(SCENES["priest"], keep=(600, 800), opts={"lang": _l}, vf="crop=1916:1078:0:121,scale=1920:1080")   # cut only at the top: the box's last line sits in the bottom 61 px
SCENES["maptest"] = {"warp": "166", "keep": (150, 150), "input": [], "env": {"LANDSTALKER_MAPSHOT": "r+150", "LANDSTALKER_OSHOT_SIZE": "1920x1080"}}
SCENES["map_a"] = dict(SCENES["maptest"])
SCENES["map_b"] = dict(SCENES["maptest"], env=dict(SCENES["maptest"]["env"], LANDSTALKER_MAPSHOT_SEL="171"))
SCENES["map_c"] = dict(SCENES["maptest"], env=dict(SCENES["maptest"]["env"], LANDSTALKER_MAPSHOT_SEL="171", LANDSTALKER_MAPSHOT_FLAG="171"))
SCENES["sprint"] = {"warp": "632:22,40", "keep": (120, 320), "input": [(150, "D"), (280, "")], "env": dict(DAY, LANDSTALKER_DAYTIME="11", LANDSTALKER_SPRINTHOLD="r+150-r+280")}
SCENES["sun_hud0"] = dict(SCENES["sun"], opts={"hud": "0"})
SCENES["friday"] = dict(SCENES["fridaytest"], keep=(120, 420))
SCENES["title_de"] = {"rec": "20261117_0810", "keep": (10, 300), "wide": 19, "size": "1920x1200", "vf": "crop=1916:1078:0:61,scale=1920:1080", "opts": {"lang": "de"}}
# user 2026-11-17: Modern HUD on another scene (old HUD long enough), particles as one feature with several kinds
SCENES["hud_o"] = {"warp": "632:30,40", "keep": (120, 480), "input": [(150, "D"), (300, "")], "opts": {"hud": "0"}, "env": dict(DAY, LANDSTALKER_DAYTIME="11")}
SCENES["hud_n"] = dict(SCENES["hud_o"], opts={"hud": "1"})
SCENES["leaves"] = {"warp": "458", "keep": (120, 420), "input": [], "env": dict(DAY, LANDSTALKER_DAYTIME="12")}
SCENES["drops"] = {"warp": "283", "keep": (120, 420), "input": []}
SCENES["drops178"] = {"warp": "178", "keep": (120, 420), "input": []}
for _n in ("leaves", "fftest", "castle2", "lava", "drops", "drops178"):   # particle finder: the same scene without particles (diff = where they fly)
    SCENES[_n + "_np"] = dict(SCENES[_n], env=dict(SCENES[_n].get("env", {}), LANDSTALKER_AMBIENT="0"))
