# Trailer clip list (frame ranges of the user recordings, see capture.py SOURCES). wide/tall: 0/0 = original picture, 39/1 = 16:9 + Full Height.
CLIPS = {
    # opening: original 4:3 picture
    "jypta_o":   {"src": "intro", "a": 1980, "b": 2600, "wide": 0, "tall": 0},
    # the slow 4:3 -> 16:9 reveal: the same frames twice
    "ryuma_o":   {"src": "ryuma", "a": 780, "b": 1220, "wide": 0, "tall": 0},
    "ryuma_w":   {"src": "ryuma", "a": 780, "b": 1220},
    "title":     {"src": "mercator", "a": 1560, "b": 1740},
    "crt":       {"src": "dwarves", "a": 630, "b": 980},
    "options":   {"src": "swordfx", "a": 840, "b": 1240},
    "buyqty":    {"src": "ryuma", "a": 1660, "b": 1860},
    "menu":      {"src": "swords", "a": 700, "b": 900},
    "quickgaia": {"src": "mercator", "a": 4180, "b": 4400},
    "livegaia":  {"src": "jump430", "a": 2300, "b": 2510},
    "qequip":    {"src": "room21", "a": 880, "b": 1140, "win": 1,
                  "env": {"LANDSTALKER_EQHOLD": "900-1125", "LANDSTALKER_EQDIR": "930:0,970:0,1010:0,1050:0,1090:0"}},
    "vase":      {"src": "vase", "a": 1600, "b": 1820},
    "ffwd":      {"src": "room430", "a": 5040, "b": 5730},
    "harbour":   {"src": "intro", "a": 4180, "b": 4700},
    "m_jypta":   {"src": "intro", "a": 1650, "b": 1950},
    "m_forest":  {"src": "room430", "a": 6600, "b": 6900},
    "m_beach":   {"src": "jump430", "a": 2600, "b": 2900},
    "m_ryuma":   {"src": "ryuma", "a": 880, "b": 1180},
    "m_fight":   {"src": "room21", "a": 2500, "b": 2800},
    "m_stream":  {"src": "vase", "a": 760, "b": 1060},
    "m_woods":   {"src": "dwarves", "a": 3240, "b": 3540},
    "m_ruins":   {"src": "intro", "a": 3150, "b": 3450},
    "end":       {"src": "intro", "a": 12260, "b": 12720},
}
